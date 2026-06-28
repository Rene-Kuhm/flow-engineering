"""Unit tests for `flow drift <change>` CLI subcommand (REQ-10/11/14).

The ``drift`` subcommand wraps :func:`decision_drift.scan_change` with:

* A small, fast table renderer (default) and a ``--json`` machine-readable form.
* Exit-code contract (REQ-11): ``0`` when every binding is ``STILL_VALID``,
  ``1`` when at least one binding is non-valid, ``2`` when the graph is
  unavailable OR the ``--since`` value fails to parse. ``2`` wins over ``1``.
* ``--write-back`` writes ``last_verified_at`` and ``last_drift_class`` metadata
  to each affected observation via :meth:`EngramClient.update_observation_metadata`
  — per-row errors are isolated, never abort the loop.
* ``--include-obsolete`` opt-in triggers the expensive
  :func:`graphify_query.query_nodes` path.
* ``--since <ISO 8601>`` parses the timestamp into a ``float`` epoch seconds
  cutoff; bad input exits ``2`` with a one-line stderr explanation.

Tests are written BEFORE the implementation per strict TDD. They MUST fail
until the GREEN commit wires the ``drift`` command.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from flow_engineering.binding import format_code_refs_block
from flow_engineering.cli import main
from flow_engineering.decision_drift import (
    DriftClass,
    DriftReport,
    Finding,
)

runner = CliRunner()


# ---------- Fixtures ----------


def _make_obs(
    *, obs_id: int, title: str, content: str, created_at: int = 1000, updated_at: int = 1000,
) -> dict:
    """Build an observation dict shaped like InMemoryBackend.mem_save output."""
    return {
        "id": obs_id,
        "title": title,
        "content": content,
        "topic_key": f"sdd/my-change/{title.split('/')[-1] if '/' in title else 'phase'}",
        "type": "architecture",
        "scope": "project",
        "project": "insyd",
        "created_at": created_at,
        "updated_at": updated_at,
    }


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point observability at a tmp_path JSONL file."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


@pytest.fixture
def seeded_backend(monkeypatch: pytest.MonkeyPatch):
    """Patch EngramClient backend to use a pre-seeded InMemoryBackend.

    Returns ``(backend, _seed, observations)`` so callers can read stored state.
    The CLI uses ``InMemoryBackend`` by default — monkeypatch
    ``_default_save_backend`` so callers can pre-seed observations.
    """
    from flow_engineering import engram_io

    backend = engram_io.InMemoryBackend()
    observations: dict[int, dict] = {}

    def _seed(obs_list: list[dict]) -> None:
        for o in obs_list:
            backend.observations[o["id"]] = o
            backend.next_id = max(backend.next_id, o["id"] + 1)
            observations[o["id"]] = o

    monkeypatch.setattr(
        "flow_engineering.cli._default_save_backend", lambda: backend
    )
    return backend, _seed, observations


@pytest.fixture
def graph_path(tmp_path: Path) -> Path:
    """Default graph.json location for tests (no fixture content required)."""
    return tmp_path / "graph.json"


def _build_finding(
    *, obs_id: Any, ref_id: str = "n1", label: str = "L",
    file: str = "src/x.py", line: int = 1, source: str = "manual",
    drift_class: DriftClass = DriftClass.STILL_VALID, detail: str = "",
) -> Finding:
    """Build a Finding with a CodeRef-style binding for CLI tests.

    v0.9.0 (REQ-V9.4): ``decision_id`` must be ``int``; the v0.8.0
    shim that accepted str and coerced via ``int()`` is gone.
    """
    from flow_engineering.binding import CodeRef

    binding = CodeRef(
        project="insyd", id=ref_id, label=label, file=file, line=line,
        confidence=0.9, source=source,
    )
    return Finding(
        decision_id=int(obs_id), binding=binding,
        drift_class=drift_class, detail=detail,
    )


def _patch_scan(
    monkeypatch: pytest.MonkeyPatch, *, report: DriftReport | None = None,
    raise_exc: Exception | None = None,
) -> None:
    """Replace ``decision_drift.scan_change`` with a stub returning ``report``.

    When ``raise_exc`` is provided, the stub raises (used to verify the CLI
    does not propagate library exceptions — REQ-14).
    """
    from flow_engineering import cli as cli_mod

    def _stub(*args: Any, **kwargs: Any) -> DriftReport:
        if raise_exc is not None:
            raise raise_exc
        assert report is not None
        return report

    monkeypatch.setattr(cli_mod.decision_drift, "scan_change", _stub)


# ---------- REQ-11: exit code 0 — all bindings STILL_VALID ----------


class TestExitCodeZero:
    """REQ-11: every binding classifies STILL_VALID -> exit 0."""

    def test_drift_all_still_valid_exits_0(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        _, _, _ = seeded_backend
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=1,
            bindings_total=1,
            class_counts={DriftClass.STILL_VALID: 1},
            findings=[_build_finding(obs_id=1, drift_class=DriftClass.STILL_VALID)],
        )
        _patch_scan(monkeypatch, report=report)

        result = runner.invoke(main, ["drift", "my-change", "--graph-json", str(graph_path)])
        assert result.exit_code == 0, result.output


# ---------- REQ-11: exit code 1 — any non-valid binding ----------


class TestExitCodeOne:
    """REQ-11: at least one non-STILL_VALID binding -> exit 1."""

    def test_drift_with_stale_id_exits_1(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        _, _, _ = seeded_backend
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=1,
            bindings_total=1,
            class_counts={DriftClass.STALE_ID: 1},
            findings=[_build_finding(obs_id=1, drift_class=DriftClass.STALE_ID)],
        )
        _patch_scan(monkeypatch, report=report)

        result = runner.invoke(main, ["drift", "my-change", "--graph-json", str(graph_path)])
        assert result.exit_code == 1, result.output

    def test_drift_with_label_drift_exits_1(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        _, _, _ = seeded_backend
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=2,
            bindings_total=2,
            class_counts={
                DriftClass.STILL_VALID: 1,
                DriftClass.LABEL_DRIFT: 1,
            },
            findings=[
                _build_finding(obs_id=1, ref_id="ok", drift_class=DriftClass.STILL_VALID),
                _build_finding(obs_id=2, ref_id="renamed",
                               drift_class=DriftClass.LABEL_DRIFT),
            ],
        )
        _patch_scan(monkeypatch, report=report)

        result = runner.invoke(main, ["drift", "my-change", "--graph-json", str(graph_path)])
        assert result.exit_code == 1, result.output


# ---------- REQ-11: exit code 2 — graph unavailable wins over exit 1 ----------


class TestExitCodeTwo:
    """REQ-11: terminal `unable_to_verify` exits 2, taking precedence over 1."""

    def test_drift_graph_unavailable_exits_2(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        _, _, _ = seeded_backend
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=None,
            decisions_total=0,
            bindings_total=0,
            class_counts={},
            findings=[],
            graph_unavailable=True,
        )
        _patch_scan(monkeypatch, report=report)

        result = runner.invoke(main, ["drift", "my-change", "--graph-json", str(graph_path)])
        assert result.exit_code == 2, result.output

    def test_drift_graph_unavailable_wins_over_drift_findings(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        """REQ-11 precedence: graph_unavailable=True forces exit 2 even with drift findings."""
        _, _, _ = seeded_backend
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=None,
            decisions_total=1,
            bindings_total=1,
            class_counts={DriftClass.STALE_ID: 1},
            findings=[_build_finding(obs_id=1, drift_class=DriftClass.STALE_ID)],
            graph_unavailable=True,
        )
        _patch_scan(monkeypatch, report=report)

        result = runner.invoke(main, ["drift", "my-change", "--graph-json", str(graph_path)])
        assert result.exit_code == 2, result.output

    def test_drift_since_invalid_exits_2(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        _, _, _ = seeded_backend
        # scan_change must NOT be called when --since is malformed.
        called: dict[str, Any] = {"called": False}

        from flow_engineering import cli as cli_mod

        def _stub(*args: Any, **kwargs: Any) -> DriftReport:
            called["called"] = True
            return DriftReport(
                change_name="my-change", scanned_at=1000.0, graph_mtime=None,
                decisions_total=0, bindings_total=0, class_counts={}, findings=[],
            )

        monkeypatch.setattr(cli_mod.decision_drift, "scan_change", _stub)

        result = runner.invoke(
            main,
            ["drift", "my-change", "--graph-json", str(graph_path),
             "--since", "yesterday"],
        )
        assert result.exit_code == 2, result.output
        assert "since" in (result.stderr or "").lower() or "iso" in (result.stderr or "").lower()
        assert called["called"] is False, "scan_change should not run on parse error"


# ---------- REQ-10: --json output ----------


class TestJsonOutput:
    """REQ-10: `--json` emits parseable machine-readable output."""

    def test_drift_json_output_parseable(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        _, _, _ = seeded_backend
        report = DriftReport(
            change_name="my-change",
            scanned_at=1700000000.0,
            graph_mtime=1699999900.0,
            decisions_total=1,
            bindings_total=1,
            class_counts={DriftClass.STALE_ID: 1},
            findings=[_build_finding(obs_id=42, ref_id="missing_node",
                                     drift_class=DriftClass.STALE_ID)],
        )
        _patch_scan(monkeypatch, report=report)

        result = runner.invoke(
            main,
            ["drift", "my-change", "--graph-json", str(graph_path), "--json"],
        )
        assert result.exit_code == 1, result.output
        payload = json.loads(result.output)
        assert isinstance(payload, dict)
        assert payload["change_name"] == "my-change"
        assert payload["decisions_total"] == 1
        assert payload["bindings_total"] == 1
        assert len(payload["findings"]) == 1
        f0 = payload["findings"][0]
        assert f0["decision_id"] == 42
        assert isinstance(f0["decision_id"], int)
        assert f0["drift_class"] == "STALE_ID"
        assert f0["binding"]["id"] == "missing_node"


# ---------- REQ-10: --include-obsolete ----------


class TestIncludeObsolete:
    """REQ-10: `--include-obsolete` propagates to scan_change."""

    def test_drift_include_obsolete_triggers_obsolete_check(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        _, _, _ = seeded_backend
        captured: dict[str, Any] = {}

        from flow_engineering import cli as cli_mod

        def _stub(
            change_name: str, *, graph_json_path: Path, backend: Any = None,
            include_obsolete: bool = False, since: float | None = None,
            snap_id: str | None = None,
        ) -> DriftReport:
            captured["change_name"] = change_name
            captured["graph_json_path"] = graph_json_path
            captured["include_obsolete"] = include_obsolete
            captured["since"] = since
            captured["snap_id"] = snap_id
            return DriftReport(
                change_name=change_name, scanned_at=1000.0, graph_mtime=999.0,
                decisions_total=0, bindings_total=0, class_counts={}, findings=[],
            )

        monkeypatch.setattr(cli_mod.decision_drift, "scan_change", _stub)

        result = runner.invoke(
            main,
            ["drift", "my-change", "--graph-json", str(graph_path),
             "--include-obsolete"],
        )
        assert result.exit_code == 0, result.output
        assert captured["include_obsolete"] is True


# ---------- REQ-10: --since ----------


class TestSince:
    """REQ-10: `--since` parses ISO 8601 and passes float epoch seconds."""

    def test_drift_since_passes_epoch_seconds(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        _, _, _ = seeded_backend
        captured: dict[str, Any] = {}

        from flow_engineering import cli as cli_mod

        def _stub(
            change_name: str, *, graph_json_path: Path, backend: Any = None,
            include_obsolete: bool = False, since: float | None = None,
            snap_id: str | None = None,
        ) -> DriftReport:
            captured["since"] = since
            captured["snap_id"] = snap_id
            return DriftReport(
                change_name=change_name, scanned_at=1000.0, graph_mtime=999.0,
                decisions_total=0, bindings_total=0, class_counts={}, findings=[],
            )

        monkeypatch.setattr(cli_mod.decision_drift, "scan_change", _stub)

        result = runner.invoke(
            main,
            ["drift", "my-change", "--graph-json", str(graph_path),
             "--since", "2026-06-15"],
        )
        assert result.exit_code == 0, result.output
        # 2026-06-15T00:00:00Z -> epoch seconds
        expected = datetime(2026, 6, 15, tzinfo=UTC).timestamp()
        assert captured["since"] == pytest.approx(expected, rel=0, abs=1)


# ---------- REQ-14: --write-back ----------


class TestWriteBack:
    """REQ-14: `--write-back` persists per-finding metadata; errors isolated."""

    def test_drift_write_back_calls_update_metadata(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        _, _, _ = seeded_backend
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=1,
            bindings_total=1,
            class_counts={DriftClass.STALE_ID: 1},
            findings=[_build_finding(obs_id=42, ref_id="missing_node",
                                     drift_class=DriftClass.STALE_ID)],
        )
        _patch_scan(monkeypatch, report=report)

        update_calls: list[tuple[int, dict[str, Any]]] = []

        # Patch the helper that drives update_observation_metadata. We assert the
        # helper is invoked with the right observation_id + payload by mocking
        # the EngramClient that the CLI uses internally. The CLI imports
        # EngramClient by name into flow_engineering.cli, so the patch must
        # target the local binding (NOT engram_io.EngramClient).
        import flow_engineering.cli as cli_mod

        class _FakeClient:
            def __init__(self, change: str, backend: Any) -> None:
                self.change = change
                self.backend = backend

            def update_observation_metadata(
                self, observation_id: int, metadata: dict[str, Any]
            ) -> None:
                update_calls.append((observation_id, dict(metadata)))

        monkeypatch.setattr(cli_mod, "EngramClient", _FakeClient)

        result = runner.invoke(
            main,
            ["drift", "my-change", "--graph-json", str(graph_path), "--write-back"],
        )
        assert result.exit_code == 1, result.output
        assert len(update_calls) == 1, update_calls
        obs_id, payload = update_calls[0]
        assert obs_id == 42
        assert payload["last_drift_class"] == "STALE_ID"
        assert "last_verified_at" in payload

    def test_drift_write_back_per_row_error_isolated(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        """REQ-14: one row failing MUST NOT abort the loop."""
        _, _, _ = seeded_backend
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=2,
            bindings_total=2,
            class_counts={DriftClass.STALE_ID: 2},
            findings=[
                _build_finding(obs_id=10, ref_id="a", drift_class=DriftClass.STALE_ID),
                _build_finding(obs_id=11, ref_id="b", drift_class=DriftClass.STALE_ID),
            ],
        )
        _patch_scan(monkeypatch, report=report)

        update_calls: list[int] = []

        import flow_engineering.cli as cli_mod

        class _FakeClient:
            def __init__(self, change: str, backend: Any) -> None:
                self.change = change
                self.backend = backend

            def update_observation_metadata(
                self, observation_id: int, metadata: dict[str, Any]
            ) -> None:
                if observation_id == 10:
                    raise RuntimeError("boom")
                update_calls.append(observation_id)

        monkeypatch.setattr(cli_mod, "EngramClient", _FakeClient)

        result = runner.invoke(
            main,
            ["drift", "my-change", "--graph-json", str(graph_path), "--write-back"],
        )
        assert result.exit_code == 1, result.output
        # The second row still got updated despite the first raising.
        assert update_calls == [11], update_calls

    def test_drift_no_write_back_default_is_read_only(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        """REQ-14: default mode MUST NOT mutate observations."""
        _, _, _ = seeded_backend
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=1,
            bindings_total=1,
            class_counts={DriftClass.STALE_ID: 1},
            findings=[_build_finding(obs_id=1, drift_class=DriftClass.STALE_ID)],
        )
        _patch_scan(monkeypatch, report=report)

        update_calls: list[int] = []

        import flow_engineering.cli as cli_mod

        class _FakeClient:
            def __init__(self, change: str, backend: Any) -> None:
                self.change = change
                self.backend = backend

            def update_observation_metadata(
                self, observation_id: int, metadata: dict[str, Any]
            ) -> None:
                update_calls.append(observation_id)

        monkeypatch.setattr(cli_mod, "EngramClient", _FakeClient)

        result = runner.invoke(main, ["drift", "my-change", "--graph-json", str(graph_path)])
        assert result.exit_code == 1, result.output
        assert update_calls == [], "default mode must NOT call update_observation_metadata"


# ---------- REQ-10: pretty table output ----------


class TestTableOutput:
    """REQ-10: default mode prints a human-readable table with key columns."""

    def test_drift_table_output_format(
        self, seeded_backend, metrics_path, graph_path, monkeypatch
    ) -> None:
        _, _, _ = seeded_backend
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=1,
            bindings_total=1,
            class_counts={DriftClass.STALE_ID: 1},
            findings=[_build_finding(
                obs_id=42, ref_id="ghost", label="GhostNode",
                drift_class=DriftClass.STALE_ID,
            )],
        )
        _patch_scan(monkeypatch, report=report)

        result = runner.invoke(main, ["drift", "my-change", "--graph-json", str(graph_path)])
        assert result.exit_code == 1, result.output
        out = result.output
        # Decision_id and binding.id + drift_class all visible.
        assert "42" in out
        assert "ghost" in out
        assert "STALE_ID" in out


# ---------- REQ-10: --help ----------


class TestHelpText:
    """The ``drift`` subcommand MUST document the exit-code contract in help."""

    def test_drift_help_text_includes_exit_codes(self) -> None:
        result = runner.invoke(main, ["drift", "--help"])
        assert result.exit_code == 0, result.output
        # Exit codes are part of the contract — they MUST appear in --help.
        assert "0" in result.output and "1" in result.output and "2" in result.output


# ---------- REQ-59 S2: _write_back_findings stderr WARN (D8) ----------


class TestWriteBackSkipWarn:
    """REQ-59 S2: ``_write_back_findings`` MUST emit a single stderr WARN
    line when ``skipped_total >= FLOW_DRIFT_SKIP_WARN_THRESHOLD``.

    Per design D8: once per batch (NOT per skipped row). Default threshold
    is 3; tunable via env var; ``-1`` disables; ``0`` emits every batch
    with skipped_total > 0; parse errors fall back to 3.
    """

    def test_write_back_emits_stderr_warn_on_non_int_decision_id(
        self,
        seeded_backend,
        metrics_path,
        graph_path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """v0.9.0 (REQ-V9.4): constructing a Finding with non-int decision_id
        raises TypeError at the dataclass boundary.

        The legacy v0.7.x soft-compat shim was removed in v0.9.0; the
        construction-time TypeError IS the new signal (no separate stderr
        WARN path is reachable via normal Finding construction). The
        skip path inside ``_write_back_findings`` is retained as
        defensive coding for any future caller that bypasses the
        dataclass.
        """
        from flow_engineering.binding import CodeRef as _CodeRef

        with pytest.raises(TypeError) as exc_info:
            Finding(
                decision_id="non-int-0",  # type: ignore[arg-type]
                binding=_CodeRef(
                    project="insyd", id="r", label="L",
                    file="src/x.py", line=1, confidence=0.9, source="manual",
                ),
                drift_class=DriftClass.STALE_ID,
                detail="",
            )
        assert "decision_id" in str(exc_info.value) or "int" in str(exc_info.value)

    def test_write_back_no_warn_when_all_decision_ids_valid(
        self,
        seeded_backend,
        metrics_path,
        graph_path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A batch with 0 skipped rows MUST NOT emit any stderr WARN line."""
        from flow_engineering import cli as cli_mod

        findings = [
            _build_finding(
                obs_id=i,
                ref_id=f"ref_{i}",
                drift_class=DriftClass.STALE_ID,
            )
            for i in range(5)
        ]
        report = DriftReport(
            change_name="my-change",
            scanned_at=1000.0,
            graph_mtime=999.0,
            decisions_total=5,
            bindings_total=5,
            class_counts={DriftClass.STALE_ID: 5},
            findings=findings,
        )
        monkeypatch.delenv("FLOW_DRIFT_SKIP_WARN_THRESHOLD", raising=False)
        _patch_scan(monkeypatch, report=report)

        update_calls: list[int] = []

        class _FakeClient:
            def __init__(self, change: str, backend: Any) -> None:
                pass

            def update_observation_metadata(
                self, observation_id: int, metadata: dict[str, Any]
            ) -> None:
                update_calls.append(observation_id)

        monkeypatch.setattr(cli_mod, "EngramClient", _FakeClient)

        result = runner.invoke(
            main,
            ["drift", "my-change", "--graph-json", str(graph_path), "--write-back"],
        )

        stderr_text = (result.stderr or "") + capsys.readouterr().err
        warn_lines = [
            ln for ln in stderr_text.splitlines() if "WARN" in ln and "skipped" in ln
        ]
        assert warn_lines == [], (
            f"expected no WARN lines on a clean batch; got {warn_lines!r}"
        )
        # All 5 rows were written.
        assert len(update_calls) == 5, update_calls

    def test_write_back_warn_includes_skipped_count(
        self,
        seeded_backend,
        metrics_path,
        graph_path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """v0.9.0 (REQ-V9.4): the v0.7.x "non-int decision_id → skipped →
        WARN" scenario is structurally unreachable. ``Finding.decision_id``
        is hard-typed ``int`` (via :meth:`Finding.__post_init__`), so the
        ``int(finding.decision_id)`` cast inside ``_write_back_findings``
        never raises — the skip path is dead code in v0.9.0.

        This fixture is kept for documentation parity with the v0.8.0
        contract surface; the body validates the strict construction-time
        rejection (the dataclass boundary IS the new signal). See
        ``test_write_back_emits_stderr_warn_on_non_int_decision_id`` for
        the primary coverage of the TypeError contract.
        """
        from flow_engineering.binding import CodeRef as _CodeRef

        with pytest.raises(TypeError) as exc_info:
            Finding(
                decision_id="non-int-0",  # type: ignore[arg-type]
                binding=_CodeRef(
                    project="insyd", id="r", label="L",
                    file="src/x.py", line=1, confidence=0.9, source="manual",
                ),
                drift_class=DriftClass.STALE_ID,
                detail="",
            )
        assert "decision_id" in str(exc_info.value) or "int" in str(exc_info.value) 
