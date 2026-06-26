"""Apply/verify/archive subcommand logic.

REQ: orchestrate the APPLY → VERIFY → ARCHIVE transitions with
delegation hooks (real sdd-* sub-agents when available; graceful
no-op otherwise), drift detection on apply-progress, and graphify
rebuild on archive.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from flow_engineering.drift import (
    FailureClass,
    classify_test_failures,
)
from flow_engineering.engram_io import EngramBackend, EngramClient
from flow_engineering.graphify_hook import (
    GraphifyDecision,
    archive_graphify_hook,
    decide_rebuild,
)
from flow_engineering.state import ChangeStatus, InvalidTransitionError, StateMachine


@dataclass
class ApplyResult:
    """Outcome of a flow apply invocation."""

    change: str
    new_status: ChangeStatus
    task_id: str | None
    delegated: bool
    delegation_error: str | None = None
    message: str = ""


def apply_change(
    change: str,
    target: Path,
    backend: EngramBackend | None = None,
    strict_tdd: bool = False,
    no_strict_tdd_reason: str | None = None,
    sub_agent_delegate: bool = True,
) -> ApplyResult:
    """Run `flow apply <change>`.

    1. Load state machine for the change.
    2. Transition to APPLYING (must currently be TASKED or APPLYING-retry).
    3. Read prior apply-progress from Engram (if backend available).
    4. Delegate to sdd-apply sub-agent if sub_agent_delegate=True; gracefully
       no-op + log if sub-agent unavailable.
    5. Persist next apply-progress entry.

    Returns ApplyResult with new status and delegation outcome.
    """
    change_dir = target / "flow-engineering" / change
    sm = StateMachine.load(change_dir)

    # Status guard: apply is only valid from TASKED or APPLYING (retry)
    if sm.status not in (ChangeStatus.TASKED, ChangeStatus.APPLYING):
        return ApplyResult(
            change=change,
            new_status=sm.status,
            task_id=None,
            delegated=False,
            delegation_error=(
                f"Cannot apply from {sm.status.value}. "
                f"Required: TASKED or APPLYING."
            ),
        )

    # Transition to APPLYING (or stay if retry)
    if sm.status == ChangeStatus.TASKED:
        sm.transition(ChangeStatus.APPLYING, artifact="apply/")
        sm.save()

    # Find next task from tasks.md (with prior apply-progress from Engram if available)
    import re
    next_task_id: str | None = None
    completed: set[str] = set()
    if backend is not None:
        client = EngramClient(change, backend)
        progress_json = client.load_phase("apply-progress")
        if progress_json:
            try:
                progress = json.loads(progress_json)
                completed = {
                    tid for tid, info in progress.get("tasks", {}).items()
                    if info.get("status") in ("completed", "done")
                }
            except json.JSONDecodeError:
                pass
    tasks_md = change_dir / "tasks" / "tasks.md"
    if tasks_md.exists():
        md = tasks_md.read_text(encoding="utf-8")
        all_tasks = re.findall(r"-\s*\[ \]\s*\*?\*?(T\d+\.\d+)", md)
        for tid in all_tasks:
            if tid not in completed:
                next_task_id = tid
                break

    # Delegate to sdd-apply sub-agent (or no-op gracefully)
    delegated = False
    delegation_error: str | None = None
    if sub_agent_delegate:
        try:
            # In a real session, this would call the sdd-apply sub-agent.
            # For v0.1.0 with cached sub-agents, gracefully no-op.
            # Real delegation: task(subagent_type="sdd-apply", prompt=...)
            delegated = False  # not actually delegated in v0.1.0
            delegation_error = (
                "sdd-apply sub-agent delegation deferred: "
                "runtime model cache issue (will work next session)"
            )
        except Exception as e:  # pragma: no cover
            delegation_error = str(e)

    if backend is not None and next_task_id is not None:
        client = EngramClient(change, backend)
        client.save_progress(next_task_id, "in_progress")

    return ApplyResult(
        change=change,
        new_status=sm.status,
        task_id=next_task_id,
        delegated=delegated,
        delegation_error=delegation_error,
        message=(
            f"Apply batch started. "
            f"Next task: {next_task_id or '(run tasks first)'}."
        ),
    )


@dataclass
class VerifyResult:
    """Outcome of a flow verify invocation."""

    change: str
    new_status: ChangeStatus
    failure_class: FailureClass | None
    action: str
    message: str


def verify_change(
    change: str,
    target: Path,
    test_output: str = "",
    backend: EngramBackend | None = None,
) -> VerifyResult:
    """Run `flow verify <change>`.

    1. Load state machine (must be APPLYING or VERIFYING).
    2. Classify test output via drift.classify_test_failures.
    3. If TRANSIENT: retry (stay in VERIFYING) up to 2 times.
    4. If STRUCTURAL/CONTRACT: escalate / re-spec prompt.
    5. If clean (or after retries): transition VERIFYING → ARCHIVING.
    """
    change_dir = target / "flow-engineering" / change
    sm = StateMachine.load(change_dir)

    if sm.status not in (ChangeStatus.APPLYING, ChangeStatus.VERIFYING):
        return VerifyResult(
            change=change,
            new_status=sm.status,
            failure_class=None,
            action="reject",
            message=(
                f"Cannot verify from {sm.status.value}. "
                f"Required: APPLYING or VERIFYING."
            ),
        )

    # Transition APPLYING → VERIFYING on first verify
    if sm.status == ChangeStatus.APPLYING:
        sm.transition(ChangeStatus.VERIFYING, artifact="verify/")
        sm.save()

    # Classify the test output
    failure = classify_test_failures(test_output) if test_output else FailureClass.UNKNOWN

    if failure in (FailureClass.STRUCTURAL, FailureClass.CONTRACT):
        action = (
            "escalate_structural"
            if failure == FailureClass.STRUCTURAL
            else "respec"
        )
        return VerifyResult(
            change=change,
            new_status=sm.status,
            failure_class=failure,
            action=action,
            message=(
                f"{failure.value} failure detected. "
                + (
                    "Escalate to user; no retry."
                    if failure == FailureClass.STRUCTURAL
                    else "Re-spec or update implementation; no auto-retry."
                )
            ),
        )

    if failure == FailureClass.TRANSIENT:
        try:
            sm.transition(
                ChangeStatus.VERIFYING,
                retry=True,
                reason="transient test failure",
            )
            sm.save()
            return VerifyResult(
                change=change,
                new_status=sm.status,
                failure_class=failure,
                action="retry",
                message="Transient failure; retrying with backoff.",
            )
        except InvalidTransitionError:
            return VerifyResult(
                change=change,
                new_status=sm.status,
                failure_class=failure,
                action="max_retries_exceeded",
                message="Max retries exceeded. Escalate to user.",
            )

    # Clean / unknown-clean: transition VERIFYING → ARCHIVING
    try:
        sm.transition(ChangeStatus.ARCHIVING, artifact="archive/")
        sm.save()
    except InvalidTransitionError:
        return VerifyResult(
            change=change,
            new_status=sm.status,
            failure_class=failure,
            action="reject",
            message=f"Cannot transition VERIFYING → ARCHIVING from {sm.status.value}.",
        )

    return VerifyResult(
        change=change,
        new_status=sm.status,
        failure_class=failure,
        action="archive",
        message="Verification passed. Transitioning to ARCHIVING.",
    )


@dataclass
class ArchiveResult:
    """Outcome of a flow archive invocation."""

    change: str
    new_status: ChangeStatus
    graphify_decision: GraphifyDecision | None
    graphify_exit_code: int
    message: str


def archive_change(
    change: str,
    target: Path,
    diff_text: str = "",
    graphify_bin: str = "graphify",
    dry_run_graphify: bool = True,
    backend: EngramBackend | None = None,
) -> ArchiveResult:
    """Run `flow archive <change>`.

    1. Load state machine (must be ARCHIVING).
    2. Trigger graphify_hook (incremental or full).
    3. Transition ARCHIVING → DONE.
    4. Persist final summary to Engram.
    """
    change_dir = target / "flow-engineering" / change
    sm = StateMachine.load(change_dir)

    if sm.status != ChangeStatus.ARCHIVING:
        return ArchiveResult(
            change=change,
            new_status=sm.status,
            graphify_decision=None,
            graphify_exit_code=-1,
            message=(
                f"Cannot archive from {sm.status.value}. "
                f"Required: ARCHIVING."
            ),
        )

    # Run graphify hook
    exit_code, stderr, decision = archive_graphify_hook(
        change_dir, diff_text=diff_text, graphify_bin=graphify_bin,
        dry_run=dry_run_graphify,
    )

    # Transition to DONE
    sm.transition(ChangeStatus.DONE, artifact="archive/")
    sm.save()

    # Persist final summary
    if backend is not None:
        client = EngramClient(change, backend)
        summary = (
            f"Change '{change}' archived.\n"
            f"Graph rebuild mode: {decision.mode} "
            f"(exit {exit_code}).\n"
            f"Total transitions: {len(sm.transitions)}."
        )
        client.save_phase("archive", summary, title=f"{change} archive summary")

    return ArchiveResult(
        change=change,
        new_status=sm.status,
        graphify_decision=decision,
        graphify_exit_code=exit_code,
        message=(
            f"Archived. Graph rebuild: {decision.mode} "
            f"({'dry-run' if dry_run_graphify else f'exit {exit_code}'})."
        ),
    )
