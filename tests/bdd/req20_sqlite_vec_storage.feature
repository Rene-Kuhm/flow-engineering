# sqlite-vec storage (REQ-20)
#
# As a flow-engineering user I want vector embeddings persisted in sqlite-vec
# so that semantic search can scale beyond in-memory limits and survive process
# restarts.
#
# Contract:
# - ``SqliteVecStore`` exposes ``add(obs_id, vector)``, ``search(vector, k)``,
#   ``delete(obs_id)``, and ``count()``.
# - Vectors are 384-dim float32; the audit BLOB is exactly 1536 bytes.
# - Writes are transactional; a failure rolls back the entire batch.
# - ``delete`` removes both the vec0 row AND the audit row atomically.

Feature: sqlite-vec storage (REQ-20)

  # ROUND-TRIP (1 scenario)

  Scenario: Add -> search round-trip returns added observation as top-1
    Given a fresh SqliteVecStore (in-memory)
    When I add obs1 with a unit vector
    And I search with the same unit vector, k=1
    Then the result is obs1 at distance ~0.0

  # DELETE (1 scenario)

  Scenario: Delete removes observation from search results
    Given a SqliteVecStore with obs1 and obs2 added
    When I delete obs1
    And I search with any vector, k=10
    Then obs1 is NOT in the result list
    And obs2 IS in the result list
    And count() == 1

  # COUNT (1 scenario)

  Scenario: count() reflects add/delete accurately
    Given a fresh SqliteVecStore (in-memory)
    When I call count() before any writes
    Then it returns 0
    When I add obs1, obs2, and obs3 with three distinct unit vectors
    Then count() returns 3
    When I delete obs2
    Then count() returns 2

  # BLOB SIZE (1 scenario)

  Scenario: Vector BLOB size matches 384 x 4 = 1536 bytes
    Given a fresh SqliteVecStore (in-memory)
    When I add obs1 with a random 384-dim vector
    And I read the observation_embeddings.vector column as raw bytes
    Then the byte length is exactly 1536
    And the deserialized numpy array has shape (384,) and dtype float32
    And the values round-trip within 1e-6 of the input

  # TOP-K ORDERING (1 scenario)

  Scenario: Search returns top-k ordered by ascending distance
    Given a SqliteVecStore with 10 random 384-dim vectors at obs1..obs10
    And a query vector chosen close to obs7 (cosine distance ~ 0.05)
    When I search with the query vector, k=3
    Then the result list has exactly 3 (obs_id, distance) tuples
    And obs7 is at position 0
    And the distances are sorted in ascending order