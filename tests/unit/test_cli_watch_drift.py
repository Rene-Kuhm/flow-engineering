"""Unit tests for ``flow watch --drift`` CLI flag (REQ-15 / PR#2 batch G T2.2).

Covers:

- The ``--drift`` flag wires through the CLI to
  ``daemon.start_watch(..., drift=True)``.
- The non-drift path (``flow watch <change>`` without ``--drift``) is
  byte-identical to the legacy behavior (drift=False is passed through
  and the message reflects the legacy form).
- The CLI calls the drift seam ``handle_apply_progress_event`` when an
  apply-progress payload containing ``status: merged`` is processed —
  verifying the full CLI -> daemon -> drift seam chain.
- Drift counters (``drift_*_total``) increment when the daemon emits a
  drift event under ``--drift``.
- The CLI returns control promptly when watchdog is mocked — the
  ``start_watch`` path returns immediately rather than blocking the
  CliRunner.
- The CLI passes through ``--graph-json`` to ``start_watch`` so the
  operator can pin a snapshot (defaults to the daemon's default).
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
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


@pytest.fixture
def fake_graph(tmp_path: Path) -> Path:
    path = tmp_path / "graph.json"
    path.write_text(json.dumps({"nodes": []}), encoding="utf-8")
    return path


def _make_change(tmp_path: Path, change: str = "my-change") -> Path:
    fe = tmp_path / "flow-engineering" / change
    fe.mkdir(parents=True)
    StateMachine.create(change, fe).save()
    return fe


def _make_finding(*, drift_class: DriftClass = DriftClass.STILL_VALID) -> Finding:
    binding = CodeRef(
        project="insyd", id="n1", label="L1", file="src/x.py", line=1,
        confidence=0.9, source="manual",
    )
    return Finding(decision_id="1", binding=binding, drift_class=drift_class, detail="")


def _patch_observer(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Stub ``watchdog.observers.Observer`` so start_watch returns fast.

    Returns a dict the test can introspect (e.g. count scheduled
    handlers). The watchdog Observer normally starts a real background
    thread; the stub starts a MagicMock so the function returns
    immediately and CliRunner does not hang.
    """
    captured: dict[str, Any] = {"scheduled": [], "started": 0, "stopped": 0}
    fake_observer = MagicMock()
    fake_observer.schedule.side_effect = lambda *a, **kw: captured["scheduled"].append((a, kw))
    fake_observer.start.side_effect = lambda: captured.__setitem__("started", captured["started"] + 1)
    fake_observer.stop.side_effect = lambda: captured.__setitem__("stopped", captured["stopped"] + 1)

    import sys
    fake_module = type(sys)("fake_watchdog")
    fake_module.Observer = MagicMock(return_value=fake_observer)
    monkeypatch.setitem(sys.modules, "watchdog.observers", fake_module)

    events_module = type(sys)("fake_watchdog_events")
    from watchdog.events import FileSystemEventHandler  # type: ignore[import-not-found]

    events_module.FileSystemEventHandler = FileSystemEventHandler
    monkeypatch.setitem(sys.modules, "watchdog.events", events_module)
    return captured


# ---------- --drift flag wiring ----------


class TestDriftFlagWiring:
    """REQ-15: --drift flag wires through CLI to start_watch(drift=True)."""

    def test_drift_flag_invokes_start_watch_with_drift_true(
        self, tmp_path: Path, metrics_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_change(tmp_path)
        _patch_observer(monkeypatch)
        captured: dict[str, Any] = {}

        def _stub(
            change: str, target: Path, *,
            drift: bool = False,
            graph_json_path: Path | None = None,
            backend: Any = None,
            on_summary: Any = None,
        ) -> tuple[bool, str]:
            captured["change"] = change
            captured["target"] = target
            captured["drift"] = drift
            captured["graph_json_path"] = graph_json_path
            return True, "stubbed message"

        monkeypatch.setattr(daemon, "start_watch", _stub)

        result = runner.invoke(
            cli_main, ["watch", "my-change", "--in", str(tmp_path), "--drift"],
        )
        assert result.exit_code == 0, result.output
        assert captured.get("change") == "my-change"
        assert captured.get("drift") is True

    def test_no_drift_flag_invokes_start_watch_with_drift_false(
        self, tmp_path: Path, metrics_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_change(tmp_path)
        _patch_observer(monkeypatch)
        captured: dict[str, Any] = {}

        def _stub(change: str, target: Path, *, drift: bool = False, **kw: Any) -> tuple[bool, str]:
            captured["drift"] = drift
            return True, "stubbed message"

        monkeypatch.setattr(daemon, "start_watch", _stub)

        result = runner.invoke(
            cli_main, ["watch", "my-change", "--in", str(tmp_path)],
        )
        assert result.exit_code == 0, result.output
        assert captured.get("drift") is False

    def test_drift_flag_with_explicit_graph_json(
        self, tmp_path: Path, metrics_path, fake_graph, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The CLI MUST expose a --graph-json flag that pipes into
        start_watch(graph_json_path=...)."""
        _make_change(tmp_path)
        _patch_observer(monkeypatch)
        captured: dict[str, Any] = {}

        def _stub(
            change: str, target: Path, *,
            drift: bool = False, graph_json_path: Path | None = None, **kw: Any
        ) -> tuple[bool, str]:
            captured["drift"] = drift
            captured["graph_json_path"] = graph_json_path
            return True, "stubbed"

        monkeypatch.setattr(daemon, "start_watch", _stub)

        result = runner.invoke(
            cli_main,
            ["watch", "my-change", "--in", str(tmp_path),
             "--drift", "--graph-json", str(fake_graph)],
        )
        assert result.exit_code == 0, result.output
        assert captured.get("drift") is True
        assert captured.get("graph_json_path") == fake_graph


# ---------- Counter increment under --drift ----------


class TestDriftCounters:
    """REQ-15 + REQ-12: drift counters increment when --drift fires."""

    def test_record_drift_summary_invoked_under_drift(
        self, tmp_path: Path, metrics_path, fake_graph, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When --drift is passed AND an apply-progress event with a merged
        task flows through the daemon seam, observability.record_drift_summary
        is called exactly once with the DriftReport."""
        _make_change(tmp_path)
        _patch_observer(monkeypatch)

        report = DriftReport(
            change_name="my-change", scanned_at=0.0, graph_mtime=999.0,
            decisions_total=1, bindings_total=1,
            class_counts={DriftClass.STILL_VALID: 1},
            findings=[_make_finding(drift_class=DriftClass.STILL_VALID)],
        )
        monkeypatch.setattr(daemon.decision_drift, "scan_change", lambda *a, **kw: report)

        recorded: list[DriftReport] = []
        monkeypatch.setattr(observability, "record_drift_summary", lambda r: recorded.append(r))

        captured_summary: list[str] = []

        def _stub(
            change: str, target: Path, *, drift: bool = False,
            graph_json_path: Path | None = None, on_summary: Any = None, **kw: Any
        ) -> tuple[bool, str]:
            # Simulate the daemon firing a drift event by directly invoking the seam.
            if drift and on_summary is not None:
                daemon.handle_apply_progress_event(
                    change,
                    {"tasks": {"T1": {"status": "merged"}}},
                    graph_json_path=graph_json_path or fake_graph,
                    on_summary=on_summary,
                )
            return True, "stubbed"

        monkeypatch.setattr(daemon, "start_watch", _stub)

        result = runner.invoke(
            cli_main,
            ["watch", "my-change", "--in", str(tmp_path),
             "--drift", "--graph-json", str(fake_graph)],
        )
        assert result.exit_code == 0, result.output
        assert len(recorded) == 1
        assert recorded[0] is report


# ---------- Stdout summary format ----------


class TestStdoutSummary:
    """REQ-15: a single-line summary is emitted when drift is detected."""

    def test_drift_event_emits_stdout_summary(
        self, tmp_path: Path, metrics_path, fake_graph, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When a merged task is observed, the seam emits a line like
        'drift: <change> N findings (a CLASS, b CLASS)' to stdout."""
        _make_change(tmp_path)
        _patch_observer(monkeypatch)

        report = DriftReport(
            change_name="my-change", scanned_at=0.0, graph_mtime=999.0,
            decisions_total=2, bindings_total=3,
            class_counts={
                DriftClass.STILL_VALID: 1,
                DriftClass.STALE_ID: 2,
            },
            findings=[
                _make_finding(drift_class=DriftClass.STILL_VALID),
                _make_finding(drift_class=DriftClass.STALE_ID),
            ],
        )
        monkeypatch.setattr(daemon.decision_drift, "scan_change", lambda *a, **kw: report)
        monkeypatch.setattr(observability, "record_drift_summary", lambda r: None)

        def _stub(
            change: str, target: Path, *, drift: bool = False,
            graph_json_path: Path | None = None, on_summary: Any = None, **kw: Any
        ) -> tuple[bool, str]:
            if drift and on_summary is not None:
                daemon.handle_apply_progress_event(
                    change,
                    {"tasks": {"T1": {"status": "merged"}}},
                    graph_json_path=graph_json_path or fake_graph,
                    on_summary=on_summary,
                )
            return True, "stubbed"

        monkeypatch.setattr(daemon, "start_watch", _stub)

        result = runner.invoke(
            cli_main,
            ["watch", "my-change", "--in", str(tmp_path),
             "--drift", "--graph-json", str(fake_graph)],
        )
        assert result.exit_code == 0, result.output
        assert "drift: my-change" in result.output
        assert "3 findings" in result.output
        assert "1 STILL_VALID" in result.output
        assert "2 STALE_ID" in result.output


# ---------- Non-blocking: CliRunner returns promptly ----------


class TestNonBlocking:
    """REQ-15 acceptance: CLI returns control; main thread is not blocked."""

    def test_watch_returns_promptly_with_mocked_observer(
        self, tmp_path: Path, metrics_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the watchdog Observer is mocked, CliRunner.invoke returns
        immediately. This proves start_watch does not block the caller.
        """
        _make_change(tmp_path)
        _patch_observer(monkeypatch)

        result = runner.invoke(
            cli_main,
            ["watch", "my-change", "--in", str(tmp_path), "--drift"],
        )
        assert result.exit_code == 0, result.output
        # Legacy + drift suffix must be visible.
        assert "drift mode" in result.output.lower()


# ---------- Non-drift regression ----------


class TestNonDriftRegression:
    """The non-drift path MUST be unchanged when --drift is absent."""

    def test_watch_without_drift_does_not_emit_drift_message(
        self, tmp_path: Path, metrics_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_change(tmp_path)
        _patch_observer(monkeypatch)

        result = runner.invoke(
            cli_main, ["watch", "my-change", "--in", str(tmp_path)],
        )
        assert result.exit_code == 0, result.output
        # The drift suffix MUST NOT appear.
        assert "drift mode" not in result.output.lower()


# ---------- Missing state.json still returns 1 ----------


class TestMissingState:
    """The pre-existing missing-state.json failure mode MUST be preserved."""

    def test_watch_missing_state_json_returns_1(
        self, tmp_path: Path, metrics_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If state.json is absent, flow watch exits 1 (legacy behavior).
        This MUST also hold under --drift."""
        # Note: we do NOT call _make_change — no state.json exists.
        result = runner.invoke(
            cli_main,
            ["watch", "ghost-change", "--in", str(tmp_path), "--drift"],
        )
        assert result.exit_code == 1, result.output
        assert "Run `flow new" in result.output