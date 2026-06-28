<!-- explore.md: drift-hardening. Source: sdd-explore sub-agent. -->
# Explore: drift-hardening (cluster change)

**Change:** `drift-hardening` (cluster consolidation)
**Date:** 2026-06-27
**Mode:** Strict TDD (per Engram #92 `sdd-init`)
**HEAD at exploration:** `9f03bcc` (post-observability PR#2 batch G fix)
**Branch:** `main` (working tree CLEAN except `openspec/changes/{prompt-registry,observability,drift-hardening}/` untracked)
**Source carry-forwards:** change #2 `decision-reality-drift` archive-report.md + change #5 `graph-snapshots` archive-report.md

---

## Executive Summary

The `drift-hardening` cluster change is a **spec/design reconciliation + small-impl additions** change that closes 7 documented WARNING/SUGGESTION carry-forwards from changes #2 (decision-reality-drift) and #5 (graph-snapshots). All carry-forwards are **STILL OPEN in main HEAD** — none were resolved by the observability change #6 PR#1/PR#2 work that landed in the last 24 hours. Two carry-forwards (W7, S1) were confirmed RESOLVED pre-archive in PR #6 squash `e8ac1d5`; W20/W21/W22/W24/W27 from change #5 were resolved at graph-snapshots archive. The remaining 7 items (W4, W5, W6, W8, W23, W25, W26 + S2) map cleanly to **5 REQs** (REQ-55..59 assuming prompt-registry change #7 lands first), with a total estimated wall time of **~3-4 hours** and **~5 500-7 200 LOC with ×6 TDD multiplier**. **Single PR recommended** (cluster change via 3-4 batches) — the items are thematically related and architecturally shallow.

---

## Section A: Current State of Carry-Forwards

| W/S ID | Source | Status | Current location (HEAD) | Notes |
|--------|--------|--------|--------------------------|-------|
| **W4** | decision-reality-drift #135 | **OPEN** | spec.md lines 121, 161, 183, 207, 230, 289 (archived); 21 scenarios NOT in `tests/bdd/` | BDD scenario count: spec 39 vs impl 18; missing req10/11/12/13/14/16 feature files |
| **W5** | decision-reality-drift #135 | **OPEN** | spec.md line 265 (archived); impl `daemon.py:75-97` | Spec demands JSONL at `~/.flow-engineering/drift_events.jsonl`; impl emits single stdout summary line via `on_summary` callback |
| **W6** | decision-reality-drift #135 | **OPEN** | spec.md line 274 (archived); impl `daemon.py:82-97` | Spec demands "no event-log line on still-valid"; impl always emits `"drift: <change> 0 findings (no classes)"` |
| **W8** | decision-reality-drift #135 | **OPEN** | design.md lines 134-155 (archived) vs impl `decision_drift.py:60-87` | `decision_id: str` (impl) vs `int` (spec design #123 line 136); `scanned_at: float` vs `str`; `graph_unavailable: bool` vs `unable_to_verify+unable_reason`; `classify_binding` 3 args vs 2 args |
| **S2** | decision-reality-drift #135 | **OPEN** | impl `cli.py:1637-1674` | Silent skip on non-int `decision_id` in `_write_back_findings` — increments `drift_write_back_skipped_total` but no stderr WARN |
| **W23** | graph-snapshots #188 | **OPEN** | `~/.flow-engineering/metrics.jsonl` on-disk; spec.md line 224 (archived) | Legacy `snapshot_pruned_total` events coexist with renamed `snapshot_prune_total` (wire-format change in T1.7 GREEN). Confirmed via grep: 70+ legacy events still in metrics file |
| **W25** | graph-snapshots #188 | **OPEN** | impl `snapshot_manager.py:101-121`; design.md line 271 (archived) | `SnapshotMeta.size_bytes` (impl) vs `file_size_bytes` (design); `pinned: bool` field added without spec/design coverage |
| **W26** | graph-snapshots #188 | **OPEN** | impl `snapshot_manager.py:209-247`; spec.md line 230, design.md line 66 (archived) | `PruneResult.freed_bytes` (impl) vs `freed_bytes_estimate` (spec/design). BDD scenarios don't assert exact field name |

### RESOLVED carry-forwards (verified closed, do NOT carry into this change)

| W/S ID | Source | Resolution evidence |
|--------|--------|---------------------|
| **W7** | decision-reality-drift #135 | commit `e8ac1d5` PR #6 squash — `CHANGELOG.md:116` now lists `drift_invoked_total` (not `drift_scan_total`) |
| **S1** | decision-reality-drift #135 | commit `e8ac1d5` PR #6 squash — `CHANGELOG.md:124` now says "63 BDD scenarios across 12 feature files" (not "39 across 9") |
| **W20** | graph-snapshots #188 | commit `a0c1419` — spec.md counter names reconciled to impl catalog (`snapshot_create_total`, `snapshot_prune_total`, `snapshot_load_failed_total`) |
| **W21** | graph-snapshots #188 | commits `d6525a0` + `fb3bd03` — `pyproject.toml` bumped `0.4.0` → `0.6.0`; `test_version` aligned |
| **W22** | graph-snapshots #188 | commit `5ef8f0e` — `--json` flag added to `flow snapshot list` + `flow snapshot diff` |
| **W24** | graph-snapshots #188 | commit `b7869b2` — all 47 acceptance criteria boxes flipped `[ ]` → `[x]` |
| **W27** | graph-snapshots #188 | archive phase — `apply-progress/batch-{a,b1,b2}.md` regenerated from Engram #187 (now in `openspec/changes/archive/2026-06-27-graph-snapshots/apply-progress/`) |

**Carry-forward count: 8 OPEN + 7 RESOLVED = 15 total**

---

## Section B: Fix Complexity Categorization

| W/S ID | Complexity | Estimated LOC | Tests needed | Dependencies |
|--------|-----------|---------------|--------------|--------------|
| **W25** | **TRIVIAL** | ~5 (3 line edits in design.md D2 + `SnapshotMeta` contract block) | 0 (pure spec cosmetic) | None |
| **W26** | **TRIVIAL** | ~4 (2 line edits in spec.md REQ-34 + 2 line edits in design.md D10) | 0 (pure spec cosmetic; BDD doesn't assert field name) | None |
| **S2** | **TRIVIAL** | ~10 (1 stderr WARN in `_write_back_findings` + 1 batch-summary flag) | 2 (unit: stderr captured once per batch + zero skip emits nothing) | None |
| **W23** | **SMALL** | ~30 (changelog deprecation note OR one-time metrics.jsonl wipe decision; either way ~3-line edit) | 0-1 (optional `flow metrics --domain snapshot` regression test) | None |
| **W8** | **SMALL** | ~60 (4 dataclass field-type corrections + 1 `classify_binding` arg-list revert + 4 spec edits + 2 design edits + defensive coercion helpers if backward compat needed) | 8-12 (dataclass shape round-trip tests + classify_binding backward-compat tests) | Decision: backward-compat shim or hard migration? See Risks |
| **W5+W6** | **MEDIUM** | ~150 (new `drift_event_log.py` module + JSONL append-only writer + JSONL rotation policy + spec edits + daemon.py integration + `record_drift_event` helper + integration with existing `record_drift_summary`) | 12-18 (unit: JSONL append per finding, file rotation, counter increment; BDD: 2-3 scenarios extending `req15_drift_daemon.feature`) | Counter catalog pattern from observability (`metrics.jsonl` + `record_*_summary` helper) |
| **W4** | **LARGE** | ~600 (21 BDD scenarios × ~30 LOC/scenario including step glue; 6 NEW `.feature` files: `req10_drift_cli.feature`, `req11_drift_exit.feature`, `req12_drift_counters.feature`, `req13_drift_metadata.feature`, `req14_drift_resilience.feature`, `req16_skill_prose.feature`) | +21 BDD (the deliverable) + 6 step-glue extensions | Existing step glue in `test_decision_reality_drift_steps.py`; partial coverage already in unit tests |

**Complexity breakdown**: TRIVIAL=3, SMALL=2, MEDIUM=1, LARGE=1 = **7 items**

---

## Section C: Proposed Scope

### Single PR (cluster change via 3-4 batches)

**Recommendation: SINGLE CHANGE, single PR with batched commits** (not 2 chained PRs).

**Why single PR:**
1. **Thematic unity** — all 7 carry-forwards are spec/design consistency + small-impl additions from the v0.5.0/v0.6.0 release cycle. No architectural change.
2. **Cross-impact is contained** — touches only `decision_drift.py`, `daemon.py`, `cli.py`, `snapshot_manager.py`, archived spec/design files in `openspec/changes/archive/`. No new modules except optional `drift_event_log.py`.
3. **Single sdd-verify pass** — one verify run covers everything; cleaner archive phase.
4. **No ordering dependency** — the 5 REQs are independent and can be implemented in any order within the apply batches.
5. **Lower PR overhead** — one PR review instead of two; one CI gate instead of two.

**Why NOT 2 chained PRs:**
- W4 (LARGE BDD coverage) could justify its own PR, but it's mechanical BDD scaffolding (translation of existing unit-test contracts to Gherkin), not architectural. Bundling avoids splitting the spec/design reconciliations (W8/W25/W26) from the BDD coverage that exercises them.
- Splitting would force the second PR to re-read the W8 dataclass shape from the first PR — needless friction.

### REQ allocation (assumes prompt-registry change #7 lands first)

Per Engram #183 + #201, REQ-35..39 are observability (shipped); REQ-45..47 + REQ-49..50 are prompt-registry (in progress, queued first); REQ-48 + REQ-51..54 are reserved for prompt-registry v1.1 defers. **Next available is REQ-55**.

| REQ | Title | Carries | LOC forecast |
|-----|-------|---------|--------------|
| **REQ-55** | `drift_events.jsonl` append-only event log + still-valid silence | W5 + W6 | ~150 prod + ~250 test = ~400 |
| **REQ-56** | `decision_drift` dataclass shape sync (int decision_id, ISO scanned_at, unable_reason field, 2-arg classify_binding) | W8 | ~60 prod + ~100 test = ~160 |
| **REQ-57** | BDD coverage completion for REQ-10/11/12/13/14/16 (21 scenarios across 6 feature files) | W4 | ~0 prod (only step glue) + ~600 BDD = ~600 |
| **REQ-58** | Snapshot spec/design field reconciliation (size_bytes, pinned, freed_bytes) | W25 + W26 | ~9 spec/design edits + 0 test = ~9 |
| **REQ-59** | Snapshot counter dual-name coexistence deprecation + write-back stderr WARN on skip | W23 + S2 | ~30 prod + ~25 test = ~55 |

**Total REQs**: 5 (REQ-55..REQ-59)
**Total LOC**: ~1 224 production + tests (without TDD multiplier)
**LOC with ×6 TDD multiplier**: ~7 344 (includes BDD scaffolding overhead)
**Wall time estimate**: ~3-4 hours end-to-end (3 apply batches × ~1h + design + verify)

### REQ-by-REQ plan

#### REQ-55 — `drift_events.jsonl` event log
- **Module**: `src/flow_engineering/drift_event_log.py` (NEW)
- **Counter**: `drift_event_log_total` (counter) + `drift_event_log_bytes` (gauge) via `record_drift_event()`
- **Schema**: `{ts, change, decision_id, binding_id, class, detected_at}` per spec #135 line 272
- **Path**: `~/.flow-engineering/drift_events.jsonl`; rotate when file > 10 MB (mirror `metrics.jsonl` policy)
- **Wiring**: `daemon.py:75-97` rewrites `on_summary` callback to ALSO call `record_drift_event(report)`; stdout summary retained as default behavior (NON-BREAKING with the new JSONL sink)
- **BDD**: extend `req15_drift_daemon.feature` with 2 scenarios (event-log line present on detected drift + no event-log line on still-valid + still-valid-but-graph-unavailable emits unable_to_verify line per W6 silence rule)
- **Still-valid silence**: outer summary suppressed when `total == 0 and not graph_unavailable` (fixes W6)
- **Design decision (D1)**: JSONL persistence is the source of truth; stdout summary is a UI-level mirror (defer the counter-only impl as a deprecated path)

#### REQ-56 — dataclass shape sync
- **`Finding.decision_id`**: `str` → `int` (with `__post_init__` coercion from str when input is numeric)
- **`DriftReport.scanned_at`**: `float` → `str` (ISO 8601 UTC with `Z` suffix, mirror `_now_iso()` helper at cli.py:1632)
- **`DriftReport.graph_unavailable`**: rename to `unable_to_verify: bool`; add `unable_reason: str | None`
- **`classify_binding`**: refactor to 2-arg `(ref, graph_nodes)`; pack `current_id_map` into a precomputed index on `current_nodes` (or accept either form via a tolerant adapter)
- **Spec edits**: archived `design.md` lines 134-155 reconcile; spec.md scenarios REQ-9..16 updated to match
- **Backward compat**: keep `graph_unavailable` as a `@property` alias on `DriftReport` for 1 release (deprecation warning via `DeprecationWarning`)
- **Affected tests**: `test_decision_drift.py:27`, `test_cli_drift.py:14`, `test_daemon_drift_events.py:10`, `test_cli_watch_drift.py:8`, `test_decision_drift_snap_id.py:8` — all must pass

#### REQ-57 — BDD coverage completion
- **6 NEW feature files**: `tests/bdd/req10_drift_cli.feature` (9), `req11_drift_exit.feature` (3, may overlap with req10), `req12_drift_counters.feature` (3), `req13_drift_metadata.feature` (3), `req14_drift_resilience.feature` (4), `req16_skill_prose.feature` (2)
- **Step glue**: extend `tests/bdd/test_decision_reality_drift_steps.py` (or split per REQ for clarity)
- **Strategy**: TRANSLATE existing unit tests to Gherkin — no behavior change. The unit tests at `test_cli_drift.py`, `test_observability.py`, `test_engram_io_code_refs.py` are the source; BDD scenarios mirror their Gherkin-shaped contracts.
- **Note on REQ-11**: 3 exit-code scenarios can be in `req11_drift_exit.feature` (9+3=12 total scenarios covering REQ-10+11). The verify-report #135 line 100 said 21 scenarios (REQ-10 9, REQ-12 3, REQ-13 3, REQ-14 4, REQ-16 2) — REQ-11 is folded into REQ-10's 9 scenarios per the original spec.
- **REQ-16** is runtime-only (SKILL.md file existence + grep checks) — the 2 BDD scenarios assert the grep check, not the SKILL.md content

#### REQ-58 — snapshot spec/design field reconciliation
- **W25**: `design.md:271` rewrite `file_size_bytes: int` → `size_bytes: int`; add `pinned: bool` field with retention-pin semantics (already at snapshot_manager.py:120, just document it)
- **W26**: `spec.md:230` rewrite `freed_bytes_estimate` → `freed_bytes`; `design.md:66, 474` same
- **No code change** required — both fields exist in impl correctly
- **0 new tests** (BDD req34 doesn't assert exact field name)

#### REQ-59 — counter dual-name coexistence + write-back stderr WARN
- **W23 decision**: pick one path:
  - **(a) Document coexistence** in CHANGELOG v0.6.0 Notes section + add deprecation banner to spec REQ-34 (PREFERRED — preserves audit trail; no consumer exists yet)
  - **(b) One-time wipe** of `metrics.jsonl` on next `flow metrics` startup (loses audit; simpler code)
- **S2**: add `import sys; print("WARN: drift write-back skipped N non-int decision_ids", file=sys.stderr)` at end of `_write_back_findings` when `success < len(report.findings) and skipped_total > 0`
- **Tests**: 1-2 unit tests for S2 (capture stderr; verify single WARN per batch, not per skipped row)

---

## Section D: Risks & Open Questions

### Risk 1: Dataclass shape migration backward compat (W8 / REQ-56)

**Risk**: changing `decision_id: str → int` and `scanned_at: float → str` is a public API breakage. Any third-party code importing `from flow_engineering.decision_drift import Finding, DriftReport` will fail at runtime when the new type annotations are checked (e.g., mypy strict mode).

**Mitigation options**:
- (a) **Hard migration** — clean break, bump minor version (v0.7.0 → v0.8.0). Per `pyproject.toml` history, the project is at v0.7.0 and observability has already added minor bumps; v0.8.0 is reasonable.
- (b) **Soft migration** — keep str/str types for 1 release, accept both via `__post_init__` coercion; `DeprecationWarning` on str inputs. Bump patch version only.
- (c) **Dual dataclasses** — `Finding` (new shape) + `FindingLegacy` (str/str) for 1 release; re-export `Finding = FindingLegacy`. Cleanup in v1.0.

**Recommendation**: **(a) Hard migration**. The project has 4 archived changes; no third-party consumers yet (no public package on PyPI — see `pyproject.toml:21` `[project.optional-dependencies]` for `dev` extras; `pip install flow-engineering` is not a supported install path). Bump version v0.7.0 → v0.8.0 (CHANGELOG entry). Add a `BREAKING:` section noting the dataclass shape change.

### Risk 2: Wire-format compatibility for W23 (counter dual-name)

**Risk**: legacy `snapshot_pruned_total` events are appended-only in `~/.flow-engineering/metrics.jsonl`. `flow metrics` consumer will see both `snapshot_prune_total` (new, K=70+) and `snapshot_pruned_total` (legacy, K=101+) until the file is reset. Sum-based queries (`sum(counter for counter in metrics.jsonl if counter.startswith("snapshot_"))`) double-count.

**Mitigation**: 
- **PREFERRED**: CHANGELOG v0.6.0 Notes section documents the dual-name coexistence + recommends `--domain snapshot` consumers use the new catalog filter (REQ-37 already supports domain filter)
- **FALLBACK**: add a one-time migration on `flow metrics` startup that drops events with deprecated names AND emits a stderr notice "dropped N legacy snapshot_pruned_total events"
- **NUCLEAR**: wipe `~/.flow-engineering/metrics.jsonl` on the user's machine (would need user consent)

**Recommendation**: **PREFERRED** (CHANGELOG doc). No code change beyond a 3-line CHANGELOG entry. If a downstream consumer materializes, revisit as REQ-59 follow-up.

### Risk 3: W4 BDD coverage scope (21 scenarios)

**Risk**: writing 21 BDD scenarios is mechanical but time-consuming. If rushed, the BDD scenarios become tautological (just call unit tests via `@scenario` without expressing the behavior in business terms).

**Mitigation**:
- **Subset strategy**: deliver the 21 scenarios across 2 batches (batch A: req10+req12+req16 = 14 scenarios; batch B: req11+req13+req14 = 7 scenarios + final tests)
- **Quality gate**: each BDD scenario MUST use business-domain Given/When/Then (e.g., "Given a decision with bindings at file X line Y", "When flow drift scans the change", "Then the report shows STILL_VALID") NOT unit-test phrasing ("Given a fixture dict X")
- **Reviewer**: sdd-verify's BDD subset assertion runs `uv run pytest tests/bdd/ -v` and confirms 0 failures across the 6 new feature files

**Recommendation**: deliver all 21 scenarios in the cluster change; this is the headline value-add (the spec promised them, the impl owes them).

### Risk 4: JSONL event log rotation policy (REQ-55)

**Risk**: `drift_events.jsonl` will grow unbounded (every daemon event = 1+ lines). On a long-running watcher, file size can exceed 100 MB/year.

**Mitigation**: mirror the metrics.jsonl policy from observability #183 explore (REQ-44 deferred to v1.1) — append-only with rotation when file > 10 MB; rotate to `drift_events.<timestamp>.jsonl` + start fresh `drift_events.jsonl`. Implement as REQ-55 sub-feature (no separate REQ).

### Risk 5: Step glue module size

**Risk**: extending `test_decision_reality_drift_steps.py` with 21 new scenarios + step glue will push the file past 1 000 LOC. Acceptable but review-awkward.

**Mitigation**: split per REQ (`test_req10_steps.py`, `test_req12_steps.py`, etc.). Mirrors the req28..34 split that `test_graph_snapshots_steps.py` uses.

---

## Section E: Files to Touch

### Production files (estimated LOC)

| File | Change | LOC delta | Reason |
|------|--------|-----------|--------|
| `src/flow_engineering/drift_event_log.py` | NEW | +150 | REQ-55 JSONL writer + rotation + `record_drift_event` helper |
| `src/flow_engineering/decision_drift.py` | MODIFY | +40 / -20 net | REQ-56 dataclass shape (decision_id int, scanned_at str ISO, unable_to_verify+unable_reason); 2-arg classify_binding |
| `src/flow_engineering/daemon.py` | MODIFY | +30 / -10 net | REQ-55 wire `record_drift_event` into `handle_apply_progress_event`; REQ-55 W6 still-valid silence rule in outer summary |
| `src/flow_engineering/cli.py` | MODIFY | +20 / -5 net | REQ-59 S2 stderr WARN in `_write_back_findings`; REQ-56 minor type-cast updates for the dataclass rename |
| `src/flow_engineering/observability.py` | MODIFY | +15 | REQ-55 `record_drift_event` helper + `drift_event_log_total` counter catalog entry |
| `src/flow_engineering/snapshot_manager.py` | MODIFY | 0 | REQ-58 is spec/design-only; no code change |

**Production total**: ~225 net LOC

### Test files (estimated LOC with ×6 TDD multiplier)

| File | Change | LOC delta | Reason |
|------|--------|-----------|--------|
| `tests/unit/test_drift_event_log.py` | NEW | +180 | REQ-55 JSONL writer unit tests (rotation, append, schema, counter increment) |
| `tests/unit/test_decision_drift.py` | MODIFY | +30 | REQ-56 dataclass shape round-trip + backward-compat shim tests |
| `tests/unit/test_daemon_drift_events.py` | MODIFY | +20 | REQ-55 event-log integration + REQ-55 W6 still-valid silence |
| `tests/unit/test_cli_watch_drift.py` | MODIFY | +10 | REQ-55 CLI wiring |
| `tests/unit/test_cli_drift.py` | MODIFY | +15 | REQ-59 S2 stderr WARN capture |
| `tests/bdd/req10_drift_cli.feature` | NEW | +250 | REQ-57 9 BDD scenarios |
| `tests/bdd/req11_drift_exit.feature` | NEW | +90 | REQ-57 3 BDD scenarios (or fold into req10) |
| `tests/bdd/req12_drift_counters.feature` | NEW | +90 | REQ-57 3 BDD scenarios |
| `tests/bdd/req13_drift_metadata.feature` | NEW | +90 | REQ-57 3 BDD scenarios |
| `tests/bdd/req14_drift_resilience.feature` | NEW | +120 | REQ-57 4 BDD scenarios |
| `tests/bdd/req16_skill_prose.feature` | NEW | +60 | REQ-57 2 BDD scenarios (runtime grep) |
| `tests/bdd/test_decision_reality_drift_steps.py` | MODIFY or split | +400 | REQ-57 step glue for 6 new feature files |
| `tests/bdd/req15_drift_daemon.feature` | MODIFY | +80 | REQ-55 extend with 2 JSONL event-log scenarios |

**Test total**: ~1 435 LOC (no multiplier) → ~1 600 with step glue + step defs
**With ×6 TDD multiplier**: ~9 500 LOC (inflated by BDD scenario overhead)

### Archived spec/design files (in `openspec/changes/archive/`)

| File | Change | LOC delta | Reason |
|------|--------|-----------|--------|
| `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` | MODIFY | +5 / -5 net | REQ-56 reconcile Finding/DriftReport shape + REQ-55 REQ-15 JSONL contract reaffirmation |
| `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md` | MODIFY | +10 / -8 net | REQ-56 reconcile dataclass type signatures |
| `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` | MODIFY | +3 / -3 net | REQ-58 W26 `freed_bytes` field reconciliation |
| `openspec/changes/archive/2026-06-27-graph-snapshots/design.md` | MODIFY | +5 / -5 net | REQ-58 W25 `size_bytes` + `pinned` field reconciliation |

**Archived spec/design total**: ~28 net LOC

### CHANGELOG + repo meta

| File | Change | LOC delta | Reason |
|------|--------|-----------|--------|
| `CHANGELOG.md` | MODIFY | +20 | v0.8.0 entry listing all 5 REQs + W23 deprecation note + breaking-shape-change notice |
| `pyproject.toml` | MODIFY | +1 / -1 net | `version = "0.8.0"` (REQ-56 breaking change mandates minor bump) |
| `openspec/changes/drift-hardening/` | NEW directory | (created by this explore) | explore.md + future proposal.md + design.md + spec.md + tasks.md |
| `openspec/changes/drift-hardening/apply-progress/` | NEW (during apply) | (will be created) | 3-4 batch files (A: dataclass + spec reconciliation; B: JSONL event-log; C: BDD coverage; D: CHANGELOG + verify) |

### LOC forecast (with ×6 TDD multiplier)

| Bucket | Net LOC | ×6 TDD | Notes |
|--------|---------|--------|-------|
| Production code | 225 | 225 × 6 = 1 350 | Realistic; BDD scaffolding is in test bucket |
| Test code | 1 600 | (already in bucket) | Includes BDD scenarios + step glue |
| Archived spec/design | 28 | 28 | Edits only, no new test |
| **Grand total** | **1 853** | **~9 700** | Includes 6 NEW BDD feature files (heavy on Gherkin scaffolding) |

### Wall time forecast

| Phase | Estimated time |
|-------|----------------|
| sdd-propose | 20 min |
| sdd-design | 30 min |
| sdd-spec | 20 min |
| sdd-tasks | 20 min |
| sdd-apply batch A (REQ-56 dataclass + REQ-58 spec/design) | 60 min |
| sdd-apply batch B (REQ-55 JSONL event-log + REQ-59 W23+S2) | 60 min |
| sdd-apply batch C (REQ-57 BDD coverage — 21 scenarios) | 60 min |
| sdd-apply batch D (CHANGELOG v0.8.0 + 6 SKILL.md hook + pyproject bump) | 30 min |
| sdd-verify | 20 min |
| sdd-archive | 15 min |
| **Total** | **~5.5 hours** end-to-end |

(Compared to the prompt's "~3-4 hours" estimate — the BDD coverage batch is the bottleneck at 60 min for 21 scenarios. If rushed, defer some scenarios to `drift-hardening-v2`; see Risk 3.)

---

## Open Questions for `sdd-propose`

1. **OQ-1** (REQ-56 backward compat): Hard migration vs soft migration vs dual dataclasses? **Recommend hard migration** (bump to v0.8.0); see Risk 1.
2. **OQ-2** (REQ-55 counter): should `record_drift_event` emit a new `drift_event_log_total` counter, or piggyback on the existing 8 `drift_*_total` counters? **Recommend new counter** for observability of the event-log sink itself (parallels `metrics.jsonl` audit pattern).
3. **OQ-3** (REQ-59 W23): CHANGELOG deprecation note vs metrics.jsonl wipe vs migration-on-startup? **Recommend CHANGELOG deprecation note** (no code change); see Risk 2.
4. **OQ-4** (REQ-57 BDD quality gate): should sdd-verify's BDD subset assertion be extended to require 21 NEW scenarios (currently it asserts only on the existing 17)? **Recommend yes** — add a follow-up `sdd-verify` Step 6b that asserts the cluster-specific scenario count.
5. **OQ-5** (scope order): should `drift-hardening` land BEFORE or AFTER `prompt-registry` change #7? **Recommend AFTER** — keeps the prompt-registry queue unblocked and gives drift-hardening REQ-55+ (cleaner than stealing REQ-40..44 which observability v1.1 has reserved).

---

## Next Steps

- **sdd-propose drift-hardening** with the 5 REQ structure (REQ-55..59) + single-PR-batch strategy + 4-batch apply plan
- Coordinate with prompt-registry queue: drift-hardening should NOT start until prompt-registry is archived (preserves REQ numbering)
- Pre-flight: confirm the `flow` script has no third-party consumers (check `pip search flow-engineering` for unrelated packages; verify `pyproject.toml` is the only installation entry point)

---

## Relevant Files

### Production code (current state in main HEAD)

- `src/flow_engineering/decision_drift.py` — `Finding`/`DriftReport` dataclasses (line 60-87) + `classify_binding` (84-112) + `scan_change` (423-666); REQ-9, REQ-12, REQ-33
- `src/flow_engineering/daemon.py` — `handle_apply_progress_event` (34-98) + `start_watch` (144-210); REQ-15
- `src/flow_engineering/cli.py` — `_write_back_findings` (1637-1674); REQ-10/11/14/15
- `src/flow_engineering/snapshot_manager.py` — `SnapshotMeta` (100-121) + `PruneResult` (209-247); REQ-28..34
- `src/flow_engineering/observability.py` — counter catalogs + `record_drift_summary`; REQ-12/26
- `src/flow_engineering/engram_io.py` — `update_observation_metadata`; REQ-13

### Archived spec/design (source of truth for drift/snapshot REQs)

- `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` — REQ-9..16 (lines 19-308); 39 BDD scenarios (lines 339-349)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md` — 10 architecture decisions + dataclass type signatures (lines 134-155)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/archive-report.md` — confirms W4/W5/W6/W8/S2 carry-forward ownership
- `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` — REQ-28..34 (lines 34-261); `freed_bytes_estimate` field at line 230
- `openspec/changes/archive/2026-06-27-graph-snapshots/design.md` — D1..D13 + `SnapshotMeta` contract (line 271); `freed_bytes_estimate` at lines 66, 474
- `openspec/changes/archive/2026-06-27-graph-snapshots/archive-report.md` — confirms W23/W25/W26/W27 ownership

### Test infrastructure (current state)

- `tests/bdd/req9_drift_detection.feature` — 14 REQ-9 scenarios (current)
- `tests/bdd/req15_drift_daemon.feature` — 3 REQ-15 scenarios (current)
- `tests/bdd/req28..req34_*.feature` — 14 BDD scenarios (graph-snapshots, current)
- `tests/bdd/test_decision_reality_drift_steps.py` — step glue (current)
- `tests/bdd/test_graph_snapshots_steps.py` — step glue (current)
- `tests/unit/test_decision_drift.py` — 27 unit tests for classify/scan/counters
- `tests/unit/test_cli_drift.py` — 14 unit tests for CLI surface (REQ-10/11/14)
- `tests/unit/test_daemon_drift_events.py` — 10 unit tests for daemon seam
- `tests/unit/test_cli_watch_drift.py` — 8 unit tests for `--drift` flag
- `tests/unit/test_engram_io_code_refs.py::TestUpdateObservationMetadata` — 6 unit tests for metadata helper (REQ-13)
- `tests/unit/test_snapshot_manager.py` — 32 unit tests (create/list/show/diff/rollback/prune)
- **Total tests in HEAD**: 947 (`uv run pytest --collect-only` confirmed)

### Repo meta

- `CHANGELOG.md` — current entries v0.1.0..v0.7.0 (162 lines); new v0.8.0 entry needed
- `pyproject.toml` — current version `0.7.0` (line 3); bump to `0.8.0` for REQ-56 breaking change

### Engram observations

- #135 — `sdd/decision-reality-drift/verify-report` (source for W4/W5/W6/W7/W8/S1/S2)
- #188 — `sdd/graph-snapshots/verify-report` (source for W20..W27, S18..S22)
- #183 — `sdd/observability/explore` (template + JSONL rotation pattern reference for REQ-55)

---

## Skill Resolution

- `paths-injected` — skill paths resolved directly via filesystem Read; no fallback needed.

**Session**: flow-engineering-drift-hardening-explore-2026-06-27
**Topic**: sdd/drift-hardening/explore
**Next**: `sdd-propose drift-hardening` (5 REQs: REQ-55..59, single PR, 4 batches)