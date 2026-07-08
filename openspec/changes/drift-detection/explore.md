<!-- explore.md: drift-detection change. Phase: explore (sdd-explore). Source: orchestrator kick-off 2026-07-08. Scope: map architectural debt + candidate refactor slices. NOT a design / spec / tasks doc. -->
# Explore: decision-drift architectural refactor

**Change**: `drift-detection` (new, not yet specified)
**Authoring**: sdd-explore sub-agent, 2026-07-08
**HEAD**: `e50adb6` (post v1.3-cli-split archive + 3-orphan closeout)
**Scope**: map the territory — architectural debt, extension points, candidate refactor slices. NO REQs proposed.

## Context

The `decision-drift` capability catalog (`openspec/specs/decision-drift/spec.md`, 56 KB / 533 lines) carries **10 root REQs (REQ-9..16, REQ-55..59)** that span 6 shipped versions (v0.3.0 → v1.2.0). The capability is feature-complete and well-tested (1678 pytest pass + 182/182 BDD scenarios + 24+ dedicated drift feature files).

The user's strategic intent (per Engram memory #2041, #2038): **"drift_detection architectural refactor"** as the pivot after v1.3-cli-split. The honest read flagged the capability as "the most isolated domain" — high isolation makes it the lowest-risk refactor target in the codebase.

This explore phase maps (a) what shipped and what's brittle, (b) what architectural debt is actually present, (c) what extension points the spec mentions but no code implements, and (d) 3 concrete refactor slices sized for the 400-LOC single-PR budget (per `cli/spec.md` REQ-CLI-SPLIT-5 + Engram pattern).

---

## 1. Current state of decision-drift

### 1.1 What shipped (versioning timeline)

| Version | Surface | File(s) | REQs | Notes |
|---------|---------|---------|------|-------|
| v0.3.0 | `flow drift <change>` (legacy positional) | `decision_drift.py:485` `scan_change` | REQ-9..16 | First drift detection; `decision_id: str` + epoch `scanned_at` |
| v0.8.0 | JSONL audit trail + dataclass shape migration (compat shim) | `drift_event_log.py` + `decision_drift.py` | REQ-55..59 | 21 NEW BDD scenarios; 1-release compat shim |
| v0.9.0 | Compat shim REMOVED (hard break) | `decision_drift.py:85-91, 336-364` | REQ-V9.1..V9.5 | `Finding.decision_id: int` enforced at boundary |
| v1.0.0 | JSONL wire-format `int` flip + read-side CLI | `drift_event_log.py:74` + `cli/__init__.py` | REQ-V1.0.1..V1.0.4 | `flow drift-events {list,tail,stats}` |
| v1.1.0 | DriftEventLog rotation + S2 hardening + `SnapshotGraphMissingError` | `drift_event_log.py:196-254` | REQ-V1.1.1..V1.1.6 | Mirrors metrics.jsonl rotation pattern |
| v1.2.0 | Path A nested group (`flow drift events {list,tail,stats}`) + `flow drift run` | `cli/drift.py` (Slice 4 of v1.3-cli-split) | REQ-V1.2.1..V1.2.4 | Hyphenated `flow drift-events` deprecated for 1 release |
| v1.3.0 | Mechanical CLI split | `cli/drift.py` 891 LOC relocated | (no behavioral REQ) | Cleanly separated from monolith |

### 1.2 Module footprint (current `main`)

| File | LOC | Role | Stability |
|------|-----|------|-----------|
| `src/flow_engineering/decision_drift.py` | 734 | Pure classifier + scan orchestrator + graph loader + snapshot-pinned helpers | Stable public API (`classify_binding`, `scan_change`, `DriftReport`, `Finding`, `DriftClass`) |
| `src/flow_engineering/drift_event_log.py` | 255 | JSONL append-only writer + reader + rotation | Stable (v1.1 + v1.0 hardening) |
| `src/flow_engineering/cli/drift.py` | 891 | `flow drift run` + `flow drift events {list,tail,stats}` + deprecated `flow drift-events` alias | Stable (v1.3-cli-split) |
| `src/flow_engineering/daemon.py` | 265 | `_append_drift_events` + `handle_apply_progress_event` (REQ-15 daemon seam) | Stable |
| `src/flow_engineering/observability.py` | 1675 | `record_drift_summary` (lines 438-474) emits 8 counters | Stable |

### 1.3 Test surface

| File | LOC | Coverage |
|------|-----|----------|
| `tests/unit/test_decision_drift.py` | 558 | `classify_binding` + `scan_change` happy path + dataclass enforcement |
| `tests/unit/test_decision_drift_v080_migration.py` | 230 | v0.8.0 dataclass shape |
| `tests/unit/test_decision_drift_v090_hardening.py` | 195 | v0.9.0 hard-break enforcement |
| `tests/unit/test_decision_drift_snap_id.py` | 620 | REQ-33 drift-pinned scan path |
| `tests/unit/test_cli_drift.py` | 1055 | CLI handlers + JSON serialization + table rendering |
| `tests/unit/test_cli_drift_events_{list,tail,stats,alias}.py` | 365 | Read-side CLI subcommands |
| `tests/unit/test_drift_event_log.py` | 740 | JSONL writer + reader + rotation + S2 hardening |
| `tests/bdd/test_decision_reality_drift_steps.py` | 2360 | BDD scenarios for REQ-10..16 |
| `tests/bdd/test_req_v1_0_drift_events_steps.py` | 245 | BDD scenarios for REQ-V1.0.2/3 |

**Total drift-related tests**: ~6 400 LOC across 9 unit files + 2 BDD files = comprehensive coverage. Any refactor MUST keep these green.

### 1.4 What's stable

- **Public dataclass contract** (`Finding`, `DriftReport`, `DriftClass`): hard-typed since v0.9.0; any refactor must preserve field names + types.
- **Wire format** (JSONL `{ts, change, decision_id, binding_id, class, detected_at}`): on-disk files since v0.8.0 are still readable.
- **Exit codes** (0/1/2/3 from `_drift_exit_code`): operator-facing contract since v0.3.0.
- **Counter names** (8 `drift_*_total`): Prometheus / dashboard consumers depend on these.
- **6 SKILL.md drift-detection hooks**: REQ-16 contract (sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md) — externally audited.

### 1.5 What's brittle (preliminary; refined in §2)

1. `scan_change` at 250 LOC does 7 distinct things in one function.
2. Three graph-load paths are conflated in `load_graph` with silent fail-open.
3. `SnapshotGraphMissing` lives in `decision_drift.py` despite being a snapshot concern.
4. `_DummyBackend` is a fixture-as-type smell.
5. `unable_reason: str | None` is declared but never populated.
6. Per-row `except Exception: continue` swallows every kind of error.
7. `drift_event_log.py` rotation duplicates `observability.py` rotation.
8. `classify_binding` + `_classify_with_id_map` form a 2-layer trivial split.

---

## 2. Architectural debt (code-level evidence)

### 2.1 Tight coupling: 7 responsibilities in `scan_change`

`decision_drift.py:485-734` — 250 LOC function:

```
1. Validate kwargs (snap_id × backend mutual exclusion) .................. lines 537-543
2. Load graph (live OR snapshot-pinned path) ............................. lines 544-594
3. Snapshot existence / graph-content check (SnapshotGraphMissing raise) .. lines 552-574
4. Acquire observation source (InMemoryBackend default OR frozen backend) .. lines 583, 596-598
5. Filter observations by topic_key prefix + created_at cutoff ........... lines 605-615
6. Per-observation loop: extract_code_refs + classify_binding + OBSOLETE  .. lines 617-672
7. Contradiction re-classification ........................................ lines 674-700
8. Aggregate class_counts + build DriftReport ............................ lines 702-719
9. Top-level Exception swallow → empty report ............................ lines 726-733
```

**Smell**: each step has its own failure mode, but `scan_change` couples them into a single function. A unit test for "graph load fails" must also mock the entire observation loop.

**Evidence**: 3 distinct `except Exception:` blocks (lines 602-603, 671-672, 699-700, 726-733) each swallow different error classes for different reasons — but the silence is uniform.

### 2.2 Three graph-load paths conflated in `load_graph`

`decision_drift.py:200-249`:

```python
def load_graph(graph_json_path=None, *, snap_id=None):
    if snap_id and graph_json_path:
        raise ValueError(...)                              # mutual exclusion
    if snap_id:
        return _load_graph_from_snapshot(snap_id)          # path A
    if graph_json_path is None:
        return (None, None, None)                          # path B (fail-open)
    try:
        if not graph_json_path.exists():
            return (None, None, None)                      # path C (fail-open)
        ...
    except (OSError, json.JSONDecodeError, ValueError):
        return (None, None, None)                          # path D (fail-open)
    ...
```

**Smell**: 4 distinct failure modes all collapse to `(None, None, None)`. Caller can't distinguish "missing" from "malformed" from "permission denied". Inside `_load_graph_from_snapshot` (lines 277-359), there's an additional sub-path: write JSON to temp file then re-read — unnecessary round-trip on a hot path.

### 2.3 `_DummyBackend` is a fixture-as-type

`decision_drift.py:362-376`:

```python
class _DummyBackend:
    """Backend stub used by ``_load_graph_from_snapshot``."""
    def iter_observations(self, *, project=None): return []
    def mem_search(self, *args, **kwargs): return []
```

**Smell**: exists ONLY to satisfy `SnapshotManager(snapshots_dir=..., backend=...)` constructor (line 311). The two methods it implements are unreachable (`# pragma: no cover`). Type-system smell — should be a `Protocol` or `None` should be accepted.

### 2.4 `SnapshotGraphMissing` belongs in `snapshot_manager.py`

`decision_drift.py:179-187` defines it; `_load_graph_from_snapshot` raises it; only `cli/drift.py:351-363` catches it.

**Smell**: domain exception lives in the wrong module. The v1.1 cycle created `SnapshotGraphMissingError` in `snapshot_manager.py` (the canonical class) but kept `SnapshotGraphMissing` as a 1-release alias — and the alias is still being raised. The new exception should be the canonical raise site.

### 2.5 `unable_reason` declared but never populated

`decision_drift.py:111` declares the field. `scan_change:727-733` returns:

```python
return DriftReport(
    change_name=change_name,
    scanned_at=scanned_at,
    graph_mtime=None,
    decisions_total=0,
    bindings_total=0,
    graph_unavailable=True,
    # unable_reason NOT SET — silently None
)
```

**Smell**: the field exists to distinguish "graph file missing" from "graph file malformed" from "permission denied" from "snapshot envelope corrupt" — but every error path returns `unable_reason=None`. The spec (line 195-200) calls out "structured JSON error pointing the user at `--graph-json=<path>`" — but only when `graph_unavailable=True` without differentiation.

### 2.6 `classify_binding` + `_classify_with_id_map` is an artificial split

`decision_drift.py:126-176`:

```python
def classify_binding(ref, graph_nodes):
    if not graph_nodes:
        return DriftClass.UNABLE_TO_VERIFY
    current_id_map = {...}
    return _classify_with_id_map(ref, graph_nodes, current_id_map)

def _classify_with_id_map(binding, current_nodes, current_id_map):
    # does the actual 4-step decision
```

**Smell**: the only purpose of the split is to allow callers who already precomputed `current_id_map` to skip the rebuild. But there's exactly 1 caller (`scan_change:662`), and the precompute is amortized across many bindings anyway. Pure over-abstraction; both functions could collapse into one with no perf cost.

### 2.7 Counter emission is split between library + CLI + daemon

- `observability.record_drift_summary(report)` at `observability.py:438-474` is the canonical emitter.
- `cli/drift.py:367` calls it after every `scan_change`.
- `daemon.py:105` calls it after every scan.
- `scan_change` itself does NOT call it (correct — pure library).

**Smell**: 2 call sites must remember to invoke `record_drift_summary`. If a 3rd consumer (e.g., scheduled CI scan, HTTP endpoint) is added, it has to remember too. Counter emission is a cross-cutting concern that should live in a DriftOrchestrator seam.

### 2.8 `drift_event_log.py` rotation duplicates `observability.py` rotation

`drift_event_log.py:196-254` (`_rotate_if_needed` + `_resolve_rotation_threshold_bytes` + `_resolve_max_age_days`):

```python
def _rotate_if_needed(path):
    threshold = _resolve_rotation_threshold_bytes()
    if threshold > 0 and path.exists():
        try:
            if path.stat().st_size >= threshold:
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                rotated = path.with_name(f"drift_events.{stamp}.jsonl")
                path.rename(rotated)
        except OSError:
            pass
    max_age_days = _resolve_max_age_days()
    if max_age_days <= 0: return
    cutoff = datetime.now(UTC).timestamp() - (max_age_days * 86400)
    parent = path.parent
    for sibling in parent.glob("drift_events.*.jsonl"):
        ...
```

**Smell**: REQ-V1.2.1 (`observability.py:_rotate_metrics_if_needed` + `_delete_stale_metrics_siblings`) implements EXACTLY the same pattern. The two helpers differ only in:
- Glob pattern (`drift_events.*.jsonl` vs `metrics.*.jsonl`)
- Env var names (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` vs `FLOW_METRICS_LOG_MAX_BYTES`)
- Constants (`ROTATE_BYTES_DEFAULT` vs `_DEFAULT_METRICS_MAX_BYTES`)

**Classic DRY violation**. A shared `_rotate_jsonl_if_needed(path, env_max_bytes, env_max_age_days, glob_pattern)` helper would eliminate ~40 LOC.

### 2.9 Lazy imports for test seams in `cli/drift.py:208-213`

```python
from flow_engineering.cli import (  # noqa: F401
    EngramClient as _EngramClient,
)
from flow_engineering.cli import (
    _default_save_backend,
)
```

**Smell**: `_write_back_findings` must re-import from `flow_engineering.cli` at call time so test monkeypatches (`monkeypatch.setattr("flow_engineering.cli.EngramClient", ...)`) take effect. This is the v1.3-cli-split Slice 3+4 lazy-import pattern (Engram memory #2041 "2-step test-seam pattern") — but it's an indicator that `_write_back_findings` is mis-located. A drift-domain module that depends on cli-package internals for test seams is fragile.

### 2.10 `_epoch_to_iso` dead-ish helper

`decision_drift.py:114-123`: docstring says "Used by `from_legacy` (REMOVED) and other v0.7.x migration sites". The only current caller is `scan_change:710` (`graph_mtime` coercion). Helper survives because the v0.8.0 contract is documented in `drift_event_log.py` too.

---

## 3. Extension points mentioned in spec, NOT yet implemented

The capability spec explicitly mentions these as future deltas (spec.md lines 47-49, 122-124, 195-200):

### 3.1 OTel push (OpenTelemetry exporter)

**Spec reference**: spec.md line 48 — "future deltas (e.g., per-finding graph_unavailable refinement, cross-project drift federation, OTel push)".

**Status**: zero code. `grep -ri "OTel\|opentelemetry\|otlp"` across `src/`: 0 matches.

**What it would require**: a `DriftSummaryOTelExporter` that consumes `DriftReport` and emits OTLP spans + metrics. Natural seam: `record_drift_summary` is the existing fan-out point.

### 3.2 Cross-project drift federation

**Spec reference**: spec.md line 392 (Cross-Impact table) — `cross-project-federation (v0.5.0) | Unrelated`. The relationship is "unrelated" because the federation exists for `mem_search_federated`, not for drift.

**What it would require**: an orchestrator that runs `scan_change` per project in a workspace, aggregates the per-project `DriftReport` results, and emits cross-project counters.

### 3.3 Per-finding `graph_unavailable` refinement

**Spec reference**: spec.md line 47 — "e.g., per-finding graph_unavailable refinement".

**Status**: `DriftReport.graph_unavailable: bool` is per-REPORT (terminal). The `unable_to_verify` enum value is per-BINDING (line 122-124 explicitly notes the conceptual tension: "the unable_to_verify state is terminal for the WHOLE report, not per-binding"). But `Finding` has no `graph_unavailable` field — only the enum value. There's no way to say "binding X failed because its specific graph entry was unreadable, but bindings Y/Z succeeded".

**What it would require**: add `graph_unavailable: bool` (per-finding) to `Finding` dataclass. The `Finding.__post_init__` already enforces `int` discipline — adding the field is small but the spec impact is large (every caller + every counter needs reconciliation).

### 3.4 Other potential extensions (not in spec)

- `DriftEventLog` async append (currently synchronous `with self._lock`).
- `flow drift watch` (continuous stream, like `flow watch --drift` but CLI-direct).
- Per-decision-id drill-down in `flow drift events stats` (currently only top-N).

---

## 4. Candidate refactor slices

The "architectural refactor" framing has many valid decompositions. Below are **3 concrete slices** sized for the 400-LOC single-PR budget (per `cli/spec.md` REQ-CLI-SPLIT-5), each independently shippable.

### Slice 1 — Extract `GraphLoader` + `ObservationSource` protocols from `scan_change` **[RECOMMENDED FIRST]**

**What**: define 2 narrow `Protocol` types — `GraphLoader` (returns `(nodes, id_map, mtime)`) and `ObservationSource` (returns `list[observation]`). Refactor `scan_change` to consume the protocols. Implement 2 concrete adapters: `LiveDiskGraphLoader` (current `load_graph` happy path) + `SnapshotGraphLoader` (current `_load_graph_from_snapshot`). Drop `_DummyBackend` — `ObservationSource` accepts `Iterable[observation]` directly.

**Why first**:
- Narrow contract — `scan_change` becomes a coordinator of 3 collaborators (graph loader, observation source, classifier).
- Creates the seam for all 3 future extensions (OTel push, federation, per-finding graph_unavailable).
- `GraphLoader` failure modes become DISTINGUISHABLE: `GraphMissing`, `GraphMalformed`, `SnapshotEnvelopeCorrupt`, `PermissionDenied` (each a distinct exception; `scan_change` maps to `unable_reason`).
- `_DummyBackend` disappears.

**Size** (rough):
- 2 protocol definitions: ~25 LOC
- 2 concrete adapters (extracted from existing code, net-zero LOC delta): ~150 LOC
- `scan_change` refactor: ~80 LOC delta (function shrinks from 250 → ~170 LOC)
- `unable_reason` population: ~30 LOC delta
- New tests: ~120 LOC (mock GraphLoader + mock ObservationSource + per-finding graph_unavailable contract tests)
- **Total**: ~400 LOC. Right at budget — justify via REQ-CLI-SPLIT-5 paragraph.

**Effort**: medium. Touches `decision_drift.py` heavily + adds 1 new test file.

**Risk**:
- **API risk**: `scan_change(..., graph_json_path=..., snap_id=..., backend=...)` signature must stay — the new protocols are internal. `LoadGraphFn` type alias is needed for downstream callers (CLI + daemon currently pass `Path` directly to `scan_change`).
- **Test risk**: 558 LOC of `test_decision_drift.py` exercises `scan_change` directly — must stay green. Add adapter-compat layer (callable adapter wraps the legacy kwargs).
- **Spec risk**: low — no behavioral REQ changes.

### Slice 2 — Unified JSONL rotation helper

**What**: extract `_rotate_jsonl_if_needed(path, *, max_bytes_env, max_age_days_env, glob_pattern, default_bytes, default_age)` shared helper. Refactor `drift_event_log.py:_rotate_if_needed` and `observability.py:_rotate_metrics_if_needed` to call it. Move both to a new `src/flow_engineering/_jsonl_rotation.py` module.

**Why second**:
- Pure deduplication — zero behavior change.
- Independently shippable (no dependency on Slice 1).
- Smallest "quick win" — fits 200-LOC budget with 50% headroom.
- Future-proofs: any new JSONL sink (e.g., `prompt_renders.jsonl` from REQ-51 already uses 3rd copy of the pattern at `prompt_render_log.py:200`) reuses the same helper.

**Size** (rough):
- New helper module: ~60 LOC
- `drift_event_log.py` refactor: -40 LOC delta
- `observability.py` refactor: -40 LOC delta
- New tests: ~80 LOC
- **Total**: ~80 LOC net. Well under budget.

**Effort**: low. Touches 2 files moderately + adds 1 new module.

**Risk**:
- **API risk**: none — internal helpers only.
- **Test risk**: rotation tests in `test_drift_event_log.py` + `test_observability.py` (REQ-V1.1.1 + REQ-V1.2.1) must stay green.
- **Spec risk**: zero — pure refactor.

### Slice 3 — Extract `DriftOrchestrator` + per-finding `graph_unavailable` refinement **[DEPENDS ON SLICE 1]**

**What**: build on Slice 1's `GraphLoader` seam. Add `Finding.graph_unavailable: bool = False` field. Update `classify_with_id_map` to set the flag when the loader returns `None` for that specific binding's id. Add `drift_graph_unavailable_per_finding_total` counter.

**Why third**:
- Implements the spec's mentioned extension (line 47).
- Requires Slice 1's `GraphLoader` distinction (per-id errors) to be meaningful.
- Real spec delta — requires new REQ (REQ-DD-1 or similar) + new BDD scenarios.

**Size** (rough):
- `Finding` dataclass change: ~5 LOC
- `classify_with_id_map` change: ~20 LOC delta
- `DriftReport` aggregation: ~15 LOC delta
- `record_drift_summary` new counter: ~5 LOC
- New BDD scenarios: ~100 LOC
- New unit tests: ~80 LOC
- Spec delta: ~50 LOC (`specs/decision-drift/specs/per-finding-graph-unavailable/spec.md`)
- **Total**: ~275 LOC. Fits budget comfortably.

**Effort**: medium-high. Touches `decision_drift.py` (data model + classifier) + `observability.py` (new counter) + spec delta.

**Risk**:
- **API risk**: `Finding` adds a field — REQ-V9.4 hard-break enforcement means new field must be defaulted (`graph_unavailable: bool = False`) to stay backwards-compatible with v1.0 JSONL.
- **Test risk**: existing `Finding(...)` constructions with positional args would break if `graph_unavailable` isn't last or defaulted. Audit all 9 test files + BDD step glue.
- **Spec risk**: medium — new REQ requires delta spec + new BDD scenarios per REQ-57 precedent.

### Out-of-scope (NOT proposed in this change)

| Candidate | Reason deferred |
|-----------|-----------------|
| OTel push exporter | External dependency (`opentelemetry-sdk`); requires separate spec + deps approval |
| Cross-project drift federation | New feature, not refactor; needs design spike |
| `decision_drift.py` file split (4 submodules) | Mechanical; mirrors v1.3-cli-split pattern but `decision_drift.py` is already 734 LOC and tightly coupled — splitting without an extraction-first (Slice 1) creates the same god-module anti-pattern in 4 places |
| `SnapshotGraphMissing` → `snapshot_manager.py` | Single-file move; not architectural; <50 LOC; bundles cleanly with Slice 1 |
| `_write_back_findings` lazy-import refactor | Slice 4 v1.3-cli-split artifact (Engram #2041); orthogonal to drift detection |

---

## 5. Recommended approach

**Recommend shipping Slice 1 (Extract `GraphLoader` + `ObservationSource`) as the first deliverable** of the `drift-detection` change.

### Why Slice 1 first

1. **Lowest blast radius for highest architectural value**. `scan_change` becomes a 170-LOC coordinator over 3 collaborators instead of a 250-LOC god-function. Future extensions (OTel, federation, per-finding graph_unavailable) all plug into the new seam without touching the classifier or the loader.
2. **Fits the 400-LOC budget with a clear REQ-CLI-SPLIT-5 justification**. "Mechanical extraction of two narrow Protocols from an over-orchestrated `scan_change`; behavior preserved; test coverage preserved; creates seam for OTel/federation/per-finding-graph_unavailable follow-ups."
3. **Reduces risk for Slice 3**. Per-finding `graph_unavailable` refinement requires distinguishable graph failure modes — Slice 1's exception hierarchy is the prerequisite. Shipping Slice 3 first would force inventing the seam under spec pressure.
4. **Matches the "isolated domain" honest read** (Engram #2038). Decision-drift is the most isolated capability in the codebase; the refactor doesn't touch `observability`, `workspace`, `prompt-registry`, `flow-where`, or any CLI scaffolding.
5. **Sets up the `DriftOrchestrator` abstraction explicitly** so Slice 3 doesn't need to invent it — Slice 3 becomes purely "add a field + a counter + BDD scenarios", not "invent the orchestrator AND add a field".

### Why not ship all 3 slices at once

- Slice 2 (rotation helper) is independent and could ship in parallel — but the user's strategic read is "drift_detection architectural refactor", singular. Combining 3 slices dilutes the review focus.
- Slice 3 (per-finding graph_unavailable) requires a spec delta — that's a different change shape (delta-spec-driven, not refactor-driven).
- 3 chained PRs (`stacked-to-main` strategy per `v1.2-followups` precedent) inflate review budget 3× and the value compounds.

### Recommended follow-up changes (NOT in this `drift-detection` change)

1. **`drift-detection-rotation`** (Slice 2 alone) — tiny debt-closure release, ~80 LOC.
2. **`drift-per-finding-graph-unavailable`** (Slice 3 alone, depends on this change shipping first) — feature release with spec delta + new BDD scenarios.

---

## 6. Risks (summary)

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `scan_change` adapter-compat layer drifts from canonical kwargs | Medium | Keep `scan_change(graph_json_path=..., snap_id=..., backend=...)` signature UNCHANGED; the adapter is internal. Add integration test asserting kwargs still work. |
| New `GraphLoader` exception types break CLI error mapping (`cli/drift.py:351`) | Low | CLI catches `SnapshotGraphMissing` specifically; new types are narrower. Add explicit catch-and-rethrow in `scan_change` adapter to preserve the existing `SnapshotGraphMissing` raise site. |
| `unable_reason` population surfaces historical silent errors | Low | The field defaults to `None`; populating it adds INFO-level noise but no breaking change. Existing tests assert `graph_unavailable=True` not `unable_reason=...`. |
| Slice 1 PR exceeds 400 LOC despite careful sizing | Medium | If actual LOC > 400, justify via REQ-CLI-SPLIT-5 paragraph (mechanical extraction, behavior preserved, public API unchanged) OR split into 2 PRs: PR1 = protocols + adapters, PR2 = `scan_change` refactor. |

---

## 7. Ready for proposal

Yes. Slice 1 is concrete, sized (fits 400-LOC budget), low-risk (no public API change, no spec delta), and creates the seam for all future drift-detection extensions.

The `proposal.md` will:
- Lock Slice 1 as the first deliverable.
- Document Slice 2 + Slice 3 as out-of-scope follow-up changes.
- Include a "Size estimate" section breaking down Slice 1 by sub-component.
- Note the strict-TDD posture (tests written first per `sdd-init/flow-engineering.md`).

---

## Relevant Files

- `src/flow_engineering/decision_drift.py` — primary refactor target (734 LOC).
- `src/flow_engineering/drift_event_log.py` — Slice 2 secondary target (255 LOC).
- `src/flow_engineering/observability.py:438-474` — `record_drift_summary` (8-counter fan-out).
- `src/flow_engineering/cli/drift.py` — CLI consumers of `scan_change`.
- `src/flow_engineering/daemon.py:36-145` — daemon consumer of `scan_change`.
- `openspec/specs/decision-drift/spec.md` — capability catalog (10 root REQs, 56 KB).
- `openspec/changes/archive/2026-06-27-drift-hardening/` — prior batch that established the capability.
- `openspec/changes/archive/2026-06-28-v0.9.0-hardening/` — v0.9.0 compat-shim removal.
- `tests/unit/test_decision_drift*.py` (4 files, 1 600 LOC) — test surface.
- `tests/unit/test_cli_drift*.py` (5 files, 1 650 LOC) — CLI test surface.
- `tests/unit/test_drift_event_log.py` (740 LOC) — JSONL rotation tests.