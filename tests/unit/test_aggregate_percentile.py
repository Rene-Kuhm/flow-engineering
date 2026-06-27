"""Unit tests for ``observability.aggregate_percentile`` + ``ReservoirSampler`` (REQ-39 / D7).

Change #6 PR#2 batch G T2.4 lands the reservoir-sampling-based percentile
aggregator that the spec REQ-39 ``flow metrics aggregate`` CLI subcommand
(T2.5) consumes. The contract:

- ``ReservoirSampler`` — Vitter's Algorithm R (O(1) per add, O(N) memory
  ceiling = ``capacity``). Deterministic when ``seed`` is provided.
- ``aggregate_percentile(events, *, percentiles, reservoir_size, seed)`` —
  groups events by counter name, builds a reservoir per counter, computes
  the requested percentiles via floor() sorted-index lookup, returns
  ``dict[str, float]`` mapping ``"{counter_name}_p{N}"`` to the value.
- ``format_percentile_report(result)`` — renders the dict as an aligned
  text table with one row per counter and one column per percentile.

When a counter has fewer than 2 samples, the function returns ``0.0`` for
each requested percentile (defensive — callers can detect via the dict
key set).

Tests are written BEFORE the implementation per strict TDD
(RED → GREEN → REFACTOR cycle).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flow_engineering import observability


# ---------- ReservoirSampler ----------


class TestReservoirSampler:
    """The ``ReservoirSampler`` class implements Vitter's Algorithm R."""

    def test_reservoir_sampler_keeps_capacity_limit(self) -> None:
        """When more than ``capacity`` values are added, the reservoir size stays at capacity."""
        sampler = observability.ReservoirSampler(capacity=10)

        for i in range(100):
            sampler.add(float(i))

        assert len(sampler.values()) == 10
        assert len(sampler) == 100  # _seen tracks total, not retained

    def test_reservoir_sampler_uniform_distribution(self) -> None:
        """1000 inputs of {0.0, 1.0, ..., 99.0} into a 100-slot reservoir with fixed seed.

        With Vitter's algorithm + a fixed seed, the reservoir MUST contain
        exactly 100 distinct values (no duplicates), drawn with approximately
        uniform probability from the 0..999 input range. We assert all 100
        slots are unique and the mean is roughly 499.5 (the input mean).
        """
        sampler = observability.ReservoirSampler(capacity=100, seed=42)

        for i in range(1000):
            sampler.add(float(i))

        samples = sampler.values()
        assert len(samples) == 100
        assert len(set(samples)) == 100, "expected all 100 samples distinct"
        sample_mean = sum(samples) / len(samples)
        # ±10% of the population mean (499.5) is a generous bound for
        # n=1000 / k=100; the seed=42 keeps it deterministic.
        assert math.isclose(sample_mean, 499.5, abs_tol=50.0), (
            f"sample mean {sample_mean} too far from population mean 499.5"
        )

    def test_reservoir_sampler_seeded_is_deterministic(self) -> None:
        """Two samplers with the same seed receive the SAME final sample set."""
        inputs = list(range(50))
        a = observability.ReservoirSampler(capacity=20, seed=7)
        b = observability.ReservoirSampler(capacity=20, seed=7)

        for v in inputs:
            a.add(float(v))
            b.add(float(v))

        assert sorted(a.values()) == sorted(b.values()), (
            f"same seed produced different samples: {a.values()} vs {b.values()}"
        )


# ---------- aggregate_percentile ----------


def _make_event(name: str, fields: dict, ts: datetime | None = None) -> observability.MetricEvent:
    """Helper: build a MetricEvent with an ISO 8601 UTC timestamp."""
    if ts is None:
        ts = datetime.now(UTC)
    return observability.MetricEvent(
        timestamp=ts.timestamp(),
        counter_name=name,
        labels=fields,
        raw_line="",
    )


class TestAggregatePercentile:
    """``aggregate_percentile`` groups events by counter + computes percentiles."""

    def test_aggregate_percentile_p50_p95_p99_returns_correct_dict(self) -> None:
        """100 monotonic events for one counter → floor-index lookup p50/p95/p99.

        With ``range(1, 101)`` (1..100, n=100) and floor(sorted-index)
        lookup: idx = (n-1) * pct / 100 = 99 * pct / 100.
        - p50: idx = 49 → samples[49] = 50.0
        - p95: idx = 94 → samples[94] = 95.0
        - p99: idx = 98 → samples[98] = 99.0
        """
        events = [
            _make_event("drift_invoked_total", {"value": float(i)})
            for i in range(1, 101)
        ]

        result = observability.aggregate_percentile(events)

        assert isinstance(result, dict)
        assert "drift_invoked_total_p50" in result
        assert "drift_invoked_total_p95" in result
        assert "drift_invoked_total_p99" in result
        assert result["drift_invoked_total_p50"] == 50.0
        assert result["drift_invoked_total_p95"] == 95.0
        assert result["drift_invoked_total_p99"] == 99.0
        # Every value is a float (not a list or dict).
        for v in result.values():
            assert isinstance(v, float)

    def test_aggregate_percentile_handles_empty_events(self) -> None:
        """Empty input → empty dict (NO counters yielded percentiles)."""
        result = observability.aggregate_percentile([])

        assert result == {}

    def test_aggregate_percentile_handles_single_value(self) -> None:
        """One event for a counter → 0.0 for each percentile (defensive default)."""
        events = [_make_event("drift_invoked_total", {"value": 42.0})]

        result = observability.aggregate_percentile(events)

        # Single-sample: every percentile returns 0.0 per the task brief
        # contract ("If a counter has fewer than 2 values, returns 0.0").
        assert result["drift_invoked_total_p50"] == 0.0
        assert result["drift_invoked_total_p95"] == 0.0
        assert result["drift_invoked_total_p99"] == 0.0

    def test_aggregate_percentile_separates_counters_correctly(self) -> None:
        """Two counters each with 100 monotonic events → independent percentile dicts."""
        events: list[observability.MetricEvent] = []
        for i in range(1, 101):
            events.append(_make_event("drift_invoked_total", {"value": float(i)}))
            events.append(_make_event("snapshot_create_total", {"value": float(i * 2)}))

        result = observability.aggregate_percentile(events)

        # drift_invoked_total: 1..100 → p50=50, p95=95, p99=99
        assert result["drift_invoked_total_p50"] == 50.0
        assert result["drift_invoked_total_p95"] == 95.0
        assert result["drift_invoked_total_p99"] == 99.0
        # snapshot_create_total: 2,4,6,...,200 → p50=100, p95=190, p99=198
        assert result["snapshot_create_total_p50"] == 100.0
        assert result["snapshot_create_total_p95"] == 190.0
        assert result["snapshot_create_total_p99"] == 198.0

    def test_aggregate_percentile_uses_reservoir_when_stream_exceeds_capacity(
        self,
    ) -> None:
        """1000 events into a reservoir of size 100 with seed=1 → deterministic percentiles."""
        events = [
            _make_event("big_counter", {"value": float(i)})
            for i in range(1, 1001)
        ]

        result = observability.aggregate_percentile(
            events, reservoir_size=100, seed=1,
        )

        # The reservoir holds 100 distinct samples from 1..1000. The
        # mean of the samples is approximately 500.5 (the population
        # mean) ± a sampling error. We assert p50 falls within a
        # generous 400..600 window — strict-TDD triangulation: a real
        # GREEN requires the reservoir path to actually execute and
        # produce a sample, not a degenerate constant.
        p50 = result["big_counter_p50"]
        assert 400.0 <= p50 <= 600.0, (
            f"expected reservoir-derived p50 near 500; got {p50}"
        )
        # P95 should land in the upper portion of the sorted sample.
        p95 = result["big_counter_p95"]
        assert p95 > p50, (
            f"expected p95 > p50 (counter-monotonic); got p50={p50}, p95={p95}"
        )


# ---------- format_percentile_report ----------


class TestFormatPercentileReport:
    """``format_percentile_report`` renders an aligned text table."""

    def test_format_percentile_report_renders_aligned_table(self) -> None:
        """3 counters × 3 percentiles → header + 3 data rows with column alignment."""
        result = {
            "drift_invoked_total_p50": 50.0,
            "drift_invoked_total_p95": 95.0,
            "drift_invoked_total_p99": 99.0,
            "snapshot_create_total_p50": 1.0,
            "snapshot_create_total_p95": 3.0,
            "snapshot_create_total_p99": 5.0,
            "vector_latency_ms_p50": 25.0,
            "vector_latency_ms_p95": 75.0,
            "vector_latency_ms_p99": 95.0,
        }

        table = observability.format_percentile_report(result)

        # Header line contains the percentile columns.
        lines = table.splitlines()
        assert len(lines) >= 4, f"expected at least 4 lines (header + 3 rows); got {table!r}"
        assert "Counter" in lines[0]
        assert "p50" in lines[0]
        assert "p95" in lines[0]
        assert "p99" in lines[0]
        # Each counter name appears once on its own line.
        for counter in ("drift_invoked_total", "snapshot_create_total", "vector_latency_ms"):
            matching = [line for line in lines if counter in line]
            assert len(matching) == 1, (
                f"expected exactly 1 row for {counter!r}; got {matching!r}"
            )
            row = matching[0]
            assert "50" in row or "25" in row  # at least one numeric
        # All 3 percentile values for the snapshot counter appear in its row.
        snap_row = next(line for line in lines if "snapshot_create_total" in line)
        assert "1.0" in snap_row
        assert "3.0" in snap_row
        assert "5.0" in snap_row

    def test_format_percentile_report_empty_dict_emits_no_rows(self) -> None:
        """Empty input → table with only the header line (no data rows)."""
        table = observability.format_percentile_report({})

        lines = table.splitlines()
        assert len(lines) == 1, f"expected 1-line table (header only); got {table!r}"
        assert "Counter" in lines[0]


# ---------- CLI integration smoke (sanity check; full coverage in test_cli_metrics_aggregate.py) ----------


def test_aggregate_percentile_smoke_does_not_break_baseline(tmp_path: Path) -> None:
    """Sanity: aggregate_percentile is importable + callable without touching the file sink.

    Ensures the new public API coexists with the existing read-side helpers
    (no import-time side effects; no global state pollution).
    """
    # The function is pure; no need to set FLOW_METRICS_PATH for an in-memory call.
    events = [_make_event("smoke_counter", {"value": 1.0})]
    result = observability.aggregate_percentile(events)

    assert isinstance(result, dict)
    assert "smoke_counter_p95" in result
