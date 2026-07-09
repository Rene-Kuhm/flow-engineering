<!-- proposal.md: drift-detection change. Phase: propose (sdd-propose). Source: explore.md (Slice 1 of 3 candidate slices). NOT a design / spec / tasks doc. -->
# Proposal: drift-detection architectural refactor (Slice 1 — Extract GraphLoader + ObservationSource protocols)

**Change**: `drift-detection` (new)
**Parent**: `openspec/changes/drift-detection/explore.md`
**Authoring**: sdd-propose sub-agent, 2026-07-08
**Mode**: hybrid (filesystem artifact + Engram persistence)
**Strict TDD**: ON (per `sdd-init/flow-engineering.md`)

## Intent

`scan_change` in `src/flow_engineering/decision_drift.py:485-734` is a 250-LOC orchestrator that couples 7 distinct responsibilities — graph loading, snapshot-pinned resolution, observation sourcing, observation filtering, classification, contradiction re-classification, and report aggregation — into a single function with 4 separate `except Exception: continue/pass` blocks that swallow every failure mode uniformly. The capability spec (`openspec/specs/decision-drift/spec.md:47`) explicitly anticipates future deltas ("per-finding graph_unavailable refinement, cross-project drift federation, OTel push") that all require a seam between classification (pure) and orchestration (I/O). This change extracts that seam by introducing 2 narrow `Protocol` types — `GraphLoader` and `ObservationSource` — that `scan_change` consumes as collaborators, eliminating the `_DummyBackend` fixture-as-type smell and surfacing the previously-silent `unable_reason` field. No public API changes; no spec-level behavior changes; no BDD scenario churn.

## Scope

### In Scope (Slice 1)

1. **`GraphLoader` Protocol + 2 concrete adapters** (`LiveDiskGraphLoader`, `SnapshotGraphLoader`) in NEW `src/flow_engineering/drift/_graph_loader.py` module.
2. **`ObservationSource` Protocol + 1 concrete adapter** (`BackendObservationSource`) in NEW `src/flow_engineering/drift/_observation_source.py` module.
3. **`scan_change` refactor** to consume the 2 protocols via an internal adapter. Public signature `(change_name, *, graph_json_path, backend, include_obsolete, since, snap_id)` PRESERVED unchanged.
4. **`unable_reason` population** in `DriftReport` (currently always `None`) — populate from the new typed exceptions (`GraphMissing`, `GraphMalformed`, `PermissionDenied`, `SnapshotEnvelopeCorrupt`).
5. **Remove `_DummyBackend`** (replaced by direct `Iterable[dict]` consumption).
6. **Move `SnapshotGraphMissing`** to `snapshot_manager.py` as canonical; `decision_drift.py` re-exports for backward compatibility with v1.1.6 1-release alias convention.
7. **New unit tests** in `tests/unit/test_decision_drift_graph_loader.py` + `tests/unit/test_decision_drift_observation_source.py` (Protocol contract tests + adapter behavior tests).
8. **No spec delta required** — this is a pure refactor. `decision-drift/spec.md` REQ-9..16 wording stays valid.

### Out of Scope (deferred to follow-up SDD changes)

| Deferred | Why separate change |
|----------|---------------------|
| Slice 2 (unified JSONL rotation helper for `drift_events.jsonl` + `metrics.jsonl`) | Independent of Slice 1; ~80 LOC; benefits from its own focused PR |
| Slice 3 (per-finding `graph_unavailable` refinement + new counter + delta spec + new BDD scenarios) | Requires Slice 1's typed exception hierarchy as a prerequisite; introduces new REQ (REQ-DD-1); benefits from delta-spec-driven SDD cycle |
| OTel push exporter | External dep (`opentelemetry-sdk`); requires deps approval + dedicated spec |
| Cross-project drift federation | New feature, not refactor; needs design spike |
| `decision_drift.py` file split (4 submodules) | Mechanical; mirrors v1.3-cli-split pattern but tightly coupled — splitting without an extraction-first creates the same god-module anti-pattern in 4 places |
| `_write_back_findings` lazy-import refactor in `cli/drift.py` | Slice 4 v1.3-cli-split artifact (Engram #2041); orthogonal to drift detection |

## Capabilities

### Modified Capabilities

- `decision-drift` — NO requirement changes. Refactor only. REQ-9..16 + REQ-55..59 wording remains valid.

### New Capabilities

- None. This change is structural, not behavioral. The `cli` family (`openspec/specs/cli/spec.md`) already covers structural REQs (REQ-CLI-SPLIT-1..5); the drift detection extraction falls under the same structural discipline. **No new capability family, no new root REQ.**

## Approach

**Extract 2 narrow `Protocol` types and refactor `scan_change` to consume them as collaborators.**

### Architecture Before

```
scan_change(change_name, *, graph_json_path, snap_id, backend, since, include_obsolete)
├── [inline] validate kwargs (snap_id × backend mutual exclusion)
├── [inline] load_graph(graph_json_path=..., snap_id=...) → (nodes, id_map, mtime)
│   ├── [inline] live disk path
│   └── [inline] snapshot path → _load_graph_from_snapshot → SnapshotManager.show(_DummyBackend)
├── [inline] acquire observation source (InMemoryBackend default OR _frozen_backend_from_snapshot)
├── [inline] filter observations by topic_key prefix + created_at cutoff
├── [inline] per-observation loop: extract_code_refs + classify_binding + OBSOLETE branch
├── [inline] _detect_contradicted post-pass
└── [inline] build DriftReport
```

### Architecture After

```
scan_change(change_name, *, graph_json_path, snap_id, backend, since, include_obsolete)
│   [public kwargs API UNCHANGED — internal adapter dispatches]
└── _scan_with_protocols(loader: GraphLoader, source: ObservationSource, ...)
    ├── loader.load() → (nodes, id_map, mtime) | raises typed exception
    ├── source.iter_observations() → Iterable[observation]
    ├── filter + classify + detect_contradicted (unchanged logic)
    └── build DriftReport(..., unable_reason=loader.last_reason)
```

**Type contracts (NEW)**:

```python
class GraphLoader(Protocol):
    def load(self) -> tuple[dict | None, dict | None, float | None]: ...
    # Raises: GraphMissing, GraphMalformed, PermissionDenied, SnapshotEnvelopeCorrupt

class ObservationSource(Protocol):
    def iter_observations(self) -> Iterable[dict]: ...
```

**Concrete adapters (NEW)**:

- `LiveDiskGraphLoader(graph_json_path: Path)` — wraps current `load_graph` happy path.
- `SnapshotGraphLoader(snap_id: str)` — wraps current `_load_graph_from_snapshot`, drops `_DummyBackend`, accepts `snapshot_manager.show()` directly.
- `BackendObservationSource(backend: EngramBackend | None)` — wraps current `backend.iter_observations()` default + filter logic.

**Adapter dispatch (NEW, internal)**:

```python
def _build_loader(*, graph_json_path, snap_id) -> GraphLoader:
    if snap_id is not None:
        return SnapshotGraphLoader(snap_id)
    if graph_json_path is None:
        return LiveDiskGraphLoader(DEFAULT_GRAPH_JSON)  # produces GraphMissing on .load()
    return LiveDiskGraphLoader(graph_json_path)
```

**Public API** (`scan_change`, `load_graph`, `classify_binding`, `DriftClass`, `Finding`, `DriftReport`): UNCHANGED. All 9 test files (1 600+ LOC) keep their existing import sites working.

### Why this approach (vs alternatives)

| Alternative | Why rejected |
|-------------|--------------|
| Ship all 3 slices at once | Dilutes review focus; Slice 3 requires a spec delta (different change shape); 3× review budget. |
| Ship Slice 3 first | Per-finding graph_unavailable requires distinguishable graph failure modes — Slice 1's typed exception hierarchy is the prerequisite. Shipping Slice 3 first forces inventing the seam under spec pressure. |
| Ship only `decision_drift.py` file split (no Protocol extraction) | Mechanical split mirrors v1.3-cli-split but doesn't create a real abstraction — 4 submodules each carrying the same god-pattern. `decision_drift.py` is 734 LOC because the logic IS complex, not because the file is bloated. |
| Extract `DriftOrchestrator` class (OOP) without Protocol contracts | Tighter coupling; harder to mock for unit tests; the project uses Protocols elsewhere (`EngramBackend` ABC + `mem_search_federated` defaults). Stay consistent with the codebase's type discipline. |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/flow_engineering/decision_drift.py` | Modified (refactor) | `scan_change` shrinks from 250 → ~170 LOC; new `_build_loader` + `_build_source` helpers added; `_DummyBackend` removed; `SnapshotGraphMissing` re-export-only (canonical in `snapshot_manager.py`) |
| `src/flow_engineering/drift/_graph_loader.py` | NEW | `GraphLoader` Protocol + `LiveDiskGraphLoader` + `SnapshotGraphLoader` + 4 typed exception classes (~180 LOC) |
| `src/flow_engineering/drift/_observation_source.py` | NEW | `ObservationSource` Protocol + `BackendObservationSource` + `FrozenBackendObservationSource` (~80 LOC) |
| `src/flow_engineering/drift/__init__.py` | NEW | Public re-export barrel preserving `flow_engineering.decision_drift` import paths (~15 LOC) |
| `src/flow_engineering/snapshot_manager.py` | Modified | `SnapshotGraphMissing` becomes canonical here; the 1-release `SnapshotGraphMissingError` alias contract is honored |
| `tests/unit/test_decision_drift.py` | Modified (no logic change) | All existing tests MUST pass unchanged — this is the regression gate |
| `tests/unit/test_decision_drift_graph_loader.py` | NEW | Protocol contract tests + adapter behavior tests (~120 LOC) |
| `tests/unit/test_decision_drift_observation_source.py` | NEW | Protocol contract tests + filter logic tests (~80 LOC) |
| `tests/unit/test_decision_drift_snap_id.py` | Modified (no logic change) | Snapshot-pinned path now goes through `SnapshotGraphLoader`; tests should pass with zero edits |
| `openspec/specs/decision-drift/spec.md` | NO CHANGE | Refactor only; REQ-9..16 + REQ-55..59 wording stays valid |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `scan_change` adapter-compat layer drifts from canonical kwargs | Medium | Keep public signature UNCHANGED; adapter is internal; integration test asserts kwargs still produce identical `DriftReport` |
| New `GraphLoader` exception types break CLI error mapping (`cli/drift.py:351`) | Low | CLI catches `SnapshotGraphMissing` specifically; new types are narrower. Adapter re-raises `SnapshotGraphMissing` when the snapshot has no graph content (preserves D2 graceful degradation contract from v0.8.0 design). |
| `unable_reason` population surfaces historical silent errors in test fixtures | Low | Field defaults to `None`; populating it adds INFO-level noise but no breaking change. Existing 9 test files assert `graph_unavailable=True` shape, not `unable_reason` content. |
| Slice 1 PR exceeds 400 LOC despite careful sizing | Medium | If actual PR diff > 400, apply `cli/spec.md` REQ-CLI-SPLIT-5 paragraph ("Mechanical extraction, not new logic") OR split into 2 chained PRs (PR1 = Protocols + adapters; PR2 = `scan_change` refactor + `unable_reason` population). The 2-PR split is the v1.2-followups `stacked-to-main` precedent. |
| `_write_back_findings` lazy-import in `cli/drift.py` becomes more fragile | Low | Slice 1 does NOT touch CLI. Drift CLI keeps importing from `flow_engineering.cli` exactly as before. |

## Rollback Plan

Single PR (or 2 chained PRs). Rollback = `git revert` the merge commit.

- The refactor preserves all public API surface (`scan_change`, `load_graph`, `classify_binding`, `Finding`, `DriftReport`, `DriftClass`).
- No spec-level changes — no need to revert `openspec/specs/decision-drift/spec.md`.
- No BDD scenario changes — no need to revert BDD step glue.
- No CLI surface changes — no need to revert `cli/drift.py`.
- The 2 new modules (`drift/_graph_loader.py`, `drift/_observation_source.py`) are additive; removal = `git rm` + revert `decision_drift.py` adapter dispatch.

Rollback window: any time before the PR merges. Post-merge, revert is safe but requires the follow-up changes (Slice 2 + Slice 3) to be re-planned against the pre-refactor `decision_drift.py`.

## Dependencies

- **Snapshot manager exception hierarchy** (REQ-V1.1.6 already shipped `SnapshotGraphMissingError` as canonical + `SnapshotGraphMissing` as 1-release alias in `snapshot_manager.py`). Slice 1 flips the canonical raise site — the alias contract is honored.
- **EngramBackend ABC** (`src/flow_engineering/engram_io.py:54`) — `ObservationSource` is a narrower Protocol that consumes the `iter_observations()` method. No ABC change needed.
- **`flow_engineering.cli` test-seam imports** — Slice 1 does NOT touch `cli/drift.py`. Drift CLI keeps working unchanged.

## Success Criteria

- [ ] `tests/unit/test_decision_drift.py` (558 LOC) passes with ZERO edits.
- [ ] `tests/unit/test_decision_drift_snap_id.py` (620 LOC) passes with ZERO edits (snapshot-pinned path now goes through `SnapshotGraphLoader`).
- [ ] `tests/unit/test_decision_drift_v080_migration.py` + `test_decision_drift_v090_hardening.py` pass unchanged.
- [ ] All 4 `tests/unit/test_cli_drift*.py` files (1 420 LOC total) pass unchanged.
- [ ] `tests/unit/test_drift_event_log.py` (740 LOC) passes unchanged (Slice 2 NOT in scope).
- [ ] 182/182 BDD scenarios pass unchanged.
- [ ] 1678 pytest pass + 0 net new failures vs `e50adb6` baseline (per `cli/spec.md` archive status).
- [ ] Ruff clean on changed files.
- [ ] Mypy clean on changed files (the new Protocol definitions may surface residual type debt — see Risk #4).
- [ ] `scan_change` LOC reduced from 250 → ≤ 200 (per `git diff --stat origin/main..HEAD -- src/flow_engineering/decision_drift.py`).
- [ ] `_DummyBackend` class REMOVED from `decision_drift.py` (verifiable via `grep -c "_DummyBackend" src/flow_engineering/decision_drift.py`).
- [ ] `unable_reason` populated on at least 2 error paths (e.g., `GraphMissing` + `SnapshotEnvelopeCorrupt`) — verifiable via 2 NEW unit tests.
- [ ] Public API surface (`from flow_engineering.decision_drift import *`) UNCHANGED — verifiable via `python -c "import flow_engineering.decision_drift; assert all(...)"`.
- [ ] PR diff ≤ 400 LOC OR includes REQ-CLI-SPLIT-5 "Mechanical extraction, not new logic" justification paragraph.

## Size Estimate

**Total: ~400 LOC across 1 single-PR (or 2 chained PRs at ~200 LOC each)**.

| Component | LOC delta | Notes |
|-----------|-----------|-------|
| `drift/_graph_loader.py` (NEW) | +180 | `GraphLoader` Protocol + 2 adapters + 4 typed exceptions |
| `drift/_observation_source.py` (NEW) | +80 | `ObservationSource` Protocol + 2 adapters |
| `drift/__init__.py` (NEW barrel) | +15 | Public re-exports preserving `flow_engineering.decision_drift` paths |
| `decision_drift.py` (refactored) | -80 net | `scan_change` shrinks 250 → 170; `_DummyBackend` removed (-15); new `_build_loader` + `_build_source` helpers (+30); `SnapshotGraphMissing` re-export-only (-5) |
| `snapshot_manager.py` (canonical exception) | +15 | Move `SnapshotGraphMissing` to canonical location + `__all__` entry |
| `tests/unit/test_decision_drift_graph_loader.py` (NEW) | +120 | 8 contract tests + 4 adapter behavior tests + 4 exception-population tests |
| `tests/unit/test_decision_drift_observation_source.py` (NEW) | +80 | 5 contract tests + 3 filter-logic tests |
| Existing test files | 0 | ZERO edits — strict regression gate |
| **Total production delta** | **+210** | within budget |
| **Total test delta** | **+200** | strict TDD (tests written first per `sdd-init/flow-engineering.md`) |
| **Total change** | **+410** | **slightly over 400-LOC budget** |

### Review budget posture

- At ~410 LOC, this change **needs the REQ-CLI-SPLIT-5 justification** ("Mechanical extraction of 2 narrow Protocols from an over-orchestrated `scan_change`; behavior preserved; public API unchanged; creates seam for OTel/federation/per-finding-graph-unavailable follow-ups").
- **Alternative**: split into 2 chained PRs at ~200 LOC each (PR1 = Protocols + adapters + new tests; PR2 = `scan_change` refactor + `unable_reason` population + canonical exception move). Uses the `stacked-to-main` precedent from `v1.2-followups`.

## Implementation Sequencing (informational — design + tasks phase will detail)

```
PR1 (Slice 1, single PR):
  T1.1 RED: test_decision_drift_graph_loader.py — Protocol contract tests
  T1.2 GREEN: drift/_graph_loader.py — Protocol + adapters + exceptions
  T1.3 RED: test_decision_drift_observation_source.py — Protocol contract tests
  T1.4 GREEN: drift/_observation_source.py — Protocol + adapters
  T1.5 RED: test_decision_drift.py — adapter-compat integration tests (kwargs still work)
  T1.6 GREEN: decision_drift.py — _build_loader + _build_source helpers
  T1.7 REFACTOR: decision_drift.py — scan_change consumes Protocols
  T1.8 RED: test_decision_drift.py — unable_reason population tests
  T1.9 GREEN: GraphLoader exceptions populate unable_reason
  T1.10 CHORE: snapshot_manager.py — canonical SnapshotGraphMissing
  T1.11 CHORE: decision_drift.py — remove _DummyBackend, re-export only
  T1.12 CHORE: CHANGELOG + pyproject version bump (none — refactor)
  T1.13 VERIFY: full test suite + ruff + mypy + spec/design drift check
```

## Notes for downstream phases

- **sdd-design**: focus on the Protocol signatures + adapter dispatch logic. The exception hierarchy is the design-critical surface.
- **sdd-tasks**: 13 tasks above (T1.1..T1.13) are a starting point. Refine via the existing strict-TDD discipline (`sdd-init/flow-engineering.md`).
- **sdd-spec**: NO spec delta. The existing 10 root REQs in `openspec/specs/decision-drift/spec.md` cover this surface.
- **sdd-archive**: archive the change per the standard cycle. Expected verdict: PASS WITH WARNINGS (per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` + `v1.2-followups` precedent posture).