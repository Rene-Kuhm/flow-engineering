"""Unit tests for ``flow_engineering.project_aliases`` (REQ-27).

TDD: written BEFORE the implementation. These MUST fail until the GREEN
commit wires ``src/flow_engineering/project_aliases.py`` with the
list-of-records schema, atomic write, and idempotent ``add_alias``.

Coverage map (REQ-27 scenarios 1-5 at the unit level):

1. ``resolve(name)`` rewrites an aliased name forward (``old → new``)
   and is identity for non-aliased names.
2. ``save_aliases([...])`` writes the file with the schema
   ``{"version": 1, "aliases": [{"old": ..., "new": ..., "created_at": ...}, ...]}``.
3. ``add_alias(old, new)`` is idempotent: same ``old -> new`` is a no-op
   (still 1 record); different ``new`` for the same ``old`` ERRORS
   (no silent history loss).
4. ``load_aliases(path=missing_file)`` returns ``[]`` and is fail-open
   (no exception, no error to caller).
5. ``load_aliases(path=malformed_json)`` raises ``AliasConfigParseError``
   with the file path AND the JSON parser error in the message so the
   user can fix it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flow_engineering import project_aliases as _aliases
from flow_engineering.project_aliases import (
    DEFAULT_ALIASES_PATH,
    AliasConfigParseError,
    add_alias,
    load_aliases,
    resolve,
    save_aliases,
)

# ---------- REQ-27 scenario 1: resolve ----------


class TestResolve:
    """``resolve(name)`` is forward-only alias resolution."""

    def test_resolve_identity_for_non_aliased(self) -> None:
        # ``flow-engineering`` is not in the alias map → returns unchanged.
        aliases = [
            {
                "old": "flow-image-generator-v2",
                "new": "flow-image-generator-main",
                "created_at": "2026-06-26T19:46:07Z",
            }
        ]
        assert resolve("flow-engineering", aliases=aliases) == "flow-engineering"

    def test_resolve_rewrites_aliased_name(self) -> None:
        aliases = [
            {
                "old": "flow-image-generator-v2",
                "new": "flow-image-generator-main",
                "created_at": "2026-06-26T19:46:07Z",
            }
        ]
        assert (
            resolve("flow-image-generator-v2", aliases=aliases)
            == "flow-image-generator-main"
        )

    def test_resolve_empty_alias_list_is_identity(self) -> None:
        assert resolve("anything", aliases=[]) == "anything"

    def test_resolve_first_match_wins(self) -> None:
        # Two aliases share the same ``old`` (shouldn't happen in practice —
        # ``add_alias`` enforces uniqueness — but if a hand-edited file does,
        # the first match wins so behaviour is deterministic).
        aliases = [
            {"old": "x", "new": "first", "created_at": "2026-06-26T00:00:00Z"},
            {"old": "x", "new": "second", "created_at": "2026-06-27T00:00:00Z"},
        ]
        assert resolve("x", aliases=aliases) == "first"

    def test_resolve_default_aliases_kwarg_is_none_for_identity(self) -> None:
        # ``resolve(name)`` with no ``aliases`` kwarg loads from disk; missing
        # file ⇒ empty list ⇒ identity. This guards the "no alias map on disk"
        # path explicitly so callers don't have to provide the kwarg.
        assert resolve("any-name") == "any-name"


# ---------- REQ-27 scenario 2: save writes the file ----------


class TestSave:
    """``save_aliases`` writes the canonical schema via atomic replace."""

    def test_save_writes_schema_with_version_and_aliases(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "project-aliases.json"
        save_aliases(
            [
                {
                    "old": "flow-image-generator-v2",
                    "new": "flow-image-generator-main",
                    "created_at": "2026-06-26T19:46:07Z",
                }
            ],
            path=path,
        )
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["version"] == 1
        assert payload["aliases"] == [
            {
                "old": "flow-image-generator-v2",
                "new": "flow-image-generator-main",
                "created_at": "2026-06-26T19:46:07Z",
            }
        ]

    def test_save_empty_list_writes_empty_aliases_array(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "project-aliases.json"
        save_aliases([], path=path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload == {"version": 1, "aliases": []}

    def test_save_writes_atomically_via_replace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # REQ-27: atomic write via ``tempfile + Path.replace`` so a mid-write
        # crash cannot corrupt the file. The impl uses ``tempfile`` in the
        # same directory and ``Path.replace`` for atomicity; we don't
        # crash-test it here, but we DO assert that the call returns
        # successfully AND the file is fully written (no partial bytes).
        path = tmp_path / "project-aliases.json"
        save_aliases(
            [
                {"old": "a", "new": "b", "created_at": "2026-06-26T19:46:07Z"}
            ],
            path=path,
        )
        # Re-load and assert the full content (no partial writes).
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["version"] == 1
        assert len(payload["aliases"]) == 1


# ---------- REQ-27 scenario 5: malformed JSON fails fast ----------


class TestLoad:
    """``load_aliases`` handles missing, empty, and malformed files."""

    def test_load_missing_file_returns_empty_list(self, tmp_path: Path) -> None:
        # REQ-27: missing file = empty list + counter. No exception.
        result = load_aliases(path=tmp_path / "nonexistent.json")
        assert result == []

    def test_load_malformed_json_raises_with_path_and_error(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "project-aliases.json"
        path.write_text("{ this is not valid json", encoding="utf-8")
        with pytest.raises(AliasConfigParseError) as exc_info:
            load_aliases(path=path)
        msg = str(exc_info.value)
        assert str(path) in msg, (
            f"Expected file path in error message, got: {msg!r}"
        )
        # Parser error message MUST also appear.
        assert any(
            needle in msg.lower()
            for needle in ("expecting", "json", "invalid", "unterminated")
        ), f"Expected JSON parser error in message, got: {msg!r}"

    def test_load_non_object_root_raises_parse_error(
        self, tmp_path: Path
    ) -> None:
        # Schema: top-level MUST be an object; ``[1, 2, 3]`` is valid JSON
        # but not the right shape. The loader MUST refuse rather than
        # silently returning ``[]`` so the user knows to fix the file.
        path = tmp_path / "project-aliases.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(AliasConfigParseError):
            load_aliases(path=path)

    def test_load_missing_aliases_key_treated_as_empty(
        self, tmp_path: Path
    ) -> None:
        # Forward-compat: a file with ``{"version": 1}`` and no ``aliases``
        # key is valid (empty alias map). Loader returns ``[]``.
        path = tmp_path / "project-aliases.json"
        path.write_text(json.dumps({"version": 1}), encoding="utf-8")
        assert load_aliases(path=path) == []

    def test_load_round_trips_save_then_load(self, tmp_path: Path) -> None:
        path = tmp_path / "project-aliases.json"
        original = [
            {
                "old": "flow-image-generator-v2",
                "new": "flow-image-generator-main",
                "created_at": "2026-06-26T19:46:07Z",
            },
            {
                "old": "ecommerce-picomar",
                "new": "ecommerce-picomar-prod",
                "created_at": "2026-06-26T20:00:00Z",
            },
        ]
        save_aliases(original, path=path)
        loaded = load_aliases(path=path)
        assert loaded == original


# ---------- REQ-27 scenarios 3 + 4: add_alias idempotency + conflict ----------


class TestAddAlias:
    """``add_alias`` is idempotent + refuses conflicting rewrites."""

    def test_add_alias_creates_file_when_missing(self, tmp_path: Path) -> None:
        path = tmp_path / "project-aliases.json"
        result = add_alias(
            "flow-image-generator-v2",
            "flow-image-generator-main",
            path=path,
        )
        assert result["status"] == "added"
        assert result["old"] == "flow-image-generator-v2"
        assert result["new"] == "flow-image-generator-main"
        # File now exists with one record.
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["version"] == 1
        assert len(payload["aliases"]) == 1
        assert payload["aliases"][0]["old"] == "flow-image-generator-v2"

    def test_add_alias_idempotent_same_target_noop(self, tmp_path: Path) -> None:
        path = tmp_path / "project-aliases.json"
        add_alias("a", "b", path=path)
        result = add_alias("a", "b", path=path)
        # REQ-27 scenario 4: re-invoking with same args is a no-op +
        # confirmation. The status reports ``already_present``.
        assert result["status"] == "already_present"
        # Only one record in the file (no duplicate row added).
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert len(payload["aliases"]) == 1

    def test_add_alias_conflicting_target_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "project-aliases.json"
        add_alias("a", "b", path=path)
        # REQ-27 scenario 3: re-invoking with the same ``old`` and a
        # DIFFERENT ``new`` MUST error to prevent silent history loss.
        with pytest.raises(ValueError) as exc_info:  # noqa: PT011
            add_alias("a", "DIFFERENT", path=path)
        msg = str(exc_info.value)
        assert "a" in msg
        assert "b" in msg
        # Existing record UNCHANGED (no silent history loss).
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert len(payload["aliases"]) == 1
        assert payload["aliases"][0]["new"] == "b"

    def test_add_alias_sets_created_at_to_now(self, tmp_path: Path) -> None:
        path = tmp_path / "project-aliases.json"
        add_alias("a", "b", path=path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        ts = payload["aliases"][0]["created_at"]
        # ISO 8601 with Z suffix (matches ``observability._now_iso`` style).
        assert "T" in ts
        assert ts.endswith("Z")

    def test_add_alias_appends_to_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "project-aliases.json"
        add_alias("a", "A", path=path)
        add_alias("b", "B", path=path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        olds = sorted(record["old"] for record in payload["aliases"])
        assert olds == ["a", "b"]


# ---------- Defaults + module surface ----------


class TestModuleSurface:
    """The public module surface exposes the right names + a default path."""

    def test_default_aliases_path_is_under_flow_engineering_config(
        self,
    ) -> None:
        from pathlib import Path as _P  # noqa: N814

        assert (
            _P.home() / ".config" / "flow-engineering" / "project-aliases.json"
        ) == DEFAULT_ALIASES_PATH

    def test_aliases_module_exposes_public_functions(self) -> None:
        for name in (
            "resolve",
            "load_aliases",
            "save_aliases",
            "add_alias",
            "AliasConfigParseError",
            "DEFAULT_ALIASES_PATH",
        ):
            assert hasattr(_aliases, name), (
                f"Missing public name project_aliases.{name}"
            )
