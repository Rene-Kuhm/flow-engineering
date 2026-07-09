"""Unit tests for ``render_prompt`` / ``render_prompt_safe`` / ``list_required_vars`` (REQ-46).

REQ-46: a shared Jinja2-based renderer that substitutes ``**kwargs`` into a
prompt template fetched by name from the ``PROMPT_NAMES`` catalog. Strict mode
(``render_prompt``) raises ``jinja2.UndefinedError`` on missing declared vars;
``render_prompt_safe`` substitutes the literal sentinel ``<{var_name}>`` for
missing vars (per design D4 — CLI inspection mode). ``list_required_vars``
parses the template AST and returns the set of undeclared variable names so
CLI surfaces know which inputs to prompt the user for.

Strict TDD: written BEFORE the implementation. They MUST fail with
``AttributeError: module 'flow_engineering.prompt_registry' has no attribute
'render_prompt'`` until the impl lands in ``prompt_registry.py``.

The existing ``PROMPT_NAMES`` catalog uses Python ``.format()`` style templates
(``{test_command}``); Jinja2 treats those as literal text, so the tests below
register NEW prompts with Jinja2 ``{{ var }}`` syntax via ``register()`` to
exercise the substitution path without mutating the legacy catalog.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flow_engineering import prompt_registry
from flow_engineering.prompt_registry import (
    list_required_vars,
    render_prompt,
    render_prompt_safe,
)


@pytest.fixture
def jinja_prompts() -> None:
    """Register NEW prompts with Jinja2 syntax for substitution tests.

    Uses the existing ``register()`` shorthand. Cleanup via
    ``unregister_prompt`` after the test to keep the catalog pristine.
    """
    prompt_registry.register(
        name="jinja_simple",
        template="Hello, {{ user_name }}!",
        domain=prompt_registry.PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=("user_name",),
    )
    prompt_registry.register(
        name="jinja_numeric",
        template="count={{ count }} pi={{ pi }}",
        domain=prompt_registry.PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=("count", "pi"),
    )
    prompt_registry.register(
        name="jinja_missing",
        template="Hello, {{ user_name }}!",
        domain=prompt_registry.PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=("user_name",),
    )
    prompt_registry.register(
        name="jinja_multiline",
        template=("Line one with {{ a }}.\nLine two with {{ b }}.\nLine three.\n"),
        domain=prompt_registry.PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=("a", "b"),
    )
    prompt_registry.register(
        name="jinja_no_vars",
        template="Static text, no placeholders.",
        domain=prompt_registry.PromptDomain.OBSERVABILITY,
        version="1.0.0",
        required_vars=(),
    )
    yield
    for name in (
        "jinja_simple",
        "jinja_numeric",
        "jinja_missing",
        "jinja_multiline",
        "jinja_no_vars",
    ):
        prompt_registry.unregister_prompt(name)


class TestRenderPromptSubstitutesStringKwarg:
    def test_renders_string_variable(self, jinja_prompts: None) -> None:
        assert render_prompt("jinja_simple", user_name="World") == "Hello, World!"

    def test_renders_empty_string_variable(self, jinja_prompts: None) -> None:
        assert render_prompt("jinja_simple", user_name="") == "Hello, !"


class TestRenderPromptSubstitutesNumericKwargs:
    def test_renders_int_variable(self, jinja_prompts: None) -> None:
        assert render_prompt("jinja_numeric", count=42, pi=3.14) == "count=42 pi=3.14"

    def test_renders_zero_and_negative(self, jinja_prompts: None) -> None:
        assert render_prompt("jinja_numeric", count=0, pi=-1.5) == "count=0 pi=-1.5"


class TestRenderPromptRaisesPromptRenderErrorOnMissingKwarg:
    def test_strict_mode_raises_when_var_missing(self, jinja_prompts: None) -> None:
        from flow_engineering.prompt_registry import PromptRenderError

        with pytest.raises(PromptRenderError) as excinfo:
            render_prompt("jinja_missing")
        assert "user_name" in str(excinfo.value)
        assert excinfo.value.payload["reason"] == "missing_var"
        assert excinfo.value.payload["prompt"] == "jinja_missing"

    def test_strict_mode_renders_when_all_vars_provided(self, jinja_prompts: None) -> None:
        assert render_prompt("jinja_missing", user_name="Filled") == "Hello, Filled!"


class TestRenderPromptRaisesKeyErrorOnUnknownName:
    def test_unknown_prompt_name_raises_key_error(self) -> None:
        with pytest.raises(KeyError) as excinfo:
            render_prompt("definitely_not_in_catalog")
        assert "definitely_not_in_catalog" in str(excinfo.value)


class TestRenderPromptSafeReturnsSentinelForMissingKwargs:
    def test_safe_substitutes_sentinel(self, jinja_prompts: None) -> None:
        result = render_prompt_safe("jinja_missing")
        # REQ-46 W2: autoescape is on, so the literal sentinel
        # ``<user_name>`` is HTML-escaped to ``&lt;user_name&gt;``.
        # The sentinel marker is still detectable because the
        # variable name ``user_name`` appears in the output between
        # ``&lt;`` and ``&gt;``.
        assert "user_name" in result
        assert "&lt;user_name&gt;" in result

    def test_safe_with_provided_var_substitutes_value(self, jinja_prompts: None) -> None:
        result = render_prompt_safe("jinja_missing", user_name="World")
        assert result == "Hello, World!"

    def test_safe_never_raises_on_missing_var(self, jinja_prompts: None) -> None:
        # Should NOT raise even when called with no kwargs for a template
        # that requires vars.
        result = render_prompt_safe("jinja_simple")
        assert "user_name" in result
        assert "&lt;user_name&gt;" in result


class TestListRequiredVarsReturnsUndeclaredVariables:
    def test_returns_set_of_vars(self, jinja_prompts: None) -> None:
        vars_ = list_required_vars("jinja_numeric")
        assert vars_ == {"count", "pi"}

    def test_returns_empty_for_no_placeholder_template(self, jinja_prompts: None) -> None:
        assert list_required_vars("jinja_no_vars") == set()

    def test_returns_single_var(self, jinja_prompts: None) -> None:
        assert list_required_vars("jinja_simple") == {"user_name"}


class TestRenderPromptHandlesMultilineTemplates:
    def test_multiline_keeps_trailing_newline(self, jinja_prompts: None) -> None:
        result = render_prompt("jinja_multiline", a="alpha", b="beta")
        assert result == ("Line one with alpha.\nLine two with beta.\nLine three.\n")

    def test_multiline_does_not_strip_internal_whitespace(self, jinja_prompts: None) -> None:
        result = render_prompt("jinja_multiline", a="x", b="y")
        assert "Line one with x." in result
        assert "Line two with y." in result
        assert "Line three." in result


class TestRenderPromptFallsBackToPythonFormatForLegacyTemplates:
    """REQ-46 W5 — the 4 migrated PROMPT_NAMES entries use Python ``.format()``
    syntax (``{test_command}``). Jinja2 treats ``{}`` as literal text, so
    ``render_prompt("strict_tdd", test_command="pytest")`` would otherwise
    return the template unchanged. ``render_prompt`` MUST detect that no
    Jinja2 substitution happened AND the template contains format-style
    placeholders, then fall back to ``str.format(**kwargs)`` so the spec's
    single ``render_prompt(name, **kwargs)`` API works for all entries.
    """

    def test_strict_tdd_substitutes_python_format_kwargs(self) -> None:
        """The migrated ``strict_tdd`` template uses ``{test_command}``."""
        result = render_prompt("strict_tdd", test_command="pytest")
        assert result == (
            "STRICT TDD MODE IS ACTIVE. Test runner: pytest. "
            "You MUST follow strict-tdd.md. Do NOT fall back to Standard Mode."
        )

    def test_auto_suggest_header_renders_no_kwargs(self) -> None:
        """Templates with no placeholders return the template unchanged."""
        result = render_prompt("auto_suggest_header")
        assert result == "Auto-suggested code bindings:"

    def test_auto_suggest_footer_renders_no_kwargs(self) -> None:
        """Templates with no placeholders return the template unchanged."""
        result = render_prompt("auto_suggest_footer")
        assert result == "Confirm: [a]ll / [n]one / comma-separated numbers (e.g., 1,3)"

    def test_auto_suggest_empty_renders_no_kwargs(self) -> None:
        """Templates with no placeholders return the template unchanged."""
        result = render_prompt("auto_suggest_empty")
        assert result == "No auto-suggested bindings available."


class TestPromptRenderSafeAutoescapeEnabled:
    """REQ-46 W2 — ``render_prompt_safe`` MUST enable Jinja2 autoescape.

    Per verify-report-pr2b W2 + design D4: the safe renderer is used by
    ``flow prompts show <id>`` to surface missing-variable sentinels to
    the user. If a prompt template contains HTML-looking content
    (``<script>``) and the user-supplied value is malicious, the CLI
    must NOT echo the raw HTML back. ``select_autoescape(
    default_for_string=True)`` enables autoescape for string templates
    by default (no filename known), so the rendered output escapes
    HTML metacharacters.
    """

    def test_render_prompt_safe_escapes_html_in_substituted_value(
        self, jinja_prompts: None
    ) -> None:
        """A Jinja2 template rendered through ``render_prompt_safe`` escapes
        HTML in the substituted value because autoescape is enabled."""
        prompt_registry.register(
            name="autoescape_html",
            template="Hello, {{ user_name }}!",
            domain=prompt_registry.PromptDomain.OBSERVABILITY,
            version="1.0.0",
            required_vars=("user_name",),
        )
        try:
            result = render_prompt_safe("autoescape_html", user_name="<script>alert(1)</script>")
            assert "<script>" not in result
            assert "&lt;script&gt;" in result
            assert "alert(1)" in result
        finally:
            prompt_registry.unregister_prompt("autoescape_html")

    def test_render_prompt_safe_env_has_select_autoescape(self) -> None:
        """The Jinja2 env used by ``render_prompt_safe`` enables autoescape.

        Inspects the module-private ``_safe_jinja_env`` factory (it's an
        implementation detail, but the spec mandates autoescape so we
        verify it directly).
        """
        from flow_engineering.prompt_registry import _safe_jinja_env

        env = _safe_jinja_env()
        assert env.autoescape is not False, (
            "expected _safe_jinja_env to enable autoescape (REQ-46 W2); "
            f"got autoescape={env.autoescape!r}"
        )


class TestPromptRenderErrorException:
    """REQ-46 W6 — ``render_prompt`` MUST raise ``PromptRenderError`` as the
    base class for all render-related failures (unknown id, missing variable,
    template parse error). The CLI maps this to exit code 5 per design D9.
    """

    def test_prompt_render_error_class_exists(self) -> None:
        """The exception class is exported from ``prompt_registry``."""
        from flow_engineering.prompt_registry import PromptRenderError

        assert issubclass(PromptRenderError, Exception)

    def test_prompt_render_error_stores_payload(self) -> None:
        """The exception carries a ``payload`` dict for CLI diagnostics."""
        from flow_engineering.prompt_registry import PromptRenderError

        exc = PromptRenderError({"prompt": "strict_tdd", "reason": "missing_var", "error": "boom"})
        assert exc.payload == {
            "prompt": "strict_tdd",
            "reason": "missing_var",
            "error": "boom",
        }
        assert "boom" in str(exc)

    def test_prompt_not_found_error_inherits_prompt_render_error(self) -> None:
        """``PromptNotFoundError`` subclasses ``PromptRenderError`` so the CLI
        can map both to exit code 5."""
        from flow_engineering.prompt_registry import (
            PromptNotFoundError,
            PromptRenderError,
        )

        assert issubclass(PromptNotFoundError, PromptRenderError)

    def test_render_prompt_unknown_id_raises_prompt_not_found_error(self) -> None:
        """Unknown prompt IDs raise ``PromptNotFoundError`` (subclass of
        ``PromptRenderError``) wrapping the original ``KeyError`` message."""
        from flow_engineering.prompt_registry import (
            PromptNotFoundError,
            PromptRenderError,
        )

        with pytest.raises(PromptNotFoundError) as excinfo:
            render_prompt("definitely_not_in_catalog")
        assert isinstance(excinfo.value, PromptRenderError)
        assert "definitely_not_in_catalog" in str(excinfo.value)

    def test_render_prompt_missing_kwargs_raises_prompt_render_error(
        self, jinja_prompts: None
    ) -> None:
        """Missing Jinja2 kwargs raise ``PromptRenderError`` (wrapping the
        underlying ``UndefinedError``)."""
        from flow_engineering.prompt_registry import PromptRenderError

        with pytest.raises(PromptRenderError) as excinfo:
            render_prompt("jinja_missing")
        assert "user_name" in str(excinfo.value)

    def test_render_prompt_missing_python_format_var_raises_prompt_render_error(
        self,
    ) -> None:
        """Missing ``.format()`` kwargs on a legacy template raise
        ``PromptRenderError`` (wrapping the underlying ``KeyError``)."""
        from flow_engineering.prompt_registry import PromptRenderError

        with pytest.raises(PromptRenderError) as excinfo:
            render_prompt("strict_tdd")  # test_command missing
        assert "test_command" in str(excinfo.value)


class TestRenderPromptWritesToSinkWhenEnabled:
    """REQ-V1.1.3 T3.3 — ``render_prompt`` writes one JSONL line to the
    prompt render sink when ``FLOW_PROMPT_LOG=1``.

    The sink is opt-in: default OFF keeps write-free agent flows
    untouched. When ON, every successful AND failed render is recorded
    with the var_keys tuple (no values — only names for privacy + size).
    """

    def test_successful_render_writes_event_when_enabled(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log_path = tmp_path / "prompt_renders.jsonl"
        from flow_engineering import prompt_render_log as log_mod

        monkeypatch.setattr(log_mod, "DEFAULT_PROMPT_RENDER_LOG_PATH", log_path)
        monkeypatch.setenv("FLOW_PROMPT_LOG", "1")

        render_prompt("strict_tdd", test_command="pytest")

        raw = log_path.read_text(encoding="utf-8").strip()
        assert raw
        import json as _json

        data = _json.loads(raw)
        assert data["prompt_id"] == "strict_tdd"
        assert data["ok"] is True
        assert data["error"] is None
        assert data["var_keys"] == ["test_command"]
        assert data["elapsed_ms"] >= 0.0

    def test_failed_render_writes_failure_event_when_enabled(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log_path = tmp_path / "prompt_renders.jsonl"
        from flow_engineering import prompt_render_log as log_mod

        monkeypatch.setattr(log_mod, "DEFAULT_PROMPT_RENDER_LOG_PATH", log_path)
        monkeypatch.setenv("FLOW_PROMPT_LOG", "1")
        monkeypatch.setattr(
            "flow_engineering.prompt_registry.render_prompt_safe",
            None,  # placeholder
            raising=False,
        )

        with pytest.raises(Exception):  # noqa: B017, PT011
            render_prompt("definitely_not_in_catalog_xyz")

        # Unknown prompt_id still records a failure event.
        raw = log_path.read_text(encoding="utf-8").strip()
        assert raw
        import json as _json

        data = _json.loads(raw)
        assert data["prompt_id"] == "definitely_not_in_catalog_xyz"
        assert data["ok"] is False
        assert data["error"] == "unknown"

    def test_no_write_when_log_disabled(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        log_path = tmp_path / "prompt_renders.jsonl"
        from flow_engineering import prompt_render_log as log_mod

        monkeypatch.setattr(log_mod, "DEFAULT_PROMPT_RENDER_LOG_PATH", log_path)
        monkeypatch.delenv("FLOW_PROMPT_LOG", raising=False)

        render_prompt("strict_tdd", test_command="pytest")

        # Default OFF → no file.
        assert not log_path.exists()
