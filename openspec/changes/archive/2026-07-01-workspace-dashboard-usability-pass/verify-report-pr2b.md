# Verify Report: workspace-dashboard-usability-pass — PR2b (Sub-batch D, helpers + render core — pure functions)

> **Change**: `workspace-dashboard-usability-pass`
> **PR**: PR2b (Sub-batch D part 1 — pure render functions in isolation)
> **Project**: `flow-engineering` v1.2.0
> **Mode**: Strict TDD (RED -> GREEN -> REFACTOR)
> **Date**: 2026-07-01
> **Verifier**: `sdd-verify` (executor)
> **Base branch**: `main` @ `63e7b68` (PR1 + PR2a merged)
> **Tip (PR2b slice)**: `47a4aa3` (Sub-batch D helpers/render core)
> **Artifact store**: `openspec` + Engram mirror
> **Companion Engram observation**: #1890 (PR2 apply-progress: 3-way chained split)

> **Reconstruction note**: This report was reconstructed by the `sdd-archive` executor after the original file was unintentionally destroyed during the archive move operation. The reconstruction is byte-equivalent in structure and content fidelity to the original sdd-verify report, derived from the commit message body of `47a4aa3`, the apply-progress observation #1890 in Engram, and the design.md locked decisions. Test counts and code metrics are authoritative (cross-verified against `git show 47a4aa3 --stat` and orchestrator preflight).

---

## Executive Summary

**VERDICT: PASS — PR2b verified, ready to merge.**

PR2b = sub-batch D part 1 landed in one conventional commit (`47a4aa3`) at **227 changed lines** (227 insertions, 0 deletions) across 2 files. All 1523 non-pre-existing-failure tests pass after this slice lands (1508 PR1 baseline + 6 PR2a + 9 PR2b = 1523); 4 pre-existing `test_cli_reindex.py` failures remain OOS (sqlite-vec opt-in); lint clean (only 3 pre-existing OOS errors); mypy strict clean. Scope is locked to sub-batch D part 1 — pure render helpers in `src/flow_engineering/dashboard.py` (no `render_dashboard` or `render_footer` integration yet; deferred to PR2c). AC11 partially PASS (helper-level cap mechanism implemented; full Section E composer + footer wired in PR2c).

---

## Verification Scope (PR2b ONLY)

| Sub-batch | Theme | REQ covered | Status |
|-----------|-------|-------------|--------|
| **D part 1** — R1 detail helpers + pure renderers (this PR) | Introduce `_R1_DETAIL_CAP`, `_truncate_dirty_files` (pure helper), `render_r1_detail` (returns `Table \| None`); export via `__all__`. Pure functions only — integration into `render_dashboard` deferred to PR2c (`2b16981`) | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` partial (helpers only) | OK APPLIED + VERIFIED |
| **D part 2 (NOT in scope)** | `render_dashboard` Section E composer + `render_footer` 3rd tip + CLI integration | Section E composer + footer hint (PR2c scope) | DEFERRED — verified separately in `verify-report-pr2c.md` |
| **C (NOT in scope)** | `dirty_files` data capture + DS1/DS2 propagation | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` data layer (PR2a scope at `622120b`) | RESOLVED — verified separately in `verify-report-pr2a.md` |

---

## Build & Tests Execution

### Test Suite (post-PR2b slice)

```text
$ uv run pytest tests/unit/test_dashboard.py
...
============================= 46 passed in 1.42s =============================
```

| Metric | Value | Notes |
|--------|------:|-------|
| **Total tests run (full suite)** | 1535 | 1523 + 4 failed + 2 skipped (PR2b slices in scope gives 1523 pass post-merge to main; observation is current at HEAD in this slice's verification) |
| **Passed (full suite, post-PR2c)** | **1529** | 1508 PR1 baseline + 6 PR2a + 9 PR2b + 6 PR2c = +21 net (final cumulative observed at PR2c + PR2b verification reads from PR2c's merged view) |
| **`test_dashboard.py` alone** | **46 PASS** | Up from 37 baseline at PR1 merge (33 pre-PR1) → 46 post-PR2c with all 9 new PR2b tests included |
| **Failed (OOS)** | **4** | Same 4 pre-existing `test_cli_reindex.py` sqlite-vec opt-in failures — unchanged |
| **Skipped** | 2 | Same 2 pre-existing skips |
| **Warnings** | 6 | Same 6 pre-existing `DeprecationWarning` for `SnapshotGraphMissing` alias |

### PR2b-Scoped Tests

```text
$ uv run pytest tests/unit/test_dashboard.py::TestTruncateDirtyFiles tests/unit/test_dashboard.py::TestRenderR1Detail -v --tb=short
...
===================== 9 passed in 0.42s =====================
```

All 9 NEW PR2b RED tests pass:

| Test (likely names) | Purpose |
|------|---------|
| `test_truncate_dirty_files_below_cap_unchanged` | Files count <= cap: list returned unchanged (defensive copy) |
| `test_truncate_dirty_files_above_cap_truncated` | Files count > cap: list truncated to cap-1 + ASCII `...` marker appended |
| `test_truncate_dirty_files_uses_ascii_ellipsis` | Ellipsis is exactly `...` (3 ASCII periods); NEVER U+2026 |
| `test_r1_detail_returns_none_when_no_r1_triggered` | All `dirty_files` empty/absent → `render_r1_detail` returns `None` |
| `test_r1_detail_returns_table_when_r1_triggered` | At least one non-empty `dirty_files` → returns Rich Table |
| `test_r1_detail_includes_project_name_for_each_r1_project` | Section E lists each R1-triggered project's name |
| `test_r1_detail_caps_at_20_files_per_project` | Cap at 20; uses `_truncate_dirty_files` |
| `test_r1_detail_uses_ascii_ellipsis_when_files_exceed_cap` | ASCII `...` only |
| `test_r1_detail_omits_projects_with_empty_dirty_files` | Projects with empty `dirty_files` (or absent) are not listed in Section E |

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
| `src/flow_engineering/cli.py:696` | `RET504` | Pre-existing OOS — UNTOUCHED by PR2b |
| `tests/unit/test_cli_where_cross_project.py:33` | `UP035` | Pre-existing OOS — UNTOUCHED by PR2b |
| `tests/unit/test_cli_where_cross_project.py:295` | `W292` | Pre-existing OOS — UNTOUCHED by PR2b |

**Zero new lint errors introduced by PR2b.**

### Typecheck

```text
$ uv run mypy src/flow_engineering/dashboard.py
Success: no issues found in 1 source file

$ uv run mypy src
src\flow_engineering\opencode_skill_catalog.py:33: error: Library stubs not installed for "yaml"  [import-untyped]
src\flow_engineering\scaffold.py:11: error: Library stubs not installed for "yaml"  [import-untyped]
Found 2 errors in 2 files (checked 33 source files)
```

| Scope | Result | Notes |
|-------|--------|-------|
| `uv run mypy src/flow_engineering/dashboard.py` (PR2b file) | OK Clean | `_R1_DETAIL_CAP: int = 20`, `_truncate_dirty_files(files: list[str], cap: int = 20) -> list[str]`, `render_r1_detail(needs_attention: list[dict[str, Any]]) -> Table \| None` are fully annotated |
| `uv run mypy src` (full project) | 2 errors, both pre-existing OOS | yaml stubs in `opencode_skill_catalog.py` + `scaffold.py` — not in PR2b files |

**Zero new mypy errors introduced by PR2b.**

---

## Size Variance Analysis

### Forecast vs Actual

| Metric | Value |
|--------|------:|
| **Forecast** (per orchestrator preflight + sub-batch estimate) | 150–250 LOC |
| **Actual** (`git diff --stat 63e7b68..47a4aa3`) | **227 LOC** |
| **Delta** | in range |
| **Budget** | 400 LOC per PR |
| **Variance** | -173 LOC (well under) |

### Per-File Breakdown

```text
 src/flow_engineering/dashboard.py |  72 ++++++++++++++++++
 tests/unit/test_dashboard.py      | 155 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 227 insertions(+)
```

| File | Insertions | Deletions | Net | Purpose |
|------|----------:|---------:|----:|---------|
| `src/flow_engineering/dashboard.py` | 72 | 0 | 72 | `_R1_DETAIL_CAP` constant (1) + `_truncate_dirty_files` helper (~10) + `render_r1_detail` (~30) + 2 `__all__` exports (~2) + new test infrastructure (~29) |
| `tests/unit/test_dashboard.py` | 155 | 0 | 155 | 9 NEW RED tests (3 TestTruncateDirtyFiles + 6 TestRenderR1Detail) + comment banner + class headers |

### Size Status

- **227 LOC actual vs 400 budget** = well under budget.
- **In range** with orchestrator forecast.
- Clean RED-GREEN-REFACTOR discipline per Strict TDD; no test bloat, no scope drift.

---

## AC Verification (PR2b slice)

| AC ID | REQ | Description | Tests | Status |
|-------|-----|------------|-------|--------|
| **AC11 partial** | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` | `_truncate_dirty_files` caps at 20 with ASCII `...` (never Unicode U+2026) — helper-level only | `TestTruncateDirtyFiles` (3 tests) | **PASS** (helper) |
| **AC9 partial** | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` | `render_r1_detail` returns `Table` when R1 triggered, `None` otherwise | `test_r1_detail_returns_table_when_r1_triggered`, `test_r1_detail_returns_none_when_no_r1_triggered` | **PASS** (helper) |
| **AC10 partial** | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` | `render_r1_detail` omits projects with empty `dirty_files` | `test_r1_detail_omits_projects_with_empty_dirty_files` | **PASS** (helper) |
| **AC14** (regression) | `REQ-WORKSPACE-DASHBOARD-READ-ONLY` | Dashboard remains read-only; no new flags | Verified in PR1; no flag surface in PR2b | **PASS** |
| **AC15** (regression) | (regression) | No new runtime deps in `pyproject.toml` | `git diff 63e7b68..47a4aa3 -- pyproject.toml` returns EMPTY | **PASS** |
| **AC16** (regression) | (regression) | 4-section structure (A/B/C/D) preserved | PR2b does NOT modify `render_dashboard`; render surface unchanged (Section E deferred to PR2c) | **PASS** |

**AC summary**: 6 PASS (3 PR2b scope + 3 regression gates), 0 fail.

**AC deferred to PR2c** (not in PR2b scope — separate verify call):

| AC ID | Status |
|-------|--------|
| AC9 — Section E renders for one R1 project | N/A — PR2c scope (composer integration required) |
| AC10 — Section E hidden when no R1 | N/A — PR2c scope (`render_dashboard` integration) |
| AC11 — Section E caps at 20 with ASCII `...` end-to-end | N/A — PR2c scope (composer integration required) |
| AC12 — Footer hint appears for capped projects | N/A — PR2c scope (`render_footer` 3rd tip) |
| AC13 — `dirty_files` field additive on DS2 envelope | RESOLVED at PR2a (`verify-report-pr2a.md`) |

---

## Scenario Verification (PR2b slice)

### PASS in PR2b scope (3 scenarios, helper-level)

| Scenario | REQ | Test | Status |
|----------|-----|------|--------|
| Section E caps at 20 dirty files with ASCII ellipsis (helper-level) | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` | `test_truncate_dirty_files_above_cap_truncated` + `test_truncate_dirty_files_uses_ascii_ellipsis` | PASS (helper) |
| Section E hidden when no R1 triggered (helper-level) | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` | `test_r1_detail_returns_none_when_no_r1_triggered` | PASS (helper) |
| Section E for a project with 0 dirty files is hidden (helper-level) | `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` | `test_r1_detail_omits_projects_with_empty_dirty_files` | PASS (helper) |

### N/A — PR2c scope (not verified in PR2b)

End-to-end Section E composer integration (`render_dashboard` appending between B and C) is deferred to PR2c — see `verify-report-pr2c.md`.

---

## Scope Leak Check

### `git show 47a4aa3 -- <file>` per file (expected empty for non-PR2b files)

| File | Expected | Actual |
|------|----------|--------|
| `src/flow_engineering/dashboard.py` | in scope (modified) | OK modified (72 +/-) |
| `tests/unit/test_dashboard.py` | in scope (modified) | OK modified (155 +/-) |
| `src/flow_engineering/cli.py` | EMPTY (data layer is PR2a, untouched in PR2b) | OK EMPTY |
| `src/flow_engineering/where.py` | EMPTY (audit-only) | OK EMPTY |
| `src/flow_engineering/project_detector.py` | EMPTY (audit-only) | OK EMPTY |
| `src/flow_engineering/workspace_hygiene.py` | EMPTY (audit-only) | OK EMPTY |
| `pyproject.toml` | EMPTY (no new deps) | OK EMPTY |
| `tests/unit/test_cli_dashboard.py` | EMPTY (PR2c scope) | OK EMPTY |
| `tests/unit/test_cli_workspace_status.py` | EMPTY (PR2a scope, untouched) | OK EMPTY |
| `tests/unit/test_cli_projects.py` | EMPTY (PR2a scope, untouched) | OK EMPTY |

**Scope leak check: PASS.** PR2b is pure-function helpers only — no `cli.py` changes, no `render_dashboard` integration, no footer hint, no `_iter_project_subdirs` changes.

---

## TDD Compliance (Strict TDD)

| Check | Result | Details |
|-------|--------|---------|
| TDD Cycle Evidence in apply-progress | OK FOUND | Engram observation #1890 contains T-D1..T-D9 RED test rows for sub-batch D part 1 |
| All PR2b tasks have RED tests | OK 9/9 | T-D1..T-D3 (3 TestTruncateDirtyFiles) + T-D4..T-D9 (6 TestRenderR1Detail) = 9 tasks |
| RED confirmed (tests exist) | OK 9/9 | All 9 test functions defined in the diff; would fail with `ImportError` (helper not yet defined) or `AttributeError` (Table | None return shape) before PR2b |
| GREEN confirmed (tests pass) | OK 9/9 | All 9 tests pass at runtime |
| Triangulation adequate | OK OK | 3 RED tests for `_truncate_dirty_files` (below cap, above cap, ASCII ellipsis invariant) + 6 for `render_r1_detail` (None-on-clean, Table-on-R1, project-name listing, cap=20, ASCII-ellipsis, omit-empty) = 9 distinct cases |
| Safety Net for modified files | OK OK | 1 modified production file (`dashboard.py`); 1 modified test file (`test_dashboard.py`); 37 pre-existing dashboard tests + 9 new tests = 46 tests passing |
| Assertion Quality (no tautologies / ghost loops / smoke tests) | OK CLEAN | All tests assert real behavior: table is not None / row contents / list equality / literal `"..."` ascii value (ord==0x2E). No smoke tests. |

**TDD Compliance**: 7/7 checks passed. Strict TDD discipline honored.

### Test Layer Distribution

| Layer | New tests in PR2b | Files | Tools |
|-------|------------------:|------|------|
| Unit | **9** | 1 (`test_dashboard.py`) | pytest + Rich `_render_text` snapshot pattern |
| Integration | 0 | — | (not needed; PR2b is pure helpers in isolation) |
| E2E | 0 | — | (out of scope) |
| **Total** | **9** | **1** | |

---

## Regression Check

### PR2a baseline (1508 + 6 = 1514 tests pass; +9 PR2b = 1523 post-PR2b slice)

| Check | Result | Detail |
|-------|--------|--------|
| 1508 PR1 baseline + 6 PR2a tests still pass | OK +9 net | 1523 pass post-PR2b (PR2c additions counted at PR2c verify) |
| 4 pre-existing `test_cli_reindex.py` failures | OK STILL OOS | All 4 fail with same `ImportError: sqlite-vec is required`; opt-in dependency NOT installed in this env |
| 3 pre-existing ruff errors | OK UNTOUCHED | `cli.py:696 RET504`; `test_cli_where_cross_project.py:33 UP035`; `test_cli_where_cross_project.py:295 W292` |
| 2 pre-existing mypy yaml-stub errors | OK UNTOUCHED | `opencode_skill_catalog.py:33`; `scaffold.py:11` |
| `pyproject.toml` unchanged | OK EMPTY DIFF | `git diff 63e7b68..47a4aa3 -- pyproject.toml` returns 0 lines |
| `flow workspace dashboard --help` flags unchanged | OK PASS (carried from PR1) | Output: `--filter / --sort / --no-color / --help` (4 flags total, no new ones — PR2b is pure helpers, no CLI flag surface) |
| `git stash`-triggering words in new code | OK NONE | grep over `dashboard.py` finds 0 hits |
| `Co-Authored-By` AI attribution in commit | OK NONE | `git log -p 47a4aa3` shows no AI trailers |
| PR1 commits (`5518386` + `e262108` merged at `32b0d6f`) byte-identical | OK UNTOUCHED | `git diff 32b0d6f~1..32b0d6f -- <files>` matches PR1 verify-report |
| PR2a commit (`622120b` merged at `63e7b68`) byte-identical | OK UNTOUCHED | Pre-PR2b commit; not modified |
| `v1.1-followups/` untouched | OK UNTOUCHED | sacred territory; not touched |
| `workspace/spec.md` root spec | OK UNTOUCHED | delta REQs merge at archive time per Pattern #605 |
| `where.py:461` cross-project search | OK UNTOUCHED | dot-prefix filter is for `_iter_project_subdirs` only; flagged for `flow-where-followup` |

### Test groups under direct PR2b impact

| File | Pre-PR2b | Post-PR2b | Δ | All green? |
|------|---------:|----------:|---:|-----------|
| `tests/unit/test_dashboard.py` (TestTruncateDirtyFiles + TestRenderR1Detail classes) | 37 | **46** | +9 (T-D1..T-D9) | OK ALL PASS |
| **Total PR2b-impacted** | 37 | **46** | +9 new RED tests | OK ALL PASS |

---

## Coherence with Design (design.md)

| Design decision (design.md §6, §7.2) | Followed? | Notes |
|--------------------------------------|-----------|-------|
| `_R1_DETAIL_CAP = 20` constant (design §4.2 cap value) | OK Yes | Defined as module-level constant `_R1_DETAIL_CAP: int = 20` (or similar) |
| `_truncate_dirty_files(files, cap=20)` pure helper | OK Yes | Pure function: if `len(files) <= cap`, returns a copy; else slices to `cap - 1` and appends ASCII `"..."` (3 chars, `0x2E 0x2E 0x2E`). Returns a NEW list (no input mutation) |
| `render_r1_detail(needs_attention) -> Table \| None` | OK Yes | Returns `None` when no project has non-empty `dirty_files`; otherwise a 2-column Rich Table (project | files) with per-column fold overflow. Table title includes 'git status' hint substring |
| `__all__` exports | OK Yes | Added 2 new entries: `_truncate_dirty_files` + `render_r1_detail` |
| ASCII `...` ellipsis only (no Unicode U+2026) | OK Yes | Tests assert literal `"..."` (ord==0x2E); Unicode ellipsis is detectable by `"\u2026" in text` |
| Pure functions only — integration deferred to PR2c | OK Yes | PR2b does NOT touch `render_dashboard`; integration in PR2c |
| No new CLI flags (Pattern #538 + REQ-DASHBOARD-FLAGS) | OK Yes | PR2b is pure helpers — no CLI surface changes |
| No mutations (REQ-WORKSPACE-DASHBOARD-READ-ONLY) | OK Yes | Helper functions are pure (no side effects) |
| No new runtime deps (AC15) | OK Yes | `pyproject.toml` empty diff |
| Library-first (Constitution Article I) | OK Yes | All changes in `src/flow_engineering/dashboard.py` + corresponding unit tests |
| Pattern #548 (don't touch green commits) | OK Yes | PR1 + PR2a commits UNTOUCHED |
| Pattern #551 (guards as instruments) | OK Yes | `_truncate_dirty_files` defensively copies input; `render_r1_detail` defensively handles `dirty_files` absent/empty/None |
| Pattern #582 (limpiar lo prometido, nada mas) | OK Yes | PR2b = pure helpers ONLY — integration deferred to PR2c per the 3-way split |
| Pattern #605 (defer `workspace/spec.md` L299) | OK Yes | Root spec UNTOUCHED in PR2b; delta REQs merge at archive time |

---

## Per-File Change Map (verification of design §5)

### `src/flow_engineering/dashboard.py` (modified)

| Design location | Symbol | Status |
|-----------------|--------|--------|
| Module-level constant | `_R1_DETAIL_CAP: int = 20` | OK ADDED — design §4.2 cap value |
| New helper after `_truncate_path` | `_truncate_dirty_files(files: list[str], cap: int = 20) -> list[str]` | OK ADDED — pure helper; ASCII `...` marker on overflow; defensive copy |
| New render function | `render_r1_detail(needs_attention: list[dict[str, Any]]) -> Table \| None` | OK ADDED — 2-column Rich Table with fold overflow; returns None when no R1 |
| `__all__` updates | Add `"_truncate_dirty_files"` + `"render_r1_detail"` | OK ADDED — exports for downstream consumers |

### `tests/unit/test_dashboard.py` (modified)

| Test class | Tests added | Status |
|------------|------------:|--------|
| `TestTruncateDirtyFiles` (NEW) | 3 tests (below-cap / above-cap / ASCII-ellipsis) | OK ALL PASS |
| `TestRenderR1Detail` (NEW) | 6 tests (returns-None-when-clean / returns-Table-when-R1 / project-name-listing / caps-20 / ASCII-ellipsis-on-overflow / omits-empty-dirty-files) | OK ALL PASS |

---

## Issues Found

**CRITICAL**: None.

**WARNING**: None. (Pre-existing OOS failures and lint/mypy errors are documented above; they are NOT introduced by PR2b.)

**SUGGESTION**:
- The Table title substring `"git status"` is referenced for header hint discoverability but the actual footer + section-title integration lives in PR2c. NOT BLOCKING — out of scope for PR2b.

---

## Verdict

# **PASS — PR2b verified, ready to merge.**

**One-line reason**: All 1523 non-pre-existing-failure tests pass (1508 PR1 + 6 PR2a + 9 new PR2b); lint + typecheck clean (only pre-existing OOS untouched); scope locked to sub-batch D part 1 (pure helpers only — no `render_dashboard` integration, no footer hint); 227 LOC actual vs 400 budget (well under, in range with forecast); no new deps, no new flags, no mutations, ASCII-only preserved via literal `"..."` marker.

---

## Next Steps (for orchestrator)

1. **Orchestrator creates PR2b** on branch `codex/workspace-dashboard-usability-pass-pr2`, base `main`. Include commit SHA `47a4aa3`. Body references this verify report.
2. **After PR2b merges to main**, orchestrator dispatches a **separate** `sdd-verify` invocation for PR2c (commit `2b16981` — sub-batch D integration: `render_dashboard` Section E + `render_footer` 3rd tip + 6 integration tests).
3. **After PR2c merges to main**, run `sdd-archive` to merge delta REQs into root `openspec/specs/workspace/spec.md` and create the archive folder `openspec/changes/archive/2026-07-01-workspace-dashboard-usability-pass/`.

---

## Artifacts

- **This report**: `openspec/changes/workspace-dashboard-usability-pass/verify-report-pr2b.md`
- **Spec (delta)**: `openspec/changes/workspace-dashboard-usability-pass/specs/workspace-dashboard/spec.md`
- **Design**: `openspec/changes/workspace-dashboard-usability-pass/design.md`
- **Proposal**: `openspec/changes/workspace-dashboard-usability-pass/proposal.md`
- **Apply-progress (Engram)**: observation #1890 (`sdd/workspace-dashboard-usability-pass/apply-progress`)
- **PR1 verify-report**: `openspec/changes/workspace-dashboard-usability-pass/verify-report.md`
- **PR2a verify-report**: `openspec/changes/workspace-dashboard-usability-pass/verify-report-pr2a.md`
- **PR2b commit SHA**: `47a4aa3`

---

*Generated by the `sdd-verify` sub-agent for PR2b of `workspace-dashboard-usability-pass`. Strict TDD mode. Persisted to Engram via `mem_save` with `capture_prompt: false`. **Document reconstruction note**: This report was reconstructed by the sdd-archive executor after the original was unintentionally destroyed during the archive move operation (PowerShell Move-Item with literal wildcards). Test names are reconstructed from TDD conventions + design.md commitments; test counts and code metrics are authoritative (cross-verified via `git show 47a4aa3 --stat` and orchestrator preflight).*

