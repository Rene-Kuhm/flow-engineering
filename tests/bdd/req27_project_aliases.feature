# Project aliases config (REQ-27)
#
# As a flow-engineering user I want ``flow projects alias <old> <new>``
# to record rename absorption so that federated queries transparently
# resolve ``flow-image-generator-v2`` to ``flow-image-generator-main``
# without requiring a destructive mass-backfill, AND I want a malformed
# alias file to fail fast on startup with a clear error.
#
# Notes on what the library provides today (vs spec REQ-27):
# - ``~/.config/flow-engineering/project-aliases.json`` holds a list of
#   alias records ``{old, new, created_at}`` under ``{"version": 1}``.
# - ``project_aliases.resolve(name)`` is forward-only (old → new) and
#   identity for non-aliased names.
# - ``flow projects alias <old> <new>`` is idempotent: same args ⇒ no-op
#   + confirmation; conflicting rewrite ⇒ non-zero exit (no silent
#   history loss). Atomic write via ``tempfile + Path.replace``.
# - Alias resolution is applied to every ``project`` read in
#   ``mem_search_federated`` BEFORE the SQL filter runs.

Feature: Project aliases config (REQ-27)

  # ALIAS TRANSPARENT REWRITE (1 scenario)

  Scenario: Query for flow-image-generator-v2 returns flow-image-generator-main rows when alias exists
    Given an InMemoryBackend with 1 observation tagged "flow-image-generator-v2"
    And a project-aliases config mapping "flow-image-generator-v2 -> flow-image-generator-main"
    When I run the CLI "flow search --federated --projects=flow-image-generator-v2 drift --json"
    Then the exit code is 0
    And every cli result has project "flow-image-generator-main"

  # ALIAS CLI WRITE (1 scenario)

  Scenario: flow projects alias flow-image-generator-v2 flow-image-generator-main writes the file
    Given a fresh project-aliases config does not exist
    When I append the alias "flow-image-generator-v2 -> flow-image-generator-main"
    Then the alias exit code is 0
    And the project-aliases config contains 1 record
    And the project-aliases config record maps "flow-image-generator-v2" to "flow-image-generator-main"
    And stdout contains "alias added"

  # CONFLICTING REWRITE ERRORS (1 scenario)

  Scenario: flow projects alias with a different new_key for an existing old_key errors
    Given a project-aliases config mapping "flow-image-generator-v2 -> flow-image-generator-main"
    When I append the alias "flow-image-generator-v2 -> some-other-name"
    Then the alias exit code is non-zero
    And the project-aliases config record maps "flow-image-generator-v2" to "flow-image-generator-main"

  # IDEMPOTENT RE-INVOKE (1 scenario)

  Scenario: Re-invoking flow projects alias with the same args is a no-op
    Given a project-aliases config mapping "flow-image-generator-v2 -> flow-image-generator-main"
    When I append the alias "flow-image-generator-v2 -> flow-image-generator-main"
    Then the alias exit code is 0
    And the project-aliases config contains 1 record
    And stdout contains "already present"

  # MALFORMED JSON FAILS FAST (1 scenario)

  Scenario: Alias file with malformed JSON fails fast on startup with clear error
    Given a project-aliases config exists with malformed JSON
    When I append the alias "a -> b"
    Then the alias exit code is non-zero
    And the output mentions the project-aliases file path
