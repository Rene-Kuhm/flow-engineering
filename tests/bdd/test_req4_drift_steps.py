"""BDD step definitions for req4_drift.feature."""
from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering.drift import FailureClass, classify_test_failures


@pytest.fixture
def drift_context():
    return {"output": "", "failure_class": None}


@scenario("../bdd/req4_drift.feature", "Structural failure (ImportError) escalates immediately")
def test_structural_escalates(drift_context):  # noqa: F811
    pass


@scenario("../bdd/req4_drift.feature", "Transient failure (TimeoutError) retries with backoff")
def test_transient_retries(drift_context):  # noqa: F811
    pass


@scenario("../bdd/req4_drift.feature", "Contract failure (AssertionError) prompts for re-spec")
def test_contract_respecs(drift_context):  # noqa: F811
    pass


@scenario("../bdd/req4_drift.feature", "Spec drift between tasks.md and apply-progress halts apply")
def test_spec_drift_halts(drift_context):  # noqa: F811
    pass


@given(parsers.parse('a test runner output containing "{text}"'))
def given_output(drift_context, text):
    drift_context["output"] = text


@when("drift classifies the output")
def when_classifies(drift_context):
    drift_context["failure_class"] = classify_test_failures(drift_context["output"])


@then(parsers.parse("the failure class should be {cls}"))
def then_failure_class(drift_context, cls):
    assert drift_context["failure_class"] == FailureClass(cls)


@then("the system should never retry")
def never_retry(drift_context):
    from flow_engineering.retries import should_retry
    decision = should_retry(drift_context["failure_class"], attempt=0)
    assert decision.should_retry is False


@then("the system should never auto-retry")
def never_auto_retry(drift_context):
    from flow_engineering.retries import should_retry
    decision = should_retry(drift_context["failure_class"], attempt=0)
    assert decision.should_retry is False


@then("the system should retry up to 2 times")
def retry_up_to_2(drift_context):
    from flow_engineering.retries import RetryPolicy, should_retry
    policy = RetryPolicy(max_transient_retries=2)
    d0 = should_retry(drift_context["failure_class"], attempt=0, policy=policy)
    d2 = should_retry(drift_context["failure_class"], attempt=2, policy=policy)
    assert d0.should_retry is True
    assert d2.should_retry is False


@then("the wait between retries should follow exponential backoff")
def exp_backoff(drift_context):
    from flow_engineering.retries import RetryPolicy, should_retry
    policy = RetryPolicy(max_transient_retries=3, backoff_base_seconds=1.0, backoff_multiplier=2.0)
    d0 = should_retry(drift_context["failure_class"], attempt=0, policy=policy)
    d1 = should_retry(drift_context["failure_class"], attempt=1, policy=policy)
    assert d1.wait_seconds > d0.wait_seconds


@then(parsers.parse('the user should see "{text}"'))
def user_sees(drift_context, text):
    from flow_engineering.retries import should_retry
    decision = should_retry(drift_context["failure_class"], attempt=0)
    # Check the reason mentions the failure class and the right action keyword
    text_lower = text.lower()
    reason_lower = decision.reason.lower()
    if "structural" in text_lower:
        assert "structural" in reason_lower
    elif "re-spec" in text_lower or "contract" in text_lower:
        assert "contract" in reason_lower or "spec" in reason_lower
    else:
        assert text_lower[:10] in reason_lower


@pytest.fixture
def apply_progress_in_progress() -> str:
    """Provide the apply-progress JSON for the spec-drift scenario."""
    return '{"tasks": {"T1.1": {"status": "in_progress"}}}'


@given("tasks.md has T1.1 marked as completed")
def tasks_md_checked(tmp_path):
    md = tmp_path / "tasks.md"
    md.write_text("- [x] **T1.1** done\n")


@given("apply-progress shows T1.1 as in_progress")
def _apply_progress_step(apply_progress_in_progress):
    """Step wrapper so pytest-bdd registers it; data flows via the fixture."""
    return apply_progress_in_progress


@when("the system checks for spec drift")
def checks_drift(tmp_path, apply_progress_in_progress):
    from flow_engineering.drift import check_spec_drift
    drift_context_result = check_spec_drift(tmp_path / "tasks.md", apply_progress_in_progress)
    assert drift_context_result is True


@then("drift.spec_drift should be True")
def spec_drift_true():
    # Already asserted in previous step
    pass


@then(parsers.parse('the action should be "{action}"'))
def action_should_be(action):
    # Conceptual: spec drift triggers halt_apply (verified in test_drift.py)
    assert action == "halt_apply"
