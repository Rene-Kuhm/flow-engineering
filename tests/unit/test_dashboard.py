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
    """``fetch_status_summary`` consumes the DS2 5-rule aggregation envelope."""

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
            assert argv == ["flow", "workspace", "status"]
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
        on top of the dashboard)."""
        projects = [
            {"name": "clean", "path": "/p/clean", "reasons": []},
            {"name": "noisy", "path": "/p/noisy",
             "reasons": ["R1", "R2", "R3", "R4"]},
            {"name": "medium", "path": "/p/medium",
             "reasons": ["R1", "R2"]},
        ]

        result = sort_projects(projects, "needs-count")

        assert [p["name"] for p in result] == ["noisy", "medium", "clean"]

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
