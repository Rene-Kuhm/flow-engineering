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
