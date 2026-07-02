"""Health advisor primitives for ``flow workspace health``.

Library-first module per Constitution Article I. Public surface is
exported via ``__all__``.

This PR (sub-batches B-verdict-only + B-R9 + C-summary + C-filter) ships:
  - verdict math primitives (``_categorize_verdict`` + threshold
    constants)
  - R9 detector (``_detect_committed_tooling_dirs``) with hard-coded
    Python + Node pattern constants and a private ``_git_ls_files``
    subprocess seam
  - per-project record builder (``summarize_project_health``) +
    internal ``_summarize_per_project`` helper
  - stack-suppression constants (``_R7_SUPPRESSED_STACKS` +
    ``_R8_SUPPRESSED_STACKS``)
  - per-rule recommendation copy registry
    (``_R6_RECOMMENDATION`` / ``_R7_RECOMMENDATIONS`` /
    ``_R8_RECOMMENDATION`` / ``_R9_RECOMMENDATION``) +
    ``_recommendations_for`` dispatcher (private dependency of
    ``_summarize_per_project``; the recommendation-copy strings
    MUST be available for the per-project builder to populate the
    record's ``recommendations`` field, so the registry ships with
    C-summary). The ``TestRecommendationLock`` grep audit on
    these constants lands in PR2c.
  - output-only filter (``filter_health_by_rules``) which intersects
    each per-project record's ``triggers[]`` + ``recommendations[]``
    with a caller-supplied rule set and recomputes the verdict from
    the filtered triggers. Unknown rule tokens are silently ignored
    (lenient) so the filter does not break on stale state when new
    rules land via follow-up changes.

The recommendation-lock grep audit (``TestRecommendationLock``),
the workspace-wide fetch + Rich render, and the CLI wiring land in
later sub-batches (PR3 + PR4).
"""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path
from typing import Literal, cast

__all__ = [
    "_VERDICT_HEALTHY_MAX_TRIGGERS",
    "_VERDICT_CRITICAL_MIN_TRIGGERS",
    "_R9_PYTHON_PATTERNS",
    "_R9_NODE_PATTERNS",
    "_R7_SUPPRESSED_STACKS",
    "_R8_SUPPRESSED_STACKS",
    "_R6_RECOMMENDATION",
    "_R7_RECOMMENDATIONS",
    "_R8_RECOMMENDATION",
    "_R9_RECOMMENDATION",
    "_categorize_verdict",
    "_detect_committed_tooling_dirs",
    "_summarize_per_project",
    "_recommendations_for",
    "summarize_project_health",
    "filter_health_by_rules",
    "fetch_workspace_health",
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


# ---------------------------------------------------------------------------
# Stack-suppression sets (REQ-WORKSPACE-HEALTH-R7-TESTS-INFRA + R8-OPENSPEC).
# ---------------------------------------------------------------------------
#
# R7 is suppressed when the project's detected stack has no canonical
# test runner to recommend (Nix/Unknown). R8 is suppressed outside the
# Python/Go/Rust scope (mirrors R4 from the status surface). R9 has no
# stack guard — any stack can have committed tooling dirs.

_R7_SUPPRESSED_STACKS: frozenset[str] = frozenset({"Nix", "Unknown"})

_R8_SUPPRESSED_STACKS: frozenset[str] = frozenset(
    {"Astro", "Next", "WXT", "Node", "Flutter", "Nix", "Unknown"}
)


# ---------------------------------------------------------------------------
# Recommendation copy (REQ-WORKSPACE-HEALTH-READ-ONLY).
# ---------------------------------------------------------------------------
#
# LOCKED to references of existing ``flow workspace {fix, archive,
# restore, new-project}`` verbs + plain English. NEVER raw filesystem
# mutations (``rm -rf``, ``git rm -r --cached``, ``--force``). The
# locked strings are exported via ``__all__`` so the
# recommendation-lock grep test can audit them statically.

_R6_RECOMMENDATION: str = (
    "Add a 'README.md' (or 'README.rst') at the project root "
    "describing purpose and usage; consult 'flow workspace fix' for "
    "remediation tips."
)

_R7_RECOMMENDATIONS: dict[str, str] = {
    "Python": (
        "Add a 'tests/' directory and a '[tool.pytest]' section in "
        "'pyproject.toml', or run 'flow workspace new-project <name> "
        "--cross-projects <this>' to scaffold SDD-aligned test infra."
    ),
    "Go": (
        "Add a 'go test ./...' entry; existing 'go.mod' is sufficient "
        "if tests live in '<pkg>_test.go' files alongside packages; "
        "see 'flow workspace fix' for details."
    ),
    "Rust": (
        "'cargo test' is automatic on a 'Cargo.toml'; ensure at least "
        "one 'tests/*.rs' file exists; consult 'flow workspace fix' "
        "for the standard layout."
    ),
    "Node": (
        "Add a 'vitest' or 'jest' config and a 'tests/' directory; "
        "'package.json' already declares a 'test' script; see "
        "'flow workspace fix' for the Node setup."
    ),
}

_R8_RECOMMENDATION: str = (
    "OpenSpec is missing — consider 'flow workspace new-project <name> "
    "--cross-projects <this>' or copy the 'openspec/' tree from a "
    "sibling SDD-adjacent project."
)

_R9_RECOMMENDATION: str = (
    "Consider untracking tooling dirs: append the offending patterns to "
    "'.gitignore' and consult 'flow workspace fix' for remediation "
    "(operator's discretion — 'flow workspace health' does NOT execute "
    "this)."
)


# ---------------------------------------------------------------------------
# Per-project record builder (REQ-WORKSPACE-HEALTH-SURFACE).
# ---------------------------------------------------------------------------
#
# The v1 envelope schema is documented at design §5.3. This module
# does NOT compose the workspace-wide envelope (that's PR3's
# ``fetch_workspace_health``). It exposes ``summarize_project_health``
# so PR3 + PR4 can call it per project without re-deriving the
# stack-suppression logic.


def _summarize_per_project(
    name: str,
    path: str,
    *,
    stack: str,
    has_readme: bool,
    has_pytest_config: bool,
    has_openspec: bool,
    tooling_hits: list[str],
) -> dict[str, object]:
    """Build the per-project v1 record for the health envelope.

    Internal helper used by ``summarize_project_health`` to keep the
    public surface's signature small (just markers + tooling_hits).

    Trigger computation (per spec REQ-WORKSPACE-HEALTH-VERDICT-MATH +
    R6/R7/R8/R9 + stack-guard):

      - R6: missing README → ``"R6"`` in ``triggers``
      - R7: missing pytest infra → ``"R7"`` in ``triggers``,
        SUPPRESSED when ``stack in _R7_SUPPRESSED_STACKS``
      - R8: missing openspec → ``"R8"`` in ``triggers``,
        SUPPRESSED when ``stack in _R8_SUPPRESSED_STACKS``
      - R9: any tooling hits → ``"R9"`` in ``triggers`` (no stack
        guard — any stack can have committed tooling dirs)

    Recommendations list contains one copy per TRIGGERED (not
    suppressed) rule. Suppressed rules are surfaced in a separate
    ``suppressed`` list so operators understand WHY no verdict hit
    a stack-guard rule (per spec REQ-WORKSPACE-HEALTH-R8-OPENSPEC).
    """
    triggers: list[str] = []
    suppressed: list[str] = []
    # R6
    if not has_readme:
        triggers.append("R6")
    # R7
    if stack in _R7_SUPPRESSED_STACKS:
        suppressed.append("R7")
    elif not has_pytest_config:
        triggers.append("R7")
    # R8
    if stack in _R8_SUPPRESSED_STACKS:
        suppressed.append("R8")
    elif not has_openspec:
        triggers.append("R8")
    # R9 — no stack guard; any tooling hit counts
    if tooling_hits:
        triggers.append("R9")
    verdict = _categorize_verdict(triggers)
    recommendations = _recommendations_for(triggers, stack)
    return {
        "name": name,
        "path": path,
        "stack": stack,
        "verdict": verdict,
        "triggers": triggers,
        "recommendations": recommendations,
        "suppressed": suppressed,
    }


def summarize_project_health(
    markers: dict[str, object],
    *,
    tooling_hits: list[str] | None = None,
) -> dict[str, object]:
    """Build the per-project v1 record from extended markers + tooling hits.

    Public entry point (REQ-WORKSPACE-HEALTH-SURFACE). Reads the
    additive keys from ``_detect_project_markers`` (R6 source =
    ``has_readme``; R7 source = ``has_pytest_config``; R8 source =
    ``has_openspec``) plus the R9 source from
    ``_detect_committed_tooling_dirs`` (the ``tooling_hits`` list).

    Args:
        markers: Per-project marker dict from
            ``_detect_project_markers``. Must include ``name``,
            ``path``, ``stack``, ``has_readme``, ``has_pytest_config``,
            and ``has_openspec``.
        tooling_hits: Non-empty list → R9 triggered. ``[]`` (default)
            → R9 not triggered.

    Returns:
        A new per-project v1 record (see ``_summarize_per_project``).
    """
    return _summarize_per_project(
        name=str(markers.get("name", "")),
        path=str(markers.get("path", "")),
        stack=str(markers.get("stack", "Unknown")),
        has_readme=bool(markers.get("has_readme", False)),
        has_pytest_config=bool(markers.get("has_pytest_config", False)),
        has_openspec=bool(markers.get("has_openspec", False)),
        tooling_hits=list(tooling_hits) if tooling_hits else [],
    )


def _recommendations_for(triggers: list[str], stack: str) -> list[str]:
    """Build the per-project recommendation list (locked copy).

    Only TRIGGERED rules produce recommendations. Suppressed rules
    are NOT in the recommendation list (they're surfaced separately
    via the ``suppressed`` field per spec REQ-WORKSPACE-HEALTH-R8).

    R7 recommendations are stack-specific (Python/Go/Rust/Node).
    For Nix/Unknown stacks, R7 is suppressed and produces no
    recommendation (no canonical hint available).

    Copy lock (REQ-WORKSPACE-HEALTH-READ-ONLY):
      - NEVER raw filesystem mutations (``rm -rf``, ``git rm``,
        ``--force``)
      - ONLY existing ``flow workspace {fix, archive, restore,
        new-project}`` verbs + plain English
      - A test (``TestRecommendationLock``, lands in PR2c) greps
        the output of this function for the forbidden tokens and
        fails the build if any are present.
    """
    out: list[str] = []
    for trigger in triggers:
        if trigger == "R6":
            out.append(_R6_RECOMMENDATION)
        elif trigger == "R7":
            rec = _R7_RECOMMENDATIONS.get(stack)
            if rec:
                out.append(rec)
        elif trigger == "R8":
            out.append(_R8_RECOMMENDATION)
        elif trigger == "R9":
            out.append(_R9_RECOMMENDATION)
    return out


# ---------------------------------------------------------------------------
# Output-only filter (REQ-WORKSPACE-HEALTH-ENVELOPE).
# ---------------------------------------------------------------------------
#
# Matches the dashboard's ``filter_by_rules`` shape but operates on
# the health envelope (per-project ``triggers[]`` +
# ``recommendations[]``). Unknown rule tokens are silently ignored
# (lenient filter — the underlying detection ALWAYS runs; only the
# output is filtered).


def filter_health_by_rules(
    projects: list[dict[str, object]],
    rules: list[str],
) -> list[dict[str, object]]:
    """Return a NEW projects list with ``triggers[]`` + ``recommendations[]``
    filtered to the named rules.

    For each project:
      - ``triggers[]`` is intersected with the rule set
      - ``recommendations[]`` is filtered in lock-step to match
      - ``suppressed[]`` is left untouched (it's the operator-facing
        "why no verdict hit this rule" signal per spec)
      - ``verdict`` is recomputed from the filtered triggers per
        REQ-WORKSPACE-HEALTH-VERDICT-MATH so a project whose
        filtered triggers drop to zero reports ``HEALTHY``

    Unknown rule tokens in ``rules`` are silently ignored (they
    contribute nothing to the filter set but do NOT raise). This is
    intentionally lenient (different from ``dashboard.filter_by_rules``
    which raises ``ValueError`` on unknown) because the health
    envelope is additive: future ``R10``-style rules land via
    follow-up changes and the filter must not break on stale state.

    If all tokens in ``rules`` are unknown (e.g. ``["R99"]``), the
    effective filter set is empty and the function returns the
    projects unchanged — this is the "unknown token keeps all"
    defensive behavior (no data loss for typo'd filter flags).

    Args:
        projects: Per-project v1 records (from
            ``summarize_project_health`` or the workspace-wide
            envelope's ``projects`` field).
        rules: Rule names to keep (``["R6", "R7", "R8", "R9"]`` or
            any subset). Unknown tokens are ignored. Case-insensitive
            (uppercased internally).

    Returns:
        A NEW list of per-project dicts with filtered triggers +
        recommendations + recomputed verdict.
    """
    if not rules:
        return list(projects)
    valid_rules = {"R6", "R7", "R8", "R9"}
    rule_set = {r.upper() for r in rules if r.upper() in valid_rules}
    if not rule_set:
        # All tokens unknown → defensive no-op (preserves the
        # "unknown token keeps all" contract per the test)
        return list(projects)
    filtered: list[dict[str, object]] = []
    for entry in projects:
        raw_triggers = entry.get("triggers", [])
        raw_recommendations = entry.get("recommendations", [])
        triggers = cast(list[str], raw_triggers) if isinstance(raw_triggers, list) else []
        recommendations = (
            cast(list[str], raw_recommendations)
            if isinstance(raw_recommendations, list)
            else []
        )
        # Pair-trigger filter: each recommendation is 1:1 with a
        # trigger from ``_recommendations_for`` — keep both lists
        # aligned by walking them in lock-step.
        kept_triggers: list[str] = []
        kept_recommendations: list[str] = []
        for trig, rec in zip(triggers, recommendations, strict=False):
            if trig in rule_set:
                kept_triggers.append(trig)
                kept_recommendations.append(rec)
        new_entry = dict(entry)
        new_entry["triggers"] = kept_triggers
        new_entry["recommendations"] = kept_recommendations
        new_entry["verdict"] = _categorize_verdict(kept_triggers)
        filtered.append(new_entry)
    return filtered


def fetch_workspace_health(root: Path) -> dict[str, object]:
    """Return the locked v1 envelope for a workspace root.

    Top-level keys in fixed order: version, root, projects, totals.
    No ``generated_at`` field (Constitution Article IV byte-determinism).
    Raises FileNotFoundError when resolved root is not a directory.

    WU3.1 ships the envelope skeleton only (projects=[], totals zeros).
    WU3.2 + WU3.3 fill them in.
    """
    resolved = root.resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"projects root not found: {resolved}")
    return {
        "version": "1",
        "root": str(resolved),
        "projects": [],
        "totals": {"healthy": 0, "attention": 0, "critical": 0},
    }

