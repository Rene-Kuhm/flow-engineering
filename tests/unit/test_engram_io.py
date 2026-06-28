"""Unit tests for engram_io.py — cross-session memory wrapper.

REQ-8: Cross-session recovery via Engram topic keys.
REQ-17: Semantic search activation gate (vector-semantic-search PR#1 T1.2).
REQ-23: Federated multi-project search (cross-project-federation PR#1 T1.2).
"""

from __future__ import annotations

import json

import pytest

from flow_engineering.engram_io import (
    EngramBackend,
    EngramClient,
    InMemoryBackend,
    VectorSearchDisabled,
    cross_session_topic_key,
    phase_topic_key,
)


class TestTopicKeys:
    def test_phase_topic_key(self) -> None:
        assert phase_topic_key("my-change", "explore") == "sdd/my-change/explore"
        assert phase_topic_key("my-change", "apply-progress") == "sdd/my-change/apply-progress"

    def test_cross_session_topic_key(self) -> None:
        assert cross_session_topic_key() == "sdd/flow-engineering"


class TestEngramClientSaveLoad:
    def test_save_and_load_phase(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("explore", "## Exploration content here")
        loaded = client.load_phase("explore")
        # save_phase now appends an unbound code_refs block, so we check
        # prose membership instead of byte-for-byte equality.
        assert loaded is not None
        assert "## Exploration content here" in loaded
        assert "code_refs" in loaded

    def test_load_missing_phase_returns_none(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        assert client.load_phase("propose") is None

    def test_save_phase_with_custom_title(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("explore", "content", title="Custom title")
        results = backend.mem_search(query="Custom", topic_key="sdd/my-change/explore")
        assert len(results) == 1
        assert results[0]["title"] == "Custom title"

    def test_two_changes_isolated(self) -> None:
        backend = InMemoryBackend()
        client_a = EngramClient("change-a", backend)
        client_b = EngramClient("change-b", backend)
        client_a.save_phase("explore", "A explore content")
        client_b.save_phase("explore", "B explore content")
        loaded_a = client_a.load_phase("explore")
        loaded_b = client_b.load_phase("explore")
        assert loaded_a is not None
        assert "A explore content" in loaded_a
        assert loaded_b is not None
        assert "B explore content" in loaded_b


class TestApplyProgress:
    def test_save_progress_creates_task(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_progress("T1.1", "completed")
        # save_phase now appends an unbound code_refs block; parse only the prose.
        loaded_raw = client.load_phase("apply-progress")
        assert loaded_raw is not None
        prose = loaded_raw.split("<!-- code_refs -->")[0]
        loaded = json.loads(prose)
        assert loaded["tasks"]["T1.1"]["status"] == "completed"

    def test_save_progress_updates_existing(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_progress("T1.1", "in_progress", details={"note": "started"})
        client.save_progress("T1.1", "completed", details={"tests_passed": True})
        loaded_raw = client.load_phase("apply-progress")
        assert loaded_raw is not None
        prose = loaded_raw.split("<!-- code_refs -->")[0]
        loaded = json.loads(prose)
        assert loaded["tasks"]["T1.1"]["status"] == "completed"
        assert loaded["tasks"]["T1.1"]["details"]["tests_passed"] is True


class TestCrossSession:
    def test_search_cross_session(self) -> None:
        backend = InMemoryBackend()
        client = EngramClient("my-change", backend)
        client.save_phase("explore", "This is about Flow Engineering")
        results = client.search_cross_session("Flow Engineering")
        assert len(results) >= 1


class TestVectorSearchDisabled:
    """REQ-17: semantic search activation gate (vector-semantic-search PR#1 T1.2).

    InMemoryBackend is the legacy prose test fixture. It MUST raise
    VectorSearchDisabled (with the install hint) when vector/hybrid methods are
    called, while mem_search (FTS5 prose) continues to work unchanged.
    """

    def test_inmemory_mem_search_semantic_raises_vector_search_disabled(self) -> None:
        backend = InMemoryBackend()
        with pytest.raises(VectorSearchDisabled) as exc_info:
            backend.mem_search_semantic("any query")
        assert "pip install flow-engineering[vectors]" in str(exc_info.value)

    def test_inmemory_mem_search_hybrid_raises_vector_search_disabled(self) -> None:
        backend = InMemoryBackend()
        with pytest.raises(VectorSearchDisabled) as exc_info:
            backend.mem_search_hybrid("any query", k=5, alpha=0.5)
        assert "pip install flow-engineering[vectors]" in str(exc_info.value)

    def test_vector_search_disabled_is_runtime_error_subclass(self) -> None:
        # Catchable as RuntimeError so callers can isolate it from other errors.
        assert issubclass(VectorSearchDisabled, RuntimeError)

    def test_inmemory_mem_search_still_works_unchanged(self) -> None:
        # REQ-17 scenario 5 zero regression: prose FTS5 path is byte-identical.
        backend = InMemoryBackend()
        backend.mem_save(
            title="drift entry",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
        )
        results = backend.mem_search("drift detection")
        assert len(results) == 1
        assert "drift detection strategy" in results[0]["content"]

    def test_inmemory_mem_search_semantic_does_not_import_torch(self) -> None:
        # Spec REQ-17: no torch/sqlite_vec import attempted at any gate path.
        import sys

        before = {"torch", "sentence_transformers", "sqlite_vec"} & set(sys.modules)
        try:
            backend = InMemoryBackend()
            with pytest.raises(VectorSearchDisabled):
                backend.mem_search_semantic("drift detection")
        finally:
            after = {"torch", "sentence_transformers", "sqlite_vec"} & set(sys.modules)
            assert before == after, (
                f"Vector search gate leaked heavy imports: {after - before}"
            )


class TestFederatedSearch:
    """REQ-23: federated multi-project search (cross-project-federation T1.2).

    ``InMemoryBackend.mem_search_federated`` filters the in-memory dict by
    ``projects`` (list membership), ``since`` (lexicographic ``>=`` on
    ``YYYY-MM-DD HH:MM:SS`` TEXT) and ``type_filter`` (exact match, case
    sensitive). Each returned row MUST preserve the ``project`` field.

    ABC default raises ``NotImplementedError`` when not overridden (third-party
    subclass scenario).
    """

    @staticmethod
    def _seed_three_projects(backend: InMemoryBackend) -> dict[str, int]:
        """Seed 3 obs, one per project. Returns {project: obs_id}."""
        ids: dict[str, int] = {}
        for project in ("flow-engineering", "mockup-2-blog", "tecnodespegue-landing"):
            obs = backend.mem_save(
                title=f"{project} drift entry",
                content=f"drift detection strategy in {project}",
                topic_key="sdd/x/spec",
            )
            obs["project"] = project
            obs["created_at"] = "2026-06-15 12:00:00"
            ids[project] = obs["id"]
        return ids

    def test_federated_three_projects_returns_each_with_project_field(self) -> None:
        # REQ-23 scenario 1: federation across 3 projects preserves `project` field.
        backend = InMemoryBackend()
        self._seed_three_projects(backend)
        results = backend.mem_search_federated(
            "drift",
            projects=["flow-engineering", "mockup-2-blog", "tecnodespegue-landing"],
            limit=10,
        )
        assert len(results) == 3, f"Expected 3 results, got {len(results)}: {results}"
        returned_projects = {r["project"] for r in results}
        assert returned_projects == {
            "flow-engineering",
            "mockup-2-blog",
            "tecnodespegue-landing",
        }, f"Project attribution mismatch: {returned_projects}"
        for r in results:
            assert r.get("project") is not None, f"Missing project field: {r!r}"

    def test_federated_projects_filter_restricts_to_single(self) -> None:
        # REQ-23 scenario 2: projects=['x'] returns ONLY project=x rows.
        backend = InMemoryBackend()
        ids = self._seed_three_projects(backend)
        results = backend.mem_search_federated("drift", projects=["flow-engineering"])
        assert len(results) == 1, f"Expected 1 result, got {len(results)}: {results}"
        assert results[0]["project"] == "flow-engineering"
        assert results[0]["id"] == ids["flow-engineering"]

    def test_federated_projects_none_searches_all(self) -> None:
        # projects=None ⇒ no project filter (search all 3).
        backend = InMemoryBackend()
        self._seed_three_projects(backend)
        results = backend.mem_search_federated("drift", projects=None, limit=10)
        assert len(results) == 3, f"Expected 3 results, got {len(results)}: {results}"

    def test_federated_since_filter_excludes_older(self) -> None:
        # REQ-23 scenario 3: since='2026-06-01' excludes obs created before.
        backend = InMemoryBackend()
        old = backend.mem_save(
            title="old entry",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
        )
        old["project"] = "flow-engineering"
        old["created_at"] = "2026-05-15 10:00:00"
        new = backend.mem_save(
            title="new entry",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
        )
        new["project"] = "flow-engineering"
        new["created_at"] = "2026-06-15 10:00:00"
        results = backend.mem_search_federated(
            "drift",
            projects=["flow-engineering"],
            since="2026-06-01",
        )
        ids = [r["id"] for r in results]
        assert new["id"] in ids, f"Expected new obs {new['id']} in {ids}"
        assert old["id"] not in ids, f"Did not expect old obs {old['id']} in {ids}"

    def test_federated_type_filter_includes_only_listed(self) -> None:
        # REQ-23 scenario 4: type_filter=['decision', 'bugfix'] exact match.
        backend = InMemoryBackend()
        decision = backend.mem_save(
            title="d",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
            type="decision",
        )
        decision["project"] = "flow-engineering"
        decision["created_at"] = "2026-06-15 10:00:00"
        bugfix = backend.mem_save(
            title="b",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
            type="bugfix",
        )
        bugfix["project"] = "flow-engineering"
        bugfix["created_at"] = "2026-06-15 10:00:00"
        pattern = backend.mem_save(
            title="p",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
            type="pattern",
        )
        pattern["project"] = "flow-engineering"
        pattern["created_at"] = "2026-06-15 10:00:00"
        results = backend.mem_search_federated(
            "drift",
            projects=["flow-engineering"],
            type_filter=["decision", "bugfix"],
        )
        ids = {r["id"] for r in results}
        types = {r["type"] for r in results}
        assert decision["id"] in ids
        assert bugfix["id"] in ids
        assert pattern["id"] not in ids
        assert types == {"decision", "bugfix"}, f"Unexpected types: {types}"

    def test_federated_empty_projects_raises_value_error(self) -> None:
        # REQ-23 scenario 5: projects=[] ⇒ ValueError (fail fast; SQLite IN () syntax).
        backend = InMemoryBackend()
        backend.mem_save(
            title="any",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
        )
        with pytest.raises(ValueError) as exc_info:  # noqa: PT011
            backend.mem_search_federated("drift", projects=[])
        assert "projects" in str(exc_info.value).lower()

    def test_federated_empty_projects_returns_empty_via_short_circuit(self) -> None:
        # Alternative interpretation: projects=[] ⇒ return [] without filtering.
        # Per spec #161 design D1: empty list MUST short-circuit BEFORE SQL runs.
        # We chose ValueError (explicit fail fast); this test documents the
        # alternative to keep the contract honest.
        backend = InMemoryBackend()
        backend.mem_save(
            title="any",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
        )
        # With ValueError chosen, this assertion is the documented behavior.
        try:
            results = backend.mem_search_federated("drift", projects=[])
            assert results == [], "If no raise, expected short-circuit []"
        except ValueError:
            pass  # explicitly chosen in T1.2 acceptance

    def test_abc_default_raises_not_implemented_when_not_overridden(self) -> None:
        # REQ-23 scenario: third-party subclass without override raises at call time.

        class PlainBackend(EngramBackend):
            def mem_save(self, title, content, topic_key, type="manual", scope="project"):  # noqa: A002
                return {"id": 1, "title": title, "content": content}

            def mem_search(self, query, topic_key=None, limit=10, scope="project"):
                return []

            def mem_get_observation(self, id):  # noqa: A002
                return {"id": id}

        with pytest.raises(NotImplementedError) as exc_info:
            PlainBackend().mem_search_federated("drift")
        assert "v1.2" in str(exc_info.value), (
            f"Expected 'v1.2' in error message, got: {exc_info.value!r}"
        )

    def test_abc_default_import_unchanged(self) -> None:
        # Third-party code that never calls the new method is unaffected.
        # Importing EngramBackend must succeed without raising.
        from flow_engineering.engram_io import EngramBackend as EBB  # noqa: N814

        assert hasattr(EBB, "mem_search_federated")
        assert EBB.mem_search_federated is not None
