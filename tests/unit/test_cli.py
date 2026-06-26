"""Unit tests for cli.py — click subcommands."""

from __future__ import annotations

from pathlib import Path

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
