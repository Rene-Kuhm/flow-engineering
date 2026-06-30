<!-- change spec: workspace-capability-bootstrap (sdd-spec ceremony artifact). Mirrors the OpenSpec delta-spec convention (ADDED / MODIFIED / REMOVED / BDD / Out of Scope / Open Questions). All ADDED Requirements point to the canonical root at `openspec/specs/workspace/spec.md` (the actual deliverable). -->
# workspace-capability-bootstrap (change #N)

> **Change**: `workspace-capability-bootstrap`
> **Phase**: spec (3/7 of SDD cycle)
> **Author**: sdd-spec sub-agent
> **Date**: 2026-06-30
> **Project**: flow-engineering (v1.2.0, main HEAD `d077d75`)
> **Artifact store**: `openspec` (writes `openspec/changes/workspace-capability-bootstrap/specs/workspace/spec.md` + Engram mirror)
> **Strict TDD**: OFF (doc-only change; no tests required)
> **Status**: COMPLETE — ready for design phase
> **Canonical deliverable**: [`openspec/specs/workspace/spec.md`](../../../../specs/workspace/spec.md) (314 lines, under 400-line review budget)

---

## Summary

This change creates the root capability spec at `openspec/specs/workspace/spec.md` to anchor 3 prior workspace-intelligence arc deltas (Phase 1 `projects-ls-extension`, Phase 3 `workspace-status`, Phase 4 `workspace-hygiene`) plus a Phase 5 dashboard placeholder. Phase 2 (`flow-where-cross-project`) is **reclassified** to the `flow-where` capability and documented as a follow-up cross-capability change (`flow-where-cross-project-capability-merge`); no Phase 2 files are moved in this PR.

**Role of this file**: SDD ceremony artifact for traceability. The **canonical** content lives at `openspec/specs/workspace/spec.md`. This file mirrors the OpenSpec delta-spec convention (ADDED / MODIFIED / REMOVED / BDD / Out of Scope / Open Questions) so downstream phases (`sdd-design`, `sdd-tasks`, `sdd-apply`, `sdd-verify`, `sdd-archive`) can mechanically discover what this change adds.

## ADDED Requirements

> Each root-level REQ is fully specified at the canonical location. This file records the cross-reference so sdd-verify can confirm coverage.

### Requirement: REQ-WORKSPACE-PROJECT-IDENTITY

Project identity is defined by 11 static metadata fields emitted by `flow projects ls`/`flow projects ls --json`. The v1 JSON envelope uses `version: "1"` as its first key; `projects` is sorted alphabetically by `name`; missing data is JSON `null`.

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-PROJECT-IDENTITY](../../../../specs/workspace/spec.md#req-workspace-project-identity)
**Source delta**: `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md` (REQ-`--json`-FLAG + REQ-FIELD-EXTENSION + REQ-HAS-ENGRAM-STUB + REQ-SCHEMA-VERSIONING + REQ-DETERMINISTIC-ORDER).

### Requirement: REQ-WORKSPACE-STATUS-DISCOVERY

The `flow workspace status` subcommand surfaces 5 needs-attention rules (R1 dirty-committed, R2 no-git, R3 no-tests, R4 no-openspec on SDD-adjacent stacks, R5 no-graphify informational only). Text default + `--json` envelope (byte-identical for unchanged filesystem states).

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-STATUS-DISCOVERY](../../../../specs/workspace/spec.md#req-workspace-status-discovery)
**Source delta**: `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` (REQ-R1..R5 + REQ-WS-JSON-ENVELOPE + REQ-WS-TEXT-DEFAULT + REQ-WS-EMPTY-ROOT).

### Requirement: REQ-WORKSPACE-MUTATION-SAFETY

Every workspace mutation executes the pollution-protocol triple (`_snapshot_project` → `_apply_rule` → `_verify_post_mutation` → restore on failure). `flow workspace fix` refuses to mutate a non-empty project without `--backup`. Backups at `~/.flow-engineering/backups/<project>/<UTC-ISO-timestamp>/`; retention INDEFINITE in MVP.

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-MUTATION-SAFETY](../../../../specs/workspace/spec.md#req-workspace-mutation-safety)
**Source delta**: `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` (REQ-HYGIENE-POLLUTION-PROTOCOL + REQ-HYGIENE-BACKUP-LAYOUT + REQ-HYGIENE-BACKUP-GATE-NONEMPTY).

### Requirement: REQ-WORKSPACE-DRY-RUN-DEFAULT

`flow workspace fix` and `flow workspace archive` default to dry-run; `--yes` switches to execute mode; both refuse to mutate without `--yes`.

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-DRY-RUN-DEFAULT](../../../../specs/workspace/spec.md#req-workspace-dry-run-default)
**Source delta**: `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` (REQ-HYGIENE-DRY-RUN-DEFAULT).

### Requirement: REQ-WORKSPACE-R1-DEFERRED

R1 dirty-git remediation is OUT OF SCOPE for the workspace-hygiene MVP. `flow workspace fix` does not remediate R1-flagged projects. R3 no-tests and R4 no-openspec bootstrap are also deferred.

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-R1-DEFERRED](../../../../specs/workspace/spec.md#req-workspace-r1-deferred)
**Source delta**: `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` (REQ-HYGIENE-R1-EXPLICITLY-OUT).

### Requirement: REQ-WORKSPACE-REGISTRY-V1

The system persists `~/.flow-engineering/registry.json` with schema `{version: 1, projects: [...], archived: [...]}`. Atomic writes via `tempfile + os.replace`. Read-only consumers do not create the registry.

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-REGISTRY-V1](../../../../specs/workspace/spec.md#req-workspace-registry-v1)
**Source delta**: `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md` (REQ-HYGIENE-REGISTRY-V1).

### Requirement: REQ-WORKSPACE-DASHBOARD-PLACEHOLDER

Phase 5 will add a `workspace-dashboard` sub-capability (TUI or web). This is a placeholder stub; the full requirement text will live in the Phase 5 delta spec.

**Canonical location**: [`openspec/specs/workspace/spec.md` §4 REQ-WORKSPACE-DASHBOARD-PLACEHOLDER](../../../../specs/workspace/spec.md#req-workspace-dashboard-placeholder)
**Source delta**: Forward-looking — no delta spec yet. See canonical spec §7 Future Changes for the `workspace-dashboard` follow-up.

## MODIFIED Requirements

None. This change is purely additive — no existing root-level REQ in `openspec/specs/workspace/spec.md` is modified (because no prior `workspace` root spec exists). No existing root-level REQ in any other capability spec (`flow-where/spec.md`, `decision-drift/spec.md`, `observability/spec.md`, `prompt-registry/spec.md`) is touched.

## REMOVED Requirements

None. No REQ is deprecated or removed by this change. Phase 2 (`flow-where-cross-project`) is **reclassified** (not removed) — see Out of Scope below.

## BDD Scenarios

None. This is a **doc/spec change, not a behavior change** — no new behavior is introduced, so no new Given/When/Then scenarios are required. The 16 BDD scenarios from Phase 4 (`tests/bdd/workspace_hygiene.feature`) and the 7 from Phase 3 (in `tests/bdd/`) remain canonical and untouched. Per locked constraint, **no tests are added in this PR**; the AC9 byte-identical guard at `tests/unit/test_cli_projects.py:435` is the only regression surface, and sdd-verify confirms it stays green.

## Out of Scope

Per `openspec/changes/workspace-capability-bootstrap/proposal.md` §10 — encoded as 14 user-locked constraints. Cross-references to source artifacts:

- **No code modifications** — no `src/` changes, no test changes, no `pyproject.toml` changes (constraint #1).
- **No modifications to any of the 4 prior archived change specs** (Phase 1, Phase 2, Phase 3, Phase 4) — canonical wording stays at the source (constraint #2, #9).
- **No touching** `openspec/changes/v1.1-followups/` — sacred territory (constraint #3).
- **No creation** of `openspec/specs/workspace-hygiene/spec.md` — separate future change (constraint #4, #10).
- **No new behavior** — document what already exists (constraint #5).
- **Phase 2 reclassification is documentation-only** — no files moved in this PR (constraint #6, #7).
- **Workspace family = 3 confirmed sub-capabilities + 1 placeholder (Phase 5)** (constraint #8).
- **Root spec is the family index, NOT the canonical source** — every REQ at root level has a `Source:` line citing the delta spec + REQ ID (constraint #9).
- **7 root-level REQs** synthesized from 25 delta REQs (constraint #10).
- **Drift Detection footer** with explicit mitigation strategy (constraint #11).
- **Cross-Impact section** documenting Phase 2 reclassification with user-quoted rationale (constraint #12).
- **Future Changes section** listing Phase 5 dashboard placeholder + `flow-where-cross-project-capability-merge` follow-up (constraint #13).
- **Under 400-line budget** (constraint #14) — canonical spec is 314 lines, **under by 21%**.
- **No `size:exception`**, **no chained PRs**, **no `openspec/specs/workspace-hygiene/spec.md`** — single PR, single file.

## Open Questions (resolved)

The 5 open questions from the proposal (`openspec/changes/workspace-capability-bootstrap/proposal.md` §11) are resolved before this spec was written. Restated here for traceability:

| # | Question | Answer |
|---|----------|--------|
| Q1 | Phase 2 reclassification — workspace or flow-where? | **`flow-where`** — user accepted reclassification rationale. Phase 2 is documented as a follow-up in this PR; no files moved. |
| Q2 | Root REQ coverage — full enumeration or synthesized? | **7 synthesized** (not full 25). Each synthesized REQ has a `Source:` line citing the delta. |
| Q3 | Root spec role — canonical source or family index? | **Family index only.** Canonical requirements live in delta specs. Root has a prominent "Family index, not canonical source" callout at the top of the spec. |
| Q4 | Phase 5 dashboard — reference now or add later? | **Reference now (REQ-WORKSPACE-DASHBOARD-PLACEHOLDER + §3 row + §7 Future Changes).** Anchors the family shape; prevents the next orphan. |
| Q5 | Phase 2 follow-up name? | **`flow-where-cross-project-capability-merge`** — regenerate Phase 2 delta spec from Engram #456 + merge into `flow-where/spec.md`. |

## Cross-References

- **Canonical deliverable**: [`openspec/specs/workspace/spec.md`](../../../../specs/workspace/spec.md) (314 lines).
- **Proposal** (authoritative source): `openspec/changes/workspace-capability-bootstrap/proposal.md` (Approach B locked, 7 root REQs, 14 user-locked constraints).
- **Explore**: `openspec/changes/workspace-capability-bootstrap/explore.md` (Approach B recommended, Phase 2 reclassification discovered).
- **Phase 1 delta spec** (source of REQ-WORKSPACE-PROJECT-IDENTITY): `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md`.
- **Phase 3 delta spec** (source of REQ-WORKSPACE-STATUS-DISCOVERY): `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md`.
- **Phase 4 delta spec** (source of REQ-WORKSPACE-MUTATION-SAFETY + DRY-RUN-DEFAULT + R1-DEFERRED + REGISTRY-V1): `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md`.
- **Phase 2 evidence** (reclassification rationale): Engram #456 (6 REQs + 7 BDD scenarios); `openspec/changes/flow-where-cross-project/status.md` (surviving artifact).
- **Sibling capability** (reclassification target): `openspec/specs/flow-where/spec.md` (245 LOC gold standard — this spec mirrors its style).
- **Engram mirror** (this spec): topic_key `sdd/workspace-capability-bootstrap/spec`; type `architecture`; `capture_prompt: false`.
