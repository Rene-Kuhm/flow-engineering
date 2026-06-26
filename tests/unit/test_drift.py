"""Unit tests for drift.py — 3-signal drift detection.

REQ-4: spec drift, test failure classification, memory mismatch.
"""

from __future__ import annotations

from pathlib import Path

from flow_engineering.drift import (
    DriftReport,
    FailureClass,
    check_spec_drift,
    classify_test_failures,
    tasks_md_hash,
)


class TestFailureClassification:
    def test_structural_import_error(self) -> None:
        output = "ImportError: cannot import name 'foo' from 'bar'"
        assert classify_test_failures(output) == FailureClass.STRUCTURAL

    def test_structural_syntax_error(self) -> None:
        output = "SyntaxError: invalid syntax at line 5"
        assert classify_test_failures(output) == FailureClass.STRUCTURAL

    def test_structural_name_error(self) -> None:
        output = "NameError: name 'undefined_var' is not defined"
        assert classify_test_failures(output) == FailureClass.STRUCTURAL

    def test_transient_timeout(self) -> None:
        output = "TimeoutError: test exceeded 30s"
        assert classify_test_failures(output) == FailureClass.TRANSIENT

    def test_transient_connection_error(self) -> None:
        output = "ConnectionRefusedError: [Errno 111]"
        assert classify_test_failures(output) == FailureClass.TRANSIENT

    def test_contract_assertion_error(self) -> None:
        output = "AssertionError: expected 200, got 404"
        assert classify_test_failures(output) == FailureClass.CONTRACT

    def test_contract_value_error(self) -> None:
        output = "ValueError: invalid input"
        assert classify_test_failures(output) == FailureClass.CONTRACT

    def test_unknown_when_no_match(self) -> None:
        output = "Some weird error that doesn't match any pattern"
        assert classify_test_failures(output) == FailureClass.UNKNOWN

    def test_structural_priority_over_transient(self) -> None:
        # Mixed output — structural should win
        output = "ImportError: cannot import x\nTimeoutError: timed out"
        assert classify_test_failures(output) == FailureClass.STRUCTURAL

    def test_contract_priority_over_transient(self) -> None:
        # Mixed output — contract should win over transient
        output = "AssertionError: expected 200\nTimeoutError: timed out"
        assert classify_test_failures(output) == FailureClass.CONTRACT


class TestSpecDrift:
    def test_no_drift_when_md_empty(self, tmp_path: Path) -> None:
        md = tmp_path / "tasks.md"
        assert check_spec_drift(md, None) is False

    def test_no_drift_when_no_progress(self, tmp_path: Path) -> None:
        md = tmp_path / "tasks.md"
        md.write_text("- [x] **T1.1** done")
        assert check_spec_drift(md, None) is False

    def test_drift_when_md_checked_but_progress_not(self, tmp_path: Path) -> None:
        md = tmp_path / "tasks.md"
        md.write_text("- [x] **T1.1** done\n")
        progress = '{"tasks": {"T1.1": {"status": "in_progress"}}}'
        assert check_spec_drift(md, progress) is True

    def test_no_drift_when_consistent(self, tmp_path: Path) -> None:
        md = tmp_path / "tasks.md"
        md.write_text("- [x] **T1.1** done\n")
        progress = '{"tasks": {"T1.1": {"status": "completed"}}}'
        assert check_spec_drift(md, progress) is False


class TestTasksMdHash:
    def test_hash_empty_string_for_missing(self, tmp_path: Path) -> None:
        md = tmp_path / "tasks.md"
        assert tasks_md_hash(md) == ""

    def test_hash_consistent(self, tmp_path: Path) -> None:
        md = tmp_path / "tasks.md"
        md.write_text("content")
        h1 = tasks_md_hash(md)
        h2 = tasks_md_hash(md)
        assert h1 == h2
        assert len(h1) == 16

    def test_hash_changes_with_content(self, tmp_path: Path) -> None:
        md = tmp_path / "tasks.md"
        md.write_text("content A")
        h1 = tasks_md_hash(md)
        md.write_text("content B")
        h2 = tasks_md_hash(md)
        assert h1 != h2


class TestDriftReport:
    def test_no_drift_clean_state(self) -> None:
        report = DriftReport(
            spec_drift=False,
            test_failure=FailureClass.UNKNOWN,
            memory_mismatch=False,
        )
        assert not report.has_drift
        assert report.action() == "continue"

    def test_spec_drift_triggers_halt(self) -> None:
        report = DriftReport(
            spec_drift=True,
            test_failure=FailureClass.UNKNOWN,
            memory_mismatch=False,
        )
        assert report.has_drift
        assert report.action() == "halt_apply"

    def test_structural_failure_escalates(self) -> None:
        report = DriftReport(
            spec_drift=False,
            test_failure=FailureClass.STRUCTURAL,
            memory_mismatch=False,
        )
        assert report.action() == "escalate_structural"

    def test_contract_failure_respecs(self) -> None:
        report = DriftReport(
            spec_drift=False,
            test_failure=FailureClass.CONTRACT,
            memory_mismatch=False,
        )
        assert report.action() == "respec"

    def test_memory_mismatch_reconciles(self) -> None:
        report = DriftReport(
            spec_drift=False,
            test_failure=FailureClass.UNKNOWN,
            memory_mismatch=True,
        )
        assert report.action() == "reconcile_memory"

    def test_transient_failure_alone_does_not_drift(self) -> None:
        # Transient alone is OK because we'll retry
        report = DriftReport(
            spec_drift=False,
            test_failure=FailureClass.TRANSIENT,
            memory_mismatch=False,
        )
        assert not report.has_drift
        assert report.action() == "continue"
