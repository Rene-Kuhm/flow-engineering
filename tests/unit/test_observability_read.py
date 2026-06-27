"""Unit tests for the read-side observability helpers added in change #6 (REQ-35..39).

These tests cover the 6 read-side helpers added in PR#1 batch A T1.1:

- :func:`observability.read_all_metrics` — public alias for the JSONL sink reader.
- :func:`observability.read_events_since` — rolling/absolute time-window filter.
- :func:`observability.read_events_by_domain` — prefix-based domain slice.
- :func:`observability.summarize` — collapse events into per-domain counters.
- :func:`observability.prometheus_exposition` — Prometheus textfile format.
- :func:`observability.aggregate` — percentile over numeric samples.
- :func:`observability.atomic_write_text` — atomic file write helper (D10).

Tests are written BEFORE the implementation per strict TDD (RED → GREEN → REFACTOR).
The fixtures mirror the v0.6.0 JSONL event shape: ``{"name", "fields", "ts"}``
where ``ts`` is an ISO-8601 UTC string with a ``Z`` suffix.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
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


def _iso_to_epoch(iso: str) -> float:
    """Convert ISO-8601 UTC string with 'Z' suffix to epoch seconds (float)."""
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()


def _event(name: str, fields: dict | None = None, ts: str = "2026-06-27T00:00:00Z") -> dict:
    """Build a single event dict matching the JSONL sink contract."""
    return {"name": name, "fields": fields or {}, "ts": ts}


# ---------- read_all_metrics ----------


class TestReadAllMetrics:
    """read_all_metrics() returns [] when file missing; parses JSONL when present."""

    def test_read_all_metrics_returns_empty_list_when_file_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        missing = tmp_path / "missing.jsonl"
        monkeypatch.setenv("FLOW_METRICS_PATH", str(missing))
        result = observability.read_all_metrics()
        assert result == []

    def test_read_all_metrics_parses_valid_jsonl(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "metrics.jsonl"
        _write_jsonl(path, [
            _event("binding_suggest_invoked_total", {"count": 1}, "2026-06-27T10:00:00Z"),
            _event("drift_invoked_total", {"change": "observability"}, "2026-06-27T11:00:00Z"),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = observability.read_all_metrics()

        assert len(result) == 2
        assert all(isinstance(m, observability.MetricEvent) for m in result)
        assert result[0].counter_name == "binding_suggest_invoked_total"
        assert result[1].counter_name == "drift_invoked_total"

    def test_read_all_metrics_skips_malformed_lines(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Malformed lines are silently skipped (best-effort sink contract)."""
        path = tmp_path / "metrics.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '{"name": "good_one", "fields": {}, "ts": "2026-06-27T10:00:00Z"}\n'
            "this is not json\n"
            '{"name": "good_two", "fields": {}, "ts": "2026-06-27T11:00:00Z"}\n',
            encoding="utf-8",
        )
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = observability.read_all_metrics()

        names = [m.counter_name for m in result]
        assert names == ["good_one", "good_two"]


# ---------- read_events_since ----------


class TestReadEventsSince:
    """read_events_since(since_epoch) filters by timestamp (epoch seconds)."""

    def test_read_events_since_filters_by_timestamp(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "metrics.jsonl"
        _write_jsonl(path, [
            _event("counter_a", ts="2026-06-27T10:00:00Z"),
            _event("counter_b", ts="2026-06-27T11:00:00Z"),
            _event("counter_c", ts="2026-06-27T12:00:00Z"),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        since = _iso_to_epoch("2026-06-27T11:00:00Z")
        result = observability.read_events_since(since)

        names = [m.counter_name for m in result]
        assert names == ["counter_b", "counter_c"]


# ---------- read_events_by_domain ----------


class TestReadEventsByDomain:
    """read_events_by_domain(prefix) filters by counter-name prefix."""

    def test_read_events_by_domain_filters_by_prefix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "metrics.jsonl"
        _write_jsonl(path, [
            _event("binding_suggest_invoked_total"),
            _event("binding_backfill_observations_total"),
            _event("drift_invoked_total"),
            _event("vector_search_invoked_total"),
            _event("snapshot_create_total"),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = observability.read_events_by_domain("binding")
        names = [m.counter_name for m in result]
        assert names == [
            "binding_suggest_invoked_total",
            "binding_backfill_observations_total",
        ]

    def test_read_events_by_domain_raises_on_unknown_domain(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "metrics.jsonl"
        _write_jsonl(path, [_event("binding_suggest_invoked_total")])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        with pytest.raises(ValueError, match="unknown domain"):
            observability.read_events_by_domain("nonexistent_domain")


# ---------- summarize ----------


class TestSummarize:
    """summarize(events) groups events by domain, then by counter_name."""

    def test_summarize_groups_by_domain_and_counter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "metrics.jsonl"
        _write_jsonl(path, [
            _event("binding_suggest_invoked_total", {"count": 2}),
            _event("binding_suggest_invoked_total", {"count": 1}),
            _event("binding_backfill_observations_total", {"count": 5}),
            _event("drift_invoked_total", {"count": 1}),
            _event("vector_search_invoked_total", {"count": 3}),
            _event("vector_search_invoked_total", {"count": 4}),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        events = observability.read_all_metrics()
        result = observability.summarize(events)

        assert result == {
            "binding": {
                "binding_suggest_invoked_total": 3,
                "binding_backfill_observations_total": 5,
            },
            "drift": {
                "drift_invoked_total": 1,
            },
            "vector": {
                "vector_search_invoked_total": 7,
            },
        }


# ---------- prometheus_exposition ----------


class TestPrometheusExposition:
    """prometheus_exposition(events) emits Prometheus textfile format with HELP + TYPE."""

    def test_prometheus_exposition_includes_help_and_type(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "metrics.jsonl"
        _write_jsonl(path, [
            _event("binding_suggest_invoked_total", {"count": 1}, "2026-06-27T10:00:00Z"),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        events = observability.read_all_metrics()
        text = observability.prometheus_exposition(events)

        assert "# HELP binding_suggest_invoked_total" in text
        assert "# TYPE binding_suggest_invoked_total counter" in text
        assert "binding_suggest_invoked_total" in text


# ---------- aggregate ----------


class TestAggregate:
    """aggregate(values, percentile) computes percentiles via reservoir sampling."""

    def test_aggregate_p50_p95_p99_returns_correct_values(self) -> None:
        values = list(range(1, 101))  # 1..100 inclusive
        assert observability.aggregate(values, 50) == 50.0
        assert observability.aggregate(values, 95) == 95.0
        assert observability.aggregate(values, 99) == 99.0

    def test_aggregate_returns_zero_on_empty(self) -> None:
        assert observability.aggregate([], 95) == 0.0


# ---------- atomic_write_text ----------


class TestAtomicWriteText:
    """atomic_write_text(path, content) writes content to disk atomically."""

    def test_atomic_write_text_creates_file_atomically(
        self, tmp_path: Path,
    ) -> None:
        target = tmp_path / "out.txt"
        observability.atomic_write_text(target, "hello world\n")
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "hello world\n"
        # No leftover .tmp files in the parent dir.
        leftovers = list(tmp_path.glob("*.tmp"))
        assert leftovers == []