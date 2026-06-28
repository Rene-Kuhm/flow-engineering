"""JSONL append-only event log writer for drift events (REQ-55).

Each finding emitted by ``daemon.handle_apply_progress_event`` is appended as
one JSONL line to ``~/.flow-engineering/drift_events.jsonl``. Per the
decision-reality-drift REQ-15 spec, the JSONL wire format contains the
keys: ``change``, ``decision_id``, ``binding_id``, ``class``,
``detected_at`` (note: the Python dataclass uses ``event_class`` but
the JSON wire key is ``class`` per the archived spec — Python reserved
word is avoided at the type level only).

Per design D11, the writer assumes a single-process Python watchdog
loop and uses a ``threading.Lock`` to guard in-process concurrent
appends from interleaving bytes. The design explicitly says NO OS-level
file lock — the daemon is single-threaded per-process, and the lock is
a defensive guard for accidental multi-thread callers. v1 ships without
rotation (D3); rotation is deferred alongside the metrics rotation
follow-up (REQ-44 → v1.1).
"""
from __future__ import annotations

import json
import os
import sys
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DRIFT_EVENT_LOG_PATH: Path = (
    Path.home() / ".flow-engineering" / "drift_events.jsonl"
)

ROTATE_BYTES_DEFAULT: int = 10 * 1024 * 1024
"""Default size threshold for ``DriftEventLog`` rotation (REQ-V1.1.1).

Mirrors the never-shipped ``metrics.jsonl`` rotation policy at REQ-44.
Override at runtime via ``FLOW_DRIFT_EVENT_LOG_MAX_BYTES`` env var; set to
``0`` to disable size-based rotation entirely.
"""

ROTATE_AGE_DAYS_DEFAULT: int = 30
"""Default age threshold (days) for deleting rotated ``DriftEventLog``
files (REQ-V1.1.1). Override via ``FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS``;
set to ``0`` to disable age-based cleanup entirely.
"""


@dataclass(frozen=True)
class DriftEvent:
    """One drift event line for JSONL append.

    Attributes:
        change: The change name (e.g., ``"decision-reality-drift"``).
        decision_id: The decision ID (int per v1.0; matches
            ``Finding.decision_id: int`` post-v0.9.0).
        binding_id: The binding identifier.
        event_class: Drift class (e.g., ``"label_drift"``,
            ``"stale_location"``, ``"stale_id"``).
        detected_at: Epoch seconds (float) per D7 deviation note.
    """

    change: str
    decision_id: int  # REQ-V1.0.1: int (was str pre-v1.0); matches Finding.decision_id post-v0.9.0
    binding_id: str
    event_class: str
    detected_at: float

    def __post_init__(self) -> None:
        # REQ-V1.0.1 hard break: enforce int decision_id at the dataclass
        # boundary (mirrors Finding.__post_init__ at decision_drift.py:84-90).
        # bool is rejected because it is an int subclass; the legacy "42"
        # str form is rejected because the wire format now matches the
        # Python int contract (single source of truth per D1).
        if not isinstance(self.decision_id, int) or isinstance(self.decision_id, bool):
            raise TypeError(
                f"DriftEvent.decision_id must be int, got {type(self.decision_id).__name__}"
            )

    def to_json_dict(self) -> dict[str, Any]:
        """Return the JSON wire dict with the spec schema (``class`` key)."""
        return {
            "change": self.change,
            "decision_id": self.decision_id,
            "binding_id": self.binding_id,
            "class": self.event_class,
            "detected_at": self.detected_at,
        }


class DriftEventLog:
    """Append-only JSONL writer with in-process thread safety (D11).

    Usage::

        log = DriftEventLog()
        log.append(DriftEvent(change="decision-reality-drift", ...))
        events = log.read_all()
    """

    def __init__(self, path: Path | None = None) -> None:
        # Resolve the default lazily so tests can monkeypatch
        # ``DEFAULT_DRIFT_EVENT_LOG_PATH`` at the module level and have
        # ``DriftEventLog()`` pick up the patched value at construction
        # time (function default values are bound at def-time).
        self.path: Path = path if path is not None else DEFAULT_DRIFT_EVENT_LOG_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # REQ-V1.0.1 D2: per-instance flag for one-time stderr WARN cadence.
        # Per-instance (not module-global) so multi-log CLI invocations each
        # get their own WARN (correct cadence).
        self._legacy_warn_emitted: bool = False

    def append(self, event: DriftEvent) -> None:
        """Append one event as a single JSONL line under an in-process lock.

        Per design D11 the lock is ``threading.Lock`` (NOT an OS-level
        file lock). The daemon is a single-process watchdog loop; the
        lock guards against accidental multi-thread callers within the
        process. ``flush`` ensures bytes reach the OS buffer before the
        lock is released so a subsequent crash does not lose the line.

        REQ-V1.1.1: the rotation helper runs INSIDE the lock so the
        rename + the next ``open("a")`` see a consistent filesystem
        state. Rotation is best-effort — a slow rename on a network FS
        never crashes the daemon (``try/except OSError`` swallow).
        """
        line = json.dumps(event.to_json_dict(), ensure_ascii=False) + "\n"
        with self._lock:
            _rotate_if_needed(self.path)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()

    def read_all(self) -> list[DriftEvent]:
        """Return all events from the JSONL file in append order.

        Missing file returns ``[]``; malformed lines are silently
        skipped (the sink is best-effort — partial writes on disk
        full must NOT crash the caller).

        REQ-V1.0.1 D2: legacy ``decision_id: "42"`` (str) lines from
        pre-v1.0 JSONL files are coerced to ``int`` with a one-time
        stderr WARN per log-path (per-instance flag; not module-global).
        Operators may run the CHANGELOG v1.0 ``sed`` migration to
        convert in place and silence the WARN.
        """
        if not self.path.exists():
            return []
        events: list[DriftEvent] = []
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
                # Wire format uses ``class`` (matches the archived spec);
                # the Python dataclass field is ``event_class`` to avoid
                # the reserved word. Remap on read.
                if "class" in data and "event_class" not in data:
                    data["event_class"] = data.pop("class")
                # REQ-V1.0.1 D2: defensive coercion for legacy str decision_id.
                if isinstance(data.get("decision_id"), str):
                    data["decision_id"] = int(data["decision_id"])
                    if not self._legacy_warn_emitted:
                        print(
                            f"warning: legacy str decision_id in {self.path}; "
                            "coercing to int. Run the CHANGELOG v1.0 sed "
                            "migration to silence.",
                            file=sys.stderr,
                        )
                        self._legacy_warn_emitted = True
                events.append(DriftEvent(**data))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return events


__all__ = [
    "DEFAULT_DRIFT_EVENT_LOG_PATH",
    "DriftEvent",
    "DriftEventLog",
    "ROTATE_AGE_DAYS_DEFAULT",
    "ROTATE_BYTES_DEFAULT",
]


def _resolve_rotation_threshold_bytes() -> int:
    """Read ``FLOW_DRIFT_EVENT_LOG_MAX_BYTES`` (0 = disable)."""
    raw = os.environ.get("FLOW_DRIFT_EVENT_LOG_MAX_BYTES")
    if raw is None or raw == "":
        return ROTATE_BYTES_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        return ROTATE_BYTES_DEFAULT
    return max(0, value)


def _resolve_max_age_days() -> int:
    """Read ``FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS`` (0 = disable)."""
    raw = os.environ.get("FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS")
    if raw is None or raw == "":
        return ROTATE_AGE_DAYS_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        return ROTATE_AGE_DAYS_DEFAULT
    return max(0, value)


def _rotate_if_needed(path: Path) -> None:
    """Rotate ``path`` when its size meets the configured threshold (REQ-V1.1.1).

    Behaviour:
    - If ``path.stat().st_size >= FLOW_DRIFT_EVENT_LOG_MAX_BYTES`` (default 10 MB),
      rename ``path`` to ``drift_events.<ISO-no-colons>.jsonl`` so the
      next append creates a fresh active file.
    - Walk sibling files matching ``drift_events.*.jsonl`` and delete
      any whose mtime is older than ``FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS``
      (default 30 days).
    - All filesystem operations are wrapped in ``try/except OSError`` so
      a slow rename on a network filesystem never crashes the daemon.
    """
    threshold = _resolve_rotation_threshold_bytes()
    if threshold > 0 and path.exists():
        try:
            if path.stat().st_size >= threshold:
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                rotated = path.with_name(f"drift_events.{stamp}.jsonl")
                path.rename(rotated)
        except OSError:
            pass

    max_age_days = _resolve_max_age_days()
    if max_age_days <= 0:
        return
    cutoff = datetime.now(UTC).timestamp() - (max_age_days * 86400)
    parent = path.parent
    for sibling in parent.glob("drift_events.*.jsonl"):
        if sibling == path:
            continue
        try:
            if sibling.stat().st_mtime < cutoff:
                sibling.unlink()
        except OSError:
            pass
