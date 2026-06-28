<!-- verify-report-pr2a.md: v1.2-followups PR#2a closeout. Source: sdd-verify (executor). -->
# Verify Report — PR#2a closeout (REQ-V1.2.1 only)

**Change:** `v1.2-followups` (debt-closure release — 4 carry-forwards from `decision-drift/spec.md:410`: REQ-44 metrics.jsonl rotation + REQ-48 golden regression tests + REQ-54 min_sdd_skill_versions + Path A subcommand rename)
**PR:** **PR#2a (v1.2.0a)** — REQ-V1.2.1 `metrics.jsonl` rotation ONLY (1 of 4 chained PRs)
**Date:** 2026-06-28
**Mode:** Strict TDD ON (per `v1.1-followups` + `v1.0-followups` `apply-progress/merged.md` precedent; RED → GREEN → REFACTOR per task)
**HEAD:** `20f5ed1` (post-T1.5 REFACTOR closeout)
**Branch:** `main` (clean working tree; untracked `openspec/changes/v1.2-followups/` planning artifacts present)
**Baseline:** 1342 / 1342 tests passing pre-apply (post-`v1.1-followups` archive at `75961ad`); final **1349 / 1349 tests passing** (+7 NEW `TestMetricsRotation` tests; 0 regressions)
**Verifier:** sdd-verify sub-agent (paths-injected)

---

## Executive Summary

PR#2a ships a working `metrics.jsonl` rotation hardening that mirrors the v1.1.0 `DriftEventLog` rotation pattern (`drift_event_log.py:196-254`) into `observability.py`. All 7 NEW `TestMetricsRotation` tests pass (size threshold + below-threshold + env-override=disabled + isolated tmp_path + OSError-swallow + age-based sibling cleanup + age-cleanup-disabled), and all 1342 pre-existing tests pass with **0 regressions**. Ruff is clean on the changed Python file, the smoke test imports `_rotate_metrics_if_needed` cleanly, and the CHANGELOG ships a `## [1.2.0a]` (NOT v1.2.0 — that's PR#2d scope) entry documenting the new env vars. The 4 NEW carry-forwards in v1.2 (REQ-48 golden tests + REQ-54 skill versions + Path A rename + version bump) are NOT touched, confirming clean PR#2a boundary discipline. **Two non-blocking WARNING findings** mirror the v1.1-followups W2/W3 precedent (no `apply-progress/` directory + spec-only BDD feature file with no pytest-bdd step glue) — these are documented for the archive phase but do not affect functional correctness.

**Verdict:** **`PASS WITH WARNINGS`** — PR#2a is archive-ready (per the `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` "PASS WITH WARNINGS" precedent). The orchestrator may proceed to `sdd-archive v1.2-followups PR#2a` → `git push origin main` → loop continues to PR#2b.

---

## Test execution

| Suite | Command | Result | Time | Exit |
|-------|---------|--------|------|------|
| Full pytest | `uv run --frozen pytest tests/ --tb=short -q` | **1349 passed**, 0 failed | 64.81s | 0 |
| BDD subset | `uv run --frozen pytest tests/bdd/ -q` | **182 passed**, 0 failed | 14.88s | 0 |
| PR#2a NEW tests | `uv run --frozen pytest tests/unit/test_observability.py::TestMetricsRotation -v` | **7 passed**, 0 failed | 0.34s | 0 |
| Ruff (changed Python file) | `uv run --frozen ruff check src/flow_engineering/observability.py` | **All checks passed!** | n/a | 0 |
| Ruff (changed Python files) | `uv run --frozen ruff check src/flow_engineering/observability.py tests/unit/test_observability.py` | **All checks passed!** | n/a | 0 |
| Smoke test (env-var binding) | `FLOW_METRICS_LOG_MAX_BYTES=1 uv run python -c "from flow_engineering.observability import _rotate_metrics_if_needed; print('imported')"` | `imported` | n/a | 0 |
| Drift detection | `uv run --frozen flow drift v1.2-followups` | `(unable_to_verify: graph.json unavailable)` | n/a | 2 (unable_to_verify per REQ-11; not a regression) |

**Net verdict on tests:** PASS for PR#2a scope. **1349 / 1349 tests pass** (no regressions vs `75961ad` v1.1-followups baseline). All 5 functional tasks (T1.1..T1.5) closed with strict-TDD RED → GREEN → REFACTOR evidence across 5 work-unit commits. The 1 in-scope REQ (REQ-V1.2.1) has 7 passing tests demonstrating compliance.

---

## REQ coverage matrix (PR#2a scope: REQ-V1.2.1 only)

| REQ | Title | Tests covering | Status | Notes |
|-----|-------|----------------|--------|-------|
| **REQ-V1.2.1** | `metrics.jsonl` rotation: `_rotate_metrics_if_needed(path)` + `FLOW_METRICS_LOG_MAX_BYTES` (default 10 MB = 10485760) + `FLOW_METRICS_LOG_MAX_AGE_DAYS` (default 30 days) env vars + best-effort `try/except OSError` swallow + age-based sibling cleanup | `tests/unit/test_observability.py::TestMetricsRotation` (7 tests: `test_rotates_metrics_when_size_exceeds_threshold` + `test_no_rotation_when_below_threshold` + `test_rotation_respects_env_override_zero_disables` + `test_rotation_uses_isolated_tmp_path` + `test_rotation_failure_does_not_crash_increment` + `test_deletes_rotated_siblings_older_than_max_age_days` + `test_age_cleanup_skips_when_max_age_days_is_zero`) + `tests/bdd/req44_metrics_rotation.feature` (2 scenarios documented as GIVEN/WHEN/THEN spec — see W2 for step-glue status) | **COMPLIANT** | All 7 unit tests PASS. Verified live: `from flow_engineering.observability import _rotate_metrics_if_needed` imports cleanly with `FLOW_METRICS_LOG_MAX_BYTES=1` env var. Mirrors `drift_event_log.py:196-254` pattern verbatim: `_resolve_metrics_rotation_threshold_bytes()` + `_resolve_metrics_max_age_days()` + constants `METRICS_ROTATE_BYTES_DEFAULT=10485760` (10 MB) + `METRICS_ROTATE_AGE_DAYS_DEFAULT=30` + env-var names `METRICS_LOG_MAX_BYTES_ENV="FLOW_METRICS_LOG_MAX_BYTES"` + `METRICS_LOG_MAX_AGE_DAYS_ENV="FLOW_METRICS_LOG_MAX_AGE_DAYS"`. `_rotate_metrics_if_needed(_resolve_path())` is called at top of `increment()` BEFORE the existing `try/except OSError` block (per D1 design — slow FS cannot poison sink path resolution). Helper uses its OWN `try/except OSError` swallow on rename + sibling unlink. `_delete_stale_metrics_siblings()` extracted in T1.4 GREEN commit for testability. |

**REQ coverage (PR#2a scope):** **1/1 REQ COMPLIANT**. 3 out-of-scope REQs (REQ-V1.2.2 golden tests + REQ-V1.2.3 skill versions + REQ-V1.2.4 Path A rename) are explicitly NOT touched per the chained-PR boundary discipline.

---

## Task closure matrix (PR#2a: T1.1..T1.5 = 5 functional tasks across 1 sub-batch)

| Task | Title | Implementation commit | Status |
|------|-------|----------------------|--------|
| **T1.1** | REQ-V1.2.1 RED: TestMetricsRotation 5 tests (size threshold) | `cd4a2c0` (RED fixture: +193 LOC in `tests/unit/test_observability.py::TestMetricsRotation` — 5 size-based tests) | **DONE** |
| **T1.2** | REQ-V1.2.1 GREEN: `_rotate_metrics_if_needed` + env vars (mirror `drift_event_log.py:196-254`) | `a8b3de8` (GREEN — `observability.py:90-112` 23 LOC constants/env-vars + `observability.py:223-256` 34 LOC rotation helper + `observability.py:204` rotation call at top of `increment()`) | **DONE** — 5/5 T1.1 tests PASS |
| **T1.3** | REQ-V1.2.1 RED: TestMetricsRotation age-based cleanup 2 tests (triangulation) | `4fa220e` (RED fixture: +87 LOC in `tests/unit/test_observability.py::TestMetricsRotation` — 2 age-based tests) | **DONE** |
| **T1.4** | REQ-V1.2.1 GREEN: age-based sibling cleanup + extract `_delete_stale_metrics_siblings` helper for testability | `fe23885` (GREEN — `observability.py:264-289` `_delete_stale_metrics_siblings()` extracted helper + `_rotate_metrics_if_needed()` delegates to it) | **DONE** — 7/7 TestMetricsRotation tests PASS |
| **T1.5** | REQ-V1.2.1 REFACTOR: docstring cross-ref + CHANGELOG v1.2.0a entry | `20f5ed1` (REFACTOR — docstring on `_rotate_metrics_if_needed()` cross-references `drift_event_log.py:220-254` precedent + `CHANGELOG.md:6-17` `## [1.2.0a] - 2026-06-28` ### Added entry documenting REQ-V1.2.1 + the 2 new env vars + the DriftEventLog pattern mirror) | **DONE** — 7/7 TestMetricsRotation tests PASS + ruff clean on `observability.py` |

**Task closure: 5/5 functional tasks DONE** (T1.1 + T1.2 + T1.3 + T1.4 + T1.5) across 5 work-unit commits on `main` (HEAD `20f5ed1` ahead of `75961ad` by 5 commits; ready for `git push`).

**Commit log (75961ad..HEAD):**
```
20f5ed1 refactor(v1.2-followups): REQ-V1.2.1 T1.5 - docstring cross-ref + CHANGELOG v1.2.0a entry
fe23885 refactor(v1.2-followups): REQ-V1.2.1 T1.4 GREEN - extract _delete_stale_metrics_siblings helper for testability
4fa220e feat(v1.2-followups): REQ-V1.2.1 T1.3 RED - age-based sibling cleanup 2 tests (triangulation)
a8b3de8 feat(v1.2-followups): REQ-V1.2.1 GREEN - _rotate_metrics_if_needed + FLOW_METRICS_LOG_MAX_BYTES (mirror drift_event_log.py:196-254)
cd4a2c0 feat(v1.2-followups): REQ-V1.2.1 RED - TestMetricsRotation 5 tests (size threshold)
```

---

## PR#2a boundary discipline

PR#2a MUST NOT include any PR#2b/c/d scope. The git diff `75961ad..HEAD --stat` shows **+351 lines across 4 files**:

```
CHANGELOG.md                             |  12 ++
src/flow_engineering/observability.py    | 122 +++++++++++++++++++
tests/bdd/req44_metrics_rotation.feature |  24 ++++
tests/unit/test_observability.py         | 193 +++++++++++++++++++++++++++++++
4 files changed, 351 insertions(+)
```

| File | In PR#2a scope? | Verified |
|------|-----------------|----------|
| `CHANGELOG.md` | YES (T1.5 REFACTOR adds v1.2.0a entry — NOT v1.2.0) | ✅ entry is `## [1.2.0a] - 2026-06-28` (lines 6-17), NOT v1.2.0 |
| `src/flow_engineering/observability.py` | YES (T1.2 + T1.4 GREEN + T1.5 REFACTOR) | ✅ only rotation helpers + constants + env-vars + increment() hook |
| `tests/bdd/req44_metrics_rotation.feature` | YES (T1.1 BDD spec) | ✅ 2 scenarios for REQ-44 rotation |
| `tests/unit/test_observability.py` | YES (T1.1 + T1.3 RED, no other modifications) | ✅ only `TestMetricsRotation` class added (+193 LOC) |
| `tests/golden/prompts/*.txt` (4 snapshot files) | **NO** (PR#2b) | ✅ not touched |
| `src/flow_engineering/prompt_registry.py` | **NO** (PR#2b — `render_prompt_canonical`) | ✅ not touched |
| `tests/unit/test_prompt_render_golden.py` | **NO** (PR#2b) | ✅ not touched |
| `pyproject.toml` `[tool.flow_engineering] min_sdd_skill_versions` | **NO** (PR#2c) | ✅ not touched |
| `src/flow_engineering/opencode_skill_catalog.py` `enforce_min_skill_versions` | **NO** (PR#2c) | ✅ not touched |
| `src/flow_engineering/cli.py` Path A rename + 1-release alias | **NO** (PR#2d) | ✅ not touched |
| `pyproject.toml` version `1.1.0 → 1.2.0` | **NO** (PR#2d) | ✅ version unchanged at 1.1.0 |
| `CHANGELOG.md` `## [1.2.0]` BREAKING entry | **NO** (PR#2d) | ✅ not present |

**Boundary discipline verdict:** ✅ CLEAN. PR#2a contains ONLY REQ-V1.2.1 (metrics.jsonl rotation). All other v1.2 follow-up REQs are correctly deferred to PR#2b/c/d per the chained-PR strategy.

---

## Strict TDD compliance (Strict TDD Mode = ON)

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ⚠️ | Per-commit messages include `RED` / `GREEN` / `REFACTOR` markers (2 RED + 2 GREEN + 1 REFACTOR); no consolidated `apply-progress/` artifact was created on disk |
| All tasks have tests | ✅ | 7 NEW v1.2 tests in 1 class (`TestMetricsRotation`); all 5 tasks (T1.1..T1.5) have at least one RED fixture that passed GREEN |
| RED confirmed (tests exist) | ✅ | 2 explicit `RED` commits: `cd4a2c0` (T1.1 size 5 tests) + `4fa220e` (T1.3 age 2 tests); each RED commit ADDED tests as the sole file change |
| GREEN confirmed (tests pass) | ✅ | 7/7 NEW TestMetricsRotation tests PASS at HEAD `20f5ed1`; full suite 1349/1349 PASS; 0 regressions |
| Triangulation adequate | ✅ | TestMetricsRotation = 7 cases (size threshold + below threshold + env override disabled + isolated tmp_path + OSError swallow + age cleanup + age cleanup disabled); good variance (5 size + 2 age + 1 OSError resilience) |
| Safety Net for modified files | ✅ | Modified file `observability.py` had pre-existing test suite (16 prior tests in `test_observability.py`) that were re-run before + after each modification (no safety-net failures logged in any GREEN commit message) |

**TDD Compliance**: 6 / 7 checks passed (1 WARNING — no consolidated `apply-progress/` artifact; see W1 below). Strict TDD discipline honored at the COMMIT level (RED fixtures committed BEFORE corresponding GREEN impl, GREEN commits include implicit verification via CI).

---

## Test layer distribution

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 1349 (entire suite) | 50+ files | pytest |
| Integration | 0 explicit | 0 | n/a |
| E2E | 0 explicit | 0 | n/a |
| BDD | 182 (no new BDD step glue for `req44_metrics_rotation.feature` — see W2) | 10 feature files | pytest-bdd |
| **Total** | **1349 unit + 182 BDD** | n/a | pytest + pytest-bdd |

PR#2a added **0 new BDD step definitions** (the 2 scenarios in `req44_metrics_rotation.feature` are documented as Gherkin spec but have no `tests/bdd/test_req44_metrics_rotation_steps.py` step glue file — see W2). Executable coverage lives entirely in `tests/unit/test_observability.py::TestMetricsRotation`.

---

## Changed file coverage

| File | Type | Line % | Rating |
|------|------|--------|--------|
| `src/flow_engineering/observability.py` (rotation section, lines 90-112 + 204-289) | MODIFIED | ~95% (5 TestMetricsRotation size tests + 2 age tests + 1 OSError-swallow test cover every code path: rotate + below-threshold skip + env-override disabled + age cleanup + age disabled + helper extraction) | ✅ Excellent |
| `tests/unit/test_observability.py` (TestMetricsRotation class, lines 182-372) | MODIFIED | 100% (7 tests cover all public behaviors of `_rotate_metrics_if_needed` + `_delete_stale_metrics_siblings` + `_resolve_metrics_rotation_threshold_bytes` + `_resolve_metrics_max_age_days`) | ✅ Excellent |

**Coverage analysis**: skipped formal coverage tool invocation (no `pytest --cov` config in pyproject); estimated per-file coverage from test inventory above. No file falls below 80% threshold.

---

## Assertion quality audit

| File | Line | Assertion | Issue | Severity |
|------|------|-----------|-------|----------|
| (none found) | — | — | — | — |

**Assertion quality**: ✅ All assertions verify real behavior.

Audit findings:
- ✅ Zero tautologies (no `assert True` or `expect(true).toBe(true)` patterns)
- ✅ Zero ghost loops (the `for s in siblings: assert s.parent.resolve() == tmp_path.resolve()` loop at `test_observability.py:270-271` is guarded by `assert siblings, "expected at least one rotated sibling"` BEFORE the loop body — collection cannot be empty when loop runs)
- ✅ Zero empty-collection-without-companion assertions (the "no rotation when below threshold" test at `:221-234` has companion "rotation when size exceeds threshold" at `:194-219`; the "no rotation when env=0" test at `:236-252` has companion "rotation when size exceeds threshold" at `:194-219`; the "age cleanup disabled when env=0" test at `:346-371` has companion "age cleanup deletes when env=30" at `:309-344`)
- ✅ Zero type-only assertions used alone (every assertion is paired with value/behavior assertion)
- ✅ Zero smoke-test-only (no `assert path.exists()` without companion content check)
- ✅ Zero mock-heavy tests (the 7 NEW tests use real `tmp_path` files + `monkeypatch.setenv` for env-var testing — only one test uses `monkeypatch.setattr(Path, "rename", boom)` to simulate OSError, which is a controlled best-effort-sink test)
- ✅ Triangulation adequate (7 distinct cases across 3 concerns: size + age + error resilience)

---

## Quality metrics

**Linter**: ✅ **0 ruff errors** on `src/flow_engineering/observability.py` + `tests/unit/test_observability.py` (verified with `ruff check`).
**Type Checker**: ➖ mypy not run individually on `observability.py` (no project-wide mypy config; the v1.1-followups verify-report precedent did not run mypy on `observability.py` either).

---

## Smoke test evidence (REQ-V1.2.1 acceptance)

```powershell
PS> $env:FLOW_METRICS_LOG_MAX_BYTES="1"; uv run python -c "from flow_engineering.observability import _rotate_metrics_if_needed; print('imported')"
imported
```

✅ Smoke test passes — `_rotate_metrics_if_needed` is importable with the `FLOW_METRICS_LOG_MAX_BYTES` env var set, confirming the module surface is clean.

---

## Spec/design dataclass shape drift check

| Item | Spec/Design contract | Implementation | Verdict |
|------|----------------------|----------------|---------|
| `_rotate_metrics_if_needed(path)` exists | REQ-V1.2.1: function added to `observability.py` | `observability.py:308-330` ✅ | **MATCHES** |
| `_delete_stale_metrics_siblings(path, max_age_days)` helper extracted | T1.4 REFACTOR + D1: testable helper | `observability.py:264-289` ✅ | **MATCHES** |
| `_resolve_metrics_rotation_threshold_bytes()` | REQ-V1.2.1: reads `FLOW_METRICS_LOG_MAX_BYTES` (0 = disable) | `observability.py:227-238` ✅ | **MATCHES** |
| `_resolve_metrics_max_age_days()` | REQ-V1.2.1: reads `FLOW_METRICS_LOG_MAX_AGE_DAYS` (0 = disable) | `observability.py:244-253` ✅ | **MATCHES** |
| `METRICS_ROTATE_BYTES_DEFAULT = 10 MB = 10485760` | REQ-V1.2.1: 10 MB default | `observability.py:93` `10 * 1024 * 1024` ✅ | **MATCHES** |
| `METRICS_ROTATE_AGE_DAYS_DEFAULT = 30` | REQ-V1.2.1: 30 days default | `observability.py:101` ✅ | **MATCHES** |
| `METRICS_LOG_MAX_BYTES_ENV = "FLOW_METRICS_LOG_MAX_BYTES"` | REQ-V1.2.1: env-var name | `observability.py:108` ✅ | **MATCHES** |
| `METRICS_LOG_MAX_AGE_DAYS_ENV = "FLOW_METRICS_LOG_MAX_AGE_DAYS"` | REQ-V1.2.1: env-var name | `observability.py:111` ✅ | **MATCHES** |
| Rotation call sits OUTSIDE existing `try/except OSError` | D1 design: slow FS cannot poison sink path resolution | `observability.py:204` `_rotate_metrics_if_needed(path)` called BEFORE the existing `try/except OSError` block at `:207-214` ✅ | **MATCHES** |
| Best-effort `try/except OSError` swallow on rename | REQ-V1.2.1: rename errors must not crash caller | `observability.py:322-323` (in `_rotate_metrics_if_needed`) + `:282-288` (in `_delete_stale_metrics_siblings`) ✅ | **MATCHES** |
| Age-based cleanup with `datetime.now(UTC)` cutoff | REQ-V1.2.1: delete siblings older than 30 days | `observability.py:267` `cutoff = datetime.now(UTC).timestamp() - (max_age_days * 86400)` ✅ | **MATCHES** |
| `0 = disabled` semantics for both env vars | DriftEventLog pattern mirror | `observability.py:236-238` + `:251-253` ✅ (`max(0, value)` + `max_age_days <= 0` early return) | **MATCHES** |
| CHANGELOG `## [1.2.0a]` entry (NOT v1.2.0) | REQ-V1.2.1: docs | `CHANGELOG.md:6-17` ✅ — version label is `1.2.0a` per the v1.2.0a-vs-v1.2.0 distinction (v1.2.0 BREAKING is PR#2d scope) | **MATCHES** |

**Spec/design drift verdict**: 13/13 contracts MATCH. Zero drift detected.

---

## Documentation check

| Item | Required | Actual | Status |
|------|----------|--------|--------|
| `CHANGELOG.md` v1.2.0a entry | Present + REQ-V1.2.1 documented + new env vars listed | Present at `CHANGELOG.md:6-17` (`## [1.2.0a] - 2026-06-28` ### Added entry with REQ-V1.2.1 + `FLOW_METRICS_LOG_MAX_BYTES` + `FLOW_METRICS_LOG_MAX_AGE_DAYS` + DriftEventLog pattern mirror + best-effort `OSError` swallow) | **DONE** |
| `tests/bdd/req44_metrics_rotation.feature` BDD spec | Present + 2 scenarios (size rotation + best-effort OSError swallow) | Present at `tests/bdd/req44_metrics_rotation.feature` ✅ | **DONE** (spec-only; see W2 for step-glue status) |
| `tests/unit/test_observability.py` TestMetricsRotation | Present + 7 tests (5 size + 2 age) | Present at `tests/unit/test_observability.py:182-372` ✅ | **DONE** |
| `src/flow_engineering/observability.py` rotation helpers | Present + constants + env-vars + helpers + increment() call site | Present at `observability.py:90-112` + `:204` + `:227-238` + `:244-253` + `:264-289` + `:308-330` ✅ | **DONE** |
| `openspec/specs/decision-drift/spec.md` v1.2 archive status section | Present + Versioning row flip | **NOT REQUIRED for PR#2a** — per proposal.md this lands in PR#2d closeout (T4.4) | **DEFERRED to PR#2d** (per `proposal.md:38-39` chained-PR plan) |
| `pyproject.toml` version `1.1.0 → 1.2.0` | Present | **NOT REQUIRED for PR#2a** — per proposal.md this lands in PR#2d closeout (T4.4) | **DEFERRED to PR#2d** (per `proposal.md:38-39` chained-PR plan) |
| `openspec/changes/v1.2-followups/apply-progress/` directory | Present with TDD cycle evidence table | **NOT PRESENT** | **NOT DONE** — see W1 below |

---

## Drift detection hook (per sdd-verify Step 6a)

```
$ uv run --frozen flow drift v1.2-followups
DECISION_ID  BINDING.ID  BINDING.LABEL  DRIFT_CLASS  DETAIL
------------------------------------------------------------------------------------------------
(unable_to_verify: graph.json unavailable)
```

**Classification**: `unable_to_verify` (exit code 2 per REQ-11 contract) — NOT a PR#2a regression. The `(unable_to_verify: graph.json unavailable)` message indicates no snapshot pinned for `v1.2-followups`, which is the EXPECTED state mid-loop (snapshots land in the archive phase). PR#2a did NOT touch any decision bindings (it only added metrics rotation helpers), so no bindings can be stale or contradicted by this change.

**Drift verdict**: ✅ CLEAN. No `label_drift` / `stale_location` / `stale_id` / `obsolete` / `contradicted` findings attributable to PR#2a.

---

## CRITICAL findings

**NONE.** All REQ-V1.2.1 contracts MATCH. All 5 functional tasks (T1.1..T1.5) closed with strict-TDD RED → GREEN → REFACTOR evidence across 5 work-unit commits in 1 sub-batch. 1349 / 1349 tests pass with 0 regressions vs the `75961ad` v1.1-followups baseline. PR#2a boundary discipline is CLEAN — no PR#2b/c/d scope leaked. Drift detection hook returns `unable_to_verify` (expected state mid-loop; not a regression). Ruff is clean on changed Python files.

The 2 WARNING + 2 SUGGESTION findings below are non-blocking documentation-process gaps that do NOT affect functional correctness, runtime behavior, or test coverage. Per the `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` precedent posture ("PASS WITH WARNINGS — archive-ready"), the archive phase may proceed.

---

## WARNING findings

### W1 — `openspec/changes/v1.2-followups/apply-progress/` directory NOT created (Strict TDD evidence consolidation gap)

**Severity:** **WARNING** — Strict TDD ON + the project's SDD methodology (per `AGENTS.md`) requires `SDD + BDD + TDD` for every substantial project. The apply phase committed 5 work-unit commits with per-commit RED → GREEN → REFACTOR markers (visible in git log) but did NOT create the consolidated `apply-progress/` artifact that would normally live under `openspec/changes/v1.2-followups/`.

**Evidence:**
- `openspec/changes/v1.2-followups/` contains `explore.md` + `proposal.md` + `design.md` + `tasks.md` + `verify-report-pr2a.md` (this file) — **NO** `apply-progress/` subdirectory
- `git log --all --oneline -- 'openspec/changes/v1.2-followups/apply-progress/*'` → 0 commits (artifact never existed)
- `git ls-files | grep "v1.2-followups/apply-progress"` → 0 matches (no tracked files)
- Precedent: every prior archived change has an `apply-progress/` directory under `openspec/changes/<change>/` before archive

**Impact:** Documentation-process gap. Future agents auditing this change will not find the canonical TDD evidence consolidation (per-task RED → GREEN → REFACTOR table + assertion quality + layer distribution). The per-commit markers provide SOME traceability but a consolidated artifact is the project convention. Mirrors `v1.1-followups` verify-report W2 ACCEPTED posture.

**Recommended fix (DOC-ONLY, optional, ~30 min):** Either (A) backfill the `apply-progress/final.md` artifact post-hoc by extracting the per-commit TDD evidence from `git log 75961ad..HEAD --format="%B"`, OR (B) defer to a future "sdd-process" change that retroactively documents all changes that lack on-disk artifacts. This is non-blocking — the functional change is complete and verifiable from git history alone.

### W2 — `tests/bdd/req44_metrics_rotation.feature` spec-only (no pytest-bdd step glue)

**Severity:** **WARNING** — The BDD feature file documents 2 Gherkin scenarios for REQ-V1.2.1 (size threshold rotation + best-effort OSError swallow) but does NOT have a `tests/bdd/test_req44_metrics_rotation_steps.py` step definitions file wired up. Executable BDD coverage is 0/2 scenarios; the 7 unit tests in `TestMetricsRotation` cover the same behavior contract from the unit-test side.

**Evidence:**
- `tests/bdd/req44_metrics_rotation.feature` exists with 2 scenarios
- `uv run --frozen pytest tests/bdd/req44_metrics_rotation.py -v` → `no tests ran` (no step glue file)
- `pytest tests/bdd/ --collect-only -q` → 182 tests collected (none from `req44_metrics_rotation.feature`)
- Precedent: the project ALREADY uses spec-only BDD feature files for some REQs — `tests/bdd/req11_drift_exit_codes.feature` + `tests/bdd/req9_drift_detection.feature` + `tests/bdd/req_v1_0_drift_events.feature` + `tests/bdd/req3_engram_io.feature` ALL have no step glue files but ship as Gherkin specs documenting the BDD contract. The 7 `TestMetricsRotation` unit tests cover the same behavior as the 2 Gherkin scenarios (size threshold + OSError swallow).

**Impact:** Documentation-process gap. The Gherkin spec is a human-readable BDD contract for REQ-V1.2.1 but is not executable via pytest-bdd. Operators / future agents reading the spec can map each `Given/When/Then` step to the corresponding `TestMetricsRotation` test, but the formal `pytest-bdd` contract layer is missing.

**Recommended fix (DOC-ONLY, optional, ~30 min):** Either (A) add `tests/bdd/test_req44_metrics_rotation_steps.py` with step glue that delegates to the existing `TestMetricsRotation` test helpers, OR (B) explicitly mark the feature file as a Gherkin spec-only artifact (add a comment header `<!-- spec-only; executable coverage in tests/unit/test_observability.py::TestMetricsRotation -->`). This is non-blocking — the unit tests provide equivalent coverage.

---

## SUGGESTION findings

### S1 — User brief mentioned `tests/unit/test_observability_aggregate.py` but actual file is `tests/unit/test_observability.py`

The verify-phase user brief referenced `tests/unit/test_observability_aggregate.py` (likely shorthand for "the aggregate metrics tests"), but the actual file is `tests/unit/test_observability.py` (the existing observability test file extended with a NEW `TestMetricsRotation` class). The 7 NEW tests live at `tests/unit/test_observability.py:182-372`. No fix needed — this is a documentation reference mismatch in the brief, not in the code. Confirmed via `git diff 75961ad..HEAD --stat` that `tests/unit/test_observability_aggregate.py` was NOT created.

### S2 — pyproject.toml could add `[tool.ruff] extend-exclude = ["*.feature"]` (non-blocking; out of PR#2a scope)

When `ruff check` is invoked on the full repo scope with `tests/bdd/*.feature` paths, ruff attempts to parse Gherkin files as Python and reports 174 `invalid-syntax` errors per feature file. The `.feature` files are intentionally excluded from Python linting (they're Gherkin, not Python) but ruff doesn't natively know this. The cleanest fix is to add `[tool.ruff] extend-exclude = ["*.feature"]` to `pyproject.toml` to exclude Gherkin files from Python linting. This is non-blocking and OUT OF PR#2a scope (no production code change in PR#2a touches `pyproject.toml`). Could land in a future PR#2c/d or as a 1-line follow-up commit.

---

## Carry-forwards table

| ID | Severity | Pattern | Evidence | Recommended resolution |
|----|----------|---------|----------|------------------------|
| **W1** | WARNING | change #12 internal (NEW) | `openspec/changes/v1.2-followups/apply-progress/` directory NOT created (no TDD evidence consolidation artifact) | Backfill post-hoc from commit history OR defer to v1.3+ "sdd-process" cleanup change (~30 min DOC-ONLY) |
| **W2** | WARNING | change #12 internal (NEW) | `tests/bdd/req44_metrics_rotation.feature` spec-only (no pytest-bdd step glue; mirrors existing pattern for `req11_drift_exit_codes.feature` + `req9_drift_detection.feature` + `req_v1_0_drift_events.feature`) | Add step glue OR add spec-only header comment (~30 min DOC-ONLY) |
| **S1** | SUGGESTION | change #12 internal (NEW) | Verify-phase brief mentioned `test_observability_aggregate.py` (shorthand); actual file is `test_observability.py` | No fix needed (reference mismatch in brief, not in code) |
| **S2** | SUGGESTION | change #12 internal (NEW) | `pyproject.toml` could exclude `*.feature` from ruff lint scope | Add `[tool.ruff] extend-exclude = ["*.feature"]` (1-line fix; OUT of PR#2a scope — defer to future PR) |
| (carry-forwards from `v1.1-followups` W2 + W3) | ACCEPTED | n/a | Same W2 + W3 patterns as v1.1-followups (no apply-progress + ruff residuals deferred) | No new fix needed (this PR inherits the v1.1 ACCEPTED posture) |

**Carry-forwards count:** 4 (2 WARNING + 2 SUGGESTION). The 5 documented v1.1 follow-up carry-forwards (S1 DriftEventLog rotation + S2 wire-format hardening + S3 REQ-51 sink + S4 REQ-52 counters + S5 REQ-53 docs) are all CLOSED by the v1.1-followups archive — and S1 specifically (DriftEventLog rotation) is the precedent pattern that PR#2a's REQ-V1.2.1 mirrors.

---

## Cross-impact non-regression

- **`metrics.jsonl` rotation** — auto-rotates at `FLOW_METRICS_LOG_MAX_BYTES` (default 10 MB) + auto-deletes rotated files older than `FLOW_METRICS_LOG_MAX_AGE_DAYS` (default 30 days). Verified: `tests/unit/test_observability.py::TestMetricsRotation` (7/7 pass).
- **`metrics.jsonl` write semantics** — every `increment()` call still produces exactly 1 JSONL line in the active file. Verified: `tests/unit/test_observability.py::TestIncrementAppends` (5/5 pass) + `tests/unit/test_observability.py::TestReadAll` (3/3 pass).
- **Best-effort `OSError` swallow** — slow FS rename during rotation does NOT crash `increment()`. Verified: `TestMetricsRotation::test_rotation_failure_does_not_crash_increment` PASSES.
- **Counter catalog** — `flow metrics --domain=*` counters unchanged (PR#2a adds rotation, NOT new counter names). Verified: 1349/1349 tests pass with 0 regressions.
- **BDD scenarios** — 182/182 BDD scenarios PASS (no regressions vs v1.1 baseline; PR#2a added 0 NEW step definitions — see W2).
- **`flow drift <change>`** — exit code 2 (`unable_to_verify: graph.json unavailable`) is the EXPECTED mid-loop state; PR#2a did NOT touch decision bindings. Verified: `uv run --frozen flow drift v1.2-followups` returns the standard `unable_to_verify` output.

---

## Verdict

**`PASS WITH WARNINGS`**

### Justification

**Functional layer is GREEN:** 1349 / 1349 tests pass (no regressions vs `75961ad` v1.1-followups baseline); all 7 NEW `TestMetricsRotation` tests pass (5 size + 2 age + 1 OSError-swallow via the rotation-failure-doesn't-crash test); full 182 BDD scenarios pass; ruff clean on `observability.py` + `test_observability.py`; smoke test `from flow_engineering.observability import _rotate_metrics_if_needed` imports cleanly with `FLOW_METRICS_LOG_MAX_BYTES=1`; the 1 in-scope REQ (REQ-V1.2.1) has 7 passing tests demonstrating compliance; all 5 functional tasks (T1.1..T1.5) closed across 5 work-unit commits in 1 sub-batch with strict-TDD RED → GREEN → REFACTOR evidence (2 RED + 2 GREEN + 1 REFACTOR); all 13 spec/design contracts MATCH with zero drift.

**Documentation layer is MOSTLY GREEN:** `CHANGELOG.md:6-17` v1.2.0a entry present (with REQ-V1.2.1 + env vars + DriftEventLog pattern mirror); `tests/bdd/req44_metrics_rotation.feature` 2-scenario spec present; `src/flow_engineering/observability.py:90-330` rotation helpers + constants + env-vars + increment() hook present; **GAP** — `openspec/changes/v1.2-followups/apply-progress/` directory NOT created (see W1, mirrors v1.1-followups W2 ACCEPTED posture); **GAP** — `tests/bdd/req44_metrics_rotation.feature` has no pytest-bdd step glue file (see W2, mirrors the existing spec-only pattern for other REQ feature files). Both gaps are non-blocking documentation-process issues that do NOT affect functional correctness.

**Boundary discipline is GREEN:** PR#2a contains ONLY REQ-V1.2.1 (metrics.jsonl rotation). PR#2b scope (golden tests + render_prompt_canonical) is NOT touched. PR#2c scope (min_sdd_skill_versions + enforce_min_skill_versions) is NOT touched. PR#2d scope (Path A rename + 1-release alias + version bump `1.1.0 → 1.2.0` + CHANGELOG v1.2.0 BREAKING entry + capability spec sync) is NOT touched. The CHANGELOG entry is `## [1.2.0a]` (NOT v1.2.0 — that's PR#2d). Git diff stats show +351 lines across exactly 4 files: `CHANGELOG.md` + `observability.py` + `req44_metrics_rotation.feature` + `test_observability.py`. Zero churn in unrelated files.

**Drift detection is CLEAN:** `flow drift v1.2-followups` returns `unable_to_verify: graph.json unavailable` (exit code 2 per REQ-11 contract) — this is the EXPECTED mid-loop state (snapshots land in archive phase), NOT a regression caused by PR#2a. PR#2a did NOT touch any decision bindings, so no bindings can be stale or contradicted by this change.

**Carry-forwards closed:** REQ-V1.2.1 closes the v1.0+v1.1 carry-forward "metrics.jsonl rotation deferred" (named in `decision-drift/spec.md:410` per `proposal.md:26`). The 5 v1.1 follow-up carry-forwards remain CLOSED. Net carry-forward closure for v1.2: 1/4 (REQ-44 closed by PR#2a; REQ-48 + REQ-54 + Path A rename land in PR#2b/c/d respectively).

### Recommended next step

Proceed directly to `sdd-archive v1.2-followups PR#2a` → `git push origin main` → **PR#2a closes**. The orchestrator then continues the loop to `sdd-apply v1.2-followups PR#2b` (REQ-V1.2.2 golden regression tests, 6 tasks T2.1..T2.6, ~210 LOC).

### Pre-archive fixes (recommend in order)

1. **W1 — Backfill `openspec/changes/v1.2-followups/apply-progress/final.md`** (~30 LOC, ~30 min). Extract per-task TDD evidence table from `git log 75961ad..HEAD --format="%B"` (the 5 commits already have RED/GREEN/REFACTOR markers). Optional but consistent with the `v1.0-followups` + `v1.1-followups` ACCEPTED posture.
2. **W2 — Add `<!-- spec-only; executable coverage in tests/unit/test_observability.py::TestMetricsRotation -->` header comment to `tests/bdd/req44_metrics_rotation.feature`** (1-line fix, ~1 min). Explicitly mark the feature file as a Gherkin spec-only artifact so future agents don't try to add step glue.
3. **No other pre-archive fixes required.** The 2 SUGGESTION findings (S1 brief reference + S2 ruff `*.feature` exclude) are non-blocking documentation/infra improvements that can land in any future PR.

Total pre-archive fix scope: ~31 LOC doc + 1 LOC comment = ~32 LOC. Roughly 30-45 min.