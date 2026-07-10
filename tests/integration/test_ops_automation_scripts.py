"""Smoke tests for operator automation helper scripts."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_WATCHDOG = REPO_ROOT / "scripts" / "install_runner_watchdog_task.ps1"
INSTALL_MONTHLY = REPO_ROOT / "scripts" / "install_monthly_maintenance_task.ps1"
MONTHLY_MAINTENANCE = REPO_ROOT / "scripts" / "monthly_maintenance.ps1"
SET_WEBHOOK = REPO_ROOT / "scripts" / "set_runner_watchdog_webhook.ps1"


pytestmark = [
    pytest.mark.skipif(
        platform.system() != "Windows", reason="operator scripts target Windows PowerShell"
    ),
    pytest.mark.skipif(
        shutil.which("pwsh") is None, reason="pwsh is required for operator scripts"
    ),
]


def _run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *args,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_install_runner_watchdog_task_dry_run_json() -> None:
    result = _run_script(INSTALL_WATCHDOG, "-DryRun", "-Json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["task_name"] == "flow-engineering-runner-watchdog"
    assert payload["schedule_minutes"] == 15
    assert payload["dry_run"] is True
    assert "runner_watchdog.ps1" in payload["arguments"]
    assert payload["webhook_source"] == "FLOW_RUNNER_ALERT_WEBHOOK environment variable"


def test_install_monthly_maintenance_task_dry_run_json() -> None:
    result = _run_script(INSTALL_MONTHLY, "-DryRun", "-Json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["task_name"] == "flow-engineering-monthly-maintenance"
    assert payload["schedule"] == "monthly"
    assert payload["day_of_month"] == 1
    assert payload["dry_run"] is True
    assert "monthly_maintenance.ps1" in payload["arguments"]


def test_set_runner_watchdog_webhook_dry_run_does_not_echo_secret() -> None:
    result = _run_script(
        SET_WEBHOOK,
        "-WebhookUrl",
        "https://hooks.example.test/super-secret-token",
        "-DryRun",
        "-Json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["variable"] == "FLOW_RUNNER_ALERT_WEBHOOK"
    assert payload["target"] == "User"
    assert payload["dry_run"] is True
    assert payload["value_present"] is True
    assert "super-secret-token" not in result.stdout


def test_monthly_maintenance_renders_expected_sections_offline() -> None:
    result = _run_script(MONTHLY_MAINTENANCE, "-SkipGitHub")

    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "monthly-maintenance: ok" in output
    assert "== git_status: ok ==" in output
    assert "== system_health: ok ==" in output
    assert "== runner_watchdog:" not in output
    assert "== follow_up_audit: ok ==" in output
    assert "== memory_policy: ok ==" in output


def test_monthly_maintenance_json_output_is_machine_readable() -> None:
    result = _run_script(MONTHLY_MAINTENANCE, "-SkipGitHub", "-Json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["overall"] == "ok"
    step_names = {step["name"] for step in payload["steps"]}
    assert "runner_watchdog" not in step_names
    assert {
        "git_status",
        "system_health",
        "follow_up_audit",
        "memory_policy",
    }.issubset(step_names)
