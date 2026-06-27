# Decision-Drift Capability Spec

## v0.8.0 migration note (REQ-56 W8 / REQ-57)

This capability spec was bootstrapped in v0.8.0 as part of the
`drift-hardening` cluster. The `decision-reality-drift` change shipped the
original REQ-9..16 contract in v0.3.0 but never created a corresponding
`openspec/specs/decision-drift/spec.md`; v0.8.0 retroactively establishes the
baseline so future deltas (e.g., per-finding graph_unavailable refinement,
cross-project drift federation, OTel push) extend this file rather than
forking the archived `decision-reality-drift` spec.

The v0.8.0 dataclass shape migration changes the public API:

- `Finding.decision_id: int` (was `str`); legacy numeric `str` callers
  use `Finding.from_legacy()` which emits `DeprecationWarning` and coerces
  via `int()`. Non-numeric `str` raises `ValueError`.
- `DriftReport.scanned_at: str` ISO 8601 UTC Z-suffixed (was `float` epoch);
  legacy `float` callers use `DriftReport.from_legacy()` which emits
  `DeprecationWarning` and coerces via `datetime.fromtimestamp(..., tz=UTC)`.
- `DriftReport.graph_unavailable: bool` retained as canonical; new
  `unable_reason: str | None` for structured diagnostics; legacy
  `unable_to_verify` kwarg mapped to `graph_unavailable` via `from_legacy`.
- `classify_binding(ref, graph_nodes)` is now 2-arg; legacy 3-arg callers
  use `classify_binding_legacy` which emits `DeprecationWarning`. The
  `current_id_map` lookup is now derived internally from `graph_nodes` in
  O(N) at function entry.

The 1-release shims (`Finding.from_legacy`, `DriftReport.from_legacy`,
`classify_binding_legacy`) are removed in v0.9.0.

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
- The v0.8.0 dataclass shape (int `decision_id`, ISO 8601 `scanned_at`,
  `graph_unavailable` + `unable_reason`, 2-arg `classify_binding`).
- The 1-release legacy shims (`Finding.from_legacy`,
  `DriftReport.from_legacy`, `classify_binding_legacy`).

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

### REQ-56 — Dataclass shape migration (v0.8.0)

The system SHALL migrate the `decision_drift` public dataclass shape:

- `Finding.decision_id: int` (was `str`); legacy callers use
  `Finding.from_legacy()` 1-release migration path.
- `DriftReport.scanned_at: str` ISO 8601 UTC Z-suffixed (was `float`
  epoch); legacy callers use `DriftReport.from_legacy()`.
- `DriftReport.graph_unavailable: bool` (canonical) + new
  `unable_reason: str | None`; legacy `unable_to_verify` kwarg mapped
  via `from_legacy()`.
- `classify_binding(ref, graph_nodes)` is 2-arg; legacy 3-arg callers
  use `classify_binding_legacy`.

All shims emit `DeprecationWarning` and are removed in v0.9.0.

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
    decision_id: int          # was: str
    binding: CodeRef
    drift_class: DriftClass
    detail: str

    @classmethod
    def from_legacy(cls, *, decision_id, binding, drift_class, detail=""):
        """1-release migration shim; removed in v0.9.0."""
        ...

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
    unable_reason: str | None = None    # NEW

    @classmethod
    def from_legacy(cls, *, change_name, scanned_at, graph_mtime=None,
                    unable_to_verify=None, ...):
        """1-release migration shim; removed in v0.9.0."""
        ...

def classify_binding(ref, graph_nodes) -> DriftClass:
    """2-arg primary; was 3-arg with separate current_id_map."""
    ...

def classify_binding_legacy(binding, current_nodes, current_id_map) -> DriftClass:
    """1-release 3-arg wrapper; removed in v0.9.0."""
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
