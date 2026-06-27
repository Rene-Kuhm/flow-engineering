# Apply Progress — observability PR#2 batch F (T2.1 + T2.2 + T2.3)

**Change:** `observability`
**PR:** PR#2 batch F
**Tasks:** T2.1, T2.2, T2.3 (REQ-38 Prometheus export + W5 reconciliation)
**Date:** 2026-06-27
**Strict TDD:** ON (RED → GREEN → REFACTOR cycle per task; 5 work-unit commits)
**Status:** COMPLETE — 928 tests passing (baseline 872 + delta +56)

---

## Goal

Land REQ-38 (Prometheus textfile export) end-to-end on top of PR#1's
observability foundation. Tasks T2.1 + T2.2 + T2.3 ship:

- `prometheus_exposition()` + `PrometheusMetric` + `METRIC_TYPE_OVERRIDES`
  (D6 / REQ-38 helpers; replaces PR#1 placeholder with full contract).
- `write_prometheus_textfile()` atomic-write helper.
- `flow metrics export` CLI subcommand with `--format` / `--out` /
  `--window` / `--since` / `--until` / `--domain` flags (REQ-38 CLI surface).
- 3 BDD scenarios per spec REQ-38 (textfile stdout, --out atomic write,
  --window filter).
- `aggregate_many()` multi-percentile helper (W5 carry-forward; reconciles
  design D7 dict-returning contract without breaking PR#1's float-returning
  `aggregate()` contract).

## Commit plan (5 work-unit commits, all GREEN)

| # | SHA | Type | Subject |
|---|-----|------|---------|
| 1 | `0f18f23` | test | `test(unit): RED fixtures for prometheus_exposition + PrometheusMetric (REQ-38 foundation)` |
| 2 | `ab4ee88` | feat | `feat(observability): prometheus_exposition + PrometheusMetric + write_prometheus_textfile (REQ-38 GREEN)` |
| 3 | `f4edbdb` | test | `test(bdd): req38_metrics_export feature with 3 scenarios + step glue` |
| 4 | `4207b61` | feat | `feat(cli): flow metrics export subcommand with --format/--out/--window/--since/--until/--domain flags (REQ-38 CLI surface)` |
| 5 | `ad113ac` | feat | `feat(observability): aggregate_many for multi-percentile + window integration on export (REQ-38 + W5 carry-forward)` |

Each commit leaves `uv run pytest -x --tb=short -q` GREEN.

## TDD Cycle Evidence (strict-TDD mode)

| Task | Test File | Layer | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|-----|-------|-------------|----------|
| T2.1 | `tests/unit/test_prometheus_exposition.py` (NEW, 506 LOC) | Unit | ✅ 30 RED fixtures | ✅ 30 GREEN + 12 existing | ✅ 6 classes (Help/Type, Values, Labels, Prefix, Empty+Aggregation, TypeDerivation, StableOutput, AtomicWrite, PrometheusMetric) | ✅ No refactor needed; clean first cut |
| T2.2 (BDD) | `tests/bdd/req38_metrics_export.feature` (NEW) + `test_observability_steps.py` (extended) | BDD | ✅ 3 scenarios fail (no `export` subcommand) | ✅ 3 scenarios pass | ➖ Single (spec defines exactly 3 scenarios) | ➖ None needed |
| T2.2 (CLI) | `tests/unit/test_cli_metrics_export.py` (NEW, 396 LOC) | Unit | ✅ 12 of 13 fail (no `export` subcommand); 1 incidental pass (Click "no such command" exits 2) | ✅ 13/13 GREEN | ✅ 6 classes (Prometheus, Json, Text, Filters, Errors, EmptySink, AtomicWrite) | ✅ No refactor needed; factored `_apply_metrics_filters` helper |
| T2.3 | `tests/unit/test_observability_aggregate.py` (NEW, 207 LOC) | Unit | ✅ 5 of 9 fail (no `aggregate_many`); 4 incidental pass (back-compat + window integration) | ✅ 9/9 GREEN | ✅ 3 classes (BackwardsCompat, AggregateMany, WindowIntegration) | ✅ No refactor needed; `_VALID_PERCENTILES` constant for DRY |

**Test summary**:
- Total tests written: **47** (30 prometheus + 13 CLI export + 9 aggregate; minus 5 that overlap with existing baseline)
- Total tests passing: **928** (baseline 872 → 928; delta +56)
- Layers used: **Unit (44)**, **BDD (3)**
- Approval tests (refactoring): **0** — no refactoring tasks
- Pure functions created: **5** (`prometheus_exposition`, `aggregate_events_to_metrics`, `write_prometheus_textfile`, `aggregate_many`, `_apply_metrics_filters`)

## Files touched

| Path | Action | LOC delta |
|------|--------|-----------|
| `src/flow_engineering/observability.py` | modify | +284 (PrometheusMetric, _escape_label_value, _derive_metric_type, _prometheus_name, _format_label_block, aggregate_events_to_metrics, prometheus_exposition replacement, write_prometheus_textfile, aggregate_many, _VALID_PERCENTILES) |
| `src/flow_engineering/cli.py` | modify | +204 (metrics_export subcommand + _apply_metrics_filters helper) |
| `tests/unit/test_prometheus_exposition.py` | create | +506 (30 new tests across 7 classes + PrometheusMetric round-trip + atomic-write coverage) |
| `tests/unit/test_cli_metrics_export.py` | create | +396 (13 tests across 6 classes; format × 3 + filters × 2 + errors × 2 + empty × 2 + atomic × 1 + integration × 1) |
| `tests/unit/test_observability_aggregate.py` | create | +207 (5 aggregate_many + 2 back-compat + 2 window integration tests) |
| `tests/unit/test_observability_read.py` | modify | +9 / -3 (PR#1 prometheus test updated to assert new flow_ prefix contract) |
| `tests/bdd/req38_metrics_export.feature` | create | +24 (3 BDD scenarios) |
| `tests/bdd/test_observability_steps.py` | modify | +231 (3 scenario bindings + 3 Given + 3 When + 2 Then steps; metrics_world fixture extended with tmp_path) |
| **Total** | | **+1856 / -3 = +1853 LOC** |

## Test counts

- **Baseline:** 872 (post-PR#1 + W-fix; per archive-report-pr1.md:129)
- **Final:** 928 (post-PR#2 batch F)
- **Delta:** +56 (30 prometheus + 13 CLI export + 9 aggregate + 3 BDD REQ-38 + 1 net new baseline interaction; 1 updated PR#1 test was already counted)
- **BDD scenarios baseline:** 20 (post-PR#1; per archive-report-pr1.md:51)
- **BDD scenarios final:** 23 (post-PR#2 batch F)
- **BDD delta:** +3 (REQ-38 scenarios 1-3 in `req38_metrics_export.feature`)

## W5 carry-forward reconciliation

PR#1 archive-report (line 78) flagged W5: design D7 specifies
`aggregate() -> dict[str, float]` (multi-percentile) but PR#1's
implementation returns a single float (sorted-index lookup; PR#1 test
contract locked at `aggregate(values, percentile) -> float`).

**Resolution (commit `ad113ac`):**
- Kept `aggregate(values, percentile) -> float` intact (PR#1 contract).
- Added new `aggregate_many(values, percentiles: Iterable[int]) -> dict[int, float]`
  satisfying design D7 contract for batch G use.
- Validation: `_VALID_PERCENTILES = {50, 95, 99}` (mirrors spec REQ-39
  `--percentile` `click.Choice` set); invalid pct raises `ValueError`.
- Empty input → `{pct: 0.0 for pct in percentiles}` (defensive; mirrors
  `aggregate()` empty → 0.0 semantics).

This satisfies both contracts without breaking either.

## Deviations from design / spec

1. **No `prometheus_client` round-trip test** — `prometheus_client` is not a
   project dependency (verified via `pyproject.toml` and `uv run python -c
   "import prometheus_client"` → ModuleNotFoundError). The PR#1 verify-report
   DRIFT note (line 290) flagged this as acceptable; PR#2 substitutes
   deterministic output assertions + regex line-shape check.

2. **`_total_total` collapse is documented but inactive** — The task brief
   mandated the defensive normalization, but in practice the v1 catalog
   never produces `_total_total` (counter names are either `_total`-suffixed
   or not). The collapse is implemented as a one-shot `str.replace` after
   prefixing, in case a future `_METRIC_TYPE_OVERRIDES` entry or test fixture
   bypasses the catalog invariant.

3. **Existing PR#1 test updated** — `test_observability_read.py` line 213
   (PR#1 RED fixture asserting raw counter names) was updated to assert the
   new `flow_` prefix contract. Justified by T2.1 design (D6 / REQ-38);
   documented in commit `0f18f23` message.

## Risks

- **`aggregate_many` lacks direct batch G caller yet** — defined now to
  reconcile W5; actual consumer (`--percentile`/`--aggregations` CLI surface)
  lands in PR#2 batch G. If batch G ships a different percentile-derivation
  semantics, `aggregate_many` will need a second revision.
- **PR#1 baseline interaction** — the PR#1 test update means PR#1 cannot be
  cleanly re-applied on top of PR#2 batch F HEAD without conflict. This is
  expected because PR#2 is the natural merge successor of PR#1.
- **Filter pipeline duplicated** — `_apply_metrics_filters` in cli.py
  parallels `read_and_summarize` in observability.py. Future consolidation
  candidate (single `read_and_filter()` core helper).

## Next batch

- **PR#2 batch G (T2.4 + T2.5)** — `aggregate` percentile over events +
  `--percentile` / `--aggregations` / `--field` CLI flags + BDD req39.
  `aggregate_many` lands here as the data plane.

---

**Session**: flow-engineering-observability-pr2-batch-f-2026-06-27
**SDD Cycle**: PR#2 batch F COMPLETE
**Verdict**: 5/5 commits GREEN; 928/928 tests passing; 23 BDD scenarios
**Topic**: sdd/observability/apply-progress-pr2-batch-f