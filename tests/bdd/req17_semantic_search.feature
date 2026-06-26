# Semantic search activation gate (REQ-17)
#
# As a flow-engineering user I want semantic and hybrid search to be opt-in
# via gate conditions so that the default install never pulls torch + sqlite-vec.
#
# Notes on what the library provides today (vs spec REQ-17):
# - Scenario 1 (active path): HybridBackend with a MockEmbeddingProvider returns
#   results — the gate is open via the mock seam.
# - Scenarios 2-3 (gate rejection): InMemoryBackend ALWAYS raises
#   VectorSearchDisabled with the install hint (the env-vs-extra distinction
#   is enforced at the CLI layer in PR#2 T2.4, not in the library).

Feature: Semantic search activation gate (REQ-17)

  # ACTIVE PATH (1 scenario)

  Scenario: Semantic search with both extra and env set returns results
    Given a HybridBackend wrapping an InMemoryBackend with a MockEmbeddingProvider
    And a corpus of 3 observations with semantic content
    When I call mem_search_semantic("drift detection", k=3)
    Then 3 results are returned
    And each result has keys observation_id, score, rank
    And results are ordered by score descending

  # GATE REJECTION (2 scenarios) — InMemoryBackend is the prose test fixture;
  # it ALWAYS raises VectorSearchDisabled with the install hint (the env-vs-extra
  # distinction is enforced at the CLI layer in PR#2 T2.4). BDD covers what the
  # library provides today.

  Scenario: Semantic search without extra raises VectorSearchDisabled with install hint
    Given an InMemoryBackend (vectors disabled)
    When I call mem_search_semantic("drift detection")
    Then VectorSearchDisabled is raised
    And the error message includes "pip install flow-engineering[vectors]"
    And no torch or sqlite_vec import is attempted

  Scenario: Semantic search without env var raises VectorSearchDisabled
    Given an InMemoryBackend (vectors disabled)
    And the env var FLOW_VECTOR_SEARCH is unset
    When I call mem_search_semantic("drift detection")
    Then VectorSearchDisabled is raised
    And no torch or sqlite_vec import is attempted

  # ZERO REGRESSION (1 scenario)

  Scenario: mem_search (FTS5) still works unchanged when vectors disabled
    Given an InMemoryBackend (vectors disabled)
    And the env var FLOW_VECTOR_SEARCH is unset
    And a corpus of 3 observations
    When I call mem_search("drift detection")
    Then FTS5 results are returned normally
    And no exception is raised
    And no torch or sqlite_vec import is attempted

  # HYBRID FORWARDING (1 scenario) — non-search methods MUST pass through

  Scenario: HybridBackend delegation - non-search methods pass through
    Given a HybridBackend wrapping an InMemoryBackend
    When I call hybrid.mem_save with title "delegated" and content "body"
    Then the observation is saved to the inner backend
    And reading via inner.mem_get_observation returns the saved observation
