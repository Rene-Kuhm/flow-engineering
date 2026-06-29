# flow where "<query>" cross-source retrieval (REQ-V1.0.1 + REQ-V1.0.3 cross-cutting render contract)
#
# The 7 scenarios owned by the orchestrator-led spec phase are upstream of this
# change; T2.5 owns the 2 cross-cutting render-contract scenarios that exercise
# the orchestrator + the graphify fail-open path together. Mirrors the BDD-first
# test pattern set by `graphify_query` (tests/bdd/test_vector_search_steps.py).
#
# Scenario isolation:
# - `tmp_path` is rooted at the WHOLE repo (we chdir via the step glue) so the
#   subprocess rg finds real `src/`, `tests/`, `openspec/changes/archive/`.
# - For the graphify-present scenario, the step writes a fixture `graph.json`
#   and monkeypatches `flow_engineering.where.DEFAULT_GRAPH_PATH` so the test
#   never reads the user's real `graphify-out/` snapshot.

Feature: flow where "<query>" cross-source retrieval (REQ-V1.0.1 + REQ-V1.0.3)

  Scenario: Graphify index absent renders the deterministic unavailable message
    Given a fresh repo with no graphify-out/graph.json
    When I run flow where with the query "jwt"
    Then the GRAPH section contains the literal "unavailable / no graph index found"
    And the section order is CODE then TESTS then SDD then GRAPH

  Scenario: Graphify index present renders scored hits
    Given a fresh repo with a fixture graph.json matching the query
    When I run flow where with the query "jwt"
    Then the GRAPH section lists at least one entry for the matching node
    And the section order is CODE then TESTS then SDD then GRAPH
