# Tasks: workspace-intelligence — Phase 1

> Branch `codex/workspace-intelligence` from `main`. Target: `flow-engineering` (Python). Approach α (augment in-place) LOCKED. TDD: **compact B** — prod first (Commit 1), tests second (Commit 2).

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | ~300 |
| 400-line budget risk | Low |
| Chained PRs | No (single PR, 2 commits by user design) |
| Chain strategy | N/A |
| Delivery strategy | ask-always |
| Decision needed before apply | No |
| Total task count | 6 (Commit 1: 4; Commit 2: 1+1 gate) |
| TDD signal shape | compact B |

```
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: N/A
400-line budget risk: Low
```

## Preconditions

Clean tree on `codex/workspace-intelligence`; apply uses `Edit` (no rewrites). Tests `tmp_path`-only — NO hardcoded `C:\dev\proyects`. All git calls route through `_git()` module-level seam. `has_engram` Phase 1 stub (always `false`); triple-enforced: TODO + `--help` + test. Phase 2-5 out-of-scope.

## Per-task Summary

| Task | Commit | File | LOC | TDD signal |
|---|---|---|---|---|
| T-1 | 1 | cli.py | ~10 | compact B |
| T-2 | 1 | cli.py | ~60 | compact B |
| T-3 | 1 | cli.py | ~40 | compact B |
| T-4 | 1 | cli.py | ~10 | compact B |
| T-5 | 2 | test file | ~180 | RED→GREEN (4+9=13) |
| T-6 | (gate) | (verify) | 0 | gates pass |

Commit 1: ~120 LOC prod. Commit 2: ~180 LOC test. Total ~300 LOC. Fits 400 budget.

## Tasks

### T-1: `_git` subprocess seam
- **task_id**: T-1 | **commit_number**: 1 | **pr_number**: 1
- **title**: Add `import subprocess` + `_git` module-level seam
- **red_evidence**: N/A (compact B pre-state)
- **green_change**: Add `import subprocess` (cli.py:5-11). Add `_git(*args, cwd=None) -> subprocess.CompletedProcess` above `_detect_project_markers()` (~line 2487). Wraps `subprocess.run(['git',*args], capture_output=True, text=True, encoding='utf-8', cwd=..., check=False, timeout=5)`. Doc mirrors `where._run_search` (where.py:89).
- **refactor_step**: N/A
- **commit_message**: `feat(cli): add _git subprocess seam for workspace-intelligence testability`
- **ci_gates**: `python -c "from flow_engineering.cli import _git"` imports.
- **rollback_cmd**: `git revert HEAD -- src/flow_engineering/cli.py`
- **depends_on**: — | **estimated_loc**: 10

### T-2: Augment `_detect_project_markers()` → 11 fields
- **task_id**: T-2 | **commit_number**: 1 | **pr_number**: 1
- **title**: Augment `_detect_project_markers()` to 11 fields
- **red_evidence**: N/A (compact B)
- **green_change**: Return `dict[str, Any]` with 11 keys: `name`, `path`, `has_git`, `branch` (`_git('rev-parse','--abbrev-ref','HEAD')`), `dirty` (`_git('status','--porcelain')`), `remote` (`_git('config','--get','remote.origin.url')`), `stack` (9-stack cascade), `test_commands` (Makefile/pyproject/package.json per-stack), `has_openspec`, `has_graphify` (STUB), `has_engram` (STUB). All git via `_git()`; per-project `try/except` isolation. Existing `type/has_flow/readme_first_line` preserved.
- **refactor_step**: If body > 80 LOC, extract `_detect_workspace_intel()` (β).
- **commit_message**: `feat(cli): augment _detect_project_markers() with 8 new detection fields`
- **ci_gates**: `git grep -n 'subprocess.run' src/flow_engineering/cli.py` shows only `_git()`; no direct git call inside `_detect_project_markers`.
- **rollback_cmd**: `git revert HEAD -- src/flow_engineering/cli.py`
- **depends_on**: T-1 | **estimated_loc**: 60

### T-3: `--json` flag + JSON envelope
- **task_id**: T-3 | **commit_number**: 1 | **pr_number**: 1
- **title**: Add `--json` flag + JSON envelope assembly
- **red_evidence**: N/A (compact B)
- **green_change**: Add `@click.option('--json','json_flag', is_flag=True, default=False)` to `projects_ls` (cli.py:2521). Branch on `json_flag`: build `{"version":"1","root":str(root),"projects":sorted(...)}`; emit `click.echo(json.dumps(..., ensure_ascii=False, indent=2))`. When `False`, retain text-table verbatim.
- **refactor_step**: N/A
- **commit_message**: `feat(cli): add --json flag + JSON envelope assembly to projects_ls`
- **ci_gates**: `flow projects ls --json` parses via `json.loads()`; text-table regression test passes.
- **rollback_cmd**: `git revert HEAD -- src/flow_engineering/cli.py`
- **depends_on**: T-2 | **estimated_loc**: 40

### T-4: `has_engram` stub triple-enforcement
- **task_id**: T-4 | **commit_number**: 1 | **pr_number**: 1
- **title**: `has_engram` stub triple-enforcement
- **red_evidence**: N/A (compact B)
- **green_change**: Add `# TODO(workspace-intelligence): Phase 2 — replace stub with Engram MCP/API call. Always returns False; see --help note.` near `has_engram = False`. Append stub note to `projects_ls` docstring AND `--json` `help=`: `NOTE: 'has_engram' is currently a stub field and always reports false; full Engram integration is planned for a later phase.`
- **refactor_step**: N/A
- **commit_message**: `feat(cli): add has_engram stub triple-enforcement (TODO + --help + test)`
- **ci_gates**: `git grep 'TODO(workspace-intelligence): Phase 2' src/flow_engineering/cli.py` ≥ 1 hit; `flow projects ls --help` contains stub note.
- **rollback_cmd**: `git revert HEAD -- src/flow_engineering/cli.py`
- **depends_on**: T-2 | **estimated_loc**: 10

### T-5: 10 fixtures + 9 new tests
- **task_id**: T-5 | **commit_number**: 2 | **pr_number**: 1
- **title**: Add 10 fixture helpers + 9 new unit tests
- **red_evidence**: Pre-Commit-2 — 4 existing pass, 9 new fail.
- **green_change**: Add 10 helpers (`make_fake_go_project`, `_python_project`, `_flutter_project`, `_nix_project`, `_astro_project`, `_next_project`, `_wxt_project`, `_no_git_project`, `_dirty_project`, `_openspec_project`) — all `tmp_path`-based. Add 9 tests: `_branch_with_git`, `_dirty_clean`, `_remote_present`, `_remote_absent`, `_test_commands_python_pytest`, `_has_openspec`, `_has_engram_stub`, `_json_deterministic_order`, `_json_version_field_first`. `CliRunner.invoke()` + `env={'FLOW_PROJECTS_ROOT': str(root)}` + `monkeypatch.setattr(cli, '_git', fake_git)`. Preserve 4 existing tests.
- **refactor_step**: Consolidate fixtures if duplication > 10 LOC.
- **commit_message**: `test(cli): add 9 new unit tests + 10 fixture helpers for workspace-intelligence`
- **ci_gates**: `uv run pytest tests/unit/test_cli_projects.py -v` → 13/13 pass.
- **rollback_cmd**: `git revert HEAD -- tests/unit/test_cli_projects.py`
- **depends_on**: T-1..T-4 | **estimated_loc**: 180

### T-6: Verification gates (no commit)
- **task_id**: T-6 | **commit_number**: (gate) | **pr_number**: 1
- **title**: Verification gates
- **red_evidence**: N/A | **green_change**: N/A (read-only) | **refactor_step**: N/A
- **commit_message**: N/A | **ci_gates**: see `## Verification gates (T-6)`
- **rollback_cmd**: N/A
- **depends_on**: T-1..T-5 | **estimated_loc**: 0

## Cross-task Risks

- `_detect_project_markers()` > 80 LOC → β refactor (low; design #439).
- `_git` seam MUST apply to ALL git calls — reviewer: `git grep -n 'subprocess.run' src/flow_engineering/cli.py` after Commit 1 shows only seam definition; inside `_detect_project_markers` empty.
- Subprocess overhead ~0.5s for 13 projects × 3 git calls (acceptable; future `--no-git`).
- `has_engram` stub misleading → triple-enforced.
- Astro/Next disambiguation: `astro.config.{mjs,ts}` wins over `package.json` substring.
- CPython 3.7+ dict insertion order for `version` first key.
- `monkeypatch.setattr(cli, '_git', fake_git)` requires module-level `_git` (T-1 mitigates).

## Implementation Order (2-commit)

**Commit 1** (production):
```
git add src/flow_engineering/cli.py
git commit -m "feat(cli): extend flow projects ls with --json + 7 new detection fields

- add _git() subprocess seam for testability
- augment _detect_project_markers() with branch, dirty, remote,
  test_commands, has_openspec, has_graphify, has_engram (stub)
- add --json flag + JSON envelope (version first key)
- has_engram stub triple-enforcement (TODO + --help + test)"
```

**Commit 2** (tests):
```
git add tests/unit/test_cli_projects.py
git commit -m "test(cli): add 9 new unit tests + 10 fixture helpers for workspace-intelligence"
```

## Verification gates (T-6)

1. `uv run pytest tests/unit/test_cli_projects.py -v` → 13/13 pass.
2. `git grep -n 'subprocess.run' src/flow_engineering/cli.py` — only `_git` seam definition.
3. `git grep -n 'C:\\dev\\proyects' tests/` — empty.
4. `has_engram` always `False` across all test scenarios.
5. `--json` output deterministic across 2 invocations.
6. `version: "1"` is the first key in the JSON envelope.

## Out-of-Scope (restated)

- `flow where` (Phase 2); `flow workspace status` (Phase 3); TUI/dashboard (Phase 5).
- Real Engram backend; other projects under `<root>` (read-only); `%APPDATA%`; new subcommand.