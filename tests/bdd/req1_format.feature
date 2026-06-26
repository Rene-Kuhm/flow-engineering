Feature: code_refs block format
  REQ-1: a trailing `<!-- code_refs -->` JSON block is the wire contract
  for binding Engram observations to Graphify code nodes.

  Background:
    Given the binding module is importable

  Scenario: Marker present with valid JSON parses cleanly
    Given an observation ending with a valid manual binding block
    When the parser extracts the block
    Then it returns one CodeRef with id "src_auth_jwt_tokenmgr"
    And the original prose is preserved byte-for-byte

  Scenario: Marker absent — content stays pure prose
    Given an observation with no code_refs marker
    When the parser extracts the block
    Then it returns an empty list
    And the original content is returned unchanged

  Scenario: Empty nodes array is a valid unbound block
    Given an observation ending with an empty unbound block
    When the parser extracts the block
    Then it returns an empty list

  Scenario: Malformed JSON after marker raises a parse error
    Given an observation ending with "<!-- code_refs -->" followed by invalid JSON
    When the parser extracts the block
    Then it raises ParseError with a non-negative offset
