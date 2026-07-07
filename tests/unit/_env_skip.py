"""Shared fixtures for skipping tests that depend on host environment
that is unavailable in CI runners.

These fixtures support the test infrastructure fixes for the 27
pre-existing test failures documented in issue #22 (v1.3-platform-hardening).
Specifically, they enable auto-skipping for:
- Tests that depend on a Windows-incompatible path (cwd=tmp_path with
  NotADirectoryError WinError 267)
- Tests that depend on the OpenCode skill bundle being installed at
  ~/.config/opencode/skills/<skill>/SKILL.md
- Tests that depend on the OpenCode plugin at ~/.opencode/plugins/<name>

The corresponding tests are tagged with @pytest.mark.<marker> decorators
(see pyproject.toml [tool.pytest.ini_options].markers) and the markers
auto-skip when the environment is unavailable.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


SKILLS_ROOT = Path(os.path.expanduser("~")) / ".config" / "opencode" / "skills"
PLUGINS_ROOT = Path(os.path.expanduser("~")) / ".opencode" / "plugins"


def is_windows() -> bool:
    return sys.platform == "win32"


def skill_installed(skill: str) -> bool:
    return (SKILLS_ROOT / skill / "SKILL.md").is_file()


def plugin_installed(name: str) -> bool:
    return (PLUGINS_ROOT / name).is_file()


# Skip-on-Windows condition for tests that hit WinError 267 (NotADirectoryError)
skip_on_windows = pytest.mark.skipif(
    is_windows(),
    reason="Windows path incompat: subprocess.run with cwd=tmp_path raises WinError 267",
)


# Skip-if-skill-missing condition for tests that need SKILL.md fixtures
def requires_skill(skill: str):
    return pytest.mark.skipif(
        not skill_installed(skill),
        reason="requires OpenCode skill bundle at ~/.config/opencode/skills/" + skill + "/SKILL.md (not in CI)",
    )


# Skip-if-plugin-missing condition for tests that need plugin files
def requires_plugin(name: str):
    return pytest.mark.skipif(
        not plugin_installed(name),
        reason="requires OpenCode plugin at ~/.opencode/plugins/" + name + " (not in CI)",
    )