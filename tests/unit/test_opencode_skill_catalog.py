"""RED fixtures for opencode_skill_catalog.py (REQ-49, T1.1).

REQ-49 D1 + D6: 20-entry catalog of OpenCode runtime SKILL.md agent prompts,
frozen dataclass schema for ``SkillEntry`` (6 fields) + ``SkillDrift`` (7 fields),
``SkillVersionError`` exception, and a ``SIDECAR_PATH`` constant at
``~/.flow-engineering/prompt_checksums.json``.

These tests are written BEFORE the implementation per strict TDD (RED).
They MUST fail with ``ImportError`` or ``AttributeError`` until the
GREEN commit lands.
"""
from __future__ import annotations

import re
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from flow_engineering.opencode_skill_catalog import (
    SKILL_CATALOG,
    SIDECAR_PATH,
    SkillDrift,
    SkillEntry,
    SkillVersionError,
)


# ---------- Fixtures ----------


@pytest.fixture
def sample_entry() -> SkillEntry:
    """Construct a representative SkillEntry used by schema tests."""
    return SkillEntry(
        skill_name="sdd-apply",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-apply/SKILL.md",
        last_verified_checksum="a" * 64,
        owner="gentleman-programming",
    )


# ---------- SkillEntry schema ----------


class TestSkillEntrySchema:
    def test_skill_entry_is_frozen_dataclass(self) -> None:
        assert is_dataclass(SkillEntry)
        entry = SkillEntry(
            skill_name="sdd-apply",
            surface="skill",
            expected_version="3.0",
            expected_path="~/.config/opencode/skills/sdd-apply/SKILL.md",
            last_verified_checksum="a" * 64,
            owner="gentleman-programming",
        )
        with pytest.raises(FrozenInstanceError):
            entry.skill_name = "sdd-other"  # type: ignore[misc]

    def test_skill_entry_has_exactly_six_fields(self) -> None:
        field_names = {f.name for f in fields(SkillEntry)}
        assert field_names == {
            "skill_name",
            "surface",
            "expected_version",
            "expected_path",
            "last_verified_checksum",
            "owner",
        }

    def test_skill_entry_skill_name_is_kebab_case(self, sample_entry: SkillEntry) -> None:
        assert re.fullmatch(r"[a-z0-9-]+", sample_entry.skill_name)

    def test_skill_entry_surface_is_valid(self, sample_entry: SkillEntry) -> None:
        assert sample_entry.surface in {"skill", "prompt"}

    def test_skill_entry_expected_version_is_major_minor(self, sample_entry: SkillEntry) -> None:
        assert re.fullmatch(r"\d+\.\d+", sample_entry.expected_version)

    def test_skill_entry_expected_path_is_string(self, sample_entry: SkillEntry) -> None:
        assert isinstance(sample_entry.expected_path, str)
        assert sample_entry.expected_path  # non-empty

    def test_skill_entry_last_verified_checksum_is_64_hex(
        self, sample_entry: SkillEntry,
    ) -> None:
        assert re.fullmatch(r"[0-9a-f]{64}", sample_entry.last_verified_checksum)

    def test_skill_entry_owner_is_non_empty(self, sample_entry: SkillEntry) -> None:
        assert isinstance(sample_entry.owner, str)
        assert sample_entry.owner


# ---------- SkillDrift schema ----------


class TestSkillDriftSchema:
    def test_skill_drift_is_frozen_dataclass(self) -> None:
        assert is_dataclass(SkillDrift)
        drift = SkillDrift(
            skill_name="sdd-apply",
            surface="skill",
            expected_version="3.0",
            on_disk_version="2.0",
            expected_checksum="a" * 64,
            on_disk_checksum="b" * 64,
            drift_kind="checksum_mismatch",
        )
        with pytest.raises(FrozenInstanceError):
            drift.skill_name = "sdd-other"  # type: ignore[misc]

    def test_skill_drift_has_seven_fields(self) -> None:
        field_names = {f.name for f in fields(SkillDrift)}
        assert field_names == {
            "skill_name",
            "surface",
            "expected_version",
            "on_disk_version",
            "expected_checksum",
            "on_disk_checksum",
            "drift_kind",
        }

    @pytest.mark.parametrize(
        "drift_kind",
        [
            "version_mismatch",
            "checksum_mismatch",
            "missing_file",
            "frontmatter_parse_error",
        ],
    )
    def test_skill_drift_kind_is_one_of_four(self, drift_kind: str) -> None:
        drift = SkillDrift(
            skill_name="sdd-apply",
            surface="skill",
            expected_version="3.0",
            on_disk_version="2.0",
            expected_checksum="a" * 64,
            on_disk_checksum="b" * 64,
            drift_kind=drift_kind,
        )
        assert drift.drift_kind == drift_kind


# ---------- SIDECAR_PATH ----------


class TestSidecarPath:
    def test_sidecar_path_lives_under_flow_engineering_dir(self) -> None:
        assert isinstance(SIDECAR_PATH, Path)
        assert SIDECAR_PATH.name == "prompt_checksums.json"
        assert SIDECAR_PATH.parent.name == ".flow-engineering"
        assert SIDECAR_PATH.parent.parent == Path.home()


# ---------- SkillVersionError ----------


class TestSkillVersionError:
    def test_skill_version_error_is_exception_subclass(self) -> None:
        assert issubclass(SkillVersionError, Exception)
        with pytest.raises(SkillVersionError, match="boom"):
            raise SkillVersionError("boom")


# ---------- SKILL_CATALOG shape ----------


class TestSkillCatalog:
    def test_skill_catalog_is_dict(self) -> None:
        assert isinstance(SKILL_CATALOG, dict)

    def test_skill_catalog_has_exactly_20_entries(self) -> None:
        assert len(SKILL_CATALOG) == 20

    def test_skill_catalog_keys_use_skill_name_slash_surface(self) -> None:
        for key in SKILL_CATALOG:
            assert "/" in key, f"key {key!r} missing slash separator"
            skill_name, surface = key.split("/", 1)
            assert surface in {"skill", "prompt"}
            assert re.fullmatch(r"[a-z0-9-]+", skill_name)

    def test_skill_catalog_covers_both_surfaces_per_agent(self) -> None:
        skill_names = {key.split("/", 1)[0] for key in SKILL_CATALOG}
        assert len(skill_names) == 10
        for skill_name in skill_names:
            assert f"{skill_name}/skill" in SKILL_CATALOG
            assert f"{skill_name}/prompt" in SKILL_CATALOG

    def test_skill_catalog_covers_ten_sdd_agents(self) -> None:
        skill_names = {key.split("/", 1)[0] for key in SKILL_CATALOG}
        expected = {
            "sdd-init",
            "sdd-explore",
            "sdd-propose",
            "sdd-design",
            "sdd-spec",
            "sdd-tasks",
            "sdd-apply",
            "sdd-verify",
            "sdd-archive",
            "sdd-onboard",
        }
        assert skill_names == expected

    def test_every_skill_entry_has_64_char_hex_checksum(self) -> None:
        for key, entry in SKILL_CATALOG.items():
            assert re.fullmatch(
                r"[0-9a-f]{64}", entry.last_verified_checksum,
            ), f"{key}: checksum {entry.last_verified_checksum!r} is not 64-char hex"

    def test_every_skill_entry_has_valid_surface(self) -> None:
        for entry in SKILL_CATALOG.values():
            assert entry.surface in {"skill", "prompt"}

    def test_every_skill_entry_has_major_minor_version(self) -> None:
        for key, entry in SKILL_CATALOG.items():
            assert re.fullmatch(
                r"\d+\.\d+", entry.expected_version,
            ), f"{key}: version {entry.expected_version!r} is not MAJOR.MINOR"