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

import pytest
from click.testing import CliRunner

from flow_engineering import dashboard as dashboard_mod
from flow_engineering.cli import main

runner = CliRunner()


# =============================================================================
# Helpers — canned fetcher payloads
# =============================================================================


def _make_project(name: str, *, path: str = "/p", reasons: list[str] | None = None) -> dict:
    """Build a minimal project dict matching the DS1/DS2 contract shape."""
    return {"name": name, "path": f"{path}/{name}", "reasons": reasons or []}


def _make_needs(name: str, reasons: list[str]) -> dict:
    """Build a DS2 needs_attention entry."""
    return {"name": name, "reasons": reasons}


# =============================================================================
# T12.1 — default invocation renders all 4 sections
# =============================================================================


def test_workspace_dashboard_cmd_default_renders_all_sections(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_workspace_dashboard_cmd_with_filter_r2_drops_non_matching(monkeypatch: pytest.MonkeyPatch) -> None:
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
        _make_project("yotta", reasons=["R1: uncommitted work", "R2: not a git repository", "R3: no tests"]),
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
    """``--no-color`` MUST emit no ANSI escape sequences.

    The handler constructs ``Console(no_color=no_color, ...)`` per design §4.5;
    when the flag is set, Rich drops ANSI codes (CI / piping contract).
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

    result = runner.invoke(main, ["workspace", "dashboard", "--no-color"])

    assert result.exit_code == 0, result.output
    assert _ANSI_ESCAPE_RE.search(result.output) is None, (
        f"--no-color must suppress ANSI escapes; got: {result.output!r}"
    )

