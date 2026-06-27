"""Unit tests for ``render_prompt`` / ``render_prompt_safe`` / ``list_required_vars`` (REQ-46).

REQ-46: a shared Jinja2-based renderer that substitutes ``**kwargs`` into a
prompt template fetched by name from the ``PROMPT_NAMES`` catalog. Strict mode
(``render_prompt``) raises ``jinja2.UndefinedError`` on missing declared vars;
``render_prompt_safe`` substitutes the literal sentinel ``<{var_name}>`` for
missing vars (per design D4 — CLI inspection mode). ``list_required_vars``
parses the template AST and returns the set of undeclared variable names so
CLI surfaces know which inputs to prompt the user for.

Strict TDD: written BEFORE the implementation. They MUST fail with
``AttributeError: module 'flow_engineering.prompt_registry' has no attribute
'render_prompt'`` until the impl lands in ``prompt_registry.py``.

The existing ``PROMPT_NAMES`` catalog uses Python ``.format()`` style templates
(``{test_command}``); Jinja2 treats those as literal text, so the tests below
register NEW prompts with Jinja2 ``{{ var }}`` syntax via ``register()`` to
exercise the substitution path without mutating the legacy catalog.
"""

from __future__ import annotations

import pytest
from jinja2 import UndefinedError

from flow_engineering import prompt_registry
from flow_engineering.prompt_registry import (
    list_required_vars,
    render_prompt,
    render_prompt_safe,
)


@pytest.fixture
def jinja_prompts() -> None:
    """Register NEW prompts with Jinja2 syntax for substitution tests.

    Uses the existing ``register()`` shorthand. Cleanup via
    ``unregister_prompt`` after the test to keep the catalog pristine.
    """
    prompt_registry.register(
        name="jinja_simple",
        template="Hello, {{ user_name }}!",
        domain=prompt_registry.PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=("user_name",),
    )
    prompt_registry.register(
        name="jinja_numeric",
        template="count={{ count }} pi={{ pi }}",
        domain=prompt_registry.PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=("count", "pi"),
    )
    prompt_registry.register(
        name="jinja_missing",
        template="Hello, {{ user_name }}!",
        domain=prompt_registry.PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=("user_name",),
    )
    prompt_registry.register(
        name="jinja_multiline",
        template=(
            "Line one with {{ a }}.\n"
            "Line two with {{ b }}.\n"
            "Line three.\n"
        ),
        domain=prompt_registry.PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=("a", "b"),
    )
    prompt_registry.register(
        name="jinja_no_vars",
        template="Static text, no placeholders.",
        domain=prompt_registry.PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=(),
    )
    yield
    for name in (
        "jinja_simple",
        "jinja_numeric",
        "jinja_missing",
        "jinja_multiline",
        "jinja_no_vars",
    ):
        prompt_registry.unregister_prompt(name)


class TestRenderPromptSubstitutesStringKwarg:
    def test_renders_string_variable(self, jinja_prompts: None) -> None:
        assert render_prompt("jinja_simple", user_name="World") == "Hello, World!"

    def test_renders_empty_string_variable(self, jinja_prompts: None) -> None:
        assert render_prompt("jinja_simple", user_name="") == "Hello, !"


class TestRenderPromptSubstitutesNumericKwargs:
    def test_renders_int_variable(self, jinja_prompts: None) -> None:
        assert render_prompt("jinja_numeric", count=42, pi=3.14) == "count=42 pi=3.14"

    def test_renders_zero_and_negative(self, jinja_prompts: None) -> None:
        assert render_prompt("jinja_numeric", count=0, pi=-1.5) == "count=0 pi=-1.5"


class TestRenderPromptRaisesUndefinedErrorOnMissingKwarg:
    def test_strict_mode_raises_when_var_missing(self, jinja_prompts: None) -> None:
        with pytest.raises(UndefinedError) as excinfo:
            render_prompt("jinja_missing")
        assert "user_name" in str(excinfo.value)

    def test_strict_mode_renders_when_all_vars_provided(
        self, jinja_prompts: None
    ) -> None:
        assert (
            render_prompt("jinja_missing", user_name="Filled") == "Hello, Filled!"
        )


class TestRenderPromptRaisesKeyErrorOnUnknownName:
    def test_unknown_prompt_name_raises_key_error(self) -> None:
        with pytest.raises(KeyError) as excinfo:
            render_prompt("definitely_not_in_catalog")
        assert "definitely_not_in_catalog" in str(excinfo.value)


class TestRenderPromptSafeReturnsSentinelForMissingKwargs:
    def test_safe_substitutes_sentinel(self, jinja_prompts: None) -> None:
        result = render_prompt_safe("jinja_missing")
        assert result == "Hello, <user_name>!"

    def test_safe_with_provided_var_substitutes_value(self, jinja_prompts: None) -> None:
        result = render_prompt_safe("jinja_missing", user_name="World")
        assert result == "Hello, World!"

    def test_safe_never_raises_on_missing_var(self, jinja_prompts: None) -> None:
        # Should NOT raise even when called with no kwargs for a template
        # that requires vars.
        result = render_prompt_safe("jinja_simple")
        assert result == "Hello, <user_name>!"


class TestListRequiredVarsReturnsUndeclaredVariables:
    def test_returns_set_of_vars(self, jinja_prompts: None) -> None:
        vars_ = list_required_vars("jinja_numeric")
        assert vars_ == {"count", "pi"}

    def test_returns_empty_for_no_placeholder_template(
        self, jinja_prompts: None
    ) -> None:
        assert list_required_vars("jinja_no_vars") == set()

    def test_returns_single_var(self, jinja_prompts: None) -> None:
        assert list_required_vars("jinja_simple") == {"user_name"}


class TestRenderPromptHandlesMultilineTemplates:
    def test_multiline_keeps_trailing_newline(self, jinja_prompts: None) -> None:
        result = render_prompt("jinja_multiline", a="alpha", b="beta")
        assert result == (
            "Line one with alpha.\n"
            "Line two with beta.\n"
            "Line three.\n"
        )

    def test_multiline_does_not_strip_internal_whitespace(
        self, jinja_prompts: None
    ) -> None:
        result = render_prompt("jinja_multiline", a="x", b="y")
        assert "Line one with x." in result
        assert "Line two with y." in result
        assert "Line three." in result