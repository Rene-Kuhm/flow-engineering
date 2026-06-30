"""Dashboard data layer for ``flow workspace dashboard`` (Phase 5).

PR1 scope: subprocess wrappers + fetchers ONLY.

  - ``_run_subprocess_json`` — generic subprocess → JSON wrapper
  - ``fetch_project_list`` — DS1: ``flow projects ls --json``
  - ``fetch_status_summary`` — DS2: ``flow workspace status``
  - ``fetch_archived_projects`` — DS5: direct ``load_registry()`` read

Out of scope here (PR2 / PR3 territory):

  - filter / sort / color logic (PR2)
  - Rich rendering — Panel / Table / Group (PR2)
  - Click integration — ``flow workspace dashboard`` subcommand (PR3)

Pattern #536: observability first, interactivity second. The dashboard never
mutates state; the registry is read-only here and the only writers remain
``flow workspace {fix, archive, restore}`` (Phase 4 mutation gates preserved).

Pattern #538: one identity per command. ``flow workspace status`` keeps the
machine-readable identity (``--json``); the new ``flow workspace dashboard``
subcommand is the human-facing counterpart and deliberately omits ``--json``.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from flow_engineering.registry import load_registry

# ---------- Public exception types ----------
#
# One error class per failure mode, mirroring the ``RegistryError`` precedent
# (``src/flow_engineering/registry.py:96``). The Click layer (PR3) will catch
# these uniformly and print ``str(exc)`` to stderr before ``SystemExit(1)``.


class DashboardSubprocessError(RuntimeError):
    """Raised when the DS1/DS2 subprocess exits with non-zero status."""


class DashboardParseError(ValueError):
    """Raised when the DS1/DS2 subprocess output is not valid JSON."""


class DashboardFlowNotFoundError(FileNotFoundError):
    """Raised when the ``flow`` binary is not found on PATH.

    Subclasses ``FileNotFoundError`` so callers that already catch the OS
    exception still see the dashboard-specific context (the message explains
    that ``flow`` is missing, not some downstream file).
    """


# ---------- Subprocess transport ----------


def _run_subprocess_json(cmd: list[str], *, timeout: int = 10) -> dict[str, Any]:
    """Run ``cmd`` and return its stdout parsed as JSON.

    Mirrors the ``where.py:89`` ``_run_search`` shape but fails LOUD instead
    of open: every error mode produces a specific exception so the dashboard
    can never render an incomplete view. The CLI layer (PR3) is responsible
    for converting these to operator-friendly messages.

    Args:
        cmd: Command and arguments to run. ``cmd[0]`` is the binary name
            (typically ``"flow"``); kept keyword-only so test fakes stay
            honest about what they receive.
        timeout: Subprocess timeout in seconds. Defaults to 10s — long
            enough for typical ``flow`` invocations, short enough to avoid
            hanging the operator's terminal.

    Returns:
        Parsed JSON object (``dict``). Empty stdout parses to ``{}`` only
        if it is literally ``"{}"``; an empty string raises
        :class:`DashboardParseError` (a defensive default — empty output
        is never valid for DS1/DS2).

    Raises:
        DashboardFlowNotFoundError: ``cmd[0]`` not on PATH.
        DashboardSubprocessError: Returncode != 0 OR ``TimeoutExpired``.
        DashboardParseError: stdout is not parseable JSON.
    """
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DashboardFlowNotFoundError(
            f"`{cmd[0]}` binary not found on PATH. "
            f"Install flow-engineering or activate the venv that provides it."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DashboardSubprocessError(
            f"`{' '.join(cmd)}` timed out after {timeout}s"
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise DashboardSubprocessError(
            f"`{' '.join(cmd)}` exited with code {completed.returncode}: {stderr}"
        )

    try:
        payload: Any = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        preview = (completed.stdout or "")[:200]
        raise DashboardParseError(
            f"`{' '.join(cmd)}` returned invalid JSON: {exc}. "
            f"stdout preview: {preview!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise DashboardParseError(
            f"`{' '.join(cmd)}` returned JSON but the top-level value is "
            f"{type(payload).__name__}, not a dict."
        )
    return payload


# ---------- DS1 / DS2 / DS5 fetchers ----------


def fetch_project_list(*, flow_bin: str = "flow") -> list[dict[str, Any]]:
    """Fetch the project list via ``flow projects ls --json`` (DS1).

    Returns the envelope's ``projects[]`` field as a list of dicts. The
    envelope's other top-level fields (``version``, ``root``) are discarded
    by design — the dashboard's data layer trusts the v1 contract and
    doesn't re-validate it on every render.
    """
    payload = _run_subprocess_json([flow_bin, "projects", "ls", "--json"])
    projects = payload.get("projects", [])
    return [p for p in projects if isinstance(p, dict)]


def fetch_status_summary(*, flow_bin: str = "flow") -> dict[str, Any]:
    """Fetch the workspace status envelope via ``flow workspace status`` (DS2).

    Returns the parsed envelope (totals + projects + needs_attention). The
    dashboard renders the totals as the header and the needs_attention list
    drives the per-row color coding.
    """
    return _run_subprocess_json([flow_bin, "workspace", "status"])


def fetch_archived_projects() -> list[dict[str, Any]]:
    """Fetch archived projects from the registry (DS5 direct read).

    Reads ``~/.flow-engineering/registry.json`` via ``load_registry()``. The
    dashboard never calls ``save_registry_atomic`` — the registry is a
    read-only data source here; mutation stays in
    ``flow workspace {fix, archive, restore}``.

    Returns:
        List of ``ArchivedEntry``-shaped dicts (JSON-serializable — Path
        fields are POSIX strings via ``model_dump(mode="json")``). Empty
        list when the registry is missing (first-run UX) or has no
        archived entries.
    """
    registry = load_registry()
    return [entry.model_dump(mode="json") for entry in registry.archived]


__all__ = [
    "DashboardFlowNotFoundError",
    "DashboardParseError",
    "DashboardSubprocessError",
    "fetch_archived_projects",
    "fetch_project_list",
    "fetch_status_summary",
]
