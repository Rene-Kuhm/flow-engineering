"""Unit tests for the 3 federated_* observability counters (REQ-26).

REQ-26 + design D4: 3 new counters land in observability.py:
- ``federated_search_invoked_total`` — counter with ``trigger`` tag (cli|programmatic)
- ``federated_search_projects_queried`` — histogram (per-call ``count=N``)
- ``federated_search_results_returned_total`` — counter, sum of result-list lengths

The naming follows the REQ-8 convention (``_total`` suffix for counters) EXCEPT
for ``federated_search_projects_queried`` which is a histogram per call (D4):
the value IS the count, so a ``_total`` suffix would be redundant.

The helper ``record_federated_summary(...)`` emits exactly 3 JSONL events
in a single call (parallels ``record_vector_summary`` from REQ-22 +
``record_drift_summary`` from REQ-12).

Integration with ``InMemoryBackend.mem_search_federated`` lands as part of
this task so BDD scenarios that seed an InMemoryBackend observe the counter
batch fire on every call. ``HybridBackend.mem_search_federated`` (added in
the same batch) forwards to the inner backend and re-emits with the same
counts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from flow_engineering import observability
from flow_engineering.engram_io import InMemoryBackend

# ---------- helpers ----------


def _read_metrics(metrics_path: Path) -> list[dict]:
    """Parse the JSONL metrics file into a list of dicts (skips malformed lines)."""
    if not metrics_path.exists():
        return []
    events: list[dict] = []
    for line in metrics_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _events_for(events: list[dict], name: str) -> list[dict]:
    return [e for e in events if e.get("name") == name]


def _sum_count(events: list[dict]) -> int:
    return sum(int(e.get("fields", {}).get("count", 0)) for e in events)


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


# ---------- REQ-26 scenario 4: counter catalog ----------


class TestFederatedCounterNaming:
    """REQ-26 scenario 4: 3 counters are first-class names + catalog list."""

    def test_three_federated_counter_names_defined(self) -> None:
        names = observability.FEDERATED_COUNTER_NAMES
        assert isinstance(names, list)
        assert len(names) == 3
        assert "federated_search_invoked_total" in names
        assert "federated_search_projects_queried" in names
        assert "federated_search_results_returned_total" in names

    def test_counter_names_subject_event_total_pattern(self) -> None:
        # REQ-8: ``_total`` suffix required for counters (verb-style events).
        counters = [
            "federated_search_invoked_total",
            "federated_search_results_returned_total",
        ]
        for c in counters:
            assert c.endswith("_total"), (
                f"Counter {c} does not match REQ-8 ``_total`` suffix convention"
            )

    def test_histogram_name_has_no_total_suffix(self) -> None:
        # D4: ``federated_search_projects_queried`` is a histogram (count per
        # call). The value IS the count, so ``_total`` would be redundant.
        assert "federated_search_projects_queried" in observability.FEDERATED_COUNTER_NAMES
        # The actual histogram name must NOT have a ``_total`` suffix.
        assert not "federated_search_projects_queried".endswith("_total")


# ---------- REQ-26: record_federated_summary helper ----------


class TestRecordFederatedSummary:
    """``record_federated_summary`` emits 3 JSONL events in a single call."""

    def test_emits_three_events_with_correct_fields(
        self, metrics_path: Path
    ) -> None:
        observability.record_federated_summary(
            invoked=1,
            projects_queried=3,
            results_returned=5,
            trigger="cli",
        )
        events = _read_metrics(metrics_path)
        # 3 counters — one event each.
        assert len(events) == 3
        names = [e["name"] for e in events]
        assert "federated_search_invoked_total" in names
        assert "federated_search_projects_queried" in names
        assert "federated_search_results_returned_total" in names

    def test_invoked_event_has_trigger_field(
        self, metrics_path: Path
    ) -> None:
        observability.record_federated_summary(
            invoked=1,
            projects_queried=2,
            results_returned=1,
            trigger="programmatic",
        )
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_invoked_total"
        )
        assert len(events) == 1
        assert events[0]["fields"]["trigger"] == "programmatic"
        assert events[0]["fields"]["count"] == 1

    def test_projects_queried_event_records_count(
        self, metrics_path: Path
    ) -> None:
        observability.record_federated_summary(
            invoked=1, projects_queried=3, results_returned=0
        )
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_projects_queried"
        )
        assert len(events) == 1
        assert events[0]["fields"]["count"] == 3

    def test_results_returned_event_records_count(
        self, metrics_path: Path
    ) -> None:
        observability.record_federated_summary(
            invoked=1, projects_queried=2, results_returned=7
        )
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_results_returned_total"
        )
        assert len(events) == 1
        assert events[0]["fields"]["count"] == 7

    def test_results_returned_cumulative_across_calls(
        self, metrics_path: Path
    ) -> None:
        # Scenario 3: a second call returning 3 rows increments the counter by another 3.
        observability.record_federated_summary(
            invoked=1, projects_queried=2, results_returned=5
        )
        observability.record_federated_summary(
            invoked=1, projects_queried=2, results_returned=3
        )
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_results_returned_total"
        )
        total = _sum_count(events)
        assert total == 8

    def test_projects_queried_histogram_records_each_bucket(
        self, metrics_path: Path
    ) -> None:
        # Scenario 2: histogram of project-bucket sizes — each call adds one event.
        observability.record_federated_summary(
            invoked=1, projects_queried=1, results_returned=0
        )
        observability.record_federated_summary(
            invoked=1, projects_queried=3, results_returned=0
        )
        observability.record_federated_summary(
            invoked=1, projects_queried=4, results_returned=0
        )
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_projects_queried"
        )
        buckets = [e["fields"]["count"] for e in events]
        assert buckets == [1, 3, 4]

    def test_invoked_cumulative_across_calls(
        self, metrics_path: Path
    ) -> None:
        # Scenario 1: invoked counter increments by 1 per call.
        observability.record_federated_summary(
            invoked=1, projects_queried=1, results_returned=0
        )
        observability.record_federated_summary(
            invoked=1, projects_queried=1, results_returned=0
        )
        observability.record_federated_summary(
            invoked=1, projects_queried=1, results_returned=0
        )
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_invoked_total"
        )
        total = _sum_count(events)
        assert total == 3

    def test_default_trigger_is_programmatic(self, metrics_path: Path) -> None:
        observability.record_federated_summary(
            invoked=1, projects_queried=1, results_returned=0
        )
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_invoked_total"
        )
        assert events[0]["fields"]["trigger"] == "programmatic"

    def test_invalid_trigger_falls_back_to_programmatic(
        self, metrics_path: Path
    ) -> None:
        observability.record_federated_summary(
            invoked=1,
            projects_queried=1,
            results_returned=0,
            trigger="background",  # not in {cli, programmatic}
        )
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_invoked_total"
        )
        assert events[0]["fields"]["trigger"] == "programmatic"

    def test_projects_queried_none_normalized_to_zero(
        self, metrics_path: Path
    ) -> None:
        # Search-all case: ``projects=None`` ⇒ ``count=0`` for the histogram bucket.
        observability.record_federated_summary(
            invoked=1,
            projects_queried=None,  # type: ignore[arg-type]
            results_returned=0,
        )
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_projects_queried"
        )
        assert events[0]["fields"]["count"] == 0

    def test_negative_inputs_clamped_to_zero(
        self, metrics_path: Path
    ) -> None:
        # Defensive clamping — bad sample cannot produce NaN / negative JSON.
        observability.record_federated_summary(
            invoked=-5,  # type: ignore[arg-type]
            projects_queried=-1,  # type: ignore[arg-type]
            results_returned=-3,  # type: ignore[arg-type]
        )
        events = _read_metrics(metrics_path)
        for e in events:
            assert int(e["fields"].get("count", 0)) >= 0


# ---------- Integration: InMemoryBackend.mem_search_federated emits counters ----------


class TestInMemoryBackendFederatedEmitsCounters:
    """Calling ``InMemoryBackend.mem_search_federated`` emits the 3 counters."""

    def _seed(self, backend: InMemoryBackend) -> None:
        for project in ("flow-engineering", "mockup-2-blog", "tecnodespegue-landing"):
            obs = backend.mem_save(
                title=f"{project} drift",
                content="drift detection strategy",
                topic_key="sdd/x/spec",
            )
            obs["project"] = project
            obs["created_at"] = "2026-06-15 12:00:00"

    def test_mem_search_federated_emits_three_events(
        self, metrics_path: Path
    ) -> None:
        backend = InMemoryBackend()
        self._seed(backend)
        backend.mem_search_federated("drift", projects=None, limit=10)
        events = _read_metrics(metrics_path)
        names = {e["name"] for e in events}
        assert "federated_search_invoked_total" in names
        assert "federated_search_projects_queried" in names
        assert "federated_search_results_returned_total" in names

    def test_mem_search_federated_invoked_increments_by_one(
        self, metrics_path: Path
    ) -> None:
        backend = InMemoryBackend()
        self._seed(backend)
        before = _sum_count(
            _events_for(
                _read_metrics(metrics_path), "federated_search_invoked_total"
            )
        )
        backend.mem_search_federated("drift", projects=None, limit=10)
        after = _sum_count(
            _events_for(
                _read_metrics(metrics_path), "federated_search_invoked_total"
            )
        )
        assert after - before == 1

    def test_mem_search_federated_results_returned_count_matches_rows(
        self, metrics_path: Path
    ) -> None:
        backend = InMemoryBackend()
        self._seed(backend)
        results = backend.mem_search_federated("drift", projects=None, limit=10)
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_results_returned_total"
        )
        assert _sum_count(events) == len(results)
        assert len(results) == 3

    def test_mem_search_federated_projects_count_matches_query(
        self, metrics_path: Path
    ) -> None:
        backend = InMemoryBackend()
        self._seed(backend)
        backend.mem_search_federated(
            "drift", projects=["flow-engineering", "mockup-2-blog"], limit=10
        )
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_projects_queried"
        )
        # One event per call (histogram), count = number of projects queried.
        assert len(events) == 1
        assert events[0]["fields"]["count"] == 2

    def test_mem_search_federated_projects_none_yields_count_zero(
        self, metrics_path: Path
    ) -> None:
        backend = InMemoryBackend()
        self._seed(backend)
        backend.mem_search_federated("drift", projects=None, limit=10)
        events = _events_for(
            _read_metrics(metrics_path), "federated_search_projects_queried"
        )
        assert events[0]["fields"]["count"] == 0
