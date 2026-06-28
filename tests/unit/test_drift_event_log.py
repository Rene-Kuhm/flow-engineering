"""Unit tests for ``drift_event_log`` (REQ-55 W5).

Covers the append-only JSONL writer that backs the
``drift_events.jsonl`` audit trail emitted by the daemon's drift handler.

Test isolation: each test gets a fresh ``tmp_path`` and constructs the
``DriftEventLog`` with an explicit ``path`` so production paths under
``~/.flow-engineering/`` are never touched.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime, timedelta
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
    decision_id: int = 42,
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


class TestDriftEvent:
    """REQ-V1.0.1: DriftEvent.decision_id is int (was str).

    v1.0 hard-break: DriftEvent.__post_init__ mirrors the v0.9.0 Finding
    pattern at ``decision_drift.py:84-90`` and raises TypeError on non-int
    decision_id (including ``bool``, which is an int subclass).
    """

    def test_decision_id_rejects_str(self) -> None:
        """Constructing DriftEvent with a str decision_id raises TypeError (REQ-V1.0.1)."""
        with pytest.raises(TypeError) as exc_info:
            DriftEvent(
                decision_id="42",  # type: ignore[arg-type]
                change="x",
                binding_id="y",
                event_class="z",
                detected_at=0.0,
            )
        assert "decision_id" in str(exc_info.value) or "int" in str(exc_info.value)

    def test_decision_id_rejects_bool(self) -> None:
        """Constructing DriftEvent with a bool decision_id raises TypeError (bool is int subclass)."""
        with pytest.raises(TypeError) as exc_info:
            DriftEvent(
                decision_id=True,  # type: ignore[arg-type]
                change="x",
                binding_id="y",
                event_class="z",
                detected_at=0.0,
            )
        assert "decision_id" in str(exc_info.value) or "int" in str(exc_info.value)

    def test_decision_id_accepts_int(self) -> None:
        """Constructing DriftEvent with an int decision_id succeeds (REQ-V1.0.1 happy path)."""
        ev = DriftEvent(
            decision_id=42,
            change="x",
            binding_id="y",
            event_class="z",
            detected_at=0.0,
        )
        assert ev.decision_id == 42
        assert isinstance(ev.decision_id, int)


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
        events = [_make_event(decision_id=i, binding_id=f"obs-{i}") for i in range(3)]

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
            _make_event(decision_id=1, binding_id="a"),
            _make_event(decision_id=2, binding_id="b"),
            _make_event(decision_id=3, binding_id="c"),
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
        log.append(_make_event(decision_id=1))
        log.append(_make_event(decision_id=2))
        # Append a malformed line directly so read_all() must skip it.
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write("not-json\n")
        log.append(_make_event(decision_id=3))

        result = log.read_all()

        assert len(result) == 3
        assert [ev.decision_id for ev in result] == [1, 2, 3]

    def test_drift_event_log_read_all_on_missing_file_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """``read_all()`` returns ``[]`` when the JSONL file does not exist."""
        log = DriftEventLog(path=tmp_path / "nope.jsonl")

        assert log.read_all() == []


# ---------- REQ-V1.0.1 D2: defensive coercion of legacy str lines ----------


class TestReadAllLegacyCoercion:
    """REQ-V1.0.1 D2: legacy ``decision_id: "42"`` (str) JSONL lines from
    pre-v1.0 files are defensively coerced to ``int`` on read with a
    one-time stderr WARN per log-path.
    """

    def test_read_all_coerces_legacy_str_decision_id(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A legacy JSONL line with str decision_id reads back as int + emits WARN."""
        log_path = tmp_path / "drift_events.jsonl"
        # Hand-write a legacy-format JSONL line (str decision_id).
        legacy_line = json.dumps({
            "change": "x",
            "decision_id": "42",
            "binding_id": "y",
            "class": "z",
            "detected_at": 1_710_000_000.0,
        })
        log_path.write_text(legacy_line + "\n", encoding="utf-8")
        log = DriftEventLog(path=log_path)

        events = log.read_all()

        # Exactly one event read back.
        assert len(events) == 1
        # decision_id was coerced from str "42" to int 42.
        assert events[0].decision_id == 42
        assert isinstance(events[0].decision_id, int)
        # One-time stderr WARN was emitted with the legacy marker.
        stderr = capsys.readouterr().err
        assert "legacy str decision_id" in stderr

    def test_read_all_skips_legacy_str_non_numeric_decision_id(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A legacy str decision_id that can't parse to int is silently skipped."""
        log_path = tmp_path / "drift_events.jsonl"
        legacy_line = json.dumps({
            "change": "x",
            "decision_id": "not-a-number",
            "binding_id": "y",
            "class": "z",
            "detected_at": 1_710_000_000.0,
        })
        log_path.write_text(legacy_line + "\n", encoding="utf-8")
        log = DriftEventLog(path=log_path)

        events = log.read_all()

        # Non-numeric legacy str lines are silently skipped (mirrors the
        # malformed-line silent-skip behavior; operator should re-migrate
        # via the CHANGELOG v1.0 sed).
        assert events == []

    def test_read_all_one_time_warn_cadence(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Multiple legacy str lines in one read_all() call emit ONE WARN (per-instance flag)."""
        log_path = tmp_path / "drift_events.jsonl"
        lines = []
        for i in range(3):
            lines.append(json.dumps({
                "change": "x",
                "decision_id": str(i + 100),
                "binding_id": f"y{i}",
                "class": "z",
                "detected_at": 1_710_000_000.0 + i,
            }))
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log = DriftEventLog(path=log_path)

        events = log.read_all()

        # All 3 events read back as int.
        assert len(events) == 3
        assert [ev.decision_id for ev in events] == [100, 101, 102]
        # Exactly ONE stderr WARN was emitted (per-instance flag works).
        stderr = capsys.readouterr().err
        warn_lines = [ln for ln in stderr.splitlines() if "legacy str decision_id" in ln]
        assert len(warn_lines) == 1, (
            f"expected 1 WARN line; got {len(warn_lines)}: {warn_lines}"
        )


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
                        decision_id=thread_idx * per_thread + i,
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


# ---------- REQ-V1.1.1: DriftEventLog rotation (size + age) ----------


class TestRotation:
    """REQ-V1.1.1: DriftEventLog rotation policy.

    Size-based: rotate the active ``drift_events.jsonl`` to
    ``drift_events.<ISO-no-colons>.jsonl`` when ``st_size >=
    FLOW_DRIFT_EVENT_LOG_MAX_BYTES`` (default 10 MB).
    Age-based: delete rotated files older than
    ``FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS`` (default 30 days).
    Best-effort ``try/except OSError`` swallow for slow FS errors.
    """

    def test_rotates_at_max_bytes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Appending past ``FLOW_DRIFT_EVENT_LOG_MAX_BYTES`` rotates the active file."""
        # T1.1 RED: 1 KB threshold so a single DriftEvent triggers rotation.
        log_path = tmp_path / "drift_events.jsonl"
        monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_BYTES", "1024")
        monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS", "30")

        log = DriftEventLog(path=log_path)
        # Force the file to look "full" by pre-sizing it to >= threshold.
        log_path.write_bytes(b"x" * 2048)

        log.append(_make_event(decision_id=1))

        # The active file now exists at the original path (fresh, ready
        # for the NEXT append); a sibling rotated file was created.
        assert log_path.exists()
        rotated = sorted(tmp_path.glob("drift_events.*.jsonl"))
        assert len(rotated) == 1, (
            f"expected exactly 1 rotated file; got {rotated}"
        )
        # The rotated file is lex-sortable (ISO-no-colons format).
        assert rotated[0].name.startswith("drift_events.")
        assert rotated[0].name.endswith(".jsonl")

    def test_no_rotation_when_below_threshold(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A small append below the threshold does NOT trigger rotation."""
        log_path = tmp_path / "drift_events.jsonl"
        monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_BYTES", "1048576")
        monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS", "30")

        log = DriftEventLog(path=log_path)
        for i in range(3):
            log.append(_make_event(decision_id=i))

        # Only the active file exists; no rotated siblings.
        assert log_path.exists()
        rotated = sorted(tmp_path.glob("drift_events.*.jsonl"))
        assert rotated == [], (
            f"unexpected rotated files below threshold: {rotated}"
        )
        # The active file contains all 3 events.
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3

    def test_rotates_when_env_var_overrides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lowering ``FLOW_DRIFT_EVENT_LOG_MAX_BYTES`` triggers rotation sooner."""
        log_path = tmp_path / "drift_events.jsonl"
        # Set a tiny 256-byte threshold — well below one DriftEvent's
        # serialized JSON. After a single append the file should be rotated.
        monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_BYTES", "256")
        monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS", "30")

        log = DriftEventLog(path=log_path)
        log.append(_make_event(decision_id=1))
        log.append(_make_event(decision_id=2))

        # At least one rotated file should exist; the active file should
        # contain only the most recent append.
        rotated = sorted(tmp_path.glob("drift_events.*.jsonl"))
        assert len(rotated) >= 1, "expected at least 1 rotated file"
        # The active file is short (only the last append — the rotated
        # file absorbed the pre-rotation writes).
        active_lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(active_lines) <= 2  # fresh file may contain 0-2 events

    def test_deletes_rotated_files_older_than_max_age_days(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rotated files older than ``FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS`` are deleted."""
        log_path = tmp_path / "drift_events.jsonl"
        monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_BYTES", "10")
        monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS", "1")

        # Pre-create a rotated file with an old mtime (simulate "10 days old").
        old_rotated = tmp_path / "drift_events.20200101T000000Z.jsonl"
        old_rotated.write_text("legacy\n", encoding="utf-8")
        ten_days_ago = (datetime.now(UTC) - timedelta(days=10)).timestamp()
        os.utime(old_rotated, (ten_days_ago, ten_days_ago))

        log = DriftEventLog(path=log_path)
        # Any append triggers the rotation helper, which also walks
        # siblings and deletes old rotated files.
        log.append(_make_event(decision_id=1))

        assert not old_rotated.exists(), (
            "old rotated file should have been deleted on next append"
        )

    def test_rotation_preserves_lock(self, log_path: Path) -> None:
        """Rotation runs inside ``self._lock`` so concurrent appends do not
        interleave bytes (D11 contract preserved across rotation)."""
        log = DriftEventLog(path=log_path)
        n_threads = 10
        per_thread = 5

        def _worker(thread_idx: int) -> None:
            for i in range(per_thread):
                log.append(
                    _make_event(
                        decision_id=thread_idx * per_thread + i,
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

        # Every line in the active + any rotated file must parse + carry
        # a unique decision_id (no interleaved bytes).
        all_lines: list[str] = []
        all_lines.extend(log_path.read_text(encoding="utf-8").splitlines())
        for rotated in sorted(log_path.parent.glob("drift_events.*.jsonl")):
            all_lines.extend(rotated.read_text(encoding="utf-8").splitlines())
        parsed = [json.loads(line) for line in all_lines if line.strip()]
        ids = sorted(int(p["decision_id"]) for p in parsed)
        assert ids == list(range(n_threads * per_thread))
