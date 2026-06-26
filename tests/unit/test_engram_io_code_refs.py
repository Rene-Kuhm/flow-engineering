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


METADATA_MARKER = "<!-- metadata -->"


class TestUpdateObservationMetadata:
    """REQ-13, REQ-14 (PR#1 batch D): append/update trailing `<!-- metadata -->` block.

    Invariants:
    - `code_refs` block MUST remain byte-identical after a write-back.
    - Existing metadata keys are preserved; new keys added; conflicting
      keys overwritten (new wins).
    - Single `update_observation` call per write-back (atomic).
    - Fail-open: any exception during the read/merge/write cycle is
      swallowed and logged to observability. The function MUST NOT raise.
    """

    def test_update_metadata_appends_new_block(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY + VALID_BLOCK)
        obs_id = next(iter(backend.observations))

        client.update_observation_metadata(
            obs_id, {"last_verified_at": "2026-06-25T22:30:00Z"}
        )

        saved = backend.observations[obs_id]["content"]
        assert METADATA_MARKER in saved
        assert PROSE_ONLY in saved
        assert VALID_BLOCK in saved
        assert '"last_verified_at"' in saved
        assert '"2026-06-25T22:30:00Z"' in saved
        assert saved.count(METADATA_MARKER) == 1
        assert saved.count(CODE_REFS_MARKER) == 1

    def test_update_metadata_preserves_code_refs(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY + VALID_BLOCK)
        obs_id = next(iter(backend.observations))

        client.update_observation_metadata(
            obs_id, {"last_verified_at": "2026-06-25T22:30:00Z"}
        )

        saved = backend.observations[obs_id]["content"]
        marker_idx = saved.rfind(CODE_REFS_MARKER)
        assert marker_idx >= 0
        code_refs_block = saved[marker_idx:]
        if not code_refs_block.endswith("\n"):
            code_refs_block = code_refs_block + "\n"
        assert code_refs_block == VALID_BLOCK

    def test_update_metadata_merges_existing_keys(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        existing_meta = (
            f"{METADATA_MARKER}\n"
            '{"schema": 1, "fields": '
            '{"existing_key": "old_value", "conflict_key": "old"}}\n'
        )
        client.save_phase("propose", PROSE_ONLY + existing_meta)
        obs_id = next(iter(backend.observations))

        client.update_observation_metadata(
            obs_id,
            {"new_key": "new_value", "conflict_key": "new"},
        )

        saved = backend.observations[obs_id]["content"]
        assert '"existing_key"' in saved
        assert '"old_value"' in saved
        assert '"new_key"' in saved
        assert '"new_value"' in saved
        assert saved.count('"conflict_key"') == 1
        assert '"conflict_key": "new"' in saved
        assert saved.count(METADATA_MARKER) == 1

    def test_update_metadata_fail_open(self, monkeypatch, metrics_path):
        from flow_engineering import observability

        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY + VALID_BLOCK)
        obs_id = next(iter(backend.observations))

        def boom(_observation_id):
            raise RuntimeError("engram backend down")

        monkeypatch.setattr(backend, "mem_get_observation", boom)

        client.update_observation_metadata(
            obs_id, {"last_verified_at": "2026-06-25T22:30:00Z"}
        )

        events = observability.read_all()
        names = [e["name"] for e in events]
        assert "update_observation_metadata_failed_total" in names, (
            f"expected failure metric, got: {names}"
        )

    def test_update_metadata_atomic(self):
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("propose", PROSE_ONLY + VALID_BLOCK)
        obs_id = next(iter(backend.observations))

        original_update = backend.update_observation
        call_count = {"n": 0}

        def counting_update(observation_id, **kwargs):
            call_count["n"] += 1
            return original_update(observation_id, **kwargs)

        backend.update_observation = counting_update

        client.update_observation_metadata(
            obs_id, {"last_verified_at": "2026-06-25T22:30:00Z"}
        )

        assert call_count["n"] == 1, (
            f"expected exactly 1 update_observation call, got {call_count['n']}"
        )

    def test_update_metadata_replaces_malformed_block_defensively(self):
        """A corrupt metadata JSON body MUST NOT block the write.

        Defensive contract: ``_extract_metadata_fields`` returns ``{}`` on
        malformed input, so the new keys become the entire block.
        """
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        corrupt_meta = (
            f"{METADATA_MARKER}\n"
            "{not valid json whatsoever}\n"
        )
        obs = backend.mem_save(
            title="seed",
            content=PROSE_ONLY + VALID_BLOCK + corrupt_meta,
            topic_key="sdd/my-change/propose",
        )
        obs_id = obs["id"]

        client.update_observation_metadata(
            obs_id, {"last_verified_at": "2026-06-25T22:30:00Z"}
        )

        saved = backend.observations[obs_id]["content"]
        assert "not valid json whatsoever" not in saved, (
            "corrupt metadata body should be replaced"
        )
        assert '"last_verified_at"' in saved
        assert '"2026-06-25T22:30:00Z"' in saved
        assert saved.count(METADATA_MARKER) == 1
        assert VALID_BLOCK in saved


import pytest  # noqa: E402
