"""Smoke tests for the installed CLI entry point.

These tests exercise the public ``flow`` console script instead of importing the
Click command directly. They catch packaging/entry-point regressions that unit
tests can miss.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def _run_flow(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["flow", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_installed_flow_entry_point_reports_version(tmp_path: Path) -> None:
    result = _run_flow("--version", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "1.3.0" in result.stdout


def test_installed_flow_entry_point_handles_basic_change_lifecycle(
    tmp_path: Path,
) -> None:
    new_result = _run_flow("new", "smoke-change", "--in", str(tmp_path), cwd=tmp_path)
    status_result = _run_flow("status", "--in", str(tmp_path), cwd=tmp_path)

    assert new_result.returncode == 0, new_result.stderr
    assert status_result.returncode == 0, status_result.stderr
    assert "smoke-change: NEW" in status_result.stdout
