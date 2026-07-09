"""ObservationSource Protocol + adapters (REQ-DRIFT-DETECTION-2).

Slice 1 (T2.1 → T2.3) of the drift-detection change. The Protocol seam
replaces the inline ``backend.iter_observations()`` + ``topic_key`` prefix
+ ``since`` filter plumbing inside ``decision_drift.scan_change``.

Three concrete adapters:

- ``BackendObservationSource`` — wraps an ``EngramBackend`` and applies
  the ``topic_key`` prefix + ``since`` cutoff filter chain.
- ``FrozenBackendObservationSource`` — rebuilds an ``InMemoryBackend``
  from a snapshot's frozen ``graph_state.observations``.
- ``StaticObservationSource`` — test-only canned-data adapter for fixtures
  that need a direct observation stream (REQ-DRIFT-DETECTION-5).

Design: ``openspec/changes/drift-detection/design.md`` §3.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from flow_engineering.engram_io import EngramBackend


# ---------- Protocol (REQ-DRIFT-DETECTION-2) ----------


@runtime_checkable
class ObservationSource(Protocol):
    """Narrow contract for an observation-stream collaborator.

    Replaces the legacy fixture-as-type seam. Declares ONLY
    ``iter_observations`` (no orphaned ``mem_search`` method with
    ``# pragma: no cover`` markers).
    """

    def iter_observations(self) -> Iterable[dict]:  # type: ignore[type-arg]
        """Yield observation dicts. Filtering by ``topic_key`` prefix +
        ``since`` cutoff happens INSIDE the ``BackendObservationSource``
        adapter so callers do not need to re-implement it.
        """
        ...


# ---------- Live-backend adapter (REQ-DRIFT-DETECTION-2 scenario 1) ----------


class BackendObservationSource:
    """Adapter that wraps an ``EngramBackend`` + the ``topic_key`` prefix
    + ``since`` filter chain (REQ-DRIFT-DETECTION-2 scenario 1).

    Mirrors the inline filter chain at ``decision_drift.py:601-615``
    byte-for-byte. The bare ``except Exception: observations = []``
    fail-open at ``decision_drift.py:602-603`` is preserved here so the
    public ``scan_change`` contract stays stable.
    """

    def __init__(
        self,
        backend: EngramBackend | None,
        *,
        change_name: str,
        since: float | None = None,
    ) -> None:
        from flow_engineering.engram_io import InMemoryBackend

        self._backend = backend if backend is not None else InMemoryBackend()
        self._change_name = change_name
        self._since = since

    def iter_observations(self) -> Iterable[dict]:  # type: ignore[type-arg]
        try:
            observations = list(self._backend.iter_observations())
        except Exception:
            return []
        prefix = f"sdd/{self._change_name}/"
        observations = [o for o in observations if str(o.get("topic_key", "")).startswith(prefix)]
        if self._since is not None:
            observations = [o for o in observations if float(o.get("created_at", 0)) >= self._since]
        return observations


# ---------- Snapshot-backed adapter (REQ-DRIFT-DETECTION-2 scenario 3) ----------


class FrozenBackendObservationSource:
    """Adapter that rebuilds an ``InMemoryBackend`` from a snapshot's
    frozen ``graph_state.observations`` (REQ-DRIFT-DETECTION-2 scenario 3).

    Replaces the existing ``_frozen_backend_from_snapshot(snap_id)``
    helper at ``decision_drift.py:422-458``. The snapshot's ``id`` field
    is preserved so iteration returns the same observation set the scan
    saw at snapshot time (REQ-33 + D13 byte-identical behavior).

    Caches the rebuilt observation list in ``self._cache`` so repeated
    ``iter_observations()`` calls (e.g., test introspection) don't
    re-read the envelope.
    """

    def __init__(self, snap_id: str) -> None:
        self._snap_id = snap_id
        self._cache: list[dict] | None = None  # type: ignore[type-arg]

    def iter_observations(self) -> Iterable[dict]:  # type: ignore[type-arg]
        if self._cache is None:
            self._cache = self._load_frozen_observations()
        return self._cache

    def _load_frozen_observations(self) -> list[dict]:  # type: ignore[type-arg]
        from flow_engineering.engram_io import InMemoryBackend
        from flow_engineering.snapshot_manager import (
            SnapshotEnvelopeError,
            SnapshotManager,
        )

        snapshots_dir = _resolve_snapshots_dir_for_source()
        manager = SnapshotManager(
            snapshots_dir=snapshots_dir,
            backend=None,  # type: ignore[arg-type]  # show() never touches backend
        )
        try:
            envelope = manager.show(self._snap_id)
        except SnapshotEnvelopeError:
            return []
        obs_list = envelope.get("graph_state", {}).get("observations", [])
        frozen = InMemoryBackend()
        if not isinstance(obs_list, list):
            return []
        for o in obs_list:
            if not isinstance(o, dict) or "id" not in o:
                continue
            # Preserve snapshot's id so iteration returns the same
            # observation set the scan saw at snapshot time.
            oid = int(o["id"])
            frozen.observations[oid] = dict(o)
            if oid >= frozen.next_id:
                frozen.next_id = oid + 1
        return list(frozen.iter_observations())


# ---------- Test-only adapter (REQ-DRIFT-DETECTION-5) ----------


class StaticObservationSource:
    """Test-only canned-data adapter.

    Provides a small canned observation stream for tests and BDD step glue.
    Excluded from ``__all__`` so the public API surface stays clean.

    Iteration is identity (no filtering, no backend, no I/O).
    """

    def __init__(self, observations: list[dict]) -> None:  # type: ignore[type-arg]
        self._observations = list(observations)

    def iter_observations(self) -> Iterable[dict]:  # type: ignore[type-arg]
        return iter(self._observations)


# ---------- Helpers ----------


def _resolve_snapshots_dir_for_source() -> Path:
    """Lazy-import ``decision_drift._resolve_snapshots_dir`` with an
    inline fallback to keep this module independent of ``decision_drift``
    (mirrors ``drift_graph_loader._resolve_snapshots_dir_for_loader``).
    """
    try:
        from flow_engineering.decision_drift import (
            _resolve_snapshots_dir as _impl,
        )

        return _impl()
    except ImportError:
        import os as _os

        env = _os.environ.get("FLOW_SNAPSHOTS_DIR")
        if env:
            return Path(env)
        return Path.home() / ".flow-engineering" / "snapshots"


__all__ = [
    "ObservationSource",
    "BackendObservationSource",
    "FrozenBackendObservationSource",
    # StaticObservationSource intentionally excluded from __all__ — test-only.
]
