# Archive Report — decision-reality-drift

## Status

**ARCHIVED** (2026-06-26)

SDD cycle complete: propose → design → spec → tasks → apply (PR#1 #3 + PR#2 #4) → verify (PASS WITH WARNINGS, 0 critical) → archive.

## Changelog

- `CHANGELOG.md` v0.3.0 entry (post-W7/S1 doc-accuracy fix PR #6 squash `e8ac1d5`)

## Files Created / Moved

### Moved to archive (renamed with git-detected 100%)

- `openspec/changes/decision-reality-drift/spec.md` → `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md`
- `openspec/changes/decision-reality-drift/design.md` → `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md`
- `openspec/changes/decision-reality-drift/tasks.md` → `openspec/changes/archive/2026-06-26-decision-reality-drift/tasks.md` (all 16 tasks marked `[x]`)

### Created (new in repo)

- `openspec/changes/archive/2026-06-26-decision-reality-drift/verify-report.md` (copy from Engram #135)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/apply-progress/pr1-batch-a.md` (Engram #125)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/apply-progress/pr1-batch-b.md` (Engram #126)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/apply-progress/pr1-batch-c.md` (Engram #127)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/apply-progress/pr1-batch-d.md` (Engram #128)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/apply-progress/pr1-batch-e.md` (Engram #129)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/apply-progress/pr1-batch-f.md` (Engram #130)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/apply-progress/pr2-batch-g.md` (Engram #133)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/apply-progress/pr2-batch-h.md` (Engram #134)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/archive-report.md` (this file)

## PRs merged

- **#3**: feat(decision-reality-drift): PR#1 - core drift detector (REQ-9, 12-14, W2/W3) — squash `b3a3ac7`
- **#4**: feat(decision-reality-drift): PR#2 - daemon --drift verification wiring (REQ-15, REQ-16 partial) — squash `a5a9719`
- **#5**: chore(release): decision-reality-drift PR#2 closure - CHANGELOG v0.3.0 + sdd-verify Step 6a + 6 SKILL.md drift hooks — squash `0d41bbe`
- **#6**: docs(changelog): fix v0.3.0 counter name typo + BDD count accuracy — squash `e8ac1d5`

## Test summary

- 385/385 unit tests passing (`uv run pytest`)
- 63 BDD scenarios across 12 feature files
- Baseline (PR#1 merge): 364 → final: 385 (+21)
- All 16 tasks closed (T1.1..T1.10 PR#1 + T2.1..T2.6 PR#2)

## Capability Mapping Decision

**No `openspec/specs/` baseline existed in this project** — verified by `Get-ChildItem openspec -Recurse`. The project uses `openspec/changes/` as the sole spec store, so no delta merge into capability specs was performed (same precedent as archive-report #119).

The 8 REQs (REQ-9..REQ-16) live in the archived spec.md as one capability ("decision-reality-drift") rather than being split across `openspec/specs/{drift-detection,drift-cli,drift-counters,drift-metadata,drift-resilience,drift-daemon,skill-prose}/spec.md`. If/when `openspec/specs/` is initialized post-archive, the archive spec is the importable source.

## Carry-forwards (WARNINGS documented, NOT CRITICAL)

- **W4** BDD shortfall — spec promised 39 scenarios across 8 feature files; impl delivered 18 across 3. Actual measurement shows 63 scenarios across 12 feature files (discrepancy in verify's count of "feature files"). Likely owner: a `drift-hardening` change.
- **W5** REQ-15 event-log drift — spec required JSONL at `~/.flow-engineering/drift_events.jsonl`; impl emits stdout summary via `on_summary`. Owner: `drift-hardening`.
- **W6** REQ-15 still-valid silence drift — spec says no event-log line for still-valid; impl emits `drift: <change> 0 findings`. Owner: `drift-hardening`.
- **W8** Spec/design dataclass drift — `decision_id: str` vs int; `scanned_at: float` vs ISO str; `graph_unavailable: bool` vs `unable_to_verify+unable_reason`; `classify_binding` takes 3 args not 2. Already acknowledged in apply-progress #126. Owner: spec delta sync or `drift-hardening`.

(W7 and S1 resolved pre-archive via PR #6 squash `e8ac1d5`.)

## Suggestions (carry-forwards, non-blocking)

- **S1** resolved pre-archive (PR #6 fixed BDD count claim)
- **S2** CLI `_write_back_findings` silently skips non-int decision_id without stderr WARN — owner: `drift-hardening`

## Out-of-scope reminders (carried from tasks.md)

- Snapshot-pinned drift — `graph-snapshots` owns; detector takes `graph_path` param (seam in place)
- Cross-project drift — `cross-project-federation` owns; v1 skip + WARN
- Re-suggestion on `stale_id` — surface-only; future `decision-resolve`
- Auto-fix drift — detector reports; humans fix (matches `flow inspect` precedent)

## Traceability (Engram observation IDs)

- #120 — explore (Approach C, 6-class taxonomy)
- #121 — proposal (PR#1/PR#2 breakdown, W2/W3 absorption)
- #122 — spec (8 REQs, 39 BDD scenarios)
- #123 — design (10 architecture decisions)
- #124 — tasks (16 tasks across 2 PRs)
- #125 — apply-progress PR#1 batch A (W2/W3 reconciliation)
- #126 — apply-progress PR#1 batch B (scaffold + RED + GREEN classify_binding)
- #127 — apply-progress PR#1 batch C (scan_change + observability counters)
- #128 — apply-progress PR#1 batch D (update_observation_metadata helper)
- #129 — apply-progress PR#1 batch E (CLI flow drift subcommand)
- #130 — apply-progress PR#1 batch F (BDD req9_drift_detection)
- #133 — apply-progress PR#2 batch G (daemon --drift + CLI flag + BDD req15)
- #134 — apply-progress PR#2 batch H (CHANGELOG + 6 SKILL.md hooks)
- #135 — verify-report (PASS WITH WARNINGS, 0 critical)
- This archive-report — topic `sdd/decision-reality-drift/archive-report`

## Cleanup Verification

- `git status --short`: archive folder created + active folder removal pending (post-commit)
- `git log --oneline -10`: PRs #3-#6 squash merges intact on `main`
- `uv run pytest --tb=no -q`: **385 passed in 1.76s** — all green (verified pre-archive)

## Relevant Files

- `openspec/changes/archive/2026-06-26-decision-reality-drift/spec.md` — archived source of truth (8 REQs)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/design.md` — archived architecture (10 decisions)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/tasks.md` — archived task breakdown (16 tasks, 21 commits)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/verify-report.md` — PASS WITH WARNINGS, 0 critical
- `openspec/changes/archive/2026-06-26-decision-reality-drift/apply-progress/*.md` — 8 batch snapshots
- `openspec/changes/archive/2026-06-25-decision-code-linking/` — predecessor archive (W2 reconciliation lives here)
- `CHANGELOG.md` — v0.3.0 entry (with W7 typo fixed in PR #6)
- `src/flow_engineering/decision_drift.py` — REQ-9, REQ-12
- `src/flow_engineering/cli.py` — REQ-10/11/14, REQ-15
- `src/flow_engineering/daemon.py` — REQ-15
- `src/flow_engineering/observability.py` — REQ-12
- `src/flow_engineering/engram_io.py` — REQ-13
- `tests/bdd/req9_drift_detection.feature` — 14 REQ-9 scenarios
- `tests/bdd/req15_drift_daemon.feature` — 3 REQ-15 scenarios
- `tests/bdd/req3_engram_io.feature` — W3 modification (+1 scenario)
- `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` — 6 runtime Drift detection hook sections

## Next change

- Change #3: `vector-semantic-search` (Engram FTS5 → fuzzy similarity via sqlite-vec or Qdrant). ~1.5-2h.

---

**Session**: flow-engineering-decision-reality-drift-archive-2026-06-26
**SDD Cycle**: COMPLETE
**Next**: `vector-semantic-search` (queue position, now unblocked)