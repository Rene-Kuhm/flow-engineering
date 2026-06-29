# Design: workspace-intelligence — Phase 1

> Approach α (augment `_detect_project_markers()` in-place) LOCKED per `proposal.md:31–45`.
> Design read-only; no source files modified. Target branch: `codex/workspace-intelligence`.

## 1. Existing Code Re-Read (Baseline)

Baseline read 2026-06-29 against `src/flow_engineering/cli.py` (3966 LOC).

| Element | Lines | Notes |
|---|---|---|
| `import subprocess` | NOT present | Must add at cli.py:5–11 next to existing stdlib imports (`json`, `os`, `sys`). |
| `_detect_project_markers()` | 2488–2518 (31 LOC) | Returns `dict[str, str \| None]` with 3 keys (`type`, `has_flow`, `readme_first_line`). Pure file probes — no subprocess yet. |
| `projects_group` | 2476–2485 | Click group; docstring lists 3 subcommands. |
| `projects_ls` | 2521–2570 | No `--json` flag. Sorts subdirs via `sorted([p for p in root.iterdir() if p.is_dir()])` (line 2553). Text table via `click.echo`. |
| `--json` flag precedent | 1076, 1120, 1869, 2906, 2952, 3087, 3432, 3596 | All use `@click.option("--json", "json_flag"/"as_json", is_flag=True, default=False)` + `click.echo(json.dumps(payload, ensure_ascii=False, indent=2))`. Closest mirror: `inspect` (cli.py:1074–1096). |
| `_now_iso()` | 1775–1777 | Reusable; returns UTC ISO 8601 with `Z` suffix (`"2026-06-29T16:30:00Z"`). |
| Subprocess seam precedent | `where.py:89 _run_search` | Module-level wrapper around `subprocess.run(capture_output=True, text=True, cwd=...)` with `try/except (OSError, subprocess.SubprocessError)` returning `""`. Mirror for `_git`. |
| Existing test fixture | `tests/unit/test_cli_projects.py:27–49` | `projects_root` fixture uses `tmp_path` + `monkeypatch.setenv("FLOW_PROJECTS_ROOT", ...)`. NO hardcoded `C:\dev\proyects` in tests — preserves portability (spec REQ-CONVENTIONS). |

## 2. Subprocess Seam — `_git()` Module-Level Wrapper

**Insertion point**: immediately above `_detect_project_markers()` at cli.py:2487 (one blank line below the `projects_group` decorator block). Imports `subprocess` added at cli.py:5–11 (after `import os`).

```python
def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run ``git <args>`` and return the CompletedProcess. Stubbable in tests.

    Mirrors ``where._run_search`` (where.py:89): production callers hit
    real ``subprocess.run(...)`` with ``timeout=5s``; tests
    ``monkeypatch.setattr(cli, "_git", fake_git)`` to inject a fake that
    returns predetermined CompletedProcess instances.

    Exit-code contract:
    - 0 → stdout parsed; caller decides field semantics.
    - non-zero → caller treats as "missing"; returns None / False.
    """
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        timeout=5,
    )
```

**Default behavior**: real `subprocess.run([...])`, `timeout=5s`, returns `CompletedProcess(stdout, stderr, returncode)`.
**Test override**: `monkeypatch.setattr(cli, "_git", fake_git)` where `fake_git(*args, **kwargs)` returns `subprocess.CompletedProcess(args=[...], returncode=0, stdout="main\n", stderr="")`.

## 3. Augmentation Strategy — `_detect_project_markers()` BEFORE/AFTER

### Signature Change

```python
# BEFORE: cli.py:2488
def _detect_project_markers(project_dir: Path) -> dict[str, str | None]:

# AFTER: cli.py:2498 (replaces old body)
def _detect_project_markers(project_dir: Path) -> dict[str, Any]:
```

### Field Computation Map

| Field | Source | When present |
|---|---|---|
| `name` | `project_dir.name` | always |
| `path` | `str(project_dir.resolve())` | always |
| `has_git` | `(project_dir/".git").exists()` (dir OR worktree file) | always |
| `branch` | `_git("rev-parse", "--abbrev-ref", "HEAD", cwd=project_dir).stdout` | only when `has_git` |
| `dirty` | `_git("status", "--porcelain", cwd=project_dir).stdout != ""` | only when `has_git` |
| `remote` | `_git("config", "--get", "remote.origin.url", cwd=project_dir).stdout` | only when `has_git` AND returncode == 0 |
| `stack` | file-probe cascade (see explore.md:30–41) | always; "Unknown" fallback |
| `test_commands` | per-stack probe (Makefile/pyproject/package.json) | always; `[]` empty default |
| `has_openspec` | `(project_dir/"openspec"/"changes").is_dir()` | always |
| `has_graphify` | STUB — always `False` (Phase 1) | always |
| `has_engram` | STUB — always `False` (Phase 1) | always |

Per-project error isolation: every field wrapped in `try/except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired)`. A broken `.git` returns `has_git=False`, never aborts the whole listing (spec REQ-FIELD-EXTENSION).

### Stub Triple Enforcement for `has_engram`

1. **Code comment** near the `has_engram` evaluation:
   ```python
   # TODO(workspace-intelligence): Phase 2 — replace stub with Engram MCP/API call.
   # Always returns False; see --help note for user-facing warning.
   out["has_engram"] = False
   ```
2. **`--help` text** appended to `projects_ls` docstring:
   ```
   NOTE: 'has_engram' is currently a stub field and always reports false;
   full Engram integration is planned for a later phase.
   ```
3. **Test enforcement**: `test_flow_projects_ls_has_engram_stub` asserts `False` for every project regardless of fixture (spec REQ-HAS-ENGRAM-STUB).

## 4. `--json` Flag Wiring

`projects_ls` (cli.py:2521) gains one decorator + one branching block:

```python
@projects_group.command(name="ls")
@click.option(
    "--root", type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=None, help="...",
)
@click.option(
    "--json", "json_flag", is_flag=True, default=False,
    help="Emit machine-readable JSON envelope (v1 schema) instead of text table. "
         "NOTE: 'has_engram' is currently a stub field and always reports false; "
         "full Engram integration is planned for a later phase.",
)
def projects_ls(root: Path | None, json_flag: bool) -> None:
    """List sibling projects with type markers + workspace-intel fields (REQ-V0.1).

    <existing docstring preserved>

    With ``--json``, emits a v1 envelope with 11 fields per project. The
    ``has_engram`` field is a Phase 1 stub and always reports false.
    """
    # <root resolution unchanged>
    subdirs = sorted([p for p in root.iterdir() if p.is_dir()])
    if not subdirs:
        click.echo("(no subdirectories under {root})")
        return
    if json_flag:
        projects = sorted(
            (_detect_project_markers(p) for p in subdirs),
            key=lambda d: d["name"],
        )
        envelope = {
            "version": "1",
            "root": str(root),
            "projects": projects,
        }
        click.echo(json.dumps(envelope, ensure_ascii=False, indent=2))
        return
    # <existing text-table rendering preserved verbatim>
```

`projects_ls` docstring appends the has_engram stub note (REQ-HAS-ENGRAM-STUB AC5).

## 5. JSON Envelope Assembly

Top-level key order is enforced by **CPython 3.7+ dict insertion order** (preserved by `json.dumps`):

```python
envelope = {
    "version": "1",          # FIRST key — semver discipline (REQ-SCHEMA-VERSIONING)
    "root": str(root),       # absolute path; from --root, env, or platform default
    "projects": [...],       # list of 11-key dicts, sorted by "name" ascending
}
```

- `version` is string `"1"` (not int) — preserves SemVer compatibility (`1.1`, `2.0`).
- `projects` sorted by `name` case-sensitive ascending (matches existing `subdirs = sorted(...)` at cli.py:2553).
- Per-project detection errors isolated (spec REQ-FIELD-EXTENSION).

## 6. Test Fixture Strategy

All fixtures use `tmp_path` exclusively. **NO hardcoded `C:\dev\proyects`** (spec REQ-CONVENTIONS).

### Helper Functions (in `tests/unit/test_cli_projects.py`)

| Helper | Creates |
|---|---|
| `make_fake_go_project(tmp_path)` | `go.mod` (`module x\n`) + `.git/` dir |
| `make_fake_python_project(tmp_path)` | `pyproject.toml` + `Makefile` with `test:` target |
| `make_fake_flutter_project(tmp_path)` | `pubspec.yaml` |
| `make_fake_nix_project(tmp_path)` | `flake.nix` (any content) |
| `make_fake_astro_project(tmp_path)` | `astro.config.mjs` + `package.json` with `"astro"` dep |
| `make_fake_next_project(tmp_path)` | `package.json` with `"next"` dep + `app/` dir |
| `make_fake_wxt_project(tmp_path)` | `wxt.config.ts` |
| `make_fake_no_git_project(tmp_path)` | `pyproject.toml` only (no `.git`) |
| `make_fake_dirty_project(tmp_path)` | `.git/` + uncommitted file `M foo.txt` |
| `make_fake_openspec_project(tmp_path)` | `openspec/changes/` dir (empty or with subdir) |

### Test Override Pattern

```python
def fake_git(*args: str, **kwargs: Any) -> subprocess.CompletedProcess:
    if args and args[0] == "rev-parse":
        return subprocess.CompletedProcess(args=[...], returncode=0, stdout="main\n", stderr="")
    if args and args[0] == "status" and "--porcelain" in args:
        return subprocess.CompletedProcess(args=[...], returncode=0, stdout=" M foo\n", stderr="")
    return subprocess.CompletedProcess(args=[...], returncode=128, stdout="", stderr="not a git repo")

monkeypatch.setattr(cli, "_git", fake_git)
```

### Assertion Pattern (Click + JSON)

```python
result = runner.invoke(
    main, ["projects", "ls", "--json"],
    env={"FLOW_PROJECTS_ROOT": str(root)},
)
assert result.exit_code == 0, result.output
payload = json.loads(result.output)
assert payload["version"] == "1"
assert payload["projects"][0]["name"] == "a"  # sorted
```

## 7. Test List (9 new unit tests, AC10 budget)

| # | Test | Verifies |
|---|---|---|
| 1 | `test_flow_projects_ls_branch_with_git` | Go project + git → `branch == "main"` (uses `_git` seam) |
| 2 | `test_flow_projects_ls_dirty_clean` | Go project clean vs uncommitted → `dirty` boolean |
| 3 | `test_flow_projects_ls_remote_present` | Go project + `origin` URL → `remote` string |
| 4 | `test_flow_projects_ls_remote_absent` | No remote → `remote is None` |
| 5 | `test_flow_projects_ls_test_commands_python_pytest` | Python + `Makefile test:` → `["make test"]` |
| 6 | `test_flow_projects_ls_has_openspec` | Project with `openspec/changes/` → `has_openspec is True` |
| 7 | `test_flow_projects_ls_has_engram_stub` | Always `False` regardless of truth (stub enforcement) |
| 8 | `test_flow_projects_ls_json_deterministic_order` | 3 projects named a/c/b → sorted to a/b/c |
| 9 | `test_flow_projects_ls_json_version_field_first` | `version` key first in serialized JSON |

Total: 9 (under spec AC10 budget). Plus 4 existing tests preserved (regression baseline).

## 8. Commit Strategy

- **Branch**: `codex/workspace-intelligence` cut from `main`
- **Commits**: 1 (work unit = "extend `flow projects ls` with workspace intel"). Optionally split into 2 work-unit commits (T1 = `_git` seam + augmentation; T2 = `--json` flag + JSON tests) — both fit in 1 PR under the 400-line budget.
- **Message**: `feat(cli): extend flow projects ls with --json + 7 new detection fields`
- **Files in diff**: `src/flow_engineering/cli.py`, `tests/unit/test_cli_projects.py`
- **Scope**: ~120 LOC production + ~180 LOC tests = ~300 LOC total. Fits 400-line review budget with margin.

## 9. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| `_detect_project_markers()` grows beyond 80 LOC — α becomes wrong choice | Low | proposal.md:91 refactor trigger documented; if > 80 LOC during apply, extract `_detect_workspace_intel()` (β) |
| Subprocess overhead: ~40ms × 13 projects × 3 git calls = ~0.5s per invocation | Low | Acceptable; future `--no-git` fast path documented (explore.md:144) |
| `has_engram` stub misleading in output | Medium | Triple enforcement: TODO comment + `--help` note + test (REQs 3+5+9) |
| Astro/Next disambiguation (`package.json` with both) | Low | `astro.config.{mjs,ts}` wins over substring; explore.md:39–41 |
| Schema versioning discipline (additive bumps) | Low | Semver comment in design; CHANGELOG entry on apply |
| `_git` seam must apply to ALL git calls in `_detect_project_markers` | Medium | Reviewer checklist: `grep "subprocess.run.*git"` in cli.py returns empty inside the function — all routes via `_git` |
| CPython dict ordering assumption for `version` first key | Low | CPython 3.7+ guarantees insertion order; spec mandates `version` first key in serialized output (REQ-SCHEMA-VERSIONING) |
| `_run_search` seam does NOT have timeout — `_git` adds `timeout=5s` (diverges from precedent) | Low | Justified: git calls have higher hang risk than `rg`; precedent is non-blocking `""` return; `_git` returns `CompletedProcess` with non-zero returncode so caller can decide. Documented. |

## 10. Out-of-Scope Restated (Phase 2-5)

- `flow where` cross-project retrieval — Phase 2.
- `flow workspace status` / `flow workspace tui` / dashboard — Phases 3-5.
- Real Engram backend integration — Phase 2; `has_engram` is Phase 1 stub only.
- Other projects under `<root>` (`mockup`, `mockup-2-blog`, `tecnosquire-infra`, `Gestor-de-Contrase-as`, `tecnodespegue-landing`, `flow-image-generator-main`) — read-only detection targets.
- `%APPDATA%` filesystem — never touched.
- New top-level subcommand (no `flow intelligence`, no `flow workspace list`) — extends `flow projects ls` only.

## Next Step

`sdd-tasks`: produce 6 implementation tasks — T1 `import subprocess` + `_git` seam; T2 augment `_detect_project_markers()` (stack + git fields + test_commands); T3 add `--json` flag + JSON envelope assembly + has_engram stub note in `--help`; T4 add `# TODO(workspace-intelligence): Phase 2` comment near `has_engram`; T5 fixture helpers + 9 new unit tests (RED → GREEN → REFACTOR); T6 verification (`pytest tests/unit/test_cli_projects.py -v`).