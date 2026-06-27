"""Central catalog for inline prompt strings (REQ-45 foundation).

REQ-45: A single source of truth for every prompt string the project ships,
so future `flow prompts list/show/lint/check` (REQ-50) and the SKILL.md mirror
catalog (REQ-49) can discover them without grepping the codebase.

Mirrors the observability counter catalog pattern
(``VECTOR_COUNTER_NAMES``, ``SNAPSHOT_COUNTER_NAMES``,
``FEDERATED_COUNTER_NAMES`` in ``observability.py``).

Public surface:
- :class:`PromptDomain` -- categorical domain enum used by ``flow prompts
  list --domain <name>`` filtering.
- :class:`PromptDef` -- frozen dataclass describing one entry.
- :data:`PROMPT_NAMES` -- the catalog (tuple of :class:`PromptDef`).
- :func:`get_prompt` -- lookup by name.
- :func:`list_prompts` -- enumerate, optionally filtered by domain.
- :func:`get_prompt_template` -- shorthand for ``get_prompt(name).template``.
- :func:`get_prompt_metadata` -- shorthand for ``get_prompt(name).metadata``.
- :func:`register_prompt` -- append a NEW prompt (idempotency check).
- :func:`unregister_prompt` -- inverse of register, primarily for tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PromptDomain(str, Enum):
    """Categorical domain for prompt grouping.

    Mirrors the ``owner`` convention used by the observability counter
    catalogs. Used by the future ``flow prompts list --domain <name>``
    CLI flag (REQ-50).

    Members:
        BINDING: code-refs auto-suggest prompts (``PROMPT_HEADER`` etc.).
        DRIFT: drift-detection prompts (reserved; future).
        OBSERVABILITY: metrics summary + strict-tdd injection prompts.
        SNAPSHOT: snapshot lifecycle prompts (reserved; future).
        RUNTIME: OpenCode SKILL.md agent prompts (REQ-49, future).
    """

    BINDING = "binding"
    DRIFT = "drift"
    OBSERVABILITY = "observability"
    SNAPSHOT = "snapshot"
    RUNTIME = "runtime"


@dataclass(frozen=True)
class PromptDef:
    """One prompt entry in the catalog.

    Attributes:
        name: Unique identifier (e.g., ``"suggest_with_context"``). Must be
            unique across the catalog; used as the lookup key.
        domain: :class:`PromptDomain` category used for grouping +
            ``flow prompts list --domain`` filtering.
        template: The prompt string. May contain ``{var}`` Python format
            placeholders for runtime substitution (the inline constants
            migrated from ``strict_tdd.py`` and ``auto_suggest_code_refs.py``
            use this style for byte-compatibility with existing call sites).
        version: SemVer string (``MAJOR.MINOR.PATCH``). Bump when template
            content or variable signature changes.
        metadata: Arbitrary key-value pairs (model name, max_tokens, source
            path, etc.). Never used by the registry itself; surfaced through
            ``flow prompts list --json`` for downstream consumers.
    """

    name: str
    domain: PromptDomain
    template: str
    version: str
    metadata: dict[str, Any] = field(default_factory=dict)


PROMPT_NAMES: tuple[PromptDef, ...] = (
    PromptDef(
        name="strict_tdd",
        domain=PromptDomain.OBSERVABILITY,
        template=(
            "STRICT TDD MODE IS ACTIVE. Test runner: {test_command}. "
            "You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."
        ),
        version="1.0.0",
        metadata={
            "source": "src/flow_engineering/strict_tdd.py:13",
            "variables": ("test_command",),
        },
    ),
    PromptDef(
        name="auto_suggest_header",
        domain=PromptDomain.BINDING,
        template="Auto-suggested code bindings:",
        version="1.0.0",
        metadata={
            "source": "src/flow_engineering/auto_suggest_code_refs.py:48",
            "variables": (),
        },
    ),
    PromptDef(
        name="auto_suggest_footer",
        domain=PromptDomain.BINDING,
        template=(
            "Confirm: [a]ll / [n]one / comma-separated numbers (e.g., 1,3)"
        ),
        version="1.0.0",
        metadata={
            "source": "src/flow_engineering/auto_suggest_code_refs.py:49",
            "variables": (),
        },
    ),
    PromptDef(
        name="auto_suggest_empty",
        domain=PromptDomain.BINDING,
        template="No auto-suggested bindings available.",
        version="1.0.0",
        metadata={
            "source": "src/flow_engineering/auto_suggest_code_refs.py:47",
            "variables": (),
        },
    ),
)
"""Canonical catalog of inline prompt strings (REQ-45).

Initial population mirrors the 4 existing inline constants:
``STRICT_TDD_PROMPT`` (strict_tdd.py:13), ``EMPTY_PROMPT_TEXT`` /
``PROMPT_HEADER`` / ``PROMPT_FOOTER`` (auto_suggest_code_refs.py:47-49).
The catalog is the single source of truth; the original module-level
constants become thin aliases that delegate to ``get_prompt_template()``
for v0.7.0 (per D10 alias convention).
"""


def get_prompt(name: str) -> PromptDef:
    """Look up a prompt by name.

    Args:
        name: The unique identifier declared in :data:`PROMPT_NAMES`.

    Returns:
        The matching :class:`PromptDef`.

    Raises:
        KeyError: When ``name`` is not in the catalog. The error message
            includes the catalog contents to ease debugging.
    """
    for prompt in PROMPT_NAMES:
        if prompt.name == name:
            return prompt
    raise KeyError(
        f"unknown prompt {name!r}; valid: {[p.name for p in PROMPT_NAMES]}"
    )


def list_prompts(domain: PromptDomain | None = None) -> list[PromptDef]:
    """List registered prompts, optionally filtered by domain.

    Args:
        domain: When ``None``, returns every entry. When a
            :class:`PromptDomain` value, returns only entries whose domain
            matches. Unknown domains return ``[]`` (defensive; the caller
            decides whether to surface a warning).

    Returns:
        A new list of :class:`PromptDef` instances. The result is sorted
        by ``name`` for stable output (used by ``flow prompts list``).
    """
    if domain is None:
        return sorted(PROMPT_NAMES, key=lambda p: p.name)
    return sorted((p for p in PROMPT_NAMES if p.domain == domain), key=lambda p: p.name)


def get_prompt_template(name: str) -> str:
    """Return the template string for a known prompt.

    Shorthand for ``get_prompt(name).template``. Raises :class:`KeyError`
    when ``name`` is not in the catalog.
    """
    return get_prompt(name).template


def get_prompt_metadata(name: str) -> dict[str, Any]:
    """Return the metadata dict for a known prompt.

    Shorthand for ``get_prompt(name).metadata``. Raises :class:`KeyError`
    when ``name`` is not in the catalog. The returned dict is the same
    reference held by the entry; callers MUST NOT mutate it (use
    :func:`register_prompt` to add new entries instead).
    """
    return get_prompt(name).metadata


def register_prompt(prompt: PromptDef) -> None:
    """Append a NEW prompt to the catalog.

    The function is intended for plugin / migration paths that build the
    catalog dynamically (e.g., a future ``prompt_load_from_disk`` helper
    or a one-off batch-import script). Production code paths should add
    new entries to :data:`PROMPT_NAMES` directly.

    Args:
        prompt: The :class:`PromptDef` to append.

    Raises:
        ValueError: When a prompt with the same name is already registered.
    """
    global PROMPT_NAMES
    if any(p.name == prompt.name for p in PROMPT_NAMES):
        raise ValueError(
            f"prompt {prompt.name!r} already registered; "
            "use unregister_prompt first to replace"
        )
    PROMPT_NAMES = PROMPT_NAMES + (prompt,)


def unregister_prompt(name: str) -> None:
    """Remove a prompt from the catalog.

    Inverse of :func:`register_prompt`. Primarily used by tests that need
    to clean up after dynamic registrations. Silently no-ops when ``name``
    is not in the catalog (defensive; mirrors the fail-open convention
    used elsewhere in the project).

    Args:
        name: The identifier to remove.
    """
    global PROMPT_NAMES
    PROMPT_NAMES = tuple(p for p in PROMPT_NAMES if p.name != name)


__all__ = [
    "PROMPT_NAMES",
    "PromptDef",
    "PromptDomain",
    "get_prompt",
    "get_prompt_metadata",
    "get_prompt_template",
    "list_prompts",
    "register_prompt",
    "unregister_prompt",
]
