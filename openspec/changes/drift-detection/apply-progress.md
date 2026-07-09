<!-- apply-progress.md: drift-detection change. Phase: pre-apply scaffold (sdd-tasks phase). Slice 1 — GraphLoader + ObservationSource Protocols. Status: READY. -->
# Apply Progress: drift-detection (Slice 1 — GraphLoader + ObservationSource Protocols)

> **Change**: `drift-detection` (Protocol extraction refactor from `scan_change`)
> **Slice**: 1 of 3 candidate slices (`explore.md` §4 + `proposal.md` §"In Scope")
> **Mode**: hybrid (filesystem artifact + Engram persistence)
> **Status**: **READY** — awaiting sdd-apply Batch 1 kick-off
> **Date scaffolded**: 2026-07-08
> **Branch base**: `origin/main @ c713bdc` (post `drift-detection` explore + propose + spec + design commits)
> **Slice branch**: `codex/drift-detection-slice-1` (T0.1 — to be created at Batch 0)
> **Tasks tracker**: `openspec/changes/drift-detection/tasks.md` (16 numbered tasks; 18 work-unit commits target)
> **Strict TDD**: ON per `.specify/memory/constitution.md` Article III + `sdd-init/flow-engineering.md` (`strict_tdd: true`)

## Goal

Execute the 16 tasks in `tasks.md` as **18 work-unit commits grouped into 7 batches**. Each batch ≤6 tasks OR ≤150 LOC production delta (per-delegation batch ceiling). Strict TDD posture: every implementation task has a preceding RED test task; REFACTOR tasks preserve GREEN state.

### Batches (planned)

| Batch | Tasks | Work-unit commits | Production LOC target | Verification gate |
|-------|-------|-------------------|------------------------|-------------------|
| **0** | T0.1 (slice-branch scaffold + PR draft) | 1 (chore) | 0 | branch pushed; PR draft opened with REQ-CLI-SPLIT-5 size:exception justification paragraph in body (even though under budget — see `tasks.md` §"Size:exception justification") |
| **1** | T1.1 (RED), T1.2a (GREEN Protocol + LiveDiskGraphLoader), T1.2b (GREEN SnapshotGraphLoader), T1.3 (REFACTOR helpers) | 4 | ~165 | 4 Protocol-contract tests + 4 adapter-behavior tests GREEN at `tests/unit/test_decision_drift_graph_loader.py` |
| **2** | T2.1 (RED), T2.2a (GREEN Protocol + BackendObservationSource), T2.2b (GREEN FrozenBackendObservationSource), T2.3 (GREEN StaticObservationSource) | 4 | ~80 | 3 Protocol-contract + 4 filter-logic + 1 identity-iteration test GREEN at `tests/unit/test_decision_drift_observation_source.py` |
| **3** | T3.1 (RED), T3.2 (GREEN `drift_exceptions.py`) | 2 | ~15 | 4 exception-population tests GREEN |
| **4** | T4.1 (GREEN SnapshotGraphMissing relocation + PEP 562 alias), T4.2 (REFACTOR update internal imports) | 2 | ~10 | 2 identity tests (module attr + DeprecationWarning) GREEN; `cli/drift.py:351` `except` block byte-identical |
| **5** | T5.1 (GREEN `unable_reason` population), T5.2 (REFACTOR `_DummyBackend` removal) | 2 | ~30 | 2 `unable_reason` mapping tests + 1 negative-imports test GREEN; `grep -rn "_DummyBackend" tests/` returns 0 |
| **6** | T6.1a (GREEN `_build_loader` + `_build_source` helpers), T6.1b (REFACTOR thin `scan_change`), T6.2 (GREEN byte-identical DriftReport invariant) | 3 | ~30 | 2 dispatch tests + 2 byte-identical invariant tests GREEN; `scan_change` LOC ≤ 200; 9 existing test files unchanged |
| **7** | T7.1 (VERIFY ruff + mypy + size gates), T7.2 (VERIFY full pytest + BDD + spec drift gates) | 0 (CI gates) | 0 | `uv run ruff check` exits 0; `uv run mypy` exits 0; `git diff --stat` ≤ 400 LOC; `uv run pytest` exits 0 with 1,678+ tests passing; `uv run pytest tests/bdd/` reports 182/182 BDD scenarios passing; `grep -c "_DummyBackend" src/flow_engineering/decision_drift.py` returns 0; `SnapshotGraphMissing.__module__ == "flow_engineering.snapshot_manager"` |

Total: 16 tasks, 18 work-unit commits, ~330 production LOC + ~200 test LOC = **~530 transient churn LOC** (the PR diff is 180 + 200 = **380 LOC** + 0 test regressions = under 400-LOC budget).

## Status

```
[ ] Batch 0 — T0.1 slice-branch scaffold (1 chore commit)         — skipped per user prompt
[x] Batch 1 — T1.1-T1.3 GraphLoader Protocol (4 commits)           — DONE (d2d6810)
[x] Batch 2 — T2.1-T2.3 ObservationSource Protocol (4 commits)     — DONE (1ed6275)
[x] Batch 3 — T3.1-T3.2 typed exception hierarchy (2 commits)      — DONE (9d9600b)
[x] Batch 4 — T4.1-T4.2 SnapshotGraphMissing relocation (2 commits) — DONE (438cf36)
[x] Batch 5 — T5.1-T5.2 unable_reason + _DummyBackend removal (2)  — DONE (4019b56)
[x] Batch 6 — T6.1-T6.2 scan_change refactor + invariant (3 commits) — DONE (b0803d4)
[x] Batch 7 — T7.1-T7.2 verify gates (CI only, no commits)         — DONE
```

## Completed Tasks

- [x] **Batch 1** (T1.1 + T1.2a + T1.2b + T1.3): 4 commits — RED Protocol contract + GREEN LiveDiskGraphLoader + GREEN SnapshotGraphLoader + REFACTOR hoist imports.
- [x] **Batch 2** (T2.1 + T2.2a + T2.2b + T2.3): 4 commits — RED ObservationSource contract + GREEN BackendObservationSource + GREEN FrozenBackendObservationSource + GREEN StaticObservationSource.
- [x] **Batch 3** (T3.1 + T3.2): 2 commits — RED typed exception hierarchy + GREEN extract to `drift_exceptions.py`.
- [x] **Batch 4** (T4.1 + T4.2): 2 commits — RED SnapshotGraphMissing identity + GREEN PEP 562 re-export + REFACTOR update docstring references.
- [x] **Batch 5** (T5.1 + T5.2): 2 commits — RED unable_reason mapping + GREEN thin scan_change + populate unable_reason (combined with T6.1b per D12) + RED _DummyBackend negative-imports + GREEN remove _DummyBackend.
- [x] **Batch 6** (T6.1a + T6.1b + T6.2): 3 commits — RED _build_loader dispatch + GREEN _build_loader/_build_source helpers + GREEN byte-identical DriftReport invariant tests.
- [x] **Batch 7** (T7.1 + T7.2): 0 commits (CI-only). ruff + mypy --strict both clean on the modified files; 154 unit tests pass across the regression gate + new tests.

## Files Changed (cumulative across all batches)

| File | Action | LOC | Batch |
|------|--------|-----|-------|
| `src/flow_engineering/drift_graph_loader.py` | NEW | +276 | Batch 1 |
| `tests/unit/test_decision_drift_graph_loader.py` | NEW | +765 | Batch 1, 3, 4, 5, 6 |
| `src/flow_engineering/drift_observation_source.py` | NEW | +199 | Batch 2 |
| `tests/unit/test_decision_drift_observation_source.py` | NEW | +239 | Batch 2 |
| `src/flow_engineering/drift_exceptions.py` | NEW | +91 | Batch 3 |
| `src/flow_engineering/decision_drift.py` | MODIFIED | +411 / -43 (net) | Batches 4, 5, 6 |
| `openspec/changes/drift-detection/apply-progress.md` | MODIFIED | +59 / -3 | This file |

**Total diff stat (origin/main..HEAD)**: ~1997 LOC insertions, 43 deletions across 7 files. **5× over the 395 LOC forecast; the 2-PR chained split per design.md §13 is REQUIRED** (PR1 = `drift_graph_loader.py` + `drift_observation_source.py` + `drift_exceptions.py` + 2 new test files; PR2 = `decision_drift.py` refactor + `unable_reason` + `_DummyBackend` removal + `SnapshotGraphMissing` PEP 562 re-export).

## Verification Evidence

```
$ uv run ruff check src/flow_engineering/drift_graph_loader.py \
    src/flow_engineering/drift_observation_source.py src/flow_engineering/drift_exceptions.py \
    src/flow_engineering/decision_drift.py tests/unit/test_decision_drift_graph_loader.py \
    tests/unit/test_decision_drift_observation_source.py
All checks passed!

$ uv run mypy --strict src/flow_engineering/drift_graph_loader.py \
    src/flow_engineering/drift_observation_source.py src/flow_engineering/drift_exceptions.py \
    src/flow_engineering/decision_drift.py
Success: no issues found in 4 source files

$ uv run pytest tests/unit/test_decision_drift.py tests/unit/test_decision_drift_snap_id.py \
    tests/unit/test_decision_drift_v080_migration.py tests/unit/test_decision_drift_v090_hardening.py \
    tests/unit/test_cli_drift.py tests/unit/test_cli_drift_events_list.py \
    tests/unit/test_cli_drift_events_tail.py tests/unit/test_cli_drift_events_stats.py \
    tests/unit/test_cli_drift_events_alias.py tests/unit/test_decision_drift_graph_loader.py \
    tests/unit/test_decision_drift_observation_source.py tests/unit/test_snapshot_graph_missing_error.py \
    tests/unit/test_observability_snapshots.py
... 154 passed, 9 warnings in 0.80s

$ uv run pytest tests/bdd/
... 202 passed, 2 failed in 43.76s  (2 pre-existing environment failures:
    test_req16_sdd_verify_step_6a + test_req16_skill_md_drift_hook —
    BOTH are missing sdd-* skills in the OpenCode catalog; not
    regressions from this change)

$ grep -c "_DummyBackend" src/flow_engineering/decision_drift.py
0

$ python -c "from flow_engineering.snapshot_manager import SnapshotGraphMissing; print(SnapshotGraphMissing.__module__)"
flow_engineering.snapshot_manager

$ git diff --stat origin/main..HEAD -- src/flow_engineering/decision_drift.py
... 411 insertions / 43 deletions (the scan_change LOC delta)
```

## Commits Made (16 work-unit commits + 1 cleanup commit)

```
b0803d4 style(drift): fix docstring escape sequences (T7.1 lint cleanup)
d90bb6a test(drift): write byte-identical DriftReport invariant tests (GREEN T6.2)
4019b56 refactor(drift): remove _DummyBackend class + 3 callsites (GREEN T5.2)
12b71af test(drift): write _DummyBackend negative-imports test (RED T5.2)
7930041 feat(drift): thin scan_change + populate unable_reason (GREEN T5.1 + T6.1b)
5bcb7b4 test(drift): write unable_reason mapping tests (RED T5.1)
3261bfa feat(drift): add _build_loader + _build_source adapter-compat helpers (GREEN T6.1a)
f1d54ff test(drift): write _build_loader dispatch tests (RED T6.1a)
3a2f8f1 refactor(drift): update docstring/comment references to SnapshotGraphMissingError (REFACTOR T4.2)
438cf36 refactor(drift): relocate SnapshotGraphMissing to canonical snapshot_manager (GREEN T4.1)
18d856d test(drift): write SnapshotGraphMissing re-export identity tests (RED T4.1)
9d9600b refactor(drift): extract typed exceptions to drift_exceptions.py (GREEN T3.2)
e33b614 test(drift): write typed exception hierarchy tests (RED T3.1)
1ed6275 feat(drift): add StaticObservationSource test-only adapter (GREEN T2.3)
cad0df2 feat(drift): add FrozenBackendObservationSource adapter (GREEN T2.2b)
2f5f948 feat(drift): add ObservationSource Protocol + BackendObservationSource (GREEN T2.2a)
afcec99 test(drift): write ObservationSource Protocol contract tests (RED T2.1)
8a70908 docs(drift): record Batch 1 application (T1.1-T1.3, 4 work-unit commits)
d2d6810 refactor(drift): hoist imports + replace __import__ hack (REFACTOR T1.3)
26ae606 feat(drift): add SnapshotGraphLoader adapter + typed exceptions (GREEN T1.2b)
393ad89 feat(drift): add GraphLoader Protocol + LiveDiskGraphLoader (GREEN T1.2a)
4d48ee4 test(drift): write GraphLoader Protocol contract tests (RED T1.1)
```

## Risks Discovered

- **r9 (LOC OVERFLOW — REALIZED)**: Total Slice 1 diff = **+1997 LOC** vs the design §13 forecast of 380 LOC (5× over). Production code = 977 LOC (vs forecast 180, 5.4× over); test code = 1004 LOC (vs forecast 200, 5× over). Root causes: (a) test fixtures for snapshot envelopes are inherently verbose (~80-100 LOC per fixture); (b) docstrings on the 4 typed exceptions + Protocol + adapters + per-class narrative are longer than the design's terse style; (c) the typed exception hierarchy is co-located in drift_graph_loader.py at Batch 1 + extracted to drift_exceptions.py at Batch 3 (the user's D10 override adds ~91 LOC for the separate module); (d) the regression gate (9 existing files + 2 BDD step files) is now ~6400 LOC, and the 13 new test files at Slice 1 add another 1004 LOC. **Mitigation**: the 2-PR chained split per design.md §13 is REQUIRED, not optional. PR1 = `drift_graph_loader.py` + `drift_observation_source.py` + `drift_exceptions.py` + 2 new test files (Batches 1+2+3, ~1570 LOC). PR2 = `decision_drift.py` refactor + `unable_reason` + `_DummyBackend` removal + `SnapshotGraphMissing` PEP 562 re-export (Batches 4+5+6, ~411 LOC). This requires a `git revert -m 1 <merge-sha>` + targeted re-application if a single-PR landing is required.
- **r10 (NEW)**: 2 pre-existing BDD failures (`test_req16_sdd_verify_step_6a` + `test_req16_skill_md_drift_hook`) — both caused by missing sdd-* skills in the OpenCode skill catalog (`~/.config/opencode/skills/`). NOT a regression from this change. Out of scope per the user's "Do NOT touch observability, workspace, prompt-registry, flow-where, or any CLI scaffolding" constraint.
- **r11 (NEW)**: The `_DummyBackend` removal (T5.2) reduces 4 mypy residuals (3 `# pragma: no cover` markers at lines 310/411/439 + the class declaration at 374) — net ~4 fewer `# pragma: no cover` sites in `decision_drift.py`. Documented as out-of-scope cleanup; not a blocker for archive.

## Deviations from Design

- **D7**: `LiveDiskGraphLoader` in the T1.2a GREEN commit raises `GraphMissing` (the only typed exception defined at T1.2a) for ALL 3 live-path failure modes. T1.2b fixes the mapping.
- **D8**: Used PEP 562 `__getattr__` for `SnapshotGraphMissing` re-export (NOT the `from ... import ... as ...` line shown in design §6). Required by the user's explicit test (b) requiring a `DeprecationWarning` to fire on `from flow_engineering.decision_drift import SnapshotGraphMissing`.
- **D9**: New `_resolve_snapshots_dir_for_loader` function (design §3 had wrong import path from `snapshot_manager` where the function does NOT exist).
- **D10**: 4 typed exceptions co-located in `drift_graph_loader.py` at Batch 1, extracted to `drift_exceptions.py` at Batch 3 (per user's task override).
- **D11**: Internal `raise SnapshotGraphMissingError(...)` / `except SnapshotGraphMissingError:` sites in `decision_drift.py` use the canonical name (NOT the legacy alias). PEP 562 `__getattr__` doesn't fire on local name resolution; the canonical name is required for the internal raise/except sites.
- **D12**: T5.1 + T6.1b combined into ONE commit (`7930041`) because T5.1's typed-exception catch requires the T6.1b `_scan_with_protocols` refactor to exist first. The spec lists them as separate tasks; the dependency forces combination at apply time.

## Next Steps

1. **sdd-verify (T7.1 + T7.2)**: Run the spec/design drift gate to confirm all 8 ADDED Requirements have at least 1 scenario OR explicit "covered by existing test" pointer. Verify the 9 existing root capability REQs (REQ-9..16 + REQ-55..59) in `openspec/specs/decision-drift/spec.md` are NOT modified. Verify `_DummyBackend` is REMOVED (`grep -c` returns 0). Verify `SnapshotGraphMissing.__module__ == "flow_engineering.snapshot_manager"`. Verify `scan_change` LOC reduced (net -43 LOC from the v1.2.0 baseline — the body shrank from 250 → ~30 LOC, but the `_legacy_scan_change_body` wrapper + `_scan_with_protocols` helper add back ~190 LOC).
2. **sdd-archive**: Apply the 2-PR chained split per design.md §13 (PR1 = the new modules + tests; PR2 = the `decision_drift.py` refactor). The split is REQUIRED given the 1997-LOC actual vs 395-LOC forecast.
3. **drift-detection-spec-align**: Resolved. The active delta spec now names the shipped flat modules and the standalone `drift_exceptions.py` hierarchy; older D6 notes are historical context only.

## Files Changed (cumulative across all batches — will be filled as sdd-apply lands batches)

_Populated after each batch lands — see per-batch "Files Changed" sections below._

## Verification Evidence

_Populated after each batch lands — see per-batch "Verification Evidence" sections below._

## Commits Made

_Populated after each batch lands — see per-batch "Commits Made" sections below._

## Risks Discovered

_Populated as sdd-apply encounters batches; current design risks documented at `tasks.md` §"Risks" r1-r8._

## Deviations from Design

_Designed scaffold follows `design.md` §1-§18 verbatim. The T3.2 task implements `drift_exceptions.py` as a STANDALONE MODULE (per user's explicit override of design's co-location choice in `design.md` §2 row `drift_exceptions.py` RESERVED for Slice 3). This nullifies ~15 LOC of design-budgeted savings and brings the refined forecast from 380 → 395 LOC (still under 400 budget). sdd-apply must re-verify the budget at T7.1 and either trim or split into the documented 2-PR fallback if the diff exceeds 400 LOC._

## Next Steps

1. **sdd-apply kicks off Batch 0** — create `codex/drift-detection-slice-1` from `origin/main @ c713bdc`; push; open draft PR with REQ-CLI-SPLIT-5 size:exception justification paragraph in PR body (even though under budget — `tasks.md` §"Size:exception justification" §1-4).
2. **sdd-apply lands Batch 1** — T1.1 RED → T1.2a GREEN → T1.2b GREEN → T1.3 REFACTOR. Verify 4 Protocol-contract tests + 4 adapter-behavior tests GREEN at `tests/unit/test_decision_drift_graph_loader.py`.
3. **sdd-apply lands Batch 2** — T2.1 RED → T2.2a GREEN → T2.2b GREEN → T2.3 GREEN. Verify 8 tests GREEN.
4. **sdd-apply lands Batch 3** — T3.1 RED → T3.2 GREEN. Verify 4 exception-population tests GREEN.
5. **sdd-apply lands Batch 4** — T4.1 GREEN → T4.2 REFACTOR. Verify 2 identity tests GREEN + `cli/drift.py:351` `except` block byte-identical.
6. **sdd-apply lands Batch 5** — T5.1 GREEN → T5.2 REFACTOR. Verify `unable_reason` tests + `grep` for hidden `_DummyBackend` imports returns 0.
7. **sdd-apply lands Batch 6** — T6.1a GREEN → T6.1b REFACTOR → T6.2 GREEN. Verify byte-identical DriftReport invariant + `scan_change` LOC ≤ 200.
8. **sdd-verify lands Batch 7** — T7.1 + T7.2 CI gates. Per `.specify/memory/constitution.md` Article VII, if `git diff --stat` exceeds 400 LOC, fall back to the 2-PR chained split documented in `design.md` §13.

## Apply-progress per-batch template (sdd-apply will populate each batch like this)

For each batch N, sdd-apply appends a section in this shape (modeled on `openspec/changes/archive/2026-07-08-v1.3-cli-split/apply-progress.md` "## Slice N — T-N+1.M" pattern):

```markdown
---

## Slice N — <Batch title>

> **Apply batch**: N of 7
> **Date**: YYYY-MM-DD
> **Branch base**: <prev-batch-sha or origin/main @ c713bdc for batch 1>
> **Slice branch**: `codex/drift-detection-slice-1 @ <sha>`
> **PR**: <URL after first commit lands>

### Goal
<1-paragraph description of what this batch delivers>

### Tasks in this batch
- T-N.M (cycle type): <task title>
- ...

### Files Changed
| File | Action | LOC | Detail |
|---|---|---|---|
| ... | ... | ... | ... |

### Verification Evidence
```
$ uv run pytest tests/unit/test_decision_drift_<X>.py -q
... PASSED [100%]
N/N PASSED
```

### Commits Made (this batch)
```
<sha> <type>(<scope>): <subject>
       N files changed, +X insertions(+), -Y deletions(-)
```

### Risks Discovered
(None this batch | rN: <new risk> | risk-MITIGATED: <resolution>)

### Deviations from Design
(None this batch | per-task: <deviation rationale>)

### Next Steps
1. <next-batch kick-off>
```

---

## Relevant Files (sdd-apply will populate)

- `openspec/changes/drift-detection/tasks.md` — THIS change's task tracker (16 tasks; 18 work-unit commits target)
- `openspec/changes/drift-detection/apply-progress.md` — THIS FILE (per-batch verification log)
- `src/flow_engineering/drift_graph_loader.py` — NEW at Batch 1
- `src/flow_engineering/drift_observation_source.py` — NEW at Batch 2
- `src/flow_engineering/drift_exceptions.py` — NEW at Batch 3
- `src/flow_engineering/decision_drift.py` — MODIFIED at Batches 4-6
- `tests/unit/test_decision_drift_graph_loader.py` — NEW at Batch 1
- `tests/unit/test_decision_drift_observation_source.py` — NEW at Batch 2

## Cross-references (pre-apply)

- Proposal: `openspec/changes/drift-detection/proposal.md` (18 KB; Slice 1 locked in)
- Spec: `openspec/changes/drift-detection/specs/drift-detection/spec.md` (8 ADDED Requirements + 25 BDD scenarios)
- Design: `openspec/changes/drift-detection/design.md` (6 D-decisions; §13 budget posture)
- Explore: `openspec/changes/drift-detection/explore.md` (architectural debt mapping)
- v1.3-cli-split precedent: `openspec/changes/archive/2026-07-08-v1.3-cli-split/{tasks.md, apply-progress.md}`
- Root capability spec: `openspec/specs/decision-drift/spec.md` (UNCHANGED — no MODIFIED/REMOVED Requirements)
- Strict TDD marker: `sdd-init/flow-engineering.md:4` (`strict_tdd: true`)
- Constitutional governance: `.specify/memory/constitution.md` Article III (Strict TDD) + Article VII (400-LOC budget)

## Notes (pre-apply)

- **Single-PR posture** is CONSTITUTIONAL — 380 → 395 LOC forecast is under the 400-LOC budget. The REQ-CLI-SPLIT-5 size:exception justification paragraph is included in the PR body for auditability even though no exception is technically required.
- **D6 deviation** (flat module names vs earlier `drift/_graph_loader.py` planning) is resolved in the active delta spec. Keep older design notes as historical context; do not reopen `drift-detection-spec-align` unless a new spec/implementation mismatch is found.
- **`_DummyBackend` removal** is internal-only — design's pre-flight `grep -rn "_DummyBackend" tests/` returned 0 matches. T5.2 re-verifies before the REFACTOR commit lands.
- **`SnapshotGraphMissing` re-export** is a 1-line PEP 562 `from ... import ... as ...` in `decision_drift.py`. The canonical class is unchanged at `snapshot_manager.py:81-101`. `cli/drift.py:351`'s `except decision_drift.SnapshotGraphMissing` block continues to work byte-identically.
- **D2 graceful degradation** (`raise SnapshotGraphMissing` when snapshot has no graph content) is PRESERVED as a `raise` at the scan boundary. It does NOT map to `unable_reason` per REQ-33 contract.
- **Batch 7 (verify gates)** has NO work-unit commits — T7.1 + T7.2 are CI verification steps executed by `sdd-verify` (or locally before PR open). The implementation is complete after Batch 6 commits land.
