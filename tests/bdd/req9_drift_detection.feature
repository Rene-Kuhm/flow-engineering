Feature: Decision ↔ code drift detection (REQ-9)

  As a flow-engineering user
  I want to detect when saved decisions no longer match current code reality
  So that stale decisions surface for review

  Background:
    Given a change "auth-refactor" with observations
    And a graph.json file

  # STILL_VALID (2 scenarios)

  Scenario: Binding resolves to same file:line with same label
    Given an observation with binding {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    And the graph shows node {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    When I run flow drift on change "auth-refactor"
    Then the exit code is 0
    And the report contains 1 findings with class STILL_VALID

  Scenario: Binding is source-agnostic (manual vs auto_suggest)
    Given an observation with binding {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 42, "source": "backfill", "confidence": 0.3}
    And the graph shows node {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    When I run flow drift on change "auth-refactor"
    Then the report contains 1 findings with class STILL_VALID

  # LABEL_DRIFT (2 scenarios)

  Scenario: Symbol renamed but file:line preserved
    Given an observation with binding {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    And the graph shows node {"id": "node_jwt", "label": "validate_jwt_token", "file": "auth/jwt.py", "line": 42}
    When I run flow drift on change "auth-refactor"
    Then the exit code is 1
    And the report contains 1 findings with class LABEL_DRIFT

  Scenario: Case-only label change is detected as LABEL_DRIFT
    Given an observation with binding {"id": "node_jwt", "label": "jwt_validator", "file": "auth/jwt.py", "line": 42}
    And the graph shows node {"id": "node_jwt", "label": "JWT_validator", "file": "auth/jwt.py", "line": 42}
    When I run flow drift on change "auth-refactor"
    Then the exit code is 1
    And the report contains 1 findings with class LABEL_DRIFT

  # STALE_LOCATION (2 scenarios)

  Scenario: Symbol moved to different file
    Given an observation with binding {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    And the graph shows node {"id": "node_jwt", "label": "JWT validator", "file": "auth/session.py", "line": 42}
    When I run flow drift on change "auth-refactor"
    Then the exit code is 1
    And the report contains 1 findings with class STALE_LOCATION

  Scenario: Symbol line shifted in same file
    Given an observation with binding {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    And the graph shows node {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 87}
    When I run flow drift on change "auth-refactor"
    Then the exit code is 1
    And the report contains 1 findings with class STALE_LOCATION

  # STALE_ID (2 scenarios)

  Scenario: Symbol id not in current graph
    Given an observation with binding {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    And the graph shows node {"id": "other_node", "label": "Other", "file": "src/other.py", "line": 1}
    When I run flow drift on change "auth-refactor"
    Then the exit code is 1
    And the report contains 1 findings with class STALE_ID

  Scenario: Symbol renamed without alias
    Given an observation with binding {"id": "old_node", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    And the graph shows node {"id": "new_node", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    When I run flow drift on change "auth-refactor"
    Then the exit code is 1
    And the report contains 1 findings with class STALE_ID

  # OBSOLETE (2 scenarios) — note: requires --include-obsolete flag

  Scenario: Decision without bindings + zero candidates yields OBSOLETE with flag
    Given an observation with empty bindings
    And graphify returns 0 candidates
    When I run flow drift on change "auth-refactor" with --include-obsolete
    Then the exit code is 1
    And the report contains 1 findings with class OBSOLETE

  Scenario: Decision without bindings is SKIPPED without flag (default off)
    Given an observation with empty bindings
    And graphify returns 0 candidates
    When I run flow drift on change "auth-refactor"
    Then the report contains 0 findings

  # CONTRADICTED (2 scenarios)

  Scenario: Two observations same id with confidence_gap > 0.4 yield CONTRADICTED
    Given an observation with binding {"id": "shared", "label": "X", "file": "a.py", "line": 1, "confidence": 0.9, "source": "manual"}
    And an observation with binding {"id": "shared", "label": "X", "file": "a.py", "line": 1, "confidence": 0.4, "source": "auto_suggest"}
    And the graph shows node {"id": "shared", "label": "X", "file": "a.py", "line": 1}
    When I run flow drift on change "auth-refactor"
    Then both observations report class CONTRADICTED

  Scenario: Two observations same id with confidence_gap <= 0.4 yield no CONTRADICTED finding
    Given an observation with binding {"id": "shared", "label": "X", "file": "a.py", "line": 1, "confidence": 0.9, "source": "manual"}
    And an observation with binding {"id": "shared", "label": "X", "file": "a.py", "line": 1, "confidence": 0.7, "source": "manual"}
    And the graph shows node {"id": "shared", "label": "X", "file": "a.py", "line": 1}
    When I run flow drift on change "auth-refactor"
    Then no finding has class CONTRADICTED

  # UNABLE_TO_VERIFY (2 scenarios) — terminal state

  Scenario: graph.json missing yields UNABLE_TO_VERIFY, exit code 2
    Given the graph.json file is absent
    And an observation with binding {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    When I run flow drift on change "auth-refactor"
    Then the exit code is 2

  Scenario: graph.json malformed yields UNABLE_TO_VERIFY, exit code 2
    Given the graph.json file is malformed
    And an observation with binding {"id": "node_jwt", "label": "JWT validator", "file": "auth/jwt.py", "line": 42}
    When I run flow drift on change "auth-refactor"
    Then the exit code is 2