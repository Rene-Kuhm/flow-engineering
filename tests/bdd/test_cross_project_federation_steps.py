"""BDD step definitions for cross-project-federation REQ-23.

Covers ``req23_federated_search.feature`` (5 scenarios) — the BDD acceptance
gate for the federated multi-project search API on ``EngramBackend`` v1.2.

REQ-23 scenarios exercise ``InMemoryBackend.mem_search_federated`` with
three orthogonal filters (projects, since, type_filter) plus the ABC default
behaviour for third-party subclasses:

- Scenario 1: federation across 3 projects preserves the ``project`` field
  on every returned row.
- Scenario 2: ``projects=["flow-engineering"]`` restricts the result set
  (no leakage from other projects).
- Scenario 3: ``since="2026-06-01"`` uses lexicographic ``>=`` against the
  ``YYYY-MM-DD HH:MM:SS`` TEXT format.
- Scenario 4: ``type_filter=["decision", "bugfix"]`` matches by exact type.
- Scenario 5: ABC default raises ``NotImplementedError`` when not overridden.

Test isolation:
- Each scenario gets a fresh ``InMemoryBackend`` (no SQLite, no real DB).
- Observations are seeded with explicit ``project`` and ``created_at`` so
  filtering assertions are deterministic.
- The ABC-default scenario uses a local ``PlainBackend`` subclass that does
  NOT override ``mem_search_federated``.

Steps are reusable: batches B and C will add REQ-24 / REQ-25 step glue to
this file under their own prefixes (the fixture and helper structure here
is the common pattern).
"""
from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering.engram_io import EngramBackend, InMemoryBackend


# ---------- World fixture ----------


@pytest.fixture
def federated_world(tmp_path) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-23 scenarios."""
    return {
        "backend": None,
        "results": None,
        "raised": None,
    }


# ---------- Scenario bindings ----------


@scenario(
    "../bdd/req23_federated_search.feature",
    "Federated search across 3 projects returns results from each with project field per row",
)
def test_req23_three_projects_with_project_field(federated_world):
    pass


@scenario(
    "../bdd/req23_federated_search.feature",
    'projects=["flow-engineering"] restricts the result set to a single project',
)
def test_req23_projects_filter_restricts(federated_world):
    pass


@scenario(
    "../bdd/req23_federated_search.feature",
    'since="2026-06-01" excludes observations created before that date',
)
def test_req23_since_filter_excludes_older(federated_world):
    pass


@scenario(
    "../bdd/req23_federated_search.feature",
    'type_filter=["decision", "bugfix"] includes only matching types',
)
def test_req23_type_filter_includes_only_listed(federated_world):
    pass


@scenario(
    "../bdd/req23_federated_search.feature",
    "ABC default raises NotImplementedError when not overridden",
)
def test_req23_abc_default_raises(federated_world):
    pass


# ---------- Given steps ----------


@given("an InMemoryBackend seeded with 3 observations across 3 distinct projects")
def seed_three_projects(federated_world):
    backend = InMemoryBackend()
    for project in ("flow-engineering", "mockup-2-blog", "tecnodespegue-landing"):
        obs = backend.mem_save(
            title=f"{project} drift entry",
            content=f"drift detection strategy in {project}",
            topic_key="sdd/x/spec",
        )
        obs["project"] = project
        obs["created_at"] = "2026-06-15 12:00:00"
    federated_world["backend"] = backend


@given(
    "an InMemoryBackend seeded with 5 observations in flow-engineering and 3 in mockup-2-blog"
)
def seed_five_three_across_two_projects(federated_world):
    backend = InMemoryBackend()
    for i in range(5):
        obs = backend.mem_save(
            title=f"fe drift {i}",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
        )
        obs["project"] = "flow-engineering"
        obs["created_at"] = "2026-06-15 12:00:00"
    for i in range(3):
        obs = backend.mem_save(
            title=f"m2b drift {i}",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
        )
        obs["project"] = "mockup-2-blog"
        obs["created_at"] = "2026-06-15 12:00:00"
    federated_world["backend"] = backend


@given(
    "an InMemoryBackend with observations on 2026-05-15 and 2026-06-15 in flow-engineering"
)
def seed_two_obs_on_different_dates(federated_world):
    backend = InMemoryBackend()
    older = backend.mem_save(
        title="older drift",
        content="drift detection strategy",
        topic_key="sdd/x/spec",
    )
    older["project"] = "flow-engineering"
    older["created_at"] = "2026-05-15 10:00:00"
    newer = backend.mem_save(
        title="newer drift",
        content="drift detection strategy",
        topic_key="sdd/x/spec",
    )
    newer["project"] = "flow-engineering"
    newer["created_at"] = "2026-06-15 10:00:00"
    federated_world["backend"] = backend


@given(
    "an InMemoryBackend with observations of types decision, bugfix, and pattern in flow-engineering"
)
def seed_three_obs_with_varied_types(federated_world):
    backend = InMemoryBackend()
    for type_name in ("decision", "bugfix", "pattern"):
        obs = backend.mem_save(
            title=f"{type_name} drift",
            content="drift detection strategy",
            topic_key="sdd/x/spec",
            type=type_name,
        )
        obs["project"] = "flow-engineering"
        obs["created_at"] = "2026-06-15 10:00:00"
    federated_world["backend"] = backend


@given("a custom EngramBackend that does not override mem_search_federated")
def build_plain_backend(federated_world):
    class PlainBackend(EngramBackend):
        def mem_save(self, title, content, topic_key, type="manual", scope="project"):
            return {"id": 1, "title": title, "content": content}

        def mem_search(self, query, topic_key=None, limit=10, scope="project"):
            return []

        def mem_get_observation(self, id):
            return {"id": id}

    federated_world["backend"] = PlainBackend()


# ---------- When steps ----------


@when("I call mem_search_federated(\"drift\") with all 3 projects")
def call_federated_all_three(federated_world):
    try:
        federated_world["results"] = federated_world["backend"].mem_search_federated(
            "drift",
            projects=[
                "flow-engineering",
                "mockup-2-blog",
                "tecnodespegue-landing",
            ],
            limit=10,
        )
    except Exception as exc:
        federated_world["raised"] = exc


@when(parsers.parse('I call mem_search_federated("{query}", projects=["flow-engineering"])'))
def call_federated_single_project(federated_world, query: str):
    try:
        federated_world["results"] = federated_world["backend"].mem_search_federated(
            query, projects=["flow-engineering"]
        )
    except Exception as exc:
        federated_world["raised"] = exc


@when(
    parsers.parse(
        'I call mem_search_federated("{query}", projects=["flow-engineering"], since="{since}")'
    )
)
def call_federated_with_since(federated_world, query: str, since: str):
    try:
        federated_world["results"] = federated_world["backend"].mem_search_federated(
            query, projects=["flow-engineering"], since=since
        )
    except Exception as exc:
        federated_world["raised"] = exc


@when(
    parsers.parse(
        'I call mem_search_federated("{query}", projects=["flow-engineering"], '
        'type_filter=["decision", "bugfix"])'
    )
)
def call_federated_with_type_filter(federated_world, query: str):
    try:
        federated_world["results"] = federated_world["backend"].mem_search_federated(
            query,
            projects=["flow-engineering"],
            type_filter=["decision", "bugfix"],
        )
    except Exception as exc:
        federated_world["raised"] = exc


@when(parsers.parse('I call mem_search_federated("{query}") on the custom backend'))
def call_federated_on_plain_backend(federated_world, query: str):
    try:
        federated_world["results"] = federated_world["backend"].mem_search_federated(query)
    except Exception as exc:
        federated_world["raised"] = exc


# ---------- Then steps ----------


@then(parsers.parse("{n:d} results are returned"))
def n_results_returned(federated_world, n: int):
    assert federated_world["raised"] is None, (
        f"Expected success, got {type(federated_world['raised']).__name__}: "
        f"{federated_world['raised']}"
    )
    results = federated_world["results"]
    assert len(results) == n, (
        f"Expected {n} results, got {len(results)}: {results!r}"
    )


@then("each result has a non-null project field matching one of the queried projects")
def each_result_has_queried_project(federated_world):
    allowed = {
        "flow-engineering",
        "mockup-2-blog",
        "tecnodespegue-landing",
    }
    for r in federated_world["results"]:
        assert r.get("project") is not None, (
            f"Missing project field in row: {r!r}"
        )
        assert r["project"] in allowed, (
            f"Unexpected project {r['project']!r} in row: {r!r}"
        )


@then(parsers.parse('every result has project == "{expected}"'))
def every_result_has_project(federated_world, expected: str):
    for r in federated_world["results"]:
        assert r.get("project") == expected, (
            f"Expected project == {expected!r}, got {r.get('project')!r} in row {r!r}"
        )


@then("only the 2026-06-15 observation is returned")
def only_newer_observation_returned(federated_world):
    results = federated_world["results"]
    assert len(results) == 1, (
        f"Expected 1 result (only 2026-06-15), got {len(results)}: {results!r}"
    )
    assert results[0]["created_at"] == "2026-06-15 10:00:00", (
        f"Expected created_at == 2026-06-15 10:00:00, got {results[0]['created_at']!r}"
    )


@then("every result has type decision or bugfix")
def every_result_type_decision_or_bugfix(federated_world):
    allowed = {"decision", "bugfix"}
    for r in federated_world["results"]:
        assert r.get("type") in allowed, (
            f"Expected type in {allowed}, got {r.get('type')!r} in row {r!r}"
        )


@then("NotImplementedError is raised")
def not_implemented_error_raised(federated_world):
    raised = federated_world["raised"]
    assert raised is not None, "Expected NotImplementedError, got None"
    assert isinstance(raised, NotImplementedError), (
        f"Expected NotImplementedError, got {type(raised).__name__}: {raised!r}"
    )


@then(parsers.parse('the error message includes "{needle}"'))
def error_message_includes(federated_world, needle: str):
    assert needle in str(federated_world["raised"]), (
        f"Expected '{needle}' in error message, got: {federated_world['raised']!r}"
    )