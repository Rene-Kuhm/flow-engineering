"""Retry policy for flow-engineering.

REQ-4: bounded retries on TRANSIENT failures only.
REQ-9: per-change token budget guard.
"""

from __future__ import annotations

from dataclasses import dataclass

from flow_engineering.drift import FailureClass


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_transient_retries: int = 2
    backoff_base_seconds: float = 1.0
    backoff_multiplier: float = 2.0


@dataclass
class RetryDecision:
    """Result of should_retry()."""

    should_retry: bool
    wait_seconds: float
    reason: str


def should_retry(
    failure_class: FailureClass,
    attempt: int,
    policy: RetryPolicy | None = None,
) -> RetryDecision:
    """Decide whether to retry based on failure class and attempt count.

    - TRANSIENT: retry up to policy.max_transient_retries with exponential backoff
    - STRUCTURAL: never retry, escalate immediately
    - CONTRACT: never retry, prompt for re-spec
    - UNKNOWN: treat as STRUCTURAL (safest)
    """
    policy = policy or RetryPolicy()

    if failure_class == FailureClass.STRUCTURAL:
        return RetryDecision(
            should_retry=False,
            wait_seconds=0,
            reason="Structural failure — escalate, never retry",
        )
    if failure_class == FailureClass.CONTRACT:
        return RetryDecision(
            should_retry=False,
            wait_seconds=0,
            reason="Contract failure — re-spec, never auto-retry",
        )
    if failure_class == FailureClass.UNKNOWN:
        return RetryDecision(
            should_retry=False,
            wait_seconds=0,
            reason="Unknown failure — escalate to user",
        )
    # TRANSIENT
    if attempt >= policy.max_transient_retries:
        return RetryDecision(
            should_retry=False,
            wait_seconds=0,
            reason=f"Max retries ({policy.max_transient_retries}) exceeded for TRANSIENT",
        )
    wait = policy.backoff_base_seconds * (policy.backoff_multiplier**attempt)
    return RetryDecision(
        should_retry=True,
        wait_seconds=wait,
        reason=f"Transient failure, attempt {attempt + 1}/{policy.max_transient_retries}",
    )


@dataclass
class CostGuard:
    """Per-change token budget tracker."""

    token_cost: int = 0
    token_budget: int = 100_000
    warn_threshold: float = 0.8

    def add(self, n: int) -> None:
        """Add tokens to the running cost."""
        self.token_cost += n

    @property
    def used_pct(self) -> float:
        if self.token_budget == 0:
            return 1.0
        return self.token_cost / self.token_budget

    @property
    def should_warn(self) -> bool:
        """True if at or above the warn threshold."""
        return self.used_pct >= self.warn_threshold

    @property
    def should_halt(self) -> bool:
        """True if over budget (caller should pause for user approval)."""
        return self.token_cost >= self.token_budget

    def warning_message(self) -> str:
        return (
            f"Token budget {self.used_pct:.0%} used "
            f"({self.token_cost}/{self.token_budget}). "
            f"Pause for user approval before continuing."
        )
