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

    def test_drift_event_log_creates_parent_dirs(self, tmp_path: Path) -> None:
        """A nested parent path (missing intermediate dirs) is auto-created."""
        nested = tmp_path / "deep" / "nested" / "drift_events.jsonl"
        log = DriftEventLog(path=nested)

        log.append(_make_event())

        assert nested.exists()


# ---------- append() + read_all() round-trip ----------


class TestAppendMultipleEvents:
    """Multiple appends write one JSONL line per event in order."""

    def test_drift_event_log_appends_multiple_events_as_jsonl(self, log_path: Path) -> None:
        """Three appends produce exactly three lines, no overwrites."""
        log = DriftEventLog(path=log_path)
        events = [_make_event(decision_id=i, binding_id=f"obs-{i}") for i in range(3)]

        for ev in events:
            log.append(ev)

        content = log_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        assert len(lines) == 3
        for ev, raw in zip(events, lines, strict=False):
            assert json.loads(raw) == ev.to_json_dict()

    def test_drift_event_log_read_all_returns_events_in_order(self, log_path: Path) -> None:
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
        for got, want in zip(result, events, strict=False):
            assert got == want

    def test_drift_event_log_read_all_skips_malformed_lines(self, log_path: Path) -> None:
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

    def test_drift_event_log_read_all_on_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """``read_all()`` returns ``[]`` when the JSONL file does not exist."""
        log = DriftEventLog(path=tmp_path / "nope.jsonl")

        assert log.read_all() == []


# ---------- REQ-V1.1.2: legacy coercion shim REMOVED ----------


class TestReadAllLegacyCoercion:
    """REQ-V1.1.2 S2 hardening: the v1.0 D2 defensive coercion shim was
    REMOVED. Legacy ``decision_id: "42"`` (str) lines now raise
    :class:`DriftEventLogLegacyFormatError`. The CLI catches per-line.

    The v1.0 tests that asserted silent coercion are REPLACED with v1.1
    tests asserting the new error semantics. See TestReadAllLegacyFormat
    above for the comprehensive 4-test class.
    """

    def test_read_all_no_longer_coerces_legacy_str_silently(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A legacy JSONL line with str decision_id RAISES (was: silent coercion)."""
        from flow_engineering.drift_event_log import (
            DriftEventLogLegacyFormatError,
        )

        log_path = tmp_path / "drift_events.jsonl"
        legacy_line = json.dumps(
            {
                "change": "x",
                "decision_id": "42",
                "binding_id": "y",
                "class": "z",
                "detected_at": 1_710_000_000.0,
            }
        )
        log_path.write_text(legacy_line + "\n", encoding="utf-8")
        log = DriftEventLog(path=log_path)

        with pytest.raises(DriftEventLogLegacyFormatError):
            log.read_all()
        # No stderr WARN emitted (the v1.0 one-time WARN cadence is gone).
        stderr = capsys.readouterr().err
        assert "legacy str decision_id" not in stderr

    def test_read_all_non_numeric_legacy_str_also_raises(self, tmp_path: Path) -> None:
        """A non-numeric legacy str decision_id RAISES too (v1.0 silently skipped)."""
        from flow_engineering.drift_event_log import (
            DriftEventLogLegacyFormatError,
        )

        log_path = tmp_path / "drift_events.jsonl"
        legacy_line = json.dumps(
            {
                "change": "x",
                "decision_id": "not-a-number",
                "binding_id": "y",
                "class": "z",
                "detected_at": 1_710_000_000.0,
            }
        )
        log_path.write_text(legacy_line + "\n", encoding="utf-8")
        log = DriftEventLog(path=log_path)

        with pytest.raises(DriftEventLogLegacyFormatError):
            log.read_all()

    def test_read_all_v10_int_lines_still_parse(self, tmp_path: Path) -> None:
        """v1.0-compliant int decision_id lines continue to parse unchanged."""
        log_path = tmp_path / "drift_events.jsonl"
        lines = []
        for i in range(3):
            lines.append(
                json.dumps(
                    {
                        "change": "x",
                        "decision_id": i + 100,
                        "binding_id": f"y{i}",
                        "class": "z",
                        "detected_at": 1_710_000_000.0 + i,
                    }
                )
            )
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log = DriftEventLog(path=log_path)

        events = log.read_all()

        # All 3 events read back as int — no regression for v1.0 sinks.
        assert len(events) == 3
        assert [ev.decision_id for ev in events] == [100, 101, 102]


# ---------- thread safety via portable file lock ----------


class TestThreadSafety:
    """The append writer MUST use a file lock so concurrent appends do not
    interleave bytes (D11 — file lock + flush for thread safety)."""

    def test_drift_event_log_thread_safety_uses_flock(self, log_path: Path) -> None:
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

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(n_threads)]
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


# ---------- REQ-V1.1.2: S2 hardening (drop defensive coercion shim) ----------


class TestReadAllLegacyFormat:
    """REQ-V1.1.2: legacy ``decision_id: "42"`` (str) lines raise
    ``DriftEventLogLegacyFormatError`` instead of being silently coerced.

    The v1.0 D2 defensive coercion shim (``_legacy_warn_emitted`` flag +
    ``try/except`` block + per-instance one-time stderr WARN) is REMOVED
    in v1.1. Legacy lines now raise a NEW exception that inherits from
    ``ValueError``. The read-side CLI catches it per-line: default mode
    skips + emits a stderr WARN per batch; ``--strict`` mode aborts on
    first legacy line.
    """

    def test_legacy_str_decision_id_raises_legacy_format_error(self, tmp_path: Path) -> None:
        """A legacy str decision_id line raises DriftEventLogLegacyFormatError (T2.1 RED)."""
        from flow_engineering.drift_event_log import (
            DriftEventLogLegacyFormatError,
        )

        log_path = tmp_path / "drift_events.jsonl"
        legacy_line = json.dumps(
            {
                "change": "x",
                "decision_id": "42",
                "binding_id": "y",
                "class": "z",
                "detected_at": 1_710_000_000.0,
            }
        )
        log_path.write_text(legacy_line + "\n", encoding="utf-8")
        log = DriftEventLog(path=log_path)

        with pytest.raises(DriftEventLogLegacyFormatError):
            log.read_all()

    def test_legacy_format_error_inherits_value_error(self) -> None:
        """``DriftEventLogLegacyFormatError`` inherits from ``ValueError``
        so external ``except ValueError:`` blocks continue to catch it."""
        from flow_engineering.drift_event_log import (
            DriftEventLogLegacyFormatError,
        )

        assert issubclass(DriftEventLogLegacyFormatError, ValueError)

    def test_legacy_lines_remain_skippable_via_caller_catch(self, tmp_path: Path) -> None:
        """Read-side callers can ``except DriftEventLogLegacyFormatError``
        to keep the best-effort sink ethos (T2.4 contract)."""
        from flow_engineering.drift_event_log import (
            DriftEventLogLegacyFormatError,
        )

        log_path = tmp_path / "drift_events.jsonl"
        legacy = json.dumps(
            {
                "change": "x",
                "decision_id": "42",
                "binding_id": "y",
                "class": "z",
                "detected_at": 1_710_000_000.0,
            }
        )
        log_path.write_text(legacy + "\n", encoding="utf-8")
        log = DriftEventLog(path=log_path)

        caught: list[DriftEventLogLegacyFormatError] = []
        try:
            log.read_all()
        except DriftEventLogLegacyFormatError as exc:
            caught.append(exc)
        assert len(caught) == 1
        assert "sed migration" in str(caught[0]) or "legacy" in str(caught[0])

    def test_legacy_warn_emitted_flag_removed(self) -> None:
        """The v1.0 per-instance ``_legacy_warn_emitted`` flag is REMOVED."""
        log = DriftEventLog(path=Path("/tmp/missing.jsonl"))
        assert not hasattr(log, "_legacy_warn_emitted"), (
            "v1.0 _legacy_warn_emitted flag should be removed in v1.1"
        )


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

    def test_rotates_at_max_bytes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        assert len(rotated) == 1, f"expected exactly 1 rotated file; got {rotated}"
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
        assert rotated == [], f"unexpected rotated files below threshold: {rotated}"
        # The active file contains all 3 events.
        lines = log_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3

    def test_rotates_when_env_var_overrides(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lowering ``FLOW_DRIFT_EVENT_LOG_MAX_BYTES`` triggers rotation sooner."""
        log_path = tmp_path / "drift_events.jsonl"
        # Set a tiny 100-byte threshold — a single DriftEvent serializes
        # to ~88 bytes; the second append pushes the file over 100 bytes
        # so the third append must rotate.
        monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_BYTES", "100")
        monkeypatch.setenv("FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS", "30")

        log = DriftEventLog(path=log_path)
        for i in range(5):
            log.append(_make_event(decision_id=i))

        # At least one rotated file should exist after 5 appends.
        rotated = sorted(tmp_path.glob("drift_events.*.jsonl"))
        assert len(rotated) >= 1, f"expected at least 1 rotated file; got {rotated}"

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

        assert not old_rotated.exists(), "old rotated file should have been deleted on next append"

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

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(n_threads)]
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
