# Proposal: workspace-dashboard-section-cleanup

> **Phase**: propose (SDD pipeline)
> **Change**: `workspace-dashboard-section-cleanup`
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Builds on**: explore #577 (Engram `sdd/workspace-dashboard-section-cleanup/explore`)

---

## 1. Header

| Field | Value |
|-------|-------|
| Change | `workspace-dashboard-section-cleanup` |
| Purpose | Clean stale prose in `workspace/spec.md` carried forward from phase-5-dashboard and sort-projects cycles. Surgical scope: 4 text edits at L73, L80, L317, L360. |
| Builds on | explore #577 — 4 in-scope items at exact line numbers, recommended fixes confirmed |
| Strict TDD | OFF (doc-only) |
| Forecast | ~10–20 LOC of text changes; single PR, well under 400-line budget |

---

## 2. Scope Locked

### In Scope (4 text edits — user-locked)

| # | Location | Action | Description |
|---|----------|--------|-------------|
| 1 | L80 §3 row 5 | UPDATE | Replace `(future)` / `(placeholder)` / `TBD` row with shipped `phase-5-dashboard` reference + 3 flags |
| 2 | L73 §3 intro | UPDATE | `3 confirmed sub-capabilities + 1 placeholder` → `4 confirmed sub-capabilities` (coupled to L80 for consistency) |
| 3 | L317 §5 row | UPDATE | Replace `flow workspace tui (future) / (placeholder)` row with `flow workspace dashboard` + 3 flags + no `--json` |
| 4 | L360 §7 row #2 | REMOVE + renumber | Remove entire row; renumber rows 3–7 → 2–6 (gap-free table) |

**User explicit constraint**: "Mantenelo quirúrgico. No abras otra caja."

### Out of Scope (strictly locked — future cleanup debt)

| Location | Reason |
|----------|--------|
| L28 §1 Purpose bullet | Future change `workspace-spec-section-cleanup-1` |
| L271–277 §4.1 dependency-graph | Same future change |
| L273 §4.1 graph cross-reference | Same future change |

---

## 3. L80 §3 Row 5 — UPDATE

**FIND** (current):
```
| 5 (future) | workspace-dashboard | flow workspace tui / web | Visualization — TBD | 📌 Placeholder | (no delta spec yet — see Future Changes §7) |
```

**REPLACE WITH**:
```
| 5 | workspace-dashboard | flow workspace dashboard | Visualization — read-only Rich MVP for human operators; supports --filter RULES, --sort FIELD, --no-color (no --json — Pattern #538) | ✅ Shipped + archived at phase-5-dashboard | openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md |
```

---

## 4. L73 §3 Intro — Coupled 1-Line Tweak

**FIND** (current):
```
The workspace family has **3 confirmed sub-capabilities + 1 placeholder**:
```

**REPLACE WITH**:
```
The workspace family has **4 confirmed sub-capabilities**:
```

> **Rationale**: L80 is being promoted from placeholder to shipped. §3 intro must reflect 4 confirmed sub-capabilities (not 3+1). This is a tightly-coupled adjacent edit to L80; fixing L80 without L73 would leave the root spec internally inconsistent.

---

## 5. L317 §5 Row — UPDATE

**FIND** (current):
```
| `flow workspace tui` (future) | (Phase 5) | 5 (placeholder) | Dashboard — not yet implemented |
```

**REPLACE WITH**:
```
| `flow workspace dashboard` | [--filter RULES] [--sort FIELD] [--no-color] (Phase 5) | 5 | Read-only Rich MVP (A header + B needs-attention + C archived + D footer); no --json (Pattern #538) |
```

**Flag inventory** (per shipped delta spec `REQ-DASHBOARD-FLAGS`):
- `--filter RULES` ✓ shipped
- `--sort FIELD` ✓ shipped
- `--no-color` ✓ shipped
- `--json` ✗ explicitly absent (Pattern #538: one identity per command)

---

## 6. L360 §7 Row #2 — REMOVE + Renumber 3-7 → 2-6

**FIND** (current, L356-L366):
```
## 7. Future Changes

| # | Change | Scope | Priority | Trigger |
|---|--------|-------|----------|---------|
| 2 | **`workspace-dashboard` (Phase 5)** | TUI (`flow workspace tui`) or web visualization of workspace state (registry + needs_attention + per-project metadata). Will add a new delta spec; this root spec is already anchored. | Low | Future change; requires CLI solidification first (per session #483) |
| 3 | `workspace-hygiene-capability-spec` (optional) | Create `openspec/specs/workspace-hygiene/spec.md` as a top-level capability for the write-side if the delta grows further. | Low | Phase 4 follow-up #2 in archive-report #477 |
...
```

**ACTION**: REMOVE row #2 entirely. Renumber rows 3→2, 4→3, 5→4, 6→5, 7→6.

**Resulting §7 rows** (gap-free):
| # | Change | Scope | Priority | Trigger |
|---|--------|-------|----------|---------|
| 2 | `workspace-hygiene-capability-spec` (optional) | Create `openspec/specs/workspace-hygiene/spec.md` as a top-level capability... | Low | Phase 4 follow-up #2... |
| 3 | `backup-retention-policy` | Currently INDEFINITE in Phase 4... | Low | Operator concern; not blocking |
| 4 | `workspace-hygiene-r1` (deferred) | R1 dirty-git remediation... | Low | Future change if requested |
| 5 | `workspace-hygiene-r3` + `workspace-hygiene-r4` (deferred) | R3 no-tests bootstrap + R4 no-openspec bootstrap... | Low | Future change if requested |
| 6 | Artifact-hygiene move | Phases 1 + 3 still in `openspec/changes/{workspace-intelligence,flow-workspace-status}/`... | Low | Out of scope for this change; separate cleanup |

---

## 7. Acceptance Criteria (4 ACs)

| AC | Description | Verification |
|----|-------------|--------------|
| **AC1** | L80 row 5 updated to reference shipped `phase-5-dashboard` (with all 3 flags, no `--json`, archive path) | Read `workspace/spec.md` L80; confirm row matches replacement text |
| **AC2** | L73 intro updated from `3 confirmed sub-capabilities + 1 placeholder` to `4 confirmed sub-capabilities` | Read `workspace/spec.md` L73; confirm wording |
| **AC3** | L317 row updated from `flow workspace tui (future) / (placeholder)` to `flow workspace dashboard` with 3 flags + no `--json` | Read `workspace/spec.md` L317; confirm row matches replacement text |
| **AC4** | L360 row removed; rows 3-7 renumbered 2-6; §7 table gap-free | Read `workspace/spec.md` §7; confirm 6 rows numbered 2-6 with no gap |

**Preservation gates** (8 existing from phase-5-dashboard):
1. `flow projects ls [--json]` still enumerated in §3 + §5
2. `flow workspace status [--json]` still enumerated in §3 + §5
3. `flow workspace {fix,archive,archived,restore}` still enumerated in §3 + §5
4. 6 dashboard REQ blocks (L170–L234) still have `Source:` lines pointing to archived delta
5. §8 family-shape protocol text unchanged
6. §6 Cross-Impact §6.1 RESOLVED note unchanged
7. Registry v1 REQ unchanged
8. Boundary rule unchanged

---

## 8. Out of Scope (explicit)

- L28 §1 Purpose bullet stale (future `workspace-spec-section-cleanup-1`)
- L271–277 §4.1 dependency-graph still references `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` (same future change)
- L273 §4.1 graph cross-reference `flow workspace tui / web` (same future change)
- No new tests (doc-only change)
- No new verify checks (8 existing still cover)
- No modifications to PR1 (`6651add`) / PR2 (`95e8579`) / PR3 (`778efdb`) / sort-projects (`c9c9650d`) commits
- No `stash`-triggering words in any new code
- No touch of `openspec/changes/v1.1-followups/`

---

## 9. Open Questions (resolved)

| Q | Question | Resolution |
|---|----------|------------|
| Q1 | §3 L80 — Replace with shipped-state row vs. drop entirely? | **Replace** (Option A) — preserves §3 family-overview invariant (1 row per Phase) |
| Q2 | §5 L317 — Replace row with shipped-state vs. remove? | **Replace** (Option A) — preserves §5 CLI surface inventory invariant |
| Q3 | §7 L360 — Remove row vs. mark as landed? | **Remove** (Option A) — §7 is forward-looking by design; renumber 3-7 → 2-6 |
| Q4 | §4.1 L271-277 dependency-graph stale? | **Out of scope** — future `workspace-spec-section-cleanup-1` |

---

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **R1**: Archived `verify-checks.sh Check 5` returns non-zero after cleanup | LOW | Informational | Script is archived historical audit trail; failure is expected and correct |
| **R2**: Markdown table column alignment breaks | LOW | Cosmetic | Replacement text matches existing column widths (Phase 1/3/4 row format) |
| **R3**: L73 coupled 1-line tweak is technically outside user-locked 3 items | LOW | Decision-only | User approved the 4th item in the same locked scope; scope is surgical |

---

## 11. Forecast

| Metric | Value |
|--------|-------|
| Total LOC | ~10–20 (4 text edits in `workspace/spec.md`) |
| Files touched | 1 (`openspec/specs/workspace/spec.md`) |
| Single PR | Yes |
| Chained PR | No |
| Size exception | No |
| Under 400-line budget | Yes |

**Wall-time**:
- `sdd-tasks`: ~5 min (mechanical derivation from locked proposal)
- `sdd-apply`: ~5 min (4 text edits + 1 commit)
- `sdd-verify`: ~5 min (4 ACs + 8 preservation gates)
- `sdd-archive`: ~5 min (single-PR archive)
- **Total remaining**: ~20 min

---

## 12. Pre-existing Failures (out-of-scope reminder)

- 3 lint errors OOS (`cli.py:683 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`)
- 4 sqlite-vec reindex test failures OOS
- 2 mypy yaml-stub errors OOS
- 4 observability_aggregate test failures OOS
- 2 skipped tests OOS
- **None introduced by this change**

---

## 13. Commit Plan (per work-unit-commits skill)

- **Single commit** per PR
- **Message**: `docs(specs): clean §3/§5/§7 stale dashboard prose`
- **NO** "Co-Authored-By" or AI attribution
- **Atomic**: 1 file modified (`workspace/spec.md`)

---

## 14. Rollback Plan

Revert the single commit. No data or state changes. `git revert <commit>` restores exact prior state.

---

## 15. Next SDD Phase

**sdd-spec** — write delta spec (for this change: text edits only, no new REQs; sdd-spec mechanically translates the 4 edits above into spec language).

---

*Generated by the `sdd-propose` sub-agent for `workspace-dashboard-section-cleanup`. Proposal mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-dashboard-section-cleanup/proposal"`, `type: "architecture"`, `capture_prompt: false`.*
