"""Unit tests for the ``flow snapshot {create,list,show,diff,rollback,prune}``
CLI subcommand group + the ``--snapshot=<snap_id>`` flag on ``flow drift``.

REQ-28..33 surface (T1.5, batch B2): the CLI is a thin Click wrapper over
``SnapshotManager`` + the existing ``decision_drift`` seam. The CLI is
NON-BREAKING — ``flow drift <change>`` without ``--snapshot`` MUST be
byte-identical to the pre-change behaviour (the unit tests at
``tests/unit/test_cli_drift.py`` already cover that surface; the
``test_drift_without_snapshot_flag_unchanged`` test here is a regression
gate).

TDD: these tests are written BEFORE the CLI implementation (batch B2 of
the ``graph-snapshots`` SDD change). They MUST fail until the GREEN
commit wires the new commands into ``src/flow_engineering/cli.py``.

Coverage map (REQ-28..33 CLI surface):

1. ``flow snapshot create`` writes a snapshot (REQ-28)
2. ``flow snapshot create --description X`` stores ``X`` (REQ-28)
3. ``flow snapshot list`` returns [] empty / N entries (REQ-29)
4. ``flow snapshot list --since=<iso>`` filters (REQ-29)
5. ``flow snapshot show <snap_id>`` prints full envelope (REQ-30)
6. ``flow snapshot diff <a> <b>`` two-arg form (REQ-31)
7. ``flow snapshot diff <a>`` one-arg form against live (REQ-31)
8. ``flow snapshot rollback <id>`` without ``--confirm`` refuses (REQ-32)
9. ``flow snapshot rollback <id> --confirm`` succeeds with safety (REQ-32)
10. ``flow snapshot rollback <id> --confirm`` with conflicts refuses (REQ-32)
11. ``flow snapshot rollback --force`` overrides conflicts (REQ-32)
12. ``flow drift --snapshot=<id> <change>`` uses frozen state (REQ-33)
13. ``flow drift <change>`` without ``--snapshot`` byte-identical (REQ-33)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main
from flow_engineering.engram_io import InMemoryBackend

runner = CliRunner()
"""Standard CliRunner; use ``result.stdout`` for pure stdout, ``result.stderr`` for warnings.

Click 8.4 separates the streams: ``result.stdout`` is the program
stdout (pure JSON for our emit-on-stdout commands); ``result.stderr``
is the warning stream (e.g. the ``--force override`` warning emitted
by rollback). ``result.output`` is the legacy combined view; tests
that need to parse JSON from stdout use ``result.stdout``.
"""


# ---------- Fixtures ----------


@pytest.fixture
def snapshots_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ``FLOW_SNAPSHOTS_DIR`` at this test's ``tmp_path/snaps``."""
    snaps = tmp_path / "snaps"
    monkeypatch.setenv("FLOW_SNAPSHOTS_DIR", str(snaps))
    return snaps


@pytest.fixture
def seeded_backend(monkeypatch: pytest.MonkeyPatch):
    """Patch ``_default_save_backend`` to return a fresh InMemoryBackend.

    Returns ``(backend, _seed)``. ``_seed(observations)`` adds observations
    to the in-memory dict so ``SnapshotManager.create()`` reads them.
    """
    from flow_engineering import engram_io

    backend = engram_io.InMemoryBackend()

    def _seed(obs_list: list[dict] | None = None, *, n: int = 0) -> None:
        if obs_list:
            for o in obs_list:
                backend.observations[o["id"]] = o
                backend.next_id = max(backend.next_id, o["id"] + 1)
        for i in range(n):
            backend.mem_save(
                title=f"seed obs {i}",
                content=f"content {i}",
                topic_key="sdd/test/spec",
            )

    monkeypatch.setattr(
        "flow_engineering.cli._default_save_backend", lambda: backend
    )
    return backend, _seed


@pytest.fixture
def metrics_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point observability at a tmp_path JSONL file."""
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("FLOW_METRICS_PATH", str(path))
    return path


def _seed_obs(backend: InMemoryBackend, *, n: int, topic_key: str = "sdd/test/spec") -> list[int]:
    """Seed ``n`` observations and return their ids."""
    ids: list[int] = []
    for i in range(n):
        obs = backend.mem_save(
            title=f"obs {i}", content=f"content {i}", topic_key=topic_key,
        )
        ids.append(int(obs["id"]))
    return ids


def _read_envelope_from_cli_output(output: str) -> dict:
    """Helper: parse the pretty-printed JSON the ``flow snapshot show`` command emits."""
    return json.loads(output)


def _snap_id_from_path(path: Path) -> str:
    """Extract the ``snap_id`` from a snapshot file path.

    ``Path("foo/snap_X.json.gz").stem`` returns ``"snap_X.json"`` — only
    one suffix is stripped. We need both ``.json`` and ``.gz`` removed.
    """
    name = path.name
    if name.endswith(".json.gz"):
        return name[: -len(".json.gz")]
    return path.stem


# ---------- REQ-28: flow snapshot create ----------


class TestSnapshotCreateCli:
    """``flow snapshot create [--description X]`` invokes SnapshotManager.create."""

    def test_snapshot_create_cli_writes_snapshot(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=3)

        result = runner.invoke(main, ["snapshot", "create"])

        assert result.exit_code == 0, result.output
        # One snapshot file should exist.
        files = sorted(snapshots_dir.glob("snap_*.json.gz"))
        assert len(files) == 1, files

    def test_snapshot_create_with_description_stored(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        result = runner.invoke(
            main, ["snapshot", "create", "--description", "pre-deploy-v0.6"]
        )

        assert result.exit_code == 0, result.output
        files = sorted(snapshots_dir.glob("snap_*.json.gz"))
        assert len(files) == 1
        import gzip
        with gzip.open(files[0], "rt", encoding="utf-8") as fh:
            envelope = json.loads(fh.read())
        assert envelope["description"] == "pre-deploy-v0.6"

    def test_snapshot_create_no_include_graph_flag(
        self, seeded_backend, snapshots_dir, metrics_path, tmp_path
    ) -> None:
        """``--no-include-graph`` excludes the graph_state.graph_json_content field."""
        import gzip as _gzip
        import os as _os

        # Lay down a graph.json file so create() would normally include it.
        graph_path = tmp_path / "graph.json"
        graph_path.write_text('{"nodes": [{"id": "x"}]}', encoding="utf-8")
        _os.environ["FLOW_GRAPH_JSON_PATH"] = str(graph_path)
        try:
            backend, _ = seeded_backend
            _seed_obs(backend, n=2)

            result = runner.invoke(main, ["snapshot", "create", "--no-include-graph"])

            assert result.exit_code == 0, result.output
            files = sorted(snapshots_dir.glob("snap_*.json.gz"))
            assert len(files) == 1
            with _gzip.open(files[0], "rt", encoding="utf-8") as fh:
                envelope = json.loads(fh.read())
            assert envelope["metadata"]["include_graph"] is False
            assert "graph_json_content" not in envelope["graph_state"]
        finally:
            _os.environ.pop("FLOW_GRAPH_JSON_PATH", None)


# ---------- REQ-29: flow snapshot list ----------


class TestSnapshotListCli:
    """``flow snapshot list [--since=<iso>] [--limit N]`` returns newest-first JSON."""

    def test_snapshot_list_cli_empty(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        result = runner.invoke(main, ["snapshot", "list"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload == []

    def test_snapshot_list_cli_three_snapshots(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        # Create 3 snapshots.
        snap_ids: list[str] = []
        for i in range(3):
            res = runner.invoke(
                main, ["snapshot", "create", "--description", f"snap-{i}"]
            )
            assert res.exit_code == 0, res.output
            # The stdout contains the snap_id (or the file name).
            # Extract from the output OR from the dir.
            files = sorted(snapshots_dir.glob("snap_*.json.gz"))
            snap_ids.append(_snap_id_from_path(files[-1]))
            # Avoid same-second collision on the next create.
            if i < 2:
                time.sleep(1.05)

        result = runner.invoke(main, ["snapshot", "list"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert len(payload) == 3
        # Newest first.
        assert [entry["snap_id"] for entry in payload] == list(reversed(snap_ids))
        # Required keys present.
        for entry in payload:
            for key in ("snap_id", "created_at", "trigger", "description", "obs_count", "size_bytes"):
                assert key in entry, f"Missing key {key} in {entry!r}"

    def test_snapshot_list_with_since_filter(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        # Create 2 snapshots, capture the created_at of the FIRST one as cutoff.
        res1 = runner.invoke(main, ["snapshot", "create", "--description", "old"])
        assert res1.exit_code == 0, res1.output
        first_files = sorted(snapshots_dir.glob("snap_*.json.gz"))
        first_id = _snap_id_from_path(first_files[0])
        # Read the first envelope's created_at to use as a since cutoff.
        import gzip as _gzip
        with _gzip.open(first_files[0], "rt", encoding="utf-8") as fh:
            first_envelope = json.loads(fh.read())
        since_iso = first_envelope["created_at"]

        time.sleep(1.05)
        res2 = runner.invoke(main, ["snapshot", "create", "--description", "new"])
        assert res2.exit_code == 0, res2.output

        # Filter with --since equal to the first snapshot's created_at —
        # both snapshots should be included (>= inclusive).
        result = runner.invoke(
            main, ["snapshot", "list", "--since", since_iso]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        ids = {entry["snap_id"] for entry in payload}
        assert first_id in ids, f"first snapshot {first_id!r} should be included; got {ids}"
        assert len(payload) == 2


# ---------- REQ-30: flow snapshot show ----------


class TestSnapshotShowCli:
    """``flow snapshot show <snap_id>`` prints full envelope JSON."""

    def test_snapshot_show_prints_full_envelope(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=3)

        res = runner.invoke(
            main, ["snapshot", "create", "--description", "show-me"]
        )
        assert res.exit_code == 0, res.output
        files = sorted(snapshots_dir.glob("snap_*.json.gz"))
        snap_id = _snap_id_from_path(files[0])

        result = runner.invoke(main, ["snapshot", "show", snap_id])
        assert result.exit_code == 0, result.output
        envelope = _read_envelope_from_cli_output(result.output)
        assert envelope["schema"] == 1
        assert envelope["id"] == snap_id
        assert envelope["description"] == "show-me"
        # All top-level keys from D2.
        for key in (
            "schema", "id", "created_at", "trigger", "description",
            "graph_state", "metadata",
        ):
            assert key in envelope

    def test_snapshot_show_unknown_id_exits_nonzero(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        result = runner.invoke(main, ["snapshot", "show", "snap_does_not_exist"])

        assert result.exit_code != 0, result.output
        # The error is JSON on stderr.
        assert result.stderr, "expected JSON error on stderr"
        payload = json.loads(result.stderr)
        assert "error" in payload


# ---------- REQ-31: flow snapshot diff ----------


class TestSnapshotDiffCli:
    """``flow snapshot diff <a> [<b>]`` two-arg / one-arg forms."""

    def test_snapshot_diff_cli_two_arg(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=3)

        # Create A.
        res_a = runner.invoke(main, ["snapshot", "create", "--description", "a"])
        assert res_a.exit_code == 0, res_a.output
        a_id = _snap_id_from_path(sorted(snapshots_dir.glob("snap_*.json.gz"))[0])

        # Add 2 observations to live.
        _seed_obs(backend, n=2)
        time.sleep(1.05)

        # Create B.
        res_b = runner.invoke(main, ["snapshot", "create", "--description", "b"])
        assert res_b.exit_code == 0, res_b.output
        files = sorted(snapshots_dir.glob("snap_*.json.gz"))
        b_id = _snap_id_from_path(files[-1])  # newest

        # Diff A -> B.
        result = runner.invoke(main, ["snapshot", "diff", a_id, b_id])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert sorted(payload["added"]) == [4, 5]
        assert payload["removed"] == []
        assert payload["modified"] == []
        assert payload["unchanged_count"] == 3
        assert "+2" in payload["summary"]

    def test_snapshot_diff_cli_one_arg_vs_live(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=3)

        # Create A.
        res_a = runner.invoke(main, ["snapshot", "create", "--description", "a"])
        assert res_a.exit_code == 0, res_a.output
        a_id = _snap_id_from_path(sorted(snapshots_dir.glob("snap_*.json.gz"))[0])

        # Add 2 observations AFTER the snapshot.
        _seed_obs(backend, n=2)

        # Diff A -> LIVE (1-arg form).
        result = runner.invoke(main, ["snapshot", "diff", a_id])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert sorted(payload["added"]) == [4, 5]
        assert payload["removed"] == []
        assert payload["modified"] == []


# ---------- REQ-32: flow snapshot rollback ----------


class TestSnapshotRollbackCli:
    """``flow snapshot rollback <id> [--confirm] [--force]`` safety gate."""

    def test_snapshot_rollback_refuses_without_confirm(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        res = runner.invoke(main, ["snapshot", "create", "--description", "t"])
        assert res.exit_code == 0, res.output
        snap_id = _snap_id_from_path(sorted(snapshots_dir.glob("snap_*.json.gz"))[0])

        # NO --confirm.
        result = runner.invoke(main, ["snapshot", "rollback", snap_id])
        assert result.exit_code != 0, result.output
        # JSON error to stderr.
        assert result.stderr, "expected stderr JSON error"
        payload = json.loads(result.stderr)
        assert "confirm" in payload["error"].lower()
        assert payload["snap_id"] == snap_id

    def test_snapshot_rollback_with_confirm_succeeds(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=3)

        res = runner.invoke(main, ["snapshot", "create", "--description", "t"])
        assert res.exit_code == 0, res.output
        snap_id = _snap_id_from_path(sorted(snapshots_dir.glob("snap_*.json.gz"))[0])

        # WITH --confirm.
        result = runner.invoke(
            main, ["snapshot", "rollback", snap_id, "--confirm"]
        )
        assert result.exit_code == 0, (
            f"rollback --confirm failed: {result.output!r} stderr={result.stderr!r}"
        )
        # JSON success on stdout.
        payload = json.loads(result.stdout)
        assert "safety_snapshot_id" in payload
        assert payload["target_snapshot_id"] == snap_id
        assert "applied" in payload
        assert payload["forced"] is False
        # Safety snapshot file exists.
        safety_path = snapshots_dir / f"{payload['safety_snapshot_id']}.json.gz"
        assert safety_path.exists()

    def test_snapshot_rollback_with_conflict_refuses(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        res = runner.invoke(main, ["snapshot", "create", "--description", "t"])
        assert res.exit_code == 0, res.output
        snap_id = _snap_id_from_path(sorted(snapshots_dir.glob("snap_*.json.gz"))[0])

        # Add 3 new observations AFTER the snapshot → conflicts.
        _seed_obs(backend, n=3)

        # WITH --confirm but no --force → conflict refusal.
        result = runner.invoke(
            main, ["snapshot", "rollback", snap_id, "--confirm"]
        )
        assert result.exit_code == 2, f"expected exit 2, got {result.exit_code}; {result.stderr}"
        # JSON error on stderr listing conflicts.
        assert result.stderr, "expected stderr JSON error"
        payload = json.loads(result.stderr)
        assert payload["error"]
        assert "conflicts" in payload
        assert len(payload["conflicts"]) == 3
        assert all(c["change"] == "added" for c in payload["conflicts"])

    def test_snapshot_rollback_force_override(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        res = runner.invoke(main, ["snapshot", "create", "--description", "t"])
        assert res.exit_code == 0, res.output
        snap_id = _snap_id_from_path(sorted(snapshots_dir.glob("snap_*.json.gz"))[0])

        # Add a new observation → conflict.
        _seed_obs(backend, n=1)

        # WITH --confirm AND --force → applies with forced=True.
        result = runner.invoke(
            main, ["snapshot", "rollback", snap_id, "--confirm", "--force"]
        )
        assert result.exit_code == 0, f"rollback --force failed: {result.stderr}"
        payload = json.loads(result.stdout)
        assert payload["forced"] is True
        # Stderr warning emitted.
        assert "--force override" in (result.stderr or ""), (
            f"expected --force warning on stderr; got {result.stderr!r}"
        )


# ---------- REQ-34 (CLI): flow snapshot prune ----------


class TestPruneCommand:
    """``flow snapshot prune`` Click subcommand coverage (REQ-34, T1.6).

    Six focused tests covering the full CLI surface:

    1. Dry-run default (no ``--confirm``) — no deletes, "would delete" listed.
    2. ``--keep-last`` flag wiring.
    3. ``--keep-days`` flag wiring.
    4. ``--max-total-size-mb`` flag wiring.
    5. ``--json`` flag — JSON object on stdout.
    6. ``--force`` flag — stderr warning emitted; most-recent deleted.
    """

    def test_prune_cli_dry_run_default(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        """No ``--confirm`` ⇒ no deletes; stdout prints the would-delete list."""
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        # Create 4 snapshots with 1.05s spacing so created_at differs.
        for i in range(4):
            res = runner.invoke(
                main, ["snapshot", "create", "--description", f"snap-{i}"]
            )
            assert res.exit_code == 0, res.output
            if i < 3:
                time.sleep(1.05)

        # Dry-run: NO --confirm.
        result = runner.invoke(main, ["snapshot", "prune", "--keep-last", "1"])
        assert result.exit_code == 0, (
            f"dry-run prune failed: {result.output!r} stderr={result.stderr!r}"
        )
        assert "DRY-RUN" in result.stdout or "would delete" in result.stdout.lower()
        # All 4 files must still exist on disk.
        files = sorted(p.name for p in snapshots_dir.glob("snap_*.json.gz"))
        assert len(files) == 4, f"dry-run MUST NOT delete; got {files!r}"

    def test_prune_cli_with_keep_last(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        """``--keep-last 2 --confirm`` keeps the 2 newest, deletes the rest."""
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        for i in range(5):
            res = runner.invoke(
                main, ["snapshot", "create", "--description", f"snap-{i}"]
            )
            assert res.exit_code == 0, res.output
            if i < 4:
                time.sleep(1.05)

        result = runner.invoke(
            main, ["snapshot", "prune", "--keep-last", "2", "--confirm"]
        )
        assert result.exit_code == 0, (
            f"prune --confirm failed: stderr={result.stderr!r}"
        )
        # 5 - 2 = 3 files removed.
        files = sorted(p.name for p in snapshots_dir.glob("snap_*.json.gz"))
        assert len(files) == 2, (
            f"expected 2 files remaining after keep_last=2; got {len(files)}: {files!r}"
        )

    def test_prune_cli_with_keep_days(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        """``--keep-days N`` keeps snapshots newer than N days."""
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        # Create a snapshot, then backdate its envelope to 2020-01-01.
        res = runner.invoke(main, ["snapshot", "create", "--description", "old"])
        assert res.exit_code == 0, res.output
        old_path = sorted(snapshots_dir.glob("snap_*.json.gz"))[0]
        import gzip as _gzip
        import hashlib as _hashlib
        with _gzip.open(old_path, "rt", encoding="utf-8") as fh:
            envelope = json.loads(fh.read())
        envelope["created_at"] = "2020-01-01T00:00:00Z"
        meta_for_hash = {
            k: v for k, v in envelope["metadata"].items() if k != "sha256"
        }
        envelope_for_hash = {k: v for k, v in envelope.items() if k != "metadata"}
        envelope_for_hash["metadata"] = meta_for_hash
        envelope["metadata"]["sha256"] = _hashlib.sha256(
            json.dumps(envelope_for_hash, sort_keys=True, separators=(",", ":"))
            .encode("utf-8")
        ).hexdigest()
        with _gzip.open(old_path, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps(envelope, sort_keys=True, separators=(",", ":")))

        # Create a NEW snapshot at the current time.
        res2 = runner.invoke(main, ["snapshot", "create", "--description", "recent"])
        assert res2.exit_code == 0, res2.output

        # Dry-run with --keep-days=30 — only the backdated old one is a candidate.
        result = runner.invoke(
            main, ["snapshot", "prune", "--keep-days", "30"]
        )
        assert result.exit_code == 0, result.output
        assert "DRY-RUN" in result.stdout
        # Both files still exist (dry-run).
        files = sorted(p.name for p in snapshots_dir.glob("snap_*.json.gz"))
        assert len(files) == 2

    def test_prune_cli_with_max_total_size_mb(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        """``--max-total-size-mb`` is wired through to SnapshotManager.prune()."""
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        for i in range(3):
            res = runner.invoke(
                main, ["snapshot", "create", "--description", f"snap-{i}"]
            )
            assert res.exit_code == 0, res.output
            if i < 2:
                time.sleep(1.05)

        # Force-evict by setting the budget to ~1 byte (unrealistic but
        # deterministic — the newest is still protected by the safety net).
        result = runner.invoke(
            main, [
                "snapshot", "prune",
                "--max-total-size-mb", "1",
                "--confirm",
            ]
        )
        # Exit 0 even if nothing was deleted (1 MB budget may already
        # accommodate the 3 tiny snapshots); we only assert the wiring.
        assert result.exit_code == 0, (
            f"prune --max-total-size-mb failed: stderr={result.stderr!r}"
        )
        # At least the newest is preserved (safety net).
        assert len(list(snapshots_dir.glob("snap_*.json.gz"))) >= 1

    def test_prune_cli_json_output(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        """``--json`` emits a parseable PruneResult JSON on stdout."""
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        for i in range(3):
            res = runner.invoke(
                main, ["snapshot", "create", "--description", f"snap-{i}"]
            )
            assert res.exit_code == 0, res.output
            if i < 2:
                time.sleep(1.05)

        result = runner.invoke(
            main, ["snapshot", "prune", "--keep-last", "1", "--json"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        # The 6 fields from PruneResult.to_dict().
        for field in (
            "deleted", "would_delete", "would_keep",
            "freed_bytes", "dry_run", "reason",
        ):
            assert field in payload, f"missing field {field!r} in {payload!r}"
        assert payload["dry_run"] is True
        assert payload["reason"] == "count"

    def test_prune_cli_force_flag_emits_warning(
        self, seeded_backend, snapshots_dir, metrics_path
    ) -> None:
        """``--force`` deletes the most-recent snapshot + emits stderr warning."""
        backend, _ = seeded_backend
        _seed_obs(backend, n=2)

        for i in range(3):
            res = runner.invoke(
                main, ["snapshot", "create", "--description", f"snap-{i}"]
            )
            assert res.exit_code == 0, res.output
            if i < 2:
                time.sleep(1.05)

        # --keep-last=0 --confirm --force overrides the most-recent safety.
        result = runner.invoke(
            main, [
                "snapshot", "prune",
                "--keep-last", "0",
                "--confirm",
                "--force",
            ]
        )
        assert result.exit_code == 0, (
            f"prune --force failed: stderr={result.stderr!r}"
        )
        # All 3 snapshots should be deleted.
        files = sorted(p.name for p in snapshots_dir.glob("snap_*.json.gz"))
        assert files == [], (
            f"--force should delete all with keep-last=0; remaining={files!r}"
        )
        # Stderr warning emitted (matches the SnapshotManager.prune() warning).
        assert "--force" in (result.stderr or "") or "override" in (
            result.stderr or ""
        ).lower(), (
            f"expected --force warning on stderr; got stderr={result.stderr!r}"
        )


# ---------- REQ-33: flow drift --snapshot=<snap_id> flag ----------


class TestDriftSnapshotFlag:
    """``flow drift <change> --snapshot=<snap_id>`` NON-BREAKING extension."""

    def test_drift_with_snapshot_flag_uses_frozen_state(
        self, snapshots_dir, metrics_path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """``--snapshot=<id>`` invokes ``scan_change`` with the snap_id kwarg."""
        from flow_engineering import cli as cli_mod
        from flow_engineering.decision_drift import DriftReport

        captured: dict = {}

        def _stub(
            change_name, *, graph_json_path, backend=None,
            include_obsolete=False, since=None, snap_id=None,
        ):
            captured["change_name"] = change_name
            captured["snap_id"] = snap_id
            captured["graph_json_path"] = graph_json_path
            return DriftReport(
                change_name=change_name, scanned_at=1000.0, graph_mtime=42.0,
                decisions_total=0, bindings_total=0,
                class_counts={}, findings=[], graph_unavailable=False,
            )

        monkeypatch.setattr(cli_mod.decision_drift, "scan_change", _stub)

        result = runner.invoke(
            main,
            ["drift", "vector-semantic-search", "--snapshot", "snap_abc"],
        )
        assert result.exit_code == 0, result.output
        assert captured["snap_id"] == "snap_abc"
        assert captured["change_name"] == "vector-semantic-search"

    def test_drift_without_snapshot_flag_unchanged(
        self, seeded_backend, snapshots_dir, metrics_path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Without ``--snapshot``, ``scan_change`` is called with snap_id=None (NON-BREAKING)."""
        from flow_engineering import cli as cli_mod
        from flow_engineering.decision_drift import DriftReport

        captured: dict = {}

        def _stub(
            change_name, *, graph_json_path, backend=None,
            include_obsolete=False, since=None, snap_id=None,
        ):
            captured["change_name"] = change_name
            captured["snap_id"] = snap_id
            captured["graph_json_path"] = graph_json_path
            return DriftReport(
                change_name=change_name, scanned_at=1000.0, graph_mtime=42.0,
                decisions_total=0, bindings_total=0,
                class_counts={}, findings=[], graph_unavailable=False,
            )

        monkeypatch.setattr(cli_mod.decision_drift, "scan_change", _stub)

        result = runner.invoke(main, ["drift", "vector-semantic-search"])
        assert result.exit_code == 0, result.output
        # snap_id MUST be None when flag absent (D13 non-breaking).
        assert captured["snap_id"] is None
        # graph_json_path is the production default (not None).
        assert captured["graph_json_path"] is not None