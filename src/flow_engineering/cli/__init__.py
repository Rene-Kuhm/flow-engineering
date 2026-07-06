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
from typing import Any

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


@click.group()
@click.version_option(package_name="flow-engineering")
def main() -> None:
    """Flow Engineering -- orchestrator of the Agentic & Context-Driven closed loop."""


_DEFAULT_PROJECTS_ROOT_WIN = "C:\\dev\\proyects"
_DEFAULT_PROJECTS_ROOT_NIX = "~/dev/proyects"


def _resolve_projects_root(root: Path | None) -> Path:
    """Resolve the workspace projects root used by projects/workspace commands."""
    if root is not None:
        return root
    env_root = os.environ.get("FLOW_PROJECTS_ROOT")
    if env_root:
        return Path(env_root)
    if os.name == "nt":
        return Path(_DEFAULT_PROJECTS_ROOT_WIN)
    return Path(_DEFAULT_PROJECTS_ROOT_NIX).expanduser()


def _iter_project_subdirs(root: Path) -> list[Path]:
    """Return sorted immediate subdirectories of ``root`` excluding dot-prefix entries.

    Dot-prefix entries (``.atl``, ``.opencode``, ``.venv``, ``.mypy_cache``,
    ``.pytest_cache``, ``.ruff_cache``, ``.specify``, ``.github``, etc.)
    are tooling/config -- never user projects. They are skipped at scan
    time so the workspace stays focused on real code (view-only filter;
    no directory is modified, archived, or deleted).
    """
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))

def _read_pyproject_min_skill_versions(
    pyproject_path: Path,
) -> dict[str, str] | None:
    """Read ``[tool.flow_engineering] min_sdd_skill_versions`` from ``pyproject.toml``.

    Returns ``None`` when the section is missing or the file does not
    exist (the gate is then a no-op pass-through). Uses stdlib
    ``tomllib`` (Python 3.11+).
    """
    if not pyproject_path.exists():
        return None
    try:
        import tomllib

        with pyproject_path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, ValueError):
        return None
    section = (
        data.get("tool", {}).get("flow_engineering", {}).get(
            "min_sdd_skill_versions",
        )
    )
    if not isinstance(section, dict):
        return None
    return {str(k): str(v) for k, v in section.items()}


def _enforce_min_skill_versions_or_exit(pyproject_path: Path) -> None:
    """REQ-V1.2.3: enforce ``min_sdd_skill_versions`` at SDD command startup.

    Reads the pyproject section and calls
    :func:`flow_engineering.opencode_skill_catalog.enforce_min_skill_versions`.
    On violation emits a structured JSON remediation payload on stderr
    and exits with code 4 (mirroring the
    ``observability.EXIT_WRITE_FAILURE`` contract per design D3 + D9).
    No-ops when the section is absent or empty.
    """
    min_versions = _read_pyproject_min_skill_versions(pyproject_path)
    if not min_versions:
        return
    from flow_engineering import opencode_skill_catalog as osc

    try:
        osc.enforce_min_skill_versions(min_versions)
    except osc.SkillVersionError as exc:
        message = str(exc)
        # Parse "<skill> requires version >= <min>; found <found>. Run: ..."
        skill_name = ""
        expected = ""
        found = ""
        hint = "pip install --upgrade gentle-ai"
        # Lightweight parser: split on common delimiters.
        try:
            head, _, tail = message.partition(" requires version >= ")
            skill_name = head.strip()
            rest = tail
            expected, _, after = rest.partition("; found ")
            expected = expected.strip()
            found_part, _, hint_part = after.partition(". Run: ")
            found = found_part.strip()
            if hint_part:
                hint = hint_part.strip()
        except Exception:
            pass
        payload = {
            "error": "skill_version_violation",
            "skill": skill_name,
            "expected": expected,
            "found": found,
            "hint": hint,
            "message": message,
        }
        click.echo(json.dumps(payload), err=True)
        sys.exit(observability.EXIT_WRITE_FAILURE)


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


# ---------- REQ-10/11/14: flow drift <change> ----------


DEFAULT_GRAPH_JSON: Path = Path.home() / ".flow-engineering" / "graph.json"
DEFAULT_SNAPSHOTS_DIR: Path = Path.home() / ".flow-engineering" / "snapshots"
"""Production default for the snapshots directory.

Mirrors the ``DEFAULT_GRAPH_JSON`` precedent — tests override via
``FLOW_SNAPSHOTS_DIR`` so the ``flow snapshot`` subcommands land in a
``tmp_path`` instead of polluting the user's home directory.
"""


def _resolve_snapshots_dir() -> Path:
    """Return the snapshots directory the CLI uses.

    Honours the ``FLOW_SNAPSHOTS_DIR`` env override (used by tests +
    parallel deploys); falls back to :data:`DEFAULT_SNAPSHOTS_DIR`.
    Mirrors ``decision_drift._resolve_snapshots_dir`` so the two paths
    stay in lockstep.
    """
    env = os.environ.get("FLOW_SNAPSHOTS_DIR")
    if env:
        return Path(env)
    return DEFAULT_SNAPSHOTS_DIR


def _parse_since(raw: str | None) -> float | None:
    """Parse a `--since` ISO 8601 timestamp into epoch seconds (float).

    Returns ``None`` when ``raw`` is ``None`` or empty. Raises ``ValueError``
    with a one-line human message on parse failure — the CLI catches the
    exception and emits a stderr line + exit code ``2`` per REQ-10/REQ-11.
    Accepts both naive and ``Z``/offset-aware ISO 8601 strings. Naive
    timestamps (no tzinfo) are interpreted as UTC by default — the CLI runs
    in any timezone, and `--since 2026-06-15` should mean a deterministic
    instant, not a local-time midnight that drifts across CI machines.
    """
    if raw is None or raw.strip() == "":
        return None
    cleaned = raw.strip()
    try:
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.timestamp()
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"--since must be ISO 8601 (e.g. 2026-06-15 or 2026-06-15T12:00:00Z); got {raw!r}: {exc}"
        ) from exc


def _drift_exit_code(report: decision_drift.DriftReport) -> int:
    """Resolve the exit code per REQ-11: 2 wins over 1 wins over 0.

    - 2 when ``graph_unavailable`` (terminal unable_to_verify state).
    - 1 when any binding classifies as non-STILL_VALID.
    - 0 when every binding (if any) is STILL_VALID.
    """
    if report.graph_unavailable:
        return 2
    for cls in report.class_counts:
        if cls != decision_drift.DriftClass.STILL_VALID:
            return 1
    return 0


def _serialize_drift_report(report: decision_drift.DriftReport) -> dict[str, Any]:
    """Convert a :class:`DriftReport` into a JSON-safe ``dict``.

    The ``findings`` list embeds :class:`CodeRef` dataclasses which the stdlib
    JSON encoder cannot serialize — convert each to a flat dict and turn the
    ``DriftClass`` keys/values into plain strings.
    """
    findings: list[dict[str, Any]] = []
    for f in report.findings:
        findings.append(
            {
                "decision_id": f.decision_id,
                "binding": {
                    "id": f.binding.id,
                    "label": f.binding.label,
                    "file": f.binding.file,
                    "line": f.binding.line,
                    "confidence": f.binding.confidence,
                    "source": f.binding.source,
                    "project": f.binding.project,
                },
                "drift_class": f.drift_class.value,
                "detail": f.detail,
            }
        )
    return {
        "change_name": report.change_name,
        "scanned_at": report.scanned_at,
        "graph_mtime": report.graph_mtime,
        "decisions_total": report.decisions_total,
        "bindings_total": report.bindings_total,
        "class_counts": {cls.value: count for cls, count in report.class_counts.items()},
        "findings": findings,
        "graph_unavailable": report.graph_unavailable,
    }


def _render_drift_table(report: decision_drift.DriftReport) -> str:
    """Pretty-print a :class:`DriftReport` as a fixed-width text table."""
    headers = ("decision_id", "binding.id", "binding.label", "drift_class", "detail")
    lines: list[str] = []
    lines.append("  ".join(h.upper() for h in headers))
    lines.append("-" * 96)
    if report.findings:
        for f in report.findings:
            detail = f.detail if f.detail else f.drift_class.value
            lines.append(
                f"{f.decision_id}  {f.binding.id}  {f.binding.label}  "
                f"{f.drift_class.value}  {detail}"
            )
    else:
        if report.graph_unavailable:
            lines.append("(unable_to_verify: graph.json unavailable)")
        else:
            lines.append("(no bindings scanned)")
    return "\n".join(lines)


def _now_iso() -> str:
    """Return UTC now as an ISO 8601 string with a ``Z`` suffix."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_back_findings(
    report: decision_drift.DriftReport, change_name: str
) -> int:
    """Persist per-finding metadata via ``EngramClient.update_observation_metadata``.

    Per REQ-14, a single-row failure MUST NOT abort the loop — each
    ``update_observation_metadata`` call is wrapped in its own ``except``
    clause that logs to observability and continues. Returns the count of
    successful writes (used by tests to assert no partial abort).

    Per REQ-59 S2 / design D8: when ``skipped_total >= FLOW_DRIFT_SKIP_WARN_THRESHOLD``
    (default 3; ``0`` = every batch with skipped > 0; ``-1`` = never),
    emit ONE ``WARN: drift write-back skipped <N> non-int decision_ids``
    line on ``sys.stderr`` at the END of the batch (NOT per skipped row).
    """
    backend = _default_save_backend()
    client = EngramClient(change_name, backend)
    success = 0
    skipped_total = 0
    for finding in report.findings:
        try:
            observation_id = int(finding.decision_id)
        except (TypeError, ValueError):
            # decision_id is not int-castable (e.g. legacy observations with
            # synthetic "unknown" id). Skip per-row without aborting.
            observability.increment(
                "drift_write_back_skipped_total",
                reason="non_int_decision_id",
            )
            skipped_total += 1
            continue
        try:
            client.update_observation_metadata(
                observation_id,
                {
                    "last_verified_at": _now_iso(),
                    "last_drift_class": finding.drift_class.value,
                },
            )
            success += 1
        except Exception:
            # Per-row error isolation — record and keep going.
            observability.increment("drift_write_back_failed_total")
            continue

    # REQ-59 S2: once-per-batch stderr WARN when skipped_total >= threshold.
    threshold = _get_skip_warn_threshold()
    if threshold >= 0 and skipped_total >= threshold:
        print(
            f"WARN: drift write-back skipped {skipped_total} "
            f"non-int decision_ids",
            file=sys.stderr,
        )
    return success


def _get_skip_warn_threshold() -> int:
    """Parse ``FLOW_DRIFT_SKIP_WARN_THRESHOLD`` env var; default 3.

    Per design D8:
    - Default 3 (3 or more skipped rows triggers one batch WARN).
    - ``0`` = WARN every batch with skipped_total > 0.
    - ``-1`` = WARN never.
    - Parse error (non-integer) falls back to default 3.
    """
    raw = os.environ.get("FLOW_DRIFT_SKIP_WARN_THRESHOLD")
    if raw is None:
        return 3
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 3


@main.group("drift", invoke_without_command=True)
@click.pass_context
def drift_group(ctx: click.Context) -> None:
    """Drift detection + read-side CLI namespace (REQ-10/11/14 + REQ-V1.2.4).

    Path A rename (v1.2.0d): the drift detection subcommand is exposed
    as ``flow drift run <change>`` (the explicit canonical form) and
    the drift events read-side lives under ``flow drift events
    {list,tail,stats}``. ``invoke_without_command=True`` keeps the
    bare ``flow drift --help`` flow working (shows subcommand list).
    """


@drift_group.command("run")
@click.argument("change_name")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Emit machine-readable JSON instead of a text table.")
@click.option("--include-obsolete", is_flag=True, default=False,
              help="Opt in to OBSOLETE classification (queries graphify).")
@click.option("--write-back", is_flag=True, default=False,
              help="Persist per-finding last_verified_at + last_drift_class metadata.")
@click.option("--since", default=None,
              help="Filter observations whose created_at >= this ISO 8601 timestamp.")
@click.option("--graph-json", "graph_json", default=None,
              type=click.Path(path_type=Path),
              help="Path to graph.json snapshot "
                   "(default: ~/.flow-engineering/graph.json).")
@click.option(
    "--snapshot",
    "snapshot_id",
    default=None,
    help="REQ-33: drift-pinned scan via a stored snapshot. "
         "Reads frozen observations + graph.json from the envelope instead of live disk.",
)
def drift_run(
    change_name: str,
    as_json: bool,
    include_obsolete: bool,
    write_back: bool,
    since: str | None,
    graph_json: str | None,
    snapshot_id: str | None,
) -> None:
    """Run drift detection for a change (REQ-10/11/14 + REQ-33).

    Exit codes: 0 = every binding STILL_VALID. 1 = any non-STILL_VALID class
    found. 2 = graph unavailable OR --since parse error. Exit 2 wins over 1.

    REQ-33 surface: ``--snapshot=<snap_id>`` activates the drift-pinned
    scan path. The snapshot's frozen observations + graph.json content
    are loaded via ``decision_drift.scan_change(snap_id=...)``; the live
    ``graph.json`` file is IGNORED. Without ``--snapshot`` the behaviour
    is byte-identical to the pre-change path (D13 non-breaking).
    """
    try:
        since_ts = _parse_since(since)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    if snapshot_id is not None:
        # REQ-33 drift-pinned path: graph_json_path is None (the snapshot
        # provides the graph implicitly); backend stays None too (the
        # snapshot's frozen observations become the implicit backend).
        # ``decision_drift.scan_change`` raises SnapshotGraphMissing when
        # the snapshot has no graph_json_content — surface it cleanly.
        graph_path = None
    else:
        graph_path = Path(graph_json) if graph_json else DEFAULT_GRAPH_JSON

    try:
        report = decision_drift.scan_change(
            change_name,
            graph_json_path=graph_path,
            include_obsolete=include_obsolete,
            since=since_ts,
            snap_id=snapshot_id,
        )
    except decision_drift.SnapshotGraphMissing as exc:
        click.echo(
            json.dumps(
                {
                    "error": "snapshot graph_json_content missing",
                    "snap_id": snapshot_id,
                    "detail": str(exc),
                },
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(2)

    # Observability: record the summary BEFORE returning so the counters
    # always reflect what was actually computed.
    observability.record_drift_summary(report)

    if write_back:
        _write_back_findings(report, change_name)

    if as_json:
        click.echo(
            json.dumps(
                _serialize_drift_report(report),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        click.echo(_render_drift_table(report))

    sys.exit(_drift_exit_code(report))


# ---------- REQ-V1.0.2 + REQ-V1.0.3: flow drift events read-side CLI (Path A nested) ----------


@drift_group.group("events")
def drift_events_group() -> None:
    """Read drift events from ~/.flow-engineering/drift_events.jsonl (REQ-V1.0.2 + REQ-V1.0.3 + REQ-V1.2.4).

    Path A rename (v1.2.0d): the read-side now lives at
    ``flow drift events {list,tail,stats}`` instead of the pre-v1.2
    top-level ``flow drift-events {list,tail,stats}``. The hyphenated
    form is preserved for one release cycle as a 1-release
    ``deprecated=True`` Click group alias (see ``drift_events_alias``
    below). Mirrors the ``flow metrics {summary,export,aggregate}``
    group pattern so the operator mental model transfers.
    """


def _format_drift_events_text(events: list[DriftEvent]) -> str:
    """Render a fixed-width text table from drift events (REQ-V1.0.2 D4).

    Mirrors the ``flow metrics summary`` text-table precedent at
    ``cli.py:999-1001`` (``name.ljust(name_width) ...``). Columns:
    ``change``, ``decision_id``, ``binding_id``, ``class``, ``detected_at``.
    Empty input renders as ``(no drift events)`` for operator clarity.
    """
    if not events:
        return "(no drift events)\n"
    headers = ("change", "decision_id", "binding_id", "class", "detected_at")
    rows: list[tuple[str, ...]] = [
        (
            ev.change,
            str(ev.decision_id),
            ev.binding_id,
            ev.event_class,
            f"{ev.detected_at:.0f}",
        )
        for ev in events
    ]
    widths = [
        max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(len(headers))
    ]
    sep = "  "
    header_line = sep.join(h.ljust(widths[i]) for i, h in enumerate(headers))
    rule_line = sep.join("-" * w for w in widths)
    data_lines = [
        sep.join(r[i].ljust(widths[i]) for i in range(len(headers))) for r in rows
    ]
    return "\n".join([header_line, rule_line, *data_lines]) + "\n"


def _parse_since_until(
    since: str | None, until: str | None,
) -> tuple[float | None, float | None]:
    """Parse ISO 8601 ``--since`` and ``--until`` flags into epoch seconds.

    Returns ``(since_ts, until_ts)`` where ``None`` means "no bound".
    Raises ``ValueError`` on malformed input; the CLI handler converts
    that to ``exit 2`` per D9.
    """
    since_ts: float | None = None
    until_ts: float | None = None
    if since is not None:
        since_ts = datetime.fromisoformat(since.replace("Z", "+00:00")).timestamp()
    if until is not None:
        until_ts = datetime.fromisoformat(until.replace("Z", "+00:00")).timestamp()
    return since_ts, until_ts


def _filter_drift_events(
    events: list[DriftEvent],
    *,
    since_ts: float | None,
    until_ts: float | None,
    change: str | None,
    event_class: str | None,
    limit: int | None,
) -> list[DriftEvent]:
    """Apply the documented filter set to a list of drift events."""
    out: list[DriftEvent] = []
    for ev in events:
        if since_ts is not None and ev.detected_at < since_ts:
            continue
        if until_ts is not None and ev.detected_at > until_ts:
            continue
        if change is not None and ev.change != change:
            continue
        if event_class is not None and ev.event_class != event_class:
            continue
        out.append(ev)
        if limit is not None and len(out) >= limit:
            break
    return out


def _read_drift_events_with_legacy_policy(
    log: DriftEventLog, *, strict: bool, log_path: Path
) -> list[DriftEvent]:
    """Read drift events from ``log``, handling legacy ``str`` decision_id lines.

    REQ-V1.1.2 S2 hardening: legacy ``str`` decision_id lines from
    pre-v1.0 sinks raise :class:`DriftEventLogLegacyFormatError`. The
    read-side CLI catches the error per-file:

    - ``--strict`` mode aborts on first legacy line with exit code 4 +
      CHANGELOG v1.0 ``sed`` migration hint.
    - Default mode emits a per-batch stderr WARN and returns ``[]``
      (legacy contamination preserved + visible to the operator).

    The CHANGELOG v1.0 ``sed`` migration is the documented upgrade path.
    """
    try:
        return log.read_all()
    except DriftEventLogLegacyFormatError as exc:
        if strict:
            click.echo(
                f"error: legacy format detected in {log_path}; {exc}\n"
                "Run the CHANGELOG v1.0 sed migration to fix in place.",
                err=True,
            )
            sys.exit(4)
        click.echo(
            f"warning: skipped legacy str decision_id lines in {log_path}; "
            "use --strict to abort. Run the CHANGELOG v1.0 sed migration "
            "to fix in place.",
            err=True,
        )
        return []


@drift_events_group.command(name="list")
@click.option("--since", default=None,
              help="Filter events with detected_at >= <iso> (ISO 8601).")
@click.option("--until", default=None,
              help="Filter events with detected_at <= <iso> (ISO 8601).")
@click.option("--change", default=None,
              help="Filter events for a specific change name.")
@click.option("--event-class", default=None,
              help="Filter events by drift class (e.g. LABEL_DRIFT).")
@click.option("--limit", type=int, default=None,
              help="Cap the number of returned events.")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json", "prometheus", "csv"]),
              help="Output format (default: text).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
def drift_events_list(
    since: str | None,
    until: str | None,
    change: str | None,
    event_class: str | None,
    limit: int | None,
    fmt: str,
    log_path: Path | None,
    strict: bool,
) -> None:
    """List drift events with optional filters (REQ-V1.0.2 + REQ-V1.1.2)."""
    try:
        since_ts, until_ts = _parse_since_until(since, until)
    except ValueError as exc:
        click.echo(f"Error: invalid --since/--until: {exc}", err=True)
        sys.exit(observability.EXIT_INVALID_VALUE)

    log = DriftEventLog(path=log_path) if log_path is not None else DriftEventLog()
    events = _read_drift_events_with_legacy_policy(
        log, strict=strict, log_path=log.path
    )
    events = _filter_drift_events(
        events,
        since_ts=since_ts,
        until_ts=until_ts,
        change=change,
        event_class=event_class,
        limit=limit,
    )

    if fmt == "text":
        click.echo(_format_drift_events_text(events))
        return
    if fmt == "json":
        click.echo(
            json.dumps([ev.to_json_dict() for ev in events], ensure_ascii=False, indent=2)
        )
        return
    if fmt == "csv":
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(["change", "decision_id", "binding_id", "class", "detected_at"])
        for ev in events:
            writer.writerow(
                [ev.change, ev.decision_id, ev.binding_id, ev.event_class, ev.detected_at]
            )
        click.echo(buf.getvalue(), nl=False)
        return
    if fmt == "prometheus":
        # REQ-V1.0.2 D4: per-change + per-event-class counts as a counter.
        lines = [
            "# HELP flow_drift_events_total Drift events recorded.",
            "# TYPE flow_drift_events_total counter",
        ]
        by_class: dict[str, int] = {}
        by_change: dict[str, int] = {}
        for ev in events:
            by_class[ev.event_class] = by_class.get(ev.event_class, 0) + 1
            by_change[ev.change] = by_change.get(ev.change, 0) + 1
        for cls, n in sorted(by_class.items()):
            lines.append(f'flow_drift_events_total{{event_class="{cls}"}} {n}')
        for change_name, n in sorted(by_change.items()):
            lines.append(f'flow_drift_events_total{{change="{change_name}"}} {n}')
        lines.append("# EOF")
        click.echo("\n".join(lines) + "\n")
        return


@drift_events_group.command(name="tail")
@click.option("--limit", type=int, default=10,
              help="Number of events to show, newest-first (default: 10).")
@click.option("--change", default=None,
              help="Filter events for a specific change name.")
@click.option("--event-class", default=None,
              help="Filter events by drift class (e.g. LABEL_DRIFT).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format (default: text).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
def drift_events_tail(
    limit: int,
    change: str | None,
    event_class: str | None,
    log_path: Path | None,
    fmt: str,
    strict: bool,
) -> None:
    """Show the last N drift events newest-first (REQ-V1.0.3 + REQ-V1.1.2).

    Mirrors the shell ``tail -n`` semantics: events are sorted by
    ``detected_at`` descending and the first ``--limit`` rows are
    rendered (default 10). Filters compose: ``--change`` and
    ``--event-class`` are applied BEFORE the limit so the operator sees
    the most recent N matching events, not the most recent N events
    post-filtered.
    """
    log = DriftEventLog(path=log_path) if log_path is not None else DriftEventLog()
    events = _read_drift_events_with_legacy_policy(
        log, strict=strict, log_path=log.path
    )
    events = sorted(events, key=lambda ev: ev.detected_at, reverse=True)
    events = _filter_drift_events(
        events,
        since_ts=None,
        until_ts=None,
        change=change,
        event_class=event_class,
        limit=limit,
    )

    if fmt == "text":
        click.echo(_format_drift_events_text(events))
        return
    click.echo(
        json.dumps([ev.to_json_dict() for ev in events], ensure_ascii=False, indent=2)
    )


@drift_events_group.command(name="stats")
@click.option("--change", default=None,
              help="Filter stats to a specific change name.")
@click.option("--since", default=None,
              help="Filter events with detected_at >= <iso> (ISO 8601).")
@click.option("--until", default=None,
              help="Filter events with detected_at <= <iso> (ISO 8601).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format (default: text).")
@click.option("--top-n", "top_n", type=int, default=5,
              help="Top-N decision_ids by frequency (default: 5).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
def drift_events_stats(
    change: str | None,
    since: str | None,
    until: str | None,
    log_path: Path | None,
    fmt: str,
    top_n: int,
    strict: bool,
) -> None:
    """Per-event-class + per-change + per-decision-id counts (REQ-V1.0.3 + REQ-V1.1.2).

    Renders an aligned text table with 3 sections (or a JSON envelope
    with ``by_event_class``, ``by_change``, ``by_decision_id`` keys).
    The ``by_decision_id`` array is sorted by frequency descending and
    capped at ``--top-n`` (default 5).
    """
    try:
        since_ts, until_ts = _parse_since_until(since, until)
    except ValueError as exc:
        click.echo(f"Error: invalid --since/--until: {exc}", err=True)
        sys.exit(observability.EXIT_INVALID_VALUE)

    log = DriftEventLog(path=log_path) if log_path is not None else DriftEventLog()
    events = _read_drift_events_with_legacy_policy(
        log, strict=strict, log_path=log.path
    )
    events = _filter_drift_events(
        events,
        since_ts=since_ts,
        until_ts=until_ts,
        change=change,
        event_class=None,
        limit=None,
    )

    by_event_class: dict[str, int] = {}
    by_change: dict[str, int] = {}
    by_decision_id: dict[int, int] = {}
    for ev in events:
        by_event_class[ev.event_class] = by_event_class.get(ev.event_class, 0) + 1
        by_change[ev.change] = by_change.get(ev.change, 0) + 1
        by_decision_id[ev.decision_id] = by_decision_id.get(ev.decision_id, 0) + 1
    top_decision_ids = Counter(by_decision_id).most_common(top_n)

    if fmt == "json":
        payload = {
            "by_event_class": by_event_class,
            "by_change": by_change,
            "by_decision_id": [
                {"decision_id": did, "count": n} for did, n in top_decision_ids
            ],
        }
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    sections = [
        ("Event class", by_event_class),
        ("Change", by_change),
    ]
    lines: list[str] = []
    for header_label, counts in sections:
        lines.append(f"## {header_label}")
        if counts:
            w = max(len(k) for k in counts)
            for k in sorted(counts):
                lines.append(f"  {k.ljust(w)}  {counts[k]}")
        else:
            lines.append("  (none)")
        lines.append("")
    lines.append(f"## Decision ID (top {top_n})")
    if top_decision_ids:
        w = max(len(str(did)) for did, _ in top_decision_ids)
        for did, n in top_decision_ids:
            lines.append(f"  {str(did).ljust(w)}  {n}")
    else:
        lines.append("  (none)")
    click.echo("\n".join(lines) + "\n")


# ---------- REQ-V1.2.4: 1-release DEPRECATED Click group alias for `flow drift-events` ----------


@main.group(
    name="drift-events",
    deprecated=True,
    help=(
        "DEPRECATED alias for ``flow drift events`` (REQ-V1.2.4). "
        "Use ``flow drift events {list,tail,stats}`` instead. "
        "This hyphenated form is REMOVED in v1.3."
    ),
)
def drift_events_alias_group() -> None:
    """Read drift events from ~/.flow-engineering/drift_events.jsonl.

    REQ-V1.2.4 1-release DEPRECATED Click group alias — preserved for
    backwards compatibility with the pre-v1.2 top-level
    ``flow drift-events`` surface. The canonical v1.2 surface is
    ``flow drift events {list,tail,stats}`` (nested under the new
    ``drift`` group). This alias emits a Click ``DeprecationWarning``
    on every invocation via ``deprecated=True`` and delegates to the
    canonical subcommands. REMOVED in v1.3 per the
    ``SnapshotGraphMissing`` v1.1 precedent.
    """


@drift_events_alias_group.command(name="list")
@click.option("--since", default=None,
              help="Filter events with detected_at >= <iso> (ISO 8601).")
@click.option("--until", default=None,
              help="Filter events with detected_at <= <iso> (ISO 8601).")
@click.option("--change", default=None,
              help="Filter events for a specific change name.")
@click.option("--event-class", default=None,
              help="Filter events by drift class (e.g. LABEL_DRIFT).")
@click.option("--limit", type=int, default=None,
              help="Cap the number of returned events.")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json", "prometheus", "csv"]),
              help="Output format (default: text).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
@click.pass_context
def drift_events_alias_list(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    change: str | None,
    event_class: str | None,
    limit: int | None,
    fmt: str,
    log_path: Path | None,
    strict: bool,
) -> None:
    """DEPRECATED alias for ``flow drift events list`` (REQ-V1.2.4)."""
    ctx.forward(
        drift_events_list,
        since=since, until=until, change=change, event_class=event_class,
        limit=limit, fmt=fmt, log_path=log_path, strict=strict,
    )


@drift_events_alias_group.command(name="tail")
@click.option("--limit", type=int, default=10,
              help="Number of events to show, newest-first (default: 10).")
@click.option("--change", default=None,
              help="Filter events for a specific change name.")
@click.option("--event-class", default=None,
              help="Filter events by drift class (e.g. LABEL_DRIFT).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format (default: text).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
@click.pass_context
def drift_events_alias_tail(
    ctx: click.Context,
    limit: int,
    change: str | None,
    event_class: str | None,
    log_path: Path | None,
    fmt: str,
    strict: bool,
) -> None:
    """DEPRECATED alias for ``flow drift events tail`` (REQ-V1.2.4)."""
    ctx.forward(
        drift_events_tail,
        limit=limit, change=change, event_class=event_class,
        log_path=log_path, fmt=fmt, strict=strict,
    )


@drift_events_alias_group.command(name="stats")
@click.option("--change", default=None,
              help="Filter stats to a specific change name.")
@click.option("--since", default=None,
              help="Filter events with detected_at >= <iso> (ISO 8601).")
@click.option("--until", default=None,
              help="Filter events with detected_at <= <iso> (ISO 8601).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format (default: text).")
@click.option("--top-n", "top_n", type=int, default=5,
              help="Top-N decision_ids by frequency (default: 5).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
@click.pass_context
def drift_events_alias_stats(
    ctx: click.Context,
    change: str | None,
    since: str | None,
    until: str | None,
    log_path: Path | None,
    fmt: str,
    top_n: int,
    strict: bool,
) -> None:
    """DEPRECATED alias for ``flow drift events stats`` (REQ-V1.2.4)."""
    ctx.forward(
        drift_events_stats,
        change=change, since=since, until=until, log_path=log_path,
        fmt=fmt, top_n=top_n, strict=strict,
    )


# ---------- Phase 3: flow workspace status ----------


_SDD_STACKS_REQUIRING_OPENSPEC = {"Python", "Go", "Rust"}


def _summarize_workspace_status(projects: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize workspace inventory into totals plus needs-attention rows."""
    needs_attention: list[dict[str, Any]] = []
    totals = {
        "projects": len(projects),
        "dirty": 0,
        "no_git": 0,
        "no_tests": 0,
        "has_openspec": 0,
        "has_graphify": 0,
        "has_engram": 0,
        "needs_attention": 0,
    }

    for project in projects:
        reasons: list[str] = []
        r1_triggered = False
        if project.get("dirty") is True:
            totals["dirty"] += 1
            if project.get("has_git") is True:
                reasons.append("R1: uncommitted work")
                r1_triggered = True
        if project.get("has_git") is False:
            totals["no_git"] += 1
            reasons.append("R2: no version control")
        if not project.get("test_commands"):
            totals["no_tests"] += 1
            reasons.append("R3: no tests detected")
        if project.get("has_openspec") is True:
            totals["has_openspec"] += 1
        elif project.get("stack") in _SDD_STACKS_REQUIRING_OPENSPEC:
            reasons.append("R4: SDD-adjacent stack missing openspec")
        if project.get("has_graphify") is True:
            totals["has_graphify"] += 1
        if project.get("has_engram") is True:
            totals["has_engram"] += 1
        if reasons:
            entry: dict[str, Any] = {
                "name": str(project.get("name", "")),
                "path": str(project.get("path", "")),
                "reasons": reasons,
            }
            # Additive field per REQ-WORKSPACE-DASHBOARD-R1-DETAIL — only
            # populated when R1 is in reasons; DS2 envelope consumers
            # ignore unknown keys. Defensive copy for list isolation.
            if r1_triggered:
                entry["dirty_files"] = list(project.get("dirty_files") or [])
            needs_attention.append(entry)

    totals["needs_attention"] = len(needs_attention)
    summary: dict[str, Any] = {"totals": totals, "needs_attention": needs_attention}
    return summary


def _workspace_status_envelope(
    root: Path,
    projects: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Return the deterministic v1 JSON envelope for workspace status."""
    return {
        "version": "1",
        "root": str(root),
        "totals": summary["totals"],
        "projects": projects,
        "needs_attention": summary["needs_attention"],
    }


def _workspace_status_tags(project: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    if project.get("dirty") is True:
        tags.append("[DIRTY]")
    if project.get("has_git") is False:
        tags.append("[NO-GIT]")
    if not project.get("test_commands"):
        tags.append("[NO TESTS]")
    if project.get("has_openspec") is False and project.get("stack") in _SDD_STACKS_REQUIRING_OPENSPEC:
        tags.append("[NO OPENSPEC]")
    return tags


def _render_workspace_status_text(
    root: Path,
    projects: list[dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    """Render human-readable workspace status text."""
    if not projects:
        return "(no projects to report)"

    lines = [f"WORKSPACE STATUS: {root}", ""]
    for project in projects:
        tags = _workspace_status_tags(project)
        suffix = f" {' '.join(tags)}" if tags else ""
        lines.append(f"- {project['name']} ({project.get('stack') or 'Unknown'}){suffix}")
        reasons = [
            item["reasons"]
            for item in summary["needs_attention"]
            if item["name"] == project["name"]
        ]
        for reason in (reasons[0] if reasons else []):
            lines.append(f"  - {reason}")
    totals = summary["totals"]
    lines.extend(
        [
            "",
            "SUMMARY",
            f"projects: {totals['projects']}",
            f"needs_attention: {totals['needs_attention']}",
            f"dirty: {totals['dirty']}",
            f"no_git: {totals['no_git']}",
            f"no_tests: {totals['no_tests']}",
            "[INFO: graphify probe is stubbed in v1]",
        ]
    )
    return "\n".join(lines)


@main.group(name="workspace")
def workspace_group() -> None:
    """Inspect workspace-level status synthesized from project inventory."""


@workspace_group.command(name="status")
@click.option(
    "--root",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Projects root directory. Defaults to FLOW_PROJECTS_ROOT, then platform default.",
)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit machine-readable workspace status JSON (v1 schema).",
)
def workspace_status(root: Path | None, json_flag: bool) -> None:
    """Show which workspace projects need attention."""
    root = _resolve_projects_root(root)
    if not root.is_dir():
        click.echo(f"projects root not found: {root}", err=True)
        raise SystemExit(1)

    subdirs = _iter_project_subdirs(root)
    projects = sorted(
        (_detect_project_markers(p) for p in subdirs),
        key=lambda d: d["name"],
    )
    summary = _summarize_workspace_status(projects)
    if json_flag:
        click.echo(
            json.dumps(
                _workspace_status_envelope(root, projects, summary),
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    click.echo(_render_workspace_status_text(root, projects, summary))


# REQ-WORKSPACE-DASHBOARD-* — `flow workspace dashboard` (Phase 5, PR3 wiring).
# Pattern #538 (one identity per command): NO ``--json`` flag here.
# Machine-readable output stays at ``flow workspace status --json``.


@workspace_group.command(name="dashboard")
@click.option("--filter", "filter_rules", multiple=True,
              type=click.Choice(["R1", "R2", "R3", "R4", "R5"], case_sensitive=False),
              help="Filter by needs-attention rules (repeatable).")
@click.option("--sort", default="name",
              type=click.Choice(["name", "path", "needs-count"], case_sensitive=False),
              help="Sort projects by field (default: name).")
@click.option("--no-color", is_flag=True, default=False,
              help="Disable Rich colors for CI / piping.")
def workspace_dashboard_cmd(
    filter_rules: tuple[str, ...], sort: str, no_color: bool
) -> None:
    """Render consolidated workspace state in terminal (read-only)."""
    from flow_engineering.dashboard import (
        fetch_archived_projects,
        fetch_project_list,
        fetch_status_summary,
        filter_by_rules,
        render_dashboard,
        sort_projects,
    )

    projects = fetch_project_list()
    status_envelope = fetch_status_summary()
    archived = fetch_archived_projects()
    needs_attention = status_envelope.get("needs_attention", [])

    if filter_rules:
        projects, needs_attention = filter_by_rules(projects, needs_attention, list(filter_rules))

    # Build needs_by_name from DS2 needs_attention (keyed by 'name' — see
    # REQ-DASHBOARD-SORT-DATA-FLOW + design §3). The 'name' key is the
    # canonical project identifier locked by the producer in
    # ``_summarize_workspace_status`` (cli.py:2913-2919). Empty-name
    # entries are dropped defensively.
    #
    # Inline-by-design: this builder is local to the single caller today;
    # extraction to ``build_needs_by_name`` is tracked as the
    # ``extract-build-needs-by-name-helper`` follow-up (trigger: Phase 5.2
    # TUI/web surface OR a 3rd caller of ``sort_projects``).
    needs_by_name: dict[str, list[str]] = {}
    for need in needs_attention:
        name = need.get("name", "")
        reasons = need.get("reasons", [])
        if name and isinstance(reasons, list):
            needs_by_name[name] = reasons

    projects = sort_projects(projects, sort, needs_by_name=needs_by_name)

    # Encoding reconfigure — Pattern #551. Falls back gracefully on legacy
    # Windows terminals / non-TTY pipes where ``reconfigure`` raises OSError.
    # ``sys.stdout`` is typed as ``TextIO | Any`` and TextIO has no
    # ``reconfigure`` method (Python 3.7+ on TextIOWrapper only); use
    # ``getattr`` so mypy strict is happy + non-TextIO streams are skipped.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        with contextlib.suppress(OSError):
            reconfigure(encoding="utf-8")
    # Width introspection: probe once, cache the result. Best-effort
    # auto-detect first, explicit fallback to 120 (matches snapshot test
    # precedent at ``tests/unit/test_dashboard.py:87``).
    probe = Console().size
    width_value = probe.width if probe.width and probe.width > 0 else 120

    console = Console(width=width_value, soft_wrap=True, no_color=no_color)
    console.print(render_dashboard(projects, status_envelope, archived, needs_attention, no_color=no_color))


# =============================================================================
# REQ-HYGIENE-* — `flow workspace {fix,archive,archived,restore}`
# =============================================================================
#
# Phase 4 CLI surface. These 4 Click verbs are a THIN wiring layer over the
# PR1-verified safety core in ``flow_engineering.workspace_hygiene`` (the
# orchestrator + pollution-protocol triple) and ``flow_engineering.registry``
# (the persistent v1 envelope). NO business logic lives here — only Click
# argument parsing, error mapping, and output formatting.
#
# Hard constraints honored:
#   - Dry-run is the DEFAULT (REQ-HYGIENE-DRY-RUN-DEFAULT).
#   - ``--yes`` is REQUIRED for any mutation (REQ-HYGIENE-FIX-SURFACE).
#   - ``--backup`` is REQUIRED for ``git init`` on a NON-EMPTY project
#     (REQ-HYGIENE-BACKUP-GATE-NONEMPTY).
#   - NO ``--json`` output flag (REQ-HYGIENE-NO-JSON-MVP).
#   - R1 dirty-git remediation is OUT OF SCOPE (REQ-HYGIENE-R1-EXPLICITLY-OUT).
#   - Phase 1/2/3 code paths are strictly READ-ONLY.


_BACKUP_ROOT: Path = Path.home() / ".flow-engineering" / "backups"
"""Backup root directory used by ``workspace fix``.

Resolved at module load (matches ``DEFAULT_REGISTRY_PATH`` precedent in
:mod:`flow_engineering.registry`). Tests that need an isolated backup root
monkeypatch ``_resolve_backup_root_for_cli`` rather than this constant.
"""


def _load_registry_for_cli() -> Registry:
    """Load the registry via the PR1 ``registry`` module.

    Re-evaluates ``Path.home()`` on every call (via ``registry_path()``) so
    tests that monkeypatch ``Path.home()`` are honored.
    """
    return load_registry()


def _resolve_backup_root_for_cli() -> Path:
    """Return the backup root, re-evaluating ``Path.home()`` per call.

    Matches the ``registry_path()`` pattern in ``registry.py:118``.
    """
    return Path.home() / ".flow-engineering" / "backups"


def _resolve_project_path(name: str, root: Path) -> Path:
    """Resolve a project name to its directory under ``root``.

    Raises :class:`click.UsageError` if the name is empty, if the resolved
    path is not a directory, or if the resolved path would land outside
    ``root`` (path-traversal guard).
    """
    if not name:
        raise click.UsageError("project name is required")
    target = (root / name).resolve()
    # Path-traversal guard: the resolved path must stay under root.
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise click.UsageError(
            f"project `{name}` resolves outside the projects root"
        ) from exc
    if not target.is_dir():
        raise click.UsageError(
            f"project `{name}` not found at {target}"
        )
    return target


def _workspace_hygiene_exit(exc: Exception) -> None:
    """Map a ``workspace_hygiene`` exception to stderr + exit 2.

    The PR1 helpers carry a ``user_message`` field for operator-friendly
    remediation hints. ``MutationGateError`` (PermissionError) and
    ``EmptyProjectError`` (ValueError) both expose it; ``RegistryError``
    does too. This helper centralizes the mapping so the 4 CLI commands
    stay consistent.
    """
    user_message = getattr(exc, "user_message", None) or str(exc)
    click.echo(user_message, err=True)
    raise SystemExit(2)


def _require_yes(yes: bool, command_name: str) -> None:
    """Gate helper: refuse mutations without ``--yes``.

    Prints a remediation hint to stderr and exits 2. Shared between
    ``workspace fix``, ``workspace archive``, and ``workspace restore``.
    """
    if not yes:
        click.echo(
            f"--yes required for `flow workspace {command_name}` mutations",
            err=True,
        )
        raise SystemExit(2)


def _format_archived_text_table(entries: list[ArchivedEntry]) -> str:
    """Render the archived list as a 3-column text table.

    Used by ``flow workspace archived``. NO JSON output (per
    REQ-HYGIENE-NO-JSON-MVP). The header is fixed; column widths adapt
    to the widest cell in each column.
    """
    if not entries:
        return "(no archived projects)"
    header = ("NAME", "ARCHIVED_AT", "REASON")
    rows: list[tuple[str, str, str]] = [header]
    for entry in entries:
        rows.append(
            (str(entry.name), str(entry.archived_at), str(entry.reason))
        )
    widths = [max(len(row[i]) for row in rows) for i in range(3)]
    lines: list[str] = []
    for row in rows:
        lines.append(
            f"{row[0]:<{widths[0]}}  {row[1]:<{widths[1]}}  {row[2]:<{widths[2]}}"
        )
    return "\n".join(lines)


@workspace_group.command(name="fix")
@click.argument("project")
@click.option(
    "--dry-run/--no-dry-run",
    default=True,
    help="Preview the plan without touching the filesystem or registry (default: dry-run).",
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Required to commit any mutation.",
)
@click.option(
    "--backup/--no-backup",
    default=False,
    help="Snapshot the project's pre-mutation files (required for non-empty projects).",
)
@click.option(
    "--root",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Projects root directory. Defaults to FLOW_PROJECTS_ROOT, then platform default.",
)
def workspace_fix_cmd(
    project: str,
    dry_run: bool,
    yes: bool,
    backup: bool,
    root: Path | None,
) -> None:
    """Initialize git on a project (REQ-HYGIENE-FIX-SURFACE).

    Dry-run is the default. ``--yes`` is required for any mutation.
    ``--backup`` is required when the project has user-visible files.

    Commit-intent semantics: any of ``--yes``, ``--no-dry-run``, or
    ``--backup`` flips the effective dry-run off. The orchestrator's
    mutation gate then fires when ``--yes`` is missing. This is what
    makes ``flow workspace fix X --backup`` refuse with a ``--yes``
    hint — the user signaled commit intent but didn't confirm.
    """
    projects_root = _resolve_projects_root(root)
    target = _resolve_project_path(project, projects_root)
    backup_root = _resolve_backup_root_for_cli()

    # Build a ProjectEntry from the read-only Phase 1 detector. The
    # orchestrator does NOT call ``_detect_project_markers`` itself; the
    # CLI is the seam where read-only metadata becomes a write-capable
    # ProjectEntry. ``has_git`` mirrors the detector so a re-fix on an
    # already-git project is idempotent (the orchestrator will still
    # rewrite the registry row, but won't error).
    markers = _detect_project_markers(target)
    entry = ProjectEntry(
        name=markers["name"],
        path=Path(markers["path"]),
        has_git=bool(markers["has_git"]),
        has_openspec=bool(markers["has_openspec"]),
        has_tests=bool(markers["test_commands"]),
        has_graphify=bool(markers["has_graphify"]),
        last_status_check=workspace_hygiene._now_iso_utc(),  # noqa: SLF001
    )

    # Commit intent: ``--yes``, ``--no-dry-run``, or ``--backup`` all flip
    # the effective dry-run off. The orchestrator's mutation gate fires
    # when the user wants to execute but didn't pass ``--yes``.
    commit_intent = yes or (not dry_run) or backup
    effective_dry_run = not commit_intent

    try:
        result = workspace_hygiene._apply_hygiene_rule(  # noqa: SLF001
            entry,
            "R2",
            dry_run=effective_dry_run,
            yes=yes,
            backup=backup,
            backup_root=backup_root,
        )
    except workspace_hygiene.MutationGateError as exc:
        _workspace_hygiene_exit(exc)
        return  # pragma: no cover — _workspace_hygiene_exit raises SystemExit
    except workspace_hygiene.EmptyProjectError as exc:
        _workspace_hygiene_exit(exc)
        return  # pragma: no cover
    except RegistryError as exc:
        _workspace_hygiene_exit(exc)
        return  # pragma: no cover

    # Render the result as a single-line summary. Dry-run is prefixed so
    # operators can see at a glance that nothing changed. When the target
    # project already has ``.git`` and is dirty (per
    # ``_detect_project_markers``), print the R1 OUT OF SCOPE hint so the
    # operator knows the orchestrator did NOT remediate the dirty state
    # (REQ-HYGIENE-R1-EXPLICITLY-OUT). This is informational; the
    # mutation still ran (``git init`` is idempotent on existing repos).
    prefix = "[DRY-RUN] " if result.dry_run else ""
    click.echo(
        f"{prefix}{result.action_taken} on {result.project}: "
        f"success={result.success}"
    )
    if markers["has_git"] and markers["dirty"]:
        click.echo(
            "R1 dirty-git is OUT OF SCOPE for Phase 4 MVP "
            "(worktree / index / untracked files preserved)."
        )

    # Mutation failures (e.g., ``git init`` rc != 0, verify failure,
    # restore-from-snapshot) are returned via ``HygieneResult(success=False,
    # error=...)`` instead of raising. Surface the error to stderr + exit 2
    # so callers (CI, scripts) can detect failure via exit code. The
    # pollution-protocol restore branch (``_verify_post_mutation`` False)
    # is one such path — per REQ-HYGIENE-POLLUTION-PROTOCOL.
    if not result.success:
        if result.error:
            click.echo(result.error, err=True)
        raise SystemExit(2)


@workspace_group.command(name="archive")
@click.argument("project")
@click.option(
    "--reason",
    default=None,
    help="Reason for archiving (defaults to 'manual archive').",
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Required to commit any mutation.",
)
def workspace_archive_cmd(project: str, reason: str | None, yes: bool) -> None:
    """Move a registered project to the archived list (REQ-HYGIENE-ARCHIVE-SURFACE).

    Registry-only operation — no filesystem change. ``--yes`` is required.
    """
    _require_yes(yes, "archive")
    try:
        registry = _load_registry_for_cli()
        new_registry = workspace_hygiene._archive_project(  # noqa: SLF001
            registry, project, reason
        )
        save_registry_atomic(new_registry)
    except RegistryError as exc:
        _workspace_hygiene_exit(exc)
        return  # pragma: no cover

    effective_reason = reason or "manual archive"
    click.echo(f"archived: {project} (reason: {effective_reason})")


@workspace_group.command(name="archived")
def workspace_archived_cmd() -> None:
    """List archived projects as a text table (REQ-HYGIENE-ARCHIVED-LISTING).

    NO ``--json`` flag (REQ-HYGIENE-NO-JSON-MVP). Always prints a 3-column
    text table (``NAME  ARCHIVED_AT  REASON``) or a clean empty message.
    """
    registry = _load_registry_for_cli()
    click.echo(_format_archived_text_table(list(registry.archived)))


@workspace_group.command(name="restore")
@click.argument("project")
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Required to commit any mutation.",
)
def workspace_restore_cmd(project: str, yes: bool) -> None:
    """Reverse a prior archive (REQ-HYGIENE-RESTORE-SURFACE).

    Moves the project from ``archived[]`` back to ``projects[]``.
    Registry-only — no filesystem change. ``--yes`` is required.
    """
    _require_yes(yes, "restore")
    try:
        registry = _load_registry_for_cli()
        new_registry = workspace_hygiene._restore_archived_project(  # noqa: SLF001
            registry, project
        )
        save_registry_atomic(new_registry)
    except RegistryError as exc:
        _workspace_hygiene_exit(exc)
        return  # pragma: no cover

    click.echo(f"restored: {project}")


# ---------- REQ-24: flow projects backfill ----------


@main.group(name="projects")
def projects_group() -> None:
    """Manage project tags and aliases (REQ-24, REQ-27).


    Subcommands:
    - ``ls``: list sibling projects with type markers (python/astro/next/rust/go/node).
    - ``backfill``: re-tag observations safely (dry-run default + --confirm gate).
    - ``alias``: append a rename record to ``project-aliases.json`` (REQ-27, lands in T1.10).
    """


# Subprocess seam for workspace-intelligence testability.
# Mirrors ``where._run_search`` (where.py:89). Production callers hit real
# ``subprocess.run`` with ``timeout=5s``; tests ``monkeypatch.setattr(cli,
# "_git", fake_git)`` to inject canned ``CompletedProcess`` instances.
# Returns the raw ``CompletedProcess``; callers branch on ``returncode``.
def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run ``git <args>`` with capture, text decoding, and a 5s timeout.

    Exit-code contract:
    - ``0`` → stdout parsed; caller decides field semantics.
    - non-zero → caller treats as "missing"; returns None / False.

    Diverges from ``_run_search`` precedent in two ways:
    1. Returns ``CompletedProcess`` (not bare ``str``) so the caller can
       branch on ``returncode`` for fields like ``remote``.
    2. Adds ``timeout=5s`` — git has higher hang risk than ``rg``/``grep``
       on Windows when the index is large. Fail-open default: caller
       catches ``TimeoutExpired`` / ``OSError`` per project.
    """
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        timeout=5,
    )


def _detect_stack(project_dir: Path) -> str:
    """Return stack enum from file probes (9-stack cascade per explore.md:30-41).

    Order: Python -> Astro (config wins over package.json substring) -> Node
    -> Flutter -> Nix -> WXT -> Rust -> Go -> Unknown. Astro/Next disambiguation
    rule: ``astro.config.{mjs,ts}`` wins over ``package.json`` substring match.
    """
    if (project_dir / "pyproject.toml").exists():
        return "Python"
    if (project_dir / "astro.config.mjs").exists() or (project_dir / "astro.config.ts").exists():
        return "Astro"
    if (project_dir / "package.json").exists():
        try:
            pkg = (project_dir / "package.json").read_text(encoding="utf-8", errors="replace")
        except OSError:
            return "Unknown"
        if "astro" in pkg:
            return "Astro"
        if "next" in pkg:
            return "Next"
        return "Node"
    if (project_dir / "pubspec.yaml").exists():
        return "Flutter"
    if (project_dir / "flake.nix").exists() or (project_dir / "default.nix").exists():
        return "Nix"
    if (project_dir / "wxt.config.ts").exists() or (project_dir / "wxt.config.js").exists():
        return "WXT"
    if (project_dir / "Cargo.toml").exists():
        return "Rust"
    if (project_dir / "go.mod").exists():
        return "Go"
    return "Unknown"


def _detect_test_commands(project_dir: Path, stack: str) -> list[str]:
    """Return detected test commands (per explore.md:46-54; first hit wins).

    Makefile ``test:`` target wins for Go/Python when present. Stack-specific
    fallbacks use ``package.json`` scripts.test for Astro/Next/WXT/Node, and
    Python uses ``uv run pytest`` when ``uv.lock`` is at root.
    """
    makefile = project_dir / "Makefile"
    if makefile.is_file():
        try:
            content = makefile.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""
        for line in content.splitlines():
            if line.strip().startswith("test:"):
                return ["make test"]
    if stack in ("Astro", "Next", "WXT", "Node"):
        return ["npm test"]
    if stack == "Python":
        if (project_dir / "uv.lock").exists():
            return ["uv run pytest"]
        if (project_dir / "pyproject.toml").exists():
            return ["python -m pytest"]
        return ["pytest"]
    if stack == "Go":
        return ["go test ./..."]
    if stack == "Flutter":
        return ["flutter test"]
    if stack == "Rust":
        return ["cargo test"]
    return []  # Nix / Unknown — no probe


def _has_pytest_config(project_dir: Path) -> bool:
    """Return True if the project has any pytest test infrastructure (R7 signal).

    Three signals are OR'd (REQ-WORKSPACE-HEALTH-R7-TESTS-INFRA):
      - ``tests/`` directory at the project root
      - ``pytest.ini`` file at the project root
      - ``[tool.pytest]`` section in ``pyproject.toml`` (parsed via stdlib
        ``tomllib``)

    The ``[tool.pytest]`` check is purely structural (key presence under
    ``tool``); it does NOT validate the section's contents. A malformed
    ``pyproject.toml`` returns ``False`` (no exception propagates, per
    Pattern #551).
    """
    if (project_dir / "tests").is_dir():
        return True
    if (project_dir / "pytest.ini").is_file():
        return True
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        import tomllib

        with pyproject.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, ValueError):
        return False
    return "pytest" in data.get("tool", {})


def _detect_project_markers(project_dir: Path) -> dict[str, Any]:
    """Detect workspace-intel fields + legacy markers for a project directory.

    Returns 14 keys: ``name``, ``path``, ``has_git``, ``branch``, ``dirty``,
    ``remote``, ``stack``, ``test_commands``, ``has_openspec``, ``has_graphify``
    (stub), ``has_engram`` (stub), ``type`` (lowercase back-compat for text
    table), ``has_flow``, ``readme_first_line``. Per-project error isolation:
    every git call is wrapped in try/except (OSError, subprocess.SubprocessError,
    subprocess.TimeoutExpired) — broken ``.git`` returns ``has_git=False``,
    never aborts the listing (REQ-FIELD-EXTENSION, design #439).
    """
    out: dict[str, Any] = {
        "name": project_dir.name,
        "path": str(project_dir.resolve()),
    }
    # Git presence + 3 derived fields via _git() seam (per-call isolation)
    has_git = (project_dir / ".git").exists()
    out["has_git"] = has_git
    out["branch"] = None
    out["dirty"] = None
    out["dirty_files"] = []
    out["remote"] = None
    if has_git:
        try:
            cp = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=project_dir)
            if cp.returncode == 0 and cp.stdout.strip():
                out["branch"] = cp.stdout.strip()
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass
        try:
            cp = _git("status", "--porcelain", cwd=project_dir)
            if cp.returncode == 0:
                # ``bool(cp.stdout.strip())`` is safe (only the truthiness
                # of the whole output matters); for ``dirty_files`` we MUST
                # preserve the leading-space 2-char XY status on each line,
                # so we splitlines() on the raw stdout (NOT on the stripped
                # version — that would drop the leading ``" "`` of the
                # first line).
                out["dirty"] = bool(cp.stdout.strip())
                out["dirty_files"] = cp.stdout.splitlines()
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass
        try:
            cp = _git("config", "--get", "remote.origin.url", cwd=project_dir)
            if cp.returncode == 0 and cp.stdout.strip():
                out["remote"] = cp.stdout.strip()
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass
    # Stack cascade + test commands (helpers above to keep body < 80 LOC)
    stack = _detect_stack(project_dir)
    out["stack"] = stack
    out["type"] = stack.lower() if stack != "Unknown" else ""
    out["test_commands"] = _detect_test_commands(project_dir, stack)
    # Workspace-intel fields (Phase 1: has_graphify/has_engram are stubs)
    out["has_openspec"] = (project_dir / "openspec" / "changes").is_dir()
    out["has_graphify"] = False
    # TODO(workspace-intelligence): Phase 2 — replace stub with Engram MCP/API call.
    # Always returns False; see --help note for user-facing warning.
    out["has_engram"] = False
    # Legacy markers (kept for text-table back-compat)
    out["has_flow"] = "yes" if (project_dir / "flow-engineering").is_dir() else ""
    readme = project_dir / "README.md"
    out["readme_first_line"] = ""
    if readme.is_file():
        try:
            first = readme.read_text(encoding="utf-8", errors="replace").splitlines()
            out["readme_first_line"] = first[0].lstrip("#").strip() if first else ""
        except OSError:
            pass
    # Health-advisor additive keys (14 -> 16; Pattern #548 — existing 14 keys
    # preserved; consumers ignore unknown keys per Pattern #538).
    # R6 source: README presence (file existence only; 0-byte is present).
    out["has_readme"] = (project_dir / "README.md").is_file() or (
        project_dir / "README.rst"
    ).is_file()
    # R7 source: pytest test infra (tests/ OR pytest.ini OR [tool.pytest]).
    out["has_pytest_config"] = _has_pytest_config(project_dir)
    return out


@projects_group.command(name="ls")
@click.option(
    "--root",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Projects root directory. Defaults to FLOW_PROJECTS_ROOT env var, "
    "then C:\\dev\\proyects on Windows or ~/dev/proyects on POSIX.",
)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit machine-readable JSON envelope (v1 schema) instead of text table. "
    "NOTE: 'has_engram' is currently a stub field and always reports false; "
    "full Engram integration is planned for a later phase.",
)
def projects_ls(root: Path | None, json_flag: bool) -> None:
    """List sibling projects with type markers (REQ-V0.1).

    Single-purpose cross-project discovery: lists immediate subdirectories
    of the projects root, shows detected type (python/astro/next/rust/go/node),
    whether `flow-engineering/` subdir exists, and the README first line.

    With ``--json``, emits a v1 envelope with 14 fields per project. The
    ``has_engram`` field is a Phase 1 stub and always reports false.

    NOTE: 'has_engram' is currently a stub field and always reports false;
    full Engram integration is planned for a later phase.

    Output is ASCII-safe (Windows cp1252 portable) per the `flow-where` MVP
    convention. Designed for quick "where's my X project?" questions
    without leaving the terminal.
    """
    if root is None:
        env_root = os.environ.get("FLOW_PROJECTS_ROOT")
        if env_root:
            root = Path(env_root)
        elif os.name == "nt":
            root = Path("C:\\dev\\proyects")
        else:
            root = Path("~/dev/proyects").expanduser()

    if not root.is_dir():
        click.echo(f"projects root not found: {root}", err=True)
        raise SystemExit(1)

    subdirs = _iter_project_subdirs(root)
    if not subdirs:
        if json_flag:
            envelope: dict[str, Any] = {
                "version": "1",
                "root": str(root),
                "projects": [],
            }
            click.echo(json.dumps(envelope, ensure_ascii=False, indent=2))
            return
        click.echo(f"(no subdirectories under {root})")
        return

    if json_flag:
        projects = sorted(
            (_detect_project_markers(p) for p in subdirs),
            key=lambda d: d["name"],
        )
        envelope = {
            "version": "1",
            "root": str(root),
            "projects": projects,
        }
        click.echo(json.dumps(envelope, ensure_ascii=False, indent=2))
        return

    # Compute column widths
    name_w = max(len("NAME"), max((len(p.name) for p in subdirs), default=4))
    type_w = max(len("TYPE"), max((len(_detect_project_markers(p)["type"] or "?") for p in subdirs), default=4))
    has_flow_w = len("FLOW")

    click.echo(f"{'NAME'.ljust(name_w)}  {'TYPE'.ljust(type_w)}  {'FLOW'.ljust(has_flow_w)}  README")
    click.echo(f"{'-' * name_w}  {'-' * type_w}  {'-' * has_flow_w}  {'-' * 20}")
    for p in subdirs:
        m = _detect_project_markers(p)
        ptype = m["type"] or "?"
        has_flow = m["has_flow"] or "-"
        readme = m["readme_first_line"] or ""
        click.echo(f"{p.name.ljust(name_w)}  {ptype.ljust(type_w)}  {has_flow.ljust(has_flow_w)}  {readme}")


@projects_group.command(name="backfill")
@click.option(
    "--dry-run",
    "dry_run_flag",
    is_flag=True,
    default=False,
    help="Preview only (DEFAULT behaviour; no writes).",
)
@click.option(
    "--confirm",
    "confirm_flag",
    is_flag=True,
    default=False,
    help="REQUIRED to write changes. Without --confirm the command is read-only.",
)
@click.option(
    "--project",
    "project_key",
    default=None,
    help="Restrict scope to a single project key. Required when --confirm is passed.",
)
@click.option(
    "--since",
    default=None,
    help="Only observations with created_at >= this ISO 8601 timestamp (lexicographic).",
)
def projects_backfill(
    dry_run_flag: bool,
    confirm_flag: bool,
    project_key: str | None,
    since: str | None,
) -> None:
    """Re-tag observations safely (REQ-24, design D3 safety gate + REQ-27 alias iteration).

    The default mode is a DRY-RUN preview: every observation that would be
    re-tagged is listed in the JSON report on stdout, but the database is
    NOT touched. To apply changes the caller MUST pass ``--confirm``.

    Scope (which observations are eligible for re-tagging):

    - With ``--project=<key>``: observations currently WITHOUT a project tag
      (i.e. ``project is None or ""``) AND observations currently tagged
      ``<key>`` (the alias-driven re-tag path: ``--project=<alias.old>``
      re-tags observations currently tagged ``<alias.old>`` to
      ``<alias.new>`` when an alias exists).
    - Without ``--project``: iterate the alias map (``project-aliases.json``)
      and re-tag every observation whose CURRENT ``project`` matches an
      ``alias.old`` to the corresponding ``alias.new``. This closes the
      batch B2 deviation: the previously-refused invocation now resolves
      via the alias map (REQ-24 scenario 5 + REQ-27 integration).

    Safety gate (REQ-24 + REQ-27):
    - ``--confirm`` is REQUIRED to write; ``--dry-run`` is the default
      and overrides ``--confirm`` (a ``--dry-run --confirm`` invocation
      still does no writes).

    Exit codes:
    - 0: success (dry-run completed OR --confirm applied changes OR
      no-op with empty alias map).
    - 2: invalid args (``--since`` parse error).

    JSON output shape::

        {
          "would_change": <int>,
          "would_skip": <int>,
          "changes": [
            {
              "observation_id": <int>,
              "current_tag": <str | null>,
              "proposed_tag": <str | null>,
              "action": "rename" | "skip_already_tagged" | "skip_no_match"
            },
            ...
          ]
        }

    On ``--confirm`` the report lists the same shape, but the ``action``
    for entries that were actually applied is ``"tagged"`` (instead of
    ``"rename"``) so downstream tooling can distinguish preview vs applied.
    """
    if since is not None:
        try:
            _parse_since(since)
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(2)

    from flow_engineering import project_aliases as _aliases

    backend = _default_save_backend()
    all_observations = list(backend.iter_observations())

    alias_records = _aliases.load_aliases()
    alias_map: dict[str, str] = {r["old"]: r["new"] for r in alias_records}

    candidates: list[dict[str, Any]]
    if project_key is not None:
        # Single-key scope (legacy REQ-24 + alias-key re-tag).
        candidates = [
            o
            for o in all_observations
            if (not o.get("project")) or o.get("project") == project_key
        ]
    else:
        # No --project: iterate the alias map (REQ-27 integration).
        candidates = [
            o
            for o in all_observations
            if o.get("project") in alias_map
        ]

    if since is not None:
        candidates = [
            o for o in candidates if str(o.get("created_at", "")) >= since
        ]

    would_change = 0
    would_skip = 0
    changes: list[dict[str, Any]] = []
    applied_action = "tagged" if confirm_flag else "rename"

    for obs in candidates:
        current_tag = obs.get("project")
        # Resolve the proposed tag for this row.
        if current_tag in alias_map:
            # Alias-driven re-tag (iteration path OR --project=<alias.old>).
            proposed_tag: str | None = alias_map[current_tag]
        elif project_key is not None and not current_tag:
            # Legacy REQ-24 untagged-observation path.
            proposed_tag = project_key
        else:
            proposed_tag = None

        if proposed_tag is None:
            action = "skip_no_match"
        elif proposed_tag == current_tag:
            action = "skip_already_tagged"
        else:
            action = applied_action

        change = {
            "observation_id": int(obs["id"]),
            "current_tag": current_tag,
            "proposed_tag": proposed_tag,
            "action": action,
        }
        changes.append(change)
        if action == applied_action:
            would_change += 1
            if confirm_flag and proposed_tag is not None:
                try:
                    _apply_tag(int(obs["id"]), proposed_tag, backend=backend)
                except Exception:
                    observability.increment("project_tag_backfill_failed_total")
                    continue
                observability.increment(
                    "project_tag_backfilled_total", from_=current_tag or "untagged"
                )
        else:
            would_skip += 1

    report = {
        "would_change": would_change,
        "would_skip": would_skip,
        "changes": changes,
    }
    click.echo(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0)


# ---------- REQ-27: flow projects alias ----------


@projects_group.command(name="alias")
@click.argument("old_key")
@click.argument("new_key")
def projects_alias(old_key: str, new_key: str) -> None:
    """Append a rename record to ``project-aliases.json`` (REQ-27).

    The alias map is the source of truth for renaming absorption:
    ``flow-image-generator-v2 → flow-image-generator-main`` is applied
    at every federated query so the user-facing contract treats the
    alias as a synonym.

    Exit codes:
    - 0: alias added (or already present — idempotent re-invoke).
    - 1: conflicting rewrite (existing alias for ``old_key`` already
      points to a different ``new_key``). The existing record is
      preserved unchanged so audit history is never silently lost.

    Stdout on success:
    - New alias: ``alias added: <old_key> -> <new_key>``.
    - Idempotent re-invoke: ``alias already present: <old_key> -> <new_key>``.

    On conflict, stderr reports the existing target so the user knows
    what to edit (or which entry to remove) before re-invoking.
    """
    from flow_engineering import project_aliases

    try:
        result = project_aliases.add_alias(old_key, new_key)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    status = result["status"]
    if status == "added":
        click.echo(f"alias added: {old_key} -> {new_key}")
        return
    if status == "already_present":
        click.echo(f"alias already present: {old_key} -> {new_key}")
        return
    # Defensive fallback — unknown statuses should not reach this point.
    click.echo(f"alias status: {status}", err=True)
    sys.exit(1)


# ---------- REQ-28..34: flow snapshot subcommand group (T1.5) ----------


def _build_snapshot_manager() -> SnapshotManager:
    """Construct a :class:`SnapshotManager` from the CLI defaults.

    Wires the snapshots dir (env override aware) + the default save
    backend so every ``flow snapshot`` subcommand gets a consistent
    facade without each command re-deriving the path.
    """
    return SnapshotManager(
        snapshots_dir=_resolve_snapshots_dir(),
        backend=_default_save_backend(),
    )


def _serialize_snapshot_meta(meta: SnapshotMeta) -> dict[str, Any]:
    """Project a ``SnapshotMeta`` dataclass into the REQ-29 JSON shape.

    REQ-29 scenario 1 requires exactly six keys: ``snap_id``,
    ``created_at``, ``trigger``, ``description``, ``obs_count``,
    ``size_bytes``. Extra fields are exposed as additional JSON keys
    (introspection for ``flow metrics`` consumers).
    """
    return {
        "snap_id": meta.id,
        "created_at": meta.created_at,
        "trigger": meta.trigger,
        "description": meta.description,
        "obs_count": meta.obs_count,
        "size_bytes": meta.size_bytes,
        "include_graph": meta.include_graph,
        "binding_count": meta.binding_count,
        "project_count": meta.project_count,
    }


def _snapshot_diff_to_dict(diff: SnapshotDiff) -> dict[str, Any]:
    """Project a ``SnapshotDiff`` dataclass into the REQ-31 JSON shape."""
    return diff.to_dict()


@main.group(name="snapshot")
def snapshot_group() -> None:
    """Manage immutable snapshots of the Engram observation graph (REQ-28..34).

    Subcommands:
    - ``create``  — write a new gzipped JSON snapshot.
    - ``list``    — list existing snapshots (newest first).
    - ``show``    — render a snapshot's full envelope.
    - ``diff``    — diff two snapshots OR snapshot-vs-live.
    - ``rollback`` — restore Engram state to a snapshot (with safety).
    - ``prune``   — retention-driven deletion (lands in T1.6).

    Exit-code conventions mirror the rest of the CLI: 0 = success, 2 =
    invalid args, 3 = safety refusal (rollback without ``--confirm``).
    """


@snapshot_group.command(name="create")
@click.option(
    "--description",
    "description_text",
    default="",
    help="Free-text note stored in the envelope's description field.",
)
@click.option(
    "--no-include-graph",
    "no_include_graph",
    is_flag=True,
    default=False,
    help="Exclude graph_state.graph_json_content from the envelope. "
         "Drift-pinned scans of such snapshots will refuse.",
)
@click.option(
    "--project",
    "project_key",
    default=None,
    help="Restrict to a single project at READ time only (D5). "
         "v1 snapshots always capture the full DB.",
)
def snapshot_create(
    description_text: str,
    no_include_graph: bool,
    project_key: str | None,
) -> None:
    """Write a new snapshot of the current Engram state (REQ-28).

    Default ``trigger='manual'``; auto-rollback-safety snapshots are
    written by ``flow snapshot rollback`` with ``trigger='rollback_safety'``.
    The snapshot file is written atomically (tempfile + Path.replace)
    so a crash mid-write cannot corrupt the directory.
    """
    manager = _build_snapshot_manager()
    snap_id = manager.create(
        description=description_text,
        trigger="manual",
        include_graph=not no_include_graph,
    )
    click.echo(snap_id)


@snapshot_group.command(name="list")
@click.option(
    "--since",
    default=None,
    help="Filter to snapshots with created_at >= this ISO 8601 timestamp.",
)
@click.option(
    "--limit",
    "limit",
    type=int,
    default=None,
    help="Maximum number of snapshots to return (default: 50).",
)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit the snapshot list as a JSON array (REQ-29 spec mandate; default output is also JSON for scriptability).",
)
def snapshot_list(since: str | None, limit: int | None, json_flag: bool) -> None:
    """List snapshots in reverse chronological order (REQ-29).

    Output is a JSON array of ``SnapshotMeta`` records with the 6 keys
    required by the spec (snap_id, created_at, trigger, description,
    obs_count, size_bytes) plus introspection fields. Empty dir ⇒ ``[]``.
    """
    manager = _build_snapshot_manager()
    entries = manager.list(since=since, limit=limit)
    payload = [_serialize_snapshot_meta(e) for e in entries]
    click.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@snapshot_group.command(name="show")
@click.argument("snap_id")
def snapshot_show(snap_id: str) -> None:
    """Render a snapshot's full envelope as pretty-printed JSON (REQ-30).

    On sha256 mismatch OR unknown ``snap_id`` the command exits non-zero
    with a JSON error object on stderr.
    """
    manager = _build_snapshot_manager()
    try:
        envelope = manager.show(snap_id)
    except SnapshotEnvelopeError as exc:
        click.echo(
            json.dumps(
                {"error": str(exc), "snap_id": snap_id},
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(2)
    click.echo(json.dumps(envelope, ensure_ascii=False, indent=2))


@snapshot_group.command(name="diff")
@click.argument("snap_id_a")
@click.argument("snap_id_b", required=False, default=None)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit the diff as a structured JSON object (REQ-31 spec mandate; default output is also JSON).",
)
def snapshot_diff(
    snap_id_a: str, snap_id_b: str | None, json_flag: bool
) -> None:
    """Diff two snapshots OR a snapshot against LIVE state (REQ-31).

    Two calling forms:

    - ``flow snapshot diff <a> <b>`` — diff two stored snapshots.
    - ``flow snapshot diff <a>`` — diff ``<a>`` against LIVE state
      (the snapshot-vs-live extension per REQ-31).

    Output is a structured JSON object with ``added``, ``removed``,
    ``modified``, ``unchanged_count``, ``summary`` keys.
    """
    manager = _build_snapshot_manager()
    try:
        diff = manager.diff(snap_id_a, snap_id_b)
    except SnapshotEnvelopeError as exc:
        click.echo(
            json.dumps(
                {"error": str(exc), "snap_id_a": snap_id_a, "snap_id_b": snap_id_b},
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(2)
    click.echo(
        json.dumps(_snapshot_diff_to_dict(diff), ensure_ascii=False, indent=2)
    )


@snapshot_group.command(name="rollback")
@click.argument("snap_id")
@click.option(
    "--confirm",
    "confirm_flag",
    is_flag=True,
    default=False,
    help="REQUIRED to write changes. Without --confirm the command refuses.",
)
@click.option(
    "--force",
    "force_flag",
    is_flag=True,
    default=False,
    help="Override conflict detection (DANGEROUS).",
)
def snapshot_rollback(
    snap_id: str, confirm_flag: bool, force_flag: bool
) -> None:
    """Restore the Engram state to match ``snap_id`` (REQ-32).

    Two-phase commit (D11):

    1. Auto-safety snapshot of CURRENT live state (trigger=rollback_safety).
    2. Atomic SQLite ``BEGIN IMMEDIATE`` apply of the target snapshot.

    Without ``--confirm`` the command refuses with exit code 3 and a
    JSON error on stderr. With ``--confirm`` but conflicts present,
    the command refuses with exit code 2 unless ``--force`` is also
    passed (which emits a stderr warning + applies anyway).
    """
    manager = _build_snapshot_manager()
    try:
        result = manager.rollback(
            snap_id, confirm=confirm_flag, force=force_flag
        )
    except RollbackRefusedError as exc:
        click.echo(
            json.dumps(exc.payload, ensure_ascii=False),
            err=True,
        )
        sys.exit(3)
    except RollbackConflictError as exc:
        click.echo(
            json.dumps(exc.payload, ensure_ascii=False),
            err=True,
        )
        sys.exit(2)
    except SnapshotEnvelopeError as exc:
        click.echo(
            json.dumps(
                {"error": str(exc), "snap_id": snap_id},
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(2)
    click.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


@snapshot_group.command(name="prune")
@click.option(
    "--keep-last",
    "keep_last",
    type=int,
    default=None,
    help="Keep the N most-recent snapshots; delete the rest (count filter).",
)
@click.option(
    "--keep-days",
    "keep_days",
    type=int,
    default=None,
    help="Keep snapshots newer than N days (age filter).",
)
@click.option(
    "--max-total-size-mb",
    "max_total_size_mb",
    type=int,
    default=None,
    help="Delete oldest-first until total size <= N MB (size filter).",
)
@click.option(
    "--confirm",
    "confirm_flag",
    is_flag=True,
    default=False,
    help="REQUIRED to actually delete. Without --confirm the command is "
         "dry-run and prints the would-delete list.",
)
@click.option(
    "--force",
    "force_flag",
    is_flag=True,
    default=False,
    help="Override the most-recent snapshot safety net (DANGEROUS).",
)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit the PruneResult as a JSON object on stdout.",
)
def snapshot_prune(
    keep_last: int | None,
    keep_days: int | None,
    max_total_size_mb: int | None,
    confirm_flag: bool,
    force_flag: bool,
    json_flag: bool,
) -> None:
    """Retention-driven deletion of snapshot files (REQ-34).

    Three retention filters are OR-combined: ``--keep-last`` (count),
    ``--keep-days`` (age), ``--max-total-size-mb`` (size). At least ONE
    MUST be supplied; otherwise the command refuses with exit code 2.

    Default (no ``--confirm``) is dry-run: ``PruneResult.dry_run`` is True
    and NO files are touched. The candidate set is printed to stdout as
    a ``"would delete"`` list so the operator can preview the impact.

    With ``--confirm``, the candidate set is deleted and the
    ``PruneResult.deleted`` list is the actually-applied deletions.

    Two safety invariants (REQ-34 D10) are non-negotiable:

    - The most-recent snapshot is NEVER deleted (unless ``--force``).
    - Pinned snapshots are NEVER deleted.

    Exit codes: 0 on success (including dry-run), 2 on no-filter /
    safety-gate, 4 on ``PruneSafetyGateError``.
    """
    manager = _build_snapshot_manager()
    try:
        result = manager.prune(
            keep_last=keep_last,
            keep_days=keep_days,
            max_total_size_mb=max_total_size_mb,
            confirm=confirm_flag,
            force=force_flag,
        )
    except PruneNoFilterError as exc:
        click.echo(
            json.dumps({"error": str(exc)}, ensure_ascii=False),
            err=True,
        )
        sys.exit(2)
    except PruneSafetyGateError as exc:
        click.echo(
            json.dumps(exc.payload, ensure_ascii=False),
            err=True,
        )
        sys.exit(4)

    if json_flag:
        click.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    # Human-readable default output. Dry-run prints "would delete"; apply
    # prints "deleted" so the operator can see what changed.
    if result.dry_run:
        click.echo(f"DRY-RUN: would delete {len(result.would_delete)} snapshots")
        click.echo(f"  reason: {result.reason!r}")
        for sid in result.would_delete:
            click.echo(f"  - {sid}")
        click.echo(f"would keep: {len(result.would_keep)}")
        return

    click.echo(f"deleted {len(result.deleted)} snapshots")
    click.echo(f"  reason: {result.reason!r}")
    for sid in result.deleted:
        click.echo(f"  - {sid}")
    click.echo(f"freed_bytes: {result.freed_bytes}")
    click.echo(f"kept: {len(result.would_keep)}")


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
            f"graphify_decision: {'applied' if result.graphify_decision.applied else 'skipped'}",
        )
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()



