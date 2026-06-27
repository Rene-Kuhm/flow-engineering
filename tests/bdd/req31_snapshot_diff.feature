# Snapshot diff (REQ-31)
#
# As a flow-engineering user I want ``flow snapshot diff`` to compute a
# structured diff between two snapshots (or one snapshot and the live
# state) so I can answer "what changed since I took this snapshot?"

Feature: Snapshot diff (REQ-31)

  # 2-ARG FORM: SNAPSHOT vs SNAPSHOT (1 scenario)

  Scenario: After creating snapshot A with 3 obs and B with 5 obs (2 added between), flow snapshot diff A B shows 2 added observations
    Given snapshot A was created with 3 observations
    And snapshot B was created with 5 observations (2 added after A)
    When I diff snapshot A against snapshot B
    Then the diff has added=[4, 5]
    And the diff has removed=[]
    And the diff has modified=[]
    And the diff has unchanged_count=3
    And the diff summary starts with "+2 -0 ~0"

  # 1-ARG FORM: SNAPSHOT vs LIVE (1 scenario)

  Scenario: With no second argument, flow snapshot diff A shows changes from A to current state
    Given snapshot A was created with 3 observations
    And 2 observations were added since snapshot A
    And observation 2 was updated since snapshot A
    When I diff snapshot A against live state
    Then the diff has added=[4, 5]
    And the diff has modified=[1 entry with id=2]
    And the diff has unchanged_count=2
    And the diff summary starts with "+2 -0 ~1"
