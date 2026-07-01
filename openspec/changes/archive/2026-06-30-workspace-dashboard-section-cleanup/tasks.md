# Tasks: workspace-dashboard-section-cleanup

> **Phase**: tasks (5th of 8)
> **Change**: `workspace-dashboard-section-cleanup`
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Strict TDD**: OFF (doc-only; no test code)
> **Design philosophy**: "limpiar lo prometido, nada más" (Pattern #582)

---

## 1. Header

| Field | Value |
|-------|-------|
| Change | `workspace-dashboard-section-cleanup` |
| Phase | tasks (5th of 8) |
| Strict TDD | OFF (doc-only; no test code) |
| Inputs | design #583 (4 components) ← spec #581 (4 text edits) ← proposal #579 ← explore #577 |
| Output | `tasks.md` — 8 mechanical tasks (T-1 to T-8); push EXCLUDED |
| Files touched (apply) | 1 (`openspec/specs/workspace/spec.md`) |
| Net LOC | ~17 lines (8 insertions / 9 deletions) |
| Forecast | ~5 min wall-time for this phase; ~20 min for apply+verify+archive cycle |

---

## 2. Review Workload Forecast

```yaml
forecast_loc: ~17
forecast_workspace_spec_md: ~17
forecast_total_loc: ~17
chained_pr_recommendation: no
chained_pr_rationale: "Single PR, ~17 LOC well under 400-line single-PR budget"
400_line_budget_risk: low
size_exception_required: no
size_exception_rationale: null
decision_needed_before_apply: no
decision_question: null
```

**Decision needed before apply**: No
**Chained PRs recommended**: No
**Chain strategy**: N/A (single PR)
**400-line budget risk**: Low

---

## 3. Task Summary Table

| T# | Title | Action type | Verifies |
|----|-------|-------------|----------|
| T-1 | Apply L73 §3 intro edit | text edit | AC2 |
| T-2 | Apply L80 §3 row 5 edit | text edit | AC1 |
| T-3 | Apply L317 §5 row edit | text edit | AC3 |
| T-4 | Apply L360 §7 row REMOVE + renumber | text edit (REMOVE+renumber) | AC4 |
| T-5 | Preservation gates verification (after 4 edits, before commit) | gate-check | 12 preservation gates |
| T-6 | Single atomic commit | git commit | T-1..T-4 atomicity |
| T-7 | Post-commit verify (after T-6 commit, before T-8 archive) | gate-check | 4 ACs + 12 preservation gates |
| T-8 | Archive (single-PR archive, not chained) | filesystem move + chore commit | change folder → `archive/2026-06-30-.../` |

---

## 4. Task Definitions

### T-1 — Apply L73 §3 intro edit

| Field | Value |
|-------|-------|
| **Goal** | Update §3 intro from "3 confirmed sub-capabilities + 1 placeholder" to "4 confirmed sub-capabilities" so the intro count matches the post-L80 row 5 state (shipped). |
| **RED step** | `grep -F "3 confirmed sub-capabilities + 1 placeholder" openspec/specs/workspace/spec.md` → expect FOUND (pre-edit state). |
| **GREEN step** | Edit L73: replace `The workspace family has **3 confirmed sub-capabilities + 1 placeholder**:` with `The workspace family has **4 confirmed sub-capabilities**:`. Use Edit tool with exact oldString/newString. |
| **REFACTOR step** | `grep -F "4 confirmed sub-capabilities" openspec/specs/workspace/spec.md` → expect FOUND at L73. `grep -F "3 confirmed sub-capabilities + 1 placeholder" openspec/specs/workspace/spec.md` → expect NOT FOUND. |
| **Files affected** | `openspec/specs/workspace/spec.md` (L73, 1 line) |
| **Pre-requisites** | None (independent edit). |
| **Acceptance criteria** | AC2 (L73 intro updated). |
| **Risk notes** | Coupled 1-line tweak to L80; without this edit, §3 intro count diverges from §3 row count (internally inconsistent). |

### T-2 — Apply L80 §3 row 5 edit

| Field | Value |
|-------|-------|
| **Goal** | Update §3 row 5 from `(future)` / `(placeholder)` / `TBD` placeholder row to shipped `phase-5-dashboard` reference + 3 flags + no `--json` + archive path. |
| **RED step** | `grep -F "5 (future) | workspace-dashboard" openspec/specs/workspace/spec.md` → expect FOUND (pre-edit placeholder row). |
| **GREEN step** | Edit L80: replace the entire row with the shipped-state row per design #583 §2.2: `\| 5 \| workspace-dashboard \| flow workspace dashboard \| Visualization — read-only Rich MVP for human operators; supports --filter RULES, --sort FIELD, --no-color (no --json — Pattern #538) \| ✅ Shipped + archived at phase-5-dashboard \| openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md \|`. Use Edit tool with the full row as oldString and the replacement row as newString. |
| **REFACTOR step** | `grep -F "✅ Shipped + archived at phase-5-dashboard" openspec/specs/workspace/spec.md` → expect FOUND at L80. `grep -F "flow workspace tui / web" openspec/specs/workspace/spec.md` → expect NOT FOUND (placeholder removed). `grep -F "Visualization — TBD" openspec/specs/workspace/spec.md` → expect NOT FOUND. |
| **Files affected** | `openspec/specs/workspace/spec.md` (L80, 1 row in §3 table) |
| **Pre-requisites** | T-1 recommended (coupled intro), but T-2 itself is independent. |
| **Acceptance criteria** | AC1 (L80 row 5 updated to reference shipped `phase-5-dashboard` with all 3 flags, no `--json`, archive path). |
| **Risk notes** | Markdown table column alignment cosmetic (mitigated: replacement text matches existing column widths from Phase 1/3/4 rows per proposal R2). |

### T-3 — Apply L317 §5 row edit

| Field | Value |
|-------|-------|
| **Goal** | Update §5 row from `flow workspace tui (future) / (placeholder)` to `flow workspace dashboard` + 3 flags (`--filter RULES`, `--sort FIELD`, `--no-color`) + no `--json` per Pattern #538. |
| **RED step** | `grep -F "flow workspace tui (future)" openspec/specs/workspace/spec.md` → expect FOUND (pre-edit stale row). |
| **GREEN step** | Edit L317: replace the entire row with the shipped-state row per design #583 §2.3: `\| flow workspace dashboard \| [--filter RULES] [--sort FIELD] [--no-color] (Phase 5) \| 5 \| Read-only Rich MVP (A header + B needs-attention + C archived + D footer); no --json (Pattern #538) \|`. Use Edit tool with exact oldString/newString. |
| **REFACTOR step** | `grep -F "flow workspace dashboard" openspec/specs/workspace/spec.md` → expect FOUND at L317. `grep -F "flow workspace tui (future)" openspec/specs/workspace/spec.md` → expect NOT FOUND. `grep -F "Dashboard — not yet implemented" openspec/specs/workspace/spec.md` → expect NOT FOUND. |
| **Files affected** | `openspec/specs/workspace/spec.md` (L317, 1 row in §5 table) |
| **Pre-requisites** | None (independent edit). |
| **Acceptance criteria** | AC3 (L317 row updated to shipped dashboard command + 3 flags + no `--json`). |
| **Risk notes** | TUI-style dashboards deferred to Phase 5.2 per `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE` (L230); this edit only documents the shipped MVP. |

### T-4 — Apply L360 §7 row REMOVE + renumber

| Field | Value |
|-------|-------|
| **Goal** | Remove the §7 row #2 (`workspace-dashboard` Phase 5 deferred entry) since the change has shipped; renumber rows 3-7 → 2-6 to keep the §7 table gap-free. |
| **RED step** | `grep -F "| 2 |" openspec/specs/workspace/spec.md` → expect FOUND (the §7 row #2 about workspace-dashboard TUI). Also verify pre-state row count: 6 §7 rows numbered 2-7. |
| **GREEN step** | Edit L356-L364 area: REMOVE the entire row #2 + renumber rows 3→2, 4→3, 5→4, 6→5, 7→6 in a single contiguous edit. Use Edit tool with the full multi-line block as oldString (containing the header + all 6 rows pre-edit) and the post-state block as newString (header + 5 rows renumbered 2-6). Per design #583 §2.4 — symmetrical precedent: §6.1 RESOLVED note at L354 already references "§7 row #1 (now removed)". |
| **REFACTOR step** | `grep -F "workspace-dashboard (Phase 5)" openspec/specs/workspace/spec.md` → expect NOT FOUND in §7. `grep -F "workspace-hygiene-capability-spec" openspec/specs/workspace/spec.md` → expect FOUND at L360 (now row #2). Verify row count: 5 §7 rows numbered 2-6, gap-free. `grep -c "^| [2-6] |" openspec/specs/workspace/spec.md` → expect exactly 5 §7 rows. |
| **Files affected** | `openspec/specs/workspace/spec.md` (L356-L364, REMOVE 1 row + renumber 5 rows in §7 table) |
| **Pre-requisites** | None (independent edit). |
| **Acceptance criteria** | AC4 (L360 row removed; rows 3-7 renumbered 2-6; §7 table gap-free). |
| **Risk notes** | Cross-reference check: §6.1 RESOLVED note at L354 already references "§7 row #1 (now removed)" — symmetrical precedent. Verified no other specs cross-reference §7 row #2 (explore #577 search returned 0 hits). |

### T-5 — Preservation Gates Verification (after 4 edits, before commit)

| Field | Value |
|-------|-------|
| **Goal** | Run the 12 preservation gates from design #583 §3 to confirm no unintended changes leaked outside the 4 targeted line edits, and that the locked commits + sacred territory + byte-identical guards remain intact. |
| **RED step** | `git status --short` → expect ONLY `openspec/specs/workspace/spec.md` modified (no other tracked files touched). |
| **GREEN step** | Run all 12 preservation gates (must all PASS):<br>1. `git show 6651add --stat` → same file set (PR1 byte-identical).<br>2. `git show 95e8579 --stat` → same file set (PR2 byte-identical).<br>3. `git show 778efdb --stat` → same file set (PR3 byte-identical).<br>4. `git show c9c9650d --stat` → same file set (sort-projects byte-identical).<br>5. `grep -c "^## REQ-WORKSPACE-" openspec/specs/workspace/spec.md` → expect 12 (7 original + 6 dashboard, byte-identical to HEAD `44f9e54`).<br>6. `grep -F "Family index, not canonical source" openspec/specs/workspace/spec.md` → expect FOUND at L4.<br>7. `grep -F "Drift Detection" openspec/specs/workspace/spec.md` → expect FOUND at L366+ (§8 footer intact).<br>8. `grep -F "RESOLVED" openspec/specs/workspace/spec.md` → expect FOUND at L354 (§6.1 Cross-Impact note intact).<br>9. `git status --short openspec/changes/v1.1-followups/` → expect untracked (sacred territory preserved).<br>10. `uv run --frozen pytest tests/unit/test_cli_projects.py::test_flow_projects_ls_json_byte_identical_envelope -xvs` → expect PASSED (AC9 byte-identical guard).<br>11. `grep -F "stash" openspec/specs/workspace/spec.md` → expect NOT FOUND in the 4 edits (no `stash`-triggering words per Pattern #548).<br>12. Visual inspection of `git diff openspec/specs/workspace/spec.md` → no reformatting of surrounding text (Pattern #580); only the 4 targeted hunks changed. |
| **REFACTOR step** | If any gate fails: ABORT and report which gate failed + the unexpected output. Do NOT proceed to T-6 until all 12 gates PASS. |
| **Files affected** | None (verification only — read-only). |
| **Pre-requisites** | T-1, T-2, T-3, T-4 all applied (file modified with the 4 edits). |
| **Acceptance criteria** | All 12 preservation gates from design #583 §3 PASS. |
| **Risk notes** | Gate 10 (AC9 byte-identical guard) requires pytest run; if env unavailable, gate can be deferred to verify phase but should be flagged. |

### T-6 — Single Atomic Commit

| Field | Value |
|-------|-------|
| **Goal** | Commit the 4 text edits as a single atomic commit with the conventional-commits message from design #583 §5. |
| **RED step** | `git status --short` → expect ONLY `openspec/specs/workspace/spec.md` modified. `git diff --stat` → expect ~17 lines diff (8 insertions / 9 deletions) in 1 file. |
| **GREEN step** | Stage explicitly (NO wildcards):<br>1. `git add openspec/specs/workspace/spec.md` (single explicit path).<br>2. `git diff --cached --stat` → verify ONLY 1 file, ~17 lines diff.<br>3. `git diff --cached --name-only` → verify ONLY `workspace/spec.md` (no other tracked files staged).<br>4. `git commit -m "..."` using the exact message from design #583 §5 (see commit plan below).<br>5. NO `Co-Authored-By` line. NO AI attribution. |
| **REFACTOR step** | Verify commit:<br>- `git log --oneline -1` → expect new commit SHA + subject `docs(specs): clean §3/§5/§7 stale dashboard prose`.<br>- `git show HEAD --stat` → expect 1 file modified, 8 insertions / 9 deletions.<br>- `git show HEAD --name-only` → verify only `workspace/spec.md`.<br>- `git log --oneline -2` → verify prior commit (HEAD~1) is the unchanged `44f9e54`. |
| **Files affected** | `openspec/specs/workspace/spec.md` (committed in 1 commit). |
| **Pre-requisites** | T-5 (all 12 preservation gates PASS). |
| **Acceptance criteria** | T-1..T-4 atomicity preserved (1 commit, 4 edits, 1 file). |
| **Risk notes** | NO `--amend` (work-unit-commits skill: each commit is a candidate chained PR). NO force-push. NO empty commit. |

### T-7 — Post-Commit Verify (after T-6, before T-8)

| Field | Value |
|-------|-------|
| **Goal** | Re-run the 12 preservation gates + verify all 4 ACs after the commit, confirming the committed state satisfies every acceptance criterion. |
| **RED step** | Re-confirm 12 preservation gates from T-5 still PASS against the committed state (`git show HEAD:openspec/specs/workspace/spec.md`). |
| **GREEN step** | Run all 4 ACs from proposal #579 §7:<br>- **AC1**: `git show HEAD:openspec/specs/workspace/spec.md` L80 → row contains `workspace-dashboard` + `✅ Shipped` markers + `flow workspace dashboard` + `--filter RULES` + `--sort FIELD` + `--no-color` + no `--json` in that row + archive path.<br>- **AC2**: `grep -F "4 confirmed sub-capabilities" openspec/specs/workspace/spec.md` → FOUND at L73. `grep -F "3 confirmed sub-capabilities + 1 placeholder" openspec/specs/workspace/spec.md` → NOT FOUND.<br>- **AC3**: `grep -F "flow workspace dashboard" openspec/specs/workspace/spec.md` → FOUND at L317 + 3 flags + no `--json` in that row.<br>- **AC4**: §7 table → `grep -c "^| [2-6] |" openspec/specs/workspace/spec.md` → expect exactly 5 §7 rows numbered 2-6 (gap-free). `grep -F "workspace-dashboard (Phase 5)" openspec/specs/workspace/spec.md` → NOT FOUND in §7. |
| **REFACTOR step** | If any AC fails: ABORT and report which AC failed + the unexpected output. Do NOT proceed to T-8 until all 4 ACs PASS. |
| **Files affected** | None (verification only — read-only against committed state). |
| **Pre-requisites** | T-6 (commit applied). |
| **Acceptance criteria** | All 4 ACs from proposal #579 §7 PASS + all 12 preservation gates from design #583 §3 still PASS. |
| **Risk notes** | This is the "gate between apply and archive" — if any AC fails here, the cycle stops and the change cannot be archived. |

### T-8 — Archive (single-PR archive, not chained)

| Field | Value |
|-------|-------|
| **Goal** | Move the change folder to `openspec/changes/archive/2026-06-30-workspace-dashboard-section-cleanup/` and commit the archive chore as a second commit. This is the end of the local cycle; push is EXCLUDED (deferred to after user merge per Pattern #584). |
| **RED step** | `git status --short` → expect ONLY `openspec/changes/workspace-dashboard-section-cleanup/` (untracked ceremony files + tracked `tasks.md` after T-6 commit; the archive move will rename this) + `openspec/changes/v1.1-followups/` (sacred, untouched). NO modifications to `openspec/specs/workspace/spec.md` (already committed in T-6). |
| **GREEN step** | Archive procedure (filesystem move + chore commit):<br>1. Create the archive dir: `New-Item -ItemType Directory -Path "openspec/changes/archive/2026-06-30-workspace-dashboard-section-cleanup" -Force` (using today's date 2026-06-30 per ISO format).<br>2. Move 7 files into the archive dir (preserving structure): `explore.md`, `proposal.md`, `design.md`, `tasks.md`, `specs/workspace/spec.md` (the change-artifact delta spec, NOT the canonical root spec), and write the NEW `archive-report.md` (consolidated 17-section report).<br>3. Remove the now-empty `openspec/changes/workspace-dashboard-section-cleanup/` dir.<br>4. Stage: `git add openspec/changes/archive/2026-06-30-workspace-dashboard-section-cleanup/` + `git rm -r openspec/changes/workspace-dashboard-section-cleanup/`.<br>5. Commit the archive chore with conventional-commits message: `chore(archive): close out workspace-dashboard-section-cleanup change artifacts`.<br>6. NO `Co-Authored-By` line. NO AI attribution. |
| **REFACTOR step** | Verify archive:<br>- `git status --short` → expect clean (no pending changes other than `openspec/changes/v1.1-followups/` untracked sacred territory).<br>- `Test-Path openspec/changes/archive/2026-06-30-workspace-dashboard-section-cleanup` → expect True.<br>- `Test-Path openspec/changes/workspace-dashboard-section-cleanup` → expect False.<br>- `git log --oneline -3` → expect: HEAD = archive chore commit; HEAD~1 = `docs(specs): clean §3/§5/§7 stale dashboard prose` (T-6); HEAD~2 = `44f9e54` (sort-projects merged).<br>- Verify `archive-report.md` exists in the archive dir with 17 sections (status, change summary, goal, 4 text edits, 12 preservation gates, rollback plan, commit message, 4 ACs, 3 carry-overs, final state, references). |
| **Files affected** | `openspec/changes/archive/2026-06-30-workspace-dashboard-section-cleanup/` (7 files moved + 1 NEW `archive-report.md`) + 1 chore commit. |
| **Pre-requisites** | T-7 (all 4 ACs PASS + all 12 preservation gates PASS). |
| **Acceptance criteria** | Change folder moved to archive with full audit trail; 2 commits on the change branch (T-6 apply + T-8 archive). Cycle ends at archive. |
| **Risk notes** | **NO push task** (deferred to after user merge; per Pattern #584). Push is the LAST step, not a mid-cycle step. The user merges the change branch to main and pushes the merge result to `origin/main`. |

---

## 5. Per-Task Dependency Graph

```
T-1 (L73 edit) ───────────┐
T-2 (L80 edit) ───────────┤
T-3 (L317 edit) ──────────┼─→ T-5 (12 preservation gates) ─→ T-6 (commit) ─→ T-7 (post-commit verify) ─→ T-8 (archive)
T-4 (L360 edit) ──────────┘                                                          │
                                                                                      │
                                                          [user merges + pushes] ←── AFTER T-8 (DEFERRED)
```

**Notes:**
- T-1, T-2, T-3, T-4 are **independent** (non-overlapping contiguous hunks in the same file). Can be applied in any order or all together.
- T-5 depends on T-1..T-4 (all 4 edits must be applied before gates can verify).
- T-6 depends on T-5 (gates PASS).
- T-7 depends on T-6 (commit applied).
- T-8 depends on T-7 (post-commit verify PASS).
- **Push** (NOT a task in this cycle) depends on T-8 + user merge decision (per Pattern #584: "push is final, not mid-cycle").

---

## 6. Forecast

| Metric | Value |
|--------|-------|
| Total LOC | ~17 (8 insertions / 9 deletions) in 1 file |
| Files touched (apply) | 1 (`openspec/specs/workspace/spec.md`) |
| Files touched (archive) | 7 moved + 1 NEW (`archive-report.md`) |
| Single PR | Yes |
| Chained PR | No |
| Size exception | No |
| 400-line budget | Yes (well under) |
| TDD strict | OFF (doc-only) |

---

## 7. Review Workload Forecast (MANDATORY per orchestrator protocol)

```yaml
forecast_loc: ~17
forecast_workspace_spec_md: ~17
forecast_total_loc: ~17
chained_pr_recommendation: no
chained_pr_rationale: "Single PR, ~17 LOC well under 400-line single-PR budget"
400_line_budget_risk: low
size_exception_required: no
size_exception_rationale: null
decision_needed_before_apply: no
decision_question: null
```

**Decision needed before apply**: No
**Chained PRs recommended**: No
**Chain strategy**: N/A (single PR)
**400-line budget risk**: Low

---

## 8. Suggested Task Ordering for Chained PRs (N/A)

Not applicable — single PR. The 4 text edits are semantically one cleanup (synchronized stale-prose fix for `phase-5-dashboard` ship state) and do not split cleanly into independent chained PRs.

---

## 9. Out-of-Scope Task Reminders

The following are EXPLICITLY OUT OF SCOPE per the user-locked constraints and must NOT be added as tasks:

- **NO** tasks for any code modification outside `openspec/specs/workspace/spec.md` (Pattern #548 lock).
- **NO** new tests (doc-only change; no test code per AGENTS.md strict-TDD:OFF).
- **NO** new verify checks (8 existing from phase-5-dashboard + 12 preservation gates from design #583 still cover; archived `verify-checks.sh Check 5` will return non-zero after cleanup — expected per explore #577 R1).
- **NO** hash check task (not needed for doc-only text edits).
- **NO** modifications to `openspec/changes/v1.1-followups/` (sacred territory).
- **NO** R1/R3/R4 hygiene operations.
- **NO** Phase 5.2 dashboard implementation (TUI frameworks deferred per `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE`).
- **NO** push task (deferred to after user merge per Pattern #584).
- **NO** L28 / §4.1 / L271-277 / L273 expansion (out of scope per proposal #579; deferred to future `workspace-spec-section-cleanup-1`).
- **NO** modifications to PR1 (`6651add`) / PR2 (`95e8579`) / PR3 (`778efdb`) / sort-projects (`c9c9650d`) commits (all locked per Pattern #548).
- **NO** new runtime dependencies (pure text edits).

The 8 verify checks from phase-5-dashboard still cover the structure; NO new verify checks are added.

---

## 10. Commit Plan (per work-unit-commits skill)

| Aspect | Value |
|--------|-------|
| **Commits** | 2 commits on the change branch: T-6 (apply) + T-8 (archive chore). T-6 is the only "code" commit; T-8 is the audit-trail chore. |
| **T-6 message** | `docs(specs): clean §3/§5/§7 stale dashboard prose` (exact message from design #583 §5; conventional-commits prefix; ≤72 char subject; NO AI attribution). |
| **T-8 message** | `chore(archive): close out workspace-dashboard-section-cleanup change artifacts` (conventional-commits `chore(archive):` prefix; NO AI attribution). |
| **Attribution** | NO `Co-Authored-By` line. NO AI attribution. (Per AGENTS.md rule.) |
| **Atomicity** | T-6 = 1 file modified (`workspace/spec.md`), 4 text edits. T-8 = filesystem move of 7 files + 1 NEW `archive-report.md`. |
| **PR size** | Well under 400-line budget (~17 LOC apply + ~50 LOC archive-report.md). |
| **Chained PR** | No — single PR is sufficient (4 edits are semantically one cleanup). |
| **Work unit** | Standalone (the 4 edits are semantically one cleanup; do not split). |

### T-6 Commit Message (verbatim from design #583 §5)

```
docs(specs): clean §3/§5/§7 stale dashboard prose

The workspace-dashboard capability shipped at commit 778efdb (PR3 of
phase-5-dashboard), but workspace/spec.md still referenced the old
placeholder structure at 4 locations: §3 intro, §3 row 5, §5 row
"tui (future)", §7 row 2. This change cleans the 4 stale prose items
so the dashboard root spec reflects the shipped state.

4 text edits in workspace/spec.md (~17 lines net change):
- L73 §3 intro: "3 confirmed sub-capabilities + 1 placeholder"
  → "4 confirmed sub-capabilities" (coupled to L80)
- L80 §3 row 5: UPDATE to reference shipped phase-5-dashboard
  (with --filter RULES, --sort FIELD, --no-color flags; no --json
  per Pattern #538; archive path)
- L317 §5 row: UPDATE "flow workspace tui (future)" → "flow
  workspace dashboard" with all 3 flags (no --json)
- L360 §7 row 2: REMOVE (dashboard shipped, no longer future)
  + renumber rows 3-7 → 2-6 (gap-free §7 table)

Out of scope (future cleanup debt):
- L28 §1 Purpose bullet (stale reference)
- L271-277 §4.1 dependency-graph (still references placeholder)
- L273 §4.1 graph cross-reference

Carry-over follow-ups (NOT in this change):
- extract-build-needs-by-name-helper
- remove-sort-projects-deprecation-fallback
- AC6 wording fix (Unknown → Unsupported)

PR1 (6651add) + PR2 (95e8579) + PR3 (778efdb) + sort-projects
(c9c9650d) all byte-identical (locked per Pattern #548).
v1.1-followups/ sacred territory preserved.
AC9 byte-identical guard green.
```

---

## 11. Pre-existing Failures (out-of-scope reminder)

All items below are pre-existing and NOT introduced by this change (per design #583 §7):

| Item | Count |
|------|-------|
| Lint errors (`cli.py:683 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`) | 3 |
| sqlite-vec reindex test failures (opt-in) | 4 |
| mypy yaml-stub errors | 2 |
| observability_aggregate test failures | 4 |
| Skipped tests | 2 |
| **Total pre-existing OOS** | **15** |

**Informational**: Archived `verify-checks.sh Check 5` (at `openspec/changes/archive/2026-06-30-phase-5-dashboard/scripts/verify-checks.sh`) will return non-zero after this cleanup. Failure is expected and correct — the archived script is historical audit trail from the phase-5-dashboard cycle; its purpose was to validate the phase-5-dashboard state, not the post-cleanup state. **No action required.**

---

## 12. Acceptance Criteria → Task Mapping

| AC | Description (from proposal #579 §7) | Task(s) that implement | Task(s) that verify |
|----|-------------------------------------|------------------------|---------------------|
| **AC1** | L80 row 5 updated to reference shipped `phase-5-dashboard` (with all 3 flags, no `--json`, archive path) | T-2 (apply the row edit) | T-7 (post-commit grep) |
| **AC2** | L73 intro updated from `3 confirmed sub-capabilities + 1 placeholder` to `4 confirmed sub-capabilities` | T-1 (apply the intro edit) | T-7 (post-commit grep) |
| **AC3** | L317 row updated from `flow workspace tui (future) / (placeholder)` to `flow workspace dashboard` with 3 flags + no `--json` | T-3 (apply the row edit) | T-7 (post-commit grep) |
| **AC4** | L360 row removed; rows 3-7 renumbered 2-6; §7 table gap-free | T-4 (REMOVE + renumber) | T-7 (post-commit grep + row count) |

---

## 13. Risk Summary

Top 5 risks for this tasks phase:

1. **LOW — File state discrepancy at apply time**: The spec phase (#581) may have already applied the 4 text edits to `openspec/specs/workspace/spec.md`. If so, T-1..T-4 RED grep checks return NOT FOUND (file already in after-state). Mitigation: T-1..T-4 verification grep (REFACTOR step) confirms the post-state matches; if pre-state grep returns NOT FOUND, treat as no-op edits + continue to T-5 gates.
2. **LOW — Archived `verify-checks.sh Check 5` returns non-zero after cleanup**: Expected per explore #577 R1. The archived script is historical audit trail; failure is correct, not a regression. No action required (per design #583 §7 + proposal #579 §10 R1).
3. **LOW — Markdown table column alignment cosmetic**: Replacement text matches existing Phase 1/3/4 column widths (per proposal #579 §10 R2). Verified by `git diff` visual inspection in T-5 Gate 12.
4. **LOW — L73 coupled 1-line tweak technically outside user-locked 3 items**: User approved the 4th item in the same locked scope (per proposal #579 §10 R3). Scope remains surgical — only L73/L80/L317/L360 touched.
5. **LOW — T-4 cross-references in other specs**: Explore #577 confirmed 0 hits for §7 row #2 cross-references outside `workspace/spec.md`. No downstream changes needed.

---

## Next SDD Phase

`sdd-apply workspace-dashboard-section-cleanup` — execute T-1..T-8 mechanically per the locked design. The cycle ends at T-8 archive; push is deferred to after user merge (per Pattern #584).

---

*Generated by the `sdd-tasks` sub-agent for `workspace-dashboard-section-cleanup`. Tasks artifact mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-dashboard-section-cleanup/tasks"`, `type: "architecture"`, `capture_prompt: false`. Design philosophy: "limpiar lo prometido, nada más" (Pattern #582).*