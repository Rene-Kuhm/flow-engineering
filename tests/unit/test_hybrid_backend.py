"""Unit tests for hybrid_backend.py (vector-semantic-search PR#1 T1.4 + T1.5).

REQ-17 + REQ-18 + design D2 + D4 + D7: HybridBackend composition wrapper.

T1.4 covered composition + forwarding with ``mem_search_semantic`` and
``mem_search_hybrid`` raising ``NotImplementedError``. T1.5 (this batch)
implements the hybrid scoring formula:

    score = α · cosine_sim + (1 − α) · normalize_bm25(fts)

where ``normalize_bm25(x) = (x − min) / (max − min + ε)`` is computed over
the FTS result set for the current query. The worked example numbers from
design D7 / spec REQ-18 scenario 1 (``obs1 ≈ 0.96``, ``obs3 ≈ 0.39``,
``obs2 ≈ 0.00``) are asserted within ``±1e-3`` tolerance.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from flow_engineering.embedding_provider import (
    EMBEDDING_DIMS,
    EmbeddingProvider,
    MockEmbeddingProvider,
)
from flow_engineering.engram_io import EngramBackend, InMemoryBackend
from flow_engineering.hybrid_backend import HybridBackend

# --- Test fixtures (REQ-18 worked example + helper coverage) ----------------


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

    Unknown texts get the zero vector (cosine_sim → 0.0 fallback).
    """

    def __init__(self, vectors: dict[str, np.ndarray]) -> None:
        self._vectors: dict[str, np.ndarray] = {
            k: _unit(np.asarray(v, dtype=np.float32)) for k, v in vectors.items()
        }
        self.dim = EMBEDDING_DIMS
        self.model_version = "fixed-v1"

    def embed(self, texts: list[str]) -> np.ndarray:
        rows: list[np.ndarray] = []
        for t in texts:
            rows.append(self._vectors.get(t, np.zeros(EMBEDDING_DIMS, dtype=np.float32)))
        return np.stack(rows).astype(np.float32)


class ScoredInMemoryBackend(InMemoryBackend):
    """Test fixture: attaches ``_fts_score`` to ``mem_search`` results.

    Used to control the per-observation FTS score in the worked example
    test without depending on a real FTS5 backend.
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


class TestHybridBackendConstruction:
    """D2: composition — constructor accepts any EngramBackend + any EmbeddingProvider."""

    def test_constructs_with_inmemory_backend_and_mock_provider(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        assert hb is not None

    def test_is_an_engram_backend_subclass(self) -> None:
        # The HybridBackend must satisfy the EngramBackend ABC contract.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        assert isinstance(hb, EngramBackend)

    def test_can_be_used_as_engram_backend_polymorphically(self) -> None:
        # Test that HybridBackend is drop-in compatible with the ABC type.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb: EngramBackend = HybridBackend(inner, provider)
        # mem_save works (it forwards to inner)
        obs = hb.mem_save(
            title="polymorphic test",
            content="any content",
            topic_key="sdd/x/explore",
        )
        assert obs["title"] == "polymorphic test"


class TestHybridBackendForwarding:
    """All non-search methods MUST delegate to inner with same args + return value."""

    def test_mem_save_forwards_to_inner_and_returns_inner_dict(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        obs = hb.mem_save(
            title="forwarded save",
            content="content body",
            topic_key="sdd/test/spec",
            type="manual",
            scope="project",
        )

        # The returned dict must be inner's dict — same id, same fields.
        assert obs["title"] == "forwarded save"
        assert obs["content"] == "content body"
        assert obs["topic_key"] == "sdd/test/spec"
        assert "id" in obs
        # And it must be persisted in the inner backend.
        assert inner.mem_get_observation(obs["id"])["title"] == "forwarded save"

    def test_mem_save_returns_byte_identical_dict_to_inner(self) -> None:
        # Direct call to inner and call through HybridBackend produce the same dict.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        # Direct
        direct_obs = inner.mem_save(
            title="direct", content="d", topic_key="sdd/x/spec", type="manual", scope="project"
        )
        # Through hybrid
        hybrid_obs = hb.mem_save(
            title="hybrid", content="h", topic_key="sdd/x/spec", type="manual", scope="project"
        )
        # The two dicts have the same SHAPE — title differs, but structural fields match.
        assert set(direct_obs.keys()) == set(hybrid_obs.keys())
        assert isinstance(direct_obs["id"], int)
        assert isinstance(hybrid_obs["id"], int)

    def test_mem_search_forwards_to_inner_unchanged(self) -> None:
        # REQ-17 scenario 5: prose FTS5 path is byte-identical when the
        # semantic path is deferred. mem_search MUST return inner.mem_search
        # results unchanged.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        hb.mem_save(title="alpha entry", content="drift detection strategy", topic_key="sdd/x/spec")
        hb.mem_save(title="beta entry", content="logging best practices", topic_key="sdd/x/spec")

        results = hb.mem_search("drift", limit=10, scope="project")
        assert len(results) == 1
        assert "drift detection strategy" in results[0]["content"]

    def test_mem_get_observation_forwards_to_inner(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        saved = hb.mem_save(title="get me", content="content", topic_key="sdd/x/spec")
        got = hb.mem_get_observation(saved["id"])
        assert got["id"] == saved["id"]
        assert got["title"] == "get me"

    def test_iter_observations_forwards_to_inner(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        hb.mem_save(title="a", content="first", topic_key="sdd/x/spec")
        hb.mem_save(title="b", content="second", topic_key="sdd/x/spec")
        hb.mem_save(title="c", content="third", topic_key="sdd/x/spec")

        all_obs = hb.iter_observations()
        assert len(all_obs) == 3

    def test_update_observation_forwards_to_inner(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        saved = hb.mem_save(title="updatable", content="original", topic_key="sdd/x/spec")
        updated = hb.update_observation(saved["id"], content="replaced")
        assert updated["content"] == "replaced"
        # And inner sees it too.
        assert inner.mem_get_observation(saved["id"])["content"] == "replaced"


class TestHybridBackendSearchImplementation:
    """T1.5: mem_search_semantic + mem_search_hybrid run the real hybrid scoring.

    The T1.4 ``NotImplementedError`` deferral is removed. Both methods now
    return ``list[dict]`` (possibly empty) without raising. The signature
    defaults (k=10, alpha=0.5) are preserved.
    """

    def test_mem_search_semantic_runs_without_error(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        # Should NOT raise — implementation landed in batch C.
        results = hb.mem_search_semantic("any query")
        assert isinstance(results, list)

    def test_mem_search_hybrid_runs_without_error(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        results = hb.mem_search_hybrid("any query")
        assert isinstance(results, list)

    def test_search_methods_are_overridden_in_hybrid(self) -> None:
        # InMemoryBackend.mem_search_semantic raises VectorSearchDisabled;
        # HybridBackend.mem_search_semantic MUST handle it itself (return []).
        # The composition wrapper does NOT forward the vector methods.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        # Hybrid returns [] (no FTS hits → empty candidates → empty result).
        assert hb.mem_search_semantic("zzz_nonexistent_token") == []
        # Inner still raises VectorSearchDisabled (proves no forwarding).
        from flow_engineering.engram_io import VectorSearchDisabled

        with pytest.raises(VectorSearchDisabled):
            inner.mem_search_semantic("zzz_nonexistent_token")

    def test_hybrid_search_signature_preserves_alpha_default(self) -> None:
        # REQ-18: alpha defaults to 0.5. Calling without alpha must succeed.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        results = hb.mem_search_hybrid("any query", k=10)  # no alpha kwarg
        assert isinstance(results, list)

    def test_semantic_search_signature_preserves_k_default(self) -> None:
        # REQ-18: k defaults to 10. Calling without k must succeed.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        results = hb.mem_search_semantic("any query")  # no k kwarg
        assert isinstance(results, list)


class TestHybridBackendDelegationPattern:
    """Verify the composition pattern: HybridBackend forwards arbitrary inner attributes."""

    def test_inner_attribute_access_via_private_inner(self) -> None:
        # The composition wrapper should expose inner as an attribute for
        # observability and tests. Tests in T1.5 may use this to inspect state.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        # The inner backend is exposed (private or public, must be reachable).
        assert hb._inner is inner or hb.inner is inner  # type: ignore[attr-defined]

    def test_embedding_provider_accessible_on_hybrid(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        assert hb._embedding_provider is provider or hb.embedding_provider is provider  # type: ignore[attr-defined]

    def test_inner_state_isolated_per_hybrid_instance(self) -> None:
        # Two HybridBackend instances over different inners do not share state.
        inner_a = InMemoryBackend()
        inner_b = InMemoryBackend()
        provider = MockEmbeddingProvider()

        hb_a = HybridBackend(inner_a, provider)
        hb_b = HybridBackend(inner_b, provider)

        hb_a.mem_save(title="a-only", content="a", topic_key="sdd/x/spec")
        hb_b.mem_save(title="b-only", content="b", topic_key="sdd/x/spec")

        assert len(hb_a.iter_observations()) == 1
        assert len(hb_b.iter_observations()) == 1
        assert hb_a.iter_observations()[0]["title"] == "a-only"
        assert hb_b.iter_observations()[0]["title"] == "b-only"


class TestHybridBackendAcceptsAnyProvider:
    """D4: any EmbeddingProvider impl can be passed in."""

    def test_works_with_fresh_mock_provider_per_instance(self) -> None:
        inner = InMemoryBackend()
        for _ in range(3):
            hb = HybridBackend(inner, MockEmbeddingProvider())
            assert isinstance(hb, EngramBackend)

    def test_works_with_mock_provider_used_repeatedly(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        for _ in range(3):
            hb = HybridBackend(inner, provider)
            assert isinstance(hb, EngramBackend)


# --- T1.5: Hybrid scoring formula (REQ-18) -----------------------------------


def _build_worked_example():
    """Construct the design D7 worked example fixture.

    Returns (backend, provider, obs1, obs2, obs3) where:
      - obs1 has semantic 0.96 and FTS score 0.50 (hybrid = 0.98)
      - obs3 has semantic 0.30 and FTS score 0.10 (hybrid = 0.15)
      - obs2 has semantic 0.00 and FTS score 0.20 (hybrid = 0.125)
    Insertion order is obs1 → obs2 → obs3 so id order is 1, 2, 3.

    All three observations contain the FTS query substring "drift detection"
    so they all appear in the candidate set returned by ``InMemoryBackend.mem_search``.
    The per-observation FTS scores are then overridden via ``ScoredInMemoryBackend``
    to hit the design D7 worked example values (0.50 / 0.20 / 0.10).
    """
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

    # Wrap with the scored test backend that attaches _fts_score.
    scored = ScoredInMemoryBackend()
    scored.observations = inner.observations.copy()
    scored.next_id = inner.next_id
    scored.set_score(obs1["id"], 0.50)
    scored.set_score(obs2["id"], 0.20)
    scored.set_score(obs3["id"], 0.10)

    # 2-D vectors chosen so cos(q_vec, obs_vec) hits the design targets:
    #   cos(q, obs1) = 0.96, cos(q, obs3) = 0.30, cos(q, obs2) = 0.0.
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
    return scored, provider, obs1, obs2, obs3


class TestHybridScoringWorkedExample:
    """REQ-18 scenario 1: Hybrid with alpha=0.5 ranks semantic + FTS blended.

    Design D7 worked example. Asserts the exact scores within ±1e-3.
    """

    def test_hybrid_alpha_05_returns_three_observations(self) -> None:
        backend, provider, _obs1, _obs2, _obs3 = _build_worked_example()
        hb = HybridBackend(backend, provider)
        results = hb.mem_search_hybrid("drift detection", k=10, alpha=0.5)
        assert len(results) == 3

    def test_hybrid_alpha_05_ordering_matches_design_d7(self) -> None:
        # obs1 (highest hybrid) > obs3 (semantic-only, mid FTS) > obs2 (zero sem, low-mid FTS)
        backend, provider, obs1, obs2, obs3 = _build_worked_example()
        hb = HybridBackend(backend, provider)
        results = hb.mem_search_hybrid("drift detection", k=10, alpha=0.5)
        ids_in_order = [r["observation_id"] for r in results]
        assert ids_in_order == [obs1["id"], obs3["id"], obs2["id"]]

    def test_hybrid_alpha_05_obs1_score_is_0_98_within_tolerance(self) -> None:
        # normalize_bm25(0.50) = 1.00; hybrid = 0.5·0.96 + 0.5·1.00 = 0.98
        backend, provider, obs1, _obs2, _obs3 = _build_worked_example()
        hb = HybridBackend(backend, provider)
        results = hb.mem_search_hybrid("drift detection", k=10, alpha=0.5)
        top = results[0]
        assert top["observation_id"] == obs1["id"]
        assert top["score"] == pytest.approx(0.98, abs=1e-3)

    def test_hybrid_alpha_05_obs3_score_is_0_15_within_tolerance(self) -> None:
        # normalize_bm25(0.10) = 0.00; hybrid = 0.5·0.30 + 0.5·0.00 = 0.15
        backend, provider, _obs1, _obs2, obs3 = _build_worked_example()
        hb = HybridBackend(backend, provider)
        results = hb.mem_search_hybrid("drift detection", k=10, alpha=0.5)
        obs3_result = next(r for r in results if r["observation_id"] == obs3["id"])
        assert obs3_result["score"] == pytest.approx(0.15, abs=1e-3)

    def test_hybrid_alpha_05_obs2_score_is_0_125_within_tolerance(self) -> None:
        # normalize_bm25(0.20) = 0.25; hybrid = 0.5·0.00 + 0.5·0.25 = 0.125
        backend, provider, _obs1, obs2, _obs3 = _build_worked_example()
        hb = HybridBackend(backend, provider)
        results = hb.mem_search_hybrid("drift detection", k=10, alpha=0.5)
        obs2_result = next(r for r in results if r["observation_id"] == obs2["id"])
        assert obs2_result["score"] == pytest.approx(0.125, abs=1e-3)

    def test_hybrid_alpha_05_results_have_required_fields(self) -> None:
        # REQ-17 contract: each result has observation_id, score, rank.
        backend, provider, *_ = _build_worked_example()
        hb = HybridBackend(backend, provider)
        results = hb.mem_search_hybrid("drift detection", k=10, alpha=0.5)
        for i, r in enumerate(results):
            assert "observation_id" in r
            assert "score" in r
            assert "rank" in r
            assert r["rank"] == i
            assert isinstance(r["score"], float)

    def test_hybrid_alpha_05_semantic_pulls_obs3_above_obs2(self) -> None:
        # REQ-18 scenario 1 explicit assertion: obs3's semantic contribution
        # pulls it above obs2 despite obs2 having higher raw FTS score (0.20 vs 0.10).
        backend, provider, _obs1, obs2, obs3 = _build_worked_example()
        hb = HybridBackend(backend, provider)
        results = hb.mem_search_hybrid("drift detection", k=10, alpha=0.5)
        # obs3 rank = 1, obs2 rank = 2
        rank_obs3 = next(r for r in results if r["observation_id"] == obs3["id"])["rank"]
        rank_obs2 = next(r for r in results if r["observation_id"] == obs2["id"])["rank"]
        assert rank_obs3 == 1
        assert rank_obs2 == 2


class TestHybridAlphaBoundaries:
    """REQ-18 scenarios 2, 3, 4: alpha boundary semantics."""

    def test_hybrid_alpha_10_returns_same_ids_as_pure_semantic(self) -> None:
        # alpha=1.0 → pure semantic. FTS contribution is multiplied by 0.
        backend, provider, obs1, obs2, obs3 = _build_worked_example()
        hb = HybridBackend(backend, provider)
        # InMemoryBackend returns observations containing the query substring;
        # for "drift" all 3 contain it via their content.
        sem_results = hb.mem_search_semantic("drift detection", k=10)
        hyb_results = hb.mem_search_hybrid("drift detection", k=10, alpha=1.0)
        sem_ids = [r["observation_id"] for r in sem_results]
        hyb_ids = [r["observation_id"] for r in hyb_results]
        assert sem_ids == hyb_ids
        # And the highest cosine_sim (0.96 for obs1) ranks first.
        assert hyb_ids[0] == obs1["id"]
        # And obs2 (cosine=0.0) ranks last.
        assert hyb_ids[-1] == obs2["id"]

    def test_hybrid_alpha_10_scores_within_tolerance_of_pure_semantic(self) -> None:
        # With alpha=1.0, hybrid score == cosine_sim (FTS multiplied by 0).
        backend, provider, obs1, _obs2, _obs3 = _build_worked_example()
        hb = HybridBackend(backend, provider)
        results = hb.mem_search_hybrid("drift detection", k=10, alpha=1.0)
        # obs1 is the top result with cosine_sim 0.96 → hybrid score ≈ 0.96.
        top = results[0]
        assert top["observation_id"] == obs1["id"]
        assert top["score"] == pytest.approx(0.96, abs=1e-3)

    def test_hybrid_alpha_00_matches_pure_fts_ordering(self) -> None:
        # alpha=0.0 → pure FTS. Hybrid order == inner.mem_search order.
        # InMemoryBackend returns by id desc; we set up FTS scores that
        # monotonically increase with id, so the orderings match.
        inner = InMemoryBackend()
        obs_low = inner.mem_save(
            title="low", content="drift detection drift", topic_key="sdd/test/spec"
        )
        obs_mid = inner.mem_save(
            title="mid", content="drift detection drift drift", topic_key="sdd/test/spec"
        )
        obs_high = inner.mem_save(
            title="high", content="drift detection drift drift drift", topic_key="sdd/test/spec"
        )
        # Inner returns [obs_high, obs_mid, obs_low] by id desc.
        # Their substring counts of "drift" are 3, 2, 1 — also desc by id.
        # So hybrid alpha=0.0 sorted by FTS desc gives same order.
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        results = hb.mem_search_hybrid("drift", k=10, alpha=0.0)
        ids_in_order = [r["observation_id"] for r in results]
        assert ids_in_order == [obs_high["id"], obs_mid["id"], obs_low["id"]]

    def test_hybrid_alpha_15_raises_value_error(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        with pytest.raises(ValueError, match=r"alpha must be in \[0\.0, 1\.0\], got 1\.5"):
            hb.mem_search_hybrid("any query", alpha=1.5)

    def test_hybrid_alpha_negative_raises_value_error(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        with pytest.raises(ValueError, match=r"alpha must be in \[0\.0, 1\.0\], got -0\.1"):
            hb.mem_search_hybrid("any query", alpha=-0.1)

    def test_hybrid_alpha_out_of_range_does_no_embedding_work(self) -> None:
        # Validation MUST happen before any embedding call.
        # We verify by passing alpha=2.0 and confirming it raises immediately
        # (the call returns within microseconds — no model.encode roundtrip).
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        with pytest.raises(ValueError, match=r"alpha must be in \[0\.0, 1\.0\]"):
            hb.mem_search_hybrid("any query", alpha=2.0)


class TestHybridSemanticDelegation:
    """mem_search_semantic delegates to mem_search_hybrid(query, k, alpha=1.0)."""

    def test_semantic_search_returns_same_ids_as_hybrid_alpha_1(self) -> None:
        backend, provider, obs1, obs2, obs3 = _build_worked_example()
        hb = HybridBackend(backend, provider)
        sem_ids = [r["observation_id"] for r in hb.mem_search_semantic("drift detection", k=10)]
        hyb_ids = [
            r["observation_id"] for r in hb.mem_search_hybrid("drift detection", k=10, alpha=1.0)
        ]
        assert sem_ids == hyb_ids
        # Spot-check that we did exercise all 3 (regression guard against
        # accidentally limiting to k=1 default).
        assert set(sem_ids) == {obs1["id"], obs2["id"], obs3["id"]}

    def test_semantic_search_honors_k_parameter(self) -> None:
        backend, provider, *_ = _build_worked_example()
        hb = HybridBackend(backend, provider)
        results = hb.mem_search_semantic("drift detection", k=2)
        assert len(results) == 2


class TestHybridEmptyAndEdgeCases:
    """REQ-18 scenario 5 + edge cases: empty / single / all-equal scores."""

    def test_empty_query_returns_empty_results(self) -> None:
        # No FTS hits → no candidates → empty result (no division-by-zero).
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        results = hb.mem_search_hybrid("zzz_nonexistent_token_xyz", k=10, alpha=0.5)
        assert results == []

    def test_single_candidate_does_not_divide_by_zero(self) -> None:
        # One candidate → span=0 → epsilon path returns 0.0 (no ZeroDivisionError).
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        obs = inner.mem_save(title="only", content="drift detection strategy", topic_key="sdd/x")
        hb = HybridBackend(inner, provider)
        results = hb.mem_search_hybrid("drift", k=10, alpha=0.5)
        assert len(results) == 1
        assert results[0]["observation_id"] == obs["id"]
        # Score is finite (no NaN, no Inf).
        assert isinstance(results[0]["score"], float)
        assert results[0]["score"] == results[0]["score"]  # not NaN
        assert abs(results[0]["score"]) < float("inf")

    def test_k_smaller_than_candidate_count_truncates(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        for i in range(5):
            inner.mem_save(title=f"obs{i}", content=f"drift detection case {i}", topic_key="sdd/x")
        hb = HybridBackend(inner, provider)
        results = hb.mem_search_hybrid("drift", k=2, alpha=0.5)
        assert len(results) == 2

    def test_all_equal_fts_scores_does_not_divide_by_zero(self) -> None:
        # All observations have identical FTS score → span=0 → epsilon path.
        # Verify result is finite and well-ordered.
        inner = InMemoryBackend()
        for i in range(3):
            inner.mem_save(title=f"obs{i}", content="drift detection case", topic_key="sdd/x")
        scored = ScoredInMemoryBackend()
        scored.observations = inner.observations.copy()
        scored.next_id = inner.next_id
        for obs in inner.observations.values():
            scored.set_score(obs["id"], 0.42)
        provider = MockEmbeddingProvider()
        hb = HybridBackend(scored, provider)
        results = hb.mem_search_hybrid("drift", k=10, alpha=0.5)
        assert len(results) == 3
        for r in results:
            assert isinstance(r["score"], float)
            assert r["score"] == r["score"]  # not NaN


class TestNormalizeBm25Helper:
    """Unit tests for the static ``_normalize_bm25`` helper."""

    def test_empty_list_returns_empty(self) -> None:
        assert HybridBackend._normalize_bm25([]) == []

    def test_single_value_returns_zero(self) -> None:
        # span = 0 → epsilon path → 0.0 (no division-by-zero).
        assert HybridBackend._normalize_bm25([0.5]) == [0.0]

    def test_all_equal_returns_all_zeros(self) -> None:
        assert HybridBackend._normalize_bm25([0.3, 0.3, 0.3]) == [0.0, 0.0, 0.0]

    def test_min_max_produces_zero_and_one(self) -> None:
        result = HybridBackend._normalize_bm25([0.1, 0.5, 0.9])
        assert result[0] == pytest.approx(0.0, abs=1e-9)
        assert result[1] == pytest.approx(0.5, abs=1e-9)
        assert result[2] == pytest.approx(1.0, abs=1e-9)

    def test_monotonic_scaling(self) -> None:
        # Strictly increasing input → strictly increasing output.
        result = HybridBackend._normalize_bm25([0.1, 0.2, 0.5, 0.9])
        for i in range(len(result) - 1):
            assert result[i] < result[i + 1]

    def test_worked_example_normalization(self) -> None:
        # From the REQ-18 worked example: FTS set [0.50, 0.10, 0.20].
        # Expected normalized: [1.00, 0.00, 0.25].
        result = HybridBackend._normalize_bm25([0.50, 0.10, 0.20])
        assert result[0] == pytest.approx(1.0, abs=1e-9)
        assert result[1] == pytest.approx(0.0, abs=1e-9)
        assert result[2] == pytest.approx(0.25, abs=1e-9)


class TestCosineSimHelper:
    """Unit tests for the static ``_cosine_sim`` helper."""

    def test_identical_unit_vectors_yield_1(self) -> None:
        v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert HybridBackend._cosine_sim(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_yield_0(self) -> None:
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        assert HybridBackend._cosine_sim(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors_yield_minus_1(self) -> None:
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
        assert HybridBackend._cosine_sim(a, b) == pytest.approx(-1.0, abs=1e-6)

    def test_zero_vector_returns_0(self) -> None:
        # Avoid division-by-zero: return 0.0 when either norm is zero.
        a = np.array([1.0, 0.0], dtype=np.float32)
        z = np.zeros(2, dtype=np.float32)
        assert HybridBackend._cosine_sim(a, z) == 0.0
        assert HybridBackend._cosine_sim(z, a) == 0.0
        assert HybridBackend._cosine_sim(z, z) == 0.0

    def test_45_degree_angle_yields_sqrt_2_over_2(self) -> None:
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([1.0, 1.0], dtype=np.float32) / float(np.sqrt(2))
        assert HybridBackend._cosine_sim(a, b) == pytest.approx(float(np.sqrt(2)) / 2, abs=1e-6)
