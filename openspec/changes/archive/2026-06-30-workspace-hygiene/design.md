# Design: workspace-hygiene — Phase 4 of workspace-intelligence

## Technical Approach

Phase 4 ships a **write-side MVP** that fixes the R2 (no-git) hygiene issue surfaced by Phase 3 and adds a registry-driven archive/restore pair for projects the user no longer maintains. The mutation layer is implemented in a **new** orchestrator module (`workspace_hygiene.py`) sitting beside the existing `workspace_group` Click commands at `cli.py:2982`; the persistent store is a **new** pydantic v2 module (`registry.py`) that uses the `tempfile + os.replace` atomic-write pattern from `project_aliases.py:176`.

The 4-verb CLI surface (`fix`, `archive`, `archived`, `restore`) is **additive only**. Phase 1 (`_detect_project_markers` at `cli.py:3137`), Phase 2 (`where.py`), and Phase 3 (`_summarize_workspace_status` at `cli.py:2869`) code paths are READ-ONLY consumers and are never modified. The Phase 1 byte-identical guard test `test_flow_projects_ls_json_byte_identical_envelope` at `tests/unit/test_cli_projects.py:435` MUST remain green throughout. R1 dirty-git remediation is **OUT OF SCOPE for Phase 4 MVP** — the canonical wording per REQ-HYGIENE-R1-EXPLICITLY-OUT is preserved verbatim.

**Strict TDD mode is ON**. Apply will execute RED → GREEN → REFACTOR per task. Forecast: ~340 production LOC + 18 unit tests + 16 BDD scenarios. AC9 guard stays green.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|---|---|---|---|
| CLI surface location | Sibling verbs on existing `workspace_group` (`cli.py:2982`) | New top-level `flow hygiene` group | Keeps related reads/writes under one mental roof. Matches Phase 3 precedent (`status`). |
| Persistent store | **NEW** `src/flow_engineering/registry.py` (pydantic v2) | Reuse `project_aliases.py` (TypedDict + aliases config) | Different schema (live `projects[]` + `archived[]` vs alias map); pydantic gives schema validation on disk-read. |
| Atomic write | `tempfile.NamedTemporaryFile` + `os.replace` (mirrors `project_aliases.py:176`) | `os.rename`, write-in-place | `os.replace` is atomic on POSIX + Windows when both paths are on the same FS; tempfile in same parent dir guarantees that. Same precedent as `save_aliases`. |
| Path resolution | `Path.home() / ".flow-engineering"` for both registry + backups | `Path.home() / ".config" / "flow-engineering"` | Hidden dotfile namespace parallels `~/.engram/`. Single root, easy to discover. |
| Mutation gate | `--yes` required + dry-run default + `--backup` enforced for non-empty | Always-mutate with `--force`, no backup | Phase 4 is safe-first; users explicitly opted into write-side Phase 4 with a "safe-first mandate" (proposal §Approach A). |
| Hidden-file exclusion | `{".DS_Store", "Thumbs.db", "desktop.ini"}` only | All hidden files | These 3 are OS-created junk, not user content. `.gitignore`, `.env`, `.vscode/` ARE user content. Documented in `_is_empty_project` rationale. |
| Pydantic model freeze | `frozen=False` on `Registry` | `frozen=True` | We mutate the model in memory then write via atomic replace at the file level. Frozen models add ceremony without value when the file-level atomicity is the actual contract. |
| Cross-platform path tests | `monkeypatch.setattr(Path, "home", ...)` parametrize | Skip on Windows CI, run on POSIX CI only | Parametrize over Windows stub (`C:\Users\test`) + POSIX stub (`/home/test`); same test runs on either host. |
| Commit shape | Single commit, prod + tests interleaved (matches user pattern per session #453) | 2-commit split (prod / tests) | User's established pattern is single commit per PR. Strict TDD evidence lives in the diff (RED test → GREEN impl → REFACTOR). |

## Data Flow

```text
                ┌────────────────────────────────────────────┐
                │  cli.py (existing workspace_group @ 2982)  │
                │  ┌──────┐ ┌────────┐ ┌──────────┐ ┌──────┐ │
                │  │ fix  │ │archive │ │ archived │ │restore│ │
                │  └──┬───┘ └───┬────┘ └─────┬────┘ └───┬──┘ │
                └─────┼─────────┼────────────┼──────────┼────┘
                      │         │            │          │
                      ▼         ▼            ▼          ▼
                ┌─────────────────────────────────────────────┐
                │  workspace_hygiene.py (NEW orchestrator)   │
                │  _apply_hygiene_rule  ← central entrypoint │
                │  _snapshot_project    ──┐                  │
                │  _verify_post_mutation ──┤ pollution triple│
                │  _restore_from_snapshot ──┘                │
                │  _archive_project / _restore_archived_proj │
                └─────────────────────────────────────────────┘
                      │                  │
                      ▼                  ▼
            ┌─────────────────┐  ┌────────────────────────────┐
            │  subprocess     │  │  registry.py (NEW)         │
            │  `_git` seam    │  │  Registry/ProjectEntry/    │
            │  (cli.py:3045)  │  │  ArchivedEntry (pydantic)  │
            │  for git init   │  │  load/save_atomic          │
            └─────────────────┘  └────────────────────────────┘
                                            │
                                            ▼
                                ~/.flow-engineering/
                                ├── registry.json
                                └── backups/<project>/<UTC-ISO>/
                                    ├── manifest.json
                                    └── [pre-mutation snapshot]
```

Pollution-protocol triple (every mutation in `_apply_hygiene_rule`):
```text
_snapshot_project()  →  apply rule  →  _verify_post_mutation()
       │                   │                    │
       ▼                   ▼                    ▼
   backup dir           git init            check .git/,
                                            if FAIL:
                                              _restore_from_snapshot()
                                              → exit 2
```

## File Changes

| File | Action | Description |
|---|---|---|
| `src/flow_engineering/registry.py` | **NEW** | Pydantic v2 models (`Registry`, `ProjectEntry`, `ArchivedEntry`); `DEFAULT_REGISTRY_PATH`, `load_registry()`, `save_registry_atomic()`, `RegistryError`. |
| `src/flow_engineering/workspace_hygiene.py` | **NEW** | Orchestrator: `HygieneResult`, `_apply_hygiene_rule`, `_snapshot_project`, `_verify_post_mutation`, `_restore_from_snapshot`, `_archive_project`, `_restore_archived_project`, `_is_empty_project`, exception hierarchy. |
| `src/flow_engineering/cli.py` | Modify | Add 4 new Click commands (`workspace_fix_cmd`, `workspace_archive_cmd`, `workspace_archived_cmd`, `workspace_restore_cmd`) below the existing `workspace_status` registration (~line 3024). Add imports for the new module. **NO** changes to `_detect_project_markers`, `_git`, `_summarize_workspace_status`, `_resolve_projects_root`, `projects_ls`, or any Phase 1/2/3 code. |
| `tests/unit/_workspace_hygiene_fixtures.py` | **NEW** | `make_fake_project`, `make_fake_registry`, `stub_home` context manager, `_default_branch_fake_git` factory. Isolated from existing `_workspace_fixtures.py` so Phase 4 fixtures don't perturb Phase 1/2/3 test pollution. |
| `tests/unit/test_workspace_hygiene.py` | **NEW** | 18 unit tests covering registry round-trip, atomic write crash recovery, hidden-file exclusion, snapshot/verify/restore, all 4 verbs at the helper level, cross-platform path resolution. |
| `tests/unit/test_cli_workspace_hygiene.py` | **NEW** | 8 CLI tests covering dry-run default, `--yes`/`--backup` gates, all 4 verb happy paths, AC9 byte-identical for non-targets. |
| `tests/bdd/workspace_hygiene.feature` | **NEW** | 16 BDD scenarios (13 required + 3 edge) bound to spec REQs; per spec §5. |
| `tests/bdd/test_workspace_hygiene_steps.py` | **NEW** | pytest-bdd step glue mirroring `tests/bdd/req_*.feature` patterns. |
| `openspec/specs/workspace/spec.md` | **NOT TOUCHED** | Out of scope (see Tech Debt §10). |

## Interfaces / Contracts

### `src/flow_engineering/registry.py` (NEW)

Pydantic v2 models. Atomic-write helper reuses the `tempfile + os.replace` precedent from `project_aliases.py:164-193` (the actual `save_aliases` function). Registry is **fresh on first write**; no v0→v1 migration needed.

```python
# All models are pydantic v2 BaseModel. Registry uses extra="forbid" + frozen=False.
from typing import Literal
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field


class ProjectEntry(BaseModel):
    """Registry entry for a live project (mirrors Phase 1 v1 envelope fields)."""

    model_config = ConfigDict(extra="forbid", frozen=False)

    name: str
    path: Path                                       # absolute, normalized
    has_git: bool
    has_openspec: bool
    has_tests: bool
    has_graphify: bool
    last_status_check: str                           # UTC ISO 8601 with Z suffix


class ArchivedEntry(BaseModel):
    """Registry entry for an archived project."""

    model_config = ConfigDict(extra="forbid", frozen=False)

    name: str
    path: Path
    archived_at: str                                 # UTC ISO 8601 with Z suffix
    reason: str                                      # defaults to "manual archive"


class Registry(BaseModel):
    """Top-level v1 registry."""

    model_config = ConfigDict(extra="forbid", frozen=False)

    version: Literal[1] = 1
    projects: list[ProjectEntry] = Field(default_factory=list)
    archived: list[ArchivedEntry] = Field(default_factory=list)


class RegistryError(RuntimeError):
    """I/O / parse / schema failures from registry operations."""

    user_message: str


DEFAULT_REGISTRY_PATH: Path = Path.home() / ".flow-engineering" / "registry.json"
"""Canonical registry path. NOT cached — Path.home() may differ across contexts."""


def load_registry(*, path: Path | None = None) -> Registry:
    """Load and validate registry.json.

    Missing file → Registry(version=1, projects=[], archived=[]).
    Malformed JSON / schema mismatch → RegistryError.
    """


def save_registry_atomic(registry: Registry, *, path: Path | None = None) -> None:
    """Atomic write via tempfile.NamedTemporaryFile + os.replace.

    Mirrors project_aliases.save_aliases (project_aliases.py:164-193). On
    OSError raises RegistryError. The temp file is cleaned up on failure.
    """
```

**Cross-platform resolution** (Windows + POSIX):

| Platform | `Path.home()` | `DEFAULT_REGISTRY_PATH` |
|---|---|---|
| Windows | `C:\Users\insyd` | `C:\Users\insyd\.flow-engineering\registry.json` |
| POSIX | `/home/user` | `/home/user/.flow-engineering/registry.json` |

Tests stub `Path.home()` via `monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))` (same pattern as `test_cli_apply_verify_archive.py:80-82`).

### `src/flow_engineering/workspace_hygiene.py` (NEW)

Orchestrator module. Holds the pollution-protocol triple and the exception hierarchy. **All mutation happens here** — Click commands are thin wrappers.

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class HygieneResult:
    rule_id: str
    project: str
    action_taken: str
    dry_run: bool
    backup_path: Path | None
    success: bool
    error: str | None


class MutationGateError(PermissionError):
    """Raised when --yes or --backup gate is violated. Carries user_message."""

    user_message: str


class EmptyProjectError(ValueError):
    """Raised when `git init` would run on a non-empty project without --backup."""

    user_message: str
    project: Path
    non_empty_files: list[str]


HIDDEN_SYSTEM_FILES: frozenset[str] = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})
"""OS-created junk excluded from the empty-project check.

Rationale: these three files are created by Finder (macOS), Windows Explorer,
and Windows folder customization respectively. They are NOT user content.
Other hidden files (e.g., ``.gitignore``, ``.env``, ``.vscode/``) ARE user
content and count as non-empty per REQ-HYGIENE-BACKUP-GATE-NONEMPTY.
"""


def _is_empty_project(project_path: Path) -> bool:
    """Return True iff project_path has no user-visible content.

    A project is "empty" when ``.git/`` is absent AND no entries remain after
    filtering out HIDDEN_SYSTEM_FILES. Hidden user content (.gitignore,
    .env, .vscode/) IS user content; only the OS junk trio is excluded.
    """


def _snapshot_project(project_path: Path, backup_root: Path) -> Path:
    """Copy project files to backup_root/<project>/<UTC-ISO-ts>/.

    Writes manifest.json with project_name, project_path, rule_id, snapshot_at,
    pre_git_status, file_count, total_bytes. Uses shutil.copytree with
    dirs_exist_ok=False since the snapshot dir is fresh.
    Returns the snapshot directory path.
    """


def _verify_post_mutation(project_path: Path, pre_snapshot: Path) -> bool:
    """Return True if post-mutation state is valid.

    For R2 git init: verify .git/ exists, contains HEAD and config.
    For archive: verify the registry contains the new entry (caller checks).
    """


def _restore_from_snapshot(snapshot: Path, target: Path) -> None:
    """Remove target content (preserve dir) and copy snapshot content back."""


def _apply_hygiene_rule(
    project: ProjectEntry,
    rule_id: str,
    *,
    dry_run: bool,
    yes: bool,
    backup: bool,
    backup_root: Path,
) -> HygieneResult:
    """The orchestrator. Sequence:

    1. Validate: not yes and not dry_run -> raise MutationGateError("--yes required")
       rule_id == "R2_GIT_INIT" and not empty and not backup
           -> raise EmptyProjectError(project, non_empty_files)
    2. If backup or non-empty project: _snapshot_project()
    3. If dry_run: return HygieneResult(dry_run=True, action="would-run-git-init")
    4. Apply mutation via _git("init", str(project.path)) (uses cli.py:3045 seam)
    5. _verify_post_mutation(); if False: _restore_from_snapshot(); exit 2
    6. Update registry: load, append to projects[] with last_status_check=now,
       save_registry_atomic()
    7. Return HygieneResult(success=True, ...)
    """


def _archive_project(
    registry: Registry, project_name: str, reason: str | None,
) -> Registry:
    """Return a new Registry with the project moved from projects[] to archived[].

    reason=None defaults to "manual archive" per locked constraint #10.
    Raises RegistryError if project_name not in projects[].
    """


def _restore_archived_project(registry: Registry, project_name: str) -> Registry:
    """Return a new Registry with the entry moved from archived[] back to projects[].

    Raises RegistryError if project_name not in archived[].
    """


def _now_iso_utc() -> str:
    """UTC ISO 8601 with Z suffix (matches project_aliases._now_iso style)."""
```

### `src/flow_engineering/cli.py` additions

All 4 commands attached to existing `workspace_group` at `cli.py:2982`. Registration order matches user mental model: `fix` → `archive` → `archived` → `restore`. New imports added near the existing top-level imports (`from flow_engineering import workspace_hygiene`).

```python
@workspace_group.command(name="fix")
@click.argument("project")
@click.option("--dry-run/--no-dry-run", default=True,
              help="Report planned actions without mutating. Default: dry-run.")
@click.option("--yes", is_flag=True, default=False,
              help="Required for any mutation.")
@click.option("--backup/--no-backup", default=False,
              help="Snapshot project before mutation. Required for git init on non-empty projects.")
def workspace_fix_cmd(project: str, dry_run: bool, yes: bool, backup: bool) -> None:
    """Apply R2 (git init) hygiene rule to a single project."""
    ...

@workspace_group.command(name="archive")
@click.argument("project")
@click.option("--reason", default=None, help="Reason for archiving (optional).")
@click.option("--yes", is_flag=True, default=False, help="Required to archive.")
def workspace_archive_cmd(project: str, reason: str | None, yes: bool) -> None:
    """Mark a project archived; excluded from flow projects ls."""
    ...

@workspace_group.command(name="archived")
def workspace_archived_cmd() -> None:
    """List archived projects (text only)."""
    ...

@workspace_group.command(name="restore")
@click.argument("project")
@click.option("--yes", is_flag=True, default=False, help="Required to restore.")
def workspace_restore_cmd(project: str, yes: bool) -> None:
    """Reverse a prior archive; re-add to flow projects ls."""
    ...
```

**Pre-flight guard** (shared by all 4 commands via a `_workspace_hygiene_preflight` helper):
- Refuse to operate on the resolved `~/.flow-engineering/` registry dir.
- Refuse to operate on the `flow-engineering` repo path (resolved, not string-equal).
- Refuse if the project name is not present in the resolved workspace root's subdirectories.

**Output format** (text only per locked constraint #11, no `--json`):
- `fix`: one line per action. Dry-run prefix `[DRY-RUN]`. Error on stderr.
- `archive`: `archived: <name> (reason: <reason>)` (per spec REQ-HYGIENE-ARCHIVE-SURFACE scenario "without --reason").
- `archived`: text table `NAME  ARCHIVED_AT  REASON` (3 columns, fixed-width) or `(no archived projects)` when empty.
- `restore`: `restored: <name>`.

## File Layout on Disk

```text
~/.flow-engineering/                                       (hidden dir; dot-prefix)
├── registry.json                                          # v1, pydantic-validated
└── backups/
    └── <project_name>/
        └── <UTC-ISO-timestamp>/                           # e.g. 20260630T120000Z
            ├── manifest.json
            │   {
            │     "project_name": "...",
            │     "project_path": "...",
            │     "rule_id": "R2_GIT_INIT",
            │     "snapshot_at": "2026-06-30T12:00:00Z",
            │     "pre_git_status": false,
            │     "file_count": 42,
            │     "total_bytes": 102400
            │   }
            └── [snapshot of pre-mutation files; excludes .git/]
```

**Platform resolution examples**:

| Platform | `Path.home()` | Registry path | Backup root |
|---|---|---|---|
| Windows | `C:\Users\insyd` | `C:\Users\insyd\.flow-engineering\registry.json` | `C:\Users\insyd\.flow-engineering\backups\` |
| POSIX | `/home/user` | `/home/user/.flow-engineering/registry.json` | `/home/user/.flow-engineering/backups/` |

> `.flow-engineering` (hidden dot-prefix) is the **project-specific registry namespace** owned by `flow-engineering`. It is NOT to be confused with the `flow-engineering` repo dir itself. The CLI refuses to operate on either as a project target (pre-flight guard).

## Testing Strategy

| Layer | What to Test | Approach | Count |
|---|---|---|---|
| Unit (registry) | load/save round-trip; missing-file default; malformed JSON → RegistryError; atomic write crash recovery (mock os.replace to raise) | Direct helper tests in `tests/unit/test_workspace_hygiene.py` | 4 |
| Unit (orchestrator) | `_is_empty_project` hidden-file exclusion; `_snapshot_project` manifest shape; `_verify_post_mutation` success/failure; `_restore_from_snapshot` round-trip; `_archive_project` + `_restore_archived_project` registry mutation | Direct helper tests | 6 |
| Unit (CLI) | `fix` dry-run default; `fix` missing-`--yes` refusal; `fix` non-empty-missing-`--backup` refusal; `fix` happy path; `archive` happy path; `archived` text output + empty case; `restore` happy path; `restore` missing-`--yes` refusal | CliRunner + tmp_path + monkeypatch `_git` seam | 8 |
| Cross-platform path | `registry_path()`, `load_registry()`, `save_registry_atomic()` resolve correctly under Windows + POSIX stubs | `@pytest.mark.parametrize` over `Path.home()` stubs | (counted in registry 4 above) |
| BDD | 16 scenarios (13 required + 3 edge) bound to spec REQs | pytest-bdd, step glue in `tests/bdd/test_workspace_hygiene_steps.py` | 16 |
| AC9 byte-identical guard | Existing `test_flow_projects_ls_json_byte_identical_envelope` at `tests/unit/test_cli_projects.py:435` stays green | NOT modified — design verifies the new code paths do not perturb `_detect_project_markers` (read-only consumer) | 0 (existing test) |
| Pollution protocol | `_verify_post_mutation` failure triggers `_restore_from_snapshot` | Unit test that monkeypatches `_verify_post_mutation` to return False | 1 |

**Total new tests**: 18 unit + 16 BDD = 34. AC9 guard stays green as the safety net.

**Fixtures** (`tests/unit/_workspace_hygiene_fixtures.py`, NEW — separate from existing `_workspace_fixtures.py` so Phase 4 fixtures don't pollute Phase 1/2/3 imports):

- `make_fake_project(name, with_files, with_git=False) -> Path` — temp dir with optional files + optional `.git/`.
- `make_fake_registry(projects=[...], archived=[...]) -> Registry` — in-memory pydantic model.
- `stub_home(monkeypatch, path) -> None` — context manager that monkeypatches `Path.home()` to a tmp path (Windows OR POSIX style; tests parametrize).
- `_default_branch_fake_git_factory(branch="main")` — returns a `_git` spy returning `CompletedProcess` for the `_git` seam.

## Error Handling Matrix

| Command | Failure | User-visible message | Exit code |
|---|---|---|---|
| `fix` | missing `--yes` (and not dry-run) | ``--yes required for `flow workspace fix` mutations`` | 2 |
| `fix` | non-empty + missing `--backup` | ``Project `<name>` is not empty. Re-run with `--backup` to snapshot before `git init`.`` | 2 |
| `fix` | project already has `.git/` | ``Project `<name>` already has a `.git/` directory. Nothing to do.`` | 0 |
| `fix` | `git init` subprocess non-zero | ``git init failed: <stderr>`` | 1 |
| `fix` | verify fails | ``Post-mutation verify failed; restored from `<snapshot>`.`` | 1 |
| `fix` | target is registry dir / `flow-engineering` repo | ``refusing to mutate `<resolved-path>`: pre-flight guard`` | 2 |
| `archive` | missing `--yes` | ``--yes required for `flow workspace archive``` | 2 |
| `archive` | project not in registry | ``Project `<name>` not found in registry. Run `flow projects ls` to see registered projects.`` | 2 |
| `restore` | missing `--yes` | ``--yes required for `flow workspace restore``` | 2 |
| `restore` | not in archived[] | ``Project `<name>` is not archived.`` | 2 |
| any | registry I/O / parse / schema | ``Registry I/O error: <details>`` | 1 |
| `archived` | accepts `--json` (rejected) | ``--json is unsupported for `flow workspace archived` in MVP`` | 2 |

## Migration / Rollout

No data migration required. Registry is fresh on first write (`fix` or `archive` create it). Read-only consumers (`flow projects ls --json`, `flow workspace status`) work with no registry present.

**Rollback plan** (mirrors proposal §Rollback):
- **Code**: single-commit revert via `git revert <sha>` or `git reset --hard HEAD~1`.
- **Registry**: `tempfile + os.replace` atomicity leaves the prior `registry.json` intact on crash (no prior-file backup retained on success — replacement is the operation).
- **Filesystem (R2 git init)**: `_restore_from_snapshot` recovers from backup; for projects where no `--backup` was passed (truly empty), `_verify_post_mutation` + restore is moot because there were no files to lose.
- **Tests**: delete `tests/unit/test_workspace_hygiene.py`, `tests/unit/test_cli_workspace_hygiene.py`, `tests/bdd/workspace_hygiene.feature`, `tests/bdd/test_workspace_hygiene_steps.py`, `tests/unit/_workspace_hygiene_fixtures.py`. Leave `tests/unit/_workspace_fixtures.py` and `tests/unit/test_cli_projects.py` untouched.

## Out of Scope (explicit re-statement)

- **R1 dirty-git rule** — OUT OF SCOPE for Phase 4 MVP. The `flow workspace fix` command SHALL NOT implement R1 remediation. The canonical wording is "R1 dirty-git is OUT OF SCOPE for Phase 4 MVP" (REQ-HYGIENE-R1-EXPLICITLY-OUT). A future change (`workspace-hygiene-r1`) may revisit; Phase 4 makes no commitment.
- **R3 no-tests bootstrap** — template-dependent; deferred.
- **R4 missing-openspec bootstrap** — semantic; deferred.
- **`--json` / `--format` flag** on `flow workspace archived` — deferred (text-only MVP).
- **Backup retention / pruning** — indefinite retention; manual cleanup is operator responsibility.
- **TUI / interactive prompts** — Phase 5 territory.
- **Web dashboard** — Phase 5.
- **Modifications to Phase 1 / Phase 2 / Phase 3 code paths** — `_detect_project_markers`, `_git`, `_summarize_workspace_status`, `_resolve_projects_root`, `projects_ls`, `where.py`, `project_aliases.py` are READ-ONLY consumers.
- **Registry migration tooling** — no v0 → v1; fresh registry on first write.
- **Mutation of `~/.flow-engineering/` itself or `flow-engineering` repo path** — pre-flight guard refuses.

## Tech Debt / Follow-up

> Per locked constraint #20, this section is REQUIRED.

**Orphan capability spec**: `openspec/specs/workspace/spec.md` does NOT exist. Phase 3 (`flow-workspace-status`) shipped a delta-only spec at `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` but never created the root `workspace` capability spec. Phase 4 likewise is a delta-only spec at `openspec/changes/workspace-hygiene/specs/workspace-hygiene/spec.md`.

**Recommended follow-up**: a SEPARATE change named `workspace-capability-bootstrap` (or similar) whose sole purpose is to create `openspec/specs/workspace/spec.md` as a stub capability with cross-references to all 4 phases:
- Phase 1: `workspace-intelligence` (project detection, `--json` envelope)
- Phase 2: `flow-where-cross-project` (cross-project search)
- Phase 3: `flow-workspace-status` (read-only aggregation + needs-attention rules)
- Phase 4: `workspace-hygiene` (write-side MVP: R2 fix + archive/restore)

This change SHOULD also fold in any future workspace-related work (Phase 5 dashboard, registry v2, etc.) as ADDED Requirements against the same root capability.

**DO NOT** create tasks in the `workspace-hygiene` `tasks.md` to address this. It is documented here for traceability and will be picked up as a separate proposal at the user's discretion.

## Pre-existing Failures (known-out-of-scope)

The following are NOT addressed by this change:

1. **4 pre-existing test failures** (from session #453, observed at HEAD `cb82274`). Not regressed by Phase 4; not fixed.
2. **`__name__ == '__main__'` guard bug at `cli.py:2665`** — pre-existing in a different file area; unrelated to Phase 4. New commands register AFTER line 2982 (consistent with `workspace_status`).
3. **Phase 1 stub fields** (`has_graphify`, `has_engram`) — read-only consumers in Phase 4; not in scope.

## Commit Plan (per `work-unit-commits` skill)

**Recommended**: single commit (matches user's established pattern per session #453). Strict TDD evidence lives in the diff (RED test → GREEN impl → REFACTOR per task).

```text
feat(workspace): add write-side hygiene surface (fix, archive, archived, restore)

- registry.py: pydantic v2 v1 schema + atomic write (project_aliases.py:176 pattern)
- workspace_hygiene.py: orchestrator + pollution-protocol triple
- cli.py: 4 new verbs under existing workspace_group at cli.py:2982
- tests: 18 unit + 16 BDD; AC9 byte-identical guard preserved
- R1 deferred; Phase 1/2/3 code paths READ-ONLY
```

**Alternative (if user prefers explicit split at apply time)**: 2-commit split — (1) registry.py + workspace_hygiene.py + 4 CLI commands; (2) tests + BDD step glue + fixtures. Each commit would be reviewable independently but the single-commit option matches the user's PR pattern.

## Wall-time Forecast

| Phase | Estimate |
|---|---|
| `sdd-design` (this) | ~50 min |
| `sdd-tasks` | 25–30 min |
| `sdd-apply` (strict TDD, ~340 LOC, 18 unit + 16 BDD) | 90–120 min |
| `sdd-verify` | 20–30 min |
| `sdd-archive` | 10–15 min |
| **Total remaining after design** | **~2.5–3.5 hours** |

## Open Questions

None. All 4 open questions from proposal were resolved before spec phase (locked constraints #10, #11, #12, #13).