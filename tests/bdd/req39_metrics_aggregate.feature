Feature: flow metrics aggregate percentile (REQ-39)
  As a flow operator
  I want to compute percentiles over counter values
  So that I can identify performance outliers

  Scenario: --percentile p95 computes p95 across counter increments in window
    Given 100 metric events of drift_invoked_total over 1 hour
    When I run `flow metrics aggregate --percentile p95 --format text`
    Then stdout contains "drift_invoked_total" with a p95 value
    And exit code is 0

  Scenario: --percentile with insufficient data emits "not enough data points" warning
    Given only 1 metric event exists
    When I run `flow metrics aggregate --percentile p99`
    Then stdout contains "not enough data points"
    And exit code is 0
