"""State machine for flow-engineering changes.

REQ-3: Forward transitions, skip rejection, retry loop, persistence.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ChangeStatus(str, Enum):
    """State machine values for a change."""

    NEW = "NEW"
    EXPLORED = "EXPLORED"
    PROPOSED = "PROPOSED"
    DESIGNED = "DESIGNED"
    SPECIFIED = "SPECIFIED"
    TASKED = "TASKED"
    APPLYING = "APPLYING"
    VERIFYING = "VERIFYING"
    ARCHIVING = "ARCHIVING"
    DONE = "DONE"


# Valid forward transitions (status -> set of allowed next statuses)
_FORWARD: dict[ChangeStatus, set[ChangeStatus]] = {
    ChangeStatus.NEW: {ChangeStatus.EXPLORED},
    ChangeStatus.EXPLORED: {ChangeStatus.PROPOSED},
    ChangeStatus.PROPOSED: {ChangeStatus.DESIGNED},
    ChangeStatus.DESIGNED: {ChangeStatus.SPECIFIED},
    ChangeStatus.SPECIFIED: {ChangeStatus.TASKED},
    ChangeStatus.TASKED: {ChangeStatus.APPLYING},
    ChangeStatus.APPLYING: {ChangeStatus.VERIFYING, ChangeStatus.APPLYING},  # retry allowed
    ChangeStatus.VERIFYING: {ChangeStatus.ARCHIVING, ChangeStatus.VERIFYING},  # retry allowed
    ChangeStatus.ARCHIVING: {ChangeStatus.DONE, ChangeStatus.ARCHIVING},  # retry allowed
    ChangeStatus.DONE: set(),
}

# Immediate next status (the one forward, not including retries)
_IMMEDIATE_NEXT: dict[ChangeStatus, ChangeStatus] = {
    ChangeStatus.NEW: ChangeStatus.EXPLORED,
    ChangeStatus.EXPLORED: ChangeStatus.PROPOSED,
    ChangeStatus.PROPOSED: ChangeStatus.DESIGNED,
    ChangeStatus.DESIGNED: ChangeStatus.SPECIFIED,
    ChangeStatus.SPECIFIED: ChangeStatus.TASKED,
    ChangeStatus.TASKED: ChangeStatus.APPLYING,
    ChangeStatus.APPLYING: ChangeStatus.VERIFYING,
    ChangeStatus.VERIFYING: ChangeStatus.ARCHIVING,
    ChangeStatus.ARCHIVING: ChangeStatus.DONE,
    ChangeStatus.DONE: ChangeStatus.DONE,
}

# All statuses reachable forward from this status (for skip detection)
_ALL_FORWARD_FROM: dict[ChangeStatus, set[ChangeStatus]] = {}
for _src, _allowed in _FORWARD.items():
    _reachable = set(_allowed)
    _queue = list(_allowed)
    while _queue:
        _cur = _queue.pop()
        for _nxt in _FORWARD.get(_cur, set()):
            if _nxt not in _reachable and _nxt != _cur:
                _reachable.add(_nxt)
                _queue.append(_nxt)
    _ALL_FORWARD_FROM[_src] = _reachable

MAX_RETRIES_PER_STATUS = 2


class InvalidTransitionError(Exception):
    """Raised when a transition is not allowed from the current status."""


@dataclass
class Transition:
    """A single state transition record."""

    from_status: ChangeStatus
    to_status: ChangeStatus
    at: datetime
    artifact: str | None = None
    retry: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["from_status"] = self.from_status.value
        d["to_status"] = self.to_status.value
        d["at"] = self.at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transition:
        return cls(
            from_status=ChangeStatus(data["from_status"]),
            to_status=ChangeStatus(data["to_status"]),
            at=datetime.fromisoformat(data["at"]),
            artifact=data.get("artifact"),
            retry=data.get("retry", False),
            reason=data.get("reason"),
        )


@dataclass
class StateMachine:
    """State machine for a single change, persisted as state.json."""

    change: str
    path: Path
    status: ChangeStatus = ChangeStatus.NEW
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    transitions: list[Transition] = field(default_factory=list)
    drift_baseline: dict[str, Any] = field(default_factory=dict)
    cross_projects: list[str] = field(default_factory=list)
    token_cost: int = 0
    token_budget: int = 100_000

    @classmethod
    def create(
        cls,
        change: str,
        path: Path,
        cross_projects: list[str] | None = None,
    ) -> StateMachine:
        path.mkdir(parents=True, exist_ok=True)
        sm = cls(
            change=change,
            path=path,
            cross_projects=cross_projects or [],
        )
        sm.save()
        return sm

    @classmethod
    def load(cls, path: Path) -> StateMachine:
        state_file = path / "state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"No state.json at {state_file}")
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return cls(
            change=data["change"],
            path=path,
            status=ChangeStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            transitions=[Transition.from_dict(t) for t in data.get("transitions", [])],
            drift_baseline=data.get("drift_baseline", {}),
            cross_projects=data.get("cross_projects", []),
            token_cost=data.get("token_cost", 0),
            token_budget=data.get("token_budget", 100_000),
        )

    def transition(
        self,
        to_status: ChangeStatus,
        artifact: str | None = None,
        retry: bool = False,
        reason: str | None = None,
    ) -> None:
        """Move to a new status. Validates against the state machine rules.

        Raises InvalidTransitionError if the transition is not allowed.
        """
        allowed = _FORWARD[self.status]
        is_retry = retry and to_status == self.status

        if not is_retry and to_status not in allowed:
            is_skip = (
                to_status != _IMMEDIATE_NEXT[self.status]
                and to_status in _ALL_FORWARD_FROM[self.status]
            )
            if is_skip:
                expected = _IMMEDIATE_NEXT[self.status]
                raise InvalidTransitionError(
                    f"Cannot skip {expected.value}. "
                    f"Run `flow {expected.value.lower()} {self.change}` first."
                )
            raise InvalidTransitionError(
                f"Cannot transition from {self.status.value} to {to_status.value}. "
                f"Allowed next: {sorted(s.value for s in allowed) or ['(terminal)']}."
            )

        if is_retry:
            retry_count = sum(1 for t in self.transitions if t.to_status == self.status and t.retry)
            if retry_count >= MAX_RETRIES_PER_STATUS:
                raise InvalidTransitionError(
                    f"Max retries ({MAX_RETRIES_PER_STATUS}) exceeded for {self.status.value}. "
                    f"Escalate to user."
                )

        self.transitions.append(
            Transition(
                from_status=self.status,
                to_status=to_status,
                at=datetime.now(UTC),
                artifact=artifact,
                retry=is_retry,
                reason=reason,
            )
        )
        self.status = to_status
        self.updated_at = datetime.now(UTC)

    def set_drift_baseline(
        self,
        tasks_md_hash: str,
        apply_progress_topic: str,
        graph_node_count: int,
    ) -> None:
        """Record the baseline used for drift detection."""
        self.drift_baseline = {
            "tasks_md_hash": tasks_md_hash,
            "apply_progress_topic": apply_progress_topic,
            "graph_node_count": graph_node_count,
            "recorded_at": datetime.now(UTC).isoformat(),
        }

    def add_token_cost(self, n: int) -> None:
        """Increment the token cost counter and warn if approaching budget."""
        self.token_cost += n
        self.updated_at = datetime.now(UTC)

    @property
    def budget_used_pct(self) -> float:
        """Percentage of token budget used (0.0 to 1.0)."""
        if self.token_budget == 0:
            return 1.0
        return self.token_cost / self.token_budget

    def save(self) -> None:
        """Persist to state.json."""
        self.path.mkdir(parents=True, exist_ok=True)
        data = {
            "change": self.change,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "transitions": [t.to_dict() for t in self.transitions],
            "drift_baseline": self.drift_baseline,
            "cross_projects": self.cross_projects,
            "token_cost": self.token_cost,
            "token_budget": self.token_budget,
        }
        (self.path / "state.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def __repr__(self) -> str:
        return f"StateMachine(change={self.change!r}, status={self.status.value}, path={self.path})"
