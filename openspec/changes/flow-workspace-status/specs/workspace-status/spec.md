# Spec: workspace-status — Phase 3 of workspace-intelligence

> **Domain**: `flow workspace status` subcommand (CLI). Phase 3 (proposal `#446`, explore `#445`). Aggregates Phase 1's v1 envelope via direct import of `_detect_project_markers` — no subprocess, no mutation of Phase 1 contract.

## Purpose

New top-level `flow workspace status` subcommand synthesizing Phase 1's per-project fields into a needs-attention report. Text default + `--json` envelope (`version:"1"`, `totals`, `projects` verbatim, `needs_attention` list). Five rules (R1–R4 count; R5 informational-only).

## Scope

**In**: `cli.py` (`@main.group("workspace")` + `status` + `_summarize_workspace_status` + `_resolve_projects_root`); `tests/unit/test_cli_workspace_status.py` (NEW, 10 tests); `tests/unit/_workspace_fixtures.py` (NEW, 9 `make_fake_*` helpers).

**Out**: `flow projects ls` (byte-identical preserved); `flow where` (Phase 2); Phase 4 hygiene; Phase 5 dashboard; real Engram/Graphify integration.

## ADDED Requirements

### Requirement: REQ-R1-DIRTY-COMMITTED

The system MUST mark a project as needs-attention when `has_git == true AND dirty == true`. Reason MUST be `"R1: uncommitted work"`.

#### Scenario: R1 detects dirty-committed project
- GIVEN a project with `.git/` AND an uncommitted file
- WHEN `flow workspace status` is invoked
- THEN the project appears in `needs_attention`
- AND `reasons` contains `"R1: uncommitted work"`

### Requirement: REQ-R2-NO-GIT

The system MUST mark a project as needs-attention when `has_git == false`. Reason MUST be `"R2: no version control"`.

#### Scenario: R2 detects no-git project
- GIVEN a project without `.git/`
- WHEN `flow workspace status` is invoked
- THEN the project appears in `needs_attention`
- AND `reasons` contains `"R2: no version control"`

### Requirement: REQ-R3-NO-TESTS

The system MUST mark a project as needs-attention when `test_commands == []`. Reason MUST be `"R3: no tests detected"`.

#### Scenario: R3 detects project with no tests
- GIVEN a project with empty `test_commands`
- WHEN `flow workspace status` is invoked
- THEN the project appears in `needs_attention`
- AND `reasons` contains `"R3: no tests detected"`

### Requirement: REQ-R4-NO-OPENSPEC-SDD-STACK

The system MUST mark a project as needs-attention when `has_openspec == false AND stack in {Python, Go, Rust}`. Reason MUST be `"R4: SDD-adjacent stack missing openspec"`. R4 detection is folded into the JSON envelope scenario (S2) to stay within the 7-scenario budget.

### Requirement: REQ-R5-NO-GRAPHIFY-INFORMATIONAL

The system MAY surface a project as informational when `has_graphify == false`. **INFORMATIONAL ONLY in v1**: MUST NOT add to `needs_attention`. Reason `"R5: graphify not initialized (informational only in v1)"`. The `has_graphify` probe is a Phase 1 stub returning `false`; Phase 2 un-stubs it.

#### Scenario: R5 informational-only does NOT add to needs_attention
- GIVEN a project with `has_graphify == false` (Phase 1 stub)
- WHEN `flow workspace status` is invoked
- THEN the project is NOT in `needs_attention`
- AND the JSON envelope reports `totals.has_graphify == 0`
- AND the text report may include `[INFO: graphify probe is stubbed in v1]`

### Requirement: REQ-WS-JSON-ENVELOPE

`flow workspace status --json` MUST emit one valid JSON object. Top-level keys MUST appear in order: `version, root, totals, projects, needs_attention`. `version` MUST equal `"1"` (string) and be first. `totals` MUST have 8 integer fields: `projects, dirty, no_git, no_tests, has_openspec, has_graphify, has_engram, needs_attention`. `projects` MUST be the verbatim list from `_detect_project_markers` (NOT re-detected). `needs_attention` items MUST have `name`, `reasons[]`, `path`. The v1 envelope MUST NOT include timestamp fields so repeated invocations over an unchanged root remain byte-identical.

#### Scenario: JSON envelope structure (also exercises R4)
- GIVEN a root with 2 projects: Python-with-openspec (clean), Python-without-openspec
- WHEN `flow workspace status --json` is invoked
- THEN stdout is a single valid JSON object
- AND keys appear in order `version, root, totals, projects, needs_attention`
- AND `envelope["version"] == "1"` (first key)
- AND `totals` has all 8 fields (each an int)
- AND `projects` is the verbatim list from `_detect_project_markers`
- AND `needs_attention` has the Python-without-openspec project with `reasons: ["R4: SDD-adjacent stack missing openspec"]`

### Requirement: REQ-WS-TEXT-DEFAULT

Without `--json`, the command MUST emit human-readable ASCII text with: header line, per-project sections (clean → no warnings; dirty → `[DIRTY]`; no-git → `[NO-GIT]`), and a summary at the bottom.

#### Scenario: Default text output format
- GIVEN a root with 3 projects (clean, dirty, no-git)
- WHEN `flow workspace status` is invoked (no flag)
- THEN stdout is human-readable text (NOT JSON)
- AND the text includes a header line
- AND clean has no warnings; dirty has `[DIRTY]`; no-git has `[NO-GIT]`
- AND the text includes a bottom summary (totals)

### Requirement: REQ-WS-EMPTY-ROOT

When the root contains no subdirectories, the command MUST exit 0 with text `(no projects to report)`. With `--json`, `totals.projects == 0` AND `totals.needs_attention == 0`.

#### Scenario: Empty projects root (degenerate case)
- GIVEN a root with NO subdirectories
- WHEN `flow workspace status` is invoked
- THEN stdout is human-readable text with `(no projects to report)`
- AND the process exits with code 0 (no error)
- AND with `--json`, `totals.projects == 0` AND `totals.needs_attention == 0`

## Acceptance Criteria

1. `flow workspace status` (no flag) outputs human-readable text with per-project layout + summary.
2. `flow workspace status --json` outputs a valid JSON envelope parseable by `json.loads()`.
3. JSON envelope has `version: "1"` as the first key (parallels Phase 1's pattern).
4. JSON envelope has `totals` with 8 fields: `projects, dirty, no_git, no_tests, has_openspec, has_graphify, has_engram, needs_attention`.
5. JSON envelope has `needs_attention` list with `name`, `reasons[]`, `path` per entry.
6. R1/R2/R3/R4 (4 rules) count as needs-attention; R5 (1 rule) is informational-only.
7. `has_graphify == false` does NOT add project to `needs_attention`; R5 is informational only in v1.
8. JSON envelope has no timestamp fields and includes `projects` verbatim from Phase 1's v1 envelope.
9. Phase 1's `flow projects ls --json` byte-identical contract is preserved (no mutation of Phase 1 code).
10. 10 new unit tests in `tests/unit/test_cli_workspace_status.py` pass.

## Out of Scope (explicit)

- **`flow projects ls` (Phase 1)** — byte-identical contract MUST stay intact; AC9 protection.
- **`flow where` (Phase 2)** — cross-project retrieval deferred.
- **`flow workspace` hygiene (Phase 4)** — out of scope.
- **Dashboard (Phase 5)** — out of scope.
- **Engram real integration** — `has_engram` stub is Phase 1's; Phase 3 reports it as informational only.
- **Graphify parsing profundo** — `has_graphify` stub is Phase 1's; Phase 3 reports it as informational only.
- **Real cloud backend integration**.
- **New subcommand beyond `flow workspace status`**.

## Cross-References

- Proposal: `openspec/changes/flow-workspace-status/proposal.md` (`#446`)
- Explore: `openspec/changes/flow-workspace-status/explore.md` (`#445`)
- Phase 1 archive: `openspec/changes/workspace-intelligence/` (Engram `#444`)
- Phase 1 spec (read-only): `openspec/changes/workspace-intelligence/specs/projects-ls-extension/spec.md`
- Phase 1 design: `openspec/changes/workspace-intelligence/design.md`
- Shared detection: `src/flow_engineering/cli.py` (`_detect_project_markers`)
