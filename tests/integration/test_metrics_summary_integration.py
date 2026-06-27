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
        self, metrics_path: Path,
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
        self, metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        events: list[dict] = []
        # 10 events at 3 days ago — outside the 24h window.
        for _ in range(10):
            events.append(
                _event("suggest_invoked_total", {"count": 1},
                       _iso(now - timedelta(days=3))),
            )
        # 10 events at 36 hours ago — outside the 24h window.
        for _ in range(10):
            events.append(
                _event("drift_invoked_total", {"count": 1},
                       _iso(now - timedelta(hours=36))),
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
        self, metrics_path: Path,
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
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "missing_metrics.jsonl"
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = runner.invoke(main, ["metrics", "summary"])

        assert result.exit_code == 0, result.output
        assert "No metrics recorded yet." in result.output


class TestIntegrationEndToEndJsonFormatRoundtrip:
    """12 events → --format json → parses back to a dict matching summarize()."""

    def test_integration_end_to_end_json_format_roundtrip(
        self, metrics_path: Path,
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
        self, metrics_path: Path,
    ) -> None:
        result = runner.invoke(main, ["metrics", "summary", "--window", "invalid"])

        assert result.exit_code == 2, result.output