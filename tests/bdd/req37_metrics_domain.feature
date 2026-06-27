Feature: flow metrics summary --domain slice (REQ-37)
  As a flow operator
  I want to slice metrics by domain
  So that I can answer "what is the drift activity this hour"

  Scenario: --domain snapshot shows only snapshot_* counters
    Given 12 metric events are written across 4 domains (3 binding + 3 drift + 3 vector + 3 snapshot)
    When I run `flow metrics summary --domain snapshot --format text`
    Then stdout contains only the 3 snapshot_* counter names
    And stdout does NOT contain "binding:" or "drift:" or "vector:"
    And exit code is 0

  Scenario: No --domain shows all 8 domains aggregated
    Given 24 metric events across all 8 domains (3 each)
    When I run `flow metrics summary --format text`
    Then stdout contains all 8 domain headers (binding, drift, vector, snapshot, backfill, federated, metadata, engine)
    And exit code is 0