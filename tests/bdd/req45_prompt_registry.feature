Feature: PromptRegistry catalog (REQ-45)

  Scenario: Registry lists all known prompts with per-entry owner/variables/location
    Given the PromptRegistry is initialized
    When I inspect the PROMPT_NAMES catalog
    Then the catalog has 4 entries total
    And every entry has owner, variables, and location fields
    And the entry "strict_tdd" has owner "flow/observability"
    And the entry "strict_tdd" declares variables ("test_command",)
    And the entry "strict_tdd" location points to an existing file
    And the entry "auto_suggest_header" has owner "flow/binding"
    And the entry "auto_suggest_header" declares variables ()
    And the entry "auto_suggest_header" location points to an existing file
    And the entry "auto_suggest_footer" has owner "flow/binding"
    And the entry "auto_suggest_footer" declares variables ()
    And the entry "auto_suggest_footer" location points to an existing file
    And the entry "auto_suggest_empty" has owner "flow/binding"
    And the entry "auto_suggest_empty" declares variables ()
    And the entry "auto_suggest_empty" location points to an existing file
    And exit code is 0

  Scenario: Registry raises KeyError on unknown prompt name
    When I call `get_prompt("does_not_exist")`
    Then a KeyError is raised with "unknown prompt 'does_not_exist'"