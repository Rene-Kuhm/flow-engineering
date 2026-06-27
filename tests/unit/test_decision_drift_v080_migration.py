"""REQ-56 W8 / REQ-57 v0.8.0 dataclass migration tests.

T4.1, T4.2, T4.3 RED fixtures for the v0.8.0 BREAKING dataclass shape
migration in ``decision_drift``. Each fixture asserts one of:

- ``Finding.decision_id`` is now ``int`` (was ``str``); ``from_legacy``
  classmethod accepts legacy ``str`` inputs and emits
  ``DeprecationWarning`` while coercing via ``int()``.
- ``DriftReport.scanned_at`` is now ``str`` ISO 8601 (was ``float``
  epoch); ``from_legacy`` classmethod accepts legacy ``float`` epoch
  inputs and coerces via the internal ``_epoch_to_iso`` helper.
- ``classify_binding`` now has a 2-arg ``(ref, graph_nodes)`` signature
  (was 3-arg ``(binding, current_nodes, current_id_map)``);
  ``classify_binding_legacy`` retains the 3-arg signature with a
  ``DeprecationWarning`` shim.

All v0.8.0 canonical surfaces must accept the new types; the legacy
factories are the migration path for any v0.7.x caller still passing
``str`` / ``float`` / 3 args.

Refs: openspec/changes/drift-hardening/{spec,design,tasks}.md T4.1..T4.3.
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
    classify_binding_legacy,
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


def test_finding_from_legacy_emits_deprecation_warning() -> None:
    """v0.7.x callers using ``Finding.from_legacy(decision_id="42", ...)``
    must see a DeprecationWarning that points at the v0.9.0 migration.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        f = Finding.from_legacy(
            decision_id="42",
            binding=_ref(),
            drift_class=DriftClass.STILL_VALID,
            detail="ok",
        )
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecations, "from_legacy(str) must emit DeprecationWarning"
    assert "decision_id" in str(deprecations[0].message)
    assert "v0.9.0" in str(deprecations[0].message)


def test_finding_from_legacy_coerces_str_to_int() -> None:
    """v0.7.x str "42" must coerce to int 42 via ``from_legacy``."""
    f = Finding.from_legacy(
        decision_id="42",
        binding=_ref(),
        drift_class=DriftClass.STILL_VALID,
        detail="ok",
    )
    assert f.decision_id == 42
    assert isinstance(f.decision_id, int)


def test_finding_from_legacy_non_numeric_str_raises() -> None:
    """Non-numeric legacy str ("not-a-number") must raise ValueError so
    callers see the migration signal instead of a silent ``0`` coercion.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with pytest.raises(ValueError):
            Finding.from_legacy(
                decision_id="not-a-number",
                binding=_ref(),
                drift_class=DriftClass.STILL_VALID,
                detail="ok",
            )


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


def test_drift_report_from_legacy_emits_deprecation_warning() -> None:
    """v0.7.x callers using ``DriftReport.from_legacy(scanned_at=0.0, ...)``
    must see a DeprecationWarning.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        r = DriftReport.from_legacy(
            change_name="obs",
            scanned_at=0.0,
        )
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecations, "from_legacy(float) must emit DeprecationWarning"
    assert "scanned_at" in str(deprecations[0].message)


def test_drift_report_from_legacy_converts_epoch_to_iso() -> None:
    """v0.7.x float epoch must coerce to ISO 8601 str via from_legacy."""
    epoch = 1751000000.0
    r = DriftReport.from_legacy(
        change_name="obs",
        scanned_at=epoch,
    )
    # ISO format expected: datetime.fromtimestamp(epoch, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    expected = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    assert r.scanned_at == expected
    assert isinstance(r.scanned_at, str)


def test_drift_report_from_legacy_handles_unable_to_verify_alias() -> None:
    """v0.7.x callers using ``unable_to_verify=True`` kwarg must map to
    the v0.8.0 ``graph_unavailable`` field.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        r = DriftReport.from_legacy(
            change_name="obs",
            scanned_at=0.0,
            unable_to_verify=True,
        )
    assert r.graph_unavailable is True


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


def test_classify_binding_legacy_3arg_emits_deprecation_warning() -> None:
    """v0.7.x 3-arg callers must see a DeprecationWarning and still work."""
    binding = _ref()
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    id_map = {
        "src_auth_jwt_jwttokenmanager": ("src/auth/jwt.py", 42, "JWTTokenManager"),
    }
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = classify_binding_legacy(binding, nodes, id_map)
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecations, "3-arg classify_binding_legacy must emit DeprecationWarning"
    assert result is DriftClass.STILL_VALID


def test_classify_binding_2arg_unable_to_verify_when_nodes_empty() -> None:
    """2-arg with empty graph_nodes -> UNABLE_TO_VERIFY (terminal state)."""
    binding = _ref()
    result = classify_binding(binding, {})
    assert result is DriftClass.UNABLE_TO_VERIFY
