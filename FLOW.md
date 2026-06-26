# FLOW — the closed loop in one page

The Flow Engineering orchestrator automates transitions between phases of an Agentic & Context-Driven development cycle.

## The loop

```
         ┌─────────────────────────────────────────────────────────┐
         │                                                         │
         ▼                                                         │
     ┌───────┐    ┌─────────┐    ┌───────┐    ┌───────┐    ┌───────┐
     │ INTENT│───▶│ CONTEXT │───▶│ SPEC  │───▶│ APPLY │───▶│VERIFY │
     └───────┘    └─────────┘    └───────┘    └───────┘    └───┬───┘
                                              ▲                │
                                              │                ▼
                                          ┌───────┐       ┌─────────┐
                                          │ TASKS │       │ ARCHIVE │
                                          └───────┘       └─────────┘
```

## What each transition does

| From → To | Trigger | Mechanism |
|---|---|---|
| INTENT → CONTEXT | `flow new <change>` | CLI scaffolds dirs + state |
| CONTEXT → SPEC | `exploration.md` written | File watcher |
| SPEC → APPLY | `tasks.md` with unchecked items | `flow apply <change>` |
| APPLY → VERIFY | All tasks `[x]` | Auto after apply |
| VERIFY → ARCHIVE | `sdd-verify` returns PASS | Auto |
| ARCHIVE → memory | Archive complete | `mem_save` + `graphify update` |

## Drift detection

Three signals can halt the loop:

1. **Spec drift** — `tasks.md` `[x]` disagrees with apply-progress in Engram
2. **Test failure classification**:
   - `STRUCTURAL` (ImportError, SyntaxError, NameError) → escalate, never retry
   - `TRANSIENT` (TimeoutError, ConnectionError) → retry up to 2 with backoff
   - `CONTRACT` (AssertionError, ValueError) → re-spec, never auto-retry
3. **Memory mismatch** — Engram, FS, and graph disagree

## State machine

```
NEW → EXPLORED → PROPOSED → DESIGNED → SPECIFIED → TASKED →
  APPLYING → VERIFYING → ARCHIVING → DONE
```

Skipping a phase is rejected. Retries allowed in APPLYING/VERIFYING/ARCHIVING up to 2 times per phase.

## Cost guard

Every change has a token budget (default 100k). When 80% used, a warning is logged. When exceeded, the loop pauses for user approval.

## Cross-session recovery

Every phase artifact is `mem_save`d with topic_key `sdd/<change>/<phase>`. On session restart, `flow status` lists in-progress changes and `flow apply <change>` resumes from the last apply-progress in Engram.

## Cross-project changes

`flow new my-change --cross-projects proj-a --cross-projects proj-b` creates a change that touches multiple sub-projects. The orchestrator creates per-project apply-progress and only archives when all reach VERIFIED.
