"""Unit tests for cli.py — click subcommands."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main

runner = CliRunner()


class TestNewCommand:
    def test_new_creates_change(self, tmp_path: Path) -> None:
        result = runner.invoke(main, ["new", "my-change", "--in", str(tmp_path)])
        assert result.exit_code == 0
        assert "my-change" in result.output
        assert (tmp_path / "flow-engineering" / "my-change" / "state.json").exists()

    def test_new_with_cross_projects(self, tmp_path: Path) -> None:
        result = runner.invoke(
            main,
            [
                "new",
                "my-change",
                "--in",
                str(tmp_path),
                "--cross-projects",
                "proj-a",
                "--cross-projects",
                "proj-b",
            ],
        )
        assert result.exit_code == 0
        change_dir = tmp_path / "flow-engineering" / "my-change"
        import yaml

        manifest = yaml.safe_load((change_dir / "change.yaml").read_text())
        assert manifest["cross_projects"] == ["proj-a", "proj-b"]
        assert "Cross-projects" in result.output


class TestStatusCommand:
    def test_status_no_changes_dir(self, tmp_path: Path) -> None:
        result = runner.invoke(main, ["status", "--in", str(tmp_path)])
        assert result.exit_code == 1
        assert "No flow-engineering" in result.output

    def test_status_no_changes(self, tmp_path: Path) -> None:
        (tmp_path / "flow-engineering").mkdir()
        result = runner.invoke(main, ["status", "--in", str(tmp_path)])
        assert result.exit_code == 0
        assert "No changes" in result.output

    def test_status_lists_changes(self, tmp_path: Path) -> None:
        runner.invoke(main, ["new", "alpha", "--in", str(tmp_path)])
        runner.invoke(main, ["new", "beta", "--in", str(tmp_path)])
        result = runner.invoke(main, ["status", "--in", str(tmp_path)])
        assert result.exit_code == 0
        assert "alpha: NEW" in result.output
        assert "beta: NEW" in result.output


class TestNewProjectCommand:
    def test_new_project(self, tmp_path: Path) -> None:
        result = runner.invoke(main, ["new-project", "my-app", "--in", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "my-app" / "README.md").exists()
        assert (tmp_path / "my-app" / ".flow-version").exists()


class TestDoctorCommand:
    def test_doctor_runs(self) -> None:
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Python OK" in result.output
        assert "0.1.0" in result.output


class TestVersionFlag:
    def test_version(self) -> None:
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


# ---------- REQ-6: `flow save` subcommand ----------


@pytest.fixture
def metrics_path(tmp_path, monkeypatch):
    """Point observability at a tmp_path JSONL file."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


class TestSaveCommand:
    def test_save_writes_unbound_by_default(self, metrics_path, monkeypatch):
        """Without --with-suggest, save writes the default unbound block."""
        monkeypatch.delenv("FLOW_AUTO_SUGGEST", raising=False)
        result = runner.invoke(
            main,
            [
                "save",
                "my-change",
                "propose",
                "--content",
                "## Decision\n\nUse JWT.\n",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Saved propose" in result.output

    def test_save_with_no_suggest_writes_manual_source(self, metrics_path, monkeypatch):
        monkeypatch.delenv("FLOW_AUTO_SUGGEST", raising=False)
        result = runner.invoke(
            main,
            [
                "save",
                "my-change",
                "propose",
                "--content",
                "## Decision\n\nUse JWT.\n",
                "--no-suggest",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "no_suggest=True" in result.output

    def test_save_with_with_suggest_flag_invokes_auto_suggest(self, metrics_path, monkeypatch):
        from flow_engineering.binding import CodeRef

        candidates = [
            CodeRef(
                project="insyd",
                id="src_auth_jwt_tokenmgr",
                label="TokenManager",
                file="src/auth/jwt.py",
                line=42,
                confidence=0.7,
                source="auto_suggest",
            )
        ]
        monkeypatch.setattr(
            "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
            lambda text, *, threshold=0.3, max_results=5: candidates,
        )

        result = runner.invoke(
            main,
            [
                "save",
                "my-change",
                "propose",
                "--content",
                "## Decision\n\nUse JWT.\n",
                "--with-suggest",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "with_suggest=True" in result.output

        # Metric was recorded.
        from flow_engineering import observability

        events = observability.read_all()
        names = [e["name"] for e in events]
        assert "suggest_invoked_total" in names

    def test_save_with_flow_auto_suggest_env_activates_auto_suggest(
        self, metrics_path, monkeypatch
    ):
        from flow_engineering.binding import CodeRef

        candidates = [
            CodeRef(
                project="insyd",
                id="src_auth_jwt_tokenmgr",
                label="TokenManager",
                file="src/auth/jwt.py",
                line=42,
                confidence=0.7,
                source="auto_suggest",
            )
        ]
        monkeypatch.setattr(
            "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
            lambda text, *, threshold=0.3, max_results=5: candidates,
        )
        monkeypatch.setenv("FLOW_AUTO_SUGGEST", "1")
        result = runner.invoke(
            main,
            [
                "save",
                "my-change",
                "propose",
                "--content",
                "## Decision\n\nUse JWT.\n",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "with_suggest=True" in result.output

    def test_save_with_content_file(self, metrics_path, monkeypatch, tmp_path):
        monkeypatch.delenv("FLOW_AUTO_SUGGEST", raising=False)
        content_file = tmp_path / "obs.txt"
        content_file.write_text("## Decision\n\nUse JWT.\n", encoding="utf-8")
        result = runner.invoke(
            main,
            [
                "save",
                "my-change",
                "propose",
                "--content-file",
                str(content_file),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Saved propose" in result.output

    def test_save_rejects_both_flags(self, metrics_path, monkeypatch):
        monkeypatch.delenv("FLOW_AUTO_SUGGEST", raising=False)
        result = runner.invoke(
            main,
            [
                "save",
                "my-change",
                "propose",
                "--content",
                "x",
                "--with-suggest",
                "--no-suggest",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "UsageError" in result.output

    def test_save_rejects_both_content_sources(self, metrics_path, monkeypatch, tmp_path):
        content_file = tmp_path / "obs.txt"
        content_file.write_text("x", encoding="utf-8")
        result = runner.invoke(
            main,
            [
                "save",
                "my-change",
                "propose",
                "--content",
                "x",
                "--content-file",
                str(content_file),
            ],
        )
        assert result.exit_code != 0
