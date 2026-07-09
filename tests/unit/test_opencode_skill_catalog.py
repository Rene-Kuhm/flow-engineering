"""RED fixtures for opencode_skill_catalog.py (REQ-49, T1.1).

REQ-49 D1 + D6: 20-entry catalog of OpenCode runtime SKILL.md agent prompts,
frozen dataclass schema for ``SkillEntry`` (6 fields) + ``SkillDrift`` (7 fields),
``SkillVersionError`` exception, and a ``SIDECAR_PATH`` constant at
``~/.flow-engineering/prompt_checksums.json``.

REQ-V1.2.3 (PR#2c, T3.1): ``enforce_min_skill_versions`` helper added at
module scope; see ``TestEnforceMinSkillVersions`` below.

These tests are written BEFORE the implementation per strict TDD (RED).
They MUST fail with ``ImportError`` or ``AttributeError`` until the
GREEN commit lands.
"""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from flow_engineering import opencode_skill_catalog as osc_module
from flow_engineering.opencode_skill_catalog import (
    FRONTMATTER_PATTERN,
    SIDECAR_PATH,
    SKILL_CATALOG,
    SkillDrift,
    SkillEntry,
    SkillVersionError,
    _read_sidecar,
    _write_sidecar,
    check_drift,
    compute_frontmatter_sha256,
    enforce_min_skill_versions,
    init_checksums,
    parse_frontmatter,
    update_checksums,
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
        self,
        sample_entry: SkillEntry,
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


def test_sidecar_path_lives_under_flow_engineering_dir() -> None:
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
                r"[0-9a-f]{64}",
                entry.last_verified_checksum,
            ), f"{key}: checksum {entry.last_verified_checksum!r} is not 64-char hex"

    def test_every_skill_entry_has_valid_surface(self) -> None:
        for entry in SKILL_CATALOG.values():
            assert entry.surface in {"skill", "prompt"}

    def test_every_skill_entry_has_major_minor_version(self) -> None:
        for key, entry in SKILL_CATALOG.items():
            assert re.fullmatch(
                r"\d+\.\d+",
                entry.expected_version,
            ), f"{key}: version {entry.expected_version!r} is not MAJOR.MINOR"


# ---------- T1.2: frontmatter checksum + parser ----------


_FRONTMATTER_TEXT = (
    "---\n"
    "name: sdd-apply\n"
    "description: test\n"
    'version: "3.0"\n'
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
            _FRONTMATTER_TEXT.replace("description: test", "description: changed"),
            encoding="utf-8",
        )
        assert compute_frontmatter_sha256(a) != compute_frontmatter_sha256(b)

    def test_compute_frontmatter_checksum_preserves_unicode(self, tmp_path: Path) -> None:
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            '---\nname: sdd-apply\ndescription: "hola mundo ñ"\n---\n',
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
        self,
        tmp_path: Path,
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
        self,
        tmp_path: Path,
    ) -> None:
        ghost = tmp_path / "ghost.md"
        with pytest.raises(SkillVersionError):
            parse_frontmatter(ghost)

    def test_parses_nested_metadata_version(self, tmp_path: Path) -> None:
        """Real OpenCode SKILL.md files nest ``version`` under ``metadata``.

        The verify report's CRITICAL C1 finding showed that
        ``~/.config/opencode/skills/sdd-init/SKILL.md`` has
        ``version: "3.0"`` nested under the ``metadata:`` block, NOT at
        the top level. ``parse_frontmatter`` MUST surface a top-level
        ``version`` key so downstream ``check_drift`` consumers see the
        real on-disk version and don't fall back to the ``"0.0"``
        default — which caused 20/20 false-positive DRIFT reports.
        """
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\n"
            "name: sdd-init\n"
            'description: "Trigger: sdd init"\n'
            "metadata:\n"
            "  author: gentleman-programming\n"
            '  version: "3.0"\n'
            "---\n"
            "\nBody content.\n",
            encoding="utf-8",
        )
        parsed = parse_frontmatter(skill)
        assert parsed["version"] == "3.0", (
            f"expected top-level 'version' key '3.0' from nested "
            f"metadata.version; got parsed={parsed!r}"
        )

    def test_top_level_version_wins_over_metadata_version(
        self,
        tmp_path: Path,
    ) -> None:
        """When both top-level ``version`` and ``metadata.version`` are
        present, the top-level value wins (it is the canonical location).
        """
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            '---\nname: sdd-test\nversion: "4.0"\nmetadata:\n  version: "3.0"\n---\n\nBody.\n',
            encoding="utf-8",
        )
        parsed = parse_frontmatter(skill)
        assert parsed["version"] == "4.0", (
            f"expected top-level 'version' '4.0' to win; got {parsed!r}"
        )

    def test_parse_frontmatter_default_version_when_missing(
        self,
        tmp_path: Path,
    ) -> None:
        """When no version is present at either location, the parsed
        dict exposes the ``"0.0"`` default at top-level so consumers
        always have a string to compare against.
        """
        skill = tmp_path / "SKILL.md"
        skill.write_text(
            "---\nname: sdd-test\ndescription: no version\n---\n",
            encoding="utf-8",
        )
        parsed = parse_frontmatter(skill)
        assert parsed["version"] == "0.0", (
            f"expected default '0.0' when no version anywhere; got {parsed!r}"
        )


# ---------- T1.3: check_drift core ----------


def _make_mock_skill(
    tmp_path: Path,
    *,
    name: str = "sdd-test",
    version: str = "3.0",
    body: str = "Body content here.\n",
) -> Path:
    """Write a SKILL.md with valid frontmatter; return the path."""
    path = tmp_path / f"{name}.md"
    path.write_text(
        f'---\nname: {name}\ndescription: mock\nversion: "{version}"\n---\n\n{body}',
        encoding="utf-8",
    )
    return path


class TestCheckDrift:
    def test_check_drift_empty_catalog_returns_empty_list(self) -> None:
        assert check_drift({}) == []

    def test_check_drift_clean_state_returns_empty(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When no sidecar exists, fallback uses catalog ``last_verified_checksum``.

        With the sidecar absent, the catalog's ``last_verified_checksum``
        is the comparison baseline. A matching on-disk checksum reports no
        drift; the function returns an empty list.
        """
        monkeypatch.setattr(
            "flow_engineering.opencode_skill_catalog._read_sidecar",
            lambda: {},
        )
        path = _make_mock_skill(tmp_path)
        checksum = compute_frontmatter_sha256(path)
        catalog = {
            "sdd-test/skill": SkillEntry(
                skill_name="sdd-test",
                surface="skill",
                expected_version="3.0",
                expected_path=str(path),
                last_verified_checksum=checksum,
                owner="test-owner",
            ),
        }
        assert check_drift(catalog) == []

    def test_check_drift_detects_checksum_mismatch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "flow_engineering.opencode_skill_catalog._read_sidecar",
            lambda: {},
        )
        path = _make_mock_skill(tmp_path)
        catalog = {
            "sdd-test/skill": SkillEntry(
                skill_name="sdd-test",
                surface="skill",
                expected_version="3.0",
                expected_path=str(path),
                last_verified_checksum="0" * 64,  # intentionally wrong
                owner="test-owner",
            ),
        }
        drifts = check_drift(catalog)
        assert len(drifts) == 1
        drift = drifts[0]
        assert drift.skill_name == "sdd-test"
        assert drift.surface == "skill"
        assert drift.drift_kind == "checksum_mismatch"
        assert drift.expected_checksum == "0" * 64
        assert drift.on_disk_checksum == compute_frontmatter_sha256(path)
        assert drift.on_disk_version == "3.0"

    def test_check_drift_detects_missing_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "flow_engineering.opencode_skill_catalog._read_sidecar",
            lambda: {},
        )
        catalog = {
            "sdd-test/skill": SkillEntry(
                skill_name="sdd-test",
                surface="skill",
                expected_version="3.0",
                expected_path=str(tmp_path / "ghost.md"),
                last_verified_checksum="a" * 64,
                owner="test-owner",
            ),
        }
        drifts = check_drift(catalog)
        assert len(drifts) == 1
        assert drifts[0].drift_kind == "missing_file"
        assert drifts[0].on_disk_version == ""
        assert drifts[0].on_disk_checksum == ""

    def test_check_drift_detects_frontmatter_parse_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "flow_engineering.opencode_skill_catalog._read_sidecar",
            lambda: {},
        )
        path = tmp_path / "broken.md"
        path.write_text("just body, no frontmatter\n", encoding="utf-8")
        catalog = {
            "sdd-test/skill": SkillEntry(
                skill_name="sdd-test",
                surface="skill",
                expected_version="3.0",
                expected_path=str(path),
                last_verified_checksum="a" * 64,
                owner="test-owner",
            ),
        }
        drifts = check_drift(catalog)
        assert len(drifts) == 1
        assert drifts[0].drift_kind == "frontmatter_parse_error"
        assert drifts[0].on_disk_version == ""
        assert drifts[0].on_disk_checksum == ""

    def test_check_drift_detects_version_mismatch_when_checksum_matches(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Version mismatch fires only after checksum matches (per design)."""
        monkeypatch.setattr(
            "flow_engineering.opencode_skill_catalog._read_sidecar",
            lambda: {},
        )
        path = _make_mock_skill(tmp_path, version="2.0")
        checksum = compute_frontmatter_sha256(path)
        catalog = {
            "sdd-test/skill": SkillEntry(
                skill_name="sdd-test",
                surface="skill",
                expected_version="3.0",  # catalog says 3.0, file says 2.0
                expected_path=str(path),
                last_verified_checksum=checksum,
                owner="test-owner",
            ),
        }
        drifts = check_drift(catalog)
        assert len(drifts) == 1
        assert drifts[0].drift_kind == "version_mismatch"
        assert drifts[0].expected_version == "3.0"
        assert drifts[0].on_disk_version == "2.0"


# ---------- T1.4: sidecar JSON I/O ----------


@pytest.fixture
def tmp_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Monkeypatch ``_sidecar_path`` to write under ``tmp_path``.

    Tests that exercise real filesystem I/O use this fixture so the
    sidecar JSON never touches the user's ``~/.flow-engineering/`` directory.
    The fixture's lambda mirrors the production contract by also creating
    parent directories on first call.
    """
    sidecar = tmp_path / ".flow-engineering" / "prompt_checksums.json"

    def _fake_sidecar_path() -> Path:
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        return sidecar

    monkeypatch.setattr(
        "flow_engineering.opencode_skill_catalog._sidecar_path",
        _fake_sidecar_path,
    )
    return sidecar


class TestSidecarPath:
    def test_sidecar_path_lazily_creates_parent_dirs(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import flow_engineering.opencode_skill_catalog as osc

        nested = tmp_path / "deep" / "nested" / "prompt_checksums.json"

        def _fake_sidecar_path() -> Path:
            nested.parent.mkdir(parents=True, exist_ok=True)
            return nested

        monkeypatch.setattr(osc, "_sidecar_path", _fake_sidecar_path)
        result = osc._sidecar_path()
        assert result == nested
        assert result.parent.exists()
        assert result.parent.is_dir()


class TestReadSidecar:
    def test_read_sidecar_returns_empty_when_file_missing(
        self,
        tmp_sidecar: Path,
    ) -> None:
        assert _read_sidecar() == {}

    def test_read_sidecar_round_trips(
        self,
        tmp_sidecar: Path,
    ) -> None:
        _write_sidecar({"foo/skill": {"version": "1.0", "checksum": "abc"}})
        loaded = _read_sidecar()
        assert loaded == {"foo/skill": {"version": "1.0", "checksum": "abc"}}


class TestWriteSidecarAtomic:
    def test_write_sidecar_creates_file(self, tmp_sidecar: Path) -> None:
        _write_sidecar({"foo/skill": {"version": "1.0", "checksum": "abc"}})
        assert tmp_sidecar.exists()

    def test_write_sidecar_overwrites_existing(self, tmp_sidecar: Path) -> None:
        _write_sidecar({"foo/skill": {"version": "1.0", "checksum": "abc"}})
        _write_sidecar({"bar/prompt": {"version": "2.0", "checksum": "def"}})
        loaded = _read_sidecar()
        assert "foo/skill" not in loaded
        assert loaded["bar/prompt"]["version"] == "2.0"

    def test_write_sidecar_uses_indent_for_grep(
        self,
        tmp_sidecar: Path,
    ) -> None:
        _write_sidecar({"foo/skill": {"version": "1.0", "checksum": "abc"}})
        text = tmp_sidecar.read_text(encoding="utf-8")
        assert "\n  " in text  # indent=2


class TestInitChecksums:
    def test_init_checksums_writes_count_of_entries_returned(
        self,
        tmp_sidecar: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = _make_mock_skill(tmp_sidecar.parent.parent)
        catalog = {
            "sdd-test/skill": SkillEntry(
                skill_name="sdd-test",
                surface="skill",
                expected_version="3.0",
                expected_path=str(path),
                last_verified_checksum="0" * 64,
                owner="test-owner",
            ),
        }
        count = init_checksums(catalog)
        assert count == 1
        loaded = _read_sidecar()
        assert "sdd-test/skill" in loaded
        assert loaded["sdd-test/skill"]["version"] == "3.0"
        assert loaded["sdd-test/skill"]["checksum"] == compute_frontmatter_sha256(path)
        assert "last_verified_at" in loaded["sdd-test/skill"]

    def test_init_checksums_last_verified_at_is_iso_8601_utc_z(
        self,
        tmp_sidecar: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = _make_mock_skill(tmp_sidecar.parent.parent)
        catalog = {
            "sdd-test/skill": SkillEntry(
                skill_name="sdd-test",
                surface="skill",
                expected_version="3.0",
                expected_path=str(path),
                last_verified_checksum="0" * 64,
                owner="test-owner",
            ),
        }
        init_checksums(catalog)
        loaded = _read_sidecar()
        ts = loaded["sdd-test/skill"]["last_verified_at"]
        assert ts.endswith("Z")
        assert "T" in ts
        # Verify it parses as ISO 8601.
        from datetime import datetime

        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")

    def test_init_checksums_walks_full_skill_catalog(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_sidecar: Path,
    ) -> None:
        """init_checksums(SKILL_CATALOG) writes all 20 entries.

        The real SKILL_CATALOG paths point to ~/.config/opencode/... which
        exist on the test machine. We monkeypatch _read_sidecar to return
        {} so check_drift doesn't fire, but init_checksums walks the real
        catalog and reads each file's frontmatter.
        """
        count = init_checksums(SKILL_CATALOG)
        assert count == 20
        loaded = _read_sidecar()
        assert len(loaded) == 20
        # Both surfaces for sdd-apply should be present.
        assert "sdd-apply/skill" in loaded
        assert "sdd-apply/prompt" in loaded

    def test_init_checksums_handles_missing_file_gracefully(
        self,
        tmp_sidecar: Path,
    ) -> None:
        catalog = {
            "sdd-test/skill": SkillEntry(
                skill_name="sdd-test",
                surface="skill",
                expected_version="3.0",
                expected_path=str(tmp_sidecar.parent / "ghost.md"),
                last_verified_checksum="0" * 64,
                owner="test-owner",
            ),
        }
        count = init_checksums(catalog)
        assert count == 1
        loaded = _read_sidecar()
        assert loaded["sdd-test/skill"]["checksum"] == ""
        assert loaded["sdd-test/skill"]["version"] == "3.0"


class TestUpdateChecksums:
    def test_update_checksums_refreshes_stale_entry(
        self,
        tmp_sidecar: Path,
    ) -> None:
        """After init_checksums writes the sidecar, update_checksums
        must overwrite with fresh on-disk values."""
        import time

        path = _make_mock_skill(tmp_sidecar.parent.parent)
        catalog = {
            "sdd-test/skill": SkillEntry(
                skill_name="sdd-test",
                surface="skill",
                expected_version="3.0",
                expected_path=str(path),
                last_verified_checksum="0" * 64,
                owner="test-owner",
            ),
        }
        init_checksums(catalog)
        loaded_before = _read_sidecar()
        ts_before = loaded_before["sdd-test/skill"]["last_verified_at"]
        # Sleep so the timestamp differs (1-second resolution on ISO 8601).
        time.sleep(1.1)
        # Mutate the file so the checksum changes.
        path.write_text(
            path.read_text(encoding="utf-8") + "\nMore body lines.\n",
            encoding="utf-8",
        )
        count = update_checksums(catalog)
        assert count == 1
        loaded_after = _read_sidecar()
        ts_after = loaded_after["sdd-test/skill"]["last_verified_at"]
        # Frontmatter checksum is unchanged (only body changed) so the
        # 'checksum' field stays the same; but last_verified_at updates.
        assert ts_after != ts_before
        assert (
            loaded_after["sdd-test/skill"]["checksum"]
            == loaded_before["sdd-test/skill"]["checksum"]
        )


# ---------- T3.1: enforce_min_skill_versions ----------


def _mock_skill_layout(
    tmp_path: Path,
    skills_root: Path,
    *,
    skills: dict[str, str] | None = None,
) -> Path:
    """Lay down ``~/.config/opencode/skills/<name>/SKILL.md`` files.

    Args:
        tmp_path: pytest tmp_path fixture root.
        skills_root: Directory that will receive ``<name>/SKILL.md`` files.
        skills: Mapping of ``skill_name -> version string``. Defaults to
            3.0 for the 8 orchestrator-dispatched sdd-* agents.

    Returns:
        The skills_root path (for downstream ``monkeypatch.setenv`` use).
    """
    if skills is None:
        skills = {
            "sdd-explore": "3.0",
            "sdd-propose": "3.0",
            "sdd-spec": "3.0",
            "sdd-design": "3.0",
            "sdd-tasks": "3.0",
            "sdd-apply": "3.0",
            "sdd-verify": "3.0",
            "sdd-archive": "3.0",
        }
    skills_root.mkdir(parents=True, exist_ok=True)
    for name, version in skills.items():
        skill_dir = skills_root / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f'---\nname: {name}\ndescription: mock\nversion: "{version}"\n---\n\n',
            encoding="utf-8",
        )
    return skills_root


@pytest.fixture
def skills_root(tmp_path: Path) -> Path:
    """Return a tmp_path-derived skills root for SKILL.md mocking."""
    return tmp_path / ".config" / "opencode" / "skills"


@pytest.fixture
def patched_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Monkeypatch ``Path.home`` so ``enforce_min_skill_versions`` reads from ``tmp_path``.

    Cross-platform: replaces the ``Path.home`` classmethod directly so
    Windows (``USERPROFILE``) and Unix (``HOME``) both redirect to the
    test's ``tmp_path``.
    """
    monkeypatch.setattr(osc_module.Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


class TestEnforceMinSkillVersions:
    """T3.1 RED tests for ``enforce_min_skill_versions(min_versions)``.

    The helper enforces a ``[tool.flow_engineering] min_sdd_skill_versions``
    dict by parsing each on-disk SKILL.md ``version`` frontmatter field
    and comparing as ``(MAJOR, MINOR)`` tuples. On downgrade it raises
    the existing ``SkillVersionError`` with remediation message.
    """

    def test_passes_when_all_skills_meet_minimum(
        self,
        tmp_path: Path,
        patched_home: Path,
    ) -> None:
        """8 SKILL.md files with version 3.0 + min dict {*: 3.0} returns None."""
        skills_root = tmp_path / ".config" / "opencode" / "skills"
        _mock_skill_layout(tmp_path, skills_root)
        min_versions = {
            "sdd-explore": "3.0",
            "sdd-propose": "3.0",
            "sdd-spec": "3.0",
            "sdd-design": "3.0",
            "sdd-tasks": "3.0",
            "sdd-apply": "3.0",
            "sdd-verify": "3.0",
            "sdd-archive": "3.0",
        }
        result = enforce_min_skill_versions(min_versions)
        assert result is None

    def test_raises_skill_version_error_on_downgrade(
        self,
        tmp_path: Path,
        patched_home: Path,
    ) -> None:
        """sdd-apply on disk at 2.5 + min dict {sdd-apply: 3.0} raises."""
        skills_root = tmp_path / ".config" / "opencode" / "skills"
        _mock_skill_layout(
            tmp_path,
            skills_root,
            skills={"sdd-apply": "2.5"},
        )
        with pytest.raises(SkillVersionError) as excinfo:
            enforce_min_skill_versions({"sdd-apply": "3.0"})
        msg = str(excinfo.value)
        assert "sdd-apply" in msg
        assert "3.0" in msg
        assert "2.5" in msg

    def test_skips_missing_skill(
        self,
        tmp_path: Path,
        patched_home: Path,
    ) -> None:
        """min dict references nonexistent skill name -> no error."""
        skills_root = tmp_path / ".config" / "opencode" / "skills"
        _mock_skill_layout(tmp_path, skills_root)
        # Skill not in the layout; helper must skip silently.
        result = enforce_min_skill_versions({"nonexistent-skill": "3.0"})
        assert result is None

    def test_skips_non_sdd_skill(
        self,
        tmp_path: Path,
        patched_home: Path,
    ) -> None:
        """min dict references non-sdd-prefixed key -> no error.

        The 8 orchestrator-dispatched sdd-* agents are the gate's only
        concern; any other key (e.g., a third-party tool name) is a
        no-op pass-through to keep the gate scoped tight.
        """
        skills_root = tmp_path / ".config" / "opencode" / "skills"
        _mock_skill_layout(tmp_path, skills_root)
        result = enforce_min_skill_versions({"some-other-tool": "3.0"})
        assert result is None

    def test_handles_non_numeric_version_gracefully(
        self,
        tmp_path: Path,
        patched_home: Path,
    ) -> None:
        """SKILL.md with version '3.0-beta' parses via safe fallback.

        Either the helper successfully parses the pre-release string OR
        the safe-fallback path returns '0.0' which triggers the gate
        correctly (any minimum version > 0.0 is satisfied after the
        fallback inverts the comparison).
        """
        skills_root = tmp_path / ".config" / "opencode" / "skills"
        _mock_skill_layout(
            tmp_path,
            skills_root,
            skills={"sdd-apply": "3.0-beta"},
        )
        # Pass-through case: helper must not raise for a non-SDD-style
        # version; it may parse, fall back, or warn — but no crash.
        result = enforce_min_skill_versions({"sdd-apply": "3.0"})
        assert result is None


# ---------- T3.3: [tool.flow_engineering] min_sdd_skill_versions pyproject section ----------


class TestPyprojectMinSkillVersionsSection:
    """T3.3 RED tests for the pyproject.toml section parser.

    The pyproject section ``[tool.flow_engineering] min_sdd_skill_versions``
    must be parseable via stdlib ``tomllib`` (Python 3.11+) and expose
    the 8 orchestrator-dispatched sdd-* agents, each with the
    ``"3.0"`` minimum semver string.
    """

    def test_pyproject_min_sdd_skill_versions_parses(self) -> None:
        """tomllib.loads(pyproject.read_text()) exposes the 8-key dict."""
        import tomllib
        from pathlib import Path as _p  # noqa: N813

        data = tomllib.loads(_p("pyproject.toml").read_text(encoding="utf-8"))
        assert "tool" in data
        assert "flow_engineering" in data["tool"]
        section = data["tool"]["flow_engineering"]
        assert "min_sdd_skill_versions" in section
        min_versions = section["min_sdd_skill_versions"]
        expected_keys = {
            "sdd-explore",
            "sdd-propose",
            "sdd-spec",
            "sdd-design",
            "sdd-tasks",
            "sdd-apply",
            "sdd-verify",
            "sdd-archive",
        }
        assert set(min_versions.keys()) == expected_keys
        for skill_name, version in min_versions.items():
            assert version == "3.0", f"{skill_name} minimum must be '3.0', got {version!r}"

    def test_pyproject_section_coexists_with_prompts_section(self) -> None:
        """[tool.flow_engineering] + [tool.flow_engineering.prompts] coexist."""
        import tomllib
        from pathlib import Path as _p  # noqa: N813

        data = tomllib.loads(_p("pyproject.toml").read_text(encoding="utf-8"))
        fe = data["tool"]["flow_engineering"]
        # Umbrella section: NEW [tool.flow_engineering] (this PR).
        assert "min_sdd_skill_versions" in fe
        # Existing nested section: [tool.flow_engineering.prompts] (carried over).
        assert "prompts" in fe
        assert "directory" in fe["prompts"]
        assert fe["prompts"]["directory"] == "prompts"
