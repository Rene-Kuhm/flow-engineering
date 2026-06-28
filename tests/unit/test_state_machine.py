"""Unit tests for state.py — the change state machine.

REQ-3: Forward transitions, skip rejection, retry loop, persistence.
"""

from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flow_engineering.state import (
    ChangeStatus,
    InvalidTransitionError,
    StateMachine,
    Transition,
)


class TestChangeStatus:
    def test_all_statuses_defined(self) -> None:
        expected = {
            "NEW",
            "EXPLORED",
            "PROPOSED",
            "DESIGNED",
            "SPECIFIED",
            "TASKED",
            "APPLYING",
            "VERIFYING",
            "ARCHIVING",
            "DONE",
        }
        actual = {s.name for s in ChangeStatus}
        assert actual == expected


class TestStateMachineForward:
    def test_new_to_explored(self, tmp_path: Path) -> None:
        sm = StateMachine.create("my-change", tmp_path)
        sm.transition(ChangeStatus.EXPLORED, artifact="explore/exploration.md")
        assert sm.status == ChangeStatus.EXPLORED
        assert sm.transitions[-1].from_status == ChangeStatus.NEW
        assert sm.transitions[-1].to_status == ChangeStatus.EXPLORED
        assert sm.transitions[-1].artifact == "explore/exploration.md"

    def test_full_happy_path(self, tmp_path: Path) -> None:
        sm = StateMachine.create("my-change", tmp_path)
        path = [
            (ChangeStatus.EXPLORED, "explore/exploration.md"),
            (ChangeStatus.PROPOSED, "propose/proposal.md"),
            (ChangeStatus.DESIGNED, "design/design.md"),
            (ChangeStatus.SPECIFIED, "spec/spec.md"),
            (ChangeStatus.TASKED, "tasks/tasks.md"),
            (ChangeStatus.APPLYING, None),
            (ChangeStatus.VERIFYING, None),
            (ChangeStatus.ARCHIVING, None),
            (ChangeStatus.DONE, None),
        ]
        for to_status, artifact in path:
            sm.transition(to_status, artifact=artifact)
        assert sm.status == ChangeStatus.DONE
        assert len(sm.transitions) == len(path)


class TestStateMachineRejects:
    def test_skip_transition_rejected(self, tmp_path: Path) -> None:
        sm = StateMachine.create("my-change", tmp_path)
        with pytest.raises(InvalidTransitionError) as exc:
            sm.transition(ChangeStatus.PROPOSED, artifact="propose/proposal.md")
        assert "Cannot skip" in str(exc.value)
        assert "EXPLORED" in str(exc.value)
        assert sm.status == ChangeStatus.NEW

    def test_backward_transition_rejected(self, tmp_path: Path) -> None:
        sm = StateMachine.create("my-change", tmp_path)
        sm.transition(ChangeStatus.EXPLORED)
        with pytest.raises(InvalidTransitionError):
            sm.transition(ChangeStatus.NEW)

    def test_invalid_same_status_rejected(self, tmp_path: Path) -> None:
        sm = StateMachine.create("my-change", tmp_path)
        with pytest.raises(InvalidTransitionError):
            sm.transition(ChangeStatus.NEW)


class TestStateMachineRetry:
    def test_retry_loop_in_applying(self, tmp_path: Path) -> None:
        sm = StateMachine.create("my-change", tmp_path)
        sm.transition(ChangeStatus.EXPLORED)
        sm.transition(ChangeStatus.PROPOSED)
        sm.transition(ChangeStatus.DESIGNED)
        sm.transition(ChangeStatus.SPECIFIED)
        sm.transition(ChangeStatus.TASKED)
        sm.transition(ChangeStatus.APPLYING)
        # Retry: stay in APPLYING but annotate
        sm.transition(ChangeStatus.APPLYING, retry=True, reason="transient timeout")
        assert sm.status == ChangeStatus.APPLYING
        assert sm.transitions[-1].retry is True
        assert sm.transitions[-1].reason == "transient timeout"

    def test_max_retries_exceeded(self, tmp_path: Path) -> None:
        sm = StateMachine.create("my-change", tmp_path)
        for _ in range(6):
            with contextlib.suppress(InvalidTransitionError):
                sm.transition(ChangeStatus.EXPLORED)
            sm = StateMachine.create("my-change", tmp_path)
        sm.transition(ChangeStatus.EXPLORED)
        sm.transition(ChangeStatus.PROPOSED)
        sm.transition(ChangeStatus.DESIGNED)
        sm.transition(ChangeStatus.SPECIFIED)
        sm.transition(ChangeStatus.TASKED)
        sm.transition(ChangeStatus.APPLYING)
        for _ in range(2):
            sm.transition(ChangeStatus.APPLYING, retry=True)
        with pytest.raises(InvalidTransitionError) as exc:
            sm.transition(ChangeStatus.APPLYING, retry=True)
        assert "max retries" in str(exc.value).lower()


class TestStateMachinePersistence:
    def test_persists_to_json(self, tmp_path: Path) -> None:
        sm = StateMachine.create("my-change", tmp_path)
        sm.transition(ChangeStatus.EXPLORED)
        sm.save()
        state_file = tmp_path / "state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["change"] == "my-change"
        assert data["status"] == "EXPLORED"
        assert len(data["transitions"]) == 1

    def test_loads_from_json(self, tmp_path: Path) -> None:
        StateMachine.create("my-change", tmp_path).save()
        sm2 = StateMachine.load(tmp_path)
        assert sm2.status == ChangeStatus.NEW
        assert sm2.change == "my-change"

    def test_creates_directory_if_missing(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "nested" / "my-change"
        StateMachine.create("my-change", new_dir)
        assert (new_dir / "state.json").exists()


class TestDriftBaseline:
    def test_records_baseline(self, tmp_path: Path) -> None:
        sm = StateMachine.create("my-change", tmp_path)
        sm.transition(ChangeStatus.EXPLORED)
        sm.set_drift_baseline(
            tasks_md_hash="abc123",
            apply_progress_topic="sdd/my-change/apply-progress",
            graph_node_count=5043,
        )
        sm.save()
        loaded = StateMachine.load(tmp_path)
        assert loaded.drift_baseline["tasks_md_hash"] == "abc123"
        assert loaded.drift_baseline["apply_progress_topic"] == "sdd/my-change/apply-progress"
        assert loaded.drift_baseline["graph_node_count"] == 5043


class TestCrossProject:
    def test_cross_project_metadata(self, tmp_path: Path) -> None:
        sm = StateMachine.create(
            "my-change",
            tmp_path,
            cross_projects=["mockup", "tecnodespegue-landing"],
        )
        sm.save()
        loaded = StateMachine.load(tmp_path)
        assert loaded.cross_projects == ["mockup", "tecnodespegue-landing"]


class TestTransitionRecord:
    def test_transition_has_timestamp(self) -> None:
        t = Transition(
            from_status=ChangeStatus.NEW,
            to_status=ChangeStatus.EXPLORED,
            at=datetime.now(UTC),
        )
        assert t.at.tzinfo is not None
