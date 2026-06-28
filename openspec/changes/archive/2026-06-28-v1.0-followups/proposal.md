<!-- proposal.md: v1.0-followups. Source: sdd-propose sub-agent. -->
# Proposal: v1.0-followups

```yaml
status: success
confidence: high
open_questions_count: 0  # All 6 OQs resolved per explore + orchestrator pre-decisions
chained_pr_recommendation: no  # Single PR; ~350 LOC well under 400 chained-PR threshold
wall_time_estimate: ~2h end-to-end
forecast_loc: 100 prod + 250 tests = 350 total
pr_split: single PR (~350 LOC delta; well under 400 LOC chained-PR threshold)
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v1.0-followups\proposal.md
next_recommended: sdd-design v1.0-followups
strict_tdd: true
chain_strategy: not_applicable
```

## Intent

`flow-engineering v0.9.0` (change #9 `v0.9.0-hardening`, shipped 2026-06-28 per HEAD `3de7783`) closed the v0.8.0 1-release compat-shim window for the `decision-drift` dataclass shape. The v0.8.0 verify-report flagged **2 SUGGESTION findings** (`S1` JSONL wire-format `decision_id: str` vs Python `Finding.decision_id: int` inconsistency + `S2` `flow drift` read-side CLI deferred) that are explicitly **deferred to v1.0** per capability spec `openspec/specs/decision-drift/spec.md:408+410` (the v1.0 planning note). This change executes that v1.0 commitment: closes the JSONL wire-format inconsistency + ships the read-side CLI operators have been asking for since v0.8.0.

The 2 SUGGESTIONs are well-bounded, low-risk, and the work is heavily precedented:

- `S1` is a 1-field type flip (`str` → `int`) on `DriftEvent.decision_id` + a coercion removal at `daemon.py:60` + a defensive `try/except` guard in `DriftEventLog.read_all()` for old `str` lines. Mirrors the v0.8.0 → v0.9.0 soft-migration pattern at `decision_drift.py:84-90` (`Finding.__post_init__` enforcement).
- `S2` is a new top-level Click command group `flow drift-events {list,tail,stats}` with 3 subcommands + the standard observability-style flag set. Mirrors the `flow metrics {summary,export,aggregate}` subcommand-group precedent from `observability` PR#2 (`openspec/changes/archive/2026-06-27-observability-pr2/verify-report-pr2.md:124-148` W1). Path B (parallel command) is recommended to preserve the existing `flow drift <change>` callers; Path A (subcommand group `flow drift check <change>` + `flow drift events ...`) is the BREAKING alternative flagged for orchestrator override.

The HEAD at `8b02d38` has **1233 / 1233 tests passing** (verified at `openspec/specs/decision-drift/spec.md:57` baseline claim — re-verify will gate the archive). Strict TDD is ON; the change follows `work-unit-commits` discipline (each commit ≤30 LOC delta; the proposed S1 batch is ~30 LOC, the S2 batch is ~150 LOC, the tech-debt batch is ~15 LOC). Total scope: **~100 prod LOC + ~250 test LOC = ~350 total** — well under the 400 LOC chained-PR threshold; single PR is the right granularity.

**Why now**: v0.9.0 shipped 1 day ago (HEAD `3de7783` → `8b02d38` is 12 commits of doc/version/ruff cleanup). The capability spec v1.0 planning note is committed (`spec.md:408+410`); the v0.8.0 verify-report's S1+S2 are explicit; the v0.9.0 verify-report's S3 (12 mypy residuals in `decision_drift.py`) and the 3 `# type: ignore[arg-type]` cleanup sites at `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439` (per capability spec `spec.md:410` "S3 mypy annotations") are all queued for v1.0 tech-debt closure. Every release cycle that ships without closing these items erodes the spec-vs-impl trust the capability spec is building. **v1.0 closes the SUGGESTIONs + the tech-debt residuals in a single focused release**.

The headline deliverable is **4 REQs** (S1 wire-format flip + S2 read-side CLI list + S2 tail+stats subcommands + tech-debt residuals). The secondary deliverable is the **CHANGELOG v1.0 entry** with the wire-format migration `sed` + the `--since/--until/--change/--event-class/--limit/--format` flag surface. v1.0 is intentionally NOT a feature release — it's the **last "debt closure" release** before the project enters the v1.x feature cycle.

## Context (from explore)

Explored in [`explore.md`](./explore.md). The exploration confirmed:

- **S1 (`DriftEvent.decision_id` type flip)**: `DriftEvent.decision_id: str` lives at `src/flow_engineering/drift_event_log.py:46`; `str(finding.decision_id)` coercion lives at `src/flow_engineering/daemon.py:60`; `DriftEventLog.read_all()` defensive guard at `src/flow_engineering/drift_event_log.py:95-119` is the place for the legacy `str` skip logic (the actual helper is `read_all()` — NOT `iter_drift_events()` as the drift-hardening verify-report.md:296 says; the verify-report's name is stale; this proposal uses the real symbol name per the explore.md R4 risk).
- **S2 (`flow drift` read-side CLI)**: `flow drift <change>` is a single `@main.command()` (NOT a group) at `src/flow_engineering/cli.py:1712-1809`; `DriftEventLog.read_all()` exists and is fully tested at `tests/unit/test_drift_event_log.py`; the helper just reads the whole file (no `since` / `change` / `event_class` filters — those land in v1.0).
- **Tech-debt residuals**: 12 mypy residuals at `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439` (per capability spec `spec.md:410` "S3 mypy annotations") are within the expected band for `__post_init__` TypeError-on-str enforcement sites; clean to `# type: ignore[arg-type]` in v1.0.

**Total scope**: ~100 prod LOC + ~250 test LOC = ~350 total. Single PR, well under the 400 LOC chained-PR threshold. Strict TDD per `work-unit-commits` (10-15 commits across 4 batches; each commit ≤30 LOC delta).

### Carry-forwards resolved by this change

| Source | Item | Resolution |
|---|---|---|
| `drift-hardening` verify-report #296 S1 | `DriftEvent.decision_id: str` (JSONL wire format) vs `Finding.decision_id: int` (Python) inconsistency | REQ-V1.0.1 — flip `DriftEvent.decision_id: int` + remove `str(finding.decision_id)` coercion at `daemon.py:60` + add defensive `try/except` guard in `DriftEventLog.read_all()` for legacy `str` lines |
| `drift-hardening` verify-report #296 S2 | `flow drift events` read-side CLI deferred to v1.0 | REQ-V1.0.2 — new `flow drift-events list` subcommand (Path B parallel-command) with `--since` / `--until` / `--change` / `--event-class` / `--limit` / `--format=text|json|prometheus|csv` flags |
| `drift-hardening` verify-report #296 S2 | read-side CLI: `tail` + `stats` subcommands | REQ-V1.0.3 — `flow drift-events tail --limit=N` (default 10) + `flow drift-events stats --change/--since/--until/--format` (per-event-class counts + per-change counts + per-decision-id top-N) |
| capability spec `spec.md:410` S3 | 12 mypy residuals in `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439` | REQ-V1.0.4 — add `# type: ignore[arg-type]` to the 12 sites (the `__post_init__` enforcement makes the ignore intentional) + CHANGELOG v1.0 entry + capability spec `## Drift event log JSONL schema` section (REQ-V1.0.1 docs) |

### Carry-forwards explicitly NOT touched by this change (deferred)

| Source | Item | Deferral target | Notes |
|---|---|---|---|
| `drift-hardening` verify-report #242 W7 | `DriftEventLog` JSONL rotation (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var + auto-rotation at threshold) | v1.1 | The v0.8.0 10 MB hardcoded rotation never landed; deferred to v1.1 alongside `metrics.jsonl` rotation (REQ-44 deferred) per capability spec `spec.md:410` "DriftEventLog rotation (v1.1 alongside metrics rotation)" |
| v0.9.0 capability spec + drift-hardening design D5 | `flow drift-events` Path A subcommand group rename (BREAKING) | v1.2+ (revisit only if `flow drift` namespace grows further) | Path A is more idiomatic with `flow metrics {summary,export,aggregate}` but BREAKING; Path B is non-breaking; v1.0 ships Path B |
| v0.9.0 capability spec REQ-51 | `prompt_renders.jsonl` sink (separate from `drift_events.jsonl`) | v1.1 | Independent of drift events; the prompt-render audit trail is its own REQ |
| v0.9.0 capability spec REQ-52 | `flow prompt-events` observability counters (analog to `flow metrics --domain=drift`) | v1.1 | Pair with REQ-51 |
| v0.9.0 capability spec REQ-53 | `docs/prompts.md` auto-generated from prompt registry | v1.1 | Pair with REQ-51/52 |

## Approach (proposed)

### Approach matrix

| Approach | LOC forecast | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A — Single PR, per-task TDD, 4 sequential batches** (S1 → S2a list → S2b tail+stats → tech-debt) | ~100 prod + ~250 test = ~350 total | Bundles the 2 SUGGESTIONs + the 12-site mypy cleanup into one logical v1.0 release; single CHANGELOG entry; one migration guide for operators; small enough to keep review focus; matches v0.9.0-hardening's 3-sub-batch precedent | Per-task TDD means ~10-15 commits (vs ~3 for per-group) | **RECOMMENDED** |
| B — Per-REQ micro-changes (4 separate tiny PRs) | ~80-100 each = ~350 split | Smallest possible review unit (~80-100 LOC each); incremental delivery | 4 PRs of small churn; high overhead (CI ×4, review ×4, archive ×4); one CHANGELOG v1.0 entry split across 4 PRs is operator-hostile; the 12-site mypy cleanup has to ship with the CHANGELOG anyway | Rejected |
| C — Per-group TDD (4 sub-batches = 4 commits) | ~350 in 4 commits | Fewer commits (4 vs 10-15); faster review | Per-group TDD hides silent regressions: if S1 wire-format flip breaks a test site, the S2 CLI commit can't bisect it; the v0.9.0-hardening per-task TDD discipline caught 3 design deviations (W1/W2/W3) via the "shim-still-exists" RED-before-GREEN pattern | Rejected |

**Recommendation: Approach A.** The wire-format flip (S1) is a BREAKING change to the JSONL contract; the read-side CLI (S2) introduces a new command surface; both are independently testable and benefit from per-task TDD discipline. The 10-15 commit target is manageable (each commit ≤30 LOC delta) and matches the `work-unit-commits` skill precedent used by `drift-hardening` + `v0.9.0-hardening`.

### Path A vs Path B for S2 (trade-off explicit)

The exploration (`explore.md:69-72`) identifies two paths for the S2 read-side CLI:

- **Path A (BREAKING — subcommand group)**: convert `cli.py:1712 @main.command() def drift(...)` to `@main.group(name="drift") def drift_group()` + add `@drift_group.command(name="check") def drift_check(...)` (the renamed scan) + `@drift_group.command(name="events") def drift_events(...)`. Operators migrate from `flow drift <change>` → `flow drift check <change>` (1-line `sed` in CHANGELOG v1.0). Cleaner long-term, more idiomatic with `flow metrics {summary,export,aggregate}` group pattern, but **BREAKING** for every existing `flow drift <change>` caller (operators, CI pipelines, hooks).
- **Path B (NON-BREAKING — parallel command)**: keep `@main.command() def drift(...)` as-is for `flow drift <change>`. Add `@main.group(name="drift-events") def drift_events_group()` (the parallel command) with `list|tail|stats` subcommands. **Zero breakage** for existing callers; slightly less elegant than the `flow metrics` group pattern; document the parallel-namespace rationale in CHANGELOG v1.0 entry.

**Orchestrator pre-decision: Path B** (per task brief). **Trade-off**: Path A is more idiomatic with the `flow metrics` group precedent but BREAKING; Path B is non-breaking but parallel-namespace. The orchestrator should override only if the operator-UX continuity is judged less important than the namespace consistency.

### Architecture (Approach A)

4 sequential batches of strict per-task TDD, 10-15 work-unit commits total:

**Sub-batch 1 (S1 — `DriftEvent.decision_id` wire-format flip)** — REQ-V1.0.1

- Task V1.0.1.1: Write RED test `test_drift_event_decision_id_is_int` —
  asserts `DriftEvent(decision_id=42, ...)` constructs with int (current
  type annotation says `str` → would fail; baseline 1233/1233 must
  still pass at the start of this task)
- Task V1.0.1.2: GREEN — change `drift_event_log.py:46` annotation
  `decision_id: str` → `decision_id: int`; update `to_json_dict()` to
  emit int (key still `"decision_id"`, value type changes)
- Task V1.0.1.3: Update `daemon.py:60` — remove `str(finding.decision_id)`
  coercion (now passes `finding.decision_id: int` directly); update the
  docstring at `daemon.py:46-51` to drop the "Future v1 follow-up may
  flip..." note (now done in v1.0)
- Task V1.0.1.4: Add defensive `try/except (TypeError, ValueError)` guard
  in `DriftEventLog.read_all()` at `drift_event_log.py:95-119` — when
  `decision_id` parses as `str` (legacy wire format), coerce to `int`
  with a stderr WARN line (one-time per process via a module-level
  flag; mirrors the `_write_back_findings` skip-warn cadence per
  `cli.py:1703-1709` D8 precedent)
- Task V1.0.1.5: Migrate 1 test site in `test_drift_event_log.py` that
  constructs `DriftEvent(decision_id="42", ...)` → `DriftEvent(decision_id=42, ...)`
  (legacy fixture for the soft-compat shim; canary for the flip)
- Task V1.0.1.6: Add `## Drift event log JSONL schema` section to
  `openspec/specs/decision-drift/spec.md` documenting the v1.0 wire
  format verbatim: `{change, decision_id: int, binding_id, class, detected_at}`
  (key order stable from v0.8.0; `decision_id` type changes from `str` → `int`)

**Sub-batch 2 (S2a — `flow drift-events list` subcommand)** — REQ-V1.0.2

- Task V1.0.2.1: Write RED test
  `test_drift_events_list_filters_since_until_change_event_class_limit` —
  asserts the `list` subcommand filters by `--since/--until/--change/
  --event-class/--limit` and emits 4 formats (`text`/`json`/
  `prometheus`/`csv`)
- Task V1.0.2.2: GREEN — add `flow_drift_events_list` Click command to
  `src/flow_engineering/cli.py` (parallel to `@main.command() def drift(...)`):
  - `@main.group(name="drift-events") def drift_events_group()`
  - `@drift_events_group.command(name="list") def drift_events_list(...)`
  - Flags: `--since=<iso>`, `--until=<iso>`, `--change=<name>`,
    `--event-class=<LABEL_DRIFT|...>`, `--limit=<N>`, `--format=<text|json|prometheus|csv>`,
    `--path=<alt-log>`
  - Default text format = fixed-width table (mirrors `flow drift <change>` at
    `cli.py:1807 _render_drift_table` + `flow metrics summary` at
    `cli.py:977`); `--format=json` mirrors `flow drift <change> --json` at
    `cli.py:1798-1805`; `--format=prometheus` mirrors `flow metrics export
    --format=prometheus` (textfile exposition with `# HELP`/`# TYPE`/
    `# EOF` per design D6)
- Task V1.0.2.3: Add 1-line `--since` parse error path → exit 2
  (mirrors `cli.py:1754-1757` for `flow drift <change>`); add 1-line
  malformed JSONL guard → exit 3 (mirrors D9 exit-code convention)
- Task V1.0.2.4: BDD scenario `tests/bdd/req_v100_drift_events_list.feature`
  with 4 scenarios (text default, `--format=json`, `--format=prometheus`,
  filters compose); step glue in
  `tests/bdd/test_req_v100_drift_events_list_steps.py`

**Sub-batch 3 (S2b — `flow drift-events tail` + `stats` subcommands)** — REQ-V1.0.3

- Task V1.0.3.1: Write RED test
  `test_drift_events_tail_limit_default_change_event_class_format` —
  asserts default `--limit=10`, `--change` + `--event-class` filters,
  text + json formats
- Task V1.0.3.2: GREEN — add `@drift_events_group.command(name="tail")
  def drift_events_tail(...)` with `--limit=<N>=10`, `--change`,
  `--event-class`, `--format` flags; renders rows newest-first
  (mirrors `tail -n` shell convention)
- Task V1.0.3.3: Write RED test
  `test_drift_events_stats_per_event_class_per_change_per_decision_id_top_n` —
  asserts per-event-class counts + per-change counts + per-decision-id
  top-N counts in a fixed-width table
- Task V1.0.3.4: GREEN — add `@drift_events_group.command(name="stats")
  def drift_events_stats(...)` with `--change`, `--since`, `--until`,
  `--format` flags; renders aligned text table per `format_percentile_report`
  at `observability.py:1199-1265` precedent
- Task V1.0.3.5: BDD scenarios for `tail` + `stats` (2 + 2 = 4 scenarios
  total) in `tests/bdd/req_v100_drift_events_tail_stats.feature` + step
  glue in `tests/bdd/test_req_v100_drift_events_tail_stats_steps.py`

**Sub-batch 4 (Tech-debt + CHANGELOG + spec docs)** — REQ-V1.0.4

- Task V1.0.4.1: Write RED test
  `test_drift_events_read_all_legacy_str_decision_id_silently_coerced` —
  asserts old `decision_id: "42"` JSONL line reads back as
  `decision_id=42` (int) with a stderr WARN (one-time per process)
- Task V1.0.4.2: GREEN — finalize the defensive guard from
  V1.0.1.4 (one-time WARN cadence, exit-cleanly on full corruption)
- Task V1.0.4.3: Add `# type: ignore[arg-type]` to the 12 mypy
  residual sites at `decision_drift.py:127/161/203/252/253/262/278/
  372/375/310/411/439` (the `Finding.__post_init__` TypeError-on-str
  enforcement sites; the ignore is intentional and matches the W1
  recommended fix precedent from `v0.9.0-hardening/proposal.md:V9.2.8`)
- Task V1.0.4.4: `pyproject.toml` version bump `0.9.0` → `1.0.0` (line 3)
- Task V1.0.4.5: CHANGELOG v1.0 entry under `## [1.0.0] - 2026-06-XX` —
  `### Changed` (BREAKING JSONL wire format) + `### Added`
  (`flow drift-events {list,tail,stats}`) + `### Migration` (1-line
  `sed` for JSONL: `sed -i 's/"decision_id": "\([0-9]*\)"/"decision_id": \1/g' ~/.flow-engineering/drift_events.jsonl`)
- Task V1.0.4.6: Update 6 SKILL.md runtime files
  (`sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md`) at
  `~/.config/opencode/skills/` with the v1.0 API note (per
  `verify-report.md:81` precedent — `--allow-empty` commit pattern)

### CLI surface

```text
# EXISTING (unchanged)
flow drift <change_name> [--json|--include-obsolete|--write-back|
                        --since|--graph-json|--snapshot=<snap_id>]

# NEW (v1.0)
flow drift-events list   [--since=<iso>] [--until=<iso>]
                         [--change=<name>] [--event-class=<STILL_VALID|LABEL_DRIFT|...>]
                         [--limit=<N>] [--format=<text|json|prometheus|csv>]
                         [--path=<alt-log>]
flow drift-events tail   [--limit=<N>=10] [--change=<name>]
                         [--event-class=<...>] [--format=<text|json>]
flow drift-events stats  [--change=<name>] [--since=<iso>] [--until=<iso>]
                         [--format=<text|json>]
```

Flags modeled after `flow metrics {summary,export,aggregate}` so the
operator mental model transfers (mirrors the
`openspec/changes/archive/2026-06-27-observability-pr2/verify-report-pr2.md:124-148`
W1 subcommand-group precedent). Exit codes mirror D9 (0=success,
2=invalid args, 3=malformed JSONL).

### Code sketch — REQ-V1.0.1 (S1 wire-format flip)

```python
# src/flow_engineering/drift_event_log.py (MODIFY — ~10 LOC delta)
# REQ-V1.0.1: DriftEvent.decision_id is now int (was str).
# The wire format on disk is now: {"decision_id": 42, ...} (int).
# Legacy str lines (pre-v1.0) are silently coerced in read_all() with a
# one-time stderr WARN per process.
from __future__ import annotations
import json
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DriftEvent:
    change: str
    decision_id: int          # was: str (v0.8.0/v0.9.0); v1.0 flips to int
    binding_id: str
    event_class: str
    detected_at: float

    def to_json_dict(self) -> dict[str, Any]:
        """Return the JSON wire dict with the spec schema (class key)."""
        return {
            "change": self.change,
            "decision_id": self.decision_id,
            "binding_id": self.binding_id,
            "class": self.event_class,
            "detected_at": self.detected_at,
        }


class DriftEventLog:
    """Append-only JSONL writer with in-process thread safety (D11)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = (path or DEFAULT_DRIFT_EVENT_LOG_PATH)
        self._lock = threading.Lock()
        self._legacy_warn_emitted = False  # REQ-V1.0.1: one-time WARN per process

    def read_all(self) -> list[DriftEvent]:
        """Return all events from the JSONL file in append order.

        Missing file returns ``[]``; malformed lines are silently
        skipped (the sink is best-effort — partial writes on disk
        full must NOT crash the caller).

        REQ-V1.0.1: legacy ``decision_id: "42"`` (str) lines are coerced
        to ``int`` with a one-time stderr WARN per process (mirrors the
        ``_write_back_findings`` skip-warn cadence per D8). Operators
        migrate via the 1-line ``sed`` in CHANGELOG v1.0.
        """
        if not self.path.exists():
            return []
        events: list[DriftEvent] = []
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
                if "class" in data and "event_class" not in data:
                    data["event_class"] = data.pop("class")
                # REQ-V1.0.1: defensive coercion for legacy str decision_id.
                if isinstance(data.get("decision_id"), str):
                    data["decision_id"] = int(data["decision_id"])
                    if not self._legacy_warn_emitted:
                        print(
                            f"warning: legacy str decision_id in "
                            f"{self.path}; coercing to int. Run the "
                            f"CHANGELOG v1.0 sed migration to silence.",
                            file=sys.stderr,
                        )
                        self._legacy_warn_emitted = True
                events.append(DriftEvent(**data))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return events
```

### Code sketch — REQ-V1.0.2 + REQ-V1.0.3 (S2 read-side CLI)

```python
# src/flow_engineering/cli.py (MODIFY — ~80 LOC delta)
# REQ-V1.0.2 + REQ-V1.0.3: NEW flow drift-events {list,tail,stats} subcommand group.
# Path B (parallel command; preserves `flow drift <change>` callers).
# Mirrors the `flow metrics {summary,export,aggregate}` subcommand-group
# precedent from observability PR#2 (verify-report-pr2.md:124-148 W1).
from __future__ import annotations
import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path
import click
from flow_engineering import drift_event_log as delog
from flow_engineering.cli import main, EXIT_OK, EXIT_INVALID_VALUE, EXIT_MALFORMED


@main.group(name="drift-events")
def drift_events_group() -> None:
    """Read drift events from ~/.flow-engineering/drift_events.jsonl (REQ-V1.0.2 + REQ-V1.0.3).

    Path B (parallel command — preserves the `flow drift <change>`
    surface). Subcommands: list, tail, stats. Mirrors `flow metrics
    {summary,export,aggregate}` flag set so the operator mental model
    transfers.
    """


@drift_events_group.command(name="list")
@click.option("--since", default=None, help="Filter events with detected_at >= <iso>.")
@click.option("--until", default=None, help="Filter events with detected_at <= <iso>.")
@click.option("--change", default=None, help="Filter events for a specific change name.")
@click.option("--event-class", default=None, help="Filter events by drift class (e.g. LABEL_DRIFT).")
@click.option("--limit", type=int, default=None, help="Cap the number of returned events.")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json", "prometheus", "csv"]),
              help="Output format (default: text).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path (default: ~/.flow-engineering/drift_events.jsonl).")
def drift_events_list(since, until, change, event_class, limit, fmt, log_path) -> None:
    """List drift events with optional filters (REQ-V1.0.2)."""
    log = delog.DriftEventLog(path=log_path) if log_path else delog.DriftEventLog()
    try:
        events = log.read_all()
    except OSError as exc:
        click.echo(json.dumps({"error": "log_read_failed", "detail": str(exc)}), err=True)
        sys.exit(EXIT_MALFORMED)
    # Apply filters; render by format; exit per D9 (0=success, 2=invalid, 3=malformed).
    ...


@drift_events_group.command(name="tail")
@click.option("--limit", type=int, default=10, help="Number of events to show (default: 10).")
@click.option("--change", default=None, help="Filter events for a specific change name.")
@click.option("--event-class", default=None, help="Filter events by drift class.")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def drift_events_tail(limit, change, event_class, fmt) -> None:
    """Show the last N drift events newest-first (REQ-V1.0.3)."""
    ...


@drift_events_group.command(name="stats")
@click.option("--change", default=None, help="Stats for a specific change name.")
@click.option("--since", default=None, help="Stats for events with detected_at >= <iso>.")
@click.option("--until", default=None, help="Stats for events with detected_at <= <iso>.")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def drift_events_stats(change, since, until, fmt) -> None:
    """Per-event-class + per-change + per-decision-id counts (REQ-V1.0.3)."""
    ...
```

### Dependencies

- **NO new runtime dependencies.** The change is a type annotation flip
  + a defensive read guard + a new Click subcommand group. Click +
  stdlib `json` + `csv` + `datetime` already cover everything.
- `_legacy_warn_emitted` flag is a per-instance `bool` (NOT
  process-global) so the WARN is per-log-file, which is the right
  cadence for a multi-log CLI invocation.

### What changes (scope)

**In scope (single PR, 4 sub-batches)**:

- **Sub-batch 1 (S1, ~3 commits)**:
  - `src/flow_engineering/drift_event_log.py` (MODIFY): `decision_id: str` → `int` at line 46; `_legacy_warn_emitted` flag + defensive `try/except` in `read_all()` at lines 95-119 (~5 prod LOC).
  - `src/flow_engineering/daemon.py` (MODIFY): remove `str(finding.decision_id)` coercion at line 60; update docstring at lines 46-51 (~3 prod LOC delta).
  - `tests/unit/test_drift_event_log.py` (MODIFY): 1 str-input fixture migrated to int + 2 NEW tests for the legacy coercion guard (~15 test LOC delta).
  - `openspec/specs/decision-drift/spec.md` (MODIFY): add `## Drift event log JSONL schema` section documenting the v1.0 wire format (~15 docs LOC).
  - KEEP 1 silent-skip test for corrupted lines (no behavior change for malformed JSON).

- **Sub-batch 2 (S2a, ~3 commits)**:
  - `src/flow_engineering/cli.py` (MODIFY): NEW `@main.group(name="drift-events")` + `drift_events_list` subcommand with 7 flags + 4 format handlers (~50 prod LOC).
  - `tests/unit/test_cli_drift_events_list.py` (NEW): ~15 unit tests for filter + format + exit-code paths (~80 test LOC).
  - `tests/bdd/req_v100_drift_events_list.feature` (NEW): 4 BDD scenarios in business-domain Given/When/Then phrasing (~30 LOC).
  - `tests/bdd/test_req_v100_drift_events_list_steps.py` (NEW): step glue (~30 LOC).

- **Sub-batch 3 (S2b, ~3 commits)**:
  - `src/flow_engineering/cli.py` (MODIFY): NEW `drift_events_tail` + `drift_events_stats` subcommands (~30 prod LOC).
  - `tests/unit/test_cli_drift_events_tail.py` (NEW) + `test_cli_drift_events_stats.py` (NEW): ~10 unit tests each (~50 test LOC each = 100 total).
  - `tests/bdd/req_v100_drift_events_tail_stats.feature` (NEW): 4 BDD scenarios + step glue (~50 LOC).

- **Sub-batch 4 (Tech-debt + docs, ~3 commits)**:
  - `src/flow_engineering/decision_drift.py` (MODIFY): add `# type: ignore[arg-type]` to 12 mypy residual sites at lines 127/161/203/252/253/262/278/372/375/310/411/439 (~12 prod LOC; 1 comment per site).
  - `pyproject.toml` (MODIFY): `version = "1.0.0"` (line 3).
  - `CHANGELOG.md` (MODIFY): v1.0 entry under `## [1.0.0] - 2026-06-XX` with `### Changed` (BREAKING JSONL wire format) + `### Added` (`flow drift-events {list,tail,stats}`) + `### Migration` (1-line `sed`).
  - `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` (MODIFY): update the v0.9.0 API note to v1.0 — add the `flow drift-events` CLI surface; mark JSONL wire format as int (~30 docs LOC across 6 files).

**Out of scope (deferred to v1.1+)**:

- `DriftEventLog` rotation (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var + auto-rotation at threshold) — DEFERRED to v1.1 alongside `metrics.jsonl` rotation (REQ-44 deferred) per capability spec `spec.md:410` "DriftEventLog rotation (v1.1 alongside metrics rotation)".
- Cross-project federation for drift events (`flow drift-events --project=<key>` filter) — DEFERRED to a separate `federated-drift-events` follow-up change.
- OpenTelemetry OTLP push for drift events — DEFERRED; Prometheus textfile from REQ-38 already covers the v1 use case.
- `flow drift <change> --drift-event-log[=<path>]` per-finding class filter — DEFERRED; v0.8.0+ persists all non-still-valid findings by default.
- `flow drift-events` Path A subcommand group rename (BREAKING) — DEFERRED; revisit only if the `flow drift` namespace grows further in v1.2+.
- REQ-51 (prompt_renders.jsonl sink) + REQ-52 (prompt observability counters) + REQ-53 (docs/prompts.md auto-generated) — DEFERRED to v1.1 per capability spec `spec.md:410`.

### Public API surface (MODIFIED)

```python
# src/flow_engineering/drift_event_log.py — MODIFIED in v1.0
@dataclass(frozen=True)
class DriftEvent:
    change: str
    decision_id: int                                  # CHANGED — was str
    binding_id: str
    event_class: str
    detected_at: float
    def to_json_dict(self) -> dict[str, Any]: ...     # emits int decision_id


class DriftEventLog:
    def __init__(self, path: Path | None = None) -> None: ...
    def append(self, event: DriftEvent) -> None: ...
    def read_all(self) -> list[DriftEvent]: ...       # MODIFIED — defensive str→int coercion with one-time WARN


# src/flow_engineering/daemon.py — MODIFIED in v1.0
def _append_drift_events(report: DriftReport, *, path: Path | None = None) -> None:
    # REMOVED — str(finding.decision_id) coercion; finding.decision_id is int
    # and DriftEvent.decision_id is int; direct assignment.
    ...


# src/flow_engineering/cli.py — NEW in v1.0
@main.group(name="drift-events")
def drift_events_group() -> None: ...

@drift_events_group.command(name="list")
def drift_events_list(since, until, change, event_class, limit, fmt, log_path) -> None: ...

@drift_events_group.command(name="tail")
def drift_events_tail(limit, change, event_class, fmt) -> None: ...

@drift_events_group.command(name="stats")
def drift_events_stats(change, since, until, fmt) -> None: ...
```

### Breaking-change policy (REQ-V1.0.1 only)

The JSONL wire-format `decision_id: int` flip is a public contract change for any consumer parsing `~/.flow-engineering/drift_events.jsonl` (jq scripts, dashboards, custom analytics). Mitigation:

- **Defensive read guard** in `DriftEventLog.read_all()` — old `str` lines coerce to `int` with a one-time stderr WARN per process. **Zero data loss**; pre-v1.0 JSONL files continue to be readable without migration.
- **1-line `sed` migration in CHANGELOG v1.0** — operators who want to convert in-place:
  ```bash
  sed -i 's/"decision_id": "\([0-9]*\)"/"decision_id": \1/g' \
    ~/.flow-engineering/drift_events.jsonl
  ```
  (Mirrors the W23 `snapshot_pruned_total` → `snapshot_prune_total` precedent from `drift-hardening/design.md`.)

The Python `decision_drift.Finding.decision_id: int` contract is **unchanged** from v0.9.0 (the v0.9.0 `Finding.__post_init__` already enforces int via `TypeError`). The wire-format change is **internal to DriftEvent serialization** — it does NOT affect the `flow drift <change>` CLI output, the `flow drift --json` envelope, or the Engram metadata write-back path.

### Non-breaking guarantees

- `flow drift <change>` exit-code semantics unchanged (0 still-valid / 1 stale / 2 unable_to_verify / 3 usage error per REQ-11).
- `flow drift <change> --json` envelope byte-identical (the `decision_id` in the JSON output is the `Finding.decision_id: int` from the in-memory dataclass, which has been int since v0.9.0).
- `flow watch --drift` daemon JSONL append behavior preserved (still writes 1 line per non-STILL_VALID finding; just with int `decision_id` now).
- `DriftEventLog.read_all()` returns identical `DriftEvent` objects for new-format JSONL; old-format JSONL returns identical `DriftEvent` objects after the defensive coercion (with the WARN).
- All existing 1233 tests pass — verified locally before PR open.
- `_legacy_warn_emitted` flag is per-instance (per-log-path), so multiple invocations on different log files each get their own WARN (correct cadence for multi-log CLI invocation).

## Open Questions

**All resolved per explore + orchestrator pre-decisions.**

| # | Question | Decision | Resolution |
|---|---|---|---|
| OQ-1 | S1: `DriftEvent.decision_id` type? | **Option A** (orchestrator pre-decided) | Flip to `int` (matches `Finding.decision_id` post-v0.9.0 hard break; matches capability spec v1.0 plan at `spec.md:408+410`; aligns with W8 design direction). |
| OQ-2 | S1: read-side compat shim for old `str` JSONL lines? | **YES — defensive guard** (orchestrator pre-decided) | Add `try: int(data["decision_id"]) except (TypeError, ValueError): skip` guard in `DriftEventLog.read_all()` (mirrors the v0.8.0 → v0.9.0 soft-migration pattern at `decision_drift.py:84-90`). Old `drift_events.<stamp>.jsonl` files remain readable without migration. **One-time stderr WARN per process per log-path** (per-instance flag, NOT module-global; mirrors `_write_back_findings` skip-warn cadence per `cli.py:1703-1709` D8 precedent). |
| OQ-3 | S1: migration guide for existing JSONL consumers? | **YES — 1-line `sed` in CHANGELOG v1.0** | `sed -i 's/"decision_id": "\([0-9]*\)"/"decision_id": \1/g' ~/.flow-engineering/drift_events.jsonl` (mirrors the W23 `snapshot_pruned_total` → `snapshot_prune_total` precedent from `drift-hardening/design.md`). |
| OQ-4 | S2: subcommand group vs parallel command? | **Path B** (orchestrator pre-decided; Path A flagged) | Parallel command `flow drift-events {list,tail,stats}` (NON-BREAKING; preserves `flow drift <change>` callers; slightly less elegant than the `flow metrics` group pattern). Path A (BREAKING `flow drift check <change>` rename) is the alternative if the orchestrator overrides. **Trade-off explicitly flagged**: Path A is more idiomatic with `flow metrics {summary,export,aggregate}` but BREAKING; Path B is non-breaking but parallel-namespace. Document the parallel-namespace rationale in CHANGELOG v1.0. |
| OQ-5 | S2: which subcommands? | **`list` + `tail` + `stats`** (per explore OQ-5) | `list` (with `--since`/`--until`/`--change`/`--event-class`/`--limit` filters + 4 formats) + `tail` (last N events, default 10, newest-first) + `stats` (per-event-class + per-change + per-decision-id counts in a fixed-width table; `--format=json` for machine-readable). Mirrors `flow metrics {summary,export,aggregate}` 3-subcommand precedent. |
| OQ-6 | S2: `--format=prometheus\|csv` for events? | **YES** (capability spec pre-decided) | Landing in v1.0 per capability spec roadmap at `spec.md:408+410` + v0.9.0-hardening tasks.md:159. Add `--format=text\|json\|prometheus\|csv` to `flow drift-events list`. |

**OQ count: 0 open** (all 6 pre-resolved per orchestrator + explore + this proposal).

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `src/flow_engineering/drift_event_log.py` | MODIFY | REQ-V1.0.1 — `decision_id: str` → `int` at line 46 (~1 LOC); `_legacy_warn_emitted` per-instance flag + defensive str→int coercion + stderr WARN in `read_all()` at lines 95-119 (~10 LOC). Net ~10 prod LOC delta. |
| `src/flow_engineering/daemon.py` | MODIFY | REQ-V1.0.1 — remove `str(finding.decision_id)` coercion at line 60; update docstring at lines 46-51 (drop "Future v1 follow-up may flip..." note). Net ~3 prod LOC delta. |
| `src/flow_engineering/cli.py` | NEW | REQ-V1.0.2 + REQ-V1.0.3 — NEW `@main.group(name="drift-events")` + 3 subcommands (`list` / `tail` / `stats`) with the 7/4/4 flag set + 4 format handlers. Net ~80 prod LOC added. |
| `src/flow_engineering/decision_drift.py` | MODIFY | REQ-V1.0.4 — add `# type: ignore[arg-type]` to 12 mypy residual sites at lines 127/161/203/252/253/262/278/372/375/310/411/439. Net +12 prod LOC (1 comment per site). |
| `tests/unit/test_drift_event_log.py` | MODIFY | REQ-V1.0.1 — 1 str-input fixture migrated to int + 2 NEW tests for the legacy coercion guard + 1 NEW test for the one-time WARN cadence. Net ~20 test LOC delta. |
| `tests/unit/test_cli_drift_events_list.py` (NEW) | NEW | REQ-V1.0.2 — ~15 unit tests for filter + format + exit-code paths. Net ~80 test LOC added. |
| `tests/unit/test_cli_drift_events_tail.py` (NEW) | NEW | REQ-V1.0.3 — ~10 unit tests for tail + filter + format. Net ~50 test LOC added. |
| `tests/unit/test_cli_drift_events_stats.py` (NEW) | NEW | REQ-V1.0.3 — ~10 unit tests for stats + filter + format. Net ~50 test LOC added. |
| `tests/bdd/req_v100_drift_events_list.feature` (NEW) | NEW | REQ-V1.0.2 — 4 BDD scenarios in business-domain Given/When/Then phrasing. Net ~30 LOC. |
| `tests/bdd/test_req_v100_drift_events_list_steps.py` (NEW) | NEW | REQ-V1.0.2 — step glue. Net ~30 LOC. |
| `tests/bdd/req_v100_drift_events_tail_stats.feature` (NEW) | NEW | REQ-V1.0.3 — 4 BDD scenarios (2 tail + 2 stats). Net ~30 LOC. |
| `tests/bdd/test_req_v100_drift_events_tail_stats_steps.py` (NEW) | NEW | REQ-V1.0.3 — step glue. Net ~30 LOC. |
| `openspec/specs/decision-drift/spec.md` | MODIFY | REQ-V1.0.1 + REQ-V1.0.4 — add `## Drift event log JSONL schema` section documenting the v1.0 wire format `{change, decision_id: int, binding_id, class, detected_at}` (~15 docs LOC). |
| `CHANGELOG.md` | MODIFY | REQ-V1.0.4 — v1.0 entry under `## [1.0.0] - 2026-06-XX` with `### Changed` (BREAKING JSONL wire format) + `### Added` (`flow drift-events {list,tail,stats}`) + `### Migration` (1-line `sed`). Net ~30 docs LOC added. |
| `pyproject.toml` | MODIFY | REQ-V1.0.4 — `version = "1.0.0"` (line 3). Net +1/-1 LOC. |
| `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` (6 files) | MODIFY | REQ-V1.0.4 — update the v0.9.0 API note to v1.0; add the `flow drift-events` CLI surface; mark JSONL wire format as int. Net ~30 docs LOC delta across 6 files. |

## Capabilities

### Modified Capabilities

- `decision-drift` (REQ-9..16 + REQ-55..59): the JSONL wire format at `~/.flow-engineering/drift_events.jsonl` is upgraded to `decision_id: int` (was `str`); the read-side CLI surface gains `flow drift-events {list,tail,stats}` as a parallel command (Path B, NON-BREAKING for `flow drift <change>`). The capability spec at `openspec/specs/decision-drift/spec.md` is updated with the v1.0 `## Drift event log JSONL schema` section + the new REQ-V1.0.X baseline entries.

**No new capabilities.** v1.0 is the SUGGESTION + tech-debt closure for the `decision-drift` capability; the read-side CLI is a NEW command group within the existing `decision-drift` capability, not a new capability.

## Risks

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | **Silent regression** in `read_all()` defensive guard — a test site passes a legacy `str` decision_id and the coercion silently succeeds instead of raising (or vice versa: the coercion raises on a value that should pass) | LOW | Per-task TDD with RED test before the GREEN impl (V1.0.1.1 + V1.0.4.1); 1 test for happy-path int + 1 test for legacy str coercion + 1 test for one-time WARN cadence; smoke test against a pre-v1.0 JSONL fixture (saved in `tests/fixtures/drift_events_v090_legacy.jsonl`) to verify the read path round-trips |
| 2 | **Wire-format BREAKING** for JSONL consumers — old `cat ~/.flow-engineering/drift_events.jsonl \| jq` consumers that pipe `decision_id` to an int-expecting script now work (good); consumers that compared as string ("42" < "9" lex sort) see behavior change (bad but rare) | LOW | CHANGELOG v1.0 1-line `sed` migration note (Q-3 resolution); defensive read guard in `read_all()` (Q-2 resolution); one-time stderr WARN per process per log-path surfaces the issue to operators on first run |
| 3 | **Path B parallel namespace is less elegant than Path A subcommand group** — `flow drift-events` is a sibling command to `flow drift`, not a subcommand. Inconsistent with `flow metrics {summary,export,aggregate}` group pattern (per `observability` PR#2 W1 precedent) | LOW | Document the parallel-namespace rationale in CHANGELOG v1.0 entry (Path A is BREAKING; Path B preserves operator-UX continuity for `flow drift <change>` callers); revisit Path A in v1.2+ if `flow drift` namespace grows |
| 4 | **Doc drift in `drift-hardening/verify-report.md:296`** — the report says `DriftEventLog.read_all()` helper is named `iter_drift_events()`. **The actual helper is `read_all()`** at `drift_event_log.py:95-119`. The verify-report's name is stale | LOW | Note in the proposal (R4 from explore; this proposal uses the real symbol name `read_all()` per `drift_event_log.py:95-119`); optional post-archive drift-note in archived `verify-report.md:296` (1-line edit; non-blocking) |
| 5 | **12 mypy residuals in `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439`** — within expected band for `__post_init__` TypeError-on-str enforcement sites (per `v0.9.0-hardening` verify-report S3); adding `# type: ignore[arg-type]` is intentional and matches the W1 recommended fix precedent | LOW | REQ-V1.0.4 cleanup adds `# type: ignore[arg-type]` to the 12 sites (1 comment per site; ~12 LOC); matches the v0.9.0-hardening W1 fix precedent at `proposal.md:V9.2.8` (3 sites cleaned) + the `v0.9.0-hardening` 12 residuals carry-forward closure |

**0 CRITICAL / 0 HIGH / 5 LOW risks.** All mitigations are within the proposed REQ scope or already-documented as low-priority follow-ups.

## Rollback Plan

All artifacts are type-flip + new CLI surface + doc updates. Single revert of the merge commit restores pre-v1.0 state:

- `src/flow_engineering/drift_event_log.py` MODIFIED — `decision_id: str` annotation restored; `_legacy_warn_emitted` flag + defensive coercion removed; `read_all()` reverts to the v0.9.0 read path. Reverting restores the v0.9.0 wire format.
- `src/flow_engineering/daemon.py` MODIFIED — `str(finding.decision_id)` coercion re-added at line 60; docstring at lines 46-51 reverts to v0.9.0.
- `src/flow_engineering/cli.py` MODIFIED — `flow drift-events` subcommand group + 3 subcommands removed (revert to v0.9.0 surface). `flow drift <change>` surface unchanged.
- `src/flow_engineering/decision_drift.py` MODIFIED — 12 `# type: ignore[arg-type]` comments removed; the 12 mypy residuals resurface (within v0.9.0 expected band).
- 4 NEW test files + 2 NEW BDD feature files + 2 NEW step-glue files — all DELETED on revert.
- `openspec/specs/decision-drift/spec.md` MODIFIED — v1.0 `## Drift event log JSONL schema` section removed; reverts to v0.9.0 baseline.
- `CHANGELOG.md` + `pyproject.toml` revert cleanly to v0.9.0.
- 6 SKILL.md runtime files revert cleanly to the v0.9.0 API note.

To restore the pre-v1.0 install: `git revert <PR-merge>`. The wire format reverts to `decision_id: str`; the `flow drift-events` subcommand group is gone; the 12 mypy residuals resurface (acceptable; v0.9.0 baseline is the documented state). Zero data loss; zero user state touched.

## Dependencies

- **None new.** The change is a type annotation flip + a defensive read guard + a new Click subcommand group. Click + stdlib `json` + `csv` + `datetime` already cover everything.
- `_legacy_warn_emitted` per-instance flag uses stdlib (no new dep).
- `--format=prometheus` reuses the `prometheus_exposition` module from `observability` PR#2 (REQ-38) at `src/flow_engineering/observability.py:945-983` — already imported via the existing observability CLI integration.
- `drift-hardening` (shipped v0.8.0) — the `DriftEvent` + `DriftEventLog` + `daemon._append_drift_events` foundation that v1.0 builds on.
- `v0.9.0-hardening` (shipped v0.9.0) — the `Finding.decision_id: int` hard break + the `Finding.__post_init__` enforcement that v1.0's wire-format flip aligns with.
- `observability` PR#2 (shipped v0.7.1) — the `prometheus_exposition` module that `flow drift-events list --format=prometheus` reuses.

## Proposed PR Strategy

**Single PR** for v1.0. Total scope: ~100 prod LOC + ~250 test LOC = ~350 total. Well under the 400 LOC chained-PR threshold. The 4 REQs are thematically unified (all are SUGGESTIONs + tech-debt from the v0.8.0 verify-report + the v0.9.0 carry-forwards + the capability spec v1.0 planning note); splitting into chained PRs would force each PR to re-establish the wire-format flip context that the previous PR just landed — needless friction.

**Sub-batches** within the single PR (10-15 commits total, per `work-unit-commits` skill — each commit ≤30 LOC delta):

- Sub-batch 1 (S1, ~3 commits): RED → GREEN wire-format flip → defensive read guard
- Sub-batch 2 (S2a, ~3 commits): RED → GREEN `list` subcommand → BDD scenarios
- Sub-batch 3 (S2b, ~3 commits): RED → GREEN `tail` + `stats` subcommands → BDD scenarios
- Sub-batch 4 (Tech-debt + docs, ~3 commits): mypy cleanup + version bump + CHANGELOG (atomic per the drift-hardening `--allow-empty` precedent) + 6 SKILL.md updates

**Commit template** (mirror v0.9.0-hardening precedent):

```
chore(v1.0-followups): REQ-V1.0.<N> — <concise description>

- RED test: <test file>:<line>
- GREEN impl: <impl file>:<line range>
- Tests: <count> unit / <count> BDD
- Risk: <low|med|high>

Refs: openspec/changes/v1.0-followups/proposal.md#step-<N>
```

## Wall Time Estimate

**~2 hours end-to-end** (single PR, 4 sub-batches of strict per-task TDD):

| Sub-batch | Time | Tasks | Commits |
|---|---|---|---|
| Sub-batch 1 (S1) | ~25 min | 6 tasks (V1.0.1.1..V1.0.1.6) | 3 commits |
| Sub-batch 2 (S2a) | ~30 min | 4 tasks (V1.0.2.1..V1.0.2.4) | 3 commits |
| Sub-batch 3 (S2b) | ~30 min | 5 tasks (V1.0.3.1..V1.0.3.5) | 3 commits |
| Sub-batch 4 (Tech-debt + docs) | ~20 min | 6 tasks (V1.0.4.1..V1.0.4.6) | 3 commits |
| Verify + archive | ~15 min | `sdd-verify` + `sdd-archive` | 1 merge commit |
| **TOTAL** | **~2 hours** | **21 tasks** | **~13 commits** |

**Per-task breakdown**:
- Sub-batch 1: ~4 min/task × 6 tasks = ~24 min
- Sub-batch 2: ~7.5 min/task × 4 tasks = ~30 min
- Sub-batch 3: ~6 min/task × 5 tasks = ~30 min
- Sub-batch 4: ~3.5 min/task × 6 tasks = ~21 min
- Verify: 1 `pytest` run + 1 `ruff` run + 1 `mypy` run + 1 `sdd-verify` pass + 1 `sdd-archive` pass = ~15 min

## Carry-forwards (NOT in v1.0)

### Deferred to v1.1 (per capability spec `spec.md:410` + drift-hardening #242 W7)

- **`DriftEventLog` JSONL rotation policy** (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var + auto-rotation at threshold + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` gzip-and-rotate cron) — DEFERRED to v1.1 alongside `metrics.jsonl` rotation (REQ-44 deferred). The v0.8.0 10 MB hardcoded rotation never landed (drift-hardening W7 at `drift_event_log.py:11-17` module docstring). The v1.0 wire-format flip does NOT include rotation; the file grows unbounded until v1.1.
- **REQ-51**: `prompt_renders.jsonl` sink (separate from `drift_events.jsonl`) — independent of drift events; the prompt-render audit trail is its own REQ.
- **REQ-52**: `flow prompt-events` observability counters (analog to `flow metrics --domain=drift`) — pairs with REQ-51.
- **REQ-53**: `docs/prompts.md` auto-generated from prompt registry — pairs with REQ-51/52.

### Deferred to v1.2+ (revisit only if `flow drift` namespace grows)

- **Path A subcommand group rename** (BREAKING) — `flow drift check <change>` + `flow drift events ...` — more idiomatic with `flow metrics {summary,export,aggregate}` group pattern but BREAKING for every existing `flow drift <change>` caller. Revisit only if the `flow drift` namespace grows further in v1.2+.

### Already RESOLVED (verified closed in v0.9.0)

| Source | Item | Resolution evidence |
|---|---|---|
| `drift-hardening` apply-progress/merged.md line 8 | Strict TDD was ON for v0.8.0 | Engram #243 |
| `drift-hardening` verify-report #135 | W1 + W2 + W3 — compat shims added with 1-release removal commitment | CHANGELOG v0.8.0 lines 43/44/46/74; resolved in v0.9.0-hardening (REQ-V9.1..V9.5) |
| `v0.9.0-hardening` verify-report S3 | 12 mypy residuals in `decision_drift.py` within expected band | REQ-V1.0.4 closes via `# type: ignore[arg-type]` cleanup |

## Success Criteria

- [ ] `DriftEvent.decision_id: int` annotation at `drift_event_log.py:46`
      (REQ-V1.0.1, 1 RED + 1 GREEN test)
- [ ] `DriftEvent(decision_id=42, ...)` constructs successfully
      (REQ-V1.0.1, 1 type-contract smoke)
- [ ] `DriftEventLog.read_all()` defensively coerces legacy `str` `decision_id`
      to `int` with a one-time stderr WARN per log-path
      (REQ-V1.0.1, 1 RED + 1 GREEN test)
- [ ] `daemon._append_drift_events` no longer coerces via `str(finding.decision_id)`
      (REQ-V1.0.1, 1 grep audit)
- [ ] `flow drift-events list --since/--until/--change/--event-class/--limit/
      --format=text|json|prometheus|csv` works for all 4 formats
      (REQ-V1.0.2, 4 BDD scenarios + 15 unit tests)
- [ ] `flow drift-events tail --limit=10` default + `--change/--event-class/
      --format` filters work (REQ-V1.0.3, 2 BDD scenarios + 10 unit tests)
- [ ] `flow drift-events stats --change/--since/--until/--format` renders
      per-event-class + per-change + per-decision-id counts in a fixed-width
      table (REQ-V1.0.3, 2 BDD scenarios + 10 unit tests)
- [ ] All existing 1233 tests pass (no regressions from wire-format flip)
      (1 `pytest` run)
- [ ] `ruff check` clean on changed files (1 `ruff` run)
- [ ] `mypy src/flow_engineering/decision_drift.py` shows ≤5 errors
      (down from 12 baseline; 12-site `# type: ignore[arg-type]` cleanup
      at REQ-V1.0.4) (1 `mypy` run)
- [ ] `openspec/specs/decision-drift/spec.md` `## Drift event log JSONL
      schema` section documents the v1.0 wire format verbatim
      (REQ-V1.0.1 docs, 1 grep audit)
- [ ] CHANGELOG v1.0 entry under `## [1.0.0] - 2026-06-XX` lists
      the JSONL wire-format change + the `flow drift-events` addition +
      the 1-line `sed` migration (REQ-V1.0.4, 1 manual review)
- [ ] `pyproject.toml` `version = "1.0.0"` (REQ-V1.0.4, 1 manual review)
- [ ] 6 SKILL.md runtime files updated atomically — v0.9.0 API note
      replaced with v1.0 (adds `flow drift-events` surface + int JSONL)
      (REQ-V1.0.4, 1 grep audit across
      `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,
      verify,archive}/SKILL.md`)
- [ ] Strict TDD evidence: every public change has RED→GREEN→REFACTOR
      history in commit log; per-commit work-unit splits per
      `work-unit-commits` skill (10-15 commits each ≤30 LOC delta)
- [ ] Drift detector (REQ-9..16) behavior unchanged for end users —
      the JSONL wire format change is internal to `DriftEvent`
      serialization; CLI output + exit codes + Engram metadata
      write-back byte-identical to v0.9.0

## Cross-Impact

| Queued/shipped change | Relationship | Verdict |
|---|---|---|
| `decision-code-linking` (shipped v0.2.0) | Unrelated layer | No conflict |
| `decision-reality-drift` (shipped v0.3.0) | The original `Finding`/`DriftReport`/`classify_binding` API | No conflict (v1.0 only touches `DriftEvent` + the CLI) |
| `vector-semantic-search` (shipped v0.4.0) | Unrelated layer | No conflict |
| `cross-project-federation` (shipped v0.5.0) | Unrelated layer | No conflict |
| `graph-snapshots` (shipped v0.6.0) | Unrelated layer | No conflict |
| `observability` (shipped v0.7.0) | The `prometheus_exposition` module (REQ-38) is reused by `flow drift-events list --format=prometheus`; the `flow metrics` subcommand-group pattern is the precedent for `flow drift-events` | Compatible (reuses + mirrors) |
| `prompt-registry` (shipped v0.8.0 PR#1 + PR#2) | Unrelated layer | No conflict |
| `drift-hardening` (shipped v0.8.0) | The `DriftEvent` + `DriftEventLog` + `daemon._append_drift_events` foundation that v1.0 builds on; the S1+S2 SUGGESTION findings from the verify-report are the trigger for v1.0 | **MIGRATION**: wire-format flip + new CLI surface |
| `v0.9.0-hardening` (shipped v0.9.0) | The `Finding.decision_id: int` hard break + `Finding.__post_init__` enforcement that v1.0's wire-format flip aligns with; the 12 mypy residuals in `decision_drift.py` are closed in REQ-V1.0.4 | **MIGRATION**: wire-format flip + mypy cleanup |

**Unblocks**: 2 SUGGESTIONs (S1 + S2) + 1 tech-debt item (S3 mypy residuals) from `drift-hardening` verify-report closed; v1.0 release ships with 1 BREAKING JSONL wire-format change documented + 1-line `sed` migration guide + new `flow drift-events {list,tail,stats}` read-side CLI surface; the capability spec v1.0 planning note at `spec.md:408+410` is honored; the 12 mypy residuals carry-forward from v0.9.0 is closed.

**Constrains**: any future change that touches the JSONL wire format MUST NOT re-introduce `str` `decision_id` (the v1.0 design is a hard break with explicit defensive read guard); the `flow drift-events` namespace is locked from v1.0 (Path B parallel command); `DriftEvent.decision_id: int` is LOCKED unless a future change ships a v1.x migration guide; Path A subcommand group rename is LOCKED to v1.2+.

## Artifacts

- `openspec/changes/v1.0-followups/explore.md` (exploration phase, pre-existing)
- `openspec/changes/v1.0-followups/proposal.md` (this file)
- Engram mirror: topic_key `sdd/v1.0-followups/proposal`, type
  `architecture`, scope `project`

## Next Step

`sdd-design v1.0-followups` — produce `design.md` with D1..D5 architecture decisions (subset of the drift-hardening D1..D12, scoped to the v1.0 wire-format flip + read-side CLI context) + Open Questions table (0 open per this proposal §OQ) + `code_refs` block.

Loop mode continues from here: orchestrator will invoke
`sdd-spec v1.0-followups` → `sdd-tasks v1.0-followups` →
`sdd-apply v1.0-followups` → `sdd-verify v1.0-followups` →
`sdd-archive v1.0-followups` in sequence.
