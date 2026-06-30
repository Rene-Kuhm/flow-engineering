"""Shared fake workspace fixtures for ``flow_engineering.workspace_hygiene`` tests.

Phase 4 (workspace-hygiene) keeps its fixture module isolated from the existing
``tests/unit/_workspace_fixtures.py`` (Phase 1/2/3 territory) so the safety-core
PR1 cannot perturb any prior test pollution. The helpers here provide:

- ``make_fake_project(name, *, with_files=(), with_git=False) -> Path``
- ``make_fake_registry(*, projects=(), archived=()) -> Registry``
- ``stub_home(monkeypatch, path) -> None`` — monkeypatches ``Path.home()``
  so the registry resolver and backup root see a tmp path under test control.

The cross-platform path tests parameterize over Windows + POSIX ``Path.home``
stubs; see ``test_workspace_hygiene.py::test_registry_path_resolves_*``.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from flow_engineering.registry import (
    ArchivedEntry,
    ProjectEntry,
    Registry,
)


def make_fake_project(
    name: str,
    *,
    with_files: Sequence[str] = (),
    with_git: bool = False,
    parent: Path | None = None,
) -> Path:
    """Create a fake project directory under ``parent`` (or cwd if ``None``).

    Args:
        name: directory name (also the project name in registry entries).
        with_files: filenames to create empty inside the project dir.
        with_git: if True, create a ``.git/`` subdirectory.
        parent: parent dir; tests usually pass ``tmp_path`` directly.

    Returns:
        The project directory path. The directory exists on disk.
    """
    base = parent if parent is not None else Path.cwd()
    project = base / name
    project.mkdir(parents=True, exist_ok=True)
    for filename in with_files:
        (project / filename).write_text("", encoding="utf-8")
    if with_git:
        (project / ".git").mkdir(exist_ok=True)
    return project


def make_fake_registry(
    *,
    projects: Sequence[ProjectEntry] = (),
    archived: Sequence[ArchivedEntry] = (),
) -> Registry:
    """Build a ``Registry`` in memory from the given entries."""
    return Registry(version=1, projects=list(projects), archived=list(archived))


def stub_home(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """Monkeypatch ``Path.home()`` to return ``path`` for the duration of a test.

    Both registry resolution and ``workspace_hygiene`` helpers depend on
    ``Path.home()``. Tests that need a clean per-test HOME (so the registry
    file does not pollute the real ``~/.flow-engineering/`` dir) call this
    helper to redirect the resolver.
    """
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: path))


__all__ = [
    "make_fake_project",
    "make_fake_registry",
    "stub_home",
]
