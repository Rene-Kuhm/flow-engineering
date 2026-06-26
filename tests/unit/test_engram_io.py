"""Unit tests for engram_io.py — cross-session memory wrapper.

REQ-8: Cross-session recovery via Engram topic keys.
REQ-17: Semantic search activation gate (vector-semantic-search PR#1 T1.2).
"""

from __future__ import annotations

import json

import pytest

from flow_engineering.engram_io import (
    EngramClient,
    InMemoryBackend,
    VectorSearchDisabled,
    cross_session_topic_key,
    phase_topic_key,
)


class TestTopicKeys:
    def test_phase_topic_key(self) -> None:
        assert phase_topic_key("my-change", "explore") == "sdd/my-change/explore"
        assert phase_topic_key("my-change", "apply-progress") == "sdd/my-change/apply-progress"

    def test_cross_session_topic_key(self) -> None:
        assert cross_session_topic_key() == "sdd/flow-engineering"


class TestEngramClientSaveLoad:
    def test_save_and_load_phase(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("explore", "## Exploration content here")
        loaded = client.load_phase("explore")
        # save_phase now appends an unbound code_refs block, so we check
        # prose membership instead of byte-for-byte equality.
        assert loaded is not None
        assert "## Exploration content here" in loaded
        assert "code_refs" in loaded

    def test_load_missing_phase_returns_none(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        assert client.load_phase("propose") is None

    def test_save_phase_with_custom_title(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("explore", "content", title="Custom title")
        results = backend.mem_search(query="Custom", topic_key="sdd/my-change/explore")
        assert len(results) == 1
        assert results[0]["title"] == "Custom title"

    def test_two_changes_isolated(self) -> None:
        backend = InMemoryBackend()
        client_a = EngramClient("change-a", backend)
        client_b = EngramClient("change-b", backend)
        client_a.save_phase("explore", "A explore content")
        client_b.save_phase("explore", "B explore content")
        loaded_a = client_a.load_phase("explore")
        loaded_b = client_b.load_phase("explore")
        assert loaded_a is not None and "A explore content" in loaded_a
        assert loaded_b is not None and "B explore content" in loaded_b


class TestApplyProgress:
    def test_save_progress_creates_task(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_progress("T1.1", "completed")
        # save_phase now appends an unbound code_refs block; parse only the prose.
        loaded_raw = client.load_phase("apply-progress")
        assert loaded_raw is not None
        prose = loaded_raw.split("<!-- code_refs -->")[0]
        loaded = json.loads(prose)
        assert loaded["tasks"]["T1.1"]["status"] == "completed"

    def test_save_progress_updates_existing(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_progress("T1.1", "in_progress", details={"note": "started"})
        client.save_progress("T1.1", "completed", details={"tests_passed": True})
        loaded_raw = client.load_phase("apply-progress")
        assert loaded_raw is not None
        prose = loaded_raw.split("<!-- code_refs -->")[0]
        loaded = json.loads(prose)
        assert loaded["tasks"]["T1.1"]["status"] == "completed"
        assert loaded["tasks"]["T1.1"]["details"]["tests_passed"] is True


class TestCrossSession:
    def test_search_cross_session(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("explore", "This is about Flow Engineering")
        results = client.search_cross_session("Flow Engineering")
        assert len(results) >= 1


class TestVectorSearchDisabled:
    """REQ-17: semantic search activation gate (vector-semantic-search PR#1 T1.2).

    InMemoryBackend is the legacy prose test fixture. It MUST raise
    VectorSearchDisabled (with the install hint) when vector/hybrid methods are
    called, while mem_search (FTS5 prose) continues to work unchanged.
    """

    def test_inmemory_mem_search_semantic_raises_vector_search_disabled(self) -> None:
        backend = InMemoryBackend()
        with pytest.raises(VectorSearchDisabled) as exc_info:
            backend.mem_search_semantic("any query")
        assert "pip install flow-engineering[vectors]" in str(exc_info.value)

    def test_inmemory_mem_search_hybrid_raises_vector_search_disabled(self) -> None:
        backend = InMemoryBackend()
        with pytest.raises(VectorSearchDisabled) as exc_info:
            backend.mem_search_hybrid("any query", k=5, alpha=0.5)
        assert "pip install flow-engineering[vectors]" in str(exc_info.value)

    def test_vector_search_disabled_is_runtime_error_subclass(self) -> None:
        # Catchable as RuntimeError so callers can isolate it from other errors.
        assert issubclass(VectorSearchDisabled, RuntimeError)

    def test_inmemory_mem_search_still_works_unchanged(self) -> None:
        # REQ-17 scenario 5 zero regression: prose FTS5 path is byte-identical.
        backend = InMemoryBackend()
        backend.mem_save(
            title="drift entry",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
        )
        results = backend.mem_search("drift detection")
        assert len(results) == 1
        assert "drift detection strategy" in results[0]["content"]

    def test_inmemory_mem_search_semantic_does_not_import_torch(self) -> None:
        # Spec REQ-17: no torch/sqlite_vec import attempted at any gate path.
        import sys

        before = {"torch", "sentence_transformers", "sqlite_vec"} & set(sys.modules)
        try:
            backend = InMemoryBackend()
            with pytest.raises(VectorSearchDisabled):
                backend.mem_search_semantic("drift detection")
        finally:
            after = {"torch", "sentence_transformers", "sqlite_vec"} & set(sys.modules)
            assert before == after, (
                f"Vector search gate leaked heavy imports: {after - before}"
            )
