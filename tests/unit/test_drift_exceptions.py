"""Typed graph-load exception contract tests for drift detection."""

from flow_engineering.drift_exceptions import (
    GraphLoadError,
    GraphMalformed,
    GraphMissing,
    PermissionDenied,
    SnapshotEnvelopeCorrupt,
)


def test_graph_load_errors_share_base_exception() -> None:
    assert issubclass(GraphMissing, GraphLoadError)
    assert issubclass(GraphMalformed, GraphLoadError)
    assert issubclass(PermissionDenied, GraphLoadError)
    assert issubclass(SnapshotEnvelopeCorrupt, GraphLoadError)


def test_graph_load_errors_are_sibling_types() -> None:
    assert not issubclass(GraphMissing, GraphMalformed)
    assert not issubclass(GraphMalformed, GraphMissing)
    assert not issubclass(PermissionDenied, GraphMalformed)
    assert not issubclass(SnapshotEnvelopeCorrupt, GraphMissing)


def test_graph_load_errors_preserve_message_attribute() -> None:
    error = GraphMissing("graph file missing: /tmp/graph.json")

    assert error.message == "graph file missing: /tmp/graph.json"
    assert str(error) == error.message


def test_each_graph_load_error_can_reference_source_context() -> None:
    cases = [
        (GraphMissing, "missing graph path: /tmp/graph.json"),
        (GraphMalformed, "malformed graph path: /tmp/graph.json"),
        (PermissionDenied, "unreadable graph path: /tmp/graph.json"),
        (SnapshotEnvelopeCorrupt, "corrupt snapshot envelope: snap-123"),
    ]

    for error_type, message in cases:
        error = error_type(message)

        assert isinstance(error, Exception)
        assert error.message == message
        assert str(error) == message
