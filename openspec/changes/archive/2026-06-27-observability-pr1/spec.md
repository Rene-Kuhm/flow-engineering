<!-- Spec: observability. Source: manual. -->
# Spec: observability

**Change:** `observability`
**Builds on:** `proposal.md` (Approach A — extend `flow metrics` CLI; 5 read-side helpers in `observability.py` + `DOMAIN_BY_PREFIX` table; bootstrap `openspec/specs/observability/spec.md` capability catalog; 2 chained PRs)
**Date:** 2026-06-27
**Status:** SPECIFIED → ready for sdd-tasks

```yaml
status: success
confidence: high
change: observability
pr_split: 2 chained PRs (PR#1: REQ-35/36/37 + spec bootstrap; PR#2: REQ-38/39)
total_reqs: 5
total_bdd_scenarios: 11
file_created: C:\dev\proyects\flow-engineering\openspec\changes\observability\spec.md
next_recommended: sdd-design observability
```

## Goal

`flow-engineering` ships a **write-side** observability layer — `observability.increment()`, `read_all()`, and 5 record helpers (`record_backfill_coverage`, `record_drift_summary`, `record_vector_summary`, `record_federated_summary`, `record_snapshot_event`) collectively emit 31 counter names across 7 implicit domains into `~/.flow-engineering/metrics.jsonl`. The **`flow metrics`** CLI today is a 13-line flat dump (`<name>  <count>`, alpha-sorted) with `--json` and **no** time-window filter, **no** domain slicing, **no** aggregation, **no** export format, **no** dashboard. Operators cannot answer "what is my snapshot failure rate over the last 24h?" or "how does drift trend this week?" without `grep` + `jq` against a multi-megabyte JSONL. This change ships the **read-side**: a `flow metrics summary` text dashboard, time-window filters, cross-domain slicing, Prometheus textfile export, and percentile aggregation — **all additive, all non-breaking**, all driven by the existing JSONL sink that REQ-8 (`decision-code-linking` v0.2.0) shipped. As a one-time side benefit, change #6 bootstraps `openspec/specs/observability/spec.md` (resolving the `cross-project-federation` archive-report #61 explicit deferral: "Spec counter catalog in `openspec/specs/observability/spec.md` for the 3 new `federated_*` counters — defer to a future observability change").

The read-side surface lives in **`src/flow_engineering/observability.py`** as 5 new pure functions (`read_events_since`, `read_events_by_domain`, `summarize`, `percentile`, `aggregate`) plus 2 new lookup tables (`DOMAIN_BY_PREFIX`, `METRIC_TYPE_OVERRIDES`). The CLI surface lives in **`src/flow_engineering/cli.py:977`** as 9 new flags on the existing `flow metrics` command (`--summary`, `--since`, `--until`, `--window`, `--domain`, `--top`, `--percentile`, `--aggregations`, `--prometheus`, `--format`). The flat text default of `flow metrics` MUST stay byte-identical to v0.6.0 — new functionality is **opt-in via flags** only.

---

## Contract table (per-PR breakdown)

| PR | REQs | LOC forecast (production / test) | BDD scenarios |
|----|------|----------------------------------|--------------|
| **PR#1** — foundation: summary + window + domain + spec bootstrap | REQ-35, REQ-36, REQ-37 | ~750 / ~1 200 (realistic ~4 500 with ×6 TDD multiplier) | 6 |
| **PR#2** — export + aggregation | REQ-38, REQ-39 | ~550 / ~970 (realistic ~3 300 with ×6 TDD multiplier) | 5 |
| **Total** | **5 REQs** | **~1 300 / ~2 170 forecast** (realistic ~7 800 with ×6 TDD multiplier) | **11** |

**Realistic LOC multiplier rationale** — per `decision-code-linking` archive-report #119 S3, the strict-TDD ×6 multiplier maps a ~1 936 LOC forecast to ~10 910 realistic. Per-PR forecast here uses the lower ~1 300 production / ~2 170 test aggregate to reflect the consolidated counter-catalog scope (single `SNAPSHOT_COUNTER_NAMES` family of tests, shared BDD glue). Per-PR work-unit commit splits per `work-unit-commits` skill (5–6 commits each ≤400 LOC).

---

## PR#1 — Foundation: summary view + time window + cross-domain slice + spec catalog bootstrap

### REQ-35: `flow metrics summary [--since=<iso>] [--until=<iso>] [--domain=<d>] [--top=<N>]` — text dashboard

The system SHALL provide a `flow metrics summary` sub-mode on the existing `flow metrics` CLI command that renders a text dashboard to stdout with the following structure (in order, top-to-bottom):

1. **Header block** — three lines: a literal `flow-engineering metrics summary`, a `Generated: <ISO 8601 UTC>` line, and a `Window: <since> → <until>  (<human-readable duration>)` line. When no `--since`/`--until` flags are given, the window is the full range of the JSONL sink (oldest event → newest event); when `--since` is given, the window starts at that ISO timestamp; when `--until` is given, the window ends at that ISO timestamp.
2. **Totals row** — two lines: `Total events: <N>` and `Distinct counters: <N>`. Both counts are computed AFTER applying any active `--since`/`--until`/`--domain` filters.
3. **By-domain breakdown** — one line per domain that has ≥1 counter in the filtered set, sorted by event count descending. Each line is `<domain-name-padded-to-15> <N> counters    <N> events`. Domain names come from the `DOMAIN_BY_PREFIX` lookup table in `observability.py`; unknown counter names (e.g., legacy `snapshot_pruned_total` from W23 carry-forward) fall into an `unknown` bucket.
4. **Top-N counters** — `--top=<N>` limits the output to the N most-fired counters (sorted by event count descending); default `--top=10` when `--summary` is used without `--top`. Each line is `<counter-name-padded> <count>`.
5. **Empty-file behavior** — when the JSONL sink is empty OR the filter set is empty after filtering, the command SHALL print a single line `(no metrics recorded)` and exit `0` (NOT an error). When the filter set is empty due to filtering (i.e., there ARE events but none match the filter), it prints `(no events matched filter)` and exits `0`.

The command SHALL NOT touch any of the 5 record helpers; it is purely read-side.

#### Scenario: Summary over all domains shows per-domain counter totals

```gherkin
Scenario: Summary over all domains shows per-domain counter totals
  Given a metrics.jsonl file with 27 distinct counters across 5 domains
  And 1247 total increment events recorded over the past 24 hours
  When the user runs "flow metrics summary"
  Then stdout contains a "Total events: 1247" line
  And stdout contains a "Distinct counters: 27" line
  And stdout contains a "By domain:" section with one row per domain
  And stdout contains a "Top 10 counters:" section listing the most-fired counters
  And the by-domain rows are sorted by event count descending
  And the command exits 0
```

#### Scenario: Summary with empty metrics file emits "no metrics yet" message

```gherkin
Scenario: Summary with empty metrics file emits "no metrics yet" message
  Given a metrics.jsonl file that does not exist or is empty
  When the user runs "flow metrics summary"
  Then stdout contains the literal text "(no metrics recorded)"
  And the command exits 0
  And no error is raised
  And no other output is printed
```

---

### REQ-36: Time window filter — `flow metrics --since=<iso> [--until=<iso>] [--window=<1h|24h|7d>]`

The system SHALL extend the existing `flow metrics` CLI command with three mutually-cooperating time-window flags. All three flags MAY be combined with `--domain` (REQ-37), `--summary` (REQ-35), `--top` (REQ-35), `--percentile` (REQ-39), `--aggregations` (REQ-39), and `--prometheus` (REQ-38); window-filtered events flow into all downstream filters and formatters.

- **`--since=<iso>`** — Filters events to those whose `ts >= <iso>` (lexicographic ISO-8601 string comparison; the timestamps are already `Z`-suffixed UTC so sort order is also chronological). The ISO string MUST be parseable by `datetime.fromisoformat()` after stripping the `Z`; on parse failure, the command SHALL exit non-zero with exit code 3 and emit `{"error": "invalid --since value", "value": "<provided>", "hint": "use ISO 8601 UTC, e.g., 2026-06-26T00:00:00Z"}` to stderr.
- **`--until=<iso>`** — Filters events to those whose `ts <= <iso>`. Same parse-error contract as `--since` (exit code 3, JSON error to stderr).
- **`--window=<1h|24h|7d>`** — Rolling shorthand for `--since=<now - duration>`. The accepted values are exactly `1h`, `24h`, `7d` (case-insensitive). When `--window` is given alongside `--since`, the LAST one wins (Click's standard behavior; documented in `flow metrics --help`). When `--window` is given alongside `--until`, both apply: window-relative `--since` + explicit `--until` cap.

The flags compose: `--since=<iso> --until=<iso>` filters to the half-open interval `[since, until]`. The flags MUST NOT touch `observability.read_all()`'s I/O path; they filter the already-read list in-memory (mirrors `read_events_since` precedent from the `vector-semantic-search` index refresh helper).

#### Scenario: --since with an absolute ISO 8601 timestamp filters events to that timestamp onward

```gherkin
Scenario: --since with an absolute ISO 8601 timestamp filters events to that timestamp onward
  Given a metrics.jsonl file with 10 events at ts = 2026-06-26T10:00:00Z through 2026-06-26T19:00:00Z (one per hour)
  When the user runs "flow metrics --since=2026-06-26T15:00:00Z"
  Then stdout contains only counters whose events fired at or after 2026-06-26T15:00:00Z
  And the 5 events at 10:00, 11:00, 12:00, 13:00, 14:00 are excluded
  And the 5 events at 15:00, 16:00, 17:00, 18:00, 19:00 are included
  And the command exits 0
```

#### Scenario: --window 1h filters to events from the last 60 minutes

```gherkin
Scenario: --window 1h filters to events from the last 60 minutes
  Given a metrics.jsonl file with 5 events at ts = <now - 2h>, <now - 90m>, <now - 45m>, <now - 30m>, <now - 5m>
  When the user runs "flow metrics --window=1h"
  Then stdout contains only the events at <now - 45m>, <now - 30m>, <now - 5m>
  And the 3 events at <now - 2h>, <now - 90m> are excluded (older than 60 minutes)
  And the command exits 0
```

---

### REQ-37: Cross-domain slice — `flow metrics --domain=<binding|drift|vector|snapshot|federated|backfill|metadata|engine>`

The system SHALL extend the existing `flow metrics` CLI command with a `--domain=<D>` flag that filters events to those whose counter name begins with one of the prefixes registered for domain `D` in the `DOMAIN_BY_PREFIX` lookup table in `observability.py`. The accepted domain values (and their registered prefixes) are:

| Domain | Registered counter prefixes |
|---|---|
| `binding` | `suggest_`, `bindings_`, `inspect_` |
| `backfill` | `backfill_` |
| `drift` | `drift_` |
| `vector` | `vector_`, `reindex_` |
| `federated` | `federated_` |
| `snapshot` | `snapshot_` |
| `metadata` | `update_observation_metadata_`, `project_tag_` |
| `engine` | (reserved for REQ-42; v1 emits no `engine_*` counters) |

When `--domain` is absent, **no domain filtering** is applied — all 7 domains contribute to the output (REQ-35 summary and the flat default both work this way). The `--domain` flag composes with `--since`/`--until`/`--window` (REQ-36), `--summary` (REQ-35), `--top` (REQ-35), `--percentile`/`--aggregations` (REQ-39), and `--prometheus` (REQ-38); all flags AND together.

The `DOMAIN_BY_PREFIX` table MUST cover all 31 catalog counters (after graph-snapshots archive); any counter name that does NOT match a registered prefix falls into the `unknown` bucket and is reported as `unknown` in the by-domain breakdown (REQ-35) but still appears in the flat default output. When an unknown `--domain=<value>` is given that is NOT in the accepted list above, the command SHALL exit non-zero with exit code 2 and emit `{"error": "unknown domain", "value": "<provided>", "valid": [<list of 8 valid domains>]}` to stderr.

#### Scenario: --domain snapshot filters output to snapshot_* counters only

```gherkin
Scenario: --domain snapshot filters output to snapshot_* counters only
  Given a metrics.jsonl file with events across all 5 active domains (binding, drift, vector, snapshot, federated)
  When the user runs "flow metrics --domain=snapshot"
  Then stdout contains ONLY counters whose name starts with "snapshot_"
  And counters like "snapshot_create_total" and "snapshot_rollback_total" appear
  And counters like "drift_invoked_total", "vector_search_invoked_total", "bindings_confirmed_total" do NOT appear
  And the command exits 0
```

#### Scenario: No --domain flag shows all 5 active domains aggregated

```gherkin
Scenario: No --domain flag shows all 5 active domains aggregated
  Given a metrics.jsonl file with events across all 5 active domains (binding, drift, vector, snapshot, federated)
  When the user runs "flow metrics" (no flags)
  Then stdout contains counters from ALL 5 active domains
  And the binding, drift, vector, snapshot, federated counters all appear
  And backfill, metadata counters also appear if they have events
  And the command exits 0
  And the output is byte-identical to the v0.6.0 default output for the same JSONL file
```

---

### PR#1 acceptance criteria

- [ ] All 6 BDD scenarios (REQ-35 ×2, REQ-36 ×2, REQ-37 ×2) pass.
- [ ] `flow metrics` without any new flags is byte-identical to v0.6.0 behavior.
- [ ] `flow metrics --json` without any new flags is byte-identical to v0.6.0 behavior.
- [ ] `openspec/specs/observability/spec.md` exists and catalogs all 31 counters with domain + helper provenance.
- [ ] `DOMAIN_BY_PREFIX` table covers all 31 counters with no orphans (BDD scenario GIVEN a counter THEN its domain is in the table — added to `tests/bdd/test_observability_steps.py` glue).
- [ ] All 801 existing tests pass; `ruff check` clean on changed files.
- [ ] Per-commit work-unit splits per `work-unit-commits` skill (5–6 commits each ≤400 LOC).
- [ ] Strict TDD evidence: every public helper (`read_events_since`, `read_events_by_domain`, `summarize`) has RED→GREEN→REFACTOR history in commit log.

### PR#1 files to touch

**Production (~750 LOC):**
- `src/flow_engineering/observability.py` (MODIFY): +`read_events_since()`, +`read_events_by_domain()`, +`summarize()` helpers; +`DOMAIN_BY_PREFIX` table; ~300 LOC delta
- `src/flow_engineering/cli.py` (MODIFY): `flow metrics` extended with `--summary`, `--since`, `--until`, `--window`, `--domain`, `--top` flags; +refactor `_summarize_metrics` → thin wrapper around `observability.summarize`; ~150 LOC delta
- `openspec/specs/observability/spec.md` (NEW): capability spec — full catalog of 31 counters across 7 domains; ~200 LOC; bootstraps `openspec/specs/` baseline (resolves archive-report #61)
- `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` (MODIFY): observability hook prose; ~100 LOC runtime-only

**Tests (~1 200 LOC):**
- `tests/unit/test_observability.py` (MODIFY): +filter + summarize unit tests; ~150 LOC delta
- `tests/unit/test_cli_metrics.py` (NEW): full CLI surface coverage for `flow metrics summary` + window + domain + top; ~400 LOC
- `tests/unit/test_observability_summary.py` (NEW): unit-level coverage for `summarize()` helper; ~150 LOC
- `tests/bdd/req35_metrics_summary.feature` (NEW): 2 BDD scenarios
- `tests/bdd/req36_metrics_window.feature` (NEW): 2 BDD scenarios
- `tests/bdd/req37_metrics_domain.feature` (NEW): 2 BDD scenarios
- `tests/bdd/test_observability_steps.py` (NEW): pytest-bdd glue shared across 3 PR#1 BDD features; ~150 LOC

---

## PR#2 — Export + aggregation: Prometheus textfile + percentile / aggregation

### REQ-38: `flow metrics --prometheus [--out=<path>]` — Prometheus textfile exporter

The system SHALL extend the existing `flow metrics` CLI command with a `--prometheus` flag that emits the filtered events in **Prometheus textfile exposition format** (the format consumable by the Prometheus `textfile` collector, used by `node_exporter`'s textfile collector pattern). The output format for each counter SHALL be:

```
# HELP <counter_name> <description>
# TYPE <counter_name> <counter|gauge|summary>
<counter_name>{label1="value1",label2="value2"} <number>
```

Type derivation rules (applied in order):
1. If the counter name appears in the `METRIC_TYPE_OVERRIDES` map in `observability.py`, that type is used (escape hatch for ambiguous cases; v1 has zero overrides but the map is the forward-compatible hook for REQ-39 deferred `_latency_ms` / `_duration_seconds` decisions).
2. Otherwise, suffix-based: `_total` → `counter`; `_ms` or `_seconds` → `summary` (single-quantile; bucket math deferred to v1.1); everything else → `gauge`.

Label derivation: for each event matching the counter name, the `fields` dict (excluding `count`, `elapsed_ms`, `value`) is converted to Prometheus labels. Numeric values for the same `(counter_name, label-tuple)` pair are summed across matching events (mirrors the existing `_summarize_metrics` semantics at `cli.py:960`).

**Output destination** — by default, output goes to stdout. When `--out=<path>` is given, output is written to that path (parent directories created if missing) AND stdout emits a one-line confirmation `{"wrote": "<path>", "metric_lines": <N>, "bytes": <N>}` to stderr (NOT stdout, to keep stdout clean for piping). When `--out` is given alongside `--prometheus` and writing fails (permission denied, disk full), the command SHALL exit non-zero with exit code 4 and emit `{"error": "write failed", "path": "<path>", "cause": "<strerror>"}` to stderr.

**Filter composition** — `--prometheus` composes with all PR#1 flags: `--since`/`--until`/`--window` (REQ-36) restrict the event set; `--domain` (REQ-37) restricts by counter prefix; `--top` (REQ-35) limits to N most-fired counters; `--percentile`/`--aggregations` (REQ-39) are orthogonal and MAY be combined with `--prometheus` to additionally emit percentile lines as summary-metric quantiles.

#### Scenario: Export to stdout in Prometheus textfile format with HELP + TYPE + metric lines

```gherkin
Scenario: Export to stdout in Prometheus textfile format with HELP + TYPE + metric lines
  Given a metrics.jsonl file with at least one event for "drift_invoked_total" (count=1, fields={"change": "observability"})
  When the user runs "flow metrics --prometheus"
  Then stdout contains a "# HELP drift_invoked_total" line with a non-empty description
  And stdout contains a "# TYPE drift_invoked_total counter" line (because of the "_total" suffix)
  And stdout contains a metric line "drift_invoked_total{change=\"observability\"} 1"
  And stdout is parseable as Prometheus textfile format (every metric line is preceded by HELP + TYPE)
  And the command exits 0
```

#### Scenario: Export to file at --out path writes the textfile format to disk

```gherkin
Scenario: Export to file at --out path writes the textfile format to disk
  Given a metrics.jsonl file with events for 3 distinct counters
  And a writable temp directory <TMPDIR>
  When the user runs "flow metrics --prometheus --out=<TMPDIR>/metrics.prom"
  Then the file <TMPDIR>/metrics.prom exists and is non-empty
  And the file content matches what stdout would have produced without --out
  And stderr contains a JSON confirmation {"wrote": "<TMPDIR>/metrics.prom", "metric_lines": 3, "bytes": <positive int>}
  And the command exits 0
```

#### Scenario: Export with --window filters exported counters to that window

```gherkin
Scenario: Export with --window filters exported counters to that window
  Given a metrics.jsonl file with 10 events for "drift_invoked_total" at various timestamps (5 within the last 1h, 5 older)
  When the user runs "flow metrics --prometheus --window=1h"
  Then the emitted Prometheus output contains a "drift_invoked_total" metric line with value 5 (the sum of in-window events)
  And the out-of-window events do not contribute to the exported count
  And the command exits 0
```

---

### REQ-39: `flow metrics --percentile=<p50|p95|p99> [--field=<name>] [--aggregations]` — percentile and statistical aggregation

The system SHALL extend the existing `flow metrics` CLI command with two cooperating aggregation flags that compute per-counter statistical summaries over the filtered event set.

- **`--percentile=<p50|p95|p99>`** — For each counter that has ≥2 events with a numeric value in the `--field` (default `elapsed_ms`; alternative is `value`), compute the requested percentile and emit a single line per counter in the format `<counter_name> <percentile_label>: <value>`. The percentile computation uses `statistics.quantiles` (Python stdlib; linear interpolation; CUT-7 method) over the sorted values list. Counters with <2 numeric values are reported as `<counter_name> <percentile_label>: insufficient data` and emit a stderr warning `{"warning": "not enough data points for percentile", "counter": "<name>", "count": <N>}` (does NOT cause non-zero exit). The accepted `--percentile` values are exactly `p50`, `p95`, `p99` (case-insensitive). On invalid value, exit code 3 with `{"error": "invalid --percentile value", "value": "<provided>", "valid": ["p50", "p95", "p99"]}` to stderr.
- **`--aggregations`** — For each counter with ≥1 numeric value in `--field`, emit a single line `<counter_name> {count: N, mean: X, stddev: Y, min: A, max: B}`. This flag is independent of `--percentile` (the percentile lines do NOT replace the aggregations; both MAY be combined). The `stddev` uses `statistics.stdev` (sample standard deviation, n-1 in the denominator); with only 1 data point, stddev is `0.0` (NOT an error).
- **`--field=<name>`** — Modifies both `--percentile` and `--aggregations` to operate on a different event field. Default `elapsed_ms` (matches the latency convention from `vector_search_latency_ms` events emitted by `record_vector_summary`). Acceptable values: `elapsed_ms`, `value`, `count`, or any key present in the event's `fields` dict.

The flags compose with all PR#1 flags (`--since`/`--until`/`--window`, `--domain`, `--summary`, `--top`) and `--prometheus` (REQ-38). Composition with `--prometheus`: the percentile lines are emitted as Prometheus `summary` metric type with a `quantile="0.95"` label (for p95), and the aggregations are emitted as additional `<counter_name>_count`, `<counter_name>_sum`, `<counter_name>_min`, `<counter_name>_max` series (mirrors the Prometheus summary-metric convention).

#### Scenario: --percentile p95 computes p95 across counter increments in window

```gherkin
Scenario: --percentile p95 computes p95 across counter increments in window
  Given a metrics.jsonl file with 100 events for "vector_search_latency_ms"
  And the elapsed_ms values are uniformly distributed from 10ms to 1000ms (i.e., 10, 20, 30, ..., 1000)
  When the user runs "flow metrics --percentile=p95 --domain=vector"
  Then stdout contains a line "vector_search_latency_ms p95: 950.5" (the linear-interpolated 95th percentile of 10..1000)
  And the command exits 0
```

#### Scenario: --percentile with insufficient data emits "not enough data points" warning

```gherkin
Scenario: --percentile with insufficient data emits "not enough data points" warning
  Given a metrics.jsonl file with exactly 1 event for "drift_scan_duration_ms" (elapsed_ms=42)
  When the user runs "flow metrics --percentile=p95 --domain=drift"
  Then stdout contains the line "drift_scan_duration_ms p95: insufficient data"
  And stderr contains a JSON warning {"warning": "not enough data points for percentile", "counter": "drift_scan_duration_ms", "count": 1}
  And the command STILL exits 0 (warning, not error)
  And no traceback is printed
```

---

### PR#2 acceptance criteria

- [ ] All 5 BDD scenarios (REQ-38 ×3, REQ-39 ×2) pass.
- [ ] `flow metrics --prometheus` output is parseable by the official `prometheus_client.parser.text_string_to_metric_families` (unit-tested via a round-trip in `tests/unit/test_observability_prometheus.py`).
- [ ] `flow metrics --percentile=p95 --domain=vector` against the synthetic 10..1000 dataset returns `950.5` (±0.5 tolerance for interpolation method variance; documented in the unit test).
- [ ] `flow metrics` and `flow metrics --json` without new flags remain byte-identical to v0.6.0 (regression test stays green).
- [ ] `--out=<path>` writes to disk atomically (`tempfile + Path.replace`); partial writes do NOT leave corrupt files.
- [ ] `--percentile=garbage` exits with code 3 + helpful error (defensive parser).
- [ ] `--domain=garbage` exits with code 2 + helpful error (defensive parser; same shape as REQ-37).
- [ ] All PR#1 tests + 801 existing tests pass; `ruff check` clean on changed files.
- [ ] Per-commit work-unit splits per `work-unit-commits` skill (5–6 commits each ≤400 LOC).

### PR#2 files to touch

**Production (~550 LOC):**
- `src/flow_engineering/observability.py` (MODIFY): +`prometheus_exposition()`, +`aggregate()` (mean/stddev/min/max), +`percentile()` helpers; +`METRIC_TYPE_OVERRIDES` map; ~200 LOC delta
- `src/flow_engineering/cli.py` (MODIFY): +`--prometheus`, +`--out`, +`--percentile`, +`--aggregations`, +`--field`, +`--format` flags; ~150 LOC delta
- `CHANGELOG.md` (MODIFY): v0.7.0 entry post-PR#2-merge (~50 LOC)
- `pyproject.toml` (MODIFY): version bump to 0.7.0 (~5 LOC)

**Tests (~970 LOC):**
- `tests/unit/test_observability_prometheus.py` (NEW): textfile format round-trip via `prometheus_client.parser`; ~250 LOC
- `tests/unit/test_observability_aggregate.py` (NEW): percentile correctness + gauge aggregation; ~250 LOC
- `tests/bdd/req38_metrics_prometheus.feature` (NEW): 3 BDD scenarios
- `tests/bdd/req39_metrics_percentile.feature` (NEW): 2 BDD scenarios
- `tests/bdd/test_observability_steps.py` (MODIFY): +2 new step groups (Prometheus + percentile); ~120 LOC delta

---

## Out of Scope (deferred)

The following are explicitly out of scope for change #6 and belong to named follow-ups (mirrors the `vector-semantic-search` and `cross-project-federation` deferral patterns):

- **REQ-40 — Label-based query** (`--label key=value` for arbitrary event-field filtering beyond `--domain`) — defer to v1.1.
- **REQ-41 — Threshold alerting** (`--threshold name:op:N` to emit non-zero exit codes for CI/CD integration) — defer to v1.1.
- **REQ-42 — `engine_*` counters** (CLI startup time, embedding provider latency, daemon queue depth) — defer to a dedicated `engine-instrumentation` change. The `engine` domain slot in `DOMAIN_BY_PREFIX` is RESERVED but the v1 table is empty for it.
- **REQ-43 — Federation-aware events** (`--project=<key>` filter that requires modifying every record helper signature to inject a `project` field into events) — defer to a `federated-observability` follow-up change.
- **REQ-44 — JSONL rotation** (`FLOW_METRICS_MAX_BYTES`, `FLOW_METRICS_MAX_AGE_DAYS` to gzip-and-rotate the sink file) — defer to v1.1 (cross-cuts `read_all()` and 6 existing call sites; too invasive for v1).
- **Snapshot export/import** for sharing (`flow snapshot export <id>` / `flow snapshot import <id>`) — already deferred in `graph-snapshots` archive.
- **Async embed-on-save** (auto-vectorize on `mem_save`) — already deferred in `vector-semantic-search` archive.
- **Per-snapshot percentile** (`flow snapshot show <id> --percentile=p95` to compute latency percentiles over the snapshot window) — v1 percentiles are over the LIVE JSONL sink only; per-snapshot percentiles are v2.
- **Histogram metric type in Prometheus exporter** (bucket-based counts for `_latency_ms` / `_duration_seconds`) — v1 emits `summary` type (single quantile); `histogram` type deferred until someone needs bucket math.
- **Real-time tail mode** (`flow metrics --tail` to follow the JSONL sink like `tail -f`) — deferred to v2; the sink is append-only and a tail would be straightforward but is not on the v1 critical path.
- **Graphviz / DOT export of counter relationships** (e.g., `vector_search_invoked_total → vector_index_size_observations`) — deferred to v2; the dependency graph is implicit in the prefix table but not formalized.
- **Webhook / Slack alerting on threshold breach** (CI integration; companion to REQ-41) — deferred to v1.1 along with REQ-41.
- **Multi-process metric aggregation** (when `flow` is invoked in parallel via a daemon or shell pipeline) — deferred; v1 assumes single-process CLI invocations.
- **OTLP / OpenTelemetry exporter** (vs. Prometheus textfile format) — deferred; Prometheus textfile is the simplest offline-first choice and OTLP would require a runtime dep.
- **CSV export** (`flow metrics --format=csv`) — deferred to v2; the 5 active formats (text, json, json-detailed, prometheus, summary) cover the v1 use cases.

---

## BDD Feature File Plan

| Feature file | Status | Covers | Scenarios |
|---|---|---|---|
| `tests/bdd/req35_metrics_summary.feature` | NEW | REQ-35 | 2 |
| `tests/bdd/req36_metrics_window.feature` | NEW | REQ-36 | 2 |
| `tests/bdd/req37_metrics_domain.feature` | NEW | REQ-37 | 2 |
| `tests/bdd/req38_metrics_prometheus.feature` | NEW | REQ-38 | 3 |
| `tests/bdd/req39_metrics_percentile.feature` | NEW | REQ-39 | 2 |
| **Total BDD scenarios** | | | **11** |

Step definitions land in `tests/bdd/test_observability_steps.py` (NEW; pytest-bdd glue per file). The per-REQ scenario counts match the task brief verbatim (REQ-35: 2, REQ-36: 2, REQ-37: 2, REQ-38: 3, REQ-39: 2 — totaling 11). Edge cases that do NOT fit the BDD scope are covered by unit tests:
- REQ-35: empty JSONL + missing `--top` flag default — `tests/unit/test_observability_summary.py`
- REQ-36: `--since=garbage` exits with code 3 — `tests/unit/test_cli_metrics.py::TestWindowParser`
- REQ-37: `--domain=garbage` exits with code 2 — `tests/unit/test_cli_metrics.py::TestDomainFilter`
- REQ-38: `--out` to non-writable path exits with code 4 — `tests/unit/test_observability_prometheus.py::TestOutFlagErrors`
- REQ-39: `--percentile=garbage` exits with code 3 — `tests/unit/test_observability_aggregate.py::TestPercentileParser`

This mirrors the `graph-snapshots` split where the sha256-tamper detection (REQ-30 edge case) and `--keep-last=0` two-flag safety gate (REQ-34) stayed at the unit-test layer.

---

## Traceability matrix

| REQ | Source | Notes |
|-----|--------|-------|
| REQ-35 | proposal #194 §"New Capabilities" + explore #183 §"Gap 1 (P0) summary dashboard" | `flow metrics summary [--since] [--until] [--domain] [--top]` — text dashboard with totals + per-domain breakdown + top-N; powers all 31 counter names |
| REQ-36 | proposal #194 §"Approach A piece 1" + explore #183 §"Gap 2 (P0) time-window filter" | `--since` / `--until` (ISO 8601) + `--window` (rolling 1h/24h/7d); composes with REQ-35/37/38/39 |
| REQ-37 | proposal #194 §"Approach A piece 1" + explore #183 §"Gap 3 (1) cross-domain slice" | `--domain=<binding|drift|vector|snapshot|federated|backfill|metadata|engine>`; prefix-based via `DOMAIN_BY_PREFIX` table |
| REQ-38 | proposal #194 §"Approach A piece 4" + explore #183 §"Gap 4 (P1) Prometheus export" | `--prometheus` textfile format with HELP + TYPE + metric lines; `--out=<path>` atomic write; composes with REQ-36 window + REQ-37 domain |
| REQ-39 | proposal #194 §"Approach A piece 3" + explore #183 §"Gap 5 (P1) percentile aggregation" | `--percentile=<p50\|p95\|p99>` (statistics.quantiles) + `--aggregations` (mean/stddev/min/max) + `--field=<name>` (default elapsed_ms); composes with REQ-38 as Prometheus `summary` type |

---

## Open Questions (carry-forward to sdd-design)

The 10 questions below MUST be resolved in the design phase before `sdd-tasks` locks the implementation contract:

1. **Default output stability** — does `flow metrics` default stay flat (`<name>  <count>`) or change to summary view? (Recommend: flat default for backwards compat; `--summary` opt-in. Mirrors REQ-8 close.) Confirm `TestMetricsCommand` 3 tests cover text/JSON/empty — all stay green with flat default.
2. **Prometheus type derivation for latency** — should `_latency_ms` / `_duration_seconds` emit as Prometheus `summary` (single quantile, v1) or `histogram` (bucket math, v1.1)? Recommend `summary` for v1.
3. **Domain categorization strategy** — prefix-based (`DOMAIN_BY_PREFIX`) or explicit `domain` field on events? Recommend prefix-based (no helper signature changes). Explicit field deferred to a `structured-events` follow-up.
4. **Percentile computation timing** — at increment time (sliding t-digest / HDR sketch) or query time (full sort + bisect)? Recommend query-time (O(N log N) per query; ~1000 events sorts in <1ms; no in-memory state). Sliding sketches deferred to v1.1.
5. **`--window` vs `--since` semantics** — confirm `1h` means "last 60 minutes" (rolling) NOT "since the top of the hour" (calendar). Recommend rolling; documented in `flow metrics --help`.
6. **`--top` sort key** — top-N by event count (default), by `first_seen` recency, or by `last_seen` recency? Recommend `count` (the use case is "what counters fire most"); `--top-by=count|first_seen|last_seen` opt-in for other orders.
7. **`--json` backward compatibility** — keep flat `{name: count}` or change to richer `[{name, count, domain, first_seen, last_seen}, ...]`? Recommend keep flat; explicit `--format=json-detailed` for richer shape. Confirm external consumers (Engram #140 vector-semantic-search proposal references `flow metrics --json`).
8. **Dashboard format choice** — text-only (like `flow drift`) vs `rich` library vs interactive TUI? Recommend text-only (zero new deps; consistent with `flow drift` / `flow status` / `flow snapshot list` precedent). Verify `rich` is NOT already a dependency in `pyproject.toml`.
9. **REQ-42 scope** — confirm `engine_*` counters in v1.1 are limited to CLI startup time + embedding provider latency (NOT daemon queue depth, which is `engine-instrumentation` change scope).
10. **`openspec/specs/` bootstrap policy** — change #6 creates the project's first capability spec at `openspec/specs/observability/spec.md`. Confirm kebab-case folder per capability baseline (e.g., `openspec/specs/vector-semantic-search/spec.md` for the v0.4.0 spec retro-fill) is the long-term convention (NOT co-located with changes).

---

## Risks (carry-forward from proposal §6)

The 12 risks below were raised in the proposal. Those that remain unmitigated after the spec phase are flagged here; mitigations are noted inline:

| # | Risk | Likelihood | Status after spec phase |
|---|---|---|---|
| 1 | `graph-snapshots` (change #5) does not land before change #6 apply starts → 4 `snapshot_*` counters unstable in `SNAPSHOT_COUNTER_NAMES` catalog | HIGH | UNMITIGATED — orchestrator must coordinate: change #5 ARCHIVE before change #6 APPLY. PR#1 SPEC references the catalog by name only and is resilient to additions (catalog is a `list[str]`, not a closed enum). |
| 2 | PR#1 cumulative realistic ~4 500 LOC > 400-line review budget; reviewers lose context | MED | MITIGATED by per-commit work-unit splits per `work-unit-commits` skill (5–6 commits each ≤400 LOC). |
| 3 | JSONL rotation (REQ-44) cross-cuts `read_all()` — risk of regression in 6 existing call sites | MED | MITIGATED — REQ-44 explicitly deferred to v1.1; v1 ships only read-side. |
| 4 | Federation-aware events (REQ-43) requires changing every record helper signature — invasive | MED | MITIGATED — REQ-43 deferred to `federated-observability` follow-up; events stay project-less for v1. |
| 5 | `openspec/specs/observability/spec.md` is precedent-setting — project has NO `openspec/specs/` baseline today | LOW | MITIGATED — `glob openspec/specs/**` empty; archive-report #61 explicitly defers to this change. Open question #10 confirms the baseline pattern is the long-term convention. |
| 6 | Prometheus type derivation ambiguous for `vector_index_size_observations` (gauge by suffix but used like a counter) | LOW | MITIGATED — `METRIC_TYPE_OVERRIDES` map is the escape hatch; v1 has zero overrides (default suffix rule suffices). |
| 7 | `--since`/`--until` parsing must mirror `flow drift --since` (REQ-10/11); typo or drift breaks window filter | LOW | MITIGATED — reuse `_parse_since()` from `cli.py`; BDD scenario `flow metrics --since=garbage` exits with code 3 + JSON error. |
| 8 | W23 carry-forward: `snapshot_pruned_total` + `snapshot_prune_total` dual-name history may confuse `summarize()` | LOW | MITIGATED — `summarize()` ignores unknown counter names (graceful); adds `unknown` bucket to by-domain breakdown; does NOT warn. |
| 9 | BDD step def file growth: `decision-code-linking` S3 forecast 30 LOC → actual 621 LOC (×21 multiplier) | LOW | MITIGATED — forecast absorbs the multiplier (`test_observability_steps.py` ~200 LOC for 3 PR#1 features + ~120 LOC delta for 2 PR#2 features = ~320 LOC total; per-REQ step files if size exceeds 400 LOC). |
| 10 | `flow metrics --json` flat-dict contract consumed by external scripts; breaking it silently breaks downstream | LOW | MITIGATED — keep `--json` flat dict; add explicit `--format=json-detailed` for raw events; documented in `flow metrics --help`. |
| 11 | `cli.py` `flow metrics` surface grows ~10× (13 → ~150 LOC); reviewer fatigue | MED | MITIGATED — per-commit work-unit splits; CLI surface documented inline with type annotations; Click auto-generates `--help`. |
| 12 | Strict-TDD ×6 LOC multiplier means realistic ~10 910 LOC vs 1 936 forecast → 2 chained PRs are MANDATORY | INFO | ACCEPTED — reflected in PR split; per-PR scope well-defined. |

---

## Cross-impact

| Queued / shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `observability.increment()`, `read_all()`, `record_backfill_coverage()` reused as the foundation; 8 binding/backfill/inspect counters stable | Compatible (consumes the seam) |
| `decision-reality-drift` (shipped v0.3.0) | `record_drift_summary()` emits the 8 drift counters that REQ-35/REQ-37 surface; `_parse_since()` from `cli.py` reused for `--since` parsing | Compatible (consumes the seam) |
| `vector-semantic-search` (shipped v0.4.0) | `record_vector_summary()` emits the 6 vector counters + `vector_search_latency_ms` events that REQ-39 percentiles aggregate over | Compatible (consumes the seam) |
| `cross-project-federation` (shipped v0.5.0) | `record_federated_summary()` emits the 3 federated counters; archive-report #61 explicitly defers the spec catalog to this change | Compatible (resolves #61) |
| `graph-snapshots` (change #5, ARCHIVED) | `record_snapshot_event()` emits the 4 snapshot counters in batch C T1.7; `SNAPSHOT_COUNTER_NAMES` catalog referenced by the new `openspec/specs/observability/spec.md` | Compatible (consumes the seam; spec absorbs the catalog) |
| `prompt-registry` (#7, future) | Unrelated layer | No conflict |

**Unblocks**: text dashboard for the 31 counters already shipped (REQ-35); Prometheus integration for local CI/CD + Grafana (REQ-38); percentile-based latency SLO tracking (REQ-39); and — as a one-time bootstrap — the project's `openspec/specs/` baseline that all subsequent changes will extend.

**Constrains**: any future change that adds a counter name MUST either add it to `DOMAIN_BY_PREFIX` or update the prefix rule. The flat text default of `flow metrics` MUST stay byte-identical to v0.6.0 for backwards compatibility with existing scripts and tests (REQ-8 close contract).

---

## References

- Explore: `openspec/changes/observability/explore.md` (Engram `sdd/observability/explore` #183 — full option matrix A-J, 10 user-facing gaps evaluated, 5 P0/P1 gaps recommended, 5 P2 gaps deferred)
- Proposal: `openspec/changes/observability/proposal.md` (Engram `sdd/observability/proposal` #194 — Approach A recommended, 5 cooperating pieces, 10 open questions for design, 12 risks, 2-chained-PR strategy)
- Predecessor specs (format reference):
  - `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` (change #5, single-PR precedent; per-REQ format + scenario structure + Reconciliation note + Out of Scope + BDD Feature File Plan table)
  - `openspec/changes/archive/2026-06-26-cross-project-federation/spec.md` (change #4, chained-PR precedent)
  - `openspec/changes/archive/2026-06-26-vector-semantic-search/spec.md` (change #3, observability-adjacent counter catalog pattern; `VECTOR_COUNTER_NAMES` precedent)
- Counter catalog sources:
  - `BINDING_COUNTER_NAMES` + backfill + inspect — `observability.py:70` (REQ-8 close, change #1)
  - `DRIFT_COUNTER_NAMES` (8 names) — `observability.py:104` (REQ-12, change #2)
  - `VECTOR_COUNTER_NAMES` (6 names) — `observability.py:85` (REQ-22, change #3)
  - `FEDERATED_COUNTER_NAMES` (3 names) — `observability.py:104` (REQ-26 federated, change #4)
  - `SNAPSHOT_COUNTER_NAMES` (4 names, tuple) — `observability.py:124` (REQ-28..34, change #5 archived)
- Carry-forwards:
  - `vector-semantic-search` archive-report #154 (line 87) — "Beyond REQ-8 dashboards — change #6 owns" — resolved by REQ-35
  - `cross-project-federation` archive-report #61 — `openspec/specs/observability/spec.md` catalog — resolved by PR#1 spec bootstrap
  - `graph-snapshots` tasks "Open follow-ups" #1 — `SNAPSHOT_COUNTER_NAMES` catalog inclusion — resolved by REQ-35/REQ-37
- Precedents:
  - `decision-code-linking` archive-report #119 S3 — BDD step def file 5–6× growth multiplier — absorbed into the ×6 forecast
  - `flow drift --since` (`cli.py:_parse_since()`) — ISO 8601 parsing precedent reused for REQ-36
  - `flow projects backfill --confirm` (REQ-24) — confirmation-gate precedent (NOT used in change #6; flagged for future `--out` write patterns)
- Engram DB state (2026-06-27): 172 observations across 10 projects — JSONL sink size at the time of change #6 proposal: ~150 KB across 31 counter names

---

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_module",
      "label": "observability.py (475→~700 LOC after change #6; 5 read-side helpers + 2 lookup tables)",
      "file": "src/flow_engineering/observability.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_read_all",
      "label": "read_all(path) — REUSED (no signature change); new helpers compose on top",
      "file": "src/flow_engineering/observability.py",
      "line": 200,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_vector_counter_names",
      "label": "VECTOR_COUNTER_NAMES catalog (REQ-22, 6 names) — referenced by openspec/specs/observability/spec.md",
      "file": "src/flow_engineering/observability.py",
      "line": 85,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_federated_counter_names",
      "label": "FEDERATED_COUNTER_NAMES catalog (REQ-26, 3 names) — referenced by openspec/specs/observability/spec.md",
      "file": "src/flow_engineering/observability.py",
      "line": 104,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_snapshot_counter_names",
      "label": "SNAPSHOT_COUNTER_NAMES catalog (REQ-26 T1.7, 4 names) — referenced by openspec/specs/observability/spec.md",
      "file": "src/flow_engineering/observability.py",
      "line": 124,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_metrics_command",
      "label": "flow metrics subcommand (cli.py:977-992, 13 LOC) — extended with 10 new flags in change #6",
      "file": "src/flow_engineering/cli.py",
      "line": 977,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_summarize_metrics",
      "label": "_summarize_metrics() helper (cli.py:960-974) — REFACTOR target: move to observability.summarize(); keep thin wrapper",
      "file": "src/flow_engineering/cli.py",
      "line": 960,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_specs_observability_spec",
      "label": "openspec/specs/observability/spec.md (NEW — bootstraps openspec/specs/ baseline; resolves cross-project-federation archive-report #61)",
      "file": "openspec/specs/observability/spec.md",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req35_metrics_summary",
      "label": "tests/bdd/req35_metrics_summary.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req35_metrics_summary.feature",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req36_metrics_window",
      "label": "tests/bdd/req36_metrics_window.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req36_metrics_window.feature",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req37_metrics_domain",
      "label": "tests/bdd/req37_metrics_domain.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req37_metrics_domain.feature",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req38_metrics_prometheus",
      "label": "tests/bdd/req38_metrics_prometheus.feature (NEW — 3 BDD scenarios)",
      "file": "tests/bdd/req38_metrics_prometheus.feature",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req39_metrics_percentile",
      "label": "tests/bdd/req39_metrics_percentile.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req39_metrics_percentile.feature",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_observability_steps",
      "label": "tests/bdd/test_observability_steps.py (NEW — pytest-bdd glue shared across 5 BDD features)",
      "file": "tests/bdd/test_observability_steps.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_cli_metrics",
      "label": "tests/unit/test_cli_metrics.py (NEW — full CLI surface coverage for flow metrics)",
      "file": "tests/unit/test_cli_metrics.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_observability_prometheus",
      "label": "tests/unit/test_observability_prometheus.py (NEW — textfile format round-trip via prometheus_client.parser)",
      "file": "tests/unit/test_observability_prometheus.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_observability_aggregate",
      "label": "tests/unit/test_observability_aggregate.py (NEW — percentile correctness + gauge aggregation)",
      "file": "tests/unit/test_observability_aggregate.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    }
  ]
}
