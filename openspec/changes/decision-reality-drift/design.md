# Design: decision-reality-drift

## Technical Approach

Pure-library `decision_drift.py` + thin `flow drift <change>` CLI mirror the `binding.py` ↔ `cli.py` separation from `decision-code-linking`. Resolver is I/O-free: takes a parsed `graph.json` dict + observation list + options → `DecisionDriftReport`. CLI owns all I/O. Six drift classes classify every binding; `unable_to_verify` is a terminal state, not a class. Two chained PRs: PR#1 ships the library + CLI + counters + W2/W3 reconciliation; PR#2 wires `flow watch --drift` and `sdd-verify` Step 6.

## Architecture Decisions

| # | Decision | Option | Tradeoff | Choice |
|---|---|---|---|---|
| 1 | Snapshot strategy | Read `graph.json` once at scan start vs per-binding | Deterministic vs mid-run inconsistency | **Snapshot once**: build `dict[id, node]` upfront; report includes `graph_mtime` for audit |
| 2 | Contradicted algorithm | Same `id` + conflict vs same `file:line` + conflict vs confidence-gap threshold | Heuristic must be cheap + low FP | **Same `id` + `confidence_gap > 0.4`**: `manual≥0.9` vs `auto_suggest<0.5` flags contradicted. Two refs at same `id` with similar confidence → still_valid. WARNING severity |
| 3 | Obsolete cost bound | Per-unbound-decision `graphify query` vs batched | $0.001/call, ~2-5s each | **Opt-in via `--include-obsolete`**; default OFF. When enabled: per decision, fail-open (missing graphify → skip, not error). Future v2 batches |
| 4 | Metadata write-back | Per-obs API call vs batched update vs in-place mutation | Atomicity vs Engram round-trips | **Per-obs via `update_observation`**: append `<!-- metadata -->` block (NEW marker) with `{last_verified_at, last_drift_class}`. Single call, no schema bump. Opt-in `--write-back` |
| 5 | Existing observation migration | Backfill `last_verified_at` on all 46+ obs vs lazy-on-first-verify | Backfill triggers drift run; lazy is cheap | **Lazy**: `--write-back` writes on first scan; legacy obs return `last_verified: never` until verified |
| 6 | Watch integration trigger | Re-scan on every file change vs on observation save vs on `state.json` event | File churn is noisy; save is rarer | **Re-scan on `state.json` transition to APPLIED + on `task_id` `merged` in apply-progress** via `flow watch --drift`. Sub-mode of existing daemon, NOT a new long-running process |
| 7 | Counter wiring | 7 counters (`*_total` per class) vs 1 counter + enum field | Per-class lets `flow metrics` summarize cleanly | **7 `drift_*_total` counters + `record_drift_summary(report)` helper** (parallels `record_backfill_coverage`) |
| 8 | Schema validation | Pin `graph.json` schema version vs accept any dict | Schema mismatch = corrupt lookup | **Pin to current build (5043 nodes); mismatch → `unable_to_verify` exit 2** |
| 9 | Exit codes | 0=clean / 1=any drift / 2=unable_to_verify vs single fail-fast | CI must distinguish "drift found" from "couldn't check" | **3-state: 0/1/2** |
| 10 | Multi-project refs | Skip + warn vs hard-error | v1 simplicity; future federation owns proper handling | **Skip with `WARNING` per ref logged to stderr** |

## Module Breakdown (file-level diff plan)

### PR#1 — Core drift detector + CLI + reconciliation (target ≤480 LOC)

| File | Action | LOC | Purpose |
|---|---|---|---|
| `src/flow_engineering/decision_drift.py` | CREATE | ~140 | `DriftClass` enum, `Finding`/`DriftReport` dataclasses, `classify_binding`, `scan_change`, `record_drift_summary` helper |
| `src/flow_engineering/cli.py` | MODIFY | +90 | `flow drift <change>` subcommand: table + `--json` renderer; exit 0/1/2 logic |
| `src/flow_engineering/observability.py` | MODIFY | +35 | 7 `drift_*_total` counters + `record_drift_summary(report)` |
| `src/flow_engineering/engram_io.py` | MODIFY | +20 | `update_observation_metadata(obs_id, metadata_dict)` — appends `<!-- metadata -->` block (NEW marker, gated, never mutates `code_refs`) |
| `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md` | MODIFY | ~30 | W2 REQ-8 rewrite: counter list + 3 scenario rewording (lines 271/273/279/285) |
| `tests/bdd/req3_engram_io.feature` | MODIFY | +5 | W3 scenario: "Save with valid empty block writes as `source: unbound`" |
| `tests/bdd/test_decision_code_linking_p1_steps.py` | MODIFY | +6 | W3 step def |
| `tests/unit/test_decision_drift.py` | CREATE | ~180 | Per-class fixtures (≥3 per class), `unable_to_verify`, multi-binding interactions |
| `tests/unit/test_cli_drift.py` | CREATE | ~80 | `flow drift` exit codes, `--json`, `--include-obsolete`, `--write-back`, `--since` |
| `tests/unit/test_engram_io_metadata.py` | CREATE | ~50 | `update_observation_metadata` append/replace/preserve-`code_refs` invariants |
| `tests/bdd/req9_drift.feature` | CREATE | ~40 | 6 scenarios — one per drift class + `--json` round-trip + `unable_to_verify` |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | MODIFY | +25 prose | "Drift detection hook" prose extension to existing binding hook |

**Total**: 4 new files, 5 modified code files, 6 modified SKILL.md files, 1 modified archived spec.md. **~700 LOC**.

### PR#2 — Watch integration + verify wiring (target ≤200 LOC)

| File | Action | LOC | Purpose |
|---|---|---|---|
| `src/flow_engineering/daemon.py` | MODIFY | +60 | `start_watch(change, target, drift=False)`; when `drift=True`, also subscribes to `apply-progress.json` writes; on event → call `decision_drift.scan_change()` + record metrics |
| `src/flow_engineering/cli.py` | MODIFY | +30 | `--drift` flag on `flow watch`; prints re-scan summary inline |
| `~/.config/opencode/skills/sdd-verify/SKILL.md` | MODIFY | +25 | New Step 6 sub-step: "Run `flow drift <change>` and surface findings" |
| `CHANGELOG.md` | MODIFY | +10 | v0.3.0 entry |
| `tests/unit/test_cli_watch_drift.py` | CREATE | ~60 | `--drift` flag wires; `apply-progress` event triggers re-scan; non-drift path unchanged |
| `tests/unit/test_daemon_drift_events.py` | CREATE | ~40 | Event handler unit tests with mock daemon |

**Total**: 2 new test files, 4 modified files. **~225 LOC**.

## Data Flow

### `flow drift <change>` (PR#1)

```
flow drift decision-reality-drift [--json] [--include-obsolete] [--since 2026-06-01]
    │
    ├─→ observability.increment("drift_invoked_total", change=...)
    ├─→ graph_path = env FLOW_GRAPH_JSON or default
    ├─→ if graph_path missing/unparseable:
    │     ├─→ emit DriftReport(unable_to_verify=True)
    │     ├─→ observability.increment("drift_unable_to_verify_total")
    │     └─→ sys.exit(2)
    │
    ├─→ graph_nodes = json.loads(graph_path); mtime = graph_path.stat().st_mtime
    │     # O(N) build of dict[id, node] for O(1) lookups
    │
    ├─→ observations = iter_observations_for_change(change, backend)
    │
    ├─→ for each observation:
    │     ├─→ refs = extract_code_refs(obs.content)   # bound via binding.py
    │     ├─→ if empty/all-unbound: silently skip (per Q8 decision)
    │     ├─→ for each ref:
    │     │     ├─→ classify_binding(ref, graph_nodes)
    │     │     │     ├─→ id not in graph    → STALE_ID
    │     │     │     ├─→ file/line mismatch → STALE_LOCATION
    │     │     │     ├─→ label mismatch     → LABEL_DRIFT
    │     │     │     └─→ match              → STILL_VALID
    │     │     └─→ finding = Finding(decision_id, ref, class, detail)
    │     │
    │     ├─→ contradicted pass (cross-ref):
    │     │     └─→ for each pair (r1, r2) in refs: same id + gap>0.4 → CONTRADICTED
    │     │
    │     └─→ if --include-obsolete AND all refs unbound:
    │           └─→ graphify_query.query_nodes(prose[:500]) → 0 above threshold → OBSOLETE
    │
    ├─→ aggregations: class_counts, bindings_total, decisions_total
    │
    ├─→ record_drift_summary(report)  # 7 counter increments
    │
    ├─→ if --write-back:
    │     └─→ for each finding: update_observation_metadata(obs_id, {last_verified_at, last_drift_class})
    │
    └─→ render table | json
          ├─→ all STILL_VALID   → sys.exit(0)
          ├─→ any non-still-valid → sys.exit(1)
          └─→ unable_to_verify  → sys.exit(2)
```

### `flow watch --drift` (PR#2)

```
flow watch decision-reality-drift --drift
    │
    ├─→ existing daemon: subscribe to flow-engineering/<change>/ (file events)
    │     # NEW: also subscribe to apply-progress.json writes
    │
    └─→ on_event(apply_progress_updated or task_merged):
          ├─→ decision_drift.scan_change(change, graph_path, since=last_scan_ts)
          ├─→ if any drift class > 0:
          │     └─→ observability.increment("drift_invoked_total", trigger=watch)
          │     └─→ click.echo(summary line)
          └─→ update last_scan_ts
```

## Interfaces / Contracts

```python
# decision_drift.py
class DriftClass(str, Enum):
    STILL_VALID = "STILL_VALID"
    LABEL_DRIFT = "LABEL_DRIFT"
    STALE_LOCATION = "STALE_LOCATION"
    STALE_ID = "STALE_ID"
    OBSOLETE = "OBSOLETE"
    CONTRADICTED = "CONTRADICTED"

@dataclass(frozen=True)
class Finding:
    decision_id: int
    binding: CodeRef
    drift_class: DriftClass
    detail: str

@dataclass
class DriftReport:
    change_name: str
    scanned_at: str  # ISO 8601
    graph_mtime: int  # epoch seconds; 0 if unable_to_verify
    decisions_total: int
    bindings_total: int
    class_counts: dict[DriftClass, int]
    findings: list[Finding]
    unable_to_verify: bool = False
    unable_reason: str | None = None

def classify_binding(ref: CodeRef, graph_nodes: dict[str, dict]) -> DriftClass: ...
def scan_change(change_name: str, graph_json_path: Path, *,
                include_obsolete: bool = False, since_ms: int | None = None) -> DriftReport: ...

# observability.py (additions)
def record_drift_summary(report: DriftReport) -> None:
    """Increment 7 counters from class_counts + 1 unable_to_verify + 1 invoked."""

# engram_io.py (additions)
def update_observation_metadata(obs_id: int, metadata: dict[str, Any]) -> dict:
    """Append/replace `<!-- metadata -->` block (different from `code_refs`).
    Preserves existing `code_refs` block byte-for-byte. Single API call."""
```

JSON shape for metadata block (NEW marker, distinct from `code_refs`):

```
<!-- metadata -->
{"schema": 1, "fields": {"last_verified_at": "2026-06-25T22:30:00Z", "last_drift_class": "STILL_VALID"}}
```

## Cross-Cutting Concerns (resolved)

| Concern | Resolution |
|---|---|
| Snapshot determinism | Single `json.loads` + mtime capture at scan start; `dict[id, node]` built once. Report carries `graph_mtime` so audit can correlate |
| Contradicted noise | Same `id` (NOT same `file:line`) + `|confidence_a - confidence_b| > 0.4`. Examples: `manual=0.9` vs `auto_suggest=0.31` → flag. `manual=0.9` vs `manual=0.85` → still_valid |
| Obsolete cost | `--include-obsolete` defaults OFF. When ON: per-decision `graphify_query.query_nodes(prose[:500])` with existing 5s timeout + cache. Bounded by change size. `unable_to_verify` if graphify missing |
| Metadata atomicity | Single `update_observation` call per finding → round-trip is atomic enough for v1. Future: batched mode in `decision-resolve` change |
| Existing obs migration | Lazy: `--write-back` writes per observation on first scan. `flow inspect` unchanged (still reads `updated_at`). `last_verified_at` is opt-in |
| Watcher events | Re-scan on `apply-progress.json` task `merged` status (existing event). NOT on every `state.json` write (noisy). Output streams to stdout; non-blocking (background thread in daemon) |
| W2 prerequisite | Landed as FIRST commit in PR#1. Drift detector's read-side contract against impl counter names is stable before any drift code |
| W3 prerequisite | Landed in same PR#1 (4-line Gherkin + 6-line step def). Unit test for empty-block already passes — BDD makes verify-report green |
| Cross-project refs | Detected when `ref.project != current_project` → log WARN to stderr, exclude from `findings`. `--project <name>` overrides default project |
| `source: unbound` boundary | Detector silently skips (no binding = nothing to verify). `flow inspect` surfaces "no bindings"; `flow drift` surfaces "drift" |
| Graph schema evolution | Pin to current schema (5043 nodes, deterministic IDs). Schema mismatch → `unable_to_verify` exit 2. Future: `graph-snapshots` owns schema evolution |
| Performance | O(N+M) where N=obs×bindings, M=graph nodes. 200 obs × 5 bindings = 1000 lookups against 5043-node dict = ~6K ops. Sub-second |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `classify_binding` per class | Table-driven; ≥3 fixtures per class (valid/stale_id/stale_location/label_drift/obsolete/contradicted) |
| Unit | `scan_change` aggregation | Synthetic graph dict + seeded observations; assert `class_counts`, `findings`, `unable_to_verify` |
| Unit | `record_drift_summary` counters | Mock metrics sink; assert 7 counter names + payload shape |
| Unit | `update_observation_metadata` | Seed obs with `code_refs`; write metadata; assert both blocks present, `code_refs` byte-identical |
| Unit | `flow drift` CLI | Click `CliRunner`; seeded backend; assert exit 0/1/2 per fixture + `--json` parse + `--include-obsolete` flag wires |
| Unit | `flow watch --drift` (PR#2) | Mock daemon event; assert scan triggered + stdout summary |
| BDD | `req9_drift.feature` | 8 scenarios: still_valid, label_drift, stale_location, stale_id, obsolete (with `--include-obsolete`), contradicted, unable_to_verify, `--json` round-trip |
| BDD | W3 `req3_engram_io.feature` | "Save with valid empty block writes as `source: unbound`" (4 lines) |
| Integration (manual) | Real `graph.json` against seeded change | Eyeball table; verify exit codes match expected |

**TDD order per file** (Strict TDD ON):
1. `decision_drift.py` — red fixtures (synthetic graph) → green → refactor dataclass + scan loop
2. `observability.py` counters + helper — red → green → refactor
3. `engram_io.py` `update_observation_metadata` — red → green → refactor
4. `cli.py` `flow drift` — red (CliRunner) → green → refactor exit-code logic
5. BDD scenarios bind unit tests
6. W2 spec.md edit (counter contract stable before drift code reads it)
7. W3 BDD scenario + step def
8. PR#2: daemon → CLI `--drift` flag → sdd-verify SKILL.md
9. SKILL.md updates land last (prose only)

Coverage target: ≥90% lines on `decision_drift.py` and CLI additions.

## Migration / Rollout

**No data migration.** `last_verified_at` is opt-in via `--write-back`. Existing 46+ observations render unchanged in `flow inspect`; `flow drift` surfaces drift silently until first `--write-back` run. Rollout order:
1. PR#1 merged → `flow drift <change>` available; W2/W3 closed in same PR
2. Operator runs `flow drift decision-reality-drift --json` once to verify (sanity)
3. PR#2 merged → `flow watch --drift` available for live re-scans; `sdd-verify` Step 6 active

Rollback per-PR per proposal (revert merge; additive changes only).

## Open Questions (resolved at design level)

| # | Question | Decision |
|---|---|---|
| 1 | Snapshot strategy | **Snapshot once** (Decision #1) |
| 2 | Re-suggestion on `stale_id` | **Out of scope** — surface only; user re-saves via auto-suggest or manual edit. Future `decision-resolve` change |
| 3 | Contradicted algorithm specifics | **Same `id` + confidence gap > 0.4** (Decision #2) |
| 4 | `--since <ts>` filter | **v1 ships**: skips observations with `updated_at < since_ms`. Cheap filter; no I/O savings (still walks all obs) but reduces `findings` size for noisy changes |
| 5 | Snapshot-pinned drift path | **Detector takes `graph_json_path` parameter**. v1 passes `default_graph_json()`. Future `graph-snapshots` change passes snapshot path. Seam in place |

## Unblocks / Constraints

**Unblocks**: closes the decision↔code "write-but-never-verify" loop. Future `decision-resolve` (auto-fix stale bindings) becomes possible.

**Constrains**: any change touching `binding.CodeRef` shape, `observability` counter names, or `graph.json` schema breaks the detector's input contract. Documented in this design.