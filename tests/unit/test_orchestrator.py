"""Unit tests for orchestrator.py — apply/verify/archive orchestration."""
from __future__ import annotations

import json
from pathlib import Path

from flow_engineering.drift import FailureClass
from flow_engineering.engram_io import InMemoryBackend
from flow_engineering.orchestrator import (
    apply_change,
    archive_change,
    verify_change,
)
from flow_engineering.state import ChangeStatus, StateMachine


def _make_change_with_tasks(
    target: Path,
    change: str = "test-change",
    status: ChangeStatus = ChangeStatus.TASKED,
) -> Path:
    """Helper: scaffold a change with tasks.md and a state machine at `status`."""
    fe = target / "flow-engineering" / change
    (fe / "tasks").mkdir(parents=True)
    (fe / "tasks" / "tasks.md").write_text(
        "# Tasks\n\n- [ ] **T1.1** do thing one\n- [ ] **T1.2** do thing two\n"
    )
    sm = StateMachine.create(change, fe)
    full_path = [
        ChangeStatus.EXPLORED, ChangeStatus.PROPOSED, ChangeStatus.DESIGNED,
        ChangeStatus.SPECIFIED, ChangeStatus.TASKED,
        ChangeStatus.APPLYING, ChangeStatus.VERIFYING,
        ChangeStatus.ARCHIVING, ChangeStatus.DONE,
    ]
    for to in full_path:
        if to == status:
            sm.transition(to)
            break
        # Walk through forward, stopping at status
        if full_path.index(to) >= full_path.index(status):
            break
        sm.transition(to)
    sm.save()
    return fe


class TestApplyChange:
    def test_apply_from_tasked_transitions_to_applying(self, tmp_path: Path) -> None:
        _make_change_with_tasks(tmp_path, status=ChangeStatus.TASKED)
        result = apply_change("test-change", tmp_path)
        assert result.new_status == ChangeStatus.APPLYING

    def test_apply_from_explored_rejected(self, tmp_path: Path) -> None:
        _make_change_with_tasks(tmp_path, status=ChangeStatus.EXPLORED)
        result = apply_change("test-change", tmp_path)
        assert "Cannot apply" in (result.delegation_error or "")
        assert result.new_status == ChangeStatus.EXPLORED

    def test_apply_finds_next_task(self, tmp_path: Path) -> None:
        _make_change_with_tasks(tmp_path, status=ChangeStatus.TASKED)
        result = apply_change("test-change", tmp_path)
        assert result.task_id == "T1.1"

    def test_apply_saves_progress_to_engram(self, tmp_path: Path) -> None:
        backend = InMemoryBackend()
        _make_change_with_tasks(tmp_path, status=ChangeStatus.TASKED)
        apply_change("test-change", tmp_path, backend=backend)
        progress = json.loads(backend.mem_search(
            query="T1.1", topic_key="sdd/test-change/apply-progress"
        )[0]["content"])
        assert "T1.1" in progress["tasks"]
        assert progress["tasks"]["T1.1"]["status"] == "in_progress"

    def test_apply_skips_completed_tasks(self, tmp_path: Path) -> None:
        backend = InMemoryBackend()
        fe = _make_change_with_tasks(tmp_path, status=ChangeStatus.TASKED)
        # Pre-populate T1.1 as completed
        client = __import__("flow_engineering.engram_io", fromlist=["EngramClient"]).EngramClient(
            "test-change", backend
        )
        client.save_progress("T1.1", "completed")
        result = apply_change("test-change", tmp_path, backend=backend)
        assert result.task_id == "T1.2"


class TestVerifyChange:
    def _make_applying(self, tmp_path: Path) -> Path:
        fe = _make_change_with_tasks(tmp_path, status=ChangeStatus.APPLYING)
        return fe

    def test_verify_clean_output_transitions_to_archiving(self, tmp_path: Path) -> None:
        self._make_applying(tmp_path)
        result = verify_change("test-change", tmp_path, test_output="all 12 tests passed")
        assert result.new_status == ChangeStatus.ARCHIVING
        assert result.action == "archive"

    def test_verify_structural_failure_escalates(self, tmp_path: Path) -> None:
        self._make_applying(tmp_path)
        result = verify_change(
            "test-change", tmp_path,
            test_output="ImportError: cannot import name 'foo'",
        )
        assert result.failure_class == FailureClass.STRUCTURAL
        assert result.action == "escalate_structural"
        assert result.new_status == ChangeStatus.VERIFYING

    def test_verify_contract_failure_respecs(self, tmp_path: Path) -> None:
        self._make_applying(tmp_path)
        result = verify_change(
            "test-change", tmp_path,
            test_output="AssertionError: expected 200, got 404",
        )
        assert result.failure_class == FailureClass.CONTRACT
        assert result.action == "respec"

    def test_verify_transient_first_retry(self, tmp_path: Path) -> None:
        self._make_applying(tmp_path)
        result = verify_change(
            "test-change", tmp_path, test_output="TimeoutError: test exceeded 30s",
        )
        assert result.failure_class == FailureClass.TRANSIENT
        assert result.action == "retry"
        assert result.new_status == ChangeStatus.VERIFYING

    def test_verify_transient_max_retries(self, tmp_path: Path) -> None:
        fe = self._make_applying(tmp_path)
        # Burn through retries: VERIFYING already, then 2 retries
        sm = StateMachine.load(fe)
        sm.transition(ChangeStatus.VERIFYING)  # APPLYING -> VERIFYING
        sm.transition(ChangeStatus.VERIFYING, retry=True)
        sm.transition(ChangeStatus.VERIFYING, retry=True)
        sm.save()
        result = verify_change(
            "test-change", tmp_path, test_output="TimeoutError: timed out",
        )
        assert result.action == "max_retries_exceeded"

    def test_verify_from_new_rejected(self, tmp_path: Path) -> None:
        fe = tmp_path / "flow-engineering" / "x"
        StateMachine.create("x", fe)
        result = verify_change("x", tmp_path, test_output="")
        assert "Cannot verify" in result.message
        assert result.action == "reject"


class TestArchiveChange:
    def _make_archiving(self, tmp_path: Path) -> Path:
        fe = _make_change_with_tasks(tmp_path, status=ChangeStatus.ARCHIVING)
        return fe

    def test_archive_transitions_to_done(self, tmp_path: Path) -> None:
        self._make_archiving(tmp_path)
        result = archive_change("test-change", tmp_path)
        assert result.new_status == ChangeStatus.DONE

    def test_archive_decides_incremental_for_empty_diff(self, tmp_path: Path) -> None:
        self._make_archiving(tmp_path)
        result = archive_change("test-change", tmp_path, diff_text="")
        assert result.graphify_decision is not None
        assert result.graphify_decision.mode == "incremental"

    def test_archive_decides_full_for_structural_diff(self, tmp_path: Path) -> None:
        self._make_archiving(tmp_path)
        result = archive_change(
            "test-change", tmp_path, diff_text="deleted file mode\nfoo.py",
        )
        assert result.graphify_decision is not None
        assert result.graphify_decision.mode == "full"

    def test_archive_persists_summary_to_engram(self, tmp_path: Path) -> None:
        backend = InMemoryBackend()
        self._make_archiving(tmp_path)
        archive_change("test-change", tmp_path, backend=backend)
        results = backend.mem_search(
            query="archived", topic_key="sdd/test-change/archive"
        )
        assert len(results) == 1
        assert "test-change" in results[0]["content"]

    def test_archive_from_applying_rejected(self, tmp_path: Path) -> None:
        _make_change_with_tasks(tmp_path, status=ChangeStatus.APPLYING)
        result = archive_change("test-change", tmp_path)
        assert "Cannot archive" in result.message
