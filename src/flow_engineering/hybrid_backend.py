"""HybridBackend composition wrapper (vector-semantic-search PR#1 T1.4 + T1.5 + T1.7).

REQ-17 + REQ-18 + design D2 + D7: HybridBackend wraps any inner EngramBackend
and adds semantic / hybrid retrieval on top, without altering the legacy
prose ``mem_search`` contract.

T1.4 (batch B) introduced the composition wrapper that forwarded all
prose-path methods to ``inner`` and deferred ``mem_search_semantic`` +
``mem_search_hybrid`` with ``NotImplementedError``.

T1.5 (batch C) implements the hybrid scoring formula from design D7:

    score = α · cosine_sim + (1 − α) · normalize_bm25(fts)

where ``normalize_bm25(x) = (x − min) / (max − min + ε)`` is computed over
the FTS result set per query. ``α`` defaults to ``0.5``; valid range is
``[0.0, 1.0]``. ``mem_search_semantic`` is a thin delegate to
``mem_search_hybrid(query, k, alpha=1.0)``.

T1.7 (batch D1) wires observability — every ``mem_search_hybrid`` (and the
``mem_search_semantic`` alias) invocation emits the REQ-22 counter batch via
:func:`observability.record_vector_summary` with ``trigger="programmatic"``.
The CLI layer (PR#2 T2.4) sets ``trigger="cli"`` for its own invocations.
Sync embed-on-save (the write-through side effect on ``mem_save``) lands
in a later batch.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any

import numpy as np

from flow_engineering import observability
from flow_engineering.embedding_provider import EmbeddingProvider
from flow_engineering.engram_io import EngramBackend


class HybridBackend(EngramBackend):
    """Composition wrapper: any EngramBackend + any EmbeddingProvider.

    Forwards prose-path methods to ``inner`` unchanged. The semantic and
    hybrid methods implement the REQ-18 linear-combo formula on top of
    the FTS candidate set returned by ``inner.mem_search``.
    """

    _EPSILON: float = 1e-9

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
        # T1.5: forward only. Sync embed-on-save lands in a later batch.
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

    # --- REQ-17 + REQ-18 retrieval methods (T1.5) ---

    def mem_search_semantic(
        self, query: str, k: int = 10, *, trigger: str = "programmatic"
    ) -> list[dict[str, Any]]:
        """Pure semantic search (REQ-17). Delegates to ``mem_search_hybrid(alpha=1.0)``.

        ``trigger`` controls the observability tag (REQ-22). Defaults to
        ``"programmatic"`` for direct library use; the CLI layer passes
        ``trigger="cli"`` so dashboards can separate user invocations from
        background work.
        """
        return self.mem_search_hybrid(query, k=k, alpha=1.0, trigger=trigger)

    def mem_search_hybrid(
        self,
        query: str,
        k: int = 10,
        alpha: float = 0.5,
        *,
        trigger: str = "programmatic",
    ) -> list[dict[str, Any]]:
        """Hybrid semantic + FTS search (REQ-18, design D7 linear combo).

        Algorithm:
          1. Validate ``alpha`` in ``[0.0, 1.0]`` (else ``ValueError``).
          2. Pull FTS candidates from ``inner.mem_search(query, limit=2*k)``.
          3. Empty candidates → ``[]`` (no ``ZeroDivisionError``; ``mem_search_semantic``
             is NOT called as a fallback).
          4. Embed ``[query] + [obs.content for obs in candidates]``.
          5. ``cosine_sim`` per candidate (0.0 if either vector is zero).
          6. ``fts_score`` per candidate (``obs['_fts_score']`` if set, else
             substring count fallback).
          7. Min-max normalize FTS scores within the candidate set
             (``+ ε`` epsilon path for span=0).
          8. ``hybrid_score = alpha · cosine_sim + (1 − alpha) · normalize_bm25``.
          9. Sort desc by hybrid score; return top-``k``.

        Each result dict carries ``observation_id``, ``score``, ``rank`` per
        REQ-17 contract, plus the inner observation fields for convenience.

        Every successful invocation emits the REQ-22 vector counter batch via
        :func:`observability.record_vector_summary` with the requested
        ``trigger`` tag (``"programmatic"`` by default; ``"cli"`` when invoked
        from the CLI layer). The observability helper is fail-open (mirrors
        ``increment``) so a broken metrics sink can never break retrieval.
        """
        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"alpha must be in [0.0, 1.0], got {alpha}")

        start = time.perf_counter()
        results = self._compute_hybrid_results(query, k=k, alpha=alpha)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        with contextlib.suppress(Exception):
            # Observability MUST be fail-open — never let metrics break retrieval.
            safe_trigger = trigger if trigger in observability.VECTOR_TRIGGER_VALUES else "programmatic"
            observability.record_vector_summary(
                invoked=1,
                results_returned=len(results),
                latency_ms=elapsed_ms,
                index_size=self._safe_index_size(),
                trigger=safe_trigger,
            )
        return results

    def _compute_hybrid_results(
        self,
        query: str,
        *,
        k: int,
        alpha: float,
    ) -> list[dict[str, Any]]:
        """Inner worker for hybrid scoring (separated from observability wiring).

        Returns the ranked list. Does NOT touch metrics — callers wrap this
        with their preferred counter trigger tag.
        """
        candidates = self._inner.mem_search(query, limit=max(k * 2, k))
        if not candidates:
            return []

        # FTS scores: prefer obs['_fts_score'] if present (test/production seam),
        # else fall back to substring count of query in content+title.
        fts_scores = [self._fts_score(query, obs) for obs in candidates]
        norm_fts = self._normalize_bm25(fts_scores)

        # Embeddings: query + each candidate's content (single batched call).
        texts = [query] + [str(obs.get("content", "")) for obs in candidates]
        embeds = self._embedding_provider.embed(texts)
        q_vec = embeds[0]
        cos_sims = [self._cosine_sim(q_vec, embeds[i + 1]) for i in range(len(candidates))]

        hybrid_scores = [
            alpha * cos + (1.0 - alpha) * nf
            for cos, nf in zip(cos_sims, norm_fts, strict=True)
        ]

        # Stable sort: hybrid score desc, then insertion order (candidates
        # arrive in inner.mem_search's ordering, which we preserve on ties
        # so the alpha=0.0 sanity check matches pure FTS).
        ranked = sorted(
            range(len(candidates)),
            key=lambda i: (-hybrid_scores[i], i),
        )

        top = ranked[:k]
        results: list[dict[str, Any]] = []
        for rank, idx in enumerate(top):
            obs = candidates[idx]
            base: dict[str, Any] = dict(obs)
            base["observation_id"] = obs["id"]
            base["score"] = float(hybrid_scores[idx])
            base["rank"] = rank
            results.append(base)
        return results

    def _safe_index_size(self) -> int:
        """Best-effort lookup of the current embedding index size for the gauge.

        Returns 0 when the index is unavailable (e.g. SqliteVecStore not
        yet wired up in this batch, or the inner backend is not a
        vector-enabled hybrid). The gauge is sampled at render time, so a
        zero here is the documented safe default.
        """
        index = getattr(self, "_index", None)
        if index is None:
            return 0
        count_fn = getattr(index, "count", None)
        if not callable(count_fn):
            return 0
        try:
            return int(count_fn())
        except Exception:
            return 0

    # --- helpers (exposed as staticmethods for direct unit testing) ---

    @staticmethod
    def _fts_score(query: str, obs: dict[str, Any]) -> float:
        """Derive an FTS score for ``obs`` against ``query``.

        Prefers ``obs['_fts_score']`` if present (test/production seam for
        controlling the score without a real FTS5 backend); otherwise falls
        back to a substring count over ``content + title``.
        """
        if "_fts_score" in obs:
            return float(obs["_fts_score"])
        q = query.lower()
        haystack = (str(obs.get("content", "")) + " " + str(obs.get("title", ""))).lower()
        return float(haystack.count(q))

    @staticmethod
    def _normalize_bm25(scores: list[float]) -> list[float]:
        """Min-max normalize a list of FTS scores per query (REQ-18 + D7).

        ``normalize_bm25(x) = (x − min) / (max − min + ε)``. Returns ``[]``
        for empty input and ``[0.0, ...]`` when ``span < ε`` (epsilon path
        prevents ``ZeroDivisionError``).
        """
        if not scores:
            return []
        s_min = min(scores)
        s_max = max(scores)
        span = s_max - s_min
        if span < HybridBackend._EPSILON:
            return [0.0 for _ in scores]
        return [(s - s_min) / span for s in scores]

    @staticmethod
    def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity ``dot(a, b) / (norm(a) * norm(b))``.

        Returns ``0.0`` if either vector has zero norm (avoids
        ``ZeroDivisionError``; treats the missing-embedding case as no
        semantic contribution per design D11).
        """
        norm_a = float(np.linalg.norm(a))
        norm_b = float(np.linalg.norm(b))
        if norm_a < HybridBackend._EPSILON or norm_b < HybridBackend._EPSILON:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


__all__ = ["HybridBackend"]
