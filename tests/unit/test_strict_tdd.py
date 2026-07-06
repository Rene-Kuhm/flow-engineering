"""Unit tests for strict_tdd.py."""

from __future__ import annotations

import json
from pathlib import Path

from flow_engineering.strict_tdd import (
    build_strict_tdd_instruction,
    find_test_command,
    load_sdd_init,
    log_strict_tdd_optout,
    should_enforce_strict_tdd,
)


class TestLoadSddInit:
    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        result = load_sdd_init(tmp_path)
        assert result is None

    def test_returns_strict_tdd_true(self, tmp_path: Path) -> None:
        sdd_init = tmp_path / "sdd-init"
        sdd_init.mkdir()
        (sdd_init / "myproj.md").write_text(
            "# sdd-init/myproj\n\n**Strict TDD:** ON\n\nother content"
        )
        result = load_sdd_init(tmp_path)
        assert result == {"strict_tdd": True}

    def test_returns_strict_tdd_false(self, tmp_path: Path) -> None:
        sdd_init = tmp_path / "sdd-init"
        sdd_init.mkdir()
        (sdd_init / "myproj.md").write_text("# sdd-init/myproj\n\n**Strict TDD:** OFF\n")
        result = load_sdd_init(tmp_path)
        assert result == {"strict_tdd": False}

    def test_yaml_style_strict_tdd_true_marker(self, tmp_path: Path) -> None:
        """REQ-V1.3.1: ``strict_tdd: true`` YAML-style marker is accepted."""
        sdd_init = tmp_path / "sdd-init"
        sdd_init.mkdir()
        (sdd_init / "flow-engineering.md").write_text(
            "---\nproject: flow-engineering\nstrict_tdd: true\n---\n\n"
            "# flow-engineering sdd-init marker\n"
        )
        result = load_sdd_init(tmp_path)
        assert result is not None
        assert result["strict_tdd"] is True

    def test_real_project_marker_restored_returns_strict_tdd_true(self) -> None:
        """REQ-V1.3.1: calling ``load_sdd_init('.')`` on the project root
        must return a non-None mapping with ``strict_tdd: True`` after
        sub-change (a) restores ``sdd-init/flow-engineering.md``.
        """
        project_root = Path(__file__).resolve().parents[2]
        result = load_sdd_init(project_root)
        assert result is not None
        assert result["strict_tdd"] is True


class TestShouldEnforceStrictTdd:
    def test_true_when_sdd_init_says_so(self, tmp_path: Path) -> None:
        sdd_init = tmp_path / "sdd-init"
        sdd_init.mkdir()
        (sdd_init / "myproj.md").write_text("**Strict TDD:** ON")
        assert should_enforce_strict_tdd(tmp_path) is True

    def test_false_when_no_sdd_init(self, tmp_path: Path) -> None:
        assert should_enforce_strict_tdd(tmp_path) is False


class TestFindTestCommand:
    def test_finds_npm_test(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test": "vitest run"}}))
        assert find_test_command(tmp_path) == "vitest run"

    def test_finds_cargo(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").touch()
        assert find_test_command(tmp_path) == "cargo test"

    def test_finds_go(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").touch()
        assert find_test_command(tmp_path) == "go test ./..."

    def test_returns_none_when_unknown(self, tmp_path: Path) -> None:
        assert find_test_command(tmp_path) is None

    def test_prefers_package_json_over_other(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test": "playwright test"}}))
        (tmp_path / "Cargo.toml").touch()
        assert find_test_command(tmp_path) == "playwright test"


class TestBuildStrictTddInstruction:
    def test_includes_test_command(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test": "vitest run"}}))
        instruction = build_strict_tdd_instruction(tmp_path)
        assert "vitest run" in instruction
        assert "STRICT TDD MODE IS ACTIVE" in instruction
        assert "strict-tdd.md" in instruction

    def test_with_explicit_test_command(self, tmp_path: Path) -> None:
        instruction = build_strict_tdd_instruction(tmp_path, test_command="npm test")
        assert "npm test" in instruction

    def test_fallback_when_no_test_runner(self, tmp_path: Path) -> None:
        instruction = build_strict_tdd_instruction(tmp_path)
        assert "(unknown" in instruction


class TestLogStrictTddOptout:
    def test_appends_optout_entry(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"status": "APPLYING", "transitions": []}))
        log_strict_tdd_optout(state_file, "tight deadline")
        data = json.loads(state_file.read_text())
        assert len(data["strict_tdd_optouts"]) == 1
        assert data["strict_tdd_optouts"][0]["reason"] == "tight deadline"
        assert "at" in data["strict_tdd_optouts"][0]

    def test_appends_to_existing_optouts(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "status": "APPLYING",
                    "strict_tdd_optouts": [
                        {"at": "2026-06-25T00:00:00+00:00", "reason": "first"},
                    ],
                }
            )
        )
        log_strict_tdd_optout(state_file, "second")
        data = json.loads(state_file.read_text())
        assert len(data["strict_tdd_optouts"]) == 2

    def test_no_op_when_state_missing(self, tmp_path: Path) -> None:
        state_file = tmp_path / "state.json"  # does not exist
        log_strict_tdd_optout(state_file, "reason")  # should not raise
