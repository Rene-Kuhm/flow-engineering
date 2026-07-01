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
