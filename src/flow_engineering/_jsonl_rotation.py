"""Shared best-effort JSONL rotation helper (REQ-JRH-1 / REQ-JRH-2).

Slice 2 of the drift-detection work consolidates the two verbatim-duplicated
rotation implementations into one private module so future JSONL sinks can
opt in by passing a ``glob_prefix``.

Two call sites share this helper today:

- :class:`flow_engineering.drift_event_log.DriftEventLog` passes
  ``glob_prefix="drift_events"`` plus the ``FLOW_DRIFT_EVENT_LOG_*`` env-var
  names + defaults (REQ-V1.1.1).
- :func:`flow_engineering.observability.increment` passes
  ``glob_prefix="metrics"`` plus the ``FLOW_METRICS_LOG_*`` env-var names +
  defaults (REQ-V1.2.1).

The helper acquires NO lock — the caller is responsible for the
concurrency contract (``DriftEventLog.append`` wraps it in
``self._lock``; ``observability.increment`` does not lock because the
metrics sink is single-process). Every filesystem call is wrapped in
``try/except OSError`` so a slow FS never crashes the caller (best-effort
contract preserved from REQ-V1.1.1 / REQ-V1.2.1).
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path


def _stamp_now() -> str:
    """Return the canonical ISO-no-colons UTC stamp ``%Y%m%dT%H%M%SZ``.

    Single source of truth for rotated-file names so both JSONL sinks
    stay byte-identical (REQ-JRH-2 operator contract). Returns a naive
    ``str`` — the trailing ``Z`` is decorative per the legacy format.
    """
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _resolve_jsonl_rotation_threshold_bytes(*, env: str, default: int) -> int:
    """Resolve the size-threshold env var for any JSONL sink.

    Mirrors the prior ``_resolve_rotation_threshold_bytes`` /
    ``_resolve_metrics_rotation_threshold_bytes`` semantics verbatim:

    - missing/empty env var → ``default`` (10 MB for both sinks today)
    - non-integer env var → ``default``
    - negative env var → ``0`` (disabled)
    - explicit ``0`` → ``0`` (disabled)
    - positive env var → ``value``
    """
    raw = os.environ.get(env)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(0, value)


def _resolve_jsonl_max_age_days(*, env: str, default: int) -> int:
    """Resolve the age-cutoff env var for any JSONL sink.

    Mirrors the prior ``_resolve_max_age_days`` /
    ``_resolve_metrics_max_age_days`` semantics verbatim:

    - missing/empty env var → ``default`` (30 days for both sinks today)
    - non-integer env var → ``default``
    - ``<= 0`` env var → ``0`` (disabled — triggers the
      ``max_age_days <= 0: return`` guard in the rotation helper so
      the glob walk is skipped entirely)
    - positive env var → ``value``
    """
    raw = os.environ.get(env)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(0, value)


def _rotate_jsonl_if_needed(
    path: Path,
    *,
    glob_prefix: str,
    max_bytes_env: str,
    max_age_days_env: str,
    default_max_bytes: int,
    default_max_age_days: int,
) -> None:
    """Best-effort size + age rotation for any append-only JSONL sink.

    Sequence:

    1. Resolve the size threshold via ``max_bytes_env``; if
       ``st_size >= threshold`` AND the active file exists, rename
       ``path`` to ``f"{glob_prefix}.{ISO-stamp}.jsonl"``.
    2. Resolve the age cutoff via ``max_age_days_env``; if
       ``max_age_days <= 0`` the function returns immediately
       (REQ-JRH-1 explicit guard BEFORE any ``parent.glob`` walk).
    3. Otherwise walk ``path.parent.glob(f"{glob_prefix}.*.jsonl")``
       and unlink every sibling whose ``st_mtime`` is older than the
       cutoff. The active ``path`` itself is skipped (never delete the
       live sink).

    Every filesystem call (``stat``, ``rename``, ``glob``, ``unlink``)
    is wrapped in ``try/except OSError`` so a slow network FS never
    crashes the caller (best-effort contract preserved from
    REQ-V1.1.1 + REQ-V1.2.1). The helper acquires NO lock.

    Args:
        path: The active JSONL sink path. The caller is responsible for
            the surrounding concurrency contract — ``DriftEventLog.append``
            wraps this call in ``self._lock``; ``observability.increment``
            does not lock (single-process sink).
        glob_prefix: The rotated-sibling filename prefix shared with the
            active file (e.g. ``"drift_events"`` or ``"metrics"``). The
            helper walks siblings of the form
            ``f"{glob_prefix}.*.jsonl"`` only — never crosses schemes.
        max_bytes_env: Env-var name to read for the size threshold
            (e.g. ``FLOW_DRIFT_EVENT_LOG_MAX_BYTES``).
        max_age_days_env: Env-var name to read for the age cutoff
            (e.g. ``FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS``).
        default_max_bytes: Size threshold when ``max_bytes_env`` is
            missing/empty/invalid (10 MB for both sinks today).
        default_max_age_days: Age cutoff when ``max_age_days_env`` is
            missing/empty/invalid (30 days for both sinks today).
    """
    threshold = _resolve_jsonl_rotation_threshold_bytes(
        env=max_bytes_env, default=default_max_bytes
    )
    if threshold > 0 and path.exists():
        try:
            if path.stat().st_size >= threshold:
                stamp = _stamp_now()
                rotated = path.with_name(f"{glob_prefix}.{stamp}.jsonl")
                path.rename(rotated)
        except OSError:
            # Best-effort: a slow rename on a network FS MUST NOT crash
            # the caller. The active file is left in place; the next
            # append will see a still-over-threshold size and retry.
            pass

    max_age_days = _resolve_jsonl_max_age_days(
        env=max_age_days_env, default=default_max_age_days
    )
    # REQ-JRH-1 explicit guard: disabled/negative age cleanup MUST
    # short-circuit BEFORE any parent.glob walk so the FS is untouched.
    if max_age_days <= 0:
        return
    cutoff = datetime.now(UTC).timestamp() - (max_age_days * 86400)
    parent = path.parent
    for sibling in parent.glob(f"{glob_prefix}.*.jsonl"):
        if sibling == path:
            continue
        try:
            if sibling.stat().st_mtime < cutoff:
                sibling.unlink()
        except OSError:
            # Best-effort: skip siblings whose stat/unlink fails.
            pass


__all__ = [
    "_resolve_jsonl_max_age_days",
    "_resolve_jsonl_rotation_threshold_bytes",
    "_rotate_jsonl_if_needed",
    "_stamp_now",
]
