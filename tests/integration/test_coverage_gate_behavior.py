"""Integration test for REQ-V1.3.2 (gate behavior).

Builds a synthetic stub module that produces 0% coverage and asserts
that pytest with `--cov-fail-under=80` exits non-zero with a clear
"Coverage failure" message.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def stub_module(tmp_path: Path) -> Path:
    """Create a tiny throwaway module with no tests covering it."""
    pkg = tmp_path / "stub_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "zero.py").write_text(
        textwrap.dedent(
            """\
            def uncovered() -> int:
                return 42


            def also_uncovered() -> str:
                return "hello"
            """
        )
    )
    return tmp_path


def test_cov_fail_under_triggers_nonzero_exit(stub_module: Path) -> None:
    """`--cov-fail-under=80` against a 0%-coverage stub MUST exit non-zero."""
    pkg_path = stub_module / "stub_pkg"

    # Prefer `python -m pytest` from the repo's venv so we don't need a
    # pyproject.toml in tmp_path. Fall back to a SKIP if pytest can't be
    # invoked at all.
    pytest_bin = shutil.which("pytest")
    if pytest_bin is None:
        # try sys.executable -m pytest
        cmd = [sys.executable, "-m", "pytest", "--no-header", "-q", "--tb=no"]
    else:
        cmd = [pytest_bin, "--no-header", "-q", "--tb=no"]

    cmd.extend(
        [
            "--cov",
            str(pkg_path),
            "--cov-fail-under=80",
        ]
    )

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=stub_module,
            timeout=60,
        )
    except (FileNotFoundError, OSError) as exc:
        pytest.skip(f"pytest not invocable in isolated tmp_path: {exc}")

    assert result.returncode != 0, (
        f"pytest should exit non-zero with --cov-fail-under=80 on 0%-coverage stub.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The coverage tool emits a "Coverage failure" line. Either stdout or stderr.
    combined = (result.stdout or "") + (result.stderr or "")
    assert "Coverage failure" in combined or "fail_under" in combined, (
        f"Expected a 'Coverage failure' message; got:\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
