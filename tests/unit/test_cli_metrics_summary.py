"""Unit tests for the `flow metrics summary` CLI subcommand (REQ-35).

The summary subcommand is added in change #6 PR#1 batch A T1.2. It wraps the
new :func:`observability.read_all_metrics` / :func:`observability.read_events_by_domain`
helpers and renders a per-domain dashboard via :func:`observability.summarize`.

Flags under test:
- ``--format text|json|json-detailed`` (default ``text``).
- ``--window 1h|24h|7d`` (optional; rolling-window filter).
- ``--domain binding|drift|vector|snapshot`` (optional; prefix-based slice).

Exit codes per design D9:
- ``0`` success (including empty / no-match default-empty contract).
- ``2`` invalid flag value (e.g. unknown ``--domain``).
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _event(name: str, fields: dict | None = None, ts: str | None = None) -> dict:
    if ts is None:
        ts = _iso(datetime.now(UTC))
    return {"name": name, "fields": fields or {}, "ts": ts}


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


# ---------- text format (default) ----------


class TestSummaryTextFormat:
    """`flow metrics summary` (no flags) renders per-domain text dashboard."""

    def test_metrics_summary_text_format_default(
        self, metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        _write_jsonl(metrics_path, [
            _event("binding_suggest_invoked_total", {"count": 2}, _iso(now)),
            _event("binding_suggest_invoked_total", {"count": 1}, _iso(now)),
            _event("drift_invoked_total", {"count": 1}, _iso(now)),
        ])

        result = runner.invoke(main, ["metrics", "summary"])

        assert result.exit_code == 0, result.output
        # Each domain is rendered as its own section.
        assert "binding:" in result.output
        assert "drift:" in result.output
        # The counter totals appear under their domain.
        assert "binding_suggest_invoked_total" in result.output
        assert "drift_invoked_total" in result.output


# ---------- json format ----------


class TestSummaryJsonFormat:
    """`flow metrics summary --format json` emits machine-readable dict."""

    def test_metrics_summary_json_format(
        self, metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        _write_jsonl(metrics_path, [
            _event("binding_suggest_invoked_total", {"count": 2}, _iso(now)),
            _event("vector_search_invoked_total", {"count": 3}, _iso(now)),
        ])

        result = runner.invoke(main, ["metrics", "summary", "--format", "json"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert isinstance(payload, dict)
        assert "binding" in payload
        assert "vector" in payload
        assert payload["binding"]["binding_suggest_invoked_total"] == 2
        assert payload["vector"]["vector_search_invoked_total"] == 3


# ---------- --window filter ----------


class TestSummaryWindowFilter:
    """`--window 1h|24h|7d` filters events to the rolling window."""

    def test_metrics_summary_with_window_filter(
        self, metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        # 3h ago (outside 1h window) and now (inside 1h window).
        _write_jsonl(metrics_path, [
            _event("binding_suggest_invoked_total", {"count": 1},
                   _iso(now - timedelta(hours=3))),
            _event("binding_suggest_invoked_total", {"count": 5}, _iso(now)),
        ])

        result = runner.invoke(main, ["metrics", "summary", "--window", "1h"])

        assert result.exit_code == 0, result.output
        # Only the "now" event survives (count=5); the 3h-old event is excluded.
        assert "5" in result.output
        # The 3h-old event's count=1 should NOT appear alone in any domain row.
        # Since both contribute to the same counter, the rendered value must
        # be 5 (sum from inside-window) — verify against the rendered count.
        # We assert by parsing the rendered text: the dashboard shows the
        # counter with its accumulated value, which must reflect only in-window
        # events.
        lines = [ln.strip() for ln in result.output.splitlines() if ln.strip()]
        # At minimum, the rendered dashboard must NOT contain the lone
        # "binding_suggest_invoked_total  1" line (which would be the
        # 3h-old event alone).
        assert not any(
            line.startswith("binding_suggest_invoked_total") and "  1" in line
            for line in lines
        )


# ---------- --domain filter ----------


class TestSummaryDomainFilter:
    """`--domain <binding|drift|vector|snapshot>` filters by counter prefix."""

    def test_metrics_summary_with_domain_filter(
        self, metrics_path: Path,
    ) -> None:
        now = datetime.now(UTC)
        _write_jsonl(metrics_path, [
            _event("binding_suggest_invoked_total", {"count": 1}, _iso(now)),
            _event("drift_invoked_total", {"count": 1}, _iso(now)),
            _event("vector_search_invoked_total", {"count": 1}, _iso(now)),
        ])

        result = runner.invoke(main, ["metrics", "summary", "--domain", "drift"])

        assert result.exit_code == 0, result.output
        assert "drift_invoked_total" in result.output
        # Other-domain counters MUST be excluded.
        assert "binding_suggest_invoked_total" not in result.output
        assert "vector_search_invoked_total" not in result.output


# ---------- empty sink ----------


class TestSummaryEmptySink:
    """Empty / missing JSONL sink emits "No metrics recorded yet." + exits 0."""

    def test_metrics_summary_empty_metrics_file_exits_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "missing.jsonl"
        monkeypatch.setenv("FLOW_METRICS_PATH", str(path))

        result = runner.invoke(main, ["metrics", "summary"])

        assert result.exit_code == 0, result.output
        assert "No metrics recorded yet." in result.output


# ---------- invalid flag values (exit code 2) ----------


class TestSummaryInvalidFlags:
    """Invalid --domain / --window values exit with code 2 (D9 usage error)."""

    def test_metrics_summary_invalid_domain_exits_2(
        self, metrics_path: Path,
    ) -> None:
        result = runner.invoke(main, ["metrics", "summary", "--domain", "garbage"])

        assert result.exit_code == 2

    def test_metrics_summary_invalid_window_exits_2(
        self, metrics_path: Path,
    ) -> None:
        result = runner.invoke(main, ["metrics", "summary", "--window", "garbage"])

        assert result.exit_code == 2


# ---------- T1.5: --window custom + --since/--until (REQ-36 bonus surface) ----------


class TestSummaryWindowAndSinceUntil:
    """T1.5 wiring: --window accepts custom <int><h|d>; --since/--until ISO 8601.

    These tests cover the REQ-36 bonus surface per the prompt: the
    ``--window`` flag accepts preset OR custom format, ``--since`` /
    ``--until`` accept ISO 8601 absolute timestamps. Invalid values exit
    with code 2 (D9 usage error). The window-filter implementation lives
    in :func:`observability.filter_by_window` (T1.4).
    """

    def test_metrics_summary_with_window_filter_filters_correctly(
        self, metrics_path: Path,
    ) -> None:
        """30d window keeps events spanning 3 weeks (rolling semantics)."""
        now = datetime.now(UTC)
        # 25 days ago: inside 30d window
        _write_jsonl(metrics_path, [
            _event("binding_suggest_invoked_total", {"count": 7},
                   _iso(now - timedelta(days=25))),
            # 40 days ago: outside 30d window
            _event("drift_invoked_total", {"count": 3},
                   _iso(now - timedelta(days=40))),
        ])

        result = runner.invoke(main, ["metrics", "summary", "--window", "30d"])

        assert result.exit_code == 0, result.output
        # The 25d-old binding event survives; the 40d-old drift event is excluded.
        assert "binding_suggest_invoked_total" in result.output
        assert "drift_invoked_total" not in result.output
        assert "7" in result.output

    def test_metrics_summary_with_invalid_window_exits_2(
        self, metrics_path: Path,
    ) -> None:
        """Invalid custom window value (e.g. ``5x``) exits with code 2 (D9)."""
        result = runner.invoke(main, ["metrics", "summary", "--window", "5x"])

        assert result.exit_code == 2

    def test_metrics_summary_with_since_until_iso_filters(
        self, metrics_path: Path,
    ) -> None:
        """--since/--until ISO 8601 absolute timestamps filter events correctly."""
        _write_jsonl(metrics_path, [
            _event("binding_suggest_invoked_total", {"count": 1},
                   "2026-06-26T10:00:00Z"),
            _event("binding_suggest_invoked_total", {"count": 1},
                   "2026-06-26T15:00:00Z"),
            _event("binding_suggest_invoked_total", {"count": 1},
                   "2026-06-26T19:00:00Z"),
        ])

        result = runner.invoke(
            main,
            [
                "metrics", "summary",
                "--since", "2026-06-26T15:00:00Z",
                "--until", "2026-06-26T19:00:00Z",
                "--format", "json",
            ],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        # The 10:00 event is excluded; the 15:00 + 19:00 events are kept
        # (inclusive on both boundaries) → count=2 for binding_suggest_invoked_total.
        assert payload == {
            "binding": {"binding_suggest_invoked_total": 2},
        }


# ---------- T1.7: --domain widening to 8 values (REQ-37) ----------


class TestSummaryDomainFilterWidening:
    """T1.7: ``--domain`` flag widens from 4 values to 8 values (REQ-37 expansion).

    Per the spec, ``--domain`` now accepts ``binding|backfill|drift|vector|
    federated|snapshot|metadata|engine``. The ``engine`` slot is RESERVED
    (REQ-42 deferred to v1.1); passing it succeeds with an empty filter
    result rather than an error.
    """

    def test_metrics_summary_with_domain_filter_backfill(
        self, metrics_path: Path,
    ) -> None:
        """`--domain=backfill` returns ONLY ``backfill_*`` events.

        Regression check that the new ``backfill`` slot in
        :data:`observability.ALL_DOMAINS` is wired through the CLI to
        :func:`observability.read_events_by_domain`.
        """
        now = datetime.now(UTC)
        _write_jsonl(metrics_path, [
            _event("backfill_observations_total", {"count": 3}, _iso(now)),
            _event("backfill_with_refs_total", {"count": 2}, _iso(now)),
            _event("binding_suggest_invoked_total", {"count": 1}, _iso(now)),
            _event("drift_invoked_total", {"count": 1}, _iso(now)),
            _event("vector_search_invoked_total", {"count": 1}, _iso(now)),
        ])

        result = runner.invoke(main, ["metrics", "summary", "--domain", "backfill"])

        assert result.exit_code == 0, result.output
        # The 2 backfill counters MUST appear in the output.
        assert "backfill_observations_total" in result.output
        assert "backfill_with_refs_total" in result.output
        # Other-domain counters MUST be excluded.
        assert "binding_suggest_invoked_total" not in result.output
        assert "drift_invoked_total" not in result.output
        assert "vector_search_invoked_total" not in result.output

    def test_metrics_summary_with_domain_filter_engine(
        self, metrics_path: Path,
    ) -> None:
        """`--domain=engine` succeeds with empty filter result (RESERVED slot).

        The engine domain is RESERVED per REQ-42 (deferred to v1.1). v1
        emits no ``engine_*`` counters, so the filter result is empty.
        The command exits 0 (not an error) and renders the filter-empty
        contract text per T1.8 (D8/D9 case 4).
        """
        now = datetime.now(UTC)
        _write_jsonl(metrics_path, [
            _event("binding_suggest_invoked_total", {"count": 1}, _iso(now)),
            _event("drift_invoked_total", {"count": 1}, _iso(now)),
            _event("vector_search_invoked_total", {"count": 1}, _iso(now)),
        ])

        result = runner.invoke(main, ["metrics", "summary", "--domain", "engine"])

        assert result.exit_code == 0, result.output
        # No engine_* counters exist in v1 — the domain filter excludes
        # every event. T1.8 contract: empty summary after filtering emits
        # "No metrics in window/domain." (filter-empty, NOT the
        # missing/empty-file case).
        assert "No metrics in window/domain." in result.output

    def test_metrics_summary_with_invalid_domain_exits_2_with_helpful_message(
        self, metrics_path: Path,
    ) -> None:
        """Invalid --domain exits 2 with a helpful error message.

        Tests the path where click.Choice rejects the value BEFORE the
        handler runs (no fallback through validate_domain needed).
        """
        result = runner.invoke(
            main, ["metrics", "summary", "--domain", "garbage"],
        )

        assert result.exit_code == 2, result.output
        # The error message must mention the invalid value AND list at
        # least one of the valid domains so the operator can self-correct.
        # click's UsageError renders to stderr; the merged output
        # contains the message in both stdout + stderr streams.
        combined = result.output
        assert "garbage" in combined
        assert "binding" in combined  # any valid domain reference