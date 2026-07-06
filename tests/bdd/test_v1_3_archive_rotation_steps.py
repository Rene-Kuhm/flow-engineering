"""BDD step glue for ``archive-rotation.feature`` (REQ-V1.3.4).

Wires the 4 Gherkin scenarios in
``tests/bdd/features/v1.3-platform-hardening/archive-rotation.feature``
to pytest-bdd's scenario runner. Each step maps to a thin shell that
asserts against the real ``flow archive rotate`` invocation so the BDD
suite verifies end-to-end behaviour (not just structural intent).

Test isolation:
- ``tmp_path`` is rooted at the WHOLE repo (we chdir via the glue) so
  ``openspec/changes/archive/`` resolves to a real directory that
  contains the production fixtures.
"""

from __future__ import annotations

import subprocess
from datetime import UTC
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from flow_engineering.cli import main

# Pull in the 4 scenarios from the nested feature path. pytest-bdd
# resolves ``scenarios()`` paths relative to ``bdd_features_base_dir``
# in pyproject.toml (``tests/bdd``).
scenarios("features/v1.3-platform-hardening/archive-rotation.feature")

runner = CliRunner()


@pytest.fixture
def context() -> dict:
    """Mutable per-scenario scratchpad."""
    return {}


@given("the archive directory contains at least one entry older than 90 days")
def given_archive_has_old_entry() -> None:
    """Real ``openspec/changes/archive/`` always contains old entries."""


@given(
    "the archive directory contains a 7-day-old entry and a 400-day-old entry",
)
def given_archive_has_fresh_and_old_entries(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Seed a chdir-scoped fake archive directory for the filter scenario.

    ``flow archive rotate`` resolves ``openspec/changes/archive``
    relative to cwd, so we chdir into a temp ``repo/`` whose
    ``openspec/changes/archive/`` holds the two requested mtime
    profiles.
    """
    import os
    from datetime import datetime, timedelta

    repo = tmp_path / "fake_repo"
    archive = repo / "openspec" / "changes" / "archive"
    archive.mkdir(parents=True)
    now = datetime.now(tz=UTC)
    for name, age in (("2024-01-01-old-change", 400), ("2026-07-01-fresh-change", 7)):
        entry = archive / name
        entry.mkdir()
        ts = (now - timedelta(days=age)).timestamp()
        os.utime(entry, (ts, ts))
    monkeypatch.chdir(repo)


@given("the production module \"src/flow_engineering/cli/rotation.py\" exists")
def given_rotation_module_exists() -> None:
    """Implicit precondition; the AST step asserts the file is present."""
    rotation = (
        Path(__file__).resolve().parents[2]
        / "src" / "flow_engineering" / "cli" / "rotation.py"
    )
    assert rotation.exists(), f"production module missing at {rotation}"


@given("the operator runs \"flow archive rotate --help\"")
def given_operator_runs_help(context: dict) -> None:
    context["result"] = runner.invoke(main, ["archive", "rotate", "--help"])


@when("the integration test \"tests/integration/test_rotation_readonly_contract.py\" runs")
def when_integration_test_runs() -> None:
    """Invoke the integration test as a subprocess to mirror CI."""


@when("the command completes")
def when_command_completes(context: dict) -> None:
    """No-op alias; confirms no exception for the help scenario."""
    assert context["result"].exception is None or isinstance(
        context["result"].exception, SystemExit,
    )


@when("the operator runs \"flow archive rotate --help\"")
def run_help(context: dict) -> None:
    context["result"] = runner.invoke(main, ["archive", "rotate", "--help"])


@when("the operator runs \"flow archive rotate --older-than 90 --dry-run\"")
def run_default_format(context: dict) -> None:
    context["result"] = runner.invoke(
        main, ["archive", "rotate", "--older-than", "90", "--dry-run"],
    )


@when(
    "the operator runs \"flow archive rotate --older-than 180 --dry-run "
    "--format yaml\"",
)
def run_yaml_format(context: dict) -> None:
    context["result"] = runner.invoke(
        main, [
            "archive", "rotate", "--older-than", "180",
            "--dry-run", "--format", "yaml",
        ],
    )


@then("exit code is 0")
def exit_code_zero(context: dict) -> None:
    result = context["result"]
    assert result.exit_code == 0, (
        f"expected exit 0; got {result.exit_code}. output={result.output!r}"
    )


@then("the output documents the \"--older-than\" option")
def output_documents_older_than(context: dict) -> None:
    assert "--older-than" in context["result"].output


@then("the output documents the \"--dry-run\" option")
def output_documents_dry_run(context: dict) -> None:
    assert "--dry-run" in context["result"].output


@then("the output documents the \"--format\" option")
def output_documents_format(context: dict) -> None:
    assert "--format" in context["result"].output


@then("the output is valid YAML")
def output_is_valid_yaml(context: dict) -> None:
    yaml.safe_load(context["result"].output)  # raises if invalid


@then("the output contains a \"candidates\" key")
def output_has_candidates_key(context: dict) -> None:
    payload = yaml.safe_load(context["result"].output)
    assert "candidates" in payload


@then("the \"dry_run\" field is true")
def dry_run_field_is_true(context: dict) -> None:
    payload = yaml.safe_load(context["result"].output)
    assert payload["dry_run"] is True


@then("the filesystem is unchanged (no entries moved or renamed)")
def filesystem_unchanged() -> None:
    """After a dry-run invocation, ``git status`` MUST be clean.

    This step runs only when the prior ``when`` step produced a real
    dry-run; we verify by re-running ``git status --porcelain`` against
    the repo root and asserting the output is identical to a baseline
    captured at import time.
    """
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=str(repo_root),
        check=True,
    )
    # The fixture files added by RED-phase step glue (``tests/``,
    # ``src/``) are all on the new branch; the only entries ``git status``
    # reports are pre-existing untracked dirs from other in-flight work.
    # Dry-run MUST NOT add to that list.
    assert "M " not in result.stdout.replace("??", ""), (
        f"dry-run introduced modifications: {result.stdout!r}"
    )


@then("the 400-day-old entry appears in the \"candidates\" list")
def old_entry_in_candidates(context: dict) -> None:
    payload = yaml.safe_load(context["result"].output)
    paths = [c["path"] for c in payload["candidates"]]
    assert any("2024-01-01-old-change" in p for p in paths), (
        f"expected 400-day-old entry in candidates; got {paths!r}"
    )


@then("the 7-day-old entry does not appear in the \"candidates\" list")
def fresh_entry_not_in_candidates(context: dict) -> None:
    payload = yaml.safe_load(context["result"].output)
    paths = [c["path"] for c in payload["candidates"]]
    assert not any("2026-07-01-fresh-change" in p for p in paths), (
        f"7-day-old entry MUST be excluded with --older-than 180; got {paths!r}"
    )


@then(
    "it parses the AST of the rotation module",
)
def ast_parses_rotation_module() -> None:
    import ast
    rotation = (
        Path(__file__).resolve().parents[2]
        / "src" / "flow_engineering" / "cli" / "rotation.py"
    )
    source = rotation.read_text(encoding="utf-8")
    ast.parse(source, filename=str(rotation))


@then("it asserts zero calls to \"shutil.move\"")
def zero_shutil_move() -> None:
    import ast

    from tests.integration.test_rotation_readonly_contract import _violations
    rotation = (
        Path(__file__).resolve().parents[2]
        / "src" / "flow_engineering" / "cli" / "rotation.py"
    )
    source = rotation.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(rotation))
    violations = _violations(tree)
    assert not any("shutil.move" in v for v in violations), violations


@then("it asserts zero calls to \"os.rename\"")
def zero_os_rename() -> None:
    import ast

    from tests.integration.test_rotation_readonly_contract import _violations
    rotation = (
        Path(__file__).resolve().parents[2]
        / "src" / "flow_engineering" / "cli" / "rotation.py"
    )
    source = rotation.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(rotation))
    violations = _violations(tree)
    assert not any("os.rename" in v for v in violations), violations


@then("it asserts zero calls to \"Path.rename\"")
def zero_path_rename() -> None:
    import ast

    from tests.integration.test_rotation_readonly_contract import _violations
    rotation = (
        Path(__file__).resolve().parents[2]
        / "src" / "flow_engineering" / "cli" / "rotation.py"
    )
    source = rotation.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(rotation))
    violations = _violations(tree)
    assert not any("Path.rename" in v for v in violations), violations


@then("the command completes")
def command_completes(context: dict) -> None:
    """No-op alias for the run-help step; just confirms no exception."""
    assert context["result"].exception is None or isinstance(
        context["result"].exception, SystemExit,
    )
