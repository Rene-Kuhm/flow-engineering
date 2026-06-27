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

### REQ-38 — Prometheus textfile export (`--prometheus` / `--out`)

The system SHALL extend `flow metrics` with `--prometheus` and
`--out=<path>` flags. The Prometheus textfile exposition emits one metric
line per `(counter_name, label-tuple)` combination with the type
derivation rule: `_total` → `counter`; `_ms` / `_seconds` → `summary`;
bare → `gauge`. Override map: `METRIC_TYPE_OVERRIDES`.

`--out=<path>` writes atomically (`tempfile.NamedTemporaryFile` +
`os.replace`) per design D10. Write failures exit `4`.

### REQ-39 — Percentile + aggregations (`--percentile` / `--aggregations`)

The system SHALL extend `flow metrics` with `--percentile=<p50|p95|p99>`,
`--aggregations`, and `--field=<name>` flags. Percentile uses
`statistics.quantiles` (or equivalent sorted-index lookup) per design D7.

Counters with <2 numeric samples emit `insufficient data` on stdout and
a stderr JSON warning (`{warning, counter, count}`) — the command STILL
exits `0`. Invalid `--percentile` value exits `3`.

## BDD scenarios

The 11 BDD scenarios from `openspec/changes/observability/spec.md` carry
verbatim into this baseline:

- `tests/bdd/req35_metrics_summary.feature` — 2 scenarios (summary
  per-domain, empty sink).
- `tests/bdd/req36_metrics_window.feature` — 2 scenarios (`--since`
  absolute, `--window=1h` rolling).
- `tests/bdd/req37_metrics_domain.feature` — 2 scenarios
  (`--domain=snapshot` filter, no `--domain` = all).
- `tests/bdd/req38_metrics_prometheus.feature` — 3 scenarios
  (stdout exposition, `--out` atomic write, `--window` composition).
- `tests/bdd/req39_metrics_percentile.feature` — 2 scenarios
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