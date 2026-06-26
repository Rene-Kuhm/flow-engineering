Feature: one-time backfill appends code_refs blocks to legacy observations
  REQ-4: dry-run by default; --apply mutates; preserves prose byte-for-byte;
  preserves created_at; advances updated_at; idempotent across re-runs.

  Background:
    Given an in-memory Engram backend with two prose-only observations

  Scenario: Dry-run reports counts without writing
    When the backfill script runs in dry-run mode
    Then the result reports would_change = 2 and applied = 0
    And no observation gained a code_refs block

  Scenario: Apply appends block without altering prose
    Given an observation whose prose is 800 characters long
    When the backfill script runs in apply mode
    Then the observation gained a code_refs block
    And the first 800 characters of the saved content equal the original prose

  Scenario: Re-running apply is idempotent
    Given a previous apply run wrote a backfill block to the observations
    When the backfill script runs in apply mode again
    Then the result reports applied = 0
    And no observation is rewritten

  Scenario: Apply writes a pre-image JSONL record
    When the backfill script runs in apply mode
    Then a backfill-preimage.jsonl file exists
    And it contains one entry per mutated observation
    And each entry records the original content under "before"
