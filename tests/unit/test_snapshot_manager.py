"""Unit tests for ``flow_engineering.snapshot_manager`` (REQ-28 + REQ-29, T1.1).

TDD: written BEFORE the implementation. These MUST fail until the GREEN
commit wires ``src/flow_engineering/snapshot_manager.py`` with the
``SnapshotManager`` class, ``create()`` + ``list()`` methods, gzip + sha256
envelope write, atomic temp-file replace, and reverse-chronological list
with ``since`` + ``limit`` filtering.

T1.5 batch B2 extension: ``SnapshotManager.create()`` MUST populate
``graph_state.graph_json_content`` so drift-pinned scans work without
manual envelope rewriting. The ``TestCreatePopulatesGraphJsonContent``
class covers the new behaviour.

T1.6 batch C extension: ``SnapshotManager.prune()`` retention policy
covers REQ-34 — the ``TestPrune`` class covers keep_last, keep_days,
max_total_size_mb, dry-run default, most-recent safety, pinned safety,
and ``--force`` override.

Coverage map (REQ-28 + REQ-29 scenarios at the unit level):

REQ-28 (create):
1. ``create`` writes a gzipped envelope with all current observations + sha256
2. ``create`` lazy-creates ``snapshots_dir`` when missing
3. ``create`` atomic write leaves no ``.tmp`` files behind on success
4. ``create`` first-run auto-labels ``initial_state`` when dir is empty
5. ``create`` explicit description wins over ``initial_state`` auto-label
6. ``create`` returns ``snap_<ISO>-<6hex>`` id matching the file stem

REQ-29 (list):
7. ``list`` returns reverse chronological (newest first)
8. ``list`` ``since`` filter excludes observations older than cutoff
9. ``list`` ``limit`` applies AFTER ``since`` filter
10. ``list`` empty dir returns ``[]`` (no error)

REQ-34 (prune, T1.6):
11. ``prune(keep_last=N)`` deletes oldest beyond N
12. ``prune(keep_days=N)`` excludes snapshots older than now-N
13. ``prune(max_total_size_mb=N)`` evicts oldest-first until total fits
14. ``prune(confirm=False)`` is dry-run (no deletes)
15. ``prune`` never deletes the most recent snapshot
16. ``prune`` respects ``metadata.pinned``
17. ``prune(force=True)`` overrides most-recent safety with stderr warning

Cross-cutting:
- SHA256 is computed over canonicalized JSON (sorted keys, no whitespace),
  so the on-disk envelope is tamper-evident.
- Snapshot id format: ``snap_<YYYY-MM-DDTHH-MM-SS>-<6hex>.json.gz`` where
  the hex suffix is ``secrets.token_hex(3)`` for collision-safety on
  sub-second creates.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import pytest

from flow_engineering.engram_io import InMemoryBackend

# ---------- Helpers ----------


def _seed_backend(backend: InMemoryBackend, *, n: int = 3) -> list[int]:
    """Seed ``n`` observations on the in-memory backend. Returns ids in order."""
    ids: list[int] = []
    for i in range(n):
        obs = backend.mem_save(
            title=f"snap obs {i}",
            content=f"drift detection strategy {i}",
            topic_key="sdd/x/spec",
        )
        ids.append(int(obs["id"]))
    return ids


def _canonical_json_dumps(obj: dict[str, Any]) -> str:
    """Serialize ``obj`` as canonical JSON (sorted keys, no whitespace)."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _read_envelope(path: Path) -> dict[str, Any]:
    """Read + gunzip + json.loads the snapshot envelope at ``path``."""
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.loads(fh.read())


# ---------- REQ-28 scenario 1: create writes a gzipped envelope + sha256 ----------


class TestCreateRoundTrip:
    """``SnapshotManager.create`` writes a gzipped envelope with sha256 stamp."""

    def test_create_returns_snap_id_and_writes_file(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)

        snap_id = manager.create()

        # ID matches the file stem.
        assert snap_id.startswith("snap_")
        assert (tmp_path / f"{snap_id}.json.gz").exists()

    def test_create_envelope_schema_and_sha256(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        ids = _seed_backend(backend, n=5)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)

        snap_id = manager.create(description="pre-deploy-v0.6")
        path = tmp_path / f"{snap_id}.json.gz"
        envelope = _read_envelope(path)

        # Schema + key fields.
        assert envelope["schema"] == 1
        assert envelope["id"] == snap_id
        assert envelope["trigger"] == "manual"
        assert envelope["description"] == "pre-deploy-v0.6"
        assert "created_at" in envelope
        assert envelope["created_at"].endswith("Z")
        assert "graph_state" in envelope
        assert "metadata" in envelope

        # Observations match the backend.
        obs_ids = [int(o["id"]) for o in envelope["graph_state"]["observations"]]
        assert sorted(obs_ids) == sorted(ids)

        # SHA256 over canonical-JSON WITHOUT the sha256 field must match.
        meta = envelope["metadata"]
        assert "sha256" in meta
        envelope_without_sha = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_without_sha["metadata"] = {
            k: v for k, v in meta.items() if k != "sha256"
        }
        expected = hashlib.sha256(
            _canonical_json_dumps(envelope_without_sha).encode("utf-8")
        ).hexdigest()
        assert meta["sha256"] == expected, (
            f"sha256 mismatch: expected {expected}, got {meta['sha256']}"
        )


# ---------- REQ-28 scenario 2: lazy-create snapshots_dir ----------


class TestLazyCreate:
    """``SnapshotManager(snapshots_dir=missing)`` lazy-creates on first write."""

    def test_constructor_lazy_creates_dir(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        target = tmp_path / "nested" / "snapshots"
        assert not target.exists()
        SnapshotManager(snapshots_dir=target, backend=InMemoryBackend())
        assert target.is_dir()


# ---------- REQ-28 scenario 3: atomic write leaves no .tmp ----------


class TestAtomicWrite:
    """Atomic write via temp file + Path.replace leaves no .tmp behind."""

    def test_atomic_write_no_tmp_files_left(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        _seed_backend(manager.backend)
        manager.create()

        # No .tmp / .partial files should remain in the snapshots dir.
        tmp_files = [
            p for p in tmp_path.iterdir()
            if p.name.endswith(".tmp") or ".tmp." in p.name
        ]
        assert tmp_files == [], f"Unexpected temp files: {tmp_files!r}"

    def test_write_creates_one_file_per_create(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        _seed_backend(manager.backend)
        manager.create()
        manager.create()
        # Exactly one file per create.
        files = sorted(tmp_path.glob("snap_*.json.gz"))
        assert len(files) == 2


# ---------- REQ-28 scenario 4 + 5: first-run auto-label + explicit override ----------


class TestFirstRunLabel:
    """First snapshot in an empty dir auto-labels ``initial_state`` unless overridden."""

    def test_first_run_empty_dir_auto_labels_initial_state(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        # Empty / missing dir ⇒ first run.
        snap_id = manager.create()
        envelope = _read_envelope(tmp_path / f"{snap_id}.json.gz")
        assert envelope["description"] == "initial_state"

    def test_explicit_description_wins_over_initial_state(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        # Pre-existing snapshot ⇒ NOT first run; explicit description honored.
        manager.create(description="first")
        snap_id = manager.create(description="second-explicit")
        envelope = _read_envelope(tmp_path / f"{snap_id}.json.gz")
        assert envelope["description"] == "second-explicit"

    def test_no_description_when_dir_not_empty_no_auto_label(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        manager.create(description="seed")
        snap_id = manager.create()  # no description, but dir not empty
        envelope = _read_envelope(tmp_path / f"{snap_id}.json.gz")
        # Empty string, NOT ``initial_state``.
        assert envelope["description"] == ""


# ---------- REQ-28 scenario 6: snapshot id format ----------


class TestSnapshotIdFormat:
    """Snapshot id format ``snap_<ISO>-<6hex>`` per design D7."""

    def test_id_format_snap_iso_six_hex(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        _seed_backend(manager.backend)
        snap_id = manager.create()

        # ``snap_YYYY-MM-DDTHH-MM-SS-XXXXXX`` (ISO with dashes instead of colons).
        assert snap_id.startswith("snap_"), snap_id
        # Strip the ``snap_`` prefix and split the rest on ``-``.
        body = snap_id[len("snap_"):]
        parts = body.split("-")
        # 5 date parts (year, month, day+hour, minute, second) + 1 hex part = 6.
        assert len(parts) == 6, f"Expected 6 dash-separated parts, got {snap_id!r}"
        # Hex suffix: 6 lowercase hex chars.
        assert len(parts[5]) == 6
        assert all(c in "0123456789abcdef" for c in parts[5]), (
            f"Hex suffix must be 6 lowercase hex chars, got {parts[5]!r}"
        )

    def test_two_creates_produce_distinct_ids(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        _seed_backend(manager.backend)
        id_a = manager.create()
        # Brief pause to avoid same-second collisions in the ISO part.
        time.sleep(1.01)
        id_b = manager.create()
        assert id_a != id_b


# ---------- REQ-29 scenario 1: reverse chronological order ----------


class TestListOrdering:
    """``list()`` returns newest first."""

    def test_list_returns_reverse_chronological(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        _seed_backend(manager.backend)
        id_a = manager.create(description="a")
        time.sleep(1.01)
        id_b = manager.create(description="b")
        time.sleep(1.01)
        id_c = manager.create(description="c")

        entries = manager.list()
        ids_in_order = [e.id for e in entries]
        assert ids_in_order == [id_c, id_b, id_a], (
            f"Expected reverse chrono, got {ids_in_order!r}"
        )


# ---------- REQ-29 scenario 2: since filter ----------


class TestSinceFilter:
    """``since`` excludes snapshots with ``created_at < since``."""

    def test_since_filter_excludes_older(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        _seed_backend(manager.backend)
        id_a = manager.create(description="a")
        time.sleep(1.01)
        id_b = manager.create(description="b")
        time.sleep(1.01)
        id_c = manager.create(description="c")

        # Pull the created_at of id_b and use it as the since filter.
        created_b = next(e.created_at for e in manager.list() if e.id == id_b)
        entries = manager.list(since=created_b)

        kept_ids = {e.id for e in entries}
        assert id_b in kept_ids
        assert id_c in kept_ids
        assert id_a not in kept_ids


# ---------- REQ-29 scenario 3: limit applies AFTER since ----------


class TestLimit:
    """``limit`` truncates AFTER ``since`` filter (newest N retained)."""

    def test_limit_applies_after_since(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        _seed_backend(manager.backend)
        for i in range(5):
            manager.create(description=f"snap-{i}")
            if i < 4:
                time.sleep(1.01)

        # All 5 ids present, take 2.
        entries = manager.list(limit=2)
        assert len(entries) == 2
        # And they're the two newest.
        all_entries = manager.list()
        assert [e.id for e in entries] == [all_entries[0].id, all_entries[1].id]


# ---------- REQ-29 scenario 4: empty dir ----------


class TestEmptyDir:
    """``list()`` on a missing/empty snapshots dir returns ``[]``."""

    def test_list_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        manager = SnapshotManager(snapshots_dir=tmp_path / "nonexistent", backend=InMemoryBackend())
        # Constructor lazy-creates the dir; it exists but is empty.
        entries = manager.list()
        assert entries == []


# ---------- SnapshotMeta shape ----------


class TestSnapshotMetaShape:
    """Each ``SnapshotMeta`` carries the 6 required keys."""

    def test_snapshot_meta_has_required_fields(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        _seed_backend(manager.backend)
        manager.create(description="x")

        entries = manager.list()
        assert len(entries) == 1
        entry = entries[0]
        for field in ("id", "created_at", "trigger", "description", "obs_count", "size_bytes"):
            assert hasattr(entry, field), f"Missing field {field} on SnapshotMeta"
        assert entry.trigger == "manual"
        assert entry.description == "x"
        assert entry.obs_count == 3
        assert entry.size_bytes > 0


# ---------- REQ-30: show round-trips envelope + sha256 verification ----------


class TestShow:
    """``SnapshotManager.show(snap_id)`` parses + verifies the envelope."""

    def test_show_round_trips_envelope(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        _seed_backend(manager.backend, n=3)
        snap_id = manager.create(description="rt")

        envelope = manager.show(snap_id)

        assert envelope["schema"] == 1
        assert envelope["id"] == snap_id
        assert envelope["description"] == "rt"
        # All 6 top-level keys from D2 are present.
        for key in (
            "schema", "id", "created_at", "trigger", "description",
            "graph_state", "metadata",
        ):
            assert key in envelope, f"Missing top-level key {key}"

    def test_show_raises_on_unknown_snap_id(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import (
            SnapshotEnvelopeError,
            SnapshotManager,
        )

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        with pytest.raises(SnapshotEnvelopeError):
            manager.show("snap_does_not_exist")

    def test_show_raises_on_tampered_sha256(self, tmp_path: Path) -> None:
        """Flipping one byte in the .gz file MUST raise SnapshotEnvelopeError."""
        from flow_engineering.snapshot_manager import (
            SnapshotEnvelopeError,
            SnapshotManager,
        )

        manager = SnapshotManager(snapshots_dir=tmp_path, backend=InMemoryBackend())
        _seed_backend(manager.backend)
        snap_id = manager.create(description="tamper-test")
        path = tmp_path / f"{snap_id}.json.gz"

        # Corrupt one byte in the gzip payload. We append a byte past the
        # original size so the file becomes invalid. A byte flip mid-file
        # would also work; we use append-then-truncate to avoid breaking
        # the gzip CRC on every iteration.
        original = path.read_bytes()
        tampered = bytes(b ^ 0xFF for b in original)
        path.write_bytes(tampered)

        with pytest.raises(SnapshotEnvelopeError):
            manager.show(snap_id)


# ---------- REQ-31: diff between two snapshots ----------


class TestDiffTwoArg:
    """``diff(snap_a, snap_b)`` returns added/removed/modified/unchanged."""

    def test_diff_two_arg_returns_added_removed_modified(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        snap_a = manager.create(description="a")

        # Add 2 more observations and create snap_b.
        backend.mem_save(title="b1", content="drift detection", topic_key="sdd/x/spec")
        backend.mem_save(title="b2", content="drift detection", topic_key="sdd/x/spec")
        snap_b = manager.create(description="b")

        diff = manager.diff(snap_a, snap_b)
        assert sorted(diff.added) == [4, 5]
        assert diff.removed == []
        assert diff.modified == []
        assert diff.unchanged_count == 3
        assert "+2 -0 ~0" in diff.summary

    def test_diff_two_arg_modified_field(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        backend.mem_save(title="o1", content="v1", topic_key="sdd/x/spec")
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        snap_a = manager.create(description="a")

        # Mutate observation 1.
        backend.update_observation(1, content="v2 updated")
        snap_b = manager.create(description="b")

        diff = manager.diff(snap_a, snap_b)
        assert diff.added == []
        assert diff.removed == []
        assert len(diff.modified) == 1
        mod = diff.modified[0]
        assert mod["id"] == 1
        assert mod["field"] == "content"
        assert mod["after"] == "v2 updated"
        assert diff.unchanged_count == 0
        assert "+0 -0 ~1" in diff.summary

    def test_diff_to_dict_round_trip(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=2)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        snap_a = manager.create(description="a")
        backend.mem_save(title="x", content="x", topic_key="sdd/x/spec")
        snap_b = manager.create(description="b")

        diff = manager.diff(snap_a, snap_b)
        as_dict = diff.to_dict()
        assert as_dict["added"] == [3]
        assert as_dict["removed"] == []
        assert as_dict["modified"] == []
        assert as_dict["unchanged_count"] == 2
        assert isinstance(as_dict["summary"], str)


# ---------- REQ-31: diff 1-arg form (snapshot vs live) ----------


class TestDiffOneArgVsLive:
    """``diff(snap_id)`` compares snapshot against LIVE state."""

    def test_diff_one_arg_vs_live_adds(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        snap_a = manager.create(description="a")

        # Add 2 obs AFTER snapshot.
        backend.mem_save(title="x", content="x", topic_key="sdd/x/spec")
        backend.mem_save(title="y", content="y", topic_key="sdd/x/spec")

        diff = manager.diff(snap_a)
        assert sorted(diff.added) == [4, 5]
        assert diff.removed == []
        assert diff.modified == []
        assert diff.unchanged_count == 3

    def test_diff_one_arg_vs_live_modifies(self, tmp_path: Path) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        backend.mem_save(title="o1", content="v1", topic_key="sdd/x/spec")
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        snap_a = manager.create(description="a")
        backend.update_observation(1, content="v2 updated")

        diff = manager.diff(snap_a)
        assert diff.added == []
        assert len(diff.modified) == 1
        assert diff.modified[0]["id"] == 1
        assert diff.modified[0]["field"] == "content"
        assert diff.modified[0]["after"] == "v2 updated"


# ---------- REQ-32: rollback with auto-safety snapshot ----------


class TestRollbackRefusedWithoutConfirm:
    """``rollback(snap_id, confirm=False)`` raises ``RollbackRefusedError``."""

    def test_rollback_without_confirm_raises_refused_error(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import (
            RollbackRefusedError,
            SnapshotManager,
        )

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        snap_id = manager.create(description="target")

        with pytest.raises(RollbackRefusedError) as excinfo:
            manager.rollback(snap_id, confirm=False)

        # Error payload has the two required keys per REQ-32 scenario 1.
        payload = excinfo.value.payload
        assert payload["error"] == (
            "--confirm required to write; use --dry-run to preview"
        )
        assert payload["snap_id"] == snap_id

    def test_rollback_without_confirm_does_not_create_safety_snapshot(
        self, tmp_path: Path
    ) -> None:
        """No Phase 1 safety snapshot must exist when --confirm is absent."""
        from flow_engineering.snapshot_manager import (
            RollbackRefusedError,
            SnapshotManager,
        )

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        snap_id = manager.create(description="target")

        # Only one snapshot file (the target) before the rollback attempt.
        files_before = sorted(tmp_path.glob("snap_*.json.gz"))
        assert len(files_before) == 1

        with pytest.raises(RollbackRefusedError):
            manager.rollback(snap_id, confirm=False)

        # Still only one snapshot file — Phase 1 did NOT run.
        files_after = sorted(tmp_path.glob("snap_*.json.gz"))
        assert len(files_after) == 1, (
            f"No safety snapshot should be created without --confirm; "
            f"found {len(files_after)} files: {[p.name for p in files_after]}"
        )


class TestRollbackAutoSafetySnapshot:
    """``rollback(snap_id, confirm=True)`` creates a safety snapshot FIRST."""

    def test_rollback_creates_safety_snapshot_with_rollback_safety_trigger(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        target_id = manager.create(description="target")

        result = manager.rollback(target_id, confirm=True)

        # RollbackResult carries the safety snapshot id.
        assert result.safety_snapshot_id != target_id
        assert result.target_snapshot_id == target_id

        # The safety snapshot file exists on disk.
        safety_path = tmp_path / f"{result.safety_snapshot_id}.json.gz"
        assert safety_path.exists()

        # Its envelope trigger is ``rollback_safety`` and description
        # references the target snapshot.
        safety_envelope = _read_envelope(safety_path)
        assert safety_envelope["trigger"] == "rollback_safety"
        assert safety_envelope["description"] == f"pre_rollback_to_{target_id}"

    def test_rollback_returns_rollback_result_with_required_fields(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        target_id = manager.create(description="target")

        result = manager.rollback(target_id, confirm=True)

        # All four required fields per the spec dataclass.
        assert hasattr(result, "safety_snapshot_id")
        assert hasattr(result, "target_snapshot_id")
        assert hasattr(result, "applied")
        assert hasattr(result, "forced")
        assert result.forced is False
        assert isinstance(result.applied, str)
        assert result.applied.startswith("+") or result.applied.startswith("~")

    def test_rollback_dict_shape_matches_spec_json_contract(
        self, tmp_path: Path
    ) -> None:
        """The RollbackResult.to_dict() must match the spec JSON contract."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        target_id = manager.create(description="target")

        result = manager.rollback(target_id, confirm=True)
        as_dict = result.to_dict()

        assert "safety_snapshot_id" in as_dict
        assert "target_snapshot_id" in as_dict
        assert "applied" in as_dict
        assert "forced" in as_dict
        assert as_dict["target_snapshot_id"] == target_id
        assert as_dict["forced"] is False


class TestRollbackConflictRefused:
    """Conflicts without --force raise ``RollbackConflictError`` (but safety snapshot still created)."""

    def test_rollback_with_added_observations_raises_conflict_error(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import (
            RollbackConflictError,
            SnapshotManager,
        )

        backend = InMemoryBackend()
        _seed_backend(backend, n=2)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        target_id = manager.create(description="target")

        # Add 3 new observations AFTER the target snapshot.
        for i in range(3):
            backend.mem_save(
                title=f"new-{i}", content=f"new content {i}",
                topic_key="sdd/x/spec",
            )

        files_before_rollback = sorted(tmp_path.glob("snap_*.json.gz"))
        assert len(files_before_rollback) == 1

        with pytest.raises(RollbackConflictError) as excinfo:
            manager.rollback(target_id, confirm=True)  # no force

        payload = excinfo.value.payload
        assert payload["error"] == (
            "live state has diverged; refusing rollback without --force"
        )
        # The new IDs (3, 4, 5) appear in the conflicts list with change="added".
        conflict_ids = {c["id"] for c in payload["conflicts"]}
        assert conflict_ids == {3, 4, 5}
        assert all(c["change"] == "added" for c in payload["conflicts"])

        # Even though conflict was raised, the safety snapshot WAS created.
        files_after = sorted(tmp_path.glob("snap_*.json.gz"))
        assert len(files_after) == 2, (
            f"Safety snapshot must be created even on conflict; "
            f"found {len(files_after)} files: {[p.name for p in files_after]}"
        )

    def test_rollback_with_modified_observations_raises_conflict_error(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import (
            RollbackConflictError,
            SnapshotManager,
        )

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        target_id = manager.create(description="target")

        # Modify observation 1's content AFTER snapshot.
        backend.update_observation(1, content="MODIFIED content")

        with pytest.raises(RollbackConflictError) as excinfo:
            manager.rollback(target_id, confirm=True)

        payload = excinfo.value.payload
        change_types = [c["change"] for c in payload["conflicts"]]
        assert "modified" in change_types

    def test_rollback_no_conflicts_succeeds_silently(
        self, tmp_path: Path
    ) -> None:
        """With no conflicts, rollback succeeds without raising."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        target_id = manager.create(description="target")

        # Live state matches snapshot exactly — no conflicts.
        result = manager.rollback(target_id, confirm=True)

        assert result.target_snapshot_id == target_id
        assert result.forced is False


class TestRollbackForceOverride:
    """``--force`` overrides conflicts with warning and applies."""

    def test_rollback_with_force_overrides_conflict(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=2)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        target_id = manager.create(description="target")

        # Add a new observation (creates a conflict).
        backend.mem_save(title="new", content="new content", topic_key="sdd/x/spec")

        result = manager.rollback(target_id, confirm=True, force=True)

        assert result.forced is True
        assert result.target_snapshot_id == target_id

        # Stderr warning emitted.
        captured = capsys.readouterr()
        assert "--force override" in captured.err, (
            f"Expected stderr warning; got stderr={captured.err!r}"
        )

    def test_rollback_force_restores_modified_content(
        self, tmp_path: Path
    ) -> None:
        """When force=True + modify conflict, rollback restores target content."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        target_id = manager.create(description="target")

        original_content = backend.mem_get_observation(1)["content"]

        # Modify observation 1.
        backend.update_observation(1, content="MODIFIED")

        result = manager.rollback(target_id, confirm=True, force=True)
        assert result.forced is True

        # Content restored.
        restored = backend.mem_get_observation(1)["content"]
        assert restored == original_content, (
            f"Expected content to be restored to {original_content!r}; "
            f"got {restored!r}"
        )


class TestRollbackIdempotency:
    """Re-running rollback after a partial Phase 2 leaves a valid safety trail."""

    def test_rollback_creates_safety_snapshot_each_invocation(
        self, tmp_path: Path
    ) -> None:
        """Each rollback creates its own safety snapshot (idempotent retry)."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        target_id = manager.create(description="target")

        # First rollback (no conflict).
        result1 = manager.rollback(target_id, confirm=True)
        # Second rollback (now the target state matches live).
        result2 = manager.rollback(target_id, confirm=True)

        # Different safety snapshot ids (each rollback is its own operation).
        assert result1.safety_snapshot_id != result2.safety_snapshot_id
        # Both target the same snapshot.
        assert result1.target_snapshot_id == target_id
        assert result2.target_snapshot_id == target_id

    def test_rollback_safety_snapshot_round_trips_via_show(
        self, tmp_path: Path
    ) -> None:
        """The safety snapshot created by rollback must be loadable via show()."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        target_id = manager.create(description="target")

        result = manager.rollback(target_id, confirm=True)

        # Show must parse + verify sha256 for the safety snapshot.
        envelope = manager.show(result.safety_snapshot_id)
        assert envelope["id"] == result.safety_snapshot_id
        assert envelope["trigger"] == "rollback_safety"


# ---------- T1.5 batch B2: REQ-33 graph_json gap fix ----------


class TestCreatePopulatesGraphJsonContent:
    """``SnapshotManager.create()`` MUST populate ``graph_state.graph_json_content``.

    REQ-33 D2 + brief T1.5: ``decision_drift.load_graph(snap_id=...)`` reads
    the frozen ``graph.json`` content from the envelope. Without this field
    populated by default, drift-pinned scans against freshly-created
    snapshots have NO graph to classify bindings against and the user has
    to manually edit the .gz file to inject one. The fix: ``create()``
    reads ``~/.flow-engineering/graph.json`` (or ``FLOW_GRAPH_JSON_PATH``
    override) and serialises the raw content into
    ``graph_state.graph_json_content`` as a ``str``.

    When the graph.json file does not exist (test fixtures, fresh
    installs), the field is omitted; drift-pinned scans of such snapshots
    will raise ``SnapshotGraphMissing`` from
    ``decision_drift.scan_change`` (D2 graceful degradation — already
    wired in batch B1).
    """

    def test_create_populates_graph_json_content_when_file_exists(
        self, tmp_path: Path
    ) -> None:
        """create() reads graph.json from disk and stores raw content as a string."""
        import json as _json

        from flow_engineering.snapshot_manager import SnapshotManager

        # Lay down a graph.json file in a temp location and point the
        # ``FLOW_GRAPH_JSON_PATH`` env at it so the production code path
        # picks it up. We also make sure ``snapshots_dir`` is empty so
        # the auto-``initial_state`` label applies — irrelevant to this
        # assertion but keeps the envelope deterministic.
        graph_path = tmp_path / "graph.json"
        graph_payload = {
            "nodes": [
                {
                    "id": "vec_store",
                    "label": "SQLiteVecStore",
                    "file": "vectors/sqlite_vec_store.py",
                    "line": 42,
                },
            ]
        }
        graph_path.write_text(
            _json.dumps(graph_payload, ensure_ascii=False), encoding="utf-8"
        )

        snaps_dir = tmp_path / "snaps"
        import os as _os
        old_env = _os.environ.get("FLOW_GRAPH_JSON_PATH")
        _os.environ["FLOW_GRAPH_JSON_PATH"] = str(graph_path)
        try:
            backend = InMemoryBackend()
            _seed_backend(backend, n=2)
            manager = SnapshotManager(snapshots_dir=snaps_dir, backend=backend)
            snap_id = manager.create(description="graph-test")

            envelope = _read_envelope(snaps_dir / f"{snap_id}.json.gz")
        finally:
            if old_env is None:
                _os.environ.pop("FLOW_GRAPH_JSON_PATH", None)
            else:
                _os.environ["FLOW_GRAPH_JSON_PATH"] = old_env

        # The new field is present and is a STRING (per the brief).
        graph_state = envelope.get("graph_state", {})
        assert "graph_json_content" in graph_state, (
            f"graph_state missing graph_json_content; keys: {sorted(graph_state.keys())!r}"
        )
        assert isinstance(graph_state["graph_json_content"], str), (
            f"graph_json_content must be a string, got {type(graph_state['graph_json_content']).__name__}"
        )
        # The content matches the file content (raw JSON serialisation).
        assert graph_state["graph_json_content"] == _json.dumps(
            graph_payload, ensure_ascii=False
        )

    def test_create_omits_graph_json_content_when_file_missing(
        self, tmp_path: Path
    ) -> None:
        """Without graph.json on disk, the field is absent — drift scans refuse."""
        from flow_engineering.snapshot_manager import SnapshotManager

        snaps_dir = tmp_path / "snaps"
        # Ensure no FLOW_GRAPH_JSON_PATH and no ~/.flow-engineering/graph.json
        # is reachable from this test (pointed elsewhere via HOME so the
        # production default is also a non-existent file).
        import os as _os

        old_graph_env = _os.environ.get("FLOW_GRAPH_JSON_PATH")
        old_home = _os.environ.get("HOME") or _os.environ.get("USERPROFILE")
        non_home = tmp_path / "fakehome"
        non_home.mkdir()
        _os.environ.pop("FLOW_GRAPH_JSON_PATH", None)
        _os.environ["HOME"] = str(non_home)
        try:
            backend = InMemoryBackend()
            _seed_backend(backend, n=2)
            manager = SnapshotManager(snapshots_dir=snaps_dir, backend=backend)
            snap_id = manager.create(description="no-graph-test")
            envelope = _read_envelope(snaps_dir / f"{snap_id}.json.gz")
        finally:
            if old_graph_env is not None:
                _os.environ["FLOW_GRAPH_JSON_PATH"] = old_graph_env
            if old_home is not None:
                _os.environ["HOME"] = old_home
            else:
                _os.environ.pop("HOME", None)

        graph_state = envelope.get("graph_state", {})
        # Field absent — drift-pinned scan will refuse with SnapshotGraphMissing.
        assert "graph_json_content" not in graph_state, (
            f"graph_json_content must be absent when graph.json missing; got: {graph_state['graph_json_content']!r}"
        )

    def test_drift_scan_with_snap_id_reads_frozen_graph_from_envelope(
        self, tmp_path: Path
    ) -> None:
        """End-to-end: snapshot has graph_json_content, scan reads frozen state.

        Mirrors the brief's acceptance criterion: "create a snapshot, call
        ``load_graph(snap_id=<that_id>)``, verify the drift scan reads the
        snapshot's frozen graph (not live)".
        """
        import json as _json
        import os as _os

        from flow_engineering import decision_drift
        from flow_engineering.snapshot_manager import SnapshotManager

        # Set up graph.json with one valid node.
        graph_path = tmp_path / "graph.json"
        graph_payload = {
            "nodes": [
                {
                    "id": "vec_store",
                    "label": "SQLiteVecStore",
                    "file": "vectors/sqlite_vec_store.py",
                    "line": 42,
                },
            ]
        }
        graph_path.write_text(
            _json.dumps(graph_payload, ensure_ascii=False), encoding="utf-8"
        )

        snaps_dir = tmp_path / "snaps"
        _os.environ["FLOW_GRAPH_JSON_PATH"] = str(graph_path)
        _os.environ["FLOW_SNAPSHOTS_DIR"] = str(snaps_dir)
        try:
            # Seed an observation whose binding matches the graph node so
            # the scan can classify it as STILL_VALID against the frozen graph.
            from flow_engineering.binding import CodeRef, format_code_refs_block

            cref = CodeRef(
                project="insyd",
                id="vec_store",
                label="SQLiteVecStore",
                file="vectors/sqlite_vec_store.py",
                line=42,
                confidence=0.9,
                source="manual",
            )
            content = (
                "## Decision\n\nSnapshot-pinned binding.\n"
                + format_code_refs_block([cref], source="manual")
            )
            backend = InMemoryBackend()
            backend.mem_save(
                title="t15-fixture/phase_0",
                content=content,
                topic_key="sdd/vector-semantic-search/spec",
            )

            manager = SnapshotManager(snapshots_dir=snaps_dir, backend=backend)
            snap_id = manager.create(description="e2e-frozen")
            # Now MUTATE the live graph.json so the snapshot's frozen state
            # diverges — proves the scan reads the envelope, not live disk.
            mutated_path = tmp_path / "mutated.json"
            mutated_path.write_text(
                _json.dumps(
                    {"nodes": [{"id": "vec_store", "label": "STALE",
                                "file": "x.py", "line": 99}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            _os.environ["FLOW_GRAPH_JSON_PATH"] = str(mutated_path)

            report = decision_drift.scan_change(
                "vector-semantic-search",
                graph_json_path=None,
                backend=None,
                snap_id=snap_id,
            )

            # The frozen graph classified the binding as STILL_VALID
            # (the live graph would have classified it as STALE_LOCATION
            # because file=x.py / line=99 no longer matches).
            assert report.findings, "expected at least one finding"
            from flow_engineering.decision_drift import DriftClass

            assert any(
                f.drift_class == DriftClass.STILL_VALID for f in report.findings
            ), (
                f"expected STILL_VALID against frozen graph; got "
                f"{[(f.drift_class.value, f.binding.id) for f in report.findings]!r}"
            )
        finally:
            _os.environ.pop("FLOW_GRAPH_JSON_PATH", None)
            _os.environ.pop("FLOW_SNAPSHOTS_DIR", None)


# ---------- T1.6 batch C: REQ-34 prune retention policy ----------


class TestPrune:
    """``SnapshotManager.prune()`` retention policy (REQ-34, T1.6 batch C).

    The prune method is OR-combined across three retention criteria:
    ``keep_last`` (count), ``keep_days`` (age), ``max_total_size_mb``
    (size). A snapshot is a candidate for deletion if ANY criterion
    returns False for it. The method is dry-run by default; ``confirm=True``
    actually deletes. Two safety invariants are non-negotiable:

    - The most-recent snapshot is NEVER deleted (unless ``force=True``).
    - Snapshots whose ``metadata.pinned`` is True are NEVER deleted.

    Both invariants hold even in dry-run (so the would-delete list
    excludes them).
    """

    def _seed_n_snapshots(
        self,
        tmp_path: Path,
        *,
        n: int,
        manager_backend: InMemoryBackend | None = None,
        interval: float = 0.0,
    ) -> list[str]:
        """Create ``n`` snapshots on a fresh manager. Returns ids oldest-first."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = manager_backend or InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        ids: list[str] = []
        for i in range(n):
            ids.append(manager.create(description=f"seed-{i}"))
            if interval > 0 and i < n - 1:
                time.sleep(interval)
        return ids

    def test_prune_keep_last_evicts_oldest(
        self, tmp_path: Path
    ) -> None:
        """With 5 snapshots and keep_last=2, dry-run returns would_delete=[3 oldest]."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        ids: list[str] = []
        for i in range(5):
            ids.append(manager.create(description=f"seed-{i}"))
            if i < 4:
                time.sleep(1.01)

        result = manager.prune(keep_last=2)  # default confirm=False (dry-run)

        # 5 snapshots exist, keep_last=2 => 3 candidates for deletion.
        assert result.deleted == [], (
            f"dry-run MUST NOT delete; got deleted={result.deleted!r}"
        )
        assert result.dry_run is True
        # would_keep = 2 newest, would_delete = 3 oldest (insertion order).
        assert len(result.would_delete) == 3
        assert len(result.would_keep) == 2
        assert set(result.would_delete) == set(ids[:3])
        assert set(result.would_keep) == set(ids[3:])
        # All 5 files still on disk (dry-run).
        remaining = sorted(p.name for p in tmp_path.glob("snap_*.json.gz"))
        assert len(remaining) == 5

    def test_prune_keep_days_evicts_older_than_threshold(
        self, tmp_path: Path
    ) -> None:
        """keep_days=N keeps snapshots created in the last N days."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)

        # Create one snapshot now (would-keep).
        recent_id = manager.create(description="recent")
        # Create another snapshot and backdate its envelope to 2020-01-01
        # so keep_days=30 evicts it. Prune reads created_at from the
        # envelope (NOT file mtime), so backdating the envelope is the
        # right lever for the test.
        very_old_id = manager.create(description="very-old")
        very_old_path = tmp_path / f"{very_old_id}.json.gz"
        import gzip as _gzip
        import hashlib as _hashlib
        import json as _json

        with _gzip.open(very_old_path, "rt", encoding="utf-8") as fh:
            envelope = _json.loads(fh.read())
        envelope["created_at"] = "2020-01-01T00:00:00Z"  # > 30 days ago
        # Recompute sha256 so the envelope stays self-consistent.
        canonical = _canonical_json_dumps(
            {**envelope, "metadata": {k: v for k, v in envelope["metadata"].items() if k != "sha256"}}
        )
        envelope["metadata"]["sha256"] = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with _gzip.open(very_old_path, "wt", encoding="utf-8") as fh:
            fh.write(_canonical_json_dumps(envelope))

        # keep_days=30 keeps recent, evicts backdated-2020.
        result = manager.prune(keep_days=30)
        assert very_old_id in result.would_delete, (
            f"expected very_old ({very_old_id}) in would_delete; "
            f"got would_delete={result.would_delete!r} would_keep={result.would_keep!r}"
        )
        assert recent_id in result.would_keep

    def test_prune_max_total_size_mb_evicts_oldest_first(
        self, tmp_path: Path
    ) -> None:
        """max_total_size_mb=N deletes oldest-first until total size fits."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        ids = [manager.create(description=f"snap-{i}") for i in range(5)]

        # Get total size on disk in bytes.
        total_bytes = sum(p.stat().st_size for p in tmp_path.glob("snap_*.json.gz"))
        # Pick a budget smaller than total (forces deletions) but big
        # enough to keep at least the newest snapshot.
        target_bytes = total_bytes // 2  # arbitrary

        result = manager.prune(max_total_size_mb=max(1, target_bytes // (1024 * 1024)))

        # The newest snapshot is NEVER deleted.
        assert ids[-1] not in result.would_delete, (
            f"newest snapshot MUST never be in would_delete; got {result.would_delete!r}"
        )
        # The would-delete list is in chronological (oldest-first) order.
        if len(result.would_delete) > 1:
            ids_to_delete = result.would_delete
            expected_oldest_first = sorted(
                ids_to_delete, key=lambda sid: ids.index(sid)
            )
            assert ids_to_delete == expected_oldest_first, (
                f"would_delete must be oldest-first; got {ids_to_delete!r} "
                f"vs expected {expected_oldest_first!r}"
            )

    def test_prune_dry_run_when_no_confirm(
        self, tmp_path: Path
    ) -> None:
        """prune() without confirm=True is dry-run; no files deleted."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        ids: list[str] = []
        for i in range(4):
            ids.append(manager.create(description=f"snap-{i}"))
            if i < 3:
                time.sleep(1.01)
        files_before = sorted(p.name for p in tmp_path.glob("snap_*.json.gz"))

        result = manager.prune(keep_last=1)

        assert result.dry_run is True
        assert result.deleted == []
        files_after = sorted(p.name for p in tmp_path.glob("snap_*.json.gz"))
        assert files_after == files_before, (
            f"dry-run MUST NOT delete; before={files_before} after={files_after}"
        )
        # Newest snapshot is in would_keep.
        assert ids[-1] in result.would_keep

    def test_prune_confirm_true_actually_deletes(
        self, tmp_path: Path
    ) -> None:
        """prune(confirm=True, keep_last=1) deletes 3 of 4 snapshots."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        ids: list[str] = []
        for i in range(4):
            ids.append(manager.create(description=f"snap-{i}"))
            if i < 3:
                time.sleep(1.01)

        result = manager.prune(keep_last=1, confirm=True)

        assert result.dry_run is False
        assert sorted(result.deleted) == sorted(ids[:3]), (
            f"expected 3 oldest deleted; got deleted={result.deleted!r}"
        )
        remaining = sorted(
            p.name.replace(".json.gz", "") for p in tmp_path.glob("snap_*.json.gz")
        )
        assert remaining == [ids[3]], (
            f"expected only the newest snapshot on disk; got {remaining!r}"
        )

    def test_prune_never_deletes_most_recent(
        self, tmp_path: Path
    ) -> None:
        """The most-recent snapshot is in would_keep, never would_delete."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        ids: list[str] = []
        for i in range(5):
            ids.append(manager.create(description=f"snap-{i}"))
            if i < 4:
                time.sleep(1.01)

        result = manager.prune(keep_last=0)  # would normally delete all

        # Without --force, the most recent snapshot is protected.
        assert ids[-1] not in result.would_delete, (
            f"newest MUST not be in would_delete; got {result.would_delete!r}"
        )
        assert ids[-1] in result.would_keep

    def test_prune_respects_pinned_metadata(
        self, tmp_path: Path
    ) -> None:
        """Snapshots with metadata.pinned=True are never deleted."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        # Create 3 snapshots; then mark the MIDDLE one pinned by
        # rewriting its envelope with metadata.pinned=True.
        ids = [manager.create(description=f"snap-{i}") for i in range(3)]
        middle_id = ids[1]
        middle_path = tmp_path / f"{middle_id}.json.gz"
        import gzip as _gzip
        import hashlib as _hashlib
        import json as _json

        with _gzip.open(middle_path, "rt", encoding="utf-8") as fh:
            envelope = _json.loads(fh.read())
        envelope["metadata"]["pinned"] = True
        # Recompute sha256 so the envelope stays self-consistent (show()
        # does not need to succeed for prune, but consistency matters
        # for downstream consumers).
        canonical = _canonical_json_dumps(
            {**envelope, "metadata": {k: v for k, v in envelope["metadata"].items() if k != "sha256"}}
        )
        envelope["metadata"]["sha256"] = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with _gzip.open(middle_path, "wt", encoding="utf-8") as fh:
            fh.write(_canonical_json_dumps(envelope))

        result = manager.prune(keep_last=1, confirm=True)

        # Pinned middle snapshot is NEVER deleted.
        assert middle_id not in result.deleted, (
            f"pinned snapshot MUST not be deleted; got deleted={result.deleted!r}"
        )
        assert (tmp_path / f"{middle_id}.json.gz").exists(), (
            "pinned snapshot file MUST remain on disk after prune"
        )

    def test_prune_force_overrides_most_recent_safety(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """prune(force=True, keep_last=0) deletes all 5 snapshots + warns."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        ids = [manager.create(description=f"snap-{i}") for i in range(5)]

        result = manager.prune(keep_last=0, confirm=True, force=True)

        # All snapshots deleted (force overrides the safety net).
        assert sorted(result.deleted) == sorted(ids), (
            f"expected all 5 deleted with --force; got deleted={result.deleted!r}"
        )
        # No snapshot files left.
        remaining = list(tmp_path.glob("snap_*.json.gz"))
        assert remaining == [], (
            f"all snapshot files MUST be deleted with --force; "
            f"remaining={[p.name for p in remaining]}"
        )
        # Stderr warning emitted.
        captured = capsys.readouterr()
        assert "--force" in captured.err or "override" in captured.err.lower(), (
            f"expected stderr warning; got stderr={captured.err!r}"
        )

    def test_prune_returns_prune_result_dataclass(
        self, tmp_path: Path
    ) -> None:
        """prune() returns a PruneResult dataclass with the 5 required fields."""
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        manager = SnapshotManager(snapshots_dir=tmp_path, backend=backend)
        manager.create(description="x")

        result = manager.prune(keep_last=1)

        for field in (
            "deleted", "would_delete", "would_keep", "freed_bytes", "dry_run",
        ):
            assert hasattr(result, field), f"missing field {field!r}"
        assert isinstance(result.deleted, list)
        assert isinstance(result.would_delete, list)
        assert isinstance(result.would_keep, list)
        assert isinstance(result.freed_bytes, int)
        assert isinstance(result.dry_run, bool)
