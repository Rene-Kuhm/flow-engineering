<!-- tasks.md: observability. Source: manual. -->
# Tasks: observability

**Change:** `observability`
**Builds on:** `proposal.md` (#194) — Approach A: extend `flow metrics` CLI; `design.md` (#197) — D1-D12 resolved (12 architecture decisions); `spec.md` (#195) — 5 REQs (REQ-35..39), 11 BDD scenarios
**Date:** 2026-06-27
**Status:** SPECIFIED + DESIGNED → ready for sdd-apply (2 chained PRs, batched)
**Strict TDD:** ON (per `decision-code-linking` precedent; RED → GREEN → REFACTOR cycle per task)
**Delivery strategy:** chained-pr (per proposal #194 + design #197 D12; 2 PRs mandatory given ×2.9 strict-TDD multiplier pushes realistic LOC past the 400-line review budget)

---

```yaml
status: success
confidence: high
total_tasks: 17  # T1.1..T1.10 + T2.1..T2.7
pr_split: 2 chained PRs (PR#1: foundation + summary + slice + window; PR#2: export + aggregation)
forecast_loc_production: ~1200
forecast_loc_test: ~2400
forecast_loc_grand_total: ~3600
forecast_loc_realistic_x2.9: ~10400  # design-specific multiplier (per design §"File Changes" 2-4× target band)
batches:
  pr1_batch_a: 3 tasks   # T1.1, T1.2, T1.3
  pr1_batch_b: 2 tasks   # T1.4, T1.5
  pr1_batch_c: 2 tasks   # T1.6, T1.7
  pr1_batch_d: 2 tasks   # T1.8, T1.9
  pr1_batch_e: 1 task    # T1.10
  pr2_batch_f: 3 tasks   # T2.1, T2.2, T2.3
  pr2_batch_g: 2 tasks   # T2.4, T2.5
  pr2_batch_h: 2 tasks   # T2.6, T2.7
review_workload_forecast:
  pr1_400_line_budget_risk: high
  pr2_400_line_budget_risk: medium
  chained_prs_recommended: yes
  decision_needed_before_apply: no  # explicit in proposal #194
strict_tdd: on
bdd_feature_files: 5 NEW (req35..req39)
bdd_scenarios: 11 (REQ-35:2 + REQ-36:2 + REQ-37:2 + REQ-38:3 + REQ-39:2)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\observability\tasks.md
next_recommended: sdd-apply observability PR#1 batch A
```

---

## PR Split

| PR | REQs | Tasks | LOC forecast | LOC realistic (×2.9) |
|----|------|-------|--------------|----------------------|
| PR#1 | REQ-35, REQ-36, REQ-37 | T1.1..T1.10 (10 tasks) | ~1200 prod / ~2400 test = ~3600 | ~10 400 |
| PR#2 | REQ-38, REQ-39 | T2.1..T2.7 (7 tasks) | ~736 prod / ~1472 test = ~2208 | ~6400 |
| **Total** | **5 REQs** | **17 tasks** | **~1936 / ~3872 = ~5808** | **~16 800** |

**Rationale**:
- **PR#1 establishes the read-side foundation + the user-facing `flow metrics summary/window/slice` commands.** It boots the `openspec/specs/` baseline (resolves `cross-project-federation` archive-report #61). Each PR is independently shippable; PR#1 adds visible user value (text dashboard, time-window filter, domain slice) without requiring the Prometheus exporter or percentile aggregation.
- **PR#2 adds export + aggregation.** It builds on PR#1's shared `observability.py` extensions + the shared BDD glue file at `tests/bdd/test_observability_steps.py` (per design D12). All additive on top of PR#1's HEAD; merge-base is PR#1's merge commit.
- **Merge ordering is MANDATORY**: PR#1 MUST merge to `main` BEFORE PR#2 apply starts (Engram #114 stacked-to-main pattern). PR#2 cherry-picks additive changes only.

---

## Dependency Graph

```
PR#1 (branched from main):
  Batch A (foundation + summary + spec bootstrap):
    T1.1 (observability.py: read_events_since + read_events_by_domain + summarize
          + DOMAIN_BY_PREFIX + ACCEPTED_DOMAINS + tests/fixtures/metrics/sample_24h.jsonl)
      ↓
    T1.2 (cli.py: --summary flag + flow metrics summary text dashboard + 5 unit tests + BDD req35)
      ↓
    T1.3 (openspec/specs/observability/spec.md NEW — capability catalog; resolves archive-report #61)
          [T1.3 lands IN PARALLEL with T1.2; no code dependency; just a docs commit]

  Batch B (time-window filter):
    T1.4 (observability.py: window helper + read_events_since extended + unit tests)
      ↓
    T1.5 (cli.py: --since/--until/--window flags + _resolve_window helper + BDD req36)

  Batch C (cross-domain slice):
    T1.6 (observability.py: DOMAIN_BY_PREFIX validation + read_events_by_domain + unit tests)
      ↓
    T1.7 (cli.py: --domain/--top flags + BDD req37)

  Batch D (error handling + atomic write helper):
    T1.8 (observability.py: default-empty handling + exit-code helpers per D9)
    T1.9 (cli.py: _atomic_write_text helper per D10 — reusable in PR#2 for --out)

  Batch E (PR#1 closeout):
    T1.10 (CHANGELOG.md v0.7.0 + 6 SKILL.md runtime updates + integration tests sweep)

[PR#1 MERGE → main]
        ↓
PR#2 (branched from PR#1's merge commit):
  Batch F (Prometheus export):
    T2.1 (observability.py: prometheus_exposition + METRIC_TYPE_OVERRIDES + unit tests)
      ↓
    T2.2 (cli.py: --prometheus/--out flags + flow metrics export path + BDD req38)
      ↓
    T2.3 (cli.py: --window composes with --prometheus; per-event sum within window)

  Batch G (percentile + aggregations):
    T2.4 (observability.py: aggregate + percentile + statistics.quantiles + unit tests)
      ↓
    T2.5 (cli.py: --percentile/--aggregations/--field flags + flow metrics aggregate path + BDD req39)

  Batch H (PR#2 closeout):
    T2.6 (end-to-end integration tests: 100 mock metrics across 4 domains → all 5 subcommands)
      ↓
    T2.7 (CHANGELOG.md v0.7.1 + 6 SKILL.md runtime updates for "Export hook" + "Aggregation hook"
          + apply-progress/finalize)
```

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Total tasks | 17 (T1.1..T1.10, T2.1..T2.7) |
| Forecast LOC production (PR#1) | ~1200 |
| Forecast LOC test (PR#1, unit + BDD) | ~2400 |
| Forecast LOC grand total (PR#1) | ~3600 |
| Forecast LOC production (PR#2) | ~736 |
| Forecast LOC test (PR#2, unit + BDD) | ~1472 |
| Forecast LOC grand total (PR#2) | ~2208 |
| Forecast LOC grand total (both PRs) | ~5808 |
| Forecast LOC realistic (×2.9 per design §"File Changes") | ~16 800 |
| BDD feature files | 5 (all NEW; req35_metrics_summary, req36_metrics_window, req37_metrics_domain, req38_metrics_prometheus, req39_metrics_percentile) |
| BDD scenarios | 11 (matches spec REQ-35..39) |
| New source files | 1 (`openspec/specs/observability/spec.md`) + 1 fixture (`tests/fixtures/metrics/sample_24h.jsonl`) |
| Modified source files | 2 (`observability.py`, `cli.py`) + 4 minor (`CHANGELOG.md`, `pyproject.toml`, `tests/unit/test_observability.py`) |
| New test files | 5 unit (`test_cli_metrics.py`, `test_observability_summary.py`, `test_observability_prometheus.py`, `test_observability_aggregate.py`, plus step glue `test_observability_steps.py` shared across all 5 BDD features) |
| Chained PRs recommended | **Yes** (per proposal #194 + design #197 D12; ×2.9 TDD multiplier pushes realistic LOC past 400-line review budget) |
| Chain strategy | PR#1 → merge → PR#2 (mandatory; no cherry-pick across PRs) |
| PR#1 400-line budget risk | **High** (~3600 LOC forecast, ~10 400 realistic; mitigated by 6 work-unit commits each ≤400 LOC per `work-unit-commits` skill) |
| PR#2 400-line budget risk | **Medium** (~2208 LOC forecast, ~6400 realistic; smaller surface, 4 work-unit commits each ≤400 LOC) |
| Decision needed before apply | **No** (chained-pr strategy is explicit in proposal #194; per-commit work-unit splits per `work-unit-commits` skill mitigate review budget) |

### Forecast rationale

| Signal | Source | Value |
|---|---|---|
| Production LOC (PR#1) | design.md D-file breakdown (`observability.py` +200 + `cli.py` +150 + `openspec/specs/observability/spec.md` +200 + 6 SKILL.md +50 + CHANGELOG +50 + `tests/unit/test_observability.py` delta +150 + integration +200) | ~1000 (revised; spec says 750) |
| Production LOC (PR#2) | design.md D-file breakdown (`observability.py` +100 + `cli.py` +100 + CHANGELOG +50 + `pyproject.toml` +5 + integration tests +50) | ~300 (revised; spec says 550) |
| Realistic ×2.9 TDD multiplier | Pattern `apply-under-strict-tdd-grows-5-6x-beyond-forecast` (#113): design §"File Changes" sets strict-TDD ratio at **~2.9×** (within the 2-4× target band) — LOWER than change #5's ×6 because observability has more library-code reuse (filter helpers + lookup tables) | ×2.9 → ~16 800 grand total realistic |
| Per-delegation batch ceiling | Pattern `apply-batches-split-into-6-tasks-per-delegation` (#112): ≤3 tasks OR ≤150 LOC prod per delegation, default runtime ~15 min | PR#1 batch A at ~500 LOC is the **TIMEOUT RISK BATCH** |
| Risk: PR#1 batch A | ~500 LOC across 3 tasks (foundation + summary CLI + spec bootstrap) at ~6 LOC/min = ~1.5h | **TIMEOUT RISK** — split into A1 (T1.1 foundation + T1.3 spec bootstrap) + A2 (T1.2 summary CLI + BDD req35) if delegation hits 15-min ceiling mid-batch |
| Risk: 400-line review budget | PR#1 cumulative ~3600 LOC > 400-line budget by ~9× | Mitigated by 6 work-unit commits per `work-unit-commits` convention; per-commit diffs ≤400 LOC |

### Suggested Work Units

Two chained PRs (per proposal #194 + design #197 D12). Each PR lands via per-delegation batching (≤3 tasks / ≤150 LOC prod) at the apply phase.

| Apply batch | Tasks | Production LOC | Test LOC | Why |
|-------------|-------|-----------------|----------|-----|
| **PR#1 A** | T1.1 + T1.2 + T1.3 | ~500 | ~450 | Foundation helpers + summary CLI + spec bootstrap — atomic foundation; 3 commits RED → GREEN → REFACTOR; **TIMEOUT RISK BATCH** |
| **PR#1 B** | T1.4 + T1.5 | ~150 | ~400 | Window filter helper + `--since`/`--until`/`--window` flags + BDD req36 (2 scenarios) |
| **PR#1 C** | T1.6 + T1.7 | ~130 | ~350 | DOMAIN_BY_PREFIX validation + `--domain`/`--top` flags + BDD req37 (2 scenarios) |
| **PR#1 D** | T1.8 + T1.9 | ~130 | ~350 | Default-empty handling + exit-code helpers per D9 + atomic write helper per D10 (reused by PR#2 `--out`) |
| **PR#1 E** | T1.10 | ~290 | ~200 | CHANGELOG v0.7.0 + 6 SKILL.md runtime updates + integration tests sweep |
| **PR#2 F** | T2.1 + T2.2 + T2.3 | ~300 | ~600 | Prometheus exposition helper + `--prometheus`/`--out` flags + BDD req38 (3 scenarios) + `--window` composition |
| **PR#2 G** | T2.4 + T2.5 | ~180 | ~400 | Aggregate + percentile helpers + `--percentile`/`--aggregations`/`--field` flags + BDD req39 (2 scenarios) |
| **PR#2 H** | T2.6 + T2.7 | ~256 | ~472 | End-to-end integration tests sweep + CHANGELOG v0.7.1 + 6 SKILL.md runtime updates for export/aggregation hooks |

---

## Out-of-Scope Reminders (do NOT pull into tasks)

These 10 items are explicitly deferred per spec.md + design.md — apply must NOT introduce code for them:

- **REQ-40 — Label-based query** (`--label key=value` for arbitrary event-field filtering beyond `--domain`) — defer to v1.1
- **REQ-41 — Threshold alerting** (`--threshold name:op:N` to emit non-zero exit codes for CI/CD integration) — defer to v1.1
- **REQ-42 — `engine_*` counters** (CLI startup time, embedding provider latency, daemon queue depth) — defer to `engine-instrumentation` change. The `engine` slot in `DOMAIN_BY_PREFIX` is RESERVED but the v1 table is empty for it
- **REQ-43 — Federation-aware events** (`--project=<key>` filter that requires modifying every record helper signature to inject a `project` field) — defer to `federated-observability` follow-up
- **REQ-44 — JSONL rotation** (`FLOW_METRICS_MAX_BYTES`, `FLOW_METRICS_MAX_AGE_DAYS` to gzip-and-rotate the sink file) — defer to v1.1 (cross-cuts `read_all()` and 6 existing call sites)
- **Snapshot export/import for sharing** — already deferred in `graph-snapshots` archive
- **Async embed-on-save** (auto-vectorize on `mem_save`) — already deferred in `vector-semantic-search` archive
- **Per-snapshot percentile** (`flow snapshot show <id> --percentile=p95`) — v2; v1 percentiles are LIVE JSONL only
- **Histogram metric type in Prometheus exporter** (bucket-based counts for `_latency_ms`) — v1 emits `summary` type (D6); histogram deferred to v1.1
- **OTLP / OpenTelemetry exporter** — v2 (Prometheus textfile is the v1 choice)
- **Real-time tail mode** (`flow metrics --tail` like `tail -f`) — v2
- **Graphviz / DOT export of counter relationships** — v2
- **Webhook / Slack alerting on threshold breach** — v1.1 (companion to REQ-41)
- **Multi-process metric aggregation** — v2 (v1 assumes single-process CLI invocations)
- **CSV export** (`flow metrics --format=csv`) — v2 (5 active formats cover v1)

---

## Task list (17 tasks, 2 chained PRs)

### PR#1 — Foundation: summary view + time window + cross-domain slice + spec catalog bootstrap

#### T1.1 — Extend `observability.py` with 3 read-side helpers + `DOMAIN_BY_PREFIX` lookup + fixture (REQ-35/36/37 foundation)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~300 impl + ~300 tests = ~600
- **Files:**
  - `src/flow_engineering/observability.py` (modify — add 3 pure functions + 2 lookup tables per design D1/D3/D5)
  - `tests/unit/test_observability.py` (modify — +30 unit tests across `TestReadEventsSince`, `TestReadEventsByDomain`, `TestSummarize`, `TestDomainByPrefix` classes)
  - `tests/fixtures/metrics/sample_24h.jsonl` (NEW — 15 events covering all 7 active domains with deterministic ISO timestamps spanning 24h; consumed by both PR#1 and PR#2 tests per D12)
- **Dependencies:** none
- **Acceptance criteria:**
  - [ ] RED: `test_read_events_since_filters_to_iso_window` fails; `test_read_events_since_inclusive_boundaries` fails; `test_read_events_since_until_iso_upper_bound` fails; `test_read_events_by_domain_returns_only_snapshot_events` fails; `test_read_events_by_domain_unknown_domain_returns_empty` fails; `test_summarize_returns_count_domain_first_seen_last_seen` fails; `test_summarize_unknown_bucket_for_orphan_names` fails; `test_summarize_alphabetical_ordering` fails; `test_domain_by_prefix_covers_all_31_counters` fails; `test_accepted_domains_has_8_values` fails; +20 more boundary/edge-case RED fixtures
  - [ ] GREEN: `read_events_since(path: Path | None, since_iso: str, until_iso: str | None = None) -> list[dict]`:
    - Reuses `read_all(path)` for I/O (no signature change to existing call sites)
    - Filters in-memory by lexicographic ISO comparison on `event["ts"]` (Z-suffixed UTC = fixed-width, so lex == chronological)
    - Inclusive on both boundaries (`since <= ts <= until`)
    - Empty `until_iso` means no upper bound
    - Empty `since_iso` raises `ValueError` (defensive; CLI catches + emits exit-code-3 JSON error per D9)
  - [ ] GREEN: `read_events_by_domain(path: Path | None, domain: str) -> list[dict]`:
    - Reuses `read_all(path)` for I/O
    - Looks up domain's registered prefixes from `DOMAIN_BY_PREFIX` table; empty prefix list (e.g., `engine`) → returns `[]`
    - Unknown domain name → returns `[]` (caller decides; CLI rejects unknown domain via `click.Choice` at flag-parse time)
  - [ ] GREEN: `summarize(events: list[dict]) -> dict[str, dict]`:
    - Collapses events into `{name: {count, domain, first_seen, last_seen}}`
    - `count` = sum of `fields.count` (fallback `fields.confirmed`, fallback 1 per event)
    - `domain` = `DOMAIN_BY_PREFIX[<longest matching prefix>]` or `"unknown"` (W23 dual-name history)
    - `first_seen` / `last_seen` = earliest / latest `ts` across matching events (ISO 8601 UTC string)
    - Returned dict is alpha-sorted by `name` for stable output
  - [ ] GREEN: `DOMAIN_BY_PREFIX: dict[str, str] = { ... }` covers all 11 prefixes per design D5: `suggest_/bindings_/inspect_ → binding`; `backfill_ → backfill`; `drift_ → drift`; `vector_/reindex_ → vector`; `federated_ → federated`; `snapshot_ → snapshot`; `update_observation_metadata_/project_tag_ → metadata`
  - [ ] GREEN: `ACCEPTED_DOMAINS: list[str] = ["binding", "backfill", "drift", "vector", "federated", "snapshot", "metadata", "engine"]` (8 values; `engine` reserved per REQ-42)
  - [ ] GREEN: `tests/fixtures/metrics/sample_24h.jsonl` contains exactly 15 events spanning all 7 active domains (binding: 3, backfill: 1, drift: 2, vector: 3, federated: 2, snapshot: 2, metadata: 2) with deterministic ISO timestamps
  - [ ] GREEN: All 801+ existing tests pass WITHOUT modification (verified via `uv run pytest` — non-breaking guarantee)
- **Commits:**
  1. `test(unit): RED fixtures for read_events_since + read_events_by_domain + summarize + DOMAIN_BY_PREFIX`
  2. `feat(observability): 3 read-side helpers + DOMAIN_BY_PREFIX + ACCEPTED_DOMAINS + sample_24h fixture`

#### T1.2 — Add `flow metrics summary` text dashboard with `--format text|json|json-detailed` flags + BDD req35 (REQ-35)

- **Type:** test + code + bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~150 impl + ~250 unit tests + ~100 BDD feature+step defs = ~500
- **Files:**
  - `src/flow_engineering/cli.py` (modify — extend `metrics` command at `cli.py:977` with `--summary` flag; refactor `_summarize_metrics()` at `cli.py:960` to be a thin wrapper calling `observability.summarize()`; add `render_summary()` helper for the text dashboard)
  - `tests/unit/test_cli_metrics.py` (NEW — `TestSummaryCommand` class with 8-10 RED fixtures)
  - `tests/unit/test_observability_summary.py` (NEW — unit-level coverage for `summarize()` helper with 6 RED fixtures)
  - `tests/bdd/req35_metrics_summary.feature` (NEW — 2 BDD scenarios from spec REQ-35)
  - `tests/bdd/test_observability_steps.py` (NEW — pytest-bdd step glue shared across all 5 BDD features per D12; PR#1 lands ~150 LOC for req35/36/37)
- **Dependencies:** T1.1
- **Acceptance criteria:**
  - [ ] RED: `test_cli_metrics_summary_empty_sink_emits_no_metrics_recorded` fails; `test_cli_metrics_summary_with_data_renders_dashboard` fails; `test_cli_metrics_summary_includes_by_domain_section` fails; `test_cli_metrics_summary_includes_top_n_section` fails; `test_cli_metrics_summary_default_top_is_10` fails; `test_cli_metrics_summary_with_top_flag_limits_output` fails; `test_cli_metrics_summary_json_format_emits_dict` fails; `test_cli_metrics_summary_json_detailed_format_emits_richer_shape` fails; `test_cli_metrics_default_no_flags_byte_identical_to_v0_6_0` fails; `test_cli_metrics_default_json_byte_identical_to_v0_6_0` fails
  - [ ] GREEN: `flow metrics summary` (no other flags) renders a text dashboard with 5 sections (header / totals / by-domain / top-N counters / footer); header shows `flow-engineering metrics summary`, `Generated: <ISO 8601 UTC>`, `Window: <since> → <until>  (<human-readable duration>)`; totals show `Total events: <N>` + `Distinct counters: <N>`; by-domain rows sorted by event count descending; top-N default = 10 (REQ-35)
  - [ ] GREEN: Empty JSONL sink OR empty filter set → emits single line `(no metrics recorded)` (text) or `{}` (JSON) and exits `0` (D8 default-empty)
  - [ ] GREEN: `--format=text` (default) → text dashboard; `--format=json` → `{name: {count, domain, first_seen, last_seen}, ...}` flat dict (same shape as `--json`); `--format=json-detailed` → `[{"name": ..., "count": ..., "domain": ..., "first_seen": ..., "last_seen": ...}, ...]` richer list shape (per OQ-7)
  - [ ] GREEN: `flow metrics` without any new flags → byte-identical to v0.6.0 behavior (REQ-8 close contract; verified by 3 existing `TestMetricsCommand` tests at `test_cli_inspect.py:269-298` staying green)
  - [ ] GREEN: `flow metrics --json` without any new flags → byte-identical to v0.6.0 behavior (flat dict `{name: count}` preserved)
  - [ ] GREEN: BDD `req35_metrics_summary.feature` 2 scenarios verbatim from spec:
    1. Summary over all domains shows per-domain counter totals (1247 events / 27 counters / 5 domains → by-domain breakdown + top-N)
    2. Empty sink → emits `(no metrics recorded)` + exits 0 + no other output
- **Commits:**
  1. `test(unit): RED fixtures for flow metrics summary + --format flag + byte-identical regression`
  2. `feat(cli): flow metrics summary text dashboard with --format flag + render_summary helper + observability.summarize refactor`
  3. `test(bdd): req35_metrics_summary feature with 2 scenarios + shared step glue foundation`

#### T1.3 — Bootstrap `openspec/specs/observability/spec.md` capability catalog (resolves archive-report #61)

- **Type:** docs
- **TDD phase:** N/A (docs)
- **LOC:** ~200 docs
- **Files:**
  - `openspec/specs/observability/spec.md` (NEW — capability catalog; bootstraps `openspec/specs/` baseline per design D11)
- **Dependencies:** none (parallel to T1.1 + T1.2; just a docs commit)
- **Acceptance criteria:**
  - [ ] GREEN: `openspec/specs/observability/spec.md` exists (verified via `Test-Path -LiteralPath "openspec/specs"` returning `True` after PR#1 merge)
  - [ ] GREEN: Catalog ALL 31 counter names (after `graph-snapshots` archive) across 7 active domains + 1 reserved (`engine`):
    - `binding` (8 names): `suggest_invoked_total`, `suggest_hit_total`, `suggest_miss_total`, `bindings_confirmed_total`, `inspect_invoked_total`, `inspect_render_ms`, `backfill_observations_total`, `backfill_with_refs_total`
    - `drift` (8 names): `drift_invoked_total`, `drift_still_valid_total`, `drift_label_drift_total`, `drift_stale_location_total`, `drift_stale_id_total`, `drift_obsolete_total`, `drift_contradicted_total`, `drift_unable_to_verify_total`
    - `vector` (6 names): `vector_search_invoked_total`, `vector_search_results_returned_total`, `vector_search_latency_ms`, `vector_index_size_observations`, `reindex_observations_total`, `reindex_duration_seconds`
    - `federated` (3 names): `federated_search_invoked_total`, `federated_search_projects_queried`, `federated_search_results_returned_total`
    - `snapshot` (4 names): `snapshot_create_total`, `snapshot_rollback_total`, `snapshot_prune_total`, `snapshot_load_failed_total`
    - `metadata` (2 names): `update_observation_metadata_*`, `project_tag_*` (representative patterns)
    - `backfill` (covered via `backfill_*` prefix above)
  - [ ] GREEN: Each counter has: helper provenance (`record_drift_summary` at `observability.py:307`, `record_vector_summary` at `observability.py:353`, `record_federated_summary` at `observability.py:411`, `record_snapshot_event` at `observability.py:453`, etc.), JSONL event shape, and label-set invariants
  - [ ] GREEN: Marks as `v1.0` baseline; kebab-case folder per capability per design D11
  - [ ] GREEN: `Test-Path -LiteralPath "openspec/specs/observability/spec.md"` returns `True` after PR#1 merge
- **Commit:**
  1. `docs(spec): bootstrap openspec/specs/observability/spec.md capability catalog (resolves archive-report #61)`

#### T1.4 — Add `filter_by_window(now, window: str)` helper + `read_events_since` extension + unit tests (REQ-36 foundation)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~100 impl + ~250 tests = ~350
- **Files:**
  - `src/flow_engineering/observability.py` (modify — extend `read_events_since` with rolling-window support; add `filter_by_window(events: list[dict], now: datetime, window: str) -> list[dict]` per design D4)
  - `tests/unit/test_observability.py` (extend — `TestFilterByWindow` class with 6 RED fixtures: 1h/24h/7d rolling, case-insensitive parse, invalid window raises ValueError, boundary inclusivity)
- **Dependencies:** T1.1
- **Acceptance criteria:**
  - [ ] RED: `test_filter_by_window_1h_excludes_events_older_than_60_minutes` fails; `test_filter_by_window_24h_excludes_events_older_than_24_hours` fails; `test_filter_by_window_7d_excludes_events_older_than_7_days` fails; `test_filter_by_window_case_insensitive` fails; `test_filter_by_window_invalid_value_raises_value_error` fails; `test_filter_by_window_boundary_inclusivity` fails
  - [ ] GREEN: `filter_by_window(events, now, window)` accepts `window` ∈ `{"1h", "24h", "7d"}` (case-insensitive); computes `since_dt = now - timedelta({"1h": hours=1, "24h": hours=24, "7d": days=7}[window.lower()])`; filters events to those with `ts >= since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")`; inclusive on the lower boundary (D4 rolling semantics)
  - [ ] GREEN: Empty `events` → `[]`; invalid `window` → raises `ValueError` with hint `"window must be one of '1h', '24h', '7d' (case-insensitive)"`
  - [ ] GREEN: Pure function (no I/O); reusable by CLI in T1.5
- **Commits:**
  1. `test(unit): RED fixtures for filter_by_window (1h/24h/7d rolling + case-insensitive + invalid value)`
  2. `feat(observability): filter_by_window helper with rolling semantics per D4`

#### T1.5 — Add `--since` / `--until` / `--window` flags to `flow metrics` + `_resolve_window` helper + BDD req36 (REQ-36)

- **Type:** test + code + bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~50 impl + ~150 tests + ~100 BDD feature+step defs = ~300
- **Files:**
  - `src/flow_engineering/cli.py` (modify — extend `metrics` command with `--since=<iso>`, `--until=<iso>`, `--window=<1h|24h|7d>` flags; add `_resolve_window(since_iso, until_iso, window) -> tuple[str | None, str | None]` helper per design §"Algorithm Details"; reuse `_parse_since()` from `cli.py:1022` for ISO validation)
  - `tests/unit/test_cli_metrics.py` (extend — `TestWindowFilter` class with 6 RED fixtures: ISO parse error → exit code 3, valid ISO → filter applied, `--window=1h` rolling, `--window=24h` rolling, `--window` + `--since` composition, `--until < --since` → empty result exit 0)
  - `tests/bdd/req36_metrics_window.feature` (NEW — 2 BDD scenarios from spec REQ-36)
  - `tests/bdd/test_observability_steps.py` (extend — +step glue for REQ-36)
- **Dependencies:** T1.4
- **Acceptance criteria:**
  - [ ] RED: `test_cli_metrics_since_iso_filters_events_after_timestamp` fails; `test_cli_metrics_until_iso_filters_events_before_timestamp` fails; `test_cli_metrics_window_1h_rolling_filters_last_60_minutes` fails; `test_cli_metrics_window_24h_rolling_filters_last_24_hours` fails; `test_cli_metrics_since_garbage_exits_code_3` fails; `test_cli_metrics_window_invalid_choice_exits_code_2` fails
  - [ ] GREEN: `--since=<iso>` filters events to `ts >= <iso>`; invalid ISO → emits `{"error": "invalid --since value", "value": "<garbage>", "hint": "use ISO 8601 UTC, e.g., 2026-06-26T00:00:00Z"}` to stderr + exits `3` (D9 data-error)
  - [ ] GREEN: `--until=<iso>` filters events to `ts <= <iso>`; same parse-error contract
  - [ ] GREEN: `--window=<1h|24h|7d>` rolling shorthand; `click.Choice(["1h", "24h", "7d"], case_sensitive=False)` validates at flag-parse time → invalid value exits `2` (D9 usage-error)
  - [ ] GREEN: `_resolve_window` helper composes `--window` (rolling) and `--since` (absolute) via Click last-wins; precedence: when both given, `--since` wins when both are explicitly passed (per design §"Algorithm Details" note)
  - [ ] GREEN: BDD `req36_metrics_window.feature` 2 scenarios verbatim from spec:
    1. 10 hourly events → `flow metrics --since=2026-06-26T15:00:00Z` returns only the 5 events at 15:00-19:00 (excludes 10:00-14:00)
    2. 5 events at `<now-2h>` / `<now-90m>` / `<now-45m>` / `<now-30m>` / `<now-5m>` → `flow metrics --window=1h` returns only the 3 events at `-45m` / `-30m` / `-5m` (excludes `-2h` / `-90m`)
- **Commits:**
  1. `test(unit): RED fixtures for --since/--until/--window flags + _resolve_window helper + ISO parse errors`
  2. `feat(cli): --since/--until/--window flags on flow metrics + _resolve_window helper (D4 rolling semantics)`
  3. `test(bdd): req36_metrics_window feature with 2 scenarios + step glue extension`

#### T1.6 — Implement `DOMAIN_BY_PREFIX` validation helper + `read_events_by_domain` integration + unit tests (REQ-37 foundation)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~80 impl + ~200 tests = ~280
- **Files:**
  - `src/flow_engineering/observability.py` (modify — add `validate_counter_in_catalog(counter_name: str) -> str` helper that returns the domain name from `DOMAIN_BY_PREFIX` or `"unknown"`; expose `ALL_KNOWN_COUNTERS` set built from `VECTOR_COUNTER_NAMES + FEDERATED_COUNTER_NAMES + SNAPSHOT_COUNTER_NAMES` + 14 REQ-8/REQ-12/REQ-13/REQ-24 names for catalog-coverage assertions)
  - `tests/unit/test_observability.py` (extend — `TestDomainCatalogCoverage` class with 5 RED fixtures: all 31 counters resolve to a known domain, no orphans in catalog, `engine` slot returns `"unknown"` for any `engine_*` counter, `update_observation_metadata_*` and `project_tag_*` resolve to `metadata`)
- **Dependencies:** T1.1 (DOMAIN_BY_PREFIX table from T1.1 is required input)
- **Acceptance criteria:**
  - [ ] RED: `test_validate_counter_returns_domain_for_known_counter` fails; `test_validate_counter_returns_unknown_for_orphan_counter` fails; `test_all_31_counters_resolve_to_known_domain` fails; `test_engine_counter_returns_unknown_bucket` fails; `test_metadata_prefixes_resolve_to_metadata_domain` fails
  - [ ] GREEN: `validate_counter_in_catalog(counter_name)` returns the matching domain from `DOMAIN_BY_PREFIX` (longest-prefix match), or `"unknown"` if no prefix matches (W23 dual-name history)
  - [ ] GREEN: `ALL_KNOWN_COUNTERS: frozenset[str]` aggregates `VECTOR_COUNTER_NAMES` (6) + `FEDERATED_COUNTER_NAMES` (3) + `SNAPSHOT_COUNTER_NAMES` (4) + 14 REQ-8/REQ-12/REQ-13/REQ-24 names = 27 names (after `graph-snapshots` archive, 31 counters; `ALL_KNOWN_COUNTERS` is a runtime superset assertion, NOT an exhaustive catalog)
  - [ ] GREEN: Counter-name validation against `[a-zA-Z_][a-zA-Z0-9_]*` (Prometheus name regex; defense in depth for PR#2's `prometheus_exposition`)
- **Commits:**
  1. `test(unit): RED fixtures for validate_counter_in_catalog + ALL_KNOWN_COUNTERS coverage`
  2. `feat(observability): validate_counter_in_catalog helper + ALL_KNOWN_COUNTERS set + Prometheus name regex`

#### T1.7 — Add `--domain` / `--top` flags to `flow metrics` + BDD req37 (REQ-37)

- **Type:** test + code + bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~50 impl + ~150 tests + ~100 BDD feature+step defs = ~300
- **Files:**
  - `src/flow_engineering/cli.py` (modify — extend `metrics` command with `--domain=<binding|drift|vector|snapshot|federated|backfill|metadata|engine>` and `--top=<N>` flags; `click.Choice(ACCEPTED_DOMAINS)` validates at flag-parse time)
  - `tests/unit/test_cli_metrics.py` (extend — `TestDomainFilter` class with 5 RED fixtures: `--domain=snapshot` filters to snapshot_* only, `--domain=engine` returns empty result, `--domain=garbage` exits code 2, `--top=5` limits output, no `--domain` shows all)
  - `tests/bdd/req37_metrics_domain.feature` (NEW — 2 BDD scenarios from spec REQ-37)
  - `tests/bdd/test_observability_steps.py` (extend — +step glue for REQ-37)
- **Dependencies:** T1.6
- **Acceptance criteria:**
  - [ ] RED: `test_cli_metrics_domain_snapshot_filters_to_snapshot_counters` fails; `test_cli_metrics_domain_engine_returns_empty` fails; `test_cli_metrics_domain_garbage_exits_code_2` fails; `test_cli_metrics_top_5_limits_output_to_5_most_fired` fails; `test_cli_metrics_no_domain_shows_all_domains` fails
  - [ ] GREEN: `--domain=<D>` filters events via `observability.read_events_by_domain(events, D)`; `click.Choice(ACCEPTED_DOMAINS)` validates at flag-parse time → invalid value exits `2` (D9 usage-error); `engine` accepts but produces empty result (reserved slot; no events in v1)
  - [ ] GREEN: `--top=<N>` limits the per-counter output to the N most-fired counters (sorted by event count descending); default `--top=10` when combined with `--summary`; `--top=0` rejected by Click int validation
  - [ ] GREEN: Composes with `--since` / `--until` / `--window` (REQ-36) and `--summary` (REQ-35) via flag-AND composition
  - [ ] GREEN: BDD `req37_metrics_domain.feature` 2 scenarios verbatim from spec:
    1. `--domain=snapshot` filters to ONLY `snapshot_*` counters (e.g., `snapshot_create_total`, `snapshot_rollback_total`); excludes `drift_invoked_total`, `vector_search_invoked_total`, `bindings_confirmed_total`
    2. No `--domain` flag → all 5 active domains aggregate; output byte-identical to v0.6.0 default for the same JSONL
- **Commits:**
  1. `test(unit): RED fixtures for --domain/--top flags + click.Choice validation + composition`
  2. `feat(cli): --domain/--top flags on flow metrics + read_events_by_domain integration`
  3. `test(bdd): req37_metrics_domain feature with 2 scenarios + step glue extension`

#### T1.8 — Implement default-empty handling + exit-code helpers per D8/D9 + unit tests (REQ-35..37 error handling)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~80 impl + ~200 tests = ~280
- **Files:**
  - `src/flow_engineering/observability.py` (modify — add `default_empty_payload(format: str) -> str` helper that returns `(no metrics recorded)` / `{}` / `# EOF\n` per D8 default-empty contract)
  - `src/flow_engineering/cli.py` (modify — add `_emit_error_and_exit(kind: str, **details) -> NoReturn` helper that emits `{"error": "<kind>", ...details}` to stderr via `click.echo(..., err=True)` + `sys.exit(<code>)` per D9 exit-code table)
  - `tests/unit/test_observability.py` (extend — `TestDefaultEmptyPayload` class with 4 RED fixtures: text/JSON/Prometheus payloads, no raises)
  - `tests/unit/test_cli_metrics.py` (extend — `TestErrorHandling` class with 6 RED fixtures: `--since=garbage` exits 3, `--window=garbage` exits 2, `--domain=garbage` exits 2, `--format=garbage` exits 2, JSON error shape on stderr, stdout stays clean for piping)
- **Dependencies:** T1.2, T1.5, T1.7 (uses `--summary` / `--since` / `--domain` flags for integration tests)
- **Acceptance criteria:**
  - [ ] RED: `test_default_empty_text_returns_no_metrics_recorded` fails; `test_default_empty_json_returns_empty_dict` fails; `test_default_empty_prometheus_returns_eof_marker` fails; `test_cli_metrics_since_garbage_emits_json_error_to_stderr` fails; `test_cli_metrics_domain_garbage_emits_click_usage_error` fails; `test_cli_metrics_error_does_not_dirty_stdout` fails
  - [ ] GREEN: `default_empty_payload(format)` returns:
    - `"text"` → `"(no metrics recorded)\n"` (matches existing REQ-8 close contract; verified by `test_cli_inspect.py:296` staying green)
    - `"json"` / `"json-detailed"` → `"{}"` / `"[]"`
    - `"prometheus"` (PR#2) → `"# EOF\n"` per Prometheus convention for empty textfiles
  - [ ] GREEN: `_emit_error_and_exit(kind, **details)` per D9:
    - `kind="invalid --since value"` → exit `3` (data error)
    - `kind="invalid --percentile value"` → exit `3` (PR#2)
    - `kind="invalid --domain value"` → exit `2` (Click `click.Choice` handles natively; this helper is the fallback for non-Click-validated errors)
    - `kind="write failed"` → exit `4` (PR#2 `--out` failure)
    - All emit `{"error": "<kind>", **details}` to stderr; stdout stays clean
- **Commits:**
  1. `test(unit): RED fixtures for default_empty_payload + _emit_error_and_exit + D9 exit-code table`
  2. `feat(cli): default_empty_payload helper + _emit_error_and_exit per D8/D9 contracts`

#### T1.9 — Implement `_atomic_write_text` helper for `--out` flag per D10 + unit tests

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~50 impl + ~150 tests = ~200
- **Files:**
  - `src/flow_engineering/cli.py` (modify — add `_atomic_write_text(target: Path, text: str) -> int` helper per design §"Algorithm Details": `tempfile.NamedTemporaryFile(delete=False, dir=target.parent, suffix=".prom.tmp")` + `os.replace` + cleanup-on-failure)
  - `tests/unit/test_cli_metrics.py` (extend — `TestAtomicWrite` class with 5 RED fixtures: target written on success, partial-write rollback on simulated `os.replace` failure, parent-dir created if missing, `.tmp` cleaned up on failure, symlink target replaced atomically)
- **Dependencies:** none (PR#2 `--out` flag depends on this; landing early in PR#1 keeps PR#2 surface clean)
- **Acceptance criteria:**
  - [ ] RED: `test_atomic_write_writes_text_to_target` fails; `test_atomic_write_creates_parent_dir` fails; `test_atomic_write_replaces_existing_file` fails; `test_atomic_write_rolls_back_on_os_replace_failure` fails; `test_atomic_write_cleans_up_tmp_on_failure` fails
  - [ ] GREEN: `_atomic_write_text(target, text)` per design D10:
    - `target.parent.mkdir(parents=True, exist_ok=True)` (creates parent if missing)
    - `tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, dir=target.parent, suffix=".prom.tmp", prefix=".metrics-")`
    - `tmp.write(text); tmp.close(); os.replace(tmp.name, target)` (atomic on POSIX + Windows when same filesystem; `dir=target.parent` guarantees same filesystem)
    - On exception during write/replace: `try: os.unlink(tmp.name) except OSError: pass` + re-raise (caller emits exit-code-4 JSON error per D9)
    - Returns `len(text.encode("utf-8"))` (byte count for the stderr confirmation JSON)
  - [ ] GREEN: Target parent doesn't exist → `mkdir(parents=True)` creates it
  - [ ] GREEN: Disk-full mid-write → exception caught, `.tmp` cleaned up, helper re-raises (caller maps to exit 4)
- **Commits:**
  1. `test(unit): RED fixtures for _atomic_write_text with rollback + parent-dir + tmp-cleanup`
  2. `feat(cli): _atomic_write_text helper per D10 (reusable by PR#2 --out flag)`

#### T1.10 — CHANGELOG.md v0.7.0 entry + 6 SKILL.md "Metrics hook" runtime updates + integration tests

- **Type:** docs + integration
- **TDD phase:** N/A (docs) + RED → GREEN (integration tests)
- **LOC:** ~50 CHANGELOG + ~30 prose (~5 per file × 6) + ~200 integration tests = ~280
- **Files:**
  - `CHANGELOG.md` (modify — new `## [0.7.0] - 2026-06-27` section above `[0.6.0]`)
  - `~/.config/opencode/skills/sdd-propose/SKILL.md` (modify, runtime — NOT in repo)
  - `~/.config/opencode/skills/sdd-design/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-tasks/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-apply/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-verify/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-archive/SKILL.md` (modify, runtime)
  - `tests/integration/test_flow_metrics_pr1_integration.py` (NEW — 4-5 integration tests covering the full PR#1 surface: write 50 events across 4 domains via `observability.increment()`, run `flow metrics summary` / `flow metrics --summary --domain=snapshot` / `flow metrics --window=1h`, assert output shapes + exit codes)
- **Dependencies:** all T1.1..T1.9
- **Acceptance criteria:**
  - [ ] GREEN: CHANGELOG v0.7.0 entry lists:
    - `flow metrics summary [--since] [--until] [--domain] [--top] [--format]` text dashboard (REQ-35)
    - `flow metrics --since=<iso> [--until=<iso>] [--window=<1h|24h|7d>]` time-window filter (REQ-36)
    - `flow metrics --domain=<binding|drift|vector|snapshot|federated|backfill|metadata|engine>` cross-domain slice (REQ-37)
    - 6 BDD scenarios across 3 feature files (req35/req36/req37)
    - `openspec/specs/observability/spec.md` bootstrap (resolves `cross-project-federation` archive-report #61)
    - 3 read-side helpers + `DOMAIN_BY_PREFIX` + `ACCEPTED_DOMAINS` + `_atomic_write_text` helper
    - `flow metrics` and `flow metrics --json` remain byte-identical to v0.6.0 (REQ-8 close contract preserved)
  - [ ] GREEN: 6 SKILL.md files have `## Metrics hook` section (3-5 lines each) naming REQ-35/36/37 and referencing `flow metrics summary`, `flow metrics --window=1h`, `flow metrics --domain=snapshot`, `DOMAIN_BY_PREFIX` lookup, `_atomic_write_text` helper
  - [ ] GREEN: CHANGELOG entry follows `[0.6.0]` format (Added / Tests / Notes sections)
  - [ ] GREEN: Integration tests pass — `flow metrics summary` against a fresh 50-event JSONL renders the dashboard; `--window=1h` filters correctly; `--domain=snapshot` returns 0 events when no snapshot events exist
- **Commits:**
  1. `docs(release): CHANGELOG v0.7.0 entry + 6 SKILL.md metrics hooks`
  2. `test(integration): end-to-end integration tests for PR#1 surface (summary + window + domain)`

---

### PR#2 — Export + aggregation: Prometheus textfile + percentile / aggregation

#### T2.1 — Implement `prometheus_exposition` + `METRIC_TYPE_OVERRIDES` + unit tests (REQ-38 foundation)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~100 impl + ~200 tests = ~300
- **Files:**
  - `src/flow_engineering/observability.py` (modify — add `prometheus_exposition(events: list[dict], catalog: dict[str, str] | None = None) -> str` per design D6; add `METRIC_TYPE_OVERRIDES: dict[str, str] = {}` forward-compatible hook; export `_escape_label_value` helper for label-value escaping)
  - `tests/unit/test_observability.py` (extend — `TestPrometheusExposition` class with 6 RED fixtures: round-trip via `prometheus_client.parser.text_string_to_metric_families`, `_total` → counter, `_ms` / `_seconds` → summary, bare → gauge, label escaping (quotes/backslashes/newlines), empty input → `# EOF\n`)
- **Dependencies:** PR#1 merge (shared `observability.py` + `tests/fixtures/metrics/sample_24h.jsonl`)
- **Acceptance criteria:**
  - [ ] RED: `test_prometheus_exposition_round_trip_parses_cleanly` fails; `test_prometheus_exposition_total_suffix_emits_counter` fails; `test_prometheus_exposition_ms_suffix_emits_summary` fails; `test_prometheus_exposition_bare_name_emits_gauge` fails; `test_prometheus_exposition_empty_input_returns_eof_marker` fails; `test_prometheus_exposition_escapes_label_values` fails
  - [ ] GREEN: `prometheus_exposition(events)` per design D6:
    - Per counter (sorted alphabetically for stable output), emits `# HELP <name> <description>\n# TYPE <name> <type>\n` + one metric line per `(counter_name, label_tuple)` combination
    - Type derivation in priority order: (1) `METRIC_TYPE_OVERRIDES.get(name)` if present (v1 has zero overrides; forward-compatible hook); (2) suffix `_total` → `counter`; (3) suffix `_ms` or `_seconds` → `summary`; (4) bare name → `gauge`
    - Numeric values formatted via `repr(float)` (deterministic; no scientific-notation surprises)
    - Label values escaped: `"` → `\"`, `\` → `\\`, newline → `\n` (Prometheus textfile spec)
    - Empty input → returns `"# EOF\n"` per Prometheus convention
  - [ ] GREEN: `METRIC_TYPE_OVERRIDES: dict[str, str] = {}` (v1 empty; escape hatch for ambiguous REQ-42 `engine_*` counters later)
  - [ ] GREEN: Counter-name validation against `[a-zA-Z_][a-zA-Z0-9_]*`; invalid names fall into `"unknown"` bucket with a stderr warning (does NOT exit non-zero; defense in depth)
  - [ ] GREEN: Round-trip parseable by `prometheus_client.parser.text_string_to_metric_families()` (test-only dep)
- **Commits:**
  1. `test(unit): RED fixtures for prometheus_exposition (round-trip + suffix rules + label escaping)`
  2. `feat(observability): prometheus_exposition helper + METRIC_TYPE_OVERRIDES map + label escaping per D6`

#### T2.2 — Add `--prometheus` / `--out` flags to `flow metrics` + BDD req38 (REQ-38)

- **Type:** test + code + bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~150 impl + ~250 tests + ~120 BDD feature+step defs = ~520
- **Files:**
  - `src/flow_engineering/cli.py` (modify — extend `metrics` command with `--prometheus` and `--out=<path>` flags; reuse `_atomic_write_text` from T1.9 for atomic write; emit stderr JSON confirmation `{"wrote": "<path>", "metric_lines": <N>, "bytes": <N>}` on `--out` success)
  - `tests/unit/test_cli_metrics.py` (extend — `TestPrometheusExport` class with 6 RED fixtures: stdout exposition format, `--out=<path>` atomic write + stderr confirmation, `--out` write failure exits 4, `--out` parent-dir auto-creation, label escaping in CLI output, `--prometheus` with empty sink emits `# EOF`)
  - `tests/unit/test_observability_prometheus.py` (NEW — full textfile format coverage with 6 RED fixtures: HELP/TYPE emission, metric line shape, label tuple grouping, per-event sum across same `(counter_name, label_tuple)` pair, invalid counter name → unknown bucket + warning)
  - `tests/bdd/req38_metrics_prometheus.feature` (NEW — 3 BDD scenarios from spec REQ-38)
  - `tests/bdd/test_observability_steps.py` (extend — +step glue for REQ-38)
- **Dependencies:** T2.1, T1.9 (`_atomic_write_text` from PR#1)
- **Acceptance criteria:**
  - [ ] RED: `test_cli_metrics_prometheus_emits_textfile_format` fails; `test_cli_metrics_prometheus_with_out_writes_atomically` fails; `test_cli_metrics_prometheus_with_out_emits_stderr_confirmation` fails; `test_cli_metrics_prometheus_out_write_failure_exits_code_4` fails; `test_cli_metrics_prometheus_empty_sink_emits_eof` fails; `test_cli_metrics_prometheus_out_creates_parent_dir` fails
  - [ ] GREEN: `--prometheus` (without `--out`) emits Prometheus textfile exposition format to stdout; exits `0`; empty sink → `# EOF\n`
  - [ ] GREEN: `--prometheus --out=<path>` writes via `_atomic_write_text` (atomic; partial-write rollback per T1.9); emits stderr JSON `{"wrote": "<path>", "metric_lines": <N>, "bytes": <positive int>}` confirmation; exits `0`
  - [ ] GREEN: `--out` write failure (perm denied / disk full) → emits stderr JSON `{"error": "write failed", "path": "<path>", "cause": "<strerror>"}` + exits `4` (D9 I/O error)
  - [ ] GREEN: Numeric values across multiple events with the same `(counter_name, label_tuple)` pair are SUMMED (mirrors the existing `_summarize_metrics()` semantics at `cli.py:960`)
  - [ ] GREEN: BDD `req38_metrics_prometheus.feature` 3 scenarios verbatim from spec:
    1. `--prometheus` emits `# HELP drift_invoked_total ...\n# TYPE drift_invoked_total counter\ndrift_invoked_total{change="observability"} 1` to stdout; exits 0
    2. `--prometheus --out=<TMPDIR>/metrics.prom` writes a non-empty file matching stdout output; stderr contains `{"wrote": ..., "metric_lines": 3, "bytes": ...}`; exits 0
    3. `--prometheus --window=1h` with 10 `drift_invoked_total` events (5 in last 1h, 5 older) emits `drift_invoked_total ... 5` (in-window sum); out-of-window events excluded
- **Commits:**
  1. `test(unit): RED fixtures for --prometheus/--out flags + atomic write + exit-code-4 path`
  2. `feat(cli): --prometheus/--out flags on flow metrics + _atomic_write_text integration + stderr confirmation`
  3. `test(bdd): req38_metrics_prometheus feature with 3 scenarios + step glue extension`

#### T2.3 — Wire `--window` composition into `--prometheus` path (REQ-36/38 composition)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~50 impl + ~150 tests = ~200
- **Files:**
  - `src/flow_engineering/cli.py` (modify — ensure `--window` / `--since` / `--until` / `--domain` filters compose with `--prometheus` in the unified event-filter pipeline; refactor the `metrics()` handler to apply the same filter chain regardless of output format)
  - `tests/unit/test_cli_metrics.py` (extend — `TestFilterComposition` class with 4 RED fixtures: `--prometheus --window=1h` filters then exports, `--prometheus --domain=snapshot` filters then exports, `--prometheus --since=<iso>` filters then exports, `--prometheus` with all 3 filters applied AND-style)
- **Dependencies:** T2.2
- **Acceptance criteria:**
  - [ ] RED: `test_cli_metrics_prometheus_with_window_filters_in_window` fails; `test_cli_metrics_prometheus_with_domain_filters_to_domain` fails; `test_cli_metrics_prometheus_with_since_filters_after_timestamp` fails; `test_cli_metrics_prometheus_with_all_filters_compose_and_style` fails
  - [ ] GREEN: `--prometheus` honors ALL active filter flags (`--since`, `--until`, `--window`, `--domain`, `--top`); filter chain applied BEFORE `prometheus_exposition()` is invoked; metric line values reflect the post-filter event set
  - [ ] GREEN: No regression — `flow metrics` and `flow metrics --json` without `--prometheus` remain byte-identical to PR#1's behavior
- **Commits:**
  1. `test(unit): RED fixtures for --window/--domain/--since composition with --prometheus`
  2. `feat(cli): unified filter pipeline in metrics() handler — --prometheus honors all active filters`

#### T2.4 — Implement `aggregate()` + `percentile()` helpers using `statistics.quantiles` per D7 + unit tests (REQ-39 foundation)

- **Type:** test + code
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~80 impl + ~180 tests = ~260
- **Files:**
  - `src/flow_engineering/observability.py` (modify — add `aggregate(events: list[dict], field: str = "value") -> dict[str, float]` returning `{count, mean, stddev, min, max}`; add `percentile(events: list[dict], pct: int, field: str = "elapsed_ms") -> float | None` using `statistics.quantiles(data, n=100, method="inclusive")` per design D7)
  - `tests/unit/test_observability.py` (extend — `TestAggregate` class with 4 RED fixtures: synthetic 100-event dataset → `{count: 100, mean: 505.0, stddev: ~290.0, min: 10.0, max: 1000.0}`, single-sample → `stddev: 0.0`, empty input → zero-filled dict, non-numeric field skipped)
  - `tests/unit/test_observability.py` (extend — `TestPercentile` class with 5 RED fixtures: synthetic 10..1000 dataset → `p50 = 505.0`, `p95 = 950.5 ±0.5`, `p99 ≈ 990.1`; single-sample → `None`; empty input → `None`; non-numeric field → `None`; `pct=50/95/99` validation; invalid `pct` raises `ValueError`)
- **Dependencies:** PR#1 merge (shared `tests/fixtures/metrics/sample_24h.jsonl`)
- **Acceptance criteria:**
  - [ ] RED: `test_aggregate_synthetic_dataset_returns_correct_stats` fails; `test_aggregate_single_sample_stddev_zero` fails; `test_aggregate_empty_input_zero_filled` fails; `test_percentile_synthetic_10_to_1000_p95_is_950_5` fails; `test_percentile_single_sample_returns_none` fails; `test_percentile_invalid_pct_raises_value_error` fails
  - [ ] GREEN: `aggregate(events, field)`:
    - Filters events to those with `isinstance(fields[field], (int, float)) and not isinstance(fields[field], bool)`
    - Returns `{"count": len(samples), "mean": statistics.mean(samples), "stddev": statistics.stdev(samples) if len(samples) >= 2 else 0.0, "min": min(samples), "max": max(samples)}`
    - Empty input → `{"count": 0, "mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}`
    - Single sample → `stddev: 0.0` (NOT an error)
  - [ ] GREEN: `percentile(events, pct, field)`:
    - Filters events to numeric samples in `fields[field]`
    - `len(samples) < 2` → returns `None` (caller emits "insufficient data" warning)
    - `samples` sorted, then `q = statistics.quantiles(samples, n=100, method="inclusive")`; returns `q[pct - 1]`
    - Synthetic `list(range(10, 1001, 10))` → `percentile(_, 95) == 950.5` (linear interpolation per REQ-39 scenario 1)
    - `pct` not in `{50, 95, 99}` → raises `ValueError` (defensive; CLI validates at parse time via `click.Choice`)
- **Commits:**
  1. `test(unit): RED fixtures for aggregate (mean/stddev/min/max) + percentile (statistics.quantiles per D7)`
  2. `feat(observability): aggregate + percentile helpers using statistics.quantiles per D7`

#### T2.5 — Add `--percentile` / `--aggregations` / `--field` flags to `flow metrics` + BDD req39 (REQ-39)

- **Type:** test + code + bdd
- **TDD phase:** RED → GREEN → REFACTOR
- **LOC:** ~100 impl + ~150 tests + ~100 BDD feature+step defs = ~350
- **Files:**
  - `src/flow_engineering/cli.py` (modify — extend `metrics` command with `--percentile=<p50|p95|p99>`, `--aggregations`, `--field=<name>` flags; `click.Choice(["p50", "p95", "p99"], case_sensitive=False)` validates `--percentile`; emit stdout line `<counter_name> <percentile>: <value>` per counter; emit `<counter_name> {count, mean, stddev, min, max}` per counter for `--aggregations`)
  - `tests/unit/test_cli_metrics.py` (extend — `TestPercentileAggregation` class with 5 RED fixtures: `--percentile=p95 --domain=vector` emits correct line, `--percentile=garbage` exits 3, `--aggregations` emits stats line per counter, `--field=value` switches from default `elapsed_ms`, insufficient-data warning on stderr + exit 0)
  - `tests/unit/test_observability_aggregate.py` (NEW — percentile correctness on synthetic 10..1000 dataset; aggregate stats shape; `--field` switching; insufficient-data warning shape)
  - `tests/bdd/req39_metrics_percentile.feature` (NEW — 2 BDD scenarios from spec REQ-39)
  - `tests/bdd/test_observability_steps.py` (extend — +step glue for REQ-39)
- **Dependencies:** T2.4
- **Acceptance criteria:**
  - [ ] RED: `test_cli_metrics_percentile_p95_emits_correct_line` fails; `test_cli_metrics_percentile_garbage_exits_code_3` fails; `test_cli_metrics_aggregations_emits_stats_per_counter` fails; `test_cli_metrics_field_value_switches_from_default` fails; `test_cli_metrics_insufficient_data_warns_and_exits_zero` fails
  - [ ] GREEN: `--percentile=<p50|p95|p99>`:
    - `click.Choice(["p50", "p95", "p99"], case_sensitive=False)` validates at flag-parse time → invalid value exits `2` (D9 usage-error); defensively `ValueError` from helper exits `3`
    - For each counter with ≥2 numeric samples in `fields[field]`: emit `<counter_name> <percentile>: <value>` line to stdout
    - For each counter with <2 numeric samples: emit `<counter_name> <percentile>: insufficient data` line to stdout + stderr JSON warning `{"warning": "not enough data points for percentile", "counter": "<name>", "count": <N>}` (D7); command STILL exits `0` (warning, not error)
  - [ ] GREEN: `--aggregations`: for each counter with ≥1 numeric sample, emit `<counter_name> {count: N, mean: X, stddev: Y, min: A, max: B}` line to stdout; independent of `--percentile` (both MAY be combined)
  - [ ] GREEN: `--field=<name>` default `"elapsed_ms"`; switches percentile + aggregations to operate on different event-field key (e.g., `value`, `count`, or any `fields` key)
  - [ ] GREEN: BDD `req39_metrics_percentile.feature` 2 scenarios verbatim from spec:
    1. `--percentile=p95 --domain=vector` with 100 events for `vector_search_latency_ms` (elapsed_ms 10..1000) emits `vector_search_latency_ms p95: 950.5` (±0.5 tolerance); exits 0
    2. `--percentile=p95 --domain=drift` with 1 event for `drift_scan_duration_ms` (elapsed_ms=42) emits `drift_scan_duration_ms p95: insufficient data` + stderr JSON warning; command STILL exits 0
- **Commits:**
  1. `test(unit): RED fixtures for --percentile/--aggregations/--field flags + insufficient-data warning`
  2. `feat(cli): --percentile/--aggregations/--field flags on flow metrics + observability.percentile/aggregate integration`
  3. `test(bdd): req39_metrics_percentile feature with 2 scenarios + step glue extension`

#### T2.6 — End-to-end integration tests: write 100 mock metrics across 4 domains → run all 5 surfaces

- **Type:** integration tests
- **TDD phase:** RED → GREEN
- **LOC:** ~30 helper + ~250 tests = ~280
- **Files:**
  - `tests/integration/test_flow_metrics_pr2_integration.py` (NEW — 5-6 integration tests covering the full PR#2 surface: write 100 mock metrics across 4 domains (binding, drift, vector, snapshot), run all 5 surfaces, assert outputs)
- **Dependencies:** T2.1, T2.2, T2.3, T2.4, T2.5
- **Acceptance criteria:**
  - [ ] RED: `test_e2e_summary_then_window_then_domain_then_prometheus_then_percentile` fails
  - [ ] GREEN: Integration test writes 100 events via `observability.increment()` across 4 domains (binding: 20, drift: 30, vector: 30, snapshot: 20), with 50% in last 1h and 50% older
  - [ ] GREEN: `flow metrics summary` renders dashboard with correct totals + by-domain + top-N
  - [ ] GREEN: `flow metrics --window=1h` filters to the 50 in-window events
  - [ ] GREEN: `flow metrics --domain=vector` filters to the 30 vector events only
  - [ ] GREEN: `flow metrics --prometheus` emits parseable textfile format
  - [ ] GREEN: `flow metrics --percentile=p95 --field=elapsed_ms` emits correct percentile lines for the latency-bearing events
  - [ ] GREEN: All 5 surfaces exit 0; no stderr noise; stdout clean for piping
- **Commits:**
  1. `test(integration): end-to-end integration tests for PR#2 surface (100 mock metrics → all 5 surfaces)`

#### T2.7 — CHANGELOG.md v0.7.1 (incremental) + 6 SKILL.md "Export hook" + "Aggregation hook" runtime updates + apply-progress/finalize

- **Type:** docs + apply-closeout
- **TDD phase:** N/A (docs)
- **LOC:** ~50 CHANGELOG + ~60 prose (~10 per file × 6) + ~40 apply-progress/finalize = ~150
- **Files:**
  - `CHANGELOG.md` (modify — add `## [0.7.1] - 2026-06-27` section above `[0.7.0]`; incremental from PR#1's v0.7.0 entry)
  - `~/.config/opencode/skills/sdd-propose/SKILL.md` (modify, runtime — extend "Metrics hook" with "Export hook" + "Aggregation hook" subsections)
  - `~/.config/opencode/skills/sdd-design/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-tasks/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-apply/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-verify/SKILL.md` (modify, runtime)
  - `~/.config/opencode/skills/sdd-archive/SKILL.md` (modify, runtime)
- **Dependencies:** all T2.1..T2.6
- **Acceptance criteria:**
  - [ ] GREEN: CHANGELOG v0.7.1 entry lists:
    - `flow metrics --prometheus [--out=<path>]` Prometheus textfile exporter (REQ-38)
    - `flow metrics --percentile=<p50|p95|p99> [--field=<name>] [--aggregations]` percentile + statistical aggregation (REQ-39)
    - 5 BDD scenarios across 2 feature files (req38/req39)
    - `prometheus_exposition` helper + `METRIC_TYPE_OVERRIDES` forward-compatible hook (D6)
    - `aggregate` + `percentile` helpers using `statistics.quantiles` per D7
    - `--out` atomic write via `_atomic_write_text` (D10) — partial-write rollback
    - Exit codes 2/3/4 per D9 contract; `--since=garbage` exits 3; `--out` write failure exits 4
  - [ ] GREEN: 6 SKILL.md files extend `## Metrics hook` with `## Export hook` (REQ-38; `--prometheus` + `--out` + textfile format) and `## Aggregation hook` (REQ-39; `--percentile` + `--aggregations` + `--field` + `statistics.quantiles` per D7) subsections (3-5 lines each)
  - [ ] GREEN: CHANGELOG entry follows the `[0.7.0]` format (Added / Tests / Notes sections)
  - [ ] GREEN: Apply-progress/finalize: confirm 801+ existing tests pass + new PR#2 tests pass + `ruff check` clean + `flow metrics` and `flow metrics --json` remain byte-identical to v0.6.0 (REQ-8 close contract preserved across both PRs)
- **Commits:**
  1. `docs(release): CHANGELOG v0.7.1 entry + 6 SKILL.md export/aggregation hooks + apply-finalize`

---

## Apply Batches (≤3 tasks OR ≤150 LOC prod per delegation)

Per-delegation batch ceiling from Engram #112 pattern (`apply-batches-split-into-6-tasks-per-delegation`). Default delegate runtime is ~15 min; larger batches TIMEOUT.

### PR#1 batches (5 batches)

| Batch | Tasks | LOC (impl + test) | Why |
|-------|-------|-------------------|-----|
| **A** | T1.1 + T1.2 + T1.3 | ~1400 | Foundation helpers + summary CLI + spec bootstrap — atomic foundation; 6 commits RED → GREEN → REFACTOR cycle; **TIMEOUT RISK BATCH** |
| **B** | T1.4 + T1.5 | ~650 | Window filter helper + `--since`/`--until`/`--window` flags + BDD req36 (2 scenarios) |
| **C** | T1.6 + T1.7 | ~580 | DOMAIN_BY_PREFIX validation + `--domain`/`--top` flags + BDD req37 (2 scenarios) |
| **D** | T1.8 + T1.9 | ~480 | Default-empty handling + exit-code helpers per D8/D9 + atomic write helper per D10 (reused by PR#2 `--out`) |
| **E** | T1.10 | ~280 | CHANGELOG v0.7.0 + 6 SKILL.md runtime updates + integration tests sweep |

**Batch A risk mitigation:** at ~1400 LOC, batch A is the highest timeout risk (~4h at ~6 LOC/min). If delegation hits 15-min ceiling mid-batch, abort and split:

- **A1** = T1.1 (foundation helpers + fixture) + T1.3 (spec bootstrap — independent docs commit) — ~800 LOC; library cohesion
- **A2** = T1.2 (summary CLI + BDD req35) — ~500 LOC; CLI-only work

If sub-agent reports progress as "foundation helpers + spec bootstrap landed, summary CLI remaining", abort and launch A2 as continuation.

### PR#2 batches (3 batches)

| Batch | Tasks | LOC (impl + test) | Why |
|-------|-------|-------------------|-----|
| **F** | T2.1 + T2.2 + T2.3 | ~1020 | Prometheus exposition helper + `--prometheus`/`--out` flags + BDD req38 (3 scenarios) + `--window` composition — **TIMEOUT RISK BATCH** |
| **G** | T2.4 + T2.5 | ~610 | Aggregate + percentile helpers + `--percentile`/`--aggregations`/`--field` flags + BDD req39 (2 scenarios) |
| **H** | T2.6 + T2.7 | ~430 | End-to-end integration tests sweep + CHANGELOG v0.7.1 + 6 SKILL.md runtime updates |

**Batch F risk mitigation:** at ~1020 LOC, batch F is the second-highest timeout risk (~2.8h at ~6 LOC/min). If delegation hits 15-min ceiling mid-batch, abort and split:

- **F1** = T2.1 (prometheus_exposition helper) — ~300 LOC; library-only work
- **F2** = T2.2 + T2.3 (`--prometheus`/`--out` CLI + `--window` composition + BDD req38) — ~720 LOC; CLI + BDD cohesion

If sub-agent reports progress as "prometheus_exposition helper landed, CLI + BDD remaining", abort and launch F2 as continuation.

### Branch targeting

- **PR#1 → `main`.** Branch from `main`; merge to `main` after batch E completes + `uv run pytest` is green + 801+ existing tests pass.
- **PR#2 → `main`.** Branch from PR#1's merge commit (NOT from `main` pre-merge; per Engram #114 stacked-to-main pattern). Cherry-pick additive changes only. Merge to `main` after batch H completes + full PR#1 + PR#2 test suites pass + `ruff check` clean.
- **Squash merge** for both PRs (preserves linear history, single commit `feat: observability v0.7.0` + `feat: observability v0.7.1`).
- Each batch's commits land on the PR branch; PR merges after the final batch completes.
- **MANDATORY**: PR#1 merge to `main` MUST complete BEFORE PR#2 apply starts (stacked-to-main pattern #114).

---

## Patterns Honored

- **`apply-batches-split-into-6-tasks-per-delegation`** (Engram #112): each batch ≤3 tasks (PR#1 A=3, B=2, C=2, D=2, E=1; PR#2 F=3, G=2, H=2)
- **`apply-under-strict-tdd-grows-5-6x-beyond-forecast`** (#113): design ×2.9 multiplier is the project-specific band for observability (lower than change #5's ×6 because observability has more library-code reuse); real ratio could be ×4-5 for the CLI-heavy batches — forecast absorbs the multiplier
- **`work-unit-commits`** skill: per-commit work-unit splits to mitigate 400-line review budget (6 work-unit commits per PR, each ≤400 LOC)
- **`stacked-to-main-requires-merging-prior-pr-before-next-apply`** (#114): MERGE PR#1 to `main` BEFORE launching PR#2 apply

---

## Open follow-ups for sdd-archive (after both PRs merge)

| # | Item | Owner |
|---|------|-------|
| 1 | Confirm `openspec/specs/observability/spec.md` is the project baseline pattern; retro-fill prior capability specs (`openspec/specs/decision-code-linking/spec.md`, etc.) on a future change | sdd-archive |
| 2 | Bump `pyproject.toml` version `0.6.0` → `0.7.1` (matches the dual CHANGELOG entries; verify the `uv version` workflow) | sdd-archive |
| 3 | Verify `MEMORY.md` or AGENTS.md mentions `flow metrics summary` + `flow metrics --prometheus` workflow for future contributors | sdd-archive |
| 4 | Cross-impact: confirm all 5 prior changes (REQ-1..34) tests stay green; observability is purely additive (REQ-8 close contract preserved) | sdd-archive |
| 5 | Update README to mention the new `~/.flow-engineering/registry.json` + the 12 new `flow metrics` flags + the Prometheus textfile exporter | sdd-archive |
| 6 | Consider follow-up changes for v1.1 deferred items: REQ-40 (label-based query), REQ-41 (threshold alerting), REQ-42 (`engine_*` counters), REQ-43 (federation-aware events), REQ-44 (JSONL rotation) | sdd-archive |
| 7 | Verify `_atomic_write_text` reuse: confirm `flow projects alias` (cross-project-federation T1.10) already uses the same `tempfile + os.replace` pattern; if not, factor into a shared `cli_io.py` helper on a future change | sdd-archive |

---

## Structured Metadata

- **status:** success
- **confidence:** high
- **total_tasks:** 17 (T1.1..T1.10 PR#1 + T2.1..T2.7 PR#2)
- **pr_split:** 2 chained PRs (PR#1 foundation + PR#2 export+aggregation)
- **forecast_loc_production:** ~1936 (~1200 PR#1 + ~736 PR#2)
- **forecast_loc_test:** ~3872 (~2400 PR#1 + ~1472 PR#2)
- **forecast_loc_grand_total:** ~5808
- **forecast_loc_realistic_x2.9:** ~16 800
- **batches:** 8 (PR#1: A=3 + B=2 + C=2 + D=2 + E=1 = 10 tasks; PR#2: F=3 + G=2 + H=2 = 7 tasks)
- **pr1_batch_a_timeout_risk:** HIGH (~1400 LOC; mitigation = split into A1 + A2 if delegation hits 15-min ceiling)
- **pr2_batch_f_timeout_risk:** HIGH (~1020 LOC; mitigation = split into F1 + F2 if delegation hits 15-min ceiling)
- **review_workload_forecast:**
  - `pr1_400_line_budget_risk`: high (~3600 LOC; ~10 400 realistic; 6 work-unit commits per `work-unit-commits` convention)
  - `pr2_400_line_budget_risk`: medium (~2208 LOC; ~6400 realistic; 4 work-unit commits per `work-unit-commits` convention)
  - `chained_prs_recommended`: yes (per proposal #194 + design #197 D12; ×2.9 TDD multiplier)
  - `decision_needed_before_apply`: no (chained-pr strategy is explicit in proposal #194)
- **strict_tdd:** on (RED → GREEN → REFACTOR per task; per `decision-code-linking` precedent)
- **bdd_feature_files:** 5 NEW (req35_metrics_summary, req36_metrics_window, req37_metrics_domain, req38_metrics_prometheus, req39_metrics_percentile)
- **bdd_scenarios:** 11 (REQ-35:2 + REQ-36:2 + REQ-37:2 + REQ-38:3 + REQ-39:2)
- **out_of_scope_count:** 15 (REQ-40..44 v1.1 defers + 10 v2 defers)
- **file_created:** `C:\dev\proyects\flow-engineering\openspec\changes\observability\tasks.md`
- **next_recommended:** `sdd-apply observability PR#1 batch A` (T1.1 + T1.2 + T1.3, ~1400 LOC, ~25-30 min)