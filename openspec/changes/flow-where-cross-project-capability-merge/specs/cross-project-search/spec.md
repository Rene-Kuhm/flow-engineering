# Spec: cross-project-search — Phase 2 of workspace-intelligence

> **Domain**: `flow where` cross-project extension. Phase 2 (proposal `#454`). ADDITIVE to existing `flow where` (REQ-V1.0.1..V1.0.4 from archived `flow-where-mvp`). Does NOT modify `where.py` module API.

## Purpose

Extend `flow where "<query>"` with cross-project search scope, three output formats (text/json/tsv), and --regex/--engram flags. The change is read-only aggregation — no mutation of existing `where.py` module behavior.

## Scope

**In**: `where_cmd` in `cli.py` (additive extension); `tests/unit/test_cli_where_cross_project.py` (NEW, 10 tests); `tests/unit/_workspace_fixtures.py` (reuse + 1 new helper).

**Out**: `where.py` module API (`where()`, `grep_repo`, `grep_sdd_archive`, `grep_graphify`, `_run_search`, `_parse_hits` unchanged); Phase 1 `_detect_project_markers`; Phase 3 `_resolve_projects_root`; Phase 1/3 test files.

## ADDED Requirements

### Requirement: REQ-CROSS-PROJECT-SCOPE

The system MUST search ONLY these 6 directories per project under `--root`: `src/` (type `code`), `internal/` (type `code`), `cmd/` (type `code`), `tests/` (type `test`), `openspec/` (type `sdd`), `graphify-out/` (type `graph`). Missing subdirectories MUST be silently skipped. Files outside these 6 directories MUST NOT be scanned regardless of query match.

#### Scenario: Cross-project search scans exactly 6 dirs
- GIVEN a root with 2 projects: `proj-a/src/foo.py` and `proj-b/node_modules/bar.js`
- WHEN `flow where "foo" --root PATH` is invoked
- THEN only `proj-a/src/foo.py` is searched (not `proj-b/node_modules/`)
- AND `proj-b/node_modules/bar.js` is NEVER scanned even if it contains the query

#### Scenario: Missing directory silently skipped
- GIVEN a project with no `internal/` subdirectory
- WHEN `flow where "query" --root PATH` is invoked
- THEN the command does NOT error on the missing directory
- AND search continues across remaining 5 directories

### Requirement: REQ-DEFAULT-TEXT-FORMAT

Without `--format`, the command MUST emit ASCII-safe text grouped by project. Each project section MUST contain: `project_name` header line, then rows of `file:line  content` (tab-aligned), then a TOTAL summary line. Output MUST NOT contain box-drawing characters or non-ASCII bytes.

#### Scenario: Default text output with multiple projects
- GIVEN root with `proj-a/src/foo.py` containing "def foo" and `proj-b/src/bar.py` containing "def foo"
- WHEN `flow where "def foo" --root PATH` is invoked
- THEN output contains `proj-a` header then `proj-a/src/foo.py:1  def foo`
- AND output contains `proj-b` header then `proj-b/src/bar.py:1  def bar`
- AND output contains a TOTAL line with match count
- AND output is ASCII-safe (no Unicode box-drawing chars)

#### Scenario: Empty match set renders "(no matches)"
- GIVEN root with `proj-a/src/foo.py` containing "bar" but not "nonexistent"
- WHEN `flow where "nonexistent" --root PATH` is invoked
- THEN output renders `(no matches)` per project
- AND TOTAL line shows `matches: 0`
- AND exit code is 0 (empty match set is NOT an error)

### Requirement: REQ-EXPLICIT-FORMAT-FLAG

`--format {text,json,tsv}` MUST produce exactly one of three formats. `--format=text` emits the ASCII-safe grouped text. `--format=json` emits a single JSON envelope. `--format=tsv` emits TSV with header.

#### Scenario: --format=json envelope structure
- GIVEN root with 1 project containing `src/foo.py` with "def foo"
- WHEN `flow where "def foo" --root PATH --format json` is invoked
- THEN stdout is a single valid JSON object
- AND top-level keys appear in order: `version`, `root`, `query`, `format`, `results`, `totals`
- AND `version == "1"` (string, first key)
- AND `results[]` items have: `project`, `file`, `line`, `content`, `type` (type is `code`)
- AND `totals` has: `projects_searched` (int), `matches` (int)
- AND `engram` field present as `{enabled: false, phase: "stub"}` (Phase 2 stub)

#### Scenario: --format=tsv header and body
- GIVEN root with 1 project containing `src/foo.py` with "def foo"
- WHEN `flow where "def foo" --root PATH --format tsv` is invoked
- THEN first line is exactly `project\tfile\tline\ttype\tcontent`
- AND subsequent lines are tab-separated with matching rows
- AND any newline inside `content` is escaped as literal `\n` (not a real newline)

### Requirement: REQ-EXIT-CODE-MAPPING

The system MUST exit with code `0` when matches are found OR when no matches exist (empty set). The system MUST exit with code `1` when NO matches are found. The system MUST exit with code `2` for errors: invalid `--regex` pattern, unreadable `--root` path, or other CLI-level failures.

#### Scenario: Exit 0 on match
- GIVEN root with `proj-a/src/foo.py` containing "foo"
- WHEN `flow where "foo" --root PATH` is invoked
- THEN exit code is 0

#### Scenario: Exit 1 on no match
- GIVEN root with `proj-a/src/foo.py` containing "foo" but not "nonexistent"
- WHEN `flow where "nonexistent" --root PATH` is invoked
- THEN exit code is 1

#### Scenario: Exit 2 on invalid regex
- GIVEN root with a valid project
- WHEN `flow where "[invalid" --root PATH --regex` is invoked
- THEN exit code is 2
- AND error message mentions the regex parse failure

### Requirement: REQ-ENGRAM-STUB

`--engram` flag is accepted with no behavior change in Phase 2. The flag MUST NOT cause an error. In `--format=json` output, `engram` field MUST be present as `{enabled: false, phase: "stub"}`.

#### Scenario: --engram flag accepted with no-op
- GIVEN root with a valid project containing "foo"
- WHEN `flow where "foo" --root PATH --engram` is invoked
- THEN exit code is 0 (normal behavior)
- AND output is identical to invocation without `--engram`

#### Scenario: --engram in JSON envelope as stub
- GIVEN root with a valid project
- WHEN `flow where "foo" --root PATH --format json --engram` is invoked
- THEN the JSON envelope contains `engram: {enabled: false, phase: "stub"}`

### Requirement: REQ-REGEX-OPT-IN

`--regex` flag enables regex matching (case-insensitive). Without `--regex`, matching is case-insensitive substring. When `--regex` is set, `re.compile(query)` is called at the CLI boundary to validate; exit 2 on `re.error`.

#### Scenario: --regex matches function definitions
- GIVEN root with `proj-a/src/foo.py` containing `def foo():` and `def bar():`
- WHEN `flow where "^def " --root PATH --regex` is invoked
- THEN both `def foo():` and `def bar():` are matched
- AND exit code is 0

#### Scenario: Invalid regex exits 2
- GIVEN root with a valid project
- WHEN `flow where "a[b" --root PATH --regex` is invoked
- THEN exit code is 2
- AND stderr/stdout mentions the regex parsing failure

## Acceptance Criteria

1. `flow where "query" --root PATH` outputs ASCII-safe text grouped by project with TOTAL summary line.
2. `flow where "query" --root PATH --format json` outputs a valid JSON envelope with `version:"1"` as first key and `results[]` + `totals`.
3. `flow where "query" --root PATH --format tsv` outputs header `project\tfile\tline\ttype\tcontent` and tab-separated body with `\n` escape in content.
4. `--regex` flag validates via `re.compile()` at CLI boundary; exit 2 on invalid regex.
5. `--engram` flag accepted; no behavior change; `engram: {enabled: false, phase: "stub"}` in JSON envelope.
6. Exit code 0: matches found OR empty set; exit code 1: no matches; exit code 2: error.
7. Files outside the 6 locked directories (e.g., `node_modules/`) are NEVER scanned.
8. `--limit N` caps results per project (default 50).
9. Phase 1 `flow projects ls --json` byte-identical contract preserved.
10. Phase 3 `flow workspace status` behavior unchanged.

## Out of Scope (explicit)

- **`where.py` module API** — `where()`, `grep_repo`, `grep_sdd_archive`, `grep_graphify`, `_run_search`, `_parse_hits` unchanged
- **`flow projects ls` (Phase 1)** — byte-identical contract preserved; AC9 protection
- **`flow workspace status` (Phase 3)** — behavior unchanged
- **Phase 4 hygiene** (`flow workspace clean`)
- **Phase 5 dashboard** (`flow workspace dashboard`)
- **Real Engram MCP/API integration** — `--engram` stub is Phase 2; Phase 4+ real integration
- **New subcommand** beyond `flow where`
- **Modifying `_detect_project_markers` or `_resolve_projects_root`**

## Cross-References

- Proposal: `openspec/changes/flow-where-cross-project/proposal.md` (`#454`)
- Explore: `openspec/changes/flow-where-cross-project/explore.md` (`#454`)
- Phase 1 archive: `openspec/changes/archive/2026-06-28-flow-where-mvp/` (archived)
- Phase 3: `openspec/changes/flow-workspace-status/` (merged)
- `src/flow_engineering/cli.py:399-438` (`where_cmd`)
- `src/flow_engineering/where.py:89-124` (`_run_search`, `_parse_hits`)
