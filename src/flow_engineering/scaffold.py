"""Scaffolding for new changes and projects.

REQ-2: Jinja2 templates for new changes and new projects.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from flow_engineering.engram_io import EngramBackend, EngramClient
from flow_engineering.state import StateMachine

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(),
        keep_trailing_newline=True,
    )


def render_new_change(
    change: str,
    target_dir: Path,
    cross_projects: list[str] | None = None,
) -> Path:
    """Render a new change scaffold at target_dir/flow-engineering/<change>/.

    Returns the change directory path.
    """
    cross_projects = cross_projects or []
    target_dir.mkdir(parents=True, exist_ok=True)
    change_dir = target_dir / "flow-engineering" / change
    change_dir.mkdir(parents=True, exist_ok=True)

    env = _env()

    # change.yaml
    (change_dir / "change.yaml").write_text(
        env.get_template("new-change/change.yaml.j2").render(
            change=change,
            created_at=datetime.now(UTC).isoformat(),
            cross_projects=cross_projects,
        ),
        encoding="utf-8",
    )

    # exploration.md (placeholder)
    explore_dir = change_dir / "explore"
    explore_dir.mkdir(exist_ok=True)
    (explore_dir / "exploration.md").write_text(
        env.get_template("new-change/explore/exploration.md.j2").render(change=change),
        encoding="utf-8",
    )

    # Empty directories for later phases
    for phase in ("propose", "design", "spec", "tasks", "apply", "verify", "archive"):
        (change_dir / phase).mkdir(exist_ok=True)
        (change_dir / phase / ".gitkeep").touch()

    return change_dir


def render_new_project(project_name: str, target_dir: Path, version: str = "0.1.0") -> Path:
    """Render a new project bootstrap at target_dir/<project_name>/.

    Returns the project root path.
    """
    project_dir = target_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    env = _env()
    (project_dir / "README.md").write_text(
        env.get_template("new-project/README.md.j2").render(project_name=project_name),
        encoding="utf-8",
    )
    (project_dir / ".flow-version").write_text(
        env.get_template("new-project/flow-version.j2").render(project_version=version),
        encoding="utf-8",
    )
    return project_dir


def load_change_yaml(change_dir: Path) -> dict[str, object]:
    """Load the change.yaml manifest."""
    yaml_path = change_dir / "change.yaml"
    if not yaml_path.exists():
        return {}
    result = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        return {}
    return result


def scaffold_change(
    change: str,
    target_dir: Path,
    backend: EngramBackend | None = None,
    cross_projects: list[str] | None = None,
) -> tuple[Path, StateMachine]:
    """Scaffold a change, initialize state machine, optionally save to Engram.

    Returns (change_dir, state_machine).
    """
    cross_projects = cross_projects or []
    change_dir = render_new_change(change, target_dir, cross_projects)
    sm = StateMachine.create(change, change_dir, cross_projects=cross_projects)
    if backend is not None:
        client = EngramClient(change, backend)
        client.save_phase(
            "created",
            f"Change '{change}' scaffolded at {change_dir}",
            title=f"{change}/created",
        )
    return change_dir, sm
