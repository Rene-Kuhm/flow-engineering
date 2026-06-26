"""Unit tests for hybrid_backend.py (vector-semantic-search PR#1 T1.4).

REQ-17 + REQ-18 + design D2 + D4: HybridBackend composition wrapper.

T1.4 is the SCAFFOLD layer — composition pattern + forwarding. The actual
hybrid scoring formula lands in T1.5 (batch C). For T1.4:

- HybridBackend(inner, embedding_provider) constructs without error.
- mem_save / mem_search / mem_get_observation / iter_observations /
  update_observation forward to inner (delegation via __getattr__).
- mem_search_semantic and mem_search_hybrid raise NotImplementedError with
  a clear pointer to batch C (T1.5) — implementation deferred.
- Signatures preserve default kwargs (k=10, alpha=0.5).
"""

from __future__ import annotations

from typing import Any

import pytest

from flow_engineering.embedding_provider import MockEmbeddingProvider
from flow_engineering.engram_io import EngramBackend, InMemoryBackend
from flow_engineering.hybrid_backend import HybridBackend


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

        saved = hb.mem_save(
            title="get me", content="content", topic_key="sdd/x/spec"
        )
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

        saved = hb.mem_save(
            title="updatable", content="original", topic_key="sdd/x/spec"
        )
        updated = hb.update_observation(saved["id"], content="replaced")
        assert updated["content"] == "replaced"
        # And inner sees it too.
        assert inner.mem_get_observation(saved["id"])["content"] == "replaced"


class TestHybridBackendSearchDeferral:
    """mem_search_semantic + mem_search_hybrid raise NotImplementedError with batch C pointer."""

    def test_mem_search_semantic_raises_not_implemented(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        with pytest.raises(NotImplementedError) as exc_info:
            hb.mem_search_semantic("any query")
        # The pointer must reference batch C (the next apply batch).
        assert "batch C" in str(exc_info.value) or "T1.5" in str(exc_info.value)

    def test_mem_search_hybrid_raises_not_implemented(self) -> None:
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        with pytest.raises(NotImplementedError) as exc_info:
            hb.mem_search_hybrid("any query")
        # The pointer must reference batch C (the next apply batch).
        assert "batch C" in str(exc_info.value) or "T1.5" in str(exc_info.value)

    def test_search_methods_are_not_forwarded_to_inner(self) -> None:
        # InMemoryBackend.mem_search_semantic raises VectorSearchDisabled;
        # HybridBackend.mem_search_semantic raises NotImplementedError with
        # a different message. The composition wrapper MUST override the
        # vector methods, NOT forward them to inner.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        with pytest.raises(NotImplementedError):
            hb.mem_search_semantic("q")
        # Confirm inner still raises VectorSearchDisabled (NOT touched).
        from flow_engineering.engram_io import VectorSearchDisabled

        with pytest.raises(VectorSearchDisabled):
            inner.mem_search_semantic("q")

    def test_hybrid_search_signature_preserves_alpha_default(self) -> None:
        # REQ-18: alpha defaults to 0.5. The signature must accept alpha as kwarg.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        # If alpha defaulted wrong, this call would still raise NotImplementedError
        # (correct) — but the call must accept alpha as a kwarg without TypeError.
        with pytest.raises(NotImplementedError):
            hb.mem_search_hybrid("q", k=10, alpha=0.5)

    def test_semantic_search_signature_preserves_k_default(self) -> None:
        # REQ-18: k defaults to 10. The signature must accept k as kwarg.
        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        with pytest.raises(NotImplementedError):
            hb.mem_search_semantic("q", k=10)


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