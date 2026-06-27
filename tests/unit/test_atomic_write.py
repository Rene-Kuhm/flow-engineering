"""Focused unit tests for :func:`observability.atomic_write_text` (D10 / REQ-38 prep).

The atomic write helper was introduced in change #6 PR#1 batch A (T1.1
GREEN) and is reused by PR#2's ``flow metrics --prometheus --out=<path>``
export path. This file pins the D10 contract:

- Writes ``content`` to ``target`` atomically (no partial-write window).
- Creates parent directories on demand.
- Replaces an existing file in a single ``os.replace`` call (POSIX + Windows
  atomicity when both paths are on the same filesystem — the
  ``dir=target.parent`` argument to ``tempfile.mkstemp`` guarantees that).
- Cleans up the ``.prom.tmp`` staging file on failure (no orphans).

Tests are regression coverage — the helper already exists, so all 4 tests
PASS at GREEN on commit. They lock in the contract so PR#2's
``flow metrics --prometheus --out`` integration can rely on the helper
without breaking D10.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flow_engineering import observability


# ---------- happy path ----------


class TestAtomicWriteCreatesAndOverwrites:
    """atomic_write_text(path, content) writes content + replaces existing files."""

    def test_atomic_write_text_creates_file_with_content(self, tmp_path: Path) -> None:
        """First write creates the file with the expected content."""
        target = tmp_path / "out.txt"
        observability.atomic_write_text(target, "hello world\n")

        assert target.exists()
        assert target.read_text(encoding="utf-8") == "hello world\n"
        # No leftover staging files in the parent dir.
        leftovers = sorted(p.name for p in tmp_path.glob("*"))
        assert leftovers == ["out.txt"]

    def test_atomic_write_text_overwrites_existing_file_atomically(
        self, tmp_path: Path,
    ) -> None:
        """Second write replaces the first content; no corruption window."""
        target = tmp_path / "out.txt"
        target.write_text("original content", encoding="utf-8")

        observability.atomic_write_text(target, "new content")

        assert target.read_text(encoding="utf-8") == "new content"
        # Only the target file remains; no stale staging file.
        leftovers = sorted(p.name for p in tmp_path.glob("*"))
        assert leftovers == ["out.txt"]


# ---------- parent-directory creation ----------


class TestAtomicWriteCreatesParentDirectories:
    """atomic_write_text creates the parent dir if it doesn't exist."""

    def test_atomic_write_text_creates_parent_directories(self, tmp_path: Path) -> None:
        """Writing to a target whose parent dir is missing creates it."""
        nested = tmp_path / "deeply" / "nested" / "out.txt"
        assert not nested.parent.exists()

        observability.atomic_write_text(nested, "data\n")

        assert nested.parent.exists()
        assert nested.read_text(encoding="utf-8") == "data\n"


# ---------- tempfile + os.replace pattern ----------


class TestAtomicWriteUsesTempfileAndRename:
    """Verify the helper uses mkstemp + os.replace (D10 atomic contract)."""

    def test_atomic_write_text_writes_to_tempfile_then_renames(
        self, tmp_path: Path,
    ) -> None:
        """The helper stages in a ``.prom.tmp`` file then calls ``os.replace``.

        Verifies the D10 pattern: write to a tempfile in the same parent dir
        (atomicity requires same filesystem), then atomic rename to the target.
        """
        target = tmp_path / "out.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        captured: dict = {}

        real_replace = __import__("os").replace

        def spy_replace(src, dst) -> None:
            """Capture (src, dst) then call the real os.replace."""
            captured["src"] = src
            captured["dst"] = dst
            real_replace(src, dst)

        with patch("flow_engineering.observability.os.replace", side_effect=spy_replace):
            observability.atomic_write_text(target, "staged content\n")

        # The src passed to os.replace MUST be a staging file inside the
        # target's parent dir (same-filesystem guarantee).
        assert "src" in captured, "os.replace was never called"
        staging_src = Path(str(captured["src"]))
        staging_dst = Path(str(captured["dst"]))
        assert staging_dst == target
        assert staging_src.parent == target.parent
        # Staging file should be the helper's prefix/suffix pair.
        assert staging_src.name.startswith(".metrics-")
        assert staging_src.name.endswith(".prom.tmp")
        # And the staging file should be gone (rename moved it).
        assert not staging_src.exists()
        # The target file holds the content.
        assert target.read_text(encoding="utf-8") == "staged content\n"


# ---------- rollback on os.replace failure ----------


class TestAtomicWriteRollsBackOnFailure:
    """When ``os.replace`` fails, the staging ``.prom.tmp`` is cleaned up."""

    def test_atomic_write_text_rolls_back_tmp_on_replace_failure(
        self, tmp_path: Path,
    ) -> None:
        """Simulated os.replace failure raises + leaves no orphan ``.prom.tmp``."""
        target = tmp_path / "out.txt"
        target.parent.mkdir(parents=True, exist_ok=True)

        with patch(
            "flow_engineering.observability.os.replace",
            side_effect=PermissionError("simulated replace failure"),
        ):
            with pytest.raises(PermissionError, match="simulated replace failure"):
                observability.atomic_write_text(target, "x")

        # The target file MUST NOT exist (the rename never completed).
        assert not target.exists()
        # The staging .prom.tmp MUST be cleaned up (no orphan).
        leftovers = list(tmp_path.glob("*"))
        assert leftovers == [], f"orphans left behind: {leftovers}"