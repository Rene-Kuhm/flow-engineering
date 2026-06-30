"""Shared fake-workspace fixtures for ``flow workspace status`` and ``flow projects ls`` tests.

Houses 10 ``make_fake_*`` helpers + the ``_default_branch_fake_git`` seam so both
``tests/unit/test_cli_projects.py`` (Phase 1 AC9 contract) and
``tests/unit/test_cli_workspace_status.py`` (Phase 3) consume them without
duplication. Per design #448 §4 + tasks #449 T-3.

The fixtures deliberately use only ``tmp_path`` and never reference a hardcoded
``C:\\dev\\proyects`` (cross-platform discipline). Each helper writes the
minimum set of marker files that ``_detect_project_markers`` (cli.py:2759) keys
on; missing ``.git/`` for ``make_fake_no_git_project`` keeps that helper's
``has_git`` as ``False``.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

__all__ = [
    "make_fake_go_project",
    "make_fake_python_project",
    "make_fake_flutter_project",
    "make_fake_nix_project",
    "make_fake_astro_project",
    "make_fake_next_project",
    "make_fake_wxt_project",
    "make_fake_no_git_project",
    "make_fake_dirty_project",
    "make_fake_openspec_project",
    "_default_branch_fake_git",
]


def make_fake_go_project(parent: Path, name: str = "go-proj") -> Path:
    """Create a Go project (go.mod + .git/) under ``parent``. Returns the project dir."""
    p = parent / name
    p.mkdir()
    (p / "go.mod").write_text("module example.com/test\n\ngo 1.21\n")
    (p / ".git").mkdir()
    return p


def make_fake_python_project(parent: Path, name: str = "py-proj") -> Path:
    """Create a Python project (pyproject.toml + Makefile with test: target)."""
    p = parent / name
    p.mkdir()
    (p / "pyproject.toml").write_text('[project]\nname = "x"\n')
    (p / "Makefile").write_text("test:\n\tpytest\n")
    return p


def make_fake_flutter_project(parent: Path, name: str = "flutter-proj") -> Path:
    """Create a Flutter project (pubspec.yaml)."""
    p = parent / name
    p.mkdir()
    (p / "pubspec.yaml").write_text("name: x\ndescription: stub\n")
    return p


def make_fake_nix_project(parent: Path, name: str = "nix-proj") -> Path:
    """Create a Nix project (flake.nix)."""
    p = parent / name
    p.mkdir()
    (p / "flake.nix").write_text("{ }: { }\n")
    return p


def make_fake_astro_project(parent: Path, name: str = "astro-proj") -> Path:
    """Create an Astro project (astro.config.mjs + package.json with astro dep)."""
    p = parent / name
    p.mkdir()
    (p / "astro.config.mjs").write_text("// config\n")
    (p / "package.json").write_text('{"dependencies": {"astro": "^5"}}\n')
    return p


def make_fake_next_project(parent: Path, name: str = "next-proj") -> Path:
    """Create a Next.js project (package.json with next dep + app/ dir)."""
    p = parent / name
    p.mkdir()
    (p / "package.json").write_text('{"dependencies": {"next": "^15"}}\n')
    (p / "app").mkdir()
    return p


def make_fake_wxt_project(parent: Path, name: str = "wxt-proj") -> Path:
    """Create a WXT project (wxt.config.ts)."""
    p = parent / name
    p.mkdir()
    (p / "wxt.config.ts").write_text("export default { }\n")
    return p


def make_fake_no_git_project(parent: Path, name: str = "no-git-proj") -> Path:
    """Create a project with pyproject.toml only (no .git/)."""
    p = parent / name
    p.mkdir()
    (p / "pyproject.toml").write_text('[project]\nname = "x"\n')
    return p


def make_fake_dirty_project(parent: Path, name: str = "dirty-proj") -> Path:
    """Create a Go project with .git/ + an uncommitted file."""
    p = make_fake_go_project(parent, name=name)
    (p / "uncommitted.txt").write_text("wip\n")
    return p


def make_fake_openspec_project(parent: Path, name: str = "os-proj") -> Path:
    """Create a project with openspec/changes/ dir (empty)."""
    p = parent / name
    p.mkdir()
    (p / "openspec" / "changes").mkdir(parents=True)
    return p


def _default_branch_fake_git(
    branch: str = "main",
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Build a ``fake_git`` that returns ``branch`` for rev-parse; no remote, clean."""

    def fake_git(*args: str, **kwargs: object) -> subprocess.CompletedProcess:
        cp = subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")
        if args and args[0] == "rev-parse":
            cp.stdout = branch + "\n"
        elif args and args[0] == "config":
            cp.returncode = 1  # no remote
        return cp

    return fake_git
