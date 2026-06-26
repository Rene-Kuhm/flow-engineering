# Design: decision-code-linking

## Technical Approach

Lock in Approach D from the proposal (`sdd/decision-code-linking/proposal` in Engram). Pointer block lives at the end of `content`, parseable by `binding.py`; `graphify_query.py` is the only outbound LLM-touching surface. `engram_io.py:save_observation()` becomes the single integration point — every other module calls it. Two chained PRs, both under the 400-line review budget.

## Architecture Decisions

| # | Decision | Option | Tradeoff | Choice |
|---|---|---|---|---|
| 1 | Block delimiter | `<!-- code_refs -->` marker vs trailing-JSON-heuristic | Marker survives future FTS5 filters; heuristic breaks on JSON inside prose | **Marker** |
| 2 | Node payload | Bare ID vs `{project,id,label,file,line,confidence,source}` | Bare ID is smaller; object survives `graph.json` rebuild | **Object** |
| 3 | `source` enum | `manual` / `auto_suggest` / `backfill` / `unbound` | Drift detector must weight differently | **4-value enum** |
| 4 | Confidence default | `manual=0.9`, `auto_suggest=score`, `backfill=0.3`, `unbound=0.0` | Lets `decision-reality-drift` weight without parsing history | **Fixed map** |
| 5 | Cache backend | In-process dict vs `~/.flow-engineering/cache.json` | Dict dies with process; file survives across sessions, ~5KB | **JSON file, 24h TTL by sha1(content+graph.json mtime)** |
| 6 | Suggest threshold | Hardcoded 0.3 vs per-call kwarg | Per-call lets noisy short decisions opt out | **Kwarg default 0.3** |
| 7 | Fail-open on graphify | Refuse save vs skip-and-mark | Refusing breaks the SDD loop on every graphify outage | **Skip-and-mark** |
| 8 | Metrics sink | `prometheus_client` (new dep) vs `~/.flow-engineering/metrics.json` (append-only JSONL) | Prometheus is heavier; metrics are local-debug-only here | **JSONL file** |
| 9 | Backfill atomicity | Per-observation transaction vs batched `UPDATE` with rollback snapshot | Per-obs is 46 round trips; batched is one shot with safe rollback via pre-image file | **Batched + pre-image** |
| 10 | `flow inspect` data source | Re-read `state.json`+`tasks.md` vs query Engram for `code_refs` | Engram is canonical; state.json is per-machine | **Engram via existing `EngramClient.load_phase()`** |

## Module Breakdown (file-level diff plan)

### PR#1 — Core pointer binding (target ≤330 LOC)

| File | Action | LOC | Purpose |
|---|---|---|---|
| `src/flow_engineering/binding.py` | CREATE | ~90 | `extract_code_refs`, `parse_code_refs`, `format_code_refs_block`, `split_prose_and_refs` |
| `src/flow_engineering/graphify_query.py` | CREATE | ~80 | `query_nodes(text, threshold, max_results, cache_dir)` — BFS via `graphify query` CLI + Jaccard fallback when binary absent |
| `src/flow_engineering/engram_io.py` | MODIFY | +30 | `EngramClient.save_phase()` appends `code_refs` block when missing; new `load_code_refs(change, phase)` accessor |
| `scripts/backfill_code_refs.py` | CREATE | ~50 | CLI: `--dry-run` (default), `--apply`, `--project insyd`. Writes pre-image to `~/.flow-engineering/backfill-preimage.jsonl` |
| `tests/unit/test_binding.py` | CREATE | ~60 | ≥10 golden fixtures: empty / single / multi / backfill / manual / auto_suggest / unbound / malformed / round-trip |
| `tests/unit/test_engram_io_code_refs.py` | CREATE | ~40 | `save_phase` injects block; `load_code_refs` parses; pre-existing observations (no block) still load |
| `tests/unit/test_backfill.py` | CREATE | ~30 | Dry-run reports counts; apply is idempotent (`source: backfill` ⇒ skip); pre-image written |
| `tests/bdd/decision_code_linking_p1.feature` | CREATE | ~30 | 3 scenarios: extract-empty / extract-with-block / backfill-idempotent |
| `tests/bdd/test_decision_code_linking_p1_steps.py` | CREATE | ~30 | pytest-bdd glue |

### PR#2 — Auto-suggest + surface (target ≤290 LOC)

| File | Action | LOC | Purpose |
|---|---|---|---|
| `src/flow_engineering/engram_io.py` | MODIFY | +60 | `auto_suggest_code_refs(text, threshold, max_results)`; writer-confirmation step via stdin + `--non-interactive` flag |
| `src/flow_engineering/cli.py` | MODIFY | +60 | New `flow inspect <change>` command: reads all phase observations, renders table with `id, label, file:line, confidence, source, last_resolved_at` |
| `src/flow_engineering/metrics.py` | CREATE | ~30 | `record(event, **fields)` appends JSONL to `~/.flow-engineering/metrics.json`; reads back as dict-of-lists |
| `.config/opencode/skills/sdd-{propose,design,tasks,apply,verify,archive}/SKILL.md` | MODIFY | +50 prose | Step 5 gains a "Resolve code_refs" sub-step (no logic, just text — agents read it) |
| `tests/unit/test_auto_suggest.py` | CREATE | ~40 | Mock graphify CLI; threshold filtering; cache hit/miss; fail-open on missing graph.json |
| `tests/unit/test_metrics.py` | CREATE | ~20 | Counter increments, JSONL rotation at 1MB |
| `tests/unit/test_cli_inspect.py` | CREATE | ~30 | Table render includes freshness column (mtime of `graphify-out/graph.json`); empty change ⇒ exit 0 + helpful msg |
| `tests/bdd/decision_code_linking_p2.feature` | CREATE | ~30 | 4 scenarios: auto-suggest-threshold / unbound-when-graph-missing / inspect-shows-table / metrics-counter-increments |

**Total**: 6 new files, 4 modified, 6 SKILL.md touched. **620 LOC** (matches proposal estimate).

## Data Flow

### Save-time (PR#1 + PR#2)

```
writer (agent or human)
    │
    │  mem_save(title, content, topic_key, type)
    ▼
EngramClient.save_phase()
    │
    ├─→ binding.extract_code_refs(content)
    │       └─ if present & non-empty ──► keep, save as-is  (manual wins)
    │
    ├─→ if empty:
    │       ├─→ auto_suggest_code_refs(text)               [PR#2]
    │       │     ├─→ graphify_query.query_nodes(text)
    │       │     │     ├─→ graphify query <text>          [CLI, ~2-5s]
    │       │     │     ├─→ cache hit? sha1(text+mtime)    [24h TTL]
    │       │     │     └─→ fallback: Jaccard on graph.json nodes
    │       │     └─→ filter >= threshold (default 0.3)
    │       ├─→ confirmation prompt  (skip if --non-interactive)
    │       └─→ format_code_refs_block(nodes, source=auto_suggest|unbound)
    │
    └─→ backend.mem_save(content + block)
            └─→ metrics.record("save", source=...)
```

### Backfill (PR#1)

```
scripts/backfill_code_refs.py --apply --project insyd
    │
    ├─→ EngramClient(topic_key=None)  # scan all observations
    ├─→ for each obs missing code_refs block:
    │     ├─→ extract prose (split_prose_and_refs)
    │     ├─→ auto_suggest on prose title + first 500 chars
    │     ├─→ format with source=backfill, confidence=0.3
    │     └─→ write to preimage.jsonl + engram.mem_update(obs.id, new_content)
    └─→ on interrupt: re-running with --apply picks up where it left
                      (skips obs that already have source=backfill)
```

### `flow inspect <change>` (PR#2)

```
flow inspect decision-code-linking
    │
    ├─→ EngramClient(change).search_cross_session(change)
    ├─→ for each obs:
    │     ├─→ binding.parse_code_refs(obs.content)
    │     ├─→ graph.json mtime → "freshness" column ("fresh"|"stale N days")
    │     └─→ render row
    └─→ click.echo(table)
```

## Interfaces / Contracts

```python
# binding.py
@dataclass(frozen=True)
class CodeRef:
    project: str
    id: str
    label: str
    file: str
    line: int
    confidence: float  # 0.0-1.0
    source: Literal["manual","auto_suggest","backfill","unbound"]

def extract_code_refs(content: str) -> list[CodeRef]: ...
def parse_code_refs(content: str) -> list[CodeRef]: ...        # alias; raises on malformed
def format_code_refs_block(refs: list[CodeRef], schema: int = 1) -> str: ...
def split_prose_and_refs(content: str) -> tuple[str, str]: ...  # (prose, block_or_empty)

# graphify_query.py
def query_nodes(text: str, *, threshold: float = 0.3,
                max_results: int = 5, cache_dir: Path = DEFAULT_CACHE) -> list[CodeRef]: ...
def jaccard_fallback(text: str, graph_json: Path, top_k: int) -> list[CodeRef]: ...

# engram_io.py (additions)
def auto_suggest_code_refs(self, text: str, *,
                           threshold: float = 0.3,
                           non_interactive: bool = False) -> list[CodeRef]: ...
def load_code_refs(self, phase: str) -> list[CodeRef]: ...

# metrics.py
def record(event: str, **fields: Any) -> None: ...
def read_all() -> dict[str, list[dict]]: ...
```

JSON shape (canonical):

```json
<!-- code_refs -->
{"schema": 1, "nodes": [
  {"project":"insyd","id":"src_auth_jwt_jwttokenmanager",
   "label":"JWTTokenManager","file":"src/auth/jwt.py","line":42,
   "confidence":0.9,"source":"manual"}
]}
```

## Cross-Cutting Concerns (resolved)

| Concern | Resolution |
|---|---|
| **Backfill atomicity** | Batched + pre-image. Single `engram.mem_update` per missing obs (no transactions needed — observations are independent). Pre-image JSONL enables `git`-style recovery. Dry-run by default; `--apply` required. |
| **Cache invalidation** | Key = `sha1(text + str(graph_json.stat().st_mtime))`. Stale `graph.json` mtime ⇒ fresh query. TTL 24h as safety net. Cache file at `~/.flow-engineering/graphify_cache.json`, ~5KB cap, LRU-trimmed. |
| **Threshold 0.3 vs noise** | 0.3 surfaces ≥1 candidate for ≥80% of decisions >50 chars (per proposal success criteria #5). Drift detector down-weights `backfill` (0.3) and `unbound` (0.0). Tunable per-call. |
| **Fail-open** | `graphify_query` returns `[]` on missing binary / missing `graph.json` / non-zero exit / timeout (5s). Caller formats `source: unbound`. **Never raises from save path.** |
| **In-flight migration** | None required — block is append-only. Observations saved between PR#1 deploy and PR#2 deploy get `source: unbound` initially; PR#2 reruns auto-suggest on next access. |
| **`flow inspect` API** | Uses existing `EngramClient.search_cross_session()` + new `load_code_refs()` accessor. No new Engram API surface. Freshness column = `graphify-out/graph.json` mtime vs obs `updated_at`. |
| **SKILL.md coupling** | 6 files (propose, design, tasks, apply, verify, archive) get identical "Step 5: Resolve code_refs" prose block. No new logic in the skills — they instruct agents to call helpers that already exist. |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `binding.py` parse/format/round-trip | Table-driven, ≥10 golden fixtures (empty/single/multi/backfill/manual/auto_suggest/unbound/malformed/round-trip/version-bump) |
| Unit | `graphify_query.py` | Mock `subprocess.run` for `graphify query`; Jaccard fallback against fixture `graph.json` (5-node mini); cache hit/miss; fail-open on each error path |
| Unit | `engram_io.save_phase` integration | Use `InMemoryBackend`; verify block appended, pre-existing block preserved, round-trip via `load_code_refs` |
| Unit | `backfill_code_refs.py` | `InMemoryBackend` with 5 seeded observations (3 missing block, 2 with manual block); assert dry-run is no-op, `--apply` mutates only the 3, re-run is idempotent, pre-image file written |
| Unit | `metrics.py` | Temp dir; append/read; rotation at 1MB stubbed via monkeypatch |
| Unit | `cli.py inspect` | Click `CliRunner`; seeded observations; assert table rows, freshness column values, empty change ⇒ graceful exit |
| BDD | PR#1 feature: `decision_code_linking_p1.feature` | 3 scenarios — extract-empty, extract-with-block, backfill-idempotent. Steps in `test_decision_code_linking_p1_steps.py` |
| BDD | PR#2 feature: `decision_code_linking_p2.feature` | 4 scenarios — auto-suggest-threshold-filters, unbound-when-graph-missing, inspect-renders-table, metrics-counter-increments |
| E2E (manual, not in CI) | Real graphify on `c:\dev\proyects\` | Run via `--non-interactive`; eyeball table; revoke network to confirm fail-open |

**TDD order per file** (Strict TDD ON):

1. `binding.py` — red fixtures (golden JSON) → green impl → refactor dataclass
2. `graphify_query.py` — red (mock subprocess) → green → refactor cache
3. `engram_io.save_phase` hook — red (assert block appended) → green → refactor
4. `backfill_code_refs.py` — red (seeded obs) → green → refactor pre-image
5. PR#1 BDD scenarios bind the unit tests via Given/When/Then
6. PR#2: same order, `auto_suggest` → `cli inspect` → `metrics` → BDD
7. SKILL.md updates land last in each PR (prose only, validated by re-reading)

Coverage target: ≥90% lines on new modules (ruff + pytest-cov already configured).

## Migration / Rollout

**No data migration.** Backfill is opt-in (`scripts/backfill_code_refs.py --apply`). Rollout order:
1. PR#1 merged → saves gain block (mostly `source: unbound` until graphify runs)
2. Operator runs backfill script once (`--apply --project insyd`)
3. PR#2 merged → auto-suggest active for new saves; `flow inspect` surfaces the table
4. Existing observations benefit retroactively without rewrite

Rollback per-PR per proposal.

## Open Questions

**None.** All 7 explore questions resolved by proposal; design phase adds no new forks.