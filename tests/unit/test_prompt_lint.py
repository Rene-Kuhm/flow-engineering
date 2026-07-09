"""Unit tests for lint_prompts helper surface (REQ-47 helper).

REQ-47 helper surface: ``lint_prompts()`` wraps :func:`validate_catalog` in a
structured :class:`LintReport` for CI / CLI consumers. The dataclass exposes
``is_clean``, ``error_count``, ``error_codes``, ``by_code()`` filters, and a
``to_dict()`` serialization for ``--json`` output.

Strict TDD: written BEFORE the GREEN implementation. They MUST fail until
``prompt_registry.py`` exposes :class:`LintReport` and :func:`lint_prompts`.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass

from flow_engineering import prompt_registry
from flow_engineering.prompt_registry import (
    PROMPT_NAMES,
    LintReport,
    PromptDef,
    PromptDomain,
    lint_prompts,
    validate_catalog,
)


def _make_broken(
    *,
    name: str,
    template: str = "broken placeholder",
    domain: PromptDomain | str = PromptDomain.BINDING,
    version: str = "1.0.0",
    metadata: dict | None = None,
) -> PromptDef:
    meta = dict(metadata) if metadata is not None else {}
    return PromptDef(
        name=name,
        domain=domain,  # type: ignore[arg-type]
        template=template,
        version=version,
        metadata=meta,
    )


class TestLintReportDataclass:
    def test_lint_report_is_frozen_dataclass(self) -> None:
        assert is_dataclass(LintReport)
        field_names = {f.name for f in fields(LintReport)}
        assert {"catalog", "errors"} <= field_names

    def test_lint_report_accepts_catalog_and_errors(self) -> None:
        report = LintReport(catalog=(), errors=[])
        assert report.catalog == ()
        assert report.errors == []


class TestLintPromptsClean:
    def test_lint_prompts_returns_clean_report_for_valid_catalog(self) -> None:
        report = lint_prompts()
        assert report.is_clean
        assert report.error_count == 0
        assert report.errors == []

    def test_lint_prompts_with_explicit_valid_catalog(self) -> None:
        report = lint_prompts(PROMPT_NAMES)
        assert report.is_clean

    def test_lint_prompts_handles_empty_catalog(self) -> None:
        report = lint_prompts(())
        assert report.is_clean
        assert report.catalog == ()
        assert report.errors == []


class TestLintReportProperties:
    def test_lint_prompts_is_clean_property(self) -> None:
        clean = lint_prompts()
        assert clean.is_clean is True

    def test_lint_prompts_is_clean_false_on_errors(self) -> None:
        bad = _make_broken(name="bad_version", template="hi", version="not-semver")
        report = lint_prompts((bad,))
        assert report.is_clean is False

    def test_lint_prompts_error_count_property(self) -> None:
        bad = _make_broken(name="bad_version", template="hi", version="not-semver")
        report = lint_prompts((bad,))
        assert report.error_count == 1

    def test_lint_prompts_error_count_zero_when_clean(self) -> None:
        report = lint_prompts()
        assert report.error_count == 0

    def test_lint_prompts_error_codes_property(self) -> None:
        bad_version = _make_broken(name="bad_v", template="hi {{ name }}", version="not-semver")
        report = lint_prompts((bad_version,))
        codes = report.error_codes
        assert "invalid_version" in codes
        assert "undefined_var" in codes

    def test_lint_prompts_error_codes_empty_when_clean(self) -> None:
        report = lint_prompts()
        assert report.error_codes == set()


class TestLintReportByCode:
    def test_lint_prompts_by_code_filters_correctly(self) -> None:
        bad_version = _make_broken(name="bad_v1", template="hi", version="not-semver")
        bad_dup = _make_broken(name="bad_v1", template="hi2")
        report = lint_prompts((bad_version, bad_dup))
        version_errors = report.by_code("invalid_version")
        assert all(e.error_code == "invalid_version" for e in version_errors)
        assert len(version_errors) == 1
        assert version_errors[0].prompt_name == "bad_v1"

    def test_lint_prompts_by_code_returns_empty_when_no_match(self) -> None:
        report = lint_prompts()
        assert report.by_code("template_parse_error") == []


class TestLintReportToDict:
    def test_lint_prompts_to_dict_serializes_clean(self) -> None:
        report = lint_prompts()
        d = report.to_dict()
        assert d["is_clean"] is True
        assert d["error_count"] == 0
        assert d["errors_by_code"] == {}
        assert d["errors"] == []

    def test_lint_prompts_to_dict_serializes_errors(self) -> None:
        bad = _make_broken(name="bad_to_dict", template="hi", version="not-semver")
        report = lint_prompts((bad,))
        d = report.to_dict()
        assert d["is_clean"] is False
        assert d["error_count"] == 1
        assert d["errors_by_code"] == {"invalid_version": 1}
        assert len(d["errors"]) == 1
        first = d["errors"][0]
        assert first["prompt_name"] == "bad_to_dict"
        assert first["error_code"] == "invalid_version"
        assert "not-semver" in first["message"]
        assert first["line"] is None


class TestLintPromptsReportsAllErrorCodes:
    def test_lint_prompts_reports_all_error_codes(self) -> None:
        """Build one entry per error code; lint_prompts must surface all of them."""
        bad = (
            _make_broken(name="dup_a", template="hi"),
            _make_broken(name="dup_a", template="hi again"),  # duplicate_name
            _make_broken(name="bad_dom", template="hi", domain="not_enum"),  # invalid_domain
            _make_broken(
                name="undef",
                template="hello {{ who }}",  # undefined_var
                metadata={"required_vars": set()},
            ),
            _make_broken(name="bad_ver", template="hi", version="not-semver"),  # invalid_version
            _make_broken(name="bad_jinja", template="{{ unclosed"),  # jinja_syntax
        )
        report = lint_prompts(bad)
        codes = report.error_codes
        assert "duplicate_name" in codes
        assert "invalid_domain" in codes
        assert "undefined_var" in codes
        assert "invalid_version" in codes
        assert "jinja_syntax" in codes


class TestLintPromptsCustomCatalogIsolation:
    def test_lint_prompts_with_custom_catalog_not_global(self) -> None:
        """``lint_prompts(custom)`` MUST NOT mutate ``PROMPT_NAMES``."""
        before = list(prompt_registry.PROMPT_NAMES)
        bad = _make_broken(name="custom_only", template="hi", version="not-semver")
        report = lint_prompts((bad,))
        assert report.error_count == 1
        # PROMPT_NAMES reference unchanged.
        assert list(prompt_registry.PROMPT_NAMES) == before
        # And the custom name is NOT in the global catalog.
        names = {p.name for p in prompt_registry.PROMPT_NAMES}
        assert "custom_only" not in names

    def test_lint_prompts_uses_validate_catalog_under_the_hood(self) -> None:
        """``lint_prompts(custom).errors`` MUST equal ``validate_catalog(custom)``."""
        bad = (
            _make_broken(name="eq_a", template="hi"),
            _make_broken(name="eq_a", template="hi again"),
            _make_broken(name="eq_b", template="hi", version="not-semver"),
        )
        expected = validate_catalog(bad)
        report = lint_prompts(bad)
        assert report.error_count == len(expected)
        # Compare sorted codes (implementation may differ in ordering).
        assert {e.error_code for e in report.errors} == {e.error_code for e in expected}


# ---------- T3.3 (W1): lint spec-taxonomy alias map shim ----------


class TestLintSpecTaxonomyAlias:
    """RED fixtures for the LINT_CATEGORY_SPEC_ALIASES mapping shim (W1).

    Per verify-report-pr1.md W1 + tasks-pr2.md T3.3: the spec-locked
    taxonomy (``missing_placeholder`` / ``unused_variable`` /
    ``template_parse_error`` / ``autoescape_disabled`` /
    ``missing_variable``) has ZERO name overlap with the impl's 5
    codes. Downstream consumers querying for spec-mandated names need
    a mapping shim. This shim DOES NOT rename the impl codes — it
    adds a public mapping + ``get_spec_category()`` helper so callers
    can resolve spec names to impl codes (or ``None`` for unimplemented
    spec codes).

    Acceptance criteria:
    - ``LINT_CATEGORY_SPEC_ALIASES`` is a module-level constant.
    - ``get_spec_category("missing_placeholder")`` returns
      ``"undefined_var"`` (impl equivalent).
    - ``get_spec_category("template_parse_error")`` returns
      ``"jinja_syntax"``.
    - ``get_spec_category("undefined_var")`` returns ``None`` (impl
      name has no spec equivalent; reverse mapping is NOT exposed
      because the spec mandates the spec-name as the source of truth).
    - Round-trip: ``get_spec_category("missing_placeholder") ==
      "undefined_var"`` and the impl code IS emitted by ``lint_prompts``.
    """

    def test_aliases_constant_exists_at_module_level(self) -> None:
        """``LINT_CATEGORY_SPEC_ALIASES`` is exported from the module.

        The mapping MUST live at module scope so it can be imported
        as ``from flow_engineering.prompt_registry import
        LINT_CATEGORY_SPEC_ALIASES`` without instantiating any object.
        """
        from flow_engineering import prompt_registry

        assert hasattr(prompt_registry, "LINT_CATEGORY_SPEC_ALIASES"), (
            "expected LINT_CATEGORY_SPEC_ALIASES module constant"
        )
        assert isinstance(prompt_registry.LINT_CATEGORY_SPEC_ALIASES, dict), (
            "expected LINT_CATEGORY_SPEC_ALIASES to be a dict"
        )

    def test_missing_placeholder_maps_to_undefined_var(self) -> None:
        """``get_spec_category("missing_placeholder")`` returns ``"undefined_var"``.

        Per spec REQ-47: ``missing_placeholder`` is the spec-locked
        name for "Jinja2 placeholder appears in the template body but
        is not declared in metadata.required_vars". The impl's
        equivalent code is ``undefined_var``.
        """
        from flow_engineering import prompt_registry

        assert prompt_registry.get_spec_category("missing_placeholder") == ("undefined_var"), (
            f"expected missing_placeholder → undefined_var; "
            f"got {prompt_registry.get_spec_category('missing_placeholder')!r}"
        )

    def test_template_parse_error_maps_to_jinja_syntax(self) -> None:
        """``get_spec_category("template_parse_error")`` returns ``"jinja_syntax"``.

        Per spec REQ-47: ``template_parse_error`` is the spec-locked
        name for "Jinja2 template body fails to parse". The impl's
        equivalent code is ``jinja_syntax``.
        """
        from flow_engineering import prompt_registry

        assert prompt_registry.get_spec_category("template_parse_error") == "jinja_syntax"

    def test_unimplemented_spec_codes_return_none(self) -> None:
        """Spec codes the impl never emits return ``None``.

        The spec lists 5 codes; the impl only emits 2 (the other 3
        are deferred to v1.1). ``get_spec_category`` returns ``None``
        for the unimplemented spec codes so downstream consumers can
        detect "no impl equivalent yet" rather than getting a
        misleading mapping.
        """
        from flow_engineering import prompt_registry

        for unimplemented in (
            "unused_variable",
            "autoescape_disabled",
            "missing_variable",
        ):
            assert prompt_registry.get_spec_category(unimplemented) is None, (
                f"expected {unimplemented} → None (unimplemented); "
                f"got {prompt_registry.get_spec_category(unimplemented)!r}"
            )

    def test_impl_codes_have_no_reverse_mapping(self) -> None:
        """Reverse lookups (impl name → spec name) return ``None``.

        The mapping is forward-only: spec → impl. The spec mandates
        spec names as the source of truth; impl names that happen to
        not match any spec code (e.g., ``duplicate_name``,
        ``invalid_domain``, ``invalid_version``) return ``None``.
        """
        from flow_engineering import prompt_registry

        for impl_only in (
            "undefined_var",  # reverse: impl has it but spec calls it missing_placeholder
            "duplicate_name",
            "invalid_domain",
            "invalid_version",
            "jinja_syntax",
        ):
            assert prompt_registry.get_spec_category(impl_only) is None, (
                f"expected reverse lookup {impl_only} → None; "
                f"got {prompt_registry.get_spec_category(impl_only)!r}"
            )

    def test_round_trip_with_lint_prompts(self) -> None:
        """Spec code resolves to an impl code that ``lint_prompts`` actually emits.

        Triangulation: register a prompt with an undefined Jinja2
        placeholder (which ``lint_prompts`` flags as
        ``undefined_var``), then assert that
        ``get_spec_category("missing_placeholder")`` resolves to that
        same code — proving the spec→impl mapping IS end-to-end
        usable.
        """
        from flow_engineering import prompt_registry

        prompt_registry.register(
            name="bdd_test_w1_alias",
            template="hello {{ undefined_thing }}",
            domain=prompt_registry.PromptDomain.OBSERVABILITY,
            version="1.0.0",
        )
        try:
            report = prompt_registry.lint_prompts()
            spec_code = "missing_placeholder"
            impl_code = prompt_registry.get_spec_category(spec_code)
            assert impl_code is not None, f"expected spec→impl mapping for {spec_code}"
            codes_emitted = {e.error_code for e in report.errors}
            assert impl_code in codes_emitted, (
                f"expected impl_code={impl_code!r} (resolved from "
                f"spec={spec_code!r}) to appear in lint_prompts output; "
                f"got codes={codes_emitted!r}"
            )
        finally:
            prompt_registry.unregister_prompt("bdd_test_w1_alias")
