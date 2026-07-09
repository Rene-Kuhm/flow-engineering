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

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Protocol as _Protocol

import pytest

from flow_engineering.decision_drift import DriftClass
from flow_engineering.drift_graph_loader import (
    LiveDiskGraphLoader as _LiveDiskGraphLoader,
)
from flow_engineering.drift_graph_loader import (
    SnapshotGraphLoader as _SnapshotGraphLoader,
)

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
            if not name.startswith("_") and callable(getattr(GraphLoader, name, None))
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
        self,
        tmp_path,
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
        self,
        tmp_path,
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
        envelope_for_hash,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
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
        json.dumps(
            envelope_for_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8"),
    ).hexdigest()
    final_bytes = gzip.compress(
        json.dumps(envelope, ensure_ascii=False).encode("utf-8"),
        mtime=0,
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
        self,
        tmp_path,
        monkeypatch,
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
        self,
        tmp_path,
        monkeypatch,
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

        for cls in (
            GraphLoadError,
            GraphMissing,
            GraphMalformed,
            PermissionDenied,
            SnapshotEnvelopeCorrupt,
        ):
            assert issubclass(cls, Exception), f"{cls.__name__} must inherit from Exception"


# ---------- T4.1 — SnapshotGraphMissing canonical relocation (2 tests) ----------


class TestSnapshotGraphMissingReExport:
    """REQ-DRIFT-DETECTION-7: ``SnapshotGraphMissing`` is canonical at
    ``flow_engineering.snapshot_manager.SnapshotGraphMissingError`` (since
    v1.1.6). ``decision_drift.SnapshotGraphMissing`` is a PEP 562 lazy
    re-export that emits a ``DeprecationWarning`` at import time.

    (Test (b) verifies the DeprecationWarning matches the v1.1.6 wording.)
    """

    def test_snapshot_graph_missing_module_is_canonical(self) -> None:
        """The class object's ``__module__`` MUST be the canonical
        ``flow_engineering.snapshot_manager`` — NOT the deprecated
        ``flow_engineering.decision_drift``. PEP 562 ``__getattr__``
        is for module-attribute access, NOT for class identity, so the
        ``SnapshotGraphMissing IS SnapshotGraphMissingError`` invariant
        must hold.
        """
        from flow_engineering.decision_drift import SnapshotGraphMissing
        from flow_engineering.snapshot_manager import SnapshotGraphMissingError

        # Class identity is preserved (PEP 562 returns the canonical class).
        assert SnapshotGraphMissing is SnapshotGraphMissingError
        # The canonical module is snapshot_manager, NOT decision_drift.
        assert SnapshotGraphMissing.__module__ == "flow_engineering.snapshot_manager"

    def test_snapshot_graph_missing_deprecation_warning(self) -> None:
        """Importing ``decision_drift.SnapshotGraphMissing`` MUST emit a
        ``DeprecationWarning`` matching the v1.1.6 wording. The warning
        fires once per import per Python's PEP 562 cache.
        """
        import warnings as _warnings

        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            # Trigger the PEP 562 lookup.
            from flow_engineering.decision_drift import (  # noqa: F401
                SnapshotGraphMissing,
            )

        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert deprecations, (
            "Expected a DeprecationWarning when importing decision_drift.SnapshotGraphMissing"
        )
        # Wording matches v1.1.6 precedent at snapshot_manager.py:113-124.
        msg = str(deprecations[0].message)
        assert "deprecated" in msg.lower()
        assert "SnapshotGraphMissingError" in msg


# ---------- T6.1a — _build_loader dispatch tests (2 tests) ----------


class TestBuildLoaderDispatch:
    """REQ-DRIFT-DETECTION-8: ``_build_loader`` is the internal helper
    that dispatches public kwargs to a ``GraphLoader`` collaborator.

    - ``snap_id="abc"`` → ``SnapshotGraphLoader("abc")``
    - ``graph_json_path=Path("foo")`` → ``LiveDiskGraphLoader(Path("foo"))``
    - Both ``None`` → ``LiveDiskGraphLoader(DEFAULT_GRAPH_JSON)`` (raises
      ``GraphMissing`` on ``.load()`` if the default is absent)
    """

    def test_snap_id_dispatches_to_snapshot_graph_loader(self) -> None:
        from flow_engineering.decision_drift import _build_loader

        loader = _build_loader(graph_json_path=None, snap_id="snap_abc")
        assert isinstance(loader, _SnapshotGraphLoader)
        assert loader._snap_id == "snap_abc"  # noqa: SLF001

    def test_graph_json_path_dispatches_to_live_disk_loader(self) -> None:
        from pathlib import Path as _Path

        from flow_engineering.decision_drift import _build_loader

        loader = _build_loader(
            graph_json_path=_Path("foo.json"),
            snap_id=None,
        )
        assert isinstance(loader, _LiveDiskGraphLoader)
        assert loader._path == _Path("foo.json")  # noqa: SLF001


# ---------- T5.1 — unable_reason mapping tests (2 tests, RED → GREEN) ----------


class TestUnableReasonMapping:
    """REQ-DRIFT-DETECTION-6: ``scan_change`` populates
    ``DriftReport.unable_reason`` from typed ``GraphLoadError`` exceptions.

    Mapping:
    - GraphMissing → ``'graph_file_missing'``
    - GraphMalformed → ``'graph_file_malformed'``
    - PermissionDenied → ``'graph_file_unreadable'``
    - SnapshotEnvelopeCorrupt → ``'snapshot_envelope_corrupt'``
    - SnapshotGraphMissing (D2 graceful degradation) → RAISES (NOT mapped)
    """

    def test_unable_reason_is_graph_file_missing_for_missing_path(
        self,
        tmp_path,
    ) -> None:
        from flow_engineering import decision_drift

        absent = tmp_path / "does_not_exist.json"
        report = decision_drift.scan_change(
            "my-change",
            graph_json_path=absent,
        )
        assert report.graph_unavailable is True
        assert report.unable_reason == "graph_file_missing"

    def test_unable_reason_is_graph_file_malformed_for_invalid_json(
        self,
        tmp_path,
    ) -> None:
        from flow_engineering import decision_drift

        malformed = tmp_path / "graph.json"
        malformed.write_text("{not-json", encoding="utf-8")

        report = decision_drift.scan_change(
            "my-change",
            graph_json_path=malformed,
        )

        assert report.graph_unavailable is True
        assert report.unable_reason == "graph_file_malformed"

    def test_unable_reason_is_snapshot_envelope_corrupt_for_bad_sha(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        import gzip
        import json

        from flow_engineering import decision_drift

        snapshots_dir = tmp_path / "snaps_t51"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("FLOW_SNAPSHOTS_DIR", str(snapshots_dir))

        envelope = {
            "schema": 1,
            "id": "snap_corrupt_t51",
            "created_at": "2026-07-08T00:00:00Z",
            "trigger": "manual",
            "description": "t51-corrupt",
            "graph_state": {"observations": [], "project_tags": {}},
            "metadata": {
                "obs_count": 0,
                "project_count": 0,
                "file_size_bytes": 0,
                "sha256": "deadbeef" * 8,
                "include_graph": True,
            },
        }
        (snapshots_dir / "snap_corrupt_t51.json.gz").write_bytes(
            gzip.compress(
                json.dumps(envelope, ensure_ascii=False).encode("utf-8"),
                mtime=0,
            )
        )

        report = decision_drift.scan_change(
            "my-change",
            snap_id="snap_corrupt_t51",
        )
        assert report.graph_unavailable is True
        assert report.unable_reason == "snapshot_envelope_corrupt"


# ---------- T5.2 — negative-imports test for _DummyBackend (1 test) ----------


class TestDummyBackendRemoved:
    """REQ-DRIFT-DETECTION-5: `_DummyBackend` is REMOVED from
    `decision_drift.py` (the class was a fixture-as-type that existed
    only to satisfy `SnapshotManager(..., backend=...)`'s constructor).
    """

    def test_dummy_backend_not_importable_from_decision_drift(self) -> None:
        with pytest.raises(ImportError):
            from flow_engineering.decision_drift import _DummyBackend  # noqa: F401


# ---------- T6.2 — byte-identical DriftReport invariant tests (2 tests) ----------


class TestByteIdenticalDriftReport:
    """REQ-DRIFT-DETECTION-8: the post-Slice-1 ``scan_change`` produces
    a ``DriftReport`` byte-identical to the v1.2.0 baseline (modulo the
    documented ``unable_reason`` addition for failure paths).

    The 9 existing test files in the regression gate cover most fields
    implicitly. These 2 explicit tests cover the byte-identical invariant
    end-to-end on the canonical happy paths (live-disk + snapshot).
    """

    def test_live_disk_path_byte_identical_happy_path(self, tmp_path) -> None:
        import json as _json

        from flow_engineering import decision_drift
        from flow_engineering.engram_io import InMemoryBackend

        # Seed an observation with a code_refs block referencing the
        # graph node.
        cref_block = (
            "<!-- code_refs -->\n"
            '{"schema": 1, "source": "manual", "nodes": ['
            '{"project": "insyd", "id": "alpha", '
            '"label": "AlphaNode", "file": "src/alpha.py", '
            '"line": 10, "confidence": 1.0, "source": "manual"}]}\n'
        )
        backend = InMemoryBackend()
        backend.mem_save(
            title="t62-fixture",
            content=f"observation prose\n{cref_block}",
            topic_key="sdd/mychange/t62",
        )

        # Graph fixture
        graph_path = tmp_path / "graph.json"
        graph_path.write_text(
            _json.dumps(
                {
                    "nodes": [
                        {"id": "alpha", "label": "AlphaNode", "file": "src/alpha.py", "line": 10},
                    ],
                },
            ),
            encoding="utf-8",
        )

        report = decision_drift.scan_change(
            "mychange",
            graph_json_path=graph_path,
            backend=backend,
        )

        # Byte-identical invariants: graph_unavailable=False + at least
        # one STILL_VALID finding.
        assert report.graph_unavailable is False
        assert report.unable_reason is None
        assert report.decisions_total == 1
        assert report.bindings_total == 1
        assert DriftClass.STILL_VALID in report.class_counts
        assert report.class_counts[DriftClass.STILL_VALID] == 1

    def test_success_paths_match_e50adb6_baseline(self, tmp_path) -> None:
        """T6.2: compare current success-path reports against the real e50adb6 code.

        The baseline is loaded in an isolated subprocess from ``git archive`` so this
        test does not import stale modules into the current pytest process. The
        expected values are produced by the baseline implementation from the same
        fixtures; this deliberately avoids baking current output into the test.
        """

        fixed_epoch = 1_700_000_000.0
        fixtures = _build_baseline_comparison_fixtures(tmp_path)

        baseline = _run_scan_change_at_commit(
            tmp_path=tmp_path,
            commit="e50adb6",
            fixtures=fixtures,
            fixed_epoch=fixed_epoch,
        )
        current = _run_current_scan_change(fixtures=fixtures, fixed_epoch=fixed_epoch)

        assert current == baseline
        assert set(current) == {"live", "snapshot"}
        assert current["live"]["graph_unavailable"] is False
        assert current["snapshot"]["graph_unavailable"] is False

    def test_snapshot_path_byte_identical_happy_path(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        import gzip
        import hashlib
        import json
        import secrets
        from datetime import UTC, datetime

        from flow_engineering import decision_drift

        snapshots_dir = tmp_path / "snaps_t62"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("FLOW_SNAPSHOTS_DIR", str(snapshots_dir))

        # Snapshot envelope with graph_json_content (raw string).
        iso = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
        snap_id = f"snap_{iso}-{secrets.token_hex(3)}"
        obs_list = [
            {
                "id": 1,
                "topic_key": "sdd/mychange/t62",
                "content": "observation prose\n<!-- code_refs -->\n"
                '{"schema": 1, "source": "manual", "nodes": ['
                '{"project": "insyd", "id": "beta", '
                '"label": "BetaNode", "file": "src/beta.py", '
                '"line": 20, "confidence": 1.0, '
                '"source": "manual"}]}\n',
            },
        ]
        graph_json_content = json.dumps(
            {
                "nodes": [
                    {"id": "beta", "label": "BetaNode", "file": "src/beta.py", "line": 20},
                ]
            },
        )
        envelope = {
            "schema": 1,
            "id": snap_id,
            "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger": "manual",
            "description": "t62-fixture",
            "graph_state": {
                "observations": obs_list,
                "project_tags": {1: "insyd"},
                "graph_json_content": graph_json_content,
            },
            "metadata": {
                "obs_count": 1,
                "project_count": 1,
                "file_size_bytes": 0,
                "sha256": "",
                "include_graph": True,
            },
        }
        meta_for_hash = {k: v for k, v in envelope["metadata"].items() if k != "sha256"}
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = meta_for_hash
        envelope["metadata"]["sha256"] = hashlib.sha256(
            json.dumps(
                envelope_for_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
        ).hexdigest()
        canonical_bytes = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        envelope["metadata"]["file_size_bytes"] = len(canonical_bytes)
        meta_for_hash = {k: v for k, v in envelope["metadata"].items() if k != "sha256"}
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = meta_for_hash
        envelope["metadata"]["sha256"] = hashlib.sha256(
            json.dumps(
                envelope_for_hash, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
        ).hexdigest()
        (snapshots_dir / f"{snap_id}.json.gz").write_bytes(
            gzip.compress(
                json.dumps(envelope, ensure_ascii=False).encode("utf-8"),
                mtime=0,
            )
        )

        report = decision_drift.scan_change("mychange", snap_id=snap_id)

        # Byte-identical invariants for the snapshot happy path.
        assert report.graph_unavailable is False
        assert report.unable_reason is None
        assert report.decisions_total == 1
        assert report.bindings_total == 1
        assert DriftClass.STILL_VALID in report.class_counts
        assert report.class_counts[DriftClass.STILL_VALID] == 1


def _build_baseline_comparison_fixtures(tmp_path: Path) -> dict[str, str]:
    graph_path = tmp_path / "baseline-graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "baseline-live",
                        "label": "BaselineLive",
                        "file": "src/live.py",
                        "line": 11,
                    },
                    {
                        "id": "baseline-snapshot",
                        "label": "BaselineSnapshot",
                        "file": "src/snapshot.py",
                        "line": 22,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    os.utime(graph_path, (1_650_000_000, 1_650_000_000))
    snapshots_dir = tmp_path / "baseline-snaps"
    snapshots_dir.mkdir()
    return {
        "graph_path": str(graph_path),
        "snapshots_dir": str(snapshots_dir),
    }


def _run_current_scan_change(*, fixtures: dict[str, str], fixed_epoch: float) -> dict:
    from flow_engineering import decision_drift
    from flow_engineering.engram_io import InMemoryBackend

    old_time = decision_drift.time.time
    old_snapshots_dir = os.environ.get("FLOW_SNAPSHOTS_DIR")
    try:
        decision_drift.time.time = lambda: fixed_epoch
        os.environ["FLOW_SNAPSHOTS_DIR"] = fixtures["snapshots_dir"]
        live_backend = InMemoryBackend()
        live_backend.mem_save(
            title="baseline-live",
            content=_code_ref_content(
                node_id="baseline-live",
                label="BaselineLive",
                file="src/live.py",
                line=11,
            ),
            topic_key="sdd/baseline-live/t62",
        )
        snap_id = _write_snapshot_fixture(
            snapshots_dir=Path(fixtures["snapshots_dir"]),
            snap_id="snap_baseline_t62",
            node_id="baseline-snapshot",
            label="BaselineSnapshot",
            file="src/snapshot.py",
            line=22,
            topic_key="sdd/baseline-snapshot/t62",
        )
        return {
            "live": _serialize_report(
                decision_drift.scan_change(
                    "baseline-live",
                    graph_json_path=Path(fixtures["graph_path"]),
                    backend=live_backend,
                )
            ),
            "snapshot": _serialize_report(
                decision_drift.scan_change("baseline-snapshot", snap_id=snap_id)
            ),
        }
    finally:
        decision_drift.time.time = old_time
        if old_snapshots_dir is None:
            os.environ.pop("FLOW_SNAPSHOTS_DIR", None)
        else:
            os.environ["FLOW_SNAPSHOTS_DIR"] = old_snapshots_dir


def _run_scan_change_at_commit(
    *,
    tmp_path: Path,
    commit: str,
    fixtures: dict[str, str],
    fixed_epoch: float,
) -> dict:
    baseline_root = tmp_path / f"baseline-{commit}"
    archive_path = tmp_path / f"{commit}.zip"
    subprocess.run(
        [
            "git",
            "archive",
            "--format=zip",
            f"--output={archive_path}",
            commit,
            "src/flow_engineering",
            "prompts",
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(baseline_root)

    script_path = tmp_path / "run_baseline_scan.py"
    script_path.write_text(_BASELINE_SCAN_SCRIPT, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(baseline_root / "src")
    env["FLOW_SNAPSHOTS_DIR"] = fixtures["snapshots_dir"]
    proc = subprocess.run(
        [
            sys.executable,
            str(script_path),
            json.dumps(fixtures),
            str(fixed_epoch),
        ],
        check=True,
        cwd=baseline_root,
        env=env,
        text=True,
        capture_output=True,
    )
    return json.loads(proc.stdout)


def _code_ref_content(*, node_id: str, label: str, file: str, line: int) -> str:
    return (
        "baseline observation\n"
        "<!-- code_refs -->\n"
        + json.dumps(
            {
                "schema": 1,
                "source": "manual",
                "nodes": [
                    {
                        "project": "insyd",
                        "id": node_id,
                        "label": label,
                        "file": file,
                        "line": line,
                        "confidence": 1.0,
                        "source": "manual",
                    }
                ],
            }
        )
        + "\n"
    )


def _write_snapshot_fixture(
    *,
    snapshots_dir: Path,
    snap_id: str,
    node_id: str,
    label: str,
    file: str,
    line: int,
    topic_key: str,
) -> str:
    import gzip

    graph_json_content = json.dumps(
        {"nodes": [{"id": node_id, "label": label, "file": file, "line": line}]}
    )
    envelope = {
        "schema": 1,
        "id": snap_id,
        "created_at": "2026-07-09T00:00:00Z",
        "trigger": "manual",
        "description": "baseline comparison",
        "graph_state": {
            "observations": [
                {
                    "id": 1,
                    "title": "baseline-snapshot",
                    "topic_key": topic_key,
                    "content": _code_ref_content(
                        node_id=node_id,
                        label=label,
                        file=file,
                        line=line,
                    ),
                    "created_at": 1_650_000_000,
                }
            ],
            "project_tags": {"1": "insyd"},
            "graph_json_content": graph_json_content,
        },
        "metadata": {
            "obs_count": 1,
            "project_count": 1,
            "file_size_bytes": 0,
            "sha256": "",
            "include_graph": True,
        },
    }
    _stamp_snapshot_hash(envelope)
    (snapshots_dir / f"{snap_id}.json.gz").write_bytes(
        gzip.compress(json.dumps(envelope, ensure_ascii=False).encode("utf-8"), mtime=0)
    )
    return snap_id


def _stamp_snapshot_hash(envelope: dict) -> None:
    import hashlib

    envelope["metadata"]["file_size_bytes"] = len(
        json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    )
    metadata_without_hash = {k: v for k, v in envelope["metadata"].items() if k != "sha256"}
    envelope_without_hash = {k: v for k, v in envelope.items() if k != "metadata"}
    envelope_without_hash["metadata"] = metadata_without_hash
    envelope["metadata"]["sha256"] = hashlib.sha256(
        json.dumps(
            envelope_without_hash,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _serialize_report(report) -> dict:  # type: ignore[no-untyped-def]
    return {
        "scanned_at": report.scanned_at,
        "graph_mtime": report.graph_mtime,
        "decisions_total": report.decisions_total,
        "bindings_total": report.bindings_total,
        "class_counts": {
            getattr(k, "value", str(k)): v for k, v in sorted(report.class_counts.items())
        },
        "findings": [
            {
                "decision_id": f.decision_id,
                "binding": {
                    "project": f.binding.project,
                    "id": f.binding.id,
                    "label": f.binding.label,
                    "file": f.binding.file,
                    "line": f.binding.line,
                    "confidence": f.binding.confidence,
                    "source": f.binding.source,
                },
                "drift_class": getattr(f.drift_class, "value", str(f.drift_class)),
                "detail": f.detail,
            }
            for f in report.findings
        ],
        "graph_unavailable": report.graph_unavailable,
        "unable_reason": report.unable_reason,
    }


_BASELINE_SCAN_SCRIPT = r'''
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

from flow_engineering import decision_drift
from flow_engineering.engram_io import InMemoryBackend


def code_ref_content(*, node_id: str, label: str, file: str, line: int) -> str:
    return (
        "baseline observation\n"
        "<!-- code_refs -->\n"
        + json.dumps(
            {
                "schema": 1,
                "source": "manual",
                "nodes": [
                    {
                        "project": "insyd",
                        "id": node_id,
                        "label": label,
                        "file": file,
                        "line": line,
                        "confidence": 1.0,
                        "source": "manual",
                    }
                ],
            }
        )
        + "\n"
    )


def stamp_snapshot_hash(envelope: dict) -> None:
    envelope["metadata"]["file_size_bytes"] = len(
        json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    )
    metadata_without_hash = {k: v for k, v in envelope["metadata"].items() if k != "sha256"}
    envelope_without_hash = {k: v for k, v in envelope.items() if k != "metadata"}
    envelope_without_hash["metadata"] = metadata_without_hash
    envelope["metadata"]["sha256"] = hashlib.sha256(
        json.dumps(
            envelope_without_hash,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def write_snapshot_fixture(snapshots_dir: Path) -> str:
    snap_id = "snap_baseline_t62"
    graph_json_content = json.dumps(
        {
            "nodes": [
                {
                    "id": "baseline-snapshot",
                    "label": "BaselineSnapshot",
                    "file": "src/snapshot.py",
                    "line": 22,
                }
            ]
        }
    )
    envelope = {
        "schema": 1,
        "id": snap_id,
        "created_at": "2026-07-09T00:00:00Z",
        "trigger": "manual",
        "description": "baseline comparison",
        "graph_state": {
            "observations": [
                {
                    "id": 1,
                    "title": "baseline-snapshot",
                    "topic_key": "sdd/baseline-snapshot/t62",
                    "content": code_ref_content(
                        node_id="baseline-snapshot",
                        label="BaselineSnapshot",
                        file="src/snapshot.py",
                        line=22,
                    ),
                    "created_at": 1_650_000_000,
                }
            ],
            "project_tags": {"1": "insyd"},
            "graph_json_content": graph_json_content,
        },
        "metadata": {
            "obs_count": 1,
            "project_count": 1,
            "file_size_bytes": 0,
            "sha256": "",
            "include_graph": True,
        },
    }
    stamp_snapshot_hash(envelope)
    (snapshots_dir / f"{snap_id}.json.gz").write_bytes(
        gzip.compress(json.dumps(envelope, ensure_ascii=False).encode("utf-8"), mtime=0)
    )
    return snap_id


def serialize_report(report) -> dict:
    return {
        "scanned_at": report.scanned_at,
        "graph_mtime": report.graph_mtime,
        "decisions_total": report.decisions_total,
        "bindings_total": report.bindings_total,
        "class_counts": {
            getattr(k, "value", str(k)): v for k, v in sorted(report.class_counts.items())
        },
        "findings": [
            {
                "decision_id": f.decision_id,
                "binding": {
                    "project": f.binding.project,
                    "id": f.binding.id,
                    "label": f.binding.label,
                    "file": f.binding.file,
                    "line": f.binding.line,
                    "confidence": f.binding.confidence,
                    "source": f.binding.source,
                },
                "drift_class": getattr(f.drift_class, "value", str(f.drift_class)),
                "detail": f.detail,
            }
            for f in report.findings
        ],
        "graph_unavailable": report.graph_unavailable,
        "unable_reason": getattr(report, "unable_reason", None),
    }


fixtures = json.loads(sys.argv[1])
fixed_epoch = float(sys.argv[2])
decision_drift.time.time = lambda: fixed_epoch
snapshots_dir = Path(fixtures["snapshots_dir"])
snap_id = write_snapshot_fixture(snapshots_dir)

live_backend = InMemoryBackend()
live_backend.mem_save(
    title="baseline-live",
    content=code_ref_content(
        node_id="baseline-live",
        label="BaselineLive",
        file="src/live.py",
        line=11,
    ),
    topic_key="sdd/baseline-live/t62",
)

print(
    json.dumps(
        {
            "live": serialize_report(
                decision_drift.scan_change(
                    "baseline-live",
                    graph_json_path=Path(fixtures["graph_path"]),
                    backend=live_backend,
                )
            ),
            "snapshot": serialize_report(
                decision_drift.scan_change("baseline-snapshot", snap_id=snap_id)
            ),
        },
        sort_keys=True,
    )
)
'''
