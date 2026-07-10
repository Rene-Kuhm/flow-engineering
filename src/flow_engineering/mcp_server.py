"""Optional stdio MCP adapter for read-only project intelligence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
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


def _register_tools(server: Any) -> None:
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
    "detect_project",
    "get_project_context",
    "summarize_project_health",
    "main",
    "mcp",
]
