"""Unit tests for watcher.py."""

from __future__ import annotations

from pathlib import Path

from flow_engineering.state import ChangeStatus, StateMachine
from flow_engineering.watcher import (
    ExplorationFileHandler,
    make_exploration_watcher,
)


class TestExplorationWatcher:
    def test_transitions_new_to_explored_on_exploration_write(self, tmp_path: Path) -> None:
        change_dir = tmp_path / "change"
        StateMachine.create("change", change_dir)
        callback = make_exploration_watcher(change_dir)
        explore = change_dir / "explore"
        explore.mkdir()
        explore_md = explore / "exploration.md"
        explore_md.write_text("# exploration content")
        callback(explore_md)
        sm = StateMachine.load(change_dir)
        assert sm.status == ChangeStatus.EXPLORED

    def test_ignores_other_files(self, tmp_path: Path) -> None:
        change_dir = tmp_path / "change"
        StateMachine.create("change", change_dir)
        callback = make_exploration_watcher(change_dir)
        other = change_dir / "other.md"
        other.write_text("not exploration")
        callback(other)
        sm = StateMachine.load(change_dir)
        assert sm.status == ChangeStatus.NEW  # unchanged

    def test_does_not_double_transition(self, tmp_path: Path) -> None:
        change_dir = tmp_path / "change"
        StateMachine.create("change", change_dir)
        callback = make_exploration_watcher(change_dir)
        explore = change_dir / "explore"
        explore.mkdir()
        md = explore / "exploration.md"
        md.write_text("first")
        callback(md)  # NEW -> EXPLORED
        callback(md)  # already EXPLORED, should stay
        sm = StateMachine.load(change_dir)
        assert sm.status == ChangeStatus.EXPLORED

    def test_calls_user_callback(self, tmp_path: Path) -> None:
        change_dir = tmp_path / "change"
        StateMachine.create("change", change_dir)
        seen: list[Path] = []
        callback = make_exploration_watcher(change_dir, on_write=lambda p: seen.append(p))
        explore = change_dir / "explore"
        explore.mkdir()
        md = explore / "exploration.md"
        md.write_text("x")
        callback(md)
        assert seen == [md]


class TestExplorationFileHandler:
    def test_on_modified_routes_to_callback(self, tmp_path: Path) -> None:
        change_dir = tmp_path / "change"
        StateMachine.create("change", change_dir)
        handler = ExplorationFileHandler(change_dir)
        explore = change_dir / "explore"
        explore.mkdir()
        md = explore / "exploration.md"
        md.write_text("x")
        # Fake watchdog event
        event = type("E", (), {"is_directory": False, "src_path": str(md)})()
        handler.on_modified(event)
        sm = StateMachine.load(change_dir)
        assert sm.status == ChangeStatus.EXPLORED

    def test_on_modified_ignores_directories(self, tmp_path: Path) -> None:
        change_dir = tmp_path / "change"
        StateMachine.create("change", change_dir)
        handler = ExplorationFileHandler(change_dir)
        event = type("E", (), {"is_directory": True, "src_path": str(change_dir)})()
        handler.on_modified(event)  # should not raise
