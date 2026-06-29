"""Cross-source retrieval backend for the ``flow where "<query>"`` subcommand.

REQ-V1.0.1..V1.0.4 — answer "where did I implement X?" in one hop by fanning
out to **repo code + tests**, **archived SDD specs**, and the **graphify graph
index** (fail-open). Output is plain text with explicit ``CODE / TESTS / SDD /
GRAPH`` sections. Zero new Python deps, zero ranking — deterministic grep
over files that already exist on disk.

Public surface (REQ-V1.0.1..V1.0.4) — added incrementally per strict TDD:
- :class:`WhereHit`
- :func:`grep_repo` + :func:`split_code_vs_tests` (D1, T1.2 + T1.4)
- :func:`grep_sdd_archive` (D2, T1.6)
- :func:`grep_graphify` (D3, T2.2)
- :class:`WhereResult` + :func:`where` orchestrator + :func:`render_text` (D4, T2.4)

All public functions are pure: subprocess + filesystem effects live behind
the ``_run_search`` private seam which tests monkeypatch.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_LIMIT: int = 20
DEFAULT_GRAPH_PATH: Path = Path(r"c:\dev\proyects\flow-engineering\graphify-out\graph.json")
"""Default path to the graphify ``graph.json`` snapshot (overridable via env).

Mirrors ``graphify_query.DEFAULT_GRAPH_JSON`` (graphify_query.py:32). Tests
override via ``monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", ...)`` so
the production default stays untouched.
"""
GRAPH_UNAVAILABLE_MESSAGE: str = "unavailable / no graph index found"
"""Exact render string for the GRAPH section when no graphify index is available.

The deterministic message is part of the public contract (D3 fail-open + D4
render): tests + downstream tooling can match on the literal text.
"""

_TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")


@dataclass(frozen=True)
class WhereHit:
    """A single retrieval hit.

    ``snippet`` is the trailing text after ``path:line:`` for SDD / GRAPH
    hits; ``None`` for CODE / TESTS where rg's ``path:line`` is the entire
    output row per design D1 + D4.
    """

    path: str
    line: int
    snippet: str | None = None


# ---------- D1: Repo grep helpers ----------


def _rg_argv() -> list[str] | None:
    """Return the rg argv prefix when rg is on PATH; ``None`` otherwise.

    Centralised so tests can monkeypatch the seam deterministically. The
    ``--no-heading`` flag strips the ``==> file:line <==`` separators rg
    emits in multi-file mode so we get one ``path:line:text`` row per hit.
    """
    if shutil.which("rg") is not None:
        return ["rg", "--line-number", "--no-heading", "--color", "never"]
    return None


def _grep_argv() -> list[str] | None:
    """Return the POSIX ``grep -rn`` argv prefix when grep is on PATH; ``None`` otherwise.

    Windows lacks ``grep`` natively; when ``rg`` is also missing we
    short-circuit to empty output so the consumer gets ``(no matches)``
    rather than a stack trace.
    """
    if shutil.which("grep") is not None:
        return ["grep", "-rn", "-H", "--color", "never", "--"]
    return None


def _run_search(query: str, paths: Iterable[str], cwd: Path) -> str:
    """Run the available search tool and return its stdout (utf-8).

    Picks ``rg`` first (``_rg_argv``); falls back to POSIX ``grep -rn``
    (``_grep_argv``). When neither tool is on PATH returns ``""`` so the
    callers render ``(no matches)`` instead of crashing — the project's
    fail-open discipline (``graphify_query._run_graphify_cli``).

    Exit-code semantics:
    - ``0`` → matches found (stdout parsed normally).
    - ``1`` → no matches (rg / grep convention; we treat this as ``""``).
    - ``2+`` → tool error (we also treat as ``""`` so the caller's
      fail-open contract holds). No exception is raised.
    """
    if not query:
        return ""
    for argv_builder in (_rg_argv, _grep_argv):
        argv_prefix = argv_builder()
        if argv_prefix is None:
            continue
        argv = [*argv_prefix, query, *paths]
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                cwd=str(cwd),
                check=False,
                encoding="utf-8",
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        if completed.returncode in (0, 1):
            return completed.stdout or ""
        return ""
    return ""


def _parse_hits(output: str) -> list[WhereHit]:
    """Parse rg-style ``path:line:col:text`` lines into :class:`WhereHit`.

    Skips malformed lines silently; the rg + grep union always produces
    ``>=3`` colon-separated fields per match, so a 2-field line is
    treated as garbage and dropped.
    """
    hits: list[WhereHit] = []
    for raw in output.splitlines():
        line = raw.rstrip("\r")
        if not line:
            continue
        parts = line.split(":", 3)
        if len(parts) < 3:
            continue
        path, ln = parts[0], parts[1]
        try:
            line_no = int(ln)
        except ValueError:
            continue
        # rg on Windows emits backslash-separated paths; normalise so the
        # `startswith("tests/")` partition check is portable. POSIX callers
        # are unaffected (no backslash in their output).
        path = path.replace("\\", "/")
        snippet: str | None = None
        if len(parts) == 4:
            # rg emits `path:line:col:text` — strip the column and keep the trailing text.
            snippet = parts[3].strip() or None
        elif len(parts) == 3:
            # grep emits `path:line:text` — `parts[2]` is the text.
            snippet = parts[2].strip() or None
        hits.append(WhereHit(path=path, line=line_no, snippet=snippet))
    return hits


# ---------- D1: Repo grep backend ----------


def grep_repo(
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    cwd: Path | None = None,
) -> tuple[list[WhereHit], list[WhereHit]]:
    """Return ``(code_hits, tests_hits)`` for ``query`` under ``cwd``.

    Splits hits by ``path.startswith("tests/")`` (D1 partition). Each
    bucket is capped at ``limit`` (default 20). Empty / missing
    ``query`` and rg-not-installed cases all return ``([], [])`` — never
    raises.
    """
    if not query:
        return ([], [])
    work_dir = Path(cwd) if cwd is not None else Path.cwd()
    stdout = _run_search(query, ["src", "tests"], work_dir)
    all_hits = _parse_hits(stdout)
    code_all, tests_all = split_code_vs_tests(all_hits)
    return (_apply_limit(code_all, limit), _apply_limit(tests_all, limit))


def _apply_limit(hits: list[WhereHit], limit: int) -> list[WhereHit]:
    """Truncate ``hits`` at ``limit`` entries (defensive copy)."""
    if limit <= 0:
        return []
    return hits[:limit]


def split_code_vs_tests(
    hits: list[WhereHit],
) -> tuple[list[WhereHit], list[WhereHit]]:
    """Partition ``hits`` by ``path.startswith("tests/")`` (D1 helper).

    Pure function — no I/O, no mutation of ``hits``. Order is preserved
    within each bucket (rg's natural ``path`` / ``line`` ascending order
    carries over).
    """
    code = [h for h in hits if not h.path.startswith("tests/")]
    tests = [h for h in hits if h.path.startswith("tests/")]
    return (code, tests)


# ---------- D2: SDD archive grep backend ----------


def _sdd_archive_dir(cwd: Path) -> Path:
    """Return the ``openspec/changes/archive`` directory under ``cwd``."""
    return cwd / "openspec" / "changes" / "archive"


def grep_sdd_archive(
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    cwd: Path | None = None,
) -> list[WhereHit]:
    """Search ``openspec/changes/archive/`` for ``query`` (D2).

    Missing ``query`` and a non-existent archive dir both yield
    ``[]`` — never raises. Hits are returned in rg's natural order
    (path-asc, line-asc) and capped at ``limit``.
    """
    if not query:
        return []
    work_dir = Path(cwd) if cwd is not None else Path.cwd()
    archive = _sdd_archive_dir(work_dir)
    if not archive.is_dir():
        return []
    # Pass the forward-slash relative path so rg's output is relative to
    # ``work_dir`` (mirrors the ``src/`` / ``tests/`` shape from grep_repo).
    stdout = _run_search(query, ["openspec/changes/archive"], work_dir)
    return _apply_limit(_parse_hits(stdout), limit)


# ---------- D3: Graphify fail-open backend ----------


def _tokenize(text: str) -> set[str]:
    """Lowercase token set for Jaccard comparison (mirrors ``graphify_query._tokenize``)."""
    if not text:
        return set()
    return {t.lower() for t in _TOKEN_PATTERN.findall(text)}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets; ``0.0`` when either is empty."""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def _node_tokens(node: dict[str, Any]) -> set[str]:
    """Build the token set for a graphify ``node`` entry.

    Concatenates ``label`` + ``id`` + ``source_file`` (same fields
    ``graphify_query._node_tokens`` touches; we duplicate the helper
    so ``where.py`` stays independently testable per design D3).
    """
    parts: list[str] = []
    for key in ("label", "source_file", "id"):
        value = node.get(key)
        if isinstance(value, str):
            parts.append(value)
    return _tokenize(" ".join(parts))


def _parse_graph_line(value: Any) -> int:
    """Extract a line number from a graphify ``source_location`` field.

    Accepts both ``int`` and strings containing digits (e.g. ``"42"``,
    ``"42:5"``, ``"L42"``). Returns ``0`` on parse failure so the
    render layer shows ``:0`` (the same convention as
    ``graphify_query._parse_line``).
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group(0))
    return 0


def grep_graphify(
    query: str,
    *,
    limit: int = DEFAULT_LIMIT,
    graph_path: Path | None = None,
) -> list[WhereHit] | None:
    """Score graphify nodes by Jaccard overlap with ``query`` (D3).

    Returns ``None`` (NOT an empty list) when the graph index is
    unavailable — missing file, ``OSError``, ``json.JSONDecodeError``,
    or an empty ``nodes`` list. Returning ``None`` lets the render
    layer emit the deterministic ``unavailable / no graph index found``
    string (D3 + D4 contract) so callers can distinguish "no graph at
    all" from "graph present but no matches".

    On valid input returns up to ``limit`` ``WhereHit`` entries sorted
    by Jaccard score descending. The hit's ``snippet`` carries the
    node ``label`` so the render output mirrors the GRAPH section shape
    from design D4.

    The ``graph_path`` parameter is resolved at call time from
    :data:`DEFAULT_GRAPH_PATH` (NOT captured as a default-value
    expression) so ``monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", ...)``
    can override the path per-test without monkeypatching this function.
    """
    if not query:
        return None
    resolved = graph_path if graph_path is not None else DEFAULT_GRAPH_PATH
    if not resolved.is_file():
        return None
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    nodes = data.get("nodes", []) if isinstance(data, dict) else []
    if not isinstance(nodes, list) or not nodes:
        return None

    query_tokens = _tokenize(query)
    scored: list[tuple[float, WhereHit]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_tokens = _node_tokens(node)
        score = _jaccard(query_tokens, node_tokens)
        if score <= 0:
            continue
        label = str(node.get("label", node.get("id", "")))
        scored.append(
            (
                score,
                WhereHit(
                    path=str(node.get("source_file", "")),
                    line=_parse_graph_line(node.get("source_location")),
                    snippet=label or None,
                ),
            )
        )
    scored.sort(key=lambda x: x[0], reverse=True)
    return [hit for _, hit in scored[:limit]]
