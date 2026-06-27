Feature: PromptRegistry catalog (REQ-45)

  Scenario: Registry lists all known prompts by domain
    Given the PromptRegistry is initialized
    When I run `python -c "from flow_engineering.prompt_registry import list_prompts; print(len(list_prompts()))"`
    Then stdout contains a number >= 4
    And exit code is 0

  Scenario: Registry raises KeyError on unknown prompt name
    When I call `get_prompt("does_not_exist")`
    Then a KeyError is raised with "unknown prompt 'does_not_exist'"