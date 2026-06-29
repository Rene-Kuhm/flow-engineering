# Proposal: flow-workspace-status — Phase 3 of workspace-intelligence

> Add `flow workspace status` as a read-only aggregation subcommand on top of Phase 1's v1 JSON envelope.

## Intent

After `flow projects ls --json` (Phase 1), the next natural question is "which projects need attention — dirty, no-git, no-tests, missing openspec on SDD-adjacent stacks?" `flow workspace status` answers that by consuming Phase 1's `_detect_project_markers` output directly (no subprocess), rendering a needs-attention synthesis with text default + `--json` envelope. Phase 3 keeps its own envelope byte-deterministic: no timestamp fields in v1. Phase 1's byte-identical contract stays intact.

## Scope

### In
- New top-level `flow workspace status` subcommand in `cli.py`
- New `_summarize_workspace_status(envelope) -> dict` pure helper
- Shared `_resolve_projects_root()` helper shared with `projects_ls`
- Phase 3 own JSON envelope with `totals` + `needs_attention` blocks
- 5 needs-attention rules (R1–R4 count; R5 informational-only)
- NEW test file: `tests/unit/test_cli_workspace_status.py` (10 tests)
- NEW shared fixtures: `tests/unit/_workspace_fixtures.py` (9 `make_fake_*` helpers moved from `test_cli_projects.py`)

### Out
- `flow projects ls` — byte-identical contract preserved
- `flow where` (Phase 2)
- Phase 4 (hygiene), Phase 5 (dashboard)
- Real Engram/Graphify integration (stubs only)
- Other modules under `src/flow_engineering/`

## Capabilities

### New Capabilities
- `workspace-status-text`: human-readable ASCII status report with DIRTY / NO GIT / NO TESTS / OPENSPEC coverage / NEEDS ATTENTION blocks
- `workspace-status-json`: machine-readable `version:"1"` envelope with `totals` + `projects` (verbatim from Phase 1) + `needs_attention` list

## Approach

```
flow workspace status [--root PATH] [--json]
```

**Data flow**: `_detect_project_markers(root)` called directly (same function Phase 1 uses, same import path, no subprocess). Results aggregated into `totals` dict + `needs_attention` list. Both text and JSON share the same data — no duplicate detection. Projects sorted by name for deterministic output.

**Subcommand registration**: `@main.group(name="workspace")` at top level (mirrors `metrics` group pattern). `status` subcommand registered under it. NOT under `flow projects`.

**JSON envelope** (Phase 3 owns this — separate from Phase 1's v1 envelope):

```json
{
  "version": "1",
  "root": "<path>",
  "totals": {
    "projects": N, "dirty": N, "no_git": N, "no_tests": N,
    "has_openspec": N, "has_graphify": N, "has_engram": N, "needs_attention": N
  },
  "projects": [...],
  "needs_attention": [
    {"name": "...", "reasons": ["R1: uncommitted work", "R2: no version control"], "path": "..."}
  ]
}
```

Key ordering (CPython 3.7+ deterministic): `version`, `root`, `totals`, `projects`, `needs_attention`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/flow_engineering/cli.py` | Modified | `@main.group("workspace")` + `status` subcommand + `_summarize_workspace_status` helper |
| `tests/unit/test_cli_workspace_status.py` | New | 10 unit tests for text default, JSON envelope, R1–R4, R5 informational, byte-determinism |
| `tests/unit/_workspace_fixtures.py` | New | 9 `make_fake_*` helpers (moved from `test_cli_projects.py`) |

## Needs-Attention Rules

| Rule | Condition | Output message | Counts as attention |
|------|-----------|----------------|---------------------|
| R1 | `has_git==true AND dirty==true` | "uncommitted work" | **YES** |
| R2 | `has_git==false` | "no version control" | **YES** |
| R3 | `test_commands==[]` | "no tests detected" | **YES** |
| R4 | `has_openspec==false AND stack in {Python, Go, Rust}` | "SDD-adjacent stack missing openspec" | **YES** |
| R5 | `has_graphify==false` | "graphify not initialized (informational only in v1)" | **NO** — informational only; Phase 1 stub returns always false |

Multiple reasons per project collapse into one `needs_attention` entry. `has_engram` is informational only (always stub-false in Phase 1).

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Phase 2/4/5 schema coupling** | Medium | Lock `version:"1"`; additive-only future fields; CHANGELOG |
| **Stale data between detection and aggregation** | Low | Direct `_detect_project_markers` import — no subprocess, no staleness window |
| **R4 false positives** (Go library legitimately lacking openspec) | Medium | Renders `reasons[]` in JSON so operators can override or ignore |
| **R5 stub masking** when Phase 2 un-stubs graphify | Low | Document `disabled_in_v1` in spec; re-evaluate at Phase 2 |
| **Empty root (degenerate)** | Low | Test: renders "(no projects to report)"; exit 0 |

## Rollback Plan

Revert the single commit `codex/flow-workspace-status`. No schema migration needed — Phase 3 envelope is fully additive (no mutation of Phase 1 output).

## Dependencies

- Phase 1 `_detect_project_markers()` at `cli.py:2586` — shared, no copy
- `tests/unit/_workspace_fixtures.py` shared module — must exist before test file

## Success Criteria

- [ ] `flow workspace status` renders human-readable ASCII report with DIRTY / NO GIT / NO TESTS blocks
- [ ] `flow workspace status --json` emits valid `version:"1"` envelope with `totals` + `needs_attention`
- [ ] Two consecutive `--json` invocations on unchanged root emit byte-identical output
- [ ] Phase 1 `flow projects ls --json` is byte-identical before and after this change
- [ ] All 10 new tests pass in `tests/unit/test_cli_workspace_status.py`
- [ ] 9 `make_fake_*` helpers moved to `tests/unit/_workspace_fixtures.py`; no duplication

## PR Strategy

- **1 PR**, **1 commit**, branch `codex/flow-workspace-status` from `main`
- Commit message: `feat(cli): add flow workspace status subcommand with needs-attention rules`
- Review budget: ~100 LOC production + ~150 LOC tests = ~250 LOC total (under 400-line budget)

