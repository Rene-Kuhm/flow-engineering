# Apply Progress: v0.9.0-hardening — CLOSEOUT

**Date:** 2026-06-28
**Change:** `v0.9.0-hardening` (BREAKING release — close v0.8.0's 1-release compat shim window)
**Branch:** main
**Base HEAD (v0.9.0 apply start):** `a2ce3f5` (post-PR#2b push; 1232/1232 tests passing)
**Final HEAD:** post-apply-progress closeout commit
**Strict TDD:** ON throughout (per-task TDD per orchestrator pre-decision for high-risk compat shim removal)
**Status:** success — v0.9.0-hardening applied; 3 compat shims removed; 1232/1232 tests still passing

## Goal

Close v0.8.0's 1-release compat shim window per CHANGELOG v0.8.0 lines 43/44/46/74 commitment. Remove 3 compat shims:
- `Finding.from_legacy` classmethod (W1 — str→int coercion)
- `DriftReport.from_legacy` classmethod (W1 — float→ISO coercion)
- `classify_binding_legacy` 3-arg wrapper (W3 — backwards-compat shim)

Add Finding.__post_init__ int enforcement (W1 enforcement). Update capability spec + CHANGELOG + version bump.

## Cluster Summary

| Field | Value |
|-------|-------|
| Change name | `v0.9.0-hardening` |
| REQs covered | REQ-V9.1..V9.5 (5 REQs) |
| Tasks | 19 per-task strict TDD tasks |
| Batches | 3 (Sub-batch A: W1 removal; Sub-batch B: W3 removal + W1 enforcement; Sub-batch C: Docs + meta) |
| Commits | 12 work-unit commits (RED/GREEN/REFACTOR pairs + REFACTOR commits + closeout) |
| Test baseline | 1232 (pre-apply) |
| Test final | 1232 (post-apply; -2 tests removed via shim cleanup, +2 new tests via __post_init__ enforcement; net even) |
| BDD scenarios | unchanged |
| Ruff | clean on all changed files |
| Mypy | residual (10 errors expected per proposal R3; deferred to v1.0) |
| Working tree | clean post-closeout |
| Wall time | ~3-4h end-to-end |

## Sub-batch summary

### Sub-batch A — W1 removal (Finding.from_legacy + DriftReport.from_legacy)
- **Tasks:** T1.1..T1.6 (6 tasks)
- **Goal:** RED fixtures + GREEN removal + REFACTOR migration of 10 test sites
- **Commits (5):**
  - `9fb4111` chore(v0.9.0-hardening): REQ-V9.1 — RED+GREEN Finding.from_legacy shim removal
  - `d1b08a2` chore(v0.9.0-hardening): REQ-V9.1 — migrate 2 Finding(str) sites + delete 3 from_legacy fixtures
  - `3d4e0f3` chore(v0.9.0-hardening): REQ-V9.2 — RED+GREEN DriftReport.from_legacy shim removal
  - `44b0edd` chore(v0.9.0-hardening): REQ-V9.2 — migrate 8 DriftReport(scanned_at=0.0) sites + delete 3 from_legacy fixtures
  - `9ca3e80` chore(v0.9.0-hardening): REQ-V9.1+V9.2 cleanup — remove unused Any import
- **Files touched:** `src/flow_engineering/decision_drift.py` (deleted 2 classmethods), `tests/unit/test_cli_watch_drift.py` (2 sites), `tests/unit/test_decision_drift.py` (3 sites), `tests/unit/test_daemon_drift_events.py` (4 sites), `tests/unit/test_decision_drift_v080_migration.py` (3 fixtures deleted)
- **Tests:** -2 (legacy fixtures deleted)

### Sub-batch B — W3 removal + W1 enforcement
- **Tasks:** T2.1..T2.6 (6 tasks)
- **Goal:** classify_binding_legacy removal + Finding.__post_init__ coercion + mypy cleanup
- **Commits (3):**
  - `d016433` chore(v0.9.0-hardening): REQ-V9.3 — RED+GREEN classify_binding_legacy shim removal
  - `aed1ed1` chore(v0.9.0-hardening): REQ-V9.3 — migrate 10 classify_binding_legacy call sites + cleanup
  - `a84b686` feat(decision-drift): Finding.__post_init__ coerces decision_id to int (W1 enforcement)
- **Files touched:** `src/flow_engineering/decision_drift.py` (deleted classify_binding_legacy + added __post_init__), 11 test sites across test_decision_drift.py + test_decision_drift_v080_migration.py + test_cli_drift.py (2 coercion test assertions updated)
- **Tests:** +2 (W1 enforcement tests)

### Sub-batch C — Docs + meta
- **Tasks:** T3.1..T3.6 (6 tasks)
- **Goal:** spec sync + CHANGELOG + version bump + Drift note + ruff --fix + apply-progress closeout
- **Commits (4):**
  - `9c15fae` docs(spec): v0.9.0 final note — REQ-V9.5 migration guide (compat shim removal)
  - `120dba1` chore(release): v0.9.0 — CHANGELOG BREAKING entry + version bump 0.8.1 -> 0.9.0
  - `2410b03` docs(design): v0.9.0 resolution note — W1/W2/W3 closed (compat shim removal)
  - `87c52c3` fix(test): update v0.9.0 coercing test assertions to match int decision_id contract
- **Files touched:** `openspec/specs/decision-drift/spec.md`, `CHANGELOG.md`, `pyproject.toml`, `openspec/changes/v0.9.0-hardening/design.md` (W2 Drift note)
- **ruff --fix:** 30 files auto-formatted (this commit captured)

## Final closeout commit
This file (apply-progress/final.md) + commit.

## Files touched (cumulative, deduped)

| File | LOC delta | Sub-batches | Notes |
|------|-----------|-------------|-------|
| `src/flow_engineering/decision_drift.py` | ~-50 net | A + B | Removed Finding.from_legacy + DriftReport.from_legacy + classify_binding_legacy; added __post_init__ |
| `openspec/specs/decision-drift/spec.md` | +migration guide | C | v0.9.0 migration section |
| `CHANGELOG.md` | +v0.9.0 entry | C | BREAKING marker |
| `pyproject.toml` | version 0.8.1 -> 0.9.0 | C | minor bump |
| `openspec/changes/v0.9.0-hardening/design.md` | +W2 Drift note | C | Option B documentation |
| 11 test files | -8 net | A + B + C | Migrated legacy usage + ruff --fix auto-formatted 30 files |
| `openspec/changes/v0.9.0-hardening/apply-progress/final.md` | +NEW | C | This file |

## Shims removed (confirmed via grep)
```bash
grep -rn "from_legacy\|classify_binding_legacy" src/ tests/
# Result: 0 matches
```

## Carry-forwards NOT in v0.9.0 (deferred)
- **v1.0 follow-ups** (~2h): flow drift events CLI read-side + DriftEvent.decision_id:str consistency
- **v1.1 follow-ups** (~3-5h): DriftEventLog rotation + REQ-51/52/53
- **Tech debt** (~1-2h): 10 mypy residuals in decision_drift.py (proposal R3)
- **W2 Option B deviation** (LOW): graph_unavailable kept canonical + unable_reason field — Drift note in design.md documents decision + links to CHANGELOG v0.8.0 step 3

## Test results
- Pre-apply: 1232 tests passing
- Post-apply: **1232 tests passing** (net even: -2 removed + 2 added)
- 0 regressions
- BDD scenarios unchanged
- Ruff clean on all changed files
- Mypy: 10 residuals in decision_drift.py (expected per proposal R3; deferred)

## Timeout recovery
3 delegation timeouts during this apply phase:
1. `secret-gold-elephant` (15-min timeout) — completed Sub-batches A + B = 7 commits
2. `anxious-salmon-hoverfly` (15-min timeout) — completed failures fix + T2.5 + T2.6 + T3.1..T3.4 = 5 commits

Per timeout-recovery pattern (memory #185), both agents committed work before timeout. Apply-progress checkpoint at `sdd/v0.9.0-hardening/apply-progress` preserved state across gaps.

## Files (filesystem)
- `src/flow_engineering/decision_drift.py` (MODIFIED: shims removed, __post_init__ added)
- `tests/unit/test_cli_drift.py` (MODIFIED: coercion assertions updated)
- `tests/unit/test_decision_drift.py` (MODIFIED: legacy usage migrated)
- `tests/unit/test_decision_drift_v080_migration.py` (MODIFIED: legacy fixtures deleted)
- `tests/unit/test_cli_watch_drift.py` (MODIFIED: Finding(str) → Finding(int))
- `tests/unit/test_daemon_drift_events.py` (MODIFIED: DriftReport(scanned_at=0.0) → DriftReport(scanned_at=ISO))
- 25 other test files (MODIFIED: ruff --fix auto-format)
- `openspec/specs/decision-drift/spec.md` (MODIFIED: migration guide)
- `CHANGELOG.md` (MODIFIED: v0.9.0 entry)
- `pyproject.toml` (MODIFIED: version 0.9.0)
- `openspec/changes/v0.9.0-hardening/design.md` (MODIFIED: W2 Drift note)
- `openspec/changes/v0.9.0-hardening/apply-progress/final.md` (NEW: THIS FILE)

## Engram artifacts
- `sdd-init/flow-engineering` — sync_id `obs-a8a3544c95c44a48`
- `sdd/v0.9.0-hardening/explore` — sync_id `obs-83f5fcbf33433ff2`
- `sdd/v0.9.0-hardening/proposal` — sync_id `obs-259054ca037a428b`
- `sdd/v0.9.0-hardening/tasks` — sync_id `obs-6c621cad4fb4c6cd`
- `sdd/v0.9.0-hardening/apply-progress` (multiple checkpoints)

## Next recommended

`sdd-verify v0.9.0-hardening` → `sdd-archive v0.9.0-hardening` → `git push origin main` → **change closes**.

Then per loop mode: T3.13 PR#2b cleanup → v1.0 follow-ups → v1.1 follow-ups → tech debt.

## Acceptance criteria

- [x] All 19 tasks (T1.1..T3.6) complete on main
- [x] 3 compat shims removed (Finding.from_legacy, DriftReport.from_legacy, classify_binding_legacy)
- [x] Finding.__post_init__ coerces decision_id to int (W1 enforcement)
- [x] 1232/1232 tests passing
- [x] Ruff clean on changed files
- [x] pyproject version is 0.9.0
- [x] CHANGELOG v0.9.0 entry present (BREAKING)
- [x] Capability spec decision-drift/spec.md has v0.9.0 migration guide
- [x] W2 Option B Drift note added to design.md
- [x] 0 remaining references to from_legacy / classify_binding_legacy in src/ or tests/
- [x] Apply-progress closeout documented (THIS FILE)