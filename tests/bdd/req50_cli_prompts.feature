Feature: flow prompts CLI (REQ-50)

  Scenario: `flow prompts list` shows all registered prompts grouped by domain
    Given PROMPT_REGISTRY has 4 entries (1 flow/observability, 3 flow/binding)
    When the user runs `flow prompts list`
    Then stdout contains a header line `prompt_id`
    And stdout contains a row for `strict_tdd` with version="1.0.0" and owner="flow/observability"
    And stdout contains a row for `auto_suggest_header` with version="1.0.0" and owner="flow/binding"
    And stdout contains a row for `auto_suggest_footer` with version="1.0.0" and owner="flow/binding"
    And stdout contains a row for `auto_suggest_empty` with version="1.0.0" and owner="flow/binding"
    And stdout contains a footer line `4 prompt entries`
    And the command exits 0

  Scenario: `flow prompts show <name>` renders the prompt with kwargs
    Given PROMPT_REGISTRY has an entry `strict_tdd` with variables=("test_command",)
    When the user runs `flow prompts show strict_tdd --var test_command=pytest`
    Then stdout contains a `prompt_id:` line with `strict_tdd`
    And stdout contains a `version:` line with `1.0.0`
    And stdout contains a `variables:` line with `test_command: pytest`
    And stdout contains the rendered string `STRICT TDD MODE IS ACTIVE. Test runner: pytest. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode.`
    And stdout contains a footer line `autoescape`
    And the command exits 0

  Scenario: `flow prompts show <unknown>` exits with code 5 and JSON error on stderr
    Given the user provides an unknown prompt id `no_such_prompt_xyz`
    When the user runs `flow prompts show no_such_prompt_xyz`
    Then the command exits 5
    And stderr contains a JSON error object with key `error` equal to `unknown prompt id`
    And stderr contains the prompt_id `no_such_prompt_xyz`