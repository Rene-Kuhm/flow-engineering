"""Render helpers for the workspace health v1 envelope (text + JSON).

Library-first per Constitution Article I. Owns Rich imports so
``src/flow_engineering/health.py`` stays SRP-clean (no Rich at module
top). WU3.5 ships the text renderer; WU3.6 adds the JSON renderer.
"""

from __future__ import annotations

import json
from io import StringIO
from typing import Literal

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

_OVERFLOW_FOLD: Literal["fold", "crop", "ellipsis", "ignore"] = "fold"
_OVERFLOW_CROP: Literal["fold", "crop", "ellipsis", "ignore"] = "crop"
_HEALTH_PATH_TRUNCATE_LEN: int = 60
_VERDICT_STYLE: dict[str, str] = {"HEALTHY": "green", "NEEDS-ATTENTION": "yellow", "CRITICAL": "red"}


def _truncate_path(path: str, max_len: int = _HEALTH_PATH_TRUNCATE_LEN) -> str:
    if len(path) <= max_len:
        return path
    return "..." + path[-(max_len - 3) :]


def _format_header(root: str, totals: dict[str, object]) -> str:
    return (
        f"workspace: {root}\n"
        f"healthy={totals.get('healthy', 0)} attention={totals.get('attention', 0)} critical={totals.get('critical', 0)}"
    )


def _build_table(projects: list[dict[str, object]]) -> Table:
    table = Table(title="Workspace health", show_lines=False, header_style="bold")
    for header, min_w, max_w, overflow in (
        ("project", 12, 30, _OVERFLOW_FOLD),
        ("path", 30, 60, _OVERFLOW_FOLD),
        ("verdict", 12, 18, _OVERFLOW_CROP),
        ("triggers", 8, 24, _OVERFLOW_FOLD),
    ):
        table.add_column(header, min_width=min_w, max_width=max_w, overflow=overflow)
    for project in projects:
        verdict = str(project.get("verdict", ""))
        triggers = project.get("triggers", [])
        trigger_text = ", ".join(str(t) for t in triggers) if isinstance(triggers, list) else ""
        table.add_row(
            str(project.get("name", "")),
            _truncate_path(str(project.get("path", ""))),
            verdict,
            trigger_text,
            style=_VERDICT_STYLE.get(verdict),
        )
    return table


def _render_into_console(envelope: dict[str, object], projects: list[dict[str, object]], console: Console) -> None:
    raw_totals = envelope.get("totals", {})
    totals_dict: dict[str, object] = raw_totals if isinstance(raw_totals, dict) else {}
    header = _format_header(str(envelope.get("root", "")), totals_dict)
    console.print(Panel(Group(header, _build_table(projects)), title="Workspace health"))


def render_workspace_health_text(envelope: dict[str, object], *, console: Console | None = None) -> str:
    """Render a workspace-health envelope as a Rich Panel + Table.

    Empty envelope returns ``"(no projects to report)"``. If ``console``
    is None, a default 120-width StringIO Console is created. Otherwise
    the caller owns the Console and we return the captured output.
    """
    raw_projects = envelope.get("projects", [])
    projects = raw_projects if isinstance(raw_projects, list) else []
    if not projects:
        return "(no projects to report)"
    if console is None:
        buffer = StringIO()
        _render_into_console(envelope, projects, Console(file=buffer, width=120))
        return buffer.getvalue()
    _render_into_console(envelope, projects, console)
    file_obj = getattr(console, "file", None)
    if file_obj is not None and hasattr(file_obj, "getvalue"):
        return str(file_obj.getvalue())
    return ""

def render_workspace_health_json(envelope: dict[str, object]) -> str:
    return json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2)
