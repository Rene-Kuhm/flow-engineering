"""Unit tests for retries.py — RetryPolicy and CostGuard."""

from __future__ import annotations

from flow_engineering.drift import FailureClass
from flow_engineering.retries import CostGuard, RetryPolicy, should_retry


class TestShouldRetryStructural:
    def test_structural_never_retries(self) -> None:
        decision = should_retry(FailureClass.STRUCTURAL, attempt=0)
        assert decision.should_retry is False
        assert "Structural" in decision.reason

    def test_structural_never_retries_even_high_attempt(self) -> None:
        decision = should_retry(FailureClass.STRUCTURAL, attempt=10)
        assert decision.should_retry is False


class TestShouldRetryContract:
    def test_contract_never_retries(self) -> None:
        decision = should_retry(FailureClass.CONTRACT, attempt=0)
        assert decision.should_retry is False
        assert "Contract" in decision.reason


class TestShouldRetryUnknown:
    def test_unknown_treated_as_structural(self) -> None:
        decision = should_retry(FailureClass.UNKNOWN, attempt=0)
        assert decision.should_retry is False
        assert "Unknown" in decision.reason or "escalate" in decision.reason.lower()


class TestShouldRetryTransient:
    def test_transient_first_attempt_retries(self) -> None:
        policy = RetryPolicy(max_transient_retries=2)
        decision = should_retry(FailureClass.TRANSIENT, attempt=0, policy=policy)
        assert decision.should_retry is True
        assert decision.wait_seconds == 1.0

    def test_transient_second_attempt_retries(self) -> None:
        policy = RetryPolicy(max_transient_retries=2)
        decision = should_retry(FailureClass.TRANSIENT, attempt=1, policy=policy)
        assert decision.should_retry is True
        assert decision.wait_seconds == 2.0

    def test_transient_max_attempts_stops(self) -> None:
        policy = RetryPolicy(max_transient_retries=2)
        decision = should_retry(FailureClass.TRANSIENT, attempt=2, policy=policy)
        assert decision.should_retry is False
        assert "Max retries" in decision.reason

    def test_transient_backoff_exponential(self) -> None:
        policy = RetryPolicy(
            max_transient_retries=5, backoff_base_seconds=1.0, backoff_multiplier=3.0
        )
        d0 = should_retry(FailureClass.TRANSIENT, attempt=0, policy=policy)
        d1 = should_retry(FailureClass.TRANSIENT, attempt=1, policy=policy)
        d2 = should_retry(FailureClass.TRANSIENT, attempt=2, policy=policy)
        assert d0.wait_seconds == 1.0
        assert d1.wait_seconds == 3.0
        assert d2.wait_seconds == 9.0


class TestCostGuard:
    def test_initial_state(self) -> None:
        cg = CostGuard()
        assert cg.used_pct == 0.0
        assert not cg.should_warn
        assert not cg.should_halt

    def test_add_tokens(self) -> None:
        cg = CostGuard()
        cg.add(50_000)
        assert cg.token_cost == 50_000
        assert cg.used_pct == 0.5
        assert not cg.should_warn  # below 80%
        assert not cg.should_halt

    def test_warn_at_threshold(self) -> None:
        cg = CostGuard()
        cg.add(80_000)
        assert cg.used_pct == 0.8
        assert cg.should_warn
        assert not cg.should_halt

    def test_halt_over_budget(self) -> None:
        cg = CostGuard()
        cg.add(100_000)
        assert cg.should_halt
        cg.add(1)
        assert cg.should_halt  # even more so

    def test_zero_budget(self) -> None:
        cg = CostGuard(token_budget=0)
        assert cg.used_pct == 1.0
        assert cg.should_halt

    def test_warning_message_includes_pct(self) -> None:
        cg = CostGuard(token_budget=100, warn_threshold=0.5)
        cg.add(60)
        msg = cg.warning_message()
        assert "60%" in msg
        assert "60/100" in msg
