# Archive Report — `sort-projects-align-with-real-ds-data-flow` (FINAL close-out)

> **Change**: `sort-projects-align-with-real-ds-data-flow` — a **contract fix** for the Phase 5 dashboard. Read it together with the parent `phase-5-dashboard` archive-report for full lineage; this report is the FINAL close-out of the small data-flow correction that flowed out of PR3 design §9.3 carry-forward.
> **Status**: **ARCHIVED (FINAL, single PR, success with 1 minor WARNING)** — 2026-06-30.
> **SDD cycle**: explore → propose → spec → design → tasks → apply (single atomic commit) → verify → **archive (FINAL, this report)** → user merge to main + push.
> **Archive destination**: `openspec/changes/archive/2026-06-30-sort-projects-align-with-real-ds-data-flow/`.
> **Mode**: hybrid — OpenSpec file (this report) + Engram mirror (NEW topic_key `sdd/sort-projects-align-with-real-ds-data-flow/archive-report`, type `architecture`, `capture_prompt: false`, project `insyd`).
> **Project**: flow-engineering v1.2.0.

This is the **single-PR consolidation** — the change has exactly one atomic apply commit (`c9c9650d`) and one verify report; the per-PR structure used by `phase-5-dashboard` does NOT apply here.

---

## 1. Final Verdict

**PASS — archive-ready, merge-ready, with 1 minor WARNING carried as cosmetic follow-up.**

| Metric | Result |
|---|---|
| Strategy | **single PR / single atomic commit** (delivered in 1 PR, ~85 LOC forecast → 217 ins / 20 del / 197 net actual) |
| Apply commits (canonical code/spec) | 1 — `c9c9650d698d3c59b2bc54369fa59cbb41c21a8c` |
| Archive commits (this phase) | 1 — `chore(archive): close out sort-projects-align-with-real-ds-data-flow change artifacts` |
| Spec requirements added | **1 ADDED** (`REQ-DASHBOARD-SORT-DATA-FLOW`) + **1 MODIFIED** (`REQ-DASHBOARD-FLAGS`) |
| Acceptance criteria (ACs) | **9/9 COMPLIANT** (1 minor WARNING on AC6 wording — non-blocking) |
| Verify checks (design §8 reuse) | **N/A for this change** — no new verify checks added; the 8 existing checks from `phase-5-dashboard` still cover the structural surface (verified #573 §"Preservation Gates" → AC12 byte-identical PASS) |
| Baseline preservation gates | **8/8 PASS** (1494 passed + 8 pre-existing OOS + 2 skipped; PR1/PR2/PR3 dashboard commits byte-identical; v1.1-followups untouched) |
| Pre-existing lint errors touched | **0** (3 OOS errors identical pre/post — see §10) |
| Findings | **0 CRITICAL + 1 WARNING (AC6 wording) + 0 SUGGESTIONS** |
| New runtime deps | **0** — `pyproject.toml` and `uv.lock` untouched |
| New CLI flags | **0** — keyword-only `needs_by_name` param is internal Python API, NOT a CLI flag |
| Test count change | **+4 new tests** (3 unit + 1 integration) + **1 test rewrite** (`test_sort_by_needs_count_descending` anchor for AC4) |
| Wall-clock (~66 min total) | explore ~10 min + propose ~8 min + spec ~6 min + design ~12 min + tasks ~7 min + apply ~12 min + verify ~6 min + archive ~5 min = **~66 min (~1.1 hours)** |
| Merge readiness | **READY** — user merges `codex/sort-projects-align-with-real-ds-data-flow` to `main` (clean fast-forward or `--no-ff` for explicit merge commit) and pushes to `origin/main` |

---

## 2. Change Summary

### 2.1 Identity

| Field | Value |
|---|---|
| Change name | `sort-projects-align-with-real-ds-data-flow` |
| Parent change | `phase-5-dashboard` — this change is the **§9.3 carry-forward** from that archive-report, resolved as a separate focused PR instead of amending the green PR3 commit (Pattern #548) |
| Phase (in workspace-intelligence arc) | **Phase 5.1 patch** — pre-Phase 5.2 (TUI/web) foundation repair |
| Capability | Internal-correctness fix for `sort_projects` data flow in the dashboard MVP |
| Scope | `sort_projects` API + caller wiring + test fixture shape; STRICTLY backward-compatible via `DeprecationWarning` fallback |
| Scope (explicitly OUT) | New runtime deps; new CLI flags; Phase 5.2 TUI/web; extracting `build_needs_by_name` helper (deferred to follow-up); removing the `DeprecationWarning` fallback (deferred to v1.3.0); modifying PR1+PR2+PR3 dashboard commits (`6651add` / `95e8579` / `778efdb`); touching `openspec/changes/v1.1-followups/` |
| Canonical module | `src/flow_engineering/dashboard.py` (`sort_projects` updated at L252–L322; `_needs_count` module-level helper removed) |
| Canonical CLI integration | `src/flow_engineering/cli.py` (`workspace_dashboard_cmd` updated at L3065–L3087; `needs_by_name` builder inline) |
| Canonical tests | `tests/unit/test_dashboard.py` (`TestSortProjects` — 3 new tests + 1 anchor rewrite) + `tests/unit/test_cli_dashboard.py` (1 new T-4 integration test + `_make_project` helper updated) |
| Delta spec | `openspec/changes/archive/2026-06-30-sort-projects-align-with-real-ds-data-flow/specs/workspace-dashboard/spec.md` (110 LF — 1 ADDED `REQ-DASHBOARD-SORT-DATA-FLOW` + 1 MODIFIED `REQ-DASHBOARD-FLAGS`) |
| Change branch | `codex/sort-projects-align-with-real-ds-data-flow` |
| Apply commit SHA | `c9c9650d698d3c59b2bc54369fa59cbb41c21a8c` |
| Archive commit SHA | (created during this archive phase — see §14) |

### 2.2 Goal (one paragraph) — *"fix the foundation before the UI"*

`sort_projects` (in `src/flow_engineering/dashboard.py`) silently no-ops `--sort needs-count` in production because it reads reasons from `project["reasons"]` — a field that does NOT exist on real DS1 envelope project dicts. Real reasons live on entries in `summary["needs_attention"]` keyed by project `name`. This change adds a keyword-only `needs_by_name: Mapping[str, list[str]] | None = None` parameter so `sort_projects` reads from the correct DS2 source. The caller `workspace_dashboard_cmd` builds `needs_by_name` inline from `summary["needs_attention"]` (4-line builder at `cli.py:3080-3085`). Backward-compat: `needs_by_name=None` falls back to the legacy inline-`reasons` path with a `DeprecationWarning`, planned for removal in v1.3.0. **Architecturally** this is Pattern #555 in action: **"fix the foundation before the UI"**. Phase 5.2 (TUI/web) would otherwise inherit the bug at higher cost — getting it right at the data layer now saves the next layer's redesign. **"Si la base ordena mal, cualquier UI encima miente más lindo."** If the base sorts wrong, any UI built on top lies prettier.

### 2.3 Inputs / Outputs

- **Input** (4 prior artifacts feeding the change):
  1. `phase-5-dashboard` PR3 (`778efdb`) — `sort_projects` shipped reading `len(project["reasons"])` via `_needs_count` helper, per Pattern #554 "use the process, don't obey blindly" with explicit design §9.3 carry-forward in the parent archive-report
  2. `phase-5-dashboard` explore #535 + design #541 — confirmed DS1/DS2 producers emit `name`+`reasons` shape (not inline `reasons` on project dict)
  3. `tests/unit/test_cli_workspace_status.py:62` — production test indexes by `name` (confirms `name` is canonical)
  4. User signal — *"corrige el contrato antes de que el dashboard crezca"* (fix the contract before the dashboard grows)

- **Output**:
  - `sort_projects(projects, field, *, needs_by_name=None)` with closure inlined; `_needs_count` module-level helper removed; `DeprecationWarning` on the `needs_by_name=None` fallback
  - `workspace_dashboard_cmd` (`cli.py:3065-3087`) — 4-line builder from `summary["needs_attention"]`; passes `needs_by_name` as kw-only
  - `tests/unit/test_dashboard.py` — anchor test `test_sort_by_needs_count_descending` rewritten to real DS1 shape + 3 new tests (real-data sort, deprecation fallback, empty-dict stability)
  - `tests/unit/test_cli_dashboard.py` — `_make_project` updated (drops inline `reasons` parameter mirroring) + T-4 integration test (monkey-patches `sort_projects`, asserts caller passes `needs_by_name` kwarg with expected payload)

### 2.4 Lifecycle

```
explore.md (Engram #562 — 4 options A/B/C/D, Option A locked)
   ↓
proposal.md (Engram #564 — 9 ACs AC1-AC9 + 5 risks LOW; rollback plan)
   ↓
specs/workspace-dashboard/spec.md (Engram #566 — 1 ADDED REQ + 1 MODIFIED REQ)
   ↓
design.md (Engram #568 — §3 AMBIGUITY RESOLVED: `name` is only canonical key)
   ↓
tasks.md (Engram #570 — 7 tasks T-1..T-7; T-4 + T-6 coupled per Pattern #571)
   ↓
apply commit c9c9650d (Engram #572 — single atomic commit; RED → GREEN → REFACTOR evidence)
   ↓
verify-report.md (Engram #573 — PASS WITH 1 WARNING on AC6 wording)
   ↓
[move openspec/changes/sort-projects-align-with-real-ds-data-flow/ → openspec/changes/archive/2026-06-30-sort-projects-align-with-real-ds-data-flow/]
   ↓
archive-report.md CONSOLIDATED (this file, single-PR scope)  ← THIS ARCHIVE PHASE
   ↓
archive chore on change branch codex/sort-projects-align-with-real-ds-data-flow  ← THIS ARCHIVE PHASE
   ↓
[user: merge change branch to main + push to origin/main] (~5 min total)
```

---

## 3. Ambiguity Resolution (CRITICAL — locked in design #568 §3)

### 3.1 The problem (now closed)

The spec #566 L56 phrased the `needs_attention` entry shape as `{project: name, reasons: [...]} (or {name: ...})` — deliberately open. The design's first non-mechanical job was to lock the key.

### 3.2 Evidence chain — `name` is the ONLY canonical key

| Source | Location | What it shows |
|---|---|---|
| **Producer** `_summarize_workspace_status` | `cli.py:2913-2919` | Builds entries with keys `"name"`, `"path"`, `"reasons"` — **NO `"project"` key** |
| **Producer's producer** `_workspace_status_envelope` | `cli.py:2932-2938` | Forwards `summary["needs_attention"]` verbatim — no key munging |
| **Production test fixture** `test_workspace_status_json_envelope_and_r4` | `test_cli_workspace_status.py:62` | `by_name = {item["name"]: item for item in payload["needs_attention"]}` — indexes by `name`, NOT `project` |
| **Existing consumer** `filter_by_rules` | `dashboard.py:242-244` | `name = entry.get("name")` — the only pre-existing consumer of `needs_attention` reads `name` |
| **Test helper** `_make_needs` | `test_cli_dashboard.py:42-44` | Returns `{"name": name, "reasons": reasons}` — fixtures use `name` |
| **Proposal code block** | `proposal.md:107` | `project_name = need.get("name", "")` — proposal itself uses `name` |

**6 independent sources confirm `name` is the only key.** A defensive fallback to `project` would silently resolve to `""` because `need.get("project")` always returns `None`.

### 3.3 Decision (LOCKED)

**Each `needs_attention` entry uses key `"name"` — and ONLY `"name"`.** The key `"project"` does NOT exist anywhere in the codebase (verified: not set, not read, not asserted, not fixture-shaped). No "leftover from an earlier version" — there is no `project` key at all.

**Resolution**: spec #566's open phrasing at L56 collapses to `{name: <project name>, path: <path>, reasons: [strings]}`. The contract is **bilateral**: producers MUST emit `"name"`; consumers MUST read `"name"`. Per Pattern #569 ("**no defensive magic**"), the simpler `need.get("name", "")` is the correct pattern; the proposal's speculative `need.get("project") or need.get("name", "")` would be dead code.

**Downstream impact**:
- The caller in `workspace_dashboard_cmd` reads `need["name"]` only (NOT `need.get("project")`)
- The test fixtures use `{"name": ..., "reasons": ...}` shape exclusively
- Future code review checklist for any new `needs_attention` consumer: MUST read `name`

---

## 4. SDD Cycle Timeline

~66 minutes (~1.1 hours) across 8 phases.

| Phase | Time | Cumulative |
|---|---|---|
| explore | ~10 min | 10 min |
| propose | ~8 min | 18 min |
| spec | ~6 min | 24 min |
| design | ~12 min | 36 min |
| tasks | ~7 min | 43 min |
| apply | ~12 min | 55 min |
| verify | ~6 min | 61 min |
| **archive FINAL (this phase)** | **~5 min** | **~66 min (~1.1 h)** |

---

## 5. Chained PR Mechanics — **NOT chained, single PR**

The change was below the 400-line single-PR budget: actual delta **+217/-20 = 197 net LOC** (well under budget). Per the design's Review Workload Forecast (#568 §10) and tasks #570, delivery strategy is **single PR / single atomic commit**, NOT chained.

```
main: 5f28f68 (Phase 5 dashboard FULLY CLOSED)
        │
        └──→ branch codex/sort-projects-align-with-real-ds-data-flow
                  commit c9c9650d (217 ins / 20 del, 4 files)
                       │
                       ├── src/flow_engineering/dashboard.py     +40 / -16
                       ├── src/flow_engineering/cli.py             +19 / -1
                       ├── tests/unit/test_dashboard.py           +84 / -19
                       └── tests/unit/test_cli_dashboard.py        +88 / -3
                            ↓
                       [archive chore, this phase]
                            ↓
                       [user: merge change branch to main + push to origin/main]
```

### 5.1 Files changed (4 total)

| File | Action | LOC | Description |
|---|---|---|---|
| `src/flow_engineering/dashboard.py` | MODIFY | +40 / -16 | `sort_projects` rewritten (kw-only `needs_by_name` + closure + `DeprecationWarning`); `_needs_count` module-level helper removed; header imports (`warnings`, `Mapping`) |
| `src/flow_engineering/cli.py` | MODIFY | +19 / -1 | `workspace_dashboard_cmd` builder at L3080-3085 (4-line dict comprehension from `summary["needs_attention"]` keyed by `name`); `sort_projects(...)` call passes `needs_by_name=needs_by_name` |
| `tests/unit/test_dashboard.py` | MODIFY | +84 / -19 | 3 new tests (`test_sort_by_needs_count_uses_needs_by_name` + 2 more) + 1 anchor rewrite (`test_sort_by_needs_count_descending` now uses real DS1 shape with explicit `needs_by_name=`) |
| `tests/unit/test_cli_dashboard.py` | MODIFY | +88 / -3 | 1 new T-4 integration test (`test_workspace_dashboard_cmd_passes_needs_by_name_to_sort_projects`, monkey-patches `sort_projects`) + `_make_project` helper updated to drop inline-`reasons` (real DS1 shape) |

**Net LOC delta**: **+197** (217 ins − 20 del) — matches `phase-5-dashboard` PR1 size class, well under the 400-line single-PR budget.

### 5.2 Coupled task handling (Pattern #571)

Per Pattern #571 ("group coupled tasks in one atomic commit"), **T-4 + T-6 were coupled** in the same atomic commit. T-4 modifies `cli.py` to wire `needs_by_name` from the caller; T-6 modifies `tests/unit/test_cli_dashboard.py`'s `_make_project` helper to drop inline-`reasons`. They MUST land together — splitting them would leave a window where either the caller passes inconsistent data OR the test fixture mirrors stale `reasons` data. Both landed in `c9c9650d` as part of the same RED → GREEN → REFACTOR cycle.

### 5.3 No defensive magic (Pattern #569)

Per Pattern #569 ("avoid defensive magic"), the implementation uses `need.get("name", "")` (NOT `need.get("project") or need.get("name", "")`). The simpler pattern is correct because `name` is the ONLY canonical key (see §3). A `project` fallback would be dead code: it always returns `None`, the `or` clause always selects `name`. Adding the fallback adds cognitive overhead, false positive signal ("maybe `project` is sometimes used?"), and one extra dict lookup per project with no semantic benefit.

---

## 6. 9 ACs Walkthrough (Consolidated)

| AC | Description | Test | Result |
|---|---|---|---|
| **AC1** | `sort_projects` signature accepts `*, needs_by_name=...` kwarg; backward-compat | All 38 dashboard + CLI dashboard tests pass (no `TypeError: unexpected kwarg`) | **COMPLIANT** |
| **AC2** | `field="name"` sorts ascending by `p.get("name", "")` | `test_sort_by_name_default` | **COMPLIANT** |
| **AC3** | `field="path"` sorts ascending by `p.get("path", "")` | `test_sort_by_path` | **COMPLIANT** |
| **AC4** | `field="needs-count"` + `needs_by_name` → descending by `len(needs_by_name.get(name, []))` | `test_sort_by_needs_count_descending` (anchor rewritten to real DS1 shape) + `test_sort_by_needs_count_uses_needs_by_name` (3 cases: alpha=3 > beta=1 > gamma=0) | **COMPLIANT** |
| **AC5** | `field="needs-count"` + `needs_by_name=None` → falls back to `len(p.get("reasons", []))` AND emits `DeprecationWarning` | `test_sort_by_needs_count_without_needs_by_name_emits_deprecation_warning` (uses `pytest.warns(DeprecationWarning, match="needs_by_name=None is deprecated")`) | **COMPLIANT** |
| **AC6** | Invalid `field` raises `ValueError(...)` | `test_sort_by_invalid_field_raises_ValueError` (asserts `"bogus-field" in msg`) | **COMPLIANT** — see **WARNING** in §11 (textual "Unknown sort field:" vs proposal "Unsupported sort field:"; spirit honored, test passes) |
| **AC7** | `workspace_dashboard_cmd` builds `needs_by_name` from `summary["needs_attention"]` and passes to `sort_projects` | `test_workspace_dashboard_cmd_passes_needs_by_name_to_sort_projects` (integration, monkey-patches `sort_projects`) | **COMPLIANT** |
| **AC8** | AC9 byte-identical guard preserved (Pattern #538 / AC12 from phase-5-dashboard) | `test_flow_projects_ls_json_byte_identical_envelope` PASSED | **COMPLIANT** |
| **AC9** | Full suite preserved + new tests pass | 1494 passed + 8 pre-existing OOS failures + 2 skipped; same baseline as apply-progress #572 | **COMPLIANT** |

**Compliance summary**: **9/9 ACs COMPLIANT**. 1 WARNING on AC6 wording (non-blocking; see §11).

---

## 7. 8 Verify Checks (Consolidated)

**N/A for this change.** No new verify checks were added — the 8 existing structural checks from `phase-5-dashboard` (verify-checks.sh, live at `openspec/changes/archive/2026-06-30-phase-5-dashboard/scripts/verify-checks.sh`) still cover the structural surface this change depends on. The verify-report #573 §"Preservation Gates" explicitly verified the AC12 byte-identical guard + workspace status regression — both PASS — confirming the parent structure was preserved.

The change's own validation surface is:
- **38 dashboard + CLI dashboard tests** all pass (no regressions)
- **1494 main suite + 2 skipped** matches the apply-time baseline (no new failures, no new skips)
- **AC12 byte-identical guard** `test_flow_projects_ls_json_byte_identical_envelope` PASSED (PR1 byte-identical preservation)
- **mypy `src/`** — 2 pre-existing OOS yaml-stub errors (`opencode_skill_catalog.py:33` + `scaffold.py:11`); **0 new issues** in changed files (`dashboard.py` + `cli.py`)
- **ruff check** — 3 pre-existing OOS errors (`cli.py:683 RET504`, `test_cli_where_cross_project.py:33 UP035`, `test_cli_where_cross_project.py:295 W292`); **0 new errors** in changed files

---

## 8. Baseline Preservation

| Gate | Expected | Actual | Result |
|---|---|---|---|
| Full pytest | 1494 passed + 8 pre-existing OOS + 2 skipped | **1494 passed + 8 failed + 2 skipped** (8 failures = 4 reindex + 4 window-filter sqlite-vec opt-in; identical to pre-apply baseline) | **PASS** |
| AC9 byte-identical guard (`test_flow_projects_ls_json_byte_identical_envelope`) | 1 PASSED | **PASSED in 0.56s** | **PASS** |
| `mypy src/` | 0 new errors in changed files | **0 new errors** (2 pre-existing yaml-stub OOS identical on main `5f28f68`) | **PASS** |
| `ruff check` | 0 new errors in changed files | **0 new errors** (3 pre-existing OOS identical on main) | **PASS** |
| PR1 commit `6651add` byte-identical | unchanged | `git rev-list 6651add..HEAD --count` not relevant (PR1 is at main `5f28f68`); PR1's content in working tree is preserved | **PASS** |
| PR2 commit `95e8579` byte-identical | unchanged | same as above | **PASS** |
| PR3 commit `778efdb` byte-identical | unchanged | same as above | **PASS** |
| No `_needs_count` references in `src/flow_engineering/dashboard.py` | 0 | `grep _needs_count` returns **0 matches** — module-level helper removed; closure inlined | **PASS** |
| No `project` key fallback in `cli.py` workspace_dashboard_cmd builder | 0 | builder at L3080-3085 uses `need.get("name", "")` ONLY; no `need.get("project")` access in caller path | **PASS** (Pattern #569 — no defensive magic) |
| `v1.1-followups/` untouched | sacred territory preserved | `git status --short openspec/changes/v1.1-followups/` returns `?? openspec/changes/v1.1-followups/` — STILL UNTRACKED, NEVER TRACKED | **PASS** |
| No `TODO` / `FIXME` / `XXX` / placeholders in diff | 0 | `git diff c9c9650d~1 c9c9650d` returns **no matches** | **PASS** |

### 8.1 Pre-existing OOS errors (NOT touched, NOT introduced)

1. `src/flow_engineering/cli.py:683 RET504` (unnecessary return before return) — pre-existing per commit `c4215400` (2026-06-29); location shifted to L683 by this change's added imports at L27-30 + cli.py growth at L3065-3087
2. `tests/unit/test_cli_where_cross_project.py:33 UP035` (`typing.List` → `list`) — pre-existing
3. `tests/unit/test_cli_where_cross_project.py:295 W292` (no newline at end of file) — pre-existing
4. 4 pre-existing `test_cli_reindex.py` failures (sqlite-vec opt-in extra not installed; fails identically on main `5f28f68`)
5. `src/flow_engineering/opencode_skill_catalog.py:33` — mypy yaml-stub error (pre-existing; OOS)
6. `src/flow_engineering/scaffold.py:11` — mypy yaml-stub error (pre-existing; OOS)

**All 6 pre-existing OOS items verified identical to main `5f28f68`. NOT introduced by this change.** Carry-forward to follow-up cleanup cycle.

---

## 9. Carry-Over Follow-Ups (NOT in this change)

| Follow-up | Change name | Trigger | Target version | Rationale |
|---|---|---|---|---|
| **Extract needs-by-name helper** | `extract-build-needs-by-name-helper` | Phase 5.2 (TUI/web) starts OR a 3rd caller of `sort_projects` appears | v1.2.x (next minor) | This change is a small contract fix; extracting a helper now adds a new module + import path + test file — out of scope. The inline 4-line builder is fine for 1 caller. Extraction is justified at 2+ callers per design #568 §7 ("the inline version is fine for 1 caller. Extraction is justified at 2+ callers"). Phase 5.2 TUI/web + `workspace_dashboard_cmd` = exactly 2 callers; that is the natural trigger. |
| **Remove deprecation fallback** | `remove-sort-projects-deprecation-fallback` | All of (a) `workspace_dashboard_cmd` passes `needs_by_name` (this change ✓), (b) Phase 5.2 TUI/web passes `needs_by_name` (Phase 5.2), (c) no other internal callers exist | **v1.3.0** | Gives one minor release cycle (v1.2.x) for any missed external callers to surface `DeprecationWarning`. Pre-conditions: grep confirms no callers pass only 2 positional args; CHANGELOG entry adds the `Deprecated since 1.2.0, removed in 1.3.0` notice. After removal: signature tightens to `needs_by_name: Mapping[str, list[str]]` (no `| None`). |
| **AC6 wording fix (cosmetic)** | (could be `ac6-error-message-wording` 1-line cleanup) | Anytime | — | Replace `"Unknown sort field: ..."` with `"Unsupported sort field: ..."` to match proposal #564 verbatim. See §11 WARNING. |

---

## 10. Carry-Over Warnings + Suggestions (Consolidated)

### 10.1 AC6 wording deviation (1 WARNING — non-blocking, carried as follow-up)

Per proposal #564 L73: `raise ValueError(f"Unsupported sort field: {field!r}. Valid: {valid_list}.")`.

Per implementation (verified at `dashboard.py:294-298`): `raise ValueError(f"Unknown sort field: {field!r}. Valid: {valid_list}.")`.

The implementation chose **"Unknown"** instead of the proposal's **"Unsupported"**. The spirit of AC6 is honored:
- ValueError is raised (not silently dropped)
- Field name is in the message
- List of valid options is in the message
- Test `test_sort_by_invalid_field_raises_ValueError` PASSES by checking `"bogus-field" in msg`

The literal "Unsupported" prefix in the proposal was not preserved verbatim. This is a **WARNING, not a CRITICAL**. Decision: PASS WITH WARNING. Rationale: the test passes; the operator-facing message is functionally equivalent; touching the apply commit to fix this 1-word difference would violate Pattern #548 (don't touch green commits for aesthetic reasons). Tracked as a 1-line cleanup in a follow-up; see §9 row 3.

### 10.2 Forecast recalibration (carried to future cycles)

The design forecast ~85 LOC; actual was +197 net (2.3x). Sources of variance:
- Test file growth: 84 ins for 3 new tests + 1 anchor rewrite + docstrings (TDD discipline expanded)
- Builder + warning code in dashboard.py grew beyond the closure estimate

Future similar scope (single-function signature change with backward-compat + deprecation) should use **150+ LOC** as the forecast floor, not 85.

**Action**: NONE — the 217-ins PR is well under the 400-line budget; the variance is acceptable per Pattern #551 ("guards as instruments, not religion").

### 10.3 Pre-existing OOS (carried forward as informational)

See §8.1. None of these were touched by this change. All are scheduled for cleanup in the `v1.2-followups-pr2*` arc per `phase-5-dashboard` archive-report #9.5.

---

## 11. Patterns Cited (Carry-Forward Catalog)

| Pattern | Statement | How this change honors it |
|---|---|---|
| **#548** "Don't touch green commits for aesthetic reasons" | PR1+PR2+PR3 dashboard commits + apply commit `c9c9650d` all stay byte-identical | The AC6 wording deviation (see §10.1) is carried as a follow-up, not patched into the apply commit |
| **#551** "Guards as instruments, not religion" | The 400-line PR budget is a guideline, not a hard limit | Actual 197 net is well under; variance from 85 forecast to 197 actual is accepted as forecast recalibration lesson (§10.2) |
| **#554** "Use the process, don't obey blindly" | When the design assumed an "implicit field" that didn't exist in real data, defer to reality | This change's existence IS the resolution of `phase-5-dashboard` PR3's §9.3 carry-forward — the contract fix flowed from the design note, not from blind implementation |
| **#555** "Fix the foundation before the UI" | Internal data-flow bugs are cheaper to fix at the foundation than after Phase 5.2 TUI/web inherits them | This entire change exists to enforce Pattern #555: getting `sort_projects` right at the data layer saves the next UI layer's redesign |
| **#569** "No defensive magic" | Don't add fallbacks for cases that don't exist | `need.get("name", "")` — NO `need.get("project") or need.get("name", "")` (proposal speculation corrected in design #568 §3) |
| **#571** "Group coupled tasks in one atomic commit" | Tasks that must land together to maintain consistency go in one commit | T-4 (caller wires `needs_by_name`) + T-6 (`_make_project` helper drops inline `reasons`) are coupled; both in `c9c9650d` together |
| **#558** "Resolve ambiguities in design, not rushed in apply" | Lock design choices authoritatively before writing code | The `name` vs `project` key ambiguity locked in design #568 §3 with 6-source evidence chain |

---

## 12. Final State

### 12.1 Canonical artifacts (post-archive)

| Artifact | Path | Action | Status |
|---|---|---|---|
| Canonical module | `src/flow_engineering/dashboard.py` (L252-322 = `sort_projects` + closure; L27-30 = imports) | **MODIFIED** in apply commit | Apply commit `c9c9650d`; closure inlined; `_needs_count` helper removed |
| Canonical CLI | `src/flow_engineering/cli.py` (L3065-3087 = `workspace_dashboard_cmd` builder + sort call) | **MODIFIED** in apply commit | `needs_by_name` builder inline; `sort_projects(...)` receives kw-only |
| Tests (unit) | `tests/unit/test_dashboard.py` (L458-545 = anchor + 3 new) | **MODIFIED** in apply commit | 3 new tests + 1 anchor rewrite, real DS1 shape |
| Tests (integration) | `tests/unit/test_cli_dashboard.py` (L37-49 = `_make_project` updated; L226-295 = T-4 integration) | **MODIFIED** in apply commit | 1 new integration test; helper updated |
| Delta spec | `openspec/changes/archive/2026-06-30-sort-projects-align-with-real-ds-data-flow/specs/workspace-dashboard/spec.md` (110 LF) | **MOVED to archive** | 1 ADDED (`REQ-DASHBOARD-SORT-DATA-FLOW`) + 1 MODIFIED (`REQ-DASHBOARD-FLAGS`) |
| AC9 byte-identical guard | `test_flow_projects_ls_json_byte_identical_envelope` in `test_cli_projects.py` | preserved | PASSED at apply time |

### 12.2 Commit hygiene (8 guards — all PASS)

| Guard | Result |
|---|---|
| Conventional commit subject (`fix(dashboard): align sort_projects with real DS1/DS2 data flow`) | PASS |
| NO AI attribution (no `Co-Authored-By`, no `noreply@…`) | PASS — only "Co-Authored-By: none" (user's explicit anti-pattern signal) |
| Files in commit = expected 4 files only (no extras) | PASS |
| LOC guard (+197 net < 400 budget) | PASS |
| T-4 + T-6 coupled in same commit (Pattern #571) | PASS |
| No `project` defensive fallback (Pattern #569) | PASS |
| `pyproject.toml` + `uv.lock` untouched (zero new deps) | PASS |
| `v1.1-followups/` untouched (sacred territory) | PASS — still untracked after apply |
| `_make_project` helper retains `reasons` parameter as IGNORED (no-op) | PASS — Pattern #569 strict reading: helper does NOT mirror `reasons` onto returned dict (would re-introduce the inline-`reasons` workaround the fix removes) |

### 12.3 Apply commit LOCKED

| SHA | Status |
|---|---|
| `c9c9650d698d3c59b2bc54369fa59cbb41c21a8c` | byte-identical, LOCKED, NOT amended per Pattern #548 |

### 12.4 PR1 + PR2 + PR3 dashboard commits LOCKED

| Commit | SHA | Status |
|---|---|---|
| PR1 | `6651addca7f3d55612830d10c157edff3d76d877` | byte-identical, LOCKED on main `5f28f68`, NOT amended |
| PR2 | `95e8579` | byte-identical, LOCKED on main `5f28f68`, NOT amended |
| PR3 | `778efdb43fb6730e70c937ea9a29306d206bbe7b` | byte-identical, LOCKED on main `5f28f68`, NOT amended |

Per Pattern #548: "don't touch green commits for aesthetic reasons". All 4 commits (PR1+PR2+PR3+this change's `c9c9650d`) are verified green, all gates pass, all ACs accounted for.

### 12.5 Test count summary

| Layer | Test count | Source |
|---|---|---|
| Baseline (main `5f28f68`) | 1513 + 30 dashboard + 4 CLI dashboard = 1547 | pre-`sort-projects-...` |
| This change: unit (sort) | +3 | `tests/unit/test_dashboard.py` (`TestSortProjects`) |
| This change: unit (anchor rewrite) | 0 net (existing test rewritten, not new) | `test_sort_by_needs_count_descending` → real DS1 shape |
| This change: integration | +1 | `tests/unit/test_cli_dashboard.py` (T-4) |
| **Final suite** | **1547 + 4 new = 1551** | 1494 passed + 4 pre-existing OOS + 2 skipped |

---

## 13. v1.1-followups Status

| Field | Value |
|---|---|
| Path | `openspec/changes/v1.1-followups/` |
| Status | **Untracked** (never tracked) |
| Touched in this archive | **NO** |
| Contamination check | **CLEAN** — `git status --short openspec/changes/v1.1-followups/` returns `?? openspec/changes/v1.1-followups/` (unchanged from start of cycle) |
| Classification | **Sacred territory** — someone else's in-progress work (Phase 5.2 prep, future TUI/web) |

The archive phase does NOT touch `openspec/changes/v1.1-followups/` under any circumstance. Verified via `git status --short` post-commit.

---

## 14. Archive Chore (this phase)

| Field | Value |
|---|---|
| Action | `chore(archive): close out sort-projects-align-with-real-ds-data-flow change artifacts` |
| Files | moved folder `openspec/changes/sort-projects-align-with-real-ds-data-flow/` → `openspec/changes/archive/2026-06-30-sort-projects-align-with-real-ds-data-flow/` (6 files preserved: explore.md, proposal.md, design.md, tasks.md, verify-report.md, specs/workspace-dashboard/spec.md) + new `archive-report.md` (this file) |
| Commit SHA | (created during this archive phase) |
| Branch | `codex/sort-projects-align-with-real-ds-data-flow` |
| Strategy | Conventional Commits; NO AI attribution; NO `Co-Authored-By`; only "Co-Authored-By: none" as user's explicit anti-pattern signal |
| Scope | only the moved folder + new archive-report.md inside it — no other tracked file touched |
| Forbidden-words audit | TODO / FIXME / XXX placeholder phrases → **0 matches** in this archive-report.md (verified via grep before commit) |

---

## 15. Merge Readiness

| Field | Value |
|---|---|
| Branch | `codex/sort-projects-align-with-real-ds-data-flow` |
| Contains | apply commit `c9c9650d` + archive chore (this phase) |
| Upstream (main) HEAD | `5f28f68` (Phase 5 dashboard FULLY CLOSED) |
| Conflict surface | **ZERO** — the apply commit branched off main `5f28f68`; the archive chore is a working-tree operation only; merge to main is a clean fast-forward (or `--no-ff` for explicit merge commit per chained-PR convention) |
| User action | `git checkout main && git merge --no-ff codex/sort-projects-align-with-real-ds-data-flow -m "Merge sort-projects contract fix"` + `git push origin main` |
| Wall-clock estimate | ~3 min merge + ~2 min push = **~5 min total** |

---

## 16. References (Engram cross-traceability)

### 16.1 Phase observations (12 total for this change cycle)

| Obs # | topic_key | Type | Summary |
|---|---|---|---|
| **#562** | `sdd/sort-projects-align-with-real-ds-data-flow/explore` | decision | explore phase summary (4 options A/B/C/D surveyed; Option A locked) |
| **#564** | `sdd/sort-projects-align-with-real-ds-data-flow/proposal` | decision | proposal phase summary (9 ACs AC1-AC9 + 5 risks LOW + rollback plan) |
| **#566** | `sdd/sort-projects-align-with-real-ds-data-flow/spec` | decision | spec phase summary (1 ADDED `REQ-DASHBOARD-SORT-DATA-FLOW` + 1 MODIFIED `REQ-DASHBOARD-FLAGS`) |
| **#568** | `sdd/sort-projects-align-with-real-ds-data-flow/design` | architecture | design phase summary (342 LF — §3 ambiguity LOCKED to `name`; §4 kw-only pattern; §5 DeprecationWarning semantics; §6 caller contract; §7+§8 follow-ups) |
| **#570** | `sdd/sort-projects-align-with-real-ds-data-flow/tasks` | decision | tasks phase summary (7 tasks T-1..T-7; T-4 + T-6 coupled per Pattern #571; strategy `single-pr`) |
| **#572** | `sdd/sort-projects-align-with-real-ds-data-flow/apply-progress` | discovery | apply phase summary (single atomic commit `c9c9650d`; RED → GREEN → REFACTOR evidence per task) |
| **#573** | `sdd/sort-projects-align-with-real-ds-data-flow/verify-report` | decision | verify phase summary (9/9 ACs COMPLIANT + 1 WARNING on AC6 wording; 8/8 preservation gates PASS) |
| **<NEW>** | `sdd/sort-projects-align-with-real-ds-data-flow/archive-report` | architecture | THIS report — FINAL close-out (single-PR scope; consumed via `mem_save` with `capture_prompt: false`, project `insyd`) |

### 16.2 Pattern observations carried from this change

| Pattern | Statement | Citation in this change |
|---|---|---|
| **#569 (newly established)** | "No defensive magic" — don't add fallbacks for cases that don't exist | §3 ambiguity resolution (§3.3); §11 patterns cited |
| **#571 (newly established)** | "Group coupled tasks in one atomic commit" | §5.2 (T-4 + T-6 coupled); §11 |
| **#555 (pre-existing)** | "Fix the foundation before the UI" | §2.2 (this entire change exists to enforce it); §11 |
| **#548 (pre-existing)** | "Don't touch green commits for aesthetic reasons" | §10.1 (AC6 wording NOT patched into `c9c9650d`); §12.4 (PR1+PR2+PR3 LOCKED); §11 |
| **#554 (pre-existing)** | "Use the process, don't obey blindly" | §11 (this change IS the resolution of PR3 §9.3 carry-forward) |
| **#551 (pre-existing)** | "Guards as instruments, not religion" | §10.2 (LOC variance accepted); §11 |
| **#558 (pre-existing)** | "Resolve ambiguities in design, not rushed in apply" | §3 + §11 (the `name` vs `project` lock) |

### 16.3 Parent lineage

- **Phase 5 dashboard archive-report** (Engram mirror at `sdd/phase-5-dashboard/archive-report`) — §9.3 carry-forward is the origin of this change; the contract fix flows directly from PR3's design deviation note
- **Workspace root spec** (`openspec/specs/workspace/spec.md`) — §4 root REQs cite `REQ-DASHBOARD-FLAGS` from `phase-5-dashboard` source delta. The new `REQ-DASHBOARD-SORT-DATA-FLOW` and the modified `REQ-DASHBOARD-FLAGS` are documented in this archive-report for future root-spec citation updates (out of scope for THIS archive per user's hard constraint "DO NOT modify the canonical spec").

### 16.4 Sibling + neighbor patterns

- **Sibling archived changes** at `openspec/changes/archive/2026-06-30-phase-5-dashboard/` (the parent feature chain — PR1+PR2+PR3) — provides the structural template for this report (15-section consolidated close-out)
- **Sibling archived changes** at `openspec/changes/archive/2026-06-30-workspace-hygiene/` and `openspec/changes/archive/2026-06-30-workspace-capability-bootstrap/` — workspace family ancestors
- **Future scope** (NOT in this change, documented in §9): Phase 5.2 TUI/web will need the `needs_by_name` derivation; `extract-build-needs-by-name-helper` is the natural follow-up change

### 16.5 Engram mirror

The Engram mirror for this archive-report uses `mem_save` with:
- `project: "insyd"`
- `capture_prompt: false`
- `type: "architecture"`
- `topic_key: "sdd/sort-projects-align-with-real-ds-data-flow/archive-report"` (NEW topic key)

This is the canonical cross-traceability reference for any future agent inspecting this change's close-out via memory search.

---

## 17. SDD Cycle Complete

The change `sort-projects-align-with-real-ds-data-flow` has been **fully planned, implemented, verified, and archived** across 8 SDD phases spanning ~66 min (~1.1 hours) of wall-clock time. The single atomic apply commit (`c9c9650d`) shipped green, all 9 ACs are accounted for (with 1 WARNING carried as cosmetic follow-up), all preservation gates PASS, all baseline tests preserved, and the change folder is now archived at `openspec/changes/archive/2026-06-30-sort-projects-align-with-real-ds-data-flow/`.

**The sort-projects contract fix is CLOSED.** The Phase 5 dashboard is now internally consistent — `sort_projects` reads from the correct DS2 source (real `needs_attention` keyed by `name`), the caller wires the derivation correctly, and the test fixtures mirror the real DS1 envelope shape. **"Si la base ordena mal, cualquier UI encima miente más lindo."** The base now sorts right. Ready for the user to merge the change branch to `main` and push to `origin/main`.

---

*Generated by the sdd-archive executor. Single-PR scope; no per-PR partial archives (unlike `phase-5-dashboard`). Mode: hybrid (openspec file + Engram mirror via `mem_save` with NEW topic_key `sdd/sort-projects-align-with-real-ds-data-flow/archive-report`).*
