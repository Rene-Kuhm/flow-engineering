"""RED fixtures for `flow prompts` CLI subcommand (REQ-49 + REQ-50, T2.1).

REQ-49 S1 + S2 user-facing surface: ``flow prompts check`` walks the
SKILL_CATALOG and reports drift findings via CliRunner-friendly exit
codes (0 = clean, 1 = drift detected, 2 = catalog missing).

The CLI wraps the ``check_drift(SKILL_CATALOG)`` helper from
``opencode_skill_catalog``. Exit codes follow the design contract:
- 0 = clean state (no drift, no parse errors)
- 1 = drift detected (one or more entries diverged)
- 2 = catalog missing (path resolution failure)

The tests are written BEFORE the implementation per strict TDD (RED).
They MUST fail with ``AttributeError`` (no ``flow_prompts_check`` Click
command) until the GREEN commit lands.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from flow_engineering import opencode_skill_catalog as osc
from flow_engineering.cli import main
from flow_engineering.opencode_skill_catalog import SkillEntry


runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def clean_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> dict[str, SkillEntry]:
    """Build a 1-entry catalog with a file whose checksum matches the catalog.

    ``_read_sidecar`` is monkeypatched to return ``{}`` so the catalog's
    ``last_verified_checksum`` is the comparison baseline; ``_sidecar_path``
    is rewritten under ``tmp_path`` so tests never touch the user's
    ``~/.flow-engineering/`` directory.
    """
    sidecar = tmp_path / ".flow-engineering" / "prompt_checksums.json"

    def _fake_sidecar_path() -> Path:
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        return sidecar

    monkeypatch.setattr(osc, "_read_sidecar", lambda: {})
    monkeypatch.setattr(osc, "_sidecar_path", _fake_sidecar_path)

    skill = tmp_path / "SKILL.md"
    skill.write_text(
        '---\nname: sdd-test\ndescription: mock\nversion: "3.0"\n---\n\nBody.\n',
        encoding="utf-8",
    )
    checksum = osc.compute_frontmatter_sha256(skill)
    return {
        "sdd-test/skill": SkillEntry(
            skill_name="sdd-test",
            surface="skill",
            expected_version="3.0",
            expected_path=str(skill),
            last_verified_checksum=checksum,
            owner="test-owner",
        ),
    }


@pytest.fixture
def drifted_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> dict[str, SkillEntry]:
    """Build a 1-entry catalog with an intentionally wrong checksum.

    The catalog's ``last_verified_checksum`` does NOT match the on-disk
    checksum, so ``check_drift`` returns a single ``checksum_mismatch``
    finding. The CLI surface must surface this as exit code 1.
    """
    sidecar = tmp_path / ".flow-engineering" / "prompt_checksums.json"

    def _fake_sidecar_path() -> Path:
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        return sidecar

    monkeypatch.setattr(osc, "_read_sidecar", lambda: {})
    monkeypatch.setattr(osc, "_sidecar_path", _fake_sidecar_path)

    skill = tmp_path / "SKILL.md"
    skill.write_text(
        '---\nname: sdd-test\ndescription: mock\nversion: "3.0"\n---\n\nBody.\n',
        encoding="utf-8",
    )
    return {
        "sdd-test/skill": SkillEntry(
            skill_name="sdd-test",
            surface="skill",
            expected_version="3.0",
            expected_path=str(skill),
            last_verified_checksum="0" * 64,  # intentionally wrong
            owner="test-owner",
        ),
    }


# ---------- T2.1: flow prompts group + check subcommand ----------


class TestFlowPromptsGroup:
    def test_flow_help_lists_prompts_group(self) -> None:
        """`flow --help` must list the `prompts` command group.

        Confirms the Click group is registered on the ``main`` Click
        object so users can discover it via the standard CLI help.
        """
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0, (
            f"flow --help failed: stdout={result.output!r} "
            f"exit={result.exit_code}"
        )
        assert "prompts" in result.output, (
            f"expected 'prompts' in flow --help output; got {result.output!r}"
        )

    def test_prompts_check_exits_zero_on_clean_state(
        self, clean_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts check` returns exit 0 when no drift is detected.

        With a single-entry catalog whose on-disk checksum matches the
        catalog's ``last_verified_checksum``, ``check_drift`` returns an
        empty list and the CLI exits 0. The expected-version string
        ``"3.0"`` MUST appear in stdout so users can audit the verified
        entries.
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", clean_catalog)
        result = runner.invoke(main, ["prompts", "check"])
        assert result.exit_code == 0, (
            f"expected exit 0 on clean state; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "3.0" in result.stdout or "verified" in result.stdout, (
            f"expected version or 'verified' marker in stdout; "
            f"got {result.stdout!r}"
        )

    def test_prompts_check_exits_one_on_drift(
        self, drifted_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts check` returns exit 1 when drift is detected.

        With a single-entry catalog whose on-disk checksum does NOT match
        the catalog's ``last_verified_checksum``, ``check_drift`` returns a
        ``checksum_mismatch`` finding and the CLI exits 1. The drift line
        MUST appear in stdout so users can see which entry diverged.
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", drifted_catalog)
        result = runner.invoke(main, ["prompts", "check"])
        assert result.exit_code == 1, (
            f"expected exit 1 on drift; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "sdd-test" in result.stdout or "drift" in result.stdout.lower(), (
            f"expected skill name or drift marker in stdout; "
            f"got {result.stdout!r}"
        )