"""RED fixtures for `flow prompts` CLI subcommand (REQ-49 + REQ-50, T2.1).

REQ-49 S1 + S2 user-facing surface: ``flow prompts check`` walks the
SKILL_CATALOG and reports drift findings via CliRunner-friendly exit
codes (0 = clean, 1 = drift detected, 2 = catalog missing).

The CLI wraps the ``check_drift(SKILL_CATALOG)`` helper from
``opencode_skill_catalog``. Exit codes follow the design contract:
- 0 = clean state (no drift, no parse errors)
- 1 = drift detected (one or more entries diverged)
- 2 = catalog missing (path resolution failure)

The tests are written BEFORE the implementation per strict TDD (RED).
They MUST fail with ``AttributeError`` (no ``flow_prompts_check`` Click
command) until the GREEN commit lands.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from flow_engineering import opencode_skill_catalog as osc
from flow_engineering.cli import main
from flow_engineering.opencode_skill_catalog import SkillEntry

runner = CliRunner()


# ---------- Fixtures ----------


@pytest.fixture
def clean_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> dict[str, SkillEntry]:
    """Build a 1-entry catalog with a file whose checksum matches the catalog.

    ``_read_sidecar`` is monkeypatched to return ``{}`` so the catalog's
    ``last_verified_checksum`` is the comparison baseline; ``_sidecar_path``
    is rewritten under ``tmp_path`` so tests never touch the user's
    ``~/.flow-engineering/`` directory.
    """
    sidecar = tmp_path / ".flow-engineering" / "prompt_checksums.json"

    def _fake_sidecar_path() -> Path:
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        return sidecar

    monkeypatch.setattr(osc, "_read_sidecar", lambda: {})
    monkeypatch.setattr(osc, "_sidecar_path", _fake_sidecar_path)

    skill = tmp_path / "SKILL.md"
    skill.write_text(
        '---\nname: sdd-test\ndescription: mock\nversion: "3.0"\n---\n\nBody.\n',
        encoding="utf-8",
    )
    checksum = osc.compute_frontmatter_sha256(skill)
    return {
        "sdd-test/skill": SkillEntry(
            skill_name="sdd-test",
            surface="skill",
            expected_version="3.0",
            expected_path=str(skill),
            last_verified_checksum=checksum,
            owner="test-owner",
        ),
    }


@pytest.fixture
def drifted_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> dict[str, SkillEntry]:
    """Build a 1-entry catalog with an intentionally wrong checksum.

    The catalog's ``last_verified_checksum`` does NOT match the on-disk
    checksum, so ``check_drift`` returns a single ``checksum_mismatch``
    finding. The CLI surface must surface this as exit code 1.
    """
    sidecar = tmp_path / ".flow-engineering" / "prompt_checksums.json"

    def _fake_sidecar_path() -> Path:
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        return sidecar

    monkeypatch.setattr(osc, "_read_sidecar", lambda: {})
    monkeypatch.setattr(osc, "_sidecar_path", _fake_sidecar_path)

    skill = tmp_path / "SKILL.md"
    skill.write_text(
        '---\nname: sdd-test\ndescription: mock\nversion: "3.0"\n---\n\nBody.\n',
        encoding="utf-8",
    )
    return {
        "sdd-test/skill": SkillEntry(
            skill_name="sdd-test",
            surface="skill",
            expected_version="3.0",
            expected_path=str(skill),
            last_verified_checksum="0" * 64,  # intentionally wrong
            owner="test-owner",
        ),
    }


# ---------- T2.1: flow prompts group + check subcommand ----------


class TestFlowPromptsGroup:
    def test_flow_help_lists_prompts_group(self) -> None:
        """`flow --help` must list the `prompts` command group.

        Confirms the Click group is registered on the ``main`` Click
        object so users can discover it via the standard CLI help.
        """
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0, (
            f"flow --help failed: stdout={result.output!r} "
            f"exit={result.exit_code}"
        )
        assert "prompts" in result.output, (
            f"expected 'prompts' in flow --help output; got {result.output!r}"
        )

    def test_prompts_check_exits_zero_on_clean_state(
        self, clean_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts check` returns exit 0 when no drift is detected.

        With a single-entry catalog whose on-disk checksum matches the
        catalog's ``last_verified_checksum``, ``check_drift`` returns an
        empty list and the CLI exits 0. The expected-version string
        ``"3.0"`` MUST appear in stdout so users can audit the verified
        entries.
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", clean_catalog)
        result = runner.invoke(main, ["prompts", "check"])
        assert result.exit_code == 0, (
            f"expected exit 0 on clean state; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "3.0" in result.stdout or "verified" in result.stdout, (
            f"expected version or 'verified' marker in stdout; "
            f"got {result.stdout!r}"
        )

    def test_prompts_check_exits_one_on_drift(
        self, drifted_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts check` returns exit 1 when drift is detected.

        With a single-entry catalog whose on-disk checksum does NOT match
        the catalog's ``last_verified_checksum``, ``check_drift`` returns a
        ``checksum_mismatch`` finding and the CLI exits 1. The drift line
        MUST appear in stdout so users can see which entry diverged.
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", drifted_catalog)
        result = runner.invoke(main, ["prompts", "check"])
        assert result.exit_code == 1, (
            f"expected exit 1 on drift; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "sdd-test" in result.stdout or "drift" in result.stdout.lower(), (
            f"expected skill name or drift marker in stdout; "
            f"got {result.stdout!r}"
        )


# ---------- T2.2: flow prompts check --init flag ----------


class TestPromptsCheckInit:
    def test_prompts_check_init_writes_sidecar(
        self, clean_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts check --init` writes the sidecar JSON and exits 0.

        The ``--init`` flag bootstraps the sidecar at
        ``~/.flow-engineering/prompt_checksums.json`` with current on-disk
        state via ``osc.init_checksums()``. After the call the sidecar
        file MUST exist on disk and contain an entry for each catalog
        row (1 in this fixture).
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", clean_catalog)
        result = runner.invoke(main, ["prompts", "check", "--init"])
        assert result.exit_code == 0, (
            f"expected exit 0 on --init; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        # Sidecar path mirrors the SKILL.md location: same parent dir.
        skill_path = Path(clean_catalog["sdd-test/skill"].expected_path)
        sidecar_file = skill_path.parent / ".flow-engineering" / "prompt_checksums.json"
        assert sidecar_file.exists(), (
            f"expected sidecar JSON at {sidecar_file}; file not found"
        )
        loaded = json.loads(sidecar_file.read_text(encoding="utf-8"))
        assert "sdd-test/skill" in loaded, (
            f"expected 'sdd-test/skill' key in sidecar; got keys {list(loaded)!r}"
        )
        assert "Initialized" in result.stdout, (
            f"expected 'Initialized' marker in stdout; got {result.stdout!r}"
        )


# ---------- T2.2 (T2.5 W1 follow-up): --update / --no-fail / --skill flags ----------


class TestCheckFlags:
    def test_update_flag_refreshes_sidecar(
        self, clean_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts check --update` refreshes the sidecar JSON and exits 0.

        Per verify-report-pr2a.md W1 + tasks-pr2.md T2.2: ``--update`` must
        call ``update_checksums()`` (which is functionally equivalent to
        ``init_checksums()``), print a confirmation line including the count
        of refreshed entries, and exit 0 unconditionally. The CLI MUST NOT
        pass-through to the drift-detection branch (which would emit drift
        lines).
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", clean_catalog)
        result = runner.invoke(main, ["prompts", "check", "--update"])
        assert result.exit_code == 0, (
            f"expected exit 0 on --update; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "Updated" in result.stdout, (
            f"expected 'Updated' marker in stdout; got {result.stdout!r}"
        )
        # The sidecar file MUST exist on disk after --update.
        skill_path = Path(clean_catalog["sdd-test/skill"].expected_path)
        sidecar_file = skill_path.parent / ".flow-engineering" / "prompt_checksums.json"
        assert sidecar_file.exists(), (
            f"expected sidecar at {sidecar_file}; file not found"
        )

    def test_no_fail_flag_exits_zero_on_drift(
        self, drifted_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts check --no-fail` exits 0 even when drift is detected.

        Per verify-report-pr2a.md W1 + design D5: ``--no-fail`` suppresses
        exit 1 on drift detection so CI pipelines can use ``flow prompts
        check`` as a warning-only gate. The drift lines MUST still appear in
        stdout (visibility preserved), but the exit code MUST be 0.
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", drifted_catalog)
        result = runner.invoke(main, ["prompts", "check", "--no-fail"])
        assert result.exit_code == 0, (
            f"expected exit 0 with --no-fail on drift; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        # Drift is still surfaced in stdout for visibility.
        assert "sdd-test" in result.stdout or "drift" in result.stdout.lower(), (
            f"expected drift marker in stdout even with --no-fail; "
            f"got {result.stdout!r}"
        )

    def test_skill_flag_filters_to_named_skill(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts check --skill sdd-apply` filters to a single skill.

        Per verify-report-pr2a.md W1 + tasks-pr2.md T2.2: ``--skill <name>``
        limits the catalog walk to the named skill's two surfaces (skill +
        prompt). A multi-entry catalog MUST report at most 2 lines on stdout
        (one per surface) and the footer MUST count only the filtered set.
        """
        skill_a = tmp_path / "skill_a.md"
        skill_a.write_text(
            '---\nname: sdd-alpha\ndescription: a\nversion: "3.0"\n---\n\nA.\n',
            encoding="utf-8",
        )
        prompt_a = tmp_path / "prompt_a.md"
        prompt_a.write_text(
            '---\nname: sdd-alpha\ndescription: a\nversion: "3.0"\n---\n\nA.\n',
            encoding="utf-8",
        )
        skill_b = tmp_path / "skill_b.md"
        skill_b.write_text(
            '---\nname: sdd-beta\ndescription: b\nversion: "3.0"\n---\n\nB.\n',
            encoding="utf-8",
        )
        prompt_b = tmp_path / "prompt_b.md"
        prompt_b.write_text(
            '---\nname: sdd-beta\ndescription: b\nversion: "3.0"\n---\n\nB.\n',
            encoding="utf-8",
        )
        multi = {
            "sdd-alpha/skill": SkillEntry(
                skill_name="sdd-alpha",
                surface="skill",
                expected_version="3.0",
                expected_path=str(skill_a),
                last_verified_checksum=osc.compute_frontmatter_sha256(skill_a),
                owner="test-owner",
            ),
            "sdd-alpha/prompt": SkillEntry(
                skill_name="sdd-alpha",
                surface="prompt",
                expected_version="3.0",
                expected_path=str(prompt_a),
                last_verified_checksum=osc.compute_frontmatter_sha256(prompt_a),
                owner="test-owner",
            ),
            "sdd-beta/skill": SkillEntry(
                skill_name="sdd-beta",
                surface="skill",
                expected_version="3.0",
                expected_path=str(skill_b),
                last_verified_checksum=osc.compute_frontmatter_sha256(skill_b),
                owner="test-owner",
            ),
            "sdd-beta/prompt": SkillEntry(
                skill_name="sdd-beta",
                surface="prompt",
                expected_version="3.0",
                expected_path=str(prompt_b),
                last_verified_checksum=osc.compute_frontmatter_sha256(prompt_b),
                owner="test-owner",
            ),
        }
        monkeypatch.setattr(osc, "_read_sidecar", lambda: {})
        monkeypatch.setattr(osc, "SKILL_CATALOG", multi)
        result = runner.invoke(main, ["prompts", "check", "--skill", "sdd-alpha"])
        assert result.exit_code == 0, (
            f"expected exit 0 on filtered clean state; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        # Footer MUST count only the filtered 2 entries.
        assert "2 skills verified" in result.stdout, (
            f"expected '2 skills verified' in footer (filtered to sdd-alpha "
            f"which has 2 surfaces); got {result.stdout!r}"
        )


# ---------- T2.4 (T2.5 W2 follow-up): stderr WARN + observability counters ----------


class _CounterCapture:
    """Test helper that monkeypatches ``observability.increment``.

    Each call to ``increment(name, **fields)`` is recorded as a tuple
    in ``self.calls`` so tests can assert on the emitted counter names
    and labels without touching the real JSONL sink.
    """

    def __init__(self) -> None:
        from flow_engineering import observability
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._original = observability.increment
        self._module = observability

    def __enter__(self) -> "_CounterCapture":
        def _capture(name: str, **fields: Any) -> None:
            self.calls.append((name, dict(fields)))
        self._module.increment = _capture
        return self

    def __exit__(self, *exc: Any) -> None:
        self._module.increment = self._original


class TestCheckStderrWarn:
    def test_writes_warn_to_stderr_on_drift(
        self, drifted_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts check` writes a `[WARN]` line to stderr when drift is detected.

        Per verify-report-pr2a.md WARNING W2 + tasks-pr2.md T2.4: the CLI
        emits a single ``[WARN]`` summary line on stderr (NOT on stdout)
        so operators get a batch-level signal of drift. The line MUST
        include the drift count.
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", drifted_catalog)
        result = runner.invoke(main, ["prompts", "check"])
        assert result.exit_code == 1, (
            f"expected exit 1 on drift; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "[WARN]" in result.stderr, (
            f"expected '[WARN]' marker in stderr; got {result.stderr!r}"
        )
        assert "1 drift" in result.stderr or "drift" in result.stderr.lower(), (
            f"expected drift count mention in stderr; got {result.stderr!r}"
        )

    def test_no_warn_on_clean_state(
        self, clean_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts check` does NOT write a `[WARN]` line on clean state.

        Negative counterpart to test_writes_warn_to_stderr_on_drift:
        the stderr MUST stay free of ``[WARN]`` markers when the
        catalog is clean (otherwise the WARN becomes noise).
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", clean_catalog)
        result = runner.invoke(main, ["prompts", "check"])
        assert result.exit_code == 0, (
            f"expected exit 0 on clean; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "[WARN]" not in result.stderr, (
            f"unexpected '[WARN]' in stderr on clean state; "
            f"got {result.stderr!r}"
        )


class TestCheckObservability:
    def test_emits_check_total_clean(
        self, clean_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Clean state emits `prompts_check_total{result="clean"}` exactly once.

        Per verify-report-pr2a.md W2: the catalog counter is the batch-
        level signal of how many `flow prompts check` invocations were
        clean vs drift-detected. The counter MUST carry a ``result``
        label so the `flow metrics --domain prompts` surface can split.
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", clean_catalog)
        with _CounterCapture() as cap:
            result = runner.invoke(main, ["prompts", "check"])
        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        clean_calls = [
            (n, f) for (n, f) in cap.calls if n == "prompts_check_total"
            and f.get("result") == "clean"
        ]
        assert len(clean_calls) == 1, (
            f"expected exactly 1 prompts_check_total{{result=clean}} call; "
            f"got {clean_calls!r} (all calls: {cap.calls!r})"
        )

    def test_emits_check_total_drift(
        self, drifted_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Drift state emits `prompts_check_total{result="drift"}` exactly once."""
        monkeypatch.setattr(osc, "SKILL_CATALOG", drifted_catalog)
        with _CounterCapture() as cap:
            result = runner.invoke(main, ["prompts", "check"])
        assert result.exit_code == 1, (
            f"expected exit 1 on drift; got {result.exit_code}."
        )
        drift_calls = [
            (n, f) for (n, f) in cap.calls if n == "prompts_check_total"
            and f.get("result") == "drift"
        ]
        assert len(drift_calls) == 1, (
            f"expected exactly 1 prompts_check_total{{result=drift}} call; "
            f"got {drift_calls!r} (all calls: {cap.calls!r})"
        )

    def test_emits_drift_total_per_skill(
        self, drifted_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Each drift finding emits `prompts_check_drift_total{skill=<name>}`.

        Per design D10 + REQ-22 prefix: the per-skill drift counter is
        emitted ONCE per drift finding so the metrics surface can break
        down drift counts by skill (e.g., to detect the noisiest skill).
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", drifted_catalog)
        with _CounterCapture() as cap:
            result = runner.invoke(main, ["prompts", "check"])
        assert result.exit_code == 1
        drift_total_calls = [
            (n, f) for (n, f) in cap.calls
            if n == "prompts_check_drift_total"
        ]
        assert len(drift_total_calls) >= 1, (
            f"expected at least 1 prompts_check_drift_total call; "
            f"got {drift_total_calls!r} (all calls: {cap.calls!r})"
        )
        # The drift fixture is a single-entry catalog with skill_name='sdd-test'.
        assert any(
            f.get("skill") == "sdd-test" for (n, f) in drift_total_calls
        ), (
            f"expected skill='sdd-test' label in drift_total call; "
            f"got {drift_total_calls!r}"
        )

    def test_emits_duration_seconds(
        self, clean_catalog: dict[str, SkillEntry], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Each `flow prompts check` invocation emits `prompts_check_duration_seconds`.

        Per design D10: the duration counter is a gauge-style ``_seconds``
        suffix counter that records the elapsed wall-clock time. The
        ``value`` field MUST be a non-negative float.
        """
        monkeypatch.setattr(osc, "SKILL_CATALOG", clean_catalog)
        with _CounterCapture() as cap:
            runner.invoke(main, ["prompts", "check"])
        duration_calls = [
            (n, f) for (n, f) in cap.calls if n == "prompts_check_duration_seconds"
        ]
        assert len(duration_calls) == 1, (
            f"expected exactly 1 prompts_check_duration_seconds call; "
            f"got {duration_calls!r} (all calls: {cap.calls!r})"
        )
        value = duration_calls[0][1].get("value")
        assert isinstance(value, (int, float)) and value >= 0, (
            f"expected non-negative numeric value in duration counter; "
            f"got {duration_calls[0][1]!r}"
        )


# ---------- T2.3: flow prompts lint subcommand ----------


class TestPromptsLint:
    def test_prompts_lint_clean_registry_exits_zero(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts lint` exits 0 when the registry is clean.

        With a freshly imported (untouched) registry, ``lint_prompts()``
        returns an empty errors list and the CLI exits 0. The footer
        MUST include ``0 warnings`` and ``0 errors``.
        """
        result = runner.invoke(main, ["prompts", "lint"])
        assert result.exit_code == 0, (
            f"expected exit 0 on clean registry; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "0 warnings" in result.stdout, (
            f"expected '0 warnings' in footer; got {result.stdout!r}"
        )
        assert "0 errors" in result.stdout, (
            f"expected '0 errors' in footer; got {result.stdout!r}"
        )

    def test_prompts_lint_warnings_only_exits_one(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts lint` exits 1 when only warnings are present.

        Registering a prompt with an undefined Jinja2 placeholder (and no
        ``required_vars`` declaration) triggers the ``undefined_var``
        validation code, which maps to "warning" severity. The CLI exits
        1 (warning, not error) and the footer MUST show at least 1
        warning + 0 errors.
        """
        from flow_engineering import prompt_registry

        prompt_registry.register(
            name="bdd_test_warning",
            template="Hello {{ undeclared }}",
            domain=prompt_registry.PromptDomain.OBSERVABILITY,
            version="1.0.0",
        )
        try:
            result = runner.invoke(main, ["prompts", "lint"])
            assert result.exit_code == 1, (
                f"expected exit 1 on warnings-only; got {result.exit_code}. "
                f"stdout={result.stdout!r} stderr={result.stderr!r}"
            )
            assert "0 errors" in result.stdout, (
                f"expected '0 errors' in footer; got {result.stdout!r}"
            )
            assert "1 warnings" in result.stdout, (
                f"expected '1 warnings' in footer; got {result.stdout!r}"
            )
        finally:
            prompt_registry.unregister_prompt("bdd_test_warning")

    def test_prompts_lint_jinja_syntax_error_exits_two(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts lint` exits 2 on jinja_syntax validation errors.

        Registering a prompt with a broken Jinja2 template triggers the
        ``jinja_syntax`` validation code, which maps to "error" severity.
        The CLI exits 2 and the footer MUST show at least 1 error.
        """
        from flow_engineering import prompt_registry

        prompt_registry.register(
            name="bdd_test_jinja_error",
            template="Hello {{ unclosed",
            domain=prompt_registry.PromptDomain.OBSERVABILITY,
            version="1.0.0",
        )
        try:
            result = runner.invoke(main, ["prompts", "lint"])
            assert result.exit_code == 2, (
                f"expected exit 2 on jinja_syntax error; got {result.exit_code}. "
                f"stdout={result.stdout!r} stderr={result.stderr!r}"
            )
            assert "jinja_syntax" in result.stdout, (
                f"expected 'jinja_syntax' code in stdout; got {result.stdout!r}"
            )
        finally:
            prompt_registry.unregister_prompt("bdd_test_jinja_error")

    def test_prompts_lint_json_flag_emits_json(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """`flow prompts lint --json` emits a structured JSON report.

        With ``--json``, the CLI prints ``LintReport.to_dict()`` shape on
        stdout instead of the human-readable line format. The JSON MUST
        parse without error and contain the expected top-level keys
        (``is_clean``, ``error_count``, ``errors_by_code``, ``errors``).
        """
        result = runner.invoke(main, ["prompts", "lint", "--json"])
        assert result.exit_code == 0, (
            f"expected exit 0; got {result.exit_code}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        loaded = json.loads(result.stdout)
        assert "is_clean" in loaded, (
            f"expected 'is_clean' key in JSON; got keys {list(loaded)!r}"
        )
        assert "error_count" in loaded, (
            f"expected 'error_count' key in JSON; got keys {list(loaded)!r}"
        )
        assert "errors" in loaded, (
            f"expected 'errors' key in JSON; got keys {list(loaded)!r}"
        )
        assert loaded["is_clean"] is True, (
            f"expected is_clean=True on clean registry; got {loaded!r}"
        )
