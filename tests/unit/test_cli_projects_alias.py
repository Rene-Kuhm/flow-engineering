"""Unit tests for ``flow projects alias <old> <new>`` CLI subcommand (REQ-27 T1.10).

TDD: written BEFORE the implementation. These MUST fail until the GREEN
commit wires the ``alias`` subcommand onto the existing ``flow projects``
group from T1.12 (batch B2) AND wires the alias-iteration path into
``flow projects backfill --confirm`` (without ``--project``), closing
the batch B2 deviation noted in Engram #167.

Coverage map (REQ-27 scenarios 2 + 3 + 4 at the CLI unit level + the
batch B2 deviation fix):

2. ``flow projects alias <old> <new>`` writes ``project-aliases.json``
   and prints confirmation on stdout.
3. Re-invoking with a DIFFERENT ``new`` for the same ``old`` exits
   non-zero (no silent history loss).
4. Re-invoking with the SAME ``old> <new>`` is a no-op + prints
   confirmation (``alias already present``).
Plus:
- Alias-iteration backfill: ``flow projects backfill --confirm`` (no
  ``--project``) iterates the alias map and re-tags every observation
  whose ``project`` matches an ``alias.old`` to ``alias.new``. Closes
  the batch B2 deviation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main
from flow_engineering.engram_io import InMemoryBackend

runner = CliRunner()


# ---------- Fixtures ----------


def _make_obs(
    obs_id: int,
    *,
    title: str = "obs",
    content: str = "c",
    project: str | None = "insyd",
    type: str = "manual",  # noqa: A002
    created_at: str = "2026-06-15 10:00:00",
) -> dict[str, Any]:
    return {
        "id": obs_id,
        "title": title,
        "content": content,
        "topic_key": "sdd/test/phase",
        "type": type,
        "scope": "project",
        "project": project,
        "created_at": created_at,
        "updated_at": created_at,
    }


def _seed(backend: InMemoryBackend, observations: list[dict[str, Any]]) -> None:
    for o in observations:
        backend.observations[o["id"]] = o
        backend.next_id = max(backend.next_id, o["id"] + 1)


@pytest.fixture
def alias_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the default alias path at a tmp file so tests do not pollute ~/.config."""
    path = tmp_path / "project-aliases.json"
    # The CLI looks up ``project_aliases.DEFAULT_ALIASES_PATH`` so we must
    # monkeypatch it before the subcommand runs.
    from flow_engineering import project_aliases

    monkeypatch.setattr(project_aliases, "DEFAULT_ALIASES_PATH", path)
    return path


@pytest.fixture
def alias_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> InMemoryBackend:
    """Empty in-memory backend wired to ``_default_save_backend``."""
    backend = InMemoryBackend()
    monkeypatch.setattr("flow_engineering.cli._default_save_backend", lambda: backend)
    return backend


# ---------- REQ-27 scenario 2: flow projects alias writes the file ----------


class TestProjectsAliasWrite:
    """``flow projects alias <old> <new>`` writes ``project-aliases.json``."""

    def test_alias_writes_file_and_prints_confirmation(
        self, alias_path: Path, alias_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            [
                "projects",
                "alias",
                "flow-image-generator-v2",
                "flow-image-generator-main",
            ],
        )
        assert result.exit_code == 0, result.output
        assert alias_path.exists()
        payload = json.loads(alias_path.read_text(encoding="utf-8"))
        assert payload["version"] == 1
        assert len(payload["aliases"]) == 1
        record = payload["aliases"][0]
        assert record["old"] == "flow-image-generator-v2"
        assert record["new"] == "flow-image-generator-main"
        # Stdout confirmation includes the alias mapping.
        assert "flow-image-generator-v2" in result.stdout
        assert "flow-image-generator-main" in result.stdout


# ---------- REQ-27 scenario 4: idempotent re-invoke is a no-op ----------


class TestProjectsAliasIdempotent:
    """Re-invoking ``alias <old> <new>`` with the same args is a no-op."""

    def test_idempotent_re_invoke_no_op(
        self, alias_path: Path, alias_backend: InMemoryBackend
    ) -> None:
        # First call writes the file.
        first = runner.invoke(
            main,
            [
                "projects",
                "alias",
                "flow-image-generator-v2",
                "flow-image-generator-main",
            ],
        )
        assert first.exit_code == 0, first.output

        # Second call with the SAME args: no-op + confirmation, exit 0.
        second = runner.invoke(
            main,
            [
                "projects",
                "alias",
                "flow-image-generator-v2",
                "flow-image-generator-main",
            ],
        )
        assert second.exit_code == 0, second.output
        assert "already present" in second.stdout.lower(), (
            f"Expected idempotent confirmation in stdout, got: {second.stdout!r}"
        )
        # The file STILL has exactly one record (no duplicate row).
        payload = json.loads(alias_path.read_text(encoding="utf-8"))
        assert len(payload["aliases"]) == 1


# ---------- REQ-27 scenario 3: conflicting rewrite ERRORS ----------


class TestProjectsAliasConflict:
    """Re-invoking ``alias <old> <different_new>`` ERRORS (no silent history loss)."""

    def test_conflict_exits_nonzero_and_preserves_existing(
        self, alias_path: Path, alias_backend: InMemoryBackend
    ) -> None:
        # Seed an existing alias.
        runner.invoke(
            main,
            ["projects", "alias", "a", "ORIGINAL"],
        )
        # Try to rewrite the same ``old`` to a DIFFERENT ``new``.
        result = runner.invoke(main, ["projects", "alias", "a", "DIFFERENT"])
        assert result.exit_code != 0, (
            f"Expected non-zero exit on conflict, got 0; output={result.output!r}"
        )
        # Stderr OR output mentions the conflict (Click joins them).
        combined = (result.output or "") + (result.stderr or "")
        assert "a" in combined and "ORIGINAL" in combined, (  # noqa: PT018
            f"Expected conflict message naming 'a' and 'ORIGINAL'; got: {combined!r}"
        )
        # Existing record UNCHANGED.
        payload = json.loads(alias_path.read_text(encoding="utf-8"))
        assert len(payload["aliases"]) == 1
        assert payload["aliases"][0]["new"] == "ORIGINAL"


# ---------- Batch B2 deviation fix: alias iteration in backfill --confirm ----------


class TestProjectsBackfillAliasIteration:
    """``flow projects backfill --confirm`` (no --project) iterates the alias map.

    Closes the batch B2 deviation from Engram #167: the previously-refused
    invocation now re-tags observations whose ``project`` matches an
    ``alias.old`` to ``alias.new``. The implementation iterates the alias
    map (NOT a global scan) and only re-tags observations matching an
    alias ``old`` key.
    """

    def _seed_multi_alias_corpus(self, alias_backend: InMemoryBackend) -> None:
        _seed(
            alias_backend,
            [
                _make_obs(1, title="old-key-A", project="old-key-A"),
                _make_obs(2, title="old-key-B", project="old-key-B"),
                _make_obs(3, title="unrelated", project="unrelated-project"),
            ],
        )

    def test_confirm_without_project_iterates_alias_map(
        self,
        alias_path: Path,
        alias_backend: InMemoryBackend,
    ) -> None:
        # Seed two aliases: old-key-A -> new-key-A, old-key-B -> new-key-B.
        runner.invoke(main, ["projects", "alias", "old-key-A", "new-key-A"])
        runner.invoke(main, ["projects", "alias", "old-key-B", "new-key-B"])
        self._seed_multi_alias_corpus(alias_backend)

        # The previously-refused invocation now resolves via the alias map.
        result = runner.invoke(main, ["projects", "backfill", "--confirm"])
        assert result.exit_code == 0, result.output

        # Both alias-matching observations are re-tagged.
        tagged = {obs["id"]: obs.get("project") for obs in alias_backend.observations.values()}
        assert tagged[1] == "new-key-A", f"Expected obs 1 re-tagged to new-key-A, got {tagged[1]!r}"
        assert tagged[2] == "new-key-B", f"Expected obs 2 re-tagged to new-key-B, got {tagged[2]!r}"
        # Unrelated observation is UNCHANGED.
        assert tagged[3] == "unrelated-project", f"Expected obs 3 unchanged, got {tagged[3]!r}"

    def test_dry_run_without_project_iterates_alias_map_no_writes(
        self,
        alias_path: Path,
        alias_backend: InMemoryBackend,
    ) -> None:
        runner.invoke(main, ["projects", "alias", "old-key-A", "new-key-A"])
        self._seed_multi_alias_corpus(alias_backend)

        # Dry-run preview: exits 0, lists both, but writes nothing.
        result = runner.invoke(main, ["projects", "backfill", "--dry-run"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        # Both alias-matching observations are reported.
        changes = payload.get("changes", [])
        ids = {c["observation_id"] for c in changes}
        assert 1 in ids
        assert 2 not in ids  # obs 2 has no alias match
        # No writes happened.
        assert alias_backend.observations[1]["project"] == "old-key-A"

    def test_confirm_without_project_no_aliases_writes_nothing(
        self,
        alias_path: Path,
        alias_backend: InMemoryBackend,
    ) -> None:
        # Empty alias map + no --project: nothing to do (the previous B2
        # refusal was a safety gate; with alias iteration in place, the
        # empty-alias-map case yields zero changes because no observation
        # matches an ``alias.old`` key).
        self._seed_multi_alias_corpus(alias_backend)
        result = runner.invoke(main, ["projects", "backfill", "--confirm"])
        # Exit code 0 with empty changes report (not a refusal).
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["would_change"] == 0
        assert payload["changes"] == []
        # No writes happened.
        for obs in alias_backend.observations.values():
            assert obs.get("project") != "new-key-A"
            assert obs.get("project") != "new-key-B"
