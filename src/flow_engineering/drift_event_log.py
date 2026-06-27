"""JSONL append-only event log writer for drift events (REQ-55).

Each finding emitted by ``daemon.handle_apply_progress_event`` is appended as
one JSONL line to ``~/.flow-engineering/drift_events.jsonl``. Per the
decision-reality-drift REQ-15 spec, the JSONL line contains the keys:
``change``, ``decision_id``, ``binding_id``, ``event_class``,
``detected_at``.

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
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_DRIFT_EVENT_LOG_PATH: Path = (
    Path.home() / ".flow-engineering" / "drift_events.jsonl"
)


@dataclass(frozen=True)
class DriftEvent:
    """One drift event line for JSONL append.

    Attributes:
        change: The change name (e.g., ``"decision-reality-drift"``).
        decision_id: The decision ID (string per pre-v0.8.0).
        binding_id: The binding identifier.
        event_class: Drift class (e.g., ``"label_drift"``,
            ``"stale_location"``, ``"stale_id"``).
        detected_at: Epoch seconds (float) per D7 deviation note.
    """

    change: str
    decision_id: str
    binding_id: str
    event_class: str
    detected_at: float


class DriftEventLog:
    """Append-only JSONL writer with in-process thread safety (D11).

    Usage::

        log = DriftEventLog()
        log.append(DriftEvent(change="decision-reality-drift", ...))
        events = log.read_all()
    """

    def __init__(self, path: Path = DEFAULT_DRIFT_EVENT_LOG_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, event: DriftEvent) -> None:
        """Append one event as a single JSONL line under an in-process lock.

        Per design D11 the lock is ``threading.Lock`` (NOT an OS-level
        file lock). The daemon is a single-process watchdog loop; the
        lock guards against accidental multi-thread callers within the
        process. ``flush`` ensures bytes reach the OS buffer before the
        lock is released so a subsequent crash does not lose the line.
        """
        line = json.dumps(asdict(event), ensure_ascii=False) + "\n"
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()

    def read_all(self) -> list[DriftEvent]:
        """Return all events from the JSONL file in append order.

        Missing file returns ``[]``; malformed lines are silently
        skipped (the sink is best-effort — partial writes on disk
        full must NOT crash the caller).
        """
        if not self.path.exists():
            return []
        events: list[DriftEvent] = []
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                events.append(DriftEvent(**json.loads(raw)))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        return events


__all__ = [
    "DEFAULT_DRIFT_EVENT_LOG_PATH",
    "DriftEvent",
    "DriftEventLog",
]
