"""Unit tests for ``flow_engineering.decision_drift.classify_binding`` (REQ-9).

T1.4 RED fixtures. Twelve per-class cases (six mutually-exclusive drift
classes plus ``UNABLE_TO_VERIFY``) plus two deferral assertions pinning
``OBSOLETE`` / ``CONTRADICTED`` to ``scan_change`` (design #123 decisions
2 + 3 — classify_binding is single-binding only).

The RED phase expects every test in this file to fail with
``NotImplementedError`` from the stubbed ``classify_binding``. The GREEN
phase (T1.5) implements the function so all of these pass.
"""

from __future__ import annotations

import pytest

from flow_engineering.binding import CodeRef
from flow_engineering.decision_drift import (
    DriftClass,
    DriftReport,
    Finding,
    classify_binding,
)


def _ref(
    *,
    project: str = "insyd",
    id: str = "src_auth_jwt_jwttokenmanager",
    label: str = "JWTTokenManager",
    file: str = "src/auth/jwt.py",
    line: int = 42,
    confidence: float = 0.9,
    source: str = "manual",
) -> CodeRef:
    return CodeRef(
        project=project,
        id=id,
        label=label,
        file=file,
        line=line,
        confidence=confidence,
        source=source,
    )


def _nodes(*pairs: tuple[str, str]) -> dict[str, dict]:
    return {
        pid: {"id": pid, "label": lbl, "file": "src/auth/jwt.py", "line": 42}
        for pid, lbl in pairs
    }


def _id_map(*entries: tuple[str, str, int, str]) -> dict[str, tuple[str, int, str]]:
    return {pid: (file, line, label) for pid, file, line, label in entries}


# --- STILL_VALID -----------------------------------------------------------


def test_classify_still_valid_basic() -> None:
    binding = _ref()
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    id_map = _id_map(
        ("src_auth_jwt_jwttokenmanager", "src/auth/jwt.py", 42, "JWTTokenManager")
    )
    assert classify_binding(binding, nodes, id_map) is DriftClass.STILL_VALID


def test_classify_still_valid_source_and_confidence_dont_affect_class() -> None:
    binding = _ref(source="backfill", confidence=0.3)
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    id_map = _id_map(
        ("src_auth_jwt_jwttokenmanager", "src/auth/jwt.py", 42, "JWTTokenManager")
    )
    assert classify_binding(binding, nodes, id_map) is DriftClass.STILL_VALID


# --- LABEL_DRIFT -----------------------------------------------------------


def test_classify_label_drift_when_label_differs() -> None:
    binding = _ref(label="JWTTokenManager")
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTManager"))
    id_map = _id_map(
        ("src_auth_jwt_jwttokenmanager", "src/auth/jwt.py", 42, "JWTManager")
    )
    assert classify_binding(binding, nodes, id_map) is DriftClass.LABEL_DRIFT


def test_classify_label_drift_case_only_still_flags() -> None:
    binding = _ref(label="jwtTokenManager")
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JwtTokenManager"))
    id_map = _id_map(
        ("src_auth_jwt_jwttokenmanager", "src/auth/jwt.py", 42, "JwtTokenManager")
    )
    assert classify_binding(binding, nodes, id_map) is DriftClass.LABEL_DRIFT


# --- STALE_LOCATION --------------------------------------------------------


def test_classify_stale_location_when_file_moved() -> None:
    binding = _ref(file="src/old.py", line=10)
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    id_map = _id_map(
        ("src_auth_jwt_jwttokenmanager", "src/new.py", 42, "JWTTokenManager")
    )
    assert classify_binding(binding, nodes, id_map) is DriftClass.STALE_LOCATION


def test_classify_stale_location_when_line_shifted_same_file() -> None:
    binding = _ref(file="src/foo.py", line=10)
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    id_map = _id_map(
        ("src_auth_jwt_jwttokenmanager", "src/foo.py", 15, "JWTTokenManager")
    )
    assert classify_binding(binding, nodes, id_map) is DriftClass.STALE_LOCATION


# --- STALE_ID --------------------------------------------------------------


def test_classify_stale_id_when_id_absent_from_id_map() -> None:
    binding = _ref(id="deleted_class_hash")
    nodes = _nodes(("other_node", "Other"))
    id_map = _id_map(("other_node", "src/other.py", 1, "Other"))
    assert classify_binding(binding, nodes, id_map) is DriftClass.STALE_ID


def test_classify_stale_id_when_id_renamed_with_no_alias() -> None:
    binding = _ref(id="old_class_hash")
    nodes = _nodes(("new_class_hash", "NewClass"))
    id_map = _id_map(("new_class_hash", "src/foo.py", 1, "NewClass"))
    assert classify_binding(binding, nodes, id_map) is DriftClass.STALE_ID


# --- UNABLE_TO_VERIFY (terminal) -------------------------------------------


def test_classify_unable_to_verify_when_current_nodes_is_none() -> None:
    binding = _ref()
    assert classify_binding(binding, None, {}) is DriftClass.UNABLE_TO_VERIFY


def test_classify_unable_to_verify_when_current_nodes_is_empty() -> None:
    binding = _ref()
    assert classify_binding(binding, {}, {}) is DriftClass.UNABLE_TO_VERIFY


# --- Deferral: OBSOLETE + CONTRADICTED are NOT classify_binding's job -----


def test_classify_binding_never_returns_obsolete_for_resolvable_id() -> None:
    """``OBSOLETE`` is scan_change's job (design #123 decision 3).

    Even when the binding's ``source`` is ``unbound``, classify_binding must
    not emit ``OBSOLETE`` — that verdict requires per-decision graphify_query
    work which only ``scan_change`` performs.
    """
    binding = _ref(source="unbound", confidence=0.0)
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    id_map = _id_map(
        ("src_auth_jwt_jwttokenmanager", "src/auth/jwt.py", 42, "JWTTokenManager")
    )
    assert classify_binding(binding, nodes, id_map) is not DriftClass.OBSOLETE


def test_classify_binding_never_returns_contradicted() -> None:
    """``CONTRADICTED`` is scan_change's job (design #123 decision 2).

    Contradiction is a cross-decision property (same id, multiple bindings,
    conflicting source/confidence); a single binding cannot be contradicted
    with itself.
    """
    binding = _ref(source="manual", confidence=0.9)
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    id_map = _id_map(
        ("src_auth_jwt_jwttokenmanager", "src/auth/jwt.py", 42, "JWTTokenManager")
    )
    assert classify_binding(binding, nodes, id_map) is not DriftClass.CONTRADICTED


# --- Dataclass shape (smoke) ----------------------------------------------


def test_finding_is_frozen() -> None:
    f = Finding(
        decision_id="obs-1",
        binding=_ref(),
        drift_class=DriftClass.STILL_VALID,
        detail="ok",
    )
    with pytest.raises(Exception):
        f.drift_class = DriftClass.LABEL_DRIFT  # type: ignore[misc]


def test_drift_report_defaults() -> None:
    r = DriftReport(
        change_name="decision-reality-drift",
        scanned_at=0.0,
        graph_mtime=None,
        decisions_total=0,
        bindings_total=0,
    )
    assert r.class_counts == {}
    assert r.findings == []
    assert r.graph_unavailable is False