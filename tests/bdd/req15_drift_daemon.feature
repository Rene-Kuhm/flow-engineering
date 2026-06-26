Feature: flow watch --drift daemon integration (REQ-15)

  REQ-15 acceptance scenarios for the drift daemon wiring. The daemon's
  ``handle_apply_progress_event`` seam runs ``decision_drift.scan_change``
  when any task in an apply-progress payload has ``status: merged``,
  emits a one-line summary via the ``on_summary`` callable, increments
  REQ-12 drift counters via ``observability.record_drift_summary``, and
  survives a missing ``graph.json`` (logs ``unable_to_verify`` once, does
  not raise).

  The three scenarios below bind to the seam function directly (rather
  than to the full CLI) because the seam is the pure-function contract
  exercised by the daemon's watchdog handler. End-to-end CLI wiring is
  covered by the unit tests in ``tests/unit/test_cli_watch_drift.py``.

  Scenario: Drift detected -> event-log summary line emitted
    Given a change "auth-refactor" with drifted bindings
    And a graph.json file
    When the daemon processes an apply-progress payload with task "T1" status "merged"
    Then the summary line starts with "drift: auth-refactor"
    And the summary line mentions "1 STALE_LOCATION"
    And the drift_stale_location_total counter is 1

  Scenario: No drift -> no event-log summary line
    Given a change "auth-refactor" with valid bindings
    And a graph.json file
    When the daemon processes an apply-progress payload with task "T1" status "in_progress"
    Then no summary line is emitted
    And no drift_*_total counter increments

  Scenario: Missing graph -> daemon survives with one-time unable_to_verify log
    Given a change "auth-refactor"
    And the graph.json file is absent
    When the daemon processes an apply-progress payload with task "T1" status "merged"
    Then the summary line contains "unable_to_verify" exactly once
    And the daemon stays alive (no exception raised)
    And the drift_unable_to_verify_total counter is 1