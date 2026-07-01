# Explore: workspace-spec-section-cleanup-2

> **Phase**: explore (1st of 8)
> **Change**: `workspace-spec-section-cleanup-2`
> **Project**: flow-engineering v1.2.0
> **Mode**: openspec (filesystem) + Engram mirror
> **Goal**: confirm exact line locations + proposed fixes for the 3 stale-prose items in `openspec/specs/workspace/spec.md` carried forward from `workspace-dashboard-section-cleanup` archive-report §9 (items #4/#5/#6 — DEFERRED to -1, then DEFERRED again to -2 by the prior cycle's design #598 gate E).
>
> User framing: *"Es el mismo caso: doc-only, chico, pero mantenemos OpenSpec + 400 líneas para que no se infle."* — same discipline as `-1` (~46 min actual) and `-0` (~45 min actual).

## Goal

Identify **exact line locations** + **proposed fixes** for the 3 stale-prose items in `workspace/spec.md` that were explicitly OUT OF SCOPE during both prior cycles:

1. `workspace-dashboard-section-cleanup` (commit `a0eb318`, merged `1ef33cf`) — deferred L69/L269/L291 as future cleanup debt per design #583 §6.
2. `workspace-spec-section-cleanup-1` (commit `43e76ed`, merged `42cfffa`) — kept deferring them per proposal #594 §2 ("Out of Scope") + design #598 Component 3 gate E ("OOS items PRESERVED (3/3) — deferred to `workspace-spec-section-cleanup-2`").

This change **picks up the deferred debt** and closes the loop on the §2 boundary stress test + §4.1 graph arrow label + §4.1 graph note.

**Builds on**: engram #577 (explore-0) + #581 (spec-0) + #583 (design-0) + #586 (apply-0) + #593 (explore-1) + #594 (proposal-1) + #596 (spec-1) + #598 (design-1) + #600 (tasks-1) + `workspace-spec-section-cleanup-1` archive-report.

## Scope

### User-locked IN scope (must-fix — 3 items)

1. **`workspace/spec.md §2 boundary stress test` — L69** — stale `"Show me a TUI of my workspace."` (TUI framing; delivered surface is Rich MVP)
2. **`workspace/spec.md §4.1 graph arrow label` — L269** — stale `│ Phase 5 (future) │` (should be `Phase 5 (shipped)` since phase-5-dashboard is on `main`)
3. **`workspace/spec.md §4.1 graph note` — L291** — stale `- Phase 5 (future) will depend on Phase 3 ...` (should be past tense — the dependency is historical fact)

### Strict OUT of scope (locks)

- NO code changes (doc-only)
- NO new tests (doc-only)
- NO new verify checks (8 existing from phase-5-dashboard still cover all invariants)
- NO modifications to any prior cycle's commits (all 14+ locked per Pattern #548)
- NO touch of `openspec/changes/v1.1-followups/` (sacred territory)
- NO expansion to Phase 5.2 (TUI/web — deferred per REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE)
- NO `stash`-triggering words (N/A — doc-only)
- NO modifications to any tracked file beyond `openspec/specs/workspace/spec.md`
- NO amend of any locked commit

### Adjacent stale items discovered (NOT in scope — surface only)

- **L299** §4.2 row 1 trigger: `Phase 5 dashboard ships | New sub-capability added` — already-actioned trigger copy; semantically still valid as a meta-rule (and the action literally happened). **Surface only.**

## L69 §2 boundary stress test — Investigation (CRITICAL)

**Current (L69, verbatim):**

```
| "Show me a TUI of my workspace." | ✅ YES (Phase 5) | Project dashboard |
```

Sits as the 6th and final row in the §2 boundary stress tests table (L62-L69). The 5 prior rows (L64-L68) describe scenarios that are still meaningful — project discovery, status aggregation, hygiene operations, cross-project search delegation. The TUI framing on L69 was a placeholder for "future TUI"; phase-5-dashboard shipped with Rich MVP, not TUI (per REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE at L230 — TUI/web deferred to Phase 5.2).

**Stale markers:**
- `"Show me a TUI of my workspace."` — `TUI` references a future capability that is explicitly deferred to Phase 5.2; Rich MVP is what shipped.
- The `✅ YES (Phase 5)` and `Project dashboard` columns remain accurate (the boundary decision is unchanged: a dashboard view belongs in workspace, not flow-where).

**Proposed fix (RECOMMENDED — single-word swap, minimal disruption):**

```
| "Show me a Rich dashboard of my workspace." | ✅ YES (Phase 5) | Project dashboard (Rich MVP) |
```

**Rationale:** Single substitution (`a TUI` → `a Rich dashboard`) preserves the boundary-stress-test nature of the bullet — "does a view-of-workspace question belong in workspace-family?" — while reflecting the actual shipped surface (Rich MVP). The `(Rich MVP)` parenthetical in the right column distinguishes it from a hypothetical TUI/web future; uses the canonical wording already established in §3 L80 + §4.1 L271-278 box. Net effect: 1 line, in-place replacement (0 line delta).

**Alternatives:**

| # | Approach | Pros | Cons | Effort |
|---|----------|------|------|--------|
| A | **Replace** with `"Show me a Rich dashboard of my workspace."` | Minimal change; preserves boundary-stress nature; matches prior-cycle canonical wording | None | **LOW (recommended)** |
| B | Replace with `"Show me a dashboard of my workspace."` | Shorter; matches §4.1 L273 wording (`flow workspace dashboard`) | Less specific about Rich; could be confused with hypothetical future TUI | LOW |
| C | Replace with `"Show me a summary of my workspace."` | Removes "TUI/dashboard" wording entirely | Loses the visualization-stressor intent; overlaps with P3 (status) | LOW |
| D | **Remove** bullet entirely (renumber to 5 rows) | Eliminates stale marker entirely; reduces surface | Loses visualization-boundary stressor (defensive boundary test); smaller §2 table | MEDIUM (semantic) |

**Recommended**: Option A — single-word swap, maximum preservation, full canonical alignment.

## L269 §4.1 graph arrow label — Investigation (CRITICAL)

**Current (L269, verbatim):**

```
                                                  │ Phase 5 (future)
```

Sits in lower-right of ASCII dependency graph (L240-L291), as the label on the arrow connecting the P4 box (L262-L267, `workspace-hygiene`) to the P5 box (L272-L278, `workspace-dashboard`). The label is centered between two `│` characters in the graph column.

**Stale marker:** `Phase 5 (future)` — phase-5-dashboard shipped at commit `778efdb` (merged `1ef33cf` on 2026-06-30; workspace-spec-section-cleanup-1 merged `42cfffa` on 2026-06-30; both on `main` HEAD `42cfffa`). The arrow label no longer reflects the actual state.

**Proposed fix (RECOMMENDED — minimal 3-character substitution):**

```
                                                  │ Phase 5 (shipped)
```

**Rationale:** Single substitution `(future)` → `(shipped)`. Both strings are 16 characters wide; ASCII column alignment preserved exactly. Uses canonical wording already established in §1 L24-L28 + §3 L80 + §4.1 L277 box (`Source: phase-5-dashboard (shipped)`). Net effect: 1 line, in-place replacement (0 line delta).

**Alternatives:**

| # | Approach | Pros | Cons | Effort |
|---|----------|------|------|--------|
| A | **Replace** `(future)` → `(shipped)` | Minimal change; matches canonical wording elsewhere in file | None | **LOW (recommended)** |
| B | Replace `(future)` → `(delivered 2026-06-30)` | Adds date context | Noisy; breaks alignment; date may age out | LOW |
| C | Replace `(future)` → `(✅)` | Visually scannable | Inconsistent with other arrow labels (which use words); not established convention | LOW |
| D | **Remove** the label entirely | Eliminates stale marker | Loses the "phase flow" visual cue; breaks ASCII symmetry | MEDIUM (semantic) |

**Recommended**: Option A — minimal substitution, full alignment preservation.

## L291 §4.1 graph note — Investigation (CRITICAL)

**Current (L291, verbatim):**

```
- Phase 5 (future) will depend on Phase 3 (read aggregation) + Phase 4 (registry).
```

Sits as the 3rd note in the §4.1 "no cycles in the family" bullet list (L290-L292):

```
- Phase 3 depends on Phase 1 helper (`_detect_project_markers`, read-only).
- Phase 4 depends on Phase 3 registry gating + Phase 1 helper (read-only).
- Phase 5 (future) will depend on Phase 3 (read aggregation) + Phase 4 (registry).
```

**Stale markers:**
- `(future)` parenthetical — phase-5-dashboard shipped; no longer future
- `will depend` — future-tense verb; the dependency is current fact (and historical fact, since the dashboard already consumes DS1+DS2 per `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1/DS2` at L198/L210)

**Proposed fix (RECOMMENDED — drop `(future)` + past-tense verb):**

```
- Phase 5 depended on Phase 3 (read aggregation) + Phase 4 (registry).
```

**Rationale:** Switches the verb to simple past tense (`depended`); drops the `(future)` parenthetical. Two semantic changes for one stale marker: (1) `Phase 5` is no longer future (it's shipped), so the parenthetical has no semantic load; (2) the dependency itself was a precondition at ship-time — past-tense framing is accurate. The resulting line matches the style of the prior 2 bullets (which use present tense `depends` for ongoing dependencies); however, L291 uniquely describes a SHIPPED phase, so past tense is the cleanest framing for "this is what happened". Net effect: 1 line, in-place replacement (0 line delta).

**Alternatives:**

| # | Approach | Pros | Cons | Effort |
|---|----------|------|------|--------|
| A | **Replace** with `Phase 5 depended on Phase 3 (read aggregation) + Phase 4 (registry).` | Past-tense; clean; explicit about shipped state | Different tense than prior 2 bullets (which use `depends`) | **LOW (recommended — matches user's "past tense" framing)** |
| B | Replace with `Phase 5 depends on Phase 3 (read aggregation) + Phase 4 (registry).` | Matches prior 2 bullets' present-tense style | Drops the "shipped" semantic; ambiguity about whether the dep is current or historical | LOW |
| C | Replace with `Phase 5 depended on Phase 3 (read aggregation) + Phase 4 (registry) — shipped.` | Past-tense + shipped marker | Noisy; "shipped" is already implied by "depended" + current file state | LOW |
| D | **Remove** the note entirely | Eliminates stale marker; one less line | Loses the explicit Phase 5 dependency documentation; the prior 2 bullets remain for symmetry | MEDIUM (semantic) |

**Recommended**: Option A — past tense, minimal noise, matches user's explicit "past tense" instruction.

## Cross-Reference with Prior Archive

Per `workspace-spec-section-cleanup-1` archive-report §9 (Carry-Over Follow-Ups) — these items were specifically locked as DEFERRED:

> "Out of scope (deferred to `workspace-spec-section-cleanup-2`):
> - L69 §2 boundary stress test (`"TUI"` framing)
> - L269 §4.1 graph arrow label (`Phase 5 (future)` → `shipped`)
> - L291 §4.1 graph note (Phase 5 future framing)"

**Confirmation:** Identical to user's launch prompt + identical to the prior cycle's design #598 Component 3 gate E (negative-space gate: "OOS items PRESERVED (3/3)"). The 3 items have NOT regressed since the prior cycle's archive. The prior cycle's cycle-cleanup #598 design correctly preserved them as future cleanup debt; this change picks them up.

**Already addressed by prior cycles (NOT in this change — preservation gates):**
- L73 §3 intro (`3 confirmed + 1 placeholder` → `4 confirmed`) — by `-0` (#583 design §2.1)
- L80 §3 row 5 (placeholder → shipped) — by `-0` (#583 design §2.2)
- L317 §5 row (`tui (future)` → `dashboard` with flags) — by `-0` (#583 design §2.3)
- L360 §7 row #2 (REMOVED + renumbered) — by `-0` (#583 design §2.4)
- L28 §1 Purpose bullet (`(Phase 5 placeholder)` → Rich dashboard state) — by `-1` (#598 design Edit 1)
- L271-278 §4.1 dependency-graph box (`PLACEHOLDER STUB` → `phase-5-dashboard (shipped)`) — by `-1` (#598 design Edit 2, subsuming L273)

This change **closes the loop** on §2 + §4.1 residue that both prior cycles correctly did not touch.

## Open Questions (3-5 with tradeoffs)

### Q1 (CRITICAL) — L69 fix: REPLACE / REMOVE / alternate wording?

- **Option A (RECOMMENDED)**: `"Show me a Rich dashboard of my workspace."` + `(Rich MVP)` right-column annotation. **Best balance**: minimal change; preserves boundary-stress test; canonical wording alignment.
- **Option B**: `"Show me a dashboard of my workspace."` — drops "Rich" qualifier; cleaner but less specific.
- **Option D**: REMOVE bullet entirely — strongest cleanup, but loses the visualization-boundary stressor (and the §2 table becomes 5 rows instead of 6, breaking the existing rhythm).

### Q2 (CRITICAL) — L269 fix: REPLACE / remove label / expand date?

- **Option A (RECOMMENDED)**: `(future)` → `(shipped)`. **Best**: minimal; column-aligned; matches canonical wording.
- **Option C**: `(future)` → `(✅)` — visually scannable but inconsistent with other arrow labels.
- **Option D**: REMOVE label — eliminates stale marker but breaks visual cue.

### Q3 (CRITICAL) — L291 fix: past-tense / present-tense / shipped-suffix?

- **Option A (RECOMMENDED)**: Past tense `Phase 5 depended on Phase 3 (read aggregation) + Phase 4 (registry).` — matches user's explicit "past tense" instruction.
- **Option B**: Present tense `Phase 5 depends on Phase 3 (read aggregation) + Phase 4 (registry).` — matches style of prior 2 bullets but loses the "shipped" semantic.
- **Option C**: Past tense + `— shipped` suffix — past-tense + explicit shipped marker; slightly noisier.

### Q4 (EXPANSION RISK) — Address adjacent stale items in the same change?

- **L299** §4.2 row 1 trigger: `Phase 5 dashboard ships | New sub-capability added` — already-actioned trigger copy. The text literally describes an event that has happened (phase-5-dashboard shipped), but the column is structured as a "rule that triggers when X happens" — so it remains semantically valid as a meta-rule, even though X has already happened.
- **RECOMMEND: do NOT expand.** User said "doc-only, chico". L299 is borderline (already-actioned trigger) but technically still correct as a forward-looking rule structure. Surface in propose for user opt-in/out.

### Q5 (FORECAST) — Run full 8-phase SDD pipeline, or skip spec phase for doc-only?

- **RECOMMEND: full pipeline.** Matches prior cycles' structure (`-0` actual ~46 min, `-1` actual ~46 min). Small but auditable; 8 phases fit within user's 30-45 min forecast.

## Tech Debt

- **Size**: ~5-10 LOC text edits (L69 single-line replacement + L269 single-line replacement + L291 single-line replacement; net 0 lines). Well under 400-line single-PR budget.
- **Strategy**: Single PR (user-locked at preflight: `single-pr`).
- **Strict TDD**: OFF (doc-only).
- **No new tests, no new verify checks.**
- **Queue position**: FOURTH queued cleanup change in v1.2 arc, after `sort-projects` + `workspace-dashboard-section-cleanup` + `workspace-spec-section-cleanup-1`. After this change, the `workspace-dashboard-section-cleanup` carry-over debt is **fully retired**.
- **Locked commits**: 14+ commits preserved byte-identical on `main` HEAD `42cfffa` per Pattern #548.
- **v1.1-followups/**: sacred territory, untracked, never touched (confirmed by `-1` archive-report §6 gate #9).

## Forecast (wall-clock)

| Phase | Estimate |
|-------|----------|
| explore (this) | ~5 min (DONE) |
| propose | ~3 min |
| spec | ~3 min |
| design | ~5 min |
| tasks | ~3 min |
| apply | ~5 min (3 single-line edits + 1 commit) |
| verify | ~5 min (3 ACs + preservation gates) |
| archive | ~3 min |
| **TOTAL** | **~30 min** (matches user's 30-45 min forecast; same discipline as `-1` per Pattern #555) |

## Verdict (recommended approach)

**PROCEED with the 3 user-locked text-only edits as a single-PR doc-only cleanup.**

- L69: REPLACE `TUI` → `Rich dashboard` (single-word swap, retains boundary-stress nature)
- L269: REPLACE `(future)` → `(shipped)` (single 3-character swap, preserves column alignment)
- L291: REPLACE `(future) will depend` → `depended` (drops parenthetical + past-tense verb)

All 3 items are unambiguous — fixes are mechanical; wordings derived from the canonical `phase-5-dashboard` archive references already established by the prior cycles (§1 L28 + §3 L80 + §4.1 L271-278 box).

**Cycle profile**: smallest in v1.2 arc; 3 mechanical edits; ~5-10 LOC; single PR; well under 400-line budget; LOW risk.

## Next SDD Phase

**sdd-propose** — write `proposal.md`:
- **Why**: 4th cleanup cycle to retire `workspace-dashboard-section-cleanup` carry-over debt (L69 + L269 + L291); closes the loop on §2 + §4.1 residue
- **Scope**: 3 user-locked text-only edits; ~5-10 LOC; ~0 net lines
- **Approach**: REPLACE / REPLACE / REPLACE (in that order)
- **Non-goals**: NO code, NO tests, NO verify checks, NO v1.1-followups touch, NO locked-commit amend, NO expansion to L299 (surface for user opt-out)
- **Acceptance**: 3 manual re-read checks (L69 + L269 + L291)
- **Rollback**: `git revert HEAD` — single-commit atomic rollback

## Risks

| # | Severity | Risk | Mitigation |
|---|----------|------|------------|
| R1 | LOW | Expansion creep at propose (user may ask to also fix L299) | Surface in propose as Open Question; user opt-in/out; default = no expansion |
| R2 | LOW | L269 ASCII alignment drift after `(future)` → `(shipped)` substitution | Both strings are 16 chars wide — verified byte-identical column count; visual re-read at apply |
| R3 | LOW | L69 right-column `(Rich MVP)` parenthetical could be perceived as verbose | Verbose is intentional — distinguishes from hypothetical Phase 5.2 TUI; matches §3 L80 + §4.1 box discipline |
| R4 | LOW | L291 past-tense `depended` may differ from prior 2 bullets' present-tense `depends` style | Acceptable: L291 uniquely describes a SHIPPED phase; past tense is accurate for historical fact. Style asymmetry is informative. |
| R5 | NEGLIGIBLE | v1.1-followups/ accidental touch | Sacred territory; preservation gate in design |
| R6 | NEGLIGIBLE | L73/L80/L317 touched accidentally (already fixed by `-0`) | Pre-flight check at apply: confirm L73 + L80 + L317 already reflect shipped state; this change only touches L69 + L269 + L291 |

---

*This explore artifact is mirrored from `openspec/changes/workspace-spec-section-cleanup-2/explore.md`. Generated by `sdd-explore` sub-agent for flow-engineering v1.2.0, project `insyd` in Engram. Build target: doc-only cleanup, single PR, ~30 min wall-time forecast, LOW risk profile. Out of scope locked: NO code, NO new tests, NO new verify checks, NO touch of v1.1-followups, NO expansion to Phase 5.2, NO expansion to L299.*