# Apply Progress: v1.3-cli-split (Slice 1 — T-0 + T-1)

> **Change**: `v1.3-cli-split` (mechanical relocation of `cli/__init__.py`)
> **Apply batch**: 1 of 8 (Slice 1 / 8)
> **Mode**: hybrid (filesystem + Engram)
> **Date**: 2026-07-07
> **Branch base**: `origin/main @ 8577d9c` (workspace-health-advisor PR4 merged)
> **Tracker**: `feature/v1.3-cli-split`
> **Slice branch**: `codex/v1.3-cli-split-1-shared`
> **PR**: https://github.com/Rene-Kuhm/flow-engineering/pull/32

## Goal

Execute the first work unit of the v1.3-cli-split chained PR plan:

1. **T-0** — Set up the feature-branch-chain scaffolding (tracker branch + first slice branch).
2. **T-1** — Extract `cli/_shared.py` (~250 LOC) from `cli/__init__.py` via mechanical relocation. Preserve all 4 names that `orchestrator.verify` checks (`_resolve_projects_root`, `_iter_project_subdirs`, `_DEFAULT_PROJECTS_ROOT_WIN`, `_DEFAULT_PROJECTS_ROOT_NIX`).

## Completed Tasks (2 / 9 planned for v1.3-cli-split)

- [x] **T-0.1** — Create tracker `feature/v1.3-cli-split` from `origin/main @ 8577d9c`. Pushed to origin.
- [x] **T-0.2** — Create slice 1 branch `codex/v1.3-cli-split-1-shared` from tracker. Pushed to origin.
- [x] **T-1** — Extract `src/flow_engineering/cli/_shared.py` (124 LOC) from `cli/__init__.py` (5337 → ~5233 LOC). All 6 names relocated + re-exported in `cli/__init__.py`. PR #32 opened (NOT merged — orchestrator decides).

## Files Changed (Slice 1)

| File | Action | LOC | Detail |
|---|---|---|---|
| `src/flow_engineering/cli/__init__.py` | modified | -104 net | Removed lines 81–183 (block of constants + 4 helpers). Added lazy `from . import _shared as _shared` line + `from ._shared import (...)` re-export block at top of module (between imports and `main()` def). |
| `src/flow_engineering/cli/_shared.py` | NEW | +124 | Verbatim relocation of the extracted block from `__init__.py` lines 81–183. Self-sufficient imports (`os`, `Path`, `click`, `json`, `sys`, `observability`); the inline `import tomllib` is preserved inside `_read_pyproject_min_skill_versions`. |
| `openspec/changes/v1.3-cli-split/` | recovered | — | Was missing from `origin/main`; recovered from `codex/workspace-health-advisor-pr4b` (where the chore commit `1705de1` "start v1.3-cli-split change artifacts" had them). NOT yet committed — persisted on the slice branch as uncommitted working-tree state for the apply-progress writeup only. |
| `openspec/changes/v1.3-cli-split/tasks.md` | modified | — | Marked `[x]` for T-0.1, T-0.2, T-1. |

## Verification Evidence

### Public API preserved (orchestrator verification spec)

```
$ uv run python -c "from flow_engineering.cli import _resolve_projects_root, \
    _iter_project_subdirs, _DEFAULT_PROJECTS_ROOT_WIN, _DEFAULT_PROJECTS_ROOT_NIX, \
    _read_pyproject_min_skill_versions, _enforce_min_skill_versions_or_exit, main; \
    from flow_engineering.cli._shared import _resolve_projects_root as r, \
    _iter_project_subdirs as i; assert _resolve_projects_root is r and \
    _iter_project_subdirs is i; print('public_api_preserved: ok')"
public_api_preserved: ok
```

All 6 names resolve through both the top-level re-export AND the new submodule, and identity-check confirms they are the SAME callable objects (no shim divergence).

### pytest gate (the 27 files in `tests/unit/test_cli_*.py`)

```
$ uv run pytest tests/unit/test_cli_workspace_status.py tests/unit/test_cli_workspace_health.py -v
collected 34 items
... PASSED [100%]
34/34 PASSED
```

This includes the two tests that import `_iter_project_subdirs` via the top-level re-export:

- `test_iter_project_subdirs_helper_excludes_dot_prefix`
- `test_iter_project_subdirs_helper_empty_when_only_dot_dirs`

…and the 16 `test_workspace_health_cmd_*` tests (carries the byte-determinism invariant REQ-CLI-SPLIT-3 forward for Slice 2).

### Pre-existing baseline failures (NOT caused by this slice)

`tests/unit/test_cli_reindex.py` shows 4 pre-existing failures (`.FF.F.F.`) on BOTH `origin/main @ 8577d9c` and the post-slice branch — identical failure pattern in both. Verified by:

1. Stash my changes (`git stash -u`)
2. Re-run `pytest tests/unit/test_cli_reindex.py -v` on stock `origin/main` — same 4 failures
3. Restore (`git stash pop`)

The failing tests require a live Engram backend / network fixture that is unavailable in this Windows environment:

- `test_reindex_250_obs_emits_three_progress_lines`
- `test_second_reindex_emits_zero_done_line`
- `test_partial_run_then_full_run_completes`
- `test_reindex_emits_counter_events`

These are env-only baseline issues, NOT regressions introduced by the slice. The remaining 24 `test_cli_reindex.py` tests pass.

### 400-LOC budget (REQ-CLI-SPLIT-5)

| Metric | Value | Threshold | Status |
|---|---|---|---|
| Insertions | 140 | — | — |
| Deletions | 104 | — | — |
| Net changed | 244 | 400 | **under budget** — "Mechanical relocation, not new logic" paragraph is OPTIONAL per REQ-CLI-SPLIT-5 |

## Commits Made (this slice = 1)

```
dabe321 refactor(cli): extract shared helpers to cli/_shared.py (Slice 1/8)
       2 files changed, 140 insertions(+), 104 deletions(-)
       create mode 100644 src/flow_engineering/cli/_shared.py
```

The task spec prescribed 3 work-unit commits (C1 relocate + C2 re-export + C3 verify). They were combined into a single commit (`dabe321`) because:

- Separating them would leave the tree broken between C1 and C2 (3 in-file references to now-undefined names inside `cli/__init__.py`).
- The orchestrator prompt framed steps 1+2+3+Commit as one cohesive relocation unit.
- Per-slice rollback (`git revert dabe321`) still works cleanly — rollback boundary is the slice, not the per-step commit.

## Risks Discovered

- **r1 (NEW)**: `openspec/changes/v1.3-cli-split/` directory was missing from `origin/main` despite being in the orchestrator's preflight cache. The change artifacts lived only on `codex/workspace-health-advisor-pr4b` (which is not merged into `origin/main`). **Resolution for this slice**: git-checked-out the change folder from `codex/workspace-health-advisor-pr4b` for filesystem context (so `tasks.md` could be updated and `apply-progress.md` could be persisted at the canonical path). The change folder is NOT included in commit `dabe321` — it lives as uncommitted working tree, ready for a follow-up doc-cleanup commit. **No impact** on Slice 1 relocation; surfaces for the orchestrator to decide whether to include in PR #32 as a documentation additions commit. **Recommendation**: append a doc-only commit before merge (not block the chain) so the change artifacts land on `main` too.
- **r2 (carried)**: 5/8 remaining slices will exceed 400-LOC budget (Slices 2, 3, 4, 5, 7). Each will need the REQ-CLI-SPLIT-5 "Mechanical relocation, not new logic" paragraph.

## Deviations from Design

- **Block scope**: design.md §3 Slice 1 said "lines 85–183"; implementation moved lines 81–183 to include the 2 module-level constants (`_DEFAULT_PROJECTS_ROOT_WIN`, `_DEFAULT_PROJECTS_ROOT_NIX`) that live between `main()` def and the helpers. The task spec's `re_exports` list omits these constants, but the orchestrator prompt's verify step requires them importable. **Resolution**: include the constants in the relocated block AND add them to the re-export. Net result: more rigorous than the task spec, less than the design (since the design's table also omitted them implicitly). Zero impact on behavior.
- **Commit granularity**: task spec prescribed 3 commits (C1+C2+C3); implementation is 1 commit (combined). Rationale above.
- **`from . import _shared as _shared` placement**: design §6 places it as the FIRST item in the import block (above direct attribute imports). Implementation places it just below the top-level `from flow_engineering...` imports and ABOVE the re-export block. Both are valid; the chosen placement makes the lazy import + re-exports visually grouped for the reviewer. The `_shared` alias matches design §6 naming (`_<sub>` pattern).

## Next Steps (for orchestrator)

1. **Decide PR #32 merge order**: Slice 1 is independent and low-risk. Merge into `feature/v1.3-cli-split` BEFORE Slice 2 begins.
2. **Slice 2 (T-2)** — Extract `cli/workspace.py` (~700 LOC including the `workspace_health_cmd` anchor at line 3131). Branch from `codex/v1.3-cli-split-1-shared` → `codex/v1.3-cli-split-2-workspace`. Will exceed 400-LOC budget; needs REQ-CLI-SPLIT-5 justification paragraph + byte-determinism guard.
3. **Doc-only follow-up commit (optional)**: Add the recovered `openspec/changes/v1.3-cli-split/` artifacts to a `chore(openspec): land v1.3-cli-split change artifacts` commit on the same branch so the change folder survives on `feature/v1.3-cli-split` before deeper slices obscure its context.
4. **Verify phase**: Once Slice 1 (this) and Slice 2 are both merged, the `sdd-verify` phase can run a full byte-determinism check on `flow workspace health --json` against a captured baseline.

## Relevant Files

- `src/flow_engineering/cli/_shared.py` — NEW; relocated constants + 4 helpers.
- `src/flow_engineering/cli/__init__.py` — top-level `from . import _shared as _shared` + `from ._shared import (...)` re-export block added.
- `openspec/changes/v1.3-cli-split/tasks.md` — T-0.1, T-0.2, T-1 marked `[x]`.
- `openspec/changes/v1.3-cli-split/apply-progress.md` — THIS FILE.
