# Exploration: v1.3-cli-split (sub-change e, mechanical relocation)

> **Phase**: sdd-explore (1/7 of SDD cycle)
> **Change**: `v1.3-cli-split` (resumed from merged umbrella `v1.3-platform-hardening`)
> **Artifact store mode**: `hybrid` (Engram `sdd/v1.3-cli-split/explore` + this file)
> **Date**: 2026-07-07
> **Branch baseline**: `origin/main` @ `8577d9c` (sub-changes a/b/c/d merged)

---

## 1. Current state (verified)

### File map on `origin/main`

| File | LOC | Status |
|------|-----|--------|
| `src/flow_engineering/cli/__init__.py` | 4695 | v1.3-d relocated `cli.py` verbatim; only ~25 LOC net-new (the `archive_group` + `rotate_cmd` registration) |
| `src/flow_engineering/cli/rotation.py` | 140 | NEW from v1.3-d; exports `rotate_cmd` |
| `src/flow_engineering/cli.py` | n/a | DELETED in v1.3-d (commit `2120df5`) |
| **Total in `cli/` package** | **~4835** | — |

### File map on working branch (`codex/workspace-health-advisor-pr4b`)

`cli/__init__.py` grew from 4695 → **5337 LOC** due to PR4a (`workspace_health_cmd` skeleton + `--json`/`--root` envelope assembly, +333 LOC) and PR4b (text render + `--filter` + `--no-color`, +316 LOC). Both PRs already merged into `feature/workspace-health-advisor-pr4` and will land on `main` via the tracker. **The relocation forecast must include this growth.**

### v1.3-e migration anchor (verified)

`cli/__init__.py:3131` contains:

```
# v1.3-e migration: this block moves to cli/workspace.py per design §v1.3-e.
```

This block (lines 3130–3257, ~127 LOC) is `workspace_health_cmd` + `_normalize_filter_rules` + `_HEALTH_FILTER_CHOICES` — pre-staged for Slice 2 of the orchestrator's chain.

### Click command map on current branch

20 `@main.command`/`@main.group` decorators (verified via Select-String):

| Line | Decorator | Function | Domain |
|------|-----------|----------|--------|
| 185 | `@main.command()` | `new` | top-level — NOT assigned in orchestrator's plan |
| 213 | `@main.command(name="new-project")` | `new_project` | top-level — NOT assigned |
| 229 | `@main.command()` | `status` | top-level — NOT assigned |
| 267 | `@main.command()` | `doctor` | top-level — NOT assigned |
| 277 | `@main.command()` | `apply` | top-level — NOT assigned |
| 302 | `@main.command()` | `verify` | top-level — NOT assigned |
| 351 | `@main.command()` | `watch` | top-level — NOT assigned |
| 393 | `@main.command(name="memory-timeline")` | `memory_timeline` | top-level — NOT assigned |
| 702 | `@main.command(name="where")` | `where_cmd` | top-level — NOT assigned |
| 935 | `@main.command()` | `save` | engram — NOT assigned |
| 1102 | `@main.command()` | `search` | engram — NOT assigned |
| 1300 | `@main.command()` | `reindex` | engram — NOT assigned |
| 1489 | `@main.command()` | `inspect` | engram — NOT assigned |
| 1534 | `@main.group(invoke_without_command=True)` | `metrics` | **ALREADY a group** (legacy flat path via `invoke_without_command`) |
| 1575 | `@metrics.command("summary")` | `metrics_summary` | engram-adjacent |
| 1752 | `@metrics.command("export")` | `metrics_export` | engram-adjacent |
| 1932 | `@metrics.command("aggregate")` | `metrics_aggregate` | engram-adjacent |
| 2269 | `@main.group("drift", invoke_without_command=True)` | `drift_group` | drift |
| 2754 | `@main.group(name="drift-events", deprecated=True)` | `drift_events_alias_group` | drift (REMOVE per REQ-V1.3.7) |
| 3013 | `@main.group(name="workspace")` | `workspace_group` | workspace |
| 3575 | `@main.group(name="projects")` | `projects_group` | project |
| 4142 | `@main.group(name="snapshot")` | `snapshot_group` | snapshot |
| 4617 | `@main.group(name="prompts")` | `prompts_group` | prompts |
| 5284 | `@main.group(name="archive")` | `archive_group` | archive (rotate + change) |

### Public API surface that MUST be preserved

Tests + downstream code import these names from `flow_engineering.cli` (verified via grep):

| Imported name | Importers | Notes |
|---------------|-----------|-------|
| `main` | 61 test files + `cli/__init__.py:5298` | Click group instance; MUST stay importable |
| `_detect_project_markers` | 8× in `tests/unit/test_cli_projects.py` + `src/flow_engineering/health.py:538` | Private helper used as a library by `health.py` |
| `_format_drift_events_text` | 2× in `tests/unit/test_cli_drift_events_list.py` | Private helper tested directly |
| `_iter_project_subdirs` | 2× in `tests/unit/test_cli_workspace_status.py` | Private helper |
| `_summarize_workspace_status` | 2× in `tests/unit/test_cli_workspace_status.py` | Private helper |
| `workspace_health_cmd` | 1× in `tests/unit/test_cli_workspace_health.py` | New from PR4a; tested directly |
| `_git` | `src/flow_engineering/workspace_hygiene.py:363` | Private helper; library surface |
| `rotate_cmd` (from `cli.rotation`) | 1× in `tests/unit/test_cli_rotation.py` + `cli/__init__.py:5298` | Already submodule-public |

**Strategy**: `cli/__init__.py` MUST re-export all of these names after each slice via `from flow_engineering.cli.<domain> import <name>`. The `__init__.py` becomes a Click-group stub PLUS a re-export barrel.

### Behavior changes already partially done vs. design-e

| REQ | Design-e slice | Current state (post-PR4) | Implication for v1.3-e |
|-----|----------------|--------------------------|--------------------------|
| REQ-V1.3.6 (metrics → real group) | Slice 5 | **DONE in a prior sub-change** (`metrics` is `@main.group()` at line 1534 with `summary`/`export`/`aggregate` children at lines 1575/1752/1932). Legacy flat path preserved via `invoke_without_command=True` + `if ctx.invoked_subcommand is not None: return` (lines 1545-1547). | **Slice 5 of design-e collapses to a mechanical relocation of `metrics_group` + 3 children** — no namespace rewrite. The legacy flat dump is preserved, so `flow metrics` (no subcommand) still works. **However**, the design-e "BREAKING" claim (`flow metrics_summary` → `NoSuchCommand`) is NOT true today: the legacy top-level form `metrics` (with `invoke_without_command`) still accepts subcommands OR runs the flat dump. If we keep that, no breaking change occurs. The orchestrator's "mechanical relocation only" framing is consistent with this — do NOT remove the legacy flat dump as part of relocation. |
| REQ-V1.3.7 (drift.events-alias removal) | Slice 6 | `drift_events_alias_group` STILL PRESENT at lines 2754-2797 (registered as `@main.group(name="drift-events", deprecated=True)`). 3 ctx.forward shims at lines 2798-2892. | **Out of scope for "mechanical relocation"** — keeping the alias preserves pre-split behavior. Document the alias removal as a separate follow-up (it was already announced in CHANGELOG v1.2.0 line 22 per design-e §ADR-e.3). |
| `cli.py` shim/delete | Slice 12 | Already done in v1.3-d (commit `2120df5`). | N/A |

---

## 2. Domain boundaries — confirmed with gap

### Proposed slice map (orchestrator's plan, 5–6 slices)

| Slice | New file | LOC forecast (moved) | Source lines (verified) | Verified |
|-------|----------|---------------------|--------------------------|----------|
| 1 | `cli/_shared.py` | 200–400 LOC | lines 1–183 (imports + constants + `_resolve_projects_root` + `_iter_project_subdirs` + `_read_pyproject_min_skill_versions` + `_enforce_min_skill_versions_or_exit`) + select cross-domain helpers | ✅ |
| 2 | `cli/workspace.py` | 600–900 LOC | lines 2894–3013 (`_summarize_workspace_status` + helpers + `workspace_group`) + 3013–3559 (`workspace_status` + `workspace_dashboard_cmd` + `workspace_health_cmd` block + `workspace_fix_cmd` + `workspace_archive_cmd` + `workspace_archived_cmd` + `workspace_restore_cmd` + hygiene helpers `_load_registry_for_cli`/`_resolve_backup_root_for_cli`/`_resolve_project_path`/`_workspace_hygiene_exit`/`_require_yes`/`_format_archived_text_table`) | ✅ |
| 3 | `cli/project.py` | 400–600 LOC | lines 3576–4102 (`projects_group` + `projects_ls` + `projects_backfill` + `projects_alias` + helpers `_git`/`_detect_stack`/`_detect_test_commands`/`_has_pytest_config`/`_detect_project_markers`) | ✅ |
| 4 | `cli/drift.py` | 600–900 LOC | lines 2076–2253 (`_resolve_snapshots_dir`/`_parse_since` are also needed here? — NO, see caveat below) + lines 2117–2893 (`drift_group` + `drift_run` + `drift_events_group` + 3 events commands + `drift_events_alias_group` + 3 alias shims + all drift helpers). **Excludes** the orphaned `archive()` function at lines 320-349 which is already declared dead per the inline comment. | ✅ (with caveat: see §3) |
| 5 | `cli/snapshot.py` | 200–300 LOC | lines 4103–4493 (`_build_snapshot_manager`/`_serialize_snapshot_meta`/`_snapshot_diff_to_dict` + `snapshot_group` + 6 sub-commands) | ✅ |
| 5 | `cli/prompts.py` | 500–600 LOC | lines 4494–5283 (`_emit_check_observability`/`_resolve_check_action`/`CheckAction`/`_LINT_*_CODES` + `prompts_group` + `prompts_check`/`prompts_lint`/`prompts_list`/`prompts_show` + all `_entry_*`/`_format_*`/`_render_*`/`_serialize_*`/`_parse_var_pair` helpers) | ✅ |
| 6 | `cli/archive.py` (rename of `cli/rotation.py`) | 150 LOC + ~200 LOC from `cli/__init__.py` lines 5284–5335 (`archive_group` + `archive_change_cmd` + late import) | ✅ |
| **Sum moved** | — | **~2,700–3,950 LOC** | — | — |

### Gap analysis: orchestrator's plan vs. `__init__.py` ≤500 LOC target

`cli/__init__.py` currently = **5337 LOC** on the working branch (4695 on `main`).
Moving 2,700–3,950 LOC leaves **1,387–2,637 LOC** in `__init__.py`.

That **fails** the success criterion `__init__.py` ≤500 LOC. What's missing from the orchestrator's plan:

| Domain | Lines | Functions | Currently planned |
|--------|-------|-----------|-------------------|
| Top-level scaffold (`new`/`new_project`/`status`/`doctor`/`apply`/`verify`) | 185–349 (~165 LOC) | 6 commands | **NOT in plan** |
| Watch (`watch`/`memory_timeline`) | 351–432 (~82 LOC) | 2 commands | **NOT in plan** |
| Where (`where_cmd` + cross-project helpers) | 433–933 (~500 LOC) | 1 command + 10 helpers | **NOT in plan** |
| Engram (`save`/`search`/`reindex`/`inspect`) | 935–1511 (~576 LOC) | 4 commands + 8 helpers | **NOT in plan** |
| Metrics (`metrics_group` + 3 children + helpers) | 1517–2074 (~557 LOC) | 1 group + 3 children + helpers | **NOT in plan** |

**Total unmapped**: ~1,880 LOC of top-level commands + helpers. Without slicing these out, `__init__.py` stays at ~3,000 LOC minimum.

### Options

| Option | Slices | `__init__.py` LOC | Pros | Cons |
|--------|--------|-------------------|------|------|
| **A. Orchestrator's plan as-stated** (5–6 slices, only domain submodules) | 5–6 | ~2,000–2,500 LOC | Short chain, low review count | **Fails ≤500 LOC success criterion**. Unmapped top-level commands accumulate as tech debt. |
| **B. Expanded 8–9 slice chain** (add `engram.py`, `where.py`, `watch.py`, `core.py` for top-level scaffold) | 8–9 | ~400 LOC | Hits ≤500 LOC target. Clear domain boundaries. Each slice stays ≤600 LOC (per `metrics.py`'s 557 LOC). | Longer chain (3 extra PRs vs design-e's 12). |
| **C. Roll top-level into `_shared.py`** | 5–6 | ~500 LOC | No extra slices | `cli/_shared.py` becomes a junk drawer (mixes constants, helpers, AND top-level commands). Anti-pattern; reviewers will flag. |

**Recommended**: **Option B** — expand the chain to 8–9 slices. Design-e's 12-slice plan is over-engineered for "mechanical relocation only" (it bundles behavior changes like the alias removal), but 5–6 slices is too few to hit the ≤500 LOC target.

---

## 3. Caveats and forward-compat notes

### Caveat 1: `_resolve_snapshots_dir` and `_parse_since` (lines 2076–2115)

These helpers are at lines 2076 and 2090, BEFORE the drift block starts at 2117. They are used by `drift_run` (line 2303). If we move drift as a unit, they MUST come along. Forecast already includes them. ✅

### Caveat 2: `_emit_check_observability` + `_resolve_check_action` + `CheckAction` dataclass (lines 4494–4594)

These are domain-shared helpers between `prompts_check` and `metrics_aggregate` (the dataclass field `catalog` is shared with metrics aggregation). If we move prompts cleanly, **verify that `metrics_aggregate` doesn't import from this block**. Currently it does NOT (verified via grep: `CheckAction` only used by `prompts_check`). Safe to move into `cli/prompts.py`.

### Caveat 3: `metrics` group is already a real group (lines 1534–1547)

The design-e Slice 5 (REQ-V1.3.6 namespace fix) is **a no-op for behavior change**. We just relocate the group + 3 children to `cli/metrics.py`. Keep the `invoke_without_command=True` legacy flat dump intact (preserves backward compat).

### Caveat 4: `drift_events_alias_group` is still registered

Per "mechanical relocation only" framing, keep `drift_events_alias_group` + its 3 `ctx.forward()` shims in the relocated `cli/drift.py`. **Do NOT** remove the alias as part of v1.3-e — that's a separate behavior change. Document as follow-up.

### Caveat 5: Anchor comment at line 3131 is workspace_health_cmd's

Slice 2 (`cli/workspace.py`) should move the entire block from line 2894 through line 3559 inclusive. The anchor comment is at line 3131 (inside the block). Removing the anchor comment after the move is fine — the new module path documents the relocation.

### Caveat 6: `archive_group` + `archive_change_cmd` (lines 5284–5335)

These live in `cli/__init__.py` at the end. Per Slice 6 (rename `rotation.py` → `archive.py`), they should move to `cli/archive.py` too. The late import `from flow_engineering.cli.rotation import rotate_cmd` (line 5298) becomes a normal top-of-file import in `cli/archive.py`.

### Caveat 7: The orphaned `archive()` function at lines 320–349

The inline comment says it was "previously declared with `@main.command()`. Now registered as a subcommand of the new `archive` group below." The actual registration is `archive_change_cmd` at line 5316 — a different function. The `archive()` body at line 334 is **dead code** but currently NOT removed (the design-e doesn't ask for its removal). **Keep it as-is** during mechanical relocation; flag for follow-up.

### Caveat 8: `archive` subcommand under `archive_group` collision

Per apply-progress d (obs #2000 §D1): the `archive_change_cmd` exists alongside the OLD `archive()` function body. This is a v1.3 BREAKING surface (the old `flow archive <change>` becomes `flow archive change <change>`). Already documented in CHANGELOG v1.3.0-alpha. Mechanical relocation preserves this.

---

## 4. Affected areas

| File | Action | Why |
|------|--------|-----|
| `src/flow_engineering/cli/__init__.py` | TRIM to ~400 LOC | Becomes Click group + re-export barrel |
| `src/flow_engineering/cli/_shared.py` | NEW | Module-level constants, `_resolve_projects_root`, `_iter_project_subdirs`, `_read_pyproject_min_skill_versions`, `_enforce_min_skill_versions_or_exit`, shared Click option helpers |
| `src/flow_engineering/cli/workspace.py` | NEW | `workspace_group` + 6 sub-commands + workspace_health_cmd block + hygiene helpers |
| `src/flow_engineering/cli/project.py` | NEW | `projects_group` + 3 sub-commands + 5 detection helpers |
| `src/flow_engineering/cli/drift.py` | NEW | `drift_group` + `drift_run` + `drift_events_group` + 3 events commands + `drift_events_alias_group` + 3 alias shims + drift helpers |
| `src/flow_engineering/cli/snapshot.py` | NEW | `snapshot_group` + 6 sub-commands + 3 snapshot helpers |
| `src/flow_engineering/cli/prompts.py` | NEW | `prompts_group` + 4 sub-commands + `CheckAction` + prompts helpers |
| `src/flow_engineering/cli/metrics.py` | NEW (proposed — see §2 Option B) | `metrics_group` + 3 children + metrics helpers |
| `src/flow_engineering/cli/engram.py` | NEW (proposed — see §2 Option B) | `save`/`search`/`reindex`/`inspect` + engram helpers |
| `src/flow_engineering/cli/where.py` | NEW (proposed — see §2 Option B) | `where_cmd` + cross-project helpers + 2 constants |
| `src/flow_engineering/cli/watch.py` | NEW (proposed — see §2 Option B) | `watch`/`memory_timeline` |
| `src/flow_engineering/cli/core.py` or `cli/scaffold.py` | NEW (proposed — see §2 Option B) | `new`/`new_project`/`status`/`doctor`/`apply`/`verify` |
| `src/flow_engineering/cli/archive.py` | RENAME of `rotation.py` | `archive_group` + `archive_change_cmd` + `rotate_cmd` |
| `src/flow_engineering/cli/rotation.py` | DELETE (after rename) | Becomes `cli/archive.py` |
| `tests/unit/test_cli_*.py` (60 files) | UNCHANGED | Import paths preserved via `cli/__init__.py` re-exports |
| `src/flow_engineering/health.py` | UNCHANGED | Imports `_detect_project_markers` from `flow_engineering.cli` (re-export preserved) |
| `src/flow_engineering/workspace_hygiene.py` | UNCHANGED | Imports `_git` from `flow_engineering.cli` (re-export preserved) |

---

## 5. Approaches

### Approach 1: 5–6 slice chain (orchestrator's plan)

- **Slice 1**: `cli/_shared.py` (~250 LOC)
- **Slice 2**: `cli/workspace.py` (~750 LOC — includes `workspace_health_cmd` ready-to-move block)
- **Slice 3**: `cli/project.py` (~450 LOC)
- **Slice 4**: `cli/drift.py` (~750 LOC — keeps `drift_events_alias_group` intact)
- **Slice 5**: `cli/snapshot.py` (~250 LOC) + `cli/prompts.py` (~550 LOC) — combined into ONE PR
- **Slice 6**: `cli/rotation.py` → `cli/archive.py` rename + relocate `archive_group` + `archive_change_cmd` (~200 LOC)
- **Pros**: Short chain (6 PRs). Each slice is mechanical relocation only. Aligns with orchestrator's framing.
- **Cons**: **Fails `__init__.py` ≤500 LOC criterion** (~2,000 LOC residual). Top-level commands (`new`/`apply`/`where`/`save`/`metrics`/`watch`) stay in `__init__.py` as a 2,000-LOC block — same problem we started with, just smaller.

### Approach 2: 8–9 slice chain (recommended — Option B)

- **Slice 1**: `cli/_shared.py` (~250 LOC)
- **Slice 2**: `cli/workspace.py` (~750 LOC)
- **Slice 3**: `cli/project.py` (~450 LOC)
- **Slice 4**: `cli/drift.py` (~750 LOC)
- **Slice 5**: `cli/metrics.py` (~550 LOC — group + 3 children, no behavior change)
- **Slice 6**: `cli/snapshot.py` (~250 LOC) + `cli/prompts.py` (~550 LOC) — combined
- **Slice 7**: `cli/engram.py` (~550 LOC) + `cli/where.py` (~500 LOC) + `cli/watch.py` (~80 LOC) — three small files combined
- **Slice 8**: `cli/core.py` (~250 LOC — `new`/`new_project`/`status`/`doctor`/`apply`/`verify`) + `cli/archive.py` rename (~200 LOC)
- **Pros**: Hits `__init__.py` ≤500 LOC target. Each slice ≤750 LOC (within 400-LOC review budget if split further, but per orchestrator's "mechanical relocation" framing, larger slices are justified). Clear domain boundaries.
- **Cons**: 8 PRs (vs design-e's 12, vs orchestrator's 5–6).

### Approach 3: 12-slice chain (original design-e)

- Per obs #1996: 12 chained PRs targeting `feature/v1.3-cli-split-tracker`.
- **Pros**: Original plan. Each slice ≤600 LOC. Hits ≤500 LOC target.
- **Cons**: 12 PRs = 12 reviewer rounds. Long chain (18–24 months per design-e risk r1). Includes behavior changes (REQ-V1.3.6 namespace rewrite + REQ-V1.3.7 alias removal) that the orchestrator explicitly excluded from v1.3-e scope. **Over-budget** for "mechanical relocation only."

### Approach 4: Single mega-PR (~3,500 LOC moved in one PR)

- **Pros**: One PR. Done.
- **Cons**: Violates 400-LOC review budget by 8.75x. Reviewer will reject. Not eligible.

---

## 6. Recommendation

**Approach 2 (8–9 slice chain)** with the following refinements:

1. **Track on `feature/v1.3-cli-split` (NEW tracker branch)** — separate from `feature/workspace-health-advisor-pr4`. The v1.3-cli-split change is independent of the workspace-health-advisor PR4 chain.

2. **Slice order (dependency-stable)**:
   - **Slice 1**: `cli/_shared.py` (foundation; nothing else can move without it)
   - **Slice 2**: `cli/workspace.py` (largest domain; includes the `workspace_health_cmd` anchor-comment block)
   - **Slice 3**: `cli/project.py` (self-contained; depends only on `_shared.py`)
   - **Slice 4**: `cli/drift.py` (depends on `_shared.py`)
   - **Slice 5**: `cli/metrics.py` (depends on `_shared.py`; preserves legacy flat dump)
   - **Slice 6**: `cli/snapshot.py` + `cli/prompts.py` (combined — both small, both depend only on `_shared.py`)
   - **Slice 7**: `cli/engram.py` + `cli/where.py` + `cli/watch.py` (combined — three small files)
   - **Slice 8**: `cli/core.py` (top-level scaffold) + `cli/archive.py` rename (combined — final clean-up)
   - **Optional Slice 9**: `cli/__init__.py` final trim + delete legacy re-exports + lock byte-identical `flow --help` test (mirrors design-e §5 step 12.1)

3. **Per-PR LOC budget**: each slice is mechanical relocation, so the 400-LOC review budget CAN be exceeded with a justification paragraph in the PR description (per design-e gate-review nit on slice 2). Document each PR's reasoning: "this slice relocates X LOC from the monolith verbatim; review burden is semantic-equivalence (no logic changes), not from-scratch logic."

4. **Excluded from v1.3-e scope** (deferred to follow-up issues):
   - REQ-V1.3.7 (alias removal) — behavior change, keep alias intact
   - REQ-V1.3.6 metrics namespace BREAKING (legacy flat dump) — already partially done; preserve what exists
   - Dead code removal (`archive()` function at lines 320–349)
   - The 4 WARNING follow-ups from workspace-health-advisor-pr4b verify report

5. **Public API preservation**: each slice's `cli/__init__.py` MUST add a re-export line for any name that moved out (verified via grep before each slice merge):
   ```python
   # After Slice 2
   from flow_engineering.cli.workspace import (
       workspace_health_cmd,  # NEW: was at line 3209 in monolith
       _workspace_hygiene_exit,
       _require_yes,
   )
   ```

---

## 7. Risks

| Risk | Likelihood | Severity | Mitigation |
|------|-----------|----------|------------|
| **r1**: Public API regression — `from flow_engineering.cli import _detect_project_markers` (or similar) breaks after a slice, breaking 60 test files | Medium | Critical | Each slice's PR description includes a grep verification: `git grep "from flow_engineering\.cli import <names-from-monolith>" tests/ src/` returns only re-export names. Add a CI step that runs the full pytest suite (already in CI). |
| **r2**: Click group double-registration — if a submodule's `@main.group()` decorator runs twice (e.g., imported eagerly in `__init__.py` AND also imported in a lazy load), click raises `RuntimeError: Group <name> is already registered` | Low | Critical | Use **lazy imports** in `cli/__init__.py`: `from flow_engineering.cli import workspace as _workspace  # noqa: F401`. The submodule's top-level decorators fire once at import time; `__init__.py` triggers that import lazily on first access. Or use `cli.dispatch.register()` pattern from click. |
| **r3**: Chain bloat — 8 PRs is still 8 reviewer rounds; if 1 PR gets stuck, the chain blocks | Medium | Medium | Use `feature-branch-chain` strategy (per design-e §ADR-e.1). Each PR targets the previous PR's branch. Rollback per-slice is `git revert <slice-N-sha>`. |
| **r4**: Orchestrator's "mechanical relocation only" framing conflicts with original design-e's behavior changes (metrics namespace, alias removal) | High (already happened) | Low | Document the scope reduction explicitly in the proposal phase. Defer alias removal + namespace BREAKING to follow-up issues (already pre-announced in CHANGELOG v1.2.0 line 22). |
| **r5**: Working branch drift — `codex/workspace-health-advisor-pr4b` has uncommitted changes (`openspec/specs/workspace/spec.md` modified + untracked `openspec/changes/archive/2026-07-07-workspace-health-advisor-pr4/`) that may conflict with v1.3-cli-split work | Medium | Low | The v1.3-cli-split tracker branch (`feature/v1.3-cli-split`) starts fresh from `origin/main` after workspace-health-advisor PR4 merges. No cross-branch conflict. |
| **r6**: 5–6 slice plan fails ≤500 LOC target (per §2 gap analysis) | Certain | Medium | Adopt Approach 2 (8–9 slices). Documented in §6 recommendation. |
| **r7**: `_detect_project_markers` is used by `health.py` (line 538) — if relocated to `cli/project.py` without re-export, `health.py` import breaks | Low | High | Add `from flow_engineering.cli.project import _detect_project_markers` re-export in `cli/__init__.py` (Slice 3). Verified: `health.py` only does `from flow_engineering.cli import _detect_project_markers`. |
| **r8**: `_git` is used by `workspace_hygiene.py` (line 363) — same concern as r7 | Low | High | Add re-export in Slice 3 (`cli/project.py` contains `_git`). |

---

## 8. Forward-compatibility

- **`workspace_health_cmd` (anchor at line 3131)**: Slice 2 moves it cleanly. The anchor comment is deleted as part of the move (its purpose is fulfilled).
- **The 4 WARNING follow-ups from workspace-health-advisor-pr4b**: NOT in v1.3-e scope. Track as separate issues.
- **Dead code at lines 320–349 (`archive()` function)**: NOT removed by v1.3-e. Flag for follow-up.
- **`drift_events_alias_group` removal**: NOT in v1.3-e scope (pre-announced in CHANGELOG v1.2.0; tracked separately).
- **`cli.py` shim/delete**: Already done in v1.3-d.

---

## 9. Success criteria

- [ ] `src/flow_engineering/cli/__init__.py` reduced to ≤500 LOC (Click group + lazy imports + re-export barrel)
- [ ] Each domain submodule ≤900 LOC (matches design-e cap)
- [ ] All 60+ existing test files pass unchanged after each slice
- [ ] Public API of `flow_engineering.cli` preserved (verified by grep + full pytest run)
- [ ] `from flow_engineering.cli.health` (or `.workspace_hygiene`) still works (re-exports preserved)
- [ ] No new logic introduced (purely mechanical relocation)
- [ ] Each slice's PR description includes: (a) "this slice relocates X LOC from the monolith verbatim" justification, (b) grep verification of re-exports, (c) full pytest run evidence
- [ ] Each slice rebases cleanly on the previous slice's branch (no cross-slice diffs in PR view)

---

## 10. Open questions (for orchestrator / user)

1. **Slice count**: Accept 8–9 slices (Approach 2) to hit ≤500 LOC? Or accept a larger `__init__.py` (~2,000 LOC) with 5–6 slices? **Recommend 8–9.**

2. **Tracker branch**: New `feature/v1.3-cli-split`? Or extend `feature/workspace-health-advisor-pr4`? **Recommend NEW tracker** — independent change, independent rollback.

3. **`cli/rotation.py` → `cli/archive.py` rename**: Standalone Slice 6, or merge with Slice 8 (`cli/archive.py` gets `archive_group` + `archive_change_cmd` + `rotate_cmd` all at once)? **Recommend merged with Slice 8** — keeps rename + relocation in one logical PR.

4. **`workspace_health_cmd` timing**: Move with `cli/workspace.py` in Slice 2 (anchor comment already declares this), or defer to a post-Slice-2 follow-up? **Recommend Slice 2** — anchor comment already commits to this; deferring would invalidate the anchor's promise.

5. **Should `cli/__init__.py` keep a CLI helper like `_git`/`_detect_project_markers` as a top-level re-export even after relocation, or should downstream code (`health.py`/`workspace_hygiene.py`) update their imports to use the new module paths?** **Recommend re-exports** — keeps backward compat with `from flow_engineering.cli import _git` working indefinitely.

6. **Behavior changes excluded from v1.3-e (alias removal, metrics namespace BREAKING, dead-code removal)**: Track as separate issues now, or defer until v1.4? **Recommend tracking as separate issues now** — gives visibility.

7. **Per-PR LOC budget**: 400 LOC default. Mechanical relocation justifies larger slices. Cap at 900 LOC per slice (design-e's design)? Or let slices grow to ~750 LOC (Approach 2's max)? **Recommend 900 LOC cap with explicit "relocation, not new logic" justification in each PR description.**

---

## 11. Ready for proposal

**YES** — recommendation is clear (Approach 2, 8–9 slice chain). Orchestrator can advance to `sdd-propose` with:

- **Scope**: mechanical relocation only; behavior changes deferred
- **Slice map**: 8 (or 9 if byte-identical help test warrants its own PR) chained PRs
- **Tracker branch**: `feature/v1.3-cli-split` (new)
- **Success criteria**: as listed in §9

If user prefers Approach 1 (5–6 slices, larger residual `__init__.py`), the proposal can also be written with that scope — but it MUST relax the ≤500 LOC success criterion.