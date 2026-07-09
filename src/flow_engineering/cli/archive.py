"""Archive group extracted from cli/rotation.py + cli/__init__.py (v1.3-cli-split, Slice 8/8, FINAL).

Hosts the ``flow archive`` Click group + its two subcommands:

- ``rotate`` -- list entries in ``openspec/changes/archive/`` older than
  ``--older-than`` days. Read-only (REQ-V1.3.4). The implementation
  below was relocated verbatim from ``cli/rotation.py`` (161 LOC whole
  file); the rename to ``archive.py`` makes the module name match the
  Click group it registers. The old ``cli/rotation.py`` path is now a
  3-line back-compat shim that re-exports ``rotate_cmd``,
  ``_candidate_entries`` and ``_entry_mtime`` so any external caller
  of ``from flow_engineering.cli.rotation import X`` continues to work.

- ``change`` -- archive a change (ARCHIVING -> DONE) and trigger the
  graph rebuild (v1.3.0-alpha BREAKING rewrite of the v1.2
  ``flow archive <change>`` surface, per spec REQ-V1.2.4 precedent for
  ``flow drift run``). The implementation below was relocated verbatim
  from ``cli/__init__.py`` lines 1568-1614 (post-Slice-1..7; pre-Slice-1
  equivalent lines 5284-5335 per tasks.md T-8).

The dead ``archive()`` function at ``cli/__init__.py:357`` is preserved
VERBATIM in ``__init__.py`` per tasks.md r4 (out-of-scope). Do NOT move
it here.

The ``archive()`` dead function and this module's ``archive_change_cmd``
are distinct functions: ``archive()`` is an unregistered, dead Click
command at the top level of ``cli/__init__.py`` (not registered with
``main``), while ``archive_change_cmd`` is the live subcommand registered
under the ``archive`` group via ``@archive_group.command(name="change")``
below. They are kept separate per tasks.md r4 ("Dead-code removal
(``archive()`` function at pre-split ``__init__.py:320-349``) ... Out
of Scope").

Behavior MUST match pre-Slice-8 exactly. The visible CLI surface is
unchanged: ``flow archive rotate [--older-than N] [--dry-run/--no-dry-run]
[--format yaml|json]`` and ``flow archive change <change> [--in target]
[--diff text] [--no-graphify]``.

Read-only contract for the ``rotate`` subcommand (enforced by
``tests/integration/test_rotation_readonly_contract.py`` via AST grep):
no calls to ``shutil.move``, ``os.rename``, ``Path.rename``, or
``git mv`` may appear anywhere in this file.

Top-level imports of ``_enforce_min_skill_versions_or_exit`` from
``flow_engineering.cli._shared`` mirror the workspace.py / project.py
precedent (Slice 2 + Slice 3): ``_shared`` does not depend on any
submodule, so the top-level import is safe and avoids a circular import.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import yaml

from flow_engineering.cli import main  # noqa: F401  (parent group; see design §6)
from flow_engineering.cli._shared import _enforce_min_skill_versions_or_exit
from flow_engineering.orchestrator import archive_change

# Paths resolved at call time (not import time) so tests can chdir freely.
# Constants. archive_dir is <repo>/openspec/changes/archive when invoked
# from the repo root; the parent indices below are documented on purpose
# because they participate in two different computations below.
#
#   archive_dir = Path("openspec/changes/archive")
#       archive_dir.parents[0]  = Path("openspec/changes")
#       archive_dir.parents[1]  = Path("openspec")    <-- output relative_to base
#       archive_dir.parents[2]  = Path(".")           <-- repo root (git cwd)
#
# Keeping the two indices as named constants makes each usage explicit so a
# future reader does not have to re-derive which `parents[N]` resolves to what.

_REPO_PARENT_DEPTH = 2  # archive_dir.parents[2] = repo root (cwd for ``git log``)
_OUTPUT_RELATIVE_PARENT = (
    1  # archive_dir.parents[1] = "openspec/" (relative-to base for output paths)
)

_SECONDS_PER_DAY = 86400  # seconds in one day (epoch ⇄ days conversions)
_GIT_FALLBACK_THRESHOLD_DAYS = 30


def _entry_mtime(entry: Path) -> float:
    """Return entry mtime as Unix epoch. Falls back to ``git log -1 --format=%ct``
    when the filesystem mtime is more than 30 days newer than the git
    timestamp (Windows + ``git checkout`` skew).

    Returns 0.0 when neither source yields a timestamp.
    """
    try:
        fs_mtime = entry.stat().st_mtime
    except OSError:
        fs_mtime = 0.0

    proposal = entry / "proposal.md"
    if proposal.exists():
        try:
            repo_root = entry.parents[_REPO_PARENT_DEPTH]
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct", str(proposal)],
                capture_output=True,
                text=True,
                cwd=str(repo_root),
                timeout=2,
            )
            git_ts = result.stdout.strip()
            if git_ts and git_ts.isdigit():
                git_mtime = float(git_ts)
                # If fs_mtime is way more recent than git (git checkout skew), prefer git.
                if fs_mtime > git_mtime + (_GIT_FALLBACK_THRESHOLD_DAYS * _SECONDS_PER_DAY):
                    return git_mtime
        except (subprocess.SubprocessError, OSError):
            pass

    return fs_mtime


def _candidate_entries(archive_dir: Path, older_than_days: int) -> list[dict[str, Any]]:
    """Return list of ``{path, mtime_days_ago, sha256}`` dicts for entries
    older than ``older_than_days``.

    Output ``path`` is the entry's path **relative to the ``openspec/``
    directory** (e.g. ``changes/archive/2026-06-25-decision-code-linking``).
    This is by design: ``openspec/`` is the operator-facing root, and the
    rendered output is meant to be copy-pasteable into the canonical SDD
    location paths (the ``relative_to`` base is captured by the
    ``_OUTPUT_RELATIVE_PARENT`` constant).
    """
    if not archive_dir.exists():
        return []
    now_ts = datetime.now(tz=UTC).timestamp()
    cutoff = now_ts - older_than_days * _SECONDS_PER_DAY
    candidates: list[dict[str, Any]] = []
    for entry in sorted(archive_dir.iterdir()):
        if not entry.is_dir():
            continue
        mtime = _entry_mtime(entry)
        if mtime <= 0 or mtime >= cutoff:
            continue
        proposal = entry / "proposal.md"
        sha = ""
        if proposal.exists():
            sha = hashlib.sha256(proposal.read_bytes()).hexdigest()[:12]
        try:
            rel = entry.relative_to(archive_dir.parents[_OUTPUT_RELATIVE_PARENT])
        except ValueError:
            rel = entry
        candidates.append(
            {
                "path": str(rel),
                "mtime_days_ago": int((now_ts - mtime) / _SECONDS_PER_DAY),
                "sha256": sha,
            }
        )
    return candidates


@click.command(name="rotate")
@click.option(
    "--older-than",
    default=90,
    type=int,
    help="Days threshold (default 90). Entries older than this are listed.",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=True,
    help="Read-only preview (default on). Destructive rotation is deferred.",
)
@click.option(
    "--format",
    "fmt",
    default="yaml",
    type=click.Choice(["yaml", "json"]),
    help="Output format (default yaml).",
)
@click.pass_context
def rotate_cmd(
    ctx: click.Context,
    older_than: int,
    dry_run: bool,
    fmt: str,
) -> None:
    """List ``openspec/changes/archive/`` entries older than N days. Read-only."""
    archive_dir = Path("openspec") / "changes" / "archive"
    candidates = _candidate_entries(archive_dir, older_than)
    payload = {
        "dry_run": dry_run,
        "older_than_days": older_than,
        "candidates": candidates,
    }
    if fmt == "yaml":
        click.echo(yaml.safe_dump(payload, sort_keys=False))
    else:
        click.echo(json.dumps(payload, indent=2))


# ---------- REQ-V1.3.4: flow archive rotate (read-only archive preview) ----------
# The archive_group + archive_change_cmd block was relocated from
# ``cli/__init__.py`` lines 1568-1614 (post-Slice-1..7) to here as part
# of v1.3-cli-split Slice 8/8 (FINAL). Behavior MUST match pre-Slice-8
# exactly. The dead ``archive()`` function at ``cli/__init__.py:357`` is
# preserved VERBATIM in ``__init__.py`` per tasks.md r4 (out-of-scope).


@main.group(name="archive")
def archive_group() -> None:
    """Read-only archive introspection (REQ-V1.3.4).

    Subcommands:
    - ``rotate``: list entries in ``openspec/changes/archive/`` older than
      ``--older-than`` days. Default behavior is dry-run; never mutates
      disk. Destructive rotation is deferred to ``chore/archive-rotation-2026``.
    """


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


__all__ = [
    "rotate_cmd",
    "_candidate_entries",
    "_entry_mtime",
    "archive_group",
    "archive_change_cmd",
    # Stdlib / typing names re-exported for the cli/rotation.py back-compat
    # shim (v1.3-cli-split Slice 8). The shim does
    # ``from flow_engineering.cli.archive import (subprocess, json, ...)`` and
    # tests patch ``flow_engineering.cli.rotation.subprocess.run`` via the
    # string-form monkeypatch API, so these bindings must be explicitly
    # exported to satisfy mypy's no-implicit-reexport (strict mode).
    "subprocess",
    "json",
    "hashlib",
    "datetime",
    "UTC",
    "Path",
    "Any",
]
