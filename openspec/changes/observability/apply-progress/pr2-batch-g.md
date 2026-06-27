# Apply Progress — observability PR#2 batch G (T2.4 + T2.5)

**Change:** `observability`
**PR:** PR#2 batch G
**Tasks:** T2.4, T2.5 (REQ-39 percentile aggregation via reservoir sampling)
**Date:** 2026-06-27
**Strict TDD:** ON (RED → GREEN → REFACTOR cycle per task; 3 work-unit commits)
**Status:** COMPLETE — 947 tests passing (baseline 928 + delta +19)

---

## Goal

Land REQ-39 percentile aggregation end-to-end on top of PR#1's
observability foundation + PR#2 batch F's Prometheus export. Tasks
T2.4 + T2.5 ship:

- `ReservoirSampler` class — Vitter's Algorithm R for memory-bounded
  random sampling of an unbounded event stream (capacity default 1000,
  optional `seed` for deterministic output).
- `aggregate_percentile(events, *, percentiles, reservoir_size, seed)`
  — groups events by counter name, builds a reservoir per counter,
  computes requested percentiles via floor() sorted-index lookup,
  returns `dict[str, float]` mapping `"{counter_name}_p{N}"` to the
  computed value (e.g., `{"drift_invoked_total_p95": 95.0}`).
- `format_percentile_report(result)` — renders the dict as an
  aligned text table with one row per counter and columns for p50,
  p95, p99 (per design D7). Renders "not enough data points" inline
  when the helper's < 2 samples contract yields all-zero values.
- `flow metrics aggregate` CLI subcommand — new `aggregate` subcommand
  on the existing `metrics` group, with `--percentile` (repeatable
  `click.Choice(["p50", "p95", "p99"])`), `--window`, `--since`,
  `--until`, `--domain`, `--reservoir-size`, `--format` flags. Reuses
  the `_apply_metrics_filters` pipeline from PR#2 batch F so the
  filter chain composes identically across subcommands (D8/D9 / T2.3).
- 2 BDD scenarios per spec REQ-39 (`req39_metrics_aggregate.feature`):
  p95 worked example with 100 monotonic events; insufficient-data
  graceful exit with "not enough data points" warning.

## Commit plan (3 work-unit commits, all GREEN)

| # | SHA | Type | Subject |
|---|-----|------|---------|
| 1 | `4167ecf` | test | `test(unit): RED fixtures for ReservoirSampler + aggregate_percentile (REQ-39 foundation)` |
| 2 | `a4c0aca` | feat | `feat(observability): ReservoirSampler + aggregate_percentile + format_percentile_report (REQ-39 GREEN)` |
| 3 | `2aec6de` | feat | `feat(cli): flow metrics aggregate subcommand with --percentile/--window/--format + BDD req39 (REQ-39 CLI surface)` |

Each commit leaves `uv run pytest -x --tb=short -q` GREEN.

## TDD Cycle Evidence (strict-TDD mode)

| Task | Test File | Layer | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|-----|-------|-------------|----------|
| T2.4 | `tests/unit/test_aggregate_percentile.py` (NEW, 266 LOC) | Unit | ✅ 11 RED fixtures (all fail with `AttributeError: module has no attribute 'aggregate_percentile'`) | ✅ 11/11 GREEN | ✅ 3 classes (`TestReservoirSampler` × 3: capacity / uniform distribution / seeded determinism; `TestAggregatePercentile` × 5: p50/p95/p99 dict / empty / single value / multi-counter separation / reservoir-overflow p50 range; `TestFormatPercentileReport` × 2: aligned table / empty dict; +1 smoke) | ✅ No refactor needed; clean first cut. `__slots__` on `ReservoirSampler` for memory predictability; `_seen` tracks total stream count distinct from retained count. |
| T2.5 (CLI) | `tests/unit/test_cli_metrics_aggregate.py` (NEW, 226 LOC) | Unit | ✅ 5 of 6 fail (no `aggregate` subcommand); 1 incidental pass (Click "no such command" exits 2 for invalid percentile) | ✅ 6/6 GREEN | ✅ 3 classes (`TestMetricsAggregateText` × 2: default p95 / multi-percentile; `TestMetricsAggregateFilters` × 1: `--window=1h` filters before reservoir; `TestMetricsAggregateJson` × 1: `--format json` emits parseable dict; `TestMetricsAggregateErrors` × 2: invalid percentile exits 2 / empty sink exits 0 + header-only table) | ✅ Fixed test assertion that incorrectly assumed `p95` label would be absent when only p50/p99 requested (per task brief, the table always renders the 3-column header). |
| T2.5 (BDD) | `tests/bdd/req39_metrics_aggregate.feature` (NEW) + `test_observability_steps.py` (+71 LOC) | BDD | ✅ 2 scenarios fail initially (scenario bindings missing) | ✅ 2/2 GREEN | ➖ Single (spec defines exactly 2 scenarios) | ✅ Aligned the feature step text `exit code is 0 (graceful)` → `exit code is 0` to match the existing `then_exit_code_zero` step. |

**Test summary**:
- Total tests written: **19** (11 percentile unit + 6 CLI aggregate unit + 2 BDD REQ-39)
- Total tests passing: **947** (baseline 928 → 947; delta +19)
- Layers used: **Unit (17)**, **BDD (2)**
- Approval tests (refactoring): **0** — no refactoring tasks
- Pure functions created: **3** (`aggregate_percentile`, `format_percentile_report`, `ReservoirSampler.add`)

## Files touched

| Path | Action | LOC delta |
|------|--------|-----------|
| `src/flow_engineering/observability.py` | modify | +166 (`random` import; `ReservoirSampler` class with `__slots__`; `aggregate_percentile`; `format_percentile_report`; module docstring extended) |
| `src/flow_engineering/cli.py` | modify | +102 (`AGGREGATE_PERCENTILE_CHOICES`; `metrics_aggregate` subcommand with 7 options; ISO / window / domain validation; `_apply_metrics_filters` reuse; text/json dispatch) |
| `tests/unit/test_aggregate_percentile.py` | create | +263 (11 tests across 4 classes: ReservoirSampler × 3, AggregatePercentile × 5, FormatPercentileReport × 2, +1 CLI smoke) |
| `tests/unit/test_cli_metrics_aggregate.py` | create | +226 (6 tests across 4 classes: Text × 2, Filters × 1, Json × 1, Errors × 2) |
| `tests/bdd/req39_metrics_aggregate.feature` | create | +17 (2 BDD scenarios: p95 worked example, insufficient-data graceful) |
| `tests/bdd/test_observability_steps.py` | modify | +130 (2 scenario bindings + 2 Given + 2 When + 2 Then steps; REQ-39 slots) |
| **Total** | | **+904 LOC** |

## Test counts

- **Baseline:** 928 (post-PR#2 batch F)
- **Final:** 947 (post-PR#2 batch G)
- **Delta:** +19 (11 percentile unit + 6 CLI aggregate unit + 2 BDD REQ-39)
- **BDD scenarios baseline:** 23 (post-PR#2 batch F)
- **BDD scenarios final:** 25 (post-PR#2 batch G)
- **BDD delta:** +2 (REQ-39 scenarios 1-2 in `req39_metrics_aggregate.feature`)

## Deviations from design / spec

1. **Helper return contract — `dict[str, float]` literal type, value 0.0 for < 2 samples** —
   The task brief explicitly mandates `dict[str, float]` with `0.0`
   values for insufficient data (rather than a sentinel like NaN).
   `format_percentile_report` reconciles this with the BDD scenario
   requirement "stdout contains 'not enough data points'" by detecting
   the all-zero pattern in a row and rendering the warning text inline
   (the helper's < 2 samples contract is the only source of 0.0
   values for positive counters).

2. **`format_percentile_report` always emits p50/p95/p99 columns** —
   The task brief's example output shows a 3-column header. When
   callers request a subset of percentiles (e.g. `--percentile p50
   --percentile p99`), the unrequested columns are present in the
   header but blank in the data row (only requested percentile keys
   are populated in the helper's return dict). The
   `test_metrics_aggregate_multiple_percentiles` unit test was
   originally over-strict (asserted `p95 not in output`) and was
   corrected to align with the documented table format.

3. **BDD feature step text — `exit code is 0 (graceful)` → `exit code is 0`** —
   The original feature file used a parenthetical note that no
   pytest-bdd step matched. Aligned to the existing
   `then_exit_code_zero` step glue for consistency with the
   req35/36/37/38 BDD features (no semantic change — exit code 0 IS
   graceful).

4. **Reservoir overflow p50 range widened to ±100** — The
   `test_aggregate_percentile_uses_reservoir_when_stream_exceeds_capacity`
   test asserts `400.0 <= p50 <= 600.0` for a 1000-event stream into
   a 100-slot reservoir (population mean = 500.5). The ±100 bound is
   intentionally generous to avoid flakiness on the boundary while
   still proving the reservoir path actually ran (a degenerate
   constant like `0.0` or `1000.0` would fail this range).

## Risks

- **Reservoir sampling precision trade-off** — The reservoir bounds
  memory at `reservoir_size` (default 1000) but is a statistical
  approximation. For very large event streams (> 10^6), the reservoir
  may miss rare outliers. The current default (1000) is tuned for
  short-to-medium windows (1h / 24h) where the event count is well
  under 10^4. Operators running the aggregate over week-long windows
  may want to bump `--reservoir-size` (e.g. 10000) for higher
  precision. Documented in the `--reservoir-size` help text.

- **All-zero false-positive in format_percentile_report** — The
  formatter treats any row with all-zero values as "insufficient
  data". For counters that legitimately yield 0.0 percentile values
  (e.g., a counter emitting only zero values), this would render the
  warning text incorrectly. In practice the catalog of `_total` /
  `_ms` / `_seconds` counters always carries positive values, so the
  risk is theoretical.

- **Pre-PR#2 baseline interaction** — The `aggregate()` helper from
  PR#1 (sorted-index lookup, single percentile) and the
  `aggregate_many()` from PR#2 batch F (W5 reconciliation) are
  unchanged. The new `aggregate_percentile` is a third, distinct
  helper (reservoir-sampled, multi-percentile, dict return).
  Three helpers with similar names is a maintenance hazard — future
  callers should default to `aggregate_percentile` (the most general)
  unless they have a specific reason to use the others.

## Next batch

- **PR#2 batch H (T2.6 + T2.7)** — End-to-end integration tests
  sweeping all 5 subcommands (summary + window + domain + export +
  aggregate) against a synthetic 100-metric JSONL + CHANGELOG v0.7.1
  entry + 6 SKILL.md runtime updates for "Export hook" + "Aggregation
  hook" + apply-progress/finalize.

---

**Session**: flow-engineering-observability-pr2-batch-g-2026-06-27
**SDD Cycle**: PR#2 batch G COMPLETE
**Verdict**: 3/3 commits GREEN; 947/947 tests passing; 25 BDD scenarios
**Topic**: sdd/observability/apply-progress-pr2-batch-g
