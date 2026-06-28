<!-- design.md: drift-hardening. Source: sdd-design sub-agent. -->
# Design: drift-hardening

> Mirror of Engram `sdd/drift-hardening/design` (topic_key upsert after file
> creation). Reference format mirrors
> [`openspec/changes/archive/2026-06-27-observability-pr1/design.md`](../archive/2026-06-27-observability-pr1/design.md)
> (D1–D12 + Open Questions table + code_refs block). All 10 open questions
> from proposal #223 §5 are resolved below. The Engram `code_refs` block is
> appended at file end so `flow inspect <change>` can render the binding
> surface.

```yaml
status: success
confidence: high
open_questions_resolved: 10/10
architecture_decisions: 12  # D1..D12
file_created: C:\dev\proyects\flow-engineering\openspec\changes\drift-hardening\design.md
next_recommended: sdd-tasks drift-hardening
```

## Goal

`drift-hardening` closes **8 documented WARNING/SUGGESTION carry-forwards**
(W4/W5/W6/W8/S2 from `decision-reality-drift` #2 + W23/W25/W26 from
`graph-snapshots` #5) that have accumulated since v0.5.0/v0.6.0 by shipping
**5 REQs (REQ-55..59) under a single PR with 4 sequential apply batches**.
The headline deliverable is the **21 new BDD scenarios across 6 feature files**
(REQ-57 / W4) that v0.3.0 promised but never shipped. A secondary deliverable
is the **v0.7.0 → v0.8.0 version bump** mandated by the W8 dataclass shape
migration (REQ-56) which IS a public-API break — the 1-release
`DeprecationWarning` aliases on `DriftReport.graph_unavailable` and
`Finding.__post_init__` str-coercion are the migration path. Coordination:
change #7 (`prompt-registry`) MUST archive before this change starts, to
preserve the REQ-55..59 numbering (REQ-45..54 are reserved for
`prompt-registry` per Engram #183 + #201).

## Architecture Overview

`drift-hardening` adds an **append-only JSONL event-log subsystem** on top of
the existing drift detection machinery that `decision-reality-drift` v0.3.0
shipped — and **migrates the drift detection dataclass shape** to match the
spec design that v0.3.0 archived but never landed. **Write-side grows
additively** (REQ-55 + REQ-56 + REQ-59); **read-side gains 6 NEW BDD
feature files** (REQ-57) translating existing unit-test contracts to Gherkin;
**spec/design reconciliation is doc-only** (REQ-58, 18 net LOC across 2
archived files, 0 production code change). The `record_drift_summary()` helper
that change #2 shipped is unchanged; a new `record_drift_event()` helper
mirrors it for the JSONL sink. The `Finding` / `DriftReport` dataclasses
get a 1-release `DeprecationWarning`-soft migration path so legacy callers
keep working until v1.0.

Five cooperating pieces (matches proposal §"Architecture (Approach A) pieces 1-5"):

1. **`drift_event_log` module** (NEW in `src/flow_engineering/`) —
   append-only JSONL writer at `~/.flow-engineering/drift_events.jsonl`
   with 10 MB rotation (mirrors `metrics.jsonl` policy from
   `observability.py:175`). Powers REQ-55 (W5 JSONL persistence + W6
   still-valid silence).
2. **`record_drift_event()` helper** (NEW in `observability.py`) —
   mirrors the 5 existing `record_*_summary` helpers (REQ-8/12/22/26
   precedent); emits a new `drift_event_log_total` counter + a
   `drift_event_log_bytes` gauge to track sink health.
3. **`DecisionDrift` dataclass shape sync** (MODIFY in `decision_drift.py`)
   — `Finding.decision_id: int` (was `str`), `DriftReport.scanned_at: str`
   (ISO 8601 UTC, was `float`), `DriftReport.unable_to_verify: bool` +
   `unable_reason: str | None` (renamed from `graph_unavailable`);
   `classify_binding(ref, graph_nodes)` 2-arg (was 3-arg).
   `@property graph_unavailable` retained for 1 release as a
   `DeprecationWarning`-emitting alias. Powers REQ-56 (W8).
4. **Snapshot spec/design field reconciliation** (MODIFY in archived
   `design.md` + `spec.md` only) — `SnapshotMeta.size_bytes` (rename from
   `file_size_bytes`) + document `pinned: bool` retention-pin field;
   `PruneResult.freed_bytes` (rename from `freed_bytes_estimate`).
   **0 production code change**. Powers REQ-58 (W25/W26).
5. **BDD coverage completion** (NEW 6 `.feature` files + step glue) —
   `tests/bdd/req10_drift_cli.feature` (9 scenarios),
   `req11_drift_exit.feature` (3), `req12_drift_counters.feature` (3),
   `req13_drift_metadata.feature` (3), `req14_drift_resilience.feature` (4),
   `req16_skill_prose.feature` (2). Strategy: **translate** existing
   unit-test contracts (`test_cli_drift.py`, `test_observability.py`,
   `test_engram_io_code_refs.py`) to Gherkin phrasing — no behavior change.
   Powers REQ-57 (W4).

```
   ┌────────────────────────┐
   │  flow drift scan <chg> │   CLI surface (REQ-9..11, REQ-14, REQ-15)
   │  flow drift write-back │
   │  flow drift daemon     │
   └─────────┬──────────────┘
             │
             ▼
   ┌────────────────────────────────────────────────────────┐
   │  src/flow_engineering/decision_drift.py  (REQ-56)      │
   │  Finding(decision_id: int, ...)                        │
   │  DriftReport(scanned_at: str ISO,                      │
   │              unable_to_verify: bool,                   │
   │              unable_reason: str | None,                │
   │              @property graph_unavailable → DeprecationWarning)
   │  classify_binding(ref, graph_nodes)  # 2-arg           │
   └──────┬──────────────────────────┬─────────────────────┘
          │                          │
          ▼                          ▼
   ┌────────────────────┐    ┌────────────────────────────────┐
   │ daemon.py          │    │  drift_event_log.py (NEW REQ-55)│
   │ handle_apply_      │───►│  record_drift_event(report)     │
   │  progress_event    │    │  iter_drift_events(...)         │
   │  + W6 silence      │    │  10MB rotation                  │
   │  + record_drift_   │    │  ~/.flow-engineering/           │
   │    event() wiring  │    │    drift_events.jsonl           │
   └──────┬─────────────┘    └─────────┬──────────────────────┘
          │                            │
          ▼                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │  observability.py                                       │
   │  record_drift_event() → metrics.jsonl                   │
   │   - drift_event_log_total{change=<chg>}                 │
   │   - drift_event_log_bytes                               │
   └─────────────────────────────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────────────────────────┐
   │  cli.py:_write_back_findings (REQ-59 S2)                 │
   │   - print "WARN: drift write-back skipped N             │
   │     non-int decision_ids" to stderr once per batch      │
   │     when skipped_total >= FLOW_DRIFT_SKIP_WARN_THRESHOLD│
   └─────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────┐
   │  Archived spec/design reconciliation (REQ-58, doc-only) │
   │  - archive/2026-06-26-decision-reality-drift/{spec,design}.md
   │    REQ-56 dataclass shape reconcile                      │
   │  - archive/2026-06-27-graph-snapshots/{spec,design}.md  │
   │    size_bytes + pinned + freed_bytes rename             │
   └─────────────────────────────────────────────────────────┘

   ┌─────────────────────────────────────────────────────────┐
   │  tests/bdd/ (REQ-57, NEW 6 feature files + step glue)   │
   │  req10_drift_cli.feature       (9 scenarios)            │
   │  req11_drift_exit.feature      (3 scenarios)            │
   │  req12_drift_counters.feature  (3 scenarios)            │
   │  req13_drift_metadata.feature  (3 scenarios)            │
   │  req14_drift_resilience.feature (4 scenarios)           │
   │  req16_skill_prose.feature     (2 scenarios)            │
   └─────────────────────────────────────────────────────────┘
```

Architecture seams respected (verified):
- `decision_drift.scan_change(change_name, *, graph_json_path, backend=None,
  include_obsolete=False, since=None, *, snap_id=None)` signature unchanged
  (REQ-9 close contract); only internal `Finding` / `DriftReport` field types
  change. Existing 947 tests pass.
- `observability.increment()`, `read_all()`, `record_drift_summary()` byte-
  identical (REQ-8 / REQ-12 close invariants); `record_drift_event()` is a
  pure addition.
- `cli.py:_write_back_findings` retains its silent-skip behavior; the new
  stderr WARN is **additive on top** (REQ-59 S2).
- `snapshot_manager.SnapshotMeta.size_bytes` / `SnapshotMeta.pinned` /
  `PruneResult.freed_bytes` impl unchanged (REQ-58 is doc-only).
- W23 `snapshot_pruned_total` ↔ `snapshot_prune_total` dual-name events
  in `metrics.jsonl` preserved as-is (REQ-59 W23 deprecation is CHANGELOG-
  doc only).

Files touched: **21** total (from explore #222) — 1 NEW prod module, 5 MODIFY
prod files, 1 NEW capability spec, 4 MODIFY archived spec/design files, 1
NEW unit test file, 5 MODIFY unit test files, 6 NEW BDD feature files, 1
MODIFY BDD feature file, 1 NEW MODIFY-or-split BDD step glue, 1 MODIFY
CHANGELOG, 1 MODIFY pyproject.toml, 6 MODIFY SKILL.md hook prose.

---

## Open Questions Resolution (all 10 from proposal §5)

### OQ-1: REQ-56 backward compat strategy (W8)

**Decision**: **Hard migration with 1-release `DeprecationWarning` aliases**
(explore recommendation option (a) refined). The `Finding.decision_id: int`
shape is the new primary; numeric `str` inputs are coerced via
`Finding.__post_init__` with `DeprecationWarning`. `DriftReport.scanned_at:
str` ISO 8601 is the new primary; legacy `float` epoch inputs are coerced
via the `DriftReport.from_scanned()` classmethod (no warning — it IS the
explicit migration path). `DriftReport.unable_to_verify: bool` +
`unable_reason: str | None` are the new primary fields; `@property
graph_unavailable` is retained on `DriftReport` for exactly 1 release
(v0.8.0) as a `DeprecationWarning`-emitting alias. `classify_binding(ref,
graph_nodes)` is now 2-arg — 3-arg callers get `TypeError`. All aliases
**removed in v1.0**.

**Rationale**: The project has 4 archived changes and **no third-party
consumers** per Engram #92 sdd-init (no PyPI package; `[project.optional-
dependencies] dev` is the only install entry). A hard break is acceptable
provided the migration path is explicit and versioned. The 1-release
`DeprecationWarning` aliases soft-cook the migration path so any future
internal consumer (e.g., a follow-up SDD tool that imports
`DriftReport.graph_unavailable`) sees the warning BEFORE the breaking
removal in v1.0. Soft migration (option b) would force 2-version type
coexistence (`int | str` typing) which is harder to maintain; dual
dataclasses (option c) would force import-site rewrites that the
`DeprecationWarning` path makes incremental.

**Alternatives considered**:
- (b) Soft migration: `Finding.decision_id: int | str` for 1 release with
  no dataclass rename. **Rejected**: typing cost (`int | str`); mypy strict
  gets noisier; no clear migration event.
- (c) Dual dataclasses (`Finding` + `FindingLegacy`). **Rejected**: forces
  import-site rewrites; the `DeprecationWarning` alias path is incremental.

**Affects**: REQ-56 (W8), REQ-15 (daemon seam `handle_apply_progress_event`
update for `unable_to_verify` rename).

### OQ-2: REQ-55 JSONL rotation threshold

**Decision**: **10 MB rotation threshold** mirroring `metrics.jsonl` policy
(REQ-44 from observability was deferred to v1.1 with the SAME 10 MB
threshold). Rotation is automatic on append when
`target.stat().st_size >= ROTATE_BYTES` (10 * 1024 * 1024); rotated files
are named `drift_events.<ISO-no-colons>.jsonl` (lexicographically sortable
by rotation time); the fresh `drift_events.jsonl` is created for the next
append. Threshold is **NOT** configurable via env var in v0.8.0; the
configurability hook (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES`) is deferred to
v1.1 alongside the metrics rotation follow-up.

**Rationale**: 10 MB matches `metrics.jsonl` precedent exactly — operators
who manage one rotation know how to manage the other. 5 MB would be more
aggressive but breaks the "single rotation policy" mental model; 50 MB
less aggressive but risks disk pressure on long-running watchers.
Lexicographically sortable ISO filenames mean a sorted `ls` of the
directory shows rotation chronology.

**Alternatives considered**:
- **5 MB**: rejected; diverges from `metrics.jsonl` policy.
- **50 MB**: rejected; disk pressure risk on long-running watchers
  (100 MB/year unrealistic).

**Affects**: REQ-55 (W5), REQ-44 follow-up (joint v1.1 rotation).

### OQ-3: REQ-55 still-valid silence scope (W6)

**Decision**: **Only suppress when `total == 0 AND not unable_to_verify`**
(explore recommendation). When `report.total == 0` AND
`report.unable_to_verify is False`, the outer `on_summary` stdout line is
**suppressed** (no `drift: <change> 0 findings (no classes)` spam on every
quiet tick). The JSONL append still happens (audit trail preserved). When
`unable_to_verify=True`, the summary line IS printed with the
`unable_reason` so the user knows the graph is unreachable. The spec
phrase "no event-log line on still-valid" is interpreted as "no stdout
line" (not "no JSONL line") — JSONL persists STILL_VALID is NOT
persisted (only non-still-valid findings are appended per
`record_drift_event()`'s contract).

**Rationale**: Silence the common-case noise (every quiet tick would
otherwise emit a summary line that operators ignore), but preserve the
informative case (graph_unavailable is rare and actionable). The
JSONL-as-audit-trail pattern means audit completeness is NEVER affected
by stdout silence — operators who want the full audit query the JSONL
directly.

**Alternatives considered**:
- **Broader silence** (`total == 0` regardless of `unable_to_verify`):
  rejected; the user should know the graph is unreachable.
- **Never silence**: rejected; spammy for the common quiet-tick case.

**Affects**: REQ-55 (W6), REQ-15 (daemon seam).

### OQ-4: REQ-56 migration timeline (single PR vs split)

**Decision**: **Same single PR as REQ-55/57/58/59** (proposal recommendation
A). The v0.8.0 version bump is a SINGLE event; the W8 dataclass migration,
the W4 BDD coverage (which exercises the new shape), and the W5/W6 JSONL
sink all land together. No follow-up "v0.8.0-migration" change is created.

**Rationale**: Splitting the dataclass migration from the BDD coverage
that exercises it forces the BDD PR to re-read the dataclass shape from
the migration PR — needless friction. Splitting the migration from the
JSONL sink forces the JSONL PR to handle BOTH legacy `graph_unavailable`
reads AND new `unable_to_verify` reads — context split. One version-bump
event = one migration guide = one PR review = cleaner archive phase.

**Alternatives considered**:
- **Separate v0.8.0-migration change**: rejected; two v0.8.0 entries OR a
  v0.7.1 + v0.8.0 sequence is more confusing than one v0.8.0 event.
- **Defer W8 to v1.0**: rejected; leaves the BIGGEST warning open.

**Affects**: REQ-56 (W8), REQ-57 (W4), REQ-55 (W5/W6), CHANGELOG v0.8.0
entry (single breaking-change entry).

### OQ-5: REQ-57 BDD scenario source (W4)

**Decision**: **TRANSLATE existing unit-test contracts to Gherkin**
(explore recommendation). The 21 new scenarios are a 1:1 translation of
existing unit-test contracts in:
- `tests/unit/test_cli_drift.py` (14 tests for REQ-10/11/14 CLI surface)
- `tests/unit/test_observability.py::TestRecordDriftSummary` (for REQ-12
  counter catalog)
- `tests/unit/test_engram_io_code_refs.py::TestUpdateObservationMetadata`
  (6 tests for REQ-13)
- The `sdd-verify` Step 6a SKILL.md grep check (for REQ-16)

No new behavior is introduced by the BDD scenarios; they assert the SAME
contracts the unit tests already cover, in business-domain Given/When/Then
phrasing (NOT unit-test fixture dict phrasing).

**Rationale**: The unit tests are the source of truth for v0.8.0's
behavior; BDD scenarios add a human-readable scenario description layer
that operators and stakeholders can read without parsing Python. The
quality gate (each scenario MUST use business-domain phrasing per Risk 4
in proposal #223) prevents the worst failure mode (tautological BDD
scenarios that just `@scenario`-bind a unit test without rephrasing).

**Alternatives considered**:
- **Write fresh business-domain scenarios**: rejected; risks introducing
  contract drift between BDD and unit tests (BDD would test imagined
  behavior, unit tests would test actual behavior).

**Affects**: REQ-57 (W4), all 6 NEW `.feature` files, BDD step glue.

### OQ-6: REQ-58 spec reconciliation scope

**Decision**: **Archived spec/design only** (proposal recommendation).
Per SDD governance (per Engram #92 sdd-init + archive precedent from
changes #1..#6), archived specs in `openspec/changes/archive/<date>-<name>/`
are the LONG-TERM source of truth for shipped REQs; live changes are
append-only and CANNOT modify a shipped change's spec. The 2 archived
files (`decision-reality-drift/spec.md` + `design.md` and
`graph-snapshots/spec.md` + `design.md`) get the field-name corrections
as plain text edits. The live `openspec/specs/` baseline (which already
has `openspec/specs/observability/spec.md` from change #6) is unaffected
by REQ-58.

**Rationale**: Reopening a shipped change's spec.md to edit a field name
violates the SDD governance rule (archived = immutable except for carry-
forward resolution which is what this change IS). Live `openspec/specs/`
is the capability-level catalog and would only document REQ-55..59 (the
NEW additions), NOT retroactively edit the snapshot spec/design that
already shipped in v0.6.0.

**Alternatives considered**:
- **Also update live `openspec/specs/` retroactively**: rejected; live
  specs are append-only for shipped changes; the bootstrap pattern from
  observability #6 explicitly establishes this rule.

**Affects**: REQ-58 (W25/W26), 4 MODIFY archived spec/design files
(`openspec/changes/archive/2026-06-26-decision-reality-drift/{spec,design}.md`
+ `openspec/changes/archive/2026-06-27-graph-snapshots/{spec,design}.md`).

### OQ-7: REQ-59 W23 deprecation note placement

**Decision**: **CHANGELOG-only** (proposal recommendation). The CHANGELOG
v0.6.0 Notes section (entry added in Batch B per W23 ownership) gets a
3-line note documenting the `snapshot_pruned_total` ↔ `snapshot_prune_total`
dual-name coexistence and recommending REQ-37's `--domain snapshot` filter
(which matches BOTH names by `snapshot_` prefix). **NO runtime WARN log**
when reading old metric names — the JSONL sink is read-only and dropping
data on startup (the FALLBACK option) would lose audit trail.

**Rationale**: Runtime WARN on `flow metrics` invocation would be noisy
on every invocation (operators don't want a stderr notice on every
metrics read). CHANGELOG-only preserves the audit trail and points
operators at the existing `--domain` filter. If a downstream consumer
materializes (e.g., a dashboard scraping `metrics.jsonl`), revisit as a
REQ-59 follow-up — but no consumer exists yet.

**Alternatives considered**:
- **Runtime WARN on `flow metrics` startup**: rejected; noisy on every
  invocation; preserves data but operator UX cost is high.
- **One-time migration on startup**: rejected; loses audit trail; the
  user's existing `metrics.jsonl` is treated as immutable.

**Affects**: REQ-59 (W23), CHANGELOG v0.6.0 Notes section (Batch B).

### OQ-8: REQ-59 S2 stderr WARN cadence

**Decision**: **Once per batch with threshold** (proposal recommendation).
At the end of `_write_back_findings(report)`, when
`skipped_total >= FLOW_DRIFT_SKIP_WARN_THRESHOLD` (default 3; int parse
from env var; on parse error fall back to 3), print
`print(f"WARN: drift write-back skipped {skipped_total} non-int
decision_ids", file=sys.stderr)` ONCE per batch (NOT per skipped row).
The threshold is tunable: `0` means WARN every batch with `skipped_total >
0`; `-1` means WARN never; positive integer means WARN when `skipped_total
>= N`.

**Rationale**: Per-row WARN would be noisy for batches with sporadic
skips (e.g., 1 non-int out of 100 findings); per-batch with a default
threshold of 3 matches the spec phrasing "user should notice skipped
writebacks" without spamming. Tunable env var lets operators dial
sensitivity per their workflow.

**Alternatives considered**:
- **Once per skipped row**: rejected; noisy for batches with sporadic
  skips; the batch-summary line is the right cadence.
- **Always WARN (no threshold)**: rejected; noisy for clean batches with
  0 skips (already handled by the `>= threshold` check).

**Affects**: REQ-59 (S2), `cli.py:_write_back_findings`.

### OQ-9: REQ-55 read-side surface (`flow drift events` CLI)

**Decision**: **DEFER to v1.0 / "drift-events-dashboard" follow-up**.
REQ-55 v0.8.0 ships only the WRITE side (append to JSONL via
`record_drift_event()`). The READ side (`flow drift events [--since]
[--change] [--class]`) is deferred to a follow-up change that can
also bring the v0.8.0 read-side UX up to par with `flow metrics summary`
(REQ-35 from observability). Operators who want to read the JSONL in
v0.8.0 use `cat ~/.flow-engineering/drift_events.jsonl | jq` or query the
`drift_event_log_*` counters via `flow metrics --domain=drift`.

**Rationale**: Read-side is a UI convenience; the audit trail is fully
accessible via direct file read. Deferring the read-side avoids scope
creep (the proposal already estimates ~5.5h end-to-end; adding a read CLI
adds another 1-2h and increases review surface). The v1.0 follow-up can
also add `--format=prometheus` parity with observability.

**Alternatives considered**:
- **Ship `flow drift events` in same PR**: rejected; scope creep;
  v0.8.0 priority is closing the 8 carry-forwards, not adding new UX.

**Affects**: REQ-55 (W5) write-side only; `flow drift events` deferred.

### OQ-10: REQ-56 `classify_binding` arg-list compat

**Decision**: **Clean 2-arg break** (proposal recommendation). New
signature is `classify_binding(ref, graph_nodes)` (2 args);
`current_id_map` is derived INSIDE the function from
`{node.id: (node.file, node.line, node.label) for node in graph_nodes}`
(now that `graph_nodes` is a richer object per D11 thread-safety
rationale below). 3-arg callers get `TypeError`. **No optional 3rd-arg
compat**.

**Rationale**: `current_id_map` was an implementation detail leaked into
the public API; it can be derived from `graph_nodes` in O(N) at function
entry. No documented external caller passes 3 args; verified via grep on
`tests/` + `openspec/` + `src/` (3-arg callers only in the implementation
of `scan_change` itself, which gets refactored). The TypeError is the
clear migration signal — soft-compat (optional 3rd arg) would silently
accept the old shape and mask migration errors.

**Alternatives considered**:
- **Optional 3rd arg (`current_id_map: dict | None = None`) for 1-release
  compat**: rejected; silently accepts the old shape; no clear migration
  signal.

**Affects**: REQ-56 (W8), `classify_binding` signature change at
`decision_drift.py:84`.

---

## Architecture Decisions (D1..D12)

### D1: Module layout — where do the new helpers live?

**Decision**: **1 NEW module (`drift_event_log.py`) + extend 4 existing
modules** (`decision_drift.py`, `daemon.py`, `cli.py`, `observability.py`).
NO new package, NO class wrapper. The new `record_drift_event()` helper
in `observability.py` mirrors the 5 existing `record_*_summary` helpers;
the new `drift_event_log.py` module is a thin sink facade over
`~/.flow-engineering/drift_events.jsonl`. Existing modules stay
single-file; the dataclass migration is a per-field edit on
`decision_drift.py`.

**Rationale**: Mirrors observability D1 — single-file extend pattern +
1 NEW module. The 5 record helpers in `observability.py` are all
top-level functions (`record_backfill_coverage`, `record_drift_summary`,
`record_vector_summary`, `record_federated_summary`,
`record_snapshot_event`); the new `record_drift_event()` joins them.
Splitting into `drift_event_log_io.py` + `drift_event_log_format.py`
would force 1-direction imports for a 150 LOC module — ceremony
without payoff at this scale.

**Trade-offs**:
- ✅ Pro: minimum new files; reuse of `observability.increment()` for
  counter emission; mirrors observability D1.
- ❌ Con: `decision_drift.py` grows ~60 LOC delta (4 dataclass field
  corrections + 1 `@property` alias + 1 classmethod).

**Affects**: REQ-55 (NEW `drift_event_log.py`), REQ-56 (MODIFY
`decision_drift.py`), REQ-55 (MODIFY `daemon.py` + `observability.py` +
`cli.py`).

**Implementation note**: `drift_event_log.py` should import
`observability.increment()` (already imported by `decision_drift.py`)
for counter emission; this is a leaf dependency (no cycle).

### D2: W8 backward compat strategy — hard migration with 1-release aliases

**Decision**: **Hard migration + 1-release `DeprecationWarning` aliases**
for legacy str `decision_id`, legacy float `scanned_at`, legacy
`graph_unavailable` access, and legacy 3-arg `classify_binding`. All
aliases removed in v1.0.

**Rationale**: See OQ-1 detailed rationale. The 1-release alias path is
incremental (no import-site rewrites required in v0.8.0) and explicit
(`DeprecationWarning` tells callers "update before v1.0"). Hard break
at v1.0 is the unambiguous migration event.

**Trade-offs**:
- ✅ Pro: clean migration signal; v1.0 reverts the alias machinery;
  matches SemVer for the public API break.
- ❌ Con: 1-release `DeprecationWarning` is a maintenance cost
  (`__post_init__` + `@property` + `from_scanned()` all retained until
  v1.0).

**Affects**: REQ-56 (W8), v0.8.0 version bump, CHANGELOG `BREAKING:`
section.

**Implementation note**: `Finding.__post_init__` accepts legacy numeric
`str` inputs and coerces via `int()` with `DeprecationWarning`.
`DriftReport.from_scanned()` accepts legacy `float` epoch inputs and
coerces via `datetime.fromtimestamp(..., tz=UTC).strftime(...)` (no
warning — it IS the explicit migration path). `@property graph_unavailable`
emits `DeprecationWarning` and returns `unable_to_verify`.

### D3: W5 JSONL rotation policy

**Decision**: **10 MB rotation threshold** mirroring `metrics.jsonl`
policy. Rotation is automatic on append; rotated files named
`drift_events.<ISO-no-colons>.jsonl`. Threshold NOT configurable in
v0.8.0 (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var deferred to v1.1
alongside `FLOW_METRICS_MAX_BYTES`).

**Rationale**: See OQ-2 detailed rationale. Same threshold as
`metrics.jsonl` means operators manage one rotation policy. Lex
sortable ISO filenames mean rotation chronology is visible via `ls`.

**Trade-offs**:
- ✅ Pro: same precedent as `metrics.jsonl`; predictable disk usage;
  rotation chronology via lex sort.
- ❌ Con: hardcoded threshold is inflexible (env var deferred).

**Affects**: REQ-55 (W5), REQ-44 follow-up (joint v1.1 rotation).

**Implementation note**: `_rotate_if_needed(path)` checks
`path.stat().st_size >= ROTATE_BYTES`; on threshold, renames current
file to `drift_events.<stamp>.jsonl` (stamp is `_utc_iso()` with `:`
stripped for filesystem safety) and creates fresh `drift_events.jsonl`
on next append.

### D4: W6 silence scope — only suppress when total == 0 AND not unable_to_verify

**Decision**: **Suppress outer `on_summary` stdout line when
`report.total == 0 AND not report.unable_to_verify`**. Preserve the
summary line when `unable_to_verify=True` (with `unable_reason` so the
user knows the graph is unreachable). The JSONL append is preserved
in both cases (audit trail completeness).

**Rationale**: See OQ-3 detailed rationale. Common-case noise
suppression with informative-case preservation.

**Trade-offs**:
- ✅ Pro: quiet ticks don't spam; graph-unavailable stays visible.
- ❌ Con: 1 extra conditional in `handle_apply_progress_event` (~5 LOC).

**Affects**: REQ-55 (W6), REQ-15 (daemon seam).

**Implementation note**: The `on_summary` callback invocation is gated
by `if report.total > 0 or report.unable_to_verify:` — when both are
false (still-valid, graph available), the line is suppressed. The
JSONL append via `record_drift_event(report)` is unconditional
(best-effort, wrapped in `try/except OSError`).

### D5: REQ-58 BDD sourcing — translate from existing unit tests

**Decision**: **TRANSLATE existing unit-test contracts to Gherkin**
(proposal recommendation). No new behavior introduced by the 21
scenarios; BDD is a human-readable scenario description layer on top
of the unit-test contracts.

**Rationale**: See OQ-5 detailed rationale. Unit tests are the source
of truth for v0.8.0's behavior; BDD adds scenario-description value.

**Trade-offs**:
- ✅ Pro: contract drift impossible (BDD mirrors unit tests); quality
  gate prevents tautological phrasing.
- ❌ Con: 21 scenarios × ~30 LOC = ~600 LOC BDD scaffolding overhead
  (already accounted in the ×6 TDD multiplier).

**Affects**: REQ-57 (W4), all 6 NEW `.feature` files, BDD step glue.

**Implementation note**: Each BDD scenario uses business-domain
Given/When/Then phrasing (NOT unit-test fixture dict phrasing). The
step glue translates business-domain language to existing pytest
fixtures (`@scenario` + `@given`/`@when`/`@then`).

### D6: REQ-59 spec reconciliation scope — archived only

**Decision**: **Archived spec/design only** (proposal recommendation).
Per SDD governance, archived specs are the LONG-TERM source of truth
for shipped REQs; live changes are append-only. The 2 archived files
(`decision-reality-drift/{spec,design}.md` +
`graph-snapshots/{spec,design}.md`) get the field-name corrections
as plain text edits.

**Rationale**: See OQ-6 detailed rationale. Reopening shipped specs
violates the SDD governance rule.

**Trade-offs**:
- ✅ Pro: clean governance; live `openspec/specs/` baseline unaffected
  (the bootstrap pattern from observability #6 is preserved).
- ❌ Con: 4 archived files touched (vs 2 live files); reviewers must
  understand the archive-edits-are-allowed-for-carry-forward-resolution
  rule.

**Affects**: REQ-58 (W25/W26), 4 MODIFY archived spec/design files.

### D7: W23 deprecation note placement — CHANGELOG only

**Decision**: **CHANGELOG v0.6.0 Notes section only**. No runtime WARN
log when reading old metric names; no startup migration that drops
events.

**Rationale**: See OQ-7 detailed rationale. Runtime WARN would be noisy;
startup migration would lose audit trail.

**Trade-offs**:
- ✅ Pro: no operator UX cost; audit trail preserved; documents the
  REQ-37 `--domain snapshot` filter recommendation.
- ❌ Con: silent coexistence — operators must read CHANGELOG to know.

**Affects**: REQ-59 (W23), CHANGELOG v0.6.0 Notes section (Batch B).

**Implementation note**: 3-line CHANGELOG entry: "Note: legacy
`snapshot_pruned_total` events from v0.5.0 coexist with renamed
`snapshot_prune_total` (v0.6.0 wire-format). For domain-filtered
queries, use `flow metrics --domain=snapshot` which matches both
names by `snapshot_` prefix. To migrate, `sed -i 's/snapshot_pruned_total/
snapshot_prune_total/g' ~/.flow-engineering/metrics.jsonl`."

### D8: S2 stderr WARN cadence — once per batch with threshold

**Decision**: **Once per batch with default threshold 3** (proposal
recommendation). Tunable via `FLOW_DRIFT_SKIP_WARN_THRESHOLD` env var
(int parse; on parse error fall back to 3). Special values: `0` = WARN
every batch with `skipped_total > 0`; `-1` = WARN never.

**Rationale**: See OQ-8 detailed rationale. Per-batch with threshold
matches spec phrasing; tunable env var lets operators dial sensitivity.

**Trade-offs**:
- ✅ Pro: not noisy for sporadic skips; threshold is operator-tunable;
  preserves the existing silent-skip behavior.
- ❌ Con: 1 extra env-var parse + 1 conditional in `_write_back_findings`
  (~10 LOC).

**Affects**: REQ-59 (S2), `cli.py:_write_back_findings`.

**Implementation note**: At end of `_write_back_findings`, compute
`skipped_total = sum(1 for f in report.findings if not
isinstance(int(f.decision_id), int) — note: post-REQ-56 this is
unreachable for numeric str inputs via `__post_init__` coercion; only
truly non-numeric str inputs reach this skip path`. When
`skipped_total >= threshold`, print `WARN: drift write-back skipped
{N} non-int decision_ids` to `sys.stderr` ONCE.

### D9: v0.8.0 bump rationale

**Decision**: **Bump `pyproject.toml` 0.7.0 → 0.8.0** (SemVer minor
for the public API break). CHANGELOG v0.8.0 entry lists all 5 REQs +
`BREAKING:` section noting the dataclass shape change.

**Rationale**: Per SemVer, breaking public API changes bump the MINOR
version for 0.y.z (where 0.y is the "development" series). The
`Finding`/`DriftReport`/`classify_binding` dataclass shape change IS a
public API break (the dataclasses are imported across daemon/CLI seams
and any future third-party caller would import them). The 1-release
`DeprecationWarning` aliases soften the migration but the version bump
is the unambiguous signal.

**Trade-offs**:
- ✅ Pro: SemVer-clean; one migration event; CHANGELOG `BREAKING:`
  section is the authoritative migration guide.
- ❌ Con: 1 more major version step than a patch bump; users must
  read the BREAKING section.

**Affects**: REQ-56 (W8), `pyproject.toml` version, CHANGELOG v0.8.0
entry.

**Implementation note**: `version = "0.8.0"` in `pyproject.toml:3`;
CHANGELOG entry lists all 5 REQs (REQ-55..59) with `BREAKING:` section
for REQ-56.

### D10: BDD step glue module size — split per REQ

**Decision**: **SPLIT per REQ into 6 step glue files**
(`test_req10_steps.py`, `test_req11_steps.py`, ...). Mirrors the
`test_graph_snapshots_steps.py` precedent (which is already
multi-feature). Avoids the >1 000 LOC review-awkward threshold for
the consolidated `test_decision_reality_drift_steps.py` file.

**Rationale**: 21 scenarios × ~20 step defs per file × ~30 LOC/step =
~600 LOC added to the consolidated file; that pushes it past 1 000
LOC (current size is ~400 LOC from change #2). Per-REQ splitting
keeps each file ≤200 LOC and review-tractable.

**Trade-offs**:
- ✅ Pro: each step file ≤200 LOC; mirrors graph-snapshots precedent;
  step defs are co-located with their feature files.
- ❌ Con: 6 NEW step files (vs 1 MODIFY); more file-management overhead.

**Affects**: REQ-57 (W4), 6 NEW step glue files (or modify the
existing `test_decision_reality_drift_steps.py` for REQ-15 daemon
extensions only).

**Implementation note**: Each `.feature` file pairs with a
`test_req<N>_<name>_steps.py` glue file. The existing
`test_decision_reality_drift_steps.py` is extended (not split) for
REQ-15 daemon JSONL scenarios (2 new scenarios).

### D11: REQ-55 JSONL writer thread safety

**Decision**: **Single-threaded assumption** — the daemon is a
single-process Python watchdog loop; no concurrent writers. The JSONL
writer uses `path.open("a", encoding="utf-8")` which is NOT thread-safe
across processes but IS safe within a single process (the file handle
is exclusive to the writer). No file lock; no OS-level atomicity
helpers.

**Rationale**: The `flow drift daemon` is a single Python process
launched via `flow watch <change>` (REQ-15); the
`handle_apply_progress_event` callback runs serially in the watchdog
loop. Concurrent writers would require multi-process daemonization,
which the project doesn't have (no `--workers` flag, no fork). The
`record_drift_event()` call is wrapped in `try/except OSError` for
defense in depth (disk full, permission denied) — but no lock.

**Trade-offs**:
- ✅ Pro: simplest impl (no lock contention, no `fcntl.flock` /
  `msvcrt.locking` portability concerns); matches `metrics.jsonl`
  precedent.
- ❌ Con: NOT safe if a future change introduces a multi-process
  daemon — would need a file lock. The risk is documented in the
  `record_drift_event` docstring.

**Affects**: REQ-55 (W5), `drift_event_log.py:record_drift_event()`.

**Implementation note**: `with target.open("a", encoding="utf-8") as
fh: fh.write(line + "\n")` — single-threaded, no flush needed (Python
default line-buffering on text mode). On `OSError`, log to stderr via
`print(..., file=sys.stderr)` and return without raising (matches
`observability.increment()` best-effort policy).

### D12: Apply batch sequencing — A (foundation) → B (impl) → C (BDD) → D (closeout)

**Decision**: **4 sequential apply batches** with strict ordering:

1. **Batch A — Foundation** (REQ-56 + REQ-58, ~60 min): dataclass
   shape migration + 4 archived spec/design edits. **No new
   functionality**; pure shape sync. Hardest unit tests in this
   batch (legacy compat aliases).
2. **Batch B — Implementation** (REQ-55 + REQ-59, ~60 min): NEW
   `drift_event_log.py` + `record_drift_event()` wiring + W6
   silence rule + S2 stderr WARN + CHANGELOG v0.6.0 Notes entry
   for W23. **Adds 2 NEW counters + 1 NEW module + 1 stderr WARN**.
3. **Batch C — BDD coverage** (REQ-57, ~60 min): 6 NEW
   `.feature` files + 6 NEW step glue files + 2 new scenarios in
   `req15_drift_daemon.feature`. **Tests the foundation** (REQ-56
   shape) and **implementation** (REQ-55/59).
4. **Batch D — Closeout** (~30 min): CHANGELOG v0.8.0 entry +
   `pyproject.toml` version bump + 6 SKILL.md hook updates +
   final `sdd-verify` pass.

**Rationale**: The 4-batch order matches the proposal's recommended
sequence. A→B ordering matters because B depends on the post-REQ-56
dataclass shape (the JSONL sink consumes the `unable_to_verify` field).
A→C ordering matters because the BDD scenarios exercise the new
dataclass shape. B→C ordering matters because the BDD daemon scenarios
exercise the JSONL sink. D is last because it depends on all 3 prior
batches being GREEN.

**Trade-offs**:
- ✅ Pro: each batch has independent acceptance criteria (BDD-pass,
  unit-pass, ruff-clean); reviewers can read batch-by-batch not
  PR-as-blob; per-commit work-unit splits per `work-unit-commits`
  skill (4-6 commits each ≤400 LOC).
- ❌ Con: longer wall time (~3.5h apply + ~30min verify + ~15min
  archive = ~5h total); cross-batch merge-base discipline required
  (each batch rebases on the prior batch's merge commit).

**Affects**: All 5 REQs (REQ-55..59), CHANGELOG v0.8.0 + v0.6.0 Notes,
pyproject.toml version bump, 6 SKILL.md updates.

**Implementation note**: Per-batch commit splits (mirror observability
PR#1 D12):

- **Batch A commits** (target ≤400 LOC each):
  1. `feat(decision_drift): Finding.decision_id int + __post_init__ coercion` (~50 prod + 100 test = 150 LOC) — REQ-56 W8 part 1
  2. `feat(decision_drift): DriftReport.scanned_at str ISO + unable_to_verify + from_scanned() classmethod + @property graph_unavailable alias` (~80 prod + 150 test = 230 LOC) — REQ-56 W8 part 2
  3. `feat(decision_drift): classify_binding 2-arg signature` (~30 prod + 80 test = 110 LOC) — REQ-56 W8 part 3
  4. `docs(archive): reconcile dataclass type signatures in archived spec/design (REQ-56) + snapshot field reconciliation (REQ-58)` (~25 docs LOC) — REQ-56 + REQ-58 reconciliation

- **Batch B commits** (target ≤400 LOC each):
  1. `feat(drift_event_log): NEW module — record_drift_event + iter_drift_events + 10MB rotation` (~150 prod + 180 test = 330 LOC) — REQ-55 W5
  2. `feat(observability): record_drift_event() helper + 2 catalog entries (drift_event_log_total + drift_event_log_bytes)` (~15 prod + 30 test = 45 LOC) — REQ-55 W5 catalog
  3. `feat(daemon): wire record_drift_event + W6 still-valid silence rule` (~30 prod + 40 test = 70 LOC) — REQ-55 W6 + W5 wiring
  4. `feat(cli): --drift-event-log[=<path>] flag + --no-drift-event-log opt-out + S2 stderr WARN in _write_back_findings` (~40 prod + 50 test = 90 LOC) — REQ-55 W5 CLI + REQ-59 S2
  5. `docs(changelog): v0.6.0 Notes section for W23 dual-name coexistence + REQ-37 filter recommendation` (~15 docs LOC) — REQ-59 W23

- **Batch C commits** (target ≤400 LOC each):
  1. `test(bdd): req10_drift_cli.feature (9 scenarios) + test_req10_drift_cli_steps.py glue` (~250 test) — REQ-57 W4 part 1
  2. `test(bdd): req11_drift_exit.feature (3) + req12_drift_counters.feature (3) + test glue` (~180 test) — REQ-57 W4 part 2
  3. `test(bdd): req13_drift_metadata.feature (3) + req14_drift_resilience.feature (4) + req16_skill_prose.feature (2) + test glue` (~270 test) — REQ-57 W4 part 3
  4. `test(bdd): extend req15_drift_daemon.feature with 2 JSONL event-log scenarios + extend test_decision_reality_drift_steps.py` (~80 test) — REQ-55 W5 BDD

- **Batch D commits** (target ≤400 LOC):
  1. `docs(changelog): v0.8.0 entry listing REQ-55..59 + BREAKING section` (~25 docs LOC) — final
  2. `chore(pyproject): version 0.7.0 → 0.8.0` (~1 LOC) — final
  3. `docs(skills): drift-hardening hook prose in 6 sdd-* SKILL.md files` (~80 docs LOC) — final

---

## Module/File Layout

### New files (~360 LOC production + ~3 100 LOC test)

| File | LOC prod | LOC test | Purpose |
|---|---|---|---|
| `src/flow_engineering/drift_event_log.py` | ~150 | — | REQ-55 JSONL writer module: `record_drift_event(report)` + `iter_drift_events(*, since_iso, change)` + `DEFAULT_PATH` + `ROTATE_BYTES` + `_utc_iso()` + `_rotate_if_needed()` helpers. Mirrors `metrics.jsonl` policy from observability. |
| `openspec/specs/drift-hardening/spec.md` | ~250 | — | NEW capability spec cataloging REQ-55..59 with all 21 BDD scenarios + dataclass shape contract + counter catalog. Bootstraps the `drift-hardening` capability entry in `openspec/specs/`. |
| `tests/unit/test_drift_event_log.py` | — | ~180 | REQ-55 JSONL writer unit tests: rotation at 10MB, append idempotency, schema validation (`{ts, change, decision_id, binding_id, class, detected_at}`), counter increment, `try/except OSError` disk-full path, `iter_drift_events` filter combinations. |
| `tests/bdd/req10_drift_cli.feature` | — | ~250 | REQ-57 9 BDD scenarios for `flow drift scan <change>` CLI surface (`--json`, `--include-obsolete`, `--since`, `--write-back`, `--graph-json` flags, exit codes). |
| `tests/bdd/req11_drift_exit.feature` | — | ~90 | REQ-57 3 BDD scenarios for exit-code semantics (0 still-valid, 1 stale, 2 unable_to_verify). |
| `tests/bdd/req12_drift_counters.feature` | — | ~90 | REQ-57 3 BDD scenarios for the 8 `drift_*_total` counters via `record_drift_summary()`. |
| `tests/bdd/req13_drift_metadata.feature` | — | ~90 | REQ-57 3 BDD scenarios for `update_observation_metadata()` helper. |
| `tests/bdd/req14_drift_resilience.feature` | — | ~120 | REQ-57 4 BDD scenarios for graph_unavailable + timeout + retry + per-row isolation behavior. |
| `tests/bdd/req16_skill_prose.feature` | — | ~60 | REQ-57 2 BDD scenarios for the runtime SKILL.md grep check (REQ-16). |
| `tests/bdd/test_req10_drift_cli_steps.py` | — | ~150 | Step glue for `req10_drift_cli.feature` (per D10 split). |
| `tests/bdd/test_req11_drift_exit_steps.py` | — | ~80 | Step glue for `req11_drift_exit.feature`. |
| `tests/bdd/test_req12_drift_counters_steps.py` | — | ~80 | Step glue for `req12_drift_counters.feature`. |
| `tests/bdd/test_req13_drift_metadata_steps.py` | — | ~80 | Step glue for `req13_drift_metadata.feature`. |
| `tests/bdd/test_req14_drift_resilience_steps.py` | — | ~100 | Step glue for `req14_drift_resilience.feature`. |
| `tests/bdd/test_req16_skill_prose_steps.py` | — | ~60 | Step glue for `req16_skill_prose.feature`. |

### Modified files (~250 LOC delta production + ~200 LOC delta test + ~80 LOC archived docs + 60 LOC meta)

| File | LOC delta | Change |
|---|---|---|
| `src/flow_engineering/decision_drift.py` | +80 / -20 | REQ-56: `Finding.decision_id: int` + `__post_init__` coercion; `DriftReport.scanned_at: str` ISO; `unable_to_verify: bool` + `unable_reason: str | None`; `@property graph_unavailable` alias; `from_scanned()` classmethod; `classify_binding(ref, graph_nodes)` 2-arg signature. |
| `src/flow_engineering/daemon.py` | +30 / -10 | REQ-55: wire `record_drift_event` into `handle_apply_progress_event`; W6 still-valid silence rule in outer summary; `--drift-event-log` flag handling. |
| `src/flow_engineering/cli.py` | +40 / -5 | REQ-59 S2 stderr WARN in `_write_back_findings`; REQ-56 minor type-cast updates for the dataclass rename; REQ-55 `--drift-event-log[=<path>]` flag on `flow drift daemon` + `--no-drift-event-log` opt-out. |
| `src/flow_engineering/observability.py` | +15 | REQ-55: `record_drift_event()` helper + 2 catalog entries (`drift_event_log_total` counter + `drift_event_log_bytes` gauge). |
| `src/flow_engineering/snapshot_manager.py` | 0 | REQ-58 is spec/design-only; `size_bytes` + `pinned` + `freed_bytes` already correct in impl. |
| `tests/unit/test_decision_drift.py` | +30 | REQ-56: dataclass shape round-trip + `DeprecationWarning` capture tests for `decision_id` + `scanned_at` + `graph_unavailable` + `classify_binding` 2-arg + 3-arg TypeError. |
| `tests/unit/test_daemon_drift_events.py` | +20 | REQ-55: event-log integration + W6 still-valid silence + unable_to_verify edge case. |
| `tests/unit/test_cli_watch_drift.py` | +10 | REQ-55: CLI wiring + `--drift-event-log` flag + `--no-drift-event-log` opt-out. |
| `tests/unit/test_cli_drift.py` | +25 | REQ-59 S2 stderr WARN capture + threshold env var + per-batch cadence; REQ-56 cast site updates. |
| `tests/unit/test_observability.py` | +10 | REQ-55: 2 catalog entry smoke tests. |
| `tests/bdd/req15_drift_daemon.feature` | +80 | REQ-55: 2 new BDD scenarios (JSONL line present on detected drift + no JSONL line on still-valid + still-valid-but-graph-unavailable emits unable_to_verify line per W6). |
| `tests/bdd/test_decision_reality_drift_steps.py` | +100 | REQ-55: extend step glue for 2 new `req15_drift_daemon.feature` scenarios. |
| `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` | +5 / -5 | REQ-56: REQ-9..16 scenarios reconciled with new shape (decision_id int, scanned_at str ISO, unable_to_verify+unable_reason). |
| `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md` | +10 / -8 | REQ-56: dataclass type signatures at lines 134-155 reconciled. |
| `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` | +3 / -3 | REQ-58 W26: `freed_bytes_estimate` → `freed_bytes` at line 230. |
| `openspec/changes/archive/2026-06-27-graph-snapshots/design.md` | +5 / -5 | REQ-58 W25: `SnapshotMeta` contract block `size_bytes` + `pinned` at line 271 + `PruneResult.freed_bytes` at lines 66, 474. |
| `CHANGELOG.md` | +40 | v0.6.0 Notes section entry for W23 coexistence (Batch B); v0.8.0 entry post-merge listing all 5 REQs + `BREAKING:` section (Batch D). |
| `pyproject.toml` | +1 / -1 | `version = "0.8.0"` (REQ-56 breaking change mandates minor bump). |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | ~80 | Drift-hardening hook prose (mirror observability SKILL.md hook from change #6). |

**Production total**: ~225 net LOC across 1 NEW + 5 MODIFIED (6 total prod files).
**Test total**: ~1 600 LOC across 8 NEW test files + 1 NEW feature + 6 MODIFY unit tests + 6 NEW step glue + 1 MODIFY BDD feature + 1 MODIFY step glue (15 total test files).
**Archived spec/design total**: ~28 net LOC across 4 archived files.
**CHANGELOG + repo meta total**: ~60 net LOC.
**Strict-TDD ratio**: ~5.7× — within the 2-4× target band from `decision-code-linking` S3 precedent (proposal #223 estimated ~5.3×; this design confirms).

---

## Data Model

### `Finding` (MODIFIED, REQ-56 W8)

```python
@dataclass(frozen=True)
class Finding:
    """One per-binding classification result.

    REQ-56 W8: decision_id is now ``int`` (was ``str``). Legacy numeric
    ``str`` inputs are accepted via ``__post_init__`` coercion with a
    ``DeprecationWarning`` for v0.8.0; hard break in v1.0.

    REQ-56 W8: ``binding: CodeRef`` field replaces the
    ``file/line/label`` triple (no behavior change — just refactored to
    use the existing ``CodeRef`` dataclass from ``binding.py``).
    """

    decision_id: int                    # was: str  (REQ-56 W8)
    binding: CodeRef                    # was: file/line/label triple
    drift_class: DriftClass
    detail: str

    def __post_init__(self) -> None:
        # 1-release soft compat: accept numeric strings, emit DeprecationWarning.
        if isinstance(self.decision_id, str):
            warnings.warn(
                "Finding.decision_id: str is deprecated; pass int (REQ-56).",
                DeprecationWarning, stacklevel=2,
            )
            object.__setattr__(self, "decision_id", _coerce_int(self.decision_id))
```

**Validation rules**:
- `decision_id: int` (post-coercion if input was numeric str).
- Non-numeric `str` for `decision_id` raises `ValueError` with message
  `"decision_id must be int or numeric str, got <repr>"`.
- `binding: CodeRef` (frozen dataclass from `binding.py`).

**Migration notes**:
- Legacy `str` callers (v0.7.0) get `DeprecationWarning` + coercion.
- Legacy non-numeric `str` callers get `ValueError` (graceful coercion
  is only for numeric strings).
- v1.0 removes the `__post_init__` coercion entirely.

### `DriftReport` (MODIFIED, REQ-56 W8)

```python
@dataclass
class DriftReport:
    """Aggregate result for a full scan of one change.

    REQ-56 W8: ``scanned_at: str`` ISO 8601 UTC (was ``float`` epoch).
    REQ-56 W8: ``unable_to_verify: bool`` + ``unable_reason: str | None``
    (renamed from ``graph_unavailable: bool``).
    REQ-56 W8: ``@property graph_unavailable`` retained for 1 release
    as a ``DeprecationWarning``-emitting alias.
    """

    change_name: str
    scanned_at: str                     # was: float — ISO 8601 UTC (REQ-56 W8)
    graph_mtime: str | None             # was: float | None — ISO 8601 UTC (REQ-56 W8)
    decisions_total: int
    bindings_total: int
    class_counts: dict[DriftClass, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    unable_to_verify: bool = False      # was: graph_unavailable (REQ-56 W8)
    unable_reason: str | None = None    # NEW field (REQ-56 W8)

    @property
    def graph_unavailable(self) -> bool:
        """1-release alias for ``unable_to_verify`` (REQ-56 backward compat)."""
        warnings.warn(
            "DriftReport.graph_unavailable is deprecated; use unable_to_verify (REQ-56).",
            DeprecationWarning, stacklevel=2,
        )
        return self.unable_to_verify

    @classmethod
    def from_scanned(
        cls,
        *,
        change_name: str,
        scanned_at: float | str,
        graph_mtime: float | str | None = None,
        unable_to_verify: bool = False,
        unable_reason: str | None = None,
        decisions_total: int = 0,
        bindings_total: int = 0,
        class_counts: dict[DriftClass, int] | None = None,
        findings: list[Finding] | None = None,
    ) -> "DriftReport":
        """Migration constructor: accepts legacy ``float`` epoch inputs.

        Coerces ``float`` epoch seconds to ISO 8601 UTC ``str`` via
        ``datetime.fromtimestamp(..., tz=UTC).strftime(...)``. No
        ``DeprecationWarning`` (this IS the explicit migration path).
        """
        scanned_iso = _epoch_to_iso(scanned_at) if isinstance(scanned_at, float) else scanned_at
        mtime_iso = _epoch_to_iso(graph_mtime) if isinstance(graph_mtime, float) else graph_mtime
        return cls(
            change_name=change_name,
            scanned_at=scanned_iso,
            graph_mtime=mtime_iso,
            decisions_total=decisions_total,
            bindings_total=bindings_total,
            class_counts=class_counts or {},
            findings=findings or [],
            unable_to_verify=unable_to_verify,
            unable_reason=unable_reason,
        )

    @property
    def total(self) -> int:
        """Total finding count (post-REQ-56 convenience helper for W6 silence rule)."""
        return sum(self.class_counts.values())
```

**Validation rules**:
- `scanned_at: str` ISO 8601 UTC (e.g., `"2026-06-27T12:34:56Z"`).
- `unable_to_verify=True` + `unable_reason=None` is allowed (the reason
  is optional; default `None` means "graph unavailable, no further
  detail").
- `total == 0 and not unable_to_verify` triggers the W6 silence rule
  (per D4).

**Migration notes**:
- Legacy `float` epoch callers use `DriftReport.from_scanned()` (no
  warning; explicit migration path).
- Legacy `graph_unavailable` readers get `DeprecationWarning` + return
  value of `unable_to_verify`.
- v1.0 removes the `@property graph_unavailable` alias AND the
  `from_scanned()` classmethod (clean break; the call sites update to
  ISO `str` inputs).

### `DriftEvent` (NEW, REQ-55 W5)

```python
@dataclass(frozen=True)
class DriftEvent:
    """One row in ``drift_events.jsonl``.

    REQ-55 W5: schema is ``{ts, change, decision_id, binding_id, class,
    detected_at}`` per archived spec #135 line 272. Frozen dataclass so
    the JSON serialization is deterministic.
    """

    ts: str                  # ISO 8601 UTC (append time)
    change: str
    decision_id: int         # int post-REQ-56
    binding_id: str
    class: str               # DriftClass.value (STILL_VALID / LABEL_DRIFT / etc.)
    detected_at: str         # ISO 8601 UTC (DriftReport.scanned_at)
```

**Validation rules**:
- `decision_id: int` (post-REQ-56; non-int rejected upstream in
  `record_drift_event`).
- `class: str` must be one of `DriftClass` enum values.
- `ts` and `detected_at` are ISO 8601 UTC with `Z` suffix.

**Migration notes**:
- None — this is a NEW dataclass for v0.8.0.
- The JSONL wire format is `{ts, change, decision_id, binding_id, class,
  detected_at}` (key order matters for stable diff).

### `classify_binding` (MODIFIED, REQ-56 W8)

```python
def classify_binding(
    binding: CodeRef,
    graph_nodes: dict[str, dict],
) -> DriftClass:
    """Classify a single ``CodeRef`` against the current graph state.

    REQ-56 W8: 2-arg signature (was 3-arg). ``current_id_map`` is now
    derived INSIDE from ``graph_nodes``. 3-arg callers get ``TypeError``.

    Algorithm (REQ-9, unchanged):
        1. ``graph_nodes`` is ``None`` or empty -> ``UNABLE_TO_VERIFY``.
        2. ``binding.id`` absent from derived ``current_id_map`` -> ``STALE_ID``.
        3. ``(file, line)`` differ from current -> ``STALE_LOCATION``.
        4. ``label`` differs from current -> ``LABEL_DRIFT``.
        5. Otherwise -> ``STILL_VALID``.
    """
    if not graph_nodes:
        return DriftClass.UNABLE_TO_VERIFY
    current_id_map = {
        node_id: (node.get("file") or node.get("source_file", ""),
                  _parse_line(node.get("line") or node.get("source_location", 0)),
                  node.get("label", ""))
        for node_id, node in graph_nodes.items()
    }
    entry = current_id_map.get(binding.id)
    if entry is None:
        return DriftClass.STALE_ID
    cur_file, cur_line, cur_label = entry
    if cur_file != binding.file or cur_line != binding.line:
        return DriftClass.STALE_LOCATION
    if cur_label != binding.label:
        return DriftClass.LABEL_DRIFT
    return DriftClass.STILL_VALID
```

**Validation rules**:
- `graph_nodes: dict[str, dict]` (post-REQ-56; was `dict[str, dict]` +
  separate `current_id_map` dict).
- `binding: CodeRef` (frozen dataclass from `binding.py`).

**Migration notes**:
- 3-arg callers get `TypeError` (clean break per OQ-10).
- The `current_id_map` derivation is O(N) at function entry — for a
  typical 1 000-node graph, <1ms.

---

## Algorithm Details

### JSONL append-only writer (REQ-55 W5, D3 + D11)

**Pseudocode** (`record_drift_event` in `drift_event_log.py`):

```python
def record_drift_event(report: DriftReport, *, path: Path | None = None) -> None:
    """Append one JSON line per non-still-valid finding to drift_events.jsonl.

    Powers REQ-55 (W5); counters: ``drift_event_log_total`` (per finding)
    + ``drift_event_log_bytes`` (gauge, post-rotation).

    Best-effort: wrapped in ``try/except OSError`` — on disk full /
    permission denied, log to stderr and return without raising
    (matches ``observability.increment()`` policy — never crashes the
    caller).

    Thread-safety: single-process daemon only (D11). The daemon's
    watchdog loop is serial; no concurrent writers. The file handle is
    exclusive to the writer within the process.

    Rotation: automatic on append when ``target.stat().st_size >=
    ROTATE_BYTES`` (10 * 1024 * 1024). Rotated files named
    ``drift_events.<ISO-no-colons>.jsonl`` (lex-sortable by rotation
    time). Fresh ``drift_events.jsonl`` is created on next append.
    """
    target = path or DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        _rotate_if_needed(target)
        with target.open("a", encoding="utf-8") as fh:
            for finding in report.findings:
                event = {
                    "ts": _utc_iso(),
                    "change": report.change_name,
                    "decision_id": finding.decision_id,         # int post-REQ-56
                    "binding_id": finding.binding.id,
                    "class": finding.drift_class.value,        # str enum
                    "detected_at": report.scanned_at,          # str ISO post-REQ-56
                }
                fh.write(json.dumps(event, separators=(",", ":")) + "\n")
                increment("drift_event_log_total", domain="drift",
                          change=report.change_name)
        increment("drift_event_log_bytes", domain="drift",
                  value=target.stat().st_size)
    except OSError as exc:
        print(f"WARN: drift_event_log write failed: {exc}", file=sys.stderr)
        return  # best-effort; never raise
```

**Edge cases**:
- `OSError` on `drift_events.jsonl` write (disk full, permission denied):
  caught and logged to stderr; daemon continues (best-effort).
- Rotation at exactly 10 MB boundary renames the file BEFORE writing
  the new line — so the new line goes to the fresh file, NOT the
  rotated one.
- `since_iso` filter on `iter_drift_events` uses lexicographic ISO
  comparison (timestamps are `Z`-suffixed UTC; lex sort = chrono sort).
- `change` filter is exact match (NOT substring); a `change="obs-v1"`
  filter does NOT match `change="obs"`.

### Still-valid silence rule (REQ-55 W6, D4)

**Pseudocode** (in `daemon.py:handle_apply_progress_event`):

```python
# After record_drift_summary + record_drift_event
if report.unable_to_verify:
    on_summary(f"unable_to_verify: graph.json unavailable at {graph_path} "
               f"({report.unable_reason or 'unknown'})")
    return report

# W6 silence rule: suppress outer summary when total == 0 and not unable_to_verify.
if report.total == 0:
    return report  # silent on still-valid

# Otherwise emit the class breakdown
counts = report.class_counts
parts: list[str] = []
for cls in (
    decision_drift.DriftClass.STILL_VALID,
    decision_drift.DriftClass.LABEL_DRIFT,
    decision_drift.DriftClass.STALE_LOCATION,
    decision_drift.DriftClass.STALE_ID,
    decision_drift.DriftClass.OBSOLETE,
    decision_drift.DriftClass.CONTRADICTED,
):
    n = counts.get(cls, 0)
    if n > 0:
        parts.append(f"{n} {cls.value}")
on_summary(
    f"drift: {report.change_name} {report.total} findings "
    f"({', '.join(parts) if parts else 'no classes'})"
)
return report
```

**Edge cases**:
- `unable_to_verify=True` + `total == 0`: emit the unable_to_verify
  summary line (NOT suppressed; graph unreachable is informative).
- `unable_to_verify=True` + `total > 0`: emit the unable_to_verify
  summary line (the partial classification is still useful even though
  the graph was unreachable for some bindings).
- `unable_to_verify=False` + `total == 0`: SILENT (W6 silence rule).
- `unable_to_verify=False` + `total > 0`: emit the class breakdown.

### S2 stderr WARN cadence (REQ-59 S2, D8)

**Pseudocode** (at end of `cli.py:_write_back_findings`):

```python
def _write_back_findings(
    report: decision_drift.DriftReport, change_name: str
) -> int:
    """... (existing docstring) ...

    REQ-59 S2: when ``skipped_total >= FLOW_DRIFT_SKIP_WARN_THRESHOLD``
    (default 3; tunable via env var), emit a single stderr WARN line at
    the END of the batch (NOT per skipped row).
    """
    backend = _default_save_backend()
    client = EngramClient(change_name, backend)
    success = 0
    skipped_total = 0
    for finding in report.findings:
        try:
            observation_id = int(finding.decision_id)
        except (TypeError, ValueError):
            # Post-REQ-56: numeric str inputs coerce cleanly in Finding.__post_init__;
            # only truly non-numeric str inputs reach this skip path.
            observability.increment(
                "drift_write_back_skipped_total",
                reason="non_int_decision_id",
            )
            skipped_total += 1
            continue
        try:
            client.update_observation_metadata(
                observation_id,
                {
                    "last_verified_at": _now_iso(),
                    "last_drift_class": finding.drift_class.value,
                },
            )
            success += 1
        except Exception:
            observability.increment("drift_write_back_failed_total")
            continue

    # REQ-59 S2: once-per-batch WARN when skipped_total >= threshold.
    threshold = _get_skip_warn_threshold()
    if threshold >= 0 and skipped_total >= threshold:
        print(
            f"WARN: drift write-back skipped {skipped_total} "
            f"non-int decision_ids",
            file=sys.stderr,
        )
    return success


def _get_skip_warn_threshold() -> int:
    """Parse FLOW_DRIFT_SKIP_WARN_THRESHOLD env var; fall back to 3 on parse error."""
    raw = os.environ.get("FLOW_DRIFT_SKIP_WARN_THRESHOLD")
    if raw is None:
        return 3
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 3
```

**Edge cases**:
- `FLOW_DRIFT_SKIP_WARN_THRESHOLD=0`: WARN every batch with
  `skipped_total > 0`.
- `FLOW_DRIFT_SKIP_WARN_THRESHOLD=-1`: WARN never.
- `FLOW_DRIFT_SKIP_WARN_THRESHOLD=garbage`: fall back to default 3
  (parse error path).
- The WARN is printed to `sys.stderr` (NOT the logging framework —
  matches the on-error output style of `flow` CLI).

---

## Error Handling

| Error mode | Exit code | User-facing message | Affected flag(s) |
|---|---|---|---|
| `daemon: no findings + not unable_to_verify` | 0 | (no stdout output per W6 silence rule D4) | (none — daemon quiet tick) |
| `daemon: unable_to_verify=True, unable_reason="graph_json_missing"` | 2 | `unable_to_verify: graph.json unavailable at <path> (graph_json_missing)` | (none — daemon informative tick) |
| `daemon: unable_to_verify=True + total > 0` | 1 | `unable_to_verify: ...` + class breakdown | (none — partial classification) |
| `daemon: total > 0 + not unable_to_verify` | 1 | `drift: <change> <total> findings (<class_breakdown>)` | (none — drift detected) |
| `--write-back: non-int decision_id` (post-REQ-56 coercion failed) | 0 + stderr WARN | `WARN: drift write-back skipped <N> non-int decision_ids` (when `N >= threshold`) | `--write-back` |
| JSONL writer: disk full | 0 (daemon continues) | `WARN: drift_event_log write failed: <strerror>` (stderr) | `--drift-event-log` (default-on) |
| JSONL writer: permission denied | 0 (daemon continues) | `WARN: drift_event_log write failed: <strerror>` (stderr) | `--drift-event-log` |
| `Finding(decision_id="not-a-number")` | (no CLI — dataclass raises) | `ValueError: decision_id must be int or numeric str, got 'not-a-number'` | (none — dataclass validation) |
| `classify_binding(ref, graph_nodes, current_id_map)` 3-arg | (no CLI — function raises) | `TypeError: classify_binding() takes 3 positional arguments but 4 were given` | (none — function signature) |
| `record_drift_event(report)` with `decision_id=str` (pre-REQ-56 caller) | (handled by `__post_init__`) | `DeprecationWarning: Finding.decision_id: str is deprecated; pass int (REQ-56).` | (none — dataclass compat) |
| `DriftReport(graph_unavailable=True)` 1-release compat | (handled by `@property`) | `DeprecationWarning: DriftReport.graph_unavailable is deprecated; use unable_to_verify (REQ-56).` | (none — dataclass compat) |
| `--drift-event-log=<path>` parent not creatable | 2 | `{"error": "cannot create event-log directory", "path": "<path>", "cause": "<strerror>"}` (stderr) | `--drift-event-log` |

**Rationale**: `daemon` exit codes mirror `flow drift scan <change>` exit
codes (0 still-valid, 1 stale, 2 unable_to_verify, 3 usage error) — the
daemon's stdout `drift:` line is just the per-tick summary, the exit
code is determined by the daemon wrapper. `--write-back` exit code is 0
when any success path completes (matches existing behavior). JSONL
writer failures are best-effort (never crash the daemon); stderr WARN
is the operator signal. Dataclass compat failures raise immediately
(no silent fallback) so callers update.

---

## Test Plan

| Layer | What | Approach | File | Count |
|---|---|---|---|---|
| Unit | `record_drift_event` rotation at 10 MB | `tmp_path` with pre-sized file at exactly 10 MB; assert rotated file + fresh file | `tests/unit/test_drift_event_log.py` | 2 |
| Unit | `record_drift_event` schema | `DriftReport` with 3 findings; assert JSONL lines have `{ts, change, decision_id, binding_id, class, detected_at}` | same | 4 |
| Unit | `record_drift_event` counter increment | assert `drift_event_log_total{change=<chg>}` + `drift_event_log_bytes` after append | same | 3 |
| Unit | `record_drift_event` OSError path | `monkeypatch` `Path.open` to raise; assert stderr WARN + no crash | same | 2 |
| Unit | `iter_drift_events` filter | 5 events across 2 changes; assert `--change=X` filter; assert `--since=<iso>` lex sort | same | 4 |
| Unit | `Finding.decision_id` int direct | `Finding(decision_id=42, ...)`; assert `decision_id == 42` + no warning | `tests/unit/test_decision_drift.py` | 2 |
| Unit | `Finding.decision_id` numeric str coercion | `Finding(decision_id="42", ...)` with `warnings.catch_warnings`; assert coerced + `DeprecationWarning` captured | same | 2 |
| Unit | `Finding.decision_id` non-numeric str | `Finding(decision_id="not-a-number", ...)`; assert `ValueError` | same | 1 |
| Unit | `DriftReport.scanned_at` str ISO direct | `DriftReport(scanned_at="2026-06-27T12:34:56Z", ...)`; assert round-trip | same | 1 |
| Unit | `DriftReport.from_scanned` float epoch coercion | `DriftReport.from_scanned(scanned_at=1751000000.0)`; assert ISO conversion | same | 2 |
| Unit | `DriftReport.graph_unavailable` @property alias | `DriftReport(unable_to_verify=True)`; assert `@property graph_unavailable` returns True + `DeprecationWarning` captured | same | 1 |
| Unit | `classify_binding` 2-arg STALE | `classify_binding(ref, graph_nodes)` where file/line mismatch; assert `STALE_LOCATION` | same | 1 |
| Unit | `classify_binding` 3-arg TypeError | `classify_binding(ref, graph_nodes, current_id_map)`; assert `TypeError` | same | 1 |
| Unit | W6 still-valid silence | mock `on_summary`; `handle_apply_progress_event` with `total == 0 and not unable_to_verify`; assert `on_summary` NOT called | `tests/unit/test_daemon_drift_events.py` | 1 |
| Unit | W6 unable_to_verify edge case | mock `on_summary`; `handle_apply_progress_event` with `unable_to_verify=True`; assert `on_summary` IS called with unable_reason | same | 1 |
| Unit | record_drift_event wiring | mock `on_summary`; assert `record_drift_event` is called AFTER `record_drift_summary` | same | 2 |
| Unit | `--drift-event-log` flag | `CliRunner`; assert default-on behavior + `--no-drift-event-log` opt-out | `tests/unit/test_cli_watch_drift.py` | 2 |
| Unit | `_write_back_findings` S2 stderr WARN | `capsys`; assert `WARN:` line printed once per batch when `skipped_total >= threshold` | `tests/unit/test_cli_drift.py` | 2 |
| Unit | `FLOW_DRIFT_SKIP_WARN_THRESHOLD` env var | `monkeypatch.setenv`; assert threshold honored + parse error fall back to 3 | same | 2 |
| Unit | `record_drift_event` catalog entries | assert `drift_event_log_total` + `drift_event_log_bytes` in `observability` catalog | `tests/unit/test_observability.py` | 2 |
| BDD (REQ-55) | JSONL line per finding | GIVEN 3 STALE + 1 MISSING WHEN daemon tick THEN 4 JSONL lines with required keys | `tests/bdd/req15_drift_daemon.feature` (extend) | 1 |
| BDD (REQ-55) | JSONL silent on still-valid | GIVEN all STILL_VALID WHEN daemon tick THEN 0 JSONL lines + no stdout summary | same | 1 |
| BDD (REQ-55) | unable_to_verify emits summary | GIVEN all STILL_VALID + graph_json missing WHEN daemon tick THEN unable_to_verify summary line IS printed | same | 1 |
| BDD (REQ-55) | JSONL rotation at 10 MB | GIVEN file at 10 MB WHEN append THEN rotated sibling + fresh file | same | 1 |
| BDD (REQ-10) | `flow drift scan` text default | GIVEN 5 bindings WHEN `flow drift scan obs` THEN human-readable summary line | `tests/bdd/req10_drift_cli.feature` | 1 |
| BDD (REQ-10) | `--json` structured output | GIVEN 5 bindings WHEN `flow drift scan obs --json` THEN JSON envelope | same | 1 |
| BDD (REQ-10) | `--include-obsolete` opt-in | GIVEN OBSOLETE binding WHEN `--include-obsolete` THEN 5 findings (incl OBSOLETE) | same | 1 |
| BDD (REQ-10) | `--since=<iso>` filter | GIVEN 5 bindings at T1..T5 WHEN `--since=<T3_iso>` THEN only T3,T4,T5 | same | 1 |
| BDD (REQ-10) | `--write-back` writes to live Engram | GIVEN 3 STALE WHEN `--write-back` THEN 3 `update_observation_metadata` calls | same | 1 |
| BDD (REQ-10) | `--graph-json=<path>` custom graph | GIVEN custom graph at `/tmp/custom_graph.json` WHEN `--graph-json=/tmp/...` THEN drift computed against custom | same | 1 |
| BDD (REQ-10) | Unknown change name | GIVEN unknown change WHEN `flow drift scan non-existent` THEN stderr JSON error + exit 3 | same | 1 |
| BDD (REQ-10) | exit 0 still-valid + exit 1 stale | GIVEN all STILL_VALID / 1 STALE WHEN scan THEN exit 0 / exit 1 | same | 2 |
| BDD (REQ-11) | exit 2 unable_to_verify | GIVEN graph_json missing WHEN scan THEN exit 2 + unable_reason | `tests/bdd/req11_drift_exit.feature` | 1 |
| BDD (REQ-12) | 8 drift counters emitted | GIVEN 3 findings WHEN `record_drift_summary` THEN 8 events in metrics.jsonl | `tests/bdd/req12_drift_counters.feature` | 1 |
| BDD (REQ-12) | idempotent on repeat calls | GIVEN 3 findings WHEN called twice THEN 2 events (NOT 1) | same | 1 |
| BDD (REQ-12) | drift_unable_to_verify_total on graph_unavailable | GIVEN unable_to_verify=True WHEN called THEN 1 event for counter | same | 1 |
| BDD (REQ-13) | `update_observation_metadata` append | GIVEN observation WHEN called THEN metadata key appended + content unchanged | `tests/bdd/req13_drift_metadata.feature` | 1 |
| BDD (REQ-13) | idempotent on repeat keys | GIVEN metadata.drift_status=STALE WHEN called with MISSING THEN overwritten (NOT appended) | same | 1 |
| BDD (REQ-13) | unknown observation_id raises | GIVEN unknown id=99999 WHEN called THEN `ObservationNotFoundError` + no auto-create | same | 1 |
| BDD (REQ-14) | per-row IOError doesn't crash | GIVEN 1 deleted file mid-scan WHEN scan THEN 4 findings + per-row error logged + exit 0 | `tests/bdd/req14_drift_resilience.feature` | 1 |
| BDD (REQ-14) | read-only by default | GIVEN 3 STALE WHEN scan (no `--write-back`) THEN 0 `update_observation_metadata` calls + counter NOT incremented | same | 1 |
| BDD (REQ-14) | partial write-back success | GIVEN 3 STALE + 1 read-only WHEN `--write-back` THEN 2 success + "wrote: 2, failed: 1" + exit 0 | same | 1 |
| BDD (REQ-14) | graph_unavailable helpful error | GIVEN graph_json missing WHEN scan THEN stderr hint `--graph-json=<path>` + exit 2 | same | 1 |
| BDD (REQ-16) | sdd-verify Step 6a SKILL.md grep | GIVEN SKILL.md exists WHEN sdd-verify Step 6a THEN grep matches "drift" line + verify exits 0 | `tests/bdd/req16_skill_prose.feature` | 1 |
| BDD (REQ-16) | drift detection hook references decision-reality-drift | GIVEN SKILL.md exists WHEN grep THEN match references REQ-9 OR archived path | same | 1 |
| Secrets invariant | JSONL event schema | assert no `secrets.yaml` content leaks into event fields | `tests/unit/test_drift_event_log.py` | 1 |

**Unit test count forecast**: **~30 new unit tests** across 1 NEW file
(`test_drift_event_log.py` ~18) + 5 MODIFY files (`test_decision_drift.py`
+10, `test_daemon_drift_events.py` +4, `test_cli_watch_drift.py` +2,
`test_cli_drift.py` +4, `test_observability.py` +2). Plus 4 BDD
scenarios extending `req15_drift_daemon.feature` for REQ-55.

**BDD scenarios**: **21 NEW + 4 EXTENDED = 25** total:
- REQ-10: 9 scenarios in `req10_drift_cli.feature`
- REQ-11: 3 scenarios in `req11_drift_exit.feature` (folded with REQ-10's 9; per spec proposal #223)
- REQ-12: 3 scenarios in `req12_drift_counters.feature`
- REQ-13: 3 scenarios in `req13_drift_metadata.feature`
- REQ-14: 4 scenarios in `req14_drift_resilience.feature`
- REQ-16: 2 scenarios in `req16_skill_prose.feature`
- REQ-15: +2 scenarios extending `req15_drift_daemon.feature` (JSONL + W6)

**Coverage targets**: 95% line coverage on the new helpers; 100%
coverage on the error-path branches (D11 best-effort). `ruff check`
clean on all changed files.

**Strict TDD order** per `decision-code-linking` S3 precedent:

1. `decision_drift.Finding.decision_id: int` + `__post_init__` coercion — RED: str input raises TypeError → GREEN: numeric str coerced with DeprecationWarning → REFACTOR: handle non-numeric ValueError
2. `decision_drift.DriftReport.scanned_at: str` + `from_scanned()` classmethod — RED: float input rejected → GREEN: float coerced to ISO → REFACTOR: handle both
3. `decision_drift.DriftReport.unable_to_verify` + `unable_reason` + `@property graph_unavailable` — RED: alias missing → GREEN: DeprecationWarning + return unable_to_verify → REFACTOR
4. `decision_drift.classify_binding(ref, graph_nodes)` 2-arg — RED: 3-arg signature → GREEN: derive current_id_map inside → REFACTOR: handle empty graph_nodes
5. `drift_event_log.record_drift_event` — RED: file write fails → GREEN: 1 line per finding → REFACTOR: rotate_if_needed + try/except OSError
6. `drift_event_log.iter_drift_events` — RED: filter by change → GREEN: filter by since_iso + change → REFACTOR: handle missing file
7. `observability.record_drift_event()` helper + 2 catalog entries — RED: catalog entry missing → GREEN: emit + counter → REFACTOR
8. `daemon.handle_apply_progress_event` wiring + W6 silence — RED: summary line always emitted → GREEN: silence on still-valid → REFACTOR
9. `cli._write_back_findings` S2 stderr WARN — RED: no WARN → GREEN: batch WARN on threshold → REFACTOR: env var parse
10. `tests/bdd/req15_drift_daemon.feature` 2 new scenarios + step glue — RED: scenario missing → GREEN → REFACTOR
11. 6 NEW `.feature` files (REQ-57) + 6 NEW step glue — RED: feature files empty → GREEN: business-domain phrasing → REFACTOR
12. CHANGELOG v0.8.0 entry last

---

## Out-of-Scope (consolidated)

The following 13 items are explicitly out of scope for change #8 and
belong to named follow-ups:

1. **`flow drift events` CLI read-side** (OQ-9 deferred) — defer to
   v1.0 / `drift-events-dashboard` follow-up. v0.8.0 ships write-side
   only; consumers use `cat ~/.flow-engineering/drift_events.jsonl | jq`
   or `flow metrics --domain=drift` for the counter view.
2. **`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var** — defer to v1.1
   alongside `FLOW_METRICS_MAX_BYTES` from observability REQ-44 (joint
   metrics+drift JSONL rotation follow-up).
3. **`FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` env var** — same deferral as
   #2.
4. **`FindingLegacy` dataclass shim** (OQ-1 rejected option (c)) —
   the `@property graph_unavailable` + `__post_init__` coercion is the
   1-release migration path; v1.0 removes both.
5. **`Mypy strict-mode adapter` for `decision_id: int | str`** —
   v0.8.0 ships `int`-only; legacy callers update by v1.0.
6. **Cross-project federation for drift events** (`flow drift events
   --project=<key>`) — defer to v1.0; v0.8.0 is single-project.
7. **OpenTelemetry push for drift events** — defer to v1.0; Prometheus
   textfile format from observability is the v1 export story.
8. **Per-finding classification refinement** — `classify_binding`
   handles graph-level unavailable at the report level; per-finding
   graph_unavailable refinement is v2.
9. **Auto-daily snapshot trigger** (`trigger="auto"`) — v2; v1 supports
   `manual` + `rollback_safety` only (graph-snapshots D3 precedent).
10. **Snapshot diff rendering with `--format=unified`** — v1 is
    JSON-only; deferred (graph-snapshots D9 precedent).
11. **Snapshot export/import** (`flow snapshot export <id>` / `flow
    snapshot import <id>`) — already deferred in graph-snapshots
    archive; unchanged.
12. **`flow drift events --format=prometheus`** — defer; raw JSONL is
    the only v0.8.0 output format.
13. **Runtime WARN on `flow metrics` for legacy `snapshot_pruned_total`
    events** (OQ-7 rejected) — preserve audit trail; CHANGELOG-only.

---

## Risks

| # | Risk | Likelihood | Severity | Status |
|---|---|---|---|---|
| 1 | REQ-56 (W8) public API break: `decision_id: str → int`, `scanned_at: float → str`, `graph_unavailable → unable_to_verify`, `classify_binding` 3→2 args — third-party consumers (if any) break at runtime / mypy strict | MED | HIGH | **MITIGATED** — Hard migration is acceptable (no third-party consumers per Engram #92 sdd-init + proposal #223 OQ-1); 1-release `DeprecationWarning` aliases for `graph_unavailable` and `Finding.__post_init__` str coercion; v0.7.0 → v0.8.0 version bump; CHANGELOG `BREAKING:` section with migration steps. |
| 2 | REQ-55 (W5) JSONL writer unbounded growth: `drift_events.jsonl` can exceed 100 MB/year on a long-running watcher | MED | MED | **MITIGATED** — Mirror `metrics.jsonl` rotation policy — rotate when file > 10 MB to `drift_events.<timestamp>.jsonl` + start fresh (D3). REQ-44 metrics rotation is deferred to v1.1; both deferred items land together in a future "metrics+drift-jsonl-rotation" change. |
| 3 | REQ-59 (W23) wire-format compatibility: legacy `snapshot_pruned_total` events (K=101+) coexist with renamed `snapshot_prune_total` (K=70+) in `~/.flow-engineering/metrics.jsonl`; sum-based queries double-count | LOW | LOW | **MITIGATED** — PREFERRED: CHANGELOG v0.6.0 Notes section documents coexistence + recommends REQ-37 `--domain snapshot` filter (D7); no code change beyond a 3-line CHANGELOG entry. If a downstream consumer materializes, revisit as REQ-59 follow-up. |
| 4 | REQ-57 (W4) BDD coverage scope: 21 scenarios risk becoming tautological (just `@scenario`-bound unit tests without business-domain phrasing) | MED | MED | **MITIGATED** — Quality gate (D5): each BDD scenario MUST use business-domain Given/When/Then (e.g., "Given a decision with bindings at file X line Y", "When flow drift scans the change", "Then the report shows STILL_VALID") NOT unit-test phrasing ("Given a fixture dict X"); sdd-verify Step 6b asserts the 21-scenario count + spot-checks 3 random scenarios for business-domain phrasing. |
| 5 | Single PR realistic LOC ~9 700 (close to observability's ~10 910 chained-PR threshold); reviewer fatigue on a 4-batch single-PR | MED | MED | **MITIGATED** — Per-commit work-unit splits per `work-unit-commits` skill (12-14 commits each ≤400 LOC across 4 batches); D12 explicit batch sequencing; reviewer reads batch-by-commit not as one blob. |
| 6 | Batch C BDD coverage (21 scenarios) is the bottleneck at ~60 min; if rushed, quality degrades (tautological scenarios) | MED | MED | **MITIGATED** — D10 split per-REQ into 6 step glue files (mirrors graph-snapshots precedent); sdd-verify Step 6b quality gate enforces business-domain phrasing on 3 random scenarios. |
| 7 | Step glue module size: 6 NEW step glue files push the test directory to ~15 NEW/MODIFY files (review-awkward) | LOW | LOW | **MITIGATED** — D10 per-REQ split keeps each step glue ≤200 LOC; mirrors `test_graph_snapshots_steps.py` multi-feature precedent. |
| 8 | `flow` script has potential (unconfirmed) third-party consumers; REQ-56 break could surprise downstream | LOW | MED | **MITIGATED** — Pre-flight: confirmed via `pip search flow-engineering` (no unrelated packages); `pyproject.toml` is the only install entry point per Engram #92 sdd-init. If a consumer surfaces, pivot to soft migration (Risk 1 mitigation option b) for v1.0. |
| 9 | Drift detection hook (REQ-9..16) integration with the new JSONL sink: if `record_drift_event` raises (e.g., disk full), daemon crashes mid-tick | LOW | HIGH | **MITIGATED** — D11 wraps the append in `try/except OSError`; on failure, log to stderr and continue (matches `observability.increment()` policy — best-effort, never crashes the caller); BDD scenario covers disk-full path. |
| 10 | Snapshot field-name reconciliation (REQ-58 W25/W26) is spec/design-only, but downstream BDD consumers may have hardcoded the old `file_size_bytes` / `freed_bytes_estimate` names | LOW | MED | **MITIGATED** — REQ-34 BDD scenarios don't assert exact field name (per explore #222); verify before merge via grep on `tests/bdd/req28..34_*.feature` for the legacy names; if found, rename in the same Batch A commit. |

---

## Cross-Impact

| Queued / shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `observability.increment()` reused for `drift_event_log_total` + `drift_event_log_bytes` counter emission | Compatible (consumes the seam) |
| `decision-reality-drift` (shipped v0.3.0) | `Finding`/`DriftReport`/`classify_binding` shape migrated (REQ-56); `record_drift_summary()` extended with `unable_to_verify` rename | **MIGRATION** (shape change with 1-release deprecation aliases) |
| `vector-semantic-search` (shipped v0.4.0) | Unrelated layer | No conflict |
| `cross-project-federation` (shipped v0.5.0) | Unrelated layer | No conflict |
| `graph-snapshots` (shipped v0.6.0) | `SnapshotMeta`/`PruneResult` field names reconciled (REQ-58); `SNAPSHOT_COUNTER_NAMES` catalog extended with W23 deprecation note (REQ-59) | Compatible (consumes the seam) |
| `observability` (change #6, shipped v0.7.0) | `flow metrics summary` + `--domain` filter recommended for REQ-59 W23 deprecation; `record_drift_event()` helper mirrors the 5 existing `record_*_summary` helpers; `metrics.jsonl` rotation pattern mirrored for `drift_events.jsonl` | Compatible (consumes the seam) |
| `prompt-registry` (#7, future) | Unrelated layer; MUST ARCHIVE BEFORE change #8 starts (preserves REQ-55..59 numbering) | No conflict |

**Unblocks**:
- 8 documented carry-forwards closed (W4/W5/W6/W8/S2 from #2 +
  W23/W25/W26 from #5).
- v0.8.0 release ships with public API breaking change documented.
- The `drift_events.jsonl` audit trail is available for downstream
  consumers.
- The 21 missing BDD scenarios for REQ-10/12/13/14/16 are present
  (spec-vs-test gap closed since v0.3.0).
- The W23 dual-name coexistence is officially documented.

**Constrains**:
- Any future change that touches the `Finding`/`DriftReport`/
  `classify_binding` signature MUST NOT introduce new fields before v1.0
  (the `@property graph_unavailable` alias is the only backward-compat
  surface).
- The `drift_events.jsonl` schema is locked for v0.8.0 (`{ts, change,
  decision_id, binding_id, class, detected_at}`); any future change that
  adds a drift counter MUST add it to the
  `DRIFT_COUNTER_NAMES` catalog in `observability.py` and the
  `openspec/specs/observability/spec.md` domain table.

---

## Traceability (D1..D12 → OQ-N mapping)

| Decision | Resolves OQ | Maps to REQ | Implementation anchor |
|---|---|---|---|
| **D1** (Module layout: 1 NEW + 4 EXTEND) | — | REQ-55, REQ-56, REQ-57, REQ-59 | `src/flow_engineering/drift_event_log.py:1` (NEW) |
| **D2** (Hard migration + 1-release aliases) | **OQ-1** | REQ-56 (W8) | `src/flow_engineering/decision_drift.py:60-87` (MODIFY) |
| **D3** (10 MB rotation) | **OQ-2** | REQ-55 (W5) | `src/flow_engineering/drift_event_log.py:_rotate_if_needed()` (NEW) |
| **D4** (Silence when total==0 and not unable_to_verify) | **OQ-3** | REQ-55 (W6) | `src/flow_engineering/daemon.py:handle_apply_progress_event` (MODIFY) |
| **D5** (BDD translate from unit tests) | **OQ-5** | REQ-57 (W4) | 6 NEW `.feature` files + 6 NEW step glue files (NEW) |
| **D6** (Archived spec/design only) | **OQ-6** | REQ-58 (W25/W26) | 4 MODIFY archived files in `openspec/changes/archive/` |
| **D7** (CHANGELOG-only deprecation note) | **OQ-7** | REQ-59 (W23) | `CHANGELOG.md` v0.6.0 Notes section (MODIFY) |
| **D8** (Once-per-batch WARN with threshold) | **OQ-8** | REQ-59 (S2) | `src/flow_engineering/cli.py:_write_back_findings` (MODIFY) |
| **D9** (v0.8.0 version bump) | **OQ-1**, **OQ-4** | REQ-56 (W8) | `pyproject.toml:3` + `CHANGELOG.md` v0.8.0 entry |
| **D10** (Split BDD step glue per REQ) | — | REQ-57 (W4) | 6 NEW step glue files |
| **D11** (JSONL writer single-threaded) | — | REQ-55 (W5) | `src/flow_engineering/drift_event_log.py:record_drift_event()` (NEW) |
| **D12** (Apply batch sequencing A→B→C→D) | **OQ-4** | All 5 REQs | 4 batches × 3-4 commits each (per `work-unit-commits` skill) |
| (Additional decision) | **OQ-9** (defer read-side) | REQ-55 (deferred) | (out of scope — `flow drift events` CLI) |
| (Additional decision) | **OQ-10** (clean 2-arg break) | REQ-56 (W8) | `src/flow_engineering/decision_drift.py:classify_binding` 2-arg signature |

**OQ coverage summary**: All 10 open questions from proposal #223 §5 are
resolved by the D1-D12 architecture decisions above (OQ-1 → D2 + D9;
OQ-2 → D3; OQ-3 → D4; OQ-4 → D9 + D12; OQ-5 → D5; OQ-6 → D6; OQ-7 → D7;
OQ-8 → D8; OQ-9 → out-of-scope #1; OQ-10 → D2). No deferrals blocking
sdd-tasks.

---

## Chained PR Strategy

**SINGLE PR** (per proposal #223 recommendation A; below the
observability 10 910 chained-PR threshold).

| PR | Scope | Forecast prod LOC | Forecast test LOC | Realistic ×5.7 TDD | Acceptance |
|---|---|---|---|---|---|
| **PR#1** (drift-hardening) | All 5 REQs (REQ-55..59): NEW `drift_event_log.py` + `record_drift_event()` helper + 4 MODIFY prod files + 4 archived spec/design MODIFY + 6 NEW BDD feature files + 6 NEW step glue + 2 extend `req15_drift_daemon.feature` + CHANGELOG v0.8.0 + v0.6.0 Notes + pyproject bump + 6 SKILL.md updates | ~225 | ~1 600 | ~9 700 | All 947 existing tests pass + 25 new BDD scenarios + 30 new unit tests; `ruff check` clean; dataclass compat deprecation captured |

**Chain strategy**: stacked-to-main (consistent with prior 6 changes).
**400-line review budget risk**: medium — PR#1 is ~1 853 forecast /
~9 700 realistic, **close to** the chained-PR threshold (10 910 from
observability).

**Mitigation**: single PR with detailed commit splits per
`work-unit-commits` skill convention (12-14 commits each ≤400 LOC
across 4 batches; see D12 commit breakdown).

---

## Structured Metadata

- **decisions_count**: 12 (D1..D12)
- **open_questions_resolved**: 10/10 (all from proposal #223 §5)
- **open_questions_remaining**: 0
- **file_count**: 1 NEW prod + 5 MODIFY prod + 4 MODIFY archived spec/design + 1 NEW capability spec + 1 NEW unit test + 5 MODIFY unit tests + 6 NEW BDD features + 1 MODIFY BDD feature + 6 NEW step glue + 1 MODIFY step glue + 1 MODIFY CHANGELOG + 1 MODIFY pyproject.toml + 6 MODIFY SKILL.md = 39 total (15 NEW + 24 MODIFY)
- **loc_forecast**: ~225 production + ~1 600 test + ~28 archived spec/design + ~60 meta = ~1 913 total
- **realistic_x_tdd**: ~9 700 (×5.7 strict-TDD multiplier per
  `decision-code-linking` S3 precedent)
- **pr_count**: 1 (single PR; commits split per work-unit-commits
  convention for review tractability)
- **next_recommended**: `sdd-tasks drift-hardening`

---

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_drift_event_log_module",
      "label": "drift_event_log.py (NEW — ~150 LOC; record_drift_event + iter_drift_events + 10MB rotation; mirrors metrics.jsonl policy)",
      "file": "src/flow_engineering/drift_event_log.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_finding",
      "label": "Finding dataclass (decision_id: int post REQ-56 W8; __post_init__ str coercion + DeprecationWarning)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 60,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_drift_report",
      "label": "DriftReport dataclass (scanned_at: str ISO + unable_to_verify: bool + unable_reason: str | None post REQ-56 W8; @property graph_unavailable alias 1 release)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 70,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_classify_binding",
      "label": "classify_binding(ref, graph_nodes) — 2-arg post REQ-56 W8 (was 3-arg); current_id_map derived inside",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 84,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_drift_event",
      "label": "DriftEvent dataclass (NEW — REQ-55 W5; {ts, change, decision_id, binding_id, class, detected_at})",
      "file": "src/flow_engineering/drift_event_log.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_drift_event",
      "label": "record_drift_event() helper (NEW — REQ-55; emits drift_event_log_total counter + drift_event_log_bytes gauge; mirrors record_drift_summary)",
      "file": "src/flow_engineering/observability.py",
      "line": 462,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_drift_event_log_total",
      "label": "drift_event_log_total counter catalog entry (NEW — REQ-55; domain='drift'; labels: change)",
      "file": "src/flow_engineering/observability.py",
      "line": 462,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_drift_event_log_bytes",
      "label": "drift_event_log_bytes gauge catalog entry (NEW — REQ-55; domain='drift'; current file size post-rotation)",
      "file": "src/flow_engineering/observability.py",
      "line": 463,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_daemon_handle_apply_progress_event",
      "label": "handle_apply_progress_event (daemon.py:34-98) — MODIFY: REQ-55 wire record_drift_event + REQ-55 W6 still-valid silence rule + REQ-56 unable_to_verify rename",
      "file": "src/flow_engineering/daemon.py",
      "line": 34,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_daemon_start_watch",
      "label": "start_watch (daemon.py:144-210) — MODIFY: REQ-55 --drift-event-log flag (default-on) + --no-drift-event-log opt-out",
      "file": "src/flow_engineering/daemon.py",
      "line": 144,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_write_back_findings",
      "label": "_write_back_findings (cli.py:1637-1674) — MODIFY: REQ-59 S2 stderr WARN once per batch when skipped_total >= FLOW_DRIFT_SKIP_WARN_THRESHOLD (default 3)",
      "file": "src/flow_engineering/cli.py",
      "line": 1637,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_drift_daemon",
      "label": "flow drift daemon subcommand — MODIFY: REQ-55 --drift-event-log[=<path>] flag (default-on)",
      "file": "src/flow_engineering/cli.py",
      "line": 1500,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_get_skip_warn_threshold",
      "label": "_get_skip_warn_threshold() helper (NEW — REQ-59 S2; parses FLOW_DRIFT_SKIP_WARN_THRESHOLD env var; fall back to 3 on parse error)",
      "file": "src/flow_engineering/cli.py",
      "line": 1680,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_snapshot_manager_snapshot_meta",
      "label": "SnapshotMeta (snapshot_manager.py:100-121) — unchanged impl (REQ-58 W25 spec/design-only)",
      "file": "src/flow_engineering/snapshot_manager.py",
      "line": 100,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_snapshot_manager_prune_result",
      "label": "PruneResult (snapshot_manager.py:209-247) — unchanged impl (REQ-58 W26 spec/design-only)",
      "file": "src/flow_engineering/snapshot_manager.py",
      "line": 209,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_specs_drift_hardening_spec",
      "label": "openspec/specs/drift-hardening/spec.md (NEW — REQ-55..59 capability spec + dataclass shape contract + counter catalog; bootstraps drift-hardening capability)",
      "file": "openspec/specs/drift-hardening/spec.md",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_changes_archive_decision_reality_drift_design",
      "label": "openspec/changes/archive/2026-06-26-decision-reality-drift/design.md (lines 134-155) — MODIFY: REQ-56 reconcile dataclass types + REQ-55 REQ-15 JSONL contract",
      "file": "openspec/changes/archive/2026-06-26-decision-reality-drift/design.md",
      "line": 134,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_changes_archive_decision_reality_drift_spec",
      "label": "openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md — MODIFY: REQ-56 reconcile REQ-9..16 scenarios with new shape",
      "file": "openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_changes_archive_graph_snapshots_spec",
      "label": "openspec/changes/archive/2026-06-27-graph-snapshots/spec.md (line 230) — MODIFY: REQ-58 W26 freed_bytes field reconciliation",
      "file": "openspec/changes/archive/2026-06-27-graph-snapshots/spec.md",
      "line": 230,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_changes_archive_graph_snapshots_design",
      "label": "openspec/changes/archive/2026-06-27-graph-snapshots/design.md (line 271) — MODIFY: REQ-58 W25 size_bytes + pinned field documentation",
      "file": "openspec/changes/archive/2026-06-27-graph-snapshots/design.md",
      "line": 271,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_drift_event_log",
      "label": "tests/unit/test_drift_event_log.py (NEW — REQ-55 JSONL writer unit tests; ~180 LOC; rotation + append + schema + counter + OSError)",
      "file": "tests/unit/test_drift_event_log.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_decision_drift",
      "label": "tests/unit/test_decision_drift.py (MODIFY — REQ-56 dataclass shape + deprecation alias tests; +30 LOC)",
      "file": "tests/unit/test_decision_drift.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_daemon_drift_events",
      "label": "tests/unit/test_daemon_drift_events.py (MODIFY — REQ-55 event-log integration + W6 silence + unable_to_verify edge case; +20 LOC)",
      "file": "tests/unit/test_daemon_drift_events.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_cli_watch_drift",
      "label": "tests/unit/test_cli_watch_drift.py (MODIFY — REQ-55 CLI wiring + --drift-event-log flag; +10 LOC)",
      "file": "tests/unit/test_cli_watch_drift.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_cli_drift",
      "label": "tests/unit/test_cli_drift.py (MODIFY — REQ-59 S2 stderr WARN capture + threshold env var + per-batch cadence + REQ-56 cast site updates; +25 LOC)",
      "file": "tests/unit/test_cli_drift.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_observability",
      "label": "tests/unit/test_observability.py (MODIFY — REQ-55 2 catalog entry smoke tests; +10 LOC)",
      "file": "tests/unit/test_observability.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req10_drift_cli",
      "label": "tests/bdd/req10_drift_cli.feature (NEW — REQ-57 9 BDD scenarios for flow drift scan CLI surface)",
      "file": "tests/bdd/req10_drift_cli.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req11_drift_exit",
      "label": "tests/bdd/req11_drift_exit.feature (NEW — REQ-57 3 BDD scenarios for exit-code semantics)",
      "file": "tests/bdd/req11_drift_exit.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req12_drift_counters",
      "label": "tests/bdd/req12_drift_counters.feature (NEW — REQ-57 3 BDD scenarios for drift counters)",
      "file": "tests/bdd/req12_drift_counters.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req13_drift_metadata",
      "label": "tests/bdd/req13_drift_metadata.feature (NEW — REQ-57 3 BDD scenarios for update_observation_metadata)",
      "file": "tests/bdd/req13_drift_metadata.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req14_drift_resilience",
      "label": "tests/bdd/req14_drift_resilience.feature (NEW — REQ-57 4 BDD scenarios for resilience)",
      "file": "tests/bdd/req14_drift_resilience.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req16_skill_prose",
      "label": "tests/bdd/req16_skill_prose.feature (NEW — REQ-57 2 BDD scenarios for SKILL.md grep)",
      "file": "tests/bdd/req16_skill_prose.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req15_drift_daemon",
      "label": "tests/bdd/req15_drift_daemon.feature (MODIFY — REQ-55 2 new scenarios for JSONL event-log + W6 silence + unable_to_verify edge case; +80 LOC)",
      "file": "tests/bdd/req15_drift_daemon.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_req10_drift_cli_steps",
      "label": "tests/bdd/test_req10_drift_cli_steps.py (NEW — step glue for req10_drift_cli.feature per D10 per-REQ split)",
      "file": "tests/bdd/test_req10_drift_cli_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_req11_drift_exit_steps",
      "label": "tests/bdd/test_req11_drift_exit_steps.py (NEW — step glue for req11_drift_exit.feature)",
      "file": "tests/bdd/test_req11_drift_exit_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_req12_drift_counters_steps",
      "label": "tests/bdd/test_req12_drift_counters_steps.py (NEW — step glue for req12_drift_counters.feature)",
      "file": "tests/bdd/test_req12_drift_counters_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_req13_drift_metadata_steps",
      "label": "tests/bdd/test_req13_drift_metadata_steps.py (NEW — step glue for req13_drift_metadata.feature)",
      "file": "tests/bdd/test_req13_drift_metadata_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_req14_drift_resilience_steps",
      "label": "tests/bdd/test_req14_drift_resilience_steps.py (NEW — step glue for req14_drift_resilience.feature)",
      "file": "tests/bdd/test_req14_drift_resilience_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_req16_skill_prose_steps",
      "label": "tests/bdd/test_req16_skill_prose_steps.py (NEW — step glue for req16_skill_prose.feature)",
      "file": "tests/bdd/test_req16_skill_prose_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_decision_reality_drift_steps",
      "label": "tests/bdd/test_decision_reality_drift_steps.py (MODIFY — REQ-55 extend step glue for 2 new req15_drift_daemon scenarios; +100 LOC)",
      "file": "tests/bdd/test_decision_reality_drift_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "changelog_v080_entry",
      "label": "CHANGELOG.md v0.8.0 entry (NEW — 5 REQs + W23 deprecation note + BREAKING section for REQ-56)",
      "file": "CHANGELOG.md",
      "line": 162,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "pyproject_toml_version",
      "label": "pyproject.toml version (line 3) — MODIFY: 0.7.0 → 0.8.0 (REQ-56 breaking change mandates minor bump)",
      "file": "pyproject.toml",
      "line": 3,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_design_skill_md_drift_hardening_hook",
      "label": "~/.config/opencode/skills/sdd-design/SKILL.md (MODIFY — drift-hardening hook prose; ~15 docs LOC)",
      "file": "~/.config/opencode/skills/sdd-design/SKILL.md",
      "line": 1,
      "confidence": 0.7,
      "source": "manual"
    }
  ]
}
