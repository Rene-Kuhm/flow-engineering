"""Unit tests for engram_io.py code_refs hook (REQ-3).

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit implements the save_phase hook.
"""

from __future__ import annotations

from flow_engineering.binding import (
    CODE_REFS_MARKER,
    CodeRef,
    SUPPORTED_SCHEMA,
)
from flow_engineering.engram_io import EngramClient, InMemoryBackend

PROSE_ONLY = "## Decision\n\nUse JWT for auth.\n"
VALID_BLOCK = (
    f"{CODE_REFS_MARKER}\n"
    '{"schema": 1, "nodes": [{"project":"p","id":"x","label":"X",'
    '"file":"x.py","line":1,"confidence":0.9,"source":"manual"}],'
    ' "source": "manual"}\n'
)
EMPTY_BLOCK = (
    f"{CODE_REFS_MARKER}\n"
    '{"schema": 1, "nodes": [], "source": "unbound"}\n'
)
MALFORMED_BLOCK = (
    f"{CODE_REFS_MARKER}\n"
    "{not json}\n"
)
SCHEMA_MISMATCH_BLOCK = (
    f"{CODE_REFS_MARKER}\n"
    '{"schema": 99, "nodes": []}\n'
)


class TestSavePhaseHook:
    def test_save_phase_appends_unbound_when_marker_absent(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY)
        saved = backend.observations[1]
        assert PROSE_ONLY in saved["content"]
        # An unbound block was appended after the original prose.
        assert CODE_REFS_MARKER in saved["content"]

    def test_save_phase_preserves_existing_valid_block(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY + VALID_BLOCK)
        saved = backend.observations[1]
        # The original block must be intact (not replaced).
        assert VALID_BLOCK in saved["content"]
        # And no second block was appended.
        assert saved["content"].count(CODE_REFS_MARKER) == 1

    def test_save_phase_accepts_empty_block_as_unbound(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY + EMPTY_BLOCK)
        saved = backend.observations[1]
        assert EMPTY_BLOCK in saved["content"]

    def test_save_phase_rejects_malformed_block(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        from flow_engineering.binding import ParseError
        with pytest.raises(ParseError):
            client.save_phase("propose", PROSE_ONLY + MALFORMED_BLOCK)
        # No row written.
        assert len(backend.observations) == 0

    def test_save_phase_rejects_unknown_schema(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        from flow_engineering.binding import ParseError
        with pytest.raises(ParseError):
            client.save_phase("propose", PROSE_ONLY + SCHEMA_MISMATCH_BLOCK)
        assert len(backend.observations) == 0


class TestLoadCodeRefs:
    def test_load_code_refs_returns_list_for_valid_block(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY + VALID_BLOCK)
        refs = client.load_code_refs("propose")
        assert isinstance(refs, list)
        assert len(refs) == 1
        assert refs[0].id == "x"

    def test_load_code_refs_returns_empty_for_marker_absent(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY)
        refs = client.load_code_refs("propose")
        assert refs == []

    def test_load_code_refs_returns_none_for_missing_phase(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        assert client.load_code_refs("nope") is None


# Imported here so pytest collection doesn't fail on missing import.
import pytest  # noqa: E402