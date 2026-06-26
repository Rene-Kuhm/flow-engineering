"""Unit tests for ``EmbeddingProvider.embed_batch`` chunking (T2.5 helper).

REQ-21 + design D8: reindex calls ``embed_batch(texts, batch_size=32)`` to
batch-process observations. The default impl chunks ``texts`` into slices
of ``batch_size`` and concatenates ``embed()`` outputs along axis 0.

Acceptance:
- Returns shape ``(N, 384)`` for ``N`` inputs.
- Concatenates per-batch results in input order.
- Empty input returns ``(0, 384)`` without touching the model.
- Invalid ``batch_size`` (<= 0) raises ``ValueError``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from flow_engineering.embedding_provider import (
    EMBEDDING_DIMS,
    MockEmbeddingProvider,
)


def _track_provider(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace ``MockEmbeddingProvider.embed`` with a tracked fake.

    Returns a dict with ``call_args`` so tests can assert how many times
    ``embed()`` was called and with which chunks.
    """
    state: dict[str, Any] = {"calls": []}
    original = MockEmbeddingProvider.embed

    def _fake_embed(self: MockEmbeddingProvider, texts: list[str]) -> np.ndarray:
        state["calls"].append(list(texts))
        return original(self, texts)

    monkeypatch.setattr(MockEmbeddingProvider, "embed", _fake_embed)
    return state


class TestEmbedBatchDefaults:
    """``embed_batch`` works on the default ABC with mock provider."""

    def test_returns_n_by_384_for_default_batch_size(self) -> None:
        provider = MockEmbeddingProvider()
        out = provider.embed_batch(["a", "b", "c", "d", "e"])
        assert out.shape == (5, EMBEDDING_DIMS)
        assert out.dtype == np.float32

    def test_empty_input_returns_zero_384(self) -> None:
        provider = MockEmbeddingProvider()
        out = provider.embed_batch([])
        assert out.shape == (0, EMBEDDING_DIMS)
        assert out.dtype == np.float32

    def test_concatenates_in_input_order(self) -> None:
        # Determinism: embed_batch(["a","b"]) == embed(["a","b"]) up to order.
        provider_a = MockEmbeddingProvider()
        provider_b = MockEmbeddingProvider()
        np.testing.assert_array_equal(
            provider_a.embed(["a", "b", "c"]),
            provider_b.embed_batch(["a", "b", "c"]),
        )


class TestEmbedBatchChunking:
    """``embed_batch`` chunks inputs into slices of ``batch_size``."""

    def test_chunks_into_correct_batch_sizes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        state = _track_provider(monkeypatch)
        provider = MockEmbeddingProvider()
        # 7 inputs, batch_size=3 → 3 chunks of [3, 3, 1].
        provider.embed_batch(["a", "b", "c", "d", "e", "f", "g"], batch_size=3)
        sizes = [len(c) for c in state["calls"]]
        assert sizes == [3, 3, 1]
        flat: list[str] = []
        for c in state["calls"]:
            flat.extend(c)
        assert flat == ["a", "b", "c", "d", "e", "f", "g"]

    def test_chunking_preserves_per_row_identity(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Each row of the concatenated output MUST equal the corresponding
        # row of a single-shot embed() call — chunking is purely an
        # implementation detail.
        provider_a = MockEmbeddingProvider()
        provider_b = MockEmbeddingProvider()
        single = provider_a.embed(["alpha", "beta", "gamma", "delta"])
        batched = provider_b.embed_batch(["alpha", "beta", "gamma", "delta"], batch_size=2)
        np.testing.assert_array_equal(single, batched)

    def test_batch_size_larger_than_input_calls_embed_once(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        state = _track_provider(monkeypatch)
        provider = MockEmbeddingProvider()
        provider.embed_batch(["a", "b"], batch_size=32)
        assert len(state["calls"]) == 1
        assert state["calls"][0] == ["a", "b"]


class TestEmbedBatchInvalidBatchSize:
    """``batch_size <= 0`` raises ``ValueError``."""

    def test_batch_size_zero_raises(self) -> None:
        provider = MockEmbeddingProvider()
        with pytest.raises(ValueError):
            provider.embed_batch(["a", "b"], batch_size=0)

    def test_batch_size_negative_raises(self) -> None:
        provider = MockEmbeddingProvider()
        with pytest.raises(ValueError):
            provider.embed_batch(["a", "b"], batch_size=-1)


# ---------- SentenceTransformersProvider.embed_batch ----------


def _ensure_torch_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    from unittest.mock import MagicMock

    if "torch" not in sys.modules:
        monkeypatch.setitem(sys.modules, "torch", MagicMock())


def _install_fake_sentence_transformers(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    """Replace ``sentence_transformers`` with a fake that records encode calls."""
    import sys
    from unittest.mock import MagicMock

    state: dict[str, Any] = {"constructs": [], "encodes": []}

    class FakeModel:
        def __init__(self, model_name: str) -> None:
            state["constructs"].append(model_name)

        def encode(self, texts, convert_to_numpy: bool = True):  # noqa: ARG002
            state["encodes"].append(list(texts))
            arr = np.asarray(list(texts), dtype=object)
            if arr.size == 0:
                return np.zeros((0, EMBEDDING_DIMS), dtype=np.float32)
            return np.zeros((len(texts), EMBEDDING_DIMS), dtype=np.float32)

    mock_module = MagicMock()
    mock_module.SentenceTransformer = FakeModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", mock_module)
    return state


class TestSentenceTransformersEmbedBatch:
    """``SentenceTransformersProvider.embed_batch`` uses the inherited default."""

    def test_embed_batch_chunks_via_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        state = _install_fake_sentence_transformers(monkeypatch)

        provider = SentenceTransformersProvider("batch-test")
        provider.embed_batch(["a", "b", "c", "d", "e"], batch_size=2)
        sizes = [len(c) for c in state["encodes"]]
        assert sizes == [2, 2, 1]

    def test_embed_batch_empty_input_does_not_load_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        state = _install_fake_sentence_transformers(monkeypatch)
        provider = SentenceTransformersProvider("batch-test")
        out = provider.embed_batch([])
        assert out.shape == (0, EMBEDDING_DIMS)
        # The model must NOT have been constructed for an empty call.
        assert state["constructs"] == []
        assert state["encodes"] == []