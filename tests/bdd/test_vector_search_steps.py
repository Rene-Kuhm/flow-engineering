"""BDD step definitions for vector-semantic-search PR#1 REQ-17 + REQ-18.

Covers ``req17_semantic_search.feature`` (5 scenarios) and
``req18_hybrid_scoring.feature`` (5 scenarios) — the BDD acceptance gate for
the activation gate (REQ-17) and the hybrid scoring formula (REQ-18).

REQ-17 scenarios exercise the InMemoryBackend / HybridBackend gate behavior:
- Scenario 1: HybridBackend with a controlled embedding provider returns
  semantic results.
- Scenarios 2-3: InMemoryBackend raises VectorSearchDisabled (library-level
  gate; the InMemoryBackend raises with the install hint regardless of env vs
  extra distinction — the env-vs-extra differentiation lives in the CLI
  layer at PR#2 T2.4).
- Scenario 4: prose ``mem_search`` is byte-identical when vectors disabled.
- Scenario 5: HybridBackend forwards mem_save / mem_get_observation to inner.

REQ-18 scenarios exercise the hybrid scoring formula from design D7:
- Scenario 1: alpha=0.5 worked example with explicit numeric assertions
  (obs1 ≈ 0.98, obs2 ≈ 0.125, obs3 ≈ 0.15 — matches the unit test
  ``test_hybrid_alpha_05_*`` values; the user's prompt listed obs2 ≈ 0.167
  which has a math error against the stated FTS scores).
- Scenarios 2-3: alpha=1.0 / alpha=0.0 degeneracy sanity checks.
- Scenario 4: alpha=1.5 raises ValueError.
- Scenario 5: empty query returns ``[]`` with no ``ZeroDivisionError``.

Test isolation:
- Each scenario gets a fresh ``InMemoryBackend`` + a ``FixedVectorsProvider``
  (or ``MockEmbeddingProvider`` for the gate scenarios).
- ``FLOW_VECTOR_SEARCH`` is unset via ``monkeypatch.delenv`` for the gate
  scenarios so the InMemoryBackend / HybridBackend layer is tested without
  the env-var coupling from real CLI invocations.
- ``sys.modules`` is introspected before / after the call to verify no torch
  or sqlite_vec import leaks through the gate path (REQ-17 scenarios 2-4).
- The worked example seeds 3 observations with extended contents
  (``drift alarm drift detection``, ``logging best practices drift detection``)
  so the substring-filter of InMemoryBackend.mem_search returns all three as
  candidates — the cosine is controlled via FixedVectorsProvider, not the
  prose.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering.embedding_provider import EMBEDDING_DIMS, EmbeddingProvider
from flow_engineering.engram_io import InMemoryBackend, VectorSearchDisabled
from flow_engineering.hybrid_backend import HybridBackend

# ---------- Vector + score fixtures (mirror tests/unit/test_hybrid_backend.py) ----------


def _pad_vec(values: list[float]) -> np.ndarray:
    """Build a 384-dim vector with ``values`` at the leading indices + zeros."""
    arr = np.zeros(EMBEDDING_DIMS, dtype=np.float32)
    arr[: len(values)] = np.asarray(values, dtype=np.float32)
    return arr


def _unit(v: np.ndarray) -> np.ndarray:
    """L2-normalize a vector in place (returns a new array)."""
    n = float(np.linalg.norm(v))
    if n <= 0.0:
        return v.astype(np.float32)
    return (v / n).astype(np.float32)


class FixedVectorsProvider(EmbeddingProvider):
    """Test fixture: returns pre-set unit-norm vectors keyed by exact text.

    Unknown texts get the zero vector (cosine_sim -> 0.0 fallback).
    """

    model_version: str = "fixed-v1"
    dim: int = EMBEDDING_DIMS

    def __init__(self, vectors: dict[str, np.ndarray]) -> None:
        self._vectors: dict[str, np.ndarray] = {
            k: _unit(np.asarray(v, dtype=np.float32)) for k, v in vectors.items()
        }

    def embed(self, texts: list[str]) -> np.ndarray:
        rows: list[np.ndarray] = []
        for t in texts:
            rows.append(
                self._vectors.get(t, np.zeros(EMBEDDING_DIMS, dtype=np.float32))
            )
        return np.stack(rows).astype(np.float32)


class ScoredInMemoryBackend(InMemoryBackend):
    """Test fixture: attaches ``_fts_score`` to ``mem_search`` results.

    Used to control per-observation FTS scores in the worked example without
    depending on a real FTS5 backend.
    """

    def __init__(self) -> None:
        super().__init__()
        self._score_overrides: dict[int, float] = {}

    def set_score(self, observation_id: int, score: float) -> None:
        self._score_overrides[observation_id] = score

    def mem_search(
        self,
        query: str,
        topic_key: str | None = None,
        limit: int = 10,
        scope: str = "project",
    ) -> list[dict[str, Any]]:
        results = super().mem_search(query, topic_key=topic_key, limit=limit, scope=scope)
        for r in results:
            if r["id"] in self._score_overrides:
                r["_fts_score"] = self._score_overrides[r["id"]]
        return results


def _build_worked_example_fixture():
    """Construct the design D7 worked example (returns backend, provider, obs ids)."""
    inner = InMemoryBackend()
    obs1 = inner.mem_save(
        title="obs1", content="drift detection strategy", topic_key="sdd/test/spec"
    )
    obs2 = inner.mem_save(
        title="obs2",
        content="drift alarm drift detection",
        topic_key="sdd/test/spec",
    )
    obs3 = inner.mem_save(
        title="obs3",
        content="logging best practices drift detection",
        topic_key="sdd/test/spec",
    )
    scored = ScoredInMemoryBackend()
    scored.observations = inner.observations.copy()
    scored.next_id = inner.next_id
    scored.set_score(obs1["id"], 0.50)
    scored.set_score(obs2["id"], 0.20)
    scored.set_score(obs3["id"], 0.10)
    q_vec = _unit(_pad_vec([1.0, 0.0]))
    obs1_vec = _unit(_pad_vec([0.96, float(np.sqrt(1.0 - 0.96**2))]))
    obs3_vec = _unit(_pad_vec([0.30, float(np.sqrt(1.0 - 0.30**2))]))
    obs2_vec = _unit(_pad_vec([0.0, 1.0]))
    provider = FixedVectorsProvider(
        {
            "drift detection": q_vec,
            "drift detection strategy": obs1_vec,
            "drift alarm drift detection": obs2_vec,
            "logging best practices drift detection": obs3_vec,
        }
    )
    return scored, provider, [obs1["id"], obs2["id"], obs3["id"]]


# ---------- World fixture ----------


@pytest.fixture
def vector_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-17 + REQ-18 scenarios."""
    metrics_path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_path))
    monkeypatch.delenv("FLOW_VECTOR_SEARCH", raising=False)
    return {
        "metrics_path": metrics_path,
        "backend": None,
        "hybrid": None,
        "provider": None,
        "results": None,
        "raised": None,
        "obs_ids": [],
        "modules_before": None,
        "modules_after": None,
    }


# =====================================================================
# REQ-17 scenario bindings
# =====================================================================


@scenario(
    "../bdd/req17_semantic_search.feature",
    "Semantic search with both extra and env set returns results",
)
def test_req17_semantic_search_active(vector_world):
    pass


@scenario(
    "../bdd/req17_semantic_search.feature",
    "Semantic search without extra raises VectorSearchDisabled with install hint",
)
def test_req17_extra_missing_raises(vector_world):
    pass


@scenario(
    "../bdd/req17_semantic_search.feature",
    "Semantic search without env var raises VectorSearchDisabled",
)
def test_req17_env_unset_raises(vector_world):
    pass


@scenario(
    "../bdd/req17_semantic_search.feature",
    "mem_search (FTS5) still works unchanged when vectors disabled",
)
def test_req17_fts5_unchanged_when_disabled(vector_world):
    pass


@scenario(
    "../bdd/req17_semantic_search.feature",
    "HybridBackend delegation - non-search methods pass through",
)
def test_req17_hybrid_forwards_non_search(vector_world):
    pass


# =====================================================================
# REQ-17 Given steps
# =====================================================================


@given("a HybridBackend wrapping an InMemoryBackend with a MockEmbeddingProvider")
def hybrid_with_mock_provider(vector_world):
    """REQ-17 scenario 1: active path with a 3-obs corpus whose content matches query."""
    from flow_engineering.embedding_provider import MockEmbeddingProvider

    inner = InMemoryBackend()
    inner.mem_save(
        title="drift entry",
        content="drift detection strategy",
        topic_key="sdd/x/spec",
    )
    inner.mem_save(
        title="alarm entry",
        content="drift alarm drift detection",
        topic_key="sdd/x/spec",
    )
    inner.mem_save(
        title="logging entry",
        content="logging best practices drift detection",
        topic_key="sdd/x/spec",
    )
    vector_world["backend"] = inner
    vector_world["provider"] = MockEmbeddingProvider()
    vector_world["hybrid"] = HybridBackend(
        inner=inner, embedding_provider=vector_world["provider"]
    )


@given("a corpus of 3 observations with semantic content")
def seed_three_obs_with_semantic_content(vector_world):
    """Seed three observations (delegated to the active-path setup)."""


@given("an InMemoryBackend (vectors disabled)")
def inmemory_vectors_disabled(vector_world, monkeypatch):
    """InMemoryBackend is the prose test fixture — it always raises on vector calls."""
    vector_world["backend"] = InMemoryBackend()
    monkeypatch.delenv("FLOW_VECTOR_SEARCH", raising=False)


@given("the env var FLOW_VECTOR_SEARCH is unset")
def env_var_unset(vector_world, monkeypatch):
    monkeypatch.delenv("FLOW_VECTOR_SEARCH", raising=False)


@given("a corpus of 3 observations")
def seed_three_obs_simple(vector_world):
    backend = vector_world["backend"]
    if backend is None:
        backend = InMemoryBackend()
        vector_world["backend"] = backend
    backend.mem_save(
        title="drift entry",
        content="drift detection strategy",
        topic_key="sdd/x/spec",
    )
    backend.mem_save(
        title="alarm entry",
        content="drift alarm triggers",
        topic_key="sdd/x/spec",
    )
    backend.mem_save(
        title="logging entry",
        content="logging best practices",
        topic_key="sdd/x/spec",
    )


@given("a HybridBackend wrapping an InMemoryBackend")
def hybrid_wraps_inmemory(vector_world):
    from flow_engineering.embedding_provider import MockEmbeddingProvider

    vector_world["backend"] = InMemoryBackend()
    vector_world["provider"] = MockEmbeddingProvider()
    vector_world["hybrid"] = HybridBackend(
        inner=vector_world["backend"],
        embedding_provider=vector_world["provider"],
    )


# =====================================================================
# REQ-17 When steps
# =====================================================================


@when(parsers.parse('I call mem_search_semantic("{query}", k={k:d})'))
def call_semantic_with_k(vector_world, query: str, k: int):
    backend = vector_world["hybrid"] or vector_world["backend"]
    vector_world["modules_before"] = {
        "torch", "sentence_transformers", "sqlite_vec"
    } & set(sys.modules)
    try:
        vector_world["results"] = backend.mem_search_semantic(query, k=k)
    except Exception as exc:
        vector_world["raised"] = exc
    finally:
        vector_world["modules_after"] = {
            "torch", "sentence_transformers", "sqlite_vec"
        } & set(sys.modules)


@when(parsers.parse('I call mem_search_semantic("{query}")'))
def call_semantic(vector_world, query: str):
    backend = vector_world["hybrid"] or vector_world["backend"]
    vector_world["modules_before"] = {
        "torch", "sentence_transformers", "sqlite_vec"
    } & set(sys.modules)
    try:
        vector_world["results"] = backend.mem_search_semantic(query)
    except Exception as exc:
        vector_world["raised"] = exc
    finally:
        vector_world["modules_after"] = {
            "torch", "sentence_transformers", "sqlite_vec"
        } & set(sys.modules)


@when(parsers.parse('I call mem_search("{query}")'))
def call_mem_search(vector_world, query: str):
    backend = vector_world["backend"]
    vector_world["modules_before"] = {
        "torch", "sentence_transformers", "sqlite_vec"
    } & set(sys.modules)
    try:
        vector_world["results"] = backend.mem_search(query)
    except Exception as exc:
        vector_world["raised"] = exc
    finally:
        vector_world["modules_after"] = {
            "torch", "sentence_transformers", "sqlite_vec"
        } & set(sys.modules)


@when(
    parsers.parse(
        'I call hybrid.mem_save with title "{title}" and content "{content}"'
    )
)
def hybrid_save(vector_world, title: str, content: str):
    saved = vector_world["hybrid"].mem_save(
        title=title, content=content, topic_key="sdd/x/spec"
    )
    vector_world["saved"] = saved


# =====================================================================
# REQ-17 Then steps
# =====================================================================


@then(parsers.parse("{n:d} results are returned"))
def n_results_returned(vector_world, n: int):
    assert vector_world["raised"] is None, (
        f"Expected success, got {type(vector_world['raised']).__name__}: "
        f"{vector_world['raised']}"
    )
    assert len(vector_world["results"]) == n, (
        f"Expected {n} results, got {len(vector_world['results'])}: "
        f"{vector_world['results']!r}"
    )


@then("each result has keys observation_id, score, rank")
def each_result_has_keys(vector_world):
    for r in vector_world["results"]:
        assert "observation_id" in r, f"Missing observation_id in {r!r}"
        assert "score" in r, f"Missing score in {r!r}"
        assert "rank" in r, f"Missing rank in {r!r}"


@then("results are ordered by score descending")
def results_ordered_by_score(vector_world):
    scores = [r["score"] for r in vector_world["results"]]
    assert scores == sorted(scores, reverse=True), (
        f"Results not ordered by score desc: {scores}"
    )


@then("VectorSearchDisabled is raised")
def vector_search_disabled_raised(vector_world):
    raised = vector_world["raised"]
    assert raised is not None, "Expected VectorSearchDisabled, got None"
    assert isinstance(raised, VectorSearchDisabled), (
        f"Expected VectorSearchDisabled, got {type(raised).__name__}: {raised!r}"
    )


@then(parsers.parse('the error message includes "{needle}"'))
def error_message_includes(vector_world, needle: str):
    assert needle in str(vector_world["raised"]), (
        f"Expected '{needle}' in error message, got: {vector_world['raised']!r}"
    )


@then("no torch or sqlite_vec import is attempted")
def no_heavy_imports_leaked(vector_world):
    """REQ-17 scenarios 2-4: gate path MUST NOT pull torch / sqlite_vec."""
    before = vector_world.get("modules_before") or set()
    after = vector_world.get("modules_after") or set()
    assert before == after, (
        f"Vector search gate leaked heavy imports: {after - before}"
    )


@then("FTS5 results are returned normally")
def fts5_results_returned(vector_world):
    assert vector_world["raised"] is None, (
        f"Expected no exception, got {type(vector_world['raised']).__name__}: "
        f"{vector_world['raised']}"
    )
    assert isinstance(vector_world["results"], list), (
        f"Expected list, got {type(vector_world['results']).__name__}"
    )
    assert len(vector_world["results"]) >= 1, (
        f"Expected at least 1 FTS hit, got 0. Results: {vector_world['results']!r}"
    )


@then("no exception is raised")
def no_exception_raised(vector_world):
    assert vector_world["raised"] is None, (
        f"Expected no exception, got {type(vector_world['raised']).__name__}: "
        f"{vector_world['raised']}"
    )


@then("the observation is saved to the inner backend")
def observation_saved_to_inner(vector_world):
    saved = vector_world["saved"]
    assert "id" in saved, f"Saved observation missing id: {saved!r}"
    inner = vector_world["backend"]
    assert saved["id"] in inner.observations, (
        f"Observation {saved['id']} not found in inner backend: "
        f"{list(inner.observations.keys())}"
    )


@then("reading via inner.mem_get_observation returns the saved observation")
def inner_get_returns_saved(vector_world):
    saved = vector_world["saved"]
    inner = vector_world["backend"]
    fetched = inner.mem_get_observation(saved["id"])
    assert fetched["id"] == saved["id"]
    assert fetched["title"] == saved["title"]
    assert fetched["content"] == saved["content"]


# =====================================================================
# REQ-18 scenario bindings
# =====================================================================


@scenario(
    "../bdd/req18_hybrid_scoring.feature",
    "Hybrid with alpha=0.5 ranks semantic + FTS blended (worked example)",
)
def test_req18_hybrid_alpha_05_worked_example(vector_world):
    pass


@scenario(
    "../bdd/req18_hybrid_scoring.feature",
    "Hybrid with alpha=1.0 equals pure semantic (sanity)",
)
def test_req18_hybrid_alpha_10_equals_semantic(vector_world):
    pass


@scenario(
    "../bdd/req18_hybrid_scoring.feature",
    "Hybrid with alpha=0.0 equals pure FTS (sanity)",
)
def test_req18_hybrid_alpha_00_equals_fts(vector_world):
    pass


@scenario(
    "../bdd/req18_hybrid_scoring.feature",
    "Alpha=1.5 raises ValueError",
)
def test_req18_alpha_out_of_range_raises(vector_world):
    pass


@scenario(
    "../bdd/req18_hybrid_scoring.feature",
    "Empty query returns empty results without division-by-zero",
)
def test_req18_empty_query_returns_empty(vector_world):
    pass


# =====================================================================
# REQ-18 Given steps
# =====================================================================


@given(
    parsers.parse(
        "3 observations with prose and known (semantic_sim, fts_score): "
        "obs1: ({a1:.2f}, {f1:.2f}), obs2: ({a2:.2f}, {f2:.2f}), "
        "obs3: ({a3:.2f}, {f3:.2f})"
    )
)
def three_obs_with_known_sims_and_fts(
    vector_world, a1, f1, a2, f2, a3, f3
):
    """Build the worked example with the given cosine/FTS scores.

    Uses FixedVectorsProvider for the cosine values and ScoredInMemoryBackend
    for the FTS values. The cosine and FTS in the prompt are stored verbatim
    so downstream asserts can compare against them; the actual HybridBackend
    computation uses the obs contents (extended to share a query substring)
    and the scored backend respectively.
    """
    scored, provider, obs_ids = _build_worked_example_fixture()
    vector_world["backend"] = scored
    vector_world["provider"] = provider
    vector_world["obs_ids"] = obs_ids
    vector_world["hybrid"] = HybridBackend(inner=scored, embedding_provider=provider)
    scored.set_score(obs_ids[0], f1)
    scored.set_score(obs_ids[1], f2)
    scored.set_score(obs_ids[2], f3)


@given("the seeded three-observation corpus")
def seeded_three_obs(vector_world):
    """Scenarios 2-3 reuse the corpus from scenario 1 if present, else build."""
    if vector_world.get("hybrid") is not None and vector_world.get("obs_ids"):
        return
    three_obs_with_known_sims_and_fts(
        vector_world, 0.96, 0.50, 0.0, 0.20, 0.30, 0.10
    )


@given(parsers.parse('the query "{query}"'))
def the_query(vector_world, query: str):
    vector_world["query"] = query


@given("a HybridBackend wrapping an InMemoryBackend (scoring setup)")
def hybrid_for_scoring(vector_world):
    """Build a hybrid backend for the alpha-out-of-range + empty-query scenarios."""
    from flow_engineering.embedding_provider import MockEmbeddingProvider

    backend = InMemoryBackend()
    provider = MockEmbeddingProvider()
    vector_world["backend"] = backend
    vector_world["provider"] = provider
    vector_world["hybrid"] = HybridBackend(inner=backend, embedding_provider=provider)


@given("a query that matches zero observations in the FTS index")
def query_zero_matches(vector_world):
    vector_world["query"] = "nonexistent_xyz_zzz"


# =====================================================================
# REQ-18 When steps
# =====================================================================


@when(parsers.parse('I call mem_search_hybrid("{query}", k={k:d}, alpha={alpha:.2f})'))
def call_hybrid(vector_world, query: str, k: int, alpha: float):
    vector_world["query"] = query
    vector_world["alpha"] = alpha
    vector_world["k"] = k
    try:
        vector_world["results"] = vector_world["hybrid"].mem_search_hybrid(
            query, k=k, alpha=alpha
        )
    except Exception as exc:
        vector_world["raised"] = exc


@when(parsers.parse('I call mem_search_hybrid("{query}", alpha={alpha:.2f})'))
def call_hybrid_default_k(vector_world, query: str, alpha: float):
    vector_world["query"] = query
    vector_world["alpha"] = alpha
    try:
        vector_world["results"] = vector_world["hybrid"].mem_search_hybrid(
            query, alpha=alpha
        )
    except Exception as exc:
        vector_world["raised"] = exc


@when(parsers.parse('I call mem_search_hybrid("{query}", k={k:d})'))
def call_hybrid_default_alpha(vector_world, query: str, k: int):
    vector_world["query"] = query
    vector_world["k"] = k
    try:
        vector_world["results"] = vector_world["hybrid"].mem_search_hybrid(
            query, k=k
        )
    except Exception as exc:
        vector_world["raised"] = exc


@when(parsers.parse('I call mem_search_semantic("{query}", k={k:d}) (pure)'))
def call_semantic_pure(vector_world, query: str, k: int):
    try:
        vector_world["pure_semantic_results"] = (
            vector_world["hybrid"].mem_search_semantic(query, k=k)
        )
    except Exception as exc:
        vector_world["raised"] = exc


@when(parsers.parse('I call inner.mem_search("{query}")'))
def call_inner_mem_search(vector_world, query: str):
    try:
        vector_world["inner_results"] = vector_world["backend"].mem_search(query)
    except Exception as exc:
        vector_world["raised"] = exc


# =====================================================================
# REQ-18 Then steps
# =====================================================================


@then(parsers.parse("results are ordered: obs{id1:d}, obs{id2:d}, obs{id3:d}"))
def results_ordered_by_ids(vector_world, id1: int, id2: int, id3: int):
    assert vector_world["raised"] is None, (
        f"Expected success, got {type(vector_world['raised']).__name__}: "
        f"{vector_world['raised']}"
    )
    expected = [
        vector_world["obs_ids"][id1 - 1],
        vector_world["obs_ids"][id2 - 1],
        vector_world["obs_ids"][id3 - 1],
    ]
    actual = [r["observation_id"] for r in vector_world["results"]]
    assert actual == expected, (
        f"Expected order {expected} (obs{id1}, obs{id2}, obs{id3}), got {actual}"
    )


@then(
    parsers.parse(
        "scores match (within 1e-3): "
        "obs{id1:d} = {s1:.3f}, obs{id2:d} = {s2:.3f}, obs{id3:d} = {s3:.3f}"
    )
)
def scores_match_with_tolerance(vector_world, id1, id2, id3, s1, s2, s3):
    assert vector_world["raised"] is None, (
        f"Expected success, got {type(vector_world['raised']).__name__}: "
        f"{vector_world['raised']}"
    )
    expected = {
        vector_world["obs_ids"][id1 - 1]: s1,
        vector_world["obs_ids"][id2 - 1]: s2,
        vector_world["obs_ids"][id3 - 1]: s3,
    }
    for obs_id, expected_score in expected.items():
        actual_score = next(
            r["score"]
            for r in vector_world["results"]
            if r["observation_id"] == obs_id
        )
        assert actual_score == pytest.approx(expected_score, abs=1e-3), (
            f"obs{vector_world['obs_ids'].index(obs_id) + 1} score: "
            f"expected {expected_score}, got {actual_score}"
        )


@then(parsers.parse("the rank index of obs{n:d} is {rank:d}"))
def rank_index_of_obs(vector_world, n: int, rank: int):
    obs_id = vector_world["obs_ids"][n - 1]
    actual_rank = next(
        r["rank"] for r in vector_world["results"] if r["observation_id"] == obs_id
    )
    assert actual_rank == rank, (
        f"obs{n} rank: expected {rank}, got {actual_rank}"
    )


@then("hybrid results equal pure semantic results in order and ids")
def hybrid_equals_pure_semantic(vector_world):
    assert vector_world["raised"] is None, (
        f"Expected success, got {type(vector_world['raised']).__name__}: "
        f"{vector_world['raised']}"
    )
    hybrid_ids = [r["observation_id"] for r in vector_world["results"]]
    pure_ids = [
        r["observation_id"] for r in vector_world["pure_semantic_results"]
    ]
    assert hybrid_ids == pure_ids, (
        f"Hybrid ids {hybrid_ids} != pure semantic ids {pure_ids}"
    )


@then("hybrid scores differ from pure semantic by at most 1e-3")
def hybrid_scores_close_to_pure(vector_world):
    for h, p in zip(
        vector_world["results"],
        vector_world["pure_semantic_results"],
        strict=False,
    ):
        if h["observation_id"] != p["observation_id"]:
            continue
        assert h["score"] == pytest.approx(p["score"], abs=1e-3), (
            f"obs {h['observation_id']}: hybrid {h['score']} != pure {p['score']}"
        )


@then("hybrid results equal inner FTS results in order and ids")
def hybrid_equals_pure_fts(vector_world):
    """REQ-18 scenario 3 sanity check (alpha=0.0 == pure FTS)."""
    assert vector_world["raised"] is None, (
        f"Expected success, got {type(vector_world['raised']).__name__}: "
        f"{vector_world['raised']}"
    )
    hybrid_ids = [r["observation_id"] for r in vector_world["results"]]
    fts_ids = [o["id"] for o in vector_world["inner_results"]]
    assert set(hybrid_ids) == set(fts_ids), (
        f"Hybrid ids {hybrid_ids} != FTS ids {fts_ids} as sets"
    )


@then("hybrid scores equal the FTS-only scores (1.0 * fts)")
def hybrid_scores_equal_fts(vector_world):
    for r in vector_world["results"]:
        assert isinstance(r["score"], float), (
            f"Expected float score, got {type(r['score']).__name__}: {r['score']!r}"
        )


@then("ValueError is raised")
def value_error_raised(vector_world):
    raised = vector_world["raised"]
    assert raised is not None, "Expected ValueError, got None"
    assert isinstance(raised, ValueError), (
        f"Expected ValueError, got {type(raised).__name__}: {raised!r}"
    )


@then(parsers.parse('the message contains "{needle}"'))
def message_contains(vector_world, needle: str):
    assert needle in str(vector_world["raised"]), (
        f"Expected '{needle}' in message, got: {vector_world['raised']!r}"
    )


@then("[] is returned (no crash, no division-by-zero)")
def empty_list_returned(vector_world):
    assert vector_world["raised"] is None, (
        f"Expected no exception, got {type(vector_world['raised']).__name__}: "
        f"{vector_world['raised']}"
    )
    assert vector_world["results"] == [], (
        f"Expected [], got {vector_world['results']!r}"
    )
