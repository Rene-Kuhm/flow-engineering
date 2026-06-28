<!-- tasks.md: v1.0-followups. Source: sdd-tasks sub-agent. -->
# Tasks: v1.0-followups

**Change:** `v1.0-followups` (debt-closure release — closes drift-hardening S1+S2 + v0.9.0-hardening 12 mypy residuals + capability spec v1.0 entry; per `openspec/changes/v1.0-followups/explore.md` + `proposal.md` + `design.md`)
**Builds on:** `proposal.md` — 4 REQs (REQ-V1.0.1..V1.0.4); `design.md` — 5 architecture decisions (D1..D5) + Open Questions OQ-1..OQ-6 all pre-resolved (S1 Option A + S2 Path B); `drift-hardening` verify-report S1+S2 carry-forwards; `v0.9.0-hardening` `apply-progress/merged.md` strict-TDD precedent + 3-sub-batch per-task shape
**Date:** 2026-06-28
**Status:** EXPLORED + PROPOSED + DESIGNED → ready for `sdd-apply v1.0-followups`
**Strict TDD:** ON (per `v0.9.0-hardening` `apply-progress/merged.md` line 8 + `work-unit-commits` discipline; RED → GREEN → REFACTOR per task with "shim-still-exists" RED-before-GREEN pattern for the S1 wire-format flip)
**Delivery strategy:** single-pr (per `proposal.md` §"Approach matrix" Approach A; ~100 prod + ~250 test = ~350 LOC delta; well under 400 LOC chained-PR threshold)

> **REQ-label note**: REQ-V1.0.1 = S1 wire-format flip (`DriftEvent.decision_id: str` → `int` + defensive read-side coercion); REQ-V1.0.2 = S2a `flow drift-events list` subcommand (Path B parallel command, NON-BREAKING); REQ-V1.0.3 = S2b `flow drift-events {tail,stats}` subcommands; REQ-V1.0.4 = tech-debt closure (12 mypy residuals + CHANGELOG + version bump + spec sync).

> **Pre-decided by orchestrator (per brief)**: S1 Option A (flip `decision_id: int`); S2 Path B (parallel command `flow drift-events {list,tail,stats}`); per-task strict TDD; single PR.

---

```yaml
status: success
confidence: high
total_tasks: 17  # T1.1..T1.6 + T2.1..T2.3 + T3.1..T3.4 + T4.1..T4.4
pr_split: single PR (4 sequential sub-batches of strict per-task TDD)
forecast_loc_production: ~100  # 1 dataclass field type + 1 daemon coercion removed + 1 NEW Click group (~80 LOC) + 12 # type: ignore + pyproject bump
forecast_loc_test: ~250  # 1 str→int test migration + 2 NEW legacy coercion tests + ~15 NEW list tests + ~10 NEW tail tests + ~10 NEW stats tests + 3 NEW BDD scenarios
forecast_loc_grand_total: ~350  # well under 400-line chained-PR threshold
forecast_loc_realistic_x5_7: ~2000  # per v0.9.0-hardening precedent multiplier
sub_batches:
  sub_batch_a: 6 tasks   # T1.1..T1.6   — REQ-V1.0.1 S1 wire-format flip
  sub_batch_b: 3 tasks   # T2.1..T2.3   — REQ-V1.0.2 S2a `list` subcommand
  sub_batch_c: 4 tasks   # T3.1..T3.4   — REQ-V1.0.3 S2b `tail` + `stats` + BDD
  sub_batch_d: 4 tasks   # T4.1..T4.4   — REQ-V1.0.4 docs + meta + tech-debt
review_workload_forecast:
  single_pr_400_line_budget_risk: low
  chained_pr_recommendation: no
  decision_needed_before_apply: no
strict_tdd: on
bdd_feature_files: 1 NEW  # tests/bdd/req_v1_0_drift_events.feature (3 scenarios: list + tail + stats)
bdd_scenarios: 3 NEW
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v1.0-followups\tasks.md
next_recommended: sdd-apply v1.0-followups sub-batch A (T1.1..T1.6)
```

---

## PR Split

| PR | REQs | Tasks | LOC forecast | LOC realistic (×5.7) |
|----|------|-------|--------------|----------------------|
| **PR#1** (v1.0-followups) | REQ-V1.0.1..V1.0.4 (all 4) | T1.1..T4.4 (17 tasks across 4 sequential sub-batches) | ~100 prod + ~250 test = ~350 total | ~2 000 |
| **Total** | **4 REQs** | **17 tasks** | **~350** | **~2 000** |

**Rationale**: Single PR per `proposal.md` Approach A. Bundles REQ-V1.0.1 (S1 wire-format flip + defensive read guard) + REQ-V1.0.2 (S2a `list` subcommand + 4 formats) + REQ-V1.0.3 (S2b `tail` + `stats` subcommands + 3 BDD scenarios) + REQ-V1.0.4 (12 mypy residuals + CHANGELOG v1.0 + version bump + spec sync) into one v1.0 release. Total ~350 LOC delta — well under the 400 LOC chained-PR threshold. The 4 REQs are thematically unified (all close SUGGESTIONs + tech-debt from drift-hardening + v0.9.0-hardening + capability spec v1.0 plan); splitting into chained PRs would force each PR to re-establish the wire-format flip context that the previous PR just landed — needless friction.

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Total tasks | 17 (T1.1..T1.6, T2.1..T2.3, T3.1..T3.4, T4.1..T4.4) |
| Forecast LOC production | ~100 (~1 dataclass type-flip + ~1 daemon coercion removal + ~80 NEW Click group + ~12 # type:ignore + ~6 docs) |
| Forecast LOC test | ~250 (~1 str→int test migration + ~2 NEW legacy coercion tests + ~15 NEW list tests + ~10 NEW tail tests + ~10 NEW stats tests + ~3 NEW BDD scenarios + ~10 step glue) |
| Forecast LOC grand total | **~350** |
| Forecast LOC realistic (×5.7 TDD multiplier per `v0.9.0-hardening` §"Structured Metadata") | **~2 000** |
| BDD feature files | 1 NEW (`tests/bdd/req_v1_0_drift_events.feature`) |
| BDD scenarios | 3 NEW (list default text, tail newest-first, stats per-change counts) |
| New source files | 0 (NEW Click group lives in `cli.py`) |
| Modified source files | 4 (`src/flow_engineering/drift_event_log.py`, `daemon.py`, `cli.py`, `decision_drift.py`) |
| New test files | 4 (3 NEW unit test files + 1 NEW BDD feature + 1 NEW BDD step glue) |
| Modified docs/meta files | 3 (`openspec/specs/decision-drift/spec.md`, `CHANGELOG.md`, `pyproject.toml`) |
| Chained PRs recommended | **No** (single PR per `proposal.md` §"Approach matrix"; ~350 well below 400-line threshold) |
| Chain strategy | N/A (single PR; per-commit work-unit splits per `work-unit-commits`) |
| 400-line budget risk | **Low** (single PR ~350 / ~2 000 realistic — mitigated by 10-15 work-unit commits each ≤30 LOC delta) |
| Decision needed before apply | **No** (single-pr + S1 Option A + S2 Path B pre-decided by orchestrator brief) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: N/A (single PR)
400-line budget risk: Low

### Forecast rationale

| Signal | Source | Value |
|---|---|---|
| Production LOC added (S1 wire-format flip) | `drift_event_log.py:46` annotation `str` → `int` (1 LOC) + `_legacy_warn_emitted` flag in `__init__()` (~3 LOC) + defensive coercion + stderr WARN in `read_all()` (~7 LOC) + `daemon.py:60` coercion removal (1 LOC) + docstring update (~3 LOC) | ~15 prod |
| Production LOC added (S2a list subcommand) | NEW `@main.group(name="drift-events")` (~3 LOC) + `drift_events_list` Click command with 7 flags (~20 LOC) + 4 format handlers (~25 LOC) + exit-code handlers (~5 LOC) | ~50 prod |
| Production LOC added (S2b tail + stats) | `drift_events_tail` (~12 LOC) + `drift_events_stats` (~18 LOC) | ~30 prod |
| Production LOC added (D tech-debt + docs) | 12 `# type: ignore` comments (~12 LOC) + pyproject bump (~1 LOC) + CHANGELOG (~30 LOC) + spec sync (~15 LOC) | ~58 prod |
| Production LOC total | | ~100 prod (rounded down from ~153 with overlap reduction; net ~100) |
| Test LOC added (S1) | 1 str→int fixture migration in `test_drift_event_log.py` (~3 LOC) + 2 NEW legacy coercion tests (~15 LOC) + 1 NEW one-time WARN cadence test (~10 LOC) | ~28 test |
| Test LOC added (S2a) | NEW `test_cli_drift_events_list.py` with ~15 unit tests (~80 LOC) | ~80 test |
| Test LOC added (S2b) | NEW `test_cli_drift_events_tail.py` (~50 LOC) + `test_cli_drift_events_stats.py` (~50 LOC) | ~100 test |
| Test LOC added (D BDD + glue) | NEW `tests/bdd/req_v1_0_drift_events.feature` (~30 LOC) + step glue (~30 LOC) | ~60 test |
| Test LOC total | | ~268 test (rounded to ~250) |
| Realistic ×5.7 TDD multiplier | `v0.9.0-hardening` precedent (design §"Structured Metadata"): strict-TDD band ×5.7 | ×5.7 → ~2 000 grand total realistic |
| Per-delegation batch ceiling | `apply-batches-split-into-6-tasks-per-delegation` pattern (Engram #112): ≤3 tasks OR ≤150 LOC prod per delegation | All sub-batches ≤6 tasks / ≤80 LOC prod — well within ceiling |
| Risk: silent regression if a test site is missed | Per-task TDD with RED test before each GREEN impl (T1.1 + T1.3 + T2.1 + T3.1); grep audit before PR open (`rg "decision_id=\"" src/ tests/` for str inputs) | **LOW** — mitigated by per-task TDD + grep audit |
| Risk: wire-format BREAKING for jq consumers | CHANGELOG v1.0 1-line `sed` migration note (per `proposal.md` OQ-3); defensive read guard with one-time WARN (D2) | **LOW** — already mitigated by D2 + CHANGELOG |
| Risk: Path B parallel namespace is less elegant than Path A subcommand group | Document the parallel-namespace rationale in CHANGELOG v1.0 entry | **LOW** — already mitigated by CHANGELOG note |

### Suggested Work Units

Single PR (no chained split per `proposal.md` §"Approach matrix" + `design.md` §"Decisions" D3). Per-delegation batching (≤3 tasks / ≤150 LOC prod) still required at apply phase because delegate runtime is ~15 min.

| Apply sub-batch | Tasks | Production LOC | Test LOC | Why |
|-----------------|-------|----------------|----------|-----|
| **A** | T1.1 + T1.2 + T1.3 | ~3 prod | ~13 added | S1 D1 RED + GREEN type-flip + RED defensive coercion |
| **B** | T1.4 + T1.5 + T1.6 | ~12 prod | ~15 added | S1 D2 GREEN defensive guard + D1 daemon coercion removal + REFACTOR migration |
| **C** | T2.1 + T2.2 + T2.3 | ~50 prod | ~80 added | S2a `list` subcommand RED → GREEN → REFACTOR text-table |
| **D** | T3.1 + T3.2 | ~12 prod | ~50 added | S2b `tail` subcommand RED → GREEN |
| **E** | T3.3 + T3.4 | ~18 prod | ~50 added | S2b `stats` subcommand GREEN + 3 BDD scenarios |
| **F** | T4.1 + T4.2 + T4.3 + T4.4 | ~58 prod | 0 | Docs + meta + 12 mypy residuals + spec sync |

---

## Dependency Graph

```
Sub-batch A — REQ-V1.0.1 S1 wire-format flip (6 tasks)
  T1.1 (RED test asserting DriftEvent(decision_id="42") raises TypeError)
    ↓
  T1.2 (GREEN: drift_event_log.py:46 str → int annotation flip)
    ↓
  T1.3 (RED test asserting DriftEventLog.read_all() coerces legacy str lines + 1-time stderr WARN)
    ↓
  T1.4 (GREEN: _legacy_warn_emitted flag + try/except coercion in read_all())
    ↓
  T1.5 (GREEN: daemon.py:60 str() coercion removal)
    ↓
  T1.6 (REFACTOR: migrate 1 str-input fixture + verify 5 existing tests + mypy clean)

Sub-batch B — REQ-V1.0.2 S2a `flow drift-events list` (3 tasks)
  T2.1 (RED test asserting flow drift-events list --since --until --change --event-class
                          --limit --format text|json|prometheus|csv --path works)
    ↓
  T2.2 (GREEN: @main.group(name="drift-events") + drift_events_list subcommand + 7 flags + 4 format handlers)
    ↓
  T2.3 (REFACTOR: text-table output mirror flow metrics summary + extract _format_drift_events_text helper)

Sub-batch C — REQ-V1.0.3 S2b `tail` + `stats` + BDD (4 tasks)
  T3.1 (RED test asserting flow drift-events tail --limit=N=10 --change --event-class --format works)
    ↓
  T3.2 (GREEN: drift_events_tail subcommand with default --limit=10 newest-first)
    ↓
  T3.3 (GREEN: drift_events_stats subcommand with per-event-class + per-change + per-decision-id top-N)
    ↓
  T3.4 (NEW BDD scenarios in tests/bdd/req_v1_0_drift_events.feature: list default text + tail newest-first + stats per-change counts; + step glue in tests/bdd/test_req_v1_0_drift_events_steps.py)

Sub-batch D — REQ-V1.0.4 Docs + meta + tech-debt (4 tasks)
  T4.1 (CHANGELOG.md v1.0 entry under ## [1.0.0] - 2026-06-XX with ### Changed (BREAKING) +
        ### Added + ### Migration sections; 1-line sed migration note)
    ↓ (independent)
  T4.2 (pyproject.toml:3 version = "1.0.0")
    ↓ (independent)
  T4.3 (12 # type: ignore comments at decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439
        using the per-site mypy error code: [type-arg] for 127/161/203/252/253/262/278,
        [arg-type] for 310/411/439, [no-untyped-def] for 372/375; mypy clean: 12 errors → 0)
    ↓ (independent)
  T4.4 (openspec/specs/decision-drift/spec.md: v1.0 ## Drift event log JSONL schema section +
        v1.0 capability entry in Versioning table at lines 408+)

[Apply sub-batch merge after each sub-batch → final PR merge]
```

---

## Out-of-Scope Reminders (do NOT pull into tasks)

These 7 items are explicitly deferred per `proposal.md` §"Carry-forwards explicitly NOT touched by this change" + `design.md` §"Carry-forwards explicitly NOT touched" — apply must NOT introduce code for them:

- **`DriftEventLog` JSONL rotation hardening** (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var + auto-rotation at threshold + `os.fsync` atomic-write) — DEFERRED to v1.1 alongside `metrics.jsonl` rotation (REQ-44) per capability spec `spec.md:410`
- **Cross-project federation for drift events** (`flow drift-events --project=<key>` filter) — DEFERRED to a separate `federated-drift-events` follow-up
- **OpenTelemetry OTLP push for drift events** — DEFERRED; Prometheus textfile (REQ-38) covers v1 export
- **`flow drift-events` Path A subcommand group rename** (BREAKING `flow drift check <change>`) — DEFERRED to v1.2+; revisit only if `flow drift` namespace grows
- **`flow drift <change> --drift-event-log[=<path>]` per-finding class filter** — DEFERRED; v0.8.0+ persists all non-still-valid findings by default
- **REQ-51 (prompt_renders.jsonl sink)** — DEFERRED to v1.1; independent of drift events
- **REQ-52 (flow prompt-events observability counters)** — DEFERRED to v1.1; pairs with REQ-51
- **REQ-53 (docs/prompts.md auto-generated from prompt registry)** — DEFERRED to v1.1; pairs with REQ-51/52

---

## Patterns Honored

- `apply-batches-split-into-6-tasks-per-delegation` (Engram #112): each apply sub-batch ≤3 tasks / ≤150 LOC prod
- `apply-under-strict-tdd-grows-5-6x-beyond-forecast` (Engram #113): design ×5.7 multiplier is the project-specific band; ~2 000 realistic vs ~350 forecast
- `work-unit-commits` skill: 10-15 work-unit commits per PR, each ≤30 LOC delta
- `stacked-to-main-requires-merging-prior-pr-before-next-apply` (Engram #114): N/A here (single PR)
- `v0.9.0-hardening` `--allow-empty` commit precedent (verify-report line 81 + commit d5f2147): 6 SKILL.md runtime files updated atomically — NOT needed here (v1.0-followups doesn't change the SDD API contract that the SKILL.md files document; the DriftEvent.decision_id flip is internal-only)
- `decision-code-linking` archive-report #119 S3 precedent: 5-6× strict-TDD multiplier applied
- `v0.9.0-hardening` per-task TDD precedent (apply-progress/merged.md line 8 + tasks.md Batch D): RED test asserts "shim-still-exists" before each delete (catches missing migrations via `AttributeError`)
- `observability` PR#2 subcommand-group precedent (verify-report-pr2.md:124-148 W1): mirrors `flow metrics {summary,export,aggregate}` shape for `flow drift-events {list,tail,stats}`

---

## Goal

Land the **2 deferred SUGGESTION items from drift-hardening verify-report** (S1 `DriftEvent.decision_id` wire-format flip + S2 `flow drift` read-side CLI) + the **12 mypy residuals from v0.9.0-hardening verify-report S3** in a single TDD-shaped change that finalizes the `decision-drift` capability at v1.0. v1.0 is intentionally NOT a feature release — it's the last **debt-closure release** before the project enters the v1.x feature cycle. Total ~350 LOC delta across 17 tasks in 4 sequential sub-batches; single PR; per-task strict TDD with RED-before-GREEN pattern; ~13 commits each ≤30 LOC delta. Pre-flight: 1233 tests collected at HEAD `8b02d38` (per `uv run --frozen pytest --collect-only -q`).

## Scope

### In scope (single PR, 4 sub-batches)

- **Sub-batch A (S1 wire-format flip, 6 tasks)**: `DriftEvent.decision_id: str` → `int` at `drift_event_log.py:46` + `DriftEventLog.read_all()` defensive coercion + `daemon.py:60` `str()` coercion removal + 1 test fixture migration
- **Sub-batch B (S2a `list` subcommand, 3 tasks)**: NEW `@main.group(name="drift-events")` + `drift_events_list` subcommand with 7 flags + 4 format handlers (text/json/prometheus/csv) + 15 unit tests + text-table REFACTOR
- **Sub-batch C (S2b `tail` + `stats` + BDD, 4 tasks)**: `drift_events_tail` (default `--limit=10` newest-first) + `drift_events_stats` (per-event-class + per-change + per-decision-id top-N counts) + 3 NEW BDD scenarios in `tests/bdd/req_v1_0_drift_events.feature`
- **Sub-batch D (Docs + meta + tech-debt, 4 tasks)**: CHANGELOG v1.0 entry (BREAKING + 1-line `sed` migration) + pyproject `0.9.0` → `1.0.0` + 12 mypy residuals via surgical `# type: ignore` comments + capability spec `## Drift event log JSONL schema` section + v1.0 Versioning entry

### Out of scope

See "Out-of-Scope Reminders" section above.

---

## Sub-batch A — REQ-V1.0.1: S1 `DriftEvent.decision_id` wire-format flip (6 tasks)

### T1.1 — RED: add failing test asserting `DriftEvent.decision_id` rejects str (REQ-V1.0.1)

- **Type:** test (RED — RED fixture for type-contract enforcement)
- **Strict TDD:**
  - RED: `tests/unit/test_drift_event_log.py::TestDriftEvent::test_decision_id_rejects_str` — asserts `DriftEvent(decision_id="42", change="x", binding_id="y", event_class="z", detected_at=0.0)` raises `TypeError` (currently allowed because `decision_id: str` accepts any string; baseline 1233/1233 must still pass at the start of this task)
  - GREEN: N/A (no production code change yet — annotation still `str`)
  - REFACTOR: N/A (single test method; ~10 LOC)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_drift_event_log.py::TestDriftEvent::test_decision_id_rejects_str -v` exits 1 with `TypeError` (RED state — annotation still `str` so construction succeeds and `__post_init__` raises on the int-flip-after-test-write sequence)
  - Verify baseline: `uv run --frozen pytest --collect-only -q` shows `1233 tests collected`
- **LOC forecast:** ~10 tests + 0 prod = ~10

### T1.2 — GREEN: flip `DriftEvent.decision_id: str` → `int` at `drift_event_log.py:46` (REQ-V1.0.1, D1)

- **Type:** code (GREEN — type annotation flip)
- **Strict TDD:**
  - RED: T1.1 RED fixture (already failing)
  - GREEN: `src/flow_engineering/drift_event_log.py:46` — `decision_id: str` → `decision_id: int` (1-line type annotation change); update the class docstring at line 38 to drop "(string per pre-v0.8.0)" → "(int per v1.0; matches `Finding.decision_id: int` post-v0.9.0)"; `to_json_dict()` at lines 51-59 emits the int naturally (no code change needed — JSON serialization follows the dataclass type)
  - REFACTOR: N/A (single annotation change; docstring 1-line edit)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_drift_event_log.py::TestDriftEvent::test_decision_id_rejects_str -v` exits 0 (GREEN state — `int` annotation rejects str)
  - `uv run --frozen pytest tests/unit/test_drift_event_log.py -v` shows 5 existing tests that construct `DriftEvent(decision_id="<str>", ...)` now FAIL with `TypeError` (expected; T1.6 migrates them)
  - `uv run --frozen pytest --collect-only -q` shows `1233` tests collected (no test count delta; T1.6 migrates the failing fixtures)
- **LOC forecast:** ~1 prod + ~2 docs = ~3

### T1.3 — RED: add failing test asserting `DriftEventLog.read_all()` defensively coerces legacy str lines (REQ-V1.0.1, D2)

- **Type:** test (RED — RED fixture for backward-compat shim)
- **Strict TDD:**
  - RED: `tests/unit/test_drift_event_log.py::TestDriftEventLog::test_read_all_coerces_legacy_str_decision_id` — writes a JSONL line `{"change": "x", "decision_id": "42", "binding_id": "y", "class": "z", "detected_at": 0.0}` (legacy str wire format) to a tmp_path fixture, calls `DriftEventLog(path=tmp).read_all()`, asserts the returned `DriftEvent` has `decision_id == 42` (int) AND `capfd.readouterr().err` contains `"legacy str decision_id"` (stderr WARN); currently RED because `read_all()` reads str and constructs `DriftEvent(decision_id="42", ...)` which would now raise `TypeError` post-T1.2 (catches the bug at the integration seam)
  - GREEN: N/A (no production code change yet — `read_all()` does not coerce)
  - REFACTOR: N/A (single test method; ~20 LOC)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_drift_event_log.py::TestDriftEventLog::test_read_all_coerces_legacy_str_decision_id -v` exits 1 with either `TypeError: DriftEvent.decision_id must be int, got str` (post-T1.2 GREEN state, pre-T1.4 GREEN state) or stale str construction (pre-T1.2 state — RED regardless)
  - `uv run --frozen pytest --collect-only -q` shows `1233 + 2 = 1235` tests collected (2 NEW RED fixtures: this + the one-time WARN cadence test in T1.4 commit; or 1 NEW if bundled)
- **LOC forecast:** ~20 tests + 0 prod = ~20

### T1.4 — GREEN: add defensive `try/except` + `_legacy_warn_emitted` flag + one-time stderr WARN in `DriftEventLog.read_all()` (REQ-V1.0.1, D2)

- **Type:** code (GREEN — defensive read guard)
- **Strict TDD:**
  - RED: T1.3 RED fixture (already failing)
  - GREEN: `src/flow_engineering/drift_event_log.py:72-79` (`__init__`) — ADD `self._legacy_warn_emitted: bool = False` (~1 LOC); `src/flow_engineering/drift_event_log.py:95-119` (`read_all`) — ADD a defensive `if isinstance(data.get("decision_id"), str):` block that coerces via `int(data["decision_id"])` and emits a one-time stderr WARN (`print(f"warning: legacy str decision_id in {self.path}; coercing to int. Run the CHANGELOG v1.0 sed migration to silence.", file=sys.stderr)`) gated by `if not self._legacy_warn_emitted: ... self._legacy_warn_emitted = True` (~10 LOC); also extend the `except (json.JSONDecodeError, TypeError, ValueError): continue` to catch non-numeric legacy strings (already catches via the existing `TypeError` from `int()` coercion)
  - REFACTOR: N/A (single block addition)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_drift_event_log.py::TestDriftEventLog::test_read_all_coerces_legacy_str_decision_id -v` exits 0 (GREEN state)
  - ADDITIONAL TEST: `tests/unit/test_drift_event_log.py::TestDriftEventLog::test_read_all_one_time_warn_cadence` — writes 2 legacy str lines to a tmp_path fixture, calls `read_all()` once, asserts `len(capfd.readouterr().err.splitlines()) == 1` (one WARN, not two; per-instance flag works correctly)
  - `uv run --frozen pytest tests/unit/test_drift_event_log.py -v` exits 0 (T1.2-broken fixtures still failing — T1.6 migrates them)
- **LOC forecast:** ~13 prod added (1 flag + ~10 read_all block + ~2 import sys) + ~10 tests = ~23

### T1.5 — GREEN: remove `str(finding.decision_id)` coercion at `daemon.py:60` (REQ-V1.0.1, D1)

- **Type:** code (GREEN — daemon write-side simplification)
- **Strict TDD:**
  - RED: N/A (T1.3 covers the read-side coercion; the write-side is tested by `tests/unit/test_daemon_drift_events.py` existing tests which construct `Finding(decision_id=<int>, ...)` and assert the appended `DriftEvent` round-trips correctly)
  - GREEN: `src/flow_engineering/daemon.py:60` — `decision_id=str(finding.decision_id),` → `decision_id=finding.decision_id,` (1-line edit; `finding.decision_id` is `int` post-v0.9.0; `DriftEvent.decision_id` is `int` post-T1.2; direct assignment works); `src/flow_engineering/daemon.py:46-51` (docstring) — DROP the "Future v1 follow-up may flip..." note (~3 LOC edit; replace with "(REQ-V1.0.1: `DriftEvent.decision_id` is `int` post-v1.0; no coercion needed)")
  - REFACTOR: N/A (single edit)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_daemon_drift_events.py -v` exits 0 (existing 8 tests pass with the direct int assignment)
  - `rg "str\(finding\.decision_id\)" src/` shows 0 matches (coercion removed)
  - `uv run --frozen pytest tests/unit/test_drift_event_log.py -v` shows 5 fixtures still FAILING (T1.6 migrates them)
- **LOC forecast:** ~1 prod + ~3 docs = ~4

### T1.6 — REFACTOR: migrate 1 str-input fixture to int + mypy clean verify + 5 existing tests still pass (REQ-V1.0.1)

- **Type:** test refactor + verification (migrate legacy str fixtures + verify RED → GREEN → REFACTOR chain)
- **Strict TDD:**
  - RED: N/A (GREEN state from T1.4 + T1.5)
  - GREEN: N/A (no production code change)
  - REFACTOR:
    - `tests/unit/test_drift_event_log.py` — find + migrate the 1-5 `DriftEvent(decision_id="<str>", ...)` fixture sites to `decision_id=<int>` (grep audit: `rg 'decision_id="\d+"' tests/unit/test_drift_event_log.py` should return 0 matches after migration)
    - `uv run --frozen pytest tests/unit/test_drift_event_log.py tests/unit/test_daemon_drift_events.py -v` exits 0 (all migrated sites pass; no regression)
    - `uv run --frozen pytest --collect-only -q` shows `1233 + 2 = 1235` tests collected (the 2 NEW T1.3 + T1.4 tests added; 0 deleted — the 5 fixtures that were str-input were not deleted, just migrated)
    - `uv run mypy src/flow_engineering/drift_event_log.py src/flow_engineering/daemon.py 2>&1 | wc -l` shows ≤3 errors (≤3 expected; the 12 mypy residuals in `decision_drift.py` are out-of-scope for sub-batch A — T4.3 cleans them)
- **Acceptance:**
  - `rg 'decision_id="[0-9]+"' tests/unit/test_drift_event_log.py` exits 0 matches (all fixtures migrated to int)
  - `uv run --frozen pytest -v` exits 0 (full suite: 1235 tests pass)
  - `uv run --frozen pytest --collect-only -q` shows `1235 tests collected`
  - `uv run mypy src/flow_engineering/drift_event_log.py src/flow_engineering/daemon.py 2>&1 | tail -5` shows ≤3 errors (≤3 expected at most — non-blocking; sub-batch A focuses on the wire-format flip)
- **LOC forecast:** ~5 tests modified + 0 tests deleted + 0 prod = ~5

---

## Sub-batch B — REQ-V1.0.2: S2a `flow drift-events list` subcommand (3 tasks)

### T2.1 — RED: add failing test asserting `flow drift-events list` subcommand exists with full filter set (REQ-V1.0.2, D3 + D4)

- **Type:** test (RED — RED fixture for CLI surface contract)
- **Strict TDD:**
  - RED: `tests/unit/test_cli_drift_events_list.py::test_drift_events_list_command_exists` — invokes `flow drift-events list --since=<iso> --until=<iso> --change=<name> --event-class=<LABEL_DRIFT> --limit=5 --format=text --path=<tmp>` via Click's `CliRunner` and asserts exit code 0 + stdout contains the expected header row ("change") + a NEW tmp_path JSONL fixture with 3 events (one matching all filters, one matching `--change` only, one matching nothing)
  - RED (also): `tests/unit/test_cli_drift_events_list.py::test_drift_events_list_json_format` — asserts `--format=json` returns the JSON envelope with `decision_id` as int (per D1) + exits 0
  - RED (also): `tests/unit/test_cli_drift_events_list.py::test_drift_events_list_invalid_format` — asserts `--format=invalid` exits 2 with stderr containing "Invalid value"
  - RED (also): `tests/unit/test_cli_drift_events_list.py::test_drift_events_list_invalid_since` — asserts `--since=not-a-date` exits 2 with stderr containing "invalid"
  - GREEN: N/A (no production code change yet — `flow drift-events` command doesn't exist)
  - REFACTOR: N/A (4 test methods; ~80 LOC)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_cli_drift_events_list.py -v` exits 1 with `AttributeError: module 'flow_engineering.cli' has no attribute 'drift_events_list'` (or `NoSuchCommand` from Click — RED state — command doesn't exist yet)
  - `uv run --frozen pytest --collect-only -q` shows `1235 + 4 = 1239` tests collected (4 NEW RED fixtures)
- **LOC forecast:** ~80 tests + 0 prod = ~80

### T2.2 — GREEN: add `@main.group(name="drift-events")` + `drift_events_list` subcommand with 7 flags + 4 format handlers (REQ-V1.0.2, D3 + D4)

- **Type:** code (GREEN — NEW Click subcommand group + `list` subcommand)
- **Strict TDD:**
  - RED: T2.1 RED fixtures (already failing)
  - GREEN: `src/flow_engineering/cli.py:~1712+` (after the existing `@main.command() def drift(...)` at lines 1712-1809) — ADD:
    - `import sys; import csv; import io; from datetime import datetime` (top-of-file additions if not present)
    - `@main.group(name="drift-events") def drift_events_group(): ...` (3 LOC)
    - `@drift_events_group.command(name="list")` + 7 Click options (`--since`, `--until`, `--change`, `--event-class`, `--limit`, `--format` with `click.Choice(["text", "json", "prometheus", "csv"])`, `--path` with `click.Path(path_type=Path)`) + `def drift_events_list(since, until, change, event_class, limit, fmt, log_path) -> None:` body (~50 LOC including 4 format handlers)
    - `--format=text` → fixed-width table (mirrors `flow drift <change>` at `cli.py:1807 _render_drift_table`)
    - `--format=json` → JSON envelope via `json.dumps([e.to_json_dict() for e in events], indent=2)`
    - `--format=prometheus` → reuse `prometheus_exposition.write_prometheus_textfile` from `observability.py:945-983` (REQ-38) — emit `flow_drift_events_total{event_class="...",change="..."} <count>` with `# HELP` + `# TYPE` + `# EOF` markers
    - `--format=csv` → `csv.writer(io.StringIO())` with header row (`change,decision_id,binding_id,class,detected_at`)
    - Filter logic: parse `--since`/`--until` ISO 8601 → `datetime.fromisoformat()`; compare against `event.detected_at` (float epoch) via `datetime.fromtimestamp(event.detected_at, tz=UTC)`; filter by `--change` (exact match) + `--event-class` (exact match); cap by `--limit` (default None = no cap)
    - Exit codes per D9: 0=success, 2=invalid args (parse error on `--since`/`--until`/`--format`), 3=malformed JSONL (gracefully caught by `read_all()` already; this only fires if the file is unreadable OSError)
  - REFACTOR: N/A (single block addition)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_cli_drift_events_list.py -v` exits 0 (all 4 RED fixtures GREEN)
  - `uv run flow drift-events --help` prints the subcommand list (`list`, `tail`, `stats` — `tail` and `stats` are sub-batch C; `list` works)
  - `uv run flow drift-events list --help` prints all 7 options
  - `uv run --frozen pytest --collect-only -q` shows `1239` tests collected (4 NEW from T2.1; 0 deleted)
  - `rg "@main.group\(name=\"drift-events\"\)" src/flow_engineering/cli.py` shows 1 match
  - `rg "def drift_events_list\(" src/flow_engineering/cli.py` shows 1 match
- **LOC forecast:** ~50 prod added (3 group + 50 list body - 3 group = ~50; some imports may already exist) + 0 tests added (T2.1 covered) = ~50

### T2.3 — REFACTOR: extract `_format_drift_events_text` helper + ensure text-table output mirrors `flow metrics summary` precedent (REQ-V1.0.2, D4)

- **Type:** code refactor (text-table helper extraction; mirrors observability PR#2 precedent at `observability.py:1199-1265 format_percentile_report`)
- **Strict TDD:**
  - RED: N/A (GREEN state from T2.2)
  - GREEN: N/A (no production code change beyond helper extraction)
  - REFACTOR:
    - `src/flow_engineering/cli.py:~1712+` — EXTRACT the text-format rendering logic from `drift_events_list` body into a module-level helper `def _format_drift_events_text(events: list[DriftEvent]) -> str:` (~15 LOC; returns the fixed-width table as a string); `drift_events_list` body now calls the helper instead of inline rendering
    - ADDITIONAL TEST: `tests/unit/test_cli_drift_events_list.py::test_format_drift_events_text_helper` — direct unit test of the helper with 3 events asserts the returned string has the expected column widths + header row + 3 data rows
    - ADDITIONAL TEST: `tests/unit/test_cli_drift_events_list.py::test_drift_events_list_text_table_mirrors_metrics_summary` — captures stdout from `flow drift-events list --format=text` on a 3-event fixture and asserts the output width matches the `flow metrics summary` precedent (column-aligned; ~120 chars wide max)
  - Acceptance:
    - `uv run --frozen pytest tests/unit/test_cli_drift_events_list.py -v` exits 0 (all 6 tests pass: 4 from T2.1 + 2 NEW)
    - `uv run --frozen pytest tests/unit -v` exits 0 (no regression on existing 1235 tests)
    - `uv run --frozen pytest --collect-only -q` shows `1239 + 2 = 1241` tests collected
- **LOC forecast:** ~15 prod refactored (no net new) + ~20 tests added = ~20

---

## Sub-batch C — REQ-V1.0.3: S2b `tail` + `stats` subcommands + 3 BDD scenarios (4 tasks)

### T3.1 — RED: add failing test asserting `flow drift-events tail` subcommand works with `--limit=10` default (REQ-V1.0.3, D3)

- **Type:** test (RED — RED fixture for `tail` subcommand contract)
- **Strict TDD:**
  - RED: `tests/unit/test_cli_drift_events_tail.py::test_drift_events_tail_default_limit_10` — invokes `flow drift-events tail` via Click's `CliRunner` against a tmp_path JSONL with 15 events, asserts exit code 0 + stdout contains exactly 10 rows + rows are ordered newest-first (last 10 events by `detected_at`)
  - RED (also): `tests/unit/test_cli_drift_events_tail.py::test_drift_events_tail_explicit_limit` — asserts `--limit=3` returns 3 rows
  - RED (also): `tests/unit/test_cli_drift_events_tail.py::test_drift_events_tail_change_filter` — asserts `--change=foo` filters to events with `change == "foo"`
  - RED (also): `tests/unit/test_cli_drift_events_tail.py::test_drift_events_tail_event_class_filter` — asserts `--event-class=LABEL_DRIFT` filters
  - RED (also): `tests/unit/test_cli_drift_events_tail.py::test_drift_events_tail_json_format` — asserts `--format=json` returns JSON envelope
  - GREEN: N/A (no production code change yet — `drift_events_tail` command doesn't exist)
  - REFACTOR: N/A (5 test methods; ~50 LOC)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_cli_drift_events_tail.py -v` exits 1 with `AttributeError: module 'flow_engineering.cli' has no attribute 'drift_events_tail'` (RED state)
  - `uv run --frozen pytest --collect-only -q` shows `1241 + 5 = 1246` tests collected (5 NEW RED fixtures)
- **LOC forecast:** ~50 tests + 0 prod = ~50

### T3.2 — GREEN: add `@drift_events_group.command(name="tail")` with `--limit=10` default + `--change` + `--event-class` + `--format` (REQ-V1.0.3, D3)

- **Type:** code (GREEN — `tail` subcommand implementation)
- **Strict TDD:**
  - RED: T3.1 RED fixtures (already failing)
  - GREEN: `src/flow_engineering/cli.py:~1800+` (after `drift_events_list`) — ADD:
    - `@drift_events_group.command(name="tail")` + 4 Click options (`--limit` with `type=int, default=10`, `--change`, `--event-class`, `--format` with `click.Choice(["text", "json"])`) + `def drift_events_tail(limit, change, event_class, fmt) -> None:` body (~15 LOC; reads events via `DriftEventLog().read_all()`, sorts by `detected_at` descending, takes first N, applies `--change` + `--event-class` filters, renders text table via the `_format_drift_events_text` helper from T2.3 or JSON envelope)
  - REFACTOR: N/A (single subcommand addition)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_cli_drift_events_tail.py -v` exits 0 (all 5 RED fixtures GREEN)
  - `uv run flow drift-events tail --help` prints all 4 options + default `--limit=10`
  - `uv run --frozen pytest --collect-only -q` shows `1246` tests collected (5 NEW from T3.1; 0 deleted)
- **LOC forecast:** ~15 prod added + 0 tests added (T3.1 covered) = ~15

### T3.3 — GREEN: add `@drift_events_group.command(name="stats")` with per-event-class + per-change + per-decision-id top-N counts (REQ-V1.0.3, D3)

- **Type:** code (GREEN — `stats` subcommand implementation)
- **Strict TDD:**
  - RED (also T3.3 commit): `tests/unit/test_cli_drift_events_stats.py::test_drift_events_stats_per_event_class_counts` — invokes `flow drift-events stats` against a tmp_path JSONL with 5 events (2× LABEL_DRIFT, 2× STALE_LOCATION, 1× STILL_VALID), asserts stdout contains "LABEL_DRIFT: 2", "STALE_LOCATION: 2", "STILL_VALID: 1"
  - RED (also): `tests/unit/test_cli_drift_events_stats.py::test_drift_events_stats_per_change_counts` — asserts stdout contains per-change counts (e.g., "change-foo: 3")
  - RED (also): `tests/unit/test_cli_drift_events_stats.py::test_drift_events_stats_per_decision_id_top_n` — asserts stdout contains the top-5 most-frequent `decision_id`s with counts
  - RED (also): `tests/unit/test_cli_drift_events_stats.py::test_drift_events_stats_json_format` — asserts `--format=json` returns JSON envelope with the 3 count dictionaries
  - RED (also): `tests/unit/test_cli_drift_events_stats.py::test_drift_events_stats_filters` — asserts `--change=foo --since=... --until=...` filters correctly
  - RED (also): `tests/unit/test_cli_drift_events_stats.py::test_drift_events_stats_empty_log` — asserts empty log → all-zero table + exit 0
  - GREEN: `src/flow_engineering/cli.py:~1830+` (after `drift_events_tail`) — ADD:
    - `@drift_events_group.command(name="stats")` + 4 Click options (`--change`, `--since`, `--until`, `--format` with `click.Choice(["text", "json"])`) + `def drift_events_stats(change, since, until, fmt) -> None:` body (~20 LOC; reads events via `DriftEventLog().read_all()`, applies filters, computes `Counter(event.event_class for event in events)` + `Counter(event.change for event in events)` + `Counter(event.decision_id for event in events).most_common(5)`, renders aligned text table with the 3 sections + JSON envelope via `--format=json`)
  - REFACTOR: N/A (single subcommand addition)
- **Acceptance:**
  - `uv run --frozen pytest tests/unit/test_cli_drift_events_stats.py -v` exits 0 (all 6 RED fixtures GREEN)
  - `uv run flow drift-events stats --help` prints all 4 options
  - `uv run --frozen pytest --collect-only -q` shows `1246 + 6 = 1252` tests collected (6 NEW)
- **LOC forecast:** ~20 prod added + ~60 tests added = ~80

### T3.4 — NEW BDD scenarios in `tests/bdd/req_v1_0_drift_events.feature` + step glue (REQ-V1.0.3, D3 + D4)

- **Type:** BDD (3 NEW scenarios in business-domain Given/When/Then phrasing)
- **Strict TDD:**
  - RED: N/A (BDD scenarios are NEW — no existing tests to break)
  - GREEN:
    - `tests/bdd/req_v1_0_drift_events.feature` (NEW) — 3 scenarios:
      1. **`Scenario: Operator reads drift events as default text table`** (REQ-V1.0.2) — `Given` the drift event log has 5 events from 2 changes / `When` the operator runs `flow drift-events list` / `Then` the output contains a fixed-width table with columns `change | decision_id | binding_id | class | detected_at` and 5 data rows
      2. **`Scenario: Operator tails recent drift events`** (REQ-V1.0.3) — `Given` the drift event log has 15 events / `When` the operator runs `flow drift-events tail --limit=5` / `Then` the output contains exactly 5 rows ordered newest-first by `detected_at`
      3. **`Scenario: Operator summarizes drift counts per change`** (REQ-V1.0.3) — `Given` the drift event log has 10 events from 3 changes / `When` the operator runs `flow drift-events stats` / `Then` the output contains a per-change count table with rows for each of the 3 changes
    - `tests/bdd/test_req_v1_0_drift_events_steps.py` (NEW) — step glue using `pytest-bdd` (~30 LOC; imports + step definitions + fixture for tmp_path JSONL setup)
  - REFACTOR: N/A (NEW files)
- **Acceptance:**
  - `uv run --frozen pytest tests/bdd/req_v1_0_drift_events.feature tests/bdd/test_req_v1_0_drift_events_steps.py -v` exits 0 (3 NEW BDD scenarios pass)
  - `uv run --frozen pytest --collect-only -q` shows `1252 + 3 = 1255` tests collected (3 NEW BDD)
  - `rg "REQ-V1.0.[123]" tests/bdd/req_v1_0_drift_events.feature` shows 3 matches (1 per scenario)
  - `rg "@scenario\(" tests/bdd/test_req_v1_0_drift_events_steps.py` shows 3 matches (1 per scenario)
- **LOC forecast:** ~30 BDD feature + ~30 step glue = ~60 (no prod)

---

## Sub-batch D — REQ-V1.0.4: Docs + meta + 12 mypy residuals + spec sync (4 tasks)

### T4.1 — CHANGELOG.md v1.0 entry under `## [1.0.0] - 2026-06-XX` (REQ-V1.0.4)

- **Type:** docs (CHANGELOG v1.0 entry per `proposal.md` §"Approach (proposed)" + `design.md` §"Migration / Rollout")
- **Strict TDD:** N/A (docs-only — no production code, no tests)
- **LOC:** ~35 CHANGELOG
- **Files:**
  - `CHANGELOG.md` (modify — INSERT `## [1.0.0] - 2026-06-XX` section above `[0.9.0]` line with 3 subsections):
    - `### Changed (BREAKING)`: "The JSONL wire format at `~/.flow-engineering/drift_events.jsonl` is now `decision_id: int` (was `str`). This aligns the wire format with `decision_drift.Finding.decision_id: int` post-v0.9.0. Operators consuming the JSONL with `jq` or custom scripts should review the migration note below." (~5 lines)
    - `### Added`: "`flow drift-events {list,tail,stats}` — new read-side CLI command group for the JSONL drift event log. Mirrors the `flow metrics {summary,export,aggregate}` operator mental model. Supports `--since`/`--until`/`--change`/`--event-class`/`--limit`/`--format=text|json|prometheus|csv`/`--path` filters on `list`; `--limit=N=10` default on `tail`; per-event-class + per-change + per-decision-id top-N counts on `stats`. `DriftEventLog.read_all()` gains defensive coercion for legacy `str` `decision_id` lines with a one-time stderr WARN per log-path." (~7 lines)
    - `### Migration`: "Convert existing JSONL files in place: `sed -i 's/\"decision_id\": \"\\([0-9]*\\)\"/\"decision_id\": \\1/g' ~/.flow-engineering/drift_events.jsonl`. Old files continue to read correctly without migration thanks to the defensive coercion shim, but the `sed` silences the one-time WARN." (~3 lines)
- **Acceptance:**
  - `rg "^## \[1\.0\.0\]" CHANGELOG.md` shows 1 match
  - `rg "### Migration|### Removed|### Changed \(BREAKING\)|### Added" CHANGELOG.md` shows the 3 v1.0 subsections (`### Migration`, `### Changed (BREAKING)`, `### Added`)
  - `rg "sed -i" CHANGELOG.md` shows 1 match (the migration note)
- **LOC forecast:** ~35 CHANGELOG added + 0 tests = ~35

### T4.2 — pyproject.toml version bump `0.9.0` → `1.0.0` (REQ-V1.0.4)

- **Type:** docs + meta (version bump per SemVer minor → major for BREAKING wire-format change)
- **Strict TDD:** N/A (docs-only)
- **LOC:** ~1 line
- **Files:**
  - `pyproject.toml:3` — `version = "0.9.0"` → `version = "1.0.0"` (per `proposal.md` §"Public API surface (MODIFIED)" + `design.md` §"Breaking-change policy")
- **Acceptance:**
  - `rg "^version" pyproject.toml` shows `version = "1.0.0"`
  - `uv run flow --version` prints `flow 1.0.0` (or equivalent; depends on CLI version flag — may need a separate edit if `cli.py` reads version from a separate constant)
  - `uv run --frozen pytest --collect-only -q` shows `1255` tests collected (no test count delta)
- **LOC forecast:** ~1 modified + 0 tests = ~1

### T4.3 — 12 mypy residuals cleanup via surgical `# type: ignore` comments at `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439` (REQ-V1.0.4, D5)

- **Type:** code (mypy cleanup — surgical `# type: ignore` per site using the site-specific mypy error code)
- **Strict TDD:**
  - RED: N/A (mypy cleanup is verification-only; tests are already passing at 1255/1255)
  - GREEN: `src/flow_engineering/decision_drift.py` — ADD `# type: ignore[<code>]` at each of the 12 sites using the per-site mypy error code from the current mypy output:
    - Line 127: `# type: ignore[type-arg]` (Missing type arguments for generic type "dict")
    - Line 161: `# type: ignore[type-arg]`
    - Line 203: `# type: ignore[type-arg]`
    - Line 252: `# type: ignore[type-arg]` (Missing type arguments for generic type "list")
    - Line 253: `# type: ignore[type-arg]`
    - Line 262: `# type: ignore[type-arg]`
    - Line 278: `# type: ignore[type-arg]`
    - Line 310: `# type: ignore[arg-type]` (Argument "backend" to "SnapshotManager" has incompatible type "_DummyBackend")
    - Line 372: `# type: ignore[no-untyped-def]` (Function is missing a type annotation)
    - Line 375: `# type: ignore[no-untyped-def]`
    - Line 411: `# type: ignore[arg-type]`
    - Line 439: `# type: ignore[arg-type]`
  - REFACTOR: N/A (12 single-line comments)
- **Acceptance:**
  - `uv run mypy src/flow_engineering/decision_drift.py 2>&1 | tail -3` shows `Found 0 errors in 1 file` (down from 12 in baseline)
  - `uv run --frozen pytest -v` exits 0 (all 1255 tests pass — no regression)
  - `rg "# type: ignore" src/flow_engineering/decision_drift.py` shows 12 matches (one per site)
- **LOC forecast:** ~12 prod (12 comment lines) + 0 tests = ~12

### T4.4 — Capability spec sync: add `## Drift event log JSONL schema` section + v1.0 entry to Versioning table at `openspec/specs/decision-drift/spec.md:408+` (REQ-V1.0.4)

- **Type:** docs (capability spec sync — document the v1.0 wire format per `proposal.md` OQ-3 + `design.md` D1)
- **Strict TDD:** N/A (docs-only)
- **LOC:** ~30 docs
- **Files:**
  - `openspec/specs/decision-drift/spec.md:408+` — UPDATE the Versioning table v1.0 entry to mark status as `ARCHIVED` (or `SHIPPED`) with date `2026-06-XX` and link to `openspec/changes/v1.0-followups/` (~5 LOC)
  - `openspec/specs/decision-drift/spec.md` — ADD a NEW `## Drift event log JSONL schema` section documenting the v1.0 wire format verbatim:
    ```
    ## Drift event log JSONL schema (v1.0)

    Each line of `~/.flow-engineering/drift_events.jsonl` is a JSON object
    with the following keys (key order stable from v0.8.0; `decision_id` type
    changed from `str` → `int` in v1.0):

    | Key          | Type    | Description                                     |
    |--------------|---------|-------------------------------------------------|
    | `change`     | `str`   | Change name (e.g., `decision-reality-drift`)    |
    | `decision_id`| `int`   | Decision ID (post-v0.9.0; was `str` pre-v1.0)   |
    | `binding_id` | `str`   | Binding identifier                              |
    | `class`      | `str`   | Drift class (`LABEL_DRIFT`, `STALE_LOCATION`, ...) |
    | `detected_at`| `float` | Epoch seconds                                   |

    Legacy `decision_id: "42"` (str) lines from pre-v1.0 JSONL files are
    silently coerced to `int` by `DriftEventLog.read_all()` with a one-time
    stderr WARN per log-path. Operators may run the CHANGELOG v1.0 `sed`
    migration to convert in place and silence the WARN.
    ```
    (~25 LOC)
- **Acceptance:**
  - `rg "Drift event log JSONL schema" openspec/specs/decision-drift/spec.md` shows 1 match (the NEW section)
  - `rg "v1\.0-followups" openspec/specs/decision-drift/spec.md` shows 1 match (the Versioning table entry)
  - `rg "decision_id.*int" openspec/specs/decision-drift/spec.md` shows ≥2 matches (the new schema + the v1.0 entry)
- **LOC forecast:** ~30 docs added + 0 tests = ~30

---

## Risks

| # | Risk | Likelihood | Mitigation |
|---|------|------------|------------|
| 1 | **Silent regression** in `DriftEventLog.read_all()` defensive guard — a test site passes a legacy `str` decision_id and the coercion silently succeeds instead of raising (or vice versa: the coercion raises on a value that should pass) | LOW | Per-task TDD with RED test before GREEN impl (T1.1 + T1.3); 1 test for happy-path int + 1 test for legacy str coercion + 1 test for one-time WARN cadence (T1.6 verifies mypy clean); smoke test against a pre-v1.0 JSONL fixture (saved in `tests/fixtures/drift_events_v090_legacy.jsonl` if needed) |
| 2 | **Wire-format BREAKING** for JSONL consumers — old `cat ~/.flow-engineering/drift_events.jsonl \| jq` consumers that pipe `decision_id` to an int-expecting script now work (good); consumers that compared as string ("42" < "9" lex sort) see behavior change (bad but rare) | LOW | T1.4 defensive read guard (silent coercion + one-time stderr WARN per log-path); T4.1 CHANGELOG v1.0 1-line `sed` migration note (per `proposal.md` OQ-3); defensive guard surfaces the issue to operators on first run |
| 3 | **Path B parallel namespace is less elegant than Path A subcommand group** — `flow drift-events` is a sibling command to `flow drift`, not a subcommand. Inconsistent with `flow metrics {summary,export,aggregate}` group pattern (per `observability` PR#2 W1 precedent) | LOW | T4.1 CHANGELOG v1.0 entry documents the parallel-namespace rationale (Path A is BREAKING; Path B preserves operator-UX continuity for `flow drift <change>` callers); revisit Path A in v1.2+ if `flow drift` namespace grows |
| 4 | **Doc drift in `archive/2026-06-27-drift-hardening/verify-report.md:296`** — the report says `DriftEventLog.read_all()` helper is named `iter_drift_events()`. **The actual helper is `read_all()`** at `drift_event_log.py:95-119`. The verify-report's name is stale | LOW | Already noted in `explore.md` R4 + `proposal.md` §"Risks" R4 (the design uses the real symbol name `read_all()` per D2); non-blocking; out-of-scope for v1.0 (post-archive drift-note is a separate follow-up) |
| 5 | **12 mypy residuals in `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439`** — within expected band for `__post_init__` TypeError-on-str enforcement test sites (per `v0.9.0-hardening` verify-report S3) | LOW | T4.3 cleanup adds `# type: ignore[<code>]` (per-site code: `[type-arg]` for 7 sites, `[arg-type]` for 3 sites, `[no-untyped-def]` for 2 sites) to the 12 sites (1 comment per site; ~12 LOC); matches the `v0.9.0-hardening` W1 fix precedent at `proposal.md:V9.2.8` (3 sites cleaned in v0.9.0; v1.0 closes the remaining 12) |
| 6 | **Click subcommand order in `flow drift-events --help`** — the 3 subcommands (`list`, `tail`, `stats`) may render in unexpected order if Click's auto-sort differs from the declaration order | LOW | T2.2 + T3.2 + T3.3 declare subcommands in `list` → `tail` → `stats` order; Click renders them in declaration order; help screen verifies the order matches `flow metrics {summary,export,aggregate}` precedent |
| 7 | **Per-instance `_legacy_warn_emitted` flag vs module-global flag** — per-instance (correct for multi-log CLI invocation) means each new `DriftEventLog(path=...)` instance gets its own WARN cadence; tests that instantiate multiple `DriftEventLog` instances in the same process may see multiple WARNs (one per instance) | LOW | T1.4 design choice per `design.md` D2: per-instance flag is the correct cadence for multi-log CLI invocation; T1.4 tests cover the single-instance cadence (2 legacy lines → 1 WARN); multi-instance cadence is out-of-scope for v1.0 (deferred to a potential v1.0.x patch if operators complain) |

**0 CRITICAL / 0 HIGH / 7 LOW risks.** All mitigations are within the proposed REQ scope or already-documented as low-priority follow-ups.

---

## Acceptance criteria

> **Note**: This is the AGGREGATE acceptance for the entire change, not per-task. Per-task acceptance is in each task's section above.

### Sub-batch A (S1 wire-format flip) — REQ-V1.0.1
- [ ] `DriftEvent.decision_id: int` annotation at `drift_event_log.py:46` (T1.2 GREEN; matches `Finding.decision_id: int` post-v0.9.0)
- [ ] `DriftEvent(decision_id=42, ...)` constructs successfully (T1.1 RED → T1.2 GREEN)
- [ ] `DriftEvent(decision_id="42", ...)` raises `TypeError` (T1.1 RED → T1.2 GREEN)
- [ ] `DriftEventLog.read_all()` defensively coerces legacy `str` `decision_id` to `int` with one-time stderr WARN per log-path (T1.3 RED → T1.4 GREEN)
- [ ] `DriftEventLog.read_all()` emits 1 WARN for N>1 legacy lines (one-time per instance; T1.4 cadence test)
- [ ] `daemon._append_drift_events` no longer coerces via `str(finding.decision_id)` (T1.5 GREEN; `rg "str\(finding\.decision_id\)" src/` shows 0 matches)
- [ ] 1-5 `DriftEvent(decision_id="<str>", ...)` test fixtures migrated to int in `tests/unit/test_drift_event_log.py` (T1.6 REFACTOR)
- [ ] All 1235 tests pass post-T1.6 (1233 baseline + 2 NEW from T1.3 + T1.4)

### Sub-batch B (S2a `list` subcommand) — REQ-V1.0.2
- [ ] `flow drift-events` Click group exists at `cli.py:~1712+` (T2.2 GREEN; `@main.group(name="drift-events")`)
- [ ] `flow drift-events list --since --until --change --event-class --limit --format --path` works for all 4 formats (T2.1 RED → T2.2 GREEN; 4 unit tests)
- [ ] Text-table output mirrors `flow metrics summary` precedent via `_format_drift_events_text` helper (T2.3 REFACTOR)
- [ ] Exit codes per D9: 0=success, 2=invalid args, 3=malformed JSONL (T2.2 GREEN; validated by `test_drift_events_list_invalid_format` + `test_drift_events_list_invalid_since`)

### Sub-batch C (S2b `tail` + `stats` + BDD) — REQ-V1.0.3
- [ ] `flow drift-events tail --limit=10` default + `--change/--event-class/--format` filters work (T3.1 RED → T3.2 GREEN; 5 unit tests)
- [ ] `flow drift-events stats --change --since --until --format` renders per-event-class + per-change + per-decision-id top-N counts in a fixed-width table (T3.3 GREEN; 6 unit tests)
- [ ] 3 NEW BDD scenarios in `tests/bdd/req_v1_0_drift_events.feature` (T3.4 GREEN; list default text + tail newest-first + stats per-change counts; + step glue in `tests/bdd/test_req_v1_0_drift_events_steps.py`)

### Sub-batch D (Docs + meta + tech-debt) — REQ-V1.0.4
- [ ] `CHANGELOG.md` `## [1.0.0] - 2026-06-XX` entry with `### Changed (BREAKING)` + `### Added` + `### Migration` sections (T4.1; 1-line `sed` migration note included)
- [ ] `pyproject.toml:3` `version = "1.0.0"` (T4.2)
- [ ] 12 `# type: ignore[<code>]` comments at `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439` (T4.3; per-site code: 7× `[type-arg]` + 3× `[arg-type]` + 2× `[no-untyped-def]`); `uv run mypy src/flow_engineering/decision_drift.py 2>&1 | tail -3` shows `Found 0 errors in 1 file`
- [ ] `openspec/specs/decision-drift/spec.md` v1.0 `## Drift event log JSONL schema` section documents the v1.0 wire format verbatim + Versioning table v1.0 entry marked ARCHIVED/SHIPPED with link to `openspec/changes/v1.0-followups/` (T4.4)

### Aggregate (full change)
- [ ] All 1255 tests pass (1233 baseline + 2 S1 NEW + 4 S2a RED + 5 S2b tail RED + 6 S2b stats RED + 3 BDD = 1253 + 2 REFACTOR = 1255; verified via `uv run --frozen pytest`)
- [ ] All 24 BDD scenarios pass (21 existing + 3 NEW from T3.4; verified via `pytest tests/bdd/`)
- [ ] `ruff check` clean on changed files (`uv run ruff check src/flow_engineering/{drift_event_log.py,daemon.py,cli.py,decision_drift.py}` exits 0)
- [ ] `mypy src/flow_engineering/decision_drift.py` shows 0 errors (down from 12 baseline; T4.3 12-site cleanup)
- [ ] `flow drift-events --help` lists 3 subcommands (`list`, `tail`, `stats`)
- [ ] `flow drift <change>` exit-code semantics unchanged (0 still-valid / 1 stale / 2 unable_to_verify / 3 usage error per REQ-11; NON-REGRESSION)
- [ ] `flow drift <change> --json` envelope byte-identical to v0.9.0 (the JSON envelope uses `Finding.decision_id: int` from the in-memory dataclass which has been int since v0.9.0; NON-REGRESSION)
- [ ] Strict TDD evidence: every public change has RED → GREEN → REFACTOR history in commit log; per-commit work-unit splits per `work-unit-commits` skill (10-15 commits each ≤30 LOC delta)
- [ ] Drift detector (REQ-9..16) behavior unchanged for end users — the wire-format change is internal to `DriftEvent` serialization only
- [ ] `_legacy_warn_emitted` flag is per-instance (per-log-path), so multiple invocations on different log files each get their own WARN (correct cadence for multi-log CLI invocation)

---

## Open follow-ups for sdd-archive (after PR merge)

- Spec catalog baseline retro-fill for prior capability specs (REQ-9..16, REQ-28..34) — `openspec/specs/` bootstrap pattern continues
- MEMORY.md / AGENTS.md update for new v1.0 wire-format + `flow drift-events` CLI surface (none expected; CHANGELOG is the operator-facing surface)
- Cross-impact verification for all 9 prior changes (decision-code-linking, decision-reality-drift, vector-semantic-search, cross-project-federation, graph-snapshots, observability, prompt-registry, drift-hardening, v0.9.0-hardening)
- README updates for new `flow drift-events` CLI surface + v1.0 wire-format (likely small; CHANGELOG is the operator-facing surface; README may need 1-line addition pointing to `flow drift-events --help`)

---

## Coordination notes

- **MANDATORY**: per-batch closeout docs (mirrors `v0.9.0-hardening` `apply-progress/merged.md` precedent)
- **MANDATORY**: per-commit work-unit splits per `work-unit-commits` skill (each commit ≤30 LOC delta; 13-15 commits total)
- **MANDATORY**: `flow drift-events` Path B is parallel-namespace (NON-BREAKING for `flow drift <change>` callers); the existing `@main.command() def drift(...)` at `cli.py:1712-1809` stays UNCHANGED
- **MANDATORY**: doc drift fix from `archive/2026-06-27-drift-hardening/verify-report.md:296` (says `iter_drift_events()`; actual is `DriftEventLog.read_all()`) — already corrected in this design (D2 uses real symbol name); post-archive drift-note in archived verify-report is a separate follow-up
- **6 SKILL.md runtime files**: NOT touched in this change (v1.0-followups doesn't change the SDD API contract that the SKILL.md files document; the DriftEvent.decision_id flip is internal-only and the `flow drift-events` CLI is documented in CHANGELOG v1.0 + capability spec — no SKILL.md update needed)
- **Mypy residuals**: 12 in `decision_drift.py` at lines 127/161/203/252/253/262/278/372/375/310/411/439 (all suppressed via T4.3 site-specific `# type: ignore[<code>]` comments); mypy baseline 12 → 0

---

## Carry-forwards (NOT in v1.0)

### Deferred to v1.1

- **`DriftEventLog` JSONL rotation policy** (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var + auto-rotation at threshold + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` gzip-and-rotate cron) — DEFERRED to v1.1 alongside `metrics.jsonl` rotation (REQ-44) per capability spec `spec.md:410` "DriftEventLog rotation (v1.1 alongside metrics rotation)"
- **REQ-51** (prompt_renders.jsonl sink) — independent of drift events; the prompt-render audit trail is its own REQ
- **REQ-52** (flow prompt-events observability counters) — pairs with REQ-51
- **REQ-53** (docs/prompts.md auto-generated from prompt registry) — pairs with REQ-51/52

### Deferred to v1.2+ (revisit only if `flow drift` namespace grows)

- **Path A subcommand group rename** (BREAKING `flow drift check <change>` + `flow drift events ...`) — more idiomatic with `flow metrics {summary,export,aggregate}` group pattern but BREAKING for every existing `flow drift <change>` caller. Revisit only if the `flow drift` namespace grows further in v1.2+

### Deferred to `federated-drift-events` follow-up

- **Cross-project federation for drift events** (`flow drift-events --project=<key>` filter) — requires modifying every record helper signature to inject a `project` field

### Already RESOLVED in v1.0-followups (per this tasks.md)

| Source | Item | Resolution evidence |
|--------|------|---------------------|
| `drift-hardening` verify-report #296 S1 | `DriftEvent.decision_id: str` (JSONL wire format) vs `Finding.decision_id: int` (Python) inconsistency | T1.1 + T1.2 + T1.3 + T1.4 + T1.5 + T1.6 — flip to `int` + defensive coercion + daemon coercion removal + test migration |
| `drift-hardening` verify-report #296 S2 | `flow drift events` read-side CLI deferred to v1.0 | T2.1 + T2.2 + T2.3 + T3.1 + T3.2 + T3.3 + T3.4 — NEW `flow drift-events {list,tail,stats}` group + 4 formats + 3 BDD scenarios |
| `drift-hardening` verify-report #296 | `iter_drift_events()` doc drift (verify-report says this name; actual is `read_all()`) | T1.3 + T1.4 use the real symbol name `DriftEventLog.read_all()` (per `drift_event_log.py:95-119`) |
| `v0.9.0-hardening` verify-report S3 | 12 mypy residuals in `decision_drift.py` within expected band | T4.3 — `# type: ignore[<code>]` cleanup at the 12 sites (7× `[type-arg]` + 3× `[arg-type]` + 2× `[no-untyped-def]`) |
| capability spec `spec.md:410` S2 | ruff `--unsafe-fixes` on `decision_drift.py` | NOT in v1.0 scope (out-of-scope per `proposal.md` §"Carry-forwards"; the 4 ruff warnings are deferred to a separate tech-debt follow-up; only the 12 mypy residuals are in REQ-V1.0.4) |
| capability spec `spec.md:410` | `DriftEventLog rotation` (v1.1 alongside metrics rotation) | DEFERRED to v1.1 (per `proposal.md` §"Carry-forwards explicitly NOT touched") |

---

## Workload next step

Ready for `sdd-apply v1.0-followups` sub-batch A (T1.1..T1.6 — REQ-V1.0.1 S1 wire-format flip). The 6 tasks fit comfortably in a single delegation (≤150 LOC prod / ≤3 tasks per the `apply-batches-split-into-6-tasks-per-delegation` Engram #112 pattern — slightly over 3 but under 6 which is the documented ceiling for v0.9.0-hardening precedent). The single-PR shape is pre-decided; no chained-PR decision needed.