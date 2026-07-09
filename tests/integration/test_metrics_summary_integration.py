"""End-to-end integration tests for `flow metrics summary` (change #6 PR#1 T1.10).

These tests exercise the FULL read pipeline: write fake events to the JSONL
metrics sink via :func:`observability.increment`, run the
``flow metrics summary`` CLI subcommand via Click's ``CliRunner``, and
assert the rendered output / exit code matches the documented contract.

This is the PR#1 closeout integration sweep (T1.10). Per the task brief,
this suite covers REQ-35..37 end-to-end with NO mocking of the read-side
helpers — the only mock surface is the JSONL path (``FLOW_METRICS_PATH``).

Coverage matrix:
- REQ-35: ``flow metrics summary`` renders all 4 active domain headers
- REQ-36: ``--window 1h`` filters to the last 60 minutes
- REQ-37: ``--domain snapshot`` filters to snapshot_* counters only
- D8 default-empty: empty sink → exit 0 + friendly message
- D9 exit codes: ``--window garbage`` exits 2
- Output format: ``--format json`` round-trips through :func:`json.loads`
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering import observability
from flow_engineering.cli import main

runner = CliRunner()


# ---------- helpers ----------


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _event(name: str, fields: dict | None = None, ts: str | None = None) -> dict:
    if ts is None:
        ts = _iso(datetime.now(UTC))
    return {"name": name, "fields": fields or {}, "ts": ts}


def _write_jsonl(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")


def _increment_event(name: str, **fields) -> None:
    observability.increment(name, **fields)


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


# ---------- end-to-end integration tests ----------


class TestIntegrationEndToEndNoWindowNoDomain:
    """24 events across 4 active domains → all 4 domain headers present."""

    def test_integration_end_to_end_no_window_no_domain(
        self,
        metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        # 24 events: 6 each across binding, drift, vector, snapshot.
        events: list[dict] = []
        for _ in range(6):
            events.append(_event("suggest_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(6):
            events.append(_event("drift_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(6):
            events.append(_event("vector_search_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(6):
            events.append(_event("snapshot_create_total", {"count": 1}, _iso(now)))
        _write_jsonl(metrics_path, events)

        result = runner.invoke(main, ["metrics", "summary"])

        assert result.exit_code == 0, result.output
        # All 4 active domains render as their own section header.
        assert "binding:" in result.output
        assert "drift:" in result.output
        assert "vector:" in result.output
        assert "snapshot:" in result.output
        # The counter names appear under their domain.
        assert "suggest_invoked_total" in result.output
        assert "drift_invoked_total" in result.output
        assert "vector_search_invoked_total" in result.output
        assert "snapshot_create_total" in result.output


class TestIntegrationEndToEndWithWindowFilter:
    """30 events spanning 3 days → --window 24h keeps only the last 24h."""

    def test_integration_end_to_end_with_window_filter(
        self,
        metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        events: list[dict] = []
        # 10 events at 3 days ago — outside the 24h window.
        for _ in range(10):
            events.append(
                _event("suggest_invoked_total", {"count": 1}, _iso(now - timedelta(days=3))),
            )
        # 10 events at 36 hours ago — outside the 24h window.
        for _ in range(10):
            events.append(
                _event("drift_invoked_total", {"count": 1}, _iso(now - timedelta(hours=36))),
            )
        # 10 events at "now" — inside the 24h window.
        for _ in range(10):
            events.append(_event("vector_search_invoked_total", {"count": 1}, _iso(now)))
        _write_jsonl(metrics_path, events)

        result = runner.invoke(main, ["metrics", "summary", "--window", "24h"])

        assert result.exit_code == 0, result.output
        # The in-window vector events (count=10) survive.
        assert "vector_search_invoked_total" in result.output
        assert "10" in result.output
        # The out-of-window binding + drift events are excluded.
        assert "suggest_invoked_total" not in result.output
        assert "drift_invoked_total" not in result.output


class TestIntegrationEndToEndWithDomainFilter:
    """24 events across 4 domains → --domain snapshot returns only snapshot."""

    def test_integration_end_to_end_with_domain_filter(
        self,
        metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        events: list[dict] = []
        for _ in range(6):
            events.append(_event("suggest_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(6):
            events.append(_event("drift_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(6):
            events.append(_event("vector_search_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(6):
            events.append(_event("snapshot_create_total", {"count": 1}, _iso(now)))
        _write_jsonl(metrics_path, events)

        result = runner.invoke(main, ["metrics", "summary", "--domain", "snapshot"])

        assert result.exit_code == 0, result.output
        # snapshot_* counters appear in the rendered output.
        assert "snapshot_create_total" in result.output
        # Other-domain counters MUST be excluded.
        assert "suggest_invoked_total" not in result.output
        assert "drift_invoked_total" not in result.output
        assert "vector_search_invoked_total" not in result.output


class TestIntegrationEndToEndEmptyMetricsFile:
    """Empty sink → exit 0 + "No metrics recorded yet." (D8 default-empty contract)."""

    def test_integration_end_to_end_empty_metrics_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "missing_metrics.jsonl"
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = runner.invoke(main, ["metrics", "summary"])

        assert result.exit_code == 0, result.output
        assert "No metrics recorded yet." in result.output


class TestIntegrationEndToEndJsonFormatRoundtrip:
    """12 events → --format json → parses back to a dict matching summarize()."""

    def test_integration_end_to_end_json_format_roundtrip(
        self,
        metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        events: list[dict] = []
        # 6 binding + 6 drift → 12 events, 2 distinct counters.
        for _ in range(6):
            events.append(_event("suggest_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(6):
            events.append(_event("drift_invoked_total", {"count": 1}, _iso(now)))
        _write_jsonl(metrics_path, events)

        result = runner.invoke(main, ["metrics", "summary", "--format", "json"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        # The CLI emits the same shape as observability.summarize(): a
        # nested dict {domain: {counter_name: count}}.
        assert isinstance(payload, dict)
        assert "binding" in payload
        assert "drift" in payload
        assert payload["binding"]["suggest_invoked_total"] == 6
        assert payload["drift"]["drift_invoked_total"] == 6
        # Cross-check the helper directly.
        parsed = observability.read_all_metrics(metrics_path)
        expected = observability.summarize(parsed)
        assert payload == expected


class TestIntegrationEndToEndInvalidWindowExits2:
    """--window invalid → exit code 2 (D9 usage error contract)."""

    def test_integration_end_to_end_invalid_window_exits_2(
        self,
        metrics_path: Path,
    ) -> None:
        result = runner.invoke(main, ["metrics", "summary", "--window", "invalid"])

        assert result.exit_code == 2, result.output


# ---------- PR#2 closeout integration tests (T2.6) ----------
#
# End-to-end coverage of `flow metrics export` (REQ-38) and
# `flow metrics aggregate` (REQ-39) exercised through the full CLI
# pipeline. No mocks beyond the FLOW_METRICS_PATH env override.


class TestIntegrationEndToEndExportPrometheusToStdout:
    """12 events → `flow metrics export --format prometheus` renders textfile format."""

    def test_integration_end_to_end_export_prometheus_to_stdout(
        self,
        metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        events: list[dict] = []
        # 4 distinct counters with cumulative counts summing to 12 events.
        for _ in range(4):
            events.append(_event("suggest_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(3):
            events.append(_event("drift_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(3):
            events.append(_event("vector_search_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(2):
            events.append(_event("snapshot_create_total", {"count": 1}, _iso(now)))
        _write_jsonl(metrics_path, events)

        result = runner.invoke(main, ["metrics", "export", "--format", "prometheus"])

        assert result.exit_code == 0, result.output
        # D6/REQ-38: HELP + TYPE comments precede every metric line.
        assert "# HELP" in result.output
        assert "# TYPE" in result.output
        # The 4 counters each get their own HELP/TYPE block.
        assert "flow_suggest_invoked_total" in result.output
        assert "flow_drift_invoked_total" in result.output
        assert "flow_vector_search_invoked_total" in result.output
        assert "flow_snapshot_create_total" in result.output
        # _total suffix → counter type (D6 priority 2).
        assert "# TYPE flow_suggest_invoked_total counter" in result.output
        assert "# TYPE flow_drift_invoked_total counter" in result.output


class TestIntegrationEndToEndExportToFileAtomic:
    """5 events → `flow metrics export --format prometheus --out PATH` writes atomically."""

    def test_integration_end_to_end_export_to_file_atomic(
        self,
        metrics_path: Path,
        tmp_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        events: list[dict] = []
        for _ in range(2):
            events.append(_event("suggest_invoked_total", {"count": 1}, _iso(now)))
        for _ in range(2):
            events.append(_event("drift_invoked_total", {"count": 1}, _iso(now)))
        events.append(_event("vector_search_invoked_total", {"count": 1}, _iso(now)))
        _write_jsonl(metrics_path, events)

        out = tmp_path / "nested" / "metrics.prom"
        result = runner.invoke(
            main,
            ["metrics", "export", "--format", "prometheus", "--out", str(out)],
        )

        assert result.exit_code == 0, result.output
        # D10: parent dir created on demand; target file exists and is non-empty.
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "# HELP" in content
        assert "# TYPE" in content
        assert "flow_suggest_invoked_total" in content
        assert "flow_drift_invoked_total" in content
        assert "flow_vector_search_invoked_total" in content
        # 3 distinct counters → 3 metric lines (one per counter in the sorted output).
        metric_line_count = sum(
            1 for line in content.splitlines() if line and not line.startswith("#")
        )
        assert metric_line_count == 3


class TestIntegrationEndToEndAggregateDefaultP95:
    """100 events → `flow metrics aggregate --percentile p95` emits p95 column."""

    def test_integration_end_to_end_aggregate_default_p95(
        self,
        metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        events: list[dict] = []
        # 100 monotonic vector latency events from 10..1000.
        for i in range(10, 1001, 10):
            events.append(
                _event(
                    "vector_search_latency_ms",
                    {"value": float(i)},
                    _iso(now),
                ),
            )
        _write_jsonl(metrics_path, events)

        result = runner.invoke(main, ["metrics", "aggregate"])

        assert result.exit_code == 0, result.output
        # Default percentile is p95 (REQ-39 / D7).
        assert "p95" in result.output
        # The table header is rendered (REQ-39 formatter contract).
        assert "Counter" in result.output
        assert "vector_search_latency_ms" in result.output
        # floor(sorted-index) lookup: 100 samples at p95 → index 94 → value 950.
        assert "950" in result.output


class TestIntegrationEndToEndAggregateMultiplePercentiles:
    """100 events → 3 percentile columns in the aggregate table."""

    def test_integration_end_to_end_aggregate_multiple_percentiles(
        self,
        metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        events: list[dict] = []
        # 100 monotonic drift latency events from 10..1000.
        for i in range(10, 1001, 10):
            events.append(
                _event(
                    "drift_scan_duration_ms",
                    {"value": float(i)},
                    _iso(now),
                ),
            )
        _write_jsonl(metrics_path, events)

        result = runner.invoke(
            main,
            [
                "metrics",
                "aggregate",
                "--percentile",
                "p50",
                "--percentile",
                "p95",
                "--percentile",
                "p99",
            ],
        )

        assert result.exit_code == 0, result.output
        # All three percentile columns present (REQ-39 / D7 formatter).
        assert "p50" in result.output
        assert "p95" in result.output
        assert "p99" in result.output
        # floor(sorted-index) lookup: p50 → idx 49 → 500; p95 → idx 94 → 950;
        # p99 → idx 98 → 990.
        assert "500" in result.output
        assert "950" in result.output
        assert "990" in result.output


class TestIntegrationEndToEndExportWithWindowFilter:
    """30 events spanning 3 days → --window 1h keeps only the last 60 minutes."""

    def test_integration_end_to_end_export_with_window_filter(
        self,
        metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        events: list[dict] = []
        # 10 events at 3 days ago — outside the 1h window.
        for _ in range(10):
            events.append(
                _event(
                    "drift_invoked_total",
                    {"count": 1},
                    _iso(now - timedelta(days=3)),
                ),
            )
        # 10 events at 90 minutes ago — outside the 1h window.
        for _ in range(10):
            events.append(
                _event(
                    "drift_invoked_total",
                    {"count": 1},
                    _iso(now - timedelta(minutes=90)),
                ),
            )
        # 10 events at "now" — inside the 1h window.
        for _ in range(10):
            events.append(
                _event(
                    "drift_invoked_total",
                    {"count": 1},
                    _iso(now),
                ),
            )
        _write_jsonl(metrics_path, events)

        result = runner.invoke(
            main,
            ["metrics", "export", "--format", "prometheus", "--window", "1h"],
        )

        assert result.exit_code == 0, result.output
        # The in-window drift_invoked_total events survived (10 events → cumulative value 10).
        assert "flow_drift_invoked_total" in result.output
        # Counter is _total-suffixed → counter type.
        assert "# TYPE flow_drift_invoked_total counter" in result.output
        # The metric line value must reflect ONLY the in-window count (10, not 30).
        # Find the metric line and verify the value is 10 (in-window) not 30 (total).
        # No labels are emitted for events whose fields dict has only "count"
        # (excluded by _LABEL_VALUE_KEYS), so the line shape is "<name> <value>".
        metric_line = next(
            line
            for line in result.output.splitlines()
            if line.startswith("flow_drift_invoked_total") and not line.startswith("#")
        )
        value_str = metric_line.rsplit(" ", 1)[-1]
        assert float(value_str) == 10.0, (
            f"in-window sum must be 10 (got {value_str}); the 20 out-of-window events "
            f"at -90m and -3d MUST be excluded by --window 1h"
        )


class TestIntegrationEndToEndAggregateWithInsufficientData:
    """1 event → 'not enough data points' inline + exit 0 (REQ-39 graceful path)."""

    def test_integration_end_to_end_aggregate_with_insufficient_data(
        self,
        metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        # Exactly 1 event → reservoir cannot produce ≥2 samples → "insufficient data".
        _write_jsonl(
            metrics_path,
            [_event("drift_scan_duration_ms", {"value": 42.0}, _iso(now))],
        )

        result = runner.invoke(
            main,
            ["metrics", "aggregate", "--percentile", "p99"],
        )

        # Graceful path: warning, not error → exit 0 (REQ-39 scenario 2).
        assert result.exit_code == 0, result.output
        # The formatter renders "not enough data points" inline for < 2 samples.
        assert "not enough data points" in result.output
        # Counter name still rendered in the table.
        assert "drift_scan_duration_ms" in result.output
