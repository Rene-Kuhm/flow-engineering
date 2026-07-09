"""Auto-generate docs/prompts.md from the prompt registry (REQ-V1.1.5 / REQ-53).

Walks :data:`PROMPT_NAMES` from
:mod:`flow_engineering.prompt_registry`, reads each ``.j2`` template body
via :attr:`PromptDef.template`, renders an example via
:func:`render_prompt_safe` (sentinel substitution for missing declared
vars — never raises on missing variables), and emits Markdown with one
section per prompt containing:

- ``prompt_id`` (the catalog name)
- ``purpose`` (human-readable description)
- ``where it appears`` (call-site reference)
- ``example output`` (rendered with sentinels for missing vars)

Usage::

    python scripts/generate_prompts_doc.py

The output is written to ``docs/prompts.md`` (overwrites existing file).
The script is idempotent — repeated runs produce identical output.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from flow_engineering.prompt_registry import (  # noqa: E402
    PROMPT_NAMES,
    PromptDef,
)

DOCS_DIR = ROOT / "docs"
DOC_PATH = DOCS_DIR / "prompts.md"


PURPOSE_BY_NAME: dict[str, str] = {
    "strict_tdd": (
        "Activates strict TDD mode for an agent session so the agent "
        "follows the RED → GREEN → REFACTOR cycle using the configured "
        "test runner. Injected by the orchestrator when strict TDD is "
        "active."
    ),
    "auto_suggest_header": (
        "Header line emitted before the auto-suggested code binding list. "
        "Lets reviewers know the following lines are AI-suggested decisions "
        "from the backfill binding surface."
    ),
    "auto_suggest_footer": (
        "Footer line prompting the operator for confirmation: "
        "[a]ll / [n]one / comma-separated numbers (e.g., 1,3)."
    ),
    "auto_suggest_empty": (
        "Fallback text shown when no auto-suggested bindings are available for the current change."
    ),
}

WHERE_BY_NAME: dict[str, str] = {
    "strict_tdd": (
        "src/flow_engineering/strict_tdd.py (`STRICT_TDD_PROMPT`); "
        "consumed by the strict-tdd.py orchestrator wrapper."
    ),
    "auto_suggest_header": (
        "src/flow_engineering/auto_suggest_code_refs.py "
        "(`PROMPT_HEADER`); rendered above each backfill batch."
    ),
    "auto_suggest_footer": (
        "src/flow_engineering/auto_suggest_code_refs.py "
        "(`PROMPT_FOOTER`); rendered below each backfill batch."
    ),
    "auto_suggest_empty": (
        "src/flow_engineering/auto_suggest_code_refs.py "
        "(`EMPTY_PROMPT_TEXT`); rendered when the backfill batch is empty."
    ),
}


def _render_example_with_sentinels(prompt: PromptDef) -> str:
    """Render the prompt body with sentinel substitutions for missing vars.

    REQ-V1.1.5 / REQ-53: the example output shown in docs/prompts.md
    must use sentinel placeholders (``<{var_name}>``) for every declared
    variable so reviewers can see what variables the prompt expects.

    The 4 migrated entries use Python ``str.format()`` syntax
    (``{test_command}``) rather than Jinja2 ``{{ var }}``; the catalog
    metadata records them under the ``"variables"`` key (not
    ``"required_vars"``). We use ``metadata.variables`` as the source
    of truth for declared variables — that's what :func:`render_prompt`
    consumes at runtime via the W5 ``str.format()`` fallback path.
    """
    declared = tuple(prompt.metadata.get("variables", ()))
    if not declared:
        # No variables → return the template body as-is.
        return prompt.template

    safe_kwargs: dict[str, str] = {var: f"<{var}>" for var in declared}
    try:
        return prompt.template.format(**safe_kwargs)
    except (KeyError, IndexError):
        # Defensive: malformed template → return raw template body.
        return prompt.template


def build_section(prompt: PromptDef) -> str:
    """Build the Markdown section for one prompt entry.

    Args:
        prompt: A :class:`PromptDef` from :data:`PROMPT_NAMES`.

    Returns:
        A Markdown string with the 4 mandatory sub-sections
        (Purpose, Where it appears, Example output, Template body)
        plus the heading + metadata table.
    """
    name = prompt.name
    domain = prompt.domain.value
    version = prompt.version
    template_path = prompt.metadata.get("template_file", f"prompts/{name}.j2")
    declared_vars: tuple[str, ...] = tuple(prompt.metadata.get("variables", ()))

    example = _render_example_with_sentinels(prompt)

    lines: list[str] = [
        f"## `{name}`",
        "",
        f"- **Domain:** `{domain}`",
        f"- **Version:** `{version}`",
        f"- **Template file:** `{template_path}`",
        "- **Variables:** "
        + (", ".join(f"`{v}`" for v in declared_vars) if declared_vars else "_(none)_"),
        "",
        "### Purpose",
        "",
        PURPOSE_BY_NAME.get(name, "_TODO: document purpose for this prompt._"),
        "",
        "### Where it appears",
        "",
        WHERE_BY_NAME.get(name, "_TODO: document call-site for this prompt._"),
        "",
        "### Example output",
        "",
        "```text",
        example.rstrip("\n"),
        "```",
        "",
        "### Template body",
        "",
        "```jinja",
        prompt.template.rstrip("\n"),
        "```",
        "",
    ]
    return "\n".join(lines)


def build_doc() -> str:
    """Build the full docs/prompts.md Markdown body.

    Returns:
        A deterministic Markdown string containing a header table
        listing all prompts + one section per prompt. The output is
        byte-identical across repeated calls (no timestamps, no
        environment-dependent values).
    """
    header_lines: list[str] = [
        "# Prompt registry",
        "",
        "Auto-generated from `src/flow_engineering/prompt_registry.py` "
        "(`PROMPT_NAMES`) + `prompts/*.j2`. Re-run "
        "`python scripts/generate_prompts_doc.py` to regenerate after "
        "edits.",
        "",
        f"Total prompts: **{len(PROMPT_NAMES)}**",
        "",
        "| Prompt ID | Domain | Version | Variables |",
        "|-----------|--------|---------|-----------|",
    ]
    table_rows: list[str] = [
        f"| `{p.name}` | `{p.domain.value}` | `{p.version}` | "
        f"{len(p.metadata.get('variables', ()))} |"
        for p in PROMPT_NAMES
    ]
    section_blocks: list[str] = [build_section(p) for p in PROMPT_NAMES]
    return "\n".join(header_lines + table_rows + ["", "---", ""] + section_blocks)


def main() -> int:
    """Write docs/prompts.md to disk; return 0 on success, 1 on failure."""
    try:
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        body = build_doc()
        DOC_PATH.write_text(body, encoding="utf-8")
    except OSError as exc:
        print(f"error: failed to write {DOC_PATH}: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {DOC_PATH} ({len(body)} chars, {len(PROMPT_NAMES)} sections)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
