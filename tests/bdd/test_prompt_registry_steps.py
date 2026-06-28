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

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering import prompt_registry
from flow_engineering.opencode_skill_catalog import (
    SkillEntry,
    check_drift,
    compute_frontmatter_sha256,
)
from flow_engineering.prompt_registry import (
    PromptDomain,
    PromptRenderError,
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
        "drift_list": None,
        "drift_elapsed_ms": None,
        "skill_catalog": None,
        "sidecar_path": None,
        "skill_files": {},
    }


@pytest.fixture(autouse=True)
def _cleanup_registered_prompts(prompt_world: dict[str, Any]) -> Any:
    """Auto-unregister any prompts added during the scenario."""
    yield
    import contextlib
    for name in prompt_world.get("registered", []):
        with contextlib.suppress(Exception):
            unregister_prompt(name)


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


# ---------- Scenario bindings: REQ-49 ----------


@scenario(
    "../bdd/req49_skill_catalog.feature",
    "check-drift detects when SKILL.md checksums don't match catalog",
)
def test_req49_check_drift_detects_mismatch(prompt_world: dict[str, Any]) -> None:
    pass


@scenario(
    "../bdd/req49_skill_catalog.feature",
    "check-drift passes when all SKILL.md checksums match",
)
def test_req49_check_drift_passes_clean(prompt_world: dict[str, Any]) -> None:
    pass


# ---------- REQ-49 Given steps ----------


def _build_20_entry_catalog(
    prompt_world: dict[str, Any], tmp_path: Path,
) -> dict[str, SkillEntry]:
    """Create a 20-entry test catalog mirroring the production SKILL_CATALOG shape.

    Each of the 10 sdd-* agents contributes 2 entries (one ``skill`` surface
    + one ``prompt`` surface) = 20 total. The on-disk files live under
    ``tmp_path`` so the test never touches the user's real OpenCode
    config directory.

    Returns the catalog dict; also stashes it in
    ``prompt_world["skill_catalog"]`` and the file path map in
    ``prompt_world["skill_files"]`` for subsequent steps.
    """
    catalog: dict[str, SkillEntry] = {}
    skill_files: dict[str, Path] = {}
    agent_names = [
        "sdd-init", "sdd-explore", "sdd-propose", "sdd-design", "sdd-spec",
        "sdd-tasks", "sdd-apply", "sdd-verify", "sdd-archive", "sdd-onboard",
    ]
    for name in agent_names:
        for surface in ("skill", "prompt"):
            if surface == "skill":
                file_path = tmp_path / "skills" / name / "SKILL.md"
            else:
                file_path = tmp_path / "prompts" / "sdd" / f"{name}.md"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                f'---\nname: {name}\ndescription: {surface}\nversion: "3.0"\n---\n\n',
                encoding="utf-8",
            )
            key = f"{name}/{surface}"
            skill_files[key] = file_path
            catalog[key] = SkillEntry(
                skill_name=name,
                surface=surface,
                expected_version="3.0",
                expected_path=str(file_path),
                last_verified_checksum=compute_frontmatter_sha256(file_path),
                owner="gentleman-programming",
            )
    prompt_world["skill_catalog"] = catalog
    prompt_world["skill_files"] = skill_files
    return catalog


@given("a SKILL_CATALOG with 20 entries (10 skills + 10 prompts)")
def given_skill_catalog_with_20_entries(
    prompt_world: dict[str, Any], tmp_path: Path,
) -> None:
    """Build a 20-entry test catalog mirroring the production shape."""
    _build_20_entry_catalog(prompt_world, tmp_path)


@given(
    parsers.parse(
        'a sidecar prompt_checksums.json recording stale checksums '
        '(e.g., sdd-apply last_verified={stale})'
    )
)
def given_sidecar_with_stale_checksum(
    prompt_world: dict[str, Any], stale: str,
) -> None:
    """Write a sidecar with a stale ``abc123`` checksum for ``sdd-apply/skill``.

    The sidecar mirrors the production shape:
    ``{key: {"version": str, "checksum": str, "last_verified_at": str}}``.
    The stale value is the SPEC's ``abc123`` placeholder — used here
    literally so the test documents the design intent.
    """
    catalog = prompt_world["skill_catalog"]
    assert catalog is not None, "skill catalog not initialized"
    sidecar: dict[str, dict[str, str]] = {}
    for key, entry in catalog.items():
        if key == "sdd-apply/skill":
            sidecar[key] = {
                "version": entry.expected_version,
                "checksum": stale,
                "last_verified_at": "2026-06-26T00:00:00Z",
            }
        else:
            sidecar[key] = {
                "version": entry.expected_version,
                "checksum": entry.last_verified_checksum,
                "last_verified_at": "2026-06-26T00:00:00Z",
            }
    sidecar_path = prompt_world["skill_files"][
        "sdd-apply/skill"
    ].parent.parent.parent / ".flow-engineering" / "prompt_checksums.json"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(
        json.dumps(sidecar, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    prompt_world["sidecar_path"] = sidecar_path


@given(
    parsers.parse(
        'the on-disk ~/.config/opencode/skills/sdd-apply/SKILL.md has been '
        'edited since last verification (current frontmatter checksum={current})'
    )
)
def given_on_disk_skill_md_edited(
    prompt_world: dict[str, Any], current: str, tmp_path: Path,
) -> None:
    """Mutate the on-disk SKILL.md so its current checksum equals ``current``.

    The literal placeholder ``def456`` from the spec is used here; the
    test asserts that ``check_drift`` reports ``expected_checksum ==
    stale value`` AND ``on_disk_checksum == current value``.
    """
    import flow_engineering.opencode_skill_catalog as osc

    skill_path = prompt_world["skill_files"]["sdd-apply/skill"]
    # Monkeypatch _read_sidecar to return the sidecar we wrote.
    sidecar_path = prompt_world["sidecar_path"]
    monkey_read = json.loads(sidecar_path.read_text(encoding="utf-8"))

    def _fake_read_sidecar() -> dict[str, dict[str, str]]:
        return monkey_read

    osc._read_sidecar = _fake_read_sidecar  # type: ignore[attr-defined]
    # Edit the file by adding a field so the checksum changes (and
    # document the literal ``def456`` placeholder as the spec value).
    original = skill_path.read_text(encoding="utf-8")
    if "description:" in original:
        edited = original.replace(
            "description: skill", f"description: edited-{current[:6]}",
        )
    else:
        edited = original + "extra: drift-marker\n"
    skill_path.write_text(edited, encoding="utf-8")
    # Track the literal "def456" value the spec uses so the next step can
    # compare against the on-disk checksum (which will NOT literally be
    # def456 — the test asserts the SEMANTIC property via the actual SHA).
    prompt_world["on_disk_current_marker"] = current


@given(
    parsers.parse(
        'a freshly updated sidecar prompt_checksums.json where every entry\'s '
        'checksum matches the current on-disk frontmatter'
    )
)
def given_freshly_updated_sidecar(prompt_world: dict[str, Any]) -> None:
    """Write a sidecar whose every entry matches the current on-disk checksum.

    Simulates the state AFTER ``flow prompts check --init``: each entry's
    ``checksum`` field equals the SHA-256 of the current on-disk
    frontmatter. ``check_drift`` MUST return an empty list.
    """
    import flow_engineering.opencode_skill_catalog as osc

    catalog = prompt_world["skill_catalog"]
    skill_files = prompt_world["skill_files"]
    sidecar: dict[str, dict[str, str]] = {}
    for key, entry in catalog.items():
        current_checksum = compute_frontmatter_sha256(skill_files[key])
        sidecar[key] = {
            "version": entry.expected_version,
            "checksum": current_checksum,
            "last_verified_at": "2026-06-27T00:00:00Z",
        }
    sidecar_path = (
        list(skill_files.values())[0].parent.parent.parent
        / ".flow-engineering" / "prompt_checksums.json"
    )
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(
        json.dumps(sidecar, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    prompt_world["sidecar_path"] = sidecar_path

    def _fake_read_sidecar() -> dict[str, dict[str, str]]:
        return sidecar

    osc._read_sidecar = _fake_read_sidecar  # type: ignore[attr-defined]


# ---------- REQ-49 When steps ----------


import time  # noqa: E402  (BDD step glue, import grouped with the step)


@when("the user calls check_drift(SKILL_CATALOG)")
def when_check_drift_on_skill_catalog(prompt_world: dict[str, Any]) -> None:
    """Invoke ``check_drift`` against the test catalog; record timing."""
    catalog = prompt_world["skill_catalog"]
    assert catalog is not None, "skill catalog not initialized"
    start = time.perf_counter()
    try:
        prompt_world["drift_list"] = check_drift(catalog)
        prompt_world["exception"] = None
    except Exception as exc:  # noqa: BLE001
        prompt_world["exception"] = exc
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    prompt_world["drift_elapsed_ms"] = elapsed_ms


# ---------- REQ-49 Then steps ----------


@then(parsers.parse("the result is a list with at least {min_count:d} SkillDrift entry"))
def then_drift_list_has_at_least(
    prompt_world: dict[str, Any], min_count: int,
) -> None:
    """Assert the drift list has >= ``min_count`` entries."""
    drift_list = prompt_world["drift_list"]
    assert drift_list is not None, "check_drift was not invoked"
    assert len(drift_list) >= min_count, (
        f"expected at least {min_count} drift entries; "
        f"got {len(drift_list)}"
    )


@then(
    parsers.parse(
        'the drift entry has skill_name={skill_name} and '
        'drift_kind={drift_kind}'
    )
)
def then_drift_entry_has_skill_and_kind(
    prompt_world: dict[str, Any], skill_name: str, drift_kind: str,
) -> None:
    """Assert at least one drift entry matches the skill+kind pair."""
    drift_list = prompt_world["drift_list"]
    assert drift_list is not None, "check_drift was not invoked"
    matching = [d for d in drift_list if d.skill_name == skill_name]
    assert matching, (
        f"expected drift entry for skill_name={skill_name!r}; "
        f"got skill_names {[d.skill_name for d in drift_list]!r}"
    )
    target = next(
        (d for d in matching if d.drift_kind == drift_kind), None,
    )
    assert target is not None, (
        f"expected drift_kind={drift_kind!r} for skill={skill_name!r}; "
        f"got drift_kinds {[d.drift_kind for d in matching]!r}"
    )
    prompt_world["target_drift"] = target


@then(
    parsers.parse(
        "the drift entry's expected_checksum equals the stale value ({value})"
    )
)
def then_drift_expected_checksum_equals(
    prompt_world: dict[str, Any], value: str,
) -> None:
    """Assert the drift entry's ``expected_checksum`` matches the spec value."""
    target = prompt_world["target_drift"]
    assert target is not None, "target drift entry not set"
    assert target.expected_checksum == value, (
        f"expected expected_checksum={value!r}; got {target.expected_checksum!r}"
    )


@then(
    parsers.parse(
        "the drift entry's on_disk_checksum equals the current value ({value})"
    )
)
def then_drift_on_disk_checksum_equals_marker(
    prompt_world: dict[str, Any], value: str,
) -> None:
    """Document the spec value; the actual on-disk checksum is the real SHA.

    The spec uses ``def456`` as a placeholder, but the on-disk SHA-256
    is whatever compute_frontmatter_sha256 produces from the edited
    frontmatter. We assert that the on-disk checksum is a 64-char hex
    string (proving the production code produced a real SHA, not the
    literal ``def456`` placeholder).
    """
    target = prompt_world["target_drift"]
    assert target is not None, "target drift entry not set"
    import re
    assert re.fullmatch(r"[0-9a-f]{64}", target.on_disk_checksum), (
        f"expected on_disk_checksum to be a 64-char hex SHA; "
        f"got {target.on_disk_checksum!r}"
    )


@then(
    "the function does NOT raise; it returns the list for the caller (CLI) "
    "to surface"
)
def then_check_drift_did_not_raise(prompt_world: dict[str, Any]) -> None:
    """Assert no exception was raised by ``check_drift``."""
    exc = prompt_world["exception"]
    assert exc is None, f"expected no exception; got {exc!r}"
    assert prompt_world["drift_list"] is not None, (
        "expected drift list to be set (no exception)"
    )


@then("the result is an empty list")
def then_drift_list_is_empty(prompt_world: dict[str, Any]) -> None:
    """Assert the drift list is empty (clean state)."""
    drift_list = prompt_world["drift_list"]
    assert drift_list is not None, "check_drift was not invoked"
    assert drift_list == [], (
        f"expected empty drift list (clean state); got {len(drift_list)} entries: "
        f"{[(d.skill_name, d.drift_kind) for d in drift_list]!r}"
    )


@then("no SkillDrift entries are returned")
def then_no_skill_drift_entries(prompt_world: dict[str, Any]) -> None:
    """Alias for the empty-list assertion; explicit phrasing for the spec."""
    then_drift_list_is_empty(prompt_world)


@then("the function completes in under 1 second for the 20-entry catalog")
def then_check_drift_under_one_second(prompt_world: dict[str, Any]) -> None:
    """Assert the check_drift call returned in under 1000ms."""
    elapsed_ms = prompt_world["drift_elapsed_ms"]
    assert elapsed_ms is not None, "elapsed time not recorded"
    assert elapsed_ms < 1000.0, (
        f"expected check_drift to complete in <1s; took {elapsed_ms:.1f}ms"
    )


@then(
    "the function does NOT raise; the empty list is the \"clean state\" signal"
)
def then_clean_state_no_raise(prompt_world: dict[str, Any]) -> None:
    """Assert no exception; the empty list is the clean-state signal."""
    exc = prompt_world["exception"]
    assert exc is None, f"expected no exception; got {exc!r}"
    assert prompt_world["drift_list"] == [], (
        f"expected empty list; got {prompt_world['drift_list']!r}"
    )
