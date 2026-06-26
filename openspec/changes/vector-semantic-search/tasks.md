# Tasks: vector-semantic-search

**Change:** `vector-semantic-search`
**Builds on:** `proposal.md` (#140) — Approach A additive `HybridBackend`; `design.md` (#141) — D1-D11 resolved; `spec.md` (#142) — 6 REQs (REQ-17..22), 28 BDD scenarios
**Date:** 2026-06-26
**Status:** SPECIFIED + DESIGNED → ready for sdd-apply (batched)
**Strict TDD:** ON (per `decision-reality-drift` precedent; RED → GREEN → REFACTOR cycle per task)

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Total tasks | 17 (PR#1: 10, PR#2: 7) |
| Forecast LOC production (PR#1) | ~280 |
| Forecast LOC production (PR#1 ×6 TDD multiplier) | ~1700 |
| Forecast LOC test (PR#1) | ~1300 |
| Forecast LOC production (PR#2) | ~190 |
| Forecast LOC production (PR#2 ×6 TDD multiplier) | ~1150 |
| Forecast LOC test (PR#2) | ~885 |
| **Grand total LOC (production + test)** | **~2655** |
| BDD feature files | 6 (all NEW) |
| BDD scenarios | 28 |
| New source files | 4 (`embedding_provider.py`, `hybrid_backend.py`, `vectors/__init__.py`, `vectors/sqlite_vec_store.py`) |
| Modified source files | 3 (`engram_io.py`, `cli.py`, `observability.py`) |
| New test files | 8 unit + 1 BDD step glue |
| Chained PRs recommended | Yes |
| Chain strategy | stacked-to-main |
| 400-line budget risk | **High** (PR#1 ~1580 LOC at file-level, but split into 4 apply batches ≤730 LOC each) |
| Delivery strategy | ask-on-risk → resolved to **auto-chain** (per prompt; user pre-approved chained PRs + batched apply) |
| Decision needed before apply | No (auto-chain resolved) |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Forecast rationale

| Signal | Source | Value |
|---|---|---|
| Production LOC | design.md D-file breakdown (sum of `embedding_provider.py` ~90 + `hybrid_backend.py` ~110 + `vectors/sqlite_vec_store.py` ~150 + `engram_io.py` +35 + `cli.py` +110 + `observability.py` +25 + `pyproject.toml` +5) | ~525 (rounded to ~470 in design #141) |
| Realistic ×6 TDD multiplier | Pattern `apply-under-strict-tdd-grows-5-6x-beyond-forecast` from decision-reality-drift apply (Engram #126..133) | ×6 |
| Per-delegation batch ceiling | Pattern `apply-batches-split-into-6-tasks-per-delegation` (Engram #112) — 15-min default runtime | ≤6 tasks OR ≤150 LOC prod per delegation |
| Risk: PR#1 batch D | ~730 LOC across 5 tasks (storage + counters + pyproject + 2 BDD) at ~6 LOC/min = ~2h | **TIMEOUT RISK** — split into D1 (impl) + D2 (BDD) if it hits 15-min ceiling mid-batch |

### Suggested Work Units

| Unit | Goal | Likely PR | Chain base | Notes |
|------|------|-----------|------------|-------|
| 1 | ABC extension + InMemoryBackend defaults + EmbeddingProvider ABC + HybridBackend scaffold + hybrid scoring | PR#1 (parts A-C) | `main` (HEAD `cad89fc`) | Library-only; zero CLI surface; no torch import on default install |
| 2 | sqlite-vec storage + observability counters + pyproject extra + 3 BDD features (req17/18/22) | PR#1 (batch D) | `main` (HEAD after PR#1 batch C lands) | Cohesive infra + BDD; risk of timeout → split into D1/D2 if needed |
| 3 | Real embedding provider + 2 BDD features (req19/20) + CLI surface (`--semantic`, `flow reindex`) + 1 BDD (req21) + release docs | PR#2 (batches E-G) | `main` (HEAD after PR#1 merges) | CLI + reindex + docs close-out |

---

## Out-of-Scope Reminders (do NOT pull into tasks)

These 8 items are explicitly deferred per spec.md — apply must NOT introduce code for them:

- **`auto_suggest_code_refs` rerank with semantic similarity** — REQ-6 seam preserved; v2 follow-up
- **Cross-project federation search** — owned by `cross-project-federation` (#4)
- **Graph-snapshots-aware temporal search** — owned by `graph-snapshots` (#5)
- **Hosted embedding fallback (OpenAI, Cohere)** — local-first v1 only
- **Int8 quantization** — sqlite-vec 0.1.x lacks int8 KNN; v1.1 follow-up
- **Async embed-on-save** — v1 is sync (~50ms CPU per ≤2KB)
- **Daemon-driven drift on vector index changes** — `flow watch` does not subscribe to `vectors.sqlite`
- **Dynamic model hot-swap at runtime** — `flow reindex --model <name>` is the only model-change path

---

## PR#1 task list (10 tasks)

Covers REQ-18 (hybrid scoring), REQ-19 (EmbeddingProvider ABC + lazy import), REQ-20 (sqlite-vec storage), REQ-22 (observability counters). Library-only — no CLI surface until PR#2.

### T1.1 — Add 2 abstract methods to `EngramBackend` ABC (NON-BREAKING defaults)

- **Type:** code
- **TDD phase:** N/A (ABC extension; backward compat covered by T1.2 RED tests)
- **LOC:** ~15 impl + ~10 tests = ~25
- **Files:**
  - `src/flow_engineering/engram_io.py` (modify — add 2 default methods to `EngramBackend`, bump docstring to "ABC v1.1")
- **Dependencies:** none
- **Acceptance criteria:**
  - [ ] `EngramBackend.mem_search_semantic(self, query: str, k: int = 10) -> list[dict]` defined with default body `raise NotImplementedError("mem_search_semantic not implemented for this backend")`
  - [ ] `EngramBackend.mem_search_hybrid(self, query: str, k: int = 10, alpha: float = 0.5) -> list[dict]` defined with same default body
  - [ ] `EngramBackend` class docstring bumped to "ABC v1.1 — added `mem_search_semantic` + `mem_search_hybrid` as default `NotImplementedError` (NON-BREAKING; mirrors `update_observation` precedent at line 86)"
  - [ ] Existing 385 tests still pass (`uv run pytest`)
  - [ ] Third-party subclass fixtures (if any) import unchanged
- **Commit:** `feat(backend): add mem_search_semantic + mem_search_hybrid to EngramBackend ABC (v1.1)`

### T1.2 — Implement default no-op `mem_search_semantic` and `mem_search_hybrid` in `InMemoryBackend`

- **Type:** test + code
- **TDD phase:** RED→GREEN
- **LOC:** ~25 impl + ~50 tests = ~75
- **Files:**
  - `src/flow_engineering/engram_io.py` (modify — override 2 methods in `InMemoryBackend` to raise `VectorSearchDisabled`)
  - `tests/unit/test_engram_io_vectors.py` (NEW — tests for gate error messages)
- **Dependencies:** T1.1
- **Acceptance criteria:**
  - [ ] RED: `test_inmemory_raises_vector_search_disabled_when_extra_missing` and `test_inmemory_raises_vector_search_disabled_when_env_unset` written first; both fail with `AttributeError` or unimplemented
  - [ ] GREEN: `InMemoryBackend.mem_search_semantic` raises `VectorSearchDisabled` with message containing `"pip install flow-engineering[vectors]"` when `sqlite_vec` import is patched to raise `ImportError`
  - [ ] GREEN: `InMemoryBackend.mem_search_semantic` raises `VectorSearchDisabled` with message containing `"FLOW_VECTOR_SEARCH=1"` when env var is unset
  - [ ] `InMemoryBackend.mem_search_hybrid` mirrors the same gate behavior (env check first, then extra check)
  - [ ] `InMemoryBackend.mem_search` (prose FTS5) returns unchanged results when gate is unmet (REQ-17 scenario 5)
  - [ ] No torch import attempted at any point during the gate check (verified via `sys.modules` introspection)
- **Commit:** `feat(backend): VectorSearchDisabled + InMemoryBackend default impls with gate validation`

### T1.3 — Scaffold `embedding_provider.py` with ABC + `MockEmbeddingProvider`

- **Type:** code + test
- **TDD phase:** RED→GREEN
- **LOC:** ~50 impl + ~80 tests = ~130
- **Files:**
  - `src/flow_engineering/embedding_provider.py` (NEW — `EmbeddingProvider` ABC; `MockEmbeddingProvider` deterministic hash-based; `EmbeddingProviderUnavailable` exception; `embed_batch` default)
  - `tests/unit/test_embedding_provider.py` (NEW)
- **Dependencies:** T1.1 (ABC version bump)
- **Acceptance criteria:**
  - [ ] RED: `test_mock_returns_deterministic_384_dim_vectors` fails; `test_no_torch_on_module_import` fails
  - [ ] GREEN: `MockEmbeddingProvider.embed(["hello world"])` returns `np.ndarray` of shape `(1, 384)`, L2 norm in `[0.99, 1.01]`, identical across two calls
  - [ ] GREEN: `MockEmbeddingProvider.embed(["hello world"])` differs from `embed(["goodbye world"])` (hash-based, not all-zeros)
  - [ ] GREEN: `embed([])` returns shape `(0, 384)` (REQ-19 scenario 4)
  - [ ] GREEN: `import flow_engineering.embedding_provider` does NOT add `"torch"` or `"sentence_transformers"` to `sys.modules`
  - [ ] `EmbeddingProviderUnavailable(ImportError)` defined with message `"Install [vectors] extra: pip install flow-engineering[vectors]"`
  - [ ] `EmbeddingProvider.dim = 384` class attribute
  - [ ] `EmbeddingProvider.embed_batch(texts)` default impl iterates `embed()` (no override needed for tests)
- **Commit:** `feat(embedding): EmbeddingProvider ABC + MockEmbeddingProvider with deterministic hash-based vectors`

### T1.4 — Scaffold `hybrid_backend.py` with `HybridBackend` class (composition wrapper)

- **Type:** code + test
- **TDD phase:** RED→GREEN
- **LOC:** ~60 impl + ~100 tests = ~160
- **Files:**
  - `src/flow_engineering/hybrid_backend.py` (NEW — `HybridBackend(EngramBackend)` wrapping inner via `__getattr__`)
  - `tests/unit/test_hybrid_backend.py` (NEW)
- **Dependencies:** T1.1, T1.2, T1.3
- **Acceptance criteria:**
  - [ ] RED: `test_hybrid_backend_forwards_mem_save_to_inner` and `test_hybrid_backend_forwards_mem_search_unchanged` written first; fail
  - [ ] GREEN: `HybridBackend(inner, embeddings=MockEmbeddingProvider(), index=InMemoryVectorIndex())` constructs without error
  - [ ] GREEN: `HybridBackend.mem_save(...)` forwards to `inner.mem_save(...)` and returns the inner obs dict byte-identically
  - [ ] GREEN: `HybridBackend.mem_search(...)` forwards to `inner.mem_search(...)` byte-identically (zero regression on prose path)
  - [ ] GREEN: `HybridBackend.mem_get_observation(id)` forwards to inner (via `__getattr__`)
  - [ ] GREEN: `HybridBackend.iter_observations()` forwards to inner
  - [ ] GREEN: `HybridBackend.mem_search_semantic(...)` raises `VectorSearchDisabled` when extra missing (delegates to gate check, doesn't override yet)
  - [ ] GREEN: `HybridBackend.mem_search_hybrid(...)` raises `VectorSearchDisabled` (same)
  - [ ] Tests cover: `MockEmbeddingProvider` + `InMemoryVectorIndex` (test fixture, separate from production)
- **Commit:** `feat(backend): HybridBackend composition wrapper forwarding all non-search methods to inner`

### T1.5 — Implement hybrid scoring formula (REQ-18): linear combo with normalized BM25

- **Type:** code + test
- **TDD phase:** RED→GREEN
- **LOC:** ~40 impl + ~150 tests = ~190
- **Files:**
  - `src/flow_engineering/hybrid_backend.py` (modify — override `mem_search_hybrid` and `mem_search_semantic`)
  - `tests/unit/test_hybrid_backend.py` (extend — add hybrid scoring tests with worked example)
- **Dependencies:** T1.4
- **Acceptance criteria:**
  - [ ] RED: `test_hybrid_alpha_05_worked_example` fails asserting `obs1 ≈ 0.96`, `obs3 ≈ 0.39`, `obs2 ≈ 0.00` (within ±1e-3)
  - [ ] RED: `test_hybrid_alpha_10_equals_pure_semantic` fails; `test_hybrid_alpha_00_equals_pure_fts` fails; `test_hybrid_alpha_out_of_range_raises` fails
  - [ ] RED: `test_hybrid_empty_query_returns_empty` fails; `test_normalize_bm25_handles_equal_scores` fails
  - [ ] GREEN: `mem_search_hybrid(query, k, alpha=0.5)` returns top-3 order `[obs1, obs3, obs2]` with scores `obs1 ≈ 0.96`, `obs3 ≈ 0.39`, `obs2 ≈ 0.00` (REQ-18 scenario 1; design D7 worked example)
  - [ ] GREEN: `mem_search_hybrid(query, k, alpha=1.0)` returns same ids + same order as `mem_search_semantic(query, k)` (REQ-18 scenario 2)
  - [ ] GREEN: `mem_search_hybrid(query, k, alpha=0.0)` returns same ids + same order as `inner.mem_search(query)` (REQ-18 scenario 3)
  - [ ] GREEN: `alpha=1.5` raises `ValueError` with message containing `"[0.0, 1.0]"` and no embedding work attempted (REQ-18 scenario 4)
  - [ ] GREEN: Empty FTS result set returns `[]` (no `ZeroDivisionError`; `+ε` epsilon applied) — `mem_search_semantic` is NOT called as fallback (REQ-18 scenario 5)
  - [ ] GREEN: `normalize_bm25` unit-tested separately: handles `min == max` (epsilon path), monotonic scaling, value clamping
  - [ ] Counter `vector_search_missing_embedding_total` increments when semantic hits an obs without embedding (D11)
- **Commit:** `feat(backend): hybrid scoring with linear combo formula α·cosine + (1−α)·normalize_bm25(fts)`

### T1.6 — Scaffold `vectors/sqlite_vec_store.py` with `SqliteVecStore` class

- **Type:** code + test
- **TDD phase:** RED→GREEN
- **LOC:** ~80 impl + ~120 tests = ~200
- **Files:**
  - `src/flow_engineering/vectors/__init__.py` (NEW — exports `SqliteVecStore`, `vectors_sqlite_path`)
  - `src/flow_engineering/vectors/sqlite_vec_store.py` (NEW — `add`, `search`, `delete`, `count`; both `observation_embeddings` audit table + `vec_observations` `vec0` virtual)
  - `src/flow_engineering/_paths.py` (modify — add `vectors_sqlite_path()` returning `~/.flow-engineering/vectors.sqlite`)
  - `tests/unit/test_sqlite_vec_store.py` (NEW)
- **Dependencies:** T1.1 (ABC version bump)
- **Acceptance criteria:**
  - [ ] RED: 5 fixtures for REQ-20 scenarios fail (round-trip, delete, count, BLOB size, top-k ordering)
  - [ ] GREEN: `SqliteVecStore(":memory:")` constructs; `add("obs1", unit_vector)` + `search(unit_vector, k=1)` returns `[("obs1", ~0.0)]` (REQ-20 scenario 1)
  - [ ] GREEN: `delete("obs1")` removes from both `vec_observations` AND `observation_embeddings` atomically (REQ-20 scenario 2)
  - [ ] GREEN: `count()` reflects add/delete accurately: 0 → 3 → 2 across the sequence (REQ-20 scenario 3)
  - [ ] GREEN: `observation_embeddings.vector` BLOB byte length is exactly `1536` (= 384 × 4 float32); deserialized numpy round-trips within `1e-6` (REQ-20 scenario 4)
  - [ ] GREEN: `search(q, k=3)` over 10-obs fixture returns 3 tuples ordered by ascending cosine distance, with `obs7` (closest to `q`) at position 0 (REQ-20 scenario 5)
  - [ ] GREEN: Writes wrapped in transaction; partial failure rolls back entire batch
  - [ ] Lazy `import sqlite_vec` inside `__init__`; missing extra raises `ImportError` with install hint
  - [ ] Observation_id type is **TEXT** (per spec #142 D20 schema; consistent with Engram SQLite prose storage)
- **Commit:** `feat(vectors): SqliteVecStore with observation_embeddings + vec_observations (sqlite-vec KNN)`

### T1.7 — Add 6 observability counters for vector operations (REQ-22)

- **Type:** code + test + bdd
- **TDD phase:** RED→GREEN
- **LOC:** ~30 impl + ~80 unit tests + ~80 BDD = ~190
- **Files:**
  - `src/flow_engineering/observability.py` (modify — add 6 counter names; `record_vector_summary` helper mirroring `record_drift_summary`)
  - `tests/unit/test_observability_vectors.py` (NEW)
  - `tests/bdd/req22_vector_observability.feature` (NEW — 4 scenarios)
  - `tests/bdd/test_vector_search_steps.py` (extend — step defs for REQ-22 scenarios)
- **Dependencies:** T1.5 (hybrid scoring emits counters)
- **Acceptance criteria:**
  - [ ] RED: Unit tests for counter increments fail; BDD scenarios fail (file does not exist yet)
  - [ ] GREEN: All 6 counters named per REQ-8 convention (`subject_event_total` / `subject_latency_ms` / `subject_duration_seconds`):
    - `vector_search_invoked_total{trigger=cli|programmatic}` — counter
    - `vector_search_results_returned_total` — counter
    - `vector_search_latency_ms` — histogram (P50/P95/P99 in summary)
    - `vector_index_size_observations` — gauge (sampled at render)
    - `reindex_observations_total` — counter (increments by batch size)
    - `reindex_duration_seconds` — gauge (last run duration)
  - [ ] GREEN: `record_vector_summary(...)` emits exactly one JSONL line per `flow reindex` invocation (mirrors `record_drift_summary` precedent at `observability.py:216`)
  - [ ] GREEN: BDD feature file `req22_vector_observability.feature` contains 4 scenarios (REQ-22 scenarios 1-4); `pytest tests/bdd/req22_vector_observability.feature` passes all 4
  - [ ] GREEN: Counter name catalog documented in `openspec/specs/observability/spec.md` (or referenced from REQ-22 spec) — no silent rename across `decision-code-linking` → `vector-semantic-search` boundary
- **Commit:** `feat(observability): 6 vector_* counters with REQ-8 naming + req22 BDD feature`

### T1.8 — Update `pyproject.toml` with `[vectors]` optional extra

- **Type:** code
- **TDD phase:** N/A (declarative)
- **LOC:** ~10
- **Files:**
  - `pyproject.toml` (modify — add `vectors = ["sqlite-vec>=0.1.0,<0.2", "sentence-transformers>=3.0", "torch>=2.1"]` under `[project.optional-dependencies]`)
- **Dependencies:** none
- **Acceptance criteria:**
  - [ ] `pip install -e .[vectors]` installs `sqlite-vec`, `sentence-transformers`, `torch` (verify on Python 3.13)
  - [ ] `pip install -e .` (default) does NOT install any of the above
  - [ ] `sqlite-vec` pinned to `<0.2` (avoids int8 KNN API churn in 0.2.x)
- **Commit:** `chore(deps): add [vectors] extra with sentence-transformers + sqlite-vec + torch-cpu`

### T1.9 — BDD feature `req17_semantic_search.feature` + step defs

- **Type:** bdd
- **TDD phase:** N/A (BDD = acceptance)
- **LOC:** ~30 feature + ~150 step defs = ~180
- **Files:**
  - `tests/bdd/req17_semantic_search.feature` (NEW — 5 scenarios from REQ-17)
  - `tests/bdd/test_vector_search_steps.py` (extend — step defs for REQ-17)
- **Dependencies:** T1.2 (InMemoryBackend gate), T1.4 (HybridBackend scaffold), T1.7 (counter fixtures)
- **Acceptance criteria:**
  - [ ] Feature file contains 5 scenarios matching spec REQ-17:
    1. Semantic search with both extra and env set returns results
    2. Semantic search without extra raises `VectorSearchDisabled` with install hint
    3. Semantic search without env var (extra present) raises `VectorSearchDisabled` with env hint
    4. CLI `--semantic` flag with extra missing exits non-zero with clear error (will activate fully in PR#2 T2.4; tested at library level here via direct backend call)
    5. `mem_search` (FTS5) still works unchanged when vectors disabled (zero regression)
  - [ ] Step defs use `MockEmbeddingProvider` + `InMemoryVectorIndex` for semantic scenarios; real `InMemoryBackend` for prose regression
  - [ ] `pytest tests/bdd/req17_semantic_search.feature -v` passes all 5 scenarios
- **Commit:** `test(bdd): req17_semantic_search feature with 5 scenarios covering activation gate`

### T1.10 — BDD feature `req18_hybrid_scoring.feature` + step defs

- **Type:** bdd
- **TDD phase:** N/A
- **LOC:** ~30 feature + ~200 step defs = ~230
- **Files:**
  - `tests/bdd/req18_hybrid_scoring.feature` (NEW — 5 scenarios from REQ-18)
  - `tests/bdd/test_vector_search_steps.py` (extend — step defs for REQ-18 with worked example numbers)
- **Dependencies:** T1.5 (hybrid scoring implementation)
- **Acceptance criteria:**
  - [ ] Feature file contains 5 scenarios matching spec REQ-18:
    1. Hybrid with `alpha=0.5` ranks semantic + FTS blended (worked example: `obs1 ≈ 0.96`, `obs3 ≈ 0.39`, `obs2 ≈ 0.00`)
    2. Hybrid with `alpha=1.0` equals pure semantic (sanity)
    3. Hybrid with `alpha=0.0` equals pure FTS (sanity)
    4. `alpha=1.5` raises `ValueError` with `[0.0, 1.0]` in message
    5. Empty query returns `[]` without division-by-zero
  - [ ] Step defs use `MockEmbeddingProvider` to control cosine values (hash-based deterministic); `InMemoryVectorIndex` for KNN
  - [ ] Numeric assertions use `pytest.approx(..., abs=1e-3)` for float tolerance
  - [ ] `pytest tests/bdd/req18_hybrid_scoring.feature -v` passes all 5 scenarios
- **Commit:** `test(bdd): req18_hybrid_scoring feature with 5 scenarios including worked example numbers`

### PR#1 totals (per prompt)

- **Production forecast:** ~280 LOC
- **Test forecast:** ~1300 LOC
- **Realistic production (×6):** ~1700 LOC
- **Total:** ~1580 LOC across 4 batches (A-D), 10 tasks

---

## PR#2 task list (7 tasks)

Covers REQ-17 CLI surface (`flow search --semantic|--hybrid`) and REQ-21 (`flow reindex`). Builds on PR#1's library foundation; assumes `HybridBackend` + `SqliteVecStore` + counters all merged to `main`.

### T2.1 — Implement `SentenceTransformersProvider` (real model, lazy torch import)

- **Type:** code + test
- **TDD phase:** RED→GREEN
- **LOC:** ~40 impl + ~60 tests = ~100
- **Files:**
  - `src/flow_engineering/embedding_provider.py` (extend — add `SentenceTransformersProvider` with function-body torch import)
  - `tests/unit/test_embedding_provider.py` (extend — test lazy import + ImportError path)
- **Dependencies:** T1.3 (ABC), PR#1 merged to `main`
- **Acceptance criteria:**
  - [ ] RED: `test_sentence_transformers_raises_when_torch_missing` fails; `test_sentence_transformers_lazy_import_does_not_load_torch_at_module_level` fails
  - [ ] GREEN: `SentenceTransformersProvider("sentence-transformers/all-MiniLM-L6-v2").dim == 384` and `.model_version == "sentence-transformers/all-MiniLM-L6-v2"`
  - [ ] GREEN: `SentenceTransformersProvider.__init__` raises `EmbeddingProviderUnavailable` with `"pip install flow-engineering[vectors]"` when `torch` is removed from `sys.modules` (REQ-19 scenario 3)
  - [ ] GREEN: First `.embed(...)` call triggers torch + sentence_transformers load (verified via `sys.modules` introspection); subsequent calls reuse cached `self._model`
  - [ ] GREEN: `import flow_engineering.embedding_provider` does NOT trigger torch load (REQ-19 scenario 2)
- **Commit:** `feat(embedding): SentenceTransformersProvider with lazy torch import + EmbeddingProviderUnavailable`

### T2.2 — BDD feature `req19_embedding_provider.feature` + step defs

- **Type:** bdd
- **TDD phase:** N/A
- **LOC:** ~25 feature + ~100 step defs = ~125
- **Files:**
  - `tests/bdd/req19_embedding_provider.feature` (NEW — 4 scenarios from REQ-19)
  - `tests/bdd/test_vector_search_steps.py` (extend)
- **Dependencies:** T2.1
- **Acceptance criteria:**
  - [ ] Feature file contains 4 scenarios matching spec REQ-19:
    1. `MockEmbeddingProvider` returns deterministic 384-dim vectors
    2. `import flow_engineering.embedding_provider` does not trigger torch import
    3. `SentenceTransformersProvider` raises `ImportError` when torch missing
    4. Embedding output shape is `(N, 384)` for N inputs (including empty list → `(0, 384)`)
  - [ ] Step defs use `subprocess` + `sys.modules` introspection to verify import isolation
  - [ ] `pytest tests/bdd/req19_embedding_provider.feature -v` passes all 4 scenarios
- **Commit:** `test(bdd): req19_embedding_provider feature with 4 scenarios`

### T2.3 — BDD feature `req20_sqlite_vec_storage.feature` + step defs

- **Type:** bdd
- **TDD phase:** N/A
- **LOC:** ~30 feature + ~120 step defs = ~150
- **Files:**
  - `tests/bdd/req20_sqlite_vec_storage.feature` (NEW — 5 scenarios from REQ-20)
  - `tests/bdd/test_vector_search_steps.py` (extend)
- **Dependencies:** T1.6 (`SqliteVecStore` impl)
- **Acceptance criteria:**
  - [ ] Feature file contains 5 scenarios matching spec REQ-20:
    1. Add → search round-trip returns added observation as top-1
    2. Delete removes observation from search results
    3. `count()` reflects add/delete accurately
    4. Vector BLOB size matches 384 × 4 = 1536 bytes
    5. Search returns top-k ordered by ascending distance
  - [ ] Step defs use `SqliteVecStore(":memory:")` for fast isolated tests
  - [ ] `pytest tests/bdd/req20_sqlite_vec_storage.feature -v` passes all 5 scenarios
- **Commit:** `test(bdd): req20_sqlite_vec_storage feature with 5 scenarios`

### T2.4 — Add `--semantic` flag to `flow search` CLI (REQ-17 scenarios 3, 4)

- **Type:** code + test
- **TDD phase:** RED→GREEN
- **LOC:** ~30 impl + ~80 tests = ~110
- **Files:**
  - `src/flow_engineering/cli.py` (modify — add `--semantic`, `--hybrid`, `--alpha`, `--k` flags on `flow search <query>`; check `[vectors]` extra independently of env var for `--semantic`)
  - `tests/unit/test_cli_search_semantic.py` (NEW)
- **Dependencies:** T1.7 (counters), PR#1 merged
- **Acceptance criteria:**
  - [ ] RED: `test_cli_search_semantic_missing_extra_exits_nonzero` fails; `test_cli_search_hybrid_with_alpha_param` fails
  - [ ] GREEN: `flow search --semantic "drift detection"` exits non-zero with stderr `pip install flow-engineering[vectors]` when extra missing (REQ-17 scenario 4); NO traceback printed
  - [ ] GREEN: `flow search --semantic "..."` works one-shot when extra present + env unset (REQ-17 gate state row 3)
  - [ ] GREEN: `flow search --hybrid "..." --alpha 0.7 --k 5` works; `alpha` validated `[0.0, 1.0]`
  - [ ] GREEN: Default `flow search "..."` (no flag) remains byte-identical to v0.3.0 (REQ-17 scenario 5 zero regression)
  - [ ] GREEN: `_default_save_backend()` returns `HybridBackend` ONLY when BOTH extra present AND `FLOW_VECTOR_SEARCH=1` (gate state row 4); otherwise returns inner unchanged
  - [ ] Counter `vector_search_invoked_total{trigger=cli}` increments per CLI invocation
- **Commit:** `feat(cli): --semantic / --hybrid / --alpha / --k flags on flow search with gate validation`

### T2.5 — Implement `flow reindex` command (REQ-21)

- **Type:** code + test
- **TDD phase:** RED→GREEN
- **LOC:** ~80 impl + ~150 tests = ~230
- **Files:**
  - `src/flow_engineering/cli.py` (modify — new `flow reindex [--batch-size=100] [--dry-run]` subcommand)
  - `src/flow_engineering/embedding_provider.py` (extend — add `embed_batch` override on `SentenceTransformersProvider` for batched inference)
  - `tests/unit/test_cli_reindex.py` (NEW)
- **Dependencies:** T2.1 (`SentenceTransformersProvider`), T1.6 (`SqliteVecStore`), T1.7 (counters)
- **Acceptance criteria:**
  - [ ] RED: 5 fixtures for REQ-21 scenarios fail (empty corpus, 250 obs progress, idempotent, --dry-run, crash-resume)
  - [ ] GREEN: `flow reindex` on empty corpus exits 0 with stderr `reindex: done — 0 observations indexed` (REQ-21 scenario 1)
  - [ ] GREEN: `flow reindex --batch-size=100` on 250 obs emits 3 progress lines + 1 done line (REQ-21 scenario 2):
    - `reindex: 100/250 (40%) embedded`
    - `reindex: 200/250 (80%) embedded`
    - `reindex: 250/250 (100%) embedded`
    - `reindex: done — 250 observations indexed in T seconds`
  - [ ] GREEN: Second `flow reindex` is idempotent: counter delta = 0; `INSERT OR REPLACE` keyed on `(observation_id, model_version)` (REQ-21 scenario 3)
  - [ ] GREEN: `flow reindex --dry-run` reports count without writing (REQ-21 scenario 4)
  - [ ] GREEN: Crash mid-run — restart completes from last committed batch (REQ-21 scenario 5): transactions commit per batch; no separate checkpoint log
  - [ ] GREEN: Counter `reindex_observations_total` increments by batch size per completed batch; `reindex_duration_seconds` set on completion
  - [ ] GREEN: `SentenceTransformersProvider.embed_batch(texts)` returns `(N, 384)` array via single `model.encode()` call (batched, ~10x faster than per-text)
- **Commit:** `feat(cli): flow reindex subcommand with streaming progress + idempotent INSERT OR REPLACE`

### T2.6 — BDD feature `req21_reindex.feature` + step defs

- **Type:** bdd
- **TDD phase:** N/A
- **LOC:** ~30 feature + ~100 step defs = ~130
- **Files:**
  - `tests/bdd/req21_reindex.feature` (NEW — 5 scenarios from REQ-21)
  - `tests/bdd/test_vector_search_steps.py` (extend)
- **Dependencies:** T2.5
- **Acceptance criteria:**
  - [ ] Feature file contains 5 scenarios matching spec REQ-21:
    1. `flow reindex` on empty corpus completes with 0 indexed
    2. `flow reindex` on 250 observations emits progress lines + done
    3. Second `flow reindex` is idempotent (no-op)
    4. `--dry-run` reports count without writing
    5. Crash mid-run — restart completes from last committed batch
  - [ ] Step defs use `CliRunner` + seeded `InMemoryBackend` + temp `SqliteVecStore`
  - [ ] `pytest tests/bdd/req21_reindex.feature -v` passes all 5 scenarios
- **Commit:** `test(bdd): req21_reindex feature with 5 scenarios`

### T2.7 — CHANGELOG.md v0.4.0 entry + 6 SKILL.md "Vector search hook" prose updates

- **Type:** docs
- **TDD phase:** N/A
- **LOC:** ~15 CHANGELOG + ~25 prose = ~40
- **Files:**
  - `CHANGELOG.md` (modify — new `## [0.4.0] - <date>` section above `[0.3.0]`)
  - `~/.config/opencode/skills/sdd-propose/SKILL.md` (runtime, not repo)
  - `~/.config/opencode/skills/sdd-design/SKILL.md` (runtime)
  - `~/.config/opencode/skills/sdd-tasks/SKILL.md` (runtime)
  - `~/.config/opencode/skills/sdd-apply/SKILL.md` (runtime)
  - `~/.config/opencode/skills/sdd-verify/SKILL.md` (runtime)
  - `~/.config/opencode/skills/sdd-archive/SKILL.md` (runtime)
- **Dependencies:** all PR#2 tasks
- **Acceptance criteria:**
  - [ ] `CHANGELOG.md` v0.4.0 entry lists: `--semantic` / `--hybrid` / `--alpha` / `--k` flags, `flow reindex` subcommand, `HybridBackend` composition, `sqlite-vec` storage, `sentence-transformers` provider, `[vectors]` extra, 6 new `vector_*` counters
  - [ ] 6 SKILL.md prose updates name all 6 REQs (REQ-17..22) and reference `sqlite-vec` + `sentence-transformers` + `[vectors]` extra in their respective "Vector search hook" sections
  - [ ] CHANGELOG entry follows the `[0.3.0]` format (Added / Tests / Notes sections)
- **Commit:** `docs(release): CHANGELOG v0.4.0 entry + 6 SKILL.md vector search hooks`

### PR#2 totals (per prompt)

- **Production forecast:** ~190 LOC
- **Test forecast:** ~885 LOC
- **Realistic production (×6):** ~1150 LOC
- **Total:** ~1075 LOC across 3 batches (E-G), 7 tasks

---

## Apply Batches (≤6 tasks OR ≤150 LOC per delegation)

Per-delegation batch ceiling from Engram #112 pattern (`apply-batches-split-into-6-tasks-per-delegation`). Default delegate runtime is ~15 min; larger batches TIMEOUT.

### PR#1 batches (4 batches)

| Batch | Tasks | LOC (impl + test) | Why |
|-------|-------|-------------------|-----|
| **A** | T1.1 + T1.2 | ~100 | ABC extension + InMemoryBackend default impls — atomic foundation; T1.2 tests backfill T1.1 |
| **B** | T1.3 + T1.4 | ~290 | EmbeddingProvider ABC + HybridBackend scaffold — both depend on T1.1+T1.2 done; cohesive library foundation |
| **C** | T1.5 | ~190 | Hybrid scoring formula — needs T1.4 (HybridBackend scaffold); biggest single task but cohesive |
| **D** | T1.6 + T1.7 + T1.8 + T1.9 + T1.10 | ~730 | Storage + counters + pyproject + 2 BDD features — cohesive "infra + acceptance" closing batch; **TIMEOUT RISK** |

**Batch D risk mitigation:** if delegation hits 15-min ceiling mid-batch, abort and split into:
- **D1** = T1.6 (storage) + T1.8 (pyproject) + T1.7 (counters) — ~400 LOC infra
- **D2** = T1.9 + T1.10 (BDD features) — ~410 LOC acceptance

At ~6 LOC/min (Strict TDD multiplier), batch D = ~2h. If sub-agent reports progress is "8 commits done + storage landed, BDD remaining", abort and launch D2 as continuation.

### PR#2 batches (3 batches)

| Batch | Tasks | LOC (impl + test) | Why |
|-------|-------|-------------------|-----|
| **E** | T2.1 + T2.2 + T2.3 | ~375 | Real embedding provider + 2 BDD features — cohesive "embedding infra + acceptance" |
| **F** | T2.4 + T2.5 | ~340 | CLI surface (semantic flag + reindex) — both touch `cli.py`; cohesion justified |
| **G** | T2.6 + T2.7 | ~170 | Last BDD feature + docs — small close-out |

### Branch targeting (per Engram #114 pattern)

- **stacked-to-main:** PR#1 → merge to `main`; PR#2 branches from updated `main` (post-PR#1 merge).
- **Squash merge** for cohesive multi-commit PRs (preserves linear history, single commit per PR).
- PR#1 batch D may produce multiple sub-commits; squash on merge preserves a clean "feat: vector-semantic-search PR#1" entry.

---

## Open follow-ups for sdd-archive (after PR#2 merges)

| # | Item | Owner |
|---|------|-------|
| 1 | Spec counter catalog in `openspec/specs/observability/spec.md` for the 6 new `vector_*` counters (REQ-22 scenario 4) | sdd-archive |
| 2 | Bump `pyproject.toml` version `0.1.0` → `0.4.0` (matches CHANGELOG entry) | sdd-archive |
| 3 | Verify `MEMORY.md` or AGENTS.md mentions `[vectors]` extra opt-in for future contributors | sdd-archive |
| 4 | Cross-impact: confirm `cross-project-federation` (#4) and `graph-snapshots` (#5) compatibility notes in their respective specs reference vector-semantic-search as a non-conflicting sibling | sdd-archive |

---

## Structured Metadata

- **total_tasks:** 17
- **pr_split:** PR#1 (REQ-18, REQ-19, REQ-20, REQ-22) — library + ABC + storage + counters + BDD req17/18/22; PR#2 (REQ-17 CLI surface, REQ-21) — CLI + reindex + BDD req19/20/21 + docs
- **forecast_loc_production:** ~470 (PR#1 ~280 + PR#2 ~190)
- **forecast_loc_realistic:** ~2850 (×6 TDD multiplier from Engram #126 decision-reality-drift precedent)
- **batches:** 7 (PR#1: A=2, B=2, C=1, D=5; PR#2: E=3, F=2, G=2)
- **batch_d_timeout_risk:** HIGH (~730 LOC; mitigation = split into D1+D2 if it hits 15-min ceiling)
- **review_workload_forecast:**
  - `400_line_budget_risk`: high
  - `chained_prs_recommended`: yes
  - `decision_needed_before_apply`: no (auto-chain resolved; user pre-approved chained PRs + batched apply per prompt)
  - `chain_strategy`: stacked-to-main
- **strict_tdd:** on (RED→GREEN→REFACTOR per task)
- **bdd_feature_files:** 6 NEW
- **bdd_scenarios:** 28
- **out_of_scope_count:** 8 (preserved from spec)
- **next_recommended:** `sdd-apply vector-semantic-search PR#1 batch A` (T1.1 + T1.2, ~100 LOC, ~17 min)