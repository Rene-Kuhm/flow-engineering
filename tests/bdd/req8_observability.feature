Feature: observability counters close (REQ-8)
  REQ-8 (PR#2 batch 2 close): the observability sink MUST track
  `inspect_invoked_total`, `inspect_render_ms`, `backfill_observations_total`,
  and `backfill_with_refs_total`. The `backfill_coverage` helper MUST compute
  the ratio of backfill-sourced observations to total observations, rounded
  to 3 decimal places.

  Background:
    Given the metrics sink points at a tmp file

  Scenario: manual_count increments when explicit code_refs block is saved with source manual
    Given an in-memory Engram backend with one observation carrying source "manual"
    When backfill_coverage is computed
    Then the ratio is 0.0

  Scenario: backfill_coverage reflects ratio of backfilled to total observations
    Given an in-memory Engram backend with 46 backfill observations and 57 manual observations
    When backfill_coverage is computed
    Then the ratio is 0.447

  Scenario: backfill_coverage with no observations returns 0
    Given an in-memory Engram backend with no observations
    When backfill_coverage is computed
    Then the ratio is 0.0

  Scenario: backfill_coverage with all backfilled observations returns 1.0
    Given an in-memory Engram backend with 3 backfill observations and 0 other observations
    When backfill_coverage is computed
    Then the ratio is 1.0

  Scenario: record_backfill_coverage increments both coverage counters
    When record_backfill_coverage is called with observations_total=10 and with_refs=4
    Then the backfill_observations_total counter was incremented with count=10
    And the backfill_with_refs_total counter was incremented with count=4

  Scenario: flow inspect increments inspect_invoked_total
    Given an in-memory Engram backend with one observation
    When the flow inspect command runs for change "my-change" once
    Then the inspect_invoked_total counter was incremented

  Scenario: flow inspect records inspect_render_ms
    Given an in-memory Engram backend with one observation
    When the flow inspect command runs for change "my-change" once
    Then the inspect_render_ms counter was recorded with elapsed_ms