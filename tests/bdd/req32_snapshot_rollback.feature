# Snapshot rollback (REQ-32)
#
# As a flow-engineering user I want ``flow snapshot rollback`` to restore
# the live Engram state to a prior snapshot with a safety net so I can
# recover from accidental destructive edits. The command refuses without
# ``--confirm`` (REQ-32 D10 two-flag safety gate); with ``--confirm`` it
# creates an auto-safety snapshot BEFORE applying (D11); if the live
# state has diverged it refuses with a structured conflict list (D4 hard-
# fail + ``--force`` override).

Feature: Snapshot rollback (REQ-32)

  # REFUSAL WITHOUT --CONFIRM (1 scenario)

  Scenario: flow snapshot rollback <snap_id> without --confirm refuses with non-zero exit
    Given a snapshot snap_A exists with 3 observations
    When I rollback to snap_A without --confirm
    Then the rollback fails with refusal
    And the live state is unchanged
    And no safety snapshot was created

  # HAPPY PATH: --CONFIRM, NO CONFLICTS (1 scenario)

  Scenario: flow snapshot rollback <snap_id> --confirm creates safety snapshot first, restores state, exits 0
    Given a snapshot snap_A exists with 3 observations
    When I rollback to snap_A with --confirm
    Then the rollback succeeds with safety_snapshot_id and target_snapshot_id snap_A
    And the safety snapshot was created with trigger "rollback_safety"
    And the safety snapshot description starts with "pre_rollback_to_"

  # CONFLICT REFUSAL (1 scenario)

  Scenario: flow snapshot rollback <old_snap_id> --confirm with new observations added since refuses with JSON error listing new IDs
    Given a snapshot snap_old exists with 2 observations
    And 3 observations were added since snap_old
    When I rollback to snap_old with --confirm
    Then the rollback fails with conflict listing the 3 new observation IDs
    And the live state is unchanged
    And the safety snapshot was still created