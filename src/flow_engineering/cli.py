"""CLI entry point for flow-engineering."""

from __future__ import annotations

import csv as _csv
import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
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
from flow_engineering.project_detector import apply_tag as _apply_tag
from flow_engineering.project_detector import detect as _detect_project
from flow_engineering.scaffold import (
    load_change_yaml,
    render_new_project,
    scaffold_change,
)
from flow_engineering.snapshot_manager import (
    PruneNoFilterError,
    PruneSafetyGateError,
    RollbackConflictError,
    RollbackRefusedError,
    SnapshotEnvelopeError,
    SnapshotManager,
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


def _sqlite_vec_available() -> bool:
    """Return True iff the ``[vectors]`` extra (specifically ``sqlite_vec``) is importable.

    Used by ``flow reindex`` to gate the SqliteVecStore path. Mirrors
    :func:`_vectors_extra_available` but focused on the SQLite side —
    sentence-transformers / torch are NOT required to write the index,
    only to compute embeddings (which can come from :class:`MockEmbeddingProvider`
    in tests).
    """
    try:
        import sqlite_vec  # noqa: F401
    except ImportError:
        return False
    return True


def _vectors_sqlite_path() -> Path:
    """Return the path used by ``flow reindex`` for ``SqliteVecStore``.

    Defaults to ``~/.flow-engineering/vectors.sqlite`` (mirrors the
    ``DEFAULT_GRAPH_JSON`` precedent). Tests override via ``monkeypatch.setattr``
    on the cli module's helper so the production default stays untouched.
    """
    return Path.home() / ".flow-engineering" / "vectors.sqlite"


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


def _parse_csv(raw: str | None) -> list[str] | None:
    """Split a comma-separated string into a list of trimmed, non-empty tokens.

    Returns ``None`` when ``raw`` is ``None`` (the flag was not given).
    Returns ``[]`` when ``raw`` is an empty string or only separators.
    Uses the stdlib ``csv`` module so quoted commas (``"a, b",c``) parse
    per RFC 4180 rather than naïve ``str.split(',')``.
    """
    if raw is None:
        return None
    rows = list(_csv.reader([raw]))
    if not rows:
        return []
    return [item.strip() for item in rows[0] if item and item.strip()]


def _format_search_row(rank: int, obs_id: int, title: str, score: float) -> str:
    """One text-table row for ``flow search`` output (legacy 4-column)."""
    return f"{rank:<3}  obs {obs_id:<6}  {score:.4f}  {title}"


def _render_search_table(rows: list[dict]) -> str:
    """Pretty-print search hits as a fixed-width text table.

    Adds a ``PROJECT`` column when any row carries a ``project`` field
    (REQ-25 federated path). Legacy single-project search renders the
    original 4-column layout so existing output is unchanged.
    """
    if not rows:
        return "(no results)"
    show_project = any("project" in r for r in rows)
    if show_project:
        headers = ("rank", "id", "score", "project", "title")
        sep = "-" * 88
    else:
        headers = ("rank", "id", "score", "title")
        sep = "-" * 64
    lines: list[str] = []
    lines.append("  ".join(h.upper() for h in headers))
    lines.append(sep)
    for r in rows:
        if show_project:
            lines.append(
                f"{int(r.get('rank', 0)):<3}  obs {int(r.get('observation_id', 0)):<6}  "
                f"{float(r.get('score', 0.0)):.4f}  {str(r.get('project', '')):<24}  "
                f"{str(r.get('title', ''))}"
            )
        else:
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
    rank and a 0.0 score so the table renders uniformly. REQ-25 adds
    federated multi-project search; rows with a ``project`` field carry
    it through so the renderer can prepend the PROJECT column.
    """
    out: list[dict] = []
    for rank, r in enumerate(results):
        obs_id = r.get("observation_id", r.get("id"))
        row: dict[str, Any] = {
            "observation_id": obs_id,
            "rank": r.get("rank", rank),
            "score": r.get("score", 0.0),
            "title": r.get("title", ""),
            "topic_key": r.get("topic_key", ""),
        }
        if r.get("project") is not None:
            row["project"] = r["project"]
        out.append(row)
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
@click.option(
    "--federated",
    "federated_flag",
    is_flag=True,
    default=False,
    help="REQ-25: federated multi-project search (opt-in; default = single-project FTS).",
)
@click.option(
    "--projects",
    default=None,
    help="REQ-25: comma-separated project keys (default = all when --federated).",
)
@click.option(
    "--since",
    default=None,
    help="REQ-25: ISO 8601 date or datetime (lexicographic >= on created_at).",
)
@click.option(
    "--type",
    "type_csv",
    default=None,
    help="REQ-25: comma-separated observation types (exact match, case-sensitive).",
)
def search(
    query: str,
    semantic_flag: bool,
    hybrid_flag: bool,
    alpha: float,
    k: int,
    as_json: bool,
    federated_flag: bool,
    projects: str | None,
    since: str | None,
    type_csv: str | None,
) -> None:
    """Search observations (REQ-17 + REQ-18 + REQ-25 CLI surface).

    Default mode is FTS5 prose (``mem_search``); this stays byte-identical
    to the pre-vector behavior so existing scripts are unaffected. The
    ``--semantic`` and ``--hybrid`` flags enable vector retrieval. The
    ``--federated`` flag enables multi-project search via
    ``mem_search_federated`` with optional ``--projects`` / ``--since``
    / ``--type`` filters. The federated and vector paths are mutually
    exclusive.
    """
    if semantic_flag and hybrid_flag:
        click.echo(
            "ERROR: --semantic and --hybrid are mutually exclusive.", err=True
        )
        sys.exit(2)
    if federated_flag and (semantic_flag or hybrid_flag):
        click.echo(
            "ERROR: --federated is mutually exclusive with --semantic/--hybrid.",
            err=True,
        )
        sys.exit(2)
    if not (0.0 <= alpha <= 1.0):
        click.echo(
            f"ERROR: --alpha must be in [0.0, 1.0], got {alpha}", err=True
        )
        sys.exit(2)
    if federated_flag and since is not None:
        # Validate the ISO string via _parse_since (epoch conversion is
        # discarded — we pass the raw ISO through to mem_search_federated
        # so the SQL `created_at >=` comparison is lexicographic on the
        # YYYY-MM-DD HH:MM:SS TEXT format per design D7).
        try:
            _parse_since(since)
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(2)

    backend = _default_save_backend()

    if federated_flag:
        # REQ-25: federated multi-project search. Projects + type are
        # CSV-parsed; None means "no filter". --since is the raw ISO
        # string (validated above). ``trigger="cli"`` tags the
        # observability event so dashboards can separate user invocations
        # from programmatic ones (REQ-26 contract).
        raw = backend.mem_search_federated(
            query,
            projects=_parse_csv(projects),
            limit=k,
            since=since,
            type_filter=_parse_csv(type_csv),
            trigger="cli",
        )
    elif semantic_flag or hybrid_flag:
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


# ---------- REQ-21: flow reindex ----------


def _resolve_reindex_provider() -> Any:
    """Return the embedding provider to use for ``flow reindex``.

    Tries :class:`SentenceTransformersProvider` first (real model); falls
    back to :class:`MockEmbeddingProvider` when torch / sentence-transformers
    are unavailable so the reindex path stays runnable in test environments
    without the ``[vectors]`` extra. Both providers satisfy the same ABC,
    so the worker code is identical.
    """
    from flow_engineering.embedding_provider import (
        MockEmbeddingProvider,
        SentenceTransformersProvider,
    )

    try:
        return SentenceTransformersProvider()
    except Exception:  # EmbeddingProviderUnavailable or any ImportError.
        return MockEmbeddingProvider()


def _perform_reindex_batch(
    observations: list[dict],
    store: Any,
    provider: Any,
    *,
    simulate_crash_after: int | None = None,
) -> int:
    """Embed + upsert one batch of observations into ``store``.

    Returns the number of rows successfully upserted. When
    ``simulate_crash_after`` is set, the worker writes only that many rows
    of the batch and then raises — used by the REQ-21 crash-resume test to
    validate that the next run picks up where the first stopped.
    """
    from flow_engineering.binding import split_prose_and_refs

    texts = [split_prose_and_refs(str(o.get("content", "")))[0] for o in observations]
    embeddings = provider.embed_batch(texts)
    written = 0
    for o, vec in zip(observations, embeddings, strict=True):
        if simulate_crash_after is not None and written >= simulate_crash_after:
            raise RuntimeError("simulated crash mid-batch")
        store.add(str(o.get("id", o.get("observation_id"))), vec)
        written += 1
    return written


@main.command()
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Observations per embedding batch (default: 100).",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    default=False,
    help="Report the count without writing anything to the vector store.",
)
def reindex(batch_size: int, dry_run: bool) -> None:
    """Reindex every observation into the sqlite-vec store (REQ-21).

    Sync streaming: walks ``backend.iter_observations()`` in batches of
    ``--batch-size``, embeds the prose of each observation (with the
    trailing ``code_refs`` block stripped), and upserts the resulting
    vector into :class:`SqliteVecStore` at the path returned by
    :func:`_vectors_sqlite_path`. Writes are idempotent (INSERT OR REPLACE)
    and commit per batch, so a crash mid-run leaves the index in a
    consistent state — re-invoking ``flow reindex`` finishes the work.
    """
    if batch_size <= 0:
        click.echo(
            f"ERROR: --batch-size must be > 0, got {batch_size}", err=True
        )
        sys.exit(2)

    if not _sqlite_vec_available():
        click.echo(
            "reindex disabled: install [vectors] extra — "
            f"{VECTOR_INSTALL_HINT}",
            err=True,
        )
        sys.exit(2)

    backend = _default_save_backend()
    # Unwrap HybridBackend so we index the underlying prose store directly.
    inner_backend = getattr(backend, "inner", backend)
    observations = list(inner_backend.iter_observations())
    total = len(observations)

    if dry_run:
        # Count report only — no DB writes, no progress lines, no done line.
        click.echo(f"reindex: {total} observations need reindex", err=True)
        return

    if total == 0:
        # Empty corpus short-circuits with the no-op summary line so the
        # done-format is consistent across zero and non-zero runs.
        click.echo(
            "reindex: done — 0 observations indexed in 0.0s", err=True
        )
        observability.increment("reindex_observations_total", count=0)
        observability.increment("reindex_duration_seconds", value=0.0)
        return

    from flow_engineering.vectors import SqliteVecStore

    store = SqliteVecStore(_vectors_sqlite_path())
    provider = _resolve_reindex_provider()

    started = time.monotonic()
    done = 0
    for batch_start in range(0, total, batch_size):
        batch = observations[batch_start : batch_start + batch_size]
        done += _perform_reindex_batch(batch, store, provider)
        pct = int(done * 100 / total) if total else 100
        # Per-batch progress to stderr (REQ-21 contract: one line per batch).
        click.echo(f"reindex: {done}/{total} ({pct}%) embedded", err=True)
    elapsed = time.monotonic() - started
    click.echo(
        f"reindex: done — {total} observations indexed in {elapsed:.1f}s",
        err=True,
    )

    # REQ-22 observability: one counter batch per reindex invocation.
    observability.increment("reindex_observations_total", count=total)
    observability.increment("reindex_duration_seconds", value=float(elapsed))


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


@main.group(invoke_without_command=True)
@click.option("--json", "json_flag", is_flag=True, default=False,
              help="Emit machine-readable JSON instead of a text summary.")
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
    "--format", "fmt", default="text",
    type=click.Choice(["text", "json", "json-detailed"], case_sensitive=False),
    help="Output format (REQ-35: text default, json for machine-readable).",
)
@click.option(
    "--window", "window", default=None,
    help=(
        "Rolling time-window filter (REQ-35/REQ-36): preset "
        "(1h|24h|7d|30d) or custom '<int><h|d>' (e.g. 12h, 3d). "
        "Rolling relative to now (NOT calendar-aligned)."
    ),
)
@click.option(
    "--domain", "domain", default=None,
    type=click.Choice(SUMMARY_DOMAIN_CHOICES, case_sensitive=False),
    help=(
        "Prefix-based domain slice (REQ-37): "
        + "|".join(observability.ALL_DOMAINS)
        + ". The engine slot is reserved (REQ-42) and returns empty in v1."
    ),
)
@click.option(
    "--since", "since_iso", default=None, metavar="ISO8601",
    help="Absolute ISO 8601 lower bound: ts >= <iso> (REQ-36).",
)
@click.option(
    "--until", "until_iso", default=None, metavar="ISO8601",
    help="Absolute ISO 8601 upper bound: ts <= <iso> (REQ-36).",
)
def metrics_summary(
    fmt: str,
    window: str | None,
    domain: str | None,
    since_iso: str | None,
    until_iso: str | None,
) -> None:
    """Render the per-domain text dashboard (REQ-35 / change #6 PR#1 T1.2 + T1.5).

    Reads metrics.jsonl via the new :func:`observability.read_all_metrics`
    helpers, applies any active ``--window`` / ``--domain`` / ``--since` /
    ``--until`` filter, and renders the result via :func:`observability.summarize`.

    Default-empty contract (D8): empty / missing / no-match → exit 0 with
    ``"No metrics recorded yet."`` on stdout. Invalid ``--window`` /
    ``--since`` / ``--until`` values emit a stderr error and exit 2 (D9).
    """
    fmt_lower = fmt.lower()

    since_epoch: float | None = None
    if since_iso is not None:
        try:
            since_epoch = _parse_since(since_iso)
        except ValueError as exc:
            click.echo(f"invalid --since value: {exc}", err=True)
            sys.exit(2)

    until_epoch: float | None = None
    if until_iso is not None:
        try:
            until_epoch = _parse_since(until_iso)
        except ValueError as exc:
            click.echo(f"invalid --until value: {exc}", err=True)
            sys.exit(2)

    try:
        events = observability.read_all_metrics()
        if domain is not None:
            # click.Choice accepts mixed case (case_sensitive=False), but
            # DOMAIN_BY_PREFIX keys are lowercase — normalize before lookup.
            domain_normalized = observability.validate_domain(domain.lower())
            events = observability.read_events_by_domain(domain_normalized)
        if window is not None:
            events = observability.filter_by_window(events, window)
        if since_epoch is not None:
            events = [e for e in events if e.timestamp >= since_epoch]
        if until_epoch is not None:
            events = [e for e in events if e.timestamp <= until_epoch]
    except ValueError as exc:
        # read_events_by_domain raises on unknown domain; click's Choice
        # already covers the validation path, but defensive in case the
        # list is widened at runtime. Also catches parse_window errors.
        click.echo(str(exc), err=True)
        sys.exit(2)

    summary_data = observability.summarize(events)

    if fmt_lower == "text":
        if not any(summary_data.values()):
            click.echo("No metrics recorded yet.")
            return
        for d in sorted(summary_data):
            click.echo(f"{d}:")
            for counter, count in sorted(summary_data[d].items()):
                click.echo(f"  {counter}: {count}")
        return
    if fmt_lower in ("json", "json-detailed"):
        click.echo(json.dumps(summary_data, ensure_ascii=False, indent=2))
        return
    click.echo(f"unknown --format value: {fmt}", err=True)
    sys.exit(2)


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
@click.option(
    "--snapshot",
    "snapshot_id",
    default=None,
    help="REQ-33: drift-pinned scan via a stored snapshot. "
         "Reads frozen observations + graph.json from the envelope instead of live disk.",
)
def drift(
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


# ---------- REQ-24: flow projects backfill ----------


@main.group(name="projects")
def projects_group() -> None:
    """Manage project tags and aliases (REQ-24, REQ-27).


    Subcommands:
    - ``backfill``: re-tag observations safely (dry-run default + --confirm gate).
    - ``alias``: append a rename record to ``project-aliases.json`` (REQ-27, lands in T1.10).
    """


@projects_group.command(name="backfill")
@click.option(
    "--dry-run",
    "dry_run_flag",
    is_flag=True,
    default=False,
    help="Preview only (DEFAULT behaviour; no writes).",
)
@click.option(
    "--confirm",
    "confirm_flag",
    is_flag=True,
    default=False,
    help="REQUIRED to write changes. Without --confirm the command is read-only.",
)
@click.option(
    "--project",
    "project_key",
    default=None,
    help="Restrict scope to a single project key. Required when --confirm is passed.",
)
@click.option(
    "--since",
    default=None,
    help="Only observations with created_at >= this ISO 8601 timestamp (lexicographic).",
)
def projects_backfill(
    dry_run_flag: bool,
    confirm_flag: bool,
    project_key: str | None,
    since: str | None,
) -> None:
    """Re-tag observations safely (REQ-24, design D3 safety gate + REQ-27 alias iteration).

    The default mode is a DRY-RUN preview: every observation that would be
    re-tagged is listed in the JSON report on stdout, but the database is
    NOT touched. To apply changes the caller MUST pass ``--confirm``.

    Scope (which observations are eligible for re-tagging):

    - With ``--project=<key>``: observations currently WITHOUT a project tag
      (i.e. ``project is None or ""``) AND observations currently tagged
      ``<key>`` (the alias-driven re-tag path: ``--project=<alias.old>``
      re-tags observations currently tagged ``<alias.old>`` to
      ``<alias.new>`` when an alias exists).
    - Without ``--project``: iterate the alias map (``project-aliases.json``)
      and re-tag every observation whose CURRENT ``project`` matches an
      ``alias.old`` to the corresponding ``alias.new``. This closes the
      batch B2 deviation: the previously-refused invocation now resolves
      via the alias map (REQ-24 scenario 5 + REQ-27 integration).

    Safety gate (REQ-24 + REQ-27):
    - ``--confirm`` is REQUIRED to write; ``--dry-run`` is the default
      and overrides ``--confirm`` (a ``--dry-run --confirm`` invocation
      still does no writes).

    Exit codes:
    - 0: success (dry-run completed OR --confirm applied changes OR
      no-op with empty alias map).
    - 2: invalid args (``--since`` parse error).

    JSON output shape::

        {
          "would_change": <int>,
          "would_skip": <int>,
          "changes": [
            {
              "observation_id": <int>,
              "current_tag": <str | null>,
              "proposed_tag": <str | null>,
              "action": "rename" | "skip_already_tagged" | "skip_no_match"
            },
            ...
          ]
        }

    On ``--confirm`` the report lists the same shape, but the ``action``
    for entries that were actually applied is ``"tagged"`` (instead of
    ``"rename"``) so downstream tooling can distinguish preview vs applied.
    """
    if since is not None:
        try:
            _parse_since(since)
        except ValueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(2)

    from flow_engineering import project_aliases as _aliases

    backend = _default_save_backend()
    all_observations = list(backend.iter_observations())

    alias_records = _aliases.load_aliases()
    alias_map: dict[str, str] = {r["old"]: r["new"] for r in alias_records}

    candidates: list[dict[str, Any]]
    if project_key is not None:
        # Single-key scope (legacy REQ-24 + alias-key re-tag).
        candidates = [
            o
            for o in all_observations
            if (not o.get("project")) or o.get("project") == project_key
        ]
    else:
        # No --project: iterate the alias map (REQ-27 integration).
        candidates = [
            o
            for o in all_observations
            if o.get("project") in alias_map
        ]

    if since is not None:
        candidates = [
            o for o in candidates if str(o.get("created_at", "")) >= since
        ]

    would_change = 0
    would_skip = 0
    changes: list[dict[str, Any]] = []
    applied_action = "tagged" if confirm_flag else "rename"

    for obs in candidates:
        current_tag = obs.get("project")
        # Resolve the proposed tag for this row.
        if current_tag in alias_map:
            # Alias-driven re-tag (iteration path OR --project=<alias.old>).
            proposed_tag: str | None = alias_map[current_tag]
        elif project_key is not None and not current_tag:
            # Legacy REQ-24 untagged-observation path.
            proposed_tag = project_key
        else:
            proposed_tag = None

        if proposed_tag is None:
            action = "skip_no_match"
        elif proposed_tag == current_tag:
            action = "skip_already_tagged"
        else:
            action = applied_action

        change = {
            "observation_id": int(obs["id"]),
            "current_tag": current_tag,
            "proposed_tag": proposed_tag,
            "action": action,
        }
        changes.append(change)
        if action == applied_action:
            would_change += 1
            if confirm_flag and proposed_tag is not None:
                try:
                    _apply_tag(int(obs["id"]), proposed_tag, backend=backend)
                except Exception:
                    observability.increment("project_tag_backfill_failed_total")
                    continue
                observability.increment(
                    "project_tag_backfilled_total", from_=current_tag or "untagged"
                )
        else:
            would_skip += 1

    report = {
        "would_change": would_change,
        "would_skip": would_skip,
        "changes": changes,
    }
    click.echo(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0)


# ---------- REQ-27: flow projects alias ----------


@projects_group.command(name="alias")
@click.argument("old_key")
@click.argument("new_key")
def projects_alias(old_key: str, new_key: str) -> None:
    """Append a rename record to ``project-aliases.json`` (REQ-27).

    The alias map is the source of truth for renaming absorption:
    ``flow-image-generator-v2 → flow-image-generator-main`` is applied
    at every federated query so the user-facing contract treats the
    alias as a synonym.

    Exit codes:
    - 0: alias added (or already present — idempotent re-invoke).
    - 1: conflicting rewrite (existing alias for ``old_key`` already
      points to a different ``new_key``). The existing record is
      preserved unchanged so audit history is never silently lost.

    Stdout on success:
    - New alias: ``alias added: <old_key> -> <new_key>``.
    - Idempotent re-invoke: ``alias already present: <old_key> -> <new_key>``.

    On conflict, stderr reports the existing target so the user knows
    what to edit (or which entry to remove) before re-invoking.
    """
    from flow_engineering import project_aliases

    try:
        result = project_aliases.add_alias(old_key, new_key)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    status = result["status"]
    if status == "added":
        click.echo(f"alias added: {old_key} -> {new_key}")
        return
    if status == "already_present":
        click.echo(f"alias already present: {old_key} -> {new_key}")
        return
    # Defensive fallback — unknown statuses should not reach this point.
    click.echo(f"alias status: {status}", err=True)
    sys.exit(1)


# ---------- REQ-28..34: flow snapshot subcommand group (T1.5) ----------


def _build_snapshot_manager() -> SnapshotManager:
    """Construct a :class:`SnapshotManager` from the CLI defaults.

    Wires the snapshots dir (env override aware) + the default save
    backend so every ``flow snapshot`` subcommand gets a consistent
    facade without each command re-deriving the path.
    """
    return SnapshotManager(
        snapshots_dir=_resolve_snapshots_dir(),
        backend=_default_save_backend(),
    )


def _serialize_snapshot_meta(meta) -> dict:
    """Project a ``SnapshotMeta`` dataclass into the REQ-29 JSON shape.

    REQ-29 scenario 1 requires exactly six keys: ``snap_id``,
    ``created_at``, ``trigger``, ``description``, ``obs_count``,
    ``size_bytes``. Extra fields are exposed as additional JSON keys
    (introspection for ``flow metrics`` consumers).
    """
    return {
        "snap_id": meta.id,
        "created_at": meta.created_at,
        "trigger": meta.trigger,
        "description": meta.description,
        "obs_count": meta.obs_count,
        "size_bytes": meta.size_bytes,
        "include_graph": meta.include_graph,
        "binding_count": meta.binding_count,
        "project_count": meta.project_count,
    }


def _snapshot_diff_to_dict(diff) -> dict:
    """Project a ``SnapshotDiff`` dataclass into the REQ-31 JSON shape."""
    return diff.to_dict()


@main.group(name="snapshot")
def snapshot_group() -> None:
    """Manage immutable snapshots of the Engram observation graph (REQ-28..34).

    Subcommands:
    - ``create``  — write a new gzipped JSON snapshot.
    - ``list``    — list existing snapshots (newest first).
    - ``show``    — render a snapshot's full envelope.
    - ``diff``    — diff two snapshots OR snapshot-vs-live.
    - ``rollback`` — restore Engram state to a snapshot (with safety).
    - ``prune``   — retention-driven deletion (lands in T1.6).

    Exit-code conventions mirror the rest of the CLI: 0 = success, 2 =
    invalid args, 3 = safety refusal (rollback without ``--confirm``).
    """


@snapshot_group.command(name="create")
@click.option(
    "--description",
    "description_text",
    default="",
    help="Free-text note stored in the envelope's description field.",
)
@click.option(
    "--no-include-graph",
    "no_include_graph",
    is_flag=True,
    default=False,
    help="Exclude graph_state.graph_json_content from the envelope. "
         "Drift-pinned scans of such snapshots will refuse.",
)
@click.option(
    "--project",
    "project_key",
    default=None,
    help="Restrict to a single project at READ time only (D5). "
         "v1 snapshots always capture the full DB.",
)
def snapshot_create(
    description_text: str,
    no_include_graph: bool,
    project_key: str | None,
) -> None:
    """Write a new snapshot of the current Engram state (REQ-28).

    Default ``trigger='manual'``; auto-rollback-safety snapshots are
    written by ``flow snapshot rollback`` with ``trigger='rollback_safety'``.
    The snapshot file is written atomically (tempfile + Path.replace)
    so a crash mid-write cannot corrupt the directory.
    """
    manager = _build_snapshot_manager()
    snap_id = manager.create(
        description=description_text,
        trigger="manual",
        include_graph=not no_include_graph,
    )
    click.echo(snap_id)


@snapshot_group.command(name="list")
@click.option(
    "--since",
    default=None,
    help="Filter to snapshots with created_at >= this ISO 8601 timestamp.",
)
@click.option(
    "--limit",
    "limit",
    type=int,
    default=None,
    help="Maximum number of snapshots to return (default: 50).",
)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit the snapshot list as a JSON array (REQ-29 spec mandate; default output is also JSON for scriptability).",
)
def snapshot_list(since: str | None, limit: int | None, json_flag: bool) -> None:
    """List snapshots in reverse chronological order (REQ-29).

    Output is a JSON array of ``SnapshotMeta`` records with the 6 keys
    required by the spec (snap_id, created_at, trigger, description,
    obs_count, size_bytes) plus introspection fields. Empty dir ⇒ ``[]``.
    """
    manager = _build_snapshot_manager()
    entries = manager.list(since=since, limit=limit)
    payload = [_serialize_snapshot_meta(e) for e in entries]
    click.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@snapshot_group.command(name="show")
@click.argument("snap_id")
def snapshot_show(snap_id: str) -> None:
    """Render a snapshot's full envelope as pretty-printed JSON (REQ-30).

    On sha256 mismatch OR unknown ``snap_id`` the command exits non-zero
    with a JSON error object on stderr.
    """
    manager = _build_snapshot_manager()
    try:
        envelope = manager.show(snap_id)
    except SnapshotEnvelopeError as exc:
        click.echo(
            json.dumps(
                {"error": str(exc), "snap_id": snap_id},
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(2)
    click.echo(json.dumps(envelope, ensure_ascii=False, indent=2))


@snapshot_group.command(name="diff")
@click.argument("snap_id_a")
@click.argument("snap_id_b", required=False, default=None)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit the diff as a structured JSON object (REQ-31 spec mandate; default output is also JSON).",
)
def snapshot_diff(
    snap_id_a: str, snap_id_b: str | None, json_flag: bool
) -> None:
    """Diff two snapshots OR a snapshot against LIVE state (REQ-31).

    Two calling forms:

    - ``flow snapshot diff <a> <b>`` — diff two stored snapshots.
    - ``flow snapshot diff <a>`` — diff ``<a>`` against LIVE state
      (the snapshot-vs-live extension per REQ-31).

    Output is a structured JSON object with ``added``, ``removed``,
    ``modified``, ``unchanged_count``, ``summary`` keys.
    """
    manager = _build_snapshot_manager()
    try:
        diff = manager.diff(snap_id_a, snap_id_b)
    except SnapshotEnvelopeError as exc:
        click.echo(
            json.dumps(
                {"error": str(exc), "snap_id_a": snap_id_a, "snap_id_b": snap_id_b},
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(2)
    click.echo(
        json.dumps(_snapshot_diff_to_dict(diff), ensure_ascii=False, indent=2)
    )


@snapshot_group.command(name="rollback")
@click.argument("snap_id")
@click.option(
    "--confirm",
    "confirm_flag",
    is_flag=True,
    default=False,
    help="REQUIRED to write changes. Without --confirm the command refuses.",
)
@click.option(
    "--force",
    "force_flag",
    is_flag=True,
    default=False,
    help="Override conflict detection (DANGEROUS).",
)
def snapshot_rollback(
    snap_id: str, confirm_flag: bool, force_flag: bool
) -> None:
    """Restore the Engram state to match ``snap_id`` (REQ-32).

    Two-phase commit (D11):

    1. Auto-safety snapshot of CURRENT live state (trigger=rollback_safety).
    2. Atomic SQLite ``BEGIN IMMEDIATE`` apply of the target snapshot.

    Without ``--confirm`` the command refuses with exit code 3 and a
    JSON error on stderr. With ``--confirm`` but conflicts present,
    the command refuses with exit code 2 unless ``--force`` is also
    passed (which emits a stderr warning + applies anyway).
    """
    manager = _build_snapshot_manager()
    try:
        result = manager.rollback(
            snap_id, confirm=confirm_flag, force=force_flag
        )
    except RollbackRefusedError as exc:
        click.echo(
            json.dumps(exc.payload, ensure_ascii=False),
            err=True,
        )
        sys.exit(3)
    except RollbackConflictError as exc:
        click.echo(
            json.dumps(exc.payload, ensure_ascii=False),
            err=True,
        )
        sys.exit(2)
    except SnapshotEnvelopeError as exc:
        click.echo(
            json.dumps(
                {"error": str(exc), "snap_id": snap_id},
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(2)
    click.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


@snapshot_group.command(name="prune")
@click.option(
    "--keep-last",
    "keep_last",
    type=int,
    default=None,
    help="Keep the N most-recent snapshots; delete the rest (count filter).",
)
@click.option(
    "--keep-days",
    "keep_days",
    type=int,
    default=None,
    help="Keep snapshots newer than N days (age filter).",
)
@click.option(
    "--max-total-size-mb",
    "max_total_size_mb",
    type=int,
    default=None,
    help="Delete oldest-first until total size <= N MB (size filter).",
)
@click.option(
    "--confirm",
    "confirm_flag",
    is_flag=True,
    default=False,
    help="REQUIRED to actually delete. Without --confirm the command is "
         "dry-run and prints the would-delete list.",
)
@click.option(
    "--force",
    "force_flag",
    is_flag=True,
    default=False,
    help="Override the most-recent snapshot safety net (DANGEROUS).",
)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit the PruneResult as a JSON object on stdout.",
)
def snapshot_prune(
    keep_last: int | None,
    keep_days: int | None,
    max_total_size_mb: int | None,
    confirm_flag: bool,
    force_flag: bool,
    json_flag: bool,
) -> None:
    """Retention-driven deletion of snapshot files (REQ-34).

    Three retention filters are OR-combined: ``--keep-last`` (count),
    ``--keep-days`` (age), ``--max-total-size-mb`` (size). At least ONE
    MUST be supplied; otherwise the command refuses with exit code 2.

    Default (no ``--confirm``) is dry-run: ``PruneResult.dry_run`` is True
    and NO files are touched. The candidate set is printed to stdout as
    a ``"would delete"`` list so the operator can preview the impact.

    With ``--confirm``, the candidate set is deleted and the
    ``PruneResult.deleted`` list is the actually-applied deletions.

    Two safety invariants (REQ-34 D10) are non-negotiable:

    - The most-recent snapshot is NEVER deleted (unless ``--force``).
    - Pinned snapshots are NEVER deleted.

    Exit codes: 0 on success (including dry-run), 2 on no-filter /
    safety-gate, 4 on ``PruneSafetyGateError``.
    """
    manager = _build_snapshot_manager()
    try:
        result = manager.prune(
            keep_last=keep_last,
            keep_days=keep_days,
            max_total_size_mb=max_total_size_mb,
            confirm=confirm_flag,
            force=force_flag,
        )
    except PruneNoFilterError as exc:
        click.echo(
            json.dumps({"error": str(exc)}, ensure_ascii=False),
            err=True,
        )
        sys.exit(2)
    except PruneSafetyGateError as exc:
        click.echo(
            json.dumps(exc.payload, ensure_ascii=False),
            err=True,
        )
        sys.exit(4)

    if json_flag:
        click.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    # Human-readable default output. Dry-run prints "would delete"; apply
    # prints "deleted" so the operator can see what changed.
    if result.dry_run:
        click.echo(f"DRY-RUN: would delete {len(result.would_delete)} snapshots")
        click.echo(f"  reason: {result.reason!r}")
        for sid in result.would_delete:
            click.echo(f"  - {sid}")
        click.echo(f"would keep: {len(result.would_keep)}")
        return

    click.echo(f"deleted {len(result.deleted)} snapshots")
    click.echo(f"  reason: {result.reason!r}")
    for sid in result.deleted:
        click.echo(f"  - {sid}")
    click.echo(f"freed_bytes: {result.freed_bytes}")
    click.echo(f"kept: {len(result.would_keep)}")


if __name__ == "__main__":
    main()
