import asyncio
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from flow_engineering import mcp_server


def test_detect_project_reports_stack() -> None:
    result = mcp_server.detect_project(str(Path.cwd()))
    assert result["stack"] == "Python"


@pytest.fixture
def document_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("FLOW_MCP_DOCUMENT_ROOTS", str(tmp_path))
    return tmp_path


def test_convert_document_returns_bounded_metadata(monkeypatch: pytest.MonkeyPatch, document_root: Path) -> None:
    (document_root / "notes.txt").write_text("source", encoding="utf-8")
    monkeypatch.setattr(mcp_server, "_convert_snapshot", lambda *_args: ("abcd", 6))
    result = mcp_server.convert_document(str(document_root), "notes.txt")
    assert (result["markdown"], result["metadata"]["truncated"]) == ("abcd", True)


@pytest.mark.parametrize(
    ("document_path", "message"),
    [
        ("../outside.txt", "relative path"),
        ("C:\\secret.txt", "relative path"),
        ("\\\\host\\share\\a.txt", "relative path"),
        ("https://example.com/a.pdf", "URLs are not supported"),
        ("file:///C:/secret.txt", "URLs are not supported"),
    ],
)
def test_convert_document_rejects_escaping_paths(document_root: Path, document_path: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        mcp_server.convert_document(str(document_root), document_path)


def test_convert_document_enforces_server_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    approved, rejected = tmp_path / "approved", tmp_path / "rejected"
    approved.mkdir()
    rejected.mkdir()
    (rejected / "notes.txt").write_text("secret", encoding="utf-8")
    monkeypatch.setenv("FLOW_MCP_DOCUMENT_ROOTS", str(approved))
    with pytest.raises(ValueError, match="approved document root"):
        mcp_server.convert_document(str(rejected), "notes.txt")


def test_convert_document_rejects_symlink(document_root: Path) -> None:
    source, link = document_root / "source", document_root / "linked"
    source.mkdir()
    (source / "secret.txt").write_text("secret", encoding="utf-8")
    try:
        link.symlink_to(source, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="symlink or reparse point"):
        mcp_server.convert_document(str(document_root), "linked/secret.txt")


@pytest.mark.parametrize(
    ("name", "kind", "message"),
    [
        ("program.exe", "bytes", "unsupported document extension"),
        ("folder.txt", "directory", "regular file"),
        ("large.txt", "large", "exceeds 4 byte"),
    ],
)
def test_convert_document_rejects_invalid_inputs(
    monkeypatch: pytest.MonkeyPatch, document_root: Path, name: str, kind: str, message: str
) -> None:
    target = document_root / name
    target.mkdir() if kind == "directory" else target.write_bytes(b"12345")
    if kind == "large":
        monkeypatch.setattr(mcp_server, "_MAX_DOCUMENT_BYTES", 4)
    with pytest.raises(ValueError, match=message):
        mcp_server.convert_document(str(document_root), name)


def test_convert_document_rejects_unsafe_or_excessive_archives(monkeypatch: pytest.MonkeyPatch, document_root: Path) -> None:
    document = document_root / "unsafe.docx"
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("../escape.xml", "xx")
    with pytest.raises(ValueError, match="unsafe member"):
        mcp_server.convert_document(str(document_root), document.name)
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("safe.xml", "xx")
    monkeypatch.setattr(mcp_server, "_MAX_ARCHIVE_MEMBERS", 0)
    with pytest.raises(ValueError, match="member limit"):
        mcp_server.convert_document(str(document_root), document.name)
    monkeypatch.setattr(mcp_server, "_MAX_ARCHIVE_MEMBERS", 1)
    monkeypatch.setattr(mcp_server, "_MAX_ARCHIVE_UNCOMPRESSED_BYTES", 1)
    with pytest.raises(ValueError, match="uncompressed byte limit"):
        mcp_server.convert_document(str(document_root), document.name)


@pytest.mark.parametrize(("limit", "message"), [(1, "uncompressed byte limit"), (10, "ZIP content requires")])
def test_convert_document_checks_renamed_zip(monkeypatch: pytest.MonkeyPatch, document_root: Path, limit: int, message: str) -> None:
    monkeypatch.setattr(mcp_server, "_MAX_ARCHIVE_UNCOMPRESSED_BYTES", limit)
    with zipfile.ZipFile(document_root / "bomb.txt", "w") as archive:
        archive.writestr("safe.xml", "xx")
    with pytest.raises(ValueError, match=message):
        mcp_server.convert_document(str(document_root), "bomb.txt")


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("fake.pdf", b"plain text", "valid PDF"),
        ("fake.txt", b"%PDF-1.7\n", "PDF content requires .pdf"),
        ("fake.docx", b"plain text", "valid ZIP"),
        ("prefixed.txt", b"x" * (1024 * 1024 + 4096) + b"PK\x03\x04", "ZIP signature at a nonzero offset"),
        ("prefixed.txt", b"x" * (1024 * 1024 + 4096) + b"%PDF-1.7\n", "PDF signature at a nonzero offset"),
    ],
    ids=lambda value: "payload" if isinstance(value, bytes) else None,
)
def test_convert_document_rejects_mismatched_magic(document_root: Path, name: str, content: bytes, message: str) -> None:
    (document_root / name).write_bytes(content)
    with pytest.raises(ValueError, match=message):
        mcp_server.convert_document(str(document_root), name)


def test_open_handle_rejects_path_outside_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside.txt"
    root.mkdir()
    outside.write_text("secret", encoding="utf-8")
    monkeypatch.setattr(mcp_server, "_opened_file_path", lambda _descriptor: outside)
    with outside.open("rb") as handle, pytest.raises(ValueError, match="outside project root"):
        mcp_server._assert_open_handle_within_root(handle.fileno(), root)


@pytest.mark.parametrize("survives_kill", [False, True])
def test_conversion_timeout_kills_stubborn_child(monkeypatch: pytest.MonkeyPatch, survives_kill: bool) -> None:
    receive, send, process, context = Mock(), Mock(), Mock(), Mock()
    receive.poll.return_value = False
    process.is_alive.side_effect = [True, True, survives_kill]
    context.Pipe.return_value = receive, send
    context.Process.return_value = process
    monkeypatch.setattr(mcp_server.multiprocessing, "get_context", lambda _: context)
    error, message = (RuntimeError, "would not stop") if survives_kill else (TimeoutError, "timed out")
    with pytest.raises(error, match=message):
        mcp_server._convert_snapshot(b"source", ".txt")
    process.terminate.assert_called_once()
    process.kill.assert_called_once()
    assert process.join.call_count == 2

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
    assert {"convert_document", "detect_project", "get_project_context", "summarize_project_health"} <= names
