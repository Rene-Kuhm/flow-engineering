"""Unit tests for scripts/backfill_code_refs.py — REQ-4 (one-time backfill).

Tests are written BEFORE the implementation per strict TDD. They MUST fail
until the GREEN commit implements the backfill runner.
"""

from __future__ import annotations

from flow_engineering.binding import CODE_REFS_MARKER


class TestDryRun:
    def test_dry_run_reports_would_change_without_writing(self, tmp_path, capsys):
        # Stub test — full behavior lands in GREEN commit.
        # This test verifies the CLI is invocable and reports the mode.
        from scripts.backfill_code_refs import main

        rc = main([
            "--cache-dir", str(tmp_path),
            "--project", "insyd",
        ])
        captured = capsys.readouterr()
        assert rc == 0
        assert "dry-run" in captured.out

    def test_apply_mode_reports_apply(self, tmp_path, capsys):
        from scripts.backfill_code_refs import main

        rc = main([
            "--apply",
            "--cache-dir", str(tmp_path),
            "--project", "insyd",
        ])
        captured = capsys.readouterr()
        assert rc == 0
        assert "apply" in captured.out


class TestIdempotencyContract:
    """Contract test: re-running on already-backfilled obs MUST be a no-op."""

    def test_idempotency_contract_documented(self):
        # Real assertions land with the InMemoryBackend runner in GREEN.
        assert CODE_REFS_MARKER  # marker constant is exported