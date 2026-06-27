"""Unit tests for the 4 SNAPSHOT observability counters + record_snapshot_event helper (REQ-26).

REQ-26 (graph-snapshots change #5 batch C T1.7): 4 new counters land in
observability.py to instrument the snapshot lifecycle:

- ``snapshot_create_total`` — one event per successful ``SnapshotManager.create()``.
- ``snapshot_rollback_total`` — one event per ``rollback()`` (success + conflict
  + refusal; the audit trail captures attempted rollbacks too).
- ``snapshot_prune_total`` — one event per deletion in apply mode (``confirm=True``);
  NOT fired in dry-run.
- ``snapshot_load_failed_total`` — one event per failed load from
  ``decision_drift._load_graph_from_snapshot`` (drift-pinned scan unavailability,
  REQ-33 D2 graceful degradation).

The catalog is exposed as :data:`SNAPSHOT_COUNTER_NAMES` (mirrors
``VECTOR_COUNTER_NAMES`` / ``FEDERATED_COUNTER_NAMES``); the helper
``record_snapshot_event(counter_name, **labels)`` emits one JSONL event per call
(parallels ``record_vector_summary`` / ``record_drift_summary`` /
``record_federated_summary``).

Integration with ``SnapshotManager.create`` / ``rollback`` / ``prune`` and with
``decision_drift.scan_change(snap_id=...)`` lands in this task so BDD scenarios
that exercise the snapshot lifecycle observe the counter batch fire on every
operation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from flow_engineering import observability
from flow_engineering.engram_io import InMemoryBackend

# ---------- helpers ----------


def _read_metrics(metrics_path: Path) -> list[dict[str, Any]]:
    """Parse the JSONL metrics file into a list of dicts (skips malformed lines)."""
    if not metrics_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in metrics_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _events_for(events: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [e for e in events if e.get("name") == name]


def _sum_count(events: list[dict[str, Any]]) -> int:
    return sum(int(e.get("fields", {}).get("count", 0)) for e in events)


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


@pytest.fixture
def snapshots_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "snapshots"
    monkeypatch.setenv("FLOW_SNAPSHOTS_DIR", str(d))
    return d


@pytest.fixture
def graph_json_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    p = tmp_path / "graph.json"
    monkeypatch.setenv("FLOW_GRAPH_JSON_PATH", str(p))
    return p


def _seed_backend(backend: InMemoryBackend, *, n: int = 3) -> list[int]:
    ids: list[int] = []
    for i in range(n):
        obs = backend.mem_save(
            title=f"snap obs {i}",
            content=f"drift detection strategy {i}",
            topic_key="sdd/x/spec",
        )
        ids.append(int(obs["id"]))
    return ids


# ---------- REQ-26 scenario 4: snapshot counter catalog ----------


class TestSnapshotCounterCatalog:
    """REQ-26 scenario 4: 4 snapshot counters are first-class names + catalog tuple."""

    def test_snapshot_counter_names_has_exactly_four_entries_in_correct_order(self) -> None:
        names = observability.SNAPSHOT_COUNTER_NAMES
        assert isinstance(names, tuple), (
            f"SNAPSHOT_COUNTER_NAMES must be a tuple for catalog immutability; "
            f"got {type(names).__name__}"
        )
        assert names == (
            "snapshot_create_total",
            "snapshot_rollback_total",
            "snapshot_prune_total",
            "snapshot_load_failed_total",
        ), (
            f"SNAPSHOT_COUNTER_NAMES order/content mismatch; got {names!r}"
        )

    def test_snapshot_counter_names_subject_event_total_pattern(self) -> None:
        # REQ-8: ``_total`` suffix required for counters (verb-style events).
        for c in observability.SNAPSHOT_COUNTER_NAMES:
            assert c.endswith("_total"), (
                f"Counter {c} does not match REQ-8 ``_total`` suffix convention"
            )


# ---------- record_snapshot_event helper ----------


class TestRecordSnapshotEvent:
    """``record_snapshot_event`` emits one JSONL event per call."""

    def test_record_snapshot_event_appends_to_metrics_json(
        self, metrics_path: Path
    ) -> None:
        observability.record_snapshot_event("snapshot_create_total")
        events = _read_metrics(metrics_path)
        assert len(events) == 1
        assert events[0]["name"] == "snapshot_create_total"
        assert events[0]["fields"] == {}
        assert "ts" in events[0]
        assert events[0]["ts"].endswith("Z")

    def test_record_snapshot_event_with_labels(self, metrics_path: Path) -> None:
        observability.record_snapshot_event(
            "snapshot_rollback_total",
            success="true",
            safety_snapshot_id="snap_abc",
            target_snapshot_id="snap_xyz",
        )
        events = _read_metrics(metrics_path)
        assert len(events) == 1
        assert events[0]["name"] == "snapshot_rollback_total"
        assert events[0]["fields"]["success"] == "true"
        assert events[0]["fields"]["safety_snapshot_id"] == "snap_abc"
        assert events[0]["fields"]["target_snapshot_id"] == "snap_xyz"

    def test_record_snapshot_event_unknown_name_still_emits(
        self, metrics_path: Path
    ) -> None:
        # Helper is fail-open: unknown name is still emitted (no validation
        # gate). Production code paths always use the catalog, but the
        # helper MUST NOT raise when called with a custom name.
        observability.record_snapshot_event("snapshot_custom_metric", value=42)
        events = _read_metrics(metrics_path)
        assert len(events) == 1
        assert events[0]["name"] == "snapshot_custom_metric"
        assert events[0]["fields"]["value"] == 42


# ---------- Integration: SnapshotManager.create emits snapshot_create_total ----------


class TestSnapshotCreateCounter:
    """``SnapshotManager.create()`` emits ``snapshot_create_total`` after success."""

    def test_snapshot_create_total_incremented_on_create(
        self, metrics_path: Path, snapshots_dir: Path, graph_json_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        graph_json_path.write_text('{"nodes": []}', encoding="utf-8")

        manager = SnapshotManager(snapshots_dir=snapshots_dir, backend=backend)

        before = len(_events_for(_read_metrics(metrics_path), "snapshot_create_total"))
        manager.create(description="before-deploy")
        manager.create(description="after-deploy")
        after = len(_events_for(_read_metrics(metrics_path), "snapshot_create_total"))

        assert after - before == 2, (
            f"expected 2 new snapshot_create_total events; "
            f"got delta {after - before} (before={before}, after={after})"
        )


# ---------- Integration: SnapshotManager.rollback emits snapshot_rollback_total ----------


class TestSnapshotRollbackCounter:
    """``SnapshotManager.rollback()`` emits ``snapshot_rollback_total`` (success + audit)."""

    def test_snapshot_rollback_total_incremented_on_rollback(
        self, metrics_path: Path, snapshots_dir: Path, graph_json_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        graph_json_path.write_text('{"nodes": []}', encoding="utf-8")

        manager = SnapshotManager(snapshots_dir=snapshots_dir, backend=backend)
        snap_id = manager.create(description="rollback-target")

        before = len(_events_for(_read_metrics(metrics_path), "snapshot_rollback_total"))
        result = manager.rollback(snap_id, confirm=True)
        after = len(_events_for(_read_metrics(metrics_path), "snapshot_rollback_total"))

        # At least one event fired (the success event). Conflict/refusal events
        # also count, but in this scenario rollback succeeded.
        assert after - before >= 1, (
            f"expected >=1 new snapshot_rollback_total event; got delta {after - before}"
        )
        assert result.target_snapshot_id == snap_id


# ---------- Integration: SnapshotManager.prune emits snapshot_prune_total (apply only) ----------


class TestSnapshotPruneCounter:
    """``SnapshotManager.prune()`` emits ``snapshot_prune_total`` per deletion in apply mode ONLY."""

    def test_snapshot_prune_total_incremented_per_deletion_only_not_dry_run(
        self, metrics_path: Path, snapshots_dir: Path, graph_json_path: Path
    ) -> None:
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=3)
        graph_json_path.write_text('{"nodes": []}', encoding="utf-8")

        manager = SnapshotManager(snapshots_dir=snapshots_dir, backend=backend)
        # Create 5 snapshots with deterministic spacing so prune() picks
        # the right candidates.
        ids: list[str] = []
        for i in range(5):
            ids.append(manager.create(description=f"seed-{i}"))
            # No sleep — all 5 share the same second; the deterministic
        # tie-break by snap_id is enough for prune() to be deterministic.

        before_dry = len(_events_for(_read_metrics(metrics_path), "snapshot_prune_total"))

        # Dry-run prune: 3 candidates (keep_last=2), NO counter increment.
        dry = manager.prune(keep_last=2)  # default confirm=False
        assert dry.dry_run is True
        assert len(dry.would_delete) == 3

        after_dry = len(_events_for(_read_metrics(metrics_path), "snapshot_prune_total"))
        assert after_dry == before_dry, (
            f"dry-run prune MUST NOT emit snapshot_prune_total; "
            f"got delta {after_dry - before_dry} (before={before_dry}, after={after_dry})"
        )

        # Apply prune: same policy, confirm=True, deletes 3 files,
        # 3 counter events fired.
        result = manager.prune(keep_last=2, confirm=True)
        assert result.dry_run is False
        assert len(result.deleted) == 3

        after_apply = len(_events_for(_read_metrics(metrics_path), "snapshot_prune_total"))
        assert after_apply - before_dry == 3, (
            f"expected 3 snapshot_prune_total events (one per deletion); "
            f"got delta {after_apply - before_dry} (before={before_dry}, after={after_apply})"
        )


# ---------- Integration: decision_drift.scan_change emits snapshot_load_failed_total ----------


class TestSnapshotLoadFailedCounter:
    """``decision_drift._load_graph_from_snapshot`` emits ``snapshot_load_failed_total`` when graph is missing."""

    def test_snapshot_load_failed_total_incremented_on_missing_graph(
        self, metrics_path: Path, snapshots_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering.decision_drift import SnapshotGraphMissing, scan_change
        from flow_engineering.snapshot_manager import SnapshotManager

        backend = InMemoryBackend()
        _seed_backend(backend, n=2)

        # Create a snapshot WITHOUT graph content (include_graph=False).
        manager = SnapshotManager(snapshots_dir=snapshots_dir, backend=backend)
        snap_id = manager.create(description="no-graph", include_graph=False)

        before = len(
            _events_for(_read_metrics(metrics_path), "snapshot_load_failed_total")
        )

        with pytest.raises(SnapshotGraphMissing):
            scan_change("test-change", snap_id=snap_id)

        after = len(
            _events_for(_read_metrics(metrics_path), "snapshot_load_failed_total")
        )
        assert after - before == 1, (
            f"expected 1 snapshot_load_failed_total event; "
            f"got delta {after - before} (before={before}, after={after})"
        )
