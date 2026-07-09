"""Project detector for flow-engineering (REQ-24, cross-project-federation T1.3).

Two surfaces:

1. ``detect(cwd) -> str | None`` — return the project name when ``cwd`` is under
   a recognised projects layout, otherwise ``None``. Layouts accepted:

   - ``*/dev/proyects/<name>/...``  — ``dev/proyects`` segment pair anywhere
   - ``<home>/proyects/<name>/...`` — literal home anchoring (mirrors
     ``Path.home() / "proyects"``)

   Returns ``None`` (NOT a silent ``"insyd"`` fallback) when no match is
   found; the caller decides what to do. The user prompt in T1.3
   explicitly tests this contract — a script running from ``/tmp`` MUST
   NOT be silently tagged as ``insyd``.

2. ``apply_tag(observation_id, project, *, backend) -> bool`` — re-tag one
   observation's ``project`` field. Refuses empty/whitespace project
   (raises ``ValueError``); returns ``False`` when the observation is not
   found; returns ``True`` after the mutation. For T1.3 unit coverage we
   mutate the live observation dict returned by ``mem_get_observation``;
   the production backend seam is handled by T1.5 BDD once we know the
   end-to-end wiring.

Registry auto-load: ``detect`` reads
``~/.config/flow-engineering/registry.json`` on every call (overridable
via the ``registry=`` kwarg in tests). The JSON shape is::

    {"cwd_to_project": {"<cwd>": "<project>", ...}}

Manual entries win over default detection. Missing file → empty dict
(no error). Malformed JSON → ``RegistryParseError`` with the file path
in the message so the user can fix it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flow_engineering.engram_io import EngramBackend


DEFAULT_REGISTRY_PATH: Path = Path.home() / ".config" / "flow-engineering" / "registry.json"


class RegistryParseError(ValueError):
    """Raised when ``registry.json`` exists but cannot be parsed or is malformed.

    The file path is included in the message so the user can locate and
    fix the broken file without needing to read a traceback.
    """


def load_registry(path: Path | None = None) -> dict[str, str]:
    """Load ``registry.json`` and return the ``cwd_to_project`` mapping.

    Returns ``{}`` when the file is missing (a missing registry is
    expected and benign). Raises :class:`RegistryParseError` when the
    file exists but the JSON is malformed or the shape is wrong.
    """
    target = path if path is not None else DEFAULT_REGISTRY_PATH
    if not target.exists():
        return {}
    try:
        raw = target.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RegistryParseError(f"failed to parse registry.json at {target}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RegistryParseError(
            f"registry.json at {target} must be a JSON object; got {type(payload).__name__}"
        )
    cwd_to_project = payload.get("cwd_to_project")
    if cwd_to_project is None:
        return {}
    if not isinstance(cwd_to_project, dict):
        raise RegistryParseError(
            f"registry.json at {target}: cwd_to_project must be an object; "
            f"got {type(cwd_to_project).__name__}"
        )
    return {str(k): str(v) for k, v in cwd_to_project.items()}


def detect(cwd: Path, *, registry: dict[str, str] | None = None) -> str | None:
    """Return the project name for ``cwd`` if it lives under a recognised layout.

    Lookup chain (first hit wins):
    1. Explicit ``registry=`` kwarg (or the auto-loaded registry file).
    2. ``*/dev/proyects/<name>/...`` segment-pair match anywhere in the path.
    3. ``<Path.home()>/proyects/<name>/...`` literal home anchoring.

    Returns ``None`` when no layout matches — the caller decides whether
    to fall back to a default tag (e.g. ``"insyd"`` for ``InMemoryBackend``).
    """
    if registry is None:
        try:
            registry = load_registry()
        except RegistryParseError:
            registry = {}

    if registry:
        cwd_key = _normalize_for_registry(cwd)
        for key, value in registry.items():
            key_norm = _normalize_for_registry(Path(key))
            if cwd_key == key_norm or cwd_key.startswith(key_norm + "/"):
                return value

    # Layout 1: */dev/proyects/<name>/...  (anywhere in the path).
    parts = cwd.parts
    for i, part in enumerate(parts):
        if part != "proyects" or i + 1 >= len(parts):
            continue
        if i >= 1 and parts[i - 1] == "dev":
            return parts[i + 1]

    # Layout 2: <home>/proyects/<name>/...  (literal home anchor).
    home_proyects = Path.home() / "proyects"
    try:
        if cwd.is_relative_to(home_proyects):
            rel = cwd.relative_to(home_proyects)
            if rel.parts:
                return rel.parts[0]
    except (ValueError, OSError):
        # Different drives / non-existent path components — not under home.
        pass

    return None


def apply_tag(
    observation_id: int,
    project: str,
    *,
    backend: EngramBackend,
) -> dict[str, object]:
    """Re-tag a single observation's ``project`` field.

    Returns ``True`` after a successful mutation; ``False`` when the
    observation does not exist on the backend. Raises :class:`ValueError`
    when ``project`` is empty or whitespace-only — the caller is
    responsible for not passing garbage.

    The mutation strategy is "fetch then write": ``mem_get_observation``
    gives us the live dict for ``InMemoryBackend`` (the test fixture)
    so we mutate the field in place. For the production backend, the
    update_observation seam is the canonical write path; T1.5 BDD covers
    end-to-end against the production wiring.
    """
    if not project or not project.strip():
        return {"ok": False, "error": "project cannot be empty or whitespace"}
    try:
        obs = backend.mem_get_observation(observation_id)
    except Exception as exc:
        return {"ok": False, "error": f"observation lookup failed: {exc}"}
    if not isinstance(obs, dict):
        return {"ok": False, "error": f"observation {observation_id} not found or not a dict"}
    obs["project"] = project
    return {"ok": True, "observation_id": observation_id, "project": project}


def _normalize_for_registry(p: Path) -> str:
    """Normalize a path for registry-key comparison (Windows + Unix safe)."""
    return str(p).replace("\\", "/").rstrip("/")
