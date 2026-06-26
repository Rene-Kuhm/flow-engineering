# Proposal: vector-semantic-search

## Intent

`flow-engineering`'s `EngramBackend` exposes `mem_search` as a substring/FTS5 prose query, which collapses on bilingual EN/ES notes and on semantic drift ("show me decisions about drift detection" misses if `drift` is not literally present). This change adds **additive** semantic and hybrid retrieval on top of the existing prose contract — never replacing `mem_search` — so users can find observations by meaning, by language, and across phrasing, while every REQ-5 (`code_refs` tokenization) and REQ-9..16 (drift detector id-based lookups) guarantee stays intact.

## Scope

### In Scope
- `HybridBackend(EngramBackend)` composing any inner backend (`InMemoryBackend` first) with an embedding provider and a vector index
- `EmbeddingProvider` ABC + `SentenceTransformerProvider` (default) behind `[vectors]` optional extra
- `VectorIndex` ABC + `SqliteVecIndex` (default) backed by `~/.flow-engineering/vectors.sqlite`
- Three additive methods on `EngramBackend`: `mem_search_semantic(query, k)`, `mem_search_hybrid(query, k, alpha)`, and a `reindex()` utility
- Lazy import strategy so `[vectors]` extra is opt-in; the default install must not pull torch
- Sync embed-on-save semantics for v1 (matches `save_phase` canonical-write precedent from `decision-code-linking`)
- CLI surface: `flow search` with `--semantic` / `--fts` / `--hybrid` flags and a `flow reindex` subcommand
- 5 new observability counters: `vector_search_invoked_total`, `embedding_computed_total`, `hybrid_search_invoked_total`, `vector_index_size`, `reindex_duration_ms`
- `InMemoryBackend.mem_search_semantic` stub returning empty list (ABC conformance, no torch dependency leak)
- Opt-in activation: `FLOW_VECTOR_SEARCH=1` enables `HybridBackend` as default in `_default_save_backend()`; absent flag preserves the inner-only path

### Out of Scope
- Embeddings for cross-project federation (owned by `cross-project-federation`)
- Hosted embedding fallback (OpenAI / Cohere) — possible v1.1 opt-in, NOT v1 default
- Dynamic model hot-swap at runtime — `flow reindex --model <name>` is the only model-change path
- Re-ranking `auto_suggest_code_refs` candidates with embeddings (v2 follow-up; REQ-6 seam is preserved)
- ANN index tuning, sharding, or billion-scale corpora (sqlite-vec ceiling is ~100k; sufficient)
- Snapshot-pinned embeddings (`graph-snapshots` owns this)

## Capabilities

### New Capabilities
- `vector-semantic-search`: embed observations on save, persist vectors in sqlite-vec, expose additive semantic and hybrid retrieval behind opt-in activation without altering the prose `mem_search` contract.

### Modified Capabilities
- None. `decision-code-linking` (REQ-5 prose tokenization), `decision-reality-drift` (REQ-9..16 id-based lookups), and `decision-code-linking` REQ-6 (`auto_suggest_code_refs`) are unchanged in v1. `HybridBackend` composes the inner backend transparently; if `FLOW_VECTOR_SEARCH` is unset, behavior is byte-identical to today.

## Approach — Sketch A, additive `HybridBackend`

`HybridBackend(inner, embeddings, index)` wraps any `EngramBackend` and adds three capabilities without modifying the inner backend or its public surface:

1. **`save_observation(...)`** — write to `inner.save_observation()` first; on success, compute embedding for `prose` (after `binding.split_prose_and_refs` strips the `<!-- code_refs -->` tail) and append to `VectorIndex`. Embedding failures MUST NOT fail the save (`except EmbeddingError → log + observability.increment("embedding_computed_total", {"status": "error"})`).
2. **`mem_search(query, ...)`** — pure delegation to `inner.mem_search`. Zero code change to existing path.
3. **`mem_search_semantic(query, k)`** — embed query, cosine KNN against `VectorIndex`, return list of observation ids ranked by score.
4. **`mem_search_hybrid(query, k, alpha)`** — Reciprocal Rank Fusion of `mem_search` (prose) and `mem_search_semantic` (vectors); `alpha` weights RRF contribution (default 0.5).
5. **`reindex(model=None)`** — walk all observations, recompute embeddings, write back to index. Idempotent; needed on model change or post-fresh-install catch-up.

**Distribution** (`pyproject.toml`):
```toml
[project.optional-dependencies]
vectors = ["sqlite-vec>=0.1.0,<0.2", "sentence-transformers>=3.0", "torch>=2.1"]
```

**Lazy import** in `hybrid_backend.py`:
```python
try:
    from sentence_transformers import SentenceTransformer  # noqa: E402
    _PROVIDER = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
except ImportError:
    raise EmbeddingProviderUnavailable("Install [vectors] extra to use semantic search")
```

**Index file**: `~/.flow-engineering/vectors.sqlite` (matches `metrics.jsonl` precedent from `decision-code-linking`).

**CLI** (`src/flow_engineering/cli.py`):
- `flow search <query>` — current behavior (prose) by default
- `flow search --semantic <query>` — semantic only
- `flow search --hybrid <query>` — RRF blend
- `flow reindex [--model <name>]` — recompute embeddings

**Activation gate**: `_default_save_backend()` returns `HybridBackend(...)` only when `FLOW_VECTOR_SEARCH=1` AND `vector_search` extras importable; otherwise returns `InMemoryBackend` unchanged.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `src/flow_engineering/hybrid_backend.py` | NEW | `HybridBackend` composition + 3 new methods + lazy imports |
| `src/flow_engineering/embedding_provider.py` | NEW | `EmbeddingProvider` ABC + `SentenceTransformerProvider` impl |
| `src/flow_engineering/vector_index.py` | NEW | `VectorIndex` ABC + `SqliteVecIndex` + `InMemoryVectorIndex` (test fixture) |
| `src/flow_engineering/engram_io.py` | MODIFY (minor) | Add 3 abstract method signatures to `EngramBackend`; `InMemoryBackend` stubs return `[]` |
| `src/flow_engineering/cli.py` | MODIFY | `--semantic` / `--hybrid` flags on `flow search`; new `flow reindex` subcommand |
| `src/flow_engineering/observability.py` | MODIFY | 5 new counter helpers |
| `src/flow_engineering/_paths.py` | MODIFY (minor) | Add `vectors_sqlite_path()` returning `~/.flow-engineering/vectors.sqlite` |
| `pyproject.toml` | MODIFY | Add `[vectors]` optional extra |
| `tests/unit/test_hybrid_backend.py` | NEW | Unit tests for save, semantic, hybrid, reindex, failure paths |
| `tests/unit/test_vector_index.py` | NEW | Sqlite-vec round-trip + cosine correctness |
| `tests/unit/test_embedding_provider.py` | NEW | Embedding shape + lazy import behavior |
| `tests/bdd/req17_semantic_search.feature` | NEW | BDD for hybrid ranking, opt-in activation, model migration |
| `tests/bdd/test_vector_search_steps.py` | NEW | pytest-bdd glue |
| `tests/bdd/test_decision_code_linking_p{1,2}_steps.py` | MODIFY (none expected) | REQ-5 stays green; no scenario changes |
| `tests/bdd/req9_drift_detection.feature` | MODIFY (none expected) | Drift uses ids, not embeddings; no scenario changes |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | MODIFY | Extend binding hook with vector-search prose |
| `CHANGELOG.md` | MODIFY | v0.4.0 entry (post-merge) |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| sqlite-vec is pre-v1 (v0.1.x); API may break in 0.2 | **High** | Pin `>=0.1.0,<0.2` in `[vectors]` extra; wrap behind `VectorIndex` ABC so we can swap to LanceDB / numpy without rewriting callers |
| Torch dep pulls ~500MB; cold-start on first `flow search` is multi-second | **High** | Gated behind `[vectors]` extra + lazy import + stderr "loading model…" line; default install never loads torch |
| Bilingual EN/ES quality of `all-MiniLM-L6-v2` is unverified for this repo's prose | **Med** | Allow `FLOW_EMBEDDINGS_MODEL` env override; document `paraphrase-multilingual-MiniLM-L12-v2` as an alternative |
| Sync embed-on-save adds latency to `save_observation` (CPU ~50ms / short prose) | **Med** | Bound the cost — observations are ≤2KB prose; CPU embed is sub-second; flag `[vectors]` users accept this; async embed is a v1.1 follow-up if needed |
| `embedding_reindex` on a large corpus (~5k observations) takes minutes and locks I/O | **Med** | CLI subcommand only (not auto-run); show progress line; allow `--batch-size`; rate-limit at 10 obs/sec to keep CPU cool |
| Hybrid RRF formula choice (Reciprocal Rank Fusion vs linear combo vs cross-encoder) is heuristic | **Med** | RRF is the simplest, well-cited baseline; expose `--alpha` so users can dial; `flow metrics` reports recall uplift vs prose-only |
| Adding 3 new abstract methods to `EngramBackend` could break third-party backend implementations | **Low** | Provide default implementations returning `NotImplementedError`; document in deprecation policy; ABC version bump from "v1" → "v1.1" |
| `code_refs` block stripping via `binding.split_prose_and_refs` could regress | **Low** | Reuse the existing helper from `decision-code-linking` REQ-1/REQ-2; add a regression test asserting embedding text excludes the JSON tail |
| Drift detector (REQ-9..16) accidentally starts reading embeddings | **Low** | Drift uses `CodeRef.id`; explicitly document that vector index is unrelated to drift lookup; add a regression test confirming `flow drift` does not touch `vectors.sqlite` |
| `auto_suggest_code_refs` reranking temptation creeps into PR scope | **Med** | Out of scope per proposal; PR review must reject any embedding-rerank commit; deferred to a named follow-up change |

## Rollback Plan

**PR#1 revert**: revert merge commit. `hybrid_backend.py`, `embedding_provider.py`, `vector_index.py`, new CLI flags, and new counters are all additive. `InMemoryBackend` and existing CLI behavior unchanged when `FLOW_VECTOR_SEARCH` is unset. `vectors.sqlite` file persists harmlessly on disk; users can `rm ~/.flow-engineering/vectors.sqlite` to reclaim ~10MB.

**Activation gate protects blast radius**: without `FLOW_VECTOR_SEARCH=1`, the default backend path is byte-identical to v0.3.0. Rolling back PR#1 plus deleting the env var returns the install to pre-change state.

**PR#2 revert** (CLI + reindex + observability): same pattern — additive CLI subcommand + counter helpers; revert commits individually if needed.

**If sqlite-vec breaks on a platform** (e.g., Windows ARM, Python 3.13): swap `SqliteVecIndex` for `NumpyVectorIndex` (brute-force). No caller changes because everything is behind `VectorIndex` ABC. This is why the ABC exists.

## Dependencies

- `sqlite-vec` (MIT/Apache-2.0, pre-v1) — `[vectors]` extra only
- `sentence-transformers` (Apache-2.0) — `[vectors]` extra only
- `torch` (BSD-3) — `[vectors]` extra only (transitive of sentence-transformers)
- `decision-code-linking` (shipped v0.2.0) — required for `binding.split_prose_and_refs` seam
- `decision-reality-drift` (shipped v0.3.0) — independent; just confirms the seam-by-design observation
- `graphify_query` (existing) — not invoked by v1; cross-cuts only

## Open Questions

**Resolved at propose level** (5 of 9 from explore #139):
1. Storage → sqlite-vec (Sketch A's ABC wraps LanceDB / numpy for escape hatch)
2. Embedding default → sentence-transformers `all-MiniLM-L6-v2`; FastEmbed deferred to v1.1
3. Embed timing → sync on save (Sketch A) — matches `save_phase` precedent
4. Activation gate → opt-in via `FLOW_VECTOR_SEARCH=1`; default install never pulls torch
5. Embedding text scope → prose only, AFTER stripping `<!-- code_refs -->` block via existing `binding.split_prose_and_refs`

**Genuinely open for design phase** (must resolve before `sdd-spec`):

1. **ABC version bump policy** — adding 3 methods to `EngramBackend` breaks any third-party backend that subclasses it directly. Recommend: default implementations returning `NotImplementedError` so old subclasses still import OK, but new methods don't exist on the wire. **Decision needed**: bump ABC to `v1.1` formally, or just document as additive?
2. **Hybrid RRF constant `k`** — Reciprocal Rank Fusion uses `k=60` (Cormack et al. 2009). Should we expose `--rrf-k` or hard-code? Recommend hard-code for v1 (cite the paper); expose in v1.1 if anyone complains.
3. **Hybrid `alpha` semantics** — for RRF, alpha isn't a natural parameter (RRF is rank-based, not score-based). Should `mem_search_hybrid` use RRF (default), or should `--alpha` toggle a linear-combination mode? **Recommend RRF only for v1**; `alpha` parameter reserved for future linear-combo mode.
4. **`mem_search_hybrid` semantic when index is empty** — first install, no embeddings yet. Should it silently fall back to prose-only, or exit 1 with a "run `flow reindex` first" message? Recommend: fall back silently + increment `vector_index_size=0` counter so `flow metrics` surfaces the gap.
5. **Test corpus for embedding determinism** — cosine scores are floats; tests cannot assert exact scores. Recommend: pin small fixtures (10 observations × 384 dims), assert rank order top-3 matches expected for ≥3 query phrasings.
6. **sqlite-vec Python wheel availability** — verified for CPython 3.11/3.12; 3.13 and PyPy untested as of Mar 2026. **Block on**: confirm 3.13 wheel exists before design phase locks in the version pin.

## Success Criteria

- [ ] `HybridBackend` composes `InMemoryBackend` without altering `mem_search` return value on a 100-observation fixture (byte-identical ordering)
- [ ] `mem_search_semantic("drift detection", k=5)` returns ≥1 relevant observation when prose search returns 0 (cross-language, paraphrase, or absent-keyword case)
- [ ] `flow search --semantic` and `flow search --hybrid` exit 0 with valid JSON-or-table output on a 50-observation bilingual fixture
- [ ] `flow reindex` processes 50 observations in ≤30s on a typical laptop with `[vectors]` extra installed
- [ ] All 5 new counters increment on a synthetic run; `flow metrics` shows them
- [ ] With `FLOW_VECTOR_SEARCH` unset, `flow search` behaves byte-identically to v0.3.0 (zero regression)
- [ ] With `[vectors]` extra NOT installed, importing `flow_engineering` does NOT pull torch (verified by `python -c "import flow_engineering; import sys; 'torch' not in sys.modules"`)
- [ ] REQ-5 prose tokenization unchanged (regression test from `decision-code-linking` stays green)
- [ ] REQ-9..16 drift detector unchanged (regression test from `decision-reality-drift` stays green)
- [ ] REQ-6 auto-suggest unchanged in v1 (no rerank commits land in PR#1 or PR#2)
- [ ] Strict TDD evidence: every public method has RED→GREEN→REFACTOR history in commit log
- [ ] Ruff lint clean on changed files

## Cross-Impact

| Queued change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `binding.split_prose_and_refs` is the embed-text seam | Required predecessor; we consume it |
| `decision-reality-drift` (shipped v0.3.0) | Drift uses id lookup; embedding-agnostic | No conflict; document non-interaction |
| `cross-project-federation` (#4) | Vector index is per-project by file path (`~/.flow-engineering/vectors.sqlite`); federation owns cross-project embedding routing | Compatible (boundary respected) |
| `graph-snapshots` (#5) | Embeddings indexed against observation ids, not graph nodes | No conflict |
| `prompt-registry` (#7) | Unrelated layer | No conflict |
| `auto_suggest_code_refs` v2 (unnamed future) | REQ-6 seam is preserved; rerank with semantic similarity is a future change | Complementary, NOT in this PR |

**Unblocks**: meaningful cross-language search; finding observations by meaning not keyword; future `decision-resolve` change that auto-re-suggests stale bindings using semantic similarity.

**Constrains**: any change that touches `EngramBackend` ABC must add to the v1.1 contract (or risk silent `NotImplementedError` failures for third-party backends).

## Estimated Effort

**Forecast (no TDD multiplier yet)**:
- `HybridBackend` + `EmbeddingProvider` + `VectorIndex` + `SqliteVecIndex` + `InMemoryVectorIndex`: ~280 LOC
- ABC additions + `InMemoryBackend` stubs: ~30 LOC
- CLI flags + `flow reindex`: ~60 LOC
- Observability counters: ~25 LOC
- Test fixtures + embedding determinism: ~75 LOC
- **Forecast total: ~470 LOC production code**

**Strict TDD multiplier applied**: ×6 per `pattern/apply-under-strict-tdd-grows-5-6x-beyond-forecast` (established in `decision-code-linking` archive-report #119 S3).
- **Realistic estimate: ~2.8k LOC** (tests included).

**PR breakdown** (recommend 2 chained PRs, both under 400-line review budget):

### PR#1 — Core hybrid backend + embedding pipeline (~280 forecast → ~1.7k real)
- `hybrid_backend.py`, `embedding_provider.py`, `vector_index.py` (incl. `SqliteVecIndex`, `InMemoryVectorIndex`)
- ABC version bump + `InMemoryBackend` stubs
- `flow_engineering/_paths.py` addition
- 5 observability counters
- Unit tests for all three modules + embedding determinism fixtures
- BDD feature `req17_semantic_search.feature` (happy path: semantic ranks correctly when prose misses)
- `pyproject.toml` `[vectors]` extra
- Branch: `feature/vector-semantic-search-pr1` → stacked PR#1

### PR#2 — CLI surface + reindex + observability wiring (~190 forecast → ~1.1k real)
- `flow search --semantic` / `--hybrid` flags
- `flow reindex [--model]` subcommand
- `flow metrics` integration (5 new counters surface in summary)
- BDD scenarios: opt-in activation, reindex after model change, hybrid vs prose-only recall comparison
- 6 SKILL.md prose extensions (binding hook)
- CHANGELOG v0.4.0 entry
- Branch: `feature/vector-semantic-search-pr2` → stacked PR#2

**Wall time estimate** (matches explore #139 + decision-reality-drift precedent):
- ~1.5-2h explore (DONE)
- ~30min propose (this phase)
- ~30min design
- ~30min spec
- ~20min tasks
- ~2h apply across 2 chained PRs (PR#1 ~75min, PR#2 ~45min)
- ~15min verify
- ~10min archive
- **Total ~4.5h end-to-end**

## Next Step

Ready for `sdd-design vector-semantic-search`. The 6 genuinely open questions listed above MUST be resolved in the design phase (especially ABC version bump policy and sqlite-vec 3.13 wheel availability) before `sdd-spec` locks the requirement contract.

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_engrambackend",
      "label": "EngramBackend",
      "file": "src/flow_engineering/engram_io.py",
      "line": 35,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_engram_io_inmemorybackend",
      "label": "InMemoryBackend",
      "file": "src/flow_engineering/engram_io.py",
      "line": 89,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_binding_split_prose_and_refs",
      "label": "binding.split_prose_and_refs",
      "file": "src/flow_engineering/binding.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_increment",
      "label": "observability.increment",
      "file": "src/flow_engineering/observability.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_flow_search",
      "label": "flow search subcommand",
      "file": "src/flow_engineering/cli.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    }
  ]
}