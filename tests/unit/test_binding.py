"""Unit tests for binding.py — code_refs parse/format/round-trip.

REQ-1 (format), REQ-2 (extract/format/round-trip). 11 golden fixtures covering
empty / single / multi / backfill / manual / auto_suggest / unbound /
malformed-with-offset / round-trip / schema-mismatch / unknown-source.

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit implements binding.py.
"""

from __future__ import annotations

import pytest

from flow_engineering.binding import (
    ALLOWED_SOURCES,
    CODE_REFS_MARKER,
    SUPPORTED_SCHEMA,
    CodeRef,
    ParseError,
    extract_code_refs,
    format_code_refs_block,
    split_prose_and_refs,
    validate_block,
)


# ---------- Fixtures ----------

PROSE_ONLY = "## Decision\n\nUse JWT for auth.\n"
EMPTY_BLOCK = (
    f"{CODE_REFS_MARKER}\n"
    '{"schema": 1, "nodes": [], "source": "unbound"}\n'
)
SINGLE_BLOCK = (
    "## Decision\n\nUse JWT for auth.\n\n"
    f"{CODE_REFS_MARKER}\n"
    '{"schema": 1, "nodes": ['
    '{"project": "insyd", "id": "src_auth_jwt_tokenmgr",'
    ' "label": "TokenManager", "file": "src/auth/jwt.py", "line": 42,'
    ' "confidence": 0.9, "source": "manual"}], "source": "manual"}\n'
)
MULTI_BLOCK = (
    "## Two bindings\n"
    f"{CODE_REFS_MARKER}\n"
    '{"schema": 1, "nodes": ['
    '{"project":"p","id":"node_a","label":"A","file":"a.py","line":1,'
    '"confidence":0.9,"source":"manual"},'
    '{"project":"p","id":"node_b","label":"B","file":"b.py","line":2,'
    '"confidence":0.4,"source":"auto_suggest"}'
    '], "source": "auto_suggest"}\n'
)
BACKFILL_BLOCK = (
    f"{CODE_REFS_MARKER}\n"
    '{"schema": 1, "nodes": [{"project":"p","id":"node_a",'
    '"label":"A","file":"a.py","line":1,"confidence":0.3,'
    '"source":"backfill"}], "source": "backfill"}\n'
)
MALFORMED_BLOCK = (
    f"{CODE_REFS_MARKER}\n"
    "{this is not json}\n"
)
SCHEMA_MISMATCH_BLOCK = (
    f"{CODE_REFS_MARKER}\n"
    '{"schema": 99, "nodes": []}\n'
)


# ---------- REQ-1: format ----------

class TestExtractFormat:
    """REQ-1: extract returns CodeRef list, preserves order, handles marker absence."""

    def test_extract_returns_empty_when_marker_absent(self):
        assert extract_code_refs(PROSE_ONLY) == []

    def test_extract_returns_empty_for_empty_string(self):
        assert extract_code_refs("") == []

    def test_extract_unbound_block_yields_empty_list(self):
        result = extract_code_refs(EMPTY_BLOCK)
        assert result == []

    def test_extract_single_block_returns_one_ref(self):
        result = extract_code_refs(SINGLE_BLOCK)
        assert len(result) == 1
        ref = result[0]
        assert ref.project == "insyd"
        assert ref.id == "src_auth_jwt_tokenmgr"
        assert ref.label == "TokenManager"
        assert ref.file == "src/auth/jwt.py"
        assert ref.line == 42
        assert ref.confidence == 0.9
        assert ref.source == "manual"

    def test_extract_multi_block_preserves_input_order(self):
        result = extract_code_refs(MULTI_BLOCK)
        assert [r.id for r in result] == ["node_a", "node_b"]
        assert [r.source for r in result] == ["manual", "auto_suggest"]

    def test_extract_backfill_block_returns_one_ref_with_confidence_0_3(self):
        result = extract_code_refs(BACKFILL_BLOCK)
        assert len(result) == 1
        assert result[0].source == "backfill"
        assert result[0].confidence == 0.3

    def test_extract_malformed_raises_parse_error_with_offset(self):
        with pytest.raises(ParseError) as exc_info:
            extract_code_refs(MALFORMED_BLOCK)
        assert exc_info.value.offset > 0

    def test_extract_schema_mismatch_raises_parse_error(self):
        with pytest.raises(ParseError) as exc_info:
            extract_code_refs(SCHEMA_MISMATCH_BLOCK)
        assert "schema" in str(exc_info.value).lower()


# ---------- REQ-2: format + round-trip ----------

class TestFormatRoundtrip:
    """REQ-2: format produces canonical block; extract∘format∘extract is identity."""

    def test_format_starts_with_marker_and_includes_schema(self):
        ref = CodeRef(
            project="p", id="x", label="X", file="x.py", line=1,
            confidence=0.9, source="manual",
        )
        out = format_code_refs_block([ref], source="manual")
        assert out.startswith(f"{CODE_REFS_MARKER}\n")
        assert '"schema": 1' in out
        assert out.endswith("\n")

    def test_format_rejects_unknown_source(self):
        ref = CodeRef(
            project="p", id="x", label="X", file="x.py", line=1,
            confidence=0.9, source="made_up",  # type: ignore[arg-type]
        )
        with pytest.raises(ValueError) as exc_info:
            format_code_refs_block([ref], source="made_up")  # type: ignore[arg-type]
        allowed = ALLOWED_SOURCES
        for s in allowed:
            assert s in str(exc_info.value)

    def test_format_sorts_by_id_canonical(self):
        ref_b = CodeRef("p", "b_id", "B", "b.py", 1, 0.5, "manual")
        ref_a = CodeRef("p", "a_id", "A", "a.py", 1, 0.5, "manual")
        out = format_code_refs_block([ref_b, ref_a], source="manual")
        # The sorted output must list a_id BEFORE b_id.
        assert out.index("a_id") < out.index("b_id")

    def test_round_trip_extract_format_extract_is_identity(self):
        original = extract_code_refs(SINGLE_BLOCK)
        assert len(original) == 1
        formatted = format_code_refs_block(original, source="manual")
        # Re-parse the formatted block — must yield the same list.
        re_extracted = extract_code_refs(f"prose\n{formatted}")
        assert re_extracted == original


# ---------- Helpers ----------

class TestSplitProseAndRefs:
    def test_split_prose_only_yields_empty_block(self):
        prose, block = split_prose_and_refs(PROSE_ONLY)
        assert prose == PROSE_ONLY
        assert block == ""

    def test_split_full_content_separates_marker_and_after(self):
        prose, block = split_prose_and_refs(SINGLE_BLOCK)
        assert CODE_REFS_MARKER not in prose
        assert CODE_REFS_MARKER in block
        # The block must start with the marker line.
        assert block.startswith(CODE_REFS_MARKER)


class TestValidateBlock:
    def test_validate_accepts_well_formed(self):
        body = '{"schema": 1, "nodes": []}'
        assert validate_block(body) == []

    def test_validate_rejects_unknown_schema(self):
        body = '{"schema": 99, "nodes": []}'
        with pytest.raises(ParseError) as exc_info:
            validate_block(body)
        assert "schema" in str(exc_info.value).lower()

    def test_validate_rejects_invalid_json(self):
        with pytest.raises(ParseError):
            validate_block("not json")