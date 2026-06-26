<!-- Archived 2026-06-26 from sdd/vector-semantic-search/verify-report (Engram #152) -->

# sdd/vector-semantic-search/verify-report

## Status

**PASS WITH WARNINGS**

## Date

2026-06-26

## Mode

Strict TDD (`uv run pytest`); main HEAD `b2f136c` (PR#2 squash merge); PR#1 squash `2ff135c`

## Test Execution

| Suite | Count | Time | Exit |
|---|---|---|---|
| Full pytest (`-x --tb=short`) | **572 passed** | 5.08s | 0 |
| BDD subset (`tests/bdd/ -v`) | **87 passed** | 2.69s | 0 |
| vector-search unit slice (8 files) | 173 passed | <1s | 0 |
| decision-reality-drift slice (REQ-9..16) | 76 passed | 0.40s | 0 |
| decision-code-linking slice (REQ-1..8) | 73 passed | 0.38s | 0 |

- Delta from PR#1 baseline (385): +187
- Delta from PR#2 baseline (502): +70
- BDD scenarios: **87 across 17 feature files** (5+5+4+5+5 = 24 new for vector-semantic-search; 63 from prior changes)

## REQ Coverage

| REQ | Title | Tests | Status |
|-----|-------|-------|--------|
| REQ-17 | semantic search activation gate | `tests/bdd/req17_semantic_search.feature` (5) + `tests/unit/test_engram_io.py::TestVectorSearchDisabled` (5) + `tests/unit/test_cli_search_semantic.py` (8 classes) | ✓ COMPLIANT |
| REQ-18 | hybrid scoring formula | `tests/bdd/req18_hybrid_scoring.feature` (5) + `tests/unit/test_hybrid_backend.py` (TestHybridScoringWorkedExample, TestHybridAlphaBoundaries, TestHybridEmptyAndEdgeCases, TestNormalizeBm25Helper, TestCosineSimHelper — ~30 cases) | ✓ COMPLIANT |
| REQ-19 | EmbeddingProvider ABC + lazy | `tests/bdd/req19_embedding_provider.feature` (4) + `tests/unit/test_embedding_provider.py` + `tests/unit/test_embedding_provider_embed_batch.py` (10) | ✓ COMPLIANT |
| REQ-20 | sqlite-vec storage | `tests/bdd/req20_sqlite_vec_storage.feature` (5) + `tests/unit/test_sqlite_vec_store.py` (7 classes including RoundTrip/Delete/Count/BlobSize/TopK/ImportSafety/PackageExports) | ✓ COMPLIANT |
| REQ-21 | `flow reindex` | `tests/bdd/req21_reindex.feature` (5) + `tests/unit/test_cli_reindex.py` (8 classes including Empty/Progress/Idempotent/DryRun/CrashResume/ExtraMissing/Counters/ModuleImportClean) | ✓ COMPLIANT |
| REQ-22 | observability counters | `tests/unit/test_observability_vectors.py` (6 classes: TestVectorCounterNaming/TestVectorSearchInvokedCounter/TestVectorSearchLatencyCounter/TestReindexCounters/TestRecordVectorSummaryContract/TestHybridBackendCounterIntegration) — **NO BDD feature file** | ⚠ PARTIAL — unit-only; spec promised `req22_vector_observability.feature` (4 scenarios) but file was never created (see W11) |

**Compliance summary**: 5/6 REQs fully covered at BDD layer; REQ-22 unit-only (spec drift).

All 6 `VECTOR_COUNTER_NAMES` in `src/flow_engineering/observability.py:63-70` match the REQ-22 contract:

- `vector_search_invoked_total{trigger=cli|programmatic}` ✓
- `vector_search_results_returned_total` ✓
- `vector_search_latency_ms` ✓
- `vector_index_size_observations` ✓
- `reindex_observations_total` ✓
- `reindex_duration_seconds` ✓

Naming follows REQ-8 convention (`subject_event_total` / `subject_latency_ms` / `subject_duration_seconds`) — verified in `observability.py:60-77` docstring and `VECTOR_COUNTER_NAMES` array.

## Task Closure

| Task | Title | Commit | Status |
|------|-------|--------|--------|
| T1.1 | Add 2 abstract methods to `EngramBackend` ABC v1.1 | `3fbed98` (squashed into `2ff135c`) | ✓ |
| T1.2 | VectorSearchDisabled + InMemoryBackend default impls | `457e4cc` + `e0e648a` (squashed into `2ff135c`) | ✓ |
| T1.3 | EmbeddingProvider ABC + MockEmbeddingProvider | `5488fdb` + `44c8402` (squashed into `2ff135c`) | ✓ |
| T1.4 | HybridBackend composition wrapper | `61036b8` + `1fe1f02` (squashed into `2ff135c`) | ✓ |
| T1.5 | Hybrid scoring formula | `8ce6368` + `426e787` (squashed into `2ff135c`) | ✓ |
| T1.6 | SqliteVecStore | `c7331e6` + `f791fcf` (squashed into `2ff135c`) | ✓ |
| T1.7 | 6 observability counters | `9651908` + `fae1825` (squashed into `2ff135c`) | ⚠ — see W11 (no BDD feature file) |
| T1.8 | `[vectors]` pyproject extra | `6bce6d9` (squashed into `2ff135c`) | ✓ (but see W10, W12) |
| T1.9 | BDD req17_semantic_search | `ffe2f25` (squashed into `2ff135c`) | ✓ |
| T1.10 | BDD req18_hybrid_scoring | `39c508e` (squashed into `2ff135c`) | ✓ |
| T2.1 | SentenceTransformersProvider lazy torch | `2852fec` + `4188d89` (squashed into `b2f136c`) | ✓ |
| T2.2 | BDD req19_embedding_provider | `6bd48e7` (squashed into `b2f136c`) | ✓ |
| T2.3 | BDD req20_sqlite_vec_storage | `9a27678` (squashed into `b2f136c`) | ✓ |
| T2.4 | `--semantic` / `--hybrid` / `--alpha` / `--k` flags | `7d07902` + `2f27c0f` (squashed into `b2f136c`) | ✓ |
| T2.5 | `flow reindex` subcommand | `20ce798` + `a6bd6f1` (squashed into `b2f136c`) | ✓ |
| T2.6 | BDD req21_reindex | `543bea7` (squashed into `b2f136c`) | ✓ |
| T2.7 | CHANGELOG v0.4.0 + 6 SKILL.md vector hooks | `29db214` + runtime SKILL.md side effects | ⚠ — see W9, W10 (CHANGELOG inaccuracy) |

**Closure summary**: 15/17 tasks cleanly complete; 2 tasks flagged (T1.7 missing BDD layer; T2.7 CHANGELOG inaccuracies). All have passing code+unit tests; both gaps are documentation/coverage, not behavioral.

## CHANGELOG Accuracy Check

| Claim | Source | Reality | Match? |
|-------|--------|---------|--------|
| `572 / 572 tests passing` | CHANGELOG.md:22 | 572/572 passing in 5.08s | ✓ match |
| `28 new BDD scenarios across 5 feature files` | CHANGELOG.md:23 | **24 new** (req17: 5, req18: 5, req19: 4, req20: 5, req21: 5) | ❌ **MISMATCH** (W9) |
| `Total BDD: 91 scenarios across 17 feature files` | CHANGELOG.md:23 | **87 total across 17** (63 prior + 24 new) | ❌ **MISMATCH** (W9) |
| Counter names listed | CHANGELOG.md:17 | All 6 match `VECTOR_COUNTER_NAMES` | ✓ match |
| REQs claimed (REQ-17..22) | CHANGELOG.md:10-19 | Spec defines REQ-17..22 | ✓ match |
| `[vectors]` extra: `sqlite-vec>=0.1.0,<0.2`, `sentence-transformers>=3.0`, `torch>=2.1` | CHANGELOG.md:16 | pyproject.toml:39-42 has `sqlite-vec>=0.1.0,<0.2`, `sentence-transformers>=2.0` (no torch declared in `[vectors]` extra — torch installed separately per pyproject comment) | ❌ **MISMATCH** (W10) |
| `[vectors]` extra pins `sqlite-vec<0.2` | CHANGELOG.md:29 | pyproject.toml:40 confirms | ✓ match |
| ABC v1.1, NON-BREAKING defaults | CHANGELOG.md:13, 28 | `engram_io.py:53-60` docstring + `VectorSearchDisabled` class | ✓ match |

## Documentation Check

| Artifact | Status | Evidence |
|----------|--------|----------|
| `sdd-verify/SKILL.md` Step 6a sub-step | ✓ PRESENT | `sdd-verify/SKILL.md` size 6457 bytes; Step 6a lines 58-63 cover drift detection hook; Vector search hook at line 91 |
| 6 SKILL.md `## Vector search hook` sections | ✓ ALL 6 PRESENT | Confirmed via grep: sdd-propose (1, 9273 bytes), sdd-design (1, 8706 bytes), sdd-tasks (1, 12768 bytes), sdd-apply (1, 13152 bytes), sdd-verify (1, 6457 bytes), sdd-archive (1, 8332 bytes) |
| SKILL.md contents naming REQ-17..22 | ✓ CONFIRMED | sdd-verify/SKILL.md line 93 references "REQ-17..22" |

## Cross-Impact Non-Regression

| Check | Status | Evidence |
|-------|--------|----------|
| `mem_search` (FTS5) unchanged | ✓ | REQ-17 BDD scenario "mem_search (FTS5) still works unchanged when vectors disabled" PASSED; `test_inmemory_mem_search_still_works_unchanged` PASSED |
| `EngramBackend` ABC backward compat (third-party subclass import unchanged) | ✓ | Default methods on `EngramBackend` raise `NotImplementedError` at call-time only (`engram_io.py:97-99`, `113-115`); existing 4 test_decision_drift / 4 test_engram_io_code_refs / 6 test_observability / 7 test_binding / 7 test_backfill / 5 test_graphify_query / etc. all pass without modification |
| decision-reality-drift REQs (9-16) still passing | ✓ | 76 passed across `test_decision_drift.py` + `test_daemon_drift_events.py` + `test_cli_drift.py` + `test_cli_watch_drift.py` + `test_decision_reality_drift_steps.py`; drift uses id lookup (embedding-agnostic) per spec.md cross-impact table |
| auto_suggest_code_refs (REQ-6) unchanged | ✓ | `test_auto_suggest.py` (18 tests) + `test_engram_io_code_refs.py` (20 tests) + `test_cli_inspect.py` (28 tests) all pass; REQ-6 seam preserved (no semantic rerank in v1 per spec.md out-of-scope) |
| `binding.split_prose_and_refs` consumed by reindex | ✓ | `cli.py:621` calls `split_prose_and_refs(content)` before embedding — embed-text seam honored per design.md D1 + spec.md cross-impact table |

## CRITICAL findings

**None.** All 572 tests pass. All 6 REQs have covering tests. All 17 tasks have implementation. No behavioral gaps. No test failures. No spec violations that block the contract.

## WARNING findings

### W9 — CHANGELOG v0.4.0 BDD scenario count is inflated (2 mismatches in one line)

- **CHANGELOG.md:23** claims "28 new BDD scenarios across 5 feature files" → actual: **24** (5+5+4+5+5)
- **CHANGELOG.md:23** claims "Total BDD: 91 scenarios across 17 feature files" → actual: **87** (63 prior + 24 new)
- **Root cause**: spec.md plan said 28 scenarios across 6 feature files (including req22 with 4 scenarios). apply-progress #147 (PR#1 batch D1) confirmed T1.7 acceptance criteria for req22 BDD feature file but **the file was never created** (see W11). The CHANGELOG counted the planned-but-not-shipped 4 req22 scenarios.
- **Severity**: WARNING (documentation accuracy; user-visible count is wrong by 4 scenarios)
- **Pre-archive fix**: Either (a) edit CHANGELOG.md:23 to say "24 new BDD scenarios across 5 feature files ... Total BDD: 87 scenarios across 17 feature files", or (b) add the missing req22 BDD feature file with 4 scenarios.
- **Recommendation**: (a) is faster and consistent with the actual delivered scope; (b) closes the spec drift but is more work.

### W10 — CHANGELOG v0.4.0 `[vectors]` extra contents inaccurate

- **CHANGELOG.md:16** claims `[vectors]` extra contains `sqlite-vec>=0.1.0,<0.2`, `sentence-transformers>=3.0`, `torch>=2.1`
- **Actual `pyproject.toml:39-42`**: `vectors = ["sqlite-vec>=0.1.0,<0.2", "sentence-transformers>=2.0"]` — **no torch declared** in the extra
- **Why**: design D5 + spec REQ-17 both say torch must be importable when `[vectors]` is installed. The implementation honors this by (a) lazy-importing torch inside `SentenceTransformersProvider.__init__` (`embedding_provider.py:162-168`), AND (b) documenting in `pyproject.toml:36-38` that users should install torch separately with `pip install --index-url https://download.pytorch.org/whl/cpu torch` to avoid the 800MB CUDA bundle from PyPI.
- **Severity**: WARNING (documentation accuracy; CHANGELOG overstates the extra's contents)
- **Pre-archive fix**: Edit `CHANGELOG.md:16` to read: "`[vectors]` optional extra in `pyproject.toml` (`sqlite-vec>=0.1.0,<0.2`, `sentence-transformers>=2.0`). Default install pulls ZERO heavy deps. `torch` is installed separately per `pyproject.toml:36-38` (CPU-only index) before the first `flow reindex`."

### W11 — REQ-22 BDD feature file not created (spec drift)

- **Spec plan** (`spec.md:353` and `tasks.md:204-218`): `tests/bdd/req22_vector_observability.feature` (4 scenarios from REQ-22)
- **Actual**: No `req22_vector_observability.feature` exists on disk. REQ-22 is covered only at the unit-test layer via `tests/unit/test_observability_vectors.py` (6 test classes: TestVectorCounterNaming, TestVectorSearchInvokedCounter, TestVectorSearchLatencyCounter, TestReindexCounters, TestRecordVectorSummaryContract, TestHybridBackendCounterIntegration).
- **Cross-confirmation**: `apply-progress #147` T1.7 acceptance line says "HybridBackend integration verified via TestHybridBackendCounterIntegration" but does NOT confirm the BDD feature file was created.
- **Severity**: WARNING (spec drift; 4 acceptance scenarios at BDD layer replaced by 6 unit-test classes). The contract is met; the coverage layer diverges from spec.
- **Pre-archive fix**: Either (a) add `tests/bdd/req22_vector_observability.feature` with 4 scenarios (mirrors req18 pattern), or (b) accept unit-test coverage and update spec/tasks.md to note the deviation.
- **Recommendation**: (a) is preferable since spec.md + tasks.md both explicitly required the BDD file; closing the spec gap is the right move before archive.

### W12 — `pyproject.toml` version still 0.1.0 (known follow-up)

- `pyproject.toml:3`: `version = "0.1.0"`
- CHANGELOG.md ships v0.4.0 entry as the current release
- **tasks.md open follow-up #2** explicitly defers this to sdd-archive: "Bump pyproject.toml version 0.1.0 → 0.4.0 (matches CHANGELOG entry)"
- **Severity**: WARNING (known, deferred, documented). Not blocking.
- **Pre-archive fix**: Edit `pyproject.toml:3` to `version = "0.4.0"`. Mechanical.

### W13 — Mypy strict: 2 NEW errors introduced by `trigger` kwarg

- `cli.py:571` — `Unexpected keyword argument "trigger" for "mem_search_hybrid" of "EngramBackend"`
- `cli.py:573` — `Unexpected keyword argument "trigger" for "mem_search_semantic" of "EngramBackend"`
- **Cause**: `HybridBackend.mem_search_hybrid` and `mem_search_semantic` accept a `*, trigger="programmatic"` kwarg for observability tagging, but the ABC base methods on `EngramBackend` (`engram_io.py:87-116`) do NOT have this kwarg. CLI calls them on `_default_save_backend()` (typed as `EngramBackend`), so mypy strict rejects the kwarg.
- **Tests pass**: 572/572 because tests use concrete `HybridBackend` instances, not the ABC type.
- **Severity**: WARNING (quality issue; not blocking). The "trigger" kwarg is a real observability contract — should either (a) be added to the ABC default methods, or (b) `cli.py` should narrow the type to `HybridBackend` for the dispatch path.
- **Pre-archive fix**: Either (a) widen the ABC signature to accept the trigger kwarg, or (b) cast/narrow the backend type in cli.py. Both are ~5 LOC.

### W14 — Ruff: 15 stylistic warnings in vector-semantic-search files

- 1× I001 (`cli.py:310` import sort) — fixable
- 2× N818 (exception naming `EmbeddingProviderUnavailable` and `VectorSearchDisabled` should have `Error` suffix per PEP 8) — **public API; renaming breaks callers** → likely acceptable
- 1× RET504 (unnecessary `arr =` assignment before `return` in `embedding_provider.py:193`) — fixable
- 1× W292 (no newline at EOF in `embedding_provider.py:202`) — fixable
- 1× F821 (`DriftReport` undefined in `observability.py:249`) — **pre-existing**, import inside function body to avoid cycle
- 1× UP037 (quoted type annotation `observability.py:249`) — pre-existing, mirrors F821
- ~8× A002 (`type` / `id` builtin shadowing) — pre-existing convention matching engram MCP API
- **Severity**: WARNING (style, not blocking). 4 are pre-existing.
- **Pre-archive fix**: Optional — none of these block archive.

### W15 — tasks.md acceptance checkboxes not flipped to [x]

- `openspec/changes/vector-semantic-search/tasks.md` still shows `- [ ]` for every acceptance criterion across all 17 tasks, even though all 17 tasks are completed and shipped in code.
- **Cause**: apply batches A through G each had explicit "mark task complete" commits (`3fbed98` T1.1, `457e4cc` T1.2, ..., `82e7fd0` T1.9+T1.10, `060b6dc` T2.4+T2.5, `ad43a30` T2.6+T2.7) but the `tasks.md` checkbox flipping did NOT happen as expected. Looking at task list directly: the `[ ]` markers remain.
- **Severity**: WARNING (documentation gap; readers can't tell tasks.md is "all done" at a glance)
- **Pre-archive fix**: Mechanical search-replace `- [ ]` → `- [x]` across `tasks.md`. ~30s of work.

### W16 — `uv.lock` dirty in working tree (843 line additions unstaged)

- `git status` shows `uv.lock` modified but not staged/committed
- Per apply-progress #148 (PR#1 batch D2): the noise is from PR#1 batch D1's `uv sync` operations; was reverted before committing batch D2 to keep commits focused. Reappeared in PR#2 batches.
- **Severity**: WARNING (housekeeping; orchestrator handles at merge time per the apply-progress pattern)
- **Pre-archive fix**: `git checkout uv.lock` to discard, or commit the noise as a chore commit. Either is fine.

## SUGGESTION findings

### S3 — T1.7 acceptance criterion referenced `vector_search_missing_embedding_total` counter that was never implemented

- `tasks.md:171`: "Counter `vector_search_missing_embedding_total` increments when semantic hits an obs without embedding (D11)"
- `observability.py` does NOT define this counter (only 6 counters in `VECTOR_COUNTER_NAMES`, none named this)
- **Spec REQ-22** also does NOT mention this counter (spec.md line 22-25 lists only the 6 counters in the table)
- **Severity**: SUGGESTION (internal task-tracking artifact; the counter was a nice-to-have from design D11 that wasn't required by REQ-22). No spec violation.
- **Recommendation**: Remove the bullet from tasks.md T1.7 acceptance criteria or note as "deferred — not in REQ-22".

### S4 — REQ-18 worked-example obs2 score in spec differs from impl math

- **Spec.md:96** says obs2 score ≈ 0.00 with FTS scores (0.85, 0.40).
- **Actual implementation** (`hybrid_backend.py:184-233` + tests in `test_hybrid_backend.py::TestHybridScoringWorkedExample`): obs2 score = **0.125** with FTS scores (0.50, 0.20, 0.10).
- **Math reconciliation** (per apply-progress #148): `normalize_bm25(0.20) = (0.20 − 0.10) / (0.50 − 0.10) = 0.25`; `hybrid = 0.5·0.0 + 0.5·0.25 = 0.125` (correct given the FTS inputs).
- **Spec example inputs are inconsistent** with the stated result. The spec says "obs1 ≈ 0.96, obs3 ≈ 0.39, obs2 ≈ 0.00" but the FTS scores (0.85, 0.40) only produce obs2 = 0.00 — which means a different prose corpus was assumed in the worked example vs the BDD step defs.
- **Severity**: SUGGESTION (spec/impl drift on a worked example; math is internally consistent in implementation).
- **Recommendation**: Update spec.md:96 to use the actual FTS scores from the BDD test fixture (0.50, 0.20, 0.10), or accept the existing spec wording as illustrative and note the actual test fixtures differ.

### S5 — 8 ruff `A002` builtin-shadowing warnings are pre-existing project convention

- These match the engram MCP API parameter naming (`type`, `id`); not new in this change. Carry-forward from decision-code-linking verify-report #118 (S4 there).
- No fix needed.

## Verdict

**ARCHIVE (PASS WITH WARNINGS)** — but recommend applying W9 + W10 pre-archive (both are one-line CHANGELOG edits that close the user-visible count and extra-claims inaccuracies).

Rationale:

- All 572 tests pass; 0 failures, 0 errors.
- All 6 REQs have covering tests; REQ-22 is unit-only (W11) but covers the contract.
- All 17 tasks have implementation + tests; documentation lag (W15) is mechanical.
- All 6 prior changes' contracts preserved (FTS5, ABC compat, drift detector, auto-suggest).
- 5 documentation-class WARNINGS (W9, W10, W11, W12, W15) — none block archive.
- 2 quality-class WARNINGS (W13 mypy, W14 ruff) — non-blocking, ~10 LOC total to fix.
- 1 housekeeping WARNING (W16 uv.lock noise) — pre-existing pattern.
- 3 SUGGESTION findings — cleanups, not blockers.

## Verification Artifacts

- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-pytest.log` — full pytest output (572 passed in 5.08s)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-bdd.log` — BDD-only output (87 passed in 2.69s)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-vector-bdd.log` — vector_search_steps.py (24 passed)
- `C:\Users\insyd\AppData\Local\Temp\opencode\verify-unit-vector.log` — 8 vector-semantic-search unit test files (173 passed)
- `C:\Users\insyd\AppData\Local\Temp\opencode\ruff-vector.log` — ruff lint output (15 warnings)
- `C:\Users\insyd\AppData\Local\Temp\opencode\mypy-vector.log` — mypy strict output (19 errors)
- `C:\Users\insyd\AppData\Local\Temp\opencode\skill_check.ps1` — SKILL.md hook verification script

## Relevant Files

- `C:\dev\proyects\flow-engineering\src\flow_engineering\engram_io.py` — REQ-17 (VectorSearchDisabled class line 35, InMemoryBackend overrides lines 223-245, ABC v1.1 methods lines 87-116)
- `C:\dev\proyects\flow-engineering\src\flow_engineering\hybrid_backend.py` — REQ-18 (linear combo formula, lines 184-233), REQ-22 observability wiring (lines 169-182)
- `C:\dev\proyects\flow-engineering\src\flow_engineering\embedding_provider.py` — REQ-19 (EmbeddingProvider ABC, MockEmbeddingProvider, SentenceTransformersProvider with lazy torch)
- `C:\dev\proyects\flow-engineering\src\flow_engineering\vectors\sqlite_vec_store.py` — REQ-20 (observation_embeddings + vec_observations tables, atomic add/delete)
- `C:\dev\proyects\flow-engineering\src\flow_engineering\observability.py` — REQ-22 (VECTOR_COUNTER_NAMES lines 63-70, record_vector_summary lines 295-343)
- `C:\dev\proyects\flow-engineering\src\flow_engineering\cli.py` — REQ-17 CLI surface (flow search --semantic lines 446-581), REQ-21 (flow reindex lines 584-720)
- `C:\dev\proyects\flow-engineering\pyproject.toml` — [vectors] extra (lines 39-42; version 0.1.0 at line 3 — see W12)
- `C:\dev\proyects\flow-engineering\CHANGELOG.md` — v0.4.0 entry (lines 7-32; see W9, W10)
- `C:\dev\proyects\flow-engineering\openspec\changes\vector-semantic-search\spec.md` — REQ-17..22 (382 lines)
- `C:\dev\proyects\flow-engineering\openspec\changes\vector-semantic-search\design.md` — D1-D11
- `C:\dev\proyects\flow-engineering\openspec\changes\vector-semantic-search\tasks.md` — 17 tasks (acceptance checkboxes not flipped — see W15)
- `C:\dev\proyects\flow-engineering\tests\bdd\req{17,18,19,20,21}_*.feature` — 24 new BDD scenarios across 5 feature files
- `C:\dev\proyects\flow-engineering\tests\bdd\test_vector_search_steps.py` — pytest-bdd step glue for the 24 scenarios
- `C:\dev\proyects\flow-engineering\tests\unit\test_engram_io.py` — TestVectorSearchDisabled (5 tests)
- `C:\dev\proyects\flow-engineering\tests\unit\test_hybrid_backend.py` — 39 tests (REQs 17/18)
- `C:\dev\proyects\flow-engineering\tests\unit\test_embedding_provider.py` — 32 tests (REQ-19)
- `C:\dev\proyects\flow-engineering\tests\unit\test_embedding_provider_embed_batch.py` — 10 tests (REQ-19 + REQ-21 batched embed)
- `C:\dev\proyects\flow-engineering\tests\unit\test_sqlite_vec_store.py` — 21 tests (REQ-20)
- `C:\dev\proyects\flow-engineering\tests\unit\test_observability_vectors.py` — 20 tests (REQ-22; only unit coverage)
- `C:\dev\proyects\flow-engineering\tests\unit\test_cli_search_semantic.py` — 14 tests (REQ-17 CLI)
- `C:\dev\proyects\flow-engineering\tests\unit\test_cli_reindex.py` — 8 tests (REQ-21)
- `C:\Users\insyd\.config\opencode\skills\sdd-{propose,design,tasks,apply,verify,archive}\SKILL.md` — 6 runtime Vector search hook sections

**Session**: flow-engineering-vector-semantic-search-verify-2026-06-26
**Topic**: sdd/vector-semantic-search/verify-report
**Next**: Apply W9 + W10 CHANGELOG fixes, then sdd-archive vector-semantic-search; then change #4 cross-project-federation. If W11 (REQ-22 BDD file) is also desired, add it before archive.
