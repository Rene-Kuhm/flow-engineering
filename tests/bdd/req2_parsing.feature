Feature: binding extract and format round-trip
  REQ-2: extract( format( extract(content) ) ) == extract(content) for any
  well-formed input; format() rejects unknown source values.

  Background:
    Given the binding module is importable

  Scenario: extract preserves field order across multiple bindings
    Given an observation with two bindings in the order [A, B]
    When the parser extracts the block
    Then it returns two CodeRefs in the order [A, B]

  Scenario: format produces a canonical block string with marker and schema
    Given a list of one CodeRef with source "manual"
    When binding formats the refs with source "manual"
    Then the output starts with "<!-- code_refs -->"
    And the body contains "schema: 1"
    And the output ends with a newline

  Scenario: extract composed with format composed with extract is idempotent
    Given an observation with a well-formed manual block
    When the parser extracts then formats then extracts again
    Then the second extraction equals the first

  Scenario: format rejects an unknown source value
    Given a list of one CodeRef
    When binding formats the refs with source "made_up"
    Then it raises ValueError listing the allowed sources
