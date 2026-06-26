"""Graphify query wrapper for the `code_refs` suggester.

REQ-3 (PR#1): thin wrapper around the ``graphify query`` CLI plus a Jaccard
fallback when the binary is missing. Cache lives at
``~/.flow-engineering/graphify_cache.json`` keyed by sha1(text + graph.json
mtime). Returns ``[]`` on every error path — never raises from the save flow.

Public surface (PR#1):
- ``query_nodes(text, threshold, max_results, cache_dir)``
- ``jaccard_fallback(text, graph_json_path, top_k)``
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_CACHE_DIR: Path = Path.home() / ".flow-engineering"
DEFAULT_CACHE_FILE: str = "graphify_cache.json"
DEFAULT_TIMEOUT_SECONDS: float = 5.0
DEFAULT_THRESHOLD: float = 0.3
DEFAULT_MAX_RESULTS: int = 5


def query_nodes(
    text: str,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    max_results: int = DEFAULT_MAX_RESULTS,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> list:
    """Return up to ``max_results`` candidate CodeRefs for ``text``.

    Wraps ``graphify query <text>`` with sha1(text + graph.json mtime) caching.
    Returns ``[]`` on missing binary / missing graph.json / non-zero exit /
    timeout — never raises.
    """
    # GREEN commit implements the real wrapper; stub returns empty.
    return []


def jaccard_fallback(text: str, graph_json_path: Path, top_k: int) -> list:
    """Score nodes by Jaccard similarity of tokens.

    Used when the graphify CLI is unavailable. Returns at most ``top_k`` refs.
    """
    raise NotImplementedError("jaccard_fallback lands in GREEN commit")