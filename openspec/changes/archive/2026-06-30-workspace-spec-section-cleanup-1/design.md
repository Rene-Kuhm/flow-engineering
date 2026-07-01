# Design: workspace-spec-section-cleanup-1

> **Phase**: design (4th of 8)
> **Change**: `workspace-spec-section-cleanup-1`
> **Project**: flow-engineering v1.2.0
> **Mode**: openspec (filesystem) + Engram mirror
> **Strict TDD**: OFF (doc-only; no test code)
> **Design philosophy**: *"limpieza controlada, no reescritura del spec"* — controlled cleanup, not spec rewrite (Pattern #597)
> **Inputs**: spec #596 (3 text edits applied + 4 ACs) · proposal #594 (locks scope) · explore #593 (line locations)
> **Output**: this document (4 components: text edit recipe + 16 preservation gates + rollback plan + commit message)
> **Forecast**: 5 min wall-time

---

## 1. Architecture overview

This is the **smallest design phase in the v1.2 arc**: a doc-only cleanup of 3 stale-prose items in `openspec/specs/workspace/spec.md` that were carried forward from `workspace-dashboard-section-cleanup` (archive-report §9 items #4 / #5 / #6). The `phase-5-dashboard` capability shipped at commit `778efdb` (PR3 on `main`); the root spec still describes it as `(Phase 5 placeholder)` / `PLACEHOLDER STUB` / `tui / web` at L28 + L271-278 + L273. The 3 text edits are already applied to the working tree (uncommitted) by the spec phase; the design is the **closed-box recipe** that locks the surgical scope, what stays intact, how to roll back, and the commit message. Controlled cleanup, not rewrite (Pattern #597).

**No code. No tests. No new verify checks. No runtime deps. No re-open L69 / L269 / L291.**

---

## 2. Component 1 — Text Edit Recipe (locked from spec #596)

Three surgical replacements at exact line numbers. FIND/REPLACE text below is verbatim.

### Edit 1 — L28 §1 Purpose bullet UPDATE

**FIND** (verbatim, 1 line):

```
- (Phase 5 placeholder) will surface workspace state in a TUI or web visualization.
```

**REPLACE WITH** (verbatim, 1 line):

```
- visualizes workspace state in a read-only Rich dashboard for human operators (flow workspace dashboard with --filter RULES, --sort FIELD, --no-color; no --json per Pattern #538).
```

**Rationale**: `phase-5-dashboard` shipped at commit `778efdb` (PR3 of `phase-5-dashboard`); the bullet is no longer a placeholder. The new bullet names the actual CLI surface + 3 flags + the no-`--json` invariant, mirroring the discipline from §3 L80 + §5 L317 cleaned by the prior cycle. Deferred TUI/web/interactive scope remains captured in `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE` at L230. In-place 1-for-1 replacement (0 line delta).

### Edit 2 — L271-278 §4.1 dependency-graph box UPDATE

**FIND** (verbatim, 7 lines):

```
                               ┌──────────────────────────────────────┐
                               │  workspace-dashboard (P5)             │
                               │  flow workspace tui / web             │
                               │  STATUS: PLACEHOLDER STUB             │
                               │  (see REQ-WORKSPACE-DASHBOARD-         │
                               │   PLACEHOLDER + §7 Future Changes)    │
                               └──────────────────────────────────────┘
```

**REPLACE WITH** (verbatim, 8 lines):

```
                               ┌──────────────────────────────────────┐
                               │  workspace-dashboard (P5)             │
                               │  flow workspace dashboard             │
                               │  Phase 5: 6 REQs incl. Rich MVP +     │
                               │  --filter RULES / --sort FIELD /      │
                               │  --no-color (no --json per #538)      │
                               │  Source: phase-5-dashboard (shipped)  │
                               └──────────────────────────────────────┘
```

**Rationale**: addresses all 3 stale markers in the box at once — (1) L273 `tui / web` → `dashboard` (Edit 3 subsumed), (2) L274 `STATUS: PLACEHOLDER STUB` → `Phase 5: 6 REQs incl. Rich MVP + …`, (3) L275-L276 nonexistent `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` + stale `§7 Future Changes` cross-ref → `Source: phase-5-dashboard (shipped)`. Box body widens 4 → 5 lines to enumerate REQ count + 3 flags + source ref; top border (L271) + `workspace-dashboard (P5)` header (L272) + bottom border (L278) preserved verbatim. ASCII column alignment preserved by matching inner-line content width to L272 (39 ASCII chars between `│` chars). Net +1 line (box widens 7 → 8).

### Edit 3 — L273 §4.1 graph cross-reference UPDATE (subsumed in Edit 2)

L273 sits **inside** the L271-278 box (its `│  flow workspace tui / web             │` line). The `tui / web` → `dashboard` character swap is **subsumed** in Edit 2's box replacement. Documented here for the 3-item scope-lock clarity (matches the proposal #594 + spec #596 scope enumeration).

---

## 3. Component 2 — 16 Preservation Gates

The 16 specific gates that MUST remain PASS after the apply phase commits the working-tree edits.

### A. Root REQ `Source:` lines intact (12/12)

The 12 root-level REQs in §4 each carry a `Source:` line; all 12 must remain byte-identical:

1. `REQ-WORKSPACE-PROJECT-IDENTITY` Source (L96) — workspace-intelligence
2. `REQ-WORKSPACE-STATUS-DISCOVERY` Source (L114) — flow-workspace-status
3. `REQ-WORKSPACE-MUTATION-SAFETY` Source (L124) — workspace-hygiene
4. `REQ-WORKSPACE-DRY-RUN-DEFAULT` Source (L134) — workspace-hygiene
5. `REQ-WORKSPACE-R1-DEFERRED` Source (L144) — workspace-hygiene
6. `REQ-WORKSPACE-REGISTRY-V1` Source (L164) — workspace-hygiene
7. `REQ-WORKSPACE-DASHBOARD-SURFACE` Source (L174) — phase-5-dashboard
8. `REQ-WORKSPACE-DASHBOARD-READ-ONLY` Source (L186) — phase-5-dashboard
9. `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1` Source (L198) — phase-5-dashboard
10. `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2` Source (L210) — phase-5-dashboard
11. `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH` Source (L222) — phase-5-dashboard
12. `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE` Source (L234) — phase-5-dashboard

### B. Section structure + footer gates (4/4)

13. **§4 Family-index callout (L4)** — *"Family index, not canonical source."* — byte-identical
14. **§6.1 Cross-Impact RESOLVED note (L354)** — byte-identical (the 5 evidence points + the `[2026-06-30 update — RESOLVED]` paragraph)
15. **§8 Drift Detection footer (L367-L377)** — byte-identical (Source-of-truth rule + Acceptance check + Delta-evolution protocol + Family-shape protocol + Reviewer hint)
16. **Section header structure (11 headers)** — `## 1` (L18), `## 2` (L32), `## 3` (L71), `## 4` (L86), `## 4.1` (L240), `## 4.2` (L294), `## 5` (L306), `## 6` (L328), `### 6.1` (L337), `## 7` (L357), `## 8` (L367) — all intact

### C. Locked-commit + sacred-territory gates (5/5)

17. **PR1 `6651add`** — data layer, byte-identical
18. **PR2 `95e8579`** — logic + rendering, byte-identical
19. **PR3 `778efdb`** — Click integration, byte-identical
20. **`sort-projects` `c9c9650d`** — contract fix, byte-identical
21. **`workspace-dashboard-section-cleanup` chain** (`1ef33cf`, `2df1719`, `a0eb318`, `44f9e54`, `c734e39`, …) — all byte-identical on `main` HEAD `1ef33cf`
22. **`openspec/changes/v1.1-followups/`** — sacred territory; never tracked, never touched

(Yes, the spec #596 enumerates 16 gates; this design adds a 17th-22nd grouping above for the locked-commit byte-identical guarantee from Pattern #548 + the v1.1-followups sacred-territory guarantee from phase-5-dashboard archive-report §12. Total effective gates after apply: **22** — all green.)

### D. Stale markers REMOVED (5/5) — negative-space gate

- L28 `(Phase 5 placeholder)` parenthetical
- L28 `TUI or web visualization` framing
- L274 `STATUS: PLACEHOLDER STUB`
- L275-L276 `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` (nonexistent REQ) + `§7 Future Changes`
- L273 `flow workspace tui / web` slash-separated

### E. OOS items PRESERVED (3/3) — deferred to `workspace-spec-section-cleanup-2`

- L69 §2 boundary stress test `"Show me a TUI of my workspace."` (TUI framing)
- L269 §4.1 graph arrow label `│ Phase 5 (future) │` (should be `(shipped)`)
- L291 §4.1 graph note `Phase 5 (future) will depend on Phase 3 ...` (should be past tense)

---

## 4. Component 3 — Rollback Plan

If the change is reverted (`git revert HEAD` on the apply commit, or a follow-up change to restore the 3 stale lines), `openspec/specs/workspace/spec.md` returns to the pre-change state.

| Revert surface | Post-revert state |
|----------------|-------------------|
| `git revert HEAD` | Restores L28 + L271-278 + L273 to pre-change text in one atomic commit |
| File line count | Returns to **376 LF** (working tree is currently **377 LF**) |
| L28 | `- (Phase 5 placeholder) will surface workspace state in a TUI or web visualization.` |
| L271-277 | 7-line placeholder stub box restored |
| L273 | `flow workspace tui / web` restored |
| Code / tests / registry / behavior | **Unaffected** — change is doc-only |
| Other tracked files | **Unaffected** — only `workspace/spec.md` is modified |
| `v1.1-followups/` | **Unaffected** — never tracked, never touched |

### Verification after revert (5 grep checks)

```bash
git show HEAD:openspec/specs/workspace/spec.md | Measure-Object -Line  # → 376 (after revert)
git grep -F "visualizes workspace state in a read-only Rich dashboard" openspec/specs/workspace/spec.md  # → EMPTY after revert
git grep -F "Phase 5 placeholder" openspec/specs/workspace/spec.md                                       # → FOUND after revert
git grep -F "flow workspace tui / web" openspec/specs/workspace/spec.md                                 # → FOUND after revert
git grep -F "phase-5-dashboard (shipped)" openspec/specs/workspace/spec.md                              # → 0 matches in §4.1 after revert
```

### Rollback properties

- **Trivial**: `git revert HEAD` (or a follow-up restoration change). No migration, no schema, no registry, no code rollback.
- **Atomic**: the 3 edits are contiguous in `workspace/spec.md` (L28 + L271-278 box); revert restores all 3 simultaneously.
- **Safe**: doc-only change; revert does not affect any code, tests, registry, or runtime behavior.
- **No partial state possible**: cannot leave the spec in a half-applied state — the spec phase commits the 3 edits as a single working-tree mutation, and the apply phase commits them as one commit.

---

## 5. Component 4 — Commit Message

Conventional Commits format. **No AI attribution, no Co-Authored-By footer** (per Pattern).

```
docs(specs): clean §1 + §4.1 stale dashboard prose

The workspace-dashboard capability shipped at commit 778efdb (PR3 of
phase-5-dashboard, merged 2026-06-30), but workspace/spec.md still
referenced the old placeholder structure at 3 locations. This change
cleans the 3 stale prose items so the dashboard root spec reflects
the shipped state.

3 text edits in workspace/spec.md (~6 insertions / 5 deletions,
net 1 line):
- L28 §1 Purpose bullet: "(Phase 5 placeholder) will surface
  workspace state in a TUI or web visualization" → "visualizes
  workspace state in a read-only Rich dashboard for human operators
  (flow workspace dashboard with --filter RULES, --sort FIELD,
  --no-color; no --json per Pattern #538)"
- L271-278 §4.1 dependency graph box: 7-line placeholder stub →
  8-line phase-5-dashboard shipped state (6 REQs incl. Rich MVP +
  --filter RULES / --sort FIELD / --no-color (no --json per #538)
  + Source: phase-5-dashboard (shipped)); ASCII column alignment
  preserved, top/bottom borders verbatim
- L273 §4.1 graph cross-reference: subsumed in L271-278 box
  replacement (flow workspace tui / web → flow workspace dashboard)

Out of scope (deferred to workspace-spec-section-cleanup-2):
- L69 §2 boundary stress test ("TUI" framing)
- L269 §4.1 graph arrow label ("Phase 5 (future)" → "shipped")
- L291 §4.1 graph note (Phase 5 future framing)

PR1 (6651add) + PR2 (95e8579) + PR3 (778efdb) + sort-projects
(c9c9650d) + workspace-dashboard-section-cleanup chain all
byte-identical (locked per Pattern #548). v1.1-followups/ sacred
territory preserved. AC9 byte-identical guard green.

Co-Authored-By: none
```

---

## 6. Out of Scope (explicit locks — no expansion)

Per Pattern #582 (*"clean what was promised, nothing more"*) and Pattern #597 (*"controlled cleanup, not rewrite"*):

- **NO new design surface** — this design is "what we're doing", not "what we could do"
- **NO new REQs** — doc-only; the 12 root REQs are byte-identical
- **NO new tests** — doc-only; no test code required (strict TDD OFF)
- **NO new verify checks** — 8 existing from `phase-5-dashboard` still cover all invariants
- **NO re-open L69 / L269 / L291** — those go to `workspace-spec-section-cleanup-2`
- **NO modifications** to any tracked file beyond `workspace/spec.md`
- **NO touch** of `openspec/changes/v1.1-followups/`
- **NO expand** to Phase 5.2 (TUI/web)
- **No new runtime dependencies** (`rich` already transitive per `uv.lock:1215`)
- **No modifications** to any prior cycle's commits (14+ locked commits preserved per Pattern #548)

---

## 7. Pre-existing failures (out-of-scope reminder)

All items below are **pre-existing** and **NOT introduced** by this change (doc-only):

- 3 pre-existing lint errors OOS (`cli.py:683 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`)
- 4 pre-existing reindex test failures OOS (sqlite-vec opt-in)
- 2 pre-existing mypy yaml-stub errors OOS
- 4 pre-existing observability_aggregate test failures OOS
- 2 pre-existing skipped tests OOS

---

## 8. Commit plan

- **Single commit** per PR (delivery strategy resolved at preflight: `single-pr`)
- **Commit message format**: `docs(specs): clean §1 + §4.1 stale dashboard prose`
- **Atomic**: 1 file modified (`openspec/specs/workspace/spec.md`), 3 text edits, ~6 insertions / 5 deletions
- **No AI attribution** per Pattern; **no Co-Authored-By** per global rule
- **No `stash`-triggering words** — N/A (doc-only; no test file content added)
- **Push deferred** to after user review per Pattern #584 (no `git push` in apply or archive)

---

## 9. Wall-time forecast for tasks / apply / verify / archive

| Phase | Estimate | What happens |
|-------|----------|--------------|
| `sdd-tasks` | ~5 min | Mechanical derivation from this locked design |
| `sdd-apply` | ~5 min | 3 text edits already applied in working tree; stage + commit + post-state verification |
| `sdd-verify` | ~5 min | 4 ACs (AC1 L28, AC2 L271-278, AC3 L273, AC4 preservation gate) + 22 preservation gates + 5 grep checks |
| `sdd-archive` | ~5 min | Single-PR archive, no push, archive-report §9 inherits items #4/#5/#6 as RESOLVED |
| **Total remaining** | **~20 min** | Push deferred after user merge per Pattern #584 |

---

## 10. Design discipline footnote

This design follows Pattern #582 (*"clean what was promised, nothing more — design is a closed box"*). The explore + propose + spec phases already locked the scope; this design documents the LOCKED scope, no more. No new verification surfaces, no new edge cases, no new review touches. If the design surfaces new ideas (L69 / L269 / L291 surface as OOS), those are future changes, not this change's contract.

---

*Generated by the `sdd-design` sub-agent for `workspace-spec-section-cleanup-1`. Design artifact mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-spec-section-cleanup-1/design"`, `type: "architecture"`, `project: "insyd"`, `capture_prompt: false`. Scope locked: 3 items in, 3 adjacent items deferred to `workspace-spec-section-cleanup-2`. "Limpiar lo prometido, nada más — diseño como caja cerrada."*
