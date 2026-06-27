Feature: render_prompt helper (REQ-46)

  Scenario: render with no kwargs returns the template as-is
    Given the prompt "no_kwargs_example" exists with template "Hello, world!"
    When I call `render_prompt("no_kwargs_example")`
    Then the result equals "Hello, world!"

  Scenario: render with kwargs substitutes Jinja2 placeholders
    Given the prompt "with_kwargs_example" exists with template "Hello, {{ user_name }}!"
    When I call `render_prompt("with_kwargs_example", user_name="World")`
    Then the result equals "Hello, World!"

  Scenario: render with missing kwargs raises UndefinedError
    Given the prompt "needs_name" exists with template "Hello, {{ user_name }}!"
    When I call `render_prompt("needs_name")`
    Then an UndefinedError is raised mentioning "user_name"