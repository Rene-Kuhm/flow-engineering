"""Unit tests for the window-filter helpers added in change #6 PR#1 batch B T1.4.

REQ-36 foundation: ``parse_window`` + ``filter_by_window`` per design D4 rolling
semantics. The window string is a rolling duration relative to ``now`` (NOT
calendar-aligned). The ``now`` parameter is exposed for testability so unit
tests can pin the cutoff deterministically.

Coverage:
- :func:`observability.parse_window` — preset (1h/24h/7d) + custom (<int><h|d>).
- :func:`observability.filter_by_window` — events whose timestamp is in
  ``[now - window, now]`` survive; older events are excluded.
- :data:`observability.WINDOW_PATTERNS` — exported lookup table covering the
  4 preset values (1h/24h/7d/30d).

Tests are written BEFORE the implementation per strict TDD (RED → GREEN → REFACTOR).
"""
from __future__ import annotations

import pytest

from flow_engineering import observability


# ---------- helpers ----------


def _event(name: str, ts: float, fields: dict | None = None) -> observability.MetricEvent:
    """Build a single ``MetricEvent`` for window-filter tests."""
    return observability.MetricEvent(
        timestamp=ts,
        counter_name=name,
        labels=fields or {},
        raw_line="",
    )


# ---------- WINDOW_PATTERNS ----------


class TestWindowPatterns:
    """WINDOW_PATTERNS exposes preset durations in seconds."""

    def test_window_patterns_contains_1h_24h_7d_30d(self) -> None:
        assert observability.WINDOW_PATTERNS["1h"] == 3600
        assert observability.WINDOW_PATTERNS["24h"] == 86400
        assert observability.WINDOW_PATTERNS["7d"] == 604800
        assert observability.WINDOW_PATTERNS["30d"] == 2592000


# ---------- parse_window ----------


class TestParseWindow:
    """parse_window(window) -> int seconds, case-insensitive, with custom support."""

    def test_parse_window_recognizes_preset_1h(self) -> None:
        assert observability.parse_window("1h") == 3600

    def test_parse_window_recognizes_preset_24h(self) -> None:
        assert observability.parse_window("24h") == 86400

    def test_parse_window_recognizes_preset_7d(self) -> None:
        assert observability.parse_window("7d") == 604800

    def test_parse_window_recognizes_custom_format_12h(self) -> None:
        """Custom format: <int><h|d> — e.g. '12h' = 12 hours in seconds."""
        assert observability.parse_window("12h") == 12 * 3600
        # And the days variant.
        assert observability.parse_window("3d") == 3 * 86400

    def test_parse_window_raises_value_error_on_invalid_format(self) -> None:
        """Garbage like 'foo' / '5' / '5x' / '' raises ValueError."""
        with pytest.raises(ValueError):
            observability.parse_window("foo")
        with pytest.raises(ValueError):
            observability.parse_window("5x")
        with pytest.raises(ValueError):
            observability.parse_window("")


# ---------- filter_by_window ----------


class TestFilterByWindow:
    """filter_by_window(events, window, now=None) returns events in the rolling window."""

    def test_filter_by_window_returns_events_within_window(self) -> None:
        """Events at -30m, -10m, -2m, -90m keep; -3h is excluded under 1h."""
        now = 1_700_000_000.0
        events = [
            _event("a", now - 3 * 3600),  # 3h ago — excluded
            _event("b", now - 90 * 60),   # 90m ago — excluded
            _event("c", now - 30 * 60),   # 30m ago — kept
            _event("d", now - 10 * 60),   # 10m ago — kept
            _event("e", now - 2 * 60),    # 2m ago — kept
        ]
        result = observability.filter_by_window(events, "1h", now=now)
        names = [ev.counter_name for ev in result]
        assert names == ["c", "d", "e"]

    def test_filter_by_window_with_explicit_now_param_for_testability(self) -> None:
        """Passing `now` explicitly pins the cutoff; no reliance on time.time()."""
        # Pin now far in the past so the relative window is deterministic.
        fixed_now = 1_000_000.0
        events = [
            _event("old", fixed_now - 7200),   # 2h before fixed_now
            _event("mid", fixed_now - 1800),   # 30m before fixed_now
            _event("new", fixed_now - 60),     # 1m before fixed_now
        ]
        # 1h window from fixed_now → cut at fixed_now - 3600; "old" is excluded.
        result = observability.filter_by_window(events, "1h", now=fixed_now)
        names = [ev.counter_name for ev in result]
        assert names == ["mid", "new"]
