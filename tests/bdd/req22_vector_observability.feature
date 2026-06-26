# Vector observability counters (REQ-22)
#
# As a flow-engineering operator I want every vector search and reindex
# operation to emit JSONL counter events so that ``flow metrics`` consumers
# can surface invocation counts, result totals, latency percentiles, index
# size, and reindex duration without scraping Prometheus or instrumenting
# the call sites.
#
# Contract (mirrors spec REQ-22 + design D11):
# - 6 counters land in ``observability.VECTOR_COUNTER_NAMES`` and are emitted
#   by ``record_vector_summary(...)`` on every ``mem_search_hybrid`` call and
#   every ``flow reindex`` completion (counters fire exactly once per event;
#   reindex fires the reindex pair once per CLI invocation).
# - Names follow REQ-8 convention:
#   * ``_total`` suffix for counters (verb-style events)
#   * ``_ms`` for latency histograms (``vector_search_latency_ms``)
#   * ``_seconds`` for duration gauges (``reindex_duration_seconds``)
#   * no suffix on gauges that carry their own unit (``vector_index_size_observations``)
# - ``vector_search_invoked_total`` is tagged ``trigger=cli|programmatic`` so
#   dashboards can separate user invocations from background work.
# - Reindex counters (``reindex_observations_total``, ``reindex_duration_seconds``)
#   fire from the CLI layer at ``flow reindex`` completion; the metrics path is
#   overridable via ``FLOW_METRICS_PATH`` so tests never pollute ``~/.flow``.
#
# Notes on what the library provides today:
# - The ``record_vector_summary`` helper is the single source of truth: any
#   counter name change MUST update both ``observability.VECTOR_COUNTER_NAMES``
#   and the helper body together (REQ-22 scenario 4 invariant).
# - The CLI reindex path uses ``observability.increment(...)`` directly for
#   the two reindex counters (parity with the drift / backfill helpers).
# - Latency is sampled per call (not aggregated); percentile computation lives
#   in the ``flow metrics`` consumer.

Feature: Vector observability counters (REQ-22)

  # INVOKED COUNTER (1 scenario)

  Scenario: vector_search_invoked_total increments per mem_search_hybrid call
    Given a HybridBackend with a MockEmbeddingProvider
    And a corpus of 3 observations
    When I call mem_search_hybrid("drift detection", k=3) with trigger=programmatic
    Then the observability JSONL file contains a line with counter "vector_search_invoked_total" tagged trigger=programmatic
    And the "vector_search_invoked_total" counter value is 1

  # LATENCY HISTOGRAM (1 scenario)

  Scenario: vector_search_latency_ms appears in metrics output
    Given a HybridBackend with a MockEmbeddingProvider
    And a corpus of 3 observations
    When I call mem_search_semantic("drift detection") with trigger=programmatic
    Then the observability JSONL file contains a line with counter "vector_search_latency_ms" with a positive elapsed_ms field
    And the elapsed_ms value is less than 1000ms

  # REINDEX COUNTERS (1 scenario)

  Scenario: reindex_observations_total matches total observations after reindex
    Given an InMemoryBackend seeded with 5 observations
    And the [vectors] extra is available
    And a tmp-path SqliteVecStore
    When I run flow reindex
    Then the "reindex_observations_total" counter value is 5
    And the vector_index_size_observations gauge reads 5

  # NAMING CONVENTION (1 scenario)

  Scenario: Counter names match REQ-8 convention (no naming drift)
    Given the REQ-22 counter catalog has 6 entries
    And a HybridBackend with a MockEmbeddingProvider
    And a corpus of 1 observations
    When I call mem_search_hybrid("drift detection", k=1) with trigger=programmatic
    Then the emitted counter names follow the subject_event_total or subject_metric_unit pattern
    And the canonical 6 names from REQ-22 are all present in the catalog
    And no non-conformant name like vector_search_invocations is emitted
