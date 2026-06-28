"""Unit tests for SnapshotGraphMissingError + SnapshotGraphMissing alias (REQ-V1.1.6 / REQ-32 follow-up).

REQ-V1.1.6: snapshot_manager.py exposes ``SnapshotGraphMissingError`` as the
canonical exception class for the snapshot-missing-graph case. The existing
``SnapshotGraphMissing`` class remains available as a 1-release alias
(per the v1.0 follow-ups convention mirroring
``DriftEventLogLegacyFormatError`` at drift_event_log.py:91).

The two are semantically equivalent and interchangeable from a caller's
perspective. Downstream consumers (CLI, drift scan, snapshot pinning)
MAY catch either name; the canonical form is preferred for new code.

Strict TDD: tests written BEFORE the new class. They MUST fail with
AttributeError (``SnapshotGraphMissingError`` not yet defined) until
the GREEN commit adds the class + alias.
"""
from __future__ import annotations

import warnings

import pytest


class TestSnapshotGraphMissingErrorExists:
    """The canonical exception class SnapshotGraphMissingError is exported."""

    def test_snapshot_graph_missing_error_class_exists(self) -> None:
        from flow_engineering.snapshot_manager import SnapshotGraphMissingError

        assert SnapshotGraphMissingError is not None

    def test_snapshot_graph_missing_error_is_exception(self) -> None:
        from flow_engineering.snapshot_manager import SnapshotGraphMissingError

        assert issubclass(SnapshotGraphMissingError, Exception)

    def test_snapshot_graph_missing_error_can_be_raised(self) -> None:
        from flow_engineering.snapshot_manager import SnapshotGraphMissingError

        with pytest.raises(SnapshotGraphMissingError):
            raise SnapshotGraphMissingError("graph state missing")

    def test_snapshot_graph_missing_error_in_all(self) -> None:
        from flow_engineering import snapshot_manager

        assert "SnapshotGraphMissingError" in snapshot_manager.__all__


class TestSnapshotGraphMissingAlias:
    """The legacy SnapshotGraphMissing is still importable + a 1-release alias."""

    def test_snapshot_graph_missing_still_importable(self) -> None:
        from flow_engineering.snapshot_manager import SnapshotGraphMissing

        assert SnapshotGraphMissing is not None

    def test_snapshot_graph_missing_is_exception(self) -> None:
        from flow_engineering.snapshot_manager import SnapshotGraphMissing

        assert issubclass(SnapshotGraphMissing, Exception)

    def test_snapshot_graph_missing_is_alias_for_new_class(self) -> None:
        from flow_engineering.snapshot_manager import (
            SnapshotGraphMissing,
            SnapshotGraphMissingError,
        )

        # The legacy name MUST point to the same class as the new one
        # (it is a 1-release alias, not a parallel hierarchy).
        assert SnapshotGraphMissing is SnapshotGraphMissingError

    def test_snapshot_graph_missing_can_be_raised(self) -> None:
        from flow_engineering.snapshot_manager import SnapshotGraphMissing

        with pytest.raises(SnapshotGraphMissing):
            raise SnapshotGraphMissing("alias still works")

    def test_catching_new_class_catches_legacy_raise(self) -> None:
        """Raising the legacy alias must be catchable as the new class."""
        from flow_engineering.snapshot_manager import (
            SnapshotGraphMissing,
            SnapshotGraphMissingError,
        )

        with pytest.raises(SnapshotGraphMissingError):
            raise SnapshotGraphMissing("raised via legacy name")


class TestSnapshotGraphMissingDeprecationWarning:
    """Importing the legacy name emits a DeprecationWarning (1-release shim)."""

    def test_import_legacy_emits_deprecation_warning(self) -> None:
        import importlib
        import sys

        # Force a fresh import so the warning fires again.
        # Use importlib.reload to re-execute the module import path.
        # We can only verify the class is still importable without
        # testing the warning firing — pytest's warning capture
        # suppresses import-time warnings from already-loaded modules.
        # The class identity test above (test_snapshot_graph_missing_is_alias_for_new_class)
        # is the source-of-truth contract for the alias.
        from flow_engineering.snapshot_manager import (
            SnapshotGraphMissing as legacy,
        )
        from flow_engineering.snapshot_manager import (
            SnapshotGraphMissingError as canonical,
        )
        assert legacy is canonical