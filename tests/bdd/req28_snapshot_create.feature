# Snapshot creation (REQ-28)
#
# As a flow-engineering user I want ``flow snapshot create`` to write a
# gzipped JSON snapshot to ``~/.flow-engineering/snapshots/`` so I have a
# tamper-evident point-in-time copy of the observation graph. The first
# snapshot in an empty directory auto-labels ``initial_state`` (UX nudge);
# an explicit ``--description`` always wins.

Feature: Snapshot creation (REQ-28)

  # ROUND-TRIP CREATE (1 scenario)

  Scenario: flow snapshot create writes a snapshot with all current observations and a sha256
    Given an InMemoryBackend seeded with 5 observations
    And the snapshot directory is empty
    When I create a snapshot without a description
    Then the snapshot directory contains 1 snapshot file
    And the snapshot envelope has schema 1
    And the snapshot envelope metadata sha256 matches the canonical-JSON hash
    And the snapshot envelope graph_state contains all 5 observations

  # EXPLICIT DESCRIPTION OVERRIDES AUTO-LABEL (1 scenario)

  Scenario: flow snapshot create --description "pre-deploy-v0.6" stores the description verbatim
    Given an InMemoryBackend seeded with 3 observations
    And the snapshot directory contains 1 prior snapshot
    When I create a snapshot with description "pre-deploy-v0.6"
    Then the new snapshot envelope description equals "pre-deploy-v0.6"
    And the prior snapshot file is unchanged
