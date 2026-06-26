"""Unit tests for project_detector (REQ-24 T1.3, cross-project-federation).

TDD: written BEFORE the implementation. These MUST fail until
``project_detector.detect`` + ``apply_tag`` land.

Coverage map:
- REQ-24 scenario 1 (unit): ``detect`` returns project name when cwd under
  ``~/dev/proyects/<name>/`` or ``~/proyects/<name>/``
- REQ-24 scenario 2 (unit): ``detect`` returns ``None`` when cwd is not under
  a projects dir (no silent ``"insyd"`` fallback)
- Registry auto-load: ``~/.config/flow-engineering/registry.json`` map takes
  precedence over the default cwd-based detection
- ``apply_tag`` rejects empty/whitespace project; returns ``False`` on
  not-found; mutates the live observation's ``project`` field otherwise
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from flow_engineering.engram_io import InMemoryBackend
from flow_engineering.project_detector import (
    RegistryParseError,
    apply_tag,
    detect,
    load_registry,
)


def _make_obs(
    obs_id: int,
    *,
    title: str = "t",
    content: str = "c",
    project: str = "insyd",
    type: str = "manual",
    created_at: str | int = "2026-06-15 10:00:00",
) -> dict[str, Any]:
    """Build a memory-observation dict shaped like ``InMemoryBackend.mem_save`` output."""
    return {
        "id": obs_id,
        "title": title,
        "content": content,
        "topic_key": "sdd/test/phase",
        "type": type,
        "scope": "project",
        "project": project,
        "created_at": created_at,
        "updated_at": created_at,
    }


class TestDetectCwdMatchesProjectsDir:
    """REQ-24 scenario 1 (unit): cwd under ``~/dev/proyects/<name>/`` resolves to ``<name>``."""

    def test_cwd_is_project_root_returns_name(self) -> None:
        cwd = Path("/c/dev/proyects/flow-engineering")
        assert detect(cwd) == "flow-engineering"

    def test_cwd_subdirectory_resolves_to_parent(self) -> None:
        cwd = Path("/c/dev/proyects/flow-engineering/src")
        assert detect(cwd) == "flow-engineering"

    def test_cwd_nested_subdirectory_resolves_to_project(self) -> None:
        cwd = Path("/c/dev/proyects/mockup-2-blog/packages/site/pages/index.tsx")
        assert detect(cwd) == "mockup-2-blog"


class TestDetectCwdNotUnderProjectsDir:
    """REQ-24 scenario 2 (unit): cwd NOT under a projects dir returns ``None``."""

    def test_cwd_downloads_returns_none(self) -> None:
        assert detect(Path("/c/Users/insyd/Downloads")) is None

    def test_cwd_tmp_returns_none(self) -> None:
        assert detect(Path("/tmp")) is None

    def test_cwd_at_projects_dir_root_returns_none(self) -> None:
        """The projects root itself is NOT a project — only a child is."""
        assert detect(Path("/c/dev/proyects")) is None


class TestDetectProyectsWithoutDevPrefix:
    """The second valid layout is ``~/proyects/<name>/`` (no ``dev`` segment)."""

    def test_home_proyects_layout(self) -> None:
        cwd = Path("/c/Users/insyd/proyects/flow-engineering")
        assert detect(cwd) == "flow-engineering"

    def test_home_proyects_subdirectory(self) -> None:
        cwd = Path("/c/Users/insyd/proyects/mockup-2-blog")
        assert detect(cwd) == "mockup-2-blog"


class TestDetectRegistryOverride:
    """An explicit ``registry`` mapping takes precedence over default detection."""

    def test_registry_exact_match_wins(self) -> None:
        registry = {"c:/some/random/path": "renamed-project"}
        assert detect(Path("c:/some/random/path"), registry=registry) == "renamed-project"

    def test_registry_subdir_match_wins(self) -> None:
        registry = {"c:/Users/insyd/scratch/foo": "scratch-foo"}
        assert (
            detect(Path("c:/Users/insyd/scratch/foo/sub"), registry=registry)
            == "scratch-foo"
        )

    def test_empty_registry_falls_back_to_default(self) -> None:
        """Empty registry means no override — fall through to default parts-based detection."""
        assert detect(Path("/c/dev/proyects/flow-engineering"), registry={}) == "flow-engineering"


class TestLoadRegistry:
    """``load_registry`` reads ``~/.config/flow-engineering/registry.json``."""

    def test_missing_file_returns_empty_dict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "flow_engineering.project_detector.DEFAULT_REGISTRY_PATH",
            tmp_path / "does-not-exist.json",
        )
        assert load_registry() == {}

    def test_valid_json_loads_cwd_to_project_map(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "registry.json"
        path.write_text(
            json.dumps(
                {
                    "cwd_to_project": {
                        "c:/dev/proyects/manual-tag-1": "manual-tag-1",
                    }
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "flow_engineering.project_detector.DEFAULT_REGISTRY_PATH", path
        )
        result = load_registry()
        assert result == {"c:/dev/proyects/manual-tag-1": "manual-tag-1"}

    def test_malformed_json_raises_with_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{not valid json,", encoding="utf-8")
        monkeypatch.setattr(
            "flow_engineering.project_detector.DEFAULT_REGISTRY_PATH", path
        )
        with pytest.raises(RegistryParseError) as exc:
            load_registry()
        assert str(path) in str(exc.value)

    def test_wrong_shape_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "wrong-shape.json"
        path.write_text(json.dumps({"oops": "no cwd_to_project key"}), encoding="utf-8")
        monkeypatch.setattr(
            "flow_engineering.project_detector.DEFAULT_REGISTRY_PATH", path
        )
        with pytest.raises(RegistryParseError):
            load_registry()


class TestApplyTag:
    """``apply_tag`` mutates a single observation's ``project`` field."""

    def test_apply_tag_success_returns_true(self) -> None:
        backend = InMemoryBackend()
        obs = _make_obs(1, project="insyd")
        backend.observations[1] = obs
        backend.next_id = 2

        assert apply_tag(1, "mockup-2-blog", backend=backend) is True
        assert backend.observations[1]["project"] == "mockup-2-blog"

    def test_apply_tag_observation_not_found_returns_false(self) -> None:
        backend = InMemoryBackend()
        assert apply_tag(999, "mockup-2-blog", backend=backend) is False

    def test_apply_tag_empty_project_raises(self) -> None:
        backend = InMemoryBackend()
        backend.observations[1] = _make_obs(1)
        backend.next_id = 2
        with pytest.raises(ValueError):
            apply_tag(1, "", backend=backend)

    def test_apply_tag_whitespace_project_raises(self) -> None:
        backend = InMemoryBackend()
        backend.observations[1] = _make_obs(1)
        backend.next_id = 2
        with pytest.raises(ValueError):
            apply_tag(1, "   ", backend=backend)

    def test_apply_tag_preserves_other_fields(self) -> None:
        backend = InMemoryBackend()
        backend.observations[1] = _make_obs(
            1,
            title="keep-me",
            content="keep-this-content",
            type="decision",
        )
        backend.next_id = 2
        apply_tag(1, "mockup-2-blog", backend=backend)
        obs = backend.observations[1]
        assert obs["title"] == "keep-me"
        assert obs["content"] == "keep-this-content"
        assert obs["type"] == "decision"
        assert obs["project"] == "mockup-2-blog"
