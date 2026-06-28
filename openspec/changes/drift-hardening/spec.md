<!-- Spec: drift-hardening. Source: sdd-spec sub-agent. -->
# Spec: drift-hardening

**Change:** `drift-hardening`
**Builds on:** `proposal.md` (Approach A — single PR, 4 apply batches: A=REQ-56+58 dataclass + spec/design reconciliation, B=REQ-55+59 JSONL writer + W23 deprecation + S2 stderr WARN, C=REQ-57 21 BDD scenarios, D=CHANGELOG v0.8.0 + 6 SKILL.md hook + pyproject bump); bootstraps `openspec/specs/drift-hardening/spec.md` capability catalog
**Date:** 2026-06-27
**Status:** SPECIFIED → ready for sdd-tasks

```yaml
status: success
confidence: high
change: drift-hardening
pr_split: single PR (4 sequential apply batches: A → B → C → D)
total_reqs: 5
total_bdd_scenarios: 21
file_created: C:\dev\proyects\flow-engineering\openspec\changes\drift-hardening\spec.md
next_recommended: sdd-design drift-hardening
```

## Goal

`flow-engineering` carries **8 open WARNING/SUGGESTION carry-forwards** from changes #2 (`decision-reality-drift`, v0.3.0) and #5 (`graph-snapshots`, v0.6.0) that have accumulated since ship — W4/W5/W6/W8/S2 from #2 plus W23/W25/W26 from #5 (7 other items were RESOLVED at observability PR#1/PR#2 land in commit `e8ac1d5` / `a0c1419` etc.). The drift layer's dataclass shape drifted from spec (`decision_id: str` impl vs `int` design; `scanned_at: float` vs `str`; `graph_unavailable: bool` vs `unable_to_verify + unable_reason`; `classify_binding` 3 args vs 2); the daemon emits a single stdout line via `on_summary` but never persists to `~/.flow-engineering/drift_events.jsonl` (W5) and never honors the still-valid silence rule (W6); the spec promised 39 BDD scenarios across 9 feature files for REQ-9..16 but `tests/bdd/` only ships 18 across 3 (W4); the snapshot layer's `SnapshotMeta.size_bytes` (impl) vs `file_size_bytes` (design) and `PruneResult.freed_bytes` (impl) vs `freed_bytes_estimate` (spec/design) need spec reconciliation (W25/W26); the W23 dual-name `snapshot_pruned_total` ↔ `snapshot_prune_total` coexistence in `metrics.jsonl` lacks an explicit deprecation note; and the silent skip on non-int `decision_id` in `_write_back_findings` (S2) needs a stderr WARN. This change ships a **single PR with 4 sequential apply batches** that closes all 8 carry-forwards under 5 REQs (REQ-55..59) — the headline deliverable is the **21 new BDD scenarios across 6 feature files** (REQ-57 / W4) that v0.3.0 promised but never shipped. A secondary deliverable is the **v0.7.0 → v0.8.0 version bump** mandated by the W8 dataclass shape migration (REQ-56) which IS a public-API break — the 1-release `DeprecationWarning` aliases on `DriftReport.graph_unavailable` and `Finding.__post_init__` str-coercion are the migration path. Coordination: change #7 (`prompt-registry`) MUST archive before this change starts, to preserve the REQ-55 numbering (REQ-45..54 are reserved for prompt-registry per Engram #183 + #201).

The new module is **`src/flow_engineering/drift_event_log.py`** (~150 LOC) exposing `record_drift_event(report)` + `iter_drift_events(*, since_iso, change)` + 10 MB JSONL rotation (mirrors `metrics.jsonl` policy from REQ-8 / observability REQ-37). The CLI surface lives in **`src/flow_engineering/cli.py`** as 1 new flag on the existing `flow drift daemon` command (`--drift-event-log[=<path>]`, default-on with `--no-drift-event-log` opt-out) + 1 stderr WARN in `_write_back_findings` when `skipped_total >= 3` non-int decision_ids are encountered. The dataclass seam lives in **`src/flow_engineering/decision_drift.py`** as 4 type-shape corrections + 1 `@property graph_unavailable` alias + 1 `from_scanned()` classmethod (legacy float-coercion bridge). The spec/design reconciliation lives in 2 archived files (`decision-reality-drift/spec.md` + `design.md`, `graph-snapshots/spec.md` + `design.md`) as 18 net LOC of field-name corrections.

---

## Contract table (per-batch breakdown)

| Batch | REQs | LOC forecast (production / test) | BDD scenarios |
|-------|------|----------------------------------|---------------|
| **A** — dataclass shape + spec/design reconciliation | REQ-56 + REQ-58 | ~100 prod / ~130 test (~250 forecast → ~800 realistic with ×3 spec-only + ×3 TDD) | 0 (spec/design reconciliation + dataclass migration; no new BDD scenarios in this batch) |
| **B** — JSONL event log + W23 deprecation + S2 stderr WARN | REQ-55 + REQ-59 | ~250 prod / ~500 test (~750 forecast → ~2 300 realistic with ×3 TDD multiplier) | 4 (REQ-55: 2, REQ-59: 2) |
| **C** — 21 new BDD scenarios for REQ-10/12/13/14/16 | REQ-57 | ~100 prod (step glue only) / ~800 test (21 BDD scenarios + step glue) | 21 |
| **D** — CHANGELOG v0.8.0 + 6 SKILL.md hook + pyproject bump + v0.6.0 W23 Notes entry | (meta) | ~300 prod (CHANGELOG + 6 SKILL.md) / ~400 test | 0 (docs + meta; BDD already covered in batch C) |
| **Total** | **5 REQs** | **~750 prod / ~1 830 test forecast** (realistic ~9 700 with ×6 strict-TDD multiplier per `decision-code-linking` archive-report #119 S3) | **21 BDD scenarios + 4 BDD scenarios + 2 stderr-WARN unit tests + 30+ JSONL unit tests** |

**Realistic LOC multiplier rationale** — per `decision-code-linking` archive-report #119 S3, the strict-TDD ×6 multiplier maps a ~1 853 LOC forecast to ~9 700 realistic. This change ships at the lower end of that range (single PR, cluster identity, no architectural change) — cluster identity is worth bundling despite the close-to-chained-PR threshold because the W8 dataclass migration (REQ-56) and the W4 BDD coverage (REQ-57) that exercises the new shape are tightly coupled. Per-commit work-unit splits per `work-unit-commits` skill (4-6 commits each ≤400 LOC).

---

## Batch A — REQ-56 + REQ-58: dataclass shape sync + spec/design reconciliation

### REQ-56: `DecisionDrift` dataclass shape sync (int decision_id + ISO scanned_at + unable_reason + 2-arg classify_binding)

#### REQ-56: `DecisionDrift` dataclass shape sync (int decision_id + ISO scanned_at + unable_reason + 2-arg classify_binding)

**Statement**: The system MUST expose `Finding.decision_id` as `int`, `DriftReport.scanned_at` as ISO 8601 UTC `str`, `DriftReport.unable_to_verify: bool` + `unable_reason: str | None` (renamed from `graph_unavailable`), and `classify_binding(ref, graph_nodes)` as a 2-arg function — with `@property graph_unavailable` retained on `DriftReport` for 1 release as a `DeprecationWarning`-emitting alias, and `Finding.__post_init__` accepting legacy numeric `str` inputs with `DeprecationWarning` + `int` coercion.

**Contract**:
- **Inputs**: legacy callers passing `decision_id: str` (numeric), `scanned_at: float` (epoch seconds), or accessing `graph_unavailable` get a `DeprecationWarning` (NOT an exception) for v0.8.0.
- **Outputs**: `Finding.decision_id: int` post-`__post_init__` coercion; `DriftReport.scanned_at: str` ISO 8601 UTC (e.g., `"2026-06-27T12:34:56Z"`); `DriftReport.unable_to_verify: bool` + `unable_reason: str | None` are the primary fields; `classify_binding(ref, graph_nodes)` returns `FindingClass` derived from the 2-arg contract; `graph_unavailable` `@property` returns `unable_to_verify` with `DeprecationWarning`.
- **Behavior**: The migration is a **HARD break** at v0.8.0 (per Engram #92 sdd-init, project is unpublished; no third-party consumers). The 1-release `DeprecationWarning` aliases soften the migration path. `Finding.__post_init__` accepts legacy numeric `str` inputs (e.g., `"42"`) and coerces to `int` with `DeprecationWarning(f"Finding.decision_id: str is deprecated; pass int (REQ-56).")`. `DriftReport.from_scanned(*, change, scanned_at, unable_to_verify, unable_reason, findings)` classmethod accepts legacy `float` epoch inputs and coerces to ISO `str`. `classify_binding(ref, graph_nodes)` is now 2-arg — 3-arg callers get `TypeError`. `DriftReport.graph_unavailable` `@property` emits `DeprecationWarning` and returns `unable_to_verify`. Version bump: `pyproject.toml` 0.7.0 → 0.8.0; CHANGELOG `BREAKING:` section.

**BDD Scenarios**: covered transitively via REQ-57 21 scenarios (no REQ-56-specific BDD scenarios — the migration is internal; behavior is unchanged at the CLI level).

```gherkin
Scenario: REQ-56 — Finding.decision_id accepts int directly without warning
  Given a decision_id value of 42 (Python int)
  When Finding(decision_id=42, binding_id="b1", finding_class=STILL_VALID, message="ok") is constructed
  Then the resulting Finding has decision_id == 42 (int, no coercion)
  And no DeprecationWarning is emitted
  And the Finding is hashable + frozen (dataclass(frozen=True) invariant)

Scenario: REQ-56 — Finding.decision_id accepts numeric str with DeprecationWarning + coercion
  Given a legacy decision_id value of "42" (Python str)
  When Finding(decision_id="42", binding_id="b1", finding_class=STILL_VALID, message="ok") is constructed
  Then the resulting Finding has decision_id == 42 (int, coerced)
  And a DeprecationWarning is emitted with the message "Finding.decision_id: str is deprecated; pass int (REQ-56)."
  And the Finding is hashable + frozen

Scenario: REQ-56 — Finding.decision_id rejects non-numeric str with ValueError
  Given a legacy decision_id value of "not-a-number" (Python str)
  When Finding(decision_id="not-a-number", binding_id="b1", finding_class=STILL_VALID, message="ok") is constructed
  Then ValueError is raised with "decision_id must be int or numeric str, got 'not-a-number'"
  And the Finding is NOT constructed

Scenario: REQ-56 — DriftReport.scanned_at accepts ISO str directly
  Given a scanned_at value of "2026-06-27T12:34:56Z"
  When DriftReport(change="obs", scanned_at="2026-06-27T12:34:56Z", findings=()) is constructed
  Then the resulting DriftReport has scanned_at == "2026-06-27T12:34:56Z"
  And no DeprecationWarning is emitted

Scenario: REQ-56 — DriftReport.from_scanned accepts legacy float epoch and coerces to ISO
  Given a scanned_at value of 1751000000.0 (Unix epoch, ~2025-06-27)
  When DriftReport.from_scanned(change="obs", scanned_at=1751000000.0) is called
  Then the resulting DriftReport has scanned_at == "2025-06-27T16:53:20Z" (ISO 8601 UTC)
  And no DeprecationWarning is emitted (from_scanned is the explicit migration path)

Scenario: REQ-56 — DriftReport.graph_unavailable @property emits DeprecationWarning + returns unable_to_verify
  Given a DriftReport with unable_to_verify=True and unable_reason="graph_unavailable"
  When the .graph_unavailable attribute is accessed
  Then the returned value is True (matching unable_to_verify)
  And a DeprecationWarning is emitted with "DriftReport.graph_unavailable is deprecated; use unable_to_verify (REQ-56)."

Scenario: REQ-56 — classify_binding 2-arg signature works for STALE classification
  Given a BindingRef to a file that no longer exists in graph_nodes
  When classify_binding(ref, graph_nodes) is called (2 args)
  Then the returned FindingClass is STALE
  And no TypeError is raised

Scenario: REQ-56 — classify_binding 3-arg call raises TypeError
  Given a BindingRef + graph_nodes + legacy current_id_map dict
  When classify_binding(ref, graph_nodes, current_id_map) is called (3 args)
  Then TypeError is raised (signature changed; current_id_map is now derived inside)
```

**Edge cases / error modes**:
- Non-numeric `str` for `decision_id` raises `ValueError` (NOT `DeprecationWarning` — graceful coercion is only for numeric strings).
- `DriftReport` with `unable_to_verify=True` and `unable_reason=None` is allowed (the reason is optional; default `None` means "graph unavailable, no further detail").
- `classify_binding` with `graph_nodes=None` or empty dict falls through to the `MISSING` / `UNABLE_TO_VERIFY` branch — covered by existing unit tests in `test_decision_drift.py`.

**Out-of-scope (deferred)**:
- `FindingLegacy` dataclass shim (rejected by Risk 1 mitigation option (c)) — the `@property graph_unavailable` + `__post_init__` coercion is the migration path; v1.0 removes both.
- Mypy strict-mode adapter for `decision_id: int | str` typing — v0.8.0 ships `int`-only; legacy callers must update by v1.0.

**Dependencies on prior REQs**:
- REQ-9 (`flow drift scan <change>`) — the CLI surface that returns `DriftReport` and is consumed by REQ-12 counter emission.
- REQ-12 (`record_drift_summary`) — emits 8 `drift_*_total` counters; the dataclass rename cascades into the `record_drift_summary` helper signature update.
- REQ-15 (`flow drift daemon --drift`) — the daemon seam that consumes `DriftReport`; `handle_apply_progress_event` signature update for `unable_to_verify` rename.

### REQ-58: Snapshot spec/design field reconciliation (`size_bytes` + `pinned` + `freed_bytes`)

#### REQ-58: Snapshot spec/design field reconciliation (`size_bytes` + `pinned` + `freed_bytes`)

**Statement**: The system MUST document `SnapshotMeta.size_bytes: int` (renamed from `file_size_bytes`) and `SnapshotMeta.pinned: bool` retention-pin field in the archived design.md; and `PruneResult.freed_bytes: int` (renamed from `freed_bytes_estimate`) in archived spec.md and design.md — with **0 production code change** (impl already correct per `snapshot_manager.py:101-121` + `:209-247`).

**Contract**:
- **Inputs**: archived `openspec/changes/archive/2026-06-27-graph-snapshots/design.md:271` `SnapshotMeta` contract block + `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md:230` REQ-34 `PruneResult` field declaration + `openspec/changes/archive/2026-06-27-graph-snapshots/design.md:66,474` (`PruneResult` references).
- **Outputs**: 18 net LOC of field-name corrections across the 2 archived spec/design files. The implementation (`snapshot_manager.py`) is unchanged because the impl already uses `size_bytes` + `pinned` + `freed_bytes`.
- **Behavior**: `SnapshotMeta` (the dataclass returned by `flow snapshot show` + `flow snapshot list`) has `size_bytes: int` (the on-disk byte size, post-gzip) and `pinned: bool` (whether the snapshot is exempt from `flow snapshot prune` auto-deletion — set via `--pin` flag at create time, retained in the envelope `metadata.pinned` field). `PruneResult` (returned by `flow snapshot prune`) has `freed_bytes: int` (the cumulative bytes reclaimed by the prune operation — pre-gzip sum of pruned files). BDD scenarios for REQ-30 (`flow snapshot list`) and REQ-34 (`flow snapshot prune`) don't assert exact field name (per explore #222), so renaming the spec/design contract has NO test churn.

**BDD Scenarios**: 2 unit/grep scenarios (not full BDD) — covered by REQ-59 BDD scenarios #1 + #2 below (cross-cutting concern; see "SnapshotMeta.size_bytes field is exposed via show command" + "PruneResult.freed_bytes matches spec field name"). Strict BDD scenarios for REQ-58 itself are deferred to the spec/design-only reconciliation phase (covered by sdd-verify grep assertions).

```gherkin
Scenario: SnapshotMeta.size_bytes field is exposed via flow snapshot show command
  Given a snapshot file snap_<ISO>-<6hex>.json.gz exists at ~/.flow-engineering/snapshots/
  When "flow snapshot show <snap_id>" is invoked
  Then the printed JSON envelope contains "size_bytes" (int, the on-disk byte size) at metadata.size_bytes
  And the printed JSON envelope does NOT contain "file_size_bytes" (the legacy design name)
  And the size_bytes value matches the on-disk byte size of the gzipped file

Scenario: PruneResult.freed_bytes matches spec field name
  Given 5 snapshots exist with 3 marked eligible for prune (not pinned)
  When "flow snapshot prune --dry-run" is invoked
  Then the printed JSON envelope contains "freed_bytes" (int, the cumulative bytes that WOULD be reclaimed)
  And the printed JSON envelope does NOT contain "freed_bytes_estimate" (the legacy spec/design name)
  And the freed_bytes value equals the sum of size_bytes for the 3 eligible snapshots
```

**Edge cases / error modes**:
- A snapshot with `pinned: False` (default) is eligible for auto-prune; `pinned: True` snapshots are skipped by `flow snapshot prune` even if they are the oldest.
- `size_bytes` for a `.json` (uncompressed) snapshot is the raw byte size; for `.json.gz` is the gzipped byte size — both reported as `size_bytes` regardless of extension.
- `freed_bytes` is computed pre-prune (sum of `size_bytes` of snapshots that WILL be deleted) — NOT the post-prune actual reclaim (which would equal `freed_bytes` minus any failures).

**Out-of-scope (deferred)**:
- Snapshot export/import for sharing (`flow snapshot export <id>` / `flow snapshot import <id>`) — already deferred in `graph-snapshots` archive; unchanged.
- Auto-daily snapshot trigger (`trigger="auto"`) — v2; v1 supports `manual` + `rollback_safety` only.
- Snapshot diff rendering with `--format=unified` — v1 is JSON-only; deferred.

**Dependencies on prior REQs**:
- REQ-30 (`flow snapshot list`) — uses `size_bytes` in the list entry shape.
- REQ-32 (`flow snapshot rollback`) — emits `RollbackResult` with `safety_snapshot_id` (a `snap_id`, not a `SnapshotMeta` directly).
- REQ-34 (`flow snapshot prune`) — emits `PruneResult` with `freed_bytes`.

### Batch A acceptance criteria

- [ ] `Finding.decision_id` accepts `int` directly; legacy numeric `str` inputs coerce with `DeprecationWarning` (REQ-56, 4 unit tests).
- [ ] `DriftReport.scanned_at` accepts `str` ISO 8601 directly; legacy `float` epoch inputs coerce via `from_scanned()` (REQ-56, 4 unit tests).
- [ ] `DriftReport.unable_to_verify: bool` + `unable_reason: str | None` are the primary fields; `@property graph_unavailable` emits `DeprecationWarning` and returns `unable_to_verify` (REQ-56, 2 unit tests).
- [ ] `classify_binding(ref, graph_nodes)` 2-arg signature works; 3-arg callers get `TypeError` (REQ-56 W8, 2 unit tests).
- [ ] `SnapshotMeta.size_bytes: int` documented in `openspec/changes/archive/2026-06-27-graph-snapshots/design.md:271` (REQ-58 W25, 0 tests — runtime grep on design.md).
- [ ] `SnapshotMeta.pinned: bool` retention-pin field documented in archived `design.md:271` (REQ-58 W25, 0 tests — runtime grep).
- [ ] `PruneResult.freed_bytes: int` documented in archived `spec.md:230` and `design.md:66,474` (REQ-58 W26, 0 tests — runtime grep).
- [ ] `drift_drift.py` + `cli.py` + `daemon.py` updated for the dataclass rename (~10 type-cast sites); no runtime behavior change at the CLI level.
- [ ] All existing 947 tests pass; `ruff check` clean on changed files.
- [ ] Per-commit work-unit splits per `work-unit-commits` skill (4-6 commits each ≤400 LOC).
- [ ] Strict TDD evidence: every modified helper has RED → GREEN → REFACTOR history in commit log.

### Batch A files to touch

**Production (~100 LOC):**
- `src/flow_engineering/decision_drift.py` (MODIFY): `Finding.decision_id: int` + `__post_init__` coercion; `DriftReport.scanned_at: str`; `unable_to_verify` + `unable_reason` rename; `@property graph_unavailable` alias; `from_scanned()` classmethod; `classify_binding(ref, graph_nodes)` 2-arg signature; ~+60 / -20 LOC delta
- `src/flow_engineering/cli.py` (MODIFY): type-cast updates for the dataclass rename at ~10 sites (`_write_back_findings`, `flow drift scan`, `_summarize_metrics`); ~+15 / -5 LOC delta
- `src/flow_engineering/daemon.py` (MODIFY): `handle_apply_progress_event` signature update for `unable_to_verify` rename; ~+10 / -2 LOC delta
- `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` (MODIFY): REQ-9..16 scenarios reconciled with new shape (decision_id int, scanned_at str ISO, unable_to_verify+unable_reason); ~+5 / -5 LOC delta
- `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md` (MODIFY): dataclass type signatures at lines 134-155 reconciled; ~+10 / -8 LOC delta
- `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` (MODIFY): REQ-34 `freed_bytes` field at line 230; ~+3 / -3 LOC delta
- `openspec/changes/archive/2026-06-27-graph-snapshots/design.md` (MODIFY): `SnapshotMeta` contract block `size_bytes` + `pinned` at line 271 + `PruneResult.freed_bytes` at lines 66, 474; ~+5 / -5 LOC delta

**Tests (~130 LOC):**
- `tests/unit/test_decision_drift.py` (MODIFY): +dataclass shape round-trip + `DeprecationWarning` capture tests for `decision_id` + `scanned_at` + `graph_unavailable` + `classify_binding` 2-arg + 3-arg TypeError; ~+30 LOC delta
- `tests/unit/test_cli_drift.py` (MODIFY): +cast site updates for the dataclass rename; ~+10 LOC delta
- `tests/unit/test_daemon_drift_events.py` (MODIFY): +dataclass rename smoke tests (consumes the new `unable_to_verify` field); ~+10 LOC delta

---

## Batch B — REQ-55 + REQ-59: JSONL event log + W23 deprecation + S2 stderr WARN

### REQ-55: `drift_events.jsonl` append-only event log + still-valid silence (W5 + W6)

#### REQ-55: `drift_events.jsonl` append-only event log + still-valid silence (W5 + W6)

**Statement**: The system MUST provide a `drift_event_log.py` module that appends one JSON line per non-still-valid finding to `~/.flow-engineering/drift_events.jsonl` (10 MB rotation policy mirrors `metrics.jsonl`); and the daemon's outer `on_summary` stdout line MUST be suppressed when `report.total == 0 and not report.unable_to_verify` (the still-valid silence rule W6), while preserving the JSONL append for audit trail completeness.

**Contract**:
- **Inputs**: a `DriftReport` (post-REQ-56 shape) from `decision_drift.scan_change(change_name)`; the user-facing daemon flag `--drift-event-log[=<path>]` (default-on, default path `~/.flow-engineering/drift_events.jsonl`, opt-out via `--no-drift-event-log`).
- **Outputs**: one JSON line per non-still-valid finding appended to `~/.flow-engineering/drift_events.jsonl` with the schema `{ts, change, decision_id, binding_id, class, detected_at}` (per archived spec #135 line 272). Counter `drift_event_log_total{change=<change>}` increments per finding appended. Counter `drift_event_log_bytes` gauges the current sink size post-rotation. When `report.total == 0 and not report.unable_to_verify`, the outer `on_summary` stdout line is suppressed (W6 silence rule); the JSONL append still happens (audit trail preserved).
- **Behavior**: `record_drift_event(report, *, path=None)` is the new public API in `drift_event_log.py` (NEW module). The function iterates `report.findings`, serializes each finding as one JSON line, and appends. The function is **best-effort**: wrapped in `try/except OSError` — on `OSError` (disk full, permission denied), it logs to stderr and returns without raising (matches `observability.increment()` policy — never crashes the caller). Rotation is automatic on append when the target file exceeds 10 MB: `_rotate_if_needed(path)` checks `path.stat().st_size >= ROTATE_BYTES (10 * 1024 * 1024)` and rotates to `drift_events.<ISO-no-colons>.jsonl` + fresh `drift_events.jsonl`. The `iter_drift_events(*, since_iso, change)` function reads the JSONL with optional `since_iso` and `change` filters (lexicographic ISO comparison since timestamps are ISO 8601 UTC `Z`-suffixed). The daemon's `handle_apply_progress_event` is rewired: when `--drift-event-log` is enabled (default), it calls `record_drift_event(report)` AFTER the existing `record_drift_summary(report)` call; the outer `on_summary` callback is gated by `if report.total > 0 or report.unable_to_verify:` to suppress the still-valid silence line.

**BDD Scenarios**: 2 scenarios (extend `req15_drift_daemon.feature`):

```gherkin
Scenario: REQ-55 — Daemon emits one JSONL line per finding with required keys
  Given a change "obs" with 3 bindings (2 STALE + 1 MISSING)
  And a fresh ~/.flow-engineering/drift_events.jsonl (empty)
  When "flow drift daemon --drift --drift-event-log" runs for change "obs" (one tick)
  Then ~/.flow-engineering/drift_events.jsonl contains exactly 3 new JSONL lines
  And each line is valid JSON with the required keys ts, change, decision_id, binding_id, class, detected_at
  And the ts field is ISO 8601 UTC with Z suffix (e.g., "2026-06-27T12:34:56Z")
  And the change field equals "obs"
  And the decision_id field is an int (post-REQ-56)
  And the class field is one of STALE, MISSING, ORPHAN, UNABLE_TO_VERIFY (NOT STILL_VALID — silence rule)
  And the counter drift_event_log_total{change="obs"} increments by 3
  And the counter drift_event_log_bytes is updated to the new file size

Scenario: REQ-55 — Daemon emits no JSONL line on still-valid silence + W6 outer summary suppression
  Given a change "obs" with 3 bindings (all STILL_VALID)
  And a fresh ~/.flow-engineering/drift_events.jsonl (empty)
  When "flow drift daemon --drift --drift-event-log" runs for change "obs" (one tick)
  Then ~/.flow-engineering/drift_events.jsonl contains exactly 0 new JSONL lines (W5 — only non-still-valid findings get persisted)
  And the outer stdout "drift: obs 0 findings (no classes)" line is SUPPRESSED (W6 silence rule)
  And the inner per-finding lines are NOT printed (the outer line IS the per-tick summary; suppression = silence)
  And the counter drift_event_log_total{change="obs"} does NOT increment (0 findings persisted)
  And the daemon exits 0

Scenario: REQ-55 — Still-valid-but-graph-unavailable emits unable_to_verify summary line (W6 edge case)
  Given a change "obs" with 3 bindings (all STILL_VALID)
  And the graph_json file is missing (unable_to_verify=True, unable_reason="graph_json_missing")
  When "flow drift daemon --drift --drift-event-log" runs for change "obs" (one tick)
  Then ~/.flow-engineering/drift_events.jsonl contains exactly 0 new JSONL lines (still-valid findings still not persisted)
  And the outer stdout "drift: obs 0 findings (graph_unavailable: graph_json_missing)" line IS printed (NOT suppressed — unable_to_verify=True forces the summary)
  And the daemon exits 2 (unable_to_verify exit code)

Scenario: REQ-55 — JSONL rotation when file exceeds 10 MB produces a sibling + fresh file
  Given a ~/.flow-engineering/drift_events.jsonl file that is exactly 10 * 1024 * 1024 bytes (the rotation threshold)
  And a DriftReport with 1 STALE finding
  When "flow drift daemon --drift --drift-event-log" runs for change "obs" (one tick)
  Then the existing file is renamed to drift_events.<ISO-no-colons>.jsonl
  And a fresh ~/.flow-engineering/drift_events.jsonl is created (size 0)
  And the fresh file contains the 1 new JSONL line for the STALE finding
  And the rotated file is unchanged (append-only rotation policy)
```

**Edge cases / error modes**:
- `OSError` on `drift_events.jsonl` write (disk full, permission denied) is caught and logged to stderr; daemon continues (best-effort append).
- Rotation at exactly 10 MB boundary renames the file BEFORE writing the new line — so the new line goes to the fresh file, not the rotated one.
- `since_iso` filter on `iter_drift_events` uses lexicographic ISO comparison (the timestamps are `Z`-suffixed UTC; lex sort = chrono sort).
- `change` filter is exact match (NOT substring); a `change="obs-v1"` filter does NOT match `change="obs"`.

**Out-of-scope (deferred)**:
- `flow drift events` CLI command (read-side surface) — deferred per OQ-9; the JSONL is audit-only for v0.8.0; consumers read the file directly with `cat | jq` or use `flow metrics` to find `drift_event_log_*` counters.
- JSONL rotation threshold configurability (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var) — deferred per OQ-2; v0.8.0 ships 10 MB hardcoded, mirroring `metrics.jsonl`.
- `flow drift events --format=prometheus` or `--format=csv` — deferred; raw JSONL is the only output format.
- Cross-project federation (`flow drift events --project=<key>` filter) — deferred; v0.8.0 is single-project.

**Dependencies on prior REQs**:
- REQ-9 (`flow drift scan <change>`) — the primary consumer of `decision_drift.scan_change`.
- REQ-15 (`flow drift daemon --drift`) — the daemon seam that gets rewired to call `record_drift_event`.
- REQ-56 (this change) — `record_drift_event` consumes `DriftReport` with the new shape (`decision_id: int`, `unable_to_verify: bool`, `unable_reason: str | None`).

### REQ-59: Snapshot counter dual-name coexistence deprecation + write-back stderr WARN (W23 + S2)

#### REQ-59: Snapshot counter dual-name coexistence deprecation + write-back stderr WARN (W23 + S2)

**Statement**: The system MUST document the W23 dual-name coexistence (`snapshot_pruned_total` legacy vs `snapshot_prune_total` renamed, both emitted by `metrics.jsonl` consumers) in `CHANGELOG.md` v0.6.0 Notes section + recommend `--domain snapshot` filter for v1 consumers (per REQ-37); and MUST emit a single stderr WARN in `_write_back_findings` when `skipped_total >= 3` non-int `decision_id`s are encountered (S2), gated by the env var `FLOW_DRIFT_SKIP_WARN_THRESHOLD` (default `3`).

**Contract**:
- **Inputs**: legacy `snapshot_pruned_total` events already in `~/.flow-engineering/metrics.jsonl` (verified K=101+ at exploration); new `snapshot_prune_total` events emitted by v0.6.0+ (`record_snapshot_event()`); `_write_back_findings(report)` callers where some `Finding.decision_id` values are non-int (legacy `str` inputs that fail `_coerce_int()`).
- **Outputs**: CHANGELOG v0.6.0 Notes section adds 3-line entry documenting the W23 coexistence + recommending `--domain snapshot` filter. CHANGELOG v0.8.0 entry adds a 1-line entry for the S2 stderr WARN behavior change. stderr WARN from `_write_back_findings`: `WARN: drift write-back skipped <N> non-int decision_ids` (printed once per batch, NOT per row) when `skipped_total >= FLOW_DRIFT_SKIP_WARN_THRESHOLD` (default `3`).
- **Behavior**: W23 is **DOC ONLY** — no code change. The CHANGELOG v0.6.0 Notes section (entry to be added in batch B, not v0.6.0 release) explains that `snapshot_pruned_total` events predate the v0.6.0 wire-format rename to `snapshot_prune_total`, both names coexist in the user's `metrics.jsonl`, and downstream consumers should use REQ-37's `--domain snapshot` filter (which matches BOTH names by prefix) or rename legacy events with a one-time `sed`. S2 is a **CODE CHANGE** in `cli.py:_write_back_findings`: when the batch summary shows `skipped_total >= threshold` (default 3), print `WARN: drift write-back skipped <N> non-int decision_ids` to `sys.stderr` ONCE per batch (NOT per skipped row). The threshold is tunable via env var `FLOW_DRIFT_SKIP_WARN_THRESHOLD` (int parse; on parse error, fall back to default `3`). The stderr WARN is additive on top of the existing silent-skip behavior — it does NOT change what gets written or skipped.

**BDD Scenarios**: 2 scenarios (cross-cutting; not new feature files):

```gherkin
Scenario: REQ-59 — SnapshotMeta.size_bytes field is exposed via flow snapshot show command (REQ-58 cross-cut)
  Given a snapshot file snap_<ISO>-<6hex>.json.gz exists at ~/.flow-engineering/snapshots/
  When "flow snapshot show <snap_id>" is invoked
  Then the printed JSON envelope contains "size_bytes" (int, the on-disk byte size) at metadata.size_bytes
  And the printed JSON envelope does NOT contain "file_size_bytes" (the legacy design name)
  And the size_bytes value matches the on-disk byte size of the gzipped file

Scenario: REQ-59 — PruneResult.freed_bytes matches spec field name (REQ-58 cross-cut)
  Given 5 snapshots exist with 3 marked eligible for prune (not pinned)
  When "flow snapshot prune --dry-run" is invoked
  Then the printed JSON envelope contains "freed_bytes" (int, the cumulative bytes that WOULD be reclaimed)
  And the printed JSON envelope does NOT contain "freed_bytes_estimate" (the legacy spec/design name)
  And the freed_bytes value equals the sum of size_bytes for the 3 eligible snapshots

Scenario: REQ-59 — _write_back_findings emits stderr WARN when skipped_total >= threshold
  Given a DriftReport with 5 findings, 4 of which have non-int decision_ids (will skip)
  And FLOW_DRIFT_SKIP_WARN_THRESHOLD=3 (env var set; default)
  When "flow drift write-back" is invoked
  Then the JSON stdout result shows "success": 1, "skipped_total": 4
  And stderr contains exactly 1 WARN line "WARN: drift write-back skipped 4 non-int decision_ids" (once per batch)
  And the WARN line is NOT printed per skipped row (only the batch summary)
  And the daemon exits 0 (WARN does NOT change exit code)

Scenario: REQ-59 — _write_back_findings suppresses stderr WARN when skipped_total < threshold
  Given a DriftReport with 5 findings, 2 of which have non-int decision_ids (will skip)
  And FLOW_DRIFT_SKIP_WARN_THRESHOLD=3 (env var set; default)
  When "flow drift write-back" is invoked
  Then the JSON stdout result shows "success": 3, "skipped_total": 2
  And stderr contains 0 WARN lines (skipped_total < threshold; no noise for sporadic skips)
  And the daemon exits 0
```

**Edge cases / error modes**:
- `FLOW_DRIFT_SKIP_WARN_THRESHOLD` is a positive int; `0` means WARN every batch with `skipped_total > 0`; `-1` means WARN never.
- The WARN line is printed to `sys.stderr` via `print(..., file=sys.stderr)` (NOT the logging framework — matches the on-error output style of `flow` CLI).
- W23 deprecation: if a downstream consumer materializes (e.g., a dashboard scraping `metrics.jsonl`), the CHANGELOG entry directs them to `--domain snapshot` for prefix-based filtering OR to use `flow metrics --prometheus` (REQ-38) which emits Prometheus textfile format with the canonical name.

**Out-of-scope (deferred)**:
- Runtime migration on `flow metrics` startup that drops `snapshot_pruned_total` events with a stderr notice — rejected by Risk 2 (preserves audit trail; would lose data).
- One-time `metrics.jsonl` wipe on user consent — NUCLEAR option; rejected.
- Per-finding stderr WARN instead of per-batch — rejected by OQ-8 (per-row WARN would be noisy for sporadic skips; batch summary is the right cadence).

**Dependencies on prior REQs**:
- REQ-10 (`flow drift write-back`) — the CLI surface that calls `_write_back_findings` (REQ-11/REQ-14 also surface write-back paths).
- REQ-34 (`flow snapshot prune`) — the surface that emits `PruneResult` (REQ-58 cross-cut).
- REQ-37 (`flow metrics --domain=snapshot`) — the recommended filter for W23 coexistence consumers.
- REQ-56 (this change) — `decision_id: int` post-`__post_init__` coercion means `skipped_total` is now `0` for legacy numeric str inputs (they coerce cleanly); only truly non-numeric str inputs trigger the skip path. The WARN cadence is meaningful in this regime.

### Batch B acceptance criteria

- [ ] All 4 BDD scenarios pass (REQ-55 ×3, REQ-59 ×4 — but 2 REQ-59 cross-cut REQ-58 so net +2 REQ-59).
- [ ] `~/.flow-engineering/drift_events.jsonl` is created lazily on first non-still-valid finding (parent dirs auto-created).
- [ ] `drift_events.jsonl` rotation when file > 10 MB produces `drift_events.<ISO>.jsonl` sibling + fresh `drift_events.jsonl` (2 unit tests).
- [ ] Still-valid silence rule suppresses outer summary when `total == 0 and not unable_to_verify` (1 BDD + 2 unit tests).
- [ ] Still-valid-but-graph-unavailable emits the unable_to_verify summary line (1 BDD edge case).
- [ ] JSONL append is wrapped in `try/except OSError`; on failure, daemon continues (1 BDD + 1 unit test).
- [ ] `_write_back_findings` emits stderr WARN once per batch when `skipped_total >= FLOW_DRIFT_SKIP_WARN_THRESHOLD` (1 BDD + 2 unit tests).
- [ ] CHANGELOG v0.6.0 Notes section adds 3-line entry for W23 coexistence + REQ-37 filter recommendation (0 tests — runtime grep on CHANGELOG.md).
- [ ] All batch A tests + 947 existing tests pass; `ruff check` clean on changed files.
- [ ] Per-commit work-unit splits per `work-unit-commits` skill (4-6 commits each ≤400 LOC).
- [ ] Strict TDD evidence: every new public helper (`record_drift_event`, `iter_drift_events`) has RED → GREEN → REFACTOR history in commit log.

### Batch B files to touch

**Production (~250 LOC):**
- `src/flow_engineering/drift_event_log.py` (NEW): `record_drift_event(report, *, path=None)` + `iter_drift_events(*, since_iso, change)` + `DEFAULT_PATH` + `ROTATE_BYTES` constants + `_utc_iso()` + `_rotate_if_needed()` private helpers; ~+150 LOC
- `src/flow_engineering/observability.py` (MODIFY): +`record_drift_event()` thin wrapper + 2 catalog entries (`drift_event_log_total` counter + `drift_event_log_bytes` gauge); ~+15 LOC delta
- `src/flow_engineering/daemon.py` (MODIFY): wire `record_drift_event` into `handle_apply_progress_event`; W6 still-valid silence rule in outer summary; --drift-event-log flag handling; ~+30 / -10 LOC delta
- `src/flow_engineering/cli.py` (MODIFY): +`--drift-event-log[=<path>]` flag on `flow drift daemon`; +`--no-drift-event-log` opt-out; +S2 stderr WARN in `_write_back_findings`; ~+30 / -5 LOC delta
- `CHANGELOG.md` (MODIFY): +v0.6.0 Notes section entry for W23 coexistence; ~+20 LOC delta (NOTE: this lands in batch B per the W23 ownership; the v0.8.0 entry lands in batch D)

**Tests (~500 LOC):**
- `tests/unit/test_drift_event_log.py` (NEW): JSONL append per finding + rotation at 10 MB + schema validation + counter increment + `try/except OSError` coverage + idempotency on rotation + `iter_drift_events` filter combinations + since_iso + change; ~+180 LOC
- `tests/unit/test_daemon_drift_events.py` (MODIFY): +event-log integration + W6 still-valid silence + unable_to_verify edge case; ~+20 LOC delta
- `tests/unit/test_cli_watch_drift.py` (MODIFY): +CLI wiring + --drift-event-log flag + --no-drift-event-log opt-out; ~+10 LOC delta
- `tests/unit/test_cli_drift.py` (MODIFY): +S2 stderr WARN capture + threshold env var + per-batch cadence; ~+25 LOC delta
- `tests/unit/test_observability.py` (MODIFY): +2 catalog entry smoke tests; ~+10 LOC delta
- `tests/bdd/req15_drift_daemon.feature` (MODIFY): +2 new BDD scenarios (JSONL line present on detected drift + JSONL silent on still-valid); ~+80 LOC delta

---

## Batch C — REQ-57: 21 new BDD scenarios for REQ-10/12/13/14/16

### REQ-57: BDD coverage completion — 21 new scenarios across 6 feature files for REQ-10/11/12/13/14/16

#### REQ-57: BDD coverage completion — 21 new scenarios across 6 feature files for REQ-10/11/12/13/14/16

**Statement**: The system MUST provide 21 new BDD scenarios across 6 NEW `.feature` files in `tests/bdd/` that translate the existing unit-test contracts for REQ-10 (`flow drift <change>` CLI), REQ-11 (exit codes), REQ-12 (8 drift counters), REQ-13 (`update_observation_metadata`), REQ-14 (non-breaking behavior), and REQ-16 (SKILL.md grep check) into Gherkin phrasing — closing the W4 spec-vs-test gap (spec promised 39 BDD scenarios across 9 feature files for REQ-9..16 but `tests/bdd/` only shipped 18 across 3).

**Contract**:
- **Inputs**: existing unit tests in `tests/unit/test_cli_drift.py` (14 tests for REQ-10/11/14 CLI surface), `tests/unit/test_observability.py::TestRecordDriftSummary` (for REQ-12 counter catalog), `tests/unit/test_engram_io_code_refs.py::TestUpdateObservationMetadata` (6 tests for REQ-13), and the SKILL.md grep check from the `sdd-verify` Step 6a hook (for REQ-16).
- **Outputs**: 6 NEW `.feature` files with a combined 21 BDD scenarios + step glue in `tests/bdd/test_decision_reality_drift_steps.py` (or split per REQ into `test_req10_steps.py` etc., if the consolidated file exceeds 1 000 LOC):
  - `tests/bdd/req10_drift_cli.feature` — 9 scenarios for `flow drift <change>` CLI surface (`--json`, `--include-obsolete`, `--since`, `--write-back`, `--graph-json` flags).
  - `tests/bdd/req11_drift_exit.feature` — 3 scenarios for exit-code semantics (0 still-valid, 1 stale, 2 unable_to_verify, 3 usage error).
  - `tests/bdd/req12_drift_counters.feature` — 3 scenarios for the 8 `drift_*_total` counter emission via `record_drift_summary()`.
  - `tests/bdd/req13_drift_metadata.feature` — 3 scenarios for `update_observation_metadata()` helper (append + idempotent + structured error).
  - `tests/bdd/req14_drift_resilience.feature` — 4 scenarios for graph_unavailable + timeout + retry + per-row isolation behavior.
  - `tests/bdd/req16_skill_prose.feature` — 2 scenarios for the runtime SKILL.md grep check (sdd-verify Step 6a + drift detection hook presence).
- **Behavior**: Each BDD scenario uses business-domain Given/When/Then phrasing (NOT unit-test phrasing — e.g., `"Given a decision with bindings at file X line Y"`, `"When flow drift scans the change"`, `"Then the report shows STILL_VALID"` — NOT `"Given a fixture dict X"`). Step glue translates the business-domain language to the underlying pytest fixtures (no behavior change; pure scaffolding). The 21 scenarios are a 1:1 translation of the existing unit-test contracts in `test_cli_drift.py` + `test_observability.py::TestRecordDriftSummary` + `test_engram_io_code_refs.py::TestUpdateObservationMetadata` — they do NOT introduce new behavior.

**BDD Scenarios** (21 total — explicit per-REQ):

##### REQ-10 (9 scenarios, `req10_drift_cli.feature`)

```gherkin
Scenario: REQ-10 — flow drift scan emits human-readable text by default
  Given a change "obs" with 5 bindings (3 STILL_VALID + 2 STALE)
  When the user runs "flow drift scan obs" (no flags)
  Then stdout contains a "drift: obs 5 findings" summary line
  And stdout contains per-finding lines listing decision_id + class + binding_id
  And the output is human-readable text (NOT JSON)
  And the command exits 0

Scenario: REQ-10 — flow drift scan --json emits structured JSON output
  Given a change "obs" with 5 bindings (3 STILL_VALID + 2 STALE)
  When the user runs "flow drift scan obs --json"
  Then stdout is a JSON object with keys "change", "scanned_at", "unable_to_verify", "unable_reason", "findings"
  And the "findings" array has 5 entries, each with keys "decision_id", "binding_id", "finding_class", "message"
  And the JSON is parseable by json.loads
  And the command exits 0

Scenario: REQ-10 — flow drift scan --include-obsolete includes OBSOLETE-classified bindings
  Given a change "obs" with 5 bindings (3 STILL_VALID + 1 STALE + 1 OBSOLETE)
  When the user runs "flow drift scan obs --include-obsolete"
  Then stdout contains 5 findings (all classes including OBSOLETE)
  And the OBSOLETE finding is listed in the per-finding output
  And the command exits 0

Scenario: REQ-10 — flow drift scan (no flag) excludes OBSOLETE-classified bindings
  Given a change "obs" with 5 bindings (3 STILL_VALID + 1 STALE + 1 OBSOLETE)
  When the user runs "flow drift scan obs" (no flag)
  Then stdout contains 4 findings (OBSOLETE excluded by default)
  And the OBSOLETE finding is NOT listed
  And the command exits 0

Scenario: REQ-10 — flow drift scan --since=<iso> filters to bindings touched at or after that timestamp
  Given a change "obs" with 5 bindings touched at various timestamps (T1 < T2 < T3 < T4 < T5)
  When the user runs "flow drift scan obs --since=<T3_iso>"
  Then stdout contains only findings for bindings touched at T3, T4, T5 (3 findings)
  And findings for T1 and T2 are excluded
  And the command exits 0

Scenario: REQ-10 — flow drift scan --since=<iso> with --json emits JSON with timestamp-filtered findings
  Given a change "obs" with 5 bindings touched at various timestamps (T1 < T2 < T3 < T4 < T5)
  When the user runs "flow drift scan obs --since=<T3_iso> --json"
  Then stdout is a JSON object with a "findings" array of length 3 (T3, T4, T5 only)
  And the command exits 0

Scenario: REQ-10 — flow drift scan --write-back calls _write_back_findings and writes to live Engram
  Given a change "obs" with 3 STALE findings
  When the user runs "flow drift scan obs --write-back"
  Then the live Engram backend has been updated for the 3 STALE findings (update_observation_metadata called)
  And stdout contains "wrote: 3 findings" confirmation
  And the counter drift_write_back_total increments by 3
  And the command exits 0

Scenario: REQ-10 — flow drift scan --graph-json=<path> uses a custom graph.json instead of the default
  Given a custom graph_json file at /tmp/custom_graph.json with 3 nodes
  When the user runs "flow drift scan obs --graph-json=/tmp/custom_graph.json"
  Then the drift report is computed against the custom graph (3 nodes) not the default ~/.flow-engineering/graph.json
  And the command exits 0

Scenario: REQ-10 — flow drift scan with unknown change name emits usage error
  Given an unknown change name "non-existent-change"
  When the user runs "flow drift scan non-existent-change"
  Then stderr contains a JSON error "unknown change: non-existent-change"
  And the command exits 3 (usage error)
```

##### REQ-11 (3 scenarios, `req11_drift_exit.feature`)

```gherkin
Scenario: REQ-11 — flow drift scan exits 0 when all bindings are STILL_VALID
  Given a change "obs" with 3 bindings (all STILL_VALID)
  When the user runs "flow drift scan obs"
  Then stdout contains "drift: obs 0 stale findings" (or equivalent still-valid summary)
  And the command exits 0

Scenario: REQ-11 — flow drift scan exits 1 when at least one STALE finding is detected
  Given a change "obs" with 5 bindings (4 STILL_VALID + 1 STALE)
  When the user runs "flow drift scan obs"
  Then stdout contains the STALE finding
  And the command exits 1 (drift detected)

Scenario: REQ-11 — flow drift scan exits 2 when unable_to_verify=True (graph unavailable)
  Given a change "obs" with 3 bindings (all STILL_VALID per stubbed graph)
  And the graph_json file is missing (unable_to_verify=True, unable_reason="graph_json_missing")
  When the user runs "flow drift scan obs"
  Then stdout contains the unable_to_verify reason
  And the command exits 2 (unable_to_verify)
```

##### REQ-12 (3 scenarios, `req12_drift_counters.feature`)

```gherkin
Scenario: REQ-12 — record_drift_summary emits 8 drift counters after a scan_change invocation
  Given a DriftReport with 3 findings (1 STILL_VALID + 1 STALE + 1 MISSING)
  When record_drift_summary(report) is called
  Then ~/.flow-engineering/metrics.jsonl gains 1 event for drift_invoked_total{change=<change>}
  And the metrics.jsonl gains 1 event for drift_stale_total (1 STALE finding)
  And the metrics.jsonl gains 1 event for drift_missing_total (1 MISSING finding)
  And 6 other drift counters are emitted (drift_scanned_total, drift_orphaned_total, drift_unable_to_verify_total, drift_summary_emitted_total, drift_findings_total, drift_write_back_total) with values 1, 0, 0, 1, 3, 0 respectively
  And the total drift counter increment count equals 8

Scenario: REQ-12 — record_drift_summary is idempotent on multiple calls with the same report (no double-counting)
  Given a DriftReport with 3 findings
  When record_drift_summary(report) is called twice (same report)
  Then the metrics.jsonl shows 2 events for drift_invoked_total (1 per call; the helper increments per-call, not per-unique-report)

Scenario: REQ-12 — record_drift_summary emits drift_unable_to_verify_total when unable_to_verify=True
  Given a DriftReport with unable_to_verify=True, unable_reason="graph_json_missing"
  When record_drift_summary(report) is called
  Then the metrics.jsonl gains 1 event for drift_unable_to_verify_total{reason="graph_json_missing"}
  And the counter value is 1 (NOT 0; the unable_to_verify flag increments the counter)
```

##### REQ-13 (3 scenarios, `req13_drift_metadata.feature`)

```gherkin
Scenario: REQ-13 — update_observation_metadata appends drift metadata to an observation
  Given an observation with id=42 and content="<some content>"
  When update_observation_metadata(observation_id=42, metadata={"drift_status": "STALE", "scanned_at": "2026-06-27T12:00:00Z"}) is called
  Then the observation now has a "metadata" field with key "drift_status" == "STALE"
  And the observation now has a "metadata" field with key "scanned_at" == "2026-06-27T12:00:00Z"
  And the original "content" is unchanged
  And the operation succeeds (return value is truthy)

Scenario: REQ-13 — update_observation_metadata is idempotent when called twice with the same key (last-write-wins)
  Given an observation with id=42 and existing metadata.drift_status == "STALE"
  When update_observation_metadata(observation_id=42, metadata={"drift_status": "MISSING"}) is called
  Then the observation's metadata.drift_status == "MISSING" (overwritten; NOT appended as a list)
  And the original "STALE" entry is gone (idempotent key overwrite)

Scenario: REQ-13 — update_observation_metadata with unknown observation_id raises structured error
  Given an unknown observation id=99999
  When update_observation_metadata(observation_id=99999, metadata={"drift_status": "STALE"}) is called
  Then ObservationNotFoundError is raised with id=99999 in the message
  And no observation is created (the helper does NOT auto-create)
```

##### REQ-14 (4 scenarios, `req14_drift_resilience.feature`)

```gherkin
Scenario: REQ-14 — flow drift scan handles per-row exceptions without crashing the entire batch
  Given a change "obs" with 5 bindings where 1 binding's file has been deleted mid-scan (IOError)
  When the user runs "flow drift scan obs"
  Then the IOError is caught per-row and the other 4 bindings are classified normally
  And stdout contains 4 findings (the failed binding is logged to stderr but does not abort)
  And the command exits 0 (graceful degradation)
  And the counter drift_per_row_failure_total increments by 1

Scenario: REQ-14 — flow drift scan is read-only by default (no writes to live Engram)
  Given a change "obs" with 3 STALE findings
  When the user runs "flow drift scan obs" (no --write-back flag)
  Then no update_observation_metadata calls are made to the live Engram
  And the counter drift_write_back_total is NOT incremented
  And the command exits 1 (drift detected, but read-only)

Scenario: REQ-14 — flow drift scan with --write-back failures does not throw — partial success reported
  Given a change "obs" with 3 STALE findings
  And 1 of the 3 observations has a read-only Engram row (write fails with PermissionError)
  When the user runs "flow drift scan obs --write-back"
  Then the live Engram has been updated for the 2 successful writes
  And stdout contains "wrote: 2, failed: 1" partial-success summary
  And the command exits 0 (partial success is still success)

Scenario: REQ-14 — flow drift scan with graph_unavailable exits 2 with helpful error message
  Given a change "obs" with 3 bindings
  And the graph_json file is missing (graph_unavailable=True)
  When the user runs "flow drift scan obs"
  Then stdout contains "unable_to_verify: graph_json_missing" message
  And stderr contains "hint: provide --graph-json=<path>" guidance
  And the command exits 2
```

##### REQ-16 (2 scenarios, `req16_skill_prose.feature`)

```gherkin
Scenario: REQ-16 — sdd-verify Step 6a asserts the drift detection hook is present in SKILL.md
  Given the file ~/.config/opencode/skills/sdd-verify/SKILL.md exists
  When sdd-verify runs Step 6a (the drift detection hook grep)
  Then the grep matches a line containing "drift" in the SKILL.md file
  And the matched line is at the expected section anchor (verify Phase 6)
  And sdd-verify exits 0

Scenario: REQ-16 — the drift detection hook in sdd-verify SKILL.md references the decision-reality-drift spec
  Given the file ~/.config/opencode/skills/sdd-verify/SKILL.md exists
  When sdd-verify runs Step 6a (the drift detection hook grep)
  Then the grep matches a line referencing REQ-9 (flow drift scan) OR openspec/changes/archive/2026-06-26-decision-reality-drift/
  And the matched line is non-empty and well-formed (not a stub)
  And sdd-verify exits 0
```

**Edge cases / error modes**:
- A BDD scenario that asserts byte-exact JSON shape is fragile to whitespace; scenarios MUST use `json.loads(stdout)` + dict-shape assertions, NOT substring matches.
- The `since_iso` timestamp filter depends on the implementation emitting the same ISO 8601 UTC format; both spec and impl use the `_now_iso()` helper (mirrors `cli.py:1632`).
- The `--write-back` path may fail for some rows (PermissionError on read-only rows); the helper MUST report partial success and NOT raise.
- Step glue file may exceed 1 000 LOC; per OQ resolution, split per REQ (`test_req10_steps.py`, `test_req11_steps.py`, etc.) if it exceeds the threshold.

**Out-of-scope (deferred)**:
- BDD scenarios for REQ-9 (drift detection core classification logic) — already covered by 14 scenarios in `req9_drift_detection.feature` (current state).
- BDD scenarios for REQ-15 (daemon seam) — already covered by 3 scenarios in `req15_drift_daemon.feature` (extended in batch B with 2 new JSONL scenarios).
- Per-finding classification refactor (`classify_binding` to handle graph_unavailable at the finding level) — deferred; current is report-level flag.

**Dependencies on prior REQs**:
- REQ-9..16 (`decision-reality-drift` archive) — the BDD scenarios translate the unit-test contracts for these REQs.
- REQ-56 (this change) — the dataclass shape migration is exercised by the 21 new BDD scenarios (e.g., REQ-10 scenario 2 asserts `decision_id` is `int` post-migration).

### Batch C acceptance criteria

- [ ] All 21 new BDD scenarios pass (`uv run pytest tests/bdd/req{10,11,12,13,14,16}_*.feature -v` shows 0 failures).
- [ ] Each of the 21 new BDD scenarios uses business-domain Given/When/Then phrasing (sdd-verify Step 6b spot-checks 3 random scenarios for business-domain phrasing — NOT unit-test phrasing).
- [ ] Step glue module is split per REQ if it exceeds 1 000 LOC (Risk 5 mitigation).
- [ ] All batch A + batch B tests + 947 existing tests pass; `ruff check` clean on changed files.
- [ ] Per-commit work-unit splits per `work-unit-commits` skill (4-6 commits each ≤400 LOC).
- [ ] Strict TDD evidence: BDD scenarios are written BEFORE the step glue (RED), then step glue makes them pass (GREEN), then refactor for reuse (REFACTOR).

### Batch C files to touch

**Production (~100 LOC — step glue only):**
- `tests/bdd/test_decision_reality_drift_steps.py` (MODIFY): +step glue for 6 new feature files; or SPLIT into `test_req10_steps.py`, `test_req11_steps.py`, `test_req12_steps.py`, `test_req13_steps.py`, `test_req14_steps.py`, `test_req16_steps.py`; ~+400 LOC delta total (split if file exceeds 1 000 LOC)

**Tests (~800 LOC):**
- `tests/bdd/req10_drift_cli.feature` (NEW): 9 BDD scenarios for `flow drift <change>` CLI surface; ~+250 LOC
- `tests/bdd/req11_drift_exit.feature` (NEW): 3 BDD scenarios for exit-code semantics (0 still-valid, 1 stale, 2 unable_to_verify); ~+90 LOC
- `tests/bdd/req12_drift_counters.feature` (NEW): 3 BDD scenarios for 8 drift counters via `record_drift_summary()`; ~+90 LOC
- `tests/bdd/req13_drift_metadata.feature` (NEW): 3 BDD scenarios for `update_observation_metadata()`; ~+90 LOC
- `tests/bdd/req14_drift_resilience.feature` (NEW): 4 BDD scenarios for graph_unavailable + timeout + retry + per-row isolation; ~+120 LOC
- `tests/bdd/req16_skill_prose.feature` (NEW): 2 BDD scenarios for SKILL.md grep check; ~+60 LOC

---

## Batch D — CHANGELOG v0.8.0 + 6 SKILL.md hook + pyproject bump + v0.6.0 W23 Notes entry

### Batch D — CHANGELOG v0.8.0 + 6 SKILL.md hook + pyproject bump + v0.6.0 W23 Notes entry

**Statement**: The system MUST ship a v0.8.0 CHANGELOG entry listing all 5 REQs + a `BREAKING:` section documenting the W8 dataclass shape migration + v0.7.0 → v0.8.0 `pyproject.toml` version bump + 6 SKILL.md files (`sdd-{propose,design,tasks,apply,verify,archive}`) updated with a drift-hardening hook prose (mirror observability SKILL.md hook from change #6) + the W23 CHANGELOG Notes section entry for v0.6.0 (per REQ-59 W23 ownership).

**Contract**:
- **Inputs**: existing v0.7.0 CHANGELOG entry (`CHANGELOG.md:116-162` per exploration); existing `pyproject.toml` version line 3; existing 6 `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` files (the runtime-only hooks).
- **Outputs**: `CHANGELOG.md` v0.8.0 entry (~40 LOC) listing all 5 REQs with one-line summaries each + a `BREAKING:` section documenting the W8 dataclass shape change with migration steps + a `W23:` subsection in v0.6.0 Notes section (carried over from batch B) + `pyproject.toml` version bump `0.7.0` → `0.8.0` + 6 SKILL.md files updated with a drift-hardening hook prose (~80 LOC across 6 files; ~13 LOC per file).
- **Behavior**: `pyproject.toml` `version = "0.8.0"` (REQ-56 breaking change mandates minor bump per SemVer); `CHANGELOG.md` v0.8.0 entry is added above v0.7.0 entry (newest first) with sections for `Added`, `Changed`, `Fixed`, `Deprecated`, `Removed`, `Security`, and `BREAKING:`. The `BREAKING:` section explicitly documents: (a) `Finding.decision_id: str → int` — legacy numeric str inputs coerce with `DeprecationWarning` for v0.8.0, hard break in v1.0; (b) `DriftReport.scanned_at: float → str` — legacy float epoch inputs coerce via `from_scanned()` for v0.8.0, hard break in v1.0; (c) `DriftReport.graph_unavailable` → `DriftReport.unable_to_verify + unable_reason` — `@property graph_unavailable` alias retained for 1 release with `DeprecationWarning`; (d) `classify_binding(ref, graph_nodes, current_id_map)` 3-arg → `classify_binding(ref, graph_nodes)` 2-arg — clean break. The 6 SKILL.md hook files each gain a section near the end (mirroring the observability hook pattern from change #6) that explains when drift detection should run and what to do if W4/W5/W6/W8 carry-forwards are surfaced.

**Batch D acceptance criteria**:

- [ ] `pyproject.toml` `version = "0.8.0"` (1 line change).
- [ ] `CHANGELOG.md` v0.8.0 entry exists with all 5 REQs listed + `BREAKING:` section with 4 migration steps.
- [ ] `CHANGELOG.md` v0.6.0 Notes section has a 3-line entry documenting W23 coexistence (carried over from batch B).
- [ ] All 6 SKILL.md files have the drift-hardening hook prose section (~13 LOC each).
- [ ] All batch A + B + C tests + 947 existing tests pass; `ruff check` clean on changed files.
- [ ] Per-commit work-unit splits per `work-unit-commits` skill (1 commit per SKILL.md file + 1 commit for CHANGELOG + 1 commit for pyproject bump = 8 commits).

### Batch D files to touch

**Production (~300 LOC — docs + meta):**
- `CHANGELOG.md` (MODIFY): +v0.8.0 entry (~40 LOC, Added + Changed + Fixed + BREAKING sections) + v0.6.0 Notes section entry for W23 (3 LOC; carried over from batch B); ~+43 LOC delta
- `pyproject.toml` (MODIFY): `version = "0.8.0"` (REQ-56 breaking change mandates minor bump); ~+1 / -1 LOC delta
- `~/.config/opencode/skills/sdd-propose/SKILL.md` (MODIFY): +drift-hardening hook prose; ~+13 LOC delta
- `~/.config/opencode/skills/sdd-design/SKILL.md` (MODIFY): +drift-hardening hook prose; ~+13 LOC delta
- `~/.config/opencode/skills/sdd-tasks/SKILL.md` (MODIFY): +drift-hardening hook prose; ~+13 LOC delta
- `~/.config/opencode/skills/sdd-apply/SKILL.md` (MODIFY): +drift-hardening hook prose; ~+13 LOC delta
- `~/.config/opencode/skills/sdd-verify/SKILL.md` (MODIFY): +drift-hardening hook prose + BDD Step 6b cluster-count assertion; ~+20 LOC delta
- `~/.config/opencode/skills/sdd-archive/SKILL.md` (MODIFY): +drift-hardening hook prose; ~+13 LOC delta

**Tests (~400 LOC — BDD Step 6b + CHANGELOG grep + pyproject version check):**
- `tests/unit/test_changelog_drift_hardening.py` (NEW): CHANGELOG v0.8.0 entry exists + BREAKING section has 4 steps + v0.6.0 Notes has W23 entry; ~+100 LOC
- `tests/unit/test_pyproject_version.py` (NEW or MODIFY): `pyproject.toml` version == "0.8.0"; ~+20 LOC
- `tests/unit/test_skill_md_drift_hooks.py` (NEW): all 6 SKILL.md files have the drift-hardening hook prose section; ~+120 LOC
- `tests/bdd/test_drift_hardening_steps.py` (NEW): BDD Step 6b cluster-count assertion — verifies 21 new scenarios in the 6 new feature files; ~+160 LOC

---

## Out of Scope (deferred)

The following are explicitly out of scope for change #8 and belong to named follow-ups (mirrors the `vector-semantic-search`, `cross-project-federation`, and `observability` deferral patterns):

- **`flow drift events` CLI command** (read-side surface for `drift_events.jsonl` — mirror `flow metrics summary`) — deferred per OQ-9; the JSONL is audit-only for v0.8.0; consumers read the file directly with `cat | jq` or use `flow metrics --domain drift` to find `drift_event_log_*` counters. Lands in a v1.0 / "drift-events-dashboard" change.
- **JSONL rotation policy configurability** (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES`, `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` to gzip-and-rotate on a threshold) — deferred per OQ-2; v0.8.0 ships 10 MB hardcoded, mirroring `metrics.jsonl`. REQ-44 metrics rotation is also deferred to v1.1; both deferred items land together in a future "metrics+drift-jsonl-rotation" change.
- **Cross-project federation for drift events** (`flow drift events --project=<key>` filter; requires modifying every record helper signature to inject a `project` field into events) — deferred to a `federated-drift-events` follow-up change.
- **OpenTelemetry push for drift events** (OTLP exporter for `drift_events.jsonl` events) — deferred; Prometheus textfile format from REQ-38 already covers the v1 use case.
- **Dataclass migration tooling** (`FindingLegacy` shim; migration script `flow migrate decision-drift v0.7.0-to-v0.8.0`) — deferred; the 1-release `DeprecationWarning` aliases are the migration path. Hard break in v1.0 with a migration guide in the CHANGELOG.
- **`flow drift events --format=prometheus` / `--format=csv`** — deferred to v1.0; raw JSONL is the only output format for v0.8.0.
- **Per-finding `graph_unavailable` classification** (refactor `classify_binding` to handle graph_unavailable at the finding level — currently a report-level flag) — deferred; v0.8.0 keeps the report-level flag.
- **`flow drift daemon --drift-event-log` per-finding config** (e.g., `--event-class-filter=STALE,MISSING` to persist only specific classes) — deferred; v0.8.0 persists all non-still-valid findings by default.
- **Auto-daily snapshot trigger** (`trigger="auto"` scheduled snapshots) — already deferred in `graph-snapshots` archive; unchanged.
- **Snapshot export/import for sharing** (`flow snapshot export <id>` / `flow snapshot import <id>`) — already deferred in `graph-snapshots` archive; unchanged.
- **`flow metrics` runtime migration for W23** (drop `snapshot_pruned_total` events on startup with stderr notice) — rejected by Risk 2 (preserves audit trail; would lose data). CHANGELOG-only documentation is the chosen path.
- **Async drift-on-save** (auto-run `flow drift scan` on `mem_save` for changed observations) — deferred; v0.8.0 keeps the daemon tick + on-demand `flow drift scan` patterns.
- **Real-time drift dashboard** (`flow drift tail --follow` to follow drift events like `tail -f`) — deferred to v2; the JSONL sink is append-only and a tail would be straightforward but is not on the v0.8.0 critical path.

---

## BDD Feature File Plan

| Feature file | Status | Covers | Scenarios |
|---|---|---|---|
| `tests/bdd/req10_drift_cli.feature` | NEW | REQ-10 + REQ-57 | 9 |
| `tests/bdd/req11_drift_exit.feature` | NEW | REQ-11 + REQ-57 | 3 |
| `tests/bdd/req12_drift_counters.feature` | NEW | REQ-12 + REQ-57 | 3 |
| `tests/bdd/req13_drift_metadata.feature` | NEW | REQ-13 + REQ-57 | 3 |
| `tests/bdd/req14_drift_resilience.feature` | NEW | REQ-14 + REQ-57 | 4 |
| `tests/bdd/req16_skill_prose.feature` | NEW | REQ-16 + REQ-57 | 2 |
| `tests/bdd/req15_drift_daemon.feature` | MODIFY | REQ-15 + REQ-55 + REQ-56 W6 | +2 (extends existing 3) |
| **Total BDD scenarios** | | | **21 new + 2 extended = 23 scenarios** |

Step definitions land in `tests/bdd/test_decision_reality_drift_steps.py` (MODIFY or SPLIT into per-REQ files). The per-REQ scenario counts match the verify-report #135 forecast: REQ-10: 9, REQ-11: 3 (folded into the 9 above as a separate file for clarity), REQ-12: 3, REQ-13: 3, REQ-14: 4, REQ-16: 2 — totaling 24 if REQ-11 is not folded into REQ-10's 9. The 21 number is achieved by dropping 3 of the REQ-10/REQ-11 scenarios that are redundant with existing unit tests (the "human-readable text default" + "JSON output" + "OBSOLETE include" trio is collapsed to 2). Edge cases that do NOT fit the BDD scope are covered by unit tests:

- REQ-55: JSONL append per finding + 10 MB rotation + try/except OSError — `tests/unit/test_drift_event_log.py`
- REQ-55: still-valid silence rule — `tests/unit/test_daemon_drift_events.py::TestStillValidSilence`
- REQ-56: dataclass shape round-trip + `DeprecationWarning` capture + 2-arg classify_binding + 3-arg TypeError — `tests/unit/test_decision_drift.py`
- REQ-58: spec/design grep for `size_bytes` + `pinned` + `freed_bytes` — `tests/unit/test_skill_md_drift_hooks.py` (batch D)
- REQ-59: S2 stderr WARN capture + threshold env var + per-batch cadence — `tests/unit/test_cli_drift.py::TestWriteBackSkipWarn`

This mirrors the `graph-snapshots` split where the sha256-tamper detection (REQ-30 edge case) and `--keep-last=0` two-flag safety gate (REQ-34) stayed at the unit-test layer.

---

## Traceability matrix

| REQ | Source | Notes |
|-----|--------|-------|
| REQ-55 | proposal #223 + explore #222 | `drift_events.jsonl` append-only JSONL writer + W6 still-valid silence (W5 + W6 from change #2) |
| REQ-56 | proposal #223 + explore #222 | `DecisionDrift` dataclass shape sync: `decision_id: int`, `scanned_at: str ISO`, `unable_to_verify + unable_reason`, 2-arg `classify_binding`; BREAKING with 1-release `DeprecationWarning` aliases (W8 from change #2) |
| REQ-57 | proposal #223 + explore #222 | 21 new BDD scenarios across 6 NEW feature files for REQ-10/11/12/13/14/16 (W4 from change #2 — headline value-add) |
| REQ-58 | proposal #223 + explore #222 | Snapshot spec/design field reconciliation: `SnapshotMeta.size_bytes` (rename from `file_size_bytes`), `pinned: bool` retention-pin doc, `PruneResult.freed_bytes` (rename from `freed_bytes_estimate`); 0 production code change (W25 + W26 from change #5) |
| REQ-59 | proposal #223 + explore #222 | Snapshot counter dual-name W23 coexistence deprecation note (CHANGELOG v0.6.0 Notes section) + S2 stderr WARN in `_write_back_findings` with `FLOW_DRIFT_SKIP_WARN_THRESHOLD` env var (W23 + S2 — bundled in batch B per the cluster identity) |

Plus the v0.7.0 → v0.8.0 version bump (batch D) bundled with REQ-56 (same module). Plus the 6 SKILL.md hook updates (batch D) bundled with the cluster identity.

---

## Open Questions (carry-forward to sdd-design)

The 10 questions below MUST be resolved in the design phase before `sdd-tasks` locks the implementation contract:

1. **REQ-56 backward compat (W8 / OQ-1)** — hard migration (bump v0.7.0 → v0.8.0), soft migration (1-release `DeprecationWarning` aliases), or dual dataclasses (`Finding` + `FindingLegacy`)? **Recommend hard migration** with 1-release aliases (the `@property graph_unavailable` + `__post_init__` coercion). Decision needed: explicit confirmation that `pip search flow-engineering` shows no unrelated packages; `pyproject.toml` is the only install entry point.
2. **REQ-55 JSONL rotation threshold (W5 / OQ-2)** — 10 MB (mirror `metrics.jsonl` policy), 5 MB (more aggressive), or 50 MB (less I/O churn)? **Recommend 10 MB** — same precedent. Decision needed: confirm rotation is automatic on append (no separate cron / hook) and that rotated files use the `drift_events.<ISO-no-colons>.jsonl` naming pattern (sortable lexicographically by rotation time).
3. **REQ-55 still-valid silence scope (W6 / OQ-3)** — silence only when `total == 0 and not unable_to_verify` (the explore recommendation), OR also silence when `total == 0 and unable_to_verify` (broader), OR never silence (always emit summary for audit)? **Recommend the first** — still-valid-but-graph-unavailable is informative (the user should know the graph is unreachable). Decision needed: confirm the spec phrase "no event-log line on still-valid" means "no stdout line" (NOT "no JSONL line").
4. **REQ-56 migration timeline (W8 / OQ-4)** — ship REQ-56 in the same single PR as REQ-55/57/58/59 (cluster change), OR split REQ-56 into a separate v0.8.0-migration change (just the dataclass shape + CHANGELOG)? **Recommend same PR** — the v0.8.0 version bump is a single event; splitting forces two v0.8.0 entries or a v0.7.1 + v0.8.0 sequence. Decision needed: confirm the cluster identity is worth the single-PR review effort.
5. **REQ-57 BDD scenario source (W4 / OQ-5)** — write the 21 scenarios fresh (full business-domain Given/When/Then), OR extract from existing unit-test contracts (`test_cli_drift.py`, `test_observability.py`, `test_engram_io_code_refs.py`)? **Recommend translate** — the unit tests are the source of truth; BDD scenarios mirror their contracts in Gherkin phrasing. Decision needed: confirm that the existing unit tests are sufficient (i.e., no missing behavior tests in the unit-test suite that BDD scenarios should surface for the first time).
6. **REQ-58 spec reconciliation scope (W25/W26 / OQ-6)** — update the archived change #5 `spec.md` + `design.md` ONLY (single source of truth), OR also update the original change #5 spec.md in-place (live file)? **Recommend archived only** — per SDD governance, archived specs are the source of truth and live changes are append-only (cannot modify a shipped change). Decision needed: confirm the archive-folder is the long-term edit target.
7. **REQ-59 W23 deprecation note placement (OQ-7)** — CHANGELOG v0.6.0 Notes section ONLY, OR also runtime WARN log when reading old metric names (e.g., `flow metrics` emits "10 legacy `snapshot_pruned_total` events dropped")? **Recommend CHANGELOG only** — runtime WARN would be noisy on every `flow metrics` invocation; preserve audit trail; no consumer exists yet. Decision needed: confirm the deprecation is informational only (no consumer migration tooling needed).
8. **REQ-59 S2 stderr WARN cadence (OQ-8)** — once per batch (cumulative `skipped_total > 0` triggers one WARN), OR once per skipped item (1+ WARN per row), OR only when `skipped_total >= 5` (avoid noise for sporadic skips)? **Recommend once per batch with a threshold** (`skipped_total >= 3` to start; tunable via env var `FLOW_DRIFT_SKIP_WARN_THRESHOLD`). Decision needed: confirm the threshold matches the spec phrasing "user should notice skipped writebacks".
9. **REQ-55 read-side surface (OQ-9)** — ship `flow drift events` CLI (mirror `flow metrics summary`) in the same PR, OR defer to a follow-up change? **Recommend defer** — REQ-55 spec only requires the append side; the read side is a UI convenience that observability's `flow metrics summary` already provides indirectly. Decision needed: confirm the JSONL is "audit-only" for v0.8.0 and the read side lands in a v1.0 / "drift-events-dashboard" change.
10. **REQ-56 `classify_binding` arg-list compat (OQ-10)** — 2-arg with `current_id_map` derived inside (clean break), OR 2-arg with optional `current_id_map: dict | None = None` parameter for 1-release compat (soft)? **Recommend clean break** — `current_id_map` was an implementation detail; no documented external caller. Decision needed: grep `tests/` + `openspec/` for any caller passing 3 args and confirm the migration is mechanical.

---

## Risks (carry-forward from proposal §6)

The 10 risks below were raised in the proposal. Those that remain unmitigated after the spec phase are flagged here; mitigations are noted inline:

| # | Risk | Likelihood | Status after spec phase |
|---|---|---|---|
| 1 | REQ-56 (W8) public API break: `decision_id: str → int`, `scanned_at: float → str`, `graph_unavailable → unable_to_verify`, `classify_binding` 3 → 2 args — third-party consumers (if any) break at runtime / mypy strict | MED | MITIGATED — Hard migration is acceptable (no third-party consumers per Engram #92 `sdd-init`); 1-release `DeprecationWarning` aliases for `graph_unavailable` and `Finding.__post_init__` str coercion; v0.7.0 → v0.8.0 version bump; CHANGELOG `BREAKING:` section with migration steps |
| 2 | REQ-55 (W5) JSONL writer unbounded growth: `drift_events.jsonl` can exceed 100 MB/year on a long-running watcher | MED | MITIGATED — Mirror `metrics.jsonl` rotation policy — rotate when file > 10 MB to `drift_events.<timestamp>.jsonl` + start fresh (sub-feature of REQ-55, no separate REQ). REQ-44 metrics rotation is deferred to v1.1; both deferred items land together in a future "metrics+drift-jsonl-rotation" change |
| 3 | REQ-59 (W23) wire-format compatibility: legacy `snapshot_pruned_total` events (K=101+) coexist with renamed `snapshot_prune_total` (K=70+) in `~/.flow-engineering/metrics.jsonl`; sum-based queries double-count | LOW | MITIGATED — PREFERRED: CHANGELOG v0.6.0 Notes section documents coexistence + recommends REQ-37 `--domain snapshot` consumers use the catalog filter; no code change beyond a 3-line CHANGELOG entry. If a downstream consumer materializes, revisit as REQ-59 follow-up |
| 4 | REQ-57 (W4) BDD coverage scope: 21 scenarios risk becoming tautological (just `@scenario`-bound unit tests without business-domain phrasing) | MED | MITIGATED — Quality gate: each BDD scenario MUST use business-domain Given/When/Then (e.g., "Given a decision with bindings at file X line Y", "When flow drift scans the change", "Then the report shows STILL_VALID") NOT unit-test phrasing ("Given a fixture dict X"); sdd-verify Step 6b asserts the 21-scenario count + spot-checks 3 random scenarios for business-domain phrasing |
| 5 | Single PR realistic LOC ~9 700 (close to observability's ~10 910 chained-PR threshold); reviewer fatigue on a 4-batch single-PR | MED | MITIGATED — Per-commit work-unit splits per `work-unit-commits` skill (4-6 commits each ≤400 LOC); 4 batches in PR description; reviewer reads commit-by-commit not as one blob |
| 6 | Batch C BDD coverage (21 scenarios) is the bottleneck at ~60 min; if rushed, quality degrades (tautological scenarios) | MED | MITIGATED — Split Batch C into Batch C1 (req10+req12+req16 = 14 scenarios, simpler) + Batch C2 (req11+req13+req14 = 7 scenarios, more complex resilience tests); final tests in Batch D |
| 7 | Step glue module size: `test_decision_reality_drift_steps.py` +400 LOC for the 6 new feature files pushes the file past 1 000 LOC (review-awkward) | LOW | MITIGATED — Split per REQ into `test_req10_steps.py`, `test_req12_steps.py`, etc. — mirrors the req28..34 split that `test_graph_snapshots_steps.py` uses |
| 8 | `flow` script has potential (unconfirmed) third-party consumers; REQ-56 break could surprise downstream | LOW | MITIGATED — Pre-flight: `pip search flow-engineering` to confirm unrelated packages; verify `pyproject.toml` is the only install entry point (per Engram #92 `sdd-init`, project is unpublished); if a consumer surfaces, pivot to soft migration (Risk 1 mitigation b) |
| 9 | Drift detection hook (REQ-9..16) integration with the new JSONL sink: if `record_drift_event` raises (e.g., disk full), daemon crashes mid-tick | LOW | MITIGATED — Wrap the append in `try/except OSError`; on failure, log to stderr and continue (matches `observability.increment()` policy — best-effort, never crashes the caller); BDD scenario covers disk-full path |
| 10 | Snapshot field-name reconciliation (REQ-58 W25/W26) is spec/design-only, but downstream BDD consumers may have hardcoded the old `file_size_bytes` / `freed_bytes_estimate` names | LOW | MITIGATED — REQ-34 BDD scenarios don't assert exact field name (per explore #222); verify before merge via grep on `tests/bdd/req28..34_*.feature` for the legacy names; if found, rename in the same Batch A commit |

---

## File plan (per-file LOC forecast)

### Production files

| File | Change | LOC delta | Reason |
|------|--------|-----------|--------|
| `src/flow_engineering/drift_event_log.py` | NEW | +150 | REQ-55 JSONL writer + rotation + `record_drift_event` + `iter_drift_events` |
| `src/flow_engineering/decision_drift.py` | MODIFY | +60 / -20 net | REQ-56 dataclass shape sync |
| `src/flow_engineering/daemon.py` | MODIFY | +30 / -10 net | REQ-55 wire `record_drift_event` + W6 still-valid silence |
| `src/flow_engineering/cli.py` | MODIFY | +45 / -10 net | REQ-55 `--drift-event-log` flag + REQ-59 S2 stderr WARN + REQ-56 cast site updates |
| `src/flow_engineering/observability.py` | MODIFY | +15 | REQ-55 `record_drift_event` helper + 2 catalog entries |
| `src/flow_engineering/snapshot_manager.py` | MODIFY | 0 | REQ-58 is spec/design-only; no code change |
| `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` | MODIFY | +5 / -5 net | REQ-56 reconcile Finding/DriftReport shape |
| `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md` | MODIFY | +10 / -8 net | REQ-56 reconcile dataclass type signatures |
| `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` | MODIFY | +3 / -3 net | REQ-58 W26 `freed_bytes` field reconciliation |
| `openspec/changes/archive/2026-06-27-graph-snapshots/design.md` | MODIFY | +5 / -5 net | REQ-58 W25 `size_bytes` + `pinned` field reconciliation |
| `CHANGELOG.md` | MODIFY | +43 | v0.8.0 entry (40 LOC) + v0.6.0 Notes W23 entry (3 LOC; from batch B) |
| `pyproject.toml` | MODIFY | +1 / -1 net | `version = "0.8.0"` |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | MODIFY | ~80 LOC total runtime-only | drift-hardening hook prose (~13 LOC per file) |
| **Production total** | | **~300 prod net** | |

### Test files

| File | Change | LOC delta | Reason |
|------|--------|-----------|--------|
| `tests/unit/test_drift_event_log.py` | NEW | +180 | REQ-55 JSONL writer unit tests (rotation, append, schema, counter increment) |
| `tests/unit/test_decision_drift.py` | MODIFY | +30 | REQ-56 dataclass shape round-trip + backward-compat shim tests |
| `tests/unit/test_daemon_drift_events.py` | MODIFY | +20 | REQ-55 event-log integration + W6 still-valid silence |
| `tests/unit/test_cli_watch_drift.py` | MODIFY | +10 | REQ-55 CLI wiring + `--drift-event-log` flag |
| `tests/unit/test_cli_drift.py` | MODIFY | +25 | REQ-59 S2 stderr WARN capture + REQ-56 cast site updates |
| `tests/unit/test_observability.py` | MODIFY | +10 | REQ-55 catalog entry smoke tests |
| `tests/unit/test_changelog_drift_hardening.py` | NEW | +100 | CHANGELOG v0.8.0 entry + BREAKING section + v0.6.0 Notes W23 entry |
| `tests/unit/test_pyproject_version.py` | NEW | +20 | `pyproject.toml` version check |
| `tests/unit/test_skill_md_drift_hooks.py` | NEW | +120 | 6 SKILL.md files have drift-hardening hook prose |
| `tests/bdd/req10_drift_cli.feature` | NEW | +250 | REQ-57 9 BDD scenarios |
| `tests/bdd/req11_drift_exit.feature` | NEW | +90 | REQ-57 3 BDD scenarios |
| `tests/bdd/req12_drift_counters.feature` | NEW | +90 | REQ-57 3 BDD scenarios |
| `tests/bdd/req13_drift_metadata.feature` | NEW | +90 | REQ-57 3 BDD scenarios |
| `tests/bdd/req14_drift_resilience.feature` | NEW | +120 | REQ-57 4 BDD scenarios |
| `tests/bdd/req16_skill_prose.feature` | NEW | +60 | REQ-57 2 BDD scenarios |
| `tests/bdd/test_decision_reality_drift_steps.py` | MODIFY or split | +400 | REQ-57 step glue for 6 new feature files |
| `tests/bdd/test_drift_hardening_steps.py` | NEW | +160 | BDD Step 6b cluster-count assertion |
| `tests/bdd/req15_drift_daemon.feature` | MODIFY | +80 | REQ-55 extend with 2 JSONL event-log scenarios |
| **Test total** | | **~1 855 test net** | |

### LOC forecast (with ×6 strict-TDD multiplier per `decision-code-linking` archive-report #119 S3)

| Bucket | Net LOC | ×6 TDD | Notes |
|--------|---------|--------|-------|
| Production code | 300 | 300 × 6 = 1 800 | Realistic; BDD scaffolding is in test bucket |
| Test code | 1 855 | (already in bucket) | Includes BDD scenarios + step glue |
| Archived spec/design | 18 | 18 | Edits only, no new test |
| **Grand total** | **~2 173** | **~9 700** | Includes 6 NEW BDD feature files (heavy on Gherkin scaffolding) |

---

## Cross-impact

| Queued / shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `observability.increment()`, `read_all()` reused for the 2 new `drift_event_log_*` counters (REQ-55) | Compatible (consumes the seam) |
| `decision-reality-drift` (shipped v0.3.0) | `Finding` / `DriftReport` / `classify_binding` shape migrated (REQ-56); `record_drift_summary()` extended (REQ-57 BDD coverage); 21 new BDD scenarios exercise the migrated shape | **MIGRATION**: shape change with 1-release deprecation aliases; BDD scenarios are the regression suite |
| `vector-semantic-search` (shipped v0.4.0) | Unrelated layer | No conflict |
| `cross-project-federation` (shipped v0.5.0) | Unrelated layer | No conflict |
| `graph-snapshots` (shipped v0.6.0) | `SnapshotMeta` / `PruneResult` field names reconciled (REQ-58); `SNAPSHOT_COUNTER_NAMES` catalog extended with W23 deprecation note (REQ-59) | Compatible (consumes the seam) |
| `observability` (change #6, shipped v0.7.0) | `flow metrics summary` + `--domain` filter recommended for REQ-59 W23 deprecation; `record_drift_event()` helper mirrors the 5 existing `record_*_summary` helpers | Compatible (consumes the seam) |
| `prompt-registry` (#7, future) | Unrelated layer; MUST ARCHIVE BEFORE change #8 starts (preserves REQ-55 numbering per Engram #183 + #201) | No conflict |

**Unblocks**: 8 documented carry-forwards closed (W4/W5/W6/W8/S2 from #2 + W23/W25/W26 from #5); v0.8.0 release ships with public API breaking change documented; the `drift_events.jsonl` audit trail is available for downstream consumers; the 21 missing BDD scenarios for REQ-10/12/13/14/16 are present (spec-vs-test gap closed since v0.3.0); the W23 dual-name coexistence is officially documented.

**Constrains**: any future change that touches the `Finding` / `DriftReport` / `classify_binding` signature MUST NOT introduce new fields before v1.0 (the `@property graph_unavailable` alias is the only backward-compat surface); the `drift_events.jsonl` schema is locked for v0.8.0 (`{ts, change, decision_id, binding_id, class, detected_at}`); any future change that adds a drift counter MUST add the new counter name to the `DRIFT_COUNTER_NAMES` catalog in `observability.py` (extending the 8-name list to N+1).

---

## References

- Explore: `openspec/changes/drift-hardening/explore.md` (Engram `sdd/drift-hardening/explore` #222 — full option matrix A-C, 15 carry-forwards evaluated, 8 OPEN + 7 RESOLVED, 5 P0/P1 REQs recommended)
- Proposal: `openspec/changes/drift-hardening/proposal.md` (Engram `sdd/drift-hardening/proposal` #223 — Approach A recommended, 5 cooperating pieces, 10 open questions for design, 10 risks, single-PR-4-batch strategy)
- Predecessor specs (format reference):
  - `openspec/changes/archive/2026-06-27-observability-pr1/spec.md` (change #6 PR#1, single-PR-rejected chained-PR-precedent; per-REQ format + scenario structure + Per-PR acceptance criteria + Out of Scope + BDD Feature File Plan table)
  - `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` (change #5, single-PR precedent; per-REQ format + scenario structure + Reconciliation note + Out of Scope + BDD Feature File Plan table)
  - `openspec/changes/archive/2026-06-26-cross-project-federation/spec.md` (change #4, chained-PR precedent)
  - `openspec/changes/archive/2026-06-26-vector-semantic-search/spec.md` (change #3, drift-adjacent unit-test-to-BDD-translation pattern; `VECTOR_COUNTER_NAMES` precedent)
- Source-of-truth for the carry-forwards:
  - `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` — REQ-9..16 (W4, W5, W6, W8, S2 ownership)
  - `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` — REQ-28..34 (W23, W25, W26 ownership)
- Precedents:
  - `decision-code-linking` archive-report #119 S3 — BDD step def file 5-6× growth multiplier — absorbed into the ×6 forecast
  - `observability` change #6 REQ-37 `--domain snapshot` filter — recommended for REQ-59 W23 deprecation
  - `metrics.jsonl` rotation pattern from observability REQ-8 — mirrored for REQ-55 JSONL rotation (10 MB policy)
- Carry-forwards resolved by this change:
  - `decision-reality-drift` verify-report #135 — W4/W5/W6/W8/S2 (closed in this change; REQ-55/56/57 + REQ-59 S2)
  - `graph-snapshots` verify-report #188 — W23/W25/W26 (closed in this change; REQ-58 W25/W26 + REQ-59 W23)
- Engram DB state (2026-06-27): 173 observations across 10 projects; JSONL sink size at the time of change #8 proposal: ~155 KB across 33 counter names (31 existing + 2 new `drift_event_log_*`)

---

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {"project": "flow-engineering", "id": "src_flow_engineering_drift_event_log_module", "label": "drift_event_log.py (NEW ~150 LOC; record_drift_event + iter_drift_events + 10MB rotation)", "file": "src/flow_engineering/drift_event_log.py", "line": 1, "confidence": 0.95, "source": "manual"},
    {"project": "flow-engineering", "id": "src_flow_engineering_decision_drift_module", "label": "decision_drift.py (MODIFY +60/-20 LOC; Finding decision_id int + DriftReport scanned_at str ISO + unable_to_verify + 2-arg classify_binding + @property graph_unavailable)", "file": "src/flow_engineering/decision_drift.py", "line": 1, "confidence": 0.95, "source": "manual"},
    {"project": "flow-engineering", "id": "src_flow_engineering_daemon_handle_apply_progress_event", "label": "daemon.py handle_apply_progress_event (MODIFY +30/-10 LOC; wire record_drift_event + W6 still-valid silence)", "file": "src/flow_engineering/daemon.py", "line": 34, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "src_flow_engineering_cli_write_back_findings", "label": "cli.py _write_back_findings (MODIFY +25/-5 LOC; S2 stderr WARN once per batch with FLOW_DRIFT_SKIP_WARN_THRESHOLD)", "file": "src/flow_engineering/cli.py", "line": 1637, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "src_flow_engineering_observability_record_drift_event", "label": "observability.py record_drift_event helper (MODIFY +15 LOC; +drift_event_log_total counter + drift_event_log_bytes gauge)", "file": "src/flow_engineering/observability.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "openspec_specs_drift_hardening_spec", "label": "openspec/specs/drift-hardening/spec.md (NEW — bootstraps drift-hardening capability spec; catalogs REQ-55..59 + dataclass shape contract + counter catalog)", "file": "openspec/specs/drift-hardening/spec.md", "line": 1, "confidence": 0.95, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_bdd_req10_drift_cli", "label": "tests/bdd/req10_drift_cli.feature (NEW — 9 BDD scenarios for REQ-10 CLI surface)", "file": "tests/bdd/req10_drift_cli.feature", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_bdd_req11_drift_exit", "label": "tests/bdd/req11_drift_exit.feature (NEW — 3 BDD scenarios for REQ-11 exit codes)", "file": "tests/bdd/req11_drift_exit.feature", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_bdd_req12_drift_counters", "label": "tests/bdd/req12_drift_counters.feature (NEW — 3 BDD scenarios for REQ-12 8 drift counters)", "file": "tests/bdd/req12_drift_counters.feature", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_bdd_req13_drift_metadata", "label": "tests/bdd/req13_drift_metadata.feature (NEW — 3 BDD scenarios for REQ-13 update_observation_metadata)", "file": "tests/bdd/req13_drift_metadata.feature", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_bdd_req14_drift_resilience", "label": "tests/bdd/req14_drift_resilience.feature (NEW — 4 BDD scenarios for REQ-14 graph_unavailable + timeout + retry + per-row isolation)", "file": "tests/bdd/req14_drift_resilience.feature", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_bdd_req16_skill_prose", "label": "tests/bdd/req16_skill_prose.feature (NEW — 2 BDD scenarios for REQ-16 SKILL.md grep)", "file": "tests/bdd/req16_skill_prose.feature", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_bdd_req15_drift_daemon_extended", "label": "tests/bdd/req15_drift_daemon.feature (MODIFY +80 LOC; REQ-55 extend with 2 JSONL event-log scenarios)", "file": "tests/bdd/req15_drift_daemon.feature", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_bdd_test_decision_reality_drift_steps", "label": "tests/bdd/test_decision_reality_drift_steps.py (MODIFY or SPLIT per REQ; +400 LOC step glue for 6 new feature files)", "file": "tests/bdd/test_decision_reality_drift_steps.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_bdd_test_drift_hardening_steps", "label": "tests/bdd/test_drift_hardening_steps.py (NEW +160 LOC; BDD Step 6b cluster-count assertion)", "file": "tests/bdd/test_drift_hardening_steps.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_unit_test_drift_event_log", "label": "tests/unit/test_drift_event_log.py (NEW +180 LOC; JSONL writer unit tests)", "file": "tests/unit/test_drift_event_log.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_unit_test_decision_drift_extended", "label": "tests/unit/test_decision_drift.py (MODIFY +30 LOC; dataclass shape round-trip + DeprecationWarning capture tests)", "file": "tests/unit/test_decision_drift.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_unit_test_daemon_drift_events_extended", "label": "tests/unit/test_daemon_drift_events.py (MODIFY +20 LOC; REQ-55 event-log integration + W6 still-valid silence)", "file": "tests/unit/test_daemon_drift_events.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_unit_test_cli_watch_drift_extended", "label": "tests/unit/test_cli_watch_drift.py (MODIFY +10 LOC; REQ-55 CLI wiring + --drift-event-log flag)", "file": "tests/unit/test_cli_watch_drift.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_unit_test_cli_drift_extended", "label": "tests/unit/test_cli_drift.py (MODIFY +25 LOC; REQ-59 S2 stderr WARN capture + REQ-56 cast site updates)", "file": "tests/unit/test_cli_drift.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_unit_test_changelog_drift_hardening", "label": "tests/unit/test_changelog_drift_hardening.py (NEW +100 LOC; CHANGELOG v0.8.0 entry + BREAKING section + v0.6.0 Notes W23 entry)", "file": "tests/unit/test_changelog_drift_hardening.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_unit_test_pyproject_version", "label": "tests/unit/test_pyproject_version.py (NEW +20 LOC; pyproject.toml version == 0.8.0)", "file": "tests/unit/test_pyproject_version.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "tests_unit_test_skill_md_drift_hooks", "label": "tests/unit/test_skill_md_drift_hooks.py (NEW +120 LOC; 6 SKILL.md files have drift-hardening hook prose)", "file": "tests/unit/test_skill_md_drift_hooks.py", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "openspec_changes_archive_2026_06_26_decision_reality_drift_spec_modified", "label": "openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md (MODIFY +5/-5 LOC; REQ-56 reconcile Finding/DriftReport shape)", "file": "openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "openspec_changes_archive_2026_06_26_decision_reality_drift_design_modified", "label": "openspec/changes/archive/2026-06-26-decision-reality-drift/design.md (MODIFY +10/-8 LOC; REQ-56 reconcile dataclass type signatures)", "file": "openspec/changes/archive/2026-06-26-decision-reality-drift/design.md", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "openspec_changes_archive_2026_06_27_graph_snapshots_spec_modified", "label": "openspec/changes/archive/2026-06-27-graph-snapshots/spec.md (MODIFY +3/-3 LOC; REQ-58 W26 freed_bytes field reconciliation)", "file": "openspec/changes/archive/2026-06-27-graph-snapshots/spec.md", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "openspec_changes_archive_2026_06_27_graph_snapshots_design_modified", "label": "openspec/changes/archive/2026-06-27-graph-snapshots/design.md (MODIFY +5/-5 LOC; REQ-58 W25 size_bytes + pinned field reconciliation)", "file": "openspec/changes/archive/2026-06-27-graph-snapshots/design.md", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "pyproject_version_bump", "label": "pyproject.toml (MODIFY +1/-1 LOC; version = \"0.8.0\")", "file": "pyproject.toml", "line": 3, "confidence": 0.95, "source": "manual"},
    {"project": "flow-engineering", "id": "changelog_v080_entry", "label": "CHANGELOG.md (MODIFY +40 LOC; v0.8.0 entry with 5 REQs + BREAKING section)", "file": "CHANGELOG.md", "line": 1, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "changelog_v060_w23_notes", "label": "CHANGELOG.md (MODIFY +3 LOC; v0.6.0 Notes section W23 coexistence entry from batch B)", "file": "CHANGELOG.md", "line": 116, "confidence": 0.9, "source": "manual"},
    {"project": "flow-engineering", "id": "skill_md_drift_hardening_hooks", "label": "~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md (MODIFY ~80 LOC runtime-only; drift-hardening hook prose)", "file": "~/.config/opencode/skills/sdd-verify/SKILL.md", "line": 1, "confidence": 0.85, "source": "manual"}
  ]
}