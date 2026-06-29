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
