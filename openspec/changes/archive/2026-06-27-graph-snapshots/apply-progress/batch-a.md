# sdd/graph-snapshots/apply-progress-batch-a

## Goal
SDD apply batch A of graph-snapshots (PR first slice): T1.1 (SnapshotManager scaffold + create + list) + T1.2 (show + diff methods) + BDD req28..31 (7 scenarios). Foundation: snapshot file format, sha256 integrity, atomic write, first-run `initial_state` label, reverse-chronological list, structured JSON diff output.

## Branch / PR State
- Branch: feature/graph-snapshots
- Baseline (pre-batch A setup HEAD): b98de4d
- Batch A final HEAD: 2c7a5b1
- Working tree: CLEAN (verified `git status --short`)

## Commits (5 — work-unit per commit, strict TDD)
1. `5699d6e` test(unit): RED fixtures for SnapshotManager create + list + gzipped JSON + sha256
2. `296cae5` feat(snapshot): SnapshotManager scaffold with create + list methods (REQ-28 + REQ-29)
3. `8888e28` test(unit): RED fixtures for SnapshotManager show + diff
4. `743c134` feat(snapshot): SnapshotManager show + diff with structured JSON output (REQ-30 + REQ-31)
5. `2c7a5b1` test(bdd): req28+req29+req30+req31 snapshot features with 7 scenarios

## LOC Delta (batch A)
- src/flow_engineering/snapshot_manager.py: ~+600 (SnapshotManager class + create + list + show + diff + 4 exceptions + 4 dataclasses + sha256 helpers + atomic write)
- tests/unit/test_snapshot_manager.py: ~+500 (TestCreateRoundTrip + TestLazyCreate + TestAtomicWrite + TestFirstRunLabel + TestSnapshotIdFormat + TestCreatePopulatesGraphJsonContent + TestListOrdering + TestSinceFilter + TestLimit + TestEmptyDir + TestSnapshotMetaShape + TestShow + TestDiffTwoArg + TestDiffOneArgVsLive)
- tests/bdd/req28_snapshot_create.feature: NEW (2 scenarios)
- tests/bdd/req29_snapshot_list.feature: NEW (2 scenarios)
- tests/bdd/req30_snapshot_show.feature: NEW (1 scenario)
- tests/bdd/req31_snapshot_diff.feature: NEW (2 scenarios)
- tests/bdd/test_graph_snapshots_steps.py: ~+300 (step glue for req28..31)
- Total batch A: ~+1700 lines

## Test Delta (cumulative)
- Pre-change baseline (v0.5.0): 699
- After batch A: 729 (+30 — 23 unit + 7 BDD)

## BDD Coverage Delta (cumulative)
- Pre-change baseline: 9 scenarios across 9 feature files
- After batch A: 14 scenarios across 13 feature files (+7 — req28/29/30/31 snapshot_create + list + show + diff)
  - req28_snapshot_create: 2 (round-trip + description override)
  - req29_snapshot_list: 2 (3-snapshot reverse order + since filter)
  - req30_snapshot_show: 1 (round-trip)
  - req31_snapshot_diff: 2 (2-arg + 1-arg-vs-live)

## Cumulative Non-Regression
- 699 baseline tests (v0.5.0) all still pass — additive change confirmed
- SnapshotManager.create() default behavior preserves gzipped JSON + sha256 integrity
- SnapshotManager.diff() 1-arg form diffs against live state (current observations + current graph.json)
- All public methods return dataclasses (SnapshotMeta, SnapshotEnvelope, DiffResult); exceptions for tamper/parse

## Deviations from Design
- None material. Implementation follows D1 (SnapshotManager class API) + D2 (Envelope schema v1) + D7 (filesystem-safe file naming) + D9 (structured JSON diff output).

## Risks / Blockers
- None — 729 tests pass after batch A

## Next
- Batch B1: T1.3 (rollback with auto-safety + conflict + force) + T1.4 (decision_drift snap_id kwarg) + BDD req32 + req33

## Key Files Touched (batch A)
- src/flow_engineering/snapshot_manager.py — SnapshotManager class + create + list + show + diff
- tests/unit/test_snapshot_manager.py — 14 unit test classes (RED + GREEN)
- tests/bdd/req28_snapshot_create.feature — NEW
- tests/bdd/req29_snapshot_list.feature — NEW
- tests/bdd/req30_snapshot_show.feature — NEW
- tests/bdd/req31_snapshot_diff.feature — NEW
- tests/bdd/test_graph_snapshots_steps.py — step glue for req28..31

## Related Memory
- Per-batch key: `#178 [architecture] sdd/graph-snapshots/apply-progress-batch-a`
- Merged observation: `#187 [architecture] sdd/graph-snapshots/apply-progress` (supersedes this)
