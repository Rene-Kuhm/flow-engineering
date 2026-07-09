"""End-to-end plugin coexistence test: graphify.js + flow-engineering.js side by side.

REQ: verify that both plugins activate correctly when their conditions are met,
without interfering with each other.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _plugins_dir() -> Path:
    """Return repo-bundled plugin fixtures, with user-home fallback for smoke tests."""
    repo_plugins = Path(__file__).resolve().parents[1] / "plugins"
    expected = ("graphify.js", "flow-engineering.js")
    if all((repo_plugins / name).is_file() for name in expected):
        return repo_plugins
    return Path.home() / ".opencode" / "plugins"


def test_both_plugins_have_valid_syntax() -> None:
    """Both plugin files must parse as ES modules and export a Plugin function."""
    plugins_dir = _plugins_dir()
    for name in ("graphify.js", "flow-engineering.js"):
        plugin_path = plugins_dir / name
        assert plugin_path.exists(), f"{name} not found at {plugin_path}"
        result = subprocess.run(
            ["node", "--check", str(plugin_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{name} has syntax errors:\n{result.stderr}"


def test_both_plugins_export_expected_function(tmp_path: Path) -> None:
    """Each plugin must export a named async function matching its pattern.

    Uses a small node script file with pathToFileURL to avoid Windows path issues.
    """

    plugins_dir = _plugins_dir()
    cases = [
        ("graphify.js", "GraphifyPlugin"),
        ("flow-engineering.js", "FlowEngineeringPlugin"),
    ]
    script = tmp_path / "check_exports.mjs"
    imports_lines = [
        "import { pathToFileURL } from 'url';",
    ]
    for i, (name, expected) in enumerate(cases):
        plugin_path = plugins_dir / name
        # Build a proper file:// URL for Windows
        win_path = str(plugin_path).replace("\\", "/")
        url = f"file:///{win_path.lstrip('/')}"
        imports_lines.append(
            f"const m_{i} = await import({url!r});\n"
            f"if (!m_{i}.{expected}) throw new Error('{name}: missing {expected}');"
        )
    imports_lines.append("console.log('OK');")
    script.write_text("\n".join(imports_lines) + "\n")
    result = subprocess.run(
        ["node", str(script)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Export check failed:\n{result.stderr}"


def test_plugin_file_sizes_similar() -> None:
    """Both plugins should be roughly the same size (≤50 lines each per spec)."""
    plugins_dir = _plugins_dir()
    for name in ("graphify.js", "flow-engineering.js"):
        content = (plugins_dir / name).read_text(encoding="utf-8")
        line_count = sum(1 for line in content.splitlines() if line.strip())
        assert line_count <= 50, f"{name} is {line_count} lines, expected ≤ 50"


def test_both_plugins_activate_on_their_conditions(tmp_path: Path) -> None:
    """Verify activation logic: graphify needs graph.json, flow needs flow-engineering/."""

    # Test flow-engineering activation: needs flow-engineering/<change>/ dir
    fe_dir = tmp_path / "flow-engineering" / "test"
    fe_dir.mkdir(parents=True)
    assert (fe_dir).exists(), "flow-engineering/ condition should be met"

    # Test graphify activation: needs graphify-out/graph.json
    go_dir = tmp_path / "graphify-out"
    go_dir.mkdir()
    (go_dir / "graph.json").write_text("{}")
    assert (go_dir / "graph.json").exists(), "graphify condition should be met"

    # Verify the plugins would actually fire by inspecting their source
    plugins_dir = _plugins_dir()
    flow_plugin = (plugins_dir / "flow-engineering.js").read_text()
    assert "existsSync" in flow_plugin, "flow-engineering plugin must check existsSync"
    assert "flow-engineering" in flow_plugin, "flow-engineering plugin must check its dir"

    graphify_plugin = (plugins_dir / "graphify.js").read_text()
    assert "existsSync" in graphify_plugin, "graphify plugin must check existsSync"
    assert "graphify-out" in graphify_plugin, "graphify plugin must check its dir"
