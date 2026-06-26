"""Unit tests for cli.py `flow inspect <change>` (REQ-7) and `flow metrics` (REQ-8).

REQ-7: `flow inspect <change>` renders decisions with their `code_refs`
bindings as a table. Columns: timestamp · decision (truncated) · code_refs ·
freshness (last verified). Output supports `--json` for machine consumption.

REQ-8 close: `flow metrics` dumps the JSONL counter sink as a summary.

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit wires the inspect + metrics commands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering.binding import format_code_refs_block
from flow_engineering.cli import main

runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point observability at a tmp_path JSONL file for the test."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


def _make_obs(
    *, obs_id: int, title: str, content: str, created_at: int = 1000, updated_at: int = 1000,
) -> dict:
    """Build an observation dict shaped like InMemoryBackend.mem_save output."""
    return {
        "id": obs_id,
        "title": title,
        "content": content,
        "topic_key": f"sdd/my-change/{title.split('/')[-1] if '/' in title else 'phase'}",
        "type": "architecture",
        "scope": "project",
        "project": "insyd",
        "created_at": created_at,
        "updated_at": updated_at,
    }


@pytest.fixture
def seeded_backend(monkeypatch: pytest.MonkeyPatch):
    """Patch EngramClient to use a pre-seeded InMemoryBackend.

    Returns a tuple ``(backend, observations)`` so callers can read the
    stored state. The CLI uses ``InMemoryBackend`` by default — we
    monkeypatch ``_default_save_backend`` so it returns a backend we
    pre-seed with observations across multiple topics (phases) for the
    same change.
    """
    from flow_engineering import engram_io

    backend = engram_io.InMemoryBackend()
    # Default impl uses mem_search with empty query -- but with topic_key filtering,
    # we need to seed all observations so that change-level queries return them.
    observations: dict[int, dict] = {}

    def _seed(obs_list: list[dict]) -> None:
        for o in obs_list:
            backend.observations[o["id"]] = o
            backend.next_id = max(backend.next_id, o["id"] + 1)
            observations[o["id"]] = o

    monkeypatch.setattr(
        "flow_engineering.cli._default_save_backend", lambda: backend
    )
    return backend, _seed, observations


# ---------- REQ-7: flow inspect basic rendering ----------


class TestInspectBasic:
    """REQ-7 scenario: render decisions with their code_refs as a table."""

    def test_inspect_with_one_binding_renders_one_row(
        self, seeded_backend, metrics_path
    ) -> None:
        from flow_engineering.binding import CodeRef

        _, _seed, _ = seeded_backend
        cref = CodeRef(project="insyd", id="node_x", label="X",
                       file="src/x.py", line=10, confidence=0.9, source="manual")
        content = "## Decision\n\nUse X.\n" + format_code_refs_block([cref], source="manual")
        _seed([
            _make_obs(obs_id=1, title="my-change/propose", content=content),
        ])

        result = runner.invoke(main, ["inspect", "my-change"])
        assert result.exit_code == 0, result.output
        assert "node_x" in result.output
        assert "X" in result.output or "Use X" in result.output

    def test_inspect_with_multiple_bindings_renders_one_row_per_binding(
        self, seeded_backend, metrics_path
    ) -> None:
        from flow_engineering.binding import CodeRef

        _, _seed, _ = seeded_backend
        refs = [
            CodeRef(project="insyd", id=f"node_{i}", label=f"L{i}",
                    file=f"src/{i}.py", line=i, confidence=0.9, source="manual")
            for i in range(3)
        ]
        content = "## Decision\n\nMulti.\n" + format_code_refs_block(refs, source="manual")
        _seed([
            _make_obs(obs_id=1, title="my-change/propose", content=content),
        ])

        result = runner.invoke(main, ["inspect", "my-change"])
        assert result.exit_code == 0, result.output
        # All three binding ids should appear.
        for i in range(3):
            assert f"node_{i}" in result.output

    def test_inspect_with_no_bindings_shows_dash(
        self, seeded_backend, metrics_path
    ) -> None:
        _, _seed, _ = seeded_backend
        content = "## Decision\n\nNo refs.\n" + format_code_refs_block([], source="unbound")
        _seed([
            _make_obs(obs_id=1, title="my-change/propose", content=content),
        ])

        result = runner.invoke(main, ["inspect", "my-change"])
        assert result.exit_code == 0, result.output
        # Either "—" or "(no bindings)" or similar fail-open marker.
        assert "—" in result.output or "no bindings" in result.output.lower()


# ---------- REQ-7: malformed block isolation ----------


class TestInspectMalformed:
    """REQ-7 scenario: malformed block in one row does not blank the table."""

    def test_inspect_isolates_malformed_block(
        self, seeded_backend, metrics_path
    ) -> None:
        _, _seed, _ = seeded_backend
        good_content = (
            "## Decision\n\nGood.\n" + format_code_refs_block([], source="manual")
        )
        bad_content = "## Decision\n\nBad.\n<!-- code_refs -->\n{not json}\n"
        _seed([
            _make_obs(obs_id=1, title="my-change/propose", content=good_content),
            _make_obs(obs_id=2, title="my-change/design", content=bad_content),
        ])

        result = runner.invoke(main, ["inspect", "my-change"])
        assert result.exit_code == 0, result.output
        # The good observation should still be visible (title is its key).
        assert "my-change/propose" in result.output
        # The bad observation should show a parse-error note.
        assert "parse" in result.output.lower() or "error" in result.output.lower()


# ---------- REQ-7: change not found / no observations ----------


class TestInspectEmpty:
    """REQ-7: change with no observations renders gracefully."""

    def test_inspect_with_no_observations_succeeds(
        self, seeded_backend, metrics_path
    ) -> None:
        result = runner.invoke(main, ["inspect", "no-such-change"])
        assert result.exit_code == 0, result.output
        assert "no" in result.output.lower() or "0" in result.output


# ---------- REQ-7: --json flag ----------


class TestInspectJson:
    """REQ-7: --json flag emits machine-readable JSON."""

    def test_inspect_json_emits_valid_json(
        self, seeded_backend, metrics_path
    ) -> None:
        from flow_engineering.binding import CodeRef

        _, _seed, _ = seeded_backend
        cref = CodeRef(project="insyd", id="node_y", label="Y",
                       file="src/y.py", line=5, confidence=0.8, source="manual")
        content = "## Decision\n\nY.\n" + format_code_refs_block([cref], source="manual")
        _seed([
            _make_obs(obs_id=1, title="my-change/propose", content=content),
        ])

        result = runner.invoke(main, ["inspect", "my-change", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert isinstance(payload, list)
        assert len(payload) >= 1
        # Find the row for the propose decision.
        rows = [r for r in payload if "node_y" in json.dumps(r)]
        assert rows, f"no row references node_y; got: {payload}"


# ---------- REQ-7: freshness column ----------


class TestInspectFreshness:
    """REQ-7: freshness column shows age or stale warning."""

    def test_inspect_freshness_recent(
        self, seeded_backend, metrics_path, monkeypatch
    ) -> None:
        """An observation saved recently shows 'Xd ago' (no stale warning)."""
        import time

        from flow_engineering.binding import CodeRef

        _, _seed, _ = seeded_backend
        cref = CodeRef(project="insyd", id="n_recent", label="R",
                       file="src/r.py", line=1, confidence=0.9, source="manual")
        content = "## Decision\n\nR.\n" + format_code_refs_block([cref], source="manual")
        now_ms = int(time.time() * 1000)
        _seed([
            _make_obs(obs_id=1, title="my-change/propose", content=content,
                      created_at=now_ms - 5_000, updated_at=now_ms - 5_000),
        ])

        result = runner.invoke(main, ["inspect", "my-change"])
        assert result.exit_code == 0, result.output
        # Recent should NOT contain stale warning.
        assert "stale" not in result.output.lower()

    def test_inspect_freshness_stale(
        self, seeded_backend, metrics_path, monkeypatch
    ) -> None:
        """An observation >30 days old shows a stale warning."""
        from flow_engineering.binding import CodeRef

        _, _seed, _ = seeded_backend
        cref = CodeRef(project="insyd", id="n_old", label="O",
                       file="src/o.py", line=1, confidence=0.9, source="manual")
        content = "## Decision\n\nO.\n" + format_code_refs_block([cref], source="manual")
        # 60 days ago in ms.
        sixty_days_ms = 60 * 24 * 60 * 60 * 1000
        _seed([
            _make_obs(obs_id=1, title="my-change/propose", content=content,
                      created_at=sixty_days_ms, updated_at=sixty_days_ms),
        ])

        result = runner.invoke(main, ["inspect", "my-change"])
        assert result.exit_code == 0, result.output
        assert "stale" in result.output.lower()


# ---------- REQ-8: flow metrics subcommand ----------


class TestMetricsCommand:
    """REQ-8 close: `flow metrics` dumps the JSONL sink as a summary."""

    def test_metrics_dumps_summary(self, metrics_path) -> None:
        from flow_engineering import observability

        observability.increment("suggest_invoked_total")
        observability.increment("suggest_hit_total", count=2)

        result = runner.invoke(main, ["metrics"])
        assert result.exit_code == 0, result.output
        assert "suggest_invoked_total" in result.output
        assert "suggest_hit_total" in result.output

    def test_metrics_json_emits_dict(self, metrics_path) -> None:
        from flow_engineering import observability

        observability.increment("suggest_invoked_total")
        observability.increment("inspect_invoked_total")

        result = runner.invoke(main, ["metrics", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert isinstance(payload, dict)
        assert "suggest_invoked_total" in payload
        assert "inspect_invoked_total" in payload

    def test_metrics_empty_sink(self, metrics_path) -> None:
        result = runner.invoke(main, ["metrics"])
        assert result.exit_code == 0, result.output
        assert "no" in result.output.lower() or "0" in result.output
