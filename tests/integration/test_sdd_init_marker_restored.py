"""Integration test for REQ-V1.3.1 (sdd-init marker restore).

Asserts that the 3 marker files exist on disk, are tracked in git, and
that ``flow_engineering.strict_tdd.load_sdd_init(repo_root)`` returns a
non-None mapping with ``strict_tdd: True`` after the (a) commit lands.

Article III (Strict TDD) enforcement is dormant on ``main`` until this
passes. See ``openspec/changes/v1.3-platform-hardening/spec.md`` REQ-V1.3.1
for the BDD scenarios this test codifies.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from flow_engineering.strict_tdd import load_sdd_init

REPO_ROOT = Path(__file__).resolve().parents[2]
ON_MARKERS = (
    "strict_tdd: true",
    "Strict TDD: ON",
    "Strict TDD:** ON",
    "Strict TDD:** **ON",
)


def _git_ls_files(*paths: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", *paths],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    )
    return [line for line in result.stdout.splitlines() if line]


class TestSddInitMarkerRestored:
    def test_marker_md_exists_and_tracked(self) -> None:
        marker = REPO_ROOT / "sdd-init" / "flow-engineering.md"
        assert marker.exists(), f"missing marker file: {marker}"
        tracked = _git_ls_files("sdd-init/flow-engineering.md")
        assert tracked == ["sdd-init/flow-engineering.md"]

    def test_marker_body_matches_on_markers_pattern(self) -> None:
        content = (REPO_ROOT / "sdd-init" / "flow-engineering.md").read_text(
            encoding="utf-8"
        )
        assert any(m in content for m in ON_MARKERS), (
            f"marker body must contain one of {ON_MARKERS}"
        )

    def test_openspec_config_yaml_exists_and_tracked(self) -> None:
        cfg = REPO_ROOT / "openspec" / "config.yaml"
        assert cfg.exists(), f"missing openspec config: {cfg}"
        tracked = _git_ls_files("openspec/config.yaml")
        assert tracked == ["openspec/config.yaml"]

    def test_skill_registry_exists_and_tracked(self) -> None:
        registry = REPO_ROOT / ".atl" / "skill-registry.md"
        assert registry.exists(), f"missing skill registry: {registry}"
        tracked = _git_ls_files(".atl/skill-registry.md")
        assert tracked == [".atl/skill-registry.md"]

    def test_load_sdd_init_returns_non_none_with_strict_tdd_true(self) -> None:
        result = load_sdd_init(REPO_ROOT)
        assert result is not None
        assert result.get("strict_tdd") is True
