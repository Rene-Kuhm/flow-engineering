"""Unit tests for ``flow drift-events stats`` subcommand (REQ-V1.0.3).

Covers:
- The ``stats`` subcommand exists at ``flow drift-events stats``
- Flags: --change, --since, --until, --format
- Per-event-class counts (LABEL_DRIFT, STALE_LOCATION, ...)
- Per-change counts (change-foo, change-bar, ...)
- Per-decision-id top-N counts (most_common)
- Text format: aligned table; JSON format: envelope with 3 dicts
- Empty log graceful handling
- Exit codes per D9: 0=success, 2=invalid args

Tests written BEFORE the implementation per strict TDD. They MUST fail
until the GREEN commit wires the ``drift-events stats`` subcommand.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main
from flow_engineering.drift_event_log import DriftEvent, DriftEventLog

runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def stats_log(tmp_path: Path) -> Path:
    """Pre-seed a tmp_path JSONL with 5 events covering the stats surface.

    2x LABEL_DRIFT, 2x STALE_LOCATION, 1x STILL_VALID
    3 events for change-foo, 2 events for change-bar
    decision_id 42 appears twice, 100 appears once.
    """
    log_path = tmp_path / "drift_events.jsonl"
    log = DriftEventLog(path=log_path)
    log.append(
        DriftEvent(
            change="change-foo",
            decision_id=42,
            binding_id="obs-1",
            event_class="LABEL_DRIFT",
            detected_at=1_700_000_000.0,
        )
    )
    log.append(
        DriftEvent(
            change="change-foo",
            decision_id=42,
            binding_id="obs-2",
            event_class="LABEL_DRIFT",
            detected_at=1_700_000_100.0,
        )
    )
    log.append(
        DriftEvent(
            change="change-foo",
            decision_id=100,
            binding_id="obs-3",
            event_class="STALE_LOCATION",
            detected_at=1_700_000_200.0,
        )
    )
    log.append(
        DriftEvent(
            change="change-bar",
            decision_id=7,
            binding_id="obs-4",
            event_class="STALE_LOCATION",
            detected_at=1_700_000_300.0,
        )
    )
    log.append(
        DriftEvent(
            change="change-bar",
            decision_id=8,
            binding_id="obs-5",
            event_class="STILL_VALID",
            detected_at=1_700_000_400.0,
        )
    )
    return log_path


# ---------- REQ-V1.0.3: stats subcommand exists with full flag set ----------


class TestStatsCommandExists:
    """The stats subcommand MUST exist and emit per-event-class counts."""

    def test_drift_events_stats_per_event_class_counts(self, stats_log: Path) -> None:
        """stdout contains per-event-class counts."""
        result = runner.invoke(
            main,
            [
                "drift",
                "events",
                "stats",
                "--path",
                str(stats_log),
            ],
        )
        assert result.exit_code == 0, result.output
        # 2 LABEL_DRIFT, 2 STALE_LOCATION, 1 STILL_VALID.
        assert "LABEL_DRIFT" in result.output
        assert "STALE_LOCATION" in result.output
        assert "STILL_VALID" in result.output

    def test_drift_events_stats_per_change_counts(self, stats_log: Path) -> None:
        """stdout contains per-change counts."""
        result = runner.invoke(
            main,
            [
                "drift",
                "events",
                "stats",
                "--path",
                str(stats_log),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "change-foo" in result.output
        assert "change-bar" in result.output

    def test_drift_events_stats_per_decision_id_top_n(self, stats_log: Path) -> None:
        """stdout contains per-decision-id top-N counts (most_common)."""
        result = runner.invoke(
            main,
            [
                "drift",
                "events",
                "stats",
                "--path",
                str(stats_log),
            ],
        )
        assert result.exit_code == 0, result.output
        # decision_id 42 appears twice; 100 appears once; 7 and 8 appear once.
        assert "42" in result.output
        assert "100" in result.output

    def test_drift_events_stats_json_format(self, stats_log: Path) -> None:
        """``--format=json`` returns an envelope with 3 count dicts."""
        result = runner.invoke(
            main,
            [
                "drift",
                "events",
                "stats",
                "--path",
                str(stats_log),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert isinstance(payload, dict)
        # 3 keys: by_event_class, by_change, by_decision_id.
        assert "by_event_class" in payload
        assert "by_change" in payload
        assert "by_decision_id" in payload
        assert payload["by_event_class"]["LABEL_DRIFT"] == 2
        assert payload["by_event_class"]["STALE_LOCATION"] == 2
        assert payload["by_event_class"]["STILL_VALID"] == 1
        assert payload["by_change"]["change-foo"] == 3
        assert payload["by_change"]["change-bar"] == 2
        # Top decision_id by count.
        top = payload["by_decision_id"][0]
        assert top["decision_id"] == 42
        assert top["count"] == 2

    def test_drift_events_stats_filters(self, stats_log: Path) -> None:
        """``--change=foo`` filters correctly to change-foo only (3 events)."""
        result = runner.invoke(
            main,
            [
                "drift",
                "events",
                "stats",
                "--path",
                str(stats_log),
                "--change",
                "change-foo",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        # Only change-foo; 3 events.
        assert sum(payload["by_change"].values()) == 3
        assert "change-bar" not in payload["by_change"]

    def test_drift_events_stats_empty_log(self, tmp_path: Path) -> None:
        """An empty JSONL returns exit 0 + all-zero envelope."""
        log_path = tmp_path / "empty.jsonl"
        log_path.write_text("", encoding="utf-8")

        result = runner.invoke(
            main,
            [
                "drift",
                "events",
                "stats",
                "--path",
                str(log_path),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["by_event_class"] == {}
        assert payload["by_change"] == {}
        assert payload["by_decision_id"] == []

    def test_drift_events_stats_missing_log(self, tmp_path: Path) -> None:
        """A missing JSONL returns exit 0 (graceful empty)."""
        result = runner.invoke(
            main,
            [
                "drift",
                "events",
                "stats",
                "--path",
                str(tmp_path / "nope.jsonl"),
            ],
        )
        assert result.exit_code == 0, result.output

    def test_drift_events_stats_invalid_since(self, stats_log: Path) -> None:
        """``--since=not-a-date`` exits 2 per D9."""
        result = runner.invoke(
            main,
            [
                "drift",
                "events",
                "stats",
                "--path",
                str(stats_log),
                "--since",
                "yesterday",
            ],
        )
        assert result.exit_code == 2, result.output

    def test_drift_events_stats_invalid_format(self, stats_log: Path) -> None:
        """``--format=invalid`` exits 2 per D9."""
        result = runner.invoke(
            main,
            [
                "drift",
                "events",
                "stats",
                "--path",
                str(stats_log),
                "--format",
                "invalid",
            ],
        )
        assert result.exit_code == 2, result.output
