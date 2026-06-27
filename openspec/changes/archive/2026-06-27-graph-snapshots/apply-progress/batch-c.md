# sdd/graph-snapshots/apply-progress-batch-c

## Goal
SDD apply batch C of graph-snapshots (PR finalization): T1.6 (SnapshotManager.prune retention policy + flow snapshot prune CLI) + T1.7 (4 SNAPSHOT observability counters + SNAPSHOT_COUNTER_NAMES catalog + record_snapshot_event helper + 4 wirings) + T1.8 (CHANGELOG v0.6.0 + 6 SKILL.md Graph snapshots hook sections).

## Branch / PR State
- Branch: feature/graph-snapshots
- Baseline (batch B2 HEAD): 80d82f1
- Final HEAD: 50656a8
- Working tree: CLEAN (verified `git status --short` — only `?? openspec/changes/observability/` from change #6 explore, OUT OF SCOPE)

## Commits (8 — work-unit per commit, strict TDD)
### T1.6 (4 commits)
1. `3938e6c` test(unit): RED fixtures for SnapshotManager.prune retention policy (REQ-34)
2. `2cd6737` test(bdd): req34_snapshot_prune feature with 2 scenarios + step glue
3. `fa7e5dd` feat(snapshot): complete prune() impl — apply phase + safety nets (REQ-34 GREEN)
4. `64fee25` feat(cli): flow snapshot prune with --keep-last/--keep-days/--max-total-size-mb/--confirm/--force/--json flags

### T1.7 (2 commits — RED then GREEN)
5. `5c92832` test(unit): RED fixtures for 4 SNAPSHOT counters + record_snapshot_event helper (REQ-26)
6. `53d83f9` feat(observability): SNAPSHOT_COUNTER_NAMES catalog + record_snapshot_event + 4 wirings (REQ-26 GREEN)

### T1.8 (2 commits — docs only)
7. `4799eeb` docs(changelog): v0.6.0 entry for graph-snapshots change (REQ-26..34)
8. `50656a8` docs(skills): graph snapshots hook section in 6 SKILL.md runtime files (REQ-26) — --allow-empty (runtime files live outside repo)

## T1.6 LOC Delta
- src/flow_engineering/snapshot_manager.py: ~+250 (PruneResult dataclass, PruneNoFilterError + PruneSafetyGateError exceptions, prune() method with 3 OR-combined retention policies + safety invariants + apply phase, _record_prune_event helper)
- src/flow_engineering/cli.py: ~+200 (flow snapshot prune subcommand with 6 flags + JSON output)
- tests/unit/test_snapshot_manager.py: ~+250 (TestPrune class — keep_last/keep_days/max_total_size_mb/dry-run/most-recent-safety/pinned-safety/force-override)
- tests/unit/test_cli_snapshot.py: ~+200 (TestPruneCommand — 6 unit tests for CLI surface)
- tests/bdd/req34_snapshot_prune.feature: +28 (NEW — 2 scenarios)
- tests/bdd/test_graph_snapshots_steps.py: ~+50 (step glue for req34)
- Total T1.6: ~+978 lines

## T1.7 LOC Delta
- src/flow_engineering/observability.py: ~+70 (SNAPSHOT_COUNTER_NAMES catalog tuple + record_snapshot_event helper + module docstring update)
- src/flow_engineering/snapshot_manager.py: +25 / -10 net (new _record_create_event method, refactored _record_rollback_event + _record_prune_event to use record_snapshot_event, counter rename snapshot_pruned_total -> snapshot_prune_total, snapshot_create_total wiring at end of create() success path)
- src/flow_engineering/decision_drift.py: +10 (snapshot_load_failed_total emit BEFORE SnapshotGraphMissing raise in scan_change)
- tests/unit/test_observability_snapshots.py: +312 (NEW — 9 tests across TestSnapshotCounterCatalog + TestRecordSnapshotEvent + TestSnapshotCreateCounter + TestSnapshotRollbackCounter + TestSnapshotPruneCounter + TestSnapshotLoadFailedCounter)
- Total T1.7: +407 lines / -10 across 4 files

## T1.8 LOC Delta
- CHANGELOG.md: +22 (v0.6.0 entry with Added/Tests/Notes sections)
- 6 SKILL.md runtime files (outside repo): ~+10920 bytes total (~+1800 bytes/file)
  - sdd-propose/SKILL.md: 9106 -> 10943 (+1837)
  - sdd-design/SKILL.md: 8547 -> 10371 (+1824)
  - sdd-tasks/SKILL.md: 12595 -> 14503 (+1908)
  - sdd-apply/SKILL.md: 13003 -> 14869 (+1866)
  - sdd-verify/SKILL.md: 6310 -> 8015 (+1705)
  - sdd-archive/SKILL.md: 8197 -> 9978 (+1781)

## Test Delta (cumulative through batch C)
- Baseline (batch B2): 774 passing
- After T1.6: 790 (+16 — 6 CLI prune + 8 unit prune + 2 BDD req34)
- After T1.7: 799 (+9 — 9 observability_snapshots)
- After T1.8: 799 (no test change)
- **Final batch C: 799 passing in ~61s** (verified `uv run pytest -x --tb=short -q`)

## BDD Coverage Delta (cumulative through batch C)
- Baseline (batch B2): 19 scenarios
- After T1.6: 21 scenarios (+2 — req34_snapshot_prune)
- After T1.7/T1.8: 21 scenarios (no BDD — wiring is unit-level)
- **Final batch C: 21 BDD scenarios across 17 feature files**

## Cumulative Non-Regression
- 699 baseline tests (v0.5.0) all still pass — additive change confirmed
- SnapshotManager.prune() default confirm=False is dry-run — no counter, no file changes
- SnapshotManager.prune() with keep_last=0 requires BOTH confirm=True AND force=True (D10 two-flag safety gate)
- Pinned snapshots are NEVER deleted (force does NOT override pinned invariant)
- 4 SNAPSHOT counters all fire through record_snapshot_event helper (fail-open, never raises)

## Deviations from Design
- Counter rename: existing inline `increment("snapshot_pruned_total")` in prune() refactored to use `record_snapshot_event("snapshot_prune_total")` — drops trailing 'd' to match the SNAPSHOT_COUNTER_NAMES catalog. No consumers exist yet, so wire-format change is safe.
- SnapshotGraphMissing(Exception) in snapshot_manager.py (from batch B2) is the exception class snapshot_manager.prune is documented against. The actual raise happens in decision_drift.scan_change — wiring emits snapshot_load_failed_total at the raise site (not in _load_graph_from_snapshot, which doesn't raise directly).

## Risks / Blockers
- None — 799 tests pass, working tree clean, 22 commits total land cleanly on feature/graph-snapshots

## Next
- sdd-verify: run sdd-verify skill against this change to confirm spec adherence (REQ-28..34, REQ-26 snapshot counters, REQ-33 drift-pinned)
- PR creation: `gh pr create --base main --head feature/graph-snapshots --title "graph-snapshots: SnapshotManager + CLI + observability (REQ-26..34)" --body-file openspec/changes/graph-snapshots/proposal.md`
- PR merge: `gh pr merge --squash --delete-branch`
- sdd-archive: after verify PASS, run sdd-archive to sync delta specs to `openspec/changes/archive/2026-06-27-graph-snapshots/` and create v0.6.0 release commit

## Key Files Touched (batch C)
- src/flow_engineering/snapshot_manager.py — prune() + PruneResult + 2 exceptions + _record_create_event + counter wirings
- src/flow_engineering/cli.py — flow snapshot prune subcommand
- src/flow_engineering/observability.py — SNAPSHOT_COUNTER_NAMES + record_snapshot_event helper
- src/flow_engineering/decision_drift.py — snapshot_load_failed_total emit at SnapshotGraphMissing raise site
- CHANGELOG.md — v0.6.0 entry
- tests/unit/test_snapshot_manager.py — TestPrune class
- tests/unit/test_cli_snapshot.py — TestPruneCommand
- tests/unit/test_observability_snapshots.py — NEW (9 tests)
- tests/bdd/req34_snapshot_prune.feature — NEW (2 scenarios)
- tests/bdd/test_graph_snapshots_steps.py — step glue for req34
- 6 SKILL.md runtime files (outside repo) — Graph snapshots hook section

## Related Memory
- Merged observation: `#187 [architecture] sdd/graph-snapshots/apply-progress` (this session)
- Supersedes: `#178` (batch-a), `#179` (batch-b1), `#180` (batch-b2)
- Per-batch keys remain active for backwards compatibility but `#187` is canonical for orchestrator resume.