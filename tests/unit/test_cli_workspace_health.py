"""Tests for `flow workspace health` CLI wiring (PR4a --json skeleton).

PR4a wires the handler skeleton + ``--root`` + ``--json`` only. PR4b
adds the text render branch, ``--filter``, and ``--no-color`` -- those
tests land in this same file at PR4b apply time.

Test isolation: every fixture is rooted at ``tmp_path`` and resolves
the projects root via the explicit ``--root`` flag or via a
``monkeypatch.setenv("FLOW_PROJECTS_ROOT", ...)`` fallback. NO hardcoded
``C:\\dev\\proyects`` paths.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from click.testing import CliRunner

from flow_engineering.cli import main, workspace_health_cmd
from tests.unit._workspace_fixtures import make_project

runner = CliRunner()


def _build_single_project_workspace(tmp_path: Path) -> Path:
    """Build a 1-project workspace under ``tmp_path / "projects"``.

    Bare fixture via ``make_project`` (no openspec/R6-R9 trigger
    signals) -- T-PR4a-3 only asserts envelope shape + byte-determinism,
    not per-project verdict math. The 1-project case is sufficient to
    prove both contracts because the envelope shape is independent of
    project count.
    """
    root = tmp_path / "projects"
    root.mkdir()
    make_project(root, "alpha")
    return root


def test_workspace_health_cmd_json_envelope_shape(tmp_path: Path) -> None:
    """--json emits the v1 envelope with top-level keys ``version, root, projects, totals``.

    Locks REQ-WORKSPACE-HEALTH-JSON-1-ENVELOPE-SHAPE at the CLI surface.
    """
    p = _build_single_project_workspace(tmp_path)
    result = runner.invoke(main, ["workspace", "health", "--root", str(p), "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert set(payload.keys()) == {"version", "root", "projects", "totals"}
    assert list(payload.keys()) == ["version", "root", "projects", "totals"]
    assert payload["version"] == "1"
    # Spec REQ-WORKSPACE-HEALTH-CLI-ROOT: --root flag wins over FLOW_PROJECTS_ROOT env var
    assert Path(payload["root"]).resolve() == p.resolve()


def test_workspace_health_cmd_json_byte_deterministic(tmp_path: Path) -> None:
    """Two --json invocations against the same root produce identical sha256 bytes.

    Locks REQ-WORKSPACE-HEALTH-JSON-2-BYTE-DETERMINISTIC at the CLI surface.
    """
    p = _build_single_project_workspace(tmp_path)
    out1 = runner.invoke(main, ["workspace", "health", "--root", str(p), "--json"]).output
    out2 = runner.invoke(main, ["workspace", "health", "--root", str(p), "--json"]).output

    assert hashlib.sha256(out1.encode("utf-8")).hexdigest() == hashlib.sha256(out2.encode("utf-8")).hexdigest()


def test_workspace_health_cmd_json_flag_default_false(tmp_path: Path) -> None:
    """Without --json, the CLI does NOT emit a JSON envelope.

    Locks REQ-WORKSPACE-HEALTH-JSON-3-FLAG-DEFAULT. The text branch in
    PR4a is a ``NotImplementedError`` stub; the test only asserts that
    (a) the handler does not silently emit JSON, and (b) the handler is
    routed to the text path (NOT a JSON envelope). PR4b replaces the
    stub with the real text render.
    """
    p = _build_single_project_workspace(tmp_path)
    result = runner.invoke(main, ["workspace", "health", "--root", str(p)])

    # PR4a text branch is a NotImplementedError stub; ``result.exit_code``
    # may be non-zero from the raise, but the test contract per
    # REQ-WORKSPACE-HEALTH-JSON-3-FLAG-DEFAULT is that NO JSON is emitted
    # when --json is absent. Asserting on the output prefix is the
    # canonical byte-level check (Rich output does not start with ``{``).
    assert not result.output.startswith("{"), result.output


def test_workspace_health_cmd_root_default(tmp_path: Path, monkeypatch) -> None:
    """Omitting --root falls back to FLOW_PROJECTS_ROOT env var.

    Locks REQ-WORKSPACE-HEALTH-CLI-ROOT (env fallback scenario).
    """
    root = tmp_path / "projects"
    root.mkdir()
    make_project(root, "alpha")
    monkeypatch.setenv("FLOW_PROJECTS_ROOT", str(root))

    result = runner.invoke(main, ["workspace", "health", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert Path(payload["root"]).resolve() == root.resolve()


def test_workspace_health_cmd_missing_root(tmp_path: Path) -> None:
    """A non-existent --root exits 2 with a descriptive stderr message.

    Locks REQ-WORKSPACE-HEALTH-CLI-EXIT-MISSING-ROOT (exit code 2,
    distinct from ``workspace_status``'s exit 1).
    """
    bogus = tmp_path / "bogus"
    result = runner.invoke(main, ["workspace", "health", "--root", str(bogus)])

    assert result.exit_code == 2
    assert "projects root not found:" in result.stderr
    assert result.stdout == ""


def test_workspace_health_cmd_empty_workspace_exits_zero(tmp_path: Path) -> None:
    """REQ-WORKSPACE-HEALTH-JSON-4-EXIT-OK: empty workspace exits 0 with version='1'."""
    # tmp_path has NO projects subdirectory at all (truly empty root)
    runner = CliRunner()
    result = runner.invoke(
        workspace_health_cmd, ["--root", str(tmp_path), "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["version"] == "1"
    assert payload["projects"] == []
    assert payload["totals"] == {"healthy": 0, "attention": 0, "critical": 0}


def test_workspace_health_cmd_dotprefix_only_exits_zero(tmp_path: Path) -> None:
    """REQ-WORKSPACE-HEALTH-JSON-4-EXIT-OK: workspace with only dot-prefix dirs exits 0."""
    # Create ONLY dot-prefix directories (should be filtered out, leaving 0 projects)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / ".cache").mkdir()
    runner = CliRunner()
    result = runner.invoke(
        workspace_health_cmd, ["--root", str(tmp_path), "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["projects"] == []
    assert payload["totals"]["healthy"] == 0


# ---------------------------------------------------------------------------
# PR4b tests (T-PR4b-4 onward). These tests lock the text render branch
# (T-PR4b-1), ``--filter`` (T-PR4b-2), and ``--no-color`` (T-PR4b-3) at the
# CLI surface. The production handler is already in place (compact B); these
# tests are the follow-up compact-A lock that proves the contract.
# ---------------------------------------------------------------------------


def test_workspace_health_cmd_text_panel_header(tmp_path: Path) -> None:
    """REQ-WORKSPACE-HEALTH-TEXT-1-PANEL-HEADER: default text mode renders the panel header.

    Locks: stdout contains the Rich Panel title (``Workspace health``) for
    a populated workspace, OR equals the ``(no projects to report)``
    sentinel for an empty workspace. Both are valid text-branch surfaces.

    NOTE: ``startswith`` was the original spec assertion, but Rich's Panel
    rendering decorates the title with box-drawing characters that appear
    BEFORE the title text in the output. ``in`` is the correct contract:
    "the panel title appears in the rendered output" — same intent as the
    spec, robust to Rich's internal layout choices.
    """
    p = _build_single_project_workspace(tmp_path)
    result = runner.invoke(main, ["workspace", "health", "--root", str(p)])

    assert result.exit_code == 0, result.output
    assert "Workspace health" in result.stdout or result.stdout.startswith(
        "(no projects to report)"
    ), result.stdout


def test_workspace_health_cmd_text_table_columns(tmp_path: Path) -> None:
    """REQ-WORKSPACE-HEALTH-TEXT-2-NEEDS-TABLE: rendered table exposes the 4 columns.

    Locks: stdout contains the project name ``alpha`` AND the literal column
    header substrings ``verdict`` and ``triggers``. The default mode (no
    ``--json``, no ``--no-color``) routes through the text branch and the
    PR3-locked renderer in ``health_render._build_table``.
    """
    p = _build_single_project_workspace(tmp_path)
    result = runner.invoke(main, ["workspace", "health", "--root", str(p)])

    assert result.exit_code == 0, result.output
    stdout_lower = result.stdout.lower()
    assert "alpha" in result.stdout
    assert "verdict" in stdout_lower
    assert "triggers" in stdout_lower
