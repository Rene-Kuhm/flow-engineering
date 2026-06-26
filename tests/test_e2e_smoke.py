"""End-to-end smoke test: full flow from NEW to DONE."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from flow_engineering.cli import main
from flow_engineering.state import ChangeStatus, StateMachine

runner = CliRunner()


def test_full_flow_new_to_done(tmp_path: Path) -> None:
    """Simulate the entire closed loop in tmp_path."""
    project = tmp_path / "my-app"

    # 1. Bootstrap new project
    result = runner.invoke(main, ["new-project", "my-app", "--in", str(tmp_path)])
    assert result.exit_code == 0

    # 2. New change
    result = runner.invoke(main, ["new", "feat-x", "--in", str(project)])
    assert result.exit_code == 0
    change_dir = project / "flow-engineering" / "feat-x"
    assert change_dir.exists()

    sm = StateMachine.load(change_dir)
    assert sm.status == ChangeStatus.NEW

    # 3. Write exploration.md -> watcher transitions NEW -> EXPLORED
    (change_dir / "explore" / "exploration.md").write_text(
        "# Feat X exploration\n\nWe need to add feature X."
    )
    from flow_engineering.watcher import make_exploration_watcher

    make_exploration_watcher(change_dir)(change_dir / "explore" / "exploration.md")
    sm = StateMachine.load(change_dir)
    assert sm.status == ChangeStatus.EXPLORED

    # 4. Walk through every phase manually
    phases = [
        (ChangeStatus.PROPOSED, "propose/proposal.md", "# Proposal\n\nWe propose X."),
        (ChangeStatus.DESIGNED, "design/design.md", "# Design\n\nComponents: A, B."),
        (ChangeStatus.SPECIFIED, "spec/spec.md", "# Spec\n\n## REQ-1\nGIVEN X WHEN Y THEN Z"),
        (ChangeStatus.TASKED, "tasks/tasks.md", "# Tasks\n\n- [ ] **T1.1** do thing"),
        (ChangeStatus.APPLYING, None, None),
        (ChangeStatus.VERIFYING, None, None),
        (ChangeStatus.ARCHIVING, None, None),
        (ChangeStatus.DONE, None, None),
    ]
    for to_status, artifact, content in phases:
        if content:
            rel = artifact.split("/")[0]
            (change_dir / rel / artifact.split("/")[1]).write_text(content)
        sm.transition(to_status, artifact=artifact)
        sm.save()

    # 5. Final state
    sm = StateMachine.load(change_dir)
    assert sm.status == ChangeStatus.DONE
    assert len(sm.transitions) == 9  # NEW->EXPLORED + 8 manual

    # 6. Status CLI shows DONE
    result = runner.invoke(main, ["status", "--in", str(project)])
    assert result.exit_code == 0
    assert "feat-x: DONE" in result.output


def test_skip_transition_blocked_by_cli(tmp_path: Path) -> None:
    """Verify that CLI rejects attempts to skip phases.

    Note: this is verified at the state-machine level (test_state_machine.py).
    The CLI currently delegates to sdd-* sub-agents, which aren't available
    in this smoke test, so we just verify the state-machine guard works.
    """
    project = tmp_path / "my-app"
    runner.invoke(main, ["new-project", "my-app", "--in", str(tmp_path)])
    runner.invoke(main, ["new", "skip-test", "--in", str(project)])
    change_dir = project / "flow-engineering" / "skip-test"

    sm = StateMachine.load(change_dir)
    # Try to skip EXPLORED
    import pytest

    from flow_engineering.state import InvalidTransitionError

    with pytest.raises(InvalidTransitionError):
        sm.transition(ChangeStatus.PROPOSED, artifact="proposal")
    assert sm.status == ChangeStatus.NEW


def test_cross_project_change(tmp_path: Path) -> None:
    """Create a change that spans multiple sub-projects."""
    project = tmp_path / "my-app"
    runner.invoke(main, ["new-project", "my-app", "--in", str(tmp_path)])
    result = runner.invoke(
        main,
        [
            "new",
            "multi",
            "--in",
            str(project),
            "--cross-projects",
            "proj-a",
            "--cross-projects",
            "proj-b",
        ],
    )
    assert result.exit_code == 0
    change_dir = project / "flow-engineering" / "multi"
    sm = StateMachine.load(change_dir)
    assert sm.cross_projects == ["proj-a", "proj-b"]


def test_graphify_hook_decision_for_change(tmp_path: Path) -> None:
    """Verify the graphify hook would rebuild after a change archives."""
    project = tmp_path / "my-app"
    runner.invoke(main, ["new-project", "my-app", "--in", str(tmp_path)])
    runner.invoke(main, ["new", "hook-test", "--in", str(project)])
    change_dir = project / "flow-engineering" / "hook-test"

    from flow_engineering.graphify_hook import archive_graphify_hook

    exit_code, stderr, decision = archive_graphify_hook(change_dir, dry_run=True)
    assert exit_code == 0
    assert decision.mode in ("incremental", "full")

    # Simulate a structural diff
    structural_diff = "D\tfoo.py\n"
    exit_code, stderr, decision = archive_graphify_hook(
        change_dir, diff_text=structural_diff, dry_run=True
    )
    assert decision.mode == "full"
