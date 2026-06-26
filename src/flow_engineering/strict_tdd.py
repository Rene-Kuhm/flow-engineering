"""Strict TDD prompt injection.

REQ-7: Strict TDD mode is the default for compatible projects.
"""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path
from typing import Any

STRICT_TDD_PROMPT = (
    "STRICT TDD MODE IS ACTIVE. Test runner: {test_command}. "
    "You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."
)


def load_sdd_init(project_dir: Path) -> dict[str, Any] | None:
    """Load sdd-init/{project} observation if available.

    Reads the first .md file in sdd-init/ and looks for strict_tdd markers.
    """
    sdd_init_dir = project_dir / "sdd-init"
    if not sdd_init_dir.exists():
        return None
    md_files = sorted(sdd_init_dir.glob("*.md"))
    if not md_files:
        return None
    content = md_files[0].read_text(encoding="utf-8")
    on_markers = (
        "strict_tdd: true",
        "Strict TDD: ON",
        "Strict TDD:** ON",
        "Strict TDD:** **ON",
    )
    off_markers = (
        "strict_tdd: false",
        "Strict TDD: OFF",
        "Strict TDD:** OFF",
    )
    if any(m in content for m in on_markers):
        return {"strict_tdd": True}
    if any(m in content for m in off_markers):
        return {"strict_tdd": False}
    # Default to False if no explicit marker
    return {"strict_tdd": False}


def find_test_command(project_dir: Path) -> str | None:
    """Detect the test runner from package.json or project metadata."""
    pj = project_dir / "package.json"
    if pj.exists():
        try:
            data: dict[str, object] = json.loads(pj.read_text(encoding="utf-8"))
            scripts_obj = data.get("scripts")
            if isinstance(scripts_obj, dict):
                test = scripts_obj.get("test")
                if isinstance(test, str):
                    return test
        except json.JSONDecodeError:
            pass
    # Check for other test runners
    if (project_dir / "Cargo.toml").exists():
        return "cargo test"
    if (project_dir / "go.mod").exists():
        return "go test ./..."
    if (project_dir / "flake.nix").exists():
        return "nix flake check"
    return None


def should_enforce_strict_tdd(project_dir: Path) -> bool:
    """Determine if strict TDD should be enforced for this project."""
    init = load_sdd_init(project_dir)
    if init is None:
        return False
    return bool(init.get("strict_tdd", False))


def build_strict_tdd_instruction(project_dir: Path, test_command: str | None = None) -> str:
    """Build the prompt injection for strict TDD mode."""
    cmd = test_command or find_test_command(project_dir) or "(unknown — check project)"
    return STRICT_TDD_PROMPT.format(test_command=cmd)


def log_strict_tdd_optout(state_file: Path, reason: str) -> None:
    """Append a strict_tdd_optout entry to the change's transitions log.

    Used when the user runs `flow apply --no-strict-tdd "reason"`.
    """
    import json
    from datetime import datetime

    if not state_file.exists():
        return
    state = json.loads(state_file.read_text(encoding="utf-8"))
    if "strict_tdd_optouts" not in state:
        state["strict_tdd_optouts"] = []
    state["strict_tdd_optouts"].append(
        {
            "at": datetime.now(UTC).isoformat(),
            "reason": reason,
        }
    )
    state_file.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
