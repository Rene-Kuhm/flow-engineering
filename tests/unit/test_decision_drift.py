"""Unit tests for ``flow_engineering.decision_drift.classify_binding`` (REQ-9).

T1.4 RED fixtures. Twelve per-class cases (six mutually-exclusive drift
classes plus ``UNABLE_TO_VERIFY``) plus two deferral assertions pinning
``OBSOLETE`` / ``CONTRADICTED`` to ``scan_change`` (design #123 decisions
2 + 3 — classify_binding is single-binding only).

The RED phase expects every test in this file to fail with
``NotImplementedError`` from the stubbed ``classify_binding``. The GREEN
phase (T1.5) implements the function so all of these pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flow_engineering.binding import CodeRef, format_code_refs_block
from flow_engineering.decision_drift import (
    DriftClass,
    DriftReport,
    Finding,
    classify_binding,
    load_graph,
    scan_change,
)
from flow_engineering.engram_io import InMemoryBackend


def _ref(
    *,
    project: str = "insyd",
    id: str = "src_auth_jwt_jwttokenmanager",
    label: str = "JWTTokenManager",
    file: str = "src/auth/jwt.py",
    line: int = 42,
    confidence: float = 0.9,
    source: str = "manual",
) -> CodeRef:
    return CodeRef(
        project=project,
        id=id,
        label=label,
        file=file,
        line=line,
        confidence=confidence,
        source=source,
    )


def _nodes(*pairs: tuple[str, str]) -> dict[str, dict]:
    return {
        pid: {"id": pid, "label": lbl, "file": "src/auth/jwt.py", "line": 42}
        for pid, lbl in pairs
    }


# --- STILL_VALID -----------------------------------------------------------


def test_classify_still_valid_basic() -> None:
    binding = _ref()
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    assert classify_binding(binding, nodes) is DriftClass.STILL_VALID


def test_classify_still_valid_source_and_confidence_dont_affect_class() -> None:
    binding = _ref(source="backfill", confidence=0.3)
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    assert classify_binding(binding, nodes) is DriftClass.STILL_VALID


# --- LABEL_DRIFT -----------------------------------------------------------


def test_classify_label_drift_when_label_differs() -> None:
    binding = _ref(label="JWTTokenManager")
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTManager"))
    assert classify_binding(binding, nodes) is DriftClass.LABEL_DRIFT


def test_classify_label_drift_case_only_still_flags() -> None:
    binding = _ref(label="jwtTokenManager")
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JwtTokenManager"))
    assert classify_binding(binding, nodes) is DriftClass.LABEL_DRIFT


# --- STALE_LOCATION --------------------------------------------------------


def test_classify_stale_location_when_file_moved() -> None:
    binding = _ref(file="src/old.py", line=10)
    nodes = {
        "src_auth_jwt_jwttokenmanager": {
            "id": "src_auth_jwt_jwttokenmanager",
            "label": "JWTTokenManager",
            "file": "src/new.py",
            "line": 42,
        }
    }
    assert classify_binding(binding, nodes) is DriftClass.STALE_LOCATION


def test_classify_stale_location_when_line_shifted_same_file() -> None:
    binding = _ref(file="src/foo.py", line=10)
    nodes = {
        "src_auth_jwt_jwttokenmanager": {
            "id": "src_auth_jwt_jwttokenmanager",
            "label": "JWTTokenManager",
            "file": "src/foo.py",
            "line": 15,
        }
    }
    assert classify_binding(binding, nodes) is DriftClass.STALE_LOCATION


# --- STALE_ID --------------------------------------------------------------


def test_classify_stale_id_when_id_absent_from_graph() -> None:
    binding = _ref(id="deleted_class_hash")
    nodes = _nodes(("other_node", "Other"))
    assert classify_binding(binding, nodes) is DriftClass.STALE_ID


def test_classify_stale_id_when_id_renamed_with_no_alias() -> None:
    binding = _ref(id="old_class_hash")
    nodes = _nodes(("new_class_hash", "NewClass"))
    assert classify_binding(binding, nodes) is DriftClass.STALE_ID


# --- UNABLE_TO_VERIFY (terminal) -------------------------------------------


def test_classify_unable_to_verify_when_current_nodes_is_none() -> None:
    binding = _ref()
    assert classify_binding(binding, None) is DriftClass.UNABLE_TO_VERIFY


def test_classify_unable_to_verify_when_current_nodes_is_empty() -> None:
    binding = _ref()
    assert classify_binding(binding, {}) is DriftClass.UNABLE_TO_VERIFY


# --- Deferral: OBSOLETE + CONTRADICTED are NOT classify_binding's job -----


def test_classify_binding_never_returns_obsolete_for_resolvable_id() -> None:
    """``OBSOLETE`` is scan_change's job (design #123 decision 3).

    Even when the binding's ``source`` is ``unbound``, classify_binding must
    not emit ``OBSOLETE`` — that verdict requires per-decision graphify_query
    work which only ``scan_change`` performs.
    """
    binding = _ref(source="unbound", confidence=0.0)
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    assert classify_binding(binding, nodes) is not DriftClass.OBSOLETE


def test_classify_binding_never_returns_contradicted() -> None:
    """``CONTRADICTED`` is scan_change's job (design #123 decision 2).

    Contradiction is a cross-decision property (same id, multiple bindings,
    conflicting source/confidence); a single binding cannot be contradicted
    with itself.
    """
    binding = _ref(source="manual", confidence=0.9)
    nodes = _nodes(("src_auth_jwt_jwttokenmanager", "JWTTokenManager"))
    assert classify_binding(binding, nodes) is not DriftClass.CONTRADICTED


# --- Dataclass shape (smoke) ----------------------------------------------


def test_finding_is_frozen() -> None:
    f = Finding(
        decision_id=1,
        binding=_ref(),
        drift_class=DriftClass.STILL_VALID,
        detail="ok",
    )
    with pytest.raises(Exception):
        f.drift_class = DriftClass.LABEL_DRIFT  # type: ignore[misc]


def test_drift_report_defaults() -> None:
    r = DriftReport(
        change_name="decision-reality-drift",
        scanned_at="1970-01-01T00:00:00Z",
        graph_mtime=None,
        decisions_total=0,
        bindings_total=0,
    )
    assert r.class_counts == {}
    assert r.findings == []
    assert r.graph_unavailable is False


# --- load_graph (T1.6 batch C, commit 1) --------------------------------


def test_load_graph_returns_none_when_missing(tmp_path: Path) -> None:
    """Missing graph path -> (None, None, None). Fail-open contract."""
    nodes, id_map, mtime = load_graph(tmp_path / "does-not-exist.json")
    assert nodes is None
    assert id_map is None
    assert mtime is None


def test_load_graph_reads_valid_graph(tmp_path: Path) -> None:
    """Valid graph.json -> populated maps + matching mtime."""
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "n1",
                        "label": "Foo",
                        "source_file": "src/foo.py",
                        "source_location": "10",
                    },
                    {
                        "id": "n2",
                        "label": "Bar",
                        "file": "src/bar.py",
                        "line": 20,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    nodes, id_map, mtime = load_graph(graph_path)
    assert nodes is not None
    assert id_map is not None
    assert mtime is not None
    assert set(nodes) == {"n1", "n2"}
    assert id_map["n1"] == ("src/foo.py", 10, "Foo")
    assert id_map["n2"] == ("src/bar.py", 20, "Bar")
    assert mtime == graph_path.stat().st_mtime


def test_load_graph_returns_none_for_malformed_json(tmp_path: Path) -> None:
    """Malformed JSON -> (None, None, None). Fail-open contract."""
    graph_path = tmp_path / "graph.json"
    graph_path.write_text("this is not json {", encoding="utf-8")
    nodes, id_map, mtime = load_graph(graph_path)
    assert nodes is None
    assert id_map is None
    assert mtime is None


def test_load_graph_returns_none_for_unexpected_shape(tmp_path: Path) -> None:
    """Top-level list (not dict) or 'nodes' missing -> (None, None, None)."""
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    nodes, id_map, mtime = load_graph(graph_path)
    assert nodes is None
    assert id_map is None
    assert mtime is None


def test_load_graph_skips_malformed_node_entries(tmp_path: Path) -> None:
    """Per-node 'id' missing -> entry skipped, valid entries kept."""
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {"id": "ok", "label": "Ok", "file": "src/o.py", "line": 1},
                    {"label": "NoId", "file": "src/x.py", "line": 9},
                    "not-a-dict",
                ]
            }
        ),
        encoding="utf-8",
    )
    nodes, id_map, _ = load_graph(graph_path)
    assert nodes is not None
    assert set(nodes) == {"ok"}
    assert id_map["ok"] == ("src/o.py", 1, "Ok")


# --- scan_change + observability counters (T1.6 batch C, commit 2 RED) --


METRICS_PATH_ENV = "FLOW_METRICS_PATH"


def _ref_block(
    *,
    node_id: str,
    label: str,
    file: str,
    line: int,
    confidence: float,
    source: str = "manual",
) -> str:
    """Build a content string with a valid `code_refs` block for one node."""
    ref = CodeRef(
        project="insyd",
        id=node_id,
        label=label,
        file=file,
        line=line,
        confidence=confidence,
        source=source,
    )
    return f"prose content\n{format_code_refs_block([ref], source=source)}"


def _seed_change(backend: InMemoryBackend, *contents: str, change: str = "test") -> None:
    """Seed observations under the standard sdd/{change}/ topic-key prefix."""
    topic = f"sdd/{change}/spec"
    for content in contents:
        backend.mem_save(title="decision", content=content, topic_key=topic)


def test_scan_change_graph_unavailable(tmp_path: Path) -> None:
    """Missing graph.json -> DriftReport with graph_unavailable=True."""
    missing = tmp_path / "graph.json"
    report = scan_change("test", graph_json_path=missing)
    assert report.graph_unavailable is True
    assert report.graph_mtime is None
    assert report.decisions_total == 0
    assert report.bindings_total == 0
    assert report.class_counts == {}
    assert report.findings == []


def test_scan_change_snapshot(tmp_path: Path) -> None:
    """Available graph.json -> report carries mtime matching the file."""
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps({"nodes": []}), encoding="utf-8")
    backend = InMemoryBackend()
    _seed_change(backend, "no refs here")

    report = scan_change("test", graph_json_path=graph_path, backend=backend)

    assert report.graph_unavailable is False
    # v0.8.0 (REQ-56 W8): graph_mtime is ISO 8601 str, not float epoch.
    from datetime import datetime, timezone
    expected_iso = datetime.fromtimestamp(
        graph_path.stat().st_mtime, tz=timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert report.graph_mtime == expected_iso


def test_scan_change_basic_aggregation(tmp_path: Path) -> None:
    """Five decisions mixed -> correct class_counts + decisions_total.

    Decisions 1-4 each carry one binding covering a different drift class.
    Decision 5 carries no `code_refs` at all (counts as a decision, not a
    binding) so decisions_total=5 while bindings_total=4.
    """
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "n_valid",
                        "label": "Valid",
                        "source_file": "src/v.py",
                        "source_location": "10",
                    },
                    {
                        "id": "n_label",
                        "label": "NewLabel",
                        "source_file": "src/l.py",
                        "source_location": "20",
                    },
                    {
                        "id": "n_loc",
                        "label": "Loc",
                        "source_file": "src/loc_new.py",
                        "source_location": "30",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    backend = InMemoryBackend()
    _seed_change(
        backend,
        _ref_block(node_id="n_valid", label="Valid", file="src/v.py", line=10, confidence=0.9),
        _ref_block(node_id="n_label", label="OldLabel", file="src/l.py", line=20, confidence=0.8),
        _ref_block(node_id="n_loc", label="Loc", file="src/loc_old.py", line=1, confidence=0.7),
        _ref_block(node_id="missing_id", label="Foo", file="src/x.py", line=1, confidence=0.6),
        "decision with no code_refs at all",
    )

    report = scan_change("test", graph_json_path=graph_path, backend=backend)

    assert report.graph_unavailable is False
    assert report.decisions_total == 5
    assert report.bindings_total == 4
    assert report.class_counts.get(DriftClass.STILL_VALID) == 1
    assert report.class_counts.get(DriftClass.LABEL_DRIFT) == 1
    assert report.class_counts.get(DriftClass.STALE_LOCATION) == 1
    assert report.class_counts.get(DriftClass.STALE_ID) == 1
    assert len(report.findings) == 4


def test_scan_change_obsolete_opt_in_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """include_obsolete=False (default) -> OBSOLETE never appears in findings."""
    from flow_engineering import graphify_query

    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps({"nodes": []}), encoding="utf-8")
    backend = InMemoryBackend()
    _seed_change(backend, "decision prose with no code_refs")

    # Even when graphify would return zero candidates, OFF means no OBSOLETE.
    monkeypatch.setattr(graphify_query, "query_nodes", lambda *a, **kw: [])

    report = scan_change(
        "test", graph_json_path=graph_path, backend=backend, include_obsolete=False
    )
    obsolete = [f for f in report.findings if f.drift_class is DriftClass.OBSOLETE]
    assert obsolete == []
    assert report.graph_unavailable is False


def test_scan_change_obsolete_opt_in_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """include_obsolete=True + zero graphify candidates -> OBSOLETE finding."""
    from flow_engineering import graphify_query

    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps({"nodes": []}), encoding="utf-8")
    backend = InMemoryBackend()
    _seed_change(backend, "decision prose with no code_refs")

    monkeypatch.setattr(graphify_query, "query_nodes", lambda *a, **kw: [])

    report = scan_change(
        "test", graph_json_path=graph_path, backend=backend, include_obsolete=True
    )
    obsolete = [f for f in report.findings if f.drift_class is DriftClass.OBSOLETE]
    assert len(obsolete) == 1
    assert obsolete[0].drift_class is DriftClass.OBSOLETE


def test_scan_change_contradicted(tmp_path: Path) -> None:
    """Two decisions binding the same id with confidence_gap > 0.4 -> CONTRADICTED."""
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "n_shared",
                        "label": "Shared",
                        "source_file": "src/s.py",
                        "source_location": "10",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    backend = InMemoryBackend()
    _seed_change(
        backend,
        _ref_block(node_id="n_shared", label="Shared", file="src/s.py", line=10, confidence=0.9),
        _ref_block(node_id="n_shared", label="Shared", file="src/s.py", line=10, confidence=0.3),
    )

    report = scan_change("test", graph_json_path=graph_path, backend=backend)

    contradicted = [f for f in report.findings if f.drift_class is DriftClass.CONTRADICTED]
    assert len(contradicted) == 2
    assert report.decisions_total == 2
    assert report.bindings_total == 2
    # CONTRADICTED replaces STILL_VALID in class_counts for these two findings.
    assert report.class_counts.get(DriftClass.STILL_VALID, 0) == 0
    assert report.class_counts.get(DriftClass.CONTRADICTED) == 2


def test_scan_change_since_filter(tmp_path: Path) -> None:
    """since=<ts> skips observations whose created_at < cutoff."""
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps({"nodes": []}), encoding="utf-8")
    backend = InMemoryBackend()
    _seed_change(backend, "obs-a prose", "obs-b prose")

    # InMemoryBackend assigns created_at = next_id * 1000, so first save -> 1000,
    # second -> 2000. since=1500 keeps only the second observation.
    report = scan_change(
        "test", graph_json_path=graph_path, backend=backend, since=1500.0
    )
    assert report.decisions_total == 1
    assert report.graph_unavailable is False


def test_observability_drift_counters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """record_drift_summary emits 7 named counters into the JSONL sink.

    REQ-12: per invocation, exactly one JSONL line per counter is written.
    Counts of zero for absent classes are still emitted so downstream
    queries see a complete snapshot.
    """
    from flow_engineering import observability

    metrics_path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv(METRICS_PATH_ENV, str(metrics_path))

    report = DriftReport(
        change_name="test",
        scanned_at="1970-01-01T00:00:00Z",
        graph_mtime="1970-01-01T00:00:01Z",
        decisions_total=5,
        bindings_total=7,
        class_counts={
            DriftClass.STILL_VALID: 3,
            DriftClass.LABEL_DRIFT: 2,
            DriftClass.STALE_ID: 1,
        },
    )
    observability.record_drift_summary(report)

    events = [
        json.loads(line)
        for line in metrics_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    names = [e["name"] for e in events]
    assert names.count("drift_invoked_total") == 1
    for counter in (
        "drift_still_valid_total",
        "drift_label_drift_total",
        "drift_stale_location_total",
        "drift_stale_id_total",
        "drift_obsolete_total",
        "drift_contradicted_total",
    ):
        assert names.count(counter) == 1, counter

    by_name = {
        e["name"]: e["fields"].get("count")
        for e in events
        if "count" in e.get("fields", {})
    }
    assert by_name["drift_still_valid_total"] == 3
    assert by_name["drift_label_drift_total"] == 2
    assert by_name["drift_stale_id_total"] == 1
    assert by_name["drift_stale_location_total"] == 0
    assert by_name["drift_obsolete_total"] == 0
    assert by_name["drift_contradicted_total"] == 0