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
    FRONTMATTER_PATTERN,
    SIDECAR_PATH,
    SKILL_CATALOG,
    SkillDrift,
    SkillEntry,
    SkillVersionError,
    compute_frontmatter_sha256,
    parse_frontmatter,
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


# ---------- T1.2: frontmatter checksum + parser ----------


_FRONTMATTER_TEXT = (
    "---\n"
    "name: sdd-apply\n"
    "description: test\n"
    "version: \"3.0\"\n"
    "metadata:\n"
    "  author: gentleman-programming\n"
    "---\n\n"
    "Body content here.\n"
)


class TestFrontmatterPattern:
    def test_frontmatter_pattern_matches_double_dash_block(self) -> None:
        match = FRONTMATTER_PATTERN.match(_FRONTMATTER_TEXT)
        assert match is not None
        assert match.group(1).startswith("name: sdd-apply")

    def test_frontmatter_pattern_rejects_no_dashes(self) -> None:
        assert FRONTMATTER_PATTERN.match("no frontmatter here\n") is None


class TestComputeFrontmatterChecksum:
    def test_compute_frontmatter_checksum_returns_64_char_hex(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(_FRONTMATTER_TEXT, encoding="utf-8")
        digest = compute_frontmatter_sha256(skill)
        assert isinstance(digest, str)
        assert re.fullmatch(r"[0-9a-f]{64}", digest)

    def test_compute_frontmatter_checksum_is_deterministic(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(_FRONTMATTER_TEXT, encoding="utf-8")
        first = compute_frontmatter_sha256(skill)
        second = compute_frontmatter_sha256(skill)
        assert first == second

    def test_compute_frontmatter_checksum_ignores_body_whitespace(self, tmp_path: Path) -> None:
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        body_a = "Body content here.\n"
        body_b = "Body content here.\n\n\n   \n\nMore body lines.\n"
        a.write_text(_FRONTMATTER_TEXT.replace("Body content here.\n", body_a), encoding="utf-8")
        b.write_text(_FRONTMATTER_TEXT.replace("Body content here.\n", body_b), encoding="utf-8")
        assert compute_frontmatter_sha256(a) == compute_frontmatter_sha256(b)

    def test_compute_frontmatter_checksum_detects_field_change(self, tmp_path: Path) -> None:
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        a.write_text(_FRONTMATTER_TEXT, encoding="utf-8")
        b.write_text(
            _FRONTMATTER_TEXT.replace('description: test', 'description: changed'),
            encoding="utf-8",
        )
        assert compute_frontmatter_sha256(a) != compute_frontmatter_sha256(b)

    def test_compute_frontmatter_checksum_preserves_unicode(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: sdd-apply\ndescription: \"hola mundo ñ\"\n---\n",
            encoding="utf-8",
        )
        digest = compute_frontmatter_sha256(skill)
        assert re.fullmatch(r"[0-9a-f]{64}", digest)


class TestParseFrontmatter:
    def test_parse_frontmatter_returns_dict(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(_FRONTMATTER_TEXT, encoding="utf-8")
        parsed = parse_frontmatter(skill)
        assert isinstance(parsed, dict)
        assert parsed["name"] == "sdd-apply"
        assert parsed["version"] == "3.0"

    def test_parse_frontmatter_raises_skill_version_error_when_missing(
        self, tmp_path: Path,
    ) -> None:
        no_fm = tmp_path / "no-fm.md"
        no_fm.write_text("Just body, no frontmatter.\n", encoding="utf-8")
        with pytest.raises(SkillVersionError, match="no YAML frontmatter"):
            parse_frontmatter(no_fm)

    def test_parse_frontmatter_raises_when_not_dict(self, tmp_path: Path) -> None:
        scalar_fm = tmp_path / "scalar.md"
        scalar_fm.write_text("---\njust a string\n---\n", encoding="utf-8")
        with pytest.raises(SkillVersionError, match="not a YAML dict"):
            parse_frontmatter(scalar_fm)

    def test_parse_frontmatter_raises_skill_version_error_on_missing_file(
        self, tmp_path: Path,
    ) -> None:
        ghost = tmp_path / "ghost.md"
        with pytest.raises(SkillVersionError):
            parse_frontmatter(ghost)
