"""Snapshot subsystem for flow-engineering (REQ-28 + REQ-29, T1.1).

REQ-28 + REQ-29 (graph-snapshots change #5): additive immutable gzipped JSON
snapshot files written to ``snapshots_dir``. Each snapshot captures the
full Engram state at the moment of creation plus a sha256 stamp over the
canonicalized JSON envelope for tamper detection.

## Design references

- **D1** (SnapshotManager API) — single class with ``create`` + ``list``
  in v1 batch A; ``show``, ``diff``, ``rollback``, ``prune`` extend the
  class in later batches.
- **D2** (envelope schema v1) — ``{schema, id, created_at, trigger,
  description, graph_state: {...}, metadata: {...sha256...}}``.
- **D7** (snapshot id naming) — ``snap_<ISO>-<6hex>.json.gz`` where ISO
  uses ``-`` instead of ``:`` (filesystem-safe) and the hex suffix is
  ``secrets.token_hex(3)`` (collision-safe on sub-second creates).
- **D9** (sha256 over canonical JSON) — sorted keys + ``separators=(",",
  ":")`` so the hash is deterministic across gzip implementations.
- **D11** (atomic write) — ``tempfile.NamedTemporaryFile`` + ``Path.replace``
  so a mid-write crash cannot corrupt the directory.

## Public surface

- ``SnapshotEnvelopeError`` — raised on sha256 / schema mismatch (REQ-30).
- ``SnapshotMeta`` — frozen dataclass for ``list()`` entries.
- ``SnapshotDiff`` — frozen dataclass for ``diff()`` returns (REQ-31).
- ``SnapshotManager(snapshots_dir, backend)`` — constructor lazy-creates
  ``snapshots_dir``.
- ``SnapshotManager.create(description="", *, trigger="manual", ...)``
  — write one snapshot, return its ``snap_id``.
- ``SnapshotManager.list(*, since=None, limit=None)`` — newest-first
  list of ``SnapshotMeta`` records.

CLI surface (``flow snapshot {create,list,...}``) and the remaining
methods (``show``, ``diff``, ``rollback``, ``prune``) land in later
tasks. This file is the foundation that everything else builds on.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import secrets
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flow_engineering.engram_io import EngramBackend


SNAPSHOT_SCHEMA_VERSION: int = 1
"""Bump when the envelope shape changes incompatibly."""


# ---------- Exceptions + dataclasses ----------


class SnapshotEnvelopeError(Exception):
    """Raised when a snapshot envelope fails sha256 verification or has an
    unrecognised schema version.

    REQ-30 (show) MUST raise this rather than silently rendering a
    tampered envelope.
    """


@dataclass(frozen=True)
class SnapshotMeta:
    """One row in ``SnapshotManager.list()`` output.

    The 6 keys mirror REQ-29 scenario 1's contract: ``snap_id``,
    ``created_at``, ``trigger``, ``description``, ``obs_count``,
    ``size_bytes``. Extra metadata (binding_count, project_count,
    include_graph) is exposed as dataclass fields so tests and BDD steps
    can introspect without re-reading the file.
    """

    id: str
    created_at: str
    trigger: str
    description: str
    obs_count: int
    binding_count: int
    project_count: int
    size_bytes: int
    include_graph: bool
    path: Path


@dataclass(frozen=True)
class SnapshotDiff:
    """Structured diff between two snapshots (or snapshot + live state).

    REQ-31 + design D9: ``added`` + ``removed`` are observation id lists;
    ``modified`` is a list of ``{id, field, before, after}`` dicts where
    ``field`` is the parsed binding field name (e.g.
    ``code_refs.bound_id.file``) for ``code_refs`` blocks (block-level
    diff, NOT raw content diff). ``unchanged_count`` is the count of
    observations whose content is byte-identical between ``a`` and ``b``.
    """

    added: list[int]
    removed: list[int]
    modified: list[dict[str, Any]]
    unchanged_count: int
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": list(self.added),
            "removed": list(self.removed),
            "modified": list(self.modified),
            "unchanged_count": self.unchanged_count,
            "summary": self.summary,
        }


# ---------- Internal helpers ----------


def _canonical_json_dumps(obj: dict[str, Any]) -> str:
    """Serialize ``obj`` as canonical JSON (sorted keys, no whitespace).

    D9 — the sha256 stamp MUST be over this representation so the
    fingerprint is deterministic regardless of gzip implementation.
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now_iso_filesafe() -> str:
    """Return the current UTC time in the filesystem-safe ISO format.

    D7: ``YYYY-MM-DDTHH-MM-SS`` (dashes instead of colons) so the value
    is a legal filename on Windows + POSIX without escaping.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")


def _now_iso_z() -> str:
    """Return the current UTC time as ISO 8601 with ``Z`` suffix (display)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_snapshot_id() -> str:
    """Return a fresh snapshot id ``snap_<ISO>-<6hex>``.

    D7: the 6-hex-char suffix is ``secrets.token_hex(3)`` so simultaneous
    creates on the same second do not collide. The ISO part uses
    filesystem-safe dashes (D7).
    """
    iso = _now_iso_filesafe()
    hex_suffix = secrets.token_hex(3)  # 3 bytes = 6 hex chars
    return f"snap_{iso}-{hex_suffix}"


# ---------- SnapshotManager ----------


class SnapshotManager:
    """File-system facade for snapshot creation + listing (REQ-28 + REQ-29).

    Reads flow through ``backend.iter_observations()``; writes go to
    ``snapshots_dir`` as gzipped JSON. Constructor takes a
    ``snapshots_dir`` (Path) and a backend reference; it lazy-creates
    ``snapshots_dir`` so callers don't have to mkdir first.

    v1 batch A exposes ``create()`` + ``list()``. The remaining methods
    (``show``, ``diff``, ``rollback``, ``prune``) land in later batches
    and extend the same class — there is no API split, only
    functionality staged across the apply batches.
    """

    def __init__(
        self,
        snapshots_dir: Path,
        backend: "EngramBackend",
    ) -> None:
        self.snapshots_dir = Path(snapshots_dir)
        self.backend = backend
        # D11: lazy-create the directory so a constructor never fails on
        # a missing parent. ``mkdir(parents=True, exist_ok=True)`` is
        # idempotent and atomic per directory entry.
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    # ----- create -------------------------------------------------------

    def create(
        self,
        description: str = "",
        *,
        trigger: str = "manual",
        include_graph: bool = True,
    ) -> str:
        """Write one snapshot envelope; return the ``snap_id``.

        Steps (D2 + D9 + D11):

        1. Generate ``snap_<ISO>-<6hex>`` id (D7, collision-safe).
        2. Read full graph state from the backend via
           ``iter_observations()``. The envelope stores the FULL DB at
           creation time (D5); the ``--project=<key>`` flag is a
           read-time filter only.
        3. Resolve description: when ``snapshots_dir`` is empty AND no
           explicit description was passed, auto-label ``initial_state``
           (Q10 resolution). Explicit description always wins.
        4. Build the envelope WITHOUT the sha256 field, serialize to
           canonical JSON, compute sha256.
        5. Inject the sha256 into ``metadata``.
        6. Atomic write: temp file in the same directory + ``Path.replace``
           so a crash mid-write cannot corrupt the directory.
        """
        snap_id = _build_snapshot_id()

        # Auto-label ``initial_state`` only on the first run AND when the
        # caller did NOT pass an explicit description. Q10 resolution.
        effective_description = description
        if not description and not any(self.snapshots_dir.glob("snap_*.json.gz")):
            effective_description = "initial_state"

        observations = list(self.backend.iter_observations())
        project_tags = {
            int(o["id"]): str(o.get("project", "insyd"))
            for o in observations
            if "id" in o
        }
        obs_count = len(observations)

        # Project set for the metadata count (D2: ``project_count``).
        project_count = len({p for p in project_tags.values() if p})

        envelope: dict[str, Any] = {
            "schema": SNAPSHOT_SCHEMA_VERSION,
            "id": snap_id,
            "created_at": _now_iso_z(),
            "trigger": trigger,
            "description": effective_description,
            "graph_state": {
                "observations": observations,
                "project_tags": project_tags,
            },
            "metadata": {
                "obs_count": obs_count,
                "project_count": project_count,
                "file_size_bytes": 0,
                "sha256": "",
                "include_graph": include_graph,
            },
        }

        # Compute sha256 over canonical-JSON WITHOUT the sha256 field.
        meta_for_hash = {
            k: v for k, v in envelope["metadata"].items() if k != "sha256"
        }
        envelope_for_hash = dict(envelope)
        envelope_for_hash["metadata"] = meta_for_hash
        canonical = _canonical_json_dumps(envelope_for_hash)
        sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        envelope["metadata"]["sha256"] = sha

        # Atomic write: gzip to a temp file in the same directory, then
        # ``Path.replace`` for atomic rename. We serialize the canonical
        # JSON ONCE, measure the gzipped size, then write the final
        # envelope (with size + sha256 stamped) in a single pass.
        target = self.snapshots_dir / f"{snap_id}.json.gz"
        tmp_path: Path | None = None
        try:
            canonical_bytes = _canonical_json_dumps(envelope).encode("utf-8")
            gzipped = gzip.compress(canonical_bytes, mtime=0)
            envelope["metadata"]["file_size_bytes"] = len(gzipped)
            # Recompute sha256 with the final ``file_size_bytes`` so the
            # on-disk fingerprint matches the bytes written.
            meta_for_hash = {
                k: v for k, v in envelope["metadata"].items() if k != "sha256"
            }
            envelope_for_hash = dict(envelope)
            envelope_for_hash["metadata"] = meta_for_hash
            sha = hashlib.sha256(
                _canonical_json_dumps(envelope_for_hash).encode("utf-8")
            ).hexdigest()
            envelope["metadata"]["sha256"] = sha
            final_bytes = gzip.compress(
                _canonical_json_dumps(envelope).encode("utf-8"),
                mtime=0,
            )
            # Write to a temp file in the same directory. ``NamedTemporaryFile``
            # with ``delete=False`` is portable across POSIX + Windows; we
            # close it before ``Path.replace`` to release the file handle.
            fd, tmp_path_str = tempfile.mkstemp(
                prefix=f".{snap_id}-", suffix=".json.gz.tmp",
                dir=str(self.snapshots_dir),
            )
            os.close(fd)
            tmp_path = Path(tmp_path_str)
            tmp_path.write_bytes(final_bytes)
            tmp_path.replace(target)
        except Exception:
            if tmp_path is not None:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise

        return snap_id

    # ----- list ---------------------------------------------------------

    def list(
        self,
        *,
        since: str | None = None,
        limit: int | None = None,
    ) -> list[SnapshotMeta]:
        """Return newest-first list of ``SnapshotMeta``.

        Ordering is by ``created_at`` descending; ties are broken by id
        descending (the 6-hex suffix is treated as a tie-breaker so
        same-second creates still have a deterministic order).

        ``since`` filters to snapshots with ``created_at >= since``
        (lexicographic; the timestamp is ISO 8601 with ``Z`` suffix,
        which is sort-safe as a string). ``limit`` truncates to the N
        most recent AFTER applying ``since``.
        """
        files = sorted(self.snapshots_dir.glob("snap_*.json.gz"))
        # Reverse to newest-first; files are named chronologically.
        files.reverse()

        entries: list[SnapshotMeta] = []
        for path in files:
            meta = self._read_meta_header(path)
            if since is not None and meta.created_at < since:
                continue
            entries.append(meta)
            if limit is not None and len(entries) >= limit:
                break
        return entries

    def _read_meta_header(self, path: Path) -> SnapshotMeta:
        """Read just enough of the envelope to populate a ``SnapshotMeta``.

        We open the gzip, parse the JSON, and extract the fields. The
        full envelope is preserved for ``show()`` (REQ-30) to return.
        """
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            envelope = json.loads(fh.read())
        graph_state = envelope.get("graph_state", {})
        observations = graph_state.get("observations", [])
        project_tags = graph_state.get("project_tags", {})
        meta = envelope.get("metadata", {})
        return SnapshotMeta(
            id=str(envelope.get("id", path.stem)),
            created_at=str(envelope.get("created_at", "")),
            trigger=str(envelope.get("trigger", "manual")),
            description=str(envelope.get("description", "")),
            obs_count=int(meta.get("obs_count", len(observations))),
            binding_count=int(meta.get("binding_count", 0)),
            project_count=int(
                meta.get("project_count", len({p for p in project_tags.values() if p}))
            ),
            size_bytes=int(meta.get("file_size_bytes", path.stat().st_size)),
            include_graph=bool(meta.get("include_graph", True)),
            path=path,
        )


__all__ = [
    "SnapshotEnvelopeError",
    "SnapshotMeta",
    "SnapshotDiff",
    "SnapshotManager",
    "SNAPSHOT_SCHEMA_VERSION",
]
