"""HybridBackend composition wrapper (vector-semantic-search PR#1 T1.4).

REQ-17 + REQ-18 + design D2: HybridBackend wraps any inner EngramBackend
and adds the semantic / hybrid retrieval methods on top, without altering
the legacy prose ``mem_search`` contract.

T1.4 is the SCAFFOLD layer:
- Composition (constructor accepts any EngramBackend + any EmbeddingProvider).
- Forwards the 5 prose-path methods (``mem_save``, ``mem_search``,
  ``mem_get_observation``, ``iter_observations``, ``update_observation``)
  byte-identically to ``inner``.
- Overrides ``mem_search_semantic`` and ``mem_search_hybrid`` to raise
  ``NotImplementedError`` with a clear pointer to batch C (T1.5), where the
  actual hybrid scoring formula and sync embed-on-save land.

The real implementation in T1.5 will:
- Add sync embed-on-save side effect to ``mem_save``.
- Implement ``mem_search_semantic`` against the index.
- Implement ``mem_search_hybrid`` with the linear combo formula
  ``score = α · cosine_sim + (1 − α) · normalize_bm25(fts)`` (design D7).

Why explicit forwarding instead of ``__getattr__``: mypy strict mode is
on, and explicit overrides give us static type checking + IDE help.
The surface is ~30 LOC either way.
"""

from __future__ import annotations

from typing import Any

from flow_engineering.embedding_provider import EmbeddingProvider
from flow_engineering.engram_io import EngramBackend


class HybridBackend(EngramBackend):
    """Composition wrapper: any EngramBackend + any EmbeddingProvider.

    Forwards prose-path methods to ``inner`` unchanged. The semantic and
    hybrid methods raise ``NotImplementedError`` until T1.5 (batch C) lands.
    """

    _BATCH_C_POINTER = (
        "hybrid scoring implemented in batch C (T1.5) of vector-semantic-search PR#1"
    )

    def __init__(
        self,
        inner: EngramBackend,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._inner = inner
        self._embedding_provider = embedding_provider

    # --- inner access (public for tests + observability) ---

    @property
    def inner(self) -> EngramBackend:
        """The wrapped EngramBackend. Exposed for tests, reindex, and observability."""
        return self._inner

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        """The wrapped EmbeddingProvider. Exposed for tests, reindex, and observability."""
        return self._embedding_provider

    # --- forwarded prose-path methods (REQ-17 scenario 5: byte-identical) ---

    def mem_save(
        self,
        title: str,
        content: str,
        topic_key: str,
        type: str = "manual",  # noqa: A002
        scope: str = "project",
    ) -> dict[str, Any]:
        # T1.4: forward only. T1.5 will wrap this with sync embed-on-save.
        return self._inner.mem_save(
            title=title,
            content=content,
            topic_key=topic_key,
            type=type,  # noqa: A002
            scope=scope,
        )

    def mem_search(
        self,
        query: str,
        topic_key: str | None = None,
        limit: int = 10,
        scope: str = "project",
    ) -> list[dict[str, Any]]:
        return self._inner.mem_search(
            query=query,
            topic_key=topic_key,
            limit=limit,
            scope=scope,
        )

    def mem_get_observation(self, id: int) -> dict[str, Any]:  # noqa: A002
        return self._inner.mem_get_observation(id)  # noqa: A002

    def iter_observations(self, *, project: str | None = None) -> list[dict[str, Any]]:
        return self._inner.iter_observations(project=project)

    def update_observation(
        self,
        id: int,  # noqa: A002
        *,
        content: str | None = None,
        type: str | None = None,  # noqa: A002
    ) -> dict[str, Any]:
        return self._inner.update_observation(id, content=content, type=type)  # noqa: A002

    # --- deferred methods (T1.5 / batch C) ---

    def mem_search_semantic(
        self, query: str, k: int = 10
    ) -> list[dict[str, Any]]:
        """Semantic search (REQ-17, REQ-18). Defer to batch C (T1.5)."""
        raise NotImplementedError(self._BATCH_C_POINTER)

    def mem_search_hybrid(
        self,
        query: str,
        k: int = 10,
        alpha: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Hybrid semantic + BM25 search (REQ-18, D7 linear combo). Defer to batch C (T1.5)."""
        raise NotImplementedError(self._BATCH_C_POINTER)


__all__ = ["HybridBackend"]
