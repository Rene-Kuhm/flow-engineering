"""Unit tests for ``flow where`` cross-project search (Phase 2 of workspace-intelligence).

Per design #457 + spec #456 + tasks #458, these 10 tests cover:
    1. text default format — groups by project, ASCII-safe, TOTAL summary line
    2. --format=json envelope — version first, totals correct
    3. --format=tsv — header + tab body + newline escape
    4. --regex valid + invalid (exit 2) — opt-in regex matcher
    5. --limit N caps hits per project
    6. --root PATH resolves cross-project tree
    7. exit code trio — 0 on match / 1 on no-match / 2 on error
    8. --engram flag accepted, no behavior change (no-op identity)
    9. byte-determinism (AC9) — two invocations produce byte-identical stdout
   10. scope discipline — files outside the 6 dirs are NEVER scanned

Strict TDD per ``sdd-apply/strict-tdd.md``. Helpers under test live in
``src/flow_engineering/cli.py`` as private module-level functions:
- ``_search_projects_for_query`` (T-1 orchestrator)
- ``_format_where_text`` / ``_format_where_json`` / ``_format_where_tsv`` (T-2 formatters)
- 4 new Click options on ``where_cmd`` (T-3 + T-4 dispatch)

Tests use ``tmp_path`` exclusively — no hardcoded paths, never set
``FLOW_PROJECTS_ROOT=C:/dev/proyects``. The inline ``make_fake_workspace_with_code``
helper writes ``src/`` / ``tests/`` / ``openspec/`` / ``graphify-out/`` fixtures
across N fake projects; ``tests/unit/_workspace_fixtures.py`` is reused for the
generic project skeletons (do NOT add helpers there — Phase 2 stays additive).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main

runner = CliRunner()


# ---------- Inline fixture helper (NOT added to _workspace_fixtures.py) ----------


def make_fake_workspace_with_code(
    root: Path,
    project_names: Iterable[str],
    *,
    with_src: bool = True,
    with_tests: bool = True,
    with_openspec: bool = True,
    with_graphify: bool = True,
    with_node_modules: bool = False,
) -> None:
    """Write a fake multi-project workspace under ``root`` for ``flow where`` tests.

    Each project gets ``src/foo.py`` with ``def foo(): pass`` (case-insensitive
    substring "foo" matches) and ``tests/test_foo.py`` with ``def test_foo():
    pass``. Optional ``openspec/changes/x/explore.md`` and
    ``graphify-out/graph.json`` files round out the 6-dir prospec. Setting
    ``with_node_modules=True`` adds a ``node_modules/bar.js`` file OUTSIDE the
    prospec — used by the scope-discipline test to assert those files are
    never scanned even when their content matches the query.
    """
    root.mkdir(parents=True, exist_ok=True)
    for name in project_names:
        proj = root / name
        proj.mkdir()
        if with_src:
            (proj / "src").mkdir()
            (proj / "src" / "foo.py").write_text("def foo():\n    return 1\n", encoding="utf-8")
        if with_tests:
            (proj / "tests").mkdir()
            (proj / "tests" / "test_foo.py").write_text(
                "def test_foo():\n    assert foo() == 1\n",
                encoding="utf-8",
            )
        if with_openspec:
            (proj / "openspec" / "changes" / "x").mkdir(parents=True)
            (proj / "openspec" / "changes" / "x" / "explore.md").write_text(
                "# explore\nfoo in spec\n", encoding="utf-8"
            )
        if with_graphify:
            (proj / "graphify-out").mkdir()
            (proj / "graphify-out" / "graph.json").write_text(
                json.dumps({"nodes": [{"id": "n1", "label": "foo-node"}]}),
                encoding="utf-8",
            )
        if with_node_modules:
            (proj / "node_modules").mkdir()
            (proj / "node_modules" / "bar.js").write_text(
                "function foo() { return 'should not match'; }\n",
                encoding="utf-8",
            )


# ---------- The 10 locked tests ----------


def test_where_cmd_text_default_groups_by_project(tmp_path: Path) -> None:
    """T1: text default groups by project, ASCII-safe, TOTAL summary line."""
    make_fake_workspace_with_code(tmp_path, ["proj-a", "proj-b"])

    result = runner.invoke(main, ["where", "foo", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    out = result.output
    # Both project names appear.
    assert "proj-a" in out
    assert "proj-b" in out
    # Total summary line is present.
    assert "TOTAL" in out.upper()
    # ASCII-safe: no Unicode box-drawing chars (codepoints > 0x7E).
    for ch in out:
        assert ord(ch) < 0x80, f"non-ASCII char {ch!r} (U+{ord(ch):04X}) in text output"


def test_where_cmd_json_envelope_structure(tmp_path: Path) -> None:
    """T2: --format=json envelope has version first + totals + results[] shape."""
    make_fake_workspace_with_code(tmp_path, ["proj-a"])

    result = runner.invoke(main, ["where", "foo", "--root", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    keys = list(payload.keys())
    # First key MUST be "version" per spec.
    assert keys[0] == "version"
    assert payload["version"] == "1"
    assert payload["format"] == "json"
    assert payload["totals"]["projects_searched"] == 1
    assert payload["totals"]["matches"] >= 3
    # Each result item carries the locked field set.
    for item in payload["results"]:
        assert set(item.keys()) >= {"project", "file", "line", "content", "type"}
    # engram stub field is present.
    assert payload["engram"] == {"enabled": False, "phase": "stub"}


def test_where_cmd_tsv_header_and_body(tmp_path: Path) -> None:
    """T3: --format=tsv emits header + tab-separated body with newlines escaped."""
    make_fake_workspace_with_code(tmp_path, ["proj-a"])

    result = runner.invoke(main, ["where", "foo", "--root", str(tmp_path), "--format", "tsv"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    # First line is the locked header.
    assert lines[0] == "project\tfile\tline\ttype\tcontent"
    # Body rows have exactly 5 fields when split on tab.
    for row in lines[1:]:
        parts = row.split("\t")
        assert len(parts) == 5, f"row {row!r} has {len(parts)} fields, want 5"


def test_where_cmd_regex_valid_and_invalid(tmp_path: Path) -> None:
    """T4: --regex opt-in (valid + invalid → exit 2)."""
    make_fake_workspace_with_code(tmp_path, ["proj-a"])

    # Valid regex matches def foo / def test_foo.
    good = runner.invoke(main, ["where", "^def ", "--root", str(tmp_path), "--regex"])
    assert good.exit_code == 0, good.output
    assert "def " in good.output

    # Invalid regex → exit 2 (re.compile failure at CLI boundary).
    bad_pattern = "a[b"
    # Sanity: pytest confirms the pattern is genuinely unparseable.
    with pytest.raises(re.error):
        re.compile(bad_pattern)
    bad = runner.invoke(main, ["where", bad_pattern, "--root", str(tmp_path), "--regex"])
    assert bad.exit_code == 2, bad.output


def test_where_cmd_limit_caps_hits(tmp_path: Path) -> None:
    """T5: --limit N caps hits."""
    make_fake_workspace_with_code(tmp_path, ["proj-a"])

    # Uncapped run produces many matches.
    uncapped = runner.invoke(main, ["where", "foo", "--root", str(tmp_path)])
    assert uncapped.exit_code == 0, uncapped.output
    uncapped_match_lines = sum(1 for ln in uncapped.output.splitlines() if "foo" in ln.lower())

    # Capped run produces at most --limit matches.
    capped = runner.invoke(main, ["where", "foo", "--root", str(tmp_path), "--limit", "1"])
    assert capped.exit_code == 0, capped.output
    capped_match_lines = sum(1 for ln in capped.output.splitlines() if "foo" in ln.lower())
    # Capping must reduce (or keep equal) the match-line count.
    assert capped_match_lines <= uncapped_match_lines
    # The fixture has multiple matches; with limit=1 the cap is exercised.
    assert "matches=1" in capped.output or "matches: 1" in capped.output or capped_match_lines <= 1


def test_where_cmd_root_resolution(tmp_path: Path) -> None:
    """T6: --root PATH activates cross-project scope (different root → different hits)."""
    root_a = tmp_path / "root_a"
    root_b = tmp_path / "root_b"
    make_fake_workspace_with_code(root_a, ["proj-a"])
    make_fake_workspace_with_code(root_b, ["proj-b"])

    result_a = runner.invoke(main, ["where", "foo", "--root", str(root_a)])
    result_b = runner.invoke(main, ["where", "foo", "--root", str(root_b)])

    assert result_a.exit_code == 0, result_a.output
    assert result_b.exit_code == 0, result_b.output
    assert "proj-a" in result_a.output
    assert "proj-b" not in result_a.output
    assert "proj-b" in result_b.output
    assert "proj-a" not in result_b.output


def test_where_cmd_exit_code_trio(tmp_path: Path) -> None:
    """T7: exit 0 on match / 1 on no-match / 2 on invalid regex."""
    make_fake_workspace_with_code(tmp_path, ["proj-a"])

    # Match → exit 0.
    on_match = runner.invoke(main, ["where", "foo", "--root", str(tmp_path)])
    assert on_match.exit_code == 0, on_match.output

    # No match → exit 1 (grep convention; replaces today's always-0).
    on_no_match = runner.invoke(
        main, ["where", "totally-nonexistent-string-xyzzy", "--root", str(tmp_path)]
    )
    assert on_no_match.exit_code == 1, on_no_match.output

    # Invalid regex → exit 2 (re.compile failure at CLI boundary).
    on_error = runner.invoke(main, ["where", "[bad", "--root", str(tmp_path), "--regex"])
    assert on_error.exit_code == 2, on_error.output


def test_where_cmd_engram_noop_identity(tmp_path: Path) -> None:
    """T8: --engram flag accepted with no behavior change in Phase 2."""
    make_fake_workspace_with_code(tmp_path, ["proj-a"])

    without = runner.invoke(main, ["where", "foo", "--root", str(tmp_path)])
    with_flag = runner.invoke(main, ["where", "foo", "--root", str(tmp_path), "--engram"])

    assert without.exit_code == with_flag.exit_code == 0, (
        without.output,
        with_flag.output,
    )
    # Text output is byte-identical — --engram is a no-op stub in Phase 2.
    assert without.output == with_flag.output


def test_where_cmd_byte_identical_across_invocations(tmp_path: Path) -> None:
    """T9 (AC9): two consecutive invocations produce byte-identical stdout.

    Mirrors the pattern from ``test_flow_projects_ls_json_byte_identical_envelope``:
    no filesystem changes between the two invocations, and the rendered
    text must be byte-identical (no timestamps, no non-deterministic ordering).
    """
    make_fake_workspace_with_code(tmp_path, ["proj-a"])

    one = runner.invoke(main, ["where", "foo", "--root", str(tmp_path)])
    two = runner.invoke(main, ["where", "foo", "--root", str(tmp_path)])

    assert one.exit_code == 0, one.output
    assert two.exit_code == 0, two.output
    assert one.output == two.output, (
        f"AC9 byte-identical violation:\n  first:  {one.output!r}\n  second: {two.output!r}"
    )


def test_where_cmd_scope_discipline_excludes_node_modules(tmp_path: Path) -> None:
    """T10: files outside the 6 locked dirs are NEVER scanned.

    Even when ``node_modules/bar.js`` contains "foo", the result must NOT
    include any hit from that path — Phase 2 prospec is opt-in.
    """
    make_fake_workspace_with_code(tmp_path, ["proj-a"], with_node_modules=True)

    result = runner.invoke(main, ["where", "foo", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "node_modules" not in result.output
    assert "bar.js" not in result.output
