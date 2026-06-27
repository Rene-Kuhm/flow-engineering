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

REQ-26 (cross-project-federation PR#1 T1.8) adds three ``federated_*`` counters:
- ``federated_search_invoked_total`` (tagged ``trigger=cli|programmatic``)
- ``federated_search_projects_queried`` (histogram — NO ``_total`` suffix because
  the value IS the count; one event per call with ``count=<N>``)
- ``federated_search_results_returned_total``

REQ-26 (graph-snapshots change #5 batch C T1.7) adds four ``snapshot_*`` counters:
- ``snapshot_create_total`` — incremented by ``SnapshotManager.create()`` after
  a successful gzipped envelope write.
- ``snapshot_rollback_total`` — incremented by ``SnapshotManager.rollback()``;
  fires on success AND on conflict/refusal so the audit trail captures
  attempted rollbacks.
- ``snapshot_prune_total`` — incremented per deletion by
  ``SnapshotManager.prune()`` in apply mode (``confirm=True``); NOT fired
  in dry-run.
- ``snapshot_load_failed_total`` — incremented by
  ``decision_drift._load_graph_from_snapshot`` when the frozen graph cannot
  be loaded (drift-pinned scan unavailability, REQ-33 D2 graceful
  degradation).

The naming follows the REQ-8 convention: ``_total`` suffix for counters,
``_ms`` / ``_seconds`` suffix for timing, no suffix on gauges. A change that
renames any of these would silently break ``flow metrics`` consumers across
the decision-code-linking → vector-semantic-search → cross-project-federation
→ graph-snapshots boundary, so the names are exposed via
:data:`VECTOR_COUNTER_NAMES`, :data:`FEDERATED_COUNTER_NAMES`, and
:data:`SNAPSHOT_COUNTER_NAMES` for downstream discovery.

Plus the helper ``backfill_coverage(backend)`` that returns the ratio of
backfilled observations to total observations (rounded to 3 decimals),
and ``record_backfill_coverage(observations_total, with_refs)`` that
increments the two coverage counters in a single call.
"""

from __future__ import annotations

import json
import os
import tempfile
import time as _time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

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


# ---------- REQ-26 federated counter catalog ----------


FEDERATED_COUNTER_NAMES: list[str] = [
    "federated_search_invoked_total",
    "federated_search_projects_queried",
    "federated_search_results_returned_total",
]
"""Canonical list of REQ-26 federated counter names (REQ-26 scenario 4 contract).

Mirrors :data:`VECTOR_COUNTER_NAMES` (REQ-22). The histogram
``federated_search_projects_queried`` deliberately has NO ``_total`` suffix
because the value IS the count (design D4): per-call events with ``count=<N>``
build the per-call project-bucket histogram.
"""

if TYPE_CHECKING:
    from flow_engineering.engram_io import EngramBackend


# ---------- REQ-26 snapshot counter catalog ----------


SNAPSHOT_COUNTER_NAMES: tuple[str, ...] = (
    "snapshot_create_total",
    "snapshot_rollback_total",
    "snapshot_prune_total",
    "snapshot_load_failed_total",
)
"""Canonical list of REQ-26 snapshot counter names (REQ-26 scenario 4 contract).

Mirrors :data:`VECTOR_COUNTER_NAMES` (REQ-22) and
:data:`FEDERATED_COUNTER_NAMES` (REQ-26 federated). The tuple is the single
source of truth for ``flow metrics`` consumers and for future changes that
add to the catalog. The order matches the snapshot lifecycle:
create → rollback → prune → load-failed (audit trail).
"""


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


# ---------- Federated summary (REQ-26) ----------


#: Valid ``trigger`` values for ``federated_search_invoked_total`` events.
FEDERATED_TRIGGER_VALUES: frozenset[str] = frozenset({"cli", "programmatic"})


def record_federated_summary(
    *,
    invoked: int = 1,
    projects_queried: int | None,
    results_returned: int,
    trigger: str = "programmatic",
) -> None:
    """Emit the REQ-26 federated metrics in a single call (parallels ``record_vector_summary``).

    Always emits three counters:

    - ``federated_search_invoked_total{trigger=<cli|programmatic>}`` — counter,
      incremented by ``invoked`` per call (default 1).
    - ``federated_search_projects_queried`` — histogram with ``count=<N>``
      where ``N`` is the number of projects queried (``0`` when ``None``,
      modelling the search-all case). NO ``_total`` suffix because the
      value IS the count (design D4).
    - ``federated_search_results_returned_total`` — counter, ``count=<N>``
      where ``N`` is the number of rows returned.

    Defensive: negative numeric inputs are clamped to ``0`` so a bad sample
    cannot produce NaN / negative JSON values. Invalid ``trigger`` values
    fall back to ``"programmatic"`` so the catalog invariant holds.
    Failures are absorbed by :func:`increment` — this helper never raises.
    """
    safe_invoked = max(0, int(invoked))
    safe_results = max(0, int(results_returned))
    safe_projects = max(0, int(projects_queried)) if projects_queried is not None else 0
    safe_trigger = trigger if trigger in FEDERATED_TRIGGER_VALUES else "programmatic"

    increment(
        "federated_search_invoked_total",
        count=safe_invoked,
        trigger=safe_trigger,
    )
    increment("federated_search_projects_queried", count=safe_projects)
    increment("federated_search_results_returned_total", count=safe_results)


# ---------- Snapshot event helper (REQ-26 snapshot counters, graph-snapshots T1.7) ----------


def record_snapshot_event(counter_name: str, **labels: Any) -> None:
    """Append a snapshot counter increment to the JSONL sink (REQ-26 T1.7).

    Mirrors :func:`record_vector_summary` / :func:`record_drift_summary` /
    :func:`record_federated_summary` shape: each call appends exactly one
    JSONL line of the form
    ``{"name": "<counter_name>", "fields": {<labels>}, "ts": "<ISO 8601 UTC>"}``
    via :func:`increment`.

    Args:
        counter_name: One of :data:`SNAPSHOT_COUNTER_NAMES`. Callers MUST
            pass a name from the catalog so ``flow metrics`` consumers can
            rely on the contract. An unknown name is still emitted (the
            helper is fail-open), but production code paths always pass a
            catalog value.
        **labels: Optional label fields merged into the JSONL ``fields``
            object. When empty, the ``fields`` object is ``{}``.

    Notes:
        Defensive: never raises. Failures are absorbed by :func:`increment`
        which swallows ``OSError`` on the underlying file write.
    """
    increment(counter_name, **labels)


# ---------- Change #6 PR#1 T1.1: read-side observability helpers (REQ-35..39) ----------


DEFAULT_METRICS_PATH: Path = Path.home() / ".flow-engineering" / "metrics.jsonl"
"""Default metrics sink path used by read-side helpers when no explicit path is given.

Mirrors ``_DEFAULT_PATH`` (the write-side default) and ``read_all(path)`` behavior;
the value is overridable per-call via the ``path`` argument on each public helper.
"""


DOMAIN_BY_PREFIX: dict[str, str] = {
    # prefix -> domain
    "suggest_": "binding",        # REQ-8 close (auto_suggest_code_refs.py)
    "bindings_": "binding",       # REQ-8 close (auto_suggest_code_refs.py: note `bindings_` plural)
    "inspect_": "binding",        # REQ-8 close (cli.py:945-950)
    "backfill_": "backfill",      # REQ-8 close (backfill coverage)
    "drift_": "drift",            # REQ-12
    "vector_": "vector",          # REQ-22
    "reindex_": "vector",         # REQ-22 reindex counters
    "federated_": "federated",    # REQ-26 federated
    "snapshot_": "snapshot",      # REQ-26 snapshot (graph-snapshots)
    "update_observation_metadata_": "metadata",  # REQ-13 / REQ-24
    "project_tag_": "metadata",   # REQ-24
    "engine_": "engine",          # REQ-42 reserved (no v1 counters; v1.1 follow-up)
}
"""Prefix -> domain lookup table for change #6 read-side helpers (design D5).

Maps each counter-name prefix to its owning domain. Used by
:func:`summarize` (to group counters by domain) and by
:func:`read_events_by_domain` (inverse lookup: prefixes per domain).
Counter names that do NOT match any registered prefix fall into the
``"unknown"`` bucket per W23 dual-name history.

The binding domain carries THREE prefixes to match production counter
names per REQ-8 close + REQ-7: ``suggest_`` (auto-suggest invocation),
``bindings_`` (confirmed bindings — note the plural ``bindings_`` is the
canonical counter prefix; ``binding_`` singular would be a typo),
``inspect_`` (``flow inspect`` invocation + render time). C1 fix from
sdd-verify PR#1 — production emitted counters fall under binding only
when ALL three prefixes map here; without them, six production counters
land in the ``unknown`` bucket and the cross-domain dashboard misreports.

The 8 unique domain values (binding, backfill, drift, vector, federated,
snapshot, metadata, engine) are exported as :data:`ALL_DOMAINS` for
validation and CLI help-text rendering. The ``engine`` slot is RESERVED
for REQ-42 (``engine_*`` counters deferred to v1.1) — accepting the value
lets ``--domain=engine`` succeed with "no events matched" rather than
erroring.
"""


ALL_DOMAINS: tuple[str, ...] = (
    "binding",
    "backfill",
    "drift",
    "vector",
    "federated",
    "snapshot",
    "metadata",
    "engine",
)
"""Canonical list of accepted domain names for ``--domain=<D>`` filtering (REQ-37 / design D5).

The 8-value set covers the 7 active domains (each backed by at least one
prefix in :data:`DOMAIN_BY_PREFIX`) plus the reserved ``engine`` slot
(REQ-42 deferred to v1.1). Order is stable for CLI ``--help`` rendering
and for ``validate_domain`` error messages; case-sensitive.
"""


def validate_domain(domain: str) -> str:
    """Validate ``domain`` is an accepted domain name; return it unchanged.

    Returns the input ``domain`` string when it is one of the values in
    :data:`ALL_DOMAINS`. Raises :class:`ValueError` with a helpful message
    listing every valid domain otherwise — callers (e.g., the CLI) catch
    this and emit exit-code-2 per design D9 (usage error).

    Case-sensitive (mirrors ``click.Choice(ACCEPTED_DOMAINS)`` semantics):
    ``"Binding"`` is rejected. Callers that accept case-insensitive input
    MUST ``.lower()`` the value before calling.
    """
    if domain not in ALL_DOMAINS:
        raise ValueError(
            f"unknown domain {domain!r}; valid: {', '.join(ALL_DOMAINS)}"
        )
    return domain


@dataclass(frozen=True)
class MetricEvent:
    """One parsed line from the JSONL metrics sink (REQ-35 / change #6).

    Attributes:
        timestamp: Epoch seconds (float) parsed from the ISO-8601 ``ts`` field.
        counter_name: The ``name`` field of the event (e.g. ``"drift_invoked_total"``).
        labels: The ``fields`` dict (counter-specific labels / values).
        raw_line: The original JSON line as written to disk (for diagnostics).
    """

    timestamp: float
    counter_name: str
    labels: dict[str, Any]
    raw_line: str


def _domain_for_counter(counter_name: str) -> str:
    """Return the domain for a counter name via :data:`DOMAIN_BY_PREFIX`.

    Unknown prefixes map to ``"unknown"`` (W23 dual-name carry-forward).
    """
    # Longest-prefix match — preserves determinism if two prefixes ever
    # share a stem (e.g., ``update_observation_metadata_`` vs ``update_``).
    best: str | None = None
    for prefix, domain in DOMAIN_BY_PREFIX.items():
        if counter_name.startswith(prefix):
            if best is None or len(prefix) > len(best):
                best = prefix
    if best is None:
        return "unknown"
    return DOMAIN_BY_PREFIX[best]


def _prefixes_for_domain(domain: str) -> list[str]:
    """Return the registered prefixes for a domain (inverse of :data:`DOMAIN_BY_PREFIX`).

    Returns an empty list when the domain is not registered — callers raise
    ``ValueError`` to convert empty list into a user-facing error.
    """
    return [prefix for prefix, d in DOMAIN_BY_PREFIX.items() if d == domain]


def _read_metrics_file(path: Path) -> list[MetricEvent]:
    """Parse every line of the JSONL sink at ``path`` into :class:`MetricEvent` records.

    Returns ``[]`` when the file is missing. Malformed lines are silently
    skipped (best-effort sink contract per REQ-8).
    """
    if path is None or not path.exists():
        return []
    events: list[MetricEvent] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        name = payload.get("name")
        if not isinstance(name, str):
            continue
        ts_raw = payload.get("ts", "")
        fields = payload.get("fields") or {}
        try:
            ts_epoch = datetime.strptime(ts_raw, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=UTC
            ).timestamp()
        except (TypeError, ValueError):
            # Skip events with malformed timestamps (best-effort).
            continue
        events.append(
            MetricEvent(
                timestamp=ts_epoch,
                counter_name=name,
                labels=fields if isinstance(fields, dict) else {},
                raw_line=stripped,
            )
        )
    return events


def read_all_metrics(path: Path | None = None) -> list[MetricEvent]:
    """Return every parsed event in the JSONL sink as :class:`MetricEvent` records.

    Public alias for the read-side helper. When ``path`` is ``None``, the
    default sink path is used (overridable via the ``FLOW_METRICS_PATH`` env
    var for tests).

    Empty / missing sink → empty list (REQ-35 default-empty contract).
    Malformed lines are silently skipped.
    """
    target = path if path is not None else _resolve_path()
    return _read_metrics_file(target)


def read_events_since(since: float, path: Path | None = None) -> list[MetricEvent]:
    """Return events whose timestamp is ``>= since`` (epoch seconds).

    Used by the CLI ``--since`` / ``--until`` / ``--window`` flag pipeline.
    Lexicographic ISO-8601 comparison is replaced by epoch comparison
    (the source ISO strings are Z-suffixed UTC, so lex order == chronological).
    """
    events = read_all_metrics(path)
    return [e for e in events if e.timestamp >= since]


def read_events_by_domain(domain: str, path: Path | None = None) -> list[MetricEvent]:
    """Return events whose counter name starts with one of ``domain``'s registered prefixes.

    Raises ``ValueError`` when ``domain`` is not registered — the CLI catches
    this and emits an exit-2 error per design D9 (usage error).
    """
    prefixes = _prefixes_for_domain(domain)
    if not prefixes:
        raise ValueError(
            f"unknown domain: {domain!r}; "
            f"valid domains: {sorted({d for d in DOMAIN_BY_PREFIX.values()})}"
        )
    events = read_all_metrics(path)
    return [e for e in events if any(e.counter_name.startswith(p) for p in prefixes)]


def summarize(events: Iterable[MetricEvent]) -> dict[str, dict[str, int]]:
    """Group events by domain, then by counter name, returning count totals.

    Returns a nested dict ``{domain: {counter_name: count}}``. Counts are
    summed from ``fields.count`` (fallback ``fields.confirmed``) when
    present, otherwise each event contributes ``1`` per occurrence.

    Unknown counter names (no prefix match) fall into the ``"unknown"``
    domain bucket (W23 carry-forward).
    """
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for event in events:
        domain = _domain_for_counter(event.counter_name)
        contribution = event.labels.get("count")
        if contribution is None:
            contribution = event.labels.get("confirmed", 1)
        try:
            n = int(contribution)
        except (TypeError, ValueError):
            n = 1
        grouped[domain][event.counter_name] += n
    # Convert inner defaultdicts to plain dicts for stable serialization.
    return {domain: dict(counters) for domain, counters in grouped.items()}


def prometheus_exposition(events: Iterable[MetricEvent]) -> str:
    """Format events as Prometheus textfile exposition (D6 monotonic counter semantics).

    Emits ``# HELP <name> <description>`` + ``# TYPE <name> <type>`` comments
    plus one metric line per counter. Counter names ending in ``_total`` map
    to Prometheus ``counter`` type; bare names map to ``gauge`` (REQ-38 D6).
    """
    lines: list[str] = []
    seen_types: dict[str, str] = {}
    metric_lines: dict[str, list[str]] = defaultdict(list)
    for event in events:
        name = event.counter_name
        if name.endswith("_total"):
            ptype = "counter"
        else:
            ptype = "gauge"
        if name not in seen_types:
            seen_types[name] = ptype
        labels_str = ""
        if event.labels:
            label_parts = []
            for k, v in event.labels.items():
                label_parts.append(f'{k}="{v}"')
            labels_str = "{" + ",".join(label_parts) + "}"
        contribution = event.labels.get("count", 1)
        try:
            value = float(contribution)
        except (TypeError, ValueError):
            value = 1.0
        metric_lines[name].append(f"{name}{labels_str} {value}")
    for name in sorted(metric_lines):
        ptype = seen_types[name]
        lines.append(f"# HELP {name} flow-engineering counter {name}")
        lines.append(f"# TYPE {name} {ptype}")
        lines.extend(metric_lines[name])
    return "\n".join(lines) + ("\n" if lines else "")


# ---------- Change #6 PR#2 T2.1: Prometheus textfile exposition (REQ-38 / D6) ----------


from dataclasses import field as _dc_field


#: Default prefix prepended to every Prometheus metric name (D6 / REQ-38).
#: Callers may override per-call via the ``prefix`` kwarg on
#: :func:`prometheus_exposition`.
PROMETHEUS_NAME_PREFIX: str = "flow_"


#: Keys excluded from Prometheus label rendering (D6).
#: ``count`` / ``elapsed_ms`` / ``value`` carry numeric magnitude and would
#: explode the cardinality if emitted as labels (every distinct count
#: becomes a new series). They are excluded by :func:`prometheus_exposition`.
_LABEL_VALUE_KEYS: frozenset[str] = frozenset({"count", "elapsed_ms", "value"})


METRIC_TYPE_OVERRIDES: dict[str, str] = {}
"""Forward-compatible hook for ambiguous Prometheus types (D6 priority 1).

Empty in v1; the map is the escape hatch for cases where suffix-based
derivation produces the wrong type (e.g., future REQ-42 ``engine_*``
counters with non-suffix types). The default suffix rules handle all v1
counters correctly, so no overrides are needed today.

Lookup order in :func:`_derive_metric_type`:
1. ``METRIC_TYPE_OVERRIDES[name]`` if present (this map).
2. Suffix ``_total`` → ``"counter"``.
3. Suffix ``_ms`` or ``_seconds`` → ``"summary"``.
4. Bare name → ``"gauge"``.
"""


@dataclass(frozen=True)
class PrometheusMetric:
    """One metric line in Prometheus textfile exposition format (REQ-38 / D6).

    A ``PrometheusMetric`` represents a single aggregated metric series
    — one Prometheus ``# HELP`` + ``# TYPE`` + ``<name>{labels} <value>``
    triplet. The :func:`aggregate_events_to_metrics` helper collapses
    multiple :class:`MetricEvent` rows with the same ``(name, labels)``
    into a single :class:`PrometheusMetric` (cumulative counter semantics
    per D6 priority 2).

    Attributes:
        name: The Prometheus metric name (with prefix prepended; e.g.,
            ``"flow_suggest_invoked_total"``).
        value: The aggregated numeric value (sum of contributing event
            ``count`` / fallback fields).
        metric_type: One of ``"counter"`` / ``"gauge"`` / ``"summary"``
            (derived from suffix per D6 priority 2-4).
        help_text: The ``# HELP`` line body (no leading ``# HELP <name>``
            prefix).
        labels: Prometheus label dict (str → str). The ``count`` /
            ``elapsed_ms`` / ``value`` keys are excluded from labels
            because they carry magnitude (D6 cardinality defense).
    """

    name: str
    value: float
    metric_type: str
    help_text: str
    labels: dict[str, str] = _dc_field(default_factory=dict)


def _escape_label_value(value: object) -> str:
    """Escape a Prometheus label value per textfile convention (D6).

    Escapes: ``\\\\`` → ``\\\\\\\\``; ``"`` → ``\\\\"``; ``\\n`` → ``\\\\n``.
    Any non-string value is coerced via ``str()`` first.
    """
    text = str(value)
    return (
        text.replace("\\", "\\\\")
        .replace("\"", "\\\"")
        .replace("\n", "\\n")
    )


def _derive_metric_type(name: str) -> str:
    """Derive the Prometheus type from a metric name (D6 priority 1-4).

    Lookup order:
    1. :data:`METRIC_TYPE_OVERRIDES` (forward-compatible hook; v1 empty).
    2. Suffix ``_total`` → ``"counter"``.
    3. Suffix ``_ms`` or ``_seconds`` → ``"summary"``.
    4. Bare name → ``"gauge"``.
    """
    if name in METRIC_TYPE_OVERRIDES:
        return METRIC_TYPE_OVERRIDES[name]
    if name.endswith("_total"):
        return "counter"
    if name.endswith("_ms") or name.endswith("_seconds"):
        return "summary"
    return "gauge"


def _prometheus_name(counter_name: str, prefix: str) -> str:
    """Map a raw counter name to its Prometheus name with prefix prepended.

    Defensive normalization: ``_total_total`` → ``_total`` (one-shot
    collapse). The v1 catalog never produces a ``_total_total`` suffix,
    but the helper is defensive against future overrides or test
    fixtures that bypass the catalog.
    """
    name = f"{prefix}{counter_name}"
    name = name.replace("_total_total", "_total")
    return name


def _format_label_block(labels: dict[str, str]) -> str:
    """Render a ``{k=\"v\",...}`` label block (or ``""`` when empty).

    Label keys are sorted alphabetically for deterministic output. Values
    are escaped via :func:`_escape_label_value` per D6.
    """
    if not labels:
        return ""
    parts = ",".join(
        f'{k}="{_escape_label_value(v)}"'
        for k, v in sorted(labels.items())
    )
    return "{" + parts + "}"


def aggregate_events_to_metrics(
    events: Iterable[MetricEvent],
    *,
    prefix: str = PROMETHEUS_NAME_PREFIX,
) -> list[PrometheusMetric]:
    """Collapse :class:`MetricEvent` rows into cumulative :class:`PrometheusMetric` entries.

    Events with the same ``(prometheus_name, sorted_label_tuple)`` are
    SUMMED into a single metric (mirrors the existing
    ``_summarize_metrics`` semantics at ``cli.py:960``). Numeric magnitude
    is read from ``event.labels["count"]``; falls back to ``1`` when
    missing or non-numeric.

    Args:
        events: The events to aggregate.
        prefix: Metric-name prefix (default ``"flow_"``).

    Returns:
        A list of :class:`PrometheusMetric` entries sorted by
        ``(name, sorted_labels)`` for stable, deterministic output.
    """
    grouped: dict[
        tuple[str, frozenset[tuple[str, str]]],
        tuple[float, dict[str, str]],
    ] = {}
    for event in events:
        pname = _prometheus_name(event.counter_name, prefix)
        str_labels: dict[str, str] = {
            k: str(v)
            for k, v in event.labels.items()
            if k not in _LABEL_VALUE_KEYS
        }
        key = (pname, frozenset(str_labels.items()))
        try:
            contribution = float(event.labels.get("count", 1))
        except (TypeError, ValueError):
            contribution = 1.0
        prev_total, prev_labels = grouped.get(key, (0.0, str_labels))
        grouped[key] = (prev_total + contribution, prev_labels)
    metrics: list[PrometheusMetric] = [
        PrometheusMetric(
            name=pname,
            value=total,
            metric_type=_derive_metric_type(pname),
            help_text=f"flow-engineering counter {pname}",
            labels=labels,
        )
        for (pname, _labels_key), (total, labels) in grouped.items()
    ]
    metrics.sort(key=lambda m: (m.name, sorted(m.labels.items())))
    return metrics


def prometheus_exposition(
    events: Iterable[MetricEvent],
    *,
    prefix: str = PROMETHEUS_NAME_PREFIX,
) -> str:
    """Format events as Prometheus textfile exposition format (REQ-38 / D6).

    Output structure (per counter, sorted alphabetically):
    - ``# HELP <name> <help_text>``
    - ``# TYPE <name> <counter|summary|gauge>``
    - One ``<name>{labels} <value>`` line per distinct ``(name, labels)``
      group (events with the same group are summed).

    Counter name → Prometheus name mapping: ``<prefix><counter_name>``
    (default prefix ``"flow_"``). Type derivation per D6 priority 2-4:
    ``_total`` → counter; ``_ms`` / ``_seconds`` → summary; bare → gauge.
    Label values are escaped (``"``, ``\\``, ``\\n``) per Prometheus
    textfile spec. Empty input → ``"# EOF\\n"``.

    Args:
        events: MetricEvent list (typically from :func:`read_all_metrics`).
        prefix: Metric-name prefix (default ``"flow_"``).

    Returns:
        Prometheus textfile format string, ready to write to disk or stdout.
    """
    metrics = aggregate_events_to_metrics(events, prefix=prefix)
    if not metrics:
        return "# EOF\n"
    lines: list[str] = []
    current_name: str | None = None
    for metric in metrics:
        if metric.name != current_name:
            lines.append(f"# HELP {metric.name} {metric.help_text}")
            lines.append(f"# TYPE {metric.name} {metric.metric_type}")
            current_name = metric.name
        label_block = _format_label_block(metric.labels)
        lines.append(f"{metric.name}{label_block} {metric.value}")
    return "\n".join(lines) + "\n"


def write_prometheus_textfile(content: str, path: Path) -> None:
    """Write ``content`` to ``path`` as a Prometheus textfile (D10 atomic).

    Thin wrapper over :func:`atomic_write_text` (which lives in the same
    module). The standard production location is
    ``/var/lib/prometheus/node_exporter/textfile_collector/`` — the
    atomic-write pattern (tempfile + ``os.replace``) guarantees that the
    target is never half-written during a Prometheus scrape.
    """
    atomic_write_text(path, content)


def aggregate(
    values: Iterable[float], percentile: Literal[50, 95, 99]
) -> float:
    """Compute the requested percentile of ``values`` (D7 / REQ-39).

    Uses sorted-index lookup (floor interpolation) — closest integer rank
    is returned so a 1..100 sample yields ``p50=50``, ``p95=95``,
    ``p99=99`` (exact, deterministic). Returns ``0.0`` when ``values`` is
    empty (caller emits the "insufficient data" warning separately).
    """
    samples = list(values)
    if not samples:
        return 0.0
    samples.sort()
    if percentile <= 0 or percentile >= 100:
        return float(samples[-1]) if samples else 0.0
    idx = int((len(samples) - 1) * percentile / 100)
    return float(samples[idx])


# ---------- Change #6 PR#2 T2.3: aggregate_many (W5 carry-forward) ----------


#: Accepted percentile values for ``aggregate`` / ``aggregate_many``.
#: Mirrors the spec REQ-39 ``--percentile`` ``click.Choice`` set.
_VALID_PERCENTILES: frozenset[int] = frozenset({50, 95, 99})


def aggregate_many(
    values: Iterable[float],
    percentiles: Iterable[int],
) -> dict[int, float]:
    """Compute multiple percentiles over ``values`` (W5 / D7 / REQ-39).

    Reconciles the W5 carry-forward from PR#1 archive-report (line 78):
    the design D7 contract specifies ``dict[int, float]`` for batch G
    multi-percentile use, but PR#1's :func:`aggregate` returns a single
    float (PR#1 tests stay green by keeping that contract). This new
    helper lets batch G consume multiple percentiles in a single pass
    without breaking the PR#1 contract.

    Args:
        values: Numeric samples to compute percentiles over.
        percentiles: Iterable of percentile values (each must be in
            :data:`_VALID_PERCENTILES`; otherwise ``ValueError``).

    Returns:
        A dict mapping each percentile to its computed value. Empty
        ``values`` → dict with all-zero values (defensive; matches
        :func:`aggregate` "empty → 0.0" semantics).

    Raises:
        ValueError: When any percentile is not in ``{50, 95, 99}``.
    """
    pct_list = list(percentiles)
    for pct in pct_list:
        if pct not in _VALID_PERCENTILES:
            raise ValueError(
                f"invalid percentile {pct}; valid: {sorted(_VALID_PERCENTILES)}"
            )
    samples = list(values)
    if not samples:
        return {pct: 0.0 for pct in pct_list}
    samples.sort()
    results: dict[int, float] = {}
    for pct in pct_list:
        idx = int((len(samples) - 1) * pct / 100)
        results[pct] = float(samples[idx])
    return results


def atomic_write_text(path: Path, content: str) -> int:
    """Write ``content`` to ``path`` atomically (D10 / REQ-38).

    Pattern: ``tempfile.NamedTemporaryFile`` in the same parent dir +
    ``os.replace`` + cleanup on failure. Returns the number of bytes
    written. Parent directories are created on demand.

    Guarantees:
    - The target file is never half-written (rename is atomic on POSIX
      and Windows when both paths are on the same filesystem; the
      ``dir=path.parent`` argument ensures that).
    - No ``.tmp`` orphan files are left behind on failure.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".metrics-", suffix=".prom.tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(content)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return len(content.encode("utf-8"))


# ---------- Change #6 PR#1 batch B T1.4: window filter (REQ-36) ----------


WINDOW_PATTERNS: dict[str, int] = {
    "1h": 3600,
    "24h": 86400,
    "7d": 604800,
    "30d": 2592000,
}
"""Preset rolling-window durations in seconds (REQ-36 / D4).

The values are the canonical presets the CLI accepts via ``--window`` and
``flow metrics --window=<preset>``. The set is a strict superset of
``SUMMARY_WINDOW_CHOICES`` (1h/24h/7d) plus the 30d operational window used
for monthly rollup dashboards.

The CLI's ``--window`` flag uses ``click.Choice`` to validate at parse time;
this constant is the source of truth that the CLI choice list reads from.
"""


def parse_window(window: str) -> int:
    """Parse a window string to a duration in seconds (REQ-36 / D4).

    Accepts:
    - Presets (case-insensitive): ``"1h"`` (3600), ``"24h"`` (86400),
      ``"7d"`` (604800), ``"30d"`` (2592000).
    - Custom format: ``<int><h|d>`` — e.g. ``"12h"`` = 12 * 3600, ``"3d"`` =
      3 * 86400. Only hours (``h``) and days (``d``) units are supported.

    Raises ``ValueError`` on invalid format (CLI catches and exits 2 per D9).
    """
    if not isinstance(window, str) or not window:
        raise ValueError(
            f"window must be a non-empty string; got {window!r}"
        )
    normalized = window.strip().lower()
    if not normalized:
        raise ValueError("window must be a non-empty string")
    if normalized in WINDOW_PATTERNS:
        return WINDOW_PATTERNS[normalized]
    # Custom format: <int><h|d>
    if len(normalized) < 2:
        raise ValueError(
            f"window must be one of {sorted(WINDOW_PATTERNS)} "
            f"or '<int><h|d>'; got {window!r}"
        )
    unit = normalized[-1]
    body = normalized[:-1]
    if unit not in ("h", "d"):
        raise ValueError(
            f"window unit must be 'h' or 'd'; got {window!r}"
        )
    try:
        n = int(body)
    except ValueError as exc:
        raise ValueError(
            f"window prefix must be an integer; got {window!r}: {exc}"
        ) from exc
    if n <= 0:
        raise ValueError(
            f"window duration must be positive; got {window!r}"
        )
    if unit == "h":
        return n * 3600
    return n * 86400


def filter_by_window(
    events: list[MetricEvent],
    window: str,
    *,
    now: float | None = None,
) -> list[MetricEvent]:
    """Filter events to those with ``timestamp >= now - window`` (REQ-36 / D4).

    D4 rolling semantics: the window is a rolling duration relative to
    ``now`` (``now - parse_window(window)``). NOT calendar-aligned — ``1h``
    means "last 60 minutes", not "since the top of the hour".

    Args:
        events: The events to filter.
        window: A window string parseable by :func:`parse_window`.
        now: Epoch seconds to use as the reference point. Defaults to
            ``time.time()``; exposed as a keyword-only argument so unit
            tests can pin the cutoff deterministically.

    Returns:
        A new list containing only the events whose timestamp is in
        ``[now - window, now]``. Inclusive on the lower boundary
        (an event at exactly ``now - window`` is KEPT).
    """
    if now is None:
        now = _time.time()
    cutoff = now - parse_window(window)
    return [e for e in events if e.timestamp >= cutoff]


# ---------- Change #6 PR#1 batch D T1.8: default-empty + exit-code contract ----------


#: Exit code: success (no error, including default-empty per D8).
EXIT_OK: int = 0
#: Exit code: usage error (invalid --window, --domain, --format, --percentile).
EXIT_INVALID_VALUE: int = 2
#: Exit code: data error (invalid --since ISO 8601, malformed JSONL line set).
EXIT_MALFORMED_METRICS: int = 3
#: Exit code: I/O error (--out path not writable, permission denied, disk full).
EXIT_WRITE_FAILURE: int = 4
"""Exit-code contract per design D9 (REQ-35..37 / REQ-38 / REQ-39).

Constants are exposed at module scope so the CLI subcommands and any
downstream consumer (CI scripts, shell pipelines) can reference the same
numeric values without redefining them. The contract is:
- 0 → success (including default-empty per D8: missing/empty/all-malformed
  is NOT a hard error; the missing/empty cases still exit 0).
- 2 → usage error (invalid flag values; Click ``click.Choice`` rejects
  at parse time and emits the standard usage error).
- 3 → data error (invalid --since ISO 8601; or — via T1.8 — metrics file
  exists but every line failed to parse).
- 4 → I/O error (write failures on --out; perm denied, disk full).
"""


@dataclass(frozen=True)
class MetricsSummaryResult:
    """Result of a metrics read+summary operation (D8 default-empty contract).

    Carries the summary dict plus diagnostics about what was read so the
    CLI can map the failure mode to a user-facing message and exit code
    per design D9 (REQ-35..37 error handling).

    Attributes:
        summary: ``{domain: {counter_name: count}}``; may be empty when
            no events survived filtering.
        events_read: Total events parsed from the JSONL sink (malformed
            lines are silently skipped, per the REQ-8 best-effort contract).
        source_path: The path the metrics were read from.
        empty_reason: ``None`` when events were found; one of:
            - ``"missing_file"`` — metrics.jsonl does not exist.
            - ``"empty_file"`` — exists but has zero bytes.
            - ``"all_malformed"`` — exists but every line failed to parse.
        window: Window filter applied (``None`` when no --window).
        domain: Domain filter applied (``None`` when no --domain).
    """

    summary: dict[str, dict[str, int]]
    events_read: int
    source_path: Path
    empty_reason: str | None
    window: str | None = None
    domain: str | None = None


def read_and_summarize(
    *,
    window: str | None = None,
    domain: str | None = None,
    path: Path | None = None,
) -> MetricsSummaryResult:
    """Read metrics + apply filters + summarize in one call (D8 default-empty).

    The default-empty contract: when no events are read from the JSONL
    sink, ``summary`` is ``{}`` and ``empty_reason`` explains why
    (``missing_file`` / ``empty_file`` / ``all_malformed``). The CLI maps
    these to user-facing messages and exit codes per design D9.

    Filter ordering: ``--window`` (rolling, in-memory) is applied first
    because it is the cheapest filter; ``--domain`` (prefix-based) is
    applied second against the window-filtered set.

    Args:
        window: Optional ``--window`` value (``"1h"`` / ``"24h"`` / ``"7d"``
            / custom ``"<int><h|d>"``); parsed via :func:`parse_window`.
        domain: Optional ``--domain`` value (``"binding"`` / ``"drift"`` /
            etc.); raises ``ValueError`` when the domain is unknown (the
            CLI catches and emits exit-code-2 per D9).
        path: Optional metrics JSONL path; defaults to the resolved sink
            path (env override wins over default).

    Returns:
        A :class:`MetricsSummaryResult` carrying the per-domain summary,
        diagnostics, and applied filters.
    """
    target = path if path is not None else _resolve_path()

    events = read_all_metrics(target)
    events_read = len(events)

    if events_read == 0:
        if not target.exists():
            empty_reason = "missing_file"
        elif target.stat().st_size == 0:
            empty_reason = "empty_file"
        else:
            empty_reason = "all_malformed"
        return MetricsSummaryResult(
            summary={},
            events_read=0,
            source_path=target,
            empty_reason=empty_reason,
            window=window,
            domain=domain,
        )

    if window is not None:
        events = filter_by_window(events, window)
    if domain is not None:
        prefixes = _prefixes_for_domain(domain)
        if not prefixes:
            # Mirror the read_events_by_domain contract: unknown domain
            # raises ValueError so the CLI emits exit-code-2 (D9).
            raise ValueError(
                f"unknown domain: {domain!r}; "
                f"valid domains: {sorted({d for d in DOMAIN_BY_PREFIX.values()})}"
            )
        events = [e for e in events if any(e.counter_name.startswith(p) for p in prefixes)]

    summary = summarize(events)
    return MetricsSummaryResult(
        summary=summary,
        events_read=events_read,
        source_path=target,
        empty_reason=None,
        window=window,
        domain=domain,
    )
