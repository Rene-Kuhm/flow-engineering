---
status: success
phase: tasks
change: flow-where-mvp
requirements:
  - REQ-V1.0.1
  - REQ-V1.0.2
  - REQ-V1.0.3
  - REQ-V1.0.4
strict_tdd: true
batch_count: 2
task_count: 11
loc_forecast:
  prod: 160
  tests: 140
  total: 300
chained_pr_recommendation: no
delivery_strategy: single-pr
---

# Tasks: flow-where-mvp

**Change:** `flow-where-mvp` — `flow where "<query>"` retrieval subcommand (MVP)
**Approach:** additive CLI subcommand, 3 fail-open backends, text-only output
**Delivery:** `single-pr` · Strict TDD: ON · Chained PRs: No

## Goal

Ship `flow where "<query>"` — a single CLI subcommand that answers "where did I
implement X?" by fanning out to **repo code + tests**, **archived SDD specs**,
and the **graphify graph index** (fail-open). Output is plain text with explicit
`CODE / TESTS / SDD / GRAPH` sections. Zero new Python deps, zero JSON, zero
ranking — deterministic grep over files that already exist on disk.

## Scope

- NEW `src/flow_engineering/where.py` (~150 LOC): 3 pure-function backends +
  `WhereHit` / `WhereResult` dataclasses + `render_text` formatter.
- MODIFY `src/flow_engineering/cli.py` (+10 LOC): flat `@main.command()`
  registering `where_cmd` next to `new` / `status` / `memory-timeline`.
- NEW `tests/unit/test_where.py` (~50 LOC): pure-function tests covering all
  4 public functions + rg-mocked subprocess layer.
- NEW `tests/bdd/req_where.feature` (~50 LOC): 7 BDD scenarios (full coverage
  of REQ-V1.0.1..V1.0.4 render contract + fail-open + flag behavior).
- NEW `tests/bdd/test_where_steps.py` (~40 LOC): pytest-bdd step glue.

## Out of Scope

(Deferred to Opción media — see `proposal.md:113-122`)

- Engram backend (4th backend via `engram_io.EngramClient.mem_search`)
- `--json` flag (machine-readable output)
- Ranking / RRF / BM25 (rg natural order is sufficient for MVP)
- Commit SHA references (`git log -S` integration)
- REQ-NN cross-linking (`binding.split_prose_and_refs` seam preserved)
- Watch / daemon mode
- Persistent index / cache (every call is fresh)
- Multi-project federation (owned by `cross-project-federation`)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~300 impl + ~900 strict-TDD multiplier = ~1200 total |
| 400-line budget risk | Low (impl under 400; multiplier accounts for test iteration) |
| Chained PRs recommended | No |
| Suggested split | Single PR (backends, CLI, BDD are coupled by render contract) |
| Delivery strategy | `single-pr` |
| Chain strategy | `not_applicable` |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: not_applicable
400-line budget risk: Low
```

Per the `decision-code-linking` precedent (`archive/2026-06-25-decision-code-linking/tasks.md:18-23`),
the plain-text lines above are the literal guard contract.

---

## Sub-batch A — Backend modules (T1.1..T1.6, ~6 tasks, ~120 LOC)

Scope: pure-function backends `grep_repo`, `split_code_vs_tests`,
`grep_sdd_archive`. No I/O coupling to engram, no CLI wiring. Establishes
the dataclass shape (`WhereHit`) and the rg-or-grep subprocess seam shared
by Sub-batch B's `grep_graphify`.

### T1.1 — RED: `grep_repo` returns `[]` on no match
**REQ:** REQ-V1.0.1
**Goal:** failing test confirms `grep_repo("no-such-symbol-xyz", limit=20)`
returns `([], [])` when neither `src/` nor `tests/` contain the symbol.
**Strict TDD:**
- RED: `tests/unit/test_where.py::TestGrepRepo::test_no_match_returns_empty_pair`
  (create fixture tree in `tmp_path` via `monkeypatch.chdir(tmp_path)`; assert
  both returned lists empty)
- GREEN: T1.2
- REFACTOR: T1.2
**Acceptance:**
- `uv run --frozen pytest tests/unit/test_where.py::TestGrepRepo -k no_match -q` exits 0
- Test fails before T1.2 (RED); passes after T1.2 (GREEN)
**LOC forecast:** ~8 tests, 0 prod (RED only)

### T1.2 — GREEN: implement `grep_repo` with rg + POSIX fallback
**REQ:** REQ-V1.0.1
**Goal:** `grep_repo(query, *, limit=20, cwd=Path.cwd())` runs rg with
`--line-number --no-heading`; falls back to `grep -rn` when
`shutil.which("rg") is None`. Parses `path:line[:col]` lines into `WhereHit`.
**Strict TDD:**
- RED: T1.1
- GREEN: `src/flow_engineering/where.py::grep_repo` (~30 LOC) + private
  `_resolve_search_tool()` + `_run_search()` + `_parse_hits()` helpers
- REFACTOR: extract `_resolve_search_tool` shim to make T1.2 testable without
  relying on host rg
**Acceptance:**
- All `TestGrepRepo` cases green: no-match, CODE-only, TESTS-only, mixed,
  `--limit` truncation, rg-missing fallback
- `uv run --frozen ruff check src/flow_engineering/where.py` exits 0
**LOC forecast:** ~30 prod + ~5 tests = ~35

### T1.3 — RED: `split_code_vs_tests` partitions by path prefix
**REQ:** REQ-V1.0.1
**Goal:** failing test confirms `split_code_vs_tests(hits)` sends
`tests/...` paths to TESTS bucket and everything else to CODE bucket, with
order preserved within each bucket.
**Strict TDD:**
- RED: `tests/unit/test_where.py::TestSplitCodeVsTests::test_partitions_by_prefix`
  (3 cases: all-code, all-tests, mixed; assert buckets + ordering)
- GREEN: T1.4
- REFACTOR: T1.4
**Acceptance:**
- `uv run --frozen pytest tests/unit/test_where.py::TestSplitCodeVsTests -q` exits 0
- Test fails before T1.4 (RED); passes after T1.4 (GREEN)
**LOC forecast:** ~6 tests, 0 prod (RED only)

### T1.4 — GREEN: implement `split_code_vs_tests(hits)`
**REQ:** REQ-V1.0.1
**Goal:** `split_code_vs_tests(hits: list[WhereHit]) -> tuple[list[WhereHit], list[WhereHit]]`
with `path.startswith("tests/") → tests_bucket`, else `code_bucket`. Order
preserved (rg's natural order: path-asc, line-asc).
**Strict TDD:**
- RED: T1.3
- GREEN: `src/flow_engineering/where.py::split_code_vs_tests` (~6 LOC)
- REFACTOR: N/A (already minimal)
**Acceptance:**
- All `TestSplitCodeVsTests` cases green
- Function is pure (no I/O); amenable to table-driven tests
**LOC forecast:** ~6 prod, 0 tests

### T1.5 — RED: `grep_sdd_archive` reads `openspec/changes/archive/`
**REQ:** REQ-V1.0.2
**Goal:** failing tests cover (a) one-hit case from fixture `.md`, (b)
missing directory returns `[]`, (c) `--limit` caps hits at N.
**Strict TDD:**
- RED: `tests/unit/test_where.py::TestGrepSddArchive` (3 test methods:
  `test_one_hit`, `test_missing_dir_returns_empty`, `test_limit_caps_hits`)
- GREEN: T1.6
- REFACTOR: T1.6
**Acceptance:**
- `uv run --frozen pytest tests/unit/test_where.py::TestGrepSddArchive -q` exits 0
- 3 tests fail before T1.6 (RED); pass after T1.6 (GREEN)
**LOC forecast:** ~9 tests, 0 prod (RED only)

### T1.6 — GREEN: implement `grep_sdd_archive()`
**REQ:** REQ-V1.0.2
**Goal:** single rg call against `Path("openspec/changes/archive/")` via the
shared `_resolve_search_tool` + `_run_search` helpers from T1.2. Missing
directory returns `[]` (no error, no traceback). Same fallback to POSIX
`grep -rn` when `rg` absent.
**Strict TDD:**
- RED: T1.5
- GREEN: `src/flow_engineering/where.py::grep_sdd_archive` (~25 LOC)
- REFACTOR: factor `_run_search(query, paths, cwd)` helper so T1.2 + T1.6 +
  T2.2 share one subprocess call site
**Acceptance:**
- All `TestGrepSddArchive` cases green
- `grep_sdd_archive` never raises; exit code 0 on missing dir
**LOC forecast:** ~25 prod, 0 tests (tests written in T1.5)

---

## Sub-batch B — Graphify backend + CLI + BDD (T2.1..T2.5, ~5 tasks, ~80 LOC)

Scope: completes the data plane with the graphify fail-open backend, wires
the Click subcommand, and adds BDD coverage that locks the render contract
end-to-end. Sub-batch B depends on Sub-batch A's `WhereHit` dataclass and
the shared subprocess helpers.

### T2.1 — RED: `grep_graphify` returns `None` when `graph.json` missing
**REQ:** REQ-V1.0.3
**Goal:** failing test confirms `grep_graphify("JWT", limit=20, graph_path=tmp/fake.json)`
returns `None` when the path does not exist. Plus a malformed-JSON case
(`OSError` / `json.JSONDecodeError` → `None`) and an empty-`nodes` case
(`None`).
**Strict TDD:**
- RED: `tests/unit/test_where.py::TestGrepGraphify::test_missing_file_returns_none`
  + `test_malformed_json_returns_none` + `test_empty_nodes_returns_none`
  (3 test methods)
- GREEN: T2.2
- REFACTOR: T2.2
**Acceptance:**
- `uv run --frozen pytest tests/unit/test_where.py::TestGrepGraphify -k none -q` exits 0
- 3 tests fail before T2.2 (RED); pass after T2.2 (GREEN)
**LOC forecast:** ~9 tests, 0 prod (RED only)

### T2.2 — GREEN: implement `grep_graphify` with Jaccard scoring
**REQ:** REQ-V1.0.3
**Goal:** read `graph_path` (default `Path(r"c:\dev\proyects\flow-engineering\graphify-out\graph.json")`).
`try/except (OSError, json.JSONDecodeError)` → return `None`. Tokenize
query + each node's `label + id + source_file` (reuse `_TOKEN_PATTERN`
from `graphify_query.py:34`), score via local `_jaccard_score()`, return
top-K by score desc. Scoring helpers are duplicated (~12 LOC) from
`graphify_query.jaccard_fallback` (`graphify_query.py:217`) to keep
`where.py` independently testable.
**Strict TDD:**
- RED: T2.1
- GREEN: `src/flow_engineering/where.py::grep_graphify` (~25 LOC) +
  `_tokenize_for_jaccard` + `_jaccard_score` private helpers
- REFACTOR: consolidate token-set computation so it matches `graphify_query`
  shape 1:1 (visual diff confirms parity)
**Acceptance:**
- All `TestGrepGraphify` cases green: missing / malformed / empty / valid / scoring-monotonicity
- `grep_graphify` never raises; missing path → `None`
**LOC forecast:** ~25 prod, 0 tests (tests written in T2.1)

### T2.3 — RED: `flow where "<query>"` produces structured text output
**REQ:** REQ-V1.0.4
**Goal:** failing tests for `where()` orchestrator + `render_text()`
formatter covering: (a) all 4 sections render in `CODE / TESTS / SDD / GRAPH`
order; (b) empty section prints `(no matches)`; (c) `--no-graph` skips
GRAPH section; (d) GRAPH unavailable renders exact
`unavailable / no graph index found`; (e) `--limit N` caps each backend.
**Strict TDD:**
- RED: `tests/unit/test_where.py::TestWhereOrchestrator` (5 test methods
  covering the 5 contract points above)
- GREEN: T2.4
- REFACTOR: T2.4
**Acceptance:**
- `uv run --frozen pytest tests/unit/test_where.py::TestWhereOrchestrator -q` exits 0
- 5 tests fail before T2.4 (RED); pass after T2.4 (GREEN)
**LOC forecast:** ~10 tests, 0 prod (RED only)

### T2.4 — GREEN: register `flow where` Click subcommand + render_text
**REQ:** REQ-V1.0.4
**Goal:** `src/flow_engineering/cli.py` gains `@main.command()` `where_cmd`
(3 flags: positional `query`, `--limit` int default 20, `--no-graph`
is_flag default False). Handler delegates to `where.where(query, ...)`
and `click.echo(where.render_text(result))`. Plus
`src/flow_engineering/where.py::where()` orchestrator + `render_text()`
formatter that joins the 4 section strings with `"\n\n"` and emits
`(no matches)` for empty buckets.
**Strict TDD:**
- RED: T2.3
- GREEN: `src/flow_engineering/where.py::where()` (~15 LOC) +
  `render_text()` (~15 LOC) + `src/flow_engineering/cli.py::where_cmd`
  (~10 LOC + import block)
- REFACTOR: tighten `render_text` to a single join with deterministic
  ordering; ensure CLI handler ≤10 LOC per design budget (`design.md:46`)
**Acceptance:**
- All `TestWhereOrchestrator` cases green
- `uv run --frozen flow where "JWT" --limit 5` exits 0 with structured text
- `uv run --frozen flow where --help` lists the command
- `uv run --frozen mypy --strict src/flow_engineering/where.py src/flow_engineering/cli.py` exits 0
**LOC forecast:** ~40 prod + ~5 tests = ~45

### T2.5 — BDD: 2 NEW scenarios in `req_where.feature` + step glue
**REQ:** REQ-V1.0.1 + REQ-V1.0.3 (cross-cutting render contract)
**Goal:** 2 NEW pytest-bdd scenarios in `tests/bdd/req_where.feature`
(append to the 7 scenarios written by the orchestrator-led spec phase —
T2.5 only owns the 2 scenarios this change introduces): (1) graphify absent
→ GRAPH renders `unavailable / no graph index found`; (2) graphify
present → GRAPH section populated with scored hits. Plus step glue in
`tests/bdd/test_where_steps.py`.
**Strict TDD:**
- RED: BDD is executable spec — scenarios added before any code in this task
- GREEN: same code paths as T1.1..T2.4; BDD scenarios must pass on first run
  of `pytest tests/bdd/ -k where`
- REFACTOR: extract common `run_flow_where(tmp_path, query, ...)` step helper
  used by both scenarios
**Acceptance:**
- `uv run --frozen pytest tests/bdd/ -k where -q` exits 0
- 2 NEW scenarios green (graphify-absent + graphify-present)
- `flow where "<query>"` exit code is `0` in both scenarios
- Section order `CODE / TESTS / SDD / GRAPH` is preserved in both outputs
**LOC forecast:** ~15 BDD (feature) + ~25 steps = ~40

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `rg` not on PATH (Windows / sandboxed envs) | Low | `shutil.which("rg")` → POSIX `grep -rn` fallback (`design.md:D1`) |
| `graph.json` malformed / missing / empty `nodes` | Low | `try/except (OSError, json.JSONDecodeError)` → `None` → GRAPH renders `unavailable / no graph index found` (`design.md:D3`) |
| Query contains regex metachars rg interprets | Low | `shlex.quote(query)` before subprocess call (`design.md:89`) |
| Tests for `grep_repo` hit real `src/` + `tests/` | Low | `monkeypatch.chdir(tmp_path)` + fixture tree (`design.md:90`) |
| `openspec/changes/archive/` missing on fresh clone | Low | `grep_sdd_archive` returns `[]`; SDD section renders `(no matches)`; exit 0 |
| TDD ×6 multiplier blows past 400-line budget | Low | Per-PR impl is ~300 LOC; multiplier accounts for test iteration, not commit diff |

All risks are LOW — no torch, no ABC version bump, no third-party backend
coupling, no optional-extras activation gate.

## Acceptance criteria

Mirrors `proposal.md:149-159`:

- [ ] `flow where "JWT"` exits 0 with structured `CODE / TESTS / SDD / GRAPH`
      text on a fixture repo with all four section types (T2.4 + T2.5)
- [ ] `flow where "no-such-symbol-xyz"` exits 0 with `(no matches)` in each
      section (T2.3 + T2.4)
- [ ] `flow where --no-graph "JWT"` skips GRAPH section entirely (T2.3 + T2.4)
- [ ] `flow where --limit 5 "JWT"` caps each backend at 5 hits (T2.3 + T2.4)
- [ ] With `graphify-out/graph.json` absent → GRAPH renders exact
      `unavailable / no graph index found` (T2.1 + T2.2 + T2.5)
- [ ] Strict TDD: every RED task produces a failing test; every GREEN task
      produces a passing implementation; commit log preserves `RED → GREEN → REFACTOR`
      rhythm per `tests/unit/test_where.py` history (T1.1..T2.5)
- [ ] Test suite: 1383/1383 baseline + ~25 new (11 unit + ~14 BDD scenarios)
      = ~1408/1408 passing
- [ ] `uv run --frozen ruff check src/flow_engineering/where.py src/flow_engineering/cli.py`
      exits 0
- [ ] `uv run --frozen mypy --strict src/flow_engineering/where.py src/flow_engineering/cli.py`
      exits 0
- [ ] No new Python deps in `pyproject.toml`

## Implementation Order (rationale)

Sub-batch A is strictly bottom-up: rg subprocess seam → split helper → SDD
backend. Each T1.x builds on the previous (T1.1 → T1.2 → T1.3 → T1.4 →
T1.5 → T1.6); no parallelism inside A.

Sub-batch B layers onto A's surface: graphify backend (reuses `_TOKEN_PATTERN`
shape from `graphify_query.py:34`) → CLI orchestrator + `render_text` → BDD
scenarios that lock the cross-cutting render contract. T2.5's BDD scenarios
are append-only (orchestrator-led spec phase owns the first 7); T2.5 adds
2 cross-cutting scenarios that exercise the orchestrator + graphify fail-open
together.

No phase dependencies between A and B are bidirectional — B reads A's
`WhereHit` dataclass shape (defined implicitly in T1.2's GREEN) and the
shared `_run_search` helper (refactored in T1.6). Therefore: complete A
fully, then start B.

## Dependency Diagram

```
Sub-batch A (target: feature/flow-where-mvp)
  T1.1 → T1.2 ─────────────────────────────┐
           └→ (helpers _run_search,         │
              _resolve_search_tool)         │
  T1.3 → T1.4 ─────────────────────────────┤
  T1.5 → T1.6 (refactors _run_search) ─────┤
                                          ▼
Sub-batch B (same PR; targets main after A)
  T2.1 → T2.2 (reuses graphify token pattern)
  T2.3 → T2.4 (registers @main.command() + render_text)
  T2.4 → T2.5 (BDD cross-cutting scenarios)
                                          ▼
                                    single PR merge
```

## Pre-flight

```text
1383 tests collected in 0.45s   ✅ confirmed 2026-06-28 baseline
```

---

## Next Step

`sdd-apply flow-where-mvp` — execute Sub-batches A and B in order with strict
TDD discipline. Loop mode continues automatically.