"""Unit tests for ``observability.aggregate`` + the new ``aggregate_many`` helper.

Change #6 PR#2 T2.3 reconciles the W5 carry-forward flagged in
``openspec/changes/archive/2026-06-27-observability-pr1/archive-report-pr1.md``
line 78: PR#1's ``aggregate(values, percentile=95) -> float`` (sorted-index
lookup) is correct for the existing test contract but design D7 specifies
``aggregate(values, percentiles: list[int]) -> dict[int, float]`` for batch G
multi-percentile use.

The PR#2 T2.3 reconciliation keeps the single-percentile ``aggregate``
backward-compatible (existing PR#1 tests stay green) and ADDS a new
``aggregate_many(values, percentiles: list[int]) -> dict[int, float]``
helper that batch G can consume without breaking the PR#1 contract.

Also covers the ``--window`` integration on ``flow metrics export`` (REQ-36
composition with REQ-38; T2.3 acceptance criteria: ``--prometheus`` honors
ALL active filter flags).

Tests are written BEFORE the implementation per strict TDD.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering import observability
from flow_engineering.cli import main

runner = CliRunner()


# ---------- helpers ----------


def _write_jsonl(path: Path, events: list[dict]) -> None:
    """Write a JSONL sink file with the given events (one per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- aggregate() backward-compat (PR#1 contract) ----------


class TestAggregateBackwardCompat:
    """The single-percentile ``aggregate`` keeps its PR#1 contract."""

    def test_aggregate_unchanged_backward_compat(self) -> None:
        """``aggregate(values, percentile=95)`` returns a single float (PR#1)."""
        values = list(range(1, 101))  # 1..100

        p50 = observability.aggregate(values, 50)
        p95 = observability.aggregate(values, 95)
        p99 = observability.aggregate(values, 99)

        # PR#1 contract: floor-int sorted-index lookup.
        assert p50 == 50.0
        assert p95 == 95.0
        assert p99 == 99.0

    def test_aggregate_single_percentile_returns_float_not_dict(self) -> None:
        """``aggregate`` returns ``float``, NEVER a dict (type contract)."""
        result = observability.aggregate([1.0, 2.0, 3.0], 95)

        assert isinstance(result, float)
        assert not isinstance(result, dict)


# ---------- aggregate_many() new helper (PR#2 T2.3) ----------


class TestAggregateMany:
    """``aggregate_many`` returns ``dict[int, float]`` for multi-percentile use."""

    def test_aggregate_many_returns_dict_for_multiple_percentiles(self) -> None:
        """``aggregate_many(values, [50, 95, 99])`` returns dict mapping pct -> float."""
        values = list(range(1, 101))  # 1..100

        result = observability.aggregate_many(values, [50, 95, 99])

        assert isinstance(result, dict)
        assert set(result.keys()) == {50, 95, 99}
        assert all(isinstance(v, float) for v in result.values())
        # Floor-int sorted-index lookup (PR#1 contract inherited).
        assert result[50] == 50.0
        assert result[95] == 95.0
        assert result[99] == 99.0

    def test_aggregate_many_handles_empty_values(self) -> None:
        """Empty input → dict with all-zero values (zero-filled, NOT raising)."""
        result = observability.aggregate_many([], [50, 95, 99])

        assert result == {50: 0.0, 95: 0.0, 99: 0.0}

    def test_aggregate_many_with_p50_p95_p99_matches_aggregate_individually(
        self,
    ) -> None:
        """``aggregate_many`` results agree with ``aggregate`` for each percentile."""
        values = [42, 17, 88, 3, 56, 91, 24, 67, 12, 80]

        many = observability.aggregate_many(values, [50, 95, 99])

        assert many[50] == observability.aggregate(values, 50)
        assert many[95] == observability.aggregate(values, 95)
        assert many[99] == observability.aggregate(values, 99)

    def test_aggregate_many_with_single_percentile_list(self) -> None:
        """``aggregate_many(values, [95])`` returns a 1-key dict."""
        # 100 elements so the floor-int sorted-index lookup hits the
        # tail of the sorted list deterministically.
        values = [float(i) for i in range(1, 101)]  # 1..100

        result = observability.aggregate_many(values, [95])

        assert result == {95: 95.0}

    def test_aggregate_many_invalid_percentile_raises(self) -> None:
        """``aggregate_many(values, [50, 95, 999])`` raises ``ValueError`` on invalid pct."""
        with pytest.raises(ValueError):
            observability.aggregate_many([1.0, 2.0], [999])


# ---------- window integration on flow metrics export (T2.3 acceptance) ----------


class TestWindowIntegrationOnExport:
    """``flow metrics export --window=1h`` composes with the prometheus format."""

    def test_window_filter_integration_with_export(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--window=1h`` filters BEFORE prometheus_exposition is invoked."""
        metrics_file = tmp_path / "metrics.jsonl"
        now = datetime.now(UTC)
        # 4 fresh events (within 60min) + 1 old event (>60min).
        _write_jsonl(metrics_file, [
            {"name": "old_counter", "fields": {"count": 1}, "ts": _iso(now.replace(hour=0))},
            {"name": "fresh_a", "fields": {"count": 1}, "ts": _iso(now)},
            {"name": "fresh_b", "fields": {"count": 2}, "ts": _iso(now)},
            {"name": "fresh_c", "fields": {"count": 3}, "ts": _iso(now)},
            {"name": "fresh_d", "fields": {"count": 5}, "ts": _iso(now)},
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, [
                "metrics", "export", "--format", "prometheus",
                "--window", "1h",
            ],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        # Old event MUST be excluded.
        assert "flow_old_counter" not in result.output
        # Fresh events MUST be present and SUMMED per (name, label) group.
        assert "flow_fresh_a 1.0" in result.output
        assert "flow_fresh_b 2.0" in result.output
        assert "flow_fresh_c 3.0" in result.output
        assert "flow_fresh_d 5.0" in result.output

    def test_window_filter_with_domain_composes_and_style(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--window`` AND ``--domain`` AND ``--format prometheus`` compose (D9)."""
        metrics_file = tmp_path / "metrics.jsonl"
        now = datetime.now(UTC)
        _write_jsonl(metrics_file, [
            {"name": "snapshot_create_total", "fields": {"count": 1}, "ts": _iso(now)},
            {"name": "snapshot_prune_total", "fields": {"count": 1}, "ts": _iso(now)},
            {"name": "drift_invoked_total", "fields": {"count": 1}, "ts": _iso(now)},
            {"name": "snapshot_create_total",
             "fields": {"count": 1},
             "ts": _iso(now.replace(hour=0))},  # outside 1h window
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, [
                "metrics", "export", "--format", "prometheus",
                "--window", "1h", "--domain", "snapshot",
            ],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        # snapshot counters within window appear.
        assert "# HELP flow_snapshot_create_total" in result.output
        assert "# HELP flow_snapshot_prune_total" in result.output
        # Non-snapshot counter MUST be excluded (domain filter).
        assert "flow_drift_invoked_total" not in result.output
        # Out-of-window event MUST be excluded (window filter).
        # Cumulative in-window snapshot_create_total = 1 (only 1 in-window event).
        assert "flow_snapshot_create_total 1.0" in result.output
