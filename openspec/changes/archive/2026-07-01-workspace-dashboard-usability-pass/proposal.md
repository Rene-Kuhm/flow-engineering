# Proposal: workspace-dashboard-usability-pass

> **Phase**: propose (SDD pipeline)
> **Change**: `workspace-dashboard-usability-pass`
> **Mode**: openspec
> **Project**: flow-engineering v1.2.0
> **Strict TDD**: ON (feature change — ×6 multiplier per drift-hardening precedent)
> **Builds on**: explore #N (`openspec/changes/workspace-dashboard-usability-pass/explore.md`)

---

## Intent

Three cosmetic + usability defects on the **already-shipped** read-only dashboard (`flow workspace dashboard`). All three live in the Phase 5 dashboard surface — no new commands, no new flags, no mutations.

1. **Encoding/width**: `Gestor-de-Contraseas` renders as `Gestor-de-Contra` on Windows cp1252 terminals; long names truncate with Unicode `…` → ``.
2. **Dot-prefix scan filter**: `.atl`, `.opencode`, `.venv`, `.github`, `.ruff_cache` etc. appear as "projects" in every dashboard run — noise on every invocation.
3. **R1 detail**: dashboard says "R1: dirty" but shows no WHICH files are dirty.

---

## Scope

### In Scope

| # | Deliverable | Location |
|---|-------------|----------|
| 1 | Encoding + width fix: `sys.stdout.reconfigure(encoding="utf-8")` wrapped in `try/except OSError`; `Console(width=N, soft_wrap=True)`; per-column `min_width/max_width`; `OverflowMethod.fold` (no `…` Unicode ellipsis) | `cli.py:3089` + `dashboard.py:475-481, 535-576` |
| 2 | Dot-prefix scan filter: shared `_iter_project_subdirs(root)` helper excluding dot-prefix dirs; applied at `workspace_status` L3017 + `projects_ls` L3628 | `cli.py` |
| 3 | R1 detail: capture `git status --porcelain` stdout as `dirty_files: list[str]` in `_detect_project_markers`; thread through DS1/DS2 envelopes; render as new Section E (`render_r1_detail`) when any R1 triggered; cap 20 files/project with ASCII `...` | `cli.py:3545-3550` + `dashboard.py` |
| — | RED tests for all 3 points | `test_dashboard.py`, `test_cli_dashboard.py`, `test_cli_workspace_status.py`, `test_cli_projects.py` |

### Out of Scope

- NO new subcommands, NO new flags (`--json`, `--detail`, `--fix`, `--archive`, `--restore`, `--yes` absent)
- NO mutations to registry or filesystem
- NO modifications to `workspace/spec.md` root spec (deferred to next cleanup cycle)
- NO TUI/web/interactive/filter/layout changes ("Todavía estamos explorando producto real")
- NO modifications to PR1/PR2/PR3/sort-projects/3-prior-follow-up commits (Pattern #548)
- NO `stash`-triggering words, NO AI attribution in commits
- NO new runtime deps (`rich` already transitive)

---

## Capabilities

> Contract with `sdd-spec`: each modified/new capability maps to a delta spec entry.

### Modified Capabilities

| Capability | What changes |
|------------|--------------|
| `workspace-dashboard` (REQ-WORKSPACE-DASHBOARD-RENDERS-RICH) | **EXTEND** — add §4.1 "Output integrity" sub-clause: terminal-safe encoding (cp1252/UTF-8), column-width wrap (not truncate), no Unicode `…` ellipsis in output |
| `workspace-project-identity` (REQ-WORKSPACE-PROJECT-IDENTITY) | **MODIFY** — add sub-clause: projects are immediate subdirectories of projects root EXCLUDING any entry whose name starts with `.` (dot-prefix = tooling/config) |

### New Capabilities

| Capability | What it covers |
|------------|---------------|
| `workspace-dashboard-r1-detail` (REQ-WORKSPACE-DASHBOARD-R1-DETAIL) | New root REQ: when at least one project has R1 triggered, dashboard renders Section E listing per-R1 project + dirty file paths (cap 20/project, ASCII `...` truncation) |

---

## REQ Changes (from explore §5.2)

| REQ ID | Action | Rationale |
|--------|--------|-----------|
| `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH` | EXTEND | Add sub-clause: terminal-safe encoding + column-width wrap + no Unicode ellipsis |
| `REQ-WORKSPACE-PROJECT-IDENTITY` | MODIFY | Add sub-clause: dot-prefix entries excluded from project enumeration |
| `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` | **NEW** | New root REQ: Section E renders dirty file list when R1 triggered, cap 20 files/project |
| `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2` | *(no change)* | DS2 envelope shape unchanged; `dirty_files` added as additive field (schema versioning: consumers ignore unknown keys) |

---

## Approach

### Point 1 — Encoding/width (Option A, locked)

1. `cli.py:3089`: attempt `sys.stdout.reconfigure(encoding="utf-8")` wrapped in `try/except OSError`; fall back to current behavior (Pattern #551).
2. `Console(width=<terminal-width>, soft_wrap=True)` so dashboard shrinks gracefully on narrow terminals.
3. `dashboard.py`: explicit `min_width/max_width` per column on Section B + C tables; `OverflowMethod.fold` (wrap, not ellipsis); fallback `OverflowMethod.crop` (no ellipsis, no `…`).
4. Same fix applied to `render_archived` at L555.

### Point 2 — Dot-prefix scan filter (Option A, locked)

Extract `_iter_project_subdirs(root: Path) -> list[Path]` helper excluding `p.name.startswith(".")` entries. Apply at `workspace_status` L3017 and `projects_ls` L3628. Filter is silent (operators never opt in). Document: dot-prefix dirs are hidden from view only — NOT deleted, NOT archived, NOT mutated.

### Point 3 — R1 detail (Option B, locked)

1. `_detect_project_markers` (`cli.py:3545-3550`): capture `cp.stdout.strip().splitlines()` as `dirty_files: list[str]`; add to dict output.
2. `_summarize_workspace_status` (`cli.py:2892-2919`): copy `dirty_files` onto `needs_attention` entry when R1 reason added.
3. `dashboard.py`: new `render_r1_detail(needs_attention)` → `Table | None`; appended as Section E in `render_dashboard` only when any project has R1. Cap 20 files/project with ASCII `...`; footer tip amended to reference Section E.

---

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/flow_engineering/cli.py` | Modified | Encoding reconfigure + width at L3089; `_iter_project_subdirs` helper + 2 call sites L3017, L3628; `dirty_files` capture at L3545-3550 + propagation at L2892-2919 |
| `src/flow_engineering/dashboard.py` | Modified | Per-column widths at L475-481; `render_archived` widths at L535-576; `render_r1_detail` Section E at new function |
| `tests/unit/test_dashboard.py` | Modified | RED tests: encoding/width, Section E |
| `tests/unit/test_cli_dashboard.py` | Modified | RED tests: dot-prefix filter at scan sites, R1 detail threading |
| `tests/unit/test_cli_workspace_status.py` | Modified | RED tests: dot-prefix filter on status surface |
| `tests/unit/test_cli_projects.py` | Modified | RED tests: dot-prefix filter on projects ls surface |
| `src/flow_engineering/project_detector.py` | Audit only | Hidden-file semantics review; expect NO change |
| `src/flow_engineering/workspace_hygiene.py` | Audit only | `HIDDEN_SYSTEM_FILES` review; expect NO change |

---

## Delivery Strategy

### Cached: `single-pr-default`

Orchestrator has cached `delivery_strategy: single-pr-default`. This change is submitted as **one PR** unless `sdd-tasks` forecast proves >400 LOC realistic.

### Realistic LOC forecast

| Metric | Value | Notes |
|--------|-------|-------|
| Raw LOC (src + tests) | ~155 | explore §4.4 |
| ×6 strict-TDD multiplier | ~930 | Conservative (Constitution Article III precedent) |
| Realistic mid-range | ~400–700 | Actual TDD multiplier closer to 3–4× for tests + 1.5× fixtures |

### Tentative PR split (NOT locked — possibility only)

`sdd-tasks` is the gate. Split is a **possibility**, not a commitment:

| PR | Contents | Raw LOC | Multiplied |
|----|----------|---------|------------|
| **PR1 (tentative)** | Encoding/width + dot-prefix filter | ~75 | ~450 |
| **PR2 (tentative)** | R1 detail (data flow + Section E) | ~80 | ~480 |

Rationale: PR1 = cosmetic/scan (low risk, independent). PR2 = data-flow change (medium risk). If `sdd-tasks` forecast stays ≤400 LOC realistic, single PR is preferred (per user preference for tight usability pass).

### sdd-tasks gate

`sdd-tasks` will validate task-by-task forecast and trigger the **Review Workload Guard** if realistic LOC > 400. The orchestrator's cached `single-pr-default` will be overridden by the guard decision at that phase.

---

## Risks

### Per-point

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `sys.stdout.reconfigure` fails on legacy Windows terminal | LOW | `try/except OSError` fallback; defensive default (Pattern #551) |
| `Console(width=N)` breaks auto-detect | LOW | Use terminal introspection first; explicit `width=120` default |
| `OverflowMethod.fold` breaks per-row color coding | LOW | Rich applies row style to all cells; tested via snapshot |
| Dot-prefix filter hides a real user project | LOW | All 3 retrospective cycles confirm no real dot-prefix project; filter is view-only (no deletion) |
| `dirty_files` unbounded on very dirty project | LOW | Cap 20 files/project + ASCII `...` truncation + footer "run `git status`" hint |
| Adding `dirty_files` to DS1/DS2 breaks pinned consumers | MEDIUM | Additive field only; consumers ignore unknown keys; document in changelog |

### Cross-point / Scope realism

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Single PR exceeds 400-line budget | **HIGH** | sdd-tasks gate; tentative PR1/PR2 split available |
| Combined PR hides 3 distinct changes from reviewer | MEDIUM | Sub-batches A/B/C within work-unit commit; commit message cites each |
| 3 changes in one change folder = 3 features in 1 PR | LOW | Matches `phase-5-dashboard` precedent (3 PRs in one change); scoped as single usability pass |

---

## Rollback Plan

1. Revert `cli.py`: remove `sys.stdout.reconfigure` + `Console(width=...)`; restore `_iter_project_subdirs` to `root.iterdir()` at L3017 + L3628; revert `dirty_files` capture to `bool(cp.stdout.strip())`
2. Revert `dashboard.py`: remove per-column widths; remove `render_r1_detail` + Section E from `render_dashboard`
3. Revert 4 test files to pre-change state
4. Run full suite — expect 38 dashboard tests passing

---

## Dependencies

- PR1+PR2+PR3 dashboard commits (`6651add`, `95e8579`, `778efdb`) — LOCKED, Pattern #548
- `sort_projects` (`c9c9650d`) — LOCKED
- 3 prior follow-up commits — LOCKED
- DS1 + DS2 envelope shapes — stable (additive `dirty_files` field, consumers ignore unknown keys)

---

## Success Criteria

- [ ] `Gestor-de-Contraseas` renders correctly (no ``) on cp1252 + UTF-8 terminals
- [ ] Long project names wrap (not truncate) within column bounds; no `…` in output
- [ ] `.atl`, `.opencode`, `.venv`, `.github`, `.ruff_cache`, `.mypy_cache`, `.pytest_cache`, `.specify` absent from dashboard + `flow projects ls` + `flow workspace status`
- [ ] Section E appears only when at least one project has R1 triggered; lists up to 20 dirty files per project with ASCII `...` truncation
- [ ] DS1 + DS2 envelopes remain schema-compatible (additive field)
- [ ] 38 existing dashboard tests + all new RED tests pass
- [ ] Zero new runtime deps; `rich` stays transitive
- [ ] No `stash`-triggering words; no AI attribution in commits

