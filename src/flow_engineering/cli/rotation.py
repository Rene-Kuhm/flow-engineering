"""Read-only archive rotation utility (v1.3 sub-change d).

Implements REQ-V1.3.4 from
``openspec/changes/v1.3-platform-hardening/spec.md``. Lists entries in
``openspec/changes/archive/`` older than N days; **never** modifies
anything on disk.

Per Article II (Library-First), this module is importable without CLI.
The click command (``rotate_cmd``) is the only CLI surface; the helper
functions (``_entry_mtime``, ``_candidate_entries``) are pure and can
be exercised directly from unit tests.

Read-only contract (enforced by
``tests/integration/test_rotation_readonly_contract.py`` via AST grep):
no calls to ``shutil.move``, ``os.rename``, ``Path.rename``, or
``git mv`` may appear anywhere in this file.
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

# Paths resolved at call time (not import time) so tests can chdir freely.
_REPO_ROOT_PARENTS = 2  # archive_dir is <repo>/openspec/changes/archive; .parents[2] = <repo>
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
            repo_root = entry.parents[_REPO_ROOT_PARENTS]
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
                if fs_mtime > git_mtime + (_GIT_FALLBACK_THRESHOLD_DAYS * 86400):
                    return git_mtime
        except (subprocess.SubprocessError, OSError):
            pass

    return fs_mtime


def _candidate_entries(archive_dir: Path, older_than_days: int) -> list[dict[str, Any]]:
    """Return list of ``{path, mtime_days_ago, sha256}`` dicts for entries
    older than ``older_than_days``.
    """
    if not archive_dir.exists():
        return []
    cutoff = (
        datetime.now(tz=UTC).timestamp() - (older_than_days * 86400)
    )
    candidates: list[dict[str, Any]] = []
    now_ts = datetime.now(tz=UTC).timestamp()
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
        rel: Path = entry
        try:
            rel = entry.relative_to(archive_dir.parents[_REPO_ROOT_PARENTS - 1])
        except ValueError:
            rel = entry
        candidates.append({
            "path": str(rel),
            "mtime_days_ago": int((now_ts - mtime) / 86400),
            "sha256": sha,
        })
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
    ctx: click.Context, older_than: int, dry_run: bool, fmt: str,
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


__all__ = ["rotate_cmd", "_candidate_entries", "_entry_mtime"]

