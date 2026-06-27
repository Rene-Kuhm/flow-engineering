# Apply Progress: change #6 observability — PR#1 batch B

**Date:** 2026-06-27
**Branch:** main
**Base HEAD:** 83aba8a (post batch A)
**Final HEAD:** 27c8ae2
**Strict TDD:** ON
**Status:** success

## Goal

Implement T1.4 + T1.5 from `openspec/changes/observability/tasks.md` for
change #6 observability, PR#1 batch B: the time-window filter foundation
(`filter_by_window` + `parse_window` + `WINDOW_PATTERNS`) and the
`--since`/`--until`/`--window` CLI surface on `flow metrics summary`
plus 2 BDD scenarios (REQ-36).

## Commits landed

| # | SHA | Type | Subject |
|---|-----|------|---------|
| 1 | 89e7c72 | test(unit) | RED fixtures for window filter (REQ-36 foundation) |
| 2 | 2db59be | feat(observability) | filter_by_window + parse_window + WINDOW_PATTERNS (REQ-36 GREEN) |
| 3 | 27c8ae2 | feat(cli) | --window/--since/--until flags on flow metrics summary + BDD req36 (REQ-36 CLI surface) |

Each commit leaves `uv run pytest -x --tb=short -q` GREEN.

## TDD Cycle Evidence (strict TDD)

| Task | RED commit | GREEN commit | REFACTOR |
|------|-----------|--------------|----------|
| T1.4 — observability.py window filter | 89e7c72 (7 RED tests, AttributeError on WINDOW_PATTERNS) | 2db59be (7/7 pass + 1 WINDOW_PATTERNS table test) | n/a (clean first cut) |
| T1.5 — CLI --since/--until/--window | included in 27c8ae2 (3 RED tests, click.Choice rejects "30d" / "5x") | 27c8ae2 (3/3 pass + 10/10 full CLI suite) | n/a |
| T1.5 BDD REQ-36 | included in 27c8ae2 (2 RED scenarios, JSON parse error on empty + timedelta NameError) | 27c8ae2 (4/4 BDD scenarios pass) | n/a |

## Files touched

### Production

- `src/flow_engineering/observability.py` (+99 / -0): added `WINDOW_PATTERNS`
  table (4 presets: 1h/24h/7d/30d), `parse_window(window) -> int` (presets +
  custom `<int><h|d>` format, case-insensitive, raises `ValueError` on
  invalid input), `filter_by_window(events, window, *, now=None)` (rolling
  semantics per D4; inclusive on the lower boundary; `now` is keyword-only
  for testability). Imports added: `time as _time`.

- `src/flow_engineering/cli.py` (+50 / -19): switched `metrics_summary`'s
  `--window` from `click.Choice(["1h", "24h", "7d"])` to a free-form string
  option (validated at runtime via `observability.parse_window`), widened
  the underlying `SUMMARY_WINDOW_CHOICES` to the 4 presets via
  `list(observability.WINDOW_PATTERNS.keys())`, added `--since` and
  `--until` ISO 8601 flags reusing the existing `_parse_since` helper
  (`cli.py:1103`). Window filtering delegates to the new
  `observability.filter_by_window()`; since/until filtering is in-memory
  epoch comparison. Invalid values emit a stderr error and exit 2 per D9.

### Tests (new + extended)

- `tests/unit/test_observability_window.py` (NEW, +113 LOC, 8 tests):
  `TestWindowPatterns`, `TestParseWindow` (5 tests: 1h/24h/7d presets +
  custom 12h + 3d format + 3 invalid-format raises), `TestFilterByWindow`
  (2 tests: rolling-window filter + explicit-now param testability).
- `tests/unit/test_cli_metrics_summary.py` (EXTEND, +77 LOC, 3 new tests):
  `TestSummaryWindowAndSinceUntil` (3 tests: 30d window keeps events in
  range, invalid "5x" exits 2, --since/--until JSON filter).

### BDD (new + extended)

- `tests/bdd/req36_metrics_window.feature` (NEW, 16 LOC, 2 scenarios):
  --window 1h filters to last 1 hour; --since ISO8601 filters to events
  after timestamp.
- `tests/bdd/test_observability_steps.py` (EXTEND, +152 LOC): added 2
  scenario bindings (test_req36_window_1h + test_req36_since_iso8601),
  2 new Given steps (`given_5_events_spanning_3_days_window`,
  `given_5_events_spanning_3_days_for_since`), 2 new When steps
  (`when_run_metrics_summary_window_1h_text`,
  `when_run_metrics_summary_since_iso_json`), 2 new Then steps
  (`then_stdout_contains_only_most_recent_counter`,
  `then_stdout_json_contains_exactly_2_events`). Imports added: `timedelta`.

## Test delta

| Metric | Baseline (post batch A) | Final | Delta |
|--------|------------------------|-------|-------|
| Total tests passing | 821 | 834 | +13 |
| New unit tests | — | 11 | +11 (8 T1.4 + 3 T1.5) |
| New BDD scenarios | 16 | 18 | +2 (REQ-36) |

Full suite runs in ~63s.

## BDD scenario delta

| REQ | Pre-batch | Post-batch B | Delta |
|-----|-----------|--------------|-------|
| REQ-35 (summary) | 2 | 2 | 0 |
| REQ-36 (window) | 0 | 2 | +2 |
| REQ-37 (domain) | 0 | 0 | 0 (PR#1 batch C) |
| REQ-38 (prometheus) | 0 | 0 | 0 (PR#2 batch F) |
| REQ-39 (percentile) | 0 | 0 | 0 (PR#2 batch G) |
| Total | 16 | 18 | +2 |

## LOC delta

```
src/flow_engineering/cli.py             |  69 +++++++++++----
src/flow_engineering/observability.py   |  99 +++++++++++++++++++++
tests/bdd/req36_metrics_window.feature  |  16 ++++
tests/bdd/test_observability_steps.py   | 152 +++++++++++++++++++++++++++++++-
tests/unit/test_cli_metrics_summary.py  |  77 +++++++++++++++-
tests/unit/test_observability_window.py | 113 ++++++++++++++++++++++++
6 files changed, 507 insertions(+), 19 deletions(-)
```

Net: +488 LOC. Forecast was ~460 — within the ±10% band (the BDD glue
file grew slightly more than the prompt's ~150 LOC estimate because the
REQ-36 scenarios use the new 1h-rolling semantics + --since ISO scenario
which each need their own Given/When/Then glue).

## Deviations from spec/design

1. **`--window` flag switched from `click.Choice` to a free-form string**.
   The prompt requires the flag to accept BOTH presets (1h/24h/7d/30d) AND
   custom `<int><h|d>` format (e.g. "12h", "3d"). `click.Choice` can only
   model a fixed enum, so validation moved to runtime via
   `observability.parse_window()` in the handler. Invalid values still
   exit 2 (D9) — verified by both the new
   `test_metrics_summary_with_invalid_window_exits_2` and the existing
   `test_metrics_summary_invalid_window_exits_2` regression test.

2. **`SUMMARY_WINDOW_CHOICES` is now derived from `WINDOW_PATTERNS.keys()`**
   instead of being a hardcoded `["1h", "24h", "7d"]` list. This widens
   the accepted preset set to include 30d, matching the prompt's
   `WINDOW_PATTERNS` constant. The CLI's `--window` flag now accepts
   `1h|24h|7d|30d` via this auto-derivation.

3. **`--since` / `--until` ISO 8601 validation reuses the existing
   `_parse_since` helper** (`cli.py:1103`) per design D4's note. Invalid
   ISO strings emit a stderr error and exit 2 (D9). The prompt's REQ-36
   bonus surface is fully wired: `--since=<iso>`, `--until=<iso>`, and
   `--window=<preset|custom>` all compose in the in-memory filter pipeline.

4. **No `_resolve_window` helper** was extracted — the design's
   `Algorithm Details` suggested factoring out a `_resolve_window`
   helper, but for PR#1 the inline resolution is ~10 LOC and the
   helper wouldn't have any other callers until PR#2's `--prometheus`
   path (T2.3). Deferred to PR#2 if needed.

5. **The BDD step for `--since` ISO scenario** is a hardcoded
   `when_run_metrics_summary_since_iso_json` step rather than a generic
   parser. Mirrors the pattern set by batch A's
   `when_run_metrics_summary_text`. A generic parser (e.g. `I run
   \`flow metrics summary <args>\``) is deferred to PR#1 batch D if
   the BDD glue file grows past 400 LOC.

## Risks / follow-ups

- **W23 carry-forward (REQ-36)**: `parse_window` raises `ValueError` for
  ALL invalid input, not just unregistered presets. The CLI catches and
  exits 2; batch A's `TestSummaryInvalidFlags` regression test covers
  the "garbage" case. Verified GREEN.
- **No interaction with `--prometheus` (REQ-38 / T2.3)**: `--window`
  already works in the `flow metrics summary` filter pipeline, so the
  PR#2 composition wiring is a trivial pass-through — no extra work
  needed in batch F.
- **No interaction with `--domain` (REQ-37 / T1.7)**: `--window` and
  `--domain` compose in the same in-memory filter pipeline (verified
  by the existing `test_metrics_summary_with_domain_filter` staying
  green). The flag-AND composition design D4 is fully realized.
- **`--since` / `--until` with `--until < --since`**: returns empty
  results, exits 0 (D8 default-empty). The summary path emits
  `"No metrics recorded yet."` for the text default; the JSON path
  emits `{}`. Verified by the existing `TestSummaryEmptySink` test
  contract.
- **`openspec/specs/observability/spec.md` (T1.3 from batch A) does not
  document the `WINDOW_PATTERNS` table or the `--since`/`--until` flags**
  — the spec mentions REQ-36 conceptually but the new
  `parse_window` + `filter_by_window` helpers and the custom-format
  extension are net-new. A follow-up doc patch in PR#1 batch E
  (T1.10) is appropriate but not blocking.
- **`SUMMARY_DOMAIN_CHOICES` is still only 4 values** (binding/drift/
  vector/snapshot). The spec's 8-value `ACCEPTED_DOMAINS` expansion
  (backfill/federated/metadata/engine) lands in PR#1 batch C (T1.7).
  Out of scope for batch B per the prompt.

## Next recommended

`sdd-apply observability PR#1 batch C (T1.6 + T1.7: cross-domain slice —
`validate_counter_in_catalog` helper + `--domain` widening to 8 values
+ BDD req37)` — depends on T1.1 (DONE) and the T1.4 work (DONE).
