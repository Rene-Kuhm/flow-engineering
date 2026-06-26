"""Unit tests for engram_io.py code_refs hook (REQ-3 + REQ-6 save-phase auto-suggest).

REQ-3: write content unchanged when no marker; validate and preserve valid
blocks; reject malformed blocks before writing.
REQ-6 (PR#2 batch 1): when ``save_phase`` is called WITHOUT an explicit
``code_refs`` block AND auto-suggest is requested (``with_suggest=True`` or
``FLOW_AUTO_SUGGEST=1``), the system MUST consult the suggester and persist
the chosen bindings (or fall back to ``unbound`` when none surface). The
suggester MUST fail-open: any internal error yields a normal unbound save.

These tests are written alongside the implementation (one combined commit
per ``feat(engram_io): wire auto_suggest into save_phase``). They MUST pass
on this commit and remain green through subsequent refactors.
"""

from __future__ import annotations

import pytest

from flow_engineering.binding import (
    CODE_REFS_MARKER,
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


def _ref(node_id: str, confidence: float) -> object:
    """Build a tiny CodeRef-like for graphify_query mocks."""
    from flow_engineering.binding import CodeRef

    return CodeRef(
        project="insyd",
        id=node_id,
        label=node_id.split("_")[-1].title(),
        file=f"src/{node_id}.py",
        line=1,
        confidence=confidence,
        source="auto_suggest",
    )


@pytest.fixture
def metrics_path(tmp_path, monkeypatch):
    """Point observability at a tmp_path JSONL file."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


class TestSavePhaseHook:
    def test_save_phase_appends_unbound_when_marker_absent(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY)
        saved = backend.observations[1]
        assert PROSE_ONLY in saved["content"]
        assert CODE_REFS_MARKER in saved["content"]

    def test_save_phase_preserves_existing_valid_block(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY + VALID_BLOCK)
        saved = backend.observations[1]
        assert VALID_BLOCK in saved["content"]
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


# ---------- REQ-6: auto-suggest hook ----------


class TestSavePhaseAutoSuggest:
    """save_phase MUST consult auto_suggest when no marker + with_suggest flag."""

    def test_save_phase_calls_auto_suggest_when_no_marker_and_with_suggest(
        self, monkeypatch, metrics_path
    ):
        from flow_engineering import observability
        from flow_engineering.binding import CodeRef

        candidates = [
            CodeRef(
                project="insyd",
                id="src_auth_jwt_tokenmgr",
                label="TokenManager",
                file="src/auth/jwt.py",
                line=42,
                confidence=0.6,
                source="auto_suggest",
            )
        ]
        # Patch the query_nodes call inside the suggester.
        monkeypatch.setattr(
            "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
            lambda text, *, threshold=0.3, max_results=5: candidates,
        )

        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY, with_suggest=True)

        saved = backend.observations[1]
        assert '"source": "auto_suggest"' in saved["content"]
        assert "src_auth_jwt_tokenmgr" in saved["content"]
        # Metric was recorded.
        events = observability.read_all()
        names = [e["name"] for e in events]
        assert "suggest_invoked_total" in names
        assert "suggest_hit_total" in names

    def test_save_phase_skips_auto_suggest_when_explicit_marker(
        self, monkeypatch, metrics_path
    ):
        def should_not_be_called(text, **kw):
            raise AssertionError("auto_suggest must NOT run when explicit marker")

        monkeypatch.setattr(
            "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
            should_not_be_called,
        )

        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY + VALID_BLOCK, with_suggest=True)
        saved = backend.observations[1]
        assert VALID_BLOCK in saved["content"]

    def test_save_phase_appends_unbound_when_suggester_returns_empty(
        self, monkeypatch, metrics_path
    ):
        from flow_engineering import observability

        monkeypatch.setattr(
            "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
            lambda text, *, threshold=0.3, max_results=5: [],
        )
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY, with_suggest=True)
        saved = backend.observations[1]
        assert '"source": "unbound"' in saved["content"]
        events = observability.read_all()
        names = [e["name"] for e in events]
        assert "suggest_miss_total" in names

    def test_save_phase_fail_open_when_suggester_raises(self, monkeypatch, metrics_path):
        from flow_engineering import observability

        def boom(text, **kw):
            raise RuntimeError("graphify crashed unexpectedly")

        monkeypatch.setattr(
            "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
            boom,
        )
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        # MUST NOT raise -- the save must proceed normally.
        client.save_phase("propose", PROSE_ONLY, with_suggest=True)
        saved = backend.observations[1]
        # Saved with an unbound block.
        assert CODE_REFS_MARKER in saved["content"]
        assert '"source": "unbound"' in saved["content"]
        # Miss counter recorded.
        events = observability.read_all()
        names = [e["name"] for e in events]
        assert "suggest_miss_total" in names

    def test_save_phase_no_suggest_writes_manual_source_block(self, monkeypatch, metrics_path):
        """When --no-suggest is passed, the saved block source is 'manual'."""
        def should_not_be_called(text, **kw):
            raise AssertionError("graphify must NOT be called when no_suggest=True")

        monkeypatch.setattr(
            "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
            should_not_be_called,
        )
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY, no_suggest=True)
        saved = backend.observations[1]
        assert '"source": "manual"' in saved["content"]
        assert "[]" in saved["content"]

    def test_save_phase_default_no_suggest_writes_unbound(self, metrics_path):
        """Without any flag, save proceeds with the default unbound block."""
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY)
        saved = backend.observations[1]
        assert '"source": "unbound"' in saved["content"]


import pytest  # noqa: E402