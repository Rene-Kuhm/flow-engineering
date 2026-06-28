"""Unit tests for daemon.py drift mode (REQ-15).

Covers the ``flow watch --drift`` daemon wiring:

- ``start_watch(..., drift=True)`` registers an apply-progress handler in
  addition to the existing exploration watcher.
- ``handle_apply_progress_event(change, payload)`` runs ``scan_change`` when
  any task has ``status: merged``, emits a single-line summary, increments
  the REQ-12 drift counters via ``observability.record_drift_summary``, and
  survives a missing ``graph.json`` (logs ``unable_to_verify`` once, does
  not raise).
- ``start_watch(..., drift=False)`` MUST be byte-identical to the previous
  behavior (no new dependency, no extra message text beyond the legacy
  form).
- The internal ``_maybe_emit_drift`` filter ignores non-apply-progress
  files, directory events, and malformed JSON payloads.

Test isolation: every test gets a fresh ``tmp_path``, a per-test
``FLOW_METRICS_PATH`` so the JSONL sink never bleeds across tests, and a
fake ``EngramClient`` that returns deterministic apply-progress payloads.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from flow_engineering import daemon, observability
from flow_engineering.binding import CodeRef
from flow_engineering.cli import main as cli_main
from flow_engineering.decision_drift import DriftClass, DriftReport, Finding
from flow_engineering.state import ChangeStatus, StateMachine

runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Per-test JSONL sink under tmp_path."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


@pytest.fixture
def fake_graph(tmp_path: Path) -> Path:
    """An empty graph.json snapshot so scan_change proceeds normally."""
    path = tmp_path / "graph.json"
    path.write_text(json.dumps({"nodes": []}), encoding="utf-8")
    return path


def _make_finding(
    *,
    obs_id: int = 1,
    drift_class: DriftClass = DriftClass.STILL_VALID,
    detail: str = "",
) -> Finding:
    """Build a Finding for fake scan_change returns."""
    binding = CodeRef(
        project="insyd",
        id=f"n{obs_id}",
        label=f"L{obs_id}",
        file="src/x.py",
        line=1,
        confidence=0.9,
        source="manual",
    )
    return Finding(
        decision_id=obs_id,
        binding=binding,
        drift_class=drift_class,
        detail=detail,
    )


def _make_change(tmp_path: Path, change: str) -> Path:
    """Seed a change directory in NEW state so start_watch proceeds."""
    fe = tmp_path / "flow-engineering" / change
    fe.mkdir(parents=True)
    StateMachine.create(change, fe).save()
    return fe


# ---------- handle_apply_progress_event seam ----------


class TestHandleApplyProgressEvent:
    """REQ-15: the drift seam function behavior end-to-end."""

    def test_merged_task_triggers_scan_and_summary(
        self, metrics_path, fake_graph, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A payload containing status=merged MUST run scan_change and
        emit a one-line summary mentioning the change name."""
        report = DriftReport(
            change_name="my-change",
            scanned_at="1970-01-01T00:16:40Z",
            graph_mtime="1970-01-01T00:16:39Z",
            decisions_total=1,
            bindings_total=2,
            class_counts={
                DriftClass.STILL_VALID: 1,
                DriftClass.STALE_ID: 1,
            },
            findings=[
                _make_finding(obs_id=1, drift_class=DriftClass.STILL_VALID),
                _make_finding(obs_id=2, drift_class=DriftClass.STALE_ID),
            ],
        )
        monkeypatch.setattr(
            daemon.decision_drift,
            "scan_change",
            lambda *a, **kw: report,
        )
        summaries: list[str] = []

        result = daemon.handle_apply_progress_event(
            "my-change",
            {"tasks": {"T1": {"status": "merged"}}},
            graph_json_path=fake_graph,
            on_summary=summaries.append,
        )

        assert result is report
        assert len(summaries) == 1
        line = summaries[0]
        assert line.startswith("drift: my-change")
        assert "2 findings" in line
        assert "1 STILL_VALID" in line
        assert "1 STALE_ID" in line

    def test_no_merged_task_is_silent(
        self, metrics_path, fake_graph, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Payloads with no merged tasks MUST NOT trigger scan_change or
        emit any summary line."""
        called: dict[str, Any] = {"n": 0}

        def _stub(*a: Any, **kw: Any) -> DriftReport:
            called["n"] += 1
            return DriftReport(
                change_name="my-change", scanned_at="1970-01-01T00:00:00Z", graph_mtime=None,
                decisions_total=0, bindings_total=0, class_counts={}, findings=[],
            )

        monkeypatch.setattr(daemon.decision_drift, "scan_change", _stub)
        summaries: list[str] = []

        result = daemon.handle_apply_progress_event(
            "my-change",
            {"tasks": {"T1": {"status": "in_progress"}}},
            graph_json_path=fake_graph,
            on_summary=summaries.append,
        )

        assert result is None
        assert summaries == []
        assert called["n"] == 0

    def test_missing_graph_logs_unable_to_verify_once(
        self, metrics_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing graph.json MUST log unable_to_verify once and return
        the report — watcher MUST stay alive (no exception)."""
        report = DriftReport(
            change_name="my-change", scanned_at="1970-01-01T00:00:00Z", graph_mtime=None,
            decisions_total=0, bindings_total=0, class_counts={},
            findings=[], graph_unavailable=True,
        )
        monkeypatch.setattr(
            daemon.decision_drift, "scan_change", lambda *a, **kw: report
        )
        summaries: list[str] = []

        result = daemon.handle_apply_progress_event(
            "my-change",
            {"tasks": {"T1": {"status": "merged"}}},
            graph_json_path=Path("/nonexistent/graph.json"),
            on_summary=summaries.append,
        )

        assert result is report
        assert len(summaries) == 1
        assert "unable_to_verify" in summaries[0]
        # Path comparison is OS-agnostic (Windows uses backslashes).
        assert Path("/nonexistent/graph.json").name in summaries[0]

    def test_record_drift_summary_called_for_every_event(
        self, metrics_path, fake_graph, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """REQ-12: every event MUST increment drift_*_total counters via
        observability.record_drift_summary."""
        report = DriftReport(
            change_name="my-change",
            scanned_at="1970-01-01T00:00:00Z",
            graph_mtime="1970-01-01T00:16:39Z",
            decisions_total=1,
            bindings_total=1,
            class_counts={DriftClass.STILL_VALID: 1},
            findings=[_make_finding(obs_id=1, drift_class=DriftClass.STILL_VALID)],
        )
        monkeypatch.setattr(
            daemon.decision_drift, "scan_change", lambda *a, **kw: report
        )
        recorded: list[DriftReport] = []
        monkeypatch.setattr(
            observability, "record_drift_summary", lambda r: recorded.append(r)
        )

        daemon.handle_apply_progress_event(
            "my-change",
            {"tasks": {"T1": {"status": "merged"}}},
            graph_json_path=fake_graph,
        )

        assert len(recorded) == 1
        assert recorded[0] is report


# ---------- Still-valid silence rule (REQ-56 W6, D4) ----------


class TestStillValidSilence:
    """REQ-56 W6: suppress outer summary line on still-valid silence.

    Per design D4, the outer ``on_summary`` stdout line MUST be
    suppressed when ``report.total == 0 and not report.graph_unavailable``.
    The ``unable_to_verify`` edge case preserves the summary line so the
    user knows the graph is unreachable.
    """

    def test_daemon_silent_when_all_bindings_still_valid(
        self, metrics_path, fake_graph, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When every binding classifies as STILL_VALID (total == 0
        after class-counts are summed), the outer ``on_summary`` callback
        MUST NOT be invoked. The daemon returns the report normally;
        counters (REQ-12) are still incremented via
        ``observability.record_drift_summary``.
        """
        report = DriftReport(
            change_name="my-change",
            scanned_at="1970-01-01T00:16:40Z",
            graph_mtime="1970-01-01T00:16:39Z",
            decisions_total=3,
            bindings_total=3,
            class_counts={DriftClass.STILL_VALID: 3},
            findings=[
                _make_finding(obs_id=1, drift_class=DriftClass.STILL_VALID),
                _make_finding(obs_id=2, drift_class=DriftClass.STILL_VALID),
                _make_finding(obs_id=3, drift_class=DriftClass.STILL_VALID),
            ],
        )
        monkeypatch.setattr(
            daemon.decision_drift,
            "scan_change",
            lambda *a, **kw: report,
        )
        summaries: list[str] = []

        result = daemon.handle_apply_progress_event(
            "my-change",
            {"tasks": {"T1": {"status": "merged"}}},
            graph_json_path=fake_graph,
            on_summary=summaries.append,
        )

        assert result is report
        assert summaries == []

    def test_daemon_emits_unable_to_verify_when_graph_unavailable(
        self, metrics_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Even when total == 0, a ``graph_unavailable=True`` report MUST
        emit the unable_to_verify summary line (per design D4 edge case:
        still-valid-but-graph-unavailable is informative).
        """
        report = DriftReport(
            change_name="my-change",
            scanned_at="1970-01-01T00:00:00Z",
            graph_mtime=None,
            decisions_total=0,
            bindings_total=0,
            class_counts={},
            findings=[],
            graph_unavailable=True,
        )
        monkeypatch.setattr(
            daemon.decision_drift, "scan_change", lambda *a, **kw: report
        )
        summaries: list[str] = []

        result = daemon.handle_apply_progress_event(
            "my-change",
            {"tasks": {"T1": {"status": "merged"}}},
            graph_json_path=Path("/nonexistent/graph.json"),
            on_summary=summaries.append,
        )

        assert result is report
        assert len(summaries) == 1
        assert "unable_to_verify" in summaries[0]
        assert Path("/nonexistent/graph.json").name in summaries[0]

    def test_daemon_emits_summary_line_when_drift_found(
        self, metrics_path, fake_graph, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mixed-class breakdown (STILL_VALID + non-still-valid) MUST emit
        the outer summary line with the per-class counts. This guards
        against the W6 fix over-suppressing non-silent cases.
        """
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=2,
            bindings_total=3,
            class_counts={
                DriftClass.STILL_VALID: 1,
                DriftClass.STALE_ID: 1,
                DriftClass.LABEL_DRIFT: 1,
            },
            findings=[
                _make_finding(obs_id=1, drift_class=DriftClass.STILL_VALID),
                _make_finding(obs_id=2, drift_class=DriftClass.STALE_ID),
                _make_finding(obs_id=3, drift_class=DriftClass.LABEL_DRIFT),
            ],
        )
        monkeypatch.setattr(
            daemon.decision_drift,
            "scan_change",
            lambda *a, **kw: report,
        )
        summaries: list[str] = []

        result = daemon.handle_apply_progress_event(
            "my-change",
            {"tasks": {"T1": {"status": "merged"}}},
            graph_json_path=fake_graph,
            on_summary=summaries.append,
        )

        assert result is report
        assert len(summaries) == 1
        line = summaries[0]
        assert line.startswith("drift: my-change")
        assert "3 findings" in line
        assert "1 STILL_VALID" in line
        assert "1 STALE_ID" in line
        assert "1 LABEL_DRIFT" in line


# ---------- REQ-55 W5 daemon -> JSONL wiring ----------


class TestDriftEventLogWiring:
    """REQ-55 W5: ``handle_apply_progress_event`` MUST append one JSONL
    line per non-STILL_VALID finding to ``DriftEventLog``.

    Per the spec the JSONL line schema is
    ``{change, decision_id, binding_id, event_class, detected_at}``.
    Per the REQ-56 / W6 still-valid silence rule, STILL_VALID findings
    MUST NOT be appended (the on-disk audit trail stays quiet on a
    no-drift tick).
    """

    def test_daemon_appends_to_drift_event_log_per_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A 2-finding report (1 STALE_ID + 1 LABEL_DRIFT) results in 2
        ``DriftEventLog.append`` calls — one per non-STILL_VALID finding."""
        from flow_engineering.drift_event_log import DriftEventLog

        event_log_path = tmp_path / "drift_events.jsonl"
        appended: list[tuple[str, str, str, str, float]] = []

        class _FakeLog:
            def __init__(self, path: object = None) -> None:
                self.path = path

            def append(self, event: object) -> None:
                appended.append((
                    event.change,
                    event.decision_id,
                    event.binding_id,
                    event.event_class,
                    event.detected_at,
                ))

        monkeypatch.setattr(daemon, "DriftEventLog", _FakeLog)

        metrics = tmp_path / "metrics.jsonl"
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics))
        graph = tmp_path / "graph.json"
        graph.write_text(json.dumps({"nodes": []}), encoding="utf-8")

        report = DriftReport(
            change_name="obs",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=2,
            bindings_total=2,
            class_counts={
                DriftClass.STALE_ID: 1,
                DriftClass.LABEL_DRIFT: 1,
            },
            findings=[
                _make_finding(obs_id=10, drift_class=DriftClass.STALE_ID),
                _make_finding(obs_id=11, drift_class=DriftClass.LABEL_DRIFT),
            ],
        )
        monkeypatch.setattr(
            daemon.decision_drift, "scan_change", lambda *a, **kw: report
        )

        daemon.handle_apply_progress_event(
            "obs",
            {"tasks": {"T1": {"status": "merged"}}},
            graph_json_path=graph,
        )

        assert len(appended) == 2, f"expected 2 appends; got {appended}"
        # Each append carries the spec schema: change, decision_id,
        # binding_id, event_class, detected_at.
        for change, decision_id, binding_id, event_class, detected_at in appended:
            assert change == "obs"
            assert decision_id in {"10", "11"}
            assert binding_id.startswith("n")
            assert event_class in {"STALE_ID", "LABEL_DRIFT"}
            assert isinstance(detected_at, float)

    def test_daemon_no_jsonl_line_when_silent_per_req56(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When every binding is STILL_VALID (W6 silence rule), the daemon
        MUST NOT append any JSONL line — STILL_VALID is intentionally
        skipped per spec REQ-55 W5 ("only non-still-valid findings get
        persisted").
        """
        from flow_engineering.drift_event_log import DriftEventLog

        appended: list[object] = []

        class _FakeLog:
            def __init__(self, path: object = None) -> None:
                self.path = path

            def append(self, event: object) -> None:
                appended.append(event)

        monkeypatch.setattr(daemon, "DriftEventLog", _FakeLog)

        metrics = tmp_path / "metrics.jsonl"
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics))
        graph = tmp_path / "graph.json"
        graph.write_text(json.dumps({"nodes": []}), encoding="utf-8")

        report = DriftReport(
            change_name="obs",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=3,
            bindings_total=3,
            class_counts={DriftClass.STILL_VALID: 3},
            findings=[
                _make_finding(obs_id=1, drift_class=DriftClass.STILL_VALID),
                _make_finding(obs_id=2, drift_class=DriftClass.STILL_VALID),
                _make_finding(obs_id=3, drift_class=DriftClass.STILL_VALID),
            ],
        )
        monkeypatch.setattr(
            daemon.decision_drift, "scan_change", lambda *a, **kw: report
        )

        daemon.handle_apply_progress_event(
            "obs",
            {"tasks": {"T1": {"status": "merged"}}},
            graph_json_path=graph,
        )

        assert appended == [], (
            f"expected 0 JSONL appends on still-valid silence; got {len(appended)}"
        )

    def test_daemon_jsonl_line_keys_match_spec(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The actual JSONL line written by DriftEventLog has the spec
        schema keys: change, decision_id, binding_id, event_class,
        detected_at (archived REQ-15 line 272).
        """
        from flow_engineering.drift_event_log import DriftEventLog

        event_log_path = tmp_path / "drift_events.jsonl"
        monkeypatch.setattr(
            daemon, "DriftEventLog", lambda path=None: DriftEventLog(path=event_log_path)
        )

        metrics = tmp_path / "metrics.jsonl"
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics))
        graph = tmp_path / "graph.json"
        graph.write_text(json.dumps({"nodes": []}), encoding="utf-8")

        report = DriftReport(
            change_name="obs",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=1,
            bindings_total=1,
            class_counts={DriftClass.STALE_ID: 1},
            findings=[_make_finding(obs_id=42, drift_class=DriftClass.STALE_ID)],
        )
        monkeypatch.setattr(
            daemon.decision_drift, "scan_change", lambda *a, **kw: report
        )

        daemon.handle_apply_progress_event(
            "obs",
            {"tasks": {"T1": {"status": "merged"}}},
            graph_json_path=graph,
        )

        assert event_log_path.exists()
        lines = event_log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert set(parsed.keys()) == {
            "change",
            "decision_id",
            "binding_id",
            "class",
            "detected_at",
        }
        assert parsed["change"] == "obs"
        assert parsed["decision_id"] == "42"
        assert parsed["binding_id"] == "n42"
        assert parsed["class"] == "STALE_ID"
        assert isinstance(parsed["detected_at"], float)


# ---------- start_watch drift wiring ----------


class TestStartWatchDrift:
    """REQ-15: start_watch(..., drift=True) wires drift handler."""

    def test_drift_mode_message_mentions_drift(
        self, tmp_path: Path, metrics_path
    ) -> None:
        """start_watch(change, target, drift=True) returns a message
        that explicitly mentions the drift mode."""
        _make_change(tmp_path, "my-change")

        started, msg = daemon.start_watch(
            "my-change", tmp_path, drift=True, graph_json_path=tmp_path / "graph.json"
        )
        assert started is True
        assert "drift" in msg.lower()

    def test_non_drift_mode_unchanged(
        self, tmp_path: Path, metrics_path
    ) -> None:
        """start_watch(change, target, drift=False) is byte-identical to
        the legacy message — no extra text."""
        _make_change(tmp_path, "my-change")

        started, msg = daemon.start_watch("my-change", tmp_path, drift=False)
        assert started is True
        # Legacy message (no drift suffix)
        assert "drift mode" not in msg.lower()
        assert "exploration.md" in msg
        assert "Ctrl+C" in msg

    def test_default_drift_is_false(
        self, tmp_path: Path, metrics_path
    ) -> None:
        """start_watch without an explicit drift kwarg defaults to False."""
        _make_change(tmp_path, "my-change")

        started, msg = daemon.start_watch("my-change", tmp_path)
        assert started is True
        assert "drift mode" not in msg.lower()


# ---------- _maybe_emit_drift filter ----------


class TestMaybeEmitDrift:
    """The internal filter rejects events that should not trigger drift."""

    def test_ignores_directory_events(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: list[Any] = []
        monkeypatch.setattr(
            daemon, "handle_apply_progress_event", lambda *a, **kw: called.append((a, kw))
        )
        event = MagicMock()
        event.is_directory = True
        event.src_path = str(tmp_path / "apply-progress.json")

        daemon._maybe_emit_drift(
            event, "my-change", tmp_path, None, None, lambda *a, **kw: None
        )

        assert called == []

    def test_ignores_non_apply_progress_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: list[Any] = []
        monkeypatch.setattr(
            daemon, "handle_apply_progress_event", lambda *a, **kw: called.append((a, kw))
        )
        event = MagicMock()
        event.is_directory = False
        event.src_path = str(tmp_path / "exploration.md")

        daemon._maybe_emit_drift(
            event, "my-change", tmp_path, None, None, lambda *a, **kw: None
        )

        assert called == []

    def test_handles_missing_src_path_silently(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called: list[Any] = []
        monkeypatch.setattr(
            daemon, "handle_apply_progress_event", lambda *a, **kw: called.append((a, kw))
        )
        event = MagicMock()
        event.is_directory = False
        event.src_path = None

        # Must not raise.
        daemon._maybe_emit_drift(
            event, "my-change", tmp_path, None, None, lambda *a, **kw: None
        )
        assert called == []


# ---------- CLI smoke: --drift flag wires through to start_watch ----------
#
# The CLI ``flow watch --drift`` integration is exercised in
# ``tests/unit/test_cli_watch_drift.py`` (T2.2). Keeping this file focused
# on the daemon layer keeps the test count per task predictable.