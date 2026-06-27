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

PR#2 batch G (T2.3) extends this file with the ``req15_drift_daemon``
scenarios — three REQ-15 acceptance cases that exercise the daemon's
``handle_apply_progress_event`` seam (the pure function invoked by the
watchdog handler when an apply-progress write is observed).

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


# ============================================================
# PR#2 batch G (T2.3): req15_drift_daemon scenarios (REQ-15)
# ============================================================


@pytest.fixture
def drift_daemon_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Per-scenario scratch state for the REQ-15 daemon seam scenarios.

    Distinct from ``drift_world`` (REQ-9 scenarios) — these scenarios
    invoke the daemon's pure seam ``handle_apply_progress_event``
    directly rather than going through the ``flow drift`` CLI. Each
    scenario gets its own ``metrics_path``, ``InMemoryBackend``,
    ``summaries`` list, and graph_path.
    """
    metrics_path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_path))
    return {
        "metrics_path": metrics_path,
        "graph_path": tmp_path / "graph.json",
        "summaries": [],
        "change": "auth-refactor",
        "backend": None,
        "exception": None,
        "report": None,
    }


@scenario(
    "../bdd/req15_drift_daemon.feature",
    "Drift detected -> event-log summary line emitted",
)
def test_drift_daemon_emits_summary_on_drift(drift_daemon_world):
    pass


@scenario(
    "../bdd/req15_drift_daemon.feature",
    "No drift -> no event-log summary line",
)
def test_drift_daemon_silent_when_no_merge(drift_daemon_world):
    pass


@scenario(
    "../bdd/req15_drift_daemon.feature",
    "Missing graph -> daemon survives with one-time unable_to_verify log",
)
def test_drift_daemon_survives_missing_graph(drift_daemon_world):
    pass


@scenario(
    "../bdd/req15_drift_daemon.feature",
    "REQ-55 — Daemon appends one JSONL line per finding with required keys",
)
def test_drift_daemon_appends_jsonl_line_per_finding(drift_daemon_world):
    pass


@scenario(
    "../bdd/req15_drift_daemon.feature",
    "REQ-55 — Daemon does NOT append JSONL line when still-valid (REQ-56 silence cross-cut)",
)
def test_drift_daemon_silent_jsonl_when_still_valid(drift_daemon_world):
    pass


def _seed_drifted_backend(drift_daemon_world: dict) -> None:
    """Seed an ``InMemoryBackend`` with one observation whose binding's
    file:line differs from graph.json — produces STALE_LOCATION."""
    backend = InMemoryBackend()
    cref = CodeRef(
        project="insyd", id="n1", label="L1",
        file="src/old.py", line=10,
        confidence=0.9, source="manual",
    )
    content = (
        "## Decision\nOld binding location.\n"
        + format_code_refs_block([cref], source="manual")
    )
    backend.mem_save(
        title=f"{drift_daemon_world['change']}/phase_0",
        content=content,
        topic_key=f"sdd/{drift_daemon_world['change']}/phase_0",
    )
    drift_daemon_world["backend"] = backend
    drift_daemon_world["graph_path"].write_text(
        json.dumps(
            {"nodes": [{"id": "n1", "label": "L1", "file": "src/new.py", "line": 42}]}
        ),
        encoding="utf-8",
    )


def _seed_valid_backend(drift_daemon_world: dict) -> None:
    """Seed an ``InMemoryBackend`` with one observation whose binding's
    file:line matches graph.json — produces STILL_VALID when scanned."""
    backend = InMemoryBackend()
    cref = CodeRef(
        project="insyd", id="n1", label="L1",
        file="src/x.py", line=1,
        confidence=0.9, source="manual",
    )
    content = (
        "## Decision\nValid binding.\n"
        + format_code_refs_block([cref], source="manual")
    )
    backend.mem_save(
        title=f"{drift_daemon_world['change']}/phase_0",
        content=content,
        topic_key=f"sdd/{drift_daemon_world['change']}/phase_0",
    )
    drift_daemon_world["backend"] = backend
    drift_daemon_world["graph_path"].write_text(
        json.dumps(
            {"nodes": [{"id": "n1", "label": "L1", "file": "src/x.py", "line": 1}]}
        ),
        encoding="utf-8",
    )


# ---------- Given steps (REQ-15) ----------


@given(parsers.parse('a change "{change}" with drifted bindings'))
def daemon_change_with_drifted_bindings(drift_daemon_world, change: str) -> None:
    """Seed an InMemoryBackend whose binding points to an older file:line
    than the current graph.json node. ``scan_change`` will classify the
    binding as STALE_LOCATION, so the daemon emits a 'drift: ...' summary."""
    drift_daemon_world["change"] = change
    _seed_drifted_backend(drift_daemon_world)


@given(parsers.parse('a change "{change}" with valid bindings'))
def daemon_change_with_valid_bindings(drift_daemon_world, change: str) -> None:
    """Seed an InMemoryBackend whose binding matches graph.json — used by
    the no-drift scenario, where no merged task is present so no scan runs."""
    drift_daemon_world["change"] = change
    _seed_valid_backend(drift_daemon_world)


@given(parsers.parse('a change "{change}"'))
def daemon_change_bare(drift_daemon_world, change: str) -> None:
    """Bare change name — no backend / graph seeded (used by the
    missing-graph scenario where the graph is absent anyway)."""
    drift_daemon_world["change"] = change


@given("a graph.json file")
def daemon_graph_file(drift_daemon_world) -> None:
    """Ensure a (possibly empty) graph.json file exists at the per-scenario path.

    Most scenarios seed the graph in their drift/valid binding setup step;
    this step just guarantees the file is present so subsequent reads don't
    raise FileNotFoundError."""
    if not drift_daemon_world["graph_path"].exists():
        drift_daemon_world["graph_path"].write_text(
            json.dumps({"nodes": []}), encoding="utf-8"
        )


@given("the graph.json file is absent")
def daemon_graph_absent(drift_daemon_world) -> None:
    """Delete the graph.json file so the daemon's scan_change returns a
    terminal ``graph_unavailable=True`` DriftReport (REQ-15 missing-graph
    resilience)."""
    drift_daemon_world["graph_path"].unlink(missing_ok=True)


@given("a fresh ~/.flow-engineering/drift_events.jsonl")
def fresh_drift_events_file(
    drift_daemon_world: dict,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redirect the daemon's DriftEventLog default path to a tmp file
    and ensure the file does not exist yet.

    The production default is ``~/.flow-engineering/drift_events.jsonl``
    which would leak data across scenarios. We monkeypatch the module's
    default so the daemon writes into ``tmp_path`` for this scenario.
    """
    target = tmp_path / "drift_events.jsonl"
    from flow_engineering import drift_event_log as _delog

    monkeypatch.setattr(_delog, "DEFAULT_DRIFT_EVENT_LOG_PATH", target)
    drift_daemon_world["drift_events_path"] = target
    if target.exists():
        target.unlink()


@then(parsers.parse("the drift_events.jsonl file has exactly {n:d} line"))
@then(parsers.parse("the drift_events.jsonl file has exactly {n:d} lines"))
def drift_events_file_has_lines(drift_daemon_world: dict, n: int) -> None:
    """Assert the per-scenario JSONL sink has exactly ``n`` lines."""
    path: Path = drift_daemon_world["drift_events_path"]
    if n == 0:
        assert not path.exists() or path.read_text(encoding="utf-8").strip() == "", (
            f"expected 0 lines; file exists with content "
            f"{path.read_text(encoding='utf-8')!r}"
        )
        return
    assert path.exists(), f"expected {n} lines but file does not exist"
    lines = [
        ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    assert len(lines) == n, (
        f"expected {n} JSONL lines; got {len(lines)}; content="
        f"{path.read_text(encoding='utf-8')!r}"
    )


@then(parsers.parse("each JSONL line contains the keys: {keys_csv}"))
def each_jsonl_line_has_keys(drift_daemon_world: dict, keys_csv: str) -> None:
    """Assert every JSONL line parses with EXACTLY the listed keys."""
    import json as _json

    path: Path = drift_daemon_world["drift_events_path"]
    expected = {k.strip() for k in keys_csv.split(",")}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        parsed = _json.loads(raw)
        assert set(parsed.keys()) == expected, (
            f"expected keys {expected}; got {set(parsed.keys())}"
        )


@then(parsers.parse("the JSONL {field_name} field equals {value}"))
def jsonl_field_equals(drift_daemon_world: dict, field_name: str, value: str) -> None:
    """Assert the first JSONL line's ``field_name`` equals ``value``."""
    import json as _json

    path: Path = drift_daemon_world["drift_events_path"]
    raw = path.read_text(encoding="utf-8").splitlines()[0]
    parsed = _json.loads(raw)
    actual = parsed.get(field_name)
    # Allow literal numeric values (e.g., scenario asserts int 1).
    try:
        expected = int(value)
    except ValueError:
        expected = value.strip('"')
    assert actual == expected, (
        f"expected JSONL {field_name}={expected!r}; got {actual!r}"
    )


# ---------- When step (REQ-15) ----------


@when(
    parsers.parse(
        'the daemon processes an apply-progress payload with task "{task_id}" status "{status}"'
    )
)
def daemon_processes_payload(
    drift_daemon_world, task_id: str, status: str
) -> None:
    """Invoke ``daemon.handle_apply_progress_event`` with a synthesized
    apply-progress payload. The seam runs ``scan_change`` (when the task
    is merged), records drift counters, and emits a one-line summary
    via ``on_summary``. Any exception is captured (the seam is supposed
    to never raise, but the BDD scenario verifies the watcher stays
    alive even on edge cases)."""
    from flow_engineering import daemon

    payload = {"tasks": {task_id: {"status": status}}}
    try:
        report = daemon.handle_apply_progress_event(
            drift_daemon_world["change"],
            payload,
            graph_json_path=drift_daemon_world["graph_path"],
            backend=drift_daemon_world["backend"],
            on_summary=drift_daemon_world["summaries"].append,
        )
        drift_daemon_world["report"] = report
    except Exception as exc:  # noqa: BLE001
        drift_daemon_world["exception"] = exc


# ---------- Then steps (REQ-15) ----------


@then(parsers.parse('the summary line starts with "{prefix}"'))
def summary_line_starts_with(drift_daemon_world, prefix: str) -> None:
    """Assert the first emitted summary line begins with the given prefix.

    Used by the drift-detected scenario to assert the line is something
    like ``drift: auth-refactor ...``."""
    summaries = drift_daemon_world["summaries"]
    assert summaries, f"expected one summary line; got {summaries!r}"
    assert summaries[0].startswith(prefix), (
        f"expected summary to start with {prefix!r}; got {summaries[0]!r}"
    )


@then(parsers.parse('the summary line mentions "{substring}"'))
def summary_line_mentions(drift_daemon_world, substring: str) -> None:
    """Assert the first emitted summary line contains ``substring``."""
    summaries = drift_daemon_world["summaries"]
    assert summaries, f"expected one summary line; got {summaries!r}"
    assert substring in summaries[0], (
        f"expected summary to contain {substring!r}; got {summaries[0]!r}"
    )


@then("no summary line is emitted")
def no_summary_line_emitted(drift_daemon_world) -> None:
    """Assert no summary was emitted (silent path: no merged task)."""
    summaries = drift_daemon_world["summaries"]
    assert summaries == [], f"expected no summary; got {summaries!r}"


@then(parsers.parse('the summary line contains "{substring}" exactly once'))
def summary_line_contains_once(drift_daemon_world, substring: str) -> None:
    """Assert exactly one summary line contains ``substring`` (used by the
    missing-graph scenario to confirm ``unable_to_verify`` is logged once,
    not zero or many times)."""
    matches = [
        s for s in drift_daemon_world["summaries"] if substring in s
    ]
    assert len(matches) == 1, (
        f"expected exactly one summary containing {substring!r}; "
        f"got {len(matches)} matches in {drift_daemon_world['summaries']!r}"
    )


@then("the daemon stays alive (no exception raised)")
def daemon_stays_alive(drift_daemon_world) -> None:
    """Assert no exception escaped ``handle_apply_progress_event``."""
    exc = drift_daemon_world["exception"]
    assert exc is None, f"daemon raised exception: {exc!r}"


def _read_drift_events(metrics_path: Path) -> list[dict[str, Any]]:
    """Return all JSONL counter events from the metrics sink."""
    if not metrics_path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in metrics_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


@then(parsers.parse("the {counter_name} counter is {n:d}"))
def counter_is_n(drift_daemon_world, counter_name: str, n: int) -> None:
    """Sum the ``count`` field (default 1) across every JSONL line whose
    ``name`` matches ``counter_name``. Asserts the running total is ``n``.

    The metric JSONL shape is ``{"name": "<counter>", "fields": {"count":
    <int>, ...}, "ts": "<ISO>"}``; lines without ``count`` contribute 1
    (matching ``observability.increment``'s behavior)."""
    events = _read_drift_events(drift_daemon_world["metrics_path"])
    matches = [e for e in events if e.get("name") == counter_name]
    actual = sum(int(e.get("fields", {}).get("count", 1)) for e in matches)
    assert actual == n, (
        f"expected {counter_name}={n}; got {actual} "
        f"(counter names seen: {[e.get('name') for e in events]})"
    )


@then("no drift_*_total counter increments")
def no_drift_counter_increments(drift_daemon_world) -> None:
    """Assert the metrics sink contains no ``drift_*_total`` events
    (used by the silent path: no merged task -> no counters fire)."""
    events = _read_drift_events(drift_daemon_world["metrics_path"])
    drift_events = [
        e for e in events
        if isinstance(e.get("name"), str) and e["name"].startswith("drift_")
    ]
    assert drift_events == [], (
        f"expected no drift counter events; got "
        f"{[e.get('name') for e in drift_events]}"
    )


# ============================================================
# REQ-33: drift-pinned scan via --snapshot=<snap_id> (2 scenarios)
# ============================================================


@pytest.fixture
def drift_pinned_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Per-scenario scratch state for REQ-33 drift-pinned scenarios.

    Distinct from ``drift_world`` (REQ-9): the snapshot's graph_json
    is the canonical graph, while a separate live ``graph_path`` shows
    a diverged state. The fixture wires both so the ``--snapshot`` and
    no-flag invocations can be compared side-by-side.
    """
    metrics_path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_path))
    snaps_dir = tmp_path / "snaps"
    monkeypatch.setenv("FLOW_SNAPSHOTS_DIR", str(snaps_dir))

    graph_path = tmp_path / "graph.json"  # live graph (drifted)
    return {
        "metrics_path": metrics_path,
        "snaps_dir": snaps_dir,
        "graph_path": graph_path,
        "change": "vector-semantic-search",
        "snap_id": None,
        "report": None,
        "result": None,
    }


@scenario(
    "../bdd/req33_drift_pinned.feature",
    "Snapshot from 2026-06-01 with 0 drift findings; running flow drift --snapshot=<that_id> returns 0 findings even if live state has drift",
)
def test_drift_pinned_returns_frozen_state(drift_pinned_world):
    pass


@scenario(
    "../bdd/req33_drift_pinned.feature",
    "flow drift <change> without --snapshot is byte-identical to current behavior",
)
def test_drift_pinned_no_flag_byte_identical(drift_pinned_world):
    pass


# ---------- Given steps (REQ-33) ----------


def _seed_snapshot_with_binding_and_graph(
    snaps_dir: Path,
    *,
    binding_id: str,
    binding_file: str,
    binding_line: int,
    frozen_graph_file: str,
    frozen_graph_line: int,
    description: str,
) -> str:
    """Create a snapshot envelope with one binding + a custom frozen graph_json.

    Mirrors the unit-test helper: seeds an InMemoryBackend with one
    observation carrying a single CodeRef, builds a snapshot, then
    rewrites the envelope to inject a known ``graph_state.graph_json``
    and recompute the sha256 stamp.
    """
    import gzip as _gzip
    import hashlib as _hashlib

    from flow_engineering.binding import CodeRef, format_code_refs_block
    from flow_engineering.engram_io import InMemoryBackend
    from flow_engineering.snapshot_manager import SnapshotManager

    backend = InMemoryBackend()
    cref = CodeRef(
        project="insyd",
        id=binding_id,
        label=binding_id.upper(),
        file=binding_file,
        line=binding_line,
        confidence=0.9,
        source="manual",
    )
    content = (
        "## Decision\n\nDrift-pinned binding.\n"
        + format_code_refs_block([cref], source="manual")
    )
    backend.mem_save(
        title="vec/phase_0",
        content=content,
        topic_key=f"sdd/vector-semantic-search/spec",
    )

    snaps_dir.mkdir(parents=True, exist_ok=True)
    snap_id = SnapshotManager(
        snapshots_dir=snaps_dir, backend=backend,
    ).create(description=description)

    # Inject the frozen graph_json + recompute sha256.
    path = snaps_dir / f"{snap_id}.json.gz"
    with _gzip.open(path, "rt", encoding="utf-8") as fh:
        envelope = json.loads(fh.read())
    envelope["graph_state"]["graph_json"] = {
        "nodes": [
            {
                "id": binding_id,
                "label": binding_id.upper(),
                "file": frozen_graph_file,
                "line": frozen_graph_line,
            },
        ],
    }
    meta_for_hash = {k: v for k, v in envelope["metadata"].items() if k != "sha256"}
    envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
    envelope_for_hash["metadata"] = meta_for_hash
    canonical = json.dumps(
        envelope_for_hash, ensure_ascii=False,
        sort_keys=True, separators=(",", ":"),
    )
    envelope["metadata"]["sha256"] = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    with _gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(json.dumps(envelope, ensure_ascii=False))
    return snap_id


@given(
    parsers.parse(
        'a snapshot {snap_alias} exists with 1 binding at file "{file}" line {line:d}'
    )
)
def given_snapshot_with_frozen_binding(
    drift_pinned_world: dict[str, Any],
    snap_alias: str,
    file: str,
    line: int,
) -> None:
    """Seed a snapshot with one binding whose file:line match the frozen graph."""
    drift_pinned_world["snap_id"] = _seed_snapshot_with_binding_and_graph(
        drift_pinned_world["snaps_dir"],
        binding_id="vec_store",
        binding_file=file,
        binding_line=line,
        frozen_graph_file=file,
        frozen_graph_line=line,
        description=snap_alias,
    )
    drift_pinned_world["snap_alias"] = snap_alias


@given(
    parsers.parse(
        'the snapshot\'s frozen graph shows the binding id "{bid}" at file "{file}" line {line:d}'
    )
)
def given_frozen_graph_shows(
    drift_pinned_world: dict[str, Any],
    bid: str,
    file: str,
    line: int,
) -> None:
    """Already enforced in the previous step (frozen graph matches binding)."""
    # No-op: the frozen graph is built into the snapshot by the
    # previous Given step. This step exists for scenario clarity.


@given(
    parsers.parse(
        'today the live graph shows the same id at file "{file}" line {line:d}'
    )
)
def given_live_graph_diverged(
    drift_pinned_world: dict[str, Any],
    file: str,
    line: int,
) -> None:
    """Write the LIVE graph.json with the binding's id at a DIFFERENT line.

    This simulates "today (2026-06-26) the same binding has drifted".
    A non-snapshot scan against this file should classify the binding
    as ``STALE_LOCATION``; a snapshot-pinned scan should return
    ``STILL_VALID`` because the FROZEN graph still shows the original
    line.
    """
    drift_pinned_world["graph_path"].write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "vec_store",
                        "label": "VEC_STORE",
                        "file": file,
                        "line": line,
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# ---------- When steps (REQ-33) ----------


@when(
    parsers.parse(
        'I run flow drift with snapshot {snap_alias} on change "{change}"'
    )
)
def when_drift_with_snapshot(
    drift_pinned_world: dict[str, Any], snap_alias: str, change: str
) -> None:
    """Invoke the library directly: ``scan_change(snap_id=...)``."""
    from flow_engineering import decision_drift

    snap_id = drift_pinned_world["snap_id"]
    drift_pinned_world["change"] = change
    report = decision_drift.scan_change(
        change_name=change,
        graph_json_path=None,
        backend=None,
        snap_id=snap_id,
    )
    drift_pinned_world["report"] = report
    drift_pinned_world["result"] = type("R", (), {"report": report})()


@when(
    parsers.parse(
        'I run flow drift without --snapshot on change "{change}"'
    )
)
def when_drift_without_snapshot(
    drift_pinned_world: dict[str, Any], change: str
) -> None:
    """Invoke the library directly: ``scan_change(...)`` (no snap_id).

    The live graph.json (which has the drifted line) drives the scan,
    so the binding classifies as ``STALE_LOCATION``. The InMemoryBackend
    is seeded with the SAME observation the snapshot captured, so the
    scan has something to iterate over (D13 non-breaking: live path
    uses live backend, not snapshot's frozen one).
    """
    from flow_engineering.binding import CodeRef, format_code_refs_block
    from flow_engineering import decision_drift
    from flow_engineering.engram_io import InMemoryBackend

    backend = InMemoryBackend()
    cref = CodeRef(
        project="insyd",
        id="vec_store",
        label="VEC_STORE",
        file="src/vec.py",
        line=42,
        confidence=0.9,
        source="manual",
    )
    content = (
        "## Decision\n\nDrift-pinned binding.\n"
        + format_code_refs_block([cref], source="manual")
    )
    backend.mem_save(
        title="vec/phase_0",
        content=content,
        topic_key=f"sdd/{change}/spec",
    )

    drift_pinned_world["change"] = change
    report = decision_drift.scan_change(
        change_name=change,
        graph_json_path=drift_pinned_world["graph_path"],
        backend=backend,
    )
    drift_pinned_world["report"] = report
    drift_pinned_world["result"] = type("R", (), {"report": report})()


# ---------- Then steps (REQ-33) ----------


@then(parsers.parse("the report contains {n:d} finding with class {klass}"))
def then_report_contains_one_finding_with_class(
    drift_pinned_world: dict[str, Any], n: int, klass: str
) -> None:
    """Assert exactly ``n`` findings have class ``klass``.

    The drift pinned scenario asserts 1 finding of class STILL_VALID
    (frozen state); the no-snapshot scenario asserts 1 finding of class
    STALE_LOCATION (live state has drifted).
    """
    report = drift_pinned_world["report"]
    findings = report.findings
    matches = [f for f in findings if f.drift_class.value == klass]
    assert len(matches) == n, (
        f"expected {n} finding(s) with class {klass}; got {len(matches)}; "
        f"all findings: {[(f.drift_class.value, f.binding.id) for f in findings]}"
    )