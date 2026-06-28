"""REQ-V9.1..V9.4 v0.9.0 hardening shim-removal verification tests.

Shim removal verification tests for v0.9.0 hardening. Asserts the 3
v0.8.0 1-release compat shims are removed and ``Finding.__post_init__``
enforces int-only ``decision_id``.

Each fixture asserts one of:

- ``Finding.from_legacy`` attribute is removed (REQ-V9.1).
- ``DriftReport.from_legacy`` attribute is removed (REQ-V9.2).
- ``classify_binding_legacy`` function is removed (REQ-V9.3).
- ``Finding(decision_id=<str>, ...)`` raises ``TypeError`` via the
  v0.9.0 ``Finding.__post_init__`` enforcement (REQ-V9.4).

Refs: openspec/changes/v0.9.0-hardening/{proposal,tasks}.md
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
    id: str = "src_auth_jwt_jwttokenmanager",  # noqa: A002
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


# ---- T1.1 — Finding.from_legacy attribute removed (REQ-V9.1) -------------


def test_finding_from_legacy_attribute_removed() -> None:
    """v0.9.0: ``Finding.from_legacy`` classmethod MUST NOT exist.

    The compat shim was removed in v0.9.0 per CHANGELOG v0.8.0 lines 43/74
    (operator commitment). Accessing the attribute raises AttributeError.
    """
    assert not hasattr(Finding, "from_legacy"), (
        "Finding.from_legacy must be removed in v0.9.0 (REQ-V9.1); "
        "legacy callers must migrate to direct Finding(decision_id=<int>, ...)"
    )


# ---- T1.4 — DriftReport.from_legacy attribute removed (REQ-V9.2) --------


def test_drift_report_from_legacy_attribute_removed() -> None:
    """v0.9.0: ``DriftReport.from_legacy`` classmethod MUST NOT exist.

    The compat shim was removed in v0.9.0. Accessing the attribute raises
    AttributeError; legacy callers must use direct
    ``DriftReport(scanned_at=<iso8601_str>, ...)``.
    """
    assert not hasattr(DriftReport, "from_legacy"), (
        "DriftReport.from_legacy must be removed in v0.9.0 (REQ-V9.2); "
        "legacy callers must migrate to direct DriftReport(scanned_at=<iso8601>, ...)"
    )


# ---- T2.1 — classify_binding_legacy function removed (REQ-V9.3) ----------


def test_classify_binding_legacy_attribute_removed() -> None:
    """v0.9.0: ``classify_binding_legacy`` module-level function MUST NOT exist.

    The 3-arg compat wrapper was removed in v0.9.0. Importing it raises
    ImportError; legacy callers must use the 2-arg
    ``classify_binding(ref, graph_nodes)``.
    """
    import flow_engineering.decision_drift as dd_mod

    assert not hasattr(dd_mod, "classify_binding_legacy"), (
        "classify_binding_legacy must be removed in v0.9.0 (REQ-V9.3); "
        "legacy callers must migrate to 2-arg classify_binding(ref, graph_nodes)"
    )


# ---- T2.4 — Finding.__post_init__ rejects str decision_id (REQ-V9.4) ----


def test_finding_constructor_rejects_str_decision_id() -> None:
    """v0.9.0: ``Finding(decision_id="42", ...)`` MUST raise ``TypeError``.

    The W1 enforcement via ``Finding.__post_init__`` rejects non-int inputs
    (no DeprecationWarning, no int() coercion). The compat shim IS the soft
    compat — v0.9.0 removes it AND hardens the constructor.
    """
    with pytest.raises(TypeError) as exc_info:
        Finding(
            decision_id="42",
            binding=_ref(),
            drift_class=DriftClass.STILL_VALID,
            detail="ok",
        )
    assert "decision_id" in str(exc_info.value) or "int" in str(exc_info.value), (
        "TypeError message must reference decision_id or int type"
    )


def test_finding_constructor_rejects_bool_decision_id() -> None:
    """v0.9.0: ``Finding(decision_id=True, ...)`` MUST raise ``TypeError``.

    ``bool`` is a subclass of ``int`` in Python — naive ``isinstance(x, int)``
    would accept ``True`` as a valid ``decision_id``. The
    ``Finding.__post_init__`` MUST explicitly reject ``bool`` to prevent
    silent stringy truthy/falsy coercion bugs.
    """
    with pytest.raises(TypeError):
        Finding(
            decision_id=True,  # type: ignore[arg-type]
            binding=_ref(),
            drift_class=DriftClass.STILL_VALID,
            detail="ok",
        )


def test_finding_constructor_accepts_int_decision_id() -> None:
    """v0.9.0: ``Finding(decision_id=42, ...)`` constructs successfully.

    Canonical type-contract smoke — the constructor must remain functional
    for valid int inputs.
    """
    f = Finding(
        decision_id=42,
        binding=_ref(),
        drift_class=DriftClass.STILL_VALID,
        detail="ok",
    )
    assert f.decision_id == 42
    assert isinstance(f.decision_id, int)
    assert not isinstance(f.decision_id, bool)


# ---- T1.5/T2.2 sanity — confirm canonical 2-arg classify_binding works ---


def test_canonical_classify_binding_2arg_still_valid() -> None:
    """The 2-arg canonical ``classify_binding`` is unchanged in v0.9.0."""
    binding = _ref()
    nodes = {
        "src_auth_jwt_jwttokenmanager": {
            "id": "src_auth_jwt_jwttokenmanager",
            "label": "JWTTokenManager",
            "file": "src/auth/jwt.py",
            "line": 42,
        }
    }
    assert classify_binding(binding, nodes) is DriftClass.STILL_VALID
