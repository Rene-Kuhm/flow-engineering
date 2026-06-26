Feature: Drift detection with 3 failure classes
  Validates REQ-4 from spec/spec.md

  Scenario: Structural failure (ImportError) escalates immediately
    Given a test runner output containing "ImportError: cannot import name 'foo'"
    When drift classifies the output
    Then the failure class should be STRUCTURAL
    And the system should never retry
    And the user should see "Structural failure. Fix the spec or design before retrying."

  Scenario: Transient failure (TimeoutError) retries with backoff
    Given a test runner output containing "TimeoutError: test exceeded 30s"
    When drift classifies the output
    Then the failure class should be TRANSIENT
    And the system should retry up to 2 times
    And the wait between retries should follow exponential backoff

  Scenario: Contract failure (AssertionError) prompts for re-spec
    Given a test runner output containing "AssertionError: expected 200, got 404"
    When drift classifies the output
    Then the failure class should be CONTRACT
    And the system should never auto-retry
    And the user should see "Re-spec or update implementation"

  Scenario: Spec drift between tasks.md and apply-progress halts apply
    Given tasks.md has T1.1 marked as completed
    And apply-progress shows T1.1 as in_progress
    When the system checks for spec drift
    Then drift.spec_drift should be True
    And the action should be "halt_apply"
