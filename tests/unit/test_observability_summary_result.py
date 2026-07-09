"""Unit tests for the default-empty handling + exit code contract helpers
(change #6 observability PR#1 batch D T1.8 — REQ-35/36/37 error handling).

The new helpers land in :mod:`flow_engineering.observability` and the CLI
``metrics summary`` subcommand is refactored to consume them:

- :class:`observability.MetricsSummaryResult` — frozen dataclass carrying the
  summary dict plus diagnostics (events_read, source_path, empty_reason, etc.).
- :func:`observability.read_and_summarize` — one-call helper that reads +
  filters + summarizes + reports why the result is empty.
- :data:`observability.EXIT_OK`, :data:`observability.EXIT_INVALID_VALUE`,
  :data:`observability.EXIT_MALFORMED_METRICS`, :data:`observability.EXIT_WRITE_FAILURE`
  — the D9 exit-code contract as module-level constants.
- The CLI ``flow metrics summary`` subcommand maps ``empty_reason`` to a
  human message + exit code: missing/empty file → exit 0;
  ``all_malformed`` → exit 3 with a helpful stderr message.

Tests are written BEFORE the implementation per strict TDD (RED → GREEN).
Fixtures mirror the v0.6.0 JSONL event shape used by the rest of the
observability test suite.
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


def _write_jsonl(path: Path, events: list[dict]) -> None:
    """Write a JSONL sink file with the given events (one per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _event(name: str, fields: dict | None = None, ts: str | None = None) -> dict:
    if ts is None:
        ts = _iso(datetime.now(UTC))
    return {"name": name, "fields": fields or {}, "ts": ts}


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


# ---------- read_and_summarize: default-empty detection ----------


class TestReadAndSummarizeEmptyHandling:
    """read_and_summarize detects WHY the result is empty (D8 contract).

    Distinguishes three failure modes for downstream exit-code mapping:
    - ``missing_file`` — the JSONL file does not exist.
    - ``empty_file`` — the file exists but has zero bytes.
    - ``all_malformed`` — the file has content but every line is malformed.
    """

    def test_read_and_summarize_returns_empty_result_when_file_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        missing = tmp_path / "missing.jsonl"
        monkeypatch.setenv("FLOW_METRICS_PATH", str(missing))

        result = observability.read_and_summarize()

        assert isinstance(result, observability.MetricsSummaryResult)
        assert result.summary == {}
        assert result.events_read == 0
        assert result.empty_reason == "missing_file"
        assert result.source_path == missing

    def test_read_and_summarize_returns_empty_result_when_file_empty(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = observability.read_and_summarize()

        assert isinstance(result, observability.MetricsSummaryResult)
        assert result.summary == {}
        assert result.events_read == 0
        assert result.empty_reason == "empty_file"
        assert result.source_path == path

    def test_read_and_summarize_returns_all_malformed_when_lines_unparseable(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "garbage.jsonl"
        path.write_text("not json at all\nthis is also not json\n", encoding="utf-8")
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = observability.read_and_summarize()

        assert isinstance(result, observability.MetricsSummaryResult)
        assert result.summary == {}
        assert result.events_read == 0
        assert result.empty_reason == "all_malformed"
        assert result.source_path == path


# ---------- read_and_summarize: filter composition ----------


class TestReadAndSummarizeFilterComposition:
    """read_and_summarize composes --window (cheap, in-memory) THEN --domain."""

    def test_read_and_summarize_applies_window_then_domain_filters(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "metrics.jsonl"
        now = datetime.now(UTC)
        _write_jsonl(
            path,
            [
                # In-window binding event (kept)
                _event("suggest_invoked_total", {"count": 5}, _iso(now)),
                # In-window drift event (kept)
                _event("drift_invoked_total", {"count": 2}, _iso(now)),
                # Out-of-window binding event (window filter excludes)
                _event("suggest_invoked_total", {"count": 99}, _iso(now - timedelta(days=10))),
            ],
        )
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        # Filter chain: window=7d keeps all 3 events (the 10d-old one is excluded),
        # then domain=binding narrows to the 2 binding events that survived.
        result = observability.read_and_summarize(window="7d", domain="binding")

        assert result.empty_reason is None
        assert result.window == "7d"
        assert result.domain == "binding"
        assert result.events_read == 3  # all 3 lines were parsed
        assert "binding" in result.summary
        assert "drift" not in result.summary
        # Only the in-window binding event contributes to the count.
        assert result.summary["binding"]["suggest_invoked_total"] == 5


# ---------- exit-code constants ----------


class TestExitCodeConstants:
    """The D9 exit-code contract is exposed as module-level constants."""

    def test_exit_ok_is_zero(self) -> None:
        assert observability.EXIT_OK == 0

    def test_exit_invalid_value_is_two(self) -> None:
        assert observability.EXIT_INVALID_VALUE == 2

    def test_exit_malformed_metrics_is_three(self) -> None:
        assert observability.EXIT_MALFORMED_METRICS == 3

    def test_exit_write_failure_is_four(self) -> None:
        assert observability.EXIT_WRITE_FAILURE == 4


# ---------- CLI integration: D8 default-empty + D9 exit-code 3 on malformed ----------


class TestMetricsSummaryCliExitCodes:
    """The ``flow metrics summary`` CLI maps ``empty_reason`` to exit code.

    - missing/empty file → exit 0 with friendly "No metrics recorded yet.".
    - all-malformed file → exit 3 with "Error: metrics file at <path> is malformed.".
    """

    def test_metrics_summary_cli_exits_zero_on_missing_file_with_friendly_message(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        missing = tmp_path / "missing.jsonl"
        monkeypatch.setenv("FLOW_METRICS_PATH", str(missing))

        result = runner.invoke(main, ["metrics", "summary"])

        assert result.exit_code == 0, result.output
        assert "No metrics recorded yet." in result.output

    def test_metrics_summary_cli_exits_3_on_malformed_metrics_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "garbage.jsonl"
        path.write_text("definitely not json\nstill not json\n", encoding="utf-8")
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = runner.invoke(main, ["metrics", "summary"])

        assert result.exit_code == 3, result.output
        assert "malformed" in result.output.lower()
        assert str(path) in result.output
