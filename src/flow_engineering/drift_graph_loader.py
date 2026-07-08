"""GraphLoader Protocol + LiveDisk adapter (REQ-DRIFT-DETECTION-1).

Slice 1 (T1.2a) of the drift-detection change. The Protocol seam replaces
the inline graph-load plumbing inside ``decision_drift.scan_change`` so
future slices (OTel push, cross-project federation, per-finding
``graph_unavailable``) can plug in without touching the pure classifier.

This module grows across the slice:

- **T1.2a**: ``GraphLoadError`` base + ``GraphMissing`` +
  ``LiveDiskGraphLoader`` (live-disk path).
- **T1.2b**: ``GraphMalformed`` + ``PermissionDenied`` +
  ``SnapshotEnvelopeCorrupt`` + ``SnapshotGraphLoader`` (snapshot path)
  + co-located helpers (``_parse_envelope_graph``,
  ``_index_graph_payload``).
- **T3.2**: typed-exception classes split out to a dedicated
  ``drift_exceptions.py`` per the user's task override (see tasks.md
  "Size:exception justification" §4).

Design references: ``openspec/changes/drift-detection/design.md`` §3
(Protocol definitions) + §4 (typed exception hierarchy).
"""

from __future__ import annotations

import errno
import json
from pathlib import Path
from typing import Protocol, runtime_checkable

# ---------- Typed exception hierarchy (REQ-DRIFT-DETECTION-4) ----------


class GraphLoadError(Exception):
    """Base class for typed graph-load failures.

    All typed exceptions below inherit from this base so callers can
    catch ``except GraphLoadError`` to handle ANY graph-load failure
    uniformly while still distinguishing subtypes for fine-grained
    ``unable_reason`` mapping.

    Inherits from ``Exception`` (NOT ``RuntimeError`` or ``ValueError``)
    so it does NOT collide with ``SnapshotGraphMissing`` (the D2 graceful
    degradation signal that lives at
    ``snapshot_manager.SnapshotGraphMissingError`` since v1.1.6).
    """


class GraphMissing(GraphLoadError):  # noqa: N818
    """Raised when ``graph_json_path.exists() is False`` on the live path."""


# ---------- Protocol (REQ-DRIFT-DETECTION-1) ----------


@runtime_checkable
class GraphLoader(Protocol):
    """Narrow contract for a graph-loader collaborator.

    ``scan_change`` consumes a ``GraphLoader`` instead of inlining the
    graph-load logic. Runtime-checkable so ``isinstance(loader, GraphLoader)``
    works without explicit registration.
    """

    def load(self) -> tuple[dict | None, dict | None, float | None]:  # type: ignore[type-arg]
        """Return ``(current_nodes, current_id_map, graph_mtime)`` for the scan to consume."""
        ...


# ---------- Live-disk adapter (REQ-DRIFT-DETECTION-1 scenarios 1 + 2) ----------


class LiveDiskGraphLoader:
    """Adapter that wraps the current ``load_graph(graph_json_path)`` happy path.

    Concrete implementation of :class:`GraphLoader`. Reads from
    ``graph_json_path`` on the live disk. Raises ``GraphMissing`` /
    ``GraphMalformed`` / ``PermissionDenied`` (the typed exceptions
    added in T3.2).
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
            raise GraphMissing(  # PermissionDenied added in T3.2
                f"graph file unreadable (permission denied): {self._path}"
            ) from exc
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EPERM, errno.EROFS}:
                raise GraphMissing(  # PermissionDenied added in T3.2
                    f"graph file unreadable (errno={exc.errno}): {self._path}"
                ) from exc
            raise
        except json.JSONDecodeError as exc:
            raise GraphMissing(  # GraphMalformed added in T3.2
                f"graph file is not valid JSON: {self._path} "
                f"(line {exc.lineno}, col {exc.colno})"
            ) from exc
        if not isinstance(data, dict):
            raise GraphMissing(  # GraphMalformed added in T3.2
                f"graph file top-level is not an object: {self._path}"
            )
        nodes = data.get("nodes", [])
        if not isinstance(nodes, list):
            raise GraphMissing(  # GraphMalformed added in T3.2
                f"graph file 'nodes' field is not a list: {self._path}"
            )
        return _index_graph_payload(nodes, mtime)


# ---------- Helpers ----------


def _index_graph_payload(
    nodes: list[dict],  # type: ignore[type-arg]
    mtime: float | None,
) -> tuple[dict[str, dict] | None, dict[str, tuple[str, int, str]] | None, float | None]:  # type: ignore[type-arg]
    """Convert a raw ``graph.json`` ``nodes`` list into the index tuple.

    Mirrors the existing ``decision_drift._index_graph_payload`` (lines
    252-274). Tolerates both ``file/line`` and
    ``source_file/source_location`` node shapes.
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


_LINE_PATTERN = __import__("re").compile(r"\d+")


def _parse_line_for_loader(location: object) -> int:
    """Best-effort line-int coercion for graph.json schema variants."""
    if isinstance(location, int):
        return location
    if isinstance(location, str):
        m = _LINE_PATTERN.search(location)
        return int(m.group(0)) if m else 0
    return 0


__all__ = [
    "GraphLoadError",
    "GraphMissing",
    "GraphLoader",
    "LiveDiskGraphLoader",
]
