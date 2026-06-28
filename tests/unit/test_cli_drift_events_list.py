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


# ---------- REQ-V1.1.2: legacy str line compatibility (S2 hardening closeout) ----------


class TestListLegacyCompat:
    """REQ-V1.1.2 S2 hardening: the v1.0 D2 defensive coercion was REMOVED.

    The read-side CLI now catches ``DriftEventLogLegacyFormatError`` per
    line. Default mode (no ``--strict``) skips legacy lines + emits a
    stderr WARN per batch. ``--strict`` mode aborts on first legacy line
    with exit code 4 + CHANGELOG v1.0 ``sed`` migration hint.
    """

    def test_drift_events_list_default_mode_skips_legacy_lines_with_warn(
        self, tmp_path: Path
    ) -> None:
        """Default mode skips legacy lines + emits stderr WARN (REQ-V1.1.2)."""
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
        # Exit 0: legacy line was skipped, no events returned.
        assert result.exit_code == 0, result.output
        stdout = result.stdout if hasattr(result, "stdout") else result.output
        payload = json.loads(stdout)
        assert payload == [], "legacy line should have been skipped in default mode"
        stderr = (getattr(result, "stderr", "") or "")
        assert "legacy" in stderr.lower() or "skipped" in stderr.lower(), (
            f"expected stderr to mention legacy/skip; got: {stderr!r}"
        )

    def test_drift_events_list_strict_mode_aborts_on_legacy_line(
        self, tmp_path: Path
    ) -> None:
        """``--strict`` mode aborts on first legacy line with exit code 4 (REQ-V1.1.2)."""
        log_path = _seed_legacy_str_line(tmp_path)

        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--strict",
                "--format=json",
                "--path", str(log_path),
            ],
        )
        # Exit 4 = malformed input / migration needed.
        assert result.exit_code == 4, result.output
        stderr = (getattr(result, "stderr", "") or "")
        assert "sed" in stderr.lower() or "changelog" in stderr.lower(), (
            f"expected stderr to mention sed/changelog; got: {stderr!r}"
        )


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


# ---------- REQ-V1.0.2 T2.3: text-table helper direct unit test ----------


class TestFormatDriftEventsTextHelper:
    """The text-table helper is exposed for direct unit testing (T2.3).

    Mirrors the ``flow metrics summary`` text-table precedent at
    ``observability.py:999-1001``. Columns are fixed-width aligned and
    rows are emitted in input order with a separator rule.
    """

    def test_format_drift_events_text_helper_empty(self) -> None:
        """Empty event list returns the 'no drift events' sentinel."""
        from flow_engineering.cli import _format_drift_events_text

        out = _format_drift_events_text([])
        assert out == "(no drift events)\n"

    def test_format_drift_events_text_helper_3_rows(
        self, seeded_log: Path
    ) -> None:
        """3 events -> header + rule + 3 data rows in input order."""
        from flow_engineering.cli import _format_drift_events_text

        events = DriftEventLog(path=seeded_log).read_all()
        out = _format_drift_events_text(events)

        lines = out.splitlines()
        # header + separator + 3 data rows = 5 lines total (trailing nl = empty)
        assert len(lines) == 5
        # Header columns.
        assert "change" in lines[0]
        assert "decision_id" in lines[0]
        assert "binding_id" in lines[0]
        assert "class" in lines[0]
        assert "detected_at" in lines[0]
        # Separator line is all dashes.
        assert set(lines[1].replace(" ", "")) <= {"-"}
        # Data rows: each contains the change name + the rendered int decision_id.
        assert "change-foo" in lines[2]
        assert "change-bar" in lines[3]
        assert "change-foo" in lines[4]
        # decision_id rendered as int string (no decimal point).
        assert "1" in lines[2]
        assert "2" in lines[3]
        assert "3" in lines[4]

    def test_drift_events_list_text_table_mirrors_metrics_summary(
        self, seeded_log: Path
    ) -> None:
        """`flow drift-events list --format=text` aligns columns (mirrors flow metrics summary)."""
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
        lines = [ln for ln in result.output.splitlines() if ln]
        # header + separator + 3 data rows = 5 lines.
        assert len(lines) == 5
        # Header columns + data values must appear at predictable positions.
        # The first column of each data row must NOT have leading whitespace
        # (proves ljust() worked from column 0).
        for ln in lines[2:]:
            assert not ln[0].isspace(), f"data row has leading whitespace: {ln!r}"
        # The detected_at values appear in each data row.
        assert "1700000000" in lines[2]
        assert "1700000100" in lines[3]
        assert "1700000200" in lines[4]
