"""Unit tests for ``flow_engineering.snapshot_manager`` (REQ-28 + REQ-29, T1.1).

TDD: written BEFORE the implementation. These MUST fail until the GREEN
commit wires ``src/flow_engineering/snapshot_manager.py`` with the
``SnapshotManager`` class, ``create()`` + ``list()`` methods, gzip + sha256
envelope write, atomic temp-file replace, and reverse-chronological list
with ``since`` + ``limit`` filtering.

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
import secrets
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
        assert id_b in kept_ids and id_c in kept_ids
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
        snap_a = manager.create() if False else None
        # Build a fresh manager so we don't reuse the snap_a above.
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
