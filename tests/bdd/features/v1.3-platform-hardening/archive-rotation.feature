# REQ-V1.3.4: flow archive rotate (read-only archive rotation preview)
#
# Operator surface for the archive rotation policy. The destructive
# counterpart is deferred to ``chore/archive-rotation-2026`` per ADR-d.1;
# v1.3 ships only the read-only preview command.
#
# These 4 scenarios mirror the 4 Gherkin scenarios that REQ-V1.3.4 in
# ``openspec/changes/v1.3-platform-hardening/spec.md`` MUST satisfy.

Feature: flow archive rotate (REQ-V1.3.4)

  Scenario: help text documents all three options
    Given the operator runs "flow archive rotate --help"
    When the command completes
    Then exit code is 0
    And the output documents the "--older-than" option
    And the output documents the "--dry-run" option
    And the output documents the "--format" option

  Scenario: dry-run lists candidate archive entries as YAML by default
    Given the archive directory contains at least one entry older than 90 days
    When the operator runs "flow archive rotate --older-than 90 --dry-run"
    Then exit code is 0
    And the output is valid YAML
    And the output contains a "candidates" key
    And the "dry_run" field is true
    And the filesystem is unchanged (no entries moved or renamed)

  Scenario: --older-than filter excludes fresh entries
    Given the archive directory contains a 7-day-old entry and a 400-day-old entry
    When the operator runs "flow archive rotate --older-than 180 --dry-run --format yaml"
    Then exit code is 0
    And the output is valid YAML
    And the 400-day-old entry appears in the "candidates" list
    And the 7-day-old entry does not appear in the "candidates" list

  Scenario: read-only contract is enforced by AST contract test
    Given the production module "src/flow_engineering/cli/rotation.py" exists
    When the integration test "tests/integration/test_rotation_readonly_contract.py" runs
    Then it parses the AST of the rotation module
    And it asserts zero calls to "shutil.move"
    And it asserts zero calls to "os.rename"
    And it asserts zero calls to "Path.rename"
