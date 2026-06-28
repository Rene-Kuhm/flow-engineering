"""Unit tests for the REQ-V1.2.3 skill version gate CLI hooks (T3.5).

The three ``flow apply`` / ``flow verify`` / ``flow archive`` Click
commands now enforce a project-pinned ``[tool.flow_engineering]
min_sdd_skill_versions`` policy at startup. If the on-disk SKILL.md
``version`` frontmatter is below the declared minimum for any
orchestrator-dispatched sdd-* agent, the command emits a structured
JSON remediation payload on stderr and exits with code 4 (per the
``observability.EXIT_WRITE_FAILURE`` contract — see design D3 + D9).

These tests are written BEFORE the CLI implementation per strict TDD.
They MUST fail with no error-path coverage until the GREEN commit
wires the ``_enforce_min_skill_versions_or_exit`` helper into the
three Click command bodies.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering import opencode_skill_catalog as osc_module
from flow_engineering.cli import main

runner = CliRunner()


def _lay_skill(tmp_path: Path, skill_name: str, version: str) -> None:
    """Write a SKILL.md under ``<tmp_path>/.config/opencode/skills/<name>/SKILL.md``."""
    skill_dir = tmp_path / ".config" / "opencode" / "skills" / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: mock\nversion: \"{version}\"\n---\n\n",
        encoding="utf-8",
    )


def _write_pyproject_min_versions(
    tmp_path: Path, min_versions: dict[str, str],
) -> None:
    """Write a minimal ``pyproject.toml`` with the gate section under ``tmp_path``."""
    pyproject = tmp_path / "pyproject.toml"
    min_block = ", ".join(f'{k} = "{v}"' for k, v in min_versions.items())
    pyproject.write_text(
        "[tool.flow_engineering]\n"
        f"min_sdd_skill_versions = {{{min_block}}}\n",
        encoding="utf-8",
    )


def _set_scaffold_change(tmp_path: Path, change: str = "demo") -> Path:
    """Create a bare-bones flow-engineering change directory under ``tmp_path``."""
    change_dir = tmp_path / "flow-engineering" / change
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "state.json").write_text(
        '{"status": "TASKED", "transitions": []}\n', encoding="utf-8",
    )
    return change_dir


class TestSkillVersionGateCLI:
    """T3.5 RED tests for the 3-line CLI hooks on flow apply/verify/archive.

    The CLI hook (a) reads ``[tool.flow_engineering] min_sdd_skill_versions``
    from pyproject.toml, (b) calls ``enforce_min_skill_versions()`` on the
    on-disk SKILL.md files, (c) on violation emits a structured JSON
    payload on stderr and exits 4.
    """

    def test_flow_apply_exits_4_on_skill_version_violation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """flow apply exits 4 when sdd-apply on disk is below pyproject minimum."""
        _lay_skill(tmp_path, "sdd-apply", "2.5")
        _write_pyproject_min_versions(tmp_path, {"sdd-apply": "3.0"})
        _set_scaffold_change(tmp_path, "demo")
        # Patch Path.home so enforce_min_skill_versions reads tmp_path layout.
        monkeypatch.setattr(
            osc_module.Path, "home", classmethod(lambda cls: tmp_path),
        )

        result = runner.invoke(main, ["apply", "demo", "--in", str(tmp_path)])
        assert result.exit_code == 4
        # Structured JSON payload on stderr.
        stderr = (result.stderr or "")
        # The payload may be wrapped by Click; tolerate trailing whitespace.
        assert "skill_version_violation" in stderr
        assert "sdd-apply" in stderr
        assert "3.0" in stderr

    def test_flow_verify_exits_4_on_skill_version_violation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """flow verify exits 4 when sdd-verify on disk is below pyproject minimum."""
        _lay_skill(tmp_path, "sdd-verify", "2.0")
        _write_pyproject_min_versions(tmp_path, {"sdd-verify": "3.0"})
        _set_scaffold_change(tmp_path, "demo")
        monkeypatch.setattr(
            osc_module.Path, "home", classmethod(lambda cls: tmp_path),
        )

        result = runner.invoke(main, ["verify", "demo", "--in", str(tmp_path)])
        assert result.exit_code == 4
        stderr = result.stderr or ""
        assert "skill_version_violation" in stderr
        assert "sdd-verify" in stderr

    def test_flow_archive_exits_4_on_skill_version_violation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """flow archive exits 4 when sdd-archive on disk is below pyproject minimum."""
        _lay_skill(tmp_path, "sdd-archive", "2.0")
        _write_pyproject_min_versions(tmp_path, {"sdd-archive": "3.0"})
        _set_scaffold_change(tmp_path, "demo")
        monkeypatch.setattr(
            osc_module.Path, "home", classmethod(lambda cls: tmp_path),
        )

        result = runner.invoke(main, ["archive", "demo", "--in", str(tmp_path)])
        assert result.exit_code == 4
        stderr = result.stderr or ""
        assert "skill_version_violation" in stderr
        assert "sdd-archive" in stderr

    def test_skill_version_violation_emits_structured_json_payload(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Stderr contains a parseable JSON object describing the violation."""
        _lay_skill(tmp_path, "sdd-apply", "2.5")
        _write_pyproject_min_versions(tmp_path, {"sdd-apply": "3.0"})
        _set_scaffold_change(tmp_path, "demo")
        monkeypatch.setattr(
            osc_module.Path, "home", classmethod(lambda cls: tmp_path),
        )

        result = runner.invoke(main, ["apply", "demo", "--in", str(tmp_path)])
        assert result.exit_code == 4
        stderr = result.stderr or ""
        # Locate the first JSON object in stderr (Click may prefix lines).
        start = stderr.find("{")
        assert start != -1, f"No JSON object found in stderr: {stderr!r}"
        candidate = stderr[start:].splitlines()[0].rstrip()
        # Tolerate trailing Click decoration by trimming at first unmatched brace.
        payload = json.loads(candidate)
        assert payload["error"] == "skill_version_violation"
        assert payload["skill"] == "sdd-apply"
        assert payload["expected"] == "3.0"
        assert payload["found"] == "2.5"
        assert "hint" in payload
        assert "pip install" in payload["hint"]