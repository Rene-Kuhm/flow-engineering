# Archive Report — cross-project-federation

## Status

**ARCHIVED** (2026-06-26)

SDD cycle complete: explore (with critical correction) → propose → design → spec → tasks → apply (single PR via batches A + B1 + B2 + C) → verify (FAIL with C1 critical + 3 warnings) → W-fix PR (`4c6b39b`) → archive.

## Important correction surfaced during explore

The original premise of "7 separate Engram DBs" was **wrong**. There is ONE shared SQLite at `~/.engram/engram.db` (now 169 obs across 9 projects) with FTS5 already indexed by `project`. The "federation" is a logical surface (filtered SQL queries on the shared DB), not physical cross-DB infra. This collapsed the solution from "heavy infra" to "add 1 federated query method + fix tagging discipline + aliases for renames".

## Changelog

- CHANGELOG.md v0.5.0 entry (post-W17 doc-accuracy fix)

## Files Created / Moved

### Moved to archive (renamed with git-detected 100%)
- `openspec/changes/cross-project-federation/explore.md`
- `openspec/changes/cross-project-federation/proposal.md`
- `openspec/changes/cross-project-federation/design.md`
- `openspec/changes/cross-project-federation/spec.md`
- `openspec/changes/cross-project-federation/tasks.md` (with W18 checkbox flip applied)

### Created (new in repo)
- `openspec/changes/archive/2026-06-26-cross-project-federation/verify-report.md` (from Engram #170)
- `openspec/changes/archive/2026-06-26-cross-project-federation/apply-progress/batch-a.md` (Engram #164)
- `openspec/changes/archive/2026-06-26-cross-project-federation/apply-progress/batch-b1.md` (Engram #166)
- `openspec/changes/archive/2026-06-26-cross-project-federation/apply-progress/batch-b2.md` (Engram #167)
- `openspec/changes/archive/2026-06-26-cross-project-federation/apply-progress/batch-c.md` (Engram #169 — timeout recovery)
- `openspec/changes/archive/2026-06-26-cross-project-federation/apply-progress/w-fix-c1-w17-w18-w19.md` (commit `4c6b39b` extraction)
- `openspec/changes/archive/2026-06-26-cross-project-federation/archive-report.md` (this file)

## PRs merged

- **#10**: feat(cross-project-federation): federated search + project tagging + aliases (REQ-23..27) — squash `bfa2db5`
- Post-merge housekeeping (direct to main):
  - `4c6b39b` fix(cross-project-federation): pre-archive C1/W17/W18/W19 critical + warnings

## Test summary

- 576/576 unit tests passing (start of change #4) → 699 (post-batch C) → 699 (post-W-fix, +0 tests but +C1 fix + result rewrite)
- 91 BDD scenarios across 18 feature files (start) → 116 across 23 feature files (post-batch C)
- 25 new BDD scenarios added (req23=5, req24=6, req25=5, req26=4, req27=5)
- All 13 tasks closed (T1.1..T1.13)

## Carry-forwards from verify (all RESOLVED pre-archive)

| ID | Status | Resolution |
|----|--------|------------|
| C1 (alias transparent rewrite) | resolved | commit `4c6b39b` — forward + reverse alias resolution + result-level project field rewrite |
| W17 (CHANGELOG 'mem_search' overclaim) | resolved | commit `4c6b39b` — rewrote Notes section |
| W18 (tasks.md T1.8..T1.13 checkboxes) | resolved | archive commit — flipped `[ ]` to `[x]` for all 5 stale sections; added `DONE (<hash>)` annotations. (Note: `4c6b39b` commit message claimed W18 was resolved but the diff did not include tasks.md; the bookkeeping fix landed in the archive commit, consistent with the "PASS WITH WARNINGS after C1/W-fixes resolved" framing.) |
| W19 (apply_tag contract drift) | resolved | commit `4c6b39b` — return error dict instead of raising ValueError; updated 3 tests |
| S2 (pyproject version 0.5.0) | non-blocking | noted; deferred (TODO comment in tasks.md follow-ups) |
| S3 (record_federated_summary signature notation) | non-blocking | CHANGELOG fix; cosmetic |

## Out-of-scope reminders (carried from tasks.md follow-ups)

1. Spec counter catalog in `openspec/specs/observability/spec.md` for the 3 new `federated_*` counters (REQ-26 scenario 4) — defer to a future observability change
2. Bump `pyproject.toml` version `0.4.0` → `0.5.0` (matches CHANGELOG entry) — defer to next release
3. Verify `MEMORY.md` or AGENTS.md mentions `FLOW_AUTO_PROJECT_TAG=1` opt-in + `flow projects alias/backfill` workflow for future contributors
4. Cross-impact: confirm `vector-semantic-search` (REQ-17/22) tests stay green; vector index path is orthogonal to federation — VERIFIED in verify #170
5. Document `registry.json` auto-build behavior (D11) in `~/.config/flow-engineering/README` or AGENTS.md for first-run users

## Cross-impact on prior changes

- decision-code-linking (change #1): no impact — REQ-1..8 still green
- decision-reality-drift (change #2): no impact — REQ-9..16 still green (id-based, no project changes)
- vector-semantic-search (change #3): no impact — REQ-17..22 still green (semantic search is orthogonal to federation; both are additive on the ABC)

## Traceability (Engram observation IDs)

- #156 — explore (Approach A, premise correction: shared DB not silos)
- #158 — proposal (Sketch A additive `mem_search_federated`, 8 open questions)
- #159 — design (D1-D11, 8 OQs resolved definitively)
- #161 — spec (5 REQs, 25 BDD scenarios, filter truth table)
- #162 — tasks (13 tasks, 3 apply batches, single PR strategy)
- #164 — apply-progress batch A (T1.1 + T1.2 + T1.4)
- #166 — apply-progress batch B1 (T1.3 + T1.6)
- #167 — apply-progress batch B2 (T1.5 + T1.7 + T1.12)
- #169 — apply-progress batch C (T1.8 + T1.9 + T1.10 + T1.11 + T1.13, timeout recovery)
- #170 — verify-report (FAIL with C1 + 3 warnings; all resolved pre-archive)
- (synthesized) — w-fix-c1-w17-w18-w19 (commit `4c6b39b`)
- This archive-report — topic `sdd/cross-project-federation/archive-report`

## Cleanup Verification

- `git status`: working tree clean post-archive
- `git log --oneline -10`: PR #10 squash + `4c6b39b` W-fix + archive commit all intact on `main`
- `uv run pytest --tb=no -q`: **699 passed in 5.77s** — all green (verified pre-archive)
- 5 git rename detections (proposal/design/spec/tasks/explore mirror)
- 5 apply-progress files created in `apply-progress/` subfolder (4 PR batches + 1 W-fix sidecar)

## Next change

- Change #5: `graph-snapshots` (historical graph snapshots, diff temporal, rollback). ~1-1.5h. Use `/sdd-new graph-snapshots`.

---

**Session**: flow-engineering-cross-project-federation-archive-2026-06-26
**SDD Cycle**: COMPLETE
**Next**: `graph-snapshots` (queue position 5, now unblocked)
**Topic**: sdd/cross-project-federation/archive-report