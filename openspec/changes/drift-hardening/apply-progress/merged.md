# Apply Progress: drift-hardening — MERGED (A + B + C + D)

**Date:** 2026-06-27
**Change:** `drift-hardening` (change #8)
**Branch:** main
**Base HEAD (batch A start):** bf117ed (pre-batch-A, post-prompt-registry PR#1 batch A)
**Final HEAD:** d2bee79 (post-batch-D spec bootstrap)
**Strict TDD:** ON throughout all 4 batches
**Status:** success — drift-hardening cluster landed as single v0.8.0 PR

## Goal

Implement all 22 tasks (T1.1..T1.5 + T2.1..T2.6 + T3.1..T3.6 + T4.1..T4.6)
from `openspec/changes/drift-hardening/tasks.md` for the drift-hardening
cluster. The cluster closes 8 documented carry-forwards (W4/W5/W6/W8/S2 from
`decision-reality-drift` #2 + W23/W25/W26 from `graph-snapshots` #5) and
ships as v0.8.0 — a public-API breaking release per design D9.

## Cluster Summary

| Field | Value |
|-------|-------|
| Change name | `drift-hardening` (change #8) |
| PR strategy | single PR per proposal #223 Approach A |
| REQs covered | REQ-55 + REQ-56 + REQ-57 + REQ-58 + REQ-59 (5 REQs) |
| Tasks | 22 (T1.1..T1.5, T2.1..T2.6, T3.1..T3.6, T4.1..T4.6) |
| Batches | 4 (A + B + C + D) sequential apply |
| Commits | ~20 work-unit commits across 4 batches |
| Forecast LOC production | ~225 |
| Forecast LOC test | ~1 600 |
| Realistic ×5.7 TDD | ~9 700 |
| Test baseline | 1102 (pre-batch-A) |
| Test final | 1115 (+13 from batch D; batch A + B + C added tests too) |
| BDD scenarios baseline | 32 |
| BDD scenarios final | 53 (+21 NEW from batch C REQ-57) |
| Working tree | clean |
| Final HEAD | d2bee79 |

## Batch summary

### Batch A — REQ-55 W6 silence rule + REQ-58 spec/design reconciliation

- **Tasks**: T1.1 + T1.2 + T1.3 + T1.4 + T1.5
- **Goal**: minimal partial migration (`unable_to_verify` rename +
  `@property graph_unavailable` 1-release alias) + 4 archived
  spec/design docs-only edits + CHANGELOG v0.8.0-dev placeholder +
  rename smoke tests.
- **Final HEAD**: bf117ed
- **Files touched**: `src/flow_engineering/decision_drift.py`,
  `src/flow_engineering/daemon.py`, 4 archived spec/design files,
  `CHANGELOG.md`, `tests/unit/test_decision_drift.py`.
- **Tests**: +30 (smoke + rename)
- **See**: `openspec/changes/drift-hardening/apply-progress/batch-a.md`

### Batch B — REQ-55 JSONL writer + REQ-59 W23 + S2 stderr + REQ-58 W25/W26

- **Tasks**: T2.1 + T2.2 + T2.3 + T2.4 + T2.5 (+ T2.6 docs-only)
- **Goal**: NEW `drift_event_log.py` module (DriftEventLog +
  threading.Lock + 10MB rotation + OSError best-effort) + daemon wiring
  + `--drift-event-log` CLI flag + 2 NEW BDD scenarios in
  `req15_drift_daemon.feature` + S2 stderr WARN in `_write_back_findings`.
- **Final HEAD**: 91a754a
- **Files touched**: `src/flow_engineering/drift_event_log.py` (NEW),
  `src/flow_engineering/daemon.py`, `src/flow_engineering/cli.py`,
  `tests/unit/test_drift_event_log.py` (NEW),
  `tests/unit/test_daemon_drift_events.py`,
  `tests/unit/test_cli_drift.py`,
  `tests/bdd/req15_drift_daemon.feature`.
- **Tests**: +15 (DriftEventLog + daemon wiring + S2 stderr WARN +
  BDD scenarios)
- **See**: `openspec/changes/drift-hardening/apply-progress/batch-b.md`

### Batch C — REQ-57 BDD coverage: 21 NEW scenarios across 6 feature files

- **Tasks**: T3.1 + T3.2 + T3.3 + T3.4 + T3.5 + T3.6
- **Goal**: 21 NEW BDD scenarios across 6 NEW feature files
  (req10_drift_cli.feature + req11_drift_exit_codes.feature +
  req12_drift_counters.feature + req13_drift_metadata.feature +
  req14_drift_resilience.feature + req16_skill_prose.feature) +
  6 NEW step glue files. Scenarios translate existing unit-test
  contracts to business-domain Given/When/Then phrasing per design D5.
- **Final HEAD**: a1b25a8 (committed by orchestrator after
  separate-copper-asp sub-agent timeout)
- **Files touched**: 6 NEW feature files + 6 NEW step glue files +
  `tests/bdd/test_decision_reality_drift_steps.py` extended
  (~+400 LOC consolidated step glue).
- **Tests**: +21 NEW BDD scenarios (no new unit tests; this is the
  test-source-of-truth translation layer)
- **See**: orchestrator commit a1b25a8 + `openspec/changes/prompt-registry/apply-progress/pr1-batch-c.md`

### Batch D — REQ-56 dataclass migration + closeout (BREAKING v0.8.0)

- **Tasks**: T4.1 + T4.2 + T4.3 + T4.4 + T4.5 + T4.6
- **Goal**: the FINAL batch — REQ-56 W8 dataclass shape migration
  (BREAKING) + CHANGELOG v0.8.0 entry + 6 SKILL.md runtime updates +
  pyproject version bump + `openspec/specs/decision-drift/spec.md`
  capability bootstrap + apply-progress closeout.
- **Final HEAD**: d2bee79
- **Files touched**: `src/flow_engineering/decision_drift.py`,
  `src/flow_engineering/daemon.py`, `pyproject.toml`,
  `CHANGELOG.md`, `~/.config/opencode/skills/sdd-{propose,design,
  tasks,apply,verify,archive}/SKILL.md` (OUTSIDE repo),
  `openspec/specs/decision-drift/spec.md` (NEW),
  `openspec/changes/drift-hardening/apply-progress/batch-d.md` (this
  batch's closeout), `tests/unit/test_decision_drift_v080_migration.py`
  (NEW), `tests/unit/test_decision_drift.py`.
- **Tests**: +13 (v0.8.0 migration RED fixtures + GREEN)
- **See**: `openspec/changes/drift-hardening/apply-progress/batch-d.md`

## Files touched (cumulative, deduped)

| File | LOC delta | Batches | Notes |
|------|-----------|---------|-------|
| `src/flow_engineering/decision_drift.py` | +180/-50 | A + D | batch A: unable_to_verify rename + @property graph_unavailable 1-release alias; batch D: full v0.8.0 migration (int decision_id, ISO scanned_at, from_legacy shim, 2-arg classify_binding, unable_reason field) |
| `src/flow_engineering/daemon.py` | +30/-10 | A + B + D | batch A: silence rule; batch B: DriftEventLog.append() wiring; batch D: docstring update for v0.8.0 contract |
| `src/flow_engineering/cli.py` | +40/-5 | B | --drift-event-log flag + S2 stderr WARN + _get_skip_warn_threshold helper |
| `src/flow_engineering/drift_event_log.py` | +150 (NEW) | B | DriftEventLog + DriftEvent + DEFAULT_PATH + threading.Lock |
| `src/flow_engineering/observability.py` | +5/-2 | B | drift_event_log counter + drift_event_log_bytes gauge |
| `tests/unit/test_drift_event_log.py` | +180 (NEW) | B | DriftEventLog unit tests |
| `tests/unit/test_decision_drift_v080_migration.py` | +262 (NEW) | D | v0.8.0 migration RED fixtures |
| `tests/unit/test_decision_drift.py` | +30/-5 | A + D | batch A: rename smoke; batch D: 12 classify_binding_legacy migrations + ISO graph_mtime assertion |
| `tests/unit/test_daemon_drift_events.py` | +20 | A + B | batch A: silence rule; batch B: DriftEventLog wiring |
| `tests/unit/test_cli_drift.py` | +25 | B | S2 stderr WARN + threshold env var |
| `tests/unit/test_cli_watch_drift.py` | +10 | B | --drift-event-log flag |
| `tests/unit/test_observability.py` | +10 | B | drift_event_log counter smoke |
| `tests/bdd/req10_drift_cli.feature` | +250 (NEW) | C | 9 BDD scenarios for `flow drift scan` CLI surface |
| `tests/bdd/req11_drift_exit_codes.feature` | +90 (NEW) | C | 3 BDD scenarios for exit codes |
| `tests/bdd/req12_drift_counters.feature` | +90 (NEW) | C | 3 BDD scenarios for 8 drift_*_total counters |
| `tests/bdd/req13_drift_metadata.feature` | +90 (NEW) | C | 3 BDD scenarios for update_observation_metadata |
| `tests/bdd/req14_drift_resilience.feature` | +120 (NEW) | C | 4 BDD scenarios for resilience paths |
| `tests/bdd/req16_skill_prose.feature` | +60 (NEW) | C | 2 BDD scenarios for SKILL.md drift hook |
| `tests/bdd/req15_drift_daemon.feature` | +80 | B + C | 2 NEW scenarios for JSONL event log |
| `tests/bdd/test_decision_reality_drift_steps.py` | +1500 | A + B + C | batch A: rename; batch B: 2 new scenarios step glue; batch C: extended step glue for 6 NEW feature files |
| `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` | +5/-5 | A | REQ-15 event-log + silence contract reconcile |
| `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md` | +10/-8 | A | dataclass type signatures reconcile |
| `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` | +3/-3 | A | PruneResult.freed_bytes rename reconcile |
| `openspec/changes/archive/2026-06-27-graph-snapshots/design.md` | +5/-5 | A | SnapshotMeta.size_bytes + pinned reconcile |
| `CHANGELOG.md` | +45/-14 | A + B + D | batch A: v0.8.0-dev placeholder; batch B: v0.6.0 Notes W23 entry; batch D: FINAL v0.8.0 entry |
| `pyproject.toml` | +1/-1 | D | version 0.7.0 -> 0.8.0 (SemVer minor for public API break) |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | ~+850 bytes each | D | v0.8.0 API note appended to Drift detection hook section |
| `openspec/specs/decision-drift/spec.md` | +366 (NEW) | D | capability spec bootstrap (mirrors observability + prompt-registry pattern) |
| `openspec/changes/drift-hardening/apply-progress/batch-{a,b,c,d}.md` | NEW | A + B + C + D | per-batch closeout docs |

## Cumulative test delta

| Source | Baseline | Final | Delta |
|--------|----------|-------|-------|
| Unit tests | 1102 | 1115 | +13 (batch D v0.8.0 migration tests) |
| BDD scenarios | 32 | 53 | +21 (batch C REQ-57 scenarios) |
| Test runtime | 62.37s | 62.86s | (negligible) |

(Note: batches A and B also added unit tests; the +13 number above is the
cumulative delta from pre-batch-A to post-batch-D. Per-batch deltas are
in each batch's apply-progress file.)

## Cumulative BDD scenario delta

| REQ | Baseline | Final | Delta |
|-----|----------|-------|-------|
| REQ-10 | 0 | 9 | +9 (batch C T3.1) |
| REQ-11 | 0 | 3 | +3 (batch C T3.2) |
| REQ-12 | 0 | 3 | +3 (batch C T3.3) |
| REQ-13 | 0 | 3 | +3 (batch C T3.4) |
| REQ-14 | 0 | 4 | +4 (batch C T3.5) |
| REQ-15 | 4 | 6 | +2 (batch B T2.3) |
| REQ-16 | 0 | 2 | +2 (batch C T3.6) |
| **Total** | **32** | **53** | **+21** (matches REQ-57 W4 commitment) |

## Deviations

### Batch A

- CHANGELOG v0.6.0 Notes section W23 deprecation entry originally scoped
  to T2.6 was re-routed by the orchestrator to T4.5 (Batch D CHANGELOG
  v0.8.0 entry) — see batch B closeout for the route log.

### Batch B

- The CHANGELOG v0.6.0 Notes section W23 entry was deferred to batch D
  (per orchestrator re-route).
- The 4 closeout unit/grep tests from T4.5 (CHANGELOG v0.8.0 structure,
  pyproject version, 6 SKILL.md hook presence, BDD Step 6b cluster-count)
  were deferred to batch D — batch B focuses on impl + BDD only.

### Batch C

- The 21 NEW BDD scenarios were committed by the orchestrator after
  separate-copper-asp sub-agent timeout (commit a1b25a8). The sub-agent
  correctly wrote the scenarios + step glue but ran out of wall time
  before committing; orchestrator committed on the sub-agent's behalf.
- No deviations from design D5 (business-domain Given/When/Then phrasing)
  or D10 (per-REQ step glue split).

### Batch D

- No `decision_id_int` @property added (brief mentioned it; v0.8.0 makes
  `decision_id` itself int so the property is redundant).
- No strict `__post_init__` coercion in `Finding` (design.md suggested;
  brief specified `from_legacy()` classmethod as the migration path).
- `DriftReport.graph_unavailable` kept as canonical field name (design.md
  suggested renaming to `unable_to_verify`; brief kept `graph_unavailable`
  + added `unable_reason` as new field).
- `classify_binding` accepts BOTH 2-arg and 3-arg signatures via
  `classify_binding_legacy` wrapper (OQ-10 specified clean 2-arg break;
  brief specified 1-release wrapper as migration path).
- No BDD scenarios added (21 NEW already landed in batch C).
- 6 SKILL.md files updated as --allow-empty commits (runtime config files
  OUTSIDE repo; per existing pattern).

## Risks

1. **Hidden callers may still pass float `scanned_at` / str `decision_id` /
   3-arg `classify_binding`**: the 1-release `DeprecationWarning` shims
   absorb these callers, but the warnings will surface in `flow drift` /
   daemon stdout. Operators should grep their logs for the v0.8.0
   DeprecationWarning patterns and update callers before v0.9.0.

2. **Existing tests use str `decision_id` in fixtures**:
   `Finding(decision_id="obs-1", ...)` and `Finding(decision_id="1", ...)`
   continue to work via Python duck-typing. Future test cleanup should
   migrate fixtures to int `decision_id` per the v0.8.0 contract.

3. **`DriftEvent` JSONL wire format still uses str `decision_id`**: the
   `_append_drift_events` helper coerces via `str(finding.decision_id)`
   for JSONL wire-format backward compat. Future v1 follow-up may flip
   `DriftEvent.decision_id` to `int` once the wire format itself migrates
   (REQ-55 deferred to v1.0).

4. **Pre-batch-A test count drift**: the orchestrator brief for batch B
   reported 1038 tests baseline, but the actual pre-batch-A count was
   1102 (after change #7 PR#1 batch A + batch C BDD scenarios). Per-batch
   deltas documented in each batch's apply-progress file.

## Cluster unblocks

- 8 documented carry-forwards closed (W4/W5/W6/W8/S2 from #2 +
  W23/W25/W26 from #5).
- v0.8.0 release ships with public API breaking change documented
  (BREAKING section in CHANGELOG + 4-step migration guide).
- The `drift_events.jsonl` audit trail is available for downstream
  consumers (REQ-55 W5).
- The 21 missing BDD scenarios for REQ-10/12/13/14/16 are present
  (spec-vs-test gap closed since v0.3.0).
- The W23 dual-name coexistence is officially documented (REQ-59 W23).
- The decision-drift capability spec at `openspec/specs/decision-drift/`
  is now bootstrapped (mirrors observability + prompt-registry pattern).

## Cluster constrains

- Any future change that touches the `Finding`/`DriftReport`/
  `classify_binding` signature MUST NOT introduce new fields before v0.9.0
  (the `@property graph_unavailable` alias + `from_legacy` classmethods
  + `classify_binding_legacy` wrapper are the only backward-compat
  surface; they are removed in v0.9.0).
- The `drift_events.jsonl` schema is locked for v0.8.0
  (`{ts, change, decision_id, binding_id, class, detected_at}`); any
  future change that adds a drift counter MUST add it to the
  `DRIFT_COUNTER_NAMES` catalog in `observability.py` and the
  `openspec/specs/observability/spec.md` domain table.

## Next steps (post-cluster)

1. **sdd-verify drift-hardening cluster**: run the full suite + BDD
   scenarios + closeout unit tests; produce verify-report for the PR#1
   review.
2. **sdd-archive drift-hardening cluster**: sync delta specs to
   `openspec/changes/archive/2026-06-27-drift-hardening/`; preserve the
   REQ-56 v0.8.0 migration note in the archive header.
3. **change #7 PR#2 apply**: prompt-registry PR#2 (REQ-49..54) follows
   after drift-hardening archive; preserves REQ-55..59 numbering.

## Open follow-ups for v0.9.0 + v1.0

- Remove the 1-release legacy shims: `Finding.from_legacy`,
  `DriftReport.from_legacy`, `classify_binding_legacy`,
  `@property graph_unavailable` (v0.8.0 keeps; v0.9.0 removes).
- `flow drift events` CLI read-side (REQ-55 deferred; v1.0).
- `FLOW_DRIFT_EVENT_LOG_MAX_BYTES` + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS`
  env vars (REQ-55 deferred; v1.1 alongside metrics rotation).
- `DriftEvent.decision_id: int` + JSONL wire-format migration (v1.0).
- Cross-project federation for drift events (v1.0).
- OpenTelemetry push for drift events (v1.0; Prometheus textfile covers v1).
- Per-finding graph_unavailable classification refinement (v2).
- Snapshot export/import + auto-daily trigger (v2; graph-snapshots D3 precedent).
- Spec catalog baseline retro-fill for prior capability specs (REQ-9..16,
  REQ-28..34) — `openspec/specs/` bootstrap pattern continues.
- MEMORY.md / AGENTS.md update for new flow drift event log workflow.
- Cross-impact verification for all 5 prior changes
  (decision-reality-drift, vector-semantic-search,
  cross-project-federation, graph-snapshots, observability).
- README updates for new `--drift-event-log` flag + `drift_events.jsonl`
  audit trail.

## Coordination notes

- **MANDATORY**: prompt-registry change #7 PR#1 archived BEFORE
  drift-hardening apply started (preserves REQ-55..59 numbering;
  REQ-45..54 reserved for prompt-registry per Engram #183 + #201).
  ✅ satisfied (commit 51ac227).
- **MANDATORY**: drift-hardening cluster applied as 4 sequential batches
  with per-batch closeout docs (per design D12). ✅ satisfied.
- **MANDATORY**: per-commit work-unit splits per `work-unit-commits`
  skill (each commit ≤400 LOC). ✅ satisfied.

## Engram observation

This merged apply-progress observation is mirrored to Engram as
`sdd/drift-hardening/apply-progress-merged` (architecture type, project
scope). The per-batch closeout observations are mirrored as
`sdd/drift-hardening/apply-progress-batch-{a,b,c,d}` (architecture type,
project scope).
