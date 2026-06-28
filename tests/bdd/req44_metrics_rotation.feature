Feature: metrics.jsonl rotation (REQ-44 / REQ-V1.2.1)

  The metrics JSONL sink at ``~/.flow-engineering/metrics.jsonl`` grows
  unbounded by default (every CLI invocation appends at least one line).
  REQ-V1.2.1 mirrors the DriftEventLog rotation pattern
  (``drift_event_log.py:220-254``): when the active file exceeds
  ``FLOW_METRICS_LOG_MAX_BYTES`` (default 10 MB) the active file is
  renamed to ``metrics.<ISO-no-colons>.jsonl`` and a fresh active file
  is created on the next append. Sibling files older than
  ``FLOW_METRICS_LOG_MAX_AGE_DAYS`` (default 30) are deleted
  best-effort.

  Scenario: metrics.jsonl rotates at the configured size threshold
    Given the metrics sink lives at a tmp_path with a 1 KB rotation threshold
    When the user appends 20 counter events with payload larger than the threshold
    Then a rotated sibling ``metrics.*.jsonl`` exists in the same directory
    And the active ``metrics.jsonl`` is fresh and contains the most recent events
    And no half-written data is observed in the rotated sibling

  Scenario: metrics.jsonl rotation is best-effort and never raises
    Given the metrics sink has a small rotation threshold and the FS rename fails
    When the user appends 5 counter events
    Then increment returns None and does not raise
    And the active file still contains the appended events
