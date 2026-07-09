"""Drift group extracted from cli/__init__.py (v1.3-cli-split, Slice 4).

Hosts the ``flow drift`` Click group and its subcommands (``run``,
``events``, ``events alias`` [preserved intact per REQ-V1.2.4
deprecation]), plus the private helpers used internally by those
commands (``_resolve_snapshots_dir``, ``_parse_since``,
``_parse_since_until``, ``_format_drift_events_text``) and the
``DEFAULT_GRAPH_JSON`` / ``DEFAULT_SNAPSHOTS_DIR`` module constants
used by snapshot code. The body below is a verbatim relocation from
``cli/__init__.py`` lines 2000-2824 (post-Slice-1+2+3; pre-Slice-1+2+3
equivalent lines 2076-2893 per tasks.md T-4) -- behavior MUST match
pre-split exactly. Top-level imports were added here because a module
cannot see names that live in ``cli/__init__.py``'s import block; the
relocated body references the same names it did before.

No new logic, no new tests; this is a pure mechanical extraction
(REQ-CLI-SPLIT-4). The public API surface preserved by the top-level
re-export is ``_format_drift_events_text`` only (per tasks.md T-4
``re_exports`` list); everything else stays submodule-internal.

The ``drift_events_alias_group`` (and its ``list`` / ``tail`` / ``stats``
subcommands) is moved INTACT from ``cli/__init__.py`` -- the bodies
forward to ``drift_events_list/tail/stats`` via ``ctx.forward`` and
must not be split or modified (REQ-V1.2.4 deprecation contract).
"""

from __future__ import annotations

import csv as _csv
import io
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from flow_engineering import decision_drift, observability
from flow_engineering.cli import main  # noqa: F401  (parent group; see design section 6)
from flow_engineering.drift_event_log import (
    DriftEvent,
    DriftEventLog,
    DriftEventLogLegacyFormatError,
)

# ---------- REQ-10/11/14: flow drift <change> ----------


DEFAULT_GRAPH_JSON: Path = Path.home() / ".flow-engineering" / "graph.json"
DEFAULT_SNAPSHOTS_DIR: Path = Path.home() / ".flow-engineering" / "snapshots"
"""Production default for the snapshots directory.

Mirrors the ``DEFAULT_GRAPH_JSON`` precedent — tests override via
``FLOW_SNAPSHOTS_DIR`` so the ``flow snapshot`` subcommands land in a
``tmp_path`` instead of polluting the user's home directory.
"""


def _resolve_snapshots_dir() -> Path:
    """Return the snapshots directory the CLI uses.

    Honours the ``FLOW_SNAPSHOTS_DIR`` env override (used by tests +
    parallel deploys); falls back to :data:`DEFAULT_SNAPSHOTS_DIR`.
    Mirrors ``decision_drift._resolve_snapshots_dir`` so the two paths
    stay in lockstep.
    """
    env = os.environ.get("FLOW_SNAPSHOTS_DIR")
    if env:
        return Path(env)
    return DEFAULT_SNAPSHOTS_DIR


def _parse_since(raw: str | None) -> float | None:
    """Parse a `--since` ISO 8601 timestamp into epoch seconds (float).

    Returns ``None`` when ``raw`` is ``None`` or empty. Raises ``ValueError``
    with a one-line human message on parse failure — the CLI catches the
    exception and emits a stderr line + exit code ``2`` per REQ-10/REQ-11.
    Accepts both naive and ``Z``/offset-aware ISO 8601 strings. Naive
    timestamps (no tzinfo) are interpreted as UTC by default — the CLI runs
    in any timezone, and `--since 2026-06-15` should mean a deterministic
    instant, not a local-time midnight that drifts across CI machines.
    """
    if raw is None or raw.strip() == "":
        return None
    cleaned = raw.strip()
    try:
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.timestamp()
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"--since must be ISO 8601 (e.g. 2026-06-15 or 2026-06-15T12:00:00Z); got {raw!r}: {exc}"
        ) from exc


def _drift_exit_code(report: decision_drift.DriftReport) -> int:
    """Resolve the exit code per REQ-11: 2 wins over 1 wins over 0.

    - 2 when ``graph_unavailable`` (terminal unable_to_verify state).
    - 1 when any binding classifies as non-STILL_VALID.
    - 0 when every binding (if any) is STILL_VALID.
    """
    if report.graph_unavailable:
        return 2
    for cls in report.class_counts:
        if cls != decision_drift.DriftClass.STILL_VALID:
            return 1
    return 0


def _serialize_drift_report(report: decision_drift.DriftReport) -> dict[str, Any]:
    """Convert a :class:`DriftReport` into a JSON-safe ``dict``.

    The ``findings`` list embeds :class:`CodeRef` dataclasses which the stdlib
    JSON encoder cannot serialize — convert each to a flat dict and turn the
    ``DriftClass`` keys/values into plain strings.
    """
    findings: list[dict[str, Any]] = []
    for f in report.findings:
        findings.append(
            {
                "decision_id": f.decision_id,
                "binding": {
                    "id": f.binding.id,
                    "label": f.binding.label,
                    "file": f.binding.file,
                    "line": f.binding.line,
                    "confidence": f.binding.confidence,
                    "source": f.binding.source,
                    "project": f.binding.project,
                },
                "drift_class": f.drift_class.value,
                "detail": f.detail,
            }
        )
    return {
        "change_name": report.change_name,
        "scanned_at": report.scanned_at,
        "graph_mtime": report.graph_mtime,
        "decisions_total": report.decisions_total,
        "bindings_total": report.bindings_total,
        "class_counts": {cls.value: count for cls, count in report.class_counts.items()},
        "findings": findings,
        "graph_unavailable": report.graph_unavailable,
        "unable_reason": report.unable_reason,
    }


def _render_drift_table(report: decision_drift.DriftReport) -> str:
    """Pretty-print a :class:`DriftReport` as a fixed-width text table."""
    headers = ("decision_id", "binding.id", "binding.label", "drift_class", "detail")
    lines: list[str] = []
    lines.append("  ".join(h.upper() for h in headers))
    lines.append("-" * 96)
    if report.findings:
        for f in report.findings:
            detail = f.detail if f.detail else f.drift_class.value
            lines.append(
                f"{f.decision_id}  {f.binding.id}  {f.binding.label}  "
                f"{f.drift_class.value}  {detail}"
            )
    else:
        if report.graph_unavailable:
            lines.append("(unable_to_verify: graph.json unavailable)")
        else:
            lines.append("(no bindings scanned)")
    return "\n".join(lines)


def _now_iso() -> str:
    """Return UTC now as an ISO 8601 string with a ``Z`` suffix."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_back_findings(
    report: decision_drift.DriftReport, change_name: str
) -> int:
    """Persist per-finding metadata via ``EngramClient.update_observation_metadata``.

    Per REQ-14, a single-row failure MUST NOT abort the loop — each
    ``update_observation_metadata`` call is wrapped in its own ``except``
    clause that logs to observability and continues. Returns the count of
    successful writes (used by tests to assert no partial abort).

    Per REQ-59 S2 / design D8: when ``skipped_total >= FLOW_DRIFT_SKIP_WARN_THRESHOLD``
    (default 3; ``0`` = every batch with skipped > 0; ``-1`` = never),
    emit ONE ``WARN: drift write-back skipped <N> non-int decision_ids``
    line on ``sys.stderr`` at the END of the batch (NOT per skipped row).
    """
    # Lazy imports: ``_default_save_backend`` and ``EngramClient`` are
    # re-exported by ``cli/__init__.py`` (and ``_default_save_backend``
    # is also DEFINED there post-Slice-4). Test seam in
    # ``tests/unit/test_cli_drift.py`` patches
    # ``flow_engineering.cli.EngramClient`` and
    # ``flow_engineering.cli._default_save_backend`` via
    # ``monkeypatch.setattr``; resolving through the same-module binding
    # (``drift._write_back_findings``) would bypass those patches. Lazy
    # import re-fetches from ``flow_engineering.cli`` at call time. Same
    # precedent as Slice 3's lazy import of ``_git`` from ``cli`` inside
    # ``_detect_project_markers`` (Slice 3 apply-progress §Pragmatic
    # body adjustments item 1).
    from flow_engineering.cli import (  # noqa: F401
        EngramClient as _EngramClient,
    )
    from flow_engineering.cli import (
        _default_save_backend,
    )
    backend = _default_save_backend()
    client = _EngramClient(change_name, backend)
    success = 0
    skipped_total = 0
    for finding in report.findings:
        try:
            observation_id = int(finding.decision_id)
        except (TypeError, ValueError):
            # decision_id is not int-castable (e.g. legacy observations with
            # synthetic "unknown" id). Skip per-row without aborting.
            observability.increment(
                "drift_write_back_skipped_total",
                reason="non_int_decision_id",
            )
            skipped_total += 1
            continue
        try:
            client.update_observation_metadata(
                observation_id,
                {
                    "last_verified_at": _now_iso(),
                    "last_drift_class": finding.drift_class.value,
                },
            )
            success += 1
        except Exception:
            # Per-row error isolation — record and keep going.
            observability.increment("drift_write_back_failed_total")
            continue

    # REQ-59 S2: once-per-batch stderr WARN when skipped_total >= threshold.
    threshold = _get_skip_warn_threshold()
    if threshold >= 0 and skipped_total >= threshold:
        print(
            f"WARN: drift write-back skipped {skipped_total} "
            f"non-int decision_ids",
            file=sys.stderr,
        )
    return success


def _get_skip_warn_threshold() -> int:
    """Parse ``FLOW_DRIFT_SKIP_WARN_THRESHOLD`` env var; default 3.

    Per design D8:
    - Default 3 (3 or more skipped rows triggers one batch WARN).
    - ``0`` = WARN every batch with skipped_total > 0.
    - ``-1`` = WARN never.
    - Parse error (non-integer) falls back to default 3.
    """
    raw = os.environ.get("FLOW_DRIFT_SKIP_WARN_THRESHOLD")
    if raw is None:
        return 3
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 3


@main.group("drift", invoke_without_command=True)
@click.pass_context
def drift_group(ctx: click.Context) -> None:
    """Drift detection + read-side CLI namespace (REQ-10/11/14 + REQ-V1.2.4).

    Path A rename (v1.2.0d): the drift detection subcommand is exposed
    as ``flow drift run <change>`` (the explicit canonical form) and
    the drift events read-side lives under ``flow drift events
    {list,tail,stats}``. ``invoke_without_command=True`` keeps the
    bare ``flow drift --help`` flow working (shows subcommand list).
    """


@drift_group.command("run")
@click.argument("change_name")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Emit machine-readable JSON instead of a text table.")
@click.option("--include-obsolete", is_flag=True, default=False,
              help="Opt in to OBSOLETE classification (queries graphify).")
@click.option("--write-back", is_flag=True, default=False,
              help="Persist per-finding last_verified_at + last_drift_class metadata.")
@click.option("--since", default=None,
              help="Filter observations whose created_at >= this ISO 8601 timestamp.")
@click.option("--graph-json", "graph_json", default=None,
              type=click.Path(path_type=Path),
              help="Path to graph.json snapshot "
                   "(default: ~/.flow-engineering/graph.json).")
@click.option(
    "--snapshot",
    "snapshot_id",
    default=None,
    help="REQ-33: drift-pinned scan via a stored snapshot. "
         "Reads frozen observations + graph.json from the envelope instead of live disk.",
)
def drift_run(
    change_name: str,
    as_json: bool,
    include_obsolete: bool,
    write_back: bool,
    since: str | None,
    graph_json: str | None,
    snapshot_id: str | None,
) -> None:
    """Run drift detection for a change (REQ-10/11/14 + REQ-33).

    Exit codes: 0 = every binding STILL_VALID. 1 = any non-STILL_VALID class
    found. 2 = graph unavailable OR --since parse error. Exit 2 wins over 1.

    REQ-33 surface: ``--snapshot=<snap_id>`` activates the drift-pinned
    scan path. The snapshot's frozen observations + graph.json content
    are loaded via ``decision_drift.scan_change(snap_id=...)``; the live
    ``graph.json`` file is IGNORED. Without ``--snapshot`` the behaviour
    is byte-identical to the pre-change path (D13 non-breaking).
    """
    try:
        since_ts = _parse_since(since)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    if snapshot_id is not None:
        # REQ-33 drift-pinned path: graph_json_path is None (the snapshot
        # provides the graph implicitly); backend stays None too (the
        # snapshot's frozen observations become the implicit backend).
        # ``decision_drift.scan_change`` raises SnapshotGraphMissing when
        # the snapshot has no graph_json_content — surface it cleanly.
        graph_path = None
    else:
        graph_path = Path(graph_json) if graph_json else DEFAULT_GRAPH_JSON

    try:
        report = decision_drift.scan_change(
            change_name,
            graph_json_path=graph_path,
            include_obsolete=include_obsolete,
            since=since_ts,
            snap_id=snapshot_id,
        )
    except decision_drift.SnapshotGraphMissing as exc:
        click.echo(
            json.dumps(
                {
                    "error": "snapshot graph_json_content missing",
                    "snap_id": snapshot_id,
                    "detail": str(exc),
                },
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(2)

    # Observability: record the summary BEFORE returning so the counters
    # always reflect what was actually computed.
    observability.record_drift_summary(report)

    if write_back:
        _write_back_findings(report, change_name)

    if as_json:
        click.echo(
            json.dumps(
                _serialize_drift_report(report),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        click.echo(_render_drift_table(report))

    sys.exit(_drift_exit_code(report))


# ---------- REQ-V1.0.2 + REQ-V1.0.3: flow drift events read-side CLI (Path A nested) ----------


@drift_group.group("events")
def drift_events_group() -> None:
    """Read drift events from ~/.flow-engineering/drift_events.jsonl (REQ-V1.0.2 + REQ-V1.0.3 + REQ-V1.2.4).

    Path A rename (v1.2.0d): the read-side now lives at
    ``flow drift events {list,tail,stats}`` instead of the pre-v1.2
    top-level ``flow drift-events {list,tail,stats}``. The hyphenated
    form is preserved for one release cycle as a 1-release
    ``deprecated=True`` Click group alias (see ``drift_events_alias``
    below). Mirrors the ``flow metrics {summary,export,aggregate}``
    group pattern so the operator mental model transfers.
    """


def _format_drift_events_text(events: list[DriftEvent]) -> str:
    """Render a fixed-width text table from drift events (REQ-V1.0.2 D4).

    Mirrors the ``flow metrics summary`` text-table precedent at
    ``cli.py:999-1001`` (``name.ljust(name_width) ...``). Columns:
    ``change``, ``decision_id``, ``binding_id``, ``class``, ``detected_at``.
    Empty input renders as ``(no drift events)`` for operator clarity.
    """
    if not events:
        return "(no drift events)\n"
    headers = ("change", "decision_id", "binding_id", "class", "detected_at")
    rows: list[tuple[str, ...]] = [
        (
            ev.change,
            str(ev.decision_id),
            ev.binding_id,
            ev.event_class,
            f"{ev.detected_at:.0f}",
        )
        for ev in events
    ]
    widths = [
        max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(len(headers))
    ]
    sep = "  "
    header_line = sep.join(h.ljust(widths[i]) for i, h in enumerate(headers))
    rule_line = sep.join("-" * w for w in widths)
    data_lines = [
        sep.join(r[i].ljust(widths[i]) for i in range(len(headers))) for r in rows
    ]
    return "\n".join([header_line, rule_line, *data_lines]) + "\n"


def _parse_since_until(
    since: str | None, until: str | None,
) -> tuple[float | None, float | None]:
    """Parse ISO 8601 ``--since`` and ``--until`` flags into epoch seconds.

    Returns ``(since_ts, until_ts)`` where ``None`` means "no bound".
    Raises ``ValueError`` on malformed input; the CLI handler converts
    that to ``exit 2`` per D9.
    """
    since_ts: float | None = None
    until_ts: float | None = None
    if since is not None:
        since_ts = datetime.fromisoformat(since.replace("Z", "+00:00")).timestamp()
    if until is not None:
        until_ts = datetime.fromisoformat(until.replace("Z", "+00:00")).timestamp()
    return since_ts, until_ts


def _filter_drift_events(
    events: list[DriftEvent],
    *,
    since_ts: float | None,
    until_ts: float | None,
    change: str | None,
    event_class: str | None,
    limit: int | None,
) -> list[DriftEvent]:
    """Apply the documented filter set to a list of drift events."""
    out: list[DriftEvent] = []
    for ev in events:
        if since_ts is not None and ev.detected_at < since_ts:
            continue
        if until_ts is not None and ev.detected_at > until_ts:
            continue
        if change is not None and ev.change != change:
            continue
        if event_class is not None and ev.event_class != event_class:
            continue
        out.append(ev)
        if limit is not None and len(out) >= limit:
            break
    return out


def _read_drift_events_with_legacy_policy(
    log: DriftEventLog, *, strict: bool, log_path: Path
) -> list[DriftEvent]:
    """Read drift events from ``log``, handling legacy ``str`` decision_id lines.

    REQ-V1.1.2 S2 hardening: legacy ``str`` decision_id lines from
    pre-v1.0 sinks raise :class:`DriftEventLogLegacyFormatError`. The
    read-side CLI catches the error per-file:

    - ``--strict`` mode aborts on first legacy line with exit code 4 +
      CHANGELOG v1.0 ``sed`` migration hint.
    - Default mode emits a per-batch stderr WARN and returns ``[]``
      (legacy contamination preserved + visible to the operator).

    The CHANGELOG v1.0 ``sed`` migration is the documented upgrade path.
    """
    try:
        return log.read_all()
    except DriftEventLogLegacyFormatError as exc:
        if strict:
            click.echo(
                f"error: legacy format detected in {log_path}; {exc}\n"
                "Run the CHANGELOG v1.0 sed migration to fix in place.",
                err=True,
            )
            sys.exit(4)
        click.echo(
            f"warning: skipped legacy str decision_id lines in {log_path}; "
            "use --strict to abort. Run the CHANGELOG v1.0 sed migration "
            "to fix in place.",
            err=True,
        )
        return []


@drift_events_group.command(name="list")
@click.option("--since", default=None,
              help="Filter events with detected_at >= <iso> (ISO 8601).")
@click.option("--until", default=None,
              help="Filter events with detected_at <= <iso> (ISO 8601).")
@click.option("--change", default=None,
              help="Filter events for a specific change name.")
@click.option("--event-class", default=None,
              help="Filter events by drift class (e.g. LABEL_DRIFT).")
@click.option("--limit", type=int, default=None,
              help="Cap the number of returned events.")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json", "prometheus", "csv"]),
              help="Output format (default: text).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
def drift_events_list(
    since: str | None,
    until: str | None,
    change: str | None,
    event_class: str | None,
    limit: int | None,
    fmt: str,
    log_path: Path | None,
    strict: bool,
) -> None:
    """List drift events with optional filters (REQ-V1.0.2 + REQ-V1.1.2)."""
    try:
        since_ts, until_ts = _parse_since_until(since, until)
    except ValueError as exc:
        click.echo(f"Error: invalid --since/--until: {exc}", err=True)
        sys.exit(observability.EXIT_INVALID_VALUE)

    log = DriftEventLog(path=log_path) if log_path is not None else DriftEventLog()
    events = _read_drift_events_with_legacy_policy(
        log, strict=strict, log_path=log.path
    )
    events = _filter_drift_events(
        events,
        since_ts=since_ts,
        until_ts=until_ts,
        change=change,
        event_class=event_class,
        limit=limit,
    )

    if fmt == "text":
        click.echo(_format_drift_events_text(events))
        return
    if fmt == "json":
        click.echo(
            json.dumps([ev.to_json_dict() for ev in events], ensure_ascii=False, indent=2)
        )
        return
    if fmt == "csv":
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(["change", "decision_id", "binding_id", "class", "detected_at"])
        for ev in events:
            writer.writerow(
                [ev.change, ev.decision_id, ev.binding_id, ev.event_class, ev.detected_at]
            )
        click.echo(buf.getvalue(), nl=False)
        return
    if fmt == "prometheus":
        # REQ-V1.0.2 D4: per-change + per-event-class counts as a counter.
        lines = [
            "# HELP flow_drift_events_total Drift events recorded.",
            "# TYPE flow_drift_events_total counter",
        ]
        by_class: dict[str, int] = {}
        by_change: dict[str, int] = {}
        for ev in events:
            by_class[ev.event_class] = by_class.get(ev.event_class, 0) + 1
            by_change[ev.change] = by_change.get(ev.change, 0) + 1
        for cls, n in sorted(by_class.items()):
            lines.append(f'flow_drift_events_total{{event_class="{cls}"}} {n}')
        for change_name, n in sorted(by_change.items()):
            lines.append(f'flow_drift_events_total{{change="{change_name}"}} {n}')
        lines.append("# EOF")
        click.echo("\n".join(lines) + "\n")
        return


@drift_events_group.command(name="tail")
@click.option("--limit", type=int, default=10,
              help="Number of events to show, newest-first (default: 10).")
@click.option("--change", default=None,
              help="Filter events for a specific change name.")
@click.option("--event-class", default=None,
              help="Filter events by drift class (e.g. LABEL_DRIFT).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format (default: text).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
def drift_events_tail(
    limit: int,
    change: str | None,
    event_class: str | None,
    log_path: Path | None,
    fmt: str,
    strict: bool,
) -> None:
    """Show the last N drift events newest-first (REQ-V1.0.3 + REQ-V1.1.2).

    Mirrors the shell ``tail -n`` semantics: events are sorted by
    ``detected_at`` descending and the first ``--limit`` rows are
    rendered (default 10). Filters compose: ``--change`` and
    ``--event-class`` are applied BEFORE the limit so the operator sees
    the most recent N matching events, not the most recent N events
    post-filtered.
    """
    log = DriftEventLog(path=log_path) if log_path is not None else DriftEventLog()
    events = _read_drift_events_with_legacy_policy(
        log, strict=strict, log_path=log.path
    )
    events = sorted(events, key=lambda ev: ev.detected_at, reverse=True)
    events = _filter_drift_events(
        events,
        since_ts=None,
        until_ts=None,
        change=change,
        event_class=event_class,
        limit=limit,
    )

    if fmt == "text":
        click.echo(_format_drift_events_text(events))
        return
    click.echo(
        json.dumps([ev.to_json_dict() for ev in events], ensure_ascii=False, indent=2)
    )


@drift_events_group.command(name="stats")
@click.option("--change", default=None,
              help="Filter stats to a specific change name.")
@click.option("--since", default=None,
              help="Filter events with detected_at >= <iso> (ISO 8601).")
@click.option("--until", default=None,
              help="Filter events with detected_at <= <iso> (ISO 8601).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format (default: text).")
@click.option("--top-n", "top_n", type=int, default=5,
              help="Top-N decision_ids by frequency (default: 5).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
def drift_events_stats(
    change: str | None,
    since: str | None,
    until: str | None,
    log_path: Path | None,
    fmt: str,
    top_n: int,
    strict: bool,
) -> None:
    """Per-event-class + per-change + per-decision-id counts (REQ-V1.0.3 + REQ-V1.1.2).

    Renders an aligned text table with 3 sections (or a JSON envelope
    with ``by_event_class``, ``by_change``, ``by_decision_id`` keys).
    The ``by_decision_id`` array is sorted by frequency descending and
    capped at ``--top-n`` (default 5).
    """
    try:
        since_ts, until_ts = _parse_since_until(since, until)
    except ValueError as exc:
        click.echo(f"Error: invalid --since/--until: {exc}", err=True)
        sys.exit(observability.EXIT_INVALID_VALUE)

    log = DriftEventLog(path=log_path) if log_path is not None else DriftEventLog()
    events = _read_drift_events_with_legacy_policy(
        log, strict=strict, log_path=log.path
    )
    events = _filter_drift_events(
        events,
        since_ts=since_ts,
        until_ts=until_ts,
        change=change,
        event_class=None,
        limit=None,
    )

    by_event_class: dict[str, int] = {}
    by_change: dict[str, int] = {}
    by_decision_id: dict[int, int] = {}
    for ev in events:
        by_event_class[ev.event_class] = by_event_class.get(ev.event_class, 0) + 1
        by_change[ev.change] = by_change.get(ev.change, 0) + 1
        by_decision_id[ev.decision_id] = by_decision_id.get(ev.decision_id, 0) + 1
    top_decision_ids = Counter(by_decision_id).most_common(top_n)

    if fmt == "json":
        payload = {
            "by_event_class": by_event_class,
            "by_change": by_change,
            "by_decision_id": [
                {"decision_id": did, "count": n} for did, n in top_decision_ids
            ],
        }
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    sections = [
        ("Event class", by_event_class),
        ("Change", by_change),
    ]
    lines: list[str] = []
    for header_label, counts in sections:
        lines.append(f"## {header_label}")
        if counts:
            w = max(len(k) for k in counts)
            for k in sorted(counts):
                lines.append(f"  {k.ljust(w)}  {counts[k]}")
        else:
            lines.append("  (none)")
        lines.append("")
    lines.append(f"## Decision ID (top {top_n})")
    if top_decision_ids:
        w = max(len(str(did)) for did, _ in top_decision_ids)
        for did, n in top_decision_ids:
            lines.append(f"  {str(did).ljust(w)}  {n}")
    else:
        lines.append("  (none)")
    click.echo("\n".join(lines) + "\n")


# ---------- REQ-V1.2.4: 1-release DEPRECATED Click group alias for `flow drift-events` ----------


@main.group(
    name="drift-events",
    deprecated=True,
    help=(
        "DEPRECATED alias for ``flow drift events`` (REQ-V1.2.4). "
        "Use ``flow drift events {list,tail,stats}`` instead. "
        "This hyphenated form is REMOVED in v1.3."
    ),
)
def drift_events_alias_group() -> None:
    """Read drift events from ~/.flow-engineering/drift_events.jsonl.

    REQ-V1.2.4 1-release DEPRECATED Click group alias — preserved for
    backwards compatibility with the pre-v1.2 top-level
    ``flow drift-events`` surface. The canonical v1.2 surface is
    ``flow drift events {list,tail,stats}`` (nested under the new
    ``drift`` group). This alias emits a Click ``DeprecationWarning``
    on every invocation via ``deprecated=True`` and delegates to the
    canonical subcommands. REMOVED in v1.3 per the
    ``SnapshotGraphMissing`` v1.1 precedent.
    """


@drift_events_alias_group.command(name="list")
@click.option("--since", default=None,
              help="Filter events with detected_at >= <iso> (ISO 8601).")
@click.option("--until", default=None,
              help="Filter events with detected_at <= <iso> (ISO 8601).")
@click.option("--change", default=None,
              help="Filter events for a specific change name.")
@click.option("--event-class", default=None,
              help="Filter events by drift class (e.g. LABEL_DRIFT).")
@click.option("--limit", type=int, default=None,
              help="Cap the number of returned events.")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json", "prometheus", "csv"]),
              help="Output format (default: text).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
@click.pass_context
def drift_events_alias_list(
    ctx: click.Context,
    since: str | None,
    until: str | None,
    change: str | None,
    event_class: str | None,
    limit: int | None,
    fmt: str,
    log_path: Path | None,
    strict: bool,
) -> None:
    """DEPRECATED alias for ``flow drift events list`` (REQ-V1.2.4)."""
    ctx.forward(
        drift_events_list,
        since=since, until=until, change=change, event_class=event_class,
        limit=limit, fmt=fmt, log_path=log_path, strict=strict,
    )


@drift_events_alias_group.command(name="tail")
@click.option("--limit", type=int, default=10,
              help="Number of events to show, newest-first (default: 10).")
@click.option("--change", default=None,
              help="Filter events for a specific change name.")
@click.option("--event-class", default=None,
              help="Filter events by drift class (e.g. LABEL_DRIFT).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format (default: text).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
@click.pass_context
def drift_events_alias_tail(
    ctx: click.Context,
    limit: int,
    change: str | None,
    event_class: str | None,
    log_path: Path | None,
    fmt: str,
    strict: bool,
) -> None:
    """DEPRECATED alias for ``flow drift events tail`` (REQ-V1.2.4)."""
    ctx.forward(
        drift_events_tail,
        limit=limit, change=change, event_class=event_class,
        log_path=log_path, fmt=fmt, strict=strict,
    )


@drift_events_alias_group.command(name="stats")
@click.option("--change", default=None,
              help="Filter stats to a specific change name.")
@click.option("--since", default=None,
              help="Filter events with detected_at >= <iso> (ISO 8601).")
@click.option("--until", default=None,
              help="Filter events with detected_at <= <iso> (ISO 8601).")
@click.option("--path", "log_path", default=None, type=click.Path(path_type=Path),
              help="Alternative drift event log path "
                   "(default: ~/.flow-engineering/drift_events.jsonl).")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json"]),
              help="Output format (default: text).")
@click.option("--top-n", "top_n", type=int, default=5,
              help="Top-N decision_ids by frequency (default: 5).")
@click.option("--strict", is_flag=True,
              help="Abort on first legacy str decision_id line "
                   "(exit code 4 + CHANGELOG v1.0 sed migration hint).")
@click.pass_context
def drift_events_alias_stats(
    ctx: click.Context,
    change: str | None,
    since: str | None,
    until: str | None,
    log_path: Path | None,
    fmt: str,
    top_n: int,
    strict: bool,
) -> None:
    """DEPRECATED alias for ``flow drift events stats`` (REQ-V1.2.4)."""
    ctx.forward(
        drift_events_stats,
        change=change, since=since, until=until, log_path=log_path,
        fmt=fmt, top_n=top_n, strict=strict,
    )


