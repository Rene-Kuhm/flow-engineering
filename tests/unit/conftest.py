"""Shared pytest fixtures for the ``tests/unit`` suite (REQ-V1.2.2).

REQ-V1.2.2 (T2.6 REFACTOR): the ``golden_snapshot_dir`` fixture provides
an isolated snapshot directory for the ``flow prompts show
--update-goldens`` + ``--check-snapshot`` test surface. Mirrors the
production ``tests/golden/prompts/`` layout but rooted at ``tmp_path``
so the CLI flags do NOT mutate the committed artifacts. The fixture
monkeypatches ``flow_engineering.cli._GOLDEN_PROMPTS_DIR`` so the CLI
helper reads from the isolated dir for the test scope only.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def golden_snapshot_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated golden snapshot directory for ``--update-goldens`` / ``--check-snapshot`` tests.

    Returns:
        A fresh ``tmp_path / golden / prompts`` directory created for
        the test scope. The CLI helper is monkeypatched to read from
        this directory so tests do NOT mutate the committed
        ``tests/golden/prompts/*.txt`` artifacts.
    """
    snap_dir = tmp_path / "golden" / "prompts"
    snap_dir.mkdir(parents=True)
    from flow_engineering import cli as cli_mod

    monkeypatch.setattr(cli_mod, "_GOLDEN_PROMPTS_DIR", snap_dir, raising=False)
    return snap_dir


@pytest.fixture
def production_golden_dir() -> Path:
    """Production golden snapshot directory (``tests/golden/prompts/``).

    Use this fixture for tests that verify byte-match against the
    committed snapshots (the canonical test surface). For tests that
    need to MUTATE the snapshot directory, use ``golden_snapshot_dir``
    instead.
    """
    return Path(__file__).resolve().parent.parent / "golden" / "prompts"
