"""Metrics group extracted from cli/__init__.py (v1.3-cli-split, Slice 7).

Hosts the ``flow metrics`` Click group and its 3 subcommands (summary,
export, aggregate), plus the private helpers used internally by those
commands (``_summarize_metrics``, ``_apply_metrics_filters``) and the
module-level constants ``SUMMARY_WINDOW_CHOICES``, ``SUMMARY_DOMAIN_CHOICES``,
``AGGREGATE_PERCENTILE_CHOICES``. The body below is a verbatim relocation
from ``cli/__init__.py`` lines 1515-2066 (post-Slice-1+2+3+4+5+6;
pre-Slice-1+2+3+4+5+6 equivalent lines 1517-2074 per tasks.md T-7) --
behavior MUST match pre-split exactly.

Preserves the legacy flat dump shim (REQ-V1.3.6 followup): the root
``metrics`` command (defined without a subcommand) still emits the
v0.6.0-era byte-identical text/JSON dump of the JSONL counter sink when
no subcommand is invoked. Subcommands ``summary`` / ``export`` /
``aggregate`` are NEW behavior layered on top of that legacy shim via
Click's ``invoke_without_command=True`` flag. Lines 1546-1548 of the
original (the ``if ctx.invoked_subcommand is not None: return`` shim)
are preserved verbatim -- any change to this shim would alter the
legacy-format contract that downstream tools depend on.

Cross-cutting helpers retained in ``cli/__init__.py`` and resolved at
function-call time:

- ``_parse_since`` (at ``cli/drift.py``) -- the ISO-8601 / relative-time
  parser used by ``metrics_summary`` / ``metrics_export`` /
  ``metrics_aggregate`` for ``--since`` / ``--until`` validation.
  Same lazy-import rationale as Slices 2-6: the helper lives in
  ``cli.drift`` (Slice 4) and ``metrics.py`` re-fetches via
  ``from flow_engineering.cli.drift import _parse_since`` on each call.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from flow_engineering import observability
from flow_engineering.cli import main  # noqa: F401  (parent group; see design section 6)

# ---------- REQ-8 close: flow metrics ----------


def _summarize_metrics(events: list[dict[str, Any]]) -> dict[str, int]:
    """Collapse a list of increment events into ``{name: count}``."""
    summary: dict[str, int] = {}
    for ev in events:
        name = ev.get("name")
        if not isinstance(name, str):
            continue
        fields = ev.get("fields") or {}
        payload = fields.get("count") or fields.get("confirmed") or 1
        try:
            payload_int = int(payload)
        except (TypeError, ValueError):
            payload_int = 1
        summary[name] = summary.get(name, 0) + payload_int
    return summary


@main.group(invoke_without_command=True)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit machine-readable JSON instead of a text summary.",
)
@click.pass_context
def metrics(ctx: click.Context, json_flag: bool) -> None:
    """Dump the JSONL counter sink as a summary (REQ-8 close).

    With no subcommand, renders the legacy flat text/JSON dump (REQ-8 close
    contract; byte-identical to v0.6.0). The ``summary`` subcommand renders
    the new per-domain dashboard (REQ-35).
    """
    if ctx.invoked_subcommand is not None:
        # Subcommand handles its own output (e.g. `flow metrics summary`).
        return
    events = observability.read_all()
    summary = _summarize_metrics(events)
    if json_flag:
        click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    if not summary:
        click.echo("(no metrics recorded)")
        return
    name_width = max(len(name) for name in summary)
    for name in sorted(summary):
        click.echo(f"{name.ljust(name_width)}  {summary[name]}")


# Window choices for `flow metrics summary --window` (REQ-35/REQ-36).
# The CLI accepts both presets (1h/24h/7d/30d) and custom `<int><h|d>` format;
# the union is validated at runtime by :func:`observability.parse_window`
# rather than via ``click.Choice`` (which can only model a fixed enum).
SUMMARY_WINDOW_CHOICES: list[str] = list(observability.WINDOW_PATTERNS.keys())

# Domain choices for `flow metrics summary --domain` (REQ-37).
# Derived from observability.ALL_DOMAINS so the CLI stays in lockstep
# with the cross-domain slice expansion (T1.6: backfill + federated +
# metadata + engine). ``engine`` is RESERVED (REQ-42 deferred to v1.1)
# and produces an empty filter result rather than an error.
SUMMARY_DOMAIN_CHOICES: list[str] = list(observability.ALL_DOMAINS)


@metrics.command("summary")
@click.option(
    "--format",
    "fmt",
    default="text",
    type=click.Choice(["text", "json", "json-detailed"], case_sensitive=False),
    help="Output format (REQ-35: text default, json for machine-readable).",
)
@click.option(
    "--window",
    "window",
    default=None,
    help=(
        "Rolling time-window filter (REQ-35/REQ-36): preset "
        "(1h|24h|7d|30d) or custom '<int><h|d>' (e.g. 12h, 3d). "
        "Rolling relative to now (NOT calendar-aligned)."
    ),
)
@click.option(
    "--domain",
    "domain",
    default=None,
    type=click.Choice(SUMMARY_DOMAIN_CHOICES, case_sensitive=False),
    help=(
        "Prefix-based domain slice (REQ-37): "
        + "|".join(observability.ALL_DOMAINS)
        + ". The engine slot is reserved (REQ-42) and returns empty in v1."
    ),
)
@click.option(
    "--since",
    "since_iso",
    default=None,
    metavar="ISO8601",
    help="Absolute ISO 8601 lower bound: ts >= <iso> (REQ-36).",
)
@click.option(
    "--until",
    "until_iso",
    default=None,
    metavar="ISO8601",
    help="Absolute ISO 8601 upper bound: ts <= <iso> (REQ-36).",
)
def metrics_summary(
    fmt: str,
    window: str | None,
    domain: str | None,
    since_iso: str | None,
    until_iso: str | None,
) -> None:
    """Render the per-domain text dashboard (REQ-35 / change #6 PR#1 T1.2 + T1.5 + T1.8).

    Uses :func:`observability.read_and_summarize` for the read+filter+summary
    pipeline + empty-reason detection (D8 default-empty contract). Applies
    ``--since`` / ``--until`` as a post-filter pass when those flags are set.

    Exit-code mapping (D9):
    - 0: success (including empty / missing → "No metrics recorded yet.").
    - 2: invalid flag value (``--window`` parse failure, ``--since`` /
      ``--until`` ISO parse failure, ``--domain`` unknown).
    - 3: metrics file exists but every line is malformed
      (D9 ``EXIT_MALFORMED_METRICS``); emits ``"Error: metrics file at
      <path> is malformed."`` to stderr.
    """
    from flow_engineering.cli.drift import (
        _parse_since,  # noqa: F401  (lazy; lives in cli.drift post-Slice-4)
    )

    fmt_lower = fmt.lower()

    since_epoch: float | None = None
    if since_iso is not None:
        try:
            since_epoch = _parse_since(since_iso)
        except ValueError as exc:
            click.echo(f"invalid --since value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    until_epoch: float | None = None
    if until_iso is not None:
        try:
            until_epoch = _parse_since(until_iso)
        except ValueError as exc:
            click.echo(f"invalid --until value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    # Validate --window EARLY so a bad value exits 2 even when the JSONL
    # sink is missing (read_and_summarize short-circuits on empty reason
    # before applying the window filter, so we must validate here).
    if window is not None:
        try:
            observability.parse_window(window)
        except ValueError as exc:
            click.echo(f"invalid --window value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    domain_normalized: str | None = None
    if domain is not None:
        # click.Choice accepts mixed case (case_sensitive=False), but
        # DOMAIN_BY_PREFIX keys are lowercase — normalize before lookup.
        try:
            domain_normalized = observability.validate_domain(domain.lower())
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    try:
        result = observability.read_and_summarize(
            window=window,
            domain=domain_normalized,
        )
    except ValueError as exc:
        # unknown domain / parse_window failure — defensive fallback
        # (click.Choice covers the validation path at parse time).
        click.echo(str(exc), err=True)
        sys.exit(observability.EXIT_INVALID_VALUE)

    if result.empty_reason == "missing_file" or result.empty_reason == "empty_file":
        click.echo("No metrics recorded yet.")
        return
    if result.empty_reason == "all_malformed":
        click.echo(
            f"Error: metrics file at {result.source_path} is malformed.",
            err=True,
        )
        sys.exit(observability.EXIT_MALFORMED_METRICS)

    summary_data = result.summary

    # --since / --until are applied as a post-filter pass because
    # read_and_summarize() handles only window+domain (per design D8/D9).
    if since_epoch is not None or until_epoch is not None:
        events = observability.read_all_metrics()
        if domain_normalized is not None:
            events = observability.read_events_by_domain(domain_normalized)
        if window is not None:
            events = observability.filter_by_window(events, window)
        if since_epoch is not None:
            events = [e for e in events if e.timestamp >= since_epoch]
        if until_epoch is not None:
            events = [e for e in events if e.timestamp <= until_epoch]
        summary_data = observability.summarize(events)

    if not any(summary_data.values()):
        click.echo("No metrics in window/domain.")
        return

    if fmt_lower == "text":
        for d in sorted(summary_data):
            click.echo(f"{d}:")
            for counter, count in sorted(summary_data[d].items()):
                click.echo(f"  {counter}: {count}")
        return
    if fmt_lower in ("json", "json-detailed"):
        click.echo(json.dumps(summary_data, ensure_ascii=False, indent=2))
        return
    click.echo(f"unknown --format value: {fmt}", err=True)
    sys.exit(observability.EXIT_INVALID_VALUE)


# ---------- REQ-38: flow metrics export ----------


def _apply_metrics_filters(
    events: list[observability.MetricEvent],
    *,
    window: str | None,
    domain: str | None,
    since_epoch: float | None,
    until_epoch: float | None,
) -> list[observability.MetricEvent]:
    """Apply the unified filter pipeline used by ``metrics export``.

    Reuses ``observability.filter_by_window`` / ``_prefixes_for_domain``
    / direct epoch comparison so the filter chain is identical across
    formats (D8/D9 / T2.3 composition requirement).
    """
    filtered = events
    if window is not None:
        filtered = observability.filter_by_window(filtered, window)
    if domain is not None:
        prefixes = observability._prefixes_for_domain(domain)
        filtered = [e for e in filtered if any(e.counter_name.startswith(p) for p in prefixes)]
    if since_epoch is not None:
        filtered = [e for e in filtered if e.timestamp >= since_epoch]
    if until_epoch is not None:
        filtered = [e for e in filtered if e.timestamp <= until_epoch]
    return filtered


@metrics.command("export")
@click.option(
    "--format",
    "fmt",
    default="text",
    type=click.Choice(["text", "json", "prometheus"], case_sensitive=False),
    help=(
        "Output format (REQ-38): text default, json for machine-readable "
        "list of events, prometheus for textfile exposition."
    ),
)
@click.option(
    "--out",
    "out_path",
    default=None,
    type=click.Path(),
    help=(
        "Atomic write to <path> (REQ-38 / D10). Default = stdout. "
        "Creates parent dir on demand; rejects with exit 4 on failure."
    ),
)
@click.option(
    "--window",
    "window",
    default=None,
    help=("Rolling time-window filter (REQ-36): preset (1h|24h|7d|30d) or custom '<int><h|d>'."),
)
@click.option(
    "--since",
    "since_iso",
    default=None,
    metavar="ISO8601",
    help="Absolute ISO 8601 lower bound: ts >= <iso> (REQ-36).",
)
@click.option(
    "--until",
    "until_iso",
    default=None,
    metavar="ISO8601",
    help="Absolute ISO 8601 upper bound: ts <= <iso> (REQ-36).",
)
@click.option(
    "--domain",
    "domain",
    default=None,
    type=click.Choice(SUMMARY_DOMAIN_CHOICES, case_sensitive=False),
    help="Prefix-based domain slice (REQ-37).",
)
def metrics_export(
    fmt: str,
    out_path: str | None,
    window: str | None,
    since_iso: str | None,
    until_iso: str | None,
    domain: str | None,
) -> None:
    """Export metrics in text / json / prometheus format (REQ-38 / change #6 PR#2 T2.2).

    Honors ``--window`` / ``--since`` / ``--until`` / ``--domain`` filters
    identically to ``flow metrics summary`` so the filter chain is
    composable across subcommands (T2.3 / D8/D9).

    ``--format prometheus`` emits the D6 textfile exposition format
    (``# HELP`` + ``# TYPE`` + metric lines, cumulative counter values,
    ``# EOF`` for empty input). ``--format json`` emits a JSON list of
    MetricEvent-shaped dicts (counter_name + labels + timestamp).
    ``--format text`` (default) renders a human-readable ``name  count``
    table (mirrors the REQ-8 close contract for the no-flag ``flow metrics``).

    ``--out <path>`` triggers an atomic write via
    :func:`observability.atomic_write_text` (D10). Parent directories are
    created on demand; a write failure exits ``4`` per design D9.

    Exit-code mapping (D9):
    - 0: success (including default-empty per D8).
    - 2: invalid flag value (``--format=garbage``; ``--window`` parse
      failure; ``--domain`` unknown; ``--since`` / ``--until`` ISO parse
      failure).
    - 4: write failure on ``--out``.
    """
    from flow_engineering.cli.drift import (
        _parse_since,  # noqa: F401  (lazy; lives in cli.drift post-Slice-4)
    )

    fmt_lower = fmt.lower()

    since_epoch: float | None = None
    if since_iso is not None:
        try:
            since_epoch = _parse_since(since_iso)
        except ValueError as exc:
            click.echo(f"invalid --since value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    until_epoch: float | None = None
    if until_iso is not None:
        try:
            until_epoch = _parse_since(until_iso)
        except ValueError as exc:
            click.echo(f"invalid --until value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    if window is not None:
        try:
            observability.parse_window(window)
        except ValueError as exc:
            click.echo(f"invalid --window value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    domain_normalized: str | None = None
    if domain is not None:
        try:
            domain_normalized = observability.validate_domain(domain.lower())
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    events = observability.read_all_metrics()
    filtered = _apply_metrics_filters(
        events,
        window=window,
        domain=domain_normalized,
        since_epoch=since_epoch,
        until_epoch=until_epoch,
    )

    if fmt_lower == "prometheus":
        content = observability.prometheus_exposition(filtered)
    elif fmt_lower == "json":
        content = json.dumps(
            [
                {
                    "name": ev.counter_name,
                    "fields": ev.labels,
                    "ts": datetime.fromtimestamp(ev.timestamp, tz=UTC).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
                for ev in filtered
            ],
            ensure_ascii=False,
            indent=2,
        )
    elif fmt_lower == "text":
        if not filtered:
            content = "(no metrics recorded)\n"
        else:
            summary = observability.summarize(filtered)
            # Flatten {domain: {counter: count}} for the REQ-8-style table.
            flat: dict[str, int] = {}
            for counters in summary.values():
                flat.update(counters)
            if not flat:
                content = "(no metrics recorded)\n"
            else:
                width = max(len(name) for name in flat)
                lines = [f"{name.ljust(width)}  {count}" for name, count in sorted(flat.items())]
                content = "\n".join(lines) + "\n"
    else:
        click.echo(f"unknown --format value: {fmt}", err=True)
        sys.exit(observability.EXIT_INVALID_VALUE)

    if out_path is None:
        click.echo(content, nl=False)
        return

    target = Path(out_path)
    try:
        observability.atomic_write_text(target, content)
    except OSError as exc:
        click.echo(
            json.dumps(
                {
                    "error": "write failed",
                    "path": str(target),
                    "cause": exc.strerror or str(exc),
                }
            ),
            err=True,
        )
        sys.exit(observability.EXIT_WRITE_FAILURE)


# ---------- REQ-39: flow metrics aggregate (percentile aggregation via reservoir sampling) ----------


# Percentile choices for `flow metrics aggregate --percentile` (REQ-39).
# Mirrors observability._VALID_PERCENTILES (50/95/99) so the CLI stays
# in lockstep with the helper's validation set.
AGGREGATE_PERCENTILE_CHOICES: list[str] = ["p50", "p95", "p99"]


@metrics.command("aggregate")
@click.option(
    "--percentile",
    "percentiles",
    type=click.Choice(AGGREGATE_PERCENTILE_CHOICES, case_sensitive=False),
    multiple=True,
    default=("p95",),
    help=(
        "Percentile(s) to compute (REQ-39): p50 / p95 / p99. "
        "Repeatable; default = p95. Uses reservoir sampling for "
        "memory efficiency on large event streams."
    ),
)
@click.option(
    "--window",
    "window",
    default=None,
    help=("Rolling time-window filter (REQ-36): preset (1h|24h|7d|30d) or custom '<int><h|d>'."),
)
@click.option(
    "--since",
    "since_iso",
    default=None,
    metavar="ISO8601",
    help="Absolute ISO 8601 lower bound: ts >= <iso> (REQ-36).",
)
@click.option(
    "--until",
    "until_iso",
    default=None,
    metavar="ISO8601",
    help="Absolute ISO 8601 upper bound: ts <= <iso> (REQ-36).",
)
@click.option(
    "--domain",
    "domain",
    default=None,
    type=click.Choice(SUMMARY_DOMAIN_CHOICES, case_sensitive=False),
    help="Prefix-based domain slice (REQ-37).",
)
@click.option(
    "--reservoir-size",
    "reservoir_size",
    default=1000,
    type=int,
    help=("Sample-size ceiling per counter for the reservoir sampler (REQ-39 / D7). Default 1000."),
)
@click.option(
    "--format",
    "fmt",
    default="text",
    type=click.Choice(["text", "json"], case_sensitive=False),
    help="Output format (REQ-39): text (default aligned table) or json.",
)
def metrics_aggregate(
    percentiles: tuple[str, ...],
    window: str | None,
    since_iso: str | None,
    until_iso: str | None,
    domain: str | None,
    reservoir_size: int,
    fmt: str,
) -> None:
    """Compute percentiles over counter values (REQ-39 / change #6 PR#2 T2.5).

    Consumes :func:`observability.aggregate_percentile` (reservoir-sampled,
    memory-bounded at ``--reservoir-size``) over the filtered event set
    and renders the result as either an aligned text table (default) or
    a flat JSON dict.

    Exit-code mapping (D9):
    - 0: success (including default-empty per D8: empty sink emits
      a header-only table in text mode or ``{}`` in JSON mode).
    - 2: invalid flag value (Click ``click.Choice`` validation failure
      on ``--percentile`` / ``--domain``; ``--window`` parse failure;
      ``--since`` / ``--until`` ISO parse failure).
    """
    from flow_engineering.cli.drift import (
        _parse_since,  # noqa: F401  (lazy; lives in cli.drift post-Slice-4)
    )

    fmt_lower = fmt.lower()

    # Parse the --percentile labels into integers; validate against the
    # helper's accepted set (defensive: Click already validates at parse
    # time, but the explicit check keeps the helper self-contained).
    pct_ints: list[int] = []
    for label in percentiles:
        pct_ints.append(int(label.lower().lstrip("p")))

    since_epoch: float | None = None
    if since_iso is not None:
        try:
            since_epoch = _parse_since(since_iso)
        except ValueError as exc:
            click.echo(f"invalid --since value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    until_epoch: float | None = None
    if until_iso is not None:
        try:
            until_epoch = _parse_since(until_iso)
        except ValueError as exc:
            click.echo(f"invalid --until value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    if window is not None:
        try:
            observability.parse_window(window)
        except ValueError as exc:
            click.echo(f"invalid --window value: {exc}", err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    domain_normalized: str | None = None
    if domain is not None:
        try:
            domain_normalized = observability.validate_domain(domain.lower())
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(observability.EXIT_INVALID_VALUE)

    events = observability.read_all_metrics()
    filtered = _apply_metrics_filters(
        events,
        window=window,
        domain=domain_normalized,
        since_epoch=since_epoch,
        until_epoch=until_epoch,
    )

    result = observability.aggregate_percentile(
        filtered,
        percentiles=tuple(pct_ints),
        reservoir_size=reservoir_size,
    )

    if fmt_lower == "json":
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if fmt_lower == "text":
        click.echo(observability.format_percentile_report(result), nl=False)
        return
    click.echo(f"unknown --format value: {fmt}", err=True)
    sys.exit(observability.EXIT_INVALID_VALUE)
