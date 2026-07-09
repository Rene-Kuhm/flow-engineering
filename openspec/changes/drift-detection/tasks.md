<!-- tasks.md: drift-detection change. Phase: tasks (sdd-tasks). Slice 1 — GraphLoader + ObservationSource Protocols. NOT production code; documentation only. -->
# Tasks: drift-detection (Slice 1 — Extract GraphLoader + ObservationSource Protocols)

> **Change**: `drift-detection` (new at `openspec/changes/drift-detection/`).
> **Slice**: 1 of 3 candidate slices identified in `explore.md`.
> **Builds on**: `openspec/changes/drift-detection/{explore.md, proposal.md, specs/drift-detection/spec.md, design.md}`.
> **Artifact store mode**: hybrid (filesystem + Engram `sdd/drift-detection/tasks`).
> **Strict TDD**: ON per `.specify/memory/constitution.md` Article III + `sdd-init/flow-engineering.md` (`strict_tdd: true`). Every implementation task has a preceding RED test task.
> **Constitutional posture**: Article VII (400-LOC PR-diff budget). Refined forecast is **380 LOC** — single PR is CONSTITUTIONAL.

## Apply-progress

```yaml
status: READY
change: drift-detection
slice: 1 (GraphLoader + ObservationSource Protocols)
apply_progress_scaffold: openspec/changes/drift-detection/apply-progress.md
head_sha: c713bdc
total_tasks: 16
total_work_unit_commits_target: 18 (each T1.1-T6.2 + 2 natural splits; T7.1/T7.2 are verify gates, no commits)
strict_tdd: ON
```

sdd-apply will populate `apply-progress.md` with per-batch verification evidence as each task lands. Expected batch sequence: **Batch 1 = T1.1-T1.3 (GraphLoader Protocol)**, **Batch 2 = T2.1-T2.3 (ObservationSource Protocol)**, **Batch 3 = T3.1-T3.2 (Typed exceptions)**, **Batch 4 = T4.1-T4.2 (SnapshotGraphMissing relocation)**, **Batch 5 = T5.1-T5.2 (unable_reason + _DummyBackend removal)**, **Batch 6 = T6.1-T6.2 (scan_change refactor + byte-identical invariant)**, **Batch 7 = T7.1-T7.2 (Verify gates)**. Each batch ≤6 tasks OR ≤150 LOC production delta.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated production LOC | 180 |
| Estimated test LOC | 200 (new) |
| Existing test files (regression gate) | 6,400 LOC across 9 files; 0 edits |
| Total diff LOC | 380 |
| TDD multiplier (strict TDD ratio test:prod) | 1.11× |
| Forecast at full TDD churn (×6 nominal) | 1,080 (transient; non-issue — the PR diff is the budget metric) |
| 400-line budget risk | **Low** (single PR = 380 LOC under budget) |
| Chained PRs recommended | **No** (380 < 400) |
| Chain strategy | **n/a** (single PR posture) |
| Delivery strategy | `single-pr` |
| Decision needed before apply | **No** |
| Size:exception justified | **No** (under budget; documented for Article VII auditability) |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: single-pr
400-line budget risk: Low
```

### Size:exception justification (per REQ-CLI-SPLIT-5)

Even though the refined forecast (380 LOC) is **under** the 400-LOC budget (no `size:exception` exception required), the Article VII auditability discipline requires documenting the gap between the proposal's estimate (~410 LOC) and the refined forecast (380 LOC). The 30-LOC reduction came from FOUR design refinements documented in `design.md` §13 + §11:

1. **D6 flat module names** — the implementation uses `src/flow_engineering/drift_graph_loader.py` and `src/flow_engineering/drift_observation_source.py` (flat modules). The active spec has been aligned; older `drift/_graph_loader.py` package references are historical planning context only.
2. **Narrower `ObservationSource` Protocol surface** — REQ-DRIFT-DETECTION-2 narrowed the Protocol to ONLY `iter_observations()` (dropping the orphaned `backend` attribute and the unreachable `# pragma: no cover` `mem_search` method that `_DummyBackend` carried). ~10 LOC saved. The new `ObservationSource` Protocol + `BackendObservationSource` together shrink from ~110 LOC (proposal estimate) to ~80 LOC.
3. **PEP 562 re-export for `SnapshotGraphMissing`** — the proposal sketched a 5-LOC class block + alias in `decision_drift.py`. The design adopted the existing `snapshot_manager.py:113-124` PEP 562 `__getattr__` precedent and made `decision_drift.py` import `SnapshotGraphMissingError as SnapshotGraphMissing` (1-line). ~4 LOC saved on `decision_drift.py`. Net `snapshot_manager.py` delta: 0 (canonical already there since v1.1.6).
4. **`drift_exceptions.py` reserved for Slice 3** — the design co-located the 5 typed-exception classes inside `drift_graph_loader.py` (~+15 LOC) instead of a separate `drift_exceptions.py` module. ~15 LOC saved on a `drift_exceptions.py` barrel + imports. **CAUTION**: This task list OVERRIDES the design's co-location decision (per the user's T3.2) and creates a standalone `drift_exceptions.py`. The 15 LOC saving is therefore nullified at apply time. **Revised forecast**: 380 + 15 = 395 LOC — STILL under the 400 budget, but within 5 LOC of the threshold. The apply phase MUST run `git diff --stat origin/main..HEAD -- src/ tests/` after batch 6 + verify the diff is ≤ 400 LOC. If the actual diff exceeds 400 LOC, the apply phase SHALL either (a) trim non-essential comments/docstrings, or (b) split into the documented 2-PR chained fallback per design.md §13 (PR1 = `drift_graph_loader.py` + `drift_observation_source.py` + `drift_exceptions.py` + new tests; PR2 = `decision_drift.py` refactor + `unable_reason` population).

## Phase 0 — Slice 1 sandbox branch (no chained PR; single PR posture)

Since the 380-LOC forecast is under the 400-LOC budget, this slice uses **single-PR posture** (no chained PRs, no branch chain scaffolding). The slice branch is a personal `codex/drift-detection-slice-1` branch from `origin/main @ c713bdc` — reviewers see ONE PR with ALL 16 task commits as 18 work-unit commits grouped by RED→GREEN→REFACTOR cycles.

- [ ] **T0.1** Create branch `codex/drift-detection-slice-1` from `origin/main @ c713bdc`. Push to `origin`. rollback: `git push origin --delete codex/drift-detection-slice-1`. Create draft PR against `main` with the REQ-CLI-SPLIT-5 size:exception justification paragraph in the PR body (even though under budget — see "Size:exception justification" above).

## Phase 1 — GraphLoader Protocol (T1.1 → T1.3, 3 work-unit commits, ~165 LOC prod + ~120 LOC test)

Covers **REQ-DRIFT-DETECTION-1** (GraphLoader Protocol) + **REQ-DRIFT-DETECTION-8 scenarios 2-3** (adapter-compat layer dispatch unit test for `snap_id` → `SnapshotGraphLoader` and `graph_json_path` → `LiveDiskGraphLoader`). Plan for **Batch 1** (≤150 LOC prod).

- [ ] **T1.1** (RED — 1 commit `test: write GraphLoader Protocol contract tests`) Write `tests/unit/test_decision_drift_graph_loader.py` (~40 LOC) with RED imports of `from flow_engineering.drift_graph_loader import GraphLoader` (must fail with `ModuleNotFoundError`). Tests assert: (a) `GraphLoader` is a `typing.Protocol`, (b) Protocol declares ONLY `load(self)` (no other methods, verified via `dir()`), (c) `isinstance(LiveDiskGraphLoader_impl(), GraphLoader)` evaluates at runtime via `@runtime_checkable`. Verify RED by running `uv run pytest tests/unit/test_decision_drift_graph_loader.py -q` and confirming 4 ImportErrors + AssertionErrors.
- [ ] **T1.2a** (GREEN — 1 commit `feat: add GraphLoader Protocol + LiveDiskGraphLoader`) Create `src/flow_engineering/drift_graph_loader.py` (~80 LOC). Define `GraphLoader(Protocol)` with `load(self) -> tuple[dict|None, dict|None, float|None]` method. Define `LiveDiskGraphLoader(graph_json_path: Path)` adapter with `load()` reading JSON via `LiveDiskGraphLoader._load_live_disk()` helper (raises `GraphMissing` on `Path.exists() is False`, `GraphMalformed` on `JSONDecodeError`, `PermissionDenied` on `EACCES`/`EPERM`/`EROFS` — see T3.1 + T3.2 for exception class imports). Wire `tests/unit/test_decision_drift_graph_loader.py` to go GREEN: 4 Protocol-contract tests + 2 adapter-behavior tests (happy path + missing-file → `GraphMissing`).
- [ ] **T1.2b** (GREEN — 1 commit `feat: add SnapshotGraphLoader adapter`) Extend `src/flow_engineering/drift_graph_loader.py` with `SnapshotGraphLoader(snap_id: str)` adapter (~60 LOC). `load()` calls `snapshot_manager.SnapshotManager.show(snap_id)` directly (NO `_DummyBackend`, per REQ-DRIFT-DETECTION-1 scenario 3). Refactor shared body into `_parse_envelope_graph(envelope)` helper (~25 LOC, co-located for grep-ability). Extend `tests/unit/test_decision_drift_graph_loader.py` with 2 more adapter-behavior tests (snap-id happy path + corrupt-envelope → `SnapshotEnvelopeCorrupt`).
- [ ] **T1.3** (REFACTOR — 1 commit `refactor: extract _index_graph_payload helper`) Confirm `drift_graph_loader.py` exports `LiveDiskGraphLoader`, `SnapshotGraphLoader`, `GraphLoader` via `__all__`. No new test coverage needed (REFACTOR preserves GREEN state). If during T1.2 the body grew past 6 LOC delta, extract `_index_graph_payload(nodes, mtime)` helper shared by both adapters (verbatim from `decision_drift.py:252-274`). ruff + mypy clean.

## Phase 2 — ObservationSource Protocol (T2.1 → T2.3, 3 work-unit commits, ~80 LOC prod + ~80 LOC test)

Covers **REQ-DRIFT-DETECTION-2** (ObservationSource Protocol) + the `_DummyBackend` removal runner-up (the Protocol eliminates the fixture-as-type smell). Plan for **Batch 2** (≤150 LOC prod).

- [ ] **T2.1** (RED — 1 commit `test: write ObservationSource Protocol contract tests`) Write `tests/unit/test_decision_drift_observation_source.py` (~35 LOC) with RED imports of `from flow_engineering.drift_observation_source import ObservationSource`. Tests assert: (a) `ObservationSource` is a `Protocol`, (b) declares ONLY `iter_observations(self) -> Iterable[dict]`, (c) a stub class implementing only `iter_observations` satisfies `isinstance(stub(), ObservationSource)`. Verify RED by running `uv run pytest tests/unit/test_decision_drift_observation_source.py -q` and confirming 3 ImportErrors + AssertionErrors.
- [ ] **T2.2a** (GREEN — 1 commit `feat: add ObservationSource Protocol + BackendObservationSource`) Create `src/flow_engineering/drift_observation_source.py` (~50 LOC). Define `ObservationSource(Protocol)` with `iter_observations(self) -> Iterable[dict]`. Define `BackendObservationSource(backend, *, change_name, since=None)` adapter (~30 LOC) wrapping `EngramBackend.iter_observations()` + `topic_key` prefix filter + `created_at >= since` cutoff. Lazy-import `InMemoryBackend` inside the constructor. Mirror the existing `decision_drift.py:596-615` filter chain byte-for-byte. Wire `tests/unit/test_decision_drift_observation_source.py` to go GREEN: 3 Protocol-contract tests + 2 `BackendObservationSource` filter-logic tests (happy path + `since` cutoff).
- [ ] **T2.2b** (GREEN — 1 commit `feat: add FrozenBackendObservationSource adapter`) Extend `drift_observation_source.py` with `FrozenBackendObservationSource(snap_id: str)` adapter (~30 LOC). Lazy-imports inside `iter_observations`: `SnapshotManager`, `InMemoryBackend`, `_resolve_snapshots_dir`. Mirrors the existing `decision_drift.py:_frozen_backend_from_snapshot` logic exactly (rebuilds `InMemoryBackend` from `graph_state.observations` preserving snapshot's `id` field). Caches result in `self._cache` to avoid re-reading the envelope twice per scan. Extend `tests/unit/test_decision_drift_observation_source.py` with 2 round-trip tests (happy path + envelope-corruption → empty list).
- [ ] **T2.3** (GREEN — 1 commit `feat: add StaticObservationSource test-only adapter`) Add `StaticObservationSource(observations: list[dict])` (~10 LOC) to `drift_observation_source.py`. Excluded from `__all__` (test-only, replaces `_DummyBackend` for future fixtures). Extend `tests/unit/test_decision_drift_observation_source.py` with 1 identity-iteration test (no protocol requirement here — just iterating the canned list).

## Phase 3 — Typed exception hierarchy (T3.1 → T3.2, 2 work-unit commits, ~15 LOC prod + ~30 LOC test)

Covers **REQ-DRIFT-DETECTION-4** (typed exception hierarchy). Plan for **Batch 3** (≤150 LOC prod). The T3.2 creates a standalone `drift_exceptions.py` per the user's explicit override of the design's co-location choice (see "Size:exception justification" §4 above).

- [ ] **T3.1** (RED — 1 commit `test: write typed exception hierarchy tests`) Extend `tests/unit/test_decision_drift_graph_loader.py` (~30 LOC) with RED imports of `from flow_engineering.drift_exceptions import GraphLoadError, GraphMissing, GraphMalformed, PermissionDenied, SnapshotEnvelopeCorrupt`. Tests assert: (a) `issubclass(GraphMissing, GraphLoadError) is True`, (b) `issubclass(GraphMissing, GraphMalformed) is False` (siblings, NOT parent-child), (c) all 4 inherit from `Exception` (NOT `RuntimeError` or `ValueError`), (d) each carries a `message` attribute referencing the path/snap_id, (e) `str(exc)` returns the message. Verify RED by running `uv run pytest tests/unit/test_decision_drift_graph_loader.py -q -k "graph_exception"` and confirming 4 ImportErrors + AssertionErrors.
- [ ] **T3.2** (GREEN — 1 commit `feat: add typed exception hierarchy`) Create `src/flow_engineering/drift_exceptions.py` (~15 LOC). Define `GraphLoadError(Exception)` base + 4 siblings: `GraphMissing`, `GraphMalformed`, `PermissionDenied`, `SnapshotEnvelopeCorrupt`. All 4 carry a `message: str` (set via `super().__init__(message)`). Wire `tests/unit/test_decision_drift_graph_loader.py` to go GREEN: 4 exception-population tests. ruff + mypy clean.

## Phase 4 — `SnapshotGraphMissing` canonical relocation (T4.1 → T4.2, 2 work-unit commits, ~10 LOC prod)

Covers **REQ-DRIFT-DETECTION-7** (`SnapshotGraphMissing` relocation). Plan for **Batch 4** (≤150 LOC prod). The canonical raise site is ALREADY at `snapshot_manager.py:81-101` + PEP 562 alias at lines 113-124 (per v1.1.6). The refactor is in `decision_drift.py`: delete the duplicate at lines 179-187 + add a 1-line `from ... import ... as ...` PEP 562 alias re-export.

- [ ] **T4.1** (GREEN — 1 commit `refactor: relocate SnapshotGraphMissing to canonical snapshot_manager raise site`) In `src/flow_engineering/decision_drift.py`: (a) delete the duplicate `class SnapshotGraphMissing(ValueError)` at lines 179-187, (b) add module-level `from flow_engineering.snapshot_manager import SnapshotGraphMissingError as SnapshotGraphMissing  # noqa: F401` after the existing imports. The PEP 562 alias exists in `snapshot_manager.py:113-124` already; `decision_drift.py` simply re-exports the name. Extend `tests/unit/test_decision_drift_graph_loader.py` with 2 identity tests: (a) `SnapshotGraphMissing.__module__ == "flow_engineering.snapshot_manager"`, (b) importing it from `decision_drift` emits `DeprecationWarning` matching v1.1.6 wording.
- [ ] **T4.2** (REFACTOR — 1 commit `refactor: update internal imports to canonical SnapshotGraphMissingError`) Update INTERNAL imports in `src/flow_engineering/decision_drift.py` (the 2 internal references: lines 301 + 358 docstrings → `SnapshotGraphMissingError`; the 1 raise site at line 571 stays `SnapshotGraphMissing` for backward compat with `cli/drift.py:351`'s `except decision_drift.SnapshotGraphMissing` block). `tests/` files + `src/flow_engineering/cli/drift.py` keep importing `from flow_engineering.decision_drift import SnapshotGraphMissing` (unchanged behavior). No new test coverage needed (REFACTOR preserves GREEN state). ruff + mypy clean.

## Phase 5 — `unable_reason` population + `_DummyBackend` removal (T5.1 → T5.2, 2 work-unit commits, ~30 LOC prod + ~30 LOC test)

Covers **REQ-DRIFT-DETECTION-5** (`_DummyBackend` removal) + **REQ-DRIFT-DETECTION-6** (`unable_reason` population). Plan for **Batch 5** (≤150 LOC prod).

- [ ] **T5.1** (GREEN — 1 commit `feat: populate unable_reason from typed exceptions`) In `src/flow_engineering/decision_drift.py` `_scan_with_protocols` (post-T6.1 thinned coordinator): add the `except GraphLoadError as exc` clause after `loader.load()` that returns `DriftReport(..., graph_unavailable=True, unable_reason=_UNABLE_REASON_BY_EXC_NAME[type(exc).__name__])`. Mapping table lives as a module-level constant `_UNABLE_REASON_BY_EXC_NAME: dict[str, str] = {"GraphMissing": "graph_file_missing", "GraphMalformed": "graph_file_malformed", "PermissionDenied": "graph_file_unreadable", "SnapshotEnvelopeCorrupt": "snapshot_envelope_corrupt"}`. **CRITICAL**: do NOT map `SnapshotGraphMissing` (the D2 graceful degradation signal) to `unable_reason` — it remains a `raise` per REQ-33. Extend `tests/unit/test_decision_drift_graph_loader.py` with 2 `unable_reason` mapping tests: (a) `scan_change(change_name, graph_json_path=<missing>)` returns `unable_reason="graph_file_missing"`, (b) `scan_change(change_name, snap_id=<corrupt-snap>)` returns `unable_reason="snapshot_envelope_corrupt"`.
- [ ] **T5.2** (REFACTOR — 1 commit `refactor: remove _DummyBackend class + 4 callsites`) In `src/flow_engineering/decision_drift.py`: (a) delete the `class _DummyBackend` block at lines 362-376, (b) replace the 4 callsites at lines 311 + 410 + 438 with `SnapshotManager(snapshots_dir=..., backend=None)` (the post-v1.1.6 `SnapshotManager` constructor accepts `backend=None` because `show()` doesn't touch the backend — verified at `snapshot_manager.py:113-124` PEP 562 pattern). Verify NO test file imports `_DummyBackend` (`grep -rn "_DummyBackend" tests/`) — expected 0 matches per the design's pre-flight check. If any test file does import it, document and fix before continuing (this is the regression gate, mechanical remediation only — no behavioral change). Extend `tests/unit/test_decision_drift_graph_loader.py` with 1 negative-imports test asserting `from flow_engineering.decision_drift import _DummyBackend` raises `ImportError`.

## Phase 6 — `scan_change` refactor + byte-identical DriftReport invariant (T6.1 → T6.2, 3 work-unit commits, ~30 LOC prod + ~30 LOC test)

Covers **REQ-DRIFT-DETECTION-3** (`scan_change` thin-coordinator refactor) + **REQ-DRIFT-DETECTION-8** (adapter-compat layer + byte-identical DriftReport invariant). Plan for **Batch 6** (≤150 LOC prod).

- [ ] **T6.1a** (GREEN — 1 commit `feat: add _build_loader + _build_source adapter-compat layer`) Add 2 internal helpers to `src/flow_engineering/decision_drift.py` (~30 LOC): `_build_loader(*, graph_json_path, snap_id) -> GraphLoader` (dispatches to `SnapshotGraphLoader(snap_id)` when `snap_id` is set, else `LiveDiskGraphLoader(graph_json_path or DEFAULT_GRAPH_JSON)`); `_build_source(*, backend, snap_id, change_name, since) -> ObservationSource` (dispatches to `FrozenBackendObservationSource(snap_id)` when `snap_id` is set, else `BackendObservationSource(backend, change_name=change_name, since=since)`). Both are private (`_` prefix, NOT in `__all__`). Extend `tests/unit/test_decision_drift_graph_loader.py` with 2 dispatch tests: (a) `snap_id="abc"` → `SnapshotGraphLoader`, (b) `graph_json_path=Path("foo")` → `LiveDiskGraphLoader(Path("foo"))`. Public `scan_change` signature UNCHANGED at this commit.
- [ ] **T6.1b** (REFACTOR — 1 commit `refactor: thin scan_change body to consume Protocols`) Refactor `scan_change` body from 250 LOC → ≤ 200 LOC. New body calls `_build_loader(...)` + `_build_source(...)` + delegates the per-observation loop (lifted VERBATIM from `decision_drift.py:617-672` + `674-700`) to a new `_scan_with_protocols(loader, source, change_name, since, include_obsolete, scanned_at) -> DriftReport` helper. The 4 distinct `except Exception: continue/pass` blocks collapse to: (a) `loader.load()` → typed `except GraphLoadError` (per T5.1), (b) 1 `except Exception: pass` at the per-binding-iteration site (preserved for backwards compat), (c) 1 `except Exception: pass` at the contradiction re-classification site (preserved for backwards compat), (d) the legacy top-level `except Exception: return graph_unavailable=True` block REMOVED (replaced with the typed catch + the unparseable `SnapshotGraphMissing` re-raise). ruff + mypy clean. **CRITICAL**: no new test coverage needed (REFACTOR preserves GREEN state across the 9 existing test files + 2 BDD step files).
- [ ] **T6.2** (GREEN — 1 commit `test: byte-identical DriftReport invariant for legacy kwargs`) Extend `tests/unit/test_decision_drift_graph_loader.py` with 2 byte-identical DriftReport tests capturing the v1.2.0 baseline at `git show e50adb6:src/flow_engineering/decision_drift.py` and asserting post-Slice-1 reports match byte-for-byte on `scanned_at` + `class_counts` + `findings` + `graph_unavailable` fields (modulo the documented `unable_reason` addition for failure paths). Test fixture covers BOTH (a) live-disk path (`graph_json_path=<tmp>`) and (b) snapshot-pinned path (`snap_id=<snap-with-graph>`).

## Phase 7 — Verify gates (T7.1 → T7.2, NO commits; CI verification)

Covers **REQ-DRIFT-DETECTION-3 scenario 4** + **spec §4.1-§4.3 verification approach**. NO work-unit commit — these are CI verification gates executed by `sdd-verify` AFTER the slice branches merge (or runs locally before PR open).

- [ ] **T7.1** (VERIFY — `uv run ruff check src/flow_engineering/drift_graph_loader.py src/flow_engineering/drift_observation_source.py src/flow_engineering/drift_exceptions.py src/flow_engineering/decision_drift.py tests/unit/test_decision_drift_graph_loader.py tests/unit/test_decision_drift_observation_source.py`) exits 0; `uv run mypy --strict src/flow_engineering/drift_graph_loader.py src/flow_engineering/drift_observation_source.py src/flow_engineering/drift_exceptions.py` exits 0 (note: `--strict` may surface residual type debt at the 12 mypy residuals documented in `v0.9.0-hardening/verify-report.md`; that debt is out of scope for Slice 1); `git diff --stat origin/main..HEAD -- src/ tests/` shows ≤ 400 LOC.
- [ ] **T7.2** (VERIFY — `uv run pytest tests/unit/test_decision_drift.py tests/unit/test_decision_drift_snap_id.py tests/unit/test_decision_drift_v080_migration.py tests/unit/test_decision_drift_v090_hardening.py tests/unit/test_cli_drift.py tests/unit/test_cli_drift_events_list.py tests/unit/test_cli_drift_events_tail.py tests/unit/test_cli_drift_events_stats.py tests/unit/test_cli_drift_events_alias.py tests/unit/test_drift_event_log.py tests/unit/test_decision_drift_graph_loader.py tests/unit/test_decision_drift_observation_source.py -q`) exits 0 with 1,678+ passing tests AND 0 net-new failures vs `e50adb6` baseline. AND `uv run pytest tests/bdd/ -q` reports 182/182 BDD scenarios passing. AND `git diff origin/main..HEAD -- tests/unit/test_decision_drift.py tests/unit/test_decision_drift_snap_id.py tests/unit/test_decision_drift_v080_migration.py tests/unit/test_decision_drift_v090_hardening.py tests/unit/test_cli_drift.py tests/unit/test_cli_drift_events_{list,tail,stats,alias}.py` shows ZERO modifications (the strict regression gate). AND `grep -c "_DummyBackend" src/flow_engineering/decision_drift.py` returns `0` (REQ-DRIFT-DETECTION-5). AND `python -c "from flow_engineering.snapshot_manager import SnapshotGraphMissing; print(SnapshotGraphMissing.__module__)"` prints `flow_engineering.snapshot_manager` (REQ-DRIFT-DETECTION-7). AND `git diff --stat origin/main..HEAD -- src/flow_engineering/decision_drift.py` shows `scan_change` LOC reduced (REQ-DRIFT-DETECTION-3).

## Implementation order rationale

1. **Phase 1 (GraphLoader) FIRST** — every other task depends on the `GraphLoader` type being defined for `scan_change` to consume (Phase 6).
2. **Phase 2 (ObservationSource) SECOND** — analog of Phase 1; together they create the seam that the refactor (Phase 6) threads through.
3. **Phase 3 (Typed exceptions) THIRD** — Blocks the T5.1 `unable_reason` population (Phase 5) + Phase 6's typed `except GraphLoadError` clause.
4. **Phase 4 (SnapshotGraphMissing relocation) FOURTH** — Independent of the Protocols; bundles cleanly with Phase 5 (also touches `decision_drift.py`).
5. **Phase 5 (`unable_reason` + `_DummyBackend` removal) FIFTH** — Depends on Phase 3 (exceptions exist) + Phase 1 (loader raises them); preserves the strict regression gate (no test files import `_DummyBackend`).
6. **Phase 6 (`scan_change` refactor + byte-identical invariant) SIXTH** — Depends on ALL preceding phases. The thinned coordinator exercises both Protocols. The byte-identical invariant is the regression proof.
7. **Phase 7 (Verify gates) LAST** — T7.1 (lint+type) blocks T7.2 (full test suite); T7.2 is the gate for archive.

## Risks

- **r1**: `scan_change` adapter-compat layer drifts from canonical kwargs. *Mitigation*: T6.1a's 2 dispatch tests + T6.2's 2 byte-identical invariant tests + the 9 existing test files (5,400 LOC) as the strict regression gate.
- **r2**: New `GraphLoader` exception types break CLI error mapping (`cli/drift.py:351`). *Mitigation*: T4.1 keeps the `SnapshotGraphMissing` (the D2 graceful degradation signal) re-export byte-identical. CLI's `except decision_drift.SnapshotGraphMissing` catches unchanged.
- **r3**: `unable_reason` population surfaces historical silent errors in test fixtures. *Mitigation*: Field defaults to `None`; populating it adds INFO-level noise but no breaking change. The 9 existing test files assert `graph_unavailable=True` shape, NOT `unable_reason` content.
- **r4**: Final PR diff exceeds 400-LOC budget because T3.2's standalone `drift_exceptions.py` (per user's override of design's co-location choice) adds ~15 LOC the design didn't budget. *Mitigation*: `git diff --stat origin/main..HEAD -- src/ tests/` gate at T7.1. If > 400 LOC: (a) trim non-essential docstrings/comments, or (b) split into the documented 2-PR chained fallback (PR1 = Protocols + exceptions + tests; PR2 = `scan_change` refactor + `unable_reason` + `_DummyBackend` removal).
- **r5**: `_DummyBackend` removal breaks 4 hidden test-file imports (the design's pre-flight check found 0, but pre-flight checks miss consumer plugins). *Mitigation*: T5.2 includes a `grep -rn "_DummyBackend" tests/` verification step. If matches found, document + fix mechanically (no behavioral change); the regression gate is integration, not unit-only.
- **r6**: `decision_drift.py` mypy residuals from the 12 `# pragma: no cover` sites get re-surfaced. *Mitigation*: 4 lines (372, 375 + the 3 `# pragma: no cover` sites at 310/411/439) are deleted when `_DummyBackend` is removed and `_load_graph_from_snapshot` is relocated. Net mypy improvement: ~7 fewer residuals. Documented as out-of-scope cleanup; not a blocker for archive.
- **r7**: D6 deviation (flat module layout vs early planning wording) could create review confusion. *Mitigation*: active spec wording now points at the shipped flat modules; treat older package-layout notes as historical only.
- **r8**: `SnapshotGraphMissing` PEP 562 re-export breaks `inspect.signature` consumers. *Mitigation*: T4.1's identity test `SnapshotGraphMissing is SnapshotGraphMissingError` proves the class object is the same (PEP 562 is for module-attribute access, not class identity).

## Out of scope (deferred — see `proposal.md` §"Out of Scope" + `explore.md` §3)

- Slice 2 (unified JSONL rotation helper for `drift_events.jsonl` + `metrics.jsonl`) — separate change.
- Slice 3 (per-finding `graph_unavailable` refinement + new REQ + new BDD scenarios) — depends on Slice 1's typed exception hierarchy; standalone change with its own delta spec.
- OTel push exporter — external dep, separate change.
- Cross-project drift federation — new feature, needs design spike.
- `decision_drift.py` file split (4 submodules) — mechanical; requires Slice 1 as prerequisite to avoid duplicating the god-module pattern.
- `_write_back_findings` lazy-import refactor — Slice 4 v1.3-cli-split artifact (Engram #2041), orthogonal.
- `classify_binding` + `_classify_with_id_map` collapse — artificial 2-layer split (only 1 caller), deferred.
- D6 spec/impl alignment — resolved; active spec names the shipped flat modules and standalone `drift_exceptions.py`.

## Apply-progress format (v1.3-cli-split precedent, slice-local)

sdd-apply will create `openspec/changes/drift-detection/apply-progress.md` at the start of Batch 1 with the following shape (modeled on `openspec/changes/archive/2026-07-08-v1.3-cli-split/apply-progress.md`):

```markdown
# Apply Progress: drift-detection (Slice 1)

> **Change**: `drift-detection` (Protocol extraction refactor)
> **Slice**: 1 of 3 candidate slices
> **Mode**: hybrid (filesystem + Engram)
> **Branch base**: `origin/main @ c713bdc`
> **Slice branch**: `codex/drift-detection-slice-1`
> **PR**: <URL after first batch lands>

## Goal
Execute the 16 tasks in `tasks.md` as 18 work-unit commits in 7 batches.

## Status
| Batch | Tasks | Status | Verification |
|-------|-------|--------|--------------|
| 0 | T0.1 (branch setup) | [ ] pending | branch pushed; PR draft opened with size:exception paragraph |
| 1 | T1.1-T1.3 (GraphLoader) | [ ] pending | 4 + 2 + 2 = 8 contract/behavior tests green |
| 2 | T2.1-T2.3 (ObservationSource) | [ ] pending | 3 + 4 + 1 = 8 contract/filter tests green |
| 3 | T3.1-T3.2 (Exceptions) | [ ] pending | 4 exception-population tests green |
| 4 | T4.1-T4.2 (SnapshotGraphMissing) | [ ] pending | 2 identity tests green; DeprecationWarning verified |
| 5 | T5.1-T5.2 (unable_reason + _DummyBackend removal) | [ ] pending | 2 unable_reason tests + 1 negative-imports test green |
| 6 | T6.1-T6.2 (scan_change refactor + invariant) | [ ] pending | 2 dispatch tests + 2 byte-identical invariant tests green |
| 7 | T7.1-T7.2 (CI verify) | [ ] pending | ruff + mypy + 1678+ pytest + 182 BDD scenarios + size gates green |

<Each batch has its own ## Slice <N> — <Title> section populated as sdd-apply lands each batch, mirroring the v1.3-cli-split apply-progress.md precedent:>
  ## Slice 1 — T1.1+T1.2a (GraphLoader Protocol + LiveDiskGraphLoader)
  ### Files Changed
  ### Verification Evidence
  ### Commits Made
  ### Risks Discovered
  ### Deviations from Design
  ### Next Steps
```

## Cross-references

- Proposal: `openspec/changes/drift-detection/proposal.md` (18 KB; Slice 1 locked in)
- Spec: `openspec/changes/drift-detection/specs/drift-detection/spec.md` (414 lines; 8 ADDED Requirements + 25 BDD scenarios)
- Design: `openspec/changes/drift-detection/design.md` (1,160 lines; 6 D-decisions)
- Explore: `openspec/changes/drift-detection/explore.md` (422 lines; architectural debt mapping)
- Root capability spec: `openspec/specs/decision-drift/spec.md` (REQ-9..16 + REQ-55..59; UNCHANGED)
- v1.3-cli-split precedent: `openspec/changes/archive/2026-07-08-v1.3-cli-split/tasks.md` + `apply-progress.md`
- Snapshot manager canonical exception: `src/flow_engineering/snapshot_manager.py:81-101` + lines 113-124
- Implementation anchors: `src/flow_engineering/decision_drift.py:485-734` (`scan_change`) + lines 179-187 (`SnapshotGraphMissing` duplicate)
- CLI consumer anchor: `src/flow_engineering/cli/drift.py:351-363` (`SnapshotGraphMissing` catch)
- Strict TDD marker: `sdd-init/flow-engineering.md:4` (`strict_tdd: true`)
- Constitutional governance: `.specify/memory/constitution.md` Article III (Strict TDD) + Article VII (400-LOC budget)
