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

