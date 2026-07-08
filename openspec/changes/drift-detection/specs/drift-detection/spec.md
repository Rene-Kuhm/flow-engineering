<!-- Delta spec: drift-detection. Phase: spec (sdd-spec). Slice 1 of the drift-detection change. NOT production code; documentation only. -->
# Delta Spec: drift-detection (Slice 1 — Extract GraphLoader + ObservationSource Protocols)

> **Change**: `drift-detection` (new change at `openspec/changes/drift-detection/`).
> **Slice**: 1 of 3 candidate slices identified in `explore.md`. Slice 1 = Extract `GraphLoader` + `ObservationSource` Protocols from `scan_change`.
> **Parent capability**: `decision-drift` (root spec at `openspec/specs/decision-drift/spec.md`, REQ-9..16 + REQ-55..59). This delta spec EXTENDS the root capability — no MODIFIED Requirements, no REMOVED Requirements.
> **Authoring**: sdd-spec sub-agent, 2026-07-08.
> **Mode**: hybrid (filesystem artifact + Engram persistence).
> **Strict TDD**: ON per `sdd-init/flow-engineering.md` (`strict_tdd: true`); RED→GREEN→REFACTOR enforced at apply phase.

## Purpose

`scan_change` in `src/flow_engineering/decision_drift.py:485-734` is a 250-LOC orchestrator that couples 7 distinct responsibilities into a single function with 4 separate `except Exception: continue/pass` blocks that swallow every failure mode uniformly. The root capability spec (`openspec/specs/decision-drift/spec.md:47`) explicitly anticipates future deltas ("per-finding graph_unavailable refinement, cross-project drift federation, OTel push") that all require a seam between classification (pure) and orchestration (I/O). This delta defines the STRUCTURAL seam — 2 narrow `Protocol` types (`GraphLoader`, `ObservationSource`) plus a typed exception hierarchy — that lets future slices plug in without touching `classify_binding` or `DriftReport`. No public API change. No behavioral REQ change. No BDD scenario churn.

The 8 ADDED Requirements below describe WHAT the seam must expose. They are pure structural contracts: the existing 9 test files (~6,400 LOC) become the regression gate that proves behavior is preserved, plus new unit tests cover the Protocol contract surface.

## 1. Scope

### In Scope (Slice 1)

1. `GraphLoader` Protocol + 2 concrete adapters (`LiveDiskGraphLoader`, `SnapshotGraphLoader`) in NEW `src/flow_engineering/drift/_graph_loader.py`.
2. `ObservationSource` Protocol + concrete adapters in NEW `src/flow_engineering/drift/_observation_source.py`.
3. `scan_change` refactor — body becomes a thin coordinator over the 2 Protocols. Public signature `(change_name, *, graph_json_path, backend, include_obsolete, since, snap_id)` UNCHANGED.
4. Typed exception hierarchy (`GraphMissing`, `GraphMalformed`, `PermissionDenied`, `SnapshotEnvelopeCorrupt`) replacing bare `Exception` / `RuntimeError` swallows.
5. `unable_reason` population in `DriftReport` from the new typed exceptions.
6. `_DummyBackend` removal.
7. `SnapshotGraphMissing` relocation — canonical raise site moves to `snapshot_manager.py`; `decision_drift.py` re-exports for backward-compat with v1.1.6 alias convention.
8. Adapter-compat layer preserving public kwargs exactly (`graph_json_path`, `snap_id`, `backend`, `since`, `include_obsolete`).
9. NEW unit tests for the Protocol contracts and the typed exception hierarchy.

### Out of Scope (deferred to follow-up SDD changes — see §3)

- OTel push exporter (Slice 2 follow-up; external dep).
- Cross-project drift federation (new feature, not refactor).
- Per-finding `graph_unavailable` refinement (Slice 3, depends on Slice 1).
- Unified JSONL rotation helper (Slice 2 of the explore.md candidate slices, ~80 LOC).
- `decision_drift.py` file split into 4 submodules (mechanical; requires Slice 1 as prerequisite to avoid duplicating the god-module pattern).
- `_write_back_findings` lazy-import refactor (Slice 4 v1.3-cli-split artifact, orthogonal).
- `classify_binding` + `_classify_with_id_map` collapse (artificial 2-layer split, deferred).

## 2. ADDED Requirements

### Requirement: REQ-DRIFT-DETECTION-1 — GraphLoader Protocol

The system SHALL provide a `GraphLoader` `typing.Protocol` at `src/flow_engineering/drift/_graph_loader.py` with a single method:

- `def load(self) -> tuple[dict | None, dict | None, float | None]`

Returning the `(current_nodes, current_id_map, graph_mtime)` 3-tuple that `scan_change` already consumes. `load()` SHALL raise one of the typed exceptions from REQ-DRIFT-DETECTION-4 (`GraphMissing`, `GraphMalformed`, `PermissionDenied`, `SnapshotEnvelopeCorrupt`) on failure — NOT bare `Exception` or `RuntimeError`. Two concrete adapters SHALL implement this Protocol: `LiveDiskGraphLoader(graph_json_path: Path)` for the live disk path and `SnapshotGraphLoader(snap_id: str)` for the snapshot-pinned path.

#### Scenario: LiveDiskGraphLoader returns the same 3-tuple shape as the legacy `load_graph` happy path

- GIVEN a `graph.json` fixture at `<tmp>/graph.json` containing 2 valid nodes
- WHEN `loader = LiveDiskGraphLoader(Path("<tmp>/graph.json"); loader.load()` is called
- THEN the returned tuple is `(current_nodes, current_id_map, mtime)` matching `tests/unit/test_decision_drift.py::TestLoadGraph::test_load_graph_returns_index_tuple` byte-for-byte (modulo `mtime` epoch value)

#### Scenario: LiveDiskGraphLoader raises GraphMissing when path is absent

- GIVEN `graph_json_path` pointing at a non-existent file
- WHEN `loader.load()` is called
- THEN `GraphMissing` is raised (a subclass of the typed hierarchy from REQ-DRIFT-DETECTION-4)
- AND the message references the path so callers can render `--graph-json=<path>` hints

#### Scenario: SnapshotGraphLoader round-trips through SnapshotManager.show without a `_DummyBackend`

- GIVEN a snapshot envelope with `graph_state.graph_json_content`
- WHEN `loader = SnapshotGraphLoader(snap_id); loader.load()` is called
- THEN the loader calls `snapshot_manager.show(snap_id)` directly
- AND no `_DummyBackend` instance is constructed (verifiable via `grep -c "_DummyBackend" src/flow_engineering/decision_drift.py` returning 0 after Slice 1)

**Source**: explore.md §2.1 ("Tight coupling: 7 responsibilities in `scan_change`"), §2.2 ("Three graph-load paths conflated in `load_graph`"), §4 (Slice 1). Linked debt items: `_DummyBackend` is a fixture-as-type (§2.3); the 4 distinct fail-open paths in `load_graph` collapse indistinguishably (§2.2).

### Requirement: REQ-DRIFT-DETECTION-2 — ObservationSource Protocol

The system SHALL provide an `ObservationSource` `typing.Protocol` at `src/flow_engineering/drift/_observation_source.py` with a single method:

- `def iter_observations(self) -> Iterable[dict]`

Returning the filtered observation stream that `scan_change` already iterates. Concrete adapters SHALL consume `Iterable[observation]` directly — NOT via `_DummyBackend` or any backend-shape shim. The protocol MUST NOT require `mem_search` (the unused method that `_DummyBackend` carried).

#### Scenario: BackendObservationSource wraps an existing EngramBackend + filter chain

- GIVEN an `InMemoryBackend` populated with 5 observations, 3 of which match `topic_key` prefix `sdd/<change>/`
- WHEN `source = BackendObservationSource(backend, change_name="<change>"); list(source.iter_observations())` is called
- THEN the returned iterable has exactly 3 observations
- AND all returned observations have `topic_key` starting with `sdd/<change>/`
- AND the `since=<epoch>` filter chain is honored (observations with `created_at < since` are dropped)

#### Scenario: ObservationSource Protocol has no `mem_search` requirement

- GIVEN the Protocol definition
- WHEN `inspect.getsource(ObservationSource)` is inspected
- THEN the protocol declares ONLY `iter_observations` as a method
- AND a minimal adapter implementing only `iter_observations` (e.g., a stub returning `[]`) satisfies `isinstance(obj, ObservationSource)` at mypy time

#### Scenario: FrozenBackendObservationSource rebuilds InMemoryBackend from snapshot.observations

- GIVEN a snapshot envelope whose `graph_state.observations` is a list of 4 observation dicts
- WHEN `source = FrozenBackendObservationSource(snap_id); list(source.iter_observations())` is called
- THEN the returned iterable has exactly 4 observations
- AND each observation's `id` (int) matches the snapshot's id at the same position

**Source**: explore.md §2.1 ("Tight coupling: 7 responsibilities in `scan_change`"), §2.3 ("`_DummyBackend` is a fixture-as-type"), §4 (Slice 1). The Protocol boundary replaces the `_DummyBackend` + `_frozen_backend_from_snapshot` indirection.

### Requirement: REQ-DRIFT-DETECTION-3 — `scan_change` thin-coordinator refactor

The system SHALL refactor `decision_drift.scan_change(change_name, *, graph_json_path, backend, include_obsolete, since, snap_id) -> DriftReport` so the function body becomes a thin coordinator (~170 LOC) over the 2 Protocols from REQ-DRIFT-DETECTION-1 + REQ-DRIFT-DETECTION-2. The PUBLIC SIGNATURE (parameter names, types, defaults, return type) SHALL remain UNCHANGED. The internal flow SHALL be:

1. Validate kwargs (snap_id × backend mutual exclusion) — UNCHANGED.
2. Build a `GraphLoader` via an internal `_build_loader(*, graph_json_path, snap_id)` helper that dispatches to `SnapshotGraphLoader(snap_id)` when `snap_id` is set, else `LiveDiskGraphLoader(graph_json_path or DEFAULT_GRAPH_JSON)`.
3. Build an `ObservationSource` via an internal `_build_source(*, backend, snap_id, change_name)` helper.
4. Call `loader.load()` → catch typed exceptions → map to `DriftReport(unable_reason=...)` per REQ-DRIFT-DETECTION-6.
5. Iterate `source.iter_observations()` → filter → classify per binding → detect contradicted → build `DriftReport`.

The 4 distinct `except Exception: continue/pass` blocks at lines 602-603, 671-672, 699-700, 726-733 of `decision_drift.py` SHALL each be replaced with a narrower `except <SpecificException>:` clause tied to the typed hierarchy from REQ-DRIFT-DETECTION-4.

#### Scenario: Public signature is byte-identical to the v1.2.0 baseline

- GIVEN `scan_change` is defined in `src/flow_engineering/decision_drift.py`
- WHEN `inspect.signature(scan_change)` is called after Slice 1
- THEN the signature equals `(change_name, *, graph_json_path=None, backend=None, include_obsolete=False, since=None, snap_id=None) -> DriftReport`
- AND the parameter order, types, and defaults match the v1.2.0 baseline captured at `git show e50adb6:src/flow_engineering/decision_drift.py | grep -A 10 "^def scan_change"`

#### Scenario: `scan_change` LOC reduces from 250 → ≤ 200

- GIVEN the post-refactor `decision_drift.py`
- WHEN `git diff origin/main..HEAD -- src/flow_engineering/decision_drift.py` is run
- THEN the diff for `scan_change` (lines that belonged to the function at v1.2.0 baseline) shows the function body shrinks by at least 50 LOC
- AND `wc -l` of the function (extracted via `python -c "import ast,inspect; ..."`) reports ≤ 200 LOC

#### Scenario: Each broad `except Exception` clause is narrowed to a specific typed exception

- GIVEN the post-refactor `decision_drift.py`
- WHEN `grep -n "except Exception" src/flow_engineering/decision_drift.py` is run
- THEN the output shows zero `except Exception:` lines WITHOUT a typed-exception clause nearby
- AND any remaining `except Exception` is paired with a `# noqa: BLE001` comment justifying the broad catch (e.g., for backwards-compat with external callers)

#### Scenario: All 9 existing test files pass with ZERO edits

- GIVEN the existing 9 unit test files (`tests/unit/test_decision_drift.py`, `test_decision_drift_snap_id.py`, `test_decision_drift_v080_migration.py`, `test_decision_drift_v090_hardening.py`, `test_cli_drift.py`, `test_cli_drift_events_list.py`, `test_cli_drift_events_tail.py`, `test_cli_drift_events_stats.py`, `test_cli_drift_events_alias.py`) plus 2 BDD step files
- WHEN `uv run pytest` is run after Slice 1
- THEN 1,678/1,678 unit tests pass (the v1.2.0 baseline count)
- AND 182/182 BDD scenarios pass
- AND `git diff origin/main..HEAD -- tests/` shows zero modifications to existing test files

**Source**: explore.md §2.1 ("Tight coupling: 7 responsibilities in `scan_change`") + §4 (Slice 1 size: "function shrinks from 250 → ~170 LOC"). The 4 distinct `except Exception:` blocks at lines 602-603 / 671-672 / 699-700 / 726-733 are the explicit code anchors.

### Requirement: REQ-DRIFT-DETECTION-4 — Typed exception hierarchy

The system SHALL provide a 4-class typed exception hierarchy at `src/flow_engineering/drift/_graph_loader.py`, each inheriting from `Exception` (NOT bare `RuntimeError` or `ValueError`), with a common base `GraphLoadError(Exception)`:

| Exception | Raised when | Replaces |
|---|---|---|
| `GraphMissing` | The graph file does not exist (`graph_json_path.exists() is False`) | Bare `(None, None, None)` fail-open path C in `load_graph:238` |
| `GraphMalformed` | The graph file exists but `json.loads()` raises `JSONDecodeError`, OR the top-level shape is not a dict, OR the `nodes` field is not a list | Bare `(None, None, None)` fail-open path D in `load_graph:242-248` |
| `PermissionDenied` | `OSError` with `errno` in `{EACCES, EPERM, EROFS}` while reading the graph file | Indistinguishable `OSError` swallow in `load_graph:242` |
| `SnapshotEnvelopeCorrupt` | `SnapshotEnvelopeError` raised by `snapshot_manager.show(snap_id)` | Indistinguishable `(None, None, None)` swallow in `_load_graph_from_snapshot:314-315` |

All 4 SHALL carry a human-readable `message` attribute that references the path or `snap_id` so callers can render structured CLI errors.

#### Scenario: `GraphMissing` is distinct from `GraphMalformed` at the type system

- GIVEN the typed hierarchy is defined
- WHEN `issubclass(GraphMissing, GraphLoadError)` and `issubclass(GraphMalformed, GraphLoadError)` are checked
- THEN both return `True`
- AND `issubclass(GraphMissing, GraphMalformed)` returns `False` (siblings, not parent-child)

#### Scenario: `PermissionDenied` is raised for `EACCES`/`EPERM`/`EROFS` errno values

- GIVEN a `graph_json_path` whose read raises `PermissionError` (`errno=EACCES`)
- WHEN `LiveDiskGraphLoader(graph_json_path).load()` is called
- THEN `PermissionDenied` is raised (NOT bare `PermissionError` or `OSError`)
- AND the message includes the path

#### Scenario: `SnapshotEnvelopeCorrupt` is raised when `SnapshotManager.show()` raises `SnapshotEnvelopeError`

- GIVEN a `snap_id` whose envelope fails the sha256 integrity check
- WHEN `SnapshotGraphLoader(snap_id).load()` is called
- THEN `SnapshotEnvelopeCorrupt` is raised
- AND `cli/drift.py` still catches the legacy `SnapshotGraphMissing` alias (REQ-DRIFT-DETECTION-7 covers the alias re-export)

**Source**: explore.md §2.2 ("Three graph-load paths conflated in `load_graph`") + §2.5 ("`unable_reason` declared but never populated"). The 4 distinct failure modes that currently collapse to `(None, None, None)` are now distinguishable types.

### Requirement: REQ-DRIFT-DETECTION-5 — `_DummyBackend` removal

The system SHALL REMOVE the `_DummyBackend` class from `src/flow_engineering/decision_drift.py:362-376`. The class is a fixture-as-type — it exists only to satisfy `SnapshotManager(..., backend=...)`'s constructor signature, and neither `iter_observations` nor `mem_search` are reachable code paths (per `# pragma: no cover` markers). After Slice 1, all 3 call sites at `decision_drift.py:311, 410, 438` SHALL be refactored to either pass `None` (if `SnapshotManager` accepts it) or to use a no-op stub defined inside the new `drift/_graph_loader.py` module.

#### Scenario: `_DummyBackend` is no longer importable from `decision_drift`

- GIVEN the post-Slice-1 `decision_drift.py`
- WHEN `python -c "from flow_engineering.decision_drift import _DummyBackend"` is executed
- THEN `ImportError` is raised
- AND `grep -c "_DummyBackend" src/flow_engineering/decision_drift.py` returns `0`

#### Scenario: All 3 prior `_DummyBackend()` call sites compile without it

- GIVEN the post-Slice-1 `decision_drift.py`
- WHEN `grep -n "_DummyBackend" src/flow_engineering/decision_drift.py` is run
- THEN the output is empty
- AND the 3 prior call sites now use either `SnapshotManager(..., backend=None)` (if the constructor permits) or a local no-op stub scoped to the `_graph_loader.py` module

**Source**: explore.md §2.3 ("`_DummyBackend` is a fixture-as-type"). The class is unreachable per the `# pragma: no cover` markers; the only motivation is constructor-shape compliance that the Protocol refactor obviates.

### Requirement: REQ-DRIFT-DETECTION-6 — `unable_reason` population from typed exceptions

The system SHALL populate `DriftReport.unable_reason: str | None` (currently always `None` per `decision_drift.py:111, 727-733`) from the typed exception hierarchy in REQ-DRIFT-DETECTION-4 when a graph-load failure is caught. The mapping SHALL be:

| Caught exception | `unable_reason` value |
|---|---|
| `GraphMissing` | `"graph_file_missing"` |
| `GraphMalformed` | `"graph_file_malformed"` |
| `PermissionDenied` | `"graph_file_unreadable"` |
| `SnapshotEnvelopeCorrupt` | `"snapshot_envelope_corrupt"` |
| Any other exception (still fail-open per REQ-14) | `None` (unchanged behavior — only typed exceptions populate the field) |

The `SnapshotGraphMissing` raise site at `decision_drift.py:571` (a `ValueError` subclass, NOT a graph-load failure — it's the D2 graceful degradation signal) SHALL remain a `raise` rather than a `return` per REQ-33 contract.

#### Scenario: `unable_reason` is `"graph_file_missing"` when the graph file is absent

- GIVEN `graph_json_path` pointing at a non-existent file
- WHEN `scan_change(change_name, graph_json_path=<missing_path>)` is called
- THEN the returned `DriftReport.unable_reason == "graph_file_missing"`
- AND `DriftReport.graph_unavailable is True`

#### Scenario: `unable_reason` is `"graph_file_malformed"` when JSON parsing fails

- GIVEN a `graph.json` fixture containing the string `"{not valid json"`
- WHEN `scan_change(change_name, graph_json_path=<malformed_path>)` is called
- THEN the returned `DriftReport.unable_reason == "graph_file_malformed"`
- AND `DriftReport.graph_unavailable is True`

#### Scenario: `unable_reason` defaults to `None` for non-graph-load failures

- GIVEN a snapshot-pinned scan that raises `SnapshotGraphMissing` (the D2 graceful degradation signal)
- WHEN `scan_change(change_name, snap_id=<no-graph-snap>)` is called
- THEN the function raises `SnapshotGraphMissing` (NOT a `DriftReport` with `unable_reason` set) — the existing REQ-33 contract is preserved

#### Scenario: Backwards-compat — `unable_reason=None` still works for callers that don't read the field

- GIVEN any successful drift scan (graph loaded, classifications emitted)
- WHEN the returned `DriftReport` is inspected
- THEN `unable_reason is None` (default value preserved for the happy path)
- AND existing tests that do NOT assert on `unable_reason` (e.g., `tests/unit/test_decision_drift.py`) pass unchanged

**Source**: explore.md §2.5 ("`unable_reason` declared but never populated") + §3.3 (per-finding graph_unavailable refinement extension point, deferred). The field exists in the dataclass but every error path returns `None`; this REQ wires the typed exceptions to the field.

### Requirement: REQ-DRIFT-DETECTION-7 — `SnapshotGraphMissing` canonical relocation

The system SHALL make `SnapshotGraphMissing` canonical at `src/flow_engineering/snapshot_manager.py` (the file that already carries `SnapshotGraphMissingError` at lines 81-101 plus the v1.1.6 PEP 562 alias at lines 113-124). The current duplicate class definition at `decision_drift.py:179-187` SHALL be DELETED, and `decision_drift.py` SHALL re-export `SnapshotGraphMissing` via a PEP 562 `__getattr__` for backward-compat with batch B1 BDD tests that import from `flow_engineering.decision_drift`. The v1.1.6 alias convention (canonical name in `snapshot_manager` + deprecation alias in `decision_drift`) is honored — Slice 1 FLIPS the canonical raise site rather than introducing a parallel hierarchy.

#### Scenario: `SnapshotGraphMissing` raises from the canonical `snapshot_manager` site

- GIVEN the post-Slice-1 code
- WHEN `python -c "from flow_engineering.snapshot_manager import SnapshotGraphMissing; print(SnapshotGraphMissing.__module__)"` is run
- THEN the output is `flow_engineering.snapshot_manager` (NOT `flow_engineering.decision_drift`)

#### Scenario: Backward-compat re-export from `decision_drift` emits DeprecationWarning

- GIVEN `SnapshotGraphMissing` is canonical at `snapshot_manager.py` and only re-exported from `decision_drift.py`
- WHEN `python -W default -c "from flow_engineering.decision_drift import SnapshotGraphMissing; print(SnapshotGraphMissing)"` is run
- THEN a `DeprecationWarning` matching the v1.1.6 precedent ("`SnapshotGraphMissing` is deprecated; import `SnapshotGraphMissingError` instead") is emitted
- AND the imported class is the SAME object as `flow_engineering.snapshot_manager.SnapshotGraphMissingError`

#### Scenario: `cli/drift.py:351` continues to catch the re-exported alias

- GIVEN `cli/drift.py` catches `decision_drift.SnapshotGraphMissing` at line 351
- WHEN a snapshot-pinned scan triggers the D2 graceful degradation raise
- THEN the CLI's `except` block fires
- AND the user sees the same structured error as on the v1.2.0 baseline

**Source**: explore.md §2.4 ("`SnapshotGraphMissing` belongs in `snapshot_manager.py`"). The v1.1.6 cycle created `SnapshotGraphMissingError` as canonical with `SnapshotGraphMissing` as 1-release alias — the alias raise site was never flipped, so Slice 1 completes the relocation.

### Requirement: REQ-DRIFT-DETECTION-8 — Adapter-compat layer preserving public kwargs

The system SHALL provide an internal adapter-compat layer (in `decision_drift.py`) that maps the existing public kwargs to the 2 Protocols, so that:

- All callers (`flow drift <change>` CLI, `flow drift run`, `daemon.handle_apply_progress_event`, `tests/unit/test_decision_drift*.py`) continue to invoke `scan_change(change_name, *, graph_json_path, backend, include_obsolete, since, snap_id)` WITHOUT any caller-side change.
- The public kwargs surface remains the single source of truth for scan parameters — the Protocols are INTERNAL collaborators, not a new public API.
- The 9 existing test files (~6,400 LOC) invoke `scan_change` directly and SHALL pass unchanged (verified by `git diff origin/main..HEAD -- tests/` showing zero modifications to existing test files).

The adapter-compat layer SHALL live as 2 private helpers in `decision_drift.py`: `_build_loader(*, graph_json_path, snap_id) -> GraphLoader` and `_build_source(*, backend, snap_id, change_name) -> ObservationSource`. The internal `_scan_with_protocols(loader, source, ...)` helper holds the post-refactor coordinator body.

#### Scenario: All existing call sites pass unchanged

- GIVEN the post-Slice-1 `decision_drift.py`
- WHEN `grep -rn "scan_change(" src/ tests/` is run
- THEN every match uses kwargs in the v1.2.0 form: `scan_change(change_name, *, graph_json_path=..., backend=..., include_obsolete=..., since=..., snap_id=...)`
- AND no caller imports `GraphLoader` or `ObservationSource` directly (Protocols are internal)

#### Scenario: Adapter produces byte-identical DriftReport for legacy kwargs

- GIVEN a fixture covering BOTH the live-disk path (`graph_json_path=<tmp>`) and the snapshot-pinned path (`snap_id=<snap-with-graph>`)
- WHEN `scan_change(change_name, graph_json_path=...)` is called pre-Slice-1 baseline (captured at `git show e50adb6`)
- AND the same call is made post-Slice-1
- THEN both `DriftReport` instances have identical `scanned_at` (after `_epoch_to_iso`), `class_counts`, `findings`, and `graph_unavailable`/`unable_reason` fields (modulo the `unable_reason` addition from REQ-DRIFT-DETECTION-6 for the failure paths)

#### Scenario: New unit tests cover the adapter's kwarg→Protocol dispatch

- GIVEN the new test file `tests/unit/test_decision_drift_graph_loader.py` (NEW, ~120 LOC)
- WHEN it imports `flow_engineering.drift._graph_loader` and exercises `_build_loader` via mock kwargs
- THEN the test asserts that `snap_id` activates `SnapshotGraphLoader` and `graph_json_path` activates `LiveDiskGraphLoader`
- AND the test asserts the mutual-exclusion `ValueError` (`scan_change: snap_id and backend are mutually exclusive`) fires when both `snap_id` AND `backend` are non-None

**Source**: explore.md §4 (Slice 1 risk #1: "`scan_change` adapter-compat layer drifts from canonical kwargs") + §1.4 ("What's stable"). The kwargs surface is the public contract; the Protocols are an implementation detail.

## 3. Out of scope (deferred to follow-up SDD changes)

The following items are EXPLICITLY NOT part of this delta spec. Each is a candidate for its own follow-up change with its own spec:

| Deferred | Reason | Follow-up change |
|---|---|---|
| OTel push exporter | External dep (`opentelemetry-sdk`); requires deps approval + dedicated spec | `drift-otel-push` (NEW change) |
| Cross-project drift federation | New feature, not refactor; needs design spike | `drift-cross-project-federation` (NEW change) |
| Per-finding `graph_unavailable` refinement | Requires Slice 1's typed exception hierarchy as a prerequisite; introduces new REQ (per `explore.md` §3.3) + new BDD scenarios | `drift-per-finding-graph-unavailable` (Slice 3, separate change) |
| Unified JSONL rotation helper | Pure deduplication (`drift_event_log._rotate_if_needed` ↔ `observability._rotate_metrics_if_needed`); ~80 LOC; independent of Slice 1 | `drift-detection-rotation` (Slice 2, separate change) |
| `decision_drift.py` file split (4 submodules) | Mechanical; mirrors v1.3-cli-split but `decision_drift.py` is tightly coupled — splitting without Slice 1's extraction-first duplicates the god-module pattern in 4 places | Deferred until Slice 1 lands |
| `_write_back_findings` lazy-import refactor | Slice 4 v1.3-cli-split artifact (Engram #2041); orthogonal to drift detection | Deferred per v1.3-cli-split |
| `classify_binding` + `_classify_with_id_map` collapse | Artificial 2-layer split (only 1 caller); deferred | Bundle with future `classify_binding` perf refactor |
| JSONL rotation DRY violation | Same as "Unified JSONL rotation helper" above | `drift-detection-rotation` (Slice 2) |

## 4. Verification approach

Strict-TDD posture is ON per `sdd-init/flow-engineering.md` (`strict_tdd: true`). The spec phase does NOT add tests; the apply phase enforces RED → GREEN → REFACTOR per the standard `sdd-apply` discipline.

### 4.1 Regression gate (existing tests — ZERO edits)

The 9 existing unit test files + 2 BDD step files are the strict regression gate:

| File | LOC | Coverage area |
|---|---|---|
| `tests/unit/test_decision_drift.py` | 558 | `classify_binding` + `scan_change` happy path + dataclass enforcement |
| `tests/unit/test_decision_drift_snap_id.py` | 620 | REQ-33 drift-pinned scan path |
| `tests/unit/test_decision_drift_v080_migration.py` | 230 | v0.8.0 dataclass shape |
| `tests/unit/test_decision_drift_v090_hardening.py` | 195 | v0.9.0 hard-break enforcement |
| `tests/unit/test_cli_drift.py` | 1,055 | CLI handlers + JSON serialization + table rendering |
| `tests/unit/test_cli_drift_events_list.py` | 365 | Read-side CLI subcommands |
| `tests/unit/test_cli_drift_events_tail.py` | 365 | Read-side CLI subcommands |
| `tests/unit/test_cli_drift_events_stats.py` | 365 | Read-side CLI subcommands |
| `tests/unit/test_cli_drift_events_alias.py` | 365 | Hyphenated `flow drift-events` deprecated alias |
| `tests/bdd/test_decision_reality_drift_steps.py` | 2,360 | BDD scenarios for REQ-10..16 |
| `tests/bdd/test_req_v1_0_drift_events_steps.py` | 245 | BDD scenarios for REQ-V1.0.2/3 |

Pass criterion: `git diff origin/main..HEAD -- tests/` shows ZERO modifications; `uv run pytest` reports the v1.2.0 baseline of 1,678 passing tests + 182 passing BDD scenarios (or higher).

### 4.2 New unit tests (apply phase writes these RED → GREEN)

| File | LOC | Coverage |
|---|---|---|
| `tests/unit/test_decision_drift_graph_loader.py` (NEW) | ~120 | Protocol contract tests + 2 adapter behavior tests + 4 exception-population tests |
| `tests/unit/test_decision_drift_observation_source.py` (NEW) | ~80 | Protocol contract tests + filter-logic tests + FrozenBackendObservationSource round-trip |

Pass criterion: each new test fails RED first (asserting the Protocol's contract surface), then passes GREEN after the adapter is implemented.

### 4.3 Static checks

- Ruff: clean on changed files (per the project standard).
- Mypy: clean on changed files (the new Protocol definitions may surface residual type debt — `mitigation per proposal Risk #4`).
- `grep -c "_DummyBackend" src/flow_engineering/decision_drift.py` returns 0 (REQ-DRIFT-DETECTION-5).
- `git diff --stat origin/main..HEAD -- src/flow_engineering/decision_drift.py` shows `scan_change` LOC reduced (REQ-DRIFT-DETECTION-3).

### 4.4 Spec/design drift check

The sdd-verify phase runs the spec/design drift gate to confirm:

- All 8 ADDED Requirements in this delta spec have at least 1 scenario OR explicit "covered by existing test" pointer.
- Each REQ's "Source: explore.md §X.Y" pointer resolves to a non-empty section in `explore.md`.
- The 9 existing root capability REQs (REQ-9..16 + REQ-55..59) in `openspec/specs/decision-drift/spec.md` are NOT modified by this delta spec (the proposal's "Modified Capabilities" section declares NO requirement changes).

## 5. Cross-references

- Proposal: `openspec/changes/drift-detection/proposal.md` (18 KB; Slice 1 locked in)
- Explore: `openspec/changes/drift-detection/explore.md` (27 KB; 3 candidate slices mapped)
- Root capability spec: `openspec/specs/decision-drift/spec.md` (REQ-9..16 + REQ-55..59; 56 KB)
- v1.3-cli-split delta spec precedent: `openspec/changes/archive/2026-07-08-v1.3-cli-split/specs/cli-split/spec.md`
- Snapshot manager canonical exception: `src/flow_engineering/snapshot_manager.py:81-101` (`SnapshotGraphMissingError`) + lines 113-124 (PEP 562 `__getattr__` alias)
- Implementation anchor: `src/flow_engineering/decision_drift.py:485-734` (`scan_change`)
- CLI consumer anchor: `src/flow_engineering/cli/drift.py:351-363` (`SnapshotGraphMissing` catch)
- v1.1.6 alias convention precedent: `openspec/changes/archive/2026-06-28-v1.1-followups/` (REQ-V1.1.6)
- Strict TDD marker: `sdd-init/flow-engineering.md:4` (`strict_tdd: true`)

## 6. Acceptance criteria

The delta spec is ACCEPTED at archive time when:

- [ ] `uv run pytest` reports 1,678+ tests passing + 182/182 BDD scenarios passing with ZERO modifications to existing 9 test files + 2 BDD step files.
- [ ] The 8 ADDED Requirements have at least 1 scenario each (16+ total scenarios).
- [ ] The 4 typed exceptions (`GraphMissing`, `GraphMalformed`, `PermissionDenied`, `SnapshotEnvelopeCorrupt`) are exercised by new unit tests.
- [ ] `unable_reason` is populated on at least 2 error paths (e.g., `GraphMissing` + `SnapshotEnvelopeCorrupt`).
- [ ] `_DummyBackend` class REMOVED from `decision_drift.py` (verifiable via `grep -c "_DummyBackend" src/flow_engineering/decision_drift.py` returning 0).
- [ ] `SnapshotGraphMissing` canonical raise site is `flow_engineering.snapshot_manager` (verifiable via `__module__` introspection).
- [ ] `scan_change` LOC reduced from 250 → ≤ 200.
- [ ] Ruff clean on changed files; mypy clean on changed files.
- [ ] PR diff ≤ 400 LOC OR includes the REQ-CLI-SPLIT-5 "Mechanical extraction, not new logic" justification paragraph.
- [ ] Public API surface (`from flow_engineering.decision_drift import *`) UNCHANGED — verifiable via `python -c "import flow_engineering.decision_drift; ..."`.

## 7. Spec phase return envelope

```yaml
status: success
confidence: high
change: drift-detection
slice: 1 (GraphLoader + ObservationSource Protocols)
pr_split: single PR OR 2-PR chained split (per proposal §"Review budget posture")
total_reqs: 8
total_bdd_scenarios: 25
file_created: openspec/changes/drift-detection/specs/drift-detection/spec.md
next_recommended: sdd-design drift-detection
notes:
  - This is a STRUCTURAL delta (no MODIFIED Requirements, no REMOVED Requirements)
  - Root capability spec (openspec/specs/decision-drift/spec.md REQ-9..16 + REQ-55..59) is NOT touched
  - Slice 1 is the prerequisite for Slice 3 (per-finding graph_unavailable refinement)
  - Slice 2 (unified JSONL rotation helper) is independent and could ship in parallel
  - Strict-TDD posture is ON for the apply phase; tests are written RED → GREEN per the standard discipline
```