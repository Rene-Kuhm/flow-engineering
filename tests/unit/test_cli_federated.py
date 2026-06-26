"""Unit tests for ``flow search --federated --projects --since --type`` CLI flags (REQ-25 T1.6).

TDD: written BEFORE the implementation. These MUST fail until the GREEN
commit wires the 4 new opt-in flags onto the existing ``flow search``
subcommand.

Coverage map (REQ-25 scenarios 1-5 at the CLI unit level):
1. ``flow search "drift"`` (no flag) is byte-identical to pre-change output.
2. ``flow search --federated "drift"`` returns results from all projects.
3. ``flow search --federated --projects=... "drift"`` restricts to the named projects.
4. ``flow search --federated --since=... "drift"`` excludes older observations.
5. ``flow search --federated --type=... "drift"`` includes only matching types.
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


def _make_obs(
    obs_id: int,
    *,
    title: str,
    content: str,
    project: str = "insyd",
    type: str = "manual",
    created_at: str | int = "2026-06-15 10:00:00",
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
def multi_project_backend(monkeypatch: pytest.MonkeyPatch) -> InMemoryBackend:
    """A 4-project fixture spanning the two filter dimensions (date + type)."""
    backend = InMemoryBackend()
    _seed(
        backend,
        [
            _make_obs(
                1,
                title="flow-engineering drift decision",
                content="we handle drift via Postgres triggers",
                project="flow-engineering",
                type="decision",
                created_at="2026-06-15 10:00:00",
            ),
            _make_obs(
                2,
                title="flow-engineering drift bugfix",
                content="fixed the drift detector false positive",
                project="flow-engineering",
                type="bugfix",
                created_at="2026-06-20 10:00:00",
            ),
            _make_obs(
                3,
                title="mockup-2-blog drift pattern",
                content="use a drift budget for blog posts",
                project="mockup-2-blog",
                type="pattern",
                created_at="2026-06-25 10:00:00",
            ),
            _make_obs(
                4,
                title="mockup-2-blog old drift",
                content="an older drift decision from may",
                project="mockup-2-blog",
                type="decision",
                created_at="2026-05-15 10:00:00",
            ),
            _make_obs(
                5,
                title="tecnodespegue-landing decision",
                content="another drift decision from a peer",
                project="tecnodespegue-landing",
                type="decision",
                created_at="2026-06-18 10:00:00",
            ),
            _make_obs(
                6,
                title="unrelated noise",
                content="nothing about drift in here",
                project="flow-engineering",
                type="manual",
                created_at="2026-06-22 10:00:00",
            ),
        ],
    )
    monkeypatch.setattr("flow_engineering.cli._default_save_backend", lambda: backend)
    return backend


# ---------- REQ-25 scenario 1: --federated absent → byte-identical ----------


class TestSearchNoFederatedUnchanged:
    """Default ``flow search`` (no --federated) MUST be byte-identical to pre-change."""

    def test_default_search_unaffected_by_federated_flag_absence(
        self, multi_project_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(main, ["search", "drift"])
        assert result.exit_code == 0, result.output
        # mem_search (prose) returns ALL drift observations because it does
        # not filter by project — InMemoryBackend.mem_search matches on
        # substring. The key contract is: backend.mem_search is called,
        # NOT mem_search_federated.
        assert "drift" in result.output.lower()

    def test_default_search_does_not_call_mem_search_federated(
        self, multi_project_backend: InMemoryBackend, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering import cli as cli_mod

        called: dict[str, int] = {"federated": 0, "plain": 0}
        real_federated = multi_project_backend.mem_search_federated
        real_plain = multi_project_backend.mem_search

        def federated_spy(*args: Any, **kwargs: Any) -> Any:
            called["federated"] += 1
            return real_federated(*args, **kwargs)

        def plain_spy(*args: Any, **kwargs: Any) -> Any:
            called["plain"] += 1
            return real_plain(*args, **kwargs)

        monkeypatch.setattr(multi_project_backend, "mem_search_federated", federated_spy)
        monkeypatch.setattr(multi_project_backend, "mem_search", plain_spy)

        result = runner.invoke(main, ["search", "drift"])
        assert result.exit_code == 0, result.output
        assert called["federated"] == 0, "default search must NOT call mem_search_federated"
        assert called["plain"] >= 1, "default search MUST call mem_search"


# ---------- REQ-25 scenario 2: --federated without --projects → all projects ----------


class TestSearchFederatedAllProjects:
    """``flow search --federated "drift"`` returns rows from every project."""

    def test_federated_returns_rows_with_project_field(
        self, multi_project_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(main, ["search", "--federated", "drift", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        results = payload["results"]
        # 5 drift observations across 3 projects (the 6th is unrelated noise).
        assert len(results) == 5
        # Every row MUST carry a project field.
        assert all("project" in r for r in results)
        projects_seen = {r["project"] for r in results}
        assert projects_seen == {
            "flow-engineering",
            "mockup-2-blog",
            "tecnodespegue-landing",
        }

    def test_federated_text_table_includes_project_column(
        self, multi_project_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(main, ["search", "--federated", "drift"])
        assert result.exit_code == 0, result.output
        # Header line in table mode: the uppercase PROJECT header must appear.
        assert "PROJECT" in result.output.upper()


# ---------- REQ-25 scenario 3: --federated --projects=<csv> restricts ----------


class TestSearchFederatedProjectsCSV:
    """``--federated --projects=flow-engineering,mockup-2-blog`` restricts the scope."""

    def test_projects_csv_restricts_to_named(
        self, multi_project_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            ["search", "--federated", "--projects=flow-engineering,mockup-2-blog", "drift", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        projects_seen = {r["project"] for r in payload["results"]}
        assert projects_seen <= {"flow-engineering", "mockup-2-blog"}
        # tecnodespegue-landing MUST NOT appear.
        assert "tecnodespegue-landing" not in projects_seen

    def test_projects_csv_calls_backend_with_list(
        self, multi_project_backend: InMemoryBackend, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from flow_engineering import cli as cli_mod

        captured: dict[str, Any] = {}

        def spy(query: str, projects: list[str] | None = None, **kwargs: Any) -> Any:
            captured["query"] = query
            captured["projects"] = projects
            captured["kwargs"] = kwargs
            return multi_project_backend.observations[1] and [
                multi_project_backend.observations[1],
                multi_project_backend.observations[3],
            ]

        # Re-route via the cli module's backend spy.
        def backend_factory() -> Any:
            class Spy:
                def mem_search_federated(self_inner, *a: Any, **k: Any) -> Any:  # type: ignore[no-untyped-def]
                    return spy(*a, **k)

                def mem_search(self_inner, *a: Any, **k: Any) -> Any:  # type: ignore[no-untyped-def]
                    return []

            return Spy()

        monkeypatch.setattr(cli_mod, "_default_save_backend", backend_factory)

        result = runner.invoke(
            main,
            ["search", "--federated", "--projects=flow-engineering,mockup-2-blog", "drift"],
        )
        assert result.exit_code == 0, result.output
        assert captured.get("projects") == ["flow-engineering", "mockup-2-blog"]


# ---------- REQ-25 scenario 4: --federated --since=<iso> ----------


class TestSearchFederatedSince:
    """``--federated --since=2026-06-01`` excludes observations created before that date."""

    def test_since_filter_excludes_older(
        self, multi_project_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            ["search", "--federated", "--since=2026-06-01", "drift", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        # The mockup-2-blog old drift (obs 4, 2026-05-15) MUST be excluded.
        titles = [r["title"] for r in payload["results"]]
        assert "mockup-2-blog old drift" not in titles

    def test_since_filter_keeps_recent(
        self, multi_project_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            ["search", "--federated", "--since=2026-06-01", "drift", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        titles = [r["title"] for r in payload["results"]]
        # The flow-engineering drift decision (obs 1, 2026-06-15) stays.
        assert "flow-engineering drift decision" in titles


# ---------- REQ-25 scenario 5: --federated --type=<csv> ----------


class TestSearchFederatedType:
    """``--federated --type=decision`` includes only matching type observations."""

    def test_type_single_restricts_to_named_type(
        self, multi_project_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            ["search", "--federated", "--type=decision", "drift", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        # Obs 2 is bugfix (excluded), Obs 3 is pattern (excluded).
        titles = [r["title"] for r in payload["results"]]
        assert "flow-engineering drift bugfix" not in titles
        assert "mockup-2-blog drift pattern" not in titles
        # Obs 1, 4, 5 are decision (kept).
        assert "flow-engineering drift decision" in titles

    def test_type_csv_includes_listed_types(
        self, multi_project_backend: InMemoryBackend
    ) -> None:
        result = runner.invoke(
            main,
            ["search", "--federated", "--type=decision,bugfix", "drift", "--json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        titles = [r["title"] for r in payload["results"]]
        # Obs 3 (pattern) excluded; obs 1 (decision), 2 (bugfix) included.
        assert "mockup-2-blog drift pattern" not in titles
        assert "flow-engineering drift decision" in titles
        assert "flow-engineering drift bugfix" in titles
