"""Tests for ``flow workspace dashboard`` Click command.

PR3 scope (Wave 5 of phase-5-dashboard): wires the dashboard data + logic +
rendering layer (PR1 + PR2) into the user-facing Click surface at
``src/flow_engineering/cli.py:3034``. NO new dashboard logic — every test
here asserts the handler wires the existing public API correctly.

Pattern #538 — one identity per command. There is NO ``--json`` flag on the
dashboard; the machine-readable endpoint stays at ``flow workspace status``.
These tests confirm that contract by exercising the human-facing output
rendered via Rich (ANSI in CI / piping when ``--no-color`` is passed).

Test isolation:
    Each test monkey-patches the three ``fetch_*`` functions on
    ``flow_engineering.dashboard`` so the handler never invokes the real
    ``flow`` subprocess. The tests are deterministic and order-independent.
"""

from __future__ import annotations

import re

import click.testing
import pytest
from click.testing import CliRunner
from rich.console import Console as RealConsole

from flow_engineering import dashboard as dashboard_mod
from flow_engineering.cli import main

runner = CliRunner()


# =============================================================================
# Helpers — canned fetcher payloads
# =============================================================================


def _make_project(name: str, *, path: str = "/p", reasons: list[str] | None = None) -> dict:
    """Build a minimal project dict matching the REAL DS1 envelope shape.

    NO ``reasons`` key — reasons live on ``needs_attention`` entries only.

    The legacy ``reasons`` parameter is intentionally IGNORED: it is kept as
    a no-op for backward-compat with test bodies written before the
    sort-projects-align-with-real-ds-data-flow fix so they keep compiling,
    but ``workspace_dashboard_cmd`` does NOT mirror ``reasons`` onto each
    project dict — it derives the per-project count from
    ``needs_by_name`` (built by the caller from ``needs_attention``).
    """
    return {"name": name, "path": f"{path}/{name}"}


def _make_needs(name: str, reasons: list[str]) -> dict:
    """Build a DS2 needs_attention entry."""
    return {"name": name, "reasons": reasons}


# =============================================================================
# T12.1 — default invocation renders all 4 sections
# =============================================================================


def test_workspace_dashboard_cmd_default_renders_all_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default ``flow workspace dashboard`` MUST render Sections A, B, D.

    Section C (archived) is omitted when the archived list is empty. This
    test wires the three ``fetch_*`` functions to canned payloads so the
    handler can be exercised end-to-end without invoking the real ``flow``
    subprocess.
    """
    projects = [_make_project("alpha"), _make_project("beta")]
    summary = {
        "totals": {"projects": 2, "needs_attention": 0, "dirty": 0, "no_git": 0, "no_tests": 0},
        "needs_attention": [],
        "archived_count": 0,
    }
    monkeypatch.setattr(dashboard_mod, "fetch_project_list", lambda: projects)
    monkeypatch.setattr(dashboard_mod, "fetch_status_summary", lambda: summary)
    monkeypatch.setattr(dashboard_mod, "fetch_archived_projects", lambda: [])

    result = runner.invoke(main, ["workspace", "dashboard"])

    assert result.exit_code == 0, result.output
    plain = _ANSI_ESCAPE_RE.sub("", result.output)
    # Section A — header.
    assert "Workspace" in plain
    assert "2 projects" in plain
    # Section B — needs-attention table title.
    assert "Needs attention" in plain
    # Section D — footer tips.
    assert "Tip" in plain
    assert "flow workspace status --json" in plain
    assert "flow workspace fix" in plain


# =============================================================================
# T12.2 — --filter R2 keeps only R2-matching projects
# =============================================================================


def test_workspace_dashboard_cmd_with_filter_r2_drops_non_matching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--filter R2`` MUST drop projects whose needs-attention has no R2 reason.

    The handler calls ``filter_by_rules(projects, needs, ("R2",))`` and
    forwards the filtered lists to ``render_dashboard``. We verify the
    filtering happened by inspecting the rendered output: ``alpha`` (R2)
    appears, ``beta`` (R1-only) is gone.
    """
    projects = [_make_project("alpha"), _make_project("beta")]
    needs_attention = [
        _make_needs("alpha", ["R2: not a git repository"]),
        _make_needs("beta", ["R1: uncommitted work"]),
    ]
    summary = {
        "totals": {"projects": 2, "needs_attention": 2, "dirty": 1, "no_git": 1, "no_tests": 0},
        "needs_attention": needs_attention,
        "archived_count": 0,
    }
    monkeypatch.setattr(dashboard_mod, "fetch_project_list", lambda: projects)
    monkeypatch.setattr(dashboard_mod, "fetch_status_summary", lambda: summary)
    monkeypatch.setattr(dashboard_mod, "fetch_archived_projects", lambda: [])

    result = runner.invoke(main, ["workspace", "dashboard", "--filter", "R2"])

    assert result.exit_code == 0, result.output
    plain = _ANSI_ESCAPE_RE.sub("", result.output)
    assert "alpha" in plain
    assert "beta" not in plain


# =============================================================================
# T12.3 — --sort needs-count orders projects by descending needs count
# =============================================================================


def test_workspace_dashboard_cmd_with_sort_needs_count_orders_descending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--sort needs-count`` MUST order projects by descending reason count.

    Three projects with reason counts of 1, 3, 2 must appear in the rendered
    output in the order 3, 2, 1 (noisiest first per ``sort_projects`` design).

    Note: ``sort_projects`` reads ``len(project['reasons'])`` from each
    project dict — this matches the in-process ``render_needs_table`` path
    where reasons are mirrored onto each project entry (see PR2 design §4.2
    pre-existing implementation). The Click handler is just the wiring;
    the sort semantics live in ``sort_projects``.
    """
    projects = [
        _make_project("zeta", reasons=["R1: uncommitted work"]),
        _make_project(
            "yotta", reasons=["R1: uncommitted work", "R2: not a git repository", "R3: no tests"]
        ),
        _make_project("xeno", reasons=["R1: uncommitted work", "R4: no openspec"]),
    ]
    needs_attention = [
        _make_needs("zeta", ["R1: uncommitted work"]),
        _make_needs("yotta", ["R1: uncommitted work", "R2: not a git repository", "R3: no tests"]),
        _make_needs("xeno", ["R1: uncommitted work", "R4: no openspec"]),
    ]
    summary = {
        "totals": {"projects": 3, "needs_attention": 3, "dirty": 3, "no_git": 1, "no_tests": 1},
        "needs_attention": needs_attention,
        "archived_count": 0,
    }
    monkeypatch.setattr(dashboard_mod, "fetch_project_list", lambda: projects)
    monkeypatch.setattr(dashboard_mod, "fetch_status_summary", lambda: summary)
    monkeypatch.setattr(dashboard_mod, "fetch_archived_projects", lambda: [])

    result = runner.invoke(main, ["workspace", "dashboard", "--sort", "needs-count"])

    assert result.exit_code == 0, result.output
    # Strip ANSI escape sequences before positional search — the dashboard
    # uses Rich colors when --no-color is not set, but the sort order is a
    # plain-text property of the rendered table.
    plain = _ANSI_ESCAPE_RE.sub("", result.output)
    pos_yotta = plain.find("yotta")
    pos_xeno = plain.find("xeno")
    pos_zeta = plain.find("zeta")
    assert pos_yotta != -1, f"yotta must be rendered: {plain!r}"
    assert pos_xeno != -1, f"xeno must be rendered: {plain!r}"
    assert pos_zeta != -1, f"zeta must be rendered: {plain!r}"
    # needs-count descending: yotta (3) -> xeno (2) -> zeta (1).
    assert pos_yotta < pos_xeno < pos_zeta, (
        f"Expected yotta -> xeno -> zeta order, got positions {pos_yotta}, {pos_xeno}, {pos_zeta}"
    )


# =============================================================================
# T12.4 — --no-color suppresses ANSI escape codes
# =============================================================================


_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def test_workspace_dashboard_cmd_with_no_color_suppresses_ansi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``--no-color`` MUST emit no ANSI escape sequences + Console MUST
    use the explicit ``width`` binding (per design §3).

    Tightened in T-B10 (workspace-dashboard-usability-pass): the handler
    constructs ``Console(width=<int>, soft_wrap=True, no_color=no_color)``;
    when ``--no-color`` is set, Rich drops ANSI codes (CI / piping
    contract) AND the explicit width binding takes effect.
    """
    projects = [_make_project("alpha")]
    summary = {
        "totals": {"projects": 1, "needs_attention": 0, "dirty": 0, "no_git": 0, "no_tests": 0},
        "needs_attention": [],
        "archived_count": 0,
    }
    monkeypatch.setattr(dashboard_mod, "fetch_project_list", lambda: projects)
    monkeypatch.setattr(dashboard_mod, "fetch_status_summary", lambda: summary)
    monkeypatch.setattr(dashboard_mod, "fetch_archived_projects", lambda: [])

    # Track Console construction to verify the explicit width binding.
    console_init: dict[str, object] = {}
    original_console_init = RealConsole.__init__

    def tracking_console_init(self: object, *args: object, **kwargs: object) -> None:
        # Capture the first Console built in the handler path (post-probe).
        if "width" in kwargs and "soft_wrap" in kwargs:
            console_init.setdefault("width", kwargs.get("width"))
            console_init.setdefault("soft_wrap", kwargs.get("soft_wrap"))
            console_init.setdefault("no_color", kwargs.get("no_color"))
        original_console_init(self, *args, **kwargs)

    monkeypatch.setattr(RealConsole, "__init__", tracking_console_init)

    result = runner.invoke(main, ["workspace", "dashboard", "--no-color"])

    assert result.exit_code == 0, result.output
    assert _ANSI_ESCAPE_RE.search(result.output) is None, (
        f"--no-color must suppress ANSI escapes; got: {result.output!r}"
    )
    # Explicit width binding (post-T-B6): terminal-introspected or 120 fallback.
    assert console_init.get("width") is not None, (
        f"Console(width=None) is forbidden — width MUST be explicit; got {console_init!r}"
    )
    assert console_init.get("width") == 120 or (
        isinstance(console_init.get("width"), int) and console_init["width"] > 0
    )
    assert console_init.get("soft_wrap") is True
    assert console_init.get("no_color") is True


# =============================================================================
# T12.5 — workspace_dashboard_cmd wires needs_by_name from needs_attention
# =============================================================================


def test_workspace_dashboard_cmd_passes_needs_by_name_to_sort_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caller (workspace_dashboard_cmd) MUST build needs_by_name from
    ``summary['needs_attention']`` (keyed by ``name``) and pass it as a
    keyword to ``sort_projects`` — anchored on AC7.

    Sort_projects is monkey-patched so the assertion can verify what
    keyword payload was actually forwarded (instead of relying on rendered
    output order, which depends on the global kind/emoji order in
    render_needs_table).
    """
    captured: dict[str, object] = {}

    def fake_sort(projects: list, field: str, *, needs_by_name=None) -> list:
        captured["field"] = field
        captured["needs_by_name"] = needs_by_name
        return list(projects)

    projects = [
        {
            "name": "alpha",
            "path": "/path/alpha",
            "has_git": True,
            "has_openspec": False,
            "has_tests": False,
            "has_graphify": False,
            "last_status_check": "",
        },
        {
            "name": "beta",
            "path": "/path/beta",
            "has_git": True,
            "has_openspec": True,
            "has_tests": True,
            "has_graphify": False,
            "last_status_check": "",
        },
    ]
    needs_attention = [
        {
            "name": "alpha",
            "path": "/path/alpha",
            "reasons": ["R1: uncommitted work", "R2: not a git repository"],
        },
        {"name": "beta", "path": "/path/beta", "reasons": []},
    ]
    summary = {
        "totals": {
            "projects": 2,
            "needs_attention": 1,
            "dirty": 1,
            "no_git": 1,
            "no_tests": 0,
        },
        "needs_attention": needs_attention,
        "archived_count": 0,
    }

    monkeypatch.setattr(dashboard_mod, "fetch_project_list", lambda: projects)
    monkeypatch.setattr(dashboard_mod, "fetch_status_summary", lambda: summary)
    monkeypatch.setattr(dashboard_mod, "fetch_archived_projects", lambda: [])
    monkeypatch.setattr(dashboard_mod, "sort_projects", fake_sort)

    result = runner.invoke(main, ["workspace", "dashboard", "--sort", "needs-count"])

    assert result.exit_code == 0, result.output
    assert captured.get("field") == "needs-count"
    # Caller MUST build the map from entry['name'] (the canonical key).
    # Empty-name entries are dropped defensively; entries with a name but
    # an empty ``reasons`` list ARE included (so all listed projects have
    # a 0 baseline — count_source lookup never misses).
    expected = {
        "alpha": ["R1: uncommitted work", "R2: not a git repository"],
        "beta": [],
    }
    assert captured.get("needs_by_name") == expected, (
        f"Caller did not forward needs_by_name from needs_attention; "
        f"captured={captured.get('needs_by_name')!r}, expected={expected!r}"
    )


# =============================================================================
# T-B1 — workspace_dashboard_cmd: sys.stdout.reconfigure OSError fallback (Pattern #551)
# =============================================================================


def test_workspace_dashboard_cmd_console_reconfigure_handles_oserror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``sys.stdout.reconfigure(encoding="utf-8")`` MUST be wrapped in try/except OSError.

    Anchors AC3: legacy terminals / redirected pipes raise ``OSError`` from
    ``reconfigure``; the handler MUST swallow it, fall back to current
    behavior, and complete with exit 0. The replacement character ``\\ufffd``
    MUST NOT appear in stdout for ASCII-only project names.
    """
    projects = [_make_project("alpha")]
    summary = {
        "totals": {"projects": 1, "needs_attention": 0, "dirty": 0, "no_git": 0, "no_tests": 0},
        "needs_attention": [],
        "archived_count": 0,
    }
    monkeypatch.setattr(dashboard_mod, "fetch_project_list", lambda: projects)
    monkeypatch.setattr(dashboard_mod, "fetch_status_summary", lambda: summary)
    monkeypatch.setattr(dashboard_mod, "fetch_archived_projects", lambda: [])

    reconfigure_calls: list[dict[str, object]] = []

    def fake_reconfigure(self: object, **kwargs: object) -> None:
        reconfigure_calls.append(kwargs)
        raise OSError("reconfigure not supported on this stream")

    # Patch the class method — Click's CliRunner replaces sys.stdout with
    # its own ``_NamedTextIOWrapper`` during invocation, so monkeypatching
    # ``sys.stdout`` directly is ineffective. Patching the class captures
    # every instance CliRunner creates.
    monkeypatch.setattr(click.testing._NamedTextIOWrapper, "reconfigure", fake_reconfigure)

    result = runner.invoke(main, ["workspace", "dashboard", "--no-color"])

    # Production code MUST actually call reconfigure (otherwise OSError is
    # a no-op and the test proves nothing about the reconfigure guard).
    assert reconfigure_calls, "Handler did not call sys.stdout.reconfigure"
    assert reconfigure_calls[0].get("encoding") == "utf-8"
    # OSError is swallowed; handler still completes with exit 0.
    assert result.exit_code == 0, (
        f"OSError on reconfigure MUST be swallowed; got exit {result.exit_code}: {result.output!r}"
    )
    plain = _ANSI_ESCAPE_RE.sub("", result.output)
    # No replacement character on ASCII names.
    assert "\ufffd" not in plain
    # ASCII project name still appears.
    assert "alpha" in plain


# =============================================================================
# T-B2 — workspace_dashboard_cmd: Console(width=..., soft_wrap=True) explicit binding
# =============================================================================


def test_workspace_dashboard_cmd_console_uses_explicit_width(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``Console(...)`` in ``workspace_dashboard_cmd`` MUST be built with an
    explicit ``width`` kwarg (terminal-introspected, fallback 120) and
    ``soft_wrap=True`` so long names wrap rather than truncate with the
    Unicode U+2026 ellipsis.

    Anchors AC1 + AC4 + AC6 (per-column overflow + width binding).
    """
    import flow_engineering.cli as cli_mod

    projects = [_make_project("alpha")]
    summary = {
        "totals": {"projects": 1, "needs_attention": 0, "dirty": 0, "no_git": 0, "no_tests": 0},
        "needs_attention": [],
        "archived_count": 0,
    }
    monkeypatch.setattr(dashboard_mod, "fetch_project_list", lambda: projects)
    monkeypatch.setattr(dashboard_mod, "fetch_status_summary", lambda: summary)
    monkeypatch.setattr(dashboard_mod, "fetch_archived_projects", lambda: [])

    captured: dict[str, object] = {}

    class TrackingConsole(RealConsole):
        def __init__(self, *args: object, **kwargs: object) -> None:
            captured["width"] = kwargs.get("width")
            captured["soft_wrap"] = kwargs.get("soft_wrap")
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(cli_mod, "Console", TrackingConsole)

    result = runner.invoke(main, ["workspace", "dashboard", "--no-color"])

    assert result.exit_code == 0, result.output
    # The handler MUST pass an explicit width (not None — None = auto-detect,
    # which produces non-deterministic snapshot output).
    assert captured.get("width") is not None, (
        "Console(width=None) is forbidden — width MUST be explicit"
    )
    # Width MUST be a positive int (terminal-introspected or 120 fallback).
    assert isinstance(captured.get("width"), int)
    assert captured["width"] > 0
    # soft_wrap=True is the knob that prevents Unicode U+2026 truncation.
    assert captured.get("soft_wrap") is True


# ============================================================================
# T-D7..T-D8 — Sub-batch D (R1 detail CLI integration)
# ============================================================================
#
# Anchors REQ-WORKSPACE-DASHBOARD-R1-DETAIL end-to-end: the CLI handler
# propagates dirty_files from the needs_attention entry into the
# rendered Section E, with cap-20 truncation at the boundary.


def _make_needs_with_dirty(name: str, reasons: list[str], dirty_files: list[str]) -> dict:
    """Build a DS2 needs_attention entry carrying ``dirty_files`` (R1-triggered)."""
    return {"name": name, "reasons": reasons, "dirty_files": dirty_files}


def test_workspace_dashboard_cmd_renders_section_e_when_r1_triggered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``flow workspace dashboard`` MUST render Section E when R1 is triggered.

    Anchors AC9: Section E renders when exactly one project has R1
    triggered. The handler threads ``dirty_files`` through ``render_dashboard``
    so Section E consumes the data and surfaces it on stdout.
    """
    projects = [_make_project("alpha")]
    needs_attention = [
        _make_needs_with_dirty(
            "alpha",
            ["R1: uncommitted work"],
            [" M src/foo.py", "?? src/bar.py"],
        ),
    ]
    summary = {
        "totals": {"projects": 1, "needs_attention": 1, "dirty": 1, "no_git": 0, "no_tests": 0},
        "needs_attention": needs_attention,
        "archived_count": 0,
    }
    monkeypatch.setattr(dashboard_mod, "fetch_project_list", lambda: projects)
    monkeypatch.setattr(dashboard_mod, "fetch_status_summary", lambda: summary)
    monkeypatch.setattr(dashboard_mod, "fetch_archived_projects", lambda: [])

    result = runner.invoke(main, ["workspace", "dashboard", "--no-color"])

    assert result.exit_code == 0, result.output
    plain = _ANSI_ESCAPE_RE.sub("", result.output)
    # Section A + Section E both rendered.
    assert "Workspace" in plain
    # Dirty file paths surface in the rendered output.
    assert " M src/foo.py" in plain
    assert "?? src/bar.py" in plain
    # ASCII ellipsis invariant.
    assert "\u2026" not in plain


def test_workspace_dashboard_cmd_section_e_truncates_at_20_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``flow workspace dashboard`` MUST cap Section E at 20 files per project with ASCII ``...``.

    Anchors AC11: 25 dirty files → first 19 + ``...`` + footer hint
    substring visible in stdout. The cap mechanism is the
    ``_truncate_dirty_files`` helper at the dashboard layer.
    """
    projects = [_make_project("alpha")]
    dirty_files = [f" M f_{i}.py" for i in range(25)]
    needs_attention = [
        _make_needs_with_dirty(
            "alpha",
            ["R1: uncommitted work"],
            dirty_files,
        ),
    ]
    summary = {
        "totals": {"projects": 1, "needs_attention": 1, "dirty": 1, "no_git": 0, "no_tests": 0},
        "needs_attention": needs_attention,
        "archived_count": 0,
    }
    monkeypatch.setattr(dashboard_mod, "fetch_project_list", lambda: projects)
    monkeypatch.setattr(dashboard_mod, "fetch_status_summary", lambda: summary)
    monkeypatch.setattr(dashboard_mod, "fetch_archived_projects", lambda: [])

    result = runner.invoke(main, ["workspace", "dashboard", "--no-color"])

    assert result.exit_code == 0, result.output
    plain = _ANSI_ESCAPE_RE.sub("", result.output)
    # The first 19 file entries appear (cap-1), the 20th+ do not.
    for i in range(19):
        assert f" M f_{i}.py" in plain, f"Missing f_{i} in output"
    for i in range(19, 25):
        assert f" M f_{i}.py" not in plain, f"f_{i} should be truncated; found in output"
    # ASCII ellipsis marker present.
    assert "..." in plain
    # Footer hint substring present.
    assert "git status" in plain.lower()
    # Unicode U+2026 NEVER appears.
    assert "\u2026" not in plain
