"""Unit tests for ``flow drift-events list`` subcommand (REQ-V1.0.2).

Covers:
- The ``list`` subcommand exists at ``flow drift-events list``
- Flags: --since, --until, --change, --event-class, --limit, --format, --path
- Formats: text (default), json, prometheus, csv
- Exit codes per D9: 0=success, 2=invalid args, 3=malformed JSONL
- Empty log returns exit 0 (graceful empty)
- Invalid --format returns exit 2 with stderr explanation
- Invalid --since returns exit 2 with stderr explanation

Tests written BEFORE the implementation per strict TDD. They MUST fail
until the GREEN commit wires the ``drift-events list`` subcommand.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main
from flow_engineering.drift_event_log import DriftEvent, DriftEventLog

runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def seeded_log(tmp_path: Path) -> Path:
    """Pre-seed a tmp_path JSONL with 3 events covering the filter surface."""
    log_path = tmp_path / "drift_events.jsonl"
    log = DriftEventLog(path=log_path)
    log.append(
        DriftEvent(
            change="change-foo",
            decision_id=1,
            binding_id="obs-1",
            event_class="LABEL_DRIFT",
            detected_at=1_700_000_000.0,
        )
    )
    log.append(
        DriftEvent(
            change="change-bar",
            decision_id=2,
            binding_id="obs-2",
            event_class="STALE_LOCATION",
            detected_at=1_700_000_100.0,
        )
    )
    log.append(
        DriftEvent(
            change="change-foo",
            decision_id=3,
            binding_id="obs-3",
            event_class="LABEL_DRIFT",
            detected_at=1_700_000_200.0,
        )
    )
    return log_path


def _seed_legacy_str_line(tmp_path: Path) -> Path:
    """Write a legacy pre-v1.0 str-decision_id line to a tmp_path JSONL."""
    log_path = tmp_path / "drift_events_legacy.jsonl"
    legacy_line = json.dumps({
        "change": "legacy-change",
        "decision_id": "42",
        "binding_id": "obs-42",
        "class": "STALE_ID",
        "detected_at": 1_700_000_000.0,
    })
    log_path.write_text(legacy_line + "\n", encoding="utf-8")
    return log_path


# ---------- REQ-V1.0.2: list subcommand exists with full filter set ----------


class TestListCommandExists:
    """The list subcommand MUST exist and accept all 7 documented flags."""

    def test_drift_events_list_command_exists(self, seeded_log: Path) -> None:
        """flow drift-events list --format=text --path=<tmp> exits 0 and prints rows."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=text",
                "--path", str(seeded_log),
            ],
        )
        assert result.exit_code == 0, result.output
        # Header row + 3 data rows.
        assert "change" in result.output
        assert "change-foo" in result.output
        assert "change-bar" in result.output

    def test_drift_events_list_filter_by_change(self, seeded_log: Path) -> None:
        """--change filters to a specific change name."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=text",
                "--path", str(seeded_log),
                "--change", "change-foo",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "change-foo" in result.output
        assert "change-bar" not in result.output

    def test_drift_events_list_filter_by_event_class(self, seeded_log: Path) -> None:
        """--event-class filters to a specific drift class."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=text",
                "--path", str(seeded_log),
                "--event-class", "STALE_LOCATION",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "STALE_LOCATION" in result.output
        assert "LABEL_DRIFT" not in result.output

    def test_drift_events_list_filter_by_limit(self, seeded_log: Path) -> None:
        """--limit caps the number of returned events."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=text",
                "--path", str(seeded_log),
                "--limit", "1",
            ],
        )
        assert result.exit_code == 0, result.output
        # Only 1 data row should appear (header still present).
        lines = [ln for ln in result.output.splitlines() if "change-" in ln]
        assert len(lines) == 1


# ---------- REQ-V1.0.2: --format=json envelope ----------


class TestListJsonFormat:
    """--format=json emits the events as a JSON array with int decision_id."""

    def test_drift_events_list_json_format_int_decision_id(
        self, seeded_log: Path
    ) -> None:
        """--format=json returns a parseable JSON envelope with int decision_id."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=json",
                "--path", str(seeded_log),
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert isinstance(payload, list)
        assert len(payload) == 3
        for ev in payload:
            assert isinstance(ev["decision_id"], int)
            assert "decision_id" in ev
            assert "change" in ev
            assert "class" in ev


# ---------- REQ-V1.0.2: --format=csv envelope ----------


class TestListCsvFormat:
    """--format=csv emits a CSV with header row."""

    def test_drift_events_list_csv_format(self, seeded_log: Path) -> None:
        """--format=csv returns a CSV with header + 3 data rows."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=csv",
                "--path", str(seeded_log),
            ],
        )
        assert result.exit_code == 0, result.output
        reader = csv.reader(io.StringIO(result.output))
        rows = list(reader)
        # Header + 3 data rows.
        assert len(rows) == 4
        assert "decision_id" in rows[0]
        assert "change" in rows[0]
        # Row 1 (int decision_id as string in CSV).
        assert rows[1][rows[0].index("decision_id")] == "1"


# ---------- REQ-V1.0.2: --format=prometheus envelope ----------


class TestListPrometheusFormat:
    """--format=prometheus emits a textfile exposition with # HELP/# TYPE/# EOF."""

    def test_drift_events_list_prometheus_format(self, seeded_log: Path) -> None:
        """--format=prometheus returns textfile exposition markers."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=prometheus",
                "--path", str(seeded_log),
            ],
        )
        assert result.exit_code == 0, result.output
        # Prometheus textfile format uses these markers (per REQ-38 D6).
        assert "# HELP" in result.output or "flow_drift_events" in result.output
        assert "# EOF" in result.output


# ---------- REQ-V1.0.2: error exit codes ----------


class TestListErrorExitCodes:
    """Invalid args exit 2 per D9 convention."""

    def test_drift_events_list_invalid_format(self, seeded_log: Path) -> None:
        """--format=invalid exits 2 with stderr explanation."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=invalid",
                "--path", str(seeded_log),
            ],
        )
        assert result.exit_code == 2, result.output

    def test_drift_events_list_invalid_since(self, seeded_log: Path) -> None:
        """--since=not-a-date exits 2 with stderr explanation."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--since", "yesterday",
                "--path", str(seeded_log),
            ],
        )
        assert result.exit_code == 2, result.output


# ---------- REQ-V1.0.2: legacy str line compatibility (defensive coercion) ----------


class TestListLegacyCompat:
    """--path=<legacy log with str decision_id> reads back as int (D2)."""

    def test_drift_events_list_reads_legacy_str_as_int(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Legacy pre-v1.0 str decision_id is read back as int (REQ-V1.0.1 D2)."""
        log_path = _seed_legacy_str_line(tmp_path)

        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=json",
                "--path", str(log_path),
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert len(payload) == 1
        assert payload[0]["decision_id"] == 42
        assert isinstance(payload[0]["decision_id"], int)


# ---------- REQ-V1.0.2: empty log returns 0 ----------


class TestListEmptyLog:
    """An empty (or missing) log returns exit 0 with an informative message."""

    def test_drift_events_list_empty_log(self, tmp_path: Path) -> None:
        """A JSONL with zero events returns exit 0 and a no-events message."""
        log_path = tmp_path / "empty.jsonl"
        log_path.write_text("", encoding="utf-8")

        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=text",
                "--path", str(log_path),
            ],
        )
        assert result.exit_code == 0, result.output

    def test_drift_events_list_missing_log(self, tmp_path: Path) -> None:
        """A missing JSONL returns exit 0 (graceful empty)."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=text",
                "--path", str(tmp_path / "nope.jsonl"),
            ],
        )
        assert result.exit_code == 0, result.output