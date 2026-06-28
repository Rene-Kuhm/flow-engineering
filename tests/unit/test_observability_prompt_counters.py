"""Unit tests for prompt observability counters (REQ-V1.1.4 / REQ-52).

REQ-V1.1.4: 3 NEW counters land in :mod:`flow_engineering.observability`
to surface prompt render usage + failures:

- ``prompts_render_total{domain, prompt_id, status}`` — every render
  attempt (status = ``"ok"`` / ``"fail"``).
- ``prompts_render_ms{domain, prompt_id}`` — wall-clock duration in
  milliseconds (recorded alongside the corresponding
  ``prompts_render_total`` increment).
- ``prompts_render_failed_total{domain, prompt_id, error}`` — only
  failure events (error = ``"missing_var"`` / ``"template_error"`` /
  ``"unknown"``).

The counters flow through the existing :func:`observability.increment`
helper (JSONL append to ``~/.flow-engineering/metrics.jsonl``) and the
new ``prompts_`` prefix maps to the ``"prompt"`` domain in
:data:`DOMAIN_BY_PREFIX`.

Strict TDD: tests written BEFORE the implementation. They MUST fail
with ``AssertionError`` (counter line not found in the sink) until the
GREEN commit wires the counters + extends the prefix table.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from flow_engineering import observability
from flow_engineering import prompt_registry
from flow_engineering.prompt_registry import render_prompt


@pytest.fixture
def metrics_sink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Redirect the metrics sink to a tmp file so the test never touches
    the real ``~/.flow-engineering/metrics.jsonl``."""
    sink_path = tmp_path / "metrics.jsonl"
    monkeypatch.setattr(observability, "_DEFAULT_PATH", sink_path)
    monkeypatch.setattr(observability, "_resolve_path", lambda: sink_path)
    return sink_path


@pytest.fixture
def render_sink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Redirect the prompt render sink so render_prompt() doesn't touch disk."""
    sink_path = tmp_path / "prompt_renders.jsonl"
    from flow_engineering import prompt_render_log as log_mod

    monkeypatch.setattr(log_mod, "DEFAULT_PROMPT_RENDER_LOG_PATH", sink_path)
    monkeypatch.setenv("FLOW_PROMPT_LOG", "1")
    return sink_path


class TestPromptCountersCatalog:
    """The 3 NEW counter names exist in :data:`PROMPT_RENDER_COUNTER_NAMES`."""

    def test_catalog_contains_prompts_render_total(self) -> None:
        from flow_engineering.observability import PROMPT_RENDER_COUNTER_NAMES

        assert "prompts_render_total" in PROMPT_RENDER_COUNTER_NAMES

    def test_catalog_contains_prompts_render_ms(self) -> None:
        from flow_engineering.observability import PROMPT_RENDER_COUNTER_NAMES

        assert "prompts_render_ms" in PROMPT_RENDER_COUNTER_NAMES

    def test_catalog_contains_prompts_render_failed_total(self) -> None:
        from flow_engineering.observability import PROMPT_RENDER_COUNTER_NAMES

        assert "prompts_render_failed_total" in PROMPT_RENDER_COUNTER_NAMES


class TestPromptCountersDomainMapping:
    """The ``prompts_`` prefix maps to the ``"prompt"`` domain."""

    def test_prompts_prefix_maps_to_prompt_domain(self) -> None:
        from flow_engineering.observability import (
            DOMAIN_BY_PREFIX,
            _domain_for_counter,
        )

        assert DOMAIN_BY_PREFIX.get("prompts_") == "prompt"
        assert _domain_for_counter("prompts_render_total") == "prompt"
        assert _domain_for_counter("prompts_render_ms") == "prompt"
        assert _domain_for_counter("prompts_render_failed_total") == "prompt"


class TestRecordPromptRenderSummary:
    """The ``record_prompt_render_summary`` helper emits the 3 counters."""

    def test_successful_render_emits_ok_counter(
        self, metrics_sink: Path, render_sink: Path
    ) -> None:
        from flow_engineering.observability import (
            record_prompt_render_summary,
        )

        record_prompt_render_summary(
            prompt_id="strict_tdd",
            domain="binding",
            elapsed_ms=10.0,
            ok=True,
            error=None,
        )

        events = observability.read_all(path=metrics_sink)
        names = {e["name"] for e in events}
        assert "prompts_render_total" in names
        assert "prompts_render_ms" in names
        # No failure for a successful render.
        assert "prompts_render_failed_total" not in names

        # The total counter has status=ok.
        ok_event = next(
            e for e in events if e["name"] == "prompts_render_total"
        )
        assert ok_event["fields"].get("status") == "ok"
        assert ok_event["fields"].get("prompt_id") == "strict_tdd"
        assert ok_event["fields"].get("domain") == "binding"

    def test_failed_render_emits_failure_counters(
        self, metrics_sink: Path, render_sink: Path
    ) -> None:
        from flow_engineering.observability import (
            record_prompt_render_summary,
        )

        record_prompt_render_summary(
            prompt_id="x",
            domain="binding",
            elapsed_ms=2.5,
            ok=False,
            error="missing_var",
        )

        events = observability.read_all(path=metrics_sink)
        names = {e["name"] for e in events}
        assert "prompts_render_total" in names
        assert "prompts_render_ms" in names
        assert "prompts_render_failed_total" in names

        # Total counter has status=fail.
        total_event = next(
            e for e in events if e["name"] == "prompts_render_total"
        )
        assert total_event["fields"].get("status") == "fail"

        # Failure counter has the error label.
        fail_event = next(
            e for e in events if e["name"] == "prompts_render_failed_total"
        )
        assert fail_event["fields"].get("error") == "missing_var"
        assert fail_event["fields"].get("prompt_id") == "x"


class TestRenderPromptEmitsCounters:
    """The ``render_prompt()`` integration emits the counters on every call.

    This is the END-TO-END test that closes T4.3: every successful OR
    failed render increments the catalog and the JSONL sink records
    the event.
    """

    def test_render_emits_prompts_render_total_ok(
        self, metrics_sink: Path, render_sink: Path
    ) -> None:
        render_prompt("strict_tdd", test_command="pytest")
        events = observability.read_all(path=metrics_sink)
        ok_events = [
            e for e in events if e["name"] == "prompts_render_total"
        ]
        assert len(ok_events) >= 1
        assert ok_events[-1]["fields"].get("status") == "ok"

    def test_render_failure_emits_failed_total(
        self, metrics_sink: Path, render_sink: Path
    ) -> None:
        with pytest.raises(Exception):
            render_prompt("definitely_not_in_catalog_zzz")
        events = observability.read_all(path=metrics_sink)
        fail_events = [
            e for e in events if e["name"] == "prompts_render_failed_total"
        ]
        assert len(fail_events) >= 1
        assert fail_events[-1]["fields"].get("error") == "unknown"

    def test_render_emits_real_domain_label(
        self, metrics_sink: Path, render_sink: Path
    ) -> None:
        """REQ-V1.1.4 REFACTOR: domain label surfaces the prompt's
        PromptDomain.value, not the 'unknown' fallback (T4.4)."""
        render_prompt("strict_tdd", test_command="pytest")
        events = observability.read_all(path=metrics_sink)
        ok_events = [
            e for e in events if e["name"] == "prompts_render_total"
        ]
        assert len(ok_events) >= 1
        # strict_tdd is registered under PromptDomain.OBSERVABILITY.
        assert ok_events[-1]["fields"].get("domain") == "observability"
        assert ok_events[-1]["fields"].get("prompt_id") == "strict_tdd"


class TestPromptDomainSummarizeIntegration:
    """The :func:`summarize` helper buckets prompt counters into the
    ``"prompt"`` domain, not ``"unknown"``."""

    def test_summarize_groups_prompts_under_prompt_domain(
        self, metrics_sink: Path, render_sink: Path
    ) -> None:
        from flow_engineering.observability import (
            record_prompt_render_summary,
            summarize,
        )

        record_prompt_render_summary(
            prompt_id="x",
            domain="binding",
            elapsed_ms=1.0,
            ok=True,
            error=None,
        )
        record_prompt_render_summary(
            prompt_id="x",
            domain="binding",
            elapsed_ms=1.0,
            ok=False,
            error="template_error",
        )

        metric_events = observability.read_all_metrics(path=metrics_sink)
        result = summarize(metric_events)
        assert "prompt" in result
        assert "prompts_render_total" in result["prompt"]
        assert "prompts_render_ms" in result["prompt"]
        assert "prompts_render_failed_total" in result["prompt"]