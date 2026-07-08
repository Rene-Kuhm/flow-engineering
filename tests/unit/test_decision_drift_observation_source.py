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

from typing import Iterable, Protocol

import pytest


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