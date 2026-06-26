# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-06-26

### Added
- `flow search --semantic <query>` flag on the existing `flow search` subcommand — explicit semantic search via embeddings (one-shot override; REQ-17).
- `flow search --hybrid --alpha <float> --k <int>` flag pair — hybrid semantic + FTS5 scoring with linear combo `α·cosine + (1−α)·normalize_bm25(fts)` (REQ-18). `α` validated to `[0.0, 1.0]`.
- `flow reindex [--batch-size=100] [--dry-run]` subcommand — sync streaming reindex of the Engram corpus into the sqlite-vec store, idempotent via `INSERT OR REPLACE`, crash-resume via per-batch transactions (REQ-21).
- `HybridBackend` composition wrapper at `src/flow_engineering/hybrid_backend.py` exposing `mem_search_semantic` + `mem_search_hybrid` on top of any `EngramBackend` (NON-BREAKING; ABC v1.1; default `NotImplementedError` preserved).
- `EmbeddingProvider` ABC at `src/flow_engineering/embedding_provider.py` with `MockEmbeddingProvider` (deterministic hash-based 384-dim vectors) and `SentenceTransformersProvider` (real model `sentence-transformers/all-MiniLM-L6-v2`, lazy `torch` import at instance time).
- sqlite-vec storage at `src/flow_engineering/vectors/sqlite_vec_store.py` — `observation_embeddings` audit table (`BLOB(1536)` = 384 × float32) + `vec_observations` `vec0` virtual table for KNN (REQ-20). Persisted at `~/.flow-engineering/vectors.sqlite`.
- `[vectors]` optional extra in `pyproject.toml` (`sqlite-vec>=0.1.0,<0.2`, `sentence-transformers>=3.0`, `torch>=2.1`). Default install pulls ZERO heavy deps; the gate fires only when both the extra AND `FLOW_VECTOR_SEARCH=1` are present.
- `vector_search_invoked_total{trigger=cli|programmatic}`, `vector_search_results_returned_total`, `vector_search_latency_ms` (histogram with P50/P95/P99), `vector_index_size_observations` (gauge), `reindex_observations_total` (counter), `reindex_duration_seconds` (gauge) — 6 new observability counters persisted alongside the existing `flow metrics` JSONL (REQ-22). All names follow the `subject_event_total` / `subject_latency_ms` convention from REQ-8.
- `record_vector_summary(...)` helper in `observability.py` mirroring `record_drift_summary` — emits the 6 counters in one call; defensive clamping on negative inputs.
- `src/flow_engineering/vectors/` package (`__init__.py` + `sqlite_vec_store.py`) exposing `SqliteVecStore` and `vectors_sqlite_path()` for downstream tests.

### Tests
- 572 / 572 tests passing (`uv run pytest -x --tb=short`).
- 28 new BDD scenarios across 5 feature files: `req17_semantic_search.feature` (5), `req18_hybrid_scoring.feature` (5), `req19_embedding_provider.feature` (4), `req20_sqlite_vec_storage.feature` (5), `req21_reindex.feature` (5). Total BDD: 91 scenarios across 17 feature files.
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