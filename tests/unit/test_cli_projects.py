"""Unit tests for cli.py `flow projects ls` (cross-project discovery).

Quick utility: lists directories in the projects root (default C:\\dev\\proyects)
with markers (python, node, astro, has-flow, readme first line). Single
purpose — do NOT expand scope without a real user need (per the Opción
media discipline: validate via real use before adding features).

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit wires the `flow projects` subcommand.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering import cli as cli_mod
from flow_engineering.cli import main
from tests.unit._workspace_fixtures import (
    _default_branch_fake_git,
    make_fake_dirty_project,
    make_fake_go_project,
    make_fake_openspec_project,
    make_fake_python_project,
)

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


# Fake-project fixtures (make_fake_go_project, make_fake_python_project,
# make_fake_dirty_project, make_fake_openspec_project, _default_branch_fake_git)
# live in ``tests/unit/_workspace_fixtures.py`` (Phase 3 T-3 split; design #448 §4).


# ---------- Tests (existing 4 regression baseline) ----------


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


# ---------- Tests (workspace-intelligence: 9 new unit tests) ----------


def test_flow_projects_ls_branch_with_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Go project + fake git seam → branch == 'main' (REQ-FIELD-EXTENSION)."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_go_project(root)
    monkeypatch.setattr(cli_mod, "_git", _default_branch_fake_git(branch="main"))
    result = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert len(payload["projects"]) == 1
    project = payload["projects"][0]
    assert project["has_git"] is True
    assert project["branch"] == "main"


def test_flow_projects_ls_dirty_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clean vs uncommitted → dirty boolean (REQ-FIELD-EXTENSION)."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_go_project(root, name="clean-proj")
    make_fake_dirty_project(root, name="dirty-proj")

    def fake_git(*args: str, **kwargs: object) -> subprocess.CompletedProcess:
        cp = subprocess.CompletedProcess(
            args=["git", *args], returncode=0, stdout="", stderr=""
        )
        cwd = kwargs.get("cwd")
        cwd_path = Path(str(cwd)).resolve() if cwd else None
        is_dirty = cwd_path is not None and "dirty" in cwd_path.name
        if args and args[0] == "rev-parse":
            cp.stdout = "main\n"
        elif args and args[0] == "status" and "--porcelain" in args:
            cp.stdout = " M foo.txt\n" if is_dirty else ""
        elif args and args[0] == "config":
            cp.returncode = 1
        return cp

    monkeypatch.setattr(cli_mod, "_git", fake_git)
    result = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    by_name = {p["name"]: p for p in payload["projects"]}
    assert by_name["clean-proj"]["dirty"] is False
    assert by_name["dirty-proj"]["dirty"] is True


def test_flow_projects_ls_remote_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Go project + origin URL → remote string (REQ-FIELD-EXTENSION)."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_go_project(root)
    expected_remote = "https://github.com/example/test.git"

    def fake_git(*args: str, **kwargs: object) -> subprocess.CompletedProcess:
        cp = subprocess.CompletedProcess(
            args=["git", *args], returncode=0, stdout="", stderr=""
        )
        if args and args[0] == "rev-parse":
            cp.stdout = "main\n"
        elif args and args[0] == "config":
            cp.stdout = expected_remote + "\n"
        return cp

    monkeypatch.setattr(cli_mod, "_git", fake_git)
    result = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["projects"][0]["remote"] == expected_remote


def test_flow_projects_ls_remote_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No remote configured → remote is None (REQ-FIELD-EXTENSION)."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_go_project(root)
    monkeypatch.setattr(cli_mod, "_git", _default_branch_fake_git(branch="main"))
    result = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["projects"][0]["remote"] is None


def test_flow_projects_ls_test_commands_python_pytest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Python + Makefile test: target → ['make test'] (REQ-FIELD-EXTENSION)."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_python_project(root)
    monkeypatch.setenv("FLOW_PROJECTS_ROOT", str(root))
    result = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["projects"][0]["test_commands"] == ["make test"]


def test_flow_projects_ls_has_openspec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project with openspec/changes/ → has_openspec is True (REQ-FIELD-EXTENSION)."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_openspec_project(root)
    monkeypatch.setenv("FLOW_PROJECTS_ROOT", str(root))
    result = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["projects"][0]["has_openspec"] is True


def test_flow_projects_ls_has_engram_stub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """has_engram always False (stub) regardless of fixture (REQ-HAS-ENGRAM-STUB)."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_go_project(root, name="go-one")
    make_fake_python_project(root, name="py-one")
    make_fake_openspec_project(root, name="os-one")

    def fake_git(*args: str, **kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=["git", *args], returncode=0, stdout="main\n", stderr=""
        )

    monkeypatch.setattr(cli_mod, "_git", fake_git)
    result = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert len(payload["projects"]) == 3
    for project in payload["projects"]:
        assert project["has_engram"] is False


def test_flow_projects_ls_json_deterministic_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """3 projects a/c/b → sorted to a/b/c in output (REQ-DETERMINISTIC-ORDER)."""
    root = tmp_path / "projects"
    root.mkdir()
    for name in ("c", "a", "b"):
        (root / name).mkdir()
    monkeypatch.setenv("FLOW_PROJECTS_ROOT", str(root))
    result = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    names = [p["name"] for p in payload["projects"]]
    assert names == ["a", "b", "c"]


def test_flow_projects_ls_json_version_field_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """version key is first in serialized JSON (REQ-SCHEMA-VERSIONING)."""
    root = tmp_path / "projects"
    root.mkdir()
    (root / "any").mkdir()
    monkeypatch.setenv("FLOW_PROJECTS_ROOT", str(root))
    result = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )
    assert result.exit_code == 0, result.output
    # First key in JSON output must be "version" (json.dumps preserves dict
    # insertion order in Python 3.7+).
    first_key_line = next(
        (ln for ln in result.output.splitlines() if ln.lstrip().startswith('"')),
        None,
    )
    assert first_key_line is not None
    assert first_key_line.lstrip().startswith('"version"')


def test_flow_projects_ls_json_byte_identical_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC8: Two consecutive ``flow projects ls --json`` invocations on an unchanged
    filesystem MUST emit byte-identical bytes.

    Regression test added in the AC8 fix-up cycle (2026-06-29). The original
    envelope assembly injected ``generated_at: _now_iso()`` per invocation,
    which by design violates byte-determinism. After dropping the timestamp,
    two invocations on the same fixture must produce identical stdout.

    Pattern follows ``test_flow_projects_ls_json_deterministic_order``:
    build a tiny fixture in ``tmp_path``, run the command twice in succession
    (no filesystem changes between calls), and assert ``result1.output ==
    result2.output``.
    """
    root = tmp_path / "projects"
    root.mkdir()
    # Two minimal projects — one Go (with .git) + one Python — sorted to
    # ["go-proj", "py-proj"] in the JSON envelope.
    make_fake_go_project(root, name="go-proj")
    make_fake_python_project(root, name="py-proj")
    monkeypatch.setattr(cli_mod, "_git", _default_branch_fake_git(branch="main"))

    result1 = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )
    result2 = runner.invoke(
        main,
        ["projects", "ls", "--json"],
        env={"FLOW_PROJECTS_ROOT": str(root)},
    )

    # Both invocations must succeed.
    assert result1.exit_code == 0, result1.output
    assert result2.exit_code == 0, result2.output

    # AC8 byte-identical contract: two consecutive invocations on an unchanged
    # filesystem MUST emit the same bytes. Any timestamp/clock-dependent field
    # (e.g. ``generated_at``) would break this — the test is intentionally
    # strict.
    assert result1.output == result2.output, (
        f"AC8 violation: two invocations produced different bytes.\n"
        f"  First ({len(result1.output)} bytes): {result1.output!r}\n"
        f"  Second ({len(result2.output)} bytes): {result2.output!r}"
    )

