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
        bad_version = _make_broken(
            name="bad_v", template="hi {{ name }}", version="not-semver"
        )
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
        assert {e.error_code for e in report.errors} == {
            e.error_code for e in expected
        }
