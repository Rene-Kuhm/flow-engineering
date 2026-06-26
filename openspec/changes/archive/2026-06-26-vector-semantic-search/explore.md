<!-- Archived 2026-06-26 from sdd/vector-semantic-search/explore (Engram #139) -->

# Explore Report — vector-semantic-search

## Problem (sharp)

`flow-engineering`'s `EngramClient` searches observations through an `EngramBackend` ABC. The default backend is `InMemoryBackend` (plain substring match). Real users hit the EXTERNAL Engram MCP server, which uses SQLite FTS5 for retrieval. FTS5 is token-based: "show me decisions about drift detection" fails unless the literal token `drift` is in the prose; cross-language queries (Spanish notes, English code) collapse entirely. We need vector semantic search alongside FTS5 so users can find observations by meaning, not just keyword overlap, and so hybrid ranking outperforms either alone. Hard non-breaking constraint: existing `mem_search` semantics — including the FTS5 prose contract preserved by decision-code-linking REQ-5 — MUST stay intact.

## Codebase Findings

### FTS5 current usage

- **Where in this repo**: NO direct FTS5 / sqlite / virtual table code. FTS5 lives in the external Engram MCP binary (out-of-tree). This repo exposes only the `EngramBackend` ABC at `src/flow_engineering/engram_io.py:35`.
- **Queries supported (via ABC)**: `mem_save`, `mem_search(query, topic_key, limit, scope)`, `mem_get_observation(id)`, `iter_observations(project)`, `update_observation(id, content, type)`.
- **Default backend**: `InMemoryBackend` at `engram_io.py:89`. Substring match on `content` + `title`, sorted by id desc. No scoring, no ranking, no FTS5.
- **Storage**: in-memory `dict[int, dict]` keyed by autoincrement id. Schema fields: `id, title, content, topic_key, type, scope, project, created_at, updated_at`.
- **FTS5-prose contract (REQ-5 from decision-code-linking)**: `tests/bdd/req5_nonbreaking.feature:21` — "FTS5-style prose query still matches observations with new block". The trailing `<!-- code_refs -->` block must NOT break FTS5 tokenization downstream.

### Observation characteristics

- **Typical size**: ~500-2000 bytes prose (one explore/proposal/spec artifact) + ~50-200 bytes `<!-- code_refs -->` JSON tail. Embedding-friendly text after stripping the code_refs block via `binding.split_prose_and_refs`.
- **Count expected**: hundreds per active change, low thousands across the whole `flow-engineering` install. `observability.backfill_coverage` tests cite 46/103 as a representative corpus. Not millions. SQLite handles this trivially.
- **Language mix**: bilingual EN/ES in this repo's SKILL/AGENTS prose; user notes are mixed. `all-MiniLM-L6-v2` is English-trained; multilingual model would be safer.

### Existing embedding code

- **None.** Confirmed by `grep -ri 'embed|sqlite-vec|chroma|qdrant|faiss' src/` — zero matches. No `numpy` import anywhere in `src/`. The dependency footprint in `pyproject.toml:9-15` is intentionally tiny (click, jinja2, watchdog, pydantic, pyyaml).
- Closest precedent: `auto_suggest_code_refs` (REQ-6) integrates with external `graphify` CLI via subprocess + Jaccard similarity. New vector layer should follow the same "lazy optional dep + CLI surface" pattern.

### Existing cross-impact hooks

- `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md:340` — "vector-semantic-search | Auto-suggester is swappable behind same interface | Complementary".
- `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md:327-328` — owned by this change: linking via `memory_relations` table (v2) + re-ranking suggestions with embeddings.
- `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md:360` — "Drift uses id lookup, not similarity. Embedding-agnostic. No conflict."

## Option Matrix — Vector Storage

| Option | Setup | Runtime | Python | TDD | Maintenance | Scale | Local-first | License | Verdict |
|--------|-------|---------|--------|-----|-------------|-------|-------------|---------|---------|
| **A. sqlite-vec** | `pip install sqlite-vec` + `.load vec0` | <1ms KNN on 10k vectors @ 384d (per their benchmarks) | `pip` wheel + sqlite3 stdlib | Excellent (pure Python test seam; pin known embeddings) | Pre-v1 (v0.1.9 Mar 2026) — expect breaking changes; small surface area to absorb | ~100k vectors comfortably | Yes (in-process SQLite file) | MIT or Apache-2.0 | **recommended** |
| **B. Qdrant** | Docker sidecar + client lib | Sub-ms but with network hop | `qdrant-client` SDK | Harder (needs running server in tests) | Heavy: server lifecycle, persistence, backups | Scales to billions | Partial (needs Docker) | Apache-2.0 | **avoid** |
| **C. ChromaDB** | `pip install chromadb` (pulls pydantic, rust core) | <10ms small corpus | High-level API (collections) | Medium (mock collection for tests) | Active project but fat dep tree | Hundreds of thousands | Yes (embedded mode) | Apache-2.0 | **viable** |
| **D. LanceDB** | `pip install lancedb` (arrow + rust) | <5ms | Pythonic DataFrame API | Medium | Lance format evolving; medium maturity | Millions+ | Yes | Apache-2.0 | **viable** |
| **E. pgvector** | Postgres required | Tied to PG ops | `psycopg` style | Project is SQLite-only by policy — N/A | High (DB migration) | Massive | No | PostgreSQL License | **rejected** |
| **F. Faiss** | `pip install faiss-cpu` | Sub-ms at scale | Low-level (manual index mgmt) | Medium (need fixture indexes) | CPU/GPU split, API churn | Millions | Yes (in-process) | MIT | **avoid** (overkill at our scale, low-level API) |
| **G. Pure numpy + sklearn** | `pip install numpy` (~30MB) + optional sklearn | Brute-force: O(N) per query (~50ms at 5k × 384d) | DIY | Excellent (deterministic) | We'd own the index format forever | ~10k vectors ceiling | Yes | BSD/MIT | **rejected** for v1 (reinvents sqlite-vec badly; keep as fallback if sqlite-vec breaks on Windows) |

**Justifications**:

- **sqlite-vec (A) recommended**: it's the only option that (1) keeps storage in a single SQLite file we already know how to ship, (2) needs zero new processes, (3) is local-first by construction, (4) has a tiny Python API surface we can fully abstract behind a `VectorIndex` ABC. The "pre-v1, expect breaking changes" warning is real but mitigated by wrapping behind an interface.
- **Qdrant (B) avoid**: a CLI tool that depends on a Docker sidecar breaks the local-first / single-binary install promise that flow-engineering already makes.
- **ChromaDB / LanceDB (C/D) viable**: both are technically fine but add heavier deps than sqlite-vec with no benefit at our scale. Reserve as future "scale up" escape hatch.
- **pgvector (E) rejected**: violates SQLite-only policy and the explore goal of "alongside FTS5".
- **Faiss (F) avoid**: too low-level for ~1k-vector corpora; the manual index-management code we'd write replicates sqlite-vec's job.
- **Pure numpy (G) rejected**: we'd own index persistence, ANN algorithms, and shard logic forever. Only fall back if sqlite-vec fails on Windows ARM or Python 3.13.

## Option Matrix — Embedding Model

| Option | Cost | Quality (MTEB) | Local-first | Bundle | License | Verdict |
|--------|------|----------------|-------------|--------|---------|---------|
| **A. sentence-transformers / `all-MiniLM-L6-v2`** | Free | ~58 avg, English-only | Yes | torch + transformers ~500MB | Apache-2.0 | **recommended** |
| **B. OpenAI `text-embedding-3-small`** | $0.02/1M tokens | ~62 avg, multilingual | No (cloud) | None | OpenAI ToS | **avoid as default**, viable as opt-in |
| **C. Anthropic embeddings** | N/A | N/A | N/A | N/A | N/A | **rejected** (not released) |
| **D. Ollama `nomic-embed-text`** | Free | ~62 avg, multilingual | Yes | Requires Ollama daemon + model pull (~274MB) | Apache-2.0 (nomic) | **viable as opt-in alternative** |
| **E. Cohere embed-v3** | Paid | Excellent multilingual | No | None | Cohere ToS | **avoid** |
| **F. FastEmbed / BGE-small** | Free | ~60 avg, multilingual | Yes | ONNX runtime ~50MB (no torch) | Apache-2.0 | **recommended alternative** (lighter dep than A) |

**Justifications**:

- **sentence-transformers all-MiniLM-L6-v2 (A) recommended**: simplest install (`pip install sentence-transformers`), well-known quality, MIT-compatible license. The torch dep is the main cost — mitigated by gating it behind an optional `[vectors]` extra and lazy-importing inside the embedding provider.
- **OpenAI (B) avoid as default**: breaks local-first. Keep as opt-in `--remote-embeddings openai` escape hatch if user provides `OPENAI_API_KEY`.
- **Anthropic (C) rejected**: no public embeddings API.
- **Ollama (D) viable opt-in**: great quality + multilingual, but requires the user to install Ollama. That's a heavy precondition; ship as `OllamaEmbeddingProvider` behind `FLOW_EMBEDDINGS=ollama` env.
- **Cohere (E) avoid**: same cloud lock-in concern as OpenAI, worse DX for local-first users.
- **FastEmbed (F) recommended alternative**: BGE-small-en via ONNX runtime is ~10× smaller than torch-based sentence-transformers. Strong quality. Recommend as the default if we want to avoid torch. Pick ONE of A/F for v1, not both — both behind `EmbeddingProvider` ABC is fine but the default must be one.

## Recommendation (preliminary)

- **Storage**: **A. sqlite-vec**, behind a `VectorIndex` ABC so we can swap to LanceDB or pure numpy without rewriting callers.
- **Embedding**: **A. sentence-transformers `all-MiniLM-L6-v2`** as v1 default, with **F. FastEmbed BGE-small** as a future lighter alternative. Both pluggable behind `EmbeddingProvider` ABC.
- **Confidence**: **medium**. The architecture is solid and the precedents (InMemoryBackend + auto_suggester + observability counters) are well-established. Confidence is knocked down from "high" by: (a) sqlite-vec is pre-v1, (b) torch dep size will hurt cold-start time on first search, (c) bilingual quality of `all-MiniLM-L6-v2` is unverified for this repo's EN/ES mix.

## Architecture Sketches

### Sketch A — `HybridBackend` wraps `InMemoryBackend` + vector index

- New `HybridBackend(EngramBackend)` constructor takes `(inner: EngramBackend, embeddings: EmbeddingProvider, index: VectorIndex)`. It composes, not replaces: the inner backend keeps doing what it does (FTS5-prose or substring).
- `save_phase` flow: write to `inner.mem_save`, then asynchronously compute embedding and append to `index`. Sync path is fine for v1 (embeddings are <50ms on CPU for short prose).
- `mem_search(query, topic_key, limit)` → unchanged (prose/keyword). New method `mem_search_semantic(query, limit)` → cosine KNN. New method `mem_search_hybrid(query, limit, alpha)` → RRF-fused top-k.
- CLI: `flow search <query>` defaults to hybrid; `--semantic` and `--fts` flags flip it; `--reindex` walks all observations and recomputes.
- **Pros**: minimal blast radius; existing tests untouched; only new code paths to cover. **Cons**: two backends to keep in sync (inner + index).

### Sketch B — Lazy compute + sidecar SQLite file

- Same as A, but embeddings computed LAZILY on first `mem_search_semantic` call (or via explicit `flow reindex`).
- Persisted in `~/.flow-engineering/vectors.sqlite` via sqlite-vec; in-memory cache rebuilt on backend init.
- Background `flow watch` hook re-embeds new observations on `save_progress: merged` status.
- **Pros**: no save-time latency penalty; explicit reindex command fits flow-engineering's CLI shape. **Cons**: first search after a fresh install has a multi-second pause (acceptable if surfaced with a progress line).

### Sketch C — Pluggable everything, swappable from day 1 (premature-abstraction risk)

- `EmbeddingProvider` ABC + `SentenceTransformerProvider` (default), `FastEmbedProvider`, `OllamaProvider`, `NoopProvider`.
- `VectorIndex` ABC + `SqliteVecIndex` (default), `InMemoryIndex` (tests), `NumpyIndex` (fallback).
- `HybridBackend` composes them.
- Settings resolution via env: `FLOW_EMBEDDINGS=sentence-transformers|fastembed|ollama|none`, `FLOW_VECTOR_INDEX=sqlite-vec|memory|numpy`.
- **Pros**: future-proof for v2 scale-up, every layer unit-testable in isolation. **Cons**: more upfront design surface, more docs, risk of speculative generality when only 1 backend ships in v1. **Recommendation**: only go this far if propose-phase finds clear demand for the alternative providers; otherwise Sketch A is enough.

## Risks and Unknowns

- **Embedding model lock-in**: switching models = re-embed everything. Mitigation: store `model_name` + `model_version` per vector row; ship `flow reindex --model ...` CLI.
- **Local-first constraint vs torch**: `sentence-transformers` pulls ~500MB of torch. Cold-start time on first `flow search` will be noticeable. Mitigation: lazy-import via `[vectors]` optional extra; explicit "loading model…" stderr line.
- **Embedding storage growth**: 384 dims × 4 bytes = ~1.5KB per observation × 5k observations ≈ 7.5MB. Negligible. At 100k observations: 150MB. Still fine for SQLite.
- **Cross-language drift**: `all-MiniLM-L6-v2` is English-trained. For this repo's bilingual EN/ES prose, recall on Spanish queries may be mediocre. Mitigation: optionally swap to `paraphrase-multilingual-MiniLM-L12-v2` via `FLOW_EMBEDDINGS_MODEL` env.
- **Test determinism**: cosine scores are floats. Mitigation: pin test embeddings to a fixture file; assert rank order rather than exact scores.
- **sqlite-vec pre-v1**: breaking changes possible. Mitigation: pin minor version in `[vectors]` extra; wrap behind `VectorIndex` so we can swap to LanceDB if needed.
- **Non-breaking FTS5 contract (REQ-5)**: must keep `mem_search` semantics intact. Mitigation: do NOT modify `mem_search`; add `mem_search_semantic` and `mem_search_hybrid` as new methods.
- **Observability gap**: need counters (`vector_search_invoked_total`, `embedding_computed_total`, `hybrid_search_invoked_total`, `vector_index_size`, `reindex_duration_ms`). Use existing `observability.increment()` sink — no new dep.
- **Auto-suggester integration**: REQ-6 already swappable behind same interface. v2 can rerank `auto_suggest_code_refs` candidates using semantic similarity; out of scope for v1 but the seam must be preserved.
- **Daemon behavior**: `flow watch` already triggers on apply-progress. New change MAY add a `--reindex` flag but should not change watch semantics.

## Open Questions for Propose Phase

- Do we ship Sketch A (sync embed on save) or Sketch B (lazy embed on first search) as the v1 default? Recommend A — it's simpler and matches the "save_phase is the canonical write path" precedent from decision-code-linking.
- Should the default `HybridBackend` be opt-in via env (`FLOW_VECTOR_SEARCH=1`) or always-on behind the scenes? Recommend opt-in to preserve backward compatibility for users who don't want the torch dep pulled in.
- Do we need the FastEmbed path in v1 or only after user demand? Recommend defer to v1.1 — ship sentence-transformers only, document FastEmbed as a planned alternative.
- Embedding text: prose only, or prose + title? Recommend prose only (title is often empty/duplicated); document the decision.
- Where does the index file live? `~/.flow-engineering/vectors.sqlite` matches the metrics.jsonl precedent.

## Next Phase

`sdd-propose vector-semantic-search` based on this exploration.

---

**What**: Mapped current FTS5/Engram abstraction, evaluated 7 storage + 6 embedding options, sketched 3 architectures.
**Why**: User asked for vector semantic search to fix FTS5 keyword limitations (cross-language, semantic drift).
**Where**: `src/flow_engineering/engram_io.py` (EngramBackend ABC), `src/flow_engineering/cli.py` (`_default_save_backend`), `src/flow_engineering/auto_suggest_code_refs.py` (REQ-6 swappable seam), `src/flow_engineering/observability.py` (counter sink), `pyproject.toml` (deps).
**Learned**: FTS5 lives in the EXTERNAL Engram MCP server — this repo only defines the ABC. The non-breaking REQ-5 contract from decision-code-linking means new methods must be additive. `InMemoryBackend` is the default for v0.3.0 and the primary seam for tests. Auto-suggester (REQ-6) is already behind an interface ready for semantic reranking. Project is local-first + minimal-deps; torch would be the first big dep addition.

**Session**: sdd-vector-semantic-search-explore-2026-06-26
**Topic**: sdd/vector-semantic-search/explore
**Engram**: #139
**Next**: sdd-propose vector-semantic-search
