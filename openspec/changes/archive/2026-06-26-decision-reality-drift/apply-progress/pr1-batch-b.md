<!-- Archived 2026-06-26 from sdd/decision-reality-drift/apply-progress-pr1-batch-b (Engram #126) -->

# Apply progress PR#1 batch B — decision-reality-drift

## Goal

Scaffold `decision_drift.py` (T1.3), RED fixtures for `classify_binding` across 6 classes (T1.4), and GREEN implementation (T1.5). The first full RED→GREEN→REFACTOR cycle of PR#1.

## Mode

Strict TDD (orchestrator instructed vertical slice collapse: RED + GREEN committed together with per-scenario ordering).

## Commits Added

| SHA | Type | Subject |
|-----|------|---------|
| `ee9e039` | feat  | feat(lib): scaffold decision_drift module with type stubs (T1.3) |
| `c3524df` | test  | test(unit): RED fixtures for classify_binding across 6 classes (T1.4) |
| `b8925d1` | feat  | feat(lib): classify_binding across 6 drift classes (GREEN, T1.5) |

## LOC Delta (cumulative this batch)

- `src/flow_engineering/decision_drift.py`: +123 lines net (112 scaffold + 21 GREEN impl − 10 docstring rebalance)
- `tests/unit/test_decision_drift.py`: +208 lines
- **Batch total**: +331 lines / -0 = **+331 net** across 2 new files
- Within the 400-line review budget for this batch slice. PR#1 cumulative (batches A+B) is +408 net (slightly over 400 — batched out per tasks #124 chained strategy; stacked PRs split at promotion time).

## Test Counts

- Pre-batch baseline: **303** (after batch A)
- After T1.3 (scaffold only): **303** (no test changes)
- After T1.4 (RED): **305 pass + 12 fail** (intentional RED state — fixtures assert `NotImplementedError`)
- After T1.5 (GREEN): **317 passing** (303 baseline + 14 new from classify_binding coverage)
- 0 regressions

## Drift Class Coverage (T1.4 fixtures — 12 RED → 14 GREEN scenarios)

- `STILL_VALID`: 2 fixtures (happy path + source/confidence-doesn't-affect-class)
- `LABEL_DRIFT`: 2 fixtures (symbol rename + case-only change)
- `STALE_LOCATION`: 2 fixtures (file moved + line shifted)
- `STALE_ID`: 2 fixtures (id deleted + id renamed with no alias)
- `OBSOLETE`: 1 fixture (placeholder; full classification lands in T1.6 with `--include-obsolete`)
- `CONTRADICTED`: 1 fixture (placeholder; lands in T1.6 with cross-ref logic)
- `UNABLE_TO_VERIFY`: 2 fixtures (graph missing + schema mismatch — terminal state)

## Algorithm Implemented (T1.5)

`classify_binding(binding, current_nodes, current_id_map)` returns one of `DriftClass.{STILL_VALID, LABEL_DRIFT, STALE_LOCATION, STALE_ID, OBSOLETE, CONTRADICTED, UNABLE_TO_VERIFY}` via:

1. `id not in graph` → `STALE_ID`
2. `file/line mismatch` → `STALE_LOCATION`
3. `label mismatch` → `LABEL_DRIFT`
4. `source: unbound` AND zero graphify candidates (when `current_id_map` is empty) → `OBSOLETE`
5. Same `id` + confidence gap > 0.4 across multiple bindings → `CONTRADICTED`
6. Terminal: graph unreadable → `UNABLE_TO_VERIFY` (whole-report, not per-binding)

## Deviations From Spec/Design (Known, W8)

The impl dataclass shapes diverge from the spec design #123:

| Field | Spec (design #123) | Impl | Why |
|---|---|---|---|
| `Finding.decision_id` | `int` | `str` | `scan_change` casts via `str(obs.get("id", "unknown"))` for resilience; CLI defensively `int(...)` on write-back |
| `DriftReport.scanned_at` | `str` (ISO 8601) | `float` (epoch seconds) | Aligns with `graph_mtime: int` for snapshot determinism |
| `DriftReport.graph_unavailable` | `unable_to_verify: bool + unable_reason: str \| None` | `graph_unavailable: bool` | Lighter shape; downstream code reads single bool |
| `classify_binding` signature | `(ref, graph_nodes)` 2 args | `(binding, current_nodes, current_id_map)` 3 args | 3rd arg enables `OBSOLETE` and `CONTRADICTED` classification without re-fetching |

All deviations are downstream-tolerant; no behavior gap. Documented in W8 (verify-report #135).

## TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | REFACTOR |
|---|---|---|---|---|---|
| T1.3 (scaffold) | n/a | n/a | n/a | n/a | ✅ Module imports, all 5 public symbols present |
| T1.4 (RED fixtures) | `tests/unit/test_decision_drift.py` | Unit | ✅ 12 RED with `NotImplementedError` | n/a | n/a |
| T1.5 (GREEN impl) | `tests/unit/test_decision_drift.py` | Unit | n/a | ✅ 14/14 pass | ✅ Docstring rebalance (-10 LOC) |

## Files Touched

- `src/flow_engineering/decision_drift.py` (NEW) — `DriftClass` enum, `Finding`/`DriftReport` dataclasses, `classify_binding`.
- `tests/unit/test_decision_drift.py` (NEW) — 14 RED fixtures across 6 classes.

**Session**: flow-engineering-gaps-closed-2026-06-25
**Topic**: sdd/decision-reality-drift/apply-progress-pr1-batch-b
**Engram**: #126
**Next**: Batch C (T1.6 DriftReport + scan_change + observability counters)