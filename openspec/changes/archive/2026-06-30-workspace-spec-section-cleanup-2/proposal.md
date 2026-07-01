# Proposal: workspace-spec-section-cleanup-2

## Header

| Field | Value |
|-------|-------|
| Change | `workspace-spec-section-cleanup-2` |
| Purpose | Clean the 3 stale-prose items deferred from `workspace-dashboard-section-cleanup` explore #577 and locked as carry-over in `workspace-spec-section-cleanup-1` design #598 |
| Builds on | explore #606 (3 in-scope items at exact line numbers) |
| Artifact store | openspec |
| Strict TDD | OFF (doc-only) |
| Forecast | ~5-10 LOC of text changes; well under 400-line single-PR budget |

## 1. Intent

Retire the remaining carry-over debt from `workspace-dashboard-section-cleanup`: 3 stale-prose items in `openspec/specs/workspace/spec.md` that both prior cycles correctly deferred (§2 boundary stress test, §4.1 graph arrow label, §4.1 graph note). After this change, the `workspace-dashboard-section-cleanup` carry-over debt is **fully retired**.

**User framing**: *"Cerramos esta deuda y recién después evaluamos si queda algo real."*

## 2. Approach (locked)

Reaffirm the 3 user-locked in-scope text edits (L69, L269, L291). NO expansion to L299 or any other stale text. NO expansion to Phase 5.2 (TUI/web). NO new tests, verify checks, or code changes.

## 3. In-Scope Edit 1 — L69 §2 boundary stress test

**FIND (L69, verbatim):**
```
| "Show me a TUI of my workspace." | ✅ YES (Phase 5) | Project dashboard |
```

**REPLACE WITH:**
```
| "Show me a Rich dashboard of my workspace." | ✅ YES (Phase 5) | Project dashboard (Rich MVP) |
```

**Rationale**: Phase-5-dashboard shipped Rich MVP (not TUI); the TUI framing was a future-placeholder. The boundary stress test reflects the shipped state. `(Rich MVP)` parenthetical in the right column distinguishes from hypothetical Phase 5.2 TUI; mirrors §3 L80 + §4.1 L271-278 box. Single substitution, net 0 line delta.

## 4. In-Scope Edit 2 — L269 §4.1 graph arrow label

**FIND (L269, verbatim):**
```
                                                  │ Phase 5 (future)
```

**REPLACE WITH:**
```
                                                  │ Phase 5 (shipped)
```

**Rationale**: Phase-5-dashboard shipped; `(future)` label is stale. Same character count (16 chars each) preserves ASCII column alignment with the surrounding box. Canonical wording already established in §1 L28 + §3 L80 + §4.1 L277 box. Single 3-character substitution, net 0 line delta.

## 5. In-Scope Edit 3 — L291 §4.1 graph note

**FIND (L291, verbatim):**
```
- Phase 5 (future) will depend on Phase 3 (read aggregation) + Phase 4 (registry).
```

**REPLACE WITH:**
```
- Phase 5 depended on Phase 3 (read aggregation) + Phase 4 (registry).
```

**Rationale**: Phase-5-dashboard shipped; `(future) will depend` framing is stale. Past tense is appropriate for a historical fact (the dependency existed during the dependency cycle). Single line replacement, net 0 line delta.

## 6. Acceptance Criteria

| AC | Description |
|----|-------------|
| AC1 | L69 §2 boundary stress test updated to `"Show me a Rich dashboard of my workspace."` with `(Rich MVP)` right-column annotation (no TUI; phase-5-dashboard shipped) |
| AC2 | L269 §4.1 graph arrow label updated to `Phase 5 (shipped)` (no `(future)`; 16 chars preserved) |
| AC3 | L291 §4.1 graph note updated to past tense `Phase 5 depended` (no `(future) will depend`) |

## 7. Out of Scope (explicit locks)

- **L299** §4.2 trigger row — EXCLUDED (user-locked; deferred to post-merge evaluation per Pattern #605)
- Any other stale text beyond the 3 in-scope items — EXCLUDED (user-locked; carry-over debt fully retired after this change)
- NO new tests (doc-only; no test code)
- NO new verify checks (8 existing from phase-5-dashboard still cover all invariants)
- NO modifications to PR1 (`6651add`) / PR2 (`95e8579`) / PR3 (`778efdb`) / sort-projects (`c9c9650d`) / workspace-dashboard-section-cleanup chain commits / workspace-spec-section-cleanup-1 commits (`43e76ed`, `04575f9`)
- NO `stash`-triggering words in commit message
- NO AI attribution in commit message (per AGENTS.md)
- NO touch of `openspec/changes/v1.1-followups/`
- NO expand to Phase 5.2 (TUI/web)
- NO new runtime dependencies

## 8. Open Questions (resolved)

| Q | Answer |
|---|--------|
| Q1: L69 fix wording | Option A — `"Show me a Rich dashboard of my workspace."` + `(Rich MVP)`; mirrors §3 L80 + §4.1 L271-278 box |
| Q2: L269 label fix | Option A — `(future)` → `(shipped)`; 16 chars each, ASCII alignment preserved |
| Q3: L291 tense fix | Option A — past tense `Phase 5 depended`; matches user's explicit instruction |
| Q4: L299 §4.2 trigger row | EXCLUDED — user-locked "No expandir a L299" |

## 9. Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| L269 ASCII alignment drift | LOW | Both `(future)` and `(shipped)` are 16 chars; byte-identical column count |
| L291 past-tense style differs from prior 2 bullets | LOW | Acceptable — L291 uniquely describes a SHIPPED phase; prior bullets describe ongoing dependencies |
| v1.1-followups/ accidental touch | NEGLIGIBLE | Sacred territory; preservation gate in design |

## 10. Rollback Plan

`git revert HEAD` — single-commit atomic rollback (1 file, 3 single-line replacements).

## 11. Forecast

| File | Change |
|------|--------|
| `openspec/specs/workspace/spec.md` | 3 single-line replacements at L69, L269, L291 (~5-10 LOC) |

- Single PR, no chained PR needed
- No `size:exception` needed
- No new tests, no new verify checks
- Total: ~5-10 LOC

## 12. Pre-existing Failures (out-of-scope reminder)

- 3 pre-existing lint errors OOS (cli.py:683, test_cli_where_cross_project.py:{33, 295})
- 4 pre-existing reindex test failures OOS (sqlite-vec opt-in)
- 2 pre-existing mypy yaml-stub errors OOS
- 4 pre-existing observability_aggregate test failures OOS
- 2 pre-existing skipped tests OOS

All pre-existing; NOT introduced by this change.

## 13. Commit Plan

- **Single commit** per PR
- **Message**: `docs(specs): clean §2 + §4.1 stale future framing`
- NO AI attribution
- NO `stash`-triggering words
- Atomic — 1 file modified (`workspace/spec.md`), 3 single-line replacements
