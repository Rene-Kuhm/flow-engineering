# Archive Report — `workspace-intelligence`

> **Change**: `workspace-intelligence` — Phase 1 of the broader workspace-intelligence effort. Adds `--json` flag to `flow projects ls` with 7 new detection fields.
> **Project**: `flow-engineering`
> **Status**: **ARCHIVED (DONE)** — 2026-07-08 (archive cleanup phase; status.md originally marked 2026-06-29).
> **Archive destination**: `openspec/changes/archive/2026-06-29-workspace-intelligence/`.
> **Mode**: openspec (filesystem move only — delta-spec sync status documented in §4).

## 1. Final Verdict

**`DONE — feature shipped via `codex/workspace-intelligence` merge + absorbed into v1.3-cli-split relocation; archive-orphan cleanup; SDD cycle complete.`**

| Metric | Result |
|---|---|
| Strategy | Feature branch `codex/workspace-intelligence` (4 commits) → merged to `main` via `cb63b7d` |
| Original branch | `codex/workspace-intelligence` — **deleted locally post-merge** (per status.md "Branch: ... (preserved; awaiting user push/merge authorization)" was the original framing; the actual outcome is branch deleted after merge) |
| Original feature commit | `ebfd0d9 feat(cli): extend flow projects ls with --json + 7 new detection fields` (+217/-27 production LOC) |
| Original test commit | `0a7fc28 test(cli): add 9 new unit tests + 10 fixture helpers for workspace-intelligence` (+374 test LOC) |
| AC8 byte-determinism fix | `7aa8a53 fix(cli): drop generated_at from JSON envelope to restore AC8 byte-determinism` (prod+test, 51/-3 LOC) |
| Docs drift fix | `aee130f docs(workspace-intelligence): remove generated_at from proposal/explore/tasks` (+855 LOC documentation) |
| Archive status commit | `2daa8e7 chore(archive): add workspace-intelligence status` (added status.md to leftover dir) |
| Status reported on | 2026-06-29 |
| Actual archive move | 2026-07-08 (this commit) |
| Feature in `main` | ✅ — `src/flow_engineering/cli/project.py:277` (`--json` click option) |
| Feature parity verified | ✅ — see §3 |
| v1.3-cli-split relocation impact | Production relocated from `cli.py` → `cli/project.py` via Slice 3/8 (`aa2a955`); behavior byte-deterministic |
| Findings | 0 CRITICAL + 0 WARNING + 1 NOTE (see §3 — original claim about `f37e1ae` was incorrect; actual cross-reference is `aa2a955` + workspace-intelligence commits) |
| Archive readiness | READY — change folder moved to archive; status.md preserved as audit trail |

## 2. Change Summary

### 2.1 Identity

| Field | Value |
|---|---|
| Change name | `workspace-intelligence` (Phase 1) |
| Cycle | Full SDD (explore → propose → spec → design → tasks → apply × 4 commits → verify → merge → archive) |
| Branch (now deleted) | `codex/workspace-intelligence` — merged via `cb63b7d` then removed locally |
| Spec path | `openspec/changes/workspace-intelligence/specs/projects-ls-json/spec.md` (now in archive) |
| Final main HEAD at merge | `cb63b7d` |
| Current main HEAD | `9228289` (post-PR #41 v1.3-cli-split integration) |
| Archive artifact trail | `proposal.md`, `explore.md`, `design.md`, `tasks.md`, `status.md` (5 files) |

### 2.2 Goal

Extends `flow projects ls` with a `--json` flag that emits a v1 JSON envelope with a `version: "1"` field as the first key. The envelope exposes 7 new detection fields per project: `branch`, `dirty`, `remote`, `test_commands`, `has_openspec`, `has_graphify`, `has_engram` (the last is a stub that always reports `false` in Phase 1). The 4 legacy text-table fields (`name`, `path`, `has_git`, `type`) are preserved for backward compatibility, totaling 11 fields per project in the v1 JSON schema (per status.md §"User Requirements Satisfied").

### 2.3 What Shipped (verified live)

From `status.md` §"User Requirements Satisfied" + live verification of `cli/project.py`:

- ✅ `--json` flag on `flow projects ls` (verified at `cli/project.py:276-284`).
- ✅ `version: "1"` as first key of envelope (verified at `cli/project.py:319` and `:334`).
- ✅ 11-field envelope per project at Phase 1 merge time (4 legacy + 7 new); current production has **14 fields** due to subsequent feature additions (`has_readme`, `has_pytest_config`, `dirty_files`) — see §3.
- ✅ `has_engram` stub: always `false` (verified at `cli/project.py:282-283` help text + `:295-296` docstring).
- ✅ Subprocess seam pattern: `_git()` wrapper with lazy import (verified at `cli/project.py:185`).
- ✅ Schema versioning documented in the help text: `"v1 schema"` + `"NOTE: 'has_engram' is currently a stub field and always reports false"`.
- ✅ 14 unit tests at merge time (4 baseline + 9 new + 1 byte-determinism regression — see status.md §"Final Verification").

### 2.4 BDD Scenarios + Acceptance Criteria

Per status.md §"BDD Scenarios (7/7 PASS) and Acceptance Criteria (10/10)":

- ✅ All 7 BDD scenarios from spec #438 pass.
- ✅ All 10 acceptance criteria from spec #138 satisfied.
- ✅ AC8 byte-determinism verified live: 2 consecutive `uv run flow projects ls --json` invocations on the real `<root>` produced 6008 bytes each, byte-for-byte identical (case-sensitive comparison).

## 3. Feature Parity Verification

User requirement: verify the `flow projects ls --json` command matches the Phase 1 spec, and cross-reference the workspace-health-advisor PR3 commit.

### 3.1 Production parity

| Spec Element | Original Location (pre-v1.3-cli-split) | Current Location (post-Slice 3) | Parity |
|---|---|---|---|
| `--json` click option | `cli.py:projects_ls` (~line 2660 at merge time) | `cli/project.py:276-284` | ✅ |
| `projects_ls` handler | `cli.py` | `cli/project.py:285-353` | ✅ |
| Lazy `_git()` import | N/A (same-module at merge time) | `cli/project.py` (lazy import pattern after Slice 3 relocation; verified via `git show aa2a955` body §"Pragmatic body adjustments" — lazy import re-fetches `cli._git` on every call so monkeypatched test seams still flow through) | ✅ |
| `_detect_project_markers` helper | `cli.py` | `cli/project.py` | ✅ |
| 11-field envelope | merge time | now 14-field (extended by `5d72384 feat(cli): extend project markers with has_readme + has_pytest_config` + `622120b feat(dashboard): thread dirty_files through DS1/DS2 envelopes`) | ✅ additive evolution |
| AC8 byte-determinism | `generated_at` removed in `7aa8a53` | preserved (no re-introduction; regression test `test_flow_projects_ls_json_byte_identical_envelope` still guards against re-introduction) | ✅ |

### 3.2 Test parity

| Test File | Touched By | Current State |
|---|---|---|
| `tests/unit/test_cli_projects.py` | `0a7fc28` (workspace-intelligence — 9 new tests + 10 fixture helpers), `7aa8a53` (byte-determinism regression test), `5518386` (workspace-status — dot-prefix filter adjustments), `ba26df9` (workspace-status — subcommand additions), `5d72384` (has_readme + has_pytest_config test extensions), `622120b` (dirty_files test extensions) | Preserved at `tests/unit/test_cli_projects.py`; AC8 byte-determinism test lives on |
| `tests/unit/test_cli_workspace_status.py` | `b53baa0` (Phase 3 — workspace-status tests) | Preserved |

### 3.3 ⚠️ HONEST CORRECTION: cross-reference commit

> The user's input claimed: *"Cross-references the workspace-health-advisor PR3 commit (`f37e1ae`) which touched `test_cli_projects.py` (the Phase 1 test file from this change) — confirm this confirms the test moved with the feature"*.

**This claim is INCORRECT.** Verified via `git show f37e1ae --stat`:

```
commit f37e1ae5f2389b0c753356c6cf9d552627118887
Subject: test(cli): lock workspace_health_cmd default + root + missing-root contract

 tests/unit/test_cli_workspace_health.py | 51 +++++++++++++++++++++++++++++++++
 1 file changed, 51 insertions(+)
```

`f37e1ae` touches **`test_cli_workspace_health.py`** (a different test file added by the workspace-health-advisor chain — see `cb63b7d` through `8577d9c`), NOT `test_cli_projects.py`.

The actual commit that confirms the test moved with the feature is **`aa2a955 refactor(cli): relocate projects group to cli/project.py (Slice 3/8)`** (PR #35 in the v1.3-cli-split chain). That commit body explicitly states: *"Mechanical relocation of the flow projects Click group + its 5 private helpers (_git, _detect_stack, _detect_test_commands, _has_pytest_config, _detect_project_markers) and the 3 subcommand bodies (projects_ls, projects_backfill, projects_alias) from cli/__init__.py lines 2815-3340 (post-Slice-1+2) into a NEW cli/project.py."*

Combined with the v1.3-cli-split verification chain (see `archive/2026-07-08-v1.3-cli-split/archive-report.md` §3.3 Slice 3 entry: *"34/34 targeted workspace tests PASS; 13 cross-module import sites verified; lazy-import `_git` pattern in `_detect_project_markers`"*), this confirms the workspace-intelligence Phase 1 test contract (`test_cli_projects.py` byte-determinism guard) moved with the feature.

The AC8 byte-determinism invariant was preserved through the v1.3-cli-split relocations: `b031310 chore(cli): verify cli/workspace.py slice 2 byte-determinism green` and `a219259 chore(openspec): verify cli/project.py slice 3 byte-determinism green` both green-lit the project.py relocation with the byte-determinism contract intact.

## 4. Spec Sync Status

This change was archived as `archived-on-merge` style — the feature landed in `main` via `cb63b7d` before the canonical `openspec/specs/{domain}/spec.md` pattern was established for incremental delta-sync. Per the v1.3-cli-split archive-report §3, the projects-related requirements are now expressed structurally at `cli/project.py:277` (subcommand declaration) + `_detect_project_markers` helper. No spec drift detected at archive time.

The original delta spec at `openspec/changes/workspace-intelligence/specs/projects-ls-json/spec.md` is preserved in the archive as the audit trail for the 11-field Phase 1 schema.

## 5. Branch State (User History Honesty Note)

The `status.md` §"Branch State" says:

> **Branch**: `codex/workspace-intelligence`
> **Merge status**: NOT merged to `main`; awaiting user decision
> **Push status**: NOT pushed; awaiting user authorization

**This status was written before the merge happened.** Verified outcome:

| Field | Status at `status.md` time (2026-06-29) | Actual outcome (post-merge) |
|---|---|---|
| Branch | `codex/workspace-intelligence` preserved | Merged via `cb63b7d`, then deleted locally |
| Push | Not pushed | Branch was never pushed to `origin` (no `remotes/origin/codex/workspace-intelligence` in `git branch --list --all`); merge happened via local branch |
| Merge | "NOT merged" | Merged to `main` via `cb63b7d` |

The branch was a **local-only merge** — a codex agent merged `codex/workspace-intelligence` directly into `main` without ever pushing to `origin`. The work is therefore on `main` but not on any remote. This is consistent with the v1.3-cli-split archive-report §3.1 noting that some prior changes were local-only.

## 6. Cross-References

- **Archive directory**: `openspec/changes/archive/2026-06-29-workspace-intelligence/`
- **Status file (audit trail)**: `openspec/changes/archive/2026-06-29-workspace-intelligence/status.md`
- **Delta spec**: `openspec/changes/archive/2026-06-29-workspace-intelligence/specs/projects-ls-json/spec.md`
- **Other archived phases of workspace-intelligence**:
  - Phase 2 (`flow-where-cross-project` — close-out decision documented): `openspec/changes/archive/2026-06-29-flow-where-cross-project/`
  - Phase 3 (`flow-workspace-status`): `openspec/changes/archive/2026-06-29-flow-workspace-status/`
  - Phase 4 (`flow-where-cross-project-capability-merge` — root spec integration): `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/`
- **v1.3-cli-split relocation (Slice 3/8)** that absorbed this change: commit `aa2a955` (PR #35); archived at `openspec/changes/archive/2026-07-08-v1.3-cli-split/`.
- **Workspace-health-advisor chain** that built on this Phase 1: PRs #29 → #31, merged via `8577d9c`. The `test_cli_workspace_health.py` file (PR3, `f37e1ae` etc.) is downstream of this work but is its own change, archived at `openspec/changes/archive/2026-07-01-workspace-dashboard-usability-pass/` and similar.

## 7. Audit Trail

This archive move is the FIRST time this change directory has been moved from `openspec/changes/workspace-intelligence/` to `openspec/changes/archive/2026-06-29-workspace-intelligence/`. The 5 artifact files (`proposal.md`, `explore.md`, `design.md`, `tasks.md`, `status.md`) are preserved intact as the audit trail. No content invented or modified.

The archive chore follows the convention of `git mv` to preserve file history through git's rename detection.

## 8. SDD Cycle Complete

The change has been fully planned (explore/proposal/spec/design/tasks), implemented (4 commits: production + tests + AC8 fix + docs drift fix), verified (14/14 tests at merge, AC8 byte-determinism live-verified), merged to main (`cb63b7d`), absorbed into the v1.3-cli-split relocation (`aa2a955` Slice 3/8), and now archived. The cycle is closed.

---

## Appendix A: Honest Diff Between Status.md and Reality

Per the user's "Honest assessment" requirement (borrowed from the flow-where-cross-project case, applicable here too), the following discrepancies between `status.md` and actual git history are documented for transparency:

| Status.md Claim | Actual Git History | Honesty |
|---|---|---|
| "Branch: codex/workspace-intelligence (preserved; awaiting user push/merge authorization)" | Branch was merged via `cb63b7d` then deleted | Status.md was outdated (written pre-merge); the archive report is the authoritative truth |
| "Merged: NO — local-only" | Merged via `cb63b7d` (local-only merge; never pushed to origin) | Status.md was outdated; the local-only nature is preserved (branch was never on origin) |
| "Push status: NOT pushed; awaiting user authorization" | Branch was never pushed (no `remotes/origin/codex/workspace-intelligence`) | Consistent — branch remained local-only throughout |
| "Ahead of main: 4 commits" | 4 commits ahead of main at status.md time | Consistent at status.md time |

**Lesson captured for future cycles**: when a status.md is added to a change directory post-merge, the archive phase should treat the status.md as a historical artifact (frozen at the time of writing) rather than a current-state declaration.