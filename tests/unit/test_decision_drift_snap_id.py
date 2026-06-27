"""Unit tests for ``decision_drift.load_graph(snap_id=...)`` and
``scan_change(snap_id=...)`` extension (REQ-33, T1.4).

The seam extension is kwarg-only with ``None`` default — every existing
caller of ``load_graph(graph_json_path)`` and
``scan_change(change_name, *, graph_json_path, ...)`` MUST continue to
behave byte-identically. The new ``snap_id`` kwarg activates the
frozen-state path: snapshots own their observations + ``graph.json``
content, and the scan reads BOTH from the envelope instead of the live
backend / disk.

These tests fail RED until the GREEN commit wires the kwarg into
``src/flow_engineering/decision_drift.py``.

Coverage map (REQ-33 + D13 + D5):

1. ``load_graph(snap_id=...)`` reads frozen ``graph_state.graph_json``
   from the snapshot envelope (NOT live disk).
2. ``load_graph()`` (no kwargs, current callers) byte-identical behavior
   — NON-REGRESSION guarantee (D13).
3. ``load_graph(snap_id=X, graph_json_path=Y)`` raises ``ValueError``
   (mutual exclusion).
4. ``scan_change(snap_id=...)`` uses the snapshot's frozen
   ``graph_state.observations`` as the implicit backend.
5. ``scan_change(snap_id=X, backend=Y)`` raises ``ValueError`` (mutual
   exclusion).
6. ``scan_change()`` without ``snap_id`` byte-identical to current.
7. Snapshot's ``metadata.include_graph == False`` raises
   ``SnapshotGraphMissing`` when ``scan_change`` is invoked with that
   ``snap_id`` (D2 graceful degradation).
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import pytest

from flow_engineering.engram_io import InMemoryBackend
from flow_engineering.snapshot_manager import SnapshotManager


# ---------- Helpers ----------


def _seed_obs_with_binding(
    backend: InMemoryBackend,
    *,
    cref_id: str,
    cref_file: str,
    cref_line: int,
    cref_label: str,
    topic_key: str = "sdd/vector-semantic-search/spec",
) -> int:
    """Seed one observation carrying a single CodeRef into the backend.

    The observation's content includes a properly-formatted
    ``code_refs`` block so ``scan_change`` can parse it.
    """
    from flow_engineering.binding import CodeRef, format_code_refs_block

    cref = CodeRef(
        project="insyd",
        id=cref_id,
        label=cref_label,
        file=cref_file,
        line=cref_line,
        confidence=0.9,
        source="manual",
    )
    content = (
        "## Decision\n\nSnapshot-pinned binding.\n"
        + format_code_refs_block([cref], source="manual")
    )
    obs = backend.mem_save(
        title="snap-test/phase_0",
        content=content,
        topic_key=topic_key,
    )
    return int(obs["id"])


def _write_graph(graph_path: Path, *, nodes: list[dict[str, Any]]) -> None:
    """Write a graph.json file at ``graph_path`` with the given nodes."""
    payload = {"nodes": nodes}
    graph_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _envelope_obs_payload(
    backend: InMemoryBackend, *,
    with_include_graph: bool = True,
    nodes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a snapshot envelope with seeded backend observations.

    The caller controls whether the envelope contains the full
    ``graph_state.graph_json`` (default ON) or omits it
    (``include_graph=False`` triggers ``SnapshotGraphMissing`` in
    ``scan_change`` with ``snap_id``).
    """
    snapshots_dir = backend
    manager = SnapshotManager(snapshots_dir=snapshots_dir.snapshots_dir, backend=backend)  # type: ignore[attr-defined]
    snap_id = manager.create(description="t1.4-fixture", trigger="manual")
    # Read + amend the envelope on disk to control ``include_graph``.
    path = manager.snapshots_dir / f"{snap_id}.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        envelope = json.loads(fh.read())
    if not with_include_graph:
        envelope["graph_state"].pop("graph_json", None)
        envelope["metadata"]["include_graph"] = False
        # Rewrite without the sha256 to avoid mismatches.
        meta_for_hash = {
            k: v for k, v in envelope["metadata"].items() if k != "sha256"
        }
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = meta_for_hash
        import hashlib as _hashlib
        canonical = json.dumps(
            envelope_for_hash, ensure_ascii=False,
            sort_keys=True, separators=(",", ":"),
        )
        envelope["metadata"]["sha256"] = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps(envelope, ensure_ascii=False))
    elif nodes is not None:
        envelope["graph_state"]["graph_json"] = {"nodes": nodes}
        meta_for_hash = {
            k: v for k, v in envelope["metadata"].items() if k != "sha256"
        }
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = meta_for_hash
        import hashlib as _hashlib
        canonical = json.dumps(
            envelope_for_hash, ensure_ascii=False,
            sort_keys=True, separators=(",", ":"),
        )
        envelope["metadata"]["sha256"] = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps(envelope, ensure_ascii=False))
    return {"snap_id": snap_id, "envelope": envelope, "path": path}


# ---------- TestLoadGraphWithSnapId ----------


class TestLoadGraphWithSnapId:
    """``load_graph(snap_id=...)`` reads frozen graph.json from the envelope."""

    def test_load_graph_with_snap_id_reads_frozen_content(self, tmp_path: Path) -> None:
        from flow_engineering import decision_drift

        backend = InMemoryBackend()
        # Seed an observation so the snapshot has at least one entry.
        _seed_obs_with_binding(
            backend, cref_id="vec_store", cref_file="vectors/sqlite_vec_store.py",
            cref_line=42, cref_label="SQLiteVecStore",
        )

        # Create snapshot with custom graph.json content.
        snap_id = SnapshotManager(snapshots_dir=tmp_path / "snaps", backend=backend).create(
            description="frozen", trigger="manual",
        )
        # Rewrite envelope to embed a known graph_json.
        path = (tmp_path / "snaps") / f"{snap_id}.json.gz"
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            envelope = json.loads(fh.read())
        envelope["graph_state"]["graph_json"] = {
            "nodes": [
                {"id": "vec_store", "label": "SQLiteVecStore",
                 "file": "vectors/sqlite_vec_store.py", "line": 42},
            ]
        }
        import hashlib as _hashlib
        meta_for_hash = {
            k: v for k, v in envelope["metadata"].items() if k != "sha256"
        }
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = meta_for_hash
        canonical = json.dumps(
            envelope_for_hash, ensure_ascii=False,
            sort_keys=True, separators=(",", ":"),
        )
        envelope["metadata"]["sha256"] = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps(envelope, ensure_ascii=False))

        # Call load_graph with snap_id only (path MUST be None).
        nodes, id_map, mtime = decision_drift.load_graph(
            graph_json_path=None, snap_id=snap_id,
        )

        # Frozen graph content is loaded.
        assert nodes is not None
        assert "vec_store" in nodes
        assert id_map is not None
        assert id_map["vec_store"] == (
            "vectors/sqlite_vec_store.py", 42, "SQLiteVecStore",
        )
        assert mtime is not None  # snapshot provides a frozen mtime

    def test_load_graph_snap_id_and_path_mutual_exclusion(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering import decision_drift

        backend = InMemoryBackend()
        _seed_obs_with_binding(
            backend, cref_id="x", cref_file="x.py", cref_line=1, cref_label="X",
        )
        snap_id = SnapshotManager(snapshots_dir=tmp_path / "snaps", backend=backend).create(
            description="mx",
        )
        graph_path = tmp_path / "graph.json"
        _write_graph(graph_path, nodes=[])

        with pytest.raises(ValueError):
            decision_drift.load_graph(
                graph_json_path=graph_path, snap_id=snap_id,
            )


# ---------- TestLoadGraphNonRegression ----------


class TestLoadGraphNonRegression:
    """``load_graph(graph_json_path)`` byte-identical to pre-change (D13)."""

    def test_load_graph_default_none_byte_identical_to_pre_change(
        self, tmp_path: Path
    ) -> None:
        """Calling without snap_id returns the same shape as before the seam."""
        from flow_engineering import decision_drift

        graph_path = tmp_path / "graph.json"
        _write_graph(
            graph_path,
            nodes=[
                {"id": "alpha", "label": "Alpha",
                 "file": "src/alpha.py", "line": 10},
            ],
        )

        # No snap_id kwarg at all — pre-change signature.
        nodes, id_map, mtime = decision_drift.load_graph(graph_path)

        assert nodes is not None
        assert "alpha" in nodes
        assert id_map == {"alpha": ("src/alpha.py", 10, "Alpha")}
        assert mtime is not None and mtime > 0

    def test_load_graph_with_explicit_none_returns_same_as_default(
        self, tmp_path: Path
    ) -> None:
        """``load_graph(graph_json_path, snap_id=None)`` matches pre-change behavior."""
        from flow_engineering import decision_drift

        graph_path = tmp_path / "graph.json"
        _write_graph(graph_path, nodes=[])

        # Positional path + explicit snap_id=None.
        nodes_a, id_map_a, mtime_a = decision_drift.load_graph(
            graph_json_path=graph_path, snap_id=None,
        )
        # Pre-change positional only.
        nodes_b, id_map_b, mtime_b = decision_drift.load_graph(graph_path)

        assert nodes_a == nodes_b
        assert id_map_a == id_map_b
        # mtime is filesystem-dependent but should be the same file.
        assert mtime_a == mtime_b


# ---------- TestScanChangeWithSnapId ----------


class TestScanChangeWithSnapId:
    """``scan_change(snap_id=...)`` uses frozen observations + graph."""

    def test_scan_change_with_snap_id_uses_frozen_observations(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering import decision_drift

        backend = InMemoryBackend()
        # Seed the SNAPSHOT's observation set with one valid binding.
        _seed_obs_with_binding(
            backend,
            cref_id="vec_store",
            cref_file="vectors/sqlite_vec_store.py",
            cref_line=42,
            cref_label="SQLiteVecStore",
            topic_key="sdd/vector-semantic-search/spec",
        )
        snap_id = SnapshotManager(snapshots_dir=tmp_path / "snaps", backend=backend).create(
            description="frozen-scan",
        )
        # Inject a known graph_json matching the binding.
        path = (tmp_path / "snaps") / f"{snap_id}.json.gz"
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            envelope = json.loads(fh.read())
        envelope["graph_state"]["graph_json"] = {
            "nodes": [
                {"id": "vec_store", "label": "SQLiteVecStore",
                 "file": "vectors/sqlite_vec_store.py", "line": 42},
            ]
        }
        import hashlib as _hashlib
        meta_for_hash = {
            k: v for k, v in envelope["metadata"].items() if k != "sha256"
        }
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = meta_for_hash
        canonical = json.dumps(
            envelope_for_hash, ensure_ascii=False,
            sort_keys=True, separators=(",", ":"),
        )
        envelope["metadata"]["sha256"] = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps(envelope, ensure_ascii=False))

        # Now MUTATE live state so the binding is stale — but the scan
        # should still see the SNAPSHOT's frozen state (D5 headline).
        backend.update_observation(
            1, content=(
                "## Decision\n\nUpdated content (live, irrelevant to scan).\n"
                + "<!-- code_refs -->\n"
                + json.dumps({
                    "schema_version": 1, "source": "manual",
                    "nodes": [{
                        "id": "vec_store", "label": "STALE_LABEL",
                        "file": "vectors/sqlite_vec_store.py", "line": 42,
                        "confidence": 0.9,
                    }],
                })
            ),
        )

        report = decision_drift.scan_change(
            "vector-semantic-search",
            graph_json_path=None,
            backend=None,
            snap_id=snap_id,
        )

        # DriftReport is built from the FROZEN observation set, NOT live.
        from flow_engineering.decision_drift import DriftClass
        # The frozen observation still has the original binding, matching
        # the frozen graph_json → STILL_VALID, not LABEL_DRIFT.
        assert report.class_counts.get(DriftClass.STILL_VALID, 0) >= 1
        assert report.class_counts.get(DriftClass.LABEL_DRIFT, 0) == 0
        assert report.findings, "expected at least one frozen-state finding"

    def test_scan_change_snap_id_and_backend_mutual_exclusion(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering import decision_drift

        backend = InMemoryBackend()
        _seed_obs_with_binding(
            backend, cref_id="x", cref_file="x.py", cref_line=1, cref_label="X",
        )
        snap_id = SnapshotManager(snapshots_dir=tmp_path / "snaps", backend=backend).create(
            description="mx",
        )

        with pytest.raises(ValueError):
            decision_drift.scan_change(
                "vector-semantic-search",
                graph_json_path=None,
                backend=backend,
                snap_id=snap_id,
            )

    def test_scan_change_without_snap_id_byte_identical(
        self, tmp_path: Path
    ) -> None:
        """No ``snap_id`` ⇒ same call shape as pre-change (D13 non-breaking)."""
        from flow_engineering import decision_drift

        backend = InMemoryBackend()
        _seed_obs_with_binding(
            backend, cref_id="alpha", cref_file="src/alpha.py",
            cref_line=10, cref_label="Alpha",
            topic_key="sdd/vector-semantic-search/spec",
        )
        graph_path = tmp_path / "graph.json"
        _write_graph(
            graph_path,
            nodes=[
                {"id": "alpha", "label": "Alpha",
                 "file": "src/alpha.py", "line": 10},
            ],
        )

        report = decision_drift.scan_change(
            "vector-semantic-search",
            graph_json_path=graph_path,
            backend=backend,
        )

        from flow_engineering.decision_drift import DriftClass
        assert report.class_counts.get(DriftClass.STILL_VALID, 0) == 1
        assert report.findings[0].drift_class == DriftClass.STILL_VALID

    def test_scan_change_snap_id_missing_graph_json_raises(
        self, tmp_path: Path
    ) -> None:
        """When snapshot's ``metadata.include_graph == False``, raise ``SnapshotGraphMissing``."""
        from flow_engineering import decision_drift

        backend = InMemoryBackend()
        _seed_obs_with_binding(
            backend, cref_id="x", cref_file="x.py", cref_line=1, cref_label="X",
        )
        snap_id = SnapshotManager(snapshots_dir=tmp_path / "snaps", backend=backend).create(
            description="no-graph",
        )
        # Rewrite to omit graph_json + flip include_graph flag.
        path = (tmp_path / "snaps") / f"{snap_id}.json.gz"
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            envelope = json.loads(fh.read())
        envelope["graph_state"].pop("graph_json", None)
        envelope["metadata"]["include_graph"] = False
        import hashlib as _hashlib
        meta_for_hash = {
            k: v for k, v in envelope["metadata"].items() if k != "sha256"
        }
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = meta_for_hash
        canonical = json.dumps(
            envelope_for_hash, ensure_ascii=False,
            sort_keys=True, separators=(",", ":"),
        )
        envelope["metadata"]["sha256"] = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps(envelope, ensure_ascii=False))

        # The seam should refuse with SnapshotGraphMissing.
        with pytest.raises(decision_drift.SnapshotGraphMissing):
            decision_drift.scan_change(
                "vector-semantic-search",
                graph_json_path=None,
                backend=None,
                snap_id=snap_id,
            )