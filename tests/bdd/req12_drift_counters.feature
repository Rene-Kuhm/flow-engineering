Feature: drift observability counters (REQ-12)

  REQ-12 acceptance scenarios for the ``record_drift_summary`` helper in
  ``src/flow_engineering/observability.py``. The helper emits EIGHT
  ``drift_*_total`` counter events to ``~/.flow-engineering/metrics.jsonl``
  per ``flow drift <change>`` invocation:

  - ``drift_invoked_total``           — one per scan (tagged with change)
  - ``drift_still_valid_total``       — STILL_VALID bindings
  - ``drift_label_drift_total``       — LABEL_DRIFT count
  - ``drift_stale_location_total``    — STALE_LOCATION count
  - ``drift_stale_id_total``          — STALE_ID count
  - ``drift_obsolete_total``          — OBSOLETE count
  - ``drift_contradicted_total``      — CONTRADICTED count
  - ``drift_unable_to_verify_total``  — 1 when ``graph_unavailable`` else 0

  Scenario: record_drift_summary emits 8 counters per change
    Given a change with 5 findings across all classes
    When I run `flow drift <change>`
    Then ~/.flow-engineering/metrics.jsonl has 8 new lines

  Scenario: drift_still_valid_total increments when all valid
    Given a change with 0 drift findings
    When I run `flow drift <change>`
    Then drift_still_valid_total counter increments by 1

  Scenario: drift_unable_to_verify_total increments when graph unavailable
    Given graph.json missing
    When I run `flow drift <change>`
    Then drift_unable_to_verify_total counter increments by 1
