"""File watcher for CONTEXT -> SPEC transition.

REQ-3 hook model: detect when explore/exploration.md is written, trigger transition.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from flow_engineering.state import ChangeStatus, StateMachine


def make_exploration_watcher(
    change_dir: Path,
    on_write: Callable[[Path], None] | None = None,
) -> Callable[[Path], None]:
    """Return a callback that detects exploration.md writes and transitions state.

    The callback can be passed to watchdog's FileSystemEventHandler.on_modified.
    """
    state_path = change_dir / "state.json"

    def _on_change(file_path: Path) -> None:
        # Normalize: only fire for exploration.md inside explore/
        try:
            file_path = Path(file_path).resolve()
        except (OSError, ValueError):
            return
        if file_path.name != "exploration.md":
            return
        if "explore" not in file_path.parts:
            return
        try:
            sm = StateMachine.load(change_dir)
        except FileNotFoundError:
            return
        if sm.status == ChangeStatus.NEW:
            sm.transition(ChangeStatus.EXPLORED, artifact="explore/exploration.md")
            sm.save()
        if on_write is not None:
            on_write(file_path)

    return _on_change


class ExplorationFileHandler:
    """Watchdog handler for exploration.md writes.

    Use with:
        observer = Observer()
        observer.schedule(ExplorationFileHandler(change_dir), str(change_dir), recursive=False)
    """

    def __init__(self, change_dir: Path) -> None:
        self.change_dir = change_dir
        self._callback = make_exploration_watcher(change_dir)

    def on_modified(self, event: object) -> None:
        # Avoid importing watchdog types at module level for testability
        if getattr(event, "is_directory", False):
            return
        src_path = getattr(event, "src_path", None)
        if src_path:
            self._callback(Path(src_path))

    def on_created(self, event: object) -> None:
        self.on_modified(event)
