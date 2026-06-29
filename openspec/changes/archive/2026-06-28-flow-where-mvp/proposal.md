---
status: success
confidence: high
open_questions_count: 0
chained_pr_recommendation: no
wall_time_estimate: ~1-2h end-to-end (chica)
forecast_loc: 150 prod + 50 tests = 200 total
strict_tdd: true
chain_strategy: not_applicable
---

# Proposal: flow-where-mvp

## Status

success — 0 open questions, single PR, scope locked at 3 backends + text output.

## Goal

`flow where "<query>"` — a single CLI subcommand that answers "where did I implement X?" in one hop by fanning out across three local sources: **repo code + tests** (split by path prefix), **archived SDD specs**, and the **graphify graph index** (fail-open). Output is plain text with explicit `CODE / TESTS / SDD / GRAPH` sections, default 20 hits per backend, no new Python deps, no JSON, no ranking — deterministic file grep over files that already exist.

## Open Questions

**0 open** (all pre-decided by user + orchestrator):

- Engram backend → deferred to Opción media (avoid protocol coupling in MVP)
- `--json` flag → deferred (text is the contract for v0)
- Ranking / scoring → not in MVP (rg's natural file-path-then-line order is sufficient)
- Commit SHA refs → not in MVP (adds a subprocess + parse pass for negligible value)
- REQ-NN cross-linking → not in MVP (seam preserved; v1.x follow-up)
- `--graph` vs `--no-graph` → default ON with `--no-graph` opt-out (cheaper for the user; fail-open is free)

## Approach

### Three backends (new module `src/flow_engineering/where.py`, ~150 LOC)

1. **Repo grep (CODE + TESTS split)** — `subprocess.run(["rg", "--line-number", "--no-heading", query, "src/", "tests/"])`; if `rg` missing → fallback to POSIX `grep -rn`. Split hits: `path.startswith("tests/")` → TESTS section, else → CODE.
2. **SDD archive grep (SDD section)** — same pattern over `openspec/changes/archive/`. Missing directory returns `[]` (no error).
3. **Graphify fail-open (GRAPH section)** — read `graphify-out/graph.json` if it exists; score nodes by Jaccard over `label + id + source_file`. Missing file / malformed JSON / empty `nodes` → render `unavailable / no graph index found` (single line, no traceback). Reuses `graphify_query.jaccard_fallback` pattern — zero new deps.

### Output contract (text, UTF-8 stdout)

```
CODE
- src/flow_engineering/auth.py:42
- src/flow_engineering/middleware.py:18

TESTS
- tests/unit/test_auth.py:23

SDD
- openspec/changes/archive/2026-06-25-decision-code-linking/spec.md:88 REQ-7 mentions JWT signing key validation

GRAPH
- src/flow_engineering/auth.py:42 — module:auth (confidence 0.78)
```

Sections always render in order **CODE → TESTS → SDD → GRAPH** (even when empty). Empty section prints `(no matches)`. Exit code is `0` always (even zero hits); `2` only on internal error.

### CLI surface (new `@main.command()` in `src/flow_engineering/cli.py`, ~15 LOC)

- positional `query` (string)
- `--limit N` (default 20) — caps each backend
- `--no-graph` — opt-out flag

### Prior art avoidance (vs `2026-06-26-vector-semantic-search` #4)

We borrow the **ABC + fail-open discipline** (`graphify_query.query_nodes` returns `[]` on every error) and the **BDD-first + strict TDD** test pattern. We **explicitly reject** #4's scope: no embeddings, no sqlite-vec, no torch, no `[vectors]` extra, no `FLOW_VECTOR_SEARCH=1` activation gate, no chained 2-PR plan. This is grep over local files — fundamentally different problem.

### Single PR, not chained

Total forecast: ~200 LOC (150 prod + 50 tests) → realistic ~1.2k LOC with strict TDD multiplier (matches explore forecast; 6× per the established pattern). Well under the 400-line review budget even with TDD multiplier ×6. No natural seam for a chained PR — backends, CLI wiring, and BDD scenarios are tightly coupled by the render contract.

## Capabilities

### New Capabilities
- `flow-where-mvp`: cross-source retrieval CLI (`flow where "<query>"`) that fans out to repo grep, SDD archive grep, and graphify Jaccard, rendering structured `CODE / TESTS / SDD / GRAPH` text output with deterministic ordering and fail-open semantics.

### Modified Capabilities
- None. No existing spec changes — pure additive CLI subcommand.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `src/flow_engineering/where.py` | NEW | 3 backend funcs + `WhereHit`/`WhereResult` dataclasses + `render_text` (~150 LOC) |
| `src/flow_engineering/cli.py` | MODIFY (minor) | New `@main.command()` registering `where` (~15 LOC) |
| `tests/unit/test_where.py` | NEW | Pure-function tests for all 4 backends + renderer (~250 LOC) |
| `tests/bdd/req_where.feature` | NEW | BDD scenarios (7 scenarios, see explore.md) (~120 LOC) |
| `tests/bdd/test_where_steps.py` | NEW | pytest-bdd glue (~130 LOC) |

No changes to `engram_io.py`, `binding.py`, `graphify_query.py`, or `pyproject.toml`.

## REQ List (4 requirements)

- **REQ-V1.0.1** — Repo grep backend: `grep_repo(query)` returns `(code_hits, tests_hits)` splitting by `path.startswith("tests/")`, with `--limit` cap and POSIX `grep -rn` fallback when `rg` missing.
- **REQ-V1.0.2** — SDD archive grep backend: `grep_sdd(query)` returns hits from `openspec/changes/archive/**/*.md` only, with `--limit` cap; missing directory returns `[]`.
- **REQ-V1.0.3** — Graphify fail-open backend: `grep_graph(query)` returns `None` when `graph.json` missing/malformed/empty, else ranked hits via Jaccard over `label + id + source_file`.
- **REQ-V1.0.4** — `flow where` CLI subcommand + text formatter: registers as `@main.command()`, parses `query` + `--limit` + `--no-graph`, calls `where(...)`, renders `render_text(result)` to stdout with sections always in `CODE / TESTS / SDD / GRAPH` order.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `rg` not on PATH (some Windows / sandboxes) | Low | Fall back to POSIX `grep -rn` via `shutil.which("rg") is None` branch |
| `graph.json` malformed | Low | Wrap `json.loads` in `try/except (OSError, json.JSONDecodeError)` → return `None` |
| Query contains regex metachars rg interprets | Low | `shlex.quote` the query in subprocess call (both rg and grep accept literal queries when quoted) |
| Tests for `grep_repo` hit real `src/` + `tests/` (not isolated) | Low | Use `monkeypatch.chdir(tmp_path)` and create a small fixture tree; tests do not depend on real repo contents |
| `openspec/changes/archive/` missing (fresh repo) | Low | `grep_sdd` returns `[]`; SDD section renders `(no matches)`; exit 0 |

All risks are LOW — no torch, no ABC version bump, no third-party backend coupling, no optional-extras activation gate. Compared to vector-semantic-search #4, this is the boring happy path.

## Carry-forwards (NOT in MVP, deferred to Opción media)

- Engram backend (`engram_io.EngramClient.mem_search` filtered by topic_key prefix) — explicit user decision to defer until MCP plumbing is stable
- `--json` flag — text is the v0 contract; JSON when we know what users pipe it into
- Ranking / RRF / BM25 — rg's natural order is sufficient for "where did I implement X?"
- Commit SHA references (`git log -S` integration) — adds subprocess + parse pass for negligible value
- REQ-NN cross-linking — `binding.split_prose_and_refs` seam is preserved for v1.x
- Confidence scores on CODE/TESTS/SDD — only GRAPH carries confidence (it's in `graph.json`); repo hits are binary matched/not-matched
- Watch / daemon mode — irrelevant for read-only CLI
- Persistent index / cache — every call is fresh; rg is fast enough

## PR Strategy

**Single PR**, not chained. Forecast ~200 LOC → realistic ~1.2k LOC with strict TDD ×6 multiplier — still under the 400-line review budget. No natural slice seam: the 3 backends, CLI handler, and BDD scenarios are coupled by the `WhereResult` dataclass shape and `render_text` contract. Splitting would create artificial interfaces.

```
branch: feature/flow-where-mvp
├── where.py (NEW, ~150 LOC)
├── cli.py (MODIFY, +15 LOC @main.command())
├── tests/unit/test_where.py (NEW, ~250 LOC)
├── tests/bdd/req_where.feature (NEW, ~120 LOC)
└── tests/bdd/test_where_steps.py (NEW, ~130 LOC)
```

Review budget check: `Decision needed before apply: No` | `Chained PRs recommended: No` | `400-line budget risk: Low`.

## Rollback Plan

Revert the merge commit. `where.py`, the `@main.command()` registration, and the test files are all additive — no existing CLI subcommand, module, or capability changes. After revert, `flow where` does not exist (exit `2` on unknown command); `flow` itself is unaffected. No migrations, no env vars, no flag flips.

## Dependencies

- `rg` (preferred) or POSIX `grep -rn` (fallback) — both universal, no Python import
- `graphify-out/graph.json` (optional, user-generated) — fail-open if absent
- No new Python deps. No `pyproject.toml` changes. No `[vectors]` extra. No `FLOW_*` env var.

## Success Criteria

- [ ] `flow where "JWT"` exits 0 with structured `CODE / TESTS / SDD / GRAPH` text on a fixture repo with all four section types
- [ ] `flow where "no-such-symbol-xyz"` exits 0 with `(no matches)` in each section
- [ ] `flow where --no-graph "JWT"` skips GRAPH section entirely
- [ ] `flow where --limit 5 "JWT"` caps each backend at 5 hits
- [ ] With `graphify-out/graph.json` absent → GRAPH renders exact `unavailable / no graph index found`
- [ ] Strict TDD: every public function has RED → GREEN → REFACTOR history in commit log
- [ ] Test suite: 1383/1383 baseline + ~25 new = ~1408/1408 passing
- [ ] `ruff check` + `mypy --strict` clean on changed files
- [ ] No new Python deps in `pyproject.toml`

## Wall Time

~1-2h end-to-end:
- propose (this): ~15min ✅
- design: ~15min
- spec: ~20min
- tasks: ~10min
- apply (RED → GREEN → REFACTOR): ~45min
- verify: ~10min
- archive: ~5min

## Next Step

`flow drift flow-where-mvp` is N/A (no shipped spec to drift against). `sdd-design flow-where-mvp` will lock the `WhereResult` shape, render contract, fallback strategy, and the 3 design-phase confirmations from explore.md (snippet policy, sort order, `--no-graph` default).
