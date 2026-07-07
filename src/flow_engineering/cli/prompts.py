"""Prompts group extracted from cli/__init__.py (v1.3-cli-split, Slice 6).

Hosts the ``flow prompts`` Click group and its 4 subcommands (check, lint,
list, show), plus the private helpers used internally by those commands
(``_emit_check_observability``, ``_resolve_check_action``, the
:class:`CheckAction` dataclass, the 5 ``_entry_*`` / ``_format_*`` /
``_serialize_*`` / ``_render_*`` / ``_parse_var_pair`` prompts helpers,
and the module-level constants ``_PROMPT_REGISTRY_SCHEMA_VERSION``,
``_EXIT_UNKNOWN_PROMPT_ID``, ``_EXIT_GOLDEN_DRIFT``, ``_GOLDEN_PROMPTS_DIR``,
``_LINT_ERROR_CODES``, ``_LINT_WARNING_CODES``). The body below is a
verbatim relocation from ``cli/__init__.py`` lines 2052-2832 (post-Slice-1+
2+3+4+5; pre-Slice-1 equivalent lines 4494-5274 per tasks.md T-6) --
behavior MUST match pre-split exactly. Top-level imports were added here
because a module cannot see names that live in ``cli/__init__.py``'s
import block; the relocated body references the same names it did before
via function-body lazy imports (the Slice 3/4/5 precedent for cross-module
reference fixes).

Cross-cutting helpers retained in ``cli/__init__.py`` and resolved at
function-call time:

- ``_STATUS_LABELS`` (at ``cli/__init__.py:2037``) -- the drift-kind label
  map used by ``prompts_check``. Same lazy-import rationale as Slices 2-5:
  the helper lives ABOVE the prompts block in ``__init__.py`` so it stays
  cross-cutting; ``prompts_check`` re-fetches via ``from flow_engineering.cli
  import _STATUS_LABELS`` on each call.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from flow_engineering import observability  # for _emit_check_observability (REQ-22 prefix)
from flow_engineering.cli import main  # noqa: F401  (parent group; see design section 6)


# ---------- REQ-49 + REQ-50: flow prompts subcommand group (T2.1) ----------


def _emit_check_observability(
    drifts: list[Any], duration_seconds: float,
) -> None:
    """Emit the W2 observability counter set for one ``prompts check`` invocation.

    Four counter names are emitted (REQ-22 prefix convention; mirrors
    ``drift_*_total`` from drift-hardening + REQ-22 ``vector_*_total``):

    - ``prompts_check_total{result="clean"}`` — exactly once when no drift
      was detected.
    - ``prompts_check_total{result="drift"}`` — exactly once when at least
      one drift finding was reported.
    - ``prompts_check_drift_total{skill=<name>}`` — once per drift finding,
      tagged with the affected skill name (so the metrics surface can
      break down drift counts by skill).
    - ``prompts_check_duration_seconds`` — exactly once per invocation,
      with ``value=<elapsed>`` (gauge-style ``_seconds`` suffix counter;
      mirrors ``reindex_duration_seconds`` precedent).

    The function is best-effort and never raises; ``observability.increment``
    swallows ``OSError`` internally so a write failure to the JSONL sink
    cannot break the CLI flow.

    Args:
        drifts: The list of :class:`SkillDrift` from :func:`check_drift`.
        duration_seconds: Wall-clock duration of the check in seconds.
    """
    observability.increment(
        "prompts_check_total",
        result="drift" if drifts else "clean",
    )
    for drift in drifts:
        observability.increment(
            "prompts_check_drift_total",
            skill=drift.skill_name,
        )
    observability.increment(
        "prompts_check_duration_seconds",
        value=float(duration_seconds),
    )


@dataclass(frozen=True)
class CheckAction:
    """Resolved action for ``flow prompts check`` based on flag combinations.

    Attributes:
        catalog: The catalog dict to walk (filtered when ``--skill`` was
            passed; the full :data:`SKILL_CATALOG` otherwise).
        init_or_update: ``"init"`` for ``--init`` (bootstrap), ``"update"``
            for ``--update`` (refresh), ``None`` for the normal drift-check
            path. When set, the CLI side-steps ``check_drift`` and emits
            the init/update confirmation line.
        suppress_drift_exit: ``True`` when ``--no-fail`` was passed; the CLI
            keeps emitting drift lines but exits 0 instead of 1.
        unknown_skill: When ``--skill <name>`` did not match any catalog
            entry, this is the requested name; the CLI exits 3 with an
            error message and does NOT walk the catalog.
    """

    catalog: dict[str, Any]
    init_or_update: str | None
    suppress_drift_exit: bool
    unknown_skill: str | None


def _resolve_check_action(
    *,
    init_flag: bool,
    update_flag: bool,
    no_fail_flag: bool,
    skill_name: str | None,
    full_catalog: dict[str, Any],
) -> CheckAction:
    """Resolve the action implied by the flag combination.

    Pure function: takes the 4 flag values + the full catalog and returns
    a :class:`CheckAction` describing what the CLI should do. The caller
    (``prompts_check``) is responsible for emitting output and exit codes.

    Flag precedence:
    - ``--init`` wins over ``--update`` (first-write semantics).
    - ``--skill`` is applied to the normal drift-check path only; on
      ``--init`` / ``--update`` the full catalog is walked.
    - ``--no-fail`` only affects the drift-check path.
    """
    if init_flag:
        return CheckAction(full_catalog, "init", no_fail_flag, None)
    if update_flag:
        return CheckAction(full_catalog, "update", no_fail_flag, None)
    catalog = full_catalog
    unknown: str | None = None
    if skill_name is not None:
        filtered = {
            k: v for k, v in full_catalog.items() if v.skill_name == skill_name
        }
        if not filtered:
            unknown = skill_name
        else:
            catalog = filtered
    return CheckAction(catalog, None, no_fail_flag, unknown)


_LINT_ERROR_CODES = frozenset({"jinja_syntax", "invalid_version"})
"""Validation codes that map to "error" severity (CLI exit 2).

``jinja_syntax`` breaks render_prompt outright; ``invalid_version``
breaks the SemVer contract used by ``flow prompts show --version``.
Both are blocking and warrant the strict exit code per REQ-47 + REQ-50.
"""


_LINT_WARNING_CODES = frozenset(
    {"duplicate_name", "invalid_domain", "undefined_var"}
)
"""Validation codes that map to "warning" severity (CLI exit 1).

These are quality issues that don't break rendering but signal catalog
hygiene problems. Mirrors the ``drift-hardening`` precedent of using a
warning tier distinct from the error tier.
"""


@main.group(name="prompts")
def prompts_group() -> None:
    """Inspect and validate prompt registry + SKILL catalog (REQ-49 + REQ-50).

    Subcommands:
    - ``check`` — walk the SKILL_CATALOG and report drift findings.
    - ``lint``  — lint the inline prompt registry (REQ-47 surface).
    """


@prompts_group.command(name="check")
@click.option(
    "--init",
    "init_flag",
    is_flag=True,
    default=False,
    help="Bootstrap the sidecar JSON with current on-disk state, then exit 0.",
)
@click.option(
    "--update",
    "update_flag",
    is_flag=True,
    default=False,
    help="Re-compute and overwrite sidecar JSON checksums, then exit 0.",
)
@click.option(
    "--no-fail",
    "no_fail_flag",
    is_flag=True,
    default=False,
    help="Suppress exit 1 when drift is detected (CI warnings-only mode).",
)
@click.option(
    "--skill",
    "skill_name",
    default=None,
    help="Limit the check to the named skill (both surfaces: skill + prompt).",
)
def prompts_check(
    init_flag: bool,
    update_flag: bool,
    no_fail_flag: bool,
    skill_name: str | None,
) -> None:
    """Walk SKILL_CATALOG and report drift findings (REQ-49 + REQ-50).

    Exit codes:
    - 0: clean state (no drift detected) OR ``--init``/``--update`` succeeded
      OR ``--no-fail`` suppressed a drift-detected run.
    - 1: drift detected (one or more entries diverged). Suppressed by
      ``--no-fail``.
    - 3: usage error (e.g., ``--skill unknown`` with no matching catalog
      entry per design D9).

    Flags (per tasks-pr2.md T2.2 + verify-report-pr2a.md W1):
    - ``--init``: bootstrap the sidecar with current on-disk state.
    - ``--update``: re-compute and overwrite the sidecar JSON checksums
      (functionally equivalent to ``--init``; documented separately for
      intent: idempotent refresh vs first-run bootstrap).
    - ``--no-fail``: suppress exit 1 on drift detection (CI compat).
    - ``--skill <name>``: limit the catalog walk to the named skill's two
      surfaces (skill + prompt). Unknown names exit 3.

    Stdout format: ``<skill_name>/<surface>: <expected_version>: <status>``
    per design §"Data Flow / flow prompts check", followed by a footer
    ``N skills verified · M drift detected``.
    """
    from flow_engineering import opencode_skill_catalog as osc
    from flow_engineering.cli import _STATUS_LABELS  # noqa: F401  (lazy; lives in cli.__init__ post-Slice-6 - cross-cutting)

    action = _resolve_check_action(
        init_flag=init_flag,
        update_flag=update_flag,
        no_fail_flag=no_fail_flag,
        skill_name=skill_name,
        full_catalog=osc.SKILL_CATALOG,
    )

    if action.init_or_update == "init":
        count = osc.init_checksums()
        click.echo(
            f"Initialized {count} checksums · sidecar: {osc.SIDECAR_PATH}"
        )
        return
    if action.init_or_update == "update":
        count = osc.update_checksums()
        click.echo(
            f"Updated {count} checksums · sidecar: {osc.SIDECAR_PATH}"
        )
        return

    if action.unknown_skill is not None:
        click.echo(f"Unknown skill: {action.unknown_skill}", err=True)
        sys.exit(3)

    start = time.monotonic()
    drifts = osc.check_drift(action.catalog)
    elapsed = time.monotonic() - start
    _emit_check_observability(drifts, elapsed)

    for drift in drifts:
        status = _STATUS_LABELS.get(drift.drift_kind, "DRIFT")
        click.echo(
            f"{drift.skill_name}/{drift.surface}: "
            f"{drift.expected_version}: {status}"
        )

    drift_count = len(drifts)
    catalog_size = len(action.catalog)
    click.echo(
        f"{catalog_size} skills verified · {drift_count} drift detected"
    )

    if drift_count > 0:
        click.echo(
            f"[WARN] flow prompts check: {drift_count} drifts detected "
            f"— see stdout for details",
            err=True,
        )

    if drift_count > 0 and not action.suppress_drift_exit:
        sys.exit(1)


@prompts_group.command(name="lint")
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit the lint report as a JSON object on stdout.",
)
def prompts_lint(json_flag: bool) -> None:
    """Lint the inline prompt registry (REQ-47 surface, REQ-50 wrapper).

    Exit codes:
    - 0: clean registry (no warnings, no errors).
    - 1: warnings only (no errors).
    - 2: errors detected.

    Stdout default format: ``<prompt_id>: <error_code>: <message>`` lines
    followed by a footer ``N prompts linted · M warnings · K errors``.
    With ``--json``, the full :class:`LintReport.to_dict()` shape is
    emitted instead (machine-readable; mirrors REQ-8 ``flow metrics --json``).
    """
    from flow_engineering import prompt_registry

    report = prompt_registry.lint_prompts()
    warning_count = sum(
        1 for e in report.errors if e.error_code in _LINT_WARNING_CODES
    )
    error_count = sum(
        1 for e in report.errors if e.error_code in _LINT_ERROR_CODES
    )

    if json_flag:
        click.echo(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        for err in report.errors:
            click.echo(
                f"{err.prompt_name}: {err.error_code}: {err.message}"
            )
        catalog_size = len(report.catalog)
        click.echo(
            f"{catalog_size} prompts linted · "
            f"{warning_count} warnings · {error_count} errors"
        )

    if error_count > 0:
        sys.exit(2)
    if warning_count > 0:
        sys.exit(1)


# ---------- REQ-50 T3.1: flow prompts list subcommand ----------


_PROMPT_REGISTRY_SCHEMA_VERSION: str = "1.0"
"""Catalog-wide schema version for the prompt-registry entries.

Mirrors the spec REQ-50 schema_version contract. Surfaced via
``flow prompts list --json`` so downstream consumers can detect
catalog-shape drift between runtime + capability spec.
"""


def _entry_domain_value(entry: Any) -> str:
    """Return ``entry.domain.value`` as a string (defensive fallback).

    Defensive helper used by both the text-table and JSON serializers
    so a non-enum domain (e.g., a future ``str`` direct value) still
    renders. Mirrors the convention used in
    ``opencode_skill_catalog.py`` for surface handling.
    """
    domain = entry.domain
    return domain.value if hasattr(domain, "value") else str(domain)


def _entry_owner(entry: Any) -> str:
    """Render the spec-mandated owner string ``flow/{domain_value}``.

    Centralized so the text table + JSON serializer stay in lockstep
    with the spec REQ-50 S1 owner notation.
    """
    return f"flow/{_entry_domain_value(entry)}"


def _entry_location(entry: Any) -> str:
    """Render the spec-mandated location string ``prompts/<name>.j2``.

    Per W3 carry-forward: the canonical location is the repo-root
    ``prompts/`` directory; ``.j2`` suffix per design D1+D2.
    """
    return f"prompts/{entry.name}.j2"


def _format_prompts_list_row(entry: Any) -> str:
    """Format one PROMPT_NAMES row for the `flow prompts list` text table.

    Columns: ``prompt_id`` (24-wide), ``version`` (10-wide), ``owner``
    (24-wide), ``location``. The owner is rendered as
    ``flow/{domain.value}`` so it matches the spec REQ-50 S1 verbatim
    (``flow/observability`` / ``flow/binding``).
    """
    return (
        f"{entry.name:<24}  "
        f"{entry.version:<10}  "
        f"{_entry_owner(entry):<24}  "
        f"{_entry_location(entry)}"
    )


def _render_prompts_list_table(entries: list[Any]) -> str:
    """Pretty-print the prompts list as a fixed-width text table.

    Returns the full multi-line string (header + rows + footer). Mirrors
    the ``flow metrics`` table layout precedent per REQ-8.
    """
    headers = ("prompt_id", "version", "owner", "location")
    sep = "-" * 78
    lines: list[str] = []
    lines.append("  ".join(h.upper().ljust(24) for h in headers))
    lines.append(sep)
    for entry in entries:
        lines.append(_format_prompts_list_row(entry))
    lines.append(sep)
    lines.append(f"{len(entries)} prompt entries")
    return "\n".join(lines)


def _serialize_prompts_list(entries: list[Any]) -> dict[str, Any]:
    """Project PROMPT_NAMES entries into the REQ-50 ``--json`` shape.

    Shape: ``{"prompts": [...], "count": N, "registry_schema_version": "1.0"}``
    where each prompt entry has ``prompt_id``, ``domain``, ``version``,
    ``owner`` (``flow/{domain.value}``), ``variables`` (list), ``location``.

    Per T3.13 W-A1 carry-forward (verify-report-pr2b.md W-A1): the
    pre-T3.13 implementation emitted ``{name, version, owner, location,
    domain}`` with NO ``variables`` field; downstream consumers could
    not introspect declared variables from the JSON alone. The spec
    (REQ-50 S1) mandates ``variables: list`` + uses the user-facing key
    ``prompt_id`` (instead of the impl field ``name``); both keys are
    now included for backward compat with any pre-T3.13 consumer that
    still reads ``name``.
    """
    prompts: list[dict[str, Any]] = []
    for entry in entries:
        domain_value = _entry_domain_value(entry)
        declared_vars = list(entry.metadata.get("variables", ()))
        prompts.append(
            {
                "prompt_id": entry.name,
                "name": entry.name,
                "domain": domain_value,
                "version": entry.version,
                "owner": _entry_owner(entry),
                "variables": declared_vars,
                "location": _entry_location(entry),
            }
        )
    return {
        "prompts": prompts,
        "count": len(prompts),
        "registry_schema_version": _PROMPT_REGISTRY_SCHEMA_VERSION,
    }


@prompts_group.command(name="list")
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="Emit machine-readable JSON instead of a text table.",
)
def prompts_list(json_flag: bool) -> None:
    """List every prompt in the registry (REQ-50 S1).

    Default text output: a fixed-width table with columns
    ``prompt_id`` / ``version`` / ``owner`` / ``location``, followed
    by a footer ``N prompt entries``. Owners are rendered as
    ``flow/{domain.value}`` to match the spec verbatim
    (``flow/observability`` / ``flow/binding``).

    ``--json`` emits the flat-dict shape that mirrors REQ-8
    ``flow metrics --json``: ``{"prompts": [...], "count": N,
    "registry_schema_version": "1.0"}``.

    Exit codes: 0 always (this is a read-only introspection command).
    """
    from flow_engineering import prompt_registry

    entries = prompt_registry.list_prompts()
    if json_flag:
        click.echo(
            json.dumps(
                _serialize_prompts_list(entries),
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    click.echo(_render_prompts_list_table(entries))


# ---------- REQ-50 T3.2: flow prompts show <id> subcommand ----------


_EXIT_UNKNOWN_PROMPT_ID: int = 5
"""Exit code for ``flow prompts show <unknown>`` per design D9."""


_EXIT_GOLDEN_DRIFT: int = 3
"""Exit code for ``flow prompts show --check-snapshot`` on drift (REQ-V1.2.2)."""


_GOLDEN_PROMPTS_DIR: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "tests"
    / "golden"
    / "prompts"
)
"""Canonical on-disk location for the 4 PROMPT_NAMES golden snapshots.

REQ-V1.2.2: per ``openspec/changes/v1.2-followups/explore.md`` REQ-48
section, the 4 PROMPT_NAMES entries each get a byte-identical snapshot
under ``tests/golden/prompts/`` so unintentional template edits fail CI
with a precise drift message. The ``--update-goldens`` flag writes the
canonical render here; ``--check-snapshot`` compares the canonical
render to the file at this path. Tests override this constant via
``monkeypatch.setattr`` to isolate from the committed artifacts.
"""


def _parse_var_pair(raw: str) -> tuple[str, str]:
    """Parse a ``key=value`` string into ``(key, value)`` tuple.

    Used by ``flow prompts show --var`` to convert each Click value into
    a kwarg pair. ``=`` is the only separator; keys with ``=`` in the
    value are NOT supported (mirrors the spec REQ-50 S2 grammar).
    """
    if "=" not in raw:
        raise click.BadParameter(
            f"--var must be key=value (got {raw!r}); expected '=' separator",
            param_hint="--var",
        )
    key, _, value = raw.partition("=")
    key = key.strip()
    if not key:
        raise click.BadParameter(
            f"--var key cannot be empty (got {raw!r})",
            param_hint="--var",
        )
    return key, value


@prompts_group.command(name="show")
@click.argument("prompt_id")
@click.option(
    "--var",
    "var_pairs",
    multiple=True,
    callback=lambda _ctx, _param, values: [
        _parse_var_pair(v) for v in values
    ],
    help=(
        "Variable substitution as key=value (repeatable; last-write-wins). "
        "Per spec REQ-50 S2: missing declared vars get the "
        "literal sentinel <{var_name}>."
    ),
)
@click.option(
    "--render-count",
    is_flag=True,
    help=(
        "Emit a one-line summary of render-count + last-rendered-at from "
        "the prompt render sink (REQ-V1.1.3). Composes with the rendered body."
    ),
)
@click.option(
    "--render-history",
    "render_history",
    type=int,
    default=0,
    help=(
        "Emit the last N JSONL records for this prompt id as an aligned "
        "text table (REQ-V1.1.3; default N=5 when the flag is passed "
        "without a value). Composes with the rendered body."
    ),
)
@click.option(
    "--show-render-history",
    "show_render_history",
    is_flag=True,
    default=False,
    help=(
        "Boolean toggle for the render-history view at default N=5 "
        "(REQ-V1.1.3). Use ``--render-history 10`` to override N explicitly."
    ),
)
@click.option(
    "--update-goldens",
    "update_goldens",
    is_flag=True,
    default=False,
    help=(
        "Regenerate the golden snapshot file at "
        "``tests/golden/prompts/<id>.txt`` with the canonical render "
        "(REQ-V1.2.2). Use after an intentional template change to "
        "refresh the committed snapshot. Composes with the existing "
        "rendered body output."
    ),
)
@click.option(
    "--check-snapshot",
    "check_snapshot",
    is_flag=True,
    default=False,
    help=(
        "Compare the canonical render against the golden snapshot file "
        "at ``tests/golden/prompts/<id>.txt`` (REQ-V1.2.2). Exits 3 + "
        "emits 'snapshot drift detected' to stderr on mismatch; exits 0 "
        "on match. Use in CI to gate merges on snapshot freshness."
    ),
)
def prompts_show(
    prompt_id: str,
    var_pairs: list[tuple[str, str]],
    render_count: bool,
    render_history: int,
    show_render_history: bool,
    update_goldens: bool,
    check_snapshot: bool,
) -> None:
    """Render a prompt by id with optional --var substitutions (REQ-50 S2).

    Output: metadata header (``prompt_id:``, ``version:``, ``variables:``)
    + rendered template body + footer noting the render source + the
    autoescape status. Uses ``render_prompt_safe()`` so missing declared
    variables surface as ``<{var_name}>`` sentinels (per design D4 + OQ-4).

    The ``--render-count`` + ``--render-history [N]`` flags (REQ-V1.1.3)
    surface the prompt render sink content without coupling to the
    registry. They compose with the rendered body — they do NOT
    replace it.

    Exit codes:
    - 0: rendered successfully (or sentinel substitution).
    - 5: unknown ``prompt_id`` (emits JSON error on stderr).
    """
    from flow_engineering import prompt_registry
    from flow_engineering.cli import _GOLDEN_PROMPTS_DIR  # noqa: F401  (lazy; test seam - TestGoldenUpdate monkeypatches flow_engineering.cli._GOLDEN_PROMPTS_DIR via golden_snapshot_dir fixture, post-Slice-6)

    try:
        entry = prompt_registry.get_prompt(prompt_id)
    except KeyError:
        click.echo(
            json.dumps(
                {
                    "error": "unknown prompt id",
                    "prompt_id": prompt_id,
                    "hint": "run 'flow prompts list' to see available",
                },
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(_EXIT_UNKNOWN_PROMPT_ID)

    declared = list(entry.metadata.get("variables", ()))
    safe_kwargs: dict[str, str] = dict(var_pairs)
    # Per D4 + OQ-4: substitute the literal sentinel for missing
    # declared variables BEFORE rendering (render_prompt_safe has its
    # own logic but we pre-substitute here so the header + body use
    # the same source-of-truth).
    for var_name in declared:
        if var_name not in safe_kwargs:
            safe_kwargs[var_name] = f"<{var_name}>"

    # REQ-V1.2.2 (T2.4 GREEN): golden snapshot flags. The snapshot
    # comparison uses the CANONICAL render (via ``render_prompt_canonical``)
    # which is independent of the user's --var pairs so the snapshot
    # file is deterministic across operator invocations.
    if update_goldens or check_snapshot:
        canonical_render = prompt_registry.render_prompt_canonical(prompt_id)
        snap_path = _GOLDEN_PROMPTS_DIR / f"{prompt_id}.txt"
        if update_goldens:
            try:
                _GOLDEN_PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
                snap_path.write_text(canonical_render, encoding="utf-8")
            except OSError as exc:
                click.echo(
                    json.dumps(
                        {
                            "error": "snapshot_write_failed",
                            "prompt_id": prompt_id,
                            "path": str(snap_path),
                            "reason": str(exc),
                        },
                        ensure_ascii=False,
                    ),
                    err=True,
                )
                sys.exit(_EXIT_GOLDEN_DRIFT)
            click.echo(
                f"snapshot updated: {snap_path} ({len(canonical_render)} bytes)"
            )
        if check_snapshot:
            if not snap_path.exists():
                click.echo(
                    json.dumps(
                        {
                            "error": "snapshot_missing",
                            "prompt_id": prompt_id,
                            "path": str(snap_path),
                            "hint": "run 'flow prompts show <id> --update-goldens' first",
                        },
                        ensure_ascii=False,
                    ),
                    err=True,
                )
                sys.exit(_EXIT_GOLDEN_DRIFT)
            existing = snap_path.read_text(encoding="utf-8")
            if existing != canonical_render:
                click.echo(
                    json.dumps(
                        {
                            "error": "snapshot_drift_detected",
                            "message": "snapshot drift detected",
                            "prompt_id": prompt_id,
                            "path": str(snap_path),
                            "expected_bytes": len(canonical_render),
                            "found_bytes": len(existing),
                            "hint": (
                                "run 'flow prompts show <id> --update-goldens' "
                                "if the template change was intentional"
                            ),
                        },
                        ensure_ascii=False,
                    ),
                    err=True,
                )
                sys.exit(_EXIT_GOLDEN_DRIFT)
            click.echo(f"snapshot OK: {snap_path}")

    try:
        rendered = prompt_registry.render_prompt_safe(prompt_id, **safe_kwargs)
    except Exception as exc:
        click.echo(
            json.dumps(
                {
                    "error": "render failed",
                    "prompt_id": prompt_id,
                    "reason": str(exc),
                },
                ensure_ascii=False,
            ),
            err=True,
        )
        sys.exit(_EXIT_UNKNOWN_PROMPT_ID)

    # W5 carry-forward: the 4 migrated entries use Python
    # ``.format()`` syntax (``{test_command}``); Jinja2 leaves those
    # braces literal. Fall back to ``.format()`` for the body so the
    # rendered output reflects the user's kwargs (mirrors the
    # ``render_prompt`` fallback path). Sentinels are written as
    # ``<test_command>`` so they survive the .format() pass (the
    # angle-brackets are not Python format placeholders).
    if "{" in rendered and "}" in rendered:
        import contextlib
        with contextlib.suppress(KeyError, IndexError):
            # Missing positional or named placeholder — leave the
            # Jinja2-rendered body as-is; the sentinel subs still
            # show in the output via the header line.
            rendered = rendered.format(**safe_kwargs)

    click.echo(f"prompt_id:   {entry.name}")
    click.echo(f"version:     {entry.version}")
    click.echo(f"owner:       {_entry_owner(entry)}")
    click.echo(f"variables:   {{{', '.join(f'{k}: {v}' for k, v in safe_kwargs.items())}}}")
    click.echo("-" * 64)
    click.echo(rendered)
    click.echo("-" * 64)
    click.echo(
        f"(rendered via Jinja2 · autoescape=on · source: {_entry_location(entry)})"
    )

    # REQ-V1.1.3 S2: render-count + render-history flags surface the
    # prompt render sink content. Best-effort: a missing sink file
    # means zero renders — emit a friendly note instead of crashing.
    from flow_engineering.prompt_render_log import PromptRenderLog

    sink = PromptRenderLog()
    history_n = render_history if render_history > 0 else 0
    if show_render_history and history_n == 0:
        history_n = 5

    if render_count or history_n > 0:
        try:
            events = sink.read_all()
        except OSError as exc:
            click.echo(
                f"warning: could not read prompt render sink: {exc}",
                err=True,
            )
            events = []

        matching = [e for e in events if e.prompt_id == prompt_id]

        if render_count:
            last_at = (
                max((e.rendered_at for e in matching), default=None)
            )
            last_iso = (
                datetime.fromtimestamp(last_at, tz=UTC).isoformat()
                if last_at is not None
                else "never"
            )
            click.echo(
                f"render_count: {len(matching)} (last rendered_at: {last_iso})"
            )

        if history_n > 0:
            tail = matching[-history_n:]
            click.echo(f"render_history (last {len(tail)}):")
            if not tail:
                click.echo("  (no records)")
            else:
                click.echo(
                    f"  {'rendered_at':<22} {'status':<6} {'elapsed_ms':<10} error"
                )
                for ev in tail:
                    status = "ok" if ev.ok else "fail"
                    click.echo(
                        f"  {ev.rendered_at:<22.3f} {status:<6} "
                        f"{ev.elapsed_ms:<10.2f} {ev.error or ''}"
                    )


