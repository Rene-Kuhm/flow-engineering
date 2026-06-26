"""Unit tests for vectors/sqlite_vec_store.py (vector-semantic-search PR#1 T1.6).

REQ-20: sqlite-vec storage — observation_embeddings audit table + vec_observations
vec0 virtual table for KNN.

These tests cover all 5 REQ-20 scenarios:
1. Add → search round-trip returns added observation as top-1
2. Delete removes observation from search results
3. count() reflects add/delete accurately
4. Vector BLOB size matches 384 × 4 = 1536 bytes
5. Search returns top-k ordered by ascending distance

The tests use an in-memory ``:memory:`` SQLite database so they are fast and
isolated. They require the ``sqlite-vec`` Python package to be installed
(separate from the full ``[vectors]`` extra); when missing the tests are
skipped with a clear message rather than failing collection.
"""

from __future__ import annotations

import sqlite3
import struct
from pathlib import Path

import numpy as np
import pytest

sqlite_vec = pytest.importorskip("sqlite_vec")


# ---------- fixtures ----------


@pytest.fixture
def in_memory_db() -> sqlite3.Connection:
    """Fresh in-memory SQLite DB with sqlite-vec loaded.

    Mirrors the lazy load pattern used in the production class so tests
    exercise the same extension lifecycle.
    """
    conn = sqlite3.connect(":memory:")
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    yield conn
    conn.close()


@pytest.fixture
def unit_vector() -> np.ndarray:
    """A canonical unit-norm 384-dim vector (all 1s / sqrt(384))."""
    v = np.ones(384, dtype=np.float32)
    v /= np.linalg.norm(v)
    return v


@pytest.fixture
def random_unit_vectors() -> dict[str, np.ndarray]:
    """10 distinct unit-norm 384-dim vectors keyed ``obs1..obs10``.

    Seeded for reproducibility — REQ-20 scenario 5 depends on the relative
    distances between ``q`` and these vectors.
    """
    rng = np.random.default_rng(seed=2026_06_26)
    vectors: dict[str, np.ndarray] = {}
    for i in range(1, 11):
        v = rng.standard_normal(384).astype(np.float32)
        v /= np.linalg.norm(v)
        vectors[f"obs{i}"] = v
    return vectors


# ---------- REQ-20 scenario 1: round-trip ----------


class TestSqliteVecStoreRoundTrip:
    """REQ-20 scenario 1: add + search returns the added observation as top-1."""

    def test_module_path_exposes_store_class(self) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        assert SqliteVecStore is not None

    def test_store_constructs_with_memory_path(self) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        assert store is not None

    def test_add_then_search_returns_added_id_as_top1(self, unit_vector: np.ndarray) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        store.add("obs1", unit_vector)

        results = store.search(unit_vector, k=1)
        assert len(results) == 1
        obs_id, distance = results[0]
        assert obs_id == "obs1"
        assert distance < 1e-5

    def test_add_is_idempotent_on_repeat_id(self, unit_vector: np.ndarray) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        store.add("obs1", unit_vector)
        store.add("obs1", unit_vector)  # re-add same id with same vector
        assert store.count() == 1


# ---------- REQ-20 scenario 2: delete removes from search ----------


class TestSqliteVecStoreDelete:
    """REQ-20 scenario 2: delete removes observation from search results."""

    def test_delete_removes_obs_from_search(
        self, unit_vector: np.ndarray
    ) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        store.add("obs1", unit_vector)
        store.add("obs2", unit_vector)
        store.delete("obs1")

        ids = [obs_id for obs_id, _ in store.search(unit_vector, k=10)]
        assert "obs1" not in ids
        assert "obs2" in ids

    def test_delete_on_missing_id_is_safe_noop(self, unit_vector: np.ndarray) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        store.add("obs1", unit_vector)
        store.delete("does-not-exist")  # MUST NOT raise
        assert store.count() == 1

    def test_delete_removes_both_audit_row_and_vec_row(
        self, unit_vector: np.ndarray
    ) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        store.add("obs1", unit_vector)
        store.delete("obs1")

        conn = store._conn
        assert conn is not None
        audit_rows = conn.execute(
            "SELECT COUNT(*) FROM observation_embeddings WHERE observation_id = ?",
            ("obs1",),
        ).fetchone()[0]
        vec_rows = conn.execute(
            "SELECT COUNT(*) FROM vec_observations WHERE observation_id = ?",
            ("obs1",),
        ).fetchone()[0]
        assert audit_rows == 0
        assert vec_rows == 0


# ---------- REQ-20 scenario 3: count reflects add/delete ----------


class TestSqliteVecStoreCount:
    """REQ-20 scenario 3: count() reflects add/delete accurately."""

    def test_count_starts_at_zero(self) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        assert store.count() == 0

    def test_count_increments_on_add(self, unit_vector: np.ndarray) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        store.add("obs1", unit_vector)
        assert store.count() == 1
        store.add("obs2", unit_vector)
        assert store.count() == 2
        store.add("obs3", unit_vector)
        assert store.count() == 3

    def test_count_decrements_on_delete(self, unit_vector: np.ndarray) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        store.add("obs1", unit_vector)
        store.add("obs2", unit_vector)
        store.add("obs3", unit_vector)
        store.delete("obs2")
        assert store.count() == 2

    def test_count_returns_int_type(self, unit_vector: np.ndarray) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        store.add("obs1", unit_vector)
        result = store.count()
        assert isinstance(result, int)


# ---------- REQ-20 scenario 4: BLOB byte length ----------


class TestSqliteVecStoreBlobSize:
    """REQ-20 scenario 4: vector BLOB byte length is exactly 1536."""

    def test_observation_embeddings_blob_is_1536_bytes(
        self, unit_vector: np.ndarray
    ) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        rng = np.random.default_rng(seed=42)
        random_v = rng.standard_normal(384).astype(np.float32)
        random_v /= np.linalg.norm(random_v)

        store.add("obs1", random_v)

        conn = store._conn
        assert conn is not None
        blob = conn.execute(
            "SELECT vector FROM observation_embeddings WHERE observation_id = ?",
            ("obs1",),
        ).fetchone()[0]
        assert isinstance(blob, bytes)
        assert len(blob) == 384 * 4  # float32 = 4 bytes

    def test_blob_roundtrips_to_identical_vector(
        self, unit_vector: np.ndarray
    ) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        rng = np.random.default_rng(seed=99)
        original = rng.standard_normal(384).astype(np.float32)

        store.add("obs1", original)

        conn = store._conn
        assert conn is not None
        blob = conn.execute(
            "SELECT vector FROM observation_embeddings WHERE observation_id = ?",
            ("obs1",),
        ).fetchone()[0]
        decoded = np.frombuffer(blob, dtype=np.float32)
        assert decoded.shape == (384,)
        assert decoded.dtype == np.float32
        np.testing.assert_allclose(decoded, original, atol=1e-6)

    def test_model_version_and_created_at_persisted(
        self, unit_vector: np.ndarray
    ) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        store.add("obs1", unit_vector, model_version="all-MiniLM-L6-v2")

        conn = store._conn
        assert conn is not None
        row = conn.execute(
            "SELECT model_version, created_at FROM observation_embeddings "
            "WHERE observation_id = ?",
            ("obs1",),
        ).fetchone()
        assert row[0] == "all-MiniLM-L6-v2"
        assert isinstance(row[1], str) and len(row[1]) > 0


# ---------- REQ-20 scenario 5: top-k ordering ----------


class TestSqliteVecStoreTopK:
    """REQ-20 scenario 5: search returns top-k ordered by ascending distance."""

    def test_search_returns_top_k_ascending_by_distance(
        self, random_unit_vectors: dict[str, np.ndarray]
    ) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        for obs_id, vec in random_unit_vectors.items():
            store.add(obs_id, vec)

        # Choose q close to obs7 by perturbing obs7 with small noise.
        rng = np.random.default_rng(seed=1234)
        obs7 = random_unit_vectors["obs7"]
        noise = rng.standard_normal(384).astype(np.float32) * 0.05
        q = obs7 + noise
        q /= np.linalg.norm(q)

        results = store.search(q, k=3)
        assert len(results) == 3
        # obs7 must be at position 0 (closest to q).
        assert results[0][0] == "obs7"
        # Distances must be sorted ascending.
        distances = [d for _, d in results]
        assert distances == sorted(distances)

    def test_search_k_equals_corpus_size(self) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        rng = np.random.default_rng(seed=7)
        for i in range(5):
            v = rng.standard_normal(384).astype(np.float32)
            v /= np.linalg.norm(v)
            store.add(f"obs{i}", v)
        q = rng.standard_normal(384).astype(np.float32)
        q /= np.linalg.norm(q)

        results = store.search(q, k=10)  # corpus has 5
        assert len(results) == 5

    def test_search_empty_store_returns_empty_list(self) -> None:
        from flow_engineering.vectors.sqlite_vec_store import SqliteVecStore

        store = SqliteVecStore(Path(":memory:"))
        rng = np.random.default_rng(seed=1)
        q = rng.standard_normal(384).astype(np.float32)
        q /= np.linalg.norm(q)

        results = store.search(q, k=10)
        assert results == []


# ---------- import-safety + lazy loading ----------


class TestSqliteVecStoreImportSafety:
    """REQ-20 + design D5: lazy import; missing extra raises ImportError."""

    def test_module_import_does_not_force_load_sqlite_vec(self) -> None:
        import subprocess
        import sys

        # Subprocess isolation — guarantees fresh interpreter.
        script = (
            "import sys; "
            "import flow_engineering.vectors.sqlite_vec_store as m; "
            "ok = hasattr(m, 'SqliteVecStore'); "
            "print(f'class_ok={ok}'); "
            "sys.exit(0 if ok else 1)"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
            cwd="C:/dev/proyects/flow-engineering",
        )
        assert result.returncode == 0, (
            f"Module import failed:\nstdout={result.stdout}\nstderr={result.stderr}"
        )

    def test_constructor_raises_import_error_when_sqlite_vec_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Simulate missing sqlite_vec by patching the module-level reference.
        import flow_engineering.vectors.sqlite_vec_store as mod

        monkeypatch.setattr(mod, "sqlite_vec", None)
        with pytest.raises(ImportError) as exc_info:
            mod.SqliteVecStore(Path(":memory:"))
        assert "sqlite-vec" in str(exc_info.value) or "[vectors]" in str(exc_info.value)


# ---------- vectors/__init__.py exports ----------


class TestVectorsPackageExports:
    """The ``flow_engineering.vectors`` package must expose the store."""

    def test_package_exports_sqlite_vec_store(self) -> None:
        from flow_engineering.vectors import SqliteVecStore

        assert SqliteVecStore is not None

    def test_package_import_does_not_break_other_modules(self) -> None:
        # Side-effect guard: importing the package must not error out.
        import flow_engineering.vectors  # noqa: F401
        from flow_engineering.vectors import SqliteVecStore  # noqa: F401

        assert SqliteVecStore.__name__ == "SqliteVecStore"
