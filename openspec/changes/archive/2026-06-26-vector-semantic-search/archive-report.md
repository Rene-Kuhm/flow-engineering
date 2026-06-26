# Archive Report — vector-semantic-search

## Status

**ARCHIVED** (2026-06-26)

SDD cycle complete: propose → design → spec → tasks → apply (PR#1 #8 + PR#2 #9) → verify (PASS WITH WARNINGS, 0 critical) → W-fix PR (`bd8673b`) → archive.

## Changelog

- `CHANGELOG.md` v0.4.0 entry (post W9/W10/W12/W15 doc-accuracy fixes in commit `bd8673b`)

## Files Created / Moved

### Moved to archive (renamed with git-detected 100%)

- `openspec/changes/vector-semantic-search/explore.md` → `openspec/changes/archive/2026-06-26-vector-semantic-search/explore.md` (mirrored from Engram #139; not present in active folder)
- `openspec/changes/vector-semantic-search/proposal.md` → archive
- `openspec/changes/vector-semantic-search/design.md` → archive
- `openspec/changes/vector-semantic-search/spec.md` → archive
- `openspec/changes/vector-semantic-search/tasks.md` → archive (all 17 tasks marked `[x]` per W15 fix in `bd8673b`)

### Created (new in repo)

- `openspec/changes/archive/2026-06-26-vector-semantic-search/verify-report.md` (copy from Engram #152)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/apply-progress/pr1-batch-a.md` (Engram #144)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/apply-progress/pr1-batch-b.md` (Engram #145)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/apply-progress/pr1-batch-c.md` (Engram #146)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/apply-progress/pr1-batch-d1.md` (Engram #147)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/apply-progress/pr1-batch-d2.md` (Engram #148)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/apply-progress/pr2-batch-e.md` (Engram #149)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/apply-progress/pr2-batch-f.md` (Engram #150)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/apply-progress/pr2-batch-g.md` (Engram #151)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/apply-progress/pr2-batch-w11.md` (Engram #153)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/archive-report.md` (this file)

## PRs merged

- **#8**: feat(vector-semantic-search): PR#1 - core hybrid backend + embedding pipeline (REQ-18, 19, 20, 22) — squash `2ff135c`
- **#9**: feat(vector-semantic-search): PR#2 - CLI surface + reindex + CHANGELOG v0.4.0 (REQ-17, REQ-21) — squash `b2f136c`
- **Post-archive housekeeping** (direct to main):
  - `d19383b` test(bdd): req22_vector_observability feature (W11 from verify)
  - `bd8673b` fix(vector-semantic-search): pre-archive W-fixes W9/W10/W12/W13/W15/W16

## Test summary

- 385/385 unit tests passing (PR#1 start) → 502 (PR#1 end) → 535 (PR#2 batch E) → 567 (PR#2 batch F) → 572 (PR#2 batch G) → **576 (post-W-fixes, +4 BDD req22)**
- 91 BDD scenarios across 18 feature files (req17, req18, req19, req20, req21, req22 added — REQ-22 added post-archive via `d19383b`)
- All 17 tasks closed (T1.1..T1.10 PR#1 + T2.1..T2.7 PR#2)
- Verified post-archive: `576 passed in 5.20s` (`uv run pytest`)

## Capability Mapping Decision

**No `openspec/specs/` baseline existed in this project** — verified by `Get-ChildItem openspec -Recurse`. The project uses `openspec/changes/` as the sole spec store, so no delta merge into capability specs was performed (same precedent as archive-reports #119 and #136).

The 6 REQs (REQ-17..REQ-22) live in the archived spec.md as one capability ("vector-semantic-search") rather than being split across `openspec/specs/{semantic-search,hybrid-scoring,embedding-provider,sqlite-vec-storage,reindex-cli,vector-observability}/spec.md`. If/when `openspec/specs/` is initialized post-archive, the archive spec is the importable source.

## Carry-forwards (WARNINGS from verify — all RESOLVED pre-archive)

| ID | Status | Resolution |
|----|--------|------------|
| W9 (CHANGELOG BDD counts wrong) | resolved | commit `bd8673b` |
| W10 (CHANGELOG [vectors] extra overstated) | resolved | commit `bd8673b` |
| W11 (REQ-22 BDD missing) | resolved | commit `d19383b` (separate BDD add) |
| W12 (pyproject version 0.1.0 vs 0.4.0) | resolved | commit `bd8673b` |
| W13 (mypy strict on `trigger=` kwarg) | resolved | commit `bd8673b` |
| W14 (ruff stylistic warnings) | non-blocking | optional, no fix needed |
| W15 (tasks.md checkboxes [ ] not [x]) | resolved | commit `bd8673b` |
| W16 (uv.lock noise) | resolved | commit `bd8673b` (committed as part of W-fix) |

## Suggestions (carry-forwards, non-blocking)

- **S3** T1.7 acceptance criterion referenced `vector_search_missing_embedding_total` counter that was never implemented — spec REQ-22 also does NOT mention it; remove from tasks.md or note "deferred — not in REQ-22". Owner: optional cleanup.
- **S4** REQ-18 worked-example obs2 score in spec (0.00) differs from impl math (0.125) — spec example inputs are inconsistent with stated result. Owner: spec delta sync or `vector-search-hardening`.
- **S5** 8 ruff `A002` builtin-shadowing warnings are pre-existing project convention. No fix needed.

## Out-of-scope reminders (carried from tasks.md)

- `auto_suggest_code_refs` rerank with semantic similarity — REQ-6 seam preserved; v2 follow-up
- Hosted embedding fallback (OpenAI, Cohere) — local-first only in v1
- Int8 quantization — sqlite-vec 0.1.x lacks int8 KNN; defer to v1.1
- Cross-project federation search — change #4 owns (`cross-project-federation`)
- Graph-snapshots-aware temporal search — change #5 owns (`graph-snapshots`)
- Async embed-on-save — v1 is sync (~50ms CPU per ≤2KB); v1.1 follow-up
- Daemon-driven drift on vector index changes — `flow watch` does not subscribe to `vectors.sqlite`
- Dynamic model hot-swap at runtime — `flow reindex --model <name>` is the only model-change path
- Beyond REQ-8 dashboards — change #6 owns

## Traceability (Engram observation IDs)

- #139 — explore (Approach A additive `HybridBackend`, sqlite-vec + sentence-transformers options)
- #140 — proposal (PR#1/PR#2 breakdown, 6 REQs)
- #141 — design (11 architecture decisions, D1-D11)
- #142 — spec (6 REQs, 28 BDD scenarios)
- #143 — tasks (17 tasks across 2 PRs)
- #144 — apply-progress PR#1 batch A (ABC extension + InMemoryBackend defaults)
- #145 — apply-progress PR#1 batch B (EmbeddingProvider + HybridBackend scaffold)
- #146 — apply-progress PR#1 batch C (hybrid scoring formula)
- #147 — apply-progress PR#1 batch D1 (SqliteVecStore + counters + pyproject)
- #148 — apply-progress PR#1 batch D2 (BDD req17 + req18)
- #149 — apply-progress PR#2 batch E (SentenceTransformersProvider + BDD req19 + req20)
- #150 — apply-progress PR#2 batch F (CLI --semantic + flow reindex)
- #151 — apply-progress PR#2 batch G (BDD req21 + CHANGELOG v0.4.0 + SKILL.md hooks)
- #152 — verify-report (PASS WITH WARNINGS, 0 critical)
- #153 — apply-progress W11 (post-archive BDD req22 add)
- This archive-report — topic `sdd/vector-semantic-search/archive-report`

## Cleanup Verification

- `git status` pre-archive: working tree clean
- `git log --oneline -10`: PRs #8-#9 squash merges intact on `main` + `d19383b` W11 + `bd8673b` W-fixes
- `uv run pytest --tb=no -q`: **576 passed in 5.20s** — all green (verified pre-archive)
- 5 git rename detections (proposal/design/spec/tasks/explore mirror) mirror archive-report #119 format
- 9 apply-progress files created in `apply-progress/` subfolder (8 PR batches + 1 W11 housekeeping)

## Relevant Files

- `openspec/changes/archive/2026-06-26-vector-semantic-search/explore.md` — exploratory analysis (mirrored from Engram #139)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/proposal.md` — proposal with Approach A (additive `HybridBackend`)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/design.md` — design with 11 architecture decisions (D1-D11)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/spec.md` — 6 REQs (REQ-17..22), 28 BDD scenarios
- `openspec/changes/archive/2026-06-26-vector-semantic-search/tasks.md` — 17 tasks across 2 PRs (all `[x]` per W15)
- `openspec/changes/archive/2026-06-26-vector-semantic-search/verify-report.md` — PASS WITH WARNINGS, 0 critical
- `openspec/changes/archive/2026-06-26-vector-semantic-search/apply-progress/*.md` — 9 batch snapshots (8 PR batches + 1 W11)
- `openspec/changes/archive/2026-06-26-decision-reality-drift/` — predecessor archive (W2/W3 reconciliation pattern)
- `CHANGELOG.md` — v0.4.0 entry (with W9/W10 counts and [vectors] extra accuracy fixed in `bd8673b`)
- `pyproject.toml` — version 0.4.0 (per W12 fix in `bd8673b`); [vectors] extra at lines 39-42
- `src/flow_engineering/engram_io.py` — REQ-17 (VectorSearchDisabled, InMemoryBackend overrides, ABC v1.1)
- `src/flow_engineering/hybrid_backend.py` — REQ-18 (linear combo formula) + REQ-22 observability wiring
- `src/flow_engineering/embedding_provider.py` — REQ-19 (EmbeddingProvider ABC + MockEmbeddingProvider + SentenceTransformersProvider)
- `src/flow_engineering/vectors/sqlite_vec_store.py` — REQ-20 (observation_embeddings + vec_observations)
- `src/flow_engineering/observability.py` — REQ-22 (6 VECTOR_COUNTER_NAMES + record_vector_summary)
- `src/flow_engineering/cli.py` — REQ-17 CLI surface (`flow search --semantic|--hybrid`) + REQ-21 (`flow reindex`)
- `tests/bdd/req{17,18,19,20,21,22}_*.feature` — 6 BDD feature files, 28 scenarios
- `tests/bdd/test_vector_search_steps.py` — pytest-bdd step glue
- `tests/unit/test_engram_io.py::TestVectorSearchDisabled` — REQ-17 unit tests (5)
- `tests/unit/test_hybrid_backend.py` — REQ-18 unit tests (~39)
- `tests/unit/test_embedding_provider.py` + `test_embedding_provider_embed_batch.py` — REQ-19 unit tests (32+10)
- `tests/unit/test_sqlite_vec_store.py` — REQ-20 unit tests (21)
- `tests/unit/test_observability_vectors.py` — REQ-22 unit tests (20)
- `tests/unit/test_cli_search_semantic.py` — REQ-17 CLI unit tests (14)
- `tests/unit/test_cli_reindex.py` — REQ-21 CLI unit tests (8)
- `~/.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` — 6 runtime Vector search hook sections

## Next change

- Change #4: `cross-project-federation` (Penpax-style layer for knowledge transfer between the 6 sub-projects). ~1.5-2h. Use `/sdd-new cross-project-federation`.

---

**Session**: flow-engineering-vector-semantic-search-archive-2026-06-26
**SDD Cycle**: COMPLETE
**Next**: `cross-project-federation` (queue position 4, now unblocked)
