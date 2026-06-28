Feature: flow drift-events read-side CLI (REQ-V1.0.2 + REQ-V1.0.3)

  REQ-V1.0.2 + REQ-V1.0.3 acceptance scenarios for the ``flow drift-events``
  read-side CLI surface. The CLI reads from
  ``~/.flow-engineering/drift_events.jsonl`` and surfaces 3 subcommands:
  ``list`` (filters + 4 output formats), ``tail`` (last N events newest-first),
  and ``stats`` (per-event-class + per-change + per-decision-id top-N counts).
  This file closes the deferred S2 from ``drift-hardening`` verify-report
  and pairs with the wire-format flip in REQ-V1.0.1.

  Scenario: Operator reads drift events as default text table (REQ-V1.0.2)
    Given the drift event log has 5 events from 2 changes
    When the operator runs `flow drift-events list`
    Then the output contains a fixed-width table with columns "change | decision_id | binding_id | class | detected_at"
    And the table contains 5 data rows

  Scenario: Operator tails recent drift events newest-first (REQ-V1.0.3)
    Given the drift event log has 15 events
    When the operator runs `flow drift-events tail --limit=5`
    Then the output contains exactly 5 rows
    And the rows are ordered newest-first by detected_at

  Scenario: Operator summarizes drift counts per change (REQ-V1.0.3)
    Given the drift event log has 10 events from 3 changes
    When the operator runs `flow drift-events stats`
    Then the output contains a per-change count table with 3 change rows
    And the output contains per-event-class counts