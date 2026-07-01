# Explore: workspace-dashboard-usability-pass

> **Change**: `workspace-dashboard-usability-pass`
> **Phase**: explore (SDD pipeline)
> **Mode**: openspec (filesystem) + Engram mirror
> **Project**: flow-engineering v1.2.0
> **Strict TDD**: ON (feature change — RED → GREEN → REFACTOR discipline required at apply phase; ×6 multiplier per drift-hardening precedent)
> **Builds on**: `2026-06-30-phase-5-dashboard` (baseline, archived) + `2026-06-30-workspace-dashboard-section-cleanup` + `2026-06-30-sort-projects-align-with-real-ds-data-flow` + `2026-06-30-workspace-spec-section-cleanup-2`
> **Goal**: confirm exact locations + risks + REQ-alignment for **3 small usability fixes** to the existing read-only Rich dashboard surface. No scope expansion beyond the 3 user-locked points.

---

## 1. Goal (recap from user prompt)

Three concrete cosmetic + usability defects on the **already-shipped** read-only dashboard (`flow workspace dashboard`). All three live in the **existing** Phase 5 dashboard surface — no new commands, no new flags, no mutations. Dashboard stays read-only per `REQ-WORKSPACE-DASHBOARD-READ-ONLY`.

1. **Encoding/width fix** — long project names render with the Unicode replacement char (``) on Windows cp1252 terminals. First-impression cosmetic blocker for the operator's typical terminal.
2. **Dot-prefix scan filter** — tooling/config directories (`.atl`, `.opencode`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.venv`, `.specify`, `.github`) appear as "projects" because the workspace scan iterates `root.iterdir()` with no hidden-directory filter. Noise on every dashboard run.
3. **R1 detail** — dashboard says "R1: dirty" but does not show WHICH files are dirty. The dashboard stays read-only but exposes more information per project.

---

## 2. Scope (locked — user-fixed, do NOT re-debate)

### 2.1 In scope

- `src/flow_engineering/dashboard.py` — column-width + Console-encoding config + R1 detail rendering for `render_needs_table` / `render_dashboard`
- `src/flow_engineering/cli.py` — `workspace_dashboard_cmd` Console setup (encoding + width) + `_detect_project_markers` plumbing for R1 dirty files + the 2 subdir-iteration sites
- `src/flow_engineering/project_detector.py` — review for any dot-prefix conflict (audit only; expect NO change)
- `src/flow_engineering/workspace_hygiene.py` — audit hidden-file semantics at `_is_empty_project` / `_list_non_empty_files` (audit only; expect NO change — `HIDDEN_SYSTEM_FILES` excludes only `.DS_Store`/`Thumbs.db`/`desktop.ini`, NOT all dot-prefix)
- `tests/unit/test_dashboard.py` — RED tests for column widths, Console encoding, R1 detail rendering
- `tests/unit/test_cli_dashboard.py` — RED tests for the dot-prefix filter at scan sites + R1 detail threading
- `tests/unit/test_cli_workspace_status.py` — RED tests for dot-prefix filter on the status side
- `tests/unit/test_cli_projects.py` — RED tests for dot-prefix filter on the projects ls side
- Optionally `tests/unit/test_project_detector.py` — only if shared helper is extracted there
- Optionally extract a shared helper (e.g., `_iter_project_subdirs(root)`) to keep the 2 scan sites DRY

### 2.2 Out of scope (NON-NEGOTIABLE per user prompt + prior cycle precedents)

- **NO new subcommands**, **NO new flags** on the dashboard (`--json`, `--detail`, `--fix`, `--archive`, `--restore`, `--yes` stay absent — `REQ-WORKSPACE-DASHBOARD-FLAGS` + `REQ-WORKSPACE-DASHBOARD-READ-ONLY`).
- **NO mutations** to the registry or any filesystem path (`REQ-WORKSPACE-DASHBOARD-READ-ONLY`).
- **NO modifications** to `workspace/spec.md` root capability spec (separate change family).
- **NO modifications** to PR1+PR2+PR3 dashboard commits + sort-projects commit + the 3 prior follow-up commits (LOCKED per Pattern #548).
- **NO touch of `openspec/changes/v1.1-followups/`** (sacred territory).
- **NO expand to Phase 5.2** (TUI/web).
- **NO new runtime deps** (`rich` already transitive; promote to direct dep is zero-cost).
- **NO `stash`-triggering words** in any new code or commit.
- **NO AI attribution** in commits (per `AGENTS.md`).
- **NO modifications** to Phase 1/3/4 mutation gates or existing CLI commands.
- **NO interactive mutation triggers** from UI (deferred to Phase 5.2).

---

## 3. Current State (how the dashboard works today relevant to the 3 points)

### 3.1 Encoding / width

`src/flow_engineering/cli.py:3089`:

```python
console = Console(no_color=no_color, soft_wrap=False)
console.print(render_dashboard(projects, status_envelope, archived, needs_attention, no_color=no_color))
```

- `Console(no_color=no_color, soft_wrap=False)` — `soft_wrap=False` disables soft wrapping; combined with Rich's default column `overflow="ellipsis"` (per `rich/table.py:90`), this truncates cells with the **Unicode** `…` (U+2026) character when the cell exceeds the rendered column width.
- Windows console default codec is `cp1252`. The bytes `0xE2 0x80 0xA6` (`…` in UTF-8) are **invalid** in cp1252 → the terminal prints the Unicode replacement character `` (U+FFFD).
- For names that contain non-ASCII chars (e.g., `Gestor-de-Contraseas` with `` = U+00F1), the `` byte sequence `0xC3 0xB1` in UTF-8 also fails cp1252 → another ``.
- **Hard evidence reproduced locally** (test script ran against `Console(width=40, no_color=True, soft_wrap=False)`): `Gestor-de-Contraseas` renders as `Gestor-de-Contra`; long names like `foo-bar-quux-very-long-name-foo-bar-quux-very-long` render as `foo-bar-quux-very-l.`.

#### Where the bug lives

| Location | Why this matters |
|----------|----------------|
| `src/flow_engineering/cli.py:3089` | `Console(...)` instantiation — no explicit encoding, no explicit width, no `soft_wrap=True`. The Console inherits `sys.stdout` which on Windows defaults to cp1252. |
| `src/flow_engineering/dashboard.py:475-481` | `Table(...)` + `add_column(header)` — no `overflow=`, no `min_width=`, no `max_width=`, no `no_wrap=`. Per Rich `Column` defaults (`rich/table.py:90-109`), `overflow="ellipsis"` and `width=None` (auto). |
| `src/flow_engineering/dashboard.py:486` | `name = project.get("name", "")` — no width management. With `Console.width=40`, a 9-char name like `.opencode` fits, but `Gestor-de-Contraseas` (21 chars) overflows. |
| `src/flow_engineering/dashboard.py:487` | `path = _truncate_path(str(project.get("path", "")))` — already managed (60-char middle ellipsis, ASCII `...` per `_truncate_path` L423-436). **OK** for the path column. |
| `src/flow_engineering/dashboard.py:373-412` (`render_header`) | Uses f-strings with simple text — no special chars, ASCII-safe. **OK.** |
| `src/flow_engineering/dashboard.py:535-576` (`render_archived`) | Uses dict keys — same risk as `render_needs_table`. **Inherits the same problem** — needs the same fix. |

#### Why this is "encoding + width" not just "encoding"

The user's prompt bundles both into one point because they manifest together: a long Spanish name is BOTH non-ASCII AND long, so the operator sees `Gestor-de-Contraseas` rendered as `Gestor-de-Contra` regardless of whether the cause is encoding (cp1252 → `` for ``) or width (Rich ellipsis → `…` → ``). Both fixes are required to fully resolve the cosmetic complaint.

### 3.2 Dot-prefix scan filter

`src/flow_engineering/cli.py:3017` (`workspace_status`):

```python
subdirs = sorted([p for p in root.iterdir() if p.is_dir()])
projects = sorted(
    (_detect_project_markers(p) for p in subdirs),
    key=lambda d: d["name"],
)
```

`src/flow_engineering/cli.py:3628` (`projects_ls`):

```python
subdirs = sorted([p for p in root.iterdir() if p.is_dir()])
```

Both sites iterate **all** immediate subdirectories of the projects root with no hidden-directory filter. Confirmed live: `C:\dev\proyects\flow-engineering` contains `.atl`, `.github`, `.mypy_cache`, `.opencode`, `.pytest_cache`, `.ruff_cache`, `.specify`, `.venv`, plus 30+ real projects. All dot-prefix directories leak into the dashboard's project list because the dashboard consumes DS1 (`flow projects ls --json`) which is itself unfiltered.

#### Where the fix belongs

Three options considered (locked Option A — see §4):

| Option | Location | Tradeoff |
|--------|----------|----------|
| **A** — filter at the iteration sites (L3017 + L3628) | Scan-time filter; both `workspace_status` and `projects_ls` benefit; dashboard inherits automatically via subprocess | Reaches `_summarize_workspace_status` totals too (correctness — fewer fake projects, fewer false R2/R4 negatives). |
| B — filter inside `_detect_project_markers` | Adds an `is_dot_prefix` skip inside the function | Hidden filter; caller still iterates a too-large `subdirs` list; more work for no benefit. |
| C — filter at render time in the dashboard | Only hides the noise from the dashboard; `flow projects ls` still shows dot-prefix dirs; `flow workspace status` totals unchanged | Doesn't fix the actual problem; just hides it. REJECTED — the noise is a workspace-wide issue, not a dashboard-only one. |

#### Reachability audit

| Site | Reachable? | Touched by dashboard? |
|------|-----------|------------------------|
| `_resolve_projects_root` (cli.py:84) | YES — already imported by `workspace_status` + `workspace_dashboard_cmd` | The dashboard calls `flow projects ls --json` which calls `_resolve_projects_root` via the subprocess |
| `_detect_project_markers` (cli.py:3517) | YES — called from `_workspace_status_envelope` builder + from `workspace_status` text + from `projects_ls` text/JSON | The dashboard consumes the output of `_detect_project_markers` via the DS1 envelope |

A shared helper extraction (e.g., `_iter_project_subdirs(root) -> list[Path]` defined alongside `_resolve_projects_root` in `cli.py`) keeps the two scan sites DRY and gives a single hook for tests. **Recommended extraction** (per Article IV: 2 concrete cases = 2+1 future = extraction is justified).

### 3.3 R1 detail (data flow)

`src/flow_engineering/cli.py:3545-3550` (`_detect_project_markers`):

```python
try:
    cp = _git("status", "--porcelain", cwd=project_dir)
    if cp.returncode == 0:
        out["dirty"] = bool(cp.stdout.strip())
except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
    pass
```

The `git status --porcelain` stdout is being **discarded** after the boolean conversion. We already pay the subprocess cost — but only the bool is captured.

`src/flow_engineering/cli.py:2892-2919` (`_summarize_workspace_status`):

```python
for project in projects:
    reasons: list[str] = []
    if project.get("dirty") is True:
        totals["dirty"] += 1
        if project.get("has_git") is True:
            reasons.append("R1: uncommitted work")
    ...
    if reasons:
        needs_attention.append(
            {
                "name": str(project.get("name", "")),
                "path": str(project.get("path", "")),
                "reasons": reasons,
            }
        )
```

R1 is detected (boolean) and surfaced as a reason string, but the **list of dirty files** is lost at this boundary.

`src/flow_engineering/dashboard.py:444-518` (`render_needs_table`):

```python
for project in projects:
    name = project.get("name", "")
    path = _truncate_path(str(project.get("path", "")))
    entry = needs_by_name.get(name, {})
    reasons = entry.get("reasons", []) if isinstance(entry, dict) else []
    ...
    for rule in _NEEDS_RULE_COLUMNS:
        triggered = any(
            isinstance(r, str) and r.startswith(rule) for r in reasons_list
        )
        per_rule.append(_format_rule_cell(triggered, rule))
```

The R1 cell is **purely boolean** (`_format_rule_cell` returns `[red]R1[/red]` or `[green]OK[/green]`). No file-list info is consumed or rendered.

#### Where the data IS available

| Stage | Field available? | Currently propagated? |
|-------|------------------|----------------------|
| `_git("status", "--porcelain", cwd=...)` returns | YES — stdout has `XY filename` lines | **No** — discarded after `bool(stdout.strip())` |
| `_detect_project_markers` output | YES (potentially) | **No** — only `dirty: bool` |
| DS1 envelope (`flow projects ls --json`) | YES (potentially) | **No** — 11 static fields, no `dirty_files` |
| DS2 envelope (`flow workspace status --json`) needs_attention entries | YES (potentially) | **No** — `name` + `reasons` + `path` only |
| Dashboard render | n/a | n/a — no source to render from |

#### What's missing for "show me WHICH files"

Two things:
1. **Data plumbing**: capture `git status --porcelain` stdout as a list of paths in `_detect_project_markers`; thread it through DS1 + DS2 envelopes; surface it on the `needs_attention` entry (only when R1 triggered).
2. **Render plumbing**: a new render section (or expanded R1 cell content) that shows the dirty files for projects where R1 triggered.

The render shape has 3 candidates:

| Render option | Width cost | Discoverability | Verdict |
|---------------|------------|-----------------|---------|
| **(a)** Add a new column "R1 files" (count + first 3 truncated) | +1 column | Medium — requires scanning to "R1" column | Bloats the already-tight 9-column Section B table; ruled out. |
| **(b)** New Section E between B and C: "R1 dirty files" — list per-project | +1 section, only when any R1 triggered | High — distinct visual region; mirrors Section A/B/C/D pattern | **Recommended.** Matches the dashboard's existing 4-section shape; reads naturally; no column count increase. |
| **(c)** Embed R1 file list inline in the `name` cell when R1 is triggered (multi-line cell) | 0 column count increase, but row height grows | Low — visually overloaded with color + reason + files | Hard to scan; conflicts with the per-row color coding. Ruled out. |

---

## 4. Approach Options (per point)

### 4.1 Encoding/width — Recommended: **Option A (combined Console + Column)**

**Option A (locked)** — combined fix:
1. **Console encoding**: at `cli.py:3089`, attempt `sys.stdout.reconfigure(encoding='utf-8')` (Python 3.7+ stdlib; best-effort `try/except OSError` for non-TTY / redirected pipes). Fall back to `Console(file=sys.stdout)` if reconfig fails.
2. **Console width**: set `Console(width=<terminal-width>, soft_wrap=True)` so the dashboard shrinks gracefully on narrow terminals instead of truncating with `…`.
3. **Column widths**: in `dashboard.py:475-481`, set explicit `min_width` + `max_width` per column on the Section B and Section C tables. Use `OverflowMethod.fold` (wrap rather than ellipsis) so long names wrap onto multiple lines instead of producing `…`/`` artifacts. Apply the same to `render_archived` at L555.
4. **ASCII-only overflow character** (defense-in-depth): if `OverflowMethod.fold` doesn't fit, fall back to `OverflowMethod.crop` (no ellipsis) — never `…`.

Why A over alternatives:

- **A vs B (encoding-only)**: doesn't fix the width truncation; `Gestor-de-Contraseñas` still renders as `Gestor-de-Contra…` on cp1252 terminals because the `…` is the issue, not just the `ñ`.
- **A vs C (width-only)**: doesn't fix the cp1252 rendering of `ñ` itself; long names still get `` for the `…` truncation.
- **A vs D (custom `OverflowMethod.crop` only)**: loses the operator hint that content was truncated.

LOC estimate: ~15 src + ~30 tests = **~45 LOC**.

### 4.2 Dot-prefix scan filter — Recommended: **Option A (shared helper + scan-site)**

**Option A (locked)** — extract a shared helper:

```python
def _iter_project_subdirs(root: Path) -> list[Path]:
    """Return the project's immediate subdirectories, sorted, excluding dot-prefix.

    Dot-prefix entries (``.atl``, ``.opencode``, ``.venv``, ``.mypy_cache``,
    ``.pytest_cache``, ``.ruff_cache``, ``.specify``, ``.github``, etc.) are
    tooling/config — never user projects. They are skipped at scan time so
    the workspace stays focused on real code.
    """
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
```

Apply at `cli.py:3017` (`workspace_status`) and `cli.py:3628` (`projects_ls`).

Why A over alternatives:

- **A vs B (filter inside `_detect_project_markers`)**: the function still gets called for hidden dirs — wasted work + caller sees the full list. Worse for callers that introspect `subdirs` (e.g., `_render_workspace_status_text` at L2964 iterates `projects`, not `subdirs` directly, but `subdirs` IS the source).
- **A vs C (render-time filter only)**: `flow projects ls --json` and `flow workspace status --json` still emit the noise; downstream consumers must filter again; the totals (`projects`, `needs_attention`) keep counting fake projects.
- **A vs D (opt-in `--no-hidden` flag)**: adds a flag, breaks `REQ-WORKSPACE-DASHBOARD-FLAGS` "no new flags" intent if applied to dashboard, and adds operator cognitive load.

The dot-prefix filter is **silent** — operators never need to opt-in because the noise is universally unwanted.

LOC estimate: ~10 src + ~20 tests = **~30 LOC**.

### 4.3 R1 detail — Recommended: **Option B (new Section E)**

**Option B (locked)** — add a new Section E between Section B and Section C when any project has R1 triggered. The section lists `name` and the dirty files for each R1-triggered project.

Data plumbing (3 functions touched):

1. **`_detect_project_markers`** (`cli.py:3545-3550`): capture `cp.stdout.strip().splitlines()` as `dirty_files: list[str]`; set `out["dirty"] = bool(dirty_files)`. Drops nothing — same subprocess cost; one extra split + one extra key.
2. **`_summarize_workspace_status`** (`cli.py:2892-2919`): when `R1: uncommitted work` is added to `reasons`, also copy `dirty_files` from the project dict onto the `needs_attention` entry.
3. **`workspace_dashboard_cmd`** (`cli.py:3062-3090`): unchanged at the call site — the `needs_attention` list now carries `dirty_files` automatically.

Render plumbing:

4. **`dashboard.py`**: add `render_r1_detail(needs_attention: list[dict[str, Any]]) -> Table | None` mirroring the `render_archived` shape — returns `None` when no R1 triggered. In `render_dashboard` (L606-645), append Section E between Section B (L638) and Section C (L641) when Section E is non-None. New footer line in `render_footer` pointing to "R1: see Section E".

Why B over alternatives:

- **B vs A (new column)**: bloats Section B by 1 column on every run; only R1 projects have content; most projects show empty cells.
- **B vs C (inline R1 cell content)**: breaks the per-row color coding; cells become multi-line, breaking the table grid.
- **B vs D (`--detail` flag)**: adds a flag; conflicts with the "read-only, on-demand, single-identity" MVP; defers to a future Phase 5.2 surface.

The new section is **conditional** — only renders when at least one project has `dirty_files` non-empty. The dashboard stays minimal when no R1 is triggered.

LOC estimate: ~30 src + ~50 tests = **~80 LOC**.

### 4.4 Total LOC forecast (strict TDD ×6 multiplier)

| Point | Src LOC | Test LOC | Total raw | ×6 multiplier | Notes |
|-------|---------|----------|-----------|---------------|-------|
| Encoding/width | 15 | 30 | 45 | 270 | Console reconfigure is best-effort OSError-swallow (Pattern #551) |
| Dot-prefix filter | 10 | 20 | 30 | 180 | Single helper + 2 call sites + RED tests on both surfaces |
| R1 detail | 30 | 50 | 80 | 480 | 3 functions threaded + new render + tests + snapshot |
| **Total** | **55** | **100** | **155** | **~930** | Single-PR realistic = ~930 LOC, > 400-line budget → **chained PR required** |

**Scope realism (single PR)**: 155 raw LOC × ~2 (real TDD multiplier on a small change is closer to 3-4× for tests + ~1.5× for fixture/import code) ≈ **400-700 LOC realistic**. The `apply-under-strict-tdd-grows-5-6x-beyond-forecast` precedent (per `openspec/config.yaml:127` "PR split: ≤400-line budget per work-unit commit; chained PR for >400 LOC") suggests **930+ LOC with the conservative ×6 estimate**.

**PR strategy recommendation** (forwarded to sdd-tasks for confirmation):

- **Single PR** is achievable IF the chained PR guard allows ~700-800 LOC (the "realistic" forecast), because 3 small concerns fit one work-unit commit.
- **Chained PR** is the safer forecast given strict TDD ×6: 
  - **PR1** — encoding/width + dot-prefix filter (the two cosmetic/scan fixes; 75 raw + ~450 multipled = 1 work-unit commit; shared scan-filter helper + Console reconfigure + table column widths)
  - **PR2** — R1 detail (the 80 raw + ~480 multipled = 1 work-unit commit; data plumbing + new Section E + footer pointer)
- The guard will catch this at `sdd-tasks` time per `openspec/config.yaml:128`.

LOC final estimate: **155 raw / ~930 with ×6 / ~700 realistic forecast**. PR strategy to be confirmed at sdd-tasks.

---

## 5. REQ Alignment

### 5.1 Does each point need a NEW REQ, or do existing REQs cover it?

| Point | Existing REQ | Need NEW REQ? | Rationale |
|-------|--------------|---------------|-----------|
| Encoding/width | `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH` (existing) — covers Rich rendering; does NOT specify column widths or encoding | **EXTEND** the existing REQ — add a §4.1 "Output integrity" sub-clause covering terminal-safe encoding + column-width management | The fix is within the spirit of "renders Rich" but adds a new constraint (terminal-safe encoding). An extension is cleaner than a new top-level REQ. |
| Dot-prefix scan | `REQ-WORKSPACE-PROJECT-IDENTITY` (existing) — defines the 11 static metadata fields | **NEW sub-clause under REQ-WORKSPACE-PROJECT-IDENTITY** — "projects are immediate subdirectories of the projects root, EXCLUDING dot-prefix entries (tooling/config)" | This is a scope-narrowing addition to project identity, not a new capability. |
| R1 detail | `REQ-WORKSPACE-DASHBOARD-CONSUMES-DS2` (existing) — defines the DS2 envelope shape | **NEW root REQ**: `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` (mirrors `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH`) — declares that R1 cells expose dirty files via Section E | The R1 detail is a NEW capability surface (a new section), so a new root REQ is justified. |

### 5.2 REQ list to touch (delta spec for `openspec/changes/workspace-dashboard-usability-pass/specs/workspace-dashboard/spec.md`)

- **EXTEND** `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH` with sub-clause: "The dashboard MUST render correctly on terminals using cp1252 or UTF-8 encoding; long project names MUST wrap (not truncate) within their column bounds; the `…` Unicode ellipsis MUST NOT appear in dashboard output."
- **MODIFY** `REQ-WORKSPACE-PROJECT-IDENTITY` with sub-clause: "The list of projects enumerated by `flow projects ls` is the set of immediate subdirectories of the projects root EXCLUDING any entry whose name starts with `.` (dot). Dot-prefix entries are tooling/config and never user projects."
- **ADD** `REQ-WORKSPACE-DASHBOARD-R1-DETAIL`: "When at least one project has `R1: uncommitted work` triggered, the dashboard MUST render a Section E listing, per R1-triggered project, the list of dirty file paths as reported by `git status --porcelain`."

### 5.3 Root spec (`openspec/specs/workspace/spec.md`) impact

Per `§8 Family-shape protocol` (L374): *"When a delta REQ is updated (or a new delta is added), the corresponding root REQ summary should be reviewed for drift."* The `workspace-dashboard-section-cleanup` precedent (changes 1-2) explicitly **deferred** doc-level cleanup to follow-ups; this change should NOT modify `workspace/spec.md` directly. The drift (if any) is tracked for the next `workspace-spec-section-cleanup-*` cycle.

---

## 6. Dependencies (shared infrastructure between the 3 points)

### 6.1 What the 3 points share

| Concern | Shared across |
|---------|---------------|
| **Console encoding + width** (Point 1) | Used by `workspace_dashboard_cmd` L3089; the encoding/wrap change benefits **all dashboard sections** A/B/C/D. |
| **Subdir iteration filter** (Point 2) | Used by `workspace_status` L3017 + `projects_ls` L3628 + (potentially) `where.py:461` (where module scans subdirectories — out of scope but audit-worthy). Extracting `_iter_project_subdirs` keeps the 2 scan sites DRY. |
| **`needs_attention` entry shape** (Point 3) | Built by `_summarize_workspace_status`; consumed by `workspace_dashboard_cmd`; rendered by `render_needs_table` + new `render_r1_detail`. Adding `dirty_files` to the entry is a single-source-of-truth propagation through the existing data flow. |
| **`_detect_project_markers` output shape** (Points 2 + 3) | Adding `dirty_files` to the dict is one-line at L3548; consumed by `_summarize_workspace_status` for the propagation. |

### 6.2 Shared builder candidate

A **`build_needs_by_name(needs_attention)` helper** is already inline at `cli.py:3080-3085` (per `workspace-dashboard-section-cleanup` design D3 + sort-projects follow-up). The user's locked scope says **NO extract** (the inline pattern is intentional — single caller today). Per Article IV: 2+ concrete cases justify extraction; here we have 1 concrete case. **Out of scope** for THIS change. Document as deferred (per the sort-projects design note carry-forward pattern).

A **`_iter_project_subdirs(root)` helper** is a NEW extraction justified by 2 concrete cases (workspace_status + projects_ls). **In scope** for Point 2.

---

## 7. Risks (per point)

### 7.1 Encoding/width

| Risk | Severity | Mitigation |
|------|----------|------------|
| `sys.stdout.reconfigure(encoding='utf-8')` fails on Windows legacy terminal | LOW | Wrap in `try/except OSError`; fall back to current behavior; **defensive default** (Pattern #551) |
| `Console(width=N)` override breaks the auto-detect | LOW | Use terminal detection first; only override when auto-detect returns `None` or 0; OR use Rich's `Console().size` introspection |
| `OverflowMethod.fold` produces multi-line rows that confuse the per-row color coding | LOW | Rich applies the row style to all cells of the row; color still applies; test confirms (the per-row `style=row_style` at L509 covers all cells) |
| Existing dashboard snapshot tests (no `_render_text` width assertion) miss the regression | MEDIUM | Add explicit width-bound tests (e.g., `Console(width=40, ...)`, assert no `` chars in output) |
| `_format_rule_cell` markup (`[red]R1[/red]`) conflicts with `OverflowMethod.fold` line wrapping | LOW | Rich handles per-line markup correctly; tested via `rich.table` source |

### 7.2 Dot-prefix scan filter

| Risk | Severity | Mitigation |
|------|----------|------------|
| A user actually has a dot-prefix project they care about (e.g., `.config`) | LOW | All 3 retrospective cycles (Phase 5 + 2 follow-ups) confirm no real dot-prefix project exists in `C:\dev\proyects\`; tooling directories dominate the dot-prefix space |
| `_iter_project_subdirs` shadowed by future extension (`_iter_*`) | NEGLIGIBLE | Naming follows `_resolve_projects_root` precedent (private helper, no `__all__` entry) |
| Test fixture leaks `.` from `tmp_path`'s parent dir | LOW | Tests use `tmp_path` directly, no globbing outside it; `_iter_project_subdirs(tmp_path)` is hermetic |
| `flow where` cross-project search depends on the full subdir list (does it filter dot-prefix?) | MEDIUM | Audit `where.py:461` separately; **out of scope** for THIS change per locked scope; flagged for a future `flow-where-followup` if the audit finds a discrepancy |
| `_detect_project_markers` is called from `workspace fix` validation paths — does the dot-prefix filter affect R2 no-git remediation? | LOW | R2 remediates "no git" — the project must already be in the list to be remediated. If a user runs `flow workspace fix .atl --yes`, the fix would still work IF `.atl` is a real project; the new filter excludes it from the dashboard view but does NOT delete the dir. Note in changelog. |

### 7.3 R1 detail

| Risk | Severity | Mitigation |
|------|----------|------------|
| `git status --porcelain` output is unbounded (very dirty project = hundreds of files) | LOW | Cap at 20 files per project; truncate with ASCII `...` ellipsis; add a footer hint "run `git status` for full list" |
| Adding `dirty_files` to the DS1 + DS2 envelope breaks downstream consumers (Engram, Graphify) that pin the v1 schema | MEDIUM | Schema versioning: DS1 + DS2 envelopes already declare `"version": "1"`; adding a key is **additive** (consumers ignore unknown keys). Document in changelog. |
| New Section E bloats output on repos with many dirty projects | LOW | Cap dirty file count per project (20); cap total Section E height (e.g., 50 rows); use `OverflowMethod.fold` for long file lists |
| `_detect_project_markers` now mutates a project dict in-place when called from outside the dashboard path (e.g., from `workspace_status` text mode) | LOW | Function returns a new dict (L3528); no mutation risk. Verify via test. |
| `_git("status", "--porcelain", ...)` exit code is non-zero on a non-git dir — but `_detect_project_markers` only runs this when `has_git=True` (L3538). Edge case: a directory with a stale/corrupt `.git/` dir | LOW | Existing `_git` try/except (L3549) swallows the failure; `dirty` defaults to `None` (L3536). New `dirty_files` defaults to `[]` (defensive). |

### 7.4 Cross-point risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Single PR exceeds 400-line budget at ×6 multiplier | HIGH (per orchestrator prompt) | **Forecast 930+ LOC** at ×6; sdd-tasks will trigger chained PR recommendation; split per §4.4 PR strategy |
| Combined PR hides 3 distinct changes (reviewer can't reason about each independently) | MEDIUM | Apply in sub-batches A/B/C within the work-unit commit; commit message cites each batch |
| Three changes in one change folder = 3 separate features in one PR | LOW | The change IS one "usability pass" — the 3 points share the locked scope; pattern matches `phase-5-dashboard` (3 PRs in one change) |

---

## 8. Forecast

| Metric | Estimate | Notes |
|--------|----------|-------|
| Total raw LOC (src + tests) | ~155 | §4.4 sum |
| Total ×6 multiplier LOC | ~930 | Conservative strict-TDD per `apply-under-strict-tdd-grows-5-6x-beyond-forecast` |
| Total realistic forecast | ~700 | Mid-range estimate; actual will be confirmed at sdd-tasks |
| Files affected (in-scope) | 5 — `src/flow_engineering/dashboard.py` + `src/flow_engineering/cli.py` + 3 test files | Per §2.1 |
| Files potentially affected (audit) | 2 — `src/flow_engineering/project_detector.py` + `src/flow_engineering/workspace_hygiene.py` | Read-only audit; expect NO change |
| Files unaffected (locked) | All PR1/PR2/PR3 + sort-projects + 3 prior follow-up commits | Per Pattern #548 |
| New runtime deps | 0 | `rich` already transitive |
| Single PR | Maybe | Depends on actual ×6 multiplier reality; sdd-tasks will forecast |
| Chained PR | Likely | Recommended split: PR1 = encoding/width + dot-prefix; PR2 = R1 detail |
| Size exception | No | Per Constitution Article VII, chained PR is the preferred mechanism |
| 400-line budget risk | Medium-High | Forecast 700-930 LOC; 400-line PR budget → chained PR |
| Wall-clock (full cycle, single PR) | ~85 min | explore 12 [this doc] + propose 10 + spec 12 + design 10 + tasks 8 + apply 25 + verify 6 + archive 2 |
| Wall-clock (full cycle, chained 2 PR) | ~120 min | + extra 15 min for chained-PR ceremony |

---

## 9. Open Questions

1. **`Console.width` default**: should we use `Console().size.width` (auto-detect) or set an explicit `Console(width=120, soft_wrap=True)`? Auto-detect is friendlier to narrow terminals but adds variance to snapshot tests.
   - Recommendation: **explicit `width=120` default + best-effort auto-detect override** (mimics the test pattern at `test_dashboard.py:87`).
   - Confirmed at design phase.

2. **Dot-prefix filter — should it apply to `flow where` cross-project search too?** Out of scope per locked scope; audit shows `where.py:461` (`for entry in sorted(root.iterdir()):`) does NOT filter dot-prefix either. The user prompt locks the dashboard surface only.
   - Recommendation: **flag for `flow-where-followup` audit** in the change's explore notes; do NOT modify `where.py` in this change.

3. **R1 detail — should the footer hint change to point to Section E specifically, or stay generic?**
   - Current footer (L597-600): *"Tip: Run `flow workspace status --json` for JSON output."* + *"Tip: Run `flow workspace fix <project> --yes --backup` to remediate."*
   - Recommendation: **add a 3rd footer line** (or amend the JSON output tip) to mention Section E. Confirm at design phase.

4. **Encoding reconfigure on Linux/macOS**: `sys.stdout.reconfigure(encoding='utf-8')` works on all 3 platforms (Python 3.7+) but the test fixture `Console(file=io.StringIO(), ...)` at `test_dashboard.py:91` should remain unchanged. Confirm no regression.

5. **Should `_detect_project_markers` capture `dirty_files` ONLY when dirty=True, or always (even when empty)?** Always (empty list when clean). Cheaper to consume downstream (`if dirty_files:` check is more obvious than `if project.get("dirty_files"):`).

6. **Should the new Section E live in `render_dashboard` or as a separate top-level renderable the Click handler appends?**
   - Recommendation: **in `render_dashboard`** to keep the composer responsibility (mirrors how Section C is appended conditionally).

---

## 10. Ready for Proposal

**YES** — the orchestrator should launch `sdd-propose` next with these inputs:

- **Change name**: `workspace-dashboard-usability-pass`
- **Goal**: 3 small usability fixes to the existing read-only Rich dashboard (encoding/width, dot-prefix scan filter, R1 detail)
- **Builds on**: `2026-06-30-phase-5-dashboard` + `2026-06-30-workspace-dashboard-section-cleanup` + `2026-06-30-sort-projects-align-with-real-ds-data-flow` + `2026-06-30-workspace-spec-section-cleanup-2`
- **Approach (locked)**:
  - Encoding/width: Console reconfigure (utf-8, best-effort) + explicit width + per-column widths + `OverflowMethod.fold`
  - Dot-prefix filter: shared `_iter_project_subdirs` helper + filter at 2 scan sites
  - R1 detail: capture `git status --porcelain` in `_detect_project_markers` + thread `dirty_files` through DS1/DS2 + new `render_r1_detail` Section E
- **Scope (locked)**: 5 files modified (dashboard.py, cli.py, 3 test files). No new commands. No new flags. No mutations. No doc changes.
- **Forecast**: 155 raw / ~700 realistic / ~930 ×6 LOC. Chained PR likely required (sdd-tasks to confirm).
- **REQ alignment**:
  - EXTEND `REQ-WORKSPACE-DASHBOARD-RENDERS-RICH` (encoding/width)
  - MODIFY `REQ-WORKSPACE-PROJECT-IDENTITY` sub-clause (dot-prefix filter)
  - ADD `REQ-WORKSPACE-DASHBOARD-R1-DETAIL` (R1 detail)
- **Hard constraints honored**: dashboard stays read-only; no new flags; no mutations; no `stash`-triggering words; no AI attribution; no touch of `v1.1-followups/`; no modifications to PR1/PR2/PR3/sort-projects/3-prior-followups.

---

## 11. References

### 11.1 Source artifacts read

- `openspec/changes/archive/2026-06-30-phase-5-dashboard/specs/workspace-dashboard/spec.md` — canonical Phase 5 REQs (185 lines)
- `openspec/changes/archive/2026-06-30-workspace-dashboard-section-cleanup/proposal.md` — 4-text-edit precedent (229 lines)
- `openspec/changes/archive/2026-06-30-sort-projects-align-with-real-ds-data-flow/proposal.md` — `sort_projects` refactor precedent (185 lines)
- `openspec/changes/archive/2026-06-30-workspace-spec-section-cleanup-2/proposal.md` — 3-stale-prose-text precedent (135 lines)
- `openspec/specs/workspace/spec.md` — current root capability (377 lines, includes `REQ-WORKSPACE-DASHBOARD-*` family)
- `openspec/config.yaml` — strict-TDD ×6 multiplier + 400-line PR budget + chained-PR rules

### 11.2 Source code read

- `src/flow_engineering/dashboard.py` (663 lines) — full file
  - `render_needs_table` at L444-518
  - `_truncate_path` at L423-436 (already ASCII-safe)
  - `render_archived` at L535-576
  - `render_dashboard` composer at L606-645
- `src/flow_engineering/cli.py` (5065 lines, targeted sections)
  - `workspace_dashboard_cmd` at L3040-3090
  - `_summarize_workspace_status` at L2878-2923
  - `_workspace_status_envelope` at L2926-2938
  - `_detect_project_markers` at L3517-3578 (dirty detection at L3545-3550)
  - `_workspace_status` at L2996-3032 (scan site at L3017)
  - `projects_ls` at L3581-3666 (scan site at L3628)
  - `_resolve_projects_root` at L84-93
- `src/flow_engineering/workspace_hygiene.py` (586 lines, targeted)
  - `HIDDEN_SYSTEM_FILES` at L124 — confirms scope of "hidden" (only `.DS_Store`/`Thumbs.db`/`desktop.ini`)
- `tests/unit/test_dashboard.py` (783 lines) — existing dashboard tests
- `tests/unit/test_cli_dashboard.py` (296 lines) — `_make_project` helper at L37-49, T12.1-T12.5 tests
- `tests/unit/_workspace_fixtures.py` (59 lines) — `make_project` etc.

### 11.3 Verification scripts run (cleaned up after)

- `Console(no_color=True, soft_wrap=False)` with non-ASCII chars → confirmed `Gestor-de-Contraseñas` renders as `Gestor-de-Contra` (cp1252) or `Gestor-de-Contrase` (default `width=80`).
- `Console(width=40, ...)` with long names → confirmed truncation with `…` → `` in cp1252 output.
- Existing 38 dashboard tests pass (`uv run pytest tests/unit/test_dashboard.py tests/unit/test_cli_dashboard.py` → 38 passed in 0.75s).

### 11.4 Patterns cited

- Pattern #538 — *"one identity per command"* — already honored (no `--json` on dashboard; new fix doesn't add `--detail` either)
- Pattern #548 — *"Don't touch green commits for aesthetic reasons"* — PR1/PR2/PR3/sort-projects LOCKED
- Pattern #551 — *"Guards as instruments"* — defensive defaults for encoding reconfigure
- Pattern #555 — *"Solo el primero ahora, no mezclemos los dos"* — one usability-pass change, not three separate ones
- Pattern #605 (post-merge evaluation) — defer `workspace/spec.md` L299 trigger-row edit to a follow-up cycle

---

*Generated by the sdd-explore executor for `workspace-dashboard-usability-pass`. Persists to `openspec/changes/workspace-dashboard-usability-pass/explore.md` (this file) and mirrors to Engram via `mem_save` with `topic_key: "sdd/workspace-dashboard-usability-pass/explore"`, `type: "architecture"`, `project: flow-engineering`, `capture_prompt: false`.*

