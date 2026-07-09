"""BDD step definitions for req3_state.feature."""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering.state import ChangeStatus, InvalidTransitionError, StateMachine


@pytest.fixture
def change_context(tmp_path):
    """Shared context across BDD steps."""
    return {"path": tmp_path, "change_dir": None, "sm": None, "error": None}


@scenario("../bdd/req3_state.feature", "NEW transitions to EXPLORED when exploration.md is written")
def test_new_to_explored(change_context):  # noqa: F811
    pass


@scenario("../bdd/req3_state.feature", "Forward path NEW through DONE succeeds")
def test_full_path(change_context):  # noqa: F811
    pass


@scenario("../bdd/req3_state.feature", "Skip transition is rejected with Cannot skip message")
def test_skip_rejected(change_context):  # noqa: F811
    pass


@given(parsers.parse('a fresh change "{change}" in status NEW'))
def fresh_change(change_context, change):
    change_dir = change_context["path"] / "flow-engineering" / change
    change_dir.mkdir(parents=True)
    StateMachine.create(change, change_dir)
    change_context["change_dir"] = change_dir
    change_context["change"] = change


@given(parsers.parse('a fresh change "{change}" in status NEW'))
def fresh_change_status(change_context, change):
    """Alias for scenarios with different wording."""
    fresh_change(change_context, change)


@when('the watcher detects a write to "explore/exploration.md"')
def watcher_detects(change_context):
    from flow_engineering.watcher import make_exploration_watcher

    make_exploration_watcher(change_context["change_dir"])(
        change_context["change_dir"] / "explore" / "exploration.md"
    )


@when(parsers.parse("the user walks through all phases:"))
def walk_phases(change_context, datatable):
    """datatable is a list of dicts with from/to/artifact columns."""
    sm = StateMachine.load(change_context["change_dir"])
    headers = datatable[0] if datatable else []
    rows = datatable[1:] if len(datatable) > 1 else []
    for row in rows:
        rec = dict(zip(headers, row, strict=False))
        sm.transition(
            ChangeStatus(rec["to"]),
            artifact=rec["artifact"] or None,
        )
    sm.save()


@when(parsers.parse("the user tries to transition directly to PROPOSED"))
def try_skip(change_context):
    sm = StateMachine.load(change_context["change_dir"])
    try:
        sm.transition(ChangeStatus.PROPOSED)
    except InvalidTransitionError as e:
        change_context["error"] = e


@then(parsers.parse("the change status should become EXPLORED"))
def status_explored(change_context):
    sm = StateMachine.load(change_context["change_dir"])
    assert sm.status == ChangeStatus.EXPLORED


@then(parsers.parse('state.json should record the transition with artifact "{artifact}"'))
def artifact_recorded(change_context, artifact):
    import json

    data = json.loads((change_context["change_dir"] / "state.json").read_text())
    assert data["transitions"][-1]["artifact"] == artifact


@then(parsers.parse("the change status should be {status}"))
def check_status(change_context, status):
    sm = StateMachine.load(change_context["change_dir"])
    assert sm.status == ChangeStatus(status)


@then(parsers.parse("there should be {count:d} transitions logged"))
def transition_count(change_context, count):
    sm = StateMachine.load(change_context["change_dir"])
    assert len(sm.transitions) == count


@then("the system should raise InvalidTransitionError")
def raised_error(change_context):
    assert change_context["error"] is not None
    assert isinstance(change_context["error"], InvalidTransitionError)


@then(parsers.parse('the error message should contain "{text}"'))
def error_message_contains(change_context, text):
    assert text in str(change_context["error"])


@then(parsers.parse("the change status should remain {status}"))
def status_remains(change_context, status):
    sm = StateMachine.load(change_context["change_dir"])
    assert sm.status == ChangeStatus(status)
