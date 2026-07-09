"""Unit tests for ``flow workspace {fix,archive,archived,restore}`` Click commands.

Phase 4 (workspace-hygiene) PR2 = CLI surface. 8 tests across 4 verbs (per
``openspec/changes/workspace-hygiene/tasks.md`` T-9..T-12).

The tests wire the verified PR1 safety core (registry + workspace_hygiene)
to the user-facing Click surface added to ``workspace_group`` at
``src/flow_engineering/cli.py:2982``. They use :class:`click.testing.CliRunner`
so the test never depends on a real ``flow`` install.

Test isolation:
    The ``workspace_home`` fixture monkeypatches ``Path.home()`` so the
    registry resolver and the backup root resolve under ``tmp_path``. The
    ``fake_git`` fixture replaces ``cli._git`` with a stub that reports
    ``rc=0`` and creates a minimal ``.git/`` tree (mirrors
    ``_stub_git_success`` in ``tests/unit/test_workspace_hygiene.py``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering import cli as cli_mod
from flow_engineering.cli import main
from flow_engineering.registry import (
    load_registry,
    registry_path,
)
from tests.unit._workspace_hygiene_fixtures import (
    make_fake_project,
    stub_home,
)

runner = CliRunner()


# =============================================================================
# Shared fixtures + helpers
# =============================================================================


@pytest.fixture
def workspace_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``Path.home()`` to ``tmp_path`` so registry + backup go there.

    Also sets ``FLOW_PROJECTS_ROOT`` to ``tmp_path / "projects"`` so the CLI's
    project resolver finds the fake projects placed by :func:`_make_project`.

    Returns the new fake home dir. Tests should place their projects under
    ``tmp_path / "projects" / <name>`` and reference the backup root via
    ``tmp_path / ".flow-engineering" / "backups"``.
    """
    stub_home(monkeypatch, tmp_path)
    (tmp_path / "projects").mkdir(exist_ok=True)
    monkeypatch.setenv("FLOW_PROJECTS_ROOT", str(tmp_path / "projects"))
    return tmp_path


@pytest.fixture
def fake_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``cli._git`` with a stub that returns rc=0 + creates ``.git/``.

    Mirrors ``_stub_git_success`` in ``tests/unit/test_workspace_hygiene.py``
    so ``_verify_post_mutation`` sees a real ``.git/`` tree.
    """

    def _stub(*args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        cp = subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")
        if args and args[0] == "init":
            target = Path(args[1]) if len(args) > 1 else None
            if target is not None:
                (target / ".git").mkdir(exist_ok=True)
                (target / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
                (target / ".git" / "config").write_text(
                    "[core]\n\trepositoryformatversion = 0\n", encoding="utf-8"
                )
        return cp

    monkeypatch.setattr(cli_mod, "_git", _stub)


def _make_project(parent: Path, name: str, *, with_files: list[str] | None = None) -> Path:
    """Create a project dir under ``parent / "projects" / name``.

    Defaults to empty (no user files) so the project is empty per
    REQ-HYGIENE-BACKUP-GATE-NONEMPTY. ``with_files`` adds user-visible files.
    """
    return make_fake_project(name, with_files=with_files or [], parent=parent / "projects")


def _backup_root(tmp_path: Path) -> Path:
    """Backup root path used by the CLI commands."""
    return tmp_path / ".flow-engineering" / "backups"


# =============================================================================
# T-9 — `flow workspace fix`
# =============================================================================


def test_fix_dry_run_default_does_not_mutate(workspace_home: Path, fake_git: None) -> None:
    """T-9: ``flow workspace fix <project>`` with no flags → dry-run, no mutation.

    REQ-HYGIENE-DRY-RUN-DEFAULT: dry-run is the default. No ``.git/``
    created, no backup created, no registry written.
    """
    project = _make_project(workspace_home, "mockup", with_files=["README.md"])
    assert not (project / ".git").exists()

    result = runner.invoke(main, ["workspace", "fix", "mockup"])

    assert result.exit_code == 0, result.output
    assert not (project / ".git").exists(), "dry-run must not create .git/"
    assert not _backup_root(workspace_home).exists(), "no backup under dry-run"
    assert not registry_path().exists(), "dry-run must not write registry"


def test_fix_missing_yes_refuses(workspace_home: Path, fake_git: None) -> None:
    """T-9: ``flow workspace fix <project> --backup`` without ``--yes`` → exit != 0.

    REQ-HYGIENE-DRY-RUN-DEFAULT: missing ``--yes`` (and not dry-run) →
    the CLI surfaces ``MutationGateError.user_message`` to stderr and
    exits non-zero. No ``.git/`` created, no backup created.
    """
    project = _make_project(workspace_home, "mockup", with_files=["README.md"])

    result = runner.invoke(main, ["workspace", "fix", "mockup", "--backup"])

    assert result.exit_code != 0
    assert "--yes" in result.output, f"stderr/output must mention --yes: {result.output}"
    assert not (project / ".git").exists()
    assert not _backup_root(workspace_home).exists()


def test_fix_non_empty_missing_backup_refuses(workspace_home: Path, fake_git: None) -> None:
    """T-9: non-empty fix without ``--backup`` → exit != 0.

    REQ-HYGIENE-BACKUP-GATE-NONEMPTY: a project with user-visible files
    requires ``--backup``. The CLI surfaces ``EmptyProjectError.user_message``
    to stderr and exits non-zero. No ``.git/`` created.
    """
    project = _make_project(workspace_home, "mockup", with_files=["README.md"])

    result = runner.invoke(main, ["workspace", "fix", "mockup", "--yes"])

    assert result.exit_code != 0
    assert "--backup" in result.output, f"stderr/output must mention --backup: {result.output}"
    assert not (project / ".git").exists()


def test_fix_happy_path(workspace_home: Path, fake_git: None) -> None:
    """T-9: ``flow workspace fix <empty> --yes`` → ``.git/`` + registry entry.

    REQ-HYGIENE-FIX-SURFACE: empty project + ``--yes`` (no ``--backup``
    needed because the project has no user files) → the orchestrator
    creates ``.git/`` and appends the project to the registry.
    """
    project = _make_project(workspace_home, "fresh")  # empty by default

    result = runner.invoke(main, ["workspace", "fix", "fresh", "--yes"])

    assert result.exit_code == 0, result.output
    assert (project / ".git").is_dir(), ".git/ must be created on success"

    reg = load_registry()
    names = [p.name for p in reg.projects]
    assert "fresh" in names, f"registry must contain 'fresh'; got {names}"


# =============================================================================
# T-10 — `flow workspace archive`
# =============================================================================


def test_archive_happy_path(workspace_home: Path, fake_git: None) -> None:
    """T-10: ``flow workspace archive <project> --reason X --yes`` → archived.

    REQ-HYGIENE-ARCHIVE-SURFACE: archive moves the entry from
    ``projects[]`` to ``archived[]`` with the user-supplied reason. No
    filesystem change; registry-only.
    """
    # Pre-register the project via the CLI itself (``workspace fix``) so the
    # registry has something for the archive to find. An empty project needs
    # only ``--yes`` (no ``--backup``) per REQ-HYGIENE-BACKUP-GATE-NONEMPTY.
    _make_project(workspace_home, "mockup-2-blog")  # empty
    fix_result = runner.invoke(main, ["workspace", "fix", "mockup-2-blog", "--yes"])
    assert fix_result.exit_code == 0, fix_result.output

    result = runner.invoke(
        main,
        ["workspace", "archive", "mockup-2-blog", "--reason", "deprecated", "--yes"],
    )

    assert result.exit_code == 0, result.output
    reg = load_registry()
    archived = [a for a in reg.archived if a.name == "mockup-2-blog"]
    assert len(archived) == 1, f"must be in archived[]; got {archived}"
    assert archived[0].reason == "deprecated"
    assert all(p.name != "mockup-2-blog" for p in reg.projects)


# =============================================================================
# T-11 — `flow workspace archived`
# =============================================================================


def test_archived_text_output(workspace_home: Path, fake_git: None) -> None:
    """T-11: ``flow workspace archived`` renders a 3-column text table.

    REQ-HYGIENE-ARCHIVED-LISTING + REQ-HYGIENE-NO-JSON-MVP: the command
    prints ``NAME  ARCHIVED_AT  REASON`` header + one row per entry.
    No ``--json`` flag is exposed.
    """
    from flow_engineering.registry import (
        ArchivedEntry,
        Registry,
        save_registry_atomic,
    )

    reg = Registry(
        version=1,
        projects=[],
        archived=[
            ArchivedEntry(
                name="mockup-2-blog",
                path=Path("C:/proj/mockup-2-blog"),
                archived_at="2026-06-30T12:00:00Z",
                reason="deprecated",
            ),
            ArchivedEntry(
                name="openspec",
                path=Path("C:/proj/openspec"),
                archived_at="2026-06-30T12:30:00Z",
                reason="manual archive",
            ),
        ],
    )
    save_registry_atomic(reg)

    result = runner.invoke(main, ["workspace", "archived"])

    assert result.exit_code == 0, result.output
    assert "NAME" in result.output
    assert "ARCHIVED_AT" in result.output
    assert "REASON" in result.output
    assert "mockup-2-blog" in result.output
    assert "openspec" in result.output


# =============================================================================
# T-12 — `flow workspace restore`
# =============================================================================


def test_restore_happy_path(workspace_home: Path, fake_git: None) -> None:
    """T-12: ``flow workspace restore <project> --yes`` reverses archive.

    REQ-HYGIENE-RESTORE-SURFACE: restore moves the entry from
    ``archived[]`` back to ``projects[]``.
    """
    from flow_engineering.registry import (
        ArchivedEntry,
        Registry,
        save_registry_atomic,
    )

    reg = Registry(
        version=1,
        projects=[],
        archived=[
            ArchivedEntry(
                name="mockup-2-blog",
                path=Path("C:/proj/mockup-2-blog"),
                archived_at="2026-06-30T12:00:00Z",
                reason="deprecated",
            ),
        ],
    )
    save_registry_atomic(reg)

    result = runner.invoke(main, ["workspace", "restore", "mockup-2-blog", "--yes"])

    assert result.exit_code == 0, result.output
    reg_after = load_registry()
    assert all(a.name != "mockup-2-blog" for a in reg_after.archived)
    names = [p.name for p in reg_after.projects]
    assert "mockup-2-blog" in names


def test_restore_missing_yes_refuses(workspace_home: Path, fake_git: None) -> None:
    """T-12: ``flow workspace restore <project>`` without ``--yes`` → exit != 0.

    REQ-HYGIENE-RESTORE-SURFACE: missing ``--yes`` → the CLI refuses and
    prints the remediation hint to stderr. Registry unchanged.
    """
    from flow_engineering.registry import (
        ArchivedEntry,
        Registry,
        save_registry_atomic,
    )

    reg = Registry(
        version=1,
        projects=[],
        archived=[
            ArchivedEntry(
                name="mockup-2-blog",
                path=Path("C:/proj/mockup-2-blog"),
                archived_at="2026-06-30T12:00:00Z",
                reason="deprecated",
            ),
        ],
    )
    save_registry_atomic(reg)

    result = runner.invoke(main, ["workspace", "restore", "mockup-2-blog"])

    assert result.exit_code != 0
    assert "--yes" in result.output, f"stderr/output must mention --yes: {result.output}"
    reg_after = load_registry()
    assert any(a.name == "mockup-2-blog" for a in reg_after.archived), (
        "archive list must be unchanged"
    )
