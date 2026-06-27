Feature: flow metrics export (REQ-38)
  As a flow operator integrating with Prometheus
  I want to export metrics in textfile format
  So that node_exporter can scrape them

  Scenario: Export to stdout in Prometheus textfile format
    Given 5 metric events are written (3 snapshot_create_total + 2 drift_invoked_total)
    When I run `flow metrics export --format prometheus`
    Then stdout contains "# HELP flow_snapshot_create_total"
    And stdout contains "# TYPE flow_snapshot_create_total counter"
    And stdout contains "flow_snapshot_create_total 3.0"
    And exit code is 0

  Scenario: Export to file at --out path (atomic write)
    Given 3 metric events (one each of binding / drift / vector)
    When I run `flow metrics export --format prometheus --out metrics.prom`
    Then file metrics.prom exists with valid Prometheus content
    And exit code is 0

  Scenario: Export with --window filters exported counters
    Given 6 metric events spanning 3 days (binding_event_oldest_3d, binding_event_2d, binding_event_1d, binding_event_90m, binding_event_30m, binding_event_5m)
    When I run `flow metrics export --format prometheus --window 1h`
    Then stdout contains only the in-window counters (binding_event_30m, binding_event_5m)
    And exit code is 0