# Tasks: workspace-spec-section-cleanup-1

> **Phase**: tasks (5th of 8)
> **Change**: `workspace-spec-section-cleanup-1`
> **Project**: flow-engineering v1.2.0
> **Mode**: openspec (filesystem) + Engram mirror
> **Strict TDD**: OFF (doc-only; no test code)
> **Builds on**: design #598 (4 components, 22 preservation gates) · spec #596 (3 text edits applied) · proposal #594 · explore #593
> **Forecast**: ~5 min wall-time (mechanical derivation of locked design)
> **Pattern**: *trámite controlado* (#599) — mechanical execution of locked design; no design decisions; no scope expansion

---

## 1. Review Workload Forecast (MANDATORY per orchestrator protocol)

```yaml
forecast_loc: ~12
forecast_workspace_spec_md: ~12          # 6 insertions / 5 deletions / 1 net line
forecast_change_artifact: ~195           # change-artifact delta spec (committed in archive chore)
forecast_total_loc: ~207
chained_pr_recommendation: no
chained_pr_rationale: "Single PR, ~12 LOC well under 400-line single-PR budget"
400_line_budget_risk: low
size_exception_required: no
size_exception_rationale: null
decision_needed_before_apply: no
decision_question: null
push_excluded_from_cycle: true           # per Pattern #584
push_deferred_to_user_merge: true        # per Pattern #584
```

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

---

## 2. Task summary table

| T#  | Title                                       | Action type                | Verifies             |
|-----|---------------------------------------------|----------------------------|----------------------|
| T-1 | Apply L28 §1 Purpose bullet edit            | Edit (post-state check)    | AC1                  |
| T-2 | Apply L271-278 §4.1 dependency graph box    | Edit (post-state check)    | AC2                  |
| T-3 | Verify L273 cross-reference (subsumed)      | Verify (no-op)             | AC3 (subsumed)       |
| T-4 | Preservation gates verification (22 gates)  | Verify (pre-commit)        | AC4 preservation     |
| T-5 | Single atomic commit                        | Commit (work-unit)         | Apply single-PR step |
| T-6 | Post-commit verify (3 ACs + 22 gates)       | Verify (post-commit)       | All ACs re-check     |
| T-7 | Archive (single-PR archive, NO push)        | Archive (filesystem move)  | Cycle closure        |

**Total: 7 mechanical tasks** (T-1..T-7). NO push task (deferred to after user merge per Pattern #584). NO expand to L69 / L269 / L291 (deferred to `workspace-spec-section-cleanup-2`).

---

## 3. Task definitions

### T-1 — Apply L28 §1 Purpose bullet edit

- **Task ID**: T-1
- **Title**: Apply L28 §1 Purpose bullet edit
- **Goal**: Replace the stale `(Phase 5 placeholder) will surface workspace state in a TUI or web visualization.` bullet at L28 with the shipped Rich dashboard bullet (post-state handling per Pattern #586 — the spec phase #596 already applied the edit to the working tree).
- **RED step** (post-state check): `grep -F "(Phase 5 placeholder) will surface workspace state in a TUI or web visualization" openspec/specs/workspace/spec.md` → expect **NOT FOUND** (spec phase #596 already swapped). If FOUND, the post-state is wrong — ABORT and report.
- **GREEN step** (conditional): if RED found OLD text, apply Edit tool with FIND/REPLACE from design #598 Component 1 (L28 verbatim 1-for-1 swap; 0 net line delta).
- **REFACTOR step**: `grep -F "visualizes workspace state in a read-only Rich dashboard" openspec/specs/workspace/spec.md` → expect FOUND; `grep -F "(Phase 5 placeholder)" openspec/specs/workspace/spec.md` → expect NOT FOUND; `grep -F "TUI or web visualization" openspec/specs/workspace/spec.md` → expect NOT FOUND.
- **Files affected**: `openspec/specs/workspace/spec.md` (L28 only; conditional edit)
- **Pre-requisites**: none (independent; post-state handling)
- **Acceptance criteria**: AC1 (L28 bullet updated; no `(Phase 5 placeholder)` marker; no `TUI or web visualization` framing; names `flow workspace dashboard` + 3 flags + no-`--json` invariant)
- **Risk notes**: LOW — post-state already applied per Pattern #586; if RED finds OLD text the post-state is wrong, ABORT.

### T-2 — Apply L271-278 §4.1 dependency graph box edit

- **Task ID**: T-2
- **Title**: Apply L271-278 §4.1 dependency graph box edit
- **Goal**: Replace the 7-line PLACEHOLDER STUB box at L271-L277 with the 8-line phase-5-dashboard shipped-state box (post-state handling — spec phase #596 already applied the edit; L273 cross-reference swap is subsumed here).
- **RED step** (post-state check): `grep -F "STATUS: PLACEHOLDER STUB" openspec/specs/workspace/spec.md` → expect NOT FOUND (spec phase #596 already swapped). Also `grep -F "REQ-WORKSPACE-DASHBOARD-PLACEHOLDER" openspec/specs/workspace/spec.md` → expect NOT FOUND. If EITHER is FOUND, the post-state is wrong — ABORT.
- **GREEN step** (conditional): if RED found OLD text, apply Edit tool with FIND/REPLACE from design #598 Component 2 (L271-L277 7-line → L271-L278 8-line box; net +1 line; top/bottom borders + P5 header preserved verbatim; ASCII column alignment preserved at 39 ASCII chars between `│`).
- **REFACTOR step**: `grep -F "Source: phase-5-dashboard (shipped)" openspec/specs/workspace/spec.md` → expect FOUND at L277; `grep -F "Phase 5: 6 REQs incl. Rich MVP" openspec/specs/workspace/spec.md` → expect FOUND; `Measure-Object -Line openspec/specs/workspace/spec.md` → expect 377 LF; verify ASCII column alignment by reading L271-L278 with Read tool (visual inspection, Pattern #598: no reformatting of surrounding text).
- **Files affected**: `openspec/specs/workspace/spec.md` (L271-L278 only; conditional edit; +1 net line)
- **Pre-requisites**: none (independent of T-1; post-state handling)
- **Acceptance criteria**: AC2 (L271-278 box updated; no `PLACEHOLDER STUB`; no `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER`; no `§7 Future Changes` cross-ref; 8-line box with shipped state)
- **Risk notes**: LOW — ASCII alignment drift mitigated by reusing top/bottom borders verbatim + matching inner-line content width to L272 (39 ASCII chars between `│` chars). Visual re-read is mandatory.

### T-3 — Verify L273 cross-reference (subsumed in T-2)

- **Task ID**: T-3
- **Title**: Verify L273 cross-reference (subsumed in T-2)
- **Goal**: Verify L273 reads `flow workspace dashboard` (no `tui / web` slash-separated framing). L273 is the 2nd line of the L271-278 box replaced by T-2; this task is a verify-only no-op that confirms the swap landed.
- **RED step**: none (no edit needed; this is a verify-only task)
- **GREEN step**: nothing (L273 swap is subsumed in T-2's box replacement)
- **REFACTOR step**: `grep -F "flow workspace dashboard" openspec/specs/workspace/spec.md | wc -l` → expect multiple matches (L80 row 5 from prior cycle + L273 in box from this cycle); `grep -F "flow workspace tui / web" openspec/specs/workspace/spec.md` → expect NOT FOUND.
- **Files affected**: none (verification only)
- **Pre-requisites**: T-2 (the box replacement must be applied first)
- **Acceptance criteria**: AC3 (L273 cross-reference updated to `flow workspace dashboard`)
- **Risk notes**: NEGLIGIBLE — pure verification; if T-2's box replacement landed correctly, T-3 is automatic.

### T-4 — Preservation gates verification (22 gates before commit)

- **Task ID**: T-4
- **Title**: Preservation gates verification (22 gates before commit)
- **Goal**: Run the 22 preservation gates from design #598 Component 2 (12 root REQ `Source:` lines + 4 section/footer + 5 locked-commit/sacred-territory + 5 stale-marker-removed + 3 OOS-preserved) BEFORE the commit in T-5. All 22 gates MUST be green; any FAIL → ABORT and report.
- **RED step**: `git status --short` → expect ONLY untracked ceremony files (`openspec/changes/v1.1-followups/` + `openspec/changes/workspace-spec-section-cleanup-1/`). If any tracked file other than `openspec/specs/workspace/spec.md` shows as modified, the scope has drifted — ABORT.
- **GREEN step** (run all 22 gates — abbreviated for clarity, full list in design #598 §3):

  **A. Root REQ `Source:` lines intact (12/12)** — `grep -F "**Source:**"` per REQ block (L96, L114, L124, L134, L144, L164, L174, L186, L198, L210, L222, L234) → all FOUND
  **B. Section structure + footer gates (4/4)** — gate #13 `grep -F "Family index, not canonical source"` → FOUND at L4; gate #14 `grep -F "RESOLVED"` → FOUND at L354; gate #15 `grep -F "Drift Detection"` → FOUND in §8 footer; gate #16 `grep -c "^## "` → expect 10 (8 `##` + 1 `###` for §6.1, plus the §4.1 sub-section)
  **C. Locked-commit + sacred-territory gates (5/5)** — gate #17-21: `git log --oneline 6651add..1ef33cf^` / `95e8579..1ef33cf^` / `778efdb..1ef33cf^` / `c9c9650d..1ef33cf^` / `1ef33cf..1ef33cf^` → expect all EMPTY; gate #22: `git status --short openspec/changes/v1.1-followups/` → expect untracked
  **D. Stale markers REMOVED (5/5)** — `grep -F "Phase 5 placeholder"` / `"TUI or web visualization"` / `"PLACEHOLDER STUB"` / `"REQ-WORKSPACE-DASHBOARD-PLACEHOLDER"` / `"flow workspace tui / web"` → expect ALL NOT FOUND
  **E. OOS items PRESERVED (3/3)** — `grep -F "Show me a TUI"` → expect FOUND at L69 (OOS for -2); `grep -F "Phase 5 (future)" openspec/specs/workspace/spec.md | wc -l` → expect 2+ (L269 + L291 OOS for -2); `grep -F "Source: phase-5-dashboard (shipped)"` → expect FOUND at L277 (new reference added by T-2)

- **REFACTOR step**: if any of the 22 gates FAILS, ABORT and report which gate failed (per Pattern #599: mechanical execution — gates are non-negotiable).
- **Files affected**: none (verification only)
- **Pre-requisites**: T-1 + T-2 + T-3 (all 3 edits applied)
- **Acceptance criteria**: AC4 (preservation gate — no changes to `v1.1-followups/`, no modifications to any locked commit, no new runtime dependencies)
- **Risk notes**: LOW — gates are mechanical; failure mode is binary (pass/abort). Pattern #598 (visual inspection: no reformatting of surrounding text) + box ASCII alignment check at L271-278 are mandatory before T-5 commit.

### T-5 — Single atomic commit

- **Task ID**: T-5
- **Title**: Single atomic commit
- **Goal**: Stage + commit `openspec/specs/workspace/spec.md` as a single atomic commit with the conventional-commits message from design #598 Component 4. The commit is the work-unit that delivers the entire 3-text-edit change in one atomic diff.
- **RED step** (post-state confirmation): `git status --short` → expect ONLY untracked ceremony files + ` M openspec/specs/workspace/spec.md` (1 modified tracked file, no others). If multiple modified tracked files appear, the scope has drifted — ABORT.
- **GREEN step**:
  1. `git add openspec/specs/workspace/spec.md` (explicit path, NO wildcards per Pattern #548)
  2. `git diff --cached --stat` → verify 1 file modified, ~6 insertions / 5 deletions
  3. `git diff --cached --name-only` → verify ONLY `openspec/specs/workspace/spec.md`
  4. `git commit -m "<message from design #598 Component 4>"` — exact message format:
     - Subject: `docs(specs): clean §1 + §4.1 stale dashboard prose`
     - Body: rationale + 3-text-edit enumeration + OOS deferred list + preservation-gate green confirmation
     - Footer: `Co-Authored-By: none` (per global rule — no AI attribution)

- **REFACTOR step**: `git log --oneline -1` → verify commit message subject line is exactly `docs(specs): clean §1 + §4.1 stale dashboard prose`; `git show HEAD --stat` → verify 1 file modified, ~6 insertions / 5 deletions; `git status --short` → verify working tree clean (only untracked ceremony files remain).
- **Files affected**: `openspec/specs/workspace/spec.md` (1 file committed in 1 atomic commit; no other files touched)
- **Pre-requisites**: T-4 (22 preservation gates PASS)
- **Acceptance criteria**: AC1 + AC2 + AC3 + AC4 (all 4 ACs are committed at once)
- **Risk notes**: LOW — atomic commit prevents partial state; `git add` uses explicit path (no wildcards) per Pattern #548; commit message format is verbatim from design #598 (no AI attribution).

### T-6 — Post-commit verify (after T-5 commit, before T-7 archive)

- **Task ID**: T-6
- **Title**: Post-commit verify (after T-5 commit, before T-7 archive)
- **Goal**: Re-run the 22 preservation gates from T-4 + the 3 ACs from proposal §7 against the committed state. Confirms the commit landed cleanly and no regressions slipped in between T-4 and T-5.
- **RED step**: re-run all 22 preservation gates from T-4 against the committed state (`git show HEAD:openspec/specs/workspace/spec.md` source). All 22 MUST still PASS — any FAIL is a regression introduced by T-5 (extremely unlikely, but the post-commit gate catches it).
- **GREEN step** (3 ACs):
  - **AC1**: `grep -F "visualizes workspace state in a read-only Rich dashboard" openspec/specs/workspace/spec.md` → expect FOUND (at L28)
  - **AC2**: `grep -F "Source: phase-5-dashboard (shipped)" openspec/specs/workspace/spec.md` → expect FOUND (in the box at L277)
  - **AC3**: `grep -F "flow workspace tui / web" openspec/specs/workspace/spec.md` → expect NOT FOUND (L273 swap applied)

- **REFACTOR step**: also re-run the 22 preservation gates; if any FAILS, ABORT and report (do NOT proceed to T-7 archive with a regression).
- **Files affected**: none (verification only)
- **Pre-requisites**: T-5 (commit applied)
- **Acceptance criteria**: AC1 + AC2 + AC3 + AC4 (post-commit re-confirmation)
- **Risk notes**: NEGLIGIBLE — T-5 is atomic; regression window is the `git commit` operation itself. If any gate fails, the commit is suspect and should be investigated before T-7 archive.

### T-7 — Archive (single-PR archive, NO push)

- **Task ID**: T-7
- **Title**: Archive (single-PR archive, NO push)
- **Goal**: Move the change folder `openspec/changes/workspace-spec-section-cleanup-1/` → `openspec/changes/archive/2026-06-30-workspace-spec-section-cleanup-1/` and write the consolidated `archive-report.md` inside the moved folder. Cycle ENDS at T-7 (Pattern #584 — push is OUTSIDE the cycle).
- **RED step**: `git status --short` → expect ONLY untracked ceremony files (`v1.1-followups/` + `workspace-spec-section-cleanup-1/`) + the new commit from T-5. If any other change, ABORT.
- **GREEN step** (filesystem move + report):
  1. `Move-Item -LiteralPath "openspec/changes/workspace-spec-section-cleanup-1" -Destination "openspec/changes/archive/2026-06-30-workspace-spec-section-cleanup-1"` (or equivalent `mv`/`robocopy` + `rmdir` of source)
  2. Verify all 6 files moved: `explore.md`, `proposal.md`, `design.md`, `tasks.md`, `specs/workspace/spec.md`, plus NEW `archive-report.md` (to be created in REFACTOR step)
  3. Confirm `openspec/changes/workspace-spec-section-cleanup-1/` no longer exists at the active location
  4. Confirm `openspec/specs/workspace/spec.md` (the canonical merged result) is unchanged — archive phase does NOT touch main specs (the 3 text edits are already committed in T-5)

- **REFACTOR step**: write consolidated `archive-report.md` INSIDE the moved folder (16 sections mirroring the prior cycle's archive-report template):
  1. Status: COMPLETE / PASS / doc-only
  2. Change summary: 1-paragraph overview
  3. Goal: §1 Purpose bullet + §4.1 dependency-graph box cleaned (carry-over from `workspace-dashboard-section-cleanup` archive-report §9 items #4/#5/#6)
  4. 3 text edits: L28 + L271-278 box + L273 (subsumed)
  5. 22 preservation gates: all PASS (12 REQ Sources + 4 section/footer + 5 locked-commit/sacred-territory + 5 stale-marker-removed + 3 OOS-preserved — but presented as 5 negative-space gates merged into the "stale markers removed" group + 3 OOS-preserved at the end)
  6. Rollback plan: `git revert HEAD` (per design #598 Component 3)
  7. Commit message: full text per design #598 Component 4
  8. 3 ACs: AC1 + AC2 + AC3 verified (AC4 as preservation gate umbrella)
  9. 2 OOS deferred to `workspace-spec-section-cleanup-2`: L69 + L269 + L291 (3 items, despite the "2 OOS" label — the actual count is 3 items deferred)
  10. Final state: `openspec/specs/workspace/spec.md` at 377 LF; committed in T-5; 1 commit on `main`
  11. References: design #598 / spec #596 / proposal #594 / explore #593 / prior cycle archive
  12. Carry-forwards: items #1/#2/#3 from prior cycle's §9 are unrelated; L69/L269/L291 are THIS cycle's deferred items (record both for clarity)
  13. Pre-existing failures: 3 lint + 4 reindex + 2 mypy + 4 observability + 2 skipped (all OOS, unchanged)
  14. Locked-commit inventory: 14+ commits byte-identical per Pattern #548 (list SHAs if needed)
  15. Push status: DEFERRED to after user merge per Pattern #584 (no `git push` performed in this cycle)
  16. Cycle close: Pattern #597 honored — clean closure regardless of change size

- **Files affected**:
  - `openspec/changes/workspace-spec-section-cleanup-1/` (removed from active location)
  - `openspec/changes/archive/2026-06-30-workspace-spec-section-cleanup-1/` (created with 6 files: 5 moved + 1 NEW `archive-report.md`)
  - **NO modifications to `openspec/specs/workspace/spec.md`** (already committed in T-5; archive phase is filesystem move only)

- **Pre-requisites**: T-6 (post-commit verify PASS)
- **Acceptance criteria**: cycle closure per Pattern #597 (clean closure regardless of change size); archive-report inherits items #4/#5/#6 from prior cycle's §9 as RESOLVED
- **Risk notes**: LOW — filesystem move is reversible (`mv` back); no code or registry changes; **NO push** (deferred to after user merge per Pattern #584 — this is non-negotiable).

---

## 4. Per-task dependency graph

```
T-1 (L28 edit) ───────────────┐
                              │
T-2 (L271-278 box) ──────────┼──┐
                              │  │
T-3 (L273 verify, subsumed) ──┘  │
                                 ▼
                       T-4 (22 preservation gates)
                                 │
                                 ▼
                       T-5 (single atomic commit)
                                 │
                                 ▼
                       T-6 (post-commit verify)
                                 │
                                 ▼
                       T-7 (archive, NO push)
                                 │
                                 ▼
                  [user merges + pushes]   ← AFTER T-7, OUTSIDE cycle
```

---

## 5. Forecast

- **Total LOC of text changes**: ~12 LOC (6 insertions / 5 deletions, 1 net line)
- **Total change-artifact LOC**: ~195 LOC (delta spec, already committed as part of `v1.1-followups` ceremony via spec phase #596)
- **Total PR delta**: ~207 LOC, well under 400-line single-PR budget
- **Single PR**: yes, no chained PR needed
- **Size exception**: not needed
- **No new tests**: confirmed (doc-only)
- **No new verify checks**: confirmed (8 existing from `phase-5-dashboard` still cover)

---

## 6. Suggested task ordering for chained PRs

Not applicable — single PR. The 7 tasks are sequential within ONE atomic commit (T-5); the PR contains the entire change as 1 commit (per Pattern #548: commit by work unit, the work unit here is the doc cleanup itself).

---

## 7. Out-of-scope task reminders

- NO tasks for: any code modification outside `openspec/specs/workspace/spec.md`, new verify checks, hash check (not needed for doc-only), modifications to `openspec/changes/v1.1-followups/`, Phase 5.2 dashboard implementation, **push** (deferred to after user merge per Pattern #584)
- The 22 preservation gates are WITHIN `workspace-spec-section-cleanup-1` scope (not new verify checks added to the codebase)
- L69 / L269 / L291 are EXPLICITLY OUT OF SCOPE (deferred to `workspace-spec-section-cleanup-2` — future cleanup)

---

## 8. Commit plan (per work-unit-commits skill)

- **Single commit** per PR (delivery strategy: `single-pr`)
- **Commit message format**: `docs(specs): clean §1 + §4.1 stale dashboard prose` (exact message in design #598 Component 4)
- **NO AI attribution** (no `Co-Authored-By` footer per global rule; subject + body + `Co-Authored-By: none` per design #598)
- **Atomic** — 1 file modified (`workspace/spec.md`), 3 text edits, ~6 insertions / 5 deletions
- **Files staged**: `openspec/specs/workspace/spec.md` (explicit path, NO wildcards per Pattern #548)
- **Push deferred** to after user merge per Pattern #584 (no `git push` in T-5 or T-7)

---

## 9. Pre-existing failures (out-of-scope reminder)

All items below are **pre-existing** and **NOT introduced** by this change (doc-only):

- 3 pre-existing lint errors OOS (`cli.py:683 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`)
- 4 pre-existing reindex test failures OOS (sqlite-vec opt-in)
- 2 pre-existing mypy yaml-stub errors OOS
- 4 pre-existing observability_aggregate test failures OOS
- 2 pre-existing skipped tests OOS

---

## 10. Acceptance criteria → REQ mapping

| AC | Description                                            | Task(s)             |
|----|--------------------------------------------------------|---------------------|
| AC1 | L28 §1 Purpose bullet updated                          | T-1, T-6            |
| AC2 | L271-278 §4.1 dependency-graph box updated             | T-2, T-6            |
| AC3 | L273 in-box cross-reference updated                    | T-3 (subsumed in T-2), T-6 |
| AC4 | Preservation gate (no v1.1-followups touch, no locked-commit mods, no new runtime deps) | T-4, T-6 |

---

## 11. Risk summary

| # | Severity | Risk | Mitigation |
|---|----------|------|------------|
| R1 | LOW | Post-state already applied: spec phase #596 has the 3 text edits. T-1 / T-2 may be no-ops (Pattern #586 from prior cycle) | RED step in T-1 + T-2 verifies post-state; if OLD text found, the post-state is wrong → ABORT |
| R2 | LOW | Scope creep at apply (L69 / L269 / L291 tempting to add) | Explicit out-of-scope list in commit message body; design #598 §6 lock; commit message footer mentions OOS deferred to `-2` |
| R3 | LOW | Box height mismatch in §4.1 ASCII diagram (L271-278) | Preserve top/bottom borders verbatim + match inner-line content width to L272 (39 ASCII chars between `│` chars); visual re-read at T-2 REFACTOR + T-4 gate #22 |
| R4 | NEGLIGIBLE | ASCII column alignment drift | Inner-line width = 39 chars; box height 8 lines; both verified by visual inspection in T-2 + T-4 |
| R5 | NEGLIGIBLE | v1.1-followups/ accidental touch | Gate #22 in T-4 + T-6; `git status --short openspec/changes/v1.1-followups/` must show untracked (never tracked) |
| R6 | NEGLIGIBLE | Locked-commit amend | Gates #17-#21 in T-4 + T-6: 4 `git log --oneline <sha>..1ef33cf^` checks must return EMPTY |

---

## 12. Wall-time forecast

| Phase       | Estimate | What happens                                                                                       |
|-------------|----------|----------------------------------------------------------------------------------------------------|
| `sdd-tasks` (this) | ~5 min | Mechanical derivation from locked design #598                                                       |
| `sdd-apply` | ~5 min   | T-1..T-3 (post-state handling, likely no-ops) + T-4 (22 gates) + T-5 (commit)                      |
| `sdd-verify`| ~5 min   | T-6 (post-commit re-run of 22 gates + 3 ACs)                                                       |
| `sdd-archive`| ~5 min  | T-7 (filesystem move + archive-report.md)                                                          |
| **Total remaining** | **~20 min** | **Push deferred after user merge per Pattern #584**                                              |

---

## 13. Next SDD Phase

`sdd-apply` — execute T-1..T-5 mechanically per the locked design. Forecast: ~5 min.

---

*Generated by the `sdd-tasks` sub-agent for `workspace-spec-section-cleanup-1`. Tasks artifact mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-spec-section-cleanup-1/tasks"`, `type: "architecture"`, `project: "insyd"`, `capture_prompt: false`. Scope locked: 7 mechanical tasks (T-1..T-7), no push task, no L69/L269/L291 expansion. "Trámite controlado — diseño como caja cerrada."*