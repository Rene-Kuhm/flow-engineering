"""Health advisor primitives for ``flow workspace health``.

Library-first module per Constitution Article I. Public surface is
exported via ``__all__``.

This PR (sub-batch B-verdict-only) ships ONLY the verdict math
primitives: ``_categorize_verdict`` plus the two threshold constants
that document the bands. The R9 detector, the recommendation copy,
the summary builder, the envelope composer, and the Rich renderer
land in later sub-batches (PR2 / PR3 / PR4).
"""

from __future__ import annotations

from typing import Literal

__all__ = [
    "_VERDICT_HEALTHY_MAX_TRIGGERS",
    "_VERDICT_CRITICAL_MIN_TRIGGERS",
    "_categorize_verdict",
]


# ---------------------------------------------------------------------------
# Verdict math constants (REQ-WORKSPACE-HEALTH-VERDICT-MATH).
# ---------------------------------------------------------------------------

_VERDICT_HEALTHY_MAX_TRIGGERS: int = 0
_VERDICT_CRITICAL_MIN_TRIGGERS: int = 3


# ---------------------------------------------------------------------------
# Pure helpers.
# ---------------------------------------------------------------------------


def _categorize_verdict(
    triggers: list[str],
) -> Literal["HEALTHY", "NEEDS-ATTENTION", "CRITICAL"]:
    """Pure threshold mapping (REQ-WORKSPACE-HEALTH-VERDICT-MATH).

    Count -> verdict:
      - 0             -> HEALTHY
      - 1 or 2        -> NEEDS-ATTENTION
      - 3 or more     -> CRITICAL

    The function is pure (no I/O, no time-dependent state) so it
    can be RED-tested in isolation. The threshold constants
    ``_VERDICT_HEALTHY_MAX_TRIGGERS`` and ``_VERDICT_CRITICAL_MIN_TRIGGERS``
    document the bands and are reused by later sub-batches for the
    workspace-wide aggregate.
    """
    count = len(triggers)
    if count <= _VERDICT_HEALTHY_MAX_TRIGGERS:
        return "HEALTHY"
    if count < _VERDICT_CRITICAL_MIN_TRIGGERS:
        return "NEEDS-ATTENTION"
    return "CRITICAL"
