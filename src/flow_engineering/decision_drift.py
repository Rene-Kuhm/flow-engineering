"""Decision-reality drift detection library (REQ-9).

Pure-library resolver that classifies each ``CodeRef`` binding against the
current state of ``graph.json``. No I/O lives in this module — callers
(``flow drift`` CLI, ``flow watch --drift`` daemon) own the read side.

## DriftClass taxonomy (REQ-9)

Seven values, all mutually-exclusive per binding (except ``UNABLE_TO_VERIFY``
which is the terminal signal when the graph itself is unavailable):

- ``STILL_VALID``     — id resolves at the same ``file:line`` with matching label.
- ``LABEL_DRIFT``     — id resolves at the same ``file:line`` but label changed.
- ``STALE_LOCATION``  — id resolves at a different ``file:line``.
- ``STALE_ID``        — id is absent from current ``graph.json``.
- ``OBSOLETE``        — decision has no bindings + graphify finds no candidates.
                        **NOT** detected by ``classify_binding`` (handled by
                        ``scan_change`` per design #123 decision 3).
- ``CONTRADICTED``    — same id bound by multiple decisions with conflicting
                        source/confidence. **NOT** detected by
                        ``classify_binding`` (handled by ``scan_change`` per
                        design #123 decision 2).
- ``UNABLE_TO_VERIFY`` — graph could not be loaded (terminal, per-binding
                        fallback when ``current_nodes`` is ``None`` or empty).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from flow_engineering.binding import CodeRef


class DriftClass(str, Enum):
    """Mutually-exclusive classification for a single binding."""

    STILL_VALID = "STILL_VALID"
    LABEL_DRIFT = "LABEL_DRIFT"
    STALE_LOCATION = "STALE_LOCATION"
    STALE_ID = "STALE_ID"
    OBSOLETE = "OBSOLETE"
    CONTRADICTED = "CONTRADICTED"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"


@dataclass(frozen=True)
class Finding:
    """One per-binding classification result."""

    decision_id: str
    binding: CodeRef
    drift_class: DriftClass
    detail: str


@dataclass
class DriftReport:
    """Aggregate result for a full scan of one change."""

    change_name: str
    scanned_at: float
    graph_mtime: float | None
    decisions_total: int
    bindings_total: int
    class_counts: dict[DriftClass, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    graph_unavailable: bool = False


def classify_binding(
    binding: CodeRef,
    current_nodes: dict[str, dict],
    current_id_map: dict[str, tuple[str, int, str]],
) -> DriftClass:
    """Classify a single ``CodeRef`` against the current graph state.

    Args:
        binding: The ``CodeRef`` to classify.
        current_nodes: Full node dict from ``graph.json`` (id -> node dict).
            May be ``None`` or empty when the graph is unavailable.
        current_id_map: Projection of ``current_nodes`` mapping
            ``id -> (file, line, label)``. Built once per scan.

    Returns:
        The ``DriftClass`` for this binding.
    """
    raise NotImplementedError("classify_binding lands in T1.5 (batch B GREEN)")


def scan_change(
    change_name: str,
    *,
    graph_json_path: Path,
    include_obsolete: bool = False,
    since: float | None = None,
) -> DriftReport:
    """Scan a change for decision-to-code drift.

    Args:
        change_name: The OpenSpec/SDD change identifier.
        graph_json_path: Path to ``graph.json`` snapshot.
        include_obsolete: When ``True``, run ``graphify_query`` for unbound
            decisions to detect ``OBSOLETE``. Defaults ``False`` (opt-in
            per design #123 decision 3 — LLM cost bound).
        since: Epoch seconds; skip observations with ``updated_at`` < ``since``.

    Returns:
        ``DriftReport`` aggregating per-binding classifications.
    """
    raise NotImplementedError("scan_change lands in T1.6 (batch C)")