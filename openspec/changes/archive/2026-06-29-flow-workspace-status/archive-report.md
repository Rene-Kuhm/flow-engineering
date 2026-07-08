# Archive Report — `flow-workspace-status`

> **Change**: `flow-workspace-status` — Phase 3 of the workspace-intelligence effort. Adds top-level `flow workspace status` command with deterministic `--json` envelope.
> **Project**: `flow-engineering`
> **Status**: **ARCHIVED (DONE)** — 2026-07-08 (archive cleanup phase; status.md originally marked 2026-06-29).
> **Archive destination**: `openspec/changes/archive/2026-06-29-flow-workspace-status/`.
> **Mode**: openspec (filesystem move only — no delta-spec sync needed; no `specs/` directory exists in the original change).

## 1. Final Verdict

**`DONE — feature shipped; archive-orphan cleanup; SDD cycle complete.`**

| Metric | Result |
|---|---|
| Strategy | Single feature branch → merged to `main` via `681bfa1` (PR via `codex/flow-workspace-status`) |
| Original feature commit | `e7abfff feat(cli): add flow workspace status command` (180 LOC production) |
| Test commit | `b53baa0 test(cli): cover flow workspace status rules` (185 LOC test) |
| Archive status commit | `6b0c208 chore(archive): close flow-workspace-status` (added status.md to leftover dir) |
| Status reported on | 2026-06-29 (`status.md` self-archive declaration) |
| Actual archive move | 2026-07-08 (this commit) |
| Feature in `main` | ✅ — `src/flow_engineering/cli/workspace.py:170-207` |
| Feature parity verified | ✅ — see §3 |
| v1.3-cli-split relocation impact | Feature code relocated from `cli/__init__.py` → `cli/workspace.py` via Slice 2/8 (`d1b9ecf`); behavior byte-deterministic across the relocation |
| Findings | 0 CRITICAL + 0 WARNING |
| Archive readiness | READY — change folder moved to archive; status.md preserved as audit trail |

## 2. Change Summary

### 2.1 Identity

| Field | Value |
|---|---|
| Change name | `flow-workspace-status` |
| Cycle | Full SDD (explore → propose → spec → design → tasks → apply → verify → archive) |
| Branch | `codex/flow-workspace-status` (merged at `681bfa1`; branch still present locally — see §5) |
| Branch push status | `origin/codex/flow-workspace-status` exists (pushed earlier) |
| Spec path | `openspec/changes/flow-workspace-status/specs/workspace-status/spec.md` (now in archive) |
| Delta spec contents | ADDED requirements — REQ-WORKSPACE-STATUS-1 (top-level command) + REQ-WORKSPACE-STATUS-2 (deterministic `--json` envelope key order) + REQ-WORKSPACE-STATUS-3..7 (needs-attention rules R1-R5) |
| Final main HEAD at merge | `681bfa1` |
| Current main HEAD | `9228289` (PR #41 v1.3-cli-split integration) |

### 2.2 Goal

Adds a top-level `flow workspace status` command that lists sibling projects under the projects root with needs-attention rules (R1: dirty worktree, R2: no git, R3: no tests, R4: no OpenSpec, R5: graphify missing is informational). Supports deterministic `--json` envelope output (key order: `version`, `root`, `totals`, `projects`, `needs_attention`) for use by scripts and dashboards.

### 2.3 What Shipped

From `status.md` §"Shipped" + verification cross-check against production:

- ✅ Top-level `flow workspace status` command (verified at `cli/workspace.py:179`).
- ✅ Deterministic `--json` envelope with key order `version`, `root`, `totals`, `projects`, `needs_attention` (verified at `cli/workspace.py:198-205`).
- ✅ Needs-attention rules R1..R5 (verified via `_summarize_workspace_status` + `_render_workspace_status_text` in `cli/workspace.py`).
- ✅ Shared workspace test fixtures at `tests/unit/_workspace_fixtures.py` (59 LOC; relocated from the original `tests/unit/_workspace_fixtures.py`).
- ✅ Unit coverage: text output, JSON output, empty root, deterministic bytes, R1-R5, Phase 1 guard (24 tests at merge time; current suite adds more across the v1.3 chain).

## 3. Feature Parity Verification

User requirement: confirm the `flow workspace status --json` command matches the spec shipped at the time of merge.

| Spec Element | Original Location (pre-v1.3-cli-split) | Current Location (post-Slice 2) | Parity |
|---|---|---|---|
| `--json` click option | `cli.py:workspace_status` | `cli/workspace.py:172-178` | ✅ |
| `workspace_status` handler | `cli.py` | `cli/workspace.py:179-207` | ✅ |
| JSON envelope assembly | inline | `_workspace_status_envelope(root, projects, summary)` call (relocated) | ✅ |
| Deterministic `ensure_ascii=False`, `indent=2` | preserved | preserved | ✅ |
| Lazy import of `_detect_project_markers` | N/A (same-module at time) | `cli/workspace.py:185` (after relocation; `cli/__init__.py` is now the Click-group stub, so lazy import is required to avoid circular import — documented in the inline comment) | ✅ (refactor-stable) |
| Text render path | `_render_workspace_status_text` | relocated to `cli/workspace.py` | ✅ |
| Summary aggregator | `_summarize_workspace_status` | relocated to `cli/workspace.py` | ✅ |
| Public API re-export | N/A at merge time | `cli/__init__.py` re-exports for backward compat | ✅ (v1.3-cli-split preservation invariant REQ-CLI-SPLIT-2) |

**No production-code modifications were made by this archive commit.** The archive phase is documentation-only: `git mv` of the directory + this report.

## 4. Spec Sync Status

This change was archived as `archived-on-merge` style — the feature landed in `main` via `681bfa1` before the canonical `openspec/specs/{domain}/spec.md` pattern was fully established for incremental delta-sync. Per the v1.3-cli-split archive-report §3 (canonical `openspec/specs/cli/spec.md` for the `cli` root family), the workspace-status requirements are now expressed structurally as the `workspace_status` subcommand at `cli/workspace.py:170-207`. No spec drift detected.

## 5. Branch State

| Branch | Status |
|---|---|
| `codex/flow-workspace-status` | PRESERVED locally + pushed to `origin/codex/flow-workspace-status`. No deletion per user precedent "después vemos cleanup de branches". |
| `main` | At `9228289` (post-PR #41 v1.3-cli-split integration); workspace-status feature is part of the line of history. |

## 6. Cross-References

- **Archive directory**: `openspec/changes/archive/2026-06-29-flow-workspace-status/`
- **Status file (audit trail)**: `openspec/changes/archive/2026-06-29-flow-workspace-status/status.md`
- **Delta spec**: `openspec/changes/archive/2026-06-29-flow-workspace-status/specs/workspace-status/spec.md`
- **Other archived phases of workspace-intelligence**:
  - Phase 1 (`workspace-intelligence` — `flow projects ls --json`): `openspec/changes/archive/2026-06-29-workspace-intelligence/`
  - Phase 4 (`flow-where-cross-project-capability-merge` — root spec integration): `openspec/changes/archive/2026-06-30-flow-where-cross-project-capability-merge/`
  - Original Phase 2 (`flow-where-cross-project` — close-out decision documented): `openspec/changes/archive/2026-06-29-flow-where-cross-project/`
- **v1.3-cli-split relocation (Slice 2/8)** that absorbed this change: commit `d1b9ecf` (and follow-ups `f88b3a0` UTF-8 fixup, `b031310` byte-determinism verify); archived at `openspec/changes/archive/2026-07-08-v1.3-cli-split/`.

## 7. Audit Trail

This archive move is the FIRST time this change directory has been moved from `openspec/changes/flow-workspace-status/` to `openspec/changes/archive/2026-06-29-flow-workspace-status/`. The status.md file (originally created by `6b0c208` on 2026-06-29 as part of the chore-archive closure) is preserved intact as the audit trail. No content invented or modified.

The archive chore follows the convention of `git mv` to preserve file history through git's rename detection.

## 8. SDD Cycle Complete

The change has been fully planned (explore/proposal/spec/design/tasks), implemented (production + test), verified (24/24 tests at merge), merged to main (`681bfa1`), absorbed into the v1.3-cli-split relocation (`d1b9ecf`), and now archived. The cycle is closed.