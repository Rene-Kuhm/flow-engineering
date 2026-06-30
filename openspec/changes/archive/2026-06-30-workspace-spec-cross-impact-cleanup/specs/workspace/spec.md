# workspace-spec-cross-impact-cleanup (change #N)

> **Phase**: 3/8 — `sdd-spec`
> **Change**: `workspace-spec-cross-impact-cleanup` (doc-only)
> **Project**: flow-engineering v1.2.0 · main HEAD `780285f`
> **Strict TDD**: OFF (doc-only)
> **Approach**: A (Minimal) — locked by proposal #521
> **Scope**: W1 + W2 ONLY. 2 single-line edits in `openspec/specs/workspace/spec.md`.

## ADDED Requirements

None.

## MODIFIED Requirements

None.

## MODIFIED Prose

### workspace root spec (canonical: `openspec/specs/workspace/spec.md`)

#### §4.2 versioning table (L241)

- **Before**: `` `flow-where/spec.md` gains `REQ-V1.0.5..V1.0.X` `` (placeholder pre-integration)
- **After**: `` `flow-where/spec.md` gains `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` ``
- **Rationale**: matches §6.1 L292 RESOLVED note wording for consistency; the 6 REQ IDs landed at `flow-where/spec.md` L274, L284, L294, L304, L316, L326 during `flow-where-cross-project-capability-merge` apply (commit `6e21d4d`).

#### §6 archive-status meta-pointer (L16)

- **Before**: ``**Carry-forwards documented in Future Changes** (§7): `flow-where-cross-project-capability-merge` (Phase 2 follow-up), Phase 5 `workspace-dashboard`, optional `workspace-hygiene-capability-spec`, `backup-retention-policy` review, R1/R3/R4 deferred rules.``
- **After**: ``**Carry-forwards documented in Future Changes** (§7): Phase 5 `workspace-dashboard`, optional `workspace-hygiene-capability-spec`, `backup-retention-policy` review, R1/R3/R4 deferred rules.``
- **Rationale**: the change has landed (apply `6e21d4d`, archive chore `8d51c5f`); the §7 row was already removed per verify-report #513 AC7; the §6.1 RESOLVED note at L292 explicitly records that the reclassification is RESOLVED and the §7 row is removed. Removing cleanly matches the verify-report #513 AC7 precedent.

## REMOVED Requirements

None.

## BDD Scenarios

None — doc-only change; no behavior, no test surface. The 7 verify checks from `workspace-capability-bootstrap` design #492 remain the structural validation surface (re-validated in `explore.md` §"Protected Artifacts Verification"; survive the edits unchanged).

## Protected Artifacts (MUST remain byte-identical to HEAD `780285f`)

| Protected artifact | Location | Status post-edit |
|---|---|---|
| Source: lines for 7 root REQs | L96, L114, L124, L134, L144, L164, L174 | INTACT (confirmed by `git diff`: only L16 + L241 changed) |
| "Family index" callout | L4 (blockquote) | INTACT (outside edit surface) |
| Drift Detection footer | L305–L313 (§8) | INTACT (outside edit surface) |
| §6.1 Cross-Impact content | L274–L292 (incl. RESOLVED note at L292) | INTACT (outside edit surface; protected by user lock) |
| §7 Future Changes table | L296–L303 (rows #2–#7) | INTACT (W2 fix is in archive-status meta-pointer at L16, NOT in §7) |
| 7 verify checks (design #492 §4) | re-validated | PASS |

## Future Cleanup Changes (informational — NOT this PR)

| Location | Stale content | Tracked as |
|---|---|---|
| §4.1 ASCII diagram, L221 | `flow-where-cross-project-capability-merge follow-up` reference | Future `workspace-spec-stale-cross-impact-fixes` |
| §6.1 Cross-Impact, L290 | follow-up pointer leads to non-existent §7 row | Future `workspace-spec-stale-cross-impact-fixes` (requires §6.1 unlock) |
| §6.1 Cross-Impact, L292 | `` `[future-commit-sha]` `` placeholder (actual SHA: `6e21d4d96fbc9d94a0814c0f677cd03cb1f4bb07`) | Future `workspace-spec-stale-cross-impact-fixes` (requires §6.1 unlock) |

All three items are protected by user locks (explicit "§6.1 INTACT" or implicit "W1 + W2 ONLY").

## Out of Scope

- All items in "Future Cleanup Changes" above
- Any code modifications
- Any new verify checks (the 7 existing checks remain sufficient)
- Any modification to `openspec/specs/flow-where/spec.md` or any prior archive
- Any touch of `openspec/changes/v1.1-followups/`
- `size:exception` label · Chained PRs · `CHANGELOG.md` (no user-visible change)

## Open Questions (resolved — see proposal #521 §9)

- **Q1** W1 wording → A1: enumerated range matches §6.1 L292 verbatim (user lock)
- **Q2** W2 shape → A2: remove cleanly (matches verify-report #513 AC7 precedent)
- **Q3** 3 informational items → A3: future `workspace-spec-stale-cross-impact-fixes`
- **Q4** PR structure → A4: single PR, 1 commit, no chained, no `size:exception`
- **Q5** Why no new verify check → A5: doc-only scope lock; auto-detection belongs in `spec-drift-detector` (verify-report #513 S1)

## Related Engram Observations

- `#519` `sdd/workspace-spec-cross-impact-cleanup/explore` — W1 + W2 locations
- `#521` `sdd/workspace-spec-cross-impact-cleanup/proposal` — Approach A + 7 ACs
- `#492` `sdd/workspace-capability-bootstrap/design` — origin of the 7 verify checks
- `#513` `sdd/flow-where-cross-project-capability-merge/verify-report` — origin of W1 + W2 warnings
- `#514` `sdd/flow-where-cross-project-capability-merge/archive-report` — confirms W2 follow-up has landed