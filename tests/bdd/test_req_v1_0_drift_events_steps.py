"""BDD step definitions for ``req_v1_0_drift_events.feature``.

Covers REQ-V1.0.2 + REQ-V1.0.3 acceptance scenarios for the
``flow drift-events {list,tail,stats}`` read-side CLI surface (REQ-V1.0.2 + REQ-V1.0.3).

Scenarios:
- Operator reads drift events as default text table
- Operator tails recent drift events newest-first
- Operator summarizes drift counts per change

The step bodies invoke the ``flow drift-events`` CLI via Click's ``CliRunner``
against a tmp_path JSONL so the tests are isolated from the real
``~/.flow-engineering/drift_events.jsonl``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering.cli import main as cli_main
from flow_engineering.drift_event_log import DriftEvent, DriftEventLog

runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def drift_events_world(tmp_path: Path) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-V1.0.2 + REQ-V1.0.3 scenarios."""
    log_path = tmp_path / "drift_events.jsonl"
    return {
        "log_path": log_path,
        "result": None,
    }


# ---------- Helpers ----------


def _seed_events(
    log_path: Path, count: int, *, changes: tuple[str, ...] = ("change-foo", "change-bar")
) -> None:
    """Append ``count`` events to ``log_path``, cycling through ``changes``."""
    log = DriftEventLog(path=log_path)
    for i in range(count):
        change = changes[i % len(changes)]
        log.append(
            DriftEvent(
                change=change,
                decision_id=100 + i,
                binding_id=f"obs-{i}",
                event_class="LABEL_DRIFT" if i % 2 == 0 else "STALE_LOCATION",
                detected_at=1_700_000_000.0 + float(i),
            )
        )


# ---------- Scenarios ----------


@scenario(
    "../bdd/req_v1_0_drift_events.feature",
    "Operator reads drift events as default text table (REQ-V1.0.2)",
)
def test_operator_reads_drift_events_as_text_table(
    drift_events_world: dict[str, Any],
) -> None:
    """REQ-V1.0.2: list default text table renders 5 rows + header columns."""


@scenario(
    "../bdd/req_v1_0_drift_events.feature",
    "Operator tails recent drift events newest-first (REQ-V1.0.3)",
)
def test_operator_tails_recent_drift_events(
    drift_events_world: dict[str, Any],
) -> None:
    """REQ-V1.0.3: tail --limit=5 returns 5 rows newest-first."""


@scenario(
    "../bdd/req_v1_0_drift_events.feature",
    "Operator summarizes drift counts per change (REQ-V1.0.3)",
)
def test_operator_summarizes_drift_counts(
    drift_events_world: dict[str, Any],
) -> None:
    """REQ-V1.0.3: stats renders per-change + per-event-class counts."""


# ---------- Given ----------


@given("the drift event log has 5 events from 2 changes")
def given_log_has_5_events_from_2_changes(
    drift_events_world: dict[str, Any],
) -> None:
    """Seed 5 events cycling through change-foo + change-bar."""
    _seed_events(drift_events_world["log_path"], 5)


@given("the drift event log has 15 events")
def given_log_has_15_events(drift_events_world: dict[str, Any]) -> None:
    """Seed 15 events (1 change) so tail --limit=5 returns the most-recent 5."""
    _seed_events(drift_events_world["log_path"], 15, changes=("change-foo",))


@given("the drift event log has 10 events from 3 changes")
def given_log_has_10_events_from_3_changes(
    drift_events_world: dict[str, Any],
) -> None:
    """Seed 10 events cycling through 3 changes (4 + 3 + 3 split)."""
    _seed_events(
        drift_events_world["log_path"],
        10,
        changes=("change-foo", "change-bar", "change-baz"),
    )


# ---------- When ----------


@when("the operator runs `flow drift-events list`")
def when_operator_runs_list(drift_events_world: dict[str, Any]) -> None:
    """Invoke ``flow drift-events list`` against the tmp log."""
    drift_events_world["result"] = runner.invoke(
        cli_main,
        [
            "drift",
            "events",
            "list",
            "--path",
            str(drift_events_world["log_path"]),
        ],
    )


@when(parsers.parse("the operator runs `flow drift-events tail --limit={limit:d}`"))
def when_operator_runs_tail_with_limit(drift_events_world: dict[str, Any], limit: int) -> None:
    """Invoke ``flow drift-events tail --limit=N`` against the tmp log."""
    drift_events_world["result"] = runner.invoke(
        cli_main,
        [
            "drift",
            "events",
            "tail",
            "--path",
            str(drift_events_world["log_path"]),
            "--limit",
            str(limit),
        ],
    )


@when("the operator runs `flow drift-events stats`")
def when_operator_runs_stats(drift_events_world: dict[str, Any]) -> None:
    """Invoke ``flow drift-events stats`` against the tmp log."""
    drift_events_world["result"] = runner.invoke(
        cli_main,
        [
            "drift",
            "events",
            "stats",
            "--path",
            str(drift_events_world["log_path"]),
        ],
    )


# ---------- Then ----------


@then(parsers.parse('the output contains a fixed-width table with columns "{columns}"'))
def then_output_contains_table_with_columns(
    drift_events_world: dict[str, Any], columns: str
) -> None:
    """Assert the stdout contains all 5 column names from the header."""
    result = drift_events_world["result"]
    assert result.exit_code == 0, result.output
    for col in columns.split(" | "):
        assert col.strip() in result.output, (
            f"expected column {col!r} in output; got {result.output!r}"
        )


@then("the table contains 5 data rows")
def then_table_contains_5_data_rows(drift_events_world: dict[str, Any]) -> None:
    """Assert exactly 5 data rows (change-* prefix)."""
    result = drift_events_world["result"]
    data_rows = [ln for ln in result.output.splitlines() if ln.startswith("change-")]
    assert len(data_rows) == 5, f"expected 5 data rows; got {len(data_rows)}: {data_rows!r}"


@then("the output contains exactly 5 rows")
def then_output_contains_5_rows(drift_events_world: dict[str, Any]) -> None:
    """Tail --limit=5 returns exactly 5 data rows."""
    result = drift_events_world["result"]
    data_rows = [ln for ln in result.output.splitlines() if ln.startswith("change-")]
    assert len(data_rows) == 5, f"expected 5 rows; got {len(data_rows)}: {data_rows!r}"


@then("the rows are ordered newest-first by detected_at")
def then_rows_ordered_newest_first(drift_events_world: dict[str, Any]) -> None:
    """Tail renders rows newest-first (highest detected_at first)."""
    result = drift_events_world["result"]
    # The 15 events were seeded with detected_at 1_700_000_000+i; the 5 newest
    # are i=14,13,12,11,10. Their decision_ids are 114,113,112,111,110 — but
    # the rendered row contains the change name + decision_id (str). The row
    # for i=14 must appear before the row for i=10 in the output.
    last_row_pos = result.output.find("obs-10")
    first_row_pos = result.output.find("obs-14")
    assert last_row_pos != -1, f"expected obs-10 in output; got {result.output!r}"
    assert first_row_pos != -1, f"expected obs-14 in output; got {result.output!r}"
    assert first_row_pos < last_row_pos, (
        f"expected obs-14 (newest) before obs-10 (oldest); "
        f"obs-14 at {first_row_pos} obs-10 at {last_row_pos}"
    )


@then("the output contains a per-change count table with 3 change rows")
def then_output_contains_per_change_counts(
    drift_events_world: dict[str, Any],
) -> None:
    """Stats text output contains all 3 change names."""
    result = drift_events_world["result"]
    assert result.exit_code == 0, result.output
    for change in ("change-foo", "change-bar", "change-baz"):
        assert change in result.output, (
            f"expected {change!r} in stats output; got {result.output!r}"
        )


@then("the output contains per-event-class counts")
def then_output_contains_per_event_class_counts(
    drift_events_world: dict[str, Any],
) -> None:
    """Stats text output contains event_class labels."""
    result = drift_events_world["result"]
    assert "LABEL_DRIFT" in result.output or "STALE_LOCATION" in result.output, (
        f"expected per-event-class labels in stats output; got {result.output!r}"
    )
