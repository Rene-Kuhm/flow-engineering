# Archive Report: workspace-dashboard-section-cleanup

> **Change**: `workspace-dashboard-section-cleanup`
> **Archived**: 2026-06-30
> **Branch**: `codex/workspace-dashboard-section-cleanup`
> **Apply commit**: `a0eb318` (`docs(specs): clean §3/§5/§7 stale dashboard prose`)
> **Cycle**: Single-PR, doc-only cleanup (~17 LOC; well under 400-line budget)
> **Push status**: NOT PUSHED (deferred to after user merge per Pattern #584)

---

## 1. Status

**SUCCESS** — 4 text edits applied to `openspec/specs/workspace/spec.md`; all 4 ACs PASS; all 12 preservation gates PASS; cycle closed at archive.

---

## 2. Change Summary

| Field | Value |
|-------|-------|
| Goal | Clean 4 stale prose lines in `workspace/spec.md` that referenced `workspace-dashboard` as `(future)` / `(placeholder)` / `TBD` even though `phase-5-dashboard` shipped |
| Scope | 1 file (`openspec/specs/workspace/spec.md`); 4 text edits at L73 / L80 / L317 / L360 |
| Net LOC | 17 lines (8 insertions / 9 deletions) |
| PR strategy | Single PR (well under 400-line budget) |
| Strict TDD | OFF (doc-only) |
| Design philosophy | "limpiar lo prometido, nada más" (Pattern #582) |

---

## 3. Goal

The `workspace-dashboard` capability shipped at commit `778efdb` (PR3 of `phase-5-dashboard`), but `openspec/specs/workspace/spec.md` still referenced the old placeholder structure at 4 locations. This change cleans the 4 stale prose items so the dashboard root spec reflects the shipped state, without expanding scope to L28 / §4.1 (deferred to future `workspace-spec-section-cleanup-1`).

---

## 4. The 4 Text Edits (applied)

| # | Location | Section | Action | Net Δ |
|---|----------|---------|--------|-------|
| 1 | L73 | §3 intro | UPDATE: `3 confirmed sub-capabilities + 1 placeholder` → `4 confirmed sub-capabilities` | -1 line |
| 2 | L80 | §3 row 5 | UPDATE: placeholder row → shipped `phase-5-dashboard` row with `--filter RULES`, `--sort FIELD`, `--no-color` flags + archive path | 0 lines (replacement) |
| 3 | L317 | §5 row | UPDATE: `flow workspace tui (future)` → `flow workspace dashboard` with all 3 flags (no `--json` per Pattern #538) | 0 lines (replacement) |
| 4 | L360 | §7 row #2 | REMOVE + renumber rows 3-7 → 2-6 (gap-free §7 table) | -1 line |

**Total**: 17 lines net (8 insertions / 9 deletions).

---

## 5. Acceptance Criteria (all PASS)

| AC | Description | Result |
|----|-------------|--------|
| **AC1** | L80 row 5 references shipped `phase-5-dashboard` with all 3 flags, no `--json`, archive path | PASS |
| **AC2** | L73 intro updated from `3 confirmed sub-capabilities + 1 placeholder` to `4 confirmed sub-capabilities` | PASS (L73 confirmed) |
| **AC3** | L317 row updated to `flow workspace dashboard` with 3 flags + no `--json` | PASS |
| **AC4** | L360 row removed; rows 3-7 renumbered 2-6; §7 table gap-free (5 rows) | PASS (L360-L364) |

---

## 6. 12 Preservation Gates (all PASS against committed state)

| # | Gate | Result |
|---|------|--------|
| 1 | PR1 commit `6651add` byte-identical | PASS (commit object preserved) |
| 2 | PR2 commit `95e8579` byte-identical | PASS (commit object preserved) |
| 3 | PR3 commit `778efdb` byte-identical | PASS (commit object preserved) |
| 4 | sort-projects commit `c9c9650d` byte-identical | PASS (commit object preserved) |
| 5 | 12 `REQ-WORKSPACE-*` blocks intact (7 original + 5 dashboard; note: design §3.5 said 6 dashboard but spec only carries 5 visible blocks; total 12 = 7+5) | PASS (12 blocks at L92/102/120/130/140/150/170/182/194/206/218/230) |
| 6 | "Family index, not canonical source" callout at L4 | PASS (intact) |
| 7 | §8 Drift Detection footer at L366 | PASS (intact) |
| 8 | §6.1 Cross-Impact RESOLVED note at L354 | PASS (intact) |
| 9 | `v1.1-followups/` untouched (still untracked, sacred) | PASS (untracked; never tracked) |
| 10 | AC9 byte-identical guard green | PASS (`test_flow_projects_ls_json_byte_identical_envelope` PASSED) |
| 11 | No `stash`-triggering words in the 4 edits | PASS (pre-existing `stash/worktree` at L362 is in `workspace-hygiene-r1` description, not one of the 4 edits) |
| 12 | No reformatting of surrounding text (Pattern #580) | PASS (git diff shows only 4 targeted hunks; no whitespace or column-alignment drift) |

---

## 7. Rollback Plan

Single-command atomic rollback: `git revert HEAD`. Doc-only change; revert restores pre-change state without affecting code, tests, registry, or behavior. See design.md §4 for full rollback verification recipe.

---

## 8. Commit Message (T-6 — verbatim from design.md §5)

```
docs(specs): clean §3/§5/§7 stale dashboard prose

The workspace-dashboard capability shipped at commit 778efdb (PR3 of
phase-5-dashboard), but workspace/spec.md still referenced the old
placeholder structure at 4 locations: §3 intro, §3 row 5, §5 row
"tui (future)", §7 row 2. This change cleans the 4 stale prose items
so the dashboard root spec reflects the shipped state.

4 text edits in workspace/spec.md (17 lines net change):
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

NO `Co-Authored-By`. NO AI attribution.

---

## 9. Carry-Over Follow-Ups (NOT in this change)

These remain as future cleanup debt:

1. **extract-build-needs-by-name-helper** — internal refactor opportunity surfaced during sort-projects analysis
2. **remove-sort-projects-deprecation-fallback** — DeprecationWarning shim no longer needed after sort-projects ships
3. **AC6 wording fix** — `Unknown` → `Unsupported` for type-correct error messaging in dashboard envelope parser
4. **L28 §1 Purpose bullet** — still references placeholder state (deferred to `workspace-spec-section-cleanup-1`)
5. **L271-277 §4.1 dependency-graph** — still references placeholder (deferred to `workspace-spec-section-cleanup-1`)
6. **L273 §4.1 graph cross-reference** — same scope as above

---

## 10. Final State

| Aspect | State |
|--------|-------|
| Branch | `codex/workspace-dashboard-section-cleanup` (LOCAL, NOT pushed) |
| Commits on branch | 2 (T-6 apply + T-8 archive chore) |
| main HEAD | `44f9e54` (sort-projects merged + pushed) |
| Branch HEAD | `a0eb318` (T-6 apply commit) — archive chore commit pending |
| `workspace/spec.md` | Post-state: 4 edits applied; committed in `a0eb318` |
| `v1.1-followups/` | Untouched throughout; sacred territory preserved |
| PR1/PR2/PR3/sort-projects | All byte-identical on main `44f9e54` |
| Push | NOT pushed; deferred to after user merge per Pattern #584 |

---

## 11. References

- **Design**: `design.md` (4 components — text edit recipe + 12 preservation gates + rollback plan + commit message)
- **Tasks**: `tasks.md` (8 mechanical tasks T-1..T-8; post-state handling for T-1..T-4)
- **Proposal**: `proposal.md` (scope + 4 ACs + 4 locked text edits)
- **Explore**: `explore.md` (4 in-scope items at exact line numbers)
- **Change-artifact delta spec**: `specs/workspace/spec.md` (audit trail of the 4 text edits)
- **Canonical root spec**: `openspec/specs/workspace/spec.md` (modified by T-6 commit `a0eb318`)

---

## 12. Cycle Closure Notes

- **Wall-time actual**: ~5 minutes (post-state handling shortcut — 4 edits already in file from spec phase)
- **End-to-end cycle** (explore + propose + spec + design + tasks + apply + verify + archive): ~46 minutes total
- **Risk level**: LOW (Pattern #548 lock preserved; doc-only; single-PR; well under budget)
- **Next step**: User merges `codex/workspace-dashboard-section-cleanup` to main + pushes to `origin/main` (Pattern #584)

---

*Generated by the `sdd-apply` sub-agent for `workspace-dashboard-section-cleanup`. Design philosophy: "limpiar lo prometido, nada más" (Pattern #582). Post-state handling per Pattern #586 — T-1..T-4 were no-ops because the spec phase #581 had already applied the 4 edits to the canonical root spec; the apply commit `a0eb318` closes the audit trail with a 17-line doc-only commit. NO push (deferred to after user merge per Pattern #584).*