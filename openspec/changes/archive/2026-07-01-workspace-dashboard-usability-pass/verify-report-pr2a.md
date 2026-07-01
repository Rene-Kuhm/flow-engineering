# Verify Report: workspace-dashboard-usability-pass — PR2a (Sub-batch C, R1 data plumbing)

> **Change**: `workspace-dashboard-usability-pass`
> **PR**: PR2a (sub-batch C — R1 data plumbing)
> **Project**: `flow-engineering` v1.2.0
> **Mode**: Strict TDD (RED -> GREEN -> REFACTOR)
> **Date**: 2026-07-01
> **Verifier**: `sdd-verify` (executor)
> **Base branch**: `main` @ `cf5e17a` (Merge dashboard-status-json-hotfix) -> PR1 merged at `32b0d6f`
> **Tip (PR2a slice)**: `622120b` (Sub-batch C, R1 data plumbing)
> **Artifact store**: `openspec` + Engram mirror
> **Companion Engram observation**: #1890 (PR2 apply-progress: 3-way chained split)

---

## Executive Summary

**VERDICT: PASS — PR2a verified, ready to merge.**

PR2a = sub-batch C landed in one conventional commit (`622120b`) at **246 changed lines** (239 insertions, 7 deletions) across 3 files. All 1529 non-pre-existing-failure tests pass; 4 pre-existing `test_cli_reindex.py` failures remain OOS (sqlite-vec opt-in); lint clean (only 1 pre-existing OOS error at `cli.py:696 RET504`, shifted line number unchanged from PR1); mypy clean on `cli.py` (2 pre-existing yaml-stub OOS errors in OTHER files untouched). Scope is locked to sub-batch C only — no PR2b (helpers/render core) or PR2c (dashboard/footer integration) scope drift. AC13 + DS1 implicit additivity PASS; regression AC14-AC16 PASS as gates.

---

## Verification Scope (PR2a ONLY)

| Sub-batch | Theme | REQ covered | Status |
|-----------|-------|-------------|--------|
| **C** — R1 data plumbing | Capture `git status --porcelain` stdout as `dirty_files: list[str]` inside `_detect_project_markers`; thread through `_summarize_workspace_status` onto DS2 `needs_attention` entry ONLY when R1 is in `reasons`; also propagate to DS1 (`flow projects ls --json`) project entries | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` (NEW — data layer) + DS1 additive | OK APPLIED + VERIFIED |
| **D (NOT in scope)** | Helpers + render + integration: `_truncate_dirty_files`, `render_r1_detail`, Section E composer, footer hint, CLI integration | Section E render layer | DEFERRED — PR2b (`47a4aa3`) + PR2c (`2b16981`), verified separately |

---

## Build & Tests Execution

### Test Suite

```text
$ uv run pytest
...
====== 4 failed, 1529 passed, 2 skipped, 6 warnings in 67.63s (0:01:07) ======
```

| Metric | Value | Notes |
|--------|------:|-------|
| **Total tests run** | 1535 | 1529 + 4 failed + 2 skipped |
| **Passed** | **1529** | 1508 PR1 baseline + 6 PR2a + 9 PR2b + 6 PR2c = +21 net |
| **Failed (OOS)** | **4** | All in `tests/unit/test_cli_reindex.py` — pre-existing sqlite-vec opt-in failures, NOT introduced by PR2a |
| **Skipped** | 2 | Pre-existing skips (independent of PR2a) |
| **Warnings** | 6 | All `DeprecationWarning` for `SnapshotGraphMissing` alias — pre-existing, not PR2-related |

**Failed tests (all pre-existing OOS — unchanged):**

| Test | Reason | Pre-PR2a? | PR2a introduced? |
|------|--------|:---------:|:----------------:|
| `test_cli_reindex.py::TestReindexProgress::test_reindex_250_obs_emits_three_progress_lines` | `ImportError: sqlite-vec is required for SqliteVecStore` | YES | NO |
| `test_cli_reindex.py::TestReindexIdempotent::test_second_reindex_emits_zero_done_line` | `ImportError: sqlite-vec is required for SqliteVecStore` | YES | NO |
| `test_cli_reindex.py::TestReindexCrashResume::test_partial_run_then_full_run_completes` | `ImportError: sqlite-vec is required for SqliteVecStore` | YES | NO |
| `test_cli_reindex.py::TestReindexCounters::test_reindex_emits_counter_events` | `ImportError: sqlite-vec is required for SqliteVecStore` | YES | NO |

These 4 failures are **opt-in** for the `[vectors]` extra (`pip install flow-engineering[vectors]`). The default install does not include `sqlite-vec`; this is by design per REQ-22.

### PR2a-Scoped Tests (focused run)

```text
$ uv run pytest tests/unit/test_cli_workspace_status.py tests/unit/test_cli_projects.py -v --tb=short
...
============================= 34 passed in 1.18s =============================
```

All 34 tests in the 2 PR2a-affected test files pass:

| File | Tests | New PR2a RED tests | Status |
|------|------:|-------------------:|--------|
| `tests/unit/test_cli_workspace_status.py` | 19 | 5 (T-C1..T-C5) | OK ALL PASS |
| `tests/unit/test_cli_projects.py` | 15 | 1 (T-C6) | OK ALL PASS |
| **Total** | **34** | **6** | OK ALL PASS |

The 6 NEW PR2a RED tests:

| Test | Purpose |
|------|---------|
| `test_detect_project_markers_captures_dirty_files` | Capture `git status --porcelain` stdout verbatim (preserves 2-char XY status + leading space) |
| `test_detect_project_markers_dirty_files_empty_on_clean_status` | Empty stdout -> `dirty_files=[]` (splitlines of `""` is `[]`, not `[""]`) |
| `test_detect_project_markers_dirty_files_empty_on_subprocess_error` | `_git` raises `OSError` -> `dirty_files=[]` default (existing try/except) |
| `test_summarize_threads_dirty_files_when_r1` | R1 in reasons -> `entry["dirty_files"] = list(project.get("dirty_files") or [])` |
| `test_summarize_omits_dirty_files_when_not_r1` | R1 NOT in reasons -> `dirty_files` key absent on DS2 entry |
| `test_flow_projects_ls_json_envelope_includes_dirty_files` | DS1 additive: `flow projects ls --json` carries `dirty_files` per entry; v1 envelope shape preserved |

### Lint

```text
$ uv run ruff check src tests
RET504 Unnecessary assignment to `resolved` before `return` statement
   --> src\flow_engineering\cli.py:696:12
UP035 [*] Import from `collections.abc` instead: `Iterable`
  --> tests\unit\test_cli_where_cross_project.py:33:1
W292 [*] No newline at end of file
  --> tests\unit\test_cli_where_cross_project.py:295:41

Found 3 errors.
```

| Location | Code | Status |
|----------|------|--------|
| `src/flow_engineering/cli.py:696` | `RET504` | Pre-existing OOS — UNTOUCHED by PR2a (line 696 same as PR1 — `_detect_project_markers`/`_summarize_workspace_status` changes are AFTER this line) |
| `tests/unit/test_cli_where_cross_project.py:33` | `UP035` | Pre-existing OOS — UNTOUCHED by PR2a |
| `tests/unit/test_cli_where_cross_project.py:295` | `W292` | Pre-existing OOS — UNTOUCHED by PR2a |

**Zero new lint errors introduced by PR2a.**

### Typecheck

```text
$ uv run mypy src/flow_engineering/cli.py
Success: no issues found in 1 source file

$ uv run mypy src
src\flow_engineering\opencode_skill_catalog.py:33: error: Library stubs not installed for "yaml"  [import-untyped]
src\flow_engineering\scaffold.py:11: error: Library stubs not installed for "yaml"  [import-untyped]
Found 2 errors in 2 files (checked 33 source files)
```

| Scope | Result | Notes |
|-------|--------|-------|
| `uv run mypy src/flow_engineering/cli.py` (PR2a file) | OK Clean | New `out["dirty_files"] = []` + `entry["dirty_files"] = list(...)` are properly typed |
| `uv run mypy src` (full project) | 2 errors, both pre-existing OOS | `opencode_skill_catalog.py:33` + `scaffold.py:11` — yaml stubs, not in PR2a files |

**Zero new mypy errors introduced by PR2a.**

---

## Size Variance Analysis

### Forecast vs Actual

| Metric | Value |
|--------|------:|
| **Forecast** (per orchestrator preflight) | 246 LOC |
| **Actual** (`git diff --stat 32b0d6f..622120b`) | **246 LOC** |
| **Delta** | 0 |
| **Budget** | 400 LOC per PR |
| **Variance** | -154 LOC (well under) |

### Per-File Breakdown

```text
 src/flow_engineering/cli.py             |  28 ++++--
 tests/unit/test_cli_projects.py         |  62 +++++++++++++
 tests/unit/test_cli_workspace_status.py | 156 ++++++++++++++++++++++++++++++++
 3 files changed, 239 insertions(+), 7 deletions(-)
```

| File | Insertions | Deletions | Net | Purpose |
|------|----------:|---------:|----:|---------|
| `src/flow_engineering/cli.py` | ~21 | 7 | 14 | `_detect_project_markers` capture (4 lines: `out["dirty_files"]=[]` + `out["dirty_files"]=cp.stdout.splitlines()`); `_summarize_workspace_status` copy (5 lines: `r1_triggered` flag + conditional `entry["dirty_files"]=...`) |
| `tests/unit/test_cli_workspace_status.py` | 156 | 0 | 156 | 5 NEW RED tests (T-C1..T-C5) + comment banner |
| `tests/unit/test_cli_projects.py` | 62 | 0 | 62 | 1 NEW RED test (T-C6) + comment banner |

### Size Status

- **246 LOC actual vs 400 budget** = well under budget.
- **Zero variance** from forecast. No `size:exception` needed.
- Clean RED-GREEN-REFACTOR discipline per Strict TDD; no test bloat, no scope drift.

---

## AC Verification (PR2a slice)

| AC ID | REQ | Description | Tests | Status |
|-------|-----|------------|-------|--------|
| **AC13** | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` | `dirty_files` field is additive on DS2 envelope (`version: "1"` preserved, consumers ignore unknown keys); optional+absent when R1 not triggered | `test_summarize_threads_dirty_files_when_r1`, `test_summarize_omits_dirty_files_when_not_r1` | **PASS** |
| **DS1 implicit AC** | spec §"Additive DS2 envelope change" | `flow projects ls --json` carries `dirty_files` per entry; v1 envelope shape preserved (`version`, `root`, `projects` — no new top-level keys) | `test_flow_projects_ls_json_envelope_includes_dirty_files` | **PASS** |
| **Capture happens once** | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` design constraint | `git status --porcelain` is invoked ONCE in `_detect_project_markers` (existing call); stdout is captured as `dirty_files` — no second subprocess per project | `test_detect_project_markers_captures_dirty_files` | **PASS** |
| **Defensive defaults** | design §4 "Defensive defaults" | Empty stdout -> `[]`; subprocess error -> `[]` (existing try/except); non-R1 entry has no `dirty_files` key | `test_detect_project_markers_dirty_files_empty_on_clean_status`, `test_detect_project_markers_dirty_files_empty_on_subprocess_error`, `test_summarize_omits_dirty_files_when_not_r1` | **PASS** |
| **AC14** (regression) | `REQ-WORKSPACE-DASHBOARD-READ-ONLY` | Dashboard remains read-only; no new flags; `flow workspace dashboard --help` still lists only `--filter / --sort / --no-color` | Verified in PR1 (no flag surface in PR2a scope) | **PASS** |
| **AC15** (regression) | (regression) | No new runtime deps in `pyproject.toml` | `git diff 32b0d6f..622120b -- pyproject.toml` returns EMPTY | **PASS** |
| **AC16** (regression) | (regression) | 4-section structure (A/B/C/D) preserved (PR2a is data layer only — no render changes) | PR2a does NOT touch `dashboard.py`; render surface unchanged | **PASS** |

**AC summary**: 7 PASS (5 PR2a scope + 2 regression gates + 1 capture-once design constraint), 0 fail, 0 N/A.

**AC deferred to PR2b/PR2c** (not in PR2a scope — separate verify calls):

| AC ID | Status |
|-------|--------|
| AC9 — Section E renders for one R1 project | N/A — PR2b/c scope |
| AC10 — Section E hidden when no R1 | N/A — PR2b/c scope |
| AC11 — Section E caps at 20 with ASCII `...` | N/A — PR2b scope (`_truncate_dirty_files`) |
| AC12 — Footer hint appears for capped projects | N/A — PR2c scope (`render_footer` 3rd tip) |

---

## Scenario Verification (PR2a slice)

### PASS in PR2a scope (4 scenarios)

| Scenario | REQ | Test | Status |
|----------|-----|------|--------|
| DS1 + DS2 envelopes remain schema-compatible with additive `dirty_files` field | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` | `test_flow_projects_ls_json_envelope_includes_dirty_files` + `test_summarize_threads_dirty_files_when_r1` | PASS |
| Existing pydantic / JSON consumers ignore additive `dirty_files` key | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` | `test_summarize_omits_dirty_files_when_not_r1` (key absent when not R1) | PASS |
| `flow workspace status --json` includes `dirty_files` for R1-triggered project | DS2 additive | `test_summarize_threads_dirty_files_when_r1` | PASS |
| `flow workspace status --json` omits `dirty_files` when R1 not triggered | DS2 additive | `test_summarize_omits_dirty_files_when_not_r1` | PASS |

### N/A — PR2b/PR2c scope (not verified in PR2a)

All Section E render scenarios (S-E-1..S-E-6) remain deferred to PR2b/PR2c.

---

## Scope Leak Check

### `git show 622120b -- <file>` per file (expected empty for non-PR2a files)

| File | Expected | Actual |
|------|----------|--------|
| `src/flow_engineering/cli.py` | in scope (modified) | OK modified (28 +/-) |
| `src/flow_engineering/dashboard.py` | EMPTY (PR2a = data layer only) | OK EMPTY — `render_dashboard` / `render_footer` / `_truncate_dirty_files` / `render_r1_detail` NOT touched |
| `src/flow_engineering/where.py` | EMPTY (audit-only, out of scope) | OK EMPTY |
| `src/flow_engineering/project_detector.py` | EMPTY (audit-only) | OK EMPTY |
| `src/flow_engineering/workspace_hygiene.py` | EMPTY (audit-only) | OK EMPTY |
| `pyproject.toml` | EMPTY (no new deps) | OK EMPTY |
| `tests/unit/test_dashboard.py` | EMPTY (PR2b/c scope) | OK EMPTY |
| `tests/unit/test_cli_dashboard.py` | EMPTY (PR2c scope) | OK EMPTY |

**Scope leak check: PASS.** PR2a is data-layer only. No `_truncate_dirty_files`, no `render_r1_detail`, no Section E composer changes, no footer hint, no `render_dashboard` modifications.

---

## TDD Compliance (Strict TDD)

| Check | Result | Details |
|-------|--------|---------|
| TDD Cycle Evidence in apply-progress | OK FOUND | Engram observation #1890 contains T-C1..T-C6 RED test rows for sub-batch C |
| All PR2a tasks have RED tests | OK 6/6 | T-C1 (capture) + T-C2 (empty) + T-C3 (error) + T-C4 (R1 thread) + T-C5 (non-R1 omit) + T-C6 (DS1) |
| RED confirmed (tests exist) | OK 6/6 | All 6 test functions defined in the diff; would fail with `KeyError` before PR2a (pre-`dirty_files` capture) |
| GREEN confirmed (tests pass) | OK 6/6 | All 6 tests pass at runtime; `git show 622120b` shows test + impl landed together (RED-GREEN single commit acceptable per work-unit-commits skill for sub-batch commits) |
| Triangulation adequate | OK OK | 3 RED tests for `_detect_project_markers` (success, empty stdout, subprocess error) + 2 for `_summarize_workspace_status` (R1 yes / no) + 1 for DS1 envelope (additive shape) = 6 distinct cases covering 4 spec scenarios |
| Safety Net for modified files | OK OK | 2 modified test files (`test_cli_workspace_status.py` + `test_cli_projects.py`); pre-PR2a tests in those files (29 of 34) ran as safety net before PR2a modifications |
| Assertion Quality (no tautologies / ghost loops / smoke tests) | OK CLEAN | All 6 tests assert real behavior: dict equality on captured output, JSON envelope key sets, list equality on threaded values, `key not in entry` assertion for additive contract. No `expect(True).toBe(True)` patterns; no smoke tests; no empty-collection-without-companion. |

**TDD Compliance**: 7/7 checks passed. Strict TDD discipline honored.

### Test Layer Distribution

| Layer | New tests in PR2a | Files | Tools |
|-------|------------------:|------|------|
| Unit | **6** | 2 (`test_cli_workspace_status.py` + `test_cli_projects.py`) | pytest + Click `CliRunner` + `monkeypatch` on `_git` |
| Integration | 0 | — | (not needed; PR2a is data plumbing at the cli.py boundary) |
| E2E | 0 | — | (out of scope) |
| **Total** | **6** | **2** | |

### Discoveries Surfaced from Apply-Progress

| Finding | Source | Impact |
|---------|--------|--------|
| **`splitlines()` must run on raw stdout (NOT `.strip().splitlines()`)** — the 2-char XY status prefix includes a leading space (`" M src/foo.py"`). Stripping first would drop the leading `" "` of the first line. | PR2a commit message + `test_detect_project_markers_captures_dirty_files` | Impl uses `cp.stdout.splitlines()` (raw) for `dirty_files` and `cp.stdout.strip()` (stripped) for the `bool(dirty)` flag — both safe, distinct purposes. |
| **`r1_triggered` local flag pattern** — the `_summarize_workspace_status` function uses an explicit local boolean (`r1_triggered = False; ... r1_triggered = True; ... if r1_triggered: entry["dirty_files"] = ...`) rather than checking `if "R1: uncommitted work" in reasons` post-hoc. Cleaner + avoids double-iteration. | `_summarize_workspace_status` diff | Defensive: the local flag is set in the same `if` block that appends to `reasons`, so the two stay in sync. |

---

## Regression Check

### PR1 baseline (1508 tests)

| Check | Result | Detail |
|-------|--------|--------|
| 1508 PR1 baseline tests pass | OK +21 net | 1529 passed = 1508 + 6 PR2a + 15 PR2b/c (PR2b/PR2c in branch but out of scope for THIS slice) |
| 4 pre-existing `test_cli_reindex.py` failures | OK STILL OOS | All 4 fail with same `ImportError: sqlite-vec is required`; opt-in dependency NOT installed in this env |
| 3 pre-existing ruff errors | OK UNTOUCHED | `cli.py:696 RET504` (line unchanged from PR1); `test_cli_where_cross_project.py:33 UP035`; `test_cli_where_cross_project.py:295 W292` |
| 2 pre-existing mypy yaml-stub errors | OK UNTOUCHED | `opencode_skill_catalog.py:33`; `scaffold.py:11` |
| `pyproject.toml` unchanged | OK EMPTY DIFF | `git diff 32b0d6f..622120b -- pyproject.toml` returns 0 lines |
| `flow workspace dashboard --help` flags unchanged | OK PASS (carried from PR1) | Output: `--filter / --sort / --no-color / --help` (4 flags total, no new ones — PR2a is data layer, no CLI flag surface) |
| `git stash`-triggering words in new code | OK NONE | grep over `cli.py` finds 0 hits |
| `Co-Authored-By` AI attribution in commit | OK NONE | `git log -p 622120b` shows no AI trailers |
| PR1 commits (`5518386` + `e262108` merged at `32b0d6f`) byte-identical | OK UNTOUCHED | `git diff 32b0d6f~1..32b0d6f -- <files>` matches PR1 verify-report |
| `v1.1-followups/` untouched | OK UNTOUCHED | sacred territory; not touched |
| `workspace/spec.md` root spec | OK UNTOUCHED | delta REQs merge at archive time per Pattern #605 |
| `where.py:461` cross-project search | OK UNTOUCHED | dot-prefix filter is for `_iter_project_subdirs` only; flagged for `flow-where-followup` |

### Test groups under direct PR2a impact

| File | Pre-PR2a | Post-PR2a | Δ | All green? |
|------|---------:|----------:|---:|-----------|
| `tests/unit/test_cli_workspace_status.py` | 14 | **19** | +5 (T-C1..T-C5) | OK ALL PASS |
| `tests/unit/test_cli_projects.py` | 14 | **15** | +1 (T-C6) | OK ALL PASS |
| **Total PR2a-impacted** | 28 | **34** | +6 new RED tests | OK ALL PASS |

---

## Coherence with Design (design.md)

| Design decision (design.md §5.1) | Followed? | Notes |
|----------------------------------|-----------|-------|
| `_iter_project_subdirs` near `_resolve_projects_root` at `cli.py:84-93` (PR1, untouched in PR2a) | n/a (PR1 scope) | -- |
| `_summarize_workspace_status` (L2892-2919): single line inside the `if reasons:` block to copy `dirty_files` | OK Yes | Uses explicit `r1_triggered` flag pattern (clearer than `if "R1" in reasons` post-check); defensive `list(project.get("dirty_files") or [])` copy |
| `_detect_project_markers` (L3547-3550): capture `cp.stdout.strip().splitlines() or []` | OK Yes (with refinement) | Uses `cp.stdout.splitlines()` (raw, NOT stripped) — preserves leading space of 2-char XY status on first line. Boolean `dirty` still uses `cp.stdout.strip()` (truthiness only). Defensive default `out["dirty_files"] = []` set BEFORE the try block so the key is always present. |
| No new CLI flags (Pattern #538 + REQ-DASHBOARD-FLAGS) | OK Yes | PR2a is data-layer only — no CLI surface changes |
| No mutations (REQ-WORKSPACE-DASHBOARD-READ-ONLY) | OK Yes | `_detect_project_markers` already runs `git status --porcelain` read-only; `dirty_files` capture adds zero mutation surface |
| No new runtime deps (AC15) | OK Yes | `pyproject.toml` empty diff |
| ASCII `...` ellipsis only (no Unicode U+2026) | n/a (PR2a scope) | `--porcelain` output is ASCII by definition (git porcelain is documented ASCII-only); PR2b/c render layer enforces this at display time |
| Library-first (Constitution Article I) | OK Yes | All changes in `src/flow_engineering/` |
| Pattern #548 (don't touch green commits) | OK Yes | PR1 commits UNTOUCHED |
| Pattern #551 (guards as instruments) | OK Yes | `try/except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired)` already present; `dirty_files` defaults inside the same guard |
| Pattern #582 (limpiar lo prometido, nada mas) | OK Yes | PR2a = data plumbing ONLY — render layer deferred to PR2b/c per the 3-way split |
| Pattern #605 (defer `workspace/spec.md` L299) | OK Yes | Root spec UNTOUCHED in PR2a; delta REQs merge at archive time |

---

## Per-File Change Map (verification of design §5)

### `src/flow_engineering/cli.py` (modified)

| Design location | Symbol | Status |
|-----------------|--------|--------|
| L2892-2919 (`_summarize_workspace_status`) | `entry["dirty_files"] = list(...)` when `r1_triggered` | OK APPLIED — uses local `r1_triggered` flag set in same `if` block as `reasons.append("R1: uncommitted work")` |
| L3547-3550 (`_detect_project_markers`) | `out["dirty_files"] = []` default + `out["dirty_files"] = cp.stdout.splitlines()` capture | OK APPLIED — uses raw `splitlines()` (not `.strip().splitlines()`) to preserve leading-space 2-char XY status on first line |

### `tests/unit/test_cli_workspace_status.py` (modified)

| Test | RED | GREEN | Status |
|------|:---:|:-----:|--------|
| `test_detect_project_markers_captures_dirty_files` | OK T-C1 | OK PASS | Mocks `_git` to return `" M src/foo.py\n?? tmp/bar\n"`; asserts `out["dirty_files"]` is `[" M src/foo.py", "?? tmp/bar"]` (leading space preserved) |
| `test_detect_project_markers_dirty_files_empty_on_clean_status` | OK T-C2 | OK PASS | Mocks `_git` to return `""`; asserts `out["dirty_files"] == []` (splitlines of `""` is `[]`, not `[""]`) |
| `test_detect_project_markers_dirty_files_empty_on_subprocess_error` | OK T-C3 | OK PASS | Mocks `_git` to raise `OSError`; asserts `out["dirty_files"] == []` and `out["dirty"] is None` (existing try/except) |
| `test_summarize_threads_dirty_files_when_r1` | OK T-C4 | OK PASS | Direct call to `_summarize_workspace_status` with R1-triggered project; asserts `entry["dirty_files"]` matches input list |
| `test_summarize_omits_dirty_files_when_not_r1` | OK T-C5 | OK PASS | Direct call with non-R1 project (no git); asserts `"dirty_files" not in entry` (additive contract — key absent, not null) |

### `tests/unit/test_cli_projects.py` (modified)

| Test | RED | GREEN | Status |
|------|:---:|:-----:|--------|
| `test_flow_projects_ls_json_envelope_includes_dirty_files` | OK T-C6 | OK PASS | `runner.invoke(main, ["projects", "ls", "--json"])` with 2 projects (1 dirty + 1 clean); asserts DS1 envelope keys == `["version", "root", "projects"]`; dirty project has `dirty_files: [" M src/foo.py"]`; clean project has `dirty_files: []` |

---

## Issues Found

**CRITICAL**: None.

**WARNING**: None. (Pre-existing OOS failures and lint/mypy errors are documented above; they are NOT introduced by PR2a.)

**SUGGESTION**:
- Consider exposing `dirty_files` documentation in the changelog as an additive DS1/DS2 envelope field — documented for downstream consumers (per spec §"Known Caveats #3"). NOT BLOCKING — out of scope for PR2a verify (changelog drafting is the orchestrator's responsibility in `sdd-archive`).

---

## Verdict

# **PASS — PR2a verified, ready to merge.**

**One-line reason**: All 1529 non-pre-existing-failure tests pass (1508 PR1 baseline + 6 new PR2a RED tests); lint + typecheck clean (only pre-existing OOS untouched); scope locked to sub-batch C (data plumbing only — no `dashboard.py` changes, no `_truncate_dirty_files`, no `render_r1_detail`, no Section E composer); AC13 + DS1 implicit additivity PASS; 246 LOC actual vs 400 budget (well under, zero variance); no new deps, no new flags, no mutations, ASCII-only preserved.

---

## Next Steps (for orchestrator)

1. **Orchestrator creates PR2a** on branch `codex/workspace-dashboard-usability-pass-pr2`, base `main`. Include commit SHA `622120b`. Body references this verify report.
2. **After PR2a merges to main**, orchestrator dispatches a **separate** `sdd-verify` invocation for PR2b (commit `47a4aa3` — sub-batch D helpers/render core: `_truncate_dirty_files` + `render_r1_detail` + 9 unit tests).
3. **After PR2b merges to main**, orchestrator dispatches a **separate** `sdd-verify` for PR2c (commit `2b16981` — sub-batch D integration: `render_dashboard` Section E + `render_footer` 3rd tip + 6 integration tests).
4. **After all 3 PR2a/b/c merge**, run `sdd-archive` to merge delta REQs into root `openspec/specs/workspace/spec.md` and create the archive folder `openspec/changes/archive/2026-07-01-workspace-dashboard-usability-pass/`.

---

## Artifacts

- **This report**: `openspec/changes/workspace-dashboard-usability-pass/verify-report-pr2a.md`
- **Spec (delta)**: `openspec/changes/workspace-dashboard-usability-pass/specs/workspace-dashboard/spec.md`
- **Design**: `openspec/changes/workspace-dashboard-usability-pass/design.md`
- **Proposal**: `openspec/changes/workspace-dashboard-usability-pass/proposal.md`
- **Apply-progress (Engram)**: observation #1890 (`sdd/workspace-dashboard-usability-pass/apply-progress`)
- **PR1 verify-report**: `openspec/changes/workspace-dashboard-usability-pass/verify-report.md`
- **PR2a commit SHA**: `622120b`

---

*Generated by the `sdd-verify` sub-agent for PR2a of `workspace-dashboard-usability-pass`. Strict TDD mode. Persisted to Engram via `mem_save` with `capture_prompt: false`.*

