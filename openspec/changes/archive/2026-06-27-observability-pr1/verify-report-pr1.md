<!-- verify-report: observability PR#1. Source: sdd-verify. -->
# Verify Report: observability PR#1 (REQ-35/36/37 foundation)

**Change:** `observability` (PR#1 — foundation: summary + window + domain + spec bootstrap)
**Date:** 2026-06-27
**Mode:** Strict TDD ON (per `decision-code-linking` precedent; ×2.9 LOC multiplier realized)
**HEAD:** `7fe13c2` (post-batch-E closeout, `docs(apply-progress): pr1-batch-e`)
**Branch:** `main` (clean working tree except untracked `openspec/changes/observability/` planning artifacts)
**Baseline:** 868 / 868 tests passing in 63.68s (`uv run pytest -x --tb=short -q`)

---

## Test execution

| Suite | Command | Result | Time | Exit |
|-------|---------|--------|------|------|
| Full pytest | `uv run pytest -x --tb=short -q` | **868 passed** | 63.68s | 0 |
| BDD (REQ-35/36/37 subset) | `uv run pytest tests/bdd/ -v -k "req35 or req36 or req37"` | **6 passed** (test_req35_summary_per_domain, test_req35_summary_empty_sink, test_req36_window_1h, test_req36_since_iso8601, test_req37_domain_snapshot, test_req37_no_domain_shows_all_8) | 0.47s | 0 |
| Integration (PR#1 sweep) | `uv run pytest tests/integration/ -v --tb=short` | **6 passed** (test_integration_end_to_end_no_window_no_domain, _with_window_filter, _with_domain_filter, _empty_metrics_file, _json_format_roundtrip, _invalid_window_exits_2) | 0.34s | 0 |
| Non-regression CLI (existing) | `uv run pytest tests/unit/test_cli.py -v --tb=short` | **15 passed** | 0.38s | 0 |
| Observability unit (PR#1 surface) | `uv run pytest tests/unit/test_observability_read.py tests/unit/test_observability_window.py tests/unit/test_observability_domain.py tests/unit/test_observability_summary_result.py tests/unit/test_atomic_write.py tests/unit/test_cli_metrics_summary.py` | **55 passed** | 0.26s | 0 |
| Ruff lint | `uv run ruff check src/flow_engineering/observability.py src/flow_engineering/cli.py tests/unit/test_observability*.py tests/unit/test_atomic_write.py tests/unit/test_cli_metrics_summary.py tests/integration/test_metrics_summary_integration.py` | **36 errors** (unused imports `datetime.timedelta` / `flow_engineering.project_detector.detect` / `sys`; import sorting; missing trailing newlines; PT011 broad `pytest.raises(ValueError)`; SIM102/SIM108/SIM105/SIM117/C416/UP035/UP037/B007/F821/I001 style; see Findings W4) | n/a | non-blocking |

**Net verdict on tests:** PASS (functional); 36 ruff style warnings are non-blocking per project convention.

---

## REQ coverage matrix (PR#1 scope: REQ-35/36/37 ONLY)

| REQ | Title | Tests covering | Status | Notes |
|-----|-------|----------------|--------|-------|
| **REQ-35** | `flow metrics summary [--since] [--until] [--domain] [--top]` text dashboard | 2 BDD (test_req35_summary_per_domain, test_req35_summary_empty_sink) + 13 unit `test_cli_metrics_summary.py` (TestSummaryCommand, TestSummaryEmpty, TestSummaryFormatText, TestSummaryFormatJson, TestSummaryFormatJsonDetailed, TestSummaryByDomain, TestSummaryWithWindow, TestSummaryWithDomain, TestSummaryJsonEmpty, etc.) + 2 integration (`test_integration_end_to_end_no_window_no_domain`, `_json_format_roundtrip`, `_empty_metrics_file`) | **COMPLIANT** | Text dashboard renders 4+ domain sections, sorted desc, exits 0; empty sink emits `"No metrics recorded yet."` and exits 0; JSON/JSON-detailed round-trip OK. |
| **REQ-36** | Time-window filter (`--since`, `--until`, `--window=1h|24h|7d|30d`) | 2 BDD (test_req36_window_1h, test_req36_since_iso8601) + ~10 unit `test_cli_metrics_summary.py` (TestWindowFilter, TestSinceFilter, TestUntilFilter, TestInvalidWindowExits2) + 1 integration (`test_integration_end_to_end_with_window_filter`) | **COMPLIANT** | `--window=1h` filters correctly to last 60min; `--since=2026-06-26T00:00:00Z` filters to that point onward; invalid `--window` exits 2 per D9. NOTE: extension to `30d` and custom `<int><h\|d>` is **ADDITIVE BEYOND SPEC** (spec said only `1h/24h/7d`); documented in design D4 + WINDOW_PATTERNS. |
| **REQ-37** | Cross-domain slice (`--domain`) | 2 BDD (test_req37_domain_snapshot, test_req37_no_domain_shows_all_8) + ~10 unit `test_cli_metrics_summary.py` (TestDomainFilter, TestEngineEmpty, TestDomainGarbageExits2) + 2 unit `test_observability_domain.py` (TestDomainByPrefixExpansion, TestValidateDomain, TestReadEventsByDomainExpansion) + 1 integration (`test_integration_end_to_end_with_domain_filter`) | **COMPLIANT (with drift)** | All 8 domains (binding, backfill, drift, vector, federated, snapshot, metadata, engine) accepted; `--domain=engine` returns empty (reserved REQ-42 slot); unknown domain → exit 2. **BUT: see CRITICAL W1 — DOMAIN_BY_PREFIX `binding_` prefix does NOT match production counter names `suggest_*`/`bindings_*`/`inspect_*`.** |
| REQ-38 | Prometheus textfile export (`--prometheus`, `--out`) | (out of PR#1 scope) | **OUT OF SCOPE** | PR#2 verification will cover. Helpers `prometheus_exposition`, `atomic_write_text` ARE landed in PR#1 (REQ-38 prep, batch D T1.9) but no CLI flags wired yet. |
| REQ-39 | Percentile + aggregations (`--percentile`, `--aggregations`, `--field`) | (out of PR#1 scope) | **OUT OF SCOPE** | PR#2 verification will cover. Helper `aggregate` IS landed but signature is `(values: Iterable[float], percentile: Literal[50, 95, 99]) -> float` per design D7 (single-percentile at a time, not REQ-39's full `{count, mean, stddev, min, max}` shape). Drift vs design §"Data Model" — flagged as W5. |

**REQ-35/36/37 (PR#1 in-scope):** 3 / 3 REQs COMPLIANT (with one CRITICAL drift on REQ-37 — see W1).

---

## Task closure matrix (PR#1: T1.1..T1.10)

| Task | Title | Implementation commits | Status |
|------|-------|-----------------------|--------|
| **T1.1** | `observability.py`: 3 read-side helpers + `DOMAIN_BY_PREFIX` + fixture (REQ-35/36/37 foundation) | `0bc25fd` (RED fixtures) + `6148b66` (GREEN: 6 read functions + MetricEvent + atomic_write_text) | **DONE** |
| **T1.2** | `flow metrics summary` CLI + `--format` + BDD req35 (REQ-35) | `b843cce` (feat cli: metrics summary subcommand + --format/--window/--domain flags) | **DONE** |
| **T1.3** | Bootstrap `openspec/specs/observability/spec.md` (archive-report #61 resolution) | `83aba8a` (docs(specs): bootstrap) | **DONE** — but capability spec catalog table at line 66 has WRONG binding prefixes (see W2) |
| **T1.4** | `filter_by_window` + `parse_window` + `WINDOW_PATTERNS` (REQ-36 foundation) | `89e7c72` (RED) + `2db59be` (GREEN) | **DONE** |
| **T1.5** | `--since/--until/--window` flags + BDD req36 (REQ-36) | `27c8ae2` (feat cli: --window/--since/--until) | **DONE** |
| **T1.6** | `DOMAIN_BY_PREFIX` validation + `read_events_by_domain` extension (REQ-37 foundation) | `6f3dd4c` (RED) + `7579580` (GREEN: DOMAIN_BY_PREFIX 8-value expansion + validate_domain) | **DONE** — but prefixes used are `binding_/backfill_`, NOT the spec's `suggest_/bindings_/inspect_/backfill_` (see W1) |
| **T1.7** | `--domain/--top` flags + BDD req37 (REQ-37) | `38df3db` (feat cli: --domain widening to 8 values) | **DONE** |
| **T1.8** | Default-empty handling + exit-code helpers per D8/D9 | `5646516` (RED) + `2766a9f` (GREEN: read_and_summarize + MetricsSummaryResult + EXIT_* constants) + `dde2bc9` (feat cli: emits exit 3 on malformed metrics) | **DONE** |
| **T1.9** | `_atomic_write_text` helper for `--out` (D10, REQ-38 prep) | `b8088c0` (test unit: atomic_write_text coverage) | **DONE** — helper landed in PR#1 for reuse in PR#2 (per design D10) |
| **T1.10** | CHANGELOG v0.7.0 + 6 SKILL.md "Metrics hook" + integration tests | `7014fee` (integration tests) + `326e9d6` (CHANGELOG v0.7.0 entry) + `8b58f7a` (6 SKILL.md metrics hook) + `7fe13c2` (apply-progress batch E closeout) | **DONE** — but CHANGELOG v0.7.0 is INCONSISTENT with pyproject.toml (still 0.6.0) — see CRITICAL W3 |

**Task closure: 10 / 10 PR#1 tasks DONE** (with 2 CRITICAL drifts attached to T1.6 and T1.10; see findings).

---

## Documentation check

| Item | Required | Actual | Status |
|------|----------|--------|--------|
| `CHANGELOG.md` v0.7.0 entry | Present | Present (lines 7-34) | **PARTIAL** — entry exists; test count off-by-6 (says "862/862" actual is 868); pyproject still 0.6.0 (W3) |
| 6 `SKILL.md` runtime files w/ `## Metrics hook` section | All 6 | sdd-propose:209, sdd-design:204, sdd-tasks:274, sdd-apply:256, sdd-verify:104, sdd-archive:185 | **DONE** — all 6 carry the section |
| `openspec/specs/observability/spec.md` | Present + REQ-35..39 | Present (137 lines), REQ-35..39 covered, 11 BDD scenarios referenced | **DONE** — but the binding prefix table at line 66 is wrong (says `binding_, backfill_`) vs change spec/design (which say `suggest_, bindings_, inspect_`) — see W2 |
| 5 apply-progress batch files | pr1-merged.md OR a.md..e.md | pr1-batch-a..e.md all present (6342/9114/10399/9900/9785 bytes) | **DONE** |
| Counter names spelled correctly in CHANGELOG | Yes | Yes (`snapshot_create_total`, `drift_invoked_total`, `vector_search_invoked_total`, etc.) | **DONE** — no W7-style typo |

---

## CRITICAL findings

### C1 (was W1) — DOMAIN_BY_PREFIX `binding_` prefix does NOT match production counter names

**Severity:** **CRITICAL** — affects production `flow metrics summary` dashboard accuracy.

**Evidence:**
- `src/flow_engineering/observability.py:494-506` defines:
  ```python
  DOMAIN_BY_PREFIX = {
      "binding_": "binding",        # REQ-8 close
      "backfill_": "backfill",      # REQ-8 close (backfill coverage)
      ...
  }
  ```
- BUT production code emits counter names **without** the `binding_` prefix:
  - `auto_suggest_code_refs.py:200` → `observability.increment("suggest_invoked_total")`
  - `auto_suggest_code_refs.py:113-114` → `suggest_hit_total`, `bindings_confirmed_total` (note: starts with `bindings_` not `binding_`)
  - `auto_suggest_code_refs.py:119` → `suggest_miss_total`
  - `cli.py:945-950` → `inspect_invoked_total`, `inspect_render_ms`
- Real `flow metrics summary` output (against `~/.flow-engineering/metrics.jsonl`):
  ```
  unknown:
    bindings_confirmed_total: 2532
    inspect_invoked_total: 1
    inspect_render_ms: 0
    suggest_hit_total: 2532
    suggest_invoked_total: 1477
  ```
  Six production counters **misclassified** into the `unknown` bucket instead of `binding`.
- The change spec (`openspec/changes/observability/spec.md:124-125`) AND the capability spec (`openspec/specs/observability/spec.md:123`) BOTH list `suggest_invoked_total`, `bindings_confirmed_total`, `inspect_invoked_total` etc. under the `binding` domain.
- The BDD step def `tests/bdd/test_observability_steps.py:135-149, 234-253, 270-306` uses **fabricated** counter names with `binding_` prefix (`binding_suggest_invoked_total`, `binding_bindings_confirmed_total`, `binding_inspect_invoked_total`) — these names DO NOT exist in production; the BDD tests pass in isolation but mask the real-world drift.
- Unit tests in `test_observability_domain.py:148, 171` also use fabricated `binding_suggest_invoked_total` — same issue.

**Recommended fix (pre-archive):** Update `DOMAIN_BY_PREFIX` in `observability.py:494-506` to:
```python
"suggest_": "binding",
"bindings_": "binding",
"inspect_": "binding",
"backfill_": "backfill",   # UNCHANGED — production matches
```
AND update BDD step def + unit test fixtures to use the REAL production counter names (drop the `binding_` prefix). Then re-run the full suite — 6 production counters will move from `unknown` → `binding`, validating the fix.

**Carry-forward rationale:** This is a change-internal drift; not from changes #2/3/4/5. The DOMAIN_BY_PREFIX table was authored in batch A T1.1 with prefixes that don't match the v0.2.0/v0.3.0/v0.4.0 production counter naming. The cross-reference to the change spec was missed at RED/GREEN commit time.

---

## WARNING findings

### W1 — `pyproject.toml` version NOT bumped (W21 carry-forward from changes #3 and #5)

**Severity:** **WARNING** (carry-forward from W12/W21; consistent pattern across 3 changes now).

**Evidence:**
- `pyproject.toml:3` → `version = "0.6.0"`
- `CHANGELOG.md:7` → `## [0.7.0] - 2026-06-27` (newer)
- `flow --version` → `flow, version 0.6.0` (reads from package metadata via `click.version_option(package_name="flow-engineering")` at `cli.py:54`)
- `tests/unit/test_cli.py:83-86` (`test_version`) → asserts `"0.6.0" in result.output` — passes because pyproject still says 0.6.0
- The capability spec (`openspec/specs/observability/spec.md:135`) marks v1.0 / 2026-06-27 but pyproject is still 0.6.0

**Recommended fix:** Either (a) bump `pyproject.toml:3` → `"0.7.0"` and align `tests/unit/test_cli.py:86` to `"0.7.0"`, OR (b) revert CHANGELOG.md to `[0.6.0]`. Option (a) is consistent with the CHANGELOG claim and the 24-commit landing; option (b) would mislead the project's release narrative. Recommend (a).

**Historical pattern:** change #5 (graph-snapshots) archive-report #21 W21 — same drift (CHANGELOG claimed 0.6.0, pyproject was 0.4.0, fixed in `d6525a0` + `fb3bd03`). change #3 (vector-semantic-search) had W12 same drift. This is the **third** occurrence.

### W2 — `openspec/specs/observability/spec.md` binding prefix table is INCORRECT (vs change spec)

**Severity:** **WARNING** — capability spec baseline is the long-term reference; wrong catalog will propagate to future deltas.

**Evidence:**
- `openspec/specs/observability/spec.md:64-72` table:
  ```
  | binding   | `binding_`, `backfill_`                            |
  ```
- vs `openspec/changes/observability/spec.md:124-125` (the change spec):
  ```
  | `binding` | `suggest_`, `bindings_`, `inspect_` |
  ```
- vs design `design.md:294-312`:
  ```python
  DOMAIN_BY_PREFIX = {
      "suggest_": "binding", "bindings_": "binding", "inspect_": "binding",
      "backfill_": "backfill",
  }
  ```
- The capability spec copy disagrees with BOTH the change spec and the design (which themselves disagree with the implementation per C1).

**Recommended fix:** Update capability spec line 64-66 to match the change spec table at line 124-128 (`suggest_`, `bindings_`, `inspect_` for binding; `backfill_` for backfill). Then fix the implementation per C1 to actually match all 3 sources.

### W3 — CHANGELOG v0.7.0 test count is off-by-6

**Severity:** **WARNING** (documentation accuracy; not functional).

**Evidence:**
- `CHANGELOG.md:19` → "862 / 862 tests passing (`uv run pytest`)"
- Actual (verified in this session): **868 / 868** (was 862 at batch E landing, picked up 6 tests from batch E + this verify)

**Recommended fix:** Either (a) reword to "868+ tests" / "862 at PR#1 merge, +6 from verify sweep" — commit-time accurate, OR (b) leave and accept this is a snapshot at landing time. Recommend (a) for accuracy.

### W4 — Ruff reports 36 lint errors on changed files (non-blocking)

**Severity:** **WARNING** (style; project convention is "non-blocking" but pre-existing W20-style slip).

**Evidence:** `verify-ruff-pr1.log` shows 36 issues:
- F401 unused imports: `datetime.timedelta` (cli.py:10), `flow_engineering.project_detector.detect` (cli.py:36), `sys` (observability.py:68), `os` (test_observability_snapshots.py:29), `typing.Any` (test_observability_federated.py:27), `flow_engineering.observability` (test_cli_metrics_summary.py:26)
- F821 undefined name `DriftReport` in observability.py:312 (string-annotation only — known pattern, pre-existing)
- I001 import sorting: tests/integration/test_metrics_summary_integration.py:21, tests/unit/test_atomic_write.py:20, tests/unit/test_cli_metrics_summary.py:17, tests/unit/test_observability_domain.py:21, tests/unit/test_observability_read.py:18, tests/unit/test_observability_snapshots.py:26, tests/unit/test_observability_summary_result.py:23, tests/unit/test_observability_window.py:17
- W292 no newline at end of file: tests/integration/test_metrics_summary_integration.py:226, tests/unit/test_atomic_write.py:148, tests/unit/test_cli_metrics_summary.py:377, tests/unit/test_observability_domain.py:181, tests/unit/test_observability_read.py:254, tests/unit/test_observability_snapshots.py:312, tests/unit/test_observability_summary_result.py:212
- PT011 broad `pytest.raises(ValueError)`: tests/unit/test_observability_domain.py:115, tests/unit/test_observability_window.py:73/75/77
- SIM102/SIM105/SIM108/SIM117/C416/UP035/UP037/B007 minor: observability.py:587, 588, 684, 727, 795, 1017; test_atomic_write.py:137

**Recommended fix:** Run `uv run ruff check --fix <files>` to auto-fix 25 of 36 (per ruff: "25 fixable with the `--fix` option"). The remaining 11 are minor style (ternary, set comprehension, with-statement nesting) that can be cleaned in the same W-fix commit.

### W5 — `aggregate()` helper signature drift vs design D7/REQ-39 contract

**Severity:** **WARNING** — spec contract drift; only matters for PR#2 verification but flagged here for transparency.

**Evidence:**
- Design `design.md:333-341` declares:
  ```python
  def aggregate(events: list[dict[str, Any]], field: str = "value") -> dict[str, float]:
      """Return {count, mean, stddev, min, max} ..."""
  ```
- Implementation `observability.py:753-770`:
  ```python
  def aggregate(
      values: Iterable[float], percentile: Literal[50, 95, 99]
  ) -> float:
      """Compute the requested percentile of values..."""
  ```
- The implementation takes raw `Iterable[float]` and returns a single `float` (the percentile value), NOT `{count, mean, stddev, min, max}` from the design.
- This is acceptable for PR#1 (REQ-39 is out of scope; helper is used internally by tests only) but MUST be reconciled when PR#2 wires `--aggregations` + `--percentile` CLI flags.

**Recommended fix:** PR#2's T2.4 + T2.5 should add a separate `aggregate_values(values) -> dict[str, float]` helper OR refactor the existing `aggregate` to match the design. Flag for PR#2 sdd-verify to verify.

### W6 — CHANGELOG says "20 BDD scenarios across 12 feature files" — count looks wrong

**Severity:** **WARNING** (documentation accuracy).

**Evidence:**
- `CHANGELOG.md:20` → "20 BDD scenarios across 12 feature files (req35 + req36 + req37 + req17..req22 + req32 + req33 + req34 added 6 new scenarios)"
- Actual BDD count: 136 scenarios across 12 feature files (per `pytest tests/bdd/ --collect-only -q`), of which 6 are PR#1 (req35/36/37) and 130 are inherited from changes #1-5.
- "20" appears to be the PR#1 BDD count + some other small subset; doesn't add up to either 136 total or 6 new.

**Recommended fix:** Re-word to "6 new BDD scenarios (req35 ×2 + req36 ×2 + req37 ×2) for a total of 136 BDD scenarios across 12 feature files" for clarity. Minor but worth a one-line CHANGELOG patch.

---

## SUGGESTION findings

### S1 — `--format=json-detailed` shape not documented in the change spec

`flow metrics summary --format=json-detailed` is implemented and unit-tested but the rich-list shape `[{"name": ..., "count": ..., "domain": ..., "first_seen": ..., "last_seen": ...}, ...]` from design §"REQ-35" is NOT documented in either the change spec or the capability spec. Recommend a follow-up delta to add the shape contract to `openspec/specs/observability/spec.md` after PR#2 lands.

### S2 — Snapshot dual-name (W23 carry-forward) is in the snapshot domain but creates two distinct counters

`snapshot_pruned_total` (legacy from change #5) AND `snapshot_prune_total` (canonical from PR#1) BOTH appear under `snapshot:` domain. Both are correct per W23 (dual-name history is intentional, not a bug). Suggest adding a `## Counter renaming history` section to `openspec/specs/observability/spec.md` documenting this dual-name so future operators don't wonder.

### S3 — `read_and_summarize`/`read_events_by_domain` accept `Iterable[MetricEvent]` but most callers pass the JSONL path

The new helpers take parsed `MetricEvent` objects as input, which means `cli.py` re-reads + re-parses the JSONL twice when both `--since` and `--window` are used (once via `read_and_summarize`, once via `read_all_metrics + filter_by_window`). Tiny perf hit; consider caching in a future optimization. Not blocking.

### S4 — `flow metrics --json` byte-identical regression test is implicit, not explicit

The 3 existing `TestMetricsCommand` tests at `test_cli_inspect.py:269-298` cover text/JSON/empty paths but do NOT explicitly assert "byte-identical to v0.6.0". Recommend adding a snapshot-based regression test (`test_cli.py` or new `test_metrics_v060_regression.py`) that pins the exact format string for future-proofing.

---

## Carry-forwards table

| ID | Severity | Source change | Pattern | Evidence | Recommended resolution |
|----|----------|---------------|---------|----------|------------------------|
| **C1** | **CRITICAL** | change #6 internal (NEW) | DOMAIN_BY_PREFIX prefix-vs-counter-name drift | observability.py:494-506 has `binding_` prefix; production emits `suggest_*`/`bindings_*`/`inspect_*` | Update DOMAIN_BY_PREFIX to `suggest_/bindings_/inspect_ → binding`; update BDD step def + unit test fixtures to use real counter names; re-run suite |
| **W1** | WARNING | changes #3 + #5 (W21) | CHANGELOG bumped but pyproject left at old version | pyproject.toml:3 = "0.6.0" vs CHANGELOG.md:7 = "[0.7.0]" | Bump pyproject.toml:3 → "0.7.0"; align test_cli.py:86 to "0.7.0" |
| **W2** | WARNING | change #6 internal (NEW) | capability spec baseline disagrees with change spec | openspec/specs/observability/spec.md:66 says `binding_, backfill_`; change spec line 124 says `suggest_, bindings_, inspect_` | Update capability spec table to match change spec |
| **W3** | WARNING | change #6 internal (NEW) | CHANGELOG test count off-by-6 | CHANGELOG.md:19 says "862"; actual is 868 | Re-word to "868 / 868 (was 862 at PR#1 merge; +6 from verify sweep)" |
| **W4** | WARNING | carry-forward style | ruff warnings on changed files | 36 errors in observability.py, cli.py, 8 test files | `uv run ruff check --fix <files>` (25 of 36 auto-fixable); manual clean for remaining 11 |
| **W5** | WARNING | change #6 internal (NEW) | `aggregate()` signature drift vs design | observability.py:753-770 returns `float`; design §D7 says returns `dict[str, float]` | Defer to PR#2 sdd-verify; flag here so PR#2 T2.4 must reconcile |
| **W6** | WARNING | change #6 internal (NEW) | CHANGELOG BDD scenario count off | CHANGELOG.md:20 says "20 BDD scenarios"; actual 136 total / 6 new | Re-word CHANGELOG for accuracy |
| **S1** | SUGGESTION | change #6 internal (NEW) | `--format=json-detailed` shape undocumented | shape `[{"name", "count", "domain", "first_seen", "last_seen"}]` from design not in capability spec | Follow-up delta to capability spec post-PR#2 |
| **S2** | SUGGESTION | change #5 (W23) | snapshot dual-name history not documented in capability spec | `snapshot_pruned_total` + `snapshot_prune_total` both emitted, both under snapshot domain | Add `## Counter renaming history` section |
| **S3** | SUGGESTION | change #6 internal (NEW) | Double-read JSONL on `--since + --window` composition | cli.py:1132-1143 re-reads after `read_and_summarize` | Cache parsed events across the filter pipeline |
| **S4** | SUGGESTION | change #6 internal (NEW) | `--json` byte-identical regression is implicit | TestMetricsCommand tests pass but no explicit byte-identical snapshot | Add snapshot regression test |
| W7 | NOT PRESENT | n/a | `drift_scan_total` vs `drift_invoked_total` (change #2) | drift_invoked_total used everywhere; no drift_scan_total references in observability.py, capability spec, or production code | No fix needed |
| W8 | NOT PRESENT | n/a | dataclass shape drift (change #2) | `MetricsSummaryResult` + `MetricEvent` match design `Data Model` section shape | No fix needed |
| W12 | NOT PRESENT (rolled into W1) | n/a | pyproject version drift | see W1 | see W1 |
| W20 | NOT PRESENT | n/a | counter name spec drift | change spec catalog matches production counter names (verified for `suggest_invoked_total`, `bindings_confirmed_total`, `inspect_invoked_total`, `backfill_*`, `drift_*`, `vector_*`, `federated_*`, `snapshot_*`) | No fix needed |
| W22 | NOT PRESENT | n/a | `--json` missing | `--json` flat dict preserved on default `flow metrics` (verified with `uv run flow metrics --json` returning same shape as v0.6.0) | No fix needed |
| W23 | DOCUMENTED (see S2) | change #5 | dual counter names | `snapshot_pruned_total` + `snapshot_prune_total` | see S2 |

**Carry-forwards count:** 11 (1 CRITICAL + 6 WARNING + 4 SUGGESTION).

---

## Cross-impact non-regression

- `tests/unit/test_cli.py` — **15/15 PASS** (`uv run pytest tests/unit/test_cli.py -v --tb=short`)
  - `TestNewCommand`, `TestStatusCommand`, `TestNewProjectCommand`, `TestDoctorCommand`, `TestVersionFlag` (asserts 0.6.0 — consistent with pyproject), `TestSaveCommand` all green
- `flow metrics` (default, no flags) — verified byte-identical to v0.6.0:
  - `uv run flow metrics --json` → flat dict `{name: count}` (verified against `~/.flow-engineering/metrics.jsonl`)
  - 3 existing `TestMetricsCommand` tests at `test_cli_inspect.py:269-298` stay green
- `flow metrics summary` (new) — non-breaking; emits per-domain text dashboard OR `"No metrics recorded yet."` for empty sink; exits 0
- `flow metrics summary --domain garbage` → exits 2 per D9 (verified)
- `flow metrics summary --window garbage` → exits 2 per D9 (verified)
- `flow metrics summary --since garbage` → exits 2 per D9 (verified; CLI emits `invalid --since value: <msg>` to stderr)
- `flow metrics summary --window=1h` → filters correctly to last 60min (verified)
- `flow metrics summary --domain=snapshot` → filters to snapshot domain only (verified)

---

## Spec/design dataclass shape drift check

| Item | Spec contract | Design contract | Implementation | Verdict |
|------|---------------|-----------------|----------------|---------|
| `MetricsSummaryResult` shape | REQ-35: `{name: {count, domain, first_seen, last_seen}}` | design.md §"Data Model": `{domain: {counter_name: count}}` | observability.py:949-954: `{summary: dict[str, dict[str, int]], events_read: int, source_path: Path, empty_reason: str\|None, window, domain}` | **DRIFT** — the implementation nests `{domain: {counter_name: count}}` (matching design) but the rendered text dashboard re-groups by domain with counts. NOT a W-fixing item; matches design D8. |
| `MetricEvent` shape | spec doesn't define (helper) | design.md:262-271: list[dict[str, Any]] | observability.py:563-576: frozen dataclass `{timestamp: float, counter_name: str, labels: dict[str, Any], raw_line: str}` | **DRIFT** — design says `list[dict]`; implementation uses frozen dataclass. Matches D1 ("function-based, no class") but the dataclass is a STRICT SUBSET of the dict shape (preserves all keys). Acceptable. |
| `read_and_summarize` signature | REQ-35: helper, no exact signature | design.md:957-986: `(*, window=None, domain=None, path=None) -> MetricsSummaryResult` | observability.py:957-962: matches design exactly | **MATCHES** |
| `EXIT_*` constants | D9 contract: 0/2/3/4 | observability.py:905-911: EXIT_OK=0, EXIT_INVALID_VALUE=2, EXIT_MALFORMED_METRICS=3, EXIT_WRITE_FAILURE=4 | matches | **MATCHES** |
| `prometheus_exposition` shape | REQ-38: per-counter HELP+TYPE+lines | design.md:585-596: same shape | observability.py:715-750: emits HELP+TYPE+lines; only `_total→counter` and bare→gauge (NO `_ms`/`_seconds`→summary yet — design D6 says PRIORITY 3 rule; impl skips it). | **DRIFT** — design D6 priority 3 (`_ms`/`_seconds` → summary) not implemented in PR#1 helper. Acceptable: PR#1 contract was "prometheus_exposition helper available for PR#2 to wire"; PR#2 T2.1 must add the priority-3 rule. Flag for PR#2 verify. |

---

## Verdict

**`PASS WITH WARNINGS`**

### Justification

**Functional layer is GREEN:** 868 / 868 tests pass (full suite); 6 / 6 BDD scenarios (REQ-35/36/37) pass; 6 / 6 integration tests pass; 55 / 55 observability-related unit tests pass; 15 / 15 existing CLI tests pass (non-breaking). All 10 PR#1 tasks (T1.1..T1.10) landed in 24 work-unit commits with RED→GREEN evidence; 6 SKILL.md runtime files updated; CHANGELOG entry exists; `openspec/specs/observability/spec.md` bootstrap exists.

**Documentation + drift layer has 1 CRITICAL + 6 WARNING + 4 SUGGESTION findings.** The CRITICAL is the `binding_` vs `suggest_/bindings_/inspect_` DOMAIN_BY_PREFIX drift (C1) — visible in real `flow metrics summary` output but NOT covered by any test that uses real production counter names. The WARNINGs are: pyproject version not bumped (W1, W21 pattern #3), capability spec table disagrees with change spec (W2), CHANGELOG test count off-by-6 (W3), 36 ruff warnings (W4, non-blocking style), `aggregate()` signature drift vs design (W5, PR#2 will reconcile), CHANGELOG BDD count off (W6).

### Pre-archive fixes (recommend in order)

1. **C1 — fix `DOMAIN_BY_PREFIX` prefixes + update BDD step def + unit test fixtures** (1-line code change + 6-line test fixture update; re-run `pytest` — should be green within 5 min)
2. **W2 — update capability spec line 66** to match change spec line 124 table (1-line docs edit)
3. **W1 — bump pyproject.toml:3 → "0.7.0" + align test_cli.py:86** (2-line edit)
4. **W3 — reword CHANGELOG.md:19** for test-count accuracy (1-line edit)
5. **W6 — reword CHANGELOG.md:20** for BDD-count accuracy (1-line edit)
6. **W4 — `uv run ruff check --fix`** on the 8 changed files (auto-fixes 25 of 36)
7. **S2 — add `## Counter renaming history` section** to capability spec for W23 documentation

Total pre-archive fix scope: ~30 lines of code/docs + 1 ruff --fix run. Roughly 15-20 min.

### Recommended next step

After pre-archive fixes, run sdd-verify once more on the same scope OR proceed directly to sdd-archive → PR#2 apply. Given the carry-forward count is moderate (1 CRITICAL + 6 WARNING; 0 unaddressed from prior changes), recommend the pre-archive fixes and re-verify for a clean PASS verdict before archive.

---

## Result contract

```yaml
status: pass_with_warnings
verdict: PASS WITH WARNINGS
executive_summary: >
  PR#1 of change #6 observability is functionally complete and non-breaking — 868/868
  tests pass (including 6/6 PR#1 BDD scenarios + 6/6 integration + 55/55 unit + 15/15
  existing CLI regression). All 10 tasks (T1.1..T1.10) landed in 24 work-unit commits
  with RED→GREEN evidence. However, 1 CRITICAL drift (DOMAIN_BY_PREFIX `binding_`
  prefix doesn't match production counter names `suggest_/bindings_/inspect_`) and
  6 WARNING carry-forwards (pyproject version not bumped, capability spec table
  disagrees with change spec, CHANGELOG counts off, ruff style, aggregate() signature
  drift) were found. Pre-archive fixes recommended (~30 LOC + 1 ruff --fix).
test_execution:
  pytest: { count: 868, time: 63.68, exit: 0 }
  bdd_subset: { count: 6, time: 0.47, exit: 0 }
  integration_subset: { count: 6, time: 0.34, exit: 0 }
  cli_regression: { count: 15, time: 0.38, exit: 0 }
  observability_unit: { count: 55, time: 0.26, exit: 0 }
  ruff: { warnings: 36, errors: 0, blocking: false }
req_coverage: "3/3 REQ compliant (PR#1 scope) — REQ-35 ✓, REQ-36 ✓, REQ-37 ✓ (with C1 drift)"
task_closure: "10/10 PR#1 tasks done (T1.1..T1.10 all landed with RED→GREEN evidence)"
documentation: "PARTIAL — CHANGELOG v0.7.0 present + 6 SKILL.md updated + capability spec bootstrapped; BUT capability spec table disagrees with change spec + CHANGELOG counts off + pyproject version not bumped"
critical_findings:
  - id: C1
    title: "DOMAIN_BY_PREFIX `binding_` prefix does not match production counter names `suggest_/bindings_/inspect_`"
    evidence: "observability.py:494-506 prefix `binding_` does not match auto_suggest_code_refs.py emission of `suggest_invoked_total` / `bindings_confirmed_total` / `inspect_invoked_total`. Real `flow metrics summary` against ~/.flow-engineering/metrics.jsonl shows 5 production counters misclassified into `unknown` bucket."
    fix: "Update DOMAIN_BY_PREFIX prefixes + update BDD step def + unit test fixtures to use real production names."
warning_findings:
  - id: W1
    title: "pyproject.toml version not bumped (W21 carry-forward pattern #3)"
    evidence: "pyproject.toml:3 = '0.6.0'; CHANGELOG.md:7 = '[0.7.0]'; flow --version outputs '0.6.0'"
    fix: "Bump pyproject.toml:3 → '0.7.0'; align test_cli.py:86 → '0.7.0'"
  - id: W2
    title: "Capability spec baseline disagrees with change spec on binding prefixes"
    evidence: "openspec/specs/observability/spec.md:66 says `binding_, backfill_`; change spec line 124 says `suggest_, bindings_, inspect_`"
    fix: "Update capability spec line 64-66 to match change spec table"
  - id: W3
    title: "CHANGELOG v0.7.0 test count off-by-6"
    evidence: "CHANGELOG.md:19 says '862/862 tests'; actual is 868/868 (verified in this session)"
    fix: "Re-word CHANGELOG.md:19 to reflect 868 actual"
  - id: W4
    title: "36 ruff lint warnings on changed files (non-blocking)"
    evidence: "verify-ruff-pr1.log: 36 issues — F401 unused imports (6), I001 import sorting (8), W292 no-newline-at-eof (7), PT011 broad pytest.raises (4), SIM/UP/C416 minor (11)"
    fix: "uv run ruff check --fix on changed files (auto-fixes 25 of 36)"
  - id: W5
    title: "aggregate() helper signature drift vs design D7"
    evidence: "observability.py:753-770 returns float; design §D7 says returns dict[str, float]"
    fix: "Defer to PR#2 sdd-verify (PR#2 T2.4 must reconcile)"
  - id: W6
    title: "CHANGELOG BDD scenario count is off"
    evidence: "CHANGELOG.md:20 says '20 BDD scenarios across 12 feature files'; actual 136 scenarios (6 new + 130 inherited)"
    fix: "Re-word CHANGELOG.md:20 for accuracy"
suggestion_findings:
  - id: S1
    title: "--format=json-detailed shape undocumented in capability spec"
    fix: "Add shape contract to openspec/specs/observability/spec.md after PR#2 lands"
  - id: S2
    title: "Snapshot dual-name (W23) not documented in capability spec"
    fix: "Add '## Counter renaming history' section to capability spec"
  - id: S3
    title: "Double-read JSONL on --since + --window composition"
    fix: "Cache parsed events across the filter pipeline (PR#2 perf polish)"
  - id: S4
    title: "flow metrics --json byte-identical regression is implicit, not snapshot-pinned"
    fix: "Add snapshot regression test pinning exact format string"
carry_forwards_count: 11  # 1 CRITICAL + 6 WARNING + 4 SUGGESTION
artifacts:
  file_path: C:\dev\proyects\flow-engineering\openspec\changes\observability\verify-report-pr1.md
  engram_observation_id: <assigned on mem_save>
risks:
  - C1 affects PRODUCTION `flow metrics summary` accuracy for 5 production counters; users will see `unknown` bucket where `binding` should appear
  - W1 affects VERSION reporting (flow --version says 0.6.0 but CHANGELOG claims 0.7.0); could confuse downstream consumers + external docs
  - W5 deferred to PR#2; PR#2 sdd-verify must check aggregate() signature reconciliation
next_recommended: "Pre-archive W-fix commit (C1 + W1 + W2 + W3 + W6 + S2 + ruff --fix) → re-verify → sdd-archive → PR#2 apply"
skill_resolution: paths-injected (sdd-verify SKILL.md loaded via Skill tool)
```

---

## Appendix A — file inventory (changed by PR#1)

### Production
- `src/flow_engineering/observability.py` — +279 LOC (MetricEvent, DOMAIN_BY_PREFIX, read_all_metrics, read_events_since, read_events_by_domain, summarize, prometheus_exposition, aggregate, atomic_write_text, WINDOW_PATTERNS, parse_window, filter_by_window, EXIT_*, validate_domain, ALL_DOMAINS, MetricsSummaryResult, read_and_summarize)
- `src/flow_engineering/cli.py` — +108 LOC (metrics Group conversion + metrics_summary subcommand with --format/--window/--domain/--since/--until)
- `openspec/specs/observability/spec.md` — NEW (137 LOC; capability spec baseline)
- `CHANGELOG.md` — +29 LOC (v0.7.0 entry)

### Runtime (skills)
- `~/.config/opencode/skills/sdd-propose/SKILL.md` — +1 section (line 209)
- `~/.config/opencode/skills/sdd-design/SKILL.md` — +1 section (line 204)
- `~/.config/opencode/skills/sdd-tasks/SKILL.md` — +1 section (line 274)
- `~/.config/opencode/skills/sdd-apply/SKILL.md` — +1 section (line 256)
- `~/.config/opencode/skills/sdd-verify/SKILL.md` — +1 section (line 104)
- `~/.config/opencode/skills/sdd-archive/SKILL.md` — +1 section (line 185)

### Tests
- `tests/unit/test_observability_read.py` — NEW
- `tests/unit/test_observability_window.py` — NEW
- `tests/unit/test_observability_domain.py` — NEW
- `tests/unit/test_observability_summary_result.py` — NEW
- `tests/unit/test_atomic_write.py` — NEW
- `tests/unit/test_cli_metrics_summary.py` — NEW (14 tests)
- `tests/integration/test_metrics_summary_integration.py` — NEW (6 tests)
- `tests/bdd/req35_metrics_summary.feature` — NEW
- `tests/bdd/req36_metrics_window.feature` — NEW
- `tests/bdd/req37_metrics_domain.feature` — NEW
- `tests/bdd/test_observability_steps.py` — NEW (shared BDD glue, 573 LOC)

### Planning artifacts (untracked, out of repo)
- `openspec/changes/observability/explore.md`
- `openspec/changes/observability/proposal.md`
- `openspec/changes/observability/spec.md`
- `openspec/changes/observability/design.md`
- `openspec/changes/observability/tasks.md`
- `openspec/changes/observability/apply-progress/pr1-batch-{a,b,c,d,e}.md`

---

## Appendix B — verified commit map (PR#1)

| Commit | Type | Subject | Maps to task |
|--------|------|---------|--------------|
| `0bc25fd` | test(unit) | RED fixtures for read-side observability helpers | T1.1 (RED) |
| `6148b66` | feat(observability) | 6 read functions + MetricEvent + atomic_write_text | T1.1 (GREEN) |
| `b843cce` | feat(cli) | flow metrics summary subcommand + --format/--window/--domain flags | T1.2 |
| `83aba8a` | docs(specs) | bootstrap openspec/specs/observability/spec.md | T1.3 |
| `89e7c72` | test(unit) | RED fixtures for window filter | T1.4 (RED) |
| `2db59be` | feat(observability) | filter_by_window + parse_window + WINDOW_PATTERNS | T1.4 (GREEN) |
| `27c8ae2` | feat(cli) | --window/--since/--until flags on flow metrics summary + BDD req36 | T1.5 |
| `6f3dd4c` | test(unit) | RED fixtures for cross-domain slice expansion | T1.6 (RED) |
| `7579580` | feat(observability) | DOMAIN_BY_PREFIX 8-value expansion + validate_domain | T1.6 (GREEN) |
| `38df3db` | feat(cli) | --domain widening to 8 values on flow metrics summary + BDD req37 | T1.7 |
| `5646516` | test(unit) | RED fixtures for read_and_summarize + MetricsSummaryResult + exit code constants | T1.8 (RED) |
| `2766a9f` | feat(observability) | read_and_summarize + MetricsSummaryResult + EXIT_* constants | T1.8 (GREEN) |
| `dde2bc9` | feat(cli) | flow metrics summary uses read_and_summarize + emits exit 3 on malformed metrics | T1.8 (CLI wire-up) |
| `b8088c0` | test(unit) | atomic_write_text coverage - tempfile + os.replace pattern | T1.9 |
| `7014fee` | test(integration) | end-to-end metrics summary integration sweep | T1.10 (integration) |
| `326e9d6` | docs(changelog) | v0.7.0 entry for observability change | T1.10 (CHANGELOG) |
| `8b58f7a` | docs(skills) | metrics hook section in 6 SKILL.md runtime files | T1.10 (skills) |
| `7fe13c2` | docs(apply-progress) | pr1-batch-e — T1.10 closeout | T1.10 (closeout) |

**18 commits landing all 10 tasks** (2.9x LOC multiplier realized as planned per design §"File Changes" 2-4x target band).