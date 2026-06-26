# Reindex command (REQ-21)
#
# As a flow-engineering user I want a sync streaming ``flow reindex`` subcommand
# that rebuilds the sqlite-vec store from the Engram corpus so that I can recover
# after a crash, change the embedding model, or bootstrap a fresh machine.
#
# Notes on what the library provides today:
# - One stderr line per completed batch in the form ``reindex: N/M (P%) embedded``.
# - Done line on stderr in the form ``reindex: done — K observations indexed in T seconds``.
# - Idempotent via ``INSERT OR REPLACE`` on the audit table (REQ-20 T1.6) — a
#   second ``flow reindex`` re-uses the existing rows, so the index size does
#   not grow.
# - ``--dry-run`` short-circuits with a count-only line; the vectors.sqlite
#   file is NOT touched.
# - Crash-resume: per-batch transactions mean a fresh ``flow reindex`` call
#   picks up where the previous run stopped.
#
# The BDD layer mirrors batch E's pattern (per-scenario ``vec_reindex_world``
# fixture that wires the InMemoryBackend + monkeypatched CLI helpers + tmp-path
# metrics + tmp-path SqliteVecStore). The ``--semantic`` flag and the
# ``flow search`` CLI surface are covered by req17_semantic_search.feature.

Feature: Reindex command (REQ-21)

  # EMPTY CORPUS (1 scenario)

  Scenario: flow reindex on empty corpus completes with 0 indexed
    Given an empty InMemoryBackend
    And the [vectors] extra is available
    And a tmp-path SqliteVecStore
    When I run flow reindex
    Then the exit code is 0
    And the output contains "reindex: done — 0 observations indexed"

  # BATCHED PROGRESS (1 scenario)

  Scenario: flow reindex on 250 observations emits progress lines + done
    Given an InMemoryBackend seeded with 250 observations
    And the [vectors] extra is available
    And a tmp-path SqliteVecStore
    When I run flow reindex --batch-size 100
    Then the exit code is 0
    And the output contains "reindex: 100/250 (40%) embedded"
    And the output contains "reindex: 200/250 (80%) embedded"
    And the output contains "reindex: 250/250 (100%) embedded"
    And the output contains "reindex: done — 250 observations indexed"

  # IDEMPOTENT RE-RUN (1 scenario)

  Scenario: Second flow reindex is idempotent
    Given an InMemoryBackend seeded with 100 observations
    And the [vectors] extra is available
    And a tmp-path SqliteVecStore
    When I run flow reindex
    And I run flow reindex again
    Then the exit code is 0
    And the vector_index_size_observations gauge reads 100
    And the output contains "reindex: done — 100 observations indexed"

  # DRY-RUN (1 scenario)

  Scenario: --dry-run reports count without writing
    Given an InMemoryBackend seeded with 50 observations
    And the [vectors] extra is available
    And a tmp-path SqliteVecStore
    When I run flow reindex --dry-run
    Then the exit code is 0
    And the output contains "50 observations need reindex"
    And the vector_index_size_observations gauge reads 0

  # CRASH-RESUME (1 scenario)

  Scenario: Crash mid-run: subsequent restart completes the corpus
    Given an InMemoryBackend seeded with 250 observations
    And the [vectors] extra is available
    And a tmp-path SqliteVecStore
    And a simulated reindex crash after 100 of the first batch
    When I run flow reindex --batch-size 100 (first run, partial)
    And I run flow reindex --batch-size 100 (second run, full)
    Then the exit code is 0
    And the vector_index_size_observations gauge reads 250
    And the second output contains "reindex: done — 250 observations indexed"