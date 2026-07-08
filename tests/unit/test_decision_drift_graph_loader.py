"""Unit tests for the GraphLoader Protocol + adapters (REQ-DRIFT-DETECTION-1..4 + REQ-DRIFT-DETECTION-8).

Slice 1 of the drift-detection change. The Protocol seam replaces the
inline graph-load plumbing inside ``decision_drift.scan_change`` so future
slices (OTel push, cross-project federation, per-finding graph_unavailable)
can plug into the new seam without touching the pure classifier.

RED → GREEN → REFACTOR cycle per the Strict-TDD posture (constitution
Article III + ``sdd-init/flow-engineering.md`` ``strict_tdd: true``).

The tests accumulate across batches:

- **Batch 1** (T1.1 + T1.2a + T1.2b): Protocol-contract + 2 live-disk +
  2 snapshot adapter behavior tests.
- **Batch 3** (T3.1 + T3.2): 4 exception-population tests for the typed
  hierarchy (``GraphLoadError`` + 4 siblings).
- **Batch 4** (T4.1): 2 identity tests for the PEP 562 re-export of
  ``SnapshotGraphMissing`` from canonical ``snapshot_manager``.
- **Batch 5** (T5.1 + T5.2): 2 ``unable_reason`` mapping tests + 1
  negative-imports test (``_DummyBackend`` removed).
- **Batch 6** (T6.1a + T6.2): 2 dispatch tests for ``_build_loader`` +
  2 byte-identical ``DriftReport`` invariant tests.

This file is INTENTIONALLY co-located with the legacy
``tests/unit/test_decision_drift.py`` (the strict regression gate) so the
``git diff origin/main..HEAD -- tests/`` check at T7.2 stays focused on
the existing test files only — these are new files, not modifications.
"""

from __future__ import annotations

from typing import Protocol as _Protocol

import pytest

# ---------- T1.1 — Protocol-contract tests (4 tests, RED → GREEN) ----------


class TestGraphLoaderProtocol:
    """REQ-DRIFT-DETECTION-1: ``GraphLoader`` is a narrow Protocol with a single
    ``load(self)`` method. Concrete adapters (``LiveDiskGraphLoader``,
    ``SnapshotGraphLoader``) implement it; the seam lets future slices plug
    into ``scan_change`` without touching the pure classifier.
    """

    def test_graph_loader_is_importable_from_drift_graph_loader(self) -> None:
        """RED: this import MUST fail with ``ModuleNotFoundError`` until
        ``src/flow_engineering/drift_graph_loader.py`` lands at T1.2a.
        """
        from flow_engineering.drift_graph_loader import GraphLoader  # noqa: F401

        assert GraphLoader is not None

    def test_graph_loader_is_a_typing_protocol(self) -> None:
        """Protocols in this codebase are ``typing.Protocol`` subclasses
        (not ``abc.ABC``). The check uses ``issubclass`` against the
        Protocol meta so the assertion is import-order independent.
        """
        from flow_engineering.drift_graph_loader import GraphLoader

        assert issubclass(GraphLoader, _Protocol)

    def test_graph_loader_declares_only_load_method(self) -> None:
        """REQ-DRIFT-DETECTION-1: the Protocol declares ONLY ``load(self)``.
        ``dir()`` is used because Protocol method discovery goes through
        ``_abc`` at runtime; the public attribute surface is what the
        Protocol CONTRACTS to consumers.
        """
        from flow_engineering.drift_graph_loader import GraphLoader

        declared_methods = {
            name
            for name in dir(GraphLoader)
            if not name.startswith("_")
            and callable(getattr(GraphLoader, name, None))
        }
        assert declared_methods == {"load"}, (
            f"GraphLoader Protocol must declare ONLY the load() method; "
            f"found extra methods: {declared_methods - {'load'}}"
        )

    def test_graph_loader_is_runtime_checkable(self) -> None:
        """REQ-DRIFT-DETECTION-1 scenario 1: ``isinstance(obj, GraphLoader)``
        must succeed at runtime so the ``scan_change`` adapter-compat layer
        can dispatch via ``isinstance(loader, SnapshotGraphLoader)`` style
        checks without a separate registration step.
        """
        from flow_engineering.drift_graph_loader import GraphLoader

        class _StubLoader:
            def load(self) -> tuple[dict | None, dict | None, float | None]:  # type: ignore[type-arg]
                return (None, None, None)

        assert isinstance(_StubLoader(), GraphLoader), (
            "GraphLoader must be @runtime_checkable so isinstance() works "
            "without explicit Protocol registration"
        )


# ---------- T1.2a — LiveDiskGraphLoader behavior (2 tests, RED → GREEN) ----------


class TestLiveDiskGraphLoader:
    """REQ-DRIFT-DETECTION-1 scenarios 1 + 2: the live-disk adapter reads
    ``graph.json`` from disk and returns the same 3-tuple shape as the
    legacy ``decision_drift.load_graph`` happy path. Raises the typed
    ``GraphMissing`` exception when the path is absent (replaces the
    bare ``return (None, None, None)`` fail-open at
    ``decision_drift.py:238``).
    """

    def test_live_disk_loader_returns_index_tuple_on_valid_graph(
        self, tmp_path,
    ) -> None:
        """Happy path: a 2-node ``graph.json`` fixture returns
        ``(current_nodes, current_id_map, mtime)`` matching the legacy
        ``TestLoadGraph::test_load_graph_returns_index_tuple`` shape
        byte-for-byte (modulo ``mtime`` epoch value).
        """
        import json as _json

        from flow_engineering.drift_graph_loader import LiveDiskGraphLoader

        graph_path = tmp_path / "graph.json"
        graph_path.write_text(
            _json.dumps(
                {
                    "nodes": [
                        {
                            "id": "alpha",
                            "label": "AlphaNode",
                            "file": "src/alpha.py",
                            "line": 10,
                        },
                        {
                            "id": "beta",
                            "label": "BetaNode",
                            "file": "src/beta.py",
                            "line": 20,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        loader = LiveDiskGraphLoader(graph_path)
        current_nodes, current_id_map, mtime = loader.load()

        assert isinstance(current_nodes, dict)
        assert isinstance(current_id_map, dict)
        assert isinstance(mtime, float)
        assert mtime > 0
        assert set(current_nodes) == {"alpha", "beta"}
        assert current_id_map["alpha"] == ("src/alpha.py", 10, "AlphaNode")
        assert current_id_map["beta"] == ("src/beta.py", 20, "BetaNode")

    def test_live_disk_loader_raises_graph_missing_on_absent_path(
        self, tmp_path,
    ) -> None:
        """REQ-DRIFT-DETECTION-1 scenario 2: when ``graph_json_path``
        points at a non-existent file, ``GraphMissing`` is raised (NOT
        the legacy ``return (None, None, None)`` fail-open). The message
        references the path so callers can render ``--graph-json=<path>``
        hints.
        """
        from flow_engineering.drift_graph_loader import (
            GraphMissing,
            LiveDiskGraphLoader,
        )

        absent = tmp_path / "does_not_exist.json"
        loader = LiveDiskGraphLoader(absent)

        with pytest.raises(GraphMissing) as exc_info:
            loader.load()

        assert str(absent) in str(exc_info.value)


# ---------- T1.2b — SnapshotGraphLoader behavior (2 tests, RED → GREEN) ----------


def _make_snapshot_with_graph_json(snapshots_dir, graph_nodes):
    """Build a snapshot envelope that embeds a ``graph_json_content`` string.

    Mirrors the BDD step fixture at
    ``tests/unit/test_decision_drift_snap_id.py:_seed_obs_with_binding``
    so the snapshot round-trips through ``SnapshotManager.show()``
    without sha256 verification failures.

    Returns the ``snap_id`` string. Caller is responsible for
    ``FLOW_SNAPSHOTS_DIR`` setup via ``monkeypatch``.
    """
    import gzip
    import hashlib
    import json
    import secrets
    from datetime import UTC, datetime

    from flow_engineering.engram_io import InMemoryBackend

    backend = InMemoryBackend()
    backend.mem_save(
        title="t12b-fixture",
        content="seed observation",
        topic_key="sdd/drift-detection/test",
    )

    snapshots_dir.mkdir(parents=True, exist_ok=True)

    # Build a snap_id the same way SnapshotManager._build_snapshot_id does,
    # so the file we write lands where show() looks for it.
    iso = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
    snap_id = f"snap_{iso}-{secrets.token_hex(3)}"

    envelope: dict = {
        "schema": 1,
        "id": snap_id,
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trigger": "manual",
        "description": "t12b-fixture",
        "graph_state": {
            "observations": [],
            "project_tags": {},
            "graph_json_content": json.dumps({"nodes": graph_nodes}),
        },
        "metadata": {
            "obs_count": 0,
            "project_count": 0,
            "file_size_bytes": 0,
            "sha256": "",
            "include_graph": True,
        },
    }

    meta_for_hash = {k: v for k, v in envelope["metadata"].items() if k != "sha256"}
    envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
    envelope_for_hash["metadata"] = meta_for_hash
    canonical = json.dumps(
        envelope_for_hash, ensure_ascii=False,
        sort_keys=True, separators=(",", ":"),
    )
    envelope["metadata"]["sha256"] = hashlib.sha256(
        canonical.encode("utf-8"),
    ).hexdigest()
    canonical_bytes = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    envelope["metadata"]["file_size_bytes"] = len(canonical_bytes)
    meta_for_hash = {k: v for k, v in envelope["metadata"].items() if k != "sha256"}
    envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
    envelope_for_hash["metadata"] = meta_for_hash
    envelope["metadata"]["sha256"] = hashlib.sha256(
        json.dumps(envelope_for_hash, ensure_ascii=False,
                   sort_keys=True, separators=(",", ":")).encode("utf-8"),
    ).hexdigest()
    final_bytes = gzip.compress(
        json.dumps(envelope, ensure_ascii=False).encode("utf-8"), mtime=0,
    )
    (snapshots_dir / f"{snap_id}.json.gz").write_bytes(final_bytes)
    return snap_id


class TestSnapshotGraphLoader:
    """REQ-DRIFT-DETECTION-1 scenario 3: ``SnapshotGraphLoader`` reads the
    frozen ``graph_state.graph_json_content`` from a snapshot envelope
    via ``SnapshotManager.show()`` and returns the same 3-tuple shape
    as the live-disk path.

    Replaces the legacy ``_DummyBackend()`` stub at
    ``decision_drift.py:311`` — the new design passes ``backend=None``
    to ``SnapshotManager`` because ``show()`` does NOT touch the
    backend.
    """

    def test_snapshot_loader_round_trips_frozen_graph_content(
        self, tmp_path, monkeypatch,
    ) -> None:
        """Happy path: a snapshot envelope with ``graph_json_content``
        returns ``(current_nodes, current_id_map, mtime)`` matching the
        legacy ``_load_graph_from_snapshot`` shape.
        """
        from flow_engineering.drift_graph_loader import SnapshotGraphLoader

        snapshots_dir = tmp_path / "snaps"
        monkeypatch.setenv("FLOW_SNAPSHOTS_DIR", str(snapshots_dir))

        snap_id = _make_snapshot_with_graph_json(
            snapshots_dir,
            [
                {"id": "gamma", "label": "Gamma", "file": "src/gamma.py", "line": 7},
                {"id": "delta", "label": "Delta", "file": "src/delta.py", "line": 14},
            ],
        )

        loader = SnapshotGraphLoader(snap_id)
        current_nodes, current_id_map, mtime = loader.load()

        assert current_nodes is not None
        assert current_id_map is not None
        assert set(current_nodes) == {"gamma", "delta"}
        assert current_id_map["gamma"] == ("src/gamma.py", 7, "Gamma")
        assert current_id_map["delta"] == ("src/delta.py", 14, "Delta")
        # mtime is the synthetic ``file_size_bytes`` value from the envelope
        # (opaque audit-correlation marker; only non-emptiness is required).
        assert mtime is not None
        assert mtime >= 0

    def test_snapshot_loader_raises_envelope_corrupt_on_bad_sha(
        self, tmp_path, monkeypatch,
    ) -> None:
        """Corrupt envelope (sha256 mismatch) raises
        ``SnapshotEnvelopeCorrupt`` — NOT the legacy fail-open
        ``(None, None, None)`` swallow at
        ``decision_drift._load_graph_from_snapshot:314-315``.
        """
        import gzip
        import json

        from flow_engineering.drift_graph_loader import (
            SnapshotEnvelopeCorrupt,
            SnapshotGraphLoader,
        )

        snapshots_dir = tmp_path / "snaps_corrupt"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("FLOW_SNAPSHOTS_DIR", str(snapshots_dir))

        # Write a malformed envelope: schema=1 + wrong sha256 stamp so
        # SnapshotManager.show() raises SnapshotEnvelopeError BEFORE the
        # loader can return None.
        envelope = {
            "schema": 1,
            "id": "snap_corrupt",
            "created_at": "2026-07-08T00:00:00Z",
            "trigger": "manual",
            "description": "t12b-corrupt",
            "graph_state": {"observations": [], "project_tags": {}},
            "metadata": {
                "obs_count": 0,
                "project_count": 0,
                "file_size_bytes": 0,
                "sha256": "deadbeef" * 8,  # intentionally wrong
                "include_graph": True,
            },
        }
        (snapshots_dir / "snap_corrupt.json.gz").write_bytes(
            gzip.compress(
                json.dumps(envelope, ensure_ascii=False).encode("utf-8"),
                mtime=0,
            )
        )

        loader = SnapshotGraphLoader("snap_corrupt")

        with pytest.raises(SnapshotEnvelopeCorrupt) as exc_info:
            loader.load()

        assert "snap_corrupt" in str(exc_info.value)


# ---------- T3.1 — Typed exception hierarchy tests (4 tests, RED → GREEN) ----------


class TestTypedExceptionHierarchy:
    """REQ-DRIFT-DETECTION-4: 4 typed exceptions (``GraphMissing``,
    ``GraphMalformed``, ``PermissionDenied``, ``SnapshotEnvelopeCorrupt``)
    inheriting from a common base ``GraphLoadError(Exception)``. The 4 are
    siblings (NOT parent-child) — the 4 failure modes are mutually
    exclusive.

    The classes live in a dedicated ``drift_exceptions.py`` module (per
    user's task D10 override of the design's co-location choice —
    design.md §2 had them co-located in ``drift_graph_loader.py``).
    """

    def test_graph_load_error_is_exception_subclass(self) -> None:
        from flow_engineering.drift_exceptions import GraphLoadError

        # Base class inherits from Exception (NOT RuntimeError or ValueError)
        # so it doesn't collide with SnapshotGraphMissing (Exception since v1.1.6).
        assert issubclass(GraphLoadError, Exception)
        assert not issubclass(GraphLoadError, RuntimeError)
        assert not issubclass(GraphLoadError, ValueError)

    def test_typed_exceptions_are_siblings_under_base(self) -> None:
        from flow_engineering.drift_exceptions import (
            GraphLoadError,
            GraphMalformed,
            GraphMissing,
            PermissionDenied,
            SnapshotEnvelopeCorrupt,
        )

        # All 4 inherit from GraphLoadError.
        for cls in (GraphMissing, GraphMalformed, PermissionDenied, SnapshotEnvelopeCorrupt):
            assert issubclass(cls, GraphLoadError), (
                f"{cls.__name__} must inherit from GraphLoadError"
            )
        # But siblings — no parent-child between them.
        assert not issubclass(GraphMissing, GraphMalformed)
        assert not issubclass(GraphMalformed, GraphMissing)
        assert not issubclass(PermissionDenied, GraphMissing)
        assert not issubclass(SnapshotEnvelopeCorrupt, GraphMissing)

    def test_typed_exceptions_carry_message(self) -> None:
        from flow_engineering.drift_exceptions import (
            GraphMissing,
            PermissionDenied,
            SnapshotEnvelopeCorrupt,
        )

        # Each carries a human-readable message referencing the
        # path/snap_id so callers can render structured CLI errors.
        missing = GraphMissing("graph file not found: /tmp/g.json")
        denied = PermissionDenied("graph file unreadable: /tmp/g.json (errno=13)")
        corrupt = SnapshotEnvelopeCorrupt("snapshot envelope corrupt: snap_id='abc'")

        assert "graph file not found" in str(missing)
        assert "/tmp/g.json" in str(missing)
        assert "errno=13" in str(denied)
        assert "snap_id='abc'" in str(corrupt)

    def test_typed_exceptions_all_inherit_from_exception(self) -> None:
        """REQ-DRIFT-DETECTION-4: all 4 inherit from ``Exception`` (NOT
        ``RuntimeError`` or ``ValueError``). This keeps the type system
        orthogonal to ``SnapshotGraphMissingError(Exception)`` (the D2
        graceful degradation signal since v1.1.6).
        """
        from flow_engineering.drift_exceptions import (
            GraphLoadError,
            GraphMalformed,
            GraphMissing,
            PermissionDenied,
            SnapshotEnvelopeCorrupt,
        )

        for cls in (GraphLoadError, GraphMissing, GraphMalformed, PermissionDenied, SnapshotEnvelopeCorrupt):
            assert issubclass(cls, Exception), (
                f"{cls.__name__} must inherit from Exception"
            )
