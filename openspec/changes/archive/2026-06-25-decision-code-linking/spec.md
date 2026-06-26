# Spec: decision-code-linking

**Change:** `decision-code-linking`
**Builds on:** `proposal.md` (Approach D — pointer + auto-suggest, 2 chained PRs)
**Date:** 2026-06-25
**Status:** SPECIFIED → ready for sdd-design / sdd-tasks

> **Reconciliation note (post-archive, 2026-06-25):** REQ-8 counter names
> below were reconciled with the implementation per `sdd/decision-code-linking/verify-report`
> finding **W2**, and carried forward by the `decision-reality-drift` change
> (PR#1 batch A, T1.1). The original (pre-reconciliation) names were:
> `manual_count`, `auto_suggest_hits`, `backfill_count`, `unbound_count`,
> `avg_bindings_per_observation`, `backfill_coverage`. They were replaced by
> the actual names emitted by `src/flow_engineering/observability.py`
> (REQ-6 events + REQ-8 close in PR#2 batch 2). The `avg_bindings_per_observation`
> derived metric was dropped: coverage is now computed by the
> `record_backfill_coverage(observations_total=…, with_refs=…)` helper which
> increments `backfill_observations_total` and `backfill_with_refs_total`,
> and the ratio is exposed by `backfill_coverage(backend)`.

## Goal

Bind Engram observations to Graphify code nodes via a structured `code_refs` block appended to observation content. PR#1 ships the binding format, parser, save hook, and one-time backfill. PR#2 layers in auto-suggestion at save time, the `flow inspect` rendering, and observability counters. The contract MUST be non-breaking: existing observations, older engram binaries, and the FTS5 index MUST keep working without migration.

---

## PR#1 — Core pointer binding

### REQ-1: `code_refs` block format

The system SHALL recognize a trailing structured block in observation content, gated by an HTML comment marker `<!-- code_refs -->` followed by a JSON object. The block MUST be the **last** non-whitespace content of `content`. The JSON object MUST have a top-level `schema` integer (current value `1`) and a `nodes` array. Each element of `nodes` MUST be an object with keys `project`, `id`, `label`, `file`, `line`, `confidence`, `source`. The parser MUST treat the block as opaque prose when the marker is absent or the trailing JSON fails to parse, and MUST raise a structured error when the marker is present but the block is malformed.

#### Scenario: Marker present with valid JSON block parses cleanly

- GIVEN an observation content ending with `<!-- code_refs -->\n{"schema": 1, "nodes": []}\n`
- WHEN the parser extracts the block
- THEN it returns the parsed `nodes` array and the trailing block is removed from the prose view
- AND the original content is reconstructible by re-appending the formatted block

#### Scenario: Marker absent — content stays pure prose

- GIVEN an observation content with no `<!-- code_refs -->` marker
- WHEN the parser extracts the block
- THEN it returns an empty `nodes` array
- AND the original content is returned byte-for-byte

#### Scenario: Empty `nodes` array is a valid unbound block

- GIVEN content ending with `<!-- code_refs -->\n{"schema": 1, "nodes": [], "source": "unbound"}\n`
- WHEN the parser extracts the block
- THEN it returns an empty list with `source: unbound`

#### Scenario: Malformed JSON after marker raises a parse error

- GIVEN content ending with `<!-- code_refs -->\n{this is not json}\n`
- WHEN the parser extracts the block
- THEN it raises a structured error indicating the marker was found but the body is not valid JSON
- AND the error includes the line offset of the malformed body

---

### REQ-2: `binding.extract()` and `binding.format()` round-trip

The system SHALL provide `binding.extract(content)` returning `list[CodeRef]` where each `CodeRef` has fields `project`, `id`, `label`, `file`, `line`, `confidence`, `source`, plus `binding.format(refs, source)` producing a canonical block string. The system SHALL guarantee `extract(format(extract(content))) == extract(content)` for any well-formed input.

#### Scenario: `extract` returns one `CodeRef` per node preserving field order

- GIVEN a content block containing three binding objects in the order `[A, B, C]`
- WHEN `binding.extract(content)` runs
- THEN it returns `[A, B, C]` with `project`, `id`, `label`, `file`, `line`, `confidence`, `source` populated for each
- AND the order is preserved

#### Scenario: `format` produces canonical block string with marker

- GIVEN a list of two `CodeRef` objects with `source: manual`
- WHEN `binding.format(refs, source="manual")` runs
- THEN it returns a string starting with `<!-- code_refs -->` on its own line
- AND the JSON body is sorted by `id` within the `nodes` array
- AND `schema: 1` is present at the top level
- AND the trailing newline is included

#### Scenario: `extract ∘ format ∘ extract` is idempotent

- GIVEN any content with a well-formed `code_refs` block
- WHEN `binding.extract(content)` then `binding.format(refs, source)` then `binding.extract(formatted)` runs sequentially
- THEN the second `extract` returns the same list as the first

#### Scenario: `format` rejects an unknown `source` value

- GIVEN a list of `CodeRef` objects where `source` is `"made_up"`
- WHEN `binding.format(refs, source="made_up")` runs
- THEN it raises a validation error listing the allowed values (`manual`, `auto_suggest`, `backfill`, `unbound`)

---

### REQ-3: `engram_io.save_observation()` honors the marker

The system SHALL write observation content unchanged when no marker is present. When the marker IS present, the system SHALL validate the block structure before writing; malformed blocks MUST be rejected with no partial write.

#### Scenario: Save without marker writes through unchanged

- GIVEN observation content with no `<!-- code_refs -->` marker
- WHEN `engram_io.save_observation(...)` is called
- THEN the content is written to the database byte-for-byte
- AND no validation error is raised

#### Scenario: Save with valid block writes the content with block intact

- GIVEN observation content ending with a well-formed `code_refs` block
- WHEN `engram_io.save_observation(...)` is called
- THEN the content is written to the database with the block preserved
- AND `binding.extract(saved_content)` returns the same list that was provided

#### Scenario: Save with malformed block is rejected before write

- GIVEN observation content ending with `<!-- code_refs -->\n{not json}\n`
- WHEN `engram_io.save_observation(...)` is called
- THEN the save is rejected with a parse error naming the offset
- AND no row is written to `observations`
- AND no row is written to `memory_relations`

#### Scenario: Save with unknown schema version is rejected

- GIVEN observation content ending with `<!-- code_refs -->\n{"schema": 99, "nodes": []}\n`
- WHEN `engram_io.save_observation(...)` is called
- THEN the save is rejected with a schema-version error stating `schema: 99` is not supported
- AND no row is written

#### Scenario: Save with valid empty block writes as `source: unbound`

- GIVEN observation content ending with `<!-- code_refs -->\n{"schema": 1, "nodes": [], "source": "unbound"}\n`
- WHEN `engram_io.save_observation(...)` is called
- THEN the content is written
- AND `binding.extract(saved_content)` returns an empty list with `source: unbound`

---

### REQ-4: One-time backfill

The system SHALL provide a backfill command that appends a `code_refs` block to existing observations that lack one. The command SHALL default to **dry-run** (no writes), SHALL preserve the original prose byte-for-byte, SHALL preserve `created_at`, SHALL advance `updated_at`, and SHALL be **idempotent** across re-runs.

#### Scenario: Dry-run reports would-change count without writing

- GIVEN 46 observations in the project, none of which contain a `code_refs` block
- WHEN the backfill command runs with default flags
- THEN it reports `46/46 would change, 0 errors`
- AND it does not write to the database
- AND no observation gains a `code_refs` block

#### Scenario: Apply appends block without altering prose

- GIVEN an observation whose prose is 800 characters long with no marker
- WHEN the backfill command runs with `--apply`
- THEN the observation's first 800 characters are byte-for-byte identical to the original
- AND the trailing block now reads `<!-- code_refs -->\n{"schema": 1, "nodes": [...], "source": "backfill"}\n`
- AND `confidence` for every backfilled binding equals `0.3`

#### Scenario: `created_at` is preserved; `updated_at` advances

- GIVEN an observation with `created_at = T0`
- WHEN the backfill command runs with `--apply`
- THEN the saved row has `created_at = T0`
- AND the saved row has `updated_at > T0`

#### Scenario: Backfill is idempotent

- GIVEN 46 observations already contain a `code_refs` block with `source: backfill`
- WHEN the backfill command runs again with `--apply`
- THEN it reports `0/46 would change, 46 skipped (already backfilled)`
- AND no observation is rewritten

---

### REQ-5: Non-breaking behavior

The system SHALL remain compatible with: (a) saves that do not include a `code_refs` block, (b) older engram binaries reading new content, (c) FTS5 prose queries against observations that carry a new trailing block.

#### Scenario: Saves without `code_refs` continue to work

- GIVEN an observation payload with no marker and no block
- WHEN any save path (sdd-propose, sdd-design, manual `mem_save`) is invoked
- THEN the observation is saved successfully
- AND no migration script runs

#### Scenario: Older engram binary reads new content without error

- GIVEN an observation saved by the new code containing a `code_refs` block
- WHEN an older engram binary reads the row via `mem_get_observation`
- THEN it returns the full content as text (including the block)
- AND no parse error is raised

#### Scenario: FTS5 prose query still matches observations with new block

- GIVEN an observation whose prose contains the word `jwt` and which now also has a `code_refs` block
- WHEN an FTS5 search for `jwt` runs
- THEN the observation is returned in the result set
- AND its rank is not materially degraded compared to the pre-block state

---

## PR#2 — Auto-suggest + surface

### REQ-6: Save-time auto-suggestion

When `mem_save` is called and the content has no explicit `code_refs` block, the system SHOULD attempt to suggest bindings via `graphify query`. The system MUST surface at most `max_results` candidates whose score meets or exceeds `threshold`. The system MUST require explicit confirmation (interactive prompt OR `--no-suggest` flag) before persisting any auto-suggested binding. When graphify is unavailable, the save MUST proceed with `source: unbound` — never block.

#### Scenario: Auto-suggest prompts user when ≥1 candidate clears threshold

- GIVEN `graphify query "JWT auth"` returns two candidates with scores `0.6` and `0.4`
- AND `threshold = 0.3`
- WHEN `mem_save(content)` is called interactively
- THEN the user is shown a numbered list of the two candidates with score, label, file
- AND the prompt allows confirming all, some, or none

#### Scenario: User confirms none → saved with empty `nodes`

- GIVEN the auto-suggest prompt is shown with two candidates
- WHEN the user selects "none"
- THEN the saved content ends with `<!-- code_refs -->\n{"schema": 1, "nodes": [], "source": "unbound"}\n`
- AND no candidate ID is recorded

#### Scenario: Graphify unavailable → save proceeds with `unbound`

- GIVEN `graphify` CLI is not installed OR `graph.json` is missing
- WHEN `mem_save(content)` is called
- THEN the save proceeds without prompting
- AND the saved block has `source: unbound`
- AND the reason `"graphify_unavailable"` is recorded in the block's `note` field

#### Scenario: All candidates below threshold → no prompt, save as `unbound`

- GIVEN `graphify query` returns three candidates all scoring below `threshold`
- WHEN `mem_save(content)` is called interactively
- THEN no prompt is shown
- AND the saved block has `source: unbound`
- AND `reason: "below_threshold"` is recorded

#### Scenario: `--no-suggest` flag bypasses graphify entirely

- GIVEN `mem_save(content)` is called with `--no-suggest`
- WHEN the call runs
- THEN `graphify query` is NOT invoked
- AND the saved block has `source: manual` with empty `nodes`
- AND no latency from graphify is incurred

---

### REQ-7: `flow inspect <change>` renders bindings

The system SHALL render the decisions of an SDD change as a table with columns: `decision (id)`, `code_refs` (one row per binding showing `id`, `label`, `file:line`, `confidence`, `source`), and `last_verified` (timestamp or `never`). The renderer MUST isolate malformed blocks per row — one bad row MUST NOT blank the whole table.

#### Scenario: `flow inspect` renders one row per binding

- GIVEN a change with three decisions, the second of which has two code bindings
- WHEN `flow inspect <change>` runs
- THEN the output contains a table with three decision rows
- AND the second decision row spans two sub-rows showing each binding's `id`, `label`, `file:line`, `confidence`, `source`

#### Scenario: Change with no bindings shows explicit `unbound` row

- GIVEN a change whose decisions all carry `source: unbound`
- WHEN `flow inspect <change>` runs
- THEN each row shows `(no bindings)` in the `code_refs` column
- AND the row is NOT omitted from the table

#### Scenario: `last_verified` shows timestamp when known

- GIVEN a decision was last verified at `2026-06-25T19:00:00Z`
- WHEN `flow inspect <change>` runs
- THEN the `last_verified` column for that decision shows `2026-06-25 19:00 UTC (15m ago)`
- AND the relative time is rendered

#### Scenario: Malformed block in one row does not blank the table

- GIVEN one observation has a `code_refs` block with invalid JSON
- WHEN `flow inspect <change>` runs
- THEN the affected row shows `parse error: <offset>` in the `code_refs` column
- AND all other rows render normally

---

### REQ-8: Observability counters

The system SHALL emit the following JSONL counter events via `observability.increment()` and persist them across sessions (Engram observation of type `metrics`, sink at `~/.flow-engineering/metrics.jsonl` unless `FLOW_METRICS_PATH` overrides):

- `suggest_invoked_total` — incremented once per auto-suggest call.
- `suggest_hit_total` — incremented when at least one binding is confirmed.
- `suggest_miss_total` — incremented when no binding is confirmed (rejected, no candidates cleared threshold, or graphify unavailable).
- `bindings_confirmed_total` — incremented by the count of confirmed bindings (a batch of 3 confirmations contributes 3).
- `backfill_observations_total` — total observations scanned for coverage (via `record_backfill_coverage`).
- `backfill_with_refs_total` — observations that carry `source: backfill` (via `record_backfill_coverage`).
- `inspect_invoked_total` — one event per `flow inspect <change>` call.
- `inspect_render_ms` — one event per render with an `elapsed_ms` field.

Derived metric `backfill_coverage(backend)` returns the ratio of backfill-sourced observations to total observations, rounded to 3 decimal places.

#### Scenario: `bindings_confirmed_total` increments by the number of confirmed bindings

- GIVEN the counter `bindings_confirmed_total = N`
- WHEN `mem_save(content)` triggers a prompt and the user confirms `K` bindings
- THEN after the call, `bindings_confirmed_total == N + K`

#### Scenario: `suggest_hit_total` increments when ≥1 candidate is confirmed

- GIVEN the counter `suggest_hit_total = N`
- WHEN `mem_save(content)` triggers a prompt and the user confirms at least one binding
- THEN after the call, `suggest_hit_total == N + 1`

#### Scenario: `backfill_coverage` reflects the ratio of backfilled to total observations

- GIVEN 46 observations are marked `source: backfill` and 57 are not
- WHEN `backfill_coverage(backend)` is queried
- THEN it returns `0.446` (46 / 103) rounded to 3 decimal places
- AND the value reflects the current database state (not a cached stale value)

#### Scenario: `inspect_invoked_total` increments once per `flow inspect` call

- GIVEN the counter `inspect_invoked_total = N`
- WHEN `flow inspect <change>` runs and renders the decision table
- THEN after the call, `inspect_invoked_total == N + 1`

---

## Out of Scope (deferred)

- Migration to a dedicated `code_refs` column on `observations` (v2 — requires engram schema bump).
- Linking via `memory_relations` table (v2 — owned by `vector-semantic-search` follow-up).
- Re-ranking suggestions with embeddings (owned by `vector-semantic-search`).
- Cross-project namespacing beyond the `{project, id}` tuple (owned by `cross-project-federation`).
- Snapshot-aware binding resolution (owned by `graph-snapshots`).

---

## Cross-impact

| Queued change | Relationship | Verdict |
|---|---|---|
| `decision-reality-drift` | Direct prerequisite — drift walks `code_refs` to verify decisions against current graph | Compatible; ship `decision-code-linking` first |
| `cross-project-federation` | Format adopted `{project, id}` from day 1 | Compatible |
| `vector-semantic-search` | Auto-suggester is swappable behind same interface | Complementary, no conflict |
| `graph-snapshots` | Bindings can be re-resolved against any snapshot | No conflict |
| `observability` | New counters feed observability endpoints | Beneficial |

---

## References

- Explore: Engram `sdd/decision-code-linking/explore` (#104)
- Proposal: Engram `sdd/decision-code-linking/proposal` (#107) — Approach D
- Engram schema discovery: Engram #105
- Graphify node-ID stability: Engram #106
- Flow Engineering base spec: `c:/dev/proyects/flow-engineering/spec/spec.md` (REQ-3 state machine, REQ-5 drift surface reused)