Feature: flow drift <change> CLI flags (REQ-10)

  REQ-10 acceptance scenarios for the ``flow drift <change>`` CLI surface.
  Covers the user-facing flags that wrap the ``decision_drift.scan_change``
  library call: ``--json`` (machine output), ``--include-obsolete`` (opt
  into expensive OBSOLETE classification), ``--since=<iso>`` (filter
  observations by created_at), ``--write-back`` (persist per-finding
  metadata to live Engram), ``--graph-json=<path>`` (custom graph), and
  the default text table format. Also covers the S2 stderr WARN when
  ``--write-back`` encounters non-int ``decision_id`` rows.

  Scenario: --json outputs structured JSON
    Given a change with 3 drift findings
    When I run `flow drift <change> --json`
    Then stdout is valid JSON with key "findings"
    And stdout JSON contains 3 finding entries

  Scenario: --include-obsolete shows OBSOLETE class findings
    Given a change with OBSOLETE + LABEL_DRIFT findings
    When I run `flow drift <change> --include-obsolete`
    Then stdout contains OBSOLETE entries
    And exit code is 1 (drift detected)

  Scenario: --since filters to events after timestamp
    Given 5 findings spanning 3 days
    When I run `flow drift <change> --since 2026-06-26T00:00:00Z`
    Then stdout contains only findings after that timestamp

  Scenario: --write-back updates observation metadata
    Given a change with 3 findings
    When I run `flow drift <change> --write-back`
    Then 3 observations have new metadata
    And exit code is 1 (drift detected)

  Scenario: --graph-json reads from custom path
    Given a graph.json at /tmp/custom-graph.json
    When I run `flow drift <change> --graph-json /tmp/custom-graph.json`
    Then stdout contains findings computed against that graph

  Scenario: --format=text is default
    When I run `flow drift <change>` (no flags)
    Then stdout is human-readable table

  Scenario: Invalid --since format exits 2
    When I run `flow drift <change> --since "not-a-date"`
    Then exit code is 2
    And stderr contains "--since must be ISO 8601"

  Scenario: --write-back with non-int decision_id emits stderr WARN (S2)
    Given a finding with decision_id="unknown"
    When I run `flow drift <change> --write-back`
    Then stderr contains "WARN: drift write-back skipped"

  Scenario: --write-back updates are idempotent
    When I run `flow drift <change> --write-back` twice
    Then no duplicate metadata entries
