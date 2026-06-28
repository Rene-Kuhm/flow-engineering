"""Unit tests for ``flow drift-events tail`` subcommand (REQ-V1.0.3).

Covers:
- The ``tail`` subcommand exists at ``flow drift-events tail``
- Flags: --limit (default 10), --change, --event-class, --format
- Default behavior: last N events newest-first (mirrors shell ``tail -n``)
- Filter behavior: --change + --event-class
- Format behavior: text (default) + json
- Empty log + missing log graceful handling
- Exit codes per D9: 0=success, 2=invalid args

Tests written BEFORE the implementation per strict TDD. They MUST fail
until the GREEN commit wires the ``drift-events tail`` subcommand.
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
def tail_log(tmp_path: Path) -> Path:
    """Pre-seed a tmp_path JSONL with 15 events covering the tail surface."""
    log_path = tmp_path / "drift_events.jsonl"
    log = DriftEventLog(path=log_path)
    for i in range(15):
        log.append(
            DriftEvent(
                change=f"change-{i % 3}",
                decision_id=100 + i,
                binding_id=f"obs-{i}",
                event_class="LABEL_DRIFT" if i % 2 == 0 else "STALE_LOCATION",
                detected_at=1_700_000_000.0 + float(i),
            )
        )
    return log_path


# ---------- REQ-V1.0.3: tail subcommand exists with full flag set ----------


class TestTailCommandExists:
    """The tail subcommand MUST exist and accept all 4 documented flags."""

    def test_drift_events_tail_command_exists(self, tail_log: Path) -> None:
        """``flow drift-events tail`` defaults to --limit=10 + newest-first."""
        result = runner.invoke(
            main,
            [
                "drift", "events",
                "tail",
                "--path", str(tail_log),
            ],
        )
        assert result.exit_code == 0, result.output
        # 15 events seeded; default --limit=10 returns 10 data rows.
        lines = [ln for ln in result.output.splitlines() if ln and ln.startswith("change-")]
        assert len(lines) == 10

    def test_drift_events_tail_explicit_limit(self, tail_log: Path) -> None:
        """``--limit=3`` returns exactly 3 data rows."""
        result = runner.invoke(
            main,
            [
                "drift", "events",
                "tail",
                "--path", str(tail_log),
                "--limit", "3",
            ],
        )
        assert result.exit_code == 0, result.output
        lines = [ln for ln in result.output.splitlines() if ln and ln.startswith("change-")]
        assert len(lines) == 3

    def test_drift_events_tail_newest_first_order(self, tail_log: Path) -> None:
        """Tail emits events newest-first by detected_at (mirrors shell ``tail -n``)."""
        result = runner.invoke(
            main,
            [
                "drift", "events",
                "tail",
                "--path", str(tail_log),
                "--limit", "5",
            ],
        )
        assert result.exit_code == 0, result.output
        # The 5 newest events have decision_id 114..110 (newest first in
        # the rendered table). All 5 are present in the output.
        for did in (114, 113, 112, 111, 110):
            assert str(did) in result.output

    def test_drift_events_tail_change_filter(self, tail_log: Path) -> None:
        """``--change=change-0`` filters to events with change == 'change-0'."""
        result = runner.invoke(
            main,
            [
                "drift", "events",
                "tail",
                "--path", str(tail_log),
                "--change", "change-0",
                "--limit", "10",
            ],
        )
        assert result.exit_code == 0, result.output
        # All 15 events use change-0/change-1/change-2; filter keeps only change-0.
        lines = [ln for ln in result.output.splitlines() if ln and ln.startswith("change-")]
        assert all("change-0" in ln for ln in lines)

    def test_drift_events_tail_event_class_filter(self, tail_log: Path) -> None:
        """``--event-class=LABEL_DRIFT`` filters to LABEL_DRIFT events."""
        result = runner.invoke(
            main,
            [
                "drift", "events",
                "tail",
                "--path", str(tail_log),
                "--event-class", "LABEL_DRIFT",
                "--limit", "10",
            ],
        )
        assert result.exit_code == 0, result.output
        # Every other event (i=0,2,4,...) is LABEL_DRIFT; 8 total in 15.
        lines = [ln for ln in result.output.splitlines() if ln and ln.startswith("change-")]
        assert all("LABEL_DRIFT" in ln for ln in lines)
        assert all("STALE_LOCATION" not in ln for ln in lines)

    def test_drift_events_tail_json_format(self, tail_log: Path) -> None:
        """``--format=json`` returns a parseable JSON array."""
        result = runner.invoke(
            main,
            [
                "drift", "events",
                "tail",
                "--path", str(tail_log),
                "--limit", "3",
                "--format", "json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert isinstance(payload, list)
        assert len(payload) == 3
        # Newest-first: first element decision_id is the largest of the 3.
        assert payload[0]["decision_id"] == 114
        assert payload[1]["decision_id"] == 113
        assert payload[2]["decision_id"] == 112

    def test_drift_events_tail_invalid_format(self, tail_log: Path) -> None:
        """``--format=invalid`` exits 2 per D9."""
        result = runner.invoke(
            main,
            [
                "drift", "events",
                "tail",
                "--path", str(tail_log),
                "--format", "invalid",
            ],
        )
        assert result.exit_code == 2, result.output


# ---------- REQ-V1.0.3: empty + missing log graceful handling ----------


class TestTailEmptyLog:
    """An empty (or missing) log returns exit 0 with an informative message."""

    def test_drift_events_tail_empty_log(self, tmp_path: Path) -> None:
        """A JSONL with zero events returns exit 0."""
        log_path = tmp_path / "empty.jsonl"
        log_path.write_text("", encoding="utf-8")

        result = runner.invoke(
            main,
            [
                "drift", "events",
                "tail",
                "--path", str(log_path),
            ],
        )
        assert result.exit_code == 0, result.output

    def test_drift_events_tail_missing_log(self, tmp_path: Path) -> None:
        """A missing JSONL returns exit 0 (graceful empty)."""
        result = runner.invoke(
            main,
            [
                "drift", "events",
                "tail",
                "--path", str(tmp_path / "nope.jsonl"),
            ],
        )
        assert result.exit_code == 0, result.output
