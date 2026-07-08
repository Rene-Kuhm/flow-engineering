"""Typed graph-load exception hierarchy (REQ-DRIFT-DETECTION-4).

Slice 1 (T3.2) of the drift-detection change. Extracted from
``drift_graph_loader.py`` per user's task D10 override of the design's
co-location choice (design.md §2 had the 4 typed exceptions co-located
with the GraphLoader adapters; the standalone module keeps the public
graph-loader surface grep-able and the per-finding extension point at
Slice 3 well-located).

Hierarchy
---------

::

    GraphLoadError (Exception)
    ├── GraphMissing            # errno=ENOENT / path.exists() == False
    ├── GraphMalformed          # JSONDecodeError + shape mismatch
    ├── PermissionDenied        # OSError errno in {EACCES, EPERM, EROFS}
    └── SnapshotEnvelopeCorrupt # SnapshotManager.show() raised SnapshotEnvelopeError

All 4 inherit from ``Exception`` (NOT ``RuntimeError`` or ``ValueError``)
per REQ-DRIFT-DETECTION-4. This keeps the type system orthogonal to the
``SnapshotGraphMissingError(Exception)`` D2 graceful degradation signal
at ``snapshot_manager.SnapshotGraphMissingError`` (since v1.1.6) — that
exception stays a distinct ``raise`` at the scan boundary, NOT mapped
to ``unable_reason``.

The 4 are siblings (no parent-child relationships) because the 4
failure modes are mutually exclusive: a path is either missing, or it
exists and is malformed, or it exists and is unreadable due to
permissions, or it's a snapshot envelope that failed sha256.
"""


class GraphLoadError(Exception):
    """Base class for typed graph-load failures.

    All typed exceptions below inherit from this base so callers can
    catch ``except GraphLoadError`` to handle ANY graph-load failure
    uniformly while still distinguishing subtypes for fine-grained
    ``unable_reason`` mapping.
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
    CORRUPT (sha256 mismatch) without being MISSING (``--no-include-graph``
    at create time). ``unable_reason`` maps to
    ``"snapshot_envelope_corrupt"``.
    """


__all__ = [
    "GraphLoadError",
    "GraphMissing",
    "GraphMalformed",
    "PermissionDenied",
    "SnapshotEnvelopeCorrupt",
]
