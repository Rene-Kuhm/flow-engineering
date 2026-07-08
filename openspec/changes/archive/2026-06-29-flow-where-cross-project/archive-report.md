# Archive Report — `flow-where-cross-project`

> **Change**: `flow-where-cross-project` — Phase 2 of the workspace-intelligence effort. Cross-project search for `flow where` across 6 prospec directories per project.
> **Project**: `flow-engineering`
> **Status**: **ARCHIVED (DONE — ship-via-prior-merge, archive-orphaned cleanup)** — 2026-07-08 (archive cleanup phase; status.md originally marked 2026-06-29).
> **Archive destination**: `openspec/changes/archive/2026-06-29-flow-where-cross-project/`.
> **Mode**: openspec (filesystem move only — no delta-spec sync needed; the original change directory contained only `status.md`, all full delta artifacts were re-introduced via the `flow-where-cross-project-capability-merge` follow-up and archived separately).

## 0. ⚠️ HONEST CORRECTION: Feature IS in `main`

> The user's input claimed: *"The feature `flow where` cross-project search is NOT in `main` (verified: `where.py` only has T1.2, T1.4 baseline search of `["src", "tests"]` + `["openspec/changes/archive"]`, no cross-project traversal)"*.

**This claim is INCORRECT.** Verified via `grep "cross.project|cross_project|prospec" src/flow_engineering/cli/__init__.py` and git log inspection:

- **Merge commit**: `001651b Merge branch 'codex/flow-where-cross-project' into main` (2026-06-29) — explicitly merges the cross-project search into `main`. The merge body states: *"Phase 2 of workspace-intelligence. Adds cross-project search to flow where subcommand."*
- **Feat commit on the branch**: `c421540 feat(where): add cross-project search with --format + 6-dir prospec + --regex/--engram` — added 402 LOC in `src/flow_engineering/cli.py` + 295 LOC in `tests/unit/test_cli_where_cross_project.py`.
- **Live production code**: `src/flow_engineering/cli/__init__.py:434+` contains the Phase 2 dispatcher (`# ---------- Phase 2: flow-where-cross-project (REQ-CROSS-PROJECT-SCOPE) ----------`), `_search_projects_for_query`, `_parse_cross_project`, `_resolve_cross_project_root`, and the cross-project formatters.
- **Cap-merge follow-up**: `780285f Merge branch 'codex/flow-where-cross-project-capability-merge' into main` (2026-06-30) — integrated the Phase 2 delta spec into the `flow-where` root capability as 6 REQ-WHERE-* root REQs. Commit body explicitly states: *"Zero code changes. AC9 byte-identical guard preserved (1513/1513 suite)."*

**Why the user missed this**: the cross-project CLI wrapper lives in `cli/__init__.py` (the Click-group stub), NOT in `where.py` (the module API). The design was deliberately additive: `where.py` module API stays untouched per the spec, and the cross-project path is implemented as a CLI-level dispatcher in `cli/__init__.py`. The user only inspected `where.py`.

**Implication for the user's close-out decision**: the framing as *"close-as-superseded"* (with revival path as a future v2 SDD change) is **not the most accurate framing**. The correct framing is:

> **Decision**: **archive-with-revival-path** (close-as-archive-orphan, NOT close-as-superseded). The feature shipped to `main` via `001651b` and was integrated into the root capability spec via `780285f`. The original change directory was left behind as an archive orphan. The remaining relocation work (moving the cross-project handler from `cli/__init__.py` to a domain submodule in the v1.3-cli-split style) is a v1.3-follow-up, not a feature-revival effort.

This revised framing preserves the user's revival-path intent (a v2 SDD change may be needed if the cross-project code is to be cleanly relocated) while being honest about the actual ship state.

## 1. Final Verdict

**`DONE — feature shipped to `main` via `001651b` (2026-06-29); root-spec integration via `780285f` (2026-06-30); archive-orphan cleanup via `git mv` (2026-07-08, this commit); SDD cycle complete.`**

| Metric | Result |
|---|---|
| Strategy | Feature branch `codex/flow-where-cross-project` (2 commits) → merged to `main` via `001651b` → followed by spec-integration branch `codex/flow-where-cross-project-capability-merge` (zero-code-changes) → merged via `780285f` |
| Original feature commit | `c421540 feat(where): add cross-project search with --format + 6-dir prospec + --regex/--engram` (+402 production, +295 test) |
| Original archive status commit | `d223516 chore(archive): add flow-where-cross-project status` (+45 status.md) |
| Branch state at status.md time | 2 commits ahead of merge target |
| Cap-merge integration commit | `6e21d4d docs(specs): integrate Phase 2 cross-project into flow-where root` (+103 lines net to `openspec/specs/flow-where/spec.md`) |
| Cap-merge archive commit | `8d51c5f chore(archive): close out flow-where-cross-project-capability-merge change artifacts` (full delta spec archived at `archive/2026-06-30-flow-where-cross-project-capability-merge/`) |
| Status reported on | 2026-06-29 |
| Actual archive move | 2026-07-08 (this commit) |
| Feature in `main` | ✅ — `src/flow_engineering/cli/__init__.py:434+` (Phase 2 dispatcher) |
| Feature parity verified | ✅ — see §3 |
| Test parity | ✅ — `tests/unit/test_cli_where_cross_project.py` (295 LOC) preserved on `main` |
| v1.3-cli-split relocation impact | The cross-project handler was NOT yet relocated by v1.3-cli-split (Slice 2/8 only relocated the `workspace` group, Slice 3/8 only relocated the `projects` group); the cross-project path still lives in `cli/__init__.py` post-v1.3 |
| Findings | 0 CRITICAL + 0 WARNING + 1 NOTE (this report corrects the user's verification; see §0) |
| Archive readiness | READY — change folder moved to archive; status.md preserved as audit trail |

## 2. Change Summary

### 2.1 Identity

| Field | Value |
|---|---|
| Change name | `flow-where-cross-project` |
| Cycle | Full SDD (explore → propose → spec → design → tasks → apply × 1 feat commit → verify × 9 gates → merge → archive) |
| Branch | `codex/flow-where-cross-project` — merged via `001651b`; branch STILL present locally (user has explicit precedent of deferred branch cleanup — see §5) |
| Spec path | None in the original change dir (only `status.md` was present at archive time); full delta spec recovered + archived by the `capability-merge` follow-up at `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` |
| Final main HEAD at merge | `001651b` |
| Current main HEAD | `9228289` (post-PR #41 v1.3-cli-split integration) |

### 2.2 Goal (per status.md)

Adds a `flow where <query> --root PATH [--format {text,json,tsv}] [--regex] [--engram] [--limit N]` cross-project search across 6 prospec directories (`src/`, `internal/`, `cmd/`, `tests/`, `openspec/`, `graphify-out/`) per project under `--root`. Additive to existing `where_cmd` (preserves `--limit`, `--no-graph`, `--pretty`). Reuses existing `_run_search` from `where.py` (read-only on `where.py` module API).

### 2.3 What Shipped (verified live)

From `status.md` §"Final verification verdict" + live verification of `cli/__init__.py`:

- ✅ 9 of 9 verification gates PASS (per verify-report #460 referenced in status.md; archived in capability-merge archive).
- ✅ 10 new unit tests + 14 prior Phase 1 tests + 10 Phase 3 tests pass (AC9 byte-identical test included).
- ✅ 1235 of 1235 unit tests pass in `tests/unit/` at merge time.
- ✅ 3 output formats work (text default, json envelope, tsv).
- ✅ 6 search directories used (prospec).
- ✅ Exit codes: 0=match-or-empty, 1=no-match, 2=error.
- ✅ `--engram` stub accepted (no behavior change in v1).
- ✅ AC9 byte-identical contract preserved — Phase 1 (`test_cli_projects.py`) + Phase 3 (`test_cli_workspace_status.py`) + `test_where` (25 tests) unaffected.

## 3. Feature Parity Verification

User requirement: verify the cross-project `flow where` feature is present in main.

| Spec Element | Production Location (current `main`) | Verification |
|---|---|---|
| Phase 2 dispatcher comment | `cli/__init__.py:434` | `# ---------- Phase 2: flow-where-cross-project (REQ-CROSS-PROJECT-SCOPE) ----------` ✅ |
| Per-project search directories | `cli/__init__.py:437` (prospec dirs list) | ✅ |
| Default limit bump | `cli/__init__.py:447` (bumped from 20 to N-projects scale) | ✅ |
| `_search_projects_for_query` | `cli/__init__.py:476+` | ✅ |
| Per-directory `_run_search` calls (fail-open on rc=2) | `cli/__init__.py:499+` | ✅ |
| `_parse_cross_project` (custom parser; doesn't use `where._parse_hits` due to colon-splitting issue) | `cli/__init__.py:551+` | ✅ |
| `_resolve_cross_project_root` | `cli/__init__.py:706+` | ✅ |
| `where_cmd` handler (Phase 2 dispatch) | `cli/__init__.py:779+` | ✅ |
| `--root`, `--format`, `--regex`, `--engram`, `--limit` options | `cli/__init__.py:779-822+` | ✅ |
| AC9 byte-identical guard (Phase 1 + Phase 3 tests unaffected) | verified at merge; preserved through v1.3 relocations | ✅ |
| Test file | `tests/unit/test_cli_where_cross_project.py` (295 LOC) | ✅ |
| Shared fixtures | `tests/unit/_workspace_fixtures.py` (Phase 3, unchanged) | ✅ |

**No production-code modifications were made by this archive commit.** The archive phase is documentation-only: `git mv` of the directory + this report.

### 3.1 Honest Assessment of the Branch State

The user's prompt characterized the branch as "STALE" with "its diff vs current `main` shows it DELETES the v1.3-cli-split work (because v1.3-cli-split didn't exist when the branch was created)".

Verified via `git rev-list --count codex/flow-where-cross-project ^main` → **0**. The branch tip `d223516` (the chore-archive commit adding `status.md`) is reachable from main, meaning the branch is NOT ahead of main. The branch was already merged at `001651b` and the merge commit + all subsequent work is on main.

The "DELETES the v1.3-cli-split work" framing would apply if you tried to `git rebase` the branch onto current main and then `diff` the result, but that's a hypothetical — the branch was merged cleanly via merge-commit, so the v1.3-cli-split work and the cross-project work coexist on main without conflict.

The actual situation:
- Branch `codex/flow-where-cross-project` = `d223516` = 2 commits (`c421540` feat + `d223516` chore)
- `c421540` is reachable from `001651b` (merge commit) which is an ancestor of `main @ 9228289`
- Therefore the branch is "merged and abandoned" — preserved locally per user precedent, but logically subsumed into main

## 4. Spec Sync Status

This change was archived as `archived-on-merge` style with the full delta spec coverage provided by the follow-up `capability-merge` archive. The original change directory under `openspec/changes/flow-where-cross-project/` contained only `status.md` at archive time — no delta spec, no proposal/design/tasks. This is because:

1. The original change artifacts were temporarily lost or never committed to the change directory.
2. The `capability-merge` follow-up (`27111ed chore(archive): add flow-where-cross-project artifacts`) recovered them byte-identical from git.
3. The `capability-merge` itself was then archived at `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/` via `8d51c5f`.

The current archive `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/` contains the FULL delta spec (`explore.md`, `proposal.md`, `design.md`, `tasks.md`, `verify-report.md`, `specs/cross-project-search/spec.md`, `archive-report.md`). The original `flow-where-cross-project` archive at `openspec/changes/archive/2026-06-29-flow-where-cross-project/` (this commit's destination) contains only `status.md` + this archive-report.md.

This two-archive structure is intentional: the original change gets its audit trail (the status.md + the canonical "the feature shipped" closure), and the capability-merge gets the full SDD artifact trail.

## 5. Branch State (No Deletion Per User Precedent)

| Branch | Status |
|---|---|
| `codex/flow-where-cross-project` | **PRESERVED locally** at `d223516`. Per user precedent ("después vemos cleanup de branches" — deferred branch cleanup), the branch is NOT deleted by this archive commit. The branch is logically subsumed into main (the feat commit is reachable from main via `001651b`), but the local ref is retained for traceability. |
| `codex/flow-where-cross-project-capability-merge` | **PRESERVED locally** at `8d51c5f`. Same precedent applies. |
| `main` | At `9228289` (post-PR #41 v1.3-cli-split integration); cross-project feature is part of the line of history. |

## 6. Revival Path (Preserved Per User Intent)

Although the framing is revised (this is "shipped-via-prior-merge", not "close-as-superseded"), the user's revival-path intent is preserved as a possible future v1.3-follow-up:

**Scenario**: the v1.3-cli-split relocation chain did NOT touch the cross-project handler (Slices 1-8 each addressed different domain groups). The cross-project code at `cli/__init__.py:434+` lives in the post-v1.3 Click-group stub. A future v1.3-follow-up change could:

1. Move the cross-project handler to a dedicated submodule (e.g., `cli/where.py` if not already present, or extend an existing one).
2. Use the same v1.3-cli-split patterns: zero new logic, lazy imports, byte-determinism preservation, re-export barrel in `cli/__init__.py`.
3. Cross-reference the 10 unit tests in `tests/unit/test_cli_where_cross_project.py` (already in main) + the byte-identical guard.

If/when this is prioritized, a new SDD change named (e.g.) `flow-where-cross-project-v2` or `v1.3-platform-hardening-f` can be proposed. The archived artifacts at `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/` provide the full SDD trail for the original feature.

## 7. Cross-References

- **Archive directory (this change)**: `openspec/changes/archive/2026-06-29-flow-where-cross-project/`
- **Status file (audit trail)**: `openspec/changes/archive/2026-06-29-flow-where-cross-project/status.md`
- **Full delta spec archive (capability-merge follow-up)**: `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/`
- **Production code**: `src/flow_engineering/cli/__init__.py:434+` (Phase 2 dispatcher, not yet relocated to a domain submodule)
- **Test file**: `tests/unit/test_cli_where_cross_project.py` (preserved in main)
- **Other archived phases of workspace-intelligence**:
  - Phase 1 (`workspace-intelligence` — `flow projects ls --json`): `openspec/changes/archive/2026-06-29-workspace-intelligence/`
  - Phase 3 (`flow-workspace-status`): `openspec/changes/archive/2026-06-29-flow-workspace-status/`

## 8. Audit Trail

This archive move is the FIRST time this change directory has been moved from `openspec/changes/flow-where-cross-project/` to `openspec/changes/archive/2026-06-29-flow-where-cross-project/`. The single `status.md` file (originally created by `d223516` on 2026-06-29 as part of the chore-archive closure) is preserved intact as the audit trail. No content invented or modified.

The archive chore follows the convention of `git mv` to preserve file history through git's rename detection.

## 9. SDD Cycle Complete

The change has been fully planned (per status.md cross-references to explore #454, proposal #455, spec #456, design #457, tasks #458), implemented (1 feat commit), verified (9/9 gates + 1235/1235 tests at merge + AC9 byte-identical contract preserved), merged to main (`001651b`), integrated into the root capability spec (`780285f`), and now archived. The cycle is closed.