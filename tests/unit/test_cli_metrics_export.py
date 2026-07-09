"""Unit tests for the ``flow metrics export`` CLI subcommand (REQ-38 / D6).

Covers the new ``flow metrics export --format=<fmt> [--out=<path>]`` subcommand
that PR#2 T2.2 lands on top of the existing ``flow metrics summary`` surface.
The subcommand reuses the read-side observability helpers (read_all_metrics,
filter_by_window, read_events_by_domain, summarize) and renders the result
in one of three formats:

- ``text`` — human-readable table (default for the no-flag ``flow metrics``).
- ``json`` — flat list of MetricEvent-shaped dicts.
- ``prometheus`` — Prometheus textfile exposition format (D6 / REQ-38).

The ``--out=<path>`` flag triggers an atomic write via
:func:`observability.atomic_write_text` (D10). When the destination is
unwritable, the subcommand emits a JSON error to stderr and exits ``4``
per design D9.

Exit-code mapping (D9):
- 0: success (including default-empty per D8: ``# EOF\n`` for prometheus).
- 2: invalid flag value (``--format=garbage``).
- 4: write failure on ``--out`` (permission denied / disk full).

Tests are written BEFORE the implementation per strict TDD (RED → GREEN →
REFACTOR).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering import observability
from flow_engineering.cli import main

runner = CliRunner()


# ---------- helpers ----------


def _write_jsonl(path: Path, events: list[dict]) -> None:
    """Write a JSONL sink file with the given events (one per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _event(name: str, fields: dict | None = None, ts: str | None = None) -> dict:
    """Build a single event dict matching the JSONL sink contract."""
    if ts is None:
        ts = _iso(datetime.now(UTC))
    return {"name": name, "fields": fields or {}, "ts": ts}


# ---------- format=prometheus ----------


class TestMetricsExportPrometheus:
    """``flow metrics export --format prometheus`` emits textfile exposition."""

    def test_metrics_export_prometheus_to_stdout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Stdout receives Prometheus textfile format with HELP + TYPE + lines."""
        metrics_file = tmp_path / "metrics.jsonl"
        _write_jsonl(metrics_file, [
            _event("suggest_invoked_total", {"count": 1}),
            _event("snapshot_create_total", {"count": 3}),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, ["metrics", "export", "--format", "prometheus"],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        assert "# HELP flow_suggest_invoked_total" in result.output
        assert "# TYPE flow_suggest_invoked_total counter" in result.output
        assert "# HELP flow_snapshot_create_total" in result.output
        assert "# TYPE flow_snapshot_create_total counter" in result.output
        assert "flow_suggest_invoked_total 1.0" in result.output
        assert "flow_snapshot_create_total 3.0" in result.output

    def test_metrics_export_prometheus_to_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--out=<path>`` writes the textfile atomically to disk."""
        metrics_file = tmp_path / "metrics.jsonl"
        out_file = tmp_path / "out.prom"
        _write_jsonl(metrics_file, [
            _event("suggest_invoked_total", {"count": 1}),
            _event("drift_invoked_total", {"count": 1, "change": "obs"}),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, [
                "metrics", "export", "--format", "prometheus",
                "--out", str(out_file),
            ],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "# HELP flow_suggest_invoked_total" in content
        assert "flow_drift_invoked_total{change=\"obs\"}" in content

    def test_metrics_export_prometheus_empty_sink_emits_eof(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty JSONL sink → ``# EOF\n`` per Prometheus convention (D8)."""
        metrics_file = tmp_path / "metrics.jsonl"
        metrics_file.write_text("", encoding="utf-8")
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, ["metrics", "export", "--format", "prometheus"],
        )

        assert result.exit_code == 0
        assert "# EOF" in result.output


# ---------- format=json ----------


class TestMetricsExportJson:
    """``flow metrics export --format json`` emits JSON list of event dicts."""

    def test_metrics_export_json_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """JSON format emits a parseable JSON list of MetricEvent-shaped dicts."""
        metrics_file = tmp_path / "metrics.jsonl"
        _write_jsonl(metrics_file, [
            _event("suggest_invoked_total", {"count": 1}),
            _event("drift_invoked_total", {"count": 1, "change": "obs"}),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, ["metrics", "export", "--format", "json"],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        payload = json.loads(result.output)
        assert isinstance(payload, list)
        assert len(payload) == 2
        names = {ev["name"] for ev in payload}
        assert names == {"suggest_invoked_total", "drift_invoked_total"}

    def test_metrics_export_json_to_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """JSON format also honors ``--out`` for atomic write."""
        metrics_file = tmp_path / "metrics.jsonl"
        out_file = tmp_path / "out.json"
        _write_jsonl(metrics_file, [_event("suggest_invoked_total", {"count": 5})])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, [
                "metrics", "export", "--format", "json",
                "--out", str(out_file),
            ],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        assert out_file.exists()
        payload = json.loads(out_file.read_text(encoding="utf-8"))
        assert payload[0]["name"] == "suggest_invoked_total"


# ---------- format=text ----------


class TestMetricsExportText:
    """``flow metrics export --format text`` emits human-readable table."""

    def test_metrics_export_text_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Text format emits a readable ``name  count`` table (mirrors REQ-8)."""
        metrics_file = tmp_path / "metrics.jsonl"
        _write_jsonl(metrics_file, [
            _event("suggest_invoked_total", {"count": 1}),
            _event("snapshot_create_total", {"count": 3}),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, ["metrics", "export", "--format", "text"],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        # Counters are alpha-sorted + name-padded.
        assert "snapshot_create_total" in result.output
        assert "suggest_invoked_total" in result.output
        assert "3" in result.output
        assert "1" in result.output


# ---------- filter composition ----------


class TestMetricsExportFilters:
    """``flow metrics export`` honors ``--window`` / ``--since`` / ``--domain``."""

    def test_metrics_export_with_window_filter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--window=1h`` rolling filter excludes events older than 60 minutes."""
        metrics_file = tmp_path / "metrics.jsonl"
        now = datetime.now(UTC)
        _write_jsonl(metrics_file, [
            _event("old_counter", {"count": 1}, ts=_iso(now - timedelta(hours=2))),
            _event("fresh_counter", {"count": 1}, ts=_iso(now)),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, [
                "metrics", "export", "--format", "prometheus",
                "--window", "1h",
            ],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        assert "fresh_counter" in result.output
        assert "old_counter" not in result.output

    def test_metrics_export_with_domain_filter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--domain=snapshot`` narrows output to snapshot_* counters."""
        metrics_file = tmp_path / "metrics.jsonl"
        _write_jsonl(metrics_file, [
            _event("suggest_invoked_total", {"count": 1}),
            _event("snapshot_create_total", {"count": 1}),
            _event("snapshot_prune_total", {"count": 2}),
        ])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, [
                "metrics", "export", "--format", "prometheus",
                "--domain", "snapshot",
            ],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        assert "# HELP flow_snapshot_create_total" in result.output
        assert "# HELP flow_snapshot_prune_total" in result.output
        # Non-snapshot counters MUST be excluded.
        assert "flow_suggest_invoked_total" not in result.output


# ---------- error paths ----------


class TestMetricsExportErrors:
    """``flow metrics export`` exit-code contract per D9."""

    def test_metrics_export_invalid_format_exits_2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--format=garbage`` exits 2 (Click ``click.Choice`` validation)."""
        metrics_file = tmp_path / "metrics.jsonl"
        metrics_file.write_text("", encoding="utf-8")
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, ["metrics", "export", "--format", "garbage"],
        )

        assert result.exit_code == observability.EXIT_INVALID_VALUE, (
            f"expected exit 2; got {result.exit_code}. output={result.output!r}"
        )

    def test_metrics_export_unwritable_out_exits_4(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--out`` write failure exits 4 (D9 I/O error)."""
        metrics_file = tmp_path / "metrics.jsonl"
        _write_jsonl(metrics_file, [_event("suggest_invoked_total", {"count": 1})])
        # Target a path inside a NON-EXISTENT directory that cannot be created
        # (parent path is a regular file, not a directory).
        blocker = tmp_path / "blocker"
        blocker.write_text("I am a file, not a directory", encoding="utf-8")
        unwritable_out = blocker / "nested" / "metrics.prom"
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, [
                "metrics", "export", "--format", "prometheus",
                "--out", str(unwritable_out),
            ],
        )

        assert result.exit_code == observability.EXIT_WRITE_FAILURE, (
            f"expected exit 4; got {result.exit_code}. output={result.output!r}"
        )
        # The error MUST go to stderr, NOT stdout (keeps stdout pipe-clean).
        assert "write failed" in result.output or "Error" in result.output


# ---------- empty sink contract ----------


class TestMetricsExportEmptySink:
    """``flow metrics export`` honors D8 default-empty across formats."""

    def test_metrics_export_empty_sink_text_emits_no_metrics_recorded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty sink + text format → ``(no metrics recorded)`` (REQ-8 close)."""
        metrics_file = tmp_path / "metrics.jsonl"
        metrics_file.write_text("", encoding="utf-8")
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, ["metrics", "export", "--format", "text"],
        )

        assert result.exit_code == 0
        assert "no metrics recorded" in result.output

    def test_metrics_export_empty_sink_json_emits_empty_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty sink + json format → ``[]``."""
        metrics_file = tmp_path / "metrics.jsonl"
        metrics_file.write_text("", encoding="utf-8")
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, ["metrics", "export", "--format", "json"],
        )

        assert result.exit_code == 0
        assert json.loads(result.output) == []


# ---------- CLI integration: --out writes atomically (no .tmp leftovers) ----------


class TestMetricsExportAtomicWrite:
    """``--out`` uses the atomic-write pattern (D10)."""

    def test_metrics_export_out_does_not_leave_tmp_orphans(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After ``--out`` success, no ``.tmp`` or ``.metrics-*`` leftovers."""
        metrics_file = tmp_path / "metrics.jsonl"
        out_file = tmp_path / "out.prom"
        _write_jsonl(metrics_file, [_event("suggest_invoked_total", {"count": 1})])
        monkeypatch.setenv("FLOW_METRICS_PATH", str(metrics_file))

        result = runner.invoke(
            main, [
                "metrics", "export", "--format", "prometheus",
                "--out", str(out_file),
            ],
        )

        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. output={result.output!r}"
        )
        leftovers = list(tmp_path.glob("*.tmp"))
        leftovers += list(tmp_path.glob(".metrics-*"))
        assert leftovers == [], f"unexpected tmp leftovers: {leftovers}"
