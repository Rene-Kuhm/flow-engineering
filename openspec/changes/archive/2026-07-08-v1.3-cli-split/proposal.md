# Proposal: v1.3-cli-split (mechanical relocation)

## Intent

Split the 5,337-LOC `cli/__init__.py` monolith into 8 domain-submodule files via mechanical relocation — no new logic, no behavior changes. This is a **scope reduction** from the original v1.3-e forecast of ~5,800 LOC of net-new work; REQ-V1.3.6 (metrics namespace rewrite) and REQ-V1.3.7 (alias removal) are deferred to follow-up issues.

## Scope

### In Scope
- Mechanical relocation of `cli/__init__.py` into 8 submodules (see §Approach)
- Rename `cli/rotation.py` → `cli/archive.py`
- Re-export barrel in `cli/__init__.py` to preserve all 60+ test file import paths
- `workspace_health_cmd` anchor-migration into `cli/workspace.py` (Slice 2)
- 8 chained PRs via `feature-branch-chain` targeting `feature/v1.3-cli-split`

### Out of Scope
- REQ-V1.3.6: metrics namespace rewrite (already partially done; legacy flat dump preserved)
- REQ-V1.3.7: alias removal (`drift-events` deprecated group stays)
- Dead-code removal (`archive()` at lines 320–349 stays)
- New CLI commands or options
- New test files

## Capabilities

### New Capabilities
None — pure mechanical relocation.

### Modified Capabilities
None — no requirement-level behavior changes.

## Approach

**8-slice Feature Branch Chain** on tracker `feature/v1.3-cli-split` (from `origin/main` @ `8577d9c`):

| Slice | File | LOC (est.) | Summary |
|-------|------|-----------|---------|
| 1 | `cli/_shared.py` | ~250 | Constants, `_resolve_projects_root`, `_iter_project_subdirs`, `_read_pyproject_min_skill_versions`, `_enforce_min_skill_versions_or_exit`, shared Click option helpers |
| 2 | `cli/workspace.py` | ~700 | `workspace_group` + 6 sub-commands + `workspace_health_cmd` (anchor at line 3131) + hygiene helpers |
| 3 | `cli/project.py` | ~600 | `projects_group` + `projects_ls` + backfill + aliases + `_git`/`_detect_project_markers`/detection helpers |
| 4 | `cli/drift.py` | ~700 | `drift_group` + `drift_run` + `drift_events_group` + 3 events commands + alias shims + all drift helpers |
| 5 | `cli/snapshot.py` | ~350 | `snapshot_group` + 6 sub-commands + 3 snapshot helpers |
| 6 | `cli/prompts.py` | ~300 | `prompts_group` + `prompts_show`/`prompts_render` + `CheckAction` + prompts helpers |
| 7 | `cli/metrics.py` | ~500 | `metrics_group` + `summary`/`export`/`aggregate` children; **preserves legacy flat dump verbatim** (lines 1545–1547) |
| 8 | `cli/archive.py` | ~150 | Renamed from `rotation.py`; `archive_group` + `archive_change_cmd` + `rotate_cmd` |

After all slices: `cli/__init__.py` ≤500 LOC (Click group + lazy re-export barrel only).

**Branch chain**: Each PR targets `feature/v1.3-cli-split` (classical form, avoids cumulative diff explosion). Rollback per-slice via `git revert <slice-N-sha>`.

## Public API Preservation

8 confirmed public importable names from `flow_engineering.cli`:

| Name | Used by |
|------|---------|
| `main` | 61 test files + internal |
| `workspace_health_cmd` | 1 test file |
| `_detect_project_markers` | 8 tests + `health.py` |
| `_format_drift_events_text` | 2 tests |
| `_iter_project_subdirs` | 2 tests |
| `_summarize_workspace_status` | 2 tests |
| `_git` | `workspace_hygiene.py` |
| `rotate_cmd` | 1 test file |

Each slice adds `from .<submodule> import <name>` re-exports to `cli/__init__.py`. Private helpers also re-exported to avoid breaking `health.py` and `workspace_hygiene.py`.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Public API regression (60+ test imports break) | Medium | Grep verification + full pytest run per PR; CI gate |
| Click group double-registration | Low | Lazy imports in `cli/__init__.py` |
| LOC exceeds 400 cap (5/8 slices >400 LOC) | High | "Mechanical relocation only" justification paragraph per PR |
| Behavioral change accidentally introduced | Low | Mechanical discipline + byte-determinism invariant |

## Rollback Plan

Per-slice `git revert <sha>` — each slice is self-contained. If tracker branch is blocked, individual slices can be reverted independently without affecting other domains.

## Dependencies

- `origin/main` @ `8577d9c` (workspace-health-advisor PR4 merged)
- `feature/v1.3-cli-split` tracker branch (created before Slice 1)

## Success Criteria

- [ ] `cli/__init__.py` ≤500 LOC after all slices
- [ ] Each domain submodule ≤900 LOC
- [ ] All existing tests pass unchanged (1405+ tests)
- [ ] Public API of `flow_engineering.cli` preserved
- [ ] `flow workspace health` works after Slice 2
- [ ] Zero new tests needed
- [ ] Byte-determinism invariant preserved (no behavior changes)
