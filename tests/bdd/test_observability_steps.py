"""BDD step definitions for the observability feature files (REQ-35..39).

Covers ``req35_metrics_summary.feature`` (2 scenarios) — the BDD acceptance
gate for the ``flow metrics summary`` subcommand introduced in change #6
PR#1 batch A T1.2.

The shared BDD glue file is the convention set by ``graph-snapshots`` (D12 in
``openspec/changes/observability/design.md``). PR#1 lands ~150 LOC for
req35/36/37; PR#2 extends with ~120 LOC delta for req38/39.

Test isolation:
- Each scenario uses ``tmp_path`` for ``FLOW_METRICS_PATH`` so the user's
  real ``~/.flow-engineering/metrics.jsonl`` is never touched.
- The ``metrics_world`` fixture holds the CliRunner invocation result so
  Then steps can assert on ``result.exit_code`` / ``result.output``.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering.cli import main


runner = CliRunner()


# ---------- World fixture ----------


@pytest.fixture
def metrics_world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Per-scenario scratch state for the observability BDD scenarios."""
    metrics_file = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))
    return {
        "metrics_path": metrics_file,
        "result": None,
        "command": None,
    }


# ---------- Helpers ----------


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_jsonl(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")


# ---------- Scenario bindings: REQ-35 ----------


@scenario(
    "../bdd/req35_metrics_summary.feature",
    "Summary over all domains shows per-domain counter totals",
)
def test_req35_summary_per_domain(metrics_world: dict[str, Any]) -> None:
    pass


@scenario(
    "../bdd/req35_metrics_summary.feature",
    "Summary with empty metrics file emits \"no metrics yet\" message",
)
def test_req35_summary_empty_sink(metrics_world: dict[str, Any]) -> None:
    pass


# ---------- Scenario bindings: REQ-36 ----------


@scenario(
    "../bdd/req36_metrics_window.feature",
    "--window 1h filters to last 1 hour",
)
def test_req36_window_1h(metrics_world: dict[str, Any]) -> None:
    pass


@scenario(
    "../bdd/req36_metrics_window.feature",
    "--since ISO8601 filters to events after timestamp",
)
def test_req36_since_iso8601(metrics_world: dict[str, Any]) -> None:
    pass


# ---------- Given steps ----------


@given(
    parsers.parse(
        "12 metric events are written across 4 domains "
        "(3 binding + 3 drift + 3 vector + 3 snapshot)"
    )
)
def given_12_events_across_4_domains(metrics_world: dict[str, Any]) -> None:
    """Seed the JSONL sink with 12 events covering 4 domains (3 each)."""
    now = datetime.now(UTC)
    events: list[dict] = []
    for _ in range(3):
        events.append(
            {"name": "binding_suggest_invoked_total", "fields": {"count": 1}, "ts": _iso(now)}
        )
    for _ in range(3):
        events.append(
            {"name": "drift_invoked_total", "fields": {"count": 1}, "ts": _iso(now)}
        )
    for _ in range(3):
        events.append(
            {"name": "vector_search_invoked_total", "fields": {"count": 1}, "ts": _iso(now)}
        )
    for _ in range(3):
        events.append(
            {"name": "snapshot_create_total", "fields": {"count": 1}, "ts": _iso(now)}
        )
    _write_jsonl(metrics_world["metrics_path"], events)


@given("metrics file does not exist")
def given_metrics_file_missing(metrics_world: dict[str, Any]) -> None:
    """Ensure the metrics file is absent before the When step."""
    if metrics_world["metrics_path"].exists():
        metrics_world["metrics_path"].unlink()


@given(
    parsers.parse(
        "5 metric events are written spanning 3 days "
        "(oldest 3d ago, newest 30m ago)"
    )
)
def given_5_events_spanning_3_days_window(
    metrics_world: dict[str, Any],
) -> None:
    """Seed 5 events with deterministic offsets relative to ``now``.

    Layout: events at -3d, -2d, -1d, -90m, -30m. With a 1h rolling window
    only the -30m event survives (the -90m event is 1.5h old, just outside).
    The counter names are all distinct so the dashboard renders one line each.
    """
    now = datetime.now(UTC)
    offsets = [
        (timedelta(days=3), "binding_event_oldest_3d"),
        (timedelta(days=2), "binding_event_2d"),
        (timedelta(days=1), "binding_event_1d"),
        (timedelta(minutes=90), "binding_event_90m"),
        (timedelta(minutes=30), "binding_event_30m"),
    ]
    events: list[dict] = []
    for offset, name in offsets:
        events.append({
            "name": name,
            "fields": {"count": 1},
            "ts": _iso(now - offset),
        })
    _write_jsonl(metrics_world["metrics_path"], events)


@given("5 metric events spanning 3 days")
def given_5_events_spanning_3_days_for_since(
    metrics_world: dict[str, Any],
) -> None:
    """Seed 5 events spanning 3 days around the 2026-06-26T00:00:00Z boundary.

    Exactly 2 events have ``ts >= 2026-06-26T00:00:00Z`` (the 2026-06-26T01:00
    and 2026-06-27T00:00 events); the other 3 are before the boundary. This
    is the setup for the ``--since 2026-06-26T00:00:00Z`` filter scenario.
    """
    events: list[dict] = [
        {"name": "counter_a", "fields": {"count": 1}, "ts": "2026-06-25T23:00:00Z"},
        {"name": "counter_b", "fields": {"count": 1}, "ts": "2026-06-25T23:30:00Z"},
        {"name": "counter_c", "fields": {"count": 1}, "ts": "2026-06-25T23:59:00Z"},
        {"name": "counter_d", "fields": {"count": 1}, "ts": "2026-06-26T01:00:00Z"},
        {"name": "counter_e", "fields": {"count": 1}, "ts": "2026-06-27T00:00:00Z"},
    ]
    _write_jsonl(metrics_world["metrics_path"], events)


# ---------- When steps ----------


@when(parsers.parse("I run `flow metrics summary --format text`"))
def when_run_metrics_summary_text(metrics_world: dict[str, Any]) -> None:
    """Invoke ``flow metrics summary --format text`` via CliRunner."""
    metrics_world["command"] = ["metrics", "summary", "--format", "text"]
    metrics_world["result"] = runner.invoke(main, metrics_world["command"])


@when(parsers.parse("I run `flow metrics summary --window 1h --format text`"))
def when_run_metrics_summary_window_1h_text(
    metrics_world: dict[str, Any],
) -> None:
    """Invoke ``flow metrics summary --window 1h --format text`` via CliRunner."""
    metrics_world["command"] = [
        "metrics", "summary", "--window", "1h", "--format", "text",
    ]
    metrics_world["result"] = runner.invoke(main, metrics_world["command"])


@when(
    parsers.parse(
        "I run `flow metrics summary --since 2026-06-26T00:00:00Z --format json`"
    )
)
def when_run_metrics_summary_since_iso_json(
    metrics_world: dict[str, Any],
) -> None:
    """Invoke ``flow metrics summary --since <iso> --format json``."""
    metrics_world["command"] = [
        "metrics", "summary",
        "--since", "2026-06-26T00:00:00Z",
        "--format", "json",
    ]
    metrics_world["result"] = runner.invoke(main, metrics_world["command"])


# ---------- Then steps ----------


@then(parsers.parse('stdout contains a "{section}" section'))
def then_stdout_contains_section(
    metrics_world: dict[str, Any], section: str
) -> None:
    result = metrics_world["result"]
    assert result.exit_code == 0, (
        f"expected exit 0; got {result.exit_code}. output={result.output!r}"
    )
    assert section in result.output, (
        f"expected {section!r} in stdout; got {result.output!r}"
    )


@then(parsers.parse('stdout contains the literal text "{needle}"'))
def then_stdout_contains_literal(
    metrics_world: dict[str, Any], needle: str
) -> None:
    result = metrics_world["result"]
    assert needle in result.output, (
        f"expected {needle!r} in stdout; got {result.output!r}"
    )


@then(parsers.parse('stdout contains "{needle}"'))
def then_stdout_contains(
    metrics_world: dict[str, Any], needle: str
) -> None:
    result = metrics_world["result"]
    assert needle in result.output, (
        f"expected {needle!r} in stdout; got {result.output!r}"
    )


@then("exit code is 0")
def then_exit_code_zero(metrics_world: dict[str, Any]) -> None:
    result = metrics_world["result"]
    assert result.exit_code == 0, (
        f"expected exit 0; got {result.exit_code}. output={result.output!r}"
    )


@then(parsers.parse("stdout contains only the most-recent event's counter"))
def then_stdout_contains_only_most_recent_counter(
    metrics_world: dict[str, Any],
) -> None:
    """For the 1h window scenario: only ``binding_event_30m`` survives."""
    result = metrics_world["result"]
    assert result.exit_code == 0, (
        f"expected exit 0; got {result.exit_code}. output={result.output!r}"
    )
    assert "binding_event_30m" in result.output, (
        f"expected most-recent event counter in stdout; got {result.output!r}"
    )
    # All older events MUST be excluded.
    for excluded in (
        "binding_event_oldest_3d",
        "binding_event_2d",
        "binding_event_1d",
        "binding_event_90m",
    ):
        assert excluded not in result.output, (
            f"unexpected older counter {excluded!r} in stdout: {result.output!r}"
        )


@then(
    parsers.parse(
        "stdout JSON contains exactly the 2 events after that timestamp"
    )
)
def then_stdout_json_contains_exactly_2_events(
    metrics_world: dict[str, Any],
) -> None:
    """For the --since scenario: only ``counter_d`` and ``counter_e`` survive."""
    result = metrics_world["result"]
    assert result.exit_code == 0, (
        f"expected exit 0; got {result.exit_code}. output={result.output!r}"
    )
    payload = json.loads(result.output)
    # Flatten the nested {domain: {counter: count}} shape and assert exactly
    # the 2 expected counter names are present (each with count=1).
    flat = {
        counter: count
        for domain_map in payload.values()
        for counter, count in domain_map.items()
    }
    assert flat == {"counter_d": 1, "counter_e": 1}, (
        f"unexpected payload: {flat!r}"
    )