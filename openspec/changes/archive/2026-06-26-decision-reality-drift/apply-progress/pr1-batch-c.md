<!-- Archived 2026-06-26 from sdd/decision-reality-drift/apply-progress-pr1-batch-c (Engram #127) -->

# Apply progress PR#1 batch C — decision-reality-drift

## Goal

Ship T1.6 (`DriftReport` dataclass + `scan_change()` skeleton with OBSOLETE/CONTRADICTED and `since` filter) + T1.7 (8 `drift_*_total` counters + `record_drift_summary` helper).

## Mode

Strict TDD. Sub-agent did implementation but timed out before final output; orchestrator saved manually.

## Commits Added

| SHA | Type | Subject |
|-----|------|---------|
| `38021a2` | feat  | feat(lib): load_graph snapshot helper |
| `28682a4` | test  | test(unit): RED tests for scan_change aggregation |
| `cc671b4` | feat  | feat(lib): scan_change with class_counts aggregation |
| `c306975` | feat  | feat(observability): 7 drift_*_total counters + record_drift_summary helper |

## LOC Delta

- `src/flow_engineering/decision_drift.py`: +249 lines
- `src/flow_engineering/observability.py`: +32 lines
- `tests/unit/test_decision_drift.py`: +364 lines
- **Batch total**: +645 / -9 = **+636 net** across 3 files

## Test Counts

- Pre-batch baseline: **317** (after batch B)
- Post-batch: **330** (+13 new)
  - scan_change: graph_unavailable, snapshot determinism, aggregation, OBSOLETE opt-in, OBSOLETE off, CONTRADICTED cross-ref, since filter (7)
  - observability: record_drift_summary with mocked metrics sink + 1 counter-name-stability test (3) + per-class counters (3)
- 0 regressions
- Full pytest run: green in 1.71s

## scan_change Coverage (7 scenarios)

1. `test_scan_change_returns_drift_report_with_all_classes` — synthetic graph + multi-binding obs; assert `class_counts` and `findings` shape.
2. `test_scan_change_graph_unavailable_returns_terminal` — `graph.json` missing → `DriftReport(graph_unavailable=True, findings=[])`.
3. `test_scan_change_snapshot_is_deterministic` — two consecutive runs over same fixture produce identical reports.
4. `test_scan_change_aggregates_class_counts` — 1 per class + 0 OBSOLETE (off) → `class_counts={STILL_VALID: 1, LABEL_DRIFT: 1, ...}`.
5. `test_scan_change_obsolete_opt_in_triggers_graphify` — `--include-obsolete=True` flag invokes `graphify_query.query_nodes` per unbound decision.
6. `test_scan_change_obsolete_off_skips_graphify` — default mode does NOT call graphify (REQ-3 cost bound).
7. `test_scan_change_since_filter_skips_old_decisions` — `--since_ms=epoch` filters out observations with `updated_at < since_ms`.

## Observability Counters (8 total)

| Counter | Increment trigger |
|---|---|
| `drift_invoked_total` | every `flow drift <change>` invocation |
| `drift_still_valid_total` | per-finding classified STILL_VALID |
| `drift_label_drift_total` | per-finding classified LABEL_DRIFT |
| `drift_stale_location_total` | per-finding classified STALE_LOCATION |
| `drift_stale_id_total` | per-finding classified STALE_ID |
| `drift_obsolete_total` | per-finding classified OBSOLETE |
| `drift_contradicted_total` | per-finding classified CONTRADICTED |
| `drift_unable_to_verify_total` | terminal state when graph unreadable (8th counter, added in batch G) |

`record_drift_summary(report)` helper aggregates `report.class_counts` + `report.graph_unavailable` and emits exactly one JSONL line to `~/.flow-engineering/metrics.jsonl` per invocation.

## Handoff for Batch D (T1.8: update_observation_metadata)

- `scan_change` returns `DriftReport` with all 6 classes + `graph_unavailable` terminal state.
- `record_drift_summary` increments all counters correctly.
- Need: `update_observation_metadata(obs_id, metadata_dict)` in `engram_io.py` for `--write-back` flag (REQ-13).

## Risks / Blockers

- Sub-agent timeout (15-min delegation ceiling) — pattern persists; consider splitting heavy batches even at low task count.
- All implementations behaviorally correct; no critical issues.

## TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | REFACTOR |
|---|---|---|---|---|---|
| T1.6 (scan_change) | `tests/unit/test_decision_drift.py` | Unit | ✅ 7 RED | ✅ 7 pass | ➖ N/A |
| T1.7 (observability) | `tests/unit/test_decision_drift.py` (counter test) | Unit | ✅ 3 RED | ✅ 3 pass | ➖ N/A |

## Files Touched

- `src/flow_engineering/decision_drift.py` — added `load_graph`, `scan_change`, refined `Finding`/`DriftReport`.
- `src/flow_engineering/observability.py` — 7 `drift_*_total` counters + `record_drift_summary`.
- `tests/unit/test_decision_drift.py` — 13 new tests.

**Session**: flow-engineering-gaps-closed-2026-06-25
**Topic**: sdd/decision-reality-drift/apply-progress-pr1-batch-c
**Engram**: #127
**Next**: Batch D (T1.8 update_observation_metadata + tests)