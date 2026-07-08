"""Unit tests for the ObservationSource Protocol + adapters (REQ-DRIFT-DETECTION-2).

Slice 1 of the drift-detection change. Strict TDD posture per constitution
Article III + ``sdd-init/flow-engineering.md`` ``strict_tdd: true``.

The tests accumulate across T2.1..T2.3:

- **T2.1** (RED → GREEN): 3 Protocol-contract tests.
- **T2.2a**: 2 ``BackendObservationSource`` filter-logic tests.
- **T2.2b**: 2 ``FrozenBackendObservationSource`` round-trip tests.
- **T2.3**: 1 ``StaticObservationSource`` identity-iteration test.

Plus adapter-compat tests land at Batch 6 (T6.1a) when
``decision_drift._build_source`` is added.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

# ---------- T2.1 — Protocol-contract tests (3 tests, RED → GREEN) ----------


class TestObservationSourceProtocol:
    """REQ-DRIFT-DETECTION-2: ``ObservationSource`` is a narrow Protocol
    with a single ``iter_observations(self) -> Iterable[dict]`` method.
    The Protocol MUST NOT require ``mem_search`` (the orphaned method
    ``_DummyBackend`` carried).
    """

    def test_observation_source_is_importable(self) -> None:
        from flow_engineering.drift_observation_source import ObservationSource  # noqa: F401

        assert ObservationSource is not None

    def test_observation_source_is_a_typing_protocol(self) -> None:
        from flow_engineering.drift_observation_source import ObservationSource

        assert issubclass(ObservationSource, Protocol)

    def test_observation_source_declares_only_iter_observations(self) -> None:
        """The Protocol declares ONLY ``iter_observations``. A stub class
        implementing ONLY that method MUST satisfy ``isinstance`` at
        runtime via ``@runtime_checkable``.
        """
        from flow_engineering.drift_observation_source import ObservationSource

        declared = {
            name
            for name in dir(ObservationSource)
            if not name.startswith("_")
            and callable(getattr(ObservationSource, name, None))
        }
        assert declared == {"iter_observations"}

        class _Stub:
            def iter_observations(self) -> Iterable[dict]:  # type: ignore[type-arg]
                return iter([])

        assert isinstance(_Stub(), ObservationSource)


# ---------- T2.2a — BackendObservationSource filter-logic (2 tests) ----------


class TestBackendObservationSource:
    """REQ-DRIFT-DETECTION-2 scenario 1: wraps an ``EngramBackend`` +
    applies the ``topic_key`` prefix + ``since`` cutoff filter chain.
    """

    def test_filters_by_change_name_topic_key_prefix(self) -> None:
        from flow_engineering.drift_observation_source import (
            BackendObservationSource,
        )
        from flow_engineering.engram_io import InMemoryBackend

        backend = InMemoryBackend()
        backend.mem_save(title="t1", content="c1", topic_key="sdd/mychange/a")
        backend.mem_save(title="t2", content="c2", topic_key="sdd/mychange/b")
        backend.mem_save(title="t3", content="c3", topic_key="sdd/other/c")

        source = BackendObservationSource(backend, change_name="mychange")
        result = list(source.iter_observations())

        # 2 of 3 observations match the ``sdd/mychange/`` prefix.
        assert len(result) == 2
        for obs in result:
            assert obs["topic_key"].startswith("sdd/mychange/")

    def test_since_cutoff_drops_older_observations(self) -> None:
        from flow_engineering.drift_observation_source import (
            BackendObservationSource,
        )
        from flow_engineering.engram_io import InMemoryBackend

        backend = InMemoryBackend()
        # InMemoryBackend sets created_at = next_id * 1000 (id=1 → 1000).
        backend.mem_save(title="t1", content="c1", topic_key="sdd/c/x")

        source = BackendObservationSource(backend, change_name="c", since=1001.0)
        # since=1001.0 is strictly greater than the observation's
        # created_at=1000.0 → observation is dropped.
        assert list(source.iter_observations()) == []


# ---------- T2.2b — FrozenBackendObservationSource round-trip (2 tests) ----------


class TestFrozenBackendObservationSource:
    """REQ-DRIFT-DETECTION-2 scenario 3: rebuilds an ``InMemoryBackend``
    from a snapshot's ``graph_state.observations`` preserving ids.
    """

    def test_round_trips_snapshot_observations(
        self, tmp_path, monkeypatch,
    ) -> None:
        import gzip
        import hashlib
        import json
        import secrets
        from datetime import UTC, datetime

        from flow_engineering.drift_observation_source import (
            FrozenBackendObservationSource,
        )

        snapshots_dir = tmp_path / "snaps"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("FLOW_SNAPSHOTS_DIR", str(snapshots_dir))

        # Build a snapshot envelope with 2 observations.
        iso = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
        snap_id = f"snap_{iso}-{secrets.token_hex(3)}"
        obs_list = [
            {"id": 1, "topic_key": "sdd/obs-detection/x", "content": "first"},
            {"id": 2, "topic_key": "sdd/obs-detection/y", "content": "second"},
        ]
        envelope = {
            "schema": 1,
            "id": snap_id,
            "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trigger": "manual",
            "description": "t22b-fixture",
            "graph_state": {
                "observations": obs_list,
                "project_tags": {},
            },
            "metadata": {
                "obs_count": 2,
                "project_count": 0,
                "file_size_bytes": 0,
                "sha256": "",
                "include_graph": False,
            },
        }
        meta_for_hash = {k: v for k, v in envelope["metadata"].items() if k != "sha256"}
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = meta_for_hash
        envelope["metadata"]["sha256"] = hashlib.sha256(
            json.dumps(envelope_for_hash, ensure_ascii=False,
                       sort_keys=True, separators=(",", ":")).encode("utf-8"),
        ).hexdigest()
        (snapshots_dir / f"{snap_id}.json.gz").write_bytes(
            gzip.compress(
                json.dumps(envelope, ensure_ascii=False).encode("utf-8"), mtime=0,
            )
        )

        source = FrozenBackendObservationSource(snap_id)
        result = list(source.iter_observations())

        # Both observations round-trip.
        assert len(result) == 2
        ids = sorted(o["id"] for o in result)
        assert ids == [1, 2]

    def test_envelope_corruption_yields_empty_observations(
        self, tmp_path, monkeypatch,
    ) -> None:
        """Consistent with the existing legacy behavior: a corrupt envelope
        yields an empty observation set (the scan will fail later via the
        GraphLoader raising ``SnapshotEnvelopeCorrupt``).
        """
        import gzip
        import json

        from flow_engineering.drift_observation_source import (
            FrozenBackendObservationSource,
        )

        snapshots_dir = tmp_path / "snaps_corrupt"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("FLOW_SNAPSHOTS_DIR", str(snapshots_dir))

        envelope = {
            "schema": 1,
            "id": "snap_corrupt_obs",
            "created_at": "2026-07-08T00:00:00Z",
            "trigger": "manual",
            "description": "corrupt",
            "graph_state": {"observations": [], "project_tags": {}},
            "metadata": {
                "obs_count": 0,
                "project_count": 0,
                "file_size_bytes": 0,
                "sha256": "badbadbad" * 5,
                "include_graph": False,
            },
        }
        (snapshots_dir / "snap_corrupt_obs.json.gz").write_bytes(
            gzip.compress(
                json.dumps(envelope, ensure_ascii=False).encode("utf-8"), mtime=0,
            )
        )

        source = FrozenBackendObservationSource("snap_corrupt_obs")
        # Corrupt envelope → empty list (consistent with legacy behavior).
        assert list(source.iter_observations()) == []
