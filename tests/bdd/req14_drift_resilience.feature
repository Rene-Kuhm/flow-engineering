Feature: drift detection non-breaking behavior (REQ-14)

  REQ-14 acceptance scenarios for the ``flow drift <change>`` CLI's
  non-breaking promises:
  - Per-row isolation: one bad row does NOT abort the scan.
  - Never raises: malformed ``graph.json`` produces exit code 0 or 2
    (never an unhandled exception).
  - Read-only by default: no ``--write-back`` means no Engram writes.
  - Large ``graph.json`` handled gracefully (no timeouts).

  Scenario: per-row isolation (one bad row doesn't fail others)
    Given a change with 1 valid + 1 invalid finding
    When I run `flow drift <change> --write-back`
    Then exit code is 1 (the valid one counted)
    And stderr contains "WARN: drift write-back skipped"

  Scenario: no exceptions raised by drift detection
    When I run `flow drift <change>` against a malformed graph.json
    Then exit code is 0 or 2 (never raises)
    And stdout contains "unable_to_verify"

  Scenario: read-only default (no observation metadata changes)
    Given a change with 3 findings
    When I run `flow drift <change>` (no flags)
    Then no observation metadata changed

  Scenario: large graph.json (>10MB) handled gracefully
    Given a 10MB graph.json
    When I run `flow drift <change>`
    Then exit code is 0
    And processing completes in <5 seconds
