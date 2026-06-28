<!-- proposal.md: change #8 drift-hardening. Source: sdd-propose sub-agent. -->
# Proposal: drift-hardening

```yaml
status: success
confidence: high
open_questions_count: 10
chained_pr_recommendation: no
wall_time_estimate: ~5-5.5h end-to-end (single PR, 4 apply batches)
forecast_loc: 225 production + 1600 tests + 28 spec/design = 1853 grand-total
pr_split: single PR (cluster change via 4 batches: A=dataclass+spec/design, B=JSONL+S2, C=BDD coverage, D=CHANGELOG+meta)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\drift-hardening\proposal.md
next_recommended: sdd-spec drift-hardening
```

## Intent

`flow-engineering` carries **8 open WARNING/SUGGESTION items** from changes
#2 (`decision-reality-drift`) and #5 (`graph-snapshots`) that landed
v0.5.0/v0.6.0: W4/W5/W6/W8/S2 from #2 plus W23/W25/W26 from #5.
**7 other items (W7/S1/W20/W21/W22/W24/W27) are already RESOLVED** in
HEAD `9f03bcc` — `flow-engineering` did NOT regress; the cluster is just
debt closure. The 8 open items break down into two categories: (a)
**spec/design vs impl drift** — archived `design.md:134-155` declares
`Finding.decision_id: int` and `DriftReport.scanned_at: str`, but
`decision_drift.py:60-87` ships `str` / `float`; `SnapshotMeta.size_bytes`
(impl) vs `file_size_bytes` (design); `PruneResult.freed_bytes` (impl)
vs `freed_bytes_estimate` (spec/design); and (b) **missing implementation
+ missing BDD coverage** — spec REQ-15 demands a JSONL event log at
`~/.flow-engineering/drift_events.jsonl`, but `daemon.py:75-97` only
emits a stdout summary line via the `on_summary` callback (W5); the
still-valid silence rule (W6) is not honored; the spec promises 39 BDD
scenarios across 9 feature files for REQ-9..16 but `tests/bdd/` only
ships 18 across 3 (W4); the W23 dual-name `snapshot_pruned_total` ↔
`snapshot_prune_total` counter history in `~/.flow-engineering/metrics.jsonl`
lacks an explicit deprecation note; and the silent skip on non-int
`decision_id` in `cli.py:_write_back_findings` (S2) needs a stderr
WARN. The 8 items map cleanly to **5 REQs (REQ-55..59)** bundled into
**one PR** with 4 sequential apply batches. The headline deliverable
is the **21 new BDD scenarios across 6 feature files** (REQ-57 / W4)
which closes the spec-vs-test gap that has been open since v0.3.0.
A **secondary deliverable is the v0.7.0 → v0.8.0 version bump**
mandated by the W8 dataclass shape migration (REQ-56) which IS a
public-API break — the `DecisionDrift` dataclasses are imported
across the daemon/CLI seams. Coordination: change #7
(`prompt-registry`) MUST archive before this change starts, to preserve
the REQ-55 numbering (REQ-45..54 are reserved for prompt-registry).

## Context (from explore)

Explored in [`explore.md`](./explore.md) and Engram #222. The exploration
evaluated 15 documented carry-forwards (8 OPEN + 7 RESOLVED) from
archived changes #2 and #5; categorized each by complexity (TRIVIAL=3,
SMALL=2, MEDIUM=1, LARGE=1 = 7 items); and concluded that **the 8
OPEN items are thematically unified** (spec/design reconciliation +
small-impl additions + BDD scaffolding) and architecturally shallow
(no new modules except `drift_event_log.py`; no schema migration; no
runtime dependencies). The strict-TDD ×6 LOC multiplier (established
in `decision-code-linking` archive-report #119 S3) forecasts the work
at ~1 853 LOC forecast → ~9 700 realistic, which is BELOW the
~10 910 threshold that triggered observability's chained-PR split —
**a single PR is justified**.

### Carry-forwards resolved by this change

| Source | Item | Resolution |
|---|---|---|
| `decision-reality-drift` verify-report #135 | W4 — 21 missing BDD scenarios for REQ-10/12/13/14/16 | REQ-57 — 6 new `.feature` files + step glue |
| `decision-reality-drift` verify-report #135 | W5 — missing JSONL event log at `~/.flow-engineering/drift_events.jsonl` | REQ-55 — NEW `drift_event_log.py` module + `record_drift_event()` helper |
| `decision-reality-drift` verify-report #135 | W6 — missing still-valid silence rule | REQ-55 — silence outer summary when `total == 0 and not graph_unavailable` |
| `decision-reality-drift` verify-report #135 | W8 — dataclass shape mismatch (decision_id str↔int, scanned_at float↔str, graph_unavailable ↔ unable_to_verify+unable_reason, classify_binding 3↔2 args) | REQ-56 — hard migration with `@property` alias for `graph_unavailable` (1-release deprecation) |
| `decision-reality-drift` verify-report #135 | S2 — silent skip on non-int `decision_id` in `_write_back_findings` | REQ-59 — stderr WARN once per batch when `skipped_total > 0` |
| `graph-snapshots` verify-report #188 | W23 — dual-name `snapshot_pruned_total` ↔ `snapshot_prune_total` coexistence | REQ-59 — CHANGELOG v0.6.0 Notes section documents coexistence + REQ-37 `--domain snapshot` filter guidance |
| `graph-snapshots` verify-report #188 | W25 — `SnapshotMeta.size_bytes` (impl) vs `file_size_bytes` (design) | REQ-58 — design.md rename + document `pinned: bool` retention-pin field |
| `graph-snapshots` verify-report #188 | W26 — `PruneResult.freed_bytes` (impl) vs `freed_bytes_estimate` (spec/design) | REQ-58 — spec.md + design.md field-name reconciliation |

### Carry-forwards explicitly NOT touched by this change (already RESOLVED, verified closed)

| Source | Item | Resolution evidence |
|---|---|---|
| `decision-reality-drift` #135 | W7 — `drift_scan_total` counter rename | commit `e8ac1d5` PR #6 squash — `CHANGELOG.md:116` lists `drift_invoked_total` |
| `decision-reality-drift` #135 | S1 — "63 BDD scenarios across 12 feature files" phrasing | commit `e8ac1d5` — `CHANGELOG.md:124` updated |
| `graph-snapshots` #188 | W20 — counter-name catalog reconciliation | commit `a0c1419` |
| `graph-snapshots` #188 | W21 — `pyproject.toml` 0.4.0→0.6.0 bump | commits `d6525a0` + `fb3bd03` |
| `graph-snapshots` #188 | W22 — `--json` flag for `flow snapshot list` / `flow snapshot diff` | commit `5ef8f0e` |
| `graph-snapshots` #188 | W24 — 47 acceptance criteria boxes flipped | commit `b7869b2` |
| `graph-snapshots` #188 | W27 — apply-progress regeneration | archive phase — Engram #187 |

## Approach (proposed)

### Approach matrix

| Approach | LOC forecast | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — Single PR with 4 apply batches** (REQ-56+58 → REQ-55+59 → REQ-57 → CHANGELOG/meta) | ~1 853 | Bundles breaking W8 dataclass migration with related cleanup; single review effort; clear "drift-hardening v0.8.0" identity; single sdd-verify pass; no REQ-numbering collision with prompt-registry change #7 | One PR absorbs ~9 700 realistic LOC; reviewers see the whole picture at once | **RECOMMENDED** |
| B — Per-W micro-changes (5 separate tiny changes) | ~1 853 spread across 5 | Smallest possible review unit (≤400 LOC each) | 5 PRs of small churn; high overhead (CI ×5, review ×5, archive ×5); W8 migration isolated from W4 BDD coverage that exercises it — needless friction | Rejected |
| C — Defer W4/W8 to v1.1; ship only W25/W26/S2 + W23 deprecation note now | ~150 (just trivial + W23 doc) | Smallest PR; fastest to merge | Leaves the 2 BIGGEST warnings open (21 BDD scenarios + dataclass migration); future v1.1 release inherits debt + bumps version twice; compounds spec-vs-impl drift | Rejected |

**Recommendation: Approach A.** The cluster is small enough (1 853
forecast → ~9 700 realistic, below the observability 10 910 chained-PR
threshold); thematically unified (8 carry-forwards from 2 source
changes); and bundling the W8 breaking dataclass migration (REQ-56)
with the v0.8.0 version bump (CHANGELOG batch D) means **one
version-bump event, one migration guide, one PR review**. Approach B's
micro-PR pattern would force the W4 BDD coverage PR (REQ-57) to re-read
the W8 dataclass shape from the W8 PR (REQ-56) — needless friction.
Approach C would defer the headline value-add (21 new BDD scenarios
that v0.3.0 has been promising since ship).

### Architecture (Approach A)

Five cooperating pieces, all on top of existing drift + snapshot
infrastructure that changes #2 and #5 shipped:

1. **`drift_event_log` module** (NEW in `src/flow_engineering/`)
   — append-only JSONL writer at `~/.flow-engineering/drift_events.jsonl`
   with rotation when file > 10 MB (mirrors `metrics.jsonl` policy).
   Powers REQ-55 (W5 JSONL persistence + W6 still-valid silence).
2. **`record_drift_event()` helper** (NEW in `observability.py`) —
   mirrors the 5 existing `record_*_summary` helpers (REQ-8/12/22/26
   precedent); emits a new `drift_event_log_total` counter + a
   `drift_event_log_bytes` gauge to track sink health.
3. **`DecisionDrift` dataclass shape sync** (MODIFY in
   `decision_drift.py`) — `Finding.decision_id: int` (was `str`),
   `DriftReport.scanned_at: str` (ISO 8601 UTC, was `float`),
   `DriftReport.unable_to_verify: bool` + `unable_reason: str | None`
   (renamed from `graph_unavailable`); `classify_binding(ref, graph_nodes)`
   (2 args, was 3). `@property graph_unavailable` retained for 1
   release as a `DeprecationWarning`-emitting alias. Powers REQ-56 (W8).
4. **Snapshot spec/design field reconciliation** (MODIFY in archived
   `design.md` + `spec.md` only) — `SnapshotMeta.size_bytes` (rename
   from `file_size_bytes`) + document `pinned: bool` retention-pin
   field; `PruneResult.freed_bytes` (rename from `freed_bytes_estimate`).
   **0 production code change**. Powers REQ-58 (W25/W26).
5. **BDD coverage completion** (NEW 6 `.feature` files + step glue)
   — `tests/bdd/req10_drift_cli.feature` (9 scenarios),
   `req11_drift_exit.feature` (3), `req12_drift_counters.feature` (3),
   `req13_drift_metadata.feature` (3), `req14_drift_resilience.feature` (4),
   `req16_skill_prose.feature` (2). Strategy: **translate** existing
   unit-test contracts (`test_cli_drift.py`, `test_observability.py`,
   `test_engram_io_code_refs.py`) to Gherkin phrasing — no behavior
   change. Powers REQ-57 (W4).

### CLI surface (REQ-55 proposed)

```bash
# Today (unchanged — REQ-10 close behavior; emits single stdout line):
flow drift scan <change>           # exits 0/1/2/3 per W status
flow drift daemon --drift          # REQ-15 — emits "drift: <change> 0 findings" line via on_summary callback
flow drift write-back              # REQ-15 — silent skip on non-int decision_id (S2)

# New in change #8 (REQ-55):
flow drift daemon --drift-event-log[=<path>]
                                   # NEW: append-only JSONL at ~/.flow-engineering/drift_events.jsonl
                                   # 1 line per drift event: {ts, change, decision_id, binding_id, class, detected_at}
                                   # Default ON; --no-drift-event-log to disable

flow drift events [--since=<iso>] [--change=<name>] [--class=<STILL_VALID|...>]
                                   # NEW: read the JSONL (mirror of flow metrics read-side from observability)
                                   # Filters + flat table default; --json for list-of-dicts
```

Still-valid silence (W6, REQ-55): when `report.total == 0 and not
report.unable_to_verify`, the outer `on_summary` line is **suppressed**
(no `drift: <change> 0 findings (no classes)` spam on every quiet tick).
The JSONL append still happens (audit trail preserved); only the
stdout summary is silent. Still-valid-but-graph-unavailable (i.e.,
`unable_to_verify=True`, `unable_reason="graph_unavailable"`) emits
the summary line with the unable_to_verify reason.

### Code sketch — REQ-55 `drift_event_log.py` (NEW)

```python
# src/flow_engineering/drift_event_log.py (NEW — ~150 LOC)
"""Append-only JSONL sink for drift detection events (REQ-55)."""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterator, TextIO

from flow_engineering.observability import increment
from flow_engineering.paths import user_state_dir

DEFAULT_PATH = user_state_dir() / "drift_events.jsonl"
ROTATE_BYTES = 10 * 1024 * 1024  # 10 MB — mirror metrics.jsonl policy


def _utc_iso(ts: float | None = None) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts or time.time(), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rotate_if_needed(path: Path) -> None:
    if not path.exists() or path.stat().st_size < ROTATE_BYTES:
        return
    stamp = _utc_iso().replace(":", "")
    rotated = path.with_name(f"drift_events.{stamp}.jsonl")
    path.rename(rotated)  # rotate to drift_events.<stamp>.jsonl


def record_drift_event(report, *, path: Path | None = None) -> None:
    """Append one JSON line per non-still-valid finding to drift_events.jsonl.

    Powers REQ-55 (W5); counters: drift_event_log_total + drift_event_log_bytes.
    Idempotent re: file rotation — safe across daemon restarts.
    """
    target = path or DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    _rotate_if_needed(target)

    with target.open("a", encoding="utf-8") as fh:
        for finding in report.findings:
            event = {
                "ts": _utc_iso(),
                "change": report.change,
                "decision_id": finding.decision_id,         # int post REQ-56
                "binding_id": finding.binding_id,
                "class": finding.finding_class.value,       # str enum
                "detected_at": _utc_iso(report.scanned_at_iso),
            }
            fh.write(json.dumps(event, separators=(",", ":")) + "\n")
            increment("drift_event_log_total", domain="drift")

    increment("drift_event_log_bytes", domain="drift", value=target.stat().st_size)


def iter_drift_events(path: Path | None = None,
                      *, since_iso: str | None = None,
                      change: str | None = None) -> Iterator[dict]:
    """Yield parsed events; supports REQ-55 read-side (`flow drift events`)."""
    target = path or DEFAULT_PATH
    if not target.exists():
        return
    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            if since_iso and ev.get("ts", "") < since_iso:
                continue
            if change and ev.get("change") != change:
                continue
            yield ev
```

### Code sketch — REQ-56 dataclass migration

```python
# src/flow_engineering/decision_drift.py (MODIFY — ~60 LOC delta)
# REQ-56 (W8): Finding.decision_id str→int; DriftReport.scanned_at float→str;
# graph_unavailable → unable_to_verify + unable_reason;
# classify_binding(ref, graph_nodes) 3 args→2 args.
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _coerce_int(value: int | str) -> int:
    """Best-effort int coercion for legacy str inputs (REQ-56 1-release compat)."""
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"decision_id must be int or numeric str, got {value!r}")


@dataclass(frozen=True)
class Finding:
    decision_id: int                  # was: str  (REQ-56 W8)
    binding_id: str
    finding_class: FindingClass
    message: str

    def __post_init__(self) -> None:
        # 1-release soft compat: accept numeric strings, emit DeprecationWarning.
        if isinstance(self.decision_id, str):
            warnings.warn(
                "Finding.decision_id: str is deprecated; pass int (REQ-56).",
                DeprecationWarning, stacklevel=2,
            )
            object.__setattr__(self, "decision_id", _coerce_int(self.decision_id))


@dataclass(frozen=True)
class DriftReport:
    change: str
    scanned_at: str                   # was: float  — ISO 8601 UTC (REQ-56 W8)
    unable_to_verify: bool = False    # was: graph_unavailable (REQ-56 W8)
    unable_reason: str | None = None  # NEW field (REQ-56 W8)
    findings: tuple[Finding, ...] = field(default_factory=tuple)

    @property
    def graph_unavailable(self) -> bool:
        """1-release alias for unable_to_verify (REQ-56 backward compat)."""
        warnings.warn(
            "DriftReport.graph_unavailable is deprecated; use unable_to_verify (REQ-56).",
            DeprecationWarning, stacklevel=2,
        )
        return self.unable_to_verify

    @classmethod
    def from_scanned(cls, *, change: str, scanned_at: float | str,
                     unable_to_verify: bool = False,
                     unable_reason: str | None = None,
                     findings: tuple[Finding, ...] = ()) -> "DriftReport":
        # Accept legacy float inputs (epoch seconds) and coerce to ISO.
        if isinstance(scanned_at, float):
            scanned_at = datetime.fromtimestamp(scanned_at, tz=timezone.utc)\
                .strftime("%Y-%m-%dT%H:%M:%SZ")
        return cls(change=change, scanned_at=scanned_at,
                   unable_to_verify=unable_to_verify,
                   unable_reason=unable_reason,
                   findings=findings)


# REQ-56 (W8): classify_binding refactored from 3 args (ref, graph_nodes, current_id_map)
# to 2 args (ref, graph_nodes). current_id_map is now derived inside from graph_nodes.
def classify_binding(ref: BindingRef, graph_nodes: dict[str, GraphNode]) -> FindingClass:
    """Classify a binding as STILL_VALID | STALE | MISSING | ORPHAN | UNABLE_TO_VERIFY.

    REQ-56 (W8): 2-arg signature; current_id_map derived from graph_nodes.
    """
    ...
```

### Dependencies

- **NO new runtime dependencies.** stdlib `json` + `pathlib` + `time` +
  `dataclasses` + `datetime` + `warnings` + `enum` cover everything.
- Reuses `observability.increment()` for counter emission (REQ-8 close
  shipped the catalog; the 2 new counter names just need catalog entries).
- Reuses the `_now_iso()` helper pattern from `cli.py:1632` for ISO 8601
  serialization (REQ-10/11 precedent).
- Reuses the `_rotate_if_needed()` pattern from `observability.py` for
  JSONL rotation (REQ-44 deferred to v1.1 but the rotation helper
  already exists for `metrics.jsonl`).

### What changes (scope)

**In scope (single PR, 4 apply batches)**:

- **Batch A (REQ-56 + REQ-58, dataclass + spec/design reconciliation)**:
  - `src/flow_engineering/decision_drift.py` (MODIFY): dataclass shape
    sync (`Finding.decision_id: int`, `DriftReport.scanned_at: str`,
    `unable_to_verify`/`unable_reason`, `classify_binding(ref, graph_nodes)`
    2-arg); `graph_unavailable` `@property` alias; `from_scanned()` classmethod.
  - `src/flow_engineering/cli.py` (MODIFY): minor type-cast updates for
    the dataclass rename (~10 sites).
  - `tests/unit/test_decision_drift.py` (MODIFY): +30 LOC — dataclass
    shape round-trip + `DeprecationWarning` capture tests.
  - `tests/unit/test_cli_drift.py` (MODIFY): +10 LOC — cast site updates.
  - `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md`
    (MODIFY): reconcile dataclass type signatures at lines 134-155.
  - `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md`
    (MODIFY): align REQ-9..16 scenarios with new shape.
  - `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` (MODIFY):
    `freed_bytes_estimate` → `freed_bytes` at line 230 (W26).
  - `openspec/changes/archive/2026-06-27-graph-snapshots/design.md` (MODIFY):
    `file_size_bytes` → `size_bytes` + `pinned` field doc at line 271 (W25).

- **Batch B (REQ-55 + REQ-59, JSONL event log + counter deprecation + stderr WARN)**:
  - `src/flow_engineering/drift_event_log.py` (NEW, ~150 LOC).
  - `src/flow_engineering/observability.py` (MODIFY): +15 LOC —
    `record_drift_event()` helper + 2 catalog entries
    (`drift_event_log_total`, `drift_event_log_bytes`).
  - `src/flow_engineering/daemon.py` (MODIFY): +30/-10 LOC — wire
    `record_drift_event` into `handle_apply_progress_event`; REQ-55 W6
    still-valid silence rule in outer summary; gate `on_summary` to
    skip the stdout line when `report.total == 0 and not
    report.unable_to_verify`.
  - `src/flow_engineering/cli.py` (MODIFY): +20/-5 LOC — S2 stderr WARN
    in `_write_back_findings` (REQ-59); single batch-summary WARN when
    `skipped_total > 0`, not per-row.
  - `tests/unit/test_drift_event_log.py` (NEW, +180 LOC): rotation,
    append, schema, counter increment, idempotency, read-side iter.
  - `tests/unit/test_daemon_drift_events.py` (MODIFY, +20 LOC): event-log
    integration + W6 still-valid silence.
  - `tests/unit/test_cli_watch_drift.py` (MODIFY, +10 LOC): CLI wiring.
  - `tests/unit/test_cli_drift.py` (MODIFY, +15 LOC): S2 stderr WARN capture.
  - `tests/bdd/req15_drift_daemon.feature` (MODIFY, +80 LOC): 2 new
    scenarios (event-log line present on detected drift + no event-log
    line on still-valid; still-valid-but-graph-unavailable emits
    unable_to_verify line per W6).
  - `CHANGELOG.md` (MODIFY, +20 LOC): v0.6.0 Notes section documenting
    W23 dual-name coexistence + recommendation to use REQ-37
    `--domain snapshot` filter.

- **Batch C (REQ-57, BDD coverage completion — 21 scenarios)**:
  - `tests/bdd/req10_drift_cli.feature` (NEW, +250 LOC): 9 BDD scenarios
    for the CLI surface (`flow drift scan`, `--format`, `--json`,
    `--since`, `--change`, exit codes, write-back).
  - `tests/bdd/req11_drift_exit.feature` (NEW, +90 LOC): 3 BDD scenarios
    for exit-code semantics (0 still-valid, 1 stale, 2 unable_to_verify,
    3 usage error).
  - `tests/bdd/req12_drift_counters.feature` (NEW, +90 LOC): 3 BDD
    scenarios for the 8 drift counters (REQ-12 contract).
  - `tests/bdd/req13_drift_metadata.feature` (NEW, +90 LOC): 3 BDD
    scenarios for `update_observation_metadata` (REQ-13 contract).
  - `tests/bdd/req14_drift_resilience.feature` (NEW, +120 LOC): 4 BDD
    scenarios for graph_unavailable + timeout + retry behavior.
  - `tests/bdd/req16_skill_prose.feature` (NEW, +60 LOC): 2 BDD
    scenarios for the runtime SKILL.md grep check (REQ-16).
  - `tests/bdd/test_decision_reality_drift_steps.py` (MODIFY, +400 LOC):
    step glue for the 6 new feature files (or split per REQ for clarity;
    mirrors the `test_graph_snapshots_steps.py` precedent).

- **Batch D (CHANGELOG + meta + verify)**:
  - `CHANGELOG.md` (MODIFY, +20 LOC): v0.8.0 entry listing all 5 REQs
    + W23 deprecation note + `BREAKING:` section for the dataclass
    shape change.
  - `pyproject.toml` (MODIFY, +1/-1 LOC): `version = "0.8.0"`.
  - `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md`
    (MODIFY, ~80 LOC): drift-hardening hook prose (mirror observability
    SKILL.md hook from change #6).

**Out of scope (deferred to v1.1 or named follow-up changes)**:

- JSONL rotation policy for `drift_events.jsonl` (mirror
  `FLOW_METRICS_MAX_BYTES` from observability REQ-44 — deferred to v1.1)
- Cross-project federation awareness for drift events
  (`flow drift events --project=<key>` filter)
- OpenTelemetry push for drift events
- Dataclass migration tooling (no `FindingLegacy` shim — the 1-release
  `DeprecationWarning` alias is the migration path for v0.8.0; cleanup
  in v1.0)
- `flow drift events --format=<prometheus>` (REQ-58 from observability
  mirror for the JSONL read-side)
- Per-finding classification: refine `classify_binding` to handle
  graph_unavailable at the finding level (currently a report-level flag)

### Public API surface (NEW)

```python
# src/flow_engineering/drift_event_log.py — NEW public API (REQ-55)
def record_drift_event(report: DriftReport, *, path: Path | None = None) -> None: ...
def iter_drift_events(path: Path | None = None,
                      *, since_iso: str | None = None,
                      change: str | None = None) -> Iterator[dict]: ...
DEFAULT_PATH: Path  # ~/.flow-engineering/drift_events.jsonl
ROTATE_BYTES: int   # 10 MB

# src/flow_engineering/observability.py — NEW counters (REQ-55)
"drift_event_log_total": "Number of drift events appended to drift_events.jsonl"
"drift_event_log_bytes": "Current size in bytes of drift_events.jsonl"

# src/flow_engineering/decision_drift.py — MODIFIED dataclass shape (REQ-56)
class Finding:
    decision_id: int                    # was: str
    binding_id: str
    finding_class: FindingClass
    message: str

class DriftReport:
    change: str
    scanned_at: str                     # was: float — ISO 8601 UTC
    unable_to_verify: bool = False      # was: graph_unavailable
    unable_reason: str | None = None    # NEW
    findings: tuple[Finding, ...] = ()
    # @property graph_unavailable → @DeprecationWarning alias

def classify_binding(ref: BindingRef,
                     graph_nodes: dict[str, GraphNode]) -> FindingClass:  # was: 3 args
    ...

# src/flow_engineering/cli.py — MODIFIED stderr WARN (REQ-59 S2)
# _write_back_findings() now emits "WARN: drift write-back skipped N
# non-int decision_ids" to stderr once per batch when skipped_total > 0.
```

### Breaking-change policy (REQ-56)

The dataclass shape change (`decision_id: int`, `scanned_at: str`,
`unable_to_verify` rename, `classify_binding` arg-list) IS a public
API break. Mitigation:

- **`@property graph_unavailable`** retained on `DriftReport` for
  exactly **1 release** (v0.8.0) as a `DeprecationWarning`-emitting
  alias. Cleanup in v1.0.
- **`Finding.__post_init__`** accepts legacy numeric `str` inputs and
  coerces to `int` with `DeprecationWarning` for v0.8.0. Hard break in
  v1.0.
- **`DriftReport.from_scanned()`** classmethod accepts legacy `float`
  epoch inputs and coerces to ISO `str`. v1.0 removes the classmethod.
- **Version bump**: `pyproject.toml` `0.7.0` → `0.8.0`. CHANGELOG
  `BREAKING:` section lists the migration steps.

The project has 4 archived changes and **no third-party consumers**
(no public PyPI package; `pip install flow-engineering` is not a
supported install path; the `[project.optional-dependencies] dev`
extras in `pyproject.toml` are the only entry point). Hard break is
acceptable.

### Non-breaking guarantees

- `flow drift scan <change>` exit-code semantics unchanged (0 still-valid,
  1 stale, 2 unable_to_verify, 3 usage error).
- `flow drift scan --format=<text|json>` default text output
  byte-identical (only the dataclass field types change; the rendered
  text shape is unchanged).
- The new `--drift-event-log[=<path>]` flag on `flow drift daemon` is
  OPT-IN default-on; `--no-drift-event-log` disables. The existing
  `on_summary` callback behavior is preserved when the flag is unset
  (default).
- `flow metrics` (observability) consumers see no new counter names
  beyond the 2 catalog additions (`drift_event_log_total`,
  `drift_event_log_bytes`) — REQ-37 `--domain drift` filter surfaces them.
- `tests/bdd/req9_drift_detection.feature` (14 scenarios) and
  `req15_drift_daemon.feature` (3 scenarios) remain green — they exercise
  the same behavior, just with the renamed dataclass fields.
- All existing 947 tests pass — verified locally before PR open.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `src/flow_engineering/decision_drift.py` | MODIFY | REQ-56 (W8) dataclass shape sync (decision_id int, scanned_at str ISO, unable_to_verify+unable_reason); 2-arg classify_binding; +40/-20 LOC |
| `src/flow_engineering/drift_event_log.py` | **NEW** | REQ-55 (W5) JSONL writer + rotation + `record_drift_event` helper + `iter_drift_events`; +150 LOC |
| `src/flow_engineering/daemon.py` | MODIFY | REQ-55 wire `record_drift_event` into `handle_apply_progress_event`; W6 still-valid silence rule; +30/-10 LOC |
| `src/flow_engineering/cli.py` | MODIFY | REQ-59 S2 stderr WARN in `_write_back_findings`; REQ-56 minor type-cast updates for the dataclass rename; `flow drift daemon --drift-event-log` flag; +40/-5 LOC |
| `src/flow_engineering/observability.py` | MODIFY | REQ-55 `record_drift_event` helper + `drift_event_log_total`/`drift_event_log_bytes` counter catalog entries; +15 LOC |
| `src/flow_engineering/snapshot_manager.py` | MODIFY | 0 LOC (REQ-58 is spec/design-only; `size_bytes` + `freed_bytes` already correct in impl) |
| `openspec/specs/drift-hardening/spec.md` | **NEW** | Capability spec — REQ-55..59 with all 21 BDD scenarios + dataclass shape contract + counter catalog; ~250 LOC; bootstraps a new capability spec |
| `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` | MODIFY | REQ-56 reconcile Finding/DriftReport shape + REQ-55 REQ-15 JSONL contract reaffirmation; +5/-5 LOC |
| `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md` | MODIFY | REQ-56 reconcile dataclass type signatures at lines 134-155; +10/-8 LOC |
| `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` | MODIFY | REQ-58 W26 `freed_bytes` field reconciliation at line 230; +3/-3 LOC |
| `openspec/changes/archive/2026-06-27-graph-snapshots/design.md` | MODIFY | REQ-58 W25 `size_bytes` + `pinned` field documentation at line 271; +5/-5 LOC |
| `tests/unit/test_drift_event_log.py` | **NEW** | REQ-55 JSONL writer unit tests (rotation, append, schema, counter increment, idempotency); +180 LOC |
| `tests/unit/test_decision_drift.py` | MODIFY | REQ-56 dataclass shape round-trip + `DeprecationWarning` capture tests; +30 LOC |
| `tests/unit/test_daemon_drift_events.py` | MODIFY | REQ-55 event-log integration + W6 still-valid silence; +20 LOC |
| `tests/unit/test_cli_watch_drift.py` | MODIFY | REQ-55 CLI wiring + `--drift-event-log` flag; +10 LOC |
| `tests/unit/test_cli_drift.py` | MODIFY | REQ-59 S2 stderr WARN capture + REQ-56 cast site updates; +25 LOC |
| `tests/bdd/req10_drift_cli.feature` | **NEW** | REQ-57 9 BDD scenarios for the CLI surface |
| `tests/bdd/req11_drift_exit.feature` | **NEW** | REQ-57 3 BDD scenarios for exit-code semantics |
| `tests/bdd/req12_drift_counters.feature` | **NEW** | REQ-57 3 BDD scenarios for the 8 drift counters |
| `tests/bdd/req13_drift_metadata.feature` | **NEW** | REQ-57 3 BDD scenarios for `update_observation_metadata` |
| `tests/bdd/req14_drift_resilience.feature` | **NEW** | REQ-57 4 BDD scenarios for graph_unavailable + timeout + retry |
| `tests/bdd/req16_skill_prose.feature` | **NEW** | REQ-57 2 BDD scenarios for the runtime SKILL.md grep check |
| `tests/bdd/req15_drift_daemon.feature` | MODIFY | REQ-55 extend with 2 JSONL event-log scenarios; +80 LOC |
| `tests/bdd/test_decision_reality_drift_steps.py` | MODIFY or split | REQ-57 step glue for 6 new feature files; +400 LOC (or split per REQ for clarity) |
| `CHANGELOG.md` | MODIFY | v0.8.0 entry post-merge (batch D); W23 deprecation note in v0.6.0 Notes section (batch B); +40 LOC total |
| `pyproject.toml` | MODIFY | `version = "0.8.0"` (REQ-56 breaking change mandates minor bump); +1/-1 LOC |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | MODIFY | drift-hardening hook prose; ~80 LOC runtime-only |
| `openspec/changes/drift-hardening/{design,spec,tasks}.md` | NEW | follow-on phases (sdd-design, sdd-spec, sdd-tasks outputs) |

## Capabilities

### New Capabilities

- `drift-hardening`: cluster change that closes 8 documented
  carry-forwards from changes #2 (decision-reality-drift) and #5
  (graph-snapshots). Ships the `drift_events.jsonl` append-only
  event log with rotation (REQ-55); the still-valid silence rule
  (REQ-55 W6); the v0.8.0 dataclass shape migration for
  `Finding`/`DriftReport`/`classify_binding` (REQ-56) with 1-release
  `DeprecationWarning` aliases; 21 new BDD scenarios across 6 feature
  files completing REQ-10/12/13/14/16 coverage (REQ-57); spec/design
  field reconciliation for `SnapshotMeta.size_bytes` + `pinned` and
  `PruneResult.freed_bytes` (REQ-58); CHANGELOG deprecation note for
  the W23 dual-name `snapshot_pruned_total` ↔ `snapshot_prune_total`
  coexistence + stderr WARN on silent write-back skip (REQ-59). The
  v0.8.0 version bump signals the breaking shape change. The new
  capability spec at `openspec/specs/drift-hardening/spec.md` catalogs
  REQ-55..59 alongside the drift detection contract from change #2.

### Modified Capabilities

- `decision-reality-drift` (REQ-9..16): the `Finding.decision_id`
  field type changes from `str` to `int` (1-release soft compat via
  `__post_init__` coercion + `DeprecationWarning`); the
  `DriftReport.scanned_at` field type changes from `float` to `str`
  (ISO 8601 UTC); `DriftReport.graph_unavailable` is renamed to
  `unable_to_verify` with a new `unable_reason: str | None` field
  (`@property graph_unavailable` retained for 1 release as a
  `DeprecationWarning`-emitting alias); `classify_binding(ref, graph_nodes,
  current_id_map)` 3-arg signature refactored to
  `classify_binding(ref, graph_nodes)` 2-arg (the
  `current_id_map` is now derived inside). REQ-15 daemon gains a new
  `--drift-event-log[=<path>]` flag (default-on) that wires
  `record_drift_event` into the `on_summary` callback. REQ-15 also
  gains a still-valid silence rule (no stdout summary when
  `total == 0 and not unable_to_verify`). Each modification is delta-
  documented in the archived `spec.md` + `design.md` per the SDD
  governance precedent from observability.
- `graph-snapshots` (REQ-28..34): spec/design field-name reconciliation
  — `SnapshotMeta.size_bytes` (was `file_size_bytes` in design); add
  `pinned: bool` retention-pin field documentation (already in impl);
  `PruneResult.freed_bytes` (was `freed_bytes_estimate` in
  spec/design). 0 production code change. W23 dual-name coexistence
  (`snapshot_pruned_total` ↔ `snapshot_prune_total`) is documented in
  CHANGELOG v0.6.0 Notes section + REQ-34 spec banner; consumers
  guided to use REQ-37 `--domain snapshot` filter.

## Risks

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | REQ-56 (W8) public API break: `decision_id: str → int`, `scanned_at: float → str`, `graph_unavailable → unable_to_verify`, `classify_binding` 3→2 args — third-party consumers (if any) break at runtime / mypy strict | MED | Hard migration is acceptable (no third-party consumers per Engram #92 `sdd-init`); 1-release `DeprecationWarning` aliases for `graph_unavailable` and `Finding.__post_init__` str coercion; v0.7.0 → v0.8.0 version bump; CHANGELOG `BREAKING:` section with migration steps |
| 2 | REQ-55 (W5) JSONL writer unbounded growth: `drift_events.jsonl` can exceed 100 MB/year on a long-running watcher | MED | Mirror `metrics.jsonl` rotation policy — rotate when file > 10 MB to `drift_events.<timestamp>.jsonl` + start fresh (sub-feature of REQ-55, no separate REQ). REQ-44 metrics rotation is deferred to v1.1; both deferred items land together in a future "metrics+drift-jsonl-rotation" change |
| 3 | REQ-59 (W23) wire-format compatibility: legacy `snapshot_pruned_total` events (K=101+) coexist with renamed `snapshot_prune_total` (K=70+) in `~/.flow-engineering/metrics.jsonl`; sum-based queries double-count | LOW | PREFERRED: CHANGELOG v0.6.0 Notes section documents coexistence + recommends REQ-37 `--domain snapshot` consumers use the catalog filter; no code change beyond a 3-line CHANGELOG entry. If a downstream consumer materializes, revisit as REQ-59 follow-up |
| 4 | REQ-57 (W4) BDD coverage scope: 21 scenarios risk becoming tautological (just `@scenario`-bound unit tests without business-domain phrasing) | MED | Quality gate: each BDD scenario MUST use business-domain Given/When/Then (e.g., "Given a decision with bindings at file X line Y", "When flow drift scans the change", "Then the report shows STILL_VALID") NOT unit-test phrasing ("Given a fixture dict X"); sdd-verify Step 6b asserts the 21-scenario count + spot-checks 3 random scenarios for business-domain phrasing |
| 5 | Single PR realistic LOC ~9 700 (close to observability's ~10 910 chained-PR threshold); reviewer fatigue on a 4-batch single-PR | MED | Per-commit work-unit splits per `work-unit-commits` skill (4-6 commits each ≤400 LOC); 4 batches in PR description; reviewer reads commit-by-commit not as one blob |
| 6 | Batch C BDD coverage (21 scenarios) is the bottleneck at ~60 min; if rushed, quality degrades (tautological scenarios) | MED | Split Batch C into Batch C1 (req10+req12+req16 = 14 scenarios, simpler) + Batch C2 (req11+req13+req14 = 7 scenarios, more complex resilience tests); final tests in Batch D |
| 7 | Step glue module size: `test_decision_reality_drift_steps.py` +400 LOC for the 6 new feature files pushes the file past 1 000 LOC (review-awkward) | LOW | Split per REQ into `test_req10_steps.py`, `test_req12_steps.py`, etc. — mirrors the req28..34 split that `test_graph_snapshots_steps.py` uses |
| 8 | `flow` script has potential (unconfirmed) third-party consumers; REQ-56 break could surprise downstream | LOW | Pre-flight: `pip search flow-engineering` to confirm unrelated packages; verify `pyproject.toml` is the only install entry point (per Engram #92 `sdd-init`, project is unpublished); if a consumer surfaces, pivot to soft migration (Risk 1 mitigation b) |
| 9 | Drift detection hook (REQ-9..16) integration with the new JSONL sink: if `record_drift_event` raises (e.g., disk full), daemon crashes mid-tick | LOW | Wrap the append in `try/except OSError`; on failure, log to stderr and continue (matches `observability.increment()` policy — best-effort, never crashes the caller); BDD scenario covers disk-full path |
| 10 | Snapshot field-name reconciliation (REQ-58 W25/W26) is spec/design-only, but downstream BDD consumers may have hardcoded the old `file_size_bytes` / `freed_bytes_estimate` names | LOW | REQ-34 BDD scenarios don't assert exact field name (per explore #222); verify before merge via grep on `tests/bdd/req28..34_*.feature` for the legacy names; if found, rename in the same Batch A commit |

## Rollback Plan

All artifacts are additive or have 1-release deprecation aliases. Single
revert of the merge commit restores pre-change state:

- `src/flow_engineering/drift_event_log.py` is NEW; deleting it removes
  the JSONL sink but does not break any runtime behavior (the daemon
  callback still works without it).
- `src/flow_engineering/observability.py` gains 2 catalog entries
  (`drift_event_log_total`, `drift_event_log_bytes`) and a
  `record_drift_event` helper; all are pure additions, no existing
  function modified.
- `src/flow_engineering/decision_drift.py` MODIFIED for REQ-56 — the
  changes are gated by `@property` / `__post_init__` aliases that accept
  legacy str/float inputs. Reverting the dataclass edits restores
  pre-v0.8.0 behavior.
- `src/flow_engineering/daemon.py` MODIFIED — the new
  `record_drift_event` call is wrapped in `try/except` and gated by the
  `--drift-event-log` flag (default-on). Disabling the flag restores
  v0.7.0 behavior.
- `src/flow_engineering/cli.py` MODIFIED — the new stderr WARN in
  `_write_back_findings` is a single `print(..., file=sys.stderr)`; the
  legacy silent-skip behavior is preserved (the WARN is additive on
  top).
- 6 NEW BDD feature files; 1 MODIFIED BDD feature file; step glue MODIFY.
  Removing the new files disables BDD coverage for REQ-10/12/13/14/16
  but does not break the existing 947 tests.
- `~/.flow-engineering/drift_events.jsonl` is the user-owned file;
  not touched by the revert (the file remains on disk but is no longer
  appended to).
- CHANGELOG and `pyproject.toml` revert cleanly to v0.7.0.

To restore the pre-change-#8 install: `git revert <PR-merge>`. The
JSONL event format is forward-only (no schema migration); the user's
existing `metrics.jsonl` and any pre-existing `drift_events.jsonl`
survive intact.

## Dependencies

- **None new.** Uses stdlib `json` + `pathlib` + `time` + `dataclasses`
  + `datetime` + `warnings` + `enum` + `sys`. The JSONL event format
  is a string serialization emitted to a `Path` — no runtime dep needed.
- `decision-reality-drift` (shipped v0.3.0) — `Finding` / `DriftReport`
  / `classify_binding` / `record_drift_summary()` are the foundation
  being migrated (REQ-56).
- `decision-code-linking` (shipped v0.2.0) — `observability.increment()`
  + `read_all()` are the foundation for REQ-55 counter emission.
- `graph-snapshots` (shipped v0.6.0) — `SnapshotMeta` / `PruneResult`
  / `SNAPSHOT_COUNTER_NAMES` catalog are the foundation being reconciled
  (REQ-58).
- `observability` (change #6, shipped v0.7.0) — `flow metrics summary`,
  `--domain` filter, and `--since` window are the foundation for the
  REQ-37 `--domain snapshot` recommendation in REQ-59.
- `prompt-registry` (#7, future) — **MUST ARCHIVE BEFORE change #8
  starts** to preserve REQ-55 numbering (REQ-45..54 are reserved for
  prompt-registry per Engram #183 + #201).

## Open Questions (for sdd-design)

The 10 questions below MUST be resolved in the design phase before
`sdd-spec` locks the requirement contract. Mirror of
[`explore.md`](./explore.md) §D, expanded with design-phase specifics.

1. **REQ-56 backward compat (W8 / OQ-1)**: hard migration, soft
   migration (1-release `DeprecationWarning` aliases), or dual
   dataclasses (`Finding` + `FindingLegacy`)? **Recommend hard
   migration** (bump v0.7.0 → v0.8.0) per Risk 1 + Engram #92
   `sdd-init` (no third-party consumers). Decision needed: explicit
   confirmation that `pip search flow-engineering` shows no unrelated
   packages; `pyproject.toml` is the only install entry point.

2. **REQ-55 JSONL rotation threshold (W5 / OQ-2)**: 10 MB (mirror
   `metrics.jsonl` policy) or smaller (5 MB, more aggressive) or larger
   (50 MB, less I/O churn)? **Recommend 10 MB** — same precedent.
   Decision needed: confirm rotation is automatic on append (no separate
   cron / hook) and that rotated files use the `drift_events.<iso>.jsonl`
   naming pattern (sortable lexicographically by rotation time).

3. **REQ-55 still-valid silence scope (W6 / OQ-3)**: silence only when
   `total == 0 and not unable_to_verify` (the explore recommendation),
   OR also silence when `total == 0 and unable_to_verify` (broader),
   OR never silence (always emit summary for audit)? **Recommend the
   first** — still-valid-but-graph-unavailable is informative (the user
   should know the graph is unreachable). Decision needed: confirm the
   spec phrase "no event-log line on still-valid" means "no stdout line"
   (not "no JSONL line").

4. **REQ-56 migration timeline (W8 / OQ-4)**: ship REQ-56 in the same
   single PR as REQ-55/57/58/59 (cluster change), OR split REQ-56 into
   a separate v0.8.0-migration change (just the dataclass shape +
   CHANGELOG)? **Recommend same PR** — the v0.8.0 version bump is a
   single event; splitting forces two v0.8.0 entries or a v0.7.1 +
   v0.8.0 sequence. Decision needed: confirm the cluster identity is
   worth the single-PR review effort.

5. **REQ-57 BDD scenario source (W4 / OQ-5)**: write the 21 scenarios
   fresh (full business-domain Given/When/Then), OR extract from
   existing unit-test contracts (`test_cli_drift.py`,
   `test_observability.py`, `test_engram_io_code_refs.py`)? **Recommend
   translate** — the unit tests are the source of truth; BDD scenarios
   mirror their contracts in Gherkin phrasing. Decision needed: confirm
   that the existing unit tests are sufficient (i.e., no missing
   behavior tests in the unit-test suite that BDD scenarios should
   surface for the first time).

6. **REQ-58 spec reconciliation scope (W25/W26 / OQ-6)**: update the
   archived change #5 `spec.md` + `design.md` ONLY (single source of
   truth), OR also update the original change #5 spec.md in-place (live
   file)? **Recommend archived only** — per SDD governance, archived
   specs are the source of truth and live changes are append-only
   (cannot modify a shipped change). Decision needed: confirm the
   archive-folder is the long-term edit target.

7. **REQ-59 W23 deprecation note placement (OQ-7)**: CHANGELOG v0.6.0
   Notes section ONLY, OR also runtime WARN log when reading old metric
   names (e.g., `flow metrics` emits "10 legacy `snapshot_pruned_total`
   events dropped")? **Recommend CHANGELOG only** — runtime WARN would
   be noisy on every `flow metrics` invocation; preserve audit trail;
   no consumer exists yet. Decision needed: confirm the deprecation is
   informational only (no consumer migration tooling needed).

8. **REQ-59 S2 stderr WARN cadence (OQ-8)**: once per batch
   (cumulative `skipped_total > 0` triggers one WARN), OR once per
   skipped item (1+ WARN per row), OR only when `skipped_total >= 5`
   (avoid noise for sporadic skips)? **Recommend once per batch with a
   threshold** (`skipped_total >= 3` to start; tunable via env var
   `FLOW_DRIFT_SKIP_WARN_THRESHOLD`). Decision needed: confirm the
   threshold matches the spec phrasing "user should notice skipped
   writebacks".

9. **REQ-55 read-side surface**: ship `flow drift events` CLI (mirror
   `flow metrics summary`) in the same PR, OR defer to a follow-up
   change? **Recommend defer** — REQ-55 spec only requires the append
   side; the read side is a UI convenience that observability's
   `flow metrics summary` already provides indirectly. Decision needed:
   confirm the JSONL is "audit-only" for v0.8.0 and the read side lands
   in a v1.0 / "drift-events-dashboard" change.

10. **REQ-56 `classify_binding` arg-list compat**: 2-arg with
    `current_id_map` derived inside (clean break), OR 2-arg with
    optional `current_id_map: dict | None = None` parameter for 1-release
    compat (soft)? **Recommend clean break** — `current_id_map` was an
    implementation detail; no documented external caller. Decision
    needed: grep `tests/` + `openspec/` for any caller passing 3 args
    and confirm the migration is mechanical.

## Success Criteria

- [ ] `flow drift daemon --drift-event-log` appends one JSON line per
      non-still-valid finding to `~/.flow-engineering/drift_events.jsonl`
      (REQ-55, 2 BDD scenarios + 6 unit tests)
- [ ] `flow drift daemon --no-drift-event-log` disables JSONL append
      (REQ-55, 1 BDD scenario)
- [ ] `flow drift daemon` outer summary line is suppressed when
      `total == 0 and not unable_to_verify` (REQ-55 W6, 1 BDD scenario)
- [ ] `flow drift daemon` outer summary line is preserved when
      `unable_to_verify=True` with the unable_reason (REQ-55 W6 + W8
      edge case, 1 BDD scenario)
- [ ] `drift_events.jsonl` rotation when file > 10 MB produces a
      `drift_events.<iso>.jsonl` sibling + fresh `drift_events.jsonl`
      (REQ-55, 2 unit tests)
- [ ] `Finding.decision_id` accepts `int` directly; legacy numeric `str`
      inputs are coerced with `DeprecationWarning` (REQ-56, 4 unit tests)
- [ ] `DriftReport.scanned_at` accepts `str` (ISO 8601) directly;
      legacy `float` epoch inputs are coerced via `from_scanned()`
      (REQ-56, 4 unit tests)
- [ ] `DriftReport.graph_unavailable` `@property` emits
      `DeprecationWarning` and returns `unable_to_verify` value
      (REQ-56, 2 unit tests)
- [ ] `classify_binding(ref, graph_nodes)` 2-arg signature works;
      3-arg callers get `TypeError` (REQ-56 W8, 2 unit tests)
- [ ] 21 new BDD scenarios across 6 feature files pass
      (`uv run pytest tests/bdd/req{10,11,12,13,14,16}_*.feature -v` shows
      0 failures) (REQ-57)
- [ ] Each of the 21 new BDD scenarios uses business-domain Given/When/Then
      phrasing (sdd-verify Step 6b spot-check on 3 random scenarios)
- [ ] `flow drift write-back` emits a single stderr WARN when
      `skipped_total >= 3` non-int decision_ids are encountered
      (REQ-59 S2, 2 unit tests)
- [ ] CHANGELOG v0.6.0 Notes section documents W23 dual-name coexistence
      + REQ-37 `--domain snapshot` filter recommendation
      (REQ-59 W23, 0 tests — runtime grep on CHANGELOG.md)
- [ ] Archived `design.md` `SnapshotMeta` contract block documents
      `size_bytes: int` (not `file_size_bytes`) + `pinned: bool`
      retention-pin field (REQ-58 W25, 0 tests — runtime grep on design.md)
- [ ] Archived `spec.md` + `design.md` `PruneResult` field is
      `freed_bytes` (not `freed_bytes_estimate`) (REQ-58 W26, 0 tests —
      runtime grep)
- [ ] `pyproject.toml` `version = "0.8.0"`; CHANGELOG v0.8.0 entry
      lists all 5 REQs + `BREAKING:` section for the dataclass shape
- [ ] All existing 947 tests pass; `ruff check` clean on changed files
- [ ] Strict TDD evidence: every public helper has RED→GREEN→REFACTOR
      history in commit log; per-commit work-unit splits per
      `work-unit-commits` skill (4-6 commits each ≤400 LOC)
- [ ] Drift detector (REQ-9..16) behavior unchanged for end users —
      the dataclass shape change is internal; CLI output + exit codes
      byte-identical to v0.7.0
- [ ] Snapshot create/list/diff/rollback/prune (REQ-28..34) behavior
      unchanged — REQ-58 is spec/design-only reconciliation
- [ ] Observability counters (REQ-8, REQ-12, REQ-22, REQ-26, REQ-28..34)
      unchanged; the 2 new counters (`drift_event_log_total`,
      `drift_event_log_bytes`) appear in the `openspec/specs/observability/spec.md`
      catalog as additive entries

## Cross-Impact

| Queued/shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | `observability.increment()` reused for the 2 new counters | Compatible (consumes the seam) |
| `decision-reality-drift` (shipped v0.3.0) | `Finding`/`DriftReport`/`classify_binding` shape migrated (REQ-56); `record_drift_summary()` extended | **MIGRATION**: shape change with 1-release deprecation aliases |
| `vector-semantic-search` (shipped v0.4.0) | Unrelated layer | No conflict |
| `cross-project-federation` (shipped v0.5.0) | Unrelated layer | No conflict |
| `graph-snapshots` (shipped v0.6.0) | `SnapshotMeta`/`PruneResult` field names reconciled (REQ-58); `SNAPSHOT_COUNTER_NAMES` catalog extended with W23 deprecation note (REQ-59) | Compatible (consumes the seam) |
| `observability` (change #6, shipped v0.7.0) | `flow metrics summary` + `--domain` filter recommended for REQ-59 W23 deprecation; `record_drift_event()` helper mirrors the 5 existing `record_*_summary` helpers | Compatible (consumes the seam) |
| `prompt-registry` (#7, future) | Unrelated layer; MUST ARCHIVE BEFORE change #8 starts (preserves REQ-55 numbering) | No conflict |

**Unblocks**: 8 documented carry-forwards closed (W4/W5/W6/W8/S2 from
#2 + W23/W25/W26 from #5); v0.8.0 release ships with public API
breaking change documented; the `drift_events.jsonl` audit trail is
available for downstream consumers; the 21 missing BDD scenarios for
REQ-10/12/13/14/16 are present (spec-vs-test gap closed since v0.3.0);
the W23 dual-name coexistence is officially documented.

**Constrains**: any future change that touches the `Finding`/
`DriftReport`/`classify_binding` signature MUST NOT introduce new
fields before v1.0 (the `@property graph_unavailable` alias is the only
backward-compat surface); the `drift_events.jsonl` schema is locked
for v0.8.0 (`{ts, change, decision_id, binding_id, class,
detected_at}`); any future change that adds a drift counter MUST add
it to the `DRIFT_COUNTER_NAMES` catalog in `observability.py` and the
`openspec/specs/observability/spec.md` domain table.

## Estimated Effort

- **Apply LOC (forecast)**: ~225 production + ~1 600 tests + ~28
  archived spec/design = ~1 853 forecast total. Realistic ×6 TDD
  multiplier (per `decision-code-linking` S3 precedent): ~9 700 realistic.
- **Single PR strategy**: **YES — single PR** (forecast 1 853 is
  below the observability 10 910 chained-PR threshold; the cluster is
  thematically unified):
  - 4 apply batches: A (REQ-56 + REQ-58, ~60 min) → B (REQ-55 + REQ-59,
    ~60 min) → C (REQ-57, ~60 min) → D (CHANGELOG + meta, ~30 min).
  - Per-commit work-unit splits per `work-unit-commits` skill
    (4-6 commits each ≤400 LOC).
- **Phase estimate**:
  - ~20 min explore (DONE; Engram #222)
  - ~10 min propose (this phase)
  - ~30 min design
  - ~20 min spec
  - ~20 min tasks
  - ~210 min apply across 4 batches (A 60 + B 60 + C 60 + D 30)
  - ~20 min verify
  - ~15 min archive
  - **Total ~5-5.5h end-to-end**

## References

- Explore: [`explore.md`](./explore.md) (Engram #222, full option matrix)
- Prior patterns:
  - `openspec/changes/archive/2026-06-27-observability/` (change #6,
    chained-PR precedent + `openspec/specs/` bootstrap pattern)
  - `openspec/changes/archive/2026-06-27-graph-snapshots/` (change #5,
    single-PR precedent for the cluster change; `SNAPSHOT_COUNTER_NAMES`
    catalog pattern referenced by REQ-59)
  - `openspec/changes/archive/2026-06-26-decision-reality-drift/`
    (change #2, source of W4/W5/W6/W8/S2 carry-forwards)
- Carry-forwards: `decision-reality-drift` verify-report #135 (W4/W5/
  W6/W7/W8/S1/S2); `graph-snapshots` verify-report #188 (W20..W27)
- Counter catalog patterns: REQ-12 (`record_drift_summary`), REQ-26
  (`SNAPSHOT_COUNTER_NAMES`) — both in `observability.py`
- Precedent: `decision-code-linking` archive-report #119 S3
  (BDD step def file 5-6× growth multiplier) — absorbed into the ×6
  forecast

## Next Step

Ready for `sdd-design drift-hardening`. The 10 open questions above
MUST be resolved in the design phase (especially #1 REQ-56 backward
compat, #4 REQ-56 migration timeline, #5 REQ-57 BDD source, and #7
REQ-59 W23 deprecation placement) before `sdd-spec` locks the
requirement contract. **Single PR** with 4 apply batches (A: REQ-56 +
REQ-58; B: REQ-55 + REQ-59; C: REQ-57; D: CHANGELOG + meta).
Coordination: change #7 `prompt-registry` MUST archive before change
#8 starts to preserve REQ-55..59 numbering (REQ-45..54 are reserved
for prompt-registry per Engram #183 + #201).

<!-- code_refs -->
{
  "schema_version": 1,
  "source": "manual",
  "nodes": [
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_finding",
      "label": "Finding dataclass (decision_id: int post REQ-56; was str)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 60,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_drift_report",
      "label": "DriftReport dataclass (scanned_at: str ISO, unable_to_verify+unable_reason post REQ-56; graph_unavailable @property alias 1 release)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 70,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_decision_drift_classify_binding",
      "label": "classify_binding(ref, graph_nodes) — 2-arg post REQ-56 W8 (was 3-arg)",
      "file": "src/flow_engineering/decision_drift.py",
      "line": 84,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_drift_event_log_module",
      "label": "drift_event_log.py (NEW — ~150 LOC; JSONL writer + rotation + record_drift_event + iter_drift_events)",
      "file": "src/flow_engineering/drift_event_log.py",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_record_drift_event",
      "label": "record_drift_event() helper (NEW — REQ-55; emits drift_event_log_total + drift_event_log_bytes)",
      "file": "src/flow_engineering/observability.py",
      "line": 462,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_observability_increment",
      "label": "increment(name, **fields) — unchanged primary sink API (REQ-8 close)",
      "file": "src/flow_engineering/observability.py",
      "line": 162,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_daemon_handle_apply_progress_event",
      "label": "handle_apply_progress_event (daemon.py:34-98) — MODIFY: wire record_drift_event; W6 still-valid silence rule",
      "file": "src/flow_engineering/daemon.py",
      "line": 34,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_daemon_start_watch",
      "label": "start_watch (daemon.py:144-210) — MODIFY: --drift-event-log flag (default-on)",
      "file": "src/flow_engineering/daemon.py",
      "line": 144,
      "confidence": 0.9,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_write_back_findings",
      "label": "_write_back_findings (cli.py:1637-1674) — MODIFY: REQ-59 S2 stderr WARN once per batch",
      "file": "src/flow_engineering/cli.py",
      "line": 1637,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "src_flow_engineering_cli_drift_daemon",
      "label": "flow drift daemon subcommand — MODIFY: --drift-event-log[=<path>] flag",
      "file": "src/flow_engineering/cli.py",
      "line": 1500,
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
      "id": "src_flow_engineering_observability_snapshot_counter_names",
      "label": "SNAPSHOT_COUNTER_NAMES catalog (REQ-26 T1.7, 4 names) — REQ-59 W23 deprecation note in CHANGELOG",
      "file": "src/flow_engineering/observability.py",
      "line": 124,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_specs_drift_hardening_spec",
      "label": "openspec/specs/drift-hardening/spec.md (NEW — REQ-55..59 capability spec + dataclass shape contract)",
      "file": "openspec/specs/drift-hardening/spec.md",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_changes_archive_decision_reality_drift_design",
      "label": "openspec/changes/archive/2026-06-26-decision-reality-drift/design.md (lines 134-155) — MODIFY: REQ-56 reconcile dataclass types",
      "file": "openspec/changes/archive/2026-06-26-decision-reality-drift/design.md",
      "line": 134,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_changes_archive_decision_reality_drift_spec",
      "label": "openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md — MODIFY: REQ-56 reconcile scenario shape + REQ-55 REQ-15 JSONL",
      "file": "openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md",
      "line": 1,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_changes_archive_graph_snapshots_spec",
      "label": "openspec/changes/archive/2026-06-27-graph-snapshots/spec.md (line 230) — MODIFY: REQ-58 W26 freed_bytes",
      "file": "openspec/changes/archive/2026-06-27-graph-snapshots/spec.md",
      "line": 230,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "openspec_changes_archive_graph_snapshots_design",
      "label": "openspec/changes/archive/2026-06-27-graph-snapshots/design.md (line 271) — MODIFY: REQ-58 W25 size_bytes + pinned",
      "file": "openspec/changes/archive/2026-06-27-graph-snapshots/design.md",
      "line": 271,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req10_drift_cli",
      "label": "tests/bdd/req10_drift_cli.feature (NEW — REQ-57 9 BDD scenarios)",
      "file": "tests/bdd/req10_drift_cli.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req11_drift_exit",
      "label": "tests/bdd/req11_drift_exit.feature (NEW — REQ-57 3 BDD scenarios)",
      "file": "tests/bdd/req11_drift_exit.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req12_drift_counters",
      "label": "tests/bdd/req12_drift_counters.feature (NEW — REQ-57 3 BDD scenarios)",
      "file": "tests/bdd/req12_drift_counters.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req13_drift_metadata",
      "label": "tests/bdd/req13_drift_metadata.feature (NEW — REQ-57 3 BDD scenarios)",
      "file": "tests/bdd/req13_drift_metadata.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req14_drift_resilience",
      "label": "tests/bdd/req14_drift_resilience.feature (NEW — REQ-57 4 BDD scenarios)",
      "file": "tests/bdd/req14_drift_resilience.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req16_skill_prose",
      "label": "tests/bdd/req16_skill_prose.feature (NEW — REQ-57 2 BDD scenarios)",
      "file": "tests/bdd/req16_skill_prose.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_bdd_req15_drift_daemon",
      "label": "tests/bdd/req15_drift_daemon.feature (MODIFY — REQ-55 2 new scenarios for JSONL + W6 still-valid silence)",
      "file": "tests/bdd/req15_drift_daemon.feature",
      "line": 1,
      "confidence": 0.85,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "tests_unit_test_drift_event_log",
      "label": "tests/unit/test_drift_event_log.py (NEW — REQ-55 JSONL writer unit tests; ~180 LOC)",
      "file": "tests/unit/test_drift_event_log.py",
      "line": 1,
      "confidence": 0.85,
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
      "id": "pyproject_toml_version",
      "label": "pyproject.toml version (line 3) — MODIFY: 0.7.0 → 0.8.0 (REQ-56 breaking change mandates minor bump)",
      "file": "pyproject.toml",
      "line": 3,
      "confidence": 0.95,
      "source": "manual"
    },
    {
      "project": "flow-engineering",
      "id": "changelog_v080_entry",
      "label": "CHANGELOG.md v0.8.0 entry — NEW: 5 REQs + W23 deprecation note + BREAKING section",
      "file": "CHANGELOG.md",
      "line": 162,
      "confidence": 0.95,
      "source": "manual"
    }
  ]
}