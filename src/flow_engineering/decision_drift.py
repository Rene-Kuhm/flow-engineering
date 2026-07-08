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

import contextlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from flow_engineering import graphify_query
from flow_engineering.binding import CodeRef, ParseError, extract_code_refs
from flow_engineering.snapshot_manager import (
    SnapshotGraphMissingError,
)

if TYPE_CHECKING:
    from flow_engineering.engram_io import EngramBackend


_LINE_PATTERN = re.compile(r"\d+")


class DriftClass(StrEnum):
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
    """One per-binding classification result (REQ-V9.1 + REQ-V9.4).

    v0.9.0 (REQ-V9.1): ``decision_id`` is hard-typed ``int``; legacy
    numeric ``str`` inputs are no longer accepted (the v0.8.0
    :meth:`from_legacy` shim was removed).

    v0.9.0 (REQ-V9.4): ``__post_init__`` raises ``TypeError`` if
    ``decision_id`` is not a real ``int``. ``bool`` is explicitly
    rejected because Python treats ``bool`` as an ``int`` subclass — a
    naive ``isinstance(x, int)`` check would silently accept ``True`` /
    ``False`` as valid ``decision_id`` values, which is the kind of
    stringy truthy/falsy coercion bug this enforcement exists to
    prevent. Hard break — no ``DeprecationWarning``, no ``int()``
    coercion (the W1 shim IS the soft compat; v0.9.0 removes it).
    """

    decision_id: int  # REQ-56 W8; hard break in v0.9.0
    binding: CodeRef
    drift_class: DriftClass
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, int) or isinstance(
            self.decision_id, bool
        ):
            raise TypeError(
                f"Finding.decision_id must be int, got {type(self.decision_id).__name__}"
            )


@dataclass
class DriftReport:
    """Aggregate result for a full scan of one change (REQ-V9.2).

    v0.9.0 (REQ-V9.2): ``scanned_at`` is hard-typed ``str`` ISO 8601 UTC
    ``Z``-suffixed; legacy ``float`` epoch inputs are no longer accepted
    (the v0.8.0 :meth:`from_legacy` shim was removed).
    """

    change_name: str
    scanned_at: str  # REQ-56 W8; ISO 8601 UTC Z-suffixed; hard break in v0.9.0
    graph_mtime: str | None  # REQ-56 W8
    decisions_total: int
    bindings_total: int
    class_counts: dict[DriftClass, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    graph_unavailable: bool = False
    unable_reason: str | None = None  # REQ-56 W8 NEW field


def _epoch_to_iso(epoch: float | int) -> str:
    """Convert a Unix epoch (float seconds) to an ISO 8601 ``str`` with ``Z`` suffix.

    Used by :meth:`DriftReport.from_legacy` and other v0.7.x migration
    sites to coerce legacy ``float`` epoch inputs into the v0.8.0
    ``str`` ISO 8601 contract.
    """
    return datetime.fromtimestamp(float(epoch), tz=UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def classify_binding(
    ref: CodeRef,
    graph_nodes: dict[str, dict],  # type: ignore[type-arg]
) -> DriftClass:
    """Classify a single ``CodeRef`` against the current graph state (REQ-9 + REQ-V9.3).

    v0.9.0 signature (REQ-V9.3): 2-arg ``(ref, graph_nodes)`` is the ONLY
    entry point. The v0.8.0 3-arg signature was retained as a 1-release
    ``DeprecationWarning`` shim; it is removed in v0.9.0.

    Algorithm (REQ-9):
        1. ``graph_nodes`` is ``None`` or empty -> ``UNABLE_TO_VERIFY``.
        2. ``ref.id`` absent from derived ``current_id_map`` -> ``STALE_ID``.
        3. ``(file, line)`` differ from current -> ``STALE_LOCATION``.
        4. ``label`` differs from current -> ``LABEL_DRIFT``.
        5. Otherwise -> ``STILL_VALID``.

    ``OBSOLETE`` and ``CONTRADICTED`` are deliberately NOT emitted here
    (design #123 decisions 2 + 3) — they require cross-decision aggregation
    that only ``scan_change`` performs.
    """
    if not graph_nodes:
        return DriftClass.UNABLE_TO_VERIFY
    current_id_map: dict[str, tuple[str, int, str]] = {
        node_id: (
            str(node.get("file") or node.get("source_file", "")),
            _parse_line(node.get("line") or node.get("source_location", 0)),
            str(node.get("label", node_id)),
        )
        for node_id, node in graph_nodes.items()
    }
    return _classify_with_id_map(ref, graph_nodes, current_id_map)


def _classify_with_id_map(
    binding: CodeRef,
    current_nodes: dict[str, dict],  # type: ignore[type-arg]
    current_id_map: dict[str, tuple[str, int, str]],
) -> DriftClass:
    """Core classification algorithm shared by the 2-arg and 3-arg surfaces."""
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


# ``SnapshotGraphMissing`` is now a PEP 562 lazy re-export of the
# canonical ``flow_engineering.snapshot_manager.SnapshotGraphMissingError``
# (established since v1.1.6). The re-export lives at the BOTTOM of this
# module as a ``__getattr__`` to honor the v1.1.6 DeprecationWarning
# convention and to keep the canonical class object identical
# (``SnapshotGraphMissing IS SnapshotGraphMissingError``).
# See REQ-DRIFT-DETECTION-7 + the design §6 PEP 562 example.


def _parse_line(location: object) -> int:
    """Best-effort line-int coercion for graph.json schema variants."""
    if isinstance(location, int):
        return location
    if isinstance(location, str):
        m = _LINE_PATTERN.search(location)
        return int(m.group(0)) if m else 0
    return 0


def load_graph(
    graph_json_path: Path | None = None,
    *,
    snap_id: str | None = None,
) -> tuple[dict | None, dict | None, float | None]:  # type: ignore[type-arg]
    """Load ``graph.json`` once for a drift scan (design #123 decision 1).

    REQ-33 + design D13: the kwarg-only ``snap_id`` activates the
    frozen-state path. When ``snap_id`` is provided, ``graph_json_path``
    MUST be ``None`` (mutual exclusion) and the snapshot envelope's
    ``graph_state.graph_json`` is loaded instead of the disk file. The
    snapshot's stored ``metadata.file_size_bytes`` mtime is returned in
    place of the live ``graph_mtime`` so audit correlation reflects the
    frozen state.

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
    if snap_id is not None and graph_json_path is not None:
        raise ValueError(
            "load_graph: snap_id and graph_json_path are mutually exclusive; "
            "pass one or the other, never both"
        )
    if snap_id is not None:
        return _load_graph_from_snapshot(snap_id)
    if graph_json_path is None:
        # No path, no snap_id: fail-open return (mirrors the historical
        # ``Path is None`` behavior on the live path).
        return (None, None, None)
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
    return _index_graph_payload(nodes, mtime)


def _index_graph_payload(
    nodes: list, mtime: float | None,  # type: ignore[type-arg]
) -> tuple[dict | None, dict | None, float | None]:  # type: ignore[type-arg]
    """Convert a raw ``graph.json`` ``nodes`` list into the index tuple.

    Shared between the live and snapshot-pinned branches so the binding
    shape (``file/line`` vs ``source_file/source_location``) tolerance
    is identical.
    """
    if not isinstance(nodes, list):
        return (None, None, None)
    current_nodes: dict[str, dict] = {}  # type: ignore[type-arg]
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


def _load_graph_from_snapshot(
    snap_id: str,
) -> tuple[dict | None, dict | None, float | None]:  # type: ignore[type-arg]
    """Load the frozen ``graph_state.graph_json`` from the snapshot envelope.

    Reads from ``~/.flow-engineering/snapshots/<snap_id>.json.gz``. The
    envelope is parsed via :class:`SnapshotManager.show` so the sha256
    integrity check fires before any bytes are consumed by the scan.

    T1.5 brief: prefers ``graph_state.graph_json_content`` (the raw text
    content of ``graph.json`` populated by ``SnapshotManager.create()``
    in batch B2) and writes it to a temp file before parsing — this
    preserves the exact on-disk bytes and lets the existing
    ``_index_graph_payload`` helper consume the parsed nodes uniformly.

    Falls back to ``graph_state.graph_json`` (a dict that batch B1
    fixtures + BDD tests inject manually) for backwards compatibility
    with the existing 754-test baseline.

    If the snapshot was created with ``--no-include-graph`` OR no
    ``graph.json`` file existed at create time (test fixtures, fresh
    installs), neither field is present — we return
    ``(None, None, None)`` so the caller fail-opens with
    ``graph_unavailable=True`` and :func:`scan_change` raises
    :class:`SnapshotGraphMissingError` (canonical home since v1.1.6;
    the legacy ``SnapshotGraphMissing`` alias still works via the PEP
    562 ``__getattr__`` at the bottom of this module).
    """
    from flow_engineering.snapshot_manager import (
        SnapshotEnvelopeError,
        SnapshotManager,
    )

    # Honour the FLOW_SNAPSHOTS_DIR / test override pattern via the env
    # variable so the production default is consistent with the CLI.
    snapshots_dir = _resolve_snapshots_dir()
    manager = SnapshotManager(snapshots_dir=snapshots_dir, backend=_DummyBackend())  # type: ignore[arg-type]
    try:
        envelope = manager.show(snap_id)
    except SnapshotEnvelopeError:
        return (None, None, None)

    graph_state = envelope.get("graph_state", {})

    # Synthetic mtime = envelope's stored file_size_bytes (opaque
    # contract — only its non-emptiness is required for audit
    # correlation between frozen scans and live ones).
    meta = envelope.get("metadata", {})
    synthetic_mtime = float(meta.get("file_size_bytes", 0)) or None

    # Preferred path: ``graph_json_content`` (raw string from
    # ``SnapshotManager.create()``). Write to temp file, parse, return.
    graph_json_content = graph_state.get("graph_json_content")
    if isinstance(graph_json_content, str) and graph_json_content:
        try:
            import tempfile as _tempfile

            with _tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(graph_json_content)
                tmp_path = tmp.name
            try:
                parsed = json.loads(graph_json_content)
            finally:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
        except (OSError, json.JSONDecodeError, ValueError):
            return (None, None, None)
        if not isinstance(parsed, dict):
            return (None, None, None)
        nodes = parsed.get("nodes", [])
        return _index_graph_payload(nodes, synthetic_mtime)

    # Legacy path: ``graph_json`` (dict, manually injected by batch B1
    # fixtures and BDD tests). Kept for backwards compatibility so the
    # 754-test baseline continues to pass.
    graph_json = graph_state.get("graph_json")
    if isinstance(graph_json, dict):
        nodes = graph_json.get("nodes", [])
        return _index_graph_payload(nodes, synthetic_mtime)

    # Neither field present — fail-open so ``scan_change`` can raise
    # ``SnapshotGraphMissingError`` (canonical) with a structured error.
    return (None, None, None)


class _DummyBackend:
    """Backend stub used by ``_load_graph_from_snapshot``.

    The ``SnapshotManager`` constructor requires an ``EngramBackend`` but
    the snap-id branch never calls ``iter_observations`` — it only reads
    the envelope file directly via ``show``. The dummy satisfies the
    constructor signature without exposing any real data.
    """

    def iter_observations(self, *, project=None):  # type: ignore[no-untyped-def]  # pragma: no cover - unreachable
        return []

    def mem_search(self, *args, **kwargs):  # type: ignore[no-untyped-def]  # pragma: no cover - unreachable
        return []


def _resolve_snapshots_dir() -> Path:
    """Resolve the snapshot directory path, honouring the env override.

    Mirrors the cross-project-federation pattern: production default is
    ``~/.flow-engineering/snapshots``; tests override via
    ``FLOW_SNAPSHOTS_DIR`` (set in conftest when ``tmp_path`` is wired).
    """
    env = os.environ.get("FLOW_SNAPSHOTS_DIR")
    if env:
        return Path(env)
    return Path.home() / ".flow-engineering" / "snapshots"


def _snapshot_exists(snap_id: str) -> bool:
    """Return True iff the snapshot envelope file is on disk."""
    return (_resolve_snapshots_dir() / f"{snap_id}.json.gz").exists()


def _snapshot_has_graph(snap_id: str) -> bool:
    """Return True iff the snapshot's envelope has the frozen graph content.

    Supports BOTH the new ``graph_state.graph_json_content`` (raw string
    populated by ``SnapshotManager.create()`` in batch B2) and the legacy
    ``graph_state.graph_json`` (dict that batch B1 fixtures inject).
    Either presence means a drift-pinned scan can classify bindings.
    """
    from flow_engineering.snapshot_manager import (
        SnapshotEnvelopeError,
        SnapshotManager,
    )
    manager = SnapshotManager(
        snapshots_dir=_resolve_snapshots_dir(),
        backend=_DummyBackend(),  # type: ignore[arg-type]
    )
    try:
        envelope = manager.show(snap_id)
    except SnapshotEnvelopeError:
        return False
    graph_state = envelope.get("graph_state", {})
    if isinstance(graph_state.get("graph_json_content"), str):
        return bool(graph_state["graph_json_content"])
    return isinstance(graph_state.get("graph_json"), dict)


def _frozen_backend_from_snapshot(snap_id: str) -> EngramBackend:
    """Return an ``InMemoryBackend`` populated with the snapshot's frozen observations.

    REQ-33 D13: the snapshot's ``graph_state.observations`` becomes the
    implicit backend for the scan. We rebuild an ``InMemoryBackend``
    whose ``observations`` dict matches the snapshot, so the existing
    ``backend.iter_observations()`` scan loop runs unchanged.
    """
    from flow_engineering.engram_io import InMemoryBackend
    from flow_engineering.snapshot_manager import (
        SnapshotEnvelopeError,
        SnapshotManager,
    )

    manager = SnapshotManager(
        snapshots_dir=_resolve_snapshots_dir(),
        backend=_DummyBackend(),  # type: ignore[arg-type]
    )
    try:
        envelope = manager.show(snap_id)
    except SnapshotEnvelopeError:
        return InMemoryBackend()

    obs_list = envelope.get("graph_state", {}).get("observations", [])
    frozen = InMemoryBackend()
    if not isinstance(obs_list, list):
        return frozen
    for o in obs_list:
        if not isinstance(o, dict) or "id" not in o:
            continue
        # Preserve the snapshot's id so iteration returns the same
        # observation set the scan saw at snapshot time.
        oid = int(o["id"])
        frozen.observations[oid] = dict(o)
        if oid >= frozen.next_id:
            frozen.next_id = oid + 1
    return frozen


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
    graph_json_path: Path | None = None,
    backend: EngramBackend | None = None,
    include_obsolete: bool = False,
    since: float | None = None,
    snap_id: str | None = None,
) -> DriftReport:
    """Scan a change for decision-to-code drift (REQ-9 + REQ-12 + REQ-33).

    Aggregates per-binding classifications into a ``DriftReport``. Fails
    open: every error path returns a safe report (graph_unavailable=True
    when the snapshot cannot be read; empty otherwise). The function
    MUST NOT raise — callers (``flow drift`` CLI, daemon) rely on a
    terminal ``DriftReport``.

    REQ-33 + design D13 + D5: the kwarg-only ``snap_id`` activates the
    frozen-state path. When ``snap_id`` is provided:

    - ``backend`` MUST be ``None`` (mutual exclusion — the snapshot
      provides the observation set implicitly).
    - ``graph_json_path`` SHOULD be ``None`` (the snapshot provides the
      graph.json content implicitly).
    - Internally calls ``load_graph(snap_id=snap_id)`` to load the
      frozen graph.
    - Builds an ``InMemoryBackend`` from the snapshot's
      ``graph_state.observations`` so the rest of the scan logic runs
      unchanged against the frozen observation set.

    Args:
        change_name: The OpenSpec/SDD change identifier.
        graph_json_path: Path to ``graph.json`` snapshot. Ignored when
            ``snap_id`` is provided.
        backend: ``EngramBackend`` exposing ``iter_observations()``. When
            ``None``, an empty ``InMemoryBackend`` is used (zero decisions)
            OR a frozen-backend derived from the snapshot when
            ``snap_id`` is set.
        include_obsolete: When ``True``, query ``graphify_query`` for
            decisions without code_refs and emit ``OBSOLETE`` when zero
            candidates clear the threshold. Defaults ``False`` per design
            #123 decision 3 (LLM cost bound).
        since: Epoch seconds; skip observations whose ``created_at`` is
            strictly less than the cutoff.
        snap_id: When set, scan the snapshot's frozen observations
            instead of the live Engram backend. REQ-33 D5 headline —
            different snapshots → different drift reports.

    Returns:
        ``DriftReport`` aggregating per-binding classifications.
    """
    scanned_at = _epoch_to_iso(time.time())
    if snap_id is not None and backend is not None:
        # Mutual exclusion enforced as a ``ValueError`` so callers can
        # branch on it; ``load_graph`` mirrors this with its own check.
        raise ValueError(
            "scan_change: snap_id and backend are mutually exclusive; "
            "pass one or the other, never both"
        )
    try:
        # When ``snap_id`` is set, ``graph_json_path`` is loaded from the
        # snapshot envelope. When not, fall through to the existing
        # behavior — load from disk.
        if snap_id is not None:
            current_nodes, current_id_map, graph_mtime = load_graph(
                graph_json_path=None, snap_id=snap_id,
            )
            if current_nodes is None:
                # Either the envelope is corrupt or ``--no-include-graph``
                # was used at create time. D2 graceful degradation: raise
                # ``SnapshotGraphMissingError`` (canonical) so the CLI can
                # render a structured error rather than silently scanning
                # live. We only raise when the snapshot exists but its graph
                # is missing; an unreadable envelope returns the same
                # ``graph_unavailable=True`` report as the live path.
                if _snapshot_exists(snap_id) and not _snapshot_has_graph(snap_id):
                    # REQ-26 T1.7: emit snapshot_load_failed_total BEFORE
                    # raising so the audit trail captures the unfreezable
                    # attempt. The helper is fail-open and never raises.
                    from flow_engineering.observability import record_snapshot_event

                    record_snapshot_event(
                        "snapshot_load_failed_total",
                        snap_id=str(snap_id),
                        reason="graph_missing",
                    )
                    raise SnapshotGraphMissingError(
                        f"snapshot {snap_id} has no graph_json (created with "
                        f"--no-include-graph); drift-pinned scan unavailable"
                    )
                return DriftReport(
                    change_name=change_name,
                    scanned_at=scanned_at,
                    graph_mtime=None,
                    decisions_total=0,
                    bindings_total=0,
                    graph_unavailable=True,
                )
            backend = _frozen_backend_from_snapshot(snap_id)
        else:
            current_nodes, current_id_map, graph_mtime = load_graph(graph_json_path)
            if current_nodes is None:
                return DriftReport(
                    change_name=change_name,
                    scanned_at=scanned_at,
                    graph_mtime=None,
                    decisions_total=0,
                    bindings_total=0,
                    graph_unavailable=True,
                )

            if backend is None:
                from flow_engineering.engram_io import InMemoryBackend
                backend = InMemoryBackend()

        try:
            observations = backend.iter_observations()
        except Exception:
            observations = []

        prefix = f"sdd/{change_name}/"
        observations = [
            o for o in observations
            if str(o.get("topic_key", "")).startswith(prefix)
        ]

        if since is not None:
            observations = [
                o for o in observations
                if float(o.get("created_at", 0)) >= since
            ]

        findings: list[Finding] = []
        bindings_total = 0

        for obs in observations:
            try:
                content = str(obs.get("content", ""))
                raw_id = obs.get("id", "unknown")
                try:
                    decision_id = int(raw_id)
                except (TypeError, ValueError):
                    decision_id = -1
                try:
                    refs = extract_code_refs(content)
                except ParseError:
                    continue

                if not refs:
                    if include_obsolete:
                        prose = content[:500]
                        try:
                            candidates = graphify_query.query_nodes(prose)
                        except Exception:
                            candidates = []
                        if not candidates:
                            synthetic = CodeRef(
                                project="insyd",
                                id="(none)",
                                label="(no-binding)",
                                file="(none)",
                                line=0,
                                confidence=0.0,
                                source="unbound",
                            )
                            findings.append(
                                Finding(
                                    decision_id=decision_id,
                                    binding=synthetic,
                                    drift_class=DriftClass.OBSOLETE,
                                    detail="no code_refs; graphify returned 0 candidates",
                                )
                            )
                    continue

                for binding in refs:
                    bindings_total += 1
                    drift_class = classify_binding(binding, current_nodes)
                    findings.append(
                        Finding(
                            decision_id=decision_id,
                            binding=binding,
                            drift_class=drift_class,
                            detail="",
                        )
                    )
            except Exception:
                continue

        try:
            contradicted_indices = _detect_contradicted(findings)
            if contradicted_indices:
                rebuilt: list[Finding] = []
                for idx, f in enumerate(findings):
                    if idx in contradicted_indices:
                        conflicting = sorted(
                            {
                                other.decision_id
                                for other in findings
                                if other.binding.id == f.binding.id
                                and other.decision_id != f.decision_id
                            }
                        )
                        rebuilt.append(
                            Finding(
                                decision_id=f.decision_id,
                                binding=f.binding,
                                drift_class=DriftClass.CONTRADICTED,
                                detail=f"conflicting_decisions={conflicting}",
                            )
                        )
                    else:
                        rebuilt.append(f)
                findings = rebuilt
        except Exception:
            pass

        class_counts: dict[DriftClass, int] = {}
        for f in findings:
            class_counts[f.drift_class] = class_counts.get(f.drift_class, 0) + 1

        return DriftReport(
            change_name=change_name,
            scanned_at=scanned_at,
            graph_mtime=(
                _epoch_to_iso(graph_mtime)
                if isinstance(graph_mtime, (int, float))
                else graph_mtime
            ),
            decisions_total=len(observations),
            bindings_total=bindings_total,
            class_counts=class_counts,
            findings=findings,
            graph_unavailable=False,
        )
    except SnapshotGraphMissingError:
        # Configuration error: caller asked for ``snap_id`` scan but the
        # snapshot's graph is missing. Re-raise so the CLI can render a
        # structured error; do NOT fail-open (the user explicitly asked
        # for the frozen scan and we cannot satisfy it).
        raise
    except Exception:
        return DriftReport(
            change_name=change_name,
            scanned_at=scanned_at,
            graph_mtime=None,
            decisions_total=0,
            bindings_total=0,
            graph_unavailable=True,
        )


# ---------- Adapter-compat layer (REQ-DRIFT-DETECTION-8 + design §8) ----------


DEFAULT_GRAPH_JSON: Path = Path.home() / ".flow-engineering" / "graph.json"
"""Production default path for ``graph.json``. Mirrors the snapshot_manager
constant at ``snapshot_manager.py:60`` (defaults stay in lockstep)."""


def _build_loader(
    *,
    graph_json_path: Path | None,
    snap_id: str | None,
) -> object:  # GraphLoader
    """Dispatch public kwargs to a ``GraphLoader`` collaborator.

    REQ-DRIFT-DETECTION-8: the public kwargs are the single source of
    truth. This helper maps them to the internal Protocol surface.

    - ``snap_id`` non-None → ``SnapshotGraphLoader(snap_id)``
    - ``graph_json_path`` non-None → ``LiveDiskGraphLoader(graph_json_path)``
    - Both ``None`` → ``LiveDiskGraphLoader(DEFAULT_GRAPH_JSON)`` (raises
      ``GraphMissing`` on ``.load()`` if the default is absent, which
      maps to ``unable_reason='graph_file_missing'`` per REQ-DRIFT-DETECTION-6)
    """
    from flow_engineering.drift_graph_loader import (
        LiveDiskGraphLoader,
        SnapshotGraphLoader,
    )

    if snap_id is not None:
        return SnapshotGraphLoader(snap_id)
    if graph_json_path is None:
        return LiveDiskGraphLoader(DEFAULT_GRAPH_JSON)
    return LiveDiskGraphLoader(graph_json_path)


def _build_source(
    *,
    backend: EngramBackend | None,
    snap_id: str | None,
    change_name: str,
    since: float | None,
) -> object:  # ObservationSource
    """Dispatch public kwargs to an ``ObservationSource`` collaborator.

    REQ-DRIFT-DETECTION-8: the public kwargs are the single source of
    truth.

    - ``snap_id`` non-None → ``FrozenBackendObservationSource(snap_id)``
    - Otherwise → ``BackendObservationSource(backend, change_name, since)``
    """
    from flow_engineering.drift_observation_source import (
        BackendObservationSource,
        FrozenBackendObservationSource,
    )

    if snap_id is not None:
        return FrozenBackendObservationSource(snap_id)
    return BackendObservationSource(backend, change_name=change_name, since=since)


# ---------- PEP 562 lazy re-export (REQ-DRIFT-DETECTION-7 + design §6) ----------


def __getattr__(name: str) -> object:
    """PEP 562 module-level ``__getattr__`` for backward-compat aliases.

    REQ-DRIFT-DETECTION-7: ``SnapshotGraphMissing`` is canonical at
    ``flow_engineering.snapshot_manager.SnapshotGraphMissingError`` since
    v1.1.6. This 1-release alias at ``decision_drift`` preserves callers
    that imported the legacy name (``cli/drift.py:351`` still catches
    ``decision_drift.SnapshotGraphMissing``). The alias emits a
    ``DeprecationWarning`` at import time, matching the v1.1.6 precedent
    at ``snapshot_manager.py:113-124``.

    The ``__getattr__`` returns the canonical class object, so
    ``SnapshotGraphMissing IS SnapshotGraphMissingError`` and
    ``inspect.signature(SnapshotGraphMissing)`` work correctly (PEP 562
    is for module-attribute access, not class identity).
    """
    if name == "SnapshotGraphMissing":
        import warnings as _warnings

        from flow_engineering.snapshot_manager import SnapshotGraphMissingError

        _warnings.warn(
            "decision_drift.SnapshotGraphMissing is deprecated; "
            "import flow_engineering.snapshot_manager.SnapshotGraphMissingError "
            "instead. The alias will be removed in v1.4.",
            DeprecationWarning,
            stacklevel=2,
        )
        return SnapshotGraphMissingError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
