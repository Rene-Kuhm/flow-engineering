"""Unit tests for the 6 vector_* observability counters (REQ-22).

REQ-22 + design D11: 6 new counters land in observability.py:
- ``vector_search_invoked_total`` — counter with ``trigger`` tag (cli|programmatic)
- ``vector_search_results_returned_total`` — counter, sum of result-list lengths
- ``vector_search_latency_ms`` — histogram (elapsed_ms per call)
- ``vector_index_size_observations`` — gauge, current embedding count
- ``reindex_observations_total`` — counter, increments by batch size
- ``reindex_duration_seconds`` — gauge, last run duration

These counters MUST follow the REQ-8 naming convention (``subject_event_total``
for counters, ``subject_latency_ms`` / ``subject_duration_seconds`` for timing)
so ``flow metrics`` consumers across the ``decision-code-linking`` →
``vector-semantic-search`` boundary can rely on the names without a deprecation
period.

The helper ``record_vector_summary(...)`` emits exactly one JSONL line per
``flow reindex`` invocation (parallels ``record_drift_summary`` from REQ-12).

Integration with ``HybridBackend.mem_search_hybrid`` lands as part of this task;
the integration tests verify the counters actually fire on a real hybrid call.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from flow_engineering import observability


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
    """Filter the metrics events to those whose counter name matches."""
    return [e for e in events if e.get("name") == name]


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``FLOW_METRICS_PATH`` at a tmp file so tests don't pollute ~/.flow."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


# ---------- REQ-22 scenario 4: naming convention (no drift) ----------


class TestVectorCounterNaming:
    """REQ-22 scenario 4: counter names MUST follow REQ-8 convention."""

    def test_all_six_counter_names_defined(self) -> None:
        # The names list is the canonical contract — surfaces in
        # ``openspec/specs/observability/spec.md`` per REQ-22 scenario 4.
        names = observability.VECTOR_COUNTER_NAMES
        assert isinstance(names, list)
        assert len(names) == 6
        assert "vector_search_invoked_total" in names
        assert "vector_search_results_returned_total" in names
        assert "vector_search_latency_ms" in names
        assert "vector_index_size_observations" in names
        assert "reindex_observations_total" in names
        assert "reindex_duration_seconds" in names

    def test_counter_names_use_subject_event_total_pattern(self) -> None:
        # REQ-8: ``_total`` suffix is required for counters (verb-style events).
        counters = [
            "vector_search_invoked_total",
            "vector_search_results_returned_total",
            "reindex_observations_total",
        ]
        for c in counters:
            assert c.endswith("_total"), (
                f"Counter {c} does not match REQ-8 ``_total`` suffix convention"
            )

    def test_timing_names_use_ms_or_seconds_unit(self) -> None:
        # REQ-8: timing counters end in ``_ms`` (latency) or ``_seconds``
        # (duration) so units are unambiguous from the name.
        timings = ["vector_search_latency_ms", "reindex_duration_seconds"]
        for t in timings:
            assert t.endswith("_ms") or t.endswith("_seconds"), (
                f"Timing name {t} does not match REQ-8 unit convention"
            )

    def test_gauge_name_does_not_end_in_total(self) -> None:
        # Gauges are point-in-time values; they MUST NOT end in ``_total``.
        gauges = ["vector_index_size_observations"]
        for g in gauges:
            assert not g.endswith("_total"), (
                f"Gauge {g} erroneously uses the counter suffix"
            )


# ---------- REQ-22 scenario 1: invoked counter + trigger tag ----------


class TestVectorSearchInvokedCounter:
    """REQ-22 scenario 1: ``vector_search_invoked_total`` increments per call."""

    def test_record_vector_summary_emits_invoked_counter(
        self, metrics_path: Path
    ) -> None:
        observability.record_vector_summary(
            invoked=1,
            results_returned=3,
            latency_ms=42,
            index_size=10,
            trigger="programmatic",
        )
        events = _events_for(_read_metrics(metrics_path), "vector_search_invoked_total")
        assert len(events) == 1
        assert events[0]["fields"].get("count") == 1
        assert events[0]["fields"].get("trigger") == "programmatic"

    def test_record_vector_summary_accepts_cli_trigger(
        self, metrics_path: Path
    ) -> None:
        observability.record_vector_summary(
            invoked=1,
            results_returned=0,
            latency_ms=5,
            index_size=0,
            trigger="cli",
        )
        events = _events_for(_read_metrics(metrics_path), "vector_search_invoked_total")
        assert len(events) == 1
        assert events[0]["fields"].get("trigger") == "cli"

    def test_invoked_count_increments_across_multiple_calls(
        self, metrics_path: Path
    ) -> None:
        # Three calls should produce three distinct JSONL events with
        # ``count`` summing to the total invocation count.
        for i in range(3):
            observability.record_vector_summary(
                invoked=1,
                results_returned=i,
                latency_ms=10 * (i + 1),
                index_size=10,
                trigger="programmatic",
            )
        events = _events_for(_read_metrics(metrics_path), "vector_search_invoked_total")
        assert len(events) == 3
        total = sum(e["fields"].get("count", 0) for e in events)
        assert total == 3


# ---------- REQ-22 scenario 2: latency_ms appears in metrics ----------


class TestVectorSearchLatencyCounter:
    """REQ-22 scenario 2: ``vector_search_latency_ms`` appears in metrics."""

    def test_latency_recorded_in_elapsed_ms_field(
        self, metrics_path: Path
    ) -> None:
        observability.record_vector_summary(
            invoked=1,
            results_returned=2,
            latency_ms=42,
            index_size=10,
            trigger="programmatic",
        )
        events = _events_for(_read_metrics(metrics_path), "vector_search_latency_ms")
        assert len(events) == 1
        # Histogram convention: each event carries ``elapsed_ms`` so a
        # downstream ``flow metrics`` summary can compute P50/P95/P99.
        assert events[0]["fields"].get("elapsed_ms") == 42

    def test_multiple_latencies_persist_as_separate_events(
        self, metrics_path: Path
    ) -> None:
        for ms in [10, 25, 100, 50]:
            observability.record_vector_summary(
                invoked=1,
                results_returned=1,
                latency_ms=ms,
                index_size=1,
                trigger="programmatic",
            )
        events = _events_for(_read_metrics(metrics_path), "vector_search_latency_ms")
        elapsed = [e["fields"]["elapsed_ms"] for e in events]
        assert elapsed == [10, 25, 100, 50]


# ---------- REQ-22 scenario 3: reindex counter + index size gauge ----------


class TestReindexCounters:
    """REQ-22 scenario 3: reindex counters reflect actual reindex state."""

    def test_reindex_observations_total_matches_count(
        self, metrics_path: Path
    ) -> None:
        # Simulate a reindex of 100 observations in one batch.
        observability.record_vector_summary(
            invoked=0,  # not a search — just reindex
            results_returned=0,
            latency_ms=0,
            index_size=100,
            trigger="programmatic",
            reindex_observations=100,
            reindex_duration_seconds=4.5,
        )
        events = _events_for(_read_metrics(metrics_path), "reindex_observations_total")
        assert len(events) == 1
        assert events[0]["fields"].get("count") == 100

    def test_reindex_duration_recorded_as_gauge(
        self, metrics_path: Path
    ) -> None:
        observability.record_vector_summary(
            invoked=0,
            results_returned=0,
            latency_ms=0,
            index_size=100,
            trigger="programmatic",
            reindex_observations=100,
            reindex_duration_seconds=12.5,
        )
        events = _events_for(_read_metrics(metrics_path), "reindex_duration_seconds")
        assert len(events) == 1
        assert events[0]["fields"].get("value") == 12.5

    def test_index_size_gauge_reflects_current_count(
        self, metrics_path: Path
    ) -> None:
        # The gauge MUST reflect ``index_size`` so ``flow metrics`` can show
        # the latest size without aggregating across events.
        observability.record_vector_summary(
            invoked=1,
            results_returned=0,
            latency_ms=10,
            index_size=42,
            trigger="programmatic",
        )
        events = _events_for(_read_metrics(metrics_path), "vector_index_size_observations")
        assert len(events) == 1
        assert events[0]["fields"].get("value") == 42

    def test_results_returned_counter_sums_lengths(
        self, metrics_path: Path
    ) -> None:
        # Two calls returning 3 and 5 results should produce two JSONL
        # events whose ``count`` fields sum to 8.
        observability.record_vector_summary(
            invoked=1, results_returned=3, latency_ms=10,
            index_size=10, trigger="programmatic",
        )
        observability.record_vector_summary(
            invoked=1, results_returned=5, latency_ms=20,
            index_size=10, trigger="programmatic",
        )
        events = _events_for(
            _read_metrics(metrics_path), "vector_search_results_returned_total"
        )
        assert len(events) == 2
        total = sum(e["fields"].get("count", 0) for e in events)
        assert total == 8


# ---------- helper function contract ----------


class TestRecordVectorSummaryContract:
    """``record_vector_summary`` is the one-stop helper for vector metrics."""

    def test_helper_emits_exactly_six_jsonl_lines(self, metrics_path: Path) -> None:
        # One search call: 6 counters → 6 JSONL lines on disk.
        before = len(_read_metrics(metrics_path))
        observability.record_vector_summary(
            invoked=1,
            results_returned=2,
            latency_ms=33,
            index_size=50,
            trigger="cli",
        )
        after = len(_read_metrics(metrics_path))
        assert after - before == 6

    def test_helper_emits_only_relevant_lines_when_reindex_kw_unused(
        self, metrics_path: Path
    ) -> None:
        # Pure search call (no reindex kwargs) MUST emit only the 4
        # search-related counters, not the 2 reindex-only ones.
        before = len(_read_metrics(metrics_path))
        observability.record_vector_summary(
            invoked=1,
            results_returned=1,
            latency_ms=10,
            index_size=10,
            trigger="programmatic",
        )
        after = len(_read_metrics(metrics_path))
        assert after - before == 4  # invoked + results + latency + index_size

        names = {
            e["name"]
            for e in _read_metrics(metrics_path)[before:after]
        }
        assert names == {
            "vector_search_invoked_total",
            "vector_search_results_returned_total",
            "vector_search_latency_ms",
            "vector_index_size_observations",
        }


# ---------- HybridBackend integration ----------


class TestHybridBackendCounterIntegration:
    """T1.7 acceptance: HybridBackend.mem_search_hybrid calls the helper."""

    def test_hybrid_search_emits_invoked_counter_with_programmatic_trigger(
        self, metrics_path: Path
    ) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from flow_engineering.embedding_provider import MockEmbeddingProvider
        from flow_engineering.hybrid_backend import HybridBackend

        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)

        # Seed an observation so mem_search has something to find.
        inner.mem_save(
            title="drift", content="drift detection strategy", topic_key="t"
        )
        before = len(_read_metrics(metrics_path))
        hb.mem_search_hybrid("drift detection", k=5, alpha=0.5)
        after = len(_read_metrics(metrics_path))

        # 4 search counters: invoked + results + latency + index_size.
        assert after - before == 4
        invoked = _events_for(
            _read_metrics(metrics_path)[before:after],
            "vector_search_invoked_total",
        )
        assert len(invoked) == 1
        assert invoked[0]["fields"].get("trigger") == "programmatic"
        assert invoked[0]["fields"].get("count") == 1

    def test_hybrid_search_semantic_emits_invoked_counter(
        self, metrics_path: Path
    ) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from flow_engineering.embedding_provider import MockEmbeddingProvider
        from flow_engineering.hybrid_backend import HybridBackend

        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        inner.mem_save(title="x", content="drift detection strategy", topic_key="t")

        before = len(_read_metrics(metrics_path))
        hb.mem_search_semantic("drift detection", k=5)
        after = len(_read_metrics(metrics_path))

        assert after - before == 4
        events = _events_for(
            _read_metrics(metrics_path)[before:after],
            "vector_search_invoked_total",
        )
        assert len(events) == 1
        assert events[0]["fields"].get("count") == 1

    def test_hybrid_search_does_not_emit_reindex_only_counters(
        self, metrics_path: Path
    ) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from flow_engineering.embedding_provider import MockEmbeddingProvider
        from flow_engineering.hybrid_backend import HybridBackend

        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        inner.mem_save(title="x", content="drift detection strategy", topic_key="t")

        before = len(_read_metrics(metrics_path))
        hb.mem_search_hybrid("drift detection", k=5)
        names = {
            e["name"]
            for e in _read_metrics(metrics_path)[before:]
        }
        # Reindex-only counters MUST NOT fire on a search call.
        assert "reindex_observations_total" not in names
        assert "reindex_duration_seconds" not in names

    def test_latency_is_positive_for_real_search(
        self, metrics_path: Path
    ) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from flow_engineering.embedding_provider import MockEmbeddingProvider
        from flow_engineering.hybrid_backend import HybridBackend

        inner = InMemoryBackend()
        provider = MockEmbeddingProvider()
        hb = HybridBackend(inner, provider)
        inner.mem_save(title="x", content="drift detection strategy", topic_key="t")

        before = len(_read_metrics(metrics_path))
        hb.mem_search_hybrid("drift detection", k=5)
        events = _events_for(
            _read_metrics(metrics_path)[before:],
            "vector_search_latency_ms",
        )
        assert len(events) == 1
        elapsed = events[0]["fields"].get("elapsed_ms")
        # Latency MUST be a non-negative integer (real timer; can be 0 on
        # extremely fast machines but never negative).
        assert isinstance(elapsed, int)
        assert elapsed >= 0

    def test_metrics_helper_is_idempotent_across_failures(
        self, metrics_path: Path
    ) -> None:
        # record_vector_summary MUST be fail-open (mirrors ``increment``):
        # a bad metric value should not raise; it should be silently
        # recorded with the next-best-valid representation.
        # We pass a negative latency; the helper clamps to 0 (no NaN/neg).
        observability.record_vector_summary(
            invoked=1,
            results_returned=0,
            latency_ms=-1,  # invalid
            index_size=0,
            trigger="programmatic",
        )
        events = _events_for(_read_metrics(metrics_path), "vector_search_latency_ms")
        assert len(events) == 1
        assert events[0]["fields"].get("elapsed_ms") == 0
