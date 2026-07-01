"""Shared fake workspace fixtures for CLI workspace tests."""

from __future__ import annotations

from pathlib import Path


def make_project(parent: Path, name: str) -> Path:
    path = parent / name
    path.mkdir()
    return path


def add_git(project: Path) -> Path:
    (project / ".git").mkdir(exist_ok=True)
    return project


def add_openspec(project: Path) -> Path:
    (project / "openspec" / "changes").mkdir(parents=True, exist_ok=True)
    return project


def add_readme(project: Path, ext: str = ".md", content: str = "# fixture\n") -> Path:
    """Add a README at the project root. ``ext`` controls the suffix (.md | .rst)."""
    (project / f"README{ext}").write_text(content, encoding="utf-8")
    return project


def add_pytest_ini(project: Path) -> Path:
    """Add a minimal ``pytest.ini`` at the project root (R7 infra signal)."""
    (project / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    return project


def add_pyproject_pytest(project: Path) -> Path:
    """Append a ``[tool.pytest]`` section to an existing ``pyproject.toml``.

    The fixture is additive: it does NOT clobber an existing
    ``pyproject.toml``. If the file is absent, it creates a minimal one
    with the section. Used for R7 infra signal testing.
    """
    pyproject = project / "pyproject.toml"
    existing = ""
    if pyproject.is_file():
        existing = pyproject.read_text(encoding="utf-8")
    if "[tool.pytest]" in existing:
        return project
    pyproject.write_text(existing + "\n[tool.pytest]\ntestpaths = [\"tests\"]\n", encoding="utf-8")
    return project


def add_tests_dir(project: Path) -> Path:
    """Create an empty ``tests/`` directory at the project root (R7 infra signal)."""
    (project / "tests").mkdir(exist_ok=True)
    return project


def make_python_project(parent: Path, name: str = "py-proj", *, git: bool = True, tests: bool = True, openspec: bool = True) -> Path:
    project = make_project(parent, name)
    (project / "pyproject.toml").write_text('[project]\nname = "fixture"\n', encoding="utf-8")
    if tests:
        (project / "Makefile").write_text("test:\n\tpytest\n", encoding="utf-8")
    if git:
        add_git(project)
    if openspec:
        add_openspec(project)
    return project


def make_go_project(parent: Path, name: str = "go-proj", *, git: bool = True, tests: bool = True, openspec: bool = True) -> Path:
    project = make_project(parent, name)
    (project / "go.mod").write_text("module example.com/fixture\n\ngo 1.21\n", encoding="utf-8")
    if git:
        add_git(project)
    if openspec:
        add_openspec(project)
    return project


def make_node_project(parent: Path, name: str = "node-proj", *, git: bool = True, tests: bool = True) -> Path:
    project = make_project(parent, name)
    script = '"test": "vitest"' if tests else '"build": "vite build"'
    (project / "package.json").write_text("{" + script + "}\n", encoding="utf-8")
    if git:
        add_git(project)
    return project


def make_unknown_project(parent: Path, name: str = "unknown-proj", *, git: bool = False) -> Path:
    project = make_project(parent, name)
    if git:
        add_git(project)
    return project
