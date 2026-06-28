"""Unit tests for prompt_registry.py (REQ-45 foundation).

REQ-45: a single source of truth for every prompt string the project ships,
mirroring the observability counter catalog pattern.

These tests cover the initial bootstrap surface (T1.1):
- ``PromptDef`` is a frozen dataclass with the expected shape.
- ``PromptDomain`` enum covers the 5 documented domains.
- ``get_prompt(name)`` returns the matching entry; raises ``KeyError`` on unknown.
- ``list_prompts(domain=None)`` returns all entries; filters by domain.
- ``PROMPT_NAMES`` is non-empty (catalog exists).

Strict TDD: written BEFORE the implementation per the project convention.
They MUST fail until the GREEN commit implements ``prompt_registry.py``.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest

from flow_engineering.prompt_registry import (
    PROMPT_NAMES,
    PromptDef,
    PromptDomain,
    get_prompt,
    list_prompts,
)


class TestPromptDefSchema:
    def test_prompt_def_is_frozen_dataclass(self) -> None:
        assert is_dataclass(PromptDef)
        # frozen=True is the critical safety property; verify at the field level
        entry = PromptDef(
            name="x",
            domain=PromptDomain.BINDING,
            template="hello",
            version="1.0.0",
        )
        with pytest.raises(FrozenInstanceError):
            entry.name = "y"  # type: ignore[misc]

    def test_prompt_def_required_fields(self) -> None:
        field_names = {f.name for f in fields(PromptDef)}
        assert {"name", "domain", "template", "version"} <= field_names

    def test_prompt_def_metadata_defaults_to_empty_dict(self) -> None:
        entry = PromptDef(
            name="x",
            domain=PromptDomain.BINDING,
            template="hello",
            version="1.0.0",
        )
        assert entry.metadata == {}

    def test_prompt_def_accepts_custom_metadata(self) -> None:
        entry = PromptDef(
            name="x",
            domain=PromptDomain.BINDING,
            template="hello",
            version="1.0.0",
            metadata={"model": "gpt-4", "max_tokens": 500},
        )
        assert entry.metadata == {"model": "gpt-4", "max_tokens": 500}


class TestPromptDomain:
    def test_prompt_domain_enum_has_all_values(self) -> None:
        names = {m.name for m in PromptDomain}
        assert names == {"BINDING", "DRIFT", "OBSERVABILITY", "SNAPSHOT", "RUNTIME"}

    def test_prompt_domain_values_are_lowercase_strings(self) -> None:
        for member in PromptDomain:
            assert member.value == member.value.lower()
            assert isinstance(member.value, str)


class TestPromptNamesCatalog:
    def test_prompt_names_catalog_is_non_empty(self) -> None:
        assert len(PROMPT_NAMES) >= 1

    def test_prompt_names_catalog_names_are_unique(self) -> None:
        names = [p.name for p in PROMPT_NAMES]
        assert len(names) == len(set(names))

    def test_prompt_names_includes_strict_tdd(self) -> None:
        names = {p.name for p in PROMPT_NAMES}
        assert "strict_tdd" in names

    def test_prompt_names_includes_auto_suggest_entries(self) -> None:
        names = {p.name for p in PROMPT_NAMES}
        assert {"auto_suggest_header", "auto_suggest_footer", "auto_suggest_empty"} <= names


class TestGetPrompt:
    def test_get_prompt_returns_matching_def(self) -> None:
        entry = get_prompt("strict_tdd")
        assert entry.name == "strict_tdd"
        assert entry.domain == PromptDomain.OBSERVABILITY

    def test_get_prompt_returns_each_known_entry(self) -> None:
        for name in {"strict_tdd", "auto_suggest_header", "auto_suggest_footer", "auto_suggest_empty"}:
            entry = get_prompt(name)
            assert entry.name == name

    def test_get_prompt_raises_keyerror_on_unknown(self) -> None:
        with pytest.raises(KeyError):
            get_prompt("nonexistent_prompt_xyz")

    def test_get_prompt_keyerror_message_includes_name(self) -> None:
        with pytest.raises(KeyError) as excinfo:
            get_prompt("nonexistent_prompt_xyz")
        assert "nonexistent_prompt_xyz" in str(excinfo.value)


class TestListPrompts:
    def test_list_prompts_returns_all_when_no_domain(self) -> None:
        result = list_prompts()
        assert len(result) == len(PROMPT_NAMES)
        assert {p.name for p in result} == {p.name for p in PROMPT_NAMES}

    def test_list_prompts_filters_by_observability_domain(self) -> None:
        result = list_prompts(PromptDomain.OBSERVABILITY)
        assert all(p.domain == PromptDomain.OBSERVABILITY for p in result)
        names = {p.name for p in result}
        assert "strict_tdd" in names

    def test_list_prompts_filters_by_binding_domain(self) -> None:
        result = list_prompts(PromptDomain.BINDING)
        assert all(p.domain == PromptDomain.BINDING for p in result)
        names = {p.name for p in result}
        assert {"auto_suggest_header", "auto_suggest_footer", "auto_suggest_empty"} <= names

    def test_list_prompts_unknown_domain_returns_empty(self) -> None:
        # PromptDomain is a closed enum; this test documents the defensive
        # contract — even if someone subclassed or mocked, the empty result
        # is the expected behavior.
        result = list_prompts(PromptDomain.DRIFT)
        assert result == []

    def test_list_prompts_result_is_sorted_by_name(self) -> None:
        result = list_prompts()
        names = [p.name for p in result]
        assert names == sorted(names)


# ---------- T3.5 (W3): prompts/ directory + load_template_from_file ----------


class TestPromptRegistryLoadsFromJ2Files:
    """REQ-46 W3 — the 4 PROMPT_NAMES entries live as ``prompts/<name>.j2``.

    Per verify-report-pr2b W3: moving the template bodies out of Python
    source into standalone ``.j2`` files makes them diffable in PRs and
    reviewable in editors without opening Python. The catalog still
    holds the resolved template text (``prompt.template``) so renderers
    don't have to hit the filesystem on every call; the
    ``metadata.template_file`` key records the on-disk origin so the
    future ``flow prompts list --source`` CLI can render it back to a
    path.
    """

    def test_prompts_dir_exists_at_repo_root(self) -> None:
        """The ``prompts/`` directory is checked into the repo."""
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        prompts_dir = repo_root / "prompts"
        assert prompts_dir.is_dir(), f"expected {prompts_dir} to exist"

    def test_all_four_j2_files_exist(self) -> None:
        """Each PROMPT_NAMES entry has a matching ``prompts/<name>.j2`` file."""
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        prompts_dir = repo_root / "prompts"
        for name in (
            "strict_tdd",
            "auto_suggest_header",
            "auto_suggest_footer",
            "auto_suggest_empty",
        ):
            j2_path = prompts_dir / f"{name}.j2"
            assert j2_path.is_file(), f"expected {j2_path} to exist"

    def test_metadata_template_file_records_j2_path(self) -> None:
        """Every migrated entry carries ``metadata.template_file`` set."""
        for entry in PROMPT_NAMES:
            assert "template_file" in entry.metadata, (
                f"entry {entry.name!r} missing metadata.template_file"
            )
            assert entry.metadata["template_file"].endswith(".j2"), (
                f"entry {entry.name!r}: template_file must end in .j2; "
                f"got {entry.metadata['template_file']!r}"
            )
            assert entry.metadata["template_file"].startswith("prompts/"), (
                f"entry {entry.name!r}: template_file must be relative "
                f"to repo root under prompts/; "
                f"got {entry.metadata['template_file']!r}"
            )

    def test_load_template_from_file_helper_reads_disk(self) -> None:
        """``load_template_from_file()`` reads the body of a ``.j2`` file."""
        from flow_engineering.prompt_registry import load_template_from_file

        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        body = load_template_from_file(repo_root / "prompts" / "strict_tdd.j2")
        assert "{test_command}" in body
        assert body == get_prompt("strict_tdd").template

    def test_catalog_templates_match_disk(self) -> None:
        """``prompt.template`` matches what ``load_template_from_file`` returns."""
        from flow_engineering.prompt_registry import load_template_from_file

        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent.parent
        for entry in PROMPT_NAMES:
            j2_path = repo_root / entry.metadata["template_file"]
            disk_body = load_template_from_file(j2_path)
            assert entry.template == disk_body, (
                f"entry {entry.name!r}: catalog template disagrees with "
                f"on-disk {j2_path}"
            )

    def test_load_template_from_file_strips_trailing_newline(self) -> None:
        """POSIX text files end in ``\\n``; the loader strips it so the
        resolved ``template`` matches the inline-Python expectation."""
        from flow_engineering.prompt_registry import load_template_from_file

        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".j2", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("hello\n")
            tmp_path = fh.name
        try:
            assert load_template_from_file(tmp_path) == "hello"
        finally:
            Path(tmp_path).unlink()
