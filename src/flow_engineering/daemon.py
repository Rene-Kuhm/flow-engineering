"""Daemon mode for file watcher.

REQ: `flow watch <change>` starts a long-running observer that
transitions NEW -> EXPLORED when exploration.md is written.

REQ-15 (PR#2): when started with ``drift=True``, the daemon additionally
subscribes to ``apply-progress`` writes inside the change directory. On
every write, the payload is parsed for tasks with ``status: merged``;
when at least one merged task is present, ``decision_drift.scan_change``
runs and a single-line summary is emitted (counters via
``observability.record_drift_summary``). A missing ``graph.json`` emits
an ``unable_to_verify`` line and the watcher stays alive — no exception
escapes the handler.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from flow_engineering import decision_drift, observability
from flow_engineering.drift_event_log import DriftEvent, DriftEventLog
from flow_engineering.state import ChangeStatus, StateMachine
from flow_engineering.watcher import ExplorationFileHandler

if TYPE_CHECKING:
    from flow_engineering.decision_drift import DriftReport
    from flow_engineering.engram_io import EngramBackend


DEFAULT_DRIFT_GRAPH_PATH: Path = Path.home() / ".flow-engineering" / "graph.json"


def _append_drift_events(
    report: DriftReport, *, path: Path | None = None
) -> None:
    """Append one JSONL line per NON-STILL_VALID finding to the drift event log (REQ-55 W5).

    STILL_VALID findings are intentionally skipped — the still-valid silence
    rule (W6 / D4) treats them as "no event of interest", so they do not
    pollute the audit trail. Per design D11, this is best-effort and never
    raises into the caller (``DriftEventLog.append`` swallows OSError).

    v0.8.0 (REQ-56 W8): ``finding.decision_id`` is now ``int`` (was ``str``).
    The wire-format ``DriftEvent`` dataclass still requires ``str`` (legacy
    JSONL consumers expect it), so we coerce via ``str()`` here. Future v1
    follow-up may flip ``DriftEvent.decision_id`` to ``int`` once the wire
    format itself migrates.
    """
    log = DriftEventLog(path=path) if path is not None else DriftEventLog()
    detected_at = time.time()
    for finding in report.findings:
        if finding.drift_class is decision_drift.DriftClass.STILL_VALID:
            continue
        log.append(
            DriftEvent(
                change=report.change_name,
                decision_id=str(finding.decision_id),
                binding_id=finding.binding.id,
                event_class=finding.drift_class.value,
                detected_at=detected_at,
            )
        )


def handle_apply_progress_event(
    change: str,
    apply_progress: dict[str, Any],
    *,
    graph_json_path: Path | None = None,
    backend: EngramBackend | None = None,
    on_summary: Callable[[str], None] | None = None,
) -> DriftReport | None:
    """Process one apply-progress update from the daemon (REQ-15).

    When at least one task has ``status: merged``, runs
    :func:`decision_drift.scan_change` for the change and emits a
    single-line summary via ``on_summary`` (defaults to ``print``).
    Returns the :class:`DriftReport` (or ``None`` when no merged task
    was present in the payload).

    Fail-open: a missing ``graph.json`` emits an ``unable_to_verify``
    line via ``on_summary``; the watcher stays alive (no exception
    escapes this function). Counters are always recorded via
    :func:`observability.record_drift_summary` regardless of outcome.
    """
    if on_summary is None:
        on_summary = print

    tasks = apply_progress.get("tasks", {}) if isinstance(apply_progress, dict) else {}
    merged_present = any(
        isinstance(info, dict) and info.get("status") == "merged"
        for info in tasks.values()
    )
    if not merged_present:
        return None

    graph_path = Path(graph_json_path) if graph_json_path else DEFAULT_DRIFT_GRAPH_PATH

    report = decision_drift.scan_change(
        change,
        graph_json_path=graph_path,
        backend=backend,
    )
    observability.record_drift_summary(report)

    # REQ-55 W5: append one JSONL line per NON-STILL_VALID finding to the
    # drift event log. Best-effort (DriftEventLog swallows OSError). Called
    # AFTER record_drift_summary so the counter emission precedes the
    # audit-trail write.
    _append_drift_events(report)

    if report.graph_unavailable:
        on_summary(
            f"unable_to_verify: graph.json unavailable at {graph_path}"
        )
        return report

    counts = report.class_counts
    parts: list[str] = []
    for cls in (
        decision_drift.DriftClass.STILL_VALID,
        decision_drift.DriftClass.LABEL_DRIFT,
        decision_drift.DriftClass.STALE_LOCATION,
        decision_drift.DriftClass.STALE_ID,
        decision_drift.DriftClass.OBSOLETE,
        decision_drift.DriftClass.CONTRADICTED,
    ):
        n = counts.get(cls, 0)
        if n > 0:
            parts.append(f"{n} {cls.value}")
    total = sum(counts.values())
    # REQ-56 W6 silence rule (design D4): suppress the outer summary line
    # when every binding classifies as STILL_VALID (no drift detected).
    # The JSONL append via ``record_drift_event`` (wired in T2.1) is
    # unconditional so audit trail completeness is preserved.
    non_still_valid_total = total - counts.get(
        decision_drift.DriftClass.STILL_VALID, 0
    )
    if non_still_valid_total > 0:
        on_summary(
            f"drift: {change} {total} findings ({', '.join(parts)})"
        )
    return report


def _maybe_emit_drift(
    event: object,
    change: str,
    change_dir: Path,
    graph_json_path: Path | None,
    backend: EngramBackend | None,
    on_summary: Callable[[str], None] | None,
) -> None:
    """Internal filter: only react to apply-progress file events."""
    if getattr(event, "is_directory", False):
        return
    src_path = getattr(event, "src_path", None)
    if not src_path:
        return
    path = Path(str(src_path))
    if "apply-progress" not in path.name:
        return

    try:
        from flow_engineering.engram_io import EngramClient

        client = EngramClient(change, backend)
        prose = client.load_phase_prose("apply-progress")
        if not prose:
            return
        payload = json.loads(prose)
    except Exception:
        # Fail-open: never let a parse error crash the watcher.
        return

    try:
        handle_apply_progress_event(
            change,
            payload,
            graph_json_path=graph_json_path,
            backend=backend,
            on_summary=on_summary,
        )
    except Exception:
        # Fail-open again — the seam MUST NOT raise into the watchdog loop.
        return


def start_watch(
    change: str,
    target: Path,
    *,
    drift: bool = False,
    graph_json_path: Path | None = None,
    backend: EngramBackend | None = None,
    on_summary: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Start a watchdog observer for the given change.

    Returns (started, message). Blocks until interrupted.

    When ``drift=True`` (REQ-15), an additional handler subscribes to
    ``apply-progress`` writes inside ``change_dir`` and emits a summary
    line per event with at least one ``merged`` task. The summary
    callable defaults to ``print``; tests inject a list-append for
    capture.

    Implementation note: watchdog.Observer is imported lazily to keep
    test imports lightweight.
    """
    change_dir = target / "flow-engineering" / change
    if not (change_dir / "state.json").exists():
        return False, f"No state.json at {change_dir}. Run `flow new {change}` first."
    sm = StateMachine.load(change_dir)
    if sm.status != ChangeStatus.NEW:
        return True, (
            f"Change '{change}' is already in status {sm.status.value}. "
            f"Watcher is a no-op (no NEW -> EXPLORED transition needed)."
        )

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as e:
        return False, f"watchdog not installed: {e}"

    handler = ExplorationFileHandler(change_dir)

    class _HandlerAdapter(FileSystemEventHandler):
        def on_modified(self, event: object) -> None:
            handler.on_modified(event)
            if drift:
                _maybe_emit_drift(
                    event, change, change_dir, graph_json_path, backend, on_summary
                )

        def on_created(self, event: object) -> None:
            handler.on_modified(event)
            if drift:
                _maybe_emit_drift(
                    event, change, change_dir, graph_json_path, backend, on_summary
                )

    observer = Observer()
    observer.schedule(_HandlerAdapter(), str(change_dir), recursive=False)
    observer.start()
    suffix = (
        " (drift mode: watching apply-progress for merged tasks)"
        if drift
        else ""
    )
    return True, (
        f"Watching {change_dir}/explore/exploration.md for changes. "
        f"Press Ctrl+C to stop.{suffix}"
    )


def stop_watch(observer: object | None = None) -> None:
    """Stop a running observer (for tests)."""
    if observer is not None and hasattr(observer, "stop"):
        observer.stop()
        observer.join()  # type: ignore[attr-defined]
