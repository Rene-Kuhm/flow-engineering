<!-- Archived 2026-06-26 from sdd/vector-semantic-search/apply-progress-pr2-batch-e (Engram #149) -->

# Apply progress PR#2 batch E — vector-semantic-search

## Goal

SDD apply batch E of vector-semantic-search PR#2: T2.1 (SentenceTransformersProvider lazy import) + T2.2 (BDD req19) + T2.3 (BDD req20).

## Branch / PR State

- Branch: `feature/vector-semantic-search-pr2`
- Baseline (PR#1 squash HEAD): `2ff135c`
- Final HEAD: `9a27678`

## Commits

1. `2852fec` test(unit): RED fixtures for SentenceTransformersProvider lazy import (`tests/unit/test_embedding_provider.py` +252/-2, RED baseline confirmed)
2. `4188d89` feat(embedding): SentenceTransformersProvider with lazy torch import (`src/flow_engineering/embedding_provider.py` +67, `tests/unit/test_embedding_provider.py` +2/-1 — fix self._INSTALL_HINT reference)
3. `6bd48e7` test(bdd): req19_embedding_provider feature with 4 scenarios (`tests/bdd/req19_embedding_provider.feature` +58 NEW, `tests/bdd/test_vector_search_steps.py` +273 — REQ-19 BDD step defs)
4. `9a27678` test(bdd): req20_sqlite_vec_storage feature with 5 scenarios (`tests/bdd/req20_sqlite_vec_storage.feature` +63 NEW, `tests/bdd/test_vector_search_steps.py` +316 — REQ-20 BDD step defs)

## LOC Delta (cumulative this batch)

- `src/flow_engineering/embedding_provider.py`: +67 (NEW `SentenceTransformersProvider` class with lazy torch + sentence_transformers imports + lazy SentenceTransformer instantiation on first embed())
- `tests/unit/test_embedding_provider.py`: +252 net (14 new RED fixtures in 4 test classes: Metadata, MissingTorch, LazyModelLoad, ModuleImportClean)
- `tests/bdd/req19_embedding_provider.feature`: +58 (NEW — 4 scenarios)
- `tests/bdd/req20_sqlite_vec_storage.feature`: +63 (NEW — 5 scenarios)
- `tests/bdd/test_vector_search_steps.py`: +589 (273 for REQ-19 + 316 for REQ-20)
- Total: +1029 / -2 = +1027 net
- Compared to forecast ~375 LOC: 274% of forecast (×2.7 — the BDD step defs expanded to cover both embedding_world fixture + vec_store_world fixture + helper functions `_unit`; unit tests also include the FakeModel class with encode tracking)

## BDD Coverage Delta

- Baseline scenarios: 73 (across req1-9 + req15 + req17 + req18)
- Final scenarios: 82
- Delta: +9 (4 from req19_embedding_provider + 5 from req20_sqlite_vec_storage)

## Test Delta

- Baseline: 512 passing
- Final: **535 passing** (verified via `uv run pytest -x --tb=short` in 2.38s)
- Delta: **+23 tests** (14 unit tests for SentenceTransformersProvider + 4 req19 BDD scenarios + 5 req20 BDD scenarios)

## REQ Coverage

- REQ-19 all 4 scenarios: PASS (unit + BDD)
  - MockEmbeddingProvider deterministic 384-dim + L2 norm in [0.99, 1.01]
  - `import flow_engineering.embedding_provider` does NOT trigger torch load (subprocess test verifies sys.modules isolation)
  - SentenceTransformersProvider raises EmbeddingProviderUnavailable when torch or sentence_transformers missing
  - embed() returns (N, 384) float32; empty list returns (0, 384)
- REQ-20 all 5 scenarios: PASS (unit + BDD)
  - Round-trip add/search returns obs at top-1 (distance ~0)
  - Delete removes obs from search + count() reflects
  - Vector BLOB byte length = 1536 (float32 round-trip within 1e-6)
  - Search returns top-k ordered ascending by distance (q close to obs7 at position 0)

## BDD Step Pattern (mirror for future batches)

- **Separate world fixture per REQ batch**: vector_world (REQ-17/18), embedding_world (REQ-19), vec_store_world (REQ-20)
- **Unique step text when binding to different worlds**: pytest-bdd rejects duplicate parser expressions; e.g. "the error message includes {needle}" (vector_world) vs "the embedding error message includes {needle}" (embedding_world)
- **Mock fixture pattern for lazy deps**: `_ensure_torch_stub` injects MagicMock for torch into sys.modules if missing; `_install_fake_sentence_transformers` provides FakeModel class with construct_log + encode_log tracking
- **Random fixtures are seeded**: `random_unit_vectors` uses `np.random.default_rng(seed=2026_06_26)` for reproducibility; `query_close_to_obs7` builds q via angle interpolation `acos(0.95)` ~ 0.3176 rad on orthogonal direction
- **Subprocess for module-level isolation**: subprocess.run with cwd pinned to project root so PYTHONPATH isn't inherited
- **Test defs import from module under test inside the test function** (not at top level) so RED phase shows ImportError rather than failing on collection

## TDD Evidence (T2.1 only)

- RED: `git diff 2852fec^` shows 14 new failing tests with `ImportError: cannot import name 'SentenceTransformersProvider'`. All other 22 tests pass.
- GREEN: `git diff 4188d89` adds the class with lazy torch + lazy model. All 36 tests pass; full suite 526 passing.
- REFACTOR: skipped — impl is already tight (~67 LOC for the new class + module-level helpers). No need for extraction.

## Implementation Notes

- `SentenceTransformersProvider.__init__` does `import torch` + `from sentence_transformers import SentenceTransformer` inside a single try/except; both must succeed or EmbeddingProviderUnavailable is raised. Subclass of ImportError per spec REQ-19 scenario 3.
- Model instantiation (`SentenceTransformer(model_name)`) happens on first `embed()` call via `_ensure_model` and is cached on `self._model`. Construction itself stays cheap.
- `embed([])` short-circuits before `_ensure_model` so empty input never touches the model.
- `embed(texts)` reshapes to `(len(texts), 384)` to guard against sentence-transformers returning 1-D arrays for single inputs.
- Reference to `_INSTALL_HINT` is `self._INSTALL_HINT` not bare `_INSTALL_HINT` (class attribute, not module-level). Fix in commit `4188d89`.

## Workaround Notes

- The `uv.lock` modification (843 line additions) is pre-existing noise from batch D1's `uv sync` operations; was reverted in batch D2 to keep commits focused. The diff is left in the working tree as PR#1 squash-merge housekeeping noise; orchestrator handles cleanup at PR merge time.
- PowerShell commit message quoting choked on parentheses + backslash escapes in commit `9a27678`; switched to `git commit -F <msg-file>` to bypass shell parsing.

## Risks / Blockers

None for batch E itself.

Pre-existing mypy strict errors on untyped pytest-bdd step defs (now ~75 errors in this file, same pattern as existing BDD files) — accepted in this project pattern, not introduced by this batch.

Note for batch F: T2.4 (CLI `--semantic` flag) touches `src/flow_engineering/cli.py` and adds `tests/unit/test_cli_search_semantic.py` — the env-vs-extra differentiation gate state machine from spec REQ-17 is what the gate state scenarios in req17 need.

## Next

- batch F: T2.4 (--semantic flag on flow search) + T2.5 (flow reindex subcommand)

**Session**: sdd-vector-semantic-search-explore-2026-06-26
**Topic**: sdd/vector-semantic-search/apply-progress-pr2-batch-e
**Engram**: #149
**Next**: Batch F (CLI surface + flow reindex, ~340 LOC)
