<!-- spec.md: cli capability catalog (root). Source: sdd-archive for `v1.3-cli-split` (change #N, 2026-07-08). Family-index bootstrap — single root capability describing the **module organization invariant** of `src/flow_engineering/cli/`. The 5 root REQs are structural / architectural and are orthogonal to the behavior-level REQs owned by other families (`workspace`, `decision-drift`, `prompt-registry`, `observability`, `flow-where`). Mirrors `workspace/spec.md` style (family index, not canonical source for delta REQs). -->
# CLI Capability Spec

> **Family index, not canonical source.** Canonical requirements live in delta specs under `openspec/changes/<change-name>/specs/<sub-capability>/spec.md` and `openspec/changes/archive/<date>-<change>/specs/<sub-capability>/spec.md`. This file anchors the CLI capability family and provides cross-references for navigation. Each root-level REQ cites its delta source via the `Source:` field. Do not treat this file as the source of truth for delta REQ wording — that is what the delta specs are for.

## Archive status (2026-07-08)

**`v1.3-cli-split` SHIPPED as the first `cli` family anchor — single change, 8 chained stacked-to-tracker PRs (PRs #32–#40) + integration PR #41 + lint/type fixup `bde5f1b`, byte-deterministic, public-API-preserving, ruff/mypy-clean after the fixup.**

**Role**: This is the **first** root capability spec for `cli`. Before this change, the entire CLI was a single 5,337-LOC `cli/__init__.py` file with no root capability spec. The 5 root REQs (REQ-CLI-SPLIT-1..5) describe the **module organization invariant** that future CLI refactors MUST honor: mechanical relocation only, public API preservation, byte-determinism preservation, zero new logic per slice, and the 400-LOC review-budget-justification pattern for chained PRs.

**Verdict at archive**: **PASS — mechanical-only, zero behavior change**. The change is a pure file-tree reorganization: `cli/__init__.py` reduced from 5,337 → 1,621 LOC (Click-group stub + re-export barrel) and 8 new submodules carry the relocated code. All 14 public API names (8 spec'd + 6 cross-cutting constants/helpers) remain importable from `flow_engineering.cli`. Byte-determinism preserved across all 8 slices (SHA-256 `B51EC7F5...` matches `origin/main @ 8577d9c` baseline for `flow workspace health --json` on the same `C:\dev\proyects` fixture). Per `openspec/changes/archive/2026-07-08-v1.3-cli-split/apply-progress.md` and `verify-report-slice1.md`: 1678 pytest pass (2 pre-existing BDD skill-fixture failures per [issue #22](https://github.com/Rene-Kuhm/flow-engineering/issues/22)); ruff clean after `bde5f1b`; mypy clean after `bde5f1b`.

**Findings tally**: **0 CRITICAL + 0 WARNING + 1 SUGGESTION** at archive. The SUGGESTION is a future-work item: if the `cli` carve-out can be tightened (e.g., reducing the `flow_engineering.cli.*` mypy/lint scope currently in `pyproject.toml`), the carve-out can shrink in a follow-up. Documented as `cli-followup-lint-scope-tighten` carry-forward.

**Carry-forwards documented in Future Changes** (§7): `cli-followup-lint-scope-tighten` (mypy/lint scope carve-out refinement); `metrics-namespace-rewrite` (REQ-V1.3.6 — `flow metrics` flat-dump shim still in place, deferred); `drift-events-alias-removal` (REQ-V1.3.7 — `flow drift-events` deprecated group still in place, deferred); `archive-dead-code-removal` (`archive()` function at pre-split `__init__.py:320-349` still in place, deferred); `cli-residual-split` (top-level commands `new`/`apply`/`where`/`save`/`watch` etc. still in `cli/__init__.py`; the 1,428→1,621 LOC residual exceeds the proposal's "≤500 LOC after all slices" success criterion — see §6).

## 1. Purpose

Cross-version capability spec for the **CLI module** — the package layout
and module organization invariant for `src/flow_engineering/cli/`. The capability
governs:

- the **8-sliced module structure** of `flow_engineering.cli` — `cli/__init__.py` is a Click-group stub + re-export barrel; domain logic lives in `cli/{_shared,workspace,project,drift,snapshot,prompts,metrics,archive}.py`;
- the **14-name public API surface** importable from `flow_engineering.cli` (8 spec'd + 6 cross-cutting constants/helpers used by `health.py` / `workspace_hygiene.py` / `_GOLDEN_PROMPTS_DIR` test seam);
- the **byte-determinism invariant** — `flow workspace health --json` and `--no-color` output MUST remain sha256-stable against the captured `origin/main @ 8577d9c` baseline across any future slice;
- the **zero-new-logic discipline** — each slice is purely a `git mv` of source blocks; no new functions, no new test files, no behavior changes;
- the **400-LOC review budget justification** — slices that exceed the 400-line per-PR budget MUST include the "Mechanical relocation, not new logic" paragraph in the PR body (5/8 slices in the inaugural chain exceeded the budget; pattern established for future chains).

**What `cli` is NOT**: a behavioral capability. The 8 submodules implement Click commands owned by other families:
- `workspace_group` → `workspace/spec.md` (REQ-WORKSPACE-*)
- `projects_group` → `workspace/spec.md` (REQ-WORKSPACE-PROJECT-IDENTITY, etc.)
- `drift_group` + `drift_events_group` → `decision-drift/spec.md` (REQ-55..59, REQ-V1.2.4)
- `snapshot_group` → snapshot-manager behavioral spec (carried by `flow-snapshot-*` changes; not yet a root family)
- `prompts_group` → `prompt-registry/spec.md` (REQ-45..47, REQ-49..50)
- `metrics_group` → `observability/spec.md` (REQ-35..39)
- `archive_group` + `archive_change_cmd` → V1.3.4 archive introspection
- `rotate_cmd` → V1.3.4 archive rotation

The `cli` family describes WHERE the code lives and HOW the public API is preserved across future relocations — not WHAT the code does.

## 2. Capability boundary

```
                ┌──────────────────────────────────────────────────┐
                │              cli  (this spec)                      │
                │  "module organization + public API invariant"     │
                │                                                  │
                │  • 8-sliced submodule layout                     │
                │  • 14-name public API (8 spec'd + 6 helpers)      │
                │  • byte-determinism invariant (REQ-CLI-SPLIT-3)  │
                │  • zero-new-logic discipline (REQ-CLI-SPLIT-4)    │
                │  • 400-LOC review budget justification (REQ-5)    │
                └──────────────────────────────────────────────────┘
                                        │
                                        │  ORTHOGONAL — describes structure
                                        ▼
                ┌──────────────────────────────────────────────────┐
                │      behavior families (8 submodules)             │
                │  workspace | decision-drift | prompt-registry |   │
                │  observability | flow-where | snapshot | archive  │
                │                                                  │
                │  These specs describe WHAT the code does.         │
                │  cli describes WHERE the code lives.             │
                └──────────────────────────────────────────────────┘
```

**Boundary rule**: any REQ that describes **how the CLI is packaged, imported, or refactored** belongs here. Any REQ that describes **what a CLI command does, what data it handles, or what business logic it implements** belongs to the corresponding behavior family. The two are orthogonal: a workspace behavior REQ can ship a feature while a `cli` REQ can simultaneously split the file tree; both REQs are independently testable.

**Boundary stress tests**:

| Scenario | `cli` family? | Why |
|----------|---------------|-----|
| "Add a new `flow workspace fix --dry-run` flag" | ❌ `workspace` | New behavior; lives in `cli/workspace.py` but described by `workspace/spec.md` |
| "Move `workspace_health_cmd` from `cli/__init__.py` to `cli/workspace.py`" | ✅ YES | Module organization; no behavior change |
| "Public API of `flow_engineering.cli` MUST keep 14 names importable" | ✅ YES | Public API contract for the module |
| "Capture byte-determinism SHA-256 of `flow workspace health --json` across refactors" | ✅ YES | Byte-determinism invariant (REQ-CLI-SPLIT-3) |
| "`flow drift` exits 2 on missing snapshots dir" | ❌ `decision-drift` | Behavior; lives in `cli/drift.py` but described by `decision-drift/spec.md` |

## 3. Sub-capabilities

The `cli` family has **1 confirmed sub-capability** (the mechanical relocation itself) and **0 placeholder sub-capabilities** at archive time:

| # | Sub-capability | Module path | Role | Status | Delta spec |
|---|---------------|-------------|------|--------|------------|
| 1 | `cli-split` | `src/flow_engineering/cli/{__init__,_shared,workspace,project,drift,snapshot,prompts,metrics,archive,rotation}.py` | Module organization — 8-sliced package layout + 14-name public API + byte-determinism invariant | ✅ Shipped + archived at 2026-07-08 | `openspec/changes/archive/2026-07-08-v1.3-cli-split/specs/cli-split/spec.md` |

**Future sub-capabilities (placeholder, NOT yet in the family)**: any future mechanical refactor of the CLI module (e.g., a `cli-residual-split` change that splits the remaining top-level commands out of `cli/__init__.py`) would land as a new sub-capability in this family. Each new sub-capability is independently testable against the existing 5 root REQs.

**Module layout (post-`v1.3-cli-split`)**:

| File | LOC | Origin | Public re-exports from `flow_engineering.cli` |
|------|-----|--------|-----------------------------------------------|
| `cli/__init__.py` | 1,621 | Click-group stub + re-export barrel | `main`, `workspace_health_cmd`, `_detect_project_markers`, `_format_drift_events_text`, `_iter_project_subdirs`, `_summarize_workspace_status`, `_git`, `rotate_cmd`, `_resolve_projects_root`, `_DEFAULT_PROJECTS_ROOT_WIN`, `_DEFAULT_PROJECTS_ROOT_NIX`, `_read_pyproject_min_skill_versions`, `_enforce_min_skill_versions_or_exit`, `_GOLDEN_PROMPTS_DIR` (14 names) |
| `cli/_shared.py` | 124 | Slice 1 — constants + skill-version helpers + subdir iterator | `_iter_project_subdirs` + internal cross-cutting helpers (not re-exported at top level) |
| `cli/workspace.py` | 737 | Slice 2 — `workspace_group` + 6 sub-commands + `workspace_health_cmd` + 13 hygiene helpers | `workspace_health_cmd`, `_summarize_workspace_status` |
| `cli/project.py` | 580 | Slice 3 — `projects_group` + 3 sub-commands + `_git` + `_detect_project_markers` | `_detect_project_markers`, `_git` |
| `cli/drift.py` | 891 | Slice 4 — `drift_group` + `drift_run` + `drift_events_group` + 3 events commands + alias shims | `_format_drift_events_text` |
| `cli/snapshot.py` | 423 | Slice 5 — `snapshot_group` + 6 sub-commands + 3 snapshot helpers | (none — reached via `main.commands['snapshot']`) |
| `cli/prompts.py` | 833 | Slice 6 — `prompts_group` + 4 sub-commands + `CheckAction` + 11 prompts helpers | (none — reached via `main.commands['prompts']`; `_GOLDEN_PROMPTS_DIR` re-exported for test seam) |
| `cli/metrics.py` | 600 | Slice 7 — `metrics_group` + 3 children + `_summarize_metrics` + `_apply_metrics_filters`; legacy flat-dump shim preserved verbatim | (none — reached via `main.commands['metrics']`) |
| `cli/archive.py` | 267 | Slice 8 — renamed from `cli/rotation.py`; absorbs `archive_group` + `archive_change_cmd` | `rotate_cmd` |
| `cli/rotation.py` | 194 | Slice 8 — 3-line back-compat shim re-exporting from `cli/archive.py` | (legacy import seam; not a re-export on `flow_engineering.cli`) |
| **Total `cli/`** | **6,270** | **+933 net vs pre-split `cli/__init__.py` (5,337)** | Scaffolding + docstrings + lazy-import comments |

## 4. Requirements

The 5 root-level REQs below are **structural / architectural invariants** that any future mechanical refactor of the CLI module MUST honor. Canonical wording, Given/When/Then scenarios, and acceptance criteria live in the delta spec cited under each REQ's `Source:` line.

---

### REQ-CLI-SPLIT-1-MECHANICAL-RELOCATION

For each slice of any future chained CLI relocation (e.g., a `cli-residual-split` follow-up), the relocation SHALL be purely mechanical:

- The source code block SHALL move via `git mv` (preserves history with rename detection > 90% similarity per `git diff -M --find-renames` for true renames; extract-to-new-file patterns produce a `M+A` diff with byte-identical content match as the equivalent — see `verify-report-slice1.md` W1 for the spec wording caveat).
- The parent module (`flow_engineering.cli.__init__`) MUST add a re-export line `from flow_engineering.cli.<submodule> import <name>` for every public-API name that moved out (see REQ-CLI-SPLIT-2).
- The parent module MUST use **lazy imports** (`from . import <submodule> as _<submodule>  # noqa: F401`) for submodules that register Click groups/commands at import time, to prevent double-registration (`RuntimeError: Group <name> is already registered`). Precedent established at the post-`v1.3-cli-split` `cli/__init__.py` block (13 lazy imports, one per relocated submodule).
- All existing tests MUST pass unchanged (`uv run pytest` green per slice).

**Source:** `openspec/changes/archive/2026-07-08-v1.3-cli-split/specs/cli-split/spec.md` → REQ-CLI-SPLIT-1 + 6 scenarios (Slice 1-8 mechanical moves).

**Out of scope:** any algorithmic / behavioral change to the relocated code. The `main` Click group definition MUST stay ABOVE the lazy-import block in `cli/__init__.py` (Slice 2 placement, see apply-progress §"Slice 2" Pragmatic body adjustments), so that submodules can `from flow_engineering.cli import main` at decorator-evaluation time without circular import.

---

### REQ-CLI-SPLIT-2-PUBLIC-API-PRESERVATION

The 14 public importable names from `flow_engineering.cli` MUST remain importable across all slices and across any future chained CLI relocation. The 8 spec'd names are:

1. `main` (61 test files + `cli/__init__.py` re-export) — the Click group root
2. `workspace_health_cmd` (1 test file + downstream) — `flow workspace health`
3. `_detect_project_markers` (8 tests + `src/flow_engineering/health.py:538`) — used as a library by `health.py`
4. `_format_drift_events_text` (2 tests) — `flow drift-events list` text formatter
5. `_iter_project_subdirs` (2 tests) — `flow workspace status` project iterator
6. `_summarize_workspace_status` (2 tests) — `flow workspace status` aggregator
7. `_git` (`src/flow_engineering/workspace_hygiene.py:363`) — used as a library by `workspace_hygiene.py`
8. `rotate_cmd` (1 test file + `cli/rotation.py` shim until Slice 8 absorbs it) — `flow archive rotate`

The 6 additional cross-cutting re-exports (per `apply-progress.md` §"Slice 6" + §"Slice 7" final state):

9. `_resolve_projects_root` (used by `_iter_project_subdirs` and downstream)
10. `_DEFAULT_PROJECTS_ROOT_WIN` (constant; `pathlib.Path` Windows default)
11. `_DEFAULT_PROJECTS_ROOT_NIX` (constant; `pathlib.Path` Posix default)
12. `_read_pyproject_min_skill_versions` (helper for skill-version gate)
13. `_enforce_min_skill_versions_or_exit` (helper for skill-version gate)
14. `_GOLDEN_PROMPTS_DIR` (constant; test seam patched by `tests/unit/conftest.py:18-37` via `monkeypatch.setattr(cli_mod, "_GOLDEN_PROMPTS_DIR", snap_dir, raising=False)`)

**Source:** `openspec/changes/archive/2026-07-08-v1.3-cli-split/specs/cli-split/spec.md` → REQ-CLI-SPLIT-2 + 3 scenarios (main, `_detect_project_markers` shape, `rotate_cmd` post-rename).

**Out of scope:** adding new top-level public names. New Click commands can be added in their owning behavior family (`workspace`, `decision-drift`, etc.) without going through `cli/`'s public API contract.

---

### REQ-CLI-SPLIT-3-BYTEDETERMINISM-PRESERVED

The byte-determinism invariant MUST continue to hold across all slices and across any future chained CLI relocation. Specifically, `flow workspace health --json` and any `--no-color` output produced by the relocated subcommands MUST remain sha256-stable against the baseline captured on `origin/main @ 8577d9c` (SHA-256 `B51EC7F54995C6C48261AF4BB35617A75D05812F5FA109410C1D1E4693B2CA9D` for `flow workspace health --json` against the `C:\dev\proyects` workspace fixture).

**Source:** `openspec/changes/archive/2026-07-08-v1.3-cli-split/specs/cli-split/spec.md` → REQ-CLI-SPLIT-3 + 2 scenarios (`flow workspace health --json` byte-identical, `--no-color` text output byte-identical).

**Out of scope:** asserting byte-determinism for commands outside the workspace slice (e.g., `flow drift --help` is a separate baseline per `apply-progress.md` §"Slice 4" — `a63f07e6...`). Future slices that touch workspace code MUST re-capture the workspace health baseline before and after the slice; the diff MUST be empty for both `flow workspace health --json` and `flow workspace status --no-color`.

---

### REQ-CLI-SPLIT-4-ZERO-NEW-LOGIC

Each slice of any future chained CLI relocation SHALL introduce no new functions, no behavior changes, and no new test files. The only acceptable diff per slice is:

- `git mv` of source code blocks (rename detection > 90% similarity for true renames; byte-identical content match for extract-to-new-file)
- Re-export lines added to `cli/__init__.py`
- A lazy import line in `cli/__init__.py` for the new submodule
- The new submodule's own import block (no new third-party dependencies)
- Function-body lazy imports inside relocated code, IF AND ONLY IF the cross-module reference problem requires it (e.g., `EngramClient` lazy-import in `drift._write_back_findings` because tests monkeypatch `flow_engineering.cli.EngramClient`)

**Source:** `openspec/changes/archive/2026-07-08-v1.3-cli-split/specs/cli-split/spec.md` → REQ-CLI-SPLIT-4 + 3 scenarios (no new function names, no new test files, mechanical diff with rename detection).

**Out of scope:** algorithmic refactors, behavior changes, or test-file additions. Any of those belongs in a separate, non-mechanical change.

---

### REQ-CLI-SPLIT-5-REVIEW-BUDGET-JUSTIFICATION

Slices that exceed the 400-LOC review budget MUST include a "Mechanical relocation, not new logic" justification paragraph in the PR description. The paragraph MUST:

- Reference this spec (`openspec/specs/cli/spec.md` for the root or `openspec/changes/<change-name>/specs/cli-split/spec.md` for the delta).
- Reference the design.md for scope confirmation.
- Acknowledge the PR-review burden (5/8 inaugural slices exceeded 400 LOC).
- Confirm the diff is a `git mv` (rename detection > 90% similarity for true renames; byte-identical content match for extract-to-new-file), not new logic.
- State the number of new function names added (expected: 0).
- State the number of test files added (expected: 0).

**Source:** `openspec/changes/archive/2026-07-08-v1.3-cli-split/specs/cli-split/spec.md` → REQ-CLI-SPLIT-5 + 2 scenarios (over-budget PRs include the justification, under-budget PRs do not require it).

**Out of scope:** inflating the budget retroactively. The 400-LOC cap remains a meaningful guard; the justification paragraph is an acknowledgement, not a waiver. Future cycles that propose 3-way or 4-way splits to stay under budget should follow the `workspace-dashboard-usability-pass` precedent (PR2 704 LOC → 3 PRs of 246/227/231 LOC, all under 400 — see Engram obs #1890).

---

## 5. Cross-references

### 5.1 Other root capability specs (behavior families)

- `openspec/specs/workspace/spec.md` — owns the `workspace_group` behavior REQs; `cli/workspace.py` is its module home.
- `openspec/specs/decision-drift/spec.md` — owns `drift_group` + `drift_events_group` + the deprecation contract (REQ-V1.2.4); `cli/drift.py` is its module home.
- `openspec/specs/prompt-registry/spec.md` — owns `prompts_group` + `CheckAction`; `cli/prompts.py` is its module home.
- `openspec/specs/observability/spec.md` — owns `metrics_group` + REQ-35..39; `cli/metrics.py` is its module home.
- `openspec/specs/flow-where/spec.md` — owns `where_cmd` (still in `cli/__init__.py`; future `cli-residual-split` would relocate to `cli/where.py`).
- Snapshot manager behavior (carried by `flow-snapshot-*` changes; not yet a root family) — `snapshot_group`; `cli/snapshot.py` is its module home.

### 5.2 Source artifacts (archived)

- `openspec/changes/archive/2026-07-08-v1.3-cli-split/proposal.md` — the original 8-slice chain proposal.
- `openspec/changes/archive/2026-07-08-v1.3-cli-split/design.md` — the technical design (slice map + lazy-import pattern + review budget justification).
- `openspec/changes/archive/2026-07-08-v1.3-cli-split/specs/cli-split/spec.md` — the **canonical delta spec** for REQ-CLI-SPLIT-1..5. Treat this as the source of truth for REQ wording; the root REQ summaries in §4 are derived from it.
- `openspec/changes/archive/2026-07-08-v1.3-cli-split/tasks.md` — the 9-task plan (T-0.1, T-0.2, T-1..T-8); all 9 marked `[x]` at archive (T-2..T-8 reconciliation at archive time per orchestrator instruction; apply-progress.md proves all 8 slices shipped).
- `openspec/changes/archive/2026-07-08-v1.3-cli-split/apply-progress.md` — the 1,864-line slice-by-slice apply audit trail (8 slice sections + Slice 2 fixup `f88b3a0` for cp1252 corruption; Slice 6 + 7 + 8 detail per-slice evidence).
- `openspec/changes/archive/2026-07-08-v1.3-cli-split/verify-report-slice1.md` — the Slice 1 verify report (PASS WITH WARNINGS; W1 + W2 are spec-wording caveats closed in this archive by REQ-CLI-SPLIT-4 scenario amendment).
- `openspec/changes/archive/2026-07-08-v1.3-cli-split/archive-report.md` — the archive closeout (this report's parent).

### 5.3 Git history

| Commit | Subject | Slice |
|--------|---------|-------|
| `1705de1` | `chore(openspec): archive workspace-health-advisor-pr4 + start v1.3-cli-split change artifacts` | Pre-Slice-1 audit-trail recovery |
| `4800483` | `chore(openspec): land v1.3-cli-split change artifacts (Slice 1 audit trail)` | Slice 1 artifacts commit |
| `dabe321` | `refactor(cli): extract shared helpers to cli/_shared.py (Slice 1/8)` | Slice 1 |
| `d1b9ecf` | `refactor(cli): relocate workspace group to cli/workspace.py (Slice 2/8)` | Slice 2 |
| `f88b3a0` | `fix(cli): restore UTF-8 chars in cli/workspace.py comments (Slice 2/8)` | Slice 2 fixup (cp1252 corruption) |
| `b031310` | `chore(cli): verify cli/workspace.py slice 2 byte-determinism green (Slice 2/8)` | Slice 2 verify |
| `aa2a955` | `refactor(cli): relocate projects group to cli/project.py (Slice 3/8)` | Slice 3 |
| `06fad84` | `refactor(cli): relocate drift group to cli/drift.py (Slice 4/8)` | Slice 4 |
| `f897ab4` | `refactor(cli): relocate snapshot group to cli/snapshot.py (Slice 5/8)` | Slice 5 |
| `bc1cbcc` | `chore(cli): verify cli/snapshot.py slice 5 byte-determinism green (Slice 5/8)` | Slice 5 verify |
| `0a723f2` | `refactor(cli): relocate prompts group to cli/prompts.py (Slice 6/8)` | Slice 6 |
| `8a767d8` | `chore(cli): verify cli/prompts.py slice 6 byte-determinism green (Slice 6/8)` | Slice 6 verify |
| `a30f41c` | `refactor(cli): relocate metrics group to cli/metrics.py (Slice 7/8)` | Slice 7 |
| `1cf7363` | `chore(cli): verify cli/metrics.py slice 7 byte-determinism green (Slice 7/8)` | Slice 7 verify |
| `53f56f9` | `refactor(cli): rename rotation.py → archive.py and absorb archive group (Slice 8/8)` | Slice 8 |
| `05327d7` | `chore(cli): verify cli/archive.py slice 8 byte-determinism green (Slice 8/8)` | Slice 8 verify |
| `bde5f1b` | `chore(cli): fix lint+type debt from v1.3-cli-split mechanical split` | Post-integration fixup (30 unused imports, E402 carve-out, mypy strict carve-out for `flow_engineering.cli.*`) |
| `9228289` | `Merge pull request #41 from Rene-Kuhm/feature/v1.3-cli-split` | Final integration to `main` |

### 5.4 PR stack (chained 8-way stacked-to-tracker + integration)

```
                          main: 8577d9c (post workspace-health-advisor PR4)
                                  │
                                  ├──→ PR #32 (Slice 1)   — dabe321
                                  ├──→ PR #33 (Slice 2)   — d1b9ecf + f88b3a0 + b031310
                                  ├──→ PR #34 (integration Slices 1+2 → tracker)
                                  ├──→ PR #35 (Slice 3)   — aa2a955
                                  ├──→ PR #36 (Slice 4)   — 06fad84
                                  ├──→ PR #37 (Slice 5)   — f897ab4 + bc1cbcc
                                  ├──→ PR #38 (Slice 6)   — 0a723f2 + 8a767d8
                                  ├──→ PR #39 (Slice 7)   — a30f41c + 1cf7363
                                  ├──→ PR #40 (Slice 8)   — 53f56f9 + 05327d7
                                  │
                                  ├──→ PR #41 (integration 8/8 → main)   — bde5f1b (fixup) + 9228289 (merge)
                                  │         │
                                  │         │
                                  │    [ARCHIVE PHASE starts here]
                                  │         │
                                  │         │    root spec sync   → chore(openspec): archive v1.3-cli-split ...
                                  │         │      • openspec/specs/cli/spec.md (NEW root capability)
                                  │         │      • openspec/changes/v1.3-cli-split/ → openspec/changes/archive/2026-07-08-v1.3-cli-split/
                                  │         │      • openspec/changes/archive/2026-07-08-v1.3-cli-split/archive-report.md (NEW)
```

## 6. Residual split (carry-forward)

The inaugural `v1.3-cli-split` left `cli/__init__.py` at **1,621 LOC** (down from 5,337). The original proposal's "≤500 LOC after all slices" success criterion (proposal §Success Criteria line 87) was NOT met because the 8-sliced plan covered only the domain submodules; the top-level scaffold (`new`/`apply`/`verify`/`where`/`engram`/`watch` + `save`/`search`/`reindex`/`inspect` + module imports + `main`) is unaccounted for.

A follow-up `cli-residual-split` change is expected to:
- relocate `where_cmd` to `cli/where.py` (~235 LOC)
- relocate engram cluster (`save`/`search`/`reindex`/`inspect`) to `cli/engram.py` (~365 LOC)
- relocate top-level commands (`new`/`new_project`/`status`/`doctor`/`apply`/`verify`/`watch`/`memory_timeline`) to `cli/core.py` (~120 LOC)
- keep `cli/__init__.py` ≤ 500 LOC (Click-group stub + re-export barrel only)

This is the natural next mechanical-relocation slice. Each of the 3 follow-up submodules would be a new sub-capability in the `cli` family; the 5 root REQs (REQ-CLI-SPLIT-1..5) would govern them unchanged.

## 7. Future Changes

| Follow-up | Priority | Source | Scope |
|-----------|----------|--------|-------|
| `cli-residual-split` | MEDIUM | Proposal §"Open questions" Q1 + this spec §6 | Split the 1,621-LOC `cli/__init__.py` residual into `cli/where.py` + `cli/engram.py` + `cli/core.py` (3 chained PRs) to hit the ≤500 LOC success criterion |
| `cli-followup-lint-scope-tighten` | LOW | `bde5f1b` fixup | Reduce the `flow_engineering.cli.*` mypy/lint scope currently in `pyproject.toml` ([tool.ruff.lint.per-file-ignores] + [tool.mypy] override). The current carve-out covers the `main` import cycle (intentional, decorators ARE typed but `main` degrades to Any across the cycle); future tightening would split `main` into a typing-stable type alias. Low priority because the carve-out is correct as-is. |
| `metrics-namespace-rewrite` (REQ-V1.3.6) | LOW | Proposal §"Out of scope" | Rewrite `flow metrics` to drop the legacy flat-dump shim (preserved verbatim in `cli/metrics.py:77-78` per `apply-progress.md` §"Slice 7"). The shim is currently correct (preserves pre-split behavior) but conflates two output formats. |
| `drift-events-alias-removal` (REQ-V1.3.7) | LOW | Proposal §"Out of scope" | Remove the `flow drift-events` deprecated top-level group + 3 alias shims (preserved INTACT in `cli/drift.py` per `apply-progress.md` §"Slice 4" + REQ-V1.2.4 deprecation contract). |
| `archive-dead-code-removal` | LOW | Proposal §"Out of scope" | Remove the `archive()` function at pre-split `cli/__init__.py:320-349`. Currently in `cli/archive.py` (absorbed during Slice 8 rename). Low priority; user explicitly deferred. |

## 8. Cross-impact

- **`workspace/spec.md`** — no behavior changes. `cli/workspace.py` carries the same `workspace_health_cmd` + `workspace_status` + `workspace_dashboard` + 5 other subcommands; the public API at `flow_engineering.cli.workspace_health_cmd` is unchanged.
- **`decision-drift/spec.md`** — no behavior changes. `cli/drift.py` carries the same `drift_group` + `drift_run` + `drift_events_group` + 3 alias shims; `drift_events_alias_group` is preserved INTACT (REQ-V1.2.4 deprecation contract). The `_format_drift_events_text` re-export is preserved.
- **`prompt-registry/spec.md`** — no behavior changes. `cli/prompts.py` carries the same `prompts_group` + 4 subcommands + `CheckAction`; the `_GOLDEN_PROMPTS_DIR` re-export is preserved for the test seam.
- **`observability/spec.md`** — no behavior changes. `cli/metrics.py` carries the same `metrics_group` + 3 children + 2 helpers; the legacy flat-dump shim is preserved verbatim (REQ-V1.3.6 contract).
- **`flow-where/spec.md`** — no behavior changes. `where_cmd` is still in `cli/__init__.py`; future `cli-residual-split` will relocate it.
- **No new cross-family dependencies introduced.** The mechanical relocation did not add new cross-module references beyond what was already lazy-imported in the pre-split `cli/__init__.py` (e.g., `EngramClient` and `_default_save_backend` were already late-bound; the relocation just formalized the lazy-import pattern).

## 9. Archive status (per slice)

| Slice | Commit | LOC moved | Re-exports added | Public API verified | Tests verified | Status |
|-------|--------|-----------|------------------|---------------------|----------------|--------|
| 1 (`_shared.py`) | `dabe321` | ~124 | 4 (`_resolve_projects_root`, `_iter_project_subdirs`, `_DEFAULT_PROJECTS_ROOT_WIN`, `_DEFAULT_PROJECTS_ROOT_NIX`) | 6 names importable | 34/34 targeted workspace tests | ✅ SHIPPED |
| 2 (`workspace.py`) | `d1b9ecf` + `f88b3a0` + `b031310` | ~681 | 2 (`workspace_health_cmd`, `_summarize_workspace_status`) | 8 names importable | 34/34 + 331/331 CLI tests | ✅ SHIPPED |
| 3 (`project.py`) | `aa2a955` | ~528 | 2 (`_detect_project_markers`, `_git`) | 8 names importable | 34/34 + 316/316 CLI tests | ✅ SHIPPED |
| 4 (`drift.py`) | `06fad84` | ~825 | 1 (`_format_drift_events_text`) | 8 names importable | 20/20 drift + 34/34 targeted + 335/335 CLI tests | ✅ SHIPPED |
| 5 (`snapshot.py`) | `f897ab4` + `bc1cbcc` | ~377 | 0 (reached via `main.commands['snapshot']`) | 8 names importable | 24/24 snapshot + 335/335 CLI tests | ✅ SHIPPED |
| 6 (`prompts.py`) | `0a723f2` + `8a767d8` | ~781 | 1 (`_GOLDEN_PROMPTS_DIR` test seam) | 12 names importable | 38/38 prompts + 11/11 golden + 1434/1434 full suite | ✅ SHIPPED |
| 7 (`metrics.py`) | `a30f41c` + `1cf7363` | ~575 | 0 (reached via `main.commands['metrics']`) | 14 names importable | 30/30 metrics (2 pre-existing time-sensitive failures deselected) | ✅ SHIPPED |
| 8 (`archive.py` rename) | `53f56f9` + `05327d7` | ~194 (rename) + ~52 (extract) | 1 (`rotate_cmd`) | 14 names importable | All 14 names + `cli/rotation.py` shim verified | ✅ SHIPPED |
| Fixup (lint+type) | `bde5f1b` | (cleanup only) | (no API change) | 14 names importable | 1678/1680 pytest (2 pre-existing BDD failures per issue #22) | ✅ SHIPPED |

## 10. Skill Resolution

`paths-injected` — `sdd-archive/SKILL.md` read at session start (paths only; no other skills loaded for this archive).
