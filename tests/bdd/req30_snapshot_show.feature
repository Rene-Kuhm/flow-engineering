# Snapshot show (REQ-30)
#
# As a flow-engineering user I want ``flow snapshot show <snap_id>`` to
# print the snapshot's JSON envelope (all top-level keys) so I can
# inspect a point-in-time copy of the graph from the terminal or pipe
# it to ``jq``.

Feature: Snapshot show (REQ-30)

  # SHOW ROUND-TRIP (1 scenario)

  Scenario: After creating a snapshot, flow snapshot show <snap_id> prints the JSON with all fields
    Given an InMemoryBackend seeded with 2 observations
    And a snapshot exists with description "show-test"
    When I show the snapshot
    Then the snapshot envelope has all 7 top-level keys
    And the snapshot envelope metadata sha256 matches the canonical-JSON hash
