"""Snapshot group extracted from cli/__init__.py (v1.3-cli-split, Slice 5).

Hosts the ``flow snapshot`` Click group and its subcommands (create,
list, show, diff, rollback, prune), plus the private helpers used
internally by those commands (``_build_snapshot_manager``,
``_serialize_snapshot_meta``, ``_snapshot_diff_to_dict``). The body
below is a verbatim relocation from ``cli/__init__.py`` lines 2020-2396
(post-Slice-1+2+3+4; pre-Slice-1 equivalent lines 4103-4493 per
tasks.md T-5) -- behavior MUST match pre-split exactly. Top-level
imports were added here because a module cannot see names that live in
``cli/__init__.py``'s import block; the relocated body references the
same names it did before.

Lazy imports inside ``_build_snapshot_manager`` resolve
``_resolve_snapshots_dir`` (now in ``cli.drift`` post-Slice-4) and
``_default_save_backend`` (stays in ``cli.__init__`` as a cross-cutting
helper used by snapshot AND drift groups) at function-call time. Those
helpers cannot be bound at module-import time without circular imports
(workspace.py / project.py precedent applies).
"""

from __future__ import annotations

import json
import sys
from typing import Any

import click

from flow_engineering.cli import main  # noqa: F401  (parent group; see design §6)
from flow_engineering.snapshot_manager import (
    PruneNoFilterError,
    PruneSafetyGateError,
    RollbackConflictError,
    RollbackRefusedError,
    SnapshotDiff,
    SnapshotEnvelopeError,
    SnapshotManager,
    SnapshotMeta,
)

# ---------- REQ-28..34: flow snapshot subcommand group (T1.5) ----------


def _build_snapshot_manager() -> SnapshotManager:
    """Construct a :class:`SnapshotManager` from the CLI defaults.

    Wires the snapshots dir (env override aware) + the default save
    backend so every ``flow snapshot`` subcommand gets a consistent
    facade without each command re-deriving the path.
    """
    from flow_engineering.cli import (
        _default_save_backend,  # noqa: F401  (lazy; lives in cli.__init__ post-Slice-5)
    )
    from flow_engineering.cli.drift import (
        _resolve_snapshots_dir,  # noqa: F401  (lazy; lives in cli.drift post-Slice-4)
    )
    return SnapshotManager(
        snapshots_dir=_resolve_snapshots_dir(),
        backend=_default_save_backend(),
    )


def _serialize_snapshot_meta(meta: SnapshotMeta) -> dict[str, Any]:
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


def _snapshot_diff_to_dict(diff: SnapshotDiff) -> dict[str, Any]:
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


