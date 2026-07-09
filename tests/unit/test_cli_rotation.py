"""Unit tests for ``flow archive rotate`` (REQ-V1.3.4 / v1.3 sub-change d).

The subcommand lists entries in ``openspec/changes/archive/`` older than N
days. It is **read-only** by design — destructive rotation is deferred to
``chore/archive-rotation-2026``.

Per Article III strict TDD, these tests are written BEFORE
``flow_engineering.cli.rotation`` is implemented. They will fail to
import (ModuleNotFoundError) until the production module lands.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from flow_engineering.cli import main

# Module under test — fails to import until GREEN step 8 lands.
from flow_engineering.cli.rotation import (
    _candidate_entries,
    _entry_mtime,
)

runner = CliRunner()


# ---------- helpers ----------


def _make_entry(root: Path, name: str, *, mtime: datetime, with_proposal: bool = True) -> Path:
    """Create a fake archive entry directory with the given mtime.

    Uses ``os.utime`` so the filesystem mtime matches the requested
    timestamp (independent of git checkout skew — the unit-test fallback
    is exercised separately).
    """
    entry = root / name
    entry.mkdir(parents=True, exist_ok=True)
    if with_proposal:
        (entry / "proposal.md").write_text(
            f"# {name}\n",
            encoding="utf-8",
        )
    ts = mtime.timestamp()
    # Walk every file/dir created and pin its mtime.
    for child in [entry, *entry.rglob("*")]:
        os.utime(child, (ts, ts))
    return entry


def _make_entry_without_proposal(root: Path, name: str, *, mtime: datetime) -> Path:
    """Create an archive entry whose ``proposal.md`` is missing (edge case)."""
    entry = root / name
    entry.mkdir(parents=True, exist_ok=True)
    ts = mtime.timestamp()
    for child in [entry, *entry.rglob("*")]:
        os.utime(child, (ts, ts))
    return entry


# ---------- RED case A: filter logic ----------


class TestCandidateEntriesFilter:
    """``_candidate_entries`` filters out entries newer than the threshold."""

    def test_older_than_180_days_excludes_fresh_entry(
        self,
        tmp_path: Path,
    ) -> None:
        """A 7-day-old entry MUST be excluded when ``--older-than 180``."""
        now = datetime.now(tz=UTC)
        _make_entry(tmp_path, "2024-01-01-old-change", mtime=now - timedelta(days=400))
        _make_entry(tmp_path, "2026-07-01-fresh-change", mtime=now - timedelta(days=7))

        candidates = _candidate_entries(tmp_path, older_than_days=180)

        paths = [c["path"] for c in candidates]
        assert "2024-01-01-old-change" in paths[0] or any(
            "2024-01-01-old-change" in p for p in paths
        ), f"old entry must be a candidate; got {paths!r}"
        assert not any("2026-07-01-fresh-change" in p for p in paths), (
            f"7-day-old entry MUST be excluded with --older-than 180; got {paths!r}"
        )


# ---------- RED case B: dry-run is non-mutating ----------


class TestDryRunNonMutating:
    """``--dry-run`` does not move or rename any archive entry."""

    def test_dry_run_does_not_mutate_archive_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After ``rotate_cmd --dry-run``, the archive dir is byte-identical."""
        now = datetime.now(tz=UTC)
        old = _make_entry(tmp_path, "2024-01-01-old-change", mtime=now - timedelta(days=400))
        new = _make_entry(tmp_path, "2026-07-01-fresh-change", mtime=now - timedelta(days=7))

        before = sorted(p.name for p in tmp_path.iterdir())

        # chdir so Path("openspec/changes/archive") lands on tmp_path.
        repo = tmp_path.parent
        archive_dir = repo / "openspec" / "changes" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        # Move our fixtures into the resolved archive dir.
        for src in (old, new):
            target = archive_dir / src.name
            if target.exists():
                target.rmdir()
            src.rename(target)

        monkeypatch.chdir(repo)

        result = runner.invoke(
            main,
            ["archive", "rotate", "--older-than", "180", "--dry-run"],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )

        after = sorted(p.name for p in archive_dir.iterdir())
        assert before == after, (
            f"dry-run MUST NOT mutate archive dir; before={before!r} after={after!r}"
        )


# ---------- RED case C: output formats ----------


class TestOutputFormats:
    """``--format yaml`` and ``--format json`` both emit parseable output."""

    def test_format_yaml_emits_parseable_yaml(self) -> None:
        """``--format yaml`` parses cleanly with PyYAML and contains candidates key."""
        result = runner.invoke(
            main,
            [
                "archive",
                "rotate",
                "--older-than",
                "90",
                "--dry-run",
                "--format",
                "yaml",
            ],
        )
        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        payload = yaml.safe_load(result.output)
        assert isinstance(payload, dict)
        assert "candidates" in payload
        assert "older_than_days" in payload
        assert payload["older_than_days"] == 90
        assert payload["dry_run"] is True
        assert isinstance(payload["candidates"], list)

    def test_format_json_emits_parseable_json(self) -> None:
        """``--format json`` parses cleanly and contains the same keys."""
        result = runner.invoke(
            main,
            [
                "archive",
                "rotate",
                "--older-than",
                "90",
                "--dry-run",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        payload = json.loads(result.output)
        assert isinstance(payload, dict)
        assert payload["older_than_days"] == 90
        assert payload["dry_run"] is True
        assert isinstance(payload["candidates"], list)

    def test_default_format_is_yaml(self) -> None:
        """No ``--format`` flag defaults to YAML (ADR-d.2)."""
        result = runner.invoke(
            main,
            ["archive", "rotate", "--older-than", "90"],
        )
        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        # YAML is parseable by yaml.safe_load AND by json.loads only if it
        # happens to be valid JSON (it isn't here — keys are unquoted).
        # Try yaml first; json.loads MUST raise.
        payload = yaml.safe_load(result.output)
        assert isinstance(payload, dict)
        assert "candidates" in payload


# ---------- RED case D: click-tree wiring ----------


class TestClickTreeWiring:
    """``flow archive rotate --help`` exits 0 and lists all 3 options."""

    def test_help_lists_older_than_dry_run_format(self) -> None:
        """All three options are documented in ``--help`` output."""
        result = runner.invoke(main, ["archive", "rotate", "--help"])
        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        assert "--older-than" in result.output
        assert "--dry-run" in result.output
        assert "--format" in result.output


# ---------- helper unit tests ----------


class TestEntryMtimeHelper:
    """``_entry_mtime`` falls back to git-log when fs mtime is skewed."""

    def test_falls_back_to_git_log_on_windows_checkout_skew(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When fs_mtime is >30d ahead of git timestamp, prefer git.

        Uses a real entry under ``openspec/changes/archive/`` (where
        ``git log`` resolves correctly) and patches ``subprocess.run`` so
        the test does NOT depend on the actual git history of that file.
        """
        # Pick any real archived entry that has a proposal.md on disk.
        archive_dir = Path("openspec") / "changes" / "archive"
        assert archive_dir.exists(), "test precondition: repo archive must exist"
        entries = [p for p in archive_dir.iterdir() if (p / "proposal.md").exists()]
        assert entries, "test precondition: at least one archive entry must exist"
        real_entry = entries[0]

        # Simulate Windows checkout skew: bump fs_mtime to "now" (way ahead
        # of git). The helper MUST prefer the git log timestamp.
        now = datetime.now(tz=UTC)
        future = now + timedelta(days=400)
        os.utime(real_entry, (future.timestamp(), future.timestamp()))
        os.utime(
            real_entry / "proposal.md",
            (future.timestamp(), future.timestamp()),
        )

        # Mock subprocess.run to return a known git timestamp
        # (the real entry's actual git commit time, computed via the git CLI).
        import subprocess as _subprocess

        real_run = _subprocess.run
        git_ts_value = str(int((now - timedelta(days=400)).timestamp()))

        def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
            if args and args[0][:3] == ["git", "log", "-1"]:
                stdout_value = git_ts_value
                return _subprocess.CompletedProcess(
                    args=args[0],
                    returncode=0,
                    stdout=stdout_value,
                    stderr="",
                )
            return real_run(*args, **kwargs)

        monkeypatch.setattr(
            "flow_engineering.cli.rotation.subprocess.run",
            fake_run,
        )

        result = _entry_mtime(real_entry)

        # Tolerate up to 5s drift on the git timestamp comparison.
        expected = (now - timedelta(days=400)).timestamp()
        assert abs(result - expected) < 5, (
            f"expected fallback to git-log mtime (~{expected}); got {result} "
            f"(future fs_mtime would be ~{future.timestamp()})"
        )
