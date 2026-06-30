# Change Status: flow-where-cross-project

**Status**: ARCHIVED
**Archived**: 2026-06-29
**Branch**: `codex/flow-where-cross-project`
**Merged**: NO (local-only, awaiting user push/merge authorization)
**Commits**: 1 feat commit + 1 chore commit. 9 verification gates pass. 10 new unit tests + 14 prior Phase 1 tests + 10 Phase 3 tests pass. AC9 byte-identical contract preserved.

## Final verification verdict
- 9 of 9 verification gates PASS (per verify-report #460).
- 10 new unit tests pass + 14 prior Phase 1 tests pass (AC9 byte-identical test included).
- 10 Phase 3 tests pass (workspace-status change unaffected).
- 1235 of 1235 unit tests pass in `tests/unit/`.
- 3 output formats work (text default, json envelope, tsv).
- 6 search directories used (prospec).
- Exit codes: 0=match-or-empty, 1=no-match, 2=error.
- `--engram` stub accepted (no behavior change in v1).

## Change summary
Adds a `flow where <query> --root PATH [--format {text,json,tsv}] [--regex] [--engram] [--limit N]` cross-project search across 6 prospec directories (`src/`, `internal/`, `cmd/`, `tests/`, `openspec/`, `graphify-out/`) per project under `--root`. Additive to existing `where_cmd` (preserves `--limit`, `--no-graph`, `--pretty`). Reuses existing `_run_search` from `where.py` (read-only on `where.py` module API). 10 new unit tests in `test_cli_where_cross_project.py` reuse `_workspace_fixtures.py` from Phase 3 (read-only).

## Scope preservation
- Phase 1 (`flow-projects-ls--json`) byte-identical contract preserved — AC9 test passes.
- Phase 3 (`flow-workspace-status`) tests unaffected.
- `where.py` module API unchanged.
- `tests/unit/_workspace_fixtures.py` unchanged (Phase 3 shared fixtures).
- `_detect_project_markers` (Phase 1) and `_resolve_projects_root` (Phase 3) untouched.

## Risks documented
- `where.py` is read-only; Phase 2 uses a custom `_parse_cross_project` parser because `where._parse_hits` splits on `:` (3 parts) and mis-segments rg output for content with colons (e.g. `def foo(): pass`).
- Phase 2 calls `_run_search` per-directory (not batched) because rg returns rc=2 when any missing path is passed; per-dir calls fail-open (discard stdout on rc=2).
- Scope budget exceeded (685 LOC vs 400 nominal) due to docstrings + inline test fixture; production logic itself is well within budget. Size:exception accepted by user 2026-06-29.

## Cross-references (engram)
- explore: #454
- proposal: #455
- spec: #456
- design: #457
- tasks: #458
- apply-progress: #459
- verify-report: #460
- archive-report: <NEW ID>

## Branch
`codex/flow-where-cross-project` is preserved locally with 1 feat commit at `c421540` plus the chore commit that adds this status file. The user decides whether to merge to main and push to the fork. If merged + pushed, this is Phase 2 of the workspace-intelligence effort; Phase 3 (flow-workspace-status) is already pushed; Phase 1 is also pushed.
