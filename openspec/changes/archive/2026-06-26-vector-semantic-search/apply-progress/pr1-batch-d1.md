<!-- Archived 2026-06-26 from sdd/vector-semantic-search/apply-progress-pr1-batch-d1 (Engram #147) -->

# Apply progress PR#1 batch D1 — vector-semantic-search

## Goal

SDD apply batch D1 of vector-semantic-search PR#1: T1.6 (SqliteVecStore) + T1.7 (6 vector_* counters) + T1.8 ([vectors] pyproject extra).

## Branch / PR State

- Branch: `feature/vector-semantic-search-pr1`
- Baseline (batch C HEAD): `426e787`
- Final HEAD: `6bce6d9`

## Commits

1. `c7331e6` test(unit): RED fixtures for SqliteVecStore add/search/delete/count (`tests/unit/test_sqlite_vec_store.py` +386)
2. `f791fcf` feat(vectors): SqliteVecStore with observation_embeddings + vec_observations (sqlite-vec KNN) (`src/flow_engineering/vectors/__init__.py` +16, `sqlite_vec_store.py` +235, `test_sqlite_vec_store.py` +2/-2)
3. `9651908` test(unit): RED fixtures for 6 vector_* observability counters + HybridBackend integration (`tests/unit/test_observability_vectors.py` +453)
4. `fae1825` feat(observability): 6 vector_* counters with REQ-8 naming + record_vector_summary wired into HybridBackend (`observability.py` +91, `hybrid_backend.py` +64/-23, `test_observability_vectors.py` +8)
5. `6bce6d9` chore(deps): add [vectors] extra with sqlite-vec + sentence-transformers (opt-in ML stack) (`pyproject.toml` +14)

## LOC Delta (cumulative this batch)

- `src/flow_engineering/vectors/__init__.py`: +16 (NEW)
- `src/flow_engineering/vectors/sqlite_vec_store.py`: +235 (NEW)
- `src/flow_engineering/observability.py`: +91
- `src/flow_engineering/hybrid_backend.py`: +64/-23 (+41 net)
- `pyproject.toml`: +14
- `tests/unit/test_sqlite_vec_store.py`: +386 (NEW)
- `tests/unit/test_observability_vectors.py`: +453 (NEW)
- Total: +1257/-23 = +1234 net
- Compared to forecast ~400 LOC: 308% of forecast (×3 vs T1.6+T1.7+T1.8 estimate; SQLite-vec + HybridBackend integration tests drove the multiplier)

## Test Delta

- Baseline: 461 passing
- Final: **502 passing** (verified via `uv run pytest -x --tb=short` in 2.14s)
- Delta: **+41 tests** (21 sqlite_vec_store + 20 observability_vectors)

## REQ Coverage

- REQ-20 all 5 scenarios: ✅ (TestSqliteVecStoreRoundTrip / TestSqliteVecStoreDelete / TestSqliteVecStoreCount / TestSqliteVecStoreBlobSize / TestSqliteVecStoreTopK)
- REQ-22 all 4 scenarios: ✅ (TestVectorCounterNaming / TestVectorSearchInvokedCounter / TestVectorSearchLatencyCounter / TestReindexCounters)
- T1.7 acceptance (HybridBackend integration): ✅ (TestHybridBackendCounterIntegration — 4 tests verify mem_search_hybrid + mem_search_semantic emit counter batch)

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| T1.6 | `c7331e6` (21 RED failures: ModuleNotFoundError on flow_engineering.vectors) | `f791fcf` (21/21 pass; full suite 482/482) | Lint clean (ruff), mypy strict clean, no refactor needed |
| T1.7 | `9651908` (20 RED failures: AttributeError VECTOR_COUNTER_NAMES) | `fae1825` (20/20 pass; full suite 502/502) | contextlib.suppress for fail-open, top-level imports, fixed I001 |
| T1.8 | N/A (declarative — pyproject.toml extra) | `6bce6d9` (uv sync --check OK; full suite 502/502) | N/A |

## Implementation Notes

- SqliteVecStore: lazy sqlite-vec import (try/except in module body); `_ensure_conn` opens :memory: or file path on first DB touch; `_create_schema` runs CREATE TABLE IF NOT EXISTS for both observation_embeddings (regular) and vec_observations (vec0 virtual)
- vec0 does NOT support INSERT OR REPLACE — used UPDATE-first/INSERT-fallback pattern for upserts
- Lazy conn + schema creation means the constructor never fails on module import; only fails when actually used without the extra
- `encode_vector` is a `@staticmethod` that serializes (384,) float32 to 1536-byte canonical BLOB (same bytes used for both vec0 MATCH query and observation_embeddings audit column)
- `record_vector_summary` emits 4 search counters by default; passes reindex_observations + reindex_duration_seconds kwargs emit the 2 reindex counters; helper is fail-open via contextlib.suppress
- `HybridBackend.mem_search_hybrid` now wraps `_compute_hybrid_results` with a `time.perf_counter` timing + `record_vector_summary` call with `trigger="programmatic"`; the wrapper preserves all T1.5 math exactly (extracted worker keeps the algorithm intact)
- `_safe_index_size` returns 0 when `_index` is not yet wired (it's only set in the future sync-embed-on-save batch), so the gauge is always sampleable

## Test Fixture Pattern (for batch D2 reference)

- `_read_metrics` + `_events_for` helpers parse the JSONL sink into a list, filter by name — reusable across REQ-22 BDD steps
- `metrics_path` fixture points `FLOW_METRICS_PATH` at a tmp file via monkeypatch — same pattern as the existing observability tests

## Risks / Blockers

None for batch D1 itself.

Pre-existing mypy strict error on `record_drift_summary(report: "DriftReport")` at `observability.py:249` — NOT introduced by this batch; documented but not fixed (out of scope for D1).

sqlite-vec 0.1.9 was installed separately via `uv pip install sqlite-vec` to enable GREEN verification of the storage tests; the [vectors] extra itself was NOT installed (no torch / sentence-transformers pulled in).

## Next

- batch D2: T1.9 (BDD req17_semantic_search.feature + step defs) + T1.10 (BDD req18_hybrid_scoring.feature + step defs) — ~410 LOC acceptance
- All T1.6/T1.7 fixtures (SqliteVecStore, InMemoryBackend, MockEmbeddingProvider, HybridBackend, metrics_path) are reusable by the BDD step defs

**Session**: sdd-vector-semantic-search-explore-2026-06-26
**Topic**: sdd/vector-semantic-search/apply-progress-pr1-batch-d1
**Engram**: #147
**Next**: Batch D2 (BDD req17 + req18 features, ~410 LOC)
