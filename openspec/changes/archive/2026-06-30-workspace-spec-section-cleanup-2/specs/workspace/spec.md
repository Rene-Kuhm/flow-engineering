# workspace-spec-section-cleanup-2 spec

## ADDED Requirements

### REQ-WORKSPACE-SPEC-SECTION-CLEANUP-2
The workspace root spec MUST remove the remaining stale Phase 5 dashboard prose from the already-shipped dashboard sections without expanding scope beyond the three locked text edits.

#### Scenario: Boundary stress test references shipped dashboard
- **GIVEN** `openspec/specs/workspace/spec.md`
- **WHEN** §2 boundary stress tests are read
- **THEN** the Phase 5 dashboard row references the shipped Rich dashboard, not a future TUI/web surface.

#### Scenario: Dependency graph labels Phase 5 as shipped
- **GIVEN** `openspec/specs/workspace/spec.md`
- **WHEN** §4.1 dependency graph is read
- **THEN** the Phase 5 arrow label says `Phase 5 (shipped)`.

#### Scenario: Dependency note uses current-tense shipped wording
- **GIVEN** `openspec/specs/workspace/spec.md`
- **WHEN** §4.1 dependency notes are read
- **THEN** the Phase 5 note states the actual dependency relationship without future-tense wording.

## Out of scope

- Code changes.
- Test changes.
- Phase 5.2 TUI/web/interactive work.
- Any edits to `openspec/changes/v1.1-followups/`.
