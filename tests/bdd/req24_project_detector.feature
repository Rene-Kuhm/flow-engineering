# Project detector + backfill CLI (REQ-24)
#
# As a flow-engineering user I want sub-projects under ~/dev/proyects/
# (or ~/proyects/) to auto-resolve to their canonical project key so that
# new observations tag themselves correctly, AND I want a safe
# ``flow projects backfill`` CLI to re-tag historical observations without
# ever silently writing to the corpus.
#
# Notes on what the library provides today (vs spec REQ-24):
# - ``project_detector.detect(cwd)`` returns the project name for a cwd
#   under a recognised layout (deepest-match), or ``None`` when no match
#   is found (NOT a silent ``"insyd"`` fallback). Layout 1 is
#   ``*/dev/proyects/<name>/...``; Layout 2 is ``<home>/proyects/<name>/``.
# - The CLI exposes ``flow projects backfill [--dry-run|--confirm]
#   [--project=<key>]`` with a STRICT safety gate: ``--dry-run`` is the
#   default (no writes, JSON report); ``--confirm`` is REQUIRED to write;
#   ``--confirm`` without ``--project=<key>`` REFUSES with a non-zero
#   exit because the scope is ambiguous (multiple projects could match).

Feature: Project detector + backfill CLI (REQ-24)

  Scenario: detect returns the project name when cwd is under dev/proyects
    Given a project_detector with cwd "/c/dev/proyects/flow-engineering"
    When I call detect() with that cwd
    Then the returned project is "flow-engineering"

  Scenario: detect returns None when cwd is not under a projects dir
    Given a project_detector with cwd "/c/Users/insyd/Downloads"
    When I call detect() with that cwd
    Then the returned project is None

  Scenario: flow projects backfill with no flags defaults to dry-run
    Given an InMemoryBackend with 1 untagged observation
    When I run the flow projects backfill CLI with no flags
    Then the exit code is 0
    And the observation is still untagged

  Scenario: flow projects backfill --confirm --project=<key> writes tags
    Given an InMemoryBackend with 1 untagged observation
    When I run the CLI "flow projects backfill --confirm --project=flow-engineering"
    Then the exit code is 0
    And the observation is tagged with "flow-engineering"

  Scenario: flow projects backfill --confirm without --project iterates the alias map (REQ-27 integration)
    Given an InMemoryBackend with 1 observation tagged "flow-image-generator-v2"
    And a project-aliases config mapping "flow-image-generator-v2 -> flow-image-generator-main"
    When I run the CLI "flow projects backfill --confirm"
    Then the exit code is 0
    And the observation is tagged with "flow-image-generator-main"

  Scenario: flow projects backfill --dry-run emits a JSON report to stdout
    Given an InMemoryBackend with 1 observation tagged "flow-image-generator-v2"
    And a project-aliases config mapping "flow-image-generator-v2 -> flow-image-generator-main"
    When I run the CLI "flow projects backfill --dry-run"
    Then the exit code is 0
    And stdout is valid JSON
    And the JSON report mentions the observation id
