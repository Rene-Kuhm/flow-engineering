"""Workspace group extracted from cli/__init__.py (v1.3-cli-split, Slice 2).

Hosts the ``flow workspace`` Click group and its subcommands (status,
dashboard, health, fix, archive, archived, restore), plus the private
helpers used internally by those commands. The body below is a verbatim
relocation from ``cli/__init__.py`` lines 2803-3483 (post-Slice-1;
pre-Slice-1 equivalent lines 2894-3574 per tasks.md) -- behavior MUST
match pre-split exactly. Top-level imports were added here because a
module cannot see names that live in ``cli/__init__.py``'s import
block; the relocated body references the same names it did before.
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import Any, cast

import click

from flow_engineering import workspace_hygiene
from flow_engineering.cli import main  # noqa: F401  (parent group; see design §6)
from flow_engineering.cli._shared import (
    _iter_project_subdirs,
    _resolve_projects_root,
)
from flow_engineering.registry import (
    ArchivedEntry,
    ProjectEntry,
    Registry,
    RegistryError,
    load_registry,
    save_registry_atomic,
)


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
    # Lazy import: ``_detect_project_markers`` is defined later in
    # ``cli/__init__.py`` (projects slice, post-Slice-2) so we cannot
    # bind it at workspace.py import time without a circular import.
    # Resolved here, after __init__.py has finished loading.
    from flow_engineering.cli import _detect_project_markers  # noqa: F401

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
    # Lazy import from ``flow_engineering.cli`` (NOT ``rich.console``) so
    # tests that ``monkeypatch.setattr(cli, "Console", ...)`` keep working:
    # the local binding resolves through ``cli_mod`` at call time, picking
    # up the patched class. Using ``rich.console.Console`` directly here
    # would freeze the reference at import time and bypass the patch.
    from flow_engineering.cli import Console  # noqa: F401  (monkeypatch seam)

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


# REQ-WORKSPACE-HEALTH-* (PR4a) — `flow workspace health` (Phase 6, PR4 wiring).
# v1.3-e migration: this block moves to cli/workspace.py per design §v1.3-e.
#
# Pure CLI glue over the PR3-locked library surface in
# ``flow_engineering.health`` (fetch_workspace_health, filter_health_by_rules,
# _compute_totals) and ``flow_engineering.health_render`` (text + JSON
# renderers). PR4a wires the handler skeleton + --root + --json; PR4b adds
# the text render branch, --filter, and --no-color.


_HEALTH_FILTER_CHOICES: tuple[str, ...] = ("R6", "R7", "R8", "R9")


def _normalize_filter_rules(
    ctx: click.Context, param: click.Parameter, value: tuple[str, ...]
) -> tuple[str, ...]:
    """Normalize ``--filter`` tokens: split comma-separated AND validate against R6-R9.

    REQ-WORKSPACE-HEALTH-FILTER-1/2 (PR4b): Click's built-in
    ``multiple=True`` only accepts repeated flags (``--filter R6 --filter R7``);
    it does NOT auto-split comma-separated values (``--filter R6,R7``). The
    spec mandates both forms MUST be equivalent, so we split + validate in
    this callback (replacing ``click.Choice`` so the manual check happens
    AFTER splitting). Click's ``BadParameter`` machinery surfaces unknown
    tokens at parse time (exit 2) before any ``fetch_workspace_health``
    side effect (REQ-FILTER-1 parse-time rejection).
    """
    if not value:
        return ()
    flat: list[str] = []
    for raw in value:
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            normalized = token.upper()
            if normalized not in _HEALTH_FILTER_CHOICES:
                allowed = ", ".join(_HEALTH_FILTER_CHOICES)
                raise click.BadParameter(
                    f"{token!r} is not one of {allowed}.",
                    ctx=ctx,
                    param=param,
                )
            flat.append(normalized)
    return tuple(flat)


@workspace_group.command(name="health")
@click.option(
    "--root",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Projects root. Defaults to FLOW_PROJECTS_ROOT, then platform default.",
)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit byte-deterministic v1 JSON envelope.",
)
@click.option(
    "--filter",
    "filter_rules",
    multiple=True,
    type=click.STRING,
    callback=_normalize_filter_rules,
    help=(
        "Filter by rule (repeatable). Comma-separated or repeated flags: "
        "R6=missing-README, R7=missing-tests-infra, R8=missing-openspec, "
        "R9=committed-tooling-dirs."
    ),
)
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    help="Disable ANSI color codes for deterministic output.",
)
def workspace_health_cmd(
    root: Path | None,
    json_flag: bool,
    filter_rules: tuple[str, ...],
    no_color: bool,
) -> None:
    """Workspace health summary (per-project R6-R9 triggers + recommendations)."""
    from io import StringIO

    from rich.console import Console

    from flow_engineering import health, health_render

    resolved = _resolve_projects_root(root)
    if not resolved.is_dir():
        click.echo(f"projects root not found: {resolved}", err=True)
        raise SystemExit(2)

    envelope = health.fetch_workspace_health(resolved)

    # REQ-WORKSPACE-HEALTH-FILTER-1/2/3 (PR4b): output-only rule filter
    # (never mutates detection). Recompute ``totals`` against the filtered
    # projects per PR3 ``_compute_totals`` invariant. Empty ``filter_rules``
    # is a passthrough — does not mutate the envelope.
    if filter_rules:
        filtered_projects = health.filter_health_by_rules(
            cast(list[dict[str, object]], envelope["projects"]),
            list(filter_rules),
        )
        envelope = {
            **envelope,
            "projects": filtered_projects,
            "totals": health._compute_totals(filtered_projects),
        }

    if json_flag:
        click.echo(json.dumps(envelope, ensure_ascii=False, indent=2))
        return

    # REQ-WORKSPACE-HEALTH-TEXT-1/2/3/4 (PR4b): delegate to the PR3-locked
    # renderer (``render_workspace_health_text``) and capture its output
    # in a per-call StringIO Console (Constitution Article V: no globals).
    # REQ-WORKSPACE-HEALTH-NOCOLOR-1/2: ``--no-color`` flows through to the
    # renderer's Console as the byte-determinism seam (no ANSI escapes).
    buffer = StringIO()
    rendered = health_render.render_workspace_health_text(
        envelope, console=Console(no_color=no_color, file=buffer, width=120)
    )
    click.echo(rendered)


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
    # Lazy import: ``_detect_project_markers`` is defined later in
    # ``cli/__init__.py`` (projects slice, post-Slice-2) so we cannot
    # bind it at workspace.py import time without a circular import.
    # Resolved here, after __init__.py has finished loading.
    from flow_engineering.cli import _detect_project_markers  # noqa: F401

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

