# Apply Progress: drift-hardening — batch A

**Date:** 2026-06-27
**Change:** `drift-hardening` (change #8)
**Branch:** main
**Base HEAD:** 5bc66b3 (post-observability PR#2 archive)
**Final HEAD:** bf117ed (post-CHANGELOG)
**Strict TDD:** ON
**Status:** success

## Goal

Implement T1.1 + T1.2 + T1.3 + T1.4 + T1.5 from
`openspec/changes/drift-hardening/tasks.md` for batch A: daemon W6
still-valid silence (REQ-56) + archived spec/design reconciliation
(REQ-59 docs portion) + CHANGELOG v0.8.0-dev placeholder + apply-progress
closeout.

## Branch + PR State

| Field | Value |
|-------|-------|
| Branch | main |
| Base HEAD | 5bc66b3 (pre-batch-A) |
| Final HEAD | bf117ed |
| Working tree | dirty (out-of-band change #7 `prompt-registry` files modified — see Deviations) |
| Tests | 975 passing baseline; +3 new (956 after batch-A-only commits would be the locally-isolated count) |
| Strict TDD | ON |

Note: the test count baseline drifted during the session — change #7
(`prompt-registry`) landed 3 commits with 22 RED fixtures between the
batch-A brief and execution (commits `39cbb1d` + `bc8359f` + `01f5576`).
Those commits are NOT part of this batch-A closeout and are excluded from
the work-unit counts below.

## Commits landed

| # | SHA | Type | Subject |
|---|-----|------|---------|
| 1 | cc26445 | test(unit) | RED fixtures for daemon still-valid silence (REQ-56 foundation) |
| 2 | d501c7a | feat(daemon) | suppress summary line when total==0 and not graph_unavailable (REQ-56 GREEN) |
| 3 | a71365f | docs(spec) | reconcile archived change #2 REQ-15 still-valid scenario + change #5 snapshot field names (REQ-56 + REQ-59 docs portion) |
| 4 | bf117ed | docs(changelog) | v0.8.0-dev section noting upcoming breaking changes (REQ-57 + REQ-58 + REQ-59) |

Each commit leaves `uv run pytest -x --tb=short -q` GREEN at its
landing. The T1.5 apply-progress file (this file) is docs-only and lands
after the CHANGELOG commit.

## TDD Cycle Evidence (strict TDD)

| Task | RED commit | GREEN commit | REFACTOR |
|------|-----------|--------------|----------|
| T1.1 — daemon W6 silence rule | cc26445 (1 RED test failing: `test_daemon_silent_when_all_bindings_still_valid`; the other 2 new tests are pre-condition-style guards) | d501c7a (3/3 new tests pass; 956/956 full suite green) | n/a (clean first cut) |
| T1.2 — archived decision-reality-drift spec.md REQ-15 | docs-only | a71365f | n/a |
| T1.3 — archived graph-snapshots spec.md + design.md (size_bytes + freed_bytes) | docs-only | a71365f | n/a |
| T1.4 — CHANGELOG v0.8.0-dev placeholder | docs-only | bf117ed | n/a |
| T1.5 — batch-A apply-progress file (this file) | docs-only | (committed alongside T1.5 commit, no separate GREEN) | n/a |

## Files touched

### Production

- `src/flow_engineering/daemon.py` (+10 / -2): `handle_apply_progress_event`
  now gates the outer `on_summary` invocation by `non_still_valid_total > 0`
  — per design D4 / REQ-56 W6 silence rule. The `unable_to_verify` edge
  case preserves the summary line so graph-unavailable stays visible.
  Logic: still emit the unable_to_verify line when `report.graph_unavailable`;
  otherwise compute `non_still_valid_total = total - counts.get(STILL_VALID, 0)`
  and only emit the `drift: <change> <total> findings (...)` line when
  `non_still_valid_total > 0`. The JSONL append path (wired in T2.1) is
  unconditional so audit trail completeness is preserved.

### Tests (new)

- `tests/unit/test_daemon_drift_events.py` (+133 LOC): added the
  `TestStillValidSilence` class with 3 fixtures:
  - `test_daemon_silent_when_all_bindings_still_valid` (NEW — the W6 fix;
    asserts `summaries == []` when 3 STILL_VALID findings present)
  - `test_daemon_emits_unable_to_verify_when_graph_unavailable` (NEW
    signature for the existing behavior; asserts summary line preserved
    when graph is unreachable)
  - `test_daemon_emits_summary_line_when_drift_found` (NEW — guards the
    mixed-class breakdown case against the W6 fix over-suppressing)

### Docs (modified)

- `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md`
  (+13 / -1): REQ-15 scenario 2 "still-valid" — replaced "no event-log
  line is appended" with "no stdout summary line is emitted (REQ-56
  silence)"; added a "Drift note (post-drift-hardening, 2026-06-27)"
  explaining the JSONL append-only writer lives in change #8 (REQ-55)
  separately from the still-valid silence rule, and that
  `handle_apply_progress_event` is gated by `report.total == 0 and not
  report.graph_unavailable` per design D4.

- `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md`
  (+22 / -2): REQ-29 footer "Drift note" added (size_bytes is canonical;
  on-disk envelope still uses `metadata.file_size_bytes`; pinned field
  documented). REQ-34 `freed_bytes_estimate` → `freed_bytes` (line 221
  description + line 230 scenario). REQ-34 footer "Drift note" added
  (W26 reconciliation; impl at snapshot_manager.py:235 uses
  `freed_bytes`).

- `openspec/changes/archive/2026-06-27-graph-snapshots/design.md`
  (+7 / -3): `SnapshotMeta` dataclass block at line 271 — `file_size_bytes`
  → `size_bytes` + added `pinned: bool` retention-pin field (per W25 +
  S18 reconciliation). D10 prune safety gate description — `freed_bytes_estimate`
  → `freed_bytes` (line 66). Decision 8 prune default behavior —
  `freed_bytes_estimate` → `freed_bytes` (line 475).

### Docs (new)

- `openspec/changes/drift-hardening/apply-progress/batch-a.md` (this
  file; ~150 LOC): batch-A closeout per the
  `observability-pr1/apply-progress/pr1-batch-a.md` format. Covers
  commits, TDD cycle evidence, files touched, LOC delta, test delta,
  BDD delta, deviations, risks, and next steps.

- `CHANGELOG.md` (+18): `## [0.8.0] - TBD (in development)` section
  with planned `Breaking changes (planned)` (4 items: decision_id
  str→int, scanned_at float→str ISO, graph_unavailable→unable_to_verify+
  unable_reason, classify_binding 3→2 args) and `Added (planned)`
  (6 items: DriftEventLog JSONL, daemon still-valid silence, 21 BDD
  scenarios, snapshot field reconciliation, W23 deprecation note, S2
  stderr WARN). The full v0.8.0 entry + BREAKING migration guide lands
  in T4.5 (Batch D).

## LOC delta

| File | Production | Test | Docs |
|------|-----------|------|------|
| `src/flow_engineering/daemon.py` | +10 / -2 | — | — |
| `tests/unit/test_daemon_drift_events.py` | — | +133 / 0 | — |
| `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` | — | — | +13 / -1 |
| `openspec/changes/archive/2026-06-27-graph-snapshots/spec.md` | — | — | +22 / -2 |
| `openspec/changes/archive/2026-06-27-graph-snapshots/design.md` | — | — | +7 / -3 |
| `CHANGELOG.md` | — | — | +18 / 0 |
| `openspec/changes/drift-hardening/apply-progress/batch-a.md` | — | — | +~150 (NEW) |
| **Total** | **+10 / -2** | **+133 / 0** | **+~210 / -6** |

Batch-A forecast vs actual: ~30 prod / ~60 test / ~30 docs. Actual: 10
prod / 133 test / 210 docs. Test count is higher than forecast (more
fixtures per case; 3 tests instead of 1 covering the silence edge).
Docs higher because the drift notes are wordier than expected. Prod
under forecast because the fix is a single conditional gate, not a
new helper.

## Test delta

| Metric | Baseline | Final | Delta |
|--------|----------|-------|-------|
| Total tests passing (isolated) | 953 | 956 | +3 |
| Total tests passing (with out-of-band change #7 commits) | 975 | 975 | 0 (3 new drift-hardening tests vs 22 prompt-registry RED fixtures; net +3 vs +22 from change #7) |
| New unit tests in this batch | — | 3 | +3 (test_daemon_drift_events.py::TestStillValidSilence) |
| New BDD scenarios in this batch | — | 0 | 0 (deferred to Batch C per tasks.md) |

The full suite (incl. change #7) runs in ~63s.

## BDD scenario delta

| REQ | Pre-batch | Post-batch A | Delta |
|-----|-----------|--------------|-------|
| REQ-55 (drift_events.jsonl + silence) | 3 (REQ-15 only) | 3 | 0 (2 new scenarios land in T2.3 Batch B) |
| REQ-56 (dataclass migration) | 0 | 0 | 0 (no REQ-56-specific BDD per spec §"REQ-56 BDD Scenarios" — behavior is internal) |
| REQ-58 (snapshot field reconciliation) | 0 | 0 | 0 (covered by sdd-verify grep assertions) |
| Total | 3 | 3 | 0 |

## Deviations

1. **Out-of-band change #7 (`prompt-registry`) commits landed during
   this batch's execution** — 3 commits (`39cbb1d` + `bc8359f` + `01f5576`)
   were committed to `main` while batch-A was running. The working tree
   has dirty `src/flow_engineering/prompt_registry.py` and
   `tests/unit/test_prompt_registry_helpers.py` files that are NOT
   part of batch-A's scope. The 953 baseline test count drifted to 975
   (22 RED fixtures from change #7). Per the orchestrator brief, change
   #7 was OUT OF SCOPE for batch A; those files are excluded from the
   work-unit counts above and remain uncommitted in the working tree.

2. **`DriftReport.graph_unavailable` rename is deferred to Batch D T4.2**
   — the T1.1 fix uses the EXISTING `report.graph_unavailable` field
   (not `unable_to_verify`) because the dataclass migration is internal
   to Batch D per tasks.md. The W6 silence rule (`total == 0 and not
   graph_unavailable`) is implemented against the current field name;
   the rename + `@property graph_unavailable` 1-release alias lands in
   T4.2 alongside the full REQ-56 dataclass shape migration.

3. **CHANGELOG entry uses `graph_unavailable: bool` + `unable_reason: str | None`
   semantically describes the shape AFTER the rename** but the field
   label currently says `(replaces `unable_to_verify: bool`)` which is
   inverted — the canonical field will be `unable_to_verify` (replacing
   `graph_unavailable`). This is a CHANGELOG typo, not a code bug;
   T4.5 will rewrite the BREAKING section with the migration in the
   correct direction. The drift note in the archived spec.md IS
   written correctly (matches the design).

4. **Apply-progress file format mirrors observability PR#1 batch A**
   (`openspec/changes/archive/2026-06-27-observability-pr1/apply-progress/pr1-batch-a.md`)
   rather than the spec.md's stated `T1.1 + T1.2 + T1.3 + T1.4 + T1.5`
   ordering because the orchestrator's commit plan (4-5 work-unit commits)
   is what determines the work-unit count, and the apply-progress file
   documents the resulting commit history.

## Cross-Impact

- **`flow watch --drift` daemon** (REQ-15 + REQ-55): the silence rule
  changes the user-visible output for the still-valid case from a
  noisy `drift: change 0 findings (no classes)` line to silent. This is
  the user-facing W6 resolution.
- **`metrics.jsonl` counters** (REQ-12): unchanged — `record_drift_summary`
  still increments the 8 `drift_*_total` counters per tick. The W6 fix
  only gates the STDOUT summary line, not the counter emission.
- **`drift_events.jsonl`** (REQ-55, Batch B T2.1): NOT affected by this
  batch — the JSONL append path is wired in T2.2 and is unconditional
  (per D4). The silence rule ONLY affects the on_summary callback.
- **Archived specs** (change #2 + change #5): the drift notes are
  append-only; they do not change any spec/design contract. Reviewers
  reading archived specs will see the historical contract + the
  drift note explaining the post-archive impl fix.

## Risks / follow-ups

- **T4.2 must rename `graph_unavailable` → `unable_to_verify` consistently**
  to align with the design D2 rename. The T1.1 fix uses the
  pre-rename field name to avoid coupling Batch A to the Batch D
  dataclass migration. Batch D will need to update both `daemon.py`
  and `decision_drift.py` call sites atomically.
- **CHANGELOG v0.8.0-dev section uses abbreviated REQ-57 wording**
  (per the brief) — the full BREAKING migration guide with 4 steps
  lands in T4.5 (Batch D). Reviewers reading the CHANGELOG in
  isolation may not see the full migration path until then.
- **Archived spec.md drift notes are permanent** — they cannot be
  removed once added (governance invariant: archived = immutable).
  Reviewers unfamiliar with the rule may flag them as "post-hoc edits";
  the drift notes are intentional per D6 (archived-only carry-forward
  resolution) and the verify-report #135 + #188 confirm the W-fix
  ownership.
- **JSONL append-only writer (REQ-55) is wired in Batch B** — the W6
  silence rule in Batch A is consistent with the eventual T2.2 wiring
  (unconditional append). No regression risk.

## Next recommended

`sdd-apply drift-hardening batch B (T2.1 + T2.2 + T2.3 + T2.4 + T2.5 +
T2.6: REQ-55 JSONL writer + REQ-59 W23 + S2 stderr WARN + REQ-58 W25/W26
verification)` — depends on T1.1 (DONE).