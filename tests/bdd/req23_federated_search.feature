# Federated multi-project search (REQ-23)
#
# As a flow-engineering user I want a single query that searches across
# multiple project tags so that I can ask "has any peer decided between
# Postgres and sqlite-vec?" and get a BM25-ranked answer with project
# attribution per hit, without having to remember which project knows.
#
# Notes on what the library provides today (vs spec REQ-23):
# - InMemoryBackend.mem_search_federated overrides the ABC default and
#   filters the in-memory dict by projects / since / type_filter. No
#   SQLite required for BDD tests.
# - ABC v1.2 default raises NotImplementedError when not overridden; the
#   third-party-subclass scenario verifies this contract.

Feature: Federated multi-project search (REQ-23)

  Scenario: Federated search across 3 projects returns results from each with project field per row
    Given an InMemoryBackend seeded with 3 observations across 3 distinct projects
    When I call mem_search_federated("drift") with all 3 projects
    Then 3 results are returned
    And each result has a non-null project field matching one of the queried projects

  Scenario: projects=["flow-engineering"] restricts the result set to a single project
    Given an InMemoryBackend seeded with 5 observations in flow-engineering and 3 in mockup-2-blog
    When I call mem_search_federated("drift", projects=["flow-engineering"])
    Then 5 results are returned
    And every result has project == "flow-engineering"

  Scenario: since="2026-06-01" excludes observations created before that date
    Given an InMemoryBackend with observations on 2026-05-15 and 2026-06-15 in flow-engineering
    When I call mem_search_federated("drift", projects=["flow-engineering"], since="2026-06-01")
    Then only the 2026-06-15 observation is returned

  Scenario: type_filter=["decision", "bugfix"] includes only matching types
    Given an InMemoryBackend with observations of types decision, bugfix, and pattern in flow-engineering
    When I call mem_search_federated("drift", projects=["flow-engineering"], type_filter=["decision", "bugfix"])
    Then 2 results are returned
    And every result has type decision or bugfix

  Scenario: ABC default raises NotImplementedError when not overridden
    Given a custom EngramBackend that does not override mem_search_federated
    When I call mem_search_federated("drift") on the custom backend
    Then NotImplementedError is raised
    And the error message includes "EngramBackend v1.2"