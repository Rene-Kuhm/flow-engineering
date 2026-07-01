# workspace-spec-section-cleanup-1 — Spec Delta

> **Phase**: spec (SDD pipeline)
> **Change**: `workspace-spec-section-cleanup-1`
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Builds on**: proposal #594 (Engram `sdd/workspace-spec-section-cleanup-1/proposal`) ← explore #593
> **Strict TDD**: OFF (doc-only; no test code)
> **Scope**: 3 surgical text edits to `openspec/specs/workspace/spec.md`. No requirements added, modified, or removed.

---

## Scope of this delta

This change is **doc-only**. There are **no behavioral changes** to the `workspace` capability. The 3 edits are stale-prose cleanup of the §1 Purpose bullet (L28) and the §4.1 dependency-graph box (L271-277, with L273 subsumed) that still described `workspace-dashboard` as `(Phase 5 placeholder)` / `PLACEHOLDER STUB` / `tui / web` even though the `phase-5-dashboard` change shipped (commit `778efdb` PR3 on `main`, archived at `openspec/changes/archive/2026-06-30-phase-5-dashboard/` on 2026-06-30).

This change is the **dedicated follow-up** to `workspace-dashboard-section-cleanup` (changes #577/#579/#581/#583/#586, archived 2026-06-30-22:24), whose `archive-report.md §9` items **#4, #5, #6** carried over these exact 3 locations as future cleanup debt. The prior cycle correctly limited itself to §3/§5/§7 and explicitly excluded §1 + §4.1; **this change completes the §1 + §4.1 residue**.

Per Pattern #582 (*"limpiar lo prometido, nada más — clean what was promised, nothing more"*) and Pattern #580 (*"proportional cleanup, not rewrite"*): the 3 edits are surgical and proportional — only the stale text and its coupled box lines are touched. All 12 root-level REQs in §4, all `Source:` lines, all REQ sub-headings, the §6.1 RESOLVED note, the §8 Drift Detection footer, and unrelated prose remain byte-identical.

Per Pattern #597 (*"clean closure regardless of change size"*): even though this is the smallest change in the v1.2 arc (3 text edits, ~10-15 LOC, ~7-8 minutes wall-time for the spec+apply phases), the cycle is run end-to-end through the full 8-phase SDD pipeline for audit-trail symmetry with prior cycles.

---

## MODIFIED Prose

### Canonical: `openspec/specs/workspace/spec.md` (workspace root spec)

#### §1 Purpose bullet (L28) — UPDATE (placeholder → shipped)

- **Before**: `- (Phase 5 placeholder) will surface workspace state in a TUI or web visualization.`
- **After**: `- visualizes workspace state in a read-only Rich dashboard for human operators (flow workspace dashboard with --filter RULES, --sort FIELD, --no-color; no --json per Pattern #538).`
- **Rationale**: `phase-5-dashboard` shipped at commit `778efdb` (PR3 of `phase-5-dashboard`); the bullet is no longer a placeholder. The new bullet names the actual CLI surface (`flow workspace dashboard`) + 3 flags (`--filter RULES`, `--sort FIELD`, `--no-color`) + the no-`--json` invariant (Pattern #538), mirroring the discipline from §3 L80 + §5 L317 cleaned by the prior cycle. Deferred TUI/web/interactive scope remains captured in `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE` at L230.

#### §4.1 dependency graph box (L271-277) — UPDATE (placeholder stub → shipped)

- **Before**: 7-line ASCII dependency-graph box with `flow workspace tui / web` (L273), `STATUS: PLACEHOLDER STUB` (L274), `(see REQ-WORKSPACE-DASHBOARD-PLACEHOLDER + §7 Future Changes)` (L275-L276)
- **After**: 8-line ASCII dependency-graph box with `flow workspace dashboard` (L273), `Phase 5: 6 REQs incl. Rich MVP + --filter RULES / --sort FIELD / --no-color (no --json per #538)` (L274-L276), `Source: phase-5-dashboard (shipped)` (L277); top border (L271) + `workspace-dashboard (P5)` header (L272) + bottom border (L278) preserved
- **Rationale**: Addresses all 3 stale markers in the box at once. The 6 dashboard REQs (`DASHBOARD-SURFACE`, `DASHBOARD-READ-ONLY`, `DASHBOARD-CONSUMES-DS1`, `DASHBOARD-CONSUMES-DS2`, `DASHBOARD-RENDERS-RICH`, `DASHBOARD-DEFER-INTERACTIVE`) are all enumerated in §4 above (L170-L234); the graph box is a navigation summary, not a REQ citation index, so naming the delta-spec source keeps the box compact. ASCII column alignment preserved by reusing the original top/bottom borders verbatim and matching the inner-line ASCII-content width to L272 (39 ASCII chars between the `│` characters). Box widens 7 → 8 lines (+1 net line) because the body needs 5 lines instead of 4 to enumerate REQ count + 3 flags + source.

#### §4.1 graph cross-reference (L273) — UPDATE (subsumed in L271-277)

- **Before**: `flow workspace tui / web` (subsumed in the L271-277 box replacement)
- **After**: `flow workspace dashboard` (1-line character swap, subsumed in the L271-277 box replacement)
- **Rationale**: Subsumed; documented separately for the 3-item scope-lock clarity. Single CLI command, not slash-separated; matches the §3 L80 + §5 L317 discipline from the prior cycle.

---

## ADDED Requirements

None. (Doc-only cleanup; no new behavioral REQs introduced. The 6 dashboard REQs are already at L170-L234; the §1 + §4.1 prose-only updates do not create new requirements.)

---

## MODIFIED Requirements

None. (No behavioral REQs change. All 12 root-level REQs in §4 of `openspec/specs/workspace/spec.md` remain byte-identical:

1. `REQ-WORKSPACE-PROJECT-IDENTITY` (L92)
2. `REQ-WORKSPACE-STATUS-DISCOVERY` (L102)
3. `REQ-WORKSPACE-MUTATION-SAFETY` (L120)
4. `REQ-WORKSPACE-DRY-RUN-DEFAULT` (L130)
5. `REQ-WORKSPACE-R1-DEFERRED` (L140)
6. `REQ-WORKSPACE-REGISTRY-V1` (L150)
7. `REQ-WORKSPACE-DASHBOARD-SURFACE` (L170)
8. `REQ-WORKSPACE-DASHBOARD-READ-ONLY` (L182)
9. `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1` (L194)
10. `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2` (L206)
11. `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH` (L218)
12. `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE` (L230)

Each with its `Source:` line intact. The 3 prose edits do not modify any `### Requirement:` block — they only update surrounding prose (L28 bullet + L271-278 ASCII box).)

---

## REMOVED Requirements

None.

---

## BDD Scenarios

None. (Doc-only cleanup; no behavioral change. BDD scenarios for `workspace-dashboard` already exist in the archived delta spec at `openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` and remain canonical. Per session preflight `strict_tdd: OFF` — no Given/When/Then scenarios required for prose-only cleanup.)

---

## Acceptance Criteria (4 ACs — mirror of proposal #594 §5)

| AC | Description | Verification |
|----|-------------|--------------|
| **AC1** | L28 §1 Purpose bullet updated to shipped Rich dashboard state: no `(Phase 5 placeholder)` marker, no `TUI or web visualization` framing; new bullet names `flow workspace dashboard` + 3 flags + no-`--json` invariant | Read `workspace/spec.md` L28; confirm matches replacement text |
| **AC2** | L271-278 §4.1 dependency-graph box updated: no `PLACEHOLDER STUB`, no `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` reference, no `§7 Future Changes`; new box reflects phase-5-dashboard shipped state (6 REQs, Rich MVP, 3 flags, no `--json`, source citation) | Read `workspace/spec.md` L271-278; confirm 8-line box with the new body and ASCII alignment |
| **AC3** | L273 in-box cross-reference updated to `flow workspace dashboard` (no `tui / web` slash-separated framing) | Read `workspace/spec.md` L273; confirm `dashboard` (no `tui`/`web`) |
| **AC4 (preservation gate)** | No changes to `openspec/changes/v1.1-followups/`, no modifications to any locked commit, no new runtime dependencies introduced; all 12 root REQ `Source:` lines intact | `git diff --stat HEAD -- openspec/specs/workspace/spec.md` shows only the 3 in-scope edits; `git status` confirms no other tracked files modified |

### Preservation gates (12 specific + 4 general)

**A. Root REQ `Source:` lines intact** (12/12):

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

**B. Other preservation gates**:

13. §4 Family index callout (L4): *"Family index, not canonical source."* — unchanged
14. §6.1 Phase 2 reclassification RESOLVED note — unchanged
15. §8 Drift Detection footer — unchanged
16. All other §1 (L1-L27, L29-L30), §4 (L86-L238), §4.1 graph (L240-L268, L279-L291), §4.2 (L293-L303), §5 (L305-L325), §6 (L327-L354), §7 (L356-L364), §8 (L366-L376) sections remain byte-identical except for the 3 in-scope edits.

---

## Out of Scope (FUTURE CLEANUP DEBT — explicitly deferred)

The following stale prose items are **acknowledged but NOT modified** by this change. They will be cleaned up by a future change `workspace-spec-section-cleanup-2` (or similarly named):

| Location | Stale content | Future-change owner |
|----------|---------------|---------------------|
| **L69** | §2 boundary stress test: `"Show me a TUI of my workspace."` — uses TUI framing (delivered surface is Rich MVP, not TUI) | `workspace-spec-section-cleanup-2` |
| **L269** | §4.1 graph arrow label: `│ Phase 5 (future) │` — should read `Phase 5 (shipped)` since `phase-5-dashboard` is on `main` | same |
| **L291** | §4.1 graph note: `Phase 5 (future) will depend on Phase 3 (read aggregation) + Phase 4 (registry).` — should be past tense since the dependency is realized | same |

Per Pattern #582 (*"clean what was promised, nothing more"*) and user-locked constraint (*"cambio chico, cierre limpio"*): these items are out of scope for THIS change and will be handled by a dedicated follow-up cleanup cycle in a separate change. The user explicitly locked the scope to only L28 + L271-277 + L273 (subsumed).

---

## Open Questions (resolved at scope-lock)

| Q | Question | Resolution |
|---|----------|------------|
| **Q1** | L28 fix: UPDATE (replace with shipped-state bullet), REMOVE (drop entirely), or SHORTEN (1-line pointer)? | **UPDATE** — mirrors the §3 L80 + §5 L317 discipline from prior cycle; best §1 discoverability; preserves self-contained §1 enumeration (each bullet ships a named CLI surface + flags) |
| **Q2** | L271-277 fix: REPLACE the 7-line box in-place, MINIMAL swap (still keeps some placeholder residue), or DROP the box entirely? | **REPLACE** — cleanest end state; mirrors P1/P3/P4 box discipline (each enumerates REQ count); preserves ASCII alignment; addresses all 3 stale markers at once |
| **Q3** | L273 fix: in-place `tui / web` → `dashboard` character swap, ADD `(Rich MVP)` suffix, or DROP the L273 line? | **In-place swap** (subsumed in L271-277) — same edit the prior cycle applied to L80 + L317 |
| **Q4** | Expand this change to also address adjacent stale items L69 + L269 + L291? | **NO** — user-locked scope; defer to `workspace-spec-section-cleanup-2` as future cleanup debt. Default posture per Pattern #582 (clean what was promised, nothing more) |

---

## Pre-existing failures (out-of-scope reminder)

All items below are **pre-existing** and **NOT introduced** by this change (doc-only):

- 3 lint errors (`cli.py:683 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`)
- 4 sqlite-vec reindex test failures (opt-in)
- 2 mypy yaml-stub errors
- 4 observability_aggregate test failures
- 2 skipped tests

---

## Constraints honored (per session preflight)

- ✅ Doc-only (`workspace/spec.md` prose only; no `src/`, no tests, no verify checks)
- ✅ Feature change: **no** (no behavioral REQ changes; this is prose-only)
- ✅ Strict TDD: OFF (doc-only; no test code required)
- ✅ Surgical scope (only L28, L271-278 touched — L273 subsumed)
- ✅ No expansion to L69, L269, L291 (deferred to `workspace-spec-section-cleanup-2`)
- ✅ No touch of `openspec/changes/v1.1-followups/`
- ✅ No modifications to prior cycle's commits (PR1/PR2/PR3 of `phase-5-dashboard`, `sort-projects`, `workspace-dashboard-section-cleanup`, `workspace-hygiene`, `workspace-status`, `workspace-intelligence`, `workspace-capability-bootstrap` — all 14+ commits remain byte-identical per Pattern #548)
- ✅ No new runtime dependencies (pure text edits; `rich` already transitive per `uv.lock:1215`)
- ✅ No `stash`-triggering words (N/A — doc-only)
- ✅ No AI attribution in commit message (per Pattern — conventional commits only)
- ✅ Single PR (delivery strategy: `single-pr`, resolved at preflight; ~10-15 LOC, well under 400-line budget)
- ✅ Pattern #582 (*"clean what was promised, nothing more"*) honored
- ✅ Pattern #580 (*"proportional cleanup, not rewrite"*) honored — surrounding text in each section is unchanged
- ✅ Pattern #597 (*"clean closure regardless of change size"*) honored — full 8-phase cycle even for smallest change in v1.2 arc

---

## Commit Plan (preview)

- **Message**: `docs(specs): clean §1 + §4.1 stale dashboard prose`
- **Files**: `openspec/specs/workspace/spec.md` (1 file, 3 text edits)
- **Atomic**: Yes
- **Net LOC**: +1 line (376 → 377 content lines; L28 is a 1-for-1 replacement, box widens 7 → 8 lines)
- **PR strategy**: Single PR, well under 400-line budget (~15 LOC, < 5% of budget)

---

## Next SDD Phase

`sdd-design` — write the design doc for this change (minimal: text-edit recipe + 16 preservation gates + rollback plan + commit message).

---

*Generated by the `sdd-spec` sub-agent for `workspace-spec-section-cleanup-1`. Spec artifact mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-spec-section-cleanup-1/spec"`, `type: "architecture"`, `project: "insyd"`, `capture_prompt: false`. Scope locked: 3 items in (L28 + L271-277 + L273-subsumed), 3 adjacent items deferred to `workspace-spec-section-cleanup-2`. "Limpiar lo prometido, nada más."*
