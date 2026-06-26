<!-- Archived 2026-06-26 from sdd/vector-semantic-search/apply-progress-pr1-batch-c (Engram #146) -->

# Apply progress PR#1 batch C — vector-semantic-search

## Goal

SDD apply batch C of vector-semantic-search PR#1: T1.5 (hybrid scoring formula).

## Branch / PR State

- Branch: `feature/vector-semantic-search-pr1`
- Baseline (batch B HEAD): `1fe1f02`
- Final HEAD: `426e787`

## Commits

1. `8ce6368` test(unit): RED fixtures for hybrid scoring formula with worked example (`tests/unit/test_hybrid_backend.py` +454/-45)
2. `426e787` feat(backend): hybrid scoring with linear combo formula α·sim + (1−α)·normalize_bm25(fts) (`hybrid_backend.py` +125/-26, `test_hybrid_backend.py` +29/-24)

## LOC Delta (cumulative this batch)

- `src/flow_engineering/hybrid_backend.py`: +125/-26 (impl ~95 net, helpers + docstring)
- `tests/unit/test_hybrid_backend.py`: +483/-69 (~414 net: 2 fixtures, 1 replacement class, 6 new test classes)
- Total: +608/-95 = +513 net
- Compared to forecast ~190 LOC: 270% of forecast (test fixture vectors + 6 dedicated test classes are the bulk of the multiplier)

## Test Delta

- Baseline: 431 passing
- Final: **461 passing** (verified via `uv run pytest -x --tb=short` in 2.18s)
- Delta: **+30 tests** (5 in T1.4/5-replacement TestHybridBackendSearchImplementation + 7 TestHybridScoringWorkedExample + 6 TestHybridAlphaBoundaries + 2 TestHybridSemanticDelegation + 4 TestHybridEmptyAndEdgeCases + 6 TestNormalizeBm25Helper + 5 TestCosineSimHelper − 5 removed TestHybridBackendSearchDeferral)

## BDD Scenario Coverage

- REQ-18 scenario 1 (worked example obs1 0.98 > obs3 0.15 > obs2 0.125 within ±1e-3): ✅ verified at unit level (TestHybridScoringWorkedExample, 7 tests)
- REQ-18 scenario 2 (alpha=1.0 equals pure semantic): ✅ TestHybridAlphaBoundaries.test_hybrid_alpha_10_*
- REQ-18 scenario 3 (alpha=0.0 equals pure FTS): ✅ TestHybridAlphaBoundaries.test_hybrid_alpha_00_matches_pure_fts_ordering
- REQ-18 scenario 4 (alpha=1.5 raises ValueError): ✅ TestHybridAlphaBoundaries.test_hybrid_alpha_15_raises_value_error + negative + out-of-range variants
- REQ-18 scenario 5 (empty query returns [] no division-by-zero): ✅ TestHybridEmptyAndEdgeCases.test_empty_query_returns_empty_results + single + all-equal edge cases

All 5 REQ-18 scenarios covered at unit level. BDD feature file (T1.10) still pending in batch D.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| T1.5 | `8ce6368` (35 RED failures: 5 search-implementation + 7 worked example + 6 alpha boundaries + 2 semantic delegation + 4 edge cases + 6 normalize + 5 cosine) | `426e787` (all 49 in `test_hybrid_backend.py` pass; full suite 461/461) | Lint clean (ruff), mypy strict clean, dead code removed during GREEN pass |

## Implementation Notes

- Algorithm: validate alpha → `inner.mem_search` candidates (limit=2k) → if empty return [] → embed query+candidates in single batched call → cosine_sim per candidate → fts_score per candidate (obs["_fts_score"] seam or substring fallback) → min-max normalize → `hybrid = α·cos + (1-α)·norm_fts` → sort desc → top-k
- Helpers extracted as `@staticmethod` (_fts_score, _normalize_bm25, _cosine_sim) for direct unit testing
- Result dict shape: `observation_id`, `score`, `rank` (REQ-17 contract) + all inner obs fields (id, title, content, topic_key, type, scope, project, created_at, updated_at)
- Stable sort with insertion-order tiebreak preserves `inner.mem_search` ordering on tied scores → enables alpha=0.0 sanity check
- Epsilon path (1e-9) handles span=0 and zero-norm vectors → no ZeroDivisionError / NaN

## Test Fixture Pattern (for batch D reference)

- `FixedVectorsProvider`: pre-set unit-norm vectors keyed by exact text — used to control cosine sims in worked example
- `ScoredInMemoryBackend`: subclasses InMemoryBackend to attach `_fts_score` to mem_search results — used to control FTS scores without real FTS5
- Both fixtures are local to `test_hybrid_backend.py` — no production API surface change

## Risks / Blockers

None for batch C itself.

Workload note: batch C landed in ~6 min, well under the 15-min timeout risk threshold. Confirms the per-task batch strategy from batch B's lessons-learned.

## Next

- batch D: T1.6 (SqliteVecStore) + T1.7 (observability counters) + T1.8 (pyproject extras) + T1.9 (BDD req17) + T1.10 (BDD req18) — ~730 LOC, **HIGH TIMEOUT RISK**. Will split into D1+D2 if needed.
- batch D1 recommendation: T1.6 + T1.7 + T1.8 (storage + counters + pyproject) — cohesive infra, ~400 LOC
- batch D2 recommendation: T1.9 + T1.10 (BDD features for REQ-17 + REQ-18) — acceptance closure, ~410 LOC

**Session**: sdd-vector-semantic-search-explore-2026-06-26
**Topic**: sdd/vector-semantic-search/apply-progress-pr1-batch-c
**Engram**: #146
**Next**: Batch D1 (storage + counters + pyproject) or D2 (BDD features) — split recommended
