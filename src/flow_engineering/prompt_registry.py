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
- :func:`register` -- positional-args shorthand that wraps ``register_prompt``.
- :func:`validate_catalog` -- REQ-47 lint foundation: detect the 5 catalog
  error codes BEFORE the heavier :func:`lint_prompts` helper builds on top.
- :class:`LintError` -- frozen dataclass describing one catalog violation.
"""

from __future__ import annotations

import re
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


@dataclass(frozen=True)
class LintError:
    """One validation error in the prompt catalog (REQ-47 foundation).

    Attributes:
        prompt_name: The :class:`PromptDef` name that failed validation.
        error_code: One of ``"duplicate_name"``, ``"invalid_domain"``,
            ``"jinja_syntax"``, ``"undefined_var"``, ``"invalid_version"``.
        message: Human-readable diagnostic surfaced by ``flow prompts lint``.
        line: 1-indexed template line number when available; ``None`` for
            catalog-level checks (duplicate name, invalid domain, invalid
            version).
    """

    prompt_name: str
    error_code: str
    message: str
    line: int | None = None


def register(
    name: str,
    template: str,
    domain: PromptDomain,
    *,
    version: str = "1.0.0",
    **metadata: Any,
) -> None:
    """Shorthand :func:`register_prompt` with positional arguments.

    Convenience wrapper for plugin / test paths that build the catalog
    dynamically. Production prompts should be added to :data:`PROMPT_NAMES`
    directly so the catalog stays statically discoverable.

    Args:
        name: Unique identifier for the new prompt.
        template: The prompt string (Python ``.format()`` style for v1).
        domain: :class:`PromptDomain` category.
        version: SemVer ``MAJOR.MINOR.PATCH`` (default ``"1.0.0"``).
        **metadata: Stored on :attr:`PromptDef.metadata`. Common keys:
            ``model``, ``max_tokens``, ``required_vars``.

    Raises:
        ValueError: When a prompt with the same ``name`` is already in the
            catalog (delegated to :func:`register_prompt`).
    """
    register_prompt(
        PromptDef(
            name=name,
            domain=domain,
            template=template,
            version=version,
            metadata=dict(metadata),
        )
    )


_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def validate_catalog(
    catalog: tuple[PromptDef, ...] | None = None,
) -> list[LintError]:
    """Validate the prompt catalog (REQ-47 lint foundation).

    Detects the 5 catalog-level error codes without raising. Callers (the
    ``flow prompts lint`` CLI, pytest fixtures, CI gates) decide how to
    surface the result.

    Checks:
        1. ``duplicate_name`` -- the same name appears twice in the catalog.
        2. ``invalid_domain`` -- ``entry.domain`` is not a :class:`PromptDomain`
            value (defensive; allows subclasses / mocks to surface a useful
            error).
        3. ``jinja_syntax`` -- the template body fails Jinja2 parse.
        4. ``undefined_var`` -- a Jinja2 ``{{ var }}`` placeholder appears in
            the template body but is not declared in ``metadata.required_vars``.
            Templates using Python ``.format()`` style (e.g., ``{test_command}``)
            are valid literal text in Jinja2 and therefore do NOT trigger this
            check; the catalog is format-agnostic at v1.
        5. ``invalid_version`` -- ``entry.version`` does not match the SemVer
            ``MAJOR.MINOR.PATCH`` regex.

    Args:
        catalog: The catalog to validate. ``None`` defaults to
            :data:`PROMPT_NAMES`. An empty tuple returns ``[]``.

    Returns:
        A list of :class:`LintError` instances. Empty list means the catalog
        is well-formed. Order is unspecified; callers MUST NOT depend on
        ordering.
    """
    if catalog is None:
        catalog = PROMPT_NAMES
    errors: list[LintError] = []
    seen_names: set[str] = set()

    for entry in catalog:
        if entry.name in seen_names:
            errors.append(
                LintError(
                    prompt_name=entry.name,
                    error_code="duplicate_name",
                    message=f"prompt {entry.name!r} already in catalog",
                )
            )
        else:
            seen_names.add(entry.name)

        if not isinstance(entry.domain, PromptDomain):
            errors.append(
                LintError(
                    prompt_name=entry.name,
                    error_code="invalid_domain",
                    message=f"domain {entry.domain!r} is not a PromptDomain value",
                )
            )

        try:
            from jinja2 import Environment
            from jinja2 import meta as jinja_meta

            env = Environment()
            ast = env.parse(entry.template)
            undeclared = jinja_meta.find_undeclared_variables(ast)
            declared = entry.metadata.get("required_vars", set())
            for var in undeclared:
                if var not in declared:
                    errors.append(
                        LintError(
                            prompt_name=entry.name,
                            error_code="undefined_var",
                            message=(
                                f"variable {var!r} used in template but not "
                                "in metadata.required_vars"
                            ),
                        )
                    )
        except Exception as exc:
            line = getattr(exc, "lineno", None)
            errors.append(
                LintError(
                    prompt_name=entry.name,
                    error_code="jinja_syntax",
                    message=f"Jinja2 parse failed: {exc}",
                    line=line,
                )
            )

        if not _SEMVER_RE.match(entry.version):
            errors.append(
                LintError(
                    prompt_name=entry.name,
                    error_code="invalid_version",
                    message=(
                        f"version {entry.version!r} is not a valid SemVer "
                        "MAJOR.MINOR.PATCH string"
                    ),
                )
            )

    return errors





@dataclass(frozen=True)
class LintReport:
    """Aggregate lint result for the prompt catalog (REQ-47 helper).

    Wraps the output of :func:`validate_catalog` in a structured shape with
    convenience properties (``is_clean``, ``error_count``, ``error_codes``)
    and methods (``by_code()``, ``to_dict()``) that the ``flow prompts lint``
    CLI and CI gates consume without re-parsing raw :class:`LintError` lists.

    Attributes:
        catalog: The catalog that was linted. Captured so consumers can map
            errors back to entries without passing the catalog separately.
        errors: The list of :class:`LintError` instances from
            :func:`validate_catalog`. Empty list means the catalog is clean.
    """

    catalog: tuple[PromptDef, ...]
    errors: list[LintError]

    @property
    def is_clean(self) -> bool:
        """Return ``True`` when no errors were found."""
        return len(self.errors) == 0

    @property
    def error_count(self) -> int:
        """Return the number of errors found."""
        return len(self.errors)

    @property
    def error_codes(self) -> set[str]:
        """Return the set of distinct error codes in this report."""
        return {e.error_code for e in self.errors}

    def by_code(self, code: str) -> list[LintError]:
        """Return the errors matching ``code`` (e.g., ``"jinja_syntax"``)."""
        return [e for e in self.errors if e.error_code == code]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a JSON-friendly dict.

        Used by ``flow prompts lint --json`` and CI artifacts. The shape is
        stable; downstream consumers MUST NOT depend on the order of
        ``errors_by_code`` keys (dict iteration order is implementation-
        defined for plain ``dict`` in older Python; use the explicit
        ``errors`` list for ordering-sensitive consumers).
        """
        return {
            "is_clean": self.is_clean,
            "error_count": self.error_count,
            "errors_by_code": {
                code: len(self.by_code(code)) for code in self.error_codes
            },
            "errors": [
                {
                    "prompt_name": e.prompt_name,
                    "error_code": e.error_code,
                    "message": e.message,
                    "line": e.line,
                }
                for e in self.errors
            ],
        }


def lint_prompts(
    catalog: tuple[PromptDef, ...] | None = None,
) -> LintReport:
    """Run :func:`validate_catalog` and wrap the result in a :class:`LintReport`.

    This is the public API for CI / test surfaces (per the REQ-47 contract:
    "the function MUST NOT raise on broken registries; it MUST return a list
    of warnings and let the caller decide"). Use :attr:`LintReport.is_clean`
    for the boolean clean check; use :meth:`LintReport.to_dict` for the
    ``--json`` CLI output shape.

    Args:
        catalog: The catalog to lint. ``None`` defaults to
            :data:`PROMPT_NAMES`.

    Returns:
        A :class:`LintReport` describing the catalog's lint state.
    """
    resolved = PROMPT_NAMES if catalog is None else catalog
    errors = validate_catalog(resolved)
    return LintReport(catalog=resolved, errors=errors)


__all__ = [
    "LintError",
    "LintReport",
    "PROMPT_NAMES",
    "PromptDef",
    "PromptDomain",
    "get_prompt",
    "get_prompt_metadata",
    "get_prompt_template",
    "lint_prompts",
    "list_prompts",
    "register",
    "register_prompt",
    "unregister_prompt",
    "validate_catalog",
]
