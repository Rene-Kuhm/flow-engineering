<!-- explore.md: change #6 observability. Source: manual. -->
# Explore: observability (change #6)

**Change:** `observability`
**Scope:** Investigate the existing JSONL counter sink + `flow metrics` CLI; identify user-facing gaps; propose REQs for change #6.
**Date:** 2026-06-27
**Status:** EXPLORED → ready for sdd-propose
**Strict TDD:** ON for the IMPLEMENTATION phase; this explore work is read-only report production.
**Builds on:** change #1 (decision-code-linking REQ-8), change #2 (decision-reality-drift REQ-12), change #3 (vector-semantic-search REQ-22), change #4 (cross-project-federation REQ-26), change #5 (graph-snapshots REQ-28..34, IN PROGRESS).

---

## Why this change exists

The user prompt framing is precise: there is NO observability layer to build from scratch. There is an evolving append-only JSONL counter sink (`src/flow_engineering/observability.py`, 413 LOC, base commit `80d82f1`) plus a minimal `flow metrics` CLI subcommand that has been incrementally extended by 4 prior changes (REQ-8, REQ-12, REQ-22, REQ-26). What's missing is the **read-side** — aggregation, time-window filtering, cross-domain slicing, export formats, dashboards, alerting. The vector-semantic-search archive-report (#154) is explicit: "Beyond REQ-8 dashboards — change #6 owns". The cross-project-federation archive-report also defers a `openspec/specs/observability/spec.md` capability spec to a "future observability change". This is that change.

**Headline use case** (synthesized from prior-change deferrals + ARCHIVED-spec surface): a user runs `flow metrics` after a few hours of work and gets a single text dump `<counter_name>  <count>` with no way to ask "how did vector search perform in the last hour?" or "what's my drift trend across all changes?". Change #6 ships the read-side that answers those questions.

---

## A. Current State

### A.1 The counter sink (JSONL at `~/.flow-engineering/metrics.jsonl`)

The module is at `src/flow_engineering/observability.py:1`. Public surface:

| Symbol | Line | Purpose |
|---|---|---|
| `DEFAULT_METRICS_DIR` | 57 | `Path.home() / ".flow-engineering"` |
| `DEFAULT_METRICS_FILE` | 58 | `"metrics.jsonl"` |
| `METRICS_PATH_ENV` | 59 | `"FLOW_METRICS_PATH"` — test override |
| `STALE_DAYS_THRESHOLD` | 64 | 30 — used by freshness helper, not observability |
| `VECTOR_COUNTER_NAMES` | 70 | **catalog** of 6 REQ-22 vector counter names |
| `FEDERATED_COUNTER_NAMES` | 89 | **catalog** of 3 REQ-26 federated counter names |
| `default_metrics_path()` | 106 | production path resolver |
| `_resolve_path()` | 115 | env > default precedence |
| `_now_iso()` | 123 | UTC ISO 8601 with `Z` suffix |
| `increment(name, **fields)` | 128 | **primary sink API** — appends one JSONL line |
| `flush()` | 149 | no-op (reserved for future buffered writers) |
| `read_all(path)` | 159 | parse JSONL back into `list[dict]` (skips malformed lines) |
| `_extract_block_source()` | 183 | helper for backfill coverage scan |
| `backfill_coverage()` | 208 | derived ratio (REQ-8 close) |
| `record_backfill_coverage()` | 228 | REQ-8 — emits 2 counters |
| `_format_age()` / `compute_freshness()` | 237 / 256 | REQ-7 freshness helpers |
| `record_drift_summary()` | 273 | REQ-12 — emits 8 drift counters |
| `VECTOR_TRIGGER_VALUES` | 316 | `frozenset({"cli", "programmatic"})` |
| `record_vector_summary()` | 319 | REQ-22 — emits 6 vector counters |
| `FEDERATED_TRIGGER_VALUES` | 374 | `frozenset({"cli", "programmatic"})` |
| `record_federated_summary()` | 377 | REQ-26 — emits 3 federated counters |

### A.2 JSONL event schema (per line)

Every `increment(name, **fields)` call produces one line:

```json
{"name": "<counter_name>", "fields": {...}, "ts": "YYYY-MM-DDTHH:MM:SSZ"}
```

- `name`: counter identifier (string, kebab-case preferred, `_total`/`_ms`/`_seconds` suffix conventions per REQ-8)
- `fields`: free-form dict (most commonly `count=<int>`, `value=<float>`, `trigger=<cli|programmatic>`, `change=<name>`, `elapsed_ms=<int>`, etc.)
- `ts`: UTC ISO 8601 with `Z` suffix (lexicographic-sort-safe)

No schema versioning. No event-type discriminator. No domain/category field on the event itself — domains are inferred from name prefix today (`drift_*`, `vector_*`, `federated_*`, `snapshot_*`, `suggest_*`, etc.).

### A.3 Catalog sprawl — counter names currently used

I counted **27 distinct counter names** across the codebase (grep + cross-reference of all helpers + direct `observability.increment(...)` call sites). The split:

**In explicit catalogs (8 names, 2 catalogs):**

| Catalog | REQ | Counter names |
|---|---|---|
| `VECTOR_COUNTER_NAMES` (6) | REQ-22 | `vector_search_invoked_total`, `vector_search_results_returned_total`, `vector_search_latency_ms`, `vector_index_size_observations`, `reindex_observations_total`, `reindex_duration_seconds` |
| `FEDERATED_COUNTER_NAMES` (3) | REQ-26 | `federated_search_invoked_total`, `federated_search_projects_queried`, `federated_search_results_returned_total` |

**Counters used but NOT in a catalog list (19 names — sprawl):**

| Domain | REQ | Counter names |
|---|---|---|
| Binding (REQ-8) | REQ-6/8 | `suggest_invoked_total`, `suggest_hit_total`, `suggest_miss_total`, `bindings_confirmed_total` (4) |
| Inspect (REQ-8 close) | REQ-7/8 | `inspect_invoked_total`, `inspect_render_ms` (2) |
| Backfill coverage | REQ-8 | `backfill_observations_total`, `backfill_with_refs_total` (2) |
| Drift (REQ-12) | REQ-12 | `drift_invoked_total`, `drift_still_valid_total`, `drift_label_drift_total`, `drift_stale_location_total`, `drift_stale_id_total`, `drift_obsolete_total`, `drift_contradicted_total`, `drift_unable_to_verify_total` (8) |
| Drift write-back (REQ-13) | REQ-13 | `drift_write_back_failed_total`, `drift_write_back_skipped_total` (2) |
| Metadata update (REQ-13) | REQ-13 | `update_observation_metadata_failed_total` (1) |
| Project backfill (REQ-24) | REQ-24 | `project_tag_backfill_failed_total`, `project_tag_backfilled_total` (2) |

**Partially-landed counters (1 name):**

- `snapshot_rollback_total` (with `success="true|false"`, `safety_snapshot_id`, `target_snapshot_id` fields) — emitted directly by `snapshot_manager.py:826-851` `_record_rollback_event` helper. The full `SNAPSHOT_COUNTER_NAMES` catalog + `record_snapshot_event` helper land in batch C (T1.7) of change #5.

**Total counters expected after graph-snapshots lands: ~31** (28 + 4 snapshot - 1 partial = 31, since the partial `snapshot_rollback_total` becomes part of the catalog).

### A.4 Record helpers (4 today, 5 after change #5)

| Helper | REQ | Catalog size | Aggregator |
|---|---|---|---|
| `record_backfill_coverage(observations_total, with_refs)` | REQ-8 | 2 | one-shot |
| `record_drift_summary(report)` | REQ-12 | 8 | per-class counts |
| `record_vector_summary(invoked, results, latency, index_size, trigger, reindex_observations, reindex_duration)` | REQ-22 | 6 | search-call + optional reindex |
| `record_federated_summary(invoked, projects_queried, results, trigger)` | REQ-26 | 3 | per-call |
| `record_snapshot_event(name, **fields)` | (graph-snapshots T1.7) | 4 | per-event |

### A.5 JSONL file lifecycle

- **Path resolution**: `FLOW_METRICS_PATH` env override > `default_metrics_path()` (`~/.flow-engineering/metrics.jsonl`). Tests use `monkeypatch.setenv` (8 unit test files use this pattern).
- **Parent directory**: created on demand via `path.parent.mkdir(parents=True, exist_ok=True)` (defensive against missing `~/.flow-engineering/`).
- **Rotation**: NONE. The file is append-forever. There is no `max_bytes`, no `max_age`, no `*.1.gz` rollover, no compaction. After 6 months of daily `flow drift` runs the file will grow unbounded.
- **Concurrency**: NO thread or process lock. `path.open("a", ...)` opens per call, so concurrent writers from a daemon (`flow watch`) + a CLI invocation may interleave lines. The `os.write` syscall is atomic on POSIX for short writes (<PIPE_BUF) but the JSON encode + write pair is NOT atomic — a partial line on crash is possible.
- **Failure mode**: `OSError` on `path.open` or `fh.write` is swallowed (best-effort: "the counter MUST NOT break the save flow"). Malformed JSONL lines on `read_all` are skipped.
- **Buffered writes**: `flush()` is a no-op. Every increment calls `path.open("a", ...)` + writes synchronously. Throughput is adequate for human-driven CLI but a hot loop in a test (e.g. 1000 events) will do 1000 syscalls.

### A.6 CLI surface — `flow metrics`

The current `flow metrics` command is at `cli.py:975-990`. Full surface:

```
flow metrics [--json]
```

Behavior (cli.py:978-990):

1. Calls `observability.read_all()` — reads ALL events from the JSONL sink (no filtering).
2. `_summarize_metrics(events)` collapses events into `{name: count}` by summing `fields.get("count") or fields.get("confirmed") or 1`.
3. If `--json`: emits `json.dumps(summary, indent=2)` (a flat `{name: count}` dict).
4. Else: emits one row per counter sorted alphabetically, format `<name>  <count>` (no header, no totals, no time info).

That's it. No flags for:
- `--since=<iso>` / `--until=<iso>` (time window)
- `--domain=<binding|drift|vector|snapshot|federated>` (cross-domain slice)
- `--label key=value` (label-based filter)
- `--top=<N>` (top-N by count)
- `--percentile=<p>` (P50/P95/P99 derivation)
- `--rate` (events/min derivation)
- `--prometheus` (Prometheus textfile exporter)
- `--csv` (CSV exporter)
- `--summary` (text dashboard with totals + by-domain breakdown)
- `--project=<key>` (federation-aware)

### A.7 Test coverage

| Test file | LOC | Purpose |
|---|---|---|
| `tests/unit/test_observability.py` | 179 | REQ-8 sink: increment/flush/path/counter-names/read-all (17 tests) |
| `tests/unit/test_observability_inspect.py` | 7 968 (whole file) | REQ-8 close: `inspect_invoked_total` + `inspect_render_ms` |
| `tests/unit/test_observability_vectors.py` | 17 285 (whole file, ~445 LOC for this file alone) | REQ-22: catalog + `record_vector_summary` (20 tests) |
| `tests/unit/test_observability_federated.py` | 13 475 (whole file, ~351 LOC for this file alone) | REQ-26: catalog + `record_federated_summary` |
| `tests/unit/test_cli_inspect.py::TestMetricsCommand` | 30 LOC, 3 tests | CLI `flow metrics` text/JSON/empty |
| `tests/unit/test_decision_drift.py::test_observability_drift_counters` | ~30 LOC, 1 test | REQ-12: 8 drift counters |
| `tests/unit/test_hybrid_backend.py` | 30 584 (whole file) | REQ-22 integration: `record_vector_summary` fires on hybrid search |
| `tests/unit/test_engram_io.py` | 14 845 (whole file) | REQ-26 integration: `record_federated_summary` fires on federated search |
| `tests/unit/test_cli_drift.py` | 21 600 (whole file) | REQ-12: CLI `flow drift` increments `drift_*` counters |

**Coverage gaps for change #6:**

- No BDD feature file covers `flow metrics` (BDD coverage is per-domain-counter; `flow metrics` itself is unit-tested only).
- No test exercises `flow metrics` with `--since` / `--domain` / `--prometheus` / `--percentile` (they don't exist).
- No test for JSONL rotation.
- No test for multi-process concurrent writes.
- No test for federation-aware slicing (no `--project=<key>` flag).

### A.8 Deferred work from prior changes (sourced from archive reports)

| Source | Item | Status |
|---|---|---|
| vector-semantic-search archive-report #154 (line 87) | "Beyond REQ-8 dashboards — change #6 owns" | OPEN — this change |
| cross-project-federation archive-report (line 61) | "Spec counter catalog in `openspec/specs/observability/spec.md` for the 3 new `federated_*` counters (REQ-26 scenario 4) — defer to a future observability change" | OPEN — this change |
| vector-semantic-search tasks S3 | `vector_search_missing_embedding_total` was referenced in T1.7 acceptance but never implemented | OPEN — could be addressed by adding a missing-embedding counter in change #6 |
| decision-reality-drift verify W5/W6 | REQ-15 daemon emits a stdout summary line (not the spec'd JSONL event log); still-valid does not suppress | orthogonal — not change #6 scope |
| decision-reality-drift verify W7 | CHANGELOG typo `drift_scan_total` vs impl `drift_invoked_total` | RESOLVED — current CHANGELOG.md:65 uses `drift_invoked_total` correctly |
| decision-reality-drift verify W8 | dataclass shape drift (`decision_id: str` vs `int`, `scanned_at: float` vs `str`) | orthogonal |
| decision-code-linking archive-report S3 | BDD step def file 621 LOC vs 30 LOC forecast (5-6× growth) | pattern precedent for change #6 forecast |
| graph-snapshots tasks "Open follow-ups" #1 | "Spec counter catalog in `openspec/specs/observability/spec.md` for the 4 new `snapshot_*` counters (REQ-22/26 pattern)" — defer to sdd-archive | OPEN — this change (or archived separately) |
| graph-snapshots tasks "Open follow-ups" #2 | "Bump `pyproject.toml` version `0.5.0` → `0.6.0` (matches CHANGELOG entry)" | orthogonal to observability; resolve when graph-snapshots archives |
| graph-snapshots tasks "Open follow-ups" #3 | "Verify `MEMORY.md` or AGENTS.md mentions `flow snapshot` workflow" | orthogonal |

---

## B. Gap Analysis

10 user-facing gaps. Severity is rated against the project's needs (small B2B dev tool, 1 active user, 783 tests, 5 shipped changes, ~170 observations).

### Gap 1 — Aggregation (sum/rate/percentile) [HIGH]

**What**: `flow metrics` only produces a flat `{name: count}` dict. It cannot derive:
- P50 / P95 / P99 latencies from `vector_search_latency_ms` / `inspect_render_ms` events
- Events/min rate from any counter
- Mean/stddev across gauge values (e.g. `vector_index_size_observations`)
- Total across all counters in a domain

**Why HIGH**: The latency_ms counters exist and emit `elapsed_ms=<int>` per event; the JSONL has the raw data; the user can `awk` the JSONL manually but the project itself doesn't expose it. The vector-semantic-search verify-report (#152) explicitly noted "downstream `flow metrics` summary can compute P50/P95/P99" — that promise was never shipped.

**Severity**: HIGH. The data is captured but inaccessible without a separate Python script.

**Proposed REQ**: **REQ-39** — `flow metrics --percentile=<p>` and/or `flow metrics --aggregations` derive P50/P95/P99 from latency_ms events.

---

### Gap 2 — Time-series window (`--since` / `--until`) [HIGH]

**What**: `flow metrics` reads ALL events from the file. There is no way to ask "show me the last 1h". The `flow search --since=<iso>` flag already exists (REQ-25 added it); `flow drift --since=<epoch>` exists (REQ-10/11); `flow snapshot list --since=<iso>` exists (REQ-29). `flow metrics` is the odd one out.

**Why HIGH**: After 6 months of usage the JSONL will have thousands of events; the user cannot isolate "what happened today" vs "the all-time total".

**Severity**: HIGH. Trivial fix; high user value.

**Proposed REQ**: **REQ-36** — `flow metrics --since=<iso> --until=<iso>` filters events by `ts` field.

---

### Gap 3 — Cross-domain slicing (`--domain`) [HIGH]

**What**: There are 4-5 counter domains today (binding/inspect/backfill, drift, vector, federated, snapshot-after-change-5) plus orphan counters (`update_observation_metadata_failed_total`, `project_tag_backfilled_total`, `drift_write_back_*`). A user asking "how is drift doing?" gets ALL counters alphabetically mixed with vector/search events.

**Why HIGH**: The data is siloed by name prefix today; the user has to mentally filter.

**Severity**: HIGH. Easy fix; high user value.

**Proposed REQ**: **REQ-37** — `flow metrics --domain=<binding|drift|vector|snapshot|federated|backfill|metadata|engine>` filters by domain prefix or explicit category.

---

### Gap 4 — Label-based query (`--label key=value`) [MEDIUM]

**What**: Events carry a free-form `fields` dict with values like `trigger=cli|programmatic`, `change=<name>`, `success=true|false`. There is no way to query "show me all `trigger=cli` events in the last hour".

**Why MEDIUM**: The labels exist; the question is whether the user actually needs this vs accepting the flat view. For a 1-user tool this is nice-to-have, not blocking.

**Severity**: MEDIUM.

**Proposed REQ**: **REQ-40** (lower priority) — `flow metrics --label trigger=cli` filters by label predicate.

---

### Gap 5 — Export (Prometheus / CSV / detailed JSON) [HIGH]

**What**: The ONLY export is `--json` which emits a flat `{name: count}` dict. For integration with Prometheus, Grafana, or just plain CSV ingestion, the user must re-parse and re-aggregate. The Prometheus exposition format is well-defined and trivially generable from the JSONL.

**Why HIGH**: Local-first B2B tools almost always need Prometheus textfile export (one-line per counter, scraped by node_exporter). The flow-engineering metrics are already at `~/.flow-engineering/metrics.jsonl` — one step away from `metrics.prom`.

**Severity**: HIGH. Medium-effort; high integration value.

**Proposed REQ**: **REQ-38** — `flow metrics --prometheus` emits Prometheus textfile format (`# HELP`, `# TYPE`, metric line with optional `{label="value"}`). Additionally `--format=json-detailed` emits the raw events as JSON Lines (each event as a JSON object on its own line) for downstream consumption.

---

### Gap 6 — Dashboard view (`flow metrics summary`) [HIGH]

**What**: The vector-semantic-search archive-report (#154) explicitly defers dashboards to change #6. Today there is no summary view — the user gets an alphabetised list of counters with no totals, no per-domain breakdown, no "top 5 by activity".

**Why HIGH**: The single most-asked question for a metrics CLI is "is everything healthy?" — which requires a SUMMARY view, not a raw dump.

**Severity**: HIGH. Medium-effort (mostly UI/text formatting).

**Proposed REQ**: **REQ-35** — `flow metrics summary [--since] [--domain] [--top=N]` renders a text dashboard with: total events, total counters seen, per-domain counter counts, top-N counters by activity, freshness timestamp ("data is from 2026-06-26 to 2026-06-27").

---

### Gap 7 — Alerting (threshold-based) [MEDIUM]

**What**: No threshold-based alerting. A user cannot ask "alert me if `drift_contradicted_total > 0` in the last hour".

**Why MEDIUM**: For a 1-user tool, alerting via daemon (`flow watch`) is a different change (#7 prompt-registry territory). Change #6 could ship `flow metrics --threshold name:N --exit-code` to fail CI/CD if a threshold is breached, but this is mostly a CI/CD concern.

**Severity**: MEDIUM.

**Proposed REQ**: **REQ-41** (lower priority, defer to v1.1) — `flow metrics --threshold <name>:<op>:<N>` exits non-zero when threshold breached; for CI/CD gating.

---

### Gap 8 — FLOW engine metrics (queue depth, throughput, errors) [MEDIUM]

**What**: Today the counters measure **user-facing events** (`flow drift`, `flow search --semantic`, `flow save` auto-suggest). There are NO counters for the **engine internals**: daemon queue depth, watcher event throughput, embedding provider latency (only `vector_search_latency_ms` exists, not `embedding_provider_embed_ms`), CLI startup time, snapshot create/diff/rollback duration.

**Why MEDIUM**: Useful for diagnosing slow flows; nice-to-have for a 1-user tool. The latency_ms counters for the engine exist via `inspect_render_ms` but no equivalent for `flow snapshot create` or `flow search` overall.

**Severity**: MEDIUM.

**Proposed REQ**: **REQ-42** (lower priority) — `flow_engineering.engine.*` counter family for engine-internal metrics. Examples: `engine_cli_invoked_total{command=drift|search|save}`, `engine_daemon_queue_depth` (gauge), `engine_embedding_ms` (histogram).

---

### Gap 9 — Federation-aware slicing (`--project=<key>`) [LOW-MEDIUM]

**What**: cross-project-federation (change #4) added `project` tagging to observations + `project_aliases.json` + `project_detector`. The observability counters do NOT carry a `project` field today — events fire from CLI invocations without a project context.

**Why LOW-MEDIUM**: For a single-project workflow (which is most of today's usage), this is moot. For federated workflows, the user cannot ask "what counters fired in `flow-image-generator-main` vs `flow-engineering`?" because the events have no project field.

**Severity**: LOW-MEDIUM. Adding `project` to every event is invasive (every helper signature changes).

**Proposed REQ**: **REQ-43** (lower priority, may defer to a "federated-observability" change if scope grows) — add `project=<key>` field to events fired from project-aware surfaces; `--project=<key>` filter on `flow metrics`.

---

### Gap 10 — JSONL rotation policy [MEDIUM]

**What**: The JSONL file grows unbounded. There is no `max_bytes`, no `max_age`, no `*.gz` rollover, no compaction.

**Why MEDIUM**: For a 1-user tool with ~10 events/day, the file stays small (<1 MB) for years. But a heavy user running `flow watch --drift` for a day could emit thousands of events. A safety net is appropriate.

**Severity**: MEDIUM. Easy fix; protects against runaway growth.

**Proposed REQ**: **REQ-44** (lower priority, may be small enough to bundle into REQ-35 summary) — `FLOW_METRICS_MAX_BYTES` (default 50 MB) and `FLOW_METRICS_MAX_AGE_DAYS` (default 90) env vars trigger rename-to-`.1.jsonl.gz` rollover on `increment`. Existing default path (`metrics.jsonl`) reads from current + rolled-over siblings on `read_all`.

---

## C. Proposed Scope for Change #6

### C.1 Recommendation: TOP 3-5 gaps to address

The user prompt asks for the TOP 3-5. Based on severity + effort + precedent deferrals:

| Priority | Gap | REQ | Effort |
|---|---|---|---|
| **P0 (must)** | Gap 6 — Dashboard view | **REQ-35** `flow metrics summary` | M |
| **P0 (must)** | Gap 3 — Cross-domain slicing | **REQ-37** `flow metrics --domain` | S |
| **P0 (must)** | Gap 2 — Time-series window | **REQ-36** `flow metrics --since/--until` | S |
| **P1 (should)** | Gap 5 — Prometheus export | **REQ-38** `flow metrics --prometheus` | M |
| **P1 (should)** | Gap 1 — Aggregation | **REQ-39** `flow metrics --percentile/--aggregations` | M |

Lower-priority (defer to v1.1 or a follow-up change):

- Gap 4 (label query) — **REQ-40**
- Gap 7 (alerting) — **REQ-41**
- Gap 8 (engine metrics) — **REQ-42**
- Gap 9 (federation-aware) — **REQ-43**
- Gap 10 (rotation) — **REQ-44**

### C.2 REQ-by-REQ complexity forecast

For the P0/P1 scope (5 REQs):

| REQ | Title | Forecast LOC prod | Forecast LOC test | TDD multiplier ×6 | BDD scenarios |
|---|---|---|---|---|---|
| REQ-35 | `flow metrics summary [--since] [--domain] [--top=N]` text dashboard | ~120 | ~300 | ~720 | 3 |
| REQ-36 | `flow metrics --since=<iso> --until=<iso>` time window | ~50 | ~150 | ~300 | 2 |
| REQ-37 | `flow metrics --domain=<binding|drift|vector|snapshot|federated|backfill|metadata|engine>` | ~50 | ~150 | ~300 | 2 |
| REQ-38 | `flow metrics --prometheus` Prometheus textfile exporter | ~80 | ~200 | ~480 | 2 |
| REQ-39 | `flow metrics --percentile=<p>` and `--aggregations` | ~80 | ~250 | ~600 | 2 |
| **Total** | | **~380 prod** | **~1 050 test** | **~2 400 realistic** | **11 BDD** |

Plus shared infrastructure:
- `src/flow_engineering/observability.py` — new helpers `read_events_since(path, since)`, `read_events_by_domain(path, domain)`, `summarize(path, ...)` (~150 LOC delta)
- `src/flow_engineering/cli.py` — `flow metrics` extended with 5 flags (~150 LOC delta)
- `openspec/specs/observability/spec.md` — NEW (the capability spec the federation archive-report #61 was waiting for; ~150 LOC; resolves "Spec counter catalog ... defer to a future observability change")
- `CHANGELOG.md` v0.7.0 entry (~25 LOC)
- 6 `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` updates (~120 LOC total, runtime-only)

**Grand total forecast**: ~2 000 LOC; realistic ×6 TDD multiplier: **~12 000 LOC** (within the cross-project-federation precedent of 7 200 realistic for 1 200 forecast).

### C.3 PR split recommendation

**Recommend: 2 PRs (chained)** because the cumulative ~12 000 LOC realistic > the 400-line review budget:

| PR | Scope | REQs | Forecast LOC | Realistic ×6 |
|---|---|---|---|---|
| **PR#1** | Foundation + summary + slicing + window | REQ-35 + REQ-36 + REQ-37 | ~750 | ~4 500 |
| **PR#2** | Export + aggregation | REQ-38 + REQ-39 | ~550 | ~3 300 |

Per-PR work-unit commit splits per `work-unit-commits` skill convention (5-6 commits each ≤400 LOC).

Rationale for 2 PRs over 1:
- Cumulative realistic LOC ~12 000 is ~30× the 400-line review budget; even with per-commit splits the review load is heavy.
- PR#1 (summary/slicing/window) is the "user-facing dashboard" — high value, must land first.
- PR#2 (export/aggregation) is the "integration surface" — needed for CI/CD + Prometheus, but not blocking for the dashboard user.

Chained-PR-as-commits pattern from `work-unit-commits` SKILL mitigates review tractability.

### C.4 Recommended 6-10 specific REQs

P0 (must, this change):

- **REQ-35** — `flow metrics summary [--since=<iso>] [--until=<iso>] [--domain=<d>] [--top=<N>]` text dashboard rendering totals + per-domain breakdown + top-N counters.
- **REQ-36** — `flow metrics --since=<iso> --until=<iso>` time-window filter on `ts` field.
- **REQ-37** — `flow metrics --domain=<binding|drift|vector|snapshot|federated|backfill|metadata|engine>` filter by domain (prefix-based on counter name).

P1 (should, this change):

- **REQ-38** — `flow metrics --prometheus` Prometheus textfile exposition format (`# HELP`/`# TYPE`/`metric{label="value"} N`).
- **REQ-39** — `flow metrics --percentile=<p>` and `--aggregations` derive P50/P95/P99 from `*_latency_ms` / `*_duration_seconds` events; mean/stddev for gauge counters.

P2 (could, v1.1 follow-up):

- **REQ-40** — `flow metrics --label <key>=<value>` predicate filter on `fields` labels.
- **REQ-41** — `flow metrics --threshold <name>:<op>:<N>` exit-code-based alerting for CI/CD.
- **REQ-42** — `engine_*` counters for engine internals (CLI invocation, daemon queue, embedding provider latency).
- **REQ-43** — `--project=<key>` filter + `project=<key>` field on federated-aware events.
- **REQ-44** — `FLOW_METRICS_MAX_BYTES` / `FLOW_METRICS_MAX_AGE_DAYS` rotation env vars.

If scope allows, bundle REQ-44 into REQ-35 (small enough to merge).

### C.5 Dependencies on prior changes

- **graph-snapshots (change #5, IN PROGRESS)** — REQ-35 summary view MUST include the 4 `snapshot_*` counters once change #5 lands (currently 1 snapshot counter is partial). Coordinate with graph-snapshots archive: snapshot counters must be in `SNAPSHOT_COUNTER_NAMES` catalog before change #6 apply starts.
- **cross-project-federation (change #4)** — REQ-43 federation-aware depends on this. May defer if scope grows.
- **vector-semantic-search (change #3)** — REQ-39 percentiles derive from `vector_search_latency_ms` and `inspect_render_ms`. No new latency counters needed.
- **decision-reality-drift (change #2)** — REQ-35 summary view MUST include the 8 `drift_*` counters. No new counters needed.
- **decision-code-linking (change #1)** — REQ-35 summary view MUST include the 4 `suggest_*` + 2 `backfill_*` + 2 `inspect_*` counters. No new counters needed.

**Coordination requirement**: change #5 archive should complete BEFORE change #6 apply starts (so the 4 `snapshot_*` counters are stable and documented in `openspec/specs/observability/spec.md` per cross-project-federation archive-report #61).

---

## D. Open Questions

10 questions for the design phase. Each is labeled with which prior change it relates to.

### D.1 Should `flow metrics` default-output change?

Today `flow metrics` outputs `<name>  <count>` (text table) by default. With REQ-35 adding `--summary`, the question is: does the default become summary (richer) or stay flat (no breakage)?

**Relates to**: REQ-8 close (change #1); the original REQ-8 close shipped the text table.

**Design needs**: Default-output stability vs new-default ergonomics. Recommend: keep flat default; `--summary` opt-in.

### D.2 Prometheus exposition: which metric types per counter?

Prometheus has 4 types: `counter`, `gauge`, `histogram`, `summary`. The flow metrics have `_total` (counter), `_ms` / `_seconds` (timing/histogram), and bare (gauge). Does the Prometheus exporter auto-derive types from suffix, or does it require an explicit type map?

**Relates to**: REQ-22 (vector), REQ-26 (federated), REQ-12 (drift).

**Design needs**: Type-derivation rule + manual override for ambiguous cases (e.g. `vector_index_size_observations` is a gauge by naming convention).

### D.3 Domain categorization: by name prefix OR explicit `domain` field?

Today domains are implicit (prefix-based). REQ-37 `--domain` could:
- **(a)** Use prefix matching: `--domain=drift` matches `drift_*`.
- **(b)** Add an explicit `domain` field to every event (requires changing every helper signature).
- **(c)** Maintain a `DOMAIN_BY_PREFIX` lookup table in `observability.py` (declarative; no helper signature changes).

**Relates to**: REQ-22/26 catalog pattern.

**Design needs**: Pick (a) or (c); (b) is invasive and likely deferred.

### D.4 Aggregation: at increment time (sliding window) OR at query time (over full log)?

REQ-39 `--percentile` could:
- **(a)** Compute percentiles at query time by reading all JSONL events for the counter and sorting (O(N log N) per query).
- **(b)** Maintain a sliding-window percentile sketch (t-digest or HDR histogram) in memory and flush to JSONL periodically.

**Relates to**: REQ-22 latency_ms counter, REQ-39 new REQ.

**Design needs**: (a) is simpler but slower for large logs; (b) requires in-memory state. Recommend (a) for v1 (matches the "best-effort" sink ethos).

### D.5 Rotation policy: size-based, age-based, or both?

REQ-44 rotation could trigger on:
- **(a)** `FLOW_METRICS_MAX_BYTES` — rename to `metrics.1.jsonl.gz` when current file exceeds N bytes.
- **(b)** `FLOW_METRICS_MAX_AGE_DAYS` — rename when oldest event is older than N days.
- **(c)** Both, with rotation on whichever fires first.

**Relates to**: Graph-snapshots (REQ-34 `flow snapshot prune` precedent uses similar retention pattern).

**Design needs**: Pick one for v1; defer the other to v1.1.

### D.6 Backwards compatibility: keep flat text default OR change default to summary?

Today `flow metrics` outputs `<name>  <count>`. Adding `--summary` is opt-in. The question is whether the FLAT output should become `--format=text` and the default become `--format=summary`.

**Relates to**: REQ-8 close.

**Design needs**: Default stability — recommend keep flat default; explicit `--summary` opt-in.

### D.7 Dashboard format: text-based (like `flow drift`) OR interactive (rich/tui)?

REQ-35 summary view could:
- **(a)** Text table (like `flow drift`, `flow status`) — adds a dependency only on `click.echo`.
- **(b)** Rich library (if available) — colored output, panels.
- **(c)** Interactive TUI (textual or prompt_toolkit) — overkill for a one-shot read.

**Relates to**: All CLI surfaces.

**Design needs**: Pick (a) for consistency with `flow drift`/`flow status`; defer (b) and (c).

### D.8 Engine metrics: which surfaces get instrumented?

REQ-42 adds `engine_*` counters. Candidates:
- CLI startup time (per-command)
- Daemon queue depth (gauge from `flow watch`)
- Embedding provider latency (extends REQ-22 `vector_search_latency_ms`?)
- Snapshot create/diff/rollback duration (extends graph-snapshots T1.7)

**Relates to**: All 5 prior changes.

**Design needs**: Pick 2-3 surfaces for v1; defer the rest. Recommend CLI startup + embedding provider for v1.

### D.9 Where does change #6 land — extend `observability.py` OR new module?

The `observability.py` is 413 LOC today; adding 5 REQs + helpers + CLI flags could grow it to ~700-800 LOC. The question is whether to:
- **(a)** Extend in-place (single file, single import surface).
- **(b)** Split into `observability.py` (sink) + `observability_query.py` (read-side helpers + summary).

**Relates to**: The split is purely architectural; no behavior change.

**Design needs**: Pick based on team preference. Recommend (a) for v1 (smaller surface); revisit if observability.py exceeds 800 LOC.

### D.10 Should `openspec/specs/observability/spec.md` be created in change #6 (resolves the cross-project-federation archive-report #61 deferral)?

Today the project has `openspec/changes/` but NO `openspec/specs/` baseline (verified across archive-reports #119, #136, #154). The cross-project-federation archive-report #61 explicitly defers "Spec counter catalog in `openspec/specs/observability/spec.md` for the 3 new `federated_*` counters" to a future observability change. Change #6 is that change.

**Relates to**: Cross-project-federation #61, vector-semantic-search #154.

**Design needs**: Confirm scope includes creating `openspec/specs/observability/spec.md` with the full catalog (vector + federated + drift + snapshot + binding + backfill + metadata + engine). This is a one-time bootstrap; subsequent changes add to the catalog.

---

## E. Files to Touch

### E.1 Production files

| File | LOC delta | Type | Notes |
|---|---|---|---|
| `src/flow_engineering/observability.py` | +200 | modify | new helpers (`read_events_since`, `read_events_by_domain`, `summarize`, `percentile`, `prometheus_exposition`); extend `read_all` to accept filters; bump module docstring |
| `src/flow_engineering/cli.py` | +200 | modify | `flow metrics` extended with 5 flags (`--summary`, `--since`, `--until`, `--domain`, `--top`, `--percentile`, `--aggregations`, `--prometheus`, `--format`); new flag validation; text-table vs summary-table dispatch |
| `openspec/specs/observability/spec.md` | +200 | **NEW** | capability spec cataloging ALL counter names (vector + federated + drift + snapshot + binding + backfill + metadata + engine); resolves #61 federation deferral |
| `CHANGELOG.md` | +25 | modify | v0.7.0 entry |
| `pyproject.toml` | +1 | modify | version bump `0.6.0` → `0.7.0` (or whatever graph-snapshots archives at) |

**Production total**: ~626 LOC delta (forecast ~626; realistic ×6 = ~3 750).

### E.2 Test files

| File | LOC delta | Type | Notes |
|---|---|---|---|
| `tests/unit/test_observability.py` | +200 | modify | extend with `read_events_since`, `read_events_by_domain`, `summarize`, `percentile`, `prometheus_exposition` unit tests |
| `tests/unit/test_cli_metrics.py` | +400 | **NEW** | full CLI surface coverage for `flow metrics` (text + JSON + summary + window + domain + top + percentile + prometheus) |
| `tests/bdd/req35_metrics_summary.feature` | +60 | **NEW** | 3 scenarios: default summary, with `--since`, with `--domain` + `--top` |
| `tests/bdd/req36_metrics_window.feature` | +40 | **NEW** | 2 scenarios: `--since` filters, `--until` excludes |
| `tests/bdd/req37_metrics_domain.feature` | +40 | **NEW** | 2 scenarios: `--domain=drift` filters, `--domain=federated` filters |
| `tests/bdd/req38_metrics_prometheus.feature` | +40 | **NEW** | 2 scenarios: `--prometheus` emits correct exposition format |
| `tests/bdd/req39_metrics_percentile.feature` | +40 | **NEW** | 2 scenarios: P50/P95 from `vector_search_latency_ms`, mean/stddev from gauge |
| `tests/bdd/test_observability_steps.py` | +200 | **NEW** | pytest-bdd step glue shared across the 5 BDD features |
| `tests/unit/test_observability_summary.py` | +150 | **NEW** | unit-level coverage for `summarize` helper (independent of CLI) |

**Test total**: ~1 170 LOC (forecast; realistic ×6 = ~7 020).

### E.3 Runtime-only files (NOT in repo)

| File | LOC delta | Notes |
|---|---|---|
| `~/.config/opencode/skills/sdd-propose/SKILL.md` | +20 | `## Observability hook` section: counter catalog + summary/dashboard reference |
| `~/.config/opencode/skills/sdd-design/SKILL.md` | +20 | same |
| `~/.config/opencode/skills/sdd-tasks/SKILL.md` | +20 | same |
| `~/.config/opencode/skills/sdd-apply/SKILL.md` | +20 | same |
| `~/.config/opencode/skills/sdd-verify/SKILL.md` | +40 | `Step 6b` sub-step: run `flow metrics summary` and surface anomalies |
| `~/.config/opencode/skills/sdd-archive/SKILL.md` | +20 | same |

**Runtime total**: ~140 LOC.

### E.4 Grand total

| Category | Forecast | Realistic ×6 |
|---|---|---|
| Production | ~626 LOC | ~3 750 LOC |
| Test | ~1 170 LOC | ~7 020 LOC |
| Runtime (SKILL.md) | ~140 LOC | (no multiplier) |
| **Grand total** | **~1 936 LOC** | **~10 910 LOC** |

Per-delegation batch ceiling (Engram #112, ≤6 tasks OR ≤150 LOC prod per delegation, ~15 min runtime): production work needs **~5 delegations** (626 / 150 = 4.2; round up). Test work needs **~8 delegations** (1 170 / 150 = 7.8). Total **~13 delegations** spread across 2 PRs (PR#1 = ~7 delegations, PR#2 = ~6 delegations). At ~15 min/delegation: ~3.5 hours total.

### E.5 Out-of-scope reminders (NOT in change #6)

These follow-ups land in v1.1 or named changes:

- **Per-project rotation** (REQ-44 P2) — defer to v1.1
- **Label-based query** (REQ-40 P2) — defer to v1.1
- **Threshold alerting** (REQ-41 P2) — defer to a "ci-gating" change
- **Engine internals counters** (REQ-42 P2) — defer to "engine-instrumentation" change
- **Federation-aware events** (REQ-43 P2) — defer to "federated-observability" change
- **Vector quantization** — already deferred (vector-semantic-search archive)
- **Async embed-on-save** — already deferred (vector-semantic-search archive)
- **Snapshot export/import** — already deferred (graph-snapshots archive)
- **Per-project snapshots** — already deferred (graph-snapshots archive)
- **Auto-daily snapshot triggers** — already deferred (graph-snapshots archive)
- **Encrypted snapshots at rest** — already deferred (graph-snapshots archive)

---

## F. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | graph-snapshots (change #5) does not land before change #6 apply starts → snapshot counters unstable | HIGH | Coordinate with graph-snapshots archive; change #6 PROPOSE waits for change #5 ARCHIVE |
| 2 | PR#1 cumulative realistic ~4 500 LOC > 400-line review budget | MEDIUM | Per-commit work-unit splits per `work-unit-commits` skill; 5-6 commits each ≤400 LOC |
| 3 | JSONL rotation (REQ-44) has cross-cutting impact on `read_all` (must read siblings) | MEDIUM | Defer REQ-44 to v1.1; v1 ships only summary/window/domain |
| 4 | Federation-aware events (REQ-43) requires changing every helper signature | MEDIUM | Defer REQ-43 to "federated-observability" follow-up; keep events project-less for v1 |
| 5 | Prometheus exposition type-derivation ambiguous for counters like `vector_index_size_observations` (gauge by suffix but used like a counter in dashboards) | LOW | Explicit `METRIC_TYPE_OVERRIDES` map in observability.py |
| 6 | `--since`/`--until` parsing must mirror `flow drift --since` ISO 8601 behavior (REQ-10) | LOW | Reuse `_parse_since()` from `cli.py:1020` (already factored) |
| 7 | The CHANGELOG `drift_invoked_total` typo (W7 from verify #135) was already resolved; no drift to address here | INFO | — |
| 8 | BDD step def file growth (decision-code-linking S3 precedent: 5-6× forecast) likely applies | LOW | Forecast ×6 multiplier baked in (~10 910 realistic) |
| 9 | The project has NO `openspec/specs/` baseline; creating `openspec/specs/observability/spec.md` is precedent-setting | LOW | Confirmed by archive-reports #119, #136, #154; safe to bootstrap |
| 10 | `flow metrics --json` output format may break downstream consumers if changed | LOW | Keep `--json` flat dict; add `--format=json-detailed` for raw events; no breakage |

---

## G. Recommendation Summary

**For the orchestrator**:

1. **Scope**: 5 P0/P1 REQs (REQ-35, REQ-36, REQ-37, REQ-38, REQ-39). Defer 5 P2 REQs to v1.1.
2. **Forecast**: ~1 936 LOC total; ~10 910 LOC realistic ×6 TDD multiplier.
3. **PR split**: 2 chained PRs (PR#1: foundation+summary+slicing+window; PR#2: export+aggregation).
4. **Coordination**: Wait for graph-snapshots (change #5) to ARCHIVE before starting change #6 apply.
5. **Next recommended phase**: `sdd-propose observability` (formal proposal with 5 REQs + approach matrix).
6. **Side benefit**: Change #6 bootstraps `openspec/specs/observability/spec.md` (resolves cross-project-federation archive-report #61 deferral).

**Key dependencies resolved**:

- ✓ Change #1 (decision-code-linking) — 8 counters stable
- ✓ Change #2 (decision-reality-drift) — 8 counters stable
- ✓ Change #3 (vector-semantic-search) — 6 counters stable
- ✓ Change #4 (cross-project-federation) — 3 counters stable
- ⏳ Change #5 (graph-snapshots) — 4 counters land in batch C (T1.7); MUST complete before change #6 apply
- ❌ Change #7 (prompt-registry) — unrelated

---

## H. Structured Metadata

- **total_gaps_identified:** 10 (5 P0/P1, 5 P2)
- **recommended_reqs:** 5 (REQ-35, REQ-36, REQ-37, REQ-38, REQ-39)
- **deferred_reqs:** 5 (REQ-40, REQ-41, REQ-42, REQ-43, REQ-44)
- **forecast_loc_production:** ~626
- **forecast_loc_test:** ~1 170
- **forecast_loc_runtime_skill:** ~140
- **forecast_loc_grand_total:** ~1 936
- **forecast_loc_realistic_x6:** ~10 910
- **pr_split:** 2 chained PRs (PR#1: summary+slicing+window; PR#2: export+aggregation)
- **bdd_feature_files_new:** 5
- **bdd_scenarios_new:** 11
- **counter_names_total_in_code_today:** 27
- **counter_names_after_graph_snapshots:** 31
- **catalog_files_today:** 2 (VECTOR, FEDERATED)
- **catalog_files_after_graph_snapshots:** 3 (VECTOR, FEDERATED, SNAPSHOT)
- **counter_names_in_no_catalog:** 19 (REQ-8, REQ-12, REQ-13, REQ-24 sprawl)
- **observation_id:** (TBD; persisted to Engram on return)
- **topic_key:** `sdd/observability/explore`
- **type:** architecture
- **scope:** project
- **capture_prompt:** false (automated artifact)
- **next_recommended:** `sdd-propose observability` (5 REQs + approach matrix)

---

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_module",
      "label": "observability.py (413 LOC, JSONL sink + 3 record helpers + 2 catalogs)",
      "file": "src/flow_engineering/observability.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_increment",
      "label": "increment(name, **fields) — primary sink API",
      "file": "src/flow_engineering/observability.py",
      "line": 128,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_read_all",
      "label": "read_all(path) — JSONL reader used by flow metrics (NO filter support)",
      "file": "src/flow_engineering/observability.py",
      "line": 159,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_vector_counter_names",
      "label": "VECTOR_COUNTER_NAMES catalog (REQ-22, 6 names)",
      "file": "src/flow_engineering/observability.py",
      "line": 70,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_federated_counter_names",
      "label": "FEDERATED_COUNTER_NAMES catalog (REQ-26, 3 names)",
      "file": "src/flow_engineering/observability.py",
      "line": 89,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_drift_summary",
      "label": "record_drift_summary(report) (REQ-12, 8 drift counters)",
      "file": "src/flow_engineering/observability.py",
      "line": 273,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_vector_summary",
      "label": "record_vector_summary(...) (REQ-22, 6 vector counters)",
      "file": "src/flow_engineering/observability.py",
      "line": 319,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_federated_summary",
      "label": "record_federated_summary(...) (REQ-26, 3 federated counters)",
      "file": "src/flow_engineering/observability.py",
      "line": 377,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_metrics_command",
      "label": "flow metrics subcommand (text or --json flat dict; no filter)",
      "file": "src/flow_engineering/cli.py",
      "line": 975,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_snapshot_manager_rollback_counter",
      "label": "_record_rollback_event emits snapshot_rollback_total directly (snapshot catalog T1.7 batch C pending)",
      "file": "src/flow_engineering/snapshot_manager.py",
      "line": 826,
      "confidence": 0.85,
      "source": "manual"
    }
  ]
}