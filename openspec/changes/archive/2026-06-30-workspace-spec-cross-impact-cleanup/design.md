# Design: workspace-spec-cross-impact-cleanup

> **Phase**: 4/8 — `sdd-design` (executed)
> **Change**: `workspace-spec-cross-impact-cleanup` (doc-only)
> **Project**: flow-engineering v1.2.0 · main HEAD `780285f`
> **Strict TDD**: OFF (doc-only — no behavior, no tests)
> **Design philosophy**: *"cambio quirúrgico, verificable, sin tocar arquitectura colateral."*
> **Inputs**: spec #523 (2 single-line edits applied + 7 protected artifacts verified), proposal #521 (locks Approach A + 7 ACs), explore #519 (W1+W2 locations confirmed), design #492 (origin of the 7 verify checks)
> **Output**: this design.md — RE-VALIDATES the 7 verify checks from workspace-capability-bootstrap design #492. **NO new design surface. NO new verify checks.**

## Header

| Field | Value |
|---|---|
| Change | `workspace-spec-cross-impact-cleanup` |
| Phase | 4 of 8 (sdd-design) |
| Strict TDD | OFF |
| Artifact store | openspec (filesystem) + Engram mirror |
| Approach | A (Minimal) — locked by proposal #521 |
| Edits | 2 single-line (W1 at L241, W2 at L16) |
| Net word-tokens | ~3 (post-edit; preserved 315 LF total) |

## 1. Architecture overview (minimal)

This design is a **RE-VALIDATION** of the existing verification surface from `workspace-capability-bootstrap` design #492 §4 — NOT new design. The 7 verify checks (3 schema-shape + 4 structural-presence) were authored when the workspace root spec was created from scratch; they remain the canonical validation surface for this 2-line cleanup because:

- Both W1 + W2 edits land at lines that DO NOT participate in any `Source:` block, path reference, or structural section the 7 checks examine.
- All 7 checks target **protected artifacts** (Source: lines at L96/L114/L124/L134/L144/L164/L174; §6.1 Cross-Impact at L274-292; §7 Future Changes at L296-303; §8 Drift Detection footer at L305-313; "Family index" callout at L4). The edits at L16 + L241 sit entirely outside the protected envelope.

**Data flow** for re-validation: read `openspec/specs/workspace/spec.md` (315 LF) → grep/awk against the 7 check patterns → confirm exit 0 for each → `sdd-verify` aggregates. No new design surface; no new check primitives.

```
  openspec/specs/workspace/spec.md (315 LF, post-edit)
        │
        ├── 7 Source: lines ────► Check 1 (presence) + Check 2 (paths) + Check 3 (REQ-IDs)
        │       (L96/L114/L124/L134/L144/L164/L174, INTACT)
        │
        ├── §6.1 Cross-Impact ──► Check 4 (flow-where merge mention)
        │       (L274-292, INTACT)
        │
        ├── §7 Future Changes ──► Check 5 (workspace-dashboard)
        │       (L296-303, INTACT)
        │
        ├── §8 Drift Detection ► Check 6 (footer presence)
        │       (L305-313, INTACT)
        │
        └── L1-10 (callout) ───► Check 7 (Family index position)
                (L4, INTACT)

  + 7 existing checks (this design re-validates; NO additions)
```

## 2. Re-validation of the 7 verify checks from design #492

For each check: **post-W1/W2 state**, **re-validation method**, **expected line numbers in `workspace/spec.md` (315 LF, post-edit)**.

### Check 1 — Every `## REQ-WORKSPACE-*` block has exactly one `Source:` line (7/7 expected)

- **Post-W1/W2 state**: PASS — no REQ block touched by W1 (L241) or W2 (L16).
- **Re-validation method**: extract all `### REQ-WORKSPACE-` headings; count `**Source:**` lines inside each block; assert count == 1.
- **Expected line numbers**: L96, L114, L124, L134, L144, L164, L174 (7 root REQs, all untouched).

### Check 2 — Every `Source:` path exists on disk (6/6 expected; placeholder excepted)

- **Post-W1/W2 state**: PASS — no `Source:` path touched.
- **Re-validation method**: extract paths from `**Source:** \`<path>\`` lines; verify each file exists on disk.
- **Expected**: 3 unique paths, 6 total occurrences resolve:
  - `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md`
  - `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md`
  - `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md`
- **Excepted**: REQ-WORKSPACE-DASHBOARD-PLACEHOLDER (L174) uses forward-looking form, no path.

### Check 3 — Every `Source:` REQ-ID exists in cited delta spec (19 IDs across 6 root REQs)

- **Post-W1/W2 state**: PASS — no cited REQ-ID touched.
- **Re-validation method**: for each `**Source:** ... §<REQ-ID>` line, grep `^### Requirement: <REQ-ID>` in the cited file.
- **Expected**: 19 IDs across 6 root REQs (placeholder excepted): PROJECT-IDENTITY=5, STATUS-DISCOVERY=8, MUTATION-SAFETY=3, DRY-RUN-DEFAULT=1, R1-DEFERRED=1, REGISTRY-V1=1.

### Check 4 — Cross-Impact mentions `flow-where-cross-project-capability-merge`

- **Post-W1/W2 state**: PASS — §6.1 Cross-Impact at L274-292 is PROTECTED INTACT.
- **Re-validation method**: `grep -F "flow-where-cross-project-capability-merge" openspec/specs/workspace/spec.md` (expect matches at L221 + L241 + L290 + L292).
- **Expected**: 4 post-edit mentions. W2 removed only L16 (carry-forwards meta-pointer in archive-status header L6-L16, NOT a structural §6.1 reference). §6.1 untouched.
- **Important note**: Check 4 targets the §6.1 Cross-Impact block specifically. The L16 carry-forwards reference was a DIFFERENT occurrence (archive-status header) from the §6.1 L290 follow-up pointer + §6.1 L292 RESOLVED note. W2 cleanly removes the L16 occurrence without touching §6.1.

### Check 5 — §7 Future Changes mentions `workspace-dashboard`

- **Post-W1/W2 state**: PASS — §7 Future Changes table at L296-303 is PROTECTED INTACT.
- **Re-validation method**: `grep -F "workspace-dashboard" openspec/specs/workspace/spec.md` (expect matches at L80 §3 table + L174 Source: line + L298 §7 row).
- **Expected**: match in §7 row at L298 (`| 2 | **`workspace-dashboard` (Phase 5)** | ...`). Untouched by W1/W2.

### Check 6 — §8 Drift Detection footer present

- **Post-W1/W2 state**: PASS — §8 Drift Detection at L305-313 is PROTECTED INTACT.
- **Re-validation method**: `grep -F "Drift Detection" openspec/specs/workspace/spec.md` (expect match at L305 H2 heading).
- **Expected**: match in §8 footer (L305-313). Untouched by W1/W2.

### Check 7 — "Family index" callout in first 10 lines

- **Post-W1/W2 state**: PASS — callout at L4 inside blockquote is PROTECTED INTACT.
- **Re-validation method**: `head -n 10 openspec/specs/workspace/spec.md | grep -F "Family index"` (expect match inside L4 blockquote).
- **Expected**: match at L4. Untouched by W1/W2 (W2 lands at L16, far below the 10-line window).

## 3. Post-edit confirmation table

| Protected artifact | Pre-W1/W2 location | Post-W1/W2 location | Change |
|---|---|---|---|
| 7 Source: lines | L96 / L114 / L124 / L134 / L144 / L164 / L174 | same | NONE |
| "Family index" callout | L4 (blockquote) | L4 (blockquote) | NONE |
| Drift Detection footer | L305-313 (§8) | L305-313 (§8) | NONE |
| §6.1 Cross-Impact RESOLVED note | L274-292 | L274-292 | NONE |
| §7 Future Changes table | L296-303 (rows #2-#7) | L296-303 (rows #2-#7) | NONE |
| File total length | 315 LF | 315 LF | NONE (0 net lines) |

**Edits applied (per spec #523 — already on disk, post-edit state)**:

| Edit | Location | Before | After |
|---|---|---|---|
| W1 | L241, §4.2 versioning table, last row | `` `flow-where/spec.md` gains `REQ-V1.0.5..V1.0.X` `` | `` `flow-where/spec.md` gains `REQ-WHERE-CROSS-PROJECT-SCOPE` through `REQ-WHERE-REGEX-OPT-IN` (6 REQs) `` |
| W2 | L16, archive-status meta-pointer | `` `flow-where-cross-project-capability-merge` (Phase 2 follow-up), `` (44 chars) | (removed; remaining 4 carry-forwards grammatically intact) |

## 4. Failure modes + error handling

Identical to design #492 §6 (no new failure modes; the 7 existing checks remain the validation surface):

| Check # | Failure mode | User-visible message | Exit code |
|---|---|---|---|
| 1 | Root REQ missing or duplicating `Source:` | `FAIL: REQ-WORKSPACE-<ID> has <N> Source: lines (expected 1)` | 1 |
| 2 | Cited delta spec path missing or moved | `FAIL: missing <path>` | 1 |
| 3 | Cited REQ-ID missing in cited delta | `FAIL: <root_req> cites <delta_req_id> but <path> does not define it` | 1 |
| 4 | Cross-Impact missing flow-where merge reference | `FAIL: §6 Cross-Impact must mention the flow-where-cross-project-capability-merge follow-up` | 1 |
| 5 | §7 Future Changes missing workspace-dashboard | `FAIL: §7 Future Changes must list workspace-dashboard` | 1 |
| 6 | Drift Detection footer missing | `FAIL: §8 Drift Detection footer missing` | 1 |
| 7 | Family-index callout not in first 10 lines | `FAIL: 'Family index, not canonical source' callout must appear in the first 10 lines` | 1 |

**Aggregation contract**: `sdd-verify` runs all 7 checks; any non-zero exit fails AC3 of proposal #521 and the run halts before declaring PASS.

## 5. Out of Scope (explicit)

- NO new design surface (re-validation only).
- NO new verify checks (7 existing checks from design #492 remain sufficient).
- NO modifications to the canonical spec content (already done in spec phase).
- NO modifications to any prior archive spec.
- NO automated drift detection beyond the 7 checks (deferred to `spec-drift-detector` follow-up per verify-report #513 S1).
- NO cross-link validation across ALL capability specs (deferred to `capability-spec-linter` per #513 S2).
- NO modifications to `openspec/changes/v1.1-followups/`.
- NO code changes.
- NO path changes.
- NO expansion to §4.1 L221, §6.1 L290, §6.1 L292 stale-but-protected prose (informational only; future `workspace-spec-stale-cross-impact-fixes` change requires §6.1 unlock).

## 6. Tech Debt / Follow-up

- **Automated drift detection** (future `spec-drift-detector` change): parse Source: lines, validate REQ-IDs, flag stale prose patterns.
- **Cross-link validation across ALL capability specs** (future `capability-spec-linter` change): extend Checks 2/3 to `flow-where/spec.md`, `decision-drift/spec.md`, `observability/spec.md`, `prompt-registry/spec.md`.
- **3 informational stale-prose items** (future `workspace-spec-stale-cross-impact-fixes` change, requires §6.1 unlock): §4.1 L221 ASCII diagram + §6.1 L290 follow-up pointer + §6.1 L292 `[future-commit-sha]` placeholder.
- **Phase 5 dashboard** (future `workspace-dashboard` change): TUI or web visualization.

## 7. Pre-existing failures (out-of-scope reminder)

- 3 pre-existing ruff errors remain OOS: `cli.py:682 RET504`, `test_cli_where_cross_project.py:33 UP035`, `test_cli_where_cross_project.py:295 W292`.
- 0 pre-existing test failures on main HEAD `780285f` (1513/1513 baseline).
- AC9 byte-identical guard at `tests/unit/test_cli_projects.py:435` preserved (zero code changes; re-run by `sdd-verify` AC8).

## 8. Commit plan (per work-unit-commits skill)

- **Single commit**, conventional format, no AI attribution (per AGENTS.md).
- **Commit message**: `chore(specs): fix W1+W2 stale cross-impact prose in workspace root`
- **Files in commit**: 1 file modification — `openspec/specs/workspace/spec.md` (2 single-line edits at L16 + L241, 315 LF preserved).
- **Diff size**: ~4 diff lines (1 line W1 substitution at L241 + 1 line W2 substring removal at L16; 0 added, 0 removed net).

## 9. Wall-time forecast for tasks → apply → verify → archive

| Phase | Estimate | Rationale |
|---|---|---|
| `sdd-tasks` | ~5 min | ~4-5 mechanical tasks (2 edits + verify gates + commit). |
| `sdd-apply` | ~5 min | 2 single-line edits + `git add` + commit. |
| `sdd-verify` | ~10 min | Run 7 verify checks + confirm 1513/1513 baseline + AC9 byte-identical guard. |
| `sdd-archive` | ~5 min | Move change folder to `archive/2026-06-30-workspace-spec-cross-impact-cleanup/`. |
| **Total remaining** | **~25 min** | Mechanical; smallest cycle in the workspace-intelligence arc. |

## 10. Verdict

**PASS-by-re-validation.** The 7 verify checks from workspace-capability-bootstrap design #492 §4 all survive the W1 + W2 edits unchanged. The verification surface is intact; no new design surface required; no new verify checks introduced. Protected artifacts (Source: lines, §6.1 RESOLVED note, §7 Future Changes rows, Drift Detection footer, Family-index callout) all confirmed untouched.

**Next step**: `sdd-tasks workspace-spec-cross-impact-cleanup`.