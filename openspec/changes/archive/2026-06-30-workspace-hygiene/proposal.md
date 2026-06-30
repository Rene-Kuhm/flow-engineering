# Proposal: workspace-hygiene — Phase 4 of workspace-intelligence

> Phase 4 MVP. Write-side counterpart to Phase 3 read-only `flow workspace status`.
> Addresses R2 (no-git hygiene) and explicit archive/restore for projects no longer maintained.
> R1/R3/R4 are explicitly deferred.

## Intent

The 3 unflushed projects from session #453 (`mockup`, `mockup-2-blog`, `flow-image-generator-main`) plus 5 config/dotfile directories (`.atl`, `.opencode`, `Gestor-de-Contrase-as`, `openspec`, `sdd-init`) surfaced by `flow workspace status` need a write-side resolution path. Phase 4 adds `flow workspace fix` (R2: `git init` for non-git projects), `flow workspace archive`/`restore` (registry-driven ignore/restore), and the safety infrastructure (pollution-protocol triple, atomic registry writes, dry-run default) required to mutate projects safely. Phase 3's byte-identical contract (AC9) is preserved.

## Scope

### In Scope

- 4-verb CLI surface (`fix`, `archive`, `archived`, `restore`) attached to existing `workspace_group` at `cli.py:2982`
- R2 only: `git init` for `has_git:false` projects
- Registry v1 schema at `~/.flow-engineering/registry.json` (`projects[]` + `archived[]`)
- Pollution-protocol triple (`_snapshot_project` → mutate → `_verify_post_mutation`) via `_apply_hygiene_rule`
- Backup layout at `~/.flow-engineering/backups/<project>/<UTC-ISO-timestamp>/`
- Dry-run default; `--yes` gating for all mutations; `--backup` enforced for `git init` on non-empty projects
- AC9 byte-identical preservation: Phase 1 `_detect_project_markers` outputs are NOT modified by any Phase 4 operation
- 18 new tests in `tests/unit/test_cli_workspace_hygiene.py` (NEW) + extensions to `tests/unit/_workspace_fixtures.py`

### Out of Scope

- **R1 dirty-git**: explicitly deferred. Phase 4 MVP is safe-first. Future change (`workspace-hygiene-r1`) can revisit when user requests it.
- **R3 no-tests**: template-dependent; deferred to future change.
- **R4 no-openspec**: semantic bootstrap; deferred to future change.
- `--json` output flag: not added unless spec phase explicitly demands it.
- Any modification to Phase 1 code (`_detect_project_markers`, `flow projects ls --json` envelope assembly).
- Any modification to Phase 2 code (`where_cmd`, `_run_search`, cross-project helpers).
- TUI / interactive prompts (Phase 5 territory).
- Registry migration tooling.
- Modifications to `flow workspace status` (Phase 3 contract: byte-identical).

## Approach A — Locked

**Operations**: R2 (`git init` + initial empty commit) for `has_git:false` projects; registry-driven `archive`/`restore` for projects to ignore; dry-run default throughout.

**CLI shape** (Option A from explore):
```
flow workspace fix <project> [--dry-run] [--yes] [--backup]
flow workspace archive <project> [--reason TEXT] [--yes]
flow workspace archived
flow workspace restore <project> [--yes]
```

**Justification**: Directly solves session #453's 3 unflushed items. Single PR, ~340 LOC (under 400-line budget, no `size:exception`). Stays on the safe side of the user's "safe-first" mandate by excluding R1 (dirty-git). Provides archive escape hatch for the 5 config/dotfile directories that should never get a repo.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/flow_engineering/cli.py` | Modified | 4 new Click commands attached to `workspace_group` at line 2982; reuse `_git` seam at line 3045 |
| `src/flow_engineering/workspace_hygiene.py` | **New** | Orchestrator module: `_apply_hygiene_rule`, `_snapshot_project`, `_verify_post_mutation`, `_restore_from_snapshot`, `_archive_project`, `_restore_archived_project`, `_load_registry`, `_save_registry_atomic` |
| `src/flow_engineering/registry.py` | **New** | Registry v1 pydantic model + `DEFAULT_REGISTRY_PATH` + atomic read/write via `os.replace` after `tempfile` write |
| `tests/unit/test_cli_workspace_hygiene.py` | **New** | ~18 tests: dry-run non-mutation, `--yes` gating, `--backup` enforcement, R2 success/refusal, archive add/list/restore, registry atomicity, AC9 byte-identical |
| `tests/unit/_workspace_fixtures.py` | Modified | Extend with `make_fake_unmanaged_project` (no-git, non-empty), `make_fake_managed_project` (no-git, empty) |
| `openspec/specs/` | None | No new capability specs; Phase 4 is a modification to existing workspace-capability behavior |

> **Module naming note**: `workspace_status.py` does not exist as a standalone module — `workspace_status` command lives inline in `cli.py`. No collision with proposed `workspace_hygiene.py` or `registry.py`. `project_aliases.py` atomic-write precedent (`tempfile + Path.replace`) is the direct template for `_save_registry_atomic`.

## Registry Schema v1

```json
{
  "version": 1,
  "projects": [
    {
      "path": "/absolute/path/to/project",
      "name": "project-slug",
      "has_git": true,
      "has_openspec": true,
      "has_tests": true,
      "has_graphify": false,
      "last_status_check": "2026-06-30T12:00:00Z"
    }
  ],
  "archived": [
    {
      "name": "archived-project",
      "path": "/absolute/path/to/archived",
      "archived_at": "2026-06-30T12:00:00Z",
      "reason": "dotfiles / never a real project"
    }
  ]
}
```

- **Path**: `~/.flow-engineering/registry.json` (platform via `Path.home()`)
- **Atomic write**: `tempfile.NamedTemporaryFile` + `os.replace` (mirrors `project_aliases.save_aliases` at `project_aliases.py:176`)
- **Migrate-from-none**: `flow workspace fix`/`archive` create the file on first write; `flow projects ls --json` reads read-only and works with no registry present
- **Archived exclusion**: `archived[]` entries are filtered from `flow projects ls --json` and `flow workspace status` totals by Phase 4's `_filter_archived` helper consumed by Phase 3's renderer (Phase 1/3 envelope unchanged)

## Backup Layout

```
~/.flow-engineering/backups/<project_name>/<UTC-ISO-timestamp>/
├── manifest.json   # path, git status pre-mutation, file count, total bytes, rule applied
└── [snapshot of pre-mutation files]
```

- **Pollution-protocol triple**: `_snapshot_project` → mutate → `_verify_post_mutation`. On verify failure: `_restore_from_snapshot` + exit 2.
- **Retention**: leave to spec phase. MVP keeps all backups; no auto-cleanup.
- **Non-mutating backup**: `_snapshot_project` copies files, does not modify the project directory.

## Helper Signatures

```python
# In workspace_hygiene.py (new module)

def _apply_hygiene_rule(
    project: ProjectEntry,
    rule_id: str,
    *,
    dry_run: bool,
    yes: bool,
    backup_path: Path | None,
) -> HygieneResult: ...

def _snapshot_project(project_path: Path, backup_root: Path) -> Path:
    """Copy project files to backup_root/<project>/<ts>/. Returns snapshot dir."""

def _verify_post_mutation(project_path: Path, pre_snapshot: Path) -> bool:
    """Return True if post-mutation state is valid. On False: restore from snapshot."""

def _restore_from_snapshot(snapshot: Path, target: Path) -> None: ...

def _archive_project(
    registry: Registry,
    project_name: str,
    reason: str | None,
) -> None: ...

def _restore_archived_project(
    registry: Registry,
    project_name: str,
) -> None: ...

# In registry.py (new module)

DEFAULT_REGISTRY_PATH: Path  # ~/.flow-engineering/registry.json

class ProjectEntry(TypedDict):
    path: str
    name: str
    has_git: bool
    has_openspec: bool
    has_tests: bool
    has_graphify: bool
    last_status_check: str

class ArchivedEntry(TypedDict):
    name: str
    path: str
    archived_at: str
    reason: str | None

class Registry(TypedDict):
    version: int
    projects: list[ProjectEntry]
    archived: list[ArchivedEntry]

def _load_registry() -> Registry:
    """Missing file → {version:1, projects:[], archived:[]}. Malformed → raise."""

def _save_registry_atomic(registry: Registry) -> None:
    """Atomic write via tempfile + os.replace (mirrors project_aliases pattern)."""
```

## Click Command Signatures

```python
# Attached to workspace_group at cli.py:2982

@workspace_group.command(name="fix")
@click.argument("project")
@click.option("--dry-run/--no-dry-run", default=True, help="Report planned actions without mutating.")
@click.option("--yes", is_flag=True, default=False, help="Required to perform any mutation.")
@click.option("--backup/--no-backup", default=False,
              help="Snapshot project before mutation. Required for git init on non-empty projects.")
def workspace_fix_cmd(project: str, dry_run: bool, yes: bool, backup: bool) -> None: ...

@workspace_group.command(name="archive")
@click.argument("project")
@click.option("--reason", default=None, help="Reason for archiving (recommended).")
@click.option("--yes", is_flag=True, default=False, help="Required to archive.")
def workspace_archive_cmd(project: str, reason: str | None, yes: bool) -> None: ...

@workspace_group.command(name="archived")
def workspace_archived_cmd() -> None:
    """List archived projects."""

@workspace_group.command(name="restore")
@click.argument("project")
@click.option("--yes", is_flag=True, default=False, help="Required to restore.")
def workspace_restore_cmd(project: str, yes: bool) -> None: ...
```

- Pre-flight guard: refuse to operate on `~/.flow-engineering/` itself or on the `flow-engineering` repo path (resolved paths, not strings)
- All commands: exit code 0 on success/dry-run, 1 on user-decline (missing `--yes`), 2 on rule failure

## Safety Posture

| Guard | Behavior |
|-------|----------|
| Dry-run default | Every command's default is `--dry-run`; no mutation without explicit `--yes` |
| `--yes` required | Any mutation refuses with exit 1 if `--yes` is absent |
| `--backup` enforced | R2 (`git init`) on a non-empty project refuses without `--backup`; exit 1 |
| Pollution protocol | `_apply_hygiene_rule` runs snapshot → mutate → verify; on verify failure, restores from snapshot and exits 2 |
| Atomic registry writes | `_save_registry_atomic` uses `tempfile + os.replace` (no partial state on crash) |
| Phase 1/2/3 read-only | `_detect_project_markers` outputs never modified; `_filter_archived` is additive overlay |
| Path pre-flight | Refuse to operate on registry dir or `flow-engineering` own repo |

## Forecast

| Field | Value |
|-------|-------|
| Estimated LOC | ~340 (110 prod + 230 test) |
| Review budget | 340 < 400 → **no `size:exception` needed** |
| Chained PRs | No — single PR viable |
| New tests | +18 in `tests/unit/test_cli_workspace_hygiene.py` (NEW) |
| Test baseline | `uv run --frozen pytest tests/ -q --collect-only` at HEAD `cb82274` |
| Delivery | Single commit, stacked-to-main merge |

## Acceptance Criteria (High-Level)

| # | Criterion |
|---|-----------|
| AC1 | `flow workspace fix <project> --dry-run` (no flags) reports planned actions without touching disk |
| AC2 | `flow workspace fix <project>` without `--yes` exits non-zero with clear error |
| AC3 | `flow workspace fix <non-git-non-empty-project>` without `--backup` exits non-zero with clear error |
| AC4 | `flow workspace fix <non-git-empty-project>` with `--yes --backup` successfully runs `git init` and records it in registry |
| AC5 | `flow workspace archive <project> --yes --reason "..."` moves project from `projects[]` to `archived[]`, excluded from `flow projects ls --json` |
| AC6 | `flow workspace restore <project> --yes` reverses AC5 |
| AC7 | AC9 byte-identical: running any workspace-hygiene command does NOT change `flow projects ls --json` bytes for any OTHER project |
| AC8 | Pollution-protocol: if `_verify_post_mutation` returns False, project state is restored from snapshot |
| AC9 | Registry v1 backward compat: if registry doesn't exist, `fix`/`archive` create it; `flow projects ls --json` works with no registry present |

## Open Questions

1. **Should `--reason` be required (not just optional) for `archive`?** Currently optional via `--reason TEXT`. If user wants enforced documentation, spec phase can make it required.
2. **Should `flow workspace archived` accept `--format text|json` from day one?** Currently text-only. JSON can be added in spec if demanded.
3. **Should backup retention policy be defined now or deferred?** MVP keeps all backups (no auto-cleanup). Spec phase can add retention if needed.
4. **Should `flow workspace restore` auto-pop a `git stash` (R1 future) or just print the stash ref?** For R2 restore from snapshot backup, no git stash is involved. R1 future: recommend print-only to decouple from user intent.

## Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | `git init` on non-empty project collides with future remote push targets | **High** | `--backup` enforced for non-empty; refuse without it |
| 2 | User archives a live project by mistake | **High** | `--yes` + `--reason` required; `archived` listing always visible |
| 3 | Registry write crash leaves partial state | **Medium** | Atomic `os.replace` after `tempfile` write (pollution-protocol) |
| 4 | AC9 byte-identical violation via Phase 4 envelope mutation | **Medium** | Read-only on Phase 1/2/3 code; explicit `test_fix_dry_run_does_not_mutate_filesystem` |
| 5 | Backup retention undefined → disk usage growth | **Low/Medium** | Spec phase decides; MVP keeps all |

## Rollback Plan

- **Code**: revert the single commit; `git revert` or `git reset --hard HEAD~1`.
- **Registry**: atomic `os.replace` means rollback leaves prior `registry.json` intact (temp file is abandoned on crash; on success, prior file is replaced — no prior-file backup retained).
- **Filesystem (git init)**: `git init` is partially irreversible. `_apply_hygiene_rule` snapshots before mutation; `_restore_from_snapshot` recovers. For R2, removal of `.git/` is the rollback — `_restore_from_snapshot` restores files from the backup snapshot.
- **Tests**: `tests/unit/test_cli_workspace_hygiene.py` deleted; `tests/unit/_workspace_fixtures.py` reverted to prior state.

## Dependencies

- `_git` seam at `cli.py:3045` — reused for `git init`, `git commit`
- `_detect_project_markers` — Phase 1 import; read-only
- `_resolve_projects_root` — shared helper
- `project_aliases.py` atomic-write precedent (`tempfile + Path.replace`) — direct template
- `pydantic>=2.5.0` — already in `pyproject.toml`; use for `Registry` TypedDict validation
- `Path.home()` for cross-platform `~/.flow-engineering/` resolution

## Success Criteria

- [ ] `uv run --frozen pytest tests/unit/test_cli_workspace_hygiene.py -q` passes all 18 new tests
- [ ] `uv run --frozen pytest tests/unit/test_cli_workspace_status.py` remains green (AC9 byte-identical)
- [ ] `uv run --frozen ruff check src/flow_engineering/workspace_hygiene.py src/flow_engineering/registry.py src/flow_engineering/cli.py` passes clean
- [ ] `uv run --frozen mypy src/flow_engineering/workspace_hygiene.py src/flow_engineering/registry.py` passes strict
- [ ] `uv run --frozen pytest tests/unit/test_cli_projects.py::test_flow_projects_ls_json_byte_identical_envelope` remains green
- [ ] `flow workspace fix --dry-run` on a no-git empty project prints plan without touching disk
- [ ] `flow workspace archived` lists archived projects without error when registry is empty
