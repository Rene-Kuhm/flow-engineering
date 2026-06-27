"""Unit tests for ``flow projects backfill [--dry-run|--confirm] [--project] [--since]`` (REQ-24 T1.12).

TDD: written BEFORE the implementation. These MUST fail until the GREEN
commit wires the ``flow projects`` group + ``backfill`` subcommand onto
the existing CLI with the safety gate described in design D3 + REQ-24.

Coverage map (REQ-24 scenarios 3-6 at the CLI unit level):

3. ``flow projects backfill`` (no flags) defaults to dry-run (no writes).
4. ``flow projects backfill --confirm --project=<key>`` writes tags.
5. ``flow projects backfill --confirm`` without ``--project`` REFUSES with
   non-zero exit (scope unclear / safety gate).
6. ``flow projects backfill --dry-run`` emits a JSON report
   ``{observation_id, current_tag, proposed_tag, action}`` per row.

Plus extras for the JSON envelope shape (``would_change`` + ``would_skip``
counts), exit-code contract, and the ``--since`` filter.
"""

from __future__ import annotations

import json
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
    type: str = "manual",
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
def backfill_backend(monkeypatch: pytest.MonkeyPatch) -> InMemoryBackend:
    """3-observation fixture: 1 untagged, 1 already tagged, 1 from another date."""
    backend = InMemoryBackend()
    _seed(
        backend,
        [
            _make_obs(1, title="untagged A", project=None, created_at="2026-06-15 10:00:00"),
            _make_obs(2, title="already tagged", project="insyd", created_at="2026-06-15 10:00:00"),
            _make_obs(3, title="older untagged", project=None, created_at="2026-05-15 10:00:00"),
        ],
    )
    monkeypatch.setattr("flow_engineering.cli._default_save_backend", lambda: backend)
    return backend


@pytest.fixture
def empty_backend(monkeypatch: pytest.MonkeyPatch) -> InMemoryBackend:
    """Empty corpus — backfill has nothing to do."""
    backend = InMemoryBackend()
    monkeypatch.setattr("flow_engineering.cli._default_save_backend", lambda: backend)
    return backend


# ---------- REQ-24 scenario 3 + design D3 default: --dry-run ----------


class TestBackfillDryRunDefault:
    """``flow projects backfill`` with no flags defaults to dry-run (no writes)."""

    def test_no_flags_exits_zero(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(main, ["projects", "backfill"])
        assert result.exit_code == 0, result.output

    def test_no_flags_does_not_mutate(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(main, ["projects", "backfill"])
        assert result.exit_code == 0, result.output
        # Observation 1 (untagged) MUST remain untagged.
        assert backfill_backend.observations[1]["project"] is None
        # Observation 2 (already tagged) MUST remain tagged "insyd".
        assert backfill_backend.observations[2]["project"] == "insyd"

    def test_explicit_dry_run_is_same_as_default(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(main, ["projects", "backfill", "--dry-run"])
        assert result.exit_code == 0, result.output
        # No mutation under explicit --dry-run either.
        assert backfill_backend.observations[1]["project"] is None


# ---------- REQ-24 scenario 4: --confirm --project=<key> writes ----------


class TestBackfillConfirmWithProject:
    """``flow projects backfill --confirm --project=<key>`` writes tags."""

    def test_confirm_with_project_tags_untagged(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            ["projects", "backfill", "--confirm", "--project=flow-engineering"],
        )
        assert result.exit_code == 0, result.output
        # Observation 1 (was untagged) MUST now be tagged flow-engineering.
        assert backfill_backend.observations[1]["project"] == "flow-engineering"
        # Observation 2 (already tagged insyd) MUST remain unchanged.
        assert backfill_backend.observations[2]["project"] == "insyd"

    def test_confirm_emits_json_report(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            ["projects", "backfill", "--confirm", "--project=flow-engineering"],
        )
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        assert isinstance(report, dict)
        assert "changes" in report
        # At least one change entry should exist (the previously-untagged obs).
        tagged_changes = [
            c for c in report["changes"]
            if c.get("action") in ("rename", "tagged")
            and c.get("proposed_tag") == "flow-engineering"
        ]
        assert tagged_changes, (
            f"Expected at least one tagged change; got {report['changes']!r}"
        )

    def test_dry_run_with_project_preview_only(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            ["projects", "backfill", "--dry-run", "--project=flow-engineering"],
        )
        assert result.exit_code == 0, result.output
        # Dry-run MUST NOT mutate even with --project specified.
        assert backfill_backend.observations[1]["project"] is None


# ---------- REQ-24 scenario 5: --confirm without --project REFUSES ----------


class TestBackfillConfirmRefusesWithoutProject:
    """``flow projects backfill --confirm`` without ``--project`` REFUSES.

    Scope is ambiguous (multiple project keys could match) — the safety
    gate forces the caller to be explicit. Mirrors the dry-run default:
    no silent mass-rename ever runs.
    """

    def test_confirm_without_project_exits_nonzero(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(main, ["projects", "backfill", "--confirm"])
        assert result.exit_code != 0, (
            f"Expected non-zero exit; got {result.exit_code}; output={result.output!r}"
        )

    def test_confirm_without_project_does_not_mutate(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(main, ["projects", "backfill", "--confirm"])
        assert result.exit_code != 0
        # Even though the refusal exit was non-zero, observations MUST stay unchanged.
        assert backfill_backend.observations[1]["project"] is None
        assert backfill_backend.observations[2]["project"] == "insyd"


# ---------- REQ-24 scenario 6: --dry-run JSON report shape ----------


class TestBackfillDryRunJsonReport:
    """``flow projects backfill --dry-run`` emits JSON report to stdout."""

    def test_dry_run_emits_json_envelope(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(main, ["projects", "backfill", "--dry-run"])
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        # JSON envelope MUST contain the counters + per-row changes list.
        assert "would_change" in report, f"missing would_change in {report!r}"
        assert "would_skip" in report, f"missing would_skip in {report!r}"
        assert "changes" in report, f"missing changes in {report!r}"
        assert isinstance(report["would_change"], int)
        assert isinstance(report["would_skip"], int)
        assert isinstance(report["changes"], list)

    def test_dry_run_change_entry_shape(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            ["projects", "backfill", "--dry-run", "--project=flow-engineering"],
        )
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        for change in report["changes"]:
            assert "observation_id" in change, f"missing observation_id in {change!r}"
            assert "current_tag" in change
            assert "proposed_tag" in change
            assert "action" in change
            assert change["action"] in (
                "rename",
                "skip_already_tagged",
                "skip_no_match",
            ), f"unexpected action {change['action']!r}"


# ---------- Exit-code contract ----------


class TestBackfillExitCodes:
    """Exit codes: 0 = success / dry-run, 1 = empty corpus, 2 = invalid args."""

    def test_empty_corpus_exits_one(self, empty_backend: InMemoryBackend) -> None:
        result = runner.invoke(main, ["projects", "backfill"])
        assert result.exit_code == 1, (
            f"Expected exit 1 (empty corpus); got {result.exit_code}; output={result.output!r}"
        )

    def test_confirm_without_project_exits_two(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(main, ["projects", "backfill", "--confirm"])
        assert result.exit_code == 2, (
            f"Expected exit 2 (invalid args); got {result.exit_code}; output={result.output!r}"
        )


# ---------- --since filter ----------


class TestBackfillSinceFilter:
    """``--since=<iso>`` restricts to observations created on/after the timestamp."""

    def test_since_excludes_older_observations(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            [
                "projects",
                "backfill",
                "--dry-run",
                "--project=flow-engineering",
                "--since=2026-06-01",
            ],
        )
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        # Observation 3 (created 2026-05-15) MUST be excluded by --since.
        obs_ids = [c.get("observation_id") for c in report["changes"]]
        assert 3 not in obs_ids, (
            f"Expected obs 3 to be excluded by --since; got changes={report['changes']!r}"
        )

    def test_invalid_since_exits_two(
        self, backfill_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            [
                "projects",
                "backfill",
                "--dry-run",
                "--since=not-an-iso",
            ],
        )
        assert result.exit_code == 2, (
            f"Expected exit 2 (invalid --since); got {result.exit_code}; output={result.output!r}"
        )
