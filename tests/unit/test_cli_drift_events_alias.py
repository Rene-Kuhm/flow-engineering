"""Unit tests for ``flow drift-events {list,tail,stats}`` 1-release DEPRECATED Click group alias (REQ-V1.2.4).

The pre-v1.2 surface was a top-level ``flow drift-events`` Click group.
v1.2 nests the events read-side under the new ``drift`` group
(``flow drift events {list,tail,stats}`` is the canonical surface).

For ONE release cycle (v1.2 → v1.3), the hyphenated
``flow drift-events {list,tail,stats}`` form keeps working as a
``deprecated=True`` Click group alias that emits a ``DeprecationWarning``
on every invocation and delegates to the new canonical subcommands. This
preserves backwards compatibility for v1.0 / v1.1 operators with shell
aliases / cron jobs / docs pointing at the hyphenated name. The alias is
REMOVED in v1.3 per the ``SnapshotGraphMissing`` v1.1 precedent.

Click 8+ emits the deprecation warning to stderr as a plain text line
(``DeprecationWarning: The command 'drift-events' is deprecated.``),
NOT via Python's ``warnings.warn()`` machinery. The tests assert on
``result.stderr`` accordingly.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering.cli import main
from flow_engineering.drift_event_log import DriftEvent, DriftEventLog

runner = CliRunner()


@pytest.fixture
def seeded_log(tmp_path: Path) -> Path:
    """Pre-seed a tmp JSONL with 1 LABEL_DRIFT event for the alias tests."""
    log_path = tmp_path / "drift_events.jsonl"
    log = DriftEventLog(path=log_path)
    log.append(
        DriftEvent(
            change="change-alias",
            decision_id=42,
            binding_id="obs-42",
            event_class="LABEL_DRIFT",
            detected_at=1_700_000_000.0,
        )
    )
    return log_path


class TestDriftEventsAlias:
    """REQ-V1.2.4 1-release ``flow drift-events`` Click group alias."""

    def test_alias_list_still_works_with_deprecation_warning(
        self, seeded_log: Path
    ) -> None:
        """``flow drift-events list --path=<tmp>`` exits 0 + emits DeprecationWarning.

        The hyphenated alias is preserved for one release cycle so v1.0/v1.1
        operators do not get a hard ``No such command`` error. The
        command works AND emits a DeprecationWarning on stderr.
        """
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=text",
                "--path", str(seeded_log),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "change-alias" in result.output
        # Click's deprecated=True emits a DeprecationWarning on stderr.
        assert "DeprecationWarning" in result.stderr, (
            f"expected DeprecationWarning on stderr; got {result.stderr!r}"
        )
        assert "drift-events" in result.stderr, (
            f"expected 'drift-events' in deprecation message; got {result.stderr!r}"
        )

    def test_alias_tail_still_works_with_deprecation_warning(
        self, seeded_log: Path
    ) -> None:
        """``flow drift-events tail --path=<tmp>`` exits 0 + emits DeprecationWarning."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "tail",
                "--path", str(seeded_log),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "change-alias" in result.output
        assert "DeprecationWarning" in result.stderr
        assert "drift-events" in result.stderr

    def test_alias_stats_still_works_with_deprecation_warning(
        self, seeded_log: Path
    ) -> None:
        """``flow drift-events stats --path=<tmp>`` exits 0 + emits DeprecationWarning."""
        result = runner.invoke(
            main,
            [
                "drift-events",
                "stats",
                "--path", str(seeded_log),
            ],
        )
        assert result.exit_code == 0, result.output
        # Either the per-class section header or the LABEL_DRIFT key is present.
        assert "Event class" in result.output or "LABEL_DRIFT" in result.output
        assert "DeprecationWarning" in result.stderr
        assert "drift-events" in result.stderr

    def test_alias_dispatches_to_canonical_subcommands(
        self, seeded_log: Path
    ) -> None:
        """``flow drift-events list --format=json`` returns a JSON array (canonical dispatch).

        The alias delegates to the canonical ``flow drift events list``
        subcommand via ``ctx.forward()``. The JSON envelope contract is
        the SAME between the alias and the canonical surface — verify
        both produce byte-identical structured output for the same input.

        Note: Click 8+ mixes stderr into ``result.output`` by default,
        so the JSON envelope is preceded by the deprecation warning line.
        We strip the leading line before parsing the JSON.
        """
        result = runner.invoke(
            main,
            [
                "drift-events",
                "list",
                "--format=json",
                "--path", str(seeded_log),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "DeprecationWarning" in result.stderr
        # Strip the deprecation warning line that CliRunner mixes into output.
        import json as _json
        lines = result.output.splitlines()
        json_lines = [ln for ln in lines if not ln.startswith("DeprecationWarning")]
        payload = _json.loads("\n".join(json_lines))
        assert isinstance(payload, list)
        assert len(payload) == 1
        assert payload[0]["change"] == "change-alias"
        assert payload[0]["decision_id"] == 42
        assert payload[0]["class"] == "LABEL_DRIFT"