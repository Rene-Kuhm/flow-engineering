# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/).

## [1.3.0-alpha] - 2026-07-06


### Changed
- README.md rewrote from 1.1 KB to ~7 KB with badges, architecture
  section, capabilities matrix, compatibility table, OpenCode plugin
  mention, and contribution link. Removed stale PR-1-bootstrap status
  line and stale cross-refs to propose/design/spec/tasks.md (canonical
  path is openspec/changes/{name}/). (REQ-V1.3.3)
### BREAKING
- **`flow archive` becomes a Click group** (REQ-V1.3.4): the v1.2
  ``flow archive <change> --in <target>`` surface moves to
  ``flow archive change <change> --in <target>``. Mirrors the v1.2.0
  ``flow drift <change>`` → ``flow drift run <change>`` precedent
  (REQ-V1.2.4). v1.2 cron jobs / shell aliases pointing at the old
  form must update to the new form. The renamed surface preserves the
  full flag set (`--in`, `--diff`, `--no-graphify`) and the same skill
  version-gate exit code 4 on sdd-archive minimum-version violation.

### Added
- `flow archive rotate [--older-than Nd] [--dry-run] [--format yaml|json]`
  read-only preview command (REQ-V1.3.4 / v1.3 sub-change d). Lists entries
  in `openspec/changes/archive/` older than N days (default 90). Default
  behavior is dry-run; never mutates disk. Emits YAML or JSON to stdout.
  Includes a Windows mtime fallback (`git log -1 --format=%ct`) for
  filesystem/git-checkout skew. Destructive rotation deferred to
  `chore/archive-rotation-2026`.

## [1.2.0] - 2026-06-28

### BREAKING
- **Path A subcommand group rename** (REQ-V1.2.4): the drift events
  read-side CLI group moves from the top-level hyphenated form to a
  nested group under the new `drift` namespace. The pre-v1.2 surface
  `flow drift-events {list,tail,stats}` becomes a 1-release
  `deprecated=True` Click group alias; the new canonical surface is
  `flow drift events {list,tail,stats}` (nested under `flow drift`,
  mirroring the `flow metrics {summary,export,aggregate}` and
  `flow prompts {list,show,render}` group pattern). The detection
  subcommand also moves into the new namespace as `flow drift run <change>`
  (the legacy `flow drift <change>` positional form is REPLACED — use
  the explicit `flow drift run <change>` from now on). The hyphenated
  alias `flow drift-events` is REMOVED in v1.3 per the
  `SnapshotGraphMissing` v1.1 precedent.

  **Migration**:
  - `flow drift <change>` → `flow drift run <change>` (explicit subcommand)
  - `flow drift-events list` → `flow drift events list` (nested group)
  - `flow drift-events tail` → `flow drift events tail`
  - `flow drift-events stats` → `flow drift events stats`

### Added
- `flow drift events {list,tail,stats}` canonical subcommand group
  (REQ-V1.2.4): the drift events read-side now lives under the new
  `flow drift` group namespace as `flow drift events {list,tail,stats}`,
  sharing the same parent group as `flow drift run <change>`. Mirrors
  the existing `flow metrics` / `flow prompts` group pattern.
- `flow drift-events` 1-release DEPRECATED Click group alias: preserved
  for backwards compatibility with v1.0 / v1.1 operators that have
  shell aliases / cron jobs / docs pointing at the hyphenated name.
  Emits a `DeprecationWarning` to stderr on every invocation and
  delegates to the canonical subcommands via `ctx.forward()`. Removed
  in v1.3.

### Migration
- Shell aliases / cron jobs / docs pointing at the pre-v1.2 surface
  `flow drift-events {list,tail,stats}` will emit a `DeprecationWarning`
  but continue to work through v1.2. To opt into the new canonical
  surface, replace `flow drift-events` with `flow drift events` in
  scripts and aliases. The detection subcommand `flow drift <change>`
  becomes `flow drift run <change>` (no backwards-compat shim — the
  positional change_name is the most semantically distinct command in
  the group; explicit form is unambiguous).
- The full v1.2 release (BREAKING) closes the 4 carry-forwards from
  v1.1: REQ-44 metrics.jsonl rotation (PR#2a), REQ-48 golden
  regression tests (PR#2b), REQ-54 `min_sdd_skill_versions` gate
  (PR#2c), and Path A subcommand group rename (PR#2d).

## [1.2.0c] - 2026-06-28

### Added
- `[tool.flow_engineering] min_sdd_skill_versions` enforcement
  (REQ-V1.2.3 / REQ-54): project-pinned minimum-version dict for the
  8 orchestrator-dispatched sdd-* agents (`sdd-explore` / `sdd-propose`
  / `sdd-spec` / `sdd-design` / `sdd-tasks` / `sdd-apply` / `sdd-verify`
  / `sdd-archive`). The three `flow apply` / `flow verify` /
  `flow archive` Click commands now enforce this gate at startup:
  on-disk `~/.config/opencode/skills/<name>/SKILL.md` files below the
  declared minimum trigger exit code 4 + a structured JSON remediation
  payload on stderr pointing at `pip install --upgrade gentle-ai`.
  - New `enforce_min_skill_versions(min_versions)` helper in
    `opencode_skill_catalog.py` reuses the existing `SkillVersionError`
    exception (no new exception hierarchy needed).
  - Pre-release version strings like `"3.0-beta"` parse via a tolerant
    `_parse_major_minor()` helper that strips the suffix and returns
    `(3, 0)`. Malformed versions fall back to `(0, 0)` so the gate
    fires correctly (any minimum > 0.0 is satisfied).

### Migration
- Project operators on an outdated OpenCode runtime (e.g., sdd-apply
  2.5 vs the codebase's 3.0 minimum) will see exit code 4 from
  `flow apply` / `flow verify` / `flow archive` instead of silent
  breakage. Run `pip install --upgrade gentle-ai` to refresh the
  on-disk `SKILL.md` files.

## [1.2.0b] - 2026-06-28

### Added
- Golden regression tests for the prompt registry (REQ-V1.2.2 / REQ-48):
  the 4 `PROMPT_NAMES` entries (`strict_tdd`, `auto_suggest_header`,
  `auto_suggest_footer`, `auto_suggest_empty`) each get a byte-identical
  snapshot under `tests/golden/prompts/`. Unintentional template edits
  (whitespace, punctuation, escape chars) fail CI with a precise drift
  message instead of passing the 21 happy-path render tests. New
  `prompt_registry.render_prompt_canonical(prompt_id, **overrides)`
  helper injects canonical sentinel values (`test_command="TEST_COMMAND"`
  for `strict_tdd`; `{}` for the others) so the snapshot does NOT
  depend on caller kwargs. New CLI flags on `flow prompts show <id>`:
  - `--update-goldens` — regenerate the snapshot file with the canonical
    render. Use after an intentional template change.
  - `--check-snapshot` — compare the canonical render against the
    snapshot file; exit 3 + emit `snapshot drift detected` to stderr on
    mismatch; exit 0 on match. Use in CI to gate merges.

## [1.2.0a] - 2026-06-28

### Added
- `metrics.jsonl` rotation hardening (REQ-V1.2.1 / REQ-44): the metrics
  sink at `~/.flow-engineering/metrics.jsonl` now auto-rotates when the
  size threshold (`FLOW_METRICS_LOG_MAX_BYTES`, default 10 MB) is
  exceeded, mirroring the `DriftEventLog` rotation pattern shipped in
  v1.1.0 (REQ-V1.1.1). Sibling files older than the age threshold
  (`FLOW_METRICS_LOG_MAX_AGE_DAYS`, default 30 days) are deleted
  best-effort. All filesystem operations are wrapped in
  `try/except OSError` so a slow FS never crashes `increment()`.

## [1.1.0] - 2026-06-28

### Added
- `DriftEventLog` JSONL rotation hardening (REQ-V1.1.1 / REQ-44): the
  drift event log now auto-rotates when either the size threshold
  (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES`, default 10 MB) or age threshold
  (`FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS`, default 30 days) is exceeded.
  Best-effort: rotation failures (full disk, permission denied) never
  crash the daemon; one-time stderr WARN per path.
- Prompt render observability counters (REQ-V1.1.4 / REQ-52): three new
  counters flow through `observability.increment()`:
  * `prompts_render_total{domain, prompt_id, status}` — every render.
  * `prompts_render_ms{domain, prompt_id, count}` — wall-clock duration.
  * `prompts_render_failed_total{domain, prompt_id, error}` — failures only
    (`error` = `missing_var` / `template_error` / `unknown`).
  Surface via `flow metrics --domain prompt` (per D10 in proposal).
- `docs/prompts.md` auto-generated from `PROMPT_NAMES` + `prompts/*.j2`
  (REQ-V1.1.5 / REQ-53). Regenerate via `python scripts/generate_prompts_doc.py`
  or `make docs`. The script is idempotent — repeated runs produce
  byte-identical output.
- Prompt render JSONL sink (REQ-V1.1.3 / REQ-51): `record_prompt_render()`
  writes to `~/.flow-engineering/prompt_renders.jsonl` (opt-in via
  `FLOW_PROMPT_LOG=1`, default OFF). `flow prompts show <id>
  --render-count N` reads the last N events; `--render-history` prints
  the full sequence for one prompt.

### Changed
- `SnapshotGraphMissing` is now a 1-release alias for the canonical
  `SnapshotGraphMissingError` in `flow_engineering.snapshot_manager`
  (REQ-V1.1.6). Both names refer to the same class; importing the
  legacy name emits a `DeprecationWarning` and will be removed in v1.2.
  The independent `decision_drift.SnapshotGraphMissing(ValueError)` is
  unchanged for backwards compat with batch B1 BDD tests.
- `decision_drift.DriftClass` now uses `StrEnum` (was `str, Enum`); pure
  ruff auto-fix (`UP042`), semantically equivalent on Python 3.11+.

### Migration
- Code importing `from flow_engineering.snapshot_manager import
  SnapshotGraphMissing` should switch to `SnapshotGraphMissingError`.
  The legacy alias keeps v1.0 callers working through v1.1 but emits
  `DeprecationWarning` at import time. No behavior change; same class.

## [1.0.0] - 2026-06-28

### Changed (BREAKING)
- The JSONL wire format at `~/.flow-engineering/drift_events.jsonl` is now
  `decision_id: int` (was `str` pre-v1.0). This aligns the wire format with
  `decision_drift.Finding.decision_id: int` post-v0.9.0. Operators consuming
  the JSONL with `jq` or custom scripts should review the migration note
  below. The Python `Finding` API is unchanged — this is a wire-format-only
  flip.

### Added
- `flow drift-events {list,tail,stats}` — new read-side CLI command group for
  the JSONL drift event log. Mirrors the `flow metrics {summary,export,
  aggregate}` operator mental model (per `observability` PR#2 subcommand
  precedent). `list` supports `--since` / `--until` / `--change` /
  `--event-class` / `--limit` / `--format=text|json|prometheus|csv` /
  `--path` filters. `tail` defaults to `--limit=10` newest-first and
  supports `--change` / `--event-class` / `--format=text|json` filters.
  `stats` renders per-event-class + per-change + per-decision-id top-N
  counts in an aligned text table (or JSON envelope via `--format=json`).
- `DriftEventLog.read_all()` defensively coerces legacy `str` `decision_id`
  lines from pre-v1.0 JSONL files to `int` with a one-time stderr WARN per
  log-path. Zero data loss; old files remain readable without migration.

### Migration
- Convert existing JSONL files in place (silences the one-time WARN):
  ```bash
  sed -i 's/"decision_id": "\([0-9]*\)"/"decision_id": \1/g' \
    ~/.flow-engineering/drift_events.jsonl
  ```
- Old `decision_id: "42"` (str) JSONL lines continue to read correctly
  without migration thanks to the defensive coercion shim. The `sed` above
  just silences the WARN.

## [0.9.0] - 2026-06-28

### Changed (BREAKING)
- Removed v0.8.0 1-release compat shims (`Finding.from_legacy`,
  `DriftReport.from_legacy`, `classify_binding_legacy`).
- `Finding.__post_init__` now raises `TypeError` on non-`int`
  `decision_id` (no `DeprecationWarning`, no `int()` coercion; `bool`
  is also rejected as an `int` subclass).
- `DriftReport(scanned_at=<float>)` raises `TypeError` (no compat shim
  exists in v0.9.0).
- `classify_binding(ref, graph_nodes, current_id_map)` 3-arg raises
  `TypeError`.

### Removed
- v0.8.0 compat shims — `Finding.from_legacy`, `DriftReport.from_legacy`,
  `classify_binding_legacy`. Removed per the 1-release commitment in
  the v0.8.0 entry.

### Migration
- Replace `Finding(decision_id="42")` with `Finding(decision_id=42)`.
- Replace `DriftReport(scanned_at=0.0)` with
  `DriftReport(scanned_at="1970-01-01T00:00:00Z")`.
- Replace `classify_binding_legacy(binding, nodes, id_map)` with
  `classify_binding(binding, nodes)`.

No automatic migration — v0.9.0 is a hard break.

## [0.8.1] - 2026-06-28

### Added
- REQ-50: `flow prompts list` + `flow prompts show <id>` CLI subcommands (`flow prompts list` returns a text table grouped by domain; `--json` projects each entry into `{prompt_id, domain, version, owner, variables, location}` shape; `flow prompts show <id>` renders the template with sentinel substitution, accepts repeatable `--var key=value` flags, exits 5 on unknown id with a JSON error payload on stderr).

### Fixed
- W1: lint_prompts spec-taxonomy alias map (`LINT_CATEGORY_SPEC_ALIASES` + `get_spec_category()`) so spec-mandated category names (`missing_placeholder`, `template_parse_error`) resolve to the implementation categories (`undefined_var`, `jinja_syntax`).
- W2: `select_autoescape(default_for_string=True)` for `_safe_jinja_env()` — HTML escape blocks Jinja2 `{{ var }}` injection on untrusted input.
- W3: `prompts/` directory + 4 `.j2` files (`strict_tdd.j2` + `auto_suggest_header.j2` + `auto_suggest_footer.j2` + `auto_suggest_empty.j2`) restored at repo root.
- W4: `scaffold._env()` hoisted to shared `prompt_registry._env()` so the scaffold render path and the prompt-render path share the same Jinja2 `Environment` configuration (including autoescape + `StrictUndefined`).
- W7: `[tool.flow_engineering.prompts] directory = "prompts"` section added to `pyproject.toml`.
- W8: `pyproject.toml` version bumped 0.8.0 → 0.8.1 (additive MINOR bump for REQ-50 + 8 W-fix carry-forwards).
- W9: ruff auto-fix run on PR#2b changed files (no auto-fixable issues; the single UP042 finding for `PromptDomain(str, Enum)` requires `--unsafe-fixes` and is left as a follow-up).
- W10: strengthened REQ-45 S1 BDD scenario with per-entry assertions for owner / variables / location (closes the REQ-45 S1 PARTIAL flag from PR#1 verify-report).

## [0.8.0] - 2026-06-27

### Added
- `flow prompt-registry` Python API in `src/flow_engineering/prompt_registry.py` (REQ-45).
- `PromptRegistry` (module-level catalog) + `PromptDef` frozen dataclass + `PromptDomain` enum + `PROMPT_NAMES` catalog with 4 migrated entries (`strict_tdd`, `auto_suggest_header`, `auto_suggest_footer`, `auto_suggest_empty`) (REQ-45).
- `render_prompt(name, **kwargs)` Jinja2-based renderer with `StrictUndefined` + `render_prompt_safe()` sentinel-substitution helper + `list_required_vars(name)` AST introspection helper (REQ-46, D3 + D4).
- `validate_catalog()` + `lint_prompts()` validators with `LintError` + `LintReport` types; detects duplicate names, invalid domains, undefined Jinja2 vars, malformed Jinja2 syntax, invalid SemVer (REQ-47, 5 error codes per D7).
- 7 `SKILL.md` runtime files carry the `## Prompt registry hook` section (sdd-propose, sdd-design, sdd-tasks, sdd-apply, sdd-verify, sdd-archive + future sdd-init / sdd-explore / sdd-spec / sdd-onboard land in PR#2) (added in batch C).
- `openspec/specs/prompt-registry/spec.md` bootstrapped (mirrors change #6 observability pattern; resolves next capability spec pattern per D12).

### Tests
- 1078 / 1078 tests passing (`uv run pytest`; +15 unit tests for `render_prompt`/`render_prompt_safe`/`list_required_vars` + 7 BDD scenarios for req45/46/47).
- 32 BDD scenarios across 18 feature files (+7 this PR).
- See `openspec/changes/archive/2026-06-27-prompt-registry-pr1/` for full spec, design, and task breakdown.

### Notes
- `prompt-registry` change #7 PR#1 (foundation + validation + lint + render) shipped with 3 batches (A + B + C) in ~7 work-unit commits.
- Strict TDD throughout; 4 inline prompt constants migrated to PromptRegistry thin wrappers per D10 alias convention (`STRICT_TDD_PROMPT`, `EMPTY_PROMPT_TEXT`, `PROMPT_HEADER`, `PROMPT_FOOTER`).
- The existing 4 prompt templates use Python `.format()` style (`{test_command}`); `render_prompt()` uses Jinja2 `{{ var }}` syntax (new prompts registered via `register()` exercise the substitution path).
- Verify report: TBD (sdd-verify next).

### Out-of-scope reminders (carried to PR#2)
- REQ-49 OpenCode SKILL.md catalog (`SKILL_CATALOG` + `check_drift` + `init_checksums` / `update_checksums` + sidecar JSON) (PR#2)
- REQ-50 `flow prompts` CLI subcommand (`list` / `show <id>` / `lint` / `check` + 7 flags) (PR#2)
- REQ-48 Golden regression tests (deferred to v1.1)
- REQ-51 `prompt_renders.jsonl` append-only sink (deferred to v1.1)
- REQ-52 Prompt observability counters (deferred to v1.1; will land in `observability.py` per D10)
- REQ-53 `docs/prompts.md` generated from registry (deferred to v1.1)
- REQ-54 `min_sdd_skill_versions` enforcement (deferred to v1.1)
- Per-prompt LLM provider routing (deferred to v1.1)
- Prompt A/B testing infrastructure (deferred to v1.1)

## [0.8.0] - 2026-06-27

### Breaking changes

- `decision_drift.Finding.decision_id` is now `int` (was `str`). v0.7.x callers using `int(finding.decision_id)` should switch to direct access (decision_id IS int now). `Finding.from_legacy()` is the 1-release migration path; emits DeprecationWarning for legacy str usage; removed in v0.9.0. (REQ-56 W8)
- `decision_drift.DriftReport.scanned_at` is now `str` ISO 8601 UTC Z-suffixed (was `float` epoch). v0.7.x callers should use `datetime.fromisoformat()` to parse. `DriftReport.from_legacy()` is the 1-release migration path; emits DeprecationWarning for legacy float usage; removed in v0.9.0. (REQ-56 W8)
- `decision_drift.DriftReport.unable_reason: str | None` added (new field). `graph_unavailable: bool` retained as the canonical field name; `from_legacy()` maps legacy `unable_to_verify: bool` kwarg to `graph_unavailable`. (REQ-56 W8)
- `classify_binding(ref, graph_nodes)` 2-arg signature (was 3-arg `classify_binding(binding, current_nodes, current_id_map)`). `classify_binding_legacy` is the 1-release 3-arg wrapper; emits DeprecationWarning; removed in v0.9.0. (REQ-56 W8)

### Added

- `DriftEventLog` JSONL append-only writer at `~/.flow-engineering/drift_events.jsonl` (REQ-55 W5). Thread-safe via `threading.Lock`.
- Daemon still-valid silence: `flow watch --drift` suppresses summary line when all bindings still-valid (REQ-56 W6).
- 21 BDD scenarios covering REQ-10/12/13/14/16 (REQ-57 W4).
- SnapshotMeta.size_bytes + PruneResult.freed_bytes field reconciliation (REQ-58 W25/W26 — was already correct in impl, spec reconciled).
- `snapshot_pruned_total` legacy counter deprecation note (W23 from change #5).
- stderr WARN log on skipped non-int decision_id in `_write_back_findings` (S2, REQ-59).
- 6 SKILL.md runtime files carry the `## Drift detection hook` section (sdd-propose, sdd-design, sdd-tasks, sdd-apply, sdd-verify, sdd-archive).
- `openspec/specs/decision-drift/spec.md` bootstrapped (mirrors change #6 observability pattern + change #7 prompt-registry pattern).

### Migration guide

From v0.7.x to v0.8.0:
1. Replace `int(finding.decision_id)` with direct `finding.decision_id` access (decision_id IS int now). For legacy str callers, use `Finding.from_legacy(decision_id="42", ...)` which emits DeprecationWarning and coerces.
2. Replace `report.scanned_at` (float) with `datetime.fromisoformat(report.scanned_at)` (str ISO 8601). For legacy float callers, use `DriftReport.from_legacy(scanned_at=1751000000.0, ...)` which emits DeprecationWarning and coerces.
3. Replace `report.unable_to_verify` (bool) with `report.graph_unavailable` (bool) + `report.unable_reason` (str | None). For legacy kwarg callers, use `DriftReport.from_legacy(unable_to_verify=True, ...)` which maps to `graph_unavailable`.
4. Update `classify_binding` 3-arg callers to 2-arg `classify_binding(ref, graph_nodes)` (current_id_map derived internally). For legacy 3-arg callers, use `classify_binding_legacy` which emits DeprecationWarning.

### Tests

- 1115 / 1115 tests passing nominal in the `drift-hardening` cluster (`uv run pytest`); **1120 / 1125 effective** accounting for 5 pre-existing failures inherited from changes #6 PR#2 + #7 PR#1 (unrelated to `drift-hardening`; tracked separately).
- 53 BDD scenarios across 24 feature files (req10/11/12/13/14/16 + req15_drift_daemon extensions + prior scenarios from earlier changes).

### Notes

- `drift-hardening` cluster shipped as single v0.8.0 release. Bundles breaking change (REQ-56 W8 dataclass shape migration) with related cleanup. Migration window: v0.8.0 ships with DeprecationWarning shims; shims removed in v0.9.0.

## [0.7.1] - 2026-06-27

### Added
- `flow metrics export` CLI subcommand with `--format text|json|prometheus`, `--out PATH`, `--window/--since/--until/--domain` flags (REQ-38).
- `flow metrics aggregate` CLI subcommand with `--percentile p50|p95|p99` (repeatable), `--reservoir-size`, `--window/--since/--until/--domain`, `--format text|json` flags (REQ-39).
- `prometheus_exposition()` helper + `PrometheusMetric` dataclass + `write_prometheus_textfile()` atomic writer (REQ-38, D6 monotonic counter semantics + D10 atomic write).
- `aggregate_percentile()` helper + `ReservoirSampler` class (Vitter's Algorithm R) + `format_percentile_report()` text formatter (REQ-39, D7 reservoir sampling).
- `aggregate_many()` multi-percentile helper (W5 carry-forward from PR#1; reconciles design D7 dict[str, float] contract).
- `flow metrics aggregate` exit code 2 on invalid percentile; exit 0 on graceful "not enough data points".
- 6 SKILL.md runtime files carry the `## Export hook` + `## Aggregation hook` sections (added in batch H).

### Modified
- `src/flow_engineering/observability.py` — added prometheus_exposition, aggregate_percentile, ReservoirSampler, format_percentile_report; aggregate() signature drift (W5) reconciled via aggregate_many() back-compat shim.

### Tests
- 953 / 953 tests passing (`uv run pytest`).
- 25 BDD scenarios across 15 feature files (req35 + req36 + req37 + req38 + req39 + req17..req22 + req32 + req33 + req34 — 5 new scenarios this PR).
- See `openspec/changes/archive/2026-06-27-observability-pr2/` for full spec, design, and task breakdown.

### Notes
- `observability` change #6 PR#2 (Prometheus export + percentile aggregation) shipped with 3 batches (F + G + H) in 11 work-unit commits.
- Strict TDD throughout; ×2.9 LOC multiplier realized as planned.
- W5 (aggregate() signature drift) resolved in batch F via aggregate_many() shim.
- Verify report: PASS WITH WARNINGS (6W + 4S); C1 + W1-W6 + S1-S4 resolved; W23/W25/W26 deferred to drift-hardening cluster. See `openspec/changes/observability/verify-report-pr2.md`.

## [0.7.0] - 2026-06-27

### Added
- `flow metrics summary` CLI subcommand with `--format text|json|json-detailed`, `--window 1h|24h|7d|30d|<custom>`, `--since/--until ISO8601`, `--domain <name>` flags (REQ-35, REQ-36, REQ-37).
- 6 pure read functions in `observability.py`: `MetricEvent`, `read_all_metrics`, `read_events_since`, `read_events_by_domain`, `summarize`, `prometheus_exposition`, `aggregate`, `atomic_write_text` (REQ-35..37 foundation).
- `read_and_summarize()` helper + `MetricsSummaryResult` dataclass + 4 exit code constants (EXIT_OK=0, EXIT_INVALID_VALUE=2, EXIT_MALFORMED_METRICS=3, EXIT_WRITE_FAILURE=4).
- `DOMAIN_BY_PREFIX` lookup table expanded from 4 to 8 domains (binding, drift, vector, snapshot, backfill, federated, metadata, engine) — REQ-37 widening.
- `WINDOW_PATTERNS` table + `parse_window()` helper supporting presets (1h/24h/7d/30d) and custom `<int><h|d>` format — REQ-36.
- `openspec/specs/observability/spec.md` bootstrapped (resolves cross-project-federation archive-report #61).
- 6 `SKILL.md` runtime files carry the `## Metrics hook` section (added in batch E).

### Tests
- 868 / 868 tests passing (`uv run pytest`) — was 862 at PR#1 landing, +6 added by the verify sweep (incl. C1 regression gate for production counter names).
- 6 new BDD scenarios (req35 ×2 + req36 ×2 + req37 ×2) for a total of 136 BDD scenarios across 12 feature files.
- See `openspec/changes/archive/2026-06-27-observability-pr1/` for full spec, design, and task breakdown.

### Notes
- `observability` change #6 PR#1 (foundation + summary + window + slice) shipped with 5 batches (A + B + C + D + E) in 24 work-unit commits.
- Strict TDD throughout; 2.9x LOC multiplier realized as planned (read-side helpers are pure functions, lighter than CLI-heavy changes).
- PR#2 (Prometheus export + percentile aggregation) lands in a follow-up commit on the same change.

### Out-of-scope reminders (carried to PR#2)
- REQ-38 Prometheus textfile export (PR#2)
- REQ-39 percentile aggregation (PR#2)
- JSONL rotation policy (REQ-44, deferred to v1.1)
- Federation-aware metrics (REQ-43, deferred to v1.1)
- Grafana dashboard export (deferred to v1.1)
- OpenTelemetry push (deferred to v1.1)

## [0.6.0] - 2026-06-27

### Added
- `SnapshotManager` class in `src/flow_engineering/snapshot_manager.py` with `create()`, `list()`, `show()`, `diff()`, `rollback()`, `prune()` methods (REQ-28, REQ-29, REQ-30, REQ-31, REQ-32, REQ-34).
- `flow snapshot` CLI subcommand group: `create`, `list`, `show`, `diff`, `rollback`, `prune` (REQ-28..34).
- `flow drift <change> --snapshot <snap_id>` flag for pinned-state scans (REQ-33, NON-BREAKING).
- 4 observability counters: `snapshot_create_total`, `snapshot_rollback_total`, `snapshot_prune_total`, `snapshot_load_failed_total` (REQ-26). Wired in `SnapshotManager.create/rollback/prune` and `decision_drift._load_graph_from_snapshot`.
- `record_snapshot_event(counter_name, **labels)` helper in `observability.py` (mirrors `record_vector_summary`, `record_drift_summary`).
- `PruneResult` dataclass + `PruneNoFilterError` + `PruneSafetyGateError` exception classes.
- `SnapshotMeta.pinned` field for retention-pin semantics.
- 6 `SKILL.md` runtime files carry the Graph snapshots hook section.

### Tests
- 799 / 799 tests passing (`uv run pytest`).
- 14 BDD scenarios across 14 feature files (req3 + req9 + req15 + req17..req22 + req32 + req33 + req34) — added `req34_snapshot_prune` (2 scenarios).
- See `openspec/changes/archive/2026-06-27-graph-snapshots/` for full spec, design, and task breakdown.

### Notes
- `graph-snapshots` shipped via a single PR with 17 work-unit commits (8 from batches A + B1 + B2 + 3 from batch C T1.6 + 2 from T1.7 + 2 from T1.8 + 2 docs/housekeeping).
- Strict TDD throughout; 4-6x LOC multiplier realized as planned.
- Verify report: TBD (sdd-verify next).

## [0.5.0] - 2026-06-26

### Added
- `EngramBackend.mem_search_federated(query, projects=None, limit=10, since=None, type_filter=None)` on the `EngramBackend` ABC v1.2 — NON-BREAKING default `NotImplementedError`; the `InMemoryBackend` fixture overrides with `project`/`since`/`type_filter` SQL filters (REQ-23).
- `flow search --federated --projects=<csv> --since=<iso> --type=<csv>` flags on the existing `flow search` subcommand — explicit cross-project search; the existing single-project behavior is preserved when `--federated` is omitted (REQ-25).
- `flow projects alias <old> <new>` subcommand — appends to `~/.config/flow-engineering/project-aliases.json`; aliases are applied transparently to all `project` reads (e.g., `flow-image-generator-v2` queries resolve to `flow-image-generator-main` rows) (REQ-27).
- `flow projects backfill [--dry-run] [--confirm] [--since=<iso>] [--project=<key>]` subcommand — `--dry-run` is the DEFAULT (preview only); `--confirm` is REQUIRED to write; emits a JSON report `{would_change, would_skip, changes: [...]}`; iterates the alias map when neither `--project` nor a config override is set (REQ-24).
- `src/flow_engineering/project_detector.py` with `detect(cwd: Path) -> str | None` and `apply_tag(observation_id, project, *, backend)` — cwd-based detection under `~/dev/proyects/<name>/` or `~/proyects/<name>/`; returns `None` outside projects dir; opt-in via `FLOW_AUTO_PROJECT_TAG=1` env var (REQ-24).
- `src/flow_engineering/project_aliases.py` — versioned JSON schema `{version: 1, aliases: [{old, new, created_at}]}`; loaded on startup; cache-friendly; malformed JSON fails fast on startup with `AliasConfigError` (REQ-27).
- `~/.config/flow-engineering/project-aliases.json` — new runtime config file; created on first `flow projects alias` invocation; does NOT auto-backfill (user runs `flow projects backfill` separately) (REQ-27).
- 3 new observability counters: `federated_search_invoked_total{trigger=cli|programmatic}` (counter), `federated_search_projects_queried{count=N}` (histogram — note: no `_total` suffix per design D4), `federated_search_results_returned_total` (counter). Helper `record_federated_summary(invoked, projects_queried, results_returned, *, trigger="programmatic")` emits all 3 in one call; wired into `InMemoryBackend.mem_search_federated` (REQ-26).
- `record_federated_summary(...)` helper in `observability.py` mirroring the `record_drift_summary` (REQ-9) and `record_vector_summary` (REQ-22) pattern — consistent observability contract across all 3 history features.
- 5 new BDD feature files: `req23_federated_search.feature` (5), `req24_project_detector.feature` (6), `req25_cli_federated.feature` (5), `req26_federated_observability.feature` (4), `req27_project_aliases.feature` (5). Total BDD: 25 new scenarios across 5 files.
- ABC bumped v1.1 → v1.2 — third-party `EngramBackend` subclasses import unchanged; new `mem_search_federated` defaults to `NotImplementedError`.

### Tests
- 699 / 699 tests passing (`uv run pytest -x --tb=short`).
- 25 new BDD scenarios across 5 feature files. Total BDD: 116 scenarios across 23 feature files.
- See `openspec/changes/cross-project-federation/` for full spec, design, and task breakdown (post-archive).

### Notes
- `cross-project-federation` shipped as a SINGLE PR (no chained PRs needed; the change is small enough at ~600 prod LOC + ~1500 test LOC).
- **Important correction surfaced by explore**: the original premise of "7 separate Engram DBs" was wrong — there's ONE shared SQLite at `~/.engram/engram.db` with 158 observations across 9 project keys, FTS5 already indexed by `project`. The "federation" is therefore a logical surface (filtered SQL queries on the shared DB), not physical cross-DB infra.
- Alias resolution is applied in `mem_search_federated` and `flow projects backfill` (both forward and reverse: queries for `old` name resolve to `new`, queries for `new` name also match observations tagged with the `old` name).
- Backfill safety gate is strict: `--dry-run` is default; `--confirm` is mandatory to write; never auto-tag. This is the same safety posture as `flow reindex` (REQ-21) and `flow drift` (REQ-9).

## [0.4.0] - 2026-06-26

### Added
- `flow search --semantic <query>` flag on the existing `flow search` subcommand — explicit semantic search via embeddings (one-shot override; REQ-17).
- `flow search --hybrid --alpha <float> --k <int>` flag pair — hybrid semantic + FTS5 scoring with linear combo `α·cosine + (1−α)·normalize_bm25(fts)` (REQ-18). `α` validated to `[0.0, 1.0]`.
- `flow reindex [--batch-size=100] [--dry-run]` subcommand — sync streaming reindex of the Engram corpus into the sqlite-vec store, idempotent via `INSERT OR REPLACE`, crash-resume via per-batch transactions (REQ-21).
- `HybridBackend` composition wrapper at `src/flow_engineering/hybrid_backend.py` exposing `mem_search_semantic` + `mem_search_hybrid` on top of any `EngramBackend` (NON-BREAKING; ABC v1.1; default `NotImplementedError` preserved).
- `EmbeddingProvider` ABC at `src/flow_engineering/embedding_provider.py` with `MockEmbeddingProvider` (deterministic hash-based 384-dim vectors) and `SentenceTransformersProvider` (real model `sentence-transformers/all-MiniLM-L6-v2`, lazy `torch` import at instance time).
- sqlite-vec storage at `src/flow_engineering/vectors/sqlite_vec_store.py` — `observation_embeddings` audit table (`BLOB(1536)` = 384 × float32) + `vec_observations` `vec0` virtual table for KNN (REQ-20). Persisted at `~/.flow-engineering/vectors.sqlite`.
- `[vectors]` optional extra in `pyproject.toml` (`sqlite-vec>=0.1.0,<0.2`, `sentence-transformers>=2.0`). Default install pulls ZERO heavy deps; the gate fires only when both the extra AND `FLOW_VECTOR_SEARCH=1` are present. (`torch` is installed separately via `pip install --index-url https://download.pytorch.org/whl/cpu torch`.)
- `vector_search_invoked_total{trigger=cli|programmatic}`, `vector_search_results_returned_total`, `vector_search_latency_ms` (histogram with P50/P95/P99), `vector_index_size_observations` (gauge), `reindex_observations_total` (counter), `reindex_duration_seconds` (gauge) — 6 new observability counters persisted alongside the existing `flow metrics` JSONL (REQ-22). All names follow the `subject_event_total` / `subject_latency_ms` convention from REQ-8.
- `record_vector_summary(...)` helper in `observability.py` mirroring `record_drift_summary` — emits the 6 counters in one call; defensive clamping on negative inputs.
- `src/flow_engineering/vectors/` package (`__init__.py` + `sqlite_vec_store.py`) exposing `SqliteVecStore` and `vectors_sqlite_path()` for downstream tests.

### Tests
- 572 / 572 tests passing (`uv run pytest -x --tb=short`).
- 24 new BDD scenarios across 5 feature files: `req17_semantic_search.feature` (5), `req18_hybrid_scoring.feature` (5), `req19_embedding_provider.feature` (4), `req20_sqlite_vec_storage.feature` (5), `req21_reindex.feature` (5). Total BDD: 87 scenarios across 17 feature files.
- See `openspec/changes/vector-semantic-search/` for full spec, design, and task breakdown (post-archive).

### Notes
- `vector-semantic-search` shipped via two chained PRs (#1 core HybridBackend + EmbeddingProvider + sqlite-vec storage + observability counters; #2 CLI surface `--semantic` / `--hybrid` / `--alpha` + `flow reindex` subcommand + BDD req21 + release docs).
- ABC bumped v1.0 → v1.1 — third-party `EngramBackend` subclasses import unchanged; new `mem_search_semantic` + `mem_search_hybrid` methods default to `NotImplementedError`.
- The `[vectors]` extra pins `sqlite-vec<0.2` (avoids int8 KNN API churn in 0.2.x); int8 quantization is deferred to v1.1 per spec out-of-scope.
- Gate order in `flow search --semantic` is extra-first, env-second — so users who haven't installed the extra see the install hint, not the env-var hint.
- `flow reindex --dry-run` short-circuits BEFORE creating `vectors.sqlite`, so the on-disk file is never touched in dry-run mode.
- `flow reindex` re-running on a fully-indexed corpus re-uses the audit rows via `INSERT OR REPLACE` with identical vectors (deterministic mock provider in tests; real `SentenceTransformersProvider` in production); no churn, no duplicates.

## [0.3.0] - 2026-06-26

### Added
- `flow drift <change>` subcommand — scans Engram observations for binding drift and reports one of six classes (`still_valid`, `label_drift`, `stale_location`, `stale_id`, `obsolete`, `contradicted`) per REQ-12. Exits `0` (all `still_valid`), `1` (any drift), `2` (`unable_to_verify`) per REQ-11.
- `flow watch --drift` flag — daemon subscribes to `apply-progress` writes and re-runs `scan_change` on `merged` status, emitting a summary line per detected change (REQ-15, REQ-16).
- 8 new `drift_*_total` observability counters (`drift_still_valid_total`, `drift_label_drift_total`, `drift_stale_location_total`, `drift_stale_id_total`, `drift_obsolete_total`, `drift_contradicted_total`, `drift_unable_to_verify_total`, `drift_invoked_total`) persisted alongside the existing `flow metrics` JSONL.

### Closed (W2/W3 carry-forwards)
- **W2** — REQ-8 counter reconciliation: spec counter names now match the 8 implementation counters shipped in v0.2.0.
- **W3** — REQ-3 empty-block BDD: empty `code_refs` blocks are treated as `unbound` and counted via `unbound_observations_total`.

### Tests
- 385 / 385 tests passing (`uv run pytest -x --tb=short`).
- 63 BDD scenarios across 12 feature files (`req1_format`, `req2_parsing`, `req3_engram_io`, `req3_state`, `req4_backfill`, `req4_drift`, `req5_nonbreaking`, `req6_auto_suggest`, `req7_inspect`, `req8_observability`, `req9_drift_detection`, `req15_drift_daemon`).
- See `openspec/changes/archive/2026-06-26-decision-reality-drift/` for full spec, design, and task breakdown (post-archive).

### Notes
- `decision-reality-drift` shipped via two chained PRs (#1 core detector + counters + W2/W3, #2 verification wiring + `flow watch --drift` + REQ-15/REQ-16).
- `sdd-verify` Step 6 gained a sub-step that surfaces `flow drift <change>` findings before declaring green.

## [0.2.0] - 2026-06-25

### Added
- `code_refs` binding block in Engram observations (`<!-- code_refs -->` marker + JSON).
- `src/flow_engineering/binding.py` — extract / parse / format / split round-trip helpers and `CodeRef` dataclass (REQ-1, REQ-2).
- `src/flow_engineering/graphify_query.py` — CLI wrapper for `graphify query` with sha1+mtime cache (24h TTL) and Jaccard fallback (REQ-6 query layer).
- `scripts/backfill_code_refs.py` — append-only migration script with dry-run / apply / idempotency / pre-image JSONL (REQ-4).
- `src/flow_engineering/auto_suggest_code_refs.py` — save-time auto-suggest with threshold filter and confirmation prompt (REQ-6).
- `flow inspect <change>` — CLI command that renders decision ↔ code bindings as a table with freshness column and per-row parse-error isolation (REQ-7).
- `flow metrics` — observability counters persisted as JSONL in `~/.flow-engineering/metrics.json` (REQ-8).
- `EngramClient.save_phase()` auto-appends an `unbound` `code_refs` block when content lacks a marker (REQ-3).
- 6 `SKILL.md` files (sdd-propose / design / tasks / apply / verify / archive) carry the binding-hook prose so future SDD runs resolve `code_refs` automatically.

### Modified
- `src/flow_engineering/engram_io.py` — `save_phase` validation, `auto_suggest_code_refs` wiring, `load_code_refs` accessor (REQ-3, REQ-5, REQ-6).
- `src/flow_engineering/cli.py` — `--with-suggest` / `--no-suggest` flags on save; new `flow inspect` and `flow metrics` subcommands.
- `src/flow_engineering/orchestrator.py` — minor wiring for the save hook.

### Tests
- 302 / 302 tests passing (`uv run pytest`).
- 45 BDD scenarios across 8 feature files (`req1..req8`).
- See `openspec/changes/archive/2026-06-25-decision-code-linking/` for full spec, design, and task breakdown.

### Notes
- `decision-code-linking` shipped via two chained PRs (#1 core binding + backfill, #2 auto-suggest + surface + observability).
- Verify report: PASS WITH WARNINGS, 0 critical. Three documentation-class warnings carried forward (see sdd/decision-code-linking/verify-report for detail).

## [0.1.0] - prior

Initial baseline. See `FLOW.md` and `README.md` for project context.

[0.2.0]: #020--2026-06-25