<!-- req49_skill_catalog.feature: REQ-49 BDD scenarios.
     Source: openspec/changes/archive/2026-06-27-prompt-registry-pr1/spec.md
     "REQ-49 Scenario S1 + S2" verbatim.
-->
Feature: OpenCode SKILL.md mirror catalog + checksum drift detection (REQ-49)

  The system SHALL detect drift between on-disk SKILL.md frontmatter
  SHA-256 checksums and the catalog's ``last_verified_checksum``. The
  drift check is exposed via ``check_drift(catalog)`` which returns a
  list of ``SkillDrift`` findings (empty list = clean state).

  Scenario: check-drift detects when SKILL.md checksums don't match catalog
    Given a SKILL_CATALOG with 20 entries (10 skills + 10 prompts)
    And a sidecar prompt_checksums.json recording stale checksums (e.g., sdd-apply last_verified=abc123)
    And the on-disk ~/.config/opencode/skills/sdd-apply/SKILL.md has been edited since last verification (current frontmatter checksum=def456)
    When the user calls check_drift(SKILL_CATALOG)
    Then the result is a list with at least 1 SkillDrift entry
    And the drift entry has skill_name=sdd-apply and drift_kind=checksum_mismatch
    And the drift entry's expected_checksum equals the stale value (abc123)
    And the drift entry's on_disk_checksum equals the current value (def456)
    And the function does NOT raise; it returns the list for the caller (CLI) to surface

  Scenario: check-drift passes when all SKILL.md checksums match
    Given a SKILL_CATALOG with 20 entries (10 skills + 10 prompts)
    And a freshly updated sidecar prompt_checksums.json where every entry's checksum matches the current on-disk frontmatter
    When the user calls check_drift(SKILL_CATALOG)
    Then the result is an empty list
    And no SkillDrift entries are returned
    And the function completes in under 1 second for the 20-entry catalog
    And the function does NOT raise; the empty list is the "clean state" signal