# Tasks: workspace-spec-cross-impact-cleanup

> **Phase**: 5/8 — `sdd-tasks` (executed)
> **Change**: `workspace-spec-cross-impact-cleanup` (doc-only)
> **Project**: flow-engineering v1.2.0 · main HEAD `780285f`
> **Strict TDD**: OFF (doc-only — no RED/GREEN)
> **Inputs**: design #525 (7 checks re-validated), spec #523 (2 edits on disk), proposal #521 (Approach A + 7 ACs)
> **Output**: this tasks.md — 5 mechanical tasks, no expansion

## Header

| Field | Value |
|---|---|
| Change | `workspace-spec-cross-impact-cleanup` |
| Phase | 5 of 8 |
| Strict TDD | OFF |
| Approach | A (Minimal) — locked by proposal #521 |
| Files | 1 (`openspec/specs/workspace/spec.md`) · 4 diff lines · 1 commit |

## Task summary

| T# | Title | Type | Verifies |
|---|---|---|---|
| T-1 | Verify W1 text match at L241 | text-match (Select-String) | AC1 |
| T-2 | Verify W2 text match at L16 | text-match (read L16) | AC2 |
| T-3 | Re-run 7 verify checks from design #492 | structural (7 grep/Test-Path) | AC3, AC6 |
| T-4 | Baseline preservation | gates (pytest + AC9 + mypy + ruff) | AC4, AC5 |
| T-5 | Stage + single commit + post-commit re-verify | git (explicit path + re-run) | AC1, AC2, AC3, AC6, AC7 |

## Task definitions

### T-1 — Verify W1 text match at L241

- **Goal**: Confirm W1 substitution from spec #523 on disk at canonical `workspace/spec.md` L241.
- **Action**: `Select-String -Path openspec\specs\workspace\spec.md -Pattern "REQ-WHERE-CROSS-PROJECT-SCOPE.+REQ-WHERE-REGEX-OPT-IN" | Select-Object -First 1`
- **Expected**: matched line at L241 has new phrase; old `REQ-V1.0.5..V1.0.X` absent.
- **Files affected**: `openspec/specs/workspace/spec.md` (read).
- **Pre-requisites**: none.
- **Acceptance criteria**: AC1.
- **Risk notes**: wording must match §6.1 L292 verbatim per Q1→A1.

### T-2 — Verify W2 text match at L16

- **Goal**: Confirm W2 substring removal from spec #523 on disk at L16 — `flow-where-cross-project-capability-merge` no longer in carry-forwards list.
- **Action**: `Get-Content openspec\specs\workspace\spec.md | Select-Object -Index 15`
- **Expected**: L16 begins `**Carry-forwards documented in Future Changes** (§7): Phase 5`workspace-dashboard`, ...`; no `flow-where-cross-project-capability-merge` token.
- **Files affected**: `openspec/specs/workspace/spec.md` (read).
- **Pre-requisites**: none.
- **Acceptance criteria**: AC2.
- **Risk notes**: comma grammar pre-checked in spec #523.

### T-3 — Re-run 7 verify checks from design #492

- **Goal**: Execute the 7 checks from design #492 §4 (re-validated in design #525 §2): all 7 must PASS.
- **Action**: run checks 1–7 with patterns from design #525 §2 — `grep -c "^### REQ-WORKSPACE-"` (Check 1 = 7) · `Test-Path` × 3 cited paths (Check 2) · `grep -F "Source:"` per REQ block (Check 3 = 19 IDs) · `grep -F "flow-where-cross-project-capability-merge"` expects 4 mentions at L221+L241+L290+L292 (Check 4) · `grep -F "workspace-dashboard"` expects L298 match (Check 5) · `grep -F "Drift Detection"` expects L305 (Check 6) · `head -n 10 ... | grep -F "Family index"` (Check 7).
- **Expected**: all 7 exit 0 (PASS); fail messages match design #525 §4.
- **Files affected**: reads only — `openspec/specs/workspace/spec.md` + 3 cited delta paths.
- **Pre-requisites**: T-1, T-2.
- **Acceptance criteria**: AC3, AC6.
- **Risk notes**: Check 4 expects 4 mentions (NOT 5) after W2 — verify L16 is gone.

### T-4 — Baseline preservation (pytest + AC9 + mypy + ruff)

- **Goal**: Prove zero regression — doc-only change must keep green suite + AC9 + types + lint.
- **Action**: `uv run --frozen pytest` (expect 1513/1513) · `uv run --frozen pytest tests/unit/test_cli_projects.py::test_ac9_byte_identical_guard -v` (expect green) · `uv run --frozen mypy src` (expect 0 errors) · `uv run --frozen ruff check .` (expect 0 new errors; 3 pre-existing OOS tolerated).
- **Expected**: 1513/1513 suite, AC9 green, mypy 0 errors, ruff clean (or 3 pre-existing OOS only).
- **Files affected**: none (gates only).
- **Pre-requisites**: T-3.
- **Acceptance criteria**: AC4, AC5.
- **Risk notes**: `uv run --frozen` pins deps — matches prior cycle invariant.

### T-5 — Stage + single commit + post-commit re-verify

- **Goal**: Land the canonical diff via explicit-path stage, verify only canonical file staged, commit (no AI attribution), and re-run T-1…T-4 against committed HEAD.
- **Action**: `git add openspec/specs/workspace/spec.md` · `git diff --cached --stat` (expect 1 file / 4 diff lines) · `git status` (expect only that file staged) · `git commit -m "chore(specs): fix W1+W2 stale cross-impact prose in workspace root"` · re-run T-1…T-4 against committed HEAD.
- **Expected**: clean commit, 1 file / 4 diff lines, no AI attribution, T-1+T-2+T-3+T-4 re-PASS against `HEAD = 780285f + 1`.
- **Files affected**: `openspec/specs/workspace/spec.md` (only file in commit).
- **Pre-requisites**: T-1, T-2, T-3, T-4 (all green).
- **Acceptance criteria**: AC1, AC2, AC3, AC6, AC7.
- **Risk notes**: explicit `git add <path>` MANDATORY — never `git add .` (would pull ceremony artifacts).

## Task ordering and dependency graph

```
T-1 (W1 @ L241) → T-2 (W2 @ L16) → T-3 (7 checks) → T-4 (gates) → T-5 (commit + re-verify)
```

Linear; no parallelism needed.

## Forecast

| Phase | Estimate |
|---|---|
| sdd-tasks (this) | ~5 min |
| sdd-apply | ~5 min |
| sdd-verify | ~10 min |
| sdd-archive | ~5 min |
| **Total remaining** | **~25 min** |

## Review Workload Forecast

| Field | Value |
|---|---|
| forecast_loc | 4 |
| forecast_canonical_diff | 4 |
| forecast_change_artifact_loc | 60 (ceremony only — not in PR) |
| forecast_total_loc | 64 |
| chained_pr_recommendation | no |
| chained_pr_rationale | 4 diff lines = 1% of budget; single PR trivially sufficient |
| 400_line_budget_risk | low |
| size_exception_required | no |
| size_exception_rationale | null |
| decision_needed_before_apply | no |

Plain-text guard lines (downstream guard contract):

```
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: single-pr
400-line budget risk: Low
```

Delivery strategy: `single-pr` (locked by proposal #521 Q4 → A4).

### Suggested work units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Land W1 + W2 with full gates + post-commit re-verify | PR 1 (single) | base: `main` HEAD `780285f` |

## Out-of-scope task reminders (DO NOT expand)

- NO tasks for: code mods, new verify checks, hash check (no recovered delta), `v1.1-followups/` mods, R1/R3/R4 ops, Phase 5 dashboard, automated drift detection.
- 7 verify checks = entire verification surface — no additions, no checks for §4.1 L221 / §6.1 L290 / L292 (future `workspace-spec-stale-cross-impact-fixes` with §6.1 unlock).
- NO new requirements — tasks strictly from design #525 §3 + user-locked scope.
- DO NOT modify anything outside this file + Engram mirror.

## Commit plan

- Single commit · conventional format · no AI attribution (AGENTS.md rule).
- Message: `chore(specs): fix W1+W2 stale cross-impact prose in workspace root`.
- Files: 1 — `openspec/specs/workspace/spec.md` (L16 + L241, 315 LF preserved).
- Diff size: ~4 lines (1 W1 substitution + 1 W2 removal; 0 net lines).
- No `size:exception` · No chained PRs · No `CHANGELOG.md` touch.

## Pre-existing failures (OOS reminder)

- 3 ruff OOS: `cli.py:682 RET504`, `test_cli_where_cross_project.py:33 UP035`, `test_cli_where_cross_project.py:295 W292`.
- 0 test failures on `780285f` (1513/1513).
- AC9 byte-identical guard at `test_cli_projects.py:435` preserved (T-4 → AC4).

## AC → task mapping

| AC | Description | Tasks |
|---|---|---|
| AC1 | W1 at L241 fixed | T-1, T-5 |
| AC2 | W2 at L16 fixed | T-2, T-5 |
| AC3 | 7 verify checks pass | T-3, T-5 |
| AC4 | AC9 byte-identical guard green | T-4, T-5 |
| AC5 | 1513/1513 suite passes | T-4, T-5 |
| AC6 | No protected artifacts modified | T-3, T-5 |
| AC7 | No `v1.1-followups/` touch, no other tracked files | T-5 |

## Risk summary (per proposal #521 §10)

| # | Risk | Sev | Mitigation |
|---|---|---|---|
| 1 | Scope creep (§4.1 L221 / §6.1 L290 / L292) | Low | User locks + this file §"Out-of-scope" + T-5 explicit `git add <path>` + `git status` |
| 2 | W1 wording drift from §6.1 L292 | Low | T-1 grep enforces exact phrase from spec #523 |
| 3 | W2 grammar broken after removal | Low | T-2 read confirms 4 remaining carry-forwards grammatically intact |
