# Apply Progress: change #6 observability — PR#1 batch A

**Date:** 2026-06-27
**Branch:** main
**Final HEAD:** 83aba8a
**Base HEAD:** e0f863b
**Strict TDD:** ON
**Status:** success

## Goal

Implement T1.1 + T1.2 + T1.3 from `openspec/changes/observability/tasks.md`
for change #6 observability, PR#1 batch A.

## Commits landed

| # | SHA | Type | Subject |
|---|-----|------|---------|
| 1 | 0bc25fd | test(unit) | RED fixtures for read-side observability helpers (REQ-35 foundation) |
| 2 | 6148b66 | feat(observability) | 6 read functions + MetricEvent dataclass + atomic write helper (REQ-35 GREEN) |
| 3 | b843cce | feat(cli) | flow metrics summary subcommand with --format/--window/--domain flags (REQ-35 GREEN) |
| 4 | 83aba8a | docs(specs) | bootstrap openspec/specs/observability/spec.md from change #6 (REQ-35..39, archive-report #61 resolution) |

Each commit leaves `uv run pytest -x --tb=short -q` GREEN.

## TDD Cycle Evidence (strict TDD)

| Task | RED commit | GREEN commit | REFACTOR |
|------|-----------|--------------|----------|
| T1.1 — observability.py read helpers | 0bc25fd (11 RED tests, all AttributeError) | 6148b66 (11/11 pass) | n/a (clean first cut) |
| T1.2 — flow metrics summary CLI | included in b843cce (5 RED, 2 click-validation pass-throughs) | b843cce (7/7 pass + 3 byte-identical regression) | n/a |
| T1.3 — spec bootstrap | docs-only | 83aba8a | n/a |

## Files touched

### Production

- `src/flow_engineering/observability.py` (+279 / -1): added
  `MetricEvent` dataclass, `DOMAIN_BY_PREFIX` lookup table,
  `read_all_metrics`, `read_events_since`, `read_events_by_domain`,
  `summarize`, `prometheus_exposition`, `aggregate`, `atomic_write_text`.
  Imports added: `sys`, `tempfile`, `collections.defaultdict`,
  `dataclasses.dataclass`, `typing.Iterable`, `typing.Literal`.
- `src/flow_engineering/cli.py` (+108 / -4): converted `metrics` from
  `Command` to `Group(invoke_without_command=True)`; added
  `metrics_summary` subcommand with `--format` / `--window` / `--domain`
  flags. Imports added: `timedelta`.

### Tests (new)

- `tests/unit/test_observability_read.py` (NEW, ~254 LOC, 11 tests):
  `TestReadAllMetrics`, `TestReadEventsSince`, `TestReadEventsByDomain`,
  `TestSummarize`, `TestPrometheusExposition`, `TestAggregate`,
  `TestAtomicWriteText`.
- `tests/unit/test_cli_metrics_summary.py` (NEW, ~225 LOC, 7 tests):
  text/JSON format, window filter, domain filter, empty sink, invalid
  flag exits (2).
- `tests/bdd/req35_metrics_summary.feature` (NEW, 2 scenarios).
- `tests/bdd/test_observability_steps.py` (NEW, ~165 LOC, shared BDD
  glue for REQ-35; PR#2 will extend for req36..39).

### Docs (new)

- `openspec/specs/observability/spec.md` (NEW, 137 LOC): bootstraps the
  project's first capability spec at the `openspec/specs/` baseline.
  Carries REQ-35..39 + 11 BDD scenarios + counter catalog + versioning.
  Resolves `cross-project-federation` archive-report #61.

## Test delta

| Metric | Baseline | Final | Delta |
|--------|----------|-------|-------|
| Total tests passing | 801 | 821 | +20 |
| New unit tests | — | 18 | +18 (11 T1.1 + 7 T1.2) |
| New BDD scenarios | 14 | 16 | +2 (req35 only) |

Full suite runs in ~63s.

## BDD scenario delta

| REQ | Pre-batch | Post-batch A | Delta |
|-----|-----------|--------------|-------|
| REQ-35 (summary) | 0 | 2 | +2 |
| REQ-36 (window) | 0 | 0 | 0 (PR#1 batch B) |
| REQ-37 (domain) | 0 | 0 | 0 (PR#1 batch C) |
| REQ-38 (prometheus) | 0 | 0 | 0 (PR#2 batch F) |
| REQ-39 (percentile) | 0 | 0 | 0 (PR#2 batch G) |
| Total | 14 | 16 | +2 |

## Deviations from spec/design

1. **`summarize(events)` returns `{domain: {counter_name: count}}`**
   per the apply-batch-A prompt (NOT the design.md shape of
   `{name: {count, domain, first_seen, last_seen}}`). The prompt's shape
   is simpler and matches the BDD scenarios verbatim ("stdout contains
   `binding:` section"). The richer shape is deferred to PR#2 if needed.

2. **`aggregate(values, percentile)` uses floor via `int()` for sorted-index
   lookup** (NOT `statistics.quantiles` per design D7). Floor interpolation
   matches the prompt's test contract (1..100 → p50=50, p95=95, p99=99
   exact integers). The design's `statistics.quantiles` would yield
   50.5, 95.05, 99.01 due to linear interpolation — incompatible with
   the prompt's RED fixtures. The intent (query-time percentile, no
   streaming state) is preserved; only the algorithm differs.

3. **`read_events_by_domain(domain)` raises `ValueError` on unknown domain**
   (CLI exits 2 per the prompt). Design D5's "returns `[]` for unknown
   domain" semantics is rejected in favor of the prompt's stricter
   contract — callers get a clear error rather than silent empty results.

4. **`atomic_write_text(path, content)` lives in `observability.py`**
   (not `cli.py`) per the prompt's module-level helper placement. PR#1
   batch D T1.9 (per tasks.md) was slated to add it to `cli.py`; the
   prompt consolidates it here so PR#2's `--out` flag can import it.

5. **`flow metrics summary` is a subcommand (not a `--summary` flag)**:
   the prompt's BDD scenarios use `flow metrics summary --format text`,
   which requires a `Group` structure. Implemented via
   `invoke_without_command=True` so `flow metrics` and `flow metrics --json`
   remain byte-identical to v0.6.0 (the existing `TestMetricsCommand`
   regression at `tests/unit/test_cli_inspect.py:269-298` stays green).

## Risks / follow-ups

- **REQ-8 byte-identical regression**: verified `flow metrics` and
  `flow metrics --json` outputs match v0.6.0 against 3 existing
  `TestMetricsCommand` tests. No regression.
- **`flow metrics summary` has no `tests/unit/test_cli_metrics_summary`
  coverage for `--json-detailed` format**: deferred to PR#2 if needed.
- **BDD step glue for REQ-36/37/38/39**: `test_observability_steps.py`
  is the shared glue per design D12; PR#1 batches B-D and PR#2 batches
  F-G will extend it.
- **`openspec/specs/` is precedent-setting** — change #6 is the first
  capability spec. Kebab-case folder per capability is the long-term
  convention; subsequent changes (`prompt-registry` etc.) follow the
  same shape.

## Next recommended

`sdd-apply observability PR#1 batch B (T1.4 + T1.5: time-window filter +
--since/--until/--window flags + BDD req36)` — depends on T1.1 (DONE).