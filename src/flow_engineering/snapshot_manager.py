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


@dataclass(frozen=True)
class RollbackResult:
    """Outcome of a successful ``rollback()`` invocation (REQ-32).

    Fields mirror the JSON contract ``{"safety_snapshot_id",
    "target_snapshot_id", "applied", "forced"}`` emitted by the
    ``flow snapshot rollback`` CLI on success.

    - ``safety_snapshot_id``: the auto-safety snapshot of CURRENT live
      state created BEFORE the destructive apply (Phase 1, D11).
    - ``target_snapshot_id``: the snapshot the caller asked to roll back
      TO (Phase 3).
    - ``applied``: diff summary string (e.g. ``"+1 -0 ~0"``).
    - ``forced``: True iff ``--force`` was passed AND conflicts existed.
    """

    safety_snapshot_id: str
    target_snapshot_id: str
    applied: str
    forced: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "safety_snapshot_id": self.safety_snapshot_id,
            "target_snapshot_id": self.target_snapshot_id,
            "applied": self.applied,
            "forced": self.forced,
        }


class RollbackRefusedError(Exception):
    """Raised when ``rollback()`` is called without ``confirm=True`` (REQ-32).

    The ``payload`` attribute is the JSON-serializable dict the CLI emits
    to stderr; the BDD step ``the rollback fails with refusal`` asserts
    on these exact keys.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload.get("error", "rollback refused"))
        self.payload = payload


class RollbackConflictError(Exception):
    """Raised when ``rollback()`` detects live-state divergence (REQ-32 D4).

    Conflicts = observations added / removed / modified between the
    target snapshot's ``created_at`` and now. The ``payload`` carries
    the conflict list so the CLI can render structured JSON to stderr
    and a CI pipeline can branch on exit code 2.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload.get("error", "rollback has conflicts"))
        self.payload = payload


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

    # ----- show ---------------------------------------------------------

    def show(self, snap_id: str) -> dict[str, Any]:
        """Return the parsed envelope for ``snap_id`` after sha256 verification.

        REQ-30: parses the gzipped JSON envelope, verifies
        ``metadata.sha256`` matches ``hashlib.sha256(canonical_json_dumps(
        envelope_without_sha256)).hexdigest()``. Raises
        :class:`SnapshotEnvelopeError` on any of: missing file, malformed
        JSON, schema version mismatch, sha256 mismatch.

        The returned dict is a deep copy of the parsed envelope — callers
        may mutate it without affecting the on-disk file.
        """
        path = self.snapshots_dir / f"{snap_id}.json.gz"
        if not path.exists():
            raise SnapshotEnvelopeError(
                f"snapshot not found: {snap_id} (no file at {path})"
            )
        try:
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                envelope = json.loads(fh.read())
        except (OSError, gzip.BadGzipFile, json.JSONDecodeError) as exc:
            raise SnapshotEnvelopeError(
                f"snapshot envelope unreadable for {snap_id}: {exc}"
            ) from exc

        schema = envelope.get("schema")
        if schema != SNAPSHOT_SCHEMA_VERSION:
            raise SnapshotEnvelopeError(
                f"snapshot {snap_id} has unknown schema version {schema!r}; "
                f"expected {SNAPSHOT_SCHEMA_VERSION}"
            )

        meta = envelope.get("metadata", {})
        stored_sha = meta.get("sha256", "")
        # Recompute sha256 over canonical-JSON WITHOUT the sha256 field.
        envelope_for_hash = {
            k: v for k, v in envelope.items() if k != "metadata"
        }
        envelope_for_hash["metadata"] = {
            k: v for k, v in meta.items() if k != "sha256"
        }
        expected_sha = hashlib.sha256(
            _canonical_json_dumps(envelope_for_hash).encode("utf-8")
        ).hexdigest()
        if stored_sha != expected_sha:
            raise SnapshotEnvelopeError(
                f"snapshot {snap_id} sha256 mismatch: stored={stored_sha!r}, "
                f"expected={expected_sha!r}"
            )

        return envelope

    # ----- diff ---------------------------------------------------------

    def diff(
        self,
        snap_id_a: str,
        snap_id_b: str | None = None,
    ) -> SnapshotDiff:
        """Diff ``snap_id_a`` against ``snap_id_b`` (or live state).

        REQ-31 + D9: returns a :class:`SnapshotDiff` with ``added``,
        ``removed``, ``modified``, ``unchanged_count``, and a human
        ``summary``. Two calling forms:

        - 2-arg form (``snap_id_b`` provided): compares two stored
          snapshots loaded via :meth:`show`.
        - 1-arg form (``snap_id_b`` omitted): compares the stored
          snapshot against the LIVE Engram state via
          ``backend.iter_observations()``.

        For ``modified`` entries, ``field`` is ``"content"`` whenever the
        ``content`` string differs; the value is compared as raw strings
        (D9 field-level diff is reserved for ``code_refs`` blocks in
        future batches — for now content-string compare is the canonical
        observation-level diff).
        """
        envelope_a = self.show(snap_id_a)
        if snap_id_b is None:
            obs_b_list = list(self.backend.iter_observations())
            index_b: dict[int, dict[str, Any]] = {
                int(o["id"]): o for o in obs_b_list if "id" in o
            }
        else:
            envelope_b = self.show(snap_id_b)
            obs_b_list = list(envelope_b.get("graph_state", {}).get("observations", []))
            index_b = {int(o["id"]): o for o in obs_b_list if "id" in o}
        obs_a_list = list(envelope_a.get("graph_state", {}).get("observations", []))
        index_a = {int(o["id"]): o for o in obs_a_list if "id" in o}

        ids_a = set(index_a)
        ids_b = set(index_b)
        added = sorted(ids_b - ids_a)
        removed = sorted(ids_a - ids_b)
        common = ids_a & ids_b

        modified: list[dict[str, Any]] = []
        unchanged_count = 0
        for obs_id in sorted(common):
            a_content = str(index_a[obs_id].get("content", ""))
            b_content = str(index_b[obs_id].get("content", ""))
            if a_content == b_content:
                unchanged_count += 1
                continue
            modified.append(
                {
                    "id": int(obs_id),
                    "field": "content",
                    "before": a_content,
                    "after": b_content,
                }
            )

        summary = f"+{len(added)} -{len(removed)} ~{len(modified)} (unchanged: {unchanged_count})"
        return SnapshotDiff(
            added=added,
            removed=removed,
            modified=modified,
            unchanged_count=unchanged_count,
            summary=summary,
        )

    # ----- rollback -----------------------------------------------------

    def rollback(
        self,
        snap_id: str,
        *,
        confirm: bool = False,
        force: bool = False,
    ) -> RollbackResult:
        """Restore live Engram state to match ``snap_id`` with safety net.

        REQ-32 + design D4 + D11 + D13. Two-phase commit pattern:

        - **Phase 0 (refuse without confirm)**. When ``confirm=False``,
          raise :class:`RollbackRefusedError` with the JSON contract
          ``{"error": "--confirm required to write; use --dry-run to
          preview", "snap_id": <id>}``. NO snapshot file is created and
          NO live writes occur — Phase 1 does not start.

        - **Phase 1 (auto-safety snapshot)**. When ``confirm=True``,
          ALWAYS call :meth:`create` with ``trigger="rollback_safety"``
          and ``description=f"pre_rollback_to_{snap_id}"`` so the user
          has a recoverable snapshot of CURRENT live state regardless of
          what happens next. The safety snapshot is created BEFORE
          conflict detection so a user who hits a conflict still has a
          one-command undo.

        - **Phase 2 (conflict detection)**. Compute the live-vs-snapshot
          diff. If ANY observation was added, removed, or modified since
          the target snapshot's ``created_at`` and ``force=False``,
          raise :class:`RollbackConflictError` with a JSON payload
          listing ``{"id": <n>, "change": "added|removed|modified"}``
          per conflict. Increments ``snapshot_rollback_total{success=
          "false"}`` (audit trail of attempted rollback).

        - **Phase 3 (apply)**. When conflicts exist AND ``force=True``,
          emit a loud stderr warning (``"WARNING: --force override;
          existing observations will be overwritten"``) BEFORE applying.
          Then call ``backend.mem_save`` for missing observations and
          ``backend.update_observation`` for content changes. The SQLite
          backend's ``BEGIN IMMEDIATE`` transaction makes the apply
          atomic — interrupt anywhere mid-apply rolls back atomically
          and the Phase 1 safety snapshot remains for manual recovery.

        Args:
            snap_id: The snapshot to roll back to. Must exist in
                ``snapshots_dir``.
            confirm: Required ``True`` to write. Default ``False``
                refuses with ``RollbackRefusedError``.
            force: When ``True``, overrides conflict detection and
                applies anyway. Default ``False``.

        Returns:
            :class:`RollbackResult` on success.

        Raises:
            RollbackRefusedError: When ``confirm=False``.
            RollbackConflictError: When conflicts exist and
                ``force=False``.
            SnapshotEnvelopeError: When ``snap_id`` is unknown or its
                envelope is corrupt (propagated from ``show()``).
        """
        # Phase 0: refuse without explicit confirm. Mirrors the
        # ``flow projects backfill --confirm`` safety contract from
        # cross-project-federation (REQ-24).
        if not confirm:
            raise RollbackRefusedError(
                {
                    "error": "--confirm required to write; use --dry-run to preview",
                    "snap_id": snap_id,
                }
            )

        # Phase 1: ALWAYS create the safety snapshot first (D11). Even
        # on conflict the user gets a one-command undo via
        # ``rollback(safety_snap_id)``.
        safety_snap_id = self.create(
            description=f"pre_rollback_to_{snap_id}",
            trigger="rollback_safety",
        )

        # Phase 2: detect conflicts by reusing the 1-arg ``diff`` form
        # (snapshot vs live). The existing ``diff`` is precisely the
        # added/removed/modified breakdown D4 specifies.
        diff = self.diff(snap_id)
        has_conflicts = bool(diff.added or diff.removed or diff.modified)

        if has_conflicts and not force:
            conflicts: list[dict[str, Any]] = []
            for cid in diff.added:
                conflicts.append({"id": int(cid), "change": "added"})
            for cid in diff.removed:
                conflicts.append({"id": int(cid), "change": "removed"})
            for mod in diff.modified:
                conflicts.append(
                    {"id": int(mod["id"]), "change": "modified"}
                )
            # Audit trail: even a refused rollback increments the counter.
            self._record_rollback_event(
                success=False,
                safety_snap_id=safety_snap_id,
                target_snap_id=snap_id,
            )
            raise RollbackConflictError(
                {
                    "error": "live state has diverged; refusing rollback without --force",
                    "conflicts": conflicts,
                    "safety_snapshot_id": safety_snap_id,
                }
            )

        # Phase 3: apply. When conflicts exist AND force=True, emit the
        # loud stderr warning AND increment the audit counter BEFORE
        # touching the backend.
        applied_forced = bool(has_conflicts and force)
        if applied_forced:
            import sys

            print(
                "WARNING: --force override; existing observations will be overwritten",
                file=sys.stderr,
            )
            self._record_rollback_event(
                success=False,
                safety_snap_id=safety_snap_id,
                target_snap_id=snap_id,
            )

        # Apply: restore the target snapshot's observation set into the
        # live backend. We use the existing EngramBackend interface:
        # ``mem_save`` for adds (new IDs may differ from snapshot, but
        # the content is restored), ``update_observation`` for content
        # changes on shared IDs. The SQLite backend wraps this in a
        # single ``BEGIN IMMEDIATE`` transaction so a crash mid-apply
        # rolls back atomically.
        self._apply_diff(snap_id)

        # Success path: increment the success counter and return.
        self._record_rollback_event(
            success=True,
            safety_snap_id=safety_snap_id,
            target_snap_id=snap_id,
        )
        return RollbackResult(
            safety_snapshot_id=safety_snap_id,
            target_snapshot_id=snap_id,
            applied=diff.summary,
            forced=applied_forced,
        )

    def _apply_diff(self, snap_id: str) -> None:
        """Restore the live backend to match the target snapshot's state.

        Best-effort via the EngramBackend interface:

        - For each observation in the target snapshot that is absent
          from live (added in target, removed from live), call
          ``backend.mem_save`` with the target's content. The new ID
          may differ from the snapshot's ID — this is a known
          limitation when the backend does not expose an ID-setting API.
        - For each observation present in both with different content,
          call ``backend.update_observation(id, content=target_content)``
          to restore the snapshot's content.

        ``removed`` (in live but not in target) cannot be undone via
        the standard backend interface — there is no public delete
        method on the EngramBackend ABC. We intentionally do NOT add
        one here; ``mem_save`` plus ``update_observation`` is the v1
        surface and the spec's "soft-delete via ``deleted_at``" is a
        future backend extension. The ``--force`` path is the
        operator's explicit acknowledgment of this limitation.
        """
        target_envelope = self.show(snap_id)
        target_obs: dict[int, dict[str, Any]] = {
            int(o["id"]): o
            for o in target_envelope.get("graph_state", {}).get("observations", [])
            if "id" in o
        }
        live_obs = {int(o["id"]): o for o in self.backend.iter_observations() if "id" in o}

        # Adds: re-create via mem_save.
        for tid, target_o in target_obs.items():
            if tid not in live_obs:
                self.backend.mem_save(
                    title=str(target_o.get("title", f"restored-{tid}")),
                    content=str(target_o.get("content", "")),
                    topic_key=str(target_o.get("topic_key", f"sdd/restored/{tid}")),
                )

        # Modifies: rewrite content via update_observation.
        for tid, target_o in target_obs.items():
            if tid in live_obs:
                target_content = str(target_o.get("content", ""))
                live_content = str(live_obs[tid].get("content", ""))
                if target_content != live_content:
                    self.backend.update_observation(tid, content=target_content)

    def _record_rollback_event(
        self,
        *,
        success: bool,
        safety_snap_id: str,
        target_snap_id: str,
    ) -> None:
        """Append one ``snapshot_rollback_total`` event to the metrics sink.

        Best-effort: the call goes through :func:`observability.increment`
        which swallows ``OSError``. The counter catalog
        (``SNAPSHOT_COUNTER_NAMES``) is defined in batch C (T1.7) — until
        then we use the raw ``increment`` with the known counter name
        string. This keeps the rollback observability contract from REQ-32
        working even before the catalog lands.
        """
        # Local import to avoid a top-level cycle with the snapshot
        # module. observability has no dependency on snapshot_manager.
        from flow_engineering.observability import increment

        increment(
            "snapshot_rollback_total",
            success="true" if success else "false",
            safety_snapshot_id=safety_snap_id,
            target_snapshot_id=target_snap_id,
        )


__all__ = [
    "SnapshotEnvelopeError",
    "SnapshotMeta",
    "SnapshotDiff",
    "RollbackResult",
    "RollbackRefusedError",
    "RollbackConflictError",
    "SnapshotManager",
    "SNAPSHOT_SCHEMA_VERSION",
]
