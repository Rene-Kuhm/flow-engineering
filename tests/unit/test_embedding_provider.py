"""Unit tests for embedding_provider.py (vector-semantic-search PR#1 + PR#2).

REQ-19: EmbeddingProvider ABC + lazy import contract.
- MockEmbeddingProvider returns deterministic 384-dim vectors
- Module import does NOT pull torch / sentence_transformers
- EmbeddingProviderUnavailable is an ImportError subclass with install hint
- Embedding shape is (N, 384); empty input returns (0, 384)

PR#2 T2.1: SentenceTransformersProvider
- Lazy torch import inside __init__; module-level import stays clean
- EmbeddingProviderUnavailable raised when torch is missing
- Model loading is lazy (only on first embed() call)
- embed() returns shape (N, 384); empty list returns (0, 384)
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import numpy as np
import pytest

from flow_engineering.embedding_provider import (
    EMBEDDING_DIMS,
    EmbeddingProvider,
    EmbeddingProviderUnavailable,
    MockEmbeddingProvider,
)


class TestEmbeddingProviderABC:
    """REQ-19: ABC contract — dim, model_version, abstract embed()."""

    def test_embedding_dims_class_constant_is_384(self) -> None:
        assert EMBEDDING_DIMS == 384

    def test_embedding_dims_is_a_class_attribute_on_abc(self) -> None:
        assert hasattr(EmbeddingProvider, "EMBEDDING_DIMS")
        assert EmbeddingProvider.EMBEDDING_DIMS == 384

    def test_cannot_instantiate_abstract_provider(self) -> None:
        # Direct instantiation of the ABC MUST raise (abstract method embed).
        with pytest.raises(TypeError):
            EmbeddingProvider()  # type: ignore[abstract]

    def test_subclass_without_embed_is_still_abstract(self) -> None:
        class Incomplete(EmbeddingProvider):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]


class TestMockEmbeddingProviderDeterminism:
    """REQ-19 scenario 1: same input → same vector; L2 norm ≈ 1.0."""

    def test_returns_numpy_ndarray(self) -> None:
        provider = MockEmbeddingProvider()
        out = provider.embed(["hello world"])
        assert isinstance(out, np.ndarray)

    def test_shape_is_n_by_384_for_single_input(self) -> None:
        provider = MockEmbeddingProvider()
        out = provider.embed(["hello world"])
        assert out.shape == (1, EMBEDDING_DIMS)

    def test_shape_is_n_by_384_for_multiple_inputs(self) -> None:
        provider = MockEmbeddingProvider()
        out = provider.embed(["a", "b", "c", "d", "e"])
        assert out.shape == (5, EMBEDDING_DIMS)

    def test_shape_is_zero_384_for_empty_input(self) -> None:
        # REQ-19 scenario 4: empty input list returns (0, 384).
        provider = MockEmbeddingProvider()
        out = provider.embed([])
        assert out.shape == (0, EMBEDDING_DIMS)
        assert out.dtype == np.float32

    def test_same_input_returns_identical_vectors(self) -> None:
        provider = MockEmbeddingProvider()
        first = provider.embed(["hello world"])
        second = provider.embed(["hello world"])
        np.testing.assert_array_equal(first, second)

    def test_different_inputs_produce_different_vectors(self) -> None:
        # REQ-19 scenario 1: hash-based derivation, not all-zeros.
        provider = MockEmbeddingProvider()
        a = provider.embed(["hello world"])[0]
        b = provider.embed(["goodbye world"])[0]
        assert not np.array_equal(a, b)

    def test_rows_are_unit_norm_within_tolerance(self) -> None:
        # REQ-19 scenario 1: L2 norm in [0.99, 1.01].
        provider = MockEmbeddingProvider()
        out = provider.embed(["a", "b", "c", "d", "e"])
        norms = np.linalg.norm(out, axis=1)
        for n in norms:
            assert 0.99 <= n <= 1.01, f"norm {n} outside [0.99, 1.01]"

    def test_determinism_across_separate_instances(self) -> None:
        # Two freshly-constructed providers must agree on the same input —
        # this is the gold standard for golden tests.
        a = MockEmbeddingProvider()
        b = MockEmbeddingProvider()
        va = a.embed(["drift detection strategy"])
        vb = b.embed(["drift detection strategy"])
        np.testing.assert_array_equal(va, vb)

    def test_determinism_across_multiple_calls_same_instance(self) -> None:
        provider = MockEmbeddingProvider()
        first = provider.embed(["alpha", "beta", "gamma"])
        second = provider.embed(["alpha", "beta", "gamma"])
        third = provider.embed(["alpha", "beta", "gamma"])
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(second, third)


class TestMockEmbeddingProviderMetadata:
    """Provider-level metadata contract (dim, model_version)."""

    def test_mock_dim_attribute_is_384(self) -> None:
        provider = MockEmbeddingProvider()
        assert provider.dim == EMBEDDING_DIMS == 384

    def test_mock_model_version_is_nonempty_string(self) -> None:
        provider = MockEmbeddingProvider()
        assert isinstance(provider.model_version, str)
        assert len(provider.model_version) > 0

    def test_mock_is_a_subclass_of_embedding_provider(self) -> None:
        provider = MockEmbeddingProvider()
        assert isinstance(provider, EmbeddingProvider)


class TestEmbeddingProviderUnavailable:
    """REQ-19 scenario 3: EmbeddingProviderUnavailable is an ImportError subclass."""

    def test_is_import_error_subclass(self) -> None:
        assert issubclass(EmbeddingProviderUnavailable, ImportError)

    def test_default_message_contains_install_hint(self) -> None:
        exc = EmbeddingProviderUnavailable()
        assert "pip install flow-engineering[vectors]" in str(exc)

    def test_custom_message_preserved(self) -> None:
        exc = EmbeddingProviderUnavailable("custom message")
        assert "custom message" in str(exc)

    def test_can_be_raised_with_install_hint_message(self) -> None:
        with pytest.raises(EmbeddingProviderUnavailable) as exc_info:
            raise EmbeddingProviderUnavailable(
                "Install [vectors] extra: pip install flow-engineering[vectors]"
            )
        assert "pip install flow-engineering[vectors]" in str(exc_info.value)


class TestEmbeddingProviderLazyImport:
    """REQ-19 scenario 2: importing the module MUST NOT trigger torch/sentence_transformers."""

    def test_module_import_does_not_pull_torch(self) -> None:
        # Subprocess isolation — guarantees fresh sys.modules at import time.
        import subprocess

        script = (
            "import sys; "
            "import flow_engineering.embedding_provider as m; "
            "torch = 'torch' in sys.modules; "
            "st = 'sentence_transformers' in sys.modules; "
            "abc_ok = hasattr(m, 'EmbeddingProvider'); "
            "mock_ok = hasattr(m, 'MockEmbeddingProvider'); "
            "print(f'torch={torch} st={st} abc_ok={abc_ok} mock_ok={mock_ok}'); "
            "sys.exit(0 if (not torch and not st and abc_ok and mock_ok) else 1)"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
            cwd="C:/dev/proyects/flow-engineering",
        )
        assert result.returncode == 0, (
            f"Lazy import violated:\nstdout={result.stdout}\nstderr={result.stderr}"
        )
        assert "torch=False" in result.stdout
        assert "st=False" in result.stdout

    def test_module_is_already_loaded_no_extra_imports(self) -> None:
        # Within a normal pytest run, importing the module is idempotent.
        # This test ensures the side-effect scan above doesn't poison us.
        import flow_engineering.embedding_provider  # noqa: F401

        # torch should still not be in modules just from importing our module.
        # (We don't assert absence here because some other test in the same
        # process might have imported torch for an unrelated reason.)
        assert hasattr(EmbeddingProvider, "embed")
        assert hasattr(MockEmbeddingProvider, "embed")


# ---------------------------------------------------------------------------
# PR#2 T2.1 — SentenceTransformersProvider (lazy torch import)
# ---------------------------------------------------------------------------


def _ensure_torch_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a MagicMock for torch if it isn't installed in the test env."""
    if "torch" not in sys.modules:
        monkeypatch.setitem(sys.modules, "torch", MagicMock())


def _install_fake_sentence_transformers(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[str], list[list[str]]]:
    """Replace ``sentence_transformers`` with a deterministic fake.

    Returns ``(model_construct_log, encode_arg_log)`` so tests can assert
    that model construction only happens on first ``embed()`` and that
    subsequent calls reuse the cached model.
    """
    model_construct_log: list[str] = []
    encode_arg_log: list[list[str]] = []

    class FakeModel:
        def __init__(self, model_name: str) -> None:
            model_construct_log.append(model_name)

        def encode(self, texts, convert_to_numpy: bool = True):  # noqa: ARG002
            encode_arg_log.append(list(texts))
            arr = np.asarray(texts, dtype=object)
            if arr.size == 0:
                return np.zeros((0, EMBEDDING_DIMS), dtype=np.float32)
            return np.zeros((len(texts), EMBEDDING_DIMS), dtype=np.float32)

    mock_module = MagicMock()
    mock_module.SentenceTransformer = FakeModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", mock_module)
    return model_construct_log, encode_arg_log


class TestSentenceTransformersProviderMetadata:
    """REQ-19 T2.1 — provider metadata contract."""

    def test_class_is_exportable_from_module(self) -> None:
        # The class MUST be importable from the module — RED until impl lands.
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        assert isinstance(SentenceTransformersProvider, type)

    def test_class_is_subclass_of_embedding_provider(self) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        assert issubclass(SentenceTransformersProvider, EmbeddingProvider)

    def test_dim_attribute_is_384(self, monkeypatch) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        _install_fake_sentence_transformers(monkeypatch)
        provider = SentenceTransformersProvider("custom-model-name")
        assert provider.dim == EMBEDDING_DIMS == 384

    def test_model_version_defaults_to_all_minilm(self, monkeypatch) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        _install_fake_sentence_transformers(monkeypatch)
        provider = SentenceTransformersProvider()
        assert provider.model_version == "sentence-transformers/all-MiniLM-L6-v2"

    def test_model_version_uses_constructor_arg(self, monkeypatch) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        _install_fake_sentence_transformers(monkeypatch)
        provider = SentenceTransformersProvider("my-org/my-model")
        assert provider.model_version == "my-org/my-model"


class TestSentenceTransformersProviderMissingTorch:
    """REQ-19 T2.1 — when torch is missing, construction raises the typed error."""

    def test_raises_embedding_provider_unavailable_when_torch_missing(self, monkeypatch) -> None:
        # Patch builtins.__import__ so any ``import torch`` raises ImportError,
        # even if a cached sys.modules entry exists.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "torch" or name.startswith("torch."):
                raise ImportError(f"No module named {name!r}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.delitem(sys.modules, "torch", raising=False)
        monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)

        from flow_engineering.embedding_provider import SentenceTransformersProvider

        with pytest.raises(EmbeddingProviderUnavailable) as exc_info:
            SentenceTransformersProvider()
        msg = str(exc_info.value)
        assert "pip install flow-engineering[vectors]" in msg
        # Spec: subclass of ImportError so callers can use a single except clause.
        assert isinstance(exc_info.value, ImportError)

    def test_raises_embedding_provider_unavailable_when_sentence_transformers_missing(
        self, monkeypatch
    ) -> None:
        # If torch is present but sentence_transformers is not, still raise.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "sentence_transformers" or name.startswith("sentence_transformers."):
                raise ImportError(f"No module named {name!r}")
            return real_import(name, *args, **kwargs)

        _ensure_torch_stub(monkeypatch)
        monkeypatch.setattr(builtins, "__import__", fake_import)
        monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)

        from flow_engineering.embedding_provider import SentenceTransformersProvider

        with pytest.raises(EmbeddingProviderUnavailable) as exc_info:
            SentenceTransformersProvider()
        assert "pip install flow-engineering[vectors]" in str(exc_info.value)


class TestSentenceTransformersProviderLazyModelLoad:
    """REQ-19 T2.1 — model loading is lazy (only on first embed())."""

    def test_model_not_loaded_at_construction(self, monkeypatch) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        construct_log, _encode_log = _install_fake_sentence_transformers(monkeypatch)
        SentenceTransformersProvider("lazy-test-model")
        assert construct_log == [], f"Model loaded at construction: {construct_log}"

    def test_model_loaded_on_first_embed_call(self, monkeypatch) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        construct_log, encode_log = _install_fake_sentence_transformers(monkeypatch)
        provider = SentenceTransformersProvider("lazy-test-model")
        provider.embed(["hello", "world"])
        assert construct_log == ["lazy-test-model"], (
            f"Expected exactly one construct on first embed, got {construct_log}"
        )
        assert encode_log == [["hello", "world"]]
        assert provider._model is not None

    def test_model_cached_across_subsequent_embed_calls(self, monkeypatch) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        construct_log, encode_log = _install_fake_sentence_transformers(monkeypatch)
        provider = SentenceTransformersProvider("lazy-test-model")
        provider.embed(["first"])
        provider.embed(["second", "third"])
        provider.embed([])
        assert construct_log == ["lazy-test-model"], f"Model re-instantiated: {construct_log}"
        assert encode_log == [["first"], ["second", "third"]]

    def test_embed_returns_n_by_384(self, monkeypatch) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        _install_fake_sentence_transformers(monkeypatch)
        provider = SentenceTransformersProvider("shape-test")
        out = provider.embed(["a", "b", "c", "d", "e"])
        assert isinstance(out, np.ndarray)
        assert out.shape == (5, EMBEDDING_DIMS)
        assert out.dtype == np.float32

    def test_embed_empty_list_returns_zero_384(self, monkeypatch) -> None:
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        _install_fake_sentence_transformers(monkeypatch)
        provider = SentenceTransformersProvider("shape-test")
        out = provider.embed([])
        assert out.shape == (0, EMBEDDING_DIMS)
        assert out.dtype == np.float32

    def test_embed_batch_delegates_to_embed(self, monkeypatch) -> None:
        # Default EmbeddingProvider.embed_batch delegates to embed() — verify
        # that sentence-transformers impl inherits that contract.
        from flow_engineering.embedding_provider import SentenceTransformersProvider

        _ensure_torch_stub(monkeypatch)
        _install_fake_sentence_transformers(monkeypatch)
        provider = SentenceTransformersProvider("batch-test")
        out_single = provider.embed(["x", "y"])
        out_batch = provider.embed_batch(["x", "y"])
        assert out_single.shape == out_batch.shape == (2, EMBEDDING_DIMS)


class TestSentenceTransformersProviderModuleImportClean:
    """REQ-19 T2.1 — defining the class MUST NOT import torch at module level."""

    def test_subprocess_module_import_does_not_pull_torch(self) -> None:
        # The subprocess guarantees a fresh sys.modules at import time.
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
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
            cwd="C:/dev/proyects/flow-engineering",
        )
        assert result.returncode == 0, (
            f"Module-level import leaked heavy deps:\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
        assert "torch=False" in result.stdout
        assert "st=False" in result.stdout
        assert "has_st=True" in result.stdout
