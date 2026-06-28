"""SqliteVecStore: sqlite-vec KNN index for vector-semantic-search (REQ-20).

REQ-20 contract:
- Two cooperating tables: ``observation_embeddings`` (audit row with float32
  BLOB of size 1536 bytes = 384 floats × 4 bytes) + ``vec_observations`` (a
  sqlite-vec ``vec0`` virtual table for KNN).
- ``observation_id`` is **TEXT** (consistent with Engram SQLite prose storage
  per spec #142 D20 schema).
- Writes wrapped in transactions — partial failure rolls back the batch.
- Lazy import of ``sqlite_vec`` (mirrors the embedding-provider lazy torch
  contract). Missing extra raises :class:`ImportError` with the install hint.

The class is deliberately small and dependency-light so it can be reused by
both the embed-on-save write-through (HybridBackend, future batch) and the
``flow reindex`` command (PR#2 T2.5).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

# Lazy sqlite-vec import. Module-level ``import sqlite_vec`` would break the
# default-install contract (REQ-19 scenario 2). Tests that need the actual
# KNN machinery use ``pytest.importorskip("sqlite_vec")`` so missing extra
# produces a clean skip, not a collection error.
try:
    import sqlite_vec
except ImportError:  # pragma: no cover - covered via monkeypatch test
    sqlite_vec = None


VECTOR_DIM: int = 384
BLOB_SIZE: int = VECTOR_DIM * 4  # float32 = 4 bytes; 384 × 4 = 1536 bytes
DEFAULT_MODEL_VERSION: str = "all-MiniLM-L6-v2"

_INSTALL_HINT: str = "pip install flow-engineering[vectors]"


class SqliteVecStore:
    """Persist 384-dim embeddings in sqlite-vec for KNN retrieval.

    On first use, two tables are created:

    - ``observation_embeddings`` (regular audit row):
        ``observation_id TEXT PRIMARY KEY,
        vector BLOB(1536), model_version TEXT, created_at TEXT``

    - ``vec_observations`` (sqlite-vec ``vec0`` virtual):
        ``observation_id TEXT PRIMARY KEY, vector FLOAT[384]``

    Both writes are wrapped in a single SQLite transaction so a partial
    failure rolls back the entire batch (no half-written rows).

    The class is constructible with either a real file path or the special
    ``":memory:"`` path for fast isolated tests.
    """

    def __init__(self, db_path: Path) -> None:
        if sqlite_vec is None:
            raise ImportError(
                f"sqlite-vec is required for SqliteVecStore. "
                f"Install with: {_INSTALL_HINT}"
            )
        path_str = str(db_path)
        self._db_path: str = path_str
        self._conn: Any | None = None
        # Lazy connection: open + create schema on first DB touch.
        self._ensure_conn()

    # ---------- connection lifecycle ----------

    def _ensure_conn(self) -> Any:
        """Open the SQLite connection (lazy) and create the schema if needed."""
        if self._conn is not None:
            return self._conn
        import sqlite3

        conn = sqlite3.connect(self._db_path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        # Foreign keys are off by default in sqlite3 — we don't need them
        # here because the two tables share a TEXT PK and writes are
        # co-located in a transaction.
        self._create_schema(conn)
        self._conn = conn
        return conn

    @staticmethod
    def _create_schema(conn: Any) -> None:
        """Create the two cooperating tables if they don't exist yet."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observation_embeddings (
                observation_id TEXT PRIMARY KEY,
                vector BLOB(1536) NOT NULL,
                model_version TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_observations
            USING vec0(
                observation_id TEXT PRIMARY KEY,
                vector FLOAT[384]
            )
            """
        )
        conn.commit()

    # ---------- public API ----------

    def add(
        self,
        obs_id: str,
        vector: np.ndarray,
        *,
        model_version: str = DEFAULT_MODEL_VERSION,
    ) -> None:
        """Upsert one observation's embedding.

        Writes both the audit row and the vec0 row in a single transaction.
        Re-adding an existing ``obs_id`` replaces both rows (idempotent under
        REQ-21 scenario 3 — ``flow reindex`` is no-op on a fully-indexed corpus).

        The vec0 virtual table does NOT support ``INSERT OR REPLACE``, so we
        try ``UPDATE`` first; if no row matches (rowcount == 0), we ``INSERT``
        a fresh row. The regular audit table supports ``INSERT OR REPLACE``
        directly.
        """
        vec_bytes = self._encode_vector(vector)
        conn = self._ensure_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO observation_embeddings"
                "(observation_id, vector, model_version, created_at) "
                "VALUES (?, ?, ?, ?)",
                (obs_id, vec_bytes, model_version, _now_iso()),
            )
            cur = conn.execute(
                "UPDATE vec_observations SET vector = ? WHERE observation_id = ?",
                (vec_bytes, obs_id),
            )
            if cur.rowcount == 0:
                conn.execute(
                    "INSERT INTO vec_observations"
                    "(observation_id, vector) VALUES (?, ?)",
                    (obs_id, vec_bytes),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def search(self, vector: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        """Return up to ``k`` ``(observation_id, distance)`` tuples.

        Ordered by ascending distance. Empty store returns ``[]``. When the
        store contains fewer than ``k`` observations, returns all of them.
        """
        conn = self._ensure_conn()
        query_bytes = self._encode_vector(vector)
        rows = conn.execute(
            "SELECT observation_id, distance FROM vec_observations "
            "WHERE vector MATCH ? ORDER BY distance LIMIT ?",
            (query_bytes, int(k)),
        ).fetchall()
        return [(str(obs_id), float(distance)) for obs_id, distance in rows]

    def delete(self, obs_id: str) -> None:
        """Remove an observation from both tables atomically.

        No-op when ``obs_id`` is absent — idempotent for crash-resume safety
        (REQ-21 scenario 5). Failure during the delete rolls back the whole
        transaction so the index is never left half-deleted.
        """
        conn = self._ensure_conn()
        try:
            conn.execute(
                "DELETE FROM observation_embeddings WHERE observation_id = ?",
                (obs_id,),
            )
            conn.execute(
                "DELETE FROM vec_observations WHERE observation_id = ?",
                (obs_id,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def count(self) -> int:
        """Return the number of indexed observations."""
        conn = self._ensure_conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM observation_embeddings"
        ).fetchone()
        return int(row[0])

    # ---------- helpers ----------

    @staticmethod
    def _encode_vector(vector: np.ndarray) -> bytes:
        """Serialize a ``(384,)`` float32 vector to a 1536-byte buffer.

        The sqlite-vec virtual table accepts the same byte representation
        that we persist in the audit BLOB column — one canonical encoding
        across the index, so a vector round-trips losslessly (REQ-20
        scenario 4: tolerance 1e-6).
        """
        arr = np.asarray(vector, dtype=np.float32).reshape(-1)
        if arr.shape[0] != VECTOR_DIM:
            raise ValueError(
                f"vector must be {VECTOR_DIM}-dim float32, got shape {arr.shape}"
            )
        return arr.tobytes()


def _now_iso() -> str:
    """Return UTC time as ISO 8601 with ``Z`` suffix."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "SqliteVecStore",
    "VECTOR_DIM",
    "BLOB_SIZE",
    "DEFAULT_MODEL_VERSION",
]
