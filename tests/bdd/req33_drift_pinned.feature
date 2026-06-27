# Drift-pinned scan via snapshot (REQ-33)
#
# As a flow-engineering user I want ``flow drift --snapshot=<snap_id>``
# to scan the snapshot's frozen observation + graph.json state instead
# of live so I can answer "what was the drift state at time T?" without
# losing signal to intervening changes. The flag is OPT-IN: without it,
# behavior is byte-identical to pre-change (D13 non-breaking).

Feature: Drift-pinned scan via snapshot (REQ-33)

  # FROZEN-STATE SCAN (1 scenario)

  Scenario: Snapshot from 2026-06-01 with 0 drift findings; running flow drift --snapshot=<that_id> returns 0 findings even if live state has drift
    Given a snapshot snap_frozen exists with 1 binding at file "src/vec.py" line 42
    And the snapshot's frozen graph shows the binding id "vec_store" at file "src/vec.py" line 42
    And today the live graph shows the same id at file "src/vec.py" line 87
    When I run flow drift with snapshot snap_frozen on change "vector-semantic-search"
    Then the report contains 1 finding with class STILL_VALID

  # NON-BREAKING DEFAULT (1 scenario)

  Scenario: flow drift <change> without --snapshot is byte-identical to current behavior
    Given a snapshot snap_frozen exists with 1 binding at file "src/vec.py" line 42
    And the snapshot's frozen graph shows the binding id "vec_store" at file "src/vec.py" line 42
    And today the live graph shows the same id at file "src/vec.py" line 87
    When I run flow drift without --snapshot on change "vector-semantic-search"
    Then the report contains 1 finding with class STALE_LOCATION