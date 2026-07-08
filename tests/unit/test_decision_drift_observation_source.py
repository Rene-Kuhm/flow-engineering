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
