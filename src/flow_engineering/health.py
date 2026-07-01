"""Health advisor primitives for ``flow workspace health``.

Library-first module per Constitution Article I. Public surface is
exported via ``__all__``.

This PR (sub-batch B-verdict-only + B-R9) ships:
  - verdict math primitives (``_categorize_verdict`` + threshold
    constants)
  - R9 detector (``_detect_committed_tooling_dirs``) with hard-coded
    Python + Node pattern constants and a private ``_git_ls_files``
    subprocess seam

The recommendation copy, the summary builder, the filter, the
envelope composer, the fetch, and the Rich renderer land in later
sub-batches (PR2/C, PR3, PR4).
"""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path
from typing import Literal

__all__ = [
    "_VERDICT_HEALTHY_MAX_TRIGGERS",
    "_VERDICT_CRITICAL_MIN_TRIGGERS",
    "_R9_PYTHON_PATTERNS",
    "_R9_NODE_PATTERNS",
    "_categorize_verdict",
    "_detect_committed_tooling_dirs",
]


# ---------------------------------------------------------------------------
# Verdict math constants (REQ-WORKSPACE-HEALTH-VERDICT-MATH).
# ---------------------------------------------------------------------------

_VERDICT_HEALTHY_MAX_TRIGGERS: int = 0
_VERDICT_CRITICAL_MIN_TRIGGERS: int = 3


# ---------------------------------------------------------------------------
# R9 pattern constants (REQ-WORKSPACE-HEALTH-R9-COMMITTED-TOOLING).
# ---------------------------------------------------------------------------
#
# HARDCODED for MVP. Per the spec, extending R9 patterns via config is
# deferred to ``workspace-health-advisor-r9-config`` (Engram #1903).
# Operators wanting custom patterns MUST wait for that change.

_R9_PYTHON_PATTERNS: tuple[str, ...] = (
    ".venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "dist/",
    "build/",
    "*.egg-info/",
)

_R9_NODE_PATTERNS: tuple[str, ...] = (
    "node_modules/",
    "dist/",
    ".next/",
)

# Deduplicated union (preserves insertion order; ``dist/`` is shared
# across both tuples but emitted only once in the R9 hits list).
_R9_ALL_PATTERNS: tuple[str, ...] = tuple(
    dict.fromkeys(_R9_PYTHON_PATTERNS + _R9_NODE_PATTERNS)
)


# ---------------------------------------------------------------------------
# Pure helpers.
# ---------------------------------------------------------------------------


def _categorize_verdict(
    triggers: list[str],
) -> Literal["HEALTHY", "NEEDS-ATTENTION", "CRITICAL"]:
    """Pure threshold mapping (REQ-WORKSPACE-HEALTH-VERDICT-MATH).

    Count -> verdict:
      - 0             -> HEALTHY
      - 1 or 2        -> NEEDS-ATTENTION
      - 3 or more     -> CRITICAL

    The function is pure (no I/O, no time-dependent state) so it
    can be RED-tested in isolation. The threshold constants
    ``_VERDICT_HEALTHY_MAX_TRIGGERS`` and ``_VERDICT_CRITICAL_MIN_TRIGGERS``
    document the bands and are reused by later sub-batches for the
    workspace-wide aggregate.
    """
    count = len(triggers)
    if count <= _VERDICT_HEALTHY_MAX_TRIGGERS:
        return "HEALTHY"
    if count < _VERDICT_CRITICAL_MIN_TRIGGERS:
        return "NEEDS-ATTENTION"
    return "CRITICAL"


# ---------------------------------------------------------------------------
# R9 detector (REQ-WORKSPACE-HEALTH-R9-COMMITTED-TOOLING).
# ---------------------------------------------------------------------------


def _git_ls_files(*, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run ``git ls-files`` with capture, text decoding, and a 5s timeout.

    Local subprocess seam (mirrors ``cli._git`` semantics) so that
    ``health.py`` stays independent of ``cli.py`` and avoids a
    circular import once PR3/PR4 wire the CLI handler to import
    from ``health``.

    Returns the raw ``CompletedProcess``; the caller branches on
    ``returncode`` (non-zero → graceful ``[]`` return).
    """
    return subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(cwd),
        check=False,
        timeout=5,
    )


def _matches_glob(relpath: str, pattern: str) -> bool:
    """Return True if ``relpath`` matches the ``fnmatch`` pattern.

    Thin wrapper around stdlib ``fnmatch.fnmatch`` so the detector
    stays declarative. Patterns ending in ``/`` (e.g. ``".venv/"``)
    match any tracked path that STARTS with that prefix;
    ``fnmatch`` treats ``/`` as a normal character, so a tracked
    path like ``.venv/lib/foo.py`` does NOT literally match
    ``".venv/"`` — hence the explicit ``startswith`` short-circuit
    below for directory-prefix patterns.

    For the wildcard ``*.egg-info/`` pattern, ``fnmatch`` handles
    the leading ``*`` correctly; ``fnmatch.fnmatch("foo.egg-info/PKG-INFO",
    "*.egg-info/")`` returns True.
    """
    if pattern.endswith("/") and not pattern.startswith("*"):
        return relpath.startswith(pattern)
    return fnmatch.fnmatch(relpath, pattern)


def _detect_committed_tooling_dirs(project_dir: Path) -> list[str]:
    """R9 detector (REQ-WORKSPACE-HEALTH-R9-COMMITTED-TOOLING).

    Runs ONE ``git ls-files`` subprocess per project and post-filters
    the output against the hard-coded Python + Node pattern constants
    (``_R9_PYTHON_PATTERNS`` + ``_R9_NODE_PATTERNS``). Returns a list
    of ``"{pattern} ({count} files)"`` strings — one per pattern with
    at least one matching tracked file.

    Graceful fallback (returns ``[]``, never raises):
      - no ``.git/`` directory at the project root
      - ``git`` not installed / corrupt ``.git/`` / subprocess error
      - no tracked files match any pattern

    Per-spec scenario coverage:
      - clean project → ``[]``
      - ``.venv/`` tracked → ``[".venv/ (N files)"]``
      - ``node_modules/`` tracked → ``["node_modules/ (N files)"]``
      - mixed Python + Node → both listed
      - non-git / corrupt ``.git/`` → ``[]``
    """
    if not (project_dir / ".git").is_dir():
        return []
    try:
        cp = _git_ls_files(cwd=project_dir)
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return []
    if cp.returncode != 0 or not cp.stdout:
        return []
    tracked = cp.stdout.splitlines()
    hits: list[str] = []
    emitted: set[str] = set()
    for pattern in _R9_ALL_PATTERNS:
        if pattern in emitted:
            continue
        count = sum(1 for line in tracked if _matches_glob(line, pattern))
        if count > 0:
            hits.append(f"{pattern} ({count} files)")
            emitted.add(pattern)
    return hits
