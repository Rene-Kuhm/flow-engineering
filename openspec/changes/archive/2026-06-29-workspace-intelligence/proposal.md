# Proposal: workspace-intelligence — Phase 1

## Intent

Extend the existing `flow projects ls` command (cli.py:2521) with a `--json` flag and 7 new detection dimensions (branch, dirty, remote, test_commands, has_openspec, has_graphify, has_engram stub). Reuse and augment the existing `_detect_project_markers()` (cli.py:2488) in-place rather than duplicating detection logic. Phase 1 of a 5-phase workspace-intelligence effort; does NOT create a new subcommand.

## Scope

### In Scope
- `src/flow_engineering/cli.py` — augment `_detect_project_markers()` + add `--json` flag to `projects_ls`
- `tests/unit/test_cli_projects.py` — extend existing tests for new fields + JSON output
- `openspec/changes/workspace-intelligence/` — openspec SoT (this document)

### Out of Scope
- New subcommand (no `flow intelligence`, no `flow workspace list`) — extend only
- `flow where` extension (Phase 2)
- `flow workspace status` / `flow workspace tui` / dashboard (Phases 3–5)
- Engram backend modifications (Go project; `has_engram` is a stub seam)
- Other projects under `C:\dev\proyects\` — read-only catalog targets; no modifications
- `%APPDATA%` filesystem touches
- Commits, pushes, or merges (propose phase only)

## Capabilities

### New Capabilities
- `flow-projects-ls-json`: `flow projects ls --json` emits a stable v1 JSON envelope with 11 fields per project (see schema below).

### Modified Capabilities
- `flow-projects-ls`: adds `--json` flag + 7 new detection dimensions to the existing text-table output.

## Approach α (Augment In-Place)

Lock: **α — augment `_detect_project_markers()`**

**Rationale**: The existing function is 31 LOC (cli.py:2488–2518), returns a simple `dict[str, str | None]`, and is tightly scoped. Augmenting it avoids duplication and keeps detection logic in one place. The function is small enough that extension is cleaner than replacement.

**Implementation plan**:
1. Rename the return type to `dict[str, Any]` and add 7 new keys: `branch` (str|null), `dirty` (bool|null), `remote` (str|null), `stack` (str), `test_commands` (list[str]), `has_openspec` (bool), `has_graphify` (bool), `has_engram` (bool stub).
2. Add `import subprocess` at cli.py top if not present.
3. Stack detection: extend existing block (Flutter `pubspec.yaml`, Nix `flake.nix`/`default.nix`, WXT `wxt.config.ts`) before the Rust fallback.
4. Git detection: `subprocess.run(["git", "rev-parse", ...], ...)` with 5s timeout, `try/except OSError` per call — isolated per project.
5. Test commands: probe `pyproject.toml [tool.pytest.ini_options]` → `Makefile test:` → `package.json scripts.test` per stack.
6. `projects_ls`: add `@click.option("--json", ...)` flag; branch on `json_flag` to emit `json.dumps(v1_envelope, indent=2)`.
7. `has_engram`: stub returning `False` always; document with `# TODO Phase 2: replace with real Engram MCP call` and `--help` note.

## JSON Output Schema v1 (11 fields)

```json
{
  "version": "1",
  "root": "C:\\dev\\proyects",
  "projects": [
    {
      "name": "engram",
      "path": "C:\\dev\\proyects\\engram",
      "has_git": true,
      "branch": "main",
      "dirty": false,
      "remote": "https://github.com/Gentleman-Programming/engram.git",
      "stack": "Go",
      "test_commands": ["go test ./..."],
      "has_openspec": true,
      "has_graphify": false,
      "has_engram": false
    }
  ]
}
```

**Field-level decisions**:
- All fields required; missing data is `null` (not `""` or omitted).
- `stack` enum: `Go | Python | Astro | Next | Flutter | Nix | WXT | Rust | Unknown`.
- `test_commands`: `string[]`, empty array `[]` when none detected.
- Projects sorted alphabetically by `name` (deterministic, matches existing `projects_ls` ordering).
- Per-project errors isolated: broken `.git` returns `has_git=false` rather than aborting the whole listing.
- Schema versioning: `version: "1"` bumped on breaking change; additive changes documented in CHANGELOG.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `cli.py:2488` | Modified | Augment `_detect_project_markers()` with 7 new fields |
| `cli.py:2521` | Modified | Add `--json` flag to `projects_ls`; emit v1 JSON envelope |
| `tests/unit/test_cli_projects.py` | Modified | Extend fixtures + add tests for 7 new fields + JSON output |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `_detect_project_markers()` augmentation grows too large (>60 LOC) — α becomes wrong choice | Low | Monitor; if >60 LOC refactor to `_detect_workspace_intel()` (β) before apply |
| Subprocess overhead: ~40ms × 13 projects = 0.5s per invocation | Low | Acceptable for Phase 1; document `--no-git` fast path as future |
| `has_engram` stub always returns `false` — misleading output | Medium | Document loudly in `--help` text + `# TODO Phase 2` comment in code |
| Astro/Next disambiguation: edge case of `package.json` with both | Low | `astro.config.*` wins over `package.json` substring; documented in code |
| Cross-platform git: POSIX worktree semantics differ from Windows | Low | Phase 1 targets Windows; POSIX not validated |
| Schema additions in future phases require `version` bump | Low | CHANGELOG discipline; additive = minor bump only |

## has_engram Stub

`has_engram` is **always `False` in Phase 1**. This is intentional — Engram (Go backend) is not modified. Phase 2 will replace the stub with a real call to the Engram MCP or API (`engram mem_search --project <name>`).

In code: `# TODO Phase 2: has_engram() → Engram MCP or API call; stub returns False for now`
In `--help`: `(has_engram is a Phase 1 stub; always false — Phase 2 hooks into real Engram backend)`

## Why Not a New Subcommand

`flow projects` already exists at cli.py:2476 with `ls`/`backfill`/`alias` subcommands. Extending `ls` in-place:
- Reuses existing root-resolution logic (`FLOW_PROJECTS_ROOT` env, `C:\dev\proyects` default)
- Smaller blast radius than a parallel command
- Consistent with the existing CLI surface (users already know `flow projects ls`)

## PR Strategy

- **1 PR**, likely 1 commit (small change: ~150 LOC augmentation + ~150 LOC tests)
- Branch: `codex/workspace-intelligence` cut from `flow-engineering` main
- Diff files: `src/flow_engineering/cli.py`, `tests/unit/test_cli_projects.py`
- No chained PR needed (well under 400-line review budget)

## Rollback Plan

Revert the augmentation of `_detect_project_markers()` and remove the `--json` flag from `projects_ls`. The original function + command are preserved in git history.

## Success Criteria

- [ ] `flow projects ls` emits text table with all original columns intact
- [ ] `flow projects ls --json` emits valid v1 JSON envelope with 11 fields per project
- [ ] All 7 new fields populated correctly for each stack type in test fixtures
- [ ] `has_engram` stub returns `false` and is documented in `--help`
- [ ] Tests pass: `pytest tests/unit/test_cli_projects.py -v`
