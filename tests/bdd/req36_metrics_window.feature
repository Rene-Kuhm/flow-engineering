Feature: flow metrics summary --window filter (REQ-36)
  As a flow operator
  I want to filter metrics to a recent time window
  So that I can answer "what happened in the last 24h"

  Scenario: --window 1h filters to last 1 hour
    Given 5 metric events are written spanning 3 days (oldest 3d ago, newest 30m ago)
    When I run `flow metrics summary --window 1h --format text`
    Then stdout contains only the most-recent event's counter
    And exit code is 0

  Scenario: --since ISO8601 filters to events after timestamp
    Given 5 metric events spanning 3 days
    When I run `flow metrics summary --since 2026-06-26T00:00:00Z --format json`
    Then stdout JSON contains exactly the 2 events after that timestamp
    And exit code is 0
