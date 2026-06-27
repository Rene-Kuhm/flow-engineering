"""Project-aliases config for flow-engineering (REQ-27, cross-project-federation T1.10).

REQ-27 + design D8: forward-only alias map at
``~/.config/flow-engineering/project-aliases.json`` lets the federated
search resolve ``flow-image-generator-v2`` to ``flow-image-generator-main``
transparently — no destructive mass-backfill required.

Schema (list-of-records, audit-safe):

::

    {
      "version": 1,
      "aliases": [
        {"old": "flow-image-generator-v2",
         "new": "flow-image-generator-main",
         "created_at": "2026-06-26T19:46:07Z"},
        ...
      ]
    }

Public surface:

- ``DEFAULT_ALIASES_PATH`` — ``~/.config/flow-engineering/project-aliases.json``
- ``AliasRecord`` — typed-dict-shaped alias entry (3 required keys).
- ``resolve(name, *, aliases=None) -> str`` — forward alias resolution.
  Identity for non-aliased names. Returns ``name`` unchanged when no
  alias matches.
- ``load_aliases(path=None) -> list[AliasRecord]`` — read from disk.
  Missing file ⇒ ``[]``. Malformed JSON ⇒ :class:`AliasConfigParseError`
  with the file path AND the JSON parser error in the message.
- ``save_aliases(aliases, path=None) -> None`` — atomic write via
  ``tempfile + Path.replace`` so a mid-write crash cannot corrupt the file.
- ``add_alias(old, new, *, path=None) -> dict`` — idempotent append
  (``{"status": "added"|"already_present", "old": ..., "new": ...}``).
  Conflicting rewrite (``old -> different_new``) raises ``ValueError``
  to prevent silent history loss.

The CLI subcommand ``flow projects alias <old> <new>`` calls
``add_alias`` and prints the confirmation. Alias resolution is wired into
``InMemoryBackend.mem_search_federated`` so federated queries transparently
use the canonical name when an alias exists for the queried project.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict


# ---------- Public types ----------


class AliasRecord(TypedDict):
    """One alias record (REQ-27 schema, audit-safe with ``created_at``)."""

    old: str
    new: str
    created_at: str  # ISO 8601 with Z suffix


# ---------- Paths + errors ----------


DEFAULT_ALIASES_PATH: Path = (
    Path.home() / ".config" / "flow-engineering" / "project-aliases.json"
)
"""Canonical path for the alias config (overridable via ``path=`` kwargs)."""


class AliasConfigParseError(ValueError):
    """Raised when ``project-aliases.json`` exists but cannot be parsed.

    The file path is included in the message so the user can locate and
    fix the broken file without needing to read a traceback.
    """


# ---------- Helpers ----------


def _now_iso() -> str:
    """Return UTC now as ISO 8601 with a ``Z`` suffix (audit-safe)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- Public API ----------


def resolve(name: str, *, aliases: list[AliasRecord] | None = None) -> str:
    """Return the canonical name for ``name`` under the alias map.

    Forward-only resolution (``old → new``). Returns ``name`` unchanged
    when no alias matches. Identity for non-aliased names so the
    no-alias-map case is a cheap pass-through.

    When ``aliases`` is ``None``, ``resolve`` does NOT auto-load from
    disk — callers that need on-disk resolution should call
    :func:`load_aliases` explicitly. The default ``aliases=None``
    identity behaviour mirrors the REQ-27 test fixture pattern.
    """
    if not aliases:
        return name
    for record in aliases:
        if record.get("old") == name:
            return record.get("new", name)
    return name


def load_aliases(path: Path | None = None) -> list[AliasRecord]:
    """Load ``project-aliases.json`` and return the list of alias records.

    - Missing file ⇒ ``[]`` (no error; the user gets an empty alias map).
    - Malformed JSON ⇒ :class:`AliasConfigParseError` with the file path
      and the underlying parser error in the message.
    - Top-level shape other than an object ⇒ :class:`AliasConfigParseError`.
    - Missing ``aliases`` key ⇒ ``[]`` (forward-compat for ``{"version": 1}``
      alone).
    """
    target = path if path is not None else DEFAULT_ALIASES_PATH
    if not target.exists():
        return []
    try:
        raw = target.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AliasConfigParseError(
            f"failed to parse project-aliases.json at {target}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise AliasConfigParseError(
            f"project-aliases.json at {target} must be a JSON object; "
            f"got {type(payload).__name__}"
        )
    records = payload.get("aliases", [])
    if records is None:
        return []
    if not isinstance(records, list):
        raise AliasConfigParseError(
            f"project-aliases.json at {target}: 'aliases' must be a list; "
            f"got {type(records).__name__}"
        )
    normalized: list[AliasRecord] = []
    for record in records:
        if not isinstance(record, dict):
            raise AliasConfigParseError(
                f"project-aliases.json at {target}: alias record must be an object; "
                f"got {type(record).__name__}"
            )
        normalized.append(
            {
                "old": str(record.get("old", "")),
                "new": str(record.get("new", "")),
                "created_at": str(record.get("created_at", "")),
            }
        )
    return normalized


def save_aliases(
    aliases: list[AliasRecord], path: Path | None = None
) -> None:
    """Atomically write the alias config to disk.

    Atomic write via ``tempfile.NamedTemporaryFile + Path.replace`` so a
    mid-write crash cannot corrupt the file. The temp file is created
    in the same directory as the target so ``Path.replace`` is
    cross-filesystem safe. The temp file is cleaned up by the context
    manager on normal exit; ``Path.replace`` re-uses the inode on POSIX
    and is a metadata-only swap on Windows.
    """
    target = path if path is not None else DEFAULT_ALIASES_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"version": 1, "aliases": list(aliases)}
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    fd, tmp_path_str = tempfile.mkstemp(
        prefix=".project-aliases-", suffix=".json.tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(serialized)
            fh.flush()
            os.fsync(fh.fileno())
        Path(tmp_path_str).replace(target)
    except Exception:
        # Best-effort cleanup of the temp file on failure.
        try:
            Path(tmp_path_str).unlink()
        except OSError:
            pass
        raise


def add_alias(
    old: str, new: str, *, path: Path | None = None
) -> dict[str, str]:
    """Append a new alias record (idempotent + conflict-safe).

    Behaviour:

    - File missing ⇒ file is created with one record. Returns
      ``{"status": "added", "old": ..., "new": ..., "created_at": ...}``.
    - File present, ``old -> same_new`` ⇒ no-op + returns
      ``{"status": "already_present", "old": ..., "new": ...}``.
    - File present, ``old -> different_new`` ⇒ raises :class:`ValueError`
      with a message naming ``old`` and the EXISTING target so the user
      knows what to do (edit the JSON manually or remove the old record).

    The existing record (when present) is NEVER overwritten — audit history
    is preserved.
    """
    target = path if path is not None else DEFAULT_ALIASES_PATH
    existing = load_aliases(path=target)
    for record in existing:
        if record.get("old") == old:
            existing_new = record.get("new", "")
            if existing_new == new:
                return {
                    "status": "already_present",
                    "old": old,
                    "new": new,
                }
            raise ValueError(
                f"alias for {old} already maps to {existing_new}; "
                f"refusing to overwrite with {new}"
            )
    new_record: AliasRecord = {
        "old": old,
        "new": new,
        "created_at": _now_iso(),
    }
    save_aliases([*existing, new_record], path=target)
    return {
        "status": "added",
        "old": old,
        "new": new,
        "created_at": new_record["created_at"],
    }


__all__ = [
    "AliasRecord",
    "AliasConfigParseError",
    "DEFAULT_ALIASES_PATH",
    "resolve",
    "load_aliases",
    "save_aliases",
    "add_alias",
]
