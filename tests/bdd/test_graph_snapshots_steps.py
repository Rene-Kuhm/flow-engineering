"""BDD step definitions for graph-snapshots REQ-28, REQ-29, REQ-30, REQ-31.

Covers the feature files:

- ``req28_snapshot_create.feature`` (2 scenarios) — REQ-28 acceptance
  gate for ``SnapshotManager.create`` round-trip + sha256 verification
  + first-run auto-label + explicit description override.
- ``req29_snapshot_list.feature`` (2 scenarios) — REQ-29 acceptance
  gate for ``SnapshotManager.list`` reverse-chronological order +
  ``since`` filter + ``limit`` truncation.
- ``req30_snapshot_show.feature`` (1 scenario) — REQ-30 acceptance
  gate for ``SnapshotManager.show`` envelope round-trip + sha256
  verification.
- ``req31_snapshot_diff.feature`` (2 scenarios) — REQ-31 acceptance
  gate for ``SnapshotManager.diff`` 2-arg form (snapshot vs snapshot)
  + 1-arg form (snapshot vs live state).

Test isolation:
- Each scenario uses ``tmp_path`` for ``snapshots_dir`` so the user's
  real ``~/.flow-engineering/snapshots/`` is never touched.
- The ``InMemoryBackend`` is the prose test fixture; the step defs
  call ``SnapshotManager`` directly (the CLI surface ships in batch B
  via T1.5; the BDD scenarios validate the LIBRARY contract that the
  CLI will wrap in batch B).
- Snapshots created in the Given step persist across When/Then in the
  same scenario world.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering.engram_io import InMemoryBackend
from flow_engineering.snapshot_manager import (
    SNAPSHOT_SCHEMA_VERSION,
    PruneNoFilterError,
    PruneResult,
    PruneSafetyGateError,
    RollbackConflictError,
    RollbackRefusedError,
    RollbackResult,
    SnapshotManager,
)

# ---------- Helpers ----------


def _canonical_json_dumps(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _seed_obs(
    backend: InMemoryBackend,
    *,
    count: int,
    project: str = "insyd",
    title_prefix: str = "snap obs",
    topic_key: str = "sdd/x/spec",
) -> list[int]:
    ids: list[int] = []
    for i in range(count):
        obs = backend.mem_save(
            title=f"{title_prefix} {i}",
            content=f"drift detection strategy {i}",
            topic_key=topic_key,
        )
        ids.append(int(obs["id"]))
    return ids


# ---------- World fixture ----------


@pytest.fixture
def snapshot_world(tmp_path) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-28..31 scenarios."""
    snap_dir = tmp_path / "snapshots"
    return {
        "snapshots_dir": snap_dir,
        "backend": InMemoryBackend(),
        "manager": None,  # lazily built once snapshots_dir is known
        "snap_ids": [],
        "created_at_by_id": {},
        "diff": None,
        "envelope": None,
        "rollback_result": None,
        "rollback_exception": None,
        "safety_snap_id": None,
        "original_obs_content": {},
    }


def _get_manager(world: dict[str, Any]) -> SnapshotManager:
    """Return (lazily building) the SnapshotManager for this scenario."""
    if world["manager"] is None:
        world["manager"] = SnapshotManager(
            snapshots_dir=world["snapshots_dir"],
            backend=world["backend"],
        )
    return world["manager"]


# ---------- Scenario bindings: REQ-28 ----------


@scenario(
    "../bdd/req28_snapshot_create.feature",
    "flow snapshot create writes a snapshot with all current observations and a sha256",
)
def test_req28_create_round_trip(snapshot_world):
    pass


@scenario(
    "../bdd/req28_snapshot_create.feature",
    'flow snapshot create --description "pre-deploy-v0.6" stores the description verbatim',
)
def test_req28_description_stores_verbatim(snapshot_world):
    pass


# ---------- Scenario bindings: REQ-29 ----------


@scenario(
    "../bdd/req29_snapshot_list.feature",
    "After creating 3 snapshots, flow snapshot list returns 3 entries in reverse chronological order",
)
def test_req29_list_reverse_chronological(snapshot_world):
    pass


@scenario(
    "../bdd/req29_snapshot_list.feature",
    "flow snapshot list --since=<recent_iso> returns only snapshots at or after that timestamp",
)
def test_req29_list_since_filter(snapshot_world):
    pass


# ---------- Scenario bindings: REQ-30 ----------


@scenario(
    "../bdd/req30_snapshot_show.feature",
    "After creating a snapshot, flow snapshot show <snap_id> prints the JSON with all fields",
)
def test_req30_show_round_trip(snapshot_world):
    pass


# ---------- Scenario bindings: REQ-31 ----------


@scenario(
    "../bdd/req31_snapshot_diff.feature",
    "After creating snapshot A with 3 obs and B with 5 obs (2 added between), flow snapshot diff A B shows 2 added observations",
)
def test_req31_diff_two_arg(snapshot_world):
    pass


@scenario(
    "../bdd/req31_snapshot_diff.feature",
    "With no second argument, flow snapshot diff A shows changes from A to current state",
)
def test_req31_diff_one_arg_vs_live(snapshot_world):
    pass


# ---------- Given steps ----------


@given(parsers.parse("an InMemoryBackend seeded with {n:d} observation"))
def seed_n_observations_singular(
    snapshot_world: dict[str, Any], n: int,
) -> None:
    """Seed ``n`` observations (singular wording: "1 observation")."""
    _seed_obs(snapshot_world["backend"], count=n)


@given(parsers.parse("an InMemoryBackend seeded with {n:d} observations"))
def seed_n_observations_plural(
    snapshot_world: dict[str, Any], n: int,
) -> None:
    """Seed ``n`` observations (plural wording: "N observations")."""
    _seed_obs(snapshot_world["backend"], count=n)


@given("the snapshot directory is empty")
def given_snapshot_dir_empty(snapshot_world: dict[str, Any]) -> None:
    snapshot_world["snapshots_dir"].mkdir(parents=True, exist_ok=True)
    assert not any(snapshot_world["snapshots_dir"].glob("snap_*.json.gz"))


@given("the snapshot directory contains 1 prior snapshot")
def given_one_prior_snapshot(snapshot_world: dict[str, Any]) -> None:
    snapshot_world["snapshots_dir"].mkdir(parents=True, exist_ok=True)
    mgr = _get_manager(snapshot_world)
    _seed_obs(snapshot_world["backend"], count=1)
    prior_id = mgr.create(description="prior")
    snapshot_world["snap_ids"].append(prior_id)
    snapshot_world["prior_id"] = prior_id


@given("the snapshot directory contains 3 snapshots created at ascending times")
def given_three_ascending_snapshots(snapshot_world: dict[str, Any]) -> None:
    snapshot_world["snapshots_dir"].mkdir(parents=True, exist_ok=True)
    mgr = _get_manager(snapshot_world)
    _seed_obs(snapshot_world["backend"], count=1)
    for label in ("s1", "s2", "s3"):
        sid = mgr.create(description=label)
        snapshot_world["snap_ids"].append(sid)
        time.sleep(1.01)


@given("the snapshot directory contains 5 snapshots created at ascending times")
def given_five_ascending_snapshots(snapshot_world: dict[str, Any]) -> None:
    snapshot_world["snapshots_dir"].mkdir(parents=True, exist_ok=True)
    mgr = _get_manager(snapshot_world)
    _seed_obs(snapshot_world["backend"], count=1)
    for i in range(5):
        sid = mgr.create(description=f"s{i + 1}")
        snapshot_world["snap_ids"].append(sid)
        if i < 4:
            time.sleep(1.01)
        # Capture created_at via list() so REQ-29 step 2 can build
        # ``since=<T3.created_at>``.
        for meta in mgr.list():
            if meta.id == sid:
                snapshot_world["created_at_by_id"][sid] = meta.created_at
                break


@given("a snapshot exists with description \"show-test\"")
def given_one_snapshot_show_test(snapshot_world: dict[str, Any]) -> None:
    snapshot_world["snapshots_dir"].mkdir(parents=True, exist_ok=True)
    mgr = _get_manager(snapshot_world)
    sid = mgr.create(description="show-test")
    snapshot_world["snap_ids"].append(sid)
    snapshot_world["last_snap_id"] = sid


@given("snapshot A was created with 3 observations")
def given_snapshot_a_with_3(snapshot_world: dict[str, Any]) -> None:
    snapshot_world["snapshots_dir"].mkdir(parents=True, exist_ok=True)
    mgr = _get_manager(snapshot_world)
    _seed_obs(snapshot_world["backend"], count=3)
    sid = mgr.create(description="A")
    snapshot_world["snap_id_a"] = sid
    snapshot_world["snap_ids"].append(sid)


@given("snapshot B was created with 5 observations (2 added after A)")
def given_snapshot_b_with_5(snapshot_world: dict[str, Any]) -> None:
    mgr = _get_manager(snapshot_world)
    _seed_obs(snapshot_world["backend"], count=2)
    sid = mgr.create(description="B")
    snapshot_world["snap_id_b"] = sid
    snapshot_world["snap_ids"].append(sid)


@given("2 observations were added since snapshot A")
def given_added_2_since_a(snapshot_world: dict[str, Any]) -> None:
    _seed_obs(snapshot_world["backend"], count=2)


@given("observation 2 was updated since snapshot A")
def given_obs_2_updated(snapshot_world: dict[str, Any]) -> None:
    snapshot_world["backend"].update_observation(
        2, content="drift detection strategy 1 UPDATED",
    )


# ---------- When steps ----------


@when("I create a snapshot without a description")
def when_create_no_description(snapshot_world: dict[str, Any]) -> None:
    mgr = _get_manager(snapshot_world)
    sid = mgr.create(description="")
    snapshot_world["snap_ids"].append(sid)
    snapshot_world["last_snap_id"] = sid


@when(parsers.parse('I create a snapshot with description "{description}"'))
def when_create_with_description(
    snapshot_world: dict[str, Any], description: str,
) -> None:
    mgr = _get_manager(snapshot_world)
    sid = mgr.create(description=description)
    snapshot_world["snap_ids"].append(sid)
    snapshot_world["last_snap_id"] = sid


@when("I list snapshots")
def when_list_all(snapshot_world: dict[str, Any]) -> None:
    mgr = _get_manager(snapshot_world)
    snapshot_world["list_result"] = mgr.list()


@when(
    parsers.parse(
        'I list snapshots with since="{since}" and limit={limit:d}'
    )
)
def when_list_with_since_and_limit(
    snapshot_world: dict[str, Any], since: str, limit: int,
) -> None:
    # The scenario passes a placeholder ``<T3.created_at>``; substitute
    # with the real created_at of the 3rd snapshot (1-indexed: T1=first).
    since_iso = since
    if since.startswith("<") and since.endswith(">"):
        key = since[1:-1]
        # Resolve ``T3.created_at`` to the 3rd snapshot's created_at.
        if key == "T3.created_at" and len(snapshot_world["snap_ids"]) >= 3:
            t3_id = snapshot_world["snap_ids"][2]
            since_iso = snapshot_world["created_at_by_id"].get(t3_id, since)
    mgr = _get_manager(snapshot_world)
    snapshot_world["list_result"] = mgr.list(since=since_iso, limit=limit)


@when("I show the snapshot")
def when_show_snapshot(snapshot_world: dict[str, Any]) -> None:
    mgr = _get_manager(snapshot_world)
    sid = snapshot_world["last_snap_id"] or snapshot_world["snap_ids"][-1]
    snapshot_world["envelope"] = mgr.show(sid)


@when("I diff snapshot A against snapshot B")
def when_diff_a_vs_b(snapshot_world: dict[str, Any]) -> None:
    mgr = _get_manager(snapshot_world)
    snapshot_world["diff"] = mgr.diff(
        snapshot_world["snap_id_a"], snapshot_world["snap_id_b"],
    )


@when("I diff snapshot A against live state")
def when_diff_a_vs_live(snapshot_world: dict[str, Any]) -> None:
    mgr = _get_manager(snapshot_world)
    snapshot_world["diff"] = mgr.diff(snapshot_world["snap_id_a"])


# ---------- Then steps ----------


@then("the snapshot directory contains 1 snapshot file")
def then_dir_has_one(snapshot_world: dict[str, Any]) -> None:
    files = sorted(snapshot_world["snapshots_dir"].glob("snap_*.json.gz"))
    assert len(files) == 1, f"Expected 1 file, got {len(files)}: {files!r}"


@then("the snapshot envelope has schema 1")
def then_envelope_schema_1(snapshot_world: dict[str, Any]) -> None:
    sid = snapshot_world.get("last_snap_id") or snapshot_world["snap_ids"][-1]
    import gzip
    path = snapshot_world["snapshots_dir"] / f"{sid}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        envelope = json.loads(fh.read())
    assert envelope["schema"] == SNAPSHOT_SCHEMA_VERSION
    snapshot_world["envelope"] = envelope


@then("the snapshot envelope metadata sha256 matches the canonical-JSON hash")
def then_sha256_matches(snapshot_world: dict[str, Any]) -> None:
    envelope = snapshot_world["envelope"]
    meta = envelope["metadata"]
    meta_for_hash = {k: v for k, v in meta.items() if k != "sha256"}
    envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
    envelope_for_hash["metadata"] = meta_for_hash
    expected = hashlib.sha256(
        _canonical_json_dumps(envelope_for_hash).encode("utf-8")
    ).hexdigest()
    assert meta["sha256"] == expected, (
        f"sha256 mismatch: expected {expected}, got {meta['sha256']}"
    )


@then("the snapshot envelope graph_state contains all 5 observations")
def then_graph_state_has_5_obs(snapshot_world: dict[str, Any]) -> None:
    envelope = snapshot_world["envelope"]
    obs = envelope["graph_state"]["observations"]
    assert len(obs) == 5, f"Expected 5 observations, got {len(obs)}"


@then('the new snapshot envelope description equals "pre-deploy-v0.6"')
def then_envelope_description_literal(snapshot_world: dict[str, Any]) -> None:
    sid = snapshot_world["snap_ids"][-1]
    import gzip
    path = snapshot_world["snapshots_dir"] / f"{sid}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        envelope = json.loads(fh.read())
    assert envelope["description"] == "pre-deploy-v0.6"


@then("the prior snapshot file is unchanged")
def then_prior_unchanged(snapshot_world: dict[str, Any]) -> None:
    prior_id = snapshot_world["prior_id"]
    prior_path = snapshot_world["snapshots_dir"] / f"{prior_id}.json.gz"
    import gzip
    with gzip.open(prior_path, "rt", encoding="utf-8") as fh:
        envelope = json.loads(fh.read())
    assert envelope["description"] == "prior"


@then("the snapshot list has 3 entries")
def then_list_has_3(snapshot_world: dict[str, Any]) -> None:
    assert len(snapshot_world["list_result"]) == 3


@then("the snapshot list is in reverse chronological order")
def then_list_reverse_chrono(snapshot_world: dict[str, Any]) -> None:
    result = snapshot_world["list_result"]
    ids = [e.id for e in result]
    expected = list(reversed(snapshot_world["snap_ids"]))
    assert ids == expected, f"Expected {expected!r}, got {ids!r}"


@then("each entry has the 6 required keys")
def then_entry_has_6_keys(snapshot_world: dict[str, Any]) -> None:
    for entry in snapshot_world["list_result"]:
        for key in ("id", "created_at", "trigger", "description", "obs_count", "size_bytes"):
            assert hasattr(entry, key), f"Missing field {key} on {entry!r}"


@then("the snapshot list contains 3 entries")
def then_list_contains_3(snapshot_world: dict[str, Any]) -> None:
    assert len(snapshot_world["list_result"]) == 3


@then("the snapshot list excludes the T1 and T2 snapshots")
def then_list_excludes_t1_t2(snapshot_world: dict[str, Any]) -> None:
    ids = {e.id for e in snapshot_world["list_result"]}
    t1 = snapshot_world["snap_ids"][0]
    t2 = snapshot_world["snap_ids"][1]
    assert t1 not in ids and t2 not in ids


@then("combining --since and --limit=2 returns the 2 newest within the filter")
def then_since_limit_combine(snapshot_world: dict[str, Any]) -> None:
    # T3..T5 = 3 entries; limit=2 ⇒ T5, T4.
    mgr = _get_manager(snapshot_world)
    t3_iso = snapshot_world["created_at_by_id"][snapshot_world["snap_ids"][2]]
    result = mgr.list(since=t3_iso, limit=2)
    ids = [e.id for e in result]
    expected = [snapshot_world["snap_ids"][4], snapshot_world["snap_ids"][3]]
    assert ids == expected, f"Expected {expected!r}, got {ids!r}"


@then("the snapshot envelope has all 7 top-level keys")
def then_envelope_has_7_keys(snapshot_world: dict[str, Any]) -> None:
    envelope = snapshot_world["envelope"]
    for key in (
        "schema", "id", "created_at", "trigger", "description",
        "graph_state", "metadata",
    ):
        assert key in envelope, f"Missing top-level key {key} in {envelope.keys()!r}"


@then("the diff has added=[4, 5]")
def then_diff_added_4_5(snapshot_world: dict[str, Any]) -> None:
    assert sorted(snapshot_world["diff"].added) == [4, 5]


@then("the diff has removed=[]")
def then_diff_removed_empty(snapshot_world: dict[str, Any]) -> None:
    assert snapshot_world["diff"].removed == []


@then("the diff has modified=[]")
def then_diff_modified_empty(snapshot_world: dict[str, Any]) -> None:
    assert snapshot_world["diff"].modified == []


@then("the diff has modified=[1 entry with id=2]")
def then_diff_modified_id_2(snapshot_world: dict[str, Any]) -> None:
    modified = snapshot_world["diff"].modified
    assert len(modified) == 1, f"Expected 1 modification, got {modified!r}"
    assert modified[0]["id"] == 2


@then("the diff has unchanged_count=3")
def then_diff_unchanged_3(snapshot_world: dict[str, Any]) -> None:
    assert snapshot_world["diff"].unchanged_count == 3


@then("the diff has unchanged_count=2")
def then_diff_unchanged_2(snapshot_world: dict[str, Any]) -> None:
    assert snapshot_world["diff"].unchanged_count == 2


@then(parsers.parse('the diff summary starts with "{prefix}"'))
def then_diff_summary_starts_with(snapshot_world: dict[str, Any], prefix: str) -> None:
    summary = snapshot_world["diff"].summary
    assert summary.startswith(prefix), (
        f"Expected summary to start with {prefix!r}, got {summary!r}"
    )


# ============================================================
# REQ-32: rollback with auto-safety snapshot (3 scenarios)
# ============================================================


@scenario(
    "../bdd/req32_snapshot_rollback.feature",
    "flow snapshot rollback <snap_id> without --confirm refuses with non-zero exit",
)
def test_req32_rollback_refused_without_confirm(snapshot_world):
    pass


@scenario(
    "../bdd/req32_snapshot_rollback.feature",
    "flow snapshot rollback <snap_id> --confirm creates safety snapshot first, restores state, exits 0",
)
def test_req32_rollback_with_confirm_succeeds(snapshot_world):
    pass


@scenario(
    "../bdd/req32_snapshot_rollback.feature",
    "flow snapshot rollback <old_snap_id> --confirm with new observations added since refuses with JSON error listing new IDs",
)
def test_req32_rollback_conflict_refused(snapshot_world):
    pass


# ---------- Given steps (REQ-32) ----------


@given(parsers.parse("a snapshot {snap_id} exists with {n:d} observations"))
def given_snapshot_with_n_obs(
    snapshot_world: dict[str, Any], snap_id: str, n: int
) -> None:
    """Create a snapshot named ``snap_id`` capturing ``n`` observations.

    The InMemoryBackend's auto-incremented IDs are deterministic, so the
    snapshot's observations will be [1..n]. The ``snap_id`` here is a
    scenario-level alias (e.g. ``snap_A``, ``snap_old``); the underlying
    SnapshotManager still generates the real id (``snap_<ISO>-<hex>``),
    but we record the mapping in ``world["snap_aliases"]`` so the When
    steps can look it up.
    """
    snapshot_world["snapshots_dir"].mkdir(parents=True, exist_ok=True)
    mgr = _get_manager(snapshot_world)
    _seed_obs(snapshot_world["backend"], count=n)
    real_id = mgr.create(description=snap_id)
    snapshot_world.setdefault("snap_aliases", {})[snap_id] = real_id
    snapshot_world["snap_ids"].append(real_id)
    snapshot_world["last_snap_id"] = real_id
    # Capture original content for restoration assertions.
    for i in range(1, n + 1):
        obs = snapshot_world["backend"].mem_get_observation(i)
        snapshot_world["original_obs_content"][i] = obs["content"]


@given(parsers.parse("observation {obs_id:d} was modified after {snap_alias} was created"))
def given_obs_was_modified(
    snapshot_world: dict[str, Any], obs_id: int, snap_alias: str
) -> None:
    """Mark observation ``obs_id`` as modified AFTER the snapshot."""
    snapshot_world["backend"].update_observation(
        obs_id, content=f"MODIFIED-AFTER-{snap_alias}",
    )


@given(parsers.parse("{n:d} observations were added since {snap_alias}"))
def given_obs_added_since(
    snapshot_world: dict[str, Any], n: int, snap_alias: str
) -> None:
    """Add ``n`` observations to live state AFTER the snapshot."""
    _seed_obs(snapshot_world["backend"], count=n)


# ---------- When steps (REQ-32) ----------


@when(parsers.parse("I rollback to {snap_alias} without --confirm"))
def when_rollback_no_confirm(
    snapshot_world: dict[str, Any], snap_alias: str
) -> None:
    """Attempt rollback WITHOUT ``--confirm`` — expect refusal."""
    real_id = snapshot_world["snap_aliases"][snap_alias]
    mgr = _get_manager(snapshot_world)
    snapshot_world["files_before"] = sorted(
        snapshot_world["snapshots_dir"].glob("snap_*.json.gz")
    )
    snapshot_world["backend_before"] = {
        int(o["id"]): dict(o)
        for o in snapshot_world["backend"].iter_observations()
    }
    try:
        mgr.rollback(real_id, confirm=False)
        snapshot_world["rollback_exception"] = None
    except RollbackRefusedError as exc:
        snapshot_world["rollback_exception"] = exc


@when(parsers.parse("I rollback to {snap_alias} with --confirm"))
def when_rollback_with_confirm(
    snapshot_world: dict[str, Any], snap_alias: str
) -> None:
    """Attempt rollback WITH ``--confirm`` — may succeed or conflict."""
    real_id = snapshot_world["snap_aliases"][snap_alias]
    mgr = _get_manager(snapshot_world)
    snapshot_world["files_before"] = sorted(
        snapshot_world["snapshots_dir"].glob("snap_*.json.gz")
    )
    snapshot_world["backend_before"] = {
        int(o["id"]): dict(o)
        for o in snapshot_world["backend"].iter_observations()
    }
    try:
        result = mgr.rollback(real_id, confirm=True)
        snapshot_world["rollback_result"] = result
        snapshot_world["rollback_exception"] = None
        if isinstance(result, RollbackResult):
            snapshot_world["safety_snap_id"] = result.safety_snapshot_id
    except RollbackConflictError as exc:
        snapshot_world["rollback_exception"] = exc


# ---------- Then steps (REQ-32) ----------


@then("the rollback fails with refusal")
def then_rollback_refused(snapshot_world: dict[str, Any]) -> None:
    exc = snapshot_world["rollback_exception"]
    assert exc is not None, "expected RollbackRefusedError; got success"
    assert isinstance(exc, RollbackRefusedError), (
        f"expected RollbackRefusedError, got {type(exc).__name__}: {exc}"
    )
    payload = exc.payload
    assert payload["error"] == (
        "--confirm required to write; use --dry-run to preview"
    )
    assert "snap_id" in payload


@then("the live state is unchanged")
def then_live_state_unchanged(snapshot_world: dict[str, Any]) -> None:
    """Verify live backend observations match what was there BEFORE the rollback."""
    before = snapshot_world.get("backend_before", {})
    current = {
        int(o["id"]): dict(o)
        for o in snapshot_world["backend"].iter_observations()
    }
    assert current.keys() == before.keys(), (
        f"live state ID set changed: before={sorted(before)} after={sorted(current)}"
    )
    for oid, before_obs in before.items():
        cur_obs = current[oid]
        assert cur_obs["content"] == before_obs["content"], (
            f"obs {oid} content changed: "
            f"before={before_obs['content']!r} after={cur_obs['content']!r}"
        )


@then("no safety snapshot was created")
def then_no_safety_snapshot(snapshot_world: dict[str, Any]) -> None:
    """File count in snapshots_dir is unchanged from BEFORE the rollback attempt."""
    files_after = sorted(snapshot_world["snapshots_dir"].glob("snap_*.json.gz"))
    files_before = snapshot_world.get("files_before", [])
    assert len(files_after) == len(files_before), (
        f"snapshot count changed from {len(files_before)} to {len(files_after)}; "
        f"safety snapshot was created even though --confirm was absent"
    )


@then(parsers.parse("the rollback succeeds with safety_snapshot_id and target_snapshot_id {snap_alias}"))
def then_rollback_succeeds(
    snapshot_world: dict[str, Any], snap_alias: str
) -> None:
    result = snapshot_world["rollback_result"]
    assert result is not None, (
        f"expected RollbackResult; got exception={snapshot_world['rollback_exception']}"
    )
    expected_target = snapshot_world["snap_aliases"][snap_alias]
    assert result.target_snapshot_id == expected_target
    assert isinstance(result.safety_snapshot_id, str)
    assert result.safety_snapshot_id.startswith("snap_")


@then(parsers.parse('the safety snapshot was created with trigger "{trigger}"'))
def then_safety_trigger(
    snapshot_world: dict[str, Any], trigger: str
) -> None:
    safety_id = snapshot_world["safety_snap_id"]
    assert safety_id is not None
    safety_path = snapshot_world["snapshots_dir"] / f"{safety_id}.json.gz"
    envelope = _read_envelope_safe(safety_path)
    assert envelope["trigger"] == trigger, (
        f"expected trigger {trigger!r}, got {envelope.get('trigger')!r}"
    )


@then(parsers.parse('the safety snapshot description starts with "{prefix}"'))
def then_safety_description_prefix(
    snapshot_world: dict[str, Any], prefix: str
) -> None:
    safety_id = snapshot_world["safety_snap_id"]
    safety_path = snapshot_world["snapshots_dir"] / f"{safety_id}.json.gz"
    envelope = _read_envelope_safe(safety_path)
    assert envelope["description"].startswith(prefix), (
        f"expected description to start with {prefix!r}; "
        f"got {envelope.get('description')!r}"
    )


@then(parsers.parse("observation {obs_id:d} content is restored to the original"))
def then_obs_content_restored(
    snapshot_world: dict[str, Any], obs_id: int
) -> None:
    expected = snapshot_world["original_obs_content"].get(obs_id)
    assert expected is not None, (
        f"no original content captured for obs {obs_id}"
    )
    current = snapshot_world["backend"].mem_get_observation(obs_id)
    assert current["content"] == expected, (
        f"obs {obs_id} content not restored: expected {expected!r}; "
        f"got {current['content']!r}"
    )


@then(parsers.parse("the rollback fails with conflict listing the {n:d} new observation IDs"))
def then_rollback_conflict(
    snapshot_world: dict[str, Any], n: int
) -> None:
    exc = snapshot_world["rollback_exception"]
    assert exc is not None and isinstance(exc, RollbackConflictError), (
        f"expected RollbackConflictError; got {exc!r}"
    )
    payload = exc.payload
    conflict_ids = {c["id"] for c in payload["conflicts"]}
    assert len(conflict_ids) == n, (
        f"expected {n} conflicts; got {len(conflict_ids)}: {conflict_ids}"
    )
    assert all(c["change"] == "added" for c in payload["conflicts"]), (
        f"expected all changes to be 'added'; got "
        f"{[c['change'] for c in payload['conflicts']]}"
    )


@then("the safety snapshot was still created")
def then_safety_still_created(snapshot_world: dict[str, Any]) -> None:
    """Even on conflict, the safety snapshot must exist (D11 ordering)."""
    files_after = sorted(snapshot_world["snapshots_dir"].glob("snap_*.json.gz"))
    files_before = snapshot_world.get("files_before", [])
    assert len(files_after) == len(files_before) + 1, (
        f"safety snapshot must be created even on conflict; "
        f"file count: before={len(files_before)} after={len(files_after)}"
    )
    # Find the safety snapshot by its trigger field — hex suffix sorts
    # arbitrarily so the file-list ordering is unreliable.
    found_safety = False
    for path in files_after:
        envelope = _read_envelope_safe(path)
        if envelope.get("trigger") == "rollback_safety":
            found_safety = True
            break
    assert found_safety, (
        "expected a snapshot file with trigger='rollback_safety'; "
        f"triggers found: "
        f"{[_read_envelope_safe(p).get('trigger') for p in files_after]}"
    )


def _read_envelope_safe(path: Path) -> dict[str, Any]:
    """Read + gunzip + json.loads the snapshot envelope at ``path``."""
    import gzip as _gzip
    with _gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.loads(fh.read())


# ============================================================
# REQ-34: snapshot retention pruning (2 scenarios)
# ============================================================


@scenario(
    "../bdd/req34_snapshot_prune.feature",
    "Prune with --keep-last evicts oldest beyond N",
)
def test_req34_prune_keep_last_evicts_oldest(snapshot_world):
    pass


@scenario(
    "../bdd/req34_snapshot_prune.feature",
    "Prune without --confirm is dry-run",
)
def test_req34_prune_dry_run_no_confirm(snapshot_world):
    pass


# ---------- Given steps (REQ-34) ----------


@given(parsers.parse("{n:d} snapshots exist with timestamps spanning {n:d} days"))
def given_n_snapshots_spanning_days(
    snapshot_world: dict[str, Any], n: int,
) -> None:
    """Create ``n`` snapshots backdated to cover ``n`` distinct days.

    The newest snapshot uses ``now``; each older snapshot is backdated by
    one additional day (via envelope ``created_at`` rewrite, since the
    snap_id encodes the wall-clock at create time). The InMemoryBackend
    is seeded once so all snapshots observe the same observation set.
    """
    snapshot_world["snapshots_dir"].mkdir(parents=True, exist_ok=True)
    mgr = _get_manager(snapshot_world)
    _seed_obs(snapshot_world["backend"], count=1)

    import gzip as _gzip
    import hashlib as _hashlib
    from datetime import UTC, datetime, timedelta

    ids: list[str] = []
    for offset in range(n):
        sid = mgr.create(description=f"day-{offset}")
        ids.append(sid)
        # Backdate the envelope so the ``created_at`` reflects the offset.
        path = snapshot_world["snapshots_dir"] / f"{sid}.json.gz"
        with _gzip.open(path, "rt", encoding="utf-8") as fh:
            envelope = json.loads(fh.read())
        backdated = datetime.now(UTC) - timedelta(days=(n - 1 - offset))
        envelope["created_at"] = backdated.strftime("%Y-%m-%dT%H:%M:%SZ")
        meta_for_hash = {
            k: v for k, v in envelope["metadata"].items() if k != "sha256"
        }
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = meta_for_hash
        envelope["metadata"]["sha256"] = _hashlib.sha256(
            _canonical_json_dumps(envelope_for_hash).encode("utf-8")
        ).hexdigest()
        with _gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(_canonical_json_dumps(envelope))
        snapshot_world["snap_ids"].append(sid)
        snapshot_world["created_at_by_id"][sid] = envelope["created_at"]


@given(parsers.parse("the {n:d} oldest are NOT pinned and NOT the most recent"))
def given_n_oldest_not_pinned(
    snapshot_world: dict[str, Any], n: int,
) -> None:
    """Sanity precondition — the 3 oldest snapshots are regular (un-pinned).

    The current spec creates all snapshots un-pinned by default, so this
    step is mostly a contract assertion for the feature's intent.
    """
    import gzip as _gzip
    oldest_ids = snapshot_world["snap_ids"][:n]
    for sid in oldest_ids:
        path = snapshot_world["snapshots_dir"] / f"{sid}.json.gz"
        with _gzip.open(path, "rt", encoding="utf-8") as fh:
            envelope = json.loads(fh.read())
        assert envelope["metadata"].get("pinned", False) is False, (
            f"expected oldest snapshot {sid} to NOT be pinned"
        )


@given(parsers.parse("{n:d} snapshots exist"))
def given_n_snapshots_simple(
    snapshot_world: dict[str, Any], n: int,
) -> None:
    """Plain ``Given N snapshots exist`` setup (no date span)."""
    snapshot_world["snapshots_dir"].mkdir(parents=True, exist_ok=True)
    mgr = _get_manager(snapshot_world)
    _seed_obs(snapshot_world["backend"], count=1)
    for i in range(n):
        sid = mgr.create(description=f"snap-{i}")
        snapshot_world["snap_ids"].append(sid)
        if i < n - 1:
            time.sleep(1.01)


# ---------- When steps (REQ-34) ----------


@when(parsers.parse("I run flow snapshot prune with --keep-last {n:d} and --confirm"))
def when_prune_keep_last_with_confirm(
    snapshot_world: dict[str, Any], n: int,
) -> None:
    """Invoke ``SnapshotManager.prune(keep_last=N, confirm=True)``."""
    mgr = _get_manager(snapshot_world)
    snapshot_world["files_before"] = sorted(
        p.name for p in snapshot_world["snapshots_dir"].glob("snap_*.json.gz")
    )
    snapshot_world["prune_exception"] = None
    try:
        snapshot_world["prune_result"] = mgr.prune(keep_last=n, confirm=True)
    except (PruneNoFilterError, PruneSafetyGateError) as exc:
        snapshot_world["prune_exception"] = exc


@when(parsers.parse("I run flow snapshot prune with --keep-last {n:d} (no --confirm)"))
def when_prune_keep_last_no_confirm(
    snapshot_world: dict[str, Any], n: int,
) -> None:
    """Invoke ``SnapshotManager.prune(keep_last=N)`` (dry-run)."""
    mgr = _get_manager(snapshot_world)
    snapshot_world["files_before"] = sorted(
        p.name for p in snapshot_world["snapshots_dir"].glob("snap_*.json.gz")
    )
    snapshot_world["prune_exception"] = None
    try:
        snapshot_world["prune_result"] = mgr.prune(keep_last=n, confirm=False)
    except (PruneNoFilterError, PruneSafetyGateError) as exc:
        snapshot_world["prune_exception"] = exc


# ---------- Then steps (REQ-34) ----------


@then(parsers.parse("exactly {n:d} snapshot files are removed"))
def then_n_files_removed(
    snapshot_world: dict[str, Any], n: int,
) -> None:
    before = len(snapshot_world["files_before"])
    after_files = sorted(
        p.name for p in snapshot_world["snapshots_dir"].glob("snap_*.json.gz")
    )
    after = len(after_files)
    assert before - after == n, (
        f"expected exactly {n} files removed (before={before}, after={after}); "
        f"removed={set(snapshot_world['files_before']) - set(after_files)}"
    )
    snapshot_world["files_after"] = after_files


@then(parsers.parse("the remaining {n:d} are the {n:d} most recent"))
def then_remaining_are_most_recent(
    snapshot_world: dict[str, Any], n: int,
) -> None:
    """The ``n`` remaining snapshot ids are the ``n`` most recent (last n)."""
    remaining_ids = [
        p.name.replace(".json.gz", "") for p in (
            snapshot_world["snapshots_dir"].glob("snap_*.json.gz")
        )
    ]
    expected = snapshot_world["snap_ids"][-n:]
    assert set(remaining_ids) == set(expected), (
        f"expected remaining={expected!r}; got {remaining_ids!r}"
    )


@then("no snapshot files are removed")
def then_no_files_removed(snapshot_world: dict[str, Any]) -> None:
    after_files = sorted(
        p.name for p in snapshot_world["snapshots_dir"].glob("snap_*.json.gz")
    )
    assert after_files == snapshot_world["files_before"], (
        f"dry-run MUST NOT touch files; before={snapshot_world['files_before']} "
        f"after={after_files}"
    )


@then(parsers.parse("the prune output lists {n:d} \"would delete\" ids"))
def then_prune_would_delete_count(
    snapshot_world: dict[str, Any], n: int,
) -> None:
    """``result.would_delete`` has ``n`` ids and ``result.dry_run`` is True."""
    result = snapshot_world["prune_result"]
    assert isinstance(result, PruneResult), (
        f"expected PruneResult; got {type(result).__name__}: {result!r}"
    )
    assert result.dry_run is True
    assert len(result.would_delete) == n, (
        f"expected {n} would_delete ids; got {len(result.would_delete)}: "
        f"{result.would_delete!r}"
    )


@then("the prune command exit code is 0")
def then_prune_exit_zero(snapshot_world: dict[str, Any]) -> None:
    """The library call returned a PruneResult (no exception)."""
    exc = snapshot_world.get("prune_exception")
    assert exc is None, f"unexpected prune exception: {exc!r}"
    assert snapshot_world.get("prune_result") is not None
