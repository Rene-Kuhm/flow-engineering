Feature: flow drift exit codes (REQ-11)

  REQ-11 acceptance scenarios for the ``flow drift <change>`` CLI exit
  code contract:
  - 0 when every binding (if any) is STILL_VALID.
  - 1 when any binding classifies as non-STILL_VALID (drift detected).
  - 2 when the graph is unavailable (terminal unable_to_verify state);
    2 wins over 1 (REQ-11 priority order).

  Scenario: exit code 0 when no drift
    Given a change with 0 drift findings
    When I run `flow drift <change>`
    Then exit code is 0

  Scenario: exit code 1 when drift detected
    Given a change with 3 drift findings
    When I run `flow drift <change>`
    Then exit code is 1

  Scenario: exit code 2 wins over exit code 1 (graph unavailable)
    Given a change with drift findings + graph unavailable
    When I run `flow drift <change>`
    Then exit code is 2 (graph_unavailable wins)
