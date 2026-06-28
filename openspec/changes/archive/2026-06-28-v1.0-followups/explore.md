<!-- explore.md: v1.0-followups. Source: sdd-explore sub-agent. -->
# Explore: v1.0-followups

**Change:** `v1.0-followups` (NEW change — 2 SUGGESTION items from drift-hardening verify-report S1 + S2, scoped narrowly per capability spec `decision-drift/spec.md:408+410`).
**Date:** 2026-06-28
**Mode:** Strict TDD (per `sdd-init/flow-engineering` cached context; loop mode ACTIVE)
**HEAD at exploration:** `8b02d38` (post-v0.9.0-hardening T3.13 docs commit; 1233/1233 tests passing per `openspec/specs/decision-drift/spec.md:57`)
**Branch:** `main` (working tree CLEAN per `git status --short`)
**Pre-discussion:** capability spec already lists the v1.0 plan verbatim (`openspec/specs/decision-drift/spec.md:408+410`); drift-hardening verify-report S1+S2 carry the explicit recommendations; v0.9.0-hardening verify-report archive-report.md:166/168 + tasks.md:158-160 mirror them.

---

## Status

**explored → ready for `sdd-propose v1.0-followups`**. All 6 open questions are pre-discussed in the capability spec + drift-hardening archive + v0.9.0 archive. No new investigation required before proposal.

---

## Goal

Land the 2 deferred SUGGESTION items from drift-hardening (`S1` JSONL wire-format `decision_id` consistency + `S2` `flow drift` read-side CLI) in a single small TDD change that closes the operator-UX gap left by v0.8.0/v0.9.0 hard-break migration, without re-opening any closed carry-forward. v1.1 follow-ups (DriftEventLog rotation + cross-project federation) remain deferred per the capability spec roadmap.

---

## Investigation findings

### S1 — `DriftEvent.decision_id: str` vs `Finding.decision_id: int` inconsistency

**Current state (HEAD `8b02d38`):**

- `decision_drift.py:79` — `decision_id: int  # REQ-56 W8; hard break in v0.9.0`. The `__post_init__` at `decision_drift.py:84-90` raises `TypeError` on non-`int` (including `bool`) — post-v0.9.0 the v0.8.0 `from_legacy()` shim is REMOVED.
- `drift_event_log.py:46` — `decision_id: str` (legacy wire format per the v0.7.x spec #135 line 272 archived requirement; preserved through v0.8.0/v0.9.0 for backward compat).
- `daemon.py:60` — `decision_id=str(finding.decision_id)` coerces `Finding.decision_id: int` → `DriftEvent.decision_id: str` on append. The coercion is the explicit, intentional shim per the `daemon.py:46-50` docstring.
- `cli.py:1659` — `_write_back_findings` reads `int(finding.decision_id)`, post-v0.9.0 always succeeds (no `from_legacy` fallback needed).
- `drift_event_log.py:95-119` — `DriftEventLog.read_all()` reconstructs `DriftEvent(**data)` from each JSONL line. Currently no remapping for `decision_id` types (only `class`/`event_class` at `drift_event_log.py:114-115`).

**Inconsistency surface (operator-visible):**

- `cat ~/.flow-engineering/drift_events.jsonl | jq` shows `"decision_id": "42"` (string).
- Python `Finding.decision_id: int` (in-memory only; never round-trips through JSONL).
- Downstream consumers parsing the JSONL must coerce string→int explicitly.

**Doc drift to flag (not blocking):** `openspec/changes/archive/2026-06-27-drift-hardening/verify-report.md:296` says `DriftEventLog.read_all()` helper "already exists at `drift_event_log.py` as `iter_drift_events()`". **The actual helper is `read_all()`** (at `drift_event_log.py:95-119`); there is no `iter_drift_events()` symbol. The verify-report's name is stale; the proposal must use the real name.

**Pre-discussed resolution (capability spec `decision-drift/spec.md:408+410`):**

> "v1.0 planning resumes per the deferred follow-ups: DriftEvent JSONL `decision_id: int` wire-format flip (S1 from drift-hardening) + `flow drift events` CLI read-side (S2 from drift-hardening) + tech-debt residuals (S2 ruff `--unsafe-fixes` + S3 mypy annotations on `decision_drift.py` lines 127/161/203/252/253/262/278/372/375/310/411/439) + DriftEventLog rotation (v1.1 alongside metrics rotation)."

**Pre-discussed resolution (drift-hardening verify-report S1):**

> "Future v1.0 follow-up change flips `DriftEvent.decision_id: int` + emits JSONL with int. Add a `## Drift event log JSONL schema` section to `openspec/specs/decision-drift/spec.md` documenting the v0.8.0 wire format explicitly."

### S2 — `flow drift` read-side CLI (currently write-only)

**Current state (HEAD `8b02d38`):**

- `cli.py:1712-1809` — `@main.command() def drift(...)` is a SINGLE command, not a group. It runs `scan_change` and prints the table. There is no `flow drift events`, `flow drift log`, or `flow drift list` subcommand.
- `drift_event_log.py:95-119` — `DriftEventLog.read_all()` exists and is fully tested (`tests/unit/test_drift_event_log.py`). Returns `list[DriftEvent]` with malformed-line tolerance. **No `since` / `change` / `event_class` filters** — the helper just reads the whole file.
- `daemon.py:36-65` — `_append_drift_events` is the WRITE-side; one JSONL line per non-STILL_VALID finding.
- Operators currently use `cat ~/.flow-engineering/drift_events.jsonl | jq` or `flow metrics --domain=drift` to inspect drift counters (no event-by-event query).

**Analogue pattern (observability PR#2 — `openspec/changes/archive/2026-06-27-observability-pr2/verify-report-pr2.md:124-148`):**

The observability project adopted a **subcommand group** pattern:
- `@main.group(invoke_without_command=True)` for `flow metrics` — preserves `flow metrics` (no subcommand) as the legacy REQ-8 close surface + adds `flow metrics summary|export|aggregate` subcommands.
- The PR#2 verify-report flagged W1: spec wanted `--prometheus`/`--percentile` FLAGS; impl shipped SUBCOMMANDS. **The drift was accepted** (subcommand shape matches CHANGELOG + BDD + impl + user docs).

Drift has a different shape: `flow drift <change>` already takes a `<change>` POSITIONAL arg. Converting `@main.command() def drift(...)` to a `@main.group(name="drift") def drift_group()` would force callers to switch to `flow drift check <change>` or `flow drift scan <change>` — that's BREAKING. Two paths:

**Path A (BREAKING — rename to subcommand):** `flow drift check <change>` + `flow drift events <list|tail|stats>`. Most idiomatic with the `flow metrics` group pattern but requires a migration note in CHANGELOG.

**Path B (NON-BREAKING — parallel command):** keep `@main.command() def drift(...)` as-is for `flow drift <change>`. Add `@main.group(name="drift-events") def drift_events_group()` (or `@main.group(name="driftlog")`) with `list|tail|stats` subcommands. Zero breakage; slightly less elegant than the `flow metrics` group pattern; document the parallel-command rationale in CHANGELOG.

**Pre-discussed resolution (drift-hardening design D5 + verify-report S2):**

> "Operators use `cat ~/.flow-engineering/drift_events.jsonl | jq` in v0.8.0/v0.9.0." → "v1.0 follow-up change for `flow drift events` CLI subcommand + `DriftEventLog.read_all()` helper (already exists at `drift_event_log.py` as `iter_drift_events()`)." → "Lands in a v1.0 / `drift-events-dashboard` change."

**Pre-discussed resolution (v0.9.0-hardening archive-report.md:166-168 + tasks.md:158-160):**

> "v1.0 follow-ups: ... `flow drift events` CLI read-side ... `flow drift events --format=prometheus|csv` (deferred to v1.0) ... Cross-project federation for drift events (`flow drift events --project=<key>`) — deferred to `federated-drift-events` follow-up."

The capability spec + drift-hardening + v0.9.0-hardening archives are unanimous: ship `flow drift events` read-side in v1.0 with `--format=prometheus|csv` also landing in v1.0; cross-project federation stays v1.1+.

---

## Open Questions

| # | Question | Pre-discussed resolution | Owner |
|---|----------|--------------------------|-------|
| **OQ-1** | S1: `DriftEvent.decision_id` type? | **Option A** — flip to `int` (matches `Finding.decision_id` post-v0.9.0 hard break; matches capability spec v1.0 plan; aligns with W8 design direction). | orchestrator brief pre-decided |
| **OQ-2** | S1: read-side compat shim for old `str` JSONL lines? | **Recommended**: add a `try: int(data["decision_id"]) except (TypeError, ValueError): skip` guard in `DriftEventLog.read_all()` (mirrors the v0.8.0 → v0.9.0 soft-migration pattern). Old `drift_events.<stamp>.jsonl` files remain readable without migration. | orchestrator brief pre-decided (W1 + W3 drift-hardening precedent) |
| **OQ-3** | S1: migration guide for existing JSONL consumers? | **Yes** — 1-line `sed` note in CHANGELOG v1.0 entry: `sed -i 's/"decision_id": "\([0-9]*\)"/"decision_id": \1/g' ~/.flow-engineering/drift_events.jsonl` (mirrors the W23 `snapshot_pruned_total` → `snapshot_prune_total` precedent). | CHANGELOG owner |
| **OQ-4** | S2: subcommand vs parallel command? | **Recommended Path B** — parallel command `flow drift-events list|tail|stats` (NON-BREAKING; preserves `flow drift <change>` callers; slightly less elegant than `flow metrics summary`). Path A (subcommand group) is the alternative if orchestrator accepts the BREAKING rename. | orchestrator brief pre-decided toward subcommand; flag the trade-off |
| **OQ-5** | S2: which subcommands? | **`list` (default text/JSON table with `--since`/`--until`/`--change`/`--event-class`/`--limit` filters)** + **`tail` (last N events, default 10)** + **`stats` (per-event-class counts + per-change counts + per-decision-id counts in a fixed-width table; `--format=json` for machine-readable)**. Mirrors `flow metrics {summary,export,aggregate}` 3-subcommand precedent. | capability spec + drift-hardening design |
| **OQ-6** | S2: `--format=prometheus|csv` for events? | **YES** — landing in v1.0 per capability spec roadmap + v0.9.0-hardening tasks.md:159. Add `--format=text|json|prometheus|csv` to `flow drift-events list`. | capability spec pre-decided |

**0 truly open questions** — all 6 are pre-discussed in capability spec + drift-hardening + v0.9.0-hardening archives. Proposal can proceed without additional orchestrator input.

---

## Proposed approach

### S1 — `DriftEvent.decision_id` consistency (Option A recommended)

| Option | Description | Pros | Cons | Effort |
|--------|-------------|------|------|--------|
| **A** ✅ | Flip `DriftEvent.decision_id: str` → `int`. Remove `str(finding.decision_id)` coercion at `daemon.py:60`. Add `try/except` guard in `read_all()` for old str lines (silent drop on `ValueError`). Update `to_json_dict()` to emit JSON int. Document v1.0 wire-format in `openspec/specs/decision-drift/spec.md` Drift event log schema section. 1-line `sed` migration note in CHANGELOG v1.0 entry. | Matches `Finding.decision_id: int` (already hard-int post-v0.9.0). Single source of truth. Aligns with W8 design direction. Minimal API surface change. Drop-in for new consumers. | BREAKING wire format — old `str` consumers must coerce. `read_all()` silently drops unparseable old lines (acceptable; mirror v0.9.0 silent-skip pattern). | ~10 prod + ~20 test = ~30 LOC |
| **B** ❌ | Flip `Finding.decision_id` back to `str`. | (none — would undo the v0.9.0 hard break) | **REGRESSION**: v0.9.0 hard-break just shipped 1 day ago (HEAD `3de7783`). Undoing it would break all the v0.9.0 callers + invalidate the 1232/1232 test count. REJECTED. | n/a |
| **C** ❌ | Add explicit `decision_id_int` field alongside `decision_id: str`. | Backward-compat preserved. Two fields per event. | API surface bloat. Two-source-of-truth. Confusing for consumers (which one to read?). | ~5 prod + ~20 test = ~25 LOC |
| **D** ❌ | Keep both as-is + add `.decision_id_int` accessor on `DriftEvent`. | Same bloat as C with extra computed property. | Same bloat + extra runtime cost per access. | ~3 prod + ~10 test = ~13 LOC |

**Recommendation: Option A** (matches the unanimous pre-discussed direction in capability spec + drift-hardening + v0.9.0-hardening archives). The read-side compat shim (try/except in `read_all()`) makes the wire-format break non-destructive for old data.

### S2 — read-side CLI (Path B recommended; Path A as alternative)

**Recommended Path B — parallel command `flow drift-events <subcmd>`** (NON-BREAKING):

- `flow drift-events list [--since=<iso>] [--until=<iso>] [--change=<name>] [--event-class=<STILL_VALID|LABEL_DRIFT|...>] [--limit=<N>] [--format=text|json|prometheus|csv] [--path=<alt-log>]` → renders rows from `DriftEventLog.read_all()` with the requested filters. Default text = fixed-width table (mirrors `flow drift <change>` + `flow metrics summary` text-table precedent). `--format=json` mirrors `flow drift <change> --json` + `flow metrics --json`. `--format=prometheus` mirrors `flow metrics export --format=prometheus` (textfile exposition with `# HELP`/`# TYPE`/`# EOF`).
- `flow drift-events tail [--limit=<N>=10] [--change=<name>] [--event-class=<...>] [--format=text|json]` → renders the last N events newest-first (mirrors `tail -n` shell convention).
- `flow drift-events stats [--change=<name>] [--since=<iso>] [--until=<iso>] [--format=text|json]` → per-event-class counts + per-change counts + per-decision-id top-N counts in a fixed-width table (mirrors `flow metrics summary` per-domain dashboard).

Flags modeled after `flow metrics {summary,export,aggregate}` so the operator mental model transfers. Exit codes mirror D9 (0=success, 2=invalid args, 3=malformed JSONL).

**Alternative Path A — subcommand group `flow drift {check,events,...}`** (BREAKING):

Convert `cli.py:1712 @main.command() def drift(...)` to `@main.group(name="drift") def drift_group()`. Add `@drift_group.command(name="check") def drift_check(...)` (the renamed scan) + `@drift_group.command(name="events") def drift_events(...)`. Operators migrate from `flow drift <change>` → `flow drift check <change>` (1-line `sed` in CHANGELOG v1.0). Cleaner long-term but BREAKING and adds a soft compat shim.

**Trade-off:** Path A is more idiomatic with `flow metrics {summary,export,aggregate}` but BREAKING; Path B is non-breaking but parallel-namespace. **Recommend Path B** for v1.0 (operator UX continuity); consider Path A in a future v1.1 cleanup if the `flow drift` namespace grows further.

---

## Proposed REQs

| REQ | Title | Carries | Source |
|-----|-------|---------|--------|
| **REQ-V1.0.1** | `DriftEvent.decision_id: int` JSONL wire format + `DriftEventLog.read_all()` defensive coercion for legacy `str` lines | S1 from drift-hardening | capability spec `decision-drift/spec.md:408+410`; drift-hardening verify-report S1 |
| **REQ-V1.0.2** | `flow drift-events {list,tail,stats}` read-side CLI subcommand group (Path B) with `--since`/`--until`/`--change`/`--event-class`/`--limit`/`--format=text|json|prometheus|csv` flags + D9 exit codes | S2 from drift-hardening | capability spec `decision-drift/spec.md:408+410`; drift-hardening design D5 + verify-report S2; v0.9.0-hardening tasks.md:158-160 |
| **REQ-V1.0.3** | Drift event log JSONL schema doc section in `openspec/specs/decision-drift/spec.md` (v1.0 wire format: `{change, decision_id: int, binding_id, class, detected_at}` — same key order as v0.8.0; type changes from `str` → `int` for `decision_id`) | S1 documentation gap | drift-hardening verify-report S1 explicit recommendation |
| **REQ-V1.0.4** | Tech-debt residuals: ruff `--unsafe-fixes` on `src/flow_engineering/decision_drift.py` + mypy `# type: ignore[arg-type]` cleanup on `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439` | capability spec roadmap | capability spec `decision-drift/spec.md:410` S2 + S3 from drift-hardening |

**Total REQs**: 4 (REQ-V1.0.1..V1.0.4)
**Estimated LOC**: ~50 prod + ~150 test = ~200 (without TDD multiplier); ~1 200 with ×6 TDD multiplier (includes BDD scaffolding).
**Estimated wall time**: ~1.5-2 hours end-to-end (1 apply batch + verify).

---

## Out of scope (deferred to v1.1+)

Per capability spec `decision-drift/spec.md:408+410` + drift-hardening + v0.9.0-hardening archives:

- **`DriftEventLog` rotation policy** (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` env var + auto-rotation at threshold + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` gzip-and-rotate cron) — DEFERRED to v1.1 alongside `metrics.jsonl` rotation (REQ-44 deferred). The v0.8.0 10 MB hardcoded rotation never landed (drift-hardening W7).
- **Cross-project federation for drift events** (`flow drift-events --project=<key>` filter; requires modifying every record helper signature to inject a `project` field) — DEFERRED to a separate `federated-drift-events` follow-up change.
- **OpenTelemetry OTLP push for drift events** — DEFERRED; Prometheus textfile from REQ-38 already covers the v1 use case.
- **`flow drift <change> --drift-event-log[=<path>]` per-finding class filter** (e.g., `--event-class-filter=STALE,MISSING`) — DEFERRED; v0.8.0+ persists all non-still-valid findings by default.
- **`flow drift-events` Path A subcommand group rename** (BREAKING) — DEFERRED; revisit only if the `flow drift` namespace grows further in v1.2+.

---

## Risks + carry-forwards

| ID | Severity | Pattern | Evidence | Mitigation |
|----|----------|---------|----------|------------|
| **R1** | LOW | Wire-format BREAKING (S1) | `DriftEvent.decision_id` flips from `str` → `int`; old `cat ~/.flow-engineering/drift_events.jsonl \| jq` consumers that piped the field to a `int()`-expecting script will now work without coercion (good); consumers that compared as string ("42" < "9" lex sort) will see behavior change (bad but rare). | CHANGELOG v1.0 1-line `sed` migration note: `jq -c '.decision_id \|= tonumber' ~/.flow-engineering/drift_events.jsonl > .bak && mv .bak ~/.flow-engineering/drift_events.jsonl`. Silent-skip in `read_all()` for old `str` lines (defensive). |
| **R2** | LOW | Read-side compat shim silently drops old lines (S1) | `DriftEventLog.read_all()` will silently skip any pre-v1.0 line where `decision_id` is a non-numeric string (the defensive guard at read). | Mirror the v0.9.0 silent-skip pattern from `DriftEventLog.read_all()` (already exists at `drift_event_log.py:108-119`). Emit a one-time stderr WARN at CLI invocation if any old-format lines were skipped (mirrors `_write_back_findings` S2 cadence). |
| **R3** | LOW | Path B parallel namespace is less elegant than Path A subcommand group | `flow drift-events` is a sibling command to `flow drift`, not a subcommand. Inconsistent with `flow metrics {summary,export,aggregate}` group pattern. | Document the parallel-namespace rationale in CHANGELOG v1.0 entry. Revisit Path A in v1.2+ if `flow drift` namespace grows. |
| **R4** | LOW | Doc drift in `drift-hardening/verify-report.md:296` says `iter_drift_events()` | The actual helper is `DriftEventLog.read_all()` at `drift_event_log.py:95-119`. The verify-report's name is stale. | Note in the proposal (not blocking); the proposal must reference the real symbol name. Optional post-archive drift-note in archived `verify-report.md`. |
| **R5** | LOW | 12 mypy residuals in `decision_drift.py:127/161/203/252/253/262/278/372/375/310/411/439` (S3 from drift-hardening) | Per v0.9.0 verify-report + capability spec: within expected band for `__post_init__` TypeError-on-str enforcement sites. | REQ-V1.0.4 cleanup commit adds `# type: ignore[arg-type]` where the intentional TypeError-on-str is tested. ~3-line edit. |

**0 CRITICAL / 0 HIGH / 5 LOW risks**. All mitigations are within the proposed REQ scope or already-documented as low-priority follow-ups.

---

## Next step

Proceed to `sdd-propose v1.0-followups`. The proposal should:
1. Quote the 4 proposed REQs verbatim (REQ-V1.0.1..V1.0.4).
2. Reference the 2 SUGGESTION findings (S1+S2 from drift-hardening verify-report).
3. Reference the capability spec v1.0 entry verbatim (`decision-drift/spec.md:408+410`).
4. Reference the observability PR#2 subcommand-group precedent for the S2 design.
5. Flag the Path A vs Path B trade-off explicitly so orchestrator can override the Path B recommendation if desired.
6. Flag the `iter_drift_events()` doc drift in `drift-hardening/verify-report.md:296` so the proposal uses the real symbol name `read_all()`.

Loop mode continues: `sdd-propose v1.0-followups` → orchestrator review → `sdd-design` → `sdd-tasks` → `sdd-apply` → `sdd-verify` → `sdd-archive v1.0-followups`.
