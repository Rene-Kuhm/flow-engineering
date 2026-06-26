<!-- Archived 2026-06-26 from sdd/vector-semantic-search/apply-progress-pr2-batch-f (Engram #150) -->

# Apply progress PR#2 batch F — vector-semantic-search

## Goal

SDD apply batch F of vector-semantic-search PR#2: T2.4 (--semantic / --hybrid / --alpha flags on flow search) + T2.5 (flow reindex subcommand with embed_batch).

## Branch / PR State

- Branch: `feature/vector-semantic-search-pr2`
- Baseline (batch E HEAD): `9a27678`
- Final HEAD: `060b6dc`

## Commits

1. `7d07902` test(unit): RED fixtures for flow search --semantic and --hybrid flags (`tests/unit/test_cli_search_semantic.py` +447 NEW, RED confirmed)
2. `2f27c0f` feat(cli): --semantic / --hybrid / --alpha / --k flags on flow search with gate validation (`src/flow_engineering/cli.py` +207/-7, `src/flow_engineering/hybrid_backend.py` +19/-6, `tests/unit/test_cli_search_semantic.py` +3/-1)
3. `20ce798` test(unit): RED fixtures for flow reindex + embed_batch (`tests/unit/test_cli_reindex.py` +347 NEW, `tests/unit/test_embedding_provider_embed_batch.py` +180 NEW, RED confirmed)
4. `a6bd6f1` feat(cli): flow reindex subcommand with streaming progress + --dry-run (`src/flow_engineering/cli.py` +160, `src/flow_engineering/embedding_provider.py` +25/-2)
5. `060b6dc` docs(tasks): mark T2.4 and T2.5 as completed in vector-semantic-search tasks.md (`openspec/changes/vector-semantic-search/tasks.md` +15/-15)

## LOC Delta (cumulative this batch)

- `src/flow_engineering/cli.py`: +367/-7 = +360 net (gate helpers + flow search + flow reindex)
- `src/flow_engineering/hybrid_backend.py`: +19/-6 = +13 net (trigger kwarg for cli observability tag)
- `src/flow_engineering/embedding_provider.py`: +25/-2 = +23 net (embed_batch chunking with batch_size)
- `tests/unit/test_cli_search_semantic.py`: +450 (NEW, 14 tests across 7 classes)
- `tests/unit/test_cli_reindex.py`: +347 (NEW, 8 tests across 6 classes)
- `tests/unit/test_embedding_provider_embed_batch.py`: +180 (NEW, 10 tests across 3 classes)
- `openspec/changes/vector-semantic-search/tasks.md`: +15/-15 (acceptance checkboxes flipped)
- Total: +1403 / -30 = +1373 net

## Test Delta

- Baseline: 535 passing
- Final: **567 passing** (verified via `uv run pytest -x --tb=short` in 3.31s)
- Delta: **+32 tests** (14 T2.4 + 18 T2.5)

## REQ Coverage

- REQ-17 scenarios 3, 4 + REQ-18 CLI dispatch: PASS (unit + integration via CliRunner)
  - Default `flow search "query"` → byte-identical FTS5 (zero regression)
  - `flow search --semantic` with extra missing → exit 2 + install hint (no traceback)
  - `flow search --semantic` with env unset (extra present) → exit 2 + FLOW_VECTOR_SEARCH=1 hint
  - `flow search --semantic` with gates satisfied → calls mem_search_semantic with trigger="cli"
  - `flow search --hybrid --alpha X` → alpha validated [0.0, 1.0], exit 2 if out of range
  - JSON output format with `results` array (observation_id, score, rank, title, topic_key)
  - Counter `vector_search_invoked_total{trigger=cli}` increments per --semantic/--hybrid call
  - --semantic and --hybrid are mutually exclusive
- REQ-21 all 5 scenarios: PASS (unit via CliRunner + InMemoryBackend + tmp SqliteVecStore)
  - Empty corpus: "reindex: done — 0 observations indexed in 0.0s"
  - 250 obs / batch=100: 3 progress lines (40%, 80%, 100%) + done line with elapsed seconds
  - Idempotent: second run reports same corpus size; INSERT OR REPLACE semantics from T1.6
  - --dry-run: count printed to stderr, vectors.sqlite NOT created
  - Crash mid-run: simulate_crash_after param partial-writes first batch; second run completes corpus via INSERT OR REPLACE
  - Counters reindex_observations_total + reindex_duration_seconds fire on every run
  - Subprocess test verifies `import flow_engineering.cli` does not pull torch/sqlite_vec/sentence_transformers

## TDD Evidence

### T2.4

- RED (`7d07902`): `git diff 7d07902^` shows 14 new failing tests. First failure: `Error: No such command 'search'. Did you mean 'archive'?` because `flow search` didn't exist yet.
- GREEN (`2f27c0f`): adds gate helpers, `flow search` subcommand with all 5 flags, and trigger kwarg on HybridBackend. All 14 new tests pass; full suite 549/549.
- REFACTOR: skipped — impl is tight (~360 LOC for new CLI surface + gate helpers). One follow-up note: the `_search_results_to_rows` helper synthesizes rank from position for legacy FTS5 results that lack `rank`; this is documented and consistent.

### T2.5

- RED (`20ce798`): 18 new failing tests. First failure: `AttributeError: module 'flow_engineering.cli' has no attribute '_vectors_sqlite_path'` (test fixture references the helper before it exists).
- GREEN (`a6bd6f1`): adds `_sqlite_vec_available` + `_vectors_sqlite_path` + `_resolve_reindex_provider` + `_perform_reindex_batch` + `flow reindex` subcommand. EmbeddingProvider.embed_batch now chunks with batch_size. All 18 new tests pass; full suite 567/567.
- REFACTOR: skipped — impl is ~160 LOC for the full CLI subcommand + worker; helpers are small and single-purpose. No extraction opportunities.

## Implementation Notes

### flow search (T2.4)

- Gate order: extra check first, then env check, so the install hint wins when both fail (more actionable for users who haven't installed anything yet).
- `trigger="cli"` is passed to HybridBackend.mem_search_* so observability dashboards can separate user-driven calls from programmatic ones (REQ-22 scenario 1 trigger label contract).
- `_search_results_to_rows` normalizes the result shape: legacy `mem_search` returns plain obs dicts (no `score`/`rank`), vector methods return `{observation_id, score, rank, ...}`. Position-based rank + 0.0 score synthesized for legacy path so the table renders uniformly.
- Alpha validation done both at CLI (early exit) and library (HybridBackend raises ValueError). Defense in depth.
- `_default_save_backend()` now lazy-imports SentenceTransformersProvider only when both gates met — preserves the REQ-19 module-import-clean contract.

### flow reindex (T2.5)

- `_resolve_reindex_provider` falls back to MockEmbeddingProvider when torch/sentence_transformers missing — keeps reindex runnable in test environments without the [vectors] extra.
- `_perform_reindex_batch` worker has a `simulate_crash_after` parameter used by the crash-resume test (REQ-21 scenario 5); production callers pass `None`.
- Idempotency: SqliteVecStore.add uses INSERT OR REPLACE on the audit table + UPDATE-then-INSERT on vec0 (T1.6 design); re-running reindex re-embeds with identical vectors (deterministic Mock provider) so no churn.
- Progress lines emitted to stderr per REQ-21 contract; done line also on stderr; `--dry-run` short-circuits before any DB write so vectors.sqlite is never created.
- batch_size validation: `--batch-size 0` or negative exits 2 with clear error before any work.
- EmbeddingProvider.embed_batch now accepts batch_size (default 32) and chunks inputs; SentenceTransformersProvider inherits the default — production can override later for hardware-specific speedups.

### hybrid_backend.py change (T2.4 side-effect)

- `mem_search_semantic(query, k=10, *, trigger="programmatic")` and `mem_search_hybrid(query, k=10, alpha=0.5, *, trigger="programmatic")` add a keyword-only `trigger` parameter.
- The trigger is validated against `observability.VECTOR_TRIGGER_VALUES` before being passed to `record_vector_summary`; invalid values fall back to "programmatic" (mirrors the helper's own fail-open behavior).
- Existing tests pass unchanged because `trigger` is keyword-only with a default.

## Workaround Notes

- PowerShell quoting for the `docs(tasks):` commit worked fine (no parens / backslashes this time).
- The `uv.lock` modification (844 line additions) is pre-existing noise from batch D1's `uv sync` operations; was reverted in batch D2 to keep commits focused. Left in working tree as PR#1 squash-merge housekeeping noise; orchestrator handles cleanup at PR merge time.
- CliRunner's default `mix_stderr=True` makes `result.output` include stderr content; this is why `assert "..." in result.output` works even though progress lines go to stderr.

## Risks / Blockers

None for batch F itself.

Pre-existing mypy strict errors on untyped pytest-bdd step defs (now ~75 errors) — accepted in this project pattern, not introduced by this batch.

For batch G: T2.6 (BDD req21 feature) + T2.7 (CHANGELOG v0.4.0 + 6 SKILL.md vector search hooks); the BDD layer mirrors batch E's pattern (separate `vec_reindex_world` fixture + step text variants).

## Next

- batch G: T2.6 (BDD req21) + T2.7 (CHANGELOG v0.4.0 + 6 SKILL.md vector search hooks)
- Both touch only docs + BDD features (no production code changes), so the batch should fit comfortably under the 15-min ceiling.

**Session**: sdd-vector-semantic-search-explore-2026-06-26
**Topic**: sdd/vector-semantic-search/apply-progress-pr2-batch-f
**Engram**: #150
**Next**: Batch G (BDD req21 + CHANGELOG + SKILL.md hooks, ~170 LOC)
