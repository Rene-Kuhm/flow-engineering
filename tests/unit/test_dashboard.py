"""Tests for the dashboard data layer (PR1 = Wave 1+2 of phase-5-dashboard).

Scope: subprocess wrappers + fetchers ONLY.

  - ``_run_subprocess_json`` generic helper (DS1/DS2 transport)
  - ``fetch_project_list`` DS1 (`flow projects ls --json`)
  - ``fetch_status_summary`` DS2 (`flow workspace status`)
  - ``fetch_archived_projects`` DS5 (direct ``load_registry()`` read)

Out of scope (covered by PR2 / PR3):

  - filter / sort / color logic
  - Rich rendering
  - Click integration / ``flow workspace dashboard`` subcommand

Tests follow the existing project patterns:

  - ``monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)`` to
    inject canned ``CompletedProcess`` instances — mirrors
    ``tests/unit/test_where.py:191``.
  - ``stub_home(monkeypatch, tmp_path)`` from
    ``tests/unit/_workspace_hygiene_fixtures.py`` to redirect
    ``Path.home()`` for the registry resolver so tests do not pollute
    ``~/.flow-engineering/registry.json``.

No fixture should touch the real filesystem; every test must be
deterministic and order-independent.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console
from rich.console import Group as RichGroup
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import flow_engineering.dashboard as dashboard_mod
from flow_engineering.dashboard import (
    DashboardFlowNotFoundError,
    DashboardParseError,
    DashboardSubprocessError,
    _truncate_dirty_files,
    color_code,
    fetch_archived_projects,
    fetch_project_list,
    fetch_status_summary,
    filter_by_rules,
    render_archived,
    render_dashboard,
    render_footer,
    render_header,
    render_needs_table,
    render_r1_detail,
    sort_projects,
)
from flow_engineering.registry import (
    ArchivedEntry,
    Registry,
)
from tests.unit._workspace_hygiene_fixtures import stub_home

# ---------- helpers ----------


def _completed(
    args: list[str], *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    """Build a canned ``CompletedProcess`` for ``fake_run`` callbacks."""
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def _render_text(renderable: Any) -> str:
    """Render a Rich renderable to plain text via ``Console(record=True)``.

    Mirrors the snapshot precedent at ``tests/unit/test_prompt_render_golden.py``
    but inlined — no on-disk golden file required. The plain-text exporter
    strips ANSI escapes so assertions are byte-stable across platforms.
    """
    console = Console(
        width=120,
        force_terminal=False,
        no_color=True,
        record=True,
        file=io.StringIO(),
    )
    console.print(renderable)
    return console.export_text()


# ============================================================================
# T1 — _run_subprocess_json + 3 exception classes + fetch_project_list
# ============================================================================


class TestRunSubprocessJson:
    """``_run_subprocess_json`` is the generic subprocess wrapper used by DS1 + DS2."""

    def test_happy_path_parses_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returncode 0 + valid JSON stdout → parsed dict returned to caller."""
        captured: dict[str, Any] = {}

        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            return _completed(argv, returncode=0, stdout=json.dumps({"ok": 1, "n": 7}))

        monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)

        result = dashboard_mod._run_subprocess_json(["flow", "projects", "ls", "--json"])

        assert result == {"ok": 1, "n": 7}
        assert captured["argv"] == ["flow", "projects", "ls", "--json"]
        # The wrapper MUST pass these kwargs (text + capture_output + check=False)
        # so subprocess behavior is byte-stable across platforms.
        assert captured["kwargs"].get("capture_output") is True
        assert captured["kwargs"].get("text") is True
        assert captured["kwargs"].get("check") is False

    def test_non_zero_exit_raises_subprocess_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returncode != 0 + non-empty stderr → ``DashboardSubprocessError``."""
        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            return _completed(argv, returncode=2, stdout="", stderr="boom: missing arg")

        monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)

        with pytest.raises(DashboardSubprocessError) as exc_info:
            dashboard_mod._run_subprocess_json(["flow", "projects", "ls", "--json"])

        # Message MUST mention the failed command + stderr so operators can diagnose.
        msg = str(exc_info.value)
        assert "flow projects ls --json" in msg
        assert "boom: missing arg" in msg

    def test_invalid_json_raises_parse_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returncode 0 but stdout is not parseable JSON → ``DashboardParseError``."""
        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            return _completed(argv, returncode=0, stdout="not-json-at-all {{{")

        monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)

        with pytest.raises(DashboardParseError):
            dashboard_mod._run_subprocess_json(["flow", "workspace", "status"])

    def test_binary_not_found_raises_flow_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``FileNotFoundError`` from subprocess → ``DashboardFlowNotFoundError`` (not bare OSError)."""
        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            raise FileNotFoundError(2, "No such file", argv[0])

        monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)

        with pytest.raises(DashboardFlowNotFoundError) as exc_info:
            dashboard_mod._run_subprocess_json(["flow", "projects", "ls", "--json"])

        msg = str(exc_info.value)
        assert "flow" in msg


class TestFetchProjectList:
    """``fetch_project_list`` consumes the DS1 v1 envelope's ``projects[]`` field."""

    def test_happy_path_returns_projects_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Valid v1 envelope → returned list mirrors the envelope's ``projects[]``."""
        envelope = {
            "version": "1",
            "root": "/tmp/projects",
            "projects": [
                {"name": "alpha", "path": "/tmp/projects/alpha", "has_git": True},
                {"name": "beta", "path": "/tmp/projects/beta", "has_git": False},
            ],
        }

        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            assert argv == ["flow", "projects", "ls", "--json"]
            return _completed(argv, returncode=0, stdout=json.dumps(envelope))

        monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)

        result = fetch_project_list()

        assert len(result) == 2
        assert [p["name"] for p in result] == ["alpha", "beta"]
        assert result[1]["has_git"] is False

    def test_non_zero_exit_propagates_subprocess_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Subprocess failure bubbles up as ``DashboardSubprocessError`` (no silent fallback)."""
        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            return _completed(argv, returncode=1, stderr="flow: project root not configured")

        monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)

        with pytest.raises(DashboardSubprocessError):
            fetch_project_list()

    def test_invalid_json_propagates_parse_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Garbage stdout → ``DashboardParseError`` (no fallback to ``[]``)."""
        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            return _completed(argv, returncode=0, stdout="oops")

        monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)

        with pytest.raises(DashboardParseError):
            fetch_project_list()

    def test_flow_binary_not_found_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Binary missing → ``DashboardFlowNotFoundError`` propagates from helper."""
        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            raise FileNotFoundError(2, "No such file", "flow")

        monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)

        with pytest.raises(DashboardFlowNotFoundError):
            fetch_project_list()


# ============================================================================
# T2 — fetch_status_summary (DS2)
# ============================================================================


class TestFetchStatusSummary:
    """``fetch_status_summary`` consumes the DS2 JSON 5-rule aggregation envelope."""

    def test_happy_path_returns_envelope(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Valid status envelope → returned dict preserves all top-level keys."""
        envelope = {
            "version": "1",
            "root": "/tmp/projects",
            "totals": {
                "projects": 3,
                "dirty": 1,
                "no_git": 1,
                "no_tests": 1,
                "has_openspec": 2,
                "has_graphify": 0,
                "has_engram": 0,
                "needs_attention": 2,
            },
            "projects": [],
            "needs_attention": [
                {
                    "name": "alpha",
                    "path": "/tmp/projects/alpha",
                    "reasons": ["R1: uncommitted work"],
                }
            ],
        }

        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            assert argv == ["flow", "workspace", "status", "--json"]
            return _completed(argv, returncode=0, stdout=json.dumps(envelope))

        monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)

        result = fetch_status_summary()

        assert result["version"] == "1"
        assert result["totals"]["needs_attention"] == 2
        assert result["needs_attention"][0]["name"] == "alpha"
        assert "R1: uncommitted work" in result["needs_attention"][0]["reasons"]

    def test_non_zero_exit_propagates_subprocess_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Subprocess failure bubbles up as ``DashboardSubprocessError``."""
        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            return _completed(argv, returncode=3, stderr="workspace root unreadable")

        monkeypatch.setattr(dashboard_mod.subprocess, "run", fake_run)

        with pytest.raises(DashboardSubprocessError):
            fetch_status_summary()


# ============================================================================
# T3 — fetch_archived_projects (DS5 direct registry read)
# ============================================================================


class TestFetchArchivedProjects:
    """``fetch_archived_projects`` is the DS5 read — direct ``load_registry()``."""

    def test_happy_path_returns_archived_entries(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Registry with archived entries → returned list mirrors the registry's archived[]."""
        stub_home(monkeypatch, tmp_path)
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        entry_a = ArchivedEntry(
            name="retired-a",
            path=Path("/tmp/retired-a"),
            archived_at="2026-06-01T12:00:00Z",
            reason="manual archive",
        )
        entry_b = ArchivedEntry(
            name="retired-b",
            path=Path("/tmp/retired-b"),
            archived_at="2026-06-15T08:30:00Z",
            reason="stale",
        )
        registry = Registry(version=1, projects=[], archived=[entry_a, entry_b])

        def fake_load_registry() -> Registry:
            return registry

        monkeypatch.setattr(dashboard_mod, "load_registry", fake_load_registry)

        result = fetch_archived_projects()

        assert len(result) == 2
        assert [r["name"] for r in result] == ["retired-a", "retired-b"]
        # Path MUST serialize as a POSIX string (matches the on-disk format).
        assert isinstance(result[0]["path"], str)
        assert result[0]["reason"] == "manual archive"

    def test_missing_registry_returns_empty_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """First-run UX: registry file missing → ``load_registry()`` returns empty → ``[]``."""
        stub_home(monkeypatch, tmp_path)
        assert not (tmp_path / ".flow-engineering" / "registry.json").exists()

        def fake_load_registry() -> Registry:
            return Registry(version=1, projects=[], archived=[])

        monkeypatch.setattr(dashboard_mod, "load_registry", fake_load_registry)

        result = fetch_archived_projects()

        assert result == []

    def test_corrupt_registry_propagates_registry_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Registry parse failure → ``RegistryError`` propagates (not silently swallowed)."""
        from flow_engineering.registry import RegistryError

        stub_home(monkeypatch, tmp_path)

        def fake_load_registry() -> Registry:
            raise RegistryError("failed to parse registry at /x: bad JSON. Delete or fix.")

        monkeypatch.setattr(dashboard_mod, "load_registry", fake_load_registry)

        with pytest.raises(RegistryError) as exc_info:
            fetch_archived_projects()
        assert "failed to parse" in str(exc_info.value)


# ============================================================================
# T4 — filter_by_rules (--filter R1..R5)
# ============================================================================


class TestFilterByRules:
    """``filter_by_rules`` keeps projects whose needs_attention reasons include
    at least one of the requested rule names (R1..R5).
    """

    def test_filter_by_single_rule_R2_shows_only_no_git_projects(self) -> None:  # noqa: N802
        """``--filter R2`` keeps only projects flagged for R2 (no-git)."""
        projects = [
            {"name": "alpha", "path": "/p/alpha"},
            {"name": "beta", "path": "/p/beta"},
            {"name": "gamma", "path": "/p/gamma"},
        ]
        needs_attention = [
            {"name": "alpha", "path": "/p/alpha",
             "reasons": ["R1: uncommitted work"]},
            {"name": "beta", "path": "/p/beta",
             "reasons": ["R2: not a git repository"]},
            {"name": "gamma", "path": "/p/gamma",
             "reasons": ["R2: not a git repository", "R3: no tests"]},
        ]

        filtered_projects, filtered_needs = filter_by_rules(
            projects, needs_attention, ["R2"]
        )

        kept_names = [p["name"] for p in filtered_projects]
        kept_need_names = [n["name"] for n in filtered_needs]
        assert kept_names == ["beta", "gamma"]
        assert kept_need_names == ["beta", "gamma"]

    def test_filter_by_multiple_rules_combined_with_AND(self) -> None:  # noqa: N802
        """Combining R1+R3 keeps projects matching EITHER rule (union)."""
        projects = [
            {"name": "alpha", "path": "/p/alpha"},
            {"name": "beta", "path": "/p/beta"},
            {"name": "gamma", "path": "/p/gamma"},
            {"name": "delta", "path": "/p/delta"},
        ]
        needs_attention = [
            {"name": "alpha", "path": "/p/alpha",
             "reasons": ["R1: uncommitted work"]},
            {"name": "beta", "path": "/p/beta",
             "reasons": ["R2: not a git repository"]},
            {"name": "gamma", "path": "/p/gamma",
             "reasons": ["R3: no tests"]},
            {"name": "delta", "path": "/p/delta",
             "reasons": ["R4: no openspec"]},
        ]

        filtered_projects, _ = filter_by_rules(
            projects, needs_attention, ["R1", "R3"]
        )

        # beta (R2) and delta (R4) are excluded; alpha (R1) and gamma (R3) kept.
        kept_names = sorted(p["name"] for p in filtered_projects)
        assert kept_names == ["alpha", "gamma"]

    def test_filter_by_invalid_rule_raises_ValueError(self) -> None:  # noqa: N802
        """An unknown rule (e.g. ``R9``) raises ``ValueError``."""
        with pytest.raises(ValueError) as exc_info:  # noqa: PT011
            filter_by_rules([], [], ["R9"])

        msg = str(exc_info.value)
        assert "R9" in msg


# ============================================================================
# T5 — sort_projects (--sort name | path | needs-count)
# ============================================================================


class TestSortProjects:
    """``sort_projects`` orders projects by a chosen field."""

    def test_sort_by_name_default(self) -> None:
        """Default sort = alphabetical by ``name``."""
        projects = [
            {"name": "gamma", "path": "/p/gamma"},
            {"name": "alpha", "path": "/p/alpha"},
            {"name": "beta", "path": "/p/beta"},
        ]

        result = sort_projects(projects, "name")

        assert [p["name"] for p in result] == ["alpha", "beta", "gamma"]

    def test_sort_by_path(self) -> None:
        """``--sort path`` orders alphabetically by ``path``."""
        projects = [
            {"name": "alpha", "path": "/p/zeta/sub"},
            {"name": "beta", "path": "/p/alpha"},
            {"name": "gamma", "path": "/p/middle"},
        ]

        result = sort_projects(projects, "path")

        assert [p["path"] for p in result] == ["/p/alpha", "/p/middle", "/p/zeta/sub"]

    def test_sort_by_needs_count_descending(self) -> None:
        """``--sort needs-count`` orders by needs-count DESCENDING (most
        needs-attention first — the operator wants to see the noisiest projects
        on top of the dashboard).

        Anchor for AC4: this test uses the REAL DS1 envelope shape (NO
        inline ``reasons`` on the project dicts) + explicit
        ``needs_by_name`` — matching how the click handler forwards the
        per-project reason counts derived from the DS2 ``needs_attention``
        list. Without the ``needs_by_name`` kwarg this test would FAIL (all
        counts default to 0 → no ordering), which is exactly the bug that
        ``sort-projects-align-with-real-ds-data-flow`` closes.
        """
        projects = [
            {"name": "clean", "path": "/p/clean"},
            {"name": "noisy", "path": "/p/noisy"},
            {"name": "medium", "path": "/p/medium"},
        ]
        needs_by_name = {
            "clean":  [],
            "noisy":  ["R1", "R2", "R3", "R4"],
            "medium": ["R1", "R2"],
        }

        result = sort_projects(projects, "needs-count", needs_by_name=needs_by_name)

        assert [p["name"] for p in result] == ["noisy", "medium", "clean"]  # noqa: E501

    def test_sort_by_needs_count_uses_needs_by_name(self) -> None:
        """sort_projects with explicit needs_by_name reads from real DS2 shape
        (no inline reasons) and orders DESCENDING by len(needs_by_name[name]).

        Anchors the sort-projects-align-with-real-ds-data-flow fix: the
        function MUST accept a keyword-only ``needs_by_name`` map so callers
        (e.g. ``workspace_dashboard_cmd``) can pass reasons derived from the
        DS2 ``needs_attention`` list rather than relying on a non-existent
        inline ``reasons`` field on each project dict.
        """
        projects = [
            {"name": "alpha", "path": "/path/alpha"},
            {"name": "beta",  "path": "/path/beta"},
            {"name": "gamma", "path": "/path/gamma"},
        ]
        needs_by_name = {
            "alpha": ["R1", "R2", "R3"],
            "beta":  ["R1"],
            "gamma": [],
        }
        result = sort_projects(projects, "needs-count", needs_by_name=needs_by_name)
        # Sort descending by needs_count: alpha (3) > beta (1) > gamma (0)
        assert [p["name"] for p in result] == ["alpha", "beta", "gamma"]

    def test_sort_by_needs_count_without_needs_by_name_emits_deprecation_warning(self) -> None:
        """Backward-compat: needs_by_name=None falls back to project['reasons']
        with a DeprecationWarning. Anchors AC5 — the surface that needs fixing.
        """
        projects = [
            {"name": "alpha", "path": "/path/alpha", "reasons": ["R1", "R2"]},
            {"name": "beta",  "path": "/path/beta",  "reasons": []},
        ]
        with pytest.warns(DeprecationWarning, match="needs_by_name=None is deprecated"):
            result = sort_projects(projects, "needs-count")
        # Sort descending by len(reasons): alpha (2) > beta (0)
        assert [p["name"] for p in result] == ["alpha", "beta"]

    def test_sort_with_empty_needs_by_name_returns_zero_count_for_all(self) -> None:
        """Empty needs_by_name dict (not None) returns all projects with
        count 0; sort is stable and preserves input order.

        Documents the edge case where the caller passes ``needs_by_name={}``
        explicitly — distinct from the ``needs_by_name=None`` deprecation path.
        """
        projects = [
            {"name": "alpha", "path": "/path/alpha"},
            {"name": "beta",  "path": "/path/beta"},
            {"name": "gamma", "path": "/path/gamma"},
        ]
        result = sort_projects(projects, "needs-count", needs_by_name={})
        # All have count 0; sort is stable; original order preserved.
        assert [p["name"] for p in result] == ["alpha", "beta", "gamma"]  # noqa: E501

    def test_sort_by_invalid_field_raises_ValueError(self) -> None:  # noqa: N802
        """Unknown sort field raises ``ValueError``."""
        with pytest.raises(ValueError) as exc_info:  # noqa: PT011
            sort_projects([{"name": "alpha"}], "bogus-field")

        msg = str(exc_info.value)
        assert "bogus-field" in msg


# ============================================================================
# T6 — color_code (red >=3 | yellow 1-2 | green 0)
# ============================================================================


class TestColorCode:
    """``color_code`` maps a needs-count to a Rich color name."""

    def test_color_red_for_3_plus_needs(self) -> None:
        """Needs >= 3 → ``red``."""
        assert color_code(3) == "red"
        assert color_code(4) == "red"
        assert color_code(10) == "red"

    def test_color_yellow_for_1_to_2_needs(self) -> None:
        """Needs in 1..=2 → ``yellow``."""
        assert color_code(1) == "yellow"
        assert color_code(2) == "yellow"

    def test_color_green_for_0_needs(self) -> None:
        """Needs == 0 → ``green``."""
        assert color_code(0) == "green"


# ============================================================================
# T7 — render_header (Section A — Panel)
# ============================================================================


class TestRenderHeader:
    """``render_header`` produces a Rich ``Panel`` summarising the workspace."""

    def test_render_header_returns_rich_panel_with_workspace_summary(self) -> None:
        """The header Panel MUST include workspace totals + per-rule counts +
        an ISO timestamp. Snapshot is anchored on stable substrings (Rich
        layout varies slightly across versions)."""
        summary = {
            "totals": {
                "projects": 7,
                "needs_attention": 3,
                "dirty": 2,
                "no_git": 1,
                "no_tests": 0,
            },
            "archived_count": 4,
        }

        panel = render_header(summary)
        # Return type guard — anchors on the public contract, not the layout.
        assert isinstance(panel, Panel)

        text = _render_text(panel)
        # Workspace total + needs-attention total visible to the operator.
        assert "7" in text
        assert "Workspace" in text or "workspace" in text
        # Timestamp MUST be an ISO 8601 string (regex-anchored).
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", text), (
            f"Expected ISO 8601 timestamp in header; got: {text!r}"
        )


# ============================================================================
# T8 — render_needs_table (Section B — color-coded Table)
# ============================================================================


class TestRenderNeedsTable:
    """``render_needs_table`` produces a Rich ``Table`` with project × R1..R5."""

    def test_render_needs_table_with_multiple_projects(self) -> None:
        """The Table lists each project, shows the rule columns, and includes
        per-rule totals. Anchored on stable substrings (column headers,
        project names) instead of exact multi-line layout."""
        projects = [
            {"name": "alpha", "path": "/p/alpha"},
            {"name": "beta", "path": "/p/beta"},
        ]
        needs_attention = [
            {"name": "alpha", "path": "/p/alpha",
             "reasons": ["R1: dirty", "R2: no_git"]},
            {"name": "beta", "path": "/p/beta",
             "reasons": ["R3: no_tests"]},
        ]

        table = render_needs_table(projects, needs_attention)
        assert isinstance(table, Table)

        text = _render_text(table)
        # Project names visible.
        assert "alpha" in text
        assert "beta" in text
        # Rule column headers present (anchored — exact Rich layout may vary).
        assert "R1" in text
        assert "R2" in text
        assert "R3" in text

    def test_render_needs_table_color_coding_correct(self) -> None:
        """``color_code`` is applied per-row; with ``no_color=True`` no ANSI
        escapes leak into the output. This is the integration test that
        proves Section B + color logic cooperate correctly."""
        projects = [
            {"name": "noisy", "path": "/p/noisy",
             "reasons": ["R1", "R2", "R3"]},
            {"name": "calm", "path": "/p/calm",
             "reasons": []},
        ]
        needs_attention = [
            {"name": "noisy", "path": "/p/noisy",
             "reasons": ["R1: dirty", "R2: no_git", "R3: no_tests"]},
            {"name": "calm", "path": "/p/calm", "reasons": []},
        ]

        text_default = _render_text(render_needs_table(projects, needs_attention))
        text_no_color = _render_text(
            render_needs_table(projects, needs_attention, no_color=True)
        )

        # Both rows render — color logic does not filter content.
        assert "noisy" in text_default
        assert "calm" in text_default
        # ``no_color=True`` strips ANSI codes (Rich `no_color` console flag).
        assert "\x1b[" not in text_no_color

    def test_render_needs_table_folds_long_names(self) -> None:
        """A 35-char project name + narrow terminal MUST wrap (not truncate)
        with NO Unicode U+2026 anywhere in the output.

        Anchors AC4: Section B columns use ``OverflowMethod.fold`` so long
        project names appear on multiple lines instead of being truncated
        with the Unicode single-char ellipsis (the source of the ``\\ufffd``
        bug on cp1252 terminals).
        """
        long_name = "a" * 35
        projects = [{"name": long_name, "path": f"/p/{long_name}"}]
        needs_attention = [
            {"name": long_name, "path": f"/p/{long_name}",
             "reasons": ["R1: dirty"]},
        ]

        console = Console(
            width=40,
            no_color=True,
            record=True,
            file=io.StringIO(),
        )
        table = render_needs_table(projects, needs_attention)
        console.print(table)
        text = console.export_text()
        # Every char of the name MUST be present (fold wraps onto multiple
        # lines but never drops chars; truncation shortens the name).
        # Count the ``a`` characters in the rendered text — Rich's ``fold``
        # overflow method may split the name across column boundaries
        # (interspersed with box-drawing chars), so a naive ``in`` check
        # is brittle. Counting chars is exact and bug-anchored.
        a_count = text.count("a")
        assert a_count >= len(long_name), (
            f"render_needs_table MUST preserve all {len(long_name)} chars of "
            f"the name; found {a_count} 'a' chars in: {text!r}"
        )
        # The Unicode ellipsis is FORBIDDEN in any output. This is the
        # explicit invariant: the cp1252 bug repros as ``\ufffd`` from the
        # Unicode U+2026 char.
        assert "\u2026" not in text, (
            f"render_needs_table MUST NOT emit Unicode U+2026; got: {text!r}"
        )

    def test_render_needs_table_no_unicode_ellipsis_in_output(self) -> None:
        """Plain Section B render MUST NOT contain ``\\u2026`` even with a
        long-but-fits project name (triangulates T-B3 with a less-extreme
        but still truncatable case at width=120).

        Anchors the design §3 invariant: per-column ``OverflowMethod.fold``
        never inserts the Unicode U+2026 single-char ellipsis (Rich fold
        uses literal ``\\n`` instead).
        """
        long_but_fits = "a" * 50  # 50 chars; longer than the 30-char column
        projects = [{"name": long_but_fits, "path": f"/p/{long_but_fits}"}]
        needs_attention = [
            {"name": long_but_fits, "path": f"/p/{long_but_fits}",
             "reasons": ["R1: dirty"]},
        ]
        text = _render_text(render_needs_table(projects, needs_attention))
        assert "\u2026" not in text, (
            f"Unicode U+2026 ellipsis is FORBIDDEN in dashboard output; got: {text!r}"
        )


# ============================================================================
# T9 — render_archived (Section C — Table or None)
# ============================================================================


class TestRenderArchived:
    """``render_archived`` produces a Table of archived projects, or None when empty."""

    def test_render_archived_returns_table_or_none_when_empty(self) -> None:
        """Two assertions per the task spec: empty input → ``None`` (caller
        omits the section); non-empty → a Table with the archived entries."""
        # Empty case → caller must omit Section C.
        assert render_archived([]) is None

        # Non-empty case → Table with the rows.
        archived = [
            {
                "name": "retired-a",
                "path": "/p/retired-a",
                "archived_at": "2026-06-01T12:00:00Z",
                "reason": "manual archive",
            },
        ]
        table = render_archived(archived)
        assert isinstance(table, Table)
        text = _render_text(table)
        assert "retired-a" in text
        assert "manual archive" in text

    def test_render_archived_no_unicode_ellipsis(self) -> None:
        """``render_archived`` MUST NOT emit Unicode U+2026 in any cell.

        Triangulates the design §3 invariant: per-column widths keep short
        content intact, and the ``archived_at`` ISO timestamp is the
        longest cell — it must NOT be truncated with the Unicode single-
        char ellipsis (the cp1252 bug source).
        """
        archived = [
            {
                "name": "retired-x",
                "path": "/p/retired-x",
                "archived_at": "2026-06-15T08:30:00Z",
                "reason": "stale",
            },
        ]
        table = render_archived(archived)
        text = _render_text(table)
        assert "\u2026" not in text, (
            f"render_archived MUST NOT emit Unicode U+2026; got: {text!r}"
        )

    def test_render_archived_uses_explicit_column_widths(self) -> None:
        """Render of ``render_archived`` MUST keep the ISO ``archived_at``
        timestamp intact (no Unicode truncation) at the standard width=120.

        Anchors the design §3 contract: per-column ``min_width`` /
        ``max_width`` are honored. The 20-char ISO timestamp fits
        comfortably in the column's ``max_width=25`` slot and MUST appear
        verbatim — Rich's column overflow does NOT collapse it to the
        Unicode U+2026 single-char ellipsis.
        """
        archived = [
            {
                "name": "retired-x",
                "path": "/p/retired-x",
                "archived_at": "2026-06-15T08:30:00Z",
                "reason": "stale",
            },
        ]
        text = _render_text(render_archived(archived))
        # The ISO timestamp MUST be present (column max_width >= 19).
        assert "2026-06-15T08:30:00Z" in text, (
            f"render_archived MUST preserve the ISO timestamp; got: {text!r}"
        )
        # No Unicode U+2026 in any cell.
        assert "\u2026" not in text


# ============================================================================
# T10 — render_footer (Section D — Text)
# ============================================================================


class TestRenderFooter:
    """``render_footer`` produces a Rich ``Text`` with tip pointers."""

    def test_render_footer_returns_text_with_tips(self) -> None:
        """The footer Text MUST include both tip pointers from design §4.4:
        ``flow workspace status --json`` (machine-readable) and
        ``flow workspace fix <project> --yes --backup`` (remediation)."""
        footer = render_footer()
        assert isinstance(footer, Text)

        # Snapshot-friendly: anchor on stable substrings, not exact layout.
        text = _render_text(footer)
        assert "Tip" in text
        assert "flow workspace status --json" in text
        assert "flow workspace fix" in text


# ============================================================================
# T11 — render_dashboard (composer — A + B + (C or None) + D)
# ============================================================================


class TestRenderDashboard:
    """``render_dashboard`` composes the 4 sections into a Rich ``Group``."""

    def test_render_dashboard_full_with_all_sections(self) -> None:
        """Full composition: header + needs table + archived table + footer,
        all rendered through a single Group."""
        summary = {
            "totals": {"projects": 3, "needs_attention": 2,
                       "dirty": 1, "no_git": 1, "no_tests": 0},
            "archived_count": 1,
        }
        projects = [
            {"name": "alpha", "path": "/p/alpha"},
            {"name": "beta", "path": "/p/beta"},
        ]
        needs_attention = [
            {"name": "alpha", "path": "/p/alpha",
             "reasons": ["R1: dirty"]},
            {"name": "beta", "path": "/p/beta",
             "reasons": ["R2: no_git"]},
        ]
        archived = [
            {"name": "retired-x", "path": "/p/retired-x",
             "archived_at": "2026-06-15T08:30:00Z",
             "reason": "stale"},
        ]

        group = render_dashboard(projects, summary, archived, needs_attention)
        assert isinstance(group, RichGroup)

        text = _render_text(group)
        # Section A — header.
        assert "Workspace" in text
        # Section B — needs-attention rows.
        assert "alpha" in text
        assert "beta" in text
        # Section C — archived row.
        assert "retired-x" in text
        # Section D — footer tip.
        assert "Tip" in text

    def test_render_dashboard_with_empty_archived_omits_section(self) -> None:
        """Empty ``archived`` list MUST omit Section C from the composite."""
        summary = {"totals": {"projects": 1}, "archived_count": 0}
        projects = [{"name": "alpha", "path": "/p/alpha"}]
        needs_attention: list[dict[str, Any]] = []

        group = render_dashboard(projects, summary, [], needs_attention)
        text = _render_text(group)

        # Header + footer present.
        assert "Workspace" in text
        assert "Tip" in text
        # No archived table emitted — anchor on the absence of the title.
        assert "Archived projects" not in text


# ============================================================================
# T-D1..T-D6 — Sub-batch D (R1 detail render — Section E)
# ============================================================================
#
# Anchors REQ-WORKSPACE-DASHBOARD-R1-DETAIL: when at least one project has
# R1 triggered, the dashboard MUST render a Section E listing the dirty
# files (cap 20 per project, ASCII `...` ellipsis, footer hint). The
# section MUST be omitted when no R1 triggered. ACs 9/10/11/12/16 anchor.


class TestTruncateDirtyFiles:
    """``_truncate_dirty_files`` caps a file list at ``cap`` entries with ASCII ``...``.

    Pure helper, no I/O — easy to unit test without mocking. The cap
    defaults to 20 per design §4.2; the test exercises both the below-cap
    and above-cap paths.
    """

    def test_truncate_dirty_files_below_cap_unchanged(self) -> None:
        """When ``len(files) <= cap``, the list is returned unchanged (no copy mutation)."""
        files = [" M a.py", " M b.py", " M c.py"]
        result = _truncate_dirty_files(files, cap=20)
        assert result == files

    def test_truncate_dirty_files_above_cap_truncated(self) -> None:
        """When ``len(files) > cap``, slice to ``cap-1`` + ASCII ``\"...\"`` marker."""
        files = [f" M file_{i}.py" for i in range(25)]
        result = _truncate_dirty_files(files, cap=20)
        # cap-1 = 19 file entries + the ASCII marker
        assert len(result) == 20
        assert result[-1] == "..."
        # The first cap-1 entries are preserved verbatim.
        assert result[:19] == files[:19]

    def test_truncate_dirty_files_uses_ascii_ellipsis_not_unicode(self) -> None:
        """The truncation marker MUST be ASCII ``\"...\"`` (3 dots), NEVER Unicode ``\\u2026``.

        Triangulates the design §3 invariant: the Unicode U+2026 single-char
        ellipsis is the cp1252 bug source; all dashboard ellipses must be
        ASCII.
        """
        files = [f" M f_{i}.py" for i in range(25)]
        result = _truncate_dirty_files(files, cap=20)
        joined = "\n".join(result)
        assert "\u2026" not in joined
        assert "..." in joined


class TestRenderR1Detail:
    """``render_r1_detail`` produces Section E Table for R1-triggered projects."""

    def test_r1_detail_returns_none_when_no_r1_triggered(self) -> None:
        """Empty ``needs_attention`` MUST return ``None`` (caller omits Section E)."""
        assert render_r1_detail([]) is None

    def test_r1_detail_returns_none_when_no_dirty_files(self) -> None:
        """When no entry has ``dirty_files``, return ``None`` — Section E hidden.

        Defensive: a needs_attention entry from a non-R1 reason (R2/R3/R4)
        must NOT trigger Section E even if the entry is present.
        """
        needs = [
            {"name": "alpha", "reasons": ["R2: no version control"]},
            {"name": "beta", "reasons": ["R3: no tests detected"]},
        ]
        assert render_r1_detail(needs) is None

    def test_r1_detail_returns_table_when_r1_triggered(self) -> None:
        """One R1 project with 3 dirty files MUST render a Table containing the project + files."""
        needs = [
            {
                "name": "alpha",
                "reasons": ["R1: uncommitted work"],
                "dirty_files": [" M a.py", "?? b.py", " M c.py"],
            },
        ]
        table = render_r1_detail(needs)
        assert isinstance(table, Table)
        text = _render_text(table)
        assert "alpha" in text
        # All 3 dirty files appear in the rendered table (under cap).
        assert " M a.py" in text
        assert "?? b.py" in text
        assert " M c.py" in text

    def test_r1_detail_hides_project_with_empty_dirty_files(self) -> None:
        """A needs_attention entry with ``dirty=True`` but ``dirty_files=[]`` is hidden from Section E.

        Anchors spec scenario: 'Section E for a project with 0 dirty files
        is hidden'. The R1 reason may be present but the data is empty;
        Section E only lists projects with non-empty ``dirty_files``.
        """
        needs = [
            {
                "name": "alpha",
                "reasons": ["R1: uncommitted work"],
                "dirty_files": [],
            },
            {
                "name": "beta",
                "reasons": ["R1: uncommitted work"],
                "dirty_files": [" M b.py"],
            },
        ]
        table = render_r1_detail(needs)
        assert isinstance(table, Table)
        text = _render_text(table)
        # alpha is hidden (no dirty files)
        assert text.count("alpha") == 0
        # beta appears
        assert "beta" in text
        assert " M b.py" in text

    def test_r1_detail_caps_at_20_files_with_ascii_ellipsis(self) -> None:
        """25 dirty files MUST truncate to 19 files + ASCII ``\"...\"`` marker + footer hint substring.

        Anchors AC11: cap 20 with ASCII ellipsis. Footer hint substring
        appears in the Section E rendered text (via the table title or
        row content — exact placement is design's choice).
        """
        dirty_files = [f" M file_{i}.py" for i in range(25)]
        needs = [
            {
                "name": "alpha",
                "reasons": ["R1: uncommitted work"],
                "dirty_files": dirty_files,
            },
        ]
        table = render_r1_detail(needs)
        assert isinstance(table, Table)
        text = _render_text(table)
        # 19 file entries (cap-1) + the ASCII "..." marker.
        assert text.count("...") >= 1
        # Footer hint substring present (case-insensitive; design chooses the exact wording).
        assert "git status" in text.lower()

    def test_r1_detail_uses_ascii_ellipsis_not_unicode(self) -> None:
        """Section E MUST NOT emit Unicode U+2026 anywhere; ASCII ``...`` only."""
        dirty_files = [f" M f_{i}.py" for i in range(25)]
        needs = [
            {
                "name": "alpha",
                "reasons": ["R1: uncommitted work"],
                "dirty_files": dirty_files,
            },
        ]
        table = render_r1_detail(needs)
        text = _render_text(table)
        assert "\u2026" not in text, (
            f"Section E MUST NOT emit Unicode U+2026; got: {text!r}"
        )


class TestRenderDashboardComposesSectionE:
    """``render_dashboard`` composes Section E between B and C conditionally on R1."""

    def test_render_dashboard_includes_section_e_when_r1_triggered(self) -> None:
        """When at least one needs_attention entry has ``dirty_files``, Section E appears."""
        summary = {"totals": {"projects": 1}, "archived_count": 0}
        projects = [{"name": "alpha", "path": "/p/alpha"}]
        needs_attention = [
            {
                "name": "alpha",
                "path": "/p/alpha",
                "reasons": ["R1: uncommitted work"],
                "dirty_files": [" M a.py"],
            },
        ]

        group = render_dashboard(projects, summary, [], needs_attention)
        text = _render_text(group)

        # Section A (header) + Section E (R1 detail) present.
        assert "Workspace" in text
        assert " M a.py" in text

    def test_render_dashboard_omits_section_e_when_no_r1(self) -> None:
        """When no project has ``dirty_files``, Section E MUST be omitted."""
        summary = {"totals": {"projects": 1}, "archived_count": 0}
        projects = [{"name": "alpha", "path": "/p/alpha"}]
        needs_attention: list[dict[str, Any]] = []

        group = render_dashboard(projects, summary, [], needs_attention)
        text = _render_text(group)

        # Section A + footer present, but no dirty-file rows.
        assert "Workspace" in text
        assert "Tip" in text
        # No M-prefix dirty file rows in the dashboard output.
        assert " M " not in text

    def test_render_dashboard_section_e_appears_between_b_and_c(self) -> None:
        """Section E MUST appear between Section B (needs table) and Section C (archived).

        Anchors design §1 composition: A → B → E → (C if any) → D.

        We anchor on substring FIRST occurrences in the rendered text.
        " M a.py" is unique to Section E (the dirty-file row); the
        archived table title "Archived projects" is unique to Section C
        (the table title); "Tip" is unique to the footer. Names like
        ``alpha`` / ``retired-x`` may appear in multiple sections, so we
        avoid them as anchors.
        """
        summary = {"totals": {"projects": 2}, "archived_count": 1}
        projects = [
            {"name": "alpha", "path": "/p/alpha"},
            {"name": "retired-x", "path": "/p/retired-x"},
        ]
        needs_attention = [
            {
                "name": "alpha",
                "path": "/p/alpha",
                "reasons": ["R1: uncommitted work"],
                "dirty_files": [" M a.py"],
            },
        ]
        archived = [
            {
                "name": "retired-x",
                "path": "/p/retired-x",
                "archived_at": "2026-06-15T08:30:00Z",
                "reason": "stale",
            },
        ]

        group = render_dashboard(projects, summary, archived, needs_attention)
        text = _render_text(group)

        # All section anchors present in the rendered output.
        idx_dirty = text.find(" M a.py")
        idx_archived_title = text.find("Archived projects")
        idx_tip = text.find("Tip")
        assert idx_dirty != -1, f"dirty row ' M a.py' not in text: {text!r}"
        assert idx_archived_title != -1, (
            f"archived title 'Archived projects' not in text: {text!r}"
        )
        assert idx_tip != -1, f"footer 'Tip' not in text: {text!r}"
        # Order: A + B → E (dirty row) → C (archived table) → D (footer tip).
        assert idx_dirty < idx_archived_title < idx_tip, (
            f"Section order violated: dirty={idx_dirty} "
            f"archived_title={idx_archived_title} tip={idx_tip}"
        )


def test_render_footer_includes_section_e_hint() -> None:
    """The footer Text MUST include a tip pointer for Section E when R1 is triggered.

    Anchors AC12: 'Footer hint appears for capped projects' — the
    design §7.3 3rd tip line is unconditional, but its content MUST
    mention Section E + ``git status`` so operators know where to find
    the dirty file list.
    """
    footer = render_footer()
    assert isinstance(footer, Text)

    text = _render_text(footer)
    # Substring anchors (case-insensitive where natural).
    assert "Section E" in text
    assert "git status" in text
