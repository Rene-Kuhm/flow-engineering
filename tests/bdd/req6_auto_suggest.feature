Feature: save-time auto-suggestion
  REQ-6 (PR#2 batch 1): when `mem_save` is called without an explicit
  `code_refs` block, the system MUST consult `graphify query` and surface
  candidates whose confidence meets or exceeds the threshold (default 0.3).
  Three confirmation channels: (a) interactive prompt when TTY,
  (b) `--with-suggest` CLI flag (non-interactive accept-all), (c)
  `FLOW_AUTO_SUGGEST=1` env var. The suggester MUST fail-open: graphify
  errors yield `source: unbound` and the save proceeds without bindings.

  Background:
    Given the metrics sink points at a tmp file
    And an in-memory Engram backend and a client for change "my-change"

  Scenario: Auto-suggest surfaces chosen candidates after user confirmation
    Given graphify returns two candidates with confidence 0.6 and 0.4
    And the user confirms all candidates interactively
    When save_phase is called for "propose" with with_suggest and is_tty
    Then the persisted block source is "auto_suggest"
    And the persisted block contains two CodeRefs
    And the suggest_hit_total counter incremented by 1
    And the bindings_confirmed_total counter recorded 2 confirmed bindings

  Scenario: Threshold filter keeps only candidates at or above 0.3
    Given graphify returns three candidates with confidence 0.6, 0.4, and 0.2
    When save_phase is called for "propose" with with_suggest and threshold 0.3
    Then the persisted block contains two CodeRefs
    And the persisted block contains no candidate with confidence below 0.3

  Scenario: Graphify unavailable - save proceeds with unbound
    Given graphify is unavailable and returns an empty list
    When save_phase is called for "propose" with with_suggest
    Then the persisted block source is "unbound"
    And the suggest_miss_total counter incremented by 1

  Scenario: --with-suggest CLI flag works in non-TTY
    Given graphify returns one candidate with confidence 0.7
    When the flow save command is invoked with --with-suggest
    Then the persisted block source is "auto_suggest"
    And the persisted block contains the candidate

  Scenario: User rejection - save proceeds without code_refs
    Given graphify returns two candidates with confidence 0.6 and 0.4
    And the user rejects all candidates interactively
    When save_phase is called for "propose" with is_tty
    Then the persisted block source is "unbound"
    And the suggest_miss_total counter incremented by 1