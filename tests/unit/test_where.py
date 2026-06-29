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


# ---------- T1.1 — REQ-V1.0.1: grep_repo no-match case ----------


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
