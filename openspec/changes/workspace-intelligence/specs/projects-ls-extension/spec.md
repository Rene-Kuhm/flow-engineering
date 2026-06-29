# Spec: projects-ls-extension

> **Domain**: `flow projects ls` extension in `flow-engineering` (CLI surface). Phase 1 of `workspace-intelligence` (proposal `#437`, explore `#436`). No pre-existing main spec; this file is the canonical requirement set for the change.

## Purpose

Extend `flow projects ls` (`src/flow_engineering/cli.py:2521`) with a
`--json` flag and 11 workspace-intelligence fields per project;
augments `_detect_project_markers()` at `cli.py:2488`. Engram stays
backend (orchestration/retrieval only).

## Scope

**In**: `cli.py` augmentation + `--json` flag; v1 JSON envelope;
`tests/unit/test_cli_projects.py` extension.

**Out**: other projects under `<root>` (read-only targets);
`engram/` (Go backend untouched); `%APPDATA%` filesystem.

## Conventions

`<root>` denotes the configured projects root (default: `C:\dev\proyects`).
Tests use pytest `tmp_path` fixtures and MUST NOT hardcode the real
root — the suite must remain portable across machines.

## ADDED Requirements

### Requirement: REQ-`--json`-FLAG

`flow projects ls --json` MUST emit one valid JSON envelope to stdout
parseable by `json.loads()`. The flag MUST be order-independent
(combinable with `--root` and future path flags). Without `--json`, the
existing human-readable text-table output MUST be preserved.

#### Scenario: --json emits stable JSON envelope

- GIVEN N ≥ 1 projects under the projects root
- WHEN the operator runs `flow projects ls --json`
- THEN stdout contains exactly one valid JSON object
- AND the envelope's top-level keys appear in order `version`, `root`, `projects`
- AND `json.loads()` parses without error
- AND two consecutive invocations on an unchanged filesystem emit byte-identical bytes

#### Scenario: --json absent preserves existing text output

- GIVEN the existing fixture `projects_root` (pyproj-with-flow + my-blog)
- WHEN the operator runs `flow projects ls` (no flag)
- THEN stdout is the existing text table (NOT JSON)
- AND the regression test `test_flow_projects_lists_subdirectories_with_markers` keeps passing

### Requirement: REQ-FIELD-EXTENSION

`flow projects ls` MUST report 11 fields per project (all in JSON;
text output may render a subset):

| # | Field | Type | Source |
|---|-------|------|--------|
| 1 | `name` | string | basename |
| 2 | `path` | string | absolute path |
| 3 | `has_git` | bool | `.git/` exists (dir or worktree file) |
| 4 | `branch` | string\|null | current branch; null when `!has_git` |
| 5 | `dirty` | bool\|null | uncommitted changes; null when `!has_git` |
| 6 | `remote` | string\|null | `git config remote.origin.url`; null when missing |
| 7 | `stack` | enum | `Go \| Python \| Astro \| Next \| Flutter \| Nix \| WXT \| Rust \| Unknown` |
| 8 | `test_commands` | string[] | detected test commands; `[]` when none |
| 9 | `has_openspec` | bool | `path/openspec/changes/` exists |
| 10 | `has_graphify` | bool | stub in Phase 1 (`false`); real probe: `path/graphify-out/graph.{json,html}` |
| 11 | `has_engram` | bool | STUB (`false`) — see REQ-HAS-ENGRAM-STUB |

Missing data MUST be JSON `null` (NOT `""` or omitted). Per-project
detection errors MUST be isolated: broken `.git` → `has_git=false`,
not abort.

#### Scenario: 11-field Go project with git

- GIVEN a project with `go.mod` AND `.git/` (e.g., `engram`)
- WHEN the project is detected
- THEN the record shows `stack: "Go"`, `has_git: true`,
  `branch: "<current>"`, `dirty: <bool>`, `remote: "<url>"`,
  `test_commands: ["go test ./..."]`,
  `has_openspec: <bool>`, `has_graphify: <bool>`, `has_engram: false`

#### Scenario: 11-field Python project with pytest

- GIVEN a project with `pyproject.toml` AND a Makefile or pytest config
- WHEN the project is detected
- THEN `stack: "Python"` AND `test_commands` contains a pytest-derived
  command — `["uv run pytest"]` when `uv.lock` is at root, otherwise `["python -m pytest"]`

### Requirement: REQ-HAS-ENGRAM-STUB

`has_engram` MUST be a documented Phase 1 stub — always `false`,
regardless of real Engram backend state. Production code at
`src/flow_engineering/cli.py` MUST include a
`# TODO(workspace-intelligence): Phase 2` comment near the `has_engram`
evaluation. The CLI `--help` text for `flow projects ls` MUST include:
`NOTE: 'has_engram' is currently a stub field and always reports false;
full Engram integration is planned for a later phase.`

#### Scenario: has_engram stub remains false even when Engram has entries

- GIVEN any project — including those that DO have Engram entries in reality
- WHEN `flow projects ls --json` is invoked
- THEN every project record's `has_engram` is `false`
- AND `flow projects ls --help` contains the `has_engram` stub note

### Requirement: REQ-SCHEMA-VERSIONING

The JSON envelope MUST include a `version` string field with literal
value `"1"`, positioned as the **first key** of the envelope. Future
additive field changes MUST bump the minor version; breaking changes
(renames, removals, type changes) MUST bump the major version. Semver
semantics apply.

#### Scenario: Schema version field present and first

- GIVEN any non-empty project set
- WHEN `flow projects ls --json` is invoked
- THEN `envelope["version"] == "1"` (string)
- AND `version` is the first key in the serialized envelope

### Requirement: REQ-DETERMINISTIC-ORDER

The `projects` array in the JSON envelope MUST be sorted alphabetically
by `name` (case-sensitive, ascending). Text-table output MUST use the
same order. Guarantees diff-based testing and stable downstream
consumption.

#### Scenario: projects array sorted by name

- GIVEN a projects root containing subdirectories `a`, `c`, `b` (in that filesystem order)
- WHEN `flow projects ls --json` is invoked
- THEN the `projects` array order is `["a", "b", "c"]` (NOT the filesystem order)

## Acceptance Criteria

1. `flow projects ls` (no flag) output is unchanged from current behavior (regression covered by `test_flow_projects_lists_subdirectories_with_markers`).
2. `flow projects ls --json` output is valid JSON, parseable by `json.loads()`.
3. JSON output includes all 11 fields per project (Scenario 2 + 3 cover Go and Python; other stacks covered by unit tests).
4. `has_engram` is ALWAYS `false` in Phase 1 (stub).
5. `--help` text for `flow projects ls` includes the `has_engram` stub note.
6. JSON envelope's `version` field is `"1"` (string), positioned as the first key.
7. `projects` array is sorted by `name` (deterministic).
8. Two consecutive invocations on an unchanged filesystem produce byte-identical JSON.
9. `src/flow_engineering/cli.py` includes the `# TODO(workspace-intelligence): Phase 2` comment near the `has_engram` evaluation.
10. New unit tests in `tests/unit/test_cli_projects.py` cover: 11-field schema, `--json` flag, deterministic order, stub semantics.

## Out of Scope (explicit)

- `flow where` cross-project retrieval — Phase 2.
- `flow workspace status` — Phase 3.
- `flow workspace tui` / web dashboard — Phase 5.
- Real Engram backend integration — `has_engram` is a Phase 1 stub only; `C:\dev\proyects\engram` is NOT touched.
- Graphify parsing profundo — Phase 1 stub detector returns `false`.
- Phase 4 workspace hygiene.
- Other projects under `<root>` (`mockup`, `mockup-2-blog`, `tecnosquire-infra`, `Gestor-de-Contrase-as`, `tecnodespegue-landing`, `flow-image-generator-main`) — read-only detection targets.
- `%APPDATA%` filesystem touches.
- New top-level subcommand (no `flow intelligence`, no `flow workspace list`) — extends only.

## Cross-References

- Proposal: `openspec/changes/workspace-intelligence/proposal.md` (`#437`)
- Explore: `openspec/changes/workspace-intelligence/explore.md` (`#436`)
- Baseline: `cli.py:2488` (`_detect_project_markers`); `cli.py:2521` (`projects_ls`)
- Test base: `tests/unit/test_cli_projects.py:1-109`
- Locked approach: α (augment in-place; ~300 LOC; under 400-line budget; 1 PR, no chained).
