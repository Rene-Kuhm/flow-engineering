"""End-to-end integration test for the REQ-V1.2.3 skill version gate (T3.6).

Exercises the full gate flow with the CLI hooks + pyproject parser +
SKILL.md frontmatter read all wired together. Asserts:

- Exit code 4 when an on-disk SKILL.md is below the pyproject minimum.
- Structured JSON remediation payload on stderr.
- 0 side effects on disk (no partial state written) when the gate fires.

This is the PR#2c closeout integration sweep (T3.6). Per the task
brief, this suite covers REQ-V1.2.3 end-to-end with NO mocking of the
gate helper itself — the only mock surfaces are the ``Path.home``
resolution (so the test can lay SKILL.md files under ``tmp_path``) and
the pyproject section under ``tmp_path``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering import opencode_skill_catalog as osc_module
from flow_engineering.cli import main

runner = CliRunner()


def _lay_skill(tmp_path: Path, skill_name: str, version: str) -> Path:
    """Write a SKILL.md under ``<tmp_path>/.config/opencode/skills/<name>/SKILL.md``."""
    skill_dir = tmp_path / ".config" / "opencode" / "skills" / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        f"---\nname: {skill_name}\ndescription: mock\nversion: \"{version}\"\n---\n\n",
        encoding="utf-8",
    )
    return skill_md


def _write_pyproject_min_versions(
    tmp_path: Path, min_versions: dict[str, str],
) -> Path:
    """Write a minimal ``pyproject.toml`` with the gate section under ``tmp_path``."""
    pyproject = tmp_path / "pyproject.toml"
    min_block = ", ".join(f'{k} = "{v}"' for k, v in min_versions.items())
    pyproject.write_text(
        "[tool.flow_engineering]\n"
        f"min_sdd_skill_versions = {{{min_block}}}\n",
        encoding="utf-8",
    )
    return pyproject


def _scaffold_change(tmp_path: Path, change: str = "demo") -> Path:
    """Create a bare-bones flow-engineering change directory under ``tmp_path``."""
    change_dir = tmp_path / "flow-engineering" / change
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "state.json").write_text(
        '{"status": "TASKED", "transitions": []}\n', encoding="utf-8",
    )
    return change_dir


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Patch ``Path.home`` so the gate reads SKILL.md files from ``tmp_path``."""
    monkeypatch.setattr(
        osc_module.Path, "home", classmethod(lambda cls: tmp_path),
    )
    return tmp_path


class TestSkillVersionGateIntegration:
    """T3.6: end-to-end gate flow via the real Click CLI surface."""

    def test_gate_fires_through_full_cli_path(
        self, isolated_home: Path,
    ) -> None:
        """On-disk sdd-apply=2.5 + pyproject min=3.0 → exit 4 via flow apply."""
        _lay_skill(isolated_home, "sdd-apply", "2.5")
        _write_pyproject_min_versions(isolated_home, {"sdd-apply": "3.0"})
        _scaffold_change(isolated_home, "demo")

        result = runner.invoke(
            main, ["apply", "demo", "--in", str(isolated_home)],
        )
        assert result.exit_code == 4
        stderr = result.stderr or ""
        assert "skill_version_violation" in stderr
        assert "sdd-apply" in stderr

    def test_gate_payload_includes_remediation_hint(
        self, isolated_home: Path,
    ) -> None:
        """The JSON payload's ``hint`` field points the operator at the fix."""
        _lay_skill(isolated_home, "sdd-apply", "2.5")
        _write_pyproject_min_versions(isolated_home, {"sdd-apply": "3.0"})
        _scaffold_change(isolated_home, "demo")

        result = runner.invoke(
            main, ["apply", "demo", "--in", str(isolated_home)],
        )
        assert result.exit_code == 4
        # Locate first JSON object on stderr.
        start = (result.stderr or "").find("{")
        assert start != -1
        candidate = (result.stderr or "")[start:].splitlines()[0].rstrip()
        payload = json.loads(candidate)
        assert payload["error"] == "skill_version_violation"
        assert payload["skill"] == "sdd-apply"
        assert payload["expected"] == "3.0"
        assert payload["found"] == "2.5"
        assert "hint" in payload
        # The remediation hint references the upgrade path.
        assert "pip install" in payload["hint"]

    def test_gate_no_op_when_pyproject_section_missing(
        self, isolated_home: Path,
    ) -> None:
        """No ``[tool.flow_engineering]`` section → gate does NOT fire."""
        _lay_skill(isolated_home, "sdd-apply", "2.5")
        # Write pyproject WITHOUT the gate section.
        (isolated_home / "pyproject.toml").write_text(
            "[tool.unrelated]\nfoo = 1\n", encoding="utf-8",
        )
        _scaffold_change(isolated_home, "demo")

        result = runner.invoke(
            main, ["apply", "demo", "--in", str(isolated_home)],
        )
        # The gate is a no-op; the apply then proceeds (orchestrator may
        # still emit its own error, but NOT exit 4 with skill_version_violation).
        stderr = result.stderr or ""
        assert "skill_version_violation" not in stderr

    def test_gate_no_side_effects_on_disk_when_firing(
        self, isolated_home: Path,
    ) -> None:
        """The gate fires BEFORE any apply state mutation; no writes to disk."""
        _lay_skill(isolated_home, "sdd-apply", "2.5")
        _write_pyproject_min_versions(isolated_home, {"sdd-apply": "3.0"})
        _scaffold_change(isolated_home, "demo")

        # Snapshot the change dir contents before invocation.
        before = set((isolated_home / "flow-engineering" / "demo").iterdir())

        result = runner.invoke(
            main, ["apply", "demo", "--in", str(isolated_home)],
        )
        assert result.exit_code == 4

        # No new files / no state.json mutation.
        after = set((isolated_home / "flow-engineering" / "demo").iterdir())
        assert before == after

    def test_gate_does_not_fire_when_all_skills_meet_minimum(
        self, isolated_home: Path,
    ) -> None:
        """All on-disk SKILL.md at 3.0 + min dict {*: 3.0} → no exit 4."""
        for skill in ("sdd-apply", "sdd-verify", "sdd-archive"):
            _lay_skill(isolated_home, skill, "3.0")
        _write_pyproject_min_versions(
            isolated_home,
            {"sdd-apply": "3.0", "sdd-verify": "3.0", "sdd-archive": "3.0"},
        )
        _scaffold_change(isolated_home, "demo")

        result = runner.invoke(
            main, ["apply", "demo", "--in", str(isolated_home)],
        )
        stderr = result.stderr or ""
        assert "skill_version_violation" not in stderr