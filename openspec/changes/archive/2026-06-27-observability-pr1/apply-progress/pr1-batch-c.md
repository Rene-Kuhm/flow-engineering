# Apply Progress: change #6 observability — PR#1 batch C

**Date:** 2026-06-27
**Branch:** main
**Base HEAD:** 27c8ae2 (post batch B)
**Final HEAD:** 38df3db
**Strict TDD:** ON
**Status:** success

## Goal

Implement T1.6 + T1.7 from `openspec/changes/observability/tasks.md` for
change #6 observability, PR#1 batch C: the cross-domain slice foundation
(`ALL_DOMAINS` + `validate_domain` + `DOMAIN_BY_PREFIX` 8-value expansion)
and the `--domain` widening from 4 to 8 values on `flow metrics summary`
plus 2 BDD scenarios (REQ-37).

## Commits landed

| # | SHA | Type | Subject |
|---|-----|------|---------|
| 1 | 6f3dd4c | test(unit) | RED fixtures for cross-domain slice expansion (REQ-37 foundation) |
| 2 | 7579580 | feat(observability) | DOMAIN_BY_PREFIX 8-value expansion + validate_domain helper (REQ-37 GREEN) |
| 3 | 38df3db | feat(cli) | --domain widening to 8 values on flow metrics summary + BDD req37 (REQ-37 CLI surface) |

Each commit leaves `uv run pytest -x --tb=short -q` GREEN (the RED commit
6f3dd4c is RED-by-design — 6 of 7 tests fail; the 7th is a regression
check that passes against batch A's implementation, mirroring the pattern
from batches A and B).

## TDD Cycle Evidence (strict TDD)

| Task | RED commit | GREEN commit | REFACTOR |
|------|-----------|--------------|----------|
| T1.6 — observability.py DOMAIN/validate | 6f3dd4c (8 RED fixtures; 6 fail with AttributeError + ValueError, 1 passes as regression) | 7579580 (8/8 pass + 834 existing) | n/a (clean first cut) |
| T1.7 — CLI --domain widening + BDD req37 | included in 38df3db (3 unit + 2 BDD RED fixtures in the same commit) | 38df3db (3/3 unit + 2/2 BDD pass; full suite 847 GREEN) | n/a |

T1.7 follows the single-commit per work-unit convention from
`work-unit-commits` (impl + tests + BDD in one commit) because the
--domain widening is a small, atomic CLI surface change. The RED
fixtures were written first within the commit (per the prompt's commit
plan note "(single commit per work-unit-commits convention)").

## Files touched

### Production

- `src/flow_engineering/observability.py` (+46 / -0): added `"engine_": "engine"`
  prefix entry to `DOMAIN_BY_PREFIX` (10 prefix entries → 8 unique domain
  values), added `ALL_DOMAINS: tuple[str, ...] = (binding, backfill,
  drift, vector, federated, snapshot, metadata, engine)` constant
  (canonical 8-value list for CLI help-text rendering and validation),
  added `validate_domain(domain) -> str` helper (returns the domain
  when valid; raises `ValueError` with a helpful message listing every
  valid domain otherwise).

- `src/flow_engineering/cli.py` (+12 / -5): changed
  `SUMMARY_DOMAIN_CHOICES` from the hardcoded 4-value list
  `["binding", "drift", "vector", "snapshot"]` to derive from
  `observability.ALL_DOMAINS` (8 values); updated `--domain` help text
  to list all 8 valid domains via `"|".join(observability.ALL_DOMAINS)`;
  added `domain.lower()` normalization + `validate_domain()` runtime
  fallback in the `metrics_summary` handler (click.Choice accepts mixed
  case, but `DOMAIN_BY_PREFIX` keys are lowercase).

### Tests (new + extended)

- `tests/unit/test_observability_domain.py` (NEW, ~181 LOC, 8 tests):
  `TestDomainByPrefixExpansion` (4 tests — `DOMAIN_BY_PREFIX` covers all
  8 unique values; `ALL_DOMAINS` includes the 4 originals + 4 new
  extensions; `ALL_DOMAINS` has exactly 8 entries),
  `TestValidateDomain` (2 tests — accepts all 8; raises with helpful
  message listing valid domains), `TestReadEventsByDomainExpansion`
  (2 tests — backfill filter regression check; engine filter returns
  empty in v1 per REQ-42 deferred scope).

- `tests/unit/test_cli_metrics_summary.py` (EXTEND, +89 LOC, 3 new tests):
  `TestSummaryDomainFilterWidening` (3 tests — `--domain=backfill`
  filters to backfill_* only; `--domain=engine` returns empty
  default-empty contract; invalid `--domain` exits 2 with helpful
  message).

### BDD (new + extended)

- `tests/bdd/req37_metrics_domain.feature` (NEW, 17 LOC, 2 scenarios):
  --domain snapshot shows only snapshot_* counters (12 events seeded,
  filtered to 3 snapshot counters); no --domain shows all 8 domains
  aggregated (24 events seeded including 3 fake engine_* counters for
  the REQ-42 reserved slot).

- `tests/bdd/test_observability_steps.py` (EXTEND, +252 LOC): added 2
  scenario bindings (test_req37_domain_snapshot + test_req37_no_domain
  _shows_all_8), 2 new Given steps (`given_12_events_with_3_distinct
  _counters_per_domain` + `given_24_events_across_8_domains`), 1 new
  When step (`when_run_metrics_summary_domain_snapshot_text`), 3 new
  Then steps (`then_stdout_contains_only_3_snapshot_counters` +
  `then_stdout_does_not_contain_other_domain_headers` +
  `then_stdout_contains_all_8_domain_headers`).

## Test delta

| Metric | Baseline (post batch B) | Final | Delta |
|--------|------------------------|-------|-------|
| Total tests passing | 834 | 847 | +13 |
| New unit tests | — | 11 | +11 (8 T1.6 + 3 T1.7) |
| New BDD scenarios | 18 | 20 | +2 (REQ-37) |

Full suite runs in ~63s.

## BDD scenario delta

| REQ | Pre-batch | Post-batch C | Delta |
|-----|-----------|--------------|-------|
| REQ-35 (summary) | 2 | 2 | 0 |
| REQ-36 (window) | 2 | 2 | 0 |
| REQ-37 (domain) | 0 | 2 | +2 |
| REQ-38 (prometheus) | 0 | 0 | 0 (PR#2 batch F) |
| REQ-39 (percentile) | 0 | 0 | 0 (PR#2 batch G) |
| Total | 18 | 20 | +2 |

## LOC delta

```
src/flow_engineering/cli.py                       |  12 +++++++--
src/flow_engineering/observability.py             |  46 ++++++++++++++++++++++
tests/bdd/req37_metrics_domain.feature            |  17 +++++++
tests/bdd/test_observability_steps.py             | 252 +++++++++++++++++++++++++++++++++++++++++++-
tests/unit/test_cli_metrics_summary.py            |  89 +++++++++++++++++++++++++-
tests/unit/test_observability_domain.py           | 181 ++++++++++++++++++++++++++++++++++++++
6 files changed, 587 insertions(+), 10 deletions(-)
```

Net: +577 LOC. Forecast was ~370 LOC — exceeded by ~56% because the BDD
step glue file grew more than expected (the no-`--domain` scenario
required a 24-event Given step with explicit domain names; the all-8-
domain-headers Then step required listing 8 distinct headers). Within
the work-unit-commits envelope (≤400 LOC per commit per `chained-pr`
strategy); the 3 commits individually are all well under the budget
(commit 1: +181 LOC; commit 2: +46 LOC; commit 3: +370 LOC).

## Deviations from spec/design

1. **Used existing prefix→domain mapping structure** instead of the
   prompt's suggested `dict[str, str]` shape with keys-as-domains.
   The existing `DOMAIN_BY_PREFIX` (prefix → domain) is required by
   `_domain_for_counter` and `read_events_by_domain`; rewriting the
   structure would have broken the batch A implementation. The 8-value
   expansion was achieved by ADDING `"engine_": "engine"` to the
   existing table (10 prefix entries → 8 unique domain values). The
   spec's intent (8 accepted domains) is fully satisfied.

2. **Added `ALL_DOMAINS` as a separate constant** rather than
   deriving from `DOMAIN_BY_PREFIX.keys()`. The prompt's example
   `tuple(DOMAIN_BY_PREFIX.keys())` would return prefixes (e.g.,
   `"binding_"`), not domain values (e.g., `"binding"`) — the
   prompt's example has a typo. `ALL_DOMAINS` is now a hand-curated
   8-tuple of the canonical domain values, used by the CLI help text
   and `validate_domain` for case-sensitive lookup.

3. **Engine domain wired via fake `engine_*` counters in the BDD
   Given step** for scenario 2 (REQ-37). No real engine_* counters
   exist in v1 (REQ-42 deferred to v1.1), but the BDD scenario
   requires "all 8 domain headers" to appear in the no-`--domain`
   default output. The Given step writes 3 fake engine_* events
   (queue depth, startup, errors) matching the REQ-42 deferred
   counter names; this exercises the reserved slot without requiring
   production code changes.

4. **`--domain` flag normalization**: click.Choice with
   `case_sensitive=False` accepts mixed-case values, but
   `DOMAIN_BY_PREFIX` keys are lowercase. Added explicit
   `domain.lower()` normalization in the handler before calling
   `validate_domain` + `read_events_by_domain`. Validates the spec
   intent (case-sensitive domain values) without rejecting
   mixed-case input at the CLI boundary.

5. **T1.7 lands as a single commit** (impl + tests + BDD) per the
   prompt's commit plan note "(single commit per work-unit-commits
   convention)". RED fixtures were written first within the commit;
   the GREEN step landed the CLI widening + step glue in the same
   commit. Diff is 370 LOC — within the ≤400-LOC work-unit envelope
   but tight; future T1.8/1.9 (PR#1 batch D) should split if their
   scope grows.

## Risks / follow-ups

- **`engine_*` counter names are NOT in the production catalog** —
  the BDD scenario uses fake names (`engine_queue_depth`,
  `engine_startup_ms`, `engine_errors_total`). When REQ-42 lands
  (v1.1), the names SHOULD match the catalog or the BDD step will
  need to be updated.
- **`validate_domain` is redundant at the CLI layer** when
  `click.Choice` is active (the choice validation already exits 2
  on invalid values). The helper is exposed as a public API for
  non-Click callers (e.g., Python embedders, future REQ-40
  label-based query filter) and for explicit runtime validation in
  fallback paths. Cost: ~20 LOC of observability surface.
- **`SUMMARY_DOMAIN_CHOICES` is now derived from `ALL_DOMAINS`**
  — adding a new domain to `ALL_DOMAINS` automatically widens the
  CLI's `--domain` flag. Verified by the new
  `test_metrics_summary_with_domain_filter_backfill` test passing.
- **`openspec/specs/observability/spec.md` (T1.3 from batch A) does
  not document `ALL_DOMAINS` / `validate_domain`** — the spec
  mentions REQ-37 conceptually but the explicit 8-value expansion
  is net-new. A follow-up doc patch in PR#1 batch E (T1.10) is
  appropriate but not blocking.
- **`ALL_DOMAINS` order is stable** — used for CLI `--help`
  rendering and `validate_domain` error messages. The order matches
  the spec's table (binding, backfill, drift, vector, federated,
  snapshot, metadata, engine).

## Next recommended

`sdd-apply observability PR#1 batch D (T1.8 + T1.9: default-empty
handling + atomic write helper)` — depends on T1.1 (DONE), T1.4
(DONE), and T1.6 (DONE).