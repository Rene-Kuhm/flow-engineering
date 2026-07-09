"""BDD step definitions for ``req_where.feature`` (REQ-V1.0.1 + REQ-V1.0.3).

T2.5 owns the 2 cross-cutting scenarios for the ``flow where "<query>"``
subcommand. Mirrors the BDD-first test pattern used by
``tests/bdd/test_graph_snapshots_steps.py`` + ``test_vector_search_steps.py``.

Each scenario runs the CLI via :class:`click.testing.CliRunner` so the test
never depends on a real `flow` install (matches the precedent in
``test_cli_inspect.py``).

Test isolation:
    The ``where_world`` fixture monkeypatches
    ``flow_engineering.where.DEFAULT_GRAPH_PATH`` per scenario so we never
    read the user's real ``graphify-out/graph.json`` snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenario, then, when

from flow_engineering import where
from flow_engineering.cli import main

runner = CliRunner()


# ---------- World fixture + helpers ----------


@pytest.fixture
def where_world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Per-scenario scratch state for the BDD ``flow where`` scenarios."""
    # Build a minimal fixture tree rooted at tmp_path. Code hits come from
    # `src/x.py`; SDD archive hits from `openspec/changes/archive/x/spec.md`.
    src = tmp_path / "src"
    src.mkdir()
    (src / "x.py").write_text("def make_jwt():\n    return 'token'\n", encoding="utf-8")
    archive = tmp_path / "openspec" / "changes" / "archive" / "x"
    archive.mkdir(parents=True)
    (archive / "spec.md").write_text("the jwt validator pattern handles X.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return {
        "tmp_path": tmp_path,
        "result": None,
        "output": "",
    }


def _set_graph_json(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """Override :data:`DEFAULT_GRAPH_PATH` so ``grep_graphify`` reads the fixture."""
    monkeypatch.setattr(where, "DEFAULT_GRAPH_PATH", path)


# ---------- Scenario bindings ----------


@scenario(
    "req_where.feature", "Graphify index absent renders the deterministic unavailable message"
)
def test_graphify_absent_renders_unavailable(where_world: dict[str, Any]) -> None:
    pass


@scenario("req_where.feature", "Graphify index present renders scored hits")
def test_graphify_present_renders_scored_hits(where_world: dict[str, Any]) -> None:
    pass


# ---------- Given steps ----------


@given("a fresh repo with no graphify-out/graph.json")
def given_no_graph_json(where_world: dict[str, Any]) -> None:
    """Default-state: graph.json path points at a non-existent fixture file."""
    _set_graph_json(_monkeypatch_for(where_world), where_world["tmp_path"] / "graph.json")


@given("a fresh repo with a fixture graph.json matching the query")
def given_graph_json_fixture(where_world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Write a minimal graph.json with one node that overlaps the query ``jwt``."""
    graph = where_world["tmp_path"] / "graph.json"
    graph.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "src-auth-jwt",
                        "label": "auth.jwt",
                        "source_file": "src/x.py",
                        "source_location": "1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _set_graph_json(monkeypatch, graph)


# ---------- When steps ----------


@when('I run flow where with the query "jwt"')
def when_run_flow_where(where_world: dict[str, Any]) -> None:
    """Invoke ``flow where "jwt"`` via :class:`CliRunner` and capture output."""
    result = runner.invoke(main, ["where", "jwt"])
    where_world["result"] = result
    where_world["output"] = result.output


# ---------- Then steps ----------


@then('the GRAPH section contains the literal "unavailable / no graph index found"')
def then_graph_section_unavailable(where_world: dict[str, Any]) -> None:
    """Assert the deterministic fail-open token appears exactly once."""
    out = where_world["output"]
    assert out.count("unavailable / no graph index found") == 1


@then("the GRAPH section lists at least one entry for the matching node")
def then_graph_section_lists_match(where_world: dict[str, Any]) -> None:
    """With a matching node, GRAPH section shows the node label / file."""
    out = where_world["output"]
    assert "GRAPH" in out
    assert "src/x.py" in out
    assert "auth.jwt" in out
    assert "unavailable / no graph index found" not in out


@then("the section order is CODE then TESTS then SDD then GRAPH")
def then_section_order(where_world: dict[str, Any]) -> None:
    """Section headers appear in the documented order (REQs D4)."""
    out = where_world["output"]
    code_pos = out.index("CODE")
    tests_pos = out.index("TESTS")
    sdd_pos = out.index("SDD")
    graph_pos = out.index("GRAPH")
    assert code_pos < tests_pos < sdd_pos < graph_pos


# ---------- Helper (monkeypatch pass-through) ----------


def _monkeypatch_for(where_world: dict[str, Any]) -> pytest.MonkeyPatch:
    """Return the active ``monkeypatch`` fixture for the current scenario.

    pytest-bdd does not auto-inject the fixture into ``given``/``when``/``then``
    functions unless declared as a parameter. We stash the fixture in
    ``where_world`` at scenario setup time so the ``given`` step can grab it
    without an additional dependency on pytest-bdd's parameter parsing.
    """
    mp = where_world.get("_monkeypatch")
    if mp is None:
        raise RuntimeError("monkeypatch was never attached to where_world; check conftest")
    return mp


@pytest.fixture(autouse=True)
def _attach_monkeypatch(where_world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Attach the pytest ``monkeypatch`` fixture to ``where_world`` for step access."""
    where_world["_monkeypatch"] = monkeypatch
