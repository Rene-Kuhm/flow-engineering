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
import time as _time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from flow_engineering.engram_io import EngramBackend


SNAPSHOT_SCHEMA_VERSION: int = 1
"""Bump when the envelope shape changes incompatibly."""

DEFAULT_GRAPH_JSON_PATH: Path = Path.home() / ".flow-engineering" / "graph.json"
"""Production default path for the graph.json correlator file.

Mirrors the cross-project-federation pattern at ``cli.py:DEFAULT_GRAPH_JSON``.
Tests override via the ``FLOW_GRAPH_JSON_PATH`` env var so the
``SnapshotManager.create()`` path under test is deterministic.
"""


# ---------- Exceptions + dataclasses ----------


class SnapshotEnvelopeError(Exception):
    """Raised when a snapshot envelope fails sha256 verification or has an
    unrecognised schema version.

    REQ-30 (show) MUST raise this rather than silently rendering a
    tampered envelope.
    """


class SnapshotGraphMissingError(Exception):
    """Raised when a snapshot envelope lacks the frozen ``graph.json`` content.

    REQ-33 D2 graceful degradation: a snapshot created against an
    Engram backend with no corresponding ``graph.json`` correlator file
    has no ``graph_state.graph_json_content`` field — a drift-pinned
    scan (``decision_drift.scan_change(snap_id=...)``) cannot classify
    bindings against a frozen graph, so it raises this exception rather
    than silently scanning against live disk (which would make
    ``--snapshot`` a no-op).

    Inherits from ``Exception`` per T1.5 brief. The
    ``flow_engineering.decision_drift`` module exposes a parallel class
    (``SnapshotGraphMissing(ValueError)``) for backwards compat with
    batch B1 BDD tests — the two are semantically equivalent and
    interchangeable from a caller's perspective.

    This is the canonical name (v1.1); the legacy
    :class:`SnapshotGraphMissing` is preserved as a 1-release alias and
    will be removed in v1.2.
    """


# 1-release alias (v1.1 follow-up per REQ-V1.1.6).
# Deprecated: use ``SnapshotGraphMissingError`` instead. The alias exists
# so v1.0 callers that imported ``SnapshotGraphMissing`` keep working
# until v1.2. Both names refer to the SAME class — there is no parallel
# hierarchy. DeprecationWarning fires at import time.
import contextlib  # noqa: E402
import warnings as _warnings  # noqa: E402


def __getattr__(name: str) -> object:
    """PEP 562 module-level __getattr__ for backward-compat aliases."""
    if name == "SnapshotGraphMissing":
        _warnings.warn(
            "SnapshotGraphMissing is deprecated; "
            "import SnapshotGraphMissingError instead. "
            "The alias will be removed in v1.2.",
            DeprecationWarning,
            stacklevel=2,
        )
        return SnapshotGraphMissingError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@dataclass(frozen=True)
class SnapshotMeta:
    """One row in ``SnapshotManager.list()`` output.

    The 6 keys mirror REQ-29 scenario 1's contract: ``snap_id``,
    ``created_at``, ``trigger``, ``description``, ``obs_count``,
    ``size_bytes``. Extra metadata (binding_count, project_count,
    include_graph, pinned) is exposed as dataclass fields so tests and
    BDD steps can introspect without re-reading the file.
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
    pinned: bool
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


@dataclass(frozen=True)
class PruneResult:
    """Outcome of a ``prune()`` invocation (REQ-34).

    Fields mirror the JSON contract ``{"deleted", "would_delete",
    "would_keep", "freed_bytes", "dry_run", "reason"}`` emitted by the
    ``flow snapshot prune`` CLI. The dataclass carries both the
    actually-applied deletions (``deleted``) AND the candidate set
    (``would_delete``/``would_keep``) so callers can inspect the policy
    decision before confirming it.

    - ``deleted``: snapshot ids actually removed from disk; ``[]`` in dry-run.
    - ``would_delete``: snapshot ids that WOULD be deleted if applied
      (mirrors ``deleted`` when ``confirm=True``).
    - ``would_keep``: snapshot ids the retention policy decided to KEEP,
      in oldest-first order.
    - ``freed_bytes``: total bytes the deletion set would free (== 0 in
      dry-run is permitted; equals the on-disk size sum when applied).
    - ``dry_run``: ``True`` when no files were touched.
    - ``reason``: ``"count"`` (keep_last), ``"age"`` (keep_days),
      ``"size"`` (max_total_size_mb), or ``""`` for no-op / no filter.
    """

    deleted: list[str]
    would_delete: list[str]
    would_keep: list[str]
    freed_bytes: int
    dry_run: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "deleted": list(self.deleted),
            "would_delete": list(self.would_delete),
            "would_keep": list(self.would_keep),
            "freed_bytes": int(self.freed_bytes),
            "dry_run": bool(self.dry_run),
            "reason": str(self.reason),
        }


class PruneNoFilterError(Exception):
    """Raised when ``prune()`` is called with no retention filter (REQ-34).

    REQ-34: at least one of ``keep_last`` / ``keep_days`` /
    ``max_total_size_mb`` MUST be supplied; the command refuses otherwise.
    """


class PruneSafetyGateError(Exception):
    """Raised when ``keep_last=0`` is missing the required safety flags.

    D10 two-flag safety gate: ``keep_last=0`` requires BOTH ``confirm=True``
    AND ``force=True``; without either, the operator's intent is ambiguous
    ("I meant 1, not 0"). The CLI surfaces this as a structured error so
    a CI pipeline can branch on exit code ``4``.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload.get("error", "--keep-last=0 requires --confirm and --force"))
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


def _resolve_graph_json_path() -> Path:
    """Return the path to read graph.json content from.

    Honour the ``FLOW_GRAPH_JSON_PATH`` env override (used by tests +
    parallel deploys); fall back to the production default
    ``~/.flow-engineering/graph.json``. Mirrors the
    ``_resolve_snapshots_dir`` pattern in ``decision_drift`` so the
    two paths stay in lockstep.
    """
    env = os.environ.get("FLOW_GRAPH_JSON_PATH")
    if env:
        return Path(env)
    return DEFAULT_GRAPH_JSON_PATH


def _read_graph_json_content() -> str | None:
    """Return the raw text content of ``graph.json``, or ``None`` when missing.

    T1.5 brief: ``SnapshotManager.create()`` MUST serialise the current
    ``graph.json`` content into ``envelope.graph_state.graph_json_content``
    (as a ``str``). When the file does not exist (test fixtures, fresh
    installs) the field is omitted from the envelope and
    ``decision_drift.scan_change(snap_id=...)`` raises
    ``SnapshotGraphMissing`` for drift-pinned scans (D2 graceful
    degradation).

    We deliberately return the RAW text (not a parsed dict) so the
    snapshot envelope preserves the exact on-disk bytes — the loader
    writes the string to a temp file and parses from there, which
    avoids subtle round-trip issues with key ordering or whitespace.
    """
    path = _resolve_graph_json_path()
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return None


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
        backend: EngramBackend,
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
            int(o["id"]): str(o.get("project", "insyd")) for o in observations if "id" in o
        }
        obs_count = len(observations)

        # Project set for the metadata count (D2: ``project_count``).
        project_count = len({p for p in project_tags.values() if p})

        # T1.5 brief: populate ``graph_state.graph_json_content`` from the
        # current ``graph.json`` correlator file (REQ-33 D2 default-on).
        # When the file is missing OR ``include_graph=False``, the field
        # is omitted; ``scan_change(snap_id=...)`` will then raise
        # ``SnapshotGraphMissing`` for drift-pinned scans (D2 graceful
        # degradation).
        graph_json_content = _read_graph_json_content() if include_graph else None

        graph_state: dict[str, Any] = {
            "observations": observations,
            "project_tags": project_tags,
        }
        if graph_json_content is not None:
            graph_state["graph_json_content"] = graph_json_content

        envelope: dict[str, Any] = {
            "schema": SNAPSHOT_SCHEMA_VERSION,
            "id": snap_id,
            "created_at": _now_iso_z(),
            "trigger": trigger,
            "description": effective_description,
            "graph_state": graph_state,
            "metadata": {
                "obs_count": obs_count,
                "project_count": project_count,
                "file_size_bytes": 0,
                "sha256": "",
                "include_graph": include_graph,
            },
        }

        # Compute sha256 over canonical-JSON WITHOUT the sha256 field.
        meta_for_hash = {k: v for k, v in envelope["metadata"].items() if k != "sha256"}
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
            meta_for_hash = {k: v for k, v in envelope["metadata"].items() if k != "sha256"}
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
                prefix=f".{snap_id}-",
                suffix=".json.gz.tmp",
                dir=str(self.snapshots_dir),
            )
            os.close(fd)
            tmp_path = Path(tmp_path_str)
            tmp_path.write_bytes(final_bytes)
            tmp_path.replace(target)
        except Exception:
            if tmp_path is not None:
                with contextlib.suppress(OSError):
                    tmp_path.unlink()
            raise

        # REQ-26 T1.7: emit snapshot_create_total after the atomic replace.
        # Fire AFTER the write so a failed write does NOT increment the
        # counter. The helper is fail-open and never raises.
        self._record_create_event(snap_id=snap_id)

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
            pinned=bool(meta.get("pinned", False)),
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
            raise SnapshotEnvelopeError(f"snapshot not found: {snap_id} (no file at {path})")
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
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = {k: v for k, v in meta.items() if k != "sha256"}
        expected_sha = hashlib.sha256(
            _canonical_json_dumps(envelope_for_hash).encode("utf-8")
        ).hexdigest()
        if stored_sha != expected_sha:
            raise SnapshotEnvelopeError(
                f"snapshot {snap_id} sha256 mismatch: stored={stored_sha!r}, "
                f"expected={expected_sha!r}"
            )

        return cast(dict[str, Any], envelope)

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
            index_b: dict[int, dict[str, Any]] = {int(o["id"]): o for o in obs_b_list if "id" in o}
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
                conflicts.append({"id": int(mod["id"]), "change": "modified"})
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

    def _record_create_event(self, *, snap_id: str) -> None:
        """Append one ``snapshot_create_total`` event to the metrics sink (REQ-26 T1.7).

        Best-effort via :func:`observability.record_snapshot_event` which
        swallows ``OSError``. Called by :meth:`create` AFTER the atomic
        write + rename so a failed write does NOT increment the counter.
        """
        from flow_engineering.observability import record_snapshot_event

        record_snapshot_event("snapshot_create_total", snap_id=str(snap_id))

    def _record_rollback_event(
        self,
        *,
        success: bool,
        safety_snap_id: str,
        target_snap_id: str,
    ) -> None:
        """Append one ``snapshot_rollback_total`` event to the metrics sink.

        Best-effort via :func:`observability.record_snapshot_event` which
        swallows ``OSError``. Fires on success AND on conflict/refusal so
        the audit trail captures attempted rollbacks (the counter's
        ``success`` label distinguishes them).
        """
        from flow_engineering.observability import record_snapshot_event

        record_snapshot_event(
            "snapshot_rollback_total",
            success="true" if success else "false",
            safety_snapshot_id=str(safety_snap_id),
            target_snapshot_id=str(target_snap_id),
        )

    # ----- prune ---------------------------------------------------------

    def prune(
        self,
        *,
        keep_last: int | None = None,
        keep_days: int | None = None,
        max_total_size_mb: int | None = None,
        confirm: bool = False,
        force: bool = False,
        now: float | None = None,
    ) -> PruneResult:
        """Retention-driven deletion of snapshot files (REQ-34, T1.6).

        At least ONE of ``keep_last`` / ``keep_days`` / ``max_total_size_mb``
        MUST be supplied; otherwise :class:`PruneNoFilterError` is raised.
        The three criteria are OR-combined: a snapshot is a candidate for
        deletion if ANY of them returns False.

        Default (``confirm=False``) is dry-run — ``PruneResult.dry_run`` is
        True and NO files are touched. With ``confirm=True``, the
        candidate set is deleted and the snapshot files are removed from
        disk.

        Two safety invariants are non-negotiable (enforced BEFORE
        candidates are computed):

        - The most-recent snapshot is NEVER deleted unless ``force=True``.
        - Snapshots whose ``metadata.pinned`` is True are NEVER deleted.

        Both invariants hold in dry-run too: pinned + most-recent snapshots
        are excluded from ``would_delete`` even when no actual deletion
        occurs.

        Args:
            keep_last: keep the N most-recent snapshots (by ``created_at``
                descending); delete the rest. ``0`` is allowed only with
                BOTH ``confirm=True`` AND ``force=True`` (D10 two-flag
                safety gate). ``0`` is mutually exclusive with
                ``keep_days`` and ``max_total_size_mb``.
            keep_days: keep snapshots with ``created_at >= now - keep_days``.
                Older snapshots are candidates for deletion.
            max_total_size_mb: delete oldest-first until the total
                snapshot directory size fits within the budget. Bytes
                that do not fit a whole snapshot are rounded down
                (i.e. the newest snapshot that pushes total over budget
                is kept).
            confirm: required ``True`` to actually delete; default
                ``False`` is dry-run.
            force: when ``True``, overrides the most-recent safety
                invariant and emits a loud stderr warning. Has NO effect
                on the pinned invariant (pinned snapshots are NEVER
                deleted).
            now: epoch seconds (float) used as the "current time" for
                ``keep_days``. Defaults to ``time.time()``. Exposed for
                test determinism.

        Returns:
            :class:`PruneResult` describing both the policy decision
            (``would_delete``, ``would_keep``) and the applied deletions
            (``deleted``, ``freed_bytes``).

        Raises:
            PruneNoFilterError: when no retention filter is supplied.
            PruneSafetyGateError: when ``keep_last=0`` is missing
                ``confirm=True`` or ``force=True``.
        """
        # Validation: at least one filter MUST be supplied.
        if keep_last is None and keep_days is None and max_total_size_mb is None:
            raise PruneNoFilterError(
                "at least one of --keep-last, --keep-days, --max-total-size-mb is required"
            )

        # D10 safety gate: keep_last=0 with confirm=True requires force=True.
        # The gate only fires in apply mode (confirm=True) — in dry-run,
        # the most-recent safety net below naturally excludes the newest
        # snapshot from would_delete, so dry-run prune(keep_last=0) is
        # safe and informative without requiring force=True.
        if keep_last == 0 and confirm and not force:
            raise PruneSafetyGateError(
                {
                    "error": (
                        "--keep-last=0 with --confirm requires --force; "
                        "this combination is irreversible and the "
                        "most-recent snapshot would be deleted"
                    ),
                    "keep_last": 0,
                }
            )

        # Resolve "now" once so keep_days + the safety-net age checks
        # share a single timestamp.
        if now is None:
            now = _time.time()

        # Enumerate snapshots oldest-first. The sort key is the envelope's
        # ``created_at`` (NOT the filename) because two snapshots created
        # within the same wall-clock second get the same ISO prefix and
        # differ only by the random hex suffix — the filename order would
        # be random in that case, but ``created_at`` order is stable. We
        # break ties by ``snap_id`` so the result is deterministic.
        files = sorted(self.snapshots_dir.glob("snap_*.json.gz"))
        metas: list[tuple[Path, SnapshotMeta]] = [(p, self._read_meta_header(p)) for p in files]
        metas.sort(key=lambda pm: (pm[1].created_at, pm[1].id))
        snap_ids_oldest_first = [m.id for _, m in metas]
        newest_meta = metas[-1][1] if metas else None
        newest_id = newest_meta.id if newest_meta else None

        # ---- Apply each filter, OR-combine the boolean masks ----
        # keep_mask[i] = True means "snapshot i is retained by this filter".
        keep_mask: list[bool] = [True] * len(metas)
        reason_label = ""

        if keep_last is not None:
            # Keep the N most-recent. With 5 metas and keep_last=2, we keep
            # the last 2 in the oldest-first list (== first 2 in
            # newest-first).
            n_retained = max(0, int(keep_last))
            for i in range(len(metas) - n_retained):
                keep_mask[i] = False
            reason_label = "count"

        if keep_days is not None:
            # Keep snapshots whose created_at >= now - keep_days.
            from datetime import datetime as _dt

            cutoff_epoch = now - (float(keep_days) * 86400.0)
            cutoff_iso = _dt.fromtimestamp(cutoff_epoch, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            for i, (_, m) in enumerate(metas):
                # The created_at is ISO 8601 with Z suffix; lexicographic
                # comparison against an ISO cutoff is correct for fixed-
                # length timestamps.
                if m.created_at < cutoff_iso:
                    keep_mask[i] = False
            reason_label = reason_label or "age"

        if max_total_size_mb is not None:
            # Walk oldest-first; if removing a snapshot keeps the
            # remaining total <= budget, mark it for deletion. Stop
            # when the budget is satisfied.
            budget_bytes = int(max_total_size_mb) * 1024 * 1024
            current_total = sum(p.stat().st_size for p, _ in metas)
            for i, (path, _) in enumerate(metas):
                if current_total <= budget_bytes:
                    break
                # We always protect the newest snapshot from size-based
                # eviction; otherwise the budget could force-delete the
                # most-recent file. This is enforced uniformly below
                # via the most_recent_id safety net.
                keep_mask[i] = False
                current_total -= path.stat().st_size
            reason_label = reason_label or "size"

        # Apply safety invariants AFTER the OR-combined filter.
        for i, (_, m) in enumerate(metas):
            # Pinned snapshots are NEVER deleted (force does NOT override).
            if m.pinned:
                keep_mask[i] = True
            # Most-recent snapshot is NEVER deleted unless force=True.
            if m.id == newest_id and not force:
                keep_mask[i] = True

        # Build the candidate set.
        would_delete = [snap_ids_oldest_first[i] for i, k in enumerate(keep_mask) if not k]
        would_keep = [snap_ids_oldest_first[i] for i, k in enumerate(keep_mask) if k]
        freed_bytes = sum(metas[i][0].stat().st_size for i, k in enumerate(keep_mask) if not k)

        # Dry-run short-circuit: no files touched, no counter emitted.
        if not confirm:
            return PruneResult(
                deleted=[],
                would_delete=would_delete,
                would_keep=would_keep,
                freed_bytes=0,
                dry_run=True,
                reason=reason_label,
            )

        # Apply: actually delete the candidate files. Emit a loud stderr
        # warning if force is overriding the most-recent safety net.
        newest_idx = len(metas) - 1 if metas else -1
        force_deletes_newest = (
            force
            and newest_idx >= 0
            and metas[newest_idx][1].id == newest_id
            and not keep_mask[newest_idx]
        )
        if force_deletes_newest:
            import sys

            print(
                "WARNING: --force override; most-recent snapshot was "
                "protected by default and is being deleted",
                file=sys.stderr,
            )

        actually_deleted: list[str] = []
        for i, k in enumerate(keep_mask):
            if k:
                continue
            path, m = metas[i]
            try:
                path.unlink()
                actually_deleted.append(m.id)
            except OSError:
                # If the file is already gone (concurrent prune), skip
                # silently. Any other OSError is best-effort: the
                # operator can re-run prune to retry.
                continue

        # Emit one snapshot_prune_total counter per deletion (mirrors
        # the rollback audit-trail pattern). The counter catalog
        # (SNAPSHOT_COUNTER_NAMES) is the source of truth (REQ-26 T1.7).
        for sid in actually_deleted:
            self._record_prune_event(reason=reason_label, snap_id=sid)

        return PruneResult(
            deleted=actually_deleted,
            would_delete=would_delete,
            would_keep=would_keep,
            freed_bytes=freed_bytes,
            dry_run=False,
            reason=reason_label,
        )

    def _record_prune_event(self, *, reason: str, snap_id: str) -> None:
        """Append one ``snapshot_prune_total`` event to the metrics sink (REQ-26 T1.7).

        Best-effort via :func:`observability.record_snapshot_event` which
        swallows ``OSError``. One event per deletion in apply mode
        (``confirm=True``); NOT fired in dry-run because dry-run
        short-circuits before this method is called.
        """
        from flow_engineering.observability import record_snapshot_event

        record_snapshot_event(
            "snapshot_prune_total",
            reason=str(reason or "count"),
            snap_id=str(snap_id),
        )


__all__ = [
    "SnapshotEnvelopeError",
    "SnapshotGraphMissingError",
    "SnapshotGraphMissing",  # noqa: F822
    "SnapshotMeta",
    "SnapshotDiff",
    "RollbackResult",
    "RollbackRefusedError",
    "RollbackConflictError",
    "PruneResult",
    "PruneNoFilterError",
    "PruneSafetyGateError",
    "SnapshotManager",
    "SNAPSHOT_SCHEMA_VERSION",
    "DEFAULT_GRAPH_JSON_PATH",
]
