# Snapshot listing (REQ-29)
#
# As a flow-engineering user I want ``flow snapshot list`` to return my
# snapshots in reverse chronological order so the newest is at the top,
# and to support ``--since`` + ``--limit`` filters so I can scope the
# listing to a recent window.

Feature: Snapshot listing (REQ-29)

  # REVERSE CHRONOLOGICAL ORDER (1 scenario)

  Scenario: After creating 3 snapshots, flow snapshot list returns 3 entries in reverse chronological order
    Given an InMemoryBackend seeded with 1 observation
    And the snapshot directory contains 3 snapshots created at ascending times
    When I list snapshots
    Then the snapshot list has 3 entries
    And the snapshot list is in reverse chronological order
    And each entry has the 6 required keys

  # SINCE + LIMIT FILTERS (1 scenario)

  Scenario: flow snapshot list --since=<recent_iso> returns only snapshots at or after that timestamp
    Given an InMemoryBackend seeded with 1 observation
    And the snapshot directory contains 5 snapshots created at ascending times
    When I list snapshots with since="<T3.created_at>" and limit=10
    Then the snapshot list contains 3 entries
    And the snapshot list excludes the T1 and T2 snapshots
    And combining --since and --limit=2 returns the 2 newest within the filter
