<!-- spec.md: flow-where capability catalog. Source: sdd-archive archive sync for `flow-where-mvp` (change #13, 2026-06-28). New capability bootstrap — mirrors `decision-drift/spec.md` structure in lightweight form (single-PR scope). -->
# Flow-Where Capability Spec

## Archive status (2026-06-28)

**flow-where-mvp (change #13) SHIPPED as v0.8.2 — single PR, 2 sequential sub-batches (A + B) of strict TDD, 11 tasks complete (T1.1..T2.5), 11 work-unit commits on `main` (HEAD `7874bbc`).**

**REQs shipped**: REQ-V1.0.1 (`grep_repo` repo grep backend with rg + POSIX `grep -rn` fallback + `split_code_vs_tests` partitioner), REQ-V1.0.2 (`grep_sdd_archive` SDD-archive grep backend over `openspec/changes/archive/` with missing-dir fail-open), REQ-V1.0.3 (`grep_graphify` graphify fail-open backend with local Jaccard token-overlap scoring over `label + id + source_file`), REQ-V1.0.4 (`flow where` Click subcommand + `where()` orchestrator + `render_text()` formatter with canonical `CODE / TESTS / SDD / GRAPH` section order).

**Verdict at archive**: **PASS WITH WARNINGS — archive-ready** (accepted per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` + `v1.2-followups` precedent posture). Per `openspec/changes/archive/2026-06-28-flow-where-mvp/verify-report.md`: **0 CRITICAL findings** + **2 WARNING** + **2 SUGGESTION** (all accepted per the established archive-readiness posture). All 4 REQs (REQ-V1.0.1..V1.0.4) have at least one passing test demonstrating compliance. All 11 tasks (T1.1..T2.5) closed with strict-TDD RED → GREEN → REFACTOR evidence in the commit log (11 work-unit commits in canonical RED → GREEN → REFACTOR alternation between `7f8da73..7874bbc`). **1403/1407 tests passing** (+20 net vs `7f8da73` baseline of 1383: +22 NEW unit tests + 2 NEW BDD scenarios − 4 PRE-EXISTING failures unrelated to this change and confirmed failing on the baseline commit). **Mypy clean** on `where.py`; **ruff clean** on all changed files. **2 NEW BDD scenarios** in `tests/bdd/req_where.feature` exercise the orchestrator + graphify fail-open together (graphify-absent renders `unavailable / no graph index found` + graphify-present renders scored hits).

**Findings tally**: **0 CRITICAL + 2 WARNING + 2 SUGGESTION** (all accepted per `drift-hardening` / `v0.9.0-hardening` / `v1.0-followups` / `v1.1-followups` / `v1.2-followups` precedent):

- **W1** (design deviation, ACCEPTED) — `shlex.quote(query)` declared in `design.md:89` (D1 risk mitigation for regex-metachar queries) was NOT applied in `where.py:_run_search`. The implementation invokes `subprocess.run([...query...])` via argv-list mode (no shell), so metacharacters are interpreted as regex by `rg`/`grep` rather than literal substrings. All 24 NEW tests pass + the public contract (sections + ordering + fail-open + `--limit` + `--no-graph`) holds; the deviation is a safety-quoting omission, not a correctness break. Carry-forward decision belongs to the orchestrator; recommended remediation either (a) apply `shlex.quote` in `_run_search` for full design conformance, or (b) amend `design.md:89` to acknowledge that rg/grep are invoked via argv list (no shell) so metachars are interpreted as regex by design. Non-blocking.
- **W2** (PRE-EXISTING test failures, ACCEPTED) — 4 window-filter tests in `tests/unit/test_{observability_aggregate,cli_metrics_aggregate,cli_metrics_export}_*.py` fail on the full test suite (1403/1407). These were confirmed failing on the baseline commit `7f8da73` (BEFORE flow-where apply) by re-running the same 4 tests against the pre-apply state — they are entirely unrelated to `flow where`'s grep + Jaccard + Click surface (they live in the observability/metrics aggregate/export window-filter pipeline at `observability.py:556-560` + `cli.py:2003`). Per `drift-hardening` + `v0.9.0-hardening` + `v1.0-followups` + `v1.1-followups` + `v1.2-followups` precedent, these are acknowledged as PRE-EXISTING and non-blocking. Address in a separate change focused on the metrics window-filter logic.
- **S1** (infra, ACCEPTED) — Windows console cp1252 encoding limit. Running `uv run --frozen flow where "DriftEvent" --limit 5` from a default `cp1252` PowerShell raises `UnicodeEncodeError` when `render_text` output contains Unicode characters (`→`, `✅`, etc.). The CLI subcommand itself runs cleanly — exit code is `0` when captured via `CliRunner` or redirected to a UTF-8 file. The recommended remediation is either (a) the user wraps the call with `Out-File -Encoding utf8` or `$env:PYTHONIOENCODING='utf-8'`, or (b) `where_cmd` wraps `click.echo` in a `try/except UnicodeEncodeError` fallback that re-emits with `errors='replace'` (~3 LOC in `cli.py:402`). Non-blocking; Windows-only; affects any CLI subcommand emitting Unicode.
- **S2** (doc-process, ACCEPTED) — `tests/bdd/req_where.feature` shows only 2 NEW scenarios (T2.5 scope: graphify-absent + graphify-present). The orchestrator-led spec phase contributed 7 earlier scenarios for the cross-cutting render contract; they live in a separate spec-only artifact referenced by comments at `req_where.feature:3-6`. BDD coverage is end-to-end complete (the 2 NEW scenarios exercise the orchestrator + graphify fail-open together); the 7 orchestrator-owned scenarios are documented but not in this file. Optional follow-up: surface the 7 orchestrator-owned scenarios in the same feature file (or a sibling `req_where_scenes.feature`) for visibility.

**Timeout recovery note**: Agent completed all 11 tasks (T1.1..T2.5) in a single `sdd-apply` run with no delegation timeouts. The 11 work-unit commits between `7f8da73..7874bbc` preserve the canonical RED → GREEN → REFACTOR rhythm without gaps.

## Purpose

Cross-version capability spec for the **flow-where** subsystem — the
end-to-end `flow where "<query>"` retrieval CLI surface that:

- fans out to **3 local backends** (repo code+tests via rg-or-grep, SDD
  archive via rg-or-grep, graphify graph index via Jaccard token-overlap);
- renders structured text output with **canonical `CODE / TESTS / SDD / GRAPH`
  section order**;
- applies **fail-open semantics** (graphify absent/malformed/empty → GRAPH
  section renders `unavailable / no graph index found`; missing
  `openspec/changes/archive/` → SDD section renders `(no matches)`);
- caps each backend at `--limit N` (default 20) hits;
- exposes a `--no-graph` opt-out flag;
- exits `0` always (even with zero hits — empty sections just render);
- ships **zero new Python deps** (no embeddings, no torch, no sqlite-vec,
  no optional-extras activation gate, no `FLOW_*` env var).

## Source

The authoritative requirements + BDD scenarios for this capability live in:

- `openspec/changes/archive/2026-06-28-flow-where-mvp/proposal.md`
  (initial scope lock + 3 backend + 4 REQ contract + risk matrix).
- `openspec/changes/archive/2026-06-28-flow-where-mvp/design.md`
  (D1 rg-or-grep subprocess seam + D2 SDD archive fail-soft +
  D3 graphify Jaccard fail-open + D4 Click subcommand + text formatter).
- `openspec/changes/archive/2026-06-28-flow-where-mvp/tasks.md`
  (Sub-batch A T1.1..T1.6 backend modules + Sub-batch B T2.1..T2.5
  graphify + CLI + BDD, ~300 impl + ~900 strict-TDD multiplier =
  ~1200 total LOC; single-PR delivery; 400-line budget risk LOW).
- `openspec/changes/archive/2026-06-28-flow-where-mvp/verify-report.md`
  (PASS-WITH-WARNINGS verdict + 22/22 spec scenarios + 24/24 NEW tests +
  4/4 smoke tests + 1403/1407 full suite + 0 mypy errors + ruff clean).

This file carries the **canonical requirement statements and BDD scenarios
that survive once the change ships** — REQ-V1.0.1..V1.0.4 catalogued in
one place. Future deltas (e.g., engram backend, `--json` flag, ranking/RRF,
REQ-NN cross-linking) extend this baseline rather than forking the
archived change spec.

## Requirements

### REQ-V1.0.1 — Repo grep backend (`grep_repo` + `split_code_vs_tests`)

The system SHALL provide a pure-library function
`where.grep_repo(query, *, limit=20, cwd=Path.cwd()) -> tuple[list[WhereHit], list[WhereHit]]`
at `src/flow_engineering/where.py:165-184` that:

- runs `subprocess.run(["rg", "--line-number", "--no-heading", "--color", "never", query, "src/", "tests/"], check=False)` via the `_run_search` helper;
- falls back to POSIX `grep -rn -H --color never -- <query> src/ tests/` when `shutil.which("rg") is None` (mirrors `graphify_query.py:87` precedent);
- parses `path:line[:col]` lines from stdout into `WhereHit` dataclasses via `_parse_hits`;
- splits hits via `split_code_vs_tests(hits)` — `path.startswith("tests/")` → TESTS bucket, else → CODE bucket;
- caps each bucket independently at `limit` hits via `_apply_limit`;
- returns `([], [])` on no-match (rg exit 1 → empty stdout → empty list);
- never raises on missing `src/` or `tests/` (empty stdout → empty lists).

The `split_code_vs_tests` helper at `src/flow_engineering/where.py:194-205`
is a pure partitioner preserving rg's natural order (path-asc, line-asc)
within each bucket.

### REQ-V1.0.2 — SDD archive grep backend (`grep_sdd_archive`)

The system SHALL provide a pure-library function
`where.grep_sdd_archive(query, *, limit=20, cwd=Path.cwd()) -> list[WhereHit]`
at `src/flow_engineering/where.py:208-237` that:

- resolves `archive_dir = cwd / "openspec/changes/archive/"`;
- returns `[]` immediately if `archive_dir.is_dir()` is False (fresh-clone
  fail-soft contract — no error, no traceback);
- otherwise invokes the shared `_run_search` helper with the archive path
  constant (no separate rg call vs. `grep_repo` — same argv pattern);
- caps results at `limit` hits via `_apply_limit`.

### REQ-V1.0.3 — Graphify fail-open backend (`grep_graphify`)

The system SHALL provide a pure-library function
`where.grep_graphify(query, *, limit=20, graph_path=DEFAULT_GRAPH_PATH) -> list[WhereHit] | None`
at `src/flow_engineering/where.py:240-350` that:

- reads `graph_path` (default `Path(r"c:\dev\proyects\flow-engineering\graphify-out\graph.json")`);
- returns `None` when the file is missing, malformed, or has empty `nodes`
  (the fail-open contract — callers render the deterministic token
  `unavailable / no graph index found` for `None` returns);
- otherwise tokenizes each node's `label + id + source_file` via the local
  `_tokenize` helper (lowercase + split on `_TOKEN_PATTERN` from
  `graphify_query.py:34` — duplicated for testability without cross-module
  import);
- scores each node via local `_jaccard` against the query's token set
  (mirrors `graphify_query.jaccard_fallback` at
  `graphify_query.py:217` — duplicated for the same reason);
- returns top-K hits sorted by score desc.

`try/except (OSError, json.JSONDecodeError)` wraps the parse path so a
malformed graph never crashes the orchestrator. The scorer is
**deliberately duplicated** (not imported) per D3 to keep `where.py`
independently testable with a fixture `graph.json` and zero dependency
on the graphify CLI surface.

### REQ-V1.0.4 — `flow where` CLI subcommand + text formatter

The system SHALL provide:

- A `@main.command(name="where")` registered at
  `src/flow_engineering/cli.py:373-402` (~10 LOC handler) that accepts
  positional `query` (str), `--limit INTEGER` (default 20), and
  `--no-graph` boolean flag (default False — GRAPH is opt-out).
- The handler delegates to `where_mod.where(query, limit=limit,
  no_graph=no_graph_flag)` and emits `click.echo(where_mod.render_text(result))`.
- A pure `where.where(query, *, limit=20, no_graph=False, graph_path=DEFAULT_GRAPH_PATH) -> WhereResult`
  orchestrator at `src/flow_engineering/where.py:353-410` that fans out
  to the 3 backends (skipping GRAPH when `no_graph=True` or when graph
  fetch fails) and assembles a `WhereResult` dataclass with
  `code: list[WhereHit]` + `tests: list[WhereHit]` + `sdd: list[WhereHit]` +
  `graph: list[WhereHit] | None` (None == unavailable) +
  `graph_skipped: bool`.
- A pure `where.render_text(result: WhereResult) -> str` formatter at
  `src/flow_engineering/where.py:443-463` that emits sections in
  **canonical order `CODE / TESTS / SDD / GRAPH`** (always — even when
  empty), with `(no matches)` for empty sections and the deterministic
  `unavailable / no graph index found` for GRAPH unavailable. Sections
  are joined with `"\n\n"` for stable grep-friendly output.
- A module-level `GRAPH_UNAVAILABLE_MESSAGE: str = "unavailable / no graph index found"`
  constant at `where.py:38` that tests + render layer import for matching.
- Exit code `0` always (even with zero hits); `2` only on unexpected exception.

## Public API surface (REQ-V1.0.1..V1.0.4)

```python
# src/flow_engineering/where.py — public symbols

DEFAULT_LIMIT: int = 20                                              # where.py:30
DEFAULT_GRAPH_PATH: Path = Path(r".../graphify-out/graph.json")      # where.py:31
GRAPH_UNAVAILABLE_MESSAGE: str = "unavailable / no graph index found"  # where.py:38

@dataclass(frozen=True)
class WhereHit:                                                       # where.py:48-59
    path: str
    line: int
    snippet: str | None = None

@dataclass(frozen=True)
class WhereResult:                                                    # where.py:356-372
    code: list[WhereHit]
    tests: list[WhereHit]
    sdd: list[WhereHit]
    graph: list[WhereHit] | None      # None == unavailable
    graph_skipped: bool

def grep_repo(query, *, limit=DEFAULT_LIMIT, cwd=Path.cwd()) -> tuple[list[WhereHit], list[WhereHit]]
def split_code_vs_tests(hits: list[WhereHit]) -> tuple[list[WhereHit], list[WhereHit]]
def grep_sdd_archive(query, *, limit=DEFAULT_LIMIT, cwd=Path.cwd()) -> list[WhereHit]
def grep_graphify(query, *, limit=DEFAULT_LIMIT, graph_path=DEFAULT_GRAPH_PATH) -> list[WhereHit] | None
def where(query, *, limit=DEFAULT_LIMIT, no_graph=False, graph_path=DEFAULT_GRAPH_PATH) -> WhereResult
def render_text(result: WhereResult) -> str
```

Private helpers (`_rg_argv`, `_grep_argv`, `_run_search`, `_parse_hits`,
`_apply_limit`, `_sdd_archive_dir`, `_tokenize`, `_jaccard`, `_node_tokens`,
`_parse_graph_line`, `_format_hit`, `_render_section`) are covered
transitively by the public-function tests but are NOT part of the public
contract.

## CLI surface (REQ-V1.0.4)

```
flow where "<query>"                   # 3 backend fan-out + structured text
flow where "<query>" --limit N         # cap each backend at N hits (default 20)
flow where "<query>" --no-graph        # skip GRAPH section entirely
flow where --help                      # list query + flags + section-order docs
```

Exit codes:
- `0` — always (even with zero hits; empty sections render `(no matches)`)
- `2` — only on unexpected internal exception in `where.py`

Output contract:
```
CODE
- src/flow_engineering/where.py:165
- src/flow_engineering/where.py:194

TESTS
- tests/unit/test_where.py:71

SDD
- openspec/changes/archive/2026-06-27-prompt-registry-pr2b/verify-report-pr2b.md:1

GRAPH
- src/flow_engineering/where.py:165 — module:where (confidence 0.78)

(unavailable / no graph index found when graph.json is absent)
```

## Cross-Impact

| Capability | Relationship |
|-----------|-------------|
| `decision-drift` (v0.8.0+) | Unrelated — `flow where` does NOT touch drift detection; grep + Jaccard surface is independent |
| `observability` (v0.7.0+) | Unrelated — `flow where` does NOT emit any metrics counters in MVP (4 PRE-EXISTING window-filter test failures live here, NOT in `where.py`) |
| `prompt-registry` (v0.8.0+) | Unrelated — `flow where` does NOT consume or render any `PROMPT_NAMES` entries |
| `vector-semantic-search` (#4, v0.4.0) | **Prior art avoidance** — `flow where` borrows the ABC + fail-open discipline + BDD-first test pattern but explicitly rejects #4's scope (no embeddings, no sqlite-vec, no torch, no `[vectors]` extra, no `FLOW_VECTOR_SEARCH=1` gate, no chained 2-PR plan). `flow where` is **grep over files that already exist on disk** — fundamentally different problem class. |
| `cross-project-federation` (#4, v0.5.0) | Unrelated — `flow where` is single-project (`Path.cwd()` only); no multi-project fan-out in MVP |

## Versioning

| Version | Date | Change | Status | Headline |
|---------|------|--------|--------|----------|
| **v0.8.2** | **2026-06-28** | **`flow-where-mvp` (#13)** | **✅ SHIPPED** | **REQ-V1.0.1..V1.0.4 — NEW `flow where "<query>"` retrieval CLI subcommand with 3 fail-open backends (repo grep + SDD archive grep + graphify Jaccard) + canonical `CODE / TESTS / SDD / GRAPH` text formatter + zero new Python deps + 22 NEW unit tests + 2 NEW BDD scenarios + 1403/1407 tests passing (+20 net vs `7f8da73` baseline) + 0 CRITICAL / 2 WARNING / 2 SUGGESTION (PASS WITH WARNINGS — accepted per drift-hardening/v0.9.0/v1.0/v1.1/v1.2 precedent); single PR (Sub-batch A: T1.1..T1.6 backend modules + Sub-batch B: T2.1..T2.5 graphify + CLI + BDD), 11 work-unit commits on `main` (HEAD `7874bbc`). CHANGE #13 (`flow-where-mvp`) CLOSED.** |

**Carry-forwards NOT closed** (deferred to Opción media backlog per `proposal.md:113-122` + `verify-report.md` lines 317-327):

- **Engram backend** (4th backend via `engram_io.EngramClient.mem_search` filtered by topic_key prefix) — explicit user decision to defer until MCP plumbing is stable.
- **`--json` flag** (machine-readable output) — text is the v0 contract.
- **Ranking / RRF / BM25** (rg's natural order is sufficient for MVP).
- **Commit SHA references** (`git log -S` integration).
- **REQ-NN cross-linking** (`binding.split_prose_and_refs` seam preserved).
- **Confidence scores on CODE/TESTS/SDD** (only GRAPH carries confidence).
- **Watch / daemon mode** (irrelevant for read-only CLI).
- **Persistent index / cache** (every call is fresh; rg is fast enough).
- **`shlex.quote` application for literal query semantics** (W1 carry-forward — design deviation).
- **Windows cp1252 console encoding fallback at `cli.py:402`** (S1 carry-forward — Windows-only Unicode handling).
- **4 PRE-EXISTING observability/metrics window-filter failures** (W2 carry-forward — unrelated to `flow where`; confirmed failing on baseline commit `7f8da73`).

These carry-forwards do NOT block the archive; they are documented for the next change planning cycle per `verify-report.md` lines 317-327.