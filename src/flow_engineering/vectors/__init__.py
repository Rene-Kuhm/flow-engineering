"""Vectors package: sqlite-vec storage for vector-semantic-search (REQ-20).

Exposes :class:`SqliteVecStore` for the embed-on-save + KNN retrieval pipeline
landing in PR#1 (T1.6) and PR#2 (T2.5 reindex).

This package is **optional** — it is only loaded when ``flow_engineering.vectors``
is imported. Default ``import flow_engineering`` MUST NOT pull torch or
sqlite-vec (mirrors the ``embedding_provider`` lazy-import contract from
REQ-19).
"""

from __future__ import annotations

from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

__all__ = ["SqliteVecStore"]
