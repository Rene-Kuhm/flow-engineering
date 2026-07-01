"""Tests for `flow workspace status`."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from flow_engineering import cli as cli_mod
from flow_engineering.cli import main
from tests.unit._workspace_fixtures import (
    make_go_project,
    make_node_project,
    make_python_project,
    make_unknown_project,
)

runner = CliRunner()


def _fake_git(*args: str, **kwargs: object) -> subprocess.CompletedProcess:
    cwd = Path(str(kwargs.get("cwd", "")))
    stdout = ""
    if args and args[0] == "rev-parse":
        stdout = "main\n"
    elif args and args[0] == "status":
        stdout = " M file.txt\n" if "dirty" in cwd.name else ""
    elif args and args[0] == "config":
        stdout = "https://example.test/repo.git\n"
    return subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout=stdout, stderr="")


def _payload(root: Path, monkeypatch) -> dict:
    monkeypatch.setattr(cli_mod, "_git", _fake_git)
    result = runner.invoke(main, ["workspace", "status", "--root", str(root), "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_workspace_status_json_envelope_and_r4(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    make_python_project(root, "a-clean", openspec=True)
    make_python_project(root, "b-no-openspec", openspec=False)

    payload = _payload(root, monkeypatch)

    assert list(payload.keys()) == ["version", "root", "totals", "projects", "needs_attention"]
    assert payload["version"] == "1"
    assert set(payload["totals"]) == {
        "projects",
        "dirty",
        "no_git",
        "no_tests",
        "has_openspec",
        "has_graphify",
        "has_engram",
        "needs_attention",
    }
    by_name = {item["name"]: item for item in payload["needs_attention"]}
    assert by_name["b-no-openspec"]["reasons"] == [
        "R4: SDD-adjacent stack missing openspec"
    ]


def test_workspace_status_r1_dirty_project(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    make_go_project(root, "dirty-go")

    payload = _payload(root, monkeypatch)

    reasons = payload["needs_attention"][0]["reasons"]
    assert "R1: uncommitted work" in reasons


def test_workspace_status_r2_no_git_project(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    make_python_project(root, "no-git", git=False)

    payload = _payload(root, monkeypatch)

    reasons = payload["needs_attention"][0]["reasons"]
    assert "R2: no version control" in reasons


def test_workspace_status_r3_no_tests_project(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    make_unknown_project(root, "unknown-no-tests", git=True)

    payload = _payload(root, monkeypatch)

    reasons = payload["needs_attention"][0]["reasons"]
    assert "R3: no tests detected" in reasons


def test_workspace_status_r5_graphify_is_informational_only(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    make_node_project(root, "node-clean", tests=True)

    payload = _payload(root, monkeypatch)

    assert payload["totals"]["has_graphify"] == 0
    assert payload["needs_attention"] == []


def test_workspace_status_text_output(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    make_go_project(root, "dirty-go")
    make_unknown_project(root, "loose-folder", git=False)
    monkeypatch.setattr(cli_mod, "_git", _fake_git)

    result = runner.invoke(main, ["workspace", "status", "--root", str(root)])

    assert result.exit_code == 0, result.output
    assert "WORKSPACE STATUS" in result.output
    assert "[DIRTY]" in result.output
    assert "[NO-GIT]" in result.output
    assert "[NO TESTS]" in result.output
    assert "SUMMARY" in result.output


def test_workspace_status_subdir_scan_excludes_dot_prefix_dirs(
    tmp_path: Path, monkeypatch
) -> None:
    """``flow workspace status --json`` MUST exclude dot-prefix entries.

    View-only filter per REQ-WORKSPACE-PROJECT-IDENTITY: tooling/config
    directories (``.atl``, ``.opencode``, ``.venv``) are not user projects.
    3 regular + 5 dot-prefix subdirs in the root → 3 projects reported.
    """
    root = tmp_path / "projects"
    root.mkdir()
    make_python_project(root, "alpha")
    make_python_project(root, "beta")
    make_python_project(root, "gamma")
    for dot_name in (".atl", ".opencode", ".venv", ".pytest_cache", ".github"):
        (root / dot_name).mkdir()

    payload = _payload(root, monkeypatch)

    by_name = {p["name"] for p in payload["projects"]}
    assert by_name == {"alpha", "beta", "gamma"}
    assert payload["totals"]["projects"] == 3
    for excluded in (".atl", ".opencode", ".venv", ".pytest_cache", ".github"):
        assert excluded not in by_name


def test_workspace_status_empty_root_text_and_json(tmp_path: Path) -> None:
    root = tmp_path / "projects"
    root.mkdir()

    text = runner.invoke(main, ["workspace", "status", "--root", str(root)])
    js = runner.invoke(main, ["workspace", "status", "--root", str(root), "--json"])

    assert text.exit_code == 0, text.output
    assert "(no projects to report)" in text.output
    assert js.exit_code == 0, js.output
    payload = json.loads(js.output)
    assert payload["totals"]["projects"] == 0
    assert payload["totals"]["needs_attention"] == 0


def test_iter_project_subdirs_helper_excludes_dot_prefix(tmp_path: Path) -> None:
    """``_iter_project_subdirs`` MUST drop dot-prefix entries and return sorted output.

    Anchors REQ-WORKSPACE-PROJECT-IDENTITY at the helper level: callers
    that bypass the public ``workspace_status`` / ``projects_ls`` paths
    must still see the same filtered set.
    """
    from flow_engineering.cli import _iter_project_subdirs

    (tmp_path / "alpha").mkdir()
    (tmp_path / "beta").mkdir()
    (tmp_path / ".atl").mkdir()
    (tmp_path / ".opencode").mkdir()
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".github").mkdir()
    (tmp_path / "stray.txt").write_text("not a dir", encoding="utf-8")

    result = _iter_project_subdirs(tmp_path)

    assert [p.name for p in result] == ["alpha", "beta"]


def test_iter_project_subdirs_helper_empty_when_only_dot_dirs(tmp_path: Path) -> None:
    """``_iter_project_subdirs`` returns ``[]`` when only dot-prefix dirs exist."""
    from flow_engineering.cli import _iter_project_subdirs

    for dot_name in (".atl", ".opencode", ".venv"):
        (tmp_path / dot_name).mkdir()

    assert _iter_project_subdirs(tmp_path) == []


def test_workspace_status_json_byte_identical(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    make_python_project(root, "py")
    monkeypatch.setattr(cli_mod, "_git", _fake_git)

    one = runner.invoke(main, ["workspace", "status", "--root", str(root), "--json"])
    two = runner.invoke(main, ["workspace", "status", "--root", str(root), "--json"])

    assert one.exit_code == 0, one.output
    assert two.exit_code == 0, two.output
    assert one.output == two.output


def test_workspace_status_projects_verbatim_from_detector(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    make_go_project(root, "go")
    monkeypatch.setattr(cli_mod, "_git", _fake_git)

    payload = _payload(root, monkeypatch)

    project = payload["projects"][0]
    assert project["name"] == "go"
    assert project["stack"] == "Go"
    assert project["test_commands"] == ["go test ./..."]


def test_workspace_status_does_not_change_projects_ls_schema(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "projects"
    root.mkdir()
    make_python_project(root, "py")
    monkeypatch.setattr(cli_mod, "_git", _fake_git)

    result = runner.invoke(main, ["projects", "ls", "--root", str(root), "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert list(payload.keys()) == ["version", "root", "projects"]
    assert "totals" not in payload
    assert "needs_attention" not in payload

