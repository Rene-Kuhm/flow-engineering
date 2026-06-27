# Federated search CLI flags (REQ-25)
#
# As a flow-engineering user I want ``flow search`` to accept opt-in
# federated flags so that I can search across multiple project tags with
# the same interface I already use for single-project search, WITHOUT
# breaking existing scripts that don't pass those flags.
#
# Notes on what the CLI provides today (vs spec REQ-25):
# - ``flow search "drift"`` (no --federated) is byte-identical to the
#   pre-change behaviour (D9 non-breaking guarantee): it calls
#   ``mem_search`` (single-project FTS) and never ``mem_search_federated``.
# - ``flow search --federated "drift"`` calls ``mem_search_federated``
#   with ``projects=None`` (search all projects). The output table adds a
#   PROJECT column when any row carries a project field.
# - ``--projects=<csv>`` restricts the search to the named projects.
# - ``--since=<iso>`` filters by ``created_at >= <iso>`` (lexicographic).
# - ``--type=<csv>`` filters by observation type (exact match).
# - All federated and vector paths are mutually exclusive.

Feature: Federated search CLI flags (REQ-25)

  Scenario: flow search without --federated is byte-identical to pre-change behaviour
    Given an InMemoryBackend with drift observations in 2 projects
    When I run the CLI "flow search drift"
    Then the exit code is 0
    And the search returns 2 results

  Scenario: flow search --federated returns results from all projects
    Given an InMemoryBackend with drift observations in 2 projects
    When I run the CLI "flow search --federated drift --json"
    Then the exit code is 0
    And the JSON has results from 2 distinct projects

  Scenario: flow search --federated --projects=<csv> restricts to the named projects
    Given an InMemoryBackend with drift observations in 3 projects
    When I run the CLI "flow search --federated --projects=flow-engineering,mockup-2-blog drift --json"
    Then the exit code is 0
    And every result has project "flow-engineering" or "mockup-2-blog"
    And no result has project "tecnodespegue-landing"

  Scenario: flow search --federated --since=<iso> excludes observations created before that date
    Given an InMemoryBackend with drift observations on 2026-05-15 and 2026-06-15
    When I run the CLI "flow search --federated --since=2026-06-01 drift --json"
    Then the exit code is 0
    And the result titles include "recent drift 2026-06-15"
    And the result titles do NOT include "old drift 2026-05-15"

  Scenario: flow search --federated --type=<csv> includes only matching type observations
    Given an InMemoryBackend with drift observations of mixed types
    When I run the CLI "flow search --federated --type=decision drift --json"
    Then the exit code is 0
    And the search returns 1 result
