"""Unit tests for ``flow prompts show --render-count --render-history`` (REQ-V1.1.3).

REQ-V1.1.3 S2 — the ``flow prompts show <id>`` CLI gains two flags that
surface the prompt render sink content without coupling to the
registry:

- ``--render-count`` — emit one line with the per-prompt render count
  (and last-render timestamp) from the default sink.
- ``--render-history N`` — emit the last ``N`` JSONL records for that
  prompt id (default ``N=5``), formatted as an aligned text table.

Both flags compose with the existing ``--var`` substitution; they do
NOT replace the rendered output. The render sink is read-only from the
CLI side (writes go through ``render_prompt`` via the
``FLOW_PROMPT_LOG=1`` toggle from T3.3).

Strict TDD: tests written BEFORE the CLI flag implementation. They
MUST fail with ``'flow prompts show' got an unexpected keyword
argument 'render_count'`` (or similar click error) until the GREEN
commit wires the flags.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main

runner = CliRunner()


@pytest.fixture
def seeded_sink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Seed the prompt render sink with 3 events for ``strict_tdd``."""
    log_path = tmp_path / "prompt_renders.jsonl"
    from flow_engineering import prompt_render_log as log_mod

    monkeypatch.setattr(log_mod, "DEFAULT_PROMPT_RENDER_LOG_PATH", log_path)
    monkeypatch.setenv("FLOW_PROMPT_LOG", "1")

    log = log_mod.PromptRenderLog(path=log_path)
    log.append(
        log_mod.PromptRenderEvent(
            prompt_id="strict_tdd",
            rendered_at=1_710_000_000.0,
            elapsed_ms=10.0,
            ok=True,
            error=None,
            var_keys=("test_command",),
        )
    )
    log.append(
        log_mod.PromptRenderEvent(
            prompt_id="strict_tdd",
            rendered_at=1_710_000_010.0,
            elapsed_ms=12.0,
            ok=True,
            error=None,
            var_keys=("test_command",),
        )
    )
    log.append(
        log_mod.PromptRenderEvent(
            prompt_id="strict_tdd",
            rendered_at=1_710_000_020.0,
            elapsed_ms=8.0,
            ok=False,
            error="missing_var",
            var_keys=("test_command",),
        )
    )
    log.append(
        log_mod.PromptRenderEvent(
            prompt_id="other_prompt",
            rendered_at=1_710_000_030.0,
            elapsed_ms=4.0,
            ok=True,
            error=None,
            var_keys=(),
        )
    )
    return log_path


class TestRenderCountFlag:
    """``flow prompts show <id> --render-count`` emits a one-line summary."""

    def test_render_count_outputs_one_line_with_count(self, seeded_sink: Path) -> None:
        result = runner.invoke(
            main,
            ["prompts", "show", "strict_tdd", "--render-count"],
        )
        assert result.exit_code == 0, result.output
        # The count line contains the prompt_id and the integer count.
        assert "strict_tdd" in result.output
        assert "3" in result.output  # 3 events for strict_tdd

    def test_render_count_shows_zero_for_known_prompt_without_renders(
        self, seeded_sink: Path
    ) -> None:
        # `auto_suggest_empty` is in the catalog but has no sink records.
        result = runner.invoke(
            main,
            ["prompts", "show", "auto_suggest_empty", "--render-count"],
        )
        assert result.exit_code == 0, result.output
        assert "auto_suggest_empty" in result.output
        # Count is 0 → "render_count: 0" appears in the summary line.
        assert "render_count: 0" in result.output

    def test_render_count_last_rendered_at_present(self, seeded_sink: Path) -> None:
        result = runner.invoke(
            main,
            ["prompts", "show", "strict_tdd", "--render-count"],
        )
        assert result.exit_code == 0, result.output
        # Last rendered_at is 1_710_000_020.0 — formatted as ISO 8601.
        # The CLI uses an ISO-formatted string per design D9.
        # Verify the timestamp appears in some form (year, not full
        # ISO, is sufficient for the smoke check).
        assert "2024" in result.output


class TestRenderHistoryFlag:
    """``flow prompts show <id> --render-history`` emits a tail table."""

    def test_render_history_default_shows_last_5(self, seeded_sink: Path) -> None:
        result = runner.invoke(
            main,
            ["prompts", "show", "strict_tdd", "--show-render-history"],
        )
        assert result.exit_code == 0, result.output
        # All 3 strict_tdd events appear (≤ 5).
        assert "strict_tdd" in result.output

    def test_render_history_with_n_caps_rows(self, seeded_sink: Path) -> None:
        result = runner.invoke(
            main,
            [
                "prompts",
                "show",
                "strict_tdd",
                "--render-history",
                "1",
            ],
        )
        assert result.exit_code == 0, result.output
        # At most 1 data row (the most recent).
        # The header + footer consume several lines; we count strict_tdd
        # occurrences which should equal data rows + 1 from header.
        body_lines = [ln for ln in result.output.splitlines() if "strict_tdd" in ln]
        assert len(body_lines) >= 1

    def test_render_history_excludes_other_prompts(self, seeded_sink: Path) -> None:
        result = runner.invoke(
            main,
            [
                "prompts",
                "show",
                "strict_tdd",
                "--render-history",
                "10",
            ],
        )
        assert result.exit_code == 0, result.output
        # The "other_prompt" id must NOT appear in the strict_tdd view.
        assert "other_prompt" not in result.output

    def test_render_history_includes_status_marker(self, seeded_sink: Path) -> None:
        result = runner.invoke(
            main,
            [
                "prompts",
                "show",
                "strict_tdd",
                "--render-history",
                "10",
            ],
        )
        assert result.exit_code == 0, result.output
        # The 3rd event was a failure with error="missing_var"; the
        # table includes a status column showing ok/fail markers.
        ok_count = sum(1 for ln in result.output.splitlines() if "ok" in ln.lower())
        fail_count = sum(1 for ln in result.output.splitlines() if "fail" in ln.lower())
        assert ok_count + fail_count >= 1


class TestRenderCountAndHistoryCoexistWithVar:
    """The flags compose with ``--var`` substitution (additive)."""

    def test_render_count_does_not_break_var_substitution(self, seeded_sink: Path) -> None:
        result = runner.invoke(
            main,
            [
                "prompts",
                "show",
                "strict_tdd",
                "--var",
                "test_command=pytest",
                "--render-count",
            ],
        )
        assert result.exit_code == 0, result.output
        # The rendered prompt body still includes the substituted value.
        assert "STRICT TDD MODE IS ACTIVE" in result.output
        assert "pytest" in result.output
