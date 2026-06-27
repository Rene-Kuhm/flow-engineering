"""Unit tests for prompt_registry validation surface (REQ-47 lint foundation).

REQ-47 lint foundation: ``register()`` shorthand + ``validate_catalog()`` helper
that detects the 5 catalog error codes BEFORE the heavier ``lint_prompts()``
surface (T1.6 / T1.5 in tasks.md) builds on top.

Validation rules covered:
- ``duplicate_name`` -- same ``name`` appearing twice in the catalog.
- ``invalid_domain`` -- domain that is not a :class:`PromptDomain` value.
- ``jinja_syntax`` -- template fails to parse as Jinja2.
- ``undefined_var`` -- ``{{ var }}`` in template but not in metadata.required_vars.
- ``invalid_version`` -- version string that does not match ``MAJOR.MINOR.PATCH``.

Strict TDD: written BEFORE the GREEN implementation. They MUST fail until
``prompt_registry.py`` exposes :class:`LintError`, :func:`register`, and
:func:`validate_catalog`.
"""

from __future__ import annotations

import pytest

from flow_engineering import prompt_registry
from flow_engineering.prompt_registry import (
    PROMPT_NAMES,
    LintError,
    PromptDef,
    PromptDomain,
    register,
    unregister_prompt,
    validate_catalog,
)


def _make_broken(
    *,
    name: str = "broken",
    template: str = "broken placeholder",
    domain: PromptDomain | str = PromptDomain.BINDING,
    version: str = "1.0.0",
    metadata: dict | None = None,
) -> PromptDef:
    """Build a PromptDef-shaped broken entry with a unique internal registry name."""
    meta = dict(metadata) if metadata is not None else {}
    # Use a unique name per call so the tuple does not collide across tests.
    return PromptDef(
        name=name,
        domain=domain,  # type: ignore[arg-type]
        template=template,
        version=version,
        metadata=meta,
    )


class TestLintErrorDataclass:
    def test_lint_error_is_frozen_dataclass(self) -> None:
        from dataclasses import fields, is_dataclass

        assert is_dataclass(LintError)
        field_names = {f.name for f in fields(LintError)}
        assert {"prompt_name", "error_code", "message", "line"} <= field_names

    def test_lint_error_supports_all_five_error_codes(self) -> None:
        for code in (
            "missing_placeholder",
            "undefined_var",
            "jinja_syntax",
            "duplicate_name",
            "invalid_domain",
        ):
            err = LintError(prompt_name="x", error_code=code, message="m")
            assert err.error_code == code

    def test_lint_error_line_is_optional(self) -> None:
        err = LintError(prompt_name="x", error_code="jinja_syntax", message="m")
        assert err.line is None
        err_with_line = LintError(
            prompt_name="x", error_code="jinja_syntax", message="m", line=7
        )
        assert err_with_line.line == 7


class TestRegisterShorthand:
    def test_register_shorthand_creates_promptdef(self) -> None:
        register(
            "test_register_shorthand_1",
            "hello {{ name }}",
            PromptDomain.BINDING,
            version="2.3.4",
        )
        try:
            entry = prompt_registry.get_prompt("test_register_shorthand_1")
            assert entry.name == "test_register_shorthand_1"
            assert entry.template == "hello {{ name }}"
            assert entry.domain == PromptDomain.BINDING
            assert entry.version == "2.3.4"
        finally:
            unregister_prompt("test_register_shorthand_1")

    def test_register_shorthand_accepts_kwargs_as_metadata(self) -> None:
        register(
            "test_register_shorthand_2",
            "model={{ model }} max={{ max_tokens }}",
            PromptDomain.RUNTIME,
            version="1.0.0",
            model="gpt-4",
            max_tokens=512,
            required_vars=("model", "max_tokens"),
        )
        try:
            entry = prompt_registry.get_prompt("test_register_shorthand_2")
            assert entry.metadata == {
                "model": "gpt-4",
                "max_tokens": 512,
                "required_vars": ("model", "max_tokens"),
            }
        finally:
            unregister_prompt("test_register_shorthand_2")

    def test_register_shorthand_default_version(self) -> None:
        register(
            "test_register_shorthand_3",
            "no vars here",
            PromptDomain.OBSERVABILITY,
        )
        try:
            entry = prompt_registry.get_prompt("test_register_shorthand_3")
            assert entry.version == "1.0.0"
        finally:
            unregister_prompt("test_register_shorthand_3")

    def test_register_shorthand_duplicate_raises(self) -> None:
        # Strict duplicate check: registering an existing name raises ValueError.
        with pytest.raises(ValueError, match="already registered"):
            register("strict_tdd", "dupe", PromptDomain.OBSERVABILITY)


class TestValidateCatalogClean:
    def test_validate_catalog_returns_empty_for_valid_catalog(self) -> None:
        # The current PROMPT_NAMES catalog is well-formed (Python format
        # templates are valid literal text in Jinja2, so no jinja_syntax /
        # undefined_var errors fire; domains are PromptDomain values; versions
        # match semver; names are unique).
        errors = validate_catalog()
        assert errors == []

    def test_validate_catalog_explicit_valid_tuple(self) -> None:
        # Same as above but pass the catalog explicitly.
        errors = validate_catalog(PROMPT_NAMES)
        assert errors == []

    def test_validate_catalog_empty_tuple_returns_empty(self) -> None:
        errors = validate_catalog(())
        assert errors == []


class TestValidateCatalogDuplicateNames:
    def test_validate_catalog_detects_duplicate_names(self) -> None:
        dup_a = _make_broken(name="dup_x", template="first body")
        dup_b = _make_broken(name="dup_x", template="second body")
        errors = validate_catalog((dup_a, dup_b))
        codes = [e.error_code for e in errors]
        assert "duplicate_name" in codes
        dup_err = next(e for e in errors if e.error_code == "duplicate_name")
        assert dup_err.prompt_name == "dup_x"
        assert "dup_x" in dup_err.message


class TestValidateCatalogInvalidDomain:
    def test_validate_catalog_detects_invalid_domain(self) -> None:
        broken = _make_broken(name="bad_domain", template="hi", domain="not_a_domain")
        errors = validate_catalog((broken,))
        codes = [e.error_code for e in errors]
        assert "invalid_domain" in codes
        err = next(e for e in errors if e.error_code == "invalid_domain")
        assert err.prompt_name == "bad_domain"


class TestValidateCatalogUndefinedVar:
    def test_validate_catalog_detects_undefined_jinja_variables(self) -> None:
        # `{{ name }}` used in template but NOT declared in metadata.required_vars.
        broken = _make_broken(
            name="undefined_var_test",
            template="hello {{ name }} from {{ place }}",
            metadata={"required_vars": {"name"}},
        )
        errors = validate_catalog((broken,))
        undefined = [e for e in errors if e.error_code == "undefined_var"]
        assert len(undefined) == 1
        assert undefined[0].prompt_name == "undefined_var_test"
        assert "place" in undefined[0].message

    def test_validate_catalog_passes_when_all_vars_declared(self) -> None:
        ok = _make_broken(
            name="vars_declared_ok",
            template="hello {{ name }} from {{ place }}",
            metadata={"required_vars": {"name", "place"}},
        )
        errors = validate_catalog((ok,))
        assert [e for e in errors if e.error_code == "undefined_var"] == []


class TestValidateCatalogInvalidSemver:
    def test_validate_catalog_detects_invalid_semver(self) -> None:
        broken = _make_broken(name="bad_version", template="hi", version="not.a.version")
        errors = validate_catalog((broken,))
        codes = [e.error_code for e in errors]
        assert "invalid_version" in codes
        err = next(e for e in errors if e.error_code == "invalid_version")
        assert err.prompt_name == "bad_version"
        assert "not.a.version" in err.message

    def test_validate_catalog_accepts_valid_semver(self) -> None:
        for version in ("0.0.1", "1.0.0", "10.20.30"):
            ok = _make_broken(
                name=f"ok_v_{version.replace('.', '_')}",
                version=version,
            )
            errors = validate_catalog((ok,))
            assert [e for e in errors if e.error_code == "invalid_version"] == []


class TestValidateCatalogJinjaSyntax:
    def test_validate_catalog_detects_jinja_syntax_errors(self) -> None:
        # Unclosed Jinja2 tag is a syntax error.
        broken = _make_broken(
            name="jinja_broken",
            template="hello {{ unclosed tag",
        )
        errors = validate_catalog((broken,))
        syntax_errors = [e for e in errors if e.error_code == "jinja_syntax"]
        assert len(syntax_errors) == 1
        assert syntax_errors[0].prompt_name == "jinja_broken"

    def test_validate_catalog_jinja_syntax_error_has_line(self) -> None:
        # Jinja2 reports a line number on TemplateSyntaxError; we MUST surface
        # it on the LintError so callers can point to the broken line.
        broken = _make_broken(
            name="jinja_broken_with_line",
            template="first line\n{{ unclosed",
        )
        errors = validate_catalog((broken,))
        syntax_errors = [e for e in errors if e.error_code == "jinja_syntax"]
        assert len(syntax_errors) == 1
        assert syntax_errors[0].line is not None
        assert syntax_errors[0].line >= 1


class TestValidateCatalogMultipleErrors:
    def test_validate_catalog_reports_all_errors_per_entry(self) -> None:
        # One broken entry with multiple problems: invalid version + undefined var.
        broken = _make_broken(
            name="multi_problem",
            template="hello {{ user }} {{ count }}",
            version="not-semver",
            metadata={"required_vars": {"user"}},
        )
        errors = validate_catalog((broken,))
        codes = {e.error_code for e in errors}
        assert "invalid_version" in codes
        assert "undefined_var" in codes
