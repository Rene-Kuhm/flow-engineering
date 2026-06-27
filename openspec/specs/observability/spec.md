# Observability Capability Spec

## Purpose

Cross-version capability spec for `observability` — the read-side of the
`metrics.jsonl` sink introduced in change #1 (REQ-8, `decision-code-linking` v0.2.0).

This capability spec is the first entry in the project's `openspec/specs/`
baseline (the directory was empty before change #6). Subsequent capability
changes (`prompt-registry` etc.) follow the same convention: a kebab-case
folder per capability, a `spec.md` inside, mirroring the proposal-to-spec
shape from `openspec/changes/`.

## Source

The authoritative requirements + BDD scenarios live in:

- `openspec/changes/observability/spec.md` (the change spec; this file
  bootstraps a stable, cross-version copy of REQ-35..39).
- `openspec/changes/observability/design.md` (D1-D12 resolved).

This file does NOT duplicate the change spec verbatim — it carries the
canonical requirement statements and BDD scenarios that survive once the
change ships. Future deltas (`engine-instrumentation`,
`federated-observability`) extend this baseline rather than forking it.

## Requirements

### REQ-35 — `flow metrics summary` text dashboard

The system SHALL provide a `flow metrics summary` subcommand that reads
`~/.flow-engineering/metrics.jsonl`, groups counter events by domain via
the `DOMAIN_BY_PREFIX` lookup table, and renders a per-domain dashboard to
stdout. Flags:

- `--format text|json|json-detailed` (default `text`).
- `--window 1h|24h|7d` (optional; rolling time-window filter, REQ-36).
- `--domain binding|drift|vector|snapshot` (optional; prefix-based slice,
  REQ-37).

Exit codes (D9): `0` success (including default-empty), `2` invalid flag
value. Empty / no-match → exit `0` with `No metrics recorded yet.`.

### REQ-36 — Time window filter (`--since` / `--until` / `--window`)

The system SHALL extend `flow metrics` with three time-window flags:

- `--since=<iso>` filters events to `ts >= <iso>` (lexicographic ISO
  comparison; `Z`-suffixed UTC = fixed-width, so lex == chronological).
- `--until=<iso>` filters events to `ts <= <iso>`.
- `--window=<1h|24h|7d>` is a rolling shorthand for `--since=<now - duration>`.
  Case-insensitive. Composes with `--domain` (REQ-37) and `--summary` (REQ-35).

Invalid `--since` / `--until` ISO strings exit `3` with a JSON error on
stderr (D9 data error). Invalid `--window` value exits `2` (D9 usage
error, handled by `click.Choice`).

### REQ-37 — Cross-domain slice (`--domain`)

The system SHALL extend `flow metrics` with a `--domain=<D>` flag that
filters events to counters whose name starts with one of the prefixes
registered for `D` in `DOMAIN_BY_PREFIX`. Accepted values:

| Domain    | Registered prefixes                                                  |
|-----------|----------------------------------------------------------------------|
| binding   | `suggest_`, `bindings_`, `inspect_`                                  |
| backfill  | `backfill_`                                                          |
| drift     | `drift_`                                                             |
| vector    | `vector_`, `reindex_`                                                |
| federated | `federated_`                                                         |
| snapshot  | `snapshot_`                                                          |
| metadata  | `update_observation_metadata_`, `project_tag_`                       |
| engine    | (RESERVED for REQ-42; v1 emits no `engine_*`)                        |

When `--domain` is absent, no domain filter is applied. Unknown domain
values exit `2` with a JSON error on stderr (D9).

### REQ-38 — Prometheus textfile export (`flow metrics export` subcommand)

The system SHALL expose Prometheus textfile export via a dedicated
`flow metrics export` subcommand (the legacy `flow metrics` flat dump
and `flow metrics --json` close contract per REQ-8 are preserved on
the parent `metrics` group). Flags:

- `--format text|json|prometheus` (default `text`).
- `--out=<path>` writes atomically (`tempfile.NamedTemporaryFile` +
  `os.replace`) per design D10. Write failures exit `4`.
- `--window=<1h|24h|7d>` rolling shorthand (composes with `--domain`,
  `--since`, `--until` per REQ-36 + REQ-37).
- `--since=<iso>` / `--until=<iso>` absolute window (REQ-36).
- `--domain=<D>` prefix slice (REQ-37).

The Prometheus textfile exposition emits one metric line per
`(counter_name, label-tuple)` combination with the type derivation
rule: `_total` → `counter`; `_ms` / `_seconds` → `summary`;
bare → `gauge`. Override map: `METRIC_TYPE_OVERRIDES` (D6 priority 1).

### REQ-39 — Percentile aggregation (`flow metrics aggregate` subcommand)

The system SHALL expose percentile aggregation via a dedicated
`flow metrics aggregate` subcommand. Flags:

- `--percentile <p50|p95|p99>` (repeatable; at least one required).
- `--reservoir-size=<int>` (default `1000`; Vitter's Algorithm R).
- `--window=<1h|24h|7d>` / `--since` / `--until` / `--domain` (REQ-36
  + REQ-37, same semantics as the `export` subcommand).
- `--format text|json` (default `text`; aligned table vs JSON dict).

Percentile uses a floor(sorted-index) lookup (`int((n - 1) * pct / 100)`
on the sorted sample list) per design D7 — equivalent to
`statistics.quantiles(data, n=100, method="inclusive")` for the
worked example `aggregate(list(range(10, 1001, 10)), 95) → 950` (the
midpoint sample; the inclusive-quantile reference value is `950.5`,
off by one index — see drift note below).

**Drift note (carried forward from PR#1 W5):** the implementation
preserves the PR#1 `aggregate(values, percentile) → float` contract
(sorted-index lookup) and the design D7 `aggregate → dict[str, float]`
contract is satisfied via the additive `aggregate_many()` shim
(`dict[int, float]`) and `aggregate_percentile(events, ...)` reservoir
helper (`dict[str, float]`). Operators should default to
`aggregate_percentile` (the most general) for new code.

Counters with fewer than 2 numeric samples render `not enough data
points` inline in the text-table output (and an empty value in JSON)
— the command STILL exits `0`. Invalid `--percentile` value exits `2`
(handled by `click.Choice`). Invalid `--reservoir-size` exits `2`.

Text output renders an aligned 3-column table per the
`format_percentile_report` helper:

```
Counter                                p50    p95    p99
bindings_confirmed_total                 2      2
drift_contradicted_total       not enough data points
...
```

Each requested percentile gets a column header; unrequested columns
appear blank in the data rows. The `<counter_name> <pct>: <value>`
per-line shape from the original PR#1 spec was replaced by the
table format during PR#2 (operator-friendly alignment for parallel
counter comparison).

## BDD scenarios

The 11 BDD scenarios from `openspec/changes/observability/spec.md` carry
verbatim into this baseline:

- `tests/bdd/req35_metrics_summary.feature` — 2 scenarios (summary
  per-domain, empty sink).
- `tests/bdd/req36_metrics_window.feature` — 2 scenarios (`--since`
  absolute, `--window=1h` rolling).
- `tests/bdd/req37_metrics_domain.feature` — 2 scenarios
  (`--domain=snapshot` filter, no `--domain` = all).
- `tests/bdd/req38_metrics_export.feature` — 3 scenarios
  (stdout exposition, `--out` atomic write, `--window` composition).
- `tests/bdd/req39_metrics_aggregate.feature` — 2 scenarios
  (p95 worked example, insufficient data warning).

Step definitions land in `tests/bdd/test_observability_steps.py`
(shared across all 5 features per change #6 design D12).

## Counter catalog (v1.0 baseline)

After `graph-snapshots` (change #5) archived, the 31-counter catalog is:

| Domain    | Counters                                                                                          |
|-----------|---------------------------------------------------------------------------------------------------|
| binding   | `suggest_invoked_total`, `suggest_hit_total`, `suggest_miss_total`, `bindings_confirmed_total`, `inspect_invoked_total`, `inspect_render_ms`, `backfill_observations_total`, `backfill_with_refs_total` |
| drift     | `drift_invoked_total`, `drift_still_valid_total`, `drift_label_drift_total`, `drift_stale_location_total`, `drift_stale_id_total`, `drift_obsolete_total`, `drift_contradicted_total`, `drift_unable_to_verify_total` |
| vector    | `vector_search_invoked_total`, `vector_search_results_returned_total`, `vector_search_latency_ms`, `vector_index_size_observations`, `reindex_observations_total`, `reindex_duration_seconds` |
| federated | `federated_search_invoked_total`, `federated_search_projects_queried`, `federated_search_results_returned_total` |
| snapshot  | `snapshot_create_total`, `snapshot_rollback_total`, `snapshot_prune_total`, `snapshot_load_failed_total` |
| metadata  | `update_observation_metadata_*`, `project_tag_*` (representative patterns)                         |

Counter names ending in `_total` map to Prometheus `counter` type; `_ms`
/ `_seconds` map to `summary`; bare names map to `gauge` (D6).

## Versioning

- **v1.0 (2026-06-27)**: initial bootstrap from change #6 observability.
  Carries REQ-35..39 + 11 BDD scenarios verbatim from the change spec.
  Future deltas append to this file rather than forking.