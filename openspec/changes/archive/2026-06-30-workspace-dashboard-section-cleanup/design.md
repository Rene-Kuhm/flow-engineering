# Design: workspace-dashboard-section-cleanup

> **Phase**: design (4th of 8)
> **Change**: `workspace-dashboard-section-cleanup`
> **Strict TDD**: OFF (doc-only)
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Design philosophy**: "limpiar lo prometido, nada más" (Pattern #582)

---

## Header

| Field | Value |
|-------|-------|
| Change | `workspace-dashboard-section-cleanup` |
| Phase | design (4th of 8) |
| Strict TDD | OFF (doc-only) |
| Inputs | spec #581 (4 text edits + 4 ACs) ← proposal #579 ← explore #577 |
| Output | `design.md` — 4 components only (text edit recipe + 12 preservation gates + rollback plan + commit message) |
| Forecast | 5 min wall-time |
| Files touched | 1 (`openspec/specs/workspace/spec.md`) |
| Net LOC | ~17 lines |

---

## 1. Architecture Overview

This is the **smallest design phase in the v1.2 arc** — a doc-only cleanup of 4 stale prose lines in `openspec/specs/workspace/spec.md`. The design is a **closed box** (Pattern #582): what we're doing, how to verify, how to roll back. No architectural decisions, no new design surface, no data flow changes.

The change cleans 4 stale sentences that still describe `workspace-dashboard` as `(future)` / `(placeholder)` / `TBD`, even though `phase-5-dashboard` shipped (PR1 `6651add` + PR2 `95e8579` + PR3 `778efdb` on main; archived at `openspec/changes/archive/2026-06-30-phase-5-dashboard/`). 4 text edits at L73 / L80 / L317 / L360. 1 file. 1 commit. 1 PR. Well under the 400-line single-PR budget.

---

## 2. Component 1 — Text Edit Recipe

The 4 locked text edits (from spec #581; line numbers confirmed by explore #577).

### 2.1 Edit 1 — L73 §3 intro (coupled 1-line tweak)

| Field | Value |
|-------|-------|
| File | `openspec/specs/workspace/spec.md` L73 |
| Action | UPDATE (1 line) |
| **Before** | `The workspace family has **3 confirmed sub-capabilities + 1 placeholder**:` |
| **After** | `The workspace family has **4 confirmed sub-capabilities**:` |
| **Rationale** | L80 row 5 is being promoted from placeholder to shipped. §3 intro must reflect 4 confirmed (not 3+1) to remain internally consistent. Tightly coupled adjacent edit to L80. |

### 2.2 Edit 2 — L80 §3 row 5 (UPDATE — placeholder → shipped)

| Field | Value |
|-------|-------|
| File | `openspec/specs/workspace/spec.md` L80 |
| Action | UPDATE (row text) |
| **Before** | `\| 5 (future) \| workspace-dashboard \| flow workspace tui / web \| Visualization — TBD \| 📌 Placeholder \| (no delta spec yet — see Future Changes §7) \|` |
| **After** | `\| 5 \| workspace-dashboard \| flow workspace dashboard \| Visualization — read-only Rich MVP for human operators; supports --filter RULES, --sort FIELD, --no-color (no --json — Pattern #538) \| ✅ Shipped + archived at phase-5-dashboard \| openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md \|` |
| **Rationale** | `phase-5-dashboard` shipped; dashboard is no longer future. Row must reference the canonical delta archive path + all 3 shipped flags (`--filter RULES`, `--sort FIELD`, `--no-color`). `--json` absent per Pattern #538 (one identity per command). |

### 2.3 Edit 3 — L317 §5 row (UPDATE — `tui (future)` → shipped `dashboard`)

| Field | Value |
|-------|-------|
| File | `openspec/specs/workspace/spec.md` L317 |
| Action | UPDATE (row text) |
| **Before** | `\| `flow workspace tui` (future) \| (Phase 5) \| 5 (placeholder) \| Dashboard — not yet implemented \|` |
| **After** | `\| `flow workspace dashboard` \| [--filter RULES] [--sort FIELD] [--no-color] (Phase 5) \| 5 \| Read-only Rich MVP (A header + B needs-attention + C archived + D footer); no --json (Pattern #538) \|` |
| **Rationale** | Command renamed from `tui` (planned) to `dashboard` (shipped). Three shipped flags documented. `--json` explicitly absent per Pattern #538. TUI-style dashboards deferred to Phase 5.2 per `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE`. |

### 2.4 Edit 4 — L360 §7 row #2 (REMOVE + renumber 3-7 → 2-6)

| Field | Value |
|-------|-------|
| File | `openspec/specs/workspace/spec.md` L356-L364 |
| Action | REMOVE row #2; RENUMBER rows 3-7 → 2-6 (gap-free) |
| **Before** | `## 7. Future Changes ... \| 2 \| **workspace-dashboard** (Phase 5) ... Future change; requires CLI solidification first ... \| 3 \| workspace-hygiene-capability-spec (optional) ... \| 4 \| backup-retention-policy ... \| 5 \| workspace-hygiene-r1 (deferred) ... \| 6 \| workspace-hygiene-r3 + workspace-hygiene-r4 (deferred) ... \| 7 \| Artifact-hygiene move ...` |
| **After** | `## 7. Future Changes ... \| 2 \| workspace-hygiene-capability-spec (optional) ... \| 3 \| backup-retention-policy ... \| 4 \| workspace-hygiene-r1 (deferred) ... \| 5 \| workspace-hygiene-r3 + workspace-hygiene-r4 (deferred) ... \| 6 \| Artifact-hygiene move ...` |
| **Rationale** | §7 is forward-looking by design (per §8 family-shape protocol at L373). `phase-5-dashboard` has shipped, so the deferred entry no longer belongs here. REMOVE preserves the invariant "every row is forward-looking"; renumbering keeps the table gap-free. The §6.1 RESOLVED note at L354 already references "§7 row #1 (now removed)" — symmetrical precedent. |

### 2.5 Edit Summary

| # | Location | Section | Action | Net Δ |
|---|----------|---------|--------|-------|
| 1 | L73 | §3 intro | UPDATE | -1 line |
| 2 | L80 | §3 row 5 | UPDATE | 0 lines (replacement) |
| 3 | L317 | §5 row | UPDATE | 0 lines (replacement) |
| 4 | L360-L364 | §7 row #2 + renumber | REMOVE | -1 line (5 row renumbers net 0) |
| **Total** | | | **4 edits** | **~17 lines net when counting surrounding context (7 added + 24 removed across the 4 hunks, per `git diff --stat` estimates)** |

---

## 3. Component 2 — 12 Preservation Gates

12 gates must remain PASS after this change. Each is a byte-identical check against the pre-change state (`main` HEAD `44f9e54`).

| # | Gate | Verification |
|---|------|--------------|
| **1** | **PR1 commit `6651add` byte-identical** (data layer untouched) | `git show 6651add --stat` returns same file set |
| **2** | **PR2 commit `95e8579` byte-identical** (filter/sort/color/rendering untouched) | `git show 95e8579 --stat` returns same file set |
| **3** | **PR3 commit `778efdb` byte-identical** (Click integration + verify + ACs untouched) | `git show 778efdb --stat` returns same file set |
| **4** | **sort-projects commit `c9c9650d` byte-identical** (`needs_by_name` + DeprecationWarning untouched) | `git show c9c9650d --stat` returns same file set |
| **5** | **7 `Source:` lines for original root REQs intact** at L96/L114/L124/L134/L144/L164/L174 | byte-identical to HEAD `44f9e54`; `grep -F "Source:" openspec/specs/workspace/spec.md \| wc -l` → 13 (7 original + 6 dashboard) |
| **6** | **6 new `Source:` lines for dashboard REQs intact** at L170/L186/L198/L210/L222/L234 | byte-identical to HEAD `44f9e54` |
| **7** | **"Family index, not canonical source" callout at L4** | byte-identical (intact); preserves navigation invariant |
| **8** | **§6.1 Cross-Impact RESOLVED note at L354** | byte-identical (intact); references both "§7 row #1" + "§7 row #2" both removed (symmetrical) |
| **9** | **§8 Drift Detection footer at L366+** | byte-identical (intact); family-shape protocol text at L373 still applies |
| **10** | **`v1.1-followups/` untouched** | still untracked; never tracked; sacred territory preserved per phase-5-dashboard archive-report §12 |
| **11** | **AC9 byte-identical guard green** | `test_flow_projects_ls_json_byte_identical_envelope` PASSED on main `44f9e54` (full suite 1513/1513 at HEAD) |
| **12** | **No `stash`-triggering words in commit message** | grep on commit message returns 0 hits for `stash` / `worktree` / `dirty`-adjacent regex; doc-only, so N/A for code, but verified explicitly per the AGENTS.md guard |

**Sanity checks**: After apply, all 12 gates must PASS. The verification phase (`sdd-verify`) iterates each gate against the post-apply state and produces `verify-report.md` mirroring the gate table.

---

## 4. Component 3 — Rollback Plan

**Trigger**: User decides the cleanup is wrong, or a downstream cross-reference to §7 row #2 / L80 / L317 / L73 breaks.

### 4.1 State After Revert

| Aspect | Post-revert state |
|--------|-------------------|
| `workspace/spec.md` content | Returns to pre-change state (377 lines; L73 = `3 confirmed sub-capabilities + 1 placeholder`, L80 = original placeholder row, L317 = `flow workspace tui (future)`, L360 = original row #2 with rows 3-7 numbered 3-7) |
| Code, tests, registry, behavior | No data corruption. Change is doc-only; revert does NOT affect code, tests, registry, or behavior |
| Partial state | Impossible. The 4 edits are non-overlapping contiguous hunks in `workspace/spec.md`; revert restores all 4 simultaneously |

### 4.2 Rollback Mechanism

`git revert HEAD` — single-command atomic rollback. No migration, no schema, no registry, no code rollback.

Alternative (audit-trail-clean): follow-up change `workspace-dashboard-section-cleanup-restore` to reapply the stale prose. NOT preferred (`git revert` is atomic + audited).

### 4.3 Verification After Revert

```powershell
# File length returns to pre-change state (377 lines)
git show HEAD:openspec/specs/workspace/spec.md | Select-Object -First 1   # → 377 (post-revert)

# Stale prose markers reappear
Select-String -Path openspec/specs/workspace/spec.md -Pattern "3 confirmed sub-capabilities"   # → FOUND
Select-String -Path openspec/specs/workspace/spec.md -Pattern "flow workspace tui \(future\)"   # → FOUND
Select-String -Path openspec/specs/workspace/spec.md -Pattern "workspace-dashboard" | Measure-Object   # → lower count (compared to post-apply state with L80 dashboard row + 6 root REQs mentioning dashboard)

# Locked commits remain byte-identical
git show 6651add --stat      # → unchanged
git show 95e8579 --stat      # → unchanged
git show 778efdb --stat      # → unchanged
git show c9c9650d --stat     # → unchanged

# AC9 byte-identical guard still green
pytest tests/unit/test_cli_projects.py -k byte_identical_envelope   # → 1 passed
```

---

## 5. Component 4 — Commit Message

Conventional Commits format:

```
docs(specs): clean §3/§5/§7 stale dashboard prose

The workspace-dashboard capability shipped at commit 778efdb (PR3 of
phase-5-dashboard), but workspace/spec.md still referenced the old
placeholder structure at 4 locations: §3 intro, §3 row 5, §5 row
"tui (future)", §7 row 2. This change cleans the 4 stale prose items
so the dashboard root spec reflects the shipped state.

4 text edits in workspace/spec.md (~17 lines net change):
- L73 §3 intro: "3 confirmed sub-capabilities + 1 placeholder"
  → "4 confirmed sub-capabilities" (coupled to L80)
- L80 §3 row 5: UPDATE to reference shipped phase-5-dashboard
  (with --filter RULES, --sort FIELD, --no-color flags; no --json
  per Pattern #538; archive path)
- L317 §5 row: UPDATE "flow workspace tui (future)" → "flow
  workspace dashboard" with all 3 flags (no --json)
- L360 §7 row 2: REMOVE (dashboard shipped, no longer future)
  + renumber rows 3-7 → 2-6 (gap-free §7 table)

Out of scope (future cleanup debt):
- L28 §1 Purpose bullet (stale reference)
- L271-277 §4.1 dependency-graph (still references placeholder)
- L273 §4.1 graph cross-reference

Carry-over follow-ups (NOT in this change):
- extract-build-needs-by-name-helper
- remove-sort-projects-deprecation-fallback
- AC6 wording fix (Unknown → Unsupported)

PR1 (6651add) + PR2 (95e8579) + PR3 (778efdb) + sort-projects
(c9c9650d) all byte-identical (locked per Pattern #548).
v1.1-followups/ sacred territory preserved.
AC9 byte-identical guard green.
```

**Format rules** (per AGENTS.md + work-unit-commits skill):
- Conventional Commits prefix: `docs(specs):`
- Subject line ≤72 chars; body wrapped at ~72 cols
- NO "Co-Authored-By" or AI attribution
- Single commit per PR (atomic)
- 1 file modified (`workspace/spec.md`), 4 text edits

---

## 6. Out of Scope (explicit)

| Item | Reason |
|------|--------|
| NO new design surface | The design is "what we're doing", not "what we could do" (Pattern #582) |
| NO new REQs | Doc-only; no behavioral change |
| NO new tests | Doc-only; no test code |
| NO new verify checks | 12 preservation gates (Component 2) + 8 existing from phase-5-dashboard still cover |
| NO re-open L28 / §4.1 | Future `workspace-spec-section-cleanup-1` (NOT this change) |
| NO modifications to any tracked file beyond `workspace/spec.md` | Pattern #548 lock |
| NO modifications to PR1/PR2/PR3/sort-projects commits | All 4 locked (Pattern #548) |
| NO touch of `openspec/changes/v1.1-followups/` | Sacred territory (untracked) |
| NO `stash`-triggering words | Doc-only, so N/A for code; commit message verified per Gate 12 |

---

## 7. Pre-existing Failures (out-of-scope reminder)

All items below are pre-existing and NOT introduced by this change (per phase-5-dashboard archive-report §10.5):

| Item | Count |
|------|-------|
| Lint errors (`cli.py:683 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`) | 3 |
| sqlite-vec reindex test failures (opt-in) | 4 |
| mypy yaml-stub errors | 2 |
| observability_aggregate test failures | 4 |
| Skipped tests | 2 |
| **Total pre-existing OOS** | **15** |

**Informational**: Archived `verify-checks.sh Check 5` (at `openspec/changes/archive/2026-06-30-phase-5-dashboard/scripts/verify-checks.sh`) will return non-zero after this cleanup. Failure is expected and correct — the archived script is historical audit trail from the phase-5-dashboard cycle; its purpose was to validate the phase-5-dashboard state, not the post-cleanup state.

---

## 8. Commit Plan (per work-unit-commits skill)

| Aspect | Value |
|--------|-------|
| Commits | Single commit per PR |
| Message | `docs(specs): clean §3/§5/§7 stale dashboard prose` |
| Attribution | NO "Co-Authored-By" or AI attribution |
| Atomicity | 1 file modified (`workspace/spec.md`), 4 text edits |
| PR size | Well under 400-line budget |
| Chained PR | No — single PR is sufficient |
| Work unit | Standalone (does not split cleanly into sub-units; the 4 edits are semantically one cleanup) |

---

## 9. Wall-time Forecast (remaining phases)

| Phase | Wall-time | Risk |
|-------|-----------|------|
| `sdd-tasks` | ~5 min | LOW — mechanical derivation from locked design (4 tasks: edit L73, edit L80, edit L317, edit L360+renumber) |
| `sdd-apply` | ~5 min | LOW — 4 text edits + 1 commit |
| `sdd-verify` | ~5 min | LOW — 4 ACs + 12 preservation gates iterated |
| `sdd-archive` | ~5 min | LOW — single-PR archive; tiny archive-report |
| **Total remaining** | **~20 min** | LOW end-to-end |

**End-to-end cycle** (explore + propose + spec + design + tasks + apply + verify + archive): ~45 min. **Lowest-friction change in the v1.2 arc.**

---

## 10. Constraints Honored

- ✅ Doc-only (no code, no tests, no verify script changes)
- ✅ Surgical scope (only L73, L80, L317, L360 touched)
- ✅ No expansion to L28, L271-277, L273 (deferred to future `workspace-spec-section-cleanup-1`)
- ✅ No modifications to PR1 (`6651add`) / PR2 (`95e8579`) / PR3 (`778efdb`) / sort-projects (`c9c9650d`) commits
- ✅ No touch of `openspec/changes/v1.1-followups/`
- ✅ No `stash`-triggering words introduced (doc-only)
- ✅ Pattern #580 (proportional cleanup) honored — surrounding text in each section is unchanged
- ✅ Pattern #548 (locked commit hygiene) honored — 4 commits remain byte-identical
- ✅ Pattern #582 ("clean what was promised, nothing more") honored — closed box, 4 components only

---

## Next SDD Phase

`sdd-tasks` — write `tasks.md` mechanically derived from the 4 text edits + 12 preservation gates. Expected output: 4 tasks (one per edit) + 1 commit task + 1 verify task (12 gates).

---

*Generated by the `sdd-design` sub-agent for `workspace-dashboard-section-cleanup`. Design philosophy: "limpiar lo prometido, nada más" (Pattern #582). Closed box, 4 components only. Mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-dashboard-section-cleanup/design"`, `type: "architecture"`, `capture_prompt: false`.*
