"""Smoke tests for the PowerShell system health dashboard."""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "system_health.ps1"


@pytest.mark.skipif(platform.system() != "Windows", reason="PowerShell health script is Windows-runner focused")
@pytest.mark.skipif(shutil.which("pwsh") is None, reason="pwsh is required for the health script")
def test_system_health_script_renders_expected_sections_offline(tmp_path: Path) -> None:
    changes_root = tmp_path / "openspec" / "changes" / "demo-change"
    changes_root.mkdir(parents=True)
    docs_root = tmp_path / "docs"
    docs_root.mkdir()
    (docs_root / "follow-up-audit.md").write_text(
        "| Future drift-detection slices | Active guardrail | Keep slices small. |\n"
        "No urgent blocker remains.\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-RepoRoot",
            str(tmp_path),
            "-SkipGitHub",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "== Runner service ==" in output
    assert "== Startup fallback ==" in output
    assert "== Latest CI runs ==" in output
    assert "gh: skipped" in output
    assert "== Active OpenSpec changes ==" in output
    assert "demo-change" in output
    assert "== Follow-up audit ==" in output
    assert "Active guardrail" in output
    assert "== Memory maintenance ==" in output
