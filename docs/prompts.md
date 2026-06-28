# Prompt registry

Auto-generated from `src/flow_engineering/prompt_registry.py` (`PROMPT_NAMES`) + `prompts/*.j2`. Re-run `python scripts/generate_prompts_doc.py` to regenerate after edits.

Total prompts: **4**

| Prompt ID | Domain | Version | Variables |
|-----------|--------|---------|-----------|
| `strict_tdd` | `observability` | `1.0.0` | 1 |
| `auto_suggest_header` | `binding` | `1.0.0` | 0 |
| `auto_suggest_footer` | `binding` | `1.0.0` | 0 |
| `auto_suggest_empty` | `binding` | `1.0.0` | 0 |

---

## `strict_tdd`

- **Domain:** `observability`
- **Version:** `1.0.0`
- **Template file:** `prompts/strict_tdd.j2`
- **Variables:** `test_command`

### Purpose

Activates strict TDD mode for an agent session so the agent follows the RED → GREEN → REFACTOR cycle using the configured test runner. Injected by the orchestrator when strict TDD is active.

### Where it appears

src/flow_engineering/strict_tdd.py (`STRICT_TDD_PROMPT`); consumed by the strict-tdd.py orchestrator wrapper.

### Example output

```text
STRICT TDD MODE IS ACTIVE. Test runner: <test_command>. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode.
```

### Template body

```jinja
STRICT TDD MODE IS ACTIVE. Test runner: {test_command}. You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode.
```

## `auto_suggest_header`

- **Domain:** `binding`
- **Version:** `1.0.0`
- **Template file:** `prompts/auto_suggest_header.j2`
- **Variables:** _(none)_

### Purpose

Header line emitted before the auto-suggested code binding list. Lets reviewers know the following lines are AI-suggested decisions from the backfill binding surface.

### Where it appears

src/flow_engineering/auto_suggest_code_refs.py (`PROMPT_HEADER`); rendered above each backfill batch.

### Example output

```text
Auto-suggested code bindings:
```

### Template body

```jinja
Auto-suggested code bindings:
```

## `auto_suggest_footer`

- **Domain:** `binding`
- **Version:** `1.0.0`
- **Template file:** `prompts/auto_suggest_footer.j2`
- **Variables:** _(none)_

### Purpose

Footer line prompting the operator for confirmation: [a]ll / [n]one / comma-separated numbers (e.g., 1,3).

### Where it appears

src/flow_engineering/auto_suggest_code_refs.py (`PROMPT_FOOTER`); rendered below each backfill batch.

### Example output

```text
Confirm: [a]ll / [n]one / comma-separated numbers (e.g., 1,3)
```

### Template body

```jinja
Confirm: [a]ll / [n]one / comma-separated numbers (e.g., 1,3)
```

## `auto_suggest_empty`

- **Domain:** `binding`
- **Version:** `1.0.0`
- **Template file:** `prompts/auto_suggest_empty.j2`
- **Variables:** _(none)_

### Purpose

Fallback text shown when no auto-suggested bindings are available for the current change.

### Where it appears

src/flow_engineering/auto_suggest_code_refs.py (`EMPTY_PROMPT_TEXT`); rendered when the backfill batch is empty.

### Example output

```text
No auto-suggested bindings available.
```

### Template body

```jinja
No auto-suggested bindings available.
```
