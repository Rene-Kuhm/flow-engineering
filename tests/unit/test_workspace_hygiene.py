"""Unit tests for ``flow_engineering.registry`` + ``flow_engineering.workspace_hygiene``.

Phase 4 (workspace-hygiene) PR1 = safety core. 18 unit tests across 8 tasks
(T-1..T-8). Tests assert the public behavior the spec requires — atomic write,
hidden-file exclusion, pollution-protocol restore, archive/restore round-trip.

Test layout follows strict TDD: each test was written BEFORE the production
code that satisfies it. The diff per task is the TDD evidence trail.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from unittest import mock as unittest_mock

import pytest
from pydantic import ValidationError

from flow_engineering import workspace_hygiene as wh
from flow_engineering.registry import (
    DEFAULT_REGISTRY_PATH,
    ArchivedEntry,
    ProjectEntry,
    Registry,
    RegistryError,
    load_registry,
    registry_path,
    save_registry_atomic,
)
from tests.unit._workspace_hygiene_fixtures import (
    make_fake_project,
    make_fake_registry,
    stub_home,
)

# =============================================================================
# T-1 — registry models + RegistryError + path helper
# =============================================================================


def test_registry_model_accepts_minimal_payload(tmp_path: Path) -> None:
    """T-1 RED→GREEN: a fresh ``Registry`` is valid with the v1 defaults.

    Empty payload round-trips through the model: ``version == 1``, both lists
    empty. The schema is pydantic v2 with ``extra="forbid"`` so unknown
    fields would raise; this test pins the minimal valid shape.
    """
    r = Registry()
    assert r.version == 1
    assert r.projects == []
    assert r.archived == []


def test_registry_model_rejects_unknown_fields() -> None:
    """T-1 REFACTOR: ``extra="forbid"`` rejects an unknown top-level key.

    Forward-compat: if a future ``version: 2`` shows up in the file before the
    code knows about it, the loader MUST refuse (not silently pass). This test
    pins the policy.
    """
    with pytest.raises(ValidationError):
        Registry.model_validate({"version": 1, "future_field": "x"})


def test_registry_path_resolves_under_path_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T-1: ``registry_path()`` re-evaluates ``Path.home()`` on every call.

    Cross-platform: tests stub ``Path.home()`` to point at ``tmp_path`` and
    assert the resolved path is exactly ``tmp_path / ".flow-engineering" /
    "registry.json"``. Critical because the module-level ``DEFAULT_REGISTRY_PATH``
    constant is captured at import time and may be stale; the helper is the
    always-correct accessor.
    """
    stub_home(monkeypatch, tmp_path)
    expected = tmp_path / ".flow-engineering" / "registry.json"
    assert registry_path() == expected
    assert DEFAULT_REGISTRY_PATH.name == "registry.json"


def test_registry_path_resolves_under_windows_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-1 cross-platform: Windows-style home ``C:\\Users\\test`` resolves correctly."""
    fake_home = Path("C:\\Users\\test")
    stub_home(monkeypatch, fake_home)
    assert registry_path() == fake_home / ".flow-engineering" / "registry.json"


def test_registry_path_resolves_under_posix_home(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-1 cross-platform: POSIX-style home ``/home/test`` resolves correctly."""
    fake_home = Path("/home/test")
    stub_home(monkeypatch, fake_home)
    assert registry_path() == fake_home / ".flow-engineering" / "registry.json"


def test_registry_error_is_runtime_error_with_user_message() -> None:
    """T-1: ``RegistryError`` carries a ``user_message`` for the CLI layer.

    The Click command layer reads ``e.user_message`` and prints it to stderr.
    The exception type MUST remain a ``RuntimeError`` subclass so generic
    OS error handlers (e.g., atexit) can still catch it.
    """
    err = RegistryError(user_message="registry file is corrupt")
    assert isinstance(err, RuntimeError)
    assert err.user_message == "registry file is corrupt"


# =============================================================================
# T-2 — load_registry + save_registry_atomic
# =============================================================================


def test_load_registry_missing_file_returns_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T-2: missing file → ``Registry(version=1, projects=[], archived=[])``.

    First-run UX: the user has never run `flow workspace fix` or `flow workspace
    archive`, so the registry does not exist. ``load_registry()`` MUST return
    an empty registry (not raise) so the CLI can do ``load + mutate + save``
    without a separate "create if missing" branch.
    """
    stub_home(monkeypatch, tmp_path)
    reg_file = registry_path()
    assert not reg_file.exists()  # safety: confirm pre-condition
    result = load_registry()
    assert result == Registry(version=1, projects=[], archived=[])


def test_save_registry_atomic_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T-2: save → load round-trips the v1 registry schema field-by-field.

    Verifies the ``model_dump(mode="json")`` serialization (Path → POSIX
    string) plus the atomic tempfile write both work. After save, the file
    MUST exist and parse back into a registry that equals the input.
    """
    stub_home(monkeypatch, tmp_path)
    entry = ProjectEntry(
        name="mockup",
        path=tmp_path / "mockup",
        has_git=False,
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check="2026-06-30T12:00:00Z",
    )
    original = Registry(version=1, projects=[entry], archived=[])

    save_registry_atomic(original)
    on_disk = json.loads(registry_path().read_text(encoding="utf-8"))
    assert on_disk["version"] == 1
    assert len(on_disk["projects"]) == 1
    assert on_disk["projects"][0]["name"] == "mockup"
    # The Path field MUST serialize as a string (POSIX-style on any platform).
    assert isinstance(on_disk["projects"][0]["path"], str)

    reloaded = load_registry()
    assert reloaded == original


def test_save_registry_atomic_no_partial_on_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-2: simulated mid-write crash leaves the prior file intact.

    Mirrors the AC12 contract: ``tempfile + os.replace`` atomicity. We
    pre-seed the file with valid JSON, monkeypatch ``Path.replace`` to raise,
    and assert (a) the prior file is unchanged and (b) no ``.tmp`` file is
    left lying around in the parent dir.
    """
    stub_home(monkeypatch, tmp_path)
    reg_file = registry_path()
    reg_file.parent.mkdir(parents=True, exist_ok=True)
    prior_content = (
        '{"version": 1, "projects": [{"name": "prior", '
        '"path": "/x/prior", "has_git": false, "has_openspec": false, '
        '"has_tests": false, "has_graphify": false, '
        '"last_status_check": "2026-01-01T00:00:00Z"}], "archived": []}'
    )
    reg_file.write_text(prior_content, encoding="utf-8")

    # Force the atomic swap to fail.
    def boom(self: Path, target: Path) -> Path:  # noqa: ARG001
        raise OSError("simulated crash mid-replace")

    monkeypatch.setattr(Path, "replace", boom)

    new_reg = Registry(
        version=1,
        projects=[
            ProjectEntry(
                name="new",
                path=tmp_path / "new",
                has_git=False,
                has_openspec=False,
                has_tests=False,
                has_graphify=False,
                last_status_check="2026-06-30T12:00:00Z",
            )
        ],
        archived=[],
    )

    with pytest.raises(RegistryError):
        save_registry_atomic(new_reg)

    # Prior file MUST be byte-identical to what we wrote.
    assert reg_file.read_text(encoding="utf-8") == prior_content
    # No stray temp file in the parent dir.
    leftovers = [p for p in reg_file.parent.iterdir() if p.name != "registry.json"]
    assert leftovers == [], f"temp files left behind: {leftovers}"


def test_load_registry_raises_on_malformed_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T-2: malformed JSON → ``RegistryError`` (not bare ``JSONDecodeError``).

    The CLI layer catches ``RegistryError`` uniformly. If the loader leaked a
    bare ``json.JSONDecodeError``, the user would see a stack trace instead
    of a clear "registry is corrupt; fix or delete it" message.
    """
    stub_home(monkeypatch, tmp_path)
    reg_file = registry_path()
    reg_file.parent.mkdir(parents=True, exist_ok=True)
    reg_file.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(RegistryError) as exc:
        load_registry()
    assert exc.value.user_message  # non-empty hint for the user


# =============================================================================
# T-3 — HygieneResult + exceptions + _now_iso_utc
# =============================================================================


def test_hygiene_result_frozen_dataclass() -> None:
    """T-3: ``HygieneResult`` is a frozen dataclass.

    Once the orchestrator returns a result, callers MUST NOT be able to
    mutate the fields (this would defeat the audit trail). The frozen
    contract is enforced by ``@dataclass(frozen=True)``.
    """
    result = wh.HygieneResult(
        rule_id="R2_GIT_INIT",
        project="mockup",
        action_taken="git init",
        dry_run=False,
        backup_path=None,
        success=True,
        error=None,
    )
    assert result.rule_id == "R2_GIT_INIT"
    assert result.dry_run is False
    assert result.success is True
    with pytest.raises((AttributeError, Exception)):  # FrozenInstanceError subclass
        result.success = False  # type: ignore[misc]


def test_mutation_gate_error_is_permission_error() -> None:
    """T-3: ``MutationGateError`` is a ``PermissionError`` subclass.

    Raising ``PermissionError`` is the semantic match for a missing
    --yes/--backup gate: the user is missing the right to mutate.
    """
    err = wh.MutationGateError(user_message="--yes required")
    assert isinstance(err, PermissionError)
    assert err.user_message == "--yes required"


def test_empty_project_error_is_value_error() -> None:
    """T-3: ``EmptyProjectError`` is a ``ValueError`` subclass.

    The trigger condition (non-empty project + missing --backup) is a
    contract violation, not a permission denial. ``ValueError`` lets callers
    catch validation problems without merging the two error classes.
    """
    err = wh.EmptyProjectError(
        user_message="--backup required",
        project=Path("/tmp/proj"),
        non_empty_files=["README.md"],
    )
    assert isinstance(err, ValueError)
    assert err.project == Path("/tmp/proj")
    assert err.non_empty_files == ["README.md"]


def test_now_iso_utc_format() -> None:
    """T-3: ``_now_iso_utc()`` returns ISO 8601 with a ``Z`` suffix.

    The backup directory name MUST be the literal return value, so the
    format is fixed-width ASCII: ``YYYY-MM-DDTHH:MM:SSZ``.
    """
    stamp = wh._now_iso_utc()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", stamp), stamp


# =============================================================================
# T-4 — _is_empty_project with hidden-file exclusion
# =============================================================================


@pytest.mark.parametrize(
    "files",
    [
        pytest.param([], id="truly_empty"),
        pytest.param([".DS_Store"], id="only_ds_store"),
        pytest.param(["Thumbs.db"], id="only_thumbs_db"),
        pytest.param(["desktop.ini"], id="only_desktop_ini"),
        pytest.param([".DS_Store", "Thumbs.db", "desktop.ini"], id="all_three_junk"),
    ],
)
def test_is_empty_project_true_cases(tmp_path: Path, files: list[str]) -> None:
    """T-4: project with ONLY OS junk (or nothing) counts as empty.

    Per design D-table row 6: ``.DS_Store`` (macOS Finder), ``Thumbs.db``
    (Windows thumbnail cache), ``desktop.ini`` (Windows folder customization)
    are NOT user content. The empty check excludes them.
    """
    project = make_fake_project("mockup", with_files=files, parent=tmp_path)
    assert wh._is_empty_project(project) is True


@pytest.mark.parametrize(
    "files",
    [
        pytest.param(["README.md"], id="readme_only"),
        pytest.param([".gitignore"], id="gitignore_only"),
        pytest.param([".env"], id="dotenv_only"),
        pytest.param([".DS_Store", "README.md"], id="junk_plus_user"),
        pytest.param([".vscode"], id="vscode_subdir"),  # subdir counts as user content
    ],
)
def test_is_empty_project_false_cases(tmp_path: Path, files: list[str]) -> None:
    """T-4: any user-visible content (including hidden user content) is non-empty.

    ``.gitignore`` / ``.env`` / ``.vscode/`` are user content even though they
    start with a dot. A subdirectory at the top level also counts (no
    recursion — a subdir is itself user work).
    """
    project = make_fake_project("mockup", with_files=files, parent=tmp_path)
    assert wh._is_empty_project(project) is False


# =============================================================================
# T-5 — _snapshot_project with manifest.json
# =============================================================================


def test_snapshot_project_creates_manifest_and_files(tmp_path: Path) -> None:
    """T-5: snapshot copies files + writes a manifest with the 7 spec fields."""
    project = make_fake_project(
        "mockup", with_files=["README.md", ".gitignore"], parent=tmp_path
    )
    backup_root = tmp_path / "backups"

    snapshot = wh._snapshot_project(project, backup_root, rule_id="R2")

    assert snapshot.is_dir()
    manifest_path = snapshot / "manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # The 7 spec fields per REQ-HYGIENE-BACKUP-LAYOUT.
    for field in (
        "project_name",
        "project_path",
        "rule_id",
        "git_status_pre",
        "files_count",
        "bytes_total",
        "created_at",
    ):
        assert field in manifest, f"manifest missing field: {field}"
    assert manifest["project_name"] == "mockup"
    assert manifest["rule_id"] == "R2"
    assert manifest["git_status_pre"] is False
    # Files copied under files/ subdir.
    files_dir = snapshot / "files"
    assert (files_dir / "README.md").is_file()
    assert (files_dir / ".gitignore").is_file()
    # ``created_at`` MUST equal the snapshot directory name.
    assert manifest["created_at"] == snapshot.name


def test_snapshot_project_excludes_dotgit(tmp_path: Path) -> None:
    """T-5: ``.git/`` MUST NOT be copied into the snapshot (it's a new repo)."""
    project = make_fake_project(
        "mockup", with_files=["README.md"], with_git=False, parent=tmp_path
    )
    # Add a real .git/ after construction (with a sentinel file).
    git_dir = project / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    backup_root = tmp_path / "backups"

    snapshot = wh._snapshot_project(project, backup_root, rule_id="R2")
    files_dir = snapshot / "files"
    assert (files_dir / "README.md").is_file()
    assert not (files_dir / ".git").exists(), "snapshot must not contain .git/"


# =============================================================================
# T-6 — _verify_post_mutation + _restore_from_snapshot
# =============================================================================


def test_verify_post_mutation_returns_true_on_valid_git(tmp_path: Path) -> None:
    """T-6: ``_verify_post_mutation`` returns True iff ``.git/`` is well-formed.

    Uses the real ``git init`` subprocess (the same path T-7 takes) so the
    verifier is tested against genuine git output, not a hand-crafted stub.
    """
    project = make_fake_project("mockup", parent=tmp_path)
    backup_root = tmp_path / "backups"
    snapshot = wh._snapshot_project(project, backup_root, rule_id="R2")

    cp = subprocess.run(
        ["git", "init", str(project)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert cp.returncode == 0, cp.stderr
    assert wh._verify_post_mutation(project, snapshot) is True


def test_restore_from_snapshot_round_trip(tmp_path: Path) -> None:
    """T-6: snapshot → delete content → restore brings files back identically."""
    project = make_fake_project("mockup", with_files=["A.md"], parent=tmp_path)
    (project / "A.md").write_text("important content", encoding="utf-8")
    backup_root = tmp_path / "backups"
    snapshot = wh._snapshot_project(project, backup_root, rule_id="R2")

    # Simulate the mutation having nuked user content.
    (project / "A.md").unlink()
    assert not (project / "A.md").exists()

    wh._restore_from_snapshot(snapshot, project)
    assert (project / "A.md").is_file()
    assert (project / "A.md").read_text(encoding="utf-8") == "important content"


def test_pollution_protocol_restore_on_verify_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-6/T-7 wiring: if verify fails, the snapshot is restored.

    Sets up a real ``git init`` (so the post-state WOULD pass verification),
    then monkeypatches ``_verify_post_mutation`` to return ``False``. The
    triple restores from the snapshot: ``.git/`` is removed and the
    pre-mutation file content is back.
    """
    project = make_fake_project(
        "mockup", with_files=["README.md"], parent=tmp_path
    )
    backup_root = tmp_path / "backups"
    snapshot = wh._snapshot_project(project, backup_root, rule_id="R2")

    # Run a real git init so .git/ would normally exist.
    cp = subprocess.run(
        ["git", "init", str(project)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert cp.returncode == 0
    assert (project / ".git").exists()

    # Force verify to fail; the orchestrator will then call _restore_from_snapshot.
    monkeypatch.setattr(wh, "_verify_post_mutation", lambda *_a, **_kw: False)

    # Simulate the orchestrator's verify-failure branch.
    if not wh._verify_post_mutation(project, snapshot):
        wh._restore_from_snapshot(snapshot, project)

    # After restore: .git/ gone, README.md back.
    assert not (project / ".git").exists(), "restore must remove .git/"
    assert (project / "README.md").is_file()


# =============================================================================
# T-7 — _apply_hygiene_rule orchestrator
# =============================================================================


def _stub_git_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``cli._git`` with a no-op that reports success for ``init``."""
    from flow_engineering import cli as cli_mod

    def fake_git(*args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        cp = subprocess.CompletedProcess(
            args=["git", *args], returncode=0, stdout="", stderr=""
        )
        if args and args[0] == "init":
            # The real git init also creates .git/. We mirror that side effect
            # so ``_verify_post_mutation`` can see a real .git/ directory.
            target = Path(args[1]) if len(args) > 1 else None
            if target is not None:
                (target / ".git").mkdir(exist_ok=True)
                (target / ".git" / "HEAD").write_text(
                    "ref: refs/heads/main\n", encoding="utf-8"
                )
                (target / ".git" / "config").write_text(
                    "[core]\n\trepositoryformatversion = 0\n", encoding="utf-8"
                )
        return cp

    monkeypatch.setattr(cli_mod, "_git", fake_git)


def _make_project_entry(tmp_path: Path, name: str = "mockup") -> ProjectEntry:
    """Build a ``ProjectEntry`` for a non-git project under ``tmp_path``."""
    project = make_fake_project(name, parent=tmp_path)
    return ProjectEntry(
        name=name,
        path=project,
        has_git=False,
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check="2026-06-30T12:00:00Z",
    )


def test_apply_hygiene_rule_dry_run_does_not_mutate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-7: dry-run returns a success result and touches NOTHING on disk.

    Verifies: no ``.git/`` created, no backup directory created, no registry
    file written. The user sees a planned-action report; nothing changes.
    """
    stub_home(monkeypatch, tmp_path)
    entry = _make_project_entry(tmp_path)
    backup_root = tmp_path / "backups"

    result = wh._apply_hygiene_rule(
        entry,
        "R2_GIT_INIT",
        dry_run=True,
        yes=True,
        backup=True,
        backup_root=backup_root,
    )

    assert result.success is True
    assert result.dry_run is True
    assert result.action_taken == "would-run-git-init"
    assert not (entry.path / ".git").exists()
    assert not backup_root.exists()
    assert not registry_path().exists()


def test_apply_hygiene_rule_refuses_without_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-7: missing ``--yes`` (and not dry-run) → ``MutationGateError``."""
    stub_home(monkeypatch, tmp_path)
    entry = _make_project_entry(tmp_path)
    backup_root = tmp_path / "backups"

    with pytest.raises(wh.MutationGateError) as exc:
        wh._apply_hygiene_rule(
            entry,
            "R2_GIT_INIT",
            dry_run=False,
            yes=False,
            backup=True,
            backup_root=backup_root,
        )
    assert "--yes" in exc.value.user_message


def test_apply_hygiene_rule_refuses_non_empty_without_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-7: non-empty project + no ``--backup`` → ``EmptyProjectError``."""
    stub_home(monkeypatch, tmp_path)
    # Make the project NON-empty (a README + .gitignore).
    project = make_fake_project(
        "mockup", with_files=["README.md", ".gitignore"], parent=tmp_path
    )
    entry = ProjectEntry(
        name="mockup",
        path=project,
        has_git=False,
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check="2026-06-30T12:00:00Z",
    )
    backup_root = tmp_path / "backups"

    with pytest.raises(wh.EmptyProjectError) as exc:
        wh._apply_hygiene_rule(
            entry,
            "R2_GIT_INIT",
            dry_run=False,
            yes=True,
            backup=False,
            backup_root=backup_root,
        )
    assert "--backup" in exc.value.user_message
    assert "README.md" in exc.value.non_empty_files


def test_apply_hygiene_rule_happy_path_creates_git_and_registry_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-7: ``--yes --backup`` on non-empty project → ``.git/`` + backup + registry.

    End-to-end happy path: snapshot is taken, ``git init`` runs (stubbed),
    verify passes, registry is appended + saved. Tests the orchestrator
    wires every helper correctly.
    """
    stub_home(monkeypatch, tmp_path)
    _stub_git_success(monkeypatch)
    project = make_fake_project(
        "mockup", with_files=["README.md", ".gitignore"], parent=tmp_path
    )
    entry = ProjectEntry(
        name="mockup",
        path=project,
        has_git=False,
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check="2026-06-30T12:00:00Z",
    )
    backup_root = tmp_path / "backups"

    result = wh._apply_hygiene_rule(
        entry,
        "R2_GIT_INIT",
        dry_run=False,
        yes=True,
        backup=True,
        backup_root=backup_root,
    )
    assert result.success is True
    assert result.dry_run is False
    assert (project / ".git").is_dir()
    assert backup_root.is_dir()
    # Registry now has one entry.
    reg_after = load_registry()
    assert len(reg_after.projects) == 1
    assert reg_after.projects[0].name == "mockup"
    assert reg_after.projects[0].path == project


# =============================================================================
# T-7 fix-up — safety posture (user-found defect caught by code review)
#
# Three defects were found in the original `_apply_hygiene_rule`:
#   1. `_git("init", ...)` return code was discarded; non-zero rc silently
#      proceeded to registry update, marking the project has_git=True on a
#      failed git init.
#   2. `_verify_post_mutation` was conditional on snapshot existence, so
#      empty projects (no snapshot) skipped verify entirely.
#   3. Registry update was not gated on verify success for empty projects.
#
# The 3 tests below pin the corrected behavior end-to-end through the
# orchestrator. They are RED-first: each test exercises a path the buggy
# code would mishandle (or skip coverage for). The fix is in
# `_apply_hygiene_rule` Steps 5b/6/7.
# =============================================================================


def _stub_git_failure(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncode: int = 128,
    stderr: bytes = b"fatal: unable to init",
) -> None:
    """Replace ``cli._git`` with a stub that reports failure (no side effects).

    Unlike :func:`_stub_git_success`, this stub does NOT create a ``.git/``
    directory on disk. That mirrors a real ``git init`` failure on Windows
    (e.g., antivirus interference, FS corruption, locked directory) where
    the rc is non-zero AND no scaffolding was produced.
    """
    from flow_engineering import cli as cli_mod

    def fake_git(*args: str, **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            args=["git", *args],
            returncode=returncode,
            stdout=b"",
            stderr=stderr,
        )

    monkeypatch.setattr(cli_mod, "_git", fake_git)


def test_apply_hygiene_rule_empty_git_init_failure_no_registry_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fix-up #1: empty project + ``git init`` rc=128 → no mutation, no registry.

    The original code discarded ``_git``'s return code. With the stub
    reporting rc=128 (and no ``.git/`` side effect), the buggy code skipped
    verify (snapshot is None for an empty project), fell through to the
    registry update step, and wrote ``has_git=True`` for a failed init.
    The fixed code captures the rc and short-circuits to a failure result
    BEFORE verify and BEFORE the registry update.
    """
    stub_home(monkeypatch, tmp_path)
    _stub_git_failure(monkeypatch, returncode=128, stderr=b"fatal: bad init")
    entry = _make_project_entry(tmp_path, name="emptyproj")
    backup_root = tmp_path / "backups"

    result = wh._apply_hygiene_rule(
        entry,
        "R2",
        dry_run=False,
        yes=True,
        backup=False,
        backup_root=backup_root,
    )

    # The orchestrator reports the failure with the captured return code.
    assert result.success is False
    assert result.error is not None
    assert "git init failed (rc=128)" in result.error

    # The registry MUST NOT contain the project (it was a failed init).
    reg_after = load_registry()
    assert all(p.name != "emptyproj" for p in reg_after.projects)

    # The filesystem MUST NOT have a .git/ (the mock did not create one,
    # and the fix MUST NOT have side-effects after rc != 0).
    assert not (entry.path / ".git").exists()


def test_apply_hygiene_rule_empty_git_init_success_verify_false_no_registry_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fix-up #2: empty project + git init rc=0 but verify=False → no registry.

    The original code only ran ``_verify_post_mutation`` when a snapshot
    existed. For an empty project with ``backup=False``, ``snapshot is None``
    so the verify step was a no-op and the registry update ran even when
    verify would have failed. The fixed code runs verify UNCONDITIONALLY.
    """
    stub_home(monkeypatch, tmp_path)
    # rc=0 (git init "succeeded" from subprocess perspective) but verify
    # will return False (corrupt .git/ — simulate by mocking).
    _stub_git_failure(
        monkeypatch, returncode=0, stderr=b""
    )  # rc=0 with no .git/ side effect
    monkeypatch.setattr(wh, "_verify_post_mutation", lambda *_a, **_kw: False)
    # Spy on _restore_from_snapshot: must NOT be called (no snapshot to
    # restore from for an empty project with backup=False).
    restore_mock = unittest_mock.MagicMock()
    monkeypatch.setattr(wh, "_restore_from_snapshot", restore_mock)

    entry = _make_project_entry(tmp_path, name="emptyproj2")
    backup_root = tmp_path / "backups"

    result = wh._apply_hygiene_rule(
        entry,
        "R2",
        dry_run=False,
        yes=True,
        backup=False,
        backup_root=backup_root,
    )

    assert result.success is False
    assert result.error == "verify failed"

    # Registry unchanged.
    reg_after = load_registry()
    assert all(p.name != "emptyproj2" for p in reg_after.projects)

    # No restore was attempted (nothing to restore from).
    assert restore_mock.call_count == 0


def test_apply_hygiene_rule_non_empty_backup_verify_false_restores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fix-up #3: non-empty + backup + verify=False → restore + no registry.

    Full orchestrator wiring for the pollution-protocol restore path. The
    original code already triggered restore when ``snapshot is not None``,
    so this test is a REGRESSION GUARD for that path through the
    orchestrator (the existing ``test_pollution_protocol_restore_on_verify_fail``
    only exercised the helpers in isolation, not the orchestrator's wiring).
    The fix makes the verify check unconditional — this test confirms the
    non-empty-with-backup path still works after that change.
    """
    stub_home(monkeypatch, tmp_path)
    _stub_git_success(monkeypatch)
    # Force verify to fail so the orchestrator takes the restore branch.
    monkeypatch.setattr(wh, "_verify_post_mutation", lambda *_a, **_kw: False)

    project = make_fake_project(
        "nonempty",
        with_files=["README.md"],
        parent=tmp_path,
    )
    # Give the pre-mutation files known content so the assertion is exact.
    (project / "README.md").write_text("hello world", encoding="utf-8")
    # Nested dir + file: ``make_fake_project`` does not create parents,
    # so we build the src/ tree explicitly.
    (project / "src").mkdir()
    (project / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")

    entry = ProjectEntry(
        name="nonempty",
        path=project,
        has_git=False,
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check="2026-06-30T12:00:00Z",
    )
    backup_root = tmp_path / "backups"

    # Spy on _restore_from_snapshot: must be called exactly once.
    real_restore = wh._restore_from_snapshot
    restore_calls: list[tuple[Path, Path]] = []

    def spy_restore(snapshot: Path, target: Path) -> None:
        restore_calls.append((snapshot, target))
        real_restore(snapshot, target)

    monkeypatch.setattr(wh, "_restore_from_snapshot", spy_restore)

    result = wh._apply_hygiene_rule(
        entry,
        "R2",
        dry_run=False,
        yes=True,
        backup=True,
        backup_root=backup_root,
    )

    assert result.success is False
    assert result.error == "verify failed"

    # Snapshot directory exists at the expected path.
    snapshots_for_proj = list((backup_root / "nonempty").iterdir())
    assert len(snapshots_for_proj) == 1, (
        f"expected exactly 1 snapshot dir, got {snapshots_for_proj}"
    )
    snapshot_dir = snapshots_for_proj[0]
    assert re.match(r"^\d{8}T\d{6}Z$", snapshot_dir.name), (
        f"snapshot dir name must match compact UTC format, got {snapshot_dir.name}"
    )
    assert (snapshot_dir / "manifest.json").is_file()

    # _restore_from_snapshot was called exactly once.
    assert len(restore_calls) == 1
    assert restore_calls[0][0] == snapshot_dir
    assert restore_calls[0][1] == project

    # Filesystem state is restored: pre-mutation files intact, .git/ gone.
    assert (project / "README.md").read_text(encoding="utf-8") == "hello world"
    assert (project / "src" / "main.py").read_text(encoding="utf-8") == (
        "print('ok')\n"
    )
    assert not (project / ".git").exists(), (
        "restore must remove the .git/ created by the failed init"
    )

    # Registry unchanged (Step 7 not reached on the verify-fail branch).
    reg_after = load_registry()
    assert all(p.name != "nonempty" for p in reg_after.projects)


# =============================================================================
# Fix-up #2 — robust stderr handling for str/bytes/None (user-found defect
# caught during code review of fix-up #1)
#
# Defect: ``cli._git`` is invoked with ``text=True`` so ``cp.stderr`` is
# ``str``, not ``bytes``. The fix-up #1 code at Step 5b called
# ``cp.stderr.decode(...)`` which raises ``AttributeError`` on a ``str``.
# Safety is intact (Step 7 does not run), but the user saw an ugly
# traceback instead of a clean error message.
#
# The test below pins the production shape (str stderr) end-to-end through
# the orchestrator. The fix introduces ``_format_git_stderr(stderr)`` which
# normalizes bytes | str | None into a user-readable string. Empty stderr
# falls back to "unknown error" so the operator always sees a non-empty
# diagnostic.
# =============================================================================


def test_apply_hygiene_rule_git_init_failure_with_str_stderr_returns_clean_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fix-up #2 regression guard: ``cp.stderr`` is ``str`` (cli._git text=True).

    The production path returns ``CompletedProcess[str]`` with ``stderr``
    as a ``str``. Calling ``.decode()`` on a ``str`` raises
    ``AttributeError``. The fixed code routes through ``_format_git_stderr``
    which handles bytes | str | None and returns a clean error message
    without raising.
    """
    from flow_engineering import cli as cli_mod

    project_dir = tmp_path / "empty-project"
    project_dir.mkdir()
    project = ProjectEntry(
        name="empty-project",
        path=project_dir,
        has_git=False,
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check="",
    )

    # Stub cli._git to return CompletedProcess with STR stderr (production shape).
    # Note: must patch on the source module (cli_mod) because
    # ``_apply_hygiene_rule`` does ``from flow_engineering.cli import _git``
    # which resolves via the cli module's namespace at call time.
    class _StubGit:
        def __call__(
            self, *args: str, **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr="fatal: not a git repository",
            )

    monkeypatch.setattr(cli_mod, "_git", _StubGit())

    # Spy on save_registry_atomic — must NOT be called when git init fails.
    # Patched on the workspace_hygiene module because that is where the
    # orchestrator references it (the registry helpers are imported into
    # workspace_hygiene's namespace at module load).
    written_payloads: list[str] = []
    monkeypatch.setattr(
        "flow_engineering.workspace_hygiene.save_registry_atomic",
        lambda registry, *, path=None: written_payloads.append("called"),
    )

    result = wh._apply_hygiene_rule(
        project,
        "R2",
        dry_run=False,
        yes=True,
        backup=False,
        backup_root=tmp_path / "backups",
    )

    # Assertions per locked test contract.
    assert result.success is False
    assert "fatal: not a git repository" in (result.error or "")
    assert "rc=1" in (result.error or "")
    assert written_payloads == []  # registry was NOT updated
    assert not (project_dir / ".git").exists()  # filesystem was NOT mutated


# =============================================================================
# T-8 — _archive_project + _restore_archived_project
# =============================================================================


def test_archive_project_moves_entry_with_default_reason() -> None:
    """T-8: ``_archive_project`` moves projects→archived with reason="manual archive"."""
    entry = ProjectEntry(
        name="mockup",
        path=Path("/tmp/mockup"),
        has_git=False,
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check="2026-06-30T12:00:00Z",
    )
    registry = make_fake_registry(projects=[entry])

    new_registry = wh._archive_project(registry, "mockup", reason=None)

    # Original is unchanged (caller must save explicitly).
    assert len(registry.projects) == 1
    # New registry: entry moved to archived[] with the default reason.
    assert new_registry.projects == []
    assert len(new_registry.archived) == 1
    arc = new_registry.archived[0]
    assert arc.name == "mockup"
    assert arc.reason == "manual archive"
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", arc.archived_at)


def test_archive_project_uses_explicit_reason() -> None:
    """T-8: explicit ``--reason`` value lands verbatim in the archived entry."""
    entry = ProjectEntry(
        name="mockup",
        path=Path("/tmp/mockup"),
        has_git=False,
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check="2026-06-30T12:00:00Z",
    )
    registry = make_fake_registry(projects=[entry])

    new_registry = wh._archive_project(registry, "mockup", reason="deprecated")

    assert new_registry.archived[0].reason == "deprecated"


def test_restore_archived_project_reverses_archive() -> None:
    """T-8: ``_restore_archived_project`` mirrors archive (archived→projects)."""
    arc = ArchivedEntry(
        name="mockup",
        path=Path("/tmp/mockup"),
        archived_at="2026-06-30T12:00:00Z",
        reason="deprecated",
    )
    registry = make_fake_registry(archived=[arc])

    new_registry = wh._restore_archived_project(registry, "mockup")

    assert new_registry.archived == []
    assert len(new_registry.projects) == 1
    assert new_registry.projects[0].name == "mockup"
    assert new_registry.projects[0].path == Path("/tmp/mockup")


def test_archive_project_raises_for_missing_name() -> None:
    """T-8: archiving a name not in ``projects[]`` → ``RegistryError``."""
    registry = make_fake_registry()
    with pytest.raises(RegistryError) as exc:
        wh._archive_project(registry, "ghost", reason=None)
    assert "ghost" in exc.value.user_message or "not found" in exc.value.user_message.lower()


def test_restore_archived_project_raises_for_missing_name() -> None:
    """T-8: restoring a name not in ``archived[]`` → ``RegistryError``."""
    registry = make_fake_registry()
    with pytest.raises(RegistryError) as exc:
        wh._restore_archived_project(registry, "ghost")
    assert "ghost" in exc.value.user_message or "not archived" in exc.value.user_message.lower()


# =============================================================================
# Cross-platform path resolution (parametrized over Windows + POSIX home stubs)
# =============================================================================


@pytest.mark.parametrize(
    "fake_home",
    [
        pytest.param(Path("C:\\Users\\insyd"), id="windows_home"),
        pytest.param(Path("/home/insyd"), id="posix_home"),
        pytest.param(Path("/Users/insyd"), id="macos_home"),
    ],
)
def test_registry_path_cross_platform(
    monkeypatch: pytest.MonkeyPatch, fake_home: Path
) -> None:
    """T-1 cross-platform: ``registry_path()`` resolves under any home prefix.

    The registry namespace ``~/.flow-engineering/`` is platform-agnostic.
    Whether ``Path.home()`` returns Windows, Linux, or macOS format, the
    helper must compose the canonical registry path.
    """
    stub_home(monkeypatch, fake_home)
    assert registry_path() == fake_home / ".flow-engineering" / "registry.json"
