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

---

## 0. How to read this spec

> **Family index, not canonical source.** Canonical cross-project requirements live in the delta spec under `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md`. This file anchors the `flow-where` capability family across two generations (`REQ-V1.0.1..V1.0.4` shipped as v0.8.2 + the Phase 2 `REQ-WHERE-*` family shipped as v0.9.0) and provides cross-references for navigation. Each root-level `REQ-WHERE-*` block below cites its delta source via the `Source:` field. Do not treat this file as the source of truth for cross-project behavior — that is what the delta spec is for.

## 4.b Phase 2 cross-project search (v0.9.0)

**Phase 2** extends `flow where "<query>"` to operate across **N projects under a single `--root PATH`**, scanning exactly **6 locked directories per project** (`src/ internal/ cmd/ tests/ openspec/ graphify-out/`). The extension ships with **3 output formats** (`text/json/tsv`), **2 opt-in flags** (`--regex` + `--engram` stub), and a **new exit-code contract** (0 = match-or-empty, 1 = no-match, 2 = error — replaces v0.8.2's "always exit 0").

The canonical delta spec (full Given/When/Then scenarios + 10 acceptance criteria) lives at:

- **`openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md`** — recovered byte-identical from git commit `27111ed` (2026-06-29, "chore(archive): add flow-where-cross-project artifacts"). 155 lines; 6 `ADDED Requirements`; 13 Given/When/Then scenarios; 10 acceptance criteria.

**Test pointer**: `tests/unit/test_cli_where_cross_project.py` — **10 unit tests** covering text/json/tsv formatting, regex validation, limit caps, root resolution, exit-code trio, engram no-op identity, byte-identical-across-invocations, and scope discipline excluding `node_modules`. All 10 tests ship on `main` HEAD `920d395` (untouched by this doc-only change).

**Private helpers added in Phase 2** (leading underscore; NOT part of public API — covered transitively by the 10 unit tests):

- `_search_projects_for_query(root, query, regex_flag, limit)` — cross-project orchestrator at `cli.py:435-489`
- `_format_where_text(hits)` / `_format_where_json(hits)` / `_format_where_tsv(hits)` — three output formatters at `cli.py:564-653`
- `_validate_regex_or_exit(query)` — `re.compile` validation with exit 2 on `re.error` at `cli.py:656-668`
- `_resolve_cross_project_root(root_arg)` — `--root` path resolution at `cli.py:671-682`
- `_tag_match_type(file_path)` — path-prefix → type mapping (`code/test/sdd/graph`) at `cli.py:416-432`
- `_parse_cross_project(output)` — workaround for `where._parse_hits` colon-segmentation bug at `cli.py:516-551`
- `_strip_trailing_colon(output)` — workaround for rg `:` collision at `cli.py:492-513`
- `_ascii_safe_local(s)` — inline ASCII-safe normalizer for cross-project formatters at `cli.py:554-561`

### REQ-WHERE-CROSS-PROJECT-SCOPE

`flow where "<query>" --root PATH` MUST fan out across N projects, scanning exactly these 6 locked directories per project: `src/` (type `code`), `internal/` (type `code`), `cmd/` (type `code`), `tests/` (type `test`), `openspec/` (type `sdd`), `graphify-out/` (type `graph`). Missing subdirectories MUST be silently skipped. Files outside the 6 locked directories MUST NEVER be scanned regardless of query match.

**Source:** `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` §REQ-CROSS-PROJECT-SCOPE

**Wording:** Canonical wording (including Given/When/Then scenarios S1 + S2: cross-project scans 6 dirs + missing dir skipped) lives at the source. This root-level summary exists for navigation only.

**Out of scope:** The specific `_search_projects_for_query(root, query, regex_flag, limit)` signature; the per-directory `_run_search` dispatch pattern; the `_CROSS_PROJECT_DIRS` tuple literal at `cli.py:403-410`.

### REQ-WHERE-DEFAULT-TEXT-FORMAT

Without `--format`, the command MUST emit ASCII-safe text grouped by project. Each project section MUST contain: a `project_name` header line, rows of `file:line  content` (tab-aligned), and a TOTAL summary line. The output MUST NOT contain box-drawing characters or non-ASCII bytes. Empty match sets render `(no matches)` per project with `matches: 0` in TOTAL.

**Source:** `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` §REQ-DEFAULT-TEXT-FORMAT

**Wording:** Canonical wording (Given/When/Then scenarios: default multi-project text + empty match renders `(no matches)`) lives at the source.

**Out of scope:** The specific `_format_where_text` row-formatting code path; the `(no matches)` placeholder string literal; the TOTAL summary line schema.

### REQ-WHERE-EXPLICIT-FORMAT-FLAG

`--format {text,json,tsv}` MUST produce exactly one of three formats. `--format=text` is the ASCII-safe grouped text (REQ-WHERE-DEFAULT-TEXT-FORMAT). `--format=json` emits a single JSON envelope with `version: "1"` as the first key, plus `root`, `query`, `format`, `results[]` (each item has `project`, `file`, `line`, `content`, `type`), `totals` (`projects_searched` + `matches`), and an `engram: {enabled: false, phase: "stub"}` field. `--format=tsv` emits TSV with header `project\tfile\tline\ttype\tcontent` and `\n`-escaped content rows.

**Source:** `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` §REQ-EXPLICIT-FORMAT-FLAG

**Wording:** Canonical wording (Given/When/Then scenarios for JSON envelope structure + TSV header/body) lives at the source.

**Out of scope:** The specific `_format_where_json` + `_format_where_tsv` implementations; the exact JSON key ordering invariant; the TSV content escape sequences.

### REQ-WHERE-EXIT-CODE-MAPPING

The system MUST exit with code `0` when matches are found OR when no matches exist (empty set). The system MUST exit with code `1` when NO matches are found. The system MUST exit with code `2` for errors: invalid `--regex` pattern, unreadable `--root` path, or other CLI-level failures.

**Behavior change from v0.8.2**: v0.8.2 was always exit `0`; v0.9.0 introduces exit `1` for the no-match case (greppish convention). Documented as a user-visible change in the v0.9.0 versioning row.

**Source:** `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` §REQ-EXIT-CODE-MAPPING

**Wording:** Canonical wording (Given/When/Then scenarios for exit 0/1/2) lives at the source.

**Out of scope:** The specific `re.error` handling in `_validate_regex_or_exit`; the disk-read error paths in `_resolve_cross_project_root`; the CLI-level exception catch-all.

### REQ-WHERE-ENGRAM-STUB

The `--engram` flag MUST be accepted with no behavior change in v0.9.0. The flag MUST NOT cause an error. In `--format=json` output, the `engram` field MUST be present as `{enabled: false, phase: "stub"}`. Phase 4+ is reserved for real Engram MCP/API integration.

**Source:** `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` §REQ-ENGRAM-STUB

**Wording:** Canonical wording (Given/When/Then scenarios for flag acceptance + JSON envelope stub identity) lives at the source.

**Out of scope:** Real Engram MCP wiring; the `--engram` no-op Click-option line at `cli.py:701-706` (forward-looking placeholder).

### REQ-WHERE-REGEX-OPT-IN

The `--regex` flag MUST enable regex matching. Without `--regex`, matching is case-insensitive substring (default). With `--regex`, `re.compile(query)` MUST be called at the CLI boundary to validate the pattern; on `re.error`, the system MUST exit code `2`.

**Source:** `openspec/changes/flow-where-cross-project-capability-merge/specs/cross-project-search/spec.md` §REQ-REGEX-OPT-IN

**Wording:** Canonical wording (Given/When/Then scenarios for valid-regex match + invalid-regex exit 2) lives at the source.

**Out of scope:** The regex flavor (Python `re` module, not POSIX ERE); the case-sensitivity default (always case-insensitive regardless of `--regex`); the W1 carry-forward `shlex.quote(query)` application (open design deviation from `flow-where-mvp`).

## 8. Drift Detection

> **How drift is mitigated between this root spec and the Phase 2 delta spec.**

- **Source-of-truth rule**: Each `REQ-WHERE-*` block in §4.b carries a `Source:` line citing the exact delta spec path + delta REQ ID. Canonical wording, Given/When/Then scenarios, and acceptance criteria live at the delta spec; root-level summaries exist for navigation only.
- **Acceptance check**: `sdd-verify` validates that every `REQ-WHERE-*` block in §4.b has a `Source:` line, that the cited delta spec path exists on disk, and that every cited delta REQ ID is found in the cited delta file (mirrors the `workspace-capability-bootstrap` design #492 checks 1–3).
- **Delta-evolution protocol**: When a delta REQ is updated (or a new delta is added), the corresponding root REQ summary should be reviewed for drift. When a delta REQ is deprecated, remove the root REQ block and the corresponding `Source:` line; do not leave stale root REQs behind.
- **Behavior-change protocol**: REQ-WHERE-EXIT-CODE-MAPPING documents a user-visible behavior change from v0.8.2 (always exit 0 → 0/1/2 trio). Any future change that touches the exit-code contract MUST update both the delta REQ-EXIT-CODE-MAPPING and this root REQ-WHERE-EXIT-CODE-MAPPING block simultaneously to keep them in lockstep.
- **Open improvement (out of scope for this change)**: automated drift detection via `sdd-verify` — could parse `Source:` lines and confirm path validity + the cited REQ still exists in the delta spec. Deferred until a CI hook for OpenSpec specs exists.

> **Reviewer hint**: When reviewing a `flow-where`-related PR, start at this root spec for the family shape, then follow each `Source:` line to the canonical delta REQ for full Given/When/Then scenarios and acceptance criteria. Do not edit root-level wording without checking the delta first.