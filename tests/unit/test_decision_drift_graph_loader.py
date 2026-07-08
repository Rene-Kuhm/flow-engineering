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
        from typing import Protocol as _Protocol

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
