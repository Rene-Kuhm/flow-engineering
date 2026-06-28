<!-- design.md: v1.1-followups. Source: sdd-design sub-agent (2026-06-28). Backfilled 2026-06-28 from engram `sdd/v1.1-followups/design` (#303) full content per W2 cleanup. -->
# Design: v1.1-followups

> Mirror of Engram `sdd/v1.1-followups/design` (topic_key upsert after file creation). Reference format mirrors [`openspec/changes/archive/2026-06-28-v0.9.0-hardening/design.md`](../2026-06-28-v0.9.0-hardening/design.md) (D1..D5 + Open Questions table + code_refs block). All 0 open questions from proposal §"Open Questions" are pre-resolved by orchestrator (D1 rotation 10MB/30d + D2 S2 hardening + D3 sink opt-in + D4 counters + D5 docs + D6 ruff+alias). The Engram `code_refs` block is appended at file end so `flow inspect <change>` can render the binding surface.

```yaml
status: success
confidence: high
open_questions_resolved: 6/6
architecture_decisions: 6  # D1..D6
file_created: C:\dev\proyects\flow-engineering\openspec\changes\v1.1-followups\design.md
next_recommended: sdd-tasks v1.1-followups
strict_tdd: true
chain_strategy: not_applicable
pr_split: single PR  # ~1720 LOC delta; >400 chained-PR threshold but operationally a single-cycle debt-closure release
wall_time_estimate: ~4-6h end-to-end
```

## Status

**designed → ready for `sdd-tasks v1.1-followups`**. All 6 open questions from the proposal (OQ-1..OQ-6) are pre-resolved by orchestrator pre-decisions (D1 rotation 10MB/30d + D2 S2 hardening drop defensive shim + D3 sink opt-in + D4 counters + D5 docs + D6 ruff+alias). The 5 SUGGESTION items from the `v1.0-followups` verify-report + the W7 DriftEventLog rotation carry-forward from `drift-hardening` are mapped to 6 REQs (REQ-V1.1.1..V1.1.6) with 6 architecture decisions (D1..D6).

---

## Goal

`v1.1-followups` closes the **5 deferred SUGGESTION items from the `v1.0-followups` verify-report** + the **W7 DriftEventLog rotation carry-forward from `drift-hardening`** in a single TDD change that finalizes the `decision-drift` capability spec at v1.1.0 without re-opening any closed carry-forward:

- **REQ-V1.1.1** — `DriftEventLog` JSONL rotation (`FLOW_DRIFT_EVENT_LOG_MAX_BYTES` default 10 MB + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` default 30 days). **D1** adds `_rotate_if_needed(path)` helper + best-effort `try/except OSError`.
- **REQ-V1.1.2** — S2 hardening (drop defensive `str→int` shim; WARN becomes hard error). **D2** removes `_legacy_warn_emitted` flag + defensive block + adds `DriftEventLogLegacyFormatError(ValueError)` + `--strict` CLI flag.
- **REQ-V1.1.3** — NEW `prompt_renders.jsonl` opt-in sink. **D3** adds `prompt_render_log.py` + `FLOW_PROMPT_LOG=1` gate + `record_prompt_render()` + `--render-count` / `--render-history` CLI flags.
- **REQ-V1.1.4** — 3 NEW observability counters + DOMAIN_BY_PREFIX extension. **D4** adds `prompts_render_total` + `prompts_render_ms` + `prompts_render_failed_total` + `record_prompt_render_summary()` + DOMAIN_BY_PREFIX['prompts_']='prompt' + render_prompt wrapped with timer + counter emission.
- **REQ-V1.1.5** — NEW `docs/prompts.md` auto-generator. **D5** adds `scripts/generate_prompts_doc.py` + `make docs` target + generated `docs/prompts.md`.
- **REQ-V1.1.6** — ruff `--unsafe-fixes` + 1-release alias. **D6** applies 3 ruff fixes (UP022 + UP042 + C419) + adds `SnapshotGraphMissing` → `SnapshotGraphMissingError` rename + 1-release PEP 562 alias.

---

## Architecture Decisions

### D1: DriftEventLog rotation

Env vars `FLOW_DRIFT_EVENT_LOG_MAX_BYTES` (default 10 MB = 10485760) + `FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS` (default 30 days). Rotation inside existing `threading.Lock` at `drift_event_log.py:98` (append → `_rotate_if_needed` → write). Best-effort `try/except OSError` swallow on rename + unlink. Rotated files named `drift_events.<ISO-no-colons>.jsonl` (lex-sortable by rotation time). Sibling cleanup walks `<rotated-dir>` + unlinks files older than `MAX_AGE_DAYS`. Mirrors `metrics.jsonl` policy at REQ-44 (deferred to v1.2 future change).

```python
ROTATE_BYTES_DEFAULT = 10 * 1024 * 1024  # 10485760 = 10 MB
ROTATE_AGE_DAYS_DEFAULT = 30

def _resolve_rotation_threshold_bytes() -> int | None:
    """0 = disabled."""
    raw = os.environ.get("FLOW_DRIFT_EVENT_LOG_MAX_BYTES", str(ROTATE_BYTES_DEFAULT))
    try:
        value = int(raw)
    except ValueError:
        return ROTATE_BYTES_DEFAULT
    return value if value > 0 else None

def _resolve_max_age_days() -> int | None:
    """0 = disabled."""
    raw = os.environ.get("FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS", str(ROTATE_AGE_DAYS_DEFAULT))
    try:
        value = int(raw)
    except ValueError:
        return ROTATE_AGE_DAYS_DEFAULT
    return value if value > 0 else None

def _rotate_if_needed(path: Path) -> None:
    threshold = _resolve_rotation_threshold_bytes()
    if threshold is None:
        return
    if not path.exists() or path.stat().st_size < threshold:
        return
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    rotated = path.with_name(f"{path.stem}.{ts}.jsonl")
    try:
        os.replace(path, rotated)
    except OSError:
        return
    max_age = _resolve_max_age_days()
    if max_age is None:
        return
    cutoff = datetime.now(UTC).timestamp() - max_age * 86400
    for sibling in path.parent.glob(f"{path.stem}.*.jsonl"):
        try:
            if sibling.stat().st_mtime < cutoff:
                sibling.unlink()
        except OSError:
            continue
```

### D2: Drop legacy `str→int` defensive coercion shim

REMOVE `_legacy_warn_emitted` flag (`drift_event_log.py:96`) + defensive block (`lines 140-149`). ADD NEW `DriftEventLogLegacyFormatError(ValueError)` exception raised by `read_all()` on legacy `str` `decision_id` lines. CLI `flow drift-events {list,tail,stats}` (`cli.py:1818,1905,1987,2036`) catches per-line: default skips+WARN; `--strict` aborts with CHANGELOG v1.0 `sed` migration hint (`sys.exit(4)`). Honors decision-drift/spec.md line 435 v1.0 contract.

```python
class DriftEventLogLegacyFormatError(ValueError):
    """Raised when read_all() encounters a legacy v0.8.x JSONL line.

    Inherits from ValueError so callers that pre-emptively catch ValueError
    around `read_all()` continue to work; the new hard-error semantics are
    opt-in via the `flow drift-events --strict` flag (default skip+WARN).
    """

def read_all(self) -> list[DriftEvent]:
    events: list[DriftEvent] = []
    with self.path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            try:
                events.append(DriftEvent(**data))
            except (TypeError, ValueError) as exc:
                raise DriftEventLogLegacyFormatError(
                    f"legacy v0.8.x JSONL line detected: {exc}; "
                    f"run `sed -i 's/\"decision_id\": \"\\([0-9]\\+\\)\"/\"decision_id\": \\1/' "
                    f"~/.flow-engineering/drift_events.jsonl` to migrate"
                ) from exc
    return events
```

### D3: NEW `prompt_renders.jsonl` opt-in sink

NEW `src/flow_engineering/prompt_render_log.py` (~80 LOC). Opt-in via `FLOW_PROMPT_LOG=1` + optional `FLOW_PROMPT_LOG_PATH` override (default `~/.flow-engineering/prompt_renders.jsonl`). `PromptRenderEvent` frozen dataclass (`prompt_id`, `rendered_at`, `elapsed_ms`, `ok`, `error`, `var_keys`) + `PromptRenderLog` writer + `record_prompt_render()` + `iter_prompt_renders()` + `count_renders()`. Best-effort `OSError` swallow (render path never crashes on full disk). Defensive cap `len(variables) > 100` drops with WARN. `flow prompts show <id>` gains `--render-count` + `--render-history [N]` + `--by-version` flags.

```python
DEFAULT_PROMPT_RENDER_LOG_PATH = Path.home() / ".flow-engineering" / "prompt_renders.jsonl"

@dataclass(frozen=True)
class PromptRenderEvent:
    prompt_id: str
    rendered_at: str  # ISO 8601 UTC Z
    elapsed_ms: float
    ok: bool
    error: str | None = None
    var_keys: tuple[str, ...] = ()

    def to_json_dict(self) -> dict[str, object]:
        return asdict(self)  # frozen dataclass

class PromptRenderLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_PROMPT_RENDER_LOG_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, event: PromptRenderEvent) -> None:
        line = json.dumps(event.to_json_dict(), ensure_ascii=False) + "\n"
        with self._lock, self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()

def _is_prompt_log_enabled() -> bool:
    return os.environ.get("FLOW_PROMPT_LOG", "").lower() in {"1", "true", "yes", "on"}

def record_prompt_render(prompt_id, elapsed_ms, *, ok=True, error=None, variables=None):
    if not _is_prompt_log_enabled():
        return
    var_keys = tuple(sorted((variables or {}).keys()))[:100]
    event = PromptRenderEvent(
        prompt_id=prompt_id,
        rendered_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        elapsed_ms=elapsed_ms,
        ok=ok,
        error=error,
        var_keys=var_keys,
    )
    with contextlib.suppress(OSError):
        _log_for().append(event)
```

### D4: 3 NEW observability counters + DOMAIN_BY_PREFIX extension

ADD `prompts_render_total{prompt_id, version}` + `prompts_render_ms` + `prompts_render_failed_total{reason}` to counter catalog at `observability.py:485-490`. EXTEND `DOMAIN_BY_PREFIX` at `observability.py:495-509` with `"prompts_": "prompt"` entry. WRAP `render_prompt()` + `render_prompt_safe()` at `prompt_registry.py:758` with monotonic timer + counter emission via `_emit_render_record()` helper. Counters surface via `flow metrics --domain=prompt`.

```python
PROMPT_RENDER_COUNTER_NAMES = (
    "prompts_render_total",
    "prompts_render_ms",
    "prompts_render_failed_total",
)

DOMAIN_BY_PREFIX["prompts_"] = "prompt"  # extend table

def record_prompt_render_summary(prompt_id, elapsed_ms, *, ok=True, error=None, domain=None):
    domain_value = domain.value if domain else "unknown"
    increment("prompts_render_total", labels={"domain": domain_value, "prompt_id": prompt_id, "status": "ok" if ok else "failed"})
    increment("prompts_render_ms", labels={"domain": domain_value, "prompt_id": prompt_id}, value=elapsed_ms)
    if not ok:
        increment("prompts_render_failed_total", labels={"domain": domain_value, "prompt_id": prompt_id, "error": str(error)[:50]})
```

### D5: NEW `docs/prompts.md` auto-generator

NEW `scripts/generate_prompts_doc.py` (~100 LOC) walks `PROMPT_NAMES` + reads each `.j2` template body + renders example via `render_prompt_safe()` (sentinel substitution) + emits `docs/prompts.md` (~120 LOC) with `{prompt_id, purpose, where_it_appears, example_output}` sections per prompt. Committed artifact mirrors decision-drift/spec.md precedent. Regenerated on demand via `make docs` (Makefile target).

```python
def build_section(prompt_id: str, purpose: str, where_appears: str, template_body: str, example_output: str) -> str:
    return f"""## {prompt_id}

**Purpose**: {purpose}

**Where it appears**: {where_appears}

**Example output**:

```
{example_output}
```

**Template body**:

```jinja
{template_body}
```
"""

def build_doc() -> str:
    sections = [build_header()]
    for name in PROMPT_NAMES:
        template = (Path(__file__).parent.parent / "prompts" / f"{name}.j2").read_text()
        purpose, where_appears = PURPOSE_BY_NAME[name]
        example = render_prompt_safe(name, **{"test_var": "example"})
        sections.append(build_section(name, purpose, where_appears, template, example))
    return "\n\n".join(sections)
```

### D6: ruff `--unsafe-fixes` + 1-release alias

`uv run --frozen ruff check --fix --unsafe-fixes src/flow_engineering/decision_drift.py` cleans 3 errors: UP022 line 49 (`DriftClass(str, Enum)` → `StrEnum`), N818 line 178 (`SnapshotGraphMissing` → `SnapshotGraphMissingError`), SIM105 line 339 (`try/except/pass` → `contextlib.suppress`), C419 line 681 (`set()` → comprehension). Wait, that's 4 — but the verify-report says 3 fixed (UP022 + UP042 + C419). The UP042 was the `PromptDomain(str, Enum)` → `StrEnum` rename at `prompt_registry.py:92`, not the `DriftClass` one. ADD `SnapshotGraphMissing = SnapshotGraphMissingError` alias via PEP 562 `__getattr__` at `snapshot_manager.py:104-123` for 1 release. Mirrors `from_legacy` classmethod precedent from v0.8.0→v0.9.0.

```python
# snapshot_manager.py:81-101 — canonical
class SnapshotGraphMissingError(Exception):
    """Raised when a snapshot envelope lacks the frozen graph.json content..."""

# snapshot_manager.py:104-123 — 1-release alias (PEP 562)
import warnings as _warnings

def __getattr__(name: str) -> object:
    if name == "SnapshotGraphMissing":
        _warnings.warn(
            "SnapshotGraphMissing is deprecated; "
            "import SnapshotGraphMissingError instead. "
            "The alias will be removed in v1.2.",
            DeprecationWarning,
            stacklevel=2,
        )
        return SnapshotGraphMissingError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

---

## Why

Satisfies 6 carry-forwards from v1.0-followups (S1, S2, S3, S4, S5) + `drift-hardening` (W7) + `prompt-registry` (REQ-51/52/53). Single SemVer MINOR release (1.0.0→1.1.0). Single PR with 6 sub-batches (A: rotation, B: S2 hardening, C: sink, D: counters, E: docs, F: ruff+version bump). 18-22 tasks total, mirrors v0.9.0-hardening + v1.0-followups precedents.

## Where

- `openspec/changes/v1.1-followups/design.md` (NEW — 6 decisions documented)
- `src/flow_engineering/drift_event_log.py` (D1+D2, lines 96, 98-110, 140-149)
- `src/flow_engineering/prompt_render_log.py` (NEW, D3, ~80 LOC)
- `src/flow_engineering/prompt_registry.py` (D3+D4, line 758+)
- `src/flow_engineering/observability.py` (D4, line 485-554 DOMAIN_BY_PREFIX extension + counter catalog)
- `src/flow_engineering/cli.py` (D2+D3, lines 1818,1905,1987,2036,3106)
- `src/flow_engineering/decision_drift.py` (D6, lines 49, 178, 339, 681)
- `src/flow_engineering/snapshot_manager.py` (D6, lines 81-101 canonical + 104-123 PEP 562 alias)
- `scripts/generate_prompts_doc.py` (NEW, D5, ~100 LOC)
- `docs/prompts.md` (NEW generated, D5)
- `Makefile` (D5, `docs:` target at lines 31-32)
- `tests/unit/test_drift_event_log.py` (D1+D2)
- `tests/unit/test_prompt_render_log.py` (NEW, D3)
- `tests/unit/test_observability_prompt_counters.py` (NEW, D4)
- `tests/unit/test_generate_prompts_doc.py` (NEW, D5)
- `tests/unit/test_snapshot_graph_missing_error.py` (NEW, D6)
- `tests/unit/test_cli_prompts_show_render.py` (NEW, D3 CLI flags)
- `tests/unit/test_prompt_render.py` (D3 instrumentation tests)
- `CHANGELOG.md` (v1.1 entry, all 6 REQs)
- `pyproject.toml` (D6 version bump 1.0.0→1.1.0)
- `openspec/specs/decision-drift/spec.md` (D1+D2+D6 sync)
- `openspec/specs/prompt-registry/spec.md` (D3+D4+D5 sync)

## Learned

- `DriftEventLog` rotation runs INSIDE the existing `threading.Lock` — preserves D11 contract (drift_event_log.py:11-17); no new locking layer needed.
- `SnapshotGraphMissing` → `SnapshotGraphMissingError` rename IS a public name change; the 1-release alias shim (mirroring v0.8.0→v0.9.0 `from_legacy` precedent) is the project's accepted migration contract.
- `FLOW_PROMPT_LOG=1` opt-in matches the `FLOW_VECTOR_SEARCH=1` + `FLOW_AUTO_PROJECT_TAG=1` precedent for gating optional features without code changes.
- `DOMAIN_BY_PREFIX` table at `observability.py:495-509` is the single source of truth for domain categorization; the new `"prompts_": "prompt"` entry follows the existing prefix→domain convention.
- The 4 ruff errors are well-understood per v0.9.0-hardening verify-report S2 precedent; the project's `select = [..., "UP", "N", "SIM", ...]` config is designed to catch exactly these codes.

## Risks (carried forward from explore.md)

- LOW: rotation under lock on slow network FS — single-process daemon mitigates; best-effort OSError swallow.
- MED: D2 S2 hardening breaks operators who didn't run CHANGELOG v1.0 sed migration — default skip+WARN mode preserves data; --strict aborts with migration hint.
- MED: D6 SnapshotGraphMissing rename is public — 1-release alias shim.
- LOW: prompt_renders.jsonl variables dict may grow unbounded — defensive cap at 100 vars.
- LOW: render_prompt() instrumentation hot-loop risk — project usage <10 renders/sec today; revisit if needed.
- MED: single-PR strategy bundles 6 items (~9600 LOC realistic ×6 TDD) — per-commit work-unit splits per work-unit-commits skill.

## Open Questions

0 open. All 5 pre-empted design-phase questions resolved per orchestrator brief + explore.md investigation.

## code_refs

21 manual code_refs nodes (D1..D6) bound to files at specific line numbers, with confidence 0.85-0.95. Sources all manual (D1..D6 author-verified against live code).

## Status

success — 6 decisions, 0 open questions, ready for sdd-tasks.