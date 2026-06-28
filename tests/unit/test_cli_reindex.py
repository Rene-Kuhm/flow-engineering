"""Unit tests for ``flow reindex`` CLI subcommand (REQ-21).

T2.5 (vector-semantic-search PR#2 batch F): sync streaming reindex with
``--batch-size`` and ``--dry-run`` flags. Idempotent via ``INSERT OR REPLACE``
in ``SqliteVecStore``; crash-resume via per-batch transactions.

Acceptance from REQ-21 (5 scenarios):
1. ``flow reindex`` on empty corpus exits 0 with stderr ``reindex: done — 0 observations indexed``
2. ``flow reindex --batch-size=100`` on 250 obs emits 3 progress lines + done
3. Second ``flow reindex`` is idempotent (count delta = 0)
4. ``flow reindex --dry-run`` reports count without writing
5. Crash mid-run — restart completes from last committed batch

The tests run on the InMemoryBackend + a tmp-path SqliteVecStore. Because the
``[vectors]`` extra is not available in this environment, the reindex path
uses a MockEmbeddingProvider injected via ``monkeypatch.setattr`` on the
``flow reindex`` command's lazy constructor.

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit wires the reindex subcommand.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main
from flow_engineering.engram_io import InMemoryBackend

runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``FLOW_METRICS_PATH`` at a tmp file so tests don't pollute ~/.flow."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


@pytest.fixture
def vectors_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the SqliteVecStore path at a tmp file via monkeypatched helper."""
    path = tmp_path / "vectors.sqlite"
    # The implementation will read this path via a private helper; we set it
    # directly on the cli module so tests don't need to touch ~/.flow.
    from flow_engineering import cli as cli_mod

    monkeypatch.setattr(cli_mod, "_vectors_sqlite_path", lambda: path)
    return path


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


def _seed(backend: InMemoryBackend, n: int) -> None:
    """Seed ``n`` synthetic observations into the backend."""
    for i in range(1, n + 1):
        backend.observations[i] = _make_obs(i, f"obs-{i}", f"observation {i} content")
        backend.next_id = max(backend.next_id, i + 1)


def _patch_default_backend(
    monkeypatch: pytest.MonkeyPatch, backend: InMemoryBackend
) -> None:
    """Patch ``_default_save_backend`` to return the test backend unchanged."""
    monkeypatch.setattr(
        "flow_engineering.cli._default_save_backend", lambda: backend
    )


def _patch_sqlite_vec_available(monkeypatch: pytest.MonkeyPatch, available: bool) -> None:
    """Patch the ``_sqlite_vec_available`` gate the CLI uses."""
    from flow_engineering import cli as cli_mod

    monkeypatch.setattr(cli_mod, "_sqlite_vec_available", lambda: available)


# ---------- REQ-21 scenario 1: empty corpus ----------


class TestReindexEmpty:
    """``flow reindex`` on an empty corpus exits 0 with the no-op summary."""

    def test_reindex_empty_corpus_exits_zero(
        self,
        vectors_path: Path,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        backend = InMemoryBackend()
        _patch_default_backend(monkeypatch, backend)
        _patch_sqlite_vec_available(monkeypatch, True)

        result = runner.invoke(main, ["reindex"])
        assert result.exit_code == 0, result.output
        # The done line MUST be emitted (idempotent: nothing was written).
        assert "reindex: done — 0 observations indexed" in (result.output or "")


# ---------- REQ-21 scenario 2: 250 observations, batch_size=100 ----------


class TestReindexProgress:
    """``flow reindex`` emits progress lines + done line per batch."""

    def test_reindex_250_obs_emits_three_progress_lines(
        self,
        vectors_path: Path,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        backend = InMemoryBackend()
        _seed(backend, 250)
        _patch_default_backend(monkeypatch, backend)
        _patch_sqlite_vec_available(monkeypatch, True)

        result = runner.invoke(main, ["reindex", "--batch-size", "100"])
        assert result.exit_code == 0, result.output
        out = result.output or ""
        # Three progress lines (per batch) + one done line.
        assert "reindex: 100/250 (40%) embedded" in out
        assert "reindex: 200/250 (80%) embedded" in out
        assert "reindex: 250/250 (100%) embedded" in out
        # Done line includes total count + duration.
        assert "reindex: done — 250 observations indexed" in out


# ---------- REQ-21 scenario 3: idempotent second run ----------


class TestReindexIdempotent:
    """Second ``flow reindex`` is a no-op on a fully-indexed corpus."""

    def test_second_reindex_emits_zero_done_line(
        self,
        vectors_path: Path,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        backend = InMemoryBackend()
        _seed(backend, 10)
        _patch_default_backend(monkeypatch, backend)
        _patch_sqlite_vec_available(monkeypatch, True)

        # First run.
        r1 = runner.invoke(main, ["reindex"])
        assert r1.exit_code == 0, r1.output
        # Second run.
        r2 = runner.invoke(main, ["reindex"])
        assert r2.exit_code == 0, r2.output
        # The second run SHOULD still emit the done line — its total is the
        # corpus size (not the delta). The spec says the counter delta is 0
        # for reindex_observations_total; the CLI surface just reports the
        # total scanned, but the file count doesn't change.
        assert "reindex: done — 10 observations indexed" in (r2.output or "")


# ---------- REQ-21 scenario 4: --dry-run ----------


class TestReindexDryRun:
    """``flow reindex --dry-run`` reports count without writing."""

    def test_dry_run_reports_count_no_writes(
        self,
        vectors_path: Path,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        backend = InMemoryBackend()
        _seed(backend, 100)
        _patch_default_backend(monkeypatch, backend)
        _patch_sqlite_vec_available(monkeypatch, True)

        result = runner.invoke(main, ["reindex", "--dry-run"])
        assert result.exit_code == 0, result.output
        # The CLI must report the count of observations needing reindex.
        assert "100" in (result.output or "")
        # The done-line is NOT emitted in dry-run mode (no writes).
        # The vectors.sqlite file must NOT have been touched.
        assert not vectors_path.exists(), (
            f"dry-run should not create the vectors file; got {vectors_path}"
        )


# ---------- REQ-21 scenario 5: crash-resume ----------


class TestReindexCrashResume:
    """After a partial run, a fresh ``flow reindex`` completes the corpus."""

    def test_partial_run_then_full_run_completes(
        self,
        vectors_path: Path,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        backend = InMemoryBackend()
        _seed(backend, 100)
        _patch_default_backend(monkeypatch, backend)
        _patch_sqlite_vec_available(monkeypatch, True)

        # Simulate "partial" by patching the reindex worker so the first call
        # only commits batch 1 (the first batch of 100). The second call
        # completes the corpus. Both calls share the same vectors.sqlite file,
        # so the second run is the "restart" after the simulated crash.
        from flow_engineering import cli as cli_mod

        call_count = {"n": 0}
        original_perform = cli_mod._perform_reindex_batch

        def _crash_after_first(*args: Any, **kwargs: Any) -> Any:
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Pretend we crashed mid-batch: index only the first 50 of
                # the first batch of 100. The second call indexes the rest.
                kwargs["simulate_crash_after"] = 50
            return original_perform(*args, **kwargs)

        monkeypatch.setattr(cli_mod, "_perform_reindex_batch", _crash_after_first)

        # First run: crash after 50.
        r1 = runner.invoke(main, ["reindex", "--batch-size", "50"])
        assert r1.exit_code == 0, r1.output
        # Second run: completes the corpus via INSERT OR REPLACE.
        r2 = runner.invoke(main, ["reindex", "--batch-size", "50"])
        assert r2.exit_code == 0, r2.output
        # The vectors.sqlite file exists and the final run reports the
        # corpus size (idempotent contract).
        assert vectors_path.exists()
        assert "reindex: done — 100 observations indexed" in (r2.output or "")


# ---------- REQ-21: extra missing ----------


class TestReindexExtraMissing:
    """``flow reindex`` with extra missing exits non-zero with install hint."""

    def test_reindex_exits_nonzero_when_extra_missing(
        self,
        vectors_path: Path,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        backend = InMemoryBackend()
        _seed(backend, 5)
        _patch_default_backend(monkeypatch, backend)
        _patch_sqlite_vec_available(monkeypatch, False)

        result = runner.invoke(main, ["reindex"])
        assert result.exit_code == 2, result.output
        assert "pip install flow-engineering[vectors]" in (result.output or "")


# ---------- REQ-22: counter wiring on reindex ----------


class TestReindexCounters:
    """``reindex_observations_total`` and ``reindex_duration_seconds`` fire."""

    def test_reindex_emits_counter_events(
        self,
        vectors_path: Path,
        metrics_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        backend = InMemoryBackend()
        _seed(backend, 10)
        _patch_default_backend(monkeypatch, backend)
        _patch_sqlite_vec_available(monkeypatch, True)

        result = runner.invoke(main, ["reindex"])
        assert result.exit_code == 0, result.output

        events = [
            json.loads(line)
            for line in metrics_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        names = {e["name"] for e in events}
        assert "reindex_observations_total" in names
        assert "reindex_duration_seconds" in names
        reidx_count = [e for e in events if e["name"] == "reindex_observations_total"]
        assert reidx_count[0]["fields"].get("count") == 10


# ---------- system.modules import isolation ----------


class TestReindexModuleImportClean:
    """``import flow_engineering.cli`` MUST NOT pull torch/sqlite_vec/sentence_transformers."""

    def test_subprocess_import_does_not_pull_heavy_deps(self) -> None:
        import subprocess

        script = (
            "import sys; "
            "import flow_engineering.cli as m; "
            "has_search = hasattr(m, 'search'); "
            "has_reindex = hasattr(m, 'reindex'); "
            "torch_loaded = 'torch' in sys.modules; "
            "sv_loaded = 'sqlite_vec' in sys.modules; "
            "st_loaded = 'sentence_transformers' in sys.modules; "
            "print(f'search={has_search} reindex={has_reindex} "
            "torch={torch_loaded} sv={sv_loaded} st={st_loaded}'); "
            "sys.exit(0 if (has_search and has_reindex "
            "and not torch_loaded and not sv_loaded and not st_loaded) else 1)"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
            cwd="C:/dev/proyects/flow-engineering",
        )
        assert result.returncode == 0, (
            f"Heavy deps leaked:\nstdout={result.stdout}\nstderr={result.stderr}"
        )
        assert "torch=False" in result.stdout
        assert "sv=False" in result.stdout
        assert "st=False" in result.stdout
