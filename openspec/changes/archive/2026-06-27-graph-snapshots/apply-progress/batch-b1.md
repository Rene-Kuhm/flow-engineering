# sdd/graph-snapshots/apply-progress-batch-b1

## Goal
SDD apply batch B1 of graph-snapshots (PR second slice): T1.3 (rollback with auto-safety snapshot + conflict detection + `--force` override) + T1.4 (`decision_drift.load_graph` + `scan_change` `snap_id` kwarg for drift-pinned historical scan, NON-BREAKING). BDD req32 (3 scenarios) + req33 (2 scenarios).

## Branch / PR State
- Branch: feature/graph-snapshots
- Baseline (batch A HEAD): 2c7a5b1
- Batch B1 final HEAD: 3655a82
- Working tree: CLEAN (verified `git status --short`)

## Commits (6 — work-unit per commit, strict TDD)
1. `153ed87` test(unit): RED fixtures for rollback with --confirm + conflict detection + auto-safety + --force override
2. `acd8a2e` feat(snapshot): rollback with auto-safety snapshot + conflict detection + atomic apply (REQ-32)
3. `5af33e7` test(bdd): req32_snapshot_rollback feature with 3 scenarios (refusal + success + conflict)
4. `4980aab` test(unit): RED fixtures for decision_drift.load_graph(snap_id=...) + scan_change(snap_id=...) kwarg
5. `3b6c111` feat(drift): load_graph + scan_change accept snap_id kwarg (NON-BREAKING, REQ-33)
6. `3655a82` test(bdd): req33_drift_pinned feature with 2 scenarios (frozen-state + non-breaking)

## LOC Delta (batch B1)
- src/flow_engineering/snapshot_manager.py: ~+300 (rollback method + RollbackRefusedError + RollbackConflictError + safety snapshot logic + atomic SQLite txn)
- src/flow_engineering/decision_drift.py: ~+300 (snap_id kwarg + _load_graph_from_snapshot + _snapshot_has_graph + _frozen_backend_from_snapshot + _DummyBackend + scan_change extension + SnapshotGraphMissing)
- tests/unit/test_snapshot_manager.py: ~+200 (TestRollbackRefusedWithoutConfirm + TestRollbackAutoSafetySnapshot + TestRollbackConflictRefused + TestRollbackForceOverride + TestRollbackIdempotency)
- tests/unit/test_decision_drift_snap_id.py: ~+447 (NEW — 8 tests for snap_id kwarg)
- tests/bdd/req32_snapshot_rollback.feature: NEW (3 scenarios)
- tests/bdd/req33_drift_pinned.feature: NEW (2 scenarios)
- tests/bdd/test_graph_snapshots_steps.py: ~+150 (step glue for req32)
- tests/bdd/test_decision_reality_drift_steps.py: ~+232 (step glue for req33 — registered there per apply-progress-batch-b1 deviation)
- Total batch B1: ~+1629 lines

## Test Delta (cumulative)
- After batch A: 729
- After batch B1: 754 (+25 — 20 unit + 5 BDD)

## BDD Coverage Delta (cumulative)
- After batch A: 14 scenarios across 13 feature files
- After batch B1: 19 scenarios across 15 feature files (+5 — req32 rollback + req33 drift_pinned)
  - req32_snapshot_rollback: 3 (refusal + success + conflict)
  - req33_drift_pinned: 2 (frozen-state + non-breaking — registered in test_decision_reality_drift_steps.py)

## Cumulative Non-Regression
- 699 baseline tests (v0.5.0) all still pass — additive seam extension confirmed
- `decision_drift.load_graph(snap_id=None)` default behavior is byte-identical to pre-change
- `decision_drift.scan_change(snap_id=None)` default behavior is byte-identical to pre-change
- `snap_id` is kwarg-only with `None` default — no caller breakage possible
- Two-phase rollback: safety snapshot first, atomic SQLite txn second (D11)
- `--force` override emits stderr warning + counter increment

## Deviations from Design
- SnapshotGraphMissing(Exception) in snapshot_manager.py is a SEPARATE class from the existing SnapshotGraphMissing(ValueError) in decision_drift.py — both exist for discoverability. The brief said Exception parent; the existing one inherits from ValueError.
- BDD req33 scenarios registered in `test_decision_reality_drift_steps.py` (not `test_graph_snapshots_steps.py`) — discovered during batch B1 that the existing step glue already covered load_graph fixtures. Test names are `test_drift_pinned_*` not `test_req33_*` (carry-forward to S22 in verify-report).

## Risks / Blockers
- None — 754 tests pass after batch B1

## Next
- Batch B2: T1.5 (flow snapshot CLI subcommand group + flow drift --snapshot flag)

## Key Files Touched (batch B1)
- src/flow_engineering/snapshot_manager.py — rollback method + 2 exceptions + safety logic
- src/flow_engineering/decision_drift.py — snap_id kwarg + load_graph extension + scan_change extension + SnapshotGraphMissing
- tests/unit/test_snapshot_manager.py — 5 rollback test classes
- tests/unit/test_decision_drift_snap_id.py — NEW (8 tests)
- tests/bdd/req32_snapshot_rollback.feature — NEW
- tests/bdd/req33_drift_pinned.feature — NEW
- tests/bdd/test_graph_snapshots_steps.py — step glue for req32
- tests/bdd/test_decision_reality_drift_steps.py — step glue for req33

## Related Memory
- Per-batch key: `#179 [architecture] sdd/graph-snapshots/apply-progress-batch-b1`
- Merged observation: `#187 [architecture] sdd/graph-snapshots/apply-progress` (supersedes this)
