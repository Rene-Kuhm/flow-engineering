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
[ ] Batch 0 — T0.1 slice-branch scaffold (1 chore commit)         — pending
[ ] Batch 1 — T1.1-T1.3 GraphLoader Protocol (4 commits)           — pending
[ ] Batch 2 — T2.1-T2.3 ObservationSource Protocol (4 commits)     — pending
[ ] Batch 3 — T3.1-T3.2 typed exception hierarchy (2 commits)      — pending
[ ] Batch 4 — T4.1-T4.2 SnapshotGraphMissing relocation (2 commits) — pending
[ ] Batch 5 — T5.1-T5.2 unable_reason + _DummyBackend removal (2)   — pending
[ ] Batch 6 — T6.1-T6.2 scan_change refactor + invariant (3 commits) — pending
[ ] Batch 7 — T7.1-T7.2 verify gates (CI only, no commits)          — pending
```

## Completed Tasks

_None yet — pre-apply scaffold._

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
- **D6 deviation** (flat module names vs locked spec's `drift/_graph_loader.py` package) is documented at `design.md` §11 D6 + flagged in the PR description for reviewer awareness. A follow-up `drift-detection-spec-align` micro-change is recommended AFTER Slice 1 verifies to align the spec wording with the implementation.
- **`_DummyBackend` removal** is internal-only — design's pre-flight `grep -rn "_DummyBackend" tests/` returned 0 matches. T5.2 re-verifies before the REFACTOR commit lands.
- **`SnapshotGraphMissing` re-export** is a 1-line PEP 562 `from ... import ... as ...` in `decision_drift.py`. The canonical class is unchanged at `snapshot_manager.py:81-101`. `cli/drift.py:351`'s `except decision_drift.SnapshotGraphMissing` block continues to work byte-identically.
- **D2 graceful degradation** (`raise SnapshotGraphMissing` when snapshot has no graph content) is PRESERVED as a `raise` at the scan boundary. It does NOT map to `unable_reason` per REQ-33 contract.
- **Batch 7 (verify gates)** has NO work-unit commits — T7.1 + T7.2 are CI verification steps executed by `sdd-verify` (or locally before PR open). The implementation is complete after Batch 6 commits land.
