"""REQ-56 W8 / REQ-57 v0.8.0 dataclass migration tests (with v0.9.0 carry-forward).

Canonical type-contract smokes for ``decision_drift.Finding`` +
``DriftReport``. After v0.9.0 these are the only remaining tests in
this file; the v0.8.0 migration shim tests
(``Finding.from_legacy``, ``DriftReport.from_legacy``,
``classify_binding_legacy``) were deleted when their respective compat
shims were removed (REQ-V9.1, REQ-V9.2, REQ-V9.3).

Each remaining fixture asserts one of:

- ``Finding.decision_id`` is ``int`` (canonical type contract).
- ``DriftReport.scanned_at`` is ``str`` ISO 8601 (canonical type contract).
- ``DriftReport.unable_reason`` defaults to ``None`` when omitted.

Refs: openspec/changes/archive/2026-06-27-drift-hardening/{spec,design,tasks}.md T4.1..T4.3.
"""

from __future__ import annotations

import warnings
from datetime import datetime, timezone

import pytest

from flow_engineering.binding import CodeRef
from flow_engineering.decision_drift import (
    DriftClass,
    DriftReport,
    Finding,
    _epoch_to_iso,
    classify_binding,
)


# ---- helpers -------------------------------------------------------------


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


# ---- T4.1 — Finding.decision_id int + from_legacy shim --------------------


def test_finding_decision_id_is_int_type() -> None:
    """v0.8.0 canonical: ``Finding(decision_id=42, ...)`` keeps int type.

    Existing v0.7.x str usage continues to construct (Python duck-typed),
    but new code should pass int directly. Asserts the type is preserved
    and no warning fires.
    """
    f = Finding(
        decision_id=42,
        binding=_ref(),
        drift_class=DriftClass.STILL_VALID,
        detail="ok",
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        f = Finding(
            decision_id=42,
            binding=_ref(),
            drift_class=DriftClass.STILL_VALID,
            detail="ok",
        )
    assert isinstance(f.decision_id, int)
    assert f.decision_id == 42
    assert not any(issubclass(w.category, DeprecationWarning) for w in caught), (
        "int input must NOT trigger DeprecationWarning"
    )


# v0.9.0 (REQ-V9.1): Finding.from_legacy compat shim was removed in v0.9.0.
# The 3 v0.8.0 fixtures that exercised the shim (test_finding_from_legacy_*
# — emits_deprecation_warning, coerces_str_to_int, non_numeric_str_raises)
# are deleted; the canonical type-contract smoke at line 76
# (test_finding_decision_id_is_int_type) remains as the regression gate.
# See tests/unit/test_decision_drift_v090_hardening.py for the v0.9.0
# assertion that ``Finding.from_legacy`` no longer exists.


# ---- T4.2 — DriftReport.scanned_at str ISO + from_legacy shim ------------


def test_drift_report_scanned_at_is_str_iso() -> None:
    """v0.8.0 canonical: ``scanned_at`` is ISO 8601 str (e.g. '...Z')."""
    r = DriftReport(
        change_name="obs",
        scanned_at="2026-06-27T12:34:56Z",
        graph_mtime=None,
        decisions_total=0,
        bindings_total=0,
    )
    assert r.scanned_at == "2026-06-27T12:34:56Z"
    assert isinstance(r.scanned_at, str)


# v0.9.0 (REQ-V9.2): DriftReport.from_legacy compat shim was removed in v0.9.0.
# The 3 v0.8.0 fixtures that exercised the shim
# (test_drift_report_from_legacy_emits_deprecation_warning,
# test_drift_report_from_legacy_converts_epoch_to_iso,
# test_drift_report_from_legacy_handles_unable_to_verify_alias)
# are deleted; the canonical type-contract smokes remain
# (test_drift_report_scanned_at_is_str_iso at line 111 +
# test_drift_report_unable_reason_default_none at line 168 + the
# test_epoch_to_iso_helper_matches_datetime at line 179).
# See tests/unit/test_decision_drift_v090_hardening.py for the v0.9.0
# assertion that ``DriftReport.from_legacy`` no longer exists.


def test_drift_report_unable_reason_default_none() -> None:
    """v0.8.0 ``unable_reason`` field defaults to ``None`` when omitted."""
    r = DriftReport(
        change_name="obs",
        scanned_at="2026-06-27T12:34:56Z",
        graph_mtime=None,
        decisions_total=0,
        bindings_total=0,
    )
    assert r.unable_reason is None


def test_epoch_to_iso_helper_matches_datetime() -> None:
    """The internal ``_epoch_to_iso`` helper must format Z-suffixed ISO."""
    epoch = 1751000000.0
    expected = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    assert _epoch_to_iso(epoch) == expected


# ---- T4.3 — classify_binding 2-arg signature + legacy wrapper ------------


def test_classify_binding_2arg_signature() -> None:
    """v0.8.0 canonical: ``classify_binding(ref, graph_nodes)`` derives
    current_id_map internally.
    """
    binding = _ref()
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    result = classify_binding(binding, nodes)
    assert result is DriftClass.STILL_VALID


# v0.9.0 (REQ-V9.3): classify_binding_legacy 3-arg compat wrapper was
# removed in v0.9.0. The v0.8.0 fixture that exercised the wrapper
# (test_classify_binding_legacy_3arg_emits_deprecation_warning) is
# deleted; the canonical 2-arg surface is exercised in
# test_classify_binding_2arg_signature + test_classify_binding_2arg_unable_to_verify_when_nodes_empty below.
# See tests/unit/test_decision_drift_v090_hardening.py for the v0.9.0
# assertion that ``classify_binding_legacy`` no longer exists.


def test_classify_binding_2arg_unable_to_verify_when_nodes_empty() -> None:
    """2-arg with empty graph_nodes -> UNABLE_TO_VERIFY (terminal state)."""
    binding = _ref()
    result = classify_binding(binding, {})
    assert result is DriftClass.UNABLE_TO_VERIFY
