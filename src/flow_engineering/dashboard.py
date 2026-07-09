"""Dashboard data layer for ``flow workspace dashboard`` (Phase 5).

PR1 scope: subprocess wrappers + fetchers ONLY.

  - ``_run_subprocess_json`` — generic subprocess → JSON wrapper
  - ``fetch_project_list`` — DS1: ``flow projects ls --json``
  - ``fetch_status_summary`` — DS2: ``flow workspace status --json``
  - ``fetch_archived_projects`` — DS5: direct ``load_registry()`` read

Out of scope here (PR2 / PR3 territory):

  - filter / sort / color logic (PR2)
  - Rich rendering — Panel / Table / Group (PR2)
  - Click integration — ``flow workspace dashboard`` subcommand (PR3)

Pattern #536: observability first, interactivity second. The dashboard never
mutates state; the registry is read-only here and the only writers remain
``flow workspace {fix, archive, restore}`` (Phase 4 mutation gates preserved).

Pattern #538: one identity per command. ``flow workspace status`` keeps the
machine-readable identity (``--json``); the new ``flow workspace dashboard``
subcommand is the human-facing counterpart and deliberately omits ``--json``.
"""

from __future__ import annotations

import json
import subprocess
import warnings
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from flow_engineering.registry import load_registry

# Per-column overflow mode. ``rich.console.OverflowMethod`` is a
# ``typing.Literal`` in this Rich version (14.x), so we use the string
# literals directly to keep mypy strict-mode happy. ``"fold"`` wraps
# long content onto multiple lines; ``"crop"`` truncates without an
# ellipsis. The Unicode U+2026 single-char ellipsis (the cp1252 bug
# source) is emitted by ``"ellipsis"`` — FORBIDDEN in dashboard output.
_OVERFLOW_FOLD: Literal["fold", "crop", "ellipsis", "ignore"] = "fold"
_OVERFLOW_CROP: Literal["fold", "crop", "ellipsis", "ignore"] = "crop"

# ---------- Public exception types ----------
#
# One error class per failure mode, mirroring the ``RegistryError`` precedent
# (``src/flow_engineering/registry.py:96``). The Click layer (PR3) will catch
# these uniformly and print ``str(exc)`` to stderr before ``SystemExit(1)``.


class DashboardSubprocessError(RuntimeError):
    """Raised when the DS1/DS2 subprocess exits with non-zero status."""


class DashboardParseError(ValueError):
    """Raised when the DS1/DS2 subprocess output is not valid JSON."""


class DashboardFlowNotFoundError(FileNotFoundError):
    """Raised when the ``flow`` binary is not found on PATH.

    Subclasses ``FileNotFoundError`` so callers that already catch the OS
    exception still see the dashboard-specific context (the message explains
    that ``flow`` is missing, not some downstream file).
    """


# ---------- Subprocess transport ----------


def _run_subprocess_json(cmd: list[str], *, timeout: int = 10) -> dict[str, Any]:
    """Run ``cmd`` and return its stdout parsed as JSON.

    Mirrors the ``where.py:89`` ``_run_search`` shape but fails LOUD instead
    of open: every error mode produces a specific exception so the dashboard
    can never render an incomplete view. The CLI layer (PR3) is responsible
    for converting these to operator-friendly messages.

    Args:
        cmd: Command and arguments to run. ``cmd[0]`` is the binary name
            (typically ``"flow"``); kept keyword-only so test fakes stay
            honest about what they receive.
        timeout: Subprocess timeout in seconds. Defaults to 10s — long
            enough for typical ``flow`` invocations, short enough to avoid
            hanging the operator's terminal.

    Returns:
        Parsed JSON object (``dict``). Empty stdout parses to ``{}`` only
        if it is literally ``"{}"``; an empty string raises
        :class:`DashboardParseError` (a defensive default — empty output
        is never valid for DS1/DS2).

    Raises:
        DashboardFlowNotFoundError: ``cmd[0]`` not on PATH.
        DashboardSubprocessError: Returncode != 0 OR ``TimeoutExpired``.
        DashboardParseError: stdout is not parseable JSON.
    """
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DashboardFlowNotFoundError(
            f"`{cmd[0]}` binary not found on PATH. "
            f"Install flow-engineering or activate the venv that provides it."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DashboardSubprocessError(f"`{' '.join(cmd)}` timed out after {timeout}s") from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise DashboardSubprocessError(
            f"`{' '.join(cmd)}` exited with code {completed.returncode}: {stderr}"
        )

    try:
        payload: Any = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        preview = (completed.stdout or "")[:200]
        raise DashboardParseError(
            f"`{' '.join(cmd)}` returned invalid JSON: {exc}. stdout preview: {preview!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise DashboardParseError(
            f"`{' '.join(cmd)}` returned JSON but the top-level value is "
            f"{type(payload).__name__}, not a dict."
        )
    return payload


# ---------- DS1 / DS2 / DS5 fetchers ----------


def fetch_project_list(*, flow_bin: str = "flow") -> list[dict[str, Any]]:
    """Fetch the project list via ``flow projects ls --json`` (DS1).

    Returns the envelope's ``projects[]`` field as a list of dicts. The
    envelope's other top-level fields (``version``, ``root``) are discarded
    by design — the dashboard's data layer trusts the v1 contract and
    doesn't re-validate it on every render.
    """
    payload = _run_subprocess_json([flow_bin, "projects", "ls", "--json"])
    projects = payload.get("projects", [])
    return [p for p in projects if isinstance(p, dict)]


def fetch_status_summary(*, flow_bin: str = "flow") -> dict[str, Any]:
    """Fetch the workspace status envelope via ``flow workspace status --json`` (DS2).

    Returns the parsed envelope (totals + projects + needs_attention). The
    dashboard renders the totals as the header and the needs_attention list
    drives the per-row color coding.
    """
    return _run_subprocess_json([flow_bin, "workspace", "status", "--json"])


def fetch_archived_projects() -> list[dict[str, Any]]:
    """Fetch archived projects from the registry (DS5 direct read).

    Reads ``~/.flow-engineering/registry.json`` via ``load_registry()``. The
    dashboard never calls ``save_registry_atomic`` — the registry is a
    read-only data source here; mutation stays in
    ``flow workspace {fix, archive, restore}``.

    Returns:
        List of ``ArchivedEntry``-shaped dicts (JSON-serializable — Path
        fields are POSIX strings via ``model_dump(mode="json")``). Empty
        list when the registry is missing (first-run UX) or has no
        archived entries.
    """
    registry = load_registry()
    return [entry.model_dump(mode="json") for entry in registry.archived]


# ---------- Logic (pure functions) ----------
#
# PR2 scope (Wave 3+4): filter + sort + color. PR3 (out of scope here)
# wires these into the Click handler. Pure functions keep the tests cheap
# — no fixtures, no mocks, no Click plumbing — and the same predicates are
# reused by the Rich renderers.


_VALID_RULES: frozenset[str] = frozenset({"R1", "R2", "R3", "R4", "R5"})


def filter_by_rules(
    projects: list[dict[str, Any]],
    needs_attention: list[dict[str, Any]],
    rules: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter projects (and their needs_attention entries) by rule names.

    Implements ``--filter RULES`` for the ``flow workspace dashboard`` Click
    command (PR3). A project is KEPT if its ``needs_attention`` entry has at
    least one matching rule in its ``reasons[]`` field — the matching logic is
    union across rules (the more rules supplied, the broader the filter).

    Valid rule names (matching REQ-DASHBOARD-RENDERING):

      - ``R1`` dirty — uncommitted working-tree changes
      - ``R2`` no_git — not a git repository
      - ``R3`` no_tests — no test directory
      - ``R4`` no_openspec — missing openspec/ subdirectory
      - ``R5`` no_graphify — missing graphify/ artifact

    Args:
        projects: Project list (typically from ``fetch_project_list``).
        needs_attention: Needs-attention list from the DS2 status envelope.
        rules: Rule names to filter by. May be empty (returns inputs
            unchanged for symmetry with the Click default ``tuple()``).

    Returns:
        Tuple of ``(filtered_projects, filtered_needs_attention)``. Both
        lists are filtered in lock-step — a project is omitted iff its
        needs_attention entry is omitted.

    Raises:
        ValueError: ``rules`` contains an unknown rule name (anything other
            than ``R1``..``R5``).
    """
    unknown = [r for r in rules if r not in _VALID_RULES]
    if unknown:
        valid_list = ", ".join(sorted(_VALID_RULES))
        raise ValueError(
            f"Unknown filter rule(s): {', '.join(unknown)}. Valid rules: {valid_list}."
        )

    if not rules:
        return list(projects), list(needs_attention)

    rule_set = {f"{r}:" for r in rules}
    matched_needs: list[dict[str, Any]] = []
    matched_names: set[str] = set()
    for entry in needs_attention:
        reasons = entry.get("reasons", [])
        if any(any(reason.startswith(prefix) for prefix in rule_set) for reason in reasons):
            matched_needs.append(entry)
            name = entry.get("name")
            if isinstance(name, str):
                matched_names.add(name)

    matched_projects = [p for p in projects if p.get("name") in matched_names]
    return matched_projects, matched_needs


_VALID_SORT_FIELDS: frozenset[str] = frozenset({"name", "path", "needs-count"})


def sort_projects(
    projects: list[dict[str, Any]],
    field: str,
    *,
    needs_by_name: Mapping[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Return ``projects`` sorted by ``field``.

    Implements ``--sort FIELD`` for the ``flow workspace dashboard`` Click
    command (PR3). Valid fields:

      - ``name`` (default) — alphabetical ascending by ``name``.
      - ``path`` — alphabetical ascending by ``path``.
      - ``needs-count`` — descending by needs-count (noisiest first). The
        count source is the optional ``needs_by_name`` keyword map (keyed by
        project ``name``); when ``None``, the function falls back to reading
        ``project["reasons"]`` and emits a ``DeprecationWarning`` so stale
        callers can surface.

    Args:
        projects: Project list to sort. Returns a NEW list — the input is
            not mutated (operators may still reference it after the call).
        field: Sort key. Case-insensitive in practice (the Click option
            normalizes via ``case_sensitive=False`` in PR3); this function
            does the literal lookup as specified.
        needs_by_name: Optional name-keyed map of reasons (typically built
            from ``status_envelope["needs_attention"]`` by the caller).
            Required for an accurate ``field="needs-count"`` sort. If
            ``None`` and ``field == "needs-count"``, the function falls
            back to ``project.get("reasons", [])`` and emits a
            ``DeprecationWarning`` — this fallback will be removed in
            v1.3.0 (see REQ-DASHBOARD-SORT-DATA-FLOW + design §8).

    Returns:
        A new sorted list. The input list is not mutated.

    Raises:
        ValueError: ``field`` is not one of the valid sort keys.
    """
    if field not in _VALID_SORT_FIELDS:
        valid_list = ", ".join(sorted(_VALID_SORT_FIELDS))
        raise ValueError(f"Unknown sort field: {field!r}. Valid fields: {valid_list}.")

    if field == "name":
        return sorted(projects, key=lambda p: p.get("name", ""))
    if field == "path":
        return sorted(projects, key=lambda p: p.get("path", ""))

    # field == "needs-count"
    def needs_count(p: dict[str, Any]) -> int:
        if needs_by_name is not None:
            reasons = needs_by_name.get(p.get("name", ""), [])
            return len(reasons) if isinstance(reasons, list) else 0
        # Deprecated fallback path — remove in v1.3.0 once all callers
        # have been migrated to pass ``needs_by_name`` explicitly.
        warnings.warn(
            "sort_projects: needs_by_name=None is deprecated; pass it "
            "derived from DS2 needs_attention list. Remove the fallback "
            "in the next follow-up.",
            DeprecationWarning,
            stacklevel=2,
        )
        reasons = p.get("reasons", [])
        return len(reasons) if isinstance(reasons, list) else 0

    return sorted(projects, key=needs_count, reverse=True)


# Color threshold constants — exported as named constants so the audit log
# shows intent (e.g. "the dashboard turns red at 3+ needs") rather than
# scattering magic numbers across render_* functions.
_RED_THRESHOLD: int = 3
_YELLOW_LOWER: int = 1
_YELLOW_UPPER: int = 2


def color_code(needs_count: int) -> str:
    """Map a needs-count to a Rich color name.

    Implements the color threshold rule from REQ-DASHBOARD-RENDERING:

      - ``>= 3`` → ``"red"``     (operator must act now)
      - ``1..=2`` → ``"yellow"``  (operator should review)
      - ``0``    → ``"green"``   (clean)

    Args:
        needs_count: Number of unmet needs (typically ``len(reasons)``).
            Negative values are treated as 0 (defensive default — never
            red/yellow for nonsense input; the caller is responsible for
            the integer contract).

    Returns:
        The Rich color name as a plain string (``"red"``, ``"yellow"``, or
        ``"green"``). Returning the name (not a Rich ``Color`` object)
        keeps this function pure and import-cheap — the renderers resolve
        the name via Rich's standard color API.
    """
    if needs_count >= _RED_THRESHOLD:
        return "red"
    if _YELLOW_LOWER <= needs_count <= _YELLOW_UPPER:
        return "yellow"
    return "green"


# ---------- Rich rendering (Section A — Header Panel) ----------


def _format_timestamp() -> str:
    """UTC timestamp at second precision for the dashboard header.

    Snapshot-friendly: ``datetime.now(timezone.utc)`` with ``timespec="seconds"``
    yields a byte-stable ISO 8601 string (no microseconds, no local TZ).
    """
    return datetime.now(UTC).isoformat(timespec="seconds")


def render_header(summary: dict[str, Any], *, no_color: bool = False) -> Panel:
    """Render Section A: a Panel summarising workspace totals + per-rule counts.

    Implements design §4.1 — workspace totals, per-rule breakdown, ISO timestamp.
    Border style is cyan when color is enabled; otherwise plain (Rich's default
    for ``no_color=True``).

    Args:
        summary: The DS2 status envelope (or a partial one — the function
            tolerates missing keys by rendering zeros).
        no_color: When ``True``, the panel renders without ANSI color codes
            (CI / piping). When ``False`` (default), cyan border.

    Returns:
        A Rich ``Panel`` (not yet printed — the caller renders via a
        ``Console``). Operators see: workspace project count, archived
        count, needs-attention total, per-rule breakdown, run timestamp.
    """
    totals = summary.get("totals", {}) if isinstance(summary.get("totals"), dict) else {}
    archived_count = summary.get("archived_count", 0)

    projects_total = totals.get("projects", 0)
    needs_total = totals.get("needs_attention", 0)
    dirty = totals.get("dirty", 0)
    no_git = totals.get("no_git", 0)
    no_tests = totals.get("no_tests", 0)

    body_lines = [
        f"[bold]Workspace[/bold] {projects_total} projects, {archived_count} archived",
        f"Needs attention: {needs_total} (R1: {dirty}, R2: {no_git}, R3: {no_tests})",
        f"Run: {_format_timestamp()}",
    ]
    content = "\n".join(body_lines)
    border_style: str = "none" if no_color else "cyan"
    return Panel(
        content,
        title="flow workspace dashboard",
        border_style=border_style,
    )


# ---------- Rich rendering (Section B — Needs-Attention Table) ----------


_NEEDS_RULE_COLUMNS: tuple[str, ...] = ("R1", "R2", "R3", "R4", "R5")
_NEEDS_COLUMN_HEADERS: tuple[str, ...] = ("project", "path") + _NEEDS_RULE_COLUMNS + ("total",)
_PATH_TRUNCATE_LEN: int = 60


def _truncate_path(path: str, max_len: int = _PATH_TRUNCATE_LEN) -> str:
    """Ellipsize a path for narrow terminals.

    Mirrors the design §4.2 spec: 60 chars max, middle ellipsis. Pure
    function — never touches the filesystem.
    """
    if len(path) <= max_len:
        return path
    if max_len <= 3:
        return path[:max_len]
    keep = max_len - 3
    front = keep // 2
    back = keep - front
    return f"{path[:front]}...{path[-back:]}"


def _format_rule_cell(triggered: bool, rule: str) -> str:
    """Render a per-rule cell: ``OK`` (clean) or ``R#`` (triggered)."""
    return f"[red]{rule}[/red]" if triggered else "[green]OK[/green]"


def render_needs_table(
    projects: list[dict[str, Any]],
    needs_attention: list[dict[str, Any]],
    *,
    no_color: bool = False,
) -> Table:
    """Render Section B: a Table with project × R1..R5 rows, color-coded.

    Implements design §4.2. Columns: ``project | path (truncated 60ch) |
    R1 | R2 | R3 | R4 | R5 | total``. Per-row style follows
    :func:`color_code`: ``red`` ≥3, ``yellow`` 1-2, ``green`` 0 (skipped
    when ``no_color=True``).

    Args:
        projects: Project list (typically from ``fetch_project_list``,
            possibly pre-filtered by :func:`filter_by_rules`).
        needs_attention: Needs-attention list (from DS2 / :func:`fetch_status_summary`,
            possibly pre-filtered). The function indexes by ``name``.
        no_color: When ``True``, no per-row color is applied (CI / piping).

    Returns:
        A Rich ``Table`` (not yet printed). Empty project list renders an
        empty table with the headers + footer row only — never raises.
    """
    # Index needs by project name for O(1) per-row lookup.
    needs_by_name: dict[str, dict[str, Any]] = {}
    for n in needs_attention:
        n_name = n.get("name")
        if isinstance(n_name, str):
            needs_by_name[n_name] = n

    table = Table(
        title="Needs attention",
        show_lines=False,
        header_style="bold" if not no_color else None,
    )
    # Per-column widths: ``name`` and ``path`` use ``fold`` (wrap onto
    # multiple lines) so long project names never collapse to the
    # Unicode U+2026 single-char ellipsis (the cp1252 bug source).
    # Rule columns and ``total`` use ``crop`` (truncate without ellipsis).
    _column_specs = (
        ("project", 12, 30, _OVERFLOW_FOLD),
        ("path", 30, 60, _OVERFLOW_FOLD),
        ("R1", 3, 5, _OVERFLOW_CROP),
        ("R2", 3, 5, _OVERFLOW_CROP),
        ("R3", 3, 5, _OVERFLOW_CROP),
        ("R4", 3, 5, _OVERFLOW_CROP),
        ("R5", 3, 5, _OVERFLOW_CROP),
        ("total", 3, 4, _OVERFLOW_CROP),
    )
    for header, min_w, max_w, overflow in _column_specs:
        table.add_column(header, min_width=min_w, max_width=max_w, overflow=overflow)

    rule_totals: dict[str, int] = dict.fromkeys(_NEEDS_RULE_COLUMNS, 0)

    for project in projects:
        name = project.get("name", "")
        path = _truncate_path(str(project.get("path", "")))
        entry = needs_by_name.get(name, {})
        reasons = entry.get("reasons", []) if isinstance(entry, dict) else []
        reasons_list: list[str] = reasons if isinstance(reasons, list) else []

        triggered_count = 0
        per_rule: list[str] = []
        for rule in _NEEDS_RULE_COLUMNS:
            triggered = any(isinstance(r, str) and r.startswith(rule) for r in reasons_list)
            per_rule.append(_format_rule_cell(triggered, rule))
            if triggered:
                rule_totals[rule] += 1
                triggered_count += 1

        row_style: str | None = color_code(triggered_count) if not no_color else None

        total_cell = str(len(reasons_list))
        table.add_row(str(name), path, *per_rule, total_cell, style=row_style)

    # Footer row — per-rule totals.
    footer_cells = ["[bold]total[/bold]", ""] + [
        f"[bold]{rule_totals[r]}[/bold]" for r in _NEEDS_RULE_COLUMNS
    ]
    table.add_row(*footer_cells)

    return table


# ---------- Rich rendering (Section C — Archived Projects Table) ----------


def _format_archived_at(iso: str) -> str:
    """Normalize an archived_at timestamp for stable rendering.

    The registry stores ISO 8601 strings; this helper keeps the snapshot
    rendering byte-stable by accepting whatever shape the registry emits
    and passing it through verbatim (defensive: never crashes on weird
    timestamps — the dashboard shows what it gets).
    """
    return iso if isinstance(iso, str) else str(iso)


def render_archived(archived: list[dict[str, Any]]) -> Table | None:
    """Render Section C: a Table of archived projects, or ``None`` when empty.

    Implements design §4.3. Columns: ``name | path | archived_at (ISO) | reason``.
    Default ``row_style="dim"`` to visually separate from the needs-attention
    section. ``--no-color`` does NOT affect this section (always dim —
    intentional per design §4.3 risk note).

    Args:
        archived: Archived project list (typically from
            :func:`fetch_archived_projects`).

    Returns:
        A Rich ``Table`` for non-empty input, or ``None`` when the list is
        empty (the caller — :func:`render_dashboard` — uses the ``None``
        sentinel to omit Section C from the composite output).
    """
    if not archived:
        return None

    table = Table(
        title="Archived projects",
        show_lines=False,
        header_style="bold",
    )
    # Per-column widths: keep the ISO ``archived_at`` timestamp intact at
    # narrow terminals (``max_width=25`` accommodates the 20-char ISO
    # string with 5 chars of headroom). ``name`` and ``path`` use ``fold``
    # so long entries wrap; ``reason`` also folds (free-form prose).
    _archived_column_specs = (
        ("name", 12, 30, _OVERFLOW_FOLD),
        ("path", 30, 60, _OVERFLOW_FOLD),
        ("archived_at", 19, 25, _OVERFLOW_CROP),
        ("reason", 20, 40, _OVERFLOW_FOLD),
    )
    for header, min_w, max_w, overflow in _archived_column_specs:
        table.add_column(header, min_width=min_w, max_width=max_w, overflow=overflow)

    for entry in archived:
        if not isinstance(entry, dict):
            continue
        table.add_row(
            str(entry.get("name", "")),
            str(entry.get("path", "")),
            _format_archived_at(entry.get("archived_at", "")),
            str(entry.get("reason", "")),
            style="dim",
        )

    return table


# ---------- Rich rendering (Section E — R1 dirty file detail) ----------


_R1_DETAIL_CAP = 20


def _truncate_dirty_files(files: list[str], cap: int = _R1_DETAIL_CAP) -> list[str]:
    """Cap a dirty-file list at ``cap`` entries, appending ASCII ``\"...\"`` when truncated.

    Anchors REQ-WORKSPACE-DASHBOARD-R1-DETAIL AC11 + design §7.2. The
    marker is ASCII 3-dot ``...`` (NEVER the Unicode U+2026 single-char
    ellipsis — that's the cp1252 bug source). Returns a NEW list (does
    not mutate the input).

    When ``len(files) <= cap``, the original list is returned as a copy
    (callers can mutate the result without side effects). When the
    cap is exceeded, the result has exactly ``cap`` entries: the first
    ``cap - 1`` files verbatim, plus the ASCII ``...`` marker.
    """
    if len(files) <= cap:
        return list(files)
    truncated = list(files[: cap - 1])
    truncated.append("...")
    return truncated


def render_r1_detail(needs_attention: list[dict[str, Any]]) -> Table | None:
    """Render Section E: per-R1-project dirty file list, capped at 20 per project.

    Returns ``None`` when no needs_attention entry has non-empty
    ``dirty_files`` — caller (``render_dashboard``) omits Section E in
    that case (mirrors how Section C is omitted when archived is empty).
    Implements design §7.1 + REQ-WORKSPACE-DASHBOARD-R1-DETAIL ACs 9/10/11/12.

    The table title includes a hint substring (``git status``) so the
    rendered output stays self-explanatory even when the footer is
    collapsed by narrow terminals.
    """
    r1_entries = [
        entry for entry in needs_attention if isinstance(entry, dict) and entry.get("dirty_files")
    ]
    if not r1_entries:
        return None

    table = Table(
        title="R1 dirty files (capped at 20 per project — run 'git status' for full list)",
        show_lines=False,
        header_style="bold",
    )
    _r1_column_specs = (
        ("project", 12, 30, _OVERFLOW_FOLD),
        ("dirty files", 20, 80, _OVERFLOW_FOLD),
    )
    for header, min_w, max_w, overflow in _r1_column_specs:
        table.add_column(header, min_width=min_w, max_width=max_w, overflow=overflow)

    for entry in r1_entries:
        files = entry.get("dirty_files") or []
        truncated = _truncate_dirty_files(files, cap=_R1_DETAIL_CAP)
        table.add_row(
            str(entry.get("name", "")),
            "\n".join(truncated),
            style="red",
        )

    return table


# ---------- Rich rendering (Section D — Footer Text) ----------


def render_footer() -> Text:
    """Render Section D: a Text with 3 tip pointers.

    Implements design §4.4 + §7.3 (the 3rd tip line is a PR2 add per
    REQ-WORKSPACE-DASHBOARD-R1-DETAIL). The tip wording is byte-stable
    (no timestamps), so snapshot tests can use exact-string matches for
    the verbatim substrings. The pointers guide operators to the right
    next-step:

      - ``flow workspace status --json`` → machine-readable status (Pattern #538).
      - ``flow workspace fix <project> --yes --backup`` → Phase 4 remediation
        command (preserved untouched per Pattern #536).
      - Section E + ``git status`` → dirty-file detail when R1 is triggered.

    Returns:
        A Rich ``Text`` (not yet printed). Markup uses ``[dim]`` for the
        ``Tip:`` prefix and ``[bold]`` for the commands.
    """
    return Text.from_markup(
        "[dim]Tip:[/dim] Run [bold]flow workspace status --json[/bold] for JSON output.\n"
        "[dim]Tip:[/dim] Run [bold]flow workspace fix <project> --yes --backup[/bold] to remediate.\n"
        "[dim]Tip:[/dim] When [red]R1[/red] is triggered, see Section E for dirty files "
        "(capped at 20 per project). Run [bold]git status[/bold] in the project for the full list."
    )


# ---------- Rich rendering (Composer — A + B + (C or None) + D) ----------


def render_dashboard(
    projects: list[dict[str, Any]],
    summary: dict[str, Any],
    archived: list[dict[str, Any]],
    needs_attention: list[dict[str, Any]],
    *,
    no_color: bool = False,
) -> Group:
    """Compose Sections A + B + (E if R1) + (C if any) + D into a single Rich ``Group``.

    Implements design §4.5. Sections are appended in order:

      - A: :func:`render_header` (always).
      - B: :func:`render_needs_table` (always — empty projects render an
        empty table with headers + footer only).
      - E: :func:`render_r1_detail` (only when at least one project has R1
        triggered AND non-empty ``dirty_files``; ``None`` sentinel triggers
        omission). Added in workspace-dashboard-usability-pass.
      - C: :func:`render_archived` (only when ``archived`` is non-empty;
        ``None`` sentinel triggers omission).
      - D: :func:`render_footer` (always).

    Args:
        projects: Project list (already filtered/sorted upstream by
            :func:`filter_by_rules` + :func:`sort_projects`).
        summary: DS2 status envelope for the header.
        archived: Archived projects (from DS5).
        needs_attention: Needs-attention list (from DS2, pre-filtered).
        no_color: When ``True``, no per-row color is applied (CI / piping).

    Returns:
        A Rich ``Group`` containing 3 to 5 renderables. The caller renders
        via a ``Console`` — see ``tasks.md`` T12 for the CLI integration.
    """
    sections: list[Any] = [
        render_header(summary, no_color=no_color),
        render_needs_table(projects, needs_attention, no_color=no_color),
    ]
    # Section E — R1 dirty file detail (conditional on at least one
    # needs_attention entry having non-empty ``dirty_files``).
    # REQ-WORKSPACE-DASHBOARD-R1-DETAIL: inserted between B and C per
    # design §1 composition shape (A → B → E → C? → D).
    r1_table = render_r1_detail(needs_attention)
    if r1_table is not None:
        sections.append(r1_table)
    archived_table = render_archived(archived)
    if archived_table is not None:
        sections.append(archived_table)
    sections.append(render_footer())
    return Group(*sections)


__all__ = [
    "DashboardFlowNotFoundError",
    "DashboardParseError",
    "DashboardSubprocessError",
    "_truncate_dirty_files",
    "color_code",
    "fetch_archived_projects",
    "fetch_project_list",
    "fetch_status_summary",
    "filter_by_rules",
    "render_archived",
    "render_dashboard",
    "render_footer",
    "render_header",
    "render_needs_table",
    "render_r1_detail",
    "sort_projects",
]
