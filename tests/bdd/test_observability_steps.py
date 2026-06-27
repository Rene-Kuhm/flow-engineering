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


# ---------- Scenario bindings: REQ-37 ----------


@scenario(
    "../bdd/req37_metrics_domain.feature",
    "--domain snapshot shows only snapshot_* counters",
)
def test_req37_domain_snapshot(metrics_world: dict[str, Any]) -> None:
    pass


@scenario(
    "../bdd/req37_metrics_domain.feature",
    "No --domain shows all 8 domains aggregated",
)
def test_req37_no_domain_shows_all_8(metrics_world: dict[str, Any]) -> None:
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
            {"name": "suggest_invoked_total", "fields": {"count": 1}, "ts": _iso(now)}
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


# ---------- REQ-37 Given steps ----------


@given(
    parsers.parse(
        "12 metric events are written across 4 domains "
        "(3 binding + 3 drift + 3 vector + 3 snapshot)"
    )
)
def given_12_events_with_3_distinct_counters_per_domain(
    metrics_world: dict[str, Any],
) -> None:
    """Seed 12 events covering 4 domains with 3 distinct counter names each.

    Distinct counter names per domain (so the ``--domain snapshot`` BDD
    scenario can assert "stdout contains only the 3 snapshot_* counter
    names" as 3 distinct names rather than 1 counter aggregated 3 times).
    The 4 binding counters exercise REQ-8 close coverage; the 3 vector
    counters exercise REQ-22; the 3 snapshot counters exercise REQ-26
    graph-snapshots; the 3 drift counters exercise REQ-12.
    """
    now = datetime.now(UTC)
    events: list[dict] = [
        # 3 binding counters (3 distinct names)
        {"name": "suggest_invoked_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "bindings_confirmed_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "inspect_invoked_total", "fields": {"count": 1}, "ts": _iso(now)},
        # 3 drift counters (3 distinct names)
        {"name": "drift_invoked_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "drift_still_valid_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "drift_label_drift_total", "fields": {"count": 1}, "ts": _iso(now)},
        # 3 vector counters (3 distinct names)
        {"name": "vector_search_invoked_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "vector_search_results_returned_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "vector_search_latency_ms", "fields": {"elapsed_ms": 50}, "ts": _iso(now)},
        # 3 snapshot counters (3 distinct names)
        {"name": "snapshot_create_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "snapshot_rollback_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "snapshot_prune_total", "fields": {"count": 1}, "ts": _iso(now)},
    ]
    _write_jsonl(metrics_world["metrics_path"], events)


@given(
    parsers.parse(
        "24 metric events across all 8 domains (3 each)"
    )
)
def given_24_events_across_8_domains(
    metrics_world: dict[str, Any],
) -> None:
    """Seed 24 events covering all 8 accepted domains with 3 distinct counters each.

    Includes 3 fake ``engine_*`` counters (queue depth, startup, errors) that
    exercise the reserved REQ-42 slot. v1 production code emits no engine_*
    events, but the BDD scenario needs the ``engine`` domain header to appear
    in the no-flag default output (per design D5: 8 accepted domains).
    """
    now = datetime.now(UTC)
    events: list[dict] = [
        # 3 binding counters
        {"name": "suggest_invoked_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "bindings_confirmed_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "inspect_invoked_total", "fields": {"count": 1}, "ts": _iso(now)},
        # 3 backfill counters
        {"name": "backfill_observations_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "backfill_with_refs_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "backfill_coverage_ratio", "fields": {"value": 0.85}, "ts": _iso(now)},
        # 3 drift counters
        {"name": "drift_invoked_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "drift_still_valid_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "drift_label_drift_total", "fields": {"count": 1}, "ts": _iso(now)},
        # 3 vector counters
        {"name": "vector_search_invoked_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "vector_search_results_returned_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "vector_search_latency_ms", "fields": {"elapsed_ms": 50}, "ts": _iso(now)},
        # 3 federated counters
        {"name": "federated_search_invoked_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "federated_search_projects_queried", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "federated_search_results_returned_total", "fields": {"count": 1}, "ts": _iso(now)},
        # 3 snapshot counters
        {"name": "snapshot_create_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "snapshot_rollback_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "snapshot_prune_total", "fields": {"count": 1}, "ts": _iso(now)},
        # 3 metadata counters (REQ-13 / REQ-24)
        {"name": "update_observation_metadata_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "project_tag_total", "fields": {"count": 1}, "ts": _iso(now)},
        {"name": "project_alias_resolved_total", "fields": {"count": 1}, "ts": _iso(now)},
        # 3 engine counters (REQ-42 reserved slot — fake for BDD coverage)
        {"name": "engine_queue_depth", "fields": {"value": 5}, "ts": _iso(now)},
        {"name": "engine_startup_ms", "fields": {"elapsed_ms": 120}, "ts": _iso(now)},
        {"name": "engine_errors_total", "fields": {"count": 1}, "ts": _iso(now)},
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


# ---------- REQ-37 When steps ----------


@when(
    parsers.parse(
        "I run `flow metrics summary --domain snapshot --format text`"
    )
)
def when_run_metrics_summary_domain_snapshot_text(
    metrics_world: dict[str, Any],
) -> None:
    """Invoke ``flow metrics summary --domain snapshot --format text``."""
    metrics_world["command"] = [
        "metrics", "summary",
        "--domain", "snapshot",
        "--format", "text",
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


# ---------- REQ-37 Then steps ----------


@then(parsers.parse("stdout contains only the 3 snapshot_* counter names"))
def then_stdout_contains_only_3_snapshot_counters(
    metrics_world: dict[str, Any],
) -> None:
    """For the ``--domain snapshot`` scenario: only the 3 snapshot_* counters appear.

    Asserts that the rendered output contains the 3 snapshot counter names
    (snapshot_create_total / snapshot_rollback_total / snapshot_prune_total)
    AND does NOT contain any binding / drift / vector counter names that were
    seeded by the Given step. The ``--domain`` flag narrows the visible
    counter set to the snapshot domain; all 12 source events are filtered
    down to the 3 snapshot events.
    """
    result = metrics_world["result"]
    assert result.exit_code == 0, (
        f"expected exit 0; got {result.exit_code}. output={result.output!r}"
    )
    # The 3 distinct snapshot counter names MUST appear in the output.
    for expected in (
        "snapshot_create_total",
        "snapshot_rollback_total",
        "snapshot_prune_total",
    ):
        assert expected in result.output, (
            f"expected snapshot counter {expected!r} in stdout; "
            f"got {result.output!r}"
        )
    # All non-snapshot counter names MUST be excluded.
    for excluded in (
        "suggest_invoked_total",
        "bindings_confirmed_total",
        "inspect_invoked_total",
        "drift_invoked_total",
        "drift_still_valid_total",
        "drift_label_drift_total",
        "vector_search_invoked_total",
        "vector_search_results_returned_total",
        "vector_search_latency_ms",
    ):
        assert excluded not in result.output, (
            f"unexpected non-snapshot counter {excluded!r} in stdout: "
            f"{result.output!r}"
        )


@then(
    parsers.parse(
        'stdout does NOT contain "binding:" or "drift:" or "vector:"'
    )
)
def then_stdout_does_not_contain_other_domain_headers(
    metrics_world: dict[str, Any],
) -> None:
    """For the ``--domain snapshot`` scenario: only the ``snapshot:`` header appears.

    Asserts the text-dashboard section headers: with ``--domain snapshot``,
    the only domain header rendered MUST be ``snapshot:``. The
    ``binding:`` / ``drift:`` / ``vector:`` headers MUST NOT appear because
    their counters are filtered out before the summary is rendered.
    """
    result = metrics_world["result"]
    assert result.exit_code == 0, (
        f"expected exit 0; got {result.exit_code}. output={result.output!r}"
    )
    # The snapshot header MUST appear.
    assert "snapshot:" in result.output, (
        f"expected 'snapshot:' header in stdout; got {result.output!r}"
    )
    # Other-domain headers MUST NOT appear.
    for excluded_header in ("binding:", "drift:", "vector:"):
        assert excluded_header not in result.output, (
            f"unexpected domain header {excluded_header!r} in stdout: "
            f"{result.output!r}"
        )


@then(
    parsers.parse(
        "stdout contains all 8 domain headers "
        "(binding, drift, vector, snapshot, backfill, federated, metadata, engine)"
    )
)
def then_stdout_contains_all_8_domain_headers(
    metrics_world: dict[str, Any],
) -> None:
    """For the no-flag scenario: the no-filter default shows all 8 domains.

    Asserts that with NO ``--domain`` flag, the rendered text dashboard
    contains the headers for all 8 accepted domains (per
    :data:`observability.ALL_DOMAINS`). This validates that the
    no-filter path covers the cross-domain slice expansion — operators
    get the full picture without specifying a domain.
    """
    result = metrics_world["result"]
    assert result.exit_code == 0, (
        f"expected exit 0; got {result.exit_code}. output={result.output!r}"
    )
    for header in (
        "binding:",
        "drift:",
        "vector:",
        "snapshot:",
        "backfill:",
        "federated:",
        "metadata:",
        "engine:",
    ):
        assert header in result.output, (
            f"expected domain header {header!r} in stdout; got {result.output!r}"
        )