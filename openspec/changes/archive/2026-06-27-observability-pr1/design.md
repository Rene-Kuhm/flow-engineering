<!-- design.md: change #6 observability. Source: manual. -->
# Design: observability

> Mirror of Engram `sdd/observability/design` (topic_key upsert after file
> creation). Reference format mirrors
> [`openspec/changes/archive/2026-06-27-graph-snapshots/design.md`](../archive/2026-06-27-graph-snapshots/design.md)
> (D1–D13) extended to **D1–D12** for observability-specific concerns. All 10
> open questions from proposal #194 are resolved below. The Engram `code_refs`
> block is appended at file end so `flow inspect <change>` can render the
> binding surface.

```yaml
status: success
confidence: high
open_questions_resolved: 10/10
architecture_decisions: 12  # D1..D12
file_created: C:\dev\proyects\flow-engineering\openspec\changes\observability\design.md
next_recommended: sdd-tasks observability
```

## Technical Approach

`observability` adds a **read-side** aggregation layer on top of the existing
JSONL counter sink that change #1 (REQ-8, `decision-code-linking` v0.2.0)
shipped. **Write-side is unchanged**: `observability.increment()`, `read_all()`,
and the 5 record helpers (`record_backfill_coverage`, `record_drift_summary`,
`record_vector_summary`, `record_federated_summary`, `record_snapshot_event`)
collectively emit **31 counter names** across 7 implicit domains into
`~/.flow-engineering/metrics.jsonl` — verified via `observability.py:85,104,124`
catalogs. The `flow metrics` CLI today is a 13-line flat dump at `cli.py:977`
with `--json` and **no** time-window, no domain slice, no aggregation, no
export, no dashboard. This change ships the read-side: a `flow metrics summary`
text dashboard, ISO-8601 + rolling time-window filters, prefix-based domain
slicing, Prometheus textfile export, and percentile aggregation. **All
additive, all non-breaking**, all driven by the existing JSONL sink.

Five cooperating pieces (matches proposal §"Approach A pieces 1-5"):

1. **Five read-side helpers** (NEW in `observability.py`, PR#1 + PR#2):
   `read_events_since`, `read_events_by_domain`, `summarize`, `percentile`,
   `aggregate`, `prometheus_exposition`. All pure functions, all return
   `list[dict]` or structured dicts, all reuse `read_all()` for I/O.
2. **Two lookup tables** (NEW): `DOMAIN_BY_PREFIX` (PR#1) — maps
   `prefix → domain_name` for the 8 accepted `--domain` values; and
   `METRIC_TYPE_OVERRIDES` (PR#2) — escape hatch for ambiguous Prometheus
   type derivation (`{"vector_index_size_observations": "gauge"}`).
3. **CLI surface** — extend the existing `flow metrics` command at
   `cli.py:977` with 10 new flags (`--summary`, `--since`, `--until`,
   `--window`, `--domain`, `--top`, `--percentile`, `--aggregations`,
   `--field`, `--prometheus`, `--out`, `--format`). Flat text default
   stays byte-identical to v0.6.0 (REQ-8 close invariant); new
   functionality is opt-in via flags.
4. **Spec catalog bootstrap** — NEW `openspec/specs/observability/spec.md`
   catalogs ALL 31 counter names across 7 domains with helper provenance.
   Resolves `cross-project-federation` archive-report #61 explicit deferral.
   Also bootstraps the project's `openspec/specs/` baseline (today empty
   per `glob openspec/specs/**`).
5. **Atomic export contract** — `--out=<path>` writes via `tempfile` +
   `Path.replace` (mirrors `flow projects alias` precedent from
   `cross-project-federation` D8). Partial writes NEVER leave corrupt
   files on disk.

Architecture seams respected (verified):
- `observability.read_all(path)` signature unchanged (REQ-8 close contract).
- All 5 record helpers byte-identical (REQ-8 / REQ-12 / REQ-22 / REQ-26 /
  REQ-28..34 invariants).
- `_summarize_metrics()` at `cli.py:960` becomes a thin wrapper that calls
  `observability.summarize(events)` (REFACTOR — preserves `TestMetricsCommand`
  byte-identical output for the 3 existing tests).
- `_parse_since()` at `cli.py:1022` reused verbatim for `--since`/`--until`
  ISO 8601 parsing (REQ-10/11 drift parser precedent).

## Architecture Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| **D1** | Module layout: where do the new query/read classes live? | **Single file `src/flow_engineering/observability.py`** — extend the existing module with 5 new pure functions (`read_events_since`, `read_events_by_domain`, `summarize`, `percentile`, `aggregate`, `prometheus_exposition`) + 2 lookup tables (`DOMAIN_BY_PREFIX`, `METRIC_TYPE_OVERRIDES`). NO new package, NO new file. The 5 record helpers and 3 counter catalogs already live here; new read-side code goes beside them. Class-based API is REJECTED for v1. | The existing observability surface is single-file (`observability.py`, 475 LOC). Splitting into `observability_query.py` would force 1-direction imports and split conceptually-related code across files. The proposal's "5 cooperating pieces" are 5 **functions** (pure data transforms), not 5 classes — a class would be ceremony without payoff at this scale. Counter catalogs (`VECTOR_COUNTER_NAMES`, `FEDERATED_COUNTER_NAMES`, `SNAPSHOT_COUNTER_NAMES`) live alongside the new `DOMAIN_BY_PREFIX` so all "what counters exist and how are they grouped" knowledge is co-located. The v2 boundary (REQ-43 federation-aware events) MAY introduce a class, but YAGNI for v1. |
| **D2** | Metrics file format + rotation policy | **Keep JSONL append-only**, NO rotation in v1. REQ-44 (rotation via `FLOW_METRICS_MAX_BYTES` / `FLOW_METRICS_MAX_AGE_DAYS`) is **explicitly deferred to v1.1**. The JSONL event shape `{name, fields, ts}` is unchanged. The new read-side helpers filter in-memory after `read_all()` returns the full list — no schema migration, no I/O path changes. | Rotation cross-cuts `read_all()` and 6 existing call sites (`test_cli_inspect.py:33`, `test_cli_drift.py:65`, `test_cli_search_semantic.py:38`, etc.) — invasive for v1, low value at the 31-counter × ~150 KB realistic scale (proposal §"Carry-forwards" risk #3). In-memory filter on ~150 KB is <1ms; on 5 MB it's <50ms — well below the human-perceptible threshold. Rotation deferred cleanly per the v1.1 follow-up path. |
| **D3** | Query API surface: class-based, function-based, or both? | **Function-based ONLY for v1.** Six pure functions: `read_events_since(path, since_iso, until_iso=None)`, `read_events_by_domain(path, domain)`, `summarize(events)`, `percentile(events, pct, field="elapsed_ms")`, `aggregate(events, field="value")`, `prometheus_exposition(events, catalog=None)`. No class wrapper. | Pure functions compose naturally (`read_all() → read_events_since() → summarize()`) and are trivially testable (no mocking). A `MetricsReader` class adds state (cached events, current filters) that nobody asked for at v1 scale (~150 KB). The existing 3 record helpers are all functions (`record_drift_summary`, `record_vector_summary`, etc.) — function-first is the project convention. The class path remains open if v2 introduces filter state machines (REQ-43 federation-aware events). |
| **D4** | Time window semantics (resolves OQ-5) | **Both `--since=<iso>` (absolute) AND `--window=<1h\|24h\|7d>` (rolling shorthand)**. The `--window` value is a strict rolling window: `1h` = `now − 60 minutes`, `24h` = `now − 24 hours`, `7d` = `now − 7 days` — **NOT** calendar-aligned (`1h` ≠ "since the top of the hour"). Case-insensitive parse. The rolling shorthand is byte-equivalent to `--since=<computed-iso>` — both flow into the same in-memory filter pipeline. | Rolling windows match the operator mental model ("show me the last hour") and avoid the calendar-boundary edge case (timezone confusion, off-by-one when DST shifts). Absolute ISO 8601 stays for scripted / CI use. The `_parse_since()` parser at `cli.py:1022` is reused verbatim for absolute ISO; a new `_parse_window(value) → timedelta` helper covers the rolling shorthand. Calendar-day boundaries (`--since=today` meaning `00:00 UTC`) explicitly deferred. |
| **D5** | Domain slice representation (resolves OQ-3) | **Enum-like string, lowercase, case-sensitive.** Accepted values: `binding`, `backfill`, `drift`, `vector`, `federated`, `snapshot`, `metadata`, `engine`. Stored as a `list[str]` constant `ACCEPTED_DOMAINS` exported from `observability.py`. Lookups via `DOMAIN_BY_PREFIX: dict[str, str]` table mapping each `prefix → domain_name`. The `engine` domain is RESERVED (no `engine_*` counters in v1; REQ-42 deferred to v1.1) — accepting the value lets `--domain=engine` succeed with "no events matched" rather than erroring. | String-based domains match the existing catalog style (`VECTOR_COUNTER_NAMES`, etc.). Case-sensitive matching is simpler, deterministic, and the REQ-37 spec already lists the values verbatim — script-friendly. The prefix table is a `dict[str, str]` for O(1) lookup; prefixes are validated against the table when the module loads (test: `DOMAIN_BY_PREFIX` covers every name in `VECTOR_COUNTER_NAMES` + `FEDERATED_COUNTER_NAMES` + `SNAPSHOT_COUNTER_NAMES` + the 14 REQ-8/REQ-12/REQ-13/REQ-24 names — 31 total). |
| **D6** | Prometheus textfile format (resolves OQ-2) | **`# HELP` + `# TYPE` + `<name>{labels} <value>`** per counter. Type derivation, applied IN ORDER: (1) `METRIC_TYPE_OVERRIDES[name]` if present (escape hatch — v1 has zero overrides but the map is the forward-compatible hook); (2) suffix-based `_total` → `counter`; (3) `_ms` or `_seconds` → `summary` (single quantile, NOT histogram — bucket math deferred); (4) bare name → `gauge`. Latency/duration events (`_latency_ms`, `_duration_seconds`) emit as **`summary`** in v1 with a `quantile="0.5"`/`"0.95"`/`"0.99"` label pair emitted by REQ-39's `--percentile` flag. Histogram type with buckets explicitly deferred to v1.1. | `_total` suffix convention is established in REQ-8 / REQ-22 / REQ-26 (`vector_search_invoked_total`, `federated_search_invoked_total`, `snapshot_create_total`). Prometheus `summary` type matches REQ-39's percentile goal without needing bucket math. The override map is a cheap forward-compatible hook — when REQ-42 adds `engine_*` counters with non-suffix types, no helper signature changes. Round-trip test: `prometheus_client.parser.text_string_to_metric_families(output)` parses cleanly (test-only dep, not a runtime dep). |
| **D7** | Percentile algorithm (resolves OQ-4) | **Query-time sort + bisect via `statistics.quantiles(data, n=100, method="inclusive")`** from stdlib. O(N log N) per query. Default field is `elapsed_ms` (matches `vector_search_latency_ms` events from `record_vector_summary`); `--field=<name>` switches to `value` or any event-fields key. Counters with <2 numeric samples emit `"insufficient data"` on stdout AND a stderr warning JSON `{warning, counter, count}` (does NOT cause non-zero exit — warning, not error). | Query-time matches the "best-effort sink" ethos — no in-memory sketch, no incremental state, no consistency between `flow metrics` invocations. ~1 000 events sort in <1ms; 10 000 events in <10ms — well under the human-perceptible threshold. `statistics.quantiles` is stdlib (Python 3.8+), no numpy, no new runtime dep. The "insufficient data" warning shape mirrors the JSON-error pattern from `_parse_since()` (REQ-10/11). Sliding t-digest / HDR histogram explicitly deferred to v1.1 if performance becomes a real issue (deferral covered by REQ-44 follow-up pattern). |
| **D8** | Empty metrics file handling (resolves OQ-1) | **Default-empty, NOT error.** When `read_all()` returns `[]` (file missing OR exists but empty OR all events filtered out), `flow metrics` (flat default) emits `(no metrics recorded)` and exits 0 — byte-identical to today. `flow metrics summary` (REQ-35) emits the same single line; `flow metrics --json` emits `{}`; `flow metrics --prometheus` emits `# EOF` (Prometheus convention for empty textfile). | The existing `TestMetricsCommand::test_metrics_empty_sink` test at `test_cli_inspect.py:296` already asserts `result.output` contains `"no"` and exits 0 — REQ-35 must preserve this contract. Default-empty matches `graph-snapshots` D6 dry-run default + `flow projects backfill --dry-run` precedent (no surprises for empty input). Erroring on empty would break CI scripts that pipe `flow metrics --json` into `jq` and expect an empty dict, not a non-zero exit. |
| **D9** | Exit codes | **Three non-zero codes** for the new surface, plus `0` for success: `2` = usage error (invalid `--domain`, invalid `--format`, invalid `--window`); `3` = data error (invalid `--since` ISO 8601, invalid `--percentile`, malformed JSONL line beyond the existing best-effort skip); `4` = I/O error (`--out=<path>` write failure, permission denied, disk full). Empty / no-matches is exit `0`. All error paths emit **JSON to stderr** (not stdout) in the shape `{"error": "<kind>", ...}` so scripts can parse without inspecting human prose. | JSON-to-stderr + non-zero exit mirrors the `_parse_since()` REQ-10/11 precedent (`cli.py:642-647`) and `flow projects backfill --confirm` precedent (cross-project-federation D3). Code `2` for usage matches the universal convention (Click default); `3` for data follows the `git`/`curl` convention; `4` for I/O matches the `snapshot rollback` exit codes from `graph-snapshots`. Stdout stays clean for piping (`flow metrics --json \| jq`). The `flow metrics --out=…` write failure path is the ONLY v1 case that produces code `4`; other I/O errors (read failures) are absorbed by `read_all()`'s existing best-effort skip. |
| **D10** | Atomic write for export | **`tempfile.NamedTemporaryFile` in the same parent dir + `os.replace` + cleanup on failure.** Pattern: (1) resolve `--out` to an absolute `Path`; (2) `Path.mkdir(parents=True, exist_ok=True)` for parent; (3) write the Prometheus exposition to a `NamedTemporaryFile(delete=False, dir=parent, suffix=".prom.tmp")`; (4) `os.replace(tmp, target)` (atomic on POSIX and Windows when both paths are on the same filesystem); (5) on any exception during (3-4), `os.unlink(tmp)` if it exists, then re-raise as exit-code-4 error. Parent-dir resolution ensures `os.replace` is atomic (same filesystem). | `tempfile + os.replace` is the established atomic-write contract in the project (`project_aliases.save_aliases` from cross-project-federation D8, `snapshot envelope` from graph-snapshots D11). Pattern guarantees: (a) a partial write never produces a corrupted file (the rename is atomic), (b) the user's existing `metrics.prom` is never half-overwritten, (c) the tmp file is cleaned up on any error path (no orphans). Same-filesystem atomicity is satisfied by constructing the `NamedTemporaryFile` in the target's parent dir (not `tempfile.gettempdir()` which may be on a different mount). |
| **D11** | `openspec/specs/` observability spec bootstrap | **YES — bootstrap `openspec/specs/observability/spec.md` in PR#1.** The new spec catalogs ALL 31 counter names (after graph-snapshots archive) across 7 active domains + 1 reserved (`engine`), with helper provenance (which `record_*` helper emits which counter) and the JSONL event shape. Marks as `v1.0`. Pattern: kebab-case folder per capability, `spec.md` inside, mirrors the sdd-propose skill template "New Capabilities → each becomes `openspec/specs/<name>/spec.md`". Resolves `cross-project-federation` archive-report #61. | `glob openspec/specs/**` is empty today — change #6 is the FIRST capability spec, setting the convention. The cross-project-federation archive-report explicitly defers the spec catalog to a future observability change: this IS that change. The spec is INFORMATIONAL (catalog + BDD scenarios); runtime code in `observability.py` does not import it. Once `openspec/specs/observability/spec.md` exists, follow-on changes (engine-instrumentation, federated-observability) add specs to the same baseline at `openspec/specs/<change-name>/spec.md`. |
| **D12** | Cross-PR consistency between PR#1 and PR#2 | **Shared `observability.py` module + shared BDD glue file + shared test fixture helpers.** Both PRs edit the same `observability.py`; PR#1 lands 5 read-side helpers + `DOMAIN_BY_PREFIX`; PR#2 lands `aggregate()`, `percentile()`, `prometheus_exposition()` + `METRIC_TYPE_OVERRIDES`. PR#1 BDD glue lives in `tests/bdd/test_observability_steps.py`; PR#2 extends the SAME file with 2 new step groups (Prometheus + percentile). Both PRs share `tests/unit/test_cli_metrics.py` (PR#1 lands the base; PR#2 extends it for `--prometheus`/`--percentile`/`--aggregations`). Shared `tests/fixtures/metrics/` JSONL fixture (15 events covering all 7 active domains) committed in PR#1 and consumed by PR#2 tests. | Mirrors `cross-project-federation` chained-PR pattern (PR#1 InMemoryBackend, PR#2 production SQLite integration — shared test fixtures, shared type definitions). PR#2 cherry-picks ONLY additive changes on top of PR#1's HEAD; merge-base is PR#1's merge commit. The shared BDD glue file prevents step-def duplication (5 BDD features × ~10 scenarios each = ~50 step definitions; per-REQ step files would push >600 LOC). PR#1 carries the `openspec/specs/observability/spec.md` baseline so PR#2's `METRIC_TYPE_OVERRIDES` change can be documented as a delta against the v1.0 catalog. |

## Data Flow

### Summary view (REQ-35)

```
$ flow metrics summary [--since=<iso>] [--until=<iso>] [--domain=<d>] [--top=<N>]
   │
   ▼
@click metrics(...) with summary_flag=True         # cli.py:980 (mod)
   │
   ├─► since, until = _resolve_window(since_iso, until_iso, window)
   │       │
   │       └─► if window: rolling_since = now - timedelta(window)
   │       else:         rolling_since = since_iso
   │
   ▼
events = observability.read_all()                  # observability.py:200 (unchanged)
   │
   ▼
events = observability.read_events_since(events,   # NEW: in-memory filter
                                        since, until)
events = observability.read_events_by_domain(events, domain)  # NEW
   │
   ▼
summary = observability.summarize(events)          # NEW: collapse
   │
   ├─► for each name: {count, domain, first_seen, last_seen}
   │       domain = DOMAIN_BY_PREFIX[<longest matching prefix>]
   │       (or "unknown" if no prefix matches — W23 dual-name history)
   │
   ▼
render_summary(summary, top=N)                     # NEW: render text table
   │
   ▼
click.echo(text)                                  # stdout: text dashboard
```

### Time-window filter (REQ-36)

```
$ flow metrics --since=<iso> [--until=<iso>] [--window=<1h|24h|7d>]
   │
   ▼
@click metrics(...) with since=<iso>, until=<iso>, window=<window>
   │
   ├─► try:
   │       since_dt = _parse_since(since) or _parse_window(window)
   │                       # cli.py:1022 (REUSED)
   │   except ValueError as exc:
   │       click.echo(json.dumps({error: "invalid --since value", value: since,
   │                              hint: "..."}), err=True)
   │       sys.exit(3)                               # D9 exit code
   │
   ▼
since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
events = observability.read_all()
events = observability.read_events_since(events, since_iso, until_iso)
   │
   ▼
_summary = observability.summarize(events)          # same as REQ-35 path
```

### Prometheus export (REQ-38)

```
$ flow metrics --prometheus [--out=<path>]
   │
   ▼
@click metrics(...) with prometheus_flag=True, out=<path>
   │
   ├─► events = <filtered events via REQ-35/36/37 pipeline>
   │
   ▼
text = observability.prometheus_exposition(events)  # NEW
   │
   ├─► for each counter name:
   │       type = METRIC_TYPE_OVERRIDES.get(name)        # D6 priority 1
   │              or ("counter" if name.endswith("_total")
   │                  else "summary" if name.endswith(("_ms", "_seconds"))
   │                  else "gauge")                       # D6 priority 2-4
   │       text += f"# HELP {name} {description}\n"
   │       text += f"# TYPE {name} {type}\n"
   │       for label_tuple in name_labels:
   │           text += f"{name}{{{labels}}} {value}\n"
   │
   ▼
if out:
    tmp = NamedTemporaryFile(delete=False, dir=out.parent,
                             suffix=".prom.tmp")
    tmp.write(text.encode("utf-8"))
    tmp.close()
    os.replace(tmp.name, out)                     # D10: atomic
    click.echo(json.dumps({wrote: str(out),
                           metric_lines: count,
                           bytes: len(text)}), err=True)
else:
    click.echo(text)                              # stdout
```

### Percentile + aggregations (REQ-39)

```
$ flow metrics --percentile=p95 [--field=elapsed_ms] [--aggregations]
   │
   ▼
@click metrics(...) with percentile="p95"|"p50"|"p99"|None,
                    aggregations=True|False, field="elapsed_ms"|...
   │
   ├─► if percentile not in (None, "p50", "p95", "p99"):
   │       click.echo(json.dumps({error: "invalid --percentile value",
   │                              value: percentile,
   │                              valid: ["p50", "p95", "p99"]}), err=True)
   │       sys.exit(3)                               # D9 exit code
   │
   ▼
events = observability.read_all()                  # or filtered by REQ-35/36/37
   │
   ▼
for counter_name, counter_events in groupby(events, key="name"):
    values = [ev["fields"][field] for ev in counter_events
              if field in ev.get("fields", {})
              and isinstance(ev["fields"][field], (int, float))]
    if percentile and len(values) >= 2:
        pct = observability.percentile(values, pct=int(percentile[1:]))
        text += f"{counter_name} {percentile}: {pct}\n"
    elif percentile:
        text += f"{counter_name} {percentile}: insufficient data\n"
        click.echo(json.dumps({warning: "not enough data points for percentile",
                               counter: counter_name, count: len(values)}), err=True)
    if aggregations and len(values) >= 1:
        agg = observability.aggregate(values)       # NEW: {count, mean, stddev, min, max}
        text += f"{counter_name} {agg}\n"
```

## File Changes

### New files (~200 LOC production + ~2 170 LOC test)

| File | LOC prod | LOC test | Purpose |
|---|---|---|---|
| `openspec/specs/observability/spec.md` | ~200 | — | Capability spec cataloging ALL 31 counter names across 7 active + 1 reserved domain with helper provenance. Bootstrap of `openspec/specs/` baseline. Resolves cross-project-federation archive-report #61. |
| `tests/unit/test_cli_metrics.py` | — | ~400 | Full CLI surface coverage for `flow metrics` — all 10 new flags + the existing 2 (text + JSON). Includes flag-matrix tests, error-path tests (invalid `--domain`/`--since`/`--window`/`--percentile`/`--format`), `--out` atomic-write test, empty-sink edge cases. |
| `tests/unit/test_observability_summary.py` | — | ~150 | Unit-level coverage for `summarize()` helper — `{count, domain, first_seen, last_seen}` shape, `unknown` bucket for W23 dual-name, sorting, empty input. |
| `tests/unit/test_observability_prometheus.py` | — | ~250 (PR#2) | Textfile format round-trip via `prometheus_client.parser.text_string_to_metric_families`. `_total` → counter, `_ms` → summary, bare → gauge. Label escaping (quotes, backslashes, newlines). Empty input → `# EOF`. |
| `tests/unit/test_observability_aggregate.py` | — | ~250 (PR#2) | Percentile correctness on synthetic 10..1000 dataset (asserts p95 ≈ 950.5). `aggregate()` `{count, mean, stddev, min, max}`. `--field` switching. Insufficient-data warning shape. |
| `tests/bdd/req35_metrics_summary.feature` | — | ~50 (PR#1) | 2 BDD scenarios (full summary, empty sink). |
| `tests/bdd/req36_metrics_window.feature` | — | ~50 (PR#1) | 2 BDD scenarios (`--since` absolute, `--window=1h` rolling). |
| `tests/bdd/req37_metrics_domain.feature` | — | ~50 (PR#1) | 2 BDD scenarios (`--domain=snapshot` filter, no `--domain` shows all). |
| `tests/bdd/req38_metrics_prometheus.feature` | — | ~60 (PR#2) | 3 BDD scenarios (stdout exposition, `--out` atomic write, `--window` composition). |
| `tests/bdd/req39_metrics_percentile.feature` | — | ~50 (PR#2) | 2 BDD scenarios (p95 worked example, insufficient-data warning). |
| `tests/bdd/test_observability_steps.py` | — | ~320 (PR#1: 150; PR#2: +170) | pytest-bdd glue shared across all 5 BDD features. Single file (per D12) to avoid step-def duplication across 11 scenarios. |
| `tests/fixtures/metrics/sample_24h.jsonl` | — | ~20 lines | Committed fixture: 15 events covering all 7 active domains with deterministic ISO timestamps spanning 24h. PR#1 lands; PR#2 reuses. |

### Modified files (~550 LOC delta)

| File | LOC delta | Change |
|---|---|---|
| `src/flow_engineering/observability.py` | +300 (PR#1: +200; PR#2: +100) | **PR#1**: +`read_events_since(path, since_iso, until_iso=None) -> list[dict]`, +`read_events_by_domain(path, domain) -> list[dict]`, +`summarize(events) -> dict[str, dict]` (collapse to `{name: {count, domain, first_seen, last_seen}}`), +`DOMAIN_BY_PREFIX` table (covers all 31 counters), +`ACCEPTED_DOMAINS` list (8 values). **PR#2**: +`percentile(events, pct, field="elapsed_ms") -> float`, +`aggregate(events, field="value") -> dict[str, float]` (`{count, mean, stddev, min, max}`), +`prometheus_exposition(events, catalog=None) -> str`, +`METRIC_TYPE_OVERRIDES` map. Bump module docstring to mention read-side surface. |
| `src/flow_engineering/cli.py` | +250 (PR#1: +150; PR#2: +100) | **PR#1**: `flow metrics` extended with `--summary`, `--since`, `--until`, `--window`, `--domain`, `--top` flags. `_summarize_metrics()` becomes a thin wrapper calling `observability.summarize()`. **PR#2**: +`--prometheus`, +`--out`, +`--percentile`, +`--aggregations`, +`--field`, +`--format` flags. New `_resolve_window(since_iso, until_iso, window) -> tuple[str, str]` helper. New `_atomic_write_text(path, text) -> int` helper (D10 contract). |
| `tests/unit/test_observability.py` | +200 | Extend the existing test file with read-events, summarize, percentile, aggregate, prometheus-exposition unit tests (mirror `test_observability_vectors.py` style: ~30 new tests). |
| `CHANGELOG.md` | +50 | v0.7.0 entry post-PR#2-merge documenting the new read-side surface (mirrors the v0.6.0 graph-snapshots entry). |
| `pyproject.toml` | +5 | Version bump to 0.7.0 (after graph-snapshots archived at 0.6.0). |

**Production total**: ~750 LOC across 0 new + 2 modified = 2 production files.
**Test total**: ~2 170 LOC across 8 new test files + 1 new fixture + 1 modified.
**Strict-TDD ratio**: ~2.9× — within the 2-4× target band from
`decision-code-linking` S3 precedent.

## Interfaces / Contracts

```python
# observability.py — NEW read-side helpers (PR#1)
def read_events_since(
    path: Path | None,
    since_iso: str,
    until_iso: str | None = None,
) -> list[dict[str, Any]]:
    """Filter ``read_all(path)`` to events whose ``ts`` is in
    ``[since_iso, until_iso]`` (inclusive on both ends). The string compare
    is lexicographic — ISO 8601 ``Z``-suffixed UTC is fixed-width so lex
    order == chronological order. Empty ``until_iso`` means no upper bound."""


def read_events_by_domain(
    path: Path | None,
    domain: str,
) -> list[dict[str, Any]]:
    """Filter ``read_all(path)`` to events whose counter name matches one
    of the prefixes registered for ``domain`` in ``DOMAIN_BY_PREFIX``.
    Unknown domain → empty list (caller decides)."""


def summarize(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Collapse events into ``{name: {count, domain, first_seen, last_seen}}``.

    - ``count`` = sum of ``fields.count`` (fallback ``fields.confirmed``,
      fallback 1 per event) — matches the existing ``_summarize_metrics``
      contract exactly.
    - ``domain`` = ``DOMAIN_BY_PREFIX[<longest matching prefix>]`` or
      ``"unknown"`` if no prefix matches (W23 dual-name history).
    - ``first_seen`` / ``last_seen`` = earliest / latest ``ts`` across
      matching events (ISO 8601 string)."""


# observability.py — NEW lookup tables (PR#1)
DOMAIN_BY_PREFIX: dict[str, str] = {
    # binding (REQ-8)
    "suggest_": "binding", "bindings_": "binding", "inspect_": "binding",
    # backfill (REQ-8 close)
    "backfill_": "backfill",
    # drift (REQ-12)
    "drift_": "drift",
    # vector (REQ-22)
    "vector_": "vector", "reindex_": "vector",
    # federated (REQ-26)
    "federated_": "federated",
    # snapshot (REQ-26 T1.7)
    "snapshot_": "snapshot",
    # metadata (REQ-13, REQ-24)
    "update_observation_metadata_": "metadata",
    "project_tag_": "metadata",
    # engine — RESERVED for REQ-42; v1 has no engine_* counters
}

ACCEPTED_DOMAINS: list[str] = [
    "binding", "backfill", "drift", "vector",
    "federated", "snapshot", "metadata", "engine",
]

# observability.py — NEW read-side helpers (PR#2)
def percentile(
    events: list[dict[str, Any]],
    pct: int,                           # 50, 95, or 99
    field: str = "elapsed_ms",
) -> float | None:
    """Return the requested percentile of ``events[*].fields[field]``.

    Uses ``statistics.quantiles(data, n=100, method="inclusive")`` from
    stdlib — linear interpolation. Returns ``None`` when fewer than 2
    numeric samples exist (caller emits the "insufficient data" warning).
    Invalid ``pct`` raises ``ValueError`` — the CLI catches and exits 3."""


def aggregate(
    events: list[dict[str, Any]],
    field: str = "value",
) -> dict[str, float]:
    """Return ``{count, mean, stddev, min, max}`` for the numeric samples
    in ``events[*].fields[field]``. Sample stddev (n-1 denominator via
    ``statistics.stdev``). Empty input → ``{count: 0, mean: 0.0,
    stddev: 0.0, min: 0.0, max: 0.0}``. Single sample → ``stddev: 0.0``
    (not an error)."""


def prometheus_exposition(
    events: list[dict[str, Any]],
    catalog: dict[str, str] | None = None,
) -> str:
    """Format the filtered events as a Prometheus textfile exposition.

    Per counter (sorted alphabetically for stable output), emits:
    - ``# HELP <name> <description>``
    - ``# TYPE <name> <counter|summary|gauge>``
    - One ``<name>{label1="v1",...} <value>`` line per distinct label tuple

    Type derivation per D6: ``METRIC_TYPE_OVERRIDES`` first, then suffix
    rule (``_total`` → counter; ``_ms`` / ``_seconds`` → summary; bare →
    gauge). Empty input → ``"# EOF\\n"`` (Prometheus convention)."""


# observability.py — NEW lookup table (PR#2)
METRIC_TYPE_OVERRIDES: dict[str, str] = {
    # v1: zero overrides. The map is the forward-compatible hook for
    # ambiguous cases (e.g., REQ-42 engine_* counters with non-suffix types).
}


# cli.py — MODIFIED, NON-BREAKING (PR#1 + PR#2)
@click.command()
@click.option("--json", "json_flag", is_flag=True, default=False,
              help="Emit machine-readable JSON instead of a text summary.")
@click.option("--summary", "summary_flag", is_flag=True, default=False,
              help="Render the text dashboard with totals + per-domain "
                   "breakdown + top-N counters (REQ-35).")
@click.option("--since", "since_iso", default=None, metavar="ISO8601",
              help="Filter events to those with ts >= ISO 8601 UTC.")
@click.option("--until", "until_iso", default=None, metavar="ISO8601",
              help="Filter events to those with ts <= ISO 8601 UTC.")
@click.option("--window", "window", default=None,
              type=click.Choice(["1h", "24h", "7d"], case_sensitive=False),
              help="Rolling time-window shorthand for --since.")
@click.option("--domain", "domain", default=None,
              type=click.Choice(ACCEPTED_DOMAINS),
              help="Filter events to one of the 8 accepted domains.")
@click.option("--top", "top_n", default=None, type=int,
              help="Limit output to the N most-fired counters.")
@click.option("--prometheus", "prometheus_flag", is_flag=True, default=False,
              help="Emit Prometheus textfile exposition format (REQ-38).")
@click.option("--out", "out_path", default=None, type=click.Path(),
              help="Write --prometheus output to <path> (atomic write).")
@click.option("--percentile", "percentile_flag", default=None,
              type=click.Choice(["p50", "p95", "p99"], case_sensitive=False),
              help="Compute P50/P95/P99 over the active --field (REQ-39).")
@click.option("--aggregations", "aggregations_flag", is_flag=True,
              default=False, help="Emit {count, mean, stddev, min, max} "
                                  "per counter (REQ-39).")
@click.option("--field", "field_name", default="elapsed_ms",
              help="Field for --percentile / --aggregations "
                   "(default: elapsed_ms).")
@click.option("--format", "format_flag", default=None,
              type=click.Choice(["text", "json", "json-detailed",
                                 "prometheus", "summary"], case_sensitive=False),
              help="Explicit format override (REQ-37 / REQ-38).")
def metrics(...) -> None:
    """Dump the JSONL counter sink as a summary (REQ-8 + REQ-35..39)."""
    ...
```

## Algorithm Details

### Time-window filter (REQ-36)

**Pseudocode** (`_resolve_window` helper in `cli.py`):

```python
def _resolve_window(
    since_iso: str | None,
    until_iso: str | None,
    window: str | None,
) -> tuple[str | None, str | None]:
    """Convert --since/--until/--window flags into a (since, until) ISO pair.

    Precedence: --window > --since (last-wins, Click default).
    """
    # Resolve --window → absolute --since
    if window:
        delta = {"1h": timedelta(hours=1),
                 "24h": timedelta(hours=24),
                 "7d": timedelta(days=7)}[window.lower()]
        rolling_since = (datetime.now(UTC) - delta).strftime("%Y-%m-%dT%H:%M:%SZ")
        since_iso = rolling_since if since_iso is None else since_iso
        # (Click last-wins means --window overrides --since only when
        # the user explicitly passes both; here we let --since win when
        # both are given — matches the spec "When --window is given
        # alongside --since, the LAST one wins".)

    # Parse --since (REUSES _parse_since from cli.py:1022)
    if since_iso:
        try:
            _parse_since(since_iso)            # validate; raises on garbage
        except ValueError:
            emit_error_and_exit_3("--since", since_iso)
    if until_iso:
        try:
            _parse_since(until_iso)
        except ValueError:
            emit_error_and_exit_3("--until", until_iso)
    return since_iso, until_iso
```

**Edge cases**:
- `--since=garbage` → `_parse_since()` raises `ValueError` → CLI catches, emits
  `{"error": "invalid --since value", "value": "garbage", "hint": "..."}` to
  stderr, exits **3** (D9).
- `--since` and `--until` with `--until < --since` → empty filter set; the
  command emits `(no metrics recorded)` (text default) or `{}` (`--json`) or
  `# EOF` (`--prometheus`) and exits **0** (D8).
- `--window=garbage` → `click.Choice` validation rejects at the CLI layer
  (before the handler runs) with the standard Click usage-error message +
  exit code **2** (D9).
- Missing `FLOW_METRICS_PATH` env var and missing default path → `read_all()`
  returns `[]` (D8 default-empty).

### Percentile computation (REQ-39, D7)

**Pseudocode**:

```python
def percentile(events: list[dict], pct: int, field: str = "elapsed_ms") -> float | None:
    """Compute the p<pct> percentile of fields[field] across events."""
    samples: list[float] = []
    for ev in events:
        fields = ev.get("fields") or {}
        v = fields.get(field)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            samples.append(float(v))
    if len(samples) < 2:
        return None
    # statistics.quantiles uses n=100 quantiles and CUT-7 / "inclusive" method
    # which is linear interpolation between adjacent samples — matches the
    # worked example (synthetic 10..1000 → p95 ≈ 950.5 ±0.5).
    q = statistics.quantiles(samples, n=100, method="inclusive")
    return q[pct - 1]      # q is 0-indexed: q[49] = p50, q[94] = p95, q[98] = p99
```

**Edge cases**:
- Empty input → returns `None`. CLI emits `<name> p95: insufficient data` +
  stderr JSON warning; exits **0** (warning, not error).
- Non-numeric `field` (e.g., `trigger="cli"`) → skipped; falls through to
  the "insufficient data" branch.
- Single sample → returns `None` for the same reason.
- `pct` not in {50, 95, 99} → `q[pct - 1]` raises `IndexError`; the CLI
  validates at parse time via `click.Choice`, so this is defensive only.

**Worked example** (mirrors REQ-39 scenario 1):

```python
samples = list(range(10, 1001, 10))       # 100 values: 10, 20, ..., 1000
percentile(samples, 95)                    # → 950.5 (linear interpolation)
```

### Atomic write for export (REQ-38, D10)

**Pseudocode**:

```python
def _atomic_write_text(target: Path, text: str) -> int:
    """Write text to target atomically. Returns the number of bytes written.

    Pattern: tempfile in same parent dir + os.replace + cleanup on failure.
    Guarantees: (a) target is never half-written; (b) no .tmp orphan left
    behind on failure; (c) atomic rename is on the same filesystem
    (target.parent ensures that).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8",
        delete=False, dir=str(target.parent),
        suffix=".prom.tmp", prefix=".metrics-",
    )
    try:
        tmp.write(text)
        tmp.close()
        os.replace(tmp.name, target)        # atomic on POSIX + Windows
    except Exception:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise
    return len(text.encode("utf-8"))
```

**Edge cases**:
- Target parent doesn't exist → `mkdir(parents=True)` creates it.
- Target is a symlink → `os.replace` replaces the symlink target (does NOT
  follow). This is the safe behavior — atomic rename, not atomic content swap.
- Disk full mid-write → exception caught, `.tmp` cleaned up, CLI exits
  **4** (D9) with `{"error": "write failed", "path": ..., "cause": <strerror>}`.
- Permission denied on target → same exit-code-4 path.
- Concurrent invocations (rare for a CLI) → last writer wins via atomic
  rename; no partial-overwrite window.

## Data Model

### `summarize(events)` return shape

```python
{
    "vector_search_invoked_total": {
        "count": 421,
        "domain": "vector",
        "first_seen": "2026-06-26T15:42:11Z",
        "last_seen": "2026-06-27T15:42:11Z",
    },
    "snapshot_pruned_total": {          # W23 dual-name history
        "count": 12,
        "domain": "unknown",             # falls through DOMAIN_BY_PREFIX
        "first_seen": "2026-06-25T11:00:00Z",
        "last_seen": "2026-06-27T09:30:00Z",
    },
    # ... one entry per distinct counter name, sorted alphabetically
}
```

- `count` is `int` (sum of `fields.count` fallback 1).
- `domain` is `str` from `DOMAIN_BY_PREFIX` (or `"unknown"` if no prefix match).
- `first_seen` / `last_seen` are ISO 8601 UTC strings (lexicographically
  comparable; the JSONL sink uses `_now_iso()` from `observability.py:157`
  which produces a fixed-width format).

### `aggregate(events, field)` return shape

```python
{
    "count": 100,
    "mean": 505.0,
    "stddev": 290.0,       # statistics.stdev (n-1); single sample → 0.0
    "min": 10.0,
    "max": 1000.0,
}
```

All values are `float`; `count` is `int` (always non-negative).

### `prometheus_exposition(events)` output format

```text
# HELP vector_search_invoked_total Number of vector search invocations
# TYPE vector_search_invoked_total counter
vector_search_invoked_total{trigger="cli"} 312
vector_search_invoked_total{trigger="programmatic"} 109
# HELP drift_invoked_total Number of drift scan invocations
# TYPE drift_invoked_total counter
drift_invoked_total{change="observability"} 1
# EOF
```

- One `# HELP` + `# TYPE` pair per distinct counter name.
- One metric line per `(counter_name, label_tuple)` combination.
- Numeric values are formatted via Python's `repr(float)` (deterministic,
  no scientific-notation surprises; matches Prometheus textfile convention).
- Empty input → single line `# EOF` (Prometheus convention; signals an
  empty-but-valid textfile).

### Label escaping (REQ-38)

- Label values are wrapped in double quotes; embedded `"`, `\`, and newline
  characters are escaped (`\"`, `\\`, `\n`) per Prometheus textfile spec.
- Counter names and label keys are validated against
  `[a-zA-Z_][a-zA-Z0-9_]*` — invalid names fall into the `"unknown"` bucket
  with a stderr warning (does NOT exit non-zero; defense in depth).

## Error Handling

| Error mode | Exit code | User-facing message (stderr) | Affected flag(s) |
|---|---|---|---|
| Metrics file missing (no `--summary`) | 0 | `(no metrics recorded)` (stdout, NOT stderr) | (no flag) |
| Metrics file missing (`--summary`) | 0 | `(no metrics recorded)` (stdout) | `--summary` |
| Metrics file missing (`--json`) | 0 | `{}` (stdout) | `--json` |
| Metrics file missing (`--prometheus`) | 0 | `# EOF` (stdout) | `--prometheus` |
| Filter set empty after filtering | 0 | `(no events matched filter)` (stdout) | `--since`/`--domain`/etc. |
| `--since=<garbage>` | 3 | `{"error": "invalid --since value", "value": "<garbage>", "hint": "use ISO 8601 UTC, e.g., 2026-06-26T00:00:00Z"}` | `--since` |
| `--until=<garbage>` | 3 | `{"error": "invalid --until value", "value": "<garbage>", "hint": "..."}` | `--until` |
| `--window=<garbage>` | 2 | Click's standard usage error: `Invalid value for '--window': 'garbage' is not one of '1h', '24h', '7d'.` | `--window` |
| `--domain=<garbage>` | 2 | Click's standard usage error: `Invalid value for '--domain': 'garbage' is not one of 'binding', 'backfill', 'drift', 'vector', 'federated', 'snapshot', 'metadata', 'engine'.` | `--domain` |
| `--percentile=<garbage>` | 2 | Click's standard usage error: `Invalid value for '--percentile': ...` | `--percentile` |
| `--format=<garbage>` | 2 | Click's standard usage error: `Invalid value for '--format': ...` | `--format` |
| `--out=<path>` not writable (perm denied) | 4 | `{"error": "write failed", "path": "<path>", "cause": "<strerror>"}` | `--out` |
| `--out=<path>` parent not creatable | 4 | `{"error": "write failed", "path": "<path>", "cause": "<strerror>"}` | `--out` |
| Malformed JSONL line in sink | 0 | (silently skipped; `read_all()` swallows per existing best-effort contract) | (no flag) |
| Percentile with <2 samples | 0 | `{"warning": "not enough data points for percentile", "counter": "<name>", "count": <N>}` (stderr) + `<name> p95: insufficient data` (stdout) | `--percentile` |
| Counter name with invalid Prometheus chars | 0 | `{"warning": "counter name invalid for Prometheus", "name": "<name>"}` (stderr) + falls into `unknown` bucket | `--prometheus` |

**Rationale**: empty/no-matches → exit 0 (D8 default-empty); usage errors
→ exit 2 (Click standard); data errors → exit 3 (matches `flow drift` REQ-10/11
and `git`/`curl` conventions); I/O errors → exit 4 (matches `flow snapshot
rollback` from graph-snapshots). JSON to stderr keeps stdout clean for
piping (`flow metrics --json | jq`).

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `read_events_since` | Synthetic JSONL with 10 events spanning 24h; assert boundary inclusivity (`since`, `until`, both, neither). |
| Unit | `read_events_by_domain` | One event per active domain; assert each `--domain=` filter returns the right subset; unknown domain → empty list (no error). |
| Unit | `summarize` | 15-event fixture; assert `{count, domain, first_seen, last_seen}` shape; assert alphabetical ordering; assert `unknown` bucket for W23 dual-name. |
| Unit | `percentile` (D7) | Synthetic 10..1000 dataset → assert p50=505.0, p95=950.5 (±0.5); single-sample → None; empty → None; non-numeric field → None; `pct=50/95/99` validation. |
| Unit | `aggregate` | Synthetic 100-event fixture → assert `{count, mean, stddev, min, max}`; single-sample → stddev=0.0 (not an error); empty input → zero-filled dict. |
| Unit | `prometheus_exposition` (D6) | Round-trip via `prometheus_client.parser.text_string_to_metric_families(output)`; assert `_total` → counter, `_ms` → summary, bare → gauge; label escaping (quotes, backslashes, newlines); empty → `# EOF`. |
| Unit | `DOMAIN_BY_PREFIX` | Assert every name in `VECTOR_COUNTER_NAMES` + `FEDERATED_COUNTER_NAMES` + `SNAPSHOT_COUNTER_NAMES` + 14 REQ-8/12/13/24 names (31 total) has a matching prefix (no orphans). |
| Unit | Atomic write (D10) | `tmp_path` target; assert `.prom.tmp` cleaned up on success; assert no orphan on simulated write failure (monkeypatch `os.replace` to raise); assert exit code 4 path. |
| Unit | CLI flag matrix | Click `CliRunner` with `FLOW_METRICS_PATH=tmp_path/m.jsonl`; assert all 10 new flags + the existing 2 (text/JSON) produce expected output shape; assert byte-identical output for the legacy 2 paths. |
| Unit | Error paths (D9) | Assert exit codes 2/3/4 for each error mode in the table above; assert JSON shape on stderr; assert stdout stays clean. |
| Unit | `TestMetricsCommand` regression | Verify the 3 existing tests at `test_cli_inspect.py:269-298` stay GREEN — output must be byte-identical to v0.6.0 (no flag = text table; `--json` = flat dict; empty sink = `(no metrics recorded)`). |
| BDD (REQ-35) | Summary view | GIVEN 27 counters across 5 domains + 1 247 events WHEN `flow metrics summary` THEN dashboard renders with totals + per-domain rows sorted desc + top-N counters; exits 0. |
| BDD (REQ-35) | Empty sink | GIVEN empty / missing JSONL WHEN `flow metrics summary` THEN emits `(no metrics recorded)`; exits 0. |
| BDD (REQ-36) | `--since` absolute | GIVEN 10 hourly events WHEN `flow metrics --since=2026-06-26T15:00:00Z` THEN only the 5 events at 15:00..19:00 contribute; exits 0. |
| BDD (REQ-36) | `--window=1h` rolling | GIVEN 5 events at <now-2h>, <now-90m>, <now-45m>, <now-30m>, <now-5m> WHEN `flow metrics --window=1h` THEN only the 3 events at <now-45m>, <now-30m>, <now-5m> contribute; exits 0. |
| BDD (REQ-37) | `--domain=snapshot` | GIVEN events across 5 domains WHEN `flow metrics --domain=snapshot` THEN ONLY `snapshot_*` counters appear; exits 0. |
| BDD (REQ-37) | No `--domain` = all | GIVEN events across 5 domains WHEN `flow metrics` (no flag) THEN all domains contribute; exits 0; output byte-identical to v0.6.0. |
| BDD (REQ-38) | Stdout exposition | GIVEN a `drift_invoked_total` event WHEN `flow metrics --prometheus` THEN stdout contains `# HELP`, `# TYPE counter`, `drift_invoked_total{change="observability"} 1`; exits 0. |
| BDD (REQ-38) | `--out` atomic write | GIVEN 3 distinct counters + writable TMPDIR WHEN `flow metrics --prometheus --out=<TMPDIR>/metrics.prom` THEN file exists and is non-empty + stderr JSON `{wrote, metric_lines: 3, bytes}`; exits 0. |
| BDD (REQ-38) | `--window` composition | GIVEN 10 `drift_invoked_total` events (5 in last 1h, 5 older) WHEN `flow metrics --prometheus --window=1h` THEN the metric line value is 5 (sum of in-window events); exits 0. |
| BDD (REQ-39) | `--percentile=p95` | GIVEN 100 events with elapsed_ms 10..1000 (uniform) WHEN `flow metrics --percentile=p95 --domain=vector` THEN stdout contains `vector_search_latency_ms p95: 950.5` (±0.5); exits 0. |
| BDD (REQ-39) | Insufficient data | GIVEN exactly 1 event for `drift_scan_duration_ms` (elapsed_ms=42) WHEN `flow metrics --percentile=p95 --domain=drift` THEN stdout contains `drift_scan_duration_ms p95: insufficient data` + stderr JSON warning; command STILL exits 0. |
| Secrets invariant | Counter names don't leak paths | GIVEN a counter name like `drift_invoked_total` and a separate `secrets.yaml` reference in the codebase WHEN `flow metrics --prometheus` THEN stdout contains ONLY the documented label keys (`change`, `trigger`, etc.); no file paths leak. |

**Unit test count forecast**: ~30 new unit tests across 4 new files
(`test_cli_metrics.py` ~15, `test_observability_summary.py` ~6,
`test_observability_prometheus.py` ~5, `test_observability_aggregate.py` ~5)
+ ~10 new tests in `test_observability.py` (read-side helpers).

**BDD scenarios**: 11 (per spec REQ-35 ×2, REQ-36 ×2, REQ-37 ×2, REQ-38 ×3,
REQ-39 ×2).

**Coverage targets**: 95% line coverage on the new helpers; 100% coverage on
the error-path branches (D9). `ruff check` clean on all changed files.

**Strict TDD order** per `decision-code-linking` S3 precedent:

1. `observability.py` `read_events_since` — RED: filter boundary cases →
   GREEN: 5 events filtered correctly → REFACTOR: handle edge cases
2. `observability.py` `read_events_by_domain` — RED: prefix matching →
   GREEN: per-domain subset → REFACTOR: `unknown` bucket
3. `observability.py` `summarize` — RED: collapse to `{count, domain, ...}`
   → GREEN: 15-event fixture matches → REFACTOR: alphabetical sort
4. `observability.py` `DOMAIN_BY_PREFIX` — RED: orphan-name test → GREEN:
   all 31 names covered → REFACTOR: dict-literal layout
5. `cli.py` `--summary` / `--since` / `--until` / `--window` / `--domain` /
   `--top` flags — RED: CliRunner → GREEN: flag matrix → REFACTOR: error
   path D9
6. `tests/bdd/req35/36/37_*.feature` + `test_observability_steps.py` —
   RED: BDD step defs → GREEN: scenarios pass → REFACTOR
7. `observability.py` `aggregate` / `percentile` (PR#2) — RED: 10..1000
   dataset → GREEN: p95 ≈ 950.5 → REFACTOR
8. `observability.py` `prometheus_exposition` (PR#2) — RED: round-trip
   fails → GREEN: `prometheus_client.parser` parses → REFACTOR
9. `cli.py` `--prometheus` / `--out` / `--percentile` / `--aggregations` /
   `--field` / `--format` flags (PR#2) — RED: CliRunner → GREEN → REFACTOR
10. `tests/bdd/req38/39_*.feature` + step glue extension (PR#2)
11. `CHANGELOG.md` v0.7.0 entry last

## Migration / Rollout

**No data migration** is required. The user's existing `~/.flow-engineering/metrics.jsonl`
stays untouched — the new read-side helpers filter the already-written events
in-memory. Two opt-in rollout paths:

1. **Operators who want the summary view** — run `flow metrics summary`
   (no flags). No migration, no setup.

2. **Operators who want Prometheus integration** — install
   `prometheus_client` (test-only dep) and point `node_exporter`'s
   textfile collector at a cron-scheduled `flow metrics --prometheus
   --out=/var/lib/prometheus/textfile/metrics.prom` invocation. The
   `--out` flag is atomic (D10) so concurrent scrapes are safe.

**Rollback** per-PR (revert merge; all additive):

- PR#1 revert: `flow metrics` returns to its v0.6.0 13-LOC shape
  (text + JSON only). The 5 new functions in `observability.py`
  (`read_events_since`, `read_events_by_domain`, `summarize`,
  `DOMAIN_BY_PREFIX`, `ACCEPTED_DOMAINS`) are unused; deleting the
  new flags restores the v0.6.0 surface byte-identically.
- PR#2 revert: `flow metrics` returns to PR#1's state (summary +
  window + domain work; no Prometheus / percentile). Same additive
  contract.
- `openspec/specs/observability/spec.md` is a NEW file; deleting it
  removes the capability spec but does not break runtime behavior
  (the catalog is informational).
- 5 BDD feature files are NEW; removing them disables BDD coverage
  for the new REQs but does not break the existing 801 tests.
- The user's `~/.flow-engineering/metrics.jsonl` is NOT touched by
  any change in this proposal — the sink is read-only.

To restore the pre-change-#6 install: `git revert <PR#1-merge> <PR#2-merge>`.
The JSONL event format is unchanged; the user's existing metrics data
survives intact.

## Open Questions — RESOLVED (all 10 from proposal #194)

| # | Question | Resolution |
|---|---|---|
| **1** | Default output change — does `flow metrics` default stay flat or change to summary view? | **FLAT DEFAULT, `--summary` opt-in.** `flow metrics` without any new flags stays byte-identical to v0.6.0 (`<name>  <count>` text OR `--json` flat dict). REQ-35 (`--summary`) is the opt-in path to the text dashboard. Confirmed against `TestMetricsCommand` at `tests/unit/test_cli_inspect.py:269-298` — the 3 existing tests cover text/JSON/empty and stay GREEN with the flat default. (Resolves OQ-1 + D8 default-empty contract.) |
| **2** | Prometheus type derivation for latency — `summary` (v1) or `histogram` (v1.1)? | **`summary` for v1.** `_latency_ms` / `_duration_seconds` counters emit as Prometheus `summary` type (single quantile via `--percentile=p50\|p95\|p99`). Histogram type with bucket math is explicitly deferred to v1.1. (Resolves OQ-2 + D6 + spec REQ-38 D6.) |
| **3** | Domain categorization strategy — prefix-based or explicit `domain` field on events? | **PREFIX-BASED via `DOMAIN_BY_PREFIX` table.** No changes to the 5 record helpers; no `domain` field injected into events. Prefix table maps each `prefix → domain_name` for the 8 accepted `--domain` values. Explicit `domain` field on events is explicitly deferred to a `structured-events` follow-up change. (Resolves OQ-3 + D5.) |
| **4** | Percentile computation timing — at increment time (sliding sketch) or query time (sort + bisect)? | **QUERY-TIME.** `statistics.quantiles(data, n=100, method="inclusive")` from stdlib. O(N log N) per query; ~1 000 events sorts in <1ms. No in-memory state, no sketch overhead, no consistency between `flow metrics` invocations. Sliding t-digest / HDR histogram explicitly deferred to v1.1 if performance becomes a real issue. (Resolves OQ-4 + D7.) |
| **5** | `--since` / `--until` / `--window` semantics — rolling vs calendar boundaries? | **BOTH — `--since=<iso>` (absolute, reused from `flow drift` REQ-10/11) AND `--window=<1h\|24h\|7d>` (rolling shorthand).** `1h` = `now − 60 minutes` (rolling, NOT calendar-aligned to top-of-hour). Case-insensitive parse. Calendar-day boundaries (`--since=today` meaning `00:00 UTC`) explicitly deferred. (Resolves OQ-5 + D4.) |
| **6** | `--top=N` semantics — by event count, by `first_seen` recency, or by `last_seen` recency? | **BY EVENT COUNT (default), descending.** `--top=N` returns the N most-fired counters. No `--top-by` flag in v1 — if users need recency sorting, they use `--since` + the flat default. (Resolves OQ-6 — confirmed `count` is the default for the "what counters fire most" use case.) |
| **7** | Backward compatibility of `--json` — keep flat dict or richer shape? | **KEEP FLAT for backwards compat.** `flow metrics --json` continues to emit `{name: count}` flat dict (byte-identical to v0.6.0). Explicit `--format=json-detailed` emits the richer shape `{name, count, domain, first_seen, last_seen, ...}` (uses `summarize()` return value). `--format=json` aliases to today's contract. External consumers (Engram #140 vector-semantic-search references `flow metrics --json`) are protected. (Resolves OQ-7 + D8.) |
| **8** | Dashboard format choice — text-only vs `rich` library vs interactive TUI? | **TEXT-ONLY via `click.echo`.** Verified `pyproject.toml` has NO `rich` runtime dep (only transitive via `uv.lock`); no new runtime dep added. Mirrors the precedent from `flow drift`, `flow status`, `flow snapshot list`. `rich` is on the v2 watch list if dashboard density grows. (Resolves OQ-8.) |
| **9** | REQ-42 scope — what surfaces get `engine_*` counters in v1.1? | **LIMITED SCOPE: CLI startup time + embedding provider latency** (extends REQ-22's `vector_search_latency_ms` precedent). Daemon queue depth is explicitly deferred to a dedicated `engine-instrumentation` change. The `engine` domain slot in `DOMAIN_BY_PREFIX` is RESERVED but the v1 table has no `engine_*` prefixes. (Resolves OQ-9.) |
| **10** | `openspec/specs/` bootstrap policy — kebab-case folder per capability vs co-located specs? | **KEBAB-CASE FOLDER PER CAPABILITY** at `openspec/specs/<change-name>/spec.md`. Change #6 creates `openspec/specs/observability/spec.md` as the FIRST capability spec, bootstrapping the baseline. Future changes add specs to the same baseline (`openspec/specs/vector-semantic-search/spec.md` retro-fill, `openspec/specs/cross-project-federation/spec.md` retro-fill, etc.). Matches the sdd-propose skill template "New Capabilities → each becomes `openspec/specs/<name>/spec.md`". Co-located specs (in `openspec/changes/<change>/spec.md`) are kept for in-flight changes; the `openspec/specs/` baseline is the LONG-TERM home for capability definitions. (Resolves OQ-10 + D11 + archive-report #61.) |

**Resolved: 10/10. Remaining: 0.**

## Unblocks / Constraints

**Unblocks**:

- Text dashboard for the 31 counters already shipped (REQ-35) — operators
  can answer "what counters fire most?" without `grep` + `jq`.
- Prometheus integration for local CI/CD + Grafana (REQ-38) — `flow metrics
  --prometheus --out=/var/lib/prometheus/textfile/metrics.prom` plugs into
  the standard node_exporter textfile collector pattern.
- Percentile-based latency SLO tracking (REQ-39) — `flow metrics
  --percentile=p95 --domain=vector` answers "what's my vector-search
  p95 latency?" from the existing `vector_search_latency_ms` events.
- The project's `openspec/specs/` baseline (D11) — future changes
  add specs to `openspec/specs/<change-name>/spec.md` and the
  `code_refs` block reference surface from `flow inspect <change>`.
- Federation-aware filtering (REQ-43, deferred) — when the
  `federated-observability` follow-up lands, the existing
  `DOMAIN_BY_PREFIX` table extends with `--project=<key>` filter.
- Rotation policy (REQ-44, deferred) — when the v1.1 rotation lands,
  `read_all()` becomes the single I/O seam to extend.

**Constrains**:

- Any future change that adds a counter name MUST either add it to
  `DOMAIN_BY_PREFIX` or update the prefix rule. The BDD scenario
  "GIVEN a counter THEN its domain is in the table" enforces this.
- The flat text default of `flow metrics` MUST stay byte-identical to
  v0.6.0 for backwards compatibility with existing scripts and tests
  (REQ-8 close contract; `TestMetricsCommand` 3 tests are the regression
  gate).
- The `_summarize_metrics()` helper at `cli.py:960` becomes a thin
  wrapper; existing internal callers (none outside `metrics()`) stay
  unaffected.
- Prometheus textfile output MUST be parseable by the official
  `prometheus_client.parser.text_string_to_metric_families` — round-trip
  test in `tests/unit/test_observability_prometheus.py` is the contract gate.

## Out-of-Scope (consolidated)

The following 15 items are explicitly out of scope for change #6 and belong
to named follow-ups:

1. **REQ-40 — Label-based query** (`--label key=value` for arbitrary
   event-field filtering beyond `--domain`) — defer to v1.1.
2. **REQ-41 — Threshold alerting** (`--threshold name:op:N` to emit
   non-zero exit codes for CI/CD integration) — defer to v1.1.
3. **REQ-42 — `engine_*` counters** (CLI startup time, embedding
   provider latency, daemon queue depth) — defer to a dedicated
   `engine-instrumentation` change. The `engine` domain slot in
   `DOMAIN_BY_PREFIX` is RESERVED but the v1 table is empty for it.
4. **REQ-43 — Federation-aware events** (`--project=<key>` filter that
   requires modifying every record helper signature to inject a
   `project` field into events) — defer to a `federated-observability`
   follow-up change.
5. **REQ-44 — JSONL rotation** (`FLOW_METRICS_MAX_BYTES`,
   `FLOW_METRICS_MAX_AGE_DAYS` to gzip-and-rotate the sink file) —
   defer to v1.1 (cross-cuts `read_all()` and 6 existing call sites;
   too invasive for v1).
6. **Snapshot export/import** for sharing (`flow snapshot export <id>`
   / `flow snapshot import <id>`) — already deferred in `graph-snapshots`
   archive.
7. **Async embed-on-save** (auto-vectorize on `mem_save`) — already
   deferred in `vector-semantic-search` archive.
8. **Per-snapshot percentile** (`flow snapshot show <id> --percentile=p95`
   to compute latency percentiles over the snapshot window) — v2;
   v1 percentiles are over the LIVE JSONL sink only.
9. **Histogram metric type in Prometheus exporter** (bucket-based
   counts for `_latency_ms` / `_duration_seconds`) — v1 emits `summary`
   type (single quantile); `histogram` type deferred until someone
   needs bucket math.
10. **Real-time tail mode** (`flow metrics --tail` to follow the JSONL
    sink like `tail -f`) — deferred to v2; the sink is append-only and
    a tail would be straightforward but is not on the v1 critical path.
11. **Graphviz / DOT export of counter relationships** (e.g.,
    `vector_search_invoked_total → vector_index_size_observations`) —
    deferred to v2; the dependency graph is implicit in the prefix
    table but not formalized.
12. **Webhook / Slack alerting on threshold breach** (CI integration;
    companion to REQ-41) — deferred to v1.1 along with REQ-41.
13. **Multi-process metric aggregation** (when `flow` is invoked in
    parallel via a daemon or shell pipeline) — deferred; v1 assumes
    single-process CLI invocations.
14. **OTLP / OpenTelemetry exporter** (vs. Prometheus textfile format) —
    deferred; Prometheus textfile is the simplest offline-first choice
    and OTLP would require a runtime dep.
15. **CSV export** (`flow metrics --format=csv`) — deferred to v2; the
    5 active formats (text, json, json-detailed, prometheus, summary)
    cover the v1 use cases.

## Risks

The 12 risks from proposal §6 are reduced to 8 carry-forwards + 0 new
risks identified during the design phase. The risks below incorporate
the mitigations noted in the proposal:

| # | Risk | Likelihood | Severity | Status |
|---|---|---|---|---|
| 1 | `graph-snapshots` (change #5) does not archive before change #6 apply starts → 4 `snapshot_*` counters unstable in `SNAPSHOT_COUNTER_NAMES` catalog | LOW (was HIGH) | MED | **RESOLVED** — HEAD `e0f863b` commit message confirms `graph-snapshots - SDD cycle complete (PASS WITH WARNINGS, 4/8 W-fixes resolved)`. SNAPSHOT_COUNTER_NAMES catalog is stable. PR#1 SPEC references the catalog by name only (resilient to additions). |
| 2 | PR#1 cumulative realistic ~4 500 LOC > 400-line review budget | MED | MED | MITIGATED — per-commit work-unit splits per `work-unit-commits` skill (5-6 commits each ≤400 LOC). Mirror `cross-project-federation` chained-PR pattern. |
| 3 | JSONL rotation (REQ-44) cross-cuts `read_all()` — risk of regression in 6 existing call sites | MED | HIGH | MITIGATED — REQ-44 explicitly deferred to v1.1 (out-of-scope item #5); v1 ships only read-side with no I/O path changes. |
| 4 | Federation-aware events (REQ-43) requires changing every record helper signature — invasive | MED | MED | MITIGATED — REQ-43 deferred to `federated-observability` follow-up (out-of-scope item #4); events stay project-less for v1. |
| 5 | `openspec/specs/observability/spec.md` is precedent-setting — project has NO `openspec/specs/` baseline today | LOW | LOW | MITIGATED — `glob openspec/specs/**` confirmed empty; cross-project-federation archive-report #61 explicitly defers to this change. OQ-10 confirms kebab-case baseline pattern. |
| 6 | Prometheus type derivation ambiguous for `vector_index_size_observations` (gauge by suffix but used like a counter) | LOW | LOW | MITIGATED — D6 `METRIC_TYPE_OVERRIDES` map is the escape hatch; v1 has zero overrides (default suffix rule `_total → counter` does NOT apply to `vector_index_size_observations`, so it falls into `gauge` automatically). |
| 7 | `--since`/`--until` parsing must mirror `flow drift --since` ISO 8601 behavior (REQ-10/11); typo or drift breaks window filter | LOW | MED | MITIGATED — REUSES `_parse_since()` from `cli.py:1022` verbatim (no new parser); BDD scenario `flow metrics --since=garbage` exits with code 3 + JSON error (D9). |
| 8 | W23 carry-forward: `snapshot_pruned_total` + `snapshot_prune_total` dual-name history may confuse `summarize()` | LOW | LOW | MITIGATED — `summarize()` matches the LONGEST prefix in `DOMAIN_BY_PREFIX` (or `"unknown"` if no match); the W23 dual-name `snapshot_prune_total` (without `d`) matches `snapshot_` prefix → domain=`snapshot`. The `unknown` bucket is the defense for future name drift. |

## Cross-Impact

| Queued / shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `observability.increment()`, `read_all()`, `record_backfill_coverage()` reused as the foundation; 8 binding/backfill/inspect counters stable | Compatible (consumes the seam; existing 3 `TestMetricsCommand` tests stay green) |
| `decision-reality-drift` (shipped v0.3.0) | `record_drift_summary()` emits the 8 drift counters that REQ-35/REQ-37 surface; `_parse_since()` at `cli.py:1022` reused verbatim for `--since` parsing | Compatible (consumes the seam) |
| `vector-semantic-search` (shipped v0.4.0) | `record_vector_summary()` emits the 6 vector counters + `vector_search_latency_ms` events that REQ-39 percentiles aggregate over | Compatible (consumes the seam; the worked example from spec REQ-39 scenario 1 validates the contract) |
| `cross-project-federation` (shipped v0.5.0) | `record_federated_summary()` emits the 3 federated counters; archive-report #61 explicitly defers the spec catalog to this change | Compatible (resolves #61; D11 + D8 confirm the bootstrap pattern) |
| `graph-snapshots` (change #5, ARCHIVED at HEAD `e0f863b`) | `record_snapshot_event()` emits the 4 snapshot counters in batch C T1.7; `SNAPSHOT_COUNTER_NAMES` catalog referenced by the new `openspec/specs/observability/spec.md` | Compatible (consumes the seam; spec absorbs the catalog; risk #1 RESOLVED) |
| `prompt-registry` (#7, future) | Unrelated layer | No conflict |

## Chained PR Strategy

**TWO CHAINED PRs** (per proposal #194 + spec #195):

| PR | Scope | Forecast prod LOC | Forecast test LOC | Realistic ×2.9 TDD | Acceptance |
|---|---|---|---|---|---|
| **PR#1 — Foundation** | REQ-35 + REQ-36 + REQ-37 + `openspec/specs/observability/spec.md` bootstrap + 5 read-side helpers + 2 lookup tables + 6 new flags (`--summary`, `--since`, `--until`, `--window`, `--domain`, `--top`) + 3 BDD features + 4 unit test files + 1 BDD glue file | ~550 | ~1 100 | ~4 500 | All 801 existing tests pass + 6 new BDD scenarios + 17 new unit tests; `ruff check` clean; `TestMetricsCommand` regression green |
| **PR#2 — Export + aggregation** | REQ-38 + REQ-39 + `prometheus_exposition()` + `aggregate()` + `percentile()` + `METRIC_TYPE_OVERRIDES` + 6 new flags (`--prometheus`, `--out`, `--percentile`, `--aggregations`, `--field`, `--format`) + 2 BDD features + 2 unit test files + BDD glue extension + CHANGELOG v0.7.0 | ~250 | ~750 | ~3 300 | All PR#1 tests + 801 existing tests pass + 5 new BDD scenarios + 10 new unit tests; `ruff check` clean; prometheus_client parser round-trip green; atomic-write test green |

**Chain strategy**: stacked-to-main (consistent with prior 4 changes).
**400-line review budget risk**: HIGH per-PR — both PRs exceed budget.

**Mitigation**: per-commit work-unit splits per `work-unit-commits` skill
convention. PR#1 commits (target ≤400 LOC each):

1. `feat(observability): DOMAIN_BY_PREFIX + ACCEPTED_DOMAINS tables + 31-counter coverage test` (~150 prod LOC + 100 test LOC = 250 LOC) — RED phase for D5
2. `feat(observability): read_events_since + read_events_by_domain` (~100 prod + 150 test = 250 LOC) — RED→GREEN for D3 filter helpers
3. `feat(observability): summarize() helper with {count, domain, first_seen, last_seen}` (~80 prod + 200 test = 280 LOC) — REQ-35 foundation
4. `feat(cli): --summary + --since + --until + --window flags on flow metrics` (~100 prod + 200 test = 300 LOC) — REQ-35 + REQ-36 CLI surface
5. `feat(cli): --domain + --top flags on flow metrics` (~50 prod + 200 test = 250 LOC) — REQ-37 CLI surface
6. `docs(specs): bootstrap openspec/specs/observability/spec.md (31-counter catalog)` (~200 docs + 100 test = 300 LOC) — D11 + archive-report #61 resolution

PR#2 commits (target ≤400 LOC each):

1. `feat(observability): percentile() + aggregate() + METRIC_TYPE_OVERRIDES` (~80 prod + 250 test = 330 LOC) — REQ-39 helpers
2. `feat(observability): prometheus_exposition() formatter + parser round-trip` (~120 prod + 200 test = 320 LOC) — REQ-38 helper
3. `feat(cli): --prometheus + --out atomic write` (~70 prod + 150 test = 220 LOC) — REQ-38 CLI surface
4. `feat(cli): --percentile + --aggregations + --field + --format flags` (~80 prod + 200 test = 280 LOC) — REQ-39 CLI surface
5. `docs(changelog): v0.7.0 entry + 2 SKILL.md updates + 2 BDD feature files` (~100 prod + 250 test/docs = 350 LOC) — final

The per-commit diffs stay focused (≤400 LOC each) so review remains tractable
even though each PR is large cumulatively. This is the chained-PR-as-commits
pattern from the `work-unit-commits` skill.

## Decision ↔ Code Binding

12 architecture decisions bind to concrete anchor points:

- **D1** (module layout: extend `observability.py`) → `src/flow_engineering/observability.py:475` (current end-of-file)
- **D2** (JSONL append-only, no rotation) → `src/flow_engineering/observability.py:175` (`increment()` append path unchanged)
- **D3** (function-based API) → `src/flow_engineering/observability.py` (NEW section after `SNAPSHOT_COUNTER_NAMES`)
- **D4** (rolling `--window`) → `src/flow_engineering/cli.py:1022` (`_parse_since()` reused) + new `_parse_window` helper
- **D5** (`DOMAIN_BY_PREFIX` table) → `src/flow_engineering/observability.py:124` (next to `SNAPSHOT_COUNTER_NAMES`)
- **D6** (Prometheus textfile format) → `src/flow_engineering/observability.py` (NEW `prometheus_exposition()` function, PR#2)
- **D7** (`statistics.quantiles` percentile) → `src/flow_engineering/observability.py` (NEW `percentile()` function, PR#2)
- **D8** (default-empty, exit 0) → `src/flow_engineering/cli.py:987-989` (existing `(no metrics recorded)` path preserved)
- **D9** (exit codes 2/3/4) → `src/flow_engineering/cli.py` (NEW error handlers in `metrics()`)
- **D10** (atomic write via `tempfile + os.replace`) → `src/flow_engineering/cli.py` (NEW `_atomic_write_text()` helper)
- **D11** (spec bootstrap) → `openspec/specs/observability/spec.md:1` (NEW file)
- **D12** (cross-PR consistency) → `tests/bdd/test_observability_steps.py:1` (single shared glue file, both PRs)

---

## Structured Metadata

- **decisions_count**: 12 (D1..D12)
- **open_questions_resolved**: 10/10 (all from proposal #194)
- **open_questions_remaining**: 0
- **file_count**: 11 new + 4 modified = 15 total (1 prod new + 10 test new + 4 prod modified)
- **loc_forecast**: ~800 production + ~2 170 test = ~2 970 total
- **pr_count**: 2 (chained, foundation PR#1 first then export+aggregation PR#2)
- **next_recommended**: `sdd-tasks observability`

## Traceability

| Decision | Resolves OQ | Maps to REQ | Implementation anchor |
|---|---|---|---|
| **D1** (module layout: extend `observability.py`) | — | REQ-35..39 (all 5) | `src/flow_engineering/observability.py:475` |
| **D2** (JSONL append-only, no rotation) | — | REQ-35..39 (all 5) | `src/flow_engineering/observability.py:175` (append path unchanged) |
| **D3** (function-based API) | — | REQ-35..39 (all 5) | `src/flow_engineering/observability.py` (5 new functions) |
| **D4** (rolling `--window` + absolute `--since`) | **OQ-5** | REQ-36 | `src/flow_engineering/cli.py:1022` (`_parse_since` reused) + new `_parse_window` |
| **D5** (`DOMAIN_BY_PREFIX` table) | **OQ-3** | REQ-37 | `src/flow_engineering/observability.py:124` (next to `SNAPSHOT_COUNTER_NAMES`) |
| **D6** (Prometheus `summary` for latency, `_total` → counter) | **OQ-2** | REQ-38 | `src/flow_engineering/observability.py` (new `prometheus_exposition`, PR#2) |
| **D7** (`statistics.quantiles` query-time percentile) | **OQ-4** | REQ-39 | `src/flow_engineering/observability.py` (new `percentile`, PR#2) |
| **D8** (default-empty, exit 0) | **OQ-1** | REQ-35 | `src/flow_engineering/cli.py:987-989` (preserved) |
| **D9** (exit codes 2/3/4) | — | REQ-35..39 (error paths) | `src/flow_engineering/cli.py` (new error handlers) |
| **D10** (atomic write via `tempfile + os.replace`) | — | REQ-38 (`--out` flag) | `src/flow_engineering/cli.py` (new `_atomic_write_text`) |
| **D11** (spec bootstrap at `openspec/specs/observability/spec.md`) | **OQ-10** | REQ-35..39 (catalog) | `openspec/specs/observability/spec.md:1` (NEW) |
| **D12** (cross-PR consistency: shared module + shared glue) | — | REQ-35..39 (all 5) | `tests/bdd/test_observability_steps.py:1` (single shared file) |

**OQ coverage summary**: All 10 open questions from proposal #194 §5 are
resolved by the D1-D12 architecture decisions above (OQ-1 → D8; OQ-2 → D6;
OQ-3 → D5; OQ-4 → D7; OQ-5 → D4; OQ-6 → D5 sort key; OQ-7 → D8 flat-dict
contract; OQ-8 → D8 text-only dashboard; OQ-9 → D5 reserved `engine` slot;
OQ-10 → D11 kebab-case baseline). No deferrals.

---

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_module",
      "label": "observability.py (475→~775 LOC after change #6; +5 read-side helpers + 2 lookup tables)",
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
      "id": "src_flow_engineering_observability_read_events_since",
      "label": "read_events_since(path, since_iso, until_iso=None) — NEW (D3, PR#1)",
      "file": "src/flow_engineering/observability.py",
      "line": 475,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_read_events_by_domain",
      "label": "read_events_by_domain(path, domain) — NEW (D3 + D5, PR#1)",
      "file": "src/flow_engineering/observability.py",
      "line": 490,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_summarize",
      "label": "summarize(events) -> dict[str, dict] — NEW (D3, REQ-35, PR#1)",
      "file": "src/flow_engineering/observability.py",
      "line": 505,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_percentile",
      "label": "percentile(events, pct, field='elapsed_ms') — NEW (D7, REQ-39, PR#2)",
      "file": "src/flow_engineering/observability.py",
      "line": 540,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_aggregate",
      "label": "aggregate(events, field='value') — NEW (REQ-39, PR#2)",
      "file": "src/flow_engineering/observability.py",
      "line": 555,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_prometheus_exposition",
      "label": "prometheus_exposition(events, catalog=None) — NEW (D6, REQ-38, PR#2)",
      "file": "src/flow_engineering/observability.py",
      "line": 570,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_domain_by_prefix",
      "label": "DOMAIN_BY_PREFIX table — NEW (D5, REQ-37, 11 prefixes covering all 31 counters)",
      "file": "src/flow_engineering/observability.py",
      "line": 600,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_accepted_domains",
      "label": "ACCEPTED_DOMAINS list — NEW (D5, 8 values including reserved 'engine')",
      "file": "src/flow_engineering/observability.py",
      "line": 615,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_metric_type_overrides",
      "label": "METRIC_TYPE_OVERRIDES map — NEW (D6, zero entries in v1, forward-compatible hook)",
      "file": "src/flow_engineering/observability.py",
      "line": 620,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_vector_counter_names",
      "label": "VECTOR_COUNTER_NAMES catalog (REQ-22, 6 names) — referenced by DOMAIN_BY_PREFIX test",
      "file": "src/flow_engineering/observability.py",
      "line": 85,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_federated_counter_names",
      "label": "FEDERATED_COUNTER_NAMES catalog (REQ-26, 3 names) — referenced by DOMAIN_BY_PREFIX test",
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
      "label": "flow metrics subcommand (cli.py:980-992, 13 LOC) — extended with 10 new flags in change #6",
      "file": "src/flow_engineering/cli.py",
      "line": 980,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_summarize_metrics",
      "label": "_summarize_metrics() helper (cli.py:960-974, 15 LOC) — REFACTOR target: thin wrapper around observability.summarize()",
      "file": "src/flow_engineering/cli.py",
      "line": 960,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_parse_since",
      "label": "_parse_since(raw) at cli.py:1022 — REUSED verbatim for --since/--until ISO 8601 parsing",
      "file": "src/flow_engineering/cli.py",
      "line": 1022,
      "confidence": 0.95,
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
      "label": "tests/bdd/test_observability_steps.py (NEW — pytest-bdd glue shared across 5 BDD features, ~320 LOC total)",
      "file": "tests/bdd/test_observability_steps.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_cli_metrics",
      "label": "tests/unit/test_cli_metrics.py (NEW — full CLI surface coverage for flow metrics, ~400 LOC)",
      "file": "tests/unit/test_cli_metrics.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_observability_summary",
      "label": "tests/unit/test_observability_summary.py (NEW — summarize() helper coverage, ~150 LOC)",
      "file": "tests/unit/test_observability_summary.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_observability_prometheus",
      "label": "tests/unit/test_observability_prometheus.py (NEW — textfile format round-trip, ~250 LOC)",
      "file": "tests/unit/test_observability_prometheus.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_observability_aggregate",
      "label": "tests/unit/test_observability_aggregate.py (NEW — percentile + aggregate coverage, ~250 LOC)",
      "file": "tests/unit/test_observability_aggregate.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    }
  ]
}