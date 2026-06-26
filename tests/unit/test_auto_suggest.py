"""Unit tests for auto_suggest_code_refs.py — save-time auto-suggest (REQ-6).

REQ-6 (PR#2 batch 1): when ``mem_save`` is called without a ``code_refs`` block
AND graphify is available, the system MUST offer auto-suggest candidates above
the threshold (default 0.3) and require explicit confirmation. Three
confirmation channels: (a) interactive prompt when TTY, (b) ``--with-suggest``
CLI flag (non-interactive accept-all), (c) ``FLOW_AUTO_SUGGEST=1`` env var
(non-interactive accept-all). ``--no-suggest`` skips graphify entirely. The
suggester MUST fail-open: any graphify error yields ``source: unbound`` and
the save proceeds without bindings.

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit implements auto_suggest_code_refs.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from flow_engineering.binding import CodeRef

METRICS_PATH_ENV = "FLOW_METRICS_PATH"
FLOW_AUTO_SUGGEST_ENV = "FLOW_AUTO_SUGGEST"


def _ref(node_id: str, label: str, confidence: float, file: str = "x.py", line: int = 1) -> CodeRef:
    return CodeRef(
        project="insyd",
        id=node_id,
        label=label,
        file=file,
        line=line,
        confidence=confidence,
        source="auto_suggest",
    )


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point observability at a tmp_path JSONL file for the test."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv(METRICS_PATH_ENV, str(path))
    return path


@pytest.fixture
def graphify_available(monkeypatch: pytest.MonkeyPatch) -> list[CodeRef]:
    """Patch graphify_query.query_nodes to return a deterministic candidate set."""
    candidates = [
        _ref("src_auth_jwt_tokenmgr", "TokenManager", 0.6, "src/auth/jwt.py", 42),
        _ref("src_auth_oauth_oauthhandler", "OAuthHandler", 0.4, "src/auth/oauth.py", 10),
    ]
    monkeypatch.setattr(
        "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
        lambda text, *, threshold=0.3, max_results=5: [
            r for r in candidates if r.confidence >= threshold
        ][:max_results],
    )
    return candidates


@pytest.fixture
def graphify_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch graphify_query.query_nodes to return [] (fail-open signal)."""
    monkeypatch.setattr(
        "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
        lambda text, *, threshold=0.3, max_results=5: [],
    )


@pytest.fixture
def graphify_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch graphify_query.query_nodes to raise an unexpected exception."""
    def boom(text: str, **kw: Any) -> list[CodeRef]:
        raise RuntimeError("graphify crashed")

    monkeypatch.setattr(
        "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
        boom,
    )


# ---------- Happy path: candidates returned, accepted ----------


class TestHappyPath:
    def test_returns_auto_suggest_when_with_suggest_flag_and_candidates(self, graphify_available):
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        result = auto_suggest_code_refs("jwt auth", with_suggest=True)
        assert result.source == "auto_suggest"
        assert len(result.refs) == 2
        assert [r.id for r in result.refs] == ["src_auth_jwt_tokenmgr", "src_auth_oauth_oauthhandler"]

    def test_returns_auto_suggest_when_env_var_activates(self, graphify_available, monkeypatch):
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        monkeypatch.setenv(FLOW_AUTO_SUGGEST_ENV, "1")
        result = auto_suggest_code_refs("jwt auth")
        assert result.source == "auto_suggest"
        assert len(result.refs) == 2

    def test_threshold_filter_keeps_only_high_confidence(self, graphify_available):
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        result = auto_suggest_code_refs("jwt auth", threshold=0.5, with_suggest=True)
        assert result.source == "auto_suggest"
        assert len(result.refs) == 1
        assert result.refs[0].id == "src_auth_jwt_tokenmgr"


# ---------- No-suggest bypass ----------


class TestNoSuggestBypass:
    def test_no_suggest_returns_manual_without_querying_graphify(self, monkeypatch):
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        def should_not_be_called(text: str, **kw: Any) -> list[CodeRef]:
            raise AssertionError("graphify_query.query_nodes must NOT be called")

        monkeypatch.setattr(
            "flow_engineering.auto_suggest_code_refs.graphify_query.query_nodes",
            should_not_be_called,
        )
        result = auto_suggest_code_refs("jwt auth", no_suggest=True)
        assert result.source == "manual"
        assert result.refs == []
        assert result.error is None


# ---------- Fail-open: graphify unavailable ----------


class TestFailOpen:
    def test_returns_unbound_when_graphify_returns_empty(self, graphify_unavailable, metrics_path):
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        result = auto_suggest_code_refs("obscure query", with_suggest=True)
        assert result.source == "unbound"
        assert result.refs == []
        assert result.error is not None

    def test_returns_unbound_when_graphify_raises(self, graphify_error, metrics_path):
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        result = auto_suggest_code_refs("jwt auth", with_suggest=True)
        assert result.source == "unbound"
        assert result.refs == []
        assert result.error is not None

    def test_records_suggest_invoked_when_called(self, graphify_unavailable, metrics_path):
        from flow_engineering import observability
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        auto_suggest_code_refs("anything", with_suggest=True)
        events = observability.read_all()
        names = [e["name"] for e in events]
        assert "suggest_invoked_total" in names

    def test_records_suggest_hit_when_bindings_confirmed(self, graphify_available, metrics_path):
        from flow_engineering import observability
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        auto_suggest_code_refs("jwt auth", with_suggest=True)
        events = observability.read_all()
        names = [e["name"] for e in events]
        assert "suggest_hit_total" in names
        assert "bindings_confirmed_total" in names
        confirmed = next(
            e for e in events if e["name"] == "bindings_confirmed_total"
        )
        assert confirmed["fields"].get("count") == 2

    def test_records_suggest_miss_when_no_candidates(self, graphify_unavailable, metrics_path):
        from flow_engineering import observability
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        auto_suggest_code_refs("obscure", with_suggest=True)
        events = observability.read_all()
        names = [e["name"] for e in events]
        assert "suggest_miss_total" in names
        assert "suggest_hit_total" not in names


# ---------- Interactive prompt flow ----------


class TestInteractivePrompt:
    def test_prompt_called_when_tty_and_with_suggest_false(self, graphify_available):
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        captured: dict[str, list[CodeRef]] = {}

        def prompt(refs: list[CodeRef]) -> list[CodeRef]:
            captured["refs"] = refs
            return refs  # accept all

        result = auto_suggest_code_refs(
            "jwt auth",
            is_tty=True,
            prompt_fn=prompt,
        )
        assert "refs" in captured
        assert len(captured["refs"]) == 2
        assert result.source == "auto_suggest"
        assert len(result.refs) == 2

    def test_prompt_rejection_returns_unbound(self, graphify_available, metrics_path):
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        def prompt(refs: list[CodeRef]) -> list[CodeRef]:
            return []  # user rejects all

        result = auto_suggest_code_refs(
            "jwt auth",
            is_tty=True,
            prompt_fn=prompt,
        )
        assert result.source == "unbound"
        assert result.refs == []

        from flow_engineering import observability
        events = observability.read_all()
        assert "suggest_miss_total" in [e["name"] for e in events]

    def test_prompt_partial_selection_returns_subset(self, graphify_available):
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        def prompt(refs: list[CodeRef]) -> list[CodeRef]:
            return [refs[0]]  # confirm only first

        result = auto_suggest_code_refs(
            "jwt auth",
            is_tty=True,
            prompt_fn=prompt,
        )
        assert result.source == "auto_suggest"
        assert len(result.refs) == 1
        assert result.refs[0].id == "src_auth_jwt_tokenmgr"

    def test_with_suggest_overrides_tty(self, graphify_available):
        """Even in TTY, --with-suggest bypasses the prompt."""
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        def prompt(refs: list[CodeRef]) -> list[CodeRef]:
            raise AssertionError("prompt_fn must NOT be called when with_suggest=True")

        result = auto_suggest_code_refs(
            "jwt auth",
            is_tty=True,
            with_suggest=True,
            prompt_fn=prompt,
        )
        assert result.source == "auto_suggest"
        assert len(result.refs) == 2


# ---------- Threshold / default constants ----------


class TestDefaults:
    def test_default_threshold_is_0_3(self):
        from flow_engineering.auto_suggest_code_refs import DEFAULT_THRESHOLD

        assert DEFAULT_THRESHOLD == 0.3

    def test_default_max_results_is_5(self):
        from flow_engineering.auto_suggest_code_refs import DEFAULT_MAX_RESULTS

        assert DEFAULT_MAX_RESULTS == 5

    def test_default_is_to_not_prompt_in_non_tty(self, graphify_available, monkeypatch):
        """Without --with-suggest, env, or TTY, fall back to non-interactive accept-all."""
        from flow_engineering.auto_suggest_code_refs import auto_suggest_code_refs

        monkeypatch.delenv(FLOW_AUTO_SUGGEST_ENV, raising=False)
        result = auto_suggest_code_refs("jwt auth", is_tty=False)
        assert result.source == "auto_suggest"
        assert len(result.refs) == 2


# ---------- Pure function: format_suggestion_prompt ----------


class TestFormatSuggestionPrompt:
    def test_format_prompt_lists_candidates_with_score_and_label(self, graphify_available):
        from flow_engineering.auto_suggest_code_refs import format_suggestion_prompt

        text = format_suggestion_prompt(graphify_available)
        # Lists candidates with numbered prefix and score.
        assert "[1]" in text
        assert "[2]" in text
        assert "TokenManager" in text
        assert "0.60" in text or "0.6" in text
        assert "OAuthHandler" in text
        # Has the confirmation hint.
        assert "all" in text.lower() or "confirm" in text.lower() or "yes" in text.lower()

    def test_format_prompt_empty_refs_returns_explanatory_message(self):
        from flow_engineering.auto_suggest_code_refs import format_suggestion_prompt

        text = format_suggestion_prompt([])
        assert "no" in text.lower() or "0" in text
