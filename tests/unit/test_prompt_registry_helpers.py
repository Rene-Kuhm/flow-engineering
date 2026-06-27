"""Unit tests for prompt_registry helper surface (REQ-45 T1.2).

REQ-45 helper surface: thin convenience wrappers over the catalog that
shrink common call sites to one line.

- ``get_prompt_template(name)`` -- shorthand for ``get_prompt(name).template``.
- ``get_prompt_metadata(name)`` -- shorthand for ``get_prompt(name).metadata``.
- ``register_prompt(prompt)`` -- append a NEW prompt (idempotency check).
- ``unregister_prompt(name)`` -- inverse, primarily for tests.

Strict TDD: written BEFORE the GREEN implementation. They MUST fail
until ``prompt_registry.py`` is extended.
"""

from __future__ import annotations

import pytest

from flow_engineering import prompt_registry
from flow_engineering.prompt_registry import (
    PromptDef,
    PromptDomain,
    get_prompt,
    get_prompt_metadata,
    get_prompt_template,
    register_prompt,
    unregister_prompt,
)


def _names() -> list[str]:
    """Return current catalog names via module attribute access.

    ``PROMPT_NAMES`` is a module-level tuple that ``register_prompt``
    rebinds via ``global``; tests that imported ``PROMPT_NAMES`` directly
    would hold a stale reference. Always go through the module.
    """
    return [p.name for p in prompt_registry.PROMPT_NAMES]


class TestGetPromptTemplate:
    def test_get_prompt_template_returns_strict_tdd_template(self) -> None:
        template = get_prompt_template("strict_tdd")
        assert "{test_command}" in template
        assert "STRICT TDD MODE IS ACTIVE" in template

    def test_get_prompt_template_returns_static_string_when_no_variables(self) -> None:
        template = get_prompt_template("auto_suggest_header")
        assert template == "Auto-suggested code bindings:"

    def test_get_prompt_template_propagates_keyerror(self) -> None:
        with pytest.raises(KeyError):
            get_prompt_template("nonexistent_prompt_xyz")

    def test_get_prompt_template_matches_get_prompt_dot_template(self) -> None:
        for name in {"strict_tdd", "auto_suggest_header", "auto_suggest_footer", "auto_suggest_empty"}:
            assert get_prompt_template(name) == get_prompt(name).template


class TestGetPromptMetadata:
    def test_get_prompt_metadata_returns_dict(self) -> None:
        meta = get_prompt_metadata("strict_tdd")
        assert isinstance(meta, dict)
        assert "source" in meta

    def test_get_prompt_metadata_source_field(self) -> None:
        meta = get_prompt_metadata("strict_tdd")
        assert "strict_tdd.py" in meta["source"]

    def test_get_prompt_metadata_propagates_keyerror(self) -> None:
        with pytest.raises(KeyError):
            get_prompt_metadata("nonexistent_prompt_xyz")

    def test_get_prompt_metadata_matches_get_prompt_dot_metadata(self) -> None:
        for name in {"strict_tdd", "auto_suggest_header", "auto_suggest_footer", "auto_suggest_empty"}:
            assert get_prompt_metadata(name) == get_prompt(name).metadata


class TestRegisterPrompt:
    def test_register_prompt_appends_to_catalog(self) -> None:
        new_prompt = PromptDef(
            name="test_only_register",
            domain=PromptDomain.DRIFT,
            template="drift placeholder",
            version="0.1.0",
        )
        original_count = len(prompt_registry.PROMPT_NAMES)
        register_prompt(new_prompt)
        try:
            assert len(prompt_registry.PROMPT_NAMES) == original_count + 1
            assert get_prompt("test_only_register").template == "drift placeholder"
        finally:
            unregister_prompt("test_only_register")

    def test_register_prompt_raises_on_duplicate(self) -> None:
        duplicate = PromptDef(
            name="strict_tdd",
            domain=PromptDomain.OBSERVABILITY,
            template="different content",
            version="9.9.9",
        )
        with pytest.raises(ValueError, match="already registered"):
            register_prompt(duplicate)

    def test_register_prompt_preserves_original_order_for_existing(self) -> None:
        new_prompt = PromptDef(
            name="zzz_test_register",
            domain=PromptDomain.RUNTIME,
            template="runtime placeholder",
            version="0.1.0",
        )
        register_prompt(new_prompt)
        try:
            names = _names()
            assert names[-1] == "zzz_test_register"
            assert "strict_tdd" in names
        finally:
            unregister_prompt("zzz_test_register")


class TestUnregisterPrompt:
    def test_unregister_prompt_removes_from_catalog(self) -> None:
        new_prompt = PromptDef(
            name="test_only_unregister",
            domain=PromptDomain.SNAPSHOT,
            template="snapshot placeholder",
            version="0.1.0",
        )
        register_prompt(new_prompt)
        unregister_prompt("test_only_unregister")
        assert "test_only_unregister" not in _names()

    def test_unregister_prompt_unknown_name_is_silent(self) -> None:
        # Defensive: caller may pass a stale name from a previous session;
        # unregister MUST NOT raise. Mirrors the fail-open convention used
        # elsewhere in the project (observability.increment, etc.).
        original_count = len(prompt_registry.PROMPT_NAMES)
        unregister_prompt("nonexistent_prompt_xyz")
        assert len(prompt_registry.PROMPT_NAMES) == original_count
