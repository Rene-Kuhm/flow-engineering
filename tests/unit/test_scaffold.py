"""Unit tests for scaffold.py."""

from __future__ import annotations

from pathlib import Path

import yaml

from flow_engineering.engram_io import InMemoryBackend
from flow_engineering.scaffold import (
    load_change_yaml,
    render_new_change,
    render_new_project,
    scaffold_change,
)


class TestRenderNewChange:
    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        change_dir = render_new_change("my-change", tmp_path)
        assert (change_dir / "change.yaml").exists()
        assert (change_dir / "explore" / "exploration.md").exists()
        for phase in ("propose", "design", "spec", "tasks", "apply", "verify", "archive"):
            assert (change_dir / phase).exists(), f"missing {phase}/"
            assert (change_dir / phase / ".gitkeep").exists(), f"missing {phase}/.gitkeep"

    def test_change_yaml_contents(self, tmp_path: Path) -> None:
        change_dir = render_new_change("my-change", tmp_path, cross_projects=["proj-a"])
        manifest = yaml.safe_load((change_dir / "change.yaml").read_text())
        assert manifest["change"] == "my-change"
        assert manifest["cross_projects"] == ["proj-a"]
        assert "created_at" in manifest

    def test_exploration_md_placeholder(self, tmp_path: Path) -> None:
        change_dir = render_new_change("my-change", tmp_path)
        md = (change_dir / "explore" / "exploration.md").read_text()
        assert "my-change" in md
        assert "exploration" in md.lower()

    def test_no_cross_projects_default(self, tmp_path: Path) -> None:
        change_dir = render_new_change("my-change", tmp_path)
        manifest = yaml.safe_load((change_dir / "change.yaml").read_text())
        assert manifest["cross_projects"] == []


class TestRenderNewProject:
    def test_creates_readme_and_version(self, tmp_path: Path) -> None:
        project_dir = render_new_project("my-app", tmp_path, version="0.2.0")
        assert project_dir.name == "my-app"
        assert (project_dir / "README.md").exists()
        assert (project_dir / ".flow-version").exists()
        assert (project_dir / ".flow-version").read_text().strip() == "0.2.0"
        assert "my-app" in (project_dir / "README.md").read_text()


class TestScaffoldChange:
    def test_scaffold_creates_state(self, tmp_path: Path) -> None:
        change_dir, sm = scaffold_change("my-change", tmp_path)
        assert (change_dir / "state.json").exists()
        assert sm.status.name == "NEW"
        assert sm.change == "my-change"

    def test_scaffold_saves_to_engram(self, tmp_path: Path) -> None:
        backend = InMemoryBackend()
        change_dir, sm = scaffold_change(
            "my-change", tmp_path, backend=backend, cross_projects=["proj-a"]
        )
        # Verify Engram has the observation
        results = backend.mem_search(query="scaffolded", topic_key="sdd/my-change/created")
        assert len(results) == 1
        assert "my-change" in results[0]["content"]


class TestLoadChangeYaml:
    def test_loads_existing(self, tmp_path: Path) -> None:
        change_dir = render_new_change("my-change", tmp_path)
        manifest = load_change_yaml(change_dir)
        assert manifest["change"] == "my-change"

    def test_empty_for_missing(self, tmp_path: Path) -> None:
        manifest = load_change_yaml(tmp_path / "nonexistent")
        assert manifest == {}


# ---------- T3.6 (W4): scaffold._env hoisted to shared prompt_registry._env ----------


class TestScaffoldEnvUsesSharedFactory:
    """REQ-46 W4 — ``scaffold._env()`` delegates to ``prompt_registry._env``.

    Per verify-report-pr2b W4: the autoescape + ``keep_trailing_newline``
    kwargs lived in two places (``scaffold._env`` and
    ``prompt_registry._safe_jinja_env``). After the hoist, scaffold
    imports the shared factory so the policy lives in one location.
    Scaffold's call sites now pass ``loader_path=_TEMPLATE_DIR`` inline
    so behavior is unchanged from a caller's view.
    """

    def test_scaffold_env_uses_prompt_registry_env_factory(self) -> None:
        """``flow_engineering.scaffold._env`` is the shared factory."""
        from flow_engineering import scaffold
        from flow_engineering.prompt_registry import _env as shared_env

        assert scaffold._env is shared_env, (
            "expected scaffold._env to BE prompt_registry._env "
            "(REQ-46 W4 hoist); got a different function object"
        )

    def test_scaffold_render_uses_file_system_loader(self, tmp_path: Path) -> None:
        """End-to-end: rendering a new change succeeds, which means the
        env factory was called with ``loader_path=_TEMPLATE_DIR`` —
        Jinja2 must locate the .j2 files on disk."""
        change_dir = render_new_change("hoist-loader", tmp_path)
        # If the loader path were wrong, get_template() would raise
        # TemplateNotFound during render_new_change; the file existing
        # is positive proof the loader works.
        assert (change_dir / "change.yaml").exists()
        assert "hoist-loader" in (change_dir / "change.yaml").read_text()

    def test_shared_factory_enables_autoescape(self) -> None:
        """The shared factory enables autoescape — scaffold inherits it
        for free because it goes through the same factory."""
        from flow_engineering.prompt_registry import _env as shared_env
        from flow_engineering.scaffold import _TEMPLATE_DIR

        env = shared_env(loader_path=_TEMPLATE_DIR)
        assert env.autoescape is not False

    def test_scaffold_render_unchanged_after_hoist(self, tmp_path: Path) -> None:
        """End-to-end behavior is unchanged after the W4 hoist: rendering
        a new change still produces the same files."""
        change_dir = render_new_change("post-hoist", tmp_path)
        assert (change_dir / "change.yaml").exists()
        assert (change_dir / "explore" / "exploration.md").exists()
