# Design: vector-semantic-search

## Technical Approach

`HybridBackend(EngramBackend)` wraps any inner backend (default `InMemoryBackend`) and adds **two** new retrieval methods (`mem_search_semantic`, `mem_search_hybrid`) without altering the prose `mem_search` contract. Composition over inheritance: the inner backend is injected, its `mem_save` / `mem_search` / `mem_get_observation` / `iter_observations` / `update_observation` are forwarded unchanged. Embedding is a **sync write-through** side effect of `save_observation`: `split_prose_and_refs(content)` extracts embedding text (prose only, `code_refs` block stripped), `EmbeddingProvider.embed()` runs in ~50ms on CPU for ≤2KB prose, the vector lands in a `vec0` virtual table inside the same SQLite file as the prose backend. Three new sub-modules: `embedding_provider.py` (ABC + sentence-transformers impl + mock), `vector_index.py` (ABC + SqliteVecIndex + NumpyVectorIndex + InMemoryVectorIndex), `hybrid_backend.py` (composition + ABC conformance). Two chained PRs, both under the 400-line review budget. Activation is opt-in via `FLOW_VECTOR_SEARCH=1` AND `[vectors]` extra installed.

## Architecture Decisions

| # | Decision | Options Considered | Choice | Rationale |
|---|---|---|---|---|
| 1 | ABC evolution | Add abstract methods (BREAKING) vs default methods raising `NotImplementedError` (NON-BREAKING) | **NON-BREAKING default methods** | Mirrors existing `update_observation` precedent at `engram_io.py:86`. Third-party `EngramBackend` subclasses import unchanged; they only break at call-time of the new methods, which is exactly the right surface. ABC version is annotated v1.1 in the class docstring (documentation only, not enforced). |
| 2 | `HybridBackend` shape | Inheritance (subclass `EngramBackend`) vs Composition (wrap any backend) | **Composition** (`__init__(inner: EngramBackend, ...)`) | Inner backend is injectable → trivial to test with `InMemoryBackend`. Forwarding via `__getattr__` keeps surface tiny (~30 LOC). Future swap to a real Engram MCP backend needs zero changes here. |
| 3 | Vector storage layout | Same SQLite as prose / separate `vectors.sqlite` / separate table only | **Same SQLite (when InMemoryBackend is sqlite-backed), otherwise a dedicated `~/.flow-engineering/vectors.sqlite` file** mirroring the `metrics.jsonl` precedent | One file per role is the project's convention (`DEFAULT_GRAPH_JSON`, `metrics.jsonl`). Two tables inside: `observation_embeddings(observation_id INTEGER PRIMARY KEY, model_version TEXT, created_at INTEGER, vector BLOB)` is the audit row; `vec_observations(observation_id INTEGER PRIMARY KEY, vector FLOAT[384])` is the sqlite-vec virtual KNN index. Both share the file. |
| 4 | Embedding provider | Hardcode `sentence-transformers` vs `EmbeddingProvider` ABC | **ABC** with one production impl `SentenceTransformersProvider` and one test impl `MockEmbeddingProvider` | Future swap to FastEmbed / Ollama / OpenAI is one new class. Tests don't touch torch (CI cost savings). The mock provides deterministic vectors for golden tests. |
| 5 | Lazy import strategy | Module-level import vs function-body import vs entry-point gated | **Function-body import inside `SentenceTransformersProvider.embed()`** wrapped in `try/except ImportError → raise EmbeddingProviderUnavailable("pip install flow-engineering[vectors]")` | Default `import flow_engineering` MUST NOT pull torch. Confirmed via test `test_no_torch_on_default_import`. The `__init__.py` of `flow_engineering` stays import-clean; only the `HybridBackend(...)` constructor triggers torch load (one-shot, ~500MB memory cost, ~2s first-call latency on CPU). |
| 6 | Activation gate | `FLOW_VECTOR_SEARCH=1` only / extra installed only / both / CLI flag override | **BOTH env var AND `[vectors]` extra required**; CLI `--semantic` flag is an explicit override that errors clearly if extra is missing | Gate prevents accidental torch import on default installs (the most common state). CLI flag is the documented escape hatch for one-off usage without polluting the env. State machine: `[extra missing]` → `--semantic` → clear error pointing to `pip install flow-engineering[vectors]`. `[extra present, env unset]` → `--semantic` works, prose-only also works (HybridBackend default inactive in `_default_save_backend`). `[extra present, env set]` → HybridBackend is the default backend, all searches go through it. |
| 7 | Hybrid scoring formula | RRF (Cormack k=60) vs linear combo with normalized BM25 vs cross-encoder rerank | **Linear combo**: `score = alpha · semantic_sim + (1 - alpha) · normalize_bm25(fts_score)` where `normalize_bm25(x) = (x − min) / (max − min)` computed over the FTS result set per query. `alpha=0.5` default; `alpha=0.0` = pure FTS, `alpha=1.0` = pure semantic | RRF (proposal's first cut) is rank-based, so alpha loses meaning. Linear combo with min-max normalization lets alpha be a continuous dial with intuitive semantics. Documented worked example: 3 observations, 2 queries — see "Interfaces / Contracts" below. |
| 8 | Reindex command behavior | Sync block / async background / streaming with progress | **Sync streaming with progress** — blocks CLI, prints one stderr line per 100 observations (`rich.progress.Progress` if available, else plain stderr `100/1234 embedded...`) | Background async adds complexity (PID file, signal handling) for marginal benefit at 5k-obs scale. Sync streaming matches the existing `flow backfill` precedent (`decision-code-linking`). Idempotent: `INSERT OR REPLACE` keyed on `(observation_id, model_version)`. Resume: a crash mid-reindex leaves stale embeddings, but the next `flow reindex` replaces them in-place; no separate checkpoint log needed. Rate-limit at 10 obs/sec (sleep 100ms every 10) keeps CPU cool. |
| 9 | Embedding storage size | float32 (1.5KB/obs) vs int8 quantized (384B/obs) | **float32 (sqlite-vec native)** with documented growth estimate | sqlite-vec 0.1.x does NOT support int8; binary quantization is available but its accuracy impact on `all-MiniLM-L6-v2` for bilingual EN/ES is uncharacterized. At expected scale (1k obs ≈ 1.5MB, 5k ≈ 7.5MB, 100k ≈ 150MB) SQLite handles this trivially. **v1.1 will revisit int8** after measuring recall drift on our specific corpus. Document the 100k=150MB number in the design so it doesn't surprise anyone. |
| 10 | Test determinism for semantic search | Assert exact cosine scores vs assert rank order vs property-based | **Assert rank order + top-k membership on a 10-obs × 384-dim pinned fixture**; property test asserts `len(result) > 0` for non-empty corpus | Cosine scores are floats — exact assertions are brittle across numpy versions. Rank order is stable. The `MockEmbeddingProvider` returns `hash(query_text) % 384` mapped to a unit-norm float vector, so the same query always yields the same embedding → reproducible rank ordering. |
| 11 | Backwards compat (pre-existing obs without embeddings) | Error on unembedded obs / silently skip in semantic / FTS-only in hybrid | **FTS-only in hybrid** (score = `normalize_bm25(fts_score)`, semantic contribution = 0); absent from semantic-only results with a `missing_embedding_total` counter increment | Pre-existing observations are part of the corpus users care about; erroring breaks `flow search`. Silent skip in semantic is honest (no vector → no match). `flow reindex` promotes them to full hybrid. The `missing_embedding_total` counter surfaces the gap in `flow metrics` so operators can plan a reindex. |

## Data Flow

### Save-time (sync embed-on-save, both PRs)

```
writer (agent or human)
    │
    │  EngramClient.save_phase(phase, content, ...)
    ▼
HybridBackend.mem_save(title, content, topic_key, type, scope)
    │
    ├─→ inner.mem_save(title, content, topic_key, type, scope)
    │       └─→ returns obs dict with id
    │
    ├─→ try:
    │       prose, _ = split_prose_and_refs(content)
    │       embedding = embeddings.embed(prose)            # ~50ms CPU for ≤2KB
    │       index.upsert(obs_id, embedding, model_version)
    │   except EmbeddingProviderUnavailable:
    │       observability.increment("embedding_skipped_total", reason="provider_missing")
    │   except Exception as exc:
    │       observability.increment("embedding_computed_total", status="error")
    │       # save already succeeded → embedding failure MUST NOT fail save
    │
    └─→ return obs dict
```

### `flow search --semantic` (PR#2)

```
flow search --semantic "<query>" [--k 10] [--alpha 0.5]
    │
    ├─→ backend = _default_save_backend()        # HybridBackend if gate active
    ├─→ if --semantic:
    │       results = backend.mem_search_semantic(query, k)
    │       # list[dict(observation_id, score, rank)]
    ├─→ if --hybrid:
    │       results = backend.mem_search_hybrid(query, k, alpha)
    ├─→ default (no flag):
    │       results = backend.mem_search(query, ...)        # prose path unchanged
    │
    ├─→ render_table(results) | json
    └─→ observability.increment("vector_search_invoked_total", mode=...)
```

### `flow reindex` (PR#2)

```
flow reindex [--model sentence-transformers/all-MiniLM-L6-v2] [--batch 100]
    │
    ├─→ provider = SentenceTransformersProvider(model)
    ├─→ index = SqliteVecIndex(vectors_sqlite_path())
    ├─→ inner = _default_save_backend()
    ├─→ observations = inner.iter_observations()
    ├─→ total = len(observations); started = time.monotonic()
    ├─→ for batch of --batch:
    │     prose_list = [split_prose_and_refs(o.content)[0] for o in batch]
    │     vectors = provider.embed_batch(prose_list)        # batched, faster
    │     for o, v in zip(batch, vectors):
    │         index.upsert(o.id, v, provider.model_version)
    │         observability.increment("embedding_computed_total", status="ok")
    │         if count % 100 == 0: stderr_line(f"{count}/{total} embedded...")
    │
    ├─→ observability.increment("reindex_duration_ms", elapsed_ms=...)
    └─→ return summary line (count, duration, model_version)
```

## File Changes

### New files

| File | LOC | Purpose |
|---|---|---|
| `src/flow_engineering/embedding_provider.py` | ~90 | `EmbeddingProvider` ABC; `SentenceTransformersProvider` impl (lazy torch); `MockEmbeddingProvider` (deterministic hash-based vectors); `EmbeddingProviderUnavailable` exception |
| `src/flow_engineering/vector_index.py` | ~150 | `VectorIndex` ABC (`upsert`, `query`, `delete`, `count`); `SqliteVecIndex` (production, sqlite-vec `vec0` virtual table + `observation_embeddings` audit table); `NumpyVectorIndex` (Windows ARM fallback, brute-force cosine); `InMemoryVectorIndex` (test fixture) |
| `src/flow_engineering/hybrid_backend.py` | ~110 | `HybridBackend(EngramBackend)` composition; forwards 5 inner methods via `__getattr__`; overrides `mem_search_semantic` and `mem_search_hybrid`; sync embed-on-save; reindex utility |
| `tests/unit/test_embedding_provider.py` | ~120 | Mock determinism, lazy import behavior (`assert 'torch' not in sys.modules after import flow_engineering`), batched vs single-call equivalence |
| `tests/unit/test_vector_index.py` | ~180 | SqliteVecIndex round-trip + cosine correctness + concurrency-free KNN order; NumpyVectorIndex correctness; InMemoryVectorIndex fixture sanity |
| `tests/unit/test_hybrid_backend.py` | ~220 | Save forwards + embeds; mem_search delegation byte-identical; semantic ranks correctly on fixture; hybrid linear combo formula; embed failure does NOT fail save; reindex idempotent |
| `tests/unit/test_cli_search_semantic.py` | ~140 | `--semantic`, `--hybrid`, `--alpha`, `--k` flags; clear error when `[vectors]` missing; default flow unchanged |
| `tests/unit/test_cli_reindex.py` | ~100 | Progress output; idempotency; `--model` switch rebuilds; missing graph.json path |
| `tests/unit/test_observability_vectors.py` | ~80 | 5 new counters increment on synthetic run; `flow metrics` surfaces them |
| `tests/bdd/req17_semantic_search.feature` | ~60 | 5 scenarios: opt-in gate, semantic-vs-prose rank difference, hybrid rank, reindex after install, missing-extra error |

### Modified files

| File | LOC delta | Change |
|---|---|---|
| `src/flow_engineering/engram_io.py` | +35 | Add `mem_search_semantic` + `mem_search_hybrid` as default methods on `EngramBackend` (raise `NotImplementedError`); `InMemoryBackend` overrides both returning `[]`. Class docstring bumped to "ABC v1.1". |
| `src/flow_engineering/cli.py` | +110 | New `--semantic` / `--hybrid` flags on a new `flow search <query>` subcommand; new `flow reindex [--model] [--batch]` subcommand; `_default_save_backend()` returns `HybridBackend` when gate active |
| `src/flow_engineering/observability.py` | +25 | 5 new counters: `vector_search_invoked_total`, `embedding_computed_total`, `hybrid_search_invoked_total`, `vector_index_size`, `reindex_duration_ms`; `record_vector_summary(...)` helper mirroring `record_drift_summary` |
| `pyproject.toml` | +5 | Add `[vectors]` extra: `sqlite-vec>=0.1.0,<0.2`, `sentence-transformers>=3.0`, `torch>=2.1` (transitive) |

**Production total**: ~470 LOC across 6 new + 3 modified. **Test total**: ~900 LOC across 6 new unit + 1 new BDD (conservative ×2 TDD multiplier for vectors vs ×6 for CLI/BDD from the precedent).

## Interfaces / Contracts

```python
# embedding_provider.py
class EmbeddingProvider(ABC):
    model_version: str
    dim: int
    @abstractmethod
    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

class SentenceTransformersProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_version = model_name
        self.dim = 384
        self._model = None  # lazy
    def embed(self, text: str) -> list[float]:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # noqa
                self._model = SentenceTransformer(self.model_version)
            except ImportError as exc:
                raise EmbeddingProviderUnavailable(
                    "Install [vectors] extra: pip install flow-engineering[vectors]"
                ) from exc
        v = self._model.encode(text, normalize_embeddings=True)
        return v.tolist()

class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic hash-based vectors for tests."""
    def __init__(self) -> None:
        self.model_version = "mock-v1"; self.dim = 384
    def embed(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        v = [rng.gauss(0, 1) for _ in range(self.dim)]
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

# vector_index.py
class VectorIndex(ABC):
    @abstractmethod
    def upsert(self, obs_id: int, vector: list[float], model_version: str) -> None: ...
    @abstractmethod
    def query(self, vector: list[float], k: int) -> list[tuple[int, float]]: ...  # (obs_id, cosine)
    @abstractmethod
    def delete(self, obs_id: int) -> None: ...
    @abstractmethod
    def count(self) -> int: ...

class SqliteVecIndex(VectorIndex):
    """Uses vec0 virtual table for KNN + observation_embeddings table for audit."""
    def __init__(self, db_path: Path) -> None:
        import sqlite_vec                              # lazy
        self._conn = sqlite3.connect(db_path)
        self._conn.enable_load_extension(True)
        self._conn.load_extension(sqlite_vec.loadable_path())
        self._conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vec_observations USING vec0(observation_id INTEGER PRIMARY KEY, vector FLOAT[384])")
        self._conn.execute("CREATE TABLE IF NOT EXISTS observation_embeddings(observation_id INTEGER PRIMARY KEY, model_version TEXT, created_at INTEGER, vector BLOB)")
        # ... (full impl in vector_index.py)

# hybrid_backend.py
class HybridBackend(EngramBackend):
    def __init__(self, inner: EngramBackend, *, embeddings: EmbeddingProvider,
                 index: VectorIndex, model_version: str | None = None) -> None:
        self._inner = inner
        self._embeddings = embeddings
        self._index = index
        self._model_version = model_version or embeddings.model_version

    def mem_save(self, title, content, topic_key, type="manual", scope="project"):
        obs = self._inner.mem_save(title, content, topic_key, type, scope)
        try:
            prose, _ = split_prose_and_refs(content)
            vec = self._embeddings.embed(prose)
            self._index.upsert(obs["id"], vec, self._model_version)
            observability.increment("embedding_computed_total", status="ok")
        except Exception as exc:
            observability.increment("embedding_computed_total", status="error",
                                    error=type(exc).__name__)
        return obs

    def mem_search_semantic(self, query: str, k: int = 10) -> list[dict]:
        vec = self._embeddings.embed(query)
        hits = self._index.query(vec, k=k)
        rows = [{"observation_id": oid, "score": float(sim), "rank": i}
                for i, (oid, sim) in enumerate(hits)]
        observability.increment("vector_search_invoked_total", mode="semantic",
                                k=k, results=len(rows))
        return rows

    def mem_search_hybrid(self, query: str, k: int = 10, alpha: float = 0.5) -> list[dict]:
        # D7: linear combo with min-max normalized BM25 from inner.mem_search.
        prose_hits = self._inner.mem_search(query, topic_key=None, limit=10_000, scope="project")
        if not prose_hits:
            return self.mem_search_semantic(query, k)
        scores = [self._bm25_like_score(query, h) for h in prose_hits]
        smin, smax = min(scores), max(scores)
        span = (smax - smin) or 1.0
        fts_norm = {id(h): (s - smin) / span for h, s in zip(prose_hits, scores)}
        sem_hits = {h["observation_id"]: h for h in self.mem_search_semantic(query, k=k)}
        # union of ids
        all_ids = {id(h) for h in prose_hits} | set(sem_hits.keys())
        scored = []
        for h in prose_hits:
            sem_score = sem_hits.get(h["id"], {}).get("score", 0.0)
            scored.append({
                "observation_id": h["id"],
                "score": alpha * float(sem_score) + (1 - alpha) * fts_norm[id(h)],
                "title": h.get("title", ""),
            })
        # add semantic-only ids (not in prose_hits)
        for oid, hit in sem_hits.items():
            if not any(r["observation_id"] == oid for r in scored):
                scored.append({"observation_id": oid, "score": alpha * float(hit["score"]),
                               "title": ""})
        scored.sort(key=lambda r: r["score"], reverse=True)
        for i, r in enumerate(scored[:k]):
            r["rank"] = i
        observability.increment("hybrid_search_invoked_total", alpha=alpha, k=k,
                                results=len(scored))
        return scored[:k]

    # forward all other methods
    def __getattr__(self, name):
        return getattr(self._inner, name)
```

### Worked example for D7 (hybrid scoring)

Corpus: 3 observations `[obs1, obs2, obs3]` with prose `"drift detection strategy"` / `"drift alarm"` / `"logging best practices"`. Query: `"how do we detect drift"` (`alpha=0.5`).

- Prose search returns `[obs1, obs2]` (token overlap on `drift`). Inner score (toy BM25-like): `obs1=0.85`, `obs2=0.40`. `min=0.40`, `max=0.85`, `span=0.45`.
- `normalize_bm25(obs1) = (0.85 − 0.40) / 0.45 = 1.00`. `normalize_bm25(obs2) = 0.00`.
- `mem_search_semantic` returns `[obs1, obs3]` with cosine scores `obs1=0.92`, `obs3=0.78` (model learned drift and alarm are related).
- Hybrid union: `obs1` (sem=0.92, fts_norm=1.00) → `score = 0.5·0.92 + 0.5·1.00 = 0.96`. `obs2` (sem=0, fts_norm=0.00) → `score = 0.00`. `obs3` (sem=0.78, fts_norm=0) → `score = 0.5·0.78 + 0.5·0 = 0.39`.
- Final order: `obs1 (0.96) > obs3 (0.39) > obs2 (0.00)`. Semantic pulled `obs3` above `obs2` despite zero FTS overlap. Demo of why alpha>0 helps.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `MockEmbeddingProvider` determinism | Hash-based vectors: same input → same vector; unit-norm asserted |
| Unit | `SqliteVecIndex` round-trip | 10-obs fixture, upsert + query, assert top-1 hit matches expected id |
| Unit | `NumpyVectorIndex` parity | Same 10-obs fixture, assert top-3 order matches `SqliteVecIndex` |
| Unit | `HybridBackend.mem_search` unchanged | Byte-identical to inner backend on 100-obs fixture (prose path zero regression) |
| Unit | `HybridBackend.mem_search_semantic` | 10-obs × 384-dim pinned fixture; rank-order assertions |
| Unit | `HybridBackend.mem_search_hybrid` (D7) | 3-obs corpus; assert worked-example numbers exactly |
| Unit | Embed failure does NOT fail save | Mock provider raises; save still succeeds; counter increments |
| Unit | `flow search --semantic` / `--hybrid` / `--alpha` / `--k` | CliRunner; seeded HybridBackend; assert exit 0 + table output |
| Unit | `flow reindex` idempotent | Run twice on same corpus; assert second run no-op (counter delta = 0); `--model` triggers full rebuild |
| Unit | Activation gate | `FLOW_VECTOR_SEARCH=0` → CLI uses InMemoryBackend only; `=1` + extra installed → HybridBackend; `=1` + extra missing → `--semantic` exits with clear error |
| Unit | No torch leak | `import flow_engineering; assert 'torch' not in sys.modules` |
| BDD | `req17_semantic_search.feature` | 5 scenarios: opt-in gate, semantic-vs-prose, hybrid blend, reindex after install, missing-extra error |
| Integration (manual) | Real model on 50-obs bilingual fixture | Eyeball top-5 relevance; verify `--alpha` dial shifts rank |

**Strict TDD order** per the project's RED → GREEN → REFACTOR precedent:

1. `embedding_provider.py` — RED: `MockEmbeddingProvider.embed` returns deterministic vectors → GREEN: pass → REFACTOR: add batch + dim
2. `vector_index.py` — RED: `InMemoryVectorIndex.upsert/query` round-trip → GREEN: pass → REFACTOR: add SqliteVecIndex + NumpyVectorIndex
3. `hybrid_backend.py` — RED: composition forwards unchanged; save-then-embed; semantic rank; hybrid formula; failure isolation → GREEN → REFACTOR
4. `engram_io.py` — RED: `EngramBackend.mem_search_semantic` default raises; `InMemoryBackend` override returns `[]` → GREEN → REFACTOR docstring to v1.1
5. `cli.py` — RED: CliRunner with seeded HybridBackend; flags wire; clear error path → GREEN → REFACTOR
6. BDD scenarios bind unit tests; counters wired last
7. SKILL.md binding hook prose last

## Migration / Rollout

**No data migration.** Pre-existing observations live in the inner backend unchanged. Their first semantic query contributes FTS-only score (sem=0). After `flow reindex`, they join the vector index and full hybrid scoring kicks in. Rollout:

1. PR#1 merged → `HybridBackend` available via direct constructor; no CLI yet; counters record but no operator surface
2. Operator installs `[vectors]` extra, sets `FLOW_VECTOR_SEARCH=1`, runs `flow reindex` → warm corpus
3. PR#2 merged → `flow search --semantic|--hybrid` available; `flow reindex` CLI surface; `flow metrics` includes 5 new counters

**Rollback per-PR** (revert merge; all additive). With `FLOW_VECTOR_SEARCH` unset, the default backend path is byte-identical to v0.3.0. `vectors.sqlite` persists harmlessly on disk; users can `rm ~/.flow-engineering/vectors.sqlite` to reclaim space.

**Windows ARM fallback**: when sqlite-vec fails to load (`sqlite3.OperationalError: not authorized` or missing wheel), `HybridBackend.__init__` falls back to `NumpyVectorIndex` and emits a one-time stderr warning. ABC swap is invisible to callers.

## Open Questions (resolved)

| # | Question (from propose #140) | Resolution | Justification |
|---|---|---|---|
| 1 | ABC version bump policy | **NON-BREAKING** default methods raising `NotImplementedError` | Mirrors `update_observation` precedent (`engram_io.py:86`); old subclasses import unchanged; ABC annotated v1.1 in docstring only |
| 2 | sqlite-vec 3.13 wheel availability | **VERIFIED for PyPI 0.1.9** — `py3-none-any` wheel, no `requires_python` constraint, installs on Python 3.13 via `sqlite3 >= 3.41` stdlib (Python 3.13 ships 3.46+). Windows ARM NOT shipped (only `win_amd64.whl`); escape hatch via `NumpyVectorIndex` ABC swap documented above | Direct PyPI verification: 5 wheels (`macosx_10_6_x86_64`, `macosx_11_0_arm64`, `manylinux_2_17_x86_64`, `manylinux_2_17_aarch64`, `win_amd64`); no `cp313` / `cp312` ABI lock |
| 3 | Activation gate semantics | **BOTH env var AND extra required**; CLI `--semantic` flag is an explicit override that errors clearly when extra missing | State machine table at Decision #6 above |
| 4 | Hybrid scoring formula | **LINEAR COMBO `score = α · sim + (1-α) · normalize_bm25(fts)`** (overrides the propose-phase RRF recommendation) | RRF is rank-based — `alpha` loses meaning. Linear combo gives `alpha` intuitive semantics (0=pure FTS, 1=pure semantic). Documented worked example above |
| 5 | Reindex command behavior | **SYNC STREAMING** with progress line per 100 obs; idempotent via `INSERT OR REPLACE`; no separate checkpoint log needed | Matches `flow backfill` precedent (`decision-code-linking`); background async adds PID/signal complexity for marginal benefit at 5k scale; crash-resume is "re-run replaces stale rows" |
| 6 | Embedding storage size | **float32** (1.5KB/obs); growth estimates: 1k=1.5MB, 5k=7.5MB, 100k=150MB. **Defer int8 to v1.1** pending accuracy characterization | sqlite-vec 0.1.x has no int8 KNN; binary quantization's accuracy hit on `all-MiniLM-L6-v2` is uncharacterized for bilingual EN/ES; expected scale makes storage negligible |

## Unblocks / Constraints

**Unblocks**: meaningful cross-language search; finding observations by meaning not keyword; future `decision-resolve` change that auto-re-suggests stale bindings using semantic similarity.

**Constrains**: any future change that touches `EngramBackend` ABC must respect the v1.1 contract — new methods added without default `NotImplementedError` will silently break third-party subclasses at import time.

## Cross-Impact

| Queued change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `binding.split_prose_and_refs` is the embed-text seam | Required predecessor; we consume it (no change) |
| `decision-reality-drift` (shipped v0.3.0) | Drift uses id lookup; embedding-agnostic | No conflict; document non-interaction in this design |
| `cross-project-federation` (#4) | Per-project `vectors.sqlite`; federation owns cross-project embedding routing | Compatible (boundary respected) |
| `graph-snapshots` (#5) | Embeddings keyed by `observation_id`, not graph nodes | No conflict |
| `auto_suggest_code_refs` v2 (unnamed future) | REQ-6 seam preserved; rerank with semantic similarity is a future change | Complementary, NOT in this PR |

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_engrambackend",
      "label": "EngramBackend ABC v1.1",
      "file": "src/flow_engineering/engram_io.py",
      "line": 35,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_update_observation_default",
      "label": "update_observation default (NotImplementedError precedent)",
      "file": "src/flow_engineering/engram_io.py",
      "line": 86,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_binding_split_prose_and_refs",
      "label": "binding.split_prose_and_refs (embed-text seam)",
      "file": "src/flow_engineering/binding.py",
      "line": 83,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_increment",
      "label": "observability.increment (counter sink)",
      "file": "src/flow_engineering/observability.py",
      "line": 71,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_drift_summary",
      "label": "observability.record_drift_summary (counter-batch helper precedent)",
      "file": "src/flow_engineering/observability.py",
      "line": 216,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_default_save_backend",
      "label": "_default_save_backend (gate anchor)",
      "file": "src/flow_engineering/cli.py",
      "line": 272,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_scan_change",
      "label": "decision_drift.scan_change (id-based, embedding-agnostic)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 188,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "pyproject_toml_optional_dependencies",
      "label": "pyproject.toml [vectors] extra (NEW)",
      "file": "pyproject.toml",
      "line": 20,
      "confidence": 0.9,
      "source": "manual"
    }
  ]
}