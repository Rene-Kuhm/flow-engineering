"""Persistent registry for ``flow workspace {fix,archive,archived,restore}`` (Phase 4).

REQ-HYGIENE-REGISTRY-V1: a pydantic v2 schema persisted at
``~/.flow-engineering/registry.json`` with two parallel lists
(``projects[]`` for live projects, ``archived[]`` for retired ones) and a
``version: 1`` discriminator. Atomic write via ``tempfile.mkstemp`` +
``Path.replace`` mirrors the ``project_aliases.save_aliases`` precedent
(``src/flow_engineering/project_aliases.py:164``).

Public surface:

- ``ProjectEntry`` — pydantic model for a live project row.
- ``ArchivedEntry`` — pydantic model for an archived project row.
- ``Registry`` — top-level v1 envelope (version + projects + archived).
- ``RegistryError`` — raised on I/O / parse / schema failures; carries a
  ``user_message`` for the CLI layer to print to stderr.
- ``DEFAULT_REGISTRY_PATH`` — canonical path; **not** re-evaluated on access.
  Use ``registry_path()`` (which always re-evaluates ``Path.home()``) inside
  loaders/savers so test contexts that monkeypatch ``Path.home()`` work.
- ``registry_path()`` — accessor; re-evaluates ``Path.home()`` per call.
- ``load_registry()`` — read + validate; missing file → empty ``Registry``.
- ``save_registry_atomic()`` — atomic write; crash mid-``replace`` leaves
  the prior file intact and removes the temp file.

Read-only consumers (``flow projects ls --json``, ``flow workspace status``)
MUST NOT call ``save_registry_atomic`` — the file is created on first
mutation by ``fix`` or ``archive`` only.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

# ---------- Public models ----------


class ProjectEntry(BaseModel):
    """Registry entry for a live project (mirrors Phase 1 v1 envelope fields).

    Fields align with the read-only ``_detect_project_markers`` output at
    ``src/flow_engineering/cli.py:3137`` plus a ``last_status_check``
    timestamp so the registry can serve as a "last seen alive" audit.
    """

    model_config = ConfigDict(extra="forbid", frozen=False)

    name: str
    path: Path
    has_git: bool
    has_openspec: bool
    has_tests: bool
    has_graphify: bool
    last_status_check: str  # UTC ISO 8601 with Z suffix


class ArchivedEntry(BaseModel):
    """Registry entry for an archived project.

    The archive move is a registry-only operation (no filesystem change).
    ``reason`` defaults to ``"manual archive"`` per locked constraint #10.
    """

    model_config = ConfigDict(extra="forbid", frozen=False)

    name: str
    path: Path
    archived_at: str  # UTC ISO 8601 with Z suffix
    reason: str  # literal "manual archive" when --reason omitted


class Registry(BaseModel):
    """Top-level v1 registry envelope.

    The ``version: Literal[1]`` discriminator lets a future v2 reader detect
    a v1 file and reject (or migrate) it. ``extra="forbid"`` keeps the file
    honest: a stray key fails the load rather than silently passing.
    """

    model_config = ConfigDict(extra="forbid", frozen=False)

    version: Literal[1] = 1
    projects: list[ProjectEntry] = Field(default_factory=list)
    archived: list[ArchivedEntry] = Field(default_factory=list)


# ---------- Errors ----------


class RegistryError(RuntimeError):
    """I/O / parse / schema failures from registry operations.

    The CLI layer prints ``user_message`` to stderr (exit 2) so the user
    sees a clear remediation hint rather than a raw traceback.
    """

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


# ---------- Paths ----------


DEFAULT_REGISTRY_PATH: Path = Path.home() / ".flow-engineering" / "registry.json"
"""Canonical registry path. NOT cached — ``Path.home()`` may differ across
contexts. Use :func:`registry_path` inside loaders/savers so test contexts
that monkeypatch ``Path.home()`` are honored.
"""


def registry_path() -> Path:
    """Return the canonical registry path, re-evaluating ``Path.home()``.

    This is the accessor all load/save code MUST use (not the constant).
    Re-evaluation is required because tests monkeypatch ``Path.home()`` to
    point at ``tmp_path``; if loaders cached the constant at import time
    they would point at the real ``~/.flow-engineering/`` dir.
    """
    return Path.home() / ".flow-engineering" / "registry.json"


# ---------- Helpers ----------


def _serialized_payload(registry: Registry) -> str:
    """Serialize a ``Registry`` to indented JSON with POSIX-style Path fields.

    ``model_dump(mode="json")`` converts ``Path`` instances to strings (POSIX
    form) so the file is portable across machines regardless of host OS.
    """
    return json.dumps(registry.model_dump(mode="json"), ensure_ascii=False, indent=2)


# ---------- Public API ----------


def load_registry(*, path: Path | None = None) -> Registry:
    """Load and validate ``registry.json`` from ``path`` (or default location).

    - Missing file → ``Registry(version=1, projects=[], archived=[])``.
    - Malformed JSON → ``RegistryError`` with the file path in the message.
    - Schema mismatch (``extra="forbid"``) → ``RegistryError``.
    """
    target = path if path is not None else registry_path()
    if not target.exists():
        return Registry()
    try:
        raw = target.read_text(encoding="utf-8")
        payload: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RegistryError(
            f"failed to parse registry at {target}: {exc}. "
            f"Delete or fix the file before retrying."
        ) from exc
    try:
        return Registry.model_validate(payload)
    except ValidationError as exc:
        raise RegistryError(
            f"registry at {target} has invalid schema: {exc}. "
            f"Delete or fix the file before retrying."
        ) from exc


def save_registry_atomic(registry: Registry, *, path: Path | None = None) -> None:
    """Atomically write ``registry`` to ``path`` (or default location).

    Mirrors :func:`flow_engineering.project_aliases.save_aliases`
    (``project_aliases.py:164``). The temp file is created in the same
    parent directory as the target so ``Path.replace`` is cross-filesystem
    safe (atomic on POSIX + Windows when src/dst are on the same FS).
    ``Path.replace`` re-uses the inode on POSIX and is a metadata-only swap
    on Windows; the prior file is intact until the swap lands.

    On any exception (OSError during write/replace, JSON encoding failure)
    the temp file is removed and the exception is re-raised as
    ``RegistryError`` (the caller is the CLI layer; it must see a single
    error type to catch).
    """
    target = path if path is not None else registry_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = _serialized_payload(registry)
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=".registry-", suffix=".json.tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(serialized)
            fh.flush()
            os.fsync(fh.fileno())
        Path(tmp_path_str).replace(target)
    except Exception as exc:
        # Best-effort cleanup of the temp file on failure.
        with contextlib.suppress(OSError):
            Path(tmp_path_str).unlink()
        if isinstance(exc, RegistryError):
            raise
        raise RegistryError(
            f"failed to write registry at {target}: {exc}"
        ) from exc


__all__ = [
    "ArchivedEntry",
    "DEFAULT_REGISTRY_PATH",
    "ProjectEntry",
    "Registry",
    "RegistryError",
    "load_registry",
    "registry_path",
    "save_registry_atomic",
]
