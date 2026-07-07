"""CLI entry point for flow-engineering."""

from __future__ import annotations

import contextlib
import csv as _csv
import io
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import click
from rich.console import Console

from flow_engineering import decision_drift, observability, workspace_hygiene
from flow_engineering import where as where_mod
from flow_engineering.auto_suggest_code_refs import FLOW_AUTO_SUGGEST_ENV
from flow_engineering.binding import (
    CODE_REFS_MARKER,
    CodeRef,
    extract_code_refs,
)
from flow_engineering.daemon import start_watch
from flow_engineering.drift_event_log import (
    DriftEvent,
    DriftEventLog,
    DriftEventLogLegacyFormatError,
)
from flow_engineering.engram_io import (
    EngramBackend,
    EngramClient,
    InMemoryBackend,
    iter_observations_for_change,
)
from flow_engineering.orchestrator import (
    apply_change,
    archive_change,
    verify_change,
)
from flow_engineering.project_detector import apply_tag as _apply_tag
from flow_engineering.registry import (
    ArchivedEntry,
    ProjectEntry,
    Registry,
    RegistryError,
    load_registry,
    save_registry_atomic,
)
from flow_engineering.scaffold import (
    load_change_yaml,
    render_new_project,
    scaffold_change,
)
from flow_engineering.snapshot_manager import (
    PruneNoFilterError,
    PruneSafetyGateError,
    RollbackConflictError,
    RollbackRefusedError,
    SnapshotDiff,
    SnapshotEnvelopeError,
    SnapshotManager,
    SnapshotMeta,
)
from flow_engineering.state import StateMachine


# Lazy submodule import (v1.3-cli-split, Slice 1). Keeps ``cli._shared``
# registered in ``sys.modules`` so subsequent submodule-scope decorators
# fire deterministically; ``_shared`` itself defines no Click decorators,
# but the lazy-import pattern is the v1.3-cli-split convention (see
# design §6) and is harmless here.
from . import _shared as _shared  # noqa: F401  (lazy; see design §6)
from ._shared import (
    _DEFAULT_PROJECTS_ROOT_WIN,
    _DEFAULT_PROJECTS_ROOT_NIX,
    _resolve_projects_root,
    _iter_project_subdirs,
    _read_pyproject_min_skill_versions,
    _enforce_min_skill_versions_or_exit,
)


@click.group()
@click.version_option(package_name="flow-engineering")
def main() -> None:
    """Flow Engineering -- orchestrator of the Agentic & Context-Driven closed loop."""


# Lazy submodule import (v1.3-cli-split, Slice 2). Keeps ``cli.workspace``
# registered in ``sys.modules`` so its ``@workspace_group.command``
# decorators fire deterministically when this module is imported; the
# lazy-import pattern is the v1.3-cli-split convention (see design §6).
# ``main`` is defined ABOVE this lazy import so ``workspace.py`` can
# ``from flow_engineering.cli import main`` at decorator-evaluation time
# without hitting a NameError on the partially-loaded __init__ namespace.
from . import workspace as _workspace  # noqa: F401  (lazy; see design §6)
from .workspace import workspace_health_cmd  # noqa: F401
from .workspace import _summarize_workspace_status  # noqa: F401


# Lazy submodule import (v1.3-cli-split, Slice 3). Keeps ``cli.project``
# registered in ``sys.modules`` so its ``@projects_group.command``
# decorators fire deterministically when this module is imported; the
# lazy-import pattern is the v1.3-cli-split convention (see design §6).
# ``main`` is defined ABOVE this lazy import so ``project.py`` can
# ``from flow_engineering.cli import main`` at decorator-evaluation time
# without hitting a NameError on the partially-loaded __init__ namespace.
# Same precedent as Slice 2 (``workspace.py``).
from . import project as _project  # noqa: F401  (lazy; see design §6)
from .project import _detect_project_markers  # noqa: F401
from .project import _git  # noqa: F401


# Lazy submodule import (v1.3-cli-split, Slice 4). Keeps ``cli.drift``
# registered in ``sys.modules`` so its ``@drift_group.command``,
# ``@drift_events_group.command`` and ``@drift_events_alias_group.command``
# decorators fire deterministically when this module is imported; the
# lazy-import pattern is the v1.3-cli-split convention (see design §6).
# ``main`` is defined ABOVE this lazy import so ``drift.py`` can
# ``from flow_engineering.cli import main`` at decorator-evaluation time
# without hitting a NameError on the partially-loaded __init__ namespace.
# Same precedent as Slice 2 (``workspace.py``) and Slice 3 (``project.py``).
from . import drift as _drift  # noqa: F401  (lazy; see design §6)
from .drift import _format_drift_events_text  # noqa: F401


# Lazy submodule import (v1.3-cli-split, Slice 5). Keeps ``cli.snapshot``
# registered in ``sys.modules`` so its ``@snapshot_group.command``
# decorators fire deterministically when this module is imported; the
# lazy-import pattern is the v1.3-cli-split convention (see design §6).
# ``main`` is defined ABOVE this lazy import so ``snapshot.py`` can
# ``from flow_engineering.cli import main`` at decorator-evaluation time
# without hitting a NameError on the partially-loaded __init__ namespace.
# Same precedent as Slice 2 (``workspace.py``), Slice 3 (``project.py``),
# and Slice 4 (``drift.py``). NO re-exports — ``snapshot`` subcommands
# are reached via the ``main`` Click group; the snapshot helpers
# (``_build_snapshot_manager`` etc.) are submodule-internal only.
from . import snapshot as _snapshot  # noqa: F401  (lazy; see design §6)


@main.command()
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Project root where flow-engineering/<change>/ will be created.",
)
@click.option(
    "--cross-projects",
    multiple=True,
    help="Sub-projects affected (repeatable).",
)
def new(change: str, target: Path, cross_projects: tuple[str, ...]) -> None:
    """Scaffold a new change."""
    change_dir, sm = scaffold_change(
        change=change,
        target_dir=target,
        cross_projects=list(cross_projects),
    )
    click.echo(f"Created change '{change}' at {change_dir}")
    click.echo(f"State: {sm.status.value}")
    if cross_projects:
        click.echo(f"Cross-projects: {', '.join(cross_projects)}")
    click.echo(f"\nNext: edit {change_dir}/explore/exploration.md")


@main.command(name="new-project")
@click.argument("project_name")
@click.option(
    "--in",
    "target",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Directory where the new project will be bootstrapped.",
)
@click.option("--version", default="0.1.0", help="Initial flow-engineering version pin.")
def new_project(project_name: str, target: Path, version: str) -> None:
    """Bootstrap a new project."""
    project_dir = render_new_project(project_name, target, version=version)
    click.echo(f"Bootstrapped project '{project_name}' at {project_dir}")


@main.command()
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Project root to inspect.",
)
def status(target: Path) -> None:
    """List all changes and their current status."""
    fe_dir = target / "flow-engineering"
    if not fe_dir.exists():
        click.echo(f"No flow-engineering/ directory at {target}")
        sys.exit(1)
    changes = [d for d in fe_dir.iterdir() if d.is_dir()]
    if not changes:
        click.echo(f"No changes in {fe_dir}")
        return
    for change_dir in sorted(changes):
        # Skip subdirectories of changes (e.g., bootstrap/explore is NOT a change)
        if not (change_dir / "state.json").exists():
            continue
        try:
            sm = StateMachine.load(change_dir)
        except FileNotFoundError:
            continue
        manifest = load_change_yaml(change_dir)
        cross_obj = manifest.get("cross_projects", []) if isinstance(manifest, dict) else []
        cross = [str(p) for p in cross_obj] if isinstance(cross_obj, list) else []
        cross_marker = f" [cross: {', '.join(cross)}]" if cross else ""
        click.echo(
            f"  {change_dir.name}: {sm.status.value}"
            f"  ({len(sm.transitions)} transitions,"
            f" {sm.token_cost}/{sm.token_budget} tokens)"
            f"{cross_marker}"
        )


@main.command()
def doctor() -> None:
    """Check plugin/CLI version compatibility."""
    import flow_engineering

    click.echo(f"flow-engineering {flow_engineering.__version__}")
    click.echo("Python OK")
    click.echo("Plugin: not loaded (this CLI is invoked directly)")


@main.command()
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Project root containing flow-engineering/<change>/.",
)
@click.option("--no-strict-tdd", "no_strict_tdd", is_flag=True, help="Disable strict TDD (requires --reason).")
@click.option("--reason", default=None, help="Reason for disabling strict TDD.")
def apply(change: str, target: Path, no_strict_tdd: bool, reason: str | None) -> None:
    """Apply tasks for a change (TASKED -> APPLYING -> VERIFYING)."""
    _enforce_min_skill_versions_or_exit(target / "pyproject.toml")
    if no_strict_tdd and not reason:
        click.echo("ERROR: --no-strict-tdd requires --reason", err=True)
        sys.exit(2)
    result = apply_change(change=change, target=target)
    click.echo(result.message)
    if result.delegation_error:
        click.echo(f"[delegation] {result.delegation_error}")
    if result.task_id:
        click.echo(f"Next task: {result.task_id}")


@main.command()
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
)
@click.option("--test-output", default="", help="Test runner output to classify.")
def verify(change: str, target: Path, test_output: str) -> None:
    """Verify change (APPLYING -> VERIFYING -> ARCHIVING)."""
    _enforce_min_skill_versions_or_exit(target / "pyproject.toml")
    result = verify_change(change=change, target=target, test_output=test_output)
    click.echo(f"[{result.action}] {result.message}")
    if result.failure_class:
        click.echo(f"Failure class: {result.failure_class.value}")


# NOTE: previously declared with `@main.command()`. Now registered as a
# subcommand of the new `archive` group below. The function body is
# preserved verbatim; the surface moves from `flow archive <change>`
# to `flow archive change <change>` (BREAKING per CHANGELOG v1.3.0-alpha,
# mirrors the v1.2 `flow drift <change>` → `flow drift run <change>` precedent).
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
)
@click.option("--diff", default="", help="Diff text for structural change detection.")
@click.option("--no-graphify", is_flag=True, help="Skip the graphify rebuild (dry-run).")
def archive(change: str, target: Path, diff: str, no_graphify: bool) -> None:
    """Archive change (ARCHIVING -> DONE), trigger graph rebuild."""
    _enforce_min_skill_versions_or_exit(target / "pyproject.toml")
    result = archive_change(
        change=change,
        target=target,
        diff_text=diff,
        dry_run_graphify=no_graphify or True,  # v0.1.0: always dry-run by default
    )
    click.echo(result.message)
    if result.graphify_decision:
        click.echo(
            f"Graphify: mode={result.graphify_decision.mode} "
            f"cost=${result.graphify_decision.estimated_cost_usd:.2f}"
        )


@main.command()
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
)
@click.option(
    "--drift", "drift_flag",
    is_flag=True,
    default=False,
    help="REQ-15: also watch apply-progress writes; emit drift summary per merged task.",
)
@click.option(
    "--graph-json", "graph_json",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to graph.json snapshot (default: ~/.flow-engineering/graph.json).",
)
def watch(change: str, target: Path, drift_flag: bool, graph_json: Path | None) -> None:
    """Watch for exploration.md changes and auto-transition NEW -> EXPLORED.

    With ``--drift`` (REQ-15), the watcher ALSO subscribes to apply-progress
    writes and emits a one-line ``drift: <change> N findings (...)`` summary
    to stdout on every event with at least one task in ``status: merged``.
    Counters ``drift_*_total`` are incremented per event via
    ``observability.record_drift_summary``. Missing ``graph.json`` emits
    ``unable_to_verify: ...`` once and the watcher stays alive.
    """
    started, message = start_watch(
        change=change,
        target=target,
        drift=drift_flag,
        graph_json_path=graph_json,
        on_summary=lambda line: click.echo(line),
    )
    click.echo(message)
    if not started:
        sys.exit(1)


@main.command(name="memory-timeline")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
)
def memory_timeline(target: Path) -> None:
    """Show a timeline view of all changes and their transitions."""
    from flow_engineering.timeline import build_timeline, render_timeline

    fe_dir = target / "flow-engineering"
    if not fe_dir.exists():
        click.echo("No flow-engineering/ directory.")
        return
    changes = [d for d in fe_dir.iterdir() if d.is_dir() and (d / "state.json").exists()]
    if not changes:
        click.echo("No changes.")
        return
    timeline = build_timeline(changes)
    click.echo(render_timeline(timeline))


# ---------- REQ-V1.0.1..V1.0.4: flow where "<query>" ----------
# ---------- Phase 2: flow-where-cross-project (REQ-CROSS-PROJECT-SCOPE) ----------


#: Per-project search directories (Phase 2 prospec; missing subdirs silently skipped).
_CROSS_PROJECT_DIRS: tuple[str, ...] = (
    "src",
    "internal",
    "cmd",
    "tests",
    "openspec",
    "graphify-out",
)

#: Default limit for the cross-project path (bumped from 20 for N-projects scale).
_CROSS_PROJECT_DEFAULT_LIMIT: int = 50


def _tag_match_type(file_path: str) -> str:
    """Return the match-type tag for a file path under a project root.

    Mapping per Phase 2 design D3:
    - ``tests/`` → ``test``
    - ``openspec/`` → ``sdd``
    - ``graphify-out/`` → ``graph``
    - everything else (``src/``, ``internal/``, ``cmd/``) → ``code``
    """
    norm = file_path.replace("\\", "/")
    if norm.startswith("tests/"):
        return "test"
    if norm.startswith("openspec/"):
        return "sdd"
    if norm.startswith("graphify-out/"):
        return "graph"
    return "code"


def _search_projects_for_query(
    root: Path,
    query: str,
    regex_flag: bool,
    limit: int = _CROSS_PROJECT_DEFAULT_LIMIT,
) -> tuple[list[dict[str, Any]], int]:
    """Walk projects under ``root`` and search the 6 prospec dirs per project.

    Returns ``(hits, projects_searched)``. Each hit dict has
    ``{project, file, line, content, type}``. ``projects_searched`` is the
    number of directory entries iterated under ``root`` (matches are capped
    per project at ``limit``). Missing subdirs are silently skipped — the
    orchestrator walks each existing subdir independently so a partial tree
    (only ``src/`` + ``tests/``, no ``openspec/``) still produces hits.

    Pure orchestration: no printing, no Click exit, no global state. Reuses
    ``where_mod._run_search`` + ``where_mod._parse_hits`` (read-only seam;
    ``where.py`` module API stays untouched). The cross-project path needs
    the ``content`` field for the JSON / text / TSV renderers, so we
    normalise the rg/grep output before parsing — see :func:`_strip_trailing_colon`.
    """
    hits: list[dict[str, Any]] = []
    if not root.is_dir():
        return (hits, 0)
    projects_searched = 0
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        projects_searched += 1
        # Call _run_search once per existing prospec subdir so a missing
        # dir doesn't cause rg/grep to exit non-zero and discard matches
        # from the dirs that DO exist (rg's rc=2 fails the whole run when
        # any path is missing; see ``where._run_search`` fail-open contract).
        project_hits: list[dict[str, Any]] = []
        for sub in _CROSS_PROJECT_DIRS:
            sub_path = entry / sub
            if not sub_path.is_dir():
                continue
            raw = where_mod._run_search(query, [sub], entry)
            # Custom parser: robust to colons in matched text (see
            # :func:`_parse_cross_project` for the rationale).
            project_hits.extend(_parse_cross_project(raw))
        # Sort: file path asc → line asc; cap at `limit`.
        project_hits.sort(key=lambda h: (h["path"], h["line"]))
        for hit in project_hits[: max(0, limit)]:
            hits.append(
                {
                    "project": entry.name,
                    "file": hit["path"],
                    "line": hit["line"],
                    "content": hit["content"],
                    "type": _tag_match_type(hit["path"]),
                }
            )
    return (hits, projects_searched)


def _strip_trailing_colon(output: str) -> str:
    """Strip a trailing ``:`` from each rg/grep output line.

    ``where._parse_hits`` uses ``split(":", 3)`` and assumes 3-part lines
    are ``path:line:text`` (grep shape) and 4-part lines are ``path:line:col:text``
    (rg shape). When the matched line content has no internal colons and
    happens to end with one (e.g. ``def foo():``), the actual output is
    ``path:1:def foo():`` which Python splits into 4 parts with the last
    part empty — the parser then sees an empty snippet. Stripping the
    trailing colon collapses it to ``path:1:def foo()`` so the parser
    reads the snippet correctly. Read-only normalisation — we never modify
    ``where.py``.
    """
    if not output:
        return output
    out_lines: list[str] = []
    for raw in output.splitlines():
        line = raw.rstrip("\r")
        if line.endswith(":"):
            line = line[:-1]
        out_lines.append(line)
    return "\n".join(out_lines)


def _parse_cross_project(output: str) -> list[dict[str, Any]]:
    """Cross-project parser for rg/grep ``path:line:text`` output.

    Mirrors :func:`where_mod._parse_hits` semantics but is robust to the
    case where the matched line content contains colons. ``where._parse_hits``
    uses ``split(":", 3)`` and treats 4-part output as ``path:line:col:text``;
    in practice for ``--line-number`` output the 4 parts are usually
    ``path:line:half1:half2`` where ``half1:half2`` IS the text. We
    re-join the trailing parts with ``:`` to recover the full text.

    Read-only — never modifies ``where.py``. Read the rg/grep stdout,
    return ``list[dict]`` with keys ``path`` / ``line`` / ``content``.
    """
    hits: list[dict[str, Any]] = []
    if not output:
        return hits
    for raw in output.splitlines():
        line = raw.rstrip("\r")
        if not line:
            continue
        # Strip the trailing ":" so a line ending in ":" doesn't yield an
        # empty trailing part after the split.
        if line.endswith(":"):
            line = line[:-1]
        parts = line.split(":", 3)
        if len(parts) < 3:
            continue
        path = parts[0].replace("\\", "/")
        try:
            line_no = int(parts[1])
        except ValueError:
            continue
        # Recover the text by re-joining whatever was left after `line:`
        content = ":".join(parts[2:]).strip()
        hits.append({"path": path, "line": line_no, "content": content})
    return hits


def _ascii_safe_local(s: str) -> str:
    """ASCII-safe helper (mirrors ``where_mod._ascii_safe`` for the formatters).

    Defined inline so the cross-project formatters do not depend on
    ``where.py`` private helpers (``where.py`` module API stays untouched
    per Phase 2 design).
    """
    return s.encode("ascii", "replace").decode("ascii")


def _format_where_text(
    hits: list[dict[str, Any]],
    projects_searched: int,
    hits_total: int,
    query: str,
) -> str:
    """ASCII-safe text output grouped by project (Phase 2 REQ-DEFAULT-TEXT-FORMAT).

    Layout::

        proj-a
          proj-a/src/foo.py:1  def foo():
          proj-a/tests/test_foo.py:1  def test_foo():
        proj-b
          proj-b/src/bar.py:2  def bar():
        TOTAL: projects=2 matches=3

    No box-drawing characters. ASCII-safe via :func:`_ascii_safe_local`.
    """
    if not hits:
        return f"(no matches)\nTOTAL: projects={projects_searched} matches=0"
    # Group hits by project, preserving the global project-alpha order.
    grouped: dict[str, list[dict[str, Any]]] = {}
    project_order: list[str] = []
    for hit in hits:
        proj = hit["project"]
        if proj not in grouped:
            grouped[proj] = []
            project_order.append(proj)
        grouped[proj].append(hit)
    lines: list[str] = []
    for proj in project_order:
        lines.append(proj)
        for hit in grouped[proj]:
            content = _ascii_safe_local(str(hit.get("content", "")))
            lines.append(f"  {hit['file']}:{hit['line']}  {content}")
    lines.append(f"TOTAL: projects={projects_searched} matches={hits_total}")
    return "\n".join(lines)


def _format_where_json(
    root: Path,
    query: str,
    hits: list[dict[str, Any]],
    projects_searched: int,
    hits_total: int,
    engram_stub: bool = False,
) -> str:
    """JSON envelope ``version:"1"`` (Phase 2 REQ-EXPLICIT-FORMAT-FLAG).

    Top-level keys in order: ``version, root, query, format, results, totals, engram``.
    Results sorted: project alpha → file path → line. No ``generated_at`` field
    (byte-deterministic; mirrors AC9 byte-identical discipline).
    """
    sorted_hits = sorted(hits, key=lambda h: (h["project"], h["file"], h["line"]))
    payload: dict[str, Any] = {
        "version": "1",
        "root": str(root),
        "query": query,
        "format": "json",
        "results": [
            {
                "project": h["project"],
                "file": h["file"],
                "line": h["line"],
                "content": _ascii_safe_local(str(h.get("content", ""))),
                "type": h["type"],
            }
            for h in sorted_hits
        ],
        "totals": {"projects_searched": projects_searched, "matches": hits_total},
        "engram": {"enabled": False, "phase": "stub"} if engram_stub else {"enabled": False, "phase": "stub"},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _format_where_tsv(hits: list[dict[str, Any]]) -> str:
    """TSV with header ``project\\\\tfile\\\\tline\\\\ttype\\\\tcontent`` (Phase 2 REQ-EXPLICIT-FORMAT-FLAG).

    Newlines in ``content`` are escaped to the literal sequence ``\\n`` (two
    chars: backslash + n) so each row stays on a single line. UTF-8 in content
    is preserved (no ASCII-stripping at this layer — TSV is meant for piping).
    """
    lines: list[str] = ["project\tfile\tline\ttype\tcontent"]
    for hit in hits:
        content = str(hit.get("content", "")).replace("\r", "").replace("\n", "\\n")
        lines.append(
            f"{hit['project']}\t{hit['file']}\t{hit['line']}\t{hit['type']}\t{content}"
        )
    return "\n".join(lines)


def _validate_regex_or_exit(query: str) -> None:
    """Validate ``query`` as a regex at the CLI boundary; exit 2 on ``re.error``.

    Mirrors the per-gate exit contract from REQ-V1.0.4 (D9): actionable stderr
    line, exit code 2, no traceback. Used only when ``--regex`` is set on
    ``flow where``.
    """
    try:
        re.compile(query)
    except re.error as exc:
        click.echo(f"invalid --regex pattern: {exc}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)


def _resolve_cross_project_root(root_path: Path | None) -> Path | None:
    """Resolve ``--root`` from the explicit flag or the legacy projects helper.

    Returns the explicit ``root_path`` when provided; otherwise falls back to
    :func:`_resolve_projects_root` so ``FLOW_PROJECTS_ROOT`` and the platform
    default still apply. Returns ``None`` when the resolved path is not a
    directory (caller decides the exit code).
    """
    if root_path is not None:
        return root_path
    return _resolve_projects_root(None)


@main.command(name="where")
@click.argument("query")
@click.option(
    "--limit",
    type=int,
    default=where_mod.DEFAULT_LIMIT,
    help="Max hits per backend section (default: 20).",
)
@click.option(
    "--no-graph",
    "no_graph_flag",
    is_flag=True,
    default=False,
    help="Skip the graphify GRAPH section entirely.",
)
@click.option(
    "--pretty",
    "pretty_flag",
    is_flag=True,
    default=False,
    help="(Future) Emit Unicode output. Default is ASCII-safe for portability (HOTFIX-V1.0.5).",
)
@click.option(
    "--root",
    "root_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Projects root to search across (default: FLOW_PROJECTS_ROOT or platform default).",
)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["text", "json", "tsv"]),
    default="text",
    help="Output format: text (default ASCII-safe grouped), json (envelope), tsv (header + tabs).",
)
@click.option(
    "--regex",
    "regex_flag",
    is_flag=True,
    default=False,
    help="Treat query as a regex (case-insensitive). Exit 2 on invalid pattern.",
)
@click.option(
    "--engram",
    "engram_flag",
    is_flag=True,
    default=False,
    help="Reserved for Phase 4+ Engram MCP integration. No-op in v1.",
)
def where_cmd(
    query: str,
    limit: int,
    no_graph_flag: bool,
    pretty_flag: bool,
    root_path: Path | None,
    format_type: str,
    regex_flag: bool,
    engram_flag: bool,
) -> None:
    """Answer "where did I implement X?" (REQ-V1.0.1..V1.0.4 + Phase 2 cross-project).

    Legacy mode (no ``--root``/``--format``/``--regex``/``--engram``) keeps the
    existing :func:`where_mod.where` orchestrator + CODE/TESTS/SDD/GRAPH text
    rendering — byte-identical to the pre-Phase-2 contract.

    Cross-project mode (any of the four Phase 2 flags present) walks the 6
    locked directories (``src/``, ``internal/``, ``cmd/``, ``tests/``,
    ``openspec/``, ``graphify-out/``) under ``--root`` and renders one of
    three output formats. Exit codes: 0 = match-or-empty, 1 = no-match,
    2 = error (bad regex, unreadable root).

    Output is ASCII-safe by default (Windows cp1252 friendly). The
    ``--pretty`` flag is reserved for future Unicode output (Opción
    media UX work) and is currently a no-op.
    """
    # Phase 2 dispatch: any of the new flags activates the cross-project path.
    cross_project_active = (
        root_path is not None
        or format_type != "text"
        or regex_flag
        or engram_flag
    )

    if not cross_project_active:
        # Legacy path — unchanged behavior.
        result = where_mod.where(query, limit=limit, no_graph=no_graph_flag)
        click.echo(where_mod.render_text(result))
        return

    # Phase 2 cross-project path.
    if regex_flag:
        _validate_regex_or_exit(query)

    resolved_root = _resolve_cross_project_root(root_path)
    if resolved_root is None or not resolved_root.is_dir():
        click.echo(
            f"error: --root path not found or not a directory: {resolved_root}",
            err=True,
        )
        ctx = click.get_current_context()
        ctx.exit(2)

    # Bump limit to cross-project scale when the user kept the legacy default.
    effective_limit = (
        _CROSS_PROJECT_DEFAULT_LIMIT
        if limit == where_mod.DEFAULT_LIMIT
        else limit
    )

    hits, projects_searched = _search_projects_for_query(
        resolved_root, query, regex_flag, limit=effective_limit
    )
    hits_total = len(hits)

    if format_type == "json":
        click.echo(
            _format_where_json(
                resolved_root,
                query,
                hits,
                projects_searched,
                hits_total,
                engram_stub=engram_flag,
            )
        )
    elif format_type == "tsv":
        click.echo(_format_where_tsv(hits))
    else:
        click.echo(_format_where_text(hits, projects_searched, hits_total, query))

    # Exit-code mapping per Phase 2 REQ-EXIT-CODE-MAPPING:
    # 0 = matches OR empty match set; 1 = no matches.
    ctx = click.get_current_context()
    ctx.exit(0 if hits_total > 0 else 1)


FLOW_VECTOR_SEARCH_ENV: str = "FLOW_VECTOR_SEARCH"
VECTOR_INSTALL_HINT: str = "pip install flow-engineering[vectors]"


def _sqlite_vec_available() -> bool:
    """Return True iff the ``[vectors]`` extra (specifically ``sqlite_vec``) is importable.

    Used by ``flow reindex`` to gate the SqliteVecStore path. Mirrors
    :func:`_vectors_extra_available` but focused on the SQLite side —
    sentence-transformers / torch are NOT required to write the index,
    only to compute embeddings (which can come from :class:`MockEmbeddingProvider`
    in tests).
    """
    try:
        import sqlite_vec  # noqa: F401
    except ImportError:
        return False
    return True


def _vectors_sqlite_path() -> Path:
    """Return the path used by ``flow reindex`` for ``SqliteVecStore``.

    Defaults to ``~/.flow-engineering/vectors.sqlite`` (mirrors the
    ``DEFAULT_GRAPH_JSON`` precedent). Tests override via ``monkeypatch.setattr``
    on the cli module's helper so the production default stays untouched.
    """
    return Path.home() / ".flow-engineering" / "vectors.sqlite"


def _vectors_extra_available() -> bool:
    """Return True iff the ``[vectors]`` extra is importable (REQ-17 gate leg 1).

    Imports are guarded so a missing module only sets the flag to ``False``
    — it MUST NOT raise. Test isolation uses ``monkeypatch.setattr`` on this
    helper to flip the gate without touching the heavy dependencies.
    """
    try:
        import sentence_transformers  # noqa: F401
        import sqlite_vec  # noqa: F401
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


def _ensure_vector_extra() -> None:
    """Exit non-zero with the install hint if ``[vectors]`` is missing (REQ-17).

    Separate helper so ``flow search --semantic`` / ``flow reindex`` can call
    it BEFORE the env-var check. Mirrors the per-gate exit contract from
    REQ-17 scenarios 2 + 4 — actionable stderr line, exit code 2, no traceback.
    """
    if not _vectors_extra_available():
        click.echo(
            "Semantic search disabled: install [vectors] extra — "
            f"{VECTOR_INSTALL_HINT}",
            err=True,
        )
        sys.exit(2)


def _ensure_vector_env() -> None:
    """Exit non-zero with the env hint if ``FLOW_VECTOR_SEARCH!=1`` (REQ-17).

    Only reached after :func:`_ensure_vector_extra` passes, so the message
    is unambiguously "you have the extra installed but forgot to set the env".
    """
    if os.environ.get(FLOW_VECTOR_SEARCH_ENV) != "1":
        click.echo(
            "Semantic search disabled: set FLOW_VECTOR_SEARCH=1",
            err=True,
        )
        sys.exit(2)


def _default_save_backend() -> EngramBackend:
    """Return the active backend.

    REQ-17 gate state machine:
    - Both gates met (``[vectors]`` extra AND ``FLOW_VECTOR_SEARCH=1``) → wrap
      the inner ``InMemoryBackend`` in :class:`HybridBackend` with a real
      ``SentenceTransformersProvider`` so default ``flow save`` writes
      embeddings on save.
    - Otherwise → return the inner backend unchanged. Default ``flow save``
      stays byte-identical to v0.3.0 (REQ-17 scenario 5).
    """
    if not (_vectors_extra_available() and os.environ.get(FLOW_VECTOR_SEARCH_ENV) == "1"):
        return InMemoryBackend()
    from flow_engineering.embedding_provider import SentenceTransformersProvider
    from flow_engineering.hybrid_backend import HybridBackend

    provider = SentenceTransformersProvider()
    return HybridBackend(InMemoryBackend(), provider)


@main.command()
@click.argument("change")
@click.argument("phase")
@click.option(
    "--content",
    default=None,
    help="Inline content to save (mutually exclusive with --content-file).",
)
@click.option(
    "--content-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to file containing the observation content.",
)
@click.option(
    "--with-suggest",
    "with_suggest_flag",
    is_flag=True,
    default=False,
    help="Run auto-suggest and accept candidates non-interactively.",
)
@click.option(
    "--no-suggest",
    "no_suggest_flag",
    is_flag=True,
    default=False,
    help="Skip auto-suggest entirely; writes source=manual.",
)
def save(
    change: str,
    phase: str,
    content: str | None,
    content_file: Path | None,
    with_suggest_flag: bool,
    no_suggest_flag: bool,
) -> None:
    """Save a phase artifact, optionally running auto-suggest (REQ-6).

    Auto-suggest resolution order:
    1. ``--with-suggest`` flag (non-interactive accept-all).
    2. ``--no-suggest`` flag (bypass suggester, source=manual).
    3. ``FLOW_AUTO_SUGGEST=1`` env var (non-interactive accept-all).
    4. Interactive TTY prompt (when ``stdin.isatty()``).
    5. Default: append unbound block, do not call graphify.
    """
    if with_suggest_flag and no_suggest_flag:
        raise click.UsageError("--with-suggest and --no-suggest are mutually exclusive.")
    if content is not None and content_file is not None:
        raise click.UsageError("Use either --content or --content-file, not both.")

    if content_file is not None:
        text = content_file.read_text(encoding="utf-8")
    elif content is not None:
        text = content
    else:
        text = sys.stdin.read()

    env_active = os.environ.get(FLOW_AUTO_SUGGEST_ENV) == "1"
    is_tty = sys.stdin.isatty()
    if with_suggest_flag:
        with_suggest, no_suggest = True, False
    elif no_suggest_flag:
        with_suggest, no_suggest = False, True
    else:
        with_suggest = env_active or is_tty
        no_suggest = False

    client = EngramClient(change, _default_save_backend())
    client.save_phase(
        phase,
        text,
        with_suggest=with_suggest,
        no_suggest=no_suggest,
        is_tty=is_tty,
    )
    click.echo(f"Saved {phase} for {change} (with_suggest={with_suggest}, no_suggest={no_suggest})")


# ---------- REQ-17 / REQ-18: flow search <query> ----------


def _parse_csv(raw: str | None) -> list[str] | None:
    """Split a comma-separated string into a list of trimmed, non-empty tokens.

    Returns ``None`` when ``raw`` is ``None`` (the flag was not given).
    Returns ``[]`` when ``raw`` is an empty string or only separators.
    Uses the stdlib ``csv`` module so quoted commas (``"a, b",c``) parse
    per RFC 4180 rather than naïve ``str.split(',')``.
    """
    if raw is None:
        return None
    rows = list(_csv.reader([raw]))
    if not rows:
        return []
    return [item.strip() for item in rows[0] if item and item.strip()]


def _format_search_row(rank: int, obs_id: int, title: str, score: float) -> str:
    """One text-table row for ``flow search`` output (legacy 4-column)."""
    return f"{rank:<3}  obs {obs_id:<6}  {score:.4f}  {title}"


def _render_search_table(rows: list[dict[str, Any]]) -> str:
    """Pretty-print search hits as a fixed-width text table.

    Adds a ``PROJECT`` column when any row carries a ``project`` field
    (REQ-25 federated path). Legacy single-project search renders the
    original 4-column layout so existing output is unchanged.
    """
    if not rows:
        return "(no results)"
    show_project = any("project" in r for r in rows)
    headers: tuple[str, ...]
    if show_project:
        headers = ("rank", "id", "score", "project", "title")
        sep = "-" * 88
    else:
        headers = ("rank", "id", "score", "title")
        sep = "-" * 64
    lines: list[str] = []
    lines.append("  ".join(h.upper() for h in headers))
    lines.append(sep)
    for r in rows:
        if show_project:
            lines.append(
                f"{int(r.get('rank', 0)):<3}  obs {int(r.get('observation_id', 0)):<6}  "
                f"{float(r.get('score', 0.0)):.4f}  {str(r.get('project', '')):<24}  "
                f"{str(r.get('title', ''))}"
            )
        else:
            lines.append(
                _format_search_row(
                    int(r.get("rank", 0)),
                    int(r.get("observation_id", 0)),
                    str(r.get("title", "")),
                    float(r.get("score", 0.0)),
                )
            )
    return "\n".join(lines)


def _search_results_to_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project ``mem_search*`` results to the JSON/table shape.

    The vector methods return ``observation_id`` + ``score`` + ``rank`` per
    REQ-17 contract. The legacy ``mem_search`` returns plain observation
    dicts with ``id`` and no score/rank — synthesize a position-based
    rank and a 0.0 score so the table renders uniformly. REQ-25 adds
    federated multi-project search; rows with a ``project`` field carry
    it through so the renderer can prepend the PROJECT column.
    """
    out: list[dict[str, Any]] = []
    for rank, r in enumerate(results):
        obs_id = r.get("observation_id", r.get("id"))
        row: dict[str, Any] = {
            "observation_id": obs_id,
            "rank": r.get("rank", rank),
            "score": r.get("score", 0.0),
            "title": r.get("title", ""),
            "topic_key": r.get("topic_key", ""),
        }
        if r.get("project") is not None:
            row["project"] = r["project"]
        out.append(row)
    return out


@main.command()
@click.argument("query")
@click.option(
    "--semantic",
    "semantic_flag",
    is_flag=True,
    default=False,
    help="REQ-17: semantic search via embeddings (requires [vectors] extra AND FLOW_VECTOR_SEARCH=1).",
)
@click.option(
    "--hybrid",
    "hybrid_flag",
    is_flag=True,
    default=False,
    help="REQ-18: hybrid semantic + FTS search with --alpha blending.",
)
@click.option(
    "--alpha",
    type=float,
    default=0.5,
    help="REQ-18: weight for semantic vs FTS in --hybrid mode (0.0 = pure FTS, 1.0 = pure semantic).",
)
@click.option(
    "--k",
    type=int,
    default=10,
    help="Maximum number of results to return.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit machine-readable JSON instead of a text table.",
)
@click.option(
    "--federated",
    "federated_flag",
    is_flag=True,
    default=False,
    help="REQ-25: federated multi-project search (opt-in; default = single-project FTS).",
)
@click.option(
    "--projects",
    default=None,
    help="REQ-25: comma-separated project keys (default = all when --federated).",
)
@click.option(
    "--since",
    default=None,
    help="REQ-25: ISO 8601 date or datetime (lexicographic >= on created_at).",
)
@click.option(
    "--type",
    "type_csv",
    default=None,
    help="REQ-25: comma-separated observation types (exact match, case-sensitive).",
)
def search(
    query: str,
    semantic_flag: bool,
    hybrid_flag: bool,
    alpha: float,
    k: int,
    as_json: bool,
    federated_flag: bool,
    projects: str | None,
    since: str | None,
    type_csv: str | None,
) -> None:
    """Search observations (REQ-17 + REQ-18 + REQ-25 CLI surface).

    Default mode is FTS5 prose (``mem_search``); this stays byte-identical
    to the pre-vector behavior so existing scripts are unaffected. The
    ``--semantic`` and ``--hybrid`` flags enable vector retrieval. The
    ``--federated`` flag enables multi-project search via
    ``mem_search_federated`` with optional ``--projects`` / ``--since``
    / ``--type`` filters. The federated and vector paths are mutually
    exclusive.
    """
    from flow_engineering.cli.drift import _parse_since  # noqa: F401  (lazy; lives in cli.drift post-Slice-4)
    if semantic_flag and hybrid_flag:
        click.echo(
            "ERROR: --semantic and --hybrid are mutually exclusive.", err=True
        )
        sys.exit(2)
    if federated_flag and (semantic_flag or hybrid_flag):
        click.echo(
            "ERROR: --federated is mutually exclusive with --semantic/--hybrid.",
            err=True,
        )
        sys.exit(2)
    if not (0.0 <= alpha <= 1.0):
        click.echo(
            f"ERROR: --alpha must be in [0.0, 1.0], got {alpha}", err=True
        )
        sys.exit(2)
    if federated_flag and since is not None:
        # Validate the ISO string via _parse_since (epoch conversion is
        # discarded — we pass the raw ISO through to mem_search_federated
        # so the SQL `created_at >=` comparison is lexicographic on the
        # YYYY-MM-DD HH:MM:SS TEXT format per design D7).
        try:
            _parse_since(since)
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(2)

    backend = _default_save_backend()

    if federated_flag:
        # REQ-25: federated multi-project search. Projects + type are
        # CSV-parsed; None means "no filter". --since is the raw ISO
        # string (validated above). ``trigger="cli"`` tags the
        # observability event so dashboards can separate user invocations
        # from programmatic ones (REQ-26 contract).
        raw = backend.mem_search_federated(
            query,
            projects=_parse_csv(projects),
            limit=k,
            since=since,
            type_filter=_parse_csv(type_csv),
            trigger="cli",
        )
    elif semantic_flag or hybrid_flag:
        # Gate check order matters: extra first (so the install hint wins
        # over the env hint when both are missing). Mirrors REQ-17 scenarios
        # 2 and 4 — the user gets the most actionable error first.
        _ensure_vector_extra()
        _ensure_vector_env()

        if hybrid_flag:
            # The library validates alpha again at the call boundary, but
            # we exit early here so the CLI never invokes the library with
            # garbage. ``trigger="cli"`` tags the observability event so
            # dashboards can separate user-driven calls from programmatic ones.
            raw = backend.mem_search_hybrid(query, k=k, alpha=alpha, trigger="cli")
        else:
            raw = backend.mem_search_semantic(query, k=k, trigger="cli")
    else:
        raw = backend.mem_search(query, limit=k)

    rows = _search_results_to_rows(raw)
    if as_json:
        click.echo(json.dumps({"results": rows}, ensure_ascii=False, indent=2))
        return
    click.echo(_render_search_table(rows))


# ---------- REQ-21: flow reindex ----------


def _resolve_reindex_provider() -> Any:
    """Return the embedding provider to use for ``flow reindex``.

    Tries :class:`SentenceTransformersProvider` first (real model); falls
    back to :class:`MockEmbeddingProvider` when torch / sentence-transformers
    are unavailable so the reindex path stays runnable in test environments
    without the ``[vectors]`` extra. Both providers satisfy the same ABC,
    so the worker code is identical.
    """
    from flow_engineering.embedding_provider import (
        MockEmbeddingProvider,
        SentenceTransformersProvider,
    )

    try:
        return SentenceTransformersProvider()
    except Exception:  # EmbeddingProviderUnavailable or any ImportError.
        return MockEmbeddingProvider()


def _perform_reindex_batch(
    observations: list[dict[str, Any]],
    store: Any,
    provider: Any,
    *,
    simulate_crash_after: int | None = None,
) -> int:
    """Embed + upsert one batch of observations into ``store``.

    Returns the number of rows successfully upserted. When
    ``simulate_crash_after`` is set, the worker writes only that many rows
    of the batch and then raises — used by the REQ-21 crash-resume test to
    validate that the next run picks up where the first stopped.
    """
    from flow_engineering.binding import split_prose_and_refs

    texts = [split_prose_and_refs(str(o.get("content", "")))[0] for o in observations]
    embeddings = provider.embed_batch(texts)
    written = 0
    for o, vec in zip(observations, embeddings, strict=True):
        if simulate_crash_after is not None and written >= simulate_crash_after:
            raise RuntimeError("simulated crash mid-batch")
        store.add(str(o.get("id", o.get("observation_id"))), vec)
        written += 1
    return written


@main.command()
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Observations per embedding batch (default: 100).",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    default=False,
    help="Report the count without writing anything to the vector store.",
)
def reindex(batch_size: int, dry_run: bool) -> None:
    """Reindex every observation into the sqlite-vec store (REQ-21).

    Sync streaming: walks ``backend.iter_observations()`` in batches of
    ``--batch-size``, embeds the prose of each observation (with the
    trailing ``code_refs`` block stripped), and upserts the resulting
    vector into :class:`SqliteVecStore` at the path returned by
    :func:`_vectors_sqlite_path`. Writes are idempotent (INSERT OR REPLACE)
    and commit per batch, so a crash mid-run leaves the index in a
    consistent state — re-invoking ``flow reindex`` finishes the work.
    """
    if batch_size <= 0:
        click.echo(
            f"ERROR: --batch-size must be > 0, got {batch_size}", err=True
        )
        sys.exit(2)

    if not _sqlite_vec_available():
        click.echo(
            "reindex disabled: install [vectors] extra — "
            f"{VECTOR_INSTALL_HINT}",
            err=True,
        )
        sys.exit(2)

    backend = _default_save_backend()
    # Unwrap HybridBackend so we index the underlying prose store directly.
    inner_backend = getattr(backend, "inner", backend)
    observations = list(inner_backend.iter_observations())
    total = len(observations)

    if dry_run:
        # Count report only — no DB writes, no progress lines, no done line.
        click.echo(f"reindex: {total} observations need reindex", err=True)
        return

    if total == 0:
        # Empty corpus short-circuits with the no-op summary line so the
        # done-format is consistent across zero and non-zero runs.
        click.echo(
            "reindex: done — 0 observations indexed in 0.0s", err=True
        )
        observability.increment("reindex_observations_total", count=0)
        observability.increment("reindex_duration_seconds", value=0.0)
        return

    from flow_engineering.vectors import SqliteVecStore

    store = SqliteVecStore(_vectors_sqlite_path())
    provider = _resolve_reindex_provider()

    started = time.monotonic()
    done = 0
    for batch_start in range(0, total, batch_size):
        batch = observations[batch_start : batch_start + batch_size]
        done += _perform_reindex_batch(batch, store, provider)
        pct = int(done * 100 / total) if total else 100
        # Per-batch progress to stderr (REQ-21 contract: one line per batch).
        click.echo(f"reindex: {done}/{total} ({pct}%) embedded", err=True)
    elapsed = time.monotonic() - started
    click.echo(
        f"reindex: done — {total} observations indexed in {elapsed:.1f}s",
        err=True,
    )

    # REQ-22 observability: one counter batch per reindex invocation.
    observability.increment("reindex_observations_total", count=total)
    observability.increment("reindex_duration_seconds", value=float(elapsed))


if __name__ == "__main__":
    main()


# ---------- REQ-7: flow inspect <change> ----------


def _truncate(text: str, width: int) -> str:
    """Truncate text to ``width`` characters, adding an ellipsis when cut."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def _format_binding_line(ref: CodeRef) -> str:
    """One-line binding summary: ``id (label, file:line, conf, src)``."""
    return (
        f"{ref.id} ({ref.label}, {ref.file}:{ref.line}, "
        f"conf={ref.confidence:.2f}, src={ref.source})"
    )


def _render_inspect_row(obs: dict[str, Any]) -> dict[str, Any]:
    """Build one inspect row from a raw observation dict.

    Returns a dict with keys ``decision_id``, ``decision`` (title),
    ``code_refs`` (list of CodeRef objects), ``freshness``, and
    ``parse_error`` (when the block is malformed). Never raises: per-row
    parse errors are isolated (REQ-7 scenario). The CodeRef list is the
    canonical representation; dict serialization happens only at the JSON
    output boundary.
    """
    title = str(obs.get("title", ""))
    content = str(obs.get("content", ""))
    decision_id = obs.get("id")
    parse_error: str | None = None
    refs: list[CodeRef] = []
    if CODE_REFS_MARKER in content:
        try:
            refs = extract_code_refs(content)
        except Exception as exc:  # ParseError or any extraction error.
            parse_error = f"parse error: {exc}"
    freshness = observability.compute_freshness(obs.get("updated_at"))
    return {
        "decision_id": decision_id,
        "decision": title,
        "code_refs": refs,
        "freshness": freshness,
        "parse_error": parse_error,
    }


def _render_inspect_table(rows: list[dict[str, Any]]) -> str:
    """Render the inspect rows as a fixed-width text table."""
    headers = ("decision", "code_refs", "freshness")
    lines: list[str] = []
    lines.append("  ".join(h.upper() for h in headers))
    lines.append("-" * 72)
    if not rows:
        lines.append("(no observations for this change)")
        return "\n".join(lines)
    for row in rows:
        decision = _truncate(str(row.get("decision", "")), 36)
        if row.get("parse_error"):
            refs_text = str(row["parse_error"])
        elif row["code_refs"]:
            refs_text = "; ".join(_format_binding_line(r) for r in row["code_refs"])
        else:
            refs_text = "—"
        refs_text = _truncate(refs_text, 200)
        freshness = str(row.get("freshness", "never"))
        lines.append(f"{decision}  {refs_text}  {freshness}")
    return "\n".join(lines)


def _serialize_inspect_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert CodeRef objects in ``code_refs`` to dicts for JSON output."""
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "decision_id": row.get("decision_id"),
                "decision": row.get("decision"),
                "code_refs": [
                    {
                        "id": r.id,
                        "label": r.label,
                        "file": r.file,
                        "line": r.line,
                        "confidence": r.confidence,
                        "source": r.source,
                    }
                    for r in row.get("code_refs", [])
                ],
                "freshness": row.get("freshness"),
                "parse_error": row.get("parse_error"),
            }
        )
    return out


@main.command()
@click.argument("change")
@click.option("--json", "json_flag", is_flag=True, default=False,
              help="Emit machine-readable JSON instead of a text table.")
def inspect(change: str, json_flag: bool) -> None:
    """Render decisions for a change as a table (REQ-7).

    Columns: DECISION (id/title), CODE_REFS (id, label, file:line,
    confidence, source per binding), FRESHNESS (age with stale warning
    when older than 30 days). Per-row parse errors are isolated: a bad
    block in one observation never blanks the rest of the table.
    """
    started = time.monotonic()
    observability.increment("inspect_invoked_total", change=change)
    backend = _default_save_backend()
    observations = iter_observations_for_change(change, backend)
    rows = [_render_inspect_row(o) for o in observations]
    elapsed_ms = int((time.monotonic() - started) * 1000)
    observability.increment("inspect_render_ms", elapsed_ms=elapsed_ms, count=len(rows))
    if json_flag:
        click.echo(json.dumps(_serialize_inspect_rows(rows), ensure_ascii=False, indent=2))
        return
    click.echo(_render_inspect_table(rows))


# ---------- REQ-8 close: flow metrics ----------


def _summarize_metrics(events: list[dict[str, Any]]) -> dict[str, int]:
    """Collapse a list of increment events into ``{name: count}``."""
    summary: dict[str, int] = {}
    for ev in events:
        name = ev.get("name")
        if not isinstance(name, str):
            continue
        fields = ev.get("fields") or {}
        payload = fields.get("count") or fields.get("confirmed") or 1
        try:
            payload_int = int(payload)
        except (TypeError, ValueError):
            payload_int = 1
        summary[name] = summary.get(name, 0) + payload_int
    return summary


@main.group(invoke_without_command=True)
@click.option("--json", "json_flag", is_flag=True, default=False,
              help="Emit machine-readable JSON instead of a text summary.")
@click.pass_context
def metrics(ctx: click.Context, json_flag: bool) -> None:
    """Dump the JSONL counter sink as a summary (REQ-8 close).

    With no subcommand, renders the legacy flat text/JSON dump (REQ-8 close
    contract; byte-identical to v0.6.0). The ``summary`` subcommand renders
    the new per-domain dashboard (REQ-35).
    """
    if ctx.invoked_subcommand is not None:
        # Subcommand handles its own output (e.g. `flow metrics summary`).
        return
    events = observability.read_all()
    summary = _summarize_metrics(events)
    if json_flag:
        click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    if not summary:
        click.echo("(no metrics recorded)")
        return
    name_width = max(len(name) for name in summary)
    for name in sorted(summary):
        click.echo(f"{name.ljust(name_width)}  {summary[name]}")


# Window choices for `flow metrics summary --window` (REQ-35/REQ-36).
# The CLI accepts both presets (1h/24h/7d/30d) and custom `<int><h|d>` format;
# the union is validated at runtime by :func:`observability.parse_window`
# rather than via ``click.Choice`` (which can only model a fixed enum).
SUMMARY_WINDOW_CHOICES: list[str] = list(observability.WINDOW_PATTERNS.keys())

# Domain choices for `flow metrics summary --domain` (REQ-37).
# Derived from observability.ALL_DOMAINS so the CLI stays in lockstep
# with the cross-domain slice expansion (T1.6: backfill + federated +
# metadata + engine). ``engine`` is RESERVED (REQ-42 deferred to v1.1)
# and produces an empty filter result rather than an error.
SUMMARY_DOMAIN_CHOICES: list[str] = list(observability.ALL_DOMAINS)


@metrics.command("summary")
@click.option(
    "--format", "fmt", default="text",
    type=click.Choice(["text", "json", "json-detailed"], case_sensitive=False),
    help="Output format (REQ-35: text default, json for machine-readable).",
)
@click.option(
    "--window", "window", default=None,
    help=(
        "Rolling time-window filter (REQ-35/REQ-36): preset "
        "(1h|24h|7d|30d) or custom '<int><h|d>' (e.g. 12h, 3d). "
        "Rolling relative to now (NOT calendar-aligned)."
    ),
)
@click.option(
    "--domain", "domain", default=None,
    type=click.Choice(SUMMARY_DOMAIN_CHOICES, case_sensitive=False),
    help=(
        "Prefix-based domain slice (REQ-37): "
        + "|".join(observability.ALL_DOMAINS)
        + ". The engine slot is reserved (REQ-42) and returns empty in v1."
    ),
)
@click.option(
    "--since", "since_iso", default=None, metavar="ISO8601",
    help="Absolute ISO 8601 lower bound: ts >= <iso> (REQ-36).",
)
@click.option(
    "--until", "until_iso", default=None, metavar="ISO8601",
    help="Absolute ISO 8601 upper bound: ts <= <iso> (REQ-36).",
)
def metrics_summary(
    fmt: str,
    window: str | None,
    domain: str | None,
    since_iso: str | None,
    until_iso: str | None,
) -> None:
    """Render the per-domain text dashboard (REQ-35 / change #6 PR#1 T1.2 + T1.5 + T1.8).

    Uses :func:`observability.read_and_summarize` for the read+filter+summary
    pipeline + empty-reason detection (D8 default-empty contract). Applies
    ``--since`` / ``--until`` as a post-filter pass when those flags are set.

    Exit-code mapping (D9):
    - 0: success (including empty / missing → "No metrics recorded yet.").
    - 2: invalid flag value (``--window`` parse failure, ``--since`` /
      ``--until`` ISO parse failure, ``--domain`` unknown).
    - 3: metrics file exists but every line is malformed
      (D9 ``EXIT_MALFORMED_METRICS``); emits ``"Error: metrics file at
      <path> is malformed."`` to stderr.
    """
    from flow_engineering.cli.drift import _parse_since  # noqa: F401  (lazy; lives in cli.drift post-Slice-4)
    fmt_lower = fmt.lower()

    since_epoch: float | None = None
    if since_iso is not None:
        try:
            since_epoch = _parse_since(since_iso)
        except ValueError as exc:
            click.echo(f"invalid --since value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    until_epoch: float | None = None
    if until_iso is not None:
        try:
            until_epoch = _parse_since(until_iso)
        except ValueError as exc:
            click.echo(f"invalid --until value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    # Validate --window EARLY so a bad value exits 2 even when the JSONL
    # sink is missing (read_and_summarize short-circuits on empty reason
    # before applying the window filter, so we must validate here).
    if window is not None:
        try:
            observability.parse_window(window)
        except ValueError as exc:
            click.echo(f"invalid --window value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    domain_normalized: str | None = None
    if domain is not None:
        # click.Choice accepts mixed case (case_sensitive=False), but
        # DOMAIN_BY_PREFIX keys are lowercase — normalize before lookup.
        try:
            domain_normalized = observability.validate_domain(domain.lower())
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    try:
        result = observability.read_and_summarize(
            window=window,
            domain=domain_normalized,
        )
    except ValueError as exc:
        # unknown domain / parse_window failure — defensive fallback
        # (click.Choice covers the validation path at parse time).
        click.echo(str(exc), err=True)
        sys.exit(observability.EXIT_INVALID_VALUE)

    if result.empty_reason == "missing_file" or result.empty_reason == "empty_file":
        click.echo("No metrics recorded yet.")
        return
    if result.empty_reason == "all_malformed":
        click.echo(
            f"Error: metrics file at {result.source_path} is malformed.",
            err=True,
        )
        sys.exit(observability.EXIT_MALFORMED_METRICS)

    summary_data = result.summary

    # --since / --until are applied as a post-filter pass because
    # read_and_summarize() handles only window+domain (per design D8/D9).
    if since_epoch is not None or until_epoch is not None:
        events = observability.read_all_metrics()
        if domain_normalized is not None:
            events = observability.read_events_by_domain(domain_normalized)
        if window is not None:
            events = observability.filter_by_window(events, window)
        if since_epoch is not None:
            events = [e for e in events if e.timestamp >= since_epoch]
        if until_epoch is not None:
            events = [e for e in events if e.timestamp <= until_epoch]
        summary_data = observability.summarize(events)

    if not any(summary_data.values()):
        click.echo("No metrics in window/domain.")
        return

    if fmt_lower == "text":
        for d in sorted(summary_data):
            click.echo(f"{d}:")
            for counter, count in sorted(summary_data[d].items()):
                click.echo(f"  {counter}: {count}")
        return
    if fmt_lower in ("json", "json-detailed"):
        click.echo(json.dumps(summary_data, ensure_ascii=False, indent=2))
        return
    click.echo(f"unknown --format value: {fmt}", err=True)
    sys.exit(observability.EXIT_INVALID_VALUE)


# ---------- REQ-38: flow metrics export ----------


def _apply_metrics_filters(
    events: list[observability.MetricEvent],
    *,
    window: str | None,
    domain: str | None,
    since_epoch: float | None,
    until_epoch: float | None,
) -> list[observability.MetricEvent]:
    """Apply the unified filter pipeline used by ``metrics export``.

    Reuses ``observability.filter_by_window`` / ``_prefixes_for_domain``
    / direct epoch comparison so the filter chain is identical across
    formats (D8/D9 / T2.3 composition requirement).
    """
    filtered = events
    if window is not None:
        filtered = observability.filter_by_window(filtered, window)
    if domain is not None:
        prefixes = observability._prefixes_for_domain(domain)
        filtered = [
            e for e in filtered
            if any(e.counter_name.startswith(p) for p in prefixes)
        ]
    if since_epoch is not None:
        filtered = [e for e in filtered if e.timestamp >= since_epoch]
    if until_epoch is not None:
        filtered = [e for e in filtered if e.timestamp <= until_epoch]
    return filtered


@metrics.command("export")
@click.option(
    "--format", "fmt", default="text",
    type=click.Choice(["text", "json", "prometheus"], case_sensitive=False),
    help=(
        "Output format (REQ-38): text default, json for machine-readable "
        "list of events, prometheus for textfile exposition."
    ),
)
@click.option(
    "--out", "out_path", default=None,
    type=click.Path(),
    help=(
        "Atomic write to <path> (REQ-38 / D10). Default = stdout. "
        "Creates parent dir on demand; rejects with exit 4 on failure."
    ),
)
@click.option(
    "--window", "window", default=None,
    help=(
        "Rolling time-window filter (REQ-36): preset "
        "(1h|24h|7d|30d) or custom '<int><h|d>'."
    ),
)
@click.option(
    "--since", "since_iso", default=None, metavar="ISO8601",
    help="Absolute ISO 8601 lower bound: ts >= <iso> (REQ-36).",
)
@click.option(
    "--until", "until_iso", default=None, metavar="ISO8601",
    help="Absolute ISO 8601 upper bound: ts <= <iso> (REQ-36).",
)
@click.option(
    "--domain", "domain", default=None,
    type=click.Choice(SUMMARY_DOMAIN_CHOICES, case_sensitive=False),
    help="Prefix-based domain slice (REQ-37).",
)
def metrics_export(
    fmt: str,
    out_path: str | None,
    window: str | None,
    since_iso: str | None,
    until_iso: str | None,
    domain: str | None,
) -> None:
    """Export metrics in text / json / prometheus format (REQ-38 / change #6 PR#2 T2.2).

    Honors ``--window`` / ``--since`` / ``--until`` / ``--domain`` filters
    identically to ``flow metrics summary`` so the filter chain is
    composable across subcommands (T2.3 / D8/D9).

    ``--format prometheus`` emits the D6 textfile exposition format
    (``# HELP`` + ``# TYPE`` + metric lines, cumulative counter values,
    ``# EOF`` for empty input). ``--format json`` emits a JSON list of
    MetricEvent-shaped dicts (counter_name + labels + timestamp).
    ``--format text`` (default) renders a human-readable ``name  count``
    table (mirrors the REQ-8 close contract for the no-flag ``flow metrics``).

    ``--out <path>`` triggers an atomic write via
    :func:`observability.atomic_write_text` (D10). Parent directories are
    created on demand; a write failure exits ``4`` per design D9.

    Exit-code mapping (D9):
    - 0: success (including default-empty per D8).
    - 2: invalid flag value (``--format=garbage``; ``--window`` parse
      failure; ``--domain`` unknown; ``--since`` / ``--until`` ISO parse
      failure).
    - 4: write failure on ``--out``.
    """
    from flow_engineering.cli.drift import _parse_since  # noqa: F401  (lazy; lives in cli.drift post-Slice-4)
    fmt_lower = fmt.lower()

    since_epoch: float | None = None
    if since_iso is not None:
        try:
            since_epoch = _parse_since(since_iso)
        except ValueError as exc:
            click.echo(f"invalid --since value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    until_epoch: float | None = None
    if until_iso is not None:
        try:
            until_epoch = _parse_since(until_iso)
        except ValueError as exc:
            click.echo(f"invalid --until value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    if window is not None:
        try:
            observability.parse_window(window)
        except ValueError as exc:
            click.echo(f"invalid --window value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    domain_normalized: str | None = None
    if domain is not None:
        try:
            domain_normalized = observability.validate_domain(domain.lower())
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    events = observability.read_all_metrics()
    filtered = _apply_metrics_filters(
        events,
        window=window,
        domain=domain_normalized,
        since_epoch=since_epoch,
        until_epoch=until_epoch,
    )

    if fmt_lower == "prometheus":
        content = observability.prometheus_exposition(filtered)
    elif fmt_lower == "json":
        content = json.dumps(
            [
                {
                    "name": ev.counter_name,
                    "fields": ev.labels,
                    "ts": datetime.fromtimestamp(
                        ev.timestamp, tz=UTC
                    ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                for ev in filtered
            ],
            ensure_ascii=False,
            indent=2,
        )
    elif fmt_lower == "text":
        if not filtered:
            content = "(no metrics recorded)\n"
        else:
            summary = observability.summarize(filtered)
            # Flatten {domain: {counter: count}} for the REQ-8-style table.
            flat: dict[str, int] = {}
            for counters in summary.values():
                flat.update(counters)
            if not flat:
                content = "(no metrics recorded)\n"
            else:
                width = max(len(name) for name in flat)
                lines = [
                    f"{name.ljust(width)}  {count}"
                    for name, count in sorted(flat.items())
                ]
                content = "\n".join(lines) + "\n"
    else:
        click.echo(f"unknown --format value: {fmt}", err=True)
        sys.exit(observability.EXIT_INVALID_VALUE)

    if out_path is None:
        click.echo(content, nl=False)
        return

    target = Path(out_path)
    try:
        observability.atomic_write_text(target, content)
    except OSError as exc:
        click.echo(
            json.dumps(
                {
                    "error": "write failed",
                    "path": str(target),
                    "cause": exc.strerror or str(exc),
                }
            ),
            err=True,
        )
        sys.exit(observability.EXIT_WRITE_FAILURE)


# ---------- REQ-39: flow metrics aggregate (percentile aggregation via reservoir sampling) ----------


# Percentile choices for `flow metrics aggregate --percentile` (REQ-39).
# Mirrors observability._VALID_PERCENTILES (50/95/99) so the CLI stays
# in lockstep with the helper's validation set.
AGGREGATE_PERCENTILE_CHOICES: list[str] = ["p50", "p95", "p99"]


@metrics.command("aggregate")
@click.option(
    "--percentile", "percentiles",
    type=click.Choice(AGGREGATE_PERCENTILE_CHOICES, case_sensitive=False),
    multiple=True, default=("p95",),
    help=(
        "Percentile(s) to compute (REQ-39): p50 / p95 / p99. "
        "Repeatable; default = p95. Uses reservoir sampling for "
        "memory efficiency on large event streams."
    ),
)
@click.option(
    "--window", "window", default=None,
    help=(
        "Rolling time-window filter (REQ-36): preset "
        "(1h|24h|7d|30d) or custom '<int><h|d>'."
    ),
)
@click.option(
    "--since", "since_iso", default=None, metavar="ISO8601",
    help="Absolute ISO 8601 lower bound: ts >= <iso> (REQ-36).",
)
@click.option(
    "--until", "until_iso", default=None, metavar="ISO8601",
    help="Absolute ISO 8601 upper bound: ts <= <iso> (REQ-36).",
)
@click.option(
    "--domain", "domain", default=None,
    type=click.Choice(SUMMARY_DOMAIN_CHOICES, case_sensitive=False),
    help="Prefix-based domain slice (REQ-37).",
)
@click.option(
    "--reservoir-size", "reservoir_size", default=1000, type=int,
    help=(
        "Sample-size ceiling per counter for the reservoir sampler "
        "(REQ-39 / D7). Default 1000."
    ),
)
@click.option(
    "--format", "fmt", default="text",
    type=click.Choice(["text", "json"], case_sensitive=False),
    help="Output format (REQ-39): text (default aligned table) or json.",
)
def metrics_aggregate(
    percentiles: tuple[str, ...],
    window: str | None,
    since_iso: str | None,
    until_iso: str | None,
    domain: str | None,
    reservoir_size: int,
    fmt: str,
) -> None:
    """Compute percentiles over counter values (REQ-39 / change #6 PR#2 T2.5).

    Consumes :func:`observability.aggregate_percentile` (reservoir-sampled,
    memory-bounded at ``--reservoir-size``) over the filtered event set
    and renders the result as either an aligned text table (default) or
    a flat JSON dict.

    Exit-code mapping (D9):
    - 0: success (including default-empty per D8: empty sink emits
      a header-only table in text mode or ``{}`` in JSON mode).
    - 2: invalid flag value (Click ``click.Choice`` validation failure
      on ``--percentile`` / ``--domain``; ``--window`` parse failure;
      ``--since`` / ``--until`` ISO parse failure).
    """
    from flow_engineering.cli.drift import _parse_since  # noqa: F401  (lazy; lives in cli.drift post-Slice-4)
    fmt_lower = fmt.lower()

    # Parse the --percentile labels into integers; validate against the
    # helper's accepted set (defensive: Click already validates at parse
    # time, but the explicit check keeps the helper self-contained).
    pct_ints: list[int] = []
    for label in percentiles:
        pct_ints.append(int(label.lower().lstrip("p")))

    since_epoch: float | None = None
    if since_iso is not None:
        try:
            since_epoch = _parse_since(since_iso)
        except ValueError as exc:
            click.echo(f"invalid --since value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    until_epoch: float | None = None
    if until_iso is not None:
        try:
            until_epoch = _parse_since(until_iso)
        except ValueError as exc:
            click.echo(f"invalid --until value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    if window is not None:
        try:
            observability.parse_window(window)
        except ValueError as exc:
            click.echo(f"invalid --window value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    domain_normalized: str | None = None
    if domain is not None:
        try:
            domain_normalized = observability.validate_domain(domain.lower())
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    events = observability.read_all_metrics()
    filtered = _apply_metrics_filters(
        events,
        window=window,
        domain=domain_normalized,
        since_epoch=since_epoch,
        until_epoch=until_epoch,
    )

    result = observability.aggregate_percentile(
        filtered,
        percentiles=tuple(pct_ints),
        reservoir_size=reservoir_size,
    )

    if fmt_lower == "json":
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if fmt_lower == "text":
        click.echo(observability.format_percentile_report(result), nl=False)
        return
    click.echo(f"unknown --format value: {fmt}", err=True)
    sys.exit(observability.EXIT_INVALID_VALUE)


# ---------- Phase 3: flow workspace status ----------


# ---------- REQ-49 + REQ-50: flow prompts subcommand group (T2.1) ----------


_STATUS_LABELS = {
    "checksum_mismatch": "DRIFT",
    "version_mismatch": "DRIFT",
    "missing_file": "MISSING",
    "frontmatter_parse_error": "PARSE_ERROR",
}
"""Map :class:`SkillDrift.drift_kind` to the CLI's short status label.

Drift kinds that imply a real divergence (``checksum_mismatch`` and
``version_mismatch``) collapse to ``"DRIFT"``; the parse-error and
missing-file kinds keep their distinct labels so the CLI footer can
report parse-error counts separately (REQ-59 S2 mirror, future T2.4).
"""


def _emit_check_observability(
    drifts: list[Any], duration_seconds: float,
) -> None:
    """Emit the W2 observability counter set for one ``prompts check`` invocation.

    Four counter names are emitted (REQ-22 prefix convention; mirrors
    ``drift_*_total`` from drift-hardening + REQ-22 ``vector_*_total``):

    - ``prompts_check_total{result="clean"}`` — exactly once when no drift
      was detected.
    - ``prompts_check_total{result="drift"}`` — exactly once when at least
      one drift finding was reported.
    - ``prompts_check_drift_total{skill=<name>}`` — once per drift finding,
      tagged with the affected skill name (so the metrics surface can
      break down drift counts by skill).
    - ``prompts_check_duration_seconds`` — exactly once per invocation,
      with ``value=<elapsed>`` (gauge-style ``_seconds`` suffix counter;
      mirrors ``reindex_duration_seconds`` precedent).

    The function is best-effort and never raises; ``observability.increment``
    swallows ``OSError`` internally so a write failure to the JSONL sink
    cannot break the CLI flow.

    Args:
        drifts: The list of :class:`SkillDrift` from :func:`check_drift`.
        duration_seconds: Wall-clock duration of the check in seconds.
    """
    observability.increment(
        "prompts_check_total",
        result="drift" if drifts else "clean",
    )
    for drift in drifts:
        observability.increment(
            "prompts_check_drift_total",
            skill=drift.skill_name,
        )
    observability.increment(
        "prompts_check_duration_seconds",
        value=float(duration_seconds),
    )


@dataclass(frozen=True)
class CheckAction:
    """Resolved action for ``flow prompts check`` based on flag combinations.

    Attributes:
        catalog: The catalog dict to walk (filtered when ``--skill`` was
            passed; the full :data:`SKILL_CATALOG` otherwise).
        init_or_update: ``"init"`` for ``--init`` (bootstrap), ``"update"``
            for ``--update`` (refresh), ``None`` for the normal drift-check
            path. When set, the CLI side-steps ``check_drift`` and emits
            the init/update confirmation line.
        suppress_drift_exit: ``True`` when ``--no-fail`` was passed; the CLI
            keeps emitting drift lines but exits 0 instead of 1.
        unknown_skill: When ``--skill <name>`` did not match any catalog
            entry, this is the requested name; the CLI exits 3 with an
            error message and does NOT walk the catalog.
    """

    catalog: dict[str, Any]
    init_or_update: str | None
    suppress_drift_exit: bool
    unknown_skill: str | None


def _resolve_check_action(
    *,
    init_flag: bool,
    update_flag: bool,
    no_fail_flag: bool,
    skill_name: str | None,
    full_catalog: dict[str, Any],
) -> CheckAction:
    """Resolve the action implied by the flag combination.

    Pure function: takes the 4 flag values + the full catalog and returns
    a :class:`CheckAction` describing what the CLI should do. The caller
    (``prompts_check``) is responsible for emitting output and exit codes.

    Flag precedence:
    - ``--init`` wins over ``--update`` (first-write semantics).
    - ``--skill`` is applied to the normal drift-check path only; on
      ``--init`` / ``--update`` the full catalog is walked.
    - ``--no-fail`` only affects the drift-check path.
    """
    if init_flag:
        return CheckAction(full_catalog, "init", no_fail_flag, None)
    if update_flag:
        return CheckAction(full_catalog, "update", no_fail_flag, None)
    catalog = full_catalog
    unknown: str | None = None
    if skill_name is not None:
        filtered = {
            k: v for k, v in full_catalog.items() if v.skill_name == skill_name
        }
        if not filtered:
            unknown = skill_name
        else:
            catalog = filtered
    return CheckAction(catalog, None, no_fail_flag, unknown)


_LINT_ERROR_CODES = frozenset({"jinja_syntax", "invalid_version"})
"""Validation codes that map to "error" severity (CLI exit 2).

``jinja_syntax`` breaks render_prompt outright; ``invalid_version``
breaks the SemVer contract used by ``flow prompts show --version``.
Both are blocking and warrant the strict exit code per REQ-47 + REQ-50.
"""


_LINT_WARNING_CODES = frozenset(
    {"duplicate_name", "invalid_domain", "undefined_var"}
)
"""Validation codes that map to "warning" severity (CLI exit 1).

These are quality issues that don't break rendering but signal catalog
hygiene problems. Mirrors the ``drift-hardening`` precedent of using a
warning tier distinct from the error tier.
"""


@main.group(name="prompts")
def prompts_group() -> None:
    """Inspect and validate prompt registry + SKILL catalog (REQ-49 + REQ-50).

    Subcommands:
    - ``check`` — walk the SKILL_CATALOG and report drift findings.
    - ``lint``  — lint the inline prompt registry (REQ-47 surface).
    """


@prompts_group.command(name="check")
@click.option(
    "--init",
    "init_flag",
    is_flag=True,
    default=False,
    help="Bootstrap the sidecar JSON with current on-disk state, then exit 0.",
)
@click.option(
    "--update",
    "update_flag",
    is_flag=True,
    default=False,
    help="Re-compute and overwrite sidecar JSON checksums, then exit 0.",
)
@click.option(
    "--no-fail",
    "no_fail_flag",
    is_flag=True,
    default=False,
    help="Suppress exit 1 when drift is detected (CI warnings-only mode).",
)
@click.option(
    "--skill",
    "skill_name",
    default=None,
    help="Limit the check to the named skill (both surfaces: skill + prompt).",
)
def prompts_check(
    init_flag: bool,
    update_flag: bool,
    no_fail_flag: bool,
    skill_name: str | None,
) -> None:
    """Walk SKILL_CATALOG and report drift findings (REQ-49 + REQ-50).

    Exit codes:
    - 0: clean state (no drift detected) OR ``--init``/``--update`` succeeded
      OR ``--no-fail`` suppressed a drift-detected run.
    - 1: drift detected (one or more entries diverged). Suppressed by
      ``--no-fail``.
    - 3: usage error (e.g., ``--skill unknown`` with no matching catalog
      entry per design D9).

    Flags (per tasks-pr2.md T2.2 + verify-report-pr2a.md W1):
    - ``--init``: bootstrap the sidecar with current on-disk state.
    - ``--update``: re-compute and overwrite the sidecar JSON checksums
      (functionally equivalent to ``--init``; documented separately for
      intent: idempotent refresh vs first-run bootstrap).
    - ``--no-fail``: suppress exit 1 on drift detection (CI compat).
    - ``--skill <name>``: limit the catalog walk to the named skill's two
      surfaces (skill + prompt). Unknown names exit 3.

    Stdout format: ``<skill_name>/<surface>: <expected_version>: <status>``
    per design §"Data Flow / flow prompts check", followed by a footer
    ``N skills verified · M drift detected``.
    """
    from flow_engineering import opencode_skill_catalog as osc

    action = _resolve_check_action(
        init_flag=init_flag,
        update_flag=update_flag,
        no_fail_flag=no_fail_flag,
        skill_name=skill_name,
        full_catalog=osc.SKILL_CATALOG,
    )

    if action.init_or_update == "init":
        count = osc.init_checksums()
        click.echo(
            f"Initialized {count} checksums · sidecar: {osc.SIDECAR_PATH}"
        )
        return
    if action.init_or_update == "update":
        count = osc.update_checksums()
        click.echo(
            f"Updated {count} checksums · sidecar: {osc.SIDECAR_PATH}"
        )
        return

    if action.unknown_skill is not None:
        click.echo(f"Unknown skill: {action.unknown_skill}", err=True)
        sys.exit(3)

    start = time.monotonic()
    drifts = osc.check_drift(action.catalog)
    elapsed = time.monotonic() - start
    _emit_check_observability(drifts, elapsed)

    for drift in drifts:
        status = _STATUS_LABELS.get(drift.drift_kind, "DRIFT")
        click.echo(
            f"{drift.skill_name}/{drift.surface}: "
            f"{drift.expected_version}: {status}"
        )

    drift_count = len(drifts)
    catalog_size = len(action.catalog)
    click.echo(
        f"{catalog_size} skills verified · {drift_count} drift detected"
    )

    if drift_count > 0:
        click.echo(
            f"[WARN] flow prompts check: {drift_count} drifts detected "
            f"— see stdout for details",
            err=True,
        )

    if drift_count > 0 and not action.suppress_drift_exit:
        sys.exit(1)


@prompts_group.command(name="lint")
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit the lint report as a JSON object on stdout.",
)
def prompts_lint(json_flag: bool) -> None:
    """Lint the inline prompt registry (REQ-47 surface, REQ-50 wrapper).

    Exit codes:
    - 0: clean registry (no warnings, no errors).
    - 1: warnings only (no errors).
    - 2: errors detected.

    Stdout default format: ``<prompt_id>: <error_code>: <message>`` lines
    followed by a footer ``N prompts linted · M warnings · K errors``.
    With ``--json``, the full :class:`LintReport.to_dict()` shape is
    emitted instead (machine-readable; mirrors REQ-8 ``flow metrics --json``).
    """
    from flow_engineering import prompt_registry

    report = prompt_registry.lint_prompts()
    warning_count = sum(
        1 for e in report.errors if e.error_code in _LINT_WARNING_CODES
    )
    error_count = sum(
        1 for e in report.errors if e.error_code in _LINT_ERROR_CODES
    )

    if json_flag:
        click.echo(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        for err in report.errors:
            click.echo(
                f"{err.prompt_name}: {err.error_code}: {err.message}"
            )
        catalog_size = len(report.catalog)
        click.echo(
            f"{catalog_size} prompts linted · "
            f"{warning_count} warnings · {error_count} errors"
        )

    if error_count > 0:
        sys.exit(2)
    if warning_count > 0:
        sys.exit(1)


# ---------- REQ-50 T3.1: flow prompts list subcommand ----------


_PROMPT_REGISTRY_SCHEMA_VERSION: str = "1.0"
"""Catalog-wide schema version for the prompt-registry entries.

Mirrors the spec REQ-50 schema_version contract. Surfaced via
``flow prompts list --json`` so downstream consumers can detect
catalog-shape drift between runtime + capability spec.
"""


def _entry_domain_value(entry: Any) -> str:
    """Return ``entry.domain.value`` as a string (defensive fallback).

    Defensive helper used by both the text-table and JSON serializers
    so a non-enum domain (e.g., a future ``str`` direct value) still
    renders. Mirrors the convention used in
    ``opencode_skill_catalog.py`` for surface handling.
    """
    domain = entry.domain
    return domain.value if hasattr(domain, "value") else str(domain)


def _entry_owner(entry: Any) -> str:
    """Render the spec-mandated owner string ``flow/{domain_value}``.

    Centralized so the text table + JSON serializer stay in lockstep
    with the spec REQ-50 S1 owner notation.
    """
    return f"flow/{_entry_domain_value(entry)}"


def _entry_location(entry: Any) -> str:
    """Render the spec-mandated location string ``prompts/<name>.j2``.

    Per W3 carry-forward: the canonical location is the repo-root
    ``prompts/`` directory; ``.j2`` suffix per design D1+D2.
    """
    return f"prompts/{entry.name}.j2"


def _format_prompts_list_row(entry: Any) -> str:
    """Format one PROMPT_NAMES row for the `flow prompts list` text table.

    Columns: ``prompt_id`` (24-wide), ``version`` (10-wide), ``owner``
    (24-wide), ``location``. The owner is rendered as
    ``flow/{domain.value}`` so it matches the spec REQ-50 S1 verbatim
    (``flow/observability`` / ``flow/binding``).
    """
    return (
        f"{entry.name:<24}  "
        f"{entry.version:<10}  "
        f"{_entry_owner(entry):<24}  "
        f"{_entry_location(entry)}"
    )


def _render_prompts_list_table(entries: list[Any]) -> str:
    """Pretty-print the prompts list as a fixed-width text table.

    Returns the full multi-line string (header + rows + footer). Mirrors
    the ``flow metrics`` table layout precedent per REQ-8.
    """
    headers = ("prompt_id", "version", "owner", "location")
    sep = "-" * 78
    lines: list[str] = []
    lines.append("  ".join(h.upper().ljust(24) for h in headers))
    lines.append(sep)
    for entry in entries:
        lines.append(_format_prompts_list_row(entry))
    lines.append(sep)
    lines.append(f"{len(entries)} prompt entries")
    return "\n".join(lines)


def _serialize_prompts_list(entries: list[Any]) -> dict[str, Any]:
    """Project PROMPT_NAMES entries into the REQ-50 ``--json`` shape.

    Shape: ``{"prompts": [...], "count": N, "registry_schema_version": "1.0"}``
    where each prompt entry has ``prompt_id``, ``domain``, ``version``,
    ``owner`` (``flow/{domain.value}``), ``variables`` (list), ``location``.

    Per T3.13 W-A1 carry-forward (verify-report-pr2b.md W-A1): the
    pre-T3.13 implementation emitted ``{name, version, owner, location,
    domain}`` with NO ``variables`` field; downstream consumers could
    not introspect declared variables from the JSON alone. The spec
    (REQ-50 S1) mandates ``variables: list`` + uses the user-facing key
    ``prompt_id`` (instead of the impl field ``name``); both keys are
    now included for backward compat with any pre-T3.13 consumer that
    still reads ``name``.
    """
    prompts: list[dict[str, Any]] = []
    for entry in entries:
        domain_value = _entry_domain_value(entry)
        declared_vars = list(entry.metadata.get("variables", ()))
        prompts.append(
            {
                "prompt_id": entry.name,
                "name": entry.name,
                "domain": domain_value,
                "version": entry.version,
                "owner": _entry_owner(entry),
                "variables": declared_vars,
                "location": _entry_location(entry),
            }
        )
    return {
        "prompts": prompts,
        "count": len(prompts),
        "registry_schema_version": _PROMPT_REGISTRY_SCHEMA_VERSION,
    }


@prompts_group.command(name="list")
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit machine-readable JSON instead of a text table.",
)
def prompts_list(json_flag: bool) -> None:
    """List every prompt in the registry (REQ-50 S1).

    Default text output: a fixed-width table with columns
    ``prompt_id`` / ``version`` / ``owner`` / ``location``, followed
    by a footer ``N prompt entries``. Owners are rendered as
    ``flow/{domain.value}`` to match the spec verbatim
    (``flow/observability`` / ``flow/binding``).

    ``--json`` emits the flat-dict shape that mirrors REQ-8
    ``flow metrics --json``: ``{"prompts": [...], "count": N,
    "registry_schema_version": "1.0"}``.

    Exit codes: 0 always (this is a read-only introspection command).
    """
    from flow_engineering import prompt_registry

    entries = prompt_registry.list_prompts()
    if json_flag:
        click.echo(
            json.dumps(
                _serialize_prompts_list(entries),
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    click.echo(_render_prompts_list_table(entries))


# ---------- REQ-50 T3.2: flow prompts show <id> subcommand ----------


_EXIT_UNKNOWN_PROMPT_ID: int = 5
"""Exit code for ``flow prompts show <unknown>`` per design D9."""


_EXIT_GOLDEN_DRIFT: int = 3
"""Exit code for ``flow prompts show --check-snapshot`` on drift (REQ-V1.2.2)."""


_GOLDEN_PROMPTS_DIR: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "tests"
    / "golden"
    / "prompts"
)
"""Canonical on-disk location for the 4 PROMPT_NAMES golden snapshots.

REQ-V1.2.2: per ``openspec/changes/v1.2-followups/explore.md`` REQ-48
section, the 4 PROMPT_NAMES entries each get a byte-identical snapshot
under ``tests/golden/prompts/`` so unintentional template edits fail CI
with a precise drift message. The ``--update-goldens`` flag writes the
canonical render here; ``--check-snapshot`` compares the canonical
render to the file at this path. Tests override this constant via
``monkeypatch.setattr`` to isolate from the committed artifacts.
"""


def _parse_var_pair(raw: str) -> tuple[str, str]:
    """Parse a ``key=value`` string into ``(key, value)`` tuple.

    Used by ``flow prompts show --var`` to convert each Click value into
    a kwarg pair. ``=`` is the only separator; keys with ``=`` in the
    value are NOT supported (mirrors the spec REQ-50 S2 grammar).
    """
    if "=" not in raw:
        raise click.BadParameter(
            f"--var must be key=value (got {raw!r}); expected '=' separator",
            param_hint="--var",
        )
    key, _, value = raw.partition("=")
    key = key.strip()
    if not key:
        raise click.BadParameter(
            f"--var key cannot be empty (got {raw!r})",
            param_hint="--var",
        )
    return key, value


@prompts_group.command(name="show")
@click.argument("prompt_id")
@click.option(
    "--var",
    "var_pairs",
    multiple=True,
    callback=lambda _ctx, _param, values: [
        _parse_var_pair(v) for v in values
    ],
    help=(
        "Variable substitution as key=value (repeatable; last-write-wins). "
        "Per spec REQ-50 S2: missing declared vars get the "
        "literal sentinel <{var_name}>."
    ),
)
@click.option(
    "--render-count",
    is_flag=True,
    help=(
        "Emit a one-line summary of render-count + last-rendered-at from "
        "the prompt render sink (REQ-V1.1.3). Composes with the rendered body."
    ),
)
@click.option(
    "--render-history",
    "render_history",
    type=int,
    default=0,
    help=(
        "Emit the last N JSONL records for this prompt id as an aligned "
        "text table (REQ-V1.1.3; default N=5 when the flag is passed "
        "without a value). Composes with the rendered body."
    ),
)
@click.option(
    "--show-render-history",
    "show_render_history",
    is_flag=True,
    default=False,
    help=(
        "Boolean toggle for the render-history view at default N=5 "
        "(REQ-V1.1.3). Use ``--render-history 10`` to override N explicitly."
    ),
)
@click.option(
    "--update-goldens",
    "update_goldens",
    is_flag=True,
    default=False,
    help=(
        "Regenerate the golden snapshot file at "
        "``tests/golden/prompts/<id>.txt`` with the canonical render "
        "(REQ-V1.2.2). Use after an intentional template change to "
        "refresh the committed snapshot. Composes with the existing "
        "rendered body output."
    ),
)
@click.option(
    "--check-snapshot",
    "check_snapshot",
    is_flag=True,
    default=False,
    help=(
        "Compare the canonical render against the golden snapshot file "
        "at ``tests/golden/prompts/<id>.txt`` (REQ-V1.2.2). Exits 3 + "
        "emits 'snapshot drift detected' to stderr on mismatch; exits 0 "
        "on match. Use in CI to gate merges on snapshot freshness."
    ),
)
def prompts_show(
    prompt_id: str,
    var_pairs: list[tuple[str, str]],
    render_count: bool,
    render_history: int,
    show_render_history: bool,
    update_goldens: bool,
    check_snapshot: bool,
) -> None:
    """Render a prompt by id with optional --var substitutions (REQ-50 S2).

    Output: metadata header (``prompt_id:``, ``version:``, ``variables:``)
    + rendered template body + footer noting the render source + the
    autoescape status. Uses ``render_prompt_safe()`` so missing declared
    variables surface as ``<{var_name}>`` sentinels (per design D4 + OQ-4).

    The ``--render-count`` + ``--render-history [N]`` flags (REQ-V1.1.3)
    surface the prompt render sink content without coupling to the
    registry. They compose with the rendered body — they do NOT
    replace it.

    Exit codes:
    - 0: rendered successfully (or sentinel substitution).
    - 5: unknown ``prompt_id`` (emits JSON error on stderr).
    """
    from flow_engineering import prompt_registry

    try:
        entry = prompt_registry.get_prompt(prompt_id)
    except KeyError:
        click.echo(
            json.dumps(
                {
                    "error": "unknown prompt id",
                    "prompt_id": prompt_id,
                    "hint": "run 'flow prompts list' to see available",
                },
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(_EXIT_UNKNOWN_PROMPT_ID)

    declared = list(entry.metadata.get("variables", ()))
    safe_kwargs: dict[str, str] = dict(var_pairs)
    # Per D4 + OQ-4: substitute the literal sentinel for missing
    # declared variables BEFORE rendering (render_prompt_safe has its
    # own logic but we pre-substitute here so the header + body use
    # the same source-of-truth).
    for var_name in declared:
        if var_name not in safe_kwargs:
            safe_kwargs[var_name] = f"<{var_name}>"

    # REQ-V1.2.2 (T2.4 GREEN): golden snapshot flags. The snapshot
    # comparison uses the CANONICAL render (via ``render_prompt_canonical``)
    # which is independent of the user's --var pairs so the snapshot
    # file is deterministic across operator invocations.
    if update_goldens or check_snapshot:
        canonical_render = prompt_registry.render_prompt_canonical(prompt_id)
        snap_path = _GOLDEN_PROMPTS_DIR / f"{prompt_id}.txt"
        if update_goldens:
            try:
                _GOLDEN_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
                snap_path.write_text(canonical_render, encoding="utf-8")
            except OSError as exc:
                click.echo(
                    json.dumps(
                        {
                            "error": "snapshot_write_failed",
                            "prompt_id": prompt_id,
                            "path": str(snap_path),
                            "reason": str(exc),
                        },
                        ensure_ascii=False,
                    ),
                    err=True,
                )
                sys.exit(_EXIT_GOLDEN_DRIFT)
            click.echo(
                f"snapshot updated: {snap_path} ({len(canonical_render)} bytes)"
            )
        if check_snapshot:
            if not snap_path.exists():
                click.echo(
                    json.dumps(
                        {
                            "error": "snapshot_missing",
                            "prompt_id": prompt_id,
                            "path": str(snap_path),
                            "hint": "run 'flow prompts show <id> --update-goldens' first",
                        },
                        ensure_ascii=False,
                    ),
                    err=True,
                )
                sys.exit(_EXIT_GOLDEN_DRIFT)
            existing = snap_path.read_text(encoding="utf-8")
            if existing != canonical_render:
                click.echo(
                    json.dumps(
                        {
                            "error": "snapshot_drift_detected",
                            "message": "snapshot drift detected",
                            "prompt_id": prompt_id,
                            "path": str(snap_path),
                            "expected_bytes": len(canonical_render),
                            "found_bytes": len(existing),
                            "hint": (
                                "run 'flow prompts show <id> --update-goldens' "
                                "if the template change was intentional"
                            ),
                        },
                        ensure_ascii=False,
                    ),
                    err=True,
                )
                sys.exit(_EXIT_GOLDEN_DRIFT)
            click.echo(f"snapshot OK: {snap_path}")

    try:
        rendered = prompt_registry.render_prompt_safe(prompt_id, **safe_kwargs)
    except Exception as exc:
        click.echo(
            json.dumps(
                {
                    "error": "render failed",
                    "prompt_id": prompt_id,
                    "reason": str(exc),
                },
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(_EXIT_UNKNOWN_PROMPT_ID)

    # W5 carry-forward: the 4 migrated entries use Python
    # ``.format()`` syntax (``{test_command}``); Jinja2 leaves those
    # braces literal. Fall back to ``.format()`` for the body so the
    # rendered output reflects the user's kwargs (mirrors the
    # ``render_prompt`` fallback path). Sentinels are written as
    # ``<test_command>`` so they survive the .format() pass (the
    # angle-brackets are not Python format placeholders).
    if "{" in rendered and "}" in rendered:
        import contextlib
        with contextlib.suppress(KeyError, IndexError):
            # Missing positional or named placeholder — leave the
            # Jinja2-rendered body as-is; the sentinel subs still
            # show in the output via the header line.
            rendered = rendered.format(**safe_kwargs)

    click.echo(f"prompt_id:   {entry.name}")
    click.echo(f"version:     {entry.version}")
    click.echo(f"owner:       {_entry_owner(entry)}")
    click.echo(f"variables:   {{{', '.join(f'{k}: {v}' for k, v in safe_kwargs.items())}}}")
    click.echo("-" * 64)
    click.echo(rendered)
    click.echo("-" * 64)
    click.echo(
        f"(rendered via Jinja2 · autoescape=on · source: {_entry_location(entry)})"
    )

    # REQ-V1.1.3 S2: render-count + render-history flags surface the
    # prompt render sink content. Best-effort: a missing sink file
    # means zero renders — emit a friendly note instead of crashing.
    from flow_engineering.prompt_render_log import PromptRenderLog

    sink = PromptRenderLog()
    history_n = render_history if render_history > 0 else 0
    if show_render_history and history_n == 0:
        history_n = 5

    if render_count or history_n > 0:
        try:
            events = sink.read_all()
        except OSError as exc:
            click.echo(
                f"warning: could not read prompt render sink: {exc}",
                err=True,
            )
            events = []

        matching = [e for e in events if e.prompt_id == prompt_id]

        if render_count:
            last_at = (
                max((e.rendered_at for e in matching), default=None)
            )
            last_iso = (
                datetime.fromtimestamp(last_at, tz=UTC).isoformat()
                if last_at is not None
                else "never"
            )
            click.echo(
                f"render_count: {len(matching)} (last rendered_at: {last_iso})"
            )

        if history_n > 0:
            tail = matching[-history_n:]
            click.echo(f"render_history (last {len(tail)}):")
            if not tail:
                click.echo("  (no records)")
            else:
                click.echo(
                    f"  {'rendered_at':<22} {'status':<6} {'elapsed_ms':<10} error"
                )
                for ev in tail:
                    status = "ok" if ev.ok else "fail"
                    click.echo(
                        f"  {ev.rendered_at:<22.3f} {status:<6} "
                        f"{ev.elapsed_ms:<10.2f} {ev.error or ''}"
                    )


# ---------- REQ-V1.3.4: flow archive rotate (read-only archive preview) ----------
# Note: this ``cli/__init__.py`` is the result of the v1.3 sub-change (d)
# apply that relocated the original monolithic ``cli.py`` (5168 lines) here
# verbatim. The package layout was created so that
# ``flow_engineering.cli.rotation`` is importable; see commit 2120df5 for the
# rename-detection commit. Subsequent sub-change (e) cli-split slices will
# further modularise this file.


@main.group(name="archive")
def archive_group() -> None:
    """Read-only archive introspection (REQ-V1.3.4).

    Subcommands:
    - ``rotate``: list entries in ``openspec/changes/archive/`` older than
      ``--older-than`` days. Default behavior is dry-run; never mutates
      disk. Destructive rotation is deferred to ``chore/archive-rotation-2026``.
    """


# Late import so sub-change (e) slice 11 can re-locate this without
# disturbing the rest of the click tree. The module is library-first
# (importable without CLI).
from flow_engineering.cli.rotation import rotate_cmd  # noqa: E402

archive_group.add_command(rotate_cmd)


# v1.2 surface ``flow archive <change> --in <target>`` rewritten as
# ``flow archive change <change> --in <target>`` (v1.3.0-alpha BREAKING,
# per spec REQ-V1.2.4 precedent for `flow drift run`).
@archive_group.command(name="change")
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
)
@click.option("--diff", default="", help="Diff text for structural change detection.")
@click.option("--no-graphify", is_flag=True, help="Skip the graphify rebuild (dry-run).")
def archive_change_cmd(change: str, target: Path, diff: str, no_graphify: bool) -> None:
    """Archive change (ARCHIVING -> DONE), trigger graph rebuild."""
    _enforce_min_skill_versions_or_exit(target / "pyproject.toml")
    result = archive_change(
        change=change,
        target=target,
        diff_text=diff,
        dry_run_graphify=no_graphify or True,  # v0.1.0: always dry-run by default
    )
    click.echo(result.message)
    if result.graphify_decision:
        click.echo(
            f"Graphify: mode={result.graphify_decision.mode} "
            f"cost=${result.graphify_decision.estimated_cost_usd:.2f}"
        )


if __name__ == "__main__":
    main()



