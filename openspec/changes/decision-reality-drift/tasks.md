# Tasks: decision-reality-drift

## ⚠️ SESSION CHECKPOINT (2026-06-26)

**PR#1 STATUS: MERGED** to main (squash commit `b3a3ac7`, 364 tests passing).

**PR#2 STATUS: PENDING** — daemon `--drift` integration + SKILL.md updates + sdd-verify Step 6 + CHANGELOG.

**Branch for resume**: `feature/decision-reality-drift-pr2` (to be created from main).

**Apply-progress trail**: Engram `#125..#130` (batches A..F + recoveries).

**Next delegation**: sdd-apply PR#2 batch G (T2.1+T2.2+T2.3 — daemon --drift integration).

**Cross-session recovery**: All artifacts in Engram + OpenSpec. Re-init by reading `#130` (latest apply-progress) + this file.

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Total tasks | 16 (PR#1: 10, PR#2: 6) |
| Forecast LOC (PR#1) | ~700 |
| Forecast LOC (PR#1 ×6 TDD multiplier) | ~4200 |
| Forecast LOC (PR#2) | ~225 |
| Forecast LOC (PR#2 ×6 TDD multiplier) | ~1350 |
| **Total forecast** | **~925 LOC / ~5550 LOC real** |
| BDD feature files | 8 (7 NEW + 1 MODIFY) |
| BDD scenarios | 39 (38 NEW + 1 W3 append) |
| Chained PRs recommended | Yes |
| Chain strategy | stacked-to-main |
| 400-line budget risk | High (both PRs exceed 400 at ×6) |
| Decision needed before apply | No (auto-chain) |
| Recommended apply batch size | ≤6 tasks OR ≤150 LOC per delegation |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Work Units

| Unit | PR | Tasks | Forecast | ×6 Real | Branch | Base |
|------|----|-------|----------|---------|--------|------|
| 1 | PR#1 | T1.1–T1.10 | ~700 | ~4200 | `feature/decision-reality-drift-pr1` | `main` |
| 2 | PR#2 | T2.1–T2.6 | ~225 | ~1350 | `feature/decision-reality-drift-pr2` | `main` (after PR#1) |

---

## PR#1 — Core Verifier (`flow drift <change>` library + CLI + counters + W2/W3)

### Phase 1: Counter contract (W2) + BDD absorption (W3)

- [ ] **T1.1** W2 spec.md REQ-8 counter reconciliation
  - Type: `docs` · TDD: `N/A` · LOC: ~30
  - Files: `openspec/changes/archive/2026-06-25-decision-code-linking/spec.md` (lines 271/273/279/285)
  - Depends on: —
  - Acceptance: REQ-8 lists 8 impl counters (`suggest_invoked_total`, `suggest_hit_total`, `suggest_miss_total`, `bindings_confirmed_total`, `backfill_observations_total`, `backfill_with_refs_total`, `inspect_invoked_total`, `inspect_render_ms`); drops `avg_bindings_per_observation`; 3 scenarios assert impl names
  - Commit: `docs(spec): reconcile REQ-8 counter names to impl (W2)`

- [ ] **T1.2** W3 BDD scenario + step def
  - Type: `bdd` · TDD: `N/A` · LOC: ~11
  - Files: `tests/bdd/req3_engram_io.feature` (+1 scenario), `tests/bdd/test_decision_code_linking_p1_steps.py` (+6 LOC step def reusing `binding.extract`)
  - Depends on: —
  - Acceptance: `pytest tests/bdd/test_decision_code_linking_p1_steps.py -k "empty block"` passes the new scenario; unit test still green
  - Commit: `test(bdd): add REQ-3 empty-block-as-unbound scenario (W3)`

### Phase 2: Library scaffold + classify_binding TDD loop

- [x] **T1.3** Scaffold `decision_drift.py` with empty stubs + type hints
  - Type: `code` · TDD: `N/A` · LOC: ~40
  - Files: `src/flow_engineering/decision_drift.py`
  - Depends on: T1.1, T1.2
  - Acceptance: Module imports; `classify_binding`/`scan_change`/`DriftReport`/`Finding` exist with `raise NotImplementedError`; type hints compile
  - Commit: `feat(lib): scaffold decision_drift module with type stubs`
  - **Status (batch B)**: ✅ shipped via `ee9e039` — module imports; all 5 public symbols present; raises NotImplementedError for classify_binding/scan_change (T1.4 RED expected this).

- [x] **T1.4** RED tests for `classify_binding()` per drift class
  - Type: `test` · TDD: `RED` · LOC: ~80
  - Files: `tests/unit/test_decision_drift.py` (NEW, 14 fixtures: 2 per class × 6 + 2 unable_to_verify)
  - Depends on: T1.3
  - Acceptance: All 14 fixtures FAIL with `NotImplementedError`; commit lands red (proven by CI)
  - Commit: `test(unit): RED fixtures for classify_binding across 6 classes`
  - **Status (batch B)**: ✅ shipped via `c3524df` — 12 classify_binding fixtures RED with NotImplementedError + 2 dataclass smoke tests passing; full suite showed 305 pass + 12 fail post-commit (intentional).

- [x] **T1.5** GREEN implementation of `classify_binding()`
  - Type: `code` · TDD: `GREEN` · LOC: ~70
  - Files: `src/flow_engineering/decision_drift.py`
  - Depends on: T1.4
  - Acceptance: All 14 T1.4 fixtures PASS; coverage of `classify_binding` ≥90%
  - Commit: `feat(lib): classify_binding across 6 drift classes (GREEN)`
  - **Status (batch B)**: ✅ shipped via `b8925d1` — 5-step algorithm; 14/14 fixtures pass; full suite 317 passing (303 baseline + 14 new).

### Phase 3: Dataclasses + scan_change skeleton

- [ ] **T1.6** `DriftReport`/`Finding` dataclasses + `scan_change()` + tests
  - Type: `code` · TDD: `RED→GREEN` · LOC: ~60 impl + ~50 tests = ~110
  - Files: `src/flow_engineering/decision_drift.py`, `tests/unit/test_decision_drift.py` (+~50 LOC aggregation tests)
  - Depends on: T1.5
  - Acceptance: `scan_change` returns `DriftReport` from synthetic graph dict; aggregates `class_counts`; `unable_to_verify` path emits terminal state with `unable_reason`; multi-binding observations handled
  - Commit: `feat(lib): DriftReport dataclass + scan_change skeleton`

### Phase 4: Observability + engram_io + CLI

- [ ] **T1.7** Observability counters + `record_drift_summary()` helper
  - Type: `code` · TDD: `RED→GREEN` · LOC: ~35 impl + ~40 tests = ~75
  - Files: `src/flow_engineering/observability.py`, `tests/unit/test_observability_drift.py` (NEW)
  - Depends on: T1.6
  - Acceptance: 8 `drift_*_total` counters increment per `DriftReport.class_counts`; mocked metrics sink verifies one JSONL line per invocation with correct payload shape
  - Commit: `feat(observability): drift counters + record_drift_summary helper`

- [ ] **T1.8** `update_observation_metadata()` in `engram_io.py`
  - Type: `code` · TDD: `RED→GREEN` · LOC: ~20 impl + ~50 tests = ~70
  - Files: `src/flow_engineering/engram_io.py`, `tests/unit/test_engram_io_metadata.py` (NEW)
  - Depends on: T1.6
  - Acceptance: Appends `<!-- metadata -->` block distinct from `code_refs`; `code_refs` byte-identical after write; idempotent re-write (no duplicate keys); missing observation raises structured `ObservationNotFound`
  - Commit: `feat(io): update_observation_metadata appends drift_meta block`

- [ ] **T1.9** CLI subcommand `flow drift <change>` + tests
  - Type: `code` · TDD: `RED→GREEN` · LOC: ~90 impl + ~80 tests = ~170
  - Files: `src/flow_engineering/cli.py`, `tests/unit/test_cli_drift.py` (NEW)
  - Depends on: T1.7, T1.8
  - Acceptance: exit 0/1/2 per REQ-11 (2 wins over 1); `--json` parseable; `--include-obsolete` triggers graphify (mocked); `--write-back` calls `update_observation_metadata`; `--since` ISO 8601 validates; per-row parse errors isolated
  - Commit: `feat(cli): flow drift subcommand with exit code contract`

### Phase 5: BDD feature + step glue

- [ ] **T1.10** BDD feature `req9_drift_detection` + step defs
  - Type: `bdd` · TDD: `N/A` · LOC: ~40 feature + ~120 step defs (~8 LOC × 15 scenarios) = ~160
  - Files: `tests/bdd/req9_drift_detection.feature` (NEW), `tests/bdd/test_decision_reality_drift_steps.py` (NEW)
  - Depends on: T1.9
  - Acceptance: `pytest tests/bdd/req9_drift_detection.feature` passes 14 REQ-9 scenarios + 1 unable_to_verify round-trip
  - Commit: `test(bdd): req9_drift_detection feature + step glue`

---

## PR#2 — Verification Wiring (`flow watch --drift` + sdd-verify + SKILL.md)

### Phase 6: Daemon `--drift` integration

- [ ] **T2.1** Daemon `--drift` event handling
  - Type: `code` · TDD: `RED→GREEN` · LOC: ~60 impl + ~40 tests = ~100
  - Files: `src/flow_engineering/daemon.py`, `tests/unit/test_daemon_drift_events.py` (NEW)
  - Depends on: PR#1 merged
  - Acceptance: `start_watch(..., drift=True)` subscribes to `apply-progress.json` writes; `merged` status triggers `scan_change`; missing graph logs `unable_to_verify` once and watcher stays alive
  - Commit: `feat(daemon): flow watch --drift subscribes to apply-progress`

- [ ] **T2.2** `flow watch --drift` CLI trigger logic
  - Type: `code` · TDD: `RED→GREEN` · LOC: ~30 impl + ~60 tests = ~90
  - Files: `src/flow_engineering/cli.py`, `tests/unit/test_cli_watch_drift.py` (NEW)
  - Depends on: T2.1
  - Acceptance: `--drift` flag wires to daemon; non-drift path unchanged; on event, stdout shows summary line; counters increment; non-blocking background thread
  - Commit: `feat(cli): --drift flag on flow watch`

### Phase 7: BDD + docs + SKILL.md prose

- [ ] **T2.3** BDD feature `req15_drift_daemon` + step defs
  - Type: `bdd` · TDD: `N/A` · LOC: ~20 feature + ~25 step defs (~8 LOC × 3 scenarios) = ~45
  - Files: `tests/bdd/req15_drift_daemon.feature` (NEW), `tests/bdd/test_decision_reality_drift_steps.py` (extend)
  - Depends on: T2.2
  - Acceptance: 3 scenarios pass — event-log line on detected drift, no event-log on still-valid, daemon survives missing graph
  - Commit: `test(bdd): req15_drift_daemon feature`

- [ ] **T2.4** sdd-verify Step 6 sub-step
  - Type: `docs` · TDD: `N/A` · LOC: ~25
  - Files: `~/.config/opencode/skills/sdd-verify/SKILL.md` (runtime location, NOT repo)
  - Depends on: T2.3
  - Acceptance: New sub-step "Run `flow drift <change>` and surface findings before declaring green" present; names exit codes 0/1/2 from REQ-11
  - Commit: `docs(verify): add drift-check sub-step under Step 6`

- [ ] **T2.5** CHANGELOG.md v0.3.0 entry
  - Type: `docs` · TDD: `N/A` · LOC: ~10
  - Files: `CHANGELOG.md`
  - Depends on: T2.4
  - Acceptance: v0.3.0 entry lists `flow drift <change>`, `flow watch --drift`, W2/W3 closure, 8 new drift counters
  - Commit: `chore(release): CHANGELOG v0.3.0 entry`

- [ ] **T2.6** 6 SKILL.md "Drift detection hook" prose updates
  - Type: `docs` · TDD: `N/A` · LOC: ~25 prose (~4 LOC per file)
  - Files: `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` (runtime location, NOT repo)
  - Depends on: T2.5
  - Acceptance: Each file contains `## Drift detection hook` heading naming all 6 classes (`still_valid`, `label_drift`, `stale_location`, `stale_id`, `obsolete`, `contradicted`) + `flow drift <change>` invocation point + REQ-11/REQ-12 contract references
  - Commit: `docs(skills): extend binding hook with drift detection prose`

---

## Apply Batch Guidance (lessons from `decision-code-linking` change #1)

Per-delegation batch: **≤6 tasks OR ≤150 LOC**. Larger batches TIMEOUT.

### PR#1 suggested batches (6 batches)
| Batch | Tasks | LOC | Why |
|-------|-------|-----|-----|
| A | T1.1 + T1.2 | ~41 | W2/W3 reconciliation — small, atomic, lands first |
| B | T1.3 + T1.4 + T1.5 | ~190 | Scaffold + RED + GREEN classify — single TDD cycle |
| C | T1.6 | ~110 | Dataclasses + scan_change skeleton — one logical unit |
| D | T1.7 + T1.8 | ~145 | Observability + engram_io — both touch helpers, both ready after T1.6 |
| E | T1.9 | ~170 | CLI subcommand — needs T1.7 + T1.8 done |
| F | T1.10 | ~160 | BDD feature — binds to green T1.9 |

### PR#2 suggested batches (2 batches)
| Batch | Tasks | LOC | Why |
|-------|-------|-----|-----|
| G | T2.1 + T2.2 + T2.3 | ~190 | Daemon + CLI flag + BDD — cohesive verification wiring |
| H | T2.4 + T2.5 + T2.6 | ~60 | Docs only — last batch, after PR#2 logic lands |

---

## Out-of-scope reminders

- Snapshot-pinned drift — `graph-snapshots` owns; detector takes `graph_path` param (seam in place)
- Cross-project drift — `cross-project-federation` owns; v1 skip + WARN
- Re-suggestion on `stale_id` — surface-only; future `decision-resolve`
- Auto-fix drift — detector reports; humans fix (matches `flow inspect` precedent)

## References

- Spec: `openspec/changes/decision-reality-drift/spec.md` (8 REQs, 39 scenarios)
- Design: `openspec/changes/decision-reality-drift/design.md` (10 decisions resolved)
- Explore: Engram #120 · Proposal: Engram #121 · Spec: Engram #122 · Design: Engram #123