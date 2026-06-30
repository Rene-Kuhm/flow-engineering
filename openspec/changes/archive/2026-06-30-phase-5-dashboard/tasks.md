# Tasks: `phase-5-dashboard` — Read-only Rich Dashboard (Approach E)

> **Change**: `phase-5-dashboard`
> **Phase**: 5 of 8 — `sdd-tasks`
> **Project**: flow-engineering v1.2.0 · main HEAD `6133e70` · `pyproject.toml` Python 3.12 / uv-managed
> **Strict TDD**: **ON** (feature change; `uv run --frozen pytest`; RED → GREEN → REFACTOR at every wave)
> **Test runner (preflight-locked)**: `uv run --frozen pytest` · lint `uv run --frozen ruff check .` · types `uv run --frozen mypy src/`
> **PR strategy (user-locked)**: **Option B — chained by wave** (3 PRs; each independently mergeable; each ≤ 400-line review budget)
> **Inputs (authoritative)**: design #541 (641 LF, 8 verify checks, 7 TDD waves, insertion point `cli.py:3034`); spec #539 (185 LF delta + 378 LF canonical, 6 root REQs + 7 delta-internal REQs); proposal #537 (196 LF, Approach E, `--json` REMOVED per Pattern #538)
> **Output**: this `tasks.md` (15 tasks across 7 TDD waves grouped into 3 chained PRs) + Engram mirror

---

## Review Workload Forecast

> **MANDATORY** per `sdd-phase-common.md` §E. Forecast measured against design #541 + spec #539 + proposal #537 + workspace/spec.md.

| Field | Value |
|---|---|
| `forecast_loc_total` | **~692 LOC** (impl + tests + cli edit + verify script) |
| `forecast_loc_per_pr.pr1` | **~120 LOC** (Wave 1+2 — fetchers + subprocess wrappers + 3 exceptions + tests) |
| `forecast_loc_per_pr.pr2` | **~200 LOC** (Wave 3+4 — filter + sort + color + 4 Rich renderers + tests) |
| `forecast_loc_per_pr.pr3` | **~210 LOC** (Wave 5+6+7 — Click integration `+32` to `cli.py` + CliRunner tests + 60 LOC verify script + AC walkthrough) |
| `forecast_loc_per_file.src/flow_engineering/dashboard.py` | **~250 LOC** (NEW; 3 fetchers + 3 logic + 5 renderers + 1 Click handler + 1 internal helper + 3 exception classes + module docstring) |
| `forecast_loc_per_file.tests/unit/test_dashboard.py` | **~350 LOC** (NEW; 8 test classes; ~24 tests; design §6.2) |
| `forecast_loc_per_file.src/flow_engineering/cli.py` | **+32 LOC** (MODIFY at `L3034`; design §5 verified insertion point) |
| `forecast_loc_per_file.openspec/changes/phase-5-dashboard/scripts/verify-checks.sh` | **~60 LOC** (NEW; the 8 check one-liners from design §8) |
| `chained_pr_recommendation` | **yes** — Option B (chained by wave; user preference locked at preflight) |
| `chained_pr_rationale` | Total ~692 LOC exceeds 400-line single-PR budget by ~73%. Chained by wave aligns with the 7 TDD cycles; each PR ships a coherent testable capability (subprocess wrappers / logic+rendering / integration+verify). Matches user preference (Option B locked at this tasks phase) and Pattern #542 ("chain by wave not by capability"). |
| `400_line_budget_risk` | **high** (single-PR would be ~692 LOC vs. 400 budget) |
| `size_exception_required` | **no** — Option B chains each PR under budget (max ~210 LOC) |
| `decision_needed_before_apply` | **no** — user locked Option B at this tasks phase |
| `decision_question` | **null** |

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: high
```

**Chain strategy = `feature-branch-chain`** per `chained-pr` skill §3: the dashboard is one vertically integrated user-facing feature, so a tracker branch (`feature/phase-5-dashboard`) accumulates the final integration; PR #1 targets the tracker branch; PR #2 targets PR #1's branch; PR #3 targets PR #2's branch. Only the tracker merges to `main` (no premature intermediate merge noise).

---

## PR strategy decision (LOCKED)

> User preflight explicitly required: *"PR strategy: Option B — chained by wave (user preference, locked)"*. No design-time or apply-time re-decision permitted.

| PR | Scope (waves) | Title | LOC est | Independently mergeable? | Base branch |
|----|--------------|-------|---------|--------------------------|-------------|
| **PR1** | Wave 1 + Wave 2 | `feat(dashboard): subprocess wrappers + fetchers` | ~120 LOC | **Yes** (no Click, no rendering, no flags) | `feature/phase-5-dashboard` |
| **PR2** | Wave 3 + Wave 4 | `feat(dashboard): filter + sort + color + rich rendering` | ~200 LOC | Depends on PR1 (uses fetcher return types) | PR1 branch |
| **PR3** | Wave 5 + Wave 6 + Wave 7 | `feat(dashboard): click integration + verify script + ACs` | ~150 + 60 LOC | Depends on PR2 (uses renderers) | PR2 branch |

**Single commit per PR** (per `work-unit-commits` skill + AGENTS.md no-AI-attribution rule). Conventional commits format. PR3 carries the verify script in its commit (one commit; verify script is non-runtime infra).

---

## Task summary table

> Mechanical decomposition of design #541 §7 (7 TDD waves) into 15 tasks. Wave↔test mapping follows design §6.1 test class matrix.

| Wave | Task ID | Title | Tests (RED) | Impl (GREEN) | LOC delta |
|------|---------|-------|-------------|--------------|-----------|
| W1 | PR1-W1-T1 | `fetch_project_list` + `_run_subprocess_json` + 3 exceptions | 4 (happy + 3 error paths) | 3 exceptions + DS1 subprocess wrapper | +60 |
| W2 | PR1-W2-T2 | `fetch_status_summary` (DS2) | 2 (happy + 1 error) | DS2 subprocess wrapper | +25 |
| W2 | PR1-W2-T3 | `fetch_archived_projects` (DS5 direct) | 3 (happy + missing + malformed) | DS5 direct `load_registry()` read | +15 |
| W3 | PR2-W3-T4 | `filter_by_rules` (`--filter RULES`) | 3 (single/multi/invalid) | pure function + `_validate_filter_rules` | +18 |
| W3 | PR2-W3-T5 | `sort_projects` (`--sort FIELD`) | 4 (name/path/needs-count/invalid) | pure function | +16 |
| W3 | PR2-W3-T6 | `color_code` (red/yellow/green thresholds) | 3 (3+ / 1-2 / 0) | pure function | +6 |
| W4 | PR2-W4-T7 | `render_header` (Section A — Panel) | 1 (snapshot) | Rich `Panel` | +18 |
| W4 | PR2-W4-T8 | `render_needs_table` (Section B — color-coded Table) | 2 (snapshot + filter) | Rich `Table` + row styles | +35 |
| W4 | PR2-W4-T9 | `render_archived` (Section C — Table or None) | 1 (snapshot + empty) | Rich `Table` + dim row style | +18 |
| W4 | PR2-W4-T10 | `render_footer` (Section D — Text) | 1 (snapshot) | `Text.from_markup` | +8 |
| W4 | PR2-W4-T11 | `render_dashboard` (composes A+B+C+D into `Group`) | 2 (snapshot + no-archived) | `rich.console.Group` composer | +15 |
| W5 | PR3-W5-T12 | `workspace_dashboard_cmd` Click handler at `cli.py:3034` | 4 (CliRunner happy/filter/sort/no-color) | decorator chain + handler body + imports | +32 |
| W6 | PR3-W6-T13 | `verify-checks.sh` (8 structural checks) + AC9 byte-identical guard re-run | 8 (one-liners, exit 0) | the 8 check scripts from design §8 | +60 (script) |
| W7 | PR3-W7-T14 | Full suite `1513+24=1537` must pass (preflight baseline `1513/1513`) | 0 new tests | GREEN full suite | 0 |
| W7 | PR3-W7-T15 | AC1–AC15 walkthrough + AC9 byte-identical guard + visual capture | 0 new tests | document pass / fail per AC | 0 |

**Total: 15 tasks · ~692 LOC · ~24 new tests · 1 verify script · 0 new deps.**

---

## Task definitions

> Per-task schema: Task ID · Title · Goal · RED step · GREEN step · REFACTOR · Files · Pre-req · Acceptance criteria · Risk notes.
> All RED steps invoke `uv run --frozen pytest tests/unit/test_dashboard.py -x -k <pattern> -v`. Strict TDD preflight = ON; no fallback to Standard Mode.

---

### PR1 — `feat(dashboard): subprocess wrappers + fetchers` (Wave 1 + Wave 2)

#### PR1-W1-T1 — `fetch_project_list` + `_run_subprocess_json` + 3 exceptions

- **Goal**: Implement DS1 subprocess wrapper (`flow projects ls --json`) with 3 specific failure-mode exceptions, behind a single internal helper.
- **RED step**: write `tests/unit/test_dashboard.py::TestFetchProjectList` (4 tests): `test_fetch_project_list_happy_path`, `test_fetch_project_list_non_zero_exit`, `test_fetch_project_list_json_parse_error`, `test_fetch_project_list_binary_not_found`. Mock `dashboard_mod.subprocess.run` with canned `CompletedProcess` instances via `monkeypatch.setattr` (mirror `tests/unit/test_where.py:191` pattern). Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestFetchProjectList -x -v` — must FAIL with `ImportError: cannot import name 'fetch_project_list'`.
- **GREEN step**: implement in `src/flow_engineering/dashboard.py`: 3 exception classes (`DashboardSubprocessError(RuntimeError)`, `DashboardParseError(RuntimeError)`, `DashboardBinaryNotFoundError(RuntimeError)`) + private `_run_subprocess_json(cmd: list[str], *, timeout: int = 10) -> dict[str, Any]` helper (`subprocess.run(..., capture_output=True, text=True, encoding="utf-8", check=False)`; branch on `returncode`/`FileNotFoundError`/`json.JSONDecodeError` per design §3) + public `fetch_project_list(*, flow_bin: str = "flow") -> list[dict[str, Any]]` calling `_run_subprocess_json(["flow", "projects", "ls", "--json"])`. All 4 RED tests turn GREEN.
- **REFACTOR step**: type hints; docstring cross-referencing design §3 divergence from `_run_search` (`check=False` for SPECIFIC error classes, not fail-open).
- **Files affected**: NEW `src/flow_engineering/dashboard.py` (partial); NEW `tests/unit/test_dashboard.py` (partial).
- **Pre-requisites**: none (first task in PR1).
- **Acceptance criteria**: AC3 (subprocess DS1 succeeds); AC5 (partial — registry missing → empty, deferred to T3).
- **Risk notes**: Windows cp1252 encoding on non-ASCII paths — `encoding="utf-8"` argument forces UTF-8 at the wrapper layer; project-level stdout may still carry cp1252 bytes if a downstream call lacks `encoding`. Test the happy path with ASCII-only envelope to keep this PR focused.

#### PR1-W2-T2 — `fetch_status_summary` (DS2 subprocess wrapper)

- **Goal**: Implement DS2 subprocess wrapper (`flow workspace status --json`) returning the parsed needs-attention envelope.
- **RED step**: add `tests/unit/test_dashboard.py::TestFetchStatusSummary` (2 tests): `test_fetch_status_summary_happy_path`, `test_fetch_status_summary_non_zero_exit`. Mock `dashboard_mod.subprocess.run`. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestFetchStatusSummary -x -v` — must FAIL.
- **GREEN step**: in `dashboard.py`, implement `fetch_status_summary(*, flow_bin: str = "flow") -> dict[str, Any]` calling `_run_subprocess_json(["flow", "workspace", "status", "--json"])`. Reuses T1's helper + 3 exception classes (zero duplication). Both RED tests turn GREEN.
- **REFACTOR step**: none required.
- **Files affected**: `src/flow_engineering/dashboard.py`; `tests/unit/test_dashboard.py`.
- **Pre-requisites**: PR1-W1-T1 (helper + exception classes exist).
- **Acceptance criteria**: AC4 (subprocess DS2 succeeds).
- **Risk notes**: `_run_subprocess_json` was designed DS1-specific in T1; refactor only if T2 reveals a divergence (unlikely — same `subprocess.run` shape).

#### PR1-W2-T3 — `fetch_archived_projects` (DS5 direct `load_registry()` read)

- **Goal**: Implement DS5 direct read (`load_registry()` from `flow_engineering.registry`) returning the archived list, gracefully handling missing/malformed registry.
- **RED step**: add `tests/unit/test_dashboard.py::TestFetchArchivedProjects` (3 tests): `test_fetch_archived_happy_path` (registry with 2 archived entries), `test_fetch_archived_missing_registry_returns_empty` (`monkeypatch` `Path.home()` to a non-existent dir), `test_fetch_archived_malformed_registry_raises`. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestFetchArchivedProjects -x -v` — must FAIL.
- **GREEN step**: in `dashboard.py`, implement `fetch_archived_projects() -> list[dict[str, Any]]` that calls `load_registry()` and returns `reg.archived` (the `ArchivedEntry` list, projected to dicts with `name`/`path`/`archived_at`/`reason` keys). Missing file path: `load_registry()` already returns empty `Registry()` per `registry.py:144`. Malformed JSON path: catches `RegistryError` (or `json.JSONDecodeError`) and re-raises as `DashboardParseError` for parity with the DS1/DS2 wrappers.
- **REFACTOR step**: type the returned list shape (`list[dict[str, Any]]` with the 4 keys) in the docstring.
- **Files affected**: `src/flow_engineering/dashboard.py`; `tests/unit/test_dashboard.py`.
- **Pre-requisites**: PR1-W1-T1.
- **Acceptance criteria**: AC5 (registry missing → empty default).
- **Risk notes**: registry projection (Pydantic `ArchivedEntry` → dict) is a coercion hot-spot — keep the dict keys literal (`str(entry.name)`, etc.) per the precedent at `cli.py:_format_archived_text_table` (`str(entry.name)`, `str(entry.archived_at)`, `str(entry.reason)`) for Pydantic v2 forward-compat.

---

### PR2 — `feat(dashboard): filter + sort + color + rich rendering` (Wave 3 + Wave 4)

#### PR2-W3-T4 — `filter_by_rules` (--filter RULES)

- **Goal**: Pure function implementing `--filter RULES` R1–R5 filtering of (projects, needs_attention) pairs.
- **RED step**: add `tests/unit/test_dashboard.py::TestFilterByRules` (3 tests): `test_filter_single_rule_R2_keeps_only_no_git`, `test_filter_multiple_rules_R1_R3_union`, `test_filter_invalid_rule_raises_click_usage_error`. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestFilterByRules -x -v` — must FAIL.
- **GREEN step**: in `dashboard.py`, implement `filter_by_rules(projects, needs_attention, rules: tuple[str, ...]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]` + private `_validate_filter_rules(rules)` (accepts only `{"R1","R2","R3","R4","R5"}`; raises `click.UsageError` for unknowns). Filter logic: keep a project only if its needs_attention entry has at least one matching rule in `reasons[]`. Use set intersection.
- **REFACTOR step**: docstring with the 5 R-names spelled out (R1 dirty / R2 no-git / R3 no-tests / R4 no-openspec / R5 no-graphify).
- **Files affected**: `src/flow_engineering/dashboard.py`; `tests/unit/test_dashboard.py`.
- **Pre-requisites**: PR1-W2-T2 (uses `needs_attention` shape).
- **Acceptance criteria**: AC6 (`--filter RULES` works; e.g. `--filter R2` shows only no-git).
- **Risk notes**: `click` import inside `dashboard.py` is a new dependency for the module (Click is already a direct dep — zero-cost). Keep `_validate_filter_rules` lazy-imported inside the function to avoid module-load side effects.

#### PR2-W3-T5 — `sort_projects` (--sort FIELD)

- **Goal**: Pure function implementing `--sort FIELD` (`name` / `path` / `needs-count`).
- **RED step**: add `tests/unit/test_dashboard.py::TestSortProjects` (4 tests): `test_sort_by_name_default`, `test_sort_by_path`, `test_sort_by_needs_count_descending`, `test_sort_invalid_field_raises`. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestSortProjects -x -v` — must FAIL.
- **GREEN step**: in `dashboard.py`, implement `sort_projects(projects: list[dict[str, Any]], field: str) -> list[dict[str, Any]]`. Default = `name` (Click decorator in T12). Branches: `name` → `key=lambda p: p["name"]`; `path` → `key=lambda p: p["path"]`; `needs-count` → `key=lambda p: len(p.get("reasons", []))`, `reverse=True`. Invalid → `click.UsageError`.
- **REFACTOR step**: extract `_needs_count(project) -> int` helper (reused by T6 + T8).
- **Files affected**: `src/flow_engineering/dashboard.py`; `tests/unit/test_dashboard.py`.
- **Pre-requisites**: PR1-W2-T2 (uses needs_attention shape).
- **Acceptance criteria**: AC7 (`--sort FIELD` sorts correctly).
- **Risk notes**: `reasons` key may be absent on clean projects; `p.get("reasons", [])` keeps sorting stable.

#### PR2-W3-T6 — `color_code` (red/yellow/green thresholds)

- **Goal**: Pure function implementing the red/yellow/green color threshold logic.
- **RED step**: add `tests/unit/test_dashboard.py::TestColorCode` (3 tests): `test_color_code_red_when_3_or_more`, `test_color_code_yellow_when_1_to_2`, `test_color_code_green_when_zero`. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestColorCode -x -v` — must FAIL.
- **GREEN step**: in `dashboard.py`, implement `color_code(needs_count: int) -> str`: return `"red"` if `>= 3`, `"yellow"` if `1..=2`, `"green"` if `== 0`. Mirrors spec REQ-DASHBOARD-RENDERING color rule.
- **REFACTOR step**: constant tuple `(_RED_THRESHOLD, _YELLOW_LOWER, _YELLOW_UPPER) = (3, 1, 2)` for readability + easy threshold audit.
- **Files affected**: `src/flow_engineering/dashboard.py`; `tests/unit/test_dashboard.py`.
- **Pre-requisites**: PR2-W3-T5 (uses `_needs_count` helper).
- **Acceptance criteria**: AC10 (red ≥3 / yellow 1-2 / green 0).
- **Risk notes**: `int` return value contract is `str` (Rich color name). Do NOT return a `Color` object — keeps the function pure and testable without Rich imports in unit tests.

#### PR2-W4-T7 — `render_header` (Section A — Panel)

- **Goal**: Rich `Panel` rendering workspace totals + per-rule breakdown + run timestamp.
- **RED step**: add `tests/unit/test_dashboard.py::TestRenderHeader` (1 snapshot test): `test_render_header_golden_text`. Use `Console(record=True, file=io.StringIO())` + `console.export_text()` per design §6.1 precedent (`tests/unit/test_prompt_render_golden.py`). Assert exact substring match for "Workspace" + per-rule counts + timestamp ISO. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestRenderHeader -x -v` — must FAIL.
- **GREEN step**: in `dashboard.py`, implement `render_header(summary: dict[str, Any], *, no_color: bool = False) -> Panel`. Content from design §4.1: totals `['projects','needs_attention']`, per-rule breakdown `['dirty','no_git','no_tests']`, run timestamp `datetime.now(timezone.utc).isoformat(timespec="seconds")`. `border_style="cyan" if not no_color else None`. Wrap markup via `Panel.fit(...)` or `[bold]…[/bold]` (Rich markup). Title = `"flow workspace dashboard"`.
- **REFACTOR step**: extract `_format_timestamp() -> str` for snapshot stability.
- **Files affected**: `src/flow_engineering/dashboard.py`; `tests/unit/test_dashboard.py`.
- **Pre-requisites**: PR2-W3-T6.
- **Acceptance criteria**: AC2 (Rich table/panel default output).
- **Risk notes**: timestamp drift makes snapshot tests fragile — use `[TIMESTAMP]` literal placeholder in golden text + regex match (`\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}`) instead of exact match.

#### PR2-W4-T8 — `render_needs_table` (Section B — color-coded Table)

- **Goal**: Rich `Table` rendering project × R1–R5 matrix with row-color coding.
- **RED step**: add `tests/unit/test_dashboard.py::TestRenderNeedsTable` (2 tests): `test_render_needs_table_golden_text` (snapshot), `test_render_needs_table_filter_R2_only_no_git`. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestRenderNeedsTable -x -v` — must FAIL.
- **GREEN step**: in `dashboard.py`, implement `render_needs_table(projects, needs_attention, *, no_color: bool = False) -> Table`. Columns per design §4.2: `project | path (truncated 60ch via `_truncate_path`) | R1 | R2 | R3 | R4 | R5 | total`. Cell text: `✓` for satisfied, `R#` for triggered. Row border style: `color_code(needs_count)` (when `not no_color`; else `None`). Footer row: per-rule totals via `Table.add_row(…)` with `[bold]` markup.
- **REFACTOR step**: extract `_format_rule_cell(triggered: bool, rule: str) -> str` helper (reused in tests for assertions).
- **Files affected**: `src/flow_engineering/dashboard.py`; `tests/unit/test_dashboard.py`.
- **Pre-requisites**: PR2-W4-T7.
- **Acceptance criteria**: AC2 + AC6 + AC10.
- **Risk notes**: snapshot brittleness — anchor assertions on stable substrings ("project-1", "R1", "R2", column count), not exact multi-line layout. Rich layout varies slightly across versions.

#### PR2-W4-T9 — `render_archived` (Section C — Table or None)

- **Goal**: Rich `Table` for archived projects; returns `None` when empty so the caller omits the section.
- **RED step**: add `tests/unit/test_dashboard.py::TestRenderArchived` (1 test with 2 assertions): `test_render_archived_returns_none_when_empty`, `test_render_archived_golden_text_with_entries`. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestRenderArchived -x -v` — must FAIL.
- **GREEN step**: in `dashboard.py`, implement `render_archived(archived: list[dict[str, Any]]) -> Table | None`. Columns per design §4.3: `name | path | archived_at (ISO) | reason`. Default `row_style="dim"`. Empty list → return `None`.
- **REFACTOR step**: extract `_format_archived_at(iso: str) -> str` to keep ISO timestamps stable in snapshots.
- **Files affected**: `src/flow_engineering/dashboard.py`; `tests/unit/test_dashboard.py`.
- **Pre-requisites**: PR2-W3-T6 (color logic precedent, not strictly required).
- **Acceptance criteria**: AC2.
- **Risk notes**: `--no-color` does NOT affect archived section (always dim); this is intentional per design §4.3.

#### PR2-W4-T10 — `render_footer` (Section D — Text)

- **Goal**: Rich `Text` rendering the 2 tip pointers.
- **RED step**: add `tests/unit/test_dashboard.py::TestRenderFooter` (1 snapshot test): `test_render_footer_golden_text`. Assert exact substring match for both tip lines from design §4.4. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestRenderFooter -x -v` — must FAIL.
- **GREEN step**: in `dashboard.py`, implement `render_footer() -> Text` using `Text.from_markup("[dim]Tip:[/dim] …")` per design §4.4.
- **REFACTOR step**: none required (3 LOC).
- **Files affected**: `src/flow_engineering/dashboard.py`; `tests/unit/test_dashboard.py`.
- **Pre-requisites**: none.
- **Acceptance criteria**: AC2 + AC12 (no modifications to mutation commands; tip points operators to them).
- **Risk notes**: tip wording is byte-stable (no timestamps) — golden text can use exact-string match.

#### PR2-W4-T11 — `render_dashboard` (composes A+B+C+D into `Group`)

- **Goal**: Compose the 4 sections into a single `rich.console.Group` for atomic emission.
- **RED step**: add `tests/unit/test_dashboard.py::TestRenderDashboard` (2 tests): `test_render_dashboard_composes_all_four_sections`, `test_render_dashboard_omits_archived_when_empty`. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestRenderDashboard -x -v` — must FAIL.
- **GREEN step**: in `dashboard.py`, implement `render_dashboard(projects, summary, archived, needs_attention, *, no_color: bool = False) -> Group` per design §4.5. Sections appended in order A→B→(C if not None)→D.
- **REFACTOR step**: type the `Group` import as `from rich.console import Group` at module top.
- **Files affected**: `src/flow_engineering/dashboard.py`; `tests/unit/test_dashboard.py`.
- **Pre-requisites**: PR2-W4-T7 + PR2-W4-T8 + PR2-W4-T9 + PR2-W4-T10.
- **Acceptance criteria**: AC2 (full Rich output structure).
- **Risk notes**: `rich.console.Group` requires Rich ≥ 12.0 (verified at `uv.lock:1215` → `rich==15.0.0`).

---

### PR3 — `feat(dashboard): click integration + verify script + ACs` (Wave 5 + Wave 6 + Wave 7)

#### PR3-W5-T12 — `workspace_dashboard_cmd` Click handler at `cli.py:3034`

- **Goal**: Wire `dashboard.py` into the Click CLI by registering `workspace dashboard` immediately after `workspace status` (ends L3032).
- **RED step**: add `tests/unit/test_dashboard.py::TestWorkspaceDashboardCmd` (4 Click `CliRunner` tests): `test_click_invokes_dashboard`, `test_click_with_filter_R2`, `test_click_with_sort_needs_count`, `test_click_with_no_color_disables_ansi`. Use `click.testing.CliRunner` invoking the `workspace` group + `dashboard` subcommand (pattern from `tests/unit/test_cli_workspace_status.py`). Mock the 3 fetchers via `monkeypatch.setattr(dashboard_mod, "fetch_project_list", fake)` etc. Run `uv run --frozen pytest tests/unit/test_dashboard.py::TestWorkspaceDashboardCmd -x -v` — must FAIL (`No such command "dashboard"`).
- **GREEN step**: in `cli.py` at L3034 (between `workspace_status` ending L3032 and the `workspace_hygiene` section starting L3035), insert the handler from design §5: import block + `@workspace_group.command(name="dashboard")` decorator chain (`--filter`/`--sort`/`--no-color` options) + handler body (3 fetchers → filter → sort → `Console(no_color=no_color, soft_wrap=False).print(render_dashboard(...))`). ~32 LOC added at L3034. All 4 RED tests turn GREEN.
- **REFACTOR step**: extract `workspace_dashboard_cmd` body into a `dashboard_mod.run_dashboard(filter_rules, sort, no_color)` helper inside `dashboard.py` if the handler body exceeds 25 lines (improves testability; deferred decision until T12 implementation).
- **Files affected**: MODIFY `src/flow_engineering/cli.py` (+32 LOC at L3034); `tests/unit/test_dashboard.py`.
- **Pre-requisites**: PR2-W4-T11 (compose + renderers).
- **Acceptance criteria**: AC1 (Click registration under `workspace_group`); AC8 (`--no-color` disables ANSI); AC11 (zero new runtime deps — `rich` is already transitive); AC15 (`flow workspace status` text output unchanged).
- **Risk notes**: insertion point at L3034 is verified against current `cli.py` head (line 3034 begins `# =====...` block comment for hygiene). Adding the block BEFORE L3034 keeps the read-side commands grouped (status + dashboard) before the write-side block (fix/archive/archived/restore) — preserves the "observability first, mutations grouped" reading order per Pattern #536.

#### PR3-W6-T13 — `verify-checks.sh` (8 structural checks) + AC9 byte-identical guard re-run

- **Goal**: Author the 8-check verify script from design §8 at `openspec/changes/phase-5-dashboard/scripts/verify-checks.sh`; the 7 inherited checks re-validate that the canonical `workspace/spec.md` still has 12 root REQs (was 7; +5 dashboard REQs after this archive — wait, +6 dashboard REQs minus 1 placeholder = +5 net; placeholder REQ replaced by 6 REQs, so 7→12 net) with correct `Source:` lines, and Check 8 (NEW) guards the 6 dashboard REQ `Source:` paths.
- **RED step**: run each check as a one-liner (per design §8 verbatim patterns). All 8 must currently FAIL (Check 8 confirms `phase-5-dashboard/specs/workspace-dashboard/spec.md` is missing from the cited `Source:` lines because the workspace/spec.md §4 Source: lines were written in the spec phase; this task is to write the script, NOT to mutate the canonical spec). Run `uv run --frozen pytest` baseline first (expect 1513/1513 green, AC9 byte-identical guard green) — required to detect pre-existing drift.
- **GREEN step**: author `openspec/changes/phase-5-dashboard/scripts/verify-checks.sh` (~60 LOC): 8 `bash` one-liners from design §8 (Checks 1-7 verbatim; Check 8 is the new Python heredoc). `chmod +x` it. Run `./openspec/changes/phase-5-dashboard/scripts/verify-checks.sh` — all 8 must exit `0`. Then re-run `uv run --frozen pytest tests/unit/test_cli_projects.py::test_flow_projects_ls_json_byte_identical_envelope -xvs` (AC9 guard) — must remain green.
- **REFACTOR step**: add a top-level aggregation so a single `bash verify-checks.sh` runs all 8 sequentially and exits non-zero on any fail (per design §8.1 failure-mode matrix).
- **Files affected**: NEW `openspec/changes/phase-5-dashboard/scripts/verify-checks.sh` (~60 LOC).
- **Pre-requisites**: PR3-W5-T12 (the canonical spec must be archived with the dashboard REQ Source: lines; sdd-archive handles that, so this task runs against the as-yet-un-archived tree).
- **Acceptance criteria**: AC2 (verify checks preserve structural integrity); AC12 (AC9 byte-identical guard preserved).
- **Risk notes**: **at sdd-archive time** the cited path becomes `archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` (per design §8 Check 8 note). Check 8's regex must tolerate either path — use substring match `phase-5-dashboard/specs/workspace-dashboard/spec.md` (not exact path equality).

#### PR3-W7-T14 — Full suite `1513+24=1537` must pass

- **Goal**: Prove zero regression with the new dashboard code merged in.
- **Action**: `uv run --frozen pytest` — expect `1537 passed` (`1513 baseline + 24 new dashboard tests` per design §6.2).
- **Acceptance criteria**: AC13 (full suite green).
- **Risk notes**: if any new failure appears, STOP — the dashboard module must be self-contained. The 3 pre-existing ruff errors remain OOS; do NOT chase them.

#### PR3-W7-T15 — AC1–AC15 walkthrough (visual + automated)

- **Goal**: Execute each of the 15 acceptance criteria from proposal §7 and document PASS/FAIL.
- **Action**: per-AC verification (15 short notes in `verify-report.md` at sdd-verify time — this task is the runbook):
  - AC1: `uv run flow workspace --help` shows `dashboard` subcommand.
  - AC2: visual inspection of rendered output (Sections A+B+C+D present in golden text).
  - AC3-AC5: covered by T1-T3 unit tests.
  - AC6: visual inspection of `--filter R2` golden text.
  - AC7: visual inspection of `--sort needs-count` golden text (descending).
  - AC8: regex `re.search(rb"\x1b\[", stdout)` returns `None` when `--no-color` is set.
  - AC10: covered by T6 unit tests.
  - AC11: `uv pip install --dry-run rich` confirms no new packages.
  - AC12: AC9 byte-identical guard at `tests/unit/test_cli_projects.py:435` still green.
  - AC13: T14 covered.
  - AC14: workspace/spec.md §4 has 6 `REQ-WORKSPACE-DASHBOARD-*` REQs (no placeholder).
  - AC15: `flow workspace status` text output unchanged (golden text comparison).
- **Acceptance criteria**: AC1-AC15 PASS.
- **Risk notes**: AC1 + AC2 + AC6 + AC7 + AC8 + AC15 are manual; AC3-AC5 + AC10-AC14 are automated.

---

## Per-PR dependency graph

```text
                      main
                        │
                        ▼
            feature/phase-5-dashboard   (tracker / no-merge draft PR)
                        │
                        ▼
       ┌──────────────────────────────┐
PR1    │  feat(dashboard): fetchers   │  Wave 1 + Wave 2
       │  ────────────────────────── │  +120 LOC · ~7 tests
       │  T1  fetch_project_list      │  + exceptions + helper
       │  T2  fetch_status_summary    │
       │  T3  fetch_archived_projects │
       └──────────────┬───────────────┘
                      │ (merge PR1 to tracker)
                      ▼
       ┌──────────────────────────────┐
PR2    │  feat(dashboard): rendering  │  Wave 3 + Wave 4
       │  ────────────────────────── │  +200 LOC · ~11 tests
       │  T4  filter_by_rules         │
       │  T5  sort_projects           │  depends on T2 (needs_attention
       │  T6  color_code              │  shape from PR1)
       │  T7  render_header           │
       │  T8  render_needs_table      │
       │  T9  render_archived         │
       │  T10 render_footer           │
       │  T11 render_dashboard        │  composes T7-T10
       └──────────────┬───────────────┘
                      │ (merge PR2 to tracker)
                      ▼
       ┌──────────────────────────────┐
PR3    │  feat(dashboard): wire-up    │  Wave 5 + Wave 6 + Wave 7
       │  ────────────────────────── │  +210 LOC · ~6 tests + script
       │  T12 workspace_dashboard_cmd │  Click handler @ cli.py:3034
       │  T13 verify-checks.sh        │  8 check one-liners
       │  T14 full suite 1537/1537    │  no new tests
       │  T15 AC1-AC15 walkthrough    │  no new tests
       └──────────────┬───────────────┘
                      │
                      ▼
            feature/phase-5-dashboard   (now ready)
                      │
                      ▼  (sdd-archive)
              main (final merge)
```

**Chain strategy**: `feature-branch-chain` per `chained-pr` skill §3. The tracker PR (`feature/phase-5-dashboard` → `main`) stays in DRAFT / no-merge until PR1+PR2+PR3 all land. Each child PR targets its immediate parent (PR1 → tracker, PR2 → PR1's branch, PR3 → PR2's branch) so child diffs stay clean.

---

## Forecast

- **Total changed lines**: **~692 LOC** (sum of new file LOC + cli.py edits)
- **Per-PR LOC**: PR1 ~120, PR2 ~200, PR3 ~210 (each well under the 400-line review budget)
- **New files (3)**: `src/flow_engineering/dashboard.py` (~250) · `tests/unit/test_dashboard.py` (~350) · `openspec/changes/phase-5-dashboard/scripts/verify-checks.sh` (~60)
- **Modified files (1)**: `src/flow_engineering/cli.py` (+32 LOC at L3034)
- **Strict TDD cycles**: **~24 RED → GREEN cycles** across the 7 waves (T1=4 · T2=2 · T3=3 · T4=3 · T5=4 · T6=3 · T7=1 · T8=2 · T9=1 · T10=1 · T11=2 · T12=4)
- **Wave-by-wave LOC delta**: matches design §7 Table exactly (W1=+60, W2=+40, W3=+50, W4=+90, W5=+32, W6=+60 script, W7=0)

---

## PR commit hygiene (per `work-unit-commits` skill)

> Per AGENTS.md: **NO AI attribution** in any commit; **conventional commits** only.

| PR | Commit message | Files in commit | Atomicity |
|----|---------------|-----------------|-----------|
| **PR1** | `feat(dashboard): subprocess wrappers + fetchers (wave 1+2)` | NEW `src/flow_engineering/dashboard.py` (partial: helpers + 3 exceptions + DS1/DS2/DS5 fetchers) · NEW `tests/unit/test_dashboard.py` (partial: TestFetch*) | One work unit: "data acquisition layer". |
| **PR2** | `feat(dashboard): filter + sort + color + rich rendering (wave 3+4)` | MODIFY `src/flow_engineering/dashboard.py` (add logic + 4 renderers + composer) · MODIFY `tests/unit/test_dashboard.py` (add TestFilter/Sort/Color/Render*) | One work unit: "presentation layer". |
| **PR3** | `feat(dashboard): click integration + verify script + ACs (wave 5+6+7)` | MODIFY `src/flow_engineering/cli.py` (+32 LOC at L3034) · MODIFY `tests/unit/test_dashboard.py` (add TestWorkspaceDashboardCmd) · NEW `openspec/changes/phase-5-dashboard/scripts/verify-checks.sh` | One work unit: "wire-up + verification surface". |

**Commit narrative**: a reviewer should understand WHY each commit exists from its message alone. PR1 = "how does the dashboard read state". PR2 = "how does the dashboard present state". PR3 = "how does the dashboard become a CLI command + how is it verified".

---

## Pre-existing failures (out-of-scope reminder)

- **3 pre-existing ruff errors** remain OOS (carried from Phase 4 close-out per design §12):
  - `cli.py:682 RET504` (unnecessary assignment before return)
  - `test_cli_where_cross_project.py:33 UP035` (deprecated import)
  - `test_cli_where_cross_project.py:295 W292` (encoding warning)
- **0 pre-existing test failures** on main HEAD `6133e70` (1513/1513 baseline)
- **AC9 byte-identical guard** at `tests/unit/test_cli_projects.py:435` MUST stay green — preserved by the zero-modification policy to Phase 1 (`flow projects ls`) code paths in T1
- **AC15 byte-identical guard** on `flow workspace status` text output preserved by zero-modification policy to Phase 3 code paths in T2

---

## Acceptance criteria → task mapping (traceability)

| AC | Description (proposal §7) | Tasks |
|----|---------------------------|-------|
| AC1 | `flow workspace dashboard` registered under `workspace_group` | T12 |
| AC2 | Default output is Rich table/panel/section layout | T7, T8, T9, T10, T11, T15 |
| AC3 | Subprocess DS1 succeeds | T1, T15 |
| AC4 | Subprocess DS2 succeeds | T2, T15 |
| AC5 | Registry read works (missing → empty) | T3, T15 |
| AC6 | `--filter RULES` filters needs-attention | T4, T15 |
| AC7 | `--sort FIELD` sorts projects | T5, T15 |
| AC8 | `--no-color` disables ANSI | T12, T15 |
| AC9 | (implicit) byte-identical guard preserved | T1, T13 (re-run guard) |
| AC10 | Color coding red/yellow/green | T6, T8, T15 |
| AC11 | Zero new runtime deps | T15 (`uv pip install --dry-run rich`) |
| AC12 | AC9 byte-identical guard preserved | T13, T15 |
| AC13 | Full suite 1513 → 1537/1537 passes | T14, T15 |
| AC14 | `REQ-WORKSPACE-DASHBOARD-PLACEHOLDER` resolved | (delivered by spec phase; verified at archive) |
| AC15 | `flow workspace status` text output unchanged | T13 (re-run), T15 |

---

## Risk summary

Top 5 risks (carried from design #541 §11 + proposal §11):

| # | Risk | Severity | Mitigation in tasks |
|---|------|----------|---------------------|
| 1 | LOC ~692 exceeds 400-line single-PR budget | **HIGH** | **Chained by wave (Option B)** — each PR ≤ 220 LOC, well under 400. PR1 + PR2 + PR3 independently mergeable. |
| 2 | Rich snapshot tests brittleness across `rich` versions / OSes | MEDIUM | Anchor golden-text assertions on stable substrings ("project-1", column header "R1", timestamps via regex), not exact multi-line layout. Use `Console(record=True)` + `export_text()` for plain-text snapshots. |
| 3 | Subprocess latency (~100-200ms per DS1/DS2 call) | MEDIUM | Acceptable for on-demand refresh; no daemon. Document in CLI help text. |
| 4 | Windows cp1252 encoding on non-ASCII project paths | MEDIUM | `_run_subprocess_json` passes `encoding="utf-8"` to `subprocess.run`. ASCII-only test envelopes keep the test surface clean; non-ASCII is operator-side concern, not test-side. |
| 5 | Color accessibility (colorblind users) | LOW | Per design §4.2: text labels (`R1`, `R2`, …) appear alongside color codes (Pattern #536 — observability first; readable always). |

---

## Wall-time forecast

| Phase | Estimate | Rationale |
|-------|----------|-----------|
| `sdd-tasks` (this artifact) | ~25 min | Authored 15 tasks × full schema; Review Workload Forecast gate + chained-by-wave decomposition. |
| `sdd-apply` PR1 (W1+W2) | ~2-3 h | T1-T3 · 9 new tests · 3 fetchers + exceptions + helper. |
| `sdd-apply` PR2 (W3+W4) | ~1-2 h | T4-T11 · 11 new tests · logic + 4 renderers + composer. Reuses PR1 helpers. |
| `sdd-apply` PR3 (W5+W6+W7) | ~1-2 h | T12-T15 · 4 new tests · Click handler + verify script + full suite + AC walkthrough. |
| `sdd-verify` per PR | ~20-30 min | 8 verify checks + AC1-AC15 walkthrough + AC9 byte-identical guard re-run + full suite. |
| `sdd-archive` (final) | ~10 min | Move change folder to `archive/2026-06-30-phase-5-dashboard/`; merge deltas (placeholder REQ replaced with 6 dashboard REQs already done in spec phase); re-run 8 verify checks post-archive. |
| **Total remaining** | **~5-9 hours** | Consistent with design #541 §14 forecast and explore #535 verdict. |

---

## Commit plan (summary)

1. **PR1** — `feat(dashboard): subprocess wrappers + fetchers (wave 1+2)` — atomic; review ~12 min.
2. **PR2** — `feat(dashboard): filter + sort + color + rich rendering (wave 3+4)` — atomic; review ~18 min.
3. **PR3** — `feat(dashboard): click integration + verify script + ACs (wave 5+6+7)` — atomic; review ~22 min.

**Total review time**: ~52 min distributed across 3 PRs (vs. ~30-45 min single-PR Option A which requires `size:exception` justification).

---

## Out-of-scope task reminders

- **NO** tasks for: TUI framework selection (Textual/urwid/etc.) — deferred per REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE; web framework selection — same; real-time updates / file watching / websocket; interactive mutations from UI (Phase 5.2); i18n / theming / mobile; historical data / audit log; multi-user support; modifications to Phase 4 mutation gates (pollution-protocol triple, `MutationGateError`, `EmptyProjectError`); modifications to Phase 1/2/3/4 CLI commands (DS1/DS2/DS3/DS4 stay byte-identical); modifications to `openspec/changes/v1.1-followups/` (sacred territory); `size:exception` commitment (3 split options considered; Option B locked at this tasks phase); `feature-branch-chain` strategy re-decision (locked).
- **NO** `stash`-triggering words in any new artifact (per spec §Out of Scope).
- **NO** §3 / §5 / §7 cleanup of the workspace root spec (deferred to `workspace-dashboard-section-cleanup` follow-up per spec #539).
- **The 8 verify checks are the verification surface** (T13); they are NOT pytest tests and MUST NOT be added to the test suite.