"""Engram I/O wrapper for flow-engineering.

REQ-8: Cross-session recovery via Engram topic keys.
REQ-3 (decision-code-linking PR#1): ``save_phase`` appends an unbound
``code_refs`` block when the marker is absent, preserves valid blocks, and
rejects malformed blocks before writing. ``load_code_refs`` returns the
parsed bindings for a phase.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from flow_engineering.auto_suggest_code_refs import (
    FLOW_AUTO_SUGGEST_ENV as _FLOW_AUTO_SUGGEST_ENV,
)
from flow_engineering.auto_suggest_code_refs import (
    auto_suggest_code_refs,
)
from flow_engineering.binding import (
    CODE_REFS_MARKER,
    CodeRef,
    extract_code_refs,
    format_code_refs_block,
    split_prose_and_refs,
    validate_block,
)


class EngramBackend(ABC):
    """Abstract Engram backend. Real implementation calls MCP, tests use in-memory."""

    @abstractmethod
    def mem_save(
        self,
        title: str,
        content: str,
        topic_key: str,
        type: str = "manual",
        scope: str = "project",
    ) -> dict[str, Any]:
        """Save an observation."""

    @abstractmethod
    def mem_search(
        self,
        query: str,
        topic_key: str | None = None,
        limit: int = 10,
        scope: str = "project",
    ) -> list[dict[str, Any]]:
        """Search observations."""

    @abstractmethod
    def mem_get_observation(self, id: int) -> dict[str, Any]:
        """Get a single observation by ID."""

    def iter_observations(self, *, project: str | None = None) -> list[dict[str, Any]]:
        """Return every observation, optionally filtered by project.

        Default impl uses mem_search with an empty query and a generous
        limit; real backends should override for efficient scans.
        """
        results = self.mem_search(query="", topic_key=None, limit=10_000, scope="project")
        if project is not None:
            return [r for r in results if r.get("project") in (project, None) or True]
        return results

    def update_observation(
        self,
        id: int,
        *,
        content: str | None = None,
        type: str | None = None,
    ) -> dict[str, Any]:
        """Replace an existing observation's content and/or type.

        Default impl raises NotImplementedError — concrete backends MUST
        override (the InMemoryBackend does).
        """
        raise NotImplementedError("update_observation not implemented for this backend")


class InMemoryBackend(EngramBackend):
    """In-memory backend for tests."""

    def __init__(self) -> None:
        self.observations: dict[int, dict[str, Any]] = {}
        self.next_id = 1

    def mem_save(
        self,
        title: str,
        content: str,
        topic_key: str,
        type: str = "manual",
        scope: str = "project",
    ) -> dict[str, Any]:
        obs = {
            "id": self.next_id,
            "title": title,
            "content": content,
            "topic_key": topic_key,
            "type": type,
            "scope": scope,
            "project": "insyd",
            "created_at": self.next_id * 1000,
            "updated_at": self.next_id * 1000,
        }
        self.observations[self.next_id] = obs
        self.next_id += 1
        return obs

    def mem_search(
        self,
        query: str,
        topic_key: str | None = None,
        limit: int = 10,
        scope: str = "project",
    ) -> list[dict[str, Any]]:
        results = []
        # Sort by id descending so newest is first
        for obs in sorted(self.observations.values(), key=lambda o: o["id"], reverse=True):
            if topic_key and obs["topic_key"] != topic_key:
                continue
            if query and query.lower() not in obs["content"].lower() and query.lower() not in obs["title"].lower():
                continue
            results.append(obs)
            if len(results) >= limit:
                break
        return results

    def mem_get_observation(self, id: int) -> dict[str, Any]:
        if id not in self.observations:
            raise KeyError(f"No observation with id {id}")
        return self.observations[id]

    def iter_observations(self, *, project: str | None = None) -> list[dict[str, Any]]:
        # Empty query scans all observations (mem_search returns everything).
        all_obs = self.mem_search(query="", topic_key=None, limit=10_000, scope="project")
        if project is None:
            return all_obs
        return [o for o in all_obs if o.get("project") == project]

    def update_observation(
        self,
        id: int,
        *,
        content: str | None = None,
        type: str | None = None,
    ) -> dict[str, Any]:
        if id not in self.observations:
            raise KeyError(f"No observation with id {id}")
        obs = self.observations[id]
        if content is not None:
            obs["content"] = content
        if type is not None:
            obs["type"] = type
        # Advance updated_at, preserve created_at.
        obs["updated_at"] = obs.get("updated_at", 0) + 1
        return obs


def phase_topic_key(change: str, phase: str) -> str:
    """Build the topic_key for a change phase observation."""
    return f"sdd/{change}/{phase}"


def cross_session_topic_key() -> str:
    """Topic key for cross-session flow searches."""
    return "sdd/flow-engineering"


class EngramClient:
    """High-level wrapper for Engram operations on a change."""

    def __init__(self, change: str, backend: EngramBackend) -> None:
        self.change = change
        self.backend = backend

    def save_phase(
        self,
        phase: str,
        content: str,
        title: str | None = None,
        *,
        with_suggest: bool = False,
        no_suggest: bool = False,
        is_tty: bool | None = None,
        prompt_fn=None,
    ) -> dict[str, Any]:
        """Save a phase artifact (explore/propose/design/spec/tasks/apply-progress/etc).

        ``code_refs`` block handling (REQ-3):
        - When the marker is absent, append an empty ``unbound`` block so
          downstream readers can rely on the block being present.
        - When the marker IS present, validate the block via
          ``binding.validate_block``. Malformed or unknown-schema blocks
          raise ``ParseError`` and prevent the write (no row is written).
        - A valid existing block is preserved as-is.

        Auto-suggest hook (REQ-6, PR#2 batch 1):
        - When ``with_suggest=True`` OR ``FLOW_AUTO_SUGGEST=1`` env var is
          set AND the content has no explicit ``code_refs`` block, the
          suggester is consulted. Its ``SuggestionResult`` drives the
          block source (``auto_suggest`` / ``unbound`` / ``manual``).
        - When ``no_suggest=True``, the suggester is bypassed entirely;
          the saved block has ``source: manual`` with empty nodes.
        - The suggester MUST fail-open: any internal error yields a normal
          ``unbound`` save (no exception escapes this method).
        """
        if title is None:
            title = f"{self.change}/{phase}"
        new_content = self._build_content_with_block(
            content,
            with_suggest=with_suggest,
            no_suggest=no_suggest,
            is_tty=is_tty,
            prompt_fn=prompt_fn,
        )
        return self.backend.mem_save(
            title=title,
            content=new_content,
            topic_key=phase_topic_key(self.change, phase),
            type="architecture",
        )

    def load_phase(self, phase: str) -> str | None:
        """Load the most recent artifact for a phase. Returns None if not found."""
        topic = phase_topic_key(self.change, phase)
        results = self.backend.mem_search(query=self.change, topic_key=topic, limit=1)
        if not results:
            return None
        content = self.backend.mem_get_observation(results[0]["id"])["content"]
        return content if isinstance(content, str) else str(content)

    def load_code_refs(self, phase: str) -> list[CodeRef] | None:
        """Return the parsed ``code_refs`` bindings for a phase.

        Returns ``None`` when no observation exists for the phase. Returns
        an empty list when the phase exists but the marker is absent (legacy
        content). Raises ``ParseError`` only when the marker is present but
        the block is malformed; callers may swallow that to render a row
        with the parse-error note (REQ-7 scenario).
        """
        content = self.load_phase(phase)
        if content is None:
            return None
        if CODE_REFS_MARKER not in content:
            return []
        return extract_code_refs(content)

    def load_phase_prose(self, phase: str) -> str | None:
        """Load the phase content with the trailing ``code_refs`` block stripped.

        Useful for callers that need the prose portion (e.g. JSON parsing
        of apply-progress). Returns ``None`` when the phase is missing.
        """
        content = self.load_phase(phase)
        if content is None:
            return None
        prose, _block = split_prose_and_refs(content)
        return prose

    @staticmethod
    def _ensure_code_refs_block(content: str) -> str:
        """Return content guaranteed to end with a valid ``code_refs`` block.

        - Marker absent  -> append an empty unbound block.
        - Marker present -> validate the existing block (raises ParseError
          on bad JSON / unknown schema); preserve as-is when valid.
        """
        if CODE_REFS_MARKER in content:
            # Existing block — validate before write. Raises ParseError on failure.
            prose, block = split_prose_and_refs(content)
            body = block[len(CODE_REFS_MARKER):].strip()
            if body:
                validate_block(body)  # raises ParseError on bad shape
            # Preserve prose + block byte-for-byte.
            return content
        # Append a fresh unbound block.
        return content + format_code_refs_block([], source="unbound")

    def _build_content_with_block(
        self,
        content: str,
        *,
        with_suggest: bool,
        no_suggest: bool,
        is_tty: bool | None,
        prompt_fn,
    ) -> str:
        """Build content + block honoring REQ-3 validation + REQ-6 auto-suggest.

        - Marker present: validate and preserve (REQ-3, no auto-suggest).
        - Marker absent: run auto-suggest when warranted, otherwise append
          a default unbound block. The suggester MUST fail-open.
        """
        # REQ-3 path: explicit block already present — validate + preserve.
        if CODE_REFS_MARKER in content:
            prose, block = split_prose_and_refs(content)
            body = block[len(CODE_REFS_MARKER):].strip()
            if body:
                validate_block(body)  # raises ParseError on bad shape
            return content

        # No explicit block — decide whether to auto-suggest.
        env_active = (
            with_suggest
            or __import__("os").environ.get(_FLOW_AUTO_SUGGEST_ENV) == "1"
            or bool(is_tty)
        )
        if no_suggest:
            # Caller opted out — record the explicit manual intent.
            return content + format_code_refs_block([], source="manual")
        if not env_active:
            # Default path: append a fresh unbound block.
            return content + format_code_refs_block([], source="unbound")

        # Auto-suggest path. Must fail-open: any error -> default unbound.
        try:
            result = auto_suggest_code_refs(
                content,
                with_suggest=with_suggest,
                no_suggest=False,
                is_tty=bool(is_tty) if is_tty is not None else False,
                prompt_fn=prompt_fn,
            )
        except Exception:
            return content + format_code_refs_block([], source="unbound")

        # Build the block from the suggestion result. The block's source
        # field matches the result source so REQ-7 / REQ-8 can read it.
        return content + format_code_refs_block(result.refs, source=result.source)

    def save_progress(
        self,
        task_id: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Save apply-progress for a specific task. Merge with existing if present."""
        existing = self.load_phase_prose("apply-progress") or "{}"
        try:
            data = json.loads(existing)
        except json.JSONDecodeError:
            data = {}
        if "tasks" not in data:
            data["tasks"] = {}
        data["tasks"][task_id] = {
            "status": status,
            "details": details or {},
            "updated_at": data.get("updated_at"),
        }
        data["updated_at"] = data["tasks"][task_id]["updated_at"]
        return self.save_phase(
            "apply-progress",
            json.dumps(data, indent=2, ensure_ascii=False),
            title=f"{self.change} apply-progress",
        )

    def search_cross_session(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search across all flow-engineering changes (no topic filter)."""
        return self.backend.mem_search(
            query=query,
            topic_key=None,
            limit=limit,
        )
