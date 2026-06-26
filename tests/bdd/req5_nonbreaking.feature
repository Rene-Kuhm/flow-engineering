Feature: non-breaking behavior for code_refs blocks
  REQ-5: saves without a block keep working; older readers see the full
  content including the block; FTS5 prose queries still match.

  Background:
    Given an in-memory Engram backend and a client for change "my-change"

  Scenario: Saves without code_refs continue to work
    Given observation prose with no code_refs marker
    When save_phase is called for "propose"
    Then the save succeeds
    And the persisted content includes the original prose

  Scenario: load_phase returns full content including the appended block
    Given observation prose ending with a valid manual block
    When save_phase is called for "propose"
    And load_phase is called for "propose"
    Then the loaded content equals the saved content
    And the loaded content contains the code_refs marker

  Scenario: FTS5-style prose query still matches observations with new block
    Given an observation whose prose contains the word "jwt"
    And save_phase is called for "propose"
    When mem_search is called for the query "jwt"
    Then the observation is returned in the results
