# Explore: workspace-intelligence

> Phase 1 — NEW CLI subcommand for `flow-engineering` (Python). Scope: `flow projects` + `flow projects --json` only. Engram stays backend; this is orchestration/retrieval.

## 1. Existing flow CLI structure

`src/flow_engineering/cli.py` is a **Click** group (`main`, line 63). Each subcommand is `@main.command()` (or `@main.group(...)` for nested namespaces).

**Critical discovery**: `flow projects` **already exists** as a group at `cli.py:2476` with three subcommands:

- `flow projects ls` (line 2521) — text table of `NAME / TYPE / FLOW / README`. Backed by `_detect_project_markers()` at `cli.py:2488`. Default root: `FLOW_PROJECTS_ROOT` env → `C:\dev\proyects` (Win) / `~/dev/proyects` (POSIX). Type detection: `pyproject.toml` → `python`, `package.json` + `"astro"` → `astro`, `package.json` + `"next"` → `next`, `Cargo.toml` → `rust`, `go.mod` → `go`. No `--json` flag.
- `flow projects backfill` (line 2573) — alias re-tagging (REQ-24/27). Out of scope here.
- `flow projects alias` (line 2747) — rename records. Out of scope here.

**Template pattern** to mirror: `flow where` (`cli.py:380-421`, backed by `src/flow_engineering/where.py:482`). It already exhibits the `_run_*` subprocess seam (`where.py:89`), `monkeypatch`-friendly defaults (`where.py:31`), and ASCII-safe rendering (`where.py:411`).

**Decision point (resolved below)**: Phase 1 extends `flow projects ls` in-place (new fields + `--json` flag) rather than introducing a parallel subcommand — keeps the CLI surface coherent and reuses the existing root-resolution logic.

## 2. Test patterns

- **Framework**: pytest (`pyproject.toml:88-91`, `testpaths = ["tests"]`, `pythonpath = ["src"]`).
- **Layout**: `tests/unit/` for unit, `tests/bdd/` for Given/When/Then features, `tests/integration/` for cross-module.
- **CLI tests**: `Click`'s `CliRunner.invoke(main, [...])`. See `tests/unit/test_cli_projects.py:1-109` — the canonical pattern for this change.
- **Fixtures**: `tmp_path` (pytest built-in) for fake project trees; `monkeypatch.setenv("FLOW_PROJECTS_ROOT", str(root))` to redirect discovery.
- **Subprocess isolation**: `monkeypatch.chdir(tmp_path)` (see `test_where.py:66`). For `git` calls in this change, follow the same pattern + provide a `_run_git` seam that returns canned output for unit tests (mirrors `where._run_search`).
- **TDD discipline**: `pyproject.toml:79-86` pins `min_sdd_skill_versions = sdd-apply = "3.0"`; apply/verify enforce it at startup. Strict TDD per `FLOW.md` + `AGENTS.md` (`C:\Users\insyd\AGENTS.md`).

## 3. File probe catalog by stack

| Stack   | Primary probe                                  | Secondary signals                         | Disambiguation rule |
|---------|------------------------------------------------|-------------------------------------------|---------------------|
| Go      | `go.mod`                                       | `cmd/`, `internal/`, `pkg/`               | none                |
| Python  | `pyproject.toml` (also: `requirements.txt`, `setup.py`, `Pipfile`) | `src/`, `tests/`         | none                |
| Astro   | `astro.config.mjs` OR `astro.config.ts`        | `package.json` + `"astro"` dep            | check BEFORE Next   |
| Next    | `package.json` containing `"next"`             | `app/` or `pages/` dir                    | only if Astro probe absent |
| Flutter | `pubspec.yaml`                                 | `lib/`, `android/`, `ios/`, `web/`        | none                |
| Nix     | `flake.nix` OR `default.nix`                   | `*.nix` files in root                     | none                |
| WXT     | `wxt.config.ts` OR `wxt.config.js`             | `package.json` + `"wxt"` dep              | check after Next    |
| Rust    | `Cargo.toml`                                   | `src/main.rs`, `src/lib.rs`               | none (already supported) |

**Astro vs Next disambiguation**: Both may have `package.json`. The canonical signal is the framework config file (`astro.config.{mjs,ts}` for Astro). Only fall back to `package.json` substring match when no config file is present. Order of evaluation: **Astro config → Next app/pages → package.json substring**.

**Existing detection gap**: `_detect_project_markers()` (cli.py:2488) does not cover Flutter / Nix / WXT. Phase 1 fills the gap by extending the helper (or replacing it with a new `detect_workspace_intel()` in `src/flow_engineering/workspace_intel.py`).

## 4. Test command detection

| Stack   | Detection order (first hit wins)                                       | Default fallback     |
|---------|------------------------------------------------------------------------|----------------------|
| Go      | `Makefile` `test:` target → `go test ./...`                            | `go test ./...`      |
| Python  | `pyproject.toml [tool.pytest.ini_options]` → `Makefile test:` → `pytest.ini` | `uv run pytest`  |
| Astro/Next | `package.json` scripts.test                                           | `npm test`           |
| Flutter | (no project probe)                                                     | `flutter test`       |
| Nix     | skip (test commands are project-specific; emit `[]`)                   | `[]`                 |
| WXT     | `package.json` scripts.test                                            | `npm test`           |

**Implementation note**: For Python, prefer `uv run pytest` when a `uv.lock` is present at root, else `python -m pytest` (PyPI install) or `pytest` (system). Detect `uv.lock` presence as the heuristic.

## 5. OpenSpec / Graphify / Engram detection

- **OpenSpec**: `path / "openspec" / "changes"`. Boolean. (Already proven in `cli.py:2511` via `flow-engineering/` subdir probe — same shape.)
- **Graphify**: `path / "graphify-out" / "graph.json"` (canonical, observed at `C:\dev\proyects\graphify-out\graph.json` AND `C:\dev\proyects\tecnosquire-infra\graphify-out\`). Also accept `graphify-out/graph.html` as a softer signal (boolean OR).
- **Engram**: stub seam. Phase 1 calls a `has_engram_memory(project_name) -> bool` helper that, for now, returns `False` for all projects. The real implementation (Phase 2) will shell out to `engram mem_search` or hit the MCP. Document this as a mockable seam in the design; tests monkeypatch the helper.

## 6. JSON output schema proposal (v1)

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

- `version`: literal `"1"` (string). Bumped on any breaking shape change. Additive changes (new field) → minor bump documented in CHANGELOG.
- `root`: absolute path the user passed (or default).
- `name`: directory basename; `path`: absolute string.
- `has_git`: bool. Probe `path/.git` (dir) OR `path/.git` (file, worktree).
- `branch`: `string | null`. `null` when `!has_git`. Detached HEAD → literal string `"HEAD"`.
- `dirty`: `bool | null`. `null` when `!has_git`.
- `remote`: `string | null`. `git config --get remote.origin.url`. `null` when no remote configured.
- `stack`: enum `Go | Python | Astro | Next | Flutter | Nix | WXT | Rust | Unknown`. `null` if no probe matched (currently emitted as `"Unknown"` for human output, `null` for JSON — pick one and document).
- `test_commands`: `string[]`. Empty array (NOT null) when none detected, except for Nix (`[]`).
- `has_openspec` / `has_graphify` / `has_engram`: bool.
- **Ordering**: projects sorted alphabetically by `name` (matches existing `projects_ls` at `cli.py:2553`).
- **Errors**: per-project detection errors are isolated (`try/except OSError, subprocess.SubprocessError` per project) — one broken project never blanks the output.

## 7. Live project survey (`C:\dev\proyects\`)

| Name                       | Stack    | Git | Branch | openspec | graphify | engram (stub) |
|----------------------------|----------|-----|--------|----------|----------|---------------|
| engram                     | Go       | ✓   | main   | ✓        | ✗        | ✗             |
| flow-engineering           | Python   | ✓   | main   | ✓        | ✗        | ✗             |
| tecnosquire-infra          | Nix      | ✓   | main   | ✗        | ✓        | ✗             |
| Gestor-de-Contrase-as      | Flutter  | ✓   | main   | ✗        | ✗        | ✗             |
| mockup                     | Next     | ✗   | —      | ✗        | ✗        | ✗             |
| mockup-2-blog              | Astro    | ✗   | —      | ✗        | ✗        | ✗             |
| tecnodespegue-landing      | Astro    | ✓   | main   | ✗        | ✗        | ✗             |
| flow-image-generator-main  | Node (?) | ✗   | —      | ✗        | ✗        | ✗             |

(Workspace-root artifacts `.atl`, `.opencode`, `openspec`, `sdd-init`, `graphify-out` are not projects — filtered by `_detect_project_markers()` shape check or by adding `is_real_project()` to skip dotfiles / known artifact dirs.)

## 8. Fixture strategy

Construct fake projects under `tmp_path / projects / <name> /` per stack. Minimal probe set per fixture:

- **Go**: `go.mod` with `module x` line.
- **Python**: `pyproject.toml` with `[project]` table; add `uv.lock` for `uv run pytest` detection.
- **Astro**: `astro.config.mjs` + `package.json` with `"astro"` dep.
- **Next**: `package.json` with `"next"` dep + `app/` dir.
- **Flutter**: `pubspec.yaml` + `lib/main.dart` stub.
- **Nix**: `flake.nix` (any content).
- **WXT**: `wxt.config.ts` + `package.json` with `"wxt"` dep.

Git is mocked via `_run_git(args) -> str` seam (mirrors `where._run_search`). Tests return canned output for `rev-parse`, `status`, `config remote.origin.url`. The seam is monkeypatched per-test; production calls real `git` via `subprocess.run` with timeout=5s.

## 9. Out of scope (restated)

- `flow where` extensions (Phase 2). Engram stays backend.
- `flow workspace status` / `flow workspace tui` / dashboard (Phases 3-5).
- Engram modifications — none. `has_engram` is a stub seam.
- Modifying any project under `C:\dev\proyects\` (cataloging only).
- `%APPDATA%` filesystem touches.

## 10. Risks

- **Subprocess overhead**: `git rev-parse`, `git status`, `git config` per project. With ~13 projects, ~40ms each = 0.5s. Acceptable. Mitigation: cache results within a single `flow projects` invocation; future `--no-git` flag for fast listing.
- **Engram stub**: `has_engram` is always `false` in Phase 1. Document loudly in `--help` so users don't read it as authoritative.
- **Astro/Next disambiguation**: edge case of `package.json` with both `astro` and `next` (rare). Rule: presence of `astro.config.*` wins. Document.
- **File race conditions**: project modified between probe and use — out of scope (caller's responsibility, like `rg` results in `flow where`).
- **Cross-platform**: Windows path handling for `_DEFAULT_PROJECTS_ROOT_WIN` / `_NIX` precedent at `cli.py:69-70` is already there. Git on POSIX may behave differently (line endings, worktree semantics) — not validated in Phase 1; user said Windows.

## 11. Recommended approach (high level)

Extend `flow projects ls` in `cli.py:2521`:

1. Replace/augment `_detect_project_markers()` with `detect_workspace_intel(path) -> dict` (new module `src/flow_engineering/workspace_intel.py`).
2. Add `--json` flag; emit v1 schema via `json.dumps(..., indent=2)` (mirrors `_render_inspect_table` pattern at `cli.py:1078-1096`).
3. Reuse `_DEFAULT_PROJECTS_ROOT_WIN/NIX` and `FLOW_PROJECTS_ROOT` env-var precedence (cli.py:69-70, 2540-2547).
4. ASCII-safe text output (mirror `_ascii_safe` at `where.py:411`).
5. **No new infrastructure**. No new deps. Pure stdlib (`subprocess`, `json`, `pathlib`, `tomllib`).
6. Stack ordering follows the catalog table; first match wins; `Unknown` as fallback.
7. Per-project error isolation: a broken `.git` returns `has_git=false` rather than aborting the whole listing.

PR budget: well under 400 lines (one new module ~150 LOC + one CLI extension ~50 LOC + tests ~150 LOC). No chained PR needed.