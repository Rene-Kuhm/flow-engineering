# Status: flow-workspace-status

Status: ARCHIVED
Verdict: PASS
Date: 2026-06-29

## Summary

Implemented `flow workspace status` as Phase 3 of workspace intelligence.

## Shipped

- Added top-level `flow workspace status` command.
- Added deterministic `--json` envelope with key order: `version`, `root`, `totals`, `projects`, `needs_attention`.
- Added needs-attention rules:
  - R1: git project with dirty worktree.
  - R2: project without git.
  - R3: project without detected tests.
  - R4: Python/Go/Rust project without OpenSpec.
  - R5: graphify missing is informational-only in v1.
- Added shared workspace test fixtures.
- Added unit coverage for text output, JSON output, empty root, deterministic bytes, R1-R5, and Phase 1 guard.

## Verification

- `uv run --frozen pytest tests/unit/test_cli_projects.py tests/unit/test_cli_workspace_status.py -q` -> PASS, 24 passed.
- `uv run --frozen pytest tests/ -q` -> PASS, 1434 passed, 6 known deprecation warnings.
- `uv run --frozen ruff check .` -> PASS.
- `uv run --frozen mypy src/` -> PASS.
- Live smoke: `flow workspace status --root C:\dev\proyects --json` parses as JSON.

## Notes

- No `generated_at` or timestamp fields in v1 JSON; byte-identical output remains possible for unchanged roots.
- `flow projects ls --json` schema remains unchanged.
- `flow where` was not touched.
- `has_graphify` and `has_engram` remain informational/stub-derived in this phase.

## Commits

- `e7abfff feat(cli): add flow workspace status command`
- `b53baa0 test(cli): cover flow workspace status rules`
