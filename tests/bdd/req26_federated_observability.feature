# Federated observability counters (REQ-26)
#
# As a flow-engineering operator I want every federated search to emit
# JSONL counter events so that ``flow metrics`` consumers can surface
# invocation counts, projects-queried distributions, and result totals
# without scraping Prometheus or instrumenting the call sites.
#
# Contract (mirrors spec REQ-26 + design D4):
# - 3 counters land in ``observability.FEDERATED_COUNTER_NAMES`` and are
#   emitted by ``record_federated_summary(...)`` on every
#   ``InMemoryBackend.mem_search_federated`` invocation (and by the CLI's
#   ``flow search --federated`` path via the same backend).
# - Names follow the REQ-8 / REQ-22 convention:
#   * ``_total`` suffix for counters (verb-style events)
#   * NO ``_total`` suffix on the histogram because the value IS the count
#   * ``trigger=cli|programmatic`` tag on the invoked counter
# - ``record_federated_summary`` is the single source of truth: any
#   counter name change MUST update both
#   ``observability.FEDERATED_COUNTER_NAMES`` and the helper body together
#   (REQ-26 scenario 4 invariant).
# - The metrics path is overridable via ``FLOW_METRICS_PATH`` so tests
#   never pollute ``~/.flow``.

Feature: Federated observability counters (REQ-26)

  # INVOKED COUNTER (1 scenario)

  Scenario: federated_search_invoked_total increments per federated call
    Given an InMemoryBackend with drift observations in 2 projects
    And the metrics path points at a tmp file
    When I run the CLI "flow search --federated drift --json"
    Then the metrics file contains a federated_search_invoked_total event with trigger=cli
    And the federated_search_invoked_total count is 1

  # PROJECTS-QUERIED HISTOGRAM (1 scenario)

  Scenario: federated_search_projects_queried records the per-call count bucket
    Given an InMemoryBackend with drift observations in 3 projects
    And the metrics path points at a tmp file
    When I run the CLI "flow search --federated --projects=flow-engineering,mockup-2-blog drift --json"
    Then the metrics file contains a federated_search_projects_queried event with count=2

  # RESULTS-RETURNED COUNTER (1 scenario)

  Scenario: federated_search_results_returned_total increments by sum of result counts
    Given an InMemoryBackend with drift observations in 3 projects
    And the metrics path points at a tmp file
    When I run the CLI "flow search --federated drift --json"
    And I run the CLI "flow search --federated drift --json"
    Then the federated_search_results_returned_total count is 6

  # ALL 3 COUNTERS IN CATALOG (1 scenario)

  Scenario: All 3 federated counters appear in the FEDERATED_COUNTER_NAMES catalog
    Given the observability module exposes FEDERATED_COUNTER_NAMES
    Then the catalog contains exactly 3 entries
    And the catalog names are "federated_search_invoked_total", "federated_search_projects_queried", "federated_search_results_returned_total"
