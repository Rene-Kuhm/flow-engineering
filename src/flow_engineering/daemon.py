"""Daemon mode for file watcher.

REQ: `flow watch <change>` starts a long-running observer that
transitions NEW -> EXPLORED when exploration.md is written.
"""
from __future__ import annotations

from pathlib import Path

from flow_engineering.state import ChangeStatus, StateMachine
from flow_engineering.watcher import ExplorationFileHandler


def start_watch(change: str, target: Path) -> tuple[bool, str]:
    """Start a watchdog observer for the given change.

    Returns (started, message). Blocks until interrupted.

    Implementation note: watchdog.Obsserver is imported lazily to keep
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

        def on_created(self, event: object) -> None:
            handler.on_modified(event)

    observer = Observer()
    observer.schedule(_HandlerAdapter(), str(change_dir), recursive=False)
    observer.start()
    return True, (
        f"Watching {change_dir}/explore/exploration.md for changes. "
        f"Press Ctrl+C to stop."
    )


def stop_watch(observer: object | None = None) -> None:
    """Stop a running observer (for tests)."""
    if observer is not None and hasattr(observer, "stop"):
        observer.stop()
        observer.join()  # type: ignore[attr-defined]
