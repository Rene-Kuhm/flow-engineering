"""Optional stdio MCP adapter for read-only project intelligence."""

from __future__ import annotations

import io
import multiprocessing
import os
import stat
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import urlsplit

from flow_engineering.cli import _detect_project_markers
from flow_engineering.health import (
    _detect_committed_tooling_dirs,
)
from flow_engineering.health import (
    summarize_project_health as _summarize_project_health,
)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised by minimal installations
    FastMCP = None  # type: ignore[assignment,misc]

try:
    from markitdown import MarkItDown as _MarkItDown
    from markitdown import StreamInfo as _StreamInfo
except ImportError:  # pragma: no cover - exercised by minimal installations
    _MarkItDown = None  # type: ignore[assignment,misc]
    _StreamInfo = None  # type: ignore[assignment,misc]


_ALLOWED_CONTEXT_FILES = (
    "AGENTS.md",
    "docs/operating-manual.md",
    "docs/stack-tooling-policy.md",
    "docs/glossary.md",
    "docs/change-governance.md",
    "docs/engineering-quality-gates.md",
)
_PROJECT_CONTEXT_FILES = _ALLOWED_CONTEXT_FILES[:4]
_GOVERNANCE_CONTEXT_FILES = _ALLOWED_CONTEXT_FILES[4:]
_CONTEXT_FILES_BY_FOCUS = {
    "project": _PROJECT_CONTEXT_FILES,
    "governance": _GOVERNANCE_CONTEXT_FILES,
    "all": _ALLOWED_CONTEXT_FILES,
}
_MAX_FILE_CHARS = 12_000
_MAX_CONTEXT_CHARS = 36_000
_MAX_DETECTION_STRING_CHARS = 256
_MAX_DETECTION_LIST_ITEMS = 32
_MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
_MAX_ARCHIVE_MEMBERS = 500
_MAX_ARCHIVE_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
_MAX_MARKDOWN_CHARS = 50_000
_CONVERSION_TIMEOUT_SECONDS = 20.0
_PROCESS_JOIN_TIMEOUT_SECONDS = 1.0
_SERVER_CHECKOUT_ROOT = Path(__file__).resolve().parents[2]
_OFFICE_ARCHIVE_EXTENSIONS = frozenset({".docx", ".pptx", ".xlsx"})
_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_ALLOWED_DOCUMENT_EXTENSIONS = frozenset([".csv", ".docx", ".htm", ".html", ".json", ".md", ".pdf", ".pptx", ".txt", ".xlsx", ".xml"])
_PROJECT_DETECTION_FIELDS = (
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
)
_HEALTH_SUMMARY_FIELDS = (
    "name",
    "path",
    "stack",
    "verdict",
    "triggers",
    "recommendations",
    "suppressed",
)


def _bounded_string(value: Any, default: str = "") -> str:
    if not isinstance(value, str):
        return default
    return value[:_MAX_DETECTION_STRING_CHARS]


def _bounded_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    return value[:_MAX_DETECTION_STRING_CHARS]


def _bounded_bool(value: Any, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def _bounded_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [
        item[:_MAX_DETECTION_STRING_CHARS]
        for item in value[:_MAX_DETECTION_LIST_ITEMS]
        if isinstance(item, str)
    ]


def _safe_project_detection(markers: dict[str, Any]) -> dict[str, Any]:
    """Return the closed, bounded DTO exposed by the detection tool."""
    return {
        "name": _bounded_string(markers.get("name")),
        "path": _bounded_string(markers.get("path")),
        "has_git": _bounded_bool(markers.get("has_git")),
        "branch": _bounded_optional_string(markers.get("branch")),
        "dirty": _bounded_bool(markers.get("dirty")),
        "dirty_files": _bounded_string_list(markers.get("dirty_files")),
        "stack": _bounded_string(markers.get("stack"), "Unknown"),
        "type": _bounded_string(markers.get("type")),
        "test_commands": _bounded_string_list(markers.get("test_commands")),
        "has_openspec": _bounded_bool(markers.get("has_openspec")),
        "has_graphify": _bounded_bool(markers.get("has_graphify")),
        "has_engram": _bounded_bool(markers.get("has_engram")),
        "has_flow": _bounded_string(markers.get("has_flow")),
        "readme_first_line": _bounded_string(markers.get("readme_first_line")),
        "has_readme": _bounded_bool(markers.get("has_readme")),
        "has_pytest_config": _bounded_bool(markers.get("has_pytest_config")),
    }


def _safe_health_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Return the closed, bounded DTO exposed by the health tool."""
    return {
        "name": _bounded_string(summary.get("name")),
        "path": _bounded_string(summary.get("path")),
        "stack": _bounded_string(summary.get("stack"), "Unknown"),
        "verdict": _bounded_string(summary.get("verdict")),
        "triggers": _bounded_string_list(summary.get("triggers")),
        "recommendations": _bounded_string_list(summary.get("recommendations")),
        "suppressed": _bounded_string_list(summary.get("suppressed")),
    }


def _project_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser().absolute()
    if any(part.is_symlink() for part in (candidate, *candidate.parents)):
        raise ValueError(f"project path must not be a symlink: {candidate}")
    resolved = candidate.resolve()
    if not resolved.exists():
        raise ValueError(f"project path does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"project path is not a directory: {resolved}")
    return resolved


def detect_project(path: str) -> dict[str, Any]:
    """Detect the project stack and repository markers at ``path``."""
    markers = _detect_project_markers(_project_path(path))
    return _safe_project_detection(markers)


def get_project_context(path: str, focus: str = "project") -> dict[str, Any]:
    """Return bounded context from the fixed, safe root-file allowlist."""
    if not isinstance(focus, str) or focus not in _CONTEXT_FILES_BY_FOCUS:
        raise ValueError(f"unsupported focus: {focus!r}")
    root = _project_path(path)
    selected = _CONTEXT_FILES_BY_FOCUS[focus]
    files: dict[str, str] = {}
    remaining = _MAX_CONTEXT_CHARS
    for name in selected:
        target = root / name
        if not target.is_file():
            continue
        resolved_target = target.resolve()
        if not resolved_target.is_relative_to(root):
            raise ValueError(f"context file escapes project path: {name}")
        limit = min(_MAX_FILE_CHARS, remaining)
        if limit <= 0:
            break
        with resolved_target.open("r", encoding="utf-8", errors="replace") as handle:
            content = handle.read(limit)
        files[name] = content
        remaining -= len(content)
    return {"path": str(root), "focus": focus, "files": files}


def summarize_project_health(path: str) -> dict[str, Any]:
    """Build the existing deterministic health summary for one project."""
    root = _project_path(path)
    markers = _safe_project_detection(_detect_project_markers(root))
    tooling_hits = _bounded_string_list(_detect_committed_tooling_dirs(root))
    summary = _summarize_project_health(markers, tooling_hits=tooling_hits)
    return _safe_health_summary(summary)


def _path_is_link_or_reparse(path: Path) -> bool:
    details = path.lstat()
    attributes = getattr(details, "st_file_attributes", 0)
    return stat.S_ISLNK(details.st_mode) or bool(attributes & 0x400)


def _assert_plain_components(path: Path) -> None:
    for component in reversed((path, *path.parents)):
        if _path_is_link_or_reparse(component):
            raise ValueError(f"path contains a symlink or reparse point: {component}")


def _approved_document_roots() -> tuple[Path, ...]:
    configured = os.environ.get("FLOW_MCP_DOCUMENT_ROOTS")
    entries = configured.split(os.pathsep) if configured else [str(_SERVER_CHECKOUT_ROOT)]
    roots: list[Path] = []
    for entry in entries:
        candidate = Path(entry).expanduser()
        if not entry or not candidate.is_absolute():
            raise ValueError("FLOW_MCP_DOCUMENT_ROOTS must contain absolute paths")
        _assert_plain_components(candidate)
        resolved = candidate.resolve(strict=True)
        if not resolved.is_dir():
            raise ValueError(f"approved document root is not a directory: {resolved}")
        roots.append(resolved)
    return tuple(roots)


def _authorized_project_root(project_root: str) -> Path:
    candidate = Path(project_root).expanduser()
    if not candidate.is_absolute():
        raise ValueError("project_root must be an absolute approved document root")
    _assert_plain_components(candidate)
    root = candidate.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"project path is not a directory: {root}")
    if not any(root == allowed or root.is_relative_to(allowed) for allowed in _approved_document_roots()):
        raise ValueError("project_root is outside every approved document root")
    return root


def _validate_office_archive(snapshot: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(snapshot)) as archive:
            members = archive.infolist()
            if len(members) > _MAX_ARCHIVE_MEMBERS:
                raise ValueError("Office archive exceeds member limit")
            if sum(member.file_size for member in members) > _MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                raise ValueError("Office archive exceeds uncompressed byte limit")
            for member in members:
                posix = PurePosixPath(member.filename.replace("\\", "/"))
                windows = PureWindowsPath(member.filename)
                if (
                    member.flag_bits & 1
                    or "\x00" in member.filename
                    or posix.is_absolute()
                    or ".." in posix.parts
                    or windows.drive
                    or windows.root
                ):
                    raise ValueError("Office archive contains an unsafe member")
    except zipfile.BadZipFile as error:
        raise ValueError("Office document is not a valid ZIP archive") from error


def _validate_declared_format(snapshot: bytes, extension: str) -> None:
    probe = snapshot
    zip_offsets = [offset for magic in _ZIP_MAGICS if (offset := probe.find(magic)) >= 0]
    zip_offset = min(zip_offsets, default=-1)
    pdf_offset = probe.find(b"%PDF-")
    for label, offset in (("ZIP", zip_offset), ("PDF", pdf_offset)):
        if offset > 0:
            raise ValueError(f"{label} signature at a nonzero offset is not allowed")
    if zip_offset == 0:
        _validate_office_archive(snapshot)
        if extension not in _OFFICE_ARCHIVE_EXTENSIONS:
            raise ValueError("ZIP content requires a .docx, .pptx, or .xlsx extension")
    elif extension in _OFFICE_ARCHIVE_EXTENSIONS:
        raise ValueError("Office document is not a valid ZIP archive")
    if pdf_offset == 0 and extension != ".pdf":
        raise ValueError("PDF content requires .pdf extension")
    if extension == ".pdf" and pdf_offset != 0:
        raise ValueError("PDF document must have valid PDF magic")


def _opened_file_path(descriptor: int) -> Path:
    if os.name == "nt":
        import ctypes
        import msvcrt

        final_path: Any = ctypes.WinDLL("kernel32", use_last_error=True).GetFinalPathNameByHandleW
        final_path.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
        final_path.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32_768)
        length = final_path(msvcrt.get_osfhandle(descriptor), buffer, len(buffer), 0)
        if not 0 < length < len(buffer):
            raise ValueError("opened file path verification failed")
        value = "\\\\" + buffer.value[8:] if buffer.value.startswith("\\\\?\\UNC\\") else buffer.value
        return Path(value.removeprefix("\\\\?\\")).resolve(strict=True)
    try:
        target = os.readlink(f"/proc/self/fd/{descriptor}")
        return Path(target).resolve(strict=True)
    except OSError as error:
        raise ValueError("opened file path verification is unavailable") from error


def _assert_open_handle_within_root(descriptor: int, root: Path) -> None:
    if not _opened_file_path(descriptor).is_relative_to(root):
        raise ValueError("opened document is outside project root")


def _conversion_worker(connection: Any, snapshot: bytes, extension: str) -> None:
    try:
        if _MarkItDown is None or _StreamInfo is None:
            raise RuntimeError
        converted = _MarkItDown(enable_plugins=False).convert_stream(
            io.BytesIO(snapshot),
            stream_info=_StreamInfo(extension=extension, filename=f"document{extension}"),
        )
        markdown = converted.text_content
        connection.send((True, markdown[:_MAX_MARKDOWN_CHARS], len(markdown)))
    except Exception:
        connection.send((False, "", 0))
    finally:
        connection.close()


def _convert_snapshot(snapshot: bytes, extension: str) -> tuple[str, int]:
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_conversion_worker, args=(send, snapshot, extension))
    process.start()
    send.close()
    try:
        if not receive.poll(_CONVERSION_TIMEOUT_SECONDS):
            raise TimeoutError("document conversion timed out")
        success, markdown, original_chars = receive.recv()
        if success:
            return str(markdown), int(original_chars)
        raise RuntimeError("document conversion failed")
    except EOFError as error:
        raise RuntimeError("document conversion failed") from error
    finally:
        if process.is_alive():
            process.terminate()
        process.join(_PROCESS_JOIN_TIMEOUT_SECONDS)
        if process.is_alive():
            process.kill()
            process.join(_PROCESS_JOIN_TIMEOUT_SECONDS)
        alive = process.is_alive()
        receive.close()
        if alive:
            raise RuntimeError("document conversion process would not stop")


def convert_document(project_root: str, document_path: str) -> dict[str, Any]:
    """Convert one local project document to bounded Markdown."""
    windows_path = PureWindowsPath(document_path)
    posix_path = PurePosixPath(document_path)
    if not document_path or windows_path.drive or windows_path.root or posix_path.root:
        raise ValueError("document_path must be a relative path without traversal")
    if urlsplit(document_path).scheme:
        raise ValueError("document URLs are not supported")
    relative = Path(document_path)
    if ".." in posix_path.parts or ".." in windows_path.parts:
        raise ValueError("document_path must be a relative path without traversal")
    extension = relative.suffix.lower()
    if extension not in _ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValueError(f"unsupported document extension: {extension or '<none>'}")
    root = _authorized_project_root(project_root)
    target = root / relative
    try:
        _assert_plain_components(target)
        target = target.resolve(strict=True)
    except FileNotFoundError as error:
        raise ValueError("document must be a regular file") from error
    if not target.is_relative_to(root):
        raise ValueError("document_path must be a relative path without traversal")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(target, flags)
    except OSError as error:
        raise ValueError("document must be a regular file") from error
    with os.fdopen(descriptor, "rb") as stream:
        _assert_open_handle_within_root(stream.fileno(), root)
        details = os.fstat(stream.fileno())
        if not stat.S_ISREG(details.st_mode):
            raise ValueError("document must be a regular file")
        size_bytes = details.st_size
        if size_bytes > _MAX_DOCUMENT_BYTES:
            raise ValueError(f"document exceeds {_MAX_DOCUMENT_BYTES} byte limit")
        snapshot = stream.read(_MAX_DOCUMENT_BYTES + 1)
    if len(snapshot) > _MAX_DOCUMENT_BYTES:
        raise ValueError(f"document exceeds {_MAX_DOCUMENT_BYTES} byte limit")
    _validate_declared_format(snapshot, extension)
    if _MarkItDown is None or _StreamInfo is None:
        raise RuntimeError("MarkItDown is unavailable; install flow-engineering[mcp]")
    bounded, original_chars = _convert_snapshot(snapshot, extension)
    return {
        "markdown": bounded,
        "metadata": {
            "document_path": document_path,
            "extension": extension,
            "size_bytes": size_bytes,
            "markdown_chars": len(bounded),
            "original_markdown_chars": original_chars,
            "markdown_limit_chars": _MAX_MARKDOWN_CHARS,
            "truncated": len(bounded) < original_chars,
        },
    }


def _register_tools(server: Any) -> None:
    server.tool()(convert_document)
    server.tool()(detect_project)
    server.tool()(get_project_context)
    server.tool()(summarize_project_health)


mcp = FastMCP("flow-engineering") if FastMCP is not None else None
if mcp is not None:  # pragma: no branch - depends on optional extra
    _register_tools(mcp)


def main() -> None:
    """Run the optional FastMCP server over stdio."""
    if mcp is None:
        raise RuntimeError("FastMCP is unavailable; install flow-engineering[mcp]")
    mcp.run(transport="stdio")


__all__ = [
    "convert_document",
    "detect_project",
    "get_project_context",
    "summarize_project_health",
    "main",
    "mcp",
]
