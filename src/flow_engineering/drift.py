"""Drift detection for flow-engineering.

REQ-4: 3-signal drift detection — spec drift, test failure classification, memory mismatch.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FailureClass(str, Enum):
    """Classification of test failures for retry routing."""

    TRANSIENT = "TRANSIENT"  # retry up to 2 times
    STRUCTURAL = "STRUCTURAL"  # escalate immediately, never retry
    CONTRACT = "CONTRACT"  # re-spec, never auto-retry
    UNKNOWN = "UNKNOWN"  # treat as structural (safest)


# Regex patterns for each failure class
_STRUCTURAL_PATTERNS = [
    re.compile(r"ImportError", re.IGNORECASE),
    re.compile(r"ModuleNotFoundError", re.IGNORECASE),
    re.compile(r"SyntaxError", re.IGNORECASE),
    re.compile(r"NameError", re.IGNORECASE),
    re.compile(r"IndentationError", re.IGNORECASE),
    re.compile(r"AttributeError", re.IGNORECASE),
]

_TRANSIENT_PATTERNS = [
    re.compile(r"TimeoutError", re.IGNORECASE),
    re.compile(r"ConnectionError", re.IGNORECASE),
    re.compile(r"ConnectionRefusedError", re.IGNORECASE),
    re.compile(r"timed out", re.IGNORECASE),
]

_CONTRACT_PATTERNS = [
    re.compile(r"AssertionError", re.IGNORECASE),
    re.compile(r"ValueError", re.IGNORECASE),
    re.compile(r"expected .+ got", re.IGNORECASE),
    re.compile(r"Expected .+ but got", re.IGNORECASE),
]


def classify_test_failures(output: str) -> FailureClass:
    """Classify test runner output by failure type.

    Priority: STRUCTURAL > CONTRACT > TRANSIENT > UNKNOWN.
    """
    if any(p.search(output) for p in _STRUCTURAL_PATTERNS):
        return FailureClass.STRUCTURAL
    if any(p.search(output) for p in _CONTRACT_PATTERNS):
        return FailureClass.CONTRACT
    if any(p.search(output) for p in _TRANSIENT_PATTERNS):
        return FailureClass.TRANSIENT
    return FailureClass.UNKNOWN


def tasks_md_hash(path: Path) -> str:
    """Hash the tasks.md file for drift baseline."""
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def check_spec_drift(
    tasks_md: Path,
    apply_progress_json: str | None,
) -> bool:
    """Check if tasks.md checked-state disagrees with apply-progress.

    Returns True if drift detected, False if consistent or no apply-progress yet.
    """
    import json

    if not tasks_md.exists():
        return False
    if not apply_progress_json:
        return False
    try:
        progress = json.loads(apply_progress_json)
    except json.JSONDecodeError:
        return True

    tasks_in_progress = progress.get("tasks", {})
    if not tasks_in_progress:
        return False

    md_content = tasks_md.read_text(encoding="utf-8")
    # Find all checked task IDs: `- [x] **T1.1**` or `- [x] T1.1`
    checked = set(re.findall(r"-\s*\[x\]\s*\*?\*?(T\d+\.\d+)", md_content))
    # Find all task IDs marked as completed in progress
    completed = {
        tid
        for tid, info in tasks_in_progress.items()
        if info.get("status") in ("completed", "done", "merged")
    }
    # Drift = marked completed in progress but not checked in md, OR vice versa
    return checked != completed


@dataclass
class DriftReport:
    """Aggregated drift signals for a change."""

    spec_drift: bool
    test_failure: FailureClass
    memory_mismatch: bool

    @property
    def has_drift(self) -> bool:
        return (
            self.spec_drift
            or self.memory_mismatch
            or self.test_failure
            in (
                FailureClass.STRUCTURAL,
                FailureClass.CONTRACT,
            )
        )

    def action(self) -> str:
        """Recommended action based on drift signals."""
        if self.spec_drift:
            return "halt_apply"
        if self.test_failure == FailureClass.STRUCTURAL:
            return "escalate_structural"
        if self.test_failure == FailureClass.CONTRACT:
            return "respec"
        if self.memory_mismatch:
            return "reconcile_memory"
        return "continue"
