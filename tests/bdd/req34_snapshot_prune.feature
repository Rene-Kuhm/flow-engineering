# Snapshot retention pruning (REQ-34)
#
# As a flow-engineering user I want ``flow snapshot prune`` to evict
# old snapshot files under a retention policy (count, age, OR total size)
# so the snapshots directory does not grow without bound. The command is
# DRY-RUN by default (no --confirm ⇒ no files deleted) and prints the
# candidate list as "would delete" so I can preview the impact before
# committing. The two safety invariants (REQ-34 D10) are non-negotiable:
# the most-recent snapshot is never deleted (unless --force), and
# pinned snapshots are never deleted (no override).

Feature: Snapshot retention pruning (REQ-34)

  # KEEP-LAST EVICTION (1 scenario)

  Scenario: Prune with --keep-last evicts oldest beyond N
    Given 5 snapshots exist with timestamps spanning 5 days
    And the 3 oldest are NOT pinned and NOT the most recent
    When I run flow snapshot prune with --keep-last 2 and --confirm
    Then exactly 3 snapshot files are removed
    And the remaining 2 are the 2 most recent

  # DRY-RUN BY DEFAULT (1 scenario)

  Scenario: Prune without --confirm is dry-run
    Given 5 snapshots exist
    When I run flow snapshot prune with --keep-last 2 (no --confirm)
    Then no snapshot files are removed
    And the prune output lists 3 "would delete" ids
    And the prune command exit code is 0