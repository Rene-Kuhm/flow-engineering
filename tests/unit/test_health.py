"""Unit tests for ``flow_engineering.health``.

Covers:
- REQ-WORKSPACE-HEALTH-VERDICT-MATH -- pure threshold function
  (``TestCategorizeVerdict``: 5 boundary cases).

The implementations live in a NEW module ``src/flow_engineering/health.py``
(library-first; introduced by ``workspace-health-advisor`` change).

This file intentionally covers ONLY the verdict math primitives for
PR1 (sub-batch B-verdict-only). The R9 detector, the recommendation
copy, the summary builder, the envelope composer, and the Rich
renderer land in later sub-batches (PR2/PR3/PR4).
"""

from __future__ import annotations

# ============================================================================
# T-B.1 RED -- pure verdict math.
# ============================================================================


class TestCategorizeVerdict:
    """REQ-WORKSPACE-HEALTH-VERDICT-MATH: 0=HEALTHY, 1-2=NEEDS-ATTENTION, 3+=CRITICAL.

    The function is a pure threshold mapping with NO I/O and NO time-dependent
    state; every boundary count is exercised (0/1/2/3/4).
    """

    def test_zero_triggers_is_healthy(self) -> None:
        from flow_engineering.health import _categorize_verdict

        assert _categorize_verdict([]) == "HEALTHY"

    def test_one_trigger_is_needs_attention(self) -> None:
        from flow_engineering.health import _categorize_verdict

        assert _categorize_verdict(["R6"]) == "NEEDS-ATTENTION"

    def test_two_triggers_is_needs_attention(self) -> None:
        from flow_engineering.health import _categorize_verdict

        assert _categorize_verdict(["R6", "R7"]) == "NEEDS-ATTENTION"

    def test_three_triggers_is_critical(self) -> None:
        from flow_engineering.health import _categorize_verdict

        assert _categorize_verdict(["R6", "R7", "R8"]) == "CRITICAL"

    def test_four_triggers_is_critical(self) -> None:
        from flow_engineering.health import _categorize_verdict

        assert _categorize_verdict(["R6", "R7", "R8", "R9"]) == "CRITICAL"
