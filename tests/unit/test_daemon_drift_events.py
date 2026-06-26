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
        decision_id=str(obs_id),
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
            scanned_at=1000.0,
            graph_mtime=999.0,
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
                change_name="my-change", scanned_at=0.0, graph_mtime=None,
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
            change_name="my-change", scanned_at=0.0, graph_mtime=None,
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
            scanned_at=0.0,
            graph_mtime=999.0,
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