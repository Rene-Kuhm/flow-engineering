Feature: flow inspect renders decisions and bindings as a table
  REQ-7 (PR#2 batch 2): `flow inspect <change>` MUST render the decisions of
  an SDD change as a table with columns `decision`, `code_refs`, and
  `freshness`. The renderer MUST isolate malformed blocks per row — one bad
  row MUST NOT blank the whole table. The output supports `--json` for
  machine consumption.

  Background:
    Given the metrics sink points at a tmp file

  Scenario: flow inspect renders one row per binding
    Given an in-memory Engram backend with one decision carrying two bindings
    When the flow inspect command runs for change "my-change"
    Then the output contains two binding ids

  Scenario: Change with no bindings shows explicit unbound marker
    Given an in-memory Engram backend with one decision carrying source "unbound"
    When the flow inspect command runs for change "my-change"
    Then the output contains the unbound marker

  Scenario: Freshness column shows recent age without stale warning
    Given an in-memory Engram backend with one decision saved 5 seconds ago
    When the flow inspect command runs for change "my-change"
    Then the output does not contain the stale warning

  Scenario: Freshness column shows stale warning when older than 30 days
    Given an in-memory Engram backend with one decision saved 60 days ago
    When the flow inspect command runs for change "my-change"
    Then the output contains the stale warning

  Scenario: Malformed block in one row does not blank the table
    Given an in-memory Engram backend with one good decision and one malformed decision
    When the flow inspect command runs for change "my-change"
    Then the good decision title is visible
    And the malformed row shows a parse error note

  Scenario: --json flag emits valid JSON
    Given an in-memory Engram backend with one decision carrying one binding
    When the flow inspect command runs for change "my-change" with --json
    Then the output parses as JSON
    And the JSON contains the binding id

  Scenario: Change with no observations succeeds gracefully
    Given an in-memory Engram backend with no observations
    When the flow inspect command runs for change "empty-change"
    Then the exit code is 0
    And the output indicates no observations