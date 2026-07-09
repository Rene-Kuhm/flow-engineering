"""Smoke tests for the out-of-band runner watchdog script."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "runner_watchdog.ps1"


pytestmark = [
    pytest.mark.skipif(
        platform.system() != "Windows", reason="runner watchdog is Windows-service focused"
    ),
    pytest.mark.skipif(
        shutil.which("pwsh") is None, reason="pwsh is required for the watchdog script"
    ),
]


def _run_watchdog(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            *args,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_runner_watchdog_reports_missing_service_as_critical() -> None:
    result = _run_watchdog(
        "-RunnerNamePattern",
        "definitely-not-a-real-runner-service-*",
        "-SkipGitHub",
        "-Json",
    )

    assert result.returncode == 2, result.stderr
    payload = json.loads(result.stdout)
    assert payload["overall"] == "critical"
    assert any(
        check["name"] == "runner_service" and check["status"] == "critical"
        for check in payload["checks"]
    )
    assert any(
        check["name"] == "github_ci" and check["status"] == "skipped" for check in payload["checks"]
    )


def test_runner_watchdog_text_output_is_operator_readable() -> None:
    result = _run_watchdog(
        "-RunnerNamePattern",
        "definitely-not-a-real-runner-service-*",
        "-SkipGitHub",
    )

    assert result.returncode == 2, result.stderr
    assert "runner-watchdog: critical" in result.stdout
    assert "runner_service: critical" in result.stdout
    assert "github_ci: skipped" in result.stdout


def test_runner_watchdog_webhook_test_dry_run_is_machine_readable() -> None:
    result = _run_watchdog(
        "-RunnerNamePattern",
        "definitely-not-a-real-runner-service-*",
        "-SkipGitHub",
        "-WebhookUrl",
        "https://hooks.example.test/super-secret-token",
        "-WebhookTest",
        "-WebhookDryRun",
        "-Json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["overall"] == "critical"
    assert payload["webhook"]["configured"] is True
    assert payload["webhook"]["dry_run"] is True
    assert payload["webhook"]["test"] is True
    assert "super-secret-token" not in result.stdout
    assert any(
        check["name"] == "webhook_test" and check["status"] == "warning"
        for check in payload["checks"]
    )
