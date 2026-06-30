# Proposal: workspace-spec-cross-impact-cleanup

> **Phase**: 2/8 — `sdd-propose`
> **Change**: `workspace-spec-cross-impact-cleanup` (doc-only)
> **Project**: flow-engineering v1.2.0 · main HEAD `780285f`
> **Artifact store**: openspec + Engram mirror
> **Strict TDD**: OFF (doc-only)
> **Scope discipline**: W1 + W2 ONLY. Limpiar lo prometido, no abrir otra caja.

## 1. Header

| Field | Value |
|---|---|
| **Change** | `workspace-spec-cross-impact-cleanup` |
| **Purpose** | Clean W1 + W2 stale prose in `openspec/specs/workspace/spec.md` carried forward from `flow-where-cross-project-capability-merge` verify #513. ~3 word-tokens net change. |
| **Builds on** | explore #519 (Approach A Minimal; exact W1/W2 locations confirmed) |
| **Strict TDD** | OFF (doc-only) |
| **Forecast** | 2 single-line edits, single PR, 1 commit, ~3 word-tokens |

## 2. Approach A locked

**Approach A (Minimal)** — reaffirmed. Two single-line edits in `openspec/specs/workspace/spec.md`:

| Edit | Location | What changes |
|---|---|---|
| W1 | L241, §4.2 versioning table | `REQ-V1.0.5..V1.0.X` → `REQ-WHERE-CROSS-PROJECT-SCOPE through REQ-WHERE-REGEX-OPT-IN` |
| W2 | L16, archive-status meta-pointer | remove `flow-where-cross-project-capability-merge` from carry-forwards list |

- NO verify check additions (7 existing checks from design #492 still pass)
- ~3 word-tokens net change (~10 word-tokens including surrounding context, 0 lines added/removed)
- Single PR, 1 commit
- Under 400-line review budget

## 3. W1 fix details

| Field | Value |
|---|---|
| **Location** | `openspec/specs/workspace/spec.md` L241, §4.2 versioning table, last row |
| **Current text** | `` `flow-where/spec.md` gains `REQ-V1.0.5..V1.0.X` `` |
| **Fixed text** | `` `flow-where/spec.md` gains `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` (6 REQs) `` |
| **Rationale** | Matches exact wording of §6.1 L292 RESOLVED note (consistency); gives concrete REQ IDs for spot-check |
| **Multiplicity** | 1 occurrence only (confirmed by grep) |
| **Edit type** | Single-line, in-place substitution; surrounding lines untouched |

## 4. W2 fix details

| Field | Value |
|---|---|
| **Location** | `openspec/specs/workspace/spec.md` L16, Archive status meta-pointer sentence |
| **Current text** | ``**Carry-forwards documented in Future Changes** (§7): `flow-where-cross-project-capability-merge` (Phase 2 follow-up), Phase 5...`` |
| **Fixed text** | ``**Carry-forwards documented in Future Changes** (§7): Phase 5 `workspace-dashboard`, optional `workspace-hygiene-capability-spec`, `backup-retention-policy` review, R1/R3/R4 deferred rules.`` |
| **Rationale** | Follow-up has landed (apply `6e21d4d`, archive `8d51c5f`); §7 row already removed (verify-report #513 AC7); stale pointer contradicts §6.1 RESOLVED note |
| **Multiplicity** | 1 occurrence only (confirmed by grep) |
| **Edit type** | Single-line; 44 characters removed; grammar of remaining sentence intact |

## 5. Protected artifacts inventory

These categories are **must remain intact** — zero modifications permitted:

| Protected artifact | Location | Status |
|---|---|---|
| Source: lines for 7 root REQs | L96, L114, L124, L134, L144, L164, L174 | INTACT — W1/W2 do not touch any REQ block |
| "Family index" callout | L4 (blockquote) | INTACT — fix is at L16 + L241 |
| Drift Detection footer | L305-313 | INTACT — fix is at L16 + L241, far from §8 |
| §6.1 Cross-Impact RESOLVED note | L274-292 | INTACT — both fixes are outside §6.1 |
| §7 Future Changes table rows | L296-303 (rows #2–#7) | INTACT — W2 edit is in archive-status meta-pointer, not §7 |
| 7 verify checks from design #492 | §4 of design #492 | STILL PASS — re-validated in explore §7 table |

## 6. 3 informational stale-prose items (FUTURE cleanup only)

The following were found during explore but are **explicitly out of scope** per user locks. Documented here for audit trail; do NOT fix in this change:

| Location | Stale content | Future change |
|---|---|---|
| §4.1 ASCII diagram, L221 | `flow-where-cross-project-capability-merge follow-up` reference | `workspace-spec-stale-cross-impact-fixes` |
| §6.1 Cross-Impact, L290 | `**Follow-up** (\`flow-where-cross-project-capability-merge\`)`: See §7...` pointer | `workspace-spec-stale-cross-impact-fixes` |
| §6.1 Cross-Impact, L292 | `[future-commit-sha]` placeholder (actual SHA: `6e21d4d96fbc9d94a0814c0f677cd03cb1f4bb07`) | `workspace-spec-stale-cross-impact-fixes` |

**Note**: §6.1 is PROTECTED per user locks; §4.1 is protected by "W1 + W2 ONLY" lock. These cannot be touched in this change.

## 7. Acceptance criteria (7 ACs for sdd-verify)

- **AC1**: W1 at L241 fixed — `` `REQ-V1.0.5..V1.0.X` `` → `` `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` (6 REQs) ``
- **AC2**: W2 at L16 fixed — `` `flow-where-cross-project-capability-merge` (Phase 2 follow-up), `` removed from carry-forwards list; remaining 4 carry-forwards grammatically intact
- **AC3**: 7 verify checks from workspace-capability-bootstrap design #492 still pass post-fix (explore §7 re-validation confirms)
- **AC4**: AC9 byte-identical guard still green (`tests/unit/test_cli_projects.py:435`, zero code changes)
- **AC5**: Full test suite 1513/1513 still passes (zero regressions; doc-only)
- **AC6**: NO modifications to protected artifacts — Source: lines (L96/114/124/134/144/164/174), §6.1 RESOLVED note (L274-292), §7 Future Changes rows (L296-303), Drift Detection footer (L305-313), "Family index" callout (L4)
- **AC7**: NO touch of `openspec/changes/v1.1-followups/`; NO modifications to any other tracked file (cli.py, pyproject.toml, CHANGELOG.md, flow-where/spec.md, etc.)

## 8. Out of Scope (explicit)

- §4.1 L221 stale cross-impact diagram text → `workspace-spec-stale-cross-impact-fixes` (future)
- §6.1 L290 stale follow-up pointer → `workspace-spec-stale-cross-impact-fixes` (future)
- §6.1 L292 `[future-commit-sha]` placeholder → `workspace-spec-stale-cross-impact-fixes` (future)
- Any new verify checks (7 existing checks remain; auto-detection deferred to `spec-drift-detector` follow-up)
- Any code modifications (strictly doc-only)
- Any modifications to `openspec/specs/flow-where/spec.md` or other tracked files
- Any `size:exception` label
- Any chained PRs

## 9. Open Questions (resolved)

| Q | A |
|---|---|
| Q1: W1 wording — generic wildcard vs enumerated? | A1: **Enumerated** — "REQ-WHERE-CROSS-PROJECT-SCOPE through REQ-WHERE-REGEX-OPT-IN" matches §6.1 L292 verbatim; gives concrete IDs for spot-check |
| Q2: W2 — remove cleanly vs "landed" marker? | A2: **Remove cleanly** — matches verify-report #513 AC7 precedent; audit trail preserved in §6.1 RESOLVED + Engram #514 + archive-report |
| Q3: 3 informational stale-prose items in §4.1/§6.1? | A3: **Future cleanup** — `workspace-spec-stale-cross-impact-fixes`; not this PR |
| Q4: PR structure? | A4: **Single PR, 1 commit**, no chained, no `size:exception` |

## 10. Risks (top 3)

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **Scope creep during apply** — tempted to also clean §4.1 L221 / §6.1 L290 / L292 | Low | User locks + explore "Other Stale Prose Survey" explicitly defer; apply phase reads explore before editing |
| 2 | **Wording drift between W1 fix and §6.1 RESOLVED note** | Low | W1 fix reuses exact `REQ-WHERE-CROSS-PROJECT-SCOPE through REQ-WHERE-REGEX-OPT-IN` phrase from §6.1 L292 |
| 3 | **Verify Check 4 regression** — 5 mentions of `flow-where-cross-project-capability-merge` exist; W2 removes only L16 | Low | After W2 fix: 4 mentions remain (L221, L241, L290, L292); Check 4 still passes |

## 11. Forecast

| Phase | Wall time |
|---|---|
| sdd-propose (this) | ~10 min |
| sdd-spec | ~5 min |
| sdd-design | ~5 min (no new design surface) |
| sdd-tasks | ~5 min |
| sdd-apply | ~5 min |
| sdd-verify | ~10 min |
| sdd-archive | ~5 min |
| **Total cycle** | **~45 min** |

- 2 single-line edits in `openspec/specs/workspace/spec.md`
- ~3 word-tokens net change
- Single PR, 1 commit
- Review budget: ~3 lines of diff (well under 400-line cap)
