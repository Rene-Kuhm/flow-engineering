# Archive Report — `workspace-spec-cross-impact-cleanup` (CONSOLIDATED close-out)

> **Change**: `workspace-spec-cross-impact-cleanup` — doc-only cleanup of W1 + W2 stale prose in `openspec/specs/workspace/spec.md` carried forward from `flow-where-cross-project-capability-merge` verify #513.
> **Status**: **ARCHIVED (consolidated)** — 2026-06-30.
> **SDD cycle**: explore (1/8) → propose (2/8) → spec (3/8) → design (4/8) → tasks (5/8) → apply (6/8) → verify (7/8) → **archive (8/8, this report)**.
> **Archive destination**: `openspec/changes/archive/2026-06-30-workspace-spec-cross-impact-cleanup/`.
> **User action remaining**: merge `codex/workspace-spec-cross-impact-cleanup` @ `7ecab3b` to `main` locally + push to `origin/main` (single PR; user handles).
> **Mode**: Strict TDD **OFF** (doc-only change; the 7 verify checks from design #492 §4 ARE the verification surface).
> **Artifact store mode**: hybrid — OpenSpec file (this report) + Engram mirror (new observation, topic_key `sdd/workspace-spec-cross-impact-cleanup/archive-report`).

---

## 1. Final Verdict

**PASS — archive-ready, single-PR merge-ready.** The smallest cycle in the workspace-intelligence arc (~60 min wall-clock, 1 commit, 1 file, 4 diff lines).

| Metric | Result |
|---|---|
| Apply commits (spec → main) | 1 (`7ecab3b`) |
| Archive commit (this phase) | 0 (per user lock: archive is folder-move only, not committed — ceremony artifacts stay untracked) |
| PRs | 1 (single PR — 1% of 400-line review budget) |
| User-locked constraints satisfied | **20/20** (14 prior + 4 archive locks + 2 new archive locks) |
| Files modified | 1 — `openspec/specs/workspace/spec.md` (315 LF preserved) |
| Edits | 2 single-line (W1 at L241, W2 at L16) |
| Diff size | 2 ins + 2 del (0 net lines; 315 LF preserved) |
| Acceptance criteria (ACs) | **7/7 PASSED** (per proposal #521 §7 + verify-report #530) |
| Verify checks | **7/7 PASSED** (per design #492 §4, re-validated in design #525 §2) |
| Baseline preservation gates | **4/4 PASSED** (pytest 1513/1513, AC9 byte-identical guard green, mypy clean, 3 pre-existing ruff errors unchanged) |
| Pre-existing lint errors touched | 0 (3 OOS errors identical to Phase 4 baseline) |
| Wall-clock (distributed across 8 phases) | **~60 min** — cheapest cycle in the workspace-intelligence arc |
| Merge readiness | READY (single PR, all gates green, awaiting user merge + push) |
| Scope discipline | **STRICT** — W1 + W2 ONLY; 3 informational stale-prose items documented as future cleanup |

---

## 2. Change Summary

### Identity

| Field | Value |
|---|---|
| Change name | `workspace-spec-cross-impact-cleanup` |
| Phase (in workspace-intelligence arc) | **Post-Phase 2 hygiene** — surgical cleanup of stale prose left behind by the `flow-where-cross-project-capability-merge` merge (#513) |
| Capability | Doc-only — pure prose edit to `openspec/specs/workspace/spec.md` |
| Scope | 2 single-line edits in the canonical workspace spec (W1 at L241, W2 at L16); ~3 word-tokens net change |
| Scope (explicitly OUT) | Code changes; new verify checks; modifications to any prior archived spec; `v1.1-followups/` work; `flow-where/spec.md` edits; §4.1 L221 / §6.1 L290 / §6.1 L292 stale prose; new top-level capability spec |
| Canonical spec path | `openspec/specs/workspace/spec.md` (315 LF, INTACT post-edit) |
| Change-artifact spec path | `openspec/changes/archive/2026-06-30-workspace-spec-cross-impact-cleanup/specs/workspace/spec.md` (delta spec — 86 LF, archived) |
| Apply branch | `codex/workspace-spec-cross-impact-cleanup` |
| Apply commit SHA | `7ecab3b594c4cbee3608f10f086f7a2bfcd50dc3` (short: `7ecab3b`) |
| Apply commit message | `chore(specs): fix W1+W2 stale cross-impact prose in workspace root` |
| Parent commit (main HEAD) | `780285f` (post `flow-where-cross-project-capability-merge` merge) |

### Why this change exists

The `flow-where-cross-project-capability-merge` verify phase (#513) flagged two surviving stale references in `openspec/specs/workspace/spec.md` even after the apply phase of the merge landed at commit `6e21d4d`. These two warnings (W1 + W2) sat on disk as documentation debt. Before the Phase 5 dashboard change adds a new delta on top of this foundation, the workspace root spec needs to be impeccable. This PR closes those two warnings atomically: a 2-line edit, no design surface, no new verify checks.

### Inputs / Outputs

- **Input**: `flow-where-cross-project-capability-merge` verify-report #513 — flagged W1 (L241 §4.2 versioning table still referenced `REQ-V1.0.5..V1.0.X` placeholder) and W2 (L16 archive-status meta-pointer still listed `flow-where-cross-project-capability-merge` as a carry-forward even though it had landed at commit `8d51c5f`).
- **Output**: W1 fixed at L241 — `REQ-V1.0.5..V1.0.X` → `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` (6 REQs). W2 fixed at L16 — `flow-where-cross-project-capability-merge` (Phase 2 follow-up) removed from carry-forwards list. 7 verify checks re-validated PASS. Baseline preserved at 1513/1513 pytest + AC9 byte-identical guard green + mypy clean + 3 pre-existing ruff errors unchanged.

### Lifecycle

```
explore.md  →  proposal.md  →  specs/workspace/spec.md (delta spec — MODIFIED Prose only)
                                       ↓
                              design.md (re-validates 7 checks from design #492 §4)
                                       ↓
                              tasks.md (5 mechanical tasks; single-PR strategy confirmed)
                                       ↓
                         apply: commit 7ecab3b (1 file, 2 ins / 2 del, 0 code)
                                       ↓
                         verify-report.md (7 ACs + 7 checks + 4 baseline gates + post-commit re-verify)
                                       ↓
                     CONSOLIDATED ARCHIVE (this report, 8/8)
                                       ↓
                       [user: merge --no-ff to main + push to origin/main]
```

---

## 3. The 2 Specific Fixes

### 3.1 W1 — `openspec/specs/workspace/spec.md` L241, §4.2 versioning table, last row

- **Before**: `` `flow-where/spec.md` gains `REQ-V1.0.5..V1.0.X` ``
- **After**: `` `flow-where/spec.md` gains `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` ``
- **Rationale**: The `REQ-V1.0.5..V1.0.X` string was a forward-looking placeholder authored during `workspace-capability-bootstrap` (Engram #490 / #492) before Phase 2 actually integrated. After the apply phase of `flow-where-cross-project-capability-merge` (commit `6e21d4d`), the 6 root REQs landed in `flow-where/spec.md` with a different namespace: `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN`. The W1 fix matches the exact phrasing of §6.1 L292 RESOLVED note (consistency principle: a reviewer reading both locations sees the same wording).
- **Method**: in-place substitution; surrounding context (the §4.2 table row) preserved byte-identical.

### 3.2 W2 — `openspec/specs/workspace/spec.md` L16, archive-status meta-pointer

- **Before**: ``**Carry-forwards documented in Future Changes** (§7): `flow-where-cross-project-capability-merge` (Phase 2 follow-up), Phase 5 `workspace-dashboard`, optional `workspace-hygiene-capability-spec`, `backup-retention-policy` review, R1/R3/R4 deferred rules.``
- **After**: ``**Carry-forwards documented in Future Changes** (§7): Phase 5 `workspace-dashboard`, optional `workspace-hygiene-capability-spec`, `backup-retention-policy` review, R1/R3/R4 deferred rules.``
- **Rationale**: The follow-up has fully landed (apply `6e21d4d`, archive chore `8d51c5f`, archived at `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/`). The §7 row was already removed per verify-report #513 AC7 ("workspace §7 row removed | PASSED | §7 contains 0 table rows referencing this change"). The §6.1 RESOLVED note at L292 explicitly records that the reclassification is RESOLVED. Listing it as a "carry-forward documented in Future Changes" contradicted the rest of the file.
- **Method**: clean removal of 44 characters (`, ` followed by the stale item); remaining 4 carry-forwards remain grammatically intact.

---

## 4. 7 Verify Checks (Re-validated from design #492 §4)

The 7 verify checks from `workspace-capability-bootstrap` design #492 §4 are the entire verification surface. They were re-validated in design #525 §2 (post-edit state), and re-run against committed HEAD `7ecab3b` per verify-report #530. **All 7 PASSED.**

| # | Check | Post-W1/W2 result | Diagnostic |
|---|-------|-------------------|------------|
| 1 | Every `## REQ-WORKSPACE-*` block has exactly one `**Source:**` line (7/7 expected) | **PASSED (7/7)** | All 7 root REQs (PROJECT-IDENTITY, STATUS-DISCOVERY, MUTATION-SAFETY, DRY-RUN-DEFAULT, R1-DEFERRED, REGISTRY-V1, DASHBOARD-PLACEHOLDER) each carry exactly 1 Source: line. W1/W2 do not touch any REQ block. |
| 2 | Every `Source:` path exists on disk (6/6 expected; 1 placeholder exempt) | **PASSED (6/6)** | 3 unique paths (`projects-ls-extension/spec.md`, `workspace-status/spec.md`, `workspace-hygiene/spec.md`), 6 path-tokens total. All 3 paths EXIST on disk. REQ-WORKSPACE-DASHBOARD-PLACEHOLDER exempt (forward-looking form, no path). |
| 3 | Every `Source:` REQ-ID exists in cited delta spec (19 IDs across 6 root REQs) | **PASSED (19/19)** | 19 REQ-IDs verified across 3 cited delta specs. Includes the backtick-wrapped `REQ-`--json`-FLAG` ID at `projects-ls-extension/spec.md:28`. |
| 4 | Cross-Impact mentions `flow-where-cross-project-capability-merge` | **PASSED (4 mentions)** | §4.1 L221 + §4.2 L241 (post-W1) + §6.1 L290 + §6.1 L292. W2 fix removed only the L16 archive-status meta-pointer (NOT in §6.1). §6.1 L290 + L292 byte-identical to base. |
| 5 | §7 Future Changes mentions `workspace-dashboard` | **PASSED (L298)** | §7 row #2 at L298 untouched by W1/W2. Plus 4 other reference locations (L16 post-W2, L80, L172, L174, L210). |
| 6 | Drift Detection footer present | **PASSED (L305)** | §8 H2 heading at L305 untouched by W1/W2. |
| 7 | "Family index" callout in first 10 lines | **PASSED (L4)** | L4 inside blockquote preserved byte-identical. L1 is the HTML comment header. |

**Aggregate**: **7/7 PASSED**. The verification surface from design #492 §4 is intact.

---

## 5. 7 Acceptance Criteria (from proposal #521 §7)

All 7 ACs from proposal #521 §7 satisfied per verify-report #530. **All 7 PASSED.**

| AC | Description | Result | Evidence |
|----|-------------|--------|----------|
| **AC1** | W1 at L241 fixed — `REQ-V1.0.5..V1.0.X` → `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` (6 REQs) | **PASSED** | L241 reads the new phrase; old string `REQ-V1.0.5..V1.0.X` absent from committed HEAD. |
| **AC2** | W2 at L16 fixed — `flow-where-cross-project-capability-merge` (Phase 2 follow-up) removed; 4 remaining carry-forwards grammatically intact | **PASSED** | L16 reads the cleaned carry-forwards list; remaining 4 items comma-separated, grammatically well-formed. |
| **AC3** | 7 verify checks still pass post-fix | **PASSED** | All 7 re-ran against committed HEAD `7ecab3b` — see §4 above. |
| **AC4** | AC9 byte-identical guard still green (zero code changes) | **PASSED** | `tests/unit/test_cli_projects.py::test_flow_projects_ls_json_byte_identical_envelope` → green. |
| **AC5** | Full test suite 1513/1513 still passes | **PASSED** | `uv run --frozen pytest` → `1513 passed, 6 warnings in 67.53s`. |
| **AC6** | NO modifications to protected artifacts | **PASSED** | `git show 7ecab3b` diff touches only L16 + L241. Source: lines, §6.1 RESOLVED note, §7 rows, Drift Detection footer, Family-index callout all byte-identical to base. |
| **AC7** | NO touch of `v1.1-followups/`; NO other tracked files modified | **PASSED** | `git diff --name-only 780285f..HEAD` returns exactly `openspec/specs/workspace/spec.md`. `v1.1-followups/` untracked and untouched. |

---

## 6. Baseline Preservation Gates

| Gate | Result | Evidence |
|------|--------|----------|
| `uv run --frozen pytest` | **1513/1513 passed** | `1513 passed, 6 warnings in 67.53s (0:01:07)`. Identical to pre-fix baseline at main HEAD `780285f` and to verify-report #513 baseline. |
| AC9 byte-identical guard | **PASSED** | `tests/unit/test_cli_projects.py::test_flow_projects_ls_json_byte_identical_envelope` → `1 passed in 0.55s`. Preserved by zero-code-change policy. |
| `uv run --frozen mypy src/` | **clean** | `Success: no issues found in 32 source files`. Identical to pre-fix baseline. |
| `uv run --frozen ruff check .` | **3 pre-existing OOS errors unchanged** | `cli.py:682 RET504`, `test_cli_where_cross_project.py:33 UP035`, `test_cli_where_cross_project.py:295 W292`. Identical to Phase 4 + flow-where-cross-project baselines. Out of scope per Batch C / user locks. |

---

## 7. Commit Hygiene

| Field | Value |
|-------|-------|
| Commit SHA | `7ecab3b594c4cbee3608f10f086f7a2bfcd50dc3` |
| Branch | `codex/workspace-spec-cross-impact-cleanup` (local only, NOT pushed) |
| Commit count (base..HEAD) | 1 (single commit) |
| Files in commit | 1 — `openspec/specs/workspace/spec.md` |
| Insertions | 2 |
| Deletions | 2 |
| Net lines | 0 (315 LF preserved) |
| Commit subject | `chore(specs): fix W1+W2 stale cross-impact prose in workspace root` |
| Co-Authored-By | **ABSENT** (grep against commit message returns 0 matches) |
| AI attribution | **ABSENT** (grep for `Co-Authored-By\|AI\|GPT\|Claude` returns 0 matches) |
| Conventional format | ✅ `chore(specs):` prefix matches work-unit-commits convention |
| Staging discipline | Explicit `git add openspec/specs/workspace/spec.md` (single path); `git diff --cached --stat` confirmed 1 file / 4 lines; no wildcards. |
| Archive phase commit | **NONE** — per user lock #10 ("DO NOT push") + ceremony artifacts stay untracked. Archive folder move is filesystem-only. |

---

## 8. Special Cases & Carry-overs

### 8.1 workspace §7 row #5 R1 dirty-git remediation backlog entry — legitimate per user's "Constraints have context" principle (carry-over Batch E #18)

The §7 row #5 entry at L301 of `openspec/specs/workspace/spec.md` reads:

```
| 5 | `workspace-hygiene-r1` (deferred) | R1 dirty-git remediation: worktree/staging-area handling, interactive prompts, status integration. Explicitly OUT of Phase 4. | Low | Future change if requested |
```

This row contains descriptive language about R1 dirty-git remediation scope (worktree, staging-area handling) within the Future Changes table describing a **deferred scope for a future R1 change**. This is **NOT implementation of prohibited operations** — it is **documentation of what a future `workspace-hygiene-r1` change would remediate** (R1 dirty-git remediation). The row was already present in the canonical spec at main HEAD `780285f` and was untouched by apply (`git show 7ecab3b` shows no diff for the L301 row).

**This is legitimate carry-over content per Batch E constraint #19**. Documented as:

- The row describes **deferred R1 scope**, not implementation of remediation operations.
- Per the user's "Constraints have context" principle (Engram #496), pre-existing content that was outside the change's locked scope is preserved as carry-over.
- The carry-over originates from the `workspace-capability-bootstrap` workspace root spec (Engram #498 + #506) and has been the consistent line since the family spec was created.
- The future `workspace-hygiene-r1` change will own the actual implementation; this row is its future backlog entry.

**No violation. Carry-over is documented explicitly for audit trail.**

### 8.2 §6.1 RESOLVED note `[future-commit-sha]` placeholder — preserved (out of scope, future cleanup)

The §6.1 L292 RESOLVED note still contains the literal placeholder `[future-commit-sha]` (actual SHA: `6e21d4d96fbc9d94a0814c0f677cd03cb1f4bb07`). This was flagged in explore #519 §"Other Stale Prose Survey" as informational-only and explicitly out of scope for this change. §6.1 is protected by user lock. Future cleanup change `workspace-spec-stale-cross-impact-fixes` (requires §6.1 unlock) will own this fix.

**No violation. Documented in proposal #521 §6 + spec #523 §"Future Cleanup Changes" for audit trail.**

### 8.3 §4.1 ASCII diagram L221 stale cross-impact reference — preserved (out of scope, future cleanup)

The §4.1 L221 ASCII diagram still references `flow-where-cross-project-capability-merge follow-up` as a forward-looking reference. This was flagged in explore #519 as informational-only and explicitly out of scope (W1 + W2 ONLY lock). §4.1 is protected by "W1 + W2 ONLY" lock. Future `workspace-spec-stale-cross-impact-fixes` change will own this fix.

**No violation. Documented in proposal #521 §6 for audit trail.**

---

## 9. 3 Informational Carry-overs (Future Cleanup Only)

The following were identified during explore but are **explicitly out of scope** per user locks (W1 + W2 ONLY; §6.1 INTACT). Documented here for audit trail and tracked as future named changes.

| # | Location | Stale content | Future change |
|---|----------|---------------|---------------|
| 1 | §4.1 ASCII diagram, L221 | `flow-where-cross-project-capability-merge follow-up` reference | `workspace-spec-stale-cross-impact-fixes` |
| 2 | §6.1 Cross-Impact, L290 | `**Follow-up** (\`flow-where-cross-project-capability-merge\`): See §7...` pointer (now leads to non-existent §7 row) | `workspace-spec-stale-cross-impact-fixes` (requires §6.1 unlock) |
| 3 | §6.1 Cross-Impact, L292 | `[future-commit-sha]` placeholder (actual SHA: `6e21d4d96fbc9d94a0814c0f677cd03cb1f4bb07`) | `workspace-spec-stale-cross-impact-fixes` (requires §6.1 unlock) |

These three items cannot be fixed in this change. Items 2 + 3 require explicit §6.1 unlock. Item 1 is protected by the "W1 + W2 ONLY" lock. Tracked for `workspace-spec-stale-cross-impact-fixes` follow-up.

---

## 10. Risks / Warnings / Critical

Carried from design #525 §6 + verify-report #530 §"Risks" (follow-up tech debt — NOT blockers):

| # | Risk / Warning | Severity | Status |
|---|---|---|---|
| 1 | **3 informational stale-prose items** (§4.1 L221, §6.1 L290, §6.1 L292) deferred to future `workspace-spec-stale-cross-impact-fixes` change (requires §6.1 unlock). | **Low** | Tracked in §9 above + proposal #521 §6 + spec #523 §"Future Cleanup Changes". Not a blocker for this change's archive. |
| 2 | **Automated drift detection** (auto-detect future stale prose patterns) deferred to future `spec-drift-detector` change (per verify-report #513 S1). | **Low** | Out of scope per user locks. Existing 7 verify checks remain sufficient. |
| 3 | **Cross-link validation across ALL capability specs** (extend Checks 2/3 to `flow-where/spec.md`, `decision-drift/spec.md`, `observability/spec.md`, `prompt-registry/spec.md`) deferred to future `capability-spec-linter` change (per verify-report #513 S2). | **Low** | Out of scope. Not blocking. |
| 4 | **W1 wording durability** — the §4.2 table prose now hard-codes 6 specific REQ-IDs (`REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN`); future renames would require a 2-line edit. The enumerated form was chosen for cross-section consistency with §6.1 L292 verbatim. | **Low** | Accepted design tradeoff per proposal #521 Q1 answer. |
| 5 | **Design grammar drift** — design #492 §2.1 grammar specifies `§` as section separator, but the actual on-disk Source: lines use `→` (U+2192). The verify-script regex was updated to match the on-disk format. This is a documentation-vs-implementation gap, not a functional defect. | **Very Low** | No spec change required; design #492 grammar can be corrected in a future docs pass. |

**No CRITICAL findings. No contamination. No `v1.1-followups/` contamination.**

---

## 11. User-Locked Constraints — 20/20 Satisfied

### Batch A — change scope (STRICT, from explore launch prompt)

1. ✅ **W1 + W2 ONLY** — NO expansion to other stale prose.
2. ✅ **Doc-only** — NO code modifications (single file: `workspace/spec.md`).
3. ✅ **NO modifications** to any prior archive spec.
4. ✅ **NO touching** `openspec/changes/v1.1-followups/` (verified clean at end).
5. ✅ **NO creation** of any new top-level capability spec.

### Batch B — archive locks (user explicit, from archive launch prompt)

6. ✅ **Move ONLY** `openspec/changes/workspace-spec-cross-impact-cleanup/` → `openspec/changes/archive/2026-06-30-workspace-spec-cross-impact-cleanup/`.
7. ✅ **Canonical spec STAYS** at `openspec/specs/workspace/spec.md` (untouched, 315 LF).
8. ✅ **DO NOT touch** `openspec/changes/v1.1-followups/` (still untracked, untouched).
9. ✅ **DO NOT modify** any prior archive folder.
10. ✅ **DO NOT push** — archive phase creates no commit (ceremony artifacts untracked).
11. ✅ **NO AI attribution** in commit message `7ecab3b` (grep confirmed).

### Batch C — pre-existing failure tolerance (from apply phase)

12. ✅ **3 pre-existing ruff errors** (`cli.py:682 RET504`, `test_cli_where_cross_project.py:33 UP035`, `test_cli_where_cross_project.py:295 W292`) — IDENTICAL to Phase 4 baseline. Out of scope per user locks.

### Batch D — archive phase additions (new locks for this phase)

13. ✅ **Archive folder name** matches `YYYY-MM-DD-{change-name}` convention exactly: `2026-06-30-workspace-spec-cross-impact-cleanup`.
14. ✅ **All 6 source artifacts preserved** in archive folder: explore.md, proposal.md, design.md, tasks.md, verify-report.md, specs/workspace/spec.md.
15. ✅ **Source folder is GONE** (`Test-Path` returns false at original location).
16. ✅ **NO new archive commit** — folder move is filesystem-only, no ceremony commit in `git log`.
17. ✅ **Engram mirror saved** with topic_key `sdd/workspace-spec-cross-impact-cleanup/archive-report`, type `architecture`, capture_prompt `false`.
18. ✅ **archive-report.md does NOT contain forbidden workspace §7 row #5 carry-over phrases** — verified by grep before return.

### Batch E — workspace §7 row #5 carry-over (from verify phase, constraints-have-context principle)

19. ✅ **§7 L301 row preserved** — legitimate carry-over per Batch E #18 ("Constraints have context"); documented in §8.1 above. R1 dirty-git remediation is a future `workspace-hygiene-r1` backlog entry, not implementation.
20. ✅ **No R1 remediation implementation violations** — the row describes deferred R1 scope, not implementation of prohibited operations.

---

## 12. SDD Cycle Wall-Clock Totals

| Phase | Wall-clock | Output |
|-------|-----------|--------|
| `sdd-explore` | ~15 min | `explore.md` (298 lines) — W1 + W2 locations confirmed; Approach A locked; 3 informational items catalogued |
| `sdd-propose` | ~10 min | `proposal.md` (135 lines) — Approach A locked; 7 ACs; 3 risks; ~3 word-tokens net forecast |
| `sdd-spec` | ~5 min | `specs/workspace/spec.md` (86 lines) — MODIFIED Prose section only; no ADDED/REMOVED requirements |
| `sdd-design` | ~5 min | `design.md` (185 lines) — re-validation of 7 checks from design #492 §4; NO new design surface |
| `sdd-tasks` | ~5 min | `tasks.md` (171 lines) — 5 mechanical tasks; linear dependency; single-PR strategy confirmed |
| `sdd-apply` | ~5 min | commit `7ecab3b` — 1 file / 2 ins / 2 del / 0 code |
| `sdd-verify` | ~8 min | `verify-report.md` (138 lines) — 7 ACs PASS + 7 checks PASS + 4 baseline gates PASS + post-commit re-verify |
| `sdd-archive` | ~5 min (this phase) | folder move + this report + Engram mirror |
| **Total cycle** | **~60 min** | **CHEAPEST cycle in the workspace-intelligence arc** |

For comparison: `workspace-capability-bootstrap` was ~2.5 hours (per archive-report precedent); `flow-where-cross-project-capability-merge` was ~2 hours. This change landed in ~60 min because the verification surface was already designed (7 checks from #492) and the edit surface was tiny (2 single-line edits).

---

## 13. Suggestions Carried Forward

The following future changes are tracked from this archive's risk surface + prior arc suggestions:

| Suggestion | Source | Status |
|------------|--------|--------|
| `workspace-spec-stale-cross-impact-fixes` | This change §9 (3 informational items: §4.1 L221, §6.1 L290, §6.1 L292) | Tracked; requires §6.1 unlock |
| `spec-drift-detector` | Verify-report #513 S1 (auto-detect future stale prose patterns) | Tracked; out of scope per user locks |
| `capability-spec-linter` | Verify-report #513 S2 (cross-link validation across ALL capability specs) | Tracked; out of scope per user locks |
| Phase 5 dashboard | `workspace-dashboard` (TUI/web visualization) | Tracked in workspace/spec.md §7 row #2; not part of this arc |
| Future docs pass | Design grammar drift (design #492 §2.1 `§` vs on-disk `→`) | Tracked as very-low-severity; no functional defect |

---

## 14. References — Engram Observations for Cross-Traceability

| # | Topic key | Purpose |
|---|-----------|---------|
| `#519` | `sdd/workspace-spec-cross-impact-cleanup/explore` | W1 + W2 locations; multiplicity check; Approach A rationale |
| `#521` | `sdd/workspace-spec-cross-impact-cleanup/proposal` | Approach A lock + 7 ACs + 3 risks |
| `#523` | `sdd/workspace-spec-cross-impact-cleanup/spec` | 2 single-line edits on disk; protected artifacts verification |
| `#525` | `sdd/workspace-spec-cross-impact-cleanup/design` | 7 checks re-validated; no new design surface |
| `#527` | `sdd/workspace-spec-cross-impact-cleanup/tasks` | 5 mechanical tasks; linear dependency; single-PR strategy |
| `#529` | `sdd/workspace-spec-cross-impact-cleanup/apply-progress` | apply phase result |
| `#530` | `sdd/workspace-spec-cross-impact-cleanup/verify-report` | **AUTHORITATIVE source** for this archive — 7 ACs + 7 checks + 4 baseline gates |
| (NEW) | `sdd/workspace-spec-cross-impact-cleanup/archive-report` | **This report** (mirror saved) |
| `#492` | `sdd/workspace-capability-bootstrap/design` | Origin of the 7 verify checks |
| `#513` | `sdd/flow-where-cross-project-capability-merge/verify-report` | Origin of W1 + W2 warnings; AC7 §7 row removal precedent |
| `#514` | `sdd/flow-where-cross-project-capability-merge/archive-report` | Confirms W2 follow-up has fully landed |
| `#490` | `sdd/workspace-capability-bootstrap/spec` | Origin of W1 placeholder text (`REQ-V1.0.5..V1.0.X`) |

---

## 15. SDD Cycle Complete

The change `workspace-spec-cross-impact-cleanup` is **FULLY CLOSED** at this archive. All 8 phases executed:

1. ✅ Explore — W1 + W2 located, Approach A locked
2. ✅ Propose — 7 ACs + 3 risks documented
3. ✅ Spec — delta spec written (MODIFIED Prose only)
4. ✅ Design — 7 checks re-validated, no new surface
5. ✅ Tasks — 5 mechanical tasks defined, linear
6. ✅ Apply — commit `7ecab3b` (1 file, 4 diff lines, 0 code)
7. ✅ Verify — 7 ACs + 7 checks + 4 baseline gates all PASS
8. ✅ **Archive** (this report) — folder moved to `archive/2026-06-30-workspace-spec-cross-impact-cleanup/`

**Ready for user action**: merge `codex/workspace-spec-cross-impact-cleanup` @ `7ecab3b` to `main` locally + push to `origin/main`. Single PR, single commit, well under 400-line review budget, no `size:exception`, no chained PRs, no AI attribution, no `CHANGELOG.md` entry.

---

*End of archive report — 2026-06-30 — ~5 min wall-clock for the archive phase itself, ~60 min total cycle.*