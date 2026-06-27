<!-- Archived 2026-06-26 from sdd/cross-project-federation/apply-progress-batch-a (Engram #164) -->

# Apply progress batch A — cross-project-federation

## Goal

SDD apply batch A of cross-project-federation (single PR foundation): T1.1 (ABC v1.2) + T1.2 (InMemoryBackend.mem_search_federated) + T1.4 (BDD req23).

## Branch / PR State

- Branch: `feature/cross-project-federation`
- Baseline (setup commit HEAD): `3886380`
- Final HEAD: `6076aba`
- Status: working tree clean
- PR: not yet created (batch B + C still pending)

## Commits

1. `8d158d1` feat(backend): add mem_search_federated to EngramBackend ABC v1.2 (NON-BREAKING default) — engram_io.py +35/-4
2. `5cbcd26` test(unit): RED fixtures for InMemoryBackend.mem_search_federated with project/since/type filters — test_engram_io.py +187
3. `6b2818d` feat(backend): InMemoryBackend.mem_search_federated with project/since/type filters — engram_io.py +45
4. `6076aba` test(bdd): req23_federated_search feature with 5 scenarios + step glue — req23_federated_search.feature +44 + test_cross_project_federation_steps.py +331

## LOC Delta

- `src/flow_engineering/engram_io.py`: +84 (ABC +35, InMemoryBackend +45, class docstring +4)
- `tests/unit/test_engram_io.py`: +187 (TestFederatedSearch class with 9 tests)
- `tests/bdd/req23_federated_search.feature`: +44 (NEW)
- `tests/bdd/test_cross_project_federation_steps.py`: +331 (NEW)
- Total: +642 (excluding deleted 4 lines)

## Test Delta

- Baseline: 576
- Final: 590
- Delta: +14 (9 unit + 5 BDD)

## BDD Coverage Delta

- +5 scenarios (req23_federated_search.feature)
- Final: 92 across 18 feature files (was 87 across 17)

## Risks / Blockers

- none

## Learnings

- pytest-bdd parser confusion: step text `every result has type in {"decision", "bugfix"}` triggers parser to interpret `{allowed}` as a set-of-chars. Workaround: use plain English `every result has type decision or bugfix` without curly braces.
- pytest-bdd step keyword match: the step `the error message includes "..."` must match the EXACT phrase registered via `parsers.parse(...)`. Mismatched word (e.g., "mentions" vs "includes") fails silently with StepDefinitionNotFoundError.
- ABC v1.2 default raising NotImplementedError works as designed: third-party subclass test verifies both the error type and the message contains "v1.2" (callers can identify which ABC version they need to upgrade against).
- InMemoryBackend.mem_search_federated uses substring match (mirrors mem_search) so unit tests don't need SQLite FTS5. Empty projects=[] raises ValueError (chose explicit fail-fast per design D1).
- T1.4 step def file naming: per locked spec #161, used `test_cross_project_federation_steps.py` (not `test_federation_steps.py` from user prompt). Batches B and C will extend this single file with REQ-24/25/26/27 step glue.

## Next

- batch B: T1.3 (project_detector) + T1.5 (BDD req24) + T1.6 (CLI --federated) + T1.7 (BDD req25) + T1.12 (CLI flow projects backfill) — ~730 LOC, HIGH timeout risk. Will split into B1+B2 if needed.

**Session**: sdd-cross-project-federation-design-2026-06-26
**Topic**: sdd/cross-project-federation/apply-progress-batch-a
**Engram**: #164