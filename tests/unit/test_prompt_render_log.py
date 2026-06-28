"""Unit tests for ``prompt_render_log.py`` (REQ-V1.1.3 / REQ-51).

REQ-V1.1.3: append-only JSONL sink for every ``render_prompt()`` call,
gated by the ``FLOW_PROMPT_LOG=1`` opt-in env var. The sink writes to
``~/.flow_engineering/prompt_renders.jsonl`` with one line per render
event. The CLI ``flow prompts show <id> --render-count --render-history``
surfaces the recorded data without coupling to the registry.

Strict TDD: written BEFORE the implementation per the project convention.
They MUST fail with ``ModuleNotFoundError: No module named
'flow_engineering.prompt_render_log'`` until the impl lands in
``src/flow_engineering/prompt_render_log.py``.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from flow_engineering.prompt_render_log import (
    DEFAULT_PROMPT_RENDER_LOG_PATH,
    PromptRenderEvent,
    PromptRenderLog,
    record_prompt_render,
)


class TestPromptRenderEventSchema:
    """The dataclass wire-format mirror of the JSONL sink contract."""

    def test_event_has_required_fields(self) -> None:
        from dataclasses import fields

        names = {f.name for f in fields(PromptRenderEvent)}
        assert {
            "prompt_id",
            "rendered_at",
            "elapsed_ms",
            "ok",
            "error",
            "var_keys",
        } <= names

    def test_event_ok_round_trips_to_json(self) -> None:
        ev = PromptRenderEvent(
            prompt_id="strict_tdd",
            rendered_at=1_710_000_000.0,
            elapsed_ms=12.5,
            ok=True,
            error=None,
            var_keys=("test_command",),
        )
        d = ev.to_json_dict()
        assert d["prompt_id"] == "strict_tdd"
        assert d["rendered_at"] == 1_710_000_000.0
        assert d["elapsed_ms"] == 12.5
        assert d["ok"] is True
        assert d["error"] is None
        assert d["var_keys"] == ["test_command"]

    def test_event_failed_carries_error_message(self) -> None:
        ev = PromptRenderEvent(
            prompt_id="missing_var_x",
            rendered_at=1_710_000_001.0,
            elapsed_ms=0.3,
            ok=False,
            error="missing_var",
            var_keys=(),
        )
        assert ev.ok is False
        assert ev.error == "missing_var"
        assert ev.to_json_dict()["error"] == "missing_var"


class TestPromptRenderLogAppendAndRead:
    """The append-only JSONL writer contract (mirrors DriftEventLog)."""

    def test_append_writes_one_jsonl_line(self, tmp_path: Path) -> None:
        log_path = tmp_path / "prompt_renders.jsonl"
        log = PromptRenderLog(path=log_path)
        ev = PromptRenderEvent(
            prompt_id="strict_tdd",
            rendered_at=1_710_000_000.0,
            elapsed_ms=10.0,
            ok=True,
            error=None,
            var_keys=("test_command",),
        )
        log.append(ev)

        raw = log_path.read_text(encoding="utf-8").strip()
        assert raw, "expected one non-empty JSONL line"
        data = json.loads(raw)
        assert data["prompt_id"] == "strict_tdd"
        assert data["ok"] is True

    def test_read_all_returns_appended_events_in_order(self, tmp_path: Path) -> None:
        log_path = tmp_path / "prompt_renders.jsonl"
        log = PromptRenderLog(path=log_path)
        log.append(
            PromptRenderEvent(
                prompt_id="a",
                rendered_at=1_710_000_000.0,
                elapsed_ms=1.0,
                ok=True,
                error=None,
                var_keys=(),
            )
        )
        log.append(
            PromptRenderEvent(
                prompt_id="b",
                rendered_at=1_710_000_001.0,
                elapsed_ms=2.0,
                ok=True,
                error=None,
                var_keys=(),
            )
        )
        events = log.read_all()
        assert [e.prompt_id for e in events] == ["a", "b"]
        assert events[0].rendered_at == 1_710_000_000.0
        assert events[1].elapsed_ms == 2.0

    def test_read_all_missing_file_returns_empty_list(self, tmp_path: Path) -> None:
        log_path = tmp_path / "does_not_exist.jsonl"
        log = PromptRenderLog(path=log_path)
        assert log.read_all() == []

    def test_read_all_skips_malformed_lines(self, tmp_path: Path) -> None:
        log_path = tmp_path / "prompt_renders.jsonl"
        log_path.write_text(
            "not json at all\n"
            + json.dumps({"prompt_id": "ok", "rendered_at": 1.0}) + "\n",
            encoding="utf-8",
        )
        log = PromptRenderLog(path=log_path)
        events = log.read_all()
        assert len(events) == 1
        assert events[0].prompt_id == "ok"

    def test_default_path_lives_under_flow_engineering_dir(self) -> None:
        assert DEFAULT_PROMPT_RENDER_LOG_PATH.parent.name == ".flow-engineering"
        assert DEFAULT_PROMPT_RENDER_LOG_PATH.name == "prompt_renders.jsonl"


class TestRecordPromptRenderFunction:
    """The ``record_prompt_render()`` module-level helper writes to the default sink.

    The helper accepts the same fields as ``PromptRenderEvent`` so callers
    don't have to instantiate the dataclass themselves (mirrors the v1.0
    ``record_*`` observability helpers).
    """

    def test_record_writes_event_to_default_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log_path = tmp_path / "prompt_renders.jsonl"
        monkeypatch.setattr(
            "flow_engineering.prompt_render_log.DEFAULT_PROMPT_RENDER_LOG_PATH",
            log_path,
        )
        monkeypatch.setenv("FLOW_PROMPT_LOG", "1")

        record_prompt_render(
            prompt_id="strict_tdd",
            rendered_at=1_710_000_000.0,
            elapsed_ms=15.0,
            ok=True,
            error=None,
            var_keys=("test_command",),
        )

        raw = log_path.read_text(encoding="utf-8").strip()
        assert raw
        data = json.loads(raw)
        assert data["prompt_id"] == "strict_tdd"
        assert data["elapsed_ms"] == 15.0

    def test_record_no_op_when_log_disabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log_path = tmp_path / "prompt_renders.jsonl"
        monkeypatch.setattr(
            "flow_engineering.prompt_render_log.DEFAULT_PROMPT_RENDER_LOG_PATH",
            log_path,
        )
        monkeypatch.setenv("FLOW_PROMPT_LOG", "0")

        record_prompt_render(
            prompt_id="strict_tdd",
            rendered_at=1_710_000_000.0,
            elapsed_ms=1.0,
            ok=True,
            error=None,
            var_keys=(),
        )

        # FLOW_PROMPT_LOG=0 → no file written.
        assert not log_path.exists()

    def test_record_enabled_when_env_var_is_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log_path = tmp_path / "prompt_renders.jsonl"
        monkeypatch.setattr(
            "flow_engineering.prompt_render_log.DEFAULT_PROMPT_RENDER_LOG_PATH",
            log_path,
        )
        monkeypatch.setenv("FLOW_PROMPT_LOG", "1")

        record_prompt_render(
            prompt_id="x",
            rendered_at=1_710_000_000.0,
            elapsed_ms=1.0,
            ok=True,
            error=None,
            var_keys=(),
        )

        assert log_path.exists()


class TestRecordPromptRenderIsolatesIOFailures:
    """The sink is best-effort — a write failure must NOT crash callers."""

    def test_record_swallows_os_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Replace the PromptRenderLog class with one whose append() raises.
        from flow_engineering import prompt_render_log as mod

        class BoomLog:
            def append(self, ev: object) -> None:
                raise OSError("disk full")

        # Monkeypatch the module's `_log_for` factory so the helper uses BoomLog.
        # record_prompt_render calls _log_for() internally; if that helper
        # exists and returns a real PromptRenderLog, we substitute.
        monkeypatch.setattr(mod, "PromptRenderLog", BoomLog)

        # Should NOT raise (best-effort sink).
        mod.record_prompt_render(
            prompt_id="x",
            rendered_at=1_710_000_000.0,
            elapsed_ms=1.0,
            ok=True,
            error=None,
            var_keys=(),
        )


class TestIsPromptLogEnabled:
    """The FLOW_PROMPT_LOG=1 gate is read once per call."""

    def test_default_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("FLOW_PROMPT_LOG", raising=False)
        from flow_engineering.prompt_render_log import _is_prompt_log_enabled

        assert _is_prompt_log_enabled() is False

    def test_one_enables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FLOW_PROMPT_LOG", "1")
        from flow_engineering.prompt_render_log import _is_prompt_log_enabled

        assert _is_prompt_log_enabled() is True

    def test_true_enables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FLOW_PROMPT_LOG", "true")
        from flow_engineering.prompt_render_log import _is_prompt_log_enabled

        assert _is_prompt_log_enabled() is True

    def test_zero_disables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FLOW_PROMPT_LOG", "0")
        from flow_engineering.prompt_render_log import _is_prompt_log_enabled

        assert _is_prompt_log_enabled() is False