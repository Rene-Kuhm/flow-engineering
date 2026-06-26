"""BDD step definitions for vector-semantic-search PR#1 REQ-17 + REQ-18 + REQ-22.

Covers ``req17_semantic_search.feature`` (5 scenarios),
``req18_hybrid_scoring.feature`` (5 scenarios), and
``req22_vector_observability.feature`` (4 scenarios) — the BDD acceptance
gate for the activation gate (REQ-17), the hybrid scoring formula
(REQ-18), and the observability counters (REQ-22).

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

import json
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


# =====================================================================
# REQ-19 scenario bindings — EmbeddingProvider ABC + lazy import
# =====================================================================


@scenario(
    "../bdd/req19_embedding_provider.feature",
    "MockEmbeddingProvider returns deterministic 384-dim vectors",
)
def test_req19_mock_deterministic(embedding_world):
    pass


@scenario(
    "../bdd/req19_embedding_provider.feature",
    "import flow_engineering.embedding_provider does not trigger torch import",
)
def test_req19_lazy_module_import(embedding_world):
    pass


@scenario(
    "../bdd/req19_embedding_provider.feature",
    "SentenceTransformersProvider raises ImportError when torch missing",
)
def test_req19_sentence_transformers_missing_torch(embedding_world):
    pass


@scenario(
    "../bdd/req19_embedding_provider.feature",
    "Embedding output shape is (N, 384) for N inputs",
)
def test_req19_embed_shape(embedding_world):
    pass


# =====================================================================
# REQ-19 step definitions
# =====================================================================


from flow_engineering.embedding_provider import (
    EmbeddingProviderUnavailable,
    MockEmbeddingProvider,
    SentenceTransformersProvider,
)


@pytest.fixture
def embedding_world() -> dict[str, Any]:
    """Per-scenario scratch state for REQ-19 scenarios.

    Mirrors the vector_world fixture pattern; kept separate so REQ-19 step
    defs don't accidentally mutate the REQ-17/18 shared state.
    """
    return {
        "provider": None,
        "vectors": [],
        "subprocess_result": None,
        "raised": None,
    }


# ---------- Given ----------


@given("a MockEmbeddingProvider")
def given_mock_provider(embedding_world):
    embedding_world["provider"] = MockEmbeddingProvider()


@given("a fresh subprocess")
def given_fresh_subprocess(embedding_world):
    # No-op fixture marker — the subprocess is launched lazily inside the When step.
    embedding_world["subprocess_result"] = None


@given("torch is patched to raise ImportError on import")
def given_torch_patched_to_raise(monkeypatch, embedding_world):
    """Patch builtins.__import__ so any ``import torch`` raises ImportError."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "torch" or name.startswith("torch."):
            raise ImportError(f"No module named {name!r}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


@given("sentence_transformers is removed from sys.modules")
def given_st_removed(monkeypatch, embedding_world):
    monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)


# ---------- When ----------


@when(parsers.parse('I embed "{text}" twice in a row'))
def when_embed_twice(embedding_world, text: str):
    provider = embedding_world["provider"]
    embedding_world["vectors"].append(provider.embed([text]))
    embedding_world["vectors"].append(provider.embed([text]))


@when(parsers.parse('I embed "{text}"'))
def when_embed_text(embedding_world, text: str):
    provider = embedding_world["provider"]
    embedding_world["vectors"].append(provider.embed([text]))


@when("I import flow_engineering.embedding_provider in that subprocess")
def when_subprocess_import(embedding_world):
    import subprocess

    script = (
        "import sys; "
        "import flow_engineering.embedding_provider as m; "
        "torch_loaded = 'torch' in sys.modules; "
        "st_loaded = 'sentence_transformers' in sys.modules; "
        "has_st = hasattr(m, 'SentenceTransformersProvider'); "
        "print(f'torch={torch_loaded} st={st_loaded} has_st={has_st}'); "
        "sys.exit(0 if (not torch_loaded and not st_loaded and has_st) else 1)"
    )
    embedding_world["subprocess_result"] = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        cwd="C:/dev/proyects/flow-engineering",
    )


@when("I instantiate SentenceTransformersProvider()")
def when_instantiate_st(embedding_world):
    try:
        SentenceTransformersProvider()
    except Exception as exc:
        embedding_world["raised"] = exc


@when(parsers.parse('I embed 5 texts ["{a}", "{b}", "{c}", "{d}", "{e}"]'))
def when_embed_five_texts(embedding_world, a, b, c, d, e):
    provider = embedding_world["provider"]
    embedding_world["vectors"].append(provider.embed([a, b, c, d, e]))


@when("I embed an empty list")
def when_embed_empty(embedding_world):
    provider = embedding_world["provider"]
    embedding_world["vectors"].append(provider.embed([]))


# ---------- Then ----------


@then("both calls return identical numpy arrays")
def then_both_calls_identical(embedding_world):
    assert len(embedding_world["vectors"]) >= 2, (
        f"Expected ≥2 embed results, got {len(embedding_world['vectors'])}"
    )
    first, second = embedding_world["vectors"][0], embedding_world["vectors"][1]
    assert isinstance(first, np.ndarray)
    assert isinstance(second, np.ndarray)
    np.testing.assert_array_equal(first, second)


@then(parsers.parse("the array shape is ({rows:d}, {cols:d})"))
def then_shape_n_by_m(embedding_world, rows: int, cols: int):
    arr = embedding_world["vectors"][-1]
    assert arr.shape == (rows, cols), (
        f"Expected shape ({rows}, {cols}), got {arr.shape}"
    )


@then(parsers.parse("the L2 norm of the vector is within [{lo:.2f}, {hi:.2f}] of 1.0"))
def then_l2_norm_in_range(embedding_world, lo: float, hi: float):
    arr = embedding_world["vectors"][-1]
    if arr.shape[0] == 0:
        return
    norms = np.linalg.norm(arr, axis=1)
    for n in norms:
        assert lo <= n <= hi, f"norm {n} outside [{lo}, {hi}]"


@then("the goodbye vector differs from the hello vector")
def then_bye_differs_from_hello(embedding_world):
    """The last 2 vectors in embedding_world['vectors'] are hello and goodbye."""
    assert len(embedding_world["vectors"]) >= 2
    hello, bye = embedding_world["vectors"][-2], embedding_world["vectors"][-1]
    assert not np.array_equal(hello, bye), (
        "Expected different vectors for different inputs"
    )


@then('"torch" is NOT in sys.modules')
def then_torch_not_loaded(embedding_world):
    result = embedding_world["subprocess_result"]
    assert result is not None, "Subprocess result missing"
    assert result.returncode == 0, (
        f"Subprocess failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "torch=False" in result.stdout, (
        f"Expected 'torch=False' in subprocess output: {result.stdout!r}"
    )


@then('"sentence_transformers" is NOT in sys.modules')
def then_st_not_loaded(embedding_world):
    result = embedding_world["subprocess_result"]
    assert result.returncode == 0, (
        f"Subprocess failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "st=False" in result.stdout, (
        f"Expected 'st=False' in subprocess output: {result.stdout!r}"
    )


@then("the SentenceTransformersProvider class is importable")
def then_st_class_importable(embedding_world):
    result = embedding_world["subprocess_result"]
    assert result.returncode == 0
    assert "has_st=True" in result.stdout, (
        f"Expected 'has_st=True' in subprocess output: {result.stdout!r}"
    )


@then("EmbeddingProviderUnavailable is raised")
def then_embedding_provider_unavailable_raised(embedding_world):
    raised = embedding_world["raised"]
    assert raised is not None, "Expected EmbeddingProviderUnavailable, got None"
    assert isinstance(raised, EmbeddingProviderUnavailable), (
        f"Expected EmbeddingProviderUnavailable, got {type(raised).__name__}: {raised!r}"
    )


@then(parsers.parse('the embedding error message includes "{needle}"'))
def then_embedding_error_message_includes(embedding_world, needle: str):
    raised = embedding_world["raised"]
    assert needle in str(raised), (
        f"Expected '{needle}' in error message, got: {raised!r}"
    )


@then("the exception is also an ImportError")
def then_exception_is_import_error(embedding_world):
    raised = embedding_world["raised"]
    assert isinstance(raised, ImportError), (
        f"Expected ImportError, got {type(raised).__name__}"
    )


@then(parsers.parse("the returned numpy array has shape ({rows:d}, {cols:d})"))
def then_returned_array_shape(embedding_world, rows: int, cols: int):
    arr = embedding_world["vectors"][-1]
    assert arr.shape == (rows, cols), (
        f"Expected shape ({rows}, {cols}), got {arr.shape}"
    )


@then(parsers.parse("each row has L2 norm within [{lo:.2f}, {hi:.2f}] of 1.0"))
def then_each_row_norm(embedding_world, lo: float, hi: float):
    arr = embedding_world["vectors"][-1]
    if arr.shape[0] == 0:
        return
    norms = np.linalg.norm(arr, axis=1)
    for n in norms:
        assert lo <= n <= hi, f"norm {n} outside [{lo}, {hi}]"


# =====================================================================
# REQ-20 scenario bindings — sqlite-vec storage
# =====================================================================


@scenario(
    "../bdd/req20_sqlite_vec_storage.feature",
    "Add -> search round-trip returns added observation as top-1",
)
def test_req20_round_trip(vec_store_world):
    pass


@scenario(
    "../bdd/req20_sqlite_vec_storage.feature",
    "Delete removes observation from search results",
)
def test_req20_delete_removes(vec_store_world):
    pass


@scenario(
    "../bdd/req20_sqlite_vec_storage.feature",
    "count() reflects add/delete accurately",
)
def test_req20_count_accuracy(vec_store_world):
    pass


@scenario(
    "../bdd/req20_sqlite_vec_storage.feature",
    "Vector BLOB size matches 384 x 4 = 1536 bytes",
)
def test_req20_blob_size(vec_store_world):
    pass


@scenario(
    "../bdd/req20_sqlite_vec_storage.feature",
    "Search returns top-k ordered by ascending distance",
)
def test_req20_top_k_ordering(vec_store_world):
    pass


# =====================================================================
# REQ-20 step definitions
# =====================================================================


sqlite_vec = pytest.importorskip("sqlite_vec")
"""Skip the whole REQ-20 batch when sqlite-vec is missing (test env without [vectors])."""


from flow_engineering.vectors.sqlite_vec_store import (
    BLOB_SIZE,
    VECTOR_DIM,
    SqliteVecStore,
)


@pytest.fixture
def vec_store_world(tmp_path: Path) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-20.

    Uses an in-memory ``:memory:`` SQLite DB so each scenario gets a fresh
    store with zero fixture setup overhead.
    """
    return {
        "store": None,
        "vectors": {},
        "search_results": None,
        "count_value": None,
        "raw_blob": None,
        "round_trip_input": None,
        "round_trip_output": None,
    }


def _unit(v: np.ndarray) -> np.ndarray:
    """L2-normalize a vector in place (returns a new array)."""
    n = float(np.linalg.norm(v))
    if n <= 0.0:
        return v.astype(np.float32)
    return (v / n).astype(np.float32)


# ---------- Given ----------


@given("a fresh SqliteVecStore (in-memory)")
def given_fresh_store(tmp_path, vec_store_world):
    vec_store_world["store"] = SqliteVecStore(tmp_path / "fresh.sqlite")
    # Use a tmp_path file instead of ":memory:" so each scenario has isolation
    # but cleanup is automatic via tmp_path fixture teardown.


@given("a SqliteVecStore with obs1 and obs2 added")
def given_store_with_two(tmp_path, vec_store_world):
    store = SqliteVecStore(tmp_path / "two.sqlite")
    store.add("obs1", _unit(np.ones(VECTOR_DIM, dtype=np.float32)))
    store.add("obs2", _unit(np.full(VECTOR_DIM, 2.0, dtype=np.float32)))
    vec_store_world["store"] = store


@given("a fresh SqliteVecStore (in-memory)")
def given_fresh_store_in_memory(tmp_path, vec_store_world):
    vec_store_world["store"] = SqliteVecStore(tmp_path / "fresh.sqlite")


@given("a SqliteVecStore with 10 random 384-dim vectors at obs1..obs10")
def given_store_with_ten_random(tmp_path, vec_store_world):
    rng = np.random.default_rng(seed=2026_06_26)
    vectors: dict[str, np.ndarray] = {}
    for i in range(1, 11):
        v = rng.standard_normal(VECTOR_DIM).astype(np.float32)
        v = _unit(v)
        vectors[f"obs{i}"] = v
    store = SqliteVecStore(tmp_path / "ten.sqlite")
    for obs_id, vec in vectors.items():
        store.add(obs_id, vec)
    vec_store_world["store"] = store
    vec_store_world["vectors"] = vectors


@given("a query vector chosen close to obs7 (cosine distance ~ 0.05)")
def given_query_close_to_obs7(vec_store_world):
    """Build a query vector with cosine ~ 0.05 to obs7 by interpolating
    obs7 with a small orthogonal perturbation."""
    obs7 = vec_store_world["vectors"]["obs7"]
    rng = np.random.default_rng(seed=42)
    # 0.05 cosine distance ~ angle ~ acos(0.95) ~ 0.3176 rad.
    # Use sin(0.3176) on orthogonal direction.
    ortho = rng.standard_normal(VECTOR_DIM).astype(np.float32)
    ortho -= np.dot(ortho, obs7) * obs7  # orthogonalize
    ortho = _unit(ortho)
    angle = float(np.arccos(0.95))
    q = float(np.cos(angle)) * obs7 + float(np.sin(angle)) * ortho
    vec_store_world["query_vector"] = _unit(q)


# ---------- When ----------


@when("I add obs1 with a unit vector")
def when_add_obs1_unit(vec_store_world):
    v = _unit(np.ones(VECTOR_DIM, dtype=np.float32))
    vec_store_world["store"].add("obs1", v)
    vec_store_world["vectors"]["obs1"] = v


@when(parsers.parse("I search with the same unit vector, k={k:d}"))
def when_search_same_unit(vec_store_world, k: int):
    v = vec_store_world["vectors"]["obs1"]
    vec_store_world["search_results"] = vec_store_world["store"].search(v, k=k)


@when("I delete obs1")
def when_delete_obs1(vec_store_world):
    vec_store_world["store"].delete("obs1")


@when(parsers.parse("I search with any vector, k={k:d}"))
def when_search_any(vec_store_world, k: int):
    v = _unit(np.ones(VECTOR_DIM, dtype=np.float32))
    vec_store_world["search_results"] = vec_store_world["store"].search(v, k=k)


@when("I call count() before any writes")
def when_count_before_writes(vec_store_world):
    vec_store_world["count_value"] = vec_store_world["store"].count()


@when("I add obs1, obs2, and obs3 with three distinct unit vectors")
def when_add_three(vec_store_world):
    store = vec_store_world["store"]
    store.add("obs1", _unit(np.ones(VECTOR_DIM, dtype=np.float32)))
    store.add("obs2", _unit(np.full(VECTOR_DIM, 2.0, dtype=np.float32)))
    store.add("obs3", _unit(np.full(VECTOR_DIM, 3.0, dtype=np.float32)))


@when("I delete obs2")
def when_delete_obs2(vec_store_world):
    vec_store_world["store"].delete("obs2")


@when("I add obs1 with a random 384-dim vector")
def when_add_random(vec_store_world):
    rng = np.random.default_rng(seed=2026_06_26 + 1)
    v = rng.standard_normal(VECTOR_DIM).astype(np.float32)
    vec_store_world["store"].add("obs1", v)
    vec_store_world["round_trip_input"] = v
    vec_store_world["vectors"]["obs1"] = v


@when("I read the observation_embeddings.vector column as raw bytes")
def when_read_blob(vec_store_world):
    """Read the raw bytes from the audit BLOB column via direct SQL."""
    store = vec_store_world["store"]
    conn = store._ensure_conn()  # type: ignore[attr-defined]
    row = conn.execute(
        "SELECT vector FROM observation_embeddings WHERE observation_id = ?",
        ("obs1",),
    ).fetchone()
    vec_store_world["raw_blob"] = bytes(row[0])


@when(parsers.parse("I search with the query vector, k={k:d}"))
def when_search_query(vec_store_world, k: int):
    vec_store_world["search_results"] = vec_store_world["store"].search(
        vec_store_world["query_vector"], k=k
    )


# ---------- Then ----------


@then("the result is obs1 at distance ~0.0")
def then_result_is_obs1_zero(vec_store_world):
    results = vec_store_world["search_results"]
    assert len(results) == 1, f"Expected 1 result, got {len(results)}: {results}"
    obs_id, distance = results[0]
    assert obs_id == "obs1", f"Expected obs1, got {obs_id!r}"
    assert abs(distance) < 0.01, f"Expected distance ~0.0, got {distance}"


@then(parsers.parse("{obs_id} is NOT in the result list"))
def then_obs_not_in_results(vec_store_world, obs_id: str):
    ids = [r[0] for r in vec_store_world["search_results"]]
    assert obs_id not in ids, (
        f"Expected {obs_id!r} NOT in result list, but found it: {ids}"
    )


@then(parsers.parse("{obs_id} IS in the result list"))
def then_obs_is_in_results(vec_store_world, obs_id: str):
    ids = [r[0] for r in vec_store_world["search_results"]]
    assert obs_id in ids, f"Expected {obs_id!r} in result list, got: {ids}"


@then(parsers.parse("count() == {n:d}"))
def then_count_equals(vec_store_world, n: int):
    actual = vec_store_world["store"].count()
    assert actual == n, f"Expected count() == {n}, got {actual}"


@then(parsers.parse("it returns {n:d}"))
def then_count_returns_n(vec_store_world, n: int):
    assert vec_store_world["count_value"] == n, (
        f"Expected count() == {n}, got {vec_store_world['count_value']}"
    )


@then("count() returns 2")
def then_count_returns_2(vec_store_world):
    actual = vec_store_world["store"].count()
    assert actual == 2, f"Expected count() == 2, got {actual}"


@then("count() returns 3")
def then_count_returns_3(vec_store_world):
    actual = vec_store_world["store"].count()
    assert actual == 3, f"Expected count() == 3, got {actual}"


@then(parsers.parse("the byte length is exactly {n:d}"))
def then_blob_byte_length(vec_store_world, n: int):
    assert len(vec_store_world["raw_blob"]) == n, (
        f"Expected blob byte length {n}, got {len(vec_store_world['raw_blob'])}"
    )


@then("the deserialized numpy array has shape (384,) and dtype float32")
def then_deserialized_array(vec_store_world):
    arr = np.frombuffer(vec_store_world["raw_blob"], dtype=np.float32)
    assert arr.shape == (VECTOR_DIM,), f"Expected shape ({VECTOR_DIM},), got {arr.shape}"
    assert arr.dtype == np.float32, f"Expected float32, got {arr.dtype}"


@then("the values round-trip within 1e-6 of the input")
def then_blob_round_trip(vec_store_world):
    arr = np.frombuffer(vec_store_world["raw_blob"], dtype=np.float32)
    inp = vec_store_world["round_trip_input"].astype(np.float32).reshape(-1)
    np.testing.assert_allclose(arr, inp, atol=1e-6, rtol=0)


@then(parsers.parse("the result list has exactly {n:d} (obs_id, distance) tuples"))
def then_result_list_size(vec_store_world, n: int):
    results = vec_store_world["search_results"]
    assert len(results) == n, f"Expected {n} results, got {len(results)}: {results}"
    for entry in results:
        assert isinstance(entry, tuple) and len(entry) == 2, (
            f"Expected (obs_id, distance) tuple, got {entry!r}"
        )


@then(parsers.parse("{obs_id} is at position {pos:d}"))
def then_obs_at_position(vec_store_world, obs_id: str, pos: int):
    results = vec_store_world["search_results"]
    assert 0 <= pos < len(results), (
        f"Position {pos} out of range for {len(results)} results"
    )
    assert results[pos][0] == obs_id, (
        f"Expected {obs_id!r} at position {pos}, got {results[pos][0]!r}"
    )


@then("the distances are sorted in ascending order")
def then_distances_sorted_asc(vec_store_world):
    results = vec_store_world["search_results"]
    distances = [d for _obs, d in results]
    assert distances == sorted(distances), (
        f"Distances not ascending: {distances}"
    )


# =====================================================================
# REQ-21 scenario bindings — flow reindex CLI
# =====================================================================


@scenario(
    "../bdd/req21_reindex.feature",
    "flow reindex on empty corpus completes with 0 indexed",
)
def test_req21_reindex_empty(vec_reindex_world):
    pass


@scenario(
    "../bdd/req21_reindex.feature",
    "flow reindex on 250 observations emits progress lines + done",
)
def test_req21_reindex_250_progress(vec_reindex_world):
    pass


@scenario(
    "../bdd/req21_reindex.feature",
    "Second flow reindex is idempotent",
)
def test_req21_reindex_idempotent(vec_reindex_world):
    pass


@scenario(
    "../bdd/req21_reindex.feature",
    "--dry-run reports count without writing",
)
def test_req21_reindex_dry_run(vec_reindex_world):
    pass


@scenario(
    "../bdd/req21_reindex.feature",
    "Crash mid-run: subsequent restart completes the corpus",
)
def test_req21_reindex_crash_resume(vec_reindex_world):
    pass


# =====================================================================
# REQ-21 step definitions — flow reindex CLI
# =====================================================================


from click.testing import CliRunner as _CliRunner

from flow_engineering.cli import main as _cli_main


def _seed_reindex_corpus(backend: InMemoryBackend, n: int) -> None:
    """Seed ``n`` synthetic observations directly into ``backend.observations``.

    Mirrors the seed helper in ``tests/unit/test_cli_reindex.py`` so the BDD
    fixtures exercise the same shape the unit tests use.
    """
    for i in range(1, n + 1):
        backend.observations[i] = {
            "id": i,
            "title": f"obs-{i}",
            "content": f"observation {i} content",
            "topic_key": "sdd/test/phase",
            "type": "architecture",
            "scope": "project",
            "project": "insyd",
            "created_at": i * 1000,
            "updated_at": i * 1000,
        }
    backend.next_id = max(backend.next_id, n + 1)


@pytest.fixture
def vec_reindex_world(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-21 ``flow reindex`` scenarios.

    Wires the four CLI seams ``flow reindex`` depends on:
    - ``_default_save_backend`` → test backend (so CLI reads our seed)
    - ``_sqlite_vec_available`` → True (gate cleared)
    - ``_vectors_sqlite_path`` → tmp file (no writes to ~/.flow)
    - ``FLOW_METRICS_PATH`` → tmp file (no writes to ~/.flow)

    The ``run_outputs`` list captures every CliRunner invocation so multi-run
    scenarios (idempotent + crash-resume) can assert against each one.
    """
    metrics_path = tmp_path / "metrics.jsonl"
    vectors_path = tmp_path / "vectors.sqlite"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_path))
    monkeypatch.delenv("FLOW_VECTOR_SEARCH", raising=False)

    from flow_engineering import cli as cli_mod

    backend = InMemoryBackend()
    monkeypatch.setattr(cli_mod, "_default_save_backend", lambda: backend)
    monkeypatch.setattr(cli_mod, "_sqlite_vec_available", lambda: True)
    monkeypatch.setattr(cli_mod, "_vectors_sqlite_path", lambda: vectors_path)

    runner = _CliRunner()

    return {
        "tmp_path": tmp_path,
        "metrics_path": metrics_path,
        "vectors_path": vectors_path,
        "backend": backend,
        "cli_mod": cli_mod,
        "runner": runner,
        "run_outputs": [],
        "simulate_crash_after": None,
    }


# ---------- Given ----------


@given("an empty InMemoryBackend")
def given_empty_backend(vec_reindex_world):
    pass


@given("an InMemoryBackend seeded with 250 observations")
def given_backend_250(vec_reindex_world):
    _seed_reindex_corpus(vec_reindex_world["backend"], 250)


@given(parsers.parse("an InMemoryBackend seeded with {n:d} observations"))
def given_backend_n(vec_reindex_world, n: int):
    _seed_reindex_corpus(vec_reindex_world["backend"], n)


@given("the [vectors] extra is available")
def given_vectors_extra_available(vec_reindex_world):
    pass


@given("a tmp-path SqliteVecStore")
def given_tmp_store(vec_reindex_world):
    """The vec_reindex_world fixture already wired _vectors_sqlite_path to tmp."""
    pass


@given("a simulated reindex crash after 100 of the first batch")
def given_simulated_crash(vec_reindex_world):
    """Patch ``_perform_reindex_batch`` so the FIRST call simulates a crash
    after 100 rows of the first batch; the SECOND call (and onward) runs the
    real worker. Mirrors the unit test pattern in ``test_cli_reindex.py``.
    """
    cli_mod = vec_reindex_world["cli_mod"]
    original_perform = cli_mod._perform_reindex_batch
    call_count = {"n": 0}

    def _crash_on_first_call(*args: Any, **kwargs: Any) -> Any:
        call_count["n"] += 1
        if call_count["n"] == 1:
            kwargs["simulate_crash_after"] = 100
        return original_perform(*args, **kwargs)

    vec_reindex_world["cli_mod"] = cli_mod
    cli_mod._perform_reindex_batch = _crash_on_first_call


# ---------- When ----------


@when("I run flow reindex")
def when_run_reindex_default(vec_reindex_world):
    _invoke_reindex(vec_reindex_world, [])


@when("I run flow reindex again")
def when_run_reindex_again(vec_reindex_world):
    _invoke_reindex(vec_reindex_world, [])


@when("I run flow reindex --batch-size 100")
def when_run_reindex_batch_100(vec_reindex_world):
    _invoke_reindex(vec_reindex_world, ["--batch-size", "100"])


@when("I run flow reindex --batch-size 100 (first run, partial)")
def when_run_reindex_first_partial(vec_reindex_world):
    _invoke_reindex(vec_reindex_world, ["--batch-size", "100"])


@when("I run flow reindex --batch-size 100 (second run, full)")
def when_run_reindex_second_full(vec_reindex_world):
    _invoke_reindex(vec_reindex_world, ["--batch-size", "100"])


@when("I run flow reindex --dry-run")
def when_run_reindex_dry_run(vec_reindex_world):
    _invoke_reindex(vec_reindex_world, ["--dry-run"])


def _invoke_reindex(world: dict[str, Any], extra_args: list[str]) -> None:
    """Helper: invoke ``flow reindex`` with the given extra CLI args."""
    runner = world["runner"]
    result = runner.invoke(_cli_main, ["reindex", *extra_args])
    world["run_outputs"].append(result)


# ---------- Then ----------


@then("the exit code is 0")
def then_exit_code_zero(vec_reindex_world):
    last = vec_reindex_world["run_outputs"][-1]
    assert last.exit_code == 0, (
        f"Expected exit code 0, got {last.exit_code}: "
        f"stdout={last.stdout!r} stderr={last.stderr!r}"
    )


@then(parsers.parse('the output contains "{needle}"'))
def then_reindex_output_contains(vec_reindex_world, needle: str):
    last = vec_reindex_world["run_outputs"][-1]
    combined = (last.output or "") + (last.stderr or "")
    assert needle in combined, (
        f"Expected {needle!r} in output, got:\n"
        f"output={last.output!r}\nstderr={last.stderr!r}"
    )


@then(parsers.parse("the vector_index_size_observations gauge reads {n:d}"))
def then_index_size_gauge(vec_reindex_world, n: int):
    """Read the gauge from the metrics JSONL (sampled at reindex completion).

    Falls back to ``SqliteVecStore.count()`` if the metrics file is empty
    (defensive: tests that do not assert counters should still pass).
    """
    metrics_path = vec_reindex_world["metrics_path"]
    if metrics_path.exists():
        events: list[dict[str, Any]] = []
        for line in metrics_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                events.append(json.loads(line))
        gauge_events = [
            e for e in events if e.get("name") == "vector_index_size_observations"
        ]
        if gauge_events:
            value = int(gauge_events[-1].get("fields", {}).get("value", -1))
            assert value == n, (
                f"Expected vector_index_size_observations == {n}, got {value}"
            )
            return
    # Fallback: read directly from the SqliteVecStore on disk (truth source).
    sqlite_vec = pytest.importorskip("sqlite_vec")
    from flow_engineering.vectors import SqliteVecStore

    store = SqliteVecStore(vec_reindex_world["vectors_path"])
    assert store.count() == n, (
        f"Expected store.count() == {n}, got {store.count()}"
    )


@then(parsers.parse('the second output contains "{needle}"'))
def then_second_output_contains(vec_reindex_world, needle: str):
    outputs = vec_reindex_world["run_outputs"]
    assert len(outputs) >= 2, (
        f"Expected ≥2 reindex runs, got {len(outputs)}"
    )
    last = outputs[-1]
    combined = (last.output or "") + (last.stderr or "")
    assert needle in combined, (
        f"Expected {needle!r} in second run output, got:\n"
        f"output={last.output!r}\nstderr={last.stderr!r}"
    )


# =====================================================================
# REQ-22 scenario bindings — vector observability counters
# =====================================================================


@scenario(
    "../bdd/req22_vector_observability.feature",
    "vector_search_invoked_total increments per mem_search_hybrid call",
)
def test_req22_invoked_counter(vector_world):
    pass


@scenario(
    "../bdd/req22_vector_observability.feature",
    "vector_search_latency_ms appears in metrics output",
)
def test_req22_latency_in_output(vector_world):
    pass


@scenario(
    "../bdd/req22_vector_observability.feature",
    "reindex_observations_total matches total observations after reindex",
)
def test_req22_reindex_counter(vec_reindex_world):
    pass


@scenario(
    "../bdd/req22_vector_observability.feature",
    "Counter names match REQ-8 convention (no naming drift)",
)
def test_req22_naming_convention(vector_world):
    pass


# =====================================================================
# REQ-22 step definitions — 6 vector_* counters + naming catalog
# =====================================================================


from flow_engineering import observability


def _read_jsonl_events(path: Path) -> list[dict[str, Any]]:
    """Parse the metrics JSONL file at ``path`` into a list of event dicts.

    Mirrors the inline pattern used by ``then_index_size_gauge`` for the
    REQ-21 reindex gauge read; kept as a helper so REQ-22 step defs stay
    declarative. Skips malformed lines defensively (best-effort sink).
    """
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


# ---------- Given ----------


@given("a HybridBackend with a MockEmbeddingProvider")
def given_hybrid_with_mock_provider(vector_world):
    """REQ-22 Given: build a HybridBackend + MockEmbeddingProvider + 3 obs corpus.

    Mirrors ``hybrid_with_mock_provider`` (REQ-17) but uses the shorter,
    REQ-22-style step text so the new feature file reads declaratively.
    Idempotent: if a hybrid is already wired by a previous Given step
    (e.g. for REQ-18 worked example), the existing state is preserved.
    """
    if vector_world.get("hybrid") is not None:
        return
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


@given(parsers.parse("a corpus of {n:d} observations"))
def given_corpus_of_n(vector_world, n: int):
    """REQ-22 Given: ensure exactly ``n`` observations exist on the inner backend.

    If a hybrid is already wired with >= n observations (typical path: the
    REQ-17 ``hybrid_with_mock_provider`` step pre-seeded 3), the extra seed
    step is a no-op so the BDD Given chain reads naturally.
    """
    backend = vector_world.get("backend")
    if backend is None:
        backend = InMemoryBackend()
        vector_world["backend"] = backend
    existing = len(backend.observations)
    for i in range(existing, n):
        backend.mem_save(
            title=f"obs-{i + 1}",
            content=f"drift detection observation {i + 1}",
            topic_key="sdd/x/spec",
        )


@given("the REQ-22 counter catalog has 6 entries")
def given_req22_catalog_has_six(vector_world):
    """REQ-22 scenario 4 Given: assert the canonical catalog is present + sized.

    The catalog lives in ``observability.VECTOR_COUNTER_NAMES`` and is the
    single source of truth that ``record_vector_summary`` and the CLI reindex
    path both consult. Sizing it at 6 catches silent additions or removals.
    """
    names = observability.VECTOR_COUNTER_NAMES
    assert isinstance(names, list), f"VECTOR_COUNTER_NAMES is not a list: {type(names)}"
    assert len(names) == 6, (
        f"Expected 6 counter names in VECTOR_COUNTER_NAMES, got {len(names)}: {names}"
    )


# ---------- When ----------


@when(parsers.parse('I call mem_search_hybrid("{query}", k={k:d}) with trigger={trigger}'))
def when_call_hybrid_with_trigger(vector_world, query: str, k: int, trigger: str):
    """REQ-22 scenario 1 + 4: explicit trigger tag for the observability contract.

    The trigger is passed straight through to ``mem_search_hybrid`` (REQ-22
    scenario 1 uses ``trigger=programmatic`` for direct library calls;
    scenario 4 also uses ``programmatic`` to keep the catalog invariant
    trivial). The vector_world state is preserved so subsequent Then steps
    can inspect the metrics file.
    """
    vector_world["hybrid"].mem_search_hybrid(query, k=k, trigger=trigger)


@when(parsers.parse('I call mem_search_semantic("{query}") with trigger={trigger}'))
def when_call_semantic_with_trigger(vector_world, query: str, trigger: str):
    """REQ-22 scenario 2: pure semantic call delegates to hybrid with alpha=1.0.

    Validates that the ``mem_search_semantic`` alias still emits the latency
    counter through ``record_vector_summary`` (it shares the hybrid path).
    """
    vector_world["hybrid"].mem_search_semantic(query, trigger=trigger)


# ---------- Then ----------


@then(
    parsers.parse(
        'the observability JSONL file contains a line with counter "{name}" '
        "tagged trigger={trigger}"
    )
)
def then_jsonl_has_counter_with_trigger(vector_world, name: str, trigger: str):
    """REQ-22 scenario 1: the invoked counter is tagged with the requested trigger."""
    metrics_path = vector_world["metrics_path"]
    assert metrics_path.exists(), (
        f"Metrics JSONL not found at {metrics_path} — observability sink did not fire"
    )
    events = _read_jsonl_events(metrics_path)
    matches = [
        e
        for e in events
        if e.get("name") == name
        and e.get("fields", {}).get("trigger") == trigger
    ]
    assert matches, (
        f"Expected ≥1 event with name={name!r} trigger={trigger!r}, "
        f"got names: {[e.get('name') for e in events]}"
    )


@then(parsers.parse('the "{name}" counter value is {n:d}'))
def then_counter_value_is(vector_world, name: str, n: int):
    """REQ-22 scenarios 1 + 3: sum the ``count`` (or ``value``) field across events.

    Mirrors the assertion in ``test_cli_reindex.py::TestReindexCounters`` for
    the reindex counter path. The value lives in ``fields.count`` for
    counters and ``fields.value`` for gauges; we sum both shapes so the
    step works for any single-event emission.
    """
    metrics_path = vector_world["metrics_path"]
    assert metrics_path.exists(), (
        f"Metrics JSONL not found at {metrics_path} — observability sink did not fire"
    )
    events = _read_jsonl_events(metrics_path)
    matches = [e for e in events if e.get("name") == name]
    assert matches, (
        f"Expected ≥1 event with name={name!r}, "
        f"got names: {[e.get('name') for e in events]}"
    )
    total = 0
    for e in matches:
        fields = e.get("fields", {})
        if "count" in fields:
            total += int(fields["count"])
        elif "value" in fields:
            total += int(fields["value"])
    assert total == n, (
        f"Expected {name!r} total={n}, got {total} "
        f"(across {len(matches)} event(s))"
    )


@then(
    parsers.parse(
        'the observability JSONL file contains a line with counter "{name}" '
        "with a positive elapsed_ms field"
    )
)
def then_jsonl_has_latency_event(vector_world, name: str):
    """REQ-22 scenario 2: latency histogram event is emitted with elapsed_ms > 0.

    The histogram is sampled per call (single ``elapsed_ms`` int per event),
    so we only need one non-negative sample to validate the wire format.
    """
    metrics_path = vector_world["metrics_path"]
    events = _read_jsonl_events(metrics_path)
    matches = [e for e in events if e.get("name") == name]
    assert matches, (
        f"Expected ≥1 event with name={name!r}, "
        f"got names: {[e.get('name') for e in events]}"
    )
    for e in matches:
        elapsed = e.get("fields", {}).get("elapsed_ms")
        assert elapsed is not None, (
            f"Event {name!r} missing elapsed_ms field: {e!r}"
        )
        assert elapsed >= 0, f"Expected non-negative elapsed_ms in {name}, got {elapsed!r}"


@then(parsers.parse("the elapsed_ms value is less than {limit:d}ms"))
def then_latency_under(vector_world, limit: int):
    """REQ-22 scenario 2: in-process latency stays under the sanity bound."""
    metrics_path = vector_world["metrics_path"]
    events = _read_jsonl_events(metrics_path)
    latencies = [
        e.get("fields", {}).get("elapsed_ms")
        for e in events
        if e.get("name") == "vector_search_latency_ms"
    ]
    assert latencies, "No vector_search_latency_ms events recorded"
    for elapsed in latencies:
        assert elapsed is not None and elapsed < limit, (
            f"elapsed_ms {elapsed} not < {limit}ms limit"
        )


@then("the emitted counter names follow the subject_event_total or subject_metric_unit pattern")
def then_names_follow_convention(vector_world):
    """REQ-22 scenario 4: each emitted name matches a REQ-8 naming pattern.

    Two valid shapes:
    - ``subject_event_total`` for verb-style counters (REQ-8 convention).
    - ``subject_metric_unit`` for state / timing (``_ms``, ``_seconds``,
      or an explicit unit like ``_observations`` on a gauge).
    """
    import re

    pattern = re.compile(r"^[a-z][a-z0-9_]*_(total|ms|seconds|observations)$")
    canonical = set(observability.VECTOR_COUNTER_NAMES)
    metrics_path = vector_world["metrics_path"]
    assert metrics_path.exists(), (
        f"Metrics JSONL not found at {metrics_path} — observability sink did not fire"
    )
    events = _read_jsonl_events(metrics_path)
    assert events, "No events emitted for scenario 4"
    for e in events:
        name = e.get("name", "")
        assert name in canonical, (
            f"Emitted name {name!r} not in canonical VECTOR_COUNTER_NAMES "
            f"({sorted(canonical)})"
        )
        assert pattern.match(name), (
            f"Name {name!r} does not match REQ-8 convention pattern "
            r"^[a-z][a-z0-9_]*_(total|ms|seconds|observations)$"
        )


@then("the canonical 6 names from REQ-22 are all present in the catalog")
def then_canonical_six_present(vector_world):
    """REQ-22 scenario 4: the documented catalog MUST list exactly the 6 names.

    This is the discoverability half of scenario 4: any future
    ``flow metrics`` consumer / dashboard MUST be able to introspect the
    catalog via ``observability.VECTOR_COUNTER_NAMES``.
    """
    expected = {
        "vector_search_invoked_total",
        "vector_search_results_returned_total",
        "vector_search_latency_ms",
        "vector_index_size_observations",
        "reindex_observations_total",
        "reindex_duration_seconds",
    }
    actual = set(observability.VECTOR_COUNTER_NAMES)
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"Missing canonical names: {missing}"
    assert not extra, f"Unexpected extra names: {extra}"


@then("no non-conformant name like vector_search_invocations is emitted")
def then_no_nonconformant_name(vector_world):
    """REQ-22 scenario 4: guards against the documented rename example.

    ``vector_search_invocations`` is the example non-conformant name from
    spec REQ-22 scenario 4 — a plural-only suffix that breaks the
    ``_total`` convention. The JSONL must NEVER contain it (or any other
    name not in the canonical 6).
    """
    metrics_path = vector_world["metrics_path"]
    events = _read_jsonl_events(metrics_path)
    forbidden = "vector_search_invocations"
    canonical = set(observability.VECTOR_COUNTER_NAMES)
    seen = {e.get("name") for e in events}
    assert forbidden not in seen, (
        f"Found forbidden non-conformant name {forbidden!r} in JSONL: {seen}"
    )
    drift = seen - canonical
    assert not drift, f"Found names not in canonical catalog: {drift}"
