"""Orchestrator for the ``flow workspace {fix,archive,archived,restore}`` verbs (Phase 4).

REQ-HYGIENE-FIX-SURFACE / REQ-HYGIENE-ARCHIVE-SURFACE / REQ-HYGIENE-RESTORE-SURFACE:
the central entrypoint ``_apply_hygiene_rule`` wires together the
**pollution-protocol triple** (REQ-HYGIENE-POLLUTION-PROTOCOL):

::

    _snapshot_project()  ->  apply rule  ->  _verify_post_mutation()
           |                  |                     |
           v                  v                     v
       backup dir         git init            check .git/,
                                                if FAIL:
                                                  _restore_from_snapshot()
                                                  -> exit 2

Every mutation is gated by ``--yes`` (``MutationGateError``) and
``--backup`` on non-empty projects (``EmptyProjectError``). Dry-run
default (REQ-HYGIENE-DRY-RUN-DEFAULT) returns a planned-action
``HygieneResult`` without touching the filesystem or the registry.

R1 rule remediation is **OUT OF SCOPE** for Phase 4 MVP — this module
MUST NOT implement any code path that mutates the worktree, index, or
untracked-file state. Future change ``workspace-hygiene-r1`` may revisit.

Public surface (all helpers are leading-underscore because the CLI layer
in PR2 is the only intended caller):

- ``HygieneResult`` — frozen dataclass returned by ``_apply_hygiene_rule``.
- ``MutationGateError`` — raised on missing ``--yes`` (PermissionError).
- ``EmptyProjectError`` — raised on non-empty + missing ``--backup``
  (ValueError).
- ``HIDDEN_SYSTEM_FILES`` — frozenset of OS junk excluded from empty check.
- ``_is_empty_project`` — first-level hidden-file-aware emptiness check.
- ``_snapshot_project`` — copies pre-mutation files + writes ``manifest.json``.
- ``_verify_post_mutation`` — confirms ``.git/{HEAD,config}`` exist.
- ``_restore_from_snapshot`` — wipes target, copies snapshot back.
- ``_apply_hygiene_rule`` — orchestrator; the only public-ish entrypoint.
- ``_archive_project`` — moves projects→archived immutably.
- ``_restore_archived_project`` — moves archived→projects immutably.
- ``_now_iso_utc`` — UTC ISO 8601 with ``Z`` suffix.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from flow_engineering.registry import (
    ArchivedEntry,
    ProjectEntry,
    Registry,
    RegistryError,
    load_registry,
    save_registry_atomic,
)

# ``_git`` is imported lazily inside ``_apply_hygiene_rule`` to avoid a
# module-level circular import: ``flow_engineering.cli`` does NOT import
# this module at load time, but the new Click commands (PR2) will. Lazy
# import keeps the import graph one-way.

# =============================================================================
# Public types + exceptions
# =============================================================================


@dataclass(frozen=True)
class HygieneResult:
    """Outcome of ``_apply_hygiene_rule``.

    Frozen so callers cannot mutate the audit trail after the orchestrator
    returns. The CLI layer (PR2) reads these fields to print a one-line
    summary per action.
    """

    rule_id: str
    project: str
    action_taken: str
    dry_run: bool
    backup_path: Path | None
    success: bool
    error: str | None


class MutationGateError(PermissionError):
    """Raised when a mutation gate is violated (e.g., missing ``--yes``).

    The CLI layer prints ``user_message`` to stderr (exit 2) so the user
    sees a clear remediation hint.
    """

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class EmptyProjectError(ValueError):
    """Raised when ``git init`` would run on a non-empty project without ``--backup``.

    Carries the actual list of non-empty files so the CLI can print
    "Project contains: README.md, .gitignore" if desired.
    """

    def __init__(
        self,
        user_message: str,
        project: Path,
        non_empty_files: list[str],
    ) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.project = project
        self.non_empty_files = non_empty_files


# =============================================================================
# Constants
# =============================================================================


HIDDEN_SYSTEM_FILES: frozenset[str] = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})
"""OS-created junk excluded from the empty-project check.

These three files are created by macOS Finder (``.DS_Store``), Windows
Explorer thumbnail cache (``Thumbs.db``), and Windows folder customization
(``desktop.ini``). They are NOT user content. Other hidden files
(``.gitignore``, ``.env``, ``.vscode/``) ARE user content and count
toward non-empty per REQ-HYGIENE-BACKUP-GATE-NONEMPTY.
"""


# =============================================================================
# Helpers
# =============================================================================


def _now_iso_utc() -> str:
    """Return UTC now as ISO 8601 with a ``Z`` suffix (audit-safe).

    Format is fixed-width ASCII (``YYYY-MM-DDTHH:MM:SSZ``). Used for the
    ``archived_at`` and ``last_status_check`` registry fields, and the
    ``manifest.json`` ``created_at`` field.

    For filesystem-safe directory names (which cannot contain ``:`` on
    Windows), use :func:`_now_compact_utc` instead.
    """
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_compact_utc() -> str:
    """Return UTC now as a Windows-safe compact timestamp.

    Format: ``YYYYMMDDTHHMMSSZ`` (no dashes, no colons). Used for the
    snapshot directory name so the value can be a valid path component
    on every supported platform (Windows rejects ``:`` in filenames).
    The manifest ``created_at`` field uses this same compact form so the
    directory name and the field are byte-equal (per tasks.md §T-5).
    """
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _is_empty_project(project_path: Path) -> bool:
    """Return True iff ``project_path`` has no user-visible content.

    The check is **first-level only** (no recursion): a subdirectory is
    itself user work. ``HIDDEN_SYSTEM_FILES`` are excluded; all other
    entries (including ``.gitignore``, ``.env``, ``.vscode/``) count as
    non-empty per the spec.

    Use :func:`pathlib.Path.iterdir` (NOT ``glob(\"*\")`` — that excludes
    dotfiles by default and would mis-classify a project with
    ``.gitignore`` as empty).
    """
    return all(entry.name in HIDDEN_SYSTEM_FILES for entry in project_path.iterdir())


def _list_non_empty_files(project_path: Path) -> list[str]:
    """Return the first-level entry names that make the project non-empty.

    Sorted for deterministic error messages (so the same project always
    produces the same ``non_empty_files`` list). Excludes the OS junk
    trio per REQ-HYGIENE-BACKUP-GATE-NONEMPTY.
    """
    return sorted(
        entry.name
        for entry in project_path.iterdir()
        if entry.name not in HIDDEN_SYSTEM_FILES
    )


def _compute_snapshot_stats(src: Path) -> tuple[int, int]:
    """Walk ``src`` (excluding ``.git/``) and return ``(files_count, bytes_total)``.

    Used to populate the snapshot ``manifest.json`` fields so a future
    operator can see how big the project was at backup time.
    """
    files_count = 0
    bytes_total = 0
    for path in src.rglob("*"):
        if path.is_file() and ".git" not in path.relative_to(src).parts:
            files_count += 1
            bytes_total += path.stat().st_size
    return files_count, bytes_total


def _git_metadata_intact(project_path: Path) -> bool:
    """Return True iff the project has a well-formed ``.git/`` directory.

    Used by ``_verify_post_mutation`` to confirm ``git init`` produced
    the expected scaffolding (``.git/``, ``.git/HEAD``, ``.git/config``).
    """
    git = project_path / ".git"
    if not git.is_dir():
        return False
    if not (git / "HEAD").is_file():
        return False
    return (git / "config").is_file()


def _format_git_stderr(stderr: object) -> str:
    """Normalize subprocess stderr (bytes | str | None) to a str.

    ``cli._git`` is invoked with ``text=True`` so the production path
    returns ``str``; tests use a mock that returns ``bytes`` to exercise
    the decode branch. Both must produce a user-readable error message.
    Empty or None falls back to ``"unknown error"`` so the operator
    always sees a non-empty diagnostic.
    """
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace") or "unknown error"
    if isinstance(stderr, str):
        return stderr or "unknown error"
    return "unknown error"


# =============================================================================
# Snapshot / verify / restore (pollution-protocol triple)
# =============================================================================


def _snapshot_project(
    project_path: Path, backup_root: Path, *, rule_id: str = "R2"
) -> Path:
    """Copy the project's pre-mutation files to a timestamped backup dir.

    Layout (REQ-HYGIENE-BACKUP-LAYOUT):

    ::

        <backup_root>/<project_name>/<UTC-ISO-ts>/
            manifest.json
            files/
                <recursive copy of pre-mutation files; .git/ excluded>

    The UTC-ISO timestamp is captured ONCE at the top of the function so
    the manifest ``created_at`` equals the directory name. Two
    ``_snapshot_project`` calls in the same UTC second will collide on
    ``FileExistsError`` — that is acceptable per design §Migration /
    Rollout (the user re-runs).

    Returns the snapshot directory path.
    """
    timestamp = _now_compact_utc()
    snapshot_dir = backup_root / project_path.name / timestamp
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    files_count, bytes_total = _compute_snapshot_stats(project_path)
    manifest = {
        "project_name": project_path.name,
        "project_path": str(project_path),
        "rule_id": rule_id,
        "git_status_pre": (project_path / ".git").exists(),
        "files_count": files_count,
        "bytes_total": bytes_total,
        "created_at": timestamp,
    }
    (snapshot_dir / "manifest.json").write_text(
        json_dumps(manifest), encoding="utf-8"
    )
    shutil.copytree(
        project_path,
        snapshot_dir / "files",
        ignore=shutil.ignore_patterns(".git"),
        dirs_exist_ok=False,
    )
    return snapshot_dir


def _verify_post_mutation(
    project_path: Path, pre_snapshot: Path | None
) -> bool:
    """Return True iff post-mutation ``.git/`` looks valid.

    Currently checks file existence only (fast, no subprocess). A future
    change could add ``git status --porcelain`` for a stricter check; the
    pollution-protocol triple's restore path is the safety net for the
    rare case where existence-check passes but the repo is corrupt.

    ``pre_snapshot`` is accepted as ``Path | None`` for the post-fix-up
    orchestrator signature: verify now runs unconditionally (even when
    no snapshot was taken), and the parameter is retained for future
    stricter checks that may compare pre/post file counts. The current
    body ignores the value.
    """
    return _git_metadata_intact(project_path)


def _restore_from_snapshot(snapshot: Path, target: Path) -> None:
    """Wipe ``target`` and copy ``snapshot/files/`` back.

    Used by the pollution-protocol triple when ``_verify_post_mutation``
    fails. ``.git/`` is removed first (it was created by the failed
    mutation) and the entire target directory is recreated from the
    snapshot's ``files/`` subdir. ``target`` itself is preserved as a
    directory so any inotify-style watches on the parent are not
    disturbed.
    """
    shutil.rmtree(target / ".git", ignore_errors=True)
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(snapshot / "files", target, dirs_exist_ok=True)


# =============================================================================
# Orchestrator (the central entrypoint)
# =============================================================================


def _apply_hygiene_rule(
    project: ProjectEntry,
    rule_id: str,
    *,
    dry_run: bool,
    yes: bool,
    backup: bool,
    backup_root: Path,
) -> HygieneResult:
    """Apply the hygiene rule to ``project`` with safety gates.

    Sequence (REQ-HYGIENE-FIX-SURFACE + REQ-HYGIENE-POLLUTION-PROTOCOL):

    1. **Gate** — if not ``yes`` and not ``dry_run`` → ``MutationGateError``.
    2. **Backup gate** — if not ``dry_run`` and project is non-empty and
       not ``backup`` → ``EmptyProjectError``.
    3. **Snapshot** — if ``backup`` and the project needs it, take a
       snapshot of pre-mutation state.
    4. **Dry-run** — if ``dry_run`` is True, return a planned-action result
       without touching the filesystem or registry.
    5. **Mutate** — call ``_git(\"init\", str(project.path))`` via the
       ``cli._git`` seam (lazy import to avoid circular dependency).
    6. **Verify + restore-on-fail** — if ``_verify_post_mutation`` returns
       False, call ``_restore_from_snapshot`` and return a fail result.
    7. **Registry update** — load the registry, append the project to
       ``projects[]`` with ``last_status_check=_now_iso_utc()``,
       ``save_registry_atomic`` the result.
    8. **Return** — success ``HygieneResult``.
    """
    # Lazy import: ``_git`` lives in ``flow_engineering.cli`` and importing
    # it at module load would create a cycle (PR2's Click commands will
    # import this module).
    from flow_engineering.cli import _git

    # Step 1 — mutation gate.
    if not yes and not dry_run:
        raise MutationGateError(
            "--yes required for `flow workspace fix` mutations"
        )

    # Step 2 — backup gate (only applies to the non-dry-run path; dry-run
    # can safely report the plan regardless of emptiness).
    if not dry_run and not _is_empty_project(project.path) and not backup:
        raise EmptyProjectError(
            user_message=(
                f"Project `{project.name}` is not empty. "
                f"Re-run with `--backup` to snapshot before `git init`."
            ),
            project=project.path,
            non_empty_files=_list_non_empty_files(project.path),
        )

    # Step 3 — snapshot (only if we'll actually need it).
    snapshot: Path | None = None
    needs_snapshot = backup and not _is_empty_project(project.path)
    if needs_snapshot:
        snapshot = _snapshot_project(project.path, backup_root, rule_id=rule_id)

    # Step 4 — dry-run short-circuit.
    if dry_run:
        return HygieneResult(
            rule_id=rule_id,
            project=project.name,
            action_taken="would-run-git-init",
            dry_run=True,
            backup_path=snapshot,
            success=True,
            error=None,
        )

    # Step 5 — mutate. Capture the ``CompletedProcess`` so we can inspect
    # ``returncode`` (user-found defect: the previous code discarded the
    # return value and silently proceeded to verify + registry update even
    # when ``git init`` failed).
    cp = _git("init", str(project.path))

    # Step 5b — early exit on git init failure (BEFORE verify, BEFORE
    # registry update). Failing fast here keeps the registry from claiming
    # ``has_git=True`` for a project whose ``git init`` actually failed.
    if cp.returncode != 0:
        return HygieneResult(
            rule_id=rule_id,
            project=project.name,
            action_taken="git init",
            dry_run=False,
            backup_path=snapshot,
            success=False,
            error=f"git init failed (rc={cp.returncode}): {_format_git_stderr(cp.stderr)}",
        )

    # Step 6 — verify (ALWAYS, regardless of snapshot existence).
    # User-found defect: the previous code only ran ``_verify_post_mutation``
    # when ``snapshot is not None``, so empty projects (no snapshot) skipped
    # verify entirely. A corrupted ``.git/`` after a successful-rc ``git
    # init`` (rare but documented git behavior on Windows with antivirus
    # interference, FS corruption, etc.) used to get registered as
    # ``has_git=True`` with no verification. The verify check now runs
    # unconditionally; if it fails, we restore from snapshot when present
    # and otherwise return a failure result with the registry untouched.
    if not _verify_post_mutation(project.path, snapshot):
        if snapshot is not None:
            _restore_from_snapshot(snapshot, project.path)
        return HygieneResult(
            rule_id=rule_id,
            project=project.name,
            action_taken="git init",
            dry_run=False,
            backup_path=snapshot,
            success=False,
            error="verify failed",
        )

    # Step 7 — registry update.
    registry = load_registry()
    new_entry = ProjectEntry(
        name=project.name,
        path=project.path,
        has_git=True,  # git init just ran
        has_openspec=project.has_openspec,
        has_tests=project.has_tests,
        has_graphify=project.has_graphify,
        last_status_check=_now_iso_utc(),
    )
    new_projects = [
        p for p in registry.projects if p.name != new_entry.name
    ]
    new_projects.append(new_entry)
    new_registry = registry.model_copy(update={"projects": new_projects})
    save_registry_atomic(new_registry)

    # Step 8 — return.
    return HygieneResult(
        rule_id=rule_id,
        project=project.name,
        action_taken="git init",
        dry_run=False,
        backup_path=snapshot,
        success=True,
        error=None,
    )


# =============================================================================
# Archive / restore (registry-only operations)
# =============================================================================


def _archive_project(
    registry: Registry, project_name: str, reason: str | None
) -> Registry:
    """Return a NEW ``Registry`` with ``project_name`` moved to ``archived[]``.

    The input ``registry`` is NOT mutated (pydantic v2 ``model_copy`` is
    deep). The caller (CLI layer in PR2) is responsible for
    ``save_registry_atomic`` after the move.

    ``reason=None`` defaults to the literal string ``"manual archive"``
    per locked constraint #10. An empty string is treated as a real
    reason (not as ``None``) — the ``or`` default only fires on actual
    ``None``.
    """
    found: ProjectEntry | None = None
    for entry in registry.projects:
        if entry.name == project_name:
            found = entry
            break
    if found is None:
        raise RegistryError(
            user_message=(
                f"Project `{project_name}` not found in registry. "
                f"Run `flow projects ls` to see registered projects."
            )
        )
    archived_entry = ArchivedEntry(
        name=found.name,
        path=found.path,
        archived_at=_now_iso_utc(),
        reason=reason or "manual archive",
    )
    new_projects = [p for p in registry.projects if p.name != project_name]
    new_archived = [*registry.archived, archived_entry]
    return registry.model_copy(update={"projects": new_projects, "archived": new_archived})


def _restore_archived_project(registry: Registry, project_name: str) -> Registry:
    """Return a NEW ``Registry`` with ``project_name`` moved back to ``projects[]``.

    Symmetric to :func:`_archive_project`. The restored ``ProjectEntry``
    gets a fresh ``last_status_check`` so the next ``fix`` cycle sees it
    as "seen alive just now".
    """
    found: ArchivedEntry | None = None
    for entry in registry.archived:
        if entry.name == project_name:
            found = entry
            break
    if found is None:
        raise RegistryError(
            user_message=(
                f"Project `{project_name}` is not archived. "
                f"Nothing to restore."
            )
        )
    restored_entry = ProjectEntry(
        name=found.name,
        path=found.path,
        has_git=False,  # unknown after restore; mark for re-check
        has_openspec=False,
        has_tests=False,
        has_graphify=False,
        last_status_check=_now_iso_utc(),
    )
    new_projects = [
        p for p in registry.projects if p.name != restored_entry.name
    ]
    new_projects.append(restored_entry)
    new_archived = [a for a in registry.archived if a.name != project_name]
    return registry.model_copy(update={"projects": new_projects, "archived": new_archived})


# =============================================================================
# Internal helper: JSON serializer
# =============================================================================


def json_dumps(payload: object) -> str:
    """Indented UTF-8 JSON serialization (used for ``manifest.json``).

    Kept module-local to avoid pulling in a shared serializer that
    future modules might fork.
    """
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2)


__all__ = [
    "HIDDEN_SYSTEM_FILES",
    "EmptyProjectError",
    "HygieneResult",
    "MutationGateError",
    "_apply_hygiene_rule",
    "_archive_project",
    "_compute_snapshot_stats",
    "_format_git_stderr",
    "_git_metadata_intact",
    "_is_empty_project",
    "_list_non_empty_files",
    "_now_compact_utc",
    "_now_iso_utc",
    "_restore_archived_project",
    "_restore_from_snapshot",
    "_snapshot_project",
    "_verify_post_mutation",
    "json_dumps",
]
