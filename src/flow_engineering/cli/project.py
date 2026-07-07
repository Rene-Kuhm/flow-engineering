"""Projects group extracted from cli/__init__.py (v1.3-cli-split, Slice 3).

Hosts the ``flow projects`` Click group and its subcommands (ls,
backfill, alias), plus the private helpers used internally by those
commands (``_git``, ``_detect_stack``, ``_detect_test_commands``,
``_has_pytest_config``, ``_detect_project_markers``). The body below
is a verbatim relocation from ``cli/__init__.py`` lines 2815-3340
(post-Slice-2; pre-Slice-1+2 equivalent lines 3575-4101 per tasks.md
T-3) -- behavior MUST match pre-split exactly. Top-level imports
were added here because a module cannot see names that live in
``cli/__init__.py``'s import block; the relocated body references
the same names it did before.

Lazy imports inside ``projects_backfill`` resolve ``_parse_since``
and ``_default_save_backend`` from ``cli/__init__.py`` at
function-call time. Those helpers are defined later in
``__init__.py`` and cannot be bound at module-import time without a
circular import (workspace.py precedent applies for
``_detect_project_markers``).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import click

from flow_engineering import observability
from flow_engineering.cli import main  # noqa: F401  (parent group; see design §6)
from flow_engineering.cli._shared import _iter_project_subdirs
from flow_engineering.project_detector import apply_tag as _apply_tag


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
    # Lazy import: ``_git`` is re-exported by ``cli/__init__.py`` (Slice 3),
    # and tests patch ``flow_engineering.cli._git`` via monkeypatch. Re-fetching
    # at function entry makes the lookup resolve to the (patched) ``cli._git``
    # rather than the original ``project._git``. Same pattern as Slice 2's lazy
    # import of ``_detect_project_markers`` inside ``workspace.py``.
    from flow_engineering.cli import _git  # noqa: F401

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
    # Lazy imports: ``_parse_since`` was relocated to ``cli.drift`` in
    # v1.3-cli-split Slice 4 (was previously in ``cli/__init__.py`` line
    # 2014) and ``_default_save_backend`` remains in ``cli/__init__.py``
    # (line 839). Both cannot be bound at project.py module-import time
    # without a circular import. Same pattern as workspace.py (Slice 2)
    # for ``_detect_project_markers`` and drift.py (Slice 4) for
    # ``_default_save_backend`` + ``EngramClient``.
    if since is not None:
        try:
            from flow_engineering.cli.drift import _parse_since  # noqa: F401

            _parse_since(since)
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(2)

    from flow_engineering import project_aliases as _aliases
    from flow_engineering.cli import _default_save_backend  # noqa: F401

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
