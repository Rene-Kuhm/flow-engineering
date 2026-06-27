"""Unit tests for the inline prompt migration (REQ-45 T1.3 + D10).

REQ-45 D10: the 4 existing inline prompt constants
(``STRICT_TDD_PROMPT``, ``EMPTY_PROMPT_TEXT``, ``PROMPT_HEADER``,
``PROMPT_FOOTER``) become thin wrappers that delegate to the
``prompt_registry`` catalog for v0.7.0. The wrappers MUST preserve
byte-equivalence with the pre-migration constants so existing call
sites + golden tests continue to pass without modification.

Strict TDD: written BEFORE the migration. They MUST fail until the
wrapper refactor lands in ``strict_tdd.py`` and
``auto_suggest_code_refs.py``.
"""

from __future__ import annotations

import pytest

from flow_engineering import prompt_registry
from flow_engineering.auto_suggest_code_refs import (
    EMPTY_PROMPT_TEXT,
    PROMPT_FOOTER,
    PROMPT_HEADER,
    format_suggestion_prompt,
)
from flow_engineering.strict_tdd import STRICT_TDD_PROMPT


# Pre-migration canonical strings (locked snapshot, byte-for-byte).
_LEGACY_STRICT_TDD = (
    "STRICT TDD MODE IS ACTIVE. Test runner: {test_command}. "
    "You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."
)
_LEGACY_EMPTY = "No auto-suggested bindings available."
_LEGACY_HEADER = "Auto-suggested code bindings:"
_LEGACY_FOOTER = (
    "Confirm: [a]ll / [n]one / comma-separated numbers (e.g., 1,3)"
)


class TestStrictTddPromptAlias:
    def test_strict_tdd_prompt_matches_registry_template(self) -> None:
        registry_template = prompt_registry.get_prompt_template("strict_tdd")
        assert STRICT_TDD_PROMPT == registry_template

    def test_strict_tdd_prompt_is_registry_template_by_identity(self) -> None:
        # The post-migration contract: STRICT_TDD_PROMPT IS the same
        # string object returned by the registry. Pre-migration (when
        # the constant was a literal) this is False; post-migration
        # (thin wrapper around get_prompt_template) it is True.
        assert STRICT_TDD_PROMPT is prompt_registry.get_prompt_template("strict_tdd")

    def test_strict_tdd_prompt_byte_equal_to_legacy(self) -> None:
        # Defensive: even if the registry template were refactored, the
        # legacy string MUST be preserved verbatim until the v0.8.0
        # removal milestone.
        assert STRICT_TDD_PROMPT == _LEGACY_STRICT_TDD

    def test_strict_tdd_prompt_supports_format_substitution(self) -> None:
        rendered = STRICT_TDD_PROMPT.format(test_command="pytest")
        assert "pytest" in rendered
        assert "STRICT TDD MODE IS ACTIVE" in rendered
        assert "{test_command}" not in rendered


class TestAutoSuggestEmptyAlias:
    def test_empty_prompt_text_matches_registry_template(self) -> None:
        registry_template = prompt_registry.get_prompt_template("auto_suggest_empty")
        assert EMPTY_PROMPT_TEXT == registry_template

    def test_empty_prompt_text_is_registry_template_by_identity(self) -> None:
        assert EMPTY_PROMPT_TEXT is prompt_registry.get_prompt_template(
            "auto_suggest_empty"
        )

    def test_empty_prompt_text_byte_equal_to_legacy(self) -> None:
        assert EMPTY_PROMPT_TEXT == _LEGACY_EMPTY


class TestPromptHeaderAlias:
    def test_prompt_header_matches_registry_template(self) -> None:
        registry_template = prompt_registry.get_prompt_template("auto_suggest_header")
        assert PROMPT_HEADER == registry_template

    def test_prompt_header_is_registry_template_by_identity(self) -> None:
        assert PROMPT_HEADER is prompt_registry.get_prompt_template("auto_suggest_header")

    def test_prompt_header_byte_equal_to_legacy(self) -> None:
        assert PROMPT_HEADER == _LEGACY_HEADER


class TestPromptFooterAlias:
    def test_prompt_footer_matches_registry_template(self) -> None:
        registry_template = prompt_registry.get_prompt_template("auto_suggest_footer")
        assert PROMPT_FOOTER == registry_template

    def test_prompt_footer_is_registry_template_by_identity(self) -> None:
        assert PROMPT_FOOTER is prompt_registry.get_prompt_template("auto_suggest_footer")

    def test_prompt_footer_byte_equal_to_legacy(self) -> None:
        assert PROMPT_FOOTER == _LEGACY_FOOTER


class TestFormatSuggestionPromptStillWorks:
    """The ``format_suggestion_prompt`` function delegates to the aliases;
    refactoring the constants to thin wrappers MUST NOT change the
    public behavior of the helper."""

    def test_format_suggestion_prompt_empty_case_returns_alias(self) -> None:
        assert format_suggestion_prompt([]) == EMPTY_PROMPT_TEXT

    def test_format_suggestion_prompt_with_refs_uses_header_and_footer(self) -> None:
        from flow_engineering.binding import CodeRef

        refs = [
            CodeRef(
                project="insyd",
                id="x_node",
                label="X",
                file="x.py",
                line=1,
                confidence=0.5,
                source="auto_suggest",
            )
        ]
        text = format_suggestion_prompt(refs)
        assert PROMPT_HEADER in text
        assert PROMPT_FOOTER in text
        assert "X" in text
        assert "x.py:1" in text