# Tasks: `workspace-capability-bootstrap`

> **Change**: `workspace-capability-bootstrap`
> **Phase**: tasks (5 of 8 — sdd-tasks)
> **Project**: flow-engineering v1.2.0, main HEAD `d077d75`
> **Strict TDD**: **OFF** — doc-only change; the 7 verify checks from design §4 ARE the verification surface
> **Inputs** (authoritative): design #492 (229 lines, 7 verify checks at §4); spec #490 (315-line canonical spec at `openspec/specs/workspace/spec.md` + 129-line change-artifact)
> **Output**: `openspec/changes/workspace-capability-bootstrap/tasks.md` (this file)
> **TASKS SCOPE (user-locked)**: 1 confirmation task + 4 verify-check tasks (7 checks total) + 1 baseline preservation + 1 commit + 1 post-commit re-verify. NO new requirements, NO scope expansion.

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Canonical spec LOC | 315 (under 400-line budget by 21%) |
| Change-artifact LOC | 129 (ceremony — NOT counted toward review budget) |
| Total changed lines (single PR) | 315 |
| 400-line budget risk | **Low** (315/400 = 79%) |
| Chained PRs recommended | **No** — single canonical file, well under budget |
| `size:exception` required | **No** |
| `flow-where-cross-project-capability-merge` follow-up | separate future change (named in §7 of canonical spec); OOS here |
| Decision needed before apply | **No** — preflight `chained_pr_strategy: ask-always` → surfaced: single PR is safe; no chain/exception/decision required |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: single-pr
400-line budget risk: Low
```

---

## Task summary

| T# | Title | Files affected | Action | LOC est | Verifies |
|----|-------|---------------|--------|---------|----------|
| T-1 | Confirm canonical spec at correct path with correct line count | `openspec/specs/workspace/spec.md` | read-only confirmation | 0 | AC1, AC11 |
| T-2 | Confirm change-artifact spec at correct path with correct line count | `openspec/changes/workspace-capability-bootstrap/specs/workspace/spec.md` | read-only confirmation | 0 | AC1 (traceability) |
| T-3 | Run verify Check 1 (each root REQ has exactly one `Source:` line) | canonical spec | structural check (awk) | 0 | AC2 |
| T-4 | Run verify Check 2 (every cited `Source:` path exists on disk) | canonical spec + 3 cited delta specs | structural check (grep + test) | 0 | AC2 |
| T-5 | Run verify Check 3 (every cited delta REQ-ID exists in cited file) | 3 cited delta specs (19 IDs total) | structural check (python) | 0 | AC2 |
| T-6 | Run verify Checks 4–7 (Cross-Impact / Future Changes / Drift Detection / Family-index callout) | canonical spec | structural checks (grep + head) | 0 | AC3, AC4, AC5, AC6 |
| T-7 | Baseline preservation (full suite + AC9 guard + mypy + ruff) | repo-wide, no edits | 4 read-only checks | 0 | AC7, AC8, AC10 |
| T-8 | Stage and commit the 2 spec files | 2 spec files (NEW) | git stage + commit | 0 | AC9 (no archive contamination) |
| T-9 | Post-commit re-verify (all 7 verify checks still pass) | canonical spec + 3 delta specs | re-run T-3..T-6 | 0 | AC11 |

**Total task count: 9.** Total LOC added: **315** (canonical spec only — change-artifact is ceremony).

---

## Task definitions

### T-1 — Confirm canonical spec at correct path with correct line count

- **Goal**: Prove `openspec/specs/workspace/spec.md` exists on disk at the canonical path with the expected line count.
- **Action**:
  ```powershell
  Test-Path "openspec\specs\workspace\spec.md"
  (Get-Content -Raw "openspec\specs\workspace\spec.md" -Split "`n").Count
  ```
- **Expected outcome**: `True` + `315` (within 250–350 target, under 400-line budget).
- **Files affected**: none (read-only).
- **Pre-requisites**: none.
- **Acceptance criteria**: AC1 (file exists), AC11 (line count).
- **Risk notes**: line count is LF-based; CRLF may double-count on Windows tooling — use `-Split "`n"` not `Measure-Object -Line`.

### T-2 — Confirm change-artifact spec at correct path with correct line count

- **Goal**: Prove the ceremony spec at `openspec/changes/workspace-capability-bootstrap/specs/workspace/spec.md` exists.
- **Action**:
  ```powershell
  Test-Path "openspec\changes\workspace-capability-bootstrap\specs\workspace\spec.md"
  (Get-Content -Raw "openspec\changes\workspace-capability-bootstrap\specs\workspace\spec.md" -Split "`n").Count
  ```
- **Expected outcome**: `True` + `129` (ceremony, NOT counted toward review budget).
- **Files affected**: none (read-only).
- **Pre-requisites**: none.
- **Acceptance criteria**: AC1 (traceability to change folder).
- **Risk notes**: this file mirrors the root spec at ~40% size — review budget is NOT applied to it.

### T-3 — Run verify Check 1: each root REQ has exactly one `Source:` line

- **Goal**: Detect missing or duplicated `Source:` lines in any of the 7 root REQs.
- **Action** (per design §4 Check 1):
  ```bash
  awk '/^### REQ-WORKSPACE-/ { in_block=1; req=$3; src_count=0; next }
       in_block && /\*\*Source:\*\*/ { src_count++ }
       in_block && /^### /          { printf("%s\t%d\n", req, src_count); in_block=0 }
       END { if (in_block) printf("%s\t%d\n", req, src_count) }' \
    openspec/specs/workspace/spec.md \
  | awk -F'\t' '$2 != 1 { print "FAIL: " $1 " has " $2 " Source: lines"; fail=1 } END { exit fail }'
  ```
- **Expected outcome**: exit `0`; output `7\t1` per row (7 root REQs × 1 `Source:` line each). The placeholder (REQ 7) carries a `Source:` line whose value is `Forward-looking (…no delta spec yet…)` — counted as 1, not 0.
- **Files affected**: none (read-only).
- **Pre-requisites**: T-1.
- **Acceptance criteria**: AC2 (each root REQ has a `Source:` line).
- **Risk notes**: if any `Source:` line is wrapped across multiple markdown lines, the regex may under-count; the design locks the convention to a single line.

### T-4 — Run verify Check 2: every cited `Source:` path exists on disk

- **Goal**: Prove the 3 unique cited delta spec paths exist on disk.
- **Action** (per design §4 Check 2):
  ```bash
  grep -oP 'openspec/changes/[^\s`]+`?\s+§' openspec/specs/workspace/spec.md \
    | grep -oP 'openspec/changes/[^\s`.]+\.md' \
    | sort -u \
    | while read -r path; do
        [ -f "$path" ] || { echo "FAIL: missing $path"; exit 1; }
      done
  ```
- **Expected outcome**: exit `0`; 3 unique paths resolved:
  1. `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md`
  2. `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md`
  3. `openspec/changes/archive/2026-06-30-workspace-hygiene/specs/workspace-hygiene/spec.md`
- **Files affected**: none (read-only).
- **Pre-requisites**: T-1.
- **Acceptance criteria**: AC2 (path existence).
- **Risk notes**: REQ-WORKSPACE-DASHBOARD-PLACEHOLDER has no path — its `Source:` line uses the forward-looking form, which the regex does NOT match (no `openspec/changes/` prefix in body). No false positive.

### T-5 — Run verify Check 3: every cited delta REQ-ID exists in the cited file

- **Goal**: Prove all 19 cited delta REQ-IDs exist as `### Requirement: <REQ-ID>` headings in their cited delta spec files.
- **Action** (per design §4 Check 3, single Python invocation):
  ```bash
  uv run python -c "
  import re, pathlib, sys
  spec = pathlib.Path('openspec/specs/workspace/spec.md').read_text()
  blocks = re.findall(r'^### (REQ-WORKSPACE-[A-Z0-9-]+).*?\n(.*?)(?=^### |\Z)',
                      spec, re.MULTILINE | re.DOTALL)
  fail = 0
  for req, body in blocks:
      if 'forward-looking' in body.lower(): continue
      src = re.search(r'\`([^\`]+)\`\s+§([^\n]+)', body)
      if not src: continue
      path, ids = src.group(1), re.findall(r'REQ-[\`\w-]+', src.group(2))
      src_text = pathlib.Path(path).read_text()
      for rid in ids:
          if not re.search(rf'^### Requirement: {re.escape(rid)}\b', src_text, re.MULTILINE):
              print(f'FAIL: {req} cites {rid} but {path} does not define it'); fail = 1
  sys.exit(fail)
  "
  ```
- **Expected outcome**: exit `0`; 19 delta REQ-IDs resolved across 6 of 7 root REQs (5 + 8 + 3 + 1 + 1 + 1 = 19). REQ-WORKSPACE-DASHBOARD-PLACEHOLDER is exempt (placeholder clause).
- **Files affected**: none (read-only).
- **Pre-requisites**: T-1, T-4.
- **Acceptance criteria**: AC2 (REQ-ID existence per Source: line).
- **Risk notes**: cited-REQ count by root REQ: PROJECT-IDENTITY=5, STATUS-DISCOVERY=8, MUTATION-SAFETY=3, DRY-RUN-DEFAULT=1, R1-DEFERRED=1, REGISTRY-V1=1, DASHBOARD-PLACEHOLDER=0.

### T-6 — Run verify Checks 4–7: structural-presence checks

- **Goal**: Prove the 4 non-`Source:` structural sections are present and positioned correctly.
- **Action** (per design §4 Checks 4–7, run as 4 grep/head one-liners):
  ```bash
  # Check 4: Cross-Impact names the Phase 2 follow-up
  grep -F "flow-where-cross-project-capability-merge" openspec/specs/workspace/spec.md >/dev/null
  # Check 5: Future Changes lists the Phase 5 dashboard
  grep -F "workspace-dashboard" openspec/specs/workspace/spec.md >/dev/null
  # Check 6: Drift Detection footer present
  grep -F "Drift Detection" openspec/specs/workspace/spec.md >/dev/null
  # Check 7: "Family index" callout in first 10 lines (position rule)
  head -n 10 openspec/specs/workspace/spec.md | grep -F "Family index" >/dev/null
  ```
- **Expected outcome**: all 4 exit `0`. Failures would print `FAIL: §<N> <section> must <reason>` (per design §5 failure-mode matrix).
- **Files affected**: none (read-only).
- **Pre-requisites**: T-1.
- **Acceptance criteria**: AC3 (Cross-Impact), AC4 (Future Changes / Phase 5), AC5 (Future Changes / Phase 2 follow-up named), AC6 (Drift Detection footer).
- **Risk notes**: Check 7 enforces **position** (first 10 lines) — if a future maintainer pushes the callout down, this check fails. The position rule is the design's protection against the callout being buried under other content.

### T-7 — Baseline preservation: full suite + AC9 guard + mypy + ruff

- **Goal**: Prove the change is truly doc-only by re-running the project's full verification surface.
- **Action** (4 invocations, all read-only, no files modified):
  ```powershell
  # Full suite — must be 1513/1513 on main HEAD d077d75 baseline
  uv run --frozen pytest

  # AC9 byte-identical guard at tests/unit/test_cli_projects.py:435
  uv run --frozen pytest tests/unit/test_cli_projects.py::test_flow_projects_ls_json_byte_identical_envelope -xvs

  # Type checker
  uv run --frozen mypy src/

  # Linter (3 pre-existing OOS errors expected, no new findings)
  uv run --frozen ruff check .
  ```
- **Expected outcome**:
  - pytest: `1513 passed` (zero new failures).
  - AC9 guard: `1 passed` (byte-identical JSON envelope).
  - mypy: `Success: no issues found in N source files`.
  - ruff: clean OR only the 3 pre-existing OOS errors (`cli.py:682 RET504`, `test_cli_where_cross_project.py:33 UP035`, `test_cli_where_cross_project.py:295 W292`).
- **Files affected**: none (read-only).
- **Pre-requisites**: T-1..T-6 all green.
- **Acceptance criteria**: AC7 (AC9 guard), AC8 (full suite 1513/1513), AC10 (`v1.1-followups/` untouched).
- **Risk notes**: if any of the 4 invocations returns new errors, **STOP** — the change was supposed to be doc-only and any new test/mypy/ruff finding indicates unintended drift.

### T-8 — Stage and commit the 2 spec files

- **Goal**: Commit the new canonical spec + change-artifact as a single work-unit commit.
- **Action** (PowerShell, single line of git plumbing):
  ```powershell
  # Verify no v1.1-followups contamination in the staging set
  git -C "C:\dev\proyects\flow-engineering" status --short

  # Stage exactly the 2 spec files (no wildcards, no globbing)
  git -C "C:\dev\proyects\flow-engineering" add `
    "openspec/specs/workspace/spec.md" `
    "openspec/changes/workspace-capability-bootstrap/specs/workspace/spec.md"

  # Single commit, conventional format, NO AI attribution (per AGENTS.md)
  git -C "C:\dev\proyects\flow-engineering" commit -m "chore(specs): bootstrap workspace root capability spec"
  ```
- **Expected outcome**:
  - Pre-add `git status --short` shows ONLY the new files (`?? openspec/specs/workspace/`, `?? openspec/changes/workspace-capability-bootstrap/`, `?? openspec/changes/v1.1-followups/`). The v1.1-followups line MUST be untouched (AC10).
  - Post-add `git status --short` shows `A  openspec/specs/workspace/spec.md` and `A  openspec/changes/workspace-capability-bootstrap/specs/workspace/spec.md` (and `?? openspec/changes/v1.1-followups/` still untracked).
  - Post-commit `git log --oneline -1` shows the new commit at HEAD with message exactly `chore(specs): bootstrap workspace root capability spec`. No `Co-Authored-By` line.
- **Files affected**: 2 new files (the 2 spec files). v1.1-followups/ stays untracked.
- **Pre-requisites**: T-1..T-7 all green.
- **Acceptance criteria**: AC9 (no archive modifications), AC10 (v1.1-followups untouched).
- **Risk notes**: do NOT use `git add -A` or `git add .` — they may stage v1.1-followups/ or other untracked files. Use explicit paths only. Do NOT use `git commit --amend` after a failed commit — create a new commit per work-unit-commits skill.

### T-9 — Post-commit re-verify: all 7 verify checks still pass

- **Goal**: Confirm the 7 verify checks still pass against the committed canonical spec (no working-tree drift, no commit-hook mangling, no formatting changes).
- **Action**: re-run T-3, T-4, T-5, T-6 verbatim (they are read-only and idempotent against the committed tree).
- **Expected outcome**: all 7 checks exit `0` against the committed `HEAD`. Working tree is clean except for the `v1.1-followups/` untracked entry.
- **Files affected**: none (read-only).
- **Pre-requisites**: T-8 green.
- **Acceptance criteria**: AC11 (final consistency).
- **Risk notes**: if any check fails post-commit, the commit is suspect — investigate before declaring success. Do NOT amend the commit; create a follow-up commit if a fix is needed (per work-unit-commits).

---

## Task ordering and dependency graph

```text
T-1 ─┐
     ├─► T-3 ─┐
T-2 ─┤        │
     ├─► T-4 ─┼─► T-5 ─┐
     │        │        │
     └────────┴─► T-6 ─┴─► T-7 ─► T-8 ─► T-9
                                │        │
                                ▼        ▼
                            (commit) (re-verify)
```

- T-1, T-2: file presence (independent, parallelizable).
- T-3, T-4, T-6: structural checks (depend on T-1, independent of each other).
- T-5: REQ-ID existence (depends on T-4 — paths must exist before checking IDs inside them).
- T-7: baseline preservation (gates the commit; depends on T-3..T-6 all green).
- T-8: commit (depends on T-7 green).
- T-9: post-commit re-verify (depends on T-8).

---

## Forecast

- **Total changed lines**: 315 (canonical) + 129 (change-artifact) = 444 combined, but only 315 counts toward the 400-line review budget.
- **Single PR, 1 commit** (per user pattern; work-unit-commits skill).
- **No `size:exception` needed.**
- **No chained PRs.**
- **Wall-time**: tasks=10 min (this artifact) · apply=10 min · verify=15 min · archive=15 min · **total remaining ~50 min**.

---

## Suggested task ordering for chained PRs

**N/A** — single PR. 315 canonical lines is 79% of the 400-line budget; well under the threshold for `chained-pr` activation.

---

## Out-of-scope task reminders

- **NO** tasks for: any code modification, test additions (no tests for a doc-only change), modifications to `v1.1-followups/`, R1/R3/R4 hygiene operations, Phase 5 dashboard implementation, automated drift detection (deferred per design §7), `workspace-hygiene/spec.md` creation (separate future change), `flow-where/spec.md` modifications.
- The **7 verify checks are the verification surface**; they are NOT unit tests and MUST NOT be added to the test suite in this change.
- **NO new requirements** — tasks derive strictly from design §4 (3 schema-shape + 4 structural-presence checks).

---

## Commit plan (per work-unit-commits skill)

- **One commit**, conventional format, **no AI attribution** (per AGENTS.md).
- **Commit message**: `chore(specs): bootstrap workspace root capability spec`
- **Files in commit**: just the 2 spec files — `openspec/specs/workspace/spec.md` (NEW, canonical) + `openspec/changes/workspace-capability-bootstrap/specs/workspace/spec.md` (NEW, ceremony).
- **PR body**: link AC1–AC11 from `proposal.md`; cite the 7 verify checks as the AC2/AC11 verification surface.
- **Rollback scope**: `git revert HEAD` (no impact on `src/`, `tests/`, archives, or `v1.1-followups/`).

---

## Pre-existing failures (out-of-scope reminder)

- 3 pre-existing lint errors (carried from Phase 4 close-out; remain OOS):
  - `cli.py:682 RET504` (unnecessary assignment before return)
  - `test_cli_where_cross_project.py:33 UP035` (deprecated import)
  - `test_cli_where_cross_project.py:295 W292` (encoding warning)
- 0 pre-existing test failures on main HEAD `d077d75` (Phase 4 session #483 confirmed: 1513/1513).
- AC9 byte-identical guard at `tests/unit/test_cli_projects.py:435` MUST stay green.

---

## Acceptance criteria → task mapping (traceability)

| AC | Description | Verified by |
|----|-------------|-------------|
| AC1 | Root spec exists and references all 4 sub-capabilities | T-1, T-2 |
| AC2 | Each of 7 root REQs has a `Source:` line citing exact delta spec + REQ ID | T-3, T-4, T-5 |
| AC3 | Phase 2 reclassification documented in Cross-Impact | T-6 (Check 4) |
| AC4 | Phase 5 dashboard placeholder documented in Future Changes | T-6 (Check 5) |
| AC5 | `flow-where-cross-project-capability-merge` follow-up named in Future Changes | T-6 (Check 4) |
| AC6 | Drift Detection footer present | T-6 (Check 6) |
| AC7 | AC9 byte-identical guard still passes | T-7 |
| AC8 | Full suite 1513/1513 still passes | T-7 |
| AC9 | NO modifications to any of 4 prior archived specs | T-8 (commit scope is exactly 2 files) |
| AC10 | `v1.1-followups/` UNTOUCHED | T-7, T-8 |
| AC11 | Spec length 250–350 LOC (under 400-line budget) | T-1, T-9 |

---

## Risk summary

Top 3 risks (carried from design #492 §12 + proposal §12):

| # | Risk | Severity | Mitigation in tasks |
|---|------|----------|---------------------|
| 1 | Root REQ synthesis drifts from delta REQ wording over time | Medium | T-3, T-4, T-5 detect drift via Source: presence + path + REQ-ID checks (run on every verify, not just this change) |
| 2 | Reviewer misreads root spec as the canonical source for delta REQs | Low | T-6 Check 7 enforces the "Family index" callout position in the first 10 lines |
| 3 | Phase 2 follow-up (`flow-where-cross-project-capability-merge`) never lands — Phase 2 delta spec stays missing forever | Medium (OOS for this PR) | T-6 Check 4 enforces the named follow-up mention in Cross-Impact; AC5 + AC6 track this |
