<!-- Archived 2026-06-26 from sdd/vector-semantic-search/apply-progress-pr1-batch-a (Engram #144) -->

# Apply progress PR#1 batch A — vector-semantic-search

## Goal

SDD apply batch A of vector-semantic-search PR#1: T1.1 (ABC extension) + T1.2 (InMemoryBackend default impls raising VectorSearchDisabled).

## Branch / PR State

- Branch: `feature/vector-semantic-search-pr1`
- Baseline: `cb7c6b5` (post decision-reality-drift archive)
- Final HEAD: `e0e648a`
- PR: not yet created (orchestrator will create after batch D)

## Commits

1. `3fbed98` feat(backend): add mem_search_semantic + mem_search_hybrid to EngramBackend ABC (1 file, +38/-1)
2. `457e4cc` test(unit): RED fixtures for InMemoryBackend vector search disabled (1 file, +56/-0)
3. `e0e648a` feat(backend): VectorSearchDisabled + InMemoryBackend default impls (1 file, +42/-0)

## LOC Delta (cumulative)

- `src/flow_engineering/engram_io.py`: +80 / -1 = +79 net
- `tests/unit/test_engram_io.py`: +56 / -0 = +56 net
- Total: +136 / -1 = +135 net

## Test Delta

- Baseline: 385
- Final: 390
- Delta: +5 (all in `tests/unit/test_engram_io.py::TestVectorSearchDisabled`)

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| T1.1 | (covered by T1.2) | N/A | ✅ 385/385 | ➖ N/A (ABC default) | ✅ 385/385 | ➖ N/A | ➖ None needed |
| T1.2 | `tests/unit/test_engram_io.py` | Unit | ✅ 385/385 | ✅ ImportError on VectorSearchDisabled | ✅ 390/390 | ✅ 5 cases | ➖ None needed |

### Test Summary

- **Total tests written**: 5
- **Total tests passing**: 390 (baseline 385 + 5 new)
- **Layers used**: Unit (5)
- **Approval tests** (refactoring): None — no refactoring tasks
- **Pure functions created**: 1 (VectorSearchDisabled.__init__)

## Risks / Blockers

None. All 5 new tests are real behavioral assertions: (1) semantic raises with hint substring, (2) hybrid raises with hint substring, (3) exception is RuntimeError subclass, (4) mem_search FTS5 regression unchanged, (5) no torch/sqlite_vec/sentence_transformers leaked via sys.modules introspection.

## Design Decisions Honored

- D1 (NON-BREAKING ABC): T1.1 added default methods that raise NotImplementedError at call-time only — third-party EngramBackend subclasses import and instantiate unchanged.
- D2 (HybridBackend composition): T1.1 is the foundation; HybridBackend lands in T1.4.
- REQ-17 activation gate: T1.2 exception message includes "pip install flow-engineering[vectors]" verbatim.

## Next

- batch B: T1.3 (EmbeddingProvider ABC + MockEmbeddingProvider) + T1.4 (HybridBackend scaffold)

**Session**: sdd-vector-semantic-search-explore-2026-06-26
**Topic**: sdd/vector-semantic-search/apply-progress-pr1-batch-a
**Engram**: #144
**Next**: Batch B (T1.3 + T1.4, ~290 LOC)
