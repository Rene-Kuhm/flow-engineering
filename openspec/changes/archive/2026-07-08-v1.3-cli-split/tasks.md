# Tasks: v1.3-cli-split (mechanical relocation)

> **Change**: `v1.3-cli-split` — split `cli/__init__.py` into 8 domain submodules via `git mv`.
> **Tracker**: NEW `feature/v1.3-cli-split` from `origin/main` @ `8577d9c`.
> **Mode**: hybrid (Engram `sdd/v1.3-cli-split/tasks` + this file).
> **TDD**: NONE for new tests — relocation only (REQ-CLI-SPLIT-4). Existing `tests/unit/test_cli_*.py` MUST stay green.

## Review Workload Forecast

| Metric | Value |
|--------|-------|
| Total LOC moved | ~3,909 |
| Slices count | 8 |
| Per-slice LOC range | 150–700 |
| 400-line budget risk | Medium (5/8 slices >400, justified by REQ-CLI-SPLIT-5) |
| Chained PRs | Yes |
| Chain strategy | feature-branch-chain |
| Decision needed before apply | No (orchestrator pre-approved design Q1/Q2/Q3) |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Medium

## TDD Discipline

- Mechanical relocation only — **NO new tests** (REQ-CLI-SPLIT-4).
- Compact B throughout: prod-first, then `uv run pytest tests/unit/test_cli_*.py -q`.
- CI gate per slice: `uv run pytest tests/unit/test_cli_*.py -q` green (existing 27 `test_cli_*.py` files, 1,405+ tests).
- Byte-determinism: `flow workspace health --json` sha256 MUST match `origin/main` baseline after Slice 2 (REQ-CLI-SPLIT-3).

## Phase 0 — Branch chain setup (T-0, MUST run before Slice 1)

```bash
git fetch origin
git checkout -b feature/v1.3-cli-split origin/main
git push -u origin feature/v1.3-cli-split
git checkout -b codex/v1.3-cli-split-1-shared feature/v1.3-cli-split
git push -u origin codex/v1.3-cli-split-1-shared
```

- [x] **T-0.1** Create tracker `feature/v1.3-cli-split` from `origin/main` @ `8577d9c`. rollback: `git push origin --delete feature/v1.3-cli-split`. *(created 2026-07-07, apply batch v1.3-cli-split-pr1)*
- [x] **T-0.2** Create first slice branch `codex/v1.3-cli-split-1-shared`. rollback: `git push origin --delete codex/v1.3-cli-split-1-shared`. *(created 2026-07-07, apply batch v1.3-cli-split-pr1)*
- Each subsequent slice branches from the **previous slice's branch** (feature-branch-chain): slice N from `codex/v1.3-cli-split-{N-1}-*`.

## Phase 1–8 — Slice tasks (T-1 through T-8)

Each slice = 3 work-unit commits (C1=C2=C3) + optional C4 readability nit. Pattern per slice:

| Field | Value |
|-------|-------|
| `commit_number` | C1 (relocate) → C2 (re-export + lazy import) → C3 (verify, no source change) → C4 (optional nit) |
| `ci_gates` | `uv run pytest tests/unit/test_cli_*.py -q` exits 0; byte-determinism check where applicable |
| `rollback_cmd` | `git revert HEAD~N..HEAD` (N = number of slice commits to revert) |
| `over_400_loc` | If `True`: PR description MUST contain literal string "Mechanical relocation, not new logic" + link to `specs/cli-split/spec.md` + `design.md` (REQ-CLI-SPLIT-5) |

### T-1 — `cli/_shared.py` (~250 LOC)

- depends_on: T-0.2
- source_lines: `cli/__init__.py:85–183` *(expanded to 81–183 to include the 2 module-level constants `_DEFAULT_PROJECTS_ROOT_WIN` / `_DEFAULT_PROJECTS_ROOT_NIX` that sit immediately above the helpers; both are used by tests/downstream consumers via `_resolve_projects_root`)*
- target_file: `cli/_shared.py` (NEW)
- re_exports: `_iter_project_subdirs` (plus the 3 internal-only names that `_cli/__init__.py` still calls in-place: `_DEFAULT_PROJECTS_ROOT_WIN`, `_DEFAULT_PROJECTS_ROOT_NIX`, `_resolve_projects_root`, `_read_pyproject_min_skill_versions`, `_enforce_min_skill_versions_or_exit`); lazy `from . import _shared as _shared  # noqa: F401`
- commit_messages: `refactor(cli): relocate shared helpers to cli/_shared.py (Slice 1/8)` → `refactor(cli): re-export _iter_project_subdirs from cli/_shared.py (Slice 1/8)` → `chore(cli): verify cli/_shared.py slice 1 pytest green (Slice 1/8)` *(committed as a single combined commit `dabe321` because the orchestrator prompt's framing treats all three steps together — keeping the tree green on every push boundary; per-slice rollback via `git revert dabe321` still works cleanly)*
- over_400_loc: false
- [x] **applied 2026-07-07 (commit `dabe321`)** — `cli/_shared.py` created (124 LOC), `cli/__init__.py` reduced by 104 LOC; public API verified importable (`_resolve_projects_root`, `_iter_project_subdirs`, `_DEFAULT_PROJECTS_ROOT_WIN`, `_DEFAULT_PROJECTS_ROOT_NIX`); targeted pytest `test_cli_workspace_status.py + test_cli_workspace_health.py` 34/34 PASSED; PR #32 opened against `feature/v1.3-cli-split`.

### T-2 — `cli/workspace.py` (~700 LOC, includes `workspace_health_cmd` anchor at line 3131)

- depends_on: T-1 (after merge); branch from `codex/v1.3-cli-split-1-shared`
- source_lines: `cli/__init__.py:2894–3574`
- target_file: `cli/workspace.py` (NEW; deletes the v1.3-e anchor comment at line 3131)
- re_exports: `workspace_health_cmd`, `_summarize_workspace_status`; lazy `from . import workspace as _workspace  # noqa: F401`
- commit_messages: `refactor(cli): relocate workspace group to cli/workspace.py (Slice 2/8)` → `refactor(cli): re-export workspace_health_cmd from cli/workspace.py (Slice 2/8)` → `chore(cli): verify cli/workspace.py slice 2 byte-determinism green (Slice 2/8)`
- over_400_loc: **true** — PR body requires "Mechanical relocation, not new logic" justification
- [x] **applied 2026-07-07 (PR #33, merged)** — `cli/workspace.py` created (737 LOC); `cli/__init__.py` net -681 LOC; byte-determinism preserved (SHA-256 `B51EC7F5...` matches `origin/main` baseline); 34/34 targeted workspace tests PASS. See `apply-progress.md` §"Slice 2" for full evidence. *Stale-checkbox reconciliation at archive time: T-2 was not marked [x] by sdd-apply; the orchestrator's archive instruction confirmed full implementation and apply-progress.md documents the per-slice commit + verification. Marked [x] at archive.*

### T-3 — `cli/project.py` (~600 LOC)

- depends_on: T-2; branch from `codex/v1.3-cli-split-2-workspace`
- source_lines: `cli/__init__.py:3575–4101`
- target_file: `cli/project.py` (NEW)
- re_exports: `_detect_project_markers`, `_git`; lazy `from . import project as _project  # noqa: F401`
- commit_messages: `refactor(cli): relocate projects group to cli/project.py (Slice 3/8)` → `refactor(cli): re-export _detect_project_markers from cli/project.py (Slice 3/8)` → `chore(cli): verify cli/project.py slice 3 pytest green (Slice 3/8)`
- over_400_loc: **true** — justification required
- [x] **applied 2026-07-07 (PR #35, merged)** — `cli/project.py` created (579 LOC); `cli/__init__.py` net -528 LOC; public API preserved (`_detect_project_markers`, `_git`); 34/34 targeted workspace tests PASS. See `apply-progress.md` §"Slice 3" for full evidence. *Stale-checkbox reconciliation at archive time: marked [x] at archive per orchestrator instruction + apply-progress proof.*

### T-4 — `cli/drift.py` (~700 LOC, preserves `drift_events_alias_group` intact)

- depends_on: T-3; branch from `codex/v1.3-cli-split-3-project`
- source_lines: `cli/__init__.py:2076–2893`
- target_file: `cli/drift.py` (NEW; carries `_resolve_snapshots_dir` + `_parse_since` + drift block)
- re_exports: `_format_drift_events_text`; lazy `from . import drift as _drift  # noqa: F401`
- commit_messages: `refactor(cli): relocate drift group to cli/drift.py (Slice 4/8)` → `refactor(cli): re-export _format_drift_events_text from cli/drift.py (Slice 4/8)` → `chore(cli): verify cli/drift.py slice 4 pytest green (Slice 4/8)`
- over_400_loc: **true** — justification required
- [x] **applied 2026-07-07 (PR #36, merged)** — `cli/drift.py` created (890 LOC); `cli/__init__.py` net -807 LOC; `drift_events_alias_group` preserved INTACT (REQ-V1.2.4); 20/20 drift tests + 34/34 targeted workspace tests PASS. See `apply-progress.md` §"Slice 4" for full evidence. *Stale-checkbox reconciliation at archive time: marked [x] at archive per orchestrator instruction + apply-progress proof.*

### T-5 — `cli/snapshot.py` (~350 LOC)

- depends_on: T-4; branch from `codex/v1.3-cli-split-4-drift`
- source_lines: `cli/__init__.py:4103–4493`
- target_file: `cli/snapshot.py` (NEW)
- re_exports: (none — `snapshot_*` reached via `main` group); lazy `from . import snapshot as _snapshot  # noqa: F401`
- commit_messages: `refactor(cli): relocate snapshot group to cli/snapshot.py (Slice 5/8)` → `refactor(cli): lazy-import cli/snapshot.py (Slice 5/8)` → `chore(cli): verify cli/snapshot.py slice 5 pytest green (Slice 5/8)`
- over_400_loc: false
- [x] **applied 2026-07-07 (PR #37, merged)** — `cli/snapshot.py` created (420 LOC); `cli/__init__.py` net -363 LOC; 24/24 snapshot tests PASS + 335/335 CLI tests PASS; byte-determinism preserved. See `apply-progress.md` §"Slice 5" for full evidence. *Stale-checkbox reconciliation at archive time: marked [x] at archive per orchestrator instruction + apply-progress proof.*

### T-6 — `cli/prompts.py` (~300 LOC)

- depends_on: T-5; branch from `codex/v1.3-cli-split-5-snapshot`
- source_lines: `cli/__init__.py:4494–5282`
- target_file: `cli/prompts.py` (NEW; carries `CheckAction` + `_emit_check_observability` + `_resolve_check_action`)
- re_exports: (none); lazy `from . import prompts as _prompts  # noqa: F401`
- commit_messages: `refactor(cli): relocate prompts group to cli/prompts.py (Slice 6/8)` → `refactor(cli): lazy-import cli/prompts.py (Slice 6/8)` → `chore(cli): verify cli/prompts.py slice 6 pytest green (Slice 6/8)`
- over_400_loc: false
- [x] **applied 2026-07-07 (PR #38, merged)** — `cli/prompts.py` created (717 LOC; tasks.md ~300 estimate undersized — actual 717 per apply-progress §"Slice 6"); `cli/__init__.py` net -766 LOC; 38/38 prompts tests + 11/11 golden snapshot tests + 34/34 targeted workspace tests PASS. `_GOLDEN_PROMPTS_DIR` test-seam re-export pattern applied. See `apply-progress.md` §"Slice 6" for full evidence. *Stale-checkbox reconciliation at archive time: marked [x] at archive per orchestrator instruction + apply-progress proof.*

### T-7 — `cli/metrics.py` (~500 LOC, legacy flat dump preserved verbatim)

- depends_on: T-6; branch from `codex/v1.3-cli-split-6-prompts`
- source_lines: `cli/__init__.py:1517–2074`
- target_file: `cli/metrics.py` (NEW; preserves lines 1545–1547 flat-dump shim intact)
- re_exports: (none); lazy `from . import metrics as _metrics  # noqa: F401`
- commit_messages: `refactor(cli): relocate metrics group to cli/metrics.py (Slice 7/8)` → `refactor(cli): lazy-import cli/metrics.py (Slice 7/8)` → `chore(cli): verify cli/metrics.py slice 7 pytest green (Slice 7/8)`
- over_400_loc: **true** — justification required
- [x] **applied 2026-07-08 (PR #39, merged)** — `cli/metrics.py` created (595 LOC); `cli/__init__.py` net -529 LOC; legacy flat dump shim preserved VERBATIM (REQ-V1.3.6 contract); 30/30 metrics tests PASS (2 pre-existing time-sensitive `test_*_with_window_filter` failures deselected — same pattern on `origin/main` and tracker pre-Slice-7, NOT regressions). See `apply-progress.md` §"Slice 7" for full evidence. *Stale-checkbox reconciliation at archive time: marked [x] at archive per orchestrator instruction + apply-progress proof.*

### T-8 — `cli/archive.py` rename (~150 LOC + 3-line back-compat shim in old path)

- depends_on: T-7; branch from `codex/v1.3-cli-split-7-metrics`
- source_lines: `cli/rotation.py` (whole file, ~140 LOC) + `cli/__init__.py:5284–5335` (`archive_group` + `archive_change_cmd` + late import)
- target_file: `cli/archive.py` (NEW, content = rotation body + archive group + archive_change_cmd); `cli/rotation.py` reduced to 3-line shim `from flow_engineering.cli.archive import rotate_cmd, _candidate_entries, _entry_mtime`
- re_exports: `rotate_cmd`; lazy `from . import archive as _archive  # noqa: F401`
- commit_messages: `refactor(cli): rename rotation.py → archive.py and relocate archive group (Slice 8/8)` → `refactor(cli): back-compat shim cli/rotation.py → cli/archive.py (Slice 8/8)` → `chore(cli): verify cli/archive.py slice 8 pytest green (Slice 8/8)`
- over_400_loc: false
- [x] **applied 2026-07-08 (PR #40, merged)** — `cli/rotation.py` renamed to `cli/archive.py` (267 LOC total = rotation body + archive group + archive_change_cmd + late import); `cli/rotation.py` reduced to 3-line back-compat shim preserving `from flow_engineering.cli.rotation import (...)` test seam. `rotate_cmd` importable from `flow_engineering.cli` (REQ-CLI-SPLIT-2). See `apply-progress.md` §"Slice 8" for full evidence. *Stale-checkbox reconciliation at archive time: marked [x] at archive per orchestrator instruction + apply-progress proof.*

## Per-Slice Optional Commit (C4)

- title: `chore(cli): review-readability nits on cli/<submodule>.py (Slice N/8)`
- when: only if reviewer flags readability findings (extract magic numbers, group imports, etc.)
- skip: if no findings

## Public-API Re-export Checklist (per slice, MUST verify before merge)

```bash
# Run after each slice's C3:
git grep -n "from flow_engineering\.cli import" tests/ src/ | \
  xargs -I{} echo "{}" | sort -u
# Each name must resolve via cli/__init__.py re-export OR the original module path.
```

8 names MUST stay importable across all slices: `main`, `workspace_health_cmd`, `_detect_project_markers`, `_format_drift_events_text`, `_iter_project_subdirs`, `_summarize_workspace_status`, `_git`, `rotate_cmd` (REQ-CLI-SPLIT-2).

## Implementation Order Rationale

1. **Slice 1 (`_shared.py`) FIRST** — every other slice imports the constants + skill-version helpers.
2. **Slice 2 (`workspace.py`) SECOND** — carries the v1.3-e anchor at line 3131; largest single domain (~680 LOC).
3. **Slices 3–8** in remaining order: project → drift → snapshot → prompts → metrics → archive rename. Drift and prompts are biggest; placed in middle to avoid leaving them for last.
4. **Slice 8 LAST** — rename + late-import conversion is mechanical + isolated.

## Risks

- **r1**: Public-API regression (27 test files + 2 src files import the 8 names). Mitigation: per-slice grep verification + full pytest run; CI gate.
- **r2**: Click group double-registration if submodule imported eagerly. Mitigation: lazy `from . import <sub> as _<sub>  # noqa: F401` pattern (precedent at `cli/__init__.py:5298`).
- **r3**: 5/8 slices >400-LOC review budget. Mitigation: REQ-CLI-SPLIT-5 justification paragraph in PR body for Slices 2, 3, 4, 5, 7.
- **r4**: `cli/__init__.py` residual ≥500 LOC after all slices (top-level scaffold + where + engram + watch unaccounted). Out of scope; track as follow-up issue.

## Out of Scope (deferred to follow-up issues)

- REQ-V1.3.6 metrics namespace rewrite (legacy flat dump preserved verbatim in Slice 7).
- REQ-V1.3.7 removal of `drift-events` deprecated group (kept intact in Slice 4).
- Dead-code removal (`archive()` function at pre-split `__init__.py:320–349`).
- Residual split of top-level commands (`new`/`apply`/`where`/`save`/`watch`).
- New tests, new CLI commands, new options.

## Cross-references

- Proposal: `openspec/changes/v1.3-cli-split/proposal.md`
- Spec: `openspec/changes/v1.3-cli-split/specs/cli-split/spec.md`
- Design: `openspec/changes/v1.3-cli-split/design.md`
- Tracker: `feature/v1.3-cli-split` (T-0)