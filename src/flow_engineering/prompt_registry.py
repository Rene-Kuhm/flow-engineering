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
import time as _time
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateError,
    UndefinedError,
    meta,
    select_autoescape,
)


class PromptRenderError(Exception):
    """Base class for render-related failures (REQ-46).

    Per design D9, the future ``flow prompts show <id>`` CLI maps this
    exception to exit code 5 (render error). Subclasses cover the specific
    failure modes (unknown prompt id, missing variable, template parse
    error, Jinja2 render error).

    Attributes:
        payload: Structured diagnostic dict with at least ``"prompt"``
            (the prompt id), ``"reason"`` (a stable short string code),
            and ``"error"`` (the human-readable message). CLI surfaces
            read ``payload`` directly; downstream consumers MUST NOT
            depend on the ``str(exc)`` format (which mirrors ``error``).
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload.get("error", "prompt render failed"))
        self.payload = dict(payload)


class PromptNotFoundError(PromptRenderError, KeyError):
    """Raised when ``render_prompt`` is called with an unknown prompt name.

    Inherits from both ``PromptRenderError`` (for the CLI exit-code-5
    mapping per design D9) and ``KeyError`` (preserves the original
    REQ-46 §"render contract" contract that unknown ids raise ``KeyError``).
    Use ``isinstance(exc, KeyError)`` for legacy callers that catch
    ``KeyError`` directly.
    """

    def __init__(self, prompt_id: str) -> None:
        PromptRenderError.__init__(
            self,
            {
                "prompt": prompt_id,
                "reason": "not_found",
                "error": f"unknown prompt {prompt_id!r}",
            },
        )
        KeyError.__init__(self, prompt_id)


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


_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
"""Filesystem location of the canonical ``.j2`` prompt templates (REQ-46 W3).

Resolved at module load as ``<repo-root>/prompts/`` (the package lives
at ``src/flow_engineering/prompt_registry.py``; three ``parent``s walk
up to the repo root). The directory is bundled with the project so
``prompts/`` is always co-located with ``pyproject.toml`` regardless of
the install layout.
"""


def load_template_from_file(path: Path | str) -> str:
    """Read a Jinja2 template body from a ``.j2`` file on disk.

    REQ-46 W3: the catalog's template strings live as standalone
    ``prompts/<name>.j2`` files so editors / reviewers can view them
    without opening Python. This helper reads the file, strips the
    trailing newline (so the rendered output matches the inline
    ``template=...`` argument exactly when the .j2 file ends with a
    newline — common convention for POSIX text files), and returns
    the body.

    Args:
        path: Filesystem path to the ``.j2`` file. May be absolute or
            relative to the current working directory.

    Returns:
        The template body as a single string.

    Raises:
        FileNotFoundError: When ``path`` does not exist. Surfaces
            immediately at module import if a ``PROMPT_NAMES`` entry
            is misnamed (fail-fast beats silent fallback).
        OSError: When the file is unreadable (permission, encoding, etc.).
    """
    return Path(path).read_text(encoding="utf-8").rstrip("\n")


PROMPT_NAMES: tuple[PromptDef, ...] = (
    PromptDef(
        name="strict_tdd",
        domain=PromptDomain.OBSERVABILITY,
        template=load_template_from_file(_PROMPTS_DIR / "strict_tdd.j2"),
        version="1.0.0",
        metadata={
            "source": "prompts/strict_tdd.j2",
            "template_file": "prompts/strict_tdd.j2",
            "variables": ("test_command",),
        },
    ),
    PromptDef(
        name="auto_suggest_header",
        domain=PromptDomain.BINDING,
        template=load_template_from_file(_PROMPTS_DIR / "auto_suggest_header.j2"),
        version="1.0.0",
        metadata={
            "source": "prompts/auto_suggest_header.j2",
            "template_file": "prompts/auto_suggest_header.j2",
            "variables": (),
        },
    ),
    PromptDef(
        name="auto_suggest_footer",
        domain=PromptDomain.BINDING,
        template=load_template_from_file(_PROMPTS_DIR / "auto_suggest_footer.j2"),
        version="1.0.0",
        metadata={
            "source": "prompts/auto_suggest_footer.j2",
            "template_file": "prompts/auto_suggest_footer.j2",
            "variables": (),
        },
    ),
    PromptDef(
        name="auto_suggest_empty",
        domain=PromptDomain.BINDING,
        template=load_template_from_file(_PROMPTS_DIR / "auto_suggest_empty.j2"),
        version="1.0.0",
        metadata={
            "source": "prompts/auto_suggest_empty.j2",
            "template_file": "prompts/auto_suggest_empty.j2",
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

REQ-46 W3: the actual template strings live on disk under
``<repo-root>/prompts/*.j2`` so editors and reviewers can view them
without opening Python. ``load_template_from_file()`` reads them at
module-load time; the catalog still holds the resolved text so callers
that need ``prompt.template`` don't have to hit the filesystem on
every render. The ``metadata.template_file`` key records the original
path so the future ``flow prompts list --source`` CLI can render it.
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
    "PromptNotFoundError",
    "PromptRenderError",
    "get_prompt",
    "get_prompt_metadata",
    "get_prompt_template",
    "get_spec_category",
    "lint_prompts",
    "list_prompts",
    "list_required_vars",
    "load_template_from_file",
    "register",
    "register_prompt",
    "render_prompt",
    "render_prompt_safe",
    "unregister_prompt",
    "validate_catalog",
]


# ---------- W1: spec-taxonomy alias map (PR#1 verify-report W1 carry-forward) ----------


"""Forward mapping from spec-locked REQ-47 category names to impl codes (W1).

Per verify-report-pr1.md W1 + spec REQ-47: the spec mandates 5
category names (``missing_placeholder``, ``unused_variable``,
``template_parse_error``, ``autoescape_disabled``,
``missing_variable``). The impl ships 5 different names (no
overlap). This mapping is the forward bridge from spec name →
impl name so downstream consumers querying for spec-mandated
names can resolve them. Values are:

- ``str`` — the impl code emitted by :func:`lint_prompts` /
  :func:`validate_catalog`.
- ``None`` — the spec name has NO impl equivalent yet (deferred
  to v1.1; documented in verify-report-pr1.md W1).

The mapping is FORWARD-ONLY (spec → impl). Reverse lookups
(impl name → spec name) return ``None`` because:
- The spec mandates spec names as the source of truth.
- The impl has 3 codes the spec doesn't cover at all
  (``duplicate_name``, ``invalid_domain``, ``invalid_version``).

Migration path: when the v0.8.x ``PromptDef → PromptEntry``
schema migration lands, rename impl codes to match the spec
taxonomy and remove this shim (the proposal's deferral path).
"""

LINT_CATEGORY_SPEC_ALIASES: dict[str, str | None] = {
    "missing_placeholder": "undefined_var",
    "template_parse_error": "jinja_syntax",
    "unused_variable": None,
    "autoescape_disabled": None,
    "missing_variable": None,
}


def get_spec_category(spec_name: str) -> str | None:
    """Resolve a spec-locked REQ-47 category name to its impl equivalent.

    Per verify-report-pr1.md W1: downstream consumers (future REQ-52
    counters, REQ-53 docs generator) querying for the spec-mandated
    category names can use this helper instead of duplicating the
    taxonomy in their own code.

    Args:
        spec_name: One of the 5 spec-locked category names
            (``missing_placeholder``, ``unused_variable``,
            ``template_parse_error``, ``autoescape_disabled``,
            ``missing_variable``).

    Returns:
        The impl code emitted by :func:`lint_prompts` for that spec
        name (``"undefined_var"`` or ``"jinja_syntax"``), or
        ``None`` when the spec name has NO impl equivalent yet
        (deferred to v1.1; downstream consumers should treat
        ``None`` as "no-op: implement later").

    Raises:
        Nothing. Unknown spec names return ``None`` defensively (the
        mapping is forward-only and closed-world by intent).
    """
    return LINT_CATEGORY_SPEC_ALIASES.get(spec_name)


@lru_cache(maxsize=1)
def _strict_jinja_env() -> Environment:
    """Return the shared strict Jinja2 ``Environment`` used by :func:`render_prompt`.

    ``StrictUndefined`` raises ``jinja2.UndefinedError`` on any undeclared
    variable; ``keep_trailing_newline=True`` mirrors the existing
    ``scaffold._env()`` behavior. Cached at module scope so the
    ``Environment`` is constructed once per process (Jinja2 templates are
    internally cached by the ``Environment``).
    """
    return Environment(undefined=StrictUndefined, keep_trailing_newline=True)


def _env(loader_path: Path | str | None = None) -> Environment:
    """Build the shared Jinja2 ``Environment`` (REQ-46 W4 hoisted helper).

    REQ-46 W4: previously ``scaffold._env()`` and ``prompt_registry._safe_jinja_env()``
    each carried their own copy of the kwargs
    (``autoescape=select_autoescape()``, ``keep_trailing_newline=True``).
    That duplicated the policy in two places — easy to drift if a future
    maintainer added an option to one but not the other. This helper is
    the single source of truth for those flags.

    Args:
        loader_path: When provided, the returned env is configured with a
            :class:`jinja2.FileSystemLoader` rooted at this directory so
            callers can use ``env.get_template("<name>.j2")`` to fetch a
            file by name (used by ``scaffold.render_new_change`` etc.).
            When ``None``, the env has no loader and only supports
            ``env.from_string(<source>)``.

    Returns:
        A fresh :class:`jinja2.Environment` instance. The function is
        intentionally NOT cached: each caller wants its own loader
        configuration, and Jinja2 internally caches parsed templates
        within each ``Environment``.
    """
    kwargs: dict[str, Any] = {
        "autoescape": select_autoescape(),
        "keep_trailing_newline": True,
    }
    if loader_path is not None:
        kwargs["loader"] = FileSystemLoader(str(loader_path))
    return Environment(**kwargs)


def _safe_jinja_env() -> Environment:
    """Return a permissive Jinja2 ``Environment`` used by :func:`render_prompt_safe`.

    The default ``Undefined`` silently emits empty strings for missing
    variables, but :func:`render_prompt_safe` substitutes the literal
    sentinel ``<{var_name}>`` BEFORE rendering so the user sees exactly
    which variables were missing (per design D4 — CLI inspection mode).

    REQ-46 W2: ``select_autoescape(default_for_string=True)`` enables
    HTML auto-escaping for any ``.j2`` file loaded from disk that ends
    in ``.html``/``.htm``/``.xml`` AND for any string template that
    ends with those extensions when an ``autoescape`` callable is
    supplied. The ``default_for_string=True`` flag also auto-escapes
    string templates by default when no filename is known, so
    untrusted prompt content rendered through ``render_prompt_safe``
    cannot accidentally inject HTML/JS into CLI output (per the
    REQ-46 verify-report W2 carry-forward: ``autoescape_disabled``
    spec code maps to a v1.1 impl that emits a lint warning when a
    template explicitly opts OUT of auto-escape).
    """
    return Environment(
        autoescape=select_autoescape(default_for_string=True),
        keep_trailing_newline=True,
    )


def render_prompt(name: str, **kwargs: Any) -> str:
    """Render a prompt by name with ``**kwargs`` substituted via Jinja2 (REQ-46).

    Looks up the prompt in :data:`PROMPT_NAMES` via :func:`get_prompt`,
    compiles its template body through the shared strict Jinja2
    ``Environment``, and renders with ``**kwargs``. Strict mode raises
    :class:`PromptRenderError` on missing declared variables so
    runtime callers cannot accidentally inject empty strings into agent
    context (per design OQ-4). The CLI maps :class:`PromptRenderError`
    to exit code 5 per design D9.

    The 4 migrated entries (``strict_tdd``, ``auto_suggest_header``,
    ``auto_suggest_footer``, ``auto_suggest_empty``) use Python
    ``str.format()`` syntax (``{test_command}``); Jinja2 treats those
    braces as literal text, so the renderer detects templates without
    Jinja2 ``{{ var }}`` placeholders and falls back to
    ``prompt.template.format(**kwargs)``. This keeps the public
    ``render_prompt(name, **kwargs)`` API uniform across both template
    styles (REQ-46 W5).

    Args:
        name: The catalog identifier (e.g., ``"strict_tdd"``).
        **kwargs: Variable substitutions passed to ``template.render(**kwargs)``.
            NOTE: ``name`` cannot be used as a template variable because it
            would clash with the catalog identifier positional argument;
            pick a different name for the variable (e.g., ``user_name``).

    Returns:
        The rendered string with ``**kwargs`` substituted into the
        template body. Trailing newline is preserved.

    Raises:
        PromptNotFoundError: When ``name`` is not in the catalog. Also
            a :class:`KeyError` subclass for legacy callers.
        PromptRenderError: When the template references a variable
            that was not provided in ``**kwargs`` (Jinja2 ``UndefinedError``
            or Python ``.format()`` ``KeyError``), or when the template
            fails to parse / render.

    Examples:
        >>> render_prompt("jinja_simple", user_name="World")
        'Hello, World!'
        >>> render_prompt("strict_tdd", test_command="pytest")
        'STRICT TDD MODE IS ACTIVE. Test runner: pytest. ...'
    """
    _render_started_monotonic = _time.monotonic()
    var_keys = tuple(kwargs.keys())
    try:
        prompt = get_prompt(name)
    except KeyError as exc:
        _emit_render_record(
            name=name,
            start_monotonic=_render_started_monotonic,
            ok=False,
            error="unknown",
            var_keys=var_keys,
        )
        raise PromptNotFoundError(name) from exc
    # Surface the prompt's domain into the counter labels (REQ-V1.1.4).
    # ``PromptDomain`` is a str-Enum so ``.value`` returns the lowercase
    # string ("binding" / "drift" / ...) directly.
    _prompt_domain_value: str = prompt.domain.value
    env = _strict_jinja_env()
    template = env.from_string(prompt.template)
    try:
        rendered = template.render(**kwargs)
    except UndefinedError as exc:
        _emit_render_record(
            name=name,
            start_monotonic=_render_started_monotonic,
            ok=False,
            error="missing_var",
            var_keys=var_keys,
            domain=_prompt_domain_value,
        )
        raise PromptRenderError(
            {
                "prompt": name,
                "reason": "missing_var",
                "variable": getattr(exc, "message", str(exc)),
                "error": (
                    f"prompt {name!r} requires undefined variable: "
                    f"{getattr(exc, 'message', str(exc))}"
                ),
            }
        ) from exc
    except TemplateError as exc:
        _emit_render_record(
            name=name,
            start_monotonic=_render_started_monotonic,
            ok=False,
            error="template_error",
            var_keys=var_keys,
            domain=_prompt_domain_value,
        )
        raise PromptRenderError(
            {
                "prompt": name,
                "reason": "template_error",
                "error": f"prompt {name!r} template error: {exc.message}",
            }
        ) from exc

    # W5 fallback: templates that contain NO Jinja2 placeholders (the 4
    # migrated entries) are treated as Python ``str.format()`` templates
    # so the public ``render_prompt(name, **kwargs)`` API works for both
    # template styles. Jinja2 has already substituted anything it found;
    # if there were no Jinja2 placeholders AND the output is identical
    # to the source template, we still need to do the .format() pass.
    if rendered == prompt.template:
        ast = env.parse(prompt.template)
        if not meta.find_undeclared_variables(ast):
            try:
                formatted = prompt.template.format(**kwargs)
            except KeyError as exc:
                var = exc.args[0]
                _emit_render_record(
                    name=name,
                    start_monotonic=_render_started_monotonic,
                    ok=False,
                    error="missing_var",
                    var_keys=var_keys,
                    domain=_prompt_domain_value,
                )
                raise PromptRenderError(
                    {
                        "prompt": name,
                        "reason": "missing_var",
                        "variable": var,
                        "error": (
                            f"prompt {name!r} requires undefined variable: "
                            f"{var}"
                        ),
                    }
                ) from exc
            else:
                _emit_render_record(
                    name=name,
                    start_monotonic=_render_started_monotonic,
                    ok=True,
                    error=None,
                    var_keys=var_keys,
                    domain=_prompt_domain_value,
                )
                return formatted
    _emit_render_record(
        name=name,
        start_monotonic=_render_started_monotonic,
        ok=True,
        error=None,
        var_keys=var_keys,
        domain=_prompt_domain_value,
    )
    return rendered


def _emit_render_record(
    *,
    name: str,
    start_monotonic: float,
    ok: bool,
    error: str | None,
    var_keys: tuple[str, ...],
    domain: str | None = None,
) -> None:
    """Emit one JSONL line to the prompt render sink (REQ-V1.1.3) and
    increment the prompt render counters (REQ-V1.1.4).

    Best-effort: failures are swallowed at the :func:`record_prompt_render`
    boundary so a missing dir / full disk never crashes the render path.
    The sink is opt-in via ``FLOW_PROMPT_LOG=1`` (default OFF) so write-free
    agent flows are untouched. The observability counters are emitted
    unconditionally — they flow through :func:`observability.increment`
    which is itself best-effort.
    """
    from flow_engineering.observability import record_prompt_render_summary
    from flow_engineering.prompt_render_log import record_prompt_render

    elapsed_ms = (_time.monotonic() - start_monotonic) * 1000.0
    record_prompt_render(
        prompt_id=name,
        rendered_at=_time.time(),
        elapsed_ms=elapsed_ms,
        ok=ok,
        error=error,
        var_keys=var_keys,
    )
    # Surface to the observability dashboard (REQ-V1.1.4).
    record_prompt_render_summary(
        prompt_id=name,
        domain=domain or "unknown",
        elapsed_ms=elapsed_ms,
        ok=ok,
        error=error,
    )


def render_prompt_safe(name: str, **kwargs: Any) -> str:
    """Render a prompt with sentinel substitution for missing declared vars (REQ-46, D4).

    For each declared variable in ``metadata.required_vars`` that is not
    present in ``**kwargs``, the literal sentinel ``<{var_name}>`` is
    substituted BEFORE rendering. Used by CLI inspection surfaces
    (future ``flow prompts show <id>``) where informative output matters
    more than hard failure.

    Args:
        name: The catalog identifier.
        **kwargs: Variable substitutions; missing declared vars get the
            ``<{var_name}>`` sentinel automatically. NOTE: ``name`` cannot
            be used as a template variable; pick a different name.

    Returns:
        The rendered string with sentinels in place of missing declared
        variables. Never raises on missing variables.

    Raises:
        KeyError: When ``name`` is not in the catalog (propagated from
            :func:`get_prompt`).
    """
    prompt = get_prompt(name)
    declared = set(prompt.metadata.get("required_vars", ()))
    safe_kwargs: dict[str, Any] = dict(kwargs)
    for var_name in declared - set(safe_kwargs):
        safe_kwargs[var_name] = f"<{var_name}>"
    template = _safe_jinja_env().from_string(prompt.template)
    return template.render(**safe_kwargs)


def list_required_vars(name: str) -> set[str]:
    """Return the set of variables a prompt template references (REQ-46 helper).

    Parses the template AST via :func:`jinja2.meta.find_undeclared_variables`
    and returns the names of every Jinja2 placeholder not declared by the
    template itself. Useful for CLI surfaces that need to prompt the user
    for inputs (future ``flow prompts show <id> --var``).

    Args:
        name: The catalog identifier.

    Returns:
        A set of variable name strings (possibly empty for templates
        with no placeholders).

    Raises:
        KeyError: When ``name`` is not in the catalog (propagated from
            :func:`get_prompt`).
    """
    prompt = get_prompt(name)
    ast = _strict_jinja_env().parse(prompt.template)
    return set(meta.find_undeclared_variables(ast))
