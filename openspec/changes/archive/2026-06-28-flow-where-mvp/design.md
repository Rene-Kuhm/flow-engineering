---
status: success
phase: design
change: flow-where-mvp
confidence: high
forecast_loc: 200 (150 prod + 50 tests, ~1.2k with strict TDD ×6)
strict_tdd: true
open_questions_count: 0
---

# Design: flow-where-mvp — `flow where "<query>"` retrieval subcommand

## Technical Approach

Single new CLI subcommand `flow where "<query>"` registered as a flat `@main.command()` in `src/flow_engineering/cli.py:145` (alongside `new`, `status`, `doctor`, `memory-timeline`). Logic lives in a new thin module `src/flow_engineering/where.py` (~150 LOC) shaped like `graphify_query.py:1` — three pure-function backends, one orchestrator, one text formatter. No ABC, no new Python deps, no env-var activation gate. Output is plain text, sections always render in the order **CODE → TESTS → SDD → GRAPH**, with `(no matches)` for empty sections and the exact string `unavailable / no graph index found` for the GRAPH fail-open case.

## Architecture Decisions

### D1 — Repo grep backend (`grep_repo`)

**Choice**: `subprocess.run(["rg", "--line-number", "--no-heading", query, "src/", "tests/"], check=False)`; parse `path:line[:col]` output. Detect rg via `shutil.which("rg")`; when `None`, fall back to POSIX `grep -rn <query> src/ tests/`. Split hits: `path.startswith("tests/")` → `tests_hits`, else → `code_hits`. Cap each list at `--limit` (default 20).

**Alternatives**: (a) Python `re`-based grep → slower on large repos, no `path:line` separator. (b) Force-rg, no fallback → breaks for users without `rg` (real on Windows ARM). (c) Use `pathlib.rglob` + manual read → no perf benefit, more code.

**Rationale**: rg is fastest, universal, ships on Linux/macOS and via package managers on Windows. The `grep -rn` POSIX fallback is the project's `shutil.which`-style seam (mirrors `graphify_query._run_graphify_cli` at `src/flow_engineering/graphify_query.py:87`).

### D2 — SDD archive grep backend (`grep_sdd`)

**Choice**: Same rg-or-grep pattern over the constant `Path("openspec/changes/archive/")`. Missing directory returns `[]`; the SDD section renders `(no matches)`. Never raises.

**Alternatives**: (a) Recursive `Path.rglob("**/*.md")` + `re.search` → no regex-meta quoting concerns but slower and more code. (b) Reuse `grep_repo` with a path arg → mixes two backends' contracts.

**Rationale**: One hardcoded path constant keeps the change additive and reviewable. The fail-soft contract (`[]` on missing dir) is the same discipline as `graphify_query.query_nodes` returning `[]` on missing `graph.json` (`graphify_query.py:151-156`).

### D3 — Graphify fail-open backend (`grep_graph`)

**Choice**: Read `graph.json` at `DEFAULT_GRAPH_JSON` (matches `graphify_query.DEFAULT_GRAPH_JSON` at `graphify_query.py:32`). Reuse the `Jaccard` token-overlap scorer from `graphify_query.jaccard_fallback` (`graphify_query.py:217`) over `label + id + source_file`. Missing file / `OSError` / `json.JSONDecodeError` / empty `nodes` key → return `None` → GRAPH section prints exact `unavailable / no graph index found`. The scorer is duplicated as a private helper (~15 LOC) rather than imported, to keep `where.py` independently testable with a fixture `graph.json` and zero dependency on the graphify CLI surface.

**Alternatives**: (a) Import `graphify_query.jaccard_fallback` directly → tightens coupling; tests for `where` would need the graphify cache fixture. (b) Subprocess to `graphify query` → adds a 2-5s blocking call per `flow where`; not justified for MVP. (c) Skip GRAPH entirely → loses one of the three value sources the user explicitly wants.

**Rationale**: Fail-open with a deterministic message is the established seam (see `binding.py:84-87` fail-open on `flow inspect`). Duplicating ~15 LOC of scoring is cheaper than a cross-module import for a one-time query.

### D4 — CLI subcommand + text formatter

**Choice**: New `@main.command()` in `src/flow_engineering/cli.py` (~10 LOC, see `cli.py:145` precedent). Three flags: positional `query` (str), `--limit N` (int, default 20), `--no-graph` (bool, default False — GRAPH is opt-out). Handler delegates to `where.where(query, limit, no_graph, graph_path)` and `click.echo(where.render_text(result))`. Exit code `0` always (even with zero hits); `2` only on unexpected exception.

**Alternatives**: (a) Sub-group `@main.group()` → inconsistent with flat command layout (`new`, `status`, `inspect`, `memory-timeline`); out of MVP. (b) Put logic inline in `cli.py` → blows past the 15-LOC budget for a subcommand; harder to test without `CliRunner`. (c) New `where.py` module with its own Click group, mounted via `add_command` → same coupling cost, less idiomatic.

**Rationale**: `cli.py:145` is the precedent for the flat-decorator pattern. The new `where.py` is the precedent (set by `graphify_query.py:1`) for a thin retrieval module with a 5-7 function public surface.

## Prior Art Reference — `2026-06-26-vector-semantic-search` (#4, archived)

Different problem class. #4 targeted **semantic retrieval over engram observations** using embeddings (sqlite-vec + sentence-transformers, ~500MB torch dep, 2 chained PRs, ~2.8k LOC). `flow where` is **grep over files that already exist on disk** — no embeddings, no new dep, no infra. We borrow #4's **ABC + fail-open discipline** (`graphify_query.py:151-156`) and **BDD-first + strict TDD** test pattern; we explicitly **reject** its scope (no torch, no `[vectors]` extra, no `FLOW_VECTOR_SEARCH=1` gate, no chained 2-PR plan). See `openspec/changes/archive/2026-06-26-vector-semantic-search/design.md:12-23` for the decisions we are NOT repeating.

## Open Questions

**0 open.** All pre-decided in `proposal.md:22-31` and `explore.md:168-172`:

- Snippet policy: CODE/TESTS bare (`path:line`), SDD/GRAPH may include trailing prose → locked.
- Sort order: rg's natural order (path-asc, line-asc) for CODE/TESTS/SDD; confidence-desc for GRAPH → locked.
- `--no-graph` default: ON (opt-out cheaper than opt-in) → locked.

## Architecture Sketches

**D1**: `grep_repo(query, limit, cwd)` → `_resolve_search_tool()` returns `("rg", [...args])` or `("grep", [...args])` based on `shutil.which`; `subprocess.run(...)` with `capture_output=True, text=True, check=False`; on exit 1 → `([], [])`; parse stdout lines of form `path:line:col?...` (rg) or `path:line:...` (grep), split by `pathlib.PurePath` prefix check. Test seam: pass `cwd=tmp_path` + `monkeypatch.chdir(tmp_path)` so tests never hit the real `src/`.

**D2**: `grep_sdd(query, limit, cwd)` → `archive_dir = cwd / "openspec/changes/archive"`; if not `archive_dir.is_dir()` → `[]`; otherwise call the same `_resolve_search_tool` and subprocess layer reused from D1. Test seam: create `tmp_path/openspec/changes/archive/` with one fixture `.md` and assert hit.

**D3**: `grep_graph(query, limit, graph_path)` → `if not graph_path.is_file(): return None`; try `json.loads(graph_path.read_text("utf-8"))` wrapped in `try/except (OSError, json.JSONDecodeError) → None`; if `data.get("nodes", [])` is empty → `None`; otherwise score via local `_jaccard_score(query, node)` over `label + id + source_file`; return top-K sorted by score desc. Test seam: write a 3-node fixture `graph.json` to `tmp_path`, monkeypatch the `DEFAULT_GRAPH_JSON` to that path.

**D4**: `where(query, *, limit, no_graph, graph_path)` orchestrates the three backends; `render_text(result)` joins the four section strings with `"\n\n"` and the exact tokens `CODE`, `TESTS`, `SDD`, `GRAPH` as section headers. CLI handler is a 6-line Click command:

```python
@main.command()
@click.argument("query")
@click.option("--limit", type=int, default=DEFAULT_LIMIT)
@click.option("--no-graph", is_flag=True, default=False)
def where_cmd(query: str, limit: int, no_graph: bool) -> None:
    result = where(query, limit=limit, no_graph=no_graph)
    click.echo(render_text(result))
```

## Risks (all LOW)

| Risk | Likelihood | Mitigation |
|---|---|---|
| `rg` not on PATH (some Windows / sandboxes) | Low | `shutil.which("rg")` is `None` → POSIX `grep -rn` fallback (`graphify_query.py:94-95` precedent) |
| `graph.json` malformed / missing / empty `nodes` | Low | `try/except (OSError, json.JSONDecodeError)` → return `None` → GRAPH renders `unavailable / no graph index found` |
| Query contains regex metachars rg interprets | Low | `shlex.quote(query)` before subprocess call; both rg and grep accept literal queries when quoted |
| Tests for `grep_repo` hit the real `src/` + `tests/` | Low | Pass `cwd=tmp_path` + `monkeypatch.chdir(tmp_path)`; tests build a tiny fixture tree, never touch the real repo |
| `openspec/changes/archive/` missing on fresh clone | Low | `grep_sdd` returns `[]`; SDD section renders `(no matches)`; exit 0 |

No new Python deps, no ABC version bump, no third-party backend coupling, no optional-extras activation gate. Compared to vector-semantic-search #4, this is the boring happy path.

## code_refs

| File | Action | LOC | Purpose |
|---|---|---|---|
| `src/flow_engineering/where.py` | NEW | ~150 | `WhereHit` / `WhereResult` dataclasses; `grep_repo` (D1); `grep_sdd` (D2); `grep_graph` (D3); `where` orchestrator + `render_text` (D4) |
| `src/flow_engineering/cli.py` | MODIFY | +10 | New `@main.command()` registering `where` at `cli.py:145` block (next to `new`, `status`, `memory-timeline`) |
| `tests/unit/test_where.py` | NEW | ~50 | Pure-function tests for the 3 backends + `render_text` (rg-mocked via `monkeypatch.setattr` on `_run_search`) |
| `tests/bdd/req_where.feature` | NEW | ~50 | 7 BDD scenarios: all-sections / code-only / zero-hits / graph-unavailable / --no-graph / --limit-N / exit-code-0 |
| `tests/bdd/test_where_steps.py` | NEW | ~40 | pytest-bdd glue (mirrors `test_vector_search_steps.py:192-228` decorator pattern) |
| `CHANGELOG.md` | MODIFY | +5 | `## [0.8.2] - 2026-06-XX` entry (additive MINOR bump on top of v1.2.0; `flow where` is purely additive) |

Total production: ~160 LOC; test total: ~140 LOC; well under the 400-line review budget for a single PR.
