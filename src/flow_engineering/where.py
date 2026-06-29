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

import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LIMIT: int = 20


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
