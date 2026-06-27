"""BDD step definitions for cross-project-federation REQ-23, REQ-24, REQ-25, REQ-26.

Covers the feature files:

- ``req23_federated_search.feature`` (5 scenarios) — REQ-23 acceptance gate
  for the federated multi-project search API on ``EngramBackend`` v1.2.
- ``req24_project_detector.feature`` (6 scenarios) — REQ-24 acceptance gate
  for ``project_detector.detect`` + ``flow projects backfill`` safety gate.
- ``req25_cli_federated.feature`` (5 scenarios) — REQ-25 acceptance gate
  for the four opt-in federated flags on the ``flow search`` CLI.
- ``req26_federated_observability.feature`` (4 scenarios) — REQ-26 acceptance
  gate for the 3 ``federated_*`` counters wired into
  ``InMemoryBackend.mem_search_federated``.

Test isolation:
- REQ-23: each scenario gets a fresh ``InMemoryBackend`` (no SQLite).
- REQ-24: scenarios 1-2 exercise ``project_detector.detect`` directly;
  scenarios 3-6 invoke the CLI through ``CliRunner`` with a monkeypatched
  ``_default_save_backend`` factory returning the fixture backend.
- REQ-25: every scenario invokes the CLI through ``CliRunner`` with a
  monkeypatched backend (mirrors the unit-test pattern from
  ``tests/unit/test_cli_federated.py``).
- REQ-26: scenarios 1-3 read the JSONL metrics file via
  ``observability.read_all`` after invoking the CLI; scenario 4 inspects
  the catalog constant directly.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering.cli import main
from flow_engineering.engram_io import EngramBackend, InMemoryBackend
from flow_engineering.project_detector import detect


runner = CliRunner()


# ---------- World fixtures ----------


@pytest.fixture
def federated_world(tmp_path) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-23 scenarios."""
    return {
        "backend": None,
        "results": None,
        "raised": None,
    }


@pytest.fixture
def req24_world(tmp_path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-24 scenarios 1-2 (detect only).

    Holds:
    - ``cwd``: the synthetic Path used by scenarios 1-2.
    - ``detected``: the string/None return value from ``detect()``.
    """
    return {
        "cwd": None,
        "detected": None,
    }


@pytest.fixture
def cli_world(tmp_path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-24 (scenarios 3-6) and REQ-25.

    One world covers BOTH REQ-24 backfill CLI scenarios AND REQ-25 federated
    CLI scenarios so a single set of shared ``Then`` steps can run against
    either family of scenarios. REQ-23 keeps its own ``federated_world``
    because it doesn't touch the CLI runner.
    """
    return {
        "backend": InMemoryBackend(),
        "exit_code": None,
        "output": None,
        "stdout": None,
        "payload": None,
    }


# ---------- REQ-23 scenario bindings ----------


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


# ---------- REQ-24 scenario bindings ----------


@scenario(
    "../bdd/req24_project_detector.feature",
    "detect returns the project name when cwd is under dev/proyects",
)
def test_req24_detect_returns_project_name(req24_world):
    pass


@scenario(
    "../bdd/req24_project_detector.feature",
    "detect returns None when cwd is not under a projects dir",
)
def test_req24_detect_returns_none_for_unknown(req24_world):
    pass


@scenario(
    "../bdd/req24_project_detector.feature",
    "flow projects backfill with no flags defaults to dry-run",
)
def test_req24_backfill_default_is_dry_run(cli_world):
    pass


@scenario(
    "../bdd/req24_project_detector.feature",
    "flow projects backfill --confirm --project=<key> writes tags",
)
def test_req24_backfill_confirm_project_writes(cli_world):
    pass


@scenario(
    "../bdd/req24_project_detector.feature",
    "flow projects backfill --confirm without --project refuses with non-zero exit",
)
def test_req24_backfill_confirm_no_project_refuses(cli_world):
    pass


@scenario(
    "../bdd/req24_project_detector.feature",
    "flow projects backfill --dry-run emits a JSON report to stdout",
)
def test_req24_backfill_dry_run_emits_json(cli_world):
    pass


# ---------- REQ-25 scenario bindings ----------


@scenario(
    "../bdd/req25_cli_federated.feature",
    "flow search without --federated is byte-identical to pre-change behaviour",
)
def test_req25_no_federated_byte_identical(cli_world):
    pass


@scenario(
    "../bdd/req25_cli_federated.feature",
    "flow search --federated returns results from all projects",
)
def test_req25_federated_returns_all_projects(cli_world):
    pass


@scenario(
    "../bdd/req25_cli_federated.feature",
    "flow search --federated --projects=<csv> restricts to the named projects",
)
def test_req25_federated_projects_csv_restricts(cli_world):
    pass


@scenario(
    "../bdd/req25_cli_federated.feature",
    "flow search --federated --since=<iso> excludes observations created before that date",
)
def test_req25_federated_since_excludes_older(cli_world):
    pass


@scenario(
    "../bdd/req25_cli_federated.feature",
    "flow search --federated --type=<csv> includes only matching type observations",
)
def test_req25_federated_type_restricts(cli_world):
    pass


# ---------- Given steps (REQ-23) ----------


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


# ---------- When steps (REQ-23) ----------


@when('I call mem_search_federated("drift") with all 3 projects')
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


# ---------- Then steps (REQ-23) ----------


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


# ---------- Given steps (REQ-24) ----------


@given(parsers.parse('a project_detector with cwd "{cwd}"'))
def set_req24_cwd(req24_world: dict[str, Any], cwd: str) -> None:
    req24_world["cwd"] = Path(cwd)


def _seed_untagged(backend: InMemoryBackend) -> int:
    """Seed one observation WITHOUT a project tag (REQ-24 backfill fixture).

    Overwrites the auto-default ``"insyd"`` tag with ``None`` to model the
    "historical observation that lost its tag" case the backfill exists
    to repair. Returns the observation id.
    """
    obs = backend.mem_save(
        title="legacy drift entry",
        content="drift detection strategy",
        topic_key="sdd/x/spec",
    )
    obs["project"] = None
    return int(obs["id"])


@given("an InMemoryBackend with 1 untagged observation")
def seed_one_untagged(cli_world: dict[str, Any]) -> None:
    _seed_untagged(cli_world["backend"])


# ---------- When steps (REQ-24) ----------


@when("I call detect() with that cwd")
def call_detect_with_cwd(req24_world: dict[str, Any]) -> None:
    req24_world["detected"] = detect(req24_world["cwd"])


def _run_backfill(cli_world: dict[str, Any], cli_args: list[str]) -> None:
    """Invoke ``flow projects backfill <cli_args>`` with a seeded backend."""
    from flow_engineering import cli as cli_mod

    backend = cli_world["backend"]
    cli_mod._default_save_backend = lambda: backend  # type: ignore[assignment]
    result = runner.invoke(main, ["projects", "backfill", *cli_args])
    cli_world["exit_code"] = result.exit_code
    cli_world["output"] = result.output
    cli_world["stdout"] = (
        result.output if result.stdout is None else f"{result.stdout}"
    )
    # If the CLI streams to stderr, the combined ``output`` still has it;
    # pytest's CliRunner joins them. We try to parse JSON from stdout first.
    if result.stdout:
        try:
            cli_world["stdout"] = result.stdout
        except Exception:
            pass


@when(parsers.parse('I run the CLI "flow projects backfill {flags}"'))
def run_backfill_cli(cli_world: dict[str, Any], flags: str) -> None:
    """Invoke ``flow projects backfill <flags>``. ``flags`` is one or more CLI args.

    The bare ``flow projects backfill`` (no flags) variant is handled by
    :func:`run_backfill_no_flags` because ``{flags:w}`` requires a non-empty
    capture.
    """
    tokens = flags.split()
    _run_backfill(cli_world, tokens)


@when("I run the flow projects backfill CLI with no flags")
def run_backfill_no_flags(cli_world: dict[str, Any]) -> None:
    """Invoke ``flow projects backfill`` (default dry-run)."""
    _run_backfill(cli_world, [])


# ---------- Then steps (REQ-24) ----------


@then(parsers.parse('the returned project is "{expected}"'))
def then_detected_is(req24_world: dict[str, Any], expected: str) -> None:
    assert req24_world["detected"] == expected, (
        f"Expected detect() == {expected!r}, got {req24_world['detected']!r}"
    )


@then("the returned project is None")
def then_detected_is_none(req24_world: dict[str, Any]) -> None:
    assert req24_world["detected"] is None, (
        f"Expected detect() == None, got {req24_world['detected']!r}"
    )


@then("the exit code is 0")
def then_exit_code_zero(cli_world: dict[str, Any]) -> None:
    assert cli_world["exit_code"] == 0, (
        f"Expected exit 0, got {cli_world['exit_code']}; output={cli_world['output']!r}"
    )


@then("the exit code is non-zero")
def then_exit_code_nonzero(cli_world: dict[str, Any]) -> None:
    assert cli_world["exit_code"] != 0, (
        f"Expected non-zero exit, got 0; output={cli_world['output']!r}"
    )


@then("the observation is still untagged")
def then_observation_still_untagged(cli_world: dict[str, Any]) -> None:
    backend = cli_world["backend"]
    untagged = [
        obs for obs in backend.observations.values() if obs.get("project") in (None, "")
    ]
    assert untagged, (
        f"Expected at least one untagged observation; backend={backend.observations!r}"
    )


@then(parsers.parse('the observation is tagged with "{project}"'))
def then_observation_tagged_with(cli_world: dict[str, Any], project: str) -> None:
    backend = cli_world["backend"]
    tagged = [
        obs for obs in backend.observations.values() if obs.get("project") == project
    ]
    assert tagged, (
        f"Expected at least one observation tagged {project!r}; "
        f"observations={[(o['id'], o.get('project')) for o in backend.observations.values()]!r}"
    )


@then("stdout is valid JSON")
def then_stdout_is_valid_json(cli_world: dict[str, Any]) -> None:
    raw = cli_world["stdout"] or ""
    parsed = json.loads(raw)
    assert isinstance(parsed, (dict, list)), (
        f"Expected JSON object or array, got {type(parsed).__name__}: {parsed!r}"
    )


@then("the JSON report mentions the observation id")
def then_json_mentions_obs_id(cli_world: dict[str, Any]) -> None:
    raw = cli_world["stdout"] or ""
    parsed = json.loads(raw)
    # Either a list of dicts with observation_id keys, or a dict with a
    # ``changes`` list. The new T1.12 contract is the dict shape; the BDD
    # spec lists both forms across the scenario set. Accept either.
    if isinstance(parsed, list):
        ids = [int(item.get("observation_id")) for item in parsed if isinstance(item, dict)]
    else:
        changes = parsed.get("changes") if isinstance(parsed, dict) else None
        ids = [int(item.get("observation_id")) for item in (changes or []) if isinstance(item, dict)]
    assert ids, f"Expected at least one observation_id in JSON report, got {parsed!r}"


# ---------- Given steps (REQ-25) ----------


def _seed_obs(
    backend: InMemoryBackend,
    *,
    obs_id: int,
    project: str | None,
    type: str = "manual",
    created_at: str = "2026-06-15 10:00:00",
    title: str = "",
    content: str = "drift detection strategy",
) -> None:
    obs = {
        "id": obs_id,
        "title": title or f"obs {obs_id}",
        "content": content,
        "topic_key": "sdd/test/phase",
        "type": type,
        "scope": "project",
        "project": project,
        "created_at": created_at,
        "updated_at": created_at,
    }
    backend.observations[obs_id] = obs
    backend.next_id = max(backend.next_id, obs_id + 1)


@given("an InMemoryBackend with drift observations in 2 projects")
def seed_two_projects(cli_world: dict[str, Any]) -> None:
    backend = cli_world["backend"]
    _seed_obs(backend, obs_id=1, project="flow-engineering", title="fe drift")
    _seed_obs(backend, obs_id=2, project="mockup-2-blog", title="m2b drift")
    _install_backend(cli_world, backend)


@given("an InMemoryBackend with drift observations in 3 projects")
def seed_three_projects(cli_world: dict[str, Any]) -> None:
    backend = cli_world["backend"]
    _seed_obs(backend, obs_id=1, project="flow-engineering", title="fe drift")
    _seed_obs(backend, obs_id=2, project="mockup-2-blog", title="m2b drift")
    _seed_obs(
        backend,
        obs_id=3,
        project="tecnodespegue-landing",
        title="tdl drift",
    )
    _install_backend(cli_world, backend)


def _install_backend(cli_world: dict[str, Any], backend: InMemoryBackend) -> None:
    from flow_engineering import cli as cli_mod

    cli_mod._default_save_backend = lambda: backend  # type: ignore[assignment]


@given("an InMemoryBackend with drift observations on 2026-05-15 and 2026-06-15")
def seed_two_dates(cli_world: dict[str, Any]) -> None:
    backend = cli_world["backend"]
    _seed_obs(
        backend,
        obs_id=1,
        project="flow-engineering",
        title="old drift 2026-05-15",
        created_at="2026-05-15 10:00:00",
    )
    _seed_obs(
        backend,
        obs_id=2,
        project="flow-engineering",
        title="recent drift 2026-06-15",
        created_at="2026-06-15 10:00:00",
    )
    _install_backend(cli_world, backend)


@given("an InMemoryBackend with drift observations of mixed types")
def seed_mixed_types(cli_world: dict[str, Any]) -> None:
    backend = cli_world["backend"]
    _seed_obs(
        backend,
        obs_id=1,
        project="flow-engineering",
        type="decision",
        title="drift decision",
    )
    _seed_obs(
        backend,
        obs_id=2,
        project="flow-engineering",
        type="bugfix",
        title="drift bugfix",
    )
    _seed_obs(
        backend,
        obs_id=3,
        project="flow-engineering",
        type="pattern",
        title="drift pattern",
    )
    _install_backend(cli_world, backend)


# ---------- When steps (REQ-25) ----------


@when(parsers.parse('I run the CLI "flow {args}"'))
def run_search_cli(cli_world: dict[str, Any], args: str) -> None:
    from flow_engineering import cli as cli_mod

    # Default backend factory already monkeypatched by the GIVEN step.
    # We re-patch in case the user constructed the world out-of-order.
    cli_mod._default_save_backend = lambda: cli_world["backend"]  # type: ignore[assignment]
    # ``args`` is the entire CLI tail after ``flow `` (e.g. ``search drift``
    # or ``projects backfill --confirm``). Split on whitespace for Click.
    tokens = args.split()
    result = runner.invoke(main, tokens)
    cli_world["exit_code"] = result.exit_code
    cli_world["output"] = result.output
    cli_world["stdout"] = result.stdout or ""
    if result.stdout:
        try:
            cli_world["payload"] = json.loads(result.stdout)
        except Exception:
            cli_world["payload"] = None


# ---------- Then steps (REQ-25) ----------





@then(parsers.parse("the JSON has results from {n:d} distinct projects"))
def then_json_has_n_distinct_projects(cli_world: dict[str, Any], n: int) -> None:
    payload = cli_world["payload"]
    assert payload is not None, f"Expected JSON payload; stdout={cli_world['stdout']!r}"
    results = payload.get("results", [])
    projects = {r.get("project") for r in results}
    assert len(projects) == n, (
        f"Expected {n} distinct projects, got {len(projects)} ({projects!r})"
    )


@then(parsers.parse('every result has project "{a}" or "{b}"'))
def then_every_result_in_set(cli_world: dict[str, Any], a: str, b: str) -> None:
    payload = cli_world["payload"]
    assert payload is not None, f"Expected JSON payload; stdout={cli_world['stdout']!r}"
    allowed = {a, b}
    for r in payload.get("results", []):
        assert r.get("project") in allowed, (
            f"Expected project in {allowed}, got {r.get('project')!r} in {r!r}"
        )


@then(parsers.parse('no result has project "{forbidden}"'))
def then_no_result_has_project(cli_world: dict[str, Any], forbidden: str) -> None:
    payload = cli_world["payload"]
    assert payload is not None, f"Expected JSON payload; stdout={cli_world['stdout']!r}"
    for r in payload.get("results", []):
        assert r.get("project") != forbidden, (
            f"Expected no result with project {forbidden!r}, got {r!r}"
        )


@then(parsers.parse('the result titles include "{title}"'))
def then_titles_include_title(cli_world: dict[str, Any], title: str) -> None:
    payload = cli_world["payload"]
    assert payload is not None, f"Expected JSON payload; stdout={cli_world['stdout']!r}"
    titles = [r.get("title", "") for r in payload.get("results", [])]
    assert any(title in t for t in titles), (
        f"Expected title containing {title!r}; got titles={titles!r}"
    )


@then(parsers.parse('the result titles do NOT include "{title}"'))
def then_titles_exclude_title(cli_world: dict[str, Any], title: str) -> None:
    payload = cli_world["payload"]
    assert payload is not None, f"Expected JSON payload; stdout={cli_world['stdout']!r}"
    titles = [r.get("title", "") for r in payload.get("results", [])]
    assert not any(title in t for t in titles), (
        f"Expected NO title containing {title!r}; got titles={titles!r}"
    )


@then(parsers.parse("the search returns {n:d} result"))
@then(parsers.parse("the search returns {n:d} results"))
def then_search_returns_n(cli_world: dict[str, Any], n: int) -> None:
    """Count rows in the JSON payload (non-federated and --federated --json)."""
    payload = cli_world["payload"]
    if payload is None:
        # Fall back to counting ``obs N`` markers in the text table.
        count = (cli_world["stdout"] or "").count("obs ")
        assert count == n, (
            f"Expected {n} results; got {count} 'obs ' markers in stdout={cli_world['stdout']!r}"
        )
        return
    results = payload.get("results", [])
    assert len(results) == n, (
        f"Expected {n} results, got {len(results)}: {[r.get('title') for r in results]!r}"
    )


# ---------- REQ-26 scenario bindings ----------


@scenario(
    "../bdd/req26_federated_observability.feature",
    "federated_search_invoked_total increments per federated call",
)
def test_req26_invoked_increments(cli_world):
    pass


@scenario(
    "../bdd/req26_federated_observability.feature",
    "federated_search_projects_queried records the per-call count bucket",
)
def test_req26_projects_queried_bucket(cli_world):
    pass


@scenario(
    "../bdd/req26_federated_observability.feature",
    "federated_search_results_returned_total increments by sum of result counts",
)
def test_req26_results_returned_sum(cli_world):
    pass


@scenario(
    "../bdd/req26_federated_observability.feature",
    "All 3 federated counters appear in the FEDERATED_COUNTER_NAMES catalog",
)
def test_req26_catalog_has_three(catalog_world):
    pass


# ---------- REQ-26 world + given/when/then steps ----------


@pytest.fixture
def catalog_world() -> dict[str, Any]:
    """Per-scenario scratch state for REQ-26 catalog-inspection scenario."""
    return {}


@pytest.fixture
def metrics_path(
    tmp_path, monkeypatch: pytest.MonkeyPatch, cli_world: dict[str, Any]
) -> Path:
    """Point ``FLOW_METRICS_PATH`` at a tmp JSONL file so tests do not pollute ~/.flow."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    cli_world["metrics_path"] = path
    return path


@given("the metrics path points at a tmp file")
def given_metrics_path(
    cli_world: dict[str, Any], tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    cli_world["metrics_path"] = path


@given("the observability module exposes FEDERATED_COUNTER_NAMES")
def given_catalog_exposed(catalog_world: dict[str, Any]) -> None:
    from flow_engineering import observability

    catalog_world["observability"] = observability


def _read_metrics_events(metrics_path: Path) -> list[dict[str, Any]]:
    """Parse the JSONL metrics file into a list of event dicts (defensive)."""
    if not metrics_path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in metrics_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


@then(parsers.parse("the metrics file contains a federated_search_invoked_total event with trigger={trigger}"))
def then_invoked_event_with_trigger(cli_world: dict[str, Any], trigger: str) -> None:
    events = _read_metrics_events(cli_world["metrics_path"])
    matches = [
        e for e in events
        if e.get("name") == "federated_search_invoked_total"
        and e.get("fields", {}).get("trigger") == trigger
    ]
    assert matches, (
        f"Expected federated_search_invoked_total event with trigger={trigger!r}; "
        f"got events={events!r}"
    )


@then(parsers.parse("the federated_search_invoked_total count is {n:d}"))
def then_invoked_count_is(cli_world: dict[str, Any], n: int) -> None:
    events = _read_metrics_events(cli_world["metrics_path"])
    total = sum(
        int(e.get("fields", {}).get("count", 0))
        for e in events
        if e.get("name") == "federated_search_invoked_total"
    )
    assert total == n, f"Expected invoked total {n}, got {total}; events={events!r}"


@then(parsers.parse("the metrics file contains a federated_search_projects_queried event with count={n:d}"))
def then_projects_queried_event_count(cli_world: dict[str, Any], n: int) -> None:
    events = _read_metrics_events(cli_world["metrics_path"])
    matches = [
        e for e in events
        if e.get("name") == "federated_search_projects_queried"
        and int(e.get("fields", {}).get("count", 0)) == n
    ]
    assert matches, (
        f"Expected federated_search_projects_queried event with count={n}; "
        f"got events={events!r}"
    )


@then(parsers.parse("the federated_search_results_returned_total count is {n:d}"))
def then_results_returned_total_is(cli_world: dict[str, Any], n: int) -> None:
    events = _read_metrics_events(cli_world["metrics_path"])
    total = sum(
        int(e.get("fields", {}).get("count", 0))
        for e in events
        if e.get("name") == "federated_search_results_returned_total"
    )
    assert total == n, f"Expected results_returned total {n}, got {total}; events={events!r}"


@then("the catalog contains exactly 3 entries")
def then_catalog_length_is_three(catalog_world: dict[str, Any]) -> None:
    observability = catalog_world["observability"]
    names = observability.FEDERATED_COUNTER_NAMES
    assert isinstance(names, list)
    assert len(names) == 3, f"Expected 3 catalog names, got {len(names)}: {names!r}"


@then(parsers.parse('the catalog names are "{a}", "{b}", "{c}"'))
def then_catalog_names_are(
    catalog_world: dict[str, Any], a: str, b: str, c: str
) -> None:
    observability = catalog_world["observability"]
    names = observability.FEDERATED_COUNTER_NAMES
    expected = [a, b, c]
    assert sorted(names) == sorted(expected), (
        f"Expected catalog names {expected}, got {names!r}"
    )
