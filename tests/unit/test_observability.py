"""Unit tests for observability.py — JSONL counter sink (REQ-8 shared).

REQ-8 (PR#2 batch 1 + 2): a JSONL counter sink at
``~/.flow-engineering/metrics.jsonl`` records auto-suggest events:
``suggest_invoked_total``, ``suggest_hit_total``, ``suggest_miss_total``,
``bindings_confirmed_total``.

The path is overridable for tests via the ``FLOW_METRICS_PATH`` environment
variable; this keeps the production default pointed at ``~/.flow-engineering``
while letting unit tests point at ``tmp_path`` deterministically.

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit implements observability.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

METRICS_PATH_ENV = "FLOW_METRICS_PATH"


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point observability at a tmp_path JSONL file for the test."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv(METRICS_PATH_ENV, str(path))
    return path


def _read_events(path: Path) -> list[dict]:
    """Parse the JSONL sink into a list of event dicts."""
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


class TestIncrementAppends:
    """increment(name) appends one JSONL line per call."""

    def test_increment_appends_one_jsonl_line(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        observability.increment("suggest_invoked_total")
        assert metrics_path.exists()
        events = _read_events(metrics_path)
        assert len(events) == 1
        assert events[0]["name"] == "suggest_invoked_total"

    def test_increment_appends_multiple_lines(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        observability.increment("suggest_invoked_total")
        observability.increment("suggest_hit_total")
        observability.increment("suggest_miss_total")
        events = _read_events(metrics_path)
        assert [e["name"] for e in events] == [
            "suggest_invoked_total",
            "suggest_hit_total",
            "suggest_miss_total",
        ]

    def test_increment_with_fields(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        observability.increment("suggest_hit_total", confirmed=2, max_results=5)
        events = _read_events(metrics_path)
        assert len(events) == 1
        assert events[0]["fields"] == {"confirmed": 2, "max_results": 5}

    def test_increment_without_fields_yields_empty_fields(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        observability.increment("suggest_invoked_total")
        events = _read_events(metrics_path)
        assert events[0]["fields"] == {}

    def test_increment_records_iso_timestamp(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        observability.increment("suggest_invoked_total")
        events = _read_events(metrics_path)
        ts = events[0].get("ts")
        assert ts is not None
        assert isinstance(ts, str)
        # ISO 8601 contains 'T' separator and ends with Z or +offset.
        assert "T" in ts


class TestFlush:
    """flush() is callable and idempotent."""

    def test_flush_is_callable(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        observability.increment("suggest_invoked_total")
        observability.flush()  # must not raise
        events = _read_events(metrics_path)
        assert len(events) == 1

    def test_flush_after_no_increments_is_noop(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        observability.flush()
        assert not metrics_path.exists() or _read_events(metrics_path) == []


class TestPathResolution:
    """The sink path follows FLOW_METRICS_PATH env when set; otherwise the default."""

    def test_default_path_when_env_unset(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from flow_engineering import observability

        monkeypatch.delenv(METRICS_PATH_ENV, raising=False)
        default = observability.default_metrics_path()
        assert default == Path.home() / ".flow-engineering" / "metrics.jsonl"

    def test_env_path_overrides_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from flow_engineering import observability

        custom = tmp_path / "custom-metrics.jsonl"
        monkeypatch.setenv(METRICS_PATH_ENV, str(custom))
        observability.increment("suggest_invoked_total")
        assert custom.exists()

    def test_parent_directory_created(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from flow_engineering import observability

        nested = tmp_path / "deeply" / "nested" / "metrics.jsonl"
        monkeypatch.setenv(METRICS_PATH_ENV, str(nested))
        observability.increment("suggest_invoked_total")
        assert nested.exists()


class TestCounterNames:
    """The four named counters used by REQ-6 / REQ-8 are first-class names."""

    @pytest.mark.parametrize(
        "name",
        [
            "suggest_invoked_total",
            "suggest_hit_total",
            "suggest_miss_total",
            "bindings_confirmed_total",
        ],
    )
    def test_named_counter_round_trips(self, metrics_path: Path, name: str) -> None:
        from flow_engineering import observability

        observability.increment(name, reason="smoke")
        events = _read_events(metrics_path)
        assert events[-1]["name"] == name
        assert events[-1]["fields"].get("reason") == "smoke"


class TestReadAll:
    """read_all() returns the JSONL records as a list of dicts (helper for tests)."""

    def test_read_all_returns_empty_when_file_missing(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        events = observability.read_all()
        assert events == []

    def test_read_all_returns_recorded_events(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        observability.increment("suggest_invoked_total")
        observability.increment("suggest_hit_total", confirmed=1)
        events = observability.read_all()
        assert [e["name"] for e in events] == ["suggest_invoked_total", "suggest_hit_total"]
        assert events[1]["fields"]["confirmed"] == 1
