Feature: lint_prompts validator (REQ-47)

  Scenario: lint passes for well-formed prompt catalog
    When I call `lint_prompts()`
    Then the result is_clean is True

  Scenario: lint fails for prompt with undefined placeholder variable
    Given I register a broken prompt with template "Hello, {{ undefined }}!" and no metadata.required_vars
    When I call `lint_prompts()`
    Then the result error_count > 0
    And one error has error_code="undefined_var"