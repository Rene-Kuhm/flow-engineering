# Proposal: workspace-spec-section-cleanup-1

> **Phase**: propose (SDD pipeline)
> **Change**: `workspace-spec-section-cleanup-1`
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Strict TDD**: OFF (doc-only; no test code)
> **Builds on**: explore #593 (3 in-scope items at exact line locations; 3 adjacent items explicitly out of scope)

## 1. Intent

Clean 3 stale-prose items in `openspec/specs/workspace/spec.md` that were carried forward from the `workspace-dashboard-section-cleanup` cycle as future cleanup debt (archive-report §9 carry-over items #4/#5/#6). The phase-5-dashboard shipped at commit `778efdb`; `workspace/spec.md` still references it as a placeholder in 3 locations. This change brings §1 Purpose bullet and §4.1 dependency-graph box in line with the shipped state — nothing more (Pattern #582: "limpiar lo prometido, nada más").

## 2. Scope

### In Scope (3 user-locked text edits)

| # | Location | Action | What |
|---|----------|--------|------|
| 1 | L28 §1 Purpose bullet | UPDATE | Replace stale `(Phase 5 placeholder) will surface workspace state in a TUI or web visualization.` with shipped-state bullet |
| 2 | L271-277 §4.1 dependency-graph box | UPDATE | Replace the 7-line PLACEHOLDER STUB box with the shipped phase-5-dashboard state |
| 3 | L273 §4.1 graph cross-reference | UPDATE (subsumed in #2) | `flow workspace tui / web` → `flow workspace dashboard` (1-line character swap, absorbed into box replacement) |

### Out of Scope (explicit locks)

| Location | Reason |
|----------|--------|
| L69 §2 boundary stress test | Future cleanup — `workspace-spec-section-cleanup-2` |
| L269 §4.1 graph arrow label (`Phase 5 (future)`) | Future cleanup — `workspace-spec-section-cleanup-2` |
| L291 §4.1 graph note (`Phase 5 (future) will depend...`) | Future cleanup — `workspace-spec-section-cleanup-2` |
| Any code under `src/` | Doc-only change |
| Any new tests | Doc-only change |
| Any new verify checks | 8 existing from phase-5-dashboard still cover all invariants |
| `openspec/changes/v1.1-followups/` | Sacred territory; untouched |
| Phase 5.2 (TUI/web) | Explicitly deferred per REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE (L230) |
| PR1/PR2/PR3/sort-projects/workspace-dashboard-section-cleanup commits | Byte-identical on `main`; non-negotiable |

## 3. Approach

Three mechanical text replacements in `openspec/specs/workspace/spec.md`. No code, no tests, no new dependencies.

### L28 §1 Purpose bullet — UPDATE

**FIND** (verbatim):
```
- (Phase 5 placeholder) will surface workspace state in a TUI or web visualization.
```

**REPLACE WITH**:
```
- visualizes workspace state in a read-only Rich dashboard for human operators (`flow workspace dashboard` with `--filter RULES`, `--sort FIELD`, `--no-color`; no `--json` per Pattern #538).
```

**Rationale**: Removes both stale markers (`(Phase 5 placeholder)` + `TUI or web`). Mirrors the discipline of L24-L27 (each ships a named CLI surface + flags). Matches §3 L80 + §5 L317 phrasing from the prior cleanup cycle. Deferred TUI/web/Phase 5.2 surfaces remain captured in REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE at L230.

### L271-277 §4.1 dependency-graph box — UPDATE

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

**REPLACE WITH** (verbatim, 7 lines — same column widths, ASCII alignment preserved):
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

**Rationale**: Addresses all 3 stale markers simultaneously:
- L273 fixed: `flow workspace tui / web` → `flow workspace dashboard`
- L274 fixed: `STATUS: PLACEHOLDER STUB` → `Phase 5: 6 REQs incl. Rich MVP + ...`
- L275-L276 fixed: stale `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` reference + §7 cross-reference → `Source: phase-5-dashboard (shipped)`

Box height stays at 7 lines (0 net lines delta). Column widths match P1/P3/P4 boxes above for ASCII alignment integrity.

### L273 §4.1 graph cross-reference — UPDATE (subsumed)

L273's fix is the `tui / web` → `dashboard` character swap on line 2 of the box. It is **subsumed** in the L271-277 box replacement above. Documented here for the 3-item scope-lock clarity only.

## 4. Capabilities

### Modified Capabilities

| Capability | What changes | Delta spec |
|------------|-------------|-----------|
| `workspace-dashboard` (Phase 5) | §1 Purpose bullet and §4.1 dependency-graph box text updated to reflect shipped state (no behavioral change) | `openspec/changes/workspace-spec-section-cleanup-1/specs/workspace/spec.md` |

No new capabilities. No new requirements. This is prose-only cleanup.

## 5. Acceptance Criteria

- [ ] **AC1**: L28 §1 Purpose bullet updated — no `(Phase 5 placeholder)` marker, no `TUI or web visualization` framing; bullet reads shipped Rich dashboard state with CLI surface + 3 flags + no-`--json` invariant
- [ ] **AC2**: L271-277 §4.1 dependency-graph box updated — no `PLACEHOLDER STUB`, no `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` reference, no `§7 Future Changes`; box reflects phase-5-dashboard shipped state (6 REQs, Rich MVP, 3 flags, no `--json`)
- [ ] **AC3**: L273 in-box cross-reference updated — `flow workspace dashboard` (no `tui / web` slash-separated framing)
- [ ] **AC4 (preservation gate)**: No changes to `openspec/changes/v1.1-followups/`, no modifications to any locked commit, no new runtime dependencies introduced

## 6. Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/specs/workspace/spec.md` | Modified | 3 text edits: L28 (1 line), L271-277 (7-line box replacement with L273 subsumed) |

## 7. Rollback Plan

`git revert HEAD` restores pre-change state without affecting code, tests, registry, or any other spec. Doc-only change; revert is safe and atomic.

## 8. Dependencies

- Phase 5 dashboard shipped on `main` at commit `778efdb` (confirmed present at HEAD `1ef33cf`)
- Prior cleanup cycle artifacts intact: archive-report §9 carry-over list confirms items #4/#5/#6 as this change's scope

## 9. Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Scope creep at apply (tempting to also fix L69/L269/L291) | LOW | Explicit out-of-scope list in commit message + proposal artifact |
| ASCII alignment drift in box replacement | LOW | Replacement text matches existing column widths (7 lines, same character count delta pattern as P1/P3/P4 boxes above) |
| Accidental v1.1-followups/ touch | LOW | Verify with `git status --short` post-apply; no touch is the explicit gate |

## 10. Open Questions

All resolved at scope-lock:

- **Q1**: L28 UPDATE vs. REMOVE vs. SHORTEN? → **UPDATE** (recommended; matches prior cycle's §3 L80 + §5 L317 discipline; best §1 discoverability)
- **Q2**: L271-277 REPLACE vs. MINIMAL vs. DROP? → **REPLACE** (recommended; cleanest end state, mirrors P1/P3/P4 box discipline)
- **Q3**: L273 subsumed in L271-277 vs. separate edit? → **SUBSUMED** (1-line character swap absorbed into box replacement)
- **Q4**: Expand to L69/L269/L291? → **NO** — user locked scope; defer to `workspace-spec-section-cleanup-2`

## 11. Forecast

- **Files modified**: `openspec/specs/workspace/spec.md` (1 file)
- **Net LOC**: ~10-15 lines of text changes (3 edits; 0 net lines at each location)
- **PR strategy**: Single PR, well under 400-line budget (~15 LOC, < 5% of budget)
- **Chained PR**: Not needed
- **Size exception**: Not needed
- **Total wall-time remaining**: ~20 min (tasks=5 + apply=5 + verify=5 + archive=5; push deferred after user merge per Pattern #584)

## 12. Commit Plan

- **Message**: `docs(specs): clean §1 + §4.1 stale dashboard prose`
- **Files**: `openspec/specs/workspace/spec.md` (1 file, 3 text edits)
- **Atomic**: Yes
- **NO** `stash`-triggering words
- **NO** AI attribution

---

*Proposal for `workspace-spec-section-cleanup-1`. Mirrored to Engram `sdd/workspace-spec-section-cleanup-1/proposal` (type: architecture, capture_prompt: false). Scope locked: 3 items in, 3 adjacent items deferred to `workspace-spec-section-cleanup-2`. "Mantenemos la regla: limpiar lo prometido, nada más."*
