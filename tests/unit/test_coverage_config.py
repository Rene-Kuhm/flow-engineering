"""Tests for REQ-V1.3.2 (CI coverage gate).

Confirms that:
- pyproject.toml has [tool.coverage.report] with fail_under = 80
- .github/workflows/test.yml runs pytest with --cov-fail-under=80
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
TEST_YML = WORKFLOWS_DIR / "test.yml"
GITHUB_HOSTED_RUNNERS = {"windows-latest"}
EXTERNAL_PR_TRIGGERS = {"pull_request", "pull_request_target"}


def _read_pyproject() -> str:
    return PYPROJECT.read_text(encoding="utf-8")


def _read_test_workflow() -> str:
    return TEST_YML.read_text(encoding="utf-8")


class TestCoveragePyproject:
    def test_has_coverage_report_section(self) -> None:
        text = _read_pyproject()
        assert "[tool.coverage.report]" in text, "pyproject.toml must define [tool.coverage.report]"

    def test_fail_under_is_80(self) -> None:
        text = _read_pyproject()
        # naive parse; sufficient for this static check
        assert "fail_under = 80" in text, (
            "pyproject.toml [tool.coverage.report] must set fail_under = 80"
        )

    def test_show_missing_is_true(self) -> None:
        text = _read_pyproject()
        assert "show_missing = true" in text


class TestCoverageCiFlag:
    def test_workflow_runs_pytest_with_cov_fail_under(self) -> None:
        text = _read_test_workflow()
        assert "--cov-fail-under=80" in text, (
            ".github/workflows/test.yml must pass --cov-fail-under=80 to pytest"
        )

    def test_workflow_still_collects_coverage(self) -> None:
        text = _read_test_workflow()
        # sanity: the existing cov args must still be there
        assert "--cov=src" in text
        assert "--cov-report=xml" in text


def test_workflows_do_not_reference_self_hosted_runners() -> None:
    for workflow in sorted((*WORKFLOWS_DIR.glob("*.yml"), *WORKFLOWS_DIR.glob("*.yaml"))):
        assert "self-hosted" not in workflow.read_text(encoding="utf-8").lower(), workflow


def test_external_pr_workflows_use_only_audited_github_hosted_runners() -> None:
    external_pr_workflows: list[Path] = []

    for workflow in sorted((*WORKFLOWS_DIR.glob("*.yml"), *WORKFLOWS_DIR.glob("*.yaml"))):
        text = workflow.read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        triggers = parsed.get("on", parsed.get(True))
        has_external_pr = (
            isinstance(triggers, str)
            and triggers in EXTERNAL_PR_TRIGGERS
            or isinstance(triggers, dict)
            and bool(EXTERNAL_PR_TRIGGERS.intersection(triggers))
            or isinstance(triggers, list)
            and bool(EXTERNAL_PR_TRIGGERS.intersection(triggers))
        )

        if has_external_pr:
            external_pr_workflows.append(workflow)
            for job_name, job in parsed["jobs"].items():
                assert isinstance(job, dict), f"{workflow}:{job_name} must be a job mapping"
                assert "uses" not in job, f"{workflow}:{job_name} uses an unaudited workflow"
                runs_on = job.get("runs-on")
                assert isinstance(runs_on, str), f"{workflow}:{job_name} runs-on must be static"
                assert runs_on in GITHUB_HOSTED_RUNNERS, (
                    f"{workflow}:{job_name} uses unaudited runner {runs_on!r}"
                )

    assert TEST_YML in external_pr_workflows


def test_workflow_yaml_is_parseable() -> None:
    """Sanity: the workflow file must remain valid YAML."""
    text = _read_test_workflow()
    parsed = yaml.safe_load(text)
    assert isinstance(parsed, dict)
    assert "jobs" in parsed
