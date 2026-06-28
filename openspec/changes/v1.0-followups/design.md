<!-- design.md: v1.0-followups. Source: sdd-design sub-agent. -->
# Design: v1.0-followups

> Mirror of Engram `sdd/v1.0-followups/design` (topic_key upsert after file
> creation). Reference format mirrors
> [`openspec/changes/archive/2026-06-27-drift-hardening/design.md`](../archive/2026-06-27-drift-hardening/design.md)
> (D1..D5 + Open Questions table + code_refs block). All 6 open questions
> from proposal §"Open Questions" are pre-resolved by orchestrator
> (S1 Option A + S2 Path B + Path A trade-off explicit). The Engram
> `code_refs` block is appended at file end so `flow inspect <change>`
> can render the binding surface.

```yaml
status: success
confidence: high
open_questions_resolved: 6/6
architecture_decisions: 5  # D1..D5
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v1.0-followups\design.md
next_recommended: sdd-tasks v1.0-followups
strict_tdd: true
chain_strategy: not_applicable
pr_split: single PR  # ~350 LOC delta; well under 400 LOC chained-PR threshold
wall_time_estimate: ~2h end-to-end
```

## Status

**designed → ready for `sdd-tasks v1.0-followups`**. All 6 open questions
from the proposal (OQ-1..OQ-6) are pre-resolved by orchestrator pre-decisions
(S1 Option A + S2 Path B). The 2 SUGGESTION items from the drift-hardening
verify-report + the 12 mypy residuals from v0.9.0 are mapped to 4 REQs
(REQ-V1.0.1..V1.0.4) with 5 architecture decisions (D1..D5). Doc drift in
`archive/2026-06-27-drift-hardening/verify-report.md:296` (says
`iter_drift_events()`; actual helper is `DriftEventLog.read_all()` at
`src/flow_engineering/drift_event_log.py:95-119`) is corrected via D2.

---

## Goal

`v1.0-followups` closes the **2 deferred SUGGESTION items from the
drift-hardening verify-report** + the **12 mypy residuals from v0.9.0**
in a single small TDD change that finalizes the `decision-drift`
capability spec at v1.0 without re-opening any closed carry-forward:

- **S1** — `DriftEvent.decision_id: str` (JSONL wire format) vs
  `Finding.decision_id: int` (Python dataclass) inconsistency. The
  Python side hard-broke to `int` in v0.9.0; the JSONL side never
  caught up. **D1** flips the wire format to `int`; **D2** adds a
  defensive coercion for legacy `str` lines so old JSONL files remain
  readable without migration.
- **S2** — `flow drift <change>` is write-only. Operators have been
  asking for a read-side CLI since v0.8.0. **D3** ships a new
  `flow drift-events {list,tail,stats}` Click group (Path B, parallel
  command — NON-BREAKING for `flow drift <change>` callers). **D4**
  locks the output shape (fixed-width text table by default + JSON +
  Prometheus + CSV via `--format`).
- **Tech-debt closure** — 12 mypy residuals in `decision_drift.py`
  flagged by v0.9.0 verify-report S3 (per capability spec
  `decision-drift/spec.md:410`). **D5** resolves them via surgical
  `# type: ignore[arg-type]` comments at the 12 expected sites —
  intentional because the `Finding.__post_init__` TypeError-on-str
  enforcement sites are tested behavior, not drift.

The HEAD at `8b02d38` has **1233/1233 tests passing** (per capability
spec `decision-drift/spec.md:57` baseline). Strict TDD is ON. v1.0 is
intentionally NOT a feature release — it's the **last debt-closure
release** before the project enters the v1.x feature cycle.

### Carry-forwards resolved by this design

| Source | Item | Design decision |
|---|---|---|
| `drift-hardening` verify-report #296 S1 | `DriftEvent.decision_id: str` (JSONL wire format) vs `Finding.decision_id: int` (Python) inconsistency | **D1 + D2** — flip to `int` + defensive coercion |
| `drift-hardening` verify-report #296 S2 | `flow drift events` read-side CLI deferred to v1.0 | **D3** — new `flow drift-events {list,tail,stats}` group (Path B) |
| `v0.9.0-hardening` verify-report S3 | 12 mypy residuals in `decision_drift.py` within expected band | **D5** — `# type: ignore[arg-type]` at 12 sites |
| `drift-hardening` verify-report #296 | `iter_drift_events()` doc drift (verify-report says this name; actual is `read_all()`) | **D2** — design uses the real symbol name `DriftEventLog.read_all()` |

---

## Architecture Overview

`v1.0-followups` adds a **type annotation flip + defensive read guard**
on the existing `DriftEvent` JSONL sink that `drift-hardening` v0.8.0
shipped — and **adds a new parallel read-side Click command group**
that mirrors the `flow metrics {summary,export,aggregate}` pattern
from observability PR#2 (`openspec/changes/archive/2026-06-27-observability-pr2/verify-report-pr2.md:124-148`
W1 subcommand-group precedent). **Write-side grows additively with a
type-flip** (D1 + D2); **read-side gains a NEW top-level Click group**
(D3) with 3 subcommands mirroring the `flow metrics` 3-subcommand
precedent; **tech-debt closure is doc-only at 12 sites** (D5); the
`openspec/specs/decision-drift/spec.md` baseline gains a
`## Drift event log JSONL schema` section + the v1.0 capability entry
in the Versioning table. NO new modules, NO new public API surface
beyond the new Click group, NO new third-party deps.

Three cooperating pieces (matches proposal §"Architecture (Approach A) pieces 1-3"):

1. **`DriftEvent` dataclass type-flip + daemon coercion removal** (MODIFY)
   — `decision_id: str` → `int` at `drift_event_log.py:46`; the
   `str(finding.decision_id)` coercion at `daemon.py:60` is removed
   (Finding is already int post-v0.9.0); docstring at `daemon.py:46-51`
   drops the "Future v1 follow-up may flip..." note. Powers D1.
2. **`DriftEventLog.read_all()` defensive guard** (MODIFY at
   `drift_event_log.py:95-119`) — legacy `decision_id: "42"` (str)
   lines are coerced to `int` with a one-time stderr WARN per
   log-path (per-instance flag; mirrors `_write_back_findings`
   skip-warn cadence per `cli.py:1703-1709` D8 precedent). Powers D2.
3. **NEW `flow drift-events {list,tail,stats}` Click group** (NEW in
   `cli.py:~1712+`) — parallel to `@main.command() def drift(...)` at
   `cli.py:1712-1809`; mirrors the `flow metrics` group pattern from
   observability PR#2 (D3 + D4). Powers D3 + D4.

```
   ┌──────────────────────────────────┐
   │  flow drift <change_name>        │   EXISTING — unchanged (write-side scan)
   │  flow drift --json               │   (cli.py:1712-1809; REQ-10..14 + REQ-33)
   └─────────┬────────────────────────┘
             │
             ▼
   ┌──────────────────────────────────────────────────────────┐
   │  src/flow_engineering/decision_drift.py  (D1)            │
   │  Finding.decision_id: int                  (unchanged v0.9.0)
   │  DriftEvent.decision_id: int  ← D1 (was str)             │
   └──────┬────────────────────────────┬─────────────────────┘
          │                            │
          ▼                            ▼
   ┌─────────────────────┐    ┌──────────────────────────────────┐
   │ daemon.py           │    │  drift_event_log.py (D1 + D2)    │
   │ _append_drift_events│───►│  DriftEvent(decision_id: int)    │
   │  - str() coercion   │    │  to_json_dict() emits int        │
   │    REMOVED (D1)     │    │  read_all() defensive coercion   │
   │                     │    │   (legacy str → int + WARN)      │
   └──────┬──────────────┘    └─────────┬────────────────────────┘
          │                             │
          ▼                             ▼
   ┌─────────────────────────┐  ┌────────────────────────────────────┐
   │ observability.py        │  │  ~/.flow-engineering/              │
   │ record_drift_summary()  │  │    drift_events.jsonl              │
   │  (unchanged)            │  │  v1.0 wire format:                 │
   │                         │  │   {"decision_id": 42, ...}  ← D1   │
   └─────────────────────────┘  └─────────┬──────────────────────────┘
                                           │
                                           ▼
                              ┌────────────────────────────────────┐
                              │  cli.py: NEW Click group (D3)      │
                              │  flow drift-events {               │
                              │    list --since --until --change   │
                              │         --event-class --limit      │
                              │         --format text|json|        │
                              │                prometheus|csv     │
                              │    tail --limit=N=10 ...           │
                              │    stats --change --since --until  │
                              │          --format text|json        │
                              │  }                                 │
                              └────────────────────────────────────┘
                                           │
                                           ▼
                              ┌────────────────────────────────────┐
                              │  prometheus_exposition (REQ-38)    │
                              │  reuse for --format=prometheus     │
                              └────────────────────────────────────┘
```

Architecture seams respected (verified):
- `decision_drift.Finding.decision_id: int` is UNCHANGED (already hard-int
  post-v0.9.0 per `decision_drift.py:79` + REQ-V9.4 enforcement at
  `decision_drift.py:84-90`). The wire-format flip is **internal to
  `DriftEvent` serialization only** — it does NOT affect the
  `flow drift <change>` CLI output, the `flow drift --json` envelope,
  or the Engram metadata write-back path.
- `drift_event_log.DriftEventLog.append()` is unchanged in signature
  (still accepts `DriftEvent`); only `DriftEvent` field types change.
  `daemon._append_drift_events` loses one `str()` coercion call at
  `daemon.py:60`; the surrounding loop + counters stay byte-identical.
- `observability.record_drift_summary()` byte-identical; no new helpers.
- `flow drift <change>` CLI surface unchanged (D3 Path B is
  parallel-namespace, NOT BREAKING).
- 12 mypy residuals in `decision_drift.py` are at intentional
  `__post_init__` TypeError-on-str enforcement test sites; adding
  `# type: ignore[arg-type]` is the documented resolution per
  `v0.9.0-hardening` verify-report S3 + capability spec `spec.md:410`.

Files touched: **15** total — 4 MODIFY prod files, 1 NEW prod surface
(NEW Click group within `cli.py`), 2 MODIFY test files, 3 NEW unit
test files, 2 NEW BDD feature files, 2 NEW BDD step-glue files,
1 MODIFY capability spec, 1 MODIFY CHANGELOG, 1 MODIFY pyproject.toml,
6 MODIFY SKILL.md runtime files (atomic per drift-hardening
`--allow-empty` precedent).

---

## Open Questions Resolution (all 6 from proposal §"Open Questions")

### OQ-1: S1 — `DriftEvent.decision_id` type?

**Decision**: **Option A — flip to `int`** (orchestrator pre-decided).
Flips `DriftEvent.decision_id: str` → `int` at
`drift_event_log.py:46`. Matches `Finding.decision_id: int` post-v0.9.0
hard break at `decision_drift.py:79` (already enforced via
`Finding.__post_init__` at `decision_drift.py:84-90`). Aligns with
capability spec `decision-drift/spec.md:408+410` v1.0 plan verbatim.
Single source of truth.

**Rationale**: Post-v0.9.0 the Python dataclass is already `int` (hard
break). The `str` on the wire was a backward-compat artifact from
v0.7.x pre-REQ-56 wire format (archived spec #135 line 272). The
operators who pipe `decision_id` to `int()`-expecting scripts now get
the right type for free. The operators who compare as string
(`"42" < "9"`) get a behavior change that the CHANGELOG v1.0 `sed`
migration note + the one-time stderr WARN from D2 surface.

**Alternatives considered**:
- **Option B — flip `Finding.decision_id` back to `str`**:
  REJECTED — would undo the v0.9.0 hard break (REQ-V9.4) shipped 1 day
  ago (HEAD `3de7783` → `8b02d38` is 12 commits of doc cleanup). All
  v0.9.0 callers would break; 1232/1232 test count invalidates.
- **Option C — add `decision_id_int` alongside `decision_id: str`**:
  REJECTED — API bloat; two-source-of-truth; confusing for consumers.
- **Option D — keep both as-is + `.decision_id_int` accessor**:
  REJECTED — same bloat + runtime cost per access.

**Affects**: D1 + D2 + `drift_event_log.py:46` + `daemon.py:60`.

### OQ-2: S1 — read-side compat shim for legacy `str` JSONL lines?

**Decision**: **YES — defensive coercion in `DriftEventLog.read_all()`**
(orchestrator pre-decided). Adds a per-instance `_legacy_warn_emitted`
flag + a one-time stderr WARN when a legacy `str` line is coerced to
`int`. Mirrors the v0.9.0 soft-migration pattern at
`decision_drift.py:84-90` (`Finding.__post_init__` enforcement site)
and the `_write_back_findings` skip-warn cadence per
`cli.py:1703-1709` (D8 precedent from drift-hardening).

**Rationale**: Pre-v1.0 JSONL files remain readable without migration
— zero data loss. The one-time WARN surfaces the issue to operators
on first read so they know to run the CHANGELOG v1.0 `sed` migration.
Per-instance flag (NOT module-global) so multi-log CLI invocations
each get their own WARN (correct cadence).

**Alternatives considered**:
- **Silent skip** (no coercion): REJECTED — loses the audit trail;
  the JSONL is a read-only best-effort sink.
- **Hard fail on legacy lines**: REJECTED — breaks pre-v1.0 reads;
  no migration path for operators with existing JSONL files.

**Affects**: D2 + `drift_event_log.py:95-119` (`read_all()` body).

### OQ-3: S1 — migration guide for existing JSONL consumers?

**Decision**: **YES — 1-line `sed` in CHANGELOG v1.0 entry**
(orchestrator pre-decided).

```bash
sed -i 's/"decision_id": "\([0-9]*\)"/"decision_id": \1/g' \
  ~/.flow-engineering/drift_events.jsonl
```

**Rationale**: Mirrors the W23 `snapshot_pruned_total` →
`snapshot_prune_total` precedent from `drift-hardening/design.md`
(D7 + CHANGELOG v0.6.0 Notes section). Operators who want to convert
in-place run the `sed`; operators who don't care about exact wire
format rely on the D2 defensive coercion. Zero data loss either way.

**Alternatives considered**:
- **No migration note** (silent coercion only): REJECTED — leaves
  operators guessing about the JSONL contract change.
- **Migration tool** (`flow drift-events migrate --in-place`):
  REJECTED — ceremony without payoff for a 1-line `sed`.

**Affects**: CHANGELOG.md v1.0 entry.

### OQ-4: S2 — subcommand group vs parallel command?

**Decision**: **Path B — parallel command `flow drift-events {list,tail,stats}`**
(orchestrator pre-decided; Path A flagged as alternative). NON-BREAKING;
preserves the existing `flow drift <change>` callers. Path A (BREAKING
subcommand group `flow drift check <change>` + `flow drift events ...`)
is more idiomatic with `flow metrics {summary,export,aggregate}` but
BREAKS every existing caller.

**Rationale**: Operator-UX continuity > namespace consistency. The
`flow drift <change>` callers include CI pipelines, hooks, and
documentation snippets; a BREAKING rename forces every caller to
migrate. Path B's parallel-namespace is slightly less elegant but
zero-friction. Document the parallel-namespace rationale in CHANGELOG
v1.0 entry. Revisit Path A in v1.2+ if the `flow drift` namespace
grows further.

**Alternatives considered**:
- **Path A — BREAKING subcommand group rename**: REJECTED by default;
  available as orchestrator override if namespace consistency > UX
  continuity.

**Affects**: D3 + `cli.py:~1712+` (NEW Click group).

### OQ-5: S2 — which subcommands?

**Decision**: **`list` + `tail` + `stats`** (capability spec + drift-
hardening + v0.9.0-hardening archives unanimous).

- **`list`** — default text/JSON table with `--since`/`--until`/
  `--change`/`--event-class`/`--limit` filters + 4 formats
  (`text`/`json`/`prometheus`/`csv`). REQ-V1.0.2.
- **`tail`** — last N events newest-first; default `--limit=10` +
  `--change` + `--event-class` filters + 2 formats (`text`/`json`).
  REQ-V1.0.3.
- **`stats`** — per-event-class counts + per-change counts +
  per-decision-id top-N counts in a fixed-width table; `--change` +
  `--since` + `--until` filters + 2 formats (`text`/`json`).
  REQ-V1.0.3.

Mirrors `flow metrics {summary,export,aggregate}` 3-subcommand
precedent (observability PR#2 verify-report-pr2.md:124-148 W1).
Exit codes mirror D9 (`0=success`, `2=invalid args`, `3=malformed JSONL`).

**Rationale**: 3 subcommands give operators full lifecycle (read /
monitor / summarize) without scope creep. Mirrors `flow metrics`
operator mental model. Each subcommand has a distinct primary use:
`list` = inspect, `tail` = monitor, `stats` = aggregate.

**Alternatives considered**:
- **`list` only** (no `tail`/`stats`): REJECTED — operators asked
  for both; `tail` is the natural monitoring surface.
- **`list` + `tail` only**: REJECTED — `stats` is the natural
  dashboard surface; matches `flow metrics summary`.

**Affects**: D3 + D4 + `cli.py:~1712+`.

### OQ-6: S2 — `--format=prometheus|csv` for events?

**Decision**: **YES — landing in v1.0** (capability spec pre-decided
at `decision-drift/spec.md:408+410` + v0.9.0-hardening tasks.md:159).
`--format=text|json|prometheus|csv` on `flow drift-events list`.

**Rationale**: Prometheus textfile parity with `flow metrics export
--format=prometheus` (REQ-38 from observability PR#2) is the
operator-mental-model transfer. CSV is the standard JSONL-consumer
export format. Both formats reuse existing helpers from observability
PR#2 + stdlib `csv` — zero new deps.

**Alternatives considered**:
- **Text + JSON only** (defer prometheus|csv to v1.1): REJECTED —
  capability spec explicitly lists v1.0 scope; v1.1 would be needless
  churn.

**Affects**: D4 + `cli.py:~1712+` (`list` subcommand 4-format handlers).

---

## Decisions

### D1: `DriftEvent.decision_id: int` (was `str`) — Option A

**Choice**: Flip `DriftEvent.decision_id: str` → `int` at
`drift_event_log.py:46` (1-line type annotation change). Remove the
`str(finding.decision_id)` coercion at `daemon.py:60` (1-line edit
in the `_append_drift_events` loop body). Update the docstring at
`daemon.py:46-51` to drop the "Future v1 follow-up may flip..." note
(now done in v1.0). `to_json_dict()` at `drift_event_log.py:51-59`
emits the int naturally (no code change needed — JSON serialization
follows the dataclass type).

**Rationale**: Matches `Finding.decision_id: int` post-v0.9.0 hard
break at `decision_drift.py:79` (already enforced via
`Finding.__post_init__` at `decision_drift.py:84-90`). Single source
of truth (Python and JSON wire formats align). Aligns with capability
spec `decision-drift/spec.md:408+410` v1.0 plan verbatim ("DriftEvent
JSONL `decision_id: int` wire-format flip (S1 from drift-hardening)").
Minimal API surface change (1 dataclass field + 1 coercion removal).

**Trade-offs**:
- ✅ Pro: matches Python dataclass; minimal API change; aligns with
  capability spec; single source of truth.
- ✅ Pro: zero new runtime deps; zero new modules; ~2 prod LOC delta.
- ❌ Con: BREAKING wire format (mitigated by D2 defensive coercion +
  CHANGELOG v1.0 `sed` migration note per OQ-3).

**Affects**: REQ-V1.0.1 + `drift_event_log.py:46` + `daemon.py:60` +
`daemon.py:46-51` docstring. ~2 prod LOC delta.

### D2: `DriftEventLog.read_all()` defensive coercion for legacy `str` lines

**Choice**: Add a per-instance `_legacy_warn_emitted: bool = False`
flag in `DriftEventLog.__init__()` (at `drift_event_log.py:72-79`) +
a defensive coercion block in `read_all()` at
`drift_event_log.py:95-119`. When `data["decision_id"]` is `str`,
coerce to `int` and emit a one-time stderr WARN:
```
warning: legacy str decision_id in <path>; coercing to int. Run the
         CHANGELOG v1.0 sed migration to silence.
```

**Rationale**: Pre-v1.0 JSONL files (with `decision_id: "42"` str)
remain readable without migration — zero data loss. Mirrors the
`_write_back_findings` skip-warn cadence per `cli.py:1703-1709` (D8
precedent from drift-hardening — once-per-batch with threshold; here
once-per-process-per-log-path via per-instance flag). The per-instance
flag (NOT module-global) ensures multi-log CLI invocations each get
their own WARN (correct cadence).

**Trade-offs**:
- ✅ Pro: zero data loss; backward-compat for pre-v1.0 JSONL; one-
  time WARN surfaces the issue to operators; per-instance cadence is
  correct for multi-log invocation.
- ❌ Con: ~5 prod LOC delta (1 flag + 1 try/coerce + 1 stderr print).
- ❌ Con: silent-coercion acceptance is a footgun if operators ignore
  the WARN (mitigated by CHANGELOG v1.0 `sed` migration note).

**Doc drift fix**: Uses the REAL symbol name `DriftEventLog.read_all()`
(NOT `iter_drift_events()` as the stale
`archive/2026-06-27-drift-hardening/verify-report.md:296` says).
Verified at `drift_event_log.py:95-119`.

**Affects**: REQ-V1.0.1 + `drift_event_log.py:72-79` + `drift_event_log.py:95-119`.
~5 prod LOC delta. 1 NEW test for the legacy coercion + 1 NEW test
for the one-time WARN cadence.

### D3: NEW `flow drift-events {list,tail,stats}` Click group (Path B, parallel command)

**Choice**: Add `@main.group(name="drift-events") def drift_events_group()`
+ 3 subcommands (`list`, `tail`, `stats`) at `cli.py:~1712+`. The
existing `@main.command() def drift(...)` at `cli.py:1712-1809`
stays UNCHANGED (Path B = parallel namespace, NON-BREAKING for
`flow drift <change>` callers).

```python
@main.group(name="drift-events")
def drift_events_group() -> None:
    """Read drift events from ~/.flow-engineering/drift_events.jsonl (REQ-V1.0.2 + REQ-V1.0.3).

    Path B (parallel command — preserves the `flow drift <change>`
    surface). Subcommands: list, tail, stats. Mirrors `flow metrics
    {summary,export,aggregate}` flag set so the operator mental model
    transfers.
    """
```

**Rationale**: Mirrors the observability PR#2 subcommand-group
precedent at `verify-report-pr2.md:124-148` W1 (the spec wanted
`--prometheus`/`--percentile` FLAGS; impl shipped SUBCOMMANDS; the
drift was accepted because subcommand shape matches CHANGELOG + BDD
+ impl + user docs). Path B preserves `flow drift <change>` callers
(operator-UX continuity > namespace consistency per OQ-4). Slightly
less elegant than Path A's subcommand group `flow drift check <change>`
+ `flow drift events ...`, but zero migration friction.

**Trade-offs**:
- ✅ Pro: NON-BREAKING; mirrors `flow metrics` operator mental model;
  preserves existing CI pipelines + hooks + docs; ~80 prod LOC delta.
- ❌ Con: parallel-namespace is less elegant than subcommand group;
  document the rationale in CHANGELOG v1.0 entry (mitigates the
  inconsistency).

**Flag design (modeled after `flow metrics {summary,export,aggregate}`)**:

| Subcommand | Flags | Formats |
|---|---|---|
| `flow drift-events list` | `--since=<iso>`, `--until=<iso>`, `--change=<name>`, `--event-class=<LABEL_DRIFT\|...>`, `--limit=<N>`, `--path=<alt-log>` | `text` (default), `json`, `prometheus`, `csv` |
| `flow drift-events tail` | `--limit=<N>=10`, `--change=<name>`, `--event-class=<...>` | `text` (default), `json` |
| `flow drift-events stats` | `--change=<name>`, `--since=<iso>`, `--until=<iso>` | `text` (default), `json` |

**Exit codes (per D9 convention from drift-hardening)**:
- `0` success (or empty result)
- `2` invalid args (e.g., `--since` parse error, unknown `--format`)
- `3` malformed JSONL (mirrors observability PR#2 D9 exit code 3 for
  malformed metrics file)

**Affects**: REQ-V1.0.2 + REQ-V1.0.3 + `cli.py:~1712+`. ~80 prod LOC
delta. 2 NEW BDD feature files + 2 NEW BDD step-glue files +
3 NEW unit test files.

### D4: Default text = fixed-width table; JSON + Prometheus + CSV via `--format`

**Choice**: Default text output for `flow drift-events {list,tail,stats}`
is a **fixed-width table** mirroring `flow metrics summary` at
`cli.py:977` + `flow drift <change>` at `cli.py:1807 _render_drift_table`.
`--format=json` mirrors `flow drift <change> --json` at
`cli.py:1798-1805` + `flow metrics --json`. `--format=prometheus`
reuses the `prometheus_exposition` module from observability PR#2
(REQ-38) at `src/flow_engineering/observability.py:945-983` — emits
textfile format with `# HELP`/`# TYPE`/`# EOF` per design D6.
`--format=csv` uses stdlib `csv` (zero new deps).

**Rationale**: Operators expect `flow <x>` to default to a human-
readable text table (mirrors every existing `flow` subcommand).
JSON is the standard machine-readable surface. Prometheus reuses
the proven `prometheus_exposition` helper (zero new code). CSV is
the standard JSONL-consumer export format. All 4 formats reuse
existing helpers + stdlib — zero new deps.

**Trade-offs**:
- ✅ Pro: operator mental model transfer (`flow metrics summary` →
  `flow drift-events list`); reuses `prometheus_exposition` (no new
  code for prom format); zero new deps.
- ❌ Con: 4 format handlers per subcommand (`list` × 4 = 4 handlers;
  `tail` × 2 = 2 handlers; `stats` × 2 = 2 handlers) = ~8 format
  handlers total (~30 prod LOC).

**Affects**: REQ-V1.0.2 + `cli.py:~1712+` (list + tail + stats
subcommand bodies). ~30 prod LOC delta.

### D5: 12 mypy residuals via surgical `# type: ignore[arg-type]` (NOT full type fixes)

**Choice**: Add `# type: ignore[arg-type]` comments at the 12 mypy
residual sites in `decision_drift.py`:

| Line | Function / call | Reason |
|---|---|---|
| `decision_drift.py:127` | `classify_binding(ref, graph_nodes: dict[str, dict])` — the v0.9.0 2-arg signature drops the legacy `current_id_map` arg; test sites pass it for backward-compat coverage | intentional `__post_init__` TypeError-on-str enforcement test site |
| `decision_drift.py:161` | `_classify_with_id_map(binding, current_nodes, current_id_map)` 3-arg helper (the v0.8.0 3-arg legacy) | intentional test helper for v0.9.0 W3 removal coverage |
| `decision_drift.py:203` | `load_graph(...)` 3-tuple return type annotation includes `dict \| None` | intentional JSON-loaded shape tolerance |
| `decision_drift.py:252` | `_index_graph_payload(nodes: list, mtime)` — `list` is generic; mypy strict wants `list[dict]` | JSON-loaded shape tolerance |
| `decision_drift.py:253` | `_index_graph_payload` return `tuple[dict \| None, ...]` | same as 203 |
| `decision_drift.py:262` | `current_nodes: dict[str, dict] = {}` inside `_index_graph_payload` | mypy strict `untyped dict` |
| `decision_drift.py:278` | `_load_graph_from_snapshot(snap_id)` return `tuple[dict \| None, ...]` | same as 203 |
| `decision_drift.py:310` | `SnapshotManager(snapshots_dir=snapshots_dir, backend=_DummyBackend())` — `_DummyBackend` doesn't fully implement `EngramBackend` | intentional stub for the snap-id branch |
| `decision_drift.py:372` | `_DummyBackend.iter_observations(*, project=None)` — `# pragma: no cover` | unreachable per the design docstring |
| `decision_drift.py:375` | `_DummyBackend.mem_search(*args, **kwargs)` — `# pragma: no cover` | unreachable per the design docstring |
| `decision_drift.py:411` | `SnapshotManager(snapshots_dir=..., backend=_DummyBackend())` in `_snapshot_has_graph` | same as 310 |
| `decision_drift.py:439` | `SnapshotManager(snapshots_dir=..., backend=_DummyBackend())` in `_frozen_backend_from_snapshot` | same as 310 |

**Rationale**: All 12 sites are **intentional tolerance test sites**
or **intentional stub-method sites** (the `_DummyBackend` is
unreachable per the design docstring at `decision_drift.py:364-370`).
Full type fixes would require either (a) tightening the dataclass
types (breaks the JSON-loaded shape tolerance that the drift
detector relies on), or (b) implementing `_DummyBackend` fully
(unreachable code that bloats the module). The `# type: ignore[arg-type]`
comment is the documented v0.9.0 W1-recommended fix precedent at
`v0.9.0-hardening/proposal.md:V9.2.8` (3 sites cleaned via this
pattern in v0.9.0; v1.0 cleans the remaining 12). Per v0.9.0
verify-report S3 + capability spec `spec.md:410` "S3 mypy
annotations": "12 mypy residuals in `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439`".

**Trade-offs**:
- ✅ Pro: intentional and documented (v0.9.0 W1-recommended fix
  precedent); 1-line edit per site = 12 LOC total; zero behavior
  change; mypy error count drops 12 → 0 in `decision_drift.py`.
- ❌ Con: `# type: ignore` comments are maintenance noise — future
  refactors that genuinely need a type fix here will be masked.
  Mitigation: every site has a comment explaining WHY the ignore is
  intentional (mirrors the v0.9.0 W1 fix precedent).

**Affects**: REQ-V1.0.4 + `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439`.
~12 prod LOC delta (1 comment per site + optional WHY comment).

---

## Risks (mirrors proposal §"Risks" — 5 LOW from proposal)

| ID | Severity | Pattern | Evidence | Mitigation |
|----|----------|---------|----------|------------|
| **R1** | LOW | Wire-format BREAKING (S1) | `DriftEvent.decision_id` flips from `str` → `int`; old `cat ~/.flow-engineering/drift_events.jsonl \| jq` consumers that piped the field to an `int()`-expecting script will now work without coercion (good); consumers that compared as string ("42" < "9" lex sort) will see behavior change (bad but rare). | D2 defensive read guard (silent coercion + one-time stderr WARN); CHANGELOG v1.0 1-line `sed` migration note (OQ-3). |
| **R2** | LOW | Read-side compat shim silently drops unparseable old lines (S1) | `DriftEventLog.read_all()` will silently coerce legacy `str` lines to `int`; if the coercion fails on a non-numeric string, the line is silently skipped (mirrors the existing malformed-line silent-skip behavior at `drift_event_log.py:117`). | Per-task TDD with RED test before GREEN impl (V1.0.1.1 + V1.0.4.1); 1 test for happy-path int + 1 test for legacy str coercion + 1 test for one-time WARN cadence; smoke test against a pre-v1.0 JSONL fixture in `tests/fixtures/drift_events_v090_legacy.jsonl` to verify the read path round-trips. |
| **R3** | LOW | Path B parallel namespace is less elegant than Path A subcommand group | `flow drift-events` is a sibling command to `flow drift`, not a subcommand. Inconsistent with `flow metrics {summary,export,aggregate}` group pattern (per observability PR#2 W1 precedent). | Document the parallel-namespace rationale in CHANGELOG v1.0 entry (Path A is BREAKING; Path B preserves operator-UX continuity for `flow drift <change>` callers); revisit Path A in v1.2+ if `flow drift` namespace grows. |
| **R4** | LOW | Doc drift in `archive/2026-06-27-drift-hardening/verify-report.md:296` | The verify-report says `DriftEventLog.read_all()` helper "already exists at `drift_event_log.py` as `iter_drift_events()`". **The actual helper is `read_all()`** at `drift_event_log.py:95-119`. The verify-report's name is stale. | This design uses the real symbol name `DriftEventLog.read_all()` (D2). Optional post-archive drift-note in the archived `verify-report.md:296` (1-line edit; non-blocking). |
| **R5** | LOW | 12 mypy residuals in `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439` | Per v0.9.0 verify-report S3 + capability spec `spec.md:410`: within expected band for `__post_init__` TypeError-on-str enforcement sites + JSON-loaded shape tolerance sites + unreachable `_DummyBackend` stub sites. | D5 cleanup adds `# type: ignore[arg-type]` to the 12 sites (1 comment per site; ~12 LOC); matches the v0.9.0 W1 fix precedent at `proposal.md:V9.2.8` (3 sites cleaned in v0.9.0; v1.0 closes the remaining 12). |

**0 CRITICAL / 0 HIGH / 5 LOW risks.** All mitigations are within the
proposed REQ scope or already-documented as low-priority follow-ups.

### Carry-forwards explicitly NOT touched by this design (deferred)

| Source | Item | Deferral target | Notes |
|---|---|---|---|
| `drift-hardening` verify-report #242 W7 | `DriftEventLog` JSONL rotation (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var + auto-rotation at threshold) | v1.1 | The v0.8.0 10 MB hardcoded rotation never landed; deferred to v1.1 alongside `metrics.jsonl` rotation (REQ-44 deferred) per capability spec `spec.md:410`. |
| v0.9.0 capability spec + drift-hardening design D5 | `flow drift-events` Path A subcommand group rename (BREAKING) | v1.2+ | Path A is more idiomatic with `flow metrics {summary,export,aggregate}` but BREAKING; Path B is non-breaking; v1.0 ships Path B (revisit only if `flow drift` namespace grows further). |
| v0.9.0 capability spec REQ-51 | `prompt_renders.jsonl` sink (separate from `drift_events.jsonl`) | v1.1 | Independent of drift events; the prompt-render audit trail is its own REQ. |
| v0.9.0 capability spec REQ-52 | `flow prompt-events` observability counters (analog to `flow metrics --domain=drift`) | v1.1 | Pair with REQ-51. |
| v0.9.0 capability spec REQ-53 | `docs/prompts.md` auto-generated from prompt registry | v1.1 | Pair with REQ-51/52. |
| Cross-project federation for drift events | `flow drift-events --project=<key>` filter | v1.1 (`federated-drift-events`) | Requires modifying every record helper signature to inject a `project` field. |
| OpenTelemetry OTLP push for drift events | n/a | deferred | Prometheus textfile from REQ-38 already covers the v1 use case. |

---

## Data Flow

The data flow changes ONLY in 2 places:

1. **Write-side** (D1 + D2): `daemon._append_drift_events` writes
   `DriftEvent(decision_id=finding.decision_id)` directly (no `str()`
   coercion). The JSONL wire format is `{"decision_id": 42, ...}` (int)
   instead of `{"decision_id": "42", ...}` (str).

2. **Read-side** (D2 + D3): `flow drift-events {list,tail,stats}`
   reads the JSONL via `DriftEventLog.read_all()`, which defensively
   coerces legacy `str` lines to `int` with a one-time stderr WARN
   per log-path. New-format lines pass through unchanged.

```
   finding.decision_id (int, post-v0.9.0)
            │
            ▼
   ┌─────────────────────────┐
   │ daemon._append_drift_   │
   │ events (D1: no str()    │
   │ coercion)               │
   └─────────┬───────────────┘
             │ append(DriftEvent(decision_id=int))
             ▼
   ┌─────────────────────────┐         ┌──────────────────────────┐
   │ DriftEventLog.append()  │ ──────► │ drift_events.jsonl       │
   │ (unchanged signature)   │  write  │ {"decision_id": 42, ...} │
   └─────────────────────────┘         └──────────┬───────────────┘
                                                  │ read_all() (D2)
                                                  │  ├─ new int line → coerce none
                                                  │  └─ legacy str line → coerce + WARN (1x)
                                                  ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  flow drift-events {list,tail,stats}  (D3 NEW)                  │
   │                                                                  │
   │  list   → reads all + filters + renders (text/json/prom/csv)     │
   │  tail   → reads all + filters + last N + renders (text/json)     │
   │  stats  → reads all + filters + counts + renders (text/json)     │
   └──────────────────────────────────────────────────────────────────┘
```

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/flow_engineering/drift_event_log.py` | MODIFY | D1: `decision_id: str` → `int` at line 46 (~1 LOC). D2: `_legacy_warn_emitted` per-instance flag in `__init__()` + defensive str→int coercion + stderr WARN in `read_all()` at lines 95-119 (~10 LOC). Net ~10 prod LOC delta. |
| `src/flow_engineering/daemon.py` | MODIFY | D1: remove `str(finding.decision_id)` coercion at line 60 (~1 LOC). Update docstring at lines 46-51 to drop the "Future v1 follow-up may flip..." note (~3 LOC). Net ~3 prod LOC delta. |
| `src/flow_engineering/cli.py` | MODIFY (NEW Click group) | D3 + D4: NEW `@main.group(name="drift-events")` + `drift_events_group()` + 3 subcommands (`list` / `tail` / `stats`) with 7/4/4 flag set + 4/2/2 format handlers + 3 D9 exit-code handlers. Insert at `cli.py:~1712+` (parallel to existing `drift` command at `cli.py:1712-1809`). Net ~80 prod LOC added. |
| `src/flow_engineering/decision_drift.py` | MODIFY | D5: add `# type: ignore[arg-type]` to 12 mypy residual sites at lines 127/161/203/252/253/262/278/372/375/310/411/439 (1 comment per site; optional WHY comment). Net +12 prod LOC. |
| `tests/unit/test_drift_event_log.py` | MODIFY | REQ-V1.0.1: 1 str-input fixture migrated to int + 2 NEW tests for the legacy coercion guard + 1 NEW test for the one-time WARN cadence. Net ~20 test LOC delta. |
| `tests/unit/test_cli_drift_events_list.py` | NEW | REQ-V1.0.2: ~15 unit tests for filter + format + exit-code paths. Net ~80 test LOC added. |
| `tests/unit/test_cli_drift_events_tail.py` | NEW | REQ-V1.0.3: ~10 unit tests for tail + filter + format. Net ~50 test LOC added. |
| `tests/unit/test_cli_drift_events_stats.py` | NEW | REQ-V1.0.3: ~10 unit tests for stats + filter + format. Net ~50 test LOC added. |
| `tests/bdd/req_v100_drift_events_list.feature` | NEW | REQ-V1.0.2: 4 BDD scenarios in business-domain Given/When/Then phrasing (text default, `--format=json`, `--format=prometheus`, filters compose). Net ~30 LOC. |
| `tests/bdd/test_req_v100_drift_events_list_steps.py` | NEW | REQ-V1.0.2: step glue. Net ~30 LOC. |
| `tests/bdd/req_v100_drift_events_tail_stats.feature` | NEW | REQ-V1.0.3: 4 BDD scenarios (2 tail + 2 stats). Net ~30 LOC. |
| `tests/bdd/test_req_v100_drift_events_tail_stats_steps.py` | NEW | REQ-V1.0.3: step glue. Net ~30 LOC. |
| `openspec/specs/decision-drift/spec.md` | MODIFY | REQ-V1.0.1: add `## Drift event log JSONL schema` section documenting the v1.0 wire format `{change, decision_id: int, binding_id, class, detected_at}` (key order stable from v0.8.0; `decision_id` type changes from `str` → `int`). REQ-V1.0.2: add `## Drift events read-side CLI` section documenting `flow drift-events {list,tail,stats}`. REQ-V1.0.4: add v1.0 capability entry to Versioning table at lines 408+. Net ~30 docs LOC. |
| `CHANGELOG.md` | MODIFY | REQ-V1.0.4: v1.0 entry under `## [1.0.0] - 2026-06-XX` with `### Changed` (BREAKING JSONL wire format + Path B rationale) + `### Added` (`flow drift-events {list,tail,stats}` + `DriftEventLog.read_all()` defensive coercion) + `### Migration` (1-line `sed`). Net ~30 docs LOC added. |
| `pyproject.toml` | MODIFY | REQ-V1.0.4: `version = "1.0.0"` (line 3). Net +1/-1 LOC. |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` (6 files) | MODIFY | REQ-V1.0.4: update the v0.9.0 API note to v1.0; add the `flow drift-events` CLI surface; mark JSONL wire format as int. Net ~30 docs LOC delta across 6 files. |

**Total scope**: ~100 prod LOC + ~250 test LOC + ~90 docs LOC = ~440 total (CHANGELOG + spec + SKILL.md adds the docs delta; the 350 prod+test count from the proposal is the LOC delta for the 4 code sub-batches alone).

---

## Interfaces / Contracts

### Modified public API

```python
# src/flow_engineering/drift_event_log.py — MODIFIED in v1.0
@dataclass(frozen=True)
class DriftEvent:
    change: str
    decision_id: int                                  # CHANGED — was str (D1)
    binding_id: str
    event_class: str
    detected_at: float
    def to_json_dict(self) -> dict[str, Any]: ...     # emits int decision_id (D1)


class DriftEventLog:
    def __init__(self, path: Path | None = None) -> None:
        # NEW: per-instance flag for one-time stderr WARN cadence (D2)
        self._legacy_warn_emitted: bool = False
        ...

    def append(self, event: DriftEvent) -> None: ...  # unchanged signature
    def read_all(self) -> list[DriftEvent]:
        # MODIFIED: defensive str→int coercion with one-time WARN (D2)
        ...


# src/flow_engineering/daemon.py — MODIFIED in v1.0
def _append_drift_events(report: DriftReport, *, path: Path | None = None) -> None:
    # REMOVED: str(finding.decision_id) coercion at line 60 (D1)
    # finding.decision_id is int; DriftEvent.decision_id is int; direct assignment
    ...


# src/flow_engineering/cli.py — NEW in v1.0
@main.group(name="drift-events")
def drift_events_group() -> None:
    """Read drift events from ~/.flow-engineering/drift_events.jsonl (REQ-V1.0.2 + REQ-V1.0.3)."""


@drift_events_group.command(name="list")
def drift_events_list(
    since: str | None,
    until: str | None,
    change: str | None,
    event_class: str | None,
    limit: int | None,
    fmt: str,  # text|json|prometheus|csv
    log_path: Path | None,
) -> None:
    """List drift events with optional filters (REQ-V1.0.2)."""


@drift_events_group.command(name="tail")
def drift_events_tail(
    limit: int,  # default 10
    change: str | None,
    event_class: str | None,
    fmt: str,  # text|json
) -> None:
    """Show the last N drift events newest-first (REQ-V1.0.3)."""


@drift_events_group.command(name="stats")
def drift_events_stats(
    change: str | None,
    since: str | None,
    until: str | None,
    fmt: str,  # text|json
) -> None:
    """Per-event-class + per-change + per-decision-id counts (REQ-V1.0.3)."""
```

### Breaking-change policy (REQ-V1.0.1 only)

The JSONL wire-format `decision_id: int` flip is a public contract
change for any consumer parsing `~/.flow-engineering/drift_events.jsonl`
(jq scripts, dashboards, custom analytics). Mitigation:

- **D2 defensive read guard** in `DriftEventLog.read_all()` — old
  `str` lines coerce to `int` with a one-time stderr WARN per
  process per log-path. **Zero data loss**; pre-v1.0 JSONL files
  continue to be readable without migration.
- **1-line `sed` migration in CHANGELOG v1.0** (OQ-3).

The Python `decision_drift.Finding.decision_id: int` contract is
**unchanged** from v0.9.0 (the v0.9.0 `Finding.__post_init__` already
enforces int via `TypeError`). The wire-format change is **internal
to `DriftEvent` serialization** — it does NOT affect the
`flow drift <change>` CLI output, the `flow drift --json` envelope,
or the Engram metadata write-back path.

### Non-breaking guarantees

- `flow drift <change>` exit-code semantics unchanged (0 still-valid /
  1 stale / 2 unable_to_verify / 3 usage error per REQ-11).
- `flow drift <change> --json` envelope byte-identical (the
  `decision_id` in the JSON output is the `Finding.decision_id: int`
  from the in-memory dataclass, which has been int since v0.9.0).
- `flow watch --drift` daemon JSONL append behavior preserved (still
  writes 1 line per non-STILL_VALID finding; just with int
  `decision_id` now).
- `DriftEventLog.read_all()` returns identical `DriftEvent` objects
  for new-format JSONL; old-format JSONL returns identical
  `DriftEvent` objects after the defensive coercion (with the WARN).
- All existing 1233 tests pass — verified locally before PR open.
- `_legacy_warn_emitted` flag is per-instance (per-log-path), so
  multiple invocations on different log files each get their own
  WARN (correct cadence for multi-log CLI invocation).

---

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| **Unit — `test_drift_event_log.py`** | D1 int-flip + D2 defensive coercion + one-time WARN cadence | 1 NEW test for int-flip happy path (`DriftEvent(decision_id=42, ...)` constructs); 1 NEW test for legacy `str` coercion (`DriftEvent(decision_id="42", ...)` raises TypeError at construction; legacy JSONL line reads back as int); 1 NEW test for one-time WARN cadence (2 legacy lines → 1 WARN, not 2). Migrate 1 existing fixture from str → int. |
| **Unit — `test_cli_drift_events_list.py`** (NEW) | D3 + D4 `list` subcommand | ~15 unit tests for: default text table render; `--format=json` envelope; `--format=prometheus` textfile output; `--format=csv` csv output; `--since` filter; `--until` filter; `--change` filter; `--event-class` filter; `--limit` cap; filter composition; missing log file → empty result; malformed JSONL → exit 3; unknown `--format` → exit 2; `--path` alternative log; help screen. |
| **Unit — `test_cli_drift_events_tail.py`** (NEW) | D3 + D4 `tail` subcommand | ~10 unit tests for: default `--limit=10`; `--limit=N` override; `--change` filter; `--event-class` filter; text + json formats; empty log → "no events"; newest-first order; malformed JSONL → exit 3. |
| **Unit — `test_cli_drift_events_stats.py`** (NEW) | D3 + D4 `stats` subcommand | ~10 unit tests for: per-event-class counts; per-change counts; per-decision-id top-N; `--change` filter; `--since`/`--until` filters; text + json formats; empty log → all-zero table; help screen. |
| **BDD — `req_v100_drift_events_list.feature`** (NEW) | D3 + D4 `list` subcommand in business-domain phrasing | 4 scenarios: (1) operator reads drift events with default text; (2) operator exports drift events as JSON for downstream tooling; (3) operator exports drift events as Prometheus textfile for scraping; (4) operator filters drift events by change + event-class + time range. |
| **BDD — `req_v100_drift_events_tail_stats.feature`** (NEW) | D3 + D4 `tail` + `stats` subcommands | 4 scenarios: (1) operator monitors recent drift events with `tail`; (2) operator tail-filters by change name; (3) operator summarizes drift counts per change; (4) operator summarizes drift counts per event-class. |
| **Existing — `test_cli_drift.py`** | NON-REGRESSION on `flow drift <change>` | All 25 existing tests stay green (D3 Path B is parallel-namespace; `drift` command unchanged). |
| **Existing — `test_daemon_drift_events.py`** | NON-REGRESSION on daemon JSONL append | All existing tests stay green (D1 only removes 1 `str()` coercion; the append loop is otherwise unchanged). |
| **Mypy — `decision_drift.py`** | D5 type-ignore cleanup | `uv run mypy src/flow_engineering/decision_drift.py` shows ≤5 errors (down from 12 baseline; 12-site `# type: ignore[arg-type]` cleanup at REQ-V1.0.4). |
| **Ruff — changed files** | NON-REGRESSION on lint | `uv run ruff check src/flow_engineering/{drift_event_log.py,daemon.py,cli.py,decision_drift.py}` shows ≤5 errors (project convention is non-blocking; v0.9.0 baseline was 12 errors in `decision_drift.py`). |

---

## Migration / Rollout

No data migration required for end users:

- **D1 wire-format flip** is mitigated by **D2 defensive read guard**
  — pre-v1.0 JSONL files remain readable without migration.
- **D2 one-time stderr WARN** surfaces the issue to operators on
  first read so they know to run the CHANGELOG v1.0 `sed` migration.
- **D3 Path B parallel namespace** is NON-BREAKING — `flow drift <change>`
  callers (CI pipelines, hooks, docs) work unchanged.
- **D5 `# type: ignore` comments** are doc-only — zero runtime impact.

If the v1.0 release needs to be reverted (single PR rollback):
`git revert <PR-merge>` restores the pre-v1.0 state (D1 + D2 revert
to v0.9.0; D3 NEW Click group is removed; D5 mypy residuals resurface
at the v0.9.0 baseline; CHANGELOG + pyproject revert cleanly).

---

## Wall time estimate

**~2 hours end-to-end** (single PR, 4 sub-batches of strict per-task TDD):

| Sub-batch | Time | Tasks | Commits |
|---|---|---|---|
| Sub-batch 1 (S1, D1 + D2) | ~25 min | 6 tasks (V1.0.1.1..V1.0.1.6) | 3 commits |
| Sub-batch 2 (S2a, D3 list + D4) | ~30 min | 4 tasks (V1.0.2.1..V1.0.2.4) | 3 commits |
| Sub-batch 3 (S2b, D3 tail+stats + D4) | ~30 min | 5 tasks (V1.0.3.1..V1.0.3.5) | 3 commits |
| Sub-batch 4 (Tech-debt + docs, D5 + CHANGELOG) | ~20 min | 6 tasks (V1.0.4.1..V1.0.4.6) | 3 commits |
| Verify + archive | ~15 min | `sdd-verify` + `sdd-archive` | 1 merge commit |
| **TOTAL** | **~2 hours** | **21 tasks** | **~13 commits** |

**Per-task breakdown**:
- Sub-batch 1: ~4 min/task × 6 tasks = ~24 min
- Sub-batch 2: ~7.5 min/task × 4 tasks = ~30 min
- Sub-batch 3: ~6 min/task × 5 tasks = ~30 min
- Sub-batch 4: ~3.5 min/task × 6 tasks = ~21 min
- Verify: 1 `pytest` run + 1 `ruff` run + 1 `mypy` run + 1 `sdd-verify` pass + 1 `sdd-archive` pass = ~15 min

---

## code_refs

The following code references enumerate every file to be modified in
v1.0 with line numbers and confidence scores. The block is gated by
the `<!-- code_refs -->` marker so `flow inspect <change>` can render
the binding surface for this design.

<!-- code_refs -->
```json
{
  "source": "manual",
  "refs": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_drift_event_log_drift_event_decision_id",
      "label": "DriftEvent dataclass — MODIFY D1: decision_id: str → int at drift_event_log.py:46 (REQ-V1.0.1 wire-format flip)",
      "file": "src/flow_engineering/drift_event_log.py",
      "line": 46,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_drift_event_log_read_all_defensive_coercion",
      "label": "DriftEventLog.read_all() — MODIFY D2: defensive str→int coercion + one-time stderr WARN per log-path at drift_event_log.py:95-119 (REQ-V1.0.1 read-side compat shim)",
      "file": "src/flow_engineering/drift_event_log.py",
      "line": 95,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_drift_event_log_init_legacy_warn_flag",
      "label": "DriftEventLog.__init__() — MODIFY D2: add _legacy_warn_emitted per-instance flag at drift_event_log.py:72-79 (REQ-V1.0.1 one-time WARN cadence)",
      "file": "src/flow_engineering/drift_event_log.py",
      "line": 72,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_daemon_append_drift_events_coercion_removal",
      "label": "daemon._append_drift_events() — MODIFY D1: REMOVE str(finding.decision_id) coercion at daemon.py:60; finding is int post-v0.9.0 (REQ-V1.0.1)",
      "file": "src/flow_engineering/daemon.py",
      "line": 60,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_daemon_append_drift_events_docstring_update",
      "label": "daemon._append_drift_events() — MODIFY D1: update docstring at daemon.py:46-51 to drop 'Future v1 follow-up may flip...' note (now done in v1.0)",
      "file": "src/flow_engineering/daemon.py",
      "line": 46,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_drift_events_group",
      "label": "cli.py — NEW D3: @main.group(name='drift-events') def drift_events_group() (Path B parallel command; NON-BREAKING for flow drift <change> callers) at cli.py:~1712+ (REQ-V1.0.2 + REQ-V1.0.3)",
      "file": "src/flow_engineering/cli.py",
      "line": 1712,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_drift_events_list_subcommand",
      "label": "cli.py — NEW D3 + D4: drift_events_list subcommand with --since/--until/--change/--event-class/--limit/--format=text|json|prometheus|csv/--path flags at cli.py:~1740+ (REQ-V1.0.2)",
      "file": "src/flow_engineering/cli.py",
      "line": 1740,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_drift_events_tail_subcommand",
      "label": "cli.py — NEW D3 + D4: drift_events_tail subcommand with --limit=10/--change/--event-class/--format flags at cli.py:~1790+ (REQ-V1.0.3)",
      "file": "src/flow_engineering/cli.py",
      "line": 1790,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_drift_events_stats_subcommand",
      "label": "cli.py — NEW D3 + D4: drift_events_stats subcommand with --change/--since/--until/--format flags at cli.py:~1820+ (REQ-V1.0.3)",
      "file": "src/flow_engineering/cli.py",
      "line": 1820,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_127",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 127 (classify_binding 2-arg signature test site; intentional v0.9.0 W1 enforcement)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 127,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_161",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 161 (_classify_with_id_map 3-arg legacy helper test site)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 161,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_203",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 203 (load_graph 3-tuple return type with dict | None)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 203,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_252",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 252 (_index_graph_payload nodes: list generic)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 252,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_253",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 253 (_index_graph_payload return tuple[dict | None, ...])",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 253,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_262",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 262 (current_nodes: dict[str, dict] = {} untyped dict)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 262,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_278",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 278 (_load_graph_from_snapshot return tuple[dict | None, ...])",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 278,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_372",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 372 (_DummyBackend.iter_observations # pragma: no cover unreachable)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 372,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_375",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 375 (_DummyBackend.mem_search # pragma: no cover unreachable)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 375,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_310",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 310 (SnapshotManager + _DummyBackend in _load_graph_from_snapshot)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 310,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_411",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 411 (SnapshotManager + _DummyBackend in _snapshot_has_graph)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 411,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_mypy_residual_439",
      "label": "decision_drift.py — MODIFY D5: add # type: ignore[arg-type] at line 439 (SnapshotManager + _DummyBackend in _frozen_backend_from_snapshot)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 439,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_drift_event_log_modify",
      "label": "tests/unit/test_drift_event_log.py — MODIFY D1 + D2: 1 str→int fixture migration + 2 NEW legacy coercion tests + 1 NEW one-time WARN cadence test (REQ-V1.0.1; ~20 test LOC delta)",
      "file": "tests/unit/test_drift_event_log.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_cli_drift_events_list_new",
      "label": "tests/unit/test_cli_drift_events_list.py — NEW D3 + D4: ~15 unit tests for list subcommand filters + formats + exit codes (REQ-V1.0.2; ~80 test LOC)",
      "file": "tests/unit/test_cli_drift_events_list.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_cli_drift_events_tail_new",
      "label": "tests/unit/test_cli_drift_events_tail.py — NEW D3 + D4: ~10 unit tests for tail subcommand (REQ-V1.0.3; ~50 test LOC)",
      "file": "tests/unit/test_cli_drift_events_tail.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_cli_drift_events_stats_new",
      "label": "tests/unit/test_cli_drift_events_stats.py — NEW D3 + D4: ~10 unit tests for stats subcommand (REQ-V1.0.3; ~50 test LOC)",
      "file": "tests/unit/test_cli_drift_events_stats.py",
      "line": 1,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req_v100_drift_events_list_feature_new",
      "label": "tests/bdd/req_v100_drift_events_list.feature — NEW D3 + D4: 4 BDD scenarios for list subcommand (REQ-V1.0.2; ~30 LOC)",
      "file": "tests/bdd/req_v100_drift_events_list.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_req_v100_drift_events_list_steps_new",
      "label": "tests/bdd/test_req_v100_drift_events_list_steps.py — NEW: step glue for list feature (REQ-V1.0.2; ~30 LOC)",
      "file": "tests/bdd/test_req_v100_drift_events_list_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req_v100_drift_events_tail_stats_feature_new",
      "label": "tests/bdd/req_v100_drift_events_tail_stats.feature — NEW D3 + D4: 4 BDD scenarios for tail + stats (REQ-V1.0.3; ~30 LOC)",
      "file": "tests/bdd/req_v100_drift_events_tail_stats.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_test_req_v100_drift_events_tail_stats_steps_new",
      "label": "tests/bdd/test_req_v100_drift_events_tail_stats_steps.py — NEW: step glue for tail+stats feature (REQ-V1.0.3; ~30 LOC)",
      "file": "tests/bdd/test_req_v100_drift_events_tail_stats_steps.py",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_specs_decision_drift_spec_modify",
      "label": "openspec/specs/decision-drift/spec.md — MODIFY: add ## Drift event log JSONL schema section (REQ-V1.0.1 v1.0 wire format {change, decision_id: int, binding_id, class, detected_at}) + ## Drift events read-side CLI section (REQ-V1.0.2 + REQ-V1.0.3) + v1.0 capability entry to Versioning table at lines 408+ (REQ-V1.0.4; ~30 docs LOC)",
      "file": "openspec/specs/decision-drift/spec.md",
      "line": 408,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "changelog_v100_entry",
      "label": "CHANGELOG.md — MODIFY: v1.0 entry under ## [1.0.0] - 2026-06-XX with ### Changed (BREAKING JSONL wire format + Path B rationale) + ### Added (flow drift-events {list,tail,stats} + DriftEventLog.read_all() defensive coercion) + ### Migration (1-line sed) (REQ-V1.0.4; ~30 docs LOC)",
      "file": "CHANGELOG.md",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "pyproject_toml_version_bump",
      "label": "pyproject.toml — MODIFY: version = '1.0.0' at line 3 (REQ-V1.0.4)",
      "file": "pyproject.toml",
      "line": 3,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_propose_skill_md",
      "label": "~/.config/opencode/skills/sdd-propose/SKILL.md — MODIFY: update v0.9.0 API note to v1.0; add flow drift-events CLI surface; mark JSONL wire format as int (REQ-V1.0.4)",
      "file": "~/.config/opencode/skills/sdd-propose/SKILL.md",
      "line": 1,
      "confidence": 0.7,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_design_skill_md",
      "label": "~/.config/opencode/skills/sdd-design/SKILL.md — MODIFY: update v0.9.0 API note to v1.0 (REQ-V1.0.4)",
      "file": "~/.config/opencode/skills/sdd-design/SKILL.md",
      "line": 1,
      "confidence": 0.7,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_tasks_skill_md",
      "label": "~/.config/opencode/skills/sdd-tasks/SKILL.md — MODIFY: update v0.9.0 API note to v1.0 (REQ-V1.0.4)",
      "file": "~/.config/opencode/skills/sdd-tasks/SKILL.md",
      "line": 1,
      "confidence": 0.7,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_apply_skill_md",
      "label": "~/.config/opencode/skills/sdd-apply/SKILL.md — MODIFY: update v0.9.0 API note to v1.0 (REQ-V1.0.4)",
      "file": "~/.config/opencode/skills/sdd-apply/SKILL.md",
      "line": 1,
      "confidence": 0.7,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_verify_skill_md",
      "label": "~/.config/opencode/skills/sdd-verify/SKILL.md — MODIFY: update v0.9.0 API note to v1.0 (REQ-V1.0.4)",
      "file": "~/.config/opencode/skills/sdd-verify/SKILL.md",
      "line": 1,
      "confidence": 0.7,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "opencode_skills_sdd_archive_skill_md",
      "label": "~/.config/opencode/skills/sdd-archive/SKILL.md — MODIFY: update v0.9.0 API note to v1.0 (REQ-V1.0.4)",
      "file": "~/.config/opencode/skills/sdd-archive/SKILL.md",
      "line": 1,
      "confidence": 0.7,
      "source": "manual"
    }
  ]
}
```

---

## Result contract

```yaml
status: success
verdict: PASS
executive_summary: >
  v1.0-followups design closes the 2 deferred SUGGESTION findings (S1
  wire-format flip + S2 read-side CLI) from drift-hardening + the 12
  mypy residuals from v0.9.0 in 4 REQs (REQ-V1.0.1..V1.0.4) with 5
  architecture decisions (D1..D5). D1 flips DriftEvent.decision_id to
  int; D2 adds defensive read_all() coercion with one-time stderr
  WARN; D3 ships flow drift-events {list,tail,stats} Click group
  (Path B parallel command; NON-BREAKING for flow drift <change>);
  D4 locks the 4-format output surface (text/json/prometheus/csv);
  D5 resolves 12 mypy residuals via # type: ignore[arg-type]. All 6
  open questions from proposal pre-resolved by orchestrator. Doc drift
  fixed: design uses real symbol name DriftEventLog.read_all() (NOT
  iter_drift_events() as the stale verify-report says). ~2h wall time;
  single PR; ~100 prod LOC + ~250 test LOC = ~350 total (well under
  400 LOC chained-PR threshold); 13 work-unit commits.
open_questions_count: 0  # All 6 OQs resolved per orchestrator pre-decisions
decision_count: 5  # D1..D5
artifacts:
  file_path: C:\dev\proyects\flow-engineering\openspec\changes\v1.0-followups\design.md
  engram_sync_id: <assigned on mem_save>
next_recommended: sdd-tasks v1.0-followups
risks: []  # 0 blockers; 5 LOW risks documented in Risks section
skill_resolution: paths-injected
```