# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/).

## [0.8.0] - 2026-06-27

### Added
- `flow prompt-registry` Python API in `src/flow_engineering/prompt_registry.py` (REQ-45).
- `PromptRegistry` (module-level catalog) + `PromptDef` frozen dataclass + `PromptDomain` enum + `PROMPT_NAMES` catalog with 4 migrated entries (`strict_tdd`, `auto_suggest_header`, `auto_suggest_footer`, `auto_suggest_empty`) (REQ-45).
- `render_prompt(name, **kwargs)` Jinja2-based renderer with `StrictUndefined` + `render_prompt_safe()` sentinel-substitution helper + `list_required_vars(name)` AST introspection helper (REQ-46, D3 + D4).
- `validate_catalog()` + `lint_prompts()` validators with `LintError` + `LintReport` types; detects duplicate names, invalid domains, undefined Jinja2 vars, malformed Jinja2 syntax, invalid SemVer (REQ-47, 5 error codes per D7).
- 7 `SKILL.md` runtime files carry the `## Prompt registry hook` section (sdd-propose, sdd-design, sdd-tasks, sdd-apply, sdd-verify, sdd-archive + future sdd-init / sdd-explore / sdd-spec / sdd-onboard land in PR#2) (added in batch C).
- `openspec/specs/prompt-registry/spec.md` bootstrapped (mirrors change #6 observability pattern; resolves next capability spec pattern per D12).

### Tests
- 1078 / 1078 tests passing (`uv run pytest`; +15 unit tests for `render_prompt`/`render_prompt_safe`/`list_required_vars` + 7 BDD scenarios for req45/46/47).
- 32 BDD scenarios across 18 feature files (+7 this PR).
- See `openspec/changes/archive/2026-06-27-prompt-registry-pr1/` for full spec, design, and task breakdown.

### Notes
- `prompt-registry` change #7 PR#1 (foundation + validation + lint + render) shipped with 3 batches (A + B + C) in ~7 work-unit commits.
- Strict TDD throughout; 4 inline prompt constants migrated to PromptRegistry thin wrappers per D10 alias convention (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`).
- The existing 4 prompt templates use Python `.format()` style (`{test_command}`); `render_prompt()` uses Jinja2 `{{ var }}` syntax (new prompts registered via `register()` exercise the substitution path).
- Verify report: TBD (sdd-verify next).

### Out-of-scope reminders (carried to PR#2)
- REQ-49 OpenCode SKILL.md catalog (`SKILL_CATALOG` + `check_drift` + `init_checksums` / `update_checksums` + sidecar JSON) (PR#2)
- REQ-50 `flow prompts` CLI subcommand (`list` / `show <id>` / `lint` / `check` + 7 flags) (PR#2)
- REQ-48 Golden regression tests (deferred to v1.1)
- REQ-51 `prompt_renders.jsonl` append-only sink (deferred to v1.1)
- REQ-52 Prompt observability counters (deferred to v1.1; will land in `observability.py` per D10)
- REQ-53 `docs/prompts.md` generated from registry (deferred to v1.1)
- REQ-54 `min_sdd_skill_versions` enforcement (deferred to v1.1)
- Per-prompt LLM provider routing (deferred to v1.1)
- Prompt A/B testing infrastructure (deferred to v1.1)

## [0.8.0] - TBD (in development)

### Breaking changes (planned)

- `decision_drift.Finding.decision_id` changes from `str` to `int` (REQ-57 migration; DeprecationWarning shim for v0.8.0, removed in v0.9.0)
- `decision_drift.DriftReport.scanned_at` changes from `float` to `str` ISO 8601 (REQ-57)
- `decision_drift.DriftReport.graph_unavailable: bool` + `unable_reason: str | None` (replaces `unable_to_verify: bool`) (REQ-57)
- `classify_binding(ref, graph_nodes)` 2-arg signature (was 3 args)

### Added (planned)

- `DriftEventLog` JSONL append-only writer at `~/.flow-engineering/drift_events.jsonl` (REQ-55)
- Daemon still-valid silence per REQ-56
- 21 BDD scenarios covering REQ-10/12/13/14/16 (REQ-58)
- SnapshotMeta.size_bytes + PruneResult.freed_bytes field reconciliation (REQ-59)
- `snapshot_pruned_total` legacy counter deprecation note (W23)
- stderr WARN on skipped non-int decision_id in `_write_back_findings` (S2)

## [0.7.1] - 2026-06-27

### Added
- `flow metrics export` CLI subcommand with `--format text|json|prometheus`, `--out PATH`, `--window/--since/--until/--domain` flags (REQ-38).
- `flow metrics aggregate` CLI subcommand with `--percentile p50|p95|p99` (repeatable), `--reservoir-size`, `--window/--since/--until/--domain`, `--format text|json` flags (REQ-39).
- `prometheus_exposition()` helper + `PrometheusMetric` dataclass + `write_prometheus_textfile()` atomic writer (REQ-38, D6 monotonic counter semantics + D10 atomic write).
- `aggregate_percentile()` helper + `ReservoirSampler` class (Vitter's Algorithm R) + `format_percentile_report()` text formatter (REQ-39, D7 reservoir sampling).
- `aggregate_many()` multi-percentile helper (W5 carry-forward from PR#1; reconciles design D7 dict[str, float] contract).
- `flow metrics aggregate` exit code 2 on invalid percentile; exit 0 on graceful "not enough data points".
- 6 SKILL.md runtime files carry the `## Export hook` + `## Aggregation hook` sections (added in batch H).

### Modified
- `src/flow_engineering/observability.py` — added prometheus_exposition, aggregate_percentile, ReservoirSampler, format_percentile_report; aggregate() signature drift (W5) reconciled via aggregate_many() back-compat shim.

### Tests
- 953 / 953 tests passing (`uv run pytest`).
- 25 BDD scenarios across 15 feature files (req35 + req36 + req37 + req38 + req39 + req17..req22 + req32 + req33 + req34 — 5 new scenarios this PR).
- See `openspec/changes/archive/2026-06-27-observability-pr2/` for full spec, design, and task breakdown.

### Notes
- `observability` change #6 PR#2 (Prometheus export + percentile aggregation) shipped with 3 batches (F + G + H) in 11 work-unit commits.
- Strict TDD throughout; ×2.9 LOC multiplier realized as planned.
- W5 (aggregate() signature drift) resolved in batch F via aggregate_many() shim.
- Verify report: PASS WITH WARNINGS (6W + 4S); C1 + W1-W6 + S1-S4 resolved; W23/W25/W26 deferred to drift-hardening cluster. See `openspec/changes/observability/verify-report-pr2.md`.

## [0.7.0] - 2026-06-27

### Added
- `flow metrics summary` CLI subcommand with `--format text|json|json-detailed`, `--window 1h|24h|7d|30d|<custom>`, `--since/--until ISO8601`, `--domain <name>` flags (REQ-35, REQ-36, REQ-37).
- 6 pure read functions in `observability.py`: `MetricEvent`, `read_all_metrics`, `read_events_since`, `read_events_by_domain`, `summarize`, `prometheus_exposition`, `aggregate`, `atomic_write_text` (REQ-35..37 foundation).
- `read_and_summarize()` helper + `MetricsSummaryResult` dataclass + 4 exit code constants (EXIT_OK=0, EXIT_INVALID_VALUE=2, EXIT_MALFORMED_METRICS=3, EXIT_WRITE_FAILURE=4).
- `DOMAIN_BY_PREFIX` lookup table expanded from 4 to 8 domains (binding, drift, vector, snapshot, backfill, federated, metadata, engine) — REQ-37 widening.
- `WINDOW_PATTERNS` table + `parse_window()` helper supporting presets (1h/24h/7d/30d) and custom `<int><h|d>` format — REQ-36.
- `openspec/specs/observability/spec.md` bootstrapped (resolves cross-project-federation archive-report #61).
- 6 `SKILL.md` runtime files carry the `## Metrics hook` section (added in batch E).

### Tests
- 868 / 868 tests passing (`uv run pytest`) — was 862 at PR#1 landing, +6 added by the verify sweep (incl. C1 regression gate for production counter names).
- 6 new BDD scenarios (req35 ×2 + req36 ×2 + req37 ×2) for a total of 136 BDD scenarios across 12 feature files.
- See `openspec/changes/archive/2026-06-27-observability-pr1/` for full spec, design, and task breakdown.

### Notes
- `observability` change #6 PR#1 (foundation + summary + window + slice) shipped with 5 batches (A + B + C + D + E) in 24 work-unit commits.
- Strict TDD throughout; 2.9x LOC multiplier realized as planned (read-side helpers are pure functions, lighter than CLI-heavy changes).
- PR#2 (Prometheus export + percentile aggregation) lands in a follow-up commit on the same change.

### Out-of-scope reminders (carried to PR#2)
- REQ-38 Prometheus textfile export (PR#2)
- REQ-39 percentile aggregation (PR#2)
- JSONL rotation policy (REQ-44, deferred to v1.1)
- Federation-aware metrics (REQ-43, deferred to v1.1)
- Grafana dashboard export (deferred to v1.1)
- OpenTelemetry push (deferred to v1.1)

## [0.6.0] - 2026-06-27

### Added
- `SnapshotManager` class in `src/flow_engineering/snapshot_manager.py` with `create()`, `list()`, `show()`, `diff()`, `rollback()`, `prune()` methods (REQ-28, REQ-29, REQ-30, REQ-31, REQ-32, REQ-34).
- `flow snapshot` CLI subcommand group: `create`, `list`, `show`, `diff`, `rollback`, `prune` (REQ-28..34).
- `flow drift <change> --snapshot <snap_id>` flag for pinned-state scans (REQ-33, NON-BREAKING).
- 4 observability counters: `snapshot_create_total`, `snapshot_rollback_total`, `snapshot_prune_total`, `snapshot_load_failed_total` (REQ-26). Wired in `SnapshotManager.create/rollback/prune` and `decision_drift._load_graph_from_snapshot`.
- `record_snapshot_event(counter_name, **labels)` helper in `observability.py` (mirrors `record_vector_summary`, `record_drift_summary`).
- `PruneResult` dataclass + `PruneNoFilterError` + `PruneSafetyGateError` exception classes.
- `SnapshotMeta.pinned` field for retention-pin semantics.
- 6 `SKILL.md` runtime files carry the Graph snapshots hook section.

### Tests
- 799 / 799 tests passing (`uv run pytest`).
- 14 BDD scenarios across 14 feature files (req3 + req9 + req15 + req17..req22 + req32 + req33 + req34) — added `req34_snapshot_prune` (2 scenarios).
- See `openspec/changes/archive/2026-06-27-graph-snapshots/` for full spec, design, and task breakdown.

### Notes
- `graph-snapshots` shipped via a single PR with 17 work-unit commits (8 from batches A + B1 + B2 + 3 from batch C T1.6 + 2 from T1.7 + 2 from T1.8 + 2 docs/housekeeping).
- Strict TDD throughout; 4-6x LOC multiplier realized as planned.
- Verify report: TBD (sdd-verify next).

## [0.5.0] - 2026-06-26

### Added
- `EngramBackend.mem_search_federated(query, projects=None, limit=10, since=None, type_filter=None)` on the `EngramBackend` ABC v1.2 — NON-BREAKING default `NotImplementedError`; the `InMemoryBackend` fixture overrides with `project`/`since`/`type_filter` SQL filters (REQ-23).
- `flow search --federated --projects=<csv> --since=<iso> --type=<csv>` flags on the existing `flow search` subcommand — explicit cross-project search; the existing single-project behavior is preserved when `--federated` is omitted (REQ-25).
- `flow projects alias <old> <new>` subcommand — appends to `~/.config/flow-engineering/project-aliases.json`; aliases are applied transparently to all `project` reads (e.g., `flow-image-generator-v2` queries resolve to `flow-image-generator-main` rows) (REQ-27).
- `flow projects backfill [--dry-run] [--confirm] [--since=<iso>] [--project=<key>]` subcommand — `--dry-run` is the DEFAULT (preview only); `--confirm` is REQUIRED to write; emits a JSON report `{would_change, would_skip, changes: [...]}`; iterates the alias map when neither `--project` nor a config override is set (REQ-24).
- `src/flow_engineering/project_detector.py` with `detect(cwd: Path) -> str | None` and `apply_tag(observation_id, project, *, backend)` — cwd-based detection under `~/dev/proyects/<name>/` or `~/proyects/<name>/`; returns `None` outside projects dir; opt-in via `FLOW_AUTO_PROJECT_TAG=1` env var (REQ-24).
- `src/flow_engineering/project_aliases.py` — versioned JSON schema `{version: 1, aliases: [{old, new, created_at}]}`; loaded on startup; cache-friendly; malformed JSON fails fast on startup with `AliasConfigError` (REQ-27).
- `~/.config/flow-engineering/project-aliases.json` — new runtime config file; created on first `flow projects alias` invocation; does NOT auto-backfill (user runs `flow projects backfill` separately) (REQ-27).
- 3 new observability counters: `federated_search_invoked_total{trigger=cli|programmatic}` (counter), `federated_search_projects_queried{count=N}` (histogram — note: no `_total` suffix per design D4), `federated_search_results_returned_total` (counter). Helper `record_federated_summary(invoked, projects_queried, results_returned, *, trigger="programmatic")` emits all 3 in one call; wired into `InMemoryBackend.mem_search_federated` (REQ-26).
- `record_federated_summary(...)` helper in `observability.py` mirroring the `record_drift_summary` (REQ-9) and `record_vector_summary` (REQ-22) pattern — consistent observability contract across all 3 history features.
- 5 new BDD feature files: `req23_federated_search.feature` (5), `req24_project_detector.feature` (6), `req25_cli_federated.feature` (5), `req26_federated_observability.feature` (4), `req27_project_aliases.feature` (5). Total BDD: 25 new scenarios across 5 files.
- ABC bumped v1.1 → v1.2 — third-party `EngramBackend` subclasses import unchanged; new `mem_search_federated` defaults to `NotImplementedError`.

### Tests
- 699 / 699 tests passing (`uv run pytest -x --tb=short`).
- 25 new BDD scenarios across 5 feature files. Total BDD: 116 scenarios across 23 feature files.
- See `openspec/changes/cross-project-federation/` for full spec, design, and task breakdown (post-archive).

### Notes
- `cross-project-federation` shipped as a SINGLE PR (no chained PRs needed; the change is small enough at ~600 prod LOC + ~1500 test LOC).
- **Important correction surfaced by explore**: the original premise of "7 separate Engram DBs" was wrong — there's ONE shared SQLite at `~/.engram/engram.db` with 158 observations across 9 project keys, FTS5 already indexed by `project`. The "federation" is therefore a logical surface (filtered SQL queries on the shared DB), not physical cross-DB infra.
- Alias resolution is applied in `mem_search_federated` and `flow projects backfill` (both forward and reverse: queries for `old` name resolve to `new`, queries for `new` name also match observations tagged with the `old` name).
- Backfill safety gate is strict: `--dry-run` is default; `--confirm` is mandatory to write; never auto-tag. This is the same safety posture as `flow reindex` (REQ-21) and `flow drift` (REQ-9).

## [0.4.0] - 2026-06-26

### Added
- `flow search --semantic <query>` flag on the existing `flow search` subcommand — explicit semantic search via embeddings (one-shot override; REQ-17).
- `flow search --hybrid --alpha <float> --k <int>` flag pair — hybrid semantic + FTS5 scoring with linear combo `α·cosine + (1−α)·normalize_bm25(fts)` (REQ-18). `α` validated to `[0.0, 1.0]`.
- `flow reindex [--batch-size=100] [--dry-run]` subcommand — sync streaming reindex of the Engram corpus into the sqlite-vec store, idempotent via `INSERT OR REPLACE`, crash-resume via per-batch transactions (REQ-21).
- `HybridBackend` composition wrapper at `src/flow_engineering/hybrid_backend.py` exposing `mem_search_semantic` + `mem_search_hybrid` on top of any `EngramBackend` (NON-BREAKING; ABC v1.1; default `NotImplementedError` preserved).
- `EmbeddingProvider` ABC at `src/flow_engineering/embedding_provider.py` with `MockEmbeddingProvider` (deterministic hash-based 384-dim vectors) and `SentenceTransformersProvider` (real model `sentence-transformers/all-MiniLM-L6-v2`, lazy `torch` import at instance time).
- sqlite-vec storage at `src/flow_engineering/vectors/sqlite_vec_store.py` — `observation_embeddings` audit table (`BLOB(1536)` = 384 × float32) + `vec_observations` `vec0` virtual table for KNN (REQ-20). Persisted at `~/.flow-engineering/vectors.sqlite`.
- `[vectors]` optional extra in `pyproject.toml` (`sqlite-vec>=0.1.0,<0.2`, `sentence-transformers>=2.0`). Default install pulls ZERO heavy deps; the gate fires only when both the extra AND `FLOW_VECTOR_SEARCH=1` are present. (`torch` is installed separately via `pip install --index-url https://download.pytorch.org/whl/cpu torch`.)
- `vector_search_invoked_total{trigger=cli|programmatic}`, `vector_search_results_returned_total`, `vector_search_latency_ms` (histogram with P50/P95/P99), `vector_index_size_observations` (gauge), `reindex_observations_total` (counter), `reindex_duration_seconds` (gauge) — 6 new observability counters persisted alongside the existing `flow metrics` JSONL (REQ-22). All names follow the `subject_event_total` / `subject_latency_ms` convention from REQ-8.
- `record_vector_summary(...)` helper in `observability.py` mirroring `record_drift_summary` — emits the 6 counters in one call; defensive clamping on negative inputs.
- `src/flow_engineering/vectors/` package (`__init__.py` + `sqlite_vec_store.py`) exposing `SqliteVecStore` and `vectors_sqlite_path()` for downstream tests.

### Tests
- 572 / 572 tests passing (`uv run pytest -x --tb=short`).
- 24 new BDD scenarios across 5 feature files: `req17_semantic_search.feature` (5), `req18_hybrid_scoring.feature` (5), `req19_embedding_provider.feature` (4), `req20_sqlite_vec_storage.feature` (5), `req21_reindex.feature` (5). Total BDD: 87 scenarios across 17 feature files.
- See `openspec/changes/vector-semantic-search/` for full spec, design, and task breakdown (post-archive).

### Notes
- `vector-semantic-search` shipped via two chained PRs (#1 core HybridBackend + EmbeddingProvider + sqlite-vec storage + observability counters; #2 CLI surface `--semantic` / `--hybrid` / `--alpha` + `flow reindex` subcommand + BDD req21 + release docs).
- ABC bumped v1.0 → v1.1 — third-party `EngramBackend` subclasses import unchanged; new `mem_search_semantic` + `mem_search_hybrid` methods default to `NotImplementedError`.
- The `[vectors]` extra pins `sqlite-vec<0.2` (avoids int8 KNN API churn in 0.2.x); int8 quantization is deferred to v1.1 per spec out-of-scope.
- Gate order in `flow search --semantic` is extra-first, env-second — so users who haven't installed the extra see the install hint, not the env-var hint.
- `flow reindex --dry-run` short-circuits BEFORE creating `vectors.sqlite`, so the on-disk file is never touched in dry-run mode.
- `flow reindex` re-running on a fully-indexed corpus re-uses the audit rows via `INSERT OR REPLACE` with identical vectors (deterministic mock provider in tests; real `SentenceTransformersProvider` in production); no churn, no duplicates.

## [0.3.0] - 2026-06-26

### Added
- `flow drift <change>` subcommand — scans Engram observations for binding drift and reports one of six classes (`still_valid`, `label_drift`, `stale_location`, `stale_id`, `obsolete`, `contradicted`) per REQ-12. Exits `0` (all `still_valid`), `1` (any drift), `2` (`unable_to_verify`) per REQ-11.
- `flow watch --drift` flag — daemon subscribes to `apply-progress` writes and re-runs `scan_change` on `merged` status, emitting a summary line per detected change (REQ-15, REQ-16).
- 8 new `drift_*_total` observability counters (`drift_still_valid_total`, `drift_label_drift_total`, `drift_stale_location_total`, `drift_stale_id_total`, `drift_obsolete_total`, `drift_contradicted_total`, `drift_unable_to_verify_total`, `drift_invoked_total`) persisted alongside the existing `flow metrics` JSONL.

### Closed (W2/W3 carry-forwards)
- **W2** — REQ-8 counter reconciliation: spec counter names now match the 8 implementation counters shipped in v0.2.0.
- **W3** — REQ-3 empty-block BDD: empty `code_refs` blocks are treated as `unbound` and counted via `unbound_observations_total`.

### Tests
- 385 / 385 tests passing (`uv run pytest -x --tb=short`).
- 63 BDD scenarios across 12 feature files (`req1_format`, `req2_parsing`, `req3_engram_io`, `req3_state`, `req4_backfill`, `req4_drift`, `req5_nonbreaking`, `req6_auto_suggest`, `req7_inspect`, `req8_observability`, `req9_drift_detection`, `req15_drift_daemon`).
- See `openspec/changes/archive/2026-06-26-decision-reality-drift/` for full spec, design, and task breakdown (post-archive).

### Notes
- `decision-reality-drift` shipped via two chained PRs (#1 core detector + counters + W2/W3, #2 verification wiring + `flow watch --drift` + REQ-15/REQ-16).
- `sdd-verify` Step 6 gained a sub-step that surfaces `flow drift <change>` findings before declaring green.

## [0.2.0] - 2026-06-25

### Added
- `code_refs` binding block in Engram observations (`<!-- code_refs -->` marker + JSON).
- `src/flow_engineering/binding.py` — extract / parse / format / split round-trip helpers and `CodeRef` dataclass (REQ-1, REQ-2).
- `src/flow_engineering/graphify_query.py` — CLI wrapper for `graphify query` with sha1+mtime cache (24h TTL) and Jaccard fallback (REQ-6 query layer).
- `scripts/backfill_code_refs.py` — append-only migration script with dry-run / apply / idempotency / pre-image JSONL (REQ-4).
- `src/flow_engineering/auto_suggest_code_refs.py` — save-time auto-suggest with threshold filter and confirmation prompt (REQ-6).
- `flow inspect <change>` — CLI command that renders decision ↔ code bindings as a table with freshness column and per-row parse-error isolation (REQ-7).
- `flow metrics` — observability counters persisted as JSONL in `~/.flow-engineering/metrics.json` (REQ-8).
- `EngramClient.save_phase()` auto-appends an `unbound` `code_refs` block when content lacks a marker (REQ-3).
- 6 `SKILL.md` files (sdd-propose / design / tasks / apply / verify / archive) carry the binding-hook prose so future SDD runs resolve `code_refs` automatically.

### Modified
- `src/flow_engineering/engram_io.py` — `save_phase` validation, `auto_suggest_code_refs` wiring, `load_code_refs` accessor (REQ-3, REQ-5, REQ-6).
- `src/flow_engineering/cli.py` — `--with-suggest` / `--no-suggest` flags on save; new `flow inspect` and `flow metrics` subcommands.
- `src/flow_engineering/orchestrator.py` — minor wiring for the save hook.

### Tests
- 302 / 302 tests passing (`uv run pytest`).
- 45 BDD scenarios across 8 feature files (`req1..req8`).
- See `openspec/changes/archive/2026-06-25-decision-code-linking/` for full spec, design, and task breakdown.

### Notes
- `decision-code-linking` shipped via two chained PRs (#1 core binding + backfill, #2 auto-suggest + surface + observability).
- Verify report: PASS WITH WARNINGS, 0 critical. Three documentation-class warnings carried forward (see sdd/decision-code-linking/verify-report for detail).

## [0.1.0] - prior

Initial baseline. See `FLOW.md` and `README.md` for project context.

[0.2.0]: #020--2026-06-25