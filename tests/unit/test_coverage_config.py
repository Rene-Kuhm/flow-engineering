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
TEST_YML = REPO_ROOT / ".github" / "workflows" / "test.yml"


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


def test_workflow_yaml_is_parseable() -> None:
    """Sanity: the workflow file must remain valid YAML."""
    text = _read_test_workflow()
    parsed = yaml.safe_load(text)
    assert isinstance(parsed, dict)
    assert "jobs" in parsed
