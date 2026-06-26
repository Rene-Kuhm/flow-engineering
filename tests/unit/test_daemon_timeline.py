"""Unit tests for daemon.py and timeline.py."""
from __future__ import annotations

from pathlib import Path

from flow_engineering.daemon import start_watch, stop_watch
from flow_engineering.state import ChangeStatus, StateMachine
from flow_engineering.timeline import (
    ProjectTimeline,
    TimelineEvent,
    build_timeline,
    render_timeline,
)


def _make_change(tmp_path: Path, change: str, status: ChangeStatus) -> Path:
    fe = tmp_path / "flow-engineering" / change
    fe.mkdir(parents=True)
    sm = StateMachine.create(change, fe)
    full_path = [
        ChangeStatus.EXPLORED, ChangeStatus.PROPOSED, ChangeStatus.DESIGNED,
        ChangeStatus.SPECIFIED, ChangeStatus.TASKED,
        ChangeStatus.APPLYING, ChangeStatus.VERIFYING,
        ChangeStatus.ARCHIVING, ChangeStatus.DONE,
    ]
    for to in full_path:
        sm.transition(to)
        if to == status:
            break
    sm.save()
    return fe


class TestStartWatch:
    def test_missing_state_returns_false(self, tmp_path: Path) -> None:
        started, msg = start_watch("nonexistent", tmp_path)
        assert started is False
        assert "Run `flow new" in msg

    def test_non_new_status_returns_true_noop(self, tmp_path: Path) -> None:
        _make_change(tmp_path, "x", ChangeStatus.TASKED)
        started, msg = start_watch("x", tmp_path)
        assert started is True
        assert "no-op" in msg


class TestBuildTimeline:
    def test_empty_project(self, tmp_path: Path) -> None:
        timeline = build_timeline([])
        assert timeline.total_events == 0

    def test_single_change(self, tmp_path: Path) -> None:
        _make_change(tmp_path, "alpha", ChangeStatus.DESIGNED)
        timeline = build_timeline([tmp_path / "flow-engineering" / "alpha"])
        assert len(timeline.changes) == 1
        c = timeline.changes[0]
        assert c.change == "alpha"
        assert c.status == "DESIGNED"
        # EXPLORED -> PROPOSED -> DESIGNED = 3 events
        assert len(c.events) == 3

    def test_skips_invalid_dirs(self, tmp_path: Path) -> None:
        bad = tmp_path / "no-state-here"
        bad.mkdir()
        timeline = build_timeline([bad])
        assert len(timeline.changes) == 0


class TestRenderTimeline:
    def test_render_empty(self) -> None:
        output = render_timeline(ProjectTimeline(changes=[]))
        assert "no events" in output.lower() or "Memory Timeline" in output

    def test_render_single_change(self, tmp_path: Path) -> None:
        _make_change(tmp_path, "alpha", ChangeStatus.PROPOSED)
        timeline = build_timeline([tmp_path / "flow-engineering" / "alpha"])
        output = render_timeline(timeline)
        assert "alpha" in output
        assert "PROPOSED" in output
        assert "EXPLORED" in output
