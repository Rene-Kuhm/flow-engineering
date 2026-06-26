# Hybrid scoring (REQ-18)
#
# As a flow-engineering user I want hybrid semantic + FTS scoring with a
# tunable alpha so that I can blend meaning and exact-match by query type.
#
# Linear combo formula: alpha * cosine_sim + (1 - alpha) * normalize_bm25(fts)
# where normalize_bm25(x) = (x - min) / (max - min + epsilon) over the FTS
# result set per query. alpha is in the closed interval [0.0, 1.0].

Feature: Hybrid scoring (REQ-18)

  # WORKED EXAMPLE (1 scenario)

  Scenario: Hybrid with alpha=0.5 ranks semantic + FTS blended (worked example)
    Given 3 observations with prose and known (semantic_sim, fts_score): obs1: (0.96, 0.50), obs2: (0.00, 0.20), obs3: (0.30, 0.10)
    And the query "drift detection"
    When I call mem_search_hybrid("drift detection", k=3, alpha=0.50)
    Then results are ordered: obs1, obs3, obs2
    And scores match (within 1e-3): obs1 = 0.980, obs3 = 0.150, obs2 = 0.125
    And the rank index of obs3 is 1

  # DEGENERACY SANITY (2 scenarios)

  Scenario: Hybrid with alpha=1.0 equals pure semantic (sanity)
    Given the seeded three-observation corpus
    And the query "drift detection"
    When I call mem_search_hybrid("drift detection", k=3, alpha=1.00)
    And I call mem_search_semantic("drift detection", k=3) (pure)
    Then hybrid results equal pure semantic results in order and ids
    And hybrid scores differ from pure semantic by at most 1e-3

  Scenario: Hybrid with alpha=0.0 equals pure FTS (sanity)
    Given the seeded three-observation corpus
    And the query "drift detection"
    When I call mem_search_hybrid("drift detection", k=3, alpha=0.00)
    And I call inner.mem_search("drift detection")
    Then hybrid results equal inner FTS results in order and ids
    And hybrid scores equal the FTS-only scores (1.0 * fts)

  # ALPHA VALIDATION (1 scenario)

  Scenario: Alpha=1.5 raises ValueError
    Given a HybridBackend wrapping an InMemoryBackend (scoring setup)
    When I call mem_search_hybrid("drift detection", alpha=1.50)
    Then ValueError is raised
    And the message contains "alpha must be in [0.0, 1.0]"

  # EMPTY RESULT (1 scenario)

  Scenario: Empty query returns empty results without division-by-zero
    Given a HybridBackend wrapping an InMemoryBackend (scoring setup)
    And a query that matches zero observations in the FTS index
    When I call mem_search_hybrid("nonexistent_xyz", k=10)
    Then [] is returned (no crash, no division-by-zero)
