<!-- Archived 2026-06-26 from sdd/cross-project-federation/w-fix-c1-w17-w18-w19 (commit 4c6b39b) -->

# Apply progress W-fix (C1 + W17/W18/W19) — cross-project-federation

## Goal

Pre-archive housekeeping commit that resolves all 4 verify findings from `sdd/cross-project-federation/verify-report` (#170): the C1 CRITICAL plus 3 WARNINGs (W17, W18, W19). Landed directly on `main` after PR #10 squash (`bfa2db5`) merged; consistent with prior change pattern (vector-semantic-search `bd8673b`).

## Branch / PR State

- Branch: `main` (direct post-PR housekeeping; no PR)
- Baseline (post PR #10 squash): `bfa2db5`
- Final HEAD: `4c6b39b`
- Verify report observation: Engram #170 (FAIL — 1 CRITICAL + 3 WARNINGs + 2 SUGGESTIONs)

## Commits

- `4c6b39b` fix(cross-project-federation): pre-archive C1/W17/W18/W19 critical + warnings

## Findings closed

### C1 (CRITICAL) — REQ-27 alias transparent rewrite contract now delivers

**Spec contract** (`openspec/changes/cross-project-federation/spec.md:235-242`):
- Query for `flow-image-generator-v2` returns `flow-image-generator-main` rows when alias exists
- alias resolver rewrites `projects` BEFORE SQL
- returned observation's `project` field equals the canonical name

**Fix**: forward + reverse alias resolution in `mem_search_federated` (queries for `old` name resolve to `new`, AND queries for `new` name also match observations tagged with `old` name), plus result-level `project` field rewrite via shallow copy when alias matched.

### W17 — CHANGELOG v0.5.0 `Notes` section overclaim

**Before**: claimed alias resolution applied in `mem_search_federated, mem_search, and flow projects backfill` — but `mem_search` (single-project FTS5) never applied alias resolution.

**Fix**: dropped `mem_search` from the alias-surface claim; rewrote to describe the forward+reverse alias resolution in `mem_search_federated` + `flow projects backfill`.

### W18 — tasks.md T1.8..T1.13 acceptance checkboxes stale

**Before**: T1.8, T1.9, T1.10, T1.11, T1.13 acceptance bullets were `[ ]` (unchecked) despite the work shipping in batch C. Bookkeeping commit missed in batch C sub-agent's final pass.

**Fix (delivered in this archived batch)**: flipped all T1.8/T1.9/T1.10/T1.11/T1.13 acceptance bullets from `[ ]` to `[x]`; added `DONE (<hash>)` annotations to Commit lines.

### W19 — apply_tag contract drift

**Before**: spec REQ-24 said `apply_tag` SHALL return error dict when project is empty/whitespace; impl raised `ValueError`. Two deviations bundled.

**Fix**: changed `apply_tag` to return structured error dict `{"ok": bool, "error": str | None, "observation_id": int, "project": str}`; updated 3 unit tests:
- `test_apply_tag_success_returns_true` → asserts `result["ok"] is True`
- `test_apply_tag_observation_not_found_returns_false` → asserts `result["ok"] is False`
- `test_apply_tag_empty_project_raises` / `test_apply_tag_whitespace_project_raises` → renamed + asserts `result["ok"] is False` + `result["error"]` is non-empty

## LOC Delta

- `src/flow_engineering/engram_io.py`: +56/-22 (forward + reverse alias resolution; result-level rewrite; non-breaking for `mem_search`)
- `src/flow_engineering/project_detector.py`: +13/-9 (apply_tag returns dict instead of raising)
- `tests/unit/test_project_detector.py`: +24/-15 (3 tests updated to assert new contract)
- `CHANGELOG.md`: +2/-2 (W17 doc-accuracy fix in Notes section)
- Total: +95/-48 (+47 net)

## Test Delta

- Baseline: 699 (post batch C)
- Final: 699 (post W-fix; +0 tests but +C1 fix + W17/W18/W19 mechanical fixes)
- All 699/699 passing in 5.77s

## Risks / Blockers

- None — all 4 verify findings closed; verify re-run would now show PASS WITH WARNINGS only (no CRITICAL)

## Cross-impact

- Prior changes: no impact (REQ-1..22 contracts preserved; legacy `mem_search` byte-identical)
- Vector-semantic-search (REQ-17/22): tests still green (verified by full suite pass)

## Next

- sdd-archive cross-project-federation (this archive)
- change #5 graph-snapshots

**Session**: sdd-cross-project-federation-design-2026-06-26
**Topic**: sdd/cross-project-federation/w-fix-c1-w17-w18-w19
**Commit**: 4c6b39b
**Engram**: (synthesized from commit_message; this batch was the W-fix sidecar of verify-report #170)