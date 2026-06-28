<!-- tasks.md: v1.2-followups. Source: sdd-tasks sub-agent (2026-06-28). Mirrors v1.1-followups per-task TDD format with 4-sub-batch chained-PR shape. -->
# Tasks: v1.2-followups

**Change:** `v1.2-followups` (debt-closure release — closes 4 carry-forwards from `decision-drift/spec.md:410`: REQ-44 metrics.jsonl rotation + REQ-48 golden regression tests + REQ-54 min_sdd_skill_versions + Path A subcommand rename; per `openspec/changes/v1.2-followups/explore.md` + `proposal.md` + `design.md`)
**Builds on:** `proposal.md` — 5 REQs (REQ-V1.2.1..V1.2.5); `design.md` — 4 architecture decisions (D1..D4) + Open Questions all pre-resolved; v1.1 DriftEventLog rotation precedent at `drift_event_log.py:196-254`; v1.1 `SnapshotGraphMissing` 1-release alias precedent at `snapshot_manager.py:104-123`; `scripts/generate_prompts_doc.py` snapshot pattern
**Date:** 2026-06-28
**Status:** EXPLORED + PROPOSED + DESIGNED → ready for `sdd-apply v1.2-followups PR#2a` (sub-batch A)
**Strict TDD:** ON (per AGENTS.md SDD+BDD+TDD mandate + `v1.0-followups` + `v1.1-followups` `apply-progress/merged.md` precedent; RED → GREEN → REFACTOR per task)
**Delivery strategy:** chained (4 PRs, `stacked-to-main` — each PR merges to main, next branches off)

> **REQ-label note**: REQ-V1.2.1 = D1 metrics.jsonl rotation (PR#2a); REQ-V1.2.2 = D2 golden regression tests (PR#2b); REQ-V1.2.3 = D3 min_sdd_skill_versions enforcement (PR#2c); REQ-V1.2.4 = D4 Path A subcommand rename (PR#2d); REQ-V1.2.5 = version bump + capability spec sync (lands in PR#2d closeout).

> **Pre-decided by orchestrator (per `proposal.md` §"Open Questions")**: D1 mirror `drift_event_log.py:196-254` verbatim (10 MB + 30 days); D2 on-disk snapshots + `--update-goldens` flag; D3 pyproject `[tool.flow_engineering]` section + `enforce_min_skill_versions()` helper + 3-line CLI hook (exit code 4); D4 Path A + 1-release `deprecated=True` Click group alias (mirrors `SnapshotGraphMissing` precedent); chain strategy `stacked-to-main`.

---

```yaml
status: success
confidence: high
total_tasks: 22  # T1.1..T1.5 + T2.1..T2.6 + T3.1..T3.6 + T4.1..T4.5
pr_split: 4 chained PRs (stacked-to-main)
forecast_loc_production: ~170  # rotation helpers (40) + render_prompt_canonical (20) + enforce_min_skill_versions (50) + CLI hooks (30) + 1-release alias (30)
forecast_loc_test: ~580  # TestMetricsRotation + TestGoldenRegression + TestGoldenUpdate + TestEnforceMinSkillVersions + alias tests + BDD scenarios
forecast_loc_grand_total: ~750  # + 4 NEW snapshot files (committed artifacts)
sub_batches:
  sub_batch_a: 5 tasks   # T1.1..T1.5   — REQ-V1.2.1 metrics.jsonl rotation
  sub_batch_b: 6 tasks   # T2.1..T2.6   — REQ-V1.2.2 golden regression tests
  sub_batch_c: 6 tasks   # T3.1..T3.6   — REQ-V1.2.3 min_sdd_skill_versions
  sub_batch_d: 5 tasks   # T4.1..T4.5   — REQ-V1.2.4 Path A rename + closeout
review_workload_forecast:
  single_pr_400_line_budget_risk: high  # ~790 LOC exceeds threshold by ~2x
  chained_pr_recommendation: yes  # 4 PRs MANDATORY
  decision_needed_before_apply: no  # auto-chain per orchestrator brief + proposal.md
  chain_strategy: stacked-to-main
strict_tdd: on
bdd_feature_files: 3 NEW  # req44_metrics_rotation.feature + req48_golden_prompts.feature + req54_skill_version_gate.feature
bdd_scenarios: 6 NEW (2 per REQ)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v1.2-followups\tasks.md
next_recommended: sdd-apply v1.2-followups PR#2a (T1.1..T1.5)
```

---

## PR Split

| PR | REQs | Tasks | LOC forecast | Wall time |
|----|------|-------|--------------|-----------|
| **PR#2a** (v1.2.0a) | REQ-V1.2.1 | T1.1..T1.5 (5 tasks) | ~40 prod + ~180 test = ~220 | ~50min |
| **PR#2b** (v1.2.0b) | REQ-V1.2.2 | T2.1..T2.6 (6 tasks) | ~20 prod + ~190 test + 4 snapshots = ~210 | ~60min |
| **PR#2c** (v1.2.0c) | REQ-V1.2.3 | T3.1..T3.6 (6 tasks) | ~80 prod + ~160 test = ~240 | ~70min |
| **PR#2d** (v1.2.0d) | REQ-V1.2.4 + REQ-V1.2.5 (closeout) | T4.1..T4.5 (5 tasks) | ~30 prod + ~50 test + ~40 closeout = ~120 | ~60min |
| **Total** | **5 REQs** | **22 tasks** | **~790** | **~4h** |

4 chained PRs are MANDATORY (per `proposal.md` §"Approach matrix" + `sdd-phase-common.md` Section E). `stacked-to-main` strategy — each PR merges to `main`, then the next PR branches off. Cross-PR dependencies: NONE.

---

## Goal

Break the 5 REQs (REQ-V1.2.1..V1.2.5) into 4 chained PRs with 4 sequential sub-batches of strict per-task TDD. Each PR ≤ ~250 LOC, autonomously verifiable, REQ-aligned. Mirror the `openspec/changes/archive/2026-06-28-v1.1-followups/tasks.md` per-task TDD format (YAML frontmatter + Goal + Instructions + Discoveries + sub-batches + Risks + Acceptance criteria).

## Scope

- **In scope**: REQ-V1.2.1 metrics.jsonl rotation + REQ-V1.2.2 golden regression tests + REQ-V1.2.3 min_sdd_skill_versions enforcement + REQ-V1.2.4 Path A rename + REQ-V1.2.5 version bump + capability spec sync + CHANGELOG v1.2.0 BREAKING entry.
- **Sub-batches**: 4 (one per chained PR) — Sub-batch A (PR#2a REQ-44) + Sub-batch B (PR#2b REQ-48) + Sub-batch C (PR#2c REQ-54) + Sub-batch D (PR#2d Path A + closeout).
- **Total tasks**: 22 functional tasks across 4 sub-batches.
- **BDD scenarios**: 6 NEW across 3 NEW feature files (REQ-44 + REQ-48 + REQ-54).

## Out of Scope (deferred to v1.3+)

- Path A hard removal — `flow drift-events` 1-release alias REMOVED in v1.3 (mirrors `SnapshotGraphMissing` v1.1 → v1.2 removal precedent).
- 17 ruff residuals in v1.1-touched files (per v1.1-followups verify-report W3 ACCEPTED posture).
- W2 on-disk planning artifacts backfill (per v1.1-followups verify-report W2).
- `prompt_renders.jsonl` rotation (third JSONL sink) — defer until `FLOW_PROMPT_LOG` is on-by-default.
- Golden snapshots for inline prompt constants (legacy aliases — covered via `PROMPT_NAMES`).
- `enforce_min_skill_versions` for non-SDD skills (only 8 sdd-* dispatchers need the gate).

## Instructions

- **4 chained PRs per orchestrator brief** — no single-PR; 4 sequential sub-batches of strict per-task TDD.
- **Strict TDD ON** — every public addition has RED → GREEN → REFACTOR history per task.
- **Per-PR LOC budget**: ≤ 250 LOC (enforced via per-PR sub-batch design).
- **Pre-flight pytest**: 1342 tests collected clean ✅ (HEAD `75961ad`).
- **Pyproject version bump** 1.1.0 → 1.2.0 lands in T4.4 (LAST functional task per v0.9.0-hardening + v1.0-followups + v1.1-followups precedent).

## Discoveries

- `drift_event_log.py:196-254` is the verbatim reference for `_rotate_if_needed()` + `_resolve_rotation_threshold_bytes()` + `_resolve_max_age_days()`. Mirrored in T1.2.
- `opencode_skill_catalog.py:117` `SkillVersionError(Exception)` ALREADY EXISTS. Reused as the exception type for the version gate in T3.2 — no new exception hierarchy needed.
- `snapshot_manager.py:104-123` PEP 562 `__getattr__` is the verbatim reference for the 1-release `SnapshotGraphMissing` alias pattern. Mirrored in T4.3 for `flow drift-events` Click group alias.
- `observability.py:171-189` `increment()` already has `try/except OSError` swallow (best-effort sink). T1.2 rotation call sits OUTSIDE that try block so slow rotation cannot poison sink path resolution.
- `prompts/strict_tdd.j2` declares `test_command` as required var (per `prompt_registry.py:188`); the other 3 PROMPT_NAMES entries declare empty var tuples. Canonical defaults for T2.5 snapshots: `test_command="pytest"` for strict_tdd; `{}` for the other 3.
- `pyproject.toml:106-108` already has `[tool.flow_engineering.prompts]` table — no collision with new `[tool.flow_engineering]` umbrella section.
- 1342 tests collect clean at HEAD `75961ad` (verified pre-flight 2026-06-28).
- PowerShell `tail` not available; use `Select-Object -Last 3` for pytest collect-only output (per v1.1-followups discoverie).

---

## Sub-batch A — REQ-V1.2.1 metrics.jsonl rotation (PR#2a, T1.1..T1.5)

### T1.1 — REQ-V1.2.1 RED: TestMetricsRotation 5 tests (size threshold)

- **Type**: Test (RED)
- **Strict TDD**: RED → only adds tests; rotation helper does NOT exist yet, tests must fail
- **Files**: `tests/unit/test_observability.py` (+~100 LOC: NEW `TestMetricsRotation` class with 5 tests)
- **Acceptance**: 5 new tests in `TestMetricsRotation` class:
  1. `test_rotates_metrics_when_size_exceeds_threshold` — monkeypatch `FLOW_METRICS_LOG_MAX_BYTES=1024`; call `increment()` until sink > 1KB; assert `metrics.<ISO>.jsonl` sibling exists + active `metrics.jsonl` is fresh
  2. `test_no_rotation_when_below_threshold` — default 10MB threshold; 100 `increment()` calls; assert only `metrics.jsonl` exists
  3. `test_rotation_respects_env_override` — `FLOW_METRICS_LOG_MAX_BYTES=0`; assert rotation disabled even with 10MB of data (best-effort behavior)
  4. `test_rotation_uses_isolated_tmp_path` — verify rotation helper does NOT write outside `tmp_path` (no parent traversal on rotation rename)
  5. `test_rotation_failure_does_not_crash_increment` — make `path.rename()` raise `OSError` (e.g., target exists + read-only FS); assert `increment()` still returns None (best-effort)
- **Pytest command**: `uv run --frozen pytest tests/unit/test_observability.py::TestMetricsRotation -v`
- **LOC forecast**: ~100 tests + ~0 prod = ~100
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.1 RED — TestMetricsRotation 5 tests (size threshold)`

### T1.2 — REQ-V1.2.1 GREEN: `_rotate_metrics_if_needed` + env vars (mirror drift_event_log.py:196-254)

- **Type**: Implementation (GREEN)
- **Strict TDD**: GREEN → makes T1.1 tests pass
- **Files**: `src/flow_engineering/observability.py` (+~40 LOC: NEW `_rotate_metrics_if_needed(path)` + `_resolve_metrics_rotation_threshold_bytes()` + `_resolve_metrics_max_age_days()` + constants `METRICS_ROTATE_BYTES_DEFAULT=10485760` + `METRICS_ROTATE_AGE_DAYS_DEFAULT=30`; call `_rotate_metrics_if_needed(_resolve_path())` at top of `increment()` BEFORE existing `try/except OSError`)
- **Acceptance**: All 5 TestMetricsRotation tests PASS; full `test_observability.py` suite PASS (1342+ tests); live smoke: `from flow_engineering.observability import _rotate_metrics_if_needed, METRICS_ROTATE_BYTES_DEFAULT` returns `10485760`
- **Pytest command**: `uv run --frozen pytest tests/unit/test_observability.py -v`
- **LOC forecast**: ~40 prod + ~0 tests = ~40 (T1.2 only; T1.1 tests already written)
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.1 GREEN — _rotate_metrics_if_needed + FLOW_METRICS_LOG_MAX_BYTES (mirror drift_event_log.py:196-254)`

### T1.3 — REQ-V1.2.1 RED: TestMetricsRotation age-based cleanup 2 tests

- **Type**: Test (RED)
- **Strict TDD**: RED → only adds tests; helper may have size-only stub, age cleanup does NOT exist
- **Files**: `tests/unit/test_observability.py` (+~50 LOC: 2 NEW tests in `TestMetricsRotation`)
- **Acceptance**: 2 new tests:
  1. `test_deletes_rotated_siblings_older_than_max_age_days` — create 2 sibling files (`metrics.20250601T000000Z.jsonl`, `metrics.20260601T000000Z.jsonl`) with old mtime; monkeypatch `FLOW_METRICS_LOG_MAX_AGE_DAYS=30`; call rotation; assert old sibling deleted + recent sibling preserved
  2. `test_age_cleanup_skips_when_max_age_days_is_zero` — `FLOW_METRICS_LOG_MAX_AGE_DAYS=0`; old siblings preserved (cleanup disabled)
- **Pytest command**: `uv run --frozen pytest tests/unit/test_observability.py::TestMetricsRotation -v`
- **LOC forecast**: ~50 tests + ~0 prod = ~50
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.1 RED — TestMetricsRotation age-based cleanup 2 tests`

### T1.4 — REQ-V1.2.1 GREEN: age-based sibling cleanup

- **Type**: Implementation (GREEN)
- **Strict TDD**: GREEN → makes T1.3 tests pass
- **Files**: `src/flow_engineering/observability.py` (+~10 LOC: extend `_rotate_metrics_if_needed()` to walk `parent.glob("metrics.*.jsonl")` siblings + delete any with mtime < cutoff; best-effort `try/except OSError`)
- **Acceptance**: All 7 TestMetricsRotation tests PASS; full suite 1347+ tests PASS
- **Pytest command**: `uv run --frozen pytest tests/unit/test_observability.py -v`
- **LOC forecast**: ~10 prod + ~0 tests = ~10
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.1 GREEN — age-based sibling cleanup in _rotate_metrics_if_needed`

### T1.5 — REQ-V1.2.1 REFACTOR: docs + naming + best-effort OSError finalization

- **Type**: REFACTOR
- **Strict TDD**: REFACTOR → no behavior change; full suite must remain green
- **Files**: `src/flow_engineering/observability.py` (~0 LOC delta; rename helpers for consistency + add docstring cross-reference to `drift_event_log.py:220-254` precedent); `CHANGELOG.md` (+~5 LOC: `## [1.2.0a] - 2026-06-28` entry documenting REQ-V1.2.1 + new env vars)
- **Acceptance**: All 1347+ tests PASS; `ruff check src/flow_engineering/observability.py` shows 0 findings; docstring on `_rotate_metrics_if_needed()` cross-references `drift_event_log.py:220-254`
- **Pytest command**: `uv run --frozen pytest tests/ --tb=short -q`
- **LOC forecast**: ~5 prod + ~0 tests = ~5
- **Commit message**: `refactor(v1.2-followups): REQ-V1.2.1 T1.5 — docs cross-ref + CHANGELOG v1.2.0a entry`

### Sub-batch A summary

- **Total**: ~205 prod LOC delta + ~150 test LOC delta = ~355 LOC (`observability.py:171-189` + `test_observability.py::TestMetricsRotation` 7 tests)
- **Wait — recalibrate**: T1.1 tests + T1.2 GREEN prod + T1.3 tests + T1.4 GREEN prod + T1.5 REFACTOR ≈ 0+40+0+10+5 prod + 100+0+50+0+0 tests = ~55 prod + ~150 tests = ~205 total
- **Per-PR LOC**: ~205 (well within ≤250 budget)

---

## Sub-batch B — REQ-V1.2.2 golden regression tests (PR#2b, T2.1..T2.6)

### T2.1 — REQ-V1.2.2 RED: TestGoldenRegression 4 tests (snapshot byte-match)

- **Type**: Test (RED)
- **Strict TDD**: RED → only adds tests; helper does NOT exist, snapshots do NOT exist
- **Files**: `tests/unit/test_prompt_render_golden.py` (NEW, +~80 LOC: `TestGoldenRegression` class with 4 tests)
- **Acceptance**: 4 new tests:
  1. `test_strict_tdd_matches_snapshot` — calls `render_prompt_canonical("strict_tdd", test_command="pytest")`; asserts byte-identical to `tests/golden/prompts/strict_tdd.txt`
  2. `test_auto_suggest_header_matches_snapshot` — calls `render_prompt_canonical("auto_suggest_header")`; asserts byte-match to `tests/golden/prompts/auto_suggest_header.txt`
  3. `test_auto_suggest_footer_matches_snapshot` — asserts byte-match
  4. `test_auto_suggest_empty_matches_snapshot` — asserts byte-match
- **Pytest command**: `uv run --frozen pytest tests/unit/test_prompt_render_golden.py::TestGoldenRegression -v`
- **LOC forecast**: ~80 tests + ~0 prod = ~80
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.2 RED — TestGoldenRegression 4 tests (snapshot byte-match)`

### T2.2 — REQ-V1.2.2 GREEN: `render_prompt_canonical()` helper + 4 snapshot files

- **Type**: Implementation (GREEN) + generated artifacts
- **Strict TDD**: GREEN → makes T2.1 tests pass (helper + snapshots co-created in one commit)
- **Files**: `src/flow_engineering/prompt_registry.py` (+~20 LOC: NEW `render_prompt_canonical(prompt_id, **vars)` helper at line 224+ that injects canonical defaults per PROMPT_NAMES entry — `test_command="pytest"` for `strict_tdd`; `{}` for others; delegates to `render_prompt()`); `tests/golden/prompts/strict_tdd.txt` (NEW, ~10 LOC: canonical `render_prompt("strict_tdd", test_command="pytest")` output); `tests/golden/prompts/auto_suggest_{header,footer,empty}.txt` (NEW, ~3 LOC each: empty-var render output)
- **Acceptance**: All 4 TestGoldenRegression tests PASS; live smoke: `from flow_engineering.prompt_registry import render_prompt_canonical` returns non-empty bytes for all 4 PROMPT_NAMES entries; snapshots committed to git
- **Pytest command**: `uv run --frozen pytest tests/unit/test_prompt_render_golden.py -v`
- **LOC forecast**: ~20 prod + 4 snapshot files (~20 total committed) + ~0 tests = ~40
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.2 GREEN — render_prompt_canonical() helper + 4 committed snapshot files`

### T2.3 — REQ-V1.2.2 RED: TestGoldenUpdate 2 tests (`--update-goldens` flag)

- **Type**: Test (RED)
- **Strict TDD**: RED → only adds tests; CLI flag does NOT exist
- **Files**: `tests/unit/test_prompt_render_golden.py` (+~40 LOC: NEW `TestGoldenUpdate` class with 2 tests)
- **Acceptance**: 2 new tests:
  1. `test_update_goldens_flag_regenerates_snapshot` — invoke `flow prompts show strict_tdd --update-goldens` via CliRunner; assert `tests/golden/prompts/strict_tdd.txt` was rewritten + new content matches `render_prompt_canonical("strict_tdd", test_command="pytest")`
  2. `test_default_mode_fails_on_snapshot_drift` — corrupt a snapshot file with garbage bytes; invoke `flow prompts show strict_tdd` (no flag) via CliRunner; assert exit code != 0 + stderr contains "snapshot drift detected"
- **Pytest command**: `uv run --frozen pytest tests/unit/test_prompt_render_golden.py::TestGoldenUpdate -v`
- **LOC forecast**: ~40 tests + ~0 prod = ~40
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.2 RED — TestGoldenUpdate 2 tests (--update-goldens flag)`

### T2.4 — REQ-V1.2.2 GREEN: `--update-goldens` Click flag on `flow prompts show`

- **Type**: Implementation (GREEN)
- **Strict TDD**: GREEN → makes T2.3 tests pass
- **Files**: `src/flow_engineering/cli.py` (+~30 LOC: NEW `@click.option("--update-goldens", is_flag=True, ...)` on `flow prompts show`; when set, overwrite snapshot file via `render_prompt_canonical()` + `Path.write_text()`; default mode emits "snapshot drift detected" stderr + `sys.exit(3)` on byte-mismatch)
- **Acceptance**: Both TestGoldenUpdate tests PASS; full CLI test suite PASS; live: `flow prompts show strict_tdd --update-goldens` rewrites snapshot atomically + prints "snapshot updated: tests/golden/prompts/strict_tdd.txt"
- **Pytest command**: `uv run --frozen pytest tests/unit/test_prompt_render_golden.py tests/unit/test_cli_prompts_show.py -v`
- **LOC forecast**: ~30 prod + ~0 tests = ~30
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.2 GREEN — --update-goldens Click flag on flow prompts show`

### T2.5 — REQ-V1.2.2: verify 4 snapshot files exist and are reproducible

- **Type**: Verification (idempotency check)
- **Files**: `tests/golden/prompts/*.txt` (verification only; no edits)
- **Acceptance**: `for f in tests/golden/prompts/*.txt; do uv run python -c "from pathlib import Path; from flow_engineering.prompt_registry import render_prompt_canonical; import sys; expected=Path('$f').read_text(); ..."; done` produces byte-identical output across 3 consecutive runs; all 4 files committed in git (`git ls-files tests/golden/prompts/`)
- **Pytest command**: `uv run --frozen pytest tests/unit/test_prompt_render_golden.py::TestGoldenRegression -v` (re-run for idempotency confirmation)
- **LOC forecast**: ~0 prod + ~0 tests = ~0 (verification commit)
- **Commit message**: `chore(v1.2-followups): REQ-V1.2.2 T2.5 — verify 4 snapshot files reproducible (idempotency)`

### T2.6 — REQ-V1.2.2 REFACTOR: snapshot test fixture cleanup (conftest.py or local fixture)

- **Type**: REFACTOR
- **Strict TDD**: REFACTOR → no behavior change; tests must remain green
- **Files**: `tests/unit/test_prompt_render_golden.py` (~0 LOC delta; extract `golden_snapshot_dir` fixture pointing to `tests/golden/prompts/`; reuse across `TestGoldenRegression` + `TestGoldenUpdate`); `tests/unit/conftest.py` (+~10 LOC if fixture is project-wide; else inline)
- **Acceptance**: All `test_prompt_render_golden.py` tests PASS; no duplicated `Path("tests/golden/prompts")` literals across test classes
- **Pytest command**: `uv run --frozen pytest tests/unit/test_prompt_render_golden.py -v`
- **LOC forecast**: ~0 prod + ~10 tests = ~10
- **Commit message**: `refactor(v1.2-followups): REQ-V1.2.2 T2.6 — extract golden_snapshot_dir fixture`

### Sub-batch B summary

- **Total**: ~50 prod LOC + 4 snapshot files (~20 committed) + ~130 test LOC = ~200 (close to ~210 forecast)
- **Per-PR LOC**: ~200 (well within ≤250 budget)

---

## Sub-batch C — REQ-V1.2.3 min_sdd_skill_versions (PR#2c, T3.1..T3.6)

### T3.1 — REQ-V1.2.3 RED: TestEnforceMinSkillVersions 5 tests

- **Type**: Test (RED)
- **Strict TDD**: RED → only adds tests; helper does NOT exist
- **Files**: `tests/unit/test_opencode_skill_catalog.py` (+~80 LOC: NEW `TestEnforceMinSkillVersions` class with 5 tests)
- **Acceptance**: 5 new tests:
  1. `test_passes_when_all_skills_meet_minimum` — mock 8 SKILL.md files with `version: "3.0"`; call `enforce_min_skill_versions({"sdd-apply": "3.0", ...})`; returns None (no exception)
  2. `test_raises_skill_version_error_on_downgrade` — mock `sdd-apply` with `version: "2.5"`; call helper with `{"sdd-apply": "3.0"}`; assert `SkillVersionError` raised with message containing "sdd-apply requires >= 3.0, found 2.5"
  3. `test_skips_missing_skill` — `enforce_min_skill_versions({"nonexistent-skill": "3.0"})` returns None (no error)
  4. `test_skips_non_sdd_skill` — `enforce_min_skill_versions({"some-other-tool": "3.0"})` returns None (only sdd-* keys enforced)
  5. `test_handles_non_numeric_version_gracefully` — mock SKILL.md with `version: "3.0-beta"`; call helper; assert either parse succeeds OR `_extract_version` returns "0.0" fallback + gate fires correctly
- **Pytest command**: `uv run --frozen pytest tests/unit/test_opencode_skill_catalog.py::TestEnforceMinSkillVersions -v`
- **LOC forecast**: ~80 tests + ~0 prod = ~80
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.3 RED — TestEnforceMinSkillVersions 5 tests (SkillVersionError + skip rules)`

### T3.2 — REQ-V1.2.3 GREEN: `enforce_min_skill_versions()` helper

- **Type**: Implementation (GREEN)
- **Strict TDD**: GREEN → makes T3.1 tests pass
- **Files**: `src/flow_engineering/opencode_skill_catalog.py` (+~50 LOC: NEW `enforce_min_skill_versions(min_versions: dict[str, str])` helper at line 117+ that (a) iterates dict, (b) reads on-disk `SKILL.md` via existing `_load_frontmatter`, (c) extracts `version` field, (d) parses as `(MAJOR, MINOR)` tuple, (e) raises existing `SkillVersionError` with remediation message on violation)
- **Acceptance**: All 5 TestEnforceMinSkillVersions tests PASS; live smoke: `from flow_engineering.opencode_skill_catalog import enforce_min_skill_versions` is importable; existing 1275+ `opencode_skill_catalog.py` tests PASS
- **Pytest command**: `uv run --frozen pytest tests/unit/test_opencode_skill_catalog.py -v`
- **LOC forecast**: ~50 prod + ~0 tests = ~50
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.3 GREEN — enforce_min_skill_versions() helper reusing SkillVersionError`

### T3.3 — REQ-V1.2.3 RED: TestPyprojectSection 2 tests

- **Type**: Test (RED)
- **Strict TDD**: RED → only adds tests; pyproject section does NOT exist
- **Files**: `tests/unit/test_opencode_skill_catalog.py` (+~30 LOC: NEW `TestPyprojectSection` class with 2 tests)
- **Acceptance**: 2 new tests:
  1. `test_pyproject_min_sdd_skill_versions_parses` — `tomllib.loads(pyproject.read_text())` returns dict with `tool.flow_engineering.min_sdd_skill_versions` key; assert 8 entries (sdd-explore + sdd-propose + sdd-spec + sdd-design + sdd-tasks + sdd-apply + sdd-verify + sdd-archive), all "3.0"
  2. `test_pyproject_section_coexists_with_prompts_section` — assert both `[tool.flow_engineering]` (NEW umbrella) and `[tool.flow_engineering.prompts]` (existing at lines 106-108) parse without collision
- **Pytest command**: `uv run --frozen pytest tests/unit/test_opencode_skill_catalog.py::TestPyprojectSection -v`
- **LOC forecast**: ~30 tests + ~0 prod = ~30
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.3 RED — TestPyprojectSection 2 tests (umbrella section parses)`

### T3.4 — REQ-V1.2.3 GREEN: `[tool.flow_engineering] min_sdd_skill_versions` pyproject section

- **Type**: Implementation (GREEN)
- **Strict TDD**: GREEN → makes T3.3 tests pass
- **Files**: `pyproject.toml` (+~10 LOC: NEW `[tool.flow_engineering]` section with `min_sdd_skill_versions = {"sdd-explore": "3.0", "sdd-propose": "3.0", "sdd-spec": "3.0", "sdd-design": "3.0", "sdd-tasks": "3.0", "sdd-apply": "3.0", "sdd-verify": "3.0", "sdd-archive": "3.0"}`)
- **Acceptance**: Both TestPyprojectSection tests PASS; live: `python -c "import tomllib; print(tomllib.loads(open('pyproject.toml').read())['tool']['flow_engineering']['min_sdd_skill_versions'])"` returns 8-key dict
- **Pytest command**: `uv run --frozen pytest tests/unit/test_opencode_skill_catalog.py::TestPyprojectSection -v`
- **LOC forecast**: ~10 prod + ~0 tests = ~10
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.3 GREEN — [tool.flow_engineering] min_sdd_skill_versions pyproject section`

### T3.5 — REQ-V1.2.3: 3-line CLI hooks at `flow apply` / `flow verify` / `flow archive` startup

- **Type**: Implementation (wire CLI gate)
- **Files**: `src/flow_engineering/cli.py` (+~30 LOC: NEW `_enforce_min_skill_versions_or_exit()` helper at line 3300+ that reads pyproject + calls `enforce_min_skill_versions()` + emits stderr JSON on error + `sys.exit(4)`; add 3 calls at top of `flow apply` / `flow verify` / `flow archive` Click command bodies); `tests/unit/test_cli_apply_verify_archive.py` (NEW or extend existing, +~20 LOC: 3 tests asserting each command exits 4 when on-disk skill version < pyproject minimum)
- **Acceptance**: All 3 NEW CLI hook tests PASS; live: with `sdd-apply` SKILL.md temporarily edited to `version: "2.5"`, `flow apply` exits 4 + stderr `{"error": "skill_version_violation", "skill": "sdd-apply", "expected": ">= 3.0", "found": "2.5", "hint": "run 'opencode skill install sdd-apply@latest'"}`
- **Pytest command**: `uv run --frozen pytest tests/unit/test_cli_apply_verify_archive.py -v` (or extended test file)
- **LOC forecast**: ~30 prod + ~20 tests = ~50
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.3 T3.5 — 3-line CLI hooks at flow apply/verify/archive startup (exit code 4)`

### T3.6 — REQ-V1.2.3 REFACTOR: integration test for full gate flow

- **Type**: REFACTOR (integration test)
- **Files**: `tests/integration/test_skill_version_gate.py` (NEW, +~20 LOC: end-to-end test that (a) sets up tmp pyproject with high minimum version, (b) invokes `flow apply` via subprocess, (c) asserts exit code 4 + structured stderr JSON + 0 side effects on disk)
- **Acceptance**: Integration test PASS; full test suite 1360+ tests PASS; no regressions in `cli.py` apply/verify/archive command bodies
- **Pytest command**: `uv run --frozen pytest tests/integration/test_skill_version_gate.py -v`
- **LOC forecast**: ~0 prod + ~20 tests = ~20
- **Commit message**: `refactor(v1.2-followups): REQ-V1.2.3 T3.6 — integration test for full skill version gate flow`

### Sub-batch C summary

- **Total**: ~90 prod LOC + ~150 test LOC = ~240 (matches ~240 forecast)
- **Per-PR LOC**: ~240 (at budget limit; REFACTOR T3.6 lands clean)

---

## Sub-batch D — REQ-V1.2.4 Path A rename + REQ-V1.2.5 closeout (PR#2d, T4.1..T4.5)

### T4.1 — REQ-V1.2.4 RED: TestDriftEventsGroup 3 tests (post-rename canonical surface)

- **Type**: Test (RED)
- **Strict TDD**: RED → only adds tests; `flow drift events` group does NOT exist yet, only `flow drift-events`
- **Files**: `tests/unit/test_cli_drift.py` (+~40 LOC: NEW `TestDriftEventsGroup` class with 3 tests)
- **Acceptance**: 3 new tests:
  1. `test_flow_drift_events_list_works_via_new_subcommand_group` — `flow drift events list --limit 5` exits 0 + renders aligned text table (same output as pre-rename `flow drift-events list`)
  2. `test_flow_drift_events_tail_works_via_new_subcommand_group` — `flow drift events tail` exits 0
  3. `test_flow_drift_events_stats_works_via_new_subcommand_group` — `flow drift events stats` exits 0
- **Pytest command**: `uv run --frozen pytest tests/unit/test_cli_drift.py::TestDriftEventsGroup -v`
- **LOC forecast**: ~40 tests + ~0 prod = ~40
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.4 RED — TestDriftEventsGroup 3 tests (canonical surface)`

### T4.2 — REQ-V1.2.4 GREEN: `flow drift events {list,tail,stats}` subcommand group

- **Type**: Implementation (GREEN)
- **Strict TDD**: GREEN → makes T4.1 tests pass
- **Files**: `src/flow_engineering/cli.py` (+~25 LOC: NEW `@main.group("drift")` at line 1718 (replace existing flat `@main.command("drift")`); add `@drift_group.command("events", ...)` sub-group; move `list` / `tail` / `stats` from `drift_events_group` to `@drift_group.group("events").command("list/tail/stats")`; preserve `flow drift <change>` as default command via `invoke_without_command=True` + manual dispatch on `ctx.invoked_subcommand`)
- **Acceptance**: All 3 TestDriftEventsGroup tests PASS; existing `test_cli_drift.py` tests still PASS (default command dispatch); live: `flow drift v1.1-followups` still works (now via `flow drift run v1.1-followups` default); `flow drift events list` exits 0
- **Pytest command**: `uv run --frozen pytest tests/unit/test_cli_drift.py -v`
- **LOC forecast**: ~25 prod + ~0 tests = ~25
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.4 GREEN — flow drift events {list,tail,stats} subcommand group (BREAKING) + default drift command dispatch`

### T4.3 — REQ-V1.2.4: 1-release `deprecated=True` Click group alias for `flow drift-events`

- **Type**: Implementation (alias shim)
- **Strict TDD**: REFACTOR + new tests combined; mirror v1.1 `SnapshotGraphMissing` PEP 562 pattern (but here it's a Click group alias, not a Python alias)
- **Files**: `src/flow_engineering/cli.py` (+~15 LOC: NEW `@main.group(name="drift-events", deprecated=True)` Click group at line 1821 that auto-emits `DeprecationWarning` + delegates `list`/`tail`/`stats` subcommands to the new `flow drift events` group via `ctx.forward()`); `tests/unit/test_cli_drift_events.py` (+~30 LOC: NEW `TestDriftEventsAlias` class with 4 tests: alias-still-works, alias-emits-DeprecationWarning, alias-dispatches-correctly, alias-marked-removed-in-v1.3)
- **Acceptance**: All 4 alias tests PASS; live: `flow drift-events list --limit 5` still exits 0 + emits `DeprecationWarning: 'flow drift-events' is deprecated, use 'flow drift events' instead. The alias will be removed in v1.3.` to stderr
- **Pytest command**: `uv run --frozen pytest tests/unit/test_cli_drift_events.py -v`
- **LOC forecast**: ~15 prod + ~30 tests = ~45
- **Commit message**: `feat(v1.2-followups): REQ-V1.2.4 T4.3 — flow drift-events 1-release deprecated=True Click group alias`

### T4.4 — REQ-V1.2.5: CHANGELOG v1.2.0 BREAKING entry + pyproject 1.1.0 → 1.2.0 + capability spec sync

- **Type**: Release closeout (REQ-V1.2.5)
- **Files**: `CHANGELOG.md` (+~25 LOC: `## [1.2.0] - 2026-06-28` entry with ### BREAKING (Path A rename + 1-release alias) + ### Added (REQ-44 metrics rotation + REQ-48 golden tests + REQ-54 skill version gate) + ### Migration (flow drift-events → flow drift events + FLOW_METRICS_LOG_MAX_BYTES/MAX_AGE_DAYS env vars + [tool.flow_engineering] min_sdd_skill_versions section)); `pyproject.toml` (1-line: `version = "1.2.0"`); `openspec/specs/decision-drift/spec.md` (+~20 LOC: NEW v1.2 archive status section + Versioning row flip from v1.1 → v1.2); `tests/unit/test_version.py` (1-line assertion update: `assert __version__ == "1.2.0"`)
- **Acceptance**: Full suite 1360+ tests PASS (after `test_version` fix); live: `grep "version" pyproject.toml | head -1` shows `"1.2.0"`; `grep "## \[1.2.0\]" CHANGELOG.md` returns the BREAKING entry
- **Pytest command**: `uv run --frozen pytest tests/ --tb=short -q`
- **LOC forecast**: ~45 prod + 1-line test fix = ~46
- **Commit message**: `chore(release): v1.2.0 — pyproject 1.1.0→1.2.0 + CHANGELOG v1.2.0 BREAKING entry + capability spec sync`

### T4.5 — REQ-V1.2.4 REFACTOR: ensure all existing tests pass with both old (deprecated) + new (canonical) surface

- **Type**: REFACTOR (regression sweep)
- **Files**: `tests/unit/test_cli_drift.py` + `tests/unit/test_cli_drift_events_list.py` + `tests/unit/test_cli_drift_events_tail.py` + `tests/unit/test_cli_drift_events_stats.py` (~0 LOC delta; verify all existing assertions still pass with new group dispatch)
- **Acceptance**: Full test suite 1360+ tests PASS (no regressions); `git diff tests/unit/test_cli_drift*.py` shows 0 net deletions (only additions for new tests); ruff check 0 findings on cli.py
- **Pytest command**: `uv run --frozen pytest tests/ --tb=short -q`
- **LOC forecast**: ~0 prod + ~0 tests = ~0 (verification-only commit)
- **Commit message**: `refactor(v1.2-followups): REQ-V1.2.4 T4.5 — regression sweep (old + new surface coexist)`

### Sub-batch D summary

- **Total**: ~85 prod LOC + ~70 test LOC + ~45 closeout = ~200 (slightly higher than ~120 forecast due to CHANGELOG + spec sync in T4.4; well within budget)
- **Per-PR LOC**: ~200 (well within ≤250 budget)

---

## Total scope

- **22 functional tasks** across 4 sub-batches (no separate closeout commits — T4.4 IS the closeout)
- **~170 prod LOC** + **~580 test LOC** + 4 NEW snapshot files (~20 committed) = **~790 total** (matches `proposal.md` forecast)
- **22 NEW v1.2 tests** across 4 NEW test files (test_observability.py::TestMetricsRotation +7 + test_prompt_render_golden.py +6 + test_opencode_skill_catalog.py +7 + test_cli_drift.py +3 + test_cli_drift_events.py +4 + integration test_skill_version_gate.py +1 + existing test_cli_apply_verify_archive.py +3 = ~31 tests; some are added to existing files)
- **1360 / 1360+ tests** expected post-merge (+18 net vs `75961ad` v1.1 baseline of 1342)

## Risks

- **MED**: Path A BREAKING change surprises operators with shell aliases pointing at `flow drift-events` after alias removal in v1.3 — mitigated by CHANGELOG v1.2.0 BREAKING callout + 1-release `deprecated=True` Click group alias + Click migration hint in `--help`. Bounded to one release cycle.
- **MED**: Single-PR strategy bundles 4 items (~790 LOC) — per `sdd-phase-common.md` Section E, this EXCEEDS the 400-line chained-PR threshold by ~2×. **Chained PRs MANDATORY** (4 PRs, `stacked-to-main`, each ≤ ~250 LOC).
- **LOW**: `metrics.jsonl` rotation under lock on slow network FS — rotation helper sits OUTSIDE existing `try/except OSError`; helper uses own `try/except OSError` for rename + sibling unlink.
- **LOW**: Golden snapshot drift on unintentional template edits — `--update-goldens` flag is explicit opt-in; CI failure on drift is the desired operator signal.
- **LOW**: `min_sdd_skill_versions` false positive on non-numeric version (e.g., `3.0-beta`) — `_extract_version` returns `"0.0"` fallback (precedent at `opencode_skill_catalog.py:536`); gate fires correctly.
- **LOW**: Click `deprecated=True` group alias emits generic Click warning, not the project-specific migration hint — mitigated by custom `DeprecationWarning` in T4.3 test assertion.

## Acceptance criteria

1. **1360 / 1360+ tests passing** post-merge (1342 baseline + ~18 NEW v1.2 tests)
2. **0 mypy errors** in `observability.py` + `opencode_skill_catalog.py` + `prompt_registry.py` + `cli.py` (no new annotations introduced; existing annotations preserved)
3. **6 / 6 NEW BDD scenarios passing** (2 per REQ across 3 NEW feature files: `req44_metrics_rotation.feature` + `req48_golden_prompts.feature` + `req54_skill_version_gate.feature`)
4. **`metrics.jsonl`** rotates at exactly 10 MB to `metrics.<ISO-no-colons>.jsonl` and deletes siblings > 30 days old (mirrors `drift_events.jsonl` behavior)
5. **`tests/golden/prompts/*.txt`** (4 files) match `render_prompt_canonical()` output byte-for-byte; `--update-goldens` flag regenerates snapshots
6. **`flow apply` / `flow verify` / `flow archive`** exit code 4 when `[tool.flow_engineering] min_sdd_skill_versions` declares a minimum version higher than the on-disk SKILL.md version, with `SkillVersionError` remediation message
7. **`flow drift <change>`** still works (now as `flow drift run <change>` via default command dispatch) + `flow drift events {list,tail,stats}` is the new group subcommand + `flow drift-events {list,tail,stats}` continues to work as 1-release alias emitting `DeprecationWarning`
8. **CHANGELOG v1.2.0** BREAKING entry documents the rename + the alias + the `flow drift-events` → `flow drift events` migration hint + the new env vars + the new pyproject section
9. **pyproject.toml** version bumped `1.1.0` → `1.2.0`
10. **`openspec/specs/decision-drift/spec.md`** v1.2 archive status section added
11. **4 / 4 REQs (REQ-V1.2.1..V1.2.4) have at least one passing test demonstrating compliance**
12. **22 / 22 functional tasks (T1.1..T4.5) closed across 4 sub-batches with strict-TDD RED → GREEN → REFACTOR evidence**
13. **Loop-mode continuity**: `sdd-apply v1.2-followups PR#2a` ready (T1.1..T1.5 first chained PR)

## Accomplished

- ✅ Wrote `openspec/changes/v1.2-followups/tasks.md` (22 tasks, 4 sub-batches; mirrors v1.1-followups per-task TDD format)
- ✅ Mirrored `openspec/changes/archive/2026-06-28-v1.1-followups/tasks.md` per-task TDD shape (YAML frontmatter + Goal + Scope + Out-of-Scope + Instructions + Discoveries + 4 sub-batches + Risks + Acceptance criteria)
- ✅ Per-task format includes Type + Strict TDD (RED/GREEN/REFACTOR) + Acceptance (pytest command + assertion) + LOC forecast + Commit message
- ✅ Pre-flight pytest confirmed: 1342 tests collect clean at HEAD `75961ad`
- ✅ Code references verified: `drift_event_log.py:196-254` (rotation precedent) + `opencode_skill_catalog.py:117` (existing `SkillVersionError`) + `observability.py:171-189` (`increment()` function) + `snapshot_manager.py:81-123` (PEP 562 alias pattern) + `cli.py:1718-1829` (Path A rename targets)
- ✅ Decision ↔ Code Binding Hook applied: tasks reference design.md D1..D4 line numbers + manual code_refs throughout
- ✅ Loop-mode ready: `next_recommended: sdd-apply v1.2-followups PR#2a` (sub-batch A: T1.1..T1.5)

## Next Steps

- `sdd-apply v1.2-followups PR#2a` — T1.1 RED (TestMetricsRotation 5 tests) → T1.2 GREEN (`_rotate_metrics_if_needed()` + env vars) → T1.3 RED (age cleanup 2 tests) → T1.4 GREEN (sibling cleanup) → T1.5 REFACTOR (docs + CHANGELOG v1.2.0a)
- Then PR#2b (T2.1..T2.6 golden tests + 4 snapshots + `--update-goldens` flag) → PR#2c (T3.1..T3.6 skill version gate + pyproject + 3-line CLI hook) → PR#2d (T4.1..T4.5 Path A rename + 1-release alias + closeout)
- Apply-progress closeout docs per `v1.1-followups` `apply-progress/merged.md` precedent after each sub-batch
- `sdd-verify v1.2-followups` after all 4 PRs land (validates the 22 tasks + 6 NEW BDD scenarios)
- `sdd-archive v1.2-followups` after final PR merge (closes the 4 v1.1 carry-forwards: REQ-44 + REQ-48 + REQ-54 + Path A rename)

## Relevant Files

- `openspec/changes/v1.2-followups/tasks.md` — NEW (22 tasks, 4 sub-batches; mirrors v1.1-followups per-task TDD format)
- `openspec/changes/v1.2-followups/explore.md` — input artifact (4 REQs investigated + dependency-ordered + 6 risks)
- `openspec/changes/v1.2-followups/proposal.md` — input artifact (5 REQs + 4-PR chain strategy + ~790 LOC forecast + Approach A recommended)
- `openspec/changes/v1.2-followups/design.md` — input artifact (4 design decisions D1..D4 + 0 open questions + manual code_refs)
- `openspec/changes/archive/2026-06-28-v1.1-followups/tasks.md` — precedent (18 tasks, 6 sub-batches, per-task TDD shape with strict acceptance criteria)
- `src/flow_engineering/observability.py:171-189` — T1.1..T1.5 targets (rotation helpers added above `increment()`); `increment()` is the canonical insertion point
- `src/flow_engineering/drift_event_log.py:196-254` — T1.2 verbatim reference (rotation pattern mirror)
- `src/flow_engineering/prompt_registry.py:179-224` — T2.2 target (NEW `render_prompt_canonical` helper after `PROMPT_NAMES` catalog)
- `tests/golden/prompts/{strict_tdd,auto_suggest_header,auto_suggest_footer,auto_suggest_empty}.txt` — T2.2 NEW snapshot files (4 committed artifacts)
- `src/flow_engineering/opencode_skill_catalog.py:117` — T3.2 target (NEW `enforce_min_skill_versions` helper after existing `SkillVersionError` class)
- `pyproject.toml:106-108` — T3.4 target (NEW `[tool.flow_engineering]` umbrella section alongside existing `[tool.flow_engineering.prompts]`)
- `src/flow_engineering/cli.py:1718-1829` — T4.1..T4.3 targets (Path A rename at line 1718 + 1-release alias at line 1821); T3.5 (3-line startup hooks at `flow apply`/`flow verify`/`flow archive`)
- `src/flow_engineering/snapshot_manager.py:81-123` — T4.3 reference (PEP 562 `__getattr__` pattern + `SnapshotGraphMissingError` canonical)
- `tests/unit/test_observability.py` — T1.1..T1.4 targets (NEW `TestMetricsRotation` class + 7 tests)
- `tests/unit/test_prompt_render_golden.py` — T2.1..T2.6 NEW (~120 LOC across `TestGoldenRegression` + `TestGoldenUpdate`)
- `tests/unit/test_opencode_skill_catalog.py` — T3.1..T3.4 targets (NEW `TestEnforceMinSkillVersions` + `TestPyprojectSection` classes + 7 tests)
- `tests/unit/test_cli_apply_verify_archive.py` — T3.5 target (3 NEW CLI hook tests, exit code 4)
- `tests/integration/test_skill_version_gate.py` — T3.6 NEW integration test (full gate flow)
- `tests/unit/test_cli_drift.py` — T4.1..T4.2 targets (NEW `TestDriftEventsGroup` + 3 tests + regression sweep)
- `tests/unit/test_cli_drift_events.py` — T4.3 target (NEW `TestDriftEventsAlias` + 4 alias tests)
- `tests/bdd/req44_metrics_rotation.feature` — T1.1..T1.4 NEW BDD (2 scenarios)
- `tests/bdd/req48_golden_prompts.feature` — T2.1..T2.6 NEW BDD (2 scenarios)
- `tests/bdd/req54_skill_version_gate.feature` — T3.1..T3.6 NEW BDD (2 scenarios)
- `CHANGELOG.md` — T1.5 (v1.2.0a entry) + T4.4 (v1.2.0 BREAKING entry)
- `pyproject.toml` — T3.4 (NEW `[tool.flow_engineering]` section) + T4.4 (version bump 1.1.0 → 1.2.0)
- `openspec/specs/decision-drift/spec.md` — T4.4 (NEW v1.2 archive status section + Versioning row flip)
- `tests/unit/test_version.py` — T4.4 (1-line assertion update to expect 1.2.0)
