Feature: flow metrics summary (REQ-35)
  As a flow operator
  I want a dashboard view of all counter totals by domain
  So that I can quickly understand system activity

  Scenario: Summary over all domains shows per-domain counter totals
    Given 12 metric events are written across 4 domains (3 binding + 3 drift + 3 vector + 3 snapshot)
    When I run `flow metrics summary --format text`
    Then stdout contains a "binding:" section
    And stdout contains a "drift:" section
    And stdout contains a "vector:" section
    And stdout contains a "snapshot:" section
    And exit code is 0

  Scenario: Summary with empty metrics file emits "no metrics yet" message
    Given metrics file does not exist
    When I run `flow metrics summary --format text`
    Then stdout contains "No metrics recorded yet."
    And exit code is 0