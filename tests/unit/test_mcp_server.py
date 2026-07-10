import asyncio
from pathlib import Path

import pytest

from flow_engineering import mcp_server


def test_detect_project_reports_stack() -> None:
    result = mcp_server.detect_project(str(Path.cwd()))
    assert result["stack"] == "Python"


def test_context_is_allowlisted_and_bounded(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("allowed", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("must not be read", encoding="utf-8")
    result = mcp_server.get_project_context(str(tmp_path))
    assert set(result["files"]) <= set(mcp_server._ALLOWED_CONTEXT_FILES)
    assert "secret.txt" not in result["files"]


def test_context_rejects_allowlisted_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-agents.md"
    outside.write_text("secret", encoding="utf-8")
    link = tmp_path / "AGENTS.md"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="escapes project path"):
        mcp_server.get_project_context(str(tmp_path))


def test_project_root_rejects_symlink(tmp_path: Path) -> None:
    real_root = tmp_path / "real-root"
    real_root.mkdir()
    linked_root = tmp_path / "linked-root"
    try:
        linked_root.symlink_to(real_root, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="must not be a symlink"):
        mcp_server.detect_project(str(linked_root))


def test_context_rejects_invalid_focus(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported focus"):
        mcp_server.get_project_context(str(tmp_path), focus="secret")


@pytest.mark.parametrize("focus", [[], {}, 1, None])
def test_context_rejects_non_string_focus(tmp_path: Path, focus: object) -> None:
    with pytest.raises(ValueError, match="unsupported focus"):
        mcp_server.get_project_context(str(tmp_path), focus=focus)  # type: ignore[arg-type]


def test_context_focus_selects_project_files(tmp_path: Path) -> None:
    for name in mcp_server._ALLOWED_CONTEXT_FILES:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(name, encoding="utf-8")
    result = mcp_server.get_project_context(str(tmp_path), focus="project")
    assert set(result["files"]) == {
        "AGENTS.md",
        "docs/operating-manual.md",
        "docs/stack-tooling-policy.md",
        "docs/glossary.md",
    }


def test_context_focus_selects_governance_files(tmp_path: Path) -> None:
    for name in mcp_server._ALLOWED_CONTEXT_FILES:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(name, encoding="utf-8")
    result = mcp_server.get_project_context(str(tmp_path), focus="governance")
    assert set(result["files"]) == {
        "docs/change-governance.md",
        "docs/engineering-quality-gates.md",
    }


def test_context_focus_all_selects_full_allowlist(tmp_path: Path) -> None:
    for name in mcp_server._ALLOWED_CONTEXT_FILES:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(name, encoding="utf-8")
    result = mcp_server.get_project_context(str(tmp_path), focus="all")
    assert set(result["files"]) == {
        "AGENTS.md",
        "docs/operating-manual.md",
        "docs/stack-tooling-policy.md",
        "docs/glossary.md",
        "docs/change-governance.md",
        "docs/engineering-quality-gates.md",
    }


def test_context_enforces_per_file_and_total_bounds(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("a" * (mcp_server._MAX_FILE_CHARS + 1), encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/operating-manual.md").write_text(
        "b" * mcp_server._MAX_CONTEXT_CHARS, encoding="utf-8"
    )
    result = mcp_server.get_project_context(str(tmp_path), focus="all")
    assert len(result["files"]["AGENTS.md"]) == mcp_server._MAX_FILE_CHARS
    assert sum(map(len, result["files"].values())) <= mcp_server._MAX_CONTEXT_CHARS


def test_detect_project_omits_credential_bearing_remote(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        mcp_server,
        "_detect_project_markers",
        lambda _root: {"stack": "Python", "remote": "https://user:secret@example.com/repo.git"},
    )
    result = mcp_server.detect_project(str(tmp_path))
    assert "remote" not in result
    assert "secret" not in str(result)


def test_detect_project_returns_closed_bounded_dto(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        mcp_server,
        "_detect_project_markers",
        lambda _root: {
            "name": "n" * (mcp_server._MAX_DETECTION_STRING_CHARS + 1),
            "path": "p" * (mcp_server._MAX_DETECTION_STRING_CHARS + 1),
            "stack": "Python",
            "dirty_files": ["x" * 400 for _ in range(100)],
            "test_commands": ["pytest", {"secret": "value"}],
            "remote": "https://user:secret@example.com/repo.git",
            "unexpected": "must not escape",
        },
    )

    result = mcp_server.detect_project(str(tmp_path))

    assert set(result) == {
        "name",
        "path",
        "has_git",
        "branch",
        "dirty",
        "dirty_files",
        "stack",
        "type",
        "test_commands",
        "has_openspec",
        "has_graphify",
        "has_engram",
        "has_flow",
        "readme_first_line",
        "has_readme",
        "has_pytest_config",
    }
    assert len(result["name"]) == mcp_server._MAX_DETECTION_STRING_CHARS
    assert len(result["dirty_files"]) == mcp_server._MAX_DETECTION_LIST_ITEMS
    assert all(
        len(item) <= mcp_server._MAX_DETECTION_STRING_CHARS for item in result["dirty_files"]
    )
    assert result["test_commands"] == ["pytest"]


def test_health_summary_returns_bounded_closed_dto(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(mcp_server, "_detect_project_markers", lambda _root: {})
    monkeypatch.setattr(mcp_server, "_detect_committed_tooling_dirs", lambda _root: [])
    monkeypatch.setattr(
        mcp_server,
        "_summarize_project_health",
        lambda _markers, tooling_hits: {
            "name": "n" * 500,
            "path": "p" * 500,
            "stack": "Python",
            "verdict": "v" * 500,
            "triggers": ["R6"] * 100,
            "recommendations": ["r" * 500] * 100,
            "suppressed": ["R7"],
            "unexpected": "must not escape",
        },
    )

    result = mcp_server.summarize_project_health(str(tmp_path))

    assert set(result) == {
        "name",
        "path",
        "stack",
        "verdict",
        "triggers",
        "recommendations",
        "suppressed",
    }
    assert len(result["name"]) == mcp_server._MAX_DETECTION_STRING_CHARS
    assert len(result["recommendations"]) == mcp_server._MAX_DETECTION_LIST_ITEMS
    assert all(
        len(item) <= mcp_server._MAX_DETECTION_STRING_CHARS for item in result["recommendations"]
    )


def test_missing_path_is_clear() -> None:
    with pytest.raises(ValueError, match="does not exist"):
        mcp_server.detect_project("does-not-exist")


def test_health_summary_uses_core_api(tmp_path: Path) -> None:
    result = mcp_server.summarize_project_health(str(tmp_path))
    assert "verdict" in result
    assert result["path"] == str(tmp_path.resolve())


def test_mcp_registration_when_optional_dependency_is_available() -> None:
    if mcp_server.mcp is None:
        pytest.skip("FastMCP optional extra is not installed")
    tools = asyncio.run(mcp_server.mcp.list_tools())
    names = {tool.name for tool in tools}
    assert {"detect_project", "get_project_context", "summarize_project_health"} <= names
