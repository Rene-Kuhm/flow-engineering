"""Graphify hook for archive-time rebuild.

REQ-5: Incremental rebuild by default, full rebuild on structural changes.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Patterns that indicate a STRUCTURAL change (requires full rebuild)
_STRUCTURAL_PATTERNS = [
    re.compile(r"deleted file mode", re.IGNORECASE),  # git diff deletion marker
    re.compile(r"^D\s+", re.MULTILINE),  # short format deletion (D\tfilename)
    re.compile(r"^rename from\s+", re.MULTILINE),
    re.compile(r"^rename to\s+", re.MULTILINE),
    re.compile(r"package\.json", re.IGNORECASE),  # dep changes
    re.compile(r"pyproject\.toml", re.IGNORECASE),  # dep changes
    re.compile(r"tsconfig\.json", re.IGNORECASE),  # schema changes
    re.compile(r"schema\.prisma", re.IGNORECASE),
]


@dataclass
class GraphifyDecision:
    """Decision about which graphify command to run."""

    mode: str  # "incremental" or "full"
    command: list[str]
    estimated_cost_usd: float
    reason: str


def detect_structural_change(diff_text: str) -> bool:
    """Detect if a diff indicates a structural change requiring full rebuild."""
    return any(p.search(diff_text) for p in _STRUCTURAL_PATTERNS)


def decide_rebuild(
    sub_project_path: Path,
    diff_text: str = "",
    graphify_bin: str = "graphify",
) -> GraphifyDecision:
    """Decide whether to run incremental update or full rebuild.

    Returns the command to execute and an estimated cost.
    """
    is_structural = detect_structural_change(diff_text)
    if is_structural:
        return GraphifyDecision(
            mode="full",
            command=[graphify_bin, "extract", str(sub_project_path)],
            estimated_cost_usd=0.40,
            reason="Structural change detected (deleted files, renamed modules, or schema changes).",
        )
    return GraphifyDecision(
        mode="incremental",
        command=[graphify_bin, "update", str(sub_project_path)],
        estimated_cost_usd=0.05,
        reason="Non-structural change — incremental update is sufficient.",
    )


def run_graphify_hook(
    sub_project_path: Path,
    diff_text: str = "",
    graphify_bin: str = "graphify",
    dry_run: bool = False,
) -> tuple[int, str, GraphifyDecision]:
    """Execute the graphify hook. Returns (exit_code, stderr, decision).

    If dry_run is True, doesn't execute — just returns the decision.
    Returns 127 if the graphify binary is not found.
    """
    decision = decide_rebuild(sub_project_path, diff_text, graphify_bin)
    if dry_run:
        return 0, "", decision
    if not shutil.which(graphify_bin):
        return 127, f"graphify binary not found at {graphify_bin}", decision
    try:
        result = subprocess.run(
            decision.command,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stderr, decision
    except FileNotFoundError:
        return 127, f"graphify binary not found at {graphify_bin}", decision


def archive_graphify_hook(
    change_dir: Path,
    diff_text: str = "",
    graphify_bin: str = "graphify",
    dry_run: bool = False,
) -> tuple[int, str, GraphifyDecision]:
    """Archive-time hook. Determines affected sub-projects from cross_projects in state.

    For v1: applies graphify to the parent project (c:/dev/proyects/) directly.
    """
    state_file = change_dir / "state.json"
    if state_file.exists():
        import json

        state = json.loads(state_file.read_text(encoding="utf-8"))
        cross = state.get("cross_projects", [])
    else:
        cross = []

    # Determine target path: parent of flow-engineering/<change>/ is the project
    # .../flow-engineering/<change> -> .../flow-engineering -> .../
    target = change_dir.parent.parent if cross else change_dir.parent.parent
    return run_graphify_hook(target, diff_text, graphify_bin, dry_run)
