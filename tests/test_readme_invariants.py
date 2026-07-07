"""README invariants for REQ-V1.3.3.

Pure-Python assertions on the README file. Enforces:
- Minimum byte length
- Required sections (Architecture, Capabilities, Compatibility)
- Capability table has a status column
- Compatibility table present
- At least 3 status badges
- References to plugins/flow-engineering.js and CONTRIBUTING.md
- No stale "PR #1 bootstrap" status line
- Quickstart references all 8 SDD phases in the documented order
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"

REQUIRED_PHASES = [
    "flow new",
    "flow propose",
    "flow design",
    "flow spec",
    "flow tasks",
    "flow apply",
    "flow verify",
    "flow archive",
]


def _read_readme() -> str:
    return README_PATH.read_text(encoding="utf-8")


def test_readme_exists_and_meets_size_floor() -> None:
    assert README_PATH.exists(), f"{README_PATH} must exist"
    assert len(_read_readme()) >= 6144, "README must be at least 6 KB"


def test_architecture_section_present() -> None:
    assert re.search(r"^##\s+Architecture\s*$", _read_readme(), re.MULTILINE), (
        "README must include an '## Architecture' section"
    )


def test_capabilities_section_has_status_table() -> None:
    text = _read_readme()
    capabilities_match = re.search(r"^##\s+Capabilities\s*$", text, re.MULTILINE)
    assert capabilities_match, "README must include an '## Capabilities' section"
    tail = text[capabilities_match.end(): capabilities_match.end() + 30 * 80]
    assert "status" in tail.lower(), (
        "Capabilities section must be followed by a table containing a 'status' column"
    )


def test_compatibility_section_has_table() -> None:
    text = _read_readme()
    compat_match = re.search(r"^##\s+Compatibility\s*$", text, re.MULTILINE)
    assert compat_match, "README must include an '## Compatibility' section"
    tail = text[compat_match.end(): compat_match.end() + 30 * 80]
    table_match = re.search(r"\|\s*---", tail)
    assert table_match, "Compatibility section must be followed by a Markdown table"


def test_at_least_three_status_badges() -> None:
    text = _read_readme()
    shields = re.findall(r"!\[[^\]]*\]\(https://img\.shields\.io/[^\)]+\)", text)
    actions = re.findall(
        r"!\[[^\]]*\]\(https://github\.com/[^/]+/[^/]+/actions/[^\)]+\)", text
    )
    total = len(shields) + len(actions)
    assert total >= 3, (
        "README must contain at least 3 shields.io / github-actions badges; "
        f"found {total} (shields={len(shields)}, actions={len(actions)})"
    )


def test_mentions_opencode_plugin_path() -> None:
    text = _read_readme()
    assert "plugins/flow-engineering.js" in text, (
        "README must mention plugins/flow-engineering.js"
    )


def test_mentions_contributing_link_target() -> None:
    text = _read_readme()
    assert "CONTRIBUTING.md" in text, "README must reference CONTRIBUTING.md"


def test_no_stale_pr1_bootstrap_status() -> None:
    text = _read_readme()
    assert "PR #1 bootstrap" not in text, (
        'Stale "PR #1 bootstrap" status string must be removed from README'
    )


def test_quickstart_references_all_eight_phases_in_order() -> None:
    text = _read_readme()
    pattern = r".*".join(re.escape(phase) for phase in REQUIRED_PHASES)
    assert re.search(pattern, text, re.DOTALL), (
        "Quickstart section must walk through all 8 SDD phases in order: "
        + " -> ".join(REQUIRED_PHASES)
    )
