"""Unit tests for workspace health rendering (text + JSON).

Manual smoke (NOT pytest): (1) fetch_workspace_health(Path('C:/dev/proyects')) returns valid envelope; (2) repeat for byte-identical output; (3) grep -n 'generated_at|timestamp|run_at' src/flow_engineering/health*.py returns 0 hits.
"""

from __future__ import annotations

from io import StringIO
from typing import Any

from rich.console import Console


def _sample_envelope() -> dict[str, Any]:
    return {
        "version": "1",
        "root": "/tmp/workspace",
        "projects": [
            {"name": "alpha", "path": "/tmp/workspace/alpha", "stack": "Python", "verdict": "HEALTHY", "triggers": [], "recommendations": [], "suppressed": []},
            {"name": "bravo", "path": "/tmp/workspace/bravo", "stack": "Node", "verdict": "NEEDS-ATTENTION", "triggers": ["R6"], "recommendations": ["Add README"], "suppressed": []},
            {"name": "charlie", "path": "/tmp/workspace/charlie", "stack": "Python", "verdict": "CRITICAL", "triggers": ["R6", "R7", "R8"], "recommendations": [], "suppressed": []},
        ],
        "totals": {"healthy": 1, "attention": 1, "critical": 1},
    }


def test_render_text_empty_envelope_returns_sentinel() -> None:
    from flow_engineering.health_render import render_workspace_health_text

    envelope = {"version": "1", "root": "/tmp", "projects": [], "totals": {"healthy": 0, "attention": 0, "critical": 0}}
    assert render_workspace_health_text(envelope) == "(no projects to report)"


def test_render_text_mixed_verdicts_with_columns_and_rows() -> None:
    from flow_engineering.health_render import render_workspace_health_text

    output = render_workspace_health_text(_sample_envelope(), console=Console(no_color=True, file=StringIO(), width=120))

    for expected in ("project", "path", "verdict", "triggers", "alpha", "bravo", "charlie", "HEALTHY", "NEEDS-ATTENTION", "CRITICAL"):
        assert expected in output, f"missing {expected!r}"


def test_render_text_no_color_strips_ansi() -> None:
    from flow_engineering.health_render import render_workspace_health_text

    output = render_workspace_health_text(_sample_envelope(), console=Console(no_color=True, file=StringIO(), width=120))
    assert "\x1b[" not in output


def test_render_text_ascii_ellipsis_no_unicode_ellipsis() -> None:
    from flow_engineering.health_render import render_workspace_health_text

    envelope = _sample_envelope()
    envelope["projects"][0]["path"] = "/tmp/" + "very-long-segment/" * 10
    output = render_workspace_health_text(envelope, console=Console(no_color=True, file=StringIO(), width=120))

    assert "..." in output
    assert "\u2026" not in output


def test_render_text_custom_console_seam_returns_captured_string() -> None:
    from flow_engineering.health_render import render_workspace_health_text

    buffer = StringIO()
    output = render_workspace_health_text(_sample_envelope(), console=Console(no_color=True, file=buffer, width=120))

    assert output == buffer.getvalue()
    assert "alpha" in buffer.getvalue()


def test_health_py_has_no_rich_import_srp_lock() -> None:
    import inspect

    import flow_engineering.health as health_mod

    assert "from rich" not in inspect.getsource(health_mod)


def test_render_json_byte_identical_no_temporal() -> None:
    from flow_engineering.health_render import render_workspace_health_json
    out1 = render_workspace_health_json(_sample_envelope())
    out2 = render_workspace_health_json(_sample_envelope())
    assert out1 == out2
    assert "generated_at" not in out1
