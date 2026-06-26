"""Unit tests for graphify_hook.py."""

from __future__ import annotations

from pathlib import Path

from flow_engineering.graphify_hook import (
    decide_rebuild,
    detect_structural_change,
)


class TestDetectStructural:
    def test_no_diff_is_not_structural(self) -> None:
        assert detect_structural_change("") is False

    def test_only_additions_not_structural(self) -> None:
        diff = "+ added line\n+ another line"
        assert detect_structural_change(diff) is False

    def test_only_modifications_not_structural(self) -> None:
        diff = "- old\n+ new"
        # Note: `- old` is a deletion, but in git diff format that's also D
        # Our pattern matches "D " at start of line in unified diff format
        # Actually git diff uses '-old' and '+new' (no space). Let me check.
        assert detect_structural_change(diff) is False

    def test_deletion_is_structural(self) -> None:
        diff = "D\tdeleted-file.py"
        assert detect_structural_change(diff) is True

    def test_rename_is_structural(self) -> None:
        diff = "rename from old.py\nrename to new.py"
        assert detect_structural_change(diff) is True

    def test_package_json_change_is_structural(self) -> None:
        diff = "--- a/package.json\n+++ b/package.json"
        assert detect_structural_change(diff) is True

    def test_pyproject_change_is_structural(self) -> None:
        diff = "--- a/pyproject.toml\n+++ b/pyproject.toml"
        assert detect_structural_change(diff) is True


class TestDecideRebuild:
    def test_empty_diff_incremental(self, tmp_path: Path) -> None:
        decision = decide_rebuild(tmp_path, diff_text="")
        assert decision.mode == "incremental"
        assert decision.estimated_cost_usd < 0.10

    def test_structural_diff_full(self, tmp_path: Path) -> None:
        decision = decide_rebuild(tmp_path, diff_text="D\tfoo.py")
        assert decision.mode == "full"
        assert decision.estimated_cost_usd > 0.30

    def test_command_format(self, tmp_path: Path) -> None:
        decision = decide_rebuild(tmp_path, diff_text="")
        assert decision.command[0] == "graphify"
        assert decision.command[1] == "update"
        assert str(tmp_path) in decision.command[2]


class TestRunGraphifyHook:
    def test_dry_run_no_execution(self, tmp_path: Path) -> None:
        from flow_engineering.graphify_hook import run_graphify_hook

        exit_code, stderr, decision = run_graphify_hook(tmp_path, dry_run=True)
        assert exit_code == 0
        assert decision.mode == "incremental"

    def test_missing_binary_returns_127(self, tmp_path: Path) -> None:
        from flow_engineering.graphify_hook import run_graphify_hook

        exit_code, stderr, _ = run_graphify_hook(tmp_path, graphify_bin="nonexistent-binary-xyz")
        assert exit_code == 127
        assert "not found" in stderr.lower() or "graphify" in stderr.lower()


class TestArchiveGraphifyHook:
    def test_archive_hook_finds_project_root(self, tmp_path: Path) -> None:
        # Build a fake project: tmp/project/flow-engineering/my-change/state.json
        import json

        from flow_engineering.graphify_hook import archive_graphify_hook

        project = tmp_path / "project"
        fe = project / "flow-engineering" / "my-change"
        fe.mkdir(parents=True)
        (fe / "state.json").write_text(json.dumps({"cross_projects": []}))
        exit_code, stderr, decision = archive_graphify_hook(fe, dry_run=True)
        # Target should be tmp_path/project (parent of flow-engineering)
        assert decision.mode == "incremental"
        assert "project" in decision.command[2]
