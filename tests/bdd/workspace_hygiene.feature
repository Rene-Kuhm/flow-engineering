# workspace-hygiene BDD scenarios (Phase 4 of workspace-intelligence)
#
# Mirrors the structure of tests/bdd/req27_project_aliases.feature and
# tests/bdd/req30_snapshot_show.feature. The scenarios below bind to the
# REQs in openspec/changes/workspace-hygiene/specs/workspace-hygiene/spec.md.
#
# Step glue lives in tests/bdd/test_workspace_hygiene_steps.py and uses
# pytest-bdd's `scenario` decorator pattern (mirrors req_*.feature bindings).
#
# Test isolation: NO test touches C:\dev\proyects\**; all projects, registry
# files, and backup directories are created under tmp_path (tmp_path factory
# mirrors tests/unit/_workspace_fixtures.py conventions).

Feature: workspace-hygiene (Phase 4)

  # AC1 — DRY-RUN DOES NOT MUTATE FILESYSTEM (REQ-HYGIENE-DRY-RUN-DEFAULT)

  Scenario: dry-run on non-git project does not mutate filesystem
    Given a workspace root with a non-git project named "mockup" containing a file "README.md"
    When I run the CLI "flow workspace fix mockup" with no flags
    Then the exit code is 0
    And stdout reports the planned action
    And no ".git" directory exists at the project root
    And the mtime of "README.md" is unchanged
    And no registry mutation occurred

  # AC2 — MISSING --yes REFUSES (REQ-HYGIENE-DRY-RUN-DEFAULT)

  Scenario: fix without --yes refuses and mentions --yes
    Given a workspace root with a non-git project named "mockup"
    When I run the CLI "flow workspace fix mockup --backup"
    Then the exit code is non-zero
    And stderr mentions "--yes"
    And no ".git" directory exists at the project root
    And no backup was created

  # AC3 — NON-EMPTY WITHOUT --backup REFUSES (REQ-HYGIENE-BACKUP-GATE-NONEMPTY)

  Scenario: non-empty fix without --backup refuses and mentions --backup
    Given a workspace root with a non-git project named "mockup" containing a file "README.md"
    When I run the CLI "flow workspace fix mockup --yes"
    Then the exit code is non-zero
    And stderr mentions "--backup"
    And no ".git" directory exists at the project root

  # AC4 — NON-EMPTY WITH --yes + --backup SUCCEEDS (REQ-HYGIENE-FIX-SURFACE + REQ-HYGIENE-BACKUP-LAYOUT)

  Scenario: non-empty fix with --yes --backup creates .git and backup
    Given a workspace root with a non-git project named "mockup" containing a file "README.md"
    And a clean registry file
    When I run the CLI "flow workspace fix mockup --yes --backup"
    Then the exit code is 0
    And a ".git" directory exists at the project root
    And a backup directory exists at "~/.flow-engineering/backups/mockup/<UTC-ISO>/"
    And the backup manifest records project "mockup" and rule "R2"
    And the registry contains an entry for "mockup"

  # AC5 — EMPTY PROJECT WITHOUT --backup SUCCEEDS (REQ-HYGIENE-BACKUP-GATE-NONEMPTY)

  Scenario: empty fix with --yes (no --backup) creates .git and no backup
    Given a workspace root with a non-git project named "fresh" containing zero user-visible files
    When I run the CLI "flow workspace fix fresh --yes"
    Then the exit code is 0
    And a ".git" directory exists at the project root
    And no backup was created for "fresh"

  # AC6 — ARCHIVE WITH --reason (REQ-HYGIENE-ARCHIVE-SURFACE)

  Scenario: archive with --reason records the user-supplied value
    Given a workspace root with a registered project named "mockup-2-blog"
    And a clean registry file
    When I run the CLI "flow workspace archive mockup-2-blog --reason 'deprecated' --yes"
    Then the exit code is 0
    And the registry archived list contains "mockup-2-blog" with reason "deprecated"
    And "mockup-2-blog" does not appear in "flow projects ls --json" output

  # AC7 — ARCHIVE WITHOUT --reason DEFAULTS (REQ-HYGIENE-ARCHIVE-SURFACE)

  Scenario: archive without --reason defaults to "manual archive" and logs it
    Given a workspace root with a registered project named "openspec"
    And a clean registry file
    When I run the CLI "flow workspace archive openspec --yes"
    Then the exit code is 0
    And the registry archived list contains "openspec" with reason "manual archive"
    And stdout contains "archived: openspec (reason: manual archive)"

  # AC8 — ARCHIVED COMMAND OUTPUTS TEXT TABLE (REQ-HYGIENE-ARCHIVED-LISTING)

  Scenario: archived outputs a text table with three columns
    Given a registry with 2 archived projects ("mockup-2-blog" reason "deprecated", "openspec" reason "manual archive")
    When I run the CLI "flow workspace archived"
    Then the exit code is 0
    And stdout is a text table (NOT JSON)
    And stdout contains the header "NAME  ARCHIVED_AT  REASON"
    And stdout contains a row for "mockup-2-blog"
    And stdout contains a row for "openspec"

  Scenario: archived with no entries prints a clean message
    Given a registry with no archived projects
    When I run the CLI "flow workspace archived"
    Then the exit code is 0
    And stdout contains "(no archived projects)"

  # AC9 — RESTORE REVERSES ARCHIVE (REQ-HYGIENE-RESTORE-SURFACE)

  Scenario: restore reverses a prior archive
    Given a registry with project "mockup-2-blog" in archived list with reason "deprecated"
    When I run the CLI "flow workspace restore mockup-2-blog --yes"
    Then the exit code is 0
    And the registry archived list does not contain "mockup-2-blog"
    And "mockup-2-blog" reappears in "flow projects ls --json" output
    And "mockup-2-blog" does not appear in "flow workspace archived" output

  Scenario: restore refuses without --yes
    Given a registry with project "mockup-2-blog" in archived list
    When I run the CLI "flow workspace restore mockup-2-blog"
    Then the exit code is non-zero
    And stderr mentions "--yes"
    And the registry archived list is unchanged

  # AC10 — AC9 BYTE-IDENTICAL PRESERVED FOR NON-TARGETS (REQ-HYGIENE-AC9-PRESERVATION)

  Scenario: workspace-hygiene commands preserve flow projects ls --json bytes for non-targets
    Given a workspace root with projects "project-a" (target) and "project-b" (non-target)
    And the captured bytes of "flow projects ls --json" for "project-b"
    When I run the CLI "flow workspace archive project-a --yes"
    Then the exit code is 0
    And the bytes of "flow projects ls --json" for "project-b" are byte-identical to the captured bytes

  # AC11 — POLLUTION-PROTOCOL RESTORE ON VERIFY FAILURE (REQ-HYGIENE-POLLUTION-PROTOCOL)

  Scenario: post-mutation verify failure triggers restore from snapshot
    Given a workspace root with a non-git project named "mockup" containing a file "README.md"
    And the post-mutation verifier is monkeypatched to return False
    When I run the CLI "flow workspace fix mockup --yes --backup"
    Then the exit code is 2
    And the project state is restored from the pre-mutation snapshot
    And stderr contains "verify failed"

  # AC12 — REGISTRY ATOMIC WRITE (REQ-HYGIENE-REGISTRY-V1)

  Scenario: registry write is atomic on interruption
    Given a registry file does not exist
    When the registry write is interrupted during os.replace (simulated)
    Then no partial "registry.json" exists on disk
    And the prior registry content (if any) is still readable

  Scenario: read-only consumers do not create the registry
    Given a registry file does not exist
    When I run the CLI "flow projects ls --json"
    Then the exit code is 0
    And the registry file still does not exist

  # AC13 — R1 dirty-git IS OUT OF SCOPE (REQ-HYGIENE-R1-EXPLICITLY-OUT)

  Scenario: fix on a dirty-git project does not remediate the dirty state
    Given a workspace root with a git project containing an uncommitted file "WIP.md"
    When I run the CLI "flow workspace fix <project>" with any flags
    Then the exit code is 0
    And the file "WIP.md" is still present
    And the project's working tree is unchanged
    And the project's git index is unchanged
    And the project's untracked files are unchanged
    And no worktree manipulation has occurred
    And stdout contains "R1 dirty-git is OUT OF SCOPE for Phase 4 MVP"
