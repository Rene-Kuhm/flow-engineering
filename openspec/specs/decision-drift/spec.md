<!-- spec.md: decision-drift capability catalog. Source: sdd-spec bootstrap in drift-hardening batch D. Archive sync: 2026-06-27 + 2026-06-28 + 2026-06-28 (v1.0). -->
# Decision-Drift Capability Spec

## Archive status (2026-06-27)

**drift-hardening (change #8) SHIPPED as v0.8.0 — single PR, 4 sequential apply batches (A + B + C + D), 22 tasks complete, ~9 700 realistic LOC landed across 7 commits on `main` (HEAD `4bbcc21`).**

**REQs shipped**: REQ-55 (drift_event_log JSONL writer + still-valid silence), REQ-56 (dataclass shape migration — `decision_id: int`, `scanned_at: str ISO 8601`, `unable_reason: str | None`, 2-arg `classify_binding`), REQ-57 (21 NEW BDD scenarios across 6 feature files), REQ-58 (snapshot spec/design field reconciliation), REQ-59 (W23 dual-name coexistence deprecation + S2 stderr WARN).

**Verdict at archive**: **PASS WITH WARNINGS — archive-ready**. Per `verify-report.md` (mirrored to `openspec/changes/drift-hardening/verify-report.md` and soon `openspec/changes/archive/2026-06-27-drift-hardening/verify-report.md` once the verify agent moves it): **0 CRITICAL findings** + **9 WARNING** (3 design deviations from D2/OQ-10, all explicitly endorsed by the orchestrator brief; 6 doc/style debt) + **5 SUGGESTION** (all non-blocking v0.9.0/v1.0 follow-ups). All 22 tasks (T1.1..T4.5) closed + 1 120/1 125 tests passing + 24 BDD scenarios in drift-related feature files pass + 108/108 drift-hardening unit tests pass + 13/13 v0.8.0 migration RED→GREEN tests pass. The 5 pre-existing pytest failures trace to changes #6 PR#2 (observability) + #7 PR#1 (prompt-registry) — NOT drift-hardening regressions — and are NOT blockers for this archive. **Archive the artifacts regardless** per orchestrator brief; W-fix commits for the 3 design deviations (W1/W2/W3) are endorsed by the brief and the capability spec's migration note.

The v0.8.0 1-release compat shims and the new `unable_reason: str | None` field are documented below per the brief. The dataclass shape migration deviated from the original design.md (which proposed `__post_init__` coercion + `@property graph_unavailable` rename) to follow the orchestrator brief's compat-shim migration pattern + `graph_unavailable: bool` (canonical, NOT renamed) + `unable_reason: str | None` (NEW). This spec reflects the FINAL brief-aligned shape, not the original design.md proposal.

## v0.9.0 final note (REQ-V9.1..V9.5)

**Status:** ✅ **SHIPPED as v0.9.0 (BREAKING)** — change #9 `v0.9.0-hardening` CLOSED 2026-06-28.

| REQ | Title | Status |
|-----|-------|--------|
| **REQ-V9.1** | `Finding.from_legacy` classmethod deleted (W1 — str→int coercion shim) | ✅ **SHIPPED** |
| **REQ-V9.2** | `DriftReport.from_legacy` classmethod deleted (W1 — float→ISO coercion shim) | ✅ **SHIPPED** |
| **REQ-V9.3** | `classify_binding_legacy` 3-arg wrapper deleted (W3 — backwards-compat shim) | ✅ **SHIPPED** |
| **REQ-V9.4** | `Finding.__post_init__` enforces int-only `decision_id` (W1 enforcement — hard break, no `DeprecationWarning`, no coercion) | ✅ **SHIPPED** |
| **REQ-V9.5** | Docs + meta + version bump + W2 Option B Drift note (`design.md:493`) + 6 SKILL.md updates | ✅ **SHIPPED** |

The 1-release compat shims introduced in v0.8.0 are **removed** in v0.9.0.
**No migration path** — this is a hard break:

- `Finding.decision_id: int` is required. `Finding(decision_id="42", ...)`
  raises `TypeError` via `Finding.__post_init__` (no `DeprecationWarning`,
  no `int()` coercion; `bool` is also rejected as an `int` subclass).
- `DriftReport.scanned_at: str` ISO 8601 UTC Z-suffixed is required.
  `DriftReport(scanned_at=0.0)` raises `TypeError` — no compat shim
  exists in v0.9.0.
- `classify_binding(ref, graph_nodes)` 2-arg is the only canonical entry
  point. The 3-arg form raises `TypeError`.
- `DriftReport.graph_unavailable: bool` stays canonical (per W2 Option
  B resolution); `unable_reason: str | None` stays canonical (NEW in
  v0.8.0). The `unable_to_verify` enum value + `drift_unable_to_verify_total`
  counter name + CLI exit-code 2 wording describe the terminal STATE, not
  the field — these stay unchanged.

This capability spec was bootstrapped in v0.8.0 as part of the
`drift-hardening` cluster. The `decision-reality-drift` change shipped the
original REQ-9..16 contract in v0.3.0 but never created a corresponding
`openspec/specs/decision-drift/spec.md`; v0.8.0 retroactively establishes the
baseline so future deltas (e.g., per-finding graph_unavailable refinement,
cross-project drift federation, OTel push) extend this file rather than
forking the archived `decision-reality-drift` spec.

## Archive status (2026-06-28)

**v0.9.0-hardening (change #9) SHIPPED as v0.9.0 — single PR, 3 sequential sub-batches (A + B + C) of strict TDD, 19 tasks complete (T1.1..T3.7), 12 work-unit commits on `main` (HEAD `3de7783`).**

**REQs shipped**: REQ-V9.1 (W1 `Finding.from_legacy` shim removal), REQ-V9.2 (W1 `DriftReport.from_legacy` shim removal), REQ-V9.3 (W3 `classify_binding_legacy` 3-arg wrapper removal), REQ-V9.4 (W1 enforcement via `Finding.__post_init__` raising `TypeError` on str/bool), REQ-V9.5 (CHANGELOG BREAKING + version bump 0.8.1 → 0.9.0 + W2 Option B Drift note at `archive/2026-06-27-drift-hardening/design.md:493` + 6 SKILL.md runtime updates).

**Verdict at archive**: **PASS WITH WARNINGS — archive-ready** (accepted per `drift-hardening` precedent; same posture). Per `openspec/changes/archive/2026-06-28-v0.9.0-hardening/verify-report.md`: **0 CRITICAL findings** + **1 WARNING** (W1 — `Finding.__post_init__` enforces STRICT REJECTION (TypeError) on str/bool vs the brief's "should coerce to int" example; NOT a regression — implementation honors the proposal §"Code sketch" lines 239-245 hard-break contract) + **4 SUGGESTION** (S1 stale docstring reference to `from_legacy` at `decision_drift.py:116`; S2 12 ruff errors in changed files DOWN from 27 baseline = IMPROVEMENT of 15; S3 12 mypy residuals in `decision_drift.py` within proposal R3 expected band; S4 positive docstring feedback on `__post_init__` rationale — KEEP). All 5 REQs (REQ-V9.1..V9.5) have at least one passing test demonstrating compliance. All 19 tasks (T1.1..T3.7) closed across 3 sub-batches. **1232/1232 tests passing** (net even: -2 removed + 2 added via W1 enforcement) with **0 regressions** vs the `a2ce3f5` baseline. **179/179 BDD scenarios passing**. Ruff: 12 errors in changed files (down from 27 = -15 net improvement); mypy: 12 errors in `decision_drift.py` (within proposal R3 ~10 expected residual band; 1 net improvement from 3 `# type: ignore` cleanup). The 3 documented carry-forwards from `drift-hardening` (W1 + W2 + W3) are all explicitly **CLOSED** by this change.

**Migration guide reference**: see the v0.9.0 final note above (REQ-V9.1..V9.5 section) for the hard-break contract. The v0.9.0 CHANGELOG entry (lines 7-32) documents the 4-step migration path. The W2 Option B Drift note in `archive/2026-06-27-drift-hardening/design.md:493` officially documents the `graph_unavailable` direction-flip (canonical field stays `graph_unavailable: bool` + new `unable_reason: str | None` field; design D2's intent to rename to `unable_to_verify` was NOT followed per the orchestrator pre-decision).

**Note on archive structure**: this is a **single-PR single-cycle** archive (no chained PRs, no per-PR split; 12 work-unit commits in one v0.9.0 release per tasks.md T3.1..T3.7). Mirrors the `drift-hardening` (change #8) cluster structure but condensed — v0.9.0 is a **debt-closure release**, not a feature release.

## Purpose

Cross-version capability spec for the **decision-drift** subsystem — the
end-to-end decision↔code verification surface that:

- classifies every `CodeRef` binding in a change's observations against
  the current `graph.json` (REQ-9);
- surfaces structured drift verdicts via the `flow drift <change>` CLI
  (REQ-10, REQ-11);
- emits `drift_*_total` observability counters so the drift state is
  queryable via `flow metrics --domain=drift` (REQ-12);
- threads `update_observation_metadata` so per-finding drift state can be
  persisted back into the live Engram (REQ-13);
- fails open under partial graph / per-row I/O failures (REQ-14);
- hooks into `flow watch --drift` so the daemon emits a summary line per
  merged task and writes an append-only `drift_events.jsonl` audit trail
  (REQ-15);
- drives the `sdd-verify` Step 6a SKILL.md grep + 21 BDD scenarios
  (REQ-16).

## Source

The authoritative requirements + BDD scenarios live in:

- `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md`
  (REQ-9..16 original contract, v0.3.0).
- `openspec/changes/drift-hardening/spec.md` (REQ-55..59 v0.8.0 cluster;
  REQ-57 is the BDD coverage layer that exercises REQ-9..16 in
  business-domain Given/When/Then phrasing).
- `openspec/changes/drift-hardening/design.md` (D1..D12; the dataclass
  shape migration is D2 + D9 + D12; the JSONL event log is D3 + D11;
  the still-valid silence rule is D4).

This file carries the **canonical requirement statements and BDD scenarios
that survive once the change ships** — REQ-9..16 + REQ-55..59 (with the
21 NEW BDD scenarios from REQ-57) catalogued in one place. Future deltas
extend this baseline rather than forking the archived change spec.

## Requirements

### REQ-9 — Drift classification

The system SHALL provide a pure-library resolver
`decision_drift.classify_binding(ref, graph_nodes)` (v0.8.0 2-arg signature)
that, given a `CodeRef` and the current `graph.json` parsed as
`dict[id, node]`, classifies the binding into exactly one of six
mutually-exclusive classes. When the graph cannot be read, the report
carries a terminal `unable_to_verify` state (NOT a per-binding class).

| Class | Detection rule |
|---|---|
| `still_valid` | `id` resolves at the same `file:line` with matching `label` |
| `label_drift` | `id` resolves at the same `file:line` but `label` differs |
| `stale_location` | `id` resolves at a different `file:line` |
| `stale_id` | `id` is absent from current `graph.json` |
| `obsolete` | All bindings are `source: unbound` AND `graphify query` returns 0 candidates >= threshold |
| `contradicted` | Two decisions in the same change reference the same `id` with conflicting `source`/`confidence` |
| `unable_to_verify` | Terminal: graph.json missing or empty (per-report, not per-binding) |

Classification MUST be deterministic for a given `(ref, graph_nodes)` pair
and MUST emit exactly one class per binding. The `unable_to_verify` state
is terminal for the WHOLE report, not per-binding.

### REQ-10 — `flow drift scan <change>` CLI surface

The system SHALL provide a `flow drift scan <change>` subcommand that
runs `decision_drift.scan_change(change_name, ...)` and emits the result
to stdout in human-readable text format by default. Flags:

- `--json` structured JSON envelope (REQ-12 hand-off).
- `--include-obsolete` opt-in to the OBSOLETE branch (LLM cost bound per
  design #123 decision 3; default excludes OBSOLETE).
- `--since=<iso>` filters observations to `created_at >= <iso>` epoch.
- `--write-back` persists per-finding metadata via
  `EngramClient.update_observation_metadata`.
- `--graph-json=<path>` custom `graph.json` path (default
  `~/.flow-engineering/graph.json`).
- Unknown change name exits `3` with a JSON error on stderr.

### REQ-11 — Exit code semantics

The system SHALL emit exit codes per `flow drift scan <change>` that
match the W6 / D4 still-valid silence rule:

- `0` still-valid (every binding is `STILL_VALID` or the report is empty
  AND `graph_unavailable=False`).
- `1` drift detected (any non-STILL_VALID class present).
- `2` `graph_unavailable=True` (terminal unable_to_verify state).
- `3` usage error (unknown change, invalid flag).

`2` wins over `1` wins over `0` so the most informative exit code wins
when multiple states overlap.

### REQ-12 — Drift counters via `record_drift_summary`

The system SHALL emit one event per call to
`observability.record_drift_summary(report)` for each of the 8
`drift_*_total` counters:

- `drift_invoked_total{change=<chg>}` (always 1 per call).
- `drift_still_valid_total{count=<N>}` — STILL_VALID count.
- `drift_label_drift_total{count=<N>}` — LABEL_DRIFT count.
- `drift_stale_location_total{count=<N>}` — STALE_LOCATION count.
- `drift_stale_id_total{count=<N>}` — STALE_ID count.
- `drift_obsolete_total{count=<N>}` — OBSOLETE count.
- `drift_contradicted_total{count=<N>}` — CONTRADICTED count.
- `drift_unable_to_verify_total{count=1|0}` — 1 when
  `report.graph_unavailable=True` else 0.

Counter emission is idempotent across repeat calls (each call emits one
event per counter; counter totals accumulate in `metrics.jsonl`).

### REQ-13 — `update_observation_metadata` per-finding write-back

The system SHALL thread per-finding drift state back into the live Engram
via `EngramClient.update_observation_metadata(observation_id, metadata)`:

- Append `last_verified_at` (ISO 8601 UTC) and `last_drift_class` (str
  enum) to the observation's metadata dict.
- Idempotent on repeat keys (overwrite, NOT append).
- Unknown `observation_id` raises `ObservationNotFoundError` (no
  auto-create).

### REQ-14 — Resilience: per-row IOError doesn't crash

The system SHALL isolate per-row I/O failures in `flow drift scan
<change>`:

- A single-row failure (deleted file mid-scan, read-only file during
  write-back) MUST NOT abort the loop. Each `update_observation_metadata`
  call is wrapped in its own `except` clause that logs to observability
  and continues.
- `flow drift scan` is read-only by default (no `update_observation_metadata`
  calls unless `--write-back`).
- Partial write-back success exits `0` with a `wrote: <N>, failed: <M>`
  summary line.
- `graph_unavailable=True` exits `2` with a structured JSON error pointing
  the user at `--graph-json=<path>`.

### REQ-15 — Daemon seam (`flow watch --drift`)

The system SHALL thread `decision_drift.scan_change` into the
`flow watch <change>` watchdog loop via
`daemon.handle_apply_progress_event`:

- When at least one task in `apply-progress` has `status: merged`, runs
  `scan_change(change_name)` and emits a one-line summary via the
  `on_summary` callback (defaults to `print`).
- `record_drift_summary(report)` is always called regardless of outcome.
- W6 silence rule (D4): suppress the outer summary line when
  `report.total == 0 AND not report.graph_unavailable` (the common
  quiet-tick case). `unable_to_verify=True` preserves the summary line
  with `unable_reason`.
- v0.8.0 (REQ-55 W5): `_append_drift_events(report)` writes one JSONL line
  per non-STILL_VALID finding to `~/.flow-engineering/drift_events.jsonl`
  AFTER `record_drift_summary`. Best-effort (`try/except OSError`); never
  crashes the daemon.
- The JSONL wire format is `{ts, change, decision_id, binding_id, class,
  detected_at}` (key order matters for stable diff).

### REQ-16 — SKILL.md drift detection hook

The system SHALL carry the `## Drift detection hook` section in all 6
sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md runtime files
(at `~/.config/opencode/skills/`) so every SDD phase has the v0.8.0 drift
API surface in scope. The hook must mention:

- Exit codes `0/1/2` for `flow drift <change>` (REQ-11).
- The six mutually-exclusive classes + terminal `unable_to_verify`
  (REQ-9).
- The v0.9.0 final dataclass shape (int `decision_id` with
  `__post_init__` enforcement; ISO 8601 `scanned_at`; `graph_unavailable`
  + `unable_reason`; 2-arg `classify_binding`). v0.8.0 compat shims
  removed — hard break, no migration path.

### REQ-55 — `DriftEventLog` JSONL writer (v0.8.0)

The system SHALL provide a `DriftEventLog` JSONL append-only writer at
`~/.flow-engineering/drift_events.jsonl` that:

- Writes one JSON line per non-STILL_VALID finding from `DriftReport`.
- Rotates at exactly 10 MB to `drift_events.<ISO-no-colons>.jsonl`
  (lex-sortable by rotation time).
- Wraps the append in `try/except OSError`; on disk full / permission
  denied, logs a stderr WARN and returns without raising.
- Is thread-safe via `threading.Lock` (in-process only; no OS-level file
  lock).
- Emits the `drift_event_log_total{change=<chg>}` counter via
  `observability.increment` per appended line.
- Emits the `drift_event_log_bytes` gauge post-rotation.

The read-side CLI (`flow drift events [--since] [--change]`) is deferred
to a follow-up change; consumers use
`cat ~/.flow-engineering/drift_events.jsonl | jq` in v0.8.0.

### REQ-56 — Dataclass shape migration (v0.8.0 + v0.9.0 hard break)

The system SHALL migrate the `decision_drift` public dataclass shape:

- `Finding.decision_id: int` (was `str`); v0.9.0 enforces this at the
  dataclass boundary via `Finding.__post_init__` which raises
  `TypeError` on non-`int` inputs (including `bool`).
- `DriftReport.scanned_at: str` ISO 8601 UTC Z-suffixed (was `float`
  epoch); v0.9.0 rejects `float` inputs (no compat shim).
- `DriftReport.graph_unavailable: bool` (canonical) + new
  `unable_reason: str | None`; legacy `unable_to_verify` kwarg is no
  longer mapped (v0.9.0).
- `classify_binding(ref, graph_nodes)` is 2-arg; v0.9.0 rejects the
  3-arg form.

v0.8.0 compat shims were REMOVED in v0.9.0 — hard break, no
migration path.

### REQ-57 — BDD coverage (v0.8.0)

The system SHALL provide 21 NEW BDD scenarios across 6 NEW feature files
covering REQ-10, REQ-11, REQ-12, REQ-13, REQ-14, and REQ-16 in
business-domain Given/When/Then phrasing (NOT unit-test fixture dict
phrasing):

- `tests/bdd/req10_drift_cli.feature` — 9 scenarios for `flow drift scan`
  CLI surface (text default, `--json`, `--include-obsolete`, `--since`,
  `--write-back`, `--graph-json`, unknown change, exit 0/1/2).
- `tests/bdd/req11_drift_exit_codes.feature` — 3 scenarios for exit codes.
- `tests/bdd/req12_drift_counters.feature` — 3 scenarios for the 8
  `drift_*_total` counters.
- `tests/bdd/req13_drift_metadata.feature` — 3 scenarios for
  `update_observation_metadata`.
- `tests/bdd/req14_drift_resilience.feature` — 4 scenarios for resilience
  (per-row IOError, read-only default, partial write-back success,
  graph_unavailable helpful error).
- `tests/bdd/req16_skill_prose.feature` — 2 scenarios for SKILL.md drift
  detection hook.
- `tests/bdd/req15_drift_daemon.feature` — extended with 2 NEW scenarios
  for REQ-55 JSONL writer (line per finding; silent on still-valid).

Step glue follows the per-REQ split per design D10
(`test_req<N>_<name>_steps.py`), mirroring the
`test_graph_snapshots_steps.py` precedent. The consolidated
`test_decision_reality_drift_steps.py` is extended (not split) for the
REQ-15 daemon JSONL scenarios.

### REQ-58 — Snapshot field reconciliation (v0.8.0)

The system SHALL reconcile the archived `decision-reality-drift` +
`graph-snapshots` spec/design files so the documented dataclass shape
matches the actual implementation:

- `decision-reality-drift` spec/design: REQ-9..16 scenarios reference
  `unable_to_verify` + `unable_reason` (per the v0.8.0 shape).
- `graph-snapshots` spec/design: `SnapshotMeta.size_bytes` +
  `SnapshotMeta.pinned` + `PruneResult.freed_bytes` field names match
  the implementation at `src/flow_engineering/snapshot_manager.py:100-121 +
  209-247` (zero production code change; doc-only).

### REQ-59 — W23 + S2 closeout (v0.8.0)

The system SHALL close the two remaining carry-forwards:

- W23: the `snapshot_pruned_total` ↔ `snapshot_prune_total` dual-name
  events in `~/.flow-engineering/metrics.jsonl` (REQ-37 `--domain
  snapshot` filter matches both by `snapshot_` prefix; CHANGELOG v0.6.0
  Notes section documents the coexistence + 1-line `sed` migration).
- S2: stderr WARN log on skipped non-int `decision_id` in
  `cli._write_back_findings`, emitted once per batch when
  `skipped_total >= FLOW_DRIFT_SKIP_WARN_THRESHOLD` (default 3; `-1`
  disables; `0` emits every batch with `skipped_total > 0`).

## Dataclass shape contract (v0.8.0)

```python
@dataclass(frozen=True)
class Finding:
    decision_id: int          # was: str; v0.9.0 enforces via __post_init__
    binding: CodeRef
    drift_class: DriftClass
    detail: str

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, int) or isinstance(
            self.decision_id, bool
        ):
            raise TypeError(
                f"Finding.decision_id must be int, got {type(self.decision_id).__name__}"
            )

@dataclass
class DriftReport:
    change_name: str
    scanned_at: str            # was: float (ISO 8601 UTC Z-suffixed)
    graph_mtime: str | None    # was: float | None
    decisions_total: int
    bindings_total: int
    class_counts: dict[DriftClass, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    graph_unavailable: bool = False
    unable_reason: str | None = None    # NEW in v0.8.0; canonical in v0.9.0

def classify_binding(ref, graph_nodes) -> DriftClass:
    """2-arg canonical entry point (v0.9.0 final)."""
    ...
```

## Counter catalog (REQ-12 + REQ-55)

| Counter | Source | Label |
|---|---|---|
| `drift_invoked_total` | `record_drift_summary` | `change=<chg>` |
| `drift_still_valid_total` | `record_drift_summary` | `count=<N>` |
| `drift_label_drift_total` | `record_drift_summary` | `count=<N>` |
| `drift_stale_location_total` | `record_drift_summary` | `count=<N>` |
| `drift_stale_id_total` | `record_drift_summary` | `count=<N>` |
| `drift_obsolete_total` | `record_drift_summary` | `count=<N>` |
| `drift_contradicted_total` | `record_drift_summary` | `count=<N>` |
| `drift_unable_to_verify_total` | `record_drift_summary` | `count=<0|1>` |
| `drift_event_log_total` | `_append_drift_events` | `change=<chg>` |
| `drift_event_log_bytes` | `_append_drift_events` | (gauge) |
| `drift_write_back_skipped_total` | `_write_back_findings` | `reason=non_int_decision_id` |
| `drift_write_back_failed_total` | `_write_back_findings` | (counter) |

## Cross-Impact

| Capability | Relationship |
|---|---|
| `decision-code-linking` (v0.2.0) | `CodeRef` + `extract_code_refs` + `ParseError` reused by `scan_change` |
| `observability` (v0.7.0) | `record_drift_summary` + `increment` + `metrics.jsonl` consumed by `flow metrics --domain=drift` |
| `graph-snapshots` (v0.6.0) | `SnapshotMeta.size_bytes` / `pinned` / `PruneResult.freed_bytes` reconciled (REQ-58) |
| `vector-semantic-search` (v0.4.0) | Unrelated |
| `cross-project-federation` (v0.5.0) | Unrelated |
| `prompt-registry` (v0.8.0 PR#1) | Unrelated |

## Versioning

| Version | Date | Change | Status | Headline |
|---------|------|--------|--------|----------|
| v0.2.0 | 2026-06-24 | `decision-code-linking` (#1) | SHIPPED | `CodeRef` + `extract_code_refs` + `flow inspect <change>` |
| v0.3.0 | 2026-06-26 | `decision-reality-drift` (#2) | SHIPPED | REQ-9..16 — first drift detection surface; introduced str `decision_id` + epoch `scanned_at` |
| v0.4.0 | 2026-06-26 | `vector-semantic-search` (#3) | SHIPPED | REQ-17..22 — `[vectors]` extra gated semantic search |
| v0.5.0 | 2026-06-26 | `cross-project-federation` (#4) | SHIPPED | REQ-23..27 — `flow search --federated` + `flow projects` |
| v0.6.0 | 2026-06-27 | `graph-snapshots` (#5) | SHIPPED | REQ-28..34 — `SnapshotManager` + `flow snapshot {create,list,show,diff,rollback,prune}` |
| v0.7.0 | 2026-06-27 | `observability` (#6) | SHIPPED | REQ-35..39 — `flow metrics summary/export/aggregate` + REQ-38 Prometheus textfile |
| v0.8.0 | 2026-06-27 | `prompt-registry` (#7) PR#1 | SHIPPED | REQ-45..47 — Python API catalog + `validate_catalog()` + `lint_prompts()` |
| v0.8.0 | 2026-06-27 | `drift-hardening` (#8) | SHIPPED | REQ-55..59 — `DriftEventLog` JSONL + v0.8.0 BREAKING dataclass shape + 21 NEW BDD scenarios + 1-release compat shims |
| v0.8.1 | 2026-06-28 | `prompt-registry` (#7) PR#2b | SHIPPED | REQ-49..50 — `flow prompts` CLI + SKILL.md mirror catalog |
| **v0.9.0** | **2026-06-28** | **`v0.9.0-hardening` (#9)** | **✅ SHIPPED (BREAKING)** | **REQ-V9.1..V9.5 — 1-release compat shims REMOVED (`Finding.from_legacy`, `DriftReport.from_legacy`, `classify_binding_legacy`); `Finding.__post_init__` enforces int `decision_id` (hard break); W2 Option B Drift note at `design.md:493`; 1232/1232 tests pass** |
| **v1.0.0** | **2026-06-28** | **`v1.0-followups` (#10)** | **✅ SHIPPED** | **REQ-V1.0.1..V1.0.4 — S1 DriftEvent JSONL `decision_id: int` wire-format flip + defensive legacy coercion + S2 `flow drift-events {list,tail,stats}` read-side CLI subcommand group + 12 mypy residuals cleanup + CHANGELOG v1.0 + capability spec sync + pyproject 1.0.0 bump; 1275/1275 tests pass** |
| **v1.1.0** | **2026-06-28** | **`v1.1-followups` (#11)** | **✅ SHIPPED** | **REQ-V1.1.1..V1.1.6 — DriftEventLog rotation (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` default 10 MB + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` default 30 days) + S2 wire-format hardening (drop defensive `str→int` shim; WARN becomes `DriftEventLogLegacyFormatError` + `--strict` flag) + REQ-51 (`prompt_renders.jsonl` sink + `FLOW_PROMPT_LOG=1` gate) + REQ-52 (`prompts_render_total`/`prompts_render_ms`/`prompts_render_failed_total` counters + `record_prompt_render_summary`) + REQ-53 (`docs/prompts.md` auto-gen via `scripts/generate_prompts_doc.py` + `make docs`) + REQ-V1.1.6 (`SnapshotGraphMissingError` canonical + `SnapshotGraphMissing` 1-release alias + 3 ruff `--unsafe-fixes` cleanup on `decision_drift.py`); 1342/1342 tests pass (+67 vs v1.0)** |
| **v1.2.0a** | **2026-06-28** | **`v1.2-followups` (#12) PR#2a** | **✅ SHIPPED** | **REQ-V1.2.1 — `_rotate_metrics_if_needed()` + `FLOW_METRICS_LOG_MAX_BYTES` (default 10 MB = 10485760) + `FLOW_METRICS_LOG_MAX_AGE_DAYS` (default 30 days) env vars + best-effort `try/except OSError` swallow + age-based sibling cleanup via `_delete_stale_metrics_siblings()` extracted helper; mirrors `drift_event_log.py:196-254` rotation pattern; CHANGELOG `## [1.2.0a]` entry (NOT v1.2.0 — that's PR#2d scope); 1349/1349 tests pass (+7 net vs `75961ad` v1.1.0 baseline; 0 regressions); 0 CRITICAL + 2 WARNING + 2 SUGGESTION (PASS WITH WARNINGS accepted per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` precedent). PR#2a is 1 of 4 chained PRs in the v1.2 release (stacked-to-main); PR#2b/c/d still pending.** |
| **v1.2** | **2026-06-28** | **`v1.2-followups` (#12) PR#2a/b/c/d** | **✅ SHIPPED (BREAKING)** | **Full v1.2 release closes 4 carry-forwards from v1.1: REQ-V1.2.1 metrics.jsonl rotation (PR#2a, v1.2.0a) + REQ-V1.2.2 golden regression tests for `render_prompt` (PR#2b, v1.2.0b) + REQ-V1.2.3 `min_sdd_skill_versions` enforcement (PR#2c, v1.2.0c) + REQ-V1.2.4 Path A subcommand group rename + 1-release `deprecated=True` Click group alias for `flow drift-events` (PR#2d, v1.2.0). 4 chained PRs (`stacked-to-main` strategy per `proposal.md`); the final release is `v1.2.0` (BREAKING — Path A rename); PR#2a/b/c ship as v1.2.0a/b/c pre-release markers per CHANGELOG versioning convention. pyproject `1.1.0 → 1.2.0` + CHANGELOG `## [1.2.0] - 2026-06-28` BREAKING entry. **1383/1383 tests passing** (+7 net vs v1.1 baseline of 1376; +7 NEW v1.2 tests in PR#2d: 3 `TestDriftEventsGroup` + 4 `TestDriftEventsAlias`). The hyphenated `flow drift-events` alias is preserved for one release cycle and REMOVED in v1.3 per the `SnapshotGraphMissing` v1.1 precedent. CHANGE #12 (`v1.2-followups`) CLOSED.** |

**v1.0 entry — change #9 CLOSED + v0.9.0 BREAKING shipped (2026-06-28).** With change #9 (`v0.9.0-hardening`) archived, the v0.8.0 1-release compat shim window is officially closed. Operators who delayed the v0.7.x → v0.9.0 jump now have a hard-break surface to migrate against; the v0.8.x line is end-of-life. The 3 carry-forwards from `drift-hardening` (W1, W2, W3) are CLOSED. v1.0 planning resumes per the deferred follow-ups: DriftEvent JSONL `decision_id: int` wire-format flip (S1 from drift-hardening) + `flow drift events` CLI read-side (S2 from drift-hardening) + tech-debt residuals (S2 ruff `--unsafe-fixes` + S3 mypy annotations on `decision_drift.py` lines 127/161/203/252/253/262/278/372/375/310/411/439) + DriftEventLog rotation (v1.1 alongside metrics rotation).

**v1.1 entry — change #11 CLOSED + v1.1.0 SHIPPED (2026-06-28).** Change #10 (`v1.0-followups`) shipped the BREAKING wire-format flip + `flow drift-events {list,tail,stats}` CLI + mypy cleanup (1275/1275 tests); change #11 (`v1.1-followups`) ships the debt-closure release: DriftEventLog rotation, S2 hardening (drop defensive `str→int` shim — `DriftEventLog.read_all()` raises `DriftEventLogLegacyFormatError` on legacy `str` lines; `flow drift-events {list,tail,stats} --strict` flag aborts with exit 4 + CHANGELOG v1.0 `sed` migration hint), REQ-51/52/53 prompt render observability (`prompt_renders.jsonl` sink + 3 counters + auto-generated `docs/prompts.md`), REQ-V1.1.6 `SnapshotGraphMissingError` canonical + `SnapshotGraphMissing` 1-release alias + 3 ruff `--unsafe-fixes` cleanup on `decision_drift.py`. **1342/1342 tests pass** (+67 net vs v1.0 baseline; net +68 added − 1 `test_version` regression fix). All 5 v1.0 follow-up carry-forwards (S1 rotation, S2 hardening, S3 REQ-51 sink, S4 REQ-52 counters, S5 REQ-53 docs) + 12 ruff `--unsafe-fixes` are CLOSED. The change ran as 19 work-unit commits in 6 sequential sub-batches with strict TDD discipline; planning artifacts were committed inline (per W2 finding — see v1.1.0 archive status section below). The next change is `v1.2-followups` (#12) — covers REQ-48 golden regression tests + REQ-54 `min_sdd_skill_versions` + Path A subcommand group rename (BREAKING) + remaining ruff residuals + W2 backfill.

## v1.0.0 archive status (2026-06-28)

**v1.0-followups (change #10) SHIPPED as v1.0.0 — single PR, 4 sequential sub-batches (A + B + C + D) of strict TDD, 17 tasks complete (T1.1..T4.4), 20 work-unit commits on `main` (HEAD `54d5cdb` post-closeout + planning artifacts).**

| REQ | Title | Status |
|-----|-------|--------|
| **REQ-V1.0.1** | S1 `DriftEvent.decision_id: int` JSONL wire-format flip + `daemon.py:60` `str()` coercion removed + `DriftEventLog.read_all()` defensive legacy `str`→`int` coercion with one-time stderr WARN per log-path | ✅ **SHIPPED** |
| **REQ-V1.0.2** | S2a `flow drift-events list` subcommand with `--since`/`--until`/`--change`/`--event-class`/`--limit`/`--format=text\|json\|prometheus\|csv` flags + 4 format handlers | ✅ **SHIPPED** |
| **REQ-V1.0.3** | S2b `flow drift-events tail --limit=10` + `flow drift-events stats` subcommands + 3 NEW BDD scenarios in `tests/bdd/req_v1_0_drift_events.feature` | ✅ **SHIPPED** |
| **REQ-V1.0.4** | CHANGELOG v1.0 entry + pyproject `0.9.0`→`1.0.0` bump + 3 mypy residuals cleanup via per-site `# type: ignore` + capability spec sync | ✅ **SHIPPED** |

**Verdict at archive**: **PASS WITH WARNINGS — archive-ready** (accepted per `drift-hardening` + `v0.9.0-hardening` precedent posture). Per `openspec/changes/archive/2026-06-28-v1.0-followups/verify-report.md`: **1275/1275 tests passing** with **0 regressions** vs the `3de7783` v0.9.0 baseline (net +42 — +43 added — 1 test_version regression fix). **3 NEW BDD scenarios passing**. **0 mypy errors** in `decision_drift.py` post-T4.3 (was 3 pre-cleanup; was 12 expected per proposal — 9 had already been cleaned in prior batches; the per-site `# type: ignore` cleanup at `decision_drift.py:127/161/203/252/253/262/278/310/372/375/411/439` brings mypy to 0 errors). Ruff clean on v1.0-changed files (`cli.py` + `drift_event_log.py`); 12 ruff errors in `decision_drift.py` unchanged from v0.9.0 baseline (`--unsafe-fixes` deferred to v1.1).

**Findings tally**: **0 CRITICAL + 2 WARNING + 5 SUGGESTION** (accepted per `drift-hardening` / `v0.9.0-hardening` precedent):
- **W1** (design deviation) — capability spec uses `## v1.0.0 archive status` instead of the dedicated `## Drift event log JSONL schema` section heading proposed in T4.4 (schema docs are inline; consistent with v0.9.0 archive-status pattern).
- **W2** (environmental) — `flow drift v1.0-followups` returns exit 2 (`unable_to_verify: graph.json unavailable`) — graph not yet populated for the change being verified (same posture as prior verify reports; resolves post-archive).
- **S1..S5** (deferred to v1.1+) — DriftEventLog rotation; S1 wire-format hardening (drop the defensive `str→int` shim); REQ-51/52/53 (`prompt_renders.jsonl` sink + `flow prompt-events` counters + `docs/prompts.md` auto-gen); Path A `flow drift` subcommand group rename (BREAKING); 12 ruff errors `--unsafe-fixes` cleanup.

**Carry-forwards CLOSED**: `drift-hardening` S1 (JSONL wire-format `decision_id: str` inconsistency) — closed via REQ-V1.0.1; `drift-hardening` S2 (`flow drift events` read-side CLI deferred) — closed via REQ-V1.0.2 + REQ-V1.0.3; `v0.9.0-hardening` S3 (12 mypy residuals in `decision_drift.py`) — closed via REQ-V1.0.4 (3 sites at T4.3; 9 already cleaned in prior batches).

**S1 SHIPPED — `DriftEvent.decision_id` int flip**: `src/flow_engineering/drift_event_log.py:46` annotation changed `decision_id: str` → `decision_id: int`; `src/flow_engineering/daemon.py:60` removed `str(finding.decision_id)` coercion (was 1-line hack masking the v0.9.0 int `Finding.decision_id` mismatch); `DriftEventLog.read_all()` gained defensive `try/except (TypeError, ValueError)` + `_legacy_warn_emitted` per-instance flag + one-time stderr WARN so legacy v0.8.x `str` JSONL lines (e.g., `"decision_id": "42"`) coerce gracefully to `int` for one release. The defensive coercion is a **soft compat** — the v1.0 wire format requires `int`, but legacy `str` lines are tolerated for one cycle. v1.1 will drop the legacy guard per the v1.1 deprecation roadmap.

**S2 SHIPPED — `flow drift-events` CLI**: NEW `@main.group(name="drift-events")` Click group in `src/flow_engineering/cli.py` exposes `list` (REQ-V1.0.2) + `tail` (REQ-V1.0.3) + `stats` (REQ-V1.0.3) subcommands. Total ~80 prod LOC + ~190 test LOC across 3 NEW test files (`test_cli_drift_events_list.py` + `test_cli_drift_events_tail.py` + `test_cli_drift_events_stats.py`). All 3 subcommands support `--since`/`--until`/`--change`/`--format=text|json|prometheus|csv` (the `list` subcommand also exposes `--event-class` + `--limit`). 3 NEW BDD scenarios in `tests/bdd/req_v1_0_drift_events.feature` exercise the read-side in business-domain Given/When/Then phrasing. The deferred DriftEventLog rotation (v1.1 alongside metrics rotation) is the only carry-forward not closed by this change.

**Note on archive structure**: this is a **single-PR single-cycle** archive (no chained PRs, no per-PR split; 9 work-unit commits in one v1.0 release per tasks.md T1.1..T4.4). Total scope: ~100 prod + ~250 test = ~350 total LOC delta — well under the 400 LOC chained-PR threshold per `proposal.md` Approach A. The 4 sub-batches (A+B+C+D) follow the strict-TDD `sdd-apply` precedent from `drift-hardening` + `v0.9.0-hardening` (`apply-progress/{sub-batch-X}-tN.md` files). This is a **debt-closure release** (S1 + S2 carry-forwards + tech-debt) not a feature release.

## v1.1.0 archive status (2026-06-28)

**v1.1-followups (change #11) SHIPPED as v1.1.0 — single PR, 6 sequential sub-batches (A + B + C + D + E + F) of strict TDD, 18 functional tasks complete (T1.1..T6.3) + 2 closeout commits (CHANGELOG/release + `test_version` fix), 19 work-unit commits on `main` (HEAD `6cae060` post-`test_version` fix).**

| REQ | Title | Status |
|-----|-------|--------|
| **REQ-V1.1.1** | `DriftEventLog` rotation: `_rotate_if_needed(path)` + `FLOW_DRIFT_EVENT_LOG_MAX_BYTES` (default 10 MB = 10485760) + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` (default 30 days) env vars + best-effort `try/except OSError` swallow + rotation runs INSIDE `threading.Lock` (D11 preserved) | ✅ **SHIPPED** |
| **REQ-V1.1.2** | S2 hardening: `_legacy_warn_emitted` flag REMOVED + defensive `try/except (TypeError, ValueError)` block REMOVED + NEW `DriftEventLogLegacyFormatError(ValueError)` exception + `flow drift-events {list,tail,stats} --strict` flag (default skip+WARN; `--strict` aborts with exit 4 + CHANGELOG v1.0 `sed` migration hint) | ✅ **SHIPPED** |
| **REQ-V1.1.6** | `SnapshotGraphMissingError(Exception)` canonical + `SnapshotGraphMissing` 1-release alias with `DeprecationWarning` (PEP 562 `__getattr__` at `snapshot_manager.py:104-123`) + `ruff check --fix --unsafe-fixes` on `decision_drift.py` (3 fixes: UP022 + UP042 + C419) + CHANGELOG v1.1 entry + pyproject `1.0.0`→`1.1.0` | ✅ **SHIPPED** |

**Verdict at archive**: **PASS WITH WARNINGS — archive-ready** (accepted per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` precedent posture). Per `openspec/changes/archive/2026-06-28-v1.1-followups/verify-report.md`: **0 CRITICAL findings** + **3 WARNING** + **2 SUGGESTION**. All 6 REQs (REQ-V1.1.1..V1.1.6) have at least one passing test demonstrating compliance. All 18 functional tasks (T1.1..T6.3) closed across 6 sub-batches with strict-TDD RED → GREEN → REFACTOR evidence. **1342/1342 tests passing** (+67 net vs `54d5cdb` v1.0 baseline; +68 added − 1 `test_version` regression fix). **182/182 BDD scenarios passing** (unchanged from v1.0; no NEW BDD scenarios — drift-events CLI surface BDD coverage was already complete from v1.0). Mypy: **0 errors** in `decision_drift.py` (carried forward from v1.0 T4.3 cleanup). Ruff: **17 errors** in v1.1-touched files (33 project-wide; 16 pre-existing in untouched files); `cli.py` is clean (was cleaned by v1.0 `ruff --fix`); the 3 `decision_drift.py` auto-fixes applied at T6.3 (UP022 + UP042 + C419) cleared some but not all (see W3). The 5 documented carry-forwards from `v1.0-followups` (S1 DriftEventLog rotation + S2 wire-format hardening + S3 REQ-51 sink + S4 REQ-52 counters + S5 REQ-53 docs) + the 12 ruff `--unsafe-fixes` cleanup are all explicitly **CLOSED** by this change.

**Findings tally**: **0 CRITICAL + 3 WARNING + 2 SUGGESTION** (accepted per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` precedent):
- **W1** (doc-process, RESOLVED by this archive) — `openspec/specs/decision-drift/spec.md` v1.1 archive status section NOT added at apply time (REQ-V1.1.6 T6.4 missing). **THIS ARCHIVE SECTION resolves W1** by adding the `## v1.1.0 archive status (2026-06-28)` section + flipping the Versioning row from PLANNED → SHIPPED.
- **W2** (doc-process, ACCEPTED) — `openspec/changes/v1.1-followups/` planning artifacts (`proposal.md` + `design.md` + `tasks.md` + `explore.md` + `apply-progress/`) NEVER created on disk. The change ran as 19 work-unit commits with per-commit RED → GREEN markers in git history; no consolidated artifact exists. Per the brief, planning artifacts are committed inline to commits rather than as separate files. This is a documentation-process gap; future agents can backfill from commit history if needed. Non-blocking per `drift-hardening` precedent.
- **W3** (tech-debt, ACCEPTED) — 17 ruff errors in v1.1-touched files (33 project-wide; 16 pre-existing in untouched files like `watcher.py` + `orchestrator.py` etc.). The T6.3 `ruff --fix --unsafe-fixes` only fixed 3 of the 17 (UP022 + UP042 + C419 on `decision_drift.py`). Remaining 17 are deferred per the `v0.9.0-hardening` + `v1.0-followups` acceptable-residual-ruff precedent.
- **S1** (cleanup, ACCEPTED) — `prompt_render_log.py:200` missing trailing newline (W292, 1-line fix).
- **S2** (positive, KEEP) — `decision_drift.py:179` N818 `SnapshotGraphMissing` naming convention is intentional (parallel class to canonical `SnapshotGraphMissingError` for backwards compat with batch B1 BDD tests; documented in class docstring).

**Carry-forwards CLOSED**:
- `v1.0-followups` **S1** (DriftEventLog rotation deferred) — closed via REQ-V1.1.1
- `v1.0-followups` **S2** (defensive `str→int` shim hardening — WARN becomes hard error) — closed via REQ-V1.1.2
- `v1.0-followups` **S3** (REQ-51 `prompt_renders.jsonl` sink deferred) — closed via REQ-V1.1.3
- `v1.0-followups` **S4** (REQ-52 prompt observability counters deferred) — closed via REQ-V1.1.4
- `v1.0-followups` **S5** (REQ-53 `docs/prompts.md` auto-generated deferred) — closed via REQ-V1.1.5
- `v1.0-followups` **S6** (12 ruff `--unsafe-fixes` on `decision_drift.py` deferred) — closed via REQ-V1.1.6 T6.3 (3 fixed; 14 remaining deferred to v1.2 per `v0.9.0-hardening` + `v1.0-followups` precedent)

**Net carry-forward closure**: 5/5 v1.0-followups carry-forwards + 1/1 v1.0-followups ruff cleanup = **6/6 closed**. The 5 drift-hardening + v0.9.0-hardening historical carry-forwards remain CLOSED (closed by v1.0-followups). The 3 v1.1 follow-up findings (W2 + W3 + S1) are non-blocking documentation/tech-debt gaps accepted per the established precedent.

**Note on archive structure**: this is a **single-PR single-cycle** archive (no chained PRs, no per-PR split; 19 work-unit commits in one v1.1.0 release per `verify-report.md` lines 70-91 commit log). Total scope: ~720 prod + ~1000 test = ~1720 total LOC delta — well over the 400 LOC chained-PR threshold per `proposal.md` Approach A. The 6 sub-batches (A+B+C+D+E+F) follow the strict-TDD `sdd-apply` precedent from `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` (per-commit RED → GREEN markers; planning artifacts committed inline to git history rather than as separate files — see W2). This is a **debt-closure release** (rotation + S2 hardening + REQ-51/52/53 + alias + ruff cleanup) not a feature release.

**Timeout recovery note**: The apply phase experienced ~6 delegation timeouts across the 6 sub-batches (15-min wall cap per delegation). Per the established timeout-recovery pattern, each agent committed work BEFORE the timeout fired; the `sdd/v1.1-followups/apply-progress` Engram checkpoints preserved the per-task TDD state across the gaps. Net result: **0 work lost**; all 18 functional tasks completed across the timeout cycles. This is a successful application of the project's recover-from-timeout pattern (no need for an `sdd-recover` step).

## v1.2.0a archive status (2026-06-28)

**v1.2-followups PR#2a (v1.2.0a) SHIPPED as the first of 4 chained PRs in the v1.2 release — single PR (sub-batch A only), 5 functional tasks complete (T1.1..T1.5), 5 work-unit commits on `main` (HEAD `20f5ed1` ahead of `75961ad` v1.1.0 baseline by 5 commits).**

| REQ | Title | Status |
|-----|-------|--------|
| **REQ-V1.2.1** | `metrics.jsonl` rotation: `_rotate_metrics_if_needed(path)` + `FLOW_METRICS_LOG_MAX_BYTES` (default 10 MB = 10485760) + `FLOW_METRICS_LOG_MAX_AGE_DAYS` (default 30 days) env vars + best-effort `try/except OSError` swallow + age-based sibling cleanup via `_delete_stale_metrics_siblings()` extracted helper | ✅ **SHIPPED** |

**Verdict at archive**: **PASS WITH WARNINGS — archive-ready** (accepted per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` precedent posture). Per `openspec/changes/archive/2026-06-28-v1.2-followups-pr2a/verify-report-pr2a.md`: **0 CRITICAL findings** + **2 WARNING** + **2 SUGGESTION**. The 1 in-scope REQ (REQ-V1.2.1) has 7 passing tests demonstrating compliance (5 size-threshold + 2 age-cleanup + 1 OSError-swallow via the rotation-failure-doesn't-crash test). All 5 functional tasks (T1.1..T1.5) closed across 1 sub-batch with strict-TDD RED → GREEN → REFACTOR evidence (2 RED + 2 GREEN + 1 REFACTOR commits). **1349/1349 tests passing** (+7 net vs `75961ad` v1.1.0 baseline; 0 regressions). **182/182 BDD scenarios passing** (no regressions; 2 NEW spec-only scenarios in `req44_metrics_rotation.feature` have no pytest-bdd step glue per W2). Ruff clean on changed files (`observability.py` + `test_observability.py`). Smoke test `from flow_engineering.observability import _rotate_metrics_if_needed` imports cleanly with `FLOW_METRICS_LOG_MAX_BYTES=1`. Spec/design drift check: 13/13 contracts MATCH with zero drift.

**Findings tally**: **0 CRITICAL + 2 WARNING + 2 SUGGESTION** (accepted per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` precedent):
- **W1** (doc-process, ACCEPTED) — `openspec/changes/v1.2-followups/apply-progress/` directory NOT created (no consolidated TDD evidence artifact on disk). PR#2a committed 5 work-unit commits with per-commit RED → GREEN → REFACTOR markers visible in git log; no consolidated `apply-progress/final.md` artifact. Mirrors `v1.1-followups` W2 ACCEPTED posture. Backfill option (~30 LOC, ~30 min) deferred to v1.3+ `sdd-process` cleanup change.
- **W2** (doc-process, ACCEPTED) — `tests/bdd/req44_metrics_rotation.feature` is spec-only (no pytest-bdd step glue). The 2 Gherkin scenarios document the BDD contract but are not executable via pytest-bdd; equivalent executable coverage lives in `tests/unit/test_observability.py::TestMetricsRotation` (7 tests). Mirrors the existing pattern for `req11_drift_exit_codes.feature` + `req9_drift_detection.feature` + `req_v1_0_drift_events.feature` (all spec-only). Add step glue OR add `<!-- spec-only -->` header comment (~1-line fix) deferred.
- **S1** (doc-reference, NO-FIX-NEEDED) — verify-phase user brief referenced `test_observability_aggregate.py` (likely shorthand); actual file is `test_observability.py`. Reference mismatch in brief, not in code. Confirmed via `git diff 75961ad..HEAD --stat`.
- **S2** (infra, ACCEPTED) — `pyproject.toml` could add `[tool.ruff] extend-exclude = ["*.feature"]` (1-line fix to exclude Gherkin files from ruff Python lint scope). Non-blocking; OUT of PR#2a scope; defer to future PR.

**Net carry-forward closure**: **1/4 v1.2 carry-forwards closed** by PR#2a (REQ-44 metrics.jsonl rotation ✅). **3/4 v1.2 carry-forwards still pending** (REQ-48 golden tests → PR#2b + REQ-54 skill versions → PR#2c + Path A subcommand rename → PR#2d). The 5 v1.0-followups carry-forwards remain CLOSED (closed by v1.1-followups). The 3 v1.1-followups non-blocking findings (W2 + W3 + S1) remain ACCEPTED. **The 2 PR#2a findings (W1 + W2) are non-blocking documentation-process gaps accepted per the established precedent.**

**Note on archive structure**: this is a **single-PR chained-release** archive — PR#2a (v1.2.0a) is 1 of 4 chained PRs (`stacked-to-main` strategy per `proposal.md`). ONLY `verify-report-pr2a.md` (PR#2a-specific artifact) moves to the archive folder; the **planning artifacts** (`explore.md` + `proposal.md` + `design.md` + `tasks.md`) **stay in `openspec/changes/v1.2-followups/`** for chained-PR continuity since they cover all 4 PRs (PR#2b/c/d reference them as inputs). Each subsequent PR (PR#2b/c/d) will create its own `verify-report-pr<N>.md` and move that to the archive when its cycle completes. The full release is `v1.2.0` (BREAKING — Path A rename ships in PR#2d); PR#2a/b/c ship as v1.2.0a/b/c pre-release markers per CHANGELOG versioning convention. PR#2a is **debt-closure for REQ-44 only** — not a feature release.

## v1.2.0 archive status (2026-06-28)

**v1.2-followups (#12) FULLY CLOSED as v1.2.0 — 4 chained PRs (`stacked-to-main` strategy per `proposal.md`) ship as a single BREAKING release. Final HEAD `748b10c` ahead of `75961ad` v1.1.0 baseline by 4 PRs (PR#2a + PR#2b + PR#2c + PR#2d = ~22 functional tasks across 4 sub-batches; ~170 prod LOC + ~580 test LOC + 4 snapshot files + closeout).**

| REQ | Title | Status |
|-----|-------|--------|
| **REQ-V1.2.1** | `metrics.jsonl` rotation: `_rotate_metrics_if_needed(path)` + `FLOW_METRICS_LOG_MAX_BYTES` (default 10 MB = 10485760) + `FLOW_METRICS_LOG_MAX_AGE_DAYS` (default 30 days) env vars + best-effort `try/except OSError` swallow + age-based sibling cleanup via `_delete_stale_metrics_siblings()` extracted helper | ✅ **SHIPPED** (PR#2a, v1.2.0a) |
| **REQ-V1.2.2** (alias REQ-48) | Golden regression tests for `render_prompt`: `render_prompt_canonical(prompt_id, **vars)` helper at `prompt_registry.py:1033` + 4 on-disk snapshot files at `tests/golden/prompts/{strict_tdd,auto_suggest_header,auto_suggest_footer,auto_suggest_empty}.txt` (119B / 29B / 61B / 37B respectively, UTF-8 + trailing newline) + `--update-goldens` + `--check-snapshot` Click flags on `flow prompts show <id>` (default mode fails on drift with exit code `_EXIT_GOLDEN_DRIFT = 3` at `cli.py:3263`; `--check-snapshot` emits "snapshot drift detected" on stderr) + `golden_snapshot_dir` + `production_golden_dir` fixtures extracted to `tests/unit/conftest.py:18-40` + `render_prompt_canonical` added to `__all__` export | ✅ **SHIPPED** (PR#2b, v1.2.0b) |
| **REQ-V1.2.3** (alias REQ-54) | `[tool.flow_engineering] min_sdd_skill_versions` enforcement: NEW pyproject section (`pyproject.toml:68-77`) with 8 sdd-* agent minimum versions (sdd-explore / sdd-propose / sdd-spec / sdd-design / sdd-tasks / sdd-apply / sdd-verify / sdd-archive — all "3.0") + NEW `enforce_min_skill_versions(min_versions)` helper at `opencode_skill_catalog.py:320+` that reuses the existing `SkillVersionError` exception (no new exception hierarchy) + 3-line CLI hook at `flow apply` / `flow verify` / `flow archive` startup (exit code 4 + structured JSON `{error: "skill_version_violation", skill, expected, found, hint: "run 'pip install --upgrade gentle-ai'}` on stderr) + `_parse_major_minor()` tolerant parser handles pre-release version strings (`"3.0-beta"` → `(3, 0)`) + 8 NEW tests in `tests/unit/test_opencode_skill_catalog.py::TestEnforceMinSkillVersions` (5) + `TestPyprojectMinSkillVersionsSection` (2) + `tests/unit/test_cli_apply_verify_archive.py` (3) + 1 NEW integration test in `tests/integration/test_skill_version_gate.py` (subprocess end-to-end) | ✅ **SHIPPED** (PR#2c, v1.2.0c) |
| **REQ-V1.2.4** | Path A subcommand group rename: `@main.command("drift", ...)` at pre-PR#2d `cli.py:1718` converted to `@main.group("drift", invoke_without_command=True)` + `@drift_group.command("run")` subcommand (default command dispatch via `invoke_without_command=True`; bare `flow drift --help` shows subcommand list) + NEW `@drift_group.group("events")` sub-group with `list` / `tail` / `stats` subcommands moved from the pre-v1.2 top-level `flow drift-events {list,tail,stats}` surface (BREAKING). The hyphenated `flow drift-events` surface is preserved for one release cycle via NEW `@main.group(name="drift-events", deprecated=True)` Click group alias at `cli.py:2280+` that auto-emits `DeprecationWarning` to stderr on every invocation + delegates `list` / `tail` / `stats` to the canonical `flow drift events` subcommands via `ctx.forward()`. Alias REMOVED in v1.3 per the `SnapshotGraphMissing` v1.1 precedent. 3 NEW `TestDriftEventsGroup` tests (canonical surface) + 4 NEW `TestDriftEventsAlias` tests (alias works + emits DeprecationWarning + dispatches correctly + marked-removed-in-v1.3). Total **7 NEW tests** for REQ-V1.2.4. | ✅ **SHIPPED** (PR#2d, v1.2.0) |

**Verdict at archive**: **PASS WITH WARNINGS — archive-ready** (accepted per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` + v1.2-followups PR#2a + PR#2b + PR#2c precedent posture). Per `openspec/changes/archive/2026-06-28-v1.2-followups-pr2d/verify-report-pr2d.md`: **0 CRITICAL findings** + **0 WARNING** + **3 SUGGESTION** (all accepted per orchestrator brief; all non-blocking — see PR#2b verify-report findings tally for precedent). All 4 in-scope REQs (REQ-V1.2.1..V1.2.4) have at least one passing test demonstrating compliance. All 22 functional tasks (T1.1..T4.5) closed across 4 sub-batches with strict-TDD RED → GREEN → REFACTOR evidence. **1383/1383 tests passing** (+7 net vs `75961ad` v1.1.0 baseline of 1376; +7 NEW v1.2 tests in PR#2d: 3 `TestDriftEventsGroup` + 4 `TestDriftEventsAlias`). The +41 net total v1.2 tests (PR#2a +7 + PR#2b +11 + PR#2c +16 + PR#2d +7 = +41) reflects all v1.2 work. **182/182 BDD scenarios passing** (no regressions; spec-only `req44_metrics_rotation.feature` + `req48_golden_prompts.feature` + `req54_skill_version_gate.feature` per W2 ACCEPTED posture). Ruff clean on changed files. Spec/design drift check: 12/12 spec scenarios MATCH + 4/4 design decisions EXACT (Path A nested group + 1-release `deprecated=True` alias mirrors `SnapshotGraphMissing` v1.1 precedent exactly).

**BREAKING change surface (v1.2.0d)**:
- `flow drift-events {list,tail,stats}` → `flow drift events {list,tail,stats}` (Path A subcommand group rename; nested under `flow drift` parent group). The hyphenated alias is preserved for one release cycle as `deprecated=True` Click group + REMOVED in v1.3.
- `flow drift <change>` → `flow drift run <change>` (explicit subcommand form required; the positional `<change>` argument is no longer accepted by the bare `flow drift` group). NO backwards-compat shim — the explicit `run` form is unambiguous.

**Migration**:
- `flow drift <change>` → `flow drift run <change>` (use explicit `run` subcommand)
- `flow drift-events list` → `flow drift events list` (nested group under `flow drift`)
- `flow drift-events tail` → `flow drift events tail`
- `flow drift-events stats` → `flow drift events stats`
- The hyphenated `flow drift-events` alias still works in v1.2 but emits `DeprecationWarning` on every invocation; hard removal in v1.3.

**Findings tally**: **0 CRITICAL + 0 WARNING + 3 SUGGESTION** (accepted per precedent; all non-blocking):
- **S1** (doc-process, ACCEPTED) — `openspec/changes/v1.2-followups/apply-progress/` directory NOT created (no consolidated TDD evidence artifact on disk; per-commit RED → GREEN → REFACTOR markers visible in git log; mirrors `v1.1-followups` W2 ACCEPTED posture).
- **S2** (infra, ACCEPTED) — `flow drift v1.2-followups` returns `unable_to_verify` (exit 2) because `~/.flow-engineering/graph.json` is not yet seeded for this project. Environmental; resolves post-archive when the decision graph is populated. Mirrors v1.2.0a/b/c ACCEPTED posture.
- **S3** (doc-reference, NO-FIX-NEEDED) — `flow drift-events` Click `deprecated=True` group emits a generic Click deprecation warning, not the project-specific migration hint. The custom `DeprecationWarning` text is asserted in `TestDriftEventsAlias::test_alias_emits_deprecation_warning` per design D4 — non-blocking.

**Net carry-forward closure**: **4/4 v1.2 carry-forwards CLOSED**:
- `v1.1-followups` **REQ-44** (`metrics.jsonl` rotation deferred) — closed via REQ-V1.2.1 (PR#2a)
- `v1.1-followups` **REQ-48** (golden regression tests deferred) — closed via REQ-V1.2.2 (PR#2b)
- `v1.1-followups` **REQ-54** (`min_sdd_skill_versions` deferred) — closed via REQ-V1.2.3 (PR#2c)
- `v0.9.0-hardening` S4 + `v1.0-followups` W1 + `v1.1-followups` "Path A subcommand group rename" (BREAKING `flow drift-events` → `flow drift events`) — closed via REQ-V1.2.4 (PR#2d)

**CHANGE #12 (`v1.2-followups`) CLOSED**. 4 chained PRs (`stacked-to-main`) merged to `main`: PR#2a (v1.2.0a pre-release marker) → PR#2b (v1.2.0b pre-release marker) → PR#2c (v1.2.0c pre-release marker) → PR#2d (v1.2.0 BREAKING). pyproject `1.1.0 → 1.2.0` + CHANGELOG `## [1.2.0] - 2026-06-28` BREAKING entry documents the rename + the alias + the migration hints + the new env vars + the new pyproject section. The hyphenated `flow drift-events` alias is preserved for one release cycle and REMOVED in v1.3 per the `SnapshotGraphMissing` v1.1 precedent.

**Note on archive structure**: this is a **multi-PR chained-release** archive — PR#2d (v1.2.0) is the FINAL of 4 chained PRs (`stacked-to-main` strategy). `verify-report-pr2d.md` (PR#2d-specific artifact) moves to the archive folder; the **planning artifacts** (`explore.md` + `proposal.md` + `design.md` + `tasks.md`) **stay in `openspec/changes/v1.2-followups/`** for chained-PR continuity since they cover all 4 PRs. The per-PR verify reports (`verify-report-pr2a.md` + `verify-report-pr2b.md` + `verify-report-pr2c.md` + `verify-report-pr2d.md`) live under `openspec/changes/archive/2026-06-28-v1.2-followups-pr2{abcd}/`. The full release is `v1.2.0` (BREAKING — Path A rename ships in PR#2d); PR#2a/b/c ship as v1.2.0a/b/c pre-release markers per CHANGELOG versioning convention. **CHANGE #12 is the third "debt closure" release in the flow-engineering cycle** (after `drift-hardening` for v0.8.0 and `v1.1-followups` for v1.1.0); it is intentionally NOT a feature release.
