"""Golden regression tests for ``render_prompt_canonical`` (REQ-V1.2.2).

REQ-V1.2.2 closes the v1.1 carry-forward "golden regression tests for
``render_prompt``" (per ``openspec/changes/v1.2-followups/explore.md``
REQ-48 section + ``decision-drift/spec.md:410``). The 4 PROMPT_NAMES
entries each get a byte-identical snapshot under
``tests/golden/prompts/`` so unintentional template edits (whitespace,
punctuation, escape chars) fail CI with a precise drift message.

The canonical render uses sentinel values per ``PROMPT_NAMES`` entry so
the snapshot does NOT depend on caller kwargs:

- ``strict_tdd`` → ``test_command="TEST_COMMAND"``
- ``auto_suggest_header`` / ``auto_suggest_footer`` / ``auto_suggest_empty``
  → no declared variables (no kwargs)

The companion ``--update-goldens`` flag on ``flow prompts show`` lets
operators regenerate the snapshots when an intentional template change
is approved (mirrors ``scripts/generate_prompts_doc.py`` "regenerate
via ``make docs``" precedent). The CLI flag tests live in
``TestGoldenUpdate`` (added in T2.3 RED).

Strict TDD: tests written BEFORE the helper implementation. They MUST
fail with ``ImportError: cannot import name 'render_prompt_canonical'``
until ``prompt_registry.py`` exposes the helper (T2.2 GREEN).
"""
from __future__ import annotations

from pathlib import Path

from flow_engineering.prompt_registry import render_prompt_canonical

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden" / "prompts"


class TestGoldenRegression:
    """``render_prompt_canonical()`` output is byte-identical to the committed snapshot."""

    def test_strict_tdd_matches_snapshot(self) -> None:
        """strict_tdd snapshot = render_prompt_canonical('strict_tdd')."""
        snapshot = (GOLDEN_DIR / "strict_tdd.txt").read_text(encoding="utf-8")
        rendered = render_prompt_canonical("strict_tdd")
        assert rendered == snapshot, (
            f"strict_tdd drift detected: "
            f"expected {len(snapshot)} bytes, got {len(rendered)} bytes"
        )

    def test_auto_suggest_header_matches_snapshot(self) -> None:
        """auto_suggest_header snapshot = render_prompt_canonical('auto_suggest_header')."""
        snapshot = (GOLDEN_DIR / "auto_suggest_header.txt").read_text(encoding="utf-8")
        rendered = render_prompt_canonical("auto_suggest_header")
        assert rendered == snapshot, (
            f"auto_suggest_header drift detected: "
            f"expected {len(snapshot)} bytes, got {len(rendered)} bytes"
        )

    def test_auto_suggest_footer_matches_snapshot(self) -> None:
        """auto_suggest_footer snapshot = render_prompt_canonical('auto_suggest_footer')."""
        snapshot = (GOLDEN_DIR / "auto_suggest_footer.txt").read_text(encoding="utf-8")
        rendered = render_prompt_canonical("auto_suggest_footer")
        assert rendered == snapshot, (
            f"auto_suggest_footer drift detected: "
            f"expected {len(snapshot)} bytes, got {len(rendered)} bytes"
        )

    def test_auto_suggest_empty_matches_snapshot(self) -> None:
        """auto_suggest_empty snapshot = render_prompt_canonical('auto_suggest_empty')."""
        snapshot = (GOLDEN_DIR / "auto_suggest_empty.txt").read_text(encoding="utf-8")
        rendered = render_prompt_canonical("auto_suggest_empty")
        assert rendered == snapshot, (
            f"auto_suggest_empty drift detected: "
            f"expected {len(snapshot)} bytes, got {len(rendered)} bytes"
        )


class TestCanonicalRenders:
    """Triangulation: the canonical sentinel values produce the expected substrings."""

    def test_strict_tdd_canonical_substitutes_test_command(self) -> None:
        """strict_tdd canonical render contains 'TEST_COMMAND' as the test runner value."""
        rendered = render_prompt_canonical("strict_tdd")
        assert "TEST_COMMAND" in rendered
        assert "{test_command}" not in rendered, (
            "canonical render must NOT leave template placeholders unsubstituted"
        )

    def test_auto_suggest_empty_canonical_has_no_placeholders(self) -> None:
        """auto_suggest_empty canonical render has no Jinja/format placeholders left."""
        rendered = render_prompt_canonical("auto_suggest_empty")
        assert "{{" not in rendered
        assert "}}" not in rendered
        assert "{" not in rendered
        assert "}" not in rendered, (
            f"residual placeholders in canonical render: {rendered!r}"
        )

    def test_strict_tdd_canonical_overrides_accept_user_kwarg(self) -> None:
        """``**overrides`` lets callers substitute canonical kwargs (e.g., 'pytest').

        Operators who pass a different ``test_command`` value get the
        substituted render — the canonical helper is NOT a hard-locked
        sentinel contract; it is a DEFAULT with an explicit override
        path. This guards the snapshot tests from silently breaking if
        a future maintainer renames the canonical sentinel.
        """
        rendered = render_prompt_canonical("strict_tdd", test_command="pytest")
        assert "pytest" in rendered
        assert "TEST_COMMAND" not in rendered, (
            "override should replace the canonical sentinel, not coexist with it"
        )

    def test_unknown_prompt_id_raises_value_error(self) -> None:
        """The helper rejects unknown prompt IDs (mirrors render_prompt contract)."""
        import pytest

        with pytest.raises(ValueError, match="unknown prompt id"):
            render_prompt_canonical("definitely_not_in_catalog_xyz")
