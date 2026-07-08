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
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flow_engineering._jsonl_rotation import _rotate_jsonl_if_needed

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


class DriftEventLogLegacyFormatError(ValueError):
    """Raised when ``DriftEventLog.read_all()`` encounters a legacy ``str`` decision_id.

    REQ-V1.1.2 S2 hardening: the v1.0 D2 defensive coercion shim has been
    REMOVED. Pre-v1.0 JSONL lines with ``"decision_id": "42"`` (str) now
    raise this exception per-line. Inherits from ``ValueError`` so any
    external ``except ValueError:`` block continues to catch it.

    The ``flow drift-events {list,tail,stats}`` CLI catches this per-line:
    default mode skips the line + emits a stderr WARN per batch summary;
    ``--strict`` mode aborts on first legacy line with the CHANGELOG v1.0
    ``sed`` migration hint. Operators who already ran the CHANGELOG v1.0
    migration are unaffected (their sinks are already int-only).
    """


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
            _rotate_jsonl_if_needed(
                self.path,
                glob_prefix="drift_events",
                max_bytes_env="FLOW_DRIFT_EVENT_LOG_MAX_BYTES",
                max_age_days_env="FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS",
                default_max_bytes=ROTATE_BYTES_DEFAULT,
                default_max_age_days=ROTATE_AGE_DAYS_DEFAULT,
            )
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()

    def read_all(self) -> list[DriftEvent]:
        """Return all events from the JSONL file in append order.

        Missing file returns ``[]``; malformed JSONL lines are silently
        skipped (the sink is best-effort — partial writes on disk
        full must NOT crash the caller).

        REQ-V1.1.2 S2 hardening: legacy ``decision_id: "42"`` (str) lines
        from pre-v1.0 JSONL files now raise
        :class:`DriftEventLogLegacyFormatError`. The v1.0 D2 defensive
        coercion shim has been REMOVED. The ``flow drift-events``
        read-side CLI catches the exception per-line and either skips +
        WARNs (default mode) or aborts with the CHANGELOG v1.0 ``sed``
        migration hint (``--strict`` mode).
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
                if isinstance(data.get("decision_id"), str):
                    raise DriftEventLogLegacyFormatError(
                        f"legacy str decision_id in {self.path}; "
                        "run the CHANGELOG v1.0 sed migration to convert in place."
                    )
                events.append(DriftEvent(**data))
            except json.JSONDecodeError:
                continue
        return events


__all__ = [
    "DEFAULT_DRIFT_EVENT_LOG_PATH",
    "DriftEvent",
    "DriftEventLog",
    "DriftEventLogLegacyFormatError",
    "ROTATE_AGE_DAYS_DEFAULT",
    "ROTATE_BYTES_DEFAULT",
]
