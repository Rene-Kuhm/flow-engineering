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

    def test_limit_caps_each_bucket(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    def test_rg_and_grep_missing_falls_back_to_python_search(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Windows service runners without rg/grep still get real search hits."""
        _make_src_tree(
            tmp_path,
            {
                "src/foo.py": "def make_jwt():\n    return 'token'\n",
                "tests/test_x.py": "def test_jwt():\n    pass\n",
            },
        )
        monkeypatch.chdir(tmp_path)

        import flow_engineering.where as where_mod

        monkeypatch.setattr(where_mod.shutil, "which", lambda _name: None)

        code, tests = where.grep_repo("jwt", limit=20)
        assert [h.path for h in code] == ["src/foo.py"]
        assert [h.path for h in tests] == ["tests/test_x.py"]


# ---------- T1.3 / T1.4 — REQ-V1.0.1: split_code_vs_tests ----------


class TestSplitCodeVsTests:
    """REQ-V1.0.1: ``split_code_vs_tests`` partitions hits by path prefix."""

    def test_all_code_returns_empty_tests_bucket(self) -> None:
        """No ``tests/`` paths → empty tests bucket; code bucket unchanged."""
        hits = [
            where.WhereHit(path="src/a.py", line=1, snippet=None),
            where.WhereHit(path="src/b.py", line=2, snippet=None),
        ]
        code, tests = where.split_code_vs_tests(hits)
        assert code == hits
        assert tests == []

    def test_all_tests_returns_empty_code_bucket(self) -> None:
        """All paths under ``tests/`` → empty code bucket; tests unchanged."""
        hits = [
            where.WhereHit(path="tests/test_a.py", line=1, snippet=None),
            where.WhereHit(path="tests/test_b.py", line=2, snippet=None),
        ]
        code, tests = where.split_code_vs_tests(hits)
        assert code == []
        assert tests == hits

    def test_mixed_sorts_each_bucket_deterministically(self) -> None:
        """Mixed hits: each bucket is returned in deterministic path/line order."""
        hits = [
            where.WhereHit(path="src/a.py", line=1, snippet=None),
            where.WhereHit(path="tests/test_a.py", line=1, snippet=None),
            where.WhereHit(path="src/b.py", line=2, snippet=None),
            where.WhereHit(path="tests/test_b.py", line=2, snippet=None),
        ]
        code, tests = where.split_code_vs_tests(hits)
        assert [h.path for h in code] == ["src/a.py", "src/b.py"]
        assert [h.path for h in tests] == ["tests/test_a.py", "tests/test_b.py"]

    def test_mixed_hits_are_sorted_within_each_bucket(self) -> None:
        """Out-of-order hits are returned deterministically by path, line, and snippet."""
        hits = [
            where.WhereHit(path="tests/test_b.py", line=2, snippet="second"),
            where.WhereHit(path="src/b.py", line=2, snippet="second"),
            where.WhereHit(path="tests/test_a.py", line=3, snippet="later"),
            where.WhereHit(path="src/a.py", line=4, snippet="later"),
            where.WhereHit(path="src/a.py", line=1, snippet="earlier"),
            where.WhereHit(path="tests/test_a.py", line=1, snippet="first"),
        ]

        code, tests = where.split_code_vs_tests(hits)

        assert code == [
            where.WhereHit(path="src/a.py", line=1, snippet="earlier"),
            where.WhereHit(path="src/a.py", line=4, snippet="later"),
            where.WhereHit(path="src/b.py", line=2, snippet="second"),
        ]
        assert tests == [
            where.WhereHit(path="tests/test_a.py", line=1, snippet="first"),
            where.WhereHit(path="tests/test_a.py", line=3, snippet="later"),
            where.WhereHit(path="tests/test_b.py", line=2, snippet="second"),
        ]


# ---------- T1.5 — REQ-V1.0.2: grep_sdd_archive ----------


class TestGrepSddArchive:
    """REQ-V1.0.2: ``grep_sdd_archive`` reads ``openspec/changes/archive/``."""

    def test_one_hit_from_fixture_md(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A single match in a fixture `.md` is reported with snippet."""
        archive = tmp_path / "openspec" / "changes" / "archive" / "2026-01-01-foo"
        archive.mkdir(parents=True)
        (archive / "spec.md").write_text(
            "the jwt validator pattern handles X.\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        hits = where.grep_sdd_archive("jwt", limit=20)
        assert len(hits) == 1
        assert hits[0].path == "openspec/changes/archive/2026-01-01-foo/spec.md"
        assert hits[0].line == 1
        assert hits[0].snippet is not None
        assert "jwt" in hits[0].snippet.lower()

    def test_missing_dir_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No ``openspec/changes/archive`` dir → ``[]`` (no error)."""
        monkeypatch.chdir(tmp_path)
        assert where.grep_sdd_archive("anything", limit=20) == []

    def test_limit_caps_hits(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """``limit=N`` truncates the result list at N hits."""
        archive = tmp_path / "openspec" / "changes" / "archive"
        for i in range(5):
            sub = archive / f"change-{i}"
            sub.mkdir(parents=True)
            (sub / "spec.md").write_text("jwt token\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        hits = where.grep_sdd_archive("jwt", limit=2)
        assert len(hits) == 2


# ---------- T2.1 — REQ-V1.0.3: grep_graphify ----------


class TestGrepGraphify:
    """REQ-V1.0.3: ``grep_graphify`` returns ``None`` when graph.json unavailable."""

    def test_missing_file_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-existent ``graph.json`` → ``None`` (caller renders unavailable)."""
        monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", tmp_path / "ghost.json")
        assert where.grep_graphify("jwt", limit=20) is None

    def test_malformed_json_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed JSON in ``graph.json`` → ``None`` (no stack trace)."""
        graph = tmp_path / "graph.json"
        graph.write_text("{ this is not valid JSON ", encoding="utf-8")
        monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", graph)
        assert where.grep_graphify("jwt", limit=20) is None

    def test_empty_nodes_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valid JSON with empty ``nodes`` array → ``None`` (nothing to score)."""
        graph = tmp_path / "graph.json"
        graph.write_text(json.dumps({"nodes": []}), encoding="utf-8")
        monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", graph)
        assert where.grep_graphify("jwt", limit=20) is None

    def test_valid_nodes_return_scored_hits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valid JSON with nodes → list of ``WhereHit`` ranked by score desc."""
        graph = tmp_path / "graph.json"
        graph.write_text(
            json.dumps(
                {
                    "nodes": [
                        {
                            "id": "src-auth-jwt",
                            "label": "auth.jwt",
                            "source_file": "src/auth.py",
                            "source_location": "42",
                        },
                        {
                            "id": "src-orders",
                            "label": "orders",
                            "source_file": "src/orders.py",
                            "source_location": "12",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", graph)
        hits = where.grep_graphify("jwt", limit=20)
        assert hits is not None
        assert len(hits) == 1
        assert hits[0].path == "src/auth.py"
        assert hits[0].line == 42
        assert hits[0].snippet is not None
        assert "auth.jwt" in hits[0].snippet


# ---------- T2.3 — REQ-V1.0.4: where() orchestrator + render_text() ----------


class TestWhereOrchestrator:
    """REQ-V1.0.4: ``where()`` + ``render_text()`` produce the structured output contract."""

    def test_render_text_sections_in_canonical_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All 4 sections render in ``CODE / TESTS / SDD / GRAPH`` order."""
        _make_src_tree(
            tmp_path,
            {
                "src/auth.py": "def make_jwt():\n    return 'token'\n",
                "tests/test_auth.py": "def test_jwt():\n    pass\n",
            },
        )
        archive = tmp_path / "openspec" / "changes" / "archive" / "x"
        archive.mkdir(parents=True)
        (archive / "spec.md").write_text("jwt mention here\n", encoding="utf-8")
        graph = tmp_path / "graph.json"
        graph.write_text(
            json.dumps(
                {
                    "nodes": [
                        {
                            "id": "src-auth-jwt",
                            "label": "auth.jwt",
                            "source_file": "src/auth.py",
                            "source_location": "1",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", graph)

        result = where.where("jwt", limit=20)
        text = where.render_text(result)
        assert text.index("CODE") < text.index("TESTS") < text.index("SDD") < text.index("GRAPH")

    def test_empty_section_renders_no_matches_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty sections still render — ``(no matches)`` line in place."""
        # Empty tree — every backend produces zero hits.
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", tmp_path / "nope.json")
        result = where.where("nothing-matches-x", limit=20)
        text = where.render_text(result)
        assert "(no matches)" in text
        assert "CODE" in text
        assert "TESTS" in text
        assert "SDD" in text
        assert "GRAPH" in text

    def test_no_graph_flag_skips_graph_section(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``--no-graph`` makes GRAPH section disappear entirely (not just empty)."""
        _make_src_tree(tmp_path, {"src/auth.py": "jwt here\n"})
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", tmp_path / "nope.json")
        result = where.where("jwt", limit=20, no_graph=True)
        assert result.graph is None
        text = where.render_text(result)
        assert "GRAPH" not in text

    def test_graph_unavailable_renders_exact_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing ``graph.json`` → GRAPH section prints the exact fail-open token."""
        _make_src_tree(tmp_path, {"src/auth.py": "jwt here\n"})
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", tmp_path / "missing.json")
        result = where.where("jwt", limit=20)
        text = where.render_text(result)
        assert where.GRAPH_UNAVAILABLE_MESSAGE in text
        assert text.count(where.GRAPH_UNAVAILABLE_MESSAGE) == 1

    def test_limit_caps_each_backend_independently(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``limit=1`` → CODE / TESTS / SDD each capped at 1; GRAPH if present uses limit too."""
        _make_src_tree(
            tmp_path,
            {
                "src/a.py": "jwt one\njwt two\n",
                "tests/ta.py": "jwt one\njwt two\n",
            },
        )
        archive = tmp_path / "openspec" / "changes" / "archive" / "x"
        archive.mkdir(parents=True)
        (archive / "spec.md").write_text("jwt one\njwt two\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = where.where("jwt", limit=1)
        assert len(result.code) <= 1
        assert len(result.tests) <= 1
        assert len(result.sdd) <= 1


# ---------- HOTFIX-V1.0.5: ASCII-safe output for Windows cp1252 ----------


class TestAsciiSafeOutput:
    """Regression tests for Windows cp1252 console compatibility.

    Reproduces the ``UnicodeEncodeError`` bug from the user smoke test:
    ``flow where "DriftEvent"`` and ``flow where "PromptRenderError"`` crashed
    on Windows because snippets from ``rg`` could contain Unicode (e.g. ``✅``,
    ``→``) and ``_format_hit`` emitted an em-dash (``—``) in the GRAPH section.
    The Windows ``cp1252`` console codec cannot encode ``✅``/``→``, raising
    ``UnicodeEncodeError`` on ``print``. Fix lands in :func:`where._ascii_safe`
    + the em-dash → ``--`` substitution in :func:`where._format_hit`.
    """

    def test_format_hit_with_unicode_snippet_is_ascii_safe(self) -> None:
        """Snippet with ``✅`` + ``→`` must be ASCII-encoded for cp1252.

        Without the fix, ``✅`` and ``→`` survive into the formatted row and
        raise ``UnicodeEncodeError`` when the Windows console tries to encode
        them as cp1252.
        """
        hit = where.WhereHit(path="src/whatever.py", line=42, snippet="# ✅ TODO → fix this")
        formatted = where._format_hit(hit, section="CODE")
        assert "✅" not in formatted
        assert "→" not in formatted
        assert "?" in formatted  # `?` is the cp1252 replacement marker

    def test_format_hit_graph_section_uses_ascii_dash(self) -> None:
        """GRAPH section no longer emits em-dash (``—``); uses ``--`` instead.

        Em-dash is in cp1252 but the snippet content is not — emitting ``--``
        keeps the section visually distinct AND cp1252-safe in a single move.
        """
        hit = where.WhereHit(path="graph.json", line=1, snippet="node_label")
        formatted = where._format_hit(hit, section="GRAPH")
        assert "—" not in formatted
        assert "-- " in formatted

    def test_render_text_passes_through_cp1252_encoding(self) -> None:
        """``render_text`` output must encode as cp1252 without raising.

        This is the regression test for the user-reported
        ``UnicodeEncodeError`` bug. We build a :class:`WhereResult` whose
        snippets carry real-world Unicode (``✅``, ``→``, em-dash) — the
        kind a Windows ``flow where`` smoke test produces — and verify the
        fully rendered text encodes cleanly under ``cp1252`` strict mode.
        Mirrors what the Windows console does on ``sys.stdout.write(output)``.
        """
        result = where.WhereResult(
            code=[where.WhereHit(path="src/a.py", line=1, snippet="# ✅ TODO")],
            tests=[where.WhereHit(path="tests/b.py", line=2, snippet="# → arrow")],
            sdd=[where.WhereHit(path="openspec/x.md", line=3, snippet="# — em-dash")],
            graph=None,  # graphify unavailable
            graph_skipped=False,
        )
        output = where.render_text(result)

        try:
            encoded = output.encode("cp1252", errors="strict")
        except UnicodeEncodeError as exc:
            pytest.fail(f"render_text output is NOT ASCII-safe for cp1252: {exc}")
        # Sanity: encoded payload is non-empty and decodes back losslessly.
        assert len(encoded) > 0
        assert encoded.decode("cp1252") == output
