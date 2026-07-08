"""GraphLoader Protocol + concrete adapters (REQ-DRIFT-DETECTION-1..4).

Slice 1 of the drift-detection change. The Protocol seam replaces the
inline graph-load plumbing inside ``decision_drift.scan_change`` so
future slices (OTel push, cross-project federation, per-finding
``graph_unavailable`` refinement) can plug in without touching the pure
classifier.

Module surface
--------------

- ``GraphLoadError`` + 4 typed exceptions (``GraphMissing``,
  ``GraphMalformed``, ``PermissionDenied``, ``SnapshotEnvelopeCorrupt``)
  — the typed hierarchy that replaces the bare ``Exception``/``RuntimeError``
  swallows in the v1.2.0 baseline (``load_graph:238-248``,
  ``_load_graph_from_snapshot:314-315``).
- ``GraphLoader`` — the ``@runtime_checkable`` Protocol with a single
  ``load(self) -> tuple[dict | None, dict | None, float | None]`` method.
- ``LiveDiskGraphLoader(graph_json_path: Path)`` — concrete adapter for
  the live-disk path; raises the 3 live-path typed exceptions.
- ``SnapshotGraphLoader(snap_id: str)`` — concrete adapter for the
  snapshot-pinned path; raises ``SnapshotEnvelopeCorrupt`` when the
  envelope is corrupt.
- ``_parse_envelope_graph`` + ``_index_graph_payload`` — co-located
  helpers shared by ``SnapshotGraphLoader`` and (test fixtures) the
  legacy ``decision_drift.load_graph``.

Design references: ``openspec/changes/drift-detection/design.md`` §3
(Protocol definitions) + §4 (typed exception hierarchy).
"""

from __future__ import annotations

import contextlib
import errno
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Protocol, runtime_checkable

from flow_engineering.snapshot_manager import (
    SnapshotEnvelopeError,
    SnapshotManager,
)

# ---------- Typed exception hierarchy (REQ-DRIFT-DETECTION-4) ----------


class GraphLoadError(Exception):
    """Base class for typed graph-load failures.

    All 4 typed exceptions below inherit from this base so callers can
    catch ``except GraphLoadError`` to handle ANY graph-load failure
    uniformly while still distinguishing subtypes for fine-grained
    ``unable_reason`` mapping.

    Inherits from ``Exception`` (NOT ``RuntimeError`` or ``ValueError``)
    so it does NOT collide with the ``SnapshotGraphMissing`` (the D2
    graceful degradation signal that lives at
    ``snapshot_manager.SnapshotGraphMissingError`` since v1.1.6) — the
    latter stays a distinct ``raise`` at the scan boundary per REQ-33
    contract.
    """


class GraphMissing(GraphLoadError):  # noqa: N818
    """Raised when ``graph_json_path.exists() is False`` on the live path.

    Replaces the bare ``return (None, None, None)`` fail-open at
    ``decision_drift.py:238`` (the old path C). ``unable_reason`` maps
    to ``"graph_file_missing"``.
    """


class GraphMalformed(GraphLoadError):  # noqa: N818
    """Raised when ``json.loads()`` fails, OR the top-level shape is not a
    ``dict``, OR the ``nodes`` field is not a ``list``.

    Replaces the bare ``return (None, None, None)`` fail-open at
    ``decision_drift.py:242-248`` (the old path D). ``unable_reason``
    maps to ``"graph_file_malformed"``.
    """


class PermissionDenied(GraphLoadError):  # noqa: N818
    """Raised when ``OSError`` carries ``errno`` in ``{EACCES, EPERM, EROFS}``
    while reading the graph file.

    Replaces the indistinguishable ``OSError`` swallow in the old path D.
    ``unable_reason`` maps to ``"graph_file_unreadable"``.
    """


class SnapshotEnvelopeCorrupt(GraphLoadError):  # noqa: N818
    """Raised when ``SnapshotManager.show(snap_id)`` raises
    :class:`SnapshotEnvelopeError` (sha256 verification failure or
    unrecognised schema version).

    Distinct from ``SnapshotGraphMissing`` because an envelope can be
    CORRUPT (sha256 mismatch) without being MISSING (--no-include-graph
    at create time). ``unable_reason`` maps to
    ``"snapshot_envelope_corrupt"``.

    Note: this exception is a graph-loader concern, not a
    snapshot-manager concern. ``snapshot_manager.py`` already raises
    ``SnapshotEnvelopeError`` for the broader envelope-integrity use
    case; we re-raise it as ``SnapshotEnvelopeCorrupt`` here so the
    ``scan_change`` boundary can distinguish graph-load failures from
    other snapshot failures.
    """


# ---------- Protocol (REQ-DRIFT-DETECTION-1) ----------


@runtime_checkable
class GraphLoader(Protocol):
    """Narrow contract for a graph-loader collaborator.

    ``scan_change`` consumes a ``GraphLoader`` instead of inlining the
    graph-load logic. Two concrete adapters ship in Slice 1; future
    slices (OTel-instrumented loader, federated loader) plug in here
    without touching ``scan_change``.

    Runtime-checkable so ``isinstance(loader, GraphLoader)`` works
    without explicit registration.
    """

    def load(self) -> tuple[dict | None, dict | None, float | None]:  # type: ignore[type-arg]
        """Return ``(current_nodes, current_id_map, graph_mtime)`` for the
        scan to consume.

        Raises:
            GraphMissing: graph file absent (live path).
            GraphMalformed: JSON decode failure or shape mismatch.
            PermissionDenied: OSError with EACCES/EPERM/EROFS errno.
            SnapshotEnvelopeCorrupt: snapshot envelope fails sha256 or
                schema-version check.

        Returns:
            ``(current_nodes, current_id_map, graph_mtime)`` 3-tuple. The
            legacy fail-open ``(None, None, None)`` is NOT a valid
            return value for the live-disk path — the typed exception
            hierarchy replaces it. The snapshot path MAY return
            ``(None, None, None)`` when the envelope lacks
            ``graph_json_content`` (the D2 graceful degradation signal
            that surfaces as ``SnapshotGraphMissing`` at the scan
            boundary).
        """
        ...


# ---------- Live-disk adapter (REQ-DRIFT-DETECTION-1 scenarios 1 + 2) ----------


class LiveDiskGraphLoader:
    """Adapter that wraps the current ``load_graph(graph_json_path)`` happy
    path (REQ-DRIFT-DETECTION-1 scenario 1 + 2).

    Concrete implementation of :class:`GraphLoader`. Reads from
    ``graph_json_path`` on the live disk. Raises the 3 live-path typed
    exceptions; ``SnapshotEnvelopeCorrupt`` is unreachable from this
    adapter.
    """

    def __init__(self, graph_json_path: Path) -> None:
        self._path = graph_json_path

    def load(self) -> tuple[dict | None, dict | None, float | None]:  # type: ignore[type-arg]
        if not self._path.exists():
            raise GraphMissing(
                f"graph file not found: {self._path} "
                f"(hint: pass --graph-json=<path> with a real graph.json)"
            )
        try:
            mtime = self._path.stat().st_mtime
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except PermissionError as exc:
            raise PermissionDenied(
                f"graph file unreadable (permission denied): {self._path}"
            ) from exc
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EPERM, errno.EROFS}:
                raise PermissionDenied(
                    f"graph file unreadable (errno={exc.errno}): {self._path}"
                ) from exc
            raise  # unexpected OSError → let it propagate
        except json.JSONDecodeError as exc:
            raise GraphMalformed(
                f"graph file is not valid JSON: {self._path} "
                f"(line {exc.lineno}, col {exc.colno})"
            ) from exc
        if not isinstance(data, dict):
            raise GraphMalformed(
                f"graph file top-level is not an object: {self._path}"
            )
        nodes = data.get("nodes", [])
        if not isinstance(nodes, list):
            raise GraphMalformed(
                f"graph file 'nodes' field is not a list: {self._path}"
            )
        return _index_graph_payload(nodes, mtime)


# ---------- Snapshot adapter (REQ-DRIFT-DETECTION-1 scenario 3) ----------


class SnapshotGraphLoader:
    """Adapter that wraps the current ``_load_graph_from_snapshot(snap_id)``
    (REQ-DRIFT-DETECTION-1 scenario 3).

    Concrete implementation of :class:`GraphLoader`. Reads the frozen
    ``graph_state.graph_json_content`` (or legacy ``graph_json`` dict)
    from the snapshot envelope.

    ``SnapshotManager.show()`` does NOT touch the backend, so we pass
    ``backend=None`` — the constructor accepts ``None`` because the
    constructor only requires the argument when the backend is USED
    (e.g., ``mem_save``); ``show()`` reads the envelope file directly
    without touching the backend.
    """

    def __init__(self, snap_id: str) -> None:
        self._snap_id = snap_id

    def load(self) -> tuple[dict | None, dict | None, float | None]:  # type: ignore[type-arg]
        snapshots_dir = _resolve_snapshots_dir_for_loader()
        manager = SnapshotManager(
            snapshots_dir=snapshots_dir,
            backend=None,  # type: ignore[arg-type]  # show() never touches backend
        )
        try:
            envelope = manager.show(self._snap_id)
        except SnapshotEnvelopeError as exc:
            raise SnapshotEnvelopeCorrupt(
                f"snapshot envelope corrupt: snap_id={self._snap_id!r} "
                f"(sha256 verification failed or unrecognised schema version)"
            ) from exc
        return _parse_envelope_graph(envelope)


def _parse_envelope_graph(envelope: dict) -> tuple[dict | None, dict | None, float | None]:  # type: ignore[type-arg]
    """Parse a snapshot envelope's frozen graph content.

    Mirrors the existing ``_load_graph_from_snapshot:319-359`` logic
    EXACTLY (returns ``(None, None, None)`` when no graph content is
    present — this is the signal for ``scan_change`` to raise
    ``SnapshotGraphMissing`` per the D2 graceful degradation contract).
    """
    graph_state = envelope.get("graph_state", {})
    meta = envelope.get("metadata", {})
    synthetic_mtime = float(meta.get("file_size_bytes", 0)) or None

    graph_json_content = graph_state.get("graph_json_content")
    if isinstance(graph_json_content, str) and graph_json_content:
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(graph_json_content)
                tmp_path = tmp.name
            try:
                parsed = json.loads(graph_json_content)
            finally:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise GraphMalformed(
                f"snapshot graph_json_content is not valid JSON: "
                f"snap_id={envelope.get('id', '<unknown>')!r}"
            ) from exc
        if not isinstance(parsed, dict):
            raise GraphMalformed(
                "snapshot graph_json_content top-level is not an object"
            )
        nodes = parsed.get("nodes", [])
        return _index_graph_payload(nodes, synthetic_mtime)

    graph_json = graph_state.get("graph_json")
    if isinstance(graph_json, dict):
        nodes = graph_json.get("nodes", [])
        return _index_graph_payload(nodes, synthetic_mtime)

    # No graph content — return the legacy fail-open signal; the scan
    # boundary decides whether to raise SnapshotGraphMissing.
    return (None, None, None)


# ---------- Helpers (REQ-DRIFT-DETECTION-1 + REQ-DRIFT-DETECTION-8) ----------


def _index_graph_payload(
    nodes: list[dict],  # type: ignore[type-arg]
    mtime: float | None,
) -> tuple[dict[str, dict] | None, dict[str, tuple[str, int, str]] | None, float | None]:  # type: ignore[type-arg]
    """Convert a raw ``graph.json`` ``nodes`` list into the index tuple.

    Identical to the existing ``decision_drift._index_graph_payload``
    (lines 252-274). Co-located here because it's an adapter
    implementation detail, not part of the public ``decision_drift``
    API.

    Tolerates both ``file/line`` and ``source_file/source_location``
    node shapes (legacy v0.3.0 graph.json schema compatibility).
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
        line_raw = n.get("line", n.get("source_location", 0))
        line = _parse_line_for_loader(line_raw)
        label = str(n.get("label", nid))
        current_id_map[nid] = (file, line, label)
    return (current_nodes, current_id_map, mtime)


_LINE_PATTERN = re.compile(r"\d+")


def _parse_line_for_loader(location: object) -> int:
    """Best-effort line-int coercion for graph.json schema variants.

    Mirrors ``decision_drift._parse_line`` (lines 190-197). Duplicated
    here to keep ``drift_graph_loader`` independent of ``decision_drift``
    (the Protocol refactor reverses the dependency direction).
    """
    if isinstance(location, int):
        return location
    if isinstance(location, str):
        m = _LINE_PATTERN.search(location)
        return int(m.group(0)) if m else 0
    return 0


def _resolve_snapshots_dir_for_loader() -> Path:
    """Resolve the snapshot directory path, honouring the env override.

    Lazy-imports ``decision_drift._resolve_snapshots_dir`` to avoid the
    design §3 typo (the design imports it from ``snapshot_manager``
    where it does NOT live; the canonical home is
    ``decision_drift._resolve_snapshots_dir`` at line 378).

    Fallback inline implementation covers the case where the
    ``decision_drift`` import is shadowed by a circular import (e.g.,
    when ``decision_drift`` itself lazy-imports this module).
    """
    import os as _os
    from pathlib import Path as _Path

    try:
        from flow_engineering.decision_drift import (
            _resolve_snapshots_dir as _impl,
        )

        return _impl()
    except ImportError:
        env = _os.environ.get("FLOW_SNAPSHOTS_DIR")
        if env:
            return _Path(env)
        return _Path.home() / ".flow-engineering" / "snapshots"


__all__ = [
    "GraphLoadError",
    "GraphMissing",
    "GraphMalformed",
    "PermissionDenied",
    "SnapshotEnvelopeCorrupt",
    "GraphLoader",
    "LiveDiskGraphLoader",
    "SnapshotGraphLoader",
]
