# Explore: workspace-spec-section-cleanup-1

> **Phase**: explore (SDD pipeline)
> **Change**: `workspace-spec-section-cleanup-1`
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Goal**: confirm exact line locations + proposed fixes for the 3 stale-prose items in `openspec/specs/workspace/spec.md` that were carried forward from the `workspace-dashboard-section-cleanup` cycle as future cleanup debt (per its archive-report §9 carry-over list, items #4/#5/#6).

User framing: *"Esto debería ser otro ciclo corto, tipo 30–45 min."* — quick exploration, minimal fix, doc-only.

## Goal

Identify **exact line locations** and **proposed fixes** for the 3 stale-prose items in `workspace/spec.md` that were explicitly OOS during the `workspace-dashboard-section-cleanup` cycle (#577 explore, #579 proposal, #581 spec, #583 design, #586 apply-progress) and carried forward to this dedicated follow-up change. The phase-5-dashboard capability shipped at commit `778efdb` on `main` (post-merge at `1ef33cf`); the root `workspace/spec.md` still references it as a placeholder in 3 locations that the prior cleanup cycle correctly did not touch.

**Builds on**: prior engram observations #577 (explore) + #581 (spec) + #583 (design) + #586 (apply-progress) + the prior change's `archive-report.md` §9 (carry-over follow-ups #4/#5/#6).

## Scope

### User-locked IN scope (must-fix)

1. **`workspace/spec.md §1 Purpose bullet` — L28** (stale `Phase 5 placeholder` + `TUI or web visualization` reference)
2. **`workspace/spec.md §4.1 dependency-graph box` — L271-L277** (stale `STATUS: PLACEHOLDER STUB` + `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` reference)
3. **`workspace/spec.md §4.1 graph cross-reference` — L273** (stale `flow workspace tui / web` — no TUI shipped; only `dashboard`)

### Informational / adjacent items discovered during investigation (NOT in scope, surface only)

These were NOT in the user's locked scope but are textually adjacent to the 3 locked items. Flagging them as Open Questions for the orchestrator to decide whether to expand this change (the user said "doc-only, chico", so the recommended posture is **NOT to expand**).

- **L69** §2 boundary stress test: `"Show me a TUI of my workspace."` — uses "TUI" framing; delivered surface is Rich MVP, not TUI. Borderline stale wording in a stress-test example.
- **L269** §4.1 graph arrow label: `│ Phase 5 (future) │` — should read `Phase 5 (shipped)` since `phase-5-dashboard` is on `main`.
- **L291** §4.1 graph note: `- Phase 5 (future) will depend on Phase 3 (read aggregation) + Phase 4 (registry).` — should read in past tense since the dependency is realized.
- **L299** §4.2 row 1 trigger: `Phase 5 dashboard ships | New sub-capability added` — already-actioned trigger copy; arguably stale, but it is a meta-rule for future similar events and is still semantically valid.

### Strict OUT of scope (locks)

- NO code changes (all paths under `src/`)
- NO new tests
- NO new verify checks (8 existing from phase-5-dashboard still cover)
- NO modifications to locked commits (`1ef33cf`, `2df1719`, `a0eb318`, `44f9e54`, `c734e39`, `c9c9650d`, `5f28f68`, `0fa1cae`, `778efdb`, `f2c75cf`, `95e8579`, `bd20271`, `b9da84b`, `6651add`, `b9da84b`, etc.)
- NO touch of `openspec/changes/v1.1-followups/`
- NO expansion to Phase 5.2 (TUI/web)
- NO `stash`-triggering words introduced (N/A — doc-only)

## L28 §1 Purpose bullet — Investigation (CRITICAL)

**Current text (verbatim, L28):**

```
- (Phase 5 placeholder) will surface workspace state in a TUI or web visualization.
```

**Surrounding context (§1 Purpose, L18-L30):**

The bullet sits at the end of a 5-bullet enumeration of what the workspace capability does. Bullets L24-L27 already describe the 4 shipped capabilities:

- L24: `flow projects ls [--json]` (Phase 1, shipped)
- L25: `flow workspace status [--json]` (Phase 3, shipped)
- L26: `flow workspace {fix,archive,archived,restore}` (Phase 4, shipped)
- L27: `~/.flow-engineering/registry.json` (Phase 4, shipped)
- **L28: `(Phase 5 placeholder) will surface workspace state in a TUI or web visualization.` ← STALE**
- L30: "What `workspace` is NOT" disclaimer (forward-looking content)

**Stale markers identified:**

1. `(Phase 5 placeholder)` — the parenthetical Phase 5 placeholder marker; phase-5-dashboard shipped at `778efdb`, so this is no longer a placeholder.
2. `will surface workspace state in a TUI or web visualization` — incorrect surface (no TUI shipped; Rich MVP shipped instead; web is deferred to Phase 5.2 per REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE at L230).

**Proposed fix (RECOMMENDED — replace with shipped-state bullet, matching the existing 4-bullet shipped-pattern at L24-L27):**

```
- visualizes workspace state in a read-only Rich dashboard for human operators (`flow workspace dashboard` with `--filter RULES`, `--sort FIELD`, `--no-color`; no `--json` per Pattern #538).
```

**Rationale for the proposed fix:**

- Removes both stale markers (`(Phase 5 placeholder)` + `TUI or web`).
- Uses past/present tense to reflect the shipped state, consistent with the 4 prior bullets that describe shipped capabilities.
- Names the actual CLI surface (`flow workspace dashboard`) so the bullet is self-contained and reviewable without re-reading §3/§4/§5.
- Carries the 3 flags + no-`--json` invariant for reviewer/discoverability (matches the same 3-flags discipline in the §3 row at L80 and §5 row at L317 — both cleaned in the prior cycle).
- Preserves the Rich-MVP framing (Rich is the rendering engine) consistent with REQ-WORKSPACE-DASHBOARD-RENDERS-RICH at L218.
- Deferred scope (TUI/web/interactive) is **NOT** re-introduced in this bullet; it remains captured in REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE at L230 and §4.2 versioning row 1 at L299.

**Alternative fix options (for the orchestrator to consider):**

- **Alt A — REMOVE the bullet entirely**: The shipped surface is already enumerated in §3 (L80) and §5 (L317). Removing L28 entirely would leave §1 with 4 bullets, which is also coherent. Tradeoff: L28 is the only §1 bullet that names a Phase 5 capability; removing it could make §1 read as Phase 1-4-only until a reader scrolls to §3. Net effect: 4 bullets vs 5. -1 line.
- **Alt B — Shorten to a 1-liner pointer**: e.g. `- see §3 row 5 + REQ-WORKSPACE-DASHBOARD-*` (no enumeration). Tradeoff: weaker §1 discoverability; reader has to chase a cross-reference for context. Net effect: 1 line, replacement (not -1).

**Recommended**: full replacement (proposed fix above) — keeps §1 self-contained, matches the discipline of the 4 prior bullets (each names the CLI surface + flags), and is the most reviewer-friendly option. Net effect: 1 line, replacement (0 lines delta).

## L271-L277 §4.1 dependency-graph box — Investigation (CRITICAL)

**Current text (verbatim, L271-L277):**

```
                               ┌──────────────────────────────────────┐
                               │  workspace-dashboard (P5)             │
                               │  flow workspace tui / web             │
                               │  STATUS: PLACEHOLDER STUB             │
                               │  (see REQ-WORKSPACE-DASHBOARD-         │
                               │   PLACEHOLDER + §7 Future Changes)    │
                               └──────────────────────────────────────┘
```

**Surrounding context (§4.1 graph, L240-L291):**

The box sits in the lower-right of the ASCII dependency graph, with an arrow `▲ Phase 5 (future)` (L269) pointing up to the `workspace-hygiene (P4)` box (L261-L267). Above it are the shipped P1/P3/P4 boxes (L250-L267). Below the graph (L287-L291) the prose notes describe the dependency chain as additive.

**Stale markers identified:**

1. **L273**: `flow workspace tui / web` — see dedicated L273 investigation below.
2. **L274**: `STATUS: PLACEHOLDER STUB` — phase-5-dashboard shipped; this is no longer a stub.
3. **L275-L276**: `(see REQ-WORKSPACE-DASHBOARD- PLACEHOLDER + §7 Future Changes)` — `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` does NOT exist. The actual dashboard REQs that landed in spec #539 (per user's prompt) and now anchor §4 are the 6 REQ-WORKSPACE-DASHBOARD-* blocks at L170-L234:
   - L170 `REQ-WORKSPACE-DASHBOARD-SURFACE`
   - L182 `REQ-WORKSPACE-DASHBOARD-READ-ONLY`
   - L194 `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1`
   - L206 `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2`
   - L218 `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH`
   - L230 `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE`

   The `§7 Future Changes` cross-reference is also stale because the prior cleanup cycle (workspace-dashboard-section-cleanup) REMOVED the dashboard row from §7 (commit `a0eb318`, edit #4 per archive-report §4 row 4). The current §7 has 5 rows (numbers 2-6), and row #2 is `workspace-hygiene-capability-spec (optional)`, not dashboard.

**Proposed fix (RECOMMENDED — replace the 7-line box with a shipped-state box mirroring the P1/P3/P4 boxes above):**

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

**Rationale for the proposed fix:**

- L273 fixed: `flow workspace tui / web` → `flow workspace dashboard` (matches the §5 row at L317 cleaned in the prior cycle).
- L274 fixed: `STATUS: PLACEHOLDER STUB` → `Phase 5: 6 REQs incl. Rich MVP + ...` (mirrors the discipline of the P1/P3/P4 boxes above, which enumerate "Phase 1: 5 REQs" / "Phase 3: 8 REQs" / "Phase 4: 12 REQs").
- L275-L276 fixed: `(see REQ-WORKSPACE-DASHBOARD-PLACEHOLDER + §7 Future Changes)` → `Source: phase-5-dashboard (shipped)`. The 6 actual REQs are all enumerated in §4 above; the graph box is a navigation summary, not a full REQ citation index. Naming the delta-spec source (rather than the 6 individual REQ IDs) keeps the box compact and reviewable.
- Cross-reference to §7 is dropped: the dashboard row was removed from §7 in the prior cycle and is no longer a "future change".
- Box height stays at 7 lines (matches the P1/P3/P4 boxes which are 7-9 lines tall), preserving ASCII alignment of the surrounding graph.

**Alternative fix options (for the orchestrator to consider):**

- **Alt A — Minimal swap**: Keep the 7-line box shape; only swap the stale text in-place (L273 `dashboard` + L274 `Phase 5: 6 REQs ...` + L275-L276 `Source: phase-5-dashboard (shipped)`). Tradeoff: less clean rewrite; preserves some placeholder residue. Net effect: 7 lines, in-place replacement.
- **Alt B — Drop the box entirely**: Since the dashboard is shipped and §3/§4/§5 already enumerate it, the graph box could be removed. Tradeoff: loses the visual cue that P5 depends on P3 + P4. The P1/P3/P4 boxes would remain. Net effect: -7 lines from the graph; reader loses the dependency arrow. NOT recommended.
- **Alt C — List the 6 REQ IDs in the box**: e.g. `REQs: SURFACE / READ-ONLY / CONSUMES-DS1 / CONSUMES-DS2 / RENDERS-RICH / DEFER-INTERACTIVE`. Tradeoff: noisy; the §4 anchor at L170-L234 already enumerates them. NOT recommended for the box itself; can be used as a `Source:` footnote if the reviewer asks for it.

**Recommended**: full replacement (proposed fix above). Net effect: 7 lines, in-place replacement (0 lines delta). ASCII alignment preserved.

## L273 §4.1 graph cross-reference — Investigation (CRITICAL)

**Current text (verbatim, L273):**

```
                               │  flow workspace tui / web             │
```

**Surrounding context:** See L271-L277 investigation above. L273 is **inside** the L271-L277 box, so fixing L273 is a sub-task of the L271-L277 fix. Documenting it separately per the user's 3-item scope.

**Stale markers identified:**

- `tui / web` — neither TUI nor web visualization shipped. The shipped CLI surface is `flow workspace dashboard` (single command, Rich MVP, no web stack). Per REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE at L230: *"TUI frameworks (Textual, urwid, prompt_toolkit, Blessed), web frameworks (FastAPI, Streamlit, Dash, Panel, Flask, Tauri), real-time updates, file watching, websocket-style streams, interactive forms / prompts / buttons, mobile support, i18n, theming, historical data / audit logs / trend lines, and multi-user support are ALL deferred to Phase 5.2 (or later)."*

**Proposed fix (RECOMMENDED — replace `tui / web` with `dashboard`):**

```
                               │  flow workspace dashboard             │
```

This is **already absorbed** into the L271-L277 box fix above. Documented separately here to satisfy the user's 3-item scope.

**Rationale:**

- Single CLI command, not a slash-separated list. Slash-separated list implies two distinct surfaces (tui + web), which is incorrect post-phase-5-dashboard.
- Matches the §3 row at L80 (`flow workspace dashboard`) and §5 row at L317 (`flow workspace dashboard`) — both already cleaned in the prior cycle.
- Preserves the L273 character position in the box (column alignment) for clean ASCII render.

**Alternative fix options:**

- **Alt A — `flow workspace dashboard (Rich MVP)`** — adds the rendering engine. Tradeoff: too verbose for a graph box; the rendering detail belongs in REQ-WORKSPACE-DASHBOARD-RENDERS-RICH at L218. NOT recommended.
- **Alt B — DROP the L273 line entirely**: Tradeoff: loses the "this is the CLI surface" line that the P1/P3/P4 boxes above all carry. NOT recommended.

**Recommended**: simple in-place replacement (proposed fix above). Net effect: 1 line, in-place replacement (0 lines delta, character-for-character swap of `tui / web` → `dashboard`).

## Cross-Reference with workspace-dashboard-section-cleanup archive

Per `openspec/changes/archive/2026-06-30-workspace-dashboard-section-cleanup/archive-report.md` §9 (Carry-Over Follow-Ups):

> 1. **extract-build-needs-by-name-helper** — internal refactor opportunity surfaced during sort-projects analysis
> 2. **remove-sort-projects-deprecation-fallback** — DeprecationWarning shim no longer needed after sort-projects ships
> 3. **AC6 wording fix** — `Unknown` → `Unsupported` for type-correct error messaging in dashboard envelope parser
> 4. **L28 §1 Purpose bullet** — still references placeholder state (deferred to `workspace-spec-section-cleanup-1`) ✅ THIS CHANGE
> 5. **L271-277 §4.1 dependency-graph** — still references placeholder (deferred to `workspace-spec-section-cleanup-1`) ✅ THIS CHANGE
> 6. **L273 §4.1 graph cross-reference** — same scope as above ✅ THIS CHANGE

**Confirmation**: The 3 user-locked items in this change are **exactly** items #4 + #5 + #6 from the prior archive-report §9. The carry-over wording is precise — no drift since the prior cycle's archive. Items #1 + #2 + #3 are unrelated code/AC carry-overs that remain as future debt (out of scope for this change).

**Per the prior change's commit message (T-6 verbatim, archive-report §8):**

> Out of scope (future cleanup debt):
> - L28 §1 Purpose bullet (stale reference)
> - L271-277 §4.1 dependency-graph (still references placeholder)
> - L273 §4.1 graph cross-reference

**Confirmation**: Identical wording to the user's launch prompt. The 3 items have not regressed; they remain in the same state as documented at archive.

**Related items already addressed by the prior cleanup cycle (NOT in this change):**

- L73 §3 intro (changed from "3 confirmed sub-capabilities + 1 placeholder" → "4 confirmed sub-capabilities" — archive-report §4 row 1)
- L80 §3 row 5 (placeholder row → shipped `phase-5-dashboard` row — archive-report §4 row 2)
- L317 §5 row ("tui (future)" → "dashboard" with flags — archive-report §4 row 3)
- L360 §7 row #2 (REMOVED + renumbered — archive-report §4 row 4)

The prior cycle correctly limited itself to §3/§5/§7 and explicitly excluded §1 and §4.1. This change completes the cleanup by addressing the §1 + §4.1 residue.

## Open Questions (3-5 with tradeoffs)

### Q1 (CRITICAL) — L28 fix: REPLACE with shipped-state bullet, REMOVE entirely, or SHORTEN to a 1-liner pointer?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **REPLACE** (proposed fix above) | Self-contained §1, matches discipline of 4 prior bullets, names CLI surface + flags for discoverability | 1 long line; could feel verbose if reader has already seen §3/§5 | **✅ RECOMMENDED** — best §1 discoverability; matches existing 4-bullet pattern |
| REMOVE entirely | Shortest §1; eliminates any placeholder residue; lets §3/§5 carry the enumeration | §1 reads as Phase 1-4-only until reader scrolls; loses the only §1 mention of Phase 5 | Acceptable alt; surface in proposal for user opt-out |
| SHORTEN to pointer | Forces reader to chase cross-reference; preserves a §1 line item | Weak §1; adds a cross-reference dependency | NOT recommended |

### Q2 (CRITICAL) — L271-L277 fix: REPLACE the box in-place, MINIMAL swap, or DROP the box?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **REPLACE** (proposed fix above) | Clean rewrite; mirrors P1/P3/P4 box discipline; preserves ASCII alignment; removes all 3 stale markers at once | 7-line edit (longest of the 3 changes); reviewer must compare line-by-line | **✅ RECOMMENDED** — cleanest end state |
| MINIMAL swap | Smaller diff (3-4 line edits in-place); reviewer diff is minimal | Preserves some placeholder residue (`STATUS: PLACEHOLDER STUB` → just `Phase 5: 6 REQs ...` still has a "looks like a stub" feel) | Acceptable alt; surface in proposal |
| DROP the box | Shortest; the dashboard is shipped and §3/§4/§5 already enumerate it | Loses the visual P5-depends-on-P3+P4 cue; the P1/P3/P4 boxes lose their peer | NOT recommended |

### Q3 (CRITICAL) — L273 fix: in-place `tui / web` → `dashboard` (subsumed in L271-L277)?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **In-place swap** (absorbed in L271-L277 fix) | Zero added scope; column alignment preserved; matches the §3 L80 + §5 L317 discipline from the prior cycle | None significant | **✅ RECOMMENDED** — same edit the prior cycle applied to L80 + L317 |
| Add `(Rich MVP)` suffix | More explicit about the rendering engine | Verbose for a graph box; rendering detail is in REQ-WORKSPACE-DASHBOARD-RENDERS-RICH at L218 | NOT recommended |
| Drop the L273 line | Shortest | Loses the "this is the CLI surface" line that P1/P3/P4 boxes all carry | NOT recommended |

### Q4 (EXPANSION RISK) — Address adjacent stale items in the same change?

Discovered during investigation:
- **L69** §2 boundary stress test: `"Show me a TUI of my workspace."` — uses TUI framing; Rich MVP shipped, not TUI.
- **L269** §4.1 graph arrow label: `│ Phase 5 (future) │` — should read `Phase 5 (shipped)`.
- **L291** §4.1 graph note: `- Phase 5 (future) will depend on Phase 3 ...` — should be past tense.

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Address only the 3 locked items** | Honors user-locked scope; "doc-only, chico"; well under budget; fastest cycle | Leaves 3 adjacent stale items for a future change | **✅ RECOMMENDED** — user explicitly said "doc-only, chico" |
| Also fix L69 + L269 + L291 | Slightly more polished end state; reduces future cleanup debt | Scope creep; "limpiar lo prometido, nada más" (Pattern #582); pushes the cycle past 30-45 min forecast | Acceptable if user opts in during propose phase |
| Replace L291 + L69 only (skip L269 for graph-alignment reasons) | Selective | Inconsistent | NOT recommended |

**Recommended**: surface as a single Open Question in the propose phase. If user says "yes, also fix L69 + L269 + L291", expand scope at propose time. Otherwise, leave for a future `workspace-spec-section-cleanup-2` change.

### Q5 (FORECAST) — Does this cycle need spec/design/tasks phases, or can apply be combined with one of them?

The prior cleanup cycle (workspace-dashboard-section-cleanup) at archive-report §12 reported a wall-time actual of ~5 minutes for the apply phase, with a total cycle of ~46 minutes across all 8 phases. This change is similar in scope (1 file, 3 items, ~10-20 LOC of text edits) — even smaller than the prior cycle.

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Run full pipeline** (explore → propose → spec → design → tasks → apply → verify → archive) | SDD discipline; explicit ACs; rollback plan; commit message in design | 8 phase invocations; 30-45 min wall-time | **✅ RECOMMENDED** — matches prior cycle's structure; small but auditable |
| Skip spec phase (use the explore.md's "proposed fix" sections as the delta spec) | Saves ~3 min | Breaks the SDD pipeline contract | NOT recommended |
| Combine apply+verify+archive into one phase | Saves orchestration overhead | Each phase has its own verify gate; combining masks the post-state | NOT recommended |

**Recommended**: full pipeline with the same 8 phases as the prior cycle. Forecast: 30-45 min total (matches user's expectation). The explore → propose → spec → design → tasks sequence is **fast** for doc-only changes; apply + verify + archive is also fast (no test runs, no verify commands to execute). The wall-time budget is dominated by the human-orchestrator handoffs, not by sub-agent work.

## Tech Debt

### Size

- **~10-20 LOC of text edits** (L28 1-line replacement + L271-L277 7-line box replacement with L273 absorbed; net 0-line delta per location, 0-line delta overall).
- Well under the 400-line single-PR budget.
- Comparable in size to the prior cleanup cycle (17 LOC, archive-report §2 Net LOC).

### Strategy

- **Single PR** (user-locked at preflight: "single PR, ~10-20 LOC text edits, well under 400 budget").
- Delivery strategy: `single-pr` (resolved at session preflight).
- Review budget: 400 lines (per Pattern #548 + preflight). Forecast: ~20 LOC, < 5% of budget.
- Strict TDD: **OFF** (doc-only, no test code).
- No new verify checks (8 existing from phase-5-dashboard still cover all dashboard invariants).
- No new tests.
- No code changes.
- No new files (only modifies the existing `workspace/spec.md`).

### Queue position

- **THIRD queued cleanup change** in the v1.2 arc (per Pattern #555), after:
  1. `sort-projects` (merged + pushed at `c9c9650d`)
  2. `workspace-dashboard-section-cleanup` (merged at `a0eb318`; NOT pushed per Pattern #584 — user must merge + push to `origin/main` first)
- This is the 2nd doc-only cleanup cycle in the v1.2 arc.
- After this change, the `workspace/spec.md` will be **impeccable** per the user's framing (zero stale-prose residue for the dashboard capability).

### Locked commits (NON-NEGOTIABLE — preserved per Pattern #548)

All 14+ locked commits remain byte-identical on `main` HEAD `1ef33cf`:

- PR1 `6651add` (phase-5-dashboard PR1)
- PR2 `95e8579` (phase-5-dashboard PR2)
- PR3 `778efdb` (phase-5-dashboard PR3)
- sort-projects `c9c9650d` + `f2c75cf` + `bd20271` + `b9da84b`
- workspace-dashboard-section-cleanup `a0eb318` (NOT yet pushed; user must merge first)
- workspace-hygiene `c734e39` (Phase 4 archive)
- workspace-status `5f28f68` (Phase 3)
- workspace-intelligence `0fa1cae` (Phase 1)
- workspace-capability-bootstrap `44f9e54` + `2df1719` (family anchor)

### v1.1-followups/ sacred territory

Untracked throughout; never tracked; not touched by this change. Confirmed by archive-report §6 gate #9 ("`v1.1-followups/` untouched (still untracked, sacred)").

## Forecast (wall-clock)

| Phase | Estimate | Notes |
|-------|----------|-------|
| explore (this) | ~10 min | DONE |
| propose | ~5 min | scope + 3 ACs + open questions |
| spec | ~3 min | 3 "MODIFIED Prose" entries; no new BDD scenarios (doc-only) |
| design | ~5 min | text-edit recipe + 12 preservation gates + rollback plan + commit message (T-6) |
| tasks | ~5 min | 3-4 mechanical tasks T-1..T-3 (or T-1..T-4 if expansion to L69/L269/L291 is approved) |
| apply | ~5 min | 3-4 manual table/box/bullet edits + commit |
| verify | ~5 min | manual re-read; no automated tests |
| archive | ~5 min | archive-report + state.yaml chore commit |
| **TOTAL** | **~45 min** | within user's 30-45 min forecast |

**Risk note**: The prior cycle (workspace-dashboard-section-cleanup) reported an actual wall-time of ~46 min (archive-report §12) — this matches our forecast within 1 minute. The cycle is well-bounded and predictable.

## Verdict (recommended approach)

**RECOMMENDATION: PROCEED with the 3 user-locked text-only edits as a single-PR doc-only cleanup.**

- **L28**: REPLACE the stale `(Phase 5 placeholder) will surface workspace state in a TUI or web visualization.` bullet with the shipped-state bullet that names the CLI surface + flags.
- **L271-L277**: REPLACE the 7-line placeholder-stub box with the 7-line shipped-state box that mirrors the P1/P3/P4 boxes above. L273 is fixed as a sub-task of this edit.
- **L273**: SUBSUMED in L271-L277 (in-place swap of `tui / web` → `dashboard`).

All 3 items are unambiguous — the fixes are mechanical; the wordings are derived from the 6 dashboard REQ blocks at L170-L234 (canonical source-of-truth for the shipped state) + the prior cleanup cycle's §3 L80 + §5 L317 (proven shipped-state phrasing).

**Open Question for orchestrator**: whether to expand the change to also fix the 3 adjacent stale items (L69 boundary stress test, L269 graph arrow label, L291 graph note). Recommended posture: **do NOT expand** unless user opts in at propose phase. The user said "doc-only, chico" — keep the change tight.

**Cycle profile**: smallest in the v1.2 arc; 3-4 mechanical edits; ~10-20 LOC; single PR; well under the 400-line budget; LOW risk throughout. Matches the prior cleanup cycle's structure (8 phases, 45 min) almost exactly.

## Next SDD Phase

**sdd-propose** — write `proposal.md` with:

- **Why**: Phase 5 placeholder cleanup continuation; items #4 + #5 + #6 from `workspace-dashboard-section-cleanup` archive-report §9 carry-over list. The prior cycle correctly limited itself to §3/§5/§7 and excluded §1 + §4.1; this change completes the cleanup.
- **Scope**: 3 user-locked text-only edits (L28 + L271-L277 + L273-subsumed). ~10-20 LOC, ~0 net lines.
- **Approach**: REPLACE / REPLACE / SUBSUMED (in that order — L28 first, then L271-L277 box).
- **Non-goals**: NO code, NO new tests, NO new verify checks, NO touch of v1.1-followups, NO amend of locked commits, NO expansion to L69/L269/L291 (surface as Open Question for user opt-out).
- **Acceptance**: 3 manual re-read checks (L28 bullet reflects shipped state + L271-L277 box reflects shipped state with 6 REQ count + L273 has no TUI/web reference). Optionally: 1 ASCII alignment sanity check.
- **Rollback**: `git revert HEAD`. Doc-only change; revert restores pre-change state without affecting code, tests, registry, or behavior.

## Risks

| # | Severity | Risk | Mitigation |
|---|----------|------|------------|
| R1 | LOW | Expansion creep at propose phase (user may ask to also fix L69/L269/L291, pushing past "doc-only, chico") | Surface in propose phase as a single Open Question; user opt-in/out; default = no expansion |
| R2 | LOW | ASCII alignment drift in the L271-L277 box replacement (column mis-alignment breaks graph render) | Use the P1 box at L250-L255 as a column-width reference; visual re-read at apply time |
| R3 | LOW | L28 bullet replacement introduces a 1-line diff that is longer than the original (verbose) | The new bullet matches the discipline of the 4 prior bullets (L24-L27) — verbose is intentional for §1 discoverability |
| R4 | NEGLIGIBLE | v1.1-followups/ accidental touch | Sacred territory; explicitly OUT of scope; preservation gate in design.md |
| R5 | NEGLIGIBLE | §4.1 graph L269 / L291 stale (not addressed) | User locked scope; surface in propose as Open Question for explicit user opt-in/out |
| R6 | NEGLIGIBLE | L73 (now L73 after prior cleanup) was coupled to L80 in the prior cycle — this change should not touch L73 since the prior edit already fixed it (L73 reads "4 confirmed sub-capabilities" post-cleanup, no further change needed) | Pre-flight check at apply time: confirm L73 + L80 + L317 already reflect shipped state; this change only touches L28 + L271-L277 (with L273 subsumed) |

---

*This explore artifact is mirrored from `openspec/changes/workspace-spec-section-cleanup-1/explore.md`. Generated by the `sdd-explore` sub-agent for flow-engineering v1.2.0, project `insyd` in Engram. Build target: doc-only cleanup, single PR, 30-45 min wall-time forecast, LOW risk profile. Out of scope locked: NO code, NO new tests, NO new verify checks, NO touch of v1.1-followups, NO expansion to Phase 5.2.*
