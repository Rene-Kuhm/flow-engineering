"""BDD step definitions for decision-reality-drift PR#1 REQ-9.

Covers ``req9_drift_detection.feature`` — 14 scenarios exercising the six
drift classes (STILL_VALID, LABEL_DRIFT, STALE_LOCATION, STALE_ID,
OBSOLETE, CONTRADICTED) plus the terminal UNABLE_TO_VERIFY state from
REQ-14.

The step bodies invoke the ``flow drift <change>`` CLI (full pipeline,
not just the library) so the REQ-11 exit-code contract and the REQ-14
fail-open promise are exercised end-to-end. Graphify is patched at the
``flow_engineering.graphify_query.query_nodes`` level so OBSOLETE tests
do not invoke the real binary.

Test isolation:
- Each scenario gets a fresh ``tmp_path`` and a fresh ``InMemoryBackend``.
- ``FLOW_METRICS_PATH`` is pointed at a tmp file via monkeypatch so the
  7 ``drift_*_total`` counters written by ``observability.record_drift_summary``
  never bleed across scenarios.
- ``flow_engineering.cli._default_save_backend`` is monkeypatched to the
  per-scenario ``InMemoryBackend`` so the CLI sees the seeded observations.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering import graphify_query
from flow_engineering.binding import CodeRef, format_code_refs_block
from flow_engineering.cli import main as cli_main
from flow_engineering.engram_io import InMemoryBackend

runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def drift_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-9 drift scenarios."""
    metrics_path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_path))
    backend = InMemoryBackend()
    graph_path = tmp_path / "graph.json"
    monkeypatch.setattr(
        "flow_engineering.cli._default_save_backend", lambda: backend
    )

    # Inject the seeded backend into scan_change so the CLI sees our
    # observations. The CLI does not yet wire ``backend=...`` into its
    # ``scan_change`` call (an issue noted in batch E's handoff); the
    # BDD fixtures close that seam at the test boundary so end-to-end
    # drift behavior is observable without touching production code.
    from flow_engineering import decision_drift as _dd_mod

    _original_scan_change = _dd_mod.scan_change

    def _patched_scan_change(change_name, *, graph_json_path, backend=None, **kwargs):
        effective_backend = backend if backend is not None else backend_holder["b"]
        return _original_scan_change(
            change_name,
            graph_json_path=graph_json_path,
            backend=effective_backend,
            **kwargs,
        )

    backend_holder: dict[str, Any] = {"b": backend}
    monkeypatch.setattr(_dd_mod, "scan_change", _patched_scan_change)

    return {
        "metrics_path": metrics_path,
        "graph_path": graph_path,
        "backend": backend,
        "backend_holder": backend_holder,
        "change": "auth-refactor",
        "result": None,
        "report": None,
        "graph_nodes": [],
    }


# ---------- Scenario bindings ----------


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Binding resolves to same file:line with same label",
)
def test_still_valid_basic(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Binding is source-agnostic (manual vs auto_suggest)",
)
def test_still_valid_source_agnostic(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Symbol renamed but file:line preserved",
)
def test_label_drift_renamed(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Case-only label change is detected as LABEL_DRIFT",
)
def test_label_drift_case(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Symbol moved to different file",
)
def test_stale_location_file_moved(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Symbol line shifted in same file",
)
def test_stale_location_line_shifted(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Symbol id not in current graph",
)
def test_stale_id_removed(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Symbol renamed without alias",
)
def test_stale_id_renamed(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Decision without bindings + zero candidates yields OBSOLETE with flag",
)
def test_obsolete_with_flag(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Decision without bindings is SKIPPED without flag (default off)",
)
def test_obsolete_default_off(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Two observations same id with confidence_gap > 0.4 yield CONTRADICTED",
)
def test_contradicted_gap_large(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "Two observations same id with confidence_gap <= 0.4 yield no CONTRADICTED finding",
)
def test_contradicted_gap_small(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "graph.json missing yields UNABLE_TO_VERIFY, exit code 2",
)
def test_unable_to_verify_missing(drift_world):
    pass


@scenario(
    "../bdd/req9_drift_detection.feature",
    "graph.json malformed yields UNABLE_TO_VERIFY, exit code 2",
)
def test_unable_to_verify_malformed(drift_world):
    pass


# ---------- Given steps ----------


@given(parsers.parse('a change "{change}" with observations'))
def setup_change(drift_world, change: str) -> None:
    """Tag the change name; the backend was already wired by the fixture."""
    drift_world["change"] = change


@given("a graph.json file")
def setup_graph_file(drift_world) -> None:
    """Initialize an empty ``graph.json`` snapshot.

    Each scenario starts with a valid empty graph so the Background alone
    never triggers ``unable_to_verify``. UNABLE_TO_VERIFY scenarios then
    override by deleting or corrupting the file via later Given steps.
    """
    drift_world["graph_path"].write_text(
        json.dumps({"nodes": []}), encoding="utf-8"
    )


@given(parsers.parse('an observation with binding {binding_json}'))
def add_observation_with_binding(drift_world, binding_json: str) -> None:
    """Register one observation carrying one CodeRef into the in-memory backend.

    ``binding_json`` is a JSON dict with keys: ``id``, ``label``, ``file``,
    ``line``, optional ``confidence`` (default 0.9) and ``source`` (default
    "manual"). The observation is saved under a sequential topic_key
    ``sdd/<change>/phase_<n>`` so ``scan_change``'s prefix scan picks it up.
    """
    spec = json.loads(binding_json)
    cref = CodeRef(
        project="insyd",
        id=spec["id"],
        label=spec["label"],
        file=spec["file"],
        line=int(spec["line"]),
        confidence=float(spec.get("confidence", 0.9)),
        source=spec.get("source", "manual"),
    )
    content = (
        "## Decision\n\nPick a binding.\n"
        + format_code_refs_block([cref], source=cref.source)
    )
    n = len(drift_world["backend"].observations)
    drift_world["backend"].mem_save(
        title=f"{drift_world['change']}/phase_{n}",
        content=content,
        topic_key=f"sdd/{drift_world['change']}/phase_{n}",
    )


@given("an observation with empty bindings")
def add_observation_empty(drift_world) -> None:
    """Register one observation with empty nodes (source: unbound).

    Used by OBSOLETE scenarios — when ``--include-obsolete`` is set and
    graphify returns 0 candidates, ``scan_change`` emits one OBSOLETE
    finding per such observation.
    """
    content = (
        "## Decision\n\nNo binding.\n"
        + format_code_refs_block([], source="unbound")
    )
    n = len(drift_world["backend"].observations)
    drift_world["backend"].mem_save(
        title=f"{drift_world['change']}/phase_{n}",
        content=content,
        topic_key=f"sdd/{drift_world['change']}/phase_{n}",
    )


@given(parsers.parse('the graph shows node {node_json}'))
def graph_shows_node(drift_world, node_json: str) -> None:
    """Append a node to the in-memory graph.json snapshot.

    ``node_json`` is a JSON dict with keys: ``id``, ``label``, ``file``,
    ``line``. Each call appends one node; multiple calls accumulate.
    """
    spec = json.loads(node_json)
    drift_world["graph_nodes"].append(spec)
    _write_graph(drift_world)


@given("the graph is empty")
def graph_empty(drift_world) -> None:
    """Rewrite graph.json with zero nodes (any prior nodes are discarded)."""
    drift_world["graph_nodes"] = []
    _write_graph(drift_world)


@given("the graph.json file is absent")
def graph_absent(drift_world) -> None:
    """Delete graph.json so ``load_graph`` returns ``(None, None, None)``.

    Per design #123 decision 1, a missing snapshot is fail-open — the
    report carries ``graph_unavailable=True`` and the CLI exits 2.
    """
    drift_world["graph_path"].unlink(missing_ok=True)


@given("the graph.json file is malformed")
def graph_malformed(drift_world) -> None:
    """Write invalid JSON so ``load_graph``'s ``JSONDecodeError`` branch fires.

    Per design #123 decision 8, schema mismatch also yields
    ``graph_unavailable=True`` — exit 2 wins over exit 1 (REQ-11).
    """
    drift_world["graph_path"].write_text(
        "{this is not valid json", encoding="utf-8"
    )


@given(parsers.parse("graphify returns {n:d} candidates"))
def graphify_returns_n(
    drift_world, monkeypatch: pytest.MonkeyPatch, n: int
) -> None:
    """Patch ``graphify_query.query_nodes`` to return ``n`` stub candidates.

    ``decision_drift`` imports the ``graphify_query`` module by reference
    (``from flow_engineering import graphify_query``) and calls
    ``graphify_query.query_nodes(...)`` — patching the attribute on the
    module rebinds every caller in one shot.
    """
    cands = [
        CodeRef(
            project="insyd",
            id=f"stub_{i}",
            label=f"Stub{i}",
            file=f"src/stub_{i}.py",
            line=i,
            confidence=0.5,
            source="auto_suggest",
        )
        for i in range(n)
    ]
    monkeypatch.setattr(
        graphify_query, "query_nodes", lambda text, **kwargs: list(cands)
    )


def _write_graph(drift_world) -> None:
    """Persist ``drift_world['graph_nodes']`` into the graph.json snapshot."""
    payload = {"nodes": list(drift_world["graph_nodes"])}
    drift_world["graph_path"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------- When steps ----------


@when(parsers.parse('I run flow drift on change "{change}"'))
def invoke_drift(drift_world, change: str) -> None:
    """Invoke ``flow drift <change> --graph-json <tmp> --json``.

    Default-mode invocation (no extra flags). The CLI is invoked via
    ``click.testing.CliRunner`` so the exit code, stdout, and stderr are
    captured without spawning a subprocess. The JSON output is parsed
    eagerly into ``drift_world['report']`` so the Then steps can
    introspect the canonical :class:`DriftReport` shape (findings list,
    class_counts, graph_unavailable flag) without relying on textual
    table parsing.
    """
    _invoke_drift_cli(drift_world, change, extra_flags=[])


@when(parsers.parse('I run flow drift on change "{change}" with --include-obsolete'))
def invoke_drift_with_obsolete(drift_world, change: str) -> None:
    """Invoke ``flow drift <change> --graph-json <tmp> --json --include-obsolete``.

    Opt-in trigger for the expensive OBSOLETE classification (per
    design #123 decision 3, ``--include-obsolete`` defaults OFF because
    each unbound decision triggers a ``graphify_query.query_nodes``
    call). The CLI must propagate the flag to ``scan_change`` so the
    OBSOLETE findings get generated.
    """
    _invoke_drift_cli(drift_world, change, extra_flags=["--include-obsolete"])


def _invoke_drift_cli(
    drift_world: dict, change: str, *, extra_flags: list[str]
) -> None:
    """Shared CLI invocation helper for both When step variants."""
    args = [
        "drift",
        change,
        "--graph-json",
        str(drift_world["graph_path"]),
        "--json",
        *extra_flags,
    ]
    result = runner.invoke(cli_main, args)
    drift_world["result"] = result
    drift_world["report"] = None
    if result.output and result.exit_code in (0, 1, 2):
        try:
            drift_world["report"] = json.loads(result.output)
        except json.JSONDecodeError:
            drift_world["report"] = None


# ---------- Then steps ----------


@then(parsers.parse("the exit code is {code:d}"))
def exit_code_is(drift_world, code: int) -> None:
    """Assert the CLI exit code matches REQ-11 (0/1/2 contract)."""
    result = drift_world["result"]
    assert result.exit_code == code, (
        f"expected exit {code}, got {result.exit_code}; "
        f"output={result.output!r}; stderr={result.stderr!r}"
    )


@then(parsers.parse("the report contains {n:d} findings with class {klass}"))
def report_contains_n_with_class(drift_world, n: int, klass: str) -> None:
    """Count findings whose ``drift_class`` equals ``klass`` in the report.

    Reads the JSON ``findings`` list emitted by ``flow drift --json``.
    The fixture is per-scenario so the count is exact; the assertion
    message lists every observed class+id pair for fast debugging.
    """
    report = drift_world["report"]
    assert report is not None, (
        "expected JSON report from --json output; got "
        f"exit={drift_world['result'].exit_code} "
        f"output={drift_world['result'].output!r}"
    )
    findings = report.get("findings", [])
    matches = [f for f in findings if f["drift_class"] == klass]
    assert len(matches) == n, (
        f"expected {n} findings with class {klass}; got {len(matches)}; "
        f"all findings: {[(f['drift_class'], f['binding']['id']) for f in findings]}"
    )


@then("the report contains 0 findings")
def report_is_empty(drift_world) -> None:
    """Assert the JSON ``findings`` list is empty (OBSOLETE default-off)."""
    report = drift_world["report"]
    assert report is not None, "expected JSON report"
    findings = report.get("findings", [])
    assert findings == [], (
        f"expected empty findings list; got {findings}"
    )


@then(parsers.parse("both observations report class {klass}"))
def all_observations_report_class(drift_world, klass: str) -> None:
    """Assert every finding carries ``klass`` (used by STILL_VALID x2 + CONTRADICTED x2)."""
    report = drift_world["report"]
    assert report is not None, "expected JSON report"
    findings = report.get("findings", [])
    assert findings, "expected findings for both observations; got an empty report"
    classes = [f["drift_class"] for f in findings]
    assert all(c == klass for c in classes), (
        f"all findings should be class {klass}; got {classes}"
    )


@then(parsers.parse("no finding has class {klass}"))
def no_finding_has_class(drift_world, klass: str) -> None:
    """Assert no finding carries ``klass`` (used by OBSOLETE-default-off + CONTRADICTED small-gap)."""
    report = drift_world["report"]
    assert report is not None, "expected JSON report"
    findings = report.get("findings", [])
    matches = [f for f in findings if f["drift_class"] == klass]
    assert matches == [], (
        f"no findings should be class {klass}; found "
        f"{[f['binding']['id'] for f in matches]}"
    )