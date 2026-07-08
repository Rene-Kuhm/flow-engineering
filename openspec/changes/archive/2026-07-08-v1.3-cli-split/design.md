# Design: v1.3-cli-split (mechanical relocation)

> **Change**: `v1.3-cli-split` — split 5,337-LOC `cli/__init__.py` into 8 domain submodules.
> **Tracker**: NEW `feature/v1.3-cli-split` from `origin/main` @ `8577d9c` (workspace-health-advisor PR4 merged).
> **Builds on**: `openspec/changes/v1.3-cli-split/{explore.md, proposal.md, specs/cli-split/spec.md}`.
> **Artifact store mode**: hybrid (this file + Engram `sdd/v1.3-cli-split/design`).

## 1. Technical approach

Mechanical relocation only — `git mv` source blocks from `cli/__init__.py` into 8 new/renamed submodules, leaving `cli/__init__.py` as a Click-group stub + re-export barrel. Zero new logic, zero behavior changes (REQ-CLI-SPLIT-4). 8-slice Feature Branch Chain (`feature-branch-chain` strategy, per-slice rollback via `git revert <sha>`).

The relocation is verified by `git diff -M --find-renames=90%` reporting ≥90% similarity per slice and a full pytest pass (1,405+ tests, REQ-CLI-SPLIT-1).

## 2. Architecture decisions

| Decision | Choice | Rationale |
|---|---|---|
| Branch chain strategy | `feature-branch-chain` (each PR targets `feature/v1.3-cli-split`) | Avoids cumulative diff explosion across 8 PRs; per-slice rollback is one `git revert`. |
| Submodule import pattern in `cli/__init__.py` | Lazy `from . import <sub> as _<sub>` at module level | Precedent at line 5298 (`from flow_engineering.cli.rotation import rotate_cmd  # noqa: E402`) — Click registers decorators once per submodule; eager re-import in `__init__.py` is a no-op but lazy is explicit + future-proof. |
| Public-API preservation | Re-export barrel at bottom of `cli/__init__.py` | 60+ test files + `health.py`/`workspace_hygiene.py` import 8 private/public names. Changing import paths would touch 25 test files + 2 src files. Re-export preserves callsite stability. |
| `cli/rotation.py` rename to `cli/archive.py` | Rename + thin back-compat shim | `tests/unit/test_cli_rotation.py:26` does `from flow_engineering.cli.rotation import (...)`. Spec says "delete rotation.py" but that breaks the test. **Resolution**: rename body to `cli/archive.py`, keep `cli/rotation.py` as a 3-line re-export shim (`from flow_engineering.cli.archive import rotate_cmd, _candidate_entries, _entry_mtime`). Zero test modifications. |
| `workspace_health_cmd` timing | Move in Slice 2 | Anchor comment at `cli/__init__.py:3131` already pre-commits to this. Forward-compat win from PR4. |

## 3. Slice map (relocation order)

Verified source ranges via `grep` against `origin/main` @ `8577d9c` (file is **5,337 LOC** here, not 4,695 as explore originally estimated — PR4a+PR4b are already merged into main).

| # | Source (in `cli/__init__.py`) | Target file | git mv / new | Re-exports added to `cli/__init__.py` | LOC moved |
|---|---|---|---|---|---|
| 1 | lines 85–183 (constants + `_resolve_projects_root` + `_iter_project_subdirs` + `_read_pyproject_min_skill_versions` + `_enforce_min_skill_versions_or_exit`) | `cli/_shared.py` | NEW (no mv — extracted) | `_iter_project_subdirs` | ~100 |
| 2 | lines 2894–3574 (`workspace_group` + 6 sub-commands incl. `workspace_health_cmd` block + 13 hygiene helpers; **anchor at line 3131**) | `cli/workspace.py` | NEW | `workspace_health_cmd`, `_summarize_workspace_status` | ~680 |
| 3 | lines 3575–4101 (`projects_group` + 3 sub-commands + `_git` + `_detect_project_markers` + 3 detection helpers) | `cli/project.py` | NEW | `_detect_project_markers`, `_git` | ~527 |
| 4 | lines 2076–2893 (`drift_group` + `drift_run` + `drift_events_group` + 3 events commands + `drift_events_alias_group` + 3 alias shims + 8 helpers) | `cli/drift.py` | NEW | `_format_drift_events_text` | ~817 |
| 5 | lines 4103–4493 (`snapshot_group` + 6 sub-commands + 3 snapshot helpers) | `cli/snapshot.py` | NEW | — (only `main` is tested; `snapshot_*` are reached via the group) | ~390 |
| 6 | lines 4494–5282 (`prompts_group` + 4 sub-commands + `CheckAction` + 11 prompts helpers) | `cli/prompts.py` | NEW | — | ~788 |
| 7 | lines 1517–2074 (`metrics_group` + 3 children + `_summarize_metrics` + `_apply_metrics_filters`; **legacy flat dump preserved verbatim**) | `cli/metrics.py` | NEW | — | ~557 |
| 8 | rename `cli/rotation.py` → `cli/archive.py`; relocate lines 5284–5335 (`archive_group` + `archive_change_cmd` + late import) | `cli/archive.py` | `git mv cli/rotation.py cli/archive.py` + extract lines 5284–5335 | `rotate_cmd` | ~140 (rename) + ~52 (extract) |

**Total relocated**: ~3,909 LOC out of 5,337. **Residual `__init__.py`**: ~1,428 LOC (top-level scaffold `new`/`apply`/`verify`/`where`/`engram`/`watch`/imports/main — see Open Question Q1).

### Why this order

1. **Slice 1 (`_shared.py`) FIRST** — every other slice imports the constants and skill-version helpers. Moving it second would require forward-declarations.
2. **Slice 2 (`workspace.py`) SECOND** — includes the anchor-comment block for `workspace_health_cmd` (line 3131), which is the **PR4 forward-compat commitment**. Largest single domain (~680 LOC). Tests for `workspace_health` and `workspace_status` are the most sensitive to byte-determinism (REQ-CLI-SPLIT-3).
3. **Slices 3-7 in size order** (descending): drift (817) → prompts (788) → metrics (557) → project (527) → snapshot (390). Putting biggest relocations in the middle reduces risk of leaving the biggest PR for last.
4. **Slice 8 (`archive.py` rename) LAST** — cleanups are safest when everything else is in place; rename + late-import conversion is mechanical and isolated.

## 4. Per-PR structure (each slice = 2-4 commits)

| # | Commit | Files touched | Commit message template |
|---|---|---|---|
| C1 | Source relocation | `cli/__init__.py` (deleted block) + new `cli/<sub>.py` | `refactor(cli): relocate <domain> to cli/<sub>.py (Slice N/8)` |
| C2 | Public-API re-export | `cli/__init__.py` (append re-export block) | `refactor(cli): re-export <names> from cli/<sub>.py (Slice N/8)` |
| C3 | Lock public-API | `cli/__init__.py` (no-op or comment) — or just rely on CI | `test(cli): lock public-API surface post-slice-N (no new tests)` — only needed if pytest fails without an extra sanity import; otherwise C3 is the test-run evidence in PR body, not a new commit |
| C4 (optional) | Review nits | target submodule | `refactor(cli): extract <domain> constants in cli/<sub>.py (Slice N/8 nit)` |

**Result**: 2-4 commits per slice × 8 slices = **16-32 commits**. Each PR targets `feature/v1.3-cli-split` (classical form). PRs over 400 LOC (Slices 2, 3, 4, 5, 7) MUST include the literal string "Mechanical relocation, not new logic" with links to `specs/cli-split/spec.md` and this `design.md` (REQ-CLI-SPLIT-5).

## 5. Public API surface (8 names)

| Name | Module after split | Test/downstream consumers |
|---|---|---|
| `main` | `cli/__init__.py` (stays) | 27 test files + `src/flow_engineering/cli/__init__.py` re-export |
| `workspace_health_cmd` | `cli/workspace.py` (re-exported) | `tests/unit/test_cli_workspace_health.py:21` |
| `_detect_project_markers` | `cli/project.py` (re-exported) | 8× in `test_cli_projects.py` + `src/flow_engineering/health.py:538` |
| `_format_drift_events_text` | `cli/drift.py` (re-exported) | 2× in `test_cli_drift_events_list.py:380,389` |
| `_iter_project_subdirs` | `cli/_shared.py` (re-exported) | 2× in `test_cli_workspace_status.py:177,194` |
| `_summarize_workspace_status` | `cli/workspace.py` (re-exported) | 2× in `test_cli_workspace_status.py:348,379` |
| `_git` | `cli/project.py` (re-exported) | `src/flow_engineering/workspace_hygiene.py:363` |
| `rotate_cmd` | `cli/archive.py` (re-exported; also `cli/rotation.py` shim) | `test_cli_rotation.py:23` (`from cli import main`) + `:26` (`from cli.rotation import ...`) |

## 6. Lazy-import pattern (precedent at line 5298)

`cli/__init__.py` already has the precedent at line 5298:

```python
from flow_engineering.cli.rotation import rotate_cmd  # noqa: E402
```

This is a **late module-level import** that fires the `@click.command(name="rotate")` decorator at import time. Each submodule (`workspace.py`, `drift.py`, etc.) MUST use the same shape to avoid `RuntimeError: Group <name> is already registered`:

```python
# Pattern (per slice)
from . import workspace as _workspace  # noqa: F401  (lazy submodule init)
from .workspace import workspace_health_cmd, _summarize_workspace_status  # re-export
```

The `as _<sub>` import registers decorators exactly once (Python caches submodules in `sys.modules`). Direct `from .workspace import workspace_health_cmd` then re-exports the name without re-triggering registration. **`# noqa: E402` is unnecessary** in the new pattern because the imports are at module top, not mid-file.

## 7. Risks and mitigations

| Risk | L×S | Mitigation |
|---|---|---|
| **r1**: Public-API regression across 25 test files + 2 src files | M×Critical | Each slice's PR adds re-exports (Section 5). CI gate: `uv run pytest tests/unit/test_cli_*.py` must stay green. |
| **r2**: Click double-registration (`RuntimeError: Group <name> is already registered`) | L×Critical | Lazy submodule import (Section 6). Verified pattern from `rotation.py`. |
| **r3**: 5/8 slices >400-LOC review budget (Slices 2, 3, 4, 5, 7) | H×Medium | REQ-CLI-SPLIT-5: each over-budget PR includes "Mechanical relocation, not new logic" paragraph + spec/design links + LOC count + expected 0 new functions + expected 0 new test files. |
| **r4**: Behavioral drift accidentally introduced | L×High | REQ-CLI-SPLIT-3 (byte-determinism): `flow workspace health --json` sha256 must match `origin/main` baseline. CI captures baseline before Slice 1. |
| **r5**: Working tree dirty (uncommitted `openspec/specs/workspace/spec.md` + untracked `openspec/changes/v1.3-cli-split/`) | M×Low | `feature/v1.3-cli-split` is a NEW tracker branch from `origin/main`; no cross-branch conflict. |
| **r6**: `cli/__init__.py` residual ≥500 LOC | Certain×Low | See Open Question Q1. |
| **r7**: `test_cli_rotation.py:26` imports from `flow_engineering.cli.rotation` directly (not from `flow_engineering.cli`) | M×High | Slice 8 keeps `cli/rotation.py` as a 3-line back-compat shim (Section 2). |

## 8. v1.3-e migration dependency from PR4 (forward-compat win)

`cli/__init__.py:3131` carries:

```python
# REQ-WORKSPACE-HEALTH-* (PR4a) — `flow workspace health` (Phase 6, PR4 wiring).
# v1.3-e migration: this block moves to cli/workspace.py per design §v1.3-e.
```

This block (lines 3130-3287, ~157 LOC) contains `workspace_health_cmd` + `_normalize_filter_rules` + `_HEALTH_FILTER_CHOICES` + the command's 5 click options. **Slice 2 moves it cleanly into `cli/workspace.py`**, deleting the anchor comment as the new module path documents the relocation. The 4 WARNING follow-ups from PR4b's verify report are explicitly out of scope (deferred to follow-up issues).

## 9. Open questions

- [ ] **Q1**: The 8-slice map covers ~3,909 LOC; residual `cli/__init__.py` ≈ 1,428 LOC (top-level scaffold: `new`/`new_project`/`status`/`doctor`/`apply`/`verify`/`watch`/`memory_timeline`/`where_cmd` + helpers + `save`/`search`/`reindex`/`inspect` + helpers + module imports + `main`). The proposal's "≤500 LOC after all slices" success criterion **cannot be met with 8 slices** (the explore's Approach 2 had 8-9 slices including `engram.py`/`where.py`/`watch.py`/`core.py` for top-level commands). **Decision needed**: (a) add 3-4 more slices (12 total) to hit ≤500, OR (b) accept ~1,400 LOC residual and revise the criterion. Recommend (b) for v1.3-cli-split and file follow-up issue for residual split.
- [ ] **Q2**: `cli/rotation.py` deletion vs back-compat shim (Section 2). Design recommends **shim** (3 lines). Spec says "delete". Need orchestrator/user confirmation.
- [ ] **Q3**: Tracker branch already created? Currently `codex/workspace-health-advisor-pr4b` is checked out and `feature/v1.3-cli-split` does not exist on local or remote. Slice 0 (PR creation step) must run before Slice 1's first commit.

## 10. Files affected

| File | Action |
|---|---|
| `src/flow_engineering/cli/__init__.py` | TRIM from 5,337 → ~1,428 LOC; becomes Click-group stub + re-export barrel |
| `src/flow_engineering/cli/_shared.py` | NEW |
| `src/flow_engineering/cli/workspace.py` | NEW |
| `src/flow_engineering/cli/project.py` | NEW |
| `src/flow_engineering/cli/drift.py` | NEW |
| `src/flow_engineering/cli/snapshot.py` | NEW |
| `src/flow_engineering/cli/prompts.py` | NEW |
| `src/flow_engineering/cli/metrics.py` | NEW |
| `src/flow_engineering/cli/archive.py` | RENAME of `rotation.py` + lines 5284–5335 |
| `src/flow_engineering/cli/rotation.py` | KEEP as 3-line back-compat shim |
| `tests/unit/test_cli_*.py` (25 files) | UNCHANGED |
| `src/flow_engineering/health.py` | UNCHANGED |
| `src/flow_engineering/workspace_hygiene.py` | UNCHANGED |