# Delta Spec: cli-split (mechanical relocation of `cli/__init__.py`)

> **Change**: `v1.3-cli-split` (sub-change e of `v1.3-platform-hardening`; mechanical relocation only).
> **Tracker**: `feature/v1.3-cli-split` (from `origin/main` @ `8577d9c`).
> **Builds on**: `openspec/changes/v1.3-cli-split/proposal.md` (8-slice chain, no behavior changes).
> **Domain**: NEW `cli-split` — describes the RELOCATION CONTRACT for splitting the Click monolith, not new CLI behavior. Slice applicability is marked with `[Slice-N]` tags; `[All Slices]` means the REQ applies to every PR in the chain.

## Purpose

`src/flow_engineering/cli/__init__.py` (5337 LOC on the working branch; 4695 LOC on `origin/main` @ `8577d9c`) is a single-file Click monolith. This change splits it into 8 domain submodules via `git mv` + a re-export barrel in `cli/__init__.py`. The relocation is purely mechanical: **no new logic, no behavior changes, no new tests**. The public API of `flow_engineering.cli` MUST remain stable for 60+ test files plus downstream consumers (`health.py`, `workspace_hygiene.py`).

## 1. Slice map (relocation order)

| Slice | New / renamed file | LOC moved | Anchor |
|-------|--------------------|-----------|--------|
| 1 | `cli/_shared.py` | ~250 | constants + `_resolve_projects_root` + `_iter_project_subdirs` + skill-version helpers |
| 2 | `cli/workspace.py` | ~700 | `workspace_group` + 6 sub-commands + `workspace_health_cmd` (anchor at line 3131) + hygiene helpers |
| 3 | `cli/project.py` | ~600 | `projects_group` + 3 sub-commands + `_git` + `_detect_project_markers` + detection helpers |
| 4 | `cli/drift.py` | ~700 | `drift_group` + `drift_run` + `drift_events_group` + alias shims + drift helpers (preserves `drift_events_alias_group` intact per "mechanical only") |
| 5 | `cli/snapshot.py` | ~350 | `snapshot_group` + 6 sub-commands + 3 snapshot helpers |
| 6 | `cli/prompts.py` | ~300 | `prompts_group` + sub-commands + `CheckAction` + prompts helpers |
| 7 | `cli/metrics.py` | ~500 | `metrics_group` + `summary`/`export`/`aggregate`; **legacy flat dump preserved verbatim** |
| 8 | `cli/archive.py` (rename of `cli/rotation.py`) | ~150 | `archive_group` + `archive_change_cmd` + `rotate_cmd`; `cli/rotation.py` deleted |

After all slices: `cli/__init__.py` ≤ 500 LOC (Click group + lazy re-export barrel only).

## 2. ADDED Requirements

### Requirement: REQ-CLI-SPLIT-1-MECHANICAL-RELOCATION `[All Slices]`

For each of the 8 slices, the relocation SHALL be purely mechanical:

- The source code block SHALL move via `git mv` (preserves history with rename detection > 90% similarity per `git diff -M --find-renames`).
- `cli/__init__.py` MUST add a re-export line `from flow_engineering.cli.<submodule> import <name>` for every public-API name that moved out (see REQ-CLI-SPLIT-2).
- `cli/__init__.py` MUST use **lazy imports** (`from . import <submodule> as _<submodule>`) for submodules that register Click groups/commands at import time, to prevent double-registration (`RuntimeError: Group <name> is already registered`).
- All 1405+ existing tests MUST pass unchanged (`uv run pytest` green per slice).

#### Scenario: Slice 1 — `cli/_shared.py` extracted via `git mv` and pytest green

- GIVEN `origin/main` @ `8577d9c` HEAD
- WHEN the slice-1 PR moves shared constants + `_resolve_projects_root` + `_iter_project_subdirs` + skill-version helpers from `cli/__init__.py` to `cli/_shared.py`
- AND adds a lazy import and re-exports in `cli/__init__.py`
- THEN `uv run pytest` exits 0 with the same pass count as `main`
- AND `git diff -M --find-renames=90%` reports ≥ 90% similarity for the moved block

#### Scenario: Slice 2 — `cli/workspace.py` carries the `workspace_health_cmd` anchor

- GIVEN slice 1 merged on `feature/v1.3-cli-split`
- WHEN slice 2 relocates lines 2894–3559 (incl. `workspace_health_cmd` + `_normalize_filter_rules` + `_HEALTH_FILTER_CHOICES` from the anchor at line 3131) to `cli/workspace.py`
- AND adds re-exports for `workspace_health_cmd`, `_summarize_workspace_status`, `_iter_project_subdirs`
- THEN `uv run pytest tests/unit/test_cli_workspace_health.py tests/unit/test_cli_workspace_status.py -v` exits 0
- AND `flow workspace health --json` runs without `NoSuchCommand` errors

#### Scenario: Slice 3 — `cli/project.py` re-exports `_detect_project_markers` and `_git` for downstream consumers

- GIVEN slice 2 merged
- WHEN slice 3 relocates `projects_group` + sub-commands + detection helpers (incl. `_git`, `_detect_project_markers`) to `cli/project.py`
- AND adds re-exports in `cli/__init__.py`
- THEN `from flow_engineering.cli import _detect_project_markers` still resolves (used by `health.py:538`)
- AND `from flow_engineering.cli import _git` still resolves (used by `workspace_hygiene.py:363`)

#### Scenario: Slice 4 — `cli/drift.py` preserves `drift_events_alias_group` intact

- GIVEN slice 3 merged
- WHEN slice 4 relocates `drift_group` + `drift_run` + `drift_events_group` + 3 alias shims to `cli/drift.py`
- AND re-exports `_format_drift_events_text`
- THEN `flow drift-events list` (deprecated group) still exits 0
- AND `uv run pytest tests/unit/test_cli_drift_events_list.py -v` passes

#### Scenario: Slices 5–7 — `cli/snapshot.py`, `cli/prompts.py`, `cli/metrics.py` mechanical moves

- GIVEN slice 4 merged
- WHEN slices 5/6/7 each relocate their respective submodules and add the required re-exports + lazy imports
- THEN the full pytest suite stays green across all three slices
- AND slice 7 (metrics) preserves the legacy `flow metrics` flat-dump path verbatim (lines 1545–1547 of pre-split `__init__.py`)

#### Scenario: Slice 8 — `cli/rotation.py` → `cli/archive.py` rename + late-import becomes top-of-file

- GIVEN slice 7 merged
- WHEN slice 8 renames `cli/rotation.py` to `cli/archive.py` and relocates `archive_group` + `archive_change_cmd` into it
- AND converts the late import `from flow_engineering.cli.rotation import rotate_cmd` into a normal top-of-file import in `cli/archive.py`
- AND deletes `cli/rotation.py`
- THEN `from flow_engineering.cli import rotate_cmd` still resolves
- AND `uv run pytest tests/unit/test_cli_rotation.py -v` passes

### Requirement: REQ-CLI-SPLIT-2-PUBLIC-API-PRESERVATION `[All Slices]`

The 8 public importable names from `flow_engineering.cli` MUST remain importable across all slices. Private helpers used by tests or downstream modules MUST also be re-exported to preserve existing call sites.

The 8 public names (verified via grep on `tests/` and `src/`):

1. `main` (61 test files + `cli/__init__.py` re-export)
2. `workspace_health_cmd` (1 test file)
3. `_detect_project_markers` (8 tests + `src/flow_engineering/health.py:538`)
4. `_format_drift_events_text` (2 tests)
5. `_iter_project_subdirs` (2 tests)
6. `_summarize_workspace_status` (2 tests)
7. `_git` (`src/flow_engineering/workspace_hygiene.py:363`)
8. `rotate_cmd` (1 test file + `cli/rotation.py` until Slice 8)

#### Scenario: `main` importable from `flow_engineering.cli` after each slice

- GIVEN the current `feature/v1.3-cli-split` HEAD after any merged slice
- WHEN a downstream consumer executes `from flow_engineering.cli import main`
- THEN `main` resolves to the same Click group instance it resolved to on `origin/main` @ `8577d9c`
- AND `main` has the same set of registered subcommands and groups

#### Scenario: `_detect_project_markers` preserves its return-value shape

- GIVEN `health.py:538` imports `_detect_project_markers` from `flow_engineering.cli`
- WHEN `_detect_project_markers(project_path)` is called with a project root
- THEN it returns a dict with the same keys it returned on `origin/main` (verified by `tests/unit/test_cli_projects.py`)

#### Scenario: `rotate_cmd` importable after Slice 8 rename

- GIVEN slice 8 merged: `cli/rotation.py` deleted, `cli/archive.py` created
- WHEN `from flow_engineering.cli import rotate_cmd` is executed
- THEN `rotate_cmd` resolves to the same callable previously imported from `flow_engineering.cli.rotation`

### Requirement: REQ-CLI-SPLIT-3-BYTEDETERMINISM-PRESERVED `[All Slices]`

The PR3 + PR4 byte-determinism invariant MUST continue to hold across all 8 slices. Specifically, `flow workspace health --json` and any `--no-color` output produced by the relocated subcommands MUST remain sha256-stable against the baseline captured on `origin/main` @ `8577d9c`.

#### Scenario: `flow workspace health --json` byte-identical to baseline

- GIVEN a fixed workspace fixture (e.g., `tests/fixtures/workspace-health-baseline/`)
- WHEN the slice is exercised with `flow workspace health --json` against the fixture
- THEN the sha256 of stdout equals the baseline sha256 captured on `origin/main` @ `8577d9c`
- AND any drift triggers a `pytest` failure in `tests/unit/test_cli_workspace_health.py`

#### Scenario: `--no-color` text output remains byte-identical

- GIVEN the same fixed workspace fixture
- WHEN the slice runs `flow workspace health --no-color` and `flow workspace status --no-color`
- THEN the sha256 of stdout equals the baseline sha256 captured on `origin/main` @ `8577d9c`
- AND no ANSI escape codes appear in stdout

### Requirement: REQ-CLI-SPLIT-4-ZERO-NEW-LOGIC `[All Slices]`

Each slice SHALL introduce no new functions, no behavior changes, and no new tests. The only acceptable diff per slice is:

- `git mv` of source code blocks (rename detection > 90% similarity)
- Re-export lines added to `cli/__init__.py`
- A lazy import line in `cli/__init__.py` for the new submodule
- The new submodule's own import block (no new third-party dependencies)

#### Scenario: Slice N introduces no new function names

- GIVEN slice N merged on `feature/v1.3-cli-split`
- WHEN `git diff origin/main...feature/v1.3-cli-split -- src/flow_engineering/cli/<submodule>.py` is run
- THEN the diff shows only `+def <name>` lines for names that already existed in `cli/__init__.py` at `origin/main`
- AND zero `+def <new_name>` lines appear

#### Scenario: Slice N introduces no new test files

- GIVEN slice N merged
- WHEN `git diff --stat origin/main...feature/v1.3-cli-split -- tests/` is run
- THEN no new files appear under `tests/`
- AND existing test files in `tests/unit/test_cli_*.py` show zero modifications

#### Scenario: Slice N diff is mechanical (rename detection)

- GIVEN slice N merged
- WHEN `git diff -M --find-renames=90% origin/main...feature/v1.3-cli-split --stat` is run
- THEN at least 90% of the LOC moved in this slice is reported as a rename (not add+delete)
- AND the new `<submodule>.py` is recognized by git as a rename of the corresponding `__init__.py` block

### Requirement: REQ-CLI-SPLIT-5-REVIEW-BUDGET-JUSTIFICATION `[Slices 2, 3, 4, 5, 7]`

Slices that exceed the 400-LOC review budget (5/8 slices per the proposal: 2, 3, 4, 5, 7) MUST include a "Mechanical relocation, not new logic" justification paragraph in the PR description. The paragraph MUST:

- Reference this spec (`openspec/changes/v1.3-cli-split/specs/cli-split/spec.md`).
- Reference the design.md for scope confirmation.
- Acknowledge the PR-review burden (5/8 slices exceed 400 LOC).
- Confirm the diff is a `git mv` (rename detection > 90% similarity), not new logic.
- State the number of new function names added (expected: 0).
- State the number of test files added (expected: 0).

#### Scenario: Slice 2 PR description includes the justification

- GIVEN slice 2 (`cli/workspace.py`, ~700 LOC moved) opens as a PR against `feature/v1.3-cli-split`
- WHEN the PR description is reviewed
- THEN the description contains the literal string "Mechanical relocation, not new logic"
- AND a link to `openspec/changes/v1.3-cli-split/specs/cli-split/spec.md` appears
- AND a link to `openspec/changes/v1.3-cli-split/design.md` appears
- AND the LOC count of the diff and the 400-LOC budget are both stated

#### Scenario: Slices under 400 LOC (1, 6, 8) do not require the justification

- GIVEN a slice with ≤ 400 LOC moved (Slice 1 `_shared.py` ~250, Slice 6 `prompts.py` ~300, Slice 8 `archive.py` ~150)
- WHEN the PR description is reviewed
- THEN the "Mechanical relocation, not new logic" paragraph is OPTIONAL
- AND the PR still MUST comply with REQ-CLI-SPLIT-1, -2, -3, -4

## 3. Out of scope (deferred to follow-up issues)

- REQ-V1.3.6: metrics namespace rewrite — legacy flat dump is preserved verbatim (Slice 7).
- REQ-V1.3.7: removal of the `drift-events` deprecated group + 3 alias shims (kept intact in Slice 4).
- Dead-code removal (`archive()` function at pre-split `__init__.py` lines 320–349).
- New CLI commands, new options, or new test files.

## 4. Cross-references

- Proposal: `openspec/changes/v1.3-cli-split/proposal.md`
- Exploration: `openspec/changes/v1.3-cli-split/explore.md`
- Design: `openspec/changes/v1.3-cli-split/design.md` (forthcoming)
- Tracker branch: `feature/v1.3-cli-split`
