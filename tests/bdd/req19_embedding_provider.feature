# EmbeddingProvider ABC + lazy import (REQ-19)
#
# As a flow-engineering user I want an EmbeddingProvider that NEVER pulls
# torch on the default install path so the package stays light, while still
# letting me swap in a real model via the [vectors] extra when I want it.
#
# Notes:
# - Scenario 1 covers the MockEmbeddingProvider contract: deterministic,
#   384-dim, L2-normalized to ~1.0.
# - Scenario 2 verifies the module-level isolation guarantee via subprocess
#   (sys.modules introspection from the same process is unreliable because
#   pytest itself may pull transitive deps).
# - Scenario 3 patches builtins.__import__ to simulate torch missing and
#   verifies SentenceTransformersProvider raises EmbeddingProviderUnavailable.
# - Scenario 4 covers the shape contract (N, 384) for both non-empty and
#   empty inputs.

Feature: EmbeddingProvider ABC + lazy import (REQ-19)

  # MOCK CONTRACT (1 scenario)

  Scenario: MockEmbeddingProvider returns deterministic 384-dim vectors
    Given a MockEmbeddingProvider
    When I embed "hello world" twice in a row
    Then both calls return identical numpy arrays
    And the array shape is (1, 384)
    And the L2 norm of the vector is within [0.99, 1.01] of 1.0
    When I embed "goodbye world"
    Then the goodbye vector differs from the hello vector

  # LAZY IMPORT (1 scenario)

  Scenario: import flow_engineering.embedding_provider does not trigger torch import
    Given a fresh subprocess
    When I import flow_engineering.embedding_provider in that subprocess
    Then "torch" is NOT in sys.modules
    And "sentence_transformers" is NOT in sys.modules
    And the SentenceTransformersProvider class is importable

  # MISSING TORCH (1 scenario)

  Scenario: SentenceTransformersProvider raises ImportError when torch missing
    Given torch is patched to raise ImportError on import
    And sentence_transformers is removed from sys.modules
    When I instantiate SentenceTransformersProvider()
    Then EmbeddingProviderUnavailable is raised
    And the embedding error message includes "pip install flow-engineering[vectors]"
    And the exception is also an ImportError

  # OUTPUT SHAPE (1 scenario)

  Scenario: Embedding output shape is (N, 384) for N inputs
    Given a MockEmbeddingProvider
    When I embed 5 texts ["a", "b", "c", "d", "e"]
    Then the returned numpy array has shape (5, 384)
    And each row has L2 norm within [0.99, 1.01] of 1.0
    When I embed an empty list
    Then the returned numpy array has shape (0, 384)