Feature: State machine forward transitions
  Validates REQ-3 from spec/spec.md

  Scenario: NEW transitions to EXPLORED when exploration.md is written
    Given a fresh change "my-change" in status NEW
    When the watcher detects a write to "explore/exploration.md"
    Then the change status should become EXPLORED
    And state.json should record the transition with artifact "explore/exploration.md"

  Scenario: Forward path NEW through DONE succeeds
    Given a fresh change "feat-x" in status NEW
    When the user walks through all phases:
      | from       | to         | artifact                |
      | NEW        | EXPLORED   | explore/exploration.md  |
      | EXPLORED   | PROPOSED   | propose/proposal.md     |
      | PROPOSED   | DESIGNED   | design/design.md        |
      | DESIGNED   | SPECIFIED  | spec/spec.md            |
      | SPECIFIED  | TASKED     | tasks/tasks.md          |
      | TASKED     | APPLYING   |                         |
      | APPLYING   | VERIFYING  |                         |
      | VERIFYING  | ARCHIVING  |                         |
      | ARCHIVING  | DONE       |                         |
    Then the change status should be DONE
    And there should be 9 transitions logged

  Scenario: Skip transition is rejected with Cannot skip message
    Given a fresh change "skip-test" in status NEW
    When the user tries to transition directly to PROPOSED
    Then the system should raise InvalidTransitionError
    And the error message should contain "Cannot skip EXPLORED"
    And the change status should remain NEW
