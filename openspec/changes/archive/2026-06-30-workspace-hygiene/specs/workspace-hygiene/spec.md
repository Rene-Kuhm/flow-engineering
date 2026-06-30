# Spec: workspace-hygiene — Phase 4 of workspace-intelligence

> **Capability**: `workspace-hygiene` (new — no prior `workspace` capability spec exists at `openspec/specs/workspace/`, so this is a **full spec** structured as a Phase 4 delta to Phase 3's `workspace-status` capability). Additive ONLY: no MODIFIED or REMOVED Requirements.
> **Change**: `workspace-hygiene` (Phase 4 of the workspace-intelligence arc).
> **Builds on**: `openspec/changes/workspace-hygiene/proposal.md` (Approach A locked, 4 open questions resolved).
> **Phase 3 cross-reference**: `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` — REQ-R1..REQ-R5, REQ-WS-JSON-ENVELOPE, REQ-WS-TEXT-DEFAULT, REQ-WS-EMPTY-ROOT. Phase 4 resolves R2 (no-git) and adds an archive escape hatch. R1/R3/R4 are explicitly deferred (see REQ-HYGIENE-R1-EXPLICITLY-OUT below).

## 1. Purpose

Phase 3 (`flow workspace status`) surfaces `needs_attention` items across R1–R5. Phase 4 provides the **write-side MVP** to FIX only R2 (no-git → `git init`) and to archive/restore projects the user no longer maintains (5 dotfile/config directories surfaced by `flow workspace status` in session #453: `.atl`, `.opencode`, `Gestor-de-Contrase-as`, `openspec`, `sdd-init`). All mutations flow through the pollution-protocol triple (`_snapshot_project` → mutate → `_verify_post_mutation` → restore on failure), are gated by `--yes` + dry-run default, and respect the AC9 byte-identical contract from Phase 1/3. R1 dirty-git, R3 no-tests, and R4 no-openspec remain explicitly OUT of scope for this MVP.

## 2. ADDED Requirements (delta to `workspace-status` capability)

### Requirement: REQ-HYGIENE-FIX-SURFACE

`flow workspace fix <project>` SHALL run the R2 hygiene rule (`git init` for `has_git == false` projects) on the named project. The subcommand SHALL refuse to operate on `~/.flow-engineering/` itself, on the `flow-engineering` repo path, and on any project not present in the resolved workspace root. Phase 4 SHALL NOT implement R1, R3, or R4 in this command.

#### Scenario: fix targets a registered no-git project by name
- GIVEN a workspace root containing one project named `mockup` without `.git/`
- WHEN I run `flow workspace fix mockup --yes --backup`
- THEN the exit code is 0
- AND a `.git/` directory exists at the project root
- AND a registry entry for `mockup` appears in `~/.flow-engineering/registry.json`

### Requirement: REQ-HYGIENE-ARCHIVE-SURFACE

`flow workspace archive <project> --reason [TEXT] --yes` SHALL move the named project from `registry.projects[]` to `registry.archived[]`. `--reason` is OPTIONAL. When omitted, the registry's `archived[].reason` field SHALL equal the literal string `"manual archive"`. When omitted, the command SHALL print the recorded reason to stdout so the user can see what was written. The subcommand SHALL refuse to operate without `--yes`.

#### Scenario: archive with explicit --reason records the user-supplied value
- GIVEN a registered project named `mockup-2-blog`
- WHEN I run `flow workspace archive mockup-2-blog --reason "deprecated" --yes`
- THEN the exit code is 0
- AND `registry.archived[]` contains one entry with `name == "mockup-2-blog"` and `reason == "deprecated"`
- AND `mockup-2-blog` no longer appears in `flow projects ls --json` output

#### Scenario: archive without --reason uses the default value and logs it
- GIVEN a registered project named `openspec`
- WHEN I run `flow workspace archive openspec --yes`
- THEN the exit code is 0
- AND the registry entry for `openspec` has `reason == "manual archive"`
- AND stdout includes the line `archived: openspec (reason: manual archive)`

### Requirement: REQ-HYGIENE-ARCHIVED-LISTING

`flow workspace archived` SHALL output a TEXT-only listing of archived projects to stdout. The subcommand SHALL NOT accept `--format`, `--json`, or any machine-output flag in Phase 4 MVP. Columns SHALL be `name`, `archived_at`, `reason` (in that order, fixed-width text table).

#### Scenario: archived outputs a text table with three columns
- GIVEN a registry with 2 archived projects (`mockup-2-blog` reason `"deprecated"`, `openspec` reason `"manual archive"`)
- WHEN I run `flow workspace archived`
- THEN the exit code is 0
- AND stdout is a text table (NOT JSON)
- AND stdout contains the header line `NAME  ARCHIVED_AT  REASON`
- AND stdout contains a row for each of the two archived projects

#### Scenario: archived with no entries prints a clean message
- GIVEN a registry with `archived == []`
- WHEN I run `flow workspace archived`
- THEN the exit code is 0
- AND stdout contains the line `(no archived projects)`

### Requirement: REQ-HYGIENE-RESTORE-SURFACE

`flow workspace restore <project> --yes` SHALL reverse a prior archive by moving the named entry from `registry.archived[]` back to `registry.projects[]`. The subcommand SHALL refuse to operate without `--yes`. Restoring a project that is not in `archived[]` SHALL exit non-zero with a clear error.

#### Scenario: restore reverses a prior archive
- GIVEN a project `mockup-2-blog` present in `registry.archived[]`
- WHEN I run `flow workspace restore mockup-2-blog --yes`
- THEN the exit code is 0
- AND `mockup-2-blog` is no longer in `registry.archived[]`
- AND `mockup-2-blog` reappears in `flow projects ls --json` output
- AND `mockup-2-blog` no longer appears in `flow workspace archived` output

#### Scenario: restore refuses without --yes
- GIVEN a project `mockup-2-blog` present in `registry.archived[]`
- WHEN I run `flow workspace restore mockup-2-blog`
- THEN the exit code is non-zero
- AND stderr mentions `--yes`
- AND `registry.archived[]` is unchanged

### Requirement: REQ-HYGIENE-REGISTRY-V1

The system SHALL persist a registry file at `~/.flow-engineering/registry.json` with schema `version: 1`, `projects: list[ProjectEntry]`, and `archived: list[ArchivedEntry]`. Reads of a missing file SHALL return `{version: 1, projects: [], archived: []}`. Reads of malformed JSON SHALL exit non-zero with a clear error. Writes SHALL be atomic via `tempfile.NamedTemporaryFile` + `os.replace` (mirrors `project_aliases.save_aliases` at `src/flow_engineering/project_aliases.py:164`). The registry SHALL be created on first mutation by `fix` or `archive` only. Read-only consumers (`flow projects ls --json`, `flow workspace status`) MUST NOT create or modify the registry.

#### Scenario: registry file is created on first archive
- GIVEN `~/.flow-engineering/registry.json` does not exist
- WHEN I run `flow workspace archive <project> --yes`
- THEN `~/.flow-engineering/registry.json` exists
- AND its content parses as JSON with `version == 1` and the project in `archived[]`

#### Scenario: registry write is atomic on interruption
- GIVEN the registry write is interrupted (simulated by raising inside `os.replace`)
- WHEN the next read occurs
- THEN no partial `registry.json` exists on disk
- AND the prior registry content (if any) is still readable

#### Scenario: read-only consumers do not create the registry
- GIVEN `~/.flow-engineering/registry.json` does not exist
- WHEN I run `flow projects ls --json`
- THEN the command exits 0
- AND `~/.flow-engineering/registry.json` STILL does not exist

### Requirement: REQ-HYGIENE-BACKUP-LAYOUT

When `--backup` is passed, the system SHALL create a snapshot at `~/.flow-engineering/backups/<project_name>/<UTC-ISO-timestamp>/`. The directory SHALL contain a `manifest.json` with `project_name`, `project_path`, `rule_id`, `git_status_pre`, `files_count`, `bytes_total`, and `created_at` fields, plus a verbatim copy of the project's pre-mutation files (excluding `.git/`). The UTC timestamp SHALL be ISO 8601 with `Z` suffix (e.g., `2026-06-30T12:34:56Z`). Retention SHALL be INDEFINITE — backups accumulate at this path with no auto-prune, TTL, or size cap in Phase 4 MVP. Manual cleanup is the operator's responsibility.

#### Scenario: backup directory and manifest are created for a non-empty project
- GIVEN a non-empty no-git project named `mockup`
- WHEN I run `flow workspace fix mockup --yes --backup`
- THEN `~/.flow-engineering/backups/mockup/<UTC-ISO>/manifest.json` exists
- AND the manifest's `project_name == "mockup"`
- AND the manifest's `rule_id == "R2"`
- AND the snapshot directory contains copies of the pre-mutation files

### Requirement: REQ-HYGIENE-POLLUTION-PROTOCOL

Every mutation SHALL execute the triple: `_snapshot_project` (when `--backup` is set) → `_apply_rule` → `_verify_post_mutation`. If `_verify_post_mutation` returns False, the system SHALL call `_restore_from_snapshot` and exit with code 2. This implements the pollution-protocol triple referenced in the change proposal (Engram observation banked from prior session).

#### Scenario: post-mutation verify failure triggers restore from snapshot
- GIVEN a project `mockup` with a `--backup` snapshot taken
- AND the post-mutation verifier is monkeypatched to return False (simulated failure)
- WHEN I run `flow workspace fix mockup --yes --backup`
- THEN the exit code is 2
- AND the project state is restored from the pre-mutation snapshot
- AND stderr includes the text `verify failed`

### Requirement: REQ-HYGIENE-DRY-RUN-DEFAULT

The default behavior of `flow workspace fix` and `flow workspace archive` SHALL be dry-run: the command prints the planned action and exits 0 without mutating the project directory, the registry, or the backup store. Passing `--yes` SHALL switch to execute mode. The subcommands SHALL refuse to mutate when `--yes` is absent (exit code 1, stderr mentions `--yes`).

#### Scenario: fix with no flags is a dry-run
- GIVEN a non-git project `mockup` containing a file `README.md`
- WHEN I run `flow workspace fix mockup`
- THEN the exit code is 0
- AND stdout reports the planned action
- AND no `.git/` directory is created
- AND the mtime of `README.md` is unchanged
- AND no registry mutation occurred

#### Scenario: archive refuses to mutate without --yes
- GIVEN a registered project `mockup`
- WHEN I run `flow workspace archive mockup --reason "deprecated"`
- THEN the exit code is non-zero
- AND stderr mentions `--yes`
- AND the registry is unchanged

### Requirement: REQ-HYGIENE-BACKUP-GATE-NONEMPTY

`flow workspace fix <project>` SHALL refuse to run `git init` on a NON-EMPTY project unless `--backup` is also passed. A project is "empty" iff `.git/` is absent AND no visible (non-hidden) files are present. Hidden system files (`.DS_Store`, `Thumbs.db`, desktop.ini) SHALL NOT count toward "non-empty". The refusal message SHALL mention `--backup`.

#### Scenario: fix on non-empty project without --backup refuses
- GIVEN a non-git project `mockup` containing `README.md`
- WHEN I run `flow workspace fix mockup --yes`
- THEN the exit code is non-zero
- AND stderr mentions `--backup`
- AND no `.git/` directory is created

#### Scenario: fix on truly empty project without --backup succeeds
- GIVEN a non-git project `mockup` containing zero user-visible files
- WHEN I run `flow workspace fix mockup --yes`
- THEN the exit code is 0
- AND a `.git/` directory exists at the project root
- AND no backup was created (nothing to snapshot)

### Requirement: REQ-HYGIENE-AC9-PRESERVATION

The Phase 1 v1 JSON envelope contract (`flow projects ls --json` byte-identical across invocations on an unchanged filesystem) MUST remain intact. Running any `flow workspace {fix,archive,archived,restore}` command MUST NOT modify `_detect_project_markers` (defined at `src/flow_engineering/cli.py:3137`, returning the 14-key marker dict described at `src/flow_engineering/cli.py:3140`) for any project other than the explicit target. The byte-identical guard test `test_flow_projects_ls_json_byte_identical_envelope` at `tests/unit/test_cli_projects.py:435` MUST remain green throughout Phase 4.

#### Scenario: workspace-hygiene commands preserve flow projects ls --json bytes for non-targets
- GIVEN a workspace root with projects `project-a` (target) and `project-b` (non-target)
- AND `flow projects ls --json` produces a captured byte string for `project-b`
- WHEN I run `flow workspace archive project-a --yes`
- THEN `flow projects ls --json` for `project-b` is byte-identical to the captured bytes

### Requirement: REQ-HYGIENE-R1-EXPLICITLY-OUT

Phase 4 MVP SHALL NOT implement the R1 dirty-git rule. The `flow workspace fix` subcommand SHALL NOT execute any R1 remediation. The phrase describing this prohibition in this spec is "R1 dirty-git is OUT OF SCOPE for Phase 4 MVP". This REQ is a hard wall: any code path that mutates R1-flagged projects' working tree, untracked files, or index SHALL be rejected at code review. Future change `workspace-hygiene-r1` may revisit this; Phase 4 makes no commitment.

#### Scenario: fix on a dirty-git project does not remediate the dirty state
- GIVEN a git project with an uncommitted file
- WHEN I run `flow workspace fix <project>` (any flags)
- THEN the uncommitted file is still present
- AND the project's working tree is unchanged
- AND the project's git index is unchanged
- AND the project's untracked files are unchanged
- AND no worktree manipulation has occurred
- AND the exit code is 0 with stdout explaining "R1 dirty-git is OUT OF SCOPE for Phase 4 MVP"

### Requirement: REQ-HYGIENE-NO-JSON-MVP

The `flow workspace archived` subcommand SHALL NOT accept `--format` or `--json` in Phase 4 MVP. The `flow workspace fix`, `flow workspace archive`, and `flow workspace restore` subcommands SHALL NOT emit machine-readable JSON output in MVP. If a downstream consumer needs structured data, it MUST pipe the text output. Adding a JSON output mode is a separate (unscheduled) future change.

#### Scenario: archived subcommand rejects --json attempt
- GIVEN any registry state
- WHEN I run `flow workspace archived --json`
- THEN the exit code is non-zero
- AND stderr indicates `--json` is unsupported in MVP

## 3. MODIFIED Requirements

None. Phase 4 is purely additive to the Phase 3 `workspace-status` capability. No existing REQ is changed.

## 4. REMOVED Requirements

None. No REQ from Phase 3 is deprecated or removed.

## 5. BDD Scenarios (mirror at `tests/bdd/workspace_hygiene.feature`)

Thirteen Given/When/Then scenarios, one per acceptance criterion. Each scenario is bound to a single REQ above. Scenarios run via pytest-bdd with step glue in a new `tests/bdd/test_workspace_hygiene_steps.py`. Step definitions follow the `req_*.feature` precedent (`tests/bdd/req27_project_aliases.feature`). The feature file ships 16 scenarios in total: 13 required + 3 edge cases (empty-archive list, restore-without-`--yes`, registry-read-only-consumer-non-mutation).

| Scenario | REQ | Maps to AC |
|----------|-----|------------|
| dry-run on non-git project does not mutate filesystem | REQ-HYGIENE-DRY-RUN-DEFAULT | AC1 |
| fix without --yes refuses and mentions --yes | REQ-HYGIENE-DRY-RUN-DEFAULT | AC2 |
| non-empty fix without --backup refuses and mentions --backup | REQ-HYGIENE-BACKUP-GATE-NONEMPTY | AC3 |
| non-empty fix with --yes --backup creates .git and backup | REQ-HYGIENE-FIX-SURFACE + REQ-HYGIENE-BACKUP-LAYOUT | AC4 |
| empty fix with --yes (no --backup) creates .git and no backup | REQ-HYGIENE-BACKUP-GATE-NONEMPTY | AC5 |
| archive with --reason records the value and removes from ls | REQ-HYGIENE-ARCHIVE-SURFACE | AC6 |
| archive without --reason defaults to "manual archive" | REQ-HYGIENE-ARCHIVE-SURFACE | AC7 |
| archived command outputs text table with 3 columns | REQ-HYGIENE-ARCHIVED-LISTING | AC8 |
| restore reverses archive and reappears in ls | REQ-HYGIENE-RESTORE-SURFACE | AC9 |
| workspace-hygiene does not alter non-target flow projects ls --json bytes | REQ-HYGIENE-AC9-PRESERVATION | AC10 |
| post-mutation verify failure restores from snapshot | REQ-HYGIENE-POLLUTION-PROTOCOL | AC11 |
| registry atomic write prevents partial state on interruption | REQ-HYGIENE-REGISTRY-V1 | AC12 |
| dirty-git project under fix is left untouched | REQ-HYGIENE-R1-EXPLICITLY-OUT | AC13 |

## 6. Acceptance Criteria mapping

| # | Criterion | REQ | BDD scenario |
|---|-----------|-----|--------------|
| AC1 | `flow workspace fix <project>` with no flags exits 0, prints plan, does not mutate | REQ-HYGIENE-DRY-RUN-DEFAULT | dry-run does not mutate |
| AC2 | `flow workspace fix <project> --backup` without --yes exits non-zero, mentions --yes | REQ-HYGIENE-DRY-RUN-DEFAULT | missing --yes refuses |
| AC3 | `flow workspace fix <non-git-non-empty>` without --backup exits non-zero, mentions --backup | REQ-HYGIENE-BACKUP-GATE-NONEMPTY | non-empty without --backup refuses |
| AC4 | `flow workspace fix <non-git-non-empty> --yes --backup` creates .git and backup | REQ-HYGIENE-FIX-SURFACE + REQ-HYGIENE-BACKUP-LAYOUT | full happy path |
| AC5 | `flow workspace fix <non-git-empty> --yes` (no --backup) creates .git, no backup | REQ-HYGIENE-BACKUP-GATE-NONEMPTY | empty project no backup |
| AC6 | `flow workspace archive <project> --reason X --yes` records X, removes from ls | REQ-HYGIENE-ARCHIVE-SURFACE | archive with --reason |
| AC7 | `flow workspace archive <project> --yes` defaults reason to "manual archive" | REQ-HYGIENE-ARCHIVE-SURFACE | archive without --reason |
| AC8 | `flow workspace archived` outputs text table with 3 columns, no JSON flag | REQ-HYGIENE-ARCHIVED-LISTING | archived text table |
| AC9 | `flow workspace restore <project> --yes` reverses archive | REQ-HYGIENE-RESTORE-SURFACE | restore reverses archive |
| AC10 | workspace-hygiene does not alter non-target `flow projects ls --json` bytes | REQ-HYGIENE-AC9-PRESERVATION | AC9 preserved for non-targets |
| AC11 | verify failure restores from snapshot, exit 2 | REQ-HYGIENE-POLLUTION-PROTOCOL | verify-fail restore |
| AC12 | registry atomic write prevents partial state | REQ-HYGIENE-REGISTRY-V1 | registry atomic write |
| AC13 | R1 dirty-git is OUT OF SCOPE; fix does not remediate dirty state | REQ-HYGIENE-R1-EXPLICITLY-OUT | R1 dirty-git untouched |

## 7. Out of Scope (explicit)

- **R1 dirty-git** — deferred; no uncommitted-state handling, no R1 remediation. The phrase "R1 dirty-git is OUT OF SCOPE for Phase 4 MVP" is the canonical wording.
- **R3 no-tests** bootstrap — template-dependent; deferred to a future change.
- **R4 no-openspec** bootstrap — semantic scaffold; deferred to a future change.
- **R5 no-graphify** — informational-only in Phase 3; no action.
- **`--json` / `--format` on `flow workspace archived`** — deferred.
- **Backup retention / pruning** — deferred; indefinite retention in MVP. Manual cleanup is the operator's responsibility (documented in user-facing docs as a known operational consideration).
- **TUI / interactive prompts** — Phase 5.
- **Web dashboard** — Phase 5.
- **Modifications to Phase 1 / Phase 2 / Phase 3 code paths** — Phase 4 is additive only. The byte-identical guard test (`tests/unit/test_cli_projects.py:435`) MUST remain green.
- **Registry migration tooling** — no v0 → v1 migration needed; fresh registry on first write.
- **Any mutation of the flow-engineering own repo path or `~/.flow-engineering/`** — pre-flight guard refuses.

## 8. Dependencies

- Phase 1 v1 JSON envelope contract (`flow projects ls --json`) — read-only consumer. MUST be preserved. Source: `src/flow_engineering/cli.py:3137` (`_detect_project_markers`).
- Phase 3 `flow workspace status` aggregation — read-only consumer. Not modified. Source: `src/flow_engineering/cli.py:2982` (`workspace_group`) and `src/flow_engineering/cli.py:2869` (`_summarize_workspace_status`).
- `_git` subprocess seam — reused for `git init`. Source: `src/flow_engineering/cli.py:3045`.
- `project_aliases.save_aliases` atomic-write precedent — direct template for `_save_registry_atomic`. Source: `src/flow_engineering/project_aliases.py:164`.
- Python 3.12, `pydantic>=2.5.0`, `click` — already in `pyproject.toml`.
- `Path.home()` for cross-platform `~/.flow-engineering/` resolution.
- `tempfile.NamedTemporaryFile` + `os.replace` for atomic writes (stdlib).

## 9. Open Questions (resolved by user, immutable for spec phase)

- **Q1 → A1**: `--reason` is OPTIONAL on `archive`. Default value is the literal string `"manual archive"`. No validation, no prompt. Logged to stdout so the user can see what was recorded.
- **Q2 → A2**: `flow workspace archived` outputs TEXT only in MVP. No `--format` flag, no `--json`. If a downstream consumer needs JSON, it must pipe the text output.
- **Q3 → A3**: Backup retention is INDEFINITE / no auto-delete in Phase 4. All backups accumulate at `~/.flow-engineering/backups/<project>/<UTC-ISO-timestamp>/`. No pruning, no TTL, no size cap. Documented as a known operational consideration.
- **Q4 → A4**: R1 dirty-git is FULLY OUT OF SCOPE for Phase 4. No uncommitted-state handling. The phrase "R1 dirty-git is OUT OF SCOPE for Phase 4 MVP" is the canonical wording wherever the prohibition needs restating.

## 10. Cross-References

- Proposal: `openspec/changes/workspace-hygiene/proposal.md` (Approach A locked; 4 open questions resolved)
- Explore: `openspec/changes/workspace-hygiene/explore.md` (Approach A + Option A CLI shape)
- Phase 3 spec (precedent): `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` (REQ-R1..R5, REQ-WS-JSON-ENVELOPE, REQ-WS-TEXT-DEFAULT, REQ-WS-EMPTY-ROOT)
- Phase 1 spec (read-only consumer): `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md`
- BDD feature file: `tests/bdd/workspace_hygiene.feature` (NEW, 13 scenarios)
- Byte-identical guard test: `tests/unit/test_cli_projects.py:435` (`test_flow_projects_ls_json_byte_identical_envelope`)
- Subprocess seam: `src/flow_engineering/cli.py:3045` (`_git`)
- Project-marker detector (read-only): `src/flow_engineering/cli.py:3137` (`_detect_project_markers`)
- Workspace group: `src/flow_engineering/cli.py:2982` (`workspace_group`)
- Atomic-write precedent: `src/flow_engineering/project_aliases.py:164` (`save_aliases`)
