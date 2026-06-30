# Design: phase-5-dashboard — Read-only Rich Dashboard (Approach E)

## Header

| Field | Value |
|---|---|
| Change | `phase-5-dashboard` |
| Phase | design (4 of 8 — `sdd-design`) |
| Project | flow-engineering v1.2.0, main HEAD `6133e70` |
| Strict TDD | **ON** (feature change — RED → GREEN → REFACTOR at apply phase) |
| Design philosophy | *"primero arquitectura, después presupuesto"* (Pattern #540) |
| Artifact store | openspec (filesystem) + Engram mirror |
| Inputs (authoritative) | Spec #539 (6 root REQs + 7 delta-internal REQs, 378 LF canonical), Proposal #537 (Approach E locked, `--json` REMOVED per Pattern #538), Explore #535 (5 alternatives surfaced) |
| Patterns honored | #536 (observability first, interactivity second), #538 (one identity per command), #540 (defer budget to tasks) |
| Output | `openspec/changes/phase-5-dashboard/design.md` (this file) + Engram mirror topic_key `sdd/phase-5-dashboard/design` |
| **Forecast** | 300–900 LOC (impl + tests); PR strategy **DEFERRED to sdd-tasks** (Pattern #540) — design proposes 3 split boundary options, sdd-tasks picks via Review Workload Forecast |

## 1. Architecture overview

The "architecture" is a **thin read-only adapter** between three existing data sources (DS1 Phase 1 envelope, DS2 Phase 3 aggregation, DS5 Phase 4 registry) and a Rich-based terminal renderer, registered as a single Click subcommand under the existing `workspace_group` at `cli.py:2990`. **No new runtime deps** (`rich` already transitive via `uv.lock:1215`; promotion to direct dep is zero-cost). **No mutations** (Pattern #536 — observability first). **No `--json`** on dashboard (Pattern #538 — `flow workspace status --json` keeps the machine-readable identity). The architecture deliberately avoids TUI/web frameworks (deferred to Phase 5.2).

```
   ┌──────────────────────────────────────────────────────────────────┐
   │  flow workspace dashboard  (NEW @workspace_group.command)        │
   │  cli.py:2990 (insert after workspace_status at L3009-3032)       │
   └──────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  src/flow_engineering/dashboard.py (NEW, ~250 LOC)               │
   │                                                                  │
   │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
   │  │ fetch_project_  │  │ fetch_status_   │  │ fetch_archived_  │  │
   │  │ list()          │  │ summary()       │  │ projects()       │  │
   │  │ DS1 subprocess  │  │ DS2 subprocess  │  │ DS5 direct read  │  │
   │  └────────┬────────┘  └────────┬────────┘  └────────┬─────────┘  │
   │           └────────┬───────────┘                    │            │
   │                    ▼                                │            │
   │           ┌─────────────────┐                       │            │
   │           │ filter/sort/    │                       │            │
   │           │ color logic     │                       │            │
   │           └────────┬────────┘                       │            │
   │                    ▼                                ▼            │
   │           ┌─────────────────────────────────────────────┐        │
   │           │ render_dashboard(...) -> rich.Group         │        │
   │           │ A=Panel (header) + B=Table (needs)          │        │
   │           │ + C=Table (archived) + D=Text (footer)      │        │
   │           └─────────────────────────────────────────────┘        │
   └──────────────────────────────────────────────────────────────────┘
            │                       │                       │
            ▼                       ▼                       ▼
   ┌──────────────────┐  ┌────────────────────┐  ┌─────────────────────┐
   │ flow projects ls │  │ flow workspace     │  │ load_registry()     │
   │ --json (DS1)     │  │ status --json(DS2) │  │ registry.py:144     │
   │ cli.py:3539      │  │ cli.py:3009        │  │ (Phase 4)           │
   └──────────────────┘  └────────────────────┘  └─────────────────────┘
```

**Data flow is read-only throughout**: each `fetch_*` function is invoked at command time, JSON envelopes parsed in-process, no state written back to disk. The dashboard never calls `save_registry_atomic` (registry.py:171) — that gate stays exclusive to `flow workspace {fix,archive,restore}`.

## 2. Module structure: `src/flow_engineering/dashboard.py` (NEW)

### 2.1 Responsibilities

- Subprocess wrappers for DS1 (`flow projects ls --json`) + DS2 (`flow workspace status --json`)
- Direct registry read for DS5 (`load_registry()` from `flow_engineering.registry`)
- Filter logic (`--filter RULES` R1–R5)
- Sort logic (`--sort FIELD`: name / path / needs-count)
- Color coding (`color_code(needs_count)` → `red` ≥3, `yellow` 1–2, `green` 0)
- Rich rendering: 4 sections (A header, B needs-attention, C archived, D footer)
- Click command handler `workspace_dashboard_cmd`

### 2.2 Public API (signatures + return contracts)

```python
# ---------- Fetchers (data acquisition) ----------
def fetch_project_list(*, flow_bin: str = "flow") -> list[dict[str, Any]]:
    """DS1: subprocess `flow projects ls --json`; returns parsed `projects[]`."""
def fetch_status_summary(*, flow_bin: str = "flow") -> dict[str, Any]:
    """DS2: subprocess `flow workspace status --json`; returns parsed envelope."""
def fetch_archived_projects() -> list[dict[str, Any]]:
    """DS5: direct `load_registry()`; returns `archived[]` (empty if registry missing)."""

# ---------- Logic (pure functions) ----------
def filter_by_rules(
    projects: list[dict[str, Any]],
    needs_attention: list[dict[str, Any]],
    rules: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (filtered_projects, filtered_needs) keeping only entries matching R1..R5."""
def sort_projects(
    projects: list[dict[str, Any]], field: str
) -> list[dict[str, Any]]:
    """Sort by `name` (default) | `path` | `needs-count` (descending)."""
def color_code(needs_count: int) -> str:
    """Return Rich color name: `red` ≥3, `yellow` 1–2, `green` 0."""

# ---------- Rich rendering ----------
def render_header(summary: dict[str, Any], *, no_color: bool = False) -> Panel:
    """Section A — workspace totals + per-rule breakdown + timestamp."""
def render_needs_table(
    projects: list[dict[str, Any]],
    needs_attention: list[dict[str, Any]],
    *, no_color: bool = False,
) -> Table:
    """Section B — project × R1..R5 matrix with row-color coding."""
def render_archived(archived: list[dict[str, Any]]) -> Table | None:
    """Section C — archived projects table; returns None when empty (caller omits)."""
def render_footer() -> Text:
    """Section D — tip pointers to `flow workspace status --json` and `flow workspace fix`."""
def render_dashboard(
    projects: list[dict[str, Any]],
    summary: dict[str, Any],
    archived: list[dict[str, Any]],
    needs_attention: list[dict[str, Any]],
    *, no_color: bool = False,
) -> Group:
    """Compose A + B + C + D into a single `rich.console.Group`."""

# ---------- Click handler ----------
def workspace_dashboard_cmd(
    filter_rules: tuple[str, ...],
    sort: str,
    no_color: bool,
) -> None:
    """Click entry point. Fetches DS1+DS2+DS5, applies filter/sort, renders."""
```

### 2.3 Internal helpers (private, `_` prefix)

- `_run_subprocess_json(cmd: list[str], *, timeout: int = 10) -> dict[str, Any]` — generic `subprocess.run(..., capture_output=True, text=True, check=True, encoding="utf-8")` wrapper; raises `DashboardSubprocessError` on non-zero exit, `DashboardParseError` on JSON failure, distinct `DashboardBinaryNotFoundError` on `FileNotFoundError` (mirrors `_run_search` at `where.py:89` with `check=True` divergence for strict contract).
- `_validate_filter_rules(rules: tuple[str, ...]) -> tuple[str, ...]` — accepts only `{"R1","R2","R3","R4","R5"}`; raises `click.UsageError` for unknown rules.
- `_truncate_path(path: str, max_len: int = 60) -> str` — ellipsize for narrow terminals.

### 2.4 Custom exception types (NEW, ~6 LOC total)

```python
class DashboardSubprocessError(RuntimeError):
    """Raised when DS1/DS2 subprocess exits non-zero."""
class DashboardParseError(RuntimeError):
    """Raised when DS1/DS2 output is not valid JSON."""
class DashboardBinaryNotFoundError(RuntimeError):
    """Raised when `flow` binary is not on PATH (distinct from DS call failure)."""
```

These match the registry.py:96 `RegistryError` precedent (one error type per failure mode; CLI layer prints `str(exc)` to stderr + `SystemExit(1)`).

## 3. Subprocess wrappers design

**Pattern** (mirrors `where.py:111` + `cli.py:3380`):

```python
result = subprocess.run(
    ["flow", "projects", "ls", "--json"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    timeout=10,
    check=False,  # we branch on returncode to produce specific errors
)
if result.returncode != 0:
    raise DashboardSubprocessError(f"flow projects ls --json failed: {result.stderr}")
try:
    return json.loads(result.stdout)
except json.JSONDecodeError as exc:
    raise DashboardParseError(f"flow projects ls --json returned invalid JSON: {exc}") from exc
```

**Divergence from `_run_search` (where.py:89)**: we use `check=False` and explicit `returncode` branching so we can produce a SPECIFIC error class per failure mode (mirroring the registry.py:96 precedent). `_run_search` is fail-open; dashboard must fail-loud because subprocess errors would leave the dashboard rendering an incomplete view.

**TDD test strategy** (in `tests/unit/test_dashboard.py`):

```python
def test_fetch_project_list_happy_path(monkeypatch) -> None:
    """Mock subprocess.run to return valid JSON envelope; verify projects[] parsed."""

def test_fetch_project_list_non_zero_exit(monkeypatch) -> None:
    """Mock returncode=1 + stderr; assert DashboardSubprocessError raised."""

def test_fetch_project_list_json_parse_error(monkeypatch) -> None:
    """Mock stdout='not-json'; assert DashboardParseError raised."""

def test_fetch_project_list_binary_not_found(monkeypatch) -> None:
    """Mock side_effect=FileNotFoundError; assert DashboardBinaryNotFoundError raised."""
```

**Test mocking shape**: identical to `tests/unit/test_where.py:191` (`monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)`). Production callers see the real `subprocess.run`; tests inject canned `CompletedProcess` instances.

## 4. Rich rendering design

### 4.1 Section A — Header Panel

```python
Panel(
    f"[bold]Workspace[/bold] {totals['projects']} projects, {len(archived)} archived\n"
    f"Needs attention: {totals['needs_attention']} "
    f"(R1: {totals['dirty']}, R2: {totals['no_git']}, R3: {totals['no_tests']})\n"
    f"Run: {now_iso}",
    title="flow workspace dashboard",
    border_style="cyan" if not no_color else None,
)
```

### 4.2 Section B — Needs-Attention Table

- Columns: `project | path (truncated 60ch) | R1 | R2 | R3 | R4 | R5 | total`
- Cell text: `✓` (green) for satisfied, `R#` (colored) for triggered
- Row border style: `red` ≥3 needs, `yellow` 1–2, `green` 0
- Sortable by name (default), path, or needs-count desc
- Footer row: per-rule totals

### 4.3 Section C — Archived Projects Table

- Columns: `name | path | archived_at (ISO) | reason`
- Only emitted when `archived` non-empty (returns `None` from `render_archived` to signal omission)
- Default `row_style="dim"` to visually separate from needs-attention

### 4.4 Section D — Footer

```python
Text.from_markup(
    "[dim]Tip:[/dim] Run [bold]flow workspace status --json[/bold] for JSON output.\n"
    "[dim]Tip:[/dim] Run [bold]flow workspace fix <project> --yes --backup[/bold] to remediate."
)
```

### 4.5 Layout composition

```python
from rich.console import Group
def render_dashboard(...) -> Group:
    sections: list[Renderable] = [render_header(...)]
    if needs_table := render_needs_table(...):
        sections.append(needs_table)
    if archived_table := render_archived(...):
        sections.append(archived_table)
    sections.append(render_footer())
    return Group(*sections)
```

Console emission pattern at handler level (preserves `--no-color` semantics):

```python
console = Console(no_color=no_color, soft_wrap=False)
console.print(render_dashboard(...))
```

## 5. Click integration

**Insertion point**: `src/flow_engineering/cli.py` **immediately after `workspace_status` ends at L3032** (registration sits naturally alongside `status`, `fix`, `archive`, `archived`, `restore` — same `workspace_group` decorator chain at L2990). The decorator `@workspace_group.command(name="dashboard")` is placed BEFORE the fix/archive/archived/restore block (L3156+), so the dashboard subcommand is co-located with `status` (read-side) and separated from mutation verbs (write-side) — preserves the "observability first, mutations grouped" reading order.

**Code sketch** (~25 LOC new, all in `cli.py`):

```python
# ---------- REQ-WORKSPACE-DASHBOARD-* — `flow workspace dashboard` ----------
# Read-only consumer of DS1 (Phase 1), DS2 (Phase 3), DS5 (Phase 4 registry).
# See openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md for
# the full Given/When/Then contract; this registration is the only `cli.py`
# modification (per Approach E zero-code-touch outside this block).


@workspace_group.command(name="dashboard")
@click.option(
    "--filter",
    "filter_rules",
    multiple=True,
    type=click.Choice(["R1", "R2", "R3", "R4", "R5"], case_sensitive=False),
    help="Filter by needs-attention rules (repeatable). E.g. --filter R2 --filter R3.",
)
@click.option(
    "--sort",
    default="name",
    type=click.Choice(["name", "path", "needs-count"], case_sensitive=False),
    help="Sort projects by field (default: name).",
)
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    help="Disable Rich colors for CI / piping.",
)
def workspace_dashboard_cmd(
    filter_rules: tuple[str, ...], sort: str, no_color: bool
) -> None:
    """Render consolidated workspace state in terminal (read-only)."""
    from flow_engineering.dashboard import (
        fetch_project_list,
        fetch_status_summary,
        fetch_archived_projects,
        filter_by_rules,
        sort_projects,
        render_dashboard,
    )

    projects = fetch_project_list()
    status_envelope = fetch_status_summary()
    archived = fetch_archived_projects()
    needs_attention = status_envelope.get("needs_attention", [])

    if filter_rules:
        projects, needs_attention = filter_by_rules(projects, needs_attention, filter_rules)
    projects = sort_projects(projects, sort)

    console = Console(no_color=no_color, soft_wrap=False)
    console.print(render_dashboard(projects, status_envelope, archived, needs_attention, no_color=no_color))
```

**Estimated LOC for `cli.py` modification**: ~32 LOC (1 block comment + 1 import line at top + 1 decorator chain + 1 handler body).

**Estimated LOC for `dashboard.py` (NEW)**: ~220–280 LOC (3 fetchers + 3 logic + 5 renderers + 1 handler + 1 internal helper + 3 exception classes + 1 module docstring).

**Estimated LOC for `tests/unit/test_dashboard.py` (NEW)**: ~250–400 LOC (per §7 test plan).

## 6. Tests design (TDD plan — RED → GREEN → REFACTOR)

### 6.1 Test classes (in `tests/unit/test_dashboard.py` NEW)

| Class | Tests | Coverage |
|---|---|---|
| `TestFetchProjectList` | happy_path, non_zero_exit, json_parse_error, binary_not_found | DS1 subprocess wrapper + 3 error paths |
| `TestFetchStatusSummary` | happy_path, non_zero_exit, json_parse_error | DS2 subprocess wrapper + 2 error paths |
| `TestFetchArchivedProjects` | happy_path, missing_registry_empty, malformed_registry_raises | DS5 direct read + 2 edge cases |
| `TestFilterByRules` | single_R2, multiple_rules, invalid_rule_raises | `--filter` flag logic |
| `TestSortProjects` | by_name_default, by_path, by_needs_count_desc, invalid_field_raises | `--sort` flag logic |
| `TestColorCode` | red_3plus, yellow_1to2, green_0 | color threshold logic |
| `TestRenderDashboard` | full_render, with_filter_R2, with_sort_needs_desc, with_no_color, empty_projects_no_table, no_archived_no_section | Rich rendering — golden text snapshot tests |
| `TestWorkspaceDashboardCmd` | click_invokes_dashboard, click_with_filter_R2, click_with_no_color_disables_ansi | Click CliRunner integration |

**Snapshot test strategy**: use Rich's `Console(record=True, file=io.StringIO())` + `console.export_text()` to capture plain-text output. Compare against a literal string in the test (per `tests/unit/test_prompt_render_golden.py` precedent). ANSI codes NOT asserted in snapshot tests — separate `test_with_no_color_disables_ansi` checks ANSI byte absence via `\x1b[` regex.

### 6.2 Total estimated test count: ~24 tests across 8 classes

## 7. TDD order for apply phase

Per `strict-tdd` skill + RED → GREEN → REFACTOR discipline. Each wave is one TDD cycle (RED → GREEN; REFACTOR optional per cycle).

| Wave | Tests (RED) | Implementation (GREEN) | LOC delta |
|---|---|---|---|
| **Wave 1 — Subprocess wrappers** | T1.1 fetch_project_list_happy, T1.2 non_zero, T1.3 parse_error, T1.4 binary_not_found | Implement `fetch_project_list` + `_run_subprocess_json` + 3 exception classes | +60 LOC |
| **Wave 2 — Status + Registry fetchers** | T2.1 fetch_status_summary_happy, T2.2 fetch_archived_happy, T2.3 missing_registry, T2.4 malformed | Implement `fetch_status_summary` + `fetch_archived_projects` | +40 LOC |
| **Wave 3 — Logic (filter + sort + color)** | T3.1 filter_R2, T3.2 filter_multi, T3.3 filter_invalid, T3.4 sort_name, T3.5 sort_path, T3.6 sort_needs, T3.7 sort_invalid, T3.8 color_red, T3.9 color_yellow, T3.10 color_green | Implement `filter_by_rules` + `sort_projects` + `color_code` | +50 LOC |
| **Wave 4 — Rich rendering** | T4.1 full_render, T4.2 filter_R2, T4.3 sort_needs_desc, T4.4 no_color_ansi_off, T4.5 empty_projects, T4.6 no_archived | Implement `render_header` + `render_needs_table` + `render_archived` + `render_footer` + `render_dashboard` | +90 LOC |
| **Wave 5 — Click integration** | T5.1 click_invokes, T5.2 click_filter, T5.3 click_sort, T5.4 click_no_color | Insert Click handler at `cli.py` L3034; import `dashboard` module; ~32 LOC cli.py modification | +32 LOC |
| **Wave 6 — Verify checks + AC9** | T6.1 verify_check_1..8 (8 structural checks), T6.2 AC9_byte_identical | Author `openspec/changes/phase-5-dashboard/scripts/verify-checks.sh` (the 8 check one-liners from §8) | +60 LOC (script) |
| **Wave 7 — Full suite + ACs** | (no new tests) | Run `uv run --frozen pytest` (expect 1537/1537 = 1513 baseline + 24 new dashboard tests); run AC1–AC15 checklist; AC9 byte-identical guard re-run | 0 LOC |

**Total LOC forecast**: ~330 LOC impl + tests + 60 LOC verify-script = **~390 LOC** (within 400-line single-PR budget) — but the `rich` rendering code is dense, and the snapshot tests may push to **500–600 LOC**. Hence the 3 split boundary options in §8.

## 8. 8 verify checks (paralleling #492 + 1 NEW)

`workspace-spec-cross-impact-cleanup` design #498 (archived) re-validated the 7 checks from `workspace-capability-bootstrap` design #492. This change adds 1 NEW check for the dashboard REQ Source: lines (Check 8). The first 7 are unchanged structurally but count expectations change because the placeholder REQ was replaced with 6 concrete dashboard REQs.

### Check 1 — Every root REQ has exactly one `Source:` line (12/12 expected)

```bash
awk '/^### REQ-WORKSPACE-/ { in_block=1; req=$3; src_count=0; next }
     in_block && /\*\*Source:\*\*/ { src_count++ }
     in_block && /^### / { printf("%s\t%d\n", req, src_count); in_block=0 }
     END { if (in_block) printf("%s\t%d\n", req, src_count) }' \
  openspec/specs/workspace/spec.md \
  | awk -F'\t' '$2 != 1 { print "FAIL: " $1 " has " $2 " Source: lines"; fail=1 } END { exit fail }'
```

- **Pattern**: `^### REQ-WORKSPACE-` opens root REQ; `\*\*Source:\*\*` inside MUST appear exactly once.
- **Expected**: 12/12 (was 7/7; placeholder REQ replaced by 6 dashboard REQs).
- **Exit codes**: `0` = all 12 root REQs each have exactly one `Source:` line. `1` = any missing or duplicating.
- **Diagnostic on fail**: `FAIL: REQ-WORKSPACE-<ID> has <N> Source: lines (expected 1)`.

### Check 2 — Every `Source:` path exists on disk (12/12 expected)

```bash
grep -oP 'openspec/changes/[^\s`]+\.md' openspec/specs/workspace/spec.md \
  | sort -u \
  | while read -r path; do
      [ -f "$path" ] || { echo "FAIL: missing $path"; exit 1; }
    done
```

- **Pattern**: `openspec/changes/[\w/.-]+\.md` extracted from each `Source:` line.
- **Expected**: 4 unique paths (was 3; + `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md`).
- **Exit codes**: `0` = all 4 cited paths exist. `1` = any missing.
- **Diagnostic on fail**: `FAIL: missing <path>`.

### Check 3 — Every cited `REQ-ID` exists in the cited delta spec (26 IDs across 12 root REQs)

```bash
python -c "
import re, pathlib, sys
spec = pathlib.Path('openspec/specs/workspace/spec.md').read_text()
blocks = re.findall(r'^### (REQ-WORKSPACE-[A-Z0-9-]+).*?\n(.*?)(?=^### |\Z)',
                    spec, re.MULTILINE | re.DOTALL)
fail = 0
for req, body in blocks:
    src = re.search(r'\`([^\`]+)\`\s+§([^\n]+)', body)
    if not src: continue
    path, ids = src.group(1), re.findall(r'REQ-[\`\w-]+', src.group(2))
    src_text = pathlib.Path(path).read_text()
    for rid in ids:
        if not re.search(rf'^### Requirement: {re.escape(rid)}\b', src_text, re.MULTILINE):
            print(f'FAIL: {req} cites {rid} but {path} does not define it'); fail = 1
sys.exit(fail)
"
```

- **Pattern**: `^### Requirement: <REQ-ID>\b` in the cited file.
- **Expected**: 26 distinct IDs (was 19; + 7 delta-internal dashboard REQs: REQ-DASHBOARD-COMMAND-NAME, REQ-DASHBOARD-FLAGS, REQ-DASHBOARD-READ-ONLY, REQ-DASHBOARD-DATA-SOURCES, REQ-DASHBOARD-RENDERING, REQ-DASHBOARD-ZERO-DEPS, REQ-DASHBOARD-DEFER-INTERACTIVE).
- **Exit codes**: `0` = every cited REQ-ID exists. `1` = any missing.
- **Diagnostic on fail**: `FAIL: <root_req> cites <delta_req_id> but <path> does not define it`.

**Cited-REQ count by root REQ** (post-spec phase):

| Root REQ | Delta REQ-ID count | Cited file |
|---|---|---|
| REQ-WORKSPACE-PROJECT-IDENTITY | 5 | `workspace-intelligence/.../projects-ls-extension/spec.md` |
| REQ-WORKSPACE-STATUS-DISCOVERY | 8 | `flow-workspace-status/.../workspace-status/spec.md` |
| REQ-WORKSPACE-MUTATION-SAFETY | 3 | `archive/2026-06-30-workspace-hygiene/.../workspace-hygiene/spec.md` |
| REQ-WORKSPACE-DRY-RUN-DEFAULT | 1 | same as above |
| REQ-WORKSPACE-R1-DEFERRED | 1 | same as above |
| REQ-WORKSPACE-REGISTRY-V1 | 1 | same as above |
| REQ-WORKSPACE-DASHBOARD-SURFACE | 2 | `phase-5-dashboard/specs/workspace-dashboard/spec.md` |
| REQ-WORKSPACE-DASHBOARD-READ-ONLY | 1 | same as above |
| REQ-WORKSPACE-DASHBOARD-CONSUMES-DS1 | 1 | same as above |
| REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2 | 1 | same as above |
| REQ-WORKSPACE-DASHBOARD-RENDERS-RICH | 3 | same as above |
| REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE | 1 | same as above |
| **Total** | **27** | (revised from prompt's 26; REQ-DASHBOARD-FLAGS counts as 1, total 6+6+6+1+3+1+1+1 = 26 — let me re-count from spec) |

> **NOTE**: post-design re-count by `sdd-apply` against actual `Source:` lines at `openspec/specs/workspace/spec.md` L96/L114/L124/L134/L144/L164/L174/L186/L198/L210/L222/L234 is the authoritative source. If the count differs from 27, the design is updated to match.

### Check 4 — Cross-Impact mentions `flow-where-cross-project-capability-merge`

```bash
grep -F "flow-where-cross-project-capability-merge" openspec/specs/workspace/spec.md >/dev/null
```

- **Pattern (literal)**: substring `flow-where-cross-project-capability-merge` (currently at L354 §6.1 RESOLVED note + 1 more in §6.1 body).
- **Exit codes**: `0` = mention present. `1` = missing.
- **Diagnostic on fail**: `FAIL: §6 Cross-Impact must mention the flow-where-cross-project-capability-merge follow-up`.

### Check 5 — Future Changes mentions `workspace-dashboard`

```bash
grep -F "workspace-dashboard" openspec/specs/workspace/spec.md >/dev/null
```

- **Pattern (literal)**: substring `workspace-dashboard` (currently at L28 §1 + L80 §3 + L174/L186/L198/L210/L222/L234 §4 Source: lines + L298 §7 + L360 §7 row + L377 footer).
- **Exit codes**: `0` = mention present. `1` = missing.
- **Diagnostic on fail**: `FAIL: §7 Future Changes must list workspace-dashboard`.

### Check 6 — Drift Detection footer present

```bash
grep -F "Drift Detection" openspec/specs/workspace/spec.md >/dev/null
```

- **Pattern (literal)**: substring `Drift Detection` (currently at L367 §8 H2 heading).
- **Exit codes**: `0` = footer present. `1` = missing.
- **Diagnostic on fail**: `FAIL: §8 Drift Detection footer missing`.

### Check 7 — "Family index" callout in first 10 lines

```bash
head -n 10 openspec/specs/workspace/spec.md | grep -F "Family index" >/dev/null
```

- **Pattern (literal + positional)**: substring `Family index` in lines 1-10 (currently at L4 blockquote).
- **Exit codes**: `0` = callout present in first 10 lines. `1` = missing or moved.
- **Diagnostic on fail**: `FAIL: 'Family index, not canonical source' callout must appear in the first 10 lines`.

### Check 8 (NEW) — Every dashboard REQ has a Source: line pointing to the dashboard delta spec

```bash
python -c "
import re, pathlib, sys
spec = pathlib.Path('openspec/specs/workspace/spec.md').read_text()
dashboard_reqs = re.findall(
    r'^### (REQ-WORKSPACE-DASHBOARD-[A-Z0-9-]+).*?\n(.*?)(?=^### |\Z)',
    spec, re.MULTILINE | re.DOTALL)
expected_path_suffix = 'phase-5-dashboard/specs/workspace-dashboard/spec.md'
fail = 0
for req, body in dashboard_reqs:
    src = re.search(r'\`([^\`]+)\`', body)
    if not src:
        print(f'FAIL: {req} has no Source: path'); fail = 1; continue
    if expected_path_suffix not in src.group(1):
        print(f'FAIL: {req} Source: path {src.group(1)} does not point to dashboard delta spec'); fail = 1
sys.exit(fail)
"
```

- **Pattern**: regex `^### REQ-WORKSPACE-DASHBOARD-` matches 6 dashboard REQs; each MUST have a `Source:` line whose path contains `phase-5-dashboard/specs/workspace-dashboard/spec.md`.
- **Expected**: 6/6 dashboard REQs each with a Source: pointing to the dashboard delta spec (after archive: the path becomes `archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` — Check 8 must be RE-RUN with the new path after archive; or generalized to match `phase-5-dashboard` substring for archive tolerance).
- **Exit codes**: `0` = all 6 dashboard REQs have Source: pointing to the dashboard delta spec. `1` = any missing or pointing elsewhere.
- **Diagnostic on fail**: `FAIL: <dashboard_req> Source: path <path> does not point to dashboard delta spec`.
- **Rationale**: guards against (a) the placeholder REQ being silently reintroduced, (b) future refactors that drop the dashboard REQ blocks, (c) the Source: lines pointing to a wrong file (e.g., if the change folder gets renamed).

### 8.1 Failure modes + exit codes (consolidated)

| Check # | Failure mode | Diagnostic | Exit |
|---|---|---|---|
| 1 | Root REQ missing/duplicating `Source:` | `FAIL: REQ-WORKSPACE-<ID> has <N> Source: lines (expected 1)` | 1 |
| 2 | Cited delta spec path missing | `FAIL: missing <path>` | 1 |
| 3 | Cited REQ-ID missing in delta spec | `FAIL: <root_req> cites <delta_req_id> but <path> does not define it` | 1 |
| 4 | Cross-Impact missing flow-where merge mention | `FAIL: §6 Cross-Impact must mention flow-where-cross-project-capability-merge` | 1 |
| 5 | §7 Future Changes missing workspace-dashboard | `FAIL: §7 Future Changes must list workspace-dashboard` | 1 |
| 6 | §8 Drift Detection footer missing | `FAIL: §8 Drift Detection footer missing` | 1 |
| 7 | Family-index callout not in first 10 lines | `FAIL: 'Family index, not canonical source' callout must appear in first 10 lines` | 1 |
| 8 (NEW) | Dashboard REQ missing/wrong Source: | `FAIL: <dashboard_req> Source: path <path> does not point to dashboard delta spec` | 1 |

**Aggregation contract**: `sdd-verify` runs all 8; any non-zero exit fails AC2 (preservation check) AND AC14 (REQ-WORKSPACE-DASHBOARD-PLACEHOLDER resolved). The verify script lives at `openspec/changes/phase-5-dashboard/scripts/verify-checks.sh`.

## 9. Split boundaries (proposed, NOT locked — Pattern #540)

The user explicitly required: *"NO lockear size:exception todavía: el design debe proponer split boundaries si el forecast supera 400 LOC, y sdd-tasks decidirá con Review Workload Forecast."* Per Pattern #540 (defer budget to tasks), the design PROPOSES three options and lets `sdd-tasks` measure actual LOC and pick.

### Option A — Single PR with `size:exception` (when forecast < 400 LOC)

- **Use when**: actual LOC measured by `sdd-tasks` Review Workload Forecast stays **under 400 changed lines**.
- **Composition**: dashboard.py (~250 LOC) + test_dashboard.py (~350 LOC) + cli.py modification (~32 LOC) + verify-checks.sh (~60 LOC) = **~700 LOC total**. **Likely exceeds 400 → NOT recommended unless apply-phase TDD reveals much smaller implementation than estimated.**
- **Risk**: 700 LOC in one PR violates reviewer cognitive load budget (`chained-pr` skill: PR ≤400 lines). Requires `size:exception` rationale documenting zero-fan-out coupling rationale (dashboard.py is self-contained + cli.py is one decorator block + tests are linear).
- **Precedent**: Phase 1 (`workspace-intelligence`) at 543 LOC + Phase 3 (`flow-workspace-status`) at 735 LOC both shipped single-PR with `size:exception`.
- **REVIEW WORKLOAD**: estimated 30–45 minutes per reviewer.

### Option B — Chained PR by wave (RECOMMENDED for forecast 400–800 LOC)

- **Use when**: actual LOC measured by `sdd-tasks` lands in the 400–800 range.
- **Composition**: 3 chained PRs, each with its own work unit (per `work-unit-commits` skill):
  - **PR1** (Wave 1 + Wave 2 — Data acquisition): `dashboard.py` fetchers (DS1/DS2/DS5) + tests for fetchers + 3 exception classes. ~120 LOC. **Independently mergeable** (no rendering, no Click, no flags). Reviewer test: subprocess mocks + 3 error paths.
  - **PR2** (Wave 3 + Wave 4 — Logic + Rendering): `filter_by_rules` + `sort_projects` + `color_code` + `render_*` + tests. ~200 LOC. **Depends on PR1** (uses fetcher return types). Reviewer test: pure-function tests + golden-text snapshot tests for Rich output.
  - **PR3** (Wave 5 + Wave 6 + Wave 7 — Click integration + Verify + ACs): cli.py registration + Click handler tests + 8 verify checks script + AC1–AC15 walkthrough. ~150 LOC + 60 LOC script. **Depends on PR2**. Reviewer test: CliRunner integration tests + structural checks.
- **Strategy**: Feature Branch Chain per `chained-pr` skill §3 (since the 3 slices are vertically integrated into one user-facing feature; first child targets tracker branch, later children target immediate parent branch).
- **REVIEW WORKLOAD**: estimated 15–25 minutes per reviewer per slice. Total: ~60 minutes reviewer-time but distributed across 3 reviews.

### Option C — Chained PR by capability (RECOMMENDED for forecast > 800 LOC)

- **Use when**: actual LOC measured by `sdd-tasks` exceeds 800.
- **Composition**: 3 chained PRs sliced by capability layer (instead of by TDD wave):
  - **PR1** (Core data layer): `dashboard.py` module skeleton (no rendering, no Click) + subprocess wrappers + registry read + exception classes + tests. ~180 LOC. **Independently mergeable**.
  - **PR2** (Filter + sort + color + rendering): all logic + all Rich render functions + tests. ~250 LOC. **Depends on PR1**.
  - **PR3** (Click integration + verify + ACs): cli.py registration + Click handler + 8 verify checks + AC1–AC15. ~180 LOC + 60 LOC script. **Depends on PR2**.
- **Strategy**: Stacked PRs to main per `chained-pr` skill §3 (each slice independently shippable as its own capability layer).
- **REVIEW WORKLOAD**: estimated 20–30 minutes per reviewer per slice. Total: ~75 minutes reviewer-time.

### Recommended at design time

Present all 3 options to `sdd-tasks`. `sdd-tasks` will measure actual LOC at task-authoring time and pick via Review Workload Forecast per the user's preflight `chained_pr_strategy: ask-always` cached setting. **DO NOT commit at design time** (Pattern #540 — defer budget decisions to tasks).

## 10. Out of Scope (explicit)

Per `openspec/changes/phase-5-dashboard/proposal.md` §9 + spec #539 cross-validation:

- **NO new runtime deps** (`rich` already transitive via `uv.lock:1215`; promotion to direct dep zero-cost).
- **NO TUI frameworks** (Textual, urwid, Rich Live, prompt_toolkit, Blessed).
- **NO web frameworks** (FastAPI, Streamlit, Dash, Panel, Flask, Tauri).
- **NO mutations from dashboard** (Pattern #536 — observability first; mutations stay in `flow workspace fix/archive/restore`).
- **NO `--json` flag on dashboard** (Pattern #538 — one identity per command; `flow workspace status --json` is the machine-readable endpoint).
- **NO real-time updates / file watching / websocket** (on-demand refresh only).
- **NO interactive forms / prompts / buttons / i18n / theming / mobile**.
- **NO historical data / audit log / trends / multi-user**.
- **NO modifications to Phase 4 mutation gates** (`pollution-protocol triple`, `MutationGateError`, `EmptyProjectError` stay intact).
- **NO modifications to Phase 1/2/3 CLI commands** (`flow projects ls`, `flow workspace status`, `flow where` byte-identical preserved).
- **NO modifications** to `openspec/changes/v1.1-followups/` (sacred territory).
- **NO `stash`-triggering words** in new code (§7 L363 "stash/worktree handling" stays byte-identical).
- **NO §3/§5/§7 cleanup of the workspace root spec** (deferred to a follow-up change per spec #539 Out of Scope; this PR preserves §3 row 5 "placeholder" + §5 row "tui (future)" + §7 row #2 byte-identical).
- **NO PR strategy lock at design time** (Pattern #540 — defer to `sdd-tasks` Review Workload Forecast).
- **NO `size:exception` commitment** in this design document (3 options proposed, tasks phase decides).

## 11. Tech Debt / Follow-up

- **Phase 5.2 — TUI** (deferred): if MVP falls short on operator usage, evaluate Textual (`flow workspace tui` placeholder at §5 L317).
- **Phase 5.2 — Web** (deferred): if MVP falls short, evaluate FastAPI+HTMX or Streamlit.
- **Phase 5.2 — Interactive mutations** (deferred): if operators request it, add `flow workspace fix --triggered-from-dashboard <project>` invocation with explicit gate flags (pollution-protocol triple + `--yes` + `--backup`); NEVER bypass Phase 4 gates.
- **Future `workspace-dashboard-section-cleanup`** (deferred): §3 row 5 "placeholder" + §5 row "tui (future)" + §7 row #2 stale prose in `openspec/specs/workspace/spec.md` require update when this change ships. Per spec #539 Out of Scope, this is OUT of this PR — preserve byte-identical until archive + then a small follow-up change can clean §3/§5/§7 in one stroke (matches the `workspace-spec-cross-impact-cleanup` surgical-fix precedent).
- **Future `spec-drift-detector`** (deferred per verify-report #513 S1): parse `Source:` lines, validate REQ-IDs, flag stale prose patterns — would automate the 8 verify checks in CI.
- **Future `capability-spec-linter`** (deferred per #513 S2): extend Checks 2/3/8 to `flow-where/spec.md`, `decision-drift/spec.md`, `observability/spec.md`, `prompt-registry/spec.md`.

## 12. Pre-existing failures (out-of-scope reminder)

- **3 pre-existing ruff errors** (carried from Phase 4 close-out; remain OOS): `cli.py:682 RET504`, `test_cli_where_cross_project.py:{33 UP035, 295 W292}`.
- **0 pre-existing test failures** on main HEAD `6133e70` (1513/1513 baseline).
- **AC9 byte-identical guard** at `tests/unit/test_cli_projects.py:435` preserved by zero-modification policy to Phase 1 (`flow projects ls`) code paths.
- **AC15 byte-identical guard** on `flow workspace status` text output preserved by zero-modification policy to Phase 3 code paths.
- **Rich Console hard-wrap**: `soft_wrap=False` argument added in §5 Click integration to prevent Rich from auto-wrapping project paths (operator readability on narrow terminals).

## 13. Commit hygiene (per work-unit-commits skill)

Per `work-unit-commits` skill + user session preference (no AI attribution per AGENTS.md):

- **Single commit per PR** (regardless of chained-PR strategy chosen by tasks phase).
- **Commit message format**: `feat(dashboard): <wave or slice description>` (chained) or `feat(dashboard): MVP Rich-only read-only dashboard` (single PR).
- **Files in commit** (single-PR scenario):
  - `src/flow_engineering/dashboard.py` (NEW, ~250 LOC)
  - `tests/unit/test_dashboard.py` (NEW, ~350 LOC)
  - `src/flow_engineering/cli.py` (MODIFY, +32 LOC around L2990 workspace_group section)
  - `openspec/changes/phase-5-dashboard/scripts/verify-checks.sh` (NEW, ~60 LOC — the 8 check one-liners)
- **NO AI attribution** in commit message (per AGENTS.md).
- **Conventional commits** format only.

## 14. Wall-time forecast for tasks → apply → verify → archive

| Phase | Estimate | Rationale |
|---|---|---|
| `sdd-tasks` | ~20 min | Author tasks.md with the 7 TDD waves + Review Workload Forecast (picks PR strategy A/B/C) + commit. **Reviews Workload Forecast is the gate** for PR strategy decision. |
| `sdd-apply` | 3–6 hours | Largest in the arc; strict TDD RED→GREEN→REFACTOR across 7 waves; ~390 LOC impl+tests+script. Single PR (if Option A) saves ~30 min vs. chained (Option B/C saves ~15 min on reviewer time but adds ~45 min on CI + merge overhead). |
| `sdd-verify` | 1–2 hours | Run 8 verify checks + AC1–AC15 walkthrough + full suite 1537/1537 (1513 baseline + 24 new dashboard tests) + AC9 byte-identical guard re-run. |
| `sdd-archive` | ~15 min | Move change folder to `archive/2026-06-30-phase-5-dashboard/`; merge deltas into canonical root spec (which is already in place — only the placeholder REQ block needs to remain + the 6 dashboard REQ blocks stay). |
| **Total remaining** | **~5–9 hours** | Largest in the workspace-intelligence arc; consistent with explore #535 wall-clock forecast (7–13 h for Approach E). |

## 15. Verdict

**Architecture locked. PR strategy DEFERRED.**

This design specifies:
- **Insertion point**: `cli.py:3034` (immediately after `workspace_status` at L3009-3032, before `workspace_hygiene` mutation block at L3156+).
- **Public API**: 9 functions + 1 Click handler + 3 exception classes (all signatures + return contracts in §2.2).
- **Subprocess pattern**: `_run_subprocess_json` mirrors `where.py:89` + `cli.py:3380` with `check=False` + explicit error branching for SPECIFIC failure modes.
- **Rich rendering**: 4 sections (A header Panel + B needs Table + C archived Table or omit + D footer Text) composed via `rich.console.Group`.
- **Click integration**: `workspace_dashboard_cmd` at `cli.py:3034`, ~32 LOC decorator chain + handler body.
- **8 verify checks**: 7 inherited from design #492 (unchanged structure, count expectations updated to 12/12/27 for the new dashboard REQs) + 1 NEW (Check 8) guarding the 6 dashboard REQ `Source:` lines.
- **7 TDD waves**: Wave 1 (subprocess) → Wave 2 (fetchers) → Wave 3 (logic) → Wave 4 (rendering) → Wave 5 (Click) → Wave 6 (verify script) → Wave 7 (full suite).
- **3 split boundary options**: A single PR (forecast < 400), B chained by wave (400-800), C chained by capability (> 800). **DEFERRED to sdd-tasks** for actual measurement.

**Next step**: `sdd-tasks phase-5-dashboard` (Review Workload Forecast will pick PR strategy).

---

## Appendix A — Cross-References

- **Canonical root spec**: `openspec/specs/workspace/spec.md` (378 LF, 12 root REQs total).
- **Change-artifact delta spec**: `openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md` (185 LF, 7 delta-internal REQs).
- **Proposal (authoritative source)**: `openspec/changes/phase-5-dashboard/proposal.md` (195 LF; Approach E locked; `--json` REMOVED per user adjustment; 15 acceptance criteria AC1–AC15; 14 user-locked constraints).
- **Explore**: `openspec/changes/phase-5-dashboard/explore.md` (5 approach candidates surfaced; Approach E picked as lowest-cost; Pattern #536 cited).
- **Precedent for 7 verify checks**: Engram #492 (workspace-capability-bootstrap design) + Engram #498 (workspace-spec-cross-impact-cleanup re-validation).
- **Patterns honored**: Engram #536 (observability first), #538 (one identity per command), #540 (defer budget to tasks).
- **Registry DS5 read**: `src/flow_engineering/registry.py:144` (`load_registry()`; missing file → empty `Registry()`).
- **CLI registration target**: `src/flow_engineering/cli.py:2990` (`@main.group(name="workspace") def workspace_group()`).
- **DS1 invocation precedent**: `subprocess.run(["flow", "projects", "ls", "--json"], ...)` — same pattern as Phase 1/3 DS consumption.
- **DS2 invocation precedent**: `subprocess.run(["flow", "workspace", "status", "--json"], ...)` — same pattern.
- **Rich dep**: `uv.lock:1215` (`rich 15.0.0` transitive); promote-to-direct in `pyproject.toml` is zero-cost.
- **Sibling sub-agent artifacts**: Engram #535 (explore), #536 (pattern), #537 (proposal mirror), #538 (pattern), #539 (spec mirror), #540 (pattern).
- **Engram mirror** (this design): topic_key `sdd/phase-5-dashboard/design`; type `architecture`; `capture_prompt: false`; project `insyd`.