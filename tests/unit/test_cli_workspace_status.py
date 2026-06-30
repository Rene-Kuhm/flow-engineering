"""Functional unit tests for ``flow workspace status`` (Phase 3 of workspace-intelligence).

Per design #448 §4, these 10 tests cover:
    1. text default format (header + per-project lines + SUMMARY)
    2. empty root text + JSON
    3. R1 dirty-committed -> "R1: uncommitted work"
    4. R2 no-git -> "R2: no version control"
    5. R3 no-tests -> "R3: no tests detected"
    6. R4 SDD-stack missing openspec -> "R4: SDD-adjacent stack missing openspec"
    7. R5 informational-only (no add to needs_attention)
    8. totals match array sizes
    9. byte-deterministic across invocations
    10. version first key + version == "1"

Strict TDD per ``sdd-apply/strict-tdd.md``: RED-then-GREEN cycle was satisfied
in T-1 by the placeholder signature tests; this file IS the GREEN that
exercises the locked helper behavior end-to-end via ``CliRunner``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from flow_engineering import cli as cli_mod
from flow_engineering.cli import main
from tests.unit._workspace_fixtures import (
    _default_branch_fake_git,
    make_fake_dirty_project,
    make_fake_go_project,
    make_fake_no_git_project,
    make_fake_openspec_project,
    make_fake_python_project,
)

runner = CliRunner()


def _fake_git(*args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
    """Canned git for tests that exercise the dirty/no-remote code paths."""
    cwd = Path(str(kwargs.get("cwd", "")))
    cp = subprocess.CompletedProcess(args=["git", *args], returncode=0, stdout="", stderr="")
    if args and args[0] == "rev-parse":
        cp.stdout = "main\n"
    elif args and args[0] == "status":
        cp.stdout = " M uncommitted.txt\n" if "dirty" in cwd.name else ""
    elif args and args[0] == "config":
        cp.returncode = 1  # no remote
    return cp


def _invoke(root: Path, monkeypatch, *extra: str) -> object:
    """Invoke ``flow workspace status`` with a stubbed git seam."""
    monkeypatch.setattr(cli_mod, "_git", _fake_git)
    return runner.invoke(
        main,
        ["workspace", "status", "--root", str(root), *extra],
    )


def _payload(root: Path, monkeypatch) -> dict:
    """Invoke --json and parse the envelope."""
    result = _invoke(root, monkeypatch, "--json")
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_workspace_status_text_default_format(tmp_path: Path, monkeypatch) -> None:
    """Text default contains ``WORKSPACE STATUS:``, per-project lines, SUMMARY block."""
    root = tmp_path / "projects"
    root.mkdir()
    # Two Python projects without git/openspec — fire R2+R4 each, which
    # exercises both the per-project tags AND the SUMMARY block.
    make_fake_python_project(root, "alpha")
    make_fake_python_project(root, "beta")

    result = _invoke(root, monkeypatch)

    assert result.exit_code == 0, result.output
    assert "WORKSPACE STATUS" in result.output
    assert "- alpha (Python) [NO-GIT] [NO OPENSPEC]" in result.output
    assert "- beta (Python) [NO-GIT] [NO OPENSPEC]" in result.output
    assert "SUMMARY" in result.output
    assert "projects: 2" in result.output
    assert "needs_attention: 2" in result.output
    assert "no_git: 2" in result.output
    assert "[INFO: graphify probe is stubbed in v1]" in result.output


def test_workspace_status_empty_root(tmp_path: Path, monkeypatch) -> None:
    """Empty root renders ``(no projects to report)`` + JSON totals all 0 + exit 0."""
    root = tmp_path / "projects"
    root.mkdir()

    text = _invoke(root, monkeypatch)
    js = _invoke(root, monkeypatch, "--json")

    assert text.exit_code == 0, text.output
    assert "(no projects to report)" in text.output
    assert js.exit_code == 0, js.output
    payload = json.loads(js.output)
    assert payload["totals"]["projects"] == 0
    assert payload["totals"]["needs_attention"] == 0
    assert payload["totals"]["dirty"] == 0
    assert payload["totals"]["no_git"] == 0
    assert payload["totals"]["no_tests"] == 0


def test_workspace_status_r1_dirty_committed(tmp_path: Path, monkeypatch) -> None:
    """R1: git+dirty project surfaces in ``needs_attention`` with reason ``R1: uncommitted work``."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_dirty_project(root, "dirty-go")

    payload = _payload(root, monkeypatch)
    by_name = {item["name"]: item for item in payload["needs_attention"]}

    assert "dirty-go" in by_name
    assert "R1: uncommitted work" in by_name["dirty-go"]["reasons"]
    assert payload["totals"]["dirty"] == 1


def test_workspace_status_r2_no_git(tmp_path: Path, monkeypatch) -> None:
    """R2: project without ``.git/`` surfaces ``R2: no version control``."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_no_git_project(root, "no-git-py")

    payload = _payload(root, monkeypatch)
    by_name = {item["name"]: item for item in payload["needs_attention"]}

    assert "no-git-py" in by_name
    assert "R2: no version control" in by_name["no-git-py"]["reasons"]
    assert payload["totals"]["no_git"] == 1


def test_workspace_status_r3_no_tests(tmp_path: Path, monkeypatch) -> None:
    """R3: project with empty ``test_commands`` surfaces ``R3: no tests detected``."""
    root = tmp_path / "projects"
    root.mkdir()
    # Unknown-stack project (only openspec/changes/): has_git=False (R2 fires),
    # stack=Unknown → test_commands=[] (R3 fires). Unknown is NOT in SDD_STACKS
    # so R4 does NOT fire — keeps the assertion focused on R3.
    make_fake_openspec_project(root, "unknown-os")

    payload = _payload(root, monkeypatch)
    by_name = {item["name"]: item for item in payload["needs_attention"]}

    assert "unknown-os" in by_name
    assert "R3: no tests detected" in by_name["unknown-os"]["reasons"]
    assert payload["totals"]["no_tests"] == 1


def test_workspace_status_r4_no_openspec_sdd_stack(tmp_path: Path, monkeypatch) -> None:
    """R4: SDD-adjacent stack (Python/Go/Rust) without openspec surfaces the R4 reason."""
    root = tmp_path / "projects"
    root.mkdir()
    # Python project without openspec — R4 should fire (R2 and R3 also fire).
    make_fake_python_project(root, "py-no-os")

    payload = _payload(root, monkeypatch)
    by_name = {item["name"]: item for item in payload["needs_attention"]}

    assert "py-no-os" in by_name
    assert "R4: SDD-adjacent stack missing openspec" in by_name["py-no-os"]["reasons"]

    # Same logic must hold for Go stack (Go is also in _SDD_STACKS_REQUIRING_OPENSPEC).
    root_go = tmp_path / "projects_go"
    root_go.mkdir()
    make_fake_go_project(root_go, "go-no-os")
    payload_go = _payload(root_go, monkeypatch)
    by_name_go = {item["name"]: item for item in payload_go["needs_attention"]}
    assert "go-no-os" in by_name_go
    assert "R4: SDD-adjacent stack missing openspec" in by_name_go["go-no-os"]["reasons"]

    # Counter-example: project WITH openspec does NOT get an R4 reason
    # even though R2 + R3 still fire (no .git/, no detected tests).
    root_with = tmp_path / "projects_with"
    root_with.mkdir()
    make_fake_openspec_project(root_with, "py-with-os")
    payload_with = _payload(root_with, monkeypatch)
    by_name_with = {item["name"]: item for item in payload_with["needs_attention"]}
    assert "py-with-os" in by_name_with  # present (R2 + R3 reasons)
    for reason in by_name_with["py-with-os"]["reasons"]:
        assert "R4" not in reason, f"R4 must NOT fire when has_openspec=True; got {reason!r}"


def test_workspace_status_r5_informational_only(tmp_path: Path, monkeypatch) -> None:
    """R5: ``has_graphify == False`` does NOT add to ``needs_attention`` (informational only)."""
    root = tmp_path / "projects"
    root.mkdir()
    # Python project WITHOUT openspec — should fire R4 but NOT R5 (R5 is
    # informational-only and Phase 1 graphify probe returns False always).
    make_fake_python_project(root, "py-graphify-stub")

    payload = _payload(root, monkeypatch)

    # The project IS in needs_attention (due to R3 no-tests + R4 missing openspec),
    # but R5 is NOT in the reasons list (it's only informational).
    by_name = {item["name"]: item for item in payload["needs_attention"]}
    assert "py-graphify-stub" in by_name
    for reason in by_name["py-graphify-stub"]["reasons"]:
        assert "R5" not in reason

    # totals.has_graphify counts only True (Phase 1 stub returns False).
    assert payload["totals"]["has_graphify"] == 0


def test_workspace_status_totals_match_array_size(tmp_path: Path, monkeypatch) -> None:
    """Totals counters are internally consistent: ``len(needs_attention) == totals['needs_attention']``."""
    root = tmp_path / "projects"
    root.mkdir()
    # dirty-go: Go with .git/, dirty → R1 only (Go stack, has tests, no openspec).
    # unknown-os: openspec/changes/ only → no R4 (Unknown not in SDD_STACKS),
    #             fires R2 (no git) + R3 (no detected tests).
    make_fake_dirty_project(root, "dirty-go")
    make_fake_openspec_project(root, "unknown-os")

    payload = _payload(root, monkeypatch)
    totals = payload["totals"]

    # Cardinal invariant: needs_attention total MUST equal array length.
    assert totals["needs_attention"] == len(payload["needs_attention"]) == 2

    # Per-rule counters reflect the projects detected.
    assert totals["dirty"] == 1
    assert totals["no_git"] == 1
    assert totals["no_tests"] == 1
    assert totals["projects"] == 2

    # Cross-check that the per-rule reason strings are unique across the array.
    by_name = {item["name"]: item for item in payload["needs_attention"]}
    assert "R1: uncommitted work" in by_name["dirty-go"]["reasons"]
    assert "R2: no version control" in by_name["unknown-os"]["reasons"]
    assert "R3: no tests detected" in by_name["unknown-os"]["reasons"]


def test_workspace_status_byte_deterministic(tmp_path: Path, monkeypatch) -> None:
    """Two consecutive --json invocations on an unchanged root emit byte-identical stdout."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_python_project(root, "py")
    make_fake_go_project(root, "go")
    monkeypatch.setattr(cli_mod, "_git", _default_branch_fake_git(branch="main"))

    one = _invoke(root, monkeypatch, "--json")
    two = _invoke(root, monkeypatch, "--json")

    assert one.exit_code == 0, one.output
    assert two.exit_code == 0, two.output
    assert one.output == two.output, (
        f"byte-determinism violated:\n  first:  {one.output!r}\n  second: {two.output!r}"
    )


def test_workspace_status_version_first_key(tmp_path: Path, monkeypatch) -> None:
    """JSON envelope has ``version`` as the first key and ``version == \"1\"``."""
    root = tmp_path / "projects"
    root.mkdir()
    make_fake_python_project(root, "py")

    payload = _payload(root, monkeypatch)

    keys = list(payload.keys())
    assert keys[0] == "version", f"first key MUST be 'version', got {keys[0]!r}"
    assert payload["version"] == "1"
    # Spec forbids timestamp fields for byte-determinism.
    assert "generated_at" not in payload
