"""Shared CLI helpers extracted from ``cli/__init__.py`` (v1.3-cli-split, Slice 1).

This module hosts the cross-domain constants and small helpers used by
multiple CLI submodules. Keeping them here lets later slices
(``cli/workspace.py``, ``cli/project.py``, ``cli/drift.py``, ...) import
them without reintroducing circular dependencies through ``cli/__init__``.
All code below is a verbatim relocation from ``cli/__init__.py`` lines
85-183 -- behavior MUST match pre-split exactly.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from flow_engineering import observability

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
