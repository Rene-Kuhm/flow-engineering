# sdd/graph-snapshots/apply-progress-batch-b2

## Goal
SDD apply batch B2 of graph-snapshots (PR third slice): T1.5 (flow snapshot CLI subcommand group + flow drift --snapshot flag) + REQ-33 gap fix (SnapshotManager.create() populates graph_state.graph_json_content). Wires the public API to Click CLI surface; closes the loop so `flow drift <change> --snapshot=<id>` can read the frozen graph from the snapshot envelope.

## Branch / PR State
- Branch: feature/graph-snapshots
- Baseline (batch B1 HEAD): 3655a82
- Batch B2 final HEAD: 80d82f1
- Working tree: CLEAN (verified `git status --short`)

## Commits (3 — work-unit per commit, strict TDD)
1. `7e4ab7d` fix(snapshot): SnapshotManager.create() populates graph_state.graph_json_content (REQ-33 gap fix)
2. `ded27d4` test(unit): RED fixtures for flow snapshot CLI subcommands + drift --snapshot flag
3. `80d82f1` feat(cli): flow snapshot subcommand group + flow drift --snapshot flag (NON-BREAKING, REQ-28..33)

## LOC Delta (batch B2)
- src/flow_engineering/snapshot_manager.py: +30 / -10 net (create() extension to populate graph_state.graph_json_content)
- src/flow_engineering/cli.py: ~+500 (flow snapshot group with 5 subcommands: create + list + show + diff + rollback + 5 helper functions + flow drift --snapshot flag)
- tests/unit/test_cli_snapshot.py: ~+566 (NEW — 17 CLI tests across create/list/show/diff/rollback/drift-snapshot)
- Total batch B2: ~+1086 lines

## Test Delta (cumulative)
- After batch B1: 754
- After batch B2: 774 (+20 — 3 snapshot_manager graph_json_content + 17 cli_snapshot)

## BDD Coverage Delta (cumulative)
- After batch B1: 19 scenarios across 15 feature files
- After batch B2: 19 scenarios (CLI tests are unit-level, no new BDD)

## Cumulative Non-Regression
- 699 baseline tests (v0.5.0) all still pass — additive CLI surface confirmed
- `flow snapshot <subcmd>` group is non-breaking — pre-existing `flow <verb>` commands unchanged
- `flow drift <change>` without --snapshot is byte-identical to pre-change (D13 non-breaking)
- Click 8.4 result.stdout (pure stdout) instead of legacy result.output (combined). Click 8.4 separates streams cleanly; click 8.0 had mix_stderr=True default that polluted result.output with stderr warnings. Documented in test file docstring.

## Deviations from Design
- Click 8.4 result.stdout (pure stdout) instead of legacy result.output (combined) — Click 8.4 separates streams cleanly; click 8.0 had mix_stderr=True default that polluted result.output with stderr warnings. Documented in test file docstring.
- --json flag NOT yet wired on `flow snapshot list` or `flow snapshot diff` (added in W22 post-archive fix). `flow snapshot prune` (batch C) has --json. W22 resolved in commit `5ef8f0e`.

## Risks / Blockers
- None — 774 tests pass after batch B2

## Next
- Batch C: T1.6 (prune retention policy + CLI) + T1.7 (4 SNAPSHOT counters + record_snapshot_event) + T1.8 (CHANGELOG v0.6.0 + 6 SKILL.md sections)

## Key Files Touched (batch B2)
- src/flow_engineering/snapshot_manager.py — create() graph_json_content extension
- src/flow_engineering/cli.py — flow snapshot subcommand group + flow drift --snapshot flag
- tests/unit/test_cli_snapshot.py — NEW (17 tests)

## Related Memory
- Per-batch key: `#180 [architecture] sdd/graph-snapshots/apply-progress-batch-b2`
- Merged observation: `#187 [architecture] sdd/graph-snapshots/apply-progress` (supersedes this)
