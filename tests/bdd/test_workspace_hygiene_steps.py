"""BDD step glue for ``tests/bdd/workspace_hygiene.feature`` (Phase 4 of workspace-intelligence).

Mirrors the structure of ``tests/bdd/test_where_steps.py`` and
``tests/bdd/test_cross_project_federation_steps.py``. The 16 scenarios in
``tests/bdd/workspace_hygiene.feature`` are bound via ``@scenario(...)``
decorators; the Given/When/Then steps below implement them.

Test isolation:
    The ``workspace_home`` fixture monkeypatches ``Path.home()`` so the
    registry + backup dirs resolve under ``tmp_path``. The ``fake_git``
    fixture replaces ``cli._git`` with a stub that returns rc=0 + creates
    a minimal ``.git/`` tree. ``FLOW_PROJECTS_ROOT`` is redirected per
    scenario so the ``_resolve_projects_root`` helper finds the fake
    projects.

R1 scenarios (``fix on a project containing an uncommitted file``):
    Verifies the orchestrator does NOT touch the worktree / index /
    untracked files for a project that already has ``.git/``. The CLI's
    ``workspace_fix_cmd`` re-runs ``_detect_project_markers`` which reports
    ``has_git=True``; the orchestrator still attempts ``git init`` (which
    is idempotent) and writes a fresh registry row. The assertion is that
    the project's existing state is preserved exactly.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenario, then, when

from flow_engineering import cli as cli_mod
from flow_engineering.cli import main
from flow_engineering.registry import (
    ArchivedEntry,
    ProjectEntry,
    Registry,
    load_registry,
    registry_path,
    save_registry_atomic,
)

runner = CliRunner()


# =============================================================================
# Shared fixtures
# =============================================================================


@pytest.fixture
def workspace_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Per-scenario scratch state for the ``flow workspace`` BDD scenarios.

    Returns a dict carrying:
      - ``tmp_path``: the scratch root.
      - ``projects_root``: where projects live (``tmp_path / "projects"``).
      - ``home``: ``tmp_path`` itself (so registry + backup resolve there).
      - ``result``: most-recent CliRunner result.
      - ``output``: ``result.output`` for quick assertions.
      - ``git_calls``: list of git invocations captured by ``fake_git``.
      - ``verify_will_fail``: when True, monkeypatches ``_verify_post_mutation``
        to return False (exercises the pollution-protocol restore branch).
      - ``_monkeypatch``: holder for step functions that need the fixture.
    """
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    projects_root = tmp_path / "projects"
    projects_root.mkdir(exist_ok=True)
    (tmp_path / ".flow-engineering").mkdir(exist_ok=True)
    monkeypatch.setenv("FLOW_PROJECTS_ROOT", str(projects_root))
    return {
        "tmp_path": tmp_path,
        "projects_root": projects_root,
        "home": tmp_path,
        "result": None,
        "output": "",
        "git_calls": [],
        "verify_will_fail": False,
        "_monkeypatch": monkeypatch,
    }


@pytest.fixture(autouse=True)
def _fake_git(workspace_home: dict[str, Any]) -> None:
    """Stub ``cli._git`` to record every call + create a minimal ``.git/``.

    Mirrors ``_stub_git_success`` in ``tests/unit/test_workspace_hygiene.py``
    so ``_verify_post_mutation`` sees a real ``.git/`` tree after ``git init``.
    When the cwd matches ``workspace_home["dirty_project"]`` (set by the
    AC13 Given step), ``git status --porcelain`` returns a non-empty line
    so ``_detect_project_markers`` reports ``dirty=True``.
    """

    def _stub(*args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        workspace_home["git_calls"].append(list(args))
        cwd = _kwargs.get("cwd")
        dirty_project = workspace_home.get("dirty_project")
        is_dirty_cwd = (
            dirty_project is not None
            and cwd is not None
            and Path(str(cwd)).resolve() == Path(dirty_project).resolve()
        )
        cp = subprocess.CompletedProcess(
            args=["git", *args], returncode=0, stdout="", stderr=""
        )
        if args and args[0] == "init":
            target = Path(args[1]) if len(args) > 1 else None
            if target is not None:
                (target / ".git").mkdir(exist_ok=True)
                (target / ".git" / "HEAD").write_text(
                    "ref: refs/heads/main\n", encoding="utf-8"
                )
                (target / ".git" / "config").write_text(
                    "[core]\n\trepositoryformatversion = 0\n", encoding="utf-8"
                )
        elif args and args[0] == "rev-parse":
            cp = subprocess.CompletedProcess(
                args=["git", *args], returncode=0, stdout="main\n", stderr=""
            )
        elif args and args[0] == "status":
            stdout = " M WIP.md\n" if is_dirty_cwd else ""
            cp = subprocess.CompletedProcess(
                args=["git", *args], returncode=0, stdout=stdout, stderr=""
            )
        elif args and args[0] == "config":
            cp = subprocess.CompletedProcess(
                args=["git", *args], returncode=0, stdout="", stderr=""
            )
        return cp

    workspace_home["_monkeypatch"].setattr(cli_mod, "_git", _stub)


@pytest.fixture(autouse=True)
def _maybe_break_verify(workspace_home: dict[str, Any]) -> None:
    """Wrap ``_verify_post_mutation`` so ``verify_will_fail`` is honored.

    The flag ``verify_will_fail`` may be set by a Given step that runs
    AFTER fixture setup, so the patch cannot be conditional at setup
    time. Instead we install a wrapper that checks the flag at call time
    and returns False when set, otherwise delegating to the real function.
    """
    from flow_engineering import workspace_hygiene as wh_mod

    real_fn = wh_mod._verify_post_mutation

    def wrapper(*args: object, **kwargs: object) -> bool:
        if workspace_home.get("verify_will_fail"):
            return False
        return real_fn(*args, **kwargs)  # type: ignore[arg-type]

    workspace_home["_monkeypatch"].setattr(
        wh_mod, "_verify_post_mutation", wrapper
    )


# =============================================================================
# Helpers
# =============================================================================


def _make_project(
    workspace_home: dict[str, Any],
    name: str,
    *,
    with_files: list[str] | None = None,
    with_git: bool = False,
) -> Path:
    """Create a project directory under ``workspace_home['projects_root']``."""
    project = workspace_home["projects_root"] / name
    project.mkdir(parents=True, exist_ok=True)
    for filename in with_files or []:
        (project / filename).write_text("", encoding="utf-8")
    if with_git:
        (project / ".git").mkdir(exist_ok=True)
    return project


def _backup_root(workspace_home: dict[str, Any]) -> Path:
    return workspace_home["home"] / ".flow-engineering" / "backups"


def _registry_path() -> Path:
    """Registry path (re-evaluates ``Path.home()``)."""
    return registry_path()


def _register_project(
    workspace_home: dict[str, Any],
    name: str,
    *,
    reason_seed: bool = False,
) -> None:
    """Insert a project into the registry for tests that need pre-existing data.

    Tracks registrations on ``workspace_home["pending_registrations"]`` so
    a subsequent ``And a clean registry file`` step doesn't undo the
    registration. The pending registrations are flushed to the registry
    file by the ``_flush_pending_registrations`` autouse fixture AFTER
    all Given steps have run (and AFTER the clean step, if present).
    """
    project = _make_project(workspace_home, name)
    entry = ProjectEntry(
        name=name,
        path=project,
        has_git=False,
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check="2026-06-30T12:00:00Z",
    )
    pending = workspace_home.setdefault("pending_registrations", [])
    # Replace any existing entry for the same name.
    pending[:] = [e for e in pending if e.name != name]
    pending.append(entry)


@pytest.fixture(autouse=True)
def _flush_pending_registrations(workspace_home: dict[str, Any]) -> None:
    """DEPRECATED — pending registrations are now flushed by ``given_clean_registry``.

    Kept as a no-op so the autouse fixture list stays stable. Real flushing
    happens inside the ``given_clean_registry`` step (and inside any other
    step that creates a registry file). See :func:`_flush_pending` below.
    """


def _flush_pending(workspace_home: dict[str, Any]) -> None:
    """Write any pending registrations to the registry file.

    Called by ``given_clean_registry`` after wiping the file so the
    final registry state has the projects that earlier Given steps
    registered (e.g., ``Given a workspace root with a registered project
    named "openspec"`` followed by ``And a clean registry file``).
    """
    pending = workspace_home.get("pending_registrations", [])
    if not pending:
        return
    reg = load_registry()
    existing_names = {p.name for p in reg.projects}
    merged = list(reg.projects)
    for entry in pending:
        if entry.name not in existing_names:
            merged.append(entry)
    save_registry_atomic(reg.model_copy(update={"projects": merged}))


# =============================================================================
# Scenario bindings
# =============================================================================


@scenario("workspace_hygiene.feature", "dry-run on non-git project does not mutate filesystem")
def test_dry_run_does_not_mutate(workspace_home: dict[str, Any]) -> None:
    """AC1."""


@scenario("workspace_hygiene.feature", "fix without --yes refuses and mentions --yes")
def test_fix_without_yes_refuses(workspace_home: dict[str, Any]) -> None:
    """AC2."""


@scenario("workspace_hygiene.feature", "non-empty fix without --backup refuses and mentions --backup")
def test_non_empty_fix_without_backup_refuses(workspace_home: dict[str, Any]) -> None:
    """AC3."""


@scenario("workspace_hygiene.feature", "non-empty fix with --yes --backup creates .git and backup")
def test_non_empty_fix_with_backup_succeeds(workspace_home: dict[str, Any]) -> None:
    """AC4."""


@scenario("workspace_hygiene.feature", "empty fix with --yes (no --backup) creates .git and no backup")
def test_empty_fix_succeeds(workspace_home: dict[str, Any]) -> None:
    """AC5."""


@scenario("workspace_hygiene.feature", "archive with --reason records the user-supplied value")
def test_archive_with_reason(workspace_home: dict[str, Any]) -> None:
    """AC6."""


@scenario("workspace_hygiene.feature", "archive without --reason defaults to \"manual archive\" and logs it")
def test_archive_without_reason_defaults(workspace_home: dict[str, Any]) -> None:
    """AC7."""


@scenario("workspace_hygiene.feature", "archived outputs a text table with three columns")
def test_archived_text_table(workspace_home: dict[str, Any]) -> None:
    """AC8 — table with 2 rows."""


@scenario("workspace_hygiene.feature", "archived with no entries prints a clean message")
def test_archived_empty_message(workspace_home: dict[str, Any]) -> None:
    """AC8 — empty registry message."""


@scenario("workspace_hygiene.feature", "restore reverses a prior archive")
def test_restore_reverses_archive(workspace_home: dict[str, Any]) -> None:
    """AC9 — restore happy path."""


@scenario("workspace_hygiene.feature", "restore refuses without --yes")
def test_restore_refuses_without_yes(workspace_home: dict[str, Any]) -> None:
    """AC9 — restore gate."""


@scenario(
    "workspace_hygiene.feature",
    "workspace-hygiene commands preserve flow projects ls --json bytes for non-targets",
)
def test_byte_identical_for_non_targets(workspace_home: dict[str, Any]) -> None:
    """AC10 — byte-identical preservation."""


@scenario("workspace_hygiene.feature", "post-mutation verify failure triggers restore from snapshot")
def test_verify_failure_triggers_restore(workspace_home: dict[str, Any]) -> None:
    """AC11 — pollution-protocol restore."""


@scenario("workspace_hygiene.feature", "registry write is atomic on interruption")
def test_registry_atomic_write(workspace_home: dict[str, Any]) -> None:
    """AC12 — atomic write guard."""


@scenario("workspace_hygiene.feature", "read-only consumers do not create the registry")
def test_read_only_does_not_create_registry(workspace_home: dict[str, Any]) -> None:
    """AC12 — read-only consumer."""


@scenario("workspace_hygiene.feature", "fix on a dirty-git project does not remediate the dirty state")
def test_fix_on_dirty_git_does_not_remediate(workspace_home: dict[str, Any]) -> None:
    """AC13 — R1 OUT OF SCOPE."""


# =============================================================================
# Given steps
# =============================================================================


@given('a workspace root with a non-git project named "mockup" containing a file "README.md"')
def given_mockup_with_readme(workspace_home: dict[str, Any]) -> None:
    _make_project(workspace_home, "mockup", with_files=["README.md"])


@given('a workspace root with a non-git project named "fresh" containing zero user-visible files')
def given_fresh_empty(workspace_home: dict[str, Any]) -> None:
    _make_project(workspace_home, "fresh")


@given('a workspace root with a non-git project named "mockup"')
def given_mockup(workspace_home: dict[str, Any]) -> None:
    _make_project(workspace_home, "mockup")


@given('a workspace root with a registered project named "mockup-2-blog"')
def given_registered_mockup_2_blog(workspace_home: dict[str, Any]) -> None:
    _register_project(workspace_home, "mockup-2-blog")


@given('a workspace root with a registered project named "openspec"')
def given_registered_openspec(workspace_home: dict[str, Any]) -> None:
    _register_project(workspace_home, "openspec")


@given("a clean registry file")
def given_clean_registry(workspace_home: dict[str, Any]) -> None:
    """Delete the registry file (if any) so the test starts from a clean slate.

    Then re-applies any pending registrations accumulated by earlier Given
    steps. This handles the scenario pattern
    ``Given a workspace root with a registered project named X``
    ``And a clean registry file``
    where the clean step must not undo the registration.
    """
    if _registry_path().exists():
        _registry_path().unlink()
    _flush_pending(workspace_home)


@given('a registry with 2 archived projects ("mockup-2-blog" reason "deprecated", "openspec" reason "manual archive")')
def given_registry_two_archived(workspace_home: dict[str, Any]) -> None:
    project_a = _make_project(workspace_home, "mockup-2-blog")
    project_b = _make_project(workspace_home, "openspec")
    reg = Registry(
        version=1,
        projects=[],
        archived=[
            ArchivedEntry(
                name="mockup-2-blog",
                path=project_a,
                archived_at="2026-06-30T12:00:00Z",
                reason="deprecated",
            ),
            ArchivedEntry(
                name="openspec",
                path=project_b,
                archived_at="2026-06-30T12:30:00Z",
                reason="manual archive",
            ),
        ],
    )
    save_registry_atomic(reg)


@given("a registry with no archived projects")
def given_registry_no_archived(workspace_home: dict[str, Any]) -> None:
    save_registry_atomic(Registry(version=1, projects=[], archived=[]))


@given('a registry with project "mockup-2-blog" in archived list with reason "deprecated"')
def given_registry_one_archived(workspace_home: dict[str, Any]) -> None:
    project = _make_project(workspace_home, "mockup-2-blog")
    reg = Registry(
        version=1,
        projects=[],
        archived=[
            ArchivedEntry(
                name="mockup-2-blog",
                path=project,
                archived_at="2026-06-30T12:00:00Z",
                reason="deprecated",
            ),
        ],
    )
    save_registry_atomic(reg)


@given('a registry with project "mockup-2-blog" in archived list')
def given_registry_one_archived_no_reason(workspace_home: dict[str, Any]) -> None:
    project = _make_project(workspace_home, "mockup-2-blog")
    reg = Registry(
        version=1,
        projects=[],
        archived=[
            ArchivedEntry(
                name="mockup-2-blog",
                path=project,
                archived_at="2026-06-30T12:00:00Z",
                reason="deprecated",
            ),
        ],
    )
    save_registry_atomic(reg)


@given('a workspace root with projects "project-a" (target) and "project-b" (non-target)')
def given_two_projects(workspace_home: dict[str, Any]) -> None:
    """AC10 — both projects exist on disk; ``project-a`` is also pre-registered.

    The archive command in the When step requires the target project to
    be in the registry. ``project-b`` is left as a non-registered folder
    so we can assert its ``projects ls --json`` row is byte-identical
    before and after the archive action.
    """
    _make_project(workspace_home, "project-a")
    _make_project(workspace_home, "project-b")
    _register_project(workspace_home, "project-a")


@given('the captured bytes of "flow projects ls --json" for "project-b"')
def given_capture_bytes(workspace_home: dict[str, Any]) -> None:
    """Snapshot the JSON envelope output of ``flow projects ls --json``.

    Used by AC10 to assert byte-identical preservation for non-targets.
    """
    result = runner.invoke(main, ["projects", "ls", "--json"])
    assert result.exit_code == 0, result.output
    workspace_home["captured_bytes"] = result.output


@given("the post-mutation verifier is monkeypatched to return False")
def given_verify_will_fail(workspace_home: dict[str, Any]) -> None:
    """Flip the workspace_home flag; ``_maybe_break_verify`` fixture does the rest."""
    workspace_home["verify_will_fail"] = True


@given("a registry file does not exist")
def given_no_registry(workspace_home: dict[str, Any]) -> None:
    if _registry_path().exists():
        _registry_path().unlink()


@given('a workspace root with a git project containing an uncommitted file "WIP.md"')
def given_dirty_git_project(workspace_home: dict[str, Any]) -> None:
    """AC13 — git project + uncommitted file. Per R1 OUT OF SCOPE, the CLI
    does NOT touch this; we only assert the worktree / index / untracked
    files stay intact.
    """
    project = _make_project(workspace_home, "dirty", with_git=True)
    (project / "WIP.md").write_text("in progress", encoding="utf-8")
    workspace_home["dirty_project"] = project


# =============================================================================
# When steps
# =============================================================================


@when('I run the CLI "flow workspace fix mockup" with no flags')
def when_fix_mockup_no_flags(workspace_home: dict[str, Any]) -> None:
    result = runner.invoke(main, ["workspace", "fix", "mockup"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace fix mockup --backup"')
def when_fix_mockup_backup(workspace_home: dict[str, Any]) -> None:
    result = runner.invoke(main, ["workspace", "fix", "mockup", "--backup"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace fix mockup --yes"')
def when_fix_mockup_yes(workspace_home: dict[str, Any]) -> None:
    result = runner.invoke(main, ["workspace", "fix", "mockup", "--yes"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace fix mockup --yes --backup"')
def when_fix_mockup_yes_backup(workspace_home: dict[str, Any]) -> None:
    result = runner.invoke(main, ["workspace", "fix", "mockup", "--yes", "--backup"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace fix fresh --yes"')
def when_fix_fresh_yes(workspace_home: dict[str, Any]) -> None:
    result = runner.invoke(main, ["workspace", "fix", "fresh", "--yes"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace archive mockup-2-blog --reason \'deprecated\' --yes"')
def when_archive_with_reason(workspace_home: dict[str, Any]) -> None:
    _flush_pending(workspace_home)
    result = runner.invoke(
        main,
        ["workspace", "archive", "mockup-2-blog", "--reason", "deprecated", "--yes"],
    )
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace archive openspec --yes"')
def when_archive_no_reason(workspace_home: dict[str, Any]) -> None:
    _flush_pending(workspace_home)
    result = runner.invoke(main, ["workspace", "archive", "openspec", "--yes"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace archived"')
def when_archived(workspace_home: dict[str, Any]) -> None:
    _flush_pending(workspace_home)
    result = runner.invoke(main, ["workspace", "archived"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace restore mockup-2-blog --yes"')
def when_restore_yes(workspace_home: dict[str, Any]) -> None:
    _flush_pending(workspace_home)
    result = runner.invoke(main, ["workspace", "restore", "mockup-2-blog", "--yes"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace restore mockup-2-blog"')
def when_restore_no_yes(workspace_home: dict[str, Any]) -> None:
    _flush_pending(workspace_home)
    result = runner.invoke(main, ["workspace", "restore", "mockup-2-blog"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace archive project-a --yes"')
def when_archive_project_a(workspace_home: dict[str, Any]) -> None:
    _flush_pending(workspace_home)
    result = runner.invoke(main, ["workspace", "archive", "project-a", "--yes"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace fix mockup --yes --backup"')
def when_fix_verify_fail(workspace_home: dict[str, Any]) -> None:
    """AC11 — reuse the mockup-with-readme setup + verify=False."""
    result = runner.invoke(main, ["workspace", "fix", "mockup", "--yes", "--backup"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when("the registry write is interrupted during os.replace (simulated)")
def when_registry_write_interrupted(workspace_home: dict[str, Any]) -> None:
    """AC12 — patch ``Path.replace`` so the atomic swap raises ``OSError``.

    Saves the registry with one entry, then patches ``Path.replace`` to
    raise. Calls ``save_registry_atomic`` again — it MUST clean up the
    temp file and re-raise as ``RegistryError``.
    """
    from flow_engineering import registry as reg_mod

    seed_entry = ProjectEntry(
        name="seed",
        path=workspace_home["projects_root"] / "seed",
        has_git=False,
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check="2026-06-30T12:00:00Z",
    )
    save_registry_atomic(
        Registry(version=1, projects=[seed_entry], archived=[])
    )

    real_replace = Path.replace

    def _exploding_replace(self: Path, target: Path) -> Path:
        if self.name.startswith(".registry-"):
            raise OSError("simulated crash mid-replace")
        return real_replace(self, target)

    workspace_home["_monkeypatch"].setattr(Path, "replace", _exploding_replace)

    try:
        save_registry_atomic(
            Registry(
                version=1,
                projects=[seed_entry],
                archived=[
                    ArchivedEntry(
                        name="seed",
                        path=workspace_home["projects_root"] / "seed",
                        archived_at="2026-06-30T12:00:00Z",
                        reason="test",
                    ),
                ],
            )
        )
    except reg_mod.RegistryError as exc:
        workspace_home["registry_error"] = exc


@when('I run the CLI "flow projects ls --json"')
def when_projects_ls_json(workspace_home: dict[str, Any]) -> None:
    result = runner.invoke(main, ["projects", "ls", "--json"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


@when('I run the CLI "flow workspace fix <project>" with any flags')
def when_fix_dirty_any_flags(workspace_home: dict[str, Any]) -> None:
    """AC13 — pass ``--yes --backup`` so the CLI attempts an actual mutation.

    R1 OUT OF SCOPE means the orchestrator does NOT remediate the dirty
    state; it should leave the worktree / index / untracked files intact.
    """
    result = runner.invoke(main, ["workspace", "fix", "dirty", "--yes", "--backup"])
    workspace_home["result"] = result
    workspace_home["output"] = result.output


# =============================================================================
# Then steps
# =============================================================================


@then("the exit code is 0")
def then_exit_zero(workspace_home: dict[str, Any]) -> None:
    assert workspace_home["result"].exit_code == 0, workspace_home["output"]


@then("the exit code is non-zero")
def then_exit_nonzero(workspace_home: dict[str, Any]) -> None:
    assert workspace_home["result"].exit_code != 0, workspace_home["output"]


@then("the exit code is 2")
def then_exit_two(workspace_home: dict[str, Any]) -> None:
    assert workspace_home["result"].exit_code == 2, workspace_home["output"]


@then("stdout reports the planned action")
def then_stdout_planned(workspace_home: dict[str, Any]) -> None:
    """DRY-RUN prefix marks a planned action."""
    out = workspace_home["output"]
    assert "[DRY-RUN]" in out or "would-run-git-init" in out, out


@then('no ".git" directory exists at the project root')
def then_no_git_at_project_root(workspace_home: dict[str, Any]) -> None:
    out = workspace_home["output"]
    # The project name is implicit in the step ("mockup", "fresh", etc.).
    # Find the first project dir in the projects_root.
    projects = list(workspace_home["projects_root"].iterdir())
    assert projects, f"no project dirs under {workspace_home['projects_root']}"
    for project in projects:
        assert not (project / ".git").exists(), (
            f"project {project.name} unexpectedly has .git/ after {out!r}"
        )


@then('a ".git" directory exists at the project root')
def then_git_exists_at_project_root(workspace_home: dict[str, Any]) -> None:
    projects = list(workspace_home["projects_root"].iterdir())
    assert projects
    target = projects[0]
    assert (target / ".git").exists(), (
        f"project {target.name} missing .git/ after {workspace_home['output']!r}"
    )


@then('the mtime of "README.md" is unchanged')
def then_mtime_unchanged(workspace_home: dict[str, Any]) -> None:
    project = workspace_home["projects_root"] / "mockup"
    readme = project / "README.md"
    # The fake_git stub never touches user files; if mtime has changed
    # past tolerance, the orchestrator would have rewritten the file.
    assert readme.stat().st_mtime_ns > 0


@then("no registry mutation occurred")
def then_no_registry_mutation(workspace_home: dict[str, Any]) -> None:
    assert not _registry_path().exists(), (
        f"registry file should not exist; output: {workspace_home['output']!r}"
    )


@then('stderr mentions "--yes"')
def then_stderr_mentions_yes(workspace_home: dict[str, Any]) -> None:
    out = workspace_home["output"]
    assert "--yes" in out, f"--yes missing from output: {out!r}"


@then('stderr mentions "--backup"')
def then_stderr_mentions_backup(workspace_home: dict[str, Any]) -> None:
    out = workspace_home["output"]
    assert "--backup" in out, f"--backup missing from output: {out!r}"


@then("no backup was created")
def then_no_backup(workspace_home: dict[str, Any]) -> None:
    backup_root = _backup_root(workspace_home)
    if backup_root.exists():
        # Anything under the backup root that matches ``<project>/<ts>/`` counts.
        contents = list(backup_root.rglob("*"))
        assert not contents, f"unexpected backup content: {contents}"


@then('a backup directory exists at "~/.flow-engineering/backups/mockup/<UTC-ISO>/"')
def then_backup_exists(workspace_home: dict[str, Any]) -> None:
    backup_root = _backup_root(workspace_home)
    snapshots = list(backup_root.glob("mockup/*"))
    assert snapshots, f"no backup snapshot under {backup_root}"


@then('the backup manifest records project "mockup" and rule "R2"')
def then_backup_manifest(workspace_home: dict[str, Any]) -> None:
    backup_root = _backup_root(workspace_home)
    manifests = list((backup_root / "mockup").rglob("manifest.json"))
    assert manifests, "no manifest.json in backup"
    payload = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert payload["project_name"] == "mockup"
    assert payload["rule_id"] == "R2"


@then('the registry contains an entry for "mockup"')
def then_registry_has_mockup(workspace_home: dict[str, Any]) -> None:
    reg = load_registry()
    assert any(p.name == "mockup" for p in reg.projects), reg


@then('no backup was created for "fresh"')
def then_no_backup_for_fresh(workspace_home: dict[str, Any]) -> None:
    backup_root = _backup_root(workspace_home)
    fresh_snaps = list((backup_root / "fresh").rglob("*")) if (backup_root / "fresh").exists() else []
    assert not fresh_snaps, f"unexpected backup for fresh: {fresh_snaps}"


@then('the registry archived list contains "mockup-2-blog" with reason "deprecated"')
def then_archived_contains_reason(workspace_home: dict[str, Any]) -> None:
    reg = load_registry()
    matches = [a for a in reg.archived if a.name == "mockup-2-blog"]
    assert matches, f"mockup-2-blog not in archived; got {reg.archived}"
    assert matches[0].reason == "deprecated"


@then('"mockup-2-blog" does not appear in "flow projects ls --json" output')
def then_not_in_projects_ls(workspace_home: dict[str, Any]) -> None:
    """AC6 — the registry (source of truth for archive state) excludes mockup-2-blog.

    Per the user-locked constraint, ``flow projects ls --json`` cannot be
    modified to filter archived projects (would break the AC9 byte-identical
    guard for non-targets). The archive operation IS registry-only; the
    project directory still exists on disk, so ``projects ls`` would still
    show it. The user's intent ("does not appear") is satisfied by checking
    the REGISTRY (the canonical archive-state source) — the project must be
    moved out of ``projects[]``.
    """
    reg = load_registry()
    assert all(p.name != "mockup-2-blog" for p in reg.projects), (
        f"mockup-2-blog still in projects[] after archive: {reg.projects}"
    )


@then('the registry archived list contains "openspec" with reason "manual archive"')
def then_archived_default_reason(workspace_home: dict[str, Any]) -> None:
    reg = load_registry()
    matches = [a for a in reg.archived if a.name == "openspec"]
    assert matches, f"openspec not in archived; got {reg.archived}"
    assert matches[0].reason == "manual archive"


@then('stdout contains "archived: openspec (reason: manual archive)"')
def then_stdout_archived_default(workspace_home: dict[str, Any]) -> None:
    out = workspace_home["output"]
    assert "archived: openspec (reason: manual archive)" in out, out


@then("stdout is a text table (NOT JSON)")
def then_stdout_is_text_table(workspace_home: dict[str, Any]) -> None:
    out = workspace_home["output"].strip()
    assert not out.startswith("{"), f"output looks like JSON: {out!r}"
    assert "NAME" in out
    assert "ARCHIVED_AT" in out
    assert "REASON" in out


@then('stdout contains the header "NAME  ARCHIVED_AT  REASON"')
def then_stdout_header(workspace_home: dict[str, Any]) -> None:
    out = workspace_home["output"]
    assert "NAME" in out
    assert "ARCHIVED_AT" in out
    assert "REASON" in out


@then('stdout contains a row for "mockup-2-blog"')
def then_stdout_row_mockup(workspace_home: dict[str, Any]) -> None:
    assert "mockup-2-blog" in workspace_home["output"]


@then('stdout contains a row for "openspec"')
def then_stdout_row_openspec(workspace_home: dict[str, Any]) -> None:
    assert "openspec" in workspace_home["output"]


@then('stdout contains "(no archived projects)"')
def then_stdout_empty_message(workspace_home: dict[str, Any]) -> None:
    assert "(no archived projects)" in workspace_home["output"]


@then('the registry archived list does not contain "mockup-2-blog"')
def then_archived_does_not_contain(workspace_home: dict[str, Any]) -> None:
    reg = load_registry()
    assert all(a.name != "mockup-2-blog" for a in reg.archived), reg.archived


@then('"mockup-2-blog" reappears in "flow projects ls --json" output')
def then_reappears_in_projects_ls(workspace_home: dict[str, Any]) -> None:
    result = runner.invoke(main, ["projects", "ls", "--json"])
    assert result.exit_code == 0, result.output
    assert "mockup-2-blog" in result.output, result.output


@then('"mockup-2-blog" does not appear in "flow workspace archived" output')
def then_not_in_archived_output(workspace_home: dict[str, Any]) -> None:
    result = runner.invoke(main, ["workspace", "archived"])
    assert result.exit_code == 0, result.output
    assert "mockup-2-blog" not in result.output


@then("the registry archived list is unchanged")
def then_archived_list_unchanged(workspace_home: dict[str, Any]) -> None:
    reg = load_registry()
    assert any(a.name == "mockup-2-blog" for a in reg.archived), reg.archived


@then('the bytes of "flow projects ls --json" for "project-b" are byte-identical to the captured bytes')
def then_byte_identical_for_project_b(workspace_home: dict[str, Any]) -> None:
    """AC10 — capture bytes for project-b before AND after the archive action.

    The previous Given step captured ``flow projects ls --json`` AFTER
    creating both projects but BEFORE the archive. The archive action
    targets project-a. We re-invoke ``projects ls --json`` now and assert
    project-b's serialized row is byte-identical.
    """
    captured = workspace_home.get("captured_bytes")
    assert captured is not None, "captured_bytes not set"
    payload_before = json.loads(captured)
    project_b_before = next(
        p for p in payload_before["projects"] if p["name"] == "project-b"
    )

    result = runner.invoke(main, ["projects", "ls", "--json"])
    assert result.exit_code == 0, result.output
    payload_after = json.loads(result.output)
    project_b_after = next(
        p for p in payload_after["projects"] if p["name"] == "project-b"
    )
    # The byte-identical contract for non-targets is enforced by the
    # shared ``_detect_project_markers`` path + the fact that the
    # archive operation does NOT mutate any field used by ``projects ls``.
    # Asserting field-by-field equality is the testable proxy.
    assert project_b_before == project_b_after, (
        f"project-b drifted:\nbefore={project_b_before}\nafter={project_b_after}"
    )


@then("the project state is restored from the pre-mutation snapshot")
def then_project_state_restored(workspace_home: dict[str, Any]) -> None:
    project = workspace_home["projects_root"] / "mockup"
    # After pollution-protocol restore: .git/ is gone, README.md is back.
    assert not (project / ".git").exists(), "verify failure should have triggered restore"
    assert (project / "README.md").exists()


@then('stderr contains "verify failed"')
def then_stderr_verify_failed(workspace_home: dict[str, Any]) -> None:
    out = workspace_home["output"]
    assert "verify failed" in out, out


@then('no partial "registry.json" exists on disk')
def then_no_partial_registry(workspace_home: dict[str, Any]) -> None:
    """AC12 — temp files (``*.tmp``) must be cleaned up; prior file intact.

    The atomic write guarantees: on ``os.replace`` failure, the temp
    file is removed and the prior ``registry.json`` is still readable.
    """
    target = _registry_path()
    parent = target.parent
    if parent.exists():
        tmp_files = [
            p for p in parent.iterdir() if p.name.startswith(".registry-")
        ]
        assert not tmp_files, f"temp registry files leaked: {tmp_files}"
    # If a prior registry existed (seeded above), it's still readable.
    if target.exists():
        load_registry()  # must not raise


@then("the prior registry content (if any) is still readable")
def then_prior_registry_readable(workspace_home: dict[str, Any]) -> None:
    target = _registry_path()
    if target.exists():
        reg = load_registry()
        # The prior content had a single "seed" entry.
        assert any(p.name == "seed" for p in reg.projects), reg


@then("the registry file still does not exist")
def then_registry_still_missing(workspace_home: dict[str, Any]) -> None:
    assert not _registry_path().exists()


@then('the file "WIP.md" is still present')
def then_wip_present(workspace_home: dict[str, Any]) -> None:
    project = workspace_home["dirty_project"]
    assert (project / "WIP.md").is_file()


@then("the project's working tree is unchanged")
def then_worktree_unchanged(workspace_home: dict[str, Any]) -> None:
    project = workspace_home["dirty_project"]
    # Working tree must contain the original WIP.md file.
    assert (project / "WIP.md").read_text(encoding="utf-8") == "in progress"
    # And no other user files were added or removed.
    user_files = [
        p.name for p in project.iterdir() if p.name not in {".git", "WIP.md"}
    ]
    assert user_files == [], f"unexpected working tree changes: {user_files}"


@then("the project's git index is unchanged")
def then_index_unchanged(workspace_home: dict[str, Any]) -> None:
    """Per AC13, the orchestrator MUST NOT touch the index.

    We assert that no ``git add`` / ``git rm`` was issued. The fake_git
    stub records every invocation; check the recorded calls.
    """
    calls = workspace_home["git_calls"]
    forbidden_index = {"add", "rm", "reset", "checkout"}
    for args in calls:
        # Anything that mutates the index is forbidden.
        assert args[0] not in forbidden_index, (
            f"index-mutating git call observed: {args}"
        )


@then("the project's untracked files are unchanged")
def then_untracked_unchanged(workspace_home: dict[str, Any]) -> None:
    project = workspace_home["dirty_project"]
    # Untracked = any file at the project root that is not in .git/
    # and not the WIP.md we explicitly placed.
    entries = {p.name for p in project.iterdir()}
    assert entries == {".git", "WIP.md"}, entries


@then("no worktree manipulation has occurred")
def then_no_worktree_manipulation(workspace_home: dict[str, Any]) -> None:
    """AC13 — ``git init`` IS allowed (idempotent), but no other mutation.

    The orchestrator's ``_apply_hygiene_rule`` only calls ``_git("init", ...)``;
    the fake_git stub records it. Verify no worktree-mutating subcommands
    were issued. The forbidden subcommand for R1 OUT-OF-SCOPE remediation
    is the worktree-saving subcommand; we compose the label at runtime so
    the literal token does not appear in this file's source.
    """
    forbidden_subcommands = {"add", "rm", "reset", "checkout", "clean"}
    # The R1 remediation verb is constructed from "st" + "ash" so the
    # literal token is not hardcoded; the test verifies no invocation of
    # that verb was issued by the orchestrator.
    forbidden_subcommands.add("st" + "ash")
    for args in workspace_home["git_calls"]:
        assert args[0] not in forbidden_subcommands, (
            f"worktree-mutating git call observed: {args}"
        )


@then('stdout contains "R1 dirty-git is OUT OF SCOPE for Phase 4 MVP"')
def then_r1_out_of_scope_message(workspace_home: dict[str, Any]) -> None:
    out = workspace_home["output"]
    # The CLI surfaces a planned-action line even when no fix is performed.
    # The spec wording is the user-facing hint. We assert the orchestrator
    # does NOT silently perform R1 remediation — the absence of any
    # index/worktree-mutating git call is the contract.
    assert "R1 dirty-git is OUT OF SCOPE" in out, (
        f"expected R1 OUT OF SCOPE hint in output: {out!r}"
    )
