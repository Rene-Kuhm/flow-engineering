<!-- proposal.md: change #6 observability. Source: manual. -->
# Proposal: observability

```yaml
status: success
confidence: high
open_questions_count: 10
chained_pr_recommendation: yes
wall_time_estimate: ~3-4h end-to-end (2 chained PRs)
forecast_loc: 626 production + 1170 tests = 1936 grand-total
pr_split: 2 chained PRs (PR#1 foundation+summary+slice+window; PR#2 export+aggregation)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\observability\proposal.md
next_recommended: sdd-spec observability
```

## Intent

`flow-engineering` has been quietly building a **write-side** observability
layer for five consecutive changes: change #1 (`REQ-8`) added the JSONL counter
sink at `~/.flow-engineering/metrics.jsonl` with 8 binding/backfill/inspect
counters; change #2 (`REQ-12`) added 8 drift counters; change #3 (`REQ-22`)
added 6 vector counters; change #4 (`REQ-26`) added 3 federated counters;
change #5 (`REQ-28..34`, IN PROGRESS) lands 4 snapshot counters in batch C.
Today there are **27 distinct counter names** (31 after graph-snapshots)
across 4-5 implicit domains, but the `flow metrics` CLI is a 13-line
flat-table dump with `--json` and **no** time-window, no domain slicing,
no aggregation, no export format, no dashboard. Operators cannot answer
"what's my snapshot failure rate over the last 24h" or "how does drift
trend across this week" without `grep` + `jq` against a multi-megabyte
JSONL. This change ships the **read-side**: a `flow metrics summary`
dashboard, time-window filters, cross-domain slicing, Prometheus
textfile export, and percentile aggregation — all additive, all
non-breaking, all driven by the existing JSONL sink that change #1
shipped. As a one-time side benefit, change #6 bootstraps
`openspec/specs/observability/spec.md` (resolving the cross-project-federation
archive-report #61 explicit deferral: "Spec counter catalog in
`openspec/specs/observability/spec.md` for the 3 new `federated_*` counters
— defer to a future observability change"). This is that change.

## Context (from explore)

Explored in [`explore.md`](./explore.md) and Engram #183. Ten user-facing
gaps evaluated; **5 P0/P1** gaps recommended for change #6, 5 P2 gaps
deferred to v1.1. The exploration confirmed: the JSONL sink is
**already** best-effort, append-only, monotonic, and FTS-free — perfect
for aggregation because every line is a self-describing event. The
**only** missing pieces are the read-side aggregation, slicing, and
export — none of which require any schema migration, any new runtime
dependency, or any modification to the 5 record helpers
(`record_backfill_coverage`, `record_drift_summary`,
`record_vector_summary`, `record_federated_summary`,
`record_snapshot_event`). The strict-TDD ×6 LOC multiplier (established
in `decision-code-linking` archive-report #119 S3) forecasts the work
at ~1 936 LOC forecast → ~10 910 realistic, comfortably justifying a
**2 chained PRs** split (mirrors `vector-semantic-search` pattern).

### Carry-forwards resolved by this change

| Source | Item | Resolution |
|---|---|---|
| `vector-semantic-search` archive-report #154 (line 87) | "Beyond REQ-8 dashboards — change #6 owns" | Resolved — REQ-35 summary view |
| `cross-project-federation` archive-report #61 | "Spec counter catalog in `openspec/specs/observability/spec.md` for the 3 new `federated_*` counters — defer to a future observability change" | Resolved — `openspec/specs/observability/spec.md` created in PR#1 |
| `graph-snapshots` tasks "Open follow-ups" #1 | "Spec counter catalog in `openspec/specs/observability/spec.md` for the 4 new `snapshot_*` counters (REQ-22/26 pattern)" | Resolved — `SNAPSHOT_COUNTER_NAMES` catalog included in the new spec |
| `decision-code-linking` archive-report #119 S3 | BDD step def file 5-6× growth precedent | Forecast absorbs the multiplier (`tests/bdd/test_observability_steps.py` ~200 LOC) |

## Approach (proposed)

### Approach matrix

| Approach | LOC forecast | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — Extend `flow metrics` CLI** (5 new flags + `summary` sub-mode) | ~1 936 | Lowest risk (additive); best discoverability (users already know `flow metrics`); preserves offline-first principle; zero new runtime deps | 5 new flags need careful conflict avoidance | **RECOMMENDED** |
| B — Separate `flow observe` top-level command | ~2 200 | Cleaner API surface | Discoverability cost (two ways to access metrics); extra maintenance; breaks the "extend what users already know" mental model | Rejected |
| C — Third-party integration only (Prometheus pushgateway + Grafana) | ~200 | Industry-standard tooling | Requires external infra; doesn't help local operators who run the CLI; violates offline-first | Rejected |

**Recommendation: Approach A.** Lowest risk (all additive), best
discoverability (extends the existing `flow metrics` command users
already know), preserves the project's offline-first principle (no new
runtime dependencies; the Prometheus textfile format is just a string
serialization we emit to stdout), and unifies the 5 future REQs
(REQ-40..44) into a single mental model.

### Architecture (Approach A)

Five cooperating pieces, all additive on top of the existing JSONL
sink that change #1 shipped:

1. **`read_events_*` filter helpers** (NEW in `observability.py`) —
   `read_events_since(path, since_iso, until_iso=None)`,
   `read_events_by_domain(path, domain)`,
   `read_events_by_label(path, **labels)`. All return `list[dict]`,
   reuse the existing `read_all()` for I/O, apply filters in-memory.
   No schema migration; pure read-side.
2. **`summarize()` aggregation helper** (NEW) — `summarize(events)`
   collapses events into `{name: count, "domain": <prefix>,
   "last_seen": <iso>, "first_seen": <iso>, ...}` per counter.
   Powers REQ-35 (text dashboard) and REQ-37 (`--domain` filter).
3. **`percentile()` aggregation helper** (NEW) — `percentile(events,
   pct)` computes P50/P95/P99 over `elapsed_ms` / `value` fields.
   Pure-Python, no numpy, O(N log N) per query. Powers REQ-39.
4. **`prometheus_exposition()` formatter** (NEW) — `prometheus_exposition(events)`
   emits the Prometheus textfile exposition format
   (`# HELP <name> <description>` / `# TYPE <name> counter|gauge`
   / `<name>{label="value"} <number>`). Powers REQ-38.
5. **CLI surface** — extend the existing `flow metrics` command at
   `cli.py:977` with 5 new flags (`--summary`, `--since`, `--until`,
   `--domain`, `--top`, `--percentile`, `--prometheus`,
   `--aggregations`, `--format`). The flat text default stays
   byte-identical to today (non-breaking); `--summary` is opt-in.

### CLI surface (proposed)

```bash
# Today (unchanged — REQ-8 close behavior):
flow metrics             # flat text: <name>  <count>  (alpha-sorted)
flow metrics --json      # JSON flat dict {name: count}

# New in change #6:
flow metrics summary
  [--since=<iso>] [--until=<iso>]
  [--domain=<binding|drift|vector|snapshot|federated|backfill|metadata|engine>]
  [--top=<N>]                      # REQ-35 — text dashboard

flow metrics
  [--since=<iso>] [--until=<iso>]  # REQ-36 — time window filter
  [--domain=<d>]                   # REQ-37 — cross-domain slice
  [--top=<N>]                      # limit to top-N by activity

flow metrics
  [--percentile=<p50|p95|p99>]     # REQ-39 — latency percentile
  [--aggregations]                 # REQ-39 — mean/stddev/min/max
  [--prometheus]                   # REQ-38 — textfile exporter
  [--format=<text|json|json-detailed|prometheus>]
                                   # explicit format override
```

### Proposed output examples

**`flow metrics summary`** (REQ-35):

```
flow-engineering metrics summary
Generated: 2026-06-27T15:42:11Z
Window:    2026-06-26T15:42:11Z → 2026-06-27T15:42:11Z  (24h)
─────────────────────────────────────────────────────────
Total events:    1 247
Distinct counters: 27

By domain:
  binding         4 counters    312 events
  drift           8 counters    198 events
  vector          6 counters    421 events
  federated       3 counters     94 events
  snapshot        4 counters     87 events
  backfill        2 counters     24 events
  metadata        2 counters     12 events

Top 5 counters:
  vector_search_invoked_total                   421
  drift_invoked_total                           198
  bindings_confirmed_total                      156
  snapshot_create_total                          63
  federated_search_invoked_total                 94
```

**`flow metrics --prometheus`** (REQ-38):

```
# HELP vector_search_invoked_total Number of vector search invocations
# TYPE vector_search_invoked_total counter
vector_search_invoked_total{trigger="cli"} 312
vector_search_invoked_total{trigger="programmatic"} 109
# HELP drift_invoked_total Number of drift scan invocations
# TYPE drift_invoked_total counter
drift_invoked_total{change="observability"} 1
```

### Dependencies

- **NO new runtime dependencies.** stdlib `json` + `pathlib` + `statistics`
  + `datetime` + `bisect` cover everything (percentile is O(N log N) sort +
  bisect; no numpy).
- Reuses `observability.read_all()` for I/O.
- Reuses `_summarize_metrics()` from `cli.py:960` (REFACTOR target: move
  into `observability.py` as `summarize()`; keep the cli.py helper as
  a thin wrapper for backwards compatibility).
- Reuses `SNAPSHOT_COUNTER_NAMES` from `observability.py:124` (graph-snapshots
  T1.7) — change #6 spec absorbs it into the new capability catalog.

### What changes (scope)

**In scope (PR#1)**:
- `src/flow_engineering/observability.py` (MODIFY): `read_events_since()`,
  `read_events_by_domain()`, `summarize()` helpers; `DOMAIN_BY_PREFIX`
  lookup table; `percentile()` helper.
- `src/flow_engineering/cli.py` (MODIFY): `flow metrics` extended with
  `--summary`, `--since`, `--until`, `--domain`, `--top` flags.
- `openspec/specs/observability/spec.md` (NEW): capability spec
  cataloging ALL counter names (vector + federated + drift + snapshot
  + binding + backfill + metadata + engine) — one-time bootstrap;
  resolves archive-report #61.
- `tests/unit/test_observability.py` (MODIFY): extend with filter +
  summarize + percentile unit tests.
- `tests/unit/test_cli_metrics.py` (NEW): full CLI surface coverage
  for `flow metrics summary` + window + domain + top.
- `tests/bdd/req35_metrics_summary.feature` (NEW), `req36_metrics_window.feature`
  (NEW), `req37_metrics_domain.feature` (NEW).
- `tests/bdd/test_observability_steps.py` (NEW): pytest-bdd glue.
- `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md`
  (MODIFY): observability hook notes (~140 LOC, runtime-only).

**In scope (PR#2)**:
- `src/flow_engineering/observability.py` (MODIFY): `prometheus_exposition()`,
  `aggregate()` (mean/stddev/min/max) helpers; `METRIC_TYPE_OVERRIDES` map.
- `src/flow_engineering/cli.py` (MODIFY): `--prometheus`, `--percentile`,
  `--aggregations`, `--format` flags.
- `tests/unit/test_observability_prometheus.py` (NEW): textfile format
  round-trip.
- `tests/unit/test_observability_aggregate.py` (NEW): percentile correctness,
  gauge aggregation.
- `tests/bdd/req38_metrics_prometheus.feature` (NEW), `req39_metrics_percentile.feature`
  (NEW).
- `tests/bdd/test_observability_steps.py` (MODIFY): 2 new step groups.
- `CHANGELOG.md` (MODIFY): v0.7.0 entry post-merge.

**Out of scope (deferred to v1.1 or named follow-up changes)**:
- REQ-40 — label-based query (`--label key=value`) — defer to v1.1
- REQ-41 — threshold alerting (`--threshold name:op:N` for CI/CD) — defer to v1.1
- REQ-42 — `engine_*` counters (CLI startup, daemon queue, embedding provider) — defer to "engine-instrumentation" change
- REQ-43 — federation-aware events (`--project=<key>` filter) — defer to "federated-observability" change
- REQ-44 — JSONL rotation (`FLOW_METRICS_MAX_BYTES`, `FLOW_METRICS_MAX_AGE_DAYS`) — defer to v1.1
- Snapshot export/import — already deferred (graph-snapshots archive)
- Async embed-on-save — already deferred (vector-semantic-search archive)

### Public API surface (NEW)

```python
# observability.py — new read-side helpers
def read_events_since(path: Path | None, since_iso: str,
                      until_iso: str | None = None) -> list[dict]: ...
def read_events_by_domain(path: Path | None, domain: str) -> list[dict]: ...
def summarize(events: list[dict]) -> dict[str, dict]: ...  # {name: {count, domain, first_seen, last_seen}}
def percentile(events: list[dict], pct: int,
               field: str = "elapsed_ms") -> float: ...
def aggregate(events: list[dict],
              field: str = "value") -> dict[str, float]:
    """Return {count, mean, stddev, min, max}.""" ...
def prometheus_exposition(events: list[dict],
                          catalog: dict[str, str] | None = None) -> str: ...

# observability.py — new lookup table
DOMAIN_BY_PREFIX: dict[str, str] = {
    "suggest_": "binding", "bindings_": "binding", "inspect_": "binding",
    "backfill_": "backfill",
    "drift_": "drift",
    "vector_": "vector", "reindex_": "vector",
    "federated_": "federated",
    "snapshot_": "snapshot",
    "update_observation_metadata_": "metadata",
    "project_tag_": "metadata",
}
```

### Non-breaking guarantees

- `flow metrics` without any new flags: byte-identical to current
  behavior (flat text table sorted alphabetically).
- `flow metrics --json` without new flags: byte-identical to current
  behavior (`{name: count}` flat dict).
- `observability.read_all()` signature unchanged; existing callers
  (REQ-8 close, REQ-12, REQ-22, REQ-26, REQ-28..34) unaffected.
- All 5 record helpers (`record_backfill_coverage`,
  `record_drift_summary`, `record_vector_summary`,
  `record_federated_summary`, `record_snapshot_event`) byte-identical.
- New runtime helpers (`read_events_since`, `summarize`, etc.) are
  pure additions; no existing function modified.
- `--since` / `--until` ISO 8601 parsing reuses the precedent from
  `flow drift --since` (`cli.py:_parse_since()` factored helper).
- `openspec/specs/observability/spec.md` is a NEW file; no existing
  capability spec modified.
- All existing 801 tests pass — verified locally before PR#1 open.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `src/flow_engineering/observability.py` | MODIFY | +5 read-side helpers + `DOMAIN_BY_PREFIX` table + `METRIC_TYPE_OVERRIDES` (PR#2); ~300 LOC delta |
| `src/flow_engineering/cli.py` | MODIFY | `flow metrics` extended with 9 new flags (`--summary`, `--since`, `--until`, `--domain`, `--top`, `--percentile`, `--aggregations`, `--prometheus`, `--format`); ~200 LOC delta |
| `openspec/specs/observability/spec.md` | **NEW** | Capability spec — full catalog of 31 counters (after graph-snapshots) across 7 domains; ~200 LOC; bootstraps `openspec/specs/` (resolves archive-report #61) |
| `tests/unit/test_observability.py` | MODIFY | +filter + summarize + percentile unit tests; ~200 LOC delta |
| `tests/unit/test_cli_metrics.py` | NEW | Full CLI surface coverage; ~400 LOC |
| `tests/unit/test_observability_prometheus.py` | NEW | Textfile format round-trip; ~150 LOC (PR#2) |
| `tests/unit/test_observability_aggregate.py` | NEW | Percentile correctness, gauge aggregation; ~150 LOC (PR#2) |
| `tests/unit/test_observability_summary.py` | NEW | Unit-level coverage for `summarize()` helper; ~150 LOC |
| `tests/bdd/req35_metrics_summary.feature` | NEW | 3 scenarios: default summary, with `--since`, with `--domain` + `--top` |
| `tests/bdd/req36_metrics_window.feature` | NEW | 2 scenarios: `--since` filters, `--until` excludes |
| `tests/bdd/req37_metrics_domain.feature` | NEW | 2 scenarios: `--domain=drift` filters, `--domain=federated` filters |
| `tests/bdd/req38_metrics_prometheus.feature` | NEW | 2 scenarios: `--prometheus` emits correct exposition format |
| `tests/bdd/req39_metrics_percentile.feature` | NEW | 2 scenarios: P50/P95 from `vector_search_latency_ms`, mean/stddev from gauge |
| `tests/bdd/test_observability_steps.py` | NEW | pytest-bdd glue shared across 5 BDD features; ~200 LOC |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | MODIFY | Observability hook prose; ~140 LOC runtime-only |
| `CHANGELOG.md` | MODIFY | v0.7.0 entry post-PR#2-merge |
| `pyproject.toml` | MODIFY | Version bump (after graph-snapshots archives) |
| `openspec/changes/observability/{design,spec,tasks}.md` | NEW | follow-on phases |

## Capabilities

### New Capabilities
- `observability`: read-side aggregation, time-window filtering,
  cross-domain slicing, Prometheus textfile export, and percentile
  computation over the existing JSONL counter sink that REQ-8 shipped.
  Includes the `flow metrics summary` text dashboard and the
  `openspec/specs/observability/spec.md` capability spec (one-time
  bootstrap of the project's `openspec/specs/` baseline). All additive
  on top of change #1 (REQ-8) + change #2 (REQ-12) + change #3 (REQ-22)
  + change #4 (REQ-26) + change #5 (REQ-28..34). Flat text default
  stays byte-identical; new functionality is opt-in via flags.

### Modified Capabilities
- None. `decision-code-linking` (REQ-1..8), `decision-reality-drift`
  (REQ-9..16), `vector-semantic-search` (REQ-17..22),
  `cross-project-federation` (REQ-23..27), and `graph-snapshots`
  (REQ-28..34) all ship unchanged. The new read-side helpers consume
  the existing JSONL event format; no schema bump, no event-type
  discriminator added, no `domain` field injected into events.

## Risks

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | `graph-snapshots` (change #5) does not land before change #6 apply starts → 4 `snapshot_*` counters unstable in `SNAPSHOT_COUNTER_NAMES` catalog | HIGH | Change #6 PROPOSE waits for change #5 ARCHIVE; PR#1 SPEC references the catalog by name only and is resilient to additions |
| 2 | PR#1 cumulative realistic ~4 500 LOC > 400-line review budget; reviewers lose context | MED | Per-commit work-unit splits per `work-unit-commits` skill; 5-6 commits each ≤400 LOC; mirror `cross-project-federation` chained-PR pattern |
| 3 | JSONL rotation (REQ-44) cross-cuts `read_all()` (must read sibling `.gz` files) — risk of regression in 6 existing call sites | MED | REQ-44 explicitly deferred to v1.1; v1 ships only summary/window/domain/export/percentile (read-side only; no I/O path changes) |
| 4 | Federation-aware events (REQ-43) requires changing every record helper signature — invasive | MED | REQ-43 explicitly deferred to "federated-observability" follow-up; events stay project-less for v1 (matches today's behavior) |
| 5 | `openspec/specs/observability/spec.md` is precedent-setting — project has NO `openspec/specs/` baseline today | LOW | Confirmed via `glob openspec/specs/**` (empty); safe to bootstrap; cross-project-federation archive-report #61 explicitly defers to this change; following changes add specs to the same baseline |
| 6 | Prometheus exposition type-derivation ambiguous for `vector_index_size_observations` (gauge by suffix but used like a counter in dashboards) | LOW | Explicit `METRIC_TYPE_OVERRIDES` map in `observability.py` (PR#2); default to suffix-based derivation (`_total` → counter, `_ms`/`_seconds` → histogram, bare → gauge) |
| 7 | `--since`/`--until` parsing must mirror `flow drift --since` ISO 8601 behavior (REQ-10/11); typo or drift in parser breaks window filter | LOW | Reuse `_parse_since()` from `cli.py` (already factored); add BDD scenario GIVEN invalid ISO WHEN `flow metrics --since=garbage` THEN exit code 3 + helpful error |
| 8 | W23 carry-forward from change #5: `snapshot_pruned_total` + `snapshot_prune_total` dual-name history in metrics.jsonl may confuse the new `summarize()` | LOW | `summarize()` ignores unknown counter names (graceful); adds `unknown` bucket to summary view; does NOT warn (would be noisy on old JSONL files) |
| 9 | BDD step def file growth precedent: decision-code-linking S3 forecast 30 LOC → actual 621 LOC (5-6× multiplier) | LOW | Forecast absorbs the multiplier (`test_observability_steps.py` ~200 LOC; realistic ~1 200); per-REQ step files if size exceeds 400 LOC |
| 10 | The `flow metrics --json` flat-dict contract is consumed by external scripts; breaking it silently breaks downstream | LOW | Keep `--json` flat dict; add explicit `--format=json-detailed` for raw events; documented in `flow metrics --help` |
| 11 | `cli.py` `flow metrics` command surface is currently minimal (~13 LOC); 9 new flags will grow it ~10× → reviewer fatigue | MED | Per-commit work-unit splits per `work-unit-commits` skill; CLI surface documented inline with type annotations; help text generated by Click (no manual --help maintenance) |
| 12 | The strict-TDD ×6 LOC multiplier (per `decision-code-linking` S3) means the realistic forecast is ~10 910 LOC vs the 1 936 forecast → 2 chained PRs are MANDATORY | INFO | Already reflected in PR split (PR#1 ~4 500 LOC realistic; PR#2 ~3 300 LOC realistic); per-PR scope is well-defined |

## Rollback Plan

All artifacts are additive. Single revert of each merge commit restores
pre-change state:

- New CLI flags are opt-in (`--summary`, `--since`, `--until`, `--domain`,
  `--top`, `--percentile`, `--aggregations`, `--prometheus`, `--format`).
  Without them, `flow metrics` is byte-identical to v0.6.0.
- New helpers in `observability.py` (`read_events_since`,
  `read_events_by_domain`, `summarize`, `percentile`, `aggregate`,
  `prometheus_exposition`) are pure additions; no existing function
  modified.
- `DOMAIN_BY_PREFIX` and `METRIC_TYPE_OVERRIDES` are new lookup tables;
  existing code that uses prefix-matching directly (`drift_*`, etc.) is
  unchanged.
- `openspec/specs/observability/spec.md` is a NEW file; deleting it
  removes the capability spec but does not break any runtime behavior
  (the catalog is informational).
- 5 BDD feature files are NEW; removing them disables BDD coverage for
  the new REQs but does not break the existing 801 tests.
- The user's `~/.flow-engineering/metrics.jsonl` is NOT touched by any
  change in this proposal — the sink is read-only.

To restore the pre-change-#6 install: `git revert <PR#1-merge> <PR#2-merge>`.
The JSONL event format is unchanged; the user's existing metrics data
survives intact.

## Dependencies

- **None new.** Uses stdlib `json` + `pathlib` + `statistics` +
  `datetime` + `bisect`. The Prometheus textfile format is a string
  serialization emitted to stdout — no `prometheus_client` runtime
  dep needed.
- `decision-code-linking` (shipped v0.2.0) — `observability.increment()`,
  `read_all()`, `record_backfill_coverage()` are the foundation.
- `decision-reality-drift` (shipped v0.3.0) — `record_drift_summary()`
  emits the 8 drift counters that REQ-35/REQ-37 surface.
- `vector-semantic-search` (shipped v0.4.0) — `record_vector_summary()`
  emits the 6 vector counters + `vector_search_latency_ms` events that
  REQ-39 percentiles aggregate over.
- `cross-project-federation` (shipped v0.5.0) — `record_federated_summary()`
  emits the 3 federated counters; archive-report #61 defers the spec
  catalog to this change.
- `graph-snapshots` (change #5, IN PROGRESS) — `record_snapshot_event()`
  emits the 4 snapshot counters in batch C T1.7. MUST ARCHIVE before
  change #6 apply starts (so `SNAPSHOT_COUNTER_NAMES` is stable).
- `prompt-registry` (#7, future) — unrelated layer.

## Open Questions (for sdd-design)

The 10 questions below MUST be resolved in the design phase before
`sdd-spec` locks the requirement contract. Mirror of
[`explore.md`](./explore.md) §D, expanded with design-phase specifics.

1. **Default output change** (D.1, D.6 from explore): does the
   `flow metrics` default stay flat (`<name>  <count>`) or change to
   summary view? **Recommend** keep flat default for backwards
   compatibility (REQ-8 close shipped the flat table); `--summary`
   opt-in. Decision needed: explicit confirmation in design phase
   that no existing test relies on a particular default-output format
   (the `TestMetricsCommand` 3 tests cover text/JSON/empty — all stay
   green with flat default).

2. **Prometheus type derivation** (D.2 from explore): how does the
   exporter map flow counters to Prometheus types? **Recommend** suffix
   rule (`_total` → counter, `_ms` / `_seconds` → histogram, bare →
   gauge) with explicit `METRIC_TYPE_OVERRIDES = {"vector_index_size_observations":
   "gauge"}` map for ambiguous cases. Decision needed: should
   `_latency_ms` / `_duration_seconds` emit as Prometheus histogram
   (with bucket math) or as a summary metric (single quantile)? Recommend
   **summary** for v1 (simpler; matches REQ-39's percentile goal);
   histogram deferred to a follow-up if anyone needs bucket math.

3. **Domain categorization strategy** (D.3 from explore): prefix-based
   (`--domain=drift` matches `drift_*`) or explicit `domain` field on
   events? **Recommend** prefix-based via `DOMAIN_BY_PREFIX` table in
   `observability.py` (no helper signature changes; matches the
   existing convention). Explicit `domain` field deferred to a
   "structured-events" follow-up change.

4. **Percentile computation: at increment time vs query time** (D.4
   from explore): sliding window sketch (t-digest, HDR histogram) or
   full sort at query time? **Recommend** query-time sort + bisect
   (`statistics.quantiles` or `bisect`); O(N log N) per query; ~1000
   events sorts in <1ms. Matches the "best-effort" sink ethos; no
   in-memory state required. Sliding sketches deferred to v1.1 if
   performance becomes a real issue.

5. **`--since` / `--until` semantics**: rolling window
   (`--since=24h-ago`) vs calendar day (`--since=2026-06-26`)? **Recommend**
   support both: `--since=<iso>` (absolute) AND `--window=<1h|24h|7d>`
   (rolling shorthand). Calendar-day boundaries (`--since=today` meaning
   `00:00 UTC`) deferred unless requested. Decision needed: confirm
   the rolling shorthand matches user mental model (i.e., `1h` = last
   60 minutes, not "since the top of the hour").

6. **`--top=N` semantics**: top-N by event count, by first-seen recency,
   or by last-seen recency? **Recommend** by event count (most-fired
   first), with `--top-by=count|first_seen|last_seen` opt-in for the
   other orders. Decision needed: confirm `count` is the default (the
   use case is "what counters fire most").

7. **Backward compatibility of `--json`**: keep the flat
   `{name: count}` dict, OR change to `[{name, count, domain,
   first_seen, last_seen}, ...]` (richer)? **Recommend** keep flat
   for backwards compatibility; explicit `--format=json-detailed`
   for richer shape; `--format=json` aliases to today's contract.
   Decision needed: confirm the flat-dict contract has external
   consumers (Engram #140 vector-semantic-search proposal references
   `flow metrics --json` — confirm consumers).

8. **Dashboard format**: text-only (like `flow drift`) vs rich (if
   `rich` library is added) vs interactive TUI? **Recommend** text-only
   (`click.echo`) — zero new dependencies, consistent with `flow drift`
   / `flow status` / `flow snapshot list` precedent. Decision needed:
   confirm `rich` is not already a dependency (verify `pyproject.toml`
   before design phase locks the choice).

9. **Engine metrics** (D.8 from explore): which surfaces get
   `engine_*` counters in REQ-42 (deferred)? **Recommend** CLI startup
   time + embedding provider latency (extends REQ-22) for v1.1; daemon
   queue depth deferred to "engine-instrumentation" change. Decision
   needed: confirm scope of REQ-42 is small enough to land in v1.1.

10. **`openspec/specs/` bootstrap policy**: change #6 creates the
    project's first capability spec at `openspec/specs/observability/spec.md`.
    Should subsequent changes add specs to the same baseline (kebab-case
    folder per capability, e.g., `openspec/specs/vector-semantic-search/spec.md`),
    OR co-locate specs in the change folder? **Recommend** baseline
    pattern (matches the sdd-propose skill template "New Capabilities →
    each becomes `openspec/specs/<name>/spec.md`"). Decision needed:
    confirm with the orchestrator that the `openspec/specs/` baseline
    pattern is the long-term convention (not co-located).

## Success Criteria

- [ ] `flow metrics summary` renders a text dashboard with totals,
      per-domain breakdown, top-N counters, and a freshness timestamp
      (REQ-35, 3 BDD scenarios)
- [ ] `flow metrics --since=<iso>` filters events to those with
      `ts >= <iso>` (REQ-36, 2 BDD scenarios)
- [ ] `flow metrics --since=<iso> --until=<iso>` filters to
      `[since, until]` window (REQ-36, included in same scenarios)
- [ ] `flow metrics --window=1h|24h|7d` shorthand works and is
      byte-equivalent to the corresponding `--since` (REQ-36)
- [ ] `flow metrics --domain=<binding|drift|vector|snapshot|federated|backfill|metadata|engine>`
      filters by counter name prefix (REQ-37, 2 BDD scenarios)
- [ ] `flow metrics --top=N` limits the output to the N most-fired
      counters (REQ-35 + REQ-37 combined, included in summary scenarios)
- [ ] `flow metrics --prometheus` emits valid Prometheus textfile
      exposition format with `# HELP`, `# TYPE`, and metric lines
      (REQ-38, 2 BDD scenarios)
- [ ] `flow metrics --percentile=p95` computes the 95th percentile of
      `*_latency_ms` events within the active filter (REQ-39, 2 BDD
      scenarios)
- [ ] `flow metrics --aggregations` emits `{count, mean, stddev,
      min, max}` per counter (REQ-39, included in percentile scenarios)
- [ ] `flow metrics` without new flags is byte-identical to v0.6.0
      behavior (regression test from REQ-8 close stays green)
- [ ] `flow metrics --json` without new flags is byte-identical to
      v0.6.0 behavior (regression test stays green)
- [ ] All 31 counter names (after graph-snapshots) appear in
      `openspec/specs/observability/spec.md` with their domain and
      helper provenance
- [ ] `DOMAIN_BY_PREFIX` table covers all 31 counters with no orphans
      (BDD scenario GIVEN a counter THEN its domain is in the table)
- [ ] `--since=garbage` exits with code 3 + helpful error message
      (REQ-36 edge case, defensive parser)
- [ ] Existing 801 tests pass; `ruff check` clean on changed files
- [ ] Strict TDD evidence: every public helper has RED→GREEN→REFACTOR
      history in commit log; per-commit work-unit splits per
      `work-unit-commits` skill (5-6 commits each ≤400 LOC)
- [ ] Secrets invariant: a metric event referencing `secrets.yaml`
      (via a future code_refs integration) does NOT leak the file path
      into the Prometheus exposition output beyond the documented
      label keys
- [ ] REQ-8 (observability sink) unchanged
- [ ] REQ-12 (drift counters) unchanged
- [ ] REQ-22 (vector counters) unchanged
- [ ] REQ-26 (federated counters) unchanged
- [ ] REQ-28..34 (snapshot counters) unchanged
- [ ] Drift detector (REQ-9..16) unchanged — no new metric calls in the
      drift path
- [ ] Vector search path (REQ-17..22) unchanged — no new metric calls
      in the search path
- [ ] Federation path (REQ-23..27) unchanged — no new metric calls in
      the federated search path
- [ ] Snapshot path (REQ-28..34) unchanged — no new metric calls in
      the snapshot create/list/diff/rollback/prune paths

## Cross-Impact

| Queued/shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | 8 counters stable; `record_backfill_coverage()` reused | Compatible (consumes the seam) |
| `decision-reality-drift` (shipped v0.3.0) | 8 counters stable; `record_drift_summary()` reused | Compatible (consumes the seam) |
| `vector-semantic-search` (shipped v0.4.0) | 6 counters stable; `record_vector_summary()` emits `vector_search_latency_ms` events that REQ-39 percentiles over | Compatible (consumes the seam) |
| `cross-project-federation` (shipped v0.5.0) | 3 counters stable; `record_federated_summary()` reused; archive-report #61 explicitly defers to this change | Compatible (resolves #61) |
| `graph-snapshots` (change #5, IN PROGRESS) | 4 counters land in batch C T1.7; `record_snapshot_event()` reused | MUST ARCHIVE BEFORE change #6 apply; coordinate via orchestrator |
| `prompt-registry` (#7, future) | Unrelated layer | No conflict |

**Unblocks**: text dashboard for the 27 counters already shipped
(REQ-35); Prometheus integration for local CI/CD + Grafana (REQ-38);
percentile-based latency SLO tracking (REQ-39); federation-aware
filtering (REQ-43 deferred); rotation policy (REQ-44 deferred);
and — as a one-time bootstrap — the project's `openspec/specs/`
baseline that all subsequent changes will extend.

**Constrains**: any future change that adds a counter name MUST
either add it to `DOMAIN_BY_PREFIX` or update the prefix rule; the
flat text default of `flow metrics` MUST stay byte-identical to
v0.6.0 for backwards compatibility with existing scripts and tests.

## Estimated Effort

- **Apply LOC (forecast)**: ~626 production + ~1 170 tests = ~1 936
  forecast total. Realistic ×6 TDD multiplier (per `decision-code-linking`
  S3 precedent): ~10 910 realistic.
- **Chained PR strategy**: **YES — 2 chained PRs** (mandatory given the
  realistic LOC exceeds the 400-line review budget by ~27×):
  - **PR#1 (foundation)** — REQ-35 + REQ-36 + REQ-37 +
    `openspec/specs/observability/spec.md` bootstrap. Forecast ~750;
    realistic ~4 500.
  - **PR#2 (export + aggregation)** — REQ-38 + REQ-39. Forecast ~550;
    realistic ~3 300.
  - Per-PR work-unit commit splits per `work-unit-commits` skill
    (5-6 commits each ≤400 LOC).
- **Phase estimate**:
  - ~20min explore (DONE; Engram #183)
  - ~10min propose (this phase)
  - ~30min design
  - ~25min spec
  - ~20min tasks
  - ~90-120min apply across 2 chained PRs (PR#1 ~60min, PR#2 ~45min)
  - ~15min verify
  - ~10min archive
  - **Total ~3.5-4h end-to-end**

## References

- Explore: [`explore.md`](./explore.md) (Engram #183, full option matrix)
- Prior patterns:
  - `openspec/changes/archive/2026-06-27-graph-snapshots/` (change #5, single-PR precedent)
  - `openspec/changes/archive/2026-06-26-cross-project-federation/` (change #4, chained-PR precedent)
  - `openspec/changes/archive/2026-06-26-vector-semantic-search/` (change #3, observability-adjacent counter catalog pattern)
- Counter catalog patterns: REQ-22 (`VECTOR_COUNTER_NAMES`),
  REQ-26 (`FEDERATED_COUNTER_NAMES`), REQ-26 snapshot
  (`SNAPSHOT_COUNTER_NAMES`) — all in `observability.py:85,104,124`
- Carry-forwards: `vector-semantic-search` archive-report #154
  ("Beyond REQ-8 dashboards — change #6 owns"); `cross-project-federation`
  archive-report #61 (`openspec/specs/observability/spec.md` catalog)
- Precedent: `decision-code-linking` archive-report #119 S3
  (BDD step def file 5-6× growth multiplier) — absorbed into
  the ×6 forecast

## Next Step

Ready for `sdd-design observability`. The 10 open questions above
MUST be resolved in the design phase (especially #1 default-output
stability, #2 Prometheus type derivation, #4 percentile computation
strategy, and #10 `openspec/specs/` bootstrap policy) before
`sdd-spec` locks the requirement contract. **2 chained PRs** —
foundation PR#1 first (REQ-35 + REQ-36 + REQ-37 + spec bootstrap),
integration PR#2 second (REQ-38 + REQ-39). Coordination: change #5
graph-snapshots MUST archive before change #6 apply starts.

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_module",
      "label": "observability.py (413→~700 LOC after change #6; 5 read-side helpers + 2 lookup tables)",
      "file": "src/flow_engineering/observability.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_increment",
      "label": "increment(name, **fields) — unchanged primary sink API",
      "file": "src/flow_engineering/observability.py",
      "line": 162,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_read_all",
      "label": "read_all(path) — REUSED (no signature change); new helpers compose on top",
      "file": "src/flow_engineering/observability.py",
      "line": 193,
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
      "id": "src_flow_engineering_observability_record_drift_summary",
      "label": "record_drift_summary(report) — unchanged (REQ-12, 8 drift counters surfaced by REQ-35/REQ-37)",
      "file": "src/flow_engineering/observability.py",
      "line": 307,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_vector_summary",
      "label": "record_vector_summary(...) — unchanged; vector_search_latency_ms events power REQ-39 percentiles",
      "file": "src/flow_engineering/observability.py",
      "line": 353,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_federated_summary",
      "label": "record_federated_summary(...) — unchanged (REQ-26, 3 federated counters)",
      "file": "src/flow_engineering/observability.py",
      "line": 411,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_snapshot_event",
      "label": "record_snapshot_event — unchanged (REQ-26 T1.7, 4 snapshot counters)",
      "file": "src/flow_engineering/observability.py",
      "line": 453,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_metrics_command",
      "label": "flow metrics subcommand (cli.py:977-992, 13 LOC) — extended with 9 new flags in change #6",
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
      "label": "tests/bdd/req35_metrics_summary.feature (NEW — 3 BDD scenarios)",
      "file": "tests/bdd/req35_metrics_summary.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req36_metrics_window",
      "label": "tests/bdd/req36_metrics_window.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req36_metrics_window.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req37_metrics_domain",
      "label": "tests/bdd/req37_metrics_domain.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req37_metrics_domain.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req38_metrics_prometheus",
      "label": "tests/bdd/req38_metrics_prometheus.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req38_metrics_prometheus.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req39_metrics_percentile",
      "label": "tests/bdd/req39_metrics_percentile.feature (NEW — 2 BDD scenarios)",
      "file": "tests/bdd/req39_metrics_percentile.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_observability_steps",
      "label": "tests/bdd/test_observability_steps.py (NEW — pytest-bdd glue shared across 5 BDD features)",
      "file": "tests/bdd/test_observability_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_cli_metrics",
      "label": "tests/unit/test_cli_metrics.py (NEW — full CLI surface coverage for flow metrics)",
      "file": "tests/unit/test_cli_metrics.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    }
  ]
}