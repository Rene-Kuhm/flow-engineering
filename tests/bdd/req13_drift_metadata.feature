Feature: update_observation_metadata helper (REQ-13)

  REQ-13 acceptance scenarios for the
  ``EngramClient.update_observation_metadata`` helper. The helper appends
  a trailing ``<!-- metadata -->`` block to an observation's content
  with key/value pairs (e.g. ``last_verified_at``, ``last_drift_class``).
  New keys win on conflict (idempotent overwrite); existing keys are
  preserved. The ``code_refs`` block stays byte-identical.

  Scenario: append metadata to observation
    Given observation id=1 with metadata {existing_key: existing_value}
    When I call `update_observation_metadata(1, new_key, new_value)`
    Then observation metadata has both keys

  Scenario: idempotent metadata update (no duplicates)
    Given observation id=1 with metadata {existing_key: existing_value}
    When I call `update_observation_metadata(1, key, value)` twice
    Then metadata has only one entry for key

  Scenario: structured error on missing observation
    When I call `update_observation_metadata(999999, key, value)`
    Then a structured error is raised with code OBSERVATION_NOT_FOUND
