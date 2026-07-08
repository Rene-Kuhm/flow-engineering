# Status: workspace-intelligence — ARCHIVED

> **Change**: `workspace-intelligence` (Phase 1)
> **Domain**: `flow projects ls` extension in `flow-engineering`
> **Branch**: `codex/workspace-intelligence` (preserved; awaiting user push/merge authorization)
> **Merged**: NO — local-only on `codex/workspace-intelligence`
> **Archive date**: 2026-06-29

---

## Outcome

**Status**: ✅ ARCHIVED
**Approach**: α — augment `_detect_project_markers()` in-place + extend `projects_ls` with `--json` flag (LOCKED in design #439).

## Commits (4 total on `codex/workspace-intelligence`)

| SHA | Category | Subject |
|---|---|---|
| `ebfd0d9` | production | `feat(cli): extend flow projects ls with --json + 7 new detection fields` |
| `0a7fc28` | tests | `test(cli): add 9 new unit tests + 10 fixture helpers for workspace-intelligence` |
| `7aa8a53` | AC8 fix (prod + test) | `fix(cli): drop generated_at from JSON envelope to restore AC8 byte-determinism` |
| `aee130f` | docs drift fix | `docs(workspace-intelligence): remove generated_at from proposal/explore/tasks` |

The original 2-commit compact-B strategy (#440) was extended with 2 follow-up commits: `7aa8a53` resolved the AC8 byte-determinism regression in production; `aee130f` closed the documentation drift on the openspec artifacts so all canonical sources of truth are consistent.

## User Requirements Satisfied (4/4)

| REQ | Description | Status |
|---|---|---|
| `--json` flag | `flow projects ls --json` emits one valid JSON envelope | ✅ |
| 7 fields | `branch`, `dirty`, `remote`, `test_commands`, `has_openspec`, `has_graphify`, `has_engram` (stub) | ✅ |
| `has_engram` stub | Always `false` in Phase 1; triple-enforced (TODO + `--help` + test) | ✅ |
| Schema versioning | `version: "1"` positioned as FIRST key of envelope | ✅ |

The 4 legacy fields (`name`, `path`, `has_git`, `type`) are preserved for back-compat with the existing text-table regression test, totaling 11 fields per project in the v1 JSON schema.

## BDD Scenarios (7/7 PASS) and Acceptance Criteria (10/10)

All 7 BDD scenarios from spec #438 pass:
1. `--json` emits stable JSON envelope (keys order: `version`, `root`, `projects`)
2. `--json` absent preserves existing text output
3. 11-field Go project with git
4. 11-field Python project with pytest (`uv run pytest` vs `python -m pytest` based on `uv.lock`)
5. `has_engram` stub remains `false` even when Engram has entries
6. Schema `version` field present and first
7. `projects` array sorted by name (case-sensitive ascending)

All 10 acceptance criteria from spec #138 are satisfied. See spec #438 for the full AC list.

## Final Verification (post-docs-drift-fix commit)

**Test suite**: `uv run pytest tests/unit/test_cli_projects.py -v` → **14/14 pass** in 0.85s.
- 4 baseline tests (regression — text-table + custom-root + readme + default-root)
- 9 new unit tests from Phase 1 (branch + dirty + remote + test-commands + openspec + engram-stub + json-order + json-version + byte-identical)
- 1 new regression test from AC8 fix (`test_flow_projects_ls_json_byte_identical_envelope`)

**Live byte-identical smoke test**: 2 consecutive `uv run flow projects ls --json` invocations on the real `<root>` produced 6008 bytes each, byte-for-byte identical (case-sensitive comparison). AC8 byte-determinism verified live.

**Reviewer checks (6/6 PASS)**:
1. `git grep -n 'subprocess.run' src/flow_engineering/cli.py` — only `_git` seam definition (line 2491 docstring comment + line 2508 seam body). ✓
2. `git grep -n 'subprocess.run' inside _detect_project_markers function body` — empty. All 3 git calls (rev-parse + status + config) route through the `_git()` seam. ✓
3. `git grep -n 'C:\\dev\\proyets' tests/ src/ openspec/` — empty. NO hardcoded root in any in-scope file. ✓
4. `git grep -n 'has_engram' src/flow_engineering/cli.py` — triple-enforcement: TODO comment (line 2631) + stub=False (line 2636) + `--json` help text (line 2664) + `projects_ls` docstring note (line 2677). ✓
5. `git grep -n 'generated_at' src/ openspec/` — empty (drift fully resolved by `aee130f`). Two explanatory comments in `tests/unit/test_cli_projects.py` (lines 441, 475) document WHY the field was removed — acceptable per spec intent, not functional references. ✓
6. `_detect_project_markers()` body 63 LOC < 80 LOC budget (design #439 §9). ✓

**AC8 fix verification**: `generated_at` removed from production code (`src/flow_engineering/cli.py`) — verified via `git grep -n 'generated_at' src/` returning 0 matches. New regression test `test_flow_projects_ls_json_byte_identical_envelope` guards against accidental re-introduction. AC8 violation RESOLVED.

## Code Diff Footprint

Total diff (vs main, across 4 commits):

| File | Insertions | Deletions |
|---|---|---|
| `src/flow_engineering/cli.py` | +217 | -27 (net ≈ 190 LOC production) |
| `tests/unit/test_cli_projects.py` | +374 | (net ≈ 374 LOC test) |
| `openspec/changes/workspace-intelligence/*` (drift fix in `aee130f`) | +855 | (all new in this commit) |

## Scope Budget

- **Original estimate** (tasks #440): ~300 LOC (under 400-line review budget at the time)
- **Actual**: ~543 net LOC across production + tests (does NOT fit the original 400-line budget)
- **Exception status**: `size:exception accepted by user 2026-06-29`. The budget overrun is attributable to:
  - The 9 new fixture helpers in commit `0a7fc28` (~80 LOC of fixture glue)
  - The byte-identical regression test in commit `7aa8a53` (~50 LOC)
  - The 5 openspec artifacts in commit `aee130f` (~855 LOC of documentation)
- **Decision**: no chained PR — the user's directive was to ship as a single branch and revisit only if Phase 2 mirrors it.

## Out-of-Scope (restated, never touched)

- `flow where` cross-project retrieval — Phase 2
- `flow workspace status` / TUI / dashboard — Phases 3, 5
- Real Engram backend integration — Phase 2; `has_engram` remains a stub seam
- Engram (Go project) — NOT modified
- Other projects under `<root>` (`mockup`, `mockup-2-blog`, `tecnosquire-infra`, `Gestor-de-Contrase-as`, `tecnodespegue-landing`, `flow-image-generator-main`) — read-only detection targets
- `%APPDATA%` filesystem — never touched
- New top-level subcommand — extends only

## Pre-Existing Residuals (NOT in this change's scope)

- `TestUnconfiguredCloudKeepsLocalCommandDefaults` in `cmd/engram` — already closed in a prior change; this is a different test file (`cmd/engram`), NOT in `flow-engineering/` and outside the workspace-intelligence scope. No action required.

## Cross-References (Engram topic → observation id)

- explore → `#436`
- proposal → `#437`
- spec → `#438`
- design → `#439`
- tasks → `#440`
- apply-progress → `#441`
- verify-report → `#442` (updated by AC8 fix re-run)
- apply-progress-fix → `#443`
- archive-report → `#444`

## Branch State

- **Branch**: `codex/workspace-intelligence`
- **Ahead of main**: 4 commits (`ebfd0d9`, `0a7fc28`, `7aa8a53`, `aee130f`)
- **Working tree**: clean
- **Merge status**: NOT merged to `main`; awaiting user decision
- **Push status**: NOT pushed; awaiting user authorization

## Next Steps (decisions pending)

- **Push decision**: user to decide push strategy — either `git push fork codex/workspace-intelligence` to retain the branch on a remote fork, or local-only retention.
- **Merge decision**: user to decide whether to merge to `main` directly or via a stacked PR chain when Phase 2 launches.
- **Phase 2 kickoff (optional)**: `flow where` cross-project retrieval may re-introduce `generated_at` behind an opt-in flag (`--json --with-timestamps`); the byte-identical test in `test_flow_projects_ls_json_byte_identical_envelope` will guard against accidental re-introduction in default mode.

## Audit Trail

All 4 commits are signed off with conventional-commit messages and reference the workspace-intelligence scope. No secret-bearing strings, no user-specific paths, no temp paths, no backup timestamps. Status file conforms to the workspace-intelligence spec convention of `<root>` placeholders for filesystem references.
