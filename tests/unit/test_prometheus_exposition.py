"""Unit tests for the Prometheus textfile exposition formatter (REQ-38 / D6).

Covers ``observability.prometheus_exposition()`` + ``PrometheusMetric`` +
``write_prometheus_textfile()`` — the REQ-38 / D6 helpers that PR#2 T2.1
lands on top of the PR#1 placeholder.

Behaviour per design D6:
- Type derivation, applied IN ORDER:
  1. ``METRIC_TYPE_OVERRIDES[name]`` if present (forward-compatible hook;
     v1 has zero overrides).
  2. Suffix ``_total`` → ``counter``.
  3. Suffix ``_ms`` or ``_seconds`` → ``summary``.
  4. Bare name → ``gauge``.
- One ``# HELP <name> ...`` + ``# TYPE <name> <type>`` pair per distinct
  counter; metric lines below.
- Multiple events with the same ``(name, label_tuple)`` pair are SUMMED into
  one cumulative value (mirrors the existing ``_summarize_metrics``
  semantics at ``cli.py:960``).
- Label values are escaped: ``"`` → ``\\"``, ``\\`` → ``\\\\``, ``\\n`` →
  literal ``\\\\n`` (backslash-n) per Prometheus textfile convention.
- Counter name → Prometheus name mapping: ``<prefix><counter_name>``
  (default prefix ``"flow_"``). Defensive ``_total_total`` → ``_total``
  collapse for the v1.1 future-proofing case.
- Empty input → ``"# EOF\\n"`` (Prometheus convention for empty textfile).

Tests are written BEFORE the implementation per strict TDD (RED → GREEN →
REFACTOR). The fixture format is the v0.6.0 JSONL event shape:
``{"name", "fields", "ts"}`` where ``ts`` is an ISO-8601 UTC string with a
``Z`` suffix.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flow_engineering import observability

# ---------- helpers ----------


def _write_jsonl(path: Path, events: list[dict]) -> None:
    """Write a JSONL sink file with the given events (one per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")))
            fh.write("\n")


def _event(
    name: str,
    fields: dict | None = None,
    ts: str = "2026-06-27T00:00:00Z",
) -> observability.MetricEvent:
    """Build a single ``MetricEvent`` for prometheus_exposition tests."""
    return observability.MetricEvent(
        timestamp=datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        .replace(tzinfo=UTC)
        .timestamp(),
        counter_name=name,
        labels=fields or {},
        raw_line=json.dumps(
            {"name": name, "fields": fields or {}, "ts": ts},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    )


# ---------- prometheus_exposition: HELP + TYPE ----------


class TestPrometheusExpositionHelpAndType:
    """prometheus_exposition emits ``# HELP`` + ``# TYPE`` per counter."""

    def test_prometheus_exposition_includes_help_and_type_comments(self) -> None:
        """Single counter produces ``# HELP`` + ``# TYPE`` + metric line."""
        events = [_event("suggest_invoked_total", {"count": 1})]

        text = observability.prometheus_exposition(events)

        assert "# HELP flow_suggest_invoked_total" in text
        assert "# TYPE flow_suggest_invoked_total counter" in text
        assert "flow_suggest_invoked_total 1.0" in text

    def test_prometheus_exposition_help_appears_before_type(self) -> None:
        """``# HELP`` MUST appear before ``# TYPE`` (Prometheus spec)."""
        events = [_event("snapshot_create_total", {"count": 3})]

        text = observability.prometheus_exposition(events)

        help_idx = text.index("# HELP flow_snapshot_create_total")
        type_idx = text.index("# TYPE flow_snapshot_create_total counter")
        assert help_idx < type_idx, (
            f"# HELP must precede # TYPE; got help@{help_idx}, type@{type_idx}"
        )

    def test_prometheus_exposition_emits_one_help_type_pair_per_counter(self) -> None:
        """Distinct counter names each get exactly one HELP+TYPE pair."""
        events = [
            _event("suggest_invoked_total", {"count": 1}),
            _event("snapshot_create_total", {"count": 2}),
            _event("drift_invoked_total", {"count": 3}),
        ]

        text = observability.prometheus_exposition(events)

        assert text.count("# HELP") == 3
        assert text.count("# TYPE") == 3
        assert "# HELP flow_suggest_invoked_total" in text
        assert "# HELP flow_snapshot_create_total" in text
        assert "# HELP flow_drift_invoked_total" in text


# ---------- prometheus_exposition: counter value emission ----------


class TestPrometheusExpositionCounterValues:
    """prometheus_exposition emits correct numeric values for counter lines."""

    def test_prometheus_exposition_emits_counter_lines_with_correct_values(self) -> None:
        """Count field becomes the metric line value (formatted as float)."""
        events = [
            _event("snapshot_prune_total", {"count": 7}),
            _event("drift_invoked_total", {"count": 1, "change": "observability"}),
        ]

        text = observability.prometheus_exposition(events)

        assert "flow_snapshot_prune_total 7.0" in text
        # Labels are emitted in sorted key order (change first alphabetically).
        assert 'flow_drift_invoked_total{change="observability"} 1.0' in text

    def test_prometheus_exposition_defaults_count_to_one_when_missing(self) -> None:
        """Events without a ``count`` field default to 1.0 (mirrors PR#1)."""
        events = [_event("suggest_invoked_total", {"trigger": "cli"})]

        text = observability.prometheus_exposition(events)

        assert 'flow_suggest_invoked_total{trigger="cli"} 1.0' in text

    def test_prometheus_exposition_renders_non_numeric_count_as_one(self) -> None:
        """Non-numeric ``count`` values fall back to 1.0 (defensive)."""
        events = [_event("snapshot_create_total", {"count": "not-a-number"})]

        text = observability.prometheus_exposition(events)

        assert "flow_snapshot_create_total 1.0" in text


# ---------- prometheus_exposition: labels ----------


class TestPrometheusExpositionLabels:
    """prometheus_exposition handles labels correctly."""

    def test_prometheus_exposition_handles_labels_correctly(self) -> None:
        """Label keys are sorted alphabetically; values are quoted."""
        events = [
            _event("drift_invoked_total", {"change": "observability", "kind": "scan"}),
        ]

        text = observability.prometheus_exposition(events)

        # ``change`` sorts before ``kind`` alphabetically.
        assert (
            'flow_drift_invoked_total{change="observability",kind="scan"} 1.0'
            in text
        )

    def test_prometheus_exposition_escapes_label_values(self) -> None:
        """Quotes/backslashes/newlines are escaped per Prometheus spec."""
        events = [
            _event(
                "drift_invoked_total",
                {
                    "trigger": 'value with "quote"',
                    "path": "C:\\Users\\insyd",
                    "msg": "line1\nline2",
                },
            ),
        ]

        text = observability.prometheus_exposition(events)

        assert 'trigger="value with \\"quote\\""' in text
        assert 'path="C:\\\\Users\\\\insyd"' in text
        assert 'msg="line1\\nline2"' in text

    def test_prometheus_exposition_no_labels_emits_bare_metric_line(self) -> None:
        """Empty labels → bare metric line (no ``{}`` block)."""
        events = [_event("snapshot_create_total", {})]

        text = observability.prometheus_exposition(events)

        assert "flow_snapshot_create_total 1.0" in text
        assert "flow_snapshot_create_total{}" not in text

    def test_prometheus_exposition_excludes_aggregated_count_keys_from_labels(self) -> None:
        """``count`` / ``elapsed_ms`` / ``value`` are value-carriers, NOT labels."""
        events = [
            _event(
                "drift_invoked_total",
                {"change": "observability", "count": 1, "elapsed_ms": 50},
            ),
        ]

        text = observability.prometheus_exposition(events)

        # Only ``change`` is rendered as a label.
        assert 'flow_drift_invoked_total{change="observability"} 1.0' in text
        assert "count=" not in text
        assert "elapsed_ms=" not in text


# ---------- prometheus_exposition: prefix ----------


class TestPrometheusExpositionPrefix:
    """prometheus_exposition honors the ``prefix`` kwarg."""

    def test_prometheus_exposition_uses_correct_prefix(self) -> None:
        """Default prefix ``flow_`` is prepended to every counter name."""
        events = [_event("suggest_invoked_total", {"count": 1})]

        text = observability.prometheus_exposition(events)

        assert "flow_suggest_invoked_total" in text
        # Raw name (without prefix) MUST NOT appear as a metric name.
        assert "\nsuggest_invoked_total " not in text
        assert "\nsuggest_invoked_total\n" not in text

    def test_prometheus_exposition_custom_prefix_is_respected(self) -> None:
        """A caller-supplied prefix overrides the default ``flow_``."""
        events = [_event("suggest_invoked_total", {"count": 1})]

        text = observability.prometheus_exposition(events, prefix="myapp_")

        assert "myapp_suggest_invoked_total" in text
        assert "flow_suggest_invoked_total" not in text

    def test_prometheus_exposition_empty_prefix_drops_prefix(self) -> None:
        """``prefix=""`` is the escape hatch to skip prefixing entirely."""
        events = [_event("snapshot_create_total", {"count": 2})]

        text = observability.prometheus_exposition(events, prefix="")

        assert "snapshot_create_total 2.0" in text
        assert "flow_snapshot_create_total" not in text

    def test_prometheus_exposition_collapses_double_total_suffix(self) -> None:
        """Defensive normalization: ``flow_<name>_total_total`` → ``flow_<name>_total``."""
        # Pass a counter name that, after prefixing, would yield _total_total.
        events = [_event("foo_total", {"count": 1})]

        text = observability.prometheus_exposition(events)

        assert "flow_foo_total 1.0" in text
        assert "flow_foo_total_total" not in text


# ---------- prometheus_exposition: empty + aggregation ----------


class TestPrometheusExpositionEmptyAndAggregation:
    """prometheus_exposition handles empty input + aggregates cumulative values."""

    def test_prometheus_exposition_handles_empty_events(self) -> None:
        """Empty input → ``# EOF\\n`` per Prometheus convention."""
        text = observability.prometheus_exposition([])

        assert text == "# EOF\n"

    def test_prometheus_exposition_aggregates_multiple_events_to_cumulative_value(
        self,
    ) -> None:
        """Multiple events with same name+labels → summed into one line."""
        events = [
            _event("snapshot_prune_total", {"count": 2}),
            _event("snapshot_prune_total", {"count": 3}),
            _event("snapshot_prune_total", {"count": 5}),
        ]

        text = observability.prometheus_exposition(events)

        # Cumulative value = 2 + 3 + 5 = 10.
        assert "flow_snapshot_prune_total 10.0" in text
        # Only ONE cumulative metric line for this counter (not three).
        assert text.count("flow_snapshot_prune_total 10.0") == 1
        # Exactly one HELP + one TYPE comment for this counter.
        assert text.count("# HELP flow_snapshot_prune_total") == 1
        assert text.count("# TYPE flow_snapshot_prune_total") == 1

    def test_prometheus_exposition_groups_by_label_tuple(self) -> None:
        """Events with same name + DIFFERENT labels → separate lines."""
        events = [
            _event("drift_invoked_total", {"count": 1, "change": "a"}),
            _event("drift_invoked_total", {"count": 2, "change": "b"}),
            _event("drift_invoked_total", {"count": 3, "change": "a"}),
        ]

        text = observability.prometheus_exposition(events)

        # Same (name, change="a") group → summed (1 + 3 = 4).
        assert 'flow_drift_invoked_total{change="a"} 4.0' in text
        assert 'flow_drift_invoked_total{change="b"} 2.0' in text


# ---------- prometheus_exposition: type derivation ----------


class TestPrometheusExpositionTypeDerivation:
    """prometheus_exposition derives metric type from counter name suffix."""

    def test_prometheus_exposition_total_suffix_emits_counter(self) -> None:
        """Counter name ending in ``_total`` → ``counter`` type."""
        events = [_event("snapshot_create_total", {"count": 1})]

        text = observability.prometheus_exposition(events)

        assert "# TYPE flow_snapshot_create_total counter" in text

    def test_prometheus_exposition_ms_suffix_emits_summary(self) -> None:
        """Counter name ending in ``_ms`` → ``summary`` type (D6 priority 3)."""
        events = [_event("vector_search_latency_ms", {"elapsed_ms": 50})]

        text = observability.prometheus_exposition(events)

        assert "# TYPE flow_vector_search_latency_ms summary" in text

    def test_prometheus_exposition_seconds_suffix_emits_summary(self) -> None:
        """Counter name ending in ``_seconds`` → ``summary`` type (D6 priority 3)."""
        events = [_event("reindex_duration_seconds", {"value": 1.5})]

        text = observability.prometheus_exposition(events)

        assert "# TYPE flow_reindex_duration_seconds summary" in text

    def test_prometheus_exposition_bare_name_emits_gauge(self) -> None:
        """Bare counter name (no recognised suffix) → ``gauge`` type."""
        events = [_event("vector_index_size_observations", {"value": 42})]

        text = observability.prometheus_exposition(events)

        assert "# TYPE flow_vector_index_size_observations gauge" in text


# ---------- PrometheusMetric dataclass ----------


class TestPrometheusMetricDataclass:
    """PrometheusMetric is a frozen dataclass with the contract fields."""

    def test_prometheus_metric_dataclass_round_trip(self) -> None:
        """PrometheusMetric round-trips its declared fields."""
        m = observability.PrometheusMetric(
            name="flow_suggest_invoked_total",
            value=3.0,
            metric_type="counter",
            help_text="flow-engineering counter flow_suggest_invoked_total",
            labels={"trigger": "cli"},
        )

        assert m.name == "flow_suggest_invoked_total"
        assert m.value == 3.0
        assert m.metric_type == "counter"
        assert m.help_text == "flow-engineering counter flow_suggest_invoked_total"
        assert m.labels == {"trigger": "cli"}

    def test_prometheus_metric_is_frozen(self) -> None:
        """PrometheusMetric MUST be frozen (TDD: spec says ``frozen=True``)."""
        m = observability.PrometheusMetric(
            name="flow_x_total",
            value=1.0,
            metric_type="counter",
            help_text="x",
        )

        with pytest.raises((AttributeError, TypeError)):
            m.name = "other"  # type: ignore[misc]

    def test_prometheus_metric_labels_default_to_empty_dict(self) -> None:
        """``labels`` defaults to ``{}`` (no labels case)."""
        m = observability.PrometheusMetric(
            name="flow_x_total",
            value=1.0,
            metric_type="counter",
            help_text="x",
        )

        assert m.labels == {}


# ---------- write_prometheus_textfile ----------


class TestWritePrometheusTextfile:
    """write_prometheus_textfile writes content atomically to disk."""

    def test_write_prometheus_textfile_writes_atomically(
        self, tmp_path: Path,
    ) -> None:
        """write_prometheus_textfile writes the content to the target path."""
        target = tmp_path / "metrics.prom"
        content = "# HELP flow_x_total\n# TYPE flow_x_total counter\nflow_x_total 1.0\n"

        observability.write_prometheus_textfile(content, target)

        assert target.exists()
        assert target.read_text(encoding="utf-8") == content

    def test_write_prometheus_textfile_creates_parent_directory(
        self, tmp_path: Path,
    ) -> None:
        """Missing parent dir is created on demand (D10 contract)."""
        target = tmp_path / "nested" / "subdir" / "metrics.prom"
        content = "# EOF\n"

        observability.write_prometheus_textfile(content, target)

        assert target.exists()
        assert target.read_text(encoding="utf-8") == content

    def test_write_prometheus_textfile_replaces_existing_file(
        self, tmp_path: Path,
    ) -> None:
        """Atomic write replaces existing content without half-write."""
        target = tmp_path / "metrics.prom"
        target.write_text("OLD CONTENT", encoding="utf-8")
        new_content = "# NEW\n"

        observability.write_prometheus_textfile(new_content, target)

        assert target.read_text(encoding="utf-8") == new_content

    def test_write_prometheus_textfile_no_tmp_orphan_leftovers(
        self, tmp_path: Path,
    ) -> None:
        """No ``.tmp`` files are left behind on success (D10 cleanup)."""
        target = tmp_path / "metrics.prom"
        observability.write_prometheus_textfile("# EOF\n", target)

        leftovers = list(target.parent.glob("*.tmp"))
        leftovers += list(target.parent.glob(".metrics-*"))
        assert leftovers == [], f"unexpected tmp leftovers: {leftovers}"


# ---------- round-trip stable output ----------


class TestPrometheusExpositionStableOutput:
    """prometheus_exposition output is deterministic across calls."""

    def test_prometheus_exposition_is_deterministic_for_same_input(self) -> None:
        """Two calls with the same input produce byte-identical output."""
        events = [
            _event("drift_invoked_total", {"count": 1, "change": "observability"}),
            _event("snapshot_create_total", {"count": 2}),
            _event("vector_search_latency_ms", {"elapsed_ms": 50}),
        ]

        first = observability.prometheus_exposition(events)
        second = observability.prometheus_exposition(events)

        assert first == second

    def test_prometheus_exposition_counters_sorted_alphabetically(self) -> None:
        """Counters appear in alphabetical order in the output (stable)."""
        events = [
            _event("snapshot_create_total", {"count": 1}),
            _event("drift_invoked_total", {"count": 1}),
            _event("binding_total", {"count": 1}),
        ]

        text = observability.prometheus_exposition(events)

        binding_idx = text.index("flow_binding_total")
        drift_idx = text.index("flow_drift_invoked_total")
        snapshot_idx = text.index("flow_snapshot_create_total")
        assert binding_idx < drift_idx < snapshot_idx

    def test_prometheus_exposition_line_shape_is_valid(self) -> None:
        """Every metric line matches ``^<name>(\\{<labels>\\})? <value>$``."""
        events = [
            _event("suggest_invoked_total", {"count": 1}),
            _event("drift_invoked_total", {"count": 1, "change": "obs"}),
        ]

        text = observability.prometheus_exposition(events)
        lines = [
            line
            for line in text.splitlines()
            if line and not line.startswith("#")
        ]

        pattern = re.compile(
            r"^[a-zA-Z_][a-zA-Z0-9_]*(\{[^}]*\})? -?\d+(\.\d+)?$"
        )
        for line in lines:
            assert pattern.match(line), (
                f"line {line!r} does not match Prometheus metric line shape"
            )
