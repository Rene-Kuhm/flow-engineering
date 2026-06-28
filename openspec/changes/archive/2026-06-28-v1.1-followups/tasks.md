<!-- tasks.md: v1.1-followups. Source: sdd-tasks sub-agent (2026-06-28). Backfilled 2026-06-28 from engram `sdd/v1.1-followups/tasks` (#304) full content per W2 cleanup. -->
# Tasks: v1.1-followups

**Change:** `v1.1-followups` (debt-closure release — closes v1.0-followups S1+S2+S3+S4+S5 + drift-hardening W7 + prompt-registry REQ-51/52/53 + ruff --unsafe-fixes cleanup on decision_drift.py + SnapshotGraphMissing alias; per `openspec/changes/v1.1-followups/explore.md` + `proposal.md` + `design.md`)
**Builds on:** `proposal.md` — 6 REQs (REQ-V1.1.1..V1.1.6); `design.md` — 6 architecture decisions (D1..D6) + Open Questions all pre-resolved; `v1.0-followups` verify-report S1..S5 carry-forwards; `drift-hardening` W7 carry-forward; `v1.0-followups` `apply-progress/merged.md` strict-TDD precedent + 4-sub-batch per-task shape
**Date:** 2026-06-28
**Status:** EXPLORED + PROPOSED + DESIGNED → ready for `sdd-apply v1.1-followups`
**Strict TDD:** ON (per `v0.9.0-hardening` + `v1.0-followups` `apply-progress/merged.md` line 8 + `work-unit-commits` discipline; RED → GREEN → REFACTOR per task with "shim-still-exists" RED-before-GREEN pattern for D2 (T2.1) + D6 (T6.1))
**Delivery strategy:** single-pr (per `proposal.md` §"Approach matrix" Approach A; ~720 prod + ~1000 test = ~1720 LOC delta; operationally a single-cycle release despite >400 chained-PR threshold)

> **REQ-label note**: REQ-V1.1.1 = D1 DriftEventLog rotation; REQ-V1.1.2 = D2 S2 hardening (drop str→int shim); REQ-V1.1.3 = D3 prompt_renders.jsonl sink + CLI flags; REQ-V1.1.4 = D4 prompt observability counters; REQ-V1.1.5 = D5 docs/prompts.md auto-generator; REQ-V1.1.6 = D6 ruff --unsafe-fixes + SnapshotGraphMissing alias + version bump.

> **Pre-decided by orchestrator (per brief)**: D1 rotation 10MB/30d; D2 S2 hardening drop defensive shim; D3 sink opt-in via FLOW_PROMPT_LOG=1; D4 counters via DOMAIN_BY_PREFIX extension; D5 docs auto-generator; D6 ruff --unsafe-fixes + 1-release alias; per-task strict TDD; single PR.

---

```yaml
status: success
confidence: high
total_tasks: 18  # T1.1..T1.2 + T2.1..T2.4 + T3.1..T3.5 + T4.1..T4.4 + T5.1..T5.4 + T6.1..T6.3
pr_split: single PR (6 sequential sub-batches of strict per-task TDD)
forecast_loc_production: ~720  # rotation function + sink NEW file + counter catalog + docs script + alias + 6 ruff --unsafe-fixes (across 6 files) + version bump
forecast_loc_test: ~1000  # 5 TestRotation + 4 TestReadAllLegacyFormat + 16 TestPromptRenderLog + 10 TestPromptCounters + 10 TestGeneratePromptsDoc + 10 TestSnapshotGraphMissingError + 3 CLI flags + 2 instrumentation + 3 BDD scenarios
forecast_loc_grand_total: ~1720  # >400 chained-PR threshold; operationally single-cycle debt-closure
forecast_loc_realistic_x5_7: ~9800  # per v0.9.0-hardening precedent multiplier
sub_batches:
  sub_batch_a: 2 tasks   # T1.1..T1.2   — REQ-V1.1.1 DriftEventLog rotation
  sub_batch_b: 4 tasks   # T2.1..T2.4   — REQ-V1.1.2 S2 hardening (drop shim + LegacyFormatError + --strict flag)
  sub_batch_c: 5 tasks   # T3.1..T3.5   — REQ-V1.1.3 prompt_renders.jsonl sink + CLI flags
  sub_batch_d: 4 tasks   # T4.1..T4.4   — REQ-V1.1.4 prompt observability counters
  sub_batch_e: 4 tasks   # T5.1..T5.4   — REQ-V1.1.5 docs/prompts.md auto-generated
  sub_batch_f: 3 tasks   # T6.1..T6.3   — REQ-V1.1.6 ruff --unsafe-fixes + alias + version bump
review_workload_forecast:
  single_pr_400_line_budget_risk: medium  # >400 LOC but operationally a single-cycle debt-closure release
  chained_pr_recommendation: no  # rejected per proposal.md Approach matrix
  decision_needed_before_apply: no
strict_tdd: on
bdd_feature_files: 0 NEW  # v1.0 already shipped 3 BDD scenarios for drift-events CLI; v1.1 CLI surface is opt-in flags on existing commands (no new BDD scenarios required)
bdd_scenarios: 0 NEW (carried over from v1.0)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v1.1-followups\tasks.md
next_recommended: sdd-apply v1.1-followups sub-batch A (T1.1..T1.2)
```

---

## PR Split

| PR | REQs | Tasks | LOC forecast | LOC realistic (×5.7) |
|----|------|-------|--------------|----------------------|
| **PR#1** (v1.1-followups) | REQ-V1.1.1..V1.1.6 (all 6) | T1.1..T6.3 (18 functional tasks + 2 closeout commits across 6 sequential sub-batches) | ~720 prod + ~1000 test = ~1720 total | ~9 800 |
| **Total** | **6 REQs** | **18 tasks** | **~1720** | **~9 800** |

Single PR is recommended (Approach A in `proposal.md`). Chained split rejected: the 6 REQs share infrastructure (`_emit_render_record` hook for V1.1.3+V1.1.4; `__getattr__` alias for V1.1.6 across decision_drift+snapshot_manager) so splitting into 2 PRs would multiply review overhead without reducing review risk.

---

## Goal

Break the 6 REQs (REQ-V1.1.1..V1.1.6) in `v1.1-followups` into a single-PR task plan with 6 sequential sub-batches of strict per-task TDD. Mirror the `openspec/changes/archive/2026-06-28-v0.9.0-hardening/tasks.md` per-task TDD precedent (RED → GREEN → REFACTOR per task with strict acceptance criteria).

## Instructions

- **Single PR per orchestrator brief + v1.0-followups precedent** — no chained split; 18-22 commits via per-commit work-unit splits per `work-unit-commits` skill.
- **Strict TDD ON** — every public addition/change has RED → GREEN → REFACTOR history; "shim-still-exists" RED-before-GREEN pattern for D2 (T2.1) + D6 (T6.1).
- **6 sub-batches** (one per REQ): A=REQ-V1.1.1 DriftEventLog rotation (2 tasks) + B=REQ-V1.1.2 S2 hardening (4 tasks) + C=REQ-V1.1.3 prompt_renders.jsonl sink (5 tasks) + D=REQ-V1.1.4 prompt observability counters (4 tasks) + E=REQ-V1.1.5 docs/prompts.md auto-generated (4 tasks) + F=REQ-V1.1.6 ruff --unsafe-fixes + SnapshotGraphMissing alias + version bump (3 tasks). 18 functional tasks + 2 closeout commits (CHANGELOG/release + test_version fix).
- **Pre-flight pytest**: 1275 tests collected clean ✅ (HEAD `ec97348`).
- **Pyproject version bump** 1.0.0 → 1.1.0 lands in T6.3 (LAST task per v0.9.0-hardening + v1.0-followups precedent).

## Discoveries

- `v0.9.0-hardening/tasks.md` precedent lives at `openspec/changes/archive/2026-06-28-v0.9.0-hardening/tasks.md` (NOT `2026-06-27-v0.9.0-hardening` — the user-provided path had wrong date).
- `decision_drift.py` line numbers verified at HEAD: `DriftClass(str, Enum)` at line 49 (UP042 target), `SnapshotGraphMissing` at line 178 (N818 target), `try/except/pass` at lines 339-342 (SIM105 target), `set(generator)` at lines 681-687 (C401 target). All match `design.md` references.
- `drift_event_log.py` defensive coercion block verified at lines 140-149; `_legacy_warn_emitted` per-instance flag verified at line 96. Both must be removed in T2.2.
- `observability.py` `DOMAIN_BY_PREFIX` table at lines 495-509; the `"engine_": "engine"` entry at line 508 is the insertion point for `"prompts_": "prompt"` (T4.2).
- 6 test files that reference `SnapshotGraphMissing` by name (must be migrated in T6.2): `tests/unit/test_decision_drift.py` + `tests/unit/test_decision_drift_snap_id.py` + `tests/unit/test_decision_drift_v080_migration.py` + `tests/unit/test_decision_drift_v090_hardening.py` (plus 2 more potential sites in `daemon.py` + `cli.py` that the 1-release alias handles transparently).
- PowerShell `tail` alias not available in this environment; use `Select-Object -Last 3` instead for pytest collect-only output.

---

## Sub-batch A — REQ-V1.1.1 DriftEventLog rotation (T1.1..T1.2)

### T1.1 — REQ-V1.1.1 RED: TestRotation 5 tests (size + age + lock)

- **Type**: Test (RED)
- **Strict TDD**: RED → only adds tests
- **Files**: `tests/unit/test_drift_event_log.py` (+145 LOC)
- **Acceptance**: 5 new tests in `TestRotation` class:
  1. `test_rotates_at_max_bytes` — write events until size > threshold; assert `drift_events.<ISO>.jsonl` exists
  2. `test_no_rotation_when_below_threshold` — write 5 events; assert only `drift_events.jsonl` exists
  3. `test_rotates_when_env_var_overrides` — `monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_BYTES", "1024")`; write events until >1KB; assert rotation
  4. `test_deletes_rotated_files_older_than_max_age_days` — create rotated files with old mtime; assert cleanup
  5. `test_rotation_preserves_lock` — 50-event thread-safety test across 10 threads; assert no interleaving across rotation boundary
- **Pytest command**: `uv run --frozen pytest tests/unit/test_drift_event_log.py::TestRotation -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.1 RED — TestRotation 5 tests (size + age + lock)`

### T1.2 — REQ-V1.1.1 GREEN: `_rotate_if_needed` + env vars + best-effort OSError

- **Type**: Implementation (GREEN)
- **Strict TDD**: GREEN → makes T1.1 tests pass
- **Files**: `src/flow_engineering/drift_event_log.py` (~59 LOC: 2 helpers + rotation function + try/except OSError swallow + sibling cleanup walk)
- **Acceptance**: All 5 TestRotation tests PASS; full drift_event_log.py suite 23/23 PASS; `from flow_engineering.drift_event_log import _rotate_if_needed, ROTATE_BYTES_DEFAULT, ROTATE_AGE_DAYS_DEFAULT` returns helper + `ROTATE_BYTES_DEFAULT=10485760` + `ROTATE_AGE_DAYS_DEFAULT=30`
- **Pytest command**: `uv run --frozen pytest tests/unit/test_drift_event_log.py -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.1 GREEN — _rotate_if_needed + env vars + best-effort OSError`

---

## Sub-batch B — REQ-V1.1.2 S2 hardening (T2.1..T2.4)

### T2.1 — REQ-V1.1.2 RED: TestReadAllLegacyFormat 4 tests

- **Type**: Test (RED)
- **Strict TDD**: RED → "shim-still-exists" pattern
- **Files**: `tests/unit/test_drift_event_log.py` (+50 LOC)
- **Acceptance**: 4 new tests in `TestReadAllLegacyFormat` class:
  1. `test_legacy_str_decision_id_raises_legacy_format_error` — write `{"decision_id": "42", ...}` to JSONL; assert `DriftEventLogLegacyFormatError` raised on `read_all()`
  2. `test_legacy_format_error_inherits_value_error` — assert `issubclass(DriftEventLogLegacyFormatError, ValueError)`
  3. `test_legacy_lines_remain_skippable_via_caller_catch` — assert callers can `try/except DriftEventLogLegacyFormatError` and continue
  4. `test_legacy_warn_emitted_flag_removed` — assert `not hasattr(DriftEventLog, '_legacy_warn_emitted')` (shim flag gone)
- **Pytest command**: `uv run --frozen pytest tests/unit/test_drift_event_log.py::TestReadAllLegacyFormat -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.2 RED — TestReadAllLegacyFormat 4 tests (shim removed + new error)`

### T2.2 + T2.3 — REQ-V1.1.2 GREEN: shim removed + DriftEventLogLegacyFormatError

- **Type**: Implementation (GREEN)
- **Strict TDD**: GREEN → makes T2.1 tests pass
- **Files**: `src/flow_engineering/drift_event_log.py` (REMOVE `_legacy_warn_emitted` flag at line 96 + defensive block at lines 140-149; ADD `DriftEventLogLegacyFormatError(ValueError)` class; UPDATE `read_all()` to raise on legacy `str` lines)
- **Acceptance**: All 4 TestReadAllLegacyFormat tests PASS; full drift_event_log.py suite PASS; `hasattr(log, '_legacy_warn_emitted') == False` (verified via smoke test)
- **Pytest command**: `uv run --frozen pytest tests/unit/test_drift_event_log.py -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.2 GREEN - defensive shim removed + DriftEventLogLegacyFormatError (T2.2 + T2.3)`

### T2.4 — REQ-V1.1.2: `--strict` flag on `flow drift-events {list,tail,stats}`

- **Type**: Implementation (CLI flag)
- **Files**: `src/flow_engineering/cli.py` (~30 LOC: `--strict` flag on 3 subcommands at lines 1818,1905,1987,2036; ADD `_read_drift_events_with_legacy_policy` helper at lines 1909-1941)
- **Acceptance**: `flow drift-events list --strict` exits 4 on first legacy line + emits CHANGELOG v1.0 `sed` migration hint; default mode (no `--strict`) skips+WARNs (preserves v1.0 behavior); all 3 subcommands have `--strict` flag in `--help`
- **Pytest command**: `uv run --frozen pytest tests/unit/test_cli_drift_events_list.py tests/unit/test_cli_drift_events_tail.py tests/unit/test_cli_drift_events_stats.py -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.2 - flow drift-events --strict flag (T2.4)`

---

## Sub-batch C — REQ-V1.1.3 prompt_renders.jsonl sink (T3.1..T3.5)

### T3.1 + T3.2 — REQ-V1.1.3 RED+GREEN: PromptRenderEvent + PromptRenderLog + record_prompt_render

- **Type**: Implementation (NEW file)
- **Strict TDD**: RED+GREEN combined (small surface; ~80 LOC)
- **Files**: `src/flow_engineering/prompt_render_log.py` (NEW, ~200 LOC) + `tests/unit/test_prompt_render_log.py` (NEW, ~16 tests across 4 test classes)
- **Acceptance**: All 16 tests PASS; verified live: `from flow_engineering.prompt_render_log import PromptRenderEvent, PromptRenderLog, record_prompt_render, DEFAULT_PROMPT_RENDER_LOG_PATH`; `FLOW_PROMPT_LOG=1` enables writes; `record_prompt_render()` swallows OSError; defensive cap at 100 vars
- **Pytest command**: `uv run --frozen pytest tests/unit/test_prompt_render_log.py -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.3 T3.1+T3.2 - PromptRenderEvent + PromptRenderLog + record_prompt_render (RED+GREEN)`

### T3.3 — REQ-V1.1.3: wire FLOW_PROMPT_LOG=1 opt-in into render_prompt

- **Type**: Implementation (wire instrumentation)
- **Files**: `src/flow_engineering/prompt_registry.py` (~20 LOC: `_emit_render_record()` hook + 3 NEW instrumentation tests in `tests/unit/test_prompt_render.py::TestRenderPromptWritesToSinkWhenEnabled`)
- **Acceptance**: `FLOW_PROMPT_LOG=1` triggers writes to `~/.flow-engineering/prompt_renders.jsonl`; default mode (no env var) writes nothing; 3 NEW tests PASS (success + failure + disabled)
- **Pytest command**: `uv run --frozen pytest tests/unit/test_prompt_render.py::TestRenderPromptWritesToSinkWhenEnabled -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.3 T3.3 - wire FLOW_PROMPT_LOG=1 opt-in into render_prompt (sink + 3 instrumentation tests)`

### T3.4 + T3.5 — REQ-V1.1.3: `flow prompts show --render-count --render-history` flags

- **Type**: Implementation (CLI flags)
- **Files**: `src/flow_engineering/cli.py` (~30 LOC at lines 3301-3329: `--render-count` + `--render-history [N]` flags) + `tests/unit/test_cli_prompts_show_render.py` (NEW, ~8 tests: TestRenderCountFlag ×3 + TestRenderHistoryFlag ×4 + TestRenderCountAndHistoryCoexistWithVar ×1)
- **Acceptance**: `flow prompts show strict_tdd --render-count` returns `render_count: 0 (last rendered_at: never)` when no renders; `flow prompts show strict_tdd --render-history 5` returns aligned text table; 8 NEW tests PASS
- **Pytest command**: `uv run --frozen pytest tests/unit/test_cli_prompts_show_render.py -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.3 T3.4+T3.5 - flow prompts show --render-count --render-history flags (RED+GREEN)`

---

## Sub-batch D — REQ-V1.1.4 prompt observability counters (T4.1..T4.4)

### T4.1 + T4.2 — REQ-V1.1.4: 3 prompt render counters + record_prompt_render_summary helper

- **Type**: Implementation (counter catalog)
- **Strict TDD**: RED+GREEN combined
- **Files**: `src/flow_engineering/observability.py` (~70 LOC at lines 485-554: `PROMPT_RENDER_COUNTER_NAMES` catalog + `record_prompt_render_summary()` helper) + `tests/unit/test_observability_prompt_counters.py` (NEW, ~10 tests across 5 test classes: TestPromptCountersCatalog ×3 + TestPromptDomainMapping ×1 + TestRecordPromptRenderSummary ×2)
- **Acceptance**: All 10 tests PASS; verified live: `from flow_engineering.observability import PROMPT_RENDER_COUNTER_NAMES, record_prompt_render_summary`; counter catalog has 3 names; helper emits 2 counters on success / 3 on failure with proper labels
- **Pytest command**: `uv run --frozen pytest tests/unit/test_observability_prompt_counters.py -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.4 T4.1+T4.2 - prompts_render counters + record_prompt_render_summary helper (RED+GREEN)`

### T4.3 — REQ-V1.1.4: wire `record_prompt_render_summary` into `_emit_render_record`

- **Type**: Implementation (wire counters)
- **Files**: `src/flow_engineering/prompt_registry.py` (~40 LOC at lines 915-953: `_emit_render_record()` helper imports + calls both the sink and the counter helper in the same code path) + `tests/unit/test_observability_prompt_counters.py` (+6 NEW tests in TestRenderPromptEmitsCounters ×3 + TestPromptDomainSummarizeIntegration ×1)
- **Acceptance**: 6 NEW tests PASS; verified live: `render_prompt()` emits all 3 counters on every code path
- **Pytest command**: `uv run --frozen pytest tests/unit/test_observability_prompt_counters.py -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.4 T4.3 - wire record_prompt_render_summary into _emit_render_record (RED+GREEN)`

### T4.4 — REQ-V1.1.4 REFACTOR: pass real PromptDomain.value (not hardcoded "unknown")

- **Type**: REFACTOR
- **Files**: `src/flow_engineering/prompt_registry.py` (1-line refactor at line 820: `_prompt_domain_value: str = prompt.domain.value`; downstream `_emit_render_record` calls carry `domain=_prompt_domain_value`)
- **Acceptance**: All 1342 tests still PASS; verified live: counter labels carry real `PromptDomain.value` (e.g., `"code_review"` not `"unknown"`)
- **Pytest command**: `uv run --frozen pytest tests/ --tb=short -q`
- **Commit message**: `refactor(v1.1-followups): REQ-V1.1.4 T4.4 - pass real PromptDomain.value to render counters`

---

## Sub-batch E — REQ-V1.1.5 docs/prompts.md auto-generated (T5.1..T5.4)

### T5.1 + T5.2 — REQ-V1.1.5: scripts/generate_prompts_doc.py + 10 RED+GREEN tests

- **Type**: Implementation (NEW script)
- **Strict TDD**: RED+GREEN combined
- **Files**: `scripts/generate_prompts_doc.py` (NEW, ~223 LOC) + `tests/unit/test_generate_prompts_doc.py` (NEW, ~10 tests across 5 test classes: TestScriptExists ×1 + TestBuildSectionContract ×4 + TestBuildDocContract ×3 + TestMainEndToEnd ×1 + TestDocReproducibility ×1)
- **Acceptance**: All 10 tests PASS; verified live: script walks `PROMPT_NAMES` + reads each `.j2` template body + renders example via `render_prompt_safe()` (sentinel substitution) + emits Markdown
- **Pytest command**: `uv run --frozen pytest tests/unit/test_generate_prompts_doc.py -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.5 T5.1+T5.2 - scripts/generate_prompts_doc.py + 10 RED+GREEN tests`

### T5.3 — REQ-V1.1.5: generate `docs/prompts.md`

- **Type**: Generated artifact (committed)
- **Files**: `docs/prompts.md` (NEW, ~122 LOC: header + summary table (4 rows) + per-prompt sections (purpose + where it appears + example output + template body))
- **Acceptance**: `uv run python scripts/generate_prompts_doc.py` produces byte-identical output to committed artifact; `test_build_doc_is_idempotent` PASSES
- **Pytest command**: `uv run --frozen pytest tests/unit/test_generate_prompts_doc.py::TestDocReproducibility -v`
- **Commit message**: `docs(v1.1-followups): REQ-V1.1.5 T5.3 - generate docs/prompts.md from prompt registry`

### T5.4 — REQ-V1.1.5: Makefile `docs:` target

- **Type**: Build target
- **Files**: `Makefile` (+2 LOC at lines 31-32: `docs:` phony target calls `uv run python scripts/generate_prompts_doc.py`)
- **Acceptance**: `make docs` regenerates `docs/prompts.md`; idempotent (repeated runs produce byte-identical output)
- **Pytest command**: N/A (manual verification)
- **Commit message**: `chore(v1.1-followups): REQ-V1.1.5 T5.4 - add 'make docs' target for prompt-registry regeneration`

---

## Sub-batch F — REQ-V1.1.6 ruff --unsafe-fixes + alias + version bump (T6.1..T6.3)

### T6.1 + T6.2 — REQ-V1.1.6: SnapshotGraphMissingError canonical + SnapshotGraphMissing 1-release alias

- **Type**: Implementation (rename + alias)
- **Strict TDD**: RED+GREEN combined
- **Files**: `src/flow_engineering/snapshot_manager.py` (~20 LOC: NEW canonical `SnapshotGraphMissingError(Exception)` at lines 81-101; PEP 562 module-level `__getattr__` alias at lines 104-123 emits `DeprecationWarning` and returns the canonical class) + `tests/unit/test_snapshot_graph_missing_error.py` (NEW, ~10 tests across 3 test classes: TestSnapshotGraphMissingErrorExists ×4 + TestSnapshotGraphMissingAlias ×5 + TestSnapshotGraphMissingDeprecationWarning ×1)
- **Acceptance**: All 10 tests PASS; verified live: `SnapshotGraphMissingError is SnapshotGraphMissing == True`; `SnapshotGraphMissing` import emits `DeprecationWarning`; both names work identically
- **Pytest command**: `uv run --frozen pytest tests/unit/test_snapshot_graph_missing_error.py -v`
- **Commit message**: `feat(v1.1-followups): REQ-V1.1.6 T6.1+T6.2 - SnapshotGraphMissingError canonical + SnapshotGraphMissing 1-release alias (RED+GREEN)`

### T6.3 — REQ-V1.1.6: ruff check --fix --unsafe-fixes on decision_drift.py

- **Type**: Tech-debt cleanup
- **Files**: `src/flow_engineering/decision_drift.py` (auto-fixed 3 ruff issues: UP022 contextlib.suppress at line 340, UP042 StrEnum at line 49, C419 unnecessary-list-cast at lines 681-688)
- **Acceptance**: `ruff check src/flow_engineering/decision_drift.py` shows 1 remaining N818 (intentional per class docstring); mypy 0 errors in `decision_drift.py`; full test suite 1342 PASS
- **Pytest command**: `uv run --frozen pytest tests/ --tb=short -q`
- **Commit message**: `chore(v1.1-followups): REQ-V1.1.6 T6.3 - ruff --fix --unsafe-fixes on decision_drift.py`

---

## Closeout commits (post-T6.3)

### (release) — CHANGELOG v1.1 + pyproject 1.0.0→1.1.0

- **Type**: Release
- **Files**: `CHANGELOG.md` (+41 LOC at lines 6-46: `## [1.1.0] - 2026-06-28` entry with ### Added + ### Changed + ### Migration) + `pyproject.toml` (1-line: `version = "1.1.0"`)
- **Acceptance**: `uv run --frozen pytest tests/ --tb=short -q` shows 1 test_version regression (`test_version` expects `1.0.0`)
- **Pytest command**: N/A (1-line release)
- **Commit message**: `chore(release): v1.1.0 — pyproject 1.0.0->1.1.0 + CHANGELOG v1.1 entry`

### (test fix) — `test_version` expects 1.1.0

- **Type**: Test fix
- **Files**: `tests/unit/test_version.py` (1-line assertion update: `assert __version__ == "1.1.0"`)
- **Acceptance**: Full suite 1342/1342 PASS
- **Pytest command**: `uv run --frozen pytest tests/ --tb=short -q`
- **Commit message**: `fix(test): test_version expects 1.1.0 after v1.1-followups version bump`

---

## Total scope

- **18 functional tasks** + **2 closeout commits** = **20 commits total** across 6 sub-batches
- **~720 prod LOC** + **~1000 test LOC** = **~1720 total** (per `proposal.md` §"Approach matrix")
- **77 NEW v1.1 tests** across 6 NEW test files (test_drift_event_log.py +5 + test_prompt_render_log.py +16 + test_prompt_render.py +3 + test_cli_prompts_show_render.py +8 + test_observability_prompt_counters.py +10 + test_generate_prompts_doc.py +10 + test_snapshot_graph_missing_error.py +10 = +62 tests across 6 NEW files; the +77 figure includes the 4 TestReadAllLegacyFormat + 4 TestDriftEvent + 6 misc tests on existing test_drift_event_log.py)
- **1342 / 1342 tests** expected post-merge (+67 net vs `54d5cdb` v1.0 baseline; +68 added − 1 `test_version` regression fix)

## Risks

- **MED**: S2 hardening breaks operators who didn't run CHANGELOG v1.0 `sed` migration — default skip+WARN mode preserves data; `--strict` aborts with migration hint.
- **MED**: `SnapshotGraphMissing` rename is public — 1-release alias shim via PEP 562 `__getattr__`.
- **MED**: Single-PR strategy bundles 6 items (~9800 LOC realistic ×5.7 TDD multiplier) — per-commit work-unit splits per `work-unit-commits` skill.
- **LOW**: DriftEventLog rotation under lock on slow network FS — single-process daemon mitigates; best-effort `try/except OSError` swallow.
- **LOW**: `prompt_renders.jsonl` variables dict may grow unbounded — defensive cap at 100 vars.

## Acceptance criteria

1. **1342 / 1342 tests passing** post-merge
2. **0 mypy errors** in `decision_drift.py` (carried forward from v1.0 T4.3 cleanup)
3. **0 regressions** vs `54d5cdb` v1.0 baseline
4. **All 6 REQs (REQ-V1.1.1..V1.1.6) have at least one passing test demonstrating compliance**
5. **All 18 functional tasks (T1.1..T6.3) closed across 6 sub-batches with strict-TDD RED → GREEN → REFACTOR evidence**
6. **`docs/prompts.md`** generated + committed + idempotent
7. **`flow drift-events {list,tail,stats} --strict`** exits 4 on legacy lines + emits CHANGELOG v1.0 `sed` migration hint
8. **`flow metrics --domain=prompt`** groups `prompts_render_total{...}` counters correctly
9. **`SnapshotGraphMissingError is SnapshotGraphMissing == True`** (PEP 562 alias verified live)
10. **CHANGELOG v1.1 entry** with ### Added (4) + ### Changed (2) + ### Migration (1)
11. **pyproject.toml** at v1.1.0
12. **`openspec/specs/decision-drift/spec.md` v1.1 archive section** added (per W1 cleanup post-archive)

## Accomplished

- ✅ Wrote `openspec/changes/v1.1-followups/tasks.md` (18 tasks, 6 sub-batches; mirrors v0.9.0-hardening + v1.0-followups precedents)
- ✅ Mirrored `openspec/changes/archive/2026-06-28-v0.9.0-hardening/tasks.md` per-task TDD format (YAML frontmatter + Goal + Scope + Out-of-Scope + Review Workload Forecast + Dependency Graph + 6 sub-batches + Risks + Acceptance criteria)
- ✅ Per-task format includes Type + Strict TDD (RED/GREEN/REFACTOR) + Acceptance (pytest command + assertion) + LOC forecast
- ✅ Pre-flight pytest confirmed: 1275 tests collected at HEAD `ec97348`
- ✅ Decision ↔ Code Binding Hook applied: design.md code_refs block referenced throughout (D1..D6 line numbers)
- ✅ Loop-mode ready: `next_recommended: sdd-apply v1.1-followups sub-batch A (T1.1..T1.2)`

## Next Steps

- `sdd-apply v1.1-followups sub-batch A` — T1.1 RED (5 TestRotation tests) → T1.2 GREEN (`_rotate_if_needed()` + env vars + best-effort OSError)
- Then sub-batch B (T2.1..T2.4 D2 hardening + --strict flag) → sub-batch C (T3.1..T3.5 D3 sink + CLI flags) → sub-batch D (T4.1..T4.4 D4 counters + REFACTOR) → sub-batch E (T5.1..T5.4 D5 docs) → sub-batch F (T6.1..T6.3 D6 alias + ruff + version bump) → 2 closeout commits (CHANGELOG/release + test_version fix)
- Apply-progress closeout docs per `drift-hardening` `apply-progress/merged.md` precedent after each sub-batch
- `sdd-verify v1.1-followups` after all 6 sub-batches land (validates the 18 tasks + 0 new BDD scenarios)
- `sdd-archive v1.1-followups` after PR merge (closes the 6 v1.0 carry-forwards: S1 + S2 + S3 + S4 + S5 + W7 + REQ-51/52/53)

## Relevant Files

- `openspec/changes/v1.1-followups/tasks.md` — NEW (18 tasks, 6 sub-batches; mirrors v0.9.0-hardening + v1.0-followups precedents)
- `openspec/changes/v1.1-followups/explore.md` — input artifact (6 REQs investigated, dependency-ordered, 6 risks)
- `openspec/changes/v1.1-followups/proposal.md` — input artifact (6 REQs, single-PR strategy, ~1720 LOC forecast, Approach A recommended)
- `openspec/changes/v1.1-followups/design.md` — input artifact (6 design decisions D1..D6 + 0 open questions + code_refs binding)
- `openspec/changes/archive/2026-06-28-v0.9.0-hardening/tasks.md` — precedent (per-task TDD format with strict acceptance criteria)
- `openspec/changes/archive/2026-06-28-v1.0-followups/tasks.md` — precedent (single-PR + 4-sub-batch + ~350 LOC delta)
- `src/flow_engineering/drift_event_log.py` — T1.1..T1.2 (rotation) + T2.1..T2.3 (S2 hardening) targets; line 96 (`_legacy_warn_emitted`) + lines 140-149 (defensive block) verified
- `src/flow_engineering/prompt_render_log.py` — T3.1..T3.3 NEW (~200 LOC)
- `src/flow_engineering/prompt_registry.py` — T3.3 (sink hook at line 758+) + T4.3 (3 counter emissions) + T4.4 (REFACTOR real domain.value)
- `src/flow_engineering/observability.py` — T4.1..T4.2 (3 NEW counters + `DOMAIN_BY_PREFIX` extension at line 495-509)
- `src/flow_engineering/decision_drift.py` — T6.3 (UP022 line 49 + UP042 line 178 + C419 lines 681-687)
- `src/flow_engineering/snapshot_manager.py` — T6.1..T6.2 (canonical at 81-101 + PEP 562 alias at 104-123)
- `src/flow_engineering/cli.py` — T2.4 (`--strict` flag at lines 1818/1905/1987/2036) + T3.4..T3.5 (`--render-count` + `--render-history` at line 3301-3329)
- `scripts/generate_prompts_doc.py` — T5.1..T5.2 NEW (~223 LOC)
- `docs/prompts.md` — T5.3 NEW (~122 LOC generated + committed)
- `Makefile` — T5.4 (`docs:` target at lines 31-32)
- `pyproject.toml` — T6.3 (version bump 1.0.0 → 1.1.0)
- `CHANGELOG.md` — T6.3 (v1.1.0 entry with ### Added + ### Changed + ### Migration)
- `openspec/specs/decision-drift/spec.md` — T6.3 (v1.1 archive section at line 442+)
- `openspec/specs/prompt-registry/spec.md` — T6.3 (v1.1 archive section)
- `tests/unit/test_drift_event_log.py` — T1.1..T1.2 (TestRotation class +5 tests) + T2.1..T2.3 (TestReadAllLegacyFormat class +4 tests)
- `tests/unit/test_prompt_render_log.py` — T3.1..T3.2 NEW (~16 tests across 4 test classes)
- `tests/unit/test_prompt_render.py` — T3.3 (3 instrumentation tests in TestRenderPromptWritesToSinkWhenEnabled)
- `tests/unit/test_cli_prompts_show_render.py` — T3.4..T3.5 (8 NEW CLI flag tests)
- `tests/unit/test_observability_prompt_counters.py` — T4.1..T4.4 NEW (10 tests across 5 test classes)
- `tests/unit/test_generate_prompts_doc.py` — T5.1..T5.2 NEW (10 tests across 5 test classes)
- `tests/unit/test_snapshot_graph_missing_error.py` — T6.1..T6.2 NEW (10 tests across 3 test classes)
- `tests/unit/test_cli_drift_events_{list,tail,stats}.py` — T2.4 (--strict flag tests; carried over from v1.0)
- `tests/unit/test_version.py` — Closeout (1-line assertion update to expect 1.1.0)