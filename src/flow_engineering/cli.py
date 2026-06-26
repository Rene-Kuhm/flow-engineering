"""CLI entry point for flow-engineering."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from flow_engineering import decision_drift, observability
from flow_engineering.auto_suggest_code_refs import FLOW_AUTO_SUGGEST_ENV
from flow_engineering.binding import (
    CODE_REFS_MARKER,
    CodeRef,
    extract_code_refs,
)
from flow_engineering.daemon import start_watch
from flow_engineering.engram_io import (
    EngramBackend,
    EngramClient,
    InMemoryBackend,
    iter_observations_for_change,
)
from flow_engineering.orchestrator import (
    apply_change,
    archive_change,
    verify_change,
)
from flow_engineering.scaffold import (
    load_change_yaml,
    render_new_project,
    scaffold_change,
)
from flow_engineering.state import StateMachine


@click.group()
@click.version_option(package_name="flow-engineering")
def main() -> None:
    """Flow Engineering -- orchestrator of the Agentic & Context-Driven closed loop."""


@main.command()
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Project root where flow-engineering/<change>/ will be created.",
)
@click.option(
    "--cross-projects",
    multiple=True,
    help="Sub-projects affected (repeatable).",
)
def new(change: str, target: Path, cross_projects: tuple[str, ...]) -> None:
    """Scaffold a new change."""
    change_dir, sm = scaffold_change(
        change=change,
        target_dir=target,
        cross_projects=list(cross_projects),
    )
    click.echo(f"Created change '{change}' at {change_dir}")
    click.echo(f"State: {sm.status.value}")
    if cross_projects:
        click.echo(f"Cross-projects: {', '.join(cross_projects)}")
    click.echo(f"\nNext: edit {change_dir}/explore/exploration.md")


@main.command(name="new-project")
@click.argument("project_name")
@click.option(
    "--in",
    "target",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Directory where the new project will be bootstrapped.",
)
@click.option("--version", default="0.1.0", help="Initial flow-engineering version pin.")
def new_project(project_name: str, target: Path, version: str) -> None:
    """Bootstrap a new project."""
    project_dir = render_new_project(project_name, target, version=version)
    click.echo(f"Bootstrapped project '{project_name}' at {project_dir}")


@main.command()
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Project root to inspect.",
)
def status(target: Path) -> None:
    """List all changes and their current status."""
    fe_dir = target / "flow-engineering"
    if not fe_dir.exists():
        click.echo(f"No flow-engineering/ directory at {target}")
        sys.exit(1)
    changes = [d for d in fe_dir.iterdir() if d.is_dir()]
    if not changes:
        click.echo(f"No changes in {fe_dir}")
        return
    for change_dir in sorted(changes):
        # Skip subdirectories of changes (e.g., bootstrap/explore is NOT a change)
        if not (change_dir / "state.json").exists():
            continue
        try:
            sm = StateMachine.load(change_dir)
        except FileNotFoundError:
            continue
        manifest = load_change_yaml(change_dir)
        cross_obj = manifest.get("cross_projects", []) if isinstance(manifest, dict) else []
        cross = [str(p) for p in cross_obj] if isinstance(cross_obj, list) else []
        cross_marker = f" [cross: {', '.join(cross)}]" if cross else ""
        click.echo(
            f"  {change_dir.name}: {sm.status.value}"
            f"  ({len(sm.transitions)} transitions,"
            f" {sm.token_cost}/{sm.token_budget} tokens)"
            f"{cross_marker}"
        )


@main.command()
def doctor() -> None:
    """Check plugin/CLI version compatibility."""
    import flow_engineering

    click.echo(f"flow-engineering {flow_engineering.__version__}")
    click.echo("Python OK")
    click.echo("Plugin: not loaded (this CLI is invoked directly)")


@main.command()
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help="Project root containing flow-engineering/<change>/.",
)
@click.option("--no-strict-tdd", "no_strict_tdd", is_flag=True, help="Disable strict TDD (requires --reason).")
@click.option("--reason", default=None, help="Reason for disabling strict TDD.")
def apply(change: str, target: Path, no_strict_tdd: bool, reason: str | None) -> None:
    """Apply tasks for a change (TASKED -> APPLYING -> VERIFYING)."""
    if no_strict_tdd and not reason:
        click.echo("ERROR: --no-strict-tdd requires --reason", err=True)
        sys.exit(2)
    result = apply_change(change=change, target=target)
    click.echo(result.message)
    if result.delegation_error:
        click.echo(f"[delegation] {result.delegation_error}")
    if result.task_id:
        click.echo(f"Next task: {result.task_id}")


@main.command()
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
)
@click.option("--test-output", default="", help="Test runner output to classify.")
def verify(change: str, target: Path, test_output: str) -> None:
    """Verify change (APPLYING -> VERIFYING -> ARCHIVING)."""
    result = verify_change(change=change, target=target, test_output=test_output)
    click.echo(f"[{result.action}] {result.message}")
    if result.failure_class:
        click.echo(f"Failure class: {result.failure_class.value}")


@main.command()
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
)
@click.option("--diff", default="", help="Diff text for structural change detection.")
@click.option("--no-graphify", is_flag=True, help="Skip the graphify rebuild (dry-run).")
def archive(change: str, target: Path, diff: str, no_graphify: bool) -> None:
    """Archive change (ARCHIVING -> DONE), trigger graph rebuild."""
    result = archive_change(
        change=change,
        target=target,
        diff_text=diff,
        dry_run_graphify=no_graphify or True,  # v0.1.0: always dry-run by default
    )
    click.echo(result.message)
    if result.graphify_decision:
        click.echo(
            f"Graphify: mode={result.graphify_decision.mode} "
            f"cost=${result.graphify_decision.estimated_cost_usd:.2f}"
        )


@main.command()
@click.argument("change")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
)
@click.option(
    "--drift", "drift_flag",
    is_flag=True,
    default=False,
    help="REQ-15: also watch apply-progress writes; emit drift summary per merged task.",
)
@click.option(
    "--graph-json", "graph_json",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to graph.json snapshot (default: ~/.flow-engineering/graph.json).",
)
def watch(change: str, target: Path, drift_flag: bool, graph_json: Path | None) -> None:
    """Watch for exploration.md changes and auto-transition NEW -> EXPLORED.

    With ``--drift`` (REQ-15), the watcher ALSO subscribes to apply-progress
    writes and emits a one-line ``drift: <change> N findings (...)`` summary
    to stdout on every event with at least one task in ``status: merged``.
    Counters ``drift_*_total`` are incremented per event via
    ``observability.record_drift_summary``. Missing ``graph.json`` emits
    ``unable_to_verify: ...`` once and the watcher stays alive.
    """
    started, message = start_watch(
        change=change,
        target=target,
        drift=drift_flag,
        graph_json_path=graph_json,
        on_summary=lambda line: click.echo(line),
    )
    click.echo(message)
    if not started:
        sys.exit(1)


@main.command(name="memory-timeline")
@click.option(
    "--in",
    "target",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
)
def memory_timeline(target: Path) -> None:
    """Show a timeline view of all changes and their transitions."""
    from flow_engineering.timeline import build_timeline, render_timeline

    fe_dir = target / "flow-engineering"
    if not fe_dir.exists():
        click.echo("No flow-engineering/ directory.")
        return
    changes = [d for d in fe_dir.iterdir() if d.is_dir() and (d / "state.json").exists()]
    if not changes:
        click.echo("No changes.")
        return
    timeline = build_timeline(changes)
    click.echo(render_timeline(timeline))


FLOW_VECTOR_SEARCH_ENV: str = "FLOW_VECTOR_SEARCH"
VECTOR_INSTALL_HINT: str = "pip install flow-engineering[vectors]"


def _vectors_extra_available() -> bool:
    """Return True iff the ``[vectors]`` extra is importable (REQ-17 gate leg 1).

    Imports are guarded so a missing module only sets the flag to ``False``
    — it MUST NOT raise. Test isolation uses ``monkeypatch.setattr`` on this
    helper to flip the gate without touching the heavy dependencies.
    """
    try:
        import sqlite_vec  # noqa: F401
        import torch  # noqa: F401
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return True


def _ensure_vector_extra() -> None:
    """Exit non-zero with the install hint if ``[vectors]`` is missing (REQ-17).

    Separate helper so ``flow search --semantic`` / ``flow reindex`` can call
    it BEFORE the env-var check. Mirrors the per-gate exit contract from
    REQ-17 scenarios 2 + 4 — actionable stderr line, exit code 2, no traceback.
    """
    if not _vectors_extra_available():
        click.echo(
            "Semantic search disabled: install [vectors] extra — "
            f"{VECTOR_INSTALL_HINT}",
            err=True,
        )
        sys.exit(2)


def _ensure_vector_env() -> None:
    """Exit non-zero with the env hint if ``FLOW_VECTOR_SEARCH!=1`` (REQ-17).

    Only reached after :func:`_ensure_vector_extra` passes, so the message
    is unambiguously "you have the extra installed but forgot to set the env".
    """
    if os.environ.get(FLOW_VECTOR_SEARCH_ENV) != "1":
        click.echo(
            "Semantic search disabled: set FLOW_VECTOR_SEARCH=1",
            err=True,
        )
        sys.exit(2)


def _default_save_backend() -> EngramBackend:
    """Return the active backend.

    REQ-17 gate state machine:
    - Both gates met (``[vectors]`` extra AND ``FLOW_VECTOR_SEARCH=1``) → wrap
      the inner ``InMemoryBackend`` in :class:`HybridBackend` with a real
      ``SentenceTransformersProvider`` so default ``flow save`` writes
      embeddings on save.
    - Otherwise → return the inner backend unchanged. Default ``flow save``
      stays byte-identical to v0.3.0 (REQ-17 scenario 5).
    """
    if not (_vectors_extra_available() and os.environ.get(FLOW_VECTOR_SEARCH_ENV) == "1"):
        return InMemoryBackend()
    from flow_engineering.embedding_provider import SentenceTransformersProvider
    from flow_engineering.hybrid_backend import HybridBackend

    provider = SentenceTransformersProvider()
    return HybridBackend(InMemoryBackend(), provider)


@main.command()
@click.argument("change")
@click.argument("phase")
@click.option(
    "--content",
    default=None,
    help="Inline content to save (mutually exclusive with --content-file).",
)
@click.option(
    "--content-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to file containing the observation content.",
)
@click.option(
    "--with-suggest",
    "with_suggest_flag",
    is_flag=True,
    default=False,
    help="Run auto-suggest and accept candidates non-interactively.",
)
@click.option(
    "--no-suggest",
    "no_suggest_flag",
    is_flag=True,
    default=False,
    help="Skip auto-suggest entirely; writes source=manual.",
)
def save(
    change: str,
    phase: str,
    content: str | None,
    content_file: Path | None,
    with_suggest_flag: bool,
    no_suggest_flag: bool,
) -> None:
    """Save a phase artifact, optionally running auto-suggest (REQ-6).

    Auto-suggest resolution order:
    1. ``--with-suggest`` flag (non-interactive accept-all).
    2. ``--no-suggest`` flag (bypass suggester, source=manual).
    3. ``FLOW_AUTO_SUGGEST=1`` env var (non-interactive accept-all).
    4. Interactive TTY prompt (when ``stdin.isatty()``).
    5. Default: append unbound block, do not call graphify.
    """
    if with_suggest_flag and no_suggest_flag:
        raise click.UsageError("--with-suggest and --no-suggest are mutually exclusive.")
    if content is not None and content_file is not None:
        raise click.UsageError("Use either --content or --content-file, not both.")

    if content_file is not None:
        text = content_file.read_text(encoding="utf-8")
    elif content is not None:
        text = content
    else:
        text = sys.stdin.read()

    env_active = os.environ.get(FLOW_AUTO_SUGGEST_ENV) == "1"
    is_tty = sys.stdin.isatty()
    if with_suggest_flag:
        with_suggest, no_suggest = True, False
    elif no_suggest_flag:
        with_suggest, no_suggest = False, True
    else:
        with_suggest = env_active or is_tty
        no_suggest = False

    client = EngramClient(change, _default_save_backend())
    client.save_phase(
        phase,
        text,
        with_suggest=with_suggest,
        no_suggest=no_suggest,
        is_tty=is_tty,
    )
    click.echo(f"Saved {phase} for {change} (with_suggest={with_suggest}, no_suggest={no_suggest})")


# ---------- REQ-17 / REQ-18: flow search <query> ----------


def _format_search_row(rank: int, obs_id: int, title: str, score: float) -> str:
    """One text-table row for ``flow search`` output."""
    return f"{rank:<3}  obs {obs_id:<6}  {score:.4f}  {title}"


def _render_search_table(rows: list[dict]) -> str:
    """Pretty-print search hits as a fixed-width text table."""
    if not rows:
        return "(no results)"
    lines: list[str] = []
    lines.append("  ".join(h.upper() for h in ("rank", "id", "score", "title")))
    lines.append("-" * 64)
    for r in rows:
        lines.append(
            _format_search_row(
                int(r.get("rank", 0)),
                int(r.get("observation_id", 0)),
                str(r.get("title", "")),
                float(r.get("score", 0.0)),
            )
        )
    return "\n".join(lines)


def _search_results_to_rows(results: list[dict]) -> list[dict]:
    """Project ``mem_search*`` results to the JSON/table shape.

    The vector methods return ``observation_id`` + ``score`` + ``rank`` per
    REQ-17 contract. The legacy ``mem_search`` returns plain observation
    dicts with ``id`` and no score/rank — synthesize a position-based
    rank and a 0.0 score so the table renders uniformly.
    """
    out: list[dict] = []
    for rank, r in enumerate(results):
        obs_id = r.get("observation_id", r.get("id"))
        out.append(
            {
                "observation_id": obs_id,
                "rank": r.get("rank", rank),
                "score": r.get("score", 0.0),
                "title": r.get("title", ""),
                "topic_key": r.get("topic_key", ""),
            }
        )
    return out


@main.command()
@click.argument("query")
@click.option(
    "--semantic",
    "semantic_flag",
    is_flag=True,
    default=False,
    help="REQ-17: semantic search via embeddings (requires [vectors] extra AND FLOW_VECTOR_SEARCH=1).",
)
@click.option(
    "--hybrid",
    "hybrid_flag",
    is_flag=True,
    default=False,
    help="REQ-18: hybrid semantic + FTS search with --alpha blending.",
)
@click.option(
    "--alpha",
    type=float,
    default=0.5,
    help="REQ-18: weight for semantic vs FTS in --hybrid mode (0.0 = pure FTS, 1.0 = pure semantic).",
)
@click.option(
    "--k",
    type=int,
    default=10,
    help="Maximum number of results to return.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit machine-readable JSON instead of a text table.",
)
def search(
    query: str,
    semantic_flag: bool,
    hybrid_flag: bool,
    alpha: float,
    k: int,
    as_json: bool,
) -> None:
    """Search observations (REQ-17 + REQ-18 CLI surface).

    Default mode is FTS5 prose (``mem_search``); this stays byte-identical
    to the pre-vector behavior so existing scripts are unaffected. The
    ``--semantic`` and ``--hybrid`` flags enable vector retrieval and are
    mutually exclusive.
    """
    if semantic_flag and hybrid_flag:
        click.echo(
            "ERROR: --semantic and --hybrid are mutually exclusive.", err=True
        )
        sys.exit(2)
    if not (0.0 <= alpha <= 1.0):
        click.echo(
            f"ERROR: --alpha must be in [0.0, 1.0], got {alpha}", err=True
        )
        sys.exit(2)

    backend = _default_save_backend()

    if semantic_flag or hybrid_flag:
        # Gate check order matters: extra first (so the install hint wins
        # over the env hint when both are missing). Mirrors REQ-17 scenarios
        # 2 and 4 — the user gets the most actionable error first.
        _ensure_vector_extra()
        _ensure_vector_env()

        if hybrid_flag:
            # The library validates alpha again at the call boundary, but
            # we exit early here so the CLI never invokes the library with
            # garbage. ``trigger="cli"`` tags the observability event so
            # dashboards can separate user-driven calls from programmatic ones.
            raw = backend.mem_search_hybrid(query, k=k, alpha=alpha, trigger="cli")
        else:
            raw = backend.mem_search_semantic(query, k=k, trigger="cli")
    else:
        raw = backend.mem_search(query, limit=k)

    rows = _search_results_to_rows(raw)
    if as_json:
        click.echo(json.dumps({"results": rows}, ensure_ascii=False, indent=2))
        return
    click.echo(_render_search_table(rows))


if __name__ == "__main__":
    main()


# ---------- REQ-7: flow inspect <change> ----------


def _truncate(text: str, width: int) -> str:
    """Truncate text to ``width`` characters, adding an ellipsis when cut."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def _format_binding_line(ref: CodeRef) -> str:
    """One-line binding summary: ``id (label, file:line, conf, src)``."""
    return (
        f"{ref.id} ({ref.label}, {ref.file}:{ref.line}, "
        f"conf={ref.confidence:.2f}, src={ref.source})"
    )


def _render_inspect_row(obs: dict) -> dict:
    """Build one inspect row from a raw observation dict.

    Returns a dict with keys ``decision_id``, ``decision`` (title),
    ``code_refs`` (list of CodeRef objects), ``freshness``, and
    ``parse_error`` (when the block is malformed). Never raises: per-row
    parse errors are isolated (REQ-7 scenario). The CodeRef list is the
    canonical representation; dict serialization happens only at the JSON
    output boundary.
    """
    title = str(obs.get("title", ""))
    content = str(obs.get("content", ""))
    decision_id = obs.get("id")
    parse_error: str | None = None
    refs: list[CodeRef] = []
    if CODE_REFS_MARKER in content:
        try:
            refs = extract_code_refs(content)
        except Exception as exc:  # ParseError or any extraction error.
            parse_error = f"parse error: {exc}"
    freshness = observability.compute_freshness(obs.get("updated_at"))
    return {
        "decision_id": decision_id,
        "decision": title,
        "code_refs": refs,
        "freshness": freshness,
        "parse_error": parse_error,
    }


def _render_inspect_table(rows: list[dict]) -> str:
    """Render the inspect rows as a fixed-width text table."""
    headers = ("decision", "code_refs", "freshness")
    lines: list[str] = []
    lines.append("  ".join(h.upper() for h in headers))
    lines.append("-" * 72)
    if not rows:
        lines.append("(no observations for this change)")
        return "\n".join(lines)
    for row in rows:
        decision = _truncate(str(row.get("decision", "")), 36)
        if row.get("parse_error"):
            refs_text = str(row["parse_error"])
        elif row["code_refs"]:
            refs_text = "; ".join(_format_binding_line(r) for r in row["code_refs"])
        else:
            refs_text = "—"
        refs_text = _truncate(refs_text, 200)
        freshness = str(row.get("freshness", "never"))
        lines.append(f"{decision}  {refs_text}  {freshness}")
    return "\n".join(lines)


def _serialize_inspect_rows(rows: list[dict]) -> list[dict]:
    """Convert CodeRef objects in ``code_refs`` to dicts for JSON output."""
    out: list[dict] = []
    for row in rows:
        out.append(
            {
                "decision_id": row.get("decision_id"),
                "decision": row.get("decision"),
                "code_refs": [
                    {
                        "id": r.id,
                        "label": r.label,
                        "file": r.file,
                        "line": r.line,
                        "confidence": r.confidence,
                        "source": r.source,
                    }
                    for r in row.get("code_refs", [])
                ],
                "freshness": row.get("freshness"),
                "parse_error": row.get("parse_error"),
            }
        )
    return out


@main.command()
@click.argument("change")
@click.option("--json", "json_flag", is_flag=True, default=False,
              help="Emit machine-readable JSON instead of a text table.")
def inspect(change: str, json_flag: bool) -> None:
    """Render decisions for a change as a table (REQ-7).

    Columns: DECISION (id/title), CODE_REFS (id, label, file:line,
    confidence, source per binding), FRESHNESS (age with stale warning
    when older than 30 days). Per-row parse errors are isolated: a bad
    block in one observation never blanks the rest of the table.
    """
    started = time.monotonic()
    observability.increment("inspect_invoked_total", change=change)
    backend = _default_save_backend()
    observations = iter_observations_for_change(change, backend)
    rows = [_render_inspect_row(o) for o in observations]
    elapsed_ms = int((time.monotonic() - started) * 1000)
    observability.increment("inspect_render_ms", elapsed_ms=elapsed_ms, count=len(rows))
    if json_flag:
        click.echo(json.dumps(_serialize_inspect_rows(rows), ensure_ascii=False, indent=2))
        return
    click.echo(_render_inspect_table(rows))


# ---------- REQ-8 close: flow metrics ----------


def _summarize_metrics(events: list[dict]) -> dict[str, int]:
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


@main.command()
@click.option("--json", "json_flag", is_flag=True, default=False,
              help="Emit machine-readable JSON instead of a text summary.")
def metrics(json_flag: bool) -> None:
    """Dump the JSONL counter sink as a summary (REQ-8 close)."""
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


# ---------- REQ-10/11/14: flow drift <change> ----------


DEFAULT_GRAPH_JSON: Path = Path.home() / ".flow-engineering" / "graph.json"


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
    """
    backend = _default_save_backend()
    client = EngramClient(change_name, backend)
    success = 0
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
    return success


@main.command()
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
def drift(
    change_name: str,
    as_json: bool,
    include_obsolete: bool,
    write_back: bool,
    since: str | None,
    graph_json: str | None,
) -> None:
    """Run drift detection for a change (REQ-10/11/14).

    Exit codes: 0 = every binding STILL_VALID. 1 = any non-STILL_VALID class
    found. 2 = graph unavailable OR --since parse error. Exit 2 wins over 1.
    """
    try:
        since_ts = _parse_since(since)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    graph_path = Path(graph_json) if graph_json else DEFAULT_GRAPH_JSON

    report = decision_drift.scan_change(
        change_name,
        graph_json_path=graph_path,
        include_obsolete=include_obsolete,
        since=since_ts,
    )

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
