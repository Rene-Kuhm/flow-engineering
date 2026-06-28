"""BDD step definitions for prompt-registry feature files (REQ-45/46/47).

Covers:
- ``req45_prompt_registry.feature`` (2 scenarios) — REQ-45 catalog discovery
- ``req46_prompt_render.feature`` (3 scenarios) — REQ-46 render_prompt contract
- ``req47_prompt_lint.feature`` (2 scenarios) — REQ-47 lint_prompts surface

The shared BDD glue file is the convention set by ``observability`` (D12 in
``openspec/changes/prompt-registry/design.md``). PR#1 lands all 7 scenarios
here; PR#2 T2.7 extends the file with 5 more scenarios for ``req49`` and
``req50``.

Test isolation:
- Each scenario uses a per-scenario ``prompt_world`` fixture that holds the
  setup prompts + the last command result.
- Test prompts registered via the ``Given`` step are unregistered in the
  teardown so the global ``PROMPT_NAMES`` catalog stays pristine across
  scenarios.
"""
from __future__ import annotations

import re
import subprocess
import sys
from typing import Any

import pytest
from click.testing import CliRunner
from flow_engineering.prompt_registry import PromptRenderError
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering import prompt_registry
from flow_engineering.prompt_registry import (
    PromptDomain,
    get_prompt,
    lint_prompts,
    register,
    render_prompt,
    unregister_prompt,
)


runner = CliRunner()


# ---------- World fixture ----------


@pytest.fixture
def prompt_world() -> dict[str, Any]:
    """Per-scenario scratch state for the prompt-registry BDD scenarios."""
    return {
        "registered": [],
        "result": None,
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "exception": None,
        "rendered": None,
        "lint_report": None,
    }


@pytest.fixture(autouse=True)
def _cleanup_registered_prompts(prompt_world: dict[str, Any]) -> Any:
    """Auto-unregister any prompts added during the scenario."""
    yield
    for name in prompt_world.get("registered", []):
        try:
            unregister_prompt(name)
        except Exception:
            pass


# ---------- Scenario bindings: REQ-45 ----------


@scenario(
    "../bdd/req45_prompt_registry.feature",
    "Registry lists all known prompts by domain",
)
def test_req45_lists_all_known_prompts(prompt_world: dict[str, Any]) -> None:
    pass


@scenario(
    "../bdd/req45_prompt_registry.feature",
    "Registry raises KeyError on unknown prompt name",
)
def test_req45_raises_keyerror_on_unknown(prompt_world: dict[str, Any]) -> None:
    pass


# ---------- Scenario bindings: REQ-46 ----------


@scenario(
    "../bdd/req46_prompt_render.feature",
    "render with no kwargs returns the template as-is",
)
def test_req46_render_no_kwargs(prompt_world: dict[str, Any]) -> None:
    pass


@scenario(
    "../bdd/req46_prompt_render.feature",
    "render with kwargs substitutes Jinja2 placeholders",
)
def test_req46_render_with_kwargs(prompt_world: dict[str, Any]) -> None:
    pass


@scenario(
    "../bdd/req46_prompt_render.feature",
    "render with missing kwargs raises PromptRenderError",
)
def test_req46_render_missing_kwargs(prompt_world: dict[str, Any]) -> None:
    pass


# ---------- Scenario bindings: REQ-47 ----------


@scenario(
    "../bdd/req47_prompt_lint.feature",
    "lint passes for well-formed prompt catalog",
)
def test_req47_lint_passes_clean(prompt_world: dict[str, Any]) -> None:
    pass


@scenario(
    "../bdd/req47_prompt_lint.feature",
    "lint fails for prompt with undefined placeholder variable",
)
def test_req47_lint_fails_on_broken(prompt_world: dict[str, Any]) -> None:
    pass


# ---------- REQ-45 Given steps ----------


@given("the PromptRegistry is initialized")
def given_registry_initialized(prompt_world: dict[str, Any]) -> None:
    """No-op: the catalog is initialized at module import time."""
    assert len(prompt_registry.PROMPT_NAMES) >= 4


# ---------- REQ-45 When steps ----------


@when(
    parsers.parse(
        'I run `python -c "from flow_engineering.prompt_registry import '
        'list_prompts; print(len(list_prompts()))"`'
    )
)
def when_run_list_prompts_count(prompt_world: dict[str, Any]) -> None:
    """Spawn a subprocess that imports ``list_prompts`` and prints the count."""
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from flow_engineering.prompt_registry import list_prompts; "
                "print(len(list_prompts()))"
            ),
        ],
        capture_output=True,
        text=True,
    )
    prompt_world["stdout"] = proc.stdout
    prompt_world["stderr"] = proc.stderr
    prompt_world["exit_code"] = proc.returncode


@when(parsers.parse('I call `get_prompt("{name}")`'))
def when_call_get_prompt(prompt_world: dict[str, Any], name: str) -> None:
    """Call ``get_prompt(name)``; capture any exception."""
    try:
        prompt_world["result"] = get_prompt(name)
        prompt_world["exception"] = None
    except Exception as exc:
        prompt_world["exception"] = exc


# ---------- REQ-45 Then steps ----------


@then(parsers.parse("stdout contains a number >= {min_count:d}"))
def then_stdout_contains_number_at_least(
    prompt_world: dict[str, Any], min_count: int
) -> None:
    """Assert stdout contains an integer >= ``min_count``."""
    match = re.search(r"\b(\d+)\b", prompt_world["stdout"])
    assert match is not None, (
        f"expected a number in stdout; got {prompt_world['stdout']!r}"
    )
    actual = int(match.group(1))
    assert actual >= min_count, (
        f"expected stdout number >= {min_count}; got {actual}"
    )


@then("exit code is 0")
def then_exit_code_zero(prompt_world: dict[str, Any]) -> None:
    assert prompt_world["exit_code"] == 0, (
        f"expected exit 0; got {prompt_world['exit_code']}. "
        f"stdout={prompt_world['stdout']!r} stderr={prompt_world['stderr']!r}"
    )


@then(parsers.parse('a KeyError is raised with "{fragment}"'))
def then_keyerror_with_fragment(
    prompt_world: dict[str, Any], fragment: str
) -> None:
    exc = prompt_world["exception"]
    assert exc is not None, "expected an exception to be raised"
    assert isinstance(exc, KeyError), (
        f"expected KeyError; got {type(exc).__name__}: {exc}"
    )
    assert fragment in str(exc), (
        f"expected {fragment!r} in error message; got {str(exc)!r}"
    )


# ---------- REQ-46 Given steps ----------


@given(
    parsers.parse(
        'the prompt "{name}" exists with template "{template}"'
    )
)
def given_prompt_exists_with_template(
    prompt_world: dict[str, Any], name: str, template: str
) -> None:
    """Register a test prompt with a literal template string."""
    register(
        name=name,
        template=template,
        domain=PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=(),
    )
    prompt_world["registered"].append(name)


# ---------- REQ-46 When steps ----------


@when(parsers.parse('I call `render_prompt("{name}")`'))
def when_render_prompt_no_kwargs(
    prompt_world: dict[str, Any], name: str
) -> None:
    """Call ``render_prompt(name)`` with no kwargs."""
    try:
        prompt_world["rendered"] = render_prompt(name)
        prompt_world["exception"] = None
    except Exception as exc:
        prompt_world["exception"] = exc


@when(
    parsers.parse(
        'I call `render_prompt("{name}", {kwargs})`'
    )
)
def when_render_prompt_with_kwargs(
    prompt_world: dict[str, Any], name: str, kwargs: str
) -> None:
    """Call ``render_prompt(name, **kwargs)`` parsing the kwargs literal.

    The kwargs literal is a BDD-style ``key=value`` list, e.g.
    ``user_name="World"``. We parse it via :mod:`ast` after rewriting
    each ``<identifier>=`` to ``<identifier>:`` so the result is a
    valid Python dict literal.
    """
    import ast

    rewritten = re.sub(
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=", r'"\1":', kwargs
    )
    parsed: dict[str, Any] = ast.literal_eval("{" + rewritten + "}")
    try:
        prompt_world["rendered"] = render_prompt(name, **parsed)
        prompt_world["exception"] = None
    except Exception as exc:
        prompt_world["exception"] = exc


# ---------- REQ-46 Then steps ----------


@then(parsers.parse('the result equals "{expected}"'))
def then_result_equals(prompt_world: dict[str, Any], expected: str) -> None:
    rendered = prompt_world["rendered"]
    assert rendered == expected, (
        f"expected rendered == {expected!r}; got {rendered!r}"
    )


@then(parsers.parse('a PromptRenderError is raised mentioning "{fragment}"'))
def then_promptrendererror_mentioning(
    prompt_world: dict[str, Any], fragment: str
) -> None:
    exc = prompt_world["exception"]
    assert exc is not None, "expected a PromptRenderError to be raised"
    assert isinstance(exc, PromptRenderError), (
        f"expected PromptRenderError; got {type(exc).__name__}: {exc}"
    )
    assert fragment in str(exc), (
        f"expected {fragment!r} in error message; got {str(exc)!r}"
    )


# ---------- REQ-47 Given steps ----------


@given(
    parsers.parse(
        'I register a broken prompt with template "{template}" and '
        'no metadata.required_vars'
    )
)
def given_register_broken_prompt(
    prompt_world: dict[str, Any], template: str
) -> None:
    """Register a prompt with a Jinja2 placeholder but no ``required_vars``.

    The prompt body references an undeclared variable, so the
    ``undefined_var`` lint check will fire.
    """
    register(
        name="broken_bdd_prompt",
        template=template,
        domain=PromptDomain.OBSERVABILITY,
        version="1.0.0",
    )
    prompt_world["registered"].append("broken_bdd_prompt")


# ---------- REQ-47 When steps ----------


@when("I call `lint_prompts()`")
def when_lint_prompts(prompt_world: dict[str, Any]) -> None:
    """Run ``lint_prompts(PROMPT_NAMES)`` and capture the report."""
    prompt_world["lint_report"] = lint_prompts()


# ---------- REQ-47 Then steps ----------


@then("the result is_clean is True")
def then_lint_is_clean(prompt_world: dict[str, Any]) -> None:
    report = prompt_world["lint_report"]
    assert report is not None, "expected lint report to be set"
    assert report.is_clean is True, (
        f"expected is_clean=True; got {report.to_dict()!r}"
    )


@then("the result error_count > 0")
def then_lint_error_count_positive(prompt_world: dict[str, Any]) -> None:
    report = prompt_world["lint_report"]
    assert report is not None, "expected lint report to be set"
    assert report.error_count > 0, (
        f"expected error_count > 0; got {report.to_dict()!r}"
    )


@then(parsers.parse('one error has error_code="{code}"'))
def then_one_error_has_code(
    prompt_world: dict[str, Any], code: str
) -> None:
    report = prompt_world["lint_report"]
    assert report is not None, "expected lint report to be set"
    matching = [e for e in report.errors if e.error_code == code]
    assert matching, (
        f"expected at least one error with code={code!r}; "
        f"got codes {[e.error_code for e in report.errors]!r}"
    )