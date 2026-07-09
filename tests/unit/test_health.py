"""Unit tests for ``flow_engineering.health``.

Covers:
- REQ-WORKSPACE-HEALTH-VERDICT-MATH -- pure threshold function
  (``TestCategorizeVerdict``: 5 boundary cases).
- REQ-WORKSPACE-HEALTH-R9-COMMITTED-TOOLING -- ``git ls-files`` detector
  (``TestDetectCommittedToolingDirs``: 6 cases with real git on
  ``tmp_path``).

The implementations live in a NEW module ``src/flow_engineering/health.py``
(library-first; introduced by ``workspace-health-advisor`` change).

This file intentionally covers ONLY the verdict math primitives + the
R9 detector primitives for PR2 (sub-batches B-verdict-only + B-R9). The
recommendation copy, the summary builder, the filter, the envelope
composer, and the Rich renderer land in later sub-batches
(PR2/C and PR3/PR4).
"""

from __future__ import annotations

from pathlib import Path

from tests.unit._workspace_fixtures import (
    _init_git_with_files,
    make_project,
)

# ============================================================================
# T-B.1 RED -- pure verdict math.
# ============================================================================


class TestCategorizeVerdict:
    """REQ-WORKSPACE-HEALTH-VERDICT-MATH: 0=HEALTHY, 1-2=NEEDS-ATTENTION, 3+=CRITICAL.

    The function is a pure threshold mapping with NO I/O and NO time-dependent
    state; every boundary count is exercised (0/1/2/3/4).
    """

    def test_zero_triggers_is_healthy(self) -> None:
        from flow_engineering.health import _categorize_verdict

        assert _categorize_verdict([]) == "HEALTHY"

    def test_one_trigger_is_needs_attention(self) -> None:
        from flow_engineering.health import _categorize_verdict

        assert _categorize_verdict(["R6"]) == "NEEDS-ATTENTION"

    def test_two_triggers_is_needs_attention(self) -> None:
        from flow_engineering.health import _categorize_verdict

        assert _categorize_verdict(["R6", "R7"]) == "NEEDS-ATTENTION"

    def test_three_triggers_is_critical(self) -> None:
        from flow_engineering.health import _categorize_verdict

        assert _categorize_verdict(["R6", "R7", "R8"]) == "CRITICAL"

    def test_four_triggers_is_critical(self) -> None:
        from flow_engineering.health import _categorize_verdict

        assert _categorize_verdict(["R6", "R7", "R8", "R9"]) == "CRITICAL"


# ============================================================================
# T-B.2 RED -- R9 detector (REQ-WORKSPACE-HEALTH-R9-COMMITTED-TOOLING).
# ============================================================================
#
# Real-git-on-tmp_path pattern: every test exercises the actual
# ``git ls-files`` subprocess via ``_init_git_with_files`` so the
# detector runs end-to-end against real git (no mocking). The
# graceful-fallback paths (no git / corrupt .git) still rely on real
# git because the detector's swallow-catch is the SAME code path that
# handles ``git not installed``.


class TestDetectCommittedToolingDirs:
    """REQ-WORKSPACE-HEALTH-R9-COMMITTED-TOOLING: detect git-tracked tooling dirs.

    Pattern constants are HARD-CODED Python + Node tuples in ``health.py``;
    per-pattern hits return ``"{pattern} ({count} files)"`` strings. Empty
    list on non-git, corrupt ``.git/``, or no matching patterns.
    """

    def test_clean_project_returns_empty_list(self, tmp_path: Path) -> None:
        """A real git repo with NO tooling patterns tracked → ``[]``.

        Sanity anchor for the detector: when nothing matches, the result
        must be a (possibly empty) list, not None and not a partial
        subset. The ``test_clean_project`` setup mirrors what a freshly
        initialized Python project looks like in the real world.
        """
        from flow_engineering.health import _detect_committed_tooling_dirs

        project = make_project(tmp_path, "clean-py")
        _init_git_with_files(
            project,
            {
                "src/main.py": "print('hi')\n",
                "README.md": "# clean\n",
                "pyproject.toml": '[project]\nname = "x"\n',
            },
        )

        result = _detect_committed_tooling_dirs(project)

        assert result == []

    def test_python_venv_triggers_with_venv(self, tmp_path: Path) -> None:
        """A real git repo with ``.venv/`` tracked → R9 triggered, ``.venv/`` listed.

        Mirrors spec scenario "``.venv/`` tracked means R9 is triggered
        with ``.venv/`` listed". The exact count of files in the hit
        string is asserted to exercise the per-pattern counter.
        """
        from flow_engineering.health import _detect_committed_tooling_dirs

        project = make_project(tmp_path, "py-venv")
        _init_git_with_files(
            project,
            {
                ".venv/lib/python3.12/site-packages/foo.py": "x = 1\n",
                "src/main.py": "print('hi')\n",
            },
        )

        result = _detect_committed_tooling_dirs(project)

        assert len(result) == 1
        assert result[0].startswith(".venv/")
        assert "(1 files)" in result[0]

    def test_node_modules_triggers_with_node_modules(self, tmp_path: Path) -> None:
        """A real git repo with ``node_modules/`` tracked → R9 triggered, listed.

        Mirrors spec scenario "``node_modules/`` tracked means R9 is
        triggered with ``node_modules/`` listed". A pure-Node fixture
        (no Python signals) ensures the Node pattern tuple is exercised.
        """
        from flow_engineering.health import _detect_committed_tooling_dirs

        project = make_project(tmp_path, "node-mod")
        _init_git_with_files(
            project,
            {
                "node_modules/express/index.js": "module.exports = {};\n",
                "package.json": '{"name": "fixture"}',
            },
        )

        result = _detect_committed_tooling_dirs(project)

        assert len(result) == 1
        assert result[0].startswith("node_modules/")
        assert "(1 files)" in result[0]

    def test_mixed_python_and_node_triggers_both(self, tmp_path: Path) -> None:
        """A real git repo with BOTH Python + Node tooling tracked → both listed.

        Exercises the union of the two pattern tuples: the detector
        walks both lists and emits a hit per matching pattern.
        """
        from flow_engineering.health import _detect_committed_tooling_dirs

        project = make_project(tmp_path, "polyglot")
        _init_git_with_files(
            project,
            {
                ".venv/lib/foo.py": "x\n",
                "node_modules/express/index.js": "y\n",
                "src/main.py": "z\n",
            },
        )

        result = _detect_committed_tooling_dirs(project)

        prefixes = [line.split(" ")[0] for line in result]
        assert ".venv/" in prefixes
        assert "node_modules/" in prefixes

    def test_non_git_project_returns_empty_list(self, tmp_path: Path) -> None:
        """A project WITHOUT ``.git/`` → ``[]`` and NO subprocess invoked.

        Mirrors spec scenario "R9 on a non-git project does not crash
        and is NOT triggered (edge case)". The early-return guard
        short-circuits before any ``git ls-files`` call.
        """
        from flow_engineering.health import _detect_committed_tooling_dirs

        project = make_project(tmp_path, "no-git")
        # Deliberately NO _init_git_with_files call. Files exist on
        # disk but the project is not a git repository.
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")

        result = _detect_committed_tooling_dirs(project)

        assert result == []

    def test_corrupt_git_dir_returns_empty_list_gracefully(self, tmp_path: Path) -> None:
        """A project with a fake ``.git/`` dir (corrupt) → ``[]`` with no crash.

        Mirrors spec scenario "R9 on a corrupt .git/ directory fails
        gracefully". The fake ``.git/`` directory (created manually, not
        via ``git init``) causes ``git ls-files`` to fail with
        non-zero returncode; the detector swallows the failure.
        """
        from flow_engineering.health import _detect_committed_tooling_dirs

        project = make_project(tmp_path, "corrupt-git")
        # Manually create an empty ``.git/`` directory — NOT a real git
        # repository. ``git ls-files`` will fail with rc != 0.
        (project / ".git").mkdir()
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")

        result = _detect_committed_tooling_dirs(project)

        assert result == []


# ============================================================================
# T-C.1 RED -- per-project record builder (REQ-WORKSPACE-HEALTH-SURFACE).
# ============================================================================


class TestSummarizeProjectHealth:
    """REQ-WORKSPACE-HEALTH-SURFACE: per-project v1 record builder.

    The record shape is locked at design §5.3:
    ``{name, path, stack, verdict, triggers[], recommendations[],
    suppressed[]}``. Stack guards are applied: R7 suppressed for
    ``{"Nix", "Unknown"}``; R8 suppressed outside ``{Python, Go, Rust}``.
    R9 has no stack guard (any stack can have committed tooling dirs).
    """

    def test_python_project_with_no_triggers(self) -> None:
        """All 4 rules satisfied (README + tests + openspec + no tooling) → HEALTHY."""
        from flow_engineering.health import summarize_project_health

        markers = {
            "name": "py-clean",
            "path": "/tmp/py-clean",
            "stack": "Python",
            "has_readme": True,
            "has_pytest_config": True,
            "has_openspec": True,
        }

        record = summarize_project_health(markers, tooling_hits=[])

        assert record["verdict"] == "HEALTHY"
        assert record["triggers"] == []
        assert record["recommendations"] == []
        assert record["suppressed"] == []

    def test_python_project_with_r7_and_r8_triggered(self) -> None:
        """Python project missing pytest + openspec → 2 triggers + 2 recommendations.

        Verdict = ``NEEDS-ATTENTION`` (2 triggers < 3 critical threshold).
        The recommendations list contains one copy per triggered rule.
        """
        from flow_engineering.health import summarize_project_health

        markers = {
            "name": "py-bare",
            "path": "/tmp/py-bare",
            "stack": "Python",
            "has_readme": True,
            "has_pytest_config": False,
            "has_openspec": False,
        }

        record = summarize_project_health(markers, tooling_hits=[])

        assert record["verdict"] == "NEEDS-ATTENTION"
        assert "R7" in record["triggers"]
        assert "R8" in record["triggers"]
        assert len(record["recommendations"]) == 2
        assert record["suppressed"] == []

    def test_nix_project_suppresses_r7_and_r8(self) -> None:
        """Nix stack suppresses R7 + R8 even when infra missing → HEALTHY."""
        from flow_engineering.health import summarize_project_health

        markers = {
            "name": "nix-proj",
            "path": "/tmp/nix-proj",
            "stack": "Nix",
            "has_readme": True,
            "has_pytest_config": False,
            "has_openspec": False,
        }

        record = summarize_project_health(markers, tooling_hits=[])

        assert record["verdict"] == "HEALTHY"
        assert record["triggers"] == []
        assert "R7" in record["suppressed"]
        assert "R8" in record["suppressed"]
        # Suppressed rules produce NO recommendations
        assert record["recommendations"] == []

    def test_recommendations_only_for_triggered_rules(self) -> None:
        """Only triggered (non-suppressed) rules produce recommendations.

        An R6-only project has 1 trigger and 1 recommendation; R7/R8/R9
        are NOT in the recommendations list even though they're
        "defined" — they're only emitted when triggered.
        """
        from flow_engineering.health import summarize_project_health

        markers = {
            "name": "py-no-readme",
            "path": "/tmp/py-no-readme",
            "stack": "Python",
            "has_readme": False,
            "has_pytest_config": True,
            "has_openspec": True,
        }

        record = summarize_project_health(markers, tooling_hits=[])

        assert record["triggers"] == ["R6"]
        assert len(record["recommendations"]) == 1
        assert "README" in record["recommendations"][0]


# ============================================================================
# T-C.2 RED -- output-only filter (REQ-WORKSPACE-HEALTH-ENVELOPE).
# ============================================================================


class TestFilterHealthByRules:
    """REQ-WORKSPACE-HEALTH-ENVELOPE: filter reasons by rule name.

    Operates on a list of per-project v1 records; filters each
    project's ``triggers[]`` + ``recommendations[]`` to the named
    rule set. The verdict is recomputed from the filtered triggers
    (per REQ-WORKSPACE-HEALTH-VERDICT-MATH).
    """

    def test_filter_r9_only_keeps_r9_triggers(self) -> None:
        """``--filter R9`` retains only R9 triggers per project.

        A project with R6 only has its R6 trigger dropped (and
        recommendation); a project with R9 only retains R9; a
        project with both retains only R9.
        """
        from flow_engineering.health import filter_health_by_rules

        projects = [
            {
                "name": "a",
                "path": "/tmp/a",
                "stack": "Python",
                "verdict": "NEEDS-ATTENTION",
                "triggers": ["R6"],
                "recommendations": ["Add a README"],
                "suppressed": [],
            },
            {
                "name": "b",
                "path": "/tmp/b",
                "stack": "Python",
                "verdict": "NEEDS-ATTENTION",
                "triggers": ["R9"],
                "recommendations": ["Untrack tooling dirs"],
                "suppressed": [],
            },
            {
                "name": "c",
                "path": "/tmp/c",
                "stack": "Python",
                "verdict": "NEEDS-ATTENTION",
                "triggers": ["R6", "R9"],
                "recommendations": ["Add a README", "Untrack tooling dirs"],
                "suppressed": [],
            },
        ]

        filtered = filter_health_by_rules(projects, ["R9"])

        by_name = {p["name"]: p for p in filtered}
        # a: R6 filtered out → empty triggers → HEALTHY
        assert by_name["a"]["triggers"] == []
        assert by_name["a"]["recommendations"] == []
        assert by_name["a"]["verdict"] == "HEALTHY"
        # b: R9 retained
        assert by_name["b"]["triggers"] == ["R9"]
        assert by_name["b"]["recommendations"] == ["Untrack tooling dirs"]
        # c: R6 dropped, R9 retained
        assert by_name["c"]["triggers"] == ["R9"]
        assert by_name["c"]["recommendations"] == ["Untrack tooling dirs"]

    def test_unknown_filter_token_keeps_all(self) -> None:
        """An unknown rule token (e.g. ``R99``) is silently ignored.

        The filter set is empty after the unknown token is dropped,
        so the filter has no effect — all triggers + recommendations
        remain. This matches the lenient interpretation: the health
        envelope is additive, and stale ``R10``-style tokens (not yet
        defined) MUST NOT break the filter.
        """
        from flow_engineering.health import filter_health_by_rules

        projects = [
            {
                "name": "a",
                "path": "/tmp/a",
                "stack": "Python",
                "verdict": "NEEDS-ATTENTION",
                "triggers": ["R6", "R7"],
                "recommendations": ["r6 rec", "r7 rec"],
                "suppressed": [],
            },
        ]

        filtered = filter_health_by_rules(projects, ["R99"])

        assert filtered[0]["triggers"] == ["R6", "R7"]
        assert filtered[0]["recommendations"] == ["r6 rec", "r7 rec"]


# ============================================================================
# T-C.3 RED -- recommendation copy lock (REQ-WORKSPACE-HEALTH-READ-ONLY).
# ============================================================================


class TestRecommendationLock:
    """REQ-WORKSPACE-HEALTH-READ-ONLY: recommendation copy grep audit.

    The recommendation strings MUST reference ONLY the existing
    ``flow workspace {fix, archive, restore, new-project}`` verbs
    + plain English. Forbidden tokens (``rm -rf``, ``git rm -r
    --cached``, ``--force``) MUST NOT appear in the output of
    ``_recommendations_for``.

    These tests grep the entire recommendation registry across
    every stack so a future copy change that introduces a
    forbidden token fails the build (regression lint).
    """

    def test_no_rm_rf_in_recommendations(self) -> None:
        """``rm -rf`` MUST NOT appear in any recommendation string."""
        from flow_engineering.health import _recommendations_for

        # Exercise every rule combination across every supported stack
        # to ensure the grep catches any future regression.
        for stack in ("Python", "Go", "Rust", "Node", "Nix", "Unknown"):
            for triggers in (
                ["R6"],
                ["R7"],
                ["R8"],
                ["R9"],
                ["R6", "R7", "R8", "R9"],
            ):
                recs = _recommendations_for(triggers, stack)
                for rec in recs:
                    assert "rm -rf" not in rec, f"forbidden token in {stack} {triggers}: {rec!r}"

    def test_no_git_rm_r_cached_in_recommendations(self) -> None:
        """``git rm -r --cached`` MUST NOT appear in any recommendation string.

        Per the PR2 lock (per the user prompt), the recommendation
        copy is locked to ``flow workspace`` verbs + plain English;
        raw git-mutation advice is deferred to a future change if
        operator demand surfaces.
        """
        from flow_engineering.health import _recommendations_for

        for stack in ("Python", "Go", "Rust", "Node", "Nix", "Unknown"):
            for triggers in (
                ["R6"],
                ["R7"],
                ["R8"],
                ["R9"],
                ["R6", "R7", "R8", "R9"],
            ):
                recs = _recommendations_for(triggers, stack)
                for rec in recs:
                    assert "git rm -r --cached" not in rec, (
                        f"forbidden token in {stack} {triggers}: {rec!r}"
                    )
                    assert "git rm " not in rec, f"forbidden token in {stack} {triggers}: {rec!r}"

    def test_all_recommendations_reference_flow_workspace_verbs(self) -> None:
        """Every recommendation string MUST mention ``flow workspace``."""
        from flow_engineering.health import _recommendations_for

        for stack in ("Python", "Go", "Rust", "Node", "Nix", "Unknown"):
            for triggers in (
                ["R6"],
                ["R7"],
                ["R8"],
                ["R9"],
                ["R6", "R7", "R8", "R9"],
            ):
                recs = _recommendations_for(triggers, stack)
                for rec in recs:
                    assert "flow workspace" in rec, (
                        f"missing flow workspace verb in {stack} {triggers}: {rec!r}"
                    )


# ============================================================================
# T-PR3 WU3.1 -- workspace-wide health v1 envelope shape.
# ============================================================================


class TestFetchWorkspaceHealthEnvelopeShape:
    """WU3.1: locked v1 envelope keys in fixed order, no temporal fields."""

    def test_keys_in_fixed_order(self, tmp_path: Path) -> None:
        from flow_engineering.health import fetch_workspace_health

        envelope = fetch_workspace_health(tmp_path)

        assert list(envelope.keys()) == ["version", "root", "projects", "totals"]
        assert envelope["version"] == "1"
        assert "generated_at" not in envelope
        assert "timestamp" not in envelope
        assert "run_at" not in envelope

    def test_missing_root_raises(self, tmp_path: Path) -> None:
        import pytest

        from flow_engineering.health import fetch_workspace_health

        with pytest.raises(FileNotFoundError, match="projects root not found"):
            fetch_workspace_health(tmp_path / "missing")


# ============================================================================
# T-PR3 WU3.2 -- iterate projects + per-project record building.
# ============================================================================


def _healthy_python(parent: Path, name: str) -> Path:
    from tests.unit._workspace_fixtures import (
        add_openspec,
        add_pytest_ini,
        add_readme,
        make_python_project,
    )

    project = make_python_project(parent, name, git=False, tests=False, openspec=False)
    add_readme(project)
    add_pytest_ini(project)
    add_openspec(project)
    return project


class TestFetchWorkspaceHealthIteration:
    """WU3.2: enumerate projects under root + build per-project records."""

    def test_iter_subdirs_excludes_dot_prefix(self, tmp_path: Path) -> None:
        from flow_engineering.health import _iter_project_subdirs

        _healthy_python(tmp_path, "alpha")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".pytest_cache").mkdir()
        _healthy_python(tmp_path, "bravo")

        assert sorted(p.name for p in _iter_project_subdirs(tmp_path)) == ["alpha", "bravo"]

    def test_records_in_name_order_with_v1_shape_and_distinct_verdicts(
        self, tmp_path: Path
    ) -> None:
        from flow_engineering.health import fetch_workspace_health
        from tests.unit._workspace_fixtures import (
            add_readme,
            make_node_project,
            make_python_project,
        )

        _healthy_python(tmp_path, "alpha")
        needs = make_node_project(tmp_path, "bravo", git=False, tests=False)
        add_readme(needs)
        make_python_project(tmp_path, "charlie", git=False, tests=False, openspec=False)

        envelope = fetch_workspace_health(tmp_path)
        projects = envelope["projects"]

        assert [p["name"] for p in projects] == ["alpha", "bravo", "charlie"]
        assert set(projects[0]) == {
            "name",
            "path",
            "stack",
            "verdict",
            "triggers",
            "recommendations",
            "suppressed",
        }
        assert {p["name"]: p["verdict"] for p in projects} == {
            "alpha": "HEALTHY",
            "bravo": "NEEDS-ATTENTION",
            "charlie": "CRITICAL",
        }

    def test_empty_root_returns_zero_projects(self, tmp_path: Path) -> None:
        from flow_engineering.health import fetch_workspace_health

        envelope = fetch_workspace_health(tmp_path)

        assert envelope["projects"] == []
        assert envelope["totals"] == {"healthy": 0, "attention": 0, "critical": 0}


# ============================================================================
# T-PR3 WU3.3 -- pure _compute_totals helper.
# ============================================================================


class TestComputeTotals:
    """WU3.3: pure verdict-distribution tally, no I/O."""

    def test_empty(self) -> None:
        from flow_engineering.health import _compute_totals

        assert _compute_totals([]) == {"healthy": 0, "attention": 0, "critical": 0}

    def test_mixed(self) -> None:
        from flow_engineering.health import _compute_totals

        records = [
            {"verdict": "HEALTHY"},
            {"verdict": "NEEDS-ATTENTION"},
            {"verdict": "NEEDS-ATTENTION"},
            {"verdict": "CRITICAL"},
            {"verdict": "HEALTHY"},
        ]
        assert _compute_totals(records) == {"healthy": 2, "attention": 2, "critical": 1}

    def test_does_not_mutate_input(self) -> None:
        from copy import deepcopy

        from flow_engineering.health import _compute_totals

        records = [{"verdict": "HEALTHY"}, {"verdict": "CRITICAL"}]
        original = deepcopy(records)
        _compute_totals(records)
        assert records == original


# ============================================================================
# T-PR3 WU3.4 -- byte-determinism invariant (Constitution Article IV).
# ============================================================================


class TestFetchWorkspaceHealthByteDeterminism:
    """WU3.4: two consecutive calls on unchanged root MUST be byte-identical.

    Guards against ``datetime.now()``, ``time.time()``, ``os.urandom``,
    file-mtime reads, or any other temporal / non-deterministic state.
    """

    def test_two_invocations_equal_with_time_sleep(self, tmp_path: Path) -> None:
        import time

        from flow_engineering.health import fetch_workspace_health

        _healthy_python(tmp_path, "alpha")

        first = fetch_workspace_health(tmp_path)
        time.sleep(1)
        second = fetch_workspace_health(tmp_path)

        assert first == second
        assert first["root"] == str(tmp_path.resolve())

    def test_health_module_source_has_no_temporal_primitives(self) -> None:
        import inspect

        import flow_engineering.health as health_mod

        source = inspect.getsource(health_mod)
        for forbidden in ("datetime.now", "time.time", "os.urandom"):
            assert forbidden not in source
