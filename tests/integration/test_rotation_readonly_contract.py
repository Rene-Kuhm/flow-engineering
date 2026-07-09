"""Integration test: ``flow_engineering.cli.rotation`` MUST be read-only.

Per design-d ADR-d.1, v1.3 ships ``flow archive rotate`` as **read-only**.
The destructive counterpart is deferred to ``chore/archive-rotation-2026``.
This integration test enforces the read-only contract by AST-grepping the
production module for any function call that would move or rename an
archive entry:

- ``git mv``
- ``shutil.move``
- ``os.rename``
- ``Path.rename``

Per Article III strict TDD, this test is written BEFORE the production
module exists. It MUST fail RED (file not found) until step 8 lands.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROTATION_MODULE = (
    Path(__file__).resolve().parents[2] / "src" / "flow_engineering" / "cli" / "rotation.py"
)

FORBIDDEN_FUNCTIONS: frozenset[str] = frozenset(
    {"move", "rename"},
)

# Modules whose top-level name exposes one of the forbidden functions.
FORBIDDEN_MODULES: dict[str, frozenset[str]] = {
    "shutil": FORBIDDEN_FUNCTIONS,
    "os": frozenset({"rename"}),
    "pathlib": FORBIDDEN_FUNCTIONS,
}


def _import_aliases(tree: ast.AST) -> dict[str, str]:
    """Build a ``local_name -> module`` map from top-level ``import X as Y``.

    Catches ``import shutil as sh`` and ``from os import rename`` aliases.
    """
    aliases: dict[str, str] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                aliases[local] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local = alias.asname or alias.name
                aliases[local] = f"{node.module}.{alias.name}"
    return aliases


def _resolve_attr_chain(node: ast.Call) -> tuple[str, str | None]:
    """Return ``(root_name, attr)`` for a Call like ``shutil.move(...)``.

    For ``Path.rename(...)`` the root is ``Path`` and the attr is
    ``rename``. For ``git.mv(...)`` the root is ``git`` and the attr is
    ``mv``.
    """
    func = node.func
    if isinstance(func, ast.Attribute):
        attr = func.attr
        # Walk the value side. If it's a Name, return its id.
        if isinstance(func.value, ast.Name):
            return func.value.id, attr
        # Nested attribute like ``subprocess.run.returncode`` is irrelevant.
        return "", attr
    if isinstance(func, ast.Name):
        return func.id, None
    return "", None


def _violations(tree: ast.AST) -> list[str]:
    """Walk every Call node and report forbidden module/attr combinations."""
    aliases = _import_aliases(tree)
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        root, attr = _resolve_attr_chain(node)
        if not root or not attr:
            continue
        if attr not in FORBIDDEN_FUNCTIONS:
            continue
        # 1. Aliased import: ``shutil.move(...)`` or ``from os import rename``.
        resolved = aliases.get(root)
        if resolved is None:
            # Bare ``Path.rename(...)`` — pathlib is imported as ``from pathlib import Path``.
            if root == "Path":
                violations.append(
                    f"Path.{attr}() at line {node.lineno} (forbidden read-only call)",
                )
            continue
        # Check the resolved module against the forbidden set.
        for module, fns in FORBIDDEN_MODULES.items():
            if (resolved == module or resolved.startswith(f"{module}.")) and attr in fns:
                violations.append(
                    f"{resolved}.{attr}() at line {node.lineno} (forbidden read-only call)",
                )
    return violations


class TestRotationReadOnlyContract:
    """``flow_engineering.cli.rotation`` MUST NOT call mutation APIs."""

    def test_module_exists(self) -> None:
        """The production module MUST exist (RED gate before this test runs)."""
        assert ROTATION_MODULE.exists(), (
            f"RED gate: {ROTATION_MODULE} does not exist yet — "
            "GREEN step 8 must land before this assertion passes"
        )

    def test_no_git_mv_shutil_move_os_rename_path_rename(self) -> None:
        """AST-grep forbids ``git mv``, ``shutil.move``, ``os.rename``, ``Path.rename``."""
        if not ROTATION_MODULE.exists():
            pytest.fail(
                f"RED: {ROTATION_MODULE} does not exist yet — "
                "GREEN step 8 must land before this assertion passes",
            )
        source = ROTATION_MODULE.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(ROTATION_MODULE))
        violations = _violations(tree)
        assert violations == [], (
            "Read-only contract violated by the following calls:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
