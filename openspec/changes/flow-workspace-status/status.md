# Change Status: flow-workspace-status

**Status**: ARCHIVED
**Archived**: 2026-06-29
**Branch**: `codex/flow-workspace-status`
**Merged**: NO (local-only, awaiting user push/merge authorization)
**Commits**: 1 commit (`ba26df9`). 24/24 tests pass (10 new + 14 prior). AC9 byte-identical contract preserved. Read-only aggregation on Phase 1's v1 JSON envelope.

## Final verification verdict
- 9 of 9 verification gates PASS (per verify-report Engram #451).
- 10 new unit tests pass + 14 prior tests pass (AC9 byte-identical test included).
- R5 (graphify) confirmed informational-only — does NOT populate `needs_attention`.
- No `flow where` modifications (Phase 2 out of scope; only type-annotation style change in `where_cmd` signature).
- No `generated_at` in JSON envelope (byte-determinism requirement).
- 5 needs-attention rules (R1-R4 counting + R5 informational-only).

## Change summary
Adds a top-level `flow workspace status` subcommand that consumes Phase 1's `_detect_project_markers` output and synthesizes a status report. Default human-readable text + `--json` flag for machine-readable output. Reads Phase 1's v1 JSON envelope data (11 fields per project) directly via the same internal helper; no subprocess to `flow projects ls`. Aggregates totals + 5 needs-attention rules + JSON envelope assembly.

## Scope preservation
- `flow projects ls` (Phase 1) byte-identical contract preserved — AC9 guard.
- `flow where` (Phase 2) out of scope — NOT modified.
- `flow projects` parent group unchanged (the new subcommand is at top-level `@main.group('workspace')`).

## Documented pre-existing findings (not introduced by this change)
1. **Pre-existing bug at `if __name__ == '__main__': main()` guard** in `src/flow_engineering/cli.py` — fires before `workspace_group` registration. The `.venv\Scripts\flow.exe` entry point works correctly. The `python -m flow_engineering.cli` path fails; this is pre-existing, not caused by this change.
2. **4 pre-existing test failures** in `tests/unit/` (independently reproduced on `main`):
   - `test_cli_metrics_aggregate::test_metrics_aggregate_with_window_filter`
   - `test_cli_metrics_export::test_metrics_export_with_window_filter`
   - `test_observability_aggregate::test_window_filter_integration_with_export`
   - `test_observability_aggregate::test_window_filter_with_domain_composes_and_style`
   - Root cause: `flow_snapshot_create_total` returns 2.0 vs expected 1.0 in window/domain composite filter. NOT introduced by this change.
3. **Budget overrun**: 785 insertions / 620 deletions across 4 files (production ~100 LOC within budget; test+ruff-format collateral accounts for overage). Size:exception accepted by user 2026-06-29.

## Cross-references (engram)
- explore: #445
- proposal: #446
- spec: #447
- design: #448
- tasks: #449
- apply-progress: #450
- verify-report: #451
- archive-report: #452

## Branch
`codex/flow-workspace-status` is preserved locally with 1 commit at `ba26df9`. The user decides whether to merge to main and push to their fork. If merged + pushed, this is Phase 3 of the workspace-intelligence effort; Phase 2 (`flow where`), Phase 4 (workspace hygiene), and Phase 5 (dashboard) remain pending.