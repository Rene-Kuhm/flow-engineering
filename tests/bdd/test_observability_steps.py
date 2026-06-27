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
from datetime import UTC, datetime
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


# ---------- When steps ----------


@when(parsers.parse("I run `flow metrics summary --format text`"))
def when_run_metrics_summary_text(metrics_world: dict[str, Any]) -> None:
    """Invoke ``flow metrics summary --format text`` via CliRunner."""
    metrics_world["command"] = ["metrics", "summary", "--format", "text"]
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