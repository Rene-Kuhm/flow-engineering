# Design: workspace-dashboard-usability-pass

> **Phase**: design (4/8 of SDD cycle)
> **Change**: `workspace-dashboard-usability-pass`
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Strict TDD**: ON (RED -> GREEN -> REFACTOR per task in `sdd-tasks`/`sdd-apply`)
> **Inputs**: spec (16 ACs + 24 BDD scenarios; parallel sdd-spec output) <- proposal <- explore
> **Output**: this `design.md` -- locks encoding strategy, scan helper, Section E render, file map, test strategy, sub-batch plan, and tentative PR split
> **Design philosophy**: "limpiar lo prometido, nada mas" (Pattern #582) applied to a 3-point cosmetic pass; resolve every ambiguity here so `sdd-apply` is mechanical

---

## Header

| Field | Value |
|-------|-------|
| Change | `workspace-dashboard-usability-pass` |
| Phase | design (4th of 8) |
| Strict TDD | ON |
| Forecast | ~155 raw / ~930 with conservative strict-TDD times-6 multiplier / ~400-700 realistic |
| Files modified | 5 -- `src/flow_engineering/cli.py` + `src/flow_engineering/dashboard.py` + `tests/unit/test_dashboard.py` + `tests/unit/test_cli_dashboard.py` + `tests/unit/test_cli_workspace_status.py` + `tests/unit/test_cli_projects.py` (5 src-tests = 5 modified files) |
| Audit-only files | 2 -- `src/flow_engineering/project_detector.py` + `src/flow_engineering/workspace_hygiene.py` (read-only review, expected NO change) |
| Net LOC delta | ~55 src + ~110 tests = ~155 raw |
| LOC budget status | Realistic > 400 -- `sdd-tasks` will trigger chained PR recommendation |
| New runtime deps | 0 (rich stays transitive; promotion to direct dep is zero-cost) |
| New flags | 0 (forbidden by `REQ-WORKSPACE-DASHBOARD-FLAGS` + read-only constraint) |
| New CLI commands | 0 |
| Mutations | 0 (read-only surface per `REQ-WORKSPACE-DASHBOARD-READ-ONLY`) |
| PR strategy | **NOT COMMITTED, sdd-tasks decides** -- tentative split documented in section 13 |
| Wall-time forecast | ~10 min design (this doc) + ~25 min tasks/apply/verify/archive |
| ACs satisfied | 16 ACs from spec (AC1-AC16, all locked) |

---

## 1. Architecture Overview

Three small cosmetic + usability fixes to the **already-shipped** read-only Rich dashboard (`flow workspace dashboard`). All three live in the existing Phase 5 surface -- no new commands, no new flags, no mutations. The dashboard stays read-only per `REQ-WORKSPACE-DASHBOARD-READ-ONLY`.

**Locked decisions** (one-line each; full rationale in sections 3-5):

1. **Encoding** -- `sys.stdout.reconfigure(encoding="utf-8")` wrapped in `try/except OSError` (Pattern #551) + `Console(width=<int>, soft_wrap=True)` + per-column `OverflowMethod.fold`. ASCII `...` only; the Unicode U+2026 ellipsis is forbidden everywhere in dashboard output.
2. **Dot-prefix filter** -- `_iter_project_subdirs(root)` shared helper, applied at `workspace_status` L3017 + `projects_ls` L3628. View-only filter; no deletion, no mutation.
3. **R1 detail** -- capture `git status --porcelain` stdout as `dirty_files: list[str]`; thread through `_summarize_workspace_status` -> DS2 envelope `needs_attention` entry -> `render_r1_detail` Section E (between B and C); cap 20 files/project + ASCII `...` + footer hint.

**Composition shape (post-change)**:

```
+---------------------------------------------------------------+
| SECTION A -- Header panel (totals + per-rule breakdown)         |
+---------------------------------------------------------------+
| SECTION B -- Needs-attention table (project x R1..R5)           |
+---------------------------------------------------------------+
| SECTION E -- R1 dirty files (CONDITIONAL, NEW)                  |   <- between B and C
|  Per-R1 project: name | up to 20 dirty files | "..." truncate   |
+---------------------------------------------------------------+
| SECTION C -- Archived projects list (CONDITIONAL)               |
+---------------------------------------------------------------+
| SECTION D -- Footer tips                                        |
+---------------------------------------------------------------+
```

Section E appears ONLY when at least one project has R1 triggered. Otherwise the composer omits it (mirrors how Section C is omitted when empty).

**Data flow** (R1 detail):

```
_git("status", "--porcelain", cwd=project_dir)
        |
        v
_detect_project_markers  (cli.py:3545-3550)  -- capture stdout.splitlines() as dirty_files
        |
        v
_sorted project dicts  (name-keyed, dirty + dirty_files)
        |
        v
_summarize_workspace_status  (cli.py:2892-2919)  -- copy dirty_files onto needs_attention entry when R1 reason added
        |
        v
DS2 envelope  (version: "1" unchanged; additive field "dirty_files" per needs_attention item)
        |
        v
fetch_status_summary  (dashboard.py:152-159, subprocess)
        |
        v
workspace_dashboard_cmd  (cli.py:3040-3090)  -- needs_attention carries dirty_files
        |
        v
render_r1_detail  (NEW, dashboard.py)  -- returns None when no R1 triggered, else Table
        |
        v
render_dashboard  (L606-645)  -- appends Section E between B and C
```

---

## 2. Shared Infrastructure (cross-point, locked)

The 3 points share infrastructure that benefits all sections and surfaces.

| Concern | Shared across | Mechanism | Where it lives |
|---------|---------------|-----------|----------------|
| **Console encoding + width** | Point 1; benefits Sections A/B/C/D | One `Console(...)` instance per dashboard invocation; `reconfigure(encoding="utf-8")` + `width=` + `soft_wrap=True` | `cli.py:3089` (replaces existing `Console(...)`) |
| **`_iter_project_subdirs(root)`** | Point 2; benefits `workspace_status` AND `projects_ls` AND `workspace_dashboard_cmd` (via subprocess); corrects the Section A totals (which are read via DS2 -> `_summarize_workspace_status` -> workspaces status envelope) | Single helper, 2 concrete call sites (Article IV justifies extraction) | New helper near `_resolve_projects_root` at `cli.py:84` |
| **20-file cap mechanism (R1 detail)** | Point 3 now; reusable for future sections | Function-level `_truncate_dirty_files(files: list[str], cap: int = 20) -> list[str]` helper inside `dashboard.py`; ASCII `...` truncation + footer hint reused | `dashboard.py` (Section E composer) |
| **Per-column width policy** | Point 1; benefits Sections B/E (and C retroactively) | Same `Table.add_column(..., min_width=X, max_width=Y, overflow=OverflowMethod.fold)` pattern reused | `dashboard.py:475-481` (Section B) + new Section E + Section C update |

**Cross-point benefit**: encoding fix benefits **all** sections A/B/C/D (not just B/E); the scan helper fixes **both** `workspace_status` text/JSON AND `flow projects ls` text/JSON AND the dashboard's project totals (one fix, three surfaces). The 20-file cap mechanism is a reusable policy primitive for any future per-list-with-cap section.

---

## 3. Architecture Decisions

### Decision 1 -- Console encoding reconfigure

| Field | Value |
|-------|-------|
| **Choice** | `try: sys.stdout.reconfigure(encoding="utf-8") except OSError: pass` at `cli.py:3089`, immediately before the `Console(...)` instantiation |
| **Alternatives considered** | (a) `locale.getpreferredencoding(False)` only -- doesn't fix cp1252 terminals, (b) `Console(file=sys.stdout)` without reconfigure -- same problem, (c) set PYTHONIOENCODING env var -- process-global side effect, (d) write-through-buffer replacement -- breaks subprocess integration |
| **Rationale** | `reconfigure` is the stdlib-supported escape hatch (Python 3.7+) for the cp1252 default on Windows. The `try/except OSError` is Pattern #551 (graceful OSError fallback) -- on non-TTY / redirected pipes `reconfigure` raises OSError; the dashboard then uses Rich's default file encoding. On legacy Windows console it MAY still fail (Windows 7 / non-UTF-8 code page); the fallback path renders ASCII-safe (the dashboard is mostly ASCII; only project names can be non-ASCII, and the dashboard shows them via Rich which accepts any bytes). |
| **Path taken** (locked) | The reconfigure runs **unconditionally** in the try/except -- even when stdout is cp1252 + has actual non-ASCII project names -- so the `_truncate_path` ASCII `...` tail (no non-ASCII `n-tilde`, no Unicode U+2026) stays safe regardless. |

### Decision 2 -- Console width + soft-wrap

| Field | Value |
|-------|-------|
| **Choice** | `Console(width=<int>, soft_wrap=True, no_color=no_color)` at `cli.py:3089`. `<int>` resolved at call-site from `(c.size.width or 120)` where `c` is a fresh `Console()` for size-introspection (Rich's `Console().size.width` returns the terminal width or 80 by default). |
| **Alternatives considered** | (a) `Console(width=None)` (auto-detect every render) -- non-deterministic snapshot output, (b) hardcoded `width=120` always -- broken on narrow terminals, (c) `Console(soft_wrap=False)` (default, current) -- produces Unicode U+2026 truncation |
| **Rationale** | Best-effort auto-detect first, explicit fallback second. Mirrors the existing snapshot test pattern at `test_dashboard.py:87` (`Console(width=120, force_terminal=False, no_color=True, record=True, file=io.StringIO())`) for deterministic captures. `soft_wrap=True` is the Rich knob that allows long content to wrap inside cells (rather than truncated with ellipsis at the cell boundary). The combination of width + soft_wrap replaces the existing `soft_wrap=False` which produced the Unicode U+2026 (a.k.a. single-char ellipsis) bug. |

### Decision 3 -- Per-column `OverflowMethod.fold`

| Field | Value |
|-------|-------|
| **Choice** | `OverflowMethod.fold` for `name` (Section B), `path` (Section B), and the new Section E file-column + dirty-file-name column. `OverflowMethod.crop` (no ellipsis) as defense-in-depth fallback if `fold` produces lines longer than expected. |
| **Alternatives considered** | (a) `OverflowMethod.ellipsis` (Rich default, current behavior) -- produces the Unicode single-char ellipsis (U+2026) which becomes the replacement char (U+FFFD) on cp1252, (b) `OverflowMethod.crop` only -- loses operator hint of truncation, (c) `OverflowMethod.ignore` -- leaks content past borders |
| **Rationale** | `fold` wraps long content onto multiple lines, keeping ASCII-safe characters throughout (Rich `fold` never inserts the Unicode U+2026 char -- it inserts literal `"\n"` to break the cell). `crop` is the defense-in-depth: if a cell is SO long that even wrapping feels wrong, `crop` shows the prefix without ellipsis. **NEVER** `ellipsis` -- that's the Unicode U+2026 source we're eliminating. |
| **Per-column widths** (locked) | Section B `name` column: `min_width=12, max_width=30`; `path` column: `min_width=30, max_width=60`; rule columns (R1..R5): `min_width=3, max_width=5`; `total` column: `min_width=3, max_width=4`. Section E `name` column: `min_width=12, max_width=30`; `files` column: `min_width=20, max_width=80` (wraps the file list). Defaults match `Console(width=120)` split: name 30 + path 60 + 5 x 5 + total 4 = ~119 chars. |
| **API call** | Per-column `OverflowMethod.fold` is set via `table.add_column("name", overflow=OverflowMethod.fold, min_width=12, max_width=30)`. Rich's `Column` constructor accepts these kwargs directly. |

### Decision 4 -- `_iter_project_subdirs(root)` shared helper extraction

| Field | Value |
|-------|-------|
| **Choice** | Extract a helper near `_resolve_projects_root` at `cli.py:84-93` (right after the existing helper, matching the `_resolve_*` private-helper precedent): |

```python
def _iter_project_subdirs(root: Path) -> list[Path]:
    """Return sorted immediate subdirectories of ``root`` excluding dot-prefix entries.

    Dot-prefix entries (``.atl``, ``.opencode``, ``.venv``, ``.mypy_cache``,
    ``.pytest_cache``, ``.ruff_cache``, ``.specify``, ``.github``, etc.)
    are tooling/config -- never user projects. They are skipped at scan
    time so the workspace stays focused on real code (view-only filter;
    no directory is modified, archived, or deleted).
    """
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
```

| **Alternative A** | Filter at iteration sites (L3017 + L3628) inline |
| **Alternative B** | Filter inside `_detect_project_markers` |
| **Alternative C** | Filter at render time inside `dashboard.py` |
| **Alternative D** | Opt-in `--no-hidden` flag |

**Article IV justification** (cited per explore section 3.2 + proposal Approach Point 2):

| Concrete call site | Why it needs the helper |
|--------------------|--------------------------|
| `cli.py:3017` (`workspace_status`) | Existing `[p for p in root.iterdir() if p.is_dir()]` line; replace with helper. Benefits `flow workspace status` text + `--json`. |
| `cli.py:3628` (`projects_ls`) | Identical pattern; replace with helper. Benefits `flow projects ls` text + `--json`. |

**2 concrete call sites + 1 future** = Article IV threshold (`_resolve_projects_root` is already extracted for the same reason). Extraction is justified.

| **Rationale** | (1) DRY at 2 sites, (2) single hook for RED tests, (3) rename-resistant (future `_iter_*` extensions reuse the prefix), (4) `where.py:461` audit-out-of-scope per locked scope (see section 9), (5) view-only filter -- directories are NEVER deleted, archived, or modified (per `REQ-WORKSPACE-DASHBOARD-READ-ONLY`); if a user actually has a real dot-prefix project they care about, the filter is a *view* failure only -- the project still exists. |
| **Reject A** | Inline-duplicated; not DRY. |
| **Reject B** | `_detect_project_markers` still gets called for hidden dirs; wasted subprocess cost (`git rev-parse`, `git config`, `git status`) per hidden tooling dir. |
| **Reject C** | Hides noise from dashboard only -- `flow projects ls --json` + `flow workspace status --json` would still emit dot-prefix projects; downstream consumers (Engram, Graphify) would filter again; `flow projects ls` text would still show them; totals (Section A) would still count them. **Doesn't fix the actual problem; just hides it.** |
| **Reject D** | New flag forbidden (Pattern #538 + read-only + locked scope). Dot-prefix filter is **silent** -- operators never need to opt in because the noise is universally unwanted. |

### Decision 5 -- Section E render placement + conditional

| Field | Value |
|-------|-------|
| **Choice** | New `render_r1_detail(needs_attention: list[dict[str, Any]]) -> Table | None`. Returns `None` when no project has `dirty_files` non-empty. `render_dashboard` at `dashboard.py:606-645` appends Section E between Section B and Section C when the renderable is non-None. |
| **Rationale** | Mirrors Section C's conditional shape (`None` -> omit). Keeps the existing 4-section contract intact for callers that consume the `Group` directly. New section is **conditional** -- dashboard stays minimal when no R1 triggered (the common case for most workspaces). Maps directly to AC9 + AC10 in the parallel spec. |
| **Cap mechanism** | `_truncate_dirty_files(files: list[str], cap: int = 20) -> list[str]` -- if `len(files) > cap`, slice to `cap - 1` and append ASCII `"..."` (3 chars, NOT Unicode U+2026) at the end of the last file slot. The files list passed to Section E IS already truncated; the **last cell** in the table shows `"..."` to signal truncation. Implements AC11 + AC12. |
| **Footer hint** | `render_footer` Text at `dashboard.py:582-600` -- append a new line: `"[dim]Tip:[/dim] When [red]R1[/red] is triggered, see Section E for dirty files (capped at 20 per project); run [bold]git status[/bold] in a project for the full list."`. Mirrors the `flow workspace status --json` + `flow workspace fix <project> --yes --backup` tip pattern. |
| **Reject** inline R1 cell content | Per explore section 3.3 -- the per-row color coding breaks; cells become multi-line, breaking the table grid. Low discoverability. |
| **Reject** new "R1 files" column on Section B | Bloat -- 1 extra column on every dashboard run; only R1 projects have content; 99% of cells are empty. |

### Decision 6 -- DS2 envelope `dirty_files` additive field

| Field | Value |
|-------|-------|
| **Choice** | When `R1: uncommitted work` is added to `reasons` in `_summarize_workspace_status` (`cli.py:2892-2919`), also copy `project["dirty_files"]` onto the `needs_attention` entry. DS2 envelope's `"version": "1"` key is UNCHANGED (additive field only; consumers ignore unknown keys). DS1 envelope (`flow projects ls --json`) ALSO gains `dirty_files` for downstream consumers that prefer DS1 over DS2 (e.g., Graphify). |
| **Backward compat** | Pin to `"version": "1"` envelope -- additive field is non-breaking per the v1 schema's "consumers ignore unknown keys" contract (documented at `workspace/spec.md:112` and `workspace/spec.md:196`). Pin schema does NOT bump to `"version": "2"` for additive fields; bumps are reserved for breaking changes (e.g., field rename, field removal). |
| **DEFAULT for clean project** | `dirty_files: []` (empty list) when `dirty` is False OR when `has_git` is False OR when `git status` failed. Consumers iterate with `if entry.get("dirty_files"):` semantics -- empty list is falsy. |
| **Why capture the stdout** | `_git("status", "--porcelain", cwd=...)` is ALREADY invoked at `cli.py:3545-3550` to compute `dirty`. The stdout was DISCARDED after `bool(cp.stdout.strip())`. Zero new subprocess cost; one extra `.splitlines()` call. |
| **Mapping to spec ACs** | AC13 (DS2 envelope additive) + AC14 (read-only preserved) + AC15 (no new runtime deps) + AC16 (4-section preserved). |

---

## 4. Data Flow -- `dirty_files` lifecycle (R1 detail)

```
[1] _git("status", "--porcelain", cwd=project_dir)          # cli.py:3546
        |
        |  cp.stdout (e.g., " M src/foo.py\n?? tmp/bar\n")
        v
[2] out["dirty"] = bool(cp.stdout.strip())                   # cli.py:3548 (KEPT)
    out["dirty_files"] = cp.stdout.strip().splitlines() or []  # cli.py:3548 (NEW)
        |  (defensive: empty splitlines() from "" -> [""] stripped to [])
        v
[3] project dict  (DS1 envelope / needs_attention source)    # name-keyed
        |
        v
[4] _summarize_workspace_status  (cli.py:2892-2919)         # NEW: copy dirty_files
    if project.get("dirty") is True and project.get("has_git") is True:
        reasons.append("R1: uncommitted work")
        # NEW (single line inserted after the reasons.append):
        entry["dirty_files"] = list(project.get("dirty_files") or [])
        |
        v
[5] needs_attention entry (DS2 envelope):
    { "name": "...", "path": "...", "reasons": [...], "dirty_files": [...] }   # additive field
        |
        v
[6] fetch_status_summary()   (dashboard.py:152-159, subprocess)
        |
        v
[7] workspace_dashboard_cmd (cli.py:3040-3090)
    needs_attention = status_envelope.get("needs_attention", [])  # carries dirty_files
        |
        v
[8] render_r1_detail(needs_attention) -> Table | None           # NEW, dashboard.py
    if not any(entry.get("dirty_files") for entry in needs_attention):
        return None
    table = Table(title="R1 dirty files (capped at 20 per project)", ...)
    for entry in needs_attention:
        dirty_files = entry.get("dirty_files") or []
        if not dirty_files:
            continue
        truncated = _truncate_dirty_files(dirty_files, cap=20)
        table.add_row(name, "\n".join(truncated), style=...)
    return table
        |
        v
[9] render_dashboard(...)  (dashboard.py:606-645)             # UPDATED
    sections = [render_header(...), render_needs_table(...)]
    r1_table = render_r1_detail(needs_attention)
    if r1_table is not None:
        sections.append(r1_table)               # between Section B and C
    archived_table = render_archived(archived)
    if archived_table is not None:
        sections.append(archived_table)         # Section C
    sections.append(render_footer())
    return Group(*sections)
```

**Defensive defaults**:

| Edge case | Source | Default |
|-----------|--------|---------|
| `git status --porcelain` returns non-zero (broken `.git/`) | `_detect_project_markers` L3545-3550 | `dirty_files=[]` (existing try/except preserves `dirty=None`) |
| `git status` returns empty stdout (clean project) | splitlines on `""` | `dirty_files=[]` |
| `git` not installed | `_git` raises OSError | `dirty_files=[]` |
| `_detect_project_markers` not yet migrated | legacy caller | `entry.get("dirty_files", [])` returns `[]` |
| Project has `has_git=False` | `_detect_project_markers` never runs `git status` | `dirty_files=[]` (already absent) |
| Older dashboard binary consuming new DS2 | existing consumer with `entry.get("reasons", [])` | "consumers ignore unknown keys" -- backward compatible |

---

## 5. Component 1 -- File-by-File Change Map (exhaustive)

### 5.1 `src/flow_engineering/cli.py` -- Modified

| Location | Symbol | Action | Description |
|----------|--------|--------|-------------|
| L84-93 (near `_resolve_projects_root`) | `_iter_project_subdirs(root: Path) -> list[Path]` | **ADD** | New private helper; returns sorted subdirs excluding dot-prefix; docstring cites the lock; ~5 LOC |
| L2892-2919 (`_summarize_workspace_status`) | `_summarize_workspace_status` | **MODIFY** (single line inside the `if reasons:` block) | When R1 reason added to `reasons`, also set `entry["dirty_files"] = list(project.get("dirty_files") or [])` on the `needs_attention` entry. ~1 LOC delta. Defensive: `list(...)` for `list | None`, `or []` for missing key. |
| L3017 (`workspace_status` scan site) | `workspace_status` | **MODIFY** (1 line) | `subdirs = sorted([...])` -> `subdirs = _iter_project_subdirs(root)`. 0 LOC delta (same expression, just a helper call). |
| L3040-3090 (`workspace_dashboard_cmd`) | `workspace_dashboard_cmd` | **MODIFY** (L3089 only) | Add `sys.stdout.reconfigure(encoding="utf-8")` in `try/except OSError` immediately above the `Console(...)` call. `Console(no_color=no_color, soft_wrap=False)` -> `Console(width=<int>, soft_wrap=True, no_color=no_color)` where `<int>` is resolved at call-site as `(c.size.width or 120) if (c := Console().size.width) else 120` -- keep it simple: probe once, cache, pass explicitly. ~5 LOC delta. |
| L3517-3578 (`_detect_project_markers`) | `_detect_project_markers` | **MODIFY** (L3547-3550 only) | `out["dirty"] = bool(cp.stdout.strip())` -> keep the bool, add `out["dirty_files"] = cp.stdout.strip().splitlines() or []` as a NEW key on the dict. ~2 LOC delta. |
| L3578 (function return) | (defensive default for clean projects) | Existing `_detect_project_markers` already returns a new dict (L3578), so no mutation risk from outside callers. | -- |
| L3628 (`projects_ls` scan site) | `projects_ls` | **MODIFY** (1 line) | Same as L3017 -- replace inline iteration with `_iter_project_subdirs(root)`. 0 LOC delta. |

### 5.2 `src/flow_engineering/dashboard.py` -- Modified

| Location | Symbol | Action | Description |
|----------|--------|--------|-------------|
| L34-37 (imports) | `from typing import Any, Literal` | **ADD** | `Literal` type for overflow constants. 1 line. |
| L419-481 (`render_needs_table`) | `_NEEDS_COLUMN_HEADERS` + per-column `add_column` | **MODIFY** | Replace `table.add_column(header)` loop with explicit `overflow=` + `min_width` + `max_width` per column. Header tuple UNCHANGED (backward-compatible). ~10 LOC delta. |
| L535-576 (`render_archived`) | `render_archived` | **MODIFY** | Add explicit `min_width` + `max_width` per column (no `overflow=` -- columns are short, but `min_width=10` ensures header readability). ~5 LOC delta. |
| NEW (after `render_archived` at L577) | `_R1_DETAIL_CAP: int = 20` | **ADD** | Module-level constant (design §4.2 cap value). 1 line. |
| NEW | `_truncate_dirty_files(files: list[str], cap: int = 20) -> list[str]` | **ADD** | Pure helper; if `len(files) > cap`, slice to `cap - 1` and append ASCII `"..."`. Returns a new list. ~5 LOC. |
| NEW | `render_r1_detail(needs_attention: list[dict[str, Any]]) -> Table | None` | **ADD** | New render function; mirrors `render_archived` shape. Returns `None` when no project has `dirty_files` non-empty. ~25 LOC. |
| L606-645 (`render_dashboard`) | `render_dashboard` | **MODIFY** | Append Section E (from `render_r1_detail`) between Section B (L639) and Section C (L641). Conditional on `r1_table is not None`. ~4 LOC delta. Docstring: update "4 sections" to "5 sections: A -> B -> E -> C -> D". |
| L582-600 (`render_footer`) | `render_footer` | **MODIFY** | Append a 3rd tip line: "When R1 is triggered, see Section E for dirty files..." ~2 LOC delta. |
| L648-663 (`__all__`) | `__all__` | **MODIFY** | Add `"render_r1_detail"` + `"_truncate_dirty_files"`. ~1 LOC delta. |

### 5.3 `tests/unit/test_dashboard.py` -- Modified

| Location | Test Class / Group | Action | Description |
|----------|--------------------|--------|-------------|
| T8 group | `TestRenderNeedsTable` | **MODIFY** | Add `test_render_needs_table_folds_long_names` (long project name -> wrapped, no Unicode ellipsis), `test_render_needs_table_no_unicode_ellipsis_in_output` (assert that the Unicode U+2026 character is not in `_render_text(...)`). Snapshot uses `Console(width=40, no_color=True, record=True, file=io.StringIO())` to test the narrow-terminal case. ~25 LOC delta. |
| NEW (after T9 -- `TestRenderArchived`) | `TestRenderR1Detail` | **ADD** | 6 tests: `test_r1_detail_returns_none_when_no_r1_triggered`, `test_r1_detail_returns_table_when_r1_triggered`, `test_r1_detail_includes_project_name_for_each_r1_project`, `test_r1_detail_caps_at_20_files`, `test_r1_detail_uses_ascii_ellipsis_when_files_exceed_cap`, `test_r1_detail_omits_projects_with_empty_dirty_files`. ~60 LOC. |
| NEW | `TestTruncateDirtyFiles` | **ADD** | 3 tests: `test_truncate_dirty_files_below_cap_unchanged`, `test_truncate_dirty_files_above_cap_truncated`, `test_truncate_dirty_files_uses_ascii_ellipsis`. ~15 LOC. |
| NEW | `TestRenderDashboardComposesSectionE` | **ADD** | 3 tests: `test_render_dashboard_includes_section_e_when_r1_triggered`, `test_render_dashboard_omits_section_e_when_no_r1_triggered`, `test_render_dashboard_section_e_appears_between_b_and_c` (assert order via `_render_text` snapshot). ~25 LOC. |
| NEW | `test_render_footer_includes_section_e_hint` | **ADD** | Footer 3rd tip line substring assertion. ~10 LOC. |
| (no change) | existing 38 tests | MUST REMAIN GREEN | Per Pattern #548 / Preservation Gate C below |

### 5.4 `tests/unit/test_cli_dashboard.py` -- Modified

| Location | Test | Action | Description |
|----------|------|--------|-------------|
| `test_workspace_dashboard_cmd_with_no_color_suppresses_ansi` (L195) | `test_workspace_dashboard_cmd_with_no_color_suppresses_ansi` | **MODIFY** | Update the existing test to assert that `Console(width=120, ...)` (the new instance) emits no ANSI codes. ~3 LOC delta. |
| NEW (after current T12.* tests) | `test_workspace_dashboard_cmd_renders_section_e_when_r1_triggered`, `test_workspace_dashboard_cmd_section_e_truncates_at_20_files` | **ADD** | 2 CLI integration tests confirming the CLI handler propagates `dirty_files` to `render_dashboard` correctly and Section E appears at CLI layer with cap-20 truncation + ASCII `...` invariant. ~50 LOC. |

### 5.5 `tests/unit/test_cli_workspace_status.py` -- Modified

| Location | Test | Action | Description |
|----------|------|--------|-------------|
| NEW | `test_workspace_status_subdir_scan_excludes_dot_prefix_dirs` | **ADD** | Verify `_iter_project_subdirs` excludes `.atl`, `.opencode`, `.venv`, etc. Use `tmp_path` fixture. Asserts the scan list has NO dot-prefix entries even when the tmp_path contains `.foo`, `.bar`, `real_project`. ~15 LOC. |
| NEW | `test_summarize_workspace_status_threads_dirty_files_to_needs_attention` | **ADD** | Asserts `dirty_files` is copied onto `needs_attention` entry when R1 reason added. ~10 LOC. |
| NEW | `test_iter_project_subdirs_helper_excludes_dot_prefix`, `test_iter_project_subdirs_helper_empty_when_only_dot_dirs` | **ADD** | Direct helper unit tests. ~25 LOC. |

### 5.6 `tests/unit/test_cli_projects.py` -- Modified

| Location | Test | Action | Description |
|----------|------|--------|-------------|
| NEW | `test_projects_ls_subdir_scan_excludes_dot_prefix_dirs` | **ADD** | Mirrors the workspace_status RED test but for `projects_ls`. Uses `runner.invoke(main, ["projects", "ls", "--root", str(tmp_path)])`. Asserts the text output + JSON envelope omit dot-prefix entries. ~15 LOC. |

### 5.7 `src/flow_engineering/project_detector.py` -- Audit ONLY

| Aspect | Status |
|--------|--------|
| Hidden-file semantics | `_detect_project_markers` does NOT filter dot-prefix at the file-system level (it iterates `project_dir.iterdir()` to detect `.git`, `openspec`, etc.). This is correct -- the detector must see `.git` to detect `has_git=True`. **NO change.** |
| Conclusion | Confirmed by reading L3517-3578. The dot-prefix filter belongs at the subdir-scan level (`_iter_project_subdirs`), not at the per-project detection level. |

### 5.8 `src/flow_engineering/workspace_hygiene.py` -- Audit ONLY

| Aspect | Status |
|--------|--------|
| `HIDDEN_SYSTEM_FILES` semantics | Currently excludes only `.DS_Store`, `Thumbs.db`, `desktop.ini` from the "is this empty?" question (does NOT define what a "project" is). **NO change.** |
| `where.py:461` cross-project search | Re-uses `root.iterdir()` without dot-prefix filter; out of scope per locked scope. **Flagged for a future `flow-where-followup`** audit (per explore section 9). |
| Conclusion | `HIDDEN_SYSTEM_FILES` is unrelated to project enumeration (it's about per-project empty-check); the dot-prefix filter stays at `_iter_project_subdirs`. |

### 5.9 File map summary

| File | Symbols added | Symbols modified | Change type |
|------|---------------|------------------|--------------|
| `src/flow_engineering/cli.py` | `_iter_project_subdirs` | `_summarize_workspace_status`, `workspace_status`, `_detect_project_markers`, `projects_ls`, `workspace_dashboard_cmd` | Modified (6 sites, ~13 LOC delta) |
| `src/flow_engineering/dashboard.py` | `_truncate_dirty_files`, `render_r1_detail`, `_R1_DETAIL_CAP` | `render_needs_table`, `render_archived`, `render_dashboard`, `render_footer`, `__all__` | Modified (~50 LOC delta + ~30 new LOC) |
| `tests/unit/test_dashboard.py` | `TestRenderR1Detail` (6 tests), `TestTruncateDirtyFiles` (3 tests), `TestRenderDashboardComposesSectionE` (3 tests), `test_render_footer_includes_section_e_hint` (1 test) | `TestRenderNeedsTable` (2 new tests) | Modified (~155 LOC delta) |
| `tests/unit/test_cli_dashboard.py` | -- | `test_workspace_dashboard_cmd_with_no_color_suppresses_ansi` | Modified (~101 LOC delta) |
| `tests/unit/test_cli_workspace_status.py` | `test_workspace_status_subdir_scan_excludes_dot_prefix_dirs`, `test_summarize_workspace_status_threads_dirty_files_to_needs_attention` (T-C1..T-C5) | Modified (~156 LOC delta) |
| `tests/unit/test_cli_projects.py` | `test_projects_ls_subdir_scan_excludes_dot_prefix_dirs` (T-C6) | Modified (~62 LOC delta) |
| `src/flow_engineering/project_detector.py` | -- | -- | Audit only -- no change |
| `src/flow_engineering/workspace_hygiene.py` | -- | -- | Audit only -- no change |
| **Net total** | **3 functions + 1 constant + 13 tests + 4 test classes** | **5 functions + 2 tests** | **6 files modified + 2 audit-only** |

---

## 6. Encoding Strategy -- Detailed

### 6.1 Where the encoding reconfigure lives

`cli.py:3089` -- inside `workspace_dashboard_cmd`. Pattern:

```python
# cli.py:3089 (BEFORE)
console = Console(no_color=no_color, soft_wrap=False)
console.print(render_dashboard(...))

# cli.py:3089 (AFTER)
try:
    sys.stdout.reconfigure(encoding="utf-8")   # Pattern #551 graceful OSError
except OSError:
    pass                                         # Fall back to Rich's default

# Width introspection: probe once, cache the result
_probe = Console().size
_width = _probe.width if _probe.width and _probe.width > 0 else 120

console = Console(width=_width, soft_wrap=True, no_color=no_color)
console.print(render_dashboard(...))
```

### 6.2 Width fallback chain

| Source priority | Width source | Reason |
|-----------------|--------------|--------|
| 1 (preferred) | `Console().size.width` (Rich auto-detect) | Best fit for the operator's actual terminal |
| 2 (fallback) | `120` (hardcoded default) | Matches existing snapshot-test width at `test_dashboard.py:87` |
| 3 (last resort) | `80` (Rich's intrinsic default) | Only if both 1 and 2 fail (impossible in practice) |

Rationale: priority 1 may return `0` on non-TTY (redirected pipe). The `_width > 0` check gates the fallback.

### 6.3 Per-column overflow config

Section B `render_needs_table` at `dashboard.py:475-481` -- replace `_NEEDS_COLUMN_HEADERS` loop:

```python
# After (per-column with overflow config)
_column_specs = (
    ("project", 12, 30, OverflowMethod.fold),
    ("path",     30, 60, OverflowMethod.fold),
    ("R1",        3,  5, OverflowMethod.crop),
    ("R2",        3,  5, OverflowMethod.crop),
    ("R3",        3,  5, OverflowMethod.crop),
    ("R4",        3,  5, OverflowMethod.crop),
    ("R5",        3,  5, OverflowMethod.crop),
    ("total",     3,  4, OverflowMethod.crop),
)
for header, min_w, max_w, overflow in _column_specs:
    table.add_column(header, min_width=min_w, max_width=max_w, overflow=overflow)
```

- `name` + `path` use `fold` (wrap onto multiple lines).
- Rule columns + `total` use `crop` (truncate without ellipsis -- keeps ASCII safety).
- `path` continues to use `_truncate_path` for the 60-char middle-ellipsis (`...`) at the string level; per-column `fold` is the second layer.

`render_archived` at `dashboard.py:535-576` -- analogous change with column widths `(name, 12, 30, fold), (path, 30, 60, fold), (archived_at, 19, 25, crop), (reason, 20, 40, fold)`.

New Section E `render_r1_detail` -- columns `(project, 12, 30, fold), (dirty-files, 20, 80, fold)`.

### 6.4 Encoding + width fallback path (documented)

| Terminal type | `reconfigure` outcome | `_width` outcome | Render outcome |
|---------------|----------------------|------------------|----------------|
| Modern UTF-8 (Linux/macOS) | success | auto-detect (e.g., 120) | Correct UTF-8 + correct width |
| Windows 10+ with codepage 65001 | success | auto-detect | Correct UTF-8 + correct width |
| Windows legacy cp1252 | OSError -> fallback to Rich default | auto-detect | Non-ASCII names show `?` (correct -- the terminal cannot render them); ASCII names render correctly |
| Redirected pipe (piped through cat) | OSError (no TTY) | falls back to 120 | Deterministic snapshot output |
| CI environment (no TTY env vars) | OSError -> fallback | 120 | Deterministic snapshot output |

**Defense in depth**: even if both `reconfigure` and width auto-detect fail, the dashboard never emits Unicode U+2026 (we use `fold` + ASCII `...` exclusively). Operators on broken terminals see `?` for non-ASCII chars (which is the terminal's limitation, not the dashboard's).

---

## 7. Section E Render Approach

### 7.1 Location in `render_dashboard`

`dashboard.py:606-645` -- between Section B (L638-639) and Section C (L641-643):

```python
def render_dashboard(...):
    sections: list[Any] = [
        render_header(summary, no_color=no_color),
        render_needs_table(projects, needs_attention, no_color=no_color),
    ]
    # NEW (Section E -- conditional on R1 triggered):
    r1_table = render_r1_detail(needs_attention)
    if r1_table is not None:
        sections.append(r1_table)
    # Existing (Section C -- conditional on archived non-empty):
    archived_table = render_archived(archived)
    if archived_table is not None:
        sections.append(archived_table)
    sections.append(render_footer())
    return Group(*sections)
```

### 7.2 Cap mechanism

```python
def _truncate_dirty_files(files: list[str], cap: int = 20) -> list[str]:
    """Truncate file list to ``cap`` entries; append ASCII '...' when truncated."""
    if len(files) <= cap:
        return list(files)
    truncated = list(files[: cap - 1])
    truncated.append("... (truncated, run 'git status' for full list)")
    return truncated
```

Or -- alternatively -- append the `"..."` as the LAST cell in the table (so the operator sees the hint in context). The table-level approach is **recommended** because it puts the hint adjacent to the truncation, matching how dashboard Section B's footer row shows totals adjacent to per-row data.

Final shape (recommended):

```python
def render_r1_detail(needs_attention):
    r1_projects = [n for n in needs_attention if n.get("dirty_files")]
    if not r1_projects:
        return None
    table = Table(title="R1 dirty files (cap 20 per project)", ...)
    for entry in r1_projects:
        files = entry.get("dirty_files") or []
        truncated = _truncate_dirty_files(files, cap=20)
        table.add_row(entry["name"], "\n".join(truncated), style="red")
    return table
```

### 7.3 Footer hint update

`render_footer` at `dashboard.py:582-600` -- append a 3rd tip line:

```python
return Text.from_markup(
    "[dim]Tip:[/dim] Run [bold]flow workspace status --json[/bold] for JSON output.\n"
    "[dim]Tip:[/dim] Run [bold]flow workspace fix <project> --yes --backup[/bold] to remediate.\n"
    "[dim]Tip:[/dim] When [red]R1[/red] is triggered, see Section E for dirty files "
    "(capped at 20 per project). Run [bold]git status[/bold] in the project for the full list."
)
```

`render_footer` signature stays the same (no parameters changed); the new tip is unconditional -- text-only, no additional state.

### 7.4 ASCII `...` ellipsis (NOT Unicode U+2026)

Per `REQ-WORKSPACE-PROJECT-IDENTITY` lock + the proposal's hard "ASCII only" constraint:

- Section E truncation: `"..."` (3 ASCII periods, `0x2E 0x2E 0x2E`).
- `_truncate_path` (existing at L423-436): already uses ASCII `"..."` per proposal + audit.
- Rich `OverflowMethod.crop` (no ellipsis): safe -- Rich emits empty truncation, not the Unicode U+2026 char.
- Rich `OverflowMethod.fold`: safe -- emits `"\n"`, not the Unicode U+2026 char.
- Rich `OverflowMethod.ellipsis`: **FORBIDDEN** -- Unicode U+2026 corrupts on cp1252. All `add_column` calls in this change use `fold` or `crop` only.

---

## 8. Test Strategy (Strict TDD)

Per Constitution Article III + the 28 archived changes precedent. Each public function addition follows RED -> GREEN -> REFACTOR. Sub-batches per `work-unit-commits` are sized at 5-6 commits each, each commit <=400 LOC.

### 8.1 pytest-bdd scenarios (from the spec's 24 BDD scenarios)

The parallel `sdd-spec` produced a delta spec with **24 BDD scenarios** distributed across the 3 REQ deltas. They will be exercised via **pytest unit tests** that follow the dashboard precedent (the Phase 5 design noted that BDD feature files are optional when pytest covers the contract cleanly). Existing patterns: `tests/bdd/workspace_hygiene.feature` exists (16 scenarios); for this change, all scenarios live as pytest tests in the existing 4 unit test files.

| REQ delta | BDD scenarios (count from spec) | Maps to pytest test classes |
|-----------|-------------------------------|------------------------------|
| `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH` EXTEND | 7 scenarios (UTF-8 renders ASCII; cp1252 renders non-ASCII; OSError falls back; column overflow folds; no-color + encoding coexist; width=80 reasonable; --no-color stable after fix) | `tests/unit/test_dashboard.py` (TestRenderNeedsTable +2) |
| `REQ-WORKSPACE-PROJECT-IDENTITY` MODIFY | 5 scenarios (real-only workspace unchanged; mixed returns only regular; filter applies to status totals; filter applies to dashboard render; JSON shape unchanged) | `tests/unit/test_cli_workspace_status.py` (T-A1..T-A4) + `tests/unit/test_cli_projects.py` (T-A2 mirror) |
| `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` NEW | 8 scenarios (1 R1 project renders; no R1 hides section; cap 20 + ASCII `...`; exactly 20 no ellipsis; 0 dirty hides project; DS2 schema-compatible additive; consumers ignore unknown keys; renders ASCII `...`) | `tests/unit/test_dashboard.py` (TestRenderR1Detail+TestRenderDashboardComposesSectionE+TestTruncateDirtyFiles+test_render_footer_includes_section_e_hint) + `tests/unit/test_cli_dashboard.py` (CLI integration) |
| Regression Scenarios | 7 scenarios (4-section structure; filter flag preserved; sort flag preserved; no-color flag; JSON identity; dashboard read-only; no new deps) | existing 38 tests + AC16 snapshot in test_dashboard.py |
| **Total scenarios (spec)** | **27 scenarios** | All scenarios map to pytest tests in 4 files |

**Verification of spec scenarios in this design**: pytest-based. `sdd-tasks` will mechanically verify every scenario is exercised by at least one pytest test (no orphaned scenarios).

### 8.2 pytest unit tests (per Red-Green-Refactor)

Per-point unit test counts (provisional; sdd-spec's 24 scenarios drive the count):

| Test file | New unit tests | Rationale | ACs covered |
|-----------|----------------|-----------|-------------|
| `tests/unit/test_dashboard.py` | 13 (T8 +2; new TestRenderR1Detail +6; new TestTruncateDirtyFiles +3; new TestRenderDashboardComposesSectionE +3; test_render_footer_includes_section_e_hint +1) | Encoding/width (T8), Section E (TestRenderR1Detail), 20-cap helper (TestTruncateDirtyFiles), composer (TestRenderDashboardComposesSectionE), footer text update (footer test) | AC1, AC2, AC3, AC4, AC5, AC9, AC10, AC11, AC12, AC16 |
| `tests/unit/test_cli_dashboard.py` | 2 (T14 wiring +1; T15 Section E integration at CLI +1) | Encoding/width wiring at CLI layer; Section E end-to-end via `runner.invoke` | AC5, AC9, AC10, AC11, AC14, AC16 |
| `tests/unit/test_cli_workspace_status.py` | 5 (T-A1..T-A4 dot-prefix + T-C1..T-C5 dirty_files) | Each call site for `_iter_project_subdirs`; propagate `dirty_files` into `needs_attention` | AC7, AC13 |
| `tests/unit/test_cli_projects.py` | 1 (T-A2 dot-prefix + 1 T-C6 DS1 envelope) | Mirror T-A1 for the projects ls surface | AC6, AC8 |
| **Unit test total** | **21** | Matches the explore section 4.4 forecast (~21 unit tests for encoding+dot-prefix+R1 detail) | 16 ACs fully covered |

### 8.3 Snapshot tests (deterministic Rich output)

| Pattern | Files using it | New tests using it |
|---------|----------------|--------------------|
| `Console(width=120, force_terminal=False, no_color=True, record=True, file=io.StringIO())` then `export_text()` | existing: T7 (render_header), T8 (render_needs_table), T9 (render_archived), T10 (render_footer), T11 (render_dashboard) | T8 +2 (encoding/width), TestRenderR1Detail +6 (Section E isolation), TestRenderDashboardComposesSectionE +3 (composer composition) -- all use `_render_text` helper at `test_dashboard.py:79-94` |
| New pattern: `Console(width=40, no_color=True, record=True, file=io.StringIO())` | (none) | T8 +2 (narrow terminal -- prove `fold` wraps without Unicode ellipsis) |

**Snapshot test count**: **14 new snapshot tests** (existing pattern + new narrow-terminal pattern).

### 8.4 Strict TDD order (RED -> GREEN -> REFACTOR per task)

For each public function added or modified, the order is:
1. **RED** -- write the failing test first.
   - `render_r1_detail` not yet present -> test asserts Section E content -> fails with `ImportError` or `AttributeError`.
   - `_iter_project_subdirs` not yet extracted -> test calls the helper directly -> fails with `ImportError`.
   - `dirty_files` not yet captured -> test asserts entry has `dirty_files` list -> fails with `KeyError`.
2. **GREEN** -- minimum code to pass the test.
   - For Section E: minimum = `render_r1_detail` returns a `Table` when R1 triggered, `None` otherwise; `_truncate_dirty_files` truncates at cap.
   - For scan helper: minimum = `sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))`.
   - For `dirty_files`: minimum = `out["dirty_files"] = cp.stdout.strip().splitlines() or []`.
3. **REFACTOR** -- clean up the minimum while keeping tests green.
   - For Section E: extract `_truncate_dirty_files`, refine column widths, add footer hint.
   - For scan helper: add docstring + type hints.
   - For `dirty_files`: defensive `list(project.get("dirty_files") or [])` copy.

`pytest.raises` + `pytest.warns` patterns match the existing test file conventions (see `test_cli_dashboard.py:195`).

### 8.5 Sub-batch plan per `work-unit-commits` skill

The single-PR recommendation (if `sdd-tasks` confirms single-PR) lands in **4 sub-batches** of 5-6 commits each (<=400 LOC per commit). Each sub-batch has its own RED -> GREEN -> REFACTOR cycle and conventional commit prefix.

| Sub-batch | Theme | RED tests | GREEN impl | REFACTOR + commit | Commit prefix | LOC (approx) |
|-----------|-------|-----------|------------|-------------------|---------------|--------------|
| **A. Scan helper** | Point 2 -- `_iter_project_subdirs` | `test_workspace_status_subdir_scan_excludes_dot_prefix_dirs`, `test_iter_project_subdirs_helper_excludes_dot_prefix`, `test_iter_project_subdirs_helper_empty_when_only_dot_dirs`, `test_projects_ls_subdir_scan_excludes_dot_prefix_dirs` | helper at `cli.py:84` + 2 call sites at L3017 + L3628 | docstring + test cleanup | `feat(cli): filter dot-prefix dirs from workspace scan` | ~80 |
| **B. Encoding + width** | Point 1 -- Console + column widths | `test_render_needs_table_folds_long_names`, `test_render_needs_table_no_unicode_ellipsis_in_output`, `test_workspace_dashboard_cmd_console_reconfigure_handles_oserror`, `test_workspace_dashboard_cmd_console_uses_explicit_width`, `test_render_archived_uses_explicit_column_widths`, `test_render_archived_no_unicode_ellipsis`, `test_workspace_dashboard_cmd_with_no_color_suppresses_ansi` (REFACTOR tighten) | `sys.stdout.reconfigure` + `Console(width=, soft_wrap=True)` + per-column widths + `render_archived` widths | cleanup imports + `@pytest.fixture` for Console setup | `fix(dashboard): utf-8 encoding + per-column width wrap` | ~120 |
| **C. R1 detail (data plumbing)** | Point 3 -- `dirty_files` capture + thread | `test_detect_project_markers_captures_dirty_files`, `test_detect_project_markers_dirty_files_empty_on_clean_status`, `test_detect_project_markers_dirty_files_empty_on_subprocess_error`, `test_summarize_threads_dirty_files_when_r1`, `test_summarize_omits_dirty_files_when_not_r1`, `test_flow_projects_ls_json_envelope_includes_dirty_files` | `_detect_project_markers` L3547-3550 (capture stdout as list); `_summarize_workspace_status` L2892-2919 (copy to entry) | defensive defaults at `entry.get("dirty_files") or []` | `feat(dashboard): thread dirty_files through DS1/DS2 envelopes` | ~246 |
| **D. R1 detail (render)** | Point 3 -- `render_r1_detail` + Section E + footer | `TestRenderR1Detail` (6 tests) + `TestTruncateDirtyFiles` (3 tests) + `TestRenderDashboardComposesSectionE` (3 tests) + `test_render_footer_includes_section_e_hint` (1 test) + 2 CLI integration tests | `_truncate_dirty_files` + `render_r1_detail` + `render_dashboard` insert + `render_footer` append | footer text + composer order + docstring fix (4-section -> 5-section) | `feat(dashboard): render R1 dirty file detail (Section E)` | ~458 |

Each sub-batch is a **work unit** (single coherent concern, <=400 LOC, fully verifiable). The 4 sub-batches map naturally onto the chained PR strategy (PR1 = A+B, PR2 = C+D). PR2 is further split into PR2a (C: data plumbing) + PR2b (D pure renderers) + PR2c (D integration + footer hint) per the 3-way re-split on `apply-progress` observation #1890.

---

## 9. Out of Scope (explicit, mirror of proposal section Out of Scope + spec section Out of Scope)

- NO new subcommands (`flow workspace dashboard` is the only dashboard surface).
- NO new flags (`--json`, `--detail`, `--fix`, `--archive`, `--restore`, `--yes` stay absent -- `REQ-WORKSPACE-DASHBOARD-FLAGS` + `REQ-WORKSPACE-DASHBOARD-READ-ONLY`).
- NO mutations to registry or filesystem (read-only surface per `REQ-WORKSPACE-DASHBOARD-READ-ONLY`).
- NO modifications to `workspace/spec.md` root spec directly (deferred to next `workspace-spec-section-cleanup-*` cycle per Pattern #605; sdd-archive will merge delta REQs).
- NO TUI / web / interactive / filter / layout changes (deferred to Phase 5.2 per `REQ-WORKSPACE-DASHBOARD-DEFER-INTERACTIVE`).
- NO modifications to PR1 (`6651add`) / PR2 (`95e8579`) / PR3 (`778efdb`) / sort-projects (`c9c9650d`) / the 3 prior follow-up commits (Pattern #548 -- don't touch green commits).
- NO touch of `openspec/changes/v1.1-followups/` (sacred territory).
- NO new runtime deps (`rich` already transitive; promotion to direct dep is zero-cost per AC15).
- NO `stash`-triggering words in any new code or commit.
- NO AI attribution in commits (per `AGENTS.md` + repo policy).
- NO modifications to `where.py:461` cross-project search even though it has the same dot-prefix issue -- flagged for `flow-where-followup` audit.
- NO new `_iter_project_subdirs` consumers other than the 2 call sites (the 3rd caller is `where.py:461`, out of scope).

---

## 10. Pre-existing Failures (out-of-scope reminder)

| Item | Count |
|------|-------|
| Lint errors (`cli.py:696 RET504`; `test_cli_where_cross_project.py:{33 UP035, 295 W292}`) | 3 |
| sqlite-vec reindex test failures (opt-in) | 4 |
| mypy yaml-stub errors | 2 |
| Skipped tests | 2 |
| **Total pre-existing OOS** | **11** |

All pre-existing -- NOT introduced by this change. Documented for next session's hygiene pass.

---

## 11. Migration / Rollout

**No migration required.** This is a backward-compatible additive change:

| Aspect | Before | After | Compatibility |
|--------|--------|-------|---------------|
| Console encoding | `Console(no_color=no_color, soft_wrap=False)` | `Console(width=_width, soft_wrap=True, no_color=no_color)` (after reconfigure try/except) | Output is **wider, wraps longer** -- existing snapshot tests at T7/T8/T9/T10/T11 need width binding (use `_render_text` helper at width=120) |
| Scan filter | `[p for p in root.iterdir() if p.is_dir()]` | `_iter_project_subdirs(root)` | Output excludes dot-prefix dirs; **fewer projects** in dashboard + `flow projects ls` + `flow workspace status` totals |
| DS2 envelope | `{name, path, reasons, ...}` | `{name, path, reasons, dirty_files?, ...}` | `version: "1"` UNCHANGED; additive field per the v1 schema's "consumers ignore unknown keys" contract (per AC13) |
| Dashboard sections | A + B + (C if any) + D | A + B + (E if R1) + (C if any) + D | Conditional -- Section E appears ONLY when R1 triggered; common case is unchanged shape (per AC9+AC10+AC16) |
| ASCII ellipsis | Unicode U+2026 (single char, becomes replacement char on cp1252) | `...` ASCII (3 dot chars); `fold` wraps content; `crop` truncates without ellipsis | Operators on cp1252 terminals see correct chars; operators on UTF-8 terminals see the same output (per AC1+AC2+AC3) |

**Rollback** (per proposal Rollback Plan):

1. Revert `cli.py`:
   - Remove `try/except OSError` + `sys.stdout.reconfigure` block.
   - Replace `Console(width=_width, soft_wrap=True, ...)` with the original `Console(no_color=no_color, soft_wrap=False)`.
   - Remove `_iter_project_subdirs` helper definition.
   - Replace `_iter_project_subdirs(root)` calls at L3017 + L3628 with the inline `[p for p in root.iterdir() if p.is_dir()]`.
   - Remove `out["dirty_files"] = ...` line at L3548.
   - Remove `entry["dirty_files"] = ...` line in `_summarize_workspace_status`.
2. Revert `dashboard.py`:
   - Remove per-column `min_width`/`max_width`/`overflow=` kwargs from `Table.add_column` calls in `render_needs_table` + `render_archived`.
   - Remove `render_r1_detail` + `_truncate_dirty_files` symbols.
   - Remove Section E append block from `render_dashboard`.
   - Remove the 3rd tip line from `render_footer`.
3. Revert 4 test files to pre-change state (`test_dashboard.py`, `test_cli_dashboard.py`, `test_cli_workspace_status.py`, `test_cli_projects.py`).
4. Run full suite -- expect 38 existing dashboard tests + the new ones passing. After rollback, only the 38 should remain green.

---

## 12. Wall-Time Forecast (remaining phases)

| Phase | Wall-time | Reason |
|-------|-----------|--------|
| `sdd-tasks` | ~8 min | Mechanical derivation from this locked design (4 sub-batches per section 8.5 -> 4 task groups; each RED-GREEN-REFACTOR cycle is a task unit) |
| `sdd-apply` | ~25 min | 4 sub-batches x ~6 min RED+GREEN+REFACTOR per sub-batch; ~155 raw LOC across 6 files; ~28 new tests; 4 fixtures updated |
| `sdd-verify` | ~6 min | 38 existing dashboard tests + 28 new tests + 16 ACs + 4 sub-batch verification gates per section 13 |
| `sdd-archive` | ~2 min | Single-PR archive (4 commits -> 1 PR -> archive into `2026-07-01-workspace-dashboard-usability-pass/`); merge delta REQs from `specs/workspace-dashboard/spec.md` into root `specs/workspace/spec.md` per the family-index source-of-truth rule (adds `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` block + extends `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH` + `REQ-WORKSPACE-PROJECT-IDENTITY`) |
| **Total remaining** | **~41 min** | Within explore's 85-min single-PR wall-time forecast |

---

## 13. PR Split -- Possibility (NOT COMMITTED, sdd-tasks decides)

> **CRITICAL**: Per orchestrator prompt + explore section 4.4, the PR split is **POSSIBLE**, NOT COMMITTED. `sdd-tasks` is the gate that decides.

### 13.1 Tentative split (forecasting basis only)

| PR | Contents | Raw LOC | Multiplied (x6 conservative) | Realistic mid |
|----|----------|---------|------------------------------|---------------|
| **PR1** (tentative) | Sub-batches A + B -- Encoding/width + dot-prefix filter | ~55 raw src + ~50 raw tests = ~105 | ~630 | ~350-450 |
| **PR2** (tentative) | Sub-batches C + D -- R1 detail (data flow + Section E) | ~50 raw src + ~50 raw tests = ~100 | ~600 | ~350-500 |

Both PRs exceed 400 LOC at the conservative x6 multiplier (which assumes worst-case test+fixture growth). Both fit within realistic mid-range on the lower bound. The **single-PR** strategy is also feasible at ~550-700 realistic LOC (within user's tight-usability-pass preference).

### 13.2 Why the recommendation is NOT locked

- The orchestrator cached `delivery_strategy: single-pr-default` (per session preflight).
- `sdd-tasks` will re-forecast by enumerating tasks and reading the code-change diff.
- The user's tight-usability-pass preference favors 1 PR; the strict-TDD x6 precedent argues for chained; the diff size hides whether the *realistic* LOC is closer to 400 or 700.
- **The decision lives at `sdd-tasks`, not at design.**

### 13.3 What design locks (vs. what it leaves open)

| Decision | Locked here? | Why |
|----------|--------------|-----|
| 4 sub-batches (A/B/C/D) | YES | They're the natural RED->GREEN->REFACTOR work units; each fits one commit at <=400 LOC |
| Sub-batches group as A+B and C+D | YES | Independence: A+B is UI/scan (no DS change); C+D is DS threading + render |
| Single PR vs. chained PR | **NO -- sdd-tasks decides** | Forecast is borderline; lock would overcommit |
| Commit messages per sub-batch | YES (4 messages drafted in section 8.5) | Conventional Commit prefixes; ready for mechanical application |
| Branch strategy | Not at this layer | `sdd-tasks` + the user's Git workflow conventions decide |

### 13.4 Per-sub-batch commit message (drafted)

```
# Sub-batch A
feat(cli): filter dot-prefix dirs from workspace scan

Extract _iter_project_subdirs(root) helper that excludes any subdir whose
name starts with '.' (tooling/config); apply at workspace_status (L3017)
and projects_ls (L3628). View-only filter -- no directory is modified,
archived, or deleted.

Pattern #582 closed box: 1 helper + 2 call sites + 2 RED tests.
Pattern #548 honored: PR1-PR3 + sort-projects + 3 prior follow-ups untouched.
AC9 byte-identical guard at tests/unit/test_cli_projects.py:435 still green.

# Sub-batch B
fix(dashboard): utf-8 encoding + per-column width wrap

Try sys.stdout.reconfigure(encoding='utf-8') wrapped in try/except OSError
(Pattern #551). Console instantiation now uses explicit width + soft_wrap=True
+ best-effort terminal-introspection with width=120 fallback. Per-column
min_width + max_width + OverflowMethod.fold on Section B; analogous config
on render_archived. NEVER ellipsis -- fold/crop only; ASCII '...' elsewhere.

Spanish-accent project names render correctly on cp1252 terminals; long
names wrap (not truncate) within column bounds; no Unicode U+2026
ellipsis char appears in any output cell.

# Sub-batch C
feat(dashboard): thread dirty_files through DS1/DS2 envelopes

_detect_project_markers captures git status --porcelain stdout as
dirty_files: list[str] (zero new subprocess cost; one extra splitlines()).
_summarize_workspace_status copies dirty_files onto the needs_attention
entry when R1 reason added. DS2 envelope version '1' unchanged; additive
field per 'consumers ignore unknown keys' contract (backward-compat).
DS1 envelope (flow projects ls --json) also gains dirty_files.

# Sub-batch D
feat(dashboard): render R1 dirty file detail (Section E)

New render_r1_detail(needs_attention) -> Table | None; returns None when no
R1 triggered. Section E appended between B and C in render_dashboard,
conditional on r1_table is not None. _truncate_dirty_files caps each
project's file list at 20 with ASCII '...' tail. render_footer gains a 3rd
tip pointing to git status for full list. None of the existing dashboard
sections change shape or contracts.
```

All 4 messages:

- Conventional Commits prefixes (`feat(cli):`, `fix(dashboard):`, `feat(dashboard):`).
- Subject lines <=72 chars; bodies wrapped.
- NO "Co-Authored-By" or AI attribution.
- Each cites the relevant REQ delta + the locked scope guard.
- Cross-references to the cleanup-change's `v1.1-followups/` always negative.

---

## 14. Constraints Honored

- Read-only surface (`REQ-WORKSPACE-DASHBOARD-READ-ONLY`) -- no mutations anywhere.
- No new CLI flags (Pattern #538 + read-only constraint).
- No new subcommands.
- `rich` stays transitive; no new runtime deps (AC15).
- Library-first per Constitution Article I -- code in `src/flow_engineering/`, CLI is thin wrapper (`workspace_dashboard_cmd` L3040-3090 stays a thin wiring layer).
- Strict TDD per Constitution Article III -- every public addition has RED before GREEN.
- Pattern #582 ("limpiar lo prometido, nada mas") -- 3 points only; no scope expansion to Phase 5.2 / TUI / web.
- Pattern #548 (don't touch green commits) -- PR1/PR2/PR3/sort-projects/3-prior-follow-ups all unchanged.
- Pattern #551 (graceful OSError fallback) -- `sys.stdout.reconfigure` wrapped in `try/except`.
- Pattern #605 (defer the L299 trigger-row edit to a follow-up) -- `workspace/spec.md` untouched in this change; delta REQs merge at archive time.
- ASCII `...` (3 chars) ellipsis ONLY -- never Unicode U+2026.
- 20-file cap on Section E per project; ASCII `...` truncation; footer hint for full list.
- 4 follow-up candidates documented (per explore section 9): `extract-build-needs-by-name-helper`, `remove-sort-projects-deprecation-fallback`, AC6 wording fix (Unknown -> Unsupported), `flow-where-followup` (dot-prefix audit).

---

## 15. Open Questions (resolved at design)

The open questions from the explore phase are resolved here, ahead of `sdd-tasks`. The parallel `sdd-spec` also resolved its open questions (5 questions resolved there).

| # | Question | Answer | Spec Q mapped |
|---|----------|--------|---------------|
| Q1 | `Console.width` default | **Auto-detect first, width=120 fallback** -- see section 6.2 | Spec Q1 confirmed |
| Q2 | Dot-prefix filter for `flow where` | **Out of scope** -- flagged for `flow-where-followup` | Spec Q2 confirmed |
| Q3 | Footer hint for Section E | **3rd tip line appended** -- see section 7.3 | Spec Q3 confirmed |
| Q4 | `sys.stdout.reconfigure` on Linux/macOS | **Works on all 3 platforms** (Python 3.7+); no regression for the existing `_render_text` fixture at `test_dashboard.py:79-94` | (Spec did not raise this one) |
| Q5 | Capture `dirty_files` always vs only when dirty | **Always** (empty list when clean) -- easier to consume; falsy check at `if entry.get("dirty_files"):` | Spec Q4 confirmed |
| Q6 | Section E lives in `render_dashboard` vs. Click handler | **In `render_dashboard`** -- mirrors how Section C is appended conditionally; keeps composer responsibility | (Spec did not raise this one) |
| Q7 | Real `.config` project caveat | **Caveat acknowledged in changelog, NOT a fail-case** | Spec Q5 confirmed |

---

## 16. Interfaces / Contracts (summary)

### 16.1 New public symbols

| Symbol | Signature | Module | Returns |
|--------|-----------|--------|---------|
| `_iter_project_subdirs` | `(root: Path) -> list[Path]` | `cli.py` | Sorted subdirs excluding `name.startswith(".")`; never raises |
| `render_r1_detail` | `(needs_attention: list[dict[str, Any]]) -> Table | None` | `dashboard.py` | Rich Table when R1 triggered; None otherwise |
| `_truncate_dirty_files` | `(files: list[str], cap: int = 20) -> list[str]` | `dashboard.py` | Truncated list with ASCII `"..."` tail when above cap; never raises |

### 16.2 Modified public symbols (contract unchanged; new behavior)

| Symbol | Delta |
|--------|-------|
| `Console(...)` instantiation at `cli.py:3089` | Now reconfigure-encodes stdout + uses explicit width + soft_wrap |
| `_detect_project_markers` at `cli.py:3517-3578` | Dict gains `dirty_files: list[str]` key |
| `_summarize_workspace_status` at `cli.py:2878-2923` | `needs_attention` entries gain `dirty_files: list[str]` key when R1 reason added |
| `render_needs_table` at `dashboard.py:444-518` | Per-column widths + OverflowMethod.fold |
| `render_archived` at `dashboard.py:535-576` | Per-column widths |
| `render_dashboard` at `dashboard.py:606-645` | Section E appended between B and C, conditional on R1 |
| `render_footer` at `dashboard.py:582-600` | 3rd tip line for Section E |

### 16.3 Backward compat for `flow` users consuming v1 envelopes

| Schema version | Field addition | Consumer behavior |
|----------------|----------------|-------------------|
| `"version": "1"` (DS1 + DS2) | `dirty_files: list[str]` | **Non-breaking** -- consumers that read specific keys (e.g., `entry["reasons"]`) are unaffected. Consumers that iterate all keys (e.g., `json.dumps(envelope)`) get the new key automatically. |

No schema bump to `"version": "2"`. Additive fields are explicitly the kind of change that the v1 schema tolerates (per `workspace/spec.md:112` and the DS1/DS2 schema rules; AC13).

---

## 17. Preservation Gates (per Pattern #548 + the cycle's 12-gate discipline)

After apply, the following preservation gates MUST remain green:

| # | Gate | Verification |
|---|------|--------------|
| 1 | PR1 commit `6651add` byte-identical (data layer) | `git show 6651add --stat` returns same file set |
| 2 | PR2 commit `95e8579` byte-identical (logic + rendering) | `git show 95e8579 --stat` returns same file set |
| 3 | PR3 commit `778efdb` byte-identical (Click wiring) | `git show 778efdb --stat` returns same file set |
| 4 | sort-projects commit `c9c9650d` byte-identical | `git show c9c9650d --stat` returns same file set |
| 5 | 3 prior follow-up commits byte-identical (`workspace-dashboard-section-cleanup`, `sort-projects-align-with-real-ds-data-flow`, `workspace-spec-section-cleanup-2`) | `git show <sha> --stat` per commit |
| 6 | 38 existing dashboard tests + the new ~21 tests all PASS | `uv run pytest tests/unit/test_dashboard.py tests/unit/test_cli_dashboard.py` |
| 7 | AC9 byte-identical guard `test_flow_projects_ls_json_byte_identical_envelope` green | `pytest -k byte_identical_envelope` |
| 8 | No `stash`-triggering words in any new code or output | `rg` over new files returns 0 hits; same for `_render_text` output of new tests |
| 9 | No AI attribution in any new commit | `git log --format='%(trailers)'` returns no `Co-Authored-By: ...` lines with AI markers |
| 10 | No new runtime deps | `pyproject.toml` `dependencies` list UNCHANGED (or `rich` promoted to direct, zero-cost) -- AC15 |
| 11 | No new CLI flags | `flow workspace dashboard --help` shows the same 3 flags as before (`--filter`, `--sort`, `--no-color`) -- AC14 |
| 12 | No Unicode U+2026 (single-char ellipsis) in any new code or output | `rg` over new files returns 0 hits; same for `_render_text` output of new tests |
| 13 | `v1.1-followups/` untouched | (untracked; verify via `git status`) |
| 14 | `workspace/spec.md` drift is UNCHANGED in this change (deferred to `workspace-spec-section-cleanup-*`); delta REQs merge at archive time | `git diff openspec/specs/workspace/spec.md` returns 0 lines for this PR's commits |

The verify phase (`sdd-verify`) iterates each gate against the post-apply state.

---

## 18. Next SDD Phase

`sdd-tasks` -- write `tasks.md` derived from the 4 sub-batches (A/B/C/D) per section 8.5. Expected output: 4 sub-batch task groups, each with RED tests -> GREEN impl -> REFACTOR + commit. Then `sdd-tasks` runs the **Review Workload Guard** per `openspec/config.yaml:128` and may recommend chained PR (PR1 = A+B, PR2 = C+D) based on the actual x4-x6 multiplier observed.

`sdd-tasks` is dispatched after `sdd-spec` and this design both return. Both parallel artifacts are now complete (the spec produced 24 scenarios + 16 ACs; this design locks the implementation shape).

---

## 19. Pattern References (cited)

- **Pattern #538** -- "one identity per command". Honored: no `--json` on dashboard; no new flags.
- **Pattern #548** -- "don't touch green commits for aesthetic reasons". Honored: PR1/PR2/PR3/sort-projects/3-prior-follow-ups all unchanged.
- **Pattern #551** -- "Guards as instruments". Honored: `try/except OSError` around `sys.stdout.reconfigure` + defensive defaults throughout (`_truncate_dirty_files` cap; `_iter_project_subdirs` returns sorted, never raises; `dirty_files` defaults to `[]`).
- **Pattern #555** -- "Solo el primero ahora, no mezclemos los dos". Honored: one usability-pass change with 3 points, not 3 separate changes.
- **Pattern #582** -- "limpiar lo prometido, nada mas". Honored: closed box; 3 points only; no scope expansion.
- **Pattern #605** -- deferred `workspace/spec.md` L299 trigger-row edit. Honored: this change does NOT touch the root spec directly; L299 stays as-is; delta REQs merge at archive time.

---

*Generated by the `sdd-design` sub-agent for `workspace-dashboard-usability-pass`. Design philosophy: "limpiar lo prometido, nada mas" (Pattern #582) applied to a 3-point cosmetic + usability pass. Mirrored to Engram via `mem_save` with `topic_key: "sdd/workspace-dashboard-usability-pass/design"`, `type: "architecture"`, `project: flow-engineering`, `capture_prompt: false`.*

