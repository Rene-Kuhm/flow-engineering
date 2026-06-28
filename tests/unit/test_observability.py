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


class TestMetricsRotation:
    """REQ-V1.2.1 — metrics.jsonl rotation (size threshold + env override).

    Mirrors the ``DriftEventLog`` rotation pattern at
    ``drift_event_log.py:220-254``. The helper must rotate the active
    ``metrics.jsonl`` when its size exceeds ``FLOW_METRICS_LOG_MAX_BYTES``
    (default 10 MB) by renaming it to ``metrics.<ISO-no-colons>.jsonl``,
    then resume appending to a fresh active file. Best-effort
    ``OSError`` swallow on rename prevents a slow FS from poisoning the
    sink path resolution.
    """

    def test_rotates_metrics_when_size_exceeds_threshold(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering import observability

        path = tmp_path / "metrics.jsonl"
        monkeypatch.setenv(METRICS_PATH_ENV, str(path))
        monkeypatch.setenv("FLOW_METRICS_LOG_MAX_BYTES", "1024")

        # Drive the active file past the 1 KB threshold. Each event line
        # is ~120 bytes (name + fields + ts + braces + newline) so 20
        # calls reliably cross the 1024-byte mark.
        for _ in range(20):
            observability.increment("rotation_probe_total", payload="x" * 80)

        # Active file should be present and contain at least one line
        # from AFTER the rotation (the post-rotation file is fresh).
        assert path.exists()
        active_events = _read_events(path)
        assert len(active_events) >= 1
        assert all(e["name"] == "rotation_probe_total" for e in active_events)

        # At least one rotated sibling must exist matching metrics.*.jsonl
        siblings = sorted(tmp_path.glob("metrics.*.jsonl"))
        assert siblings, "expected at least one rotated sibling"
        assert all(s != path for s in siblings)

    def test_no_rotation_when_below_threshold(
        self, metrics_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering import observability

        # Default 10 MB threshold + 100 small calls = far below threshold.
        for _ in range(100):
            observability.increment("suggest_invoked_total")
        events = _read_events(metrics_path)
        assert len(events) == 100

        # No rotated siblings should have been created.
        siblings = sorted(metrics_path.parent.glob("metrics.*.jsonl"))
        assert siblings == [], f"unexpected rotated siblings: {siblings}"

    def test_rotation_respects_env_override_zero_disables(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering import observability

        path = tmp_path / "metrics.jsonl"
        monkeypatch.setenv(METRICS_PATH_ENV, str(path))
        monkeypatch.setenv("FLOW_METRICS_LOG_MAX_BYTES", "0")

        # Even 50 calls with a large payload must not rotate when the
        # threshold is explicitly disabled via env var.
        for _ in range(50):
            observability.increment("rotation_probe_total", payload="x" * 200)
        assert path.exists()
        # No rotated siblings should be present (rotation disabled).
        siblings = sorted(tmp_path.glob("metrics.*.jsonl"))
        assert siblings == [], f"rotation should be disabled; found: {siblings}"

    def test_rotation_uses_isolated_tmp_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering import observability

        path = tmp_path / "metrics.jsonl"
        monkeypatch.setenv(METRICS_PATH_ENV, str(path))
        monkeypatch.setenv("FLOW_METRICS_LOG_MAX_BYTES", "512")

        for _ in range(15):
            observability.increment("rotation_probe_total", payload="x" * 80)

        # All rotated siblings MUST live inside tmp_path — no parent
        # traversal escapes from the rotation rename.
        siblings = list(tmp_path.glob("metrics.*.jsonl"))
        assert siblings, "expected at least one rotated sibling"
        for s in siblings:
            assert s.parent.resolve() == tmp_path.resolve()
        # Active file also stays inside tmp_path.
        assert path.parent.resolve() == tmp_path.resolve()

    def test_rotation_failure_does_not_crash_increment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering import observability

        path = tmp_path / "metrics.jsonl"
        monkeypatch.setenv(METRICS_PATH_ENV, str(path))
        monkeypatch.setenv("FLOW_METRICS_LOG_MAX_BYTES", "256")

        # Pre-create the sink with one line so size() >= threshold fires.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("seed line\n", encoding="utf-8")

        # Force rename to raise OSError; increment must still succeed
        # (best-effort sink — a slow FS must not break the caller).
        real_rename = Path.rename

        def boom(self: Path, target: Path) -> None:
            raise OSError("simulated slow FS rename failure")

        monkeypatch.setattr(Path, "rename", boom)
        try:
            for _ in range(5):
                observability.increment("rotation_probe_total", payload="x" * 80)
        finally:
            monkeypatch.setattr(Path, "rename", real_rename)

        # increment never raised; sink still has the seed line + new
        # writes appended AFTER the failed rename was swallowed.
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "seed line" in text
        assert "rotation_probe_total" in text

    def test_deletes_rotated_siblings_older_than_max_age_days(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering import observability

        path = tmp_path / "metrics.jsonl"
        monkeypatch.setenv(METRICS_PATH_ENV, str(path))
        monkeypatch.setenv("FLOW_METRICS_LOG_MAX_AGE_DAYS", "30")

        # Seed the active file so the size check passes; the rotation
        # helper will then walk the sibling glob and prune.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("active\n", encoding="utf-8")

        old_sibling = tmp_path / "metrics.20250101T000000Z.jsonl"
        recent_sibling = tmp_path / "metrics.20260628T000000Z.jsonl"
        old_sibling.write_text("old rotated\n", encoding="utf-8")
        recent_sibling.write_text("recent rotated\n", encoding="utf-8")

        # Backdate the old sibling's mtime to 60 days ago so the cutoff
        # (30 days) marks it for deletion. The recent sibling stays
        # within the retention window.
        old_time = 60 * 86400
        import os
        import time as _time

        now = _time.time()
        os.utime(old_sibling, (now - old_time, now - old_time))
        # Ensure recent sibling has a fresh mtime (just-now).
        os.utime(recent_sibling, (now, now))

        observability.increment("rotation_probe_total", payload="x" * 80)

        assert not old_sibling.exists(), "old sibling should have been pruned"
        assert recent_sibling.exists(), "recent sibling must be preserved"
        assert path.exists(), "active file must still be present"

    def test_age_cleanup_skips_when_max_age_days_is_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering import observability

        path = tmp_path / "metrics.jsonl"
        monkeypatch.setenv(METRICS_PATH_ENV, str(path))
        # Explicit 0 = disable age-based cleanup.
        monkeypatch.setenv("FLOW_METRICS_LOG_MAX_AGE_DAYS", "0")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("active\n", encoding="utf-8")
        old_sibling = tmp_path / "metrics.20200101T000000Z.jsonl"
        old_sibling.write_text("very old\n", encoding="utf-8")

        import os
        import time as _time

        now = _time.time()
        # Backdate by 5 years — should be way past any reasonable cutoff.
        os.utime(old_sibling, (now - 5 * 365 * 86400, now - 5 * 365 * 86400))

        observability.increment("rotation_probe_total", payload="x" * 80)

        # With cleanup disabled, the old sibling MUST be preserved.
        assert old_sibling.exists(), "age cleanup must be disabled when env=0"
        assert path.exists()
