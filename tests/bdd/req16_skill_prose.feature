Feature: SKILL.md Drift detection hook (REQ-16)

  REQ-16 acceptance scenarios for the drift-detection hook prose that
  the sdd-{propose,design,tasks,apply,verify,archive} SKILL.md files
  must carry. The hook is the runtime gate the sdd-verify phase uses
  to assert that a change's drift layer is "still valid" before declaring
  the cycle green (per the drift-hardening proposal #223 §3.4 and the
  observability change #6 SKILL.md precedent).

  Scenario: sdd-verify Step 6a runs `flow drift` before declaring green
    Given a change with 0 drift findings
    When I run the sdd-verify Step 6a protocol
    Then exit code is 0

  Scenario: all 6 SKILL.md files carry `## Drift detection hook` section
    When I grep `## Drift detection hook` across sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md
    Then 6 files have the section
