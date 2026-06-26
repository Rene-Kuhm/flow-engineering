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

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from flow_engineering import graphify_query
from flow_engineering.binding import CodeRef, ParseError, extract_code_refs

if TYPE_CHECKING:
    from flow_engineering.engram_io import EngramBackend


_LINE_PATTERN = re.compile(r"\d+")


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

    Algorithm (REQ-9):
        1. ``current_nodes`` is ``None`` or empty -> ``UNABLE_TO_VERIFY``.
        2. ``binding.id`` absent from ``current_id_map`` -> ``STALE_ID``.
        3. ``(file, line)`` differ from current -> ``STALE_LOCATION``.
        4. ``label`` differs from current -> ``LABEL_DRIFT``.
        5. Otherwise -> ``STILL_VALID``.

    ``OBSOLETE`` and ``CONTRADICTED`` are deliberately NOT emitted here
    (design #123 decisions 2 + 3) — they require cross-decision aggregation
    that only ``scan_change`` performs.
    """
    if not current_nodes:
        return DriftClass.UNABLE_TO_VERIFY
    entry = current_id_map.get(binding.id)
    if entry is None:
        return DriftClass.STALE_ID
    cur_file, cur_line, cur_label = entry
    if cur_file != binding.file or cur_line != binding.line:
        return DriftClass.STALE_LOCATION
    if cur_label != binding.label:
        return DriftClass.LABEL_DRIFT
    return DriftClass.STILL_VALID


def _parse_line(location: object) -> int:
    """Best-effort line-int coercion for graph.json schema variants."""
    if isinstance(location, int):
        return location
    if isinstance(location, str):
        m = _LINE_PATTERN.search(location)
        return int(m.group(0)) if m else 0
    return 0


def load_graph(graph_json_path: Path) -> tuple[dict | None, dict | None, float | None]:
    """Load ``graph.json`` once for a drift scan (design #123 decision 1).

    Returns a 3-tuple ``(current_nodes, current_id_map, graph_mtime)``. When
    the path is missing, the JSON is malformed, or the top-level shape is
    unexpected, returns ``(None, None, None)`` so callers fail-open.

    - ``current_nodes``: ``dict[id, node_dict]`` — full node for inspection.
    - ``current_id_map``: ``dict[id, (file, line, label)]`` — fast lookup
      for ``classify_binding``. Tolerates both ``file/line`` and
      ``source_file/source_location`` shapes.
    - ``graph_mtime``: epoch seconds (float) of the snapshot, used for
      audit correlation in the resulting ``DriftReport``.
    """
    try:
        if not graph_json_path.exists():
            return (None, None, None)
        mtime = graph_json_path.stat().st_mtime
        data = json.loads(graph_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return (None, None, None)
    if not isinstance(data, dict):
        return (None, None, None)
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        return (None, None, None)
    current_nodes: dict[str, dict] = {}
    current_id_map: dict[str, tuple[str, int, str]] = {}
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            continue
        nid = str(n["id"])
        current_nodes[nid] = n
        file = str(n.get("file", n.get("source_file", "")))
        line = _parse_line(n.get("line", n.get("source_location", 0)))
        label = str(n.get("label", nid))
        current_id_map[nid] = (file, line, label)
    return (current_nodes, current_id_map, mtime)


def _detect_contradicted(findings: list[Finding]) -> set[int]:
    """Return indices of findings to reclassify as ``CONTRADICTED``.

    Design #123 decision 2: same ``id`` bound by multiple findings whose
    ``confidence`` gap exceeds ``0.4``. ``UNABLE_TO_VERIFY`` and
    ``OBSOLETE`` are excluded — they have no real binding to contradict.
    """
    by_id: dict[str, list[tuple[int, float]]] = {}
    for idx, f in enumerate(findings):
        if f.drift_class in (DriftClass.UNABLE_TO_VERIFY, DriftClass.OBSOLETE):
            continue
        bid = f.binding.id
        by_id.setdefault(bid, []).append((idx, f.binding.confidence))
    contradicted: set[int] = set()
    for entries in by_id.values():
        if len(entries) < 2:
            continue
        confidences = [c for _, c in entries]
        if max(confidences) - min(confidences) > 0.4:
            for idx, _ in entries:
                contradicted.add(idx)
    return contradicted


def scan_change(
    change_name: str,
    *,
    graph_json_path: Path,
    backend: "EngramBackend | None" = None,
    include_obsolete: bool = False,
    since: float | None = None,
) -> DriftReport:
    """Scan a change for decision-to-code drift (REQ-9 + REQ-12).

    Implementation lands in T1.6 batch C GREEN phase (commit 3). See the
    RED tests in ``tests/unit/test_decision_drift.py`` for the contract.
    """
    raise NotImplementedError("scan_change lands in T1.6 (batch C) GREEN")