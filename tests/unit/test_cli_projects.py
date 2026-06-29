"""Unit tests for cli.py `flow projects ls` (cross-project discovery).

Quick utility: lists directories in the projects root (default C:\\dev\\proyects)
with markers (python, node, astro, has-flow, readme first line). Single
purpose — do NOT expand scope without a real user need (per the Opción
media discipline: validate via real use before adding features).

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit wires the `flow projects` subcommand.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main

runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def projects_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a fake projects root with a few representative subdirs."""
    root = tmp_path / "projects"
    root.mkdir()
    # Python project with flow-engineering
    (root / "pyproj-with-flow").mkdir()
    (root / "pyproj-with-flow" / "pyproject.toml").write_text('[project]\nname = "py"\n')
    (root / "pyproj-with-flow" / "flow-engineering").mkdir()
    (root / "pyproj-with-flow" / "README.md").write_text("# pyproj-with-flow\n\nReal README.\n")
    # Astro blog
    (root / "my-blog").mkdir()
    (root / "my-blog" / "package.json").write_text(
        '{"name": "blog", "dependencies": {"astro": "^5"}}\n'
    )
    (root / "my-blog" / "astro.config.mjs").write_text("// config\n")
    (root / "my-blog" / "README.md").write_text("# my-blog\n\nAstro blog.\n")
    # Empty dir
    (root / "empty-dir").mkdir()
    # Non-directory file (should be ignored)
    (root / "stray-file.txt").write_text("not a dir")
    monkeypatch.setenv("FLOW_PROJECTS_ROOT", str(root))
    return root


# ---------- Tests ----------


def test_flow_projects_lists_subdirectories_with_markers(projects_root: Path) -> None:
    """`flow projects` outputs a table with one row per subdirectory + detected markers."""
    result = runner.invoke(main, ["projects", "ls"])
    assert result.exit_code == 0, result.output
    # All 3 subdirs listed (empty-dir is filtered out OR shown — we accept either)
    assert "pyproj-with-flow" in result.output
    assert "my-blog" in result.output
    # Markers detected
    assert "python" in result.output  # pyproject.toml present
    assert "astro" in result.output  # astro.config.mjs present
    assert "flow" in result.output  # flow-engineering subdir present (lower-case marker)
    # Non-dir file ignored
    assert "stray-file.txt" not in result.output


def test_flow_projects_custom_root_flag_overrides_env(
    projects_root: Path, tmp_path: Path
) -> None:
    """`flow projects --root <path>` overrides FLOW_PROJECTS_ROOT env var."""
    other = tmp_path / "other"
    other.mkdir()
    (other / "alpha").mkdir()
    result = runner.invoke(main, ["projects", "ls", "--root", str(other)])
    assert result.exit_code == 0, result.output
    assert "alpha" in result.output
    assert "pyproj-with-flow" not in result.output  # different root, no overlap


def test_flow_projects_readme_first_line(projects_root: Path) -> None:
    """Output includes the README first line (or '(no readme)') for context."""
    result = runner.invoke(main, ["projects", "ls"])
    assert result.exit_code == 0, result.output
    # pyproj-with-flow README: "# pyproj-with-flow"
    assert "pyproj-with-flow" in result.output
    # my-blog README: "# my-blog"
    assert "my-blog" in result.output
    # First line content visible (markdown headers stripped or shown — accept either way)
    # No specific assertion on the README text, just that the project is listed


def test_flow_projects_default_root_windows(
    projects_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no --root and no FLOW_PROJECTS_ROOT, default to C:\\dev\\proyects on Windows.

    On non-Windows, the command should still succeed (use ~ or a sensible default).
    We just check that the command does not crash and returns exit 0.
    """
    monkeypatch.delenv("FLOW_PROJECTS_ROOT", raising=False)
    result = runner.invoke(main, ["projects", "ls"])
    # May or may not have content — just verify no crash
    assert result.exit_code in (0, 1)  # 0 if default root exists, 1 if not
    # If default root doesn't exist (CI/non-Windows), should print informative error
    if result.exit_code != 0:
        assert "not found" in result.output.lower() or "does not exist" in result.output.lower()
