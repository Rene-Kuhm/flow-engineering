<!-- tasks.md: v0.9.0-hardening. Source: sdd-tasks sub-agent. -->
# Tasks: v0.9.0-hardening

**Change:** `v0.9.0-hardening` (BREAKING — compat shim removal follow-up to `drift-hardening` v0.8.0)
**Builds on:** `proposal.md` (#708) — REQ-V9.1..V9.5 + 22-task plan → consolidated to 19 per-task TDD tasks; `explore.md` (#707) — 3 compat shim definitions + 25 test sites identified; `drift-hardening` `verify-report.md` W1/W2/W3 + `apply-progress/merged.md` strict-TDD precedent
**Date:** 2026-06-28
**Status:** EXPLORED + PROPOSED → ready for sdd-apply (single PR, 3 sequential sub-batches of strict TDD)
**Strict TDD:** ON (per `drift-hardening` `apply-progress/merged.md` line 8 precedent; RED → GREEN → REFACTOR per task with the "shim-still-exists" RED test before each delete)
**Delivery strategy:** single-pr (per proposal #708 §"Approach matrix" Approach A; ~100 prod removed + ~140 test removed = ~240 net delta; well under 400 LOC chained-PR threshold)

> **REQ-label note**: REQ-V9.1 = W1 `Finding.from_legacy` removal; REQ-V9.2 = W1 `DriftReport.from_legacy` removal; REQ-V9.3 = W3 `classify_binding_legacy` removal; REQ-V9.4 = W1 enforcement via `Finding.__post_init__`; REQ-V9.5 = docs + meta + version bump + Drift note. Mirrors canonical REQ-55..59 numbering from `drift-hardening` (proposal §"Modified Capabilities").

> **Pre-decided by orchestrator (per brief)**: W2 fork = **Option B** (accept deviation + Drift note in design.md); per-task strict TDD; single PR.

---

```yaml
status: success
confidence: high
total_tasks: 19  # T1.1..T1.6 + T2.1..T2.6 + T3.1..T3.6
pr_split: single PR (3 sequential sub-batches of strict TDD)
forecast_loc_production: ~100 removed + ~15 added = ~85 net removed
forecast_loc_test: ~140 removed + ~50 added = ~90 net removed
forecast_loc_grand_total: ~240 net delta  # well under 400-line chained-PR threshold
forecast_loc_realistic_x5_7: ~1370  # per drift-hardening precedent multiplier
sub_batches:
  sub_batch_a: 6 tasks   # T1.1..T1.6   — REQ-V9.1 + REQ-V9.2 W1 removal
  sub_batch_b: 6 tasks   # T2.1..T2.6   — REQ-V9.3 W3 removal + REQ-V9.4 W1 enforcement
  sub_batch_c: 7 tasks   # T3.1..T3.7   — REQ-V9.5 docs + meta + version bump
review_workload_forecast:
  single_pr_400_line_budget_risk: low
  chained_pr_recommendation: no
  decision_needed_before_apply: no
strict_tdd: on
bdd_feature_files: 0 NEW  # shim removal + type-contract enforcement only; no BDD surface changes
bdd_scenarios: 0 NEW      # all scenarios already exist in openspec/specs/decision-drift/spec.md
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v0.9.0-hardening\tasks.md
next_recommended: sdd-apply v0.9.0-hardening sub-batch A (T1.1..T1.6)
```

---

## PR Split

| PR | REQs | Tasks | LOC forecast | LOC realistic (×5.7) |
|----|------|-------|--------------|----------------------|
| **PR#1** (v0.9.0-hardening) | REQ-V9.1..V9.5 (all 5) | T1.1..T3.7 (19 tasks across 3 sequential sub-batches) | ~85 prod removed + ~90 test removed = ~175 net | ~1 370 |
| **Total** | **5 REQs** | **19 tasks** | **~175** | **~1 370** |

**Rationale**: Single PR per proposal #708 Approach A. Bundles REQ-V9.1 (W1 `Finding.from_legacy` removal) + REQ-V9.2 (W1 `DriftReport.from_legacy` removal) + REQ-V9.3 (W3 `classify_binding_legacy` removal) + REQ-V9.4 (W1 enforcement via `Finding.__post_init__`) + REQ-V9.5 (docs + meta + Drift note) into one v0.9.0 release. Total net delta ~175 LOC — well under the 400-line chained-PR threshold. The 3 compat shims are thematically unified (all v0.8.0 1-release deprecation paths with the same removal deadline); splitting into chained PRs would force each PR to re-import the legacy shape context the previous PR just deleted — needless friction.

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Total tasks | 19 (T1.1..T1.6, T2.1..T2.6, T3.1..T3.7) |
| Forecast LOC production | ~100 removed + ~15 added = ~85 net removed |
| Forecast LOC test | ~140 removed + ~50 added = ~90 net removed |
| Forecast LOC grand total | **~175 net delta** |
| Forecast LOC realistic (×5.7 TDD multiplier per `drift-hardening` §"Structured Metadata") | **~1 370** |
| BDD feature files | 0 NEW |
| BDD scenarios | 0 NEW |
| New source files | 0 |
| Modified source files | 1 (`src/flow_engineering/decision_drift.py`) + 6 tests (`test_decision_drift.py`, `test_cli_watch_drift.py`, `test_daemon_drift_events.py`, `test_decision_drift_v080_migration.py`, plus 2 NEW v0.9.0 RED fixture tests) |
| Modified docs/meta files | 4 (`openspec/specs/decision-drift/spec.md`, `CHANGELOG.md`, `pyproject.toml`, `archive/2026-06-27-drift-hardening/design.md`) + 6 SKILL.md runtime files (outside repo) |
| Chained PRs recommended | **No** (single PR per proposal #708 §"Approach matrix"; ~175 net well below 400-line threshold) |
| Chain strategy | N/A (single PR; per-commit work-unit splits per `work-unit-commits`) |
| 400-line budget risk | **Low** (single PR ~175 net / ~1 370 realistic — mitigated by 10-12 work-unit commits each ≤30 LOC delta) |
| Decision needed before apply | **No** (single-pr + W2 Option B pre-decided by orchestrator brief) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: N/A (single PR)
400-line budget risk: Low

### Forecast rationale

| Signal | Source | Value |
|---|---|---|
| Production LOC removed | `decision_drift.py` DELETE `Finding.from_legacy` (~41 LOC) + DELETE `DriftReport.from_legacy` (~55 LOC) + DELETE `classify_binding_legacy` (~19 LOC) + REMOVE 3 `# type: ignore` comments (3 LOC) = ~118 LOC removed | ~100 prod removed |
| Production LOC added | `Finding.__post_init__` (~15 LOC) per verify-report W1 recommended fix | ~15 prod added |
| Test LOC removed | DELETE 3 `Finding.from_legacy` fixtures (~42 LOC) + DELETE 3 `DriftReport.from_legacy` fixtures (~42 LOC) + DELETE `test_classify_binding_legacy_3arg_emits_deprecation_warning` (~12 LOC) + migrate 8 `DriftReport(scanned_at=0.0)` + 2 `Finding(decision_id="<str>")` + 10 `classify_binding_legacy` call sites = ~20 LOC net + delete dead `_id_map` helper (~5 LOC) + update `test_decision_drift_v080_migration.py` docstring (~5 LOC) | ~140 test removed |
| Test LOC added | 4 NEW RED fixtures (1 per shim-removed + 1 for `__post_init__`) + 1 NEW "shim-still-exists" RED test for W3 + migration docstring update | ~50 test added |
| Realistic ×5.7 TDD multiplier | `drift-hardening` precedent (design §"Structured Metadata"): strict-TDD band ×5.7 | ×5.7 → ~1 370 grand total realistic |
| Per-delegation batch ceiling | `apply-batches-split-into-6-tasks-per-delegation` pattern (Engram #112): ≤3 tasks OR ≤150 LOC prod per delegation | All sub-batches ≤6 tasks / ≤80 LOC prod — well within ceiling |
| Risk: silent regression if a test site is missed | Per-task TDD with "shim-still-exists" RED test before each delete (catches missing migrations via `AttributeError`); grep audit before PR open | **MED** — mitigated by per-task TDD + grep audit |
| Risk: W2 deviation (Option B) leaves spec/implementation mismatch | Drift note in `archive/2026-06-27-drift-hardening/design.md` documents decision + links to CHANGELOG v0.8.0 step 3 | **LOW** — already documented in explore line 161 |
| Risk: 6 SKILL.md runtime files must be updated atomically | `drift-hardening` T4.5.c precedent (`verify-report.md` line 81) — `--allow-empty` commit pattern at d5f2147 | **LOW** — established workflow |

### Suggested Work Units

Single PR (no chained split per proposal #708 + design §"Approach matrix"). Per-delegation batching (≤3 tasks / ≤150 LOC prod) still required at apply phase because delegate runtime is ~15 min.

| Apply sub-batch | Tasks | Production LOC | Test LOC | Why |
|-----------------|-------|----------------|----------|-----|
| **A** | T1.1 + T1.2 + T1.3 | ~41 removed | ~10 added + ~42 deleted | W1 `Finding.from_legacy` removal + 2 test migrations + 3 fixture deletions |
| **B** | T1.4 + T1.5 + T1.6 | ~55 removed | ~10 added + ~42 deleted | W1 `DriftReport.from_legacy` removal + 8 test migrations + 3 fixture deletions |
| **C** | T2.1 + T2.2 + T2.3 | ~19 removed | ~5 added + ~20 deleted | W3 `classify_binding_legacy` removal + 10 call site migrations + 1 fixture deletion + dead `_id_map` helper removal |
| **D** | T2.4 + T2.5 + T2.6 | ~15 added - 3 removed | ~15 added | W1 enforcement via `Finding.__post_init__` + cleanup 3 `# type: ignore` + 1 RED fixture for `__post_init__` |
| **E** | T3.1 + T3.2 + T3.3 | docs only | ~10 added | spec.md migration note + CHANGELOG v0.9.0 + pyproject bump 0.8.1 → 0.9.0 |
| **F** | T3.4 + T3.5 + T3.6 + T3.7 | docs only | 0 | Drift note in archived design.md + 6 SKILL.md runtime updates + ruff --fix + apply-progress closeout + commit |

---

## Dependency Graph

```
Sub-batch A — REQ-V9.1 W1 Finding.from_legacy removal (3 tasks)
  T1.1 (RED test asserting Finding.from_legacy is AttributeError)
    ↓
  T1.2 (GREEN: delete Finding.from_legacy + Finding docstring 1 line ref)
    ↓
  T1.3 (REFACTOR: migrate 2 Finding(str) test sites + delete 3 from_legacy fixtures + KEEP 1 type-contract smoke)

Sub-batch A.5 — REQ-V9.2 W1 DriftReport.from_legacy removal (3 tasks)
  T1.4 (RED test asserting DriftReport.from_legacy is AttributeError)
    ↓
  T1.5 (GREEN: delete DriftReport.from_legacy + DriftReport docstring 1 line ref)
    ↓
  T1.6 (REFACTOR: migrate 8 DriftReport(scanned_at=0.0) test sites + delete 3 from_legacy fixtures + KEEP 2 type-contract smokes + update file docstring)

Sub-batch B — REQ-V9.3 W3 classify_binding_legacy removal (3 tasks)
  T2.1 (RED test asserting classify_binding_legacy is NameError)
    ↓
  T2.2 (GREEN: delete classify_binding_legacy + module docstring 1 line ref)
    ↓
  T2.3 (REFACTOR: migrate 10 test_decision_drift.py call sites + delete 1 legacy fixture + delete _id_map helper at lines 61-62)

Sub-batch B.5 — REQ-V9.4 W1 enforcement via Finding.__post_init__ (3 tasks)
  T2.4 (RED test asserting Finding(decision_id="42") raises TypeError)
    ↓
  T2.5 (GREEN: add Finding.__post_init__ ~15 LOC)
    ↓
  T2.6 (REFACTOR: remove 3 # type: ignore comments at lines 759/772/792 + mypy clean verify)

Sub-batch C — REQ-V9.5 docs + meta + Drift note + closeout (7 tasks)
  T3.1 (openspec/specs/decision-drift/spec.md: replace v0.8.0 migration note with v0.9.0 final note)
  T3.2 (CHANGELOG v0.9.0 entry under ## [0.9.0] - 2026-06-XX with ### Changed (BREAKING) + ### Removed + ### Migration)
  T3.3 (pyproject.toml: version = "0.9.0")
  T3.4 (Drift note appended to archive/2026-06-27-drift-hardening/design.md after line 491)
  T3.5 (6 SKILL.md runtime files: remove "1-release shim" qualifier per verify-report W8 line 81 precedent)
  T3.6 (uv run ruff check --fix on changed files per drift-hardening T4.5.c precedent)
  T3.7 (Apply-progress closeout + commit)

[Apply sub-batch merge after each sub-batch → final PR merge]
```

---

## Out-of-Scope Reminders (do NOT pull into tasks)

These 13 items are explicitly deferred per proposal §"Carry-forwards explicitly NOT touched by this change" — apply must NOT introduce code for them:

- **`DriftEvent.decision_id: str` → `int` JSONL wire format change** (verify-report S1) — deferred to v1.0; JSONL consumed by 3rd-party tools (jq scripts, dashboards); not a v0.9.0 scope
- **`DriftEventLog` JSONL rotation hardening** (`os.fsync` + atomic-write; verify-report W7) — deferred to v1.1; 10 MB rotation threshold already shipped in v0.8.0 (REQ-55)
- **`flow drift events` CLI read-side command** (verify-report S2) — deferred to v1.0; operators use `cat ~/.flow-engineering/drift_events.jsonl | jq` in v0.8.0/v0.9.0
- **`flow drift events --format=prometheus|csv`** (verify-report S2) — deferred to v1.0
- **Cross-project federation for drift events** (`flow drift events --project=<key>`) — deferred to `federated-drift-events` follow-up
- **OpenTelemetry push for drift events** — deferred; Prometheus textfile (REQ-38) covers v1 export
- **Tech debt residuals** (4 ruff warnings + 13 mypy errors in `decision_drift.py`) — the 3 `# type: ignore` cleanup at T2.6 reduces by 3; 10 residuals remain; deferred to v1.0 tech-debt follow-up
- **`Finding.__post_init__` removal itself** — deferred to v1.0; in v0.9.0 the `__post_init__` IS the contract (the W1 shim is gone)
- **Per-finding `graph_unavailable` classification refinement** — `classify_binding` handles at report level only; v2
- **Auto-daily snapshot trigger** — already deferred in `graph-snapshots` archive; unchanged
- **Snapshot export/import** — already deferred in `graph-snapshots` archive; unchanged
- **W2 rename Option A (`graph_unavailable` → `unable_to_verify`)** — REJECTED per orchestrator Option B pre-decision; this is the W2 drift note in design.md
- **JSONL `os.fsync` atomic-write hardening** — deferred to v1.1; would require DriftEventLog surgery outside v0.9.0 scope

---

## Patterns Honored

- `apply-batches-split-into-6-tasks-per-delegation` (Engram #112): each apply sub-batch ≤3 tasks / ≤150 LOC prod
- `apply-under-strict-tdd-grows-5-6x-beyond-forecast` (#113): design ×5.7 multiplier is the project-specific band; ~1 370 realistic vs ~175 forecast
- `work-unit-commits` skill: 10-12 work-unit commits per PR, each ≤30 LOC delta
- `stacked-to-main-requires-merging-prior-pr-before-next-apply` (#114): N/A here (single PR)
- `drift-hardening` T4.5.c `--allow-empty` commit precedent (verify-report line 81 + commit d5f2147): 6 SKILL.md runtime files updated atomically
- `decision-code-linking` archive-report #119 S3 precedent: 5-6× strict-TDD multiplier applied
- `drift-hardening` per-task TDD precedent (apply-progress/merged.md line 8 + tasks.md Batch D): RED test asserts "shim-still-exists" before each delete (catches missing migrations via `AttributeError`)

---

## Goal

Remove the 3 v0.8.0 1-release compat shims (`Finding.from_legacy`, `DriftReport.from_legacy`, `classify_binding_legacy`) per CHANGELOG v0.8.0 lines 43/44/46/74 operator commitment. Accept the W2 deviation (`graph_unavailable` canonical + `unable_reason` NEW field per Option B) via Drift note in archived design.md. Add `Finding.__post_init__` str→int enforcement per verify-report W1 recommended fix. Bump `pyproject.toml` 0.8.1 → 0.9.0. Update CHANGELOG + 6 SKILL.md runtime files + `openspec/specs/decision-drift/spec.md` migration note. ~85 prod LOC removed + ~15 prod LOC added + ~90 test LOC removed = ~175 net delta. Single PR, well under 400 LOC chained-PR threshold.

## Scope

### In scope (single PR, 3 sub-batches)

- **Sub-batch A (W1 removal, 6 tasks)**: `Finding.from_legacy` + `DriftReport.from_legacy` classmethod deletions + 10 direct-legacy test site migrations + 6 v0.8.0 migration fixture deletions
- **Sub-batch B (W3 removal + W1 enforcement, 6 tasks)**: `classify_binding_legacy` 3-arg wrapper deletion + 10 call site migrations + `_id_map` test helper deletion + `Finding.__post_init__` enforcement (~15 LOC) + 3 `# type: ignore` cleanup
- **Sub-batch C (Docs + meta, 7 tasks)**: spec.md migration note + CHANGELOG v0.9.0 entry + pyproject 0.8.1→0.9.0 + Drift note in archived design.md + 6 SKILL.md runtime updates + ruff --fix + closeout

### Out of scope

See "Out-of-Scope Reminders" section above.

---

## Sub-batch A — W1 removal: `Finding.from_legacy` + `DriftReport.from_legacy` (6 tasks)

### T1.1 — RED: add failing test asserting `Finding.from_legacy` is removed (REQ-V9.1)

- **Type:** test (RED — RED fixture for shim-still-exists check)
- **Strict TDD:**
  - RED: `tests/unit/test_decision_drift_v090_hardening.py::test_finding_from_legacy_attribute_removed` — asserts `Finding.from_legacy` does NOT exist (`hasattr(Finding, "from_legacy") == False`); calling `Finding.from_legacy(decision_id=42, ...)` raises `AttributeError`
  - GREEN: N/A (no production code change yet — shim still exists)
  - REFACTOR: N/A (single test method; ~10 LOC)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift_v090_hardening.py::test_finding_from_legacy_attribute_removed -v` exits 1 with `AttributeError: type object 'Finding' has no attribute 'from_legacy'` (RED state — shim still exists)
- **LOC forecast:** ~10 tests + 0 prod = ~10

### T1.2 — GREEN: delete `Finding.from_legacy` classmethod (REQ-V9.1)

- **Type:** code (GREEN — shim deletion)
- **Strict TDD:**
  - RED: T1.1 RED fixture (already failing)
  - GREEN: `src/flow_engineering/decision_drift.py:77-117` — DELETE the `Finding.from_legacy` classmethod (~41 LOC); REMOVE the docstring reference at line 68 (`inputs are accepted via :meth:`from_legacy`...`)
  - REFACTOR: N/A (single delete; no cleanup needed beyond docstring line)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift_v090_hardening.py::test_finding_from_legacy_attribute_removed -v` exits 0 (GREEN state — shim gone)
  - `uv run --frozen pytest tests/unit/test_decision_drift_v080_migration.py -v` shows 3 `test_finding_from_legacy_*` fixtures now failing with `AttributeError` (expected; T1.3 deletes them)
- **LOC forecast:** ~41 prod removed + 0 tests = ~41

### T1.3 — REFACTOR: migrate 2 direct `Finding(str)` test sites + delete 3 `Finding.from_legacy` fixtures (REQ-V9.1)

- **Type:** test refactor (migrate direct-legacy callers + delete deprecated fixtures)
- **Strict TDD:**
  - RED: N/A (GREEN state from T1.2)
  - GREEN: N/A (no production code change)
  - REFACTOR:
    - `tests/unit/test_decision_drift.py:196` — `Finding(decision_id="obs-1", ...)` → `Finding(decision_id=1, ...)`
    - `tests/unit/test_cli_watch_drift.py:99` — `Finding(decision_id="1", ...)` → `Finding(decision_id=1, ...)`
    - `tests/unit/test_decision_drift_v080_migration.py:104-146` — DELETE 3 `test_finding_from_legacy_*` fixtures (lines 104-119, 122-131, 134-146)
    - `tests/unit/test_decision_drift_v080_migration.py:1-5` — UPDATE file-level docstring (per OQ-5: "Canonical type-contract smokes for `decision_drift.Finding` + `DriftReport`. After v0.9.0 these are the only remaining tests in this file; the v0.8.0 migration shim tests were deleted when their compat shims were removed.")
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift.py tests/unit/test_cli_watch_drift.py -v` exits 0 (migrated sites pass)
  - `uv run --frozen pytest tests/unit/test_decision_drift_v080_migration.py -v` shows 3 canonical type-contract smokes pass (decision_id int + scanned_at str + unable_reason default) + 3 `Finding.from_legacy_*` fixtures gone + 3 `DriftReport.from_legacy_*` fixtures still present (deleted in T1.6)
  - `uv run --frozen pytest --collect-only -q` shows `1232 - 3 = 1229` tests collected (3 deleted)
- **LOC forecast:** ~5 tests modified + ~42 tests deleted + 0 prod = ~47

### T1.4 — RED: add failing test asserting `DriftReport.from_legacy` is removed (REQ-V9.2)

- **Type:** test (RED — RED fixture for shim-still-exists check)
- **Strict TDD:**
  - RED: `tests/unit/test_decision_drift_v090_hardening.py::test_drift_report_from_legacy_attribute_removed` — asserts `DriftReport.from_legacy` does NOT exist (`hasattr(DriftReport, "from_legacy") == False`); calling `DriftReport.from_legacy(scanned_at=0.0, ...)` raises `AttributeError`
  - GREEN: N/A (no production code change yet — shim still exists)
  - REFACTOR: N/A (single test method; ~10 LOC)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift_v090_hardening.py::test_drift_report_from_legacy_attribute_removed -v` exits 1 with `AttributeError: type object 'DriftReport' has no attribute 'from_legacy'` (RED state)
- **LOC forecast:** ~10 tests + 0 prod = ~10

### T1.5 — GREEN: delete `DriftReport.from_legacy` classmethod (REQ-V9.2)

- **Type:** code (GREEN — shim deletion)
- **Strict TDD:**
  - RED: T1.4 RED fixture (already failing)
  - GREEN: `src/flow_engineering/decision_drift.py:143-197` — DELETE the `DriftReport.from_legacy` classmethod (~55 LOC); this also removes the W2 `unable_to_verify` kwarg shim; REMOVE the docstring reference at line 127 (`inputs are accepted via :meth:`from_legacy`...`) + the helper docstring reference at line 203 (`Used by :meth:`DriftReport.from_legacy` and other v0.7.x migration...`)
  - REFACTOR: N/A (single delete)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift_v090_hardening.py::test_drift_report_from_legacy_attribute_removed -v` exits 0 (GREEN state)
  - `uv run --frozen pytest tests/unit/test_decision_drift_v080_migration.py -v` shows 3 `test_drift_report_from_legacy_*` fixtures now failing with `AttributeError` (expected; T1.6 deletes them)
- **LOC forecast:** ~55 prod removed + 0 tests = ~55

### T1.6 — REFACTOR: migrate 8 direct `DriftReport(scanned_at=0.0)` test sites + delete 3 `DriftReport.from_legacy` fixtures (REQ-V9.2)

- **Type:** test refactor (migrate direct-legacy callers + delete deprecated fixtures)
- **Strict TDD:**
  - RED: N/A (GREEN state from T1.5)
  - GREEN: N/A (no production code change)
  - REFACTOR:
    - `tests/unit/test_decision_drift.py:208` — `DriftReport(scanned_at=0.0, ...)` → `DriftReport(scanned_at="1970-01-01T00:00:00Z", ...)`
    - `tests/unit/test_decision_drift.py:535` — same migration
    - `tests/unit/test_cli_watch_drift.py:200` — same migration
    - `tests/unit/test_cli_watch_drift.py:253` — same migration
    - `tests/unit/test_daemon_drift_events.py:151` — same migration
    - `tests/unit/test_daemon_drift_events.py:175` — same migration
    - `tests/unit/test_daemon_drift_events.py:204` — same migration
    - `tests/unit/test_daemon_drift_events.py:289` — same migration
    - `tests/unit/test_decision_drift_v080_migration.py:165-206` — DELETE 3 `test_drift_report_from_legacy_*` fixtures (lines 165-177, 180-192, 195-206)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift.py tests/unit/test_cli_watch_drift.py tests/unit/test_daemon_drift_events.py -v` exits 0 (migrated sites pass)
  - `uv run --frozen pytest tests/unit/test_decision_drift_v080_migration.py -v` shows 3 canonical smokes pass (decision_id int + scanned_at str + unable_reason default)
  - `uv run --frozen pytest --collect-only -q` shows `1229 - 3 = 1226` tests collected (3 more deleted)
- **LOC forecast:** ~8 tests modified + ~42 tests deleted + 0 prod = ~50

---

## Sub-batch B — W3 removal + W1 enforcement (6 tasks)

### T2.1 — RED: add failing test asserting `classify_binding_legacy` is removed (REQ-V9.3)

- **Type:** test (RED — RED fixture for shim-still-exists check)
- **Strict TDD:**
  - RED: `tests/unit/test_decision_drift_v090_hardening.py::test_classify_binding_legacy_attribute_removed` — asserts `classify_binding_legacy` does NOT exist in the `decision_drift` module namespace (`not hasattr(decision_drift, "classify_binding_legacy")`); calling `classify_binding_legacy(binding, nodes, id_map)` raises `NameError`
  - GREEN: N/A (no production code change yet — wrapper still exists)
  - REFACTOR: N/A (single test method; ~10 LOC)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift_v090_hardening.py::test_classify_binding_legacy_attribute_removed -v` exits 1 with `NameError: name 'classify_binding_legacy' is not defined` (RED state)
- **LOC forecast:** ~10 tests + 0 prod = ~10

### T2.2 — GREEN: delete `classify_binding_legacy` 3-arg wrapper (REQ-V9.3)

- **Type:** code (GREEN — wrapper deletion)
- **Strict TDD:**
  - RED: T2.1 RED fixture (already failing)
  - GREEN: `src/flow_engineering/decision_drift.py:267-285` — DELETE the `classify_binding_legacy(binding, current_nodes, current_id_map)` function (~19 LOC); REMOVE the docstring reference at line 221 (`is retained as :func:`classify_binding_legacy` for one release with a...`)
  - REFACTOR: N/A (single delete)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift_v090_hardening.py::test_classify_binding_legacy_attribute_removed -v` exits 0 (GREEN state)
  - `uv run --frozen pytest tests/unit/test_decision_drift.py -v` shows 10 `test_classify_binding_legacy_*` call sites now failing with `NameError` (expected; T2.3 migrates them)
- **LOC forecast:** ~19 prod removed + 0 tests = ~19

### T2.3 — REFACTOR: migrate 10 call sites + delete 1 fixture + delete `_id_map` helper (REQ-V9.3)

- **Type:** test refactor (migrate 3-arg callers + delete deprecated fixture + delete dead helper)
- **Strict TDD:**
  - RED: N/A (GREEN state from T2.2)
  - GREEN: N/A (no production code change)
  - REFACTOR:
    - `tests/unit/test_decision_drift.py:74` (test_classify_still_valid_basic) — drop `id_map = _id_map(...)` helper line + change `classify_binding_legacy(binding, nodes, id_map)` → `classify_binding(binding, nodes)`
    - `tests/unit/test_decision_drift.py:83` — same migration
    - `tests/unit/test_decision_drift.py:95` — same migration
    - `tests/unit/test_decision_drift.py:104` — same migration
    - `tests/unit/test_decision_drift.py:116` — same migration
    - `tests/unit/test_decision_drift.py:125` — same migration
    - `tests/unit/test_decision_drift.py:135` — same migration
    - `tests/unit/test_decision_drift.py:142` — same migration
    - `tests/unit/test_decision_drift.py:173` — same migration
    - `tests/unit/test_decision_drift.py:188` — same migration
    - `tests/unit/test_decision_drift_v080_migration.py:243-255` — DELETE `test_classify_binding_legacy_3arg_emits_deprecation_warning`
    - `tests/unit/test_decision_drift.py:61-62` — DELETE the `_id_map` test helper (now dead; only used by the 10 migrated tests per OQ-4)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift.py -v` exits 0 (all 10 migrated call sites pass on 2-arg `classify_binding`)
  - `uv run --frozen pytest tests/unit/test_decision_drift_v080_migration.py -v` shows `test_classify_binding_legacy_3arg_*` gone + 3 canonical smokes still pass
  - `uv run --frozen pytest --collect-only -q` shows `1226 - 1 - 1 = 1224` tests collected (1 fixture + 1 dead helper test removed)
  - `rg "classify_binding_legacy" src/ tests/` exits 0 matches (no remaining references)
- **LOC forecast:** ~10 tests modified + ~12 tests deleted + ~5 tests (helper) deleted + 0 prod = ~27

### T2.4 — RED: add failing test asserting `Finding.__post_init__` rejects str inputs (REQ-V9.4)

- **Type:** test (RED — RED fixture for W1 enforcement contract)
- **Strict TDD:**
  - RED: `tests/unit/test_decision_drift_v090_hardening.py::test_finding_constructor_rejects_str_decision_id` — asserts `Finding(decision_id="42", ...)` raises `TypeError` (NOT `DeprecationWarning` + coercion); also asserts `Finding(decision_id=True, ...)` raises `TypeError` (bool is int subclass; must reject per proposal §"Code sketch")
  - GREEN: N/A (no production code change yet — `__post_init__` not yet implemented)
  - REFACTOR: N/A (single test method; ~15 LOC; 2 RED fixtures)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift_v090_hardening.py::test_finding_constructor_rejects_str_decision_id -v` exits 1 with `TypeError: Finding.decision_id must be int, got str` (RED state — `__post_init__` not yet implemented; current code accepts str via duck-typing)
- **LOC forecast:** ~15 tests + 0 prod = ~15

### T2.5 — GREEN: add `Finding.__post_init__` enforcement (~15 LOC, REQ-V9.4)

- **Type:** code (GREEN — W1 enforcement)
- **Strict TDD:**
  - RED: T2.4 RED fixtures (already failing)
  - GREEN: `src/flow_engineering/decision_drift.py:~75-85` — ADD `Finding.__post_init__` method per proposal §"Code sketch" lines 239-245: `if not isinstance(self.decision_id, int) or isinstance(self.decision_id, bool): raise TypeError(f"Finding.decision_id must be int, got {type(self.decision_id).__name__}")` (~15 LOC incl. docstring + type annotation)
  - REFACTOR: N/A (single addition)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_decision_drift_v090_hardening.py::test_finding_constructor_rejects_str_decision_id -v` exits 0 (GREEN state — `__post_init__` rejects str/bool)
  - `uv run --frozen pytest tests/unit/test_decision_drift_v080_migration.py::test_finding_decision_id_is_int_type -v` exits 0 (canonical `decision_id=42` smoke still passes)
- **LOC forecast:** ~15 prod added + 0 tests = ~15

### T2.6 — REFACTOR: remove 3 `# type: ignore` comments + mypy clean verify (REQ-V9.4)

- **Type:** code cleanup (REFACTOR — type narrowing becomes unnecessary once `Finding` rejects str)
- **Strict TDD:**
  - RED: N/A (GREEN state from T2.5)
  - GREEN: N/A (no production code change beyond comment removal)
  - REFACTOR:
    - `src/flow_engineering/decision_drift.py:759` — REMOVE `# type: ignore[arg-type]` comment (the str-coercion site in `_append_drift_events` is now unreachable since `Finding.__post_init__` rejects str)
    - `src/flow_engineering/decision_drift.py:772` — REMOVE `# type: ignore[arg-type]` comment (same)
    - `src/flow_engineering/decision_drift.py:792` — REMOVE `# type: ignore[comparison-overlap]` comment (same)
- **Acceptance:**
  - `uv run mypy src/flow_engineering/decision_drift.py 2>&1 | wc -l` shows ≤10 errors (down from 13 in v0.8.0; 3 residuals expected at lines 759/772/792 if not removed — verify-report W9 carry-forward)
  - `uv run --frozen pytest tests/unit -v` exits 0 (all migrated tests pass; no regression)
  - `uv run --frozen pytest --collect-only -q` shows `1224` tests collected (no test count delta)
  - `rg "# type: ignore" src/flow_engineering/decision_drift.py` shows ≤3 matches (down from 3 expected — i.e., zero in the str-coercion sites; others may remain as residual tech debt)
- **LOC forecast:** 0 prod (comment removal only, ~3 LOC) + 0 tests = ~3

---

## Sub-batch C — Docs + meta + Drift note + closeout (7 tasks)

### T3.1 — Update `openspec/specs/decision-drift/spec.md` v0.9.0 migration note (REQ-V9.5)

- **Type:** docs (replace v0.8.0 migration note with v0.9.0 final note)
- **Strict TDD:** N/A (docs-only — no production code, no tests)
- **LOC:** ~18 docs
- **Files:**
  - `openspec/specs/decision-drift/spec.md:14-41` — REPLACE the `## v0.8.0 migration note (REQ-56 W8 / REQ-57)` section (lines 14-41, ~28 LOC) with `## v0.9.0 final note (REQ-V9.1..V9.5)` section (~18 LOC): "Shims removed in v0.9.0. **No migration path.** `Finding.decision_id: int` is required (str raises `TypeError` via `Finding.__post_init__`); `DriftReport.scanned_at: str` ISO 8601 UTC Z-suffixed is required (float raises `TypeError` since no compat shim exists); `classify_binding(ref, graph_nodes)` 2-arg is the only canonical entry point (3-arg raises `TypeError`). `DriftReport.graph_unavailable: bool` stays canonical (per W2 Option B); `unable_reason: str | None` stays canonical (NEW in v0.8.0)."
- **Acceptance:**
  - `rg "from_legacy|classify_binding_legacy" openspec/specs/decision-drift/spec.md` shows 0 matches (all references removed)
  - `rg "v0.9.0|REQ-V9" openspec/specs/decision-drift/spec.md` shows the new section + REQ-V9.X cross-references
- **LOC forecast:** ~18 docs modified + 0 tests = ~18

### T3.2 — CHANGELOG v0.9.0 entry under `## [0.9.0] - 2026-06-XX` (REQ-V9.5)

- **Type:** docs (BREAKING section + Removed section + Migration section)
- **Strict TDD:** N/A (docs-only)
- **LOC:** ~35 CHANGELOG
- **Files:**
  - `CHANGELOG.md` (modify — INSERT `## [0.9.0] - 2026-06-XX` section above `[0.8.1]` line 7 with 3 subsections:
    - `### Changed (BREAKING)`: "Removed v0.8.0 1-release compat shims (`Finding.from_legacy`, `DriftReport.from_legacy`, `classify_binding_legacy`); `Finding.__post_init__` now raises `TypeError` on str `decision_id` (no `DeprecationWarning`, no `int()` coercion); `DriftReport(scanned_at=<float>)` raises `TypeError` (no compat shim exists); `classify_binding(ref, graph_nodes, current_id_map)` 3-arg raises `TypeError`." (~5 lines)
    - `### Removed`: "v0.8.0 compat shims — `Finding.from_legacy`, `DriftReport.from_legacy`, `classify_binding_legacy`. Removed per the 1-release commitment in v0.8.0 entry." (~3 lines)
    - `### Migration`: "Replace `Finding(decision_id='42')` with `Finding(decision_id=42)`; replace `DriftReport(scanned_at=0.0)` with `DriftReport(scanned_at='1970-01-01T00:00:00Z')`; replace `classify_binding_legacy(binding, nodes, id_map)` with `classify_binding(binding, nodes)`. No automatic migration — v0.9.0 is a hard break." (~4 lines))
- **Acceptance:**
  - `rg "^## \[0\.9\.0\]" CHANGELOG.md` shows 1 match
  - `rg "### Migration|### Removed|### Changed \(BREAKING\)" CHANGELOG.md` shows the 3 v0.9.0 subsections
  - `flow --version` prints `flow 0.9.0` (post T3.3 bump)
- **LOC forecast:** ~35 CHANGELOG added + 0 tests = ~35

### T3.3 — pyproject.toml version bump `0.8.1` → `0.9.0` (REQ-V9.5)

- **Type:** docs + meta
- **Strict TDD:** N/A (docs-only)
- **LOC:** ~1 line
- **Files:**
  - `pyproject.toml:3` — `version = "0.8.1"` → `version = "0.9.0"` (per proposal §"Breaking-change policy"; SemVer minor for public API break)
- **Acceptance:**
  - `rg "^version" pyproject.toml` shows `version = "0.9.0"`
  - `uv run flow --version` prints `flow 0.9.0` (or equivalent; depends on CLI version flag)
  - `uv run --frozen pytest --collect-only -q` shows `1224` tests (no test count delta)
- **LOC forecast:** ~1 modified + 0 tests = ~1

### T3.4 — Drift note appended to `archive/2026-06-27-drift-hardening/design.md` (REQ-V9.5, W2 Option B)

- **Type:** docs (Drift note append; per proposal OQ-6 — append after line 491)
- **Strict TDD:** N/A (docs-only)
- **LOC:** ~10 docs
- **Files:**
  - `openspec/changes/archive/2026-06-27-drift-hardening/design.md` (modify — APPEND after line 491, within the existing `## Drift: implementation deviations from design` section, a 10-LOC resolution note documenting the W2 Option B decision: "**v0.9.0 resolution (REQ-V9.5)**: W2 deviation officially closed. `graph_unavailable: bool` stays canonical (impl chose opposite of design D2). `unable_reason: str | None` stays canonical (NEW in v0.8.0). No rename to `unable_to_verify` field per CHANGELOG v0.8.0 step 3 (`graph_unavailable: bool` retained as the canonical field name). The `unable_to_verify` enum value + `drift_unable_to_verify_total` counter name + CLI exit-code 2 wording all describe the terminal STATE, not the field — these stay unchanged. See `openspec/changes/v0.9.0-hardening/proposal.md` §"Open Questions OQ-1" for full rationale.")
- **Acceptance:**
  - `rg "v0\.9\.0 resolution \(REQ-V9\.5\)" openspec/changes/archive/2026-06-27-drift-hardening/design.md` shows 1 match
  - `rg "graph_unavailable" openspec/changes/archive/2026-06-27-drift-hardening/design.md` shows the existing Drift section + the appended resolution
- **LOC forecast:** ~10 docs added + 0 tests = ~10

### T3.5 — Update 6 SKILL.md runtime files (remove "1-release shim" qualifier per verify-report W8 line 81 precedent)

- **Type:** docs (atomic update per `drift-hardening` T4.5.c `--allow-empty` commit precedent)
- **Strict TDD:** N/A (docs-only)
- **LOC:** ~60 docs (6 files × ~10 LOC)
- **Files:**
  - `~/.config/opencode/skills/sdd-propose/SKILL.md:196` — UPDATE the v0.8.0 API note to read: "**v0.9.0 API (REQ-V9.1..V9.5)**: `decision_drift.Finding.decision_id` is `int` (rejected `str` via `__post_init__`); `decision_drift.DriftReport.scanned_at` is `str` ISO 8601 UTC Z-suffixed (rejected `float`); `DriftReport.graph_unavailable: bool` is the canonical field with `unable_reason: str | None` for structured diagnostics; `classify_binding(ref, graph_nodes)` is 2-arg. v0.8.0 compat shims (`Finding.from_legacy`, `DriftReport.from_legacy`, `classify_binding_legacy`) **removed in v0.9.0** — no migration path; hard break."
  - `~/.config/opencode/skills/sdd-design/SKILL.md:191` — same update
  - `~/.config/opencode/skills/sdd-tasks/SKILL.md:261` — same update
  - `~/.config/opencode/skills/sdd-apply/SKILL.md:243` — same update
  - `~/.config/opencode/skills/sdd-verify/SKILL.md:91` — same update
  - `~/.config/opencode/skills/sdd-archive/SKILL.md:172` — same update
- **Acceptance:**
  - `rg "1-release shim" C:/Users/insyd/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` shows 0 matches (all "1-release shim" qualifiers removed)
  - `rg "removed in v0.9.0" C:/Users/insyd/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` shows 6 matches (one per file)
- **LOC forecast:** ~60 docs modified + 0 tests = ~60

### T3.6 — Run `uv run ruff check --fix` on changed files

- **Type:** cleanup (auto-fix lint regressions; per `drift-hardening` T4.5.c precedent)
- **Strict TDD:** N/A (cleanup — verifies all existing tests still pass after auto-fix)
- **LOC:** ~0 prod (auto-fix) + ~20 verification
- **Files:**
  - `src/flow_engineering/decision_drift.py`, `tests/unit/test_decision_drift.py`, `tests/unit/test_decision_drift_v080_migration.py`, `tests/unit/test_decision_drift_v090_hardening.py` (NEW), `tests/unit/test_cli_watch_drift.py`, `tests/unit/test_daemon_drift_events.py` — `uv run ruff check --fix` auto-applies 3 auto-fixable lint fixes (I001 import sort, SIM105 contextlib.suppress, W292 trailing newline)
- **Acceptance:**
  - `uv run ruff check src/flow_engineering/decision_drift.py tests/unit/test_decision_drift.py tests/unit/test_decision_drift_v080_migration.py tests/unit/test_decision_drift_v090_hardening.py tests/unit/test_cli_watch_drift.py tests/unit/test_daemon_drift_events.py` exits 0
  - `uv run --frozen pytest tests/unit -v` exits 0 (all 1224 tests pass after auto-fix; no regression)
- **LOC forecast:** ~0 prod (auto-fix) + ~0 tests = ~0

### T3.7 — Apply-progress closeout + commit

- **Type:** docs (per-batch closeout per `drift-hardening` `apply-progress/merged.md` precedent)
- **Strict TDD:** N/A (docs)
- **LOC:** ~150 closeout docs
- **Files:**
  - `openspec/changes/v0.9.0-hardening/apply-progress/merged.md` (NEW — `Goal` + `Sub-batch summary` + `Files touched` + `Cumulative test delta` + `Deviations` + `Risks` + `Cluster unblocks` + `Cluster constrains` + `Next steps` + `Open follow-ups for v1.0+` + `Engram observation` sections; mirror `drift-hardening` `apply-progress/merged.md` structure; ~150 LOC)
  - Commit the merged PR with conventional commit message: `chore(v0.9.0-hardening): BREAKING — remove v0.8.0 1-release compat shims + enforce Finding.__post_init__ + close W2 deviation (REQ-V9.1..V9.5)`
- **Acceptance:**
  - `openspec/changes/v0.9.0-hardening/apply-progress/merged.md` exists + mirrors `drift-hardening` structure
  - `git log --oneline -20` shows the 10-12 work-unit commits from sub-batches A + B + C + the merge commit
  - `uv run --frozen pytest -v` exits 0 (full test suite: 1224 tests pass + 21 BDD scenarios pass)
  - Engram observation mirrored: `sdd/v0.9.0-hardening/apply-progress-merged` (architecture type, project scope)
- **LOC forecast:** ~150 docs added + 0 tests = ~150

---

## Risks

| # | Risk | Likelihood | Mitigation |
|---|------|------------|------------|
| 1 | **Silent regression** if a test site that passes legacy values (str `decision_id`, float `scanned_at`, 3-arg `classify_binding_legacy`) is missed in the migration → the test suite still passes GREEN but production callers break at import time | MED | Per-task TDD with the "shim-still-exists" RED test before each delete (catches missing migrations via `AttributeError`/`NameError`); grep audit before PR open (`rg "Finding\(" tests/ -n` for str inputs, `rg "scanned_at=0\.0" tests/ -n` for float inputs, `rg "classify_binding_legacy" tests/ -n` for 3-arg callers) |
| 2 | **Existing operators on v0.8.0/v0.8.1 will hit `ImportError` or `TypeError`** after upgrading to v0.9.0 if they imported the compat shims | MED | CHANGELOG v0.9.0 `### Migration` section lists the exact replacements; the v0.8.0 → v0.9.0 window was a 1-release operator commitment per CHANGELOG v0.8.0 lines 43/44/46/74; the 6 SKILL.md runtime files are updated atomically (per `drift-hardening` T4.5.c precedent); project has no third-party consumers per Engram #92 `sdd-init` (no PyPI package; `[project.optional-dependencies] dev` is the only install entry) |
| 3 | **13 mypy errors in `decision_drift.py` are PRE-existing tech debt** (per `verify-report.md` W9) — will surface as errors after shim removal (the `# type: ignore` comments at lines 759/772/792 become unnecessary + get removed; the underlying mypy errors may resurface in other locations) | LOW | Cleanup commit (T2.6) removes the 3 `# type: ignore` comments that the W1 enforcement makes unnecessary; the remaining 10 mypy errors are out of scope for v0.9.0 (carry-forward to v1.0 tech-debt follow-up); sdd-verify will report the residual count and gate the archive on a documented "10 mypy residuals carried forward to v1.0" decision |
| 4 | **W2 deviation (Option B) is technically a spec/implementation mismatch** — design.md D2 wanted `unable_to_verify` canonical but impl kept `graph_unavailable` canonical + added `unable_reason`. The Drift note documents the decision but operators grepping for `unable_to_verify` may find it absent (it's only present in the CHANGELOG v0.8.0 step 3 + the `unable_to_verify` enum value + the `drift_unable_to_verify_total` counter name + CLI exit-code 2 wording — NOT as a field name) | LOW | The Drift note in `archive/2026-06-27-drift-hardening/design.md` (T3.4) explicitly documents the deviation + links to CHANGELOG v0.8.0 step 3; the `unable_to_verify` enum value + counter name + exit-code wording remain stable (they describe the terminal STATE, not the field — explore line 134-138 confirms); the Drift note is appended to the existing `## Drift: implementation deviations from design` section (line 446-491) which already documents W1 + W2 + W3 deviations, so operators reading the section get the full context |
| 5 | **`Finding.__post_init__` enforcement is strict (rejects `bool` which is `int` subclass)** — existing test sites that pass `decision_id=1` (Python `int`) are fine, but any test that passes `decision_id=True` would now raise `TypeError` | LOW | `mypy --strict` + the `__post_init__` rejects `bool` per proposal §"Code sketch" line 242 (`isinstance(self.decision_id, bool)`); 0 known callers pass `bool` (verified via `rg "decision_id=True" tests/ src/` at HEAD `a2ce3f5`); the T2.4 RED fixture explicitly tests the bool rejection to lock the contract |
| 6 | **`tests/unit/test_decision_drift_v090_hardening.py` is a NEW test file** — needs to be created with 4 fixtures (T1.1, T1.4, T2.1, T2.4); file purpose differs from v0.8.0 migration file (v0.9.0 hardening tests assert shims are GONE; v0.8.0 migration tests assert shims WARN + COERCE) | LOW | NEW file path per proposal §"Approach" + per task T1.1/T1.4/T2.1/T2.4 acceptance; follows the same naming pattern as `test_decision_drift_v080_migration.py`; file-level docstring will explain: "Shim removal verification tests for v0.9.0 hardening. Asserts the 3 v0.8.0 1-release compat shims are removed and `Finding.__post_init__` enforces int-only `decision_id`." |
| 7 | **Per-task strict TDD adds 4 NEW test files + 19 commit work-units** — more commits than per-group TDD (3 commits); wall-time overhead | LOW | Per-task TDD gives bisect-ability that per-group TDD sacrifices for fewer commits; the 10-12 commit target is manageable (each commit ≤30 LOC delta) and matches `work-unit-commits` skill precedent; verify-report W4 precedent shows per-task discipline catches silent drift |

---

## Acceptance criteria

> **Note**: This is the AGGREGATE acceptance for the entire change, not per-task. Per-task acceptance is in each task's section above.

### Sub-batch A (W1 removal) — REQ-V9.1 + REQ-V9.2
- [ ] `Finding.from_legacy` attribute is removed; accessing it raises `AttributeError` (T1.1 RED + T1.2 GREEN)
- [ ] `DriftReport.from_legacy` attribute is removed; accessing it raises `AttributeError` (T1.4 RED + T1.5 GREEN)
- [ ] 2 `Finding(decision_id="<str>", ...)` sites migrated to int in `test_decision_drift.py:196` + `test_cli_watch_drift.py:99` (T1.3)
- [ ] 8 `DriftReport(scanned_at=0.0, ...)` sites migrated to ISO str in `test_decision_drift.py:208/535`, `test_cli_watch_drift.py:200/253`, `test_daemon_drift_events.py:151/175/204/289` (T1.6)
- [ ] 3 `Finding.from_legacy_*` fixtures deleted from `test_decision_drift_v080_migration.py:104-146` (T1.3)
- [ ] 3 `DriftReport.from_legacy_*` fixtures deleted from `test_decision_drift_v080_migration.py:165-206` (T1.6)
- [ ] 3 canonical type-contract smokes KEPT in `test_decision_drift_v080_migration.py:76-218` (decision_id int + scanned_at str + unable_reason default)

### Sub-batch B (W3 removal + W1 enforcement) — REQ-V9.3 + REQ-V9.4
- [ ] `classify_binding_legacy` function is removed; calling it raises `NameError` (T2.1 RED + T2.2 GREEN)
- [ ] `Finding(decision_id="42", ...)` raises `TypeError` via new `Finding.__post_init__` (T2.4 RED + T2.5 GREEN)
- [ ] `Finding(decision_id=True, ...)` raises `TypeError` (bool subclass rejection; T2.4 RED)
- [ ] `Finding(decision_id=42, ...)` constructs successfully (T2.4 GREEN; canonical type-contract)
- [ ] 10 `classify_binding_legacy(binding, nodes, id_map)` call sites migrated to `classify_binding(binding, nodes)` in `test_decision_drift.py:74/83/95/104/116/125/135/142/173/188` (T2.3)
- [ ] `test_classify_binding_legacy_3arg_emits_deprecation_warning` deleted from `test_decision_drift_v080_migration.py:243-255` (T2.3)
- [ ] `_id_map` test helper deleted from `test_decision_drift.py:61-62` (T2.3; dead after migration)
- [ ] 3 `# type: ignore` comments removed from `decision_drift.py:759/772/792` (T2.6)

### Sub-batch C (Docs + meta) — REQ-V9.5
- [ ] `openspec/specs/decision-drift/spec.md:14-41` v0.8.0 migration note replaced with v0.9.0 final note (T3.1)
- [ ] `CHANGELOG.md` `## [0.9.0] - 2026-06-XX` entry with `### Changed (BREAKING)` + `### Removed` + `### Migration` sections (T3.2)
- [ ] `pyproject.toml:3` `version = "0.9.0"` (T3.3)
- [ ] Drift note appended to `archive/2026-06-27-drift-hardening/design.md` after line 491 documenting W2 Option B resolution (T3.4)
- [ ] 6 SKILL.md runtime files updated atomically — "1-release shim" qualifier removed (T3.5)
- [ ] `uv run ruff check --fix` clean on all changed files (T3.6)
- [ ] `apply-progress/merged.md` closeout written; commit the merged PR (T3.7)

### Aggregate (full change)
- [ ] All 1224 existing tests pass (1232 baseline − 3 + 3 fixtures deleted in sub-batch A − 1 fixture deleted in sub-batch B = 1224; verified via `uv run --frozen pytest`)
- [ ] All 21 BDD scenarios from `openspec/specs/decision-drift/spec.md` still pass (no BDD surface changes; verified via `pytest tests/bdd/`)
- [ ] `ruff check` clean on changed files (T3.6)
- [ ] `mypy src/flow_engineering/decision_drift.py` shows ≤10 errors (down from 13 in v0.8.0; the 3 `# type: ignore` cleanup at T2.6 removes 3)
- [ ] No new warnings emitted in test output (verify-report S3 line 298-304 noise: 10 `DeprecationWarning`s from `classify_binding_legacy` callers + 3 from `Finding.from_legacy` + 3 from `DriftReport.from_legacy` are eliminated)
- [ ] Strict TDD evidence: every public deletion has RED → GREEN → REFACTOR history in commit log; per-commit work-unit splits per `work-unit-commits` skill (10-12 commits each ≤30 LOC delta)
- [ ] Drift detector (REQ-9..16) behavior unchanged for end users — the public API break is internal; CLI output + exit codes + JSONL append behavior byte-identical to v0.8.0/v0.8.1
- [ ] `flow drift scan <change>` exit-code semantics unchanged (0 still-valid, 1 drift, 2 graph_unavailable, 3 usage error)
- [ ] `flow drift scan --format=<text|json>` default text + JSON output byte-identical to v0.8.0/v0.8.1

---

## Open follow-ups for sdd-archive (after PR merge)

- Spec catalog baseline retro-fill for prior capability specs (REQ-9..16, REQ-28..34) — `openspec/specs/` bootstrap pattern continues
- MEMORY.md / AGENTS.md update for new v0.9.0 shim-removal workflow (none expected; this is a one-time deprecation closure)
- Cross-impact verification for all 8 prior changes (decision-code-linking, decision-reality-drift, vector-semantic-search, cross-project-federation, graph-snapshots, observability, prompt-registry, drift-hardening)
- README updates for new `Finding.__post_init__` contract + shim removal migration (likely none needed; CHANGELOG is the operator-facing surface)

---

## Coordination notes

- **MANDATORY**: prompt-registry PR#2b must have shipped (archived) BEFORE v0.9.0-hardening apply starts — ✅ satisfied (per Engram #263, shipped 2026-06-28)
- **MANDATORY**: v0.9.0-hardening applied as 3 sequential sub-batches with per-batch closeout docs (mirrors `drift-hardening` `apply-progress/merged.md` precedent)
- **MANDATORY**: per-commit work-unit splits per `work-unit-commits` skill (each commit ≤30 LOC delta; 10-12 commits total)
- **MANDATORY**: 6 SKILL.md runtime files updated atomically (per `drift-hardening` T4.5.c `--allow-empty` commit precedent)
- **W2 fork**: Option B (accept deviation + Drift note in design.md) pre-decided by orchestrator brief; no user pause between phases (loop mode ACTIVE)
- **Mypy residuals**: 10 expected after T2.6 (down from 13 in v0.8.0); carry-forward documented in v0.9.0 verify-report + deferred to v1.0 tech-debt follow-up

---

## Carry-forwards (NOT in v0.9.0)

### Deferred to v1.0

- **`flow drift events` CLI read-side command** (verify-report S2): operators use `cat ~/.flow-engineering/drift_events.jsonl | jq` in v0.8.0/v0.8.1/v0.9.0
- **`DriftEvent.decision_id: str` → `int` JSONL wire format change** (verify-report S1): JSONL is consumed by 3rd-party tools (jq scripts, dashboards); not a v0.9.0 scope
- **Tech debt residuals** (post v0.9.0): 4 ruff warnings + ≤10 mypy errors in `decision_drift.py`; deferred to v1.0 tech-debt follow-up
- **`Finding.__post_init__` removal itself** (v1.0): in v0.9.0 the `__post_init__` IS the contract (the W1 shim is gone)

### Deferred to v1.1

- **`DriftEventLog` JSONL rotation hardening** (verify-report W7): the 10 MB rotation threshold already shipped in v0.8.0 (REQ-55); the `os.fsync` atomic-write hardening is deferred
- **`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var** (verify-report W7): joint with REQ-44 metrics rotation
- **REQ-51/52/53** (drift-events-dashboard CLI surface): explicitly deferred from v0.8.0 per verify-report S2; carry-forward to v1.1

### Already RESOLVED in v0.9.0-hardening (per this tasks.md)

| Source | Item | Resolution evidence |
|--------|------|---------------------|
| `drift-hardening` verify-report #135 | W1 — `Finding.from_legacy` + `DriftReport.from_legacy` shims | T1.1 + T1.2 + T1.3 + T1.4 + T1.5 + T1.6 — DELETE both classmethods; migrate 10 direct-legacy test sites; delete 6 v0.8.0 migration fixtures; KEEP 3 canonical type-contract smokes |
| `drift-hardening` verify-report #135 | W2 — `graph_unavailable` field-name direction-flip | T3.4 — Drift note in `archive/2026-06-27-drift-hardening/design.md` documenting Option B; link to CHANGELOG v0.8.0 step 3 |
| `drift-hardening` verify-report #135 | W3 — `classify_binding_legacy` 3-arg wrapper | T2.1 + T2.2 + T2.3 — DELETE function; migrate 10 call sites; delete dead `_id_map` helper; delete 1 v0.8.0 migration fixture |
| `drift-hardening` verify-report #135 | W1 (optional) — add `Finding.__post_init__` str→int enforcement | T2.4 + T2.5 + T2.6 — `__post_init__` raises `TypeError` on str/bool inputs; cleanup 3 `# type: ignore` comments |

---

## Engram observation

This tasks.md is mirrored to Engram as `sdd/v0.9.0-hardening/tasks` (architecture type, project scope).
