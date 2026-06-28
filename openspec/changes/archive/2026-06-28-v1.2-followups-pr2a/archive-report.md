# Archive Report — v1.2-followups PR#2a (v1.2.0a)

## Status

**ARCHIVED — PR#2a (v1.2.0a) of v1.2-followups CLOSED** (2026-06-28)

SDD cycle complete for PR#2a (sub-batch A only): explore → propose → design → tasks → apply (5 work-unit commits with strict-TDD RED → GREEN → REFACTOR evidence) → verify (PASS WITH WARNINGS, **0 CRITICAL + 2 WARNING + 2 SUGGESTION — accepted per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` precedent**) → **archive**.

**Verdict at archive**: **PASS WITH WARNINGS — archive-ready**. PR#2a is 1 of 4 chained PRs in the v1.2 release (stacked-to-main strategy per `proposal.md`); only `verify-report-pr2a.md` (PR#2a-specific) moves to the archive. The planning artifacts (`explore.md` + `proposal.md` + `design.md` + `tasks.md`) **stay in `openspec/changes/v1.2-followups/`** for chained-PR continuity (PR#2b/c/d reference them as inputs). Each subsequent PR creates its own `verify-report-pr<N>.md` and moves that to the archive on its own closeout cycle.

## Goal

Ship PR#2a (v1.2.0a) — the first of 4 chained PRs in the v1.2 debt-closure release. PR#2a closes REQ-44 `metrics.jsonl` rotation (the only carry-forward from `decision-drift/spec.md:410` that lands in PR#2a). Per `verify-report-pr2a.md` line 5 commitment: ship `_rotate_metrics_if_needed(path)` + `FLOW_METRICS_LOG_MAX_BYTES` (default 10 MB = 10485760) + `FLOW_METRICS_LOG_MAX_AGE_DAYS` (default 30 days) env vars + best-effort `try/except OSError` swallow + age-based sibling cleanup via `_delete_stale_metrics_siblings()` extracted helper. Mirrors `drift_event_log.py:196-254` rotation pattern verbatim. CHANGELOG `## [1.2.0a]` entry (NOT v1.2.0 — that's PR#2d BREAKING scope).

## Summary

Single PR, sub-batch A only, 5 work-unit commits on `main` (HEAD `20f5ed1` ahead of `75961ad` v1.1.0 baseline by 5 commits). Net test count **+7** (1342 → 1349); 0 regressions. REQ-V1.2.1 `metrics.jsonl` rotation SHIPPED — the exact mirror of v1.1.0 `DriftEventLog` rotation (`drift_event_log.py:196-254`) adapted for the metrics sink:

- `_rotate_metrics_if_needed(path)` at `src/flow_engineering/observability.py:308-330` — 23 LOC rotation helper
- `_delete_stale_metrics_siblings(path, max_age_days)` at `src/flow_engineering/observability.py:264-289` — 26 LOC extracted helper (T1.4 REFACTOR for testability)
- Constants: `METRICS_ROTATE_BYTES_DEFAULT = 10 * 1024 * 1024` (10 MB) at `observability.py:93` + `METRICS_ROTATE_AGE_DAYS_DEFAULT = 30` at `observability.py:101`
- Env vars: `METRICS_LOG_MAX_BYTES_ENV = "FLOW_METRICS_LOG_MAX_BYTES"` + `METRICS_LOG_MAX_AGE_DAYS_ENV = "FLOW_METRICS_LOG_MAX_AGE_DAYS"` at `observability.py:108-111`
- Resolvers: `_resolve_metrics_rotation_threshold_bytes()` at `:227-238` + `_resolve_metrics_max_age_days()` at `:244-253` (env-var lookup with `0 = disabled` semantics per DriftEventLog mirror)
- Increment integration: `_rotate_metrics_if_needed(_resolve_path())` called at top of `increment()` at `:204` — **BEFORE** the existing `try/except OSError` block per D1 design (slow FS rotation cannot poison sink path resolution); helper uses own `try/except OSError` swallow on rename + sibling unlink

**7 NEW v1.2 tests** in `tests/unit/test_observability.py::TestMetricsRotation` at `:182-372`:

1. `test_rotates_metrics_when_size_exceeds_threshold` (size above 10 MB → rotation triggers)
2. `test_no_rotation_when_below_threshold` (default 10 MB → 100 increments, no rotation)
3. `test_rotation_respects_env_override_zero_disables` (`FLOW_METRICS_LOG_MAX_BYTES=0` → rotation disabled even with > 10 MB data)
4. `test_rotation_uses_isolated_tmp_path` (no parent traversal on rotation rename)
5. `test_rotation_failure_does_not_crash_increment` (monkeypatch `Path.rename` to raise `OSError` → `increment()` returns None, no crash)
6. `test_deletes_rotated_siblings_older_than_max_age_days` (sibling files with old mtime get deleted, recent ones preserved)
7. `test_age_cleanup_skips_when_max_age_days_is_zero` (`FLOW_METRICS_LOG_MAX_AGE_DAYS=0` → cleanup disabled)

**CHANGELOG**: `## [1.2.0a] - 2026-06-28` entry at `CHANGELOG.md:6-17` documenting REQ-V1.2.1 + new env vars + DriftEventLog pattern mirror + best-effort `OSError` swallow. NOTE: version label is `1.2.0a` (pre-release marker) NOT `1.2.0` — v1.2.0 is the BREAKING release that ships in PR#2d (Path A rename).

**Strict TDD discipline held across 5 per-task cycles in 1 sub-batch:**

## Sub-batch summary

| Sub-batch | REQs | Tasks | Commits | Headline |
|-----------|------|-------|---------|----------|
| **A — `metrics.jsonl` rotation** | REQ-V1.2.1 | T1.1..T1.5 (5 tasks) | 5 (`cd4a2c0` RED, `a8b3de8` GREEN, `4fa220e` RED, `fe23885` GREEN, `20f5ed1` REFACTOR) | `_rotate_metrics_if_needed()` + 2 env vars (default 10 MB + 30 days) + `_delete_stale_metrics_siblings()` helper + best-effort `OSError` swallow + `increment()` integration at `:204` (BEFORE existing try block); 7 RED→GREEN tests in `tests/unit/test_observability.py::TestMetricsRotation`; CHANGELOG `## [1.2.0a]` entry |

**Total**: 1 sub-batch × 5 commits = **5 work-unit commits** (2 RED + 2 GREEN + 1 REFACTOR; matches `verify-report-pr2a.md` lines 53-57 task closure matrix). HEAD `20f5ed1` ahead of `75961ad` by 5 commits; ready for `git push origin main`.

## Per-task completion (T1.1..T1.5 = 5 functional tasks)

### Sub-batch A — `metrics.jsonl` rotation (T1.1..T1.5)
- **T1.1** RED: 5 TestMetricsRotation tests (size threshold) — commit `cd4a2c0` (RED fixture: +193 LOC in `tests/unit/test_observability.py::TestMetricsRotation` — 5 size-based tests added as sole file change; rotation helper does NOT exist yet → tests fail)
- **T1.2** GREEN: `_rotate_metrics_if_needed` + env vars — commit `a8b3de8` (GREEN — `observability.py:90-112` 23 LOC constants/env-vars + `observability.py:223-256` 34 LOC rotation helper + `observability.py:204` rotation call at top of `increment()` BEFORE existing try block; 5/5 T1.1 tests PASS)
- **T1.3** RED: 2 age-based cleanup tests (triangulation) — commit `4fa220e` (RED fixture: +87 LOC in `tests/unit/test_observability.py::TestMetricsRotation` — 2 age-based tests added as sole file change)
- **T1.4** GREEN: age-based sibling cleanup + extract `_delete_stale_metrics_siblings` helper — commit `fe23885` (GREEN — `observability.py:264-289` `_delete_stale_metrics_siblings()` extracted helper for testability; `_rotate_metrics_if_needed()` delegates to it; 7/7 TestMetricsRotation tests PASS)
- **T1.5** REFACTOR: docstring cross-ref + CHANGELOG v1.2.0a entry — commit `20f5ed1` (REFACTOR — docstring on `_rotate_metrics_if_needed()` cross-references `drift_event_log.py:220-254` precedent + `CHANGELOG.md:6-17` `## [1.2.0a] - 2026-06-28` ### Added entry documenting REQ-V1.2.1 + the 2 new env vars + the DriftEventLog pattern mirror + best-effort `OSError` swallow; 7/7 tests PASS + ruff clean on `observability.py`)

**Task closure: 5/5 functional tasks DONE** (T1.1..T1.5) across 5 work-unit commits on `main` (HEAD `20f5ed1` ahead of `75961ad` v1.1.0 baseline by 5 commits; ready for `git push origin main`).

**Commit log (`75961ad..HEAD`):**
```
20f5ed1 refactor(v1.2-followups): REQ-V1.2.1 T1.5 - docstring cross-ref + CHANGELOG v1.2.0a entry
fe23885 refactor(v1.2-followups): REQ-V1.2.1 T1.4 GREEN - extract _delete_stale_metrics_siblings helper for testability
4fa220e feat(v1.2-followups): REQ-V1.2.1 T1.3 RED - age-based sibling cleanup 2 tests (triangulation)
a8b3de8 feat(v1.2-followups): REQ-V1.2.1 T1.4 GREEN - _rotate_metrics_if_needed + FLOW_METRICS_LOG_MAX_BYTES (mirror drift_event_log.py:196-254)
cd4a2c0 feat(v1.2-followups): REQ-V1.2.1 T1.1 RED - TestMetricsRotation 5 tests (size threshold)
```

## Test count delta

| Stage | Count | Delta vs baseline | Notes |
|-------|-------|-------------------|-------|
| Pre-apply baseline (`75961ad`, post-`v1.1-followups` archive) | **1342 / 1342 passing** | — | v1.1.0 archive baseline |
| T1.1 close (post-RED `cd4a2c0`) | 1342 passing | **+0** | 5 RED fixtures added → tests fail (rotation helper does not exist yet); RED committed before GREEN |
| T1.2 close (post-GREEN `a8b3de8`) | 1347 passing | **+5** | 5 NEW RED→GREEN tests in `tests/unit/test_observability.py::TestMetricsRotation` (size threshold) |
| T1.3 close (post-RED `4fa220e`) | 1347 passing | **+0** | 2 age-based RED fixtures added; tests fail (helper has size-only stub) |
| T1.4 close (post-GREEN `fe23885`) | 1349 passing | **+2** | 2 NEW RED→GREEN age cleanup tests pass via `_delete_stale_metrics_siblings()` extracted helper |
| T1.5 close (post-REFACTOR `20f5ed1`) | **1349 / 1349 passing** | **+0** | REFACTOR commit: docstring cross-ref + CHANGELOG v1.2.0a entry; no behavior change; 7/7 TestMetricsRotation tests still PASS + ruff clean on `observability.py` |
| **Net change** | **1342 → 1349 = NET +7** | **+7** | Matches `verify-report-pr2a.md` line 10 claim; +7 RED→GREEN tests, 0 regressions, 0 test removals |

**BDD scenarios**: **182 / 182 passing** (unchanged from v1.1.0 baseline; 0 NEW pytest-bdd step glue — 2 NEW spec-only scenarios in `tests/bdd/req44_metrics_rotation.feature` document the REQ-V1.2.1 BDD contract but are not executable via pytest-bdd per W2).

**Mypy**: not run individually on `observability.py` (no project-wide mypy config; v1.1-followups verify-report precedent did not run mypy on `observability.py` either).

**Ruff**: **0 errors** on changed files (`src/flow_engineering/observability.py` + `tests/unit/test_observability.py`); verified with `ruff check` per `verify-report-pr2a.md` lines 30-31.

## Files touched (cumulative, deduped — PR#2a scope only)

### Production code
- `src/flow_engineering/observability.py` — MODIFIED (sub-batch A, T1.2 + T1.4 + T1.5): rotation section at lines 90-112 (constants + env-var names) + `:204` (rotation call at top of `increment()` BEFORE existing try block) + `:227-238` (`_resolve_metrics_rotation_threshold_bytes`) + `:244-253` (`_resolve_metrics_max_age_days`) + `:264-289` (`_delete_stale_metrics_siblings` extracted helper) + `:308-330` (`_rotate_metrics_if_needed`). Net: ~+122 prod LOC.

### Tests (NEW + MODIFIED)
- `tests/unit/test_observability.py` — MODIFIED (sub-batch A, T1.1 + T1.3): NEW `TestMetricsRotation` class at lines 182-372 with 7 RED→GREEN tests (5 size-threshold from T1.1 + 2 age-cleanup from T1.3). Net: ~+193 test LOC.

### BDD spec (NEW — spec-only, no step glue per W2)
- `tests/bdd/req44_metrics_rotation.feature` — NEW (sub-batch A, T1.1): 2 Gherkin scenarios documenting the REQ-V1.2.1 BDD contract (size threshold rotation + best-effort OSError swallow). Spec-only artifact — executable coverage lives in `tests/unit/test_observability.py::TestMetricsRotation`. Net: +24 BDD spec LOC.

### Build/release
- `CHANGELOG.md` — MODIFIED (sub-batch A, T1.5 REFACTOR): `## [1.2.0a] - 2026-06-28` ### Added entry at lines 6-17 documenting REQ-V1.2.1 + `FLOW_METRICS_LOG_MAX_BYTES` env var (default 10 MB = 10485760) + `FLOW_METRICS_LOG_MAX_AGE_DAYS` env var (default 30 days) + DriftEventLog pattern mirror (`drift_event_log.py:196-254`) + best-effort `try/except OSError` swallow. NOTE: version label is `1.2.0a` (pre-release marker), NOT v1.2.0 (PR#2d BREAKING scope). Net: +12 CHANGELOG LOC.

### Archive (this report)
- `openspec/changes/archive/2026-06-28-v1.2-followups-pr2a/` — archive of 2 artifacts:
  - `verify-report-pr2a.md` (334 LOC — verify-agent output; moved from `openspec/changes/v1.2-followups/`)
  - `archive-report.md` (THIS FILE)
  - **Note**: Planning artifacts (`explore.md` + `proposal.md` + `design.md` + `tasks.md`) STAYED in `openspec/changes/v1.2-followups/` per the chained-PR strategy — they cover all 4 chained PRs (PR#2b/c/d reference them as inputs).

### Files NOT touched (PR#2b/c/d scope — boundary discipline)
- `tests/golden/prompts/*.txt` (4 snapshot files) — **NO** (PR#2b scope)
- `src/flow_engineering/prompt_registry.py` (`render_prompt_canonical`) — **NO** (PR#2b scope)
- `tests/unit/test_prompt_render_golden.py` — **NO** (PR#2b scope)
- `pyproject.toml` `[tool.flow_engineering] min_sdd_skill_versions` — **NO** (PR#2c scope)
- `src/flow_engineering/opencode_skill_catalog.py` `enforce_min_skill_versions` — **NO** (PR#2c scope)
- `src/flow_engineering/cli.py` Path A rename + 1-release alias — **NO** (PR#2d scope)
- `pyproject.toml` version `1.1.0 → 1.2.0` — **NO** (PR#2d closeout)
- `CHANGELOG.md` `## [1.2.0]` BREAKING entry — **NO** (PR#2d closeout)

**Boundary discipline verdict**: ✅ CLEAN. PR#2a contains ONLY REQ-V1.2.1 (metrics.jsonl rotation). Git diff `75961ad..HEAD --stat` shows **+351 lines across 4 files**: `CHANGELOG.md` (+12) + `src/flow_engineering/observability.py` (+122) + `tests/bdd/req44_metrics_rotation.feature` (+24) + `tests/unit/test_observability.py` (+193). Zero churn in unrelated files.

## Verify verdict

**`PASS WITH WARNINGS — archive-ready`** (accepted per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` precedent; same posture: 0C + 2W + 2S → archive; non-blocking follow-ups documented in Carry-forwards table + v1.2 Versioning entry).

| Severity | Count | Details |
|----------|-------|---------|
| **CRITICAL** | **0** | All 1 REQ (REQ-V1.2.1) has at least one passing test demonstrating compliance (7 tests in `TestMetricsRotation`); all 5 functional tasks (T1.1..T1.5) closed; PR#2a debt-closure release complete for REQ-44 metrics rotation; 1349/1349 tests pass with 0 regressions vs `75961ad` v1.1.0 baseline; all 13 spec/design contracts MATCH with zero drift; PR#2a boundary discipline CLEAN — no PR#2b/c/d scope leaked |
| **WARNING** | **2** | **W1** (doc-process, ACCEPTED) — `openspec/changes/v1.2-followups/apply-progress/` directory NOT created (no consolidated TDD evidence artifact on disk). PR#2a committed 5 work-unit commits with per-commit RED → GREEN → REFACTOR markers visible in git log; no consolidated `apply-progress/final.md` artifact. Mirrors `v1.1-followups` W2 ACCEPTED posture. Backfill option (~30 LOC, ~30 min) deferred to v1.3+ `sdd-process` cleanup change. **W2** (doc-process, ACCEPTED) — `tests/bdd/req44_metrics_rotation.feature` is spec-only (no pytest-bdd step glue). The 2 Gherkin scenarios document the BDD contract but are not executable via pytest-bdd; equivalent executable coverage lives in `tests/unit/test_observability.py::TestMetricsRotation` (7 tests). Mirrors the existing pattern for `req11_drift_exit_codes.feature` + `req9_drift_detection.feature` + `req_v1_0_drift_events.feature` (all spec-only). Add step glue OR add `<!-- spec-only -->` header comment (~1-line fix) deferred. |
| **SUGGESTION** | **2** | **S1** (doc-reference, NO-FIX-NEEDED) — verify-phase user brief referenced `tests/unit/test_observability_aggregate.py` (likely shorthand for "the aggregate metrics tests"), but the actual file is `tests/unit/test_observability.py` (the existing observability test file extended with a NEW `TestMetricsRotation` class). The 7 NEW tests live at `tests/unit/test_observability.py:182-372`. No fix needed — this is a documentation reference mismatch in the brief, not in the code. **S2** (infra, ACCEPTED) — `pyproject.toml` could add `[tool.ruff] extend-exclude = ["*.feature"]` (1-line fix to exclude Gherkin files from ruff Python lint scope). Non-blocking; OUT of PR#2a scope (no production code change in PR#2a touches `pyproject.toml`); defer to future PR#2c/d or as a 1-line follow-up commit. |

**Carry-forwards CLOSED by PR#2a**:
- `v1.0-followups` S1 (REQ-44 `metrics.jsonl` rotation deferred) — **closed via REQ-V1.2.1** (the only carry-forward PR#2a closes; the 5 v1.0-followups S1+S2+S3+S4+S5 were already closed by v1.1.0)

**Carry-forwards remaining in v1.2** (NOT closed by PR#2a — defer to PR#2b/c/d):
- REQ-48 golden regression tests for prompts — **PR#2b** (T2.1..T2.6)
- REQ-54 `min_sdd_skill_versions` gate in pyproject + 3-line CLI hooks — **PR#2c** (T3.1..T3.6)
- Path A subcommand group rename for `flow drift-events` (BREAKING in v1.2.0) — **PR#2d** (T4.1..T4.5)
- Remaining 17 ruff residuals in v1.1-touched files (4 auto-fixable + 10 hidden fixes + 3 intentional KEEP) — **PR#2d closeout** (T4.4)
- W2 on-disk planning-artifact backfill for v1.1-followups — **defer to v1.3+** (separate `sdd-process` cleanup change)

**Net carry-forward closure for v1.2**: **1/4 closed by PR#2a** (REQ-44 metrics rotation ✅). 3/4 v1.2 carry-forwards (REQ-48 + REQ-54 + Path A rename) still pending across PR#2b/c/d.

**Cross-impact non-regression** (per `verify-report-pr2a.md` §"Cross-impact non-regression" lines 297-304):
- `metrics.jsonl` rotation: auto-rotates at `FLOW_METRICS_LOG_MAX_BYTES` (default 10 MB) + auto-deletes rotated files older than `FLOW_METRICS_LOG_MAX_AGE_DAYS` (default 30 days). Verified: 7/7 TestMetricsRotation tests pass.
- `metrics.jsonl` write semantics: every `increment()` call still produces exactly 1 JSONL line in the active file. Verified: 5/5 TestIncrementAppends + 3/3 TestReadAll pre-existing tests pass.
- Best-effort `OSError` swallow: slow FS rename during rotation does NOT crash `increment()`. Verified: `TestMetricsRotation::test_rotation_failure_does_not_crash_increment` PASSES (monkeypatched `Path.rename` raises OSError; `increment()` returns None).
- Counter catalog: `flow metrics --domain=*` counters unchanged (PR#2a adds rotation, NOT new counter names). Verified: 1349/1349 tests pass with 0 regressions.
- BDD scenarios: 182/182 BDD scenarios PASS (no regressions vs v1.1 baseline; PR#2a added 0 NEW step definitions — see W2).
- `flow drift <change>`: exit code 2 (`unable_to_verify: graph.json unavailable`) is the EXPECTED mid-loop state; PR#2a did NOT touch decision bindings.

## Drift detection hook (per sdd-verify Step 6a)

```
$ uv run --frozen flow drift v1.2-followups
DECISION_ID  BINDING.ID  BINDING.LABEL  DRIFT_CLASS  DETAIL
------------------------------------------------------------------------------------------------
(unable_to_verify: graph.json unavailable)
```

**Classification**: `unable_to_verify` (exit code 2 per REQ-11 contract) — NOT a PR#2a regression. The `(unable_to_verify: graph.json unavailable)` message indicates no snapshot pinned for `v1.2-followups`, which is the EXPECTED state mid-loop (snapshots land in the archive phase). PR#2a did NOT touch any decision bindings (it only added metrics rotation helpers), so no bindings can be stale or contradicted by this change.

**Drift verdict**: ✅ CLEAN. No `label_drift` / `stale_location` / `stale_id` / `obsolete` / `contradicted` findings attributable to PR#2a.

## Out-of-scope reminders (carried to v1.2 PR#2b/c/d)

The v1.2 release has 4 chained PRs (stacked-to-main). PR#2a closes 1 of 4 carry-forwards; PR#2b/c/d close the remaining 3 + the version bump + the BREAKING Path A rename. Loop continues after `git push origin main`:

1. **PR#2b (v1.2.0b) — REQ-48 golden regression tests** — 6 tasks (T2.1..T2.6); `render_prompt_canonical()` helper + 4 snapshot files (`tests/golden/prompts/{strict_tdd,auto_suggest_header,auto_suggest_footer,auto_suggest_empty}.txt`) + `--update-goldens` Click flag on `flow prompts show`; ~210 LOC; ~60min wall time. Closes REQ-48 carry-forward.
2. **PR#2c (v1.2.0c) — REQ-54 min_sdd_skill_versions** — 6 tasks (T3.1..T3.6); `enforce_min_skill_versions()` helper at `opencode_skill_catalog.py` + `[tool.flow_engineering] min_sdd_skill_versions` pyproject section + 3-line CLI hooks at `flow apply`/`flow verify`/`flow archive` startup with exit code 4; ~240 LOC; ~70min wall time. Closes REQ-54 carry-forward.
3. **PR#2d (v1.2.0d) — REQ-V1.2.4 Path A rename + REQ-V1.2.5 closeout** — 5 tasks (T4.1..T4.5); `flow drift events {list,tail,stats}` subcommand group + `flow drift-events` 1-release `deprecated=True` Click group alias + `pyproject.toml` `1.1.0 → 1.2.0` version bump + CHANGELOG `## [1.2.0]` BREAKING entry + capability spec sync; ~200 LOC (incl. closeout); ~60min wall time. Closes Path A subcommand rename carry-forward + finalizes v1.2.0 release.

**Out-of-scope (deferred beyond v1.2)**:
- **Path A hard removal** — `flow drift-events` 1-release alias REMOVED in v1.3 (mirrors `SnapshotGraphMissing` v1.1 → v1.2 removal precedent)
- **17 ruff residuals** in v1.1-touched files (per v1.1-followups verify-report W3 ACCEPTED posture)
- **W2 on-disk planning artifacts backfill** for v1.1-followups (per v1.1-followups verify-report W2)
- **`prompt_renders.jsonl` rotation** (third JSONL sink) — defer until `FLOW_PROMPT_LOG` is on-by-default
- **Golden snapshots for inline prompt constants** (legacy aliases — covered via `PROMPT_NAMES`)

## Cleanup verification

- `git status --short` after archive operations: 1 untracked (`??`) for `openspec/changes/v1.2-followups/` (planning artifacts preserved for PR#2b/c/d) + 1 modified (`M`) for `openspec/specs/decision-drift/spec.md` (added `## v1.2.0a archive status (2026-06-28)` section + v1.2.0a SHIPPED Versioning row + updated v1.2 PLANNED entry to mention chained PR#2b/c/d remainder) + 1 modified (`M`) for `uv.lock` (CRLF/LF line-ending swap from git's autocrlf — environmental noise, NOT a functional change; not touched by this archive phase).
- `git log --oneline -5` (PR#2a apply commits): 5 work-unit commits between `75961ad` (pre-apply baseline) and `20f5ed1` (post-REFACTOR closeout).
- `uv run --frozen pytest tests/ --tb=short -q` (per `verify-report-pr2a.md` line 27): 1349 passed, 0 failed, 64.81s, exit 0 (final HEAD `20f5ed1`).
- 1 `Move-Item` operation (untracked `verify-report-pr2a.md` from `openspec/changes/v1.2-followups/` to `openspec/changes/archive/2026-06-28-v1.2-followups-pr2a/`).
- 1 modified capability spec (`openspec/specs/decision-drift/spec.md` — added `## v1.2.0a archive status (2026-06-28)` section + Versioning row flip for v1.2.0a SHIPPED + updated v1.2 PLANNED entry to mention chained PR#2b/c/d remainder).
- 1 created file in archive (this `archive-report.md`).
- Planning artifacts (`explore.md` + `proposal.md` + `design.md` + `tasks.md`) REMAIN in `openspec/changes/v1.2-followups/` for chained-PR continuity (PR#2b/c/d reference them as inputs).

## Relevant Files

### Production code (v1.2.0a debt-closure for REQ-44)
- `src/flow_engineering/observability.py` — MODIFIED (sub-batch A): rotation section at `:90-112` (constants + env-var names) + `:204` (rotation call at top of `increment()`) + `:227-238` (`_resolve_metrics_rotation_threshold_bytes`) + `:244-253` (`_resolve_metrics_max_age_days`) + `:264-289` (`_delete_stale_metrics_siblings` extracted helper) + `:308-330` (`_rotate_metrics_if_needed`) (~+122 prod LOC)

### Tests (NEW + MODIFIED)
- `tests/unit/test_observability.py` — MODIFIED (sub-batch A): NEW `TestMetricsRotation` class at `:182-372` with 7 RED→GREEN tests (~+193 test LOC)
- `tests/bdd/req44_metrics_rotation.feature` — NEW (sub-batch A): 2 spec-only Gherkin scenarios documenting REQ-V1.2.1 BDD contract (+24 BDD spec LOC; spec-only per W2)

### Build/release
- `CHANGELOG.md` — MODIFIED (sub-batch A, T1.5 REFACTOR): `## [1.2.0a] - 2026-06-28` ### Added entry at `:6-17` documenting REQ-V1.2.1 + new env vars + DriftEventLog pattern mirror (+12 CHANGELOG LOC)

### Capability specs (archive sync)
- `openspec/specs/decision-drift/spec.md` — MODIFIED (this archive): v1.2.0a archive status section with REQ-V1.2.1 ✅ SHIPPED table + verified PASS-WITH-WARNINGS verdict + W1/W2 + S1/S2 findings + carry-forwards closed (1/4 v1.2 carry-forwards closed by PR#2a) + carry-forwards NOT closed (REQ-48 + REQ-54 + Path A → PR#2b/c/d) + new `## v1.2.0a` SHIPPED entry in `## Versioning` table + updated v1.2 PLANNED entry to mention chained PR#2b/c/d remainder + v1.1 Versioning row unchanged

### Archive
- `openspec/changes/archive/2026-06-28-v1.2-followups-pr2a/` — archive of 2 artifacts (verify-report-pr2a.md + this archive-report.md) + NOTE on planning artifacts: `explore.md` + `proposal.md` + `design.md` + `tasks.md` STAYED in `openspec/changes/v1.2-followups/` per the chained-PR strategy

## Celebration

**Change #12 v1.2-followups PR#2a (v1.2.0a) is CLOSED. The first of 4 chained PRs in the v1.2 debt-closure release shipped clean.** REQ-44 `metrics.jsonl` rotation is **CLOSED** (the one carry-forward from `v1.0-followups` S1 + `decision-drift/spec.md:410` that PR#2a owns). The rotation pattern mirrors `drift_event_log.py:196-254` verbatim — operators now have a unified rotation + age-cleanup contract across both JSONL sinks (`drift_events.jsonl` + `metrics.jsonl`). 7 RED→GREEN tests in `TestMetricsRotation` exercise every code path (size threshold + below-threshold + env-override disabled + isolated tmp_path + OSError resilience + age cleanup + age cleanup disabled). CHANGELOG `## [1.2.0a]` entry (pre-release marker, NOT v1.2.0 — that's PR#2d BREAKING scope) documents the new env vars + the DriftEventLog pattern mirror + best-effort OSError swallow.

The debt-closure loop ran clean for PR#2a: **0 regressions, 0 lost work, 0 workarounds**. Strict TDD discipline held across 5 per-task cycles in 1 sub-batch (2 RED + 2 GREEN + 1 REFACTOR). The 2 PR#2a non-blocking findings (W1 no apply-progress + W2 spec-only BDD) are accepted per the established `v1.1-followups` precedent. PR#2a boundary discipline is CLEAN — zero PR#2b/c/d scope leaked into the 5 work-unit commits; git diff stats show +351 lines across exactly 4 files.

The next release train: **v1.2.0** ships as 4 chained PRs (`stacked-to-main`). PR#2a (v1.2.0a) is done. After `git push origin main`, the orchestrator continues the loop to **PR#2b (v1.2.0b) — REQ-48 golden regression tests for prompts** (T2.1..T2.6, ~210 LOC, ~60min).

---

**Session**: flow-engineering-v1.2-followups-pr2a-archive-2026-06-28
**SDD Cycle**: COMPLETE for PR#2a (change #12 sub-batch A)
**Verdict**: PASS WITH WARNINGS — archive-ready (0C + 2W accepted + 2S; 1/4 v1.2 carry-forwards closed)
**Capability spec sync**: `openspec/specs/decision-drift/spec.md` updated with `## v1.2.0a archive status (2026-06-28)` section (REQ-V1.2.1 ✅ SHIPPED table + verified PASS-WITH-WARNINGS verdict + W1/W2 + S1/S2 findings + carry-forwards closed REQ-44 by PR#2a + carry-forwards NOT closed REQ-48/REQ-54/Path A → PR#2b/c/d) + `## Versioning` table with v1.2.0a SHIPPED + updated v1.2 PLANNED entry to mention chained PR#2b/c/d remainder; v1.1 Versioning row unchanged
**Next**: orchestrator commits the 1 archive move + 1 capability spec sync + archive-report; pushes to `origin main`; PR#2a closes; loop continues to `v1.2-followups` PR#2b (change #12 sub-batch B)
**Topic**: sdd/v1.2-followups/archive-report-pr2a