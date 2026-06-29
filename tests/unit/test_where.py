"""Unit tests for ``src/flow_engineering/where.py`` (REQ-V1.0.1..V1.0.4).

REQ-V1.0.1..V1.0.3 — `flow where "<query>"` cross-source retrieval: pure-function
backends `grep_repo`, `split_code_vs_tests`, `grep_sdd_archive`, `grep_graphify`,
plus the `where` orchestrator + `render_text` formatter. All implementations
live in :mod:`flow_engineering.where`.

These tests are written BEFORE the implementation per strict TDD. Every
public function has a RED -> GREEN -> REFACTOR history in the commit log.

Test isolation:
    ``grep_repo`` / ``grep_sdd_archive`` shell out to rg. Each test uses
    ``monkeypatch.chdir(tmp_path)`` and builds a tiny fixture tree so the
    subprocess never touches the real repo's ``src/`` / ``tests/`` /
    ``openspec/changes/archive/``. ``grep_graphify`` operates on a
    monkeypatched ``graph_path`` pointing at a tmp_path fixture JSON.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from flow_engineering import where

runner = CliRunner()


# ---------- Helpers ----------


def _make_src_tree(root: Path, files: dict[str, str]) -> None:
    """Write a ``src/`` and ``tests/`` tree under ``root`` from a path->content mapping.

    Keys of the form ``"src/foo.py"`` go under ``root/src/foo.py``; keys of
    the form ``"tests/test_x.py"`` go under ``root/tests/test_x.py``. Parent
    directories are created on demand.
    """
    for rel_path, content in files.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


# ---------- T1.1 / T1.2 — REQ-V1.0.1: grep_repo ----------


class TestGrepRepo:
    """REQ-V1.0.1: ``grep_repo`` returns ``(code_hits, tests_hits)`` split by prefix."""

    def test_no_match_returns_empty_pair(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty tree produces ``([], [])`` — no rg hits in either bucket."""
        _make_src_tree(
            tmp_path,
            {
                "src/empty.py": "# no symbol here\n",
                "tests/test_empty.py": "# nope\n",
            },
        )
        monkeypatch.chdir(tmp_path)
        code, tests = where.grep_repo("no-such-symbol-xyz", limit=20)
        assert code == []
        assert tests == []

    def test_code_only_hits_in_code_bucket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A hit in ``src/`` flows to the code bucket; tests bucket is empty."""
        _make_src_tree(
            tmp_path,
            {
                "src/auth.py": "def make_jwt():\n    return 'token'\n",
                "tests/test_auth.py": "# unrelated\n",
            },
        )
        monkeypatch.chdir(tmp_path)
        code, tests = where.grep_repo("jwt", limit=20)
        assert tests == []
        assert len(code) == 1
        assert code[0].path == "src/auth.py"
        assert code[0].line == 1

    def test_tests_only_hits_in_tests_bucket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A hit in ``tests/`` flows to the tests bucket; code bucket is empty."""
        _make_src_tree(
            tmp_path,
            {
                "src/auth.py": "# nothing here\n",
                "tests/test_auth.py": "def test_jwt_signs():\n    pass\n",
            },
        )
        monkeypatch.chdir(tmp_path)
        code, tests = where.grep_repo("jwt", limit=20)
        assert code == []
        assert len(tests) == 1
        assert tests[0].path == "tests/test_auth.py"
        assert tests[0].line == 1

    def test_mixed_hits_split_correctly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mixed hits are partitioned by path prefix; order preserved per bucket."""
        _make_src_tree(
            tmp_path,
            {
                "src/auth.py": "jwt line\n",
                "src/middleware.py": "jwt in middleware\n",
                "tests/test_auth.py": "jwt in tests\n",
            },
        )
        monkeypatch.chdir(tmp_path)
        code, tests = where.grep_repo("jwt", limit=20)
        assert [h.path for h in code] == ["src/auth.py", "src/middleware.py"]
        assert [h.path for h in tests] == ["tests/test_auth.py"]

    def test_limit_caps_each_bucket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``limit=2`` truncates each bucket independently at 2 hits."""
        _make_src_tree(
            tmp_path,
            {
                "src/a.py": "jwt a\njwt a2\njwt a3\n",
                "src/b.py": "jwt b\n",
                "tests/test_a.py": "jwt ta\njwt ta2\njwt ta3\n",
                "tests/test_b.py": "jwt tb\n",
            },
        )
        monkeypatch.chdir(tmp_path)
        code, tests = where.grep_repo("jwt", limit=2)
        assert len(code) == 2
        assert len(tests) == 2

    def test_empty_query_returns_empty_pair(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty / falsy ``query`` short-circuits to ``([], [])`` (no subprocess)."""
        _make_src_tree(tmp_path, {"src/x.py": "JWT\n"})
        monkeypatch.chdir(tmp_path)
        assert where.grep_repo("", limit=20) == ([], [])

    def test_rg_missing_falls_back_to_grep(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ``rg`` is off PATH, ``grep_repo`` runs POSIX ``grep`` instead.

        Monkeypatches ``shutil.which`` so ``rg`` reports missing while
        ``grep`` reports a fake path (the argv builder never invokes the
        binary). Also monkeypatches ``subprocess.run`` to capture the
        argv and return canned grep-shaped output — assertion is on
        ``argv[0] == "grep"`` (not "rg").
        """
        _make_src_tree(
            tmp_path,
            {
                "src/foo.py": "JWT token\n",
                "tests/test_x.py": "JWT in tests\n",
            },
        )
        monkeypatch.chdir(tmp_path)

        captured: list[list[str]] = []

        import flow_engineering.where as where_mod

        def fake_which(name: str) -> str | None:
            if name == "rg":
                return None
            if name == "grep":
                return "/usr/bin/grep"
            return None

        def fake_run(argv: list[str], **kwargs: Any) -> Any:
            captured.append(argv)
            return subprocess.CompletedProcess(
                args=argv,
                returncode=0,
                stdout="src/foo.py:1:JWT token\ntests/test_x.py:1:JWT in tests\n",
                stderr="",
            )

        monkeypatch.setattr(where_mod.shutil, "which", fake_which)
        monkeypatch.setattr(where_mod.subprocess, "run", fake_run)

        code, tests = where.grep_repo("JWT", limit=20)
        assert len(captured) == 1
        assert captured[0][0] == "grep"
        assert any(h.path == "src/foo.py" for h in code)
        assert any(h.path == "tests/test_x.py" for h in tests)
