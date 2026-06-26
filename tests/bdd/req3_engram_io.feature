Feature: engram_io save_observation honors the code_refs marker
  REQ-3: writes content unchanged when no marker; validates and preserves
  valid blocks; rejects malformed blocks before writing.

  Background:
    Given an in-memory Engram backend and a client for change "my-change"

  Scenario: Save without marker writes through with an unbound block appended
    Given observation prose with no code_refs marker
    When save_phase is called for "propose"
    Then the persisted content includes the original prose
    And the persisted content ends with a code_refs block

  Scenario: Save with valid block writes the content with block intact
    Given observation prose ending with a valid manual block
    When save_phase is called for "propose"
    Then the persisted content contains exactly one code_refs marker
    And the persisted block source is "manual"

  Scenario: Save with malformed block is rejected before write
    Given observation prose ending with "<!-- code_refs -->" followed by invalid JSON
    When save_phase is called for "propose"
    Then it raises ParseError
    And no observation row was written

  Scenario: Save with unknown schema version is rejected before write
    Given observation prose ending with a code_refs block with schema 99
    When save_phase is called for "propose"
    Then it raises ParseError mentioning "schema"
    And no observation row was written
