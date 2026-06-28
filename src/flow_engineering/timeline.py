"""Cross-session memory timeline.

REQ: visual representation of how a change evolved through phases
across sessions (when resumed after days/weeks).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from flow_engineering.state import StateMachine


@dataclass
class TimelineEvent:
    """A single transition event in a change's lifecycle."""

    change: str
    from_status: str
    to_status: str
    at: datetime
    retry: bool = False
    reason: str | None = None


@dataclass
class ChangeTimeline:
    """Timeline of all transitions for one change."""

    change: str
    status: str
    events: list[TimelineEvent] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    total_tokens: int = 0


@dataclass
class ProjectTimeline:
    """Timeline aggregating all changes in a project."""

    changes: list[ChangeTimeline]

    @property
    def total_events(self) -> int:
        return sum(len(c.events) for c in self.changes)


def build_timeline(change_dirs: list[Path]) -> ProjectTimeline:
    """Build a project timeline from a list of change directories."""
    timelines = []
    for d in sorted(change_dirs):
        try:
            sm = StateMachine.load(d)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        events = []
        for t in sm.transitions:
            events.append(TimelineEvent(
                change=d.name,
                from_status=t.from_status.value,
                to_status=t.to_status.value,
                at=t.at,
                retry=t.retry,
                reason=t.reason,
            ))
        timelines.append(ChangeTimeline(
            change=d.name,
            status=sm.status.value,
            events=events,
            created_at=sm.created_at,
            updated_at=sm.updated_at,
            total_tokens=sm.token_cost,
        ))
    return ProjectTimeline(changes=timelines)


def render_timeline(timeline: ProjectTimeline) -> str:
    """Render the timeline as a text table."""
    lines = ["# Memory Timeline", ""]
    if timeline.total_events == 0:
        lines.append("(no events yet)")
        return "\n".join(lines)
    for c in timeline.changes:
        lines.append(f"## {c.change} [{c.status}]")
        if c.created_at:
            lines.append(f"_Created: {c.created_at.isoformat()}_")
        lines.append(f"_Tokens used: {c.total_tokens}_")
        lines.append("")
        for e in c.events:
            marker = " (retry)" if e.retry else ""
            reason = f" -- {e.reason}" if e.reason else ""
            lines.append(
                f"- {e.at.strftime('%Y-%m-%d %H:%M')} "
                f"{e.from_status} -> {e.to_status}{marker}{reason}"
            )
        lines.append("")
    return "\n".join(lines)
