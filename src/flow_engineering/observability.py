"""JSONL counter sink for decision-code-linking observability (REQ-8 shared).

REQ-8 (PR#2 batch 1 + 2): a tiny append-only JSONL sink records auto-suggest
events without adding a metrics dependency. The default path is
``~/.flow-engineering/metrics.jsonl``; the ``FLOW_METRICS_PATH`` environment
variable overrides it for tests.

Counters used by REQ-6 (PR#2 batch 1):
- ``suggest_invoked_total`` -- incremented once per auto-suggest call.
- ``suggest_hit_total`` -- incremented when at least one binding is confirmed.
- ``suggest_miss_total`` -- incremented when no binding is confirmed (rejected
  or no candidates cleared the threshold).
- ``bindings_confirmed_total`` -- incremented by the count of confirmed bindings
  (so a batch of 3 confirmations contributes 3 to the total).

REQ-8 closure in PR#2 batch 2 will add derived counters (``manual_count``,
``avg_bindings_per_observation``, ``backfill_coverage``) on top of this sink.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_METRICS_DIR: Path = Path.home() / ".flow-engineering"
DEFAULT_METRICS_FILE: str = "metrics.jsonl"
METRICS_PATH_ENV: str = "FLOW_METRICS_PATH"

_DEFAULT_PATH: Path = DEFAULT_METRICS_DIR / DEFAULT_METRICS_FILE


def default_metrics_path() -> Path:
    """Return the production default metrics path.

    The default is ``~/.flow-engineering/metrics.jsonl``; tests override via
    ``FLOW_METRICS_PATH``.
    """
    return _DEFAULT_PATH


def _resolve_path() -> Path:
    """Resolve the metrics sink path: env override wins over default."""
    env = os.environ.get(METRICS_PATH_ENV)
    if env:
        return Path(env)
    return default_metrics_path()


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string with a 'Z' suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def increment(name: str, **fields: Any) -> None:
    """Append a counter increment to the JSONL sink.

    Each call appends exactly one line of the form
    ``{"name": "<name>", "fields": {<fields>}, "ts": "<ISO 8601 UTC>"}``.

    The parent directory is created on demand. The function never raises:
    any unexpected ``OSError`` is swallowed (the counter is best-effort).
    """
    path = _resolve_path()
    event = {"name": name, "fields": fields, "ts": _now_iso()}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")
    except OSError:
        # Best-effort counter. Failing to write MUST NOT break the save flow.
        return


def flush() -> None:
    """Flush any buffered writes.

    The current implementation appends synchronously per ``increment`` call,
    so this is a no-op reserved for future buffered writers. Kept as part
    of the public contract so callers can insert it before exit.
    """
    return None


def read_all(path: Path | None = None) -> list[dict[str, Any]]:
    """Return every recorded event as a list of dicts.

    When ``path`` is omitted, the resolved sink path is used. Missing files
    yield an empty list. Malformed lines are skipped (defensive: the sink
    is best-effort and must not blow up test collection).
    """
    target = path or _resolve_path()
    if not target.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events