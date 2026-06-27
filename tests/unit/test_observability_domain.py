"""Unit tests for the cross-domain slice helpers added in change #6 PR#1 batch C T1.6.

REQ-37 foundation: ``DOMAIN_BY_PREFIX`` expansion to 8 unique domain values
(binding, backfill, drift, vector, federated, snapshot, metadata, engine),
plus a :func:`observability.validate_domain` helper and an :data:`ALL_DOMAINS`
tuple exported as the canonical list. The existing
:func:`observability.read_events_by_domain` automatically picks up new
entries because the function iterates :data:`DOMAIN_BY_PREFIX`.

Coverage:
- :data:`observability.DOMAIN_BY_PREFIX` covers all 8 unique domain values.
- :data:`observability.ALL_DOMAINS` is the canonical 8-tuple.
- :func:`observability.validate_domain` accepts known; raises on unknown.
- :func:`observability.read_events_by_domain` picks up the new
  ``backfill`` and ``engine`` entries transparently.

Tests are written BEFORE the implementation per strict TDD
(RED → GREEN → REFACTOR).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flow_engineering import observability


# ---------- helpers ----------


def _write_jsonl(path: Path, events: list[dict]) -> None:
    """Write a JSONL sink file with the given events (one per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")


def _event(name: str, ts: str = "2026-06-27T00:00:00Z") -> dict:
    """Build a single event dict matching the JSONL sink contract."""
    return {"name": name, "fields": {}, "ts": ts}


# ---------- DOMAIN_BY_PREFIX + ALL_DOMAINS ----------


class TestDomainByPrefixExpansion:
    """DOMAIN_BY_PREFIX covers all 8 unique domain values (REQ-37 / T1.6)."""

    def test_domain_by_prefix_has_eight_unique_values(self) -> None:
        """The lookup table covers all 8 unique domain values.

        Required values: binding, backfill, drift, vector, federated,
        snapshot, metadata, engine. The ``engine`` slot is RESERVED for
        REQ-42 (``engine_*`` counters deferred to v1.1 per design D5).
        """
        unique_values = set(observability.DOMAIN_BY_PREFIX.values())
        expected = {
            "binding", "backfill", "drift", "vector",
            "federated", "snapshot", "metadata", "engine",
        }
        assert expected.issubset(unique_values), (
            f"missing domains: {expected - unique_values}; "
            f"present: {unique_values}"
        )

    def test_all_domains_includes_original_four(self) -> None:
        """ALL_DOMAINS covers the 4 original domains (REQ-8/REQ-12/REQ-22/REQ-26)."""
        for original in ("binding", "drift", "vector", "snapshot"):
            assert original in observability.ALL_DOMAINS, (
                f"ALL_DOMAINS missing original domain {original!r}; "
                f"got {observability.ALL_DOMAINS!r}"
            )

    def test_all_domains_includes_new_four_extensions(self) -> None:
        """ALL_DOMAINS covers the 4 new domain extensions.

        New domains per REQ-37 cross-domain slice expansion:
        backfill (REQ-8 close coverage counters), federated (REQ-26),
        metadata (REQ-13/REQ-24), engine (REQ-42 reserved).
        """
        for new_domain in ("backfill", "federated", "metadata", "engine"):
            assert new_domain in observability.ALL_DOMAINS, (
                f"ALL_DOMAINS missing new domain {new_domain!r}; "
                f"got {observability.ALL_DOMAINS!r}"
            )

    def test_all_domains_has_exactly_eight_entries(self) -> None:
        """ALL_DOMAINS is exactly 8 entries — the canonical list."""
        assert len(observability.ALL_DOMAINS) == 8, (
            f"expected 8 ALL_DOMAINS entries; got {len(observability.ALL_DOMAINS)}: "
            f"{observability.ALL_DOMAINS!r}"
        )


# ---------- validate_domain ----------


class TestValidateDomain:
    """validate_domain(domain) returns the domain; raises ValueError on unknown."""

    def test_validate_domain_accepts_all_eight(self) -> None:
        """Each canonical domain name is accepted and returned unchanged."""
        for domain in observability.ALL_DOMAINS:
            assert observability.validate_domain(domain) == domain, (
                f"validate_domain({domain!r}) returned non-matching value"
            )

    def test_validate_domain_raises_with_helpful_message_on_invalid(self) -> None:
        """Unknown domain raises ValueError listing the valid domains."""
        with pytest.raises(ValueError) as excinfo:
            observability.validate_domain("nonexistent")
        msg = str(excinfo.value)
        # The error message must reference the invalid value AND list
        # every valid domain so the operator can self-correct.
        assert "nonexistent" in msg, (
            f"error message missing invalid value: {msg!r}"
        )
        for valid in observability.ALL_DOMAINS:
            assert valid in msg, (
                f"valid domain {valid!r} missing from error: {msg!r}"
            )


# ---------- read_events_by_domain picks up new entries ----------


class TestReadEventsByDomainExpansion:
    """read_events_by_domain picks up new entries from DOMAIN_BY_PREFIX."""

    def test_read_events_by_domain_filters_correctly_for_backfill(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`--domain=backfill` returns ONLY ``backfill_*`` events.

        Regression check: ensures the backfill entry added in batch A still
        filters correctly. Other domains (binding, drift, snapshot) MUST be
        excluded from the result.
        """
        path = tmp_path / "metrics.jsonl"
        _write_jsonl(path, [
            _event("backfill_observations_total"),
            _event("backfill_with_refs_total"),
            _event("binding_suggest_invoked_total"),
            _event("drift_invoked_total"),
            _event("snapshot_create_total"),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = observability.read_events_by_domain("backfill")
        names = [m.counter_name for m in result]
        assert names == [
            "backfill_observations_total",
            "backfill_with_refs_total",
        ], f"backfill filter leaked non-matching counters: {names!r}"

    def test_read_events_by_domain_filters_correctly_for_engine(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`--domain=engine` returns empty list (RESERVED slot, no v1 counters).

        The ``engine`` domain is reserved for REQ-42 deferred
        ``engine_*`` counters; v1 emits none, so the filter result is empty.
        """
        path = tmp_path / "metrics.jsonl"
        _write_jsonl(path, [
            _event("binding_suggest_invoked_total"),
            _event("drift_invoked_total"),
            _event("vector_search_invoked_total"),
            _event("backfill_observations_total"),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = observability.read_events_by_domain("engine")
        assert result == [], (
            f"engine domain should be empty in v1; got {[m.counter_name for m in result]!r}"
        )