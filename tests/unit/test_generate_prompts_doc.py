"""Unit tests for scripts/generate_prompts_doc.py (REQ-V1.1.5 / REQ-53).

REQ-V1.1.5: docs/prompts.md is auto-generated from PROMPT_NAMES +
prompts/*.j2 templates so the catalog has a human-readable reference.

The generator must:
- Walk PROMPT_NAMES from src/flow_engineering/prompt_registry.py.
- Read each .j2 template body from prompts/.
- Render an example via render_prompt_safe (sentinel substitution for
  missing declared vars; never raises on missing variables).
- Emit Markdown with one section per prompt containing:
  * prompt_id
  * purpose (human-readable description)
  * where it appears (call-site reference)
  * example output (rendered with sentinels)

Strict TDD: tests written BEFORE the generator script. They MUST fail
with ImportError (script module not found) until the GREEN commit
creates scripts/generate_prompts_doc.py.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_prompts_doc.py"
DOC_PATH = REPO_ROOT / "docs" / "prompts.md"


def _load_script_module():
    """Load scripts/generate_prompts_doc.py as a module (no pip install)."""
    spec = importlib.util.spec_from_file_location("generate_prompts_doc", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load spec for {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestScriptExists:
    """The generator script exists at scripts/generate_prompts_doc.py."""

    def test_script_path_exists(self) -> None:
        assert SCRIPT_PATH.is_file(), f"generator script missing at {SCRIPT_PATH}"


class TestBuildSectionContract:
    """build_section(entry) returns Markdown with the 4 mandatory sub-sections."""

    def test_build_section_contains_prompt_id_heading(self) -> None:
        mod = _load_script_module()
        from flow_engineering.prompt_registry import PROMPT_NAMES

        strict_tdd = next(p for p in PROMPT_NAMES if p.name == "strict_tdd")
        section = mod.build_section(strict_tdd)

        # prompt_id appears as a heading.
        assert "## `strict_tdd`" in section

    def test_build_section_contains_purpose(self) -> None:
        mod = _load_script_module()
        from flow_engineering.prompt_registry import PROMPT_NAMES

        strict_tdd = next(p for p in PROMPT_NAMES if p.name == "strict_tdd")
        section = mod.build_section(strict_tdd)

        assert "### Purpose" in section
        # The purpose text is non-empty for the known prompts.
        assert "strict tdd mode" in section.lower()

    def test_build_section_contains_where_it_appears(self) -> None:
        mod = _load_script_module()
        from flow_engineering.prompt_registry import PROMPT_NAMES

        strict_tdd = next(p for p in PROMPT_NAMES if p.name == "strict_tdd")
        section = mod.build_section(strict_tdd)

        assert "### Where it appears" in section
        # The call-site reference is non-empty.
        assert "strict_tdd.py" in section

    def test_build_section_contains_example_output(self) -> None:
        mod = _load_script_module()
        from flow_engineering.prompt_registry import PROMPT_NAMES

        strict_tdd = next(p for p in PROMPT_NAMES if p.name == "strict_tdd")
        section = mod.build_section(strict_tdd)

        assert "### Example output" in section
        # The rendered example includes the sentinel for the missing
        # declared var (test_command) since render_prompt_safe substitutes.
        assert "<test_command>" in section


class TestBuildDocContract:
    """build_doc() returns a Markdown body with header table + all sections."""

    def test_build_doc_contains_summary_table(self) -> None:
        mod = _load_script_module()
        body = mod.build_doc()

        # Header summary table.
        assert "# Prompt registry" in body
        assert "| Prompt ID | Domain | Version | Variables |" in body

    def test_build_doc_includes_all_prompts(self) -> None:
        mod = _load_script_module()
        from flow_engineering.prompt_registry import PROMPT_NAMES

        body = mod.build_doc()
        for prompt in PROMPT_NAMES:
            assert f"## `{prompt.name}`" in body, f"missing section for prompt {prompt.name!r}"

    def test_build_doc_includes_template_body(self) -> None:
        mod = _load_script_module()
        body = mod.build_doc()

        # The template body should be rendered verbatim for one prompt.
        assert "STRICT TDD MODE IS ACTIVE" in body


class TestMainEndToEnd:
    """Running the script as `__main__` writes docs/prompts.md."""

    def test_main_writes_docs_prompts_md(self, tmp_path: Path) -> None:
        # Run the script as a subprocess so it picks up the package on sys.path.
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"script failed: stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert DOC_PATH.is_file(), f"docs/prompts.md missing at {DOC_PATH}"

        body = DOC_PATH.read_text(encoding="utf-8")
        assert "# Prompt registry" in body
        # Spot-check 4 known prompt ids.
        for prompt_id in (
            "strict_tdd",
            "auto_suggest_header",
            "auto_suggest_footer",
            "auto_suggest_empty",
        ):
            assert f"## `{prompt_id}`" in body, f"docs/prompts.md missing section for {prompt_id!r}"


class TestDocReproducibility:
    """build_doc() is deterministic — repeated calls produce identical output."""

    def test_build_doc_is_idempotent(self) -> None:
        mod = _load_script_module()
        body_a = mod.build_doc()
        body_b = mod.build_doc()
        assert body_a == body_b
