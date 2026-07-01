# Explore: workspace-dashboard-section-cleanup

> **Phase**: explore (SDD pipeline)
> **Change**: `workspace-dashboard-section-cleanup`
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Goal**: confirm exact line locations + proposed fixes for 3 stale-prose items in `openspec/specs/workspace/spec.md` (`§3 row 5 placeholder` + `§5 row "tui (future)"` + `§7 row #2 deferred text`), per the carry-forwards documented in phase-5-dashboard archive-report §9.2.

---

## Goal

Identify the **exact line locations** and **proposed fixes** for the 3 stale-prose items in `workspace/spec.md` that were explicitly OOS during phase-5-dashboard spec phase (#539) and carried forward to a `workspace-dashboard-section-cleanup` follow-up change (per phase-5-dashboard archive-report §11).

**User framing**: *"explore rápido, confirmamos las líneas exactas, y debería ser un ciclo corto."* — quick exploration focused on line locations, minimal scope.

This is a **doc-only cleanup** — no code, no tests, no new verify checks. ~10–20 LOC of text edits.

---

## Scope

### User-locked (IN scope, must-fix)

1. `workspace/spec.md §3 row 5 placeholder` — `📌 Placeholder` row at L80 (sub-capabilities table)
2. `workspace/spec.md §5 row "tui (future)"` — `tui (future)` row at L317 (CLI surface table)
3. `workspace/spec.md §7 row #2 deferred text` — `workspace-dashboard (Phase 5)` row at L360 (Future Changes table)

### Informational only (NOT in scope — DO NOT expand)

- `workspace/spec.md:28` §1 Purpose bullet — `(Phase 5 placeholder) will surface workspace state in a TUI or web visualization` (also stale; should be removed in a future cycle)
- `workspace/spec.md:73` §3 intro phrasing — `3 confirmed sub-capabilities + 1 placeholder`
- `workspace/spec.md:271-277` §4.1 dependency-graph — still references `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` (non-existent REQ; replaced by 6 dashboard REQs at L170-L234)
- `workspace/spec.md:317 §5 row` could also fix `flow workspace tui / web` mention in §4.1 L273 graph (cross-reference)
- `workspace/spec.md:303 §4.2 row Phase 2` — historical row, mostly addressed by L354 RESOLVED note (W1 from verify-report #513)
- `workspace/spec.md:374 §8 Drift Detection — Family-shape protocol` — text is already correct (describes the protocol that this cleanup is implementing); surface as informational only

These are flagged as **cleanup debt surfaced beyond the user-locked scope** but NOT in scope for THIS change. Per Pattern #548-equivalent ("don't expand locked scopes"), they're tabled for a future cycle if the user wants.

---

## §3 Row 5 Investigation

### Location

**Line 80** in `openspec/specs/workspace/spec.md`.

### Current text (L75-L80, full surrounding table for context)

```
| Phase | Sub-capability | CLI surface | Role | Status | Delta spec |
|-------|---------------|-------------|------|--------|------------|
| 1 | `projects-ls-extension` | `flow projects ls [--json]` | Read discovery — project metadata enumeration | ✅ Shipped (local-only branch `codex/workspace-intelligence`) | `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md` |
| 3 | `workspace-status` | `flow workspace status [--json]` | Read aggregation — 5 needs-attention rules R1–R5 | ✅ Shipped (local-only branch `codex/flow-workspace-status`) | `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` |
| 4 | `workspace-hygiene` | `flow workspace {fix,archive,archived,restore}` | Write/mutation — registry-mediated lifecycle (R2 + archive) | ✅ Shipped + archived at `d077d75` | `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` |
| 5 (future) | `workspace-dashboard` | `flow workspace tui` / web | Visualization — TBD | 📌 **Placeholder** | (no delta spec yet — see Future Changes §7) |
```

### Why it's stale

After phase-5-dashboard merged (PR3 `778efdb` on tracker `phase-5-dashboard`, spec chore `b9da84b`), the dashboard is **no longer a placeholder**:

1. **6 root REQs landed** at L170-L234: `REQ-WORKSPACE-DASHBOARD-SURFACE` (L170), `REQ-WORKSPACE-DASHBOARD-READ-ONLY` (L182), `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1` (L194), `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2` (L206), `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH` (L218), `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE` (L230). All 6 carry `Source:` lines pointing to the shipped delta spec.
2. **Delta spec exists** at `openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` (per phase-5-dashboard archive-report §10.1; 7 delta REQs).
3. **`flow workspace dashboard`** is registered as a Click subcommand at `src/flow_engineering/cli.py:3034–L3072` (PR3 integration).
4. The cli_dashboard test suite (4 tests) + dashboard test suite (30 tests) all PASS (verify-report #557 §6 AC walkthrough).

Per the §8 family-shape protocol (L374): *"When a new sub-capability is added (e.g., Phase 5 dashboard), update §3 (Sub-capabilities), §5 (Public CLI surface), and §7 (Future Changes → remove the placeholder entry from Future Changes and add it to §3)."*

The current L80 row violates this protocol — still labeled `5 (future)` + `Placeholder` + `TBD` + `(no delta spec yet)` **after** the sub-capability shipped.

### Proposed fix

**Replace L80 row** with the shipped-state row matching the existing format (Phase 1 / 3 / 4 rows):

```
| 5 | `workspace-dashboard` | `flow workspace dashboard` | Visualization — read-only Rich MVP for human operators; supports `--filter RULES`, `--sort FIELD`, `--no-color` (no `--json` — Pattern #538) | ✅ Shipped + archived at `phase-5-dashboard` | `openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` |
```

Edits vs current row:
- Drop `(future)` from Phase column
- Update CLI surface: `flow workspace tui / web` → `flow workspace dashboard` (TUI explicitly deferred per `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE` L232)
- Drop TBD, `📌 Placeholder`, and `(no delta spec yet — see Future Changes §7)`
- Set Status to `✅ Shipped + archived at `phase-5-dashboard``
- Point Delta spec to the **archived** delta (delta was moved when phase-5-dashboard archived)

**Plus accompanying edit at L73**: `3 confirmed sub-capabilities + 1 placeholder` → `4 confirmed sub-capabilities` (this is a 1-line fix to keep the §3 intro consistent with the updated table). **Note**: this is technical scope creep — the L73 fix is **adjacent to** L80 and required for consistency. Calling out as a 1-line tightly-coupled edit (not expanding scope).

**Note on `flow workspace tui / web` cross-reference in L273 §4.1 dependency-graph**: out of scope for this change. Logged in §6 Open Questions.

---

## §5 Row "tui (future)" Investigation

### Location

**Line 317** in `openspec/specs/workspace/spec.md`.

### Current text (L309-L317, full surrounding table for context)

```
| Command | Subcommand | Phase | Purpose |
|---------|-----------|-------|---------|
| `flow projects ls` | (Phase 1) | 1 | Enumerate projects; `--json` for the v1 envelope |
| `flow workspace status` | `--json` (Phase 3) | 3 | Read needs-attention report |
| `flow workspace fix` | `<project> [--yes] [--backup]` (Phase 4) | 4 | R2 remediation (no-git → `git init`) |
| `flow workspace archive` | `<project> [--reason TEXT] --yes` (Phase 4) | 4 | Move project to `registry.archived[]` |
| `flow workspace archived` | (Phase 4) | 4 | TEXT-only listing of archived projects |
| `flow workspace restore` | `<project> --yes` (Phase 4) | 4 | Move project back to `registry.projects[]` |
| `flow workspace tui` (future) | (Phase 5) | 5 (placeholder) | Dashboard — not yet implemented |
```

### Why it's stale

After phase-5-dashboard merged, the actual shipped CLI is `flow workspace dashboard` (not `flow workspace tui`). Three points of staleness in L317:

1. **`flow workspace tui`** — wrong command name. Shipped = `flow workspace dashboard` (per REQ-DASHBOARD-COMMAND-NAME).
2. **`(future)`** — wrong modifier. Phase 5 is no longer "future"; it shipped.
3. **`5 (placeholder)`** — wrong Phase label. Phase 5 is no longer a placeholder.
4. **`Dashboard — not yet implemented`** — wrong state. It IS implemented.

TUI-style dashboards (Textual, urwid, prompt_toolkit, Blessed) are **explicitly deferred** to Phase 5.2 (per REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE L232). The shipped MVP is a visual Rich tables/panels layout (not a TUI per se).

### Proposed fix

**Replace L317 row** with the shipped-state row matching the existing format:

```
| `flow workspace dashboard` | `[--filter RULES] [--sort FIELD] [--no-color]` (Phase 5) | 5 | Read-only Rich MVP (A header + B needs-attention + C archived + D footer); no `--json` (Pattern #538) |
```

Edits vs current row:
- Update command: `flow workspace tui (future)` → `flow workspace dashboard` (drop `(future)`)
- Update subcommand: `(Phase 5)` → `[--filter RULES] [--sort FIELD] [--no-color] (Phase 5)` (match the explicit-flag style of Phase 1/3/4 rows)
- Update Phase: `5 (placeholder)` → `5`
- Update Purpose: `Dashboard — not yet implemented` → `Read-only Rich MVP (A header + B needs-attention + C archived + D footer); no `--json` (Pattern #538)`

**Flag inventory check** (per REQ-DASHBOARD-FLAGS at `openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md`):
- `--filter RULES` ✓ (added PR2)
- `--sort FIELD` ✓ (added PR2)
- `--no-color` ✓ (added PR3)
- `--json` ✗ — explicitly absent per Pattern #538 ("one identity per command")

All 3 shipped flags are captured; no flag is silently dropped.

---

## §7 Row #2 Investigation

### Location

**Line 360** in `openspec/specs/workspace/spec.md`.

### Current text (L357-L360)

```
## 7. Future Changes

| # | Change | Scope | Priority | Trigger |
|---|--------|-------|----------|---------|
| 2 | **`workspace-dashboard` (Phase 5)** | TUI (`flow workspace tui`) or web visualization of workspace state (registry + needs_attention + per-project metadata). Will add a new delta spec; this root spec is already anchored. | Low | Future change; requires CLI solidification first (per session #483) |
```

### Why it's stale

The `workspace-dashboard` change **shipped**. It is no longer a "future change".

Per phase-5-dashboard archive-report §16 ("SDD Cycle Complete"): *"Phase 5 of the workspace-intelligence arc is CLOSED."* Per archive-report §15 (Merge Readiness), the tracker `phase-5-dashboard` is **ready for merge** to main.

Once merged, the placeholder row at L360 must be removed — leaving the change as a "Future Changes" entry would be a **documentation lie** (the change is past, not future).

Three points of staleness in L360:

1. **No longer future** — change has shipped.
2. **Wrong CLI name** — `flow workspace tui` (deferred per L232) vs shipped `flow workspace dashboard`.
3. **Trigger is past-tense** — "requires CLI solidification first" is moot; CLI is solidified.

### Proposed fix

**Remove L360** (row #2) entirely from §7 Future Changes table.

Rationale for REMOVE vs KEEP-with-marked-resolved: §7 is "Future Changes" — the semantics is **forward-looking**. A landed change is, by definition, not future. Removing preserves §7's invariant (every row is forward-looking). Alternative: renumber the table to drop the gap (rows 3-7 → 2-6).

**Decision**: REMOVE row #2 (this cleanup cycle) + renumber 3-7 → 2-6 (this cleanup cycle, single contiguous edit).

Sample post-edit fragment (L356-L364):

```
## 7. Future Changes

| # | Change | Scope | Priority | Trigger |
|---|--------|-------|----------|---------|
| 2 | `workspace-hygiene-capability-spec` (optional) | Create `openspec/specs/workspace-hygiene/spec.md` as a top-level capability for the write-side if the delta grows further. | Low | Phase 4 follow-up #2 in archive-report #477 |
| 3 | `backup-retention-policy` | Currently INDEFINITE in Phase 4 (per locked constraint #12). Needs pruning/TTL strategy at scale. | Low | Operator concern; not blocking |
| 4 | `workspace-hygiene-r1` (deferred) | R1 dirty-git remediation: stash/worktree handling, interactive prompts, status integration. Explicitly OUT of Phase 4. | Low | Future change if requested |
| 5 | `workspace-hygiene-r3` + `workspace-hygiene-r4` (deferred) | R3 no-tests bootstrap (template-dependent) + R4 no-openspec bootstrap (semantic scaffold). | Low | Future change if requested |
| 6 | Artifact-hygiene move | Phases 1 + 3 still in `openspec/changes/{workspace-intelligence,flow-workspace-status}/` (not yet in `archive/`). | Low | Out of scope for this change; separate cleanup |
```

**Note on `flow-where-cross-project-capability-merge` row #1** (per W2 in user's background): no row #1 exists in the current §7 — it was already removed (the §6.1 RESOLVED note at L354 references "See also §7 row #1 (this follow-up is now removed from Future Changes)"). So **W2 is already resolved** — confirmed by reading L354. Not in scope.

---

## Cross-Reference with Phase 5 Archive

Per phase-5-dashboard archive-report §9.2 (carry-over from spec phase, explicitly OOS at #539):

> "### 9.2 §3/§5/§7 Cleanup Deferred (carried from spec phase)
>
> The Phase 5 placeholder cleanup in `workspace/spec.md` was explicitly OOS at spec time per #539 §Out of Scope:
>
> - §3 row 5 placeholder row still exists at L80 (now shows alongside 6 dashboard REQs)
> - §5 row "tui (future)" still exists
> - §7 row #2 cleanup still references "workspace-dashboard" Phase 5
>
> **Follow-up change recommended**: `workspace-dashboard-section-cleanup` (NOT a violation — was explicitly OOS at spec)."

**Word-by-word confirmation against the live spec**:

| Carry-over item (per archive-report §9.2) | Live spec (current state) | Match |
|---|---|---|
| "§3 row 5 placeholder row still exists at L80" | L80 = `5 (future) | workspace-dashboard | flow workspace tui / web | Visualization — TBD | 📌 Placeholder | (no delta spec yet — see Future Changes §7)` | ✅ EXACT MATCH (line + content) |
| "§5 row 'tui (future)' still exists" | L317 = ``flow workspace tui`` (future) | (Phase 5) | 5 (placeholder) | Dashboard — not yet implemented`` | ✅ EXACT MATCH (line + content) |
| "§7 row #2 cleanup still references 'workspace-dashboard' Phase 5" | L360 = `2 | workspace-dashboard (Phase 5) | TUI (flow workspace tui) or web visualization...` | ✅ EXACT MATCH (line + content + trigger) |

**Verdict**: Carry-over wording from archive-report §9.2 is **precisely accurate** against the current `workspace/spec.md` state. This confirms the 3 stale items have NOT regressed since the phase-5-dashboard archive phase — they're stable carry-over and ready for the planned cleanup.

**Bonus**: The carried-forward list (per §11 Follow-Up Changes) explicitly names this cleanup as the **FIRST follow-up recommended**, with `sort-projects-align-with-real-ds-data-flow` as MEDIUM priority second.

### Sort-projects cross-reference

For completeness: `sort-projects-align-with-real-ds-data-flow` (engram #568 design, #572 apply, #573 verify, #574 archive) **also** mentioned "§3/§5/§7 carry-over" in engram #572 (per user's preflight context). That change shipped and added an apply-progress observation about §3/§5/§7 carry-over — but **did NOT modify `workspace/spec.md`** itself. The sort-projects change only touched design + spec of the dashboard module, not the root workspace spec. So this cleanup remains necessary regardless of sort-projects landing.

---

## Open Questions

### Q1 (CRITICAL): §3 L80 — Replace with shipped-state row vs. DROP entirely?

| Option | Pros | Cons |
|---|---|---|
| **A. Replace L80 with shipped-state row** | §3 has 4 rows (one per Phase); symmetry preserved; mirrors Phase 1/3/4 row format exactly | Requires updating Phase numbering (1 → 1, 3 → 3, 4 → 4, 5 → 5); minor edit friction |
| B. DROP L80 row entirely | Maximum minimalism; force reader to inspect §4 for dashboard REQs | Loses §3-as-family-overview invariant; breaks the family-shape protocol at L374 |

**Recommendation**: **A** — preserve §3's invariant ("1 row per Phase, 1 row per sub-capability"). The fix is a row-level edit, not a structural change.

### Q2 (CRITICAL): §5 L317 — Replace row with shipped-state vs. remove row?

| Option | Pros | Cons |
|---|---|---|
| **A. Replace L317 with the shipped `flow workspace dashboard` row** | Symmetry with Phase 1/3/4 rows; §5's table reads as a complete CLI surface inventory | Edit is more verbose than remove |
| B. DROP L317 row entirely | Minimal text edit; reader gets the dashboard command from §3 / §4 | Breaks §5's invariant (CLI surface inventory); creates asymmetry (Phases 1/3/4 listed, Phase 5 absent) |

**Recommendation**: **A** — preserve §5's invariant.

### Q3 (CRITICAL): §7 L360 — Remove row vs. mark as "landed"?

| Option | Pros | Cons |
|---|---|---|
| **A. REMOVE row #2 + renumber 3-7 → 2-6** | §7 is "Future Changes" — by definition, every row must be forward-looking. Removing preserves the invariant. | Loses explicit traceability ("this placeholder used to be here") |
| B. Keep row with `Status: landed` column | Preserves traceability | Adds a column to §7's existing 5-column table (changes structure for ALL rows); §7's invariant ("forward-looking") breaks; future readers could mistake `Status: landed` for "still in queue" |

**Recommendation**: **A** — REMOVE. §7 is forward-looking by design; landed changes live in archive reports (which already document this — phase-5-dashboard archive-report §11 rows). Renumbering is a 5-row contiguous edit, low risk.

### Q4 (info-only): §4.1 L271-277 dependency-graph still references `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` — should this cleanup ALSO fix that?

The dependency-graph at L271-277 still says:

```
│  workspace-dashboard (P5)             │
│  flow workspace tui / web             │
│  STATUS: PLACEHOLDER STUB             │
│  (see REQ-WORKSPACE-DASHBOARD-         │
│   PLACEHOLDER + §7 Future Changes)    │
```

`REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` does NOT exist in §4 (was replaced by 6 dashboard REQs at L170-L234 per spec chore `b9da84b`). This is **stale** but **out of scope** per the user's lock.

**Recommendation**: SURFACE ONLY in the apply-phase tech-debt section. Do NOT fix in this change. Logged as informational.

### Q5 (info-only): §1 L28 bullet — `(Phase 5 placeholder)` — should this be touched?

Line 28 in §1 Purpose still has: `- (Phase 5 placeholder) will surface workspace state in a TUI or web visualization.`

After phase-5-dashboard merged, this bullet is stale (the dashboard shipped; it surfaces workspace state via Rich tables, not "TUI or web").

**Recommendation**: SURFACE ONLY. Do NOT fix in this change (out of user-locked scope).

### Q6 (info-only): §8 L374 family-shape protocol — Is the current protocol text correct?

Line 374: `- **Family-shape protocol**: When a new sub-capability is added (e.g., Phase 5 dashboard), update §3 (Sub-capabilities), §5 (Public CLI surface), and §7 (Future Changes → remove the placeholder entry from Future Changes and add it to §3).`

**Recommendation**: This text is **already correct** — it's describing the protocol this cleanup is implementing. After the apply phase ships, this protocol becomes "vindicated by example" for phase-5-dashboard. NO change needed.

---

## Tech Debt

1. **Size estimate**: ~10-20 LOC of text edits (table row replacements, row removal, renumbering). Well under the 400-line single-PR budget.
2. **PR strategy**: Single PR (Option A — inline trivial doc-only). The user explicitly resolved chained-PR strategy to "single PR, small doc-only change ~10-20 LOC" at preflight.
3. **TDD**: NOT applicable — doc-only change. No new tests.
4. **Verify checks**: NONE new. The 8 existing checks from phase-5-dashboard's `verify-checks.sh` (cross-platform Python/bash script at `openspec/changes/archive/2026-06-30-phase-5-dashboard/scripts/verify-checks.sh`) still cover — Check 5 ("§7 Future Changes mentions `workspace-dashboard`") will FAIL after this cleanup removes the row, but that's **expected** (the change now references the LANDED delta, not the placeholder). The change should UPDATE check 5's text to match the new invariant. Wait — that script is **archived** (read-only audit trail). Let me think...

Actually — `verify-checks.sh` is at `openspec/changes/archive/.../scripts/verify-checks.sh` — **archived**, not modified. The script's checks are HISTORICAL (validated the state at phase-5-dashboard archive time). After this cleanup, running the archived script against the new workspace/spec.md will return **non-zero** for Check 5 (because the dashboard row is now in §3 with status "Shipped", not in §7). **This is expected and correct** — the archived script's purpose was to validate the phase-5-dashboard state, not the post-cleanup state.

   Implication: this cleanup does NOT need to update the verify script. The 8-check script stays preserved as historical audit trail per archive-report §10.1 ("Verify script preserved as part of the audit trail, not deleted").

   For future validation, if the user wants a fresh verify script post-cleanup, that would be a separate `sdd-verify` invocation at the apply phase — but it's NOT needed for THIS change (no behavior moved; only text changed).

5. **Pre-existing OOS**: This cleanup does NOT touch any code. No risk of regressing the 9 pre-existing OOS errors (3 lint + 4 sqlite-vec reindex + 2 mypy yaml-stub) documented at phase-5-dashboard archive-report §10.5.

6. **Queue position**: This is the **second queued change after sort-projects** per Pattern #555. Sort-projects archived (`c9c9650d` sorted). After this cleanup archives, the next queued change is `extract-build-needs-by-name-helper` (Phase 5.2 prep). No overlap.

7. **Carry-over lock**: All 4 prior commits are LOCKED (per Pattern #548):
   - PR1 `6651add` (data layer)
   - PR2 `95e8579` (logic + rendering)
   - PR3 `778efdb` (Click + verify + ACs)
   - sort-projects `c9c9650d`

   This cleanup will produce a NEW commit; it will NOT amend any of the 4 locked commits.

---

## Forecast

| Phase | Wall-time estimate | Risk |
|---|---|---|
| explore (this) | ~10 min (done) | LOW — pure reading |
| propose | ~5 min | LOW — user already locked scope to 3 items; verify-report already documented the carry-over |
| spec | ~3 min | LOW — the "delta spec" is trivial (text edits, no new REQs); could even be a `tasks.md`-only path |
| design | ~5 min | LOW — design is "text-only edit + remove + renumber" — fits in tasks directly |
| tasks | ~5 min | LOW — ~3 small tasks: replace L80, replace L317, remove L360+renumber, plus optional L73 1-liner |
| apply | ~5 min | LOW — 4-5 manual table-cell edits in `workspace/spec.md` (3 user-locked + 1 coupled L73 tweak) |
| verify | ~5 min | LOW — manual re-read of `workspace/spec.md`; no automated verify needed (no behavior moved) |
| archive | ~5 min | LOW — move folder; tiny archive-report |
| **TOTAL** | **~45 min** | LOW end-to-end |

**Cycle verdict**: **~45 min wall-clock end-to-end** — significantly smaller than phase-5-dashboard's ~5h. This is the smallest cycle in the v1.2 arc; well-suited to a single trivial-doc-only PR.

---

## Verdict

**RECOMMENDATION: PROCEED with the 3 user-locked text-only edits** (§3 L80 replace + §5 L317 replace + §7 L360 remove + renumber 3-7 to 2-6 + L73 1-line coupled tweak).

**Out of scope (deferred to future cycles)**:

- §1 L28 bullet — `(Phase 5 placeholder) will surface workspace state in a TUI or web visualization`
- §4.1 L271-277 dependency-graph — still references `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER`
- §4.2 L303 row Phase 2 — historical row, mostly addressed by L354 RESOLVED note
- §7 L360 follow-on (if any other stale prose surfaces post-apply)

**All 3 user-locked items are unambiguous** — the fixes are mechanical, the wordings are already canonical (per phase-5-dashboard archive-report §10.1 + the 6 root REQs at L170-L234 of `workspace/spec.md`).

**Forecast**: ~45 min end-to-end, single trivial-PR. **Lowest-friction change in the v1.2 arc.**

---

## Next SDD Phase

**sdd-propose** — write the proposal.md with:

- §Why: Phase 5 placeholder cleanup; was OOS at spec time per #539; carry-forward per archive-report §9.2.
- §Scope: 3 user-locked text-only edits + 1 L73 coupled tweak (~5 edits).
- §Approach: Replace / Replace / Remove+renumber, in that order.
- §Non-goals: NO code, NO new tests, NO new verify checks, NO touch of v1.1-followups, NO amend of locked commits.
- §Acceptance: 4 manual re-read checks (3 stale items resolved + L73 intro consistent + §7 still has 6 forward-looking rows + no syntax errors in the table rendering).
- §Rollback: Revert single commit; no data or state changes.

---

## Risks

### R1 (LOW severity): §4.1 dependency-graph might break verify-script Check 5

- **Risk**: Running the archived `verify-checks.sh Check 5` ("§7 Future Changes mentions workspace-dashboard") against the post-cleanup state will FAIL.
- **Mitigation**: The script is archived and HISTORICAL; document at apply-time that the failure is expected. The script's purpose was to validate phase-5-dashboard's state, not the post-cleanup state. If user wants a fresh verify script, that's a follow-up.
- **Severity**: LOW — informational, not blocking.

### R2 (LOW severity): Table rendering after edits could break Markdown table alignment

- **Risk**: Replacing L80, L317, L360 with longer Phase / Subcommand cells could push column widths past typical terminal render, breaking column alignment in source-preview tools (GitHub diff view, VS Code Markdown preview).
- **Mitigation**: Use the SAME column widths as the existing Phase 4 / Phase 1 rows (3-char Phase, ~30-char sub-capability, ~40-char CLI surface). The proposed row text already matches the Phase 1/3/4 row widths.
- **Severity**: LOW — cosmetic.

### R3 (LOW severity): Coupling L73 tweak with the L80 fix

- **Risk**: §3 intro at L73 (`3 confirmed sub-capabilities + 1 placeholder`) is NOT user-locked; fixing it (→ `4 confirmed sub-capabilities`) is **1-line scope creep** beyond the user-locked 3 items.
- **Mitigation**: Surface this as an "adjacent 1-line tweak, tightly coupled to L80" in the propose phase. User can opt-out (leave L73 as-is, accept brief inconsistency).
- **Severity**: LOW — decision-only risk.

### R4 (NEGLIGIBLE): §7 L360 removal + renumbering could trip a downstream cross-impact

- **Risk**: Another spec could cite "§7 row #2" as a forward reference. If we remove row #2, that reference rots.
- **Mitigation**: Search the repo for `§7 row #2` / `workspace-dashboard-section-cleanup` cross-references — should return 0 hits (the §6.1 RESOLVED note at L354 already references "§7 row #1" generically). After cleanup, any stale references should be re-pointed.
- **Severity**: NEGLIGIBLE — no references found in current archive reports.

### R5 (NEGLIGIBLE): Conflict with future follow-ups in v1.1-followups/

- **Risk**: The user-locked scope says NO touch of `openspec/changes/v1.1-followups/`. If a parallel agent is working in that directory and references §3/§5/§7 row #2 of `workspace/spec.md`, conflict.
- **Mitigation**: Confirmed v1.1-followups is **untracked** per phase-5-dashboard archive-report §12 ("Untracked — never tracked"). It's sacred territory; we don't touch it. If they reference our 3 lines, they'll need to rebase.
- **Severity**: NEGLIGIBLE — sacred territory by convention.

---

## Carry-Over Status

| Item | Source | Status (post-explore) |
|---|---|---|
| W1: §4.2 versioning row Phase 2 (L303) | phase-5-dashboard verify-report #513 | **RESOLVED-IN-SPIRIT** via §6.1 RESOLVED note at L354; L303 row text remains as historical documentation. Not in scope for this change. |
| W2: archive-status meta-pointer carry-forwards (L16) | phase-5-dashboard verify-report #513 | **ALREADY RESOLVED** — L16 carry-forwards does NOT list `flow-where-cross-project-capability-merge` (verifiable by reading L16 literally). §6.1 RESOLVED note at L354 references "§7 row #1 (this follow-up is now removed from Future Changes)" — row #1 was already removed. Not in scope. |
| §3 row 5 placeholder (L80) | archive-report §9.2 + verify-report #513 | **CONFIRMED IN SCOPE** for this cleanup. |
| §5 row "tui (future)" (L317) | archive-report §9.2 + design #541 | **CONFIRMED IN SCOPE** for this cleanup. |
| §7 row #2 deferred text (L360) | archive-report §9.2 + apply-progress #572 (sort-projects carry-over) | **CONFIRMED IN SCOPE** for this cleanup. |

---

*Generated by the `sdd-explore` sub-agent for `workspace-dashboard-section-cleanup`. This is exploration-only — no code, no tests, no delta spec. The exploration is mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-dashboard-section-cleanup/explore"`, `type: "architecture"`, `capture_prompt: false`.*
