<!-- Archived 2026-06-26 from openspec/changes/vector-semantic-search/spec.md -->
# Spec: vector-semantic-search

**Change:** `vector-semantic-search`
**Builds on:** `proposal.md` (Approach A — additive `HybridBackend`, opt-in via `FLOW_VECTOR_SEARCH=1` + `[vectors]` extra), `design.md` (D1-D11 resolved: NON-BREAKING ABC, composition, sqlite-vec, lazy torch, both-gate activation, linear-combo scoring, sync streaming reindex, float32 storage, deterministic mock, FTS-only fallback)
**Date:** 2026-06-26
**Status:** SPECIFIED → ready for sdd-tasks

## Goal

`flow-engineering`'s `EngramBackend.mem_search` is FTS5 prose-only; bilingual EN/ES notes and semantic drift ("show me decisions about drift detection" misses if `drift` is not literally present) collapse to zero hits. This change ships **additive** semantic and hybrid retrieval on top of the existing prose contract — never replacing `mem_search` — so users find observations by meaning, by language, and across phrasing while every REQ-5 (`code_refs` tokenization) and REQ-9..16 (drift detector id-based lookups) guarantee stays intact. Activation is **opt-in** via BOTH `FLOW_VECTOR_SEARCH=1` AND the `[vectors]` extra; the default install NEVER pulls torch. The semantic interface adds two new methods to `EngramBackend` as NON-BREAKING defaults raising `NotImplementedError`, mirroring the `update_observation` precedent at `engram_io.py:86`. ABC is annotated v1.1 in docstring (documentation only).

**Gate state machine** (matches design D6):

| `[vectors]` extra | `FLOW_VECTOR_SEARCH` | CLI flag | Behavior |
|---|---|---|---|
| missing | anything | absent | `_default_save_backend` returns inner backend unchanged; prose path zero regression |
| missing | anything | `--semantic` | CLI exits non-zero with `pip install flow-engineering[vectors]` |
| present | unset | absent | inner backend unchanged (prose only); `--semantic` works one-shot |
| present | unset | `--semantic` | explicit one-shot semantic call against the constructed index |
| present | `=1` | absent | `HybridBackend` IS the default; `mem_save` writes embedding on save |

---

## PR#1 — Core hybrid backend + embedding pipeline

### REQ-17: Semantic search activation gate

The system SHALL provide an opt-in activation gate for `mem_search_semantic(query, k)` and `mem_search_hybrid(query, k, alpha)` such that BOTH conditions hold before any embedding code path runs:

1. The `[vectors]` extra SHALL be installed (i.e. `sqlite_vec`, `sentence_transformers`, and `torch` are importable).
2. The environment variable `FLOW_VECTOR_SEARCH` SHALL equal the string `"1"`.

If either condition fails, calling `mem_search_semantic` or `mem_search_hybrid` SHALL raise `VectorSearchDisabled` with an actionable message: when the extra is missing, the message SHALL be `"Semantic search disabled: install [vectors] extra — pip install flow-engineering[vectors]"`; when the extra is present but the env var is unset, the message SHALL be `"Semantic search disabled: set FLOW_VECTOR_SEARCH=1"`. The CLI `flow search --semantic <query>` flag SHALL act as an explicit override: it SHALL check the extra independently of the env var and exit non-zero with the install hint if the extra is missing. The legacy prose `mem_search` path SHALL remain byte-identical when the gate is unmet (zero regression).

#### Scenario: Semantic search with both extra and env set returns results

- GIVEN the `[vectors]` extra is installed
- AND the env var `FLOW_VECTOR_SEARCH=1`
- WHEN `mem_search_semantic("drift detection", k=5)` runs against a seeded corpus of three observations
- THEN it returns a list of up to 5 result dicts
- AND each result has keys `observation_id`, `score`, `rank`
- AND results are ordered by cosine similarity descending

#### Scenario: Semantic search without extra raises VectorSearchDisabled with install hint

- GIVEN the `[vectors]` extra is NOT installed (mock by patching `sqlite_vec` import to raise `ImportError`)
- WHEN `mem_search_semantic("drift detection")` is called
- THEN it raises `VectorSearchDisabled`
- AND the exception message contains `pip install flow-engineering[vectors]`
- AND no torch import is attempted

#### Scenario: Semantic search without env var (extra present) raises VectorSearchDisabled with env hint

- GIVEN the `[vectors]` extra is installed
- AND the env var `FLOW_VECTOR_SEARCH` is unset or any value other than `"1"`
- WHEN `mem_search_semantic("drift detection")` is called
- THEN it raises `VectorSearchDisabled`
- AND the exception message contains `FLOW_VECTOR_SEARCH=1`

#### Scenario: CLI `--semantic` flag with extra missing exits non-zero with clear error

- GIVEN the `[vectors]` extra is NOT installed
- WHEN `flow search --semantic "drift detection"` runs
- THEN the process exits non-zero
- AND stderr contains `pip install flow-engineering[vectors]`
- AND no traceback is printed (clear actionable message, not a raw `ImportError`)

#### Scenario: `mem_search` (FTS5) still works unchanged when vectors disabled

- GIVEN the `[vectors]` extra is NOT installed
- AND the env var `FLOW_VECTOR_SEARCH` is unset
- WHEN `mem_search("drift detection")` runs against the seeded corpus
- THEN it returns the FTS5 prose hits unchanged
- AND the call completes without any attempt to import `torch` or `sqlite_vec`

---

### REQ-18: Hybrid scoring (alpha + BM25 normalization)

The system SHALL provide `EngramBackend.mem_search_hybrid(query, k=10, alpha=0.5)` that returns the top-`k` observations ranked by the linear combination:

```
score = α · cosine_sim + (1 - α) · normalize_bm25(fts_score)
```

where `normalize_bm25(x) = (x - min) / (max - min + ε)` is computed over the FTS result set for the current query (`min` and `max` are the minimum and maximum FTS scores among the prose hits; `ε = 1e-9` prevents division by zero when all FTS scores are equal). `alpha` SHALL default to `0.5`; valid range SHALL be `[0.0, 1.0]`; out-of-range `alpha` SHALL raise `ValueError` with message `"alpha must be in [0.0, 1.0]"`. When `alpha=1.0` the result set SHALL equal `mem_search_semantic(query, k)` (pure semantic); when `alpha=0.0` it SHALL equal `mem_search(query)` (pure FTS5). Observations lacking an embedding SHALL contribute FTS-only score (`cosine_sim = 0`) in hybrid mode and SHALL be absent from pure semantic results (with a `vector_search_missing_embedding_total` counter increment per design D11).

#### Scenario: Hybrid with alpha=0.5 ranks semantic + FTS blended (worked example)

- GIVEN a corpus of three observations with prose `["drift detection strategy", "drift alarm", "logging best practices"]` (obs1, obs2, obs3 respectively)
- AND FTS5 prose search returns `[obs1 (raw=0.85), obs2 (raw=0.40)]`
- AND `mem_search_semantic` returns `[obs1 (cosine=0.92), obs3 (cosine=0.78)]`
- WHEN `mem_search_hybrid("how do we detect drift", k=10, alpha=0.5)` runs
- THEN the returned top-3 order is `obs1, obs3, obs2`
- AND the exact scores are `obs1 ≈ 0.96`, `obs3 ≈ 0.39`, `obs2 ≈ 0.00` (within float tolerance ±1e-3)
- AND the rank index of `obs3` is `1` (semantic contribution pulls it above `obs2` despite zero FTS overlap)

#### Scenario: Hybrid with alpha=1.0 equals pure semantic (sanity)

- GIVEN the seeded three-observation corpus
- WHEN `mem_search_hybrid(query, k=10, alpha=1.0)` runs
- AND `mem_search_semantic(query, k=10)` runs
- THEN both return the same observation ids in the same order
- AND the scores differ by at most `1e-3` (linear combo degenerates to pure cosine when `normalize_bm25` collapses to 0 contribution weight)

#### Scenario: Hybrid with alpha=0.0 equals pure FTS (sanity)

- GIVEN the seeded three-observation corpus
- WHEN `mem_search_hybrid(query, k=10, alpha=0.0)` runs
- AND `mem_search(query)` runs
- THEN both return the same observation ids in the same order
- AND the scores are the FTS-only scores (semantic contribution collapses to 0 weight)

#### Scenario: Alpha=1.5 raises ValueError

- GIVEN `alpha=1.5`
- WHEN `mem_search_hybrid("query", alpha=1.5)` runs
- THEN it raises `ValueError`
- AND the message contains `[0.0, 1.0]`
- AND no embedding work is attempted

#### Scenario: Empty query returns empty results without division-by-zero

- GIVEN a query that matches zero observations in the FTS index
- WHEN `mem_search_hybrid(query, k=10, alpha=0.5)` runs
- THEN it returns `[]`
- AND the `min == max` case in `normalize_bm25` is handled by the `+ ε` epsilon (no `ZeroDivisionError`)
- AND `mem_search_semantic` is NOT called as a fallback (the hybrid path is explicit, not a fallback chain)

---

### REQ-19: EmbeddingProvider ABC + lazy import

The system SHALL provide an `EmbeddingProvider` abstract base class in `src/flow_engineering/embedding_provider.py` with a method `embed(texts: list[str]) -> np.ndarray` of shape `(len(texts), 384)`. The v1 production implementation SHALL be `SentenceTransformersProvider` with model `sentence-transformers/all-MiniLM-L6-v2` and `dim = 384`. The `torch` package SHALL be imported ONLY inside `SentenceTransformersProvider.__init__` (function-body import); the module-level import path of `flow_engineering.embedding_provider` MUST NOT trigger `torch` import. If `torch` (or `sentence_transformers`) is missing, `SentenceTransformersProvider.__init__` SHALL raise `EmbeddingProviderUnavailable` with message `"Install [vectors] extra: pip install flow-engineering[vectors]"`. The `MockEmbeddingProvider` test fixture SHALL return deterministic unit-norm vectors of length 384 derived from a hash of the input text (same input → same vector; L2 norm ≈ 1.0).

#### Scenario: MockEmbeddingProvider returns deterministic 384-dim vectors

- GIVEN a `MockEmbeddingProvider`
- WHEN `embed(["hello world"])` is called twice in a row
- THEN both calls return identical numpy arrays
- AND the array shape is `(1, 384)`
- AND the L2 norm of the vector is within `[0.99, 1.01]` of `1.0`
- WHEN `embed(["hello world"])` and `embed(["goodbye world"])` are compared
- THEN the vectors differ (hash-based derivation, not all-zeros)

#### Scenario: `import flow_engineering.embedding_provider` does not trigger torch import

- GIVEN a fresh Python interpreter
- WHEN `import flow_engineering.embedding_provider` runs
- THEN `"torch"` is NOT in `sys.modules`
- AND `"sentence_transformers"` is NOT in `sys.modules`
- AND the `EmbeddingProvider` ABC is importable and usable (e.g. `MockEmbeddingProvider` can be instantiated without torch)

#### Scenario: SentenceTransformersProvider raises ImportError when torch missing

- GIVEN `torch` is removed from `sys.modules` (or patched to raise `ImportError` on import)
- WHEN `SentenceTransformersProvider("sentence-transformers/all-MiniLM-L6-v2")` is instantiated
- THEN it raises `EmbeddingProviderUnavailable` (a subclass of `ImportError`)
- AND the message contains `pip install flow-engineering[vectors]`
- AND no partial initialization leaves the provider in an inconsistent state

#### Scenario: Embedding output shape is (N, 384) for N inputs

- GIVEN a `MockEmbeddingProvider`
- WHEN `embed(["a", "b", "c", "d", "e"])` is called
- THEN the returned numpy array has shape `(5, 384)`
- AND each row has L2 norm within `[0.99, 1.01]` of `1.0`
- WHEN `embed([])` is called with an empty input list
- THEN the returned array has shape `(0, 384)`

---

### REQ-20: sqlite-vec storage (table + virtual + sync)

The system SHALL persist vectors in `~/.flow-engineering/vectors.sqlite` (or the path returned by `vectors_sqlite_path()` in `src/flow_engineering/_paths.py`) using two cooperating tables:

| Table | Kind | Schema |
|---|---|---|
| `observation_embeddings` | regular | `(observation_id TEXT PRIMARY KEY, vector BLOB(1536), model_version TEXT, created_at TEXT)` — audit row; 384 floats × 4 bytes = 1536 bytes |
| `vec_observations` | sqlite-vec `vec0` virtual | `(observation_id TEXT PRIMARY KEY, vector FLOAT[384])` — KNN index |

The `SqliteVecStore` class SHALL expose `add(obs_id, vector)`, `search(vector, k) -> list[(obs_id, distance)]`, `delete(obs_id)`, and `count() -> int`. Writes SHALL be wrapped in a SQLite transaction; a failure during `add` SHALL roll back the entire batch (no partial writes). `delete` SHALL remove both the `vec0` row AND the audit row atomically. The `count()` method SHALL reflect the count after all committed writes.

#### Scenario: Add → search round-trip returns added observation as top-1

- GIVEN a fresh `SqliteVecStore` (empty file or in-memory `:memory:`)
- WHEN `add("obs1", unit_vector)` runs
- AND `search(unit_vector, k=1)` runs
- THEN the result is `[("obs1", ~0.0)]` (cosine distance to itself ≈ 0; exact `0.0` not asserted because sqlite-vec returns float)

#### Scenario: Delete removes observation from search results

- GIVEN a `SqliteVecStore` with `obs1` and `obs2` added
- WHEN `delete("obs1")` runs
- AND `search(any_vector, k=10)` runs
- THEN `"obs1"` is NOT in the result list
- AND `"obs2"` IS in the result list
- AND `count() == 1`

#### Scenario: count() reflects add/delete accurately

- GIVEN a fresh `SqliteVecStore`
- WHEN `count()` is called before any writes
- THEN it returns `0`
- WHEN `add("obs1", v1)` AND `add("obs2", v2)` AND `add("obs3", v3)` run
- THEN `count()` returns `3`
- WHEN `delete("obs2")` runs
- THEN `count()` returns `2`

#### Scenario: Vector BLOB size matches 384 × 4 = 1536 bytes

- GIVEN a `SqliteVecStore`
- WHEN `add("obs1", random_384_dim_vector)` runs
- AND the `observation_embeddings.vector` column is read back as raw bytes
- THEN the byte length is exactly `1536`
- AND the deserialized numpy array has shape `(384,)` and dtype `float32`
- AND the values round-trip within `1e-6` of the input

#### Scenario: Search returns top-k ordered by ascending distance

- GIVEN a `SqliteVecStore` with 10 random 384-dim vectors at ids `obs1..obs10`
- AND a query vector `q` chosen close to `obs7` (cosine distance ≈ 0.05)
- WHEN `search(q, k=3)` runs
- THEN the returned list has exactly 3 `(obs_id, distance)` tuples
- AND `obs7` is at position 0
- AND the distances are sorted in ascending order (closest first)

---

### REQ-21: Reindex command (sync streaming + idempotent)

The system SHALL provide a `flow reindex [--batch-size=100] [--dry-run]` subcommand that runs synchronously and streams progress to stderr. The command SHALL iterate observations via `iter_observations()`, batch them into groups of `--batch-size` (default `100`), embed the prose of each observation via `split_prose_and_refs` + `EmbeddingProvider.embed_batch`, and upsert each vector into `SqliteVecStore`. One stderr line SHALL be emitted per completed batch in the form `reindex: N/M (P%) embedded`. On completion SHALL emit: `reindex: done — K observations indexed in T seconds`. The command SHALL be idempotent: re-running on a fully-indexed corpus reports `0 observations indexed` (uses `INSERT OR REPLACE` keyed on `(observation_id, model_version)`). The command SHALL crash-resume: transactions commit per batch, so a restart picks up where it stopped (no separate checkpoint log; `INSERT OR REPLACE` overwrites stale rows from previous partial runs). `--dry-run` SHALL count observations needing reindex WITHOUT writing any rows.

#### Scenario: `flow reindex` on empty corpus completes with 0 indexed

- GIVEN an empty Engram backend (zero observations)
- WHEN `flow reindex` runs
- THEN the process exits `0`
- AND stderr contains `reindex: done — 0 observations indexed`
- AND `count() == 0` after the run

#### Scenario: `flow reindex` on 250 observations emits progress lines + done

- GIVEN a seeded Engram backend with 250 observations
- WHEN `flow reindex --batch-size=100` runs
- THEN stderr contains exactly three progress lines: `reindex: 100/250 (40%) embedded`, `reindex: 200/250 (80%) embedded`, `reindex: 250/250 (100%) embedded`
- AND stderr contains `reindex: done — 250 observations indexed in T seconds`
- AND `count() == 250` after the run
- AND the process exits `0`

#### Scenario: Second `flow reindex` is idempotent (no-op)

- GIVEN a corpus of 100 observations that have been reindexed once
- WHEN `flow reindex` runs a second time
- THEN stderr contains `reindex: done — 0 observations indexed` (or equivalent no-op summary; counter delta = 0)
- AND `count() == 100` (unchanged)
- AND the process exits `0`
- AND `reindex_observations_total` increments by `0` (idempotency is observed via the counter contract)

#### Scenario: `--dry-run` reports count without writing

- GIVEN a seeded Engram backend with 100 unindexed observations
- AND `count() == 0` before the run
- WHEN `flow reindex --dry-run` runs
- THEN stderr contains a count line stating `100 observations need reindex`
- AND `count() == 0` after the run (no writes)
- AND the process exits `0`

#### Scenario: Crash mid-run — restart completes from last committed batch

- GIVEN a `flow reindex` run that committed the first batch (100 observations) and crashed before committing the second (50 of 100)
- WHEN `flow reindex` is invoked a second time
- THEN it indexes the remaining 50 (the 100 already committed are replaced via `INSERT OR REPLACE` with identical vectors, so no churn)
- AND stderr reports `reindex: done — 100 observations indexed` total (count is the corpus size, not the delta)
- AND `count() == 100` after the second run
- AND the process exits `0`

---

### REQ-22: Observability counters

The system SHALL emit the following JSONL counter events via `observability.increment()` and persist them in `~/.flow-engineering/metrics.jsonl` (overridable via `FLOW_METRICS_PATH`):

| Counter | Type | Trigger |
|---|---|---|
| `vector_search_invoked_total{trigger=cli\|programmatic}` | counter | per `mem_search_semantic` or `mem_search_hybrid` call |
| `vector_search_results_returned_total` | counter | sum of result-list lengths across vector searches |
| `vector_search_latency_ms` | histogram | wall-clock duration of every vector search; P50/P95/P99 surfaced in `flow metrics` summary |
| `vector_index_size_observations` | gauge | current embedding count (sampled at `flow metrics` render time) |
| `reindex_observations_total` | counter | increments by batch size per `flow reindex` batch |
| `reindex_duration_seconds` | gauge | total elapsed seconds of the last `flow reindex` |

Counter names SHALL match the REQ-8 convention established in `decision-code-linking`: `subject_event_total` for counters (e.g. `suggest_invoked_total`, `bindings_confirmed_total`, `reindex_observations_total`), `subject_latency_ms` or `subject_duration_seconds` for timing. A `record_vector_summary(...)` helper SHALL aggregate vector metrics and emit exactly one JSONL line per `flow reindex` invocation (parallels `record_drift_summary` from REQ-12 and `record_backfill_coverage` from REQ-8). All 6 counters SHALL be observable in `flow metrics` summary output.

#### Scenario: `vector_search_invoked_total` increments per `mem_search_hybrid` call

- GIVEN the metrics sink has `vector_search_invoked_total = N` (counter value)
- WHEN `mem_search_hybrid("drift detection", k=5)` runs once
- THEN `vector_search_invoked_total` reads `N + 1` from the metrics file
- AND the JSONL event includes the `trigger` label (one of `cli`, `programmatic`)

#### Scenario: `vector_search_latency_ms` appears in metrics output

- GIVEN a `mem_search_hybrid` call that took `42 ms`
- WHEN `flow metrics` runs
- THEN the summary output includes `vector_search_latency_ms`
- AND the histogram summary shows P50, P95, P99 percentiles computed over all vector searches in the metrics file
- AND the P50 is at least the median of the recorded `elapsed_ms` values

#### Scenario: `reindex_observations_total` matches total observations after reindex

- GIVEN a seeded Engram backend with 100 observations
- AND the metrics sink has `reindex_observations_total = M`
- WHEN `flow reindex` runs to completion
- THEN `reindex_observations_total` reads `M + 100` from the metrics file
- AND `reindex_duration_seconds` reads the elapsed wall-clock seconds of the run

#### Scenario: Counter names match REQ-8 convention (no naming drift)

- GIVEN the documented list of six counters above
- WHEN any future change reads these counters (e.g. `flow metrics`, dashboards, alerts)
- THEN the names MUST NOT change without a deprecation period documented in `CHANGELOG.md`
- AND the documented list SHALL appear in `openspec/specs/observability/spec.md` (or equivalent canonical counter catalog) so the contract is discoverable
- AND no counter is renamed silently across the `decision-code-linking` → `vector-semantic-search` boundary (e.g. `embedding_computed_total` from design.md D11 is a sub-counter, not a rename; it MAY exist alongside `vector_search_invoked_total` as long as both names are stable)

---

## Out of Scope (deferred)

The following are explicitly out of scope for this change and belong to named follow-ups:

- **`auto_suggest_code_refs` rerank with semantic similarity** — REQ-6 seam is preserved; reranking suggestions by embedding distance is a v2 follow-up.
- **Cross-project federation search** — owned by `cross-project-federation` (#4); per-project `vectors.sqlite` boundaries are respected.
- **Graph-snapshots-aware temporal search** — owned by `graph-snapshots` (#5); embeddings are keyed by `observation_id`, not graph nodes.
- **Hosted embedding fallback (OpenAI, Cohere)** — v1 is local-first (`sentence-transformers` only); hosted providers are a v1.1 opt-in.
- **Int8 quantization** — `sqlite-vec` 0.1.x lacks int8 KNN; defer to v1.1 after measuring recall drift on the bilingual EN/ES corpus.
- **Async embed-on-save** — v1 is sync (`save_observation` blocks for ~50ms CPU per ≤2KB prose); async is a v1.1 follow-up if profiling shows a need.
- **Daemon-driven drift on vector index changes** — `flow watch` does not subscribe to `vectors.sqlite` writes; only `flow watch --drift` (REQ-15, already shipped) watches the decision layer.
- **Dynamic model hot-swap at runtime** — `flow reindex --model <name>` is the only model-change path; no in-process model reload API.

---

## BDD Feature File Plan

| Feature file | Status | Covers | Scenarios |
|---|---|---|---|
| `tests/bdd/req17_semantic_search_activation.feature` | NEW | REQ-17 | 5 |
| `tests/bdd/req18_hybrid_scoring.feature` | NEW | REQ-18 | 5 |
| `tests/bdd/req19_embedding_provider.feature` | NEW | REQ-19 | 4 |
| `tests/bdd/req20_sqlite_vec_storage.feature` | NEW | REQ-20 | 5 |
| `tests/bdd/req21_reindex_command.feature` | NEW | REQ-21 | 5 |
| `tests/bdd/req22_vector_observability.feature` | NEW | REQ-22 | 4 |
| **Total BDD scenarios** | | | **28** |

Step definitions land in `tests/bdd/test_vector_semantic_search_steps.py` (NEW; pytest-bdd glue per file).

---

## Cross-impact

| Queued / shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `binding.split_prose_and_refs` is the embed-text seam; `code_refs` block MUST be stripped before embedding | Required predecessor; we consume it (no change to `decision-code-linking` files) |
| `decision-reality-drift` (shipped v0.3.0) | Drift uses `CodeRef.id` lookup; embedding-agnostic | No conflict; document non-interaction |
| `cross-project-federation` (#4) | Per-project `vectors.sqlite`; federation owns cross-project routing | Compatible (boundary respected) |
| `graph-snapshots` (#5) | Embeddings keyed by `observation_id`, not graph nodes | No conflict |
| `auto_suggest_code_refs` v2 (unnamed future) | REQ-6 seam preserved | Complementary, NOT in this PR |
| `observability` (REQ-8 contract) | Six new counters plug into existing `observability.increment()`; names follow established `subject_event_total` convention | Beneficial; REQ-22 scenario 4 explicitly checks for naming drift |
| Third-party `EngramBackend` subclasses | v1.1 ABC adds `mem_search_semantic` + `mem_search_hybrid` as `NotImplementedError` defaults (mirrors `update_observation` precedent) | NON-BREAKING; old subclasses import unchanged |

---

## References

- Explore: Engram `sdd/vector-semantic-search/explore` (#139) — storage/embed/timing/gate/fixture decisions
- Proposal: Engram `sdd/vector-semantic-search/proposal` (#140) — Sketch A additive `HybridBackend`, 6 open questions for design
- Design: Engram `sdd/vector-semantic-search/design` (#141) — D1-D11 resolved (ABC version policy, sqlite-vec 3.13 wheel, gate semantics, linear-combo formula, sync reindex, float32 storage)
- Predecessor spec: `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md` (REQ-5 prose tokenization, REQ-8 counter contract, REQ-6 auto-suggest seam)
- Predecessor spec: `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` (REQ-12 counter-batch helper precedent, REQ-15 daemon wiring, REQ-16 SKILL.md prose pattern)
- Predecessor design: `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md` (reference format for spec/design alignment)
- Flow Engineering base spec: `c:/dev/proyects/flow-engineering/spec/spec.md` (project-wide conventions)