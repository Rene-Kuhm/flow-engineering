# req54_skill_version_gate.feature: REQ-V1.2.3 BDD scenarios.
# Source: openspec/changes/v1.2-followups/proposal.md REQ-V1.2.3 + design D3.
Feature: `[tool.flow_engineering] min_sdd_skill_versions` enforcement (REQ-54 / REQ-V1.2.3)

  The pyproject.toml `[tool.flow_engineering]` section declares a
  project-pinned minimum-version dict for each orchestrator-dispatched
  sdd-* agent (``sdd-explore`` / ``sdd-propose`` / ``sdd-spec`` /
  ``sdd-design`` / ``sdd-tasks`` / ``sdd-apply`` / ``sdd-verify`` /
  ``sdd-archive``). The three ``flow apply`` / ``flow verify`` /
  ``flow archive`` Click commands enforce this gate at startup:
  on-disk SKILL.md files below the declared minimum trigger exit
  code 4 + a structured JSON remediation payload on stderr pointing
  at the upgrade path.

  Scenario: clean startup when all on-disk sdd-* skills meet the minimum
    Given the project pyproject.toml declares `min_sdd_skill_versions` for the 8 sdd-* agents
    And every on-disk `~/.config/opencode/skills/sdd-*/SKILL.md` carries `version: "3.0"`
    When the user runs `flow apply <change>` against the project
    Then the gate does NOT fire and the command proceeds normally
    And no `skill_version_violation` payload is written to stderr

  Scenario: blocked startup when an on-disk skill is below the declared minimum
    Given the project pyproject.toml declares `sdd-apply >= 3.0` as the minimum
    And the on-disk `~/.config/opencode/skills/sdd-apply/SKILL.md` carries `version: "2.5"`
    When the user runs `flow apply <change>` against the project
    Then the command exits with code 4
    And stderr contains a JSON object with `error=skill_version_violation`
    And the JSON payload's `skill` field equals `sdd-apply`
    And the JSON payload's `expected` field equals `3.0`
    And the JSON payload's `found` field equals `2.5`
    And the JSON payload's `hint` field references the upgrade path