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

REQ-8 close in PR#2 batch 2 adds:
- ``inspect_invoked_total`` -- one event per ``flow inspect`` call.
- ``inspect_render_ms`` -- one event per render with ``elapsed_ms`` field.
- ``backfill_observations_total`` -- total observations scanned for coverage.
- ``backfill_with_refs_total`` -- observations that carry ``source: backfill``.

REQ-22 (vector-semantic-search PR#1 T1.7) adds six ``vector_*`` counters:
- ``vector_search_invoked_total`` (tagged ``trigger=cli|programmatic``)
- ``vector_search_results_returned_total``
- ``vector_search_latency_ms`` (histogram via per-event ``elapsed_ms``)
- ``vector_index_size_observations`` (gauge)
- ``reindex_observations_total``
- ``reindex_duration_seconds``

The naming follows the REQ-8 convention: ``_total`` suffix for counters,
``_ms`` / ``_seconds`` suffix for timing, no suffix on gauges. A change that
renames any of these would silently break ``flow metrics`` consumers across
the decision-code-linking → vector-semantic-search boundary, so the names are
exposed via :data:`VECTOR_COUNTER_NAMES` for downstream discovery.

Plus the helper ``backfill_coverage(backend)`` that returns the ratio of
backfilled observations to total observations (rounded to 3 decimals),
and ``record_backfill_coverage(observations_total, with_refs)`` that
increments the two coverage counters in a single call.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

DEFAULT_METRICS_DIR: Path = Path.home() / ".flow-engineering"
DEFAULT_METRICS_FILE: str = "metrics.jsonl"
METRICS_PATH_ENV: str = "FLOW_METRICS_PATH"

_DEFAULT_PATH: Path = DEFAULT_METRICS_DIR / DEFAULT_METRICS_FILE

# REQ-8 close (PR#2 batch 2): stale threshold for freshness rendering.
STALE_DAYS_THRESHOLD: int = 30


# ---------- REQ-22 vector counter catalog ----------


VECTOR_COUNTER_NAMES: list[str] = [
    "vector_search_invoked_total",
    "vector_search_results_returned_total",
    "vector_search_latency_ms",
    "vector_index_size_observations",
    "reindex_observations_total",
    "reindex_duration_seconds",
]
"""Canonical list of REQ-22 vector counter names (REQ-22 scenario 4 contract).

The list is the single source of truth for ``flow metrics`` consumers and
for future changes that add to the catalog. The order matches the table in
``openspec/changes/vector-semantic-search/spec.md`` REQ-22.
"""

if TYPE_CHECKING:
    from flow_engineering.engram_io import EngramBackend


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
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    return


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


# ---------- Derived helpers (REQ-8 close, PR#2 batch 2) ----------


def _extract_block_source(content: str) -> str | None:
    """Return the ``source`` field from the trailing code_refs block.

    Returns ``None`` when the marker is absent or the block is malformed.
    Defensive: this is called by ``backfill_coverage`` which iterates the
    whole observation set, so any single bad row MUST NOT poison the scan.
    """
    from flow_engineering.binding import CODE_REFS_MARKER

    marker_idx = content.rfind(CODE_REFS_MARKER)
    if marker_idx < 0:
        return None
    body = content[marker_idx + len(CODE_REFS_MARKER):].strip()
    if not body:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    source = payload.get("source")
    return source if isinstance(source, str) else None


def backfill_coverage(backend: EngramBackend) -> float:
    """Return the ratio of backfill-sourced observations to total observations.

    The scan iterates every observation the backend exposes via
    ``iter_observations()`` and counts those whose trailing ``code_refs``
    block carries ``source: backfill``. Malformed blocks are skipped
    (fail-open). The result is rounded to 3 decimal places.

    Returns ``0.0`` when no observations exist.
    """
    observations = backend.iter_observations()
    if not observations:
        return 0.0
    total = len(observations)
    with_refs = sum(
        1 for o in observations if _extract_block_source(str(o.get("content", ""))) == "backfill"
    )
    return round(with_refs / total, 3)


def record_backfill_coverage(*, observations_total: int, with_refs: int) -> None:
    """Increment the two backfill-coverage counters in one call."""
    increment("backfill_observations_total", count=observations_total)
    increment("backfill_with_refs_total", count=with_refs)


# ---------- Freshness helpers (REQ-7) ----------


def _format_age(elapsed_ms: int) -> str:
    """Render an age in milliseconds as a short human string.

    Examples: ``"12m ago"``, ``"3d ago"``, ``"60d ago (stale)"``.
    """
    seconds = max(0, elapsed_ms) // 1000
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    suffix = " (stale)" if days > STALE_DAYS_THRESHOLD else ""
    return f"{days}d ago{suffix}"


def compute_freshness(updated_at_ms: int | None, *, now_ms: int | None = None) -> str:
    """Return the freshness label for an observation's ``updated_at``.

    Returns ``"never"`` when ``updated_at_ms`` is missing or non-positive.
    The label is short (``"5d ago"``, ``"60d ago (stale)"``) so it fits the
    inspect table column.
    """
    if updated_at_ms is None or updated_at_ms <= 0:
        return "never"
    if now_ms is None:
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
    return _format_age(now_ms - updated_at_ms)


# ---------- Drift summary (REQ-12, PR#1 batch 1) ----------


def record_drift_summary(report: "DriftReport") -> None:
    """Increment 8 drift counters from a ``DriftReport`` (REQ-12).

    Emits one JSONL line per counter; counts of zero for absent classes
    are still emitted so the sink captures a complete snapshot per
    ``flow drift`` invocation. The helper is fail-open (mirrors
    ``increment``) and never raises.

    Counters:
    - ``drift_invoked_total``           — one per scan, tagged with the change.
    - ``drift_still_valid_total``       — bindings classified STILL_VALID.
    - ``drift_label_drift_total``       — LABEL_DRIFT count.
    - ``drift_stale_location_total``    — STALE_LOCATION count.
    - ``drift_stale_id_total``          — STALE_ID count.
    - ``drift_obsolete_total``          — OBSOLETE count.
    - ``drift_contradicted_total``      — CONTRADICTED count.
    - ``drift_unable_to_verify_total``  — 1 when ``graph_unavailable`` else 0.

    The ``drift_unable_to_verify_total`` counter was missing from the
    PR#1 implementation (only 7 counters were emitted); PR#2 batch G
    adds it so the REQ-12 contract is complete and the missing-graph
    BDD scenario can assert counter increments.
    """
    from flow_engineering.decision_drift import DriftClass

    counts = report.class_counts
    increment("drift_invoked_total", change=report.change_name)
    increment("drift_still_valid_total", count=counts.get(DriftClass.STILL_VALID, 0))
    increment("drift_label_drift_total", count=counts.get(DriftClass.LABEL_DRIFT, 0))
    increment("drift_stale_location_total", count=counts.get(DriftClass.STALE_LOCATION, 0))
    increment("drift_stale_id_total", count=counts.get(DriftClass.STALE_ID, 0))
    increment("drift_obsolete_total", count=counts.get(DriftClass.OBSOLETE, 0))
    increment("drift_contradicted_total", count=counts.get(DriftClass.CONTRADICTED, 0))
    increment(
        "drift_unable_to_verify_total",
        count=1 if report.graph_unavailable else 0,
    )


# ---------- Vector summary (REQ-22) ----------


#: Valid ``trigger`` values for ``vector_search_invoked_total`` events.
VECTOR_TRIGGER_VALUES: frozenset[str] = frozenset({"cli", "programmatic"})


def record_vector_summary(
    *,
    invoked: int,
    results_returned: int,
    latency_ms: int,
    index_size: int,
    trigger: str,
    reindex_observations: int | None = None,
    reindex_duration_seconds: float | None = None,
) -> None:
    """Emit the REQ-22 vector metrics in a single call (parallels ``record_drift_summary``).

    Always emits the four search-related counters:
    - ``vector_search_invoked_total{trigger=<cli|programmatic>}``
    - ``vector_search_results_returned_total``
    - ``vector_search_latency_ms`` with ``elapsed_ms`` field
    - ``vector_index_size_observations`` with ``value`` field

    Additionally emits the two reindex counters when ``reindex_observations``
    is provided (callers that wrap a ``flow reindex`` invocation pass this):
    - ``reindex_observations_total`` with ``count`` field
    - ``reindex_duration_seconds`` with ``value`` field

    Defensive: negative numeric inputs are clamped to 0 so a bad latency
    sample cannot produce NaN / negative JSON values. Invalid ``trigger``
    values fall back to ``"programmatic"`` so the catalog invariant holds.
    Failures are absorbed by :func:`increment` — this helper never raises.
    """
    safe_invoked = max(0, int(invoked))
    safe_results = max(0, int(results_returned))
    safe_latency = max(0, int(latency_ms))
    safe_index_size = max(0, int(index_size))
    safe_trigger = trigger if trigger in VECTOR_TRIGGER_VALUES else "programmatic"

    increment("vector_search_invoked_total", count=safe_invoked, trigger=safe_trigger)
    increment("vector_search_results_returned_total", count=safe_results)
    increment("vector_search_latency_ms", elapsed_ms=safe_latency)
    increment("vector_index_size_observations", value=safe_index_size)

    if reindex_observations is not None:
        increment(
            "reindex_observations_total",
            count=max(0, int(reindex_observations)),
        )
    if reindex_duration_seconds is not None:
        increment(
            "reindex_duration_seconds",
            value=max(0.0, float(reindex_duration_seconds)),
        )
