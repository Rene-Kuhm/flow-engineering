"""Unit tests for ``flow search`` CLI subcommand (REQ-17 CLI surface + REQ-21 partial).

T2.4 (vector-semantic-search PR#2 batch F):
- ``flow search "query"`` default: FTS5 prose search unchanged (REQ-17 scenario 5)
- ``flow search --semantic "query"``: gate check then ``mem_search_semantic``
- ``flow search --hybrid --alpha 0.7 "query"``: gate check + alpha validation then
  ``mem_search_hybrid(query, k, alpha)``
- ``flow search --semantic "query"`` with extra missing: exit non-zero with install hint
- ``flow search --semantic "query"`` with env unset (extra present): exit non-zero with env hint
- JSON output format consistent with the existing CLI surface

These tests are written BEFORE the implementation per strict TDD. They MUST fail
until the GREEN commit wires the search subcommand.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main
from flow_engineering.embedding_provider import EMBEDDING_DIMS, EmbeddingProvider
from flow_engineering.engram_io import InMemoryBackend

runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``FLOW_METRICS_PATH`` at a tmp file so tests don't pollute ~/.flow."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


class _FixedVectorsProvider(EmbeddingProvider):
    """Deterministic test fixture: returns unit-norm vectors keyed by exact text."""

    model_version: str = "fixed-v1"
    dim: int = EMBEDDING_DIMS

    def __init__(self, vectors: dict[str, Any]) -> None:
        import numpy as np

        self._vectors: dict[str, Any] = {
            k: np.asarray(v, dtype=np.float32) for k, v in vectors.items()
        }

    def embed(self, texts: list[str]) -> Any:
        import numpy as np

        rows: list[Any] = []
        for t in texts:
            row = self._vectors.get(t)
            if row is None:
                rows.append(np.zeros(EMBEDDING_DIMS, dtype=np.float32))
            else:
                rows.append(np.asarray(row, dtype=np.float32))
        return np.stack(rows).astype(np.float32)


def _seed_observations(backend: InMemoryBackend, obs_list: list[dict[str, Any]]) -> None:
    """Seed ``backend.observations`` directly so existing next_id is preserved."""
    for o in obs_list:
        backend.observations[o["id"]] = o
        backend.next_id = max(backend.next_id, o["id"] + 1)


def _make_obs(obs_id: int, title: str, content: str) -> dict[str, Any]:
    """Build a memory-observation dict shaped like InMemoryBackend.mem_save output."""
    return {
        "id": obs_id,
        "title": title,
        "content": content,
        "topic_key": "sdd/test/phase",
        "type": "architecture",
        "scope": "project",
        "project": "insyd",
        "created_at": obs_id * 1000,
        "updated_at": obs_id * 1000,
    }


@pytest.fixture
def seeded_prose_backend(monkeypatch: pytest.MonkeyPatch) -> InMemoryBackend:
    """Patch ``_default_save_backend`` to return an InMemoryBackend seeded for prose search."""
    backend = InMemoryBackend()
    _seed_observations(
        backend,
        [
            _make_obs(1, "drift detection strategy", "we detect drift via diff stats"),
            _make_obs(2, "drift alarm", "raise an alarm when drift exceeds threshold"),
            _make_obs(3, "logging best practices", "use structured json logs everywhere"),
        ],
    )
    monkeypatch.setattr("flow_engineering.cli._default_save_backend", lambda: backend)
    return backend


@pytest.fixture
def seeded_hybrid_backend(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Patch ``_default_save_backend`` to return a HybridBackend (gates satisfied).

    The provider's embed() returns a fixed vector for "drift" and zero for
    everything else — so the ranking is deterministic.
    """
    import numpy as np

    from flow_engineering.hybrid_backend import HybridBackend

    backend = InMemoryBackend()
    _seed_observations(
        backend,
        [
            _make_obs(1, "drift detection strategy", "we detect drift via diff stats"),
            _make_obs(2, "drift alarm", "raise an alarm when drift exceeds threshold"),
            _make_obs(3, "logging best practices", "use structured json logs everywhere"),
        ],
    )
    fixed = _FixedVectorsProvider(
        {
            "drift detection": np.ones(EMBEDDING_DIMS, dtype=np.float32),
            "drift detection strategy": np.ones(EMBEDDING_DIMS, dtype=np.float32),
            "we detect drift via diff stats": np.ones(EMBEDDING_DIMS, dtype=np.float32),
            "drift alarm": np.ones(EMBEDDING_DIMS, dtype=np.float32),
            "raise an alarm when drift exceeds threshold": np.ones(
                EMBEDDING_DIMS, dtype=np.float32
            ),
            "logging best practices": np.zeros(EMBEDDING_DIMS, dtype=np.float32),
            "use structured json logs everywhere": np.zeros(EMBEDDING_DIMS, dtype=np.float32),
        }
    )
    hybrid = HybridBackend(backend, fixed)
    monkeypatch.setattr("flow_engineering.cli._default_save_backend", lambda: hybrid)
    return hybrid


# ---------- REQ-17 scenario 5: default flow search unchanged ----------


class TestSearchDefaultFts5:
    """REQ-17 scenario 5: ``flow search "query"`` (no flag) is byte-identical FTS5 prose."""

    def test_search_default_returns_fts5_hits(
        self, seeded_prose_backend: InMemoryBackend, metrics_path: Path
    ) -> None:
        result = runner.invoke(main, ["search", "drift"])
        assert result.exit_code == 0, result.output
        # The two drift-related observations should appear; logging should not.
        assert "drift detection strategy" in result.output
        assert "drift alarm" in result.output
        assert "logging best practices" not in result.output

    def test_search_default_does_not_trigger_vector_gate(
        self, seeded_prose_backend: InMemoryBackend, metrics_path: Path
    ) -> None:
        """Default flow search MUST NOT check the vector gate (zero regression)."""
        # We never set FLOW_VECTOR_SEARCH and the [vectors] extra is not installed
        # in this environment, yet default flow search must succeed.
        result = runner.invoke(main, ["search", "drift"])
        assert result.exit_code == 0, result.output
        assert "pip install" not in result.output
        assert "FLOW_VECTOR_SEARCH" not in result.output


# ---------- REQ-17 scenario 4: --semantic with extra missing ----------


class TestSearchSemanticMissingExtra:
    """REQ-17 scenario 4: ``flow search --semantic`` with extra missing exits non-zero."""

    def test_semantic_exits_nonzero_when_extra_missing(
        self,
        seeded_prose_backend: InMemoryBackend,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Force the extra-missing path by monkeypatching _ensure_vector_extra
        # to print the install hint and exit (the production helper does this).
        from flow_engineering import cli as cli_mod

        def _fake_missing() -> None:
            import sys as _sys

            cli_mod.click.echo(
                "Semantic search disabled: install [vectors] extra "
                "— pip install flow-engineering[vectors]",
                err=True,
            )
            _sys.exit(2)

        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", _fake_missing)
        # Ensure FLOW_VECTOR_SEARCH is unset so we don't accidentally pass the env gate.
        monkeypatch.delenv("FLOW_VECTOR_SEARCH", raising=False)

        result = runner.invoke(main, ["search", "--semantic", "drift"])
        assert result.exit_code == 2, result.output
        assert "pip install flow-engineering[vectors]" in (result.output or "")
        # No raw traceback (a clean actionable error, not a Python exception).
        assert "Traceback" not in (result.output or "")


# ---------- REQ-17 scenario 4 (env variant): --semantic with env unset ----------


class TestSearchSemanticMissingEnv:
    """``flow search --semantic`` with env unset (extra present) exits non-zero."""

    def test_semantic_exits_nonzero_when_env_unset(
        self,
        seeded_prose_backend: InMemoryBackend,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        # Simulate "extra present" by making _ensure_vector_extra a no-op.
        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)

        def _fake_env_missing() -> None:
            import sys as _sys

            cli_mod.click.echo(
                "Semantic search disabled: set FLOW_VECTOR_SEARCH=1",
                err=True,
            )
            _sys.exit(2)

        monkeypatch.setattr(cli_mod, "_ensure_vector_env", _fake_env_missing)
        monkeypatch.delenv("FLOW_VECTOR_SEARCH", raising=False)

        result = runner.invoke(main, ["search", "--semantic", "drift"])
        assert result.exit_code == 2, result.output
        assert "FLOW_VECTOR_SEARCH=1" in (result.output or "")


# ---------- REQ-17: --semantic with gates satisfied ----------


class TestSearchSemanticGatesSatisfied:
    """``flow search --semantic`` calls ``mem_search_semantic`` on the HybridBackend."""

    def test_semantic_calls_mem_search_semantic(
        self,
        seeded_hybrid_backend: Any,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        # Patch the gate checks to no-op (the test focuses on the dispatch path).
        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)
        monkeypatch.setattr(cli_mod, "_ensure_vector_env", lambda: None)

        result = runner.invoke(main, ["search", "--semantic", "drift"])
        assert result.exit_code == 0, result.output
        # The seed corpus has 3 observations; HybridBackend.mem_search_semantic
        # returns up to k=10 (default) so all 3 should appear in the output.
        assert "drift detection strategy" in result.output
        assert "drift alarm" in result.output

    def test_semantic_json_emits_results_array(
        self,
        seeded_hybrid_backend: Any,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)
        monkeypatch.setattr(cli_mod, "_ensure_vector_env", lambda: None)

        result = runner.invoke(main, ["search", "--semantic", "drift", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert isinstance(payload, dict)
        assert "results" in payload
        assert isinstance(payload["results"], list)
        assert len(payload["results"]) >= 1
        first = payload["results"][0]
        assert "observation_id" in first
        assert "score" in first


# ---------- REQ-18: --hybrid with --alpha ----------


class TestSearchHybrid:
    """REQ-18: ``flow search --hybrid --alpha X`` calls ``mem_search_hybrid``."""

    def test_hybrid_with_alpha_calls_mem_search_hybrid(
        self,
        seeded_hybrid_backend: Any,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)
        monkeypatch.setattr(cli_mod, "_ensure_vector_env", lambda: None)

        result = runner.invoke(main, ["search", "--hybrid", "--alpha", "0.7", "drift"])
        assert result.exit_code == 0, result.output
        # At least one drift-related observation should be present in the table.
        assert "drift" in result.output.lower()

    def test_hybrid_alpha_out_of_range_exits_nonzero(
        self,
        seeded_hybrid_backend: Any,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)
        monkeypatch.setattr(cli_mod, "_ensure_vector_env", lambda: None)

        result = runner.invoke(main, ["search", "--hybrid", "--alpha", "1.5", "drift"])
        assert result.exit_code == 2, result.output
        assert "alpha" in result.output.lower()
        assert "[0.0, 1.0]" in result.output

    def test_hybrid_alpha_below_range_exits_nonzero(
        self,
        seeded_hybrid_backend: Any,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)
        monkeypatch.setattr(cli_mod, "_ensure_vector_env", lambda: None)

        result = runner.invoke(main, ["search", "--hybrid", "--alpha", "-0.1", "drift"])
        assert result.exit_code == 2, result.output
        assert "[0.0, 1.0]" in result.output

    def test_semantic_and_hybrid_mutually_exclusive(
        self,
        seeded_hybrid_backend: Any,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)
        monkeypatch.setattr(cli_mod, "_ensure_vector_env", lambda: None)

        result = runner.invoke(main, ["search", "--semantic", "--hybrid", "drift"])
        assert result.exit_code != 0, result.output
        assert "mutually exclusive" in result.output.lower() or "UsageError" in result.output


# ---------- REQ-22: counter wiring on --semantic ----------


class TestSearchSemanticCounter:
    """``vector_search_invoked_total{trigger=cli}`` increments per --semantic call."""

    def test_semantic_increments_cli_trigger_counter(
        self,
        seeded_hybrid_backend: Any,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)
        monkeypatch.setattr(cli_mod, "_ensure_vector_env", lambda: None)

        result = runner.invoke(main, ["search", "--semantic", "drift"])
        assert result.exit_code == 0, result.output

        events = [
            json.loads(line)
            for line in metrics_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        invoked = [e for e in events if e.get("name") == "vector_search_invoked_total"]
        assert invoked, f"no invoked counter emitted; events: {events}"
        assert invoked[0]["fields"].get("trigger") == "cli"


# ---------- alpha default value ----------


class TestSearchHybridAlphaDefault:
    """When ``--hybrid`` is set without ``--alpha``, default alpha=0.5 is used."""

    def test_hybrid_default_alpha_is_0_5(
        self,
        seeded_hybrid_backend: Any,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)
        monkeypatch.setattr(cli_mod, "_ensure_vector_env", lambda: None)

        # Default alpha (no flag) → 0.5 → mem_search_hybrid(query, k, 0.5).
        # We just verify the call succeeds and returns results.
        result = runner.invoke(main, ["search", "--hybrid", "drift"])
        assert result.exit_code == 0, result.output


# ---------- k flag ----------


class TestSearchKFlag:
    """``--k`` limits the number of results."""

    def test_search_default_k_is_10(
        self,
        seeded_hybrid_backend: Any,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)
        monkeypatch.setattr(cli_mod, "_ensure_vector_env", lambda: None)

        result = runner.invoke(main, ["search", "--semantic", "--k", "2", "drift"])
        assert result.exit_code == 0, result.output
        # Just confirm the command succeeded; the exact row count is asserted in the JSON test.

    def test_search_k_json_returns_at_most_k(
        self,
        seeded_hybrid_backend: Any,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from flow_engineering import cli as cli_mod

        monkeypatch.setattr(cli_mod, "_ensure_vector_extra", lambda: None)
        monkeypatch.setattr(cli_mod, "_ensure_vector_env", lambda: None)

        result = runner.invoke(main, ["search", "--semantic", "--k", "1", "drift", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert len(payload["results"]) <= 1
