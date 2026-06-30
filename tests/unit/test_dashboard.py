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

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import flow_engineering.dashboard as dashboard_mod
from flow_engineering.dashboard import (
    DashboardFlowNotFoundError,
    DashboardParseError,
    DashboardSubprocessError,
    fetch_archived_projects,
    fetch_project_list,
    fetch_status_summary,
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
