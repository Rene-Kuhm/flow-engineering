# Tasks: flow-workspace-status

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | ~220-320 LOC |
| 400-line budget risk | Low/Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR, two commits |
| Delivery strategy | ask-always |
| Chain strategy | stacked-to-main not needed |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Add workspace status production surface | PR 1 | CLI group, root resolver, summary helper, renderers |
| 2 | Add fixtures and regression coverage | PR 1 | Unit tests + Phase 1 guard |

## Phase 1: Production CLI surface

- [x] T-1 Add `_resolve_projects_root(root)` in `src/flow_engineering/cli.py` and update `projects_ls` to use it without changing its output contract.
- [x] T-2 Add `_summarize_workspace_status(projects)` implementing R1-R4 needs-attention and R5 informational-only behavior.
- [x] T-3 Add deterministic `_workspace_status_envelope(root, projects, summary)` with key order `version`, `root`, `totals`, `projects`, `needs_attention`; no timestamp fields.
- [x] T-4 Add `_render_workspace_status_text(root, projects, summary)` with readable per-project status and bottom summary.
- [x] T-5 Add top-level `flow workspace status [--root PATH] [--json]` command that scans once via `_detect_project_markers` and renders text/JSON.

## Phase 2: Fixtures and tests

- [x] T-6 Create/extend `tests/unit/_workspace_fixtures.py` with reusable `tmp_path` fake project helpers; no hardcoded `C:\dev\proyects`.
- [x] T-7 Add `tests/unit/test_cli_workspace_status.py` covering R1 dirty, R2 no-git, R3 no-tests, R4 missing OpenSpec on SDD stack, and R5 informational-only.
- [x] T-8 Add JSON envelope tests: key order, `version == "1"`, 8 totals fields, verbatim projects list, deterministic byte-identical output across two invocations.
- [x] T-9 Add text output tests: header, `[DIRTY]`, `[NO-GIT]`, `[NO TESTS]`, clean project with no warnings, and bottom summary.
- [x] T-10 Add empty-root tests for text and JSON: exit 0, `(no projects to report)`, `totals.projects == 0`, `totals.needs_attention == 0`.
- [x] T-11 Add Phase 1 guard test proving `flow projects ls --json` behavior remains parseable and does not gain workspace-status fields.

## Phase 3: Verification

- [x] T-12 Run `uv run --frozen pytest tests/unit/test_cli_projects.py tests/unit/test_cli_workspace_status.py -q`.
- [x] T-13 Run full test suite: `uv run --frozen pytest tests/ -q`.
- [x] T-14 Run lint/type checks if available: `uv run --frozen ruff check .` and `uv run --frozen mypy src/`.
- [x] T-15 Smoke test real workspace: `uv run --frozen flow workspace status --root C:\dev\proyects --json` and verify JSON parses.

## Commit Plan

1. `feat(cli): add flow workspace status command`
   - T-1..T-5 production code.
2. `test(cli): cover flow workspace status rules`
   - T-6..T-11 tests and fixtures.
3. Optional docs/archive commit only if `sdd-archive` creates status metadata.

## Guardrails

- Do NOT modify `flow where`.
- Do NOT change Phase 1 `flow projects ls --json` schema.
- Do NOT add `generated_at` or any timestamp field to v1 JSON.
- Do NOT hardcode `C:\dev\proyects` in tests; use `tmp_path`.
- Keep `has_graphify` and `has_engram` informational-only in this command.
- If production diff exceeds ~220 LOC or `_detect_project_markers` changes materially, stop and re-design.

