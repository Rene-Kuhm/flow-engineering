"""Append-only JSONL sink for ``render_prompt()`` calls (REQ-V1.1.3 / REQ-51).

The sink records every successful and failed render to
``~/.flow-engineering/prompt_renders.jsonl`` so operators can audit
prompt usage + failure rates without coupling to the in-process registry.
The sink is opt-in via the ``FLOW_PROMPT_LOG=1`` environment variable
(default OFF) to keep write-free agent flows untouched.

Wire format (one JSONL line per event):
- ``prompt_id``: catalog identifier (e.g., ``"strict_tdd"``)
- ``rendered_at``: epoch seconds (float) of when the render completed
- ``elapsed_ms``: wall-clock duration of the render in milliseconds
- ``ok``: boolean — ``True`` on success, ``False`` on exception
- ``error``: error category string (``"missing_var"`` / ``"template_error"``
  / ``"unknown"``); ``None`` when ``ok`` is ``True``
- ``var_keys``: list of variable names supplied by the caller

The writer is best-effort: a write failure (disk full, permission
denied) is swallowed at the module level so it never crashes the
runtime render path. The reader mirrors :class:`DriftEventLog.read_all`
(malformed lines silently skipped; missing file → ``[]``).
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_PROMPT_RENDER_LOG_PATH: Path = (
    Path.home() / ".flow-engineering" / "prompt_renders.jsonl"
)
"""Default JSONL sink path (REQ-V1.1.3).

Mirrors :data:`flow_engineering.drift_event_log.DEFAULT_DRIFT_EVENT_LOG_PATH`
to keep the operator-facing layout uniform across the two JSONL
sinks. Tests monkeypatch this module attribute so they never touch the
real home directory.
"""

_FLOW_PROMPT_LOG_VALUES_TRUE: frozenset[str] = frozenset({"1", "true", "yes", "on"})


def _is_prompt_log_enabled() -> bool:
    """Return ``True`` iff ``FLOW_PROMPT_LOG`` is set to a truthy value.

    Truthy values mirror the click convention: ``1`` / ``true`` / ``yes``
    / ``on`` (case-insensitive). Empty / unset / any other value → False.
    """
    raw = os.environ.get("FLOW_PROMPT_LOG", "").strip().lower()
    return raw in _FLOW_PROMPT_LOG_VALUES_TRUE


@dataclass(frozen=True)
class PromptRenderEvent:
    """One JSONL line of the prompt render sink.

    Attributes:
        prompt_id: Catalog identifier (e.g., ``"strict_tdd"``).
        rendered_at: Epoch seconds (float) when the render completed.
        elapsed_ms: Wall-clock duration of the render in milliseconds.
        ok: ``True`` on success, ``False`` on exception.
        error: Error category (``"missing_var"`` / ``"template_error"`` /
            ``"unknown"``); ``None`` when ``ok`` is ``True``.
        var_keys: Tuple of variable names supplied to ``render_prompt``.
            Stored as a list in JSON for forward-compatibility (callers
            may pass ``**kwargs`` in any order).
    """

    prompt_id: str
    rendered_at: float
    elapsed_ms: float
    ok: bool
    error: str | None
    var_keys: tuple[str, ...] = field(default_factory=tuple)

    def to_json_dict(self) -> dict[str, Any]:
        """Return the JSON wire dict with the spec schema."""
        return {
            "prompt_id": self.prompt_id,
            "rendered_at": self.rendered_at,
            "elapsed_ms": self.elapsed_ms,
            "ok": self.ok,
            "error": self.error,
            "var_keys": list(self.var_keys),
        }


class PromptRenderLog:
    """Append-only JSONL writer with in-process thread safety (mirrors ``DriftEventLog``)."""

    def __init__(self, path: Path | None = None) -> None:
        self.path: Path = (
            path if path is not None else DEFAULT_PROMPT_RENDER_LOG_PATH
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, event: PromptRenderEvent) -> None:
        """Append one event as a single JSONL line under an in-process lock.

        Best-effort writes: an ``OSError`` from the underlying ``open()``
        or ``write()`` propagates to the caller (the
        :func:`record_prompt_render` helper swallows it so the runtime
        render path never crashes on a full disk).
        """
        line = json.dumps(event.to_json_dict(), ensure_ascii=False) + "\n"
        with self._lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()

    def read_all(self) -> list[PromptRenderEvent]:
        """Return all events from the JSONL file in append order.

        Missing file returns ``[]``; malformed JSONL lines are silently
        skipped (mirrors :meth:`DriftEventLog.read_all` best-effort
        contract).
        """
        if not self.path.exists():
            return []
        events: list[PromptRenderEvent] = []
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            try:
                events.append(
                    PromptRenderEvent(
                        prompt_id=str(data.get("prompt_id", "")),
                        rendered_at=float(data.get("rendered_at", 0.0)),
                        elapsed_ms=float(data.get("elapsed_ms", 0.0)),
                        ok=bool(data.get("ok", False)),
                        error=data.get("error"),
                        var_keys=tuple(data.get("var_keys", ())),
                    )
                )
            except (TypeError, ValueError):
                continue
        return events


def _log_for() -> PromptRenderLog:
    """Return a fresh :class:`PromptRenderLog` pointing at the default path."""
    return PromptRenderLog()


def record_prompt_render(
    *,
    prompt_id: str,
    rendered_at: float,
    elapsed_ms: float,
    ok: bool,
    error: str | None,
    var_keys: tuple[str, ...] | list[str] = (),
) -> None:
    """Append one render event to the default sink (best-effort, gated).

    Returns silently when ``FLOW_PROMPT_LOG`` is unset. Swallows
    ``OSError`` from the underlying ``open()`` / ``write()`` so a full
    disk or read-only filesystem never crashes the runtime render path.

    Args:
        prompt_id: Catalog identifier of the rendered prompt.
        rendered_at: Epoch seconds (float) of the render completion.
        elapsed_ms: Wall-clock duration in milliseconds.
        ok: ``True`` on success, ``False`` on exception.
        error: Error category (``"missing_var"`` / ``"template_error"`` /
            ``"unknown"``) or ``None`` when ``ok``.
        var_keys: Variable names supplied to ``render_prompt``. Accepts
            tuple or list; stored as tuple on the event.
    """
    if not _is_prompt_log_enabled():
        return
    event = PromptRenderEvent(
        prompt_id=prompt_id,
        rendered_at=rendered_at,
        elapsed_ms=elapsed_ms,
        ok=ok,
        error=error,
        var_keys=tuple(var_keys),
    )
    try:
        _log_for().append(event)
    except OSError:
        pass


__all__ = [
    "DEFAULT_PROMPT_RENDER_LOG_PATH",
    "PromptRenderEvent",
    "PromptRenderLog",
    "record_prompt_render",
]