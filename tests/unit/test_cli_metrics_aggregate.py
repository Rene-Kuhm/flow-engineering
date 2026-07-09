"""Unit tests for the ``flow metrics aggregate`` CLI subcommand (REQ-39 / D7).

Change #6 PR#2 batch G T2.5 lands a NEW dedicated subcommand
``flow metrics aggregate`` that consumes the :func:`aggregate_percentile`
helper from T2.4 and emits the result in either aligned text (default)
or machine-readable JSON. The subcommand is distinct from the legacy
``--percentile`` flag pipeline (which would re-use ``aggregate`` +
``aggregate_many``): the ``aggregate`` subcommand applies RESERVOIR
SAMPLING so operators can run it over arbitrarily-large JSONL sinks
without unbounded memory growth.

CLI surface (per task brief):

- ``--percentile`` — repeatable ``click.Choice(["p50", "p95", "p99"])``
  flag. Default: ``("p95",)`` (single value). Multiple allowed.
- ``--window`` / ``--since`` / ``--until`` / ``--domain`` — filter flags
  reusing the same parser as ``flow metrics summary`` / ``flow metrics export``.
- ``--reservoir-size`` — sample-size ceiling (default ``1000``).
- ``--format`` — ``text`` (default aligned table) or ``json``.

Exit-code mapping (D9):
- 0: success (including empty input per D8 default-empty contract).
- 2: invalid flag value (Click ``click.Choice`` validation failure).

Tests are written BEFORE the implementation per strict TDD
(RED → GREEN → REFACTOR cycle).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

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


def _make_events(name: str, values: list[float], ts: datetime | None = None) -> list[dict]:
    """Build a list of JSONL event dicts for ``name`` with the given numeric ``values``."""
    if ts is None:
        ts = datetime.now(UTC)
    return [
        {"name": name, "fields": {"value": v}, "ts": _iso(ts)}
        for v in values
    ]


# ---------- happy-path text format ----------


class TestMetricsAggregateText:
    """``flow metrics aggregate`` default text format emits the aligned table."""

    def test_metrics_aggregate_default_p95_text_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Default invocation emits an aligned table containing the counter name + p95 value."""
        metrics_file = tmp_path / "metrics.jsonl"
        events = _make_events("drift_invoked_total", [float(i) for i in range(1, 101)])
        _write_jsonl(metrics_file, events)
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(main, ["metrics", "aggregate"])

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        # Counter name + percentile column MUST appear in the output.
        assert "drift_invoked_total" in result.output
        assert "p95" in result.output
        # Default p95 of 1..100 is 95.0 (floor sorted-index lookup).
        assert "95" in result.output

    def test_metrics_aggregate_multiple_percentiles(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--percentile p50 --percentile p99`` emits a table with both columns."""
        metrics_file = tmp_path / "metrics.jsonl"
        events = _make_events("drift_invoked_total", [float(i) for i in range(1, 101)])
        _write_jsonl(metrics_file, events)
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, [
                "metrics", "aggregate",
                "--percentile", "p50",
                "--percentile", "p99",
            ],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        # The header always carries the p50/p95/p99 labels (per the
        # format_percentile_report contract). The requested percentiles
        # are populated; unrequested columns are blank.
        assert "p50" in result.output
        assert "p99" in result.output
        # p50 = 50.0, p99 = 99.0 for 1..100 monotonic.
        assert "50" in result.output
        assert "99" in result.output


# ---------- filters ----------


class TestMetricsAggregateFilters:
    """``flow metrics aggregate`` honors ``--window`` / ``--domain`` filter flags."""

    def test_metrics_aggregate_with_window_filter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--window=1h`` filters BEFORE reservoir sampling (out-of-window events excluded)."""
        metrics_file = tmp_path / "metrics.jsonl"
        now = datetime.now(UTC)
        # 50 fresh (in-window) + 50 stale (out-of-window).
        fresh = _make_events(
            "fresh_counter", [float(i) for i in range(1, 51)], ts=now,
        )
        stale = _make_events(
            "stale_counter", [float(i) for i in range(51, 101)],
            ts=now - timedelta(hours=2),  # outside 1h window
        )
        _write_jsonl(metrics_file, fresh + stale)
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, ["metrics", "aggregate", "--window", "1h"],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        assert "fresh_counter" in result.output
        assert "stale_counter" not in result.output


# ---------- JSON format ----------


class TestMetricsAggregateJson:
    """``--format json`` emits the result as a flat JSON dict."""

    def test_metrics_aggregate_json_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--format json`` emits ``{counter_p{N}: value}`` JSON dict to stdout."""
        metrics_file = tmp_path / "metrics.jsonl"
        events = _make_events("drift_invoked_total", [float(i) for i in range(1, 101)])
        _write_jsonl(metrics_file, events)
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, ["metrics", "aggregate", "--format", "json"],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        # Stdout is valid JSON; parseable into a dict.
        payload = json.loads(result.output)
        assert isinstance(payload, dict)
        assert "drift_invoked_total_p95" in payload
        assert payload["drift_invoked_total_p95"] == 95.0


# ---------- error paths ----------


class TestMetricsAggregateErrors:
    """``flow metrics aggregate`` maps invalid flags to exit code 2 (D9)."""

    def test_metrics_aggregate_invalid_percentile_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--percentile=garbage`` is rejected by ``click.Choice`` → exit 2."""
        metrics_file = tmp_path / "metrics.jsonl"
        _write_jsonl(metrics_file, [])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, ["metrics", "aggregate", "--percentile", "garbage"],
        )

        assert result.exit_code == 2, (
            f"expected exit 2 for invalid --percentile; got {result.exit_code}. "
            f"output={result.output!r}"
        )

    def test_metrics_aggregate_empty_sink_emits_no_counters(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty JSONL sink → empty aggregate result + exit 0 (D8 default-empty)."""
        metrics_file = tmp_path / "metrics.jsonl"
        # File does NOT exist → empty-sink default path.
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(main, ["metrics", "aggregate"])

        assert result.exit_code == 0, (
            f"expected exit 0 (default-empty); got {result.exit_code}. "
            f"output={result.output!r}"
        )
        # Empty result → table with header only, no counter rows.
        assert "Counter" in result.output
        # No percentile values populated.
        assert "drift_invoked_total" not in result.output
