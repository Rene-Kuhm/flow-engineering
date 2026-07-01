# workspace-dashboard-section-cleanup — Spec Delta

> **Phase**: spec (SDD pipeline)
> **Change**: `workspace-dashboard-section-cleanup`
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Builds on**: proposal #579 (Engram `sdd/workspace-dashboard-section-cleanup/proposal`) ← explore #577
> **Strict TDD**: OFF (doc-only)
> **Scope**: 4 surgical text edits to `openspec/specs/workspace/spec.md`. No requirements added, modified, or removed.

---

## Scope of this delta

This change is **doc-only**. There are **no behavioral changes** to the `workspace` capability. The 4 edits are stale-prose cleanup of table rows that still described `workspace-dashboard` as `(future)` / `(placeholder)` / `TBD` even though the `phase-5-dashboard` change shipped (commits `6651add` + `95e8579` + `778efdb` on `main`, archived at `openspec/changes/archive/2026-06-30-phase-5-dashboard/` on 2026-06-30).

Per Pattern #580 (*"proportional cleanup, not rewrite"*): the 4 edits are surgical and proportional — only the stale rows and their coupled intro line are touched. Surrounding text, REQ blocks, source lines, and unrelated prose remain intact.

---

## MODIFIED Prose

### Canonical: `openspec/specs/workspace/spec.md` (workspace root spec)

#### §3 intro (L73) — coupled 1-line tweak

- **Before**: `The workspace family has **3 confirmed sub-capabilities + 1 placeholder**:`
- **After**: `The workspace family has **4 confirmed sub-capabilities**:`
- **Rationale**: Tightly coupled to the L80 row 5 update. Once row 5 is promoted from placeholder to shipped, §3 intro must reflect 4 confirmed sub-capabilities (not 3 + 1) to remain internally consistent.

#### §3 row 5 (L80) — UPDATE (placeholder → shipped)

- **Before**: `| 5 (future) | `workspace-dashboard` | `flow workspace tui` / web | Visualization — TBD | 📌 **Placeholder** | (no delta spec yet — see Future Changes §7) |`
- **After**: `| 5 | `workspace-dashboard` | `flow workspace dashboard` | Visualization — read-only Rich MVP for human operators; supports `--filter RULES`, `--sort FIELD`, `--no-color` (no `--json` — Pattern #538) | ✅ Shipped + archived at `phase-5-dashboard` | `openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` |`
- **Rationale**: `phase-5-dashboard` shipped on 2026-06-30 (3 commits on `main` + archived delta spec). The sub-capability row must reflect shipped state and reference the canonical delta archive path.

#### §5 row (L317) — UPDATE (tui future → shipped dashboard)

- **Before**: `| `flow workspace tui` (future) | (Phase 5) | 5 (placeholder) | Dashboard — not yet implemented |`
- **After**: `| `flow workspace dashboard` | `[--filter RULES] [--sort FIELD] [--no-color]` (Phase 5) | 5 | Read-only Rich MVP (A header + B needs-attention + C archived + D footer); no `--json` (Pattern #538) |`
- **Rationale**: Command renamed from `tui` (planned) to `dashboard` (shipped). Three shipped flags documented (`--filter RULES`, `--sort FIELD`, `--no-color`). `--json` explicitly absent per Pattern #538 (one identity per command — visual for humans vs. structured for tools, the latter stays at `flow workspace status --json`).

#### §7 row 2 (L360) — REMOVE + renumber 3-7 → 2-6

- **Before** (L360-L365):
  ```
  | 2 | **`workspace-dashboard` (Phase 5)** | TUI (`flow workspace tui`) or web visualization of workspace state (registry + needs_attention + per-project metadata). Will add a new delta spec; this root spec is already anchored. | Low | Future change; requires CLI solidification first (per session #483) |
  | 3 | `workspace-hygiene-capability-spec` (optional) | Create `openspec/specs/workspace-hygiene/spec.md` as a top-level capability for the write-side if the delta grows further. | Low | Phase 4 follow-up #2 in archive-report #477 |
  | 4 | `backup-retention-policy` | Currently INDEFINITE in Phase 4 (per locked constraint #12). Needs pruning/TTL strategy at scale. | Low | Operator concern; not blocking |
  | 5 | `workspace-hygiene-r1` (deferred) | R1 dirty-git remediation: stash/worktree handling, interactive prompts, status integration. Explicitly OUT of Phase 4. | Low | Future change if requested |
  | 6 | `workspace-hygiene-r3` + `workspace-hygiene-r4` (deferred) | R3 no-tests bootstrap (template-dependent) + R4 no-openspec bootstrap (semantic scaffold). | Low | Future change if requested |
  | 7 | Artifact-hygiene move | Phases 1 + 3 still in `openspec/changes/{workspace-intelligence,flow-workspace-status}/` (not yet in `archive/`). | Low | Out of scope for this change; separate cleanup |
  ```
- **After** (renumbered 2-6, gap-free):
  ```
  | 2 | `workspace-hygiene-capability-spec` (optional) | Create `openspec/specs/workspace-hygiene/spec.md` as a top-level capability for the write-side if the delta grows further. | Low | Phase 4 follow-up #2 in archive-report #477 |
  | 3 | `backup-retention-policy` | Currently INDEFINITE in Phase 4 (per locked constraint #12). Needs pruning/TTL strategy at scale. | Low | Operator concern; not blocking |
  | 4 | `workspace-hygiene-r1` (deferred) | R1 dirty-git remediation: stash/worktree handling, interactive prompts, status integration. Explicitly OUT of Phase 4. | Low | Future change if requested |
  | 5 | `workspace-hygiene-r3` + `workspace-hygiene-r4` (deferred) | R3 no-tests bootstrap (template-dependent) + R4 no-openspec bootstrap (semantic scaffold). | Low | Future change if requested |
  | 6 | Artifact-hygiene move | Phases 1 + 3 still in `openspec/changes/{workspace-intelligence,flow-workspace-status}/` (not yet in `archive/`). | Low | Out of scope for this change; separate cleanup |
  ```
- **Rationale**: §7 is the forward-looking register (per §8 family-shape protocol). `phase-5-dashboard` has shipped, so the deferred entry for that change no longer belongs here. Renumber 3-7 → 2-6 keeps the table gap-free.

---

## ADDED Requirements

None.

---

## MODIFIED Requirements

None. (No behavioral REQs change. The 12 root-level REQs in §4 of `openspec/specs/workspace/spec.md` remain byte-identical: REQ-WORKSPACE-PROJECT-IDENTITY, REQ-WORKSPACE-STATUS-DISCOVERY, REQ-WORKSPACE-MUTATION-SAFETY, REQ-WORKSPACE-DRY-RUN-DEFAULT, REQ-WORKSPACE-R1-DEFERRED, REQ-WORKSPACE-REGISTRY-V1, REQ-WORKSPACE-DASHBOARD-SURFACE, REQ-WORKSPACE-DASHBOARD-READ-ONLY, REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1, REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2, REQ-WORKSPACE-DASHBOARD-RENDERS-RICH, REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE.)

---

## REMOVED Requirements

None.

---

## BDD Scenarios

None. (Doc-only cleanup; no behavioral change. BDD scenarios for `workspace-dashboard` already exist in the archived delta spec at `openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` and remain canonical.)

---

## Acceptance Criteria (4 ACs — mirror of proposal #579 §7)

| AC | Description | Verification |
|----|-------------|--------------|
| **AC1** | L80 row 5 updated to reference shipped `phase-5-dashboard` (all 3 flags, no `--json`, archive path) | Read `workspace/spec.md` L80; confirm row matches replacement text |
| **AC2** | L73 intro updated from `3 confirmed sub-capabilities + 1 placeholder` to `4 confirmed sub-capabilities` | Read `workspace/spec.md` L73; confirm wording |
| **AC3** | L317 row updated from `flow workspace tui (future) / (placeholder)` to `flow workspace dashboard` with 3 flags + no `--json` | Read `workspace/spec.md` L317; confirm row matches replacement text |
| **AC4** | L360 row #2 removed; rows 3-7 renumbered 2-6; §7 table gap-free | Read `workspace/spec.md` §7; confirm 6 rows numbered 2-6 with no gap |

### Preservation gates (8 existing from phase-5-dashboard)

1. `flow projects ls [--json]` still enumerated in §3 + §5
2. `flow workspace status [--json]` still enumerated in §3 + §5
3. `flow workspace {fix,archive,archived,restore}` still enumerated in §3 + §5
4. 12 root REQs in §4 each carry a `Source:` line (preserved — 12/12 intact)
5. §8 family-shape protocol text unchanged
6. §6.1 RESOLVED note (Phase 2 reclassification) unchanged
7. Registry v1 REQ unchanged
8. Boundary rule (workspace vs. flow-where) unchanged

---

## Out of Scope (FUTURE CLEANUP DEBT — explicitly deferred)

The following stale prose items are **acknowledged but NOT modified** by this change. They will be cleaned up by a future change `workspace-spec-section-cleanup-1` (or similarly named):

| Location | Stale content | Future-change owner |
|----------|---------------|---------------------|
| **L28** §1 Purpose bullet | `(Phase 5 placeholder) will surface workspace state in a TUI or web visualization` | `workspace-spec-section-cleanup-1` |
| **L271-277** §4.1 dependency-graph | Still references `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` (replaced by 6 dashboard REQs at L170-L234) | same |
| **L273** §4.1 graph cross-reference | `flow workspace tui / web` (now `flow workspace dashboard`) | same |

Per Pattern #580 (*"proportional cleanup, not rewrite"*) and user-locked constraint ("Mantenelo quirúrgico. No abras otra caja."): these items are out of scope for THIS change and will be handled by a dedicated cleanup cycle.

---

## Open Questions (resolved)

| Q | Question | Resolution |
|---|----------|------------|
| Q1 | §3 L80 — Replace with shipped-state row vs. drop entirely? | **Replace** (Option A) — preserves §3 family-overview invariant (1 row per Phase) |
| Q2 | §5 L317 — Replace row with shipped-state vs. remove? | **Replace** (Option A) — preserves §5 CLI surface inventory invariant |
| Q3 | §7 L360 — Remove row vs. mark as landed? | **Remove** (Option A) — §7 is forward-looking by design; renumber 3-7 → 2-6 |
| Q4 | §4.1 L271-277 dependency-graph stale? | **Out of scope** — future `workspace-spec-section-cleanup-1` |
| Q5 | §1 L28 bullet `(Phase 5 placeholder)` — fix here? | **Out of scope** — same future change |
| Q6 | §8 L374 family-shape protocol text — already correct? | **No change needed** — text is already accurate |

---

## Pre-existing failures (out-of-scope reminder)

All items below are **pre-existing** and **NOT introduced** by this change:

- 3 lint errors (`cli.py:683 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`)
- 4 sqlite-vec reindex test failures (opt-in)
- 2 mypy yaml-stub errors
- 4 observability_aggregate test failures
- 2 skipped tests

---

## Pre-existing failures expected post-cleanup (informational only)

- Archived `verify-checks.sh Check 5` will return non-zero after this cleanup. The script is a historical audit trail from the `phase-5-dashboard` cycle; the failure is expected and correct. No action required.

---

## Constraints honored (per preflight)

- ✅ Doc-only (no code, no tests, no verify checks)
- ✅ Surgical scope (only L73, L80, L317, L360 touched)
- ✅ No expansion to L28, L271-277, L273 (deferred to future cleanup)
- ✅ No modifications to PR1 (`6651add`) / PR2 (`95e8579`) / PR3 (`778efdb`) / sort-projects (`c9c9650d`) commits
- ✅ No touch of `openspec/changes/v1.1-followups/`
- ✅ No `stash`-triggering words introduced
- ✅ Pattern #580 (proportional cleanup) honored — surrounding text in each section is unchanged

---

## Next SDD Phase

`sdd-design` — write the design doc for this change (minimal: text-edit recipe + preservation gates + rollback plan).

---

*Generated by the `sdd-spec` sub-agent for `workspace-dashboard-section-cleanup`. Spec artifact mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-dashboard-section-cleanup/spec"`, `type: "architecture"`, `capture_prompt: false`.*