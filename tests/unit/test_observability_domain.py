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


def _event(name: str, ts: str = "2026-06-27T00:00:00Z", fields: dict | None = None) -> dict:
    """Build a single event dict matching the JSONL sink contract."""
    return {"name": name, "fields": fields or {}, "ts": ts}


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
            _event("suggest_invoked_total"),
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
            _event("suggest_invoked_total"),
            _event("drift_invoked_total"),
            _event("vector_search_invoked_total"),
            _event("backfill_observations_total"),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = observability.read_events_by_domain("engine")
        assert result == [], (
            f"engine domain should be empty in v1; got {[m.counter_name for m in result]!r}"
        )


# ---------- C1 regression: production counter names land in the binding domain ----------


class TestDomainByPrefixProductionCounters:
    """Regression: real production counter names land in their owning domain.

    The C1 fix from sdd-verify PR#1: production counter names emitted by
    ``auto_suggest_code_refs.py`` (``suggest_*`` / ``bindings_*``),
    ``cli.py`` (``inspect_*``), and the backfill coverage counters must
    each resolve to the correct domain via :data:`DOMAIN_BY_PREFIX`.
    Prior to the fix, ``suggest_/bindings_/inspect_`` were NOT registered,
    so six production counters fell into the ``unknown`` bucket on a
    real ``~/.flow-engineering/metrics.jsonl``.
    """

    def test_suggest_counters_route_to_binding_domain(self) -> None:
        """``suggest_invoked_total`` + ``suggest_hit_total`` resolve to ``binding``.

        The ``suggest_`` prefix is the production emission from
        ``auto_suggest_code_refs.py:200``. Prior to the C1 fix, these
        counters fell into ``unknown`` and the binding-domain dashboard
        reported zero entries.
        """
        for name in ("suggest_invoked_total", "suggest_hit_total", "suggest_miss_total"):
            assert observability._domain_for_counter(name) == "binding", (
                f"{name!r} should resolve to binding domain; "
                f"got {observability._domain_for_counter(name)!r}"
            )

    def test_bindings_counters_route_to_binding_domain(self) -> None:
        """``bindings_confirmed_total`` resolves to ``binding`` (note the ``s``).

        The ``bindings_`` prefix is the production emission from
        ``auto_suggest_code_refs.py:113-114``. The plural ``bindings_``
        (with trailing ``s``) is canonical; a singular ``binding_``
        prefix would be a typo.
        """
        assert observability._domain_for_counter("bindings_confirmed_total") == "binding", (
            "bindings_confirmed_total must resolve to binding domain"
        )

    def test_inspect_counters_route_to_binding_domain(self) -> None:
        """``inspect_invoked_total`` + ``inspect_render_ms`` resolve to ``binding``.

        The ``inspect_`` prefix is the production emission from
        ``cli.py:945-950``. Two counters share the prefix: invocation
        count (``_total``) and render time (``_ms``).
        """
        assert observability._domain_for_counter("inspect_invoked_total") == "binding"
        assert observability._domain_for_counter("inspect_render_ms") == "binding"

    def test_summarize_production_counters_group_into_binding_domain(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """End-to-end: a real-shape JSONL with production counters groups under ``binding``.

        This is the same scenario the verify report reproduced against
        ``~/.flow-engineering/metrics.jsonl``: six production counters
        (two ``suggest_``, one ``bindings_``, two ``inspect_``, one
        ``backfill_``) MUST all resolve to the ``binding`` (5) and
        ``backfill`` (1) domains respectively — NOT the ``unknown``
        bucket. Without the C1 fix, every counter lands under
        ``unknown``.
        """
        path = tmp_path / "metrics.jsonl"
        _write_jsonl(path, [
            _event("suggest_invoked_total", fields={"count": 1477}),
            _event("suggest_hit_total", fields={"count": 2532}),
            _event("bindings_confirmed_total", fields={"count": 2532}),
            _event("inspect_invoked_total", fields={"count": 1}),
            _event("inspect_render_ms", fields={"elapsed_ms": 0}),
            _event("backfill_observations_total", fields={"count": 42}),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        events = observability.read_all_metrics()
        summary = observability.summarize(events)

        # All five binding-domain counters MUST appear under the
        # ``binding`` key (not ``unknown``). This is the regression gate.
        assert "binding" in summary, (
            f"binding domain missing; counters fell into unknown: {summary!r}"
        )
        assert summary["binding"]["suggest_invoked_total"] == 1477
        assert summary["binding"]["suggest_hit_total"] == 2532
        assert summary["binding"]["bindings_confirmed_total"] == 2532
        assert summary["binding"]["inspect_invoked_total"] == 1
        # inspect_render_ms carries ``elapsed_ms`` rather than ``count``;
        # summarize() defaults the contribution to 1 per occurrence.
        assert "inspect_render_ms" in summary["binding"]
        # The backfill counter lands under its own domain.
        assert summary["backfill"]["backfill_observations_total"] == 42
        # And NO counter landed under ``unknown`` (the pre-C1 regression).
        assert "unknown" not in summary, (
            f"unexpected unknown bucket — C1 regression: {summary!r}"
        )