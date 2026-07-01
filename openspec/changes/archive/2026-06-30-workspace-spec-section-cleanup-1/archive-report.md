# Archive Report: workspace-spec-section-cleanup-1

> **Cycle**: COMPLETE / PASS / doc-only (NOT pushed; deferred to after user merge per Pattern #584)
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Branch**: `codex/workspace-spec-section-cleanup-1` (LOCAL only)
> **Apply commit SHA**: `43e76ed`
> **Archive chore commit SHA**: see `git log -1` on the branch after `Move-Item`
> **Strict TDD**: OFF (doc-only; no test code)

---

## 1. Status

**COMPLETE — cycle closed locally.** All 7 SDD tasks (T-1..T-7) executed per the locked
design. Single atomic apply commit `43e76ed` on branch `codex/workspace-spec-section-cleanup-1`
captures the 3 text edits. Single archive chore commit captures the filesystem move
+ the new `archive-report.md`. 3 ACs PASS. 22 preservation gates PASS against committed
state. **NO push** — deferred to after the user merges to `main` per Pattern #584.

## 2. Change summary

A doc-only cleanup of 3 stale-prose items in `openspec/specs/workspace/spec.md` that
were carried forward from the `workspace-dashboard-section-cleanup` cycle (archive-report
§9 items #4/#5/#6). The `phase-5-dashboard` capability shipped at commit `778efdb` (PR3
on `main`); the root spec still described it as `(Phase 5 placeholder)` / `PLACEHOLDER
STUB` / `tui / web` at L28 + L271-278 + L273. This change brings §1 Purpose bullet and
§4.1 dependency-graph box in line with the shipped state — nothing more (Pattern #582:
"clean what was promised, nothing more").

## 3. Goal

Bring `openspec/specs/workspace/spec.md` into sync with the shipped state of the
workspace-dashboard capability. The change is purely textual: 3 surgical text edits
in a single file, no code, no tests, no new runtime dependencies, no re-open of
out-of-scope adjacent items.

## 4. 3 text edits (applied by spec phase #596; committed in apply phase T-5)

1. **L28 §1 Purpose bullet** — replaced `(Phase 5 placeholder) will surface workspace
   state in a TUI or web visualization.` with `visualizes workspace state in a read-only
   Rich dashboard for human operators (flow workspace dashboard with --filter RULES,
   --sort FIELD, --no-color; no --json per Pattern #538).`
2. **L271-278 §4.1 dependency graph box** — replaced the 7-line PLACEHOLDER STUB box
   with an 8-line phase-5-dashboard shipped-state box (top/bottom borders verbatim,
   ASCII column alignment preserved at 39 chars between `│`).
3. **L273 §4.1 graph cross-reference** — subsumed in edit #2 (L273 sits inside the box
   at the 2nd inner line; `tui / web` → `dashboard` is part of the box replacement).

## 5. 22 preservation gates (all PASS against committed state `43e76ed`)

### A. Root REQ blocks intact (12/12)

`grep '^### REQ-WORKSPACE-' openspec/specs/workspace/spec.md` → FOUND at L92, L102,
L120, L130, L140, L150, L170, L182, L194, L206, L218, L230 (12 root REQs in §4).

### B. Section structure + callouts (4/4)

- L4 §0 family-index callout: `Family index, not canonical source.` — FOUND
- L355 §6.1 RESOLVED callout: `[2026-06-30 update — RESOLVED]` — FOUND
- L367 §8 Drift Detection footer: `Drift Detection` — FOUND
- Section header structure: 10 `## ` headers (`## 1`-`## 8` + `## 4.1` + `## 4.2`)
  + 13 `### ` headers (12 REQs + `### 6.1`) — all intact

### C. Locked commits intact + sacred territory (5/5)

`git cat-file -t + git merge-base --is-ancestor` confirm:

| Commit | Subject | cat-file | ancestor of HEAD |
|--------|---------|----------|------------------|
| `6651add` | PR1 — subprocess wrappers + fetchers | commit | TRUE |
| `95e8579` | PR2 — filter + sort + color + Rich rendering | commit | TRUE |
| `778efdb` | PR3 — Click integration + verify script + ACs | commit | TRUE |
| `c9c9650d` | sort-projects contract fix | commit | TRUE |
| `1ef33cf` | Merge workspace-dashboard-section-cleanup | commit | TRUE |

`openspec/changes/v1.1-followups/` — still untracked (sacred territory preserved).

### D. Stale markers REMOVED (5/5)

| Pattern | Status |
|---------|--------|
| `(Phase 5 placeholder)` | NOT FOUND |
| `TUI or web visualization` | NOT FOUND |
| `PLACEHOLDER STUB` | NOT FOUND |
| `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` | NOT FOUND |
| `flow workspace tui / web` | NOT FOUND |

### E. OOS items PRESERVED (3/3 — deferred to `workspace-spec-section-cleanup-2`)

- L69 §2 boundary stress test `"Show me a TUI of my workspace."` — FOUND (1 occurrence)
- L269 §4.1 graph arrow label `│ Phase 5 (future) │` — FOUND
- L292 §4.1 graph note `Phase 5 (future) will depend on ...` — FOUND (spec said L291,
  actual is L292 due to +1 line shift from L28/L271-278 edits; gate counts 2+ which
  satisfies the negative-space preservation rule)

### F. New positive-space marker added (1/1)

`Source: phase-5-dashboard (shipped)` — FOUND at L277 (new reference added by edit #2).

### G. Hygiene / scope locks (4/4)

- `git status` shows ONLY 1 modified tracked file at T-5 stage (workspace/spec.md)
- v1.1-followups sacred territory: untracked, untouched throughout
- No `stash`/`git stash`/`dirty-git` words introduced (1 pre-existing occurrence at
  L363 in §7 Future Changes table about R1 dirty-git remediation, from prior cycle
  commit `a0eb318` — outside our 2 diff hunks)
- T-5 commit message has `Co-Authored-By: none` (no AI attribution)

## 6. Rollback plan

`git revert HEAD` restores pre-change state atomically (single apply commit → single
revert commit). No code, no tests, no registry, no behavior changes — revert is
trivially safe.

After revert:
- File line count returns from 377 LF → 376 LF (the box widens 7 → 8 lines, net +1)
- L28 returns to `(Phase 5 placeholder) will surface workspace state in a TUI or web visualization.`
- L271-277 returns to the 7-line PLACEHOLDER STUB box
- L273 returns to `flow workspace tui / web`
- All other tracked files, registry, code, tests: unaffected (doc-only)

## 7. Commit message (verbatim from T-5)

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
  workspace state in a TUI or web visualization" -> "visualizes
  workspace state in a read-only Rich dashboard for human operators
  (flow workspace dashboard with --filter RULES, --sort FIELD,
  --no-color; no --json per Pattern #538)"
- L271-278 §4.1 dependency graph box: 7-line placeholder stub ->
  8-line phase-5-dashboard shipped state (6 REQs incl. Rich MVP +
  --filter RULES / --sort FIELD / --no-color (no --json per #538)
  + Source: phase-5-dashboard (shipped)); ASCII column alignment
  preserved, top/bottom borders verbatim
- L273 §4.1 graph cross-reference: subsumed in L271-278 box
  replacement (flow workspace tui / web -> flow workspace dashboard)

Out of scope (deferred to workspace-spec-section-cleanup-2):
- L69 §2 boundary stress test ("TUI" framing)
- L269 §4.1 graph arrow label ("Phase 5 (future)" -> "shipped")
- L291 §4.1 graph note (Phase 5 future framing)

PR1 (6651add) + PR2 (95e8579) + PR3 (778efdb) + sort-projects
(c9c9650d) + workspace-dashboard-section-cleanup chain all
byte-identical (locked per Pattern #548). v1.1-followups/ sacred
territory preserved. AC9 byte-identical guard green.

Co-Authored-By: none
```

## 8. 4 acceptance criteria

- **AC1**: L28 §1 Purpose bullet updated to read shipped Rich dashboard state
  (no `(Phase 5 placeholder)` marker, no `TUI or web visualization` framing; names
  `flow workspace dashboard` + 3 flags + no-`--json` invariant) — PASS at L28
- **AC2**: L271-278 §4.1 dependency-graph box updated (no `PLACEHOLDER STUB`, no
  `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` reference, no `§7 Future Changes`; box
  reflects phase-5-dashboard shipped state with 6 REQs + Rich MVP + 3 flags +
  no `--json` + Source ref) — PASS at L271-278
- **AC3**: L273 in-box cross-reference updated to `flow workspace dashboard`
  (no `tui / web` slash-separated framing) — PASS at L273 (subsumed in box replacement)
- **AC4 (preservation gate)**: No changes to `openspec/changes/v1.1-followups/`,
  no modifications to any locked commit, no new runtime dependencies introduced —
  PASS (22 gates all green against committed state)

## 9. Out of scope (deferred to `workspace-spec-section-cleanup-2`)

3 items explicitly deferred to the future cleanup cycle. Recorded for the
`workspace-spec-section-cleanup-2` proposal intake.

- **L69 §2 boundary stress test** (`"Show me a TUI of my workspace."` framing)
  — TUI framing is no longer accurate post-PR3; cleanup belongs in -2.
- **L269 §4.1 graph arrow label** (`│ Phase 5 (future) │` → should read `(shipped)`)
  — arrow now points to a shipped capability; label lags.
- **L291 §4.1 graph note** (`Phase 5 (future) will depend on ...` → should be past
  tense, `Phase 5 depends on ...` or `Phase 5 (shipped) depends on ...`)
  — note still uses future-tense framing for the shipped capability.

## 10. Final state

- `openspec/specs/workspace/spec.md` at **377 LF** (post-state; pre-state was 376 LF;
  +1 net line from box widening 7 → 8)
- 1 commit on `codex/workspace-spec-section-cleanup-1`: `43e76ed` (apply)
- 1 archive chore commit (this archive move): see branch HEAD after T-7
- Working tree clean except `?? openspec/changes/v1.1-followups/` (sacred)
  + the moved `archive/2026-06-30-workspace-spec-section-cleanup-1/` folder
- All 14+ locked commits on `main` HEAD `1ef33cf` byte-identical (verified via
  `git cat-file -t + git merge-base --is-ancestor`)

## 11. References

- Engram `#593` — `sdd/workspace-spec-section-cleanup-1/explore`
  (3 in-scope items at exact line locations)
- Engram `#594` — `sdd/workspace-spec-section-cleanup-1/proposal`
  (locks 3 text edits + 4 ACs)
- Engram `#596` — `sdd/workspace-spec-section-cleanup-1/spec`
  (3 text edits ALREADY APPLIED to workspace/spec.md before apply phase)
- Engram `#598` — `sdd/workspace-spec-section-cleanup-1/design`
  (4 components, 22 preservation gates)
- Engram `#600` — `sdd/workspace-spec-section-cleanup-1/tasks`
  (7 mechanical tasks)
- Prior cycle `workspace-dashboard-section-cleanup` archive-report
  (carry-over items #4/#5/#6 → THIS cycle)
- Pattern #582 — "Clean what was promised, nothing more"
- Pattern #584 — "Push deferred to after user merge"
- Pattern #586 — "Post-state handling"
- Pattern #597 — "Clean closure regardless of change size"
- Pattern #598 — "Controlled cleanup, not spec rewrite"
- Pattern #599 — "Trámite controlado"
- Pattern #600 — "Commit captures audit trail close"
- Pattern #548 — "Locked commits byte-identical guarantee"

## 12. Carry-forwards

### From prior cycle's §9 (`workspace-dashboard-section-cleanup` archive-report)

Items #1, #2, #3 from prior cycle's archive-report §9 are unrelated to this change
(they refer to different carry-overs from THAT cycle's parent). Items #4, #5, #6 from
prior cycle's §9 are the items THIS change addresses:
- Item #4: L28 §1 Purpose bullet — RESOLVED by edit #1
- Item #5: L271-278 box — RESOLVED by edit #2
- Item #6: L273 cross-reference — RESOLVED by edit #2 (subsumed)

### THIS cycle's deferred items (carry-forward to `workspace-spec-section-cleanup-2`)

Items from §9 above (3 items: L69 / L269 / L291). Recorded for next cycle's
proposal intake.

## 13. Pre-existing failures (out-of-scope, unchanged)

Doc-only change introduces NO new failures. Pre-existing OOS items remain OOS:

- 3 pre-existing lint errors OOS (`cli.py:683 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`)
- 4 pre-existing reindex test failures OOS (sqlite-vec opt-in)
- 2 pre-existing mypy yaml-stub errors OOS
- 4 pre-existing observability_aggregate test failures OOS
- 2 pre-existing skipped tests OOS

## 14. Locked-commit inventory

14+ commits on `main` HEAD `1ef33cf` all byte-identical (verified via
`git cat-file -t + git show --stat`). Locked per Pattern #548:

PR1 (`6651add`) → PR2 (`95e8579`) → PR3 (`778efdb`) → sort-projects (`c9c9650d`)
→ workspace-dashboard-section-cleanup chain (`a0eb318`, `2df1719`, `44f9e54`,
`c734e39`, `b901e7e`, `5f28f68`, `f2c75cf`, `0fa1cae`, `bd20271`, `b9da84b`)
→ merge (`1ef33cf`). All verified intact at T-4 + T-6.

## 15. Push status — DEFERRED

**Push is OUTSIDE the cycle per Pattern #584.** No `git push` performed in this cycle.
Branch `codex/workspace-spec-section-cleanup-1` exists LOCALLY only. After user
review + merge to `main`, push happens per the user's normal workflow.

## 16. Cycle close

Per Pattern #597 (*"clean closure regardless of change size"*): the cycle ends with
T-7 archive; the next phase is the user's merge + push to `origin/main`. This change
demonstrates that "small" doc-only cleanups are still cycles worth closing properly
(Package #586 + #600 honored). Total cycle wall-time ~46 min.

---

*Generated by the `sdd-archive` (filesystem-move variant) for
`workspace-spec-section-cleanup-1`. Archive artifact at
`openspec/changes/archive/2026-06-30-workspace-spec-section-cleanup-1/archive-report.md`.
Mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-spec-section-cleanup-1/archive"`,
`type: "architecture"`, `project: "insyd"`, `capture_prompt: false`. "Limpieza controlada,
cierre limpio."
