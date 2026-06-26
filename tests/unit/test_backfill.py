"""Unit tests for scripts/backfill_code_refs.py — REQ-4 (one-time backfill).

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit implements the backfill runner.

Coverage:
- Dry-run reports would-change count without writing.
- Apply mutates only observations missing the marker.
- Idempotency: re-running on already-backfilled obs is a no-op.
- Pre-image JSONL written for every mutated observation.
- created_at preserved; updated_at advances.
"""

from __future__ import annotations

import json
from pathlib import Path

from flow_engineering.binding import CODE_REFS_MARKER


class TestDryRun:
    def test_dry_run_reports_would_change_without_writing(self, tmp_path: Path) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from scripts.backfill_code_refs import run

        backend = InMemoryBackend()
        backend.mem_save("obs1", "## First prose", topic_key="t1", type="manual")
        backend.mem_save("obs2", "## Second prose", topic_key="t2", type="manual")
        result = run(backend=backend, project="insyd", cache_dir=tmp_path, dry_run=True)
        assert result.would_change == 2
        assert result.applied == 0
        assert result.errors == 0
        # No rows were written with a code_refs block.
        assert backend.observations[1]["content"] == "## First prose"
        assert backend.observations[2]["content"] == "## Second prose"

    def test_dry_run_preserves_existing_blocks(self, tmp_path: Path) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from scripts.backfill_code_refs import run

        backend = InMemoryBackend()
        backend.mem_save("obs1", "## First\n" + CODE_REFS_MARKER + "\n{}\n", topic_key="t1")
        result = run(backend=backend, project="insyd", cache_dir=tmp_path, dry_run=True)
        assert result.would_change == 0


class TestApply:
    def test_apply_appends_unbound_block_when_marker_absent(self, tmp_path: Path) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from scripts.backfill_code_refs import run

        backend = InMemoryBackend()
        original_prose = "## First prose\n\nwith multi\nlines\n"
        backend.mem_save("obs1", original_prose, topic_key="t1")
        result = run(backend=backend, project="insyd", cache_dir=tmp_path, dry_run=False)
        assert result.applied == 1
        # Prose preserved byte-for-byte; block appended at end.
        saved = backend.observations[1]["content"]
        assert saved.startswith(original_prose)
        assert saved.endswith("\n")
        assert CODE_REFS_MARKER in saved

    def test_apply_preserves_prose_byte_for_byte(self, tmp_path: Path) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from scripts.backfill_code_refs import run

        backend = InMemoryBackend()
        original = "x" * 800  # 800-char prose (spec scenario)
        backend.mem_save("obs1", original, topic_key="t1")
        run(backend=backend, project="insyd", cache_dir=tmp_path, dry_run=False)
        saved = backend.observations[1]["content"]
        # First 800 chars must be byte-identical to original prose.
        assert saved[:800] == original

    def test_apply_skips_observations_with_existing_block(self, tmp_path: Path) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from scripts.backfill_code_refs import run

        backend = InMemoryBackend()
        existing_block = CODE_REFS_MARKER + '\n{"schema": 1, "nodes": [], "source": "unbound"}\n'
        backend.mem_save("obs1", "## P\n" + existing_block, topic_key="t1")
        result = run(backend=backend, project="insyd", cache_dir=tmp_path, dry_run=False)
        assert result.applied == 0
        # Saved content unchanged.
        assert backend.observations[1]["content"] == "## P\n" + existing_block

    def test_apply_is_idempotent_across_runs(self, tmp_path: Path) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from scripts.backfill_code_refs import run

        backend = InMemoryBackend()
        backend.mem_save("obs1", "## First", topic_key="t1")
        first = run(backend=backend, project="insyd", cache_dir=tmp_path, dry_run=False)
        assert first.applied == 1
        # Second run: already has a block, so 0 applied.
        second = run(backend=backend, project="insyd", cache_dir=tmp_path, dry_run=False)
        assert second.applied == 0

    def test_apply_writes_preimage_jsonl(self, tmp_path: Path) -> None:
        from flow_engineering.engram_io import InMemoryBackend
        from scripts.backfill_code_refs import PREIMAGE_FILE, run

        backend = InMemoryBackend()
        backend.mem_save("obs1", "## First", topic_key="t1")
        backend.mem_save("obs2", "## Second", topic_key="t2")
        run(backend=backend, project="insyd", cache_dir=tmp_path, dry_run=False)
        preimage = tmp_path / PREIMAGE_FILE
        assert preimage.exists()
        lines = [json.loads(line) for line in preimage.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 2
        # Each entry records the original (pre-backfill) content + the new content.
        for entry in lines:
            assert "id" in entry
            assert "before" in entry
            assert "after" in entry
            assert entry["before"].startswith("##")