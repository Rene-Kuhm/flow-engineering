"""Save-time auto-suggest for ``code_refs`` bindings (REQ-6, PR#2 batch 1).

REQ-6: when ``mem_save`` is called without an explicit ``code_refs`` block AND
graphify is available, the system MUST offer auto-suggest candidates whose
score meets or exceeds the threshold (default 0.3) and require explicit
confirmation before persisting any binding. Three confirmation channels:

- ``--with-suggest`` CLI flag (non-interactive, accept-all).
- ``FLOW_AUTO_SUGGEST=1`` environment variable (non-interactive, accept-all).
- Interactive prompt when ``stdin.isatty()`` is true; user picks via a
  numbered list.

``--no-suggest`` (or ``no_suggest=True``) skips the suggester entirely and
records ``source: manual`` with empty ``nodes`` so the save still proceeds.

The module MUST fail-open: any graphify error yields ``source: unbound`` and
the caller writes a normal observation without bindings. No exceptions
escape this module.

Public surface (PR#2 batch 1):
- ``SuggestionResult`` -- frozen dataclass: ``refs``, ``source``, ``error``.
- ``auto_suggest_code_refs(text, *, threshold, max_results, with_suggest,
  no_suggest, is_tty, prompt_fn, env)`` -- the orchestrator.
- ``format_suggestion_prompt(refs)`` -- pure formatter for the interactive
  prompt (testable in isolation).
- ``DEFAULT_THRESHOLD`` / ``DEFAULT_MAX_RESULTS`` / ``FLOW_AUTO_SUGGEST_ENV``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Literal

from flow_engineering import graphify_query, observability
from flow_engineering.binding import CodeRef

Source = Literal["manual", "auto_suggest", "backfill", "unbound"]

DEFAULT_THRESHOLD: float = 0.3
DEFAULT_MAX_RESULTS: int = 5
FLOW_AUTO_SUGGEST_ENV: str = "FLOW_AUTO_SUGGEST"

PromptFn = Callable[[list[CodeRef]], list[CodeRef]]

EMPTY_PROMPT_TEXT: str = "No auto-suggested bindings available."
PROMPT_HEADER: str = "Auto-suggested code bindings:"
PROMPT_FOOTER: str = (
    "Confirm: [a]ll / [n]one / comma-separated numbers (e.g., 1,3)"
)


@dataclass(frozen=True)
class SuggestionResult:
    """Outcome of an auto-suggest run.

    - ``refs`` is the list of bindings to write (may be empty).
    - ``source`` is the ``code_refs`` block source: ``manual``, ``auto_suggest``,
      or ``unbound``. ``manual`` means the caller explicitly skipped suggest;
      ``unbound`` means graphify was tried but yielded nothing usable.
    - ``error`` carries an optional reason for observability (never raised).
    """

    refs: list[CodeRef]
    source: Source
    error: str | None = None


# ---------- Pure helpers (no IO) ----------


def _is_non_interactive(
    *, with_suggest: bool, is_tty: bool, env: dict[str, str]
) -> bool:
    """Return True when the suggester should run in non-interactive mode.

    Non-interactive (accept-all) is the default in batch / CI / env-driven
    contexts. Interactive prompt is used ONLY when: TTY is true, no
    ``--with-suggest`` flag, and no ``FLOW_AUTO_SUGGEST`` env override.
    """
    if with_suggest:
        return True
    if env.get(FLOW_AUTO_SUGGEST_ENV) == "1":
        return True
    return not is_tty


def format_suggestion_prompt(refs: list[CodeRef]) -> str:
    """Format the interactive confirmation prompt for the candidate ``refs``.

    Returns a multi-line string suitable for printing to a TTY. The output
    is purely deterministic so it can be asserted in tests.
    """
    if not refs:
        return EMPTY_PROMPT_TEXT
    lines = [PROMPT_HEADER]
    for i, r in enumerate(refs, 1):
        lines.append(
            f"  [{i}] {r.label} ({r.file}:{r.line}, "
            f"score={r.confidence:.2f}, id={r.id})"
        )
    lines.append("")
    lines.append(PROMPT_FOOTER)
    return "\n".join(lines)


# ---------- Metric helpers ----------


def _record_hit(count: int) -> None:
    """Record a successful suggestion outcome."""
    observability.increment("suggest_hit_total", count=count)
    observability.increment("bindings_confirmed_total", count=count)


def _record_miss(reason: str) -> None:
    """Record a suggestion miss with the given reason."""
    observability.increment("suggest_miss_total", reason=reason)


# ---------- Orchestrator ----------


def _resolve_env(env: dict[str, str] | None) -> dict[str, str]:
    """Return the effective env dict, defaulting to ``os.environ``."""
    return dict(env) if env is not None else dict(os.environ)


def _query_graphify(
    text: str, *, threshold: float, max_results: int
) -> list[CodeRef]:
    """Call graphify_query.query_nodes, returning [] on any error (fail-open)."""
    try:
        return graphify_query.query_nodes(
            text, threshold=threshold, max_results=max_results
        )
    except Exception as exc:  # pragma: no cover - defensive
        _record_miss("error")
        # Re-raise via a sentinel: caller distinguishes via empty result.
        raise GraphifyCallError(str(exc)) from exc


class GraphifyCallError(RuntimeError):
    """Internal sentinel so the orchestrator can distinguish empty-vs-error."""


def _interactive_choose(
    suggestions: list[CodeRef], prompt_fn: PromptFn | None
) -> list[CodeRef]:
    """Resolve the interactive selection; fall back to accept-all when no fn."""
    if prompt_fn is None:
        # TTY claimed but no prompt function -- fail-open to non-interactive.
        return list(suggestions)
    return list(prompt_fn(suggestions))


def auto_suggest_code_refs(
    text: str,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    max_results: int = DEFAULT_MAX_RESULTS,
    with_suggest: bool = False,
    no_suggest: bool = False,
    is_tty: bool = False,
    prompt_fn: PromptFn | None = None,
    env: dict[str, str] | None = None,
) -> SuggestionResult:
    """Run auto-suggest on ``text`` and return what the caller should write.

    The function NEVER raises. Every failure path yields a
    :class:`SuggestionResult` with ``source="unbound"`` and a populated
    ``error`` field describing the reason.

    Parameters
    ----------
    text : str
        Observation prose to match against graph nodes.
    threshold : float
        Minimum confidence to surface (default 0.3).
    max_results : int
        Maximum candidates to return (default 5).
    with_suggest : bool
        CLI flag -- forces non-interactive accept-all when True.
    no_suggest : bool
        CLI flag -- bypasses graphify entirely; returns ``source="manual"``.
    is_tty : bool
        Whether the caller is attached to a TTY (drives interactive prompt).
    prompt_fn : Callable | None
        Pluggable prompt for tests. Must return the chosen ``CodeRef`` list.
        When ``None`` and ``is_tty`` is True, the function falls back to
        non-interactive accept-all (fail-open -- real TTY prompt is wired
        in the CLI layer, not here).
    env : dict | None
        Environment overrides (for tests). Defaults to ``os.environ``.
    """
    if no_suggest:
        return SuggestionResult(refs=[], source="manual", error=None)

    observability.increment("suggest_invoked_total")

    resolved_env = _resolve_env(env)

    try:
        suggestions = _query_graphify(
            text, threshold=threshold, max_results=max_results
        )
    except GraphifyCallError as exc:
        return SuggestionResult(
            refs=[], source="unbound", error=f"graphify_error: {exc}"
        )

    if not suggestions:
        _record_miss("no_candidates")
        return SuggestionResult(refs=[], source="unbound", error="no_candidates")

    if _is_non_interactive(
        with_suggest=with_suggest, is_tty=is_tty, env=resolved_env
    ):
        _record_hit(len(suggestions))
        return SuggestionResult(
            refs=list(suggestions), source="auto_suggest", error=None
        )

    chosen = _interactive_choose(suggestions, prompt_fn)
    if chosen:
        _record_hit(len(chosen))
        return SuggestionResult(refs=chosen, source="auto_suggest", error=None)

    _record_miss("rejected")
    return SuggestionResult(refs=[], source="unbound", error="rejected")


__all__ = [
    "DEFAULT_MAX_RESULTS",
    "DEFAULT_THRESHOLD",
    "FLOW_AUTO_SUGGEST_ENV",
    "GraphifyCallError",
    "PromptFn",
    "Source",
    "SuggestionResult",
    "auto_suggest_code_refs",
    "format_suggestion_prompt",
]