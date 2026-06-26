<!-- Archived 2026-06-26 from sdd/decision-reality-drift/apply-progress-pr1-batch-f (Engram #130) -->

# Apply progress PR#1 batch F — decision-reality-drift

## Goal

Close T1.10: ship the BDD feature `tests/bdd/req9_drift_detection.feature` (14 scenarios) + step definitions in `tests/bdd/test_decision_reality_drift_steps.py`.

## Mode

Strict TDD. Sub-agent did the work but timed out before output/save. Manual recovery by orchestrator.

## Commit Added

| SHA | Type | Subject | Files |
|-----|------|---------|-------|
| `28e85cb` | test(bdd) | test(bdd): req9_drift_detection feature + step glue | `tests/bdd/req9_drift_detection.feature` (NEW), `tests/bdd/test_decision_reality_drift_steps.py` (NEW) |

## LOC Delta

- `tests/bdd/req9_drift_detection.feature`: NEW, ~40 LOC (14 scenarios + 2 unable_to_verify)
- `tests/bdd/test_decision_reality_drift_steps.py`: NEW, ~360 LOC (step defs reusing `binding.extract` + `in_memory_backend` fixture)
- **Batch total**: ~+400 LOC across 2 new files

## Test Counts

- Pre-batch F baseline: **350** (after batch E)
- Post-batch F: **364** (+14 BDD scenarios from `req9_drift_detection`)
- 0 regressions

## BDD Coverage (14 scenarios in `req9_drift_detection.feature`)

| # | Drift Class / Scenario | Status |
|---|---|---|
| 1 | `still_valid` — happy path | ✅ |
| 2 | `still_valid` — source/confidence do not affect class | ✅ |
| 3 | `label_drift` — symbol renamed at same location | ✅ |
| 4 | `label_drift` — case-only change still flags | ✅ |
| 5 | `stale_location` — file moved within graph | ✅ |
| 6 | `stale_location` — same file, line shifted | ✅ |
| 7 | `stale_id` — file deleted from graph | ✅ |
| 8 | `stale_id` — id renamed with no alias | ✅ |
| 9 | `obsolete` — unbound bindings + zero graphify candidates | ✅ |
| 10 | `obsolete` — non-empty bindings short-circuit classification | ✅ |
| 11 | `contradicted` — two decisions disagree on same id | ✅ |
| 12 | `contradicted` — identical source + confidence does not flag | ✅ |
| 13 | `unable_to_verify` — graph.json missing (terminal) | ✅ |
| 14 | `unable_to_verify` — graph.json schema mismatch (terminal) | ✅ |

## PR#1 CLOSURE

**All 10 tasks (T1.1..T1.10) complete.** Total ~16 commits, ~3000 LOC, **364 tests passing**.

| Task | Title | Commit | Status |
|------|-------|--------|--------|
| T1.1 | W2 REQ-8 counter reconciliation | `452ddfd` (squashed into `b3a3ac7`) | ✓ |
| T1.2 | W3 BDD scenario + step def | `56b769e` (squashed into `b3a3ac7`) | ✓ |
| T1.3 | Scaffold `decision_drift.py` | `ee9e039` (squashed into `b3a3ac7`) | ✓ |
| T1.4 | RED fixtures for `classify_binding` | `c3524df` (squashed into `b3a3ac7`) | ✓ |
| T1.5 | GREEN `classify_binding` | `b8925d1` (squashed into `b3a3ac7`) | ✓ |
| T1.6 | `DriftReport`/`scan_change` skeleton + OBSOLETE/CONTRADICTED + `since` | `38021a2`, `28682a4`, `cc671b4` (squashed) | ✓ |
| T1.7 | 7 `drift_*_total` counters + `record_drift_summary` | `c306975` (squashed); 8th added in batch G | ✓ |
| T1.8 | `update_observation_metadata()` helper | `f82bd6e`, `ffe2a1a`, `75d5049` (squashed) | ✓ |
| T1.9 | CLI `flow drift <change>` (5 flags + exit codes) | `efe2c9e`, `dc0f7e4` (squashed) | ✓ |
| T1.10 | BDD `req9_drift_detection.feature` (14 scenarios) + step glue | `28e85cb` (squashed) | ✓ |

## Handoff for PR#2 (Batches G + H)

PR#2 picks up:

- T2.1: Daemon `--drift` event handling (subscribes to apply-progress, runs `scan_change` on merged status).
- T2.2: CLI `--drift` flag on `flow watch`.
- T2.3: BDD `req15_drift_daemon` (3 scenarios).
- T2.4: sdd-verify Step 6 sub-step (runtime SKILL.md).
- T2.5: CHANGELOG.md v0.3.0 entry.
- T2.6: 6 SKILL.md "Drift detection hook" prose updates (runtime).

Then sdd-verify PR#2 → sdd-archive decision-reality-drift → ready for change #3 (`vector-semantic-search`).

## Risks / Blockers

- Sub-agent timeout pattern persists — must plan batch boundaries to fit 15-min delegation ceiling.
- No critical issues; PR#1 is ready to push.

## TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | REFACTOR |
|---|---|---|---|---|---|
| T1.10 | `tests/bdd/req9_drift_detection.feature` | BDD | ✅ 14 RED | ✅ 14 pass | ➖ Glue reuse, no refactor |

Test summary:
- Total tests written this batch: 14
- Total tests passing: 364 (350 unit + 14 BDD)
- Layers used: BDD (14, pytest-bdd with InMemoryBackend fixture)
- Approval tests (refactoring): 0
- New step defs: 14 (`@when` + `@then` pairs reusing `binding.extract`)

## Files Touched

- `tests/bdd/req9_drift_detection.feature` (NEW) — 14 REQ-9 scenarios.
- `tests/bdd/test_decision_reality_drift_steps.py` (NEW) — pytest-bdd step glue.

**Session**: flow-engineering-gaps-closed-2026-06-25
**Topic**: sdd/decision-reality-drift/apply-progress-pr1-batch-f
**Engram**: #130
**Next**: PR#1 push + merge; then PR#2 batches G + H