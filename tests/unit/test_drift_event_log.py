"""Unit tests for ``drift_event_log`` (REQ-55 W5).

Covers the append-only JSONL writer that backs the
``drift_events.jsonl`` audit trail emitted by the daemon's drift handler.

Test isolation: each test gets a fresh ``tmp_path`` and constructs the
``DriftEventLog`` with an explicit ``path`` so production paths under
``~/.flow-engineering/`` are never touched.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict
from pathlib import Path

import pytest

from flow_engineering.drift_event_log import (
    DEFAULT_DRIFT_EVENT_LOG_PATH,
    DriftEvent,
    DriftEventLog,
)


# ---------- Fixtures ----------


@pytest.fixture
def log_path(tmp_path: Path) -> Path:
    """Per-test JSONL sink under tmp_path."""
    return tmp_path / "drift_events.jsonl"


def _make_event(
    *,
    change: str = "decision-reality-drift",
    decision_id: str = "42",
    binding_id: str = "obs-42",
    event_class: str = "label_drift",
    detected_at: float = 1_710_000_000.0,
) -> DriftEvent:
    """Build a ``DriftEvent`` with sensible defaults."""
    return DriftEvent(
        change=change,
        decision_id=decision_id,
        binding_id=binding_id,
        event_class=event_class,
        detected_at=detected_at,
    )


# ---------- append() creates + writes a file ----------


class TestAppendCreatesFile:
    """The append writer MUST create parent dirs + the JSONL file."""

    def test_drift_event_log_creates_file_on_append(self, log_path: Path) -> None:
        """Appending one event creates the JSONL file with exactly one line."""
        log = DriftEventLog(path=log_path)
        event = _make_event()

        log.append(event)

        assert log_path.exists(), "drift_events.jsonl was not created"
        content = log_path.read_text(encoding="utf-8")
        # Exactly one JSONL line ending in newline.
        lines = content.splitlines()
        assert len(lines) == 1
        # Round-trip: parseable JSON with the spec wire schema keys
        # (note: ``class`` is the JSON key, ``event_class`` is the Python
        # field name per archived spec REQ-15).
        parsed = json.loads(lines[0])
        assert parsed == event.to_json_dict()

    def test_drift_event_log_creates_parent_dirs(
        self, tmp_path: Path
    ) -> None:
        """A nested parent path (missing intermediate dirs) is auto-created."""
        nested = tmp_path / "deep" / "nested" / "drift_events.jsonl"
        log = DriftEventLog(path=nested)

        log.append(_make_event())

        assert nested.exists()


# ---------- append() + read_all() round-trip ----------


class TestAppendMultipleEvents:
    """Multiple appends write one JSONL line per event in order."""

    def test_drift_event_log_appends_multiple_events_as_jsonl(
        self, log_path: Path
    ) -> None:
        """Three appends produce exactly three lines, no overwrites."""
        log = DriftEventLog(path=log_path)
        events = [_make_event(decision_id=str(i), binding_id=f"obs-{i}") for i in range(3)]

        for ev in events:
            log.append(ev)

        content = log_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        assert len(lines) == 3
        for ev, raw in zip(events, lines):
            assert json.loads(raw) == ev.to_json_dict()

    def test_drift_event_log_read_all_returns_events_in_order(
        self, log_path: Path
    ) -> None:
        """``read_all()`` returns the events in append order."""
        log = DriftEventLog(path=log_path)
        events = [
            _make_event(decision_id="1", binding_id="a"),
            _make_event(decision_id="2", binding_id="b"),
            _make_event(decision_id="3", binding_id="c"),
        ]
        for ev in events:
            log.append(ev)

        result = log.read_all()

        assert len(result) == 3
        for got, want in zip(result, events):
            assert got == want

    def test_drift_event_log_read_all_skips_malformed_lines(
        self, log_path: Path
    ) -> None:
        """Malformed JSONL lines are silently skipped (sink is best-effort)."""
        log = DriftEventLog(path=log_path)
        log.append(_make_event(decision_id="1"))
        log.append(_make_event(decision_id="2"))
        # Append a malformed line directly so read_all() must skip it.
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write("not-json\n")
        log.append(_make_event(decision_id="3"))

        result = log.read_all()

        assert len(result) == 3
        assert [ev.decision_id for ev in result] == ["1", "2", "3"]

    def test_drift_event_log_read_all_on_missing_file_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """``read_all()`` returns ``[]`` when the JSONL file does not exist."""
        log = DriftEventLog(path=tmp_path / "nope.jsonl")

        assert log.read_all() == []


# ---------- thread safety via portable file lock ----------


class TestThreadSafety:
    """The append writer MUST use a file lock so concurrent appends do not
    interleave bytes (D11 — file lock + flush for thread safety)."""

    def test_drift_event_log_thread_safety_uses_flock(
        self, log_path: Path
    ) -> None:
        """20 threads × 10 events each produce exactly 200 lines (no lost
        writes, no interleaved bytes)."""
        log = DriftEventLog(path=log_path)
        n_threads = 20
        per_thread = 10

        def _worker(thread_idx: int) -> None:
            for i in range(per_thread):
                log.append(
                    _make_event(
                        decision_id=str(thread_idx * per_thread + i),
                        binding_id=f"obs-{thread_idx}-{i}",
                    )
                )

        threads = [
            threading.Thread(target=_worker, args=(i,)) for i in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lines = log_path.read_text(encoding="utf-8").splitlines()
        # Exactly n_threads * per_thread lines, each a parseable JSON event.
        assert len(lines) == n_threads * per_thread
        parsed = [json.loads(line) for line in lines]
        # No duplicate decision_ids (no lost writes).
        ids = sorted(int(p["decision_id"]) for p in parsed)
        assert ids == list(range(n_threads * per_thread))


# ---------- Default path ----------


class TestDefaultPath:
    """The default path resolves under ``~/.flow-engineering/`` and ends in
    ``drift_events.jsonl`` (mirrors the metrics sink layout)."""

    def test_default_path_is_under_flow_engineering(self) -> None:
        assert DEFAULT_DRIFT_EVENT_LOG_PATH.parent.name == ".flow-engineering"
        assert DEFAULT_DRIFT_EVENT_LOG_PATH.name == "drift_events.jsonl"
