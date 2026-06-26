"""Unit tests for observability counters added in PR#2 batch 2 (REQ-8 close).

REQ-8 close introduces four new counters on top of the existing REQ-6 set:

- ``inspect_invoked_total`` -- incremented once per ``flow inspect`` call.
- ``inspect_render_ms`` -- one observation per inspect render with elapsed ms.
- ``backfill_observations_total`` -- total observations scanned for coverage.
- ``backfill_with_refs_total`` -- observations that carry a backfill source.

Plus a helper ``backfill_coverage(backend)`` that returns the ratio of
backfilled observations to total observations (rounded to 3 decimals).

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit wires the new counters and helpers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flow_engineering.binding import format_code_refs_block
from flow_engineering.engram_io import InMemoryBackend

METRICS_PATH_ENV = "FLOW_METRICS_PATH"


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv(METRICS_PATH_ENV, str(path))
    return path


def _read_events(path: Path) -> list[dict]:
    import json

    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _make_obs(obs_id: int, *, content: str, created_at: int = 1000) -> dict:
    return {
        "id": obs_id,
        "title": f"obs-{obs_id}",
        "content": content,
        "topic_key": f"sdd/test/{obs_id}",
        "type": "architecture",
        "scope": "project",
        "project": "insyd",
        "created_at": created_at,
        "updated_at": created_at,
    }


# ---------- New counter names ----------


class TestNewCounterNames:
    """The new counter names round-trip through the JSONL sink."""

    @pytest.mark.parametrize(
        "name",
        [
            "inspect_invoked_total",
            "inspect_render_ms",
            "backfill_observations_total",
            "backfill_with_refs_total",
        ],
    )
    def test_new_counter_round_trips(self, metrics_path: Path, name: str) -> None:
        from flow_engineering import observability

        observability.increment(name, payload=1)
        events = _read_events(metrics_path)
        assert events[-1]["name"] == name
        assert events[-1]["fields"].get("payload") == 1

    def test_inspect_render_ms_records_elapsed(
        self, metrics_path: Path
    ) -> None:
        from flow_engineering import observability

        observability.increment("inspect_render_ms", elapsed_ms=12)
        events = _read_events(metrics_path)
        assert events[-1]["fields"].get("elapsed_ms") == 12


# ---------- backfill_coverage helper ----------


class TestBackfillCoverage:
    """``backfill_coverage(backend)`` returns the ratio of backfill-sourced obs."""

    def test_backfill_coverage_with_no_observations_returns_zero(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        backend = InMemoryBackend()
        ratio = observability.backfill_coverage(backend)
        assert ratio == 0.0

    def test_backfill_coverage_with_all_backfilled_returns_one(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        backend = InMemoryBackend()
        for i in range(3):
            content = "## D\n\n" + format_code_refs_block([], source="backfill")
            backend.mem_save(title=f"d{i}", content=content, topic_key=f"sdd/test/{i}")
        ratio = observability.backfill_coverage(backend)
        assert ratio == 1.0

    def test_backfill_coverage_mixed_returns_ratio(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        backend = InMemoryBackend()
        # 2 backfill, 3 manual -- 2/5 = 0.4
        for i in range(2):
            backend.mem_save(
                title=f"b{i}",
                content="## D\n\n" + format_code_refs_block([], source="backfill"),
                topic_key=f"sdd/test/b{i}",
            )
        for i in range(3):
            backend.mem_save(
                title=f"m{i}",
                content="## D\n\n" + format_code_refs_block([], source="manual"),
                topic_key=f"sdd/test/m{i}",
            )
        ratio = observability.backfill_coverage(backend)
        assert ratio == 0.4

    def test_backfill_coverage_rounded_to_three_decimals(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        backend = InMemoryBackend()
        # 1 backfill, 2 manual -- 1/3 = 0.333333... rounded to 0.333
        backend.mem_save(
            title="b0",
            content="## D\n\n" + format_code_refs_block([], source="backfill"),
            topic_key="sdd/test/b0",
        )
        for i in range(2):
            backend.mem_save(
                title=f"m{i}",
                content="## D\n\n" + format_code_refs_block([], source="manual"),
                topic_key=f"sdd/test/m{i}",
            )
        ratio = observability.backfill_coverage(backend)
        assert ratio == 0.333

    def test_backfill_coverage_spec_example_46_of_103(self, metrics_path: Path) -> None:
        """REQ-8 scenario: 46 backfill of 103 total; standard rounding to 3dp.

        Note: the spec example says 0.446 but the actual ratio is
        46/103 = 0.4466019..., which standard-rounds to 0.447 (the 4th
        decimal is 6, so the 3rd rounds up). This test asserts the
        mathematically correct value.
        """
        from flow_engineering import observability

        backend = InMemoryBackend()
        for i in range(46):
            backend.mem_save(
                title=f"b{i}",
                content="## D\n\n" + format_code_refs_block([], source="backfill"),
                topic_key=f"sdd/test/b{i}",
            )
        for i in range(57):
            backend.mem_save(
                title=f"m{i}",
                content="## D\n\n" + format_code_refs_block([], source="manual"),
                topic_key=f"sdd/test/m{i}",
            )
        ratio = observability.backfill_coverage(backend)
        assert ratio == 0.447

    def test_backfill_coverage_ignores_unbound(self, metrics_path: Path) -> None:
        from flow_engineering import observability

        backend = InMemoryBackend()
        # 1 backfill, 1 unbound -- ratio is 1/2 of backfill = 0.5.
        backend.mem_save(
            title="b0",
            content="## D\n\n" + format_code_refs_block([], source="backfill"),
            topic_key="sdd/test/b0",
        )
        backend.mem_save(
            title="u0",
            content="## D\n\n" + format_code_refs_block([], source="unbound"),
            topic_key="sdd/test/u0",
        )
        ratio = observability.backfill_coverage(backend)
        assert ratio == 0.5


# ---------- Coverage counter helpers ----------


class TestCoverageCounters:
    """``record_backfill_coverage`` increments the two coverage counters."""

    def test_record_backfill_coverage_increments_total_and_with_refs(
        self, metrics_path: Path
    ) -> None:
        from flow_engineering import observability

        observability.record_backfill_coverage(observations_total=10, with_refs=4)
        events = _read_events(metrics_path)
        names = [e["name"] for e in events]
        assert "backfill_observations_total" in names
        assert "backfill_with_refs_total" in names
        by_name = {e["name"]: e for e in events}
        assert by_name["backfill_observations_total"]["fields"].get("count") == 10
        assert by_name["backfill_with_refs_total"]["fields"].get("count") == 4
