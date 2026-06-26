"""BDD step definitions for vector-semantic-search PR#1 REQ-17 (batch D2 T1.9).

Covers ``req17_semantic_search.feature`` — 5 scenarios exercising the
semantic-search activation gate (REQ-17).

Scenarios:
- Scenario 1: HybridBackend with a controlled embedding provider returns
  semantic results (the gate is open via the mock seam).
- Scenarios 2-3: InMemoryBackend raises VectorSearchDisabled (library-level
  gate; the InMemoryBackend raises with the install hint regardless of env vs
  extra distinction — the env-vs-extra differentiation lives in the CLI
  layer at PR#2 T2.4).
- Scenario 4: prose ``mem_search`` is byte-identical when vectors disabled.
- Scenario 5: HybridBackend forwards mem_save / mem_get_observation to inner.

Test isolation:
- Each scenario gets a fresh ``InMemoryBackend`` + ``MockEmbeddingProvider``.
- ``FLOW_VECTOR_SEARCH`` is unset via ``monkeypatch.delenv`` for the gate
  scenarios so the InMemoryBackend / HybridBackend layer is tested without
  the env-var coupling from real CLI invocations.
- ``sys.modules`` is introspected before / after the call to verify no torch
  or sqlite_vec import leaks through the gate path (REQ-17 scenarios 2-4).

REQ-18 (hybrid scoring) step definitions land in batch D2 T1.10 and extend
this file with additional @scenario bindings + @given / @when / @then steps.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering.engram_io import InMemoryBackend, VectorSearchDisabled
from flow_engineering.hybrid_backend import HybridBackend


# ---------- World fixture ----------


@pytest.fixture
def vector_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-17 scenarios."""
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
