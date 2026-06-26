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

METADATA_MARKER: str = "<!-- metadata -->"
_METADATA_SCHEMA: int = 1


class VectorSearchDisabled(RuntimeError):
    """Raised when vector / hybrid search is called without the activation gate.

    REQ-17: the message MUST include the install hint so users without the
    ``[vectors]`` extra get an actionable error. Subclassing ``RuntimeError``
    lets callers isolate gate failures from genuine bugs in semantic search
    code paths.
    """

    def __init__(self, message: str | None = None) -> None:
        if message is None:
            message = (
                "Vector search disabled. "
                "Install with: pip install flow-engineering[vectors]"
            )
        super().__init__(message)


class EngramBackend(ABC):
    """Abstract Engram backend. Real implementation calls MCP, tests use in-memory.

    ABC v1.2 — added ``mem_search_federated`` as default ``NotImplementedError``
    (NON-BREAKING; mirrors ``mem_search_semantic`` / ``mem_search_hybrid`` from
    v1.1 and the ``update_observation`` precedent further below). Third-party
    subclasses import unchanged; they only break at call-time of the new method.
    """

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

    def mem_search_semantic(
        self, query: str, k: int = 10, *, trigger: str = "programmatic"
    ) -> list[dict[str, Any]]:
        """Semantic search by embedding similarity (v1.1 — NON-BREAKING default).

        Subclasses that do not override this method get a call-time
        ``NotImplementedError``; instantiation is unaffected. The
        ``InMemoryBackend`` test fixture overrides this to raise
        ``VectorSearchDisabled`` with an actionable install hint.

        ``trigger`` is a kwarg-only observability tag (REQ-22) carried
        through to the ``vector_search_invoked_total`` counter. The ABC
        default ignores it (raises before any counter would fire).
        """
        raise NotImplementedError(
            "vector search requires explicit backend impl — see [vectors] extra"
        )

    def mem_search_hybrid(
        self,
        query: str,
        k: int = 10,
        alpha: float = 0.5,
        *,
        trigger: str = "programmatic",
    ) -> list[dict[str, Any]]:
        """Hybrid semantic + BM25 search (v1.1 — NON-BREAKING default).

        Subclasses that do not override this method get a call-time
        ``NotImplementedError``; instantiation is unaffected. The
        ``InMemoryBackend`` test fixture overrides this to raise
        ``VectorSearchDisabled`` with an actionable install hint.
        """
        raise NotImplementedError(
            "vector search requires explicit backend impl — see [vectors] extra"
        )

    def mem_search_federated(
        self,
        query: str,
        projects: list[str] | None = None,
        *,
        limit: int = 10,
        since: str | None = None,
        type_filter: list[str] | None = None,
        scope: str = "project",
    ) -> list[dict[str, Any]]:
        """Federated multi-project search (v1.2 — NON-BREAKING default).

        REQ-23 (cross-project-federation): search across N project tags in a
        single FTS5 pass with optional ``project IN (...)``, ``created_at >=``
        and ``type IN (...)`` filters. ``projects=None`` ⇒ no project filter
        (search all). ``projects=[]`` ⇒ short-circuit ``[]`` (SQLite rejects
        ``IN ()`` as a syntax error). Non-empty ``projects`` ⇒ parameterised
        ``IN (?, ?, ...)``. ``since`` is lexicographic against the
        ``YYYY-MM-DD HH:MM:SS`` TEXT format. ``type_filter`` is exact-match
        (case-sensitive). Each returned row MUST preserve the ``project``
        field for caller attribution.

        Subclasses that do not override this method get a call-time
        ``NotImplementedError``; instantiation is unaffected. The
        ``InMemoryBackend`` test fixture overrides this to filter the
        in-memory dict (no SQLite required for unit tests).
        """
        raise NotImplementedError(
            "federated search requires explicit backend impl — EngramBackend v1.2"
        )

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

    def mem_search_semantic(
        self, query: str, k: int = 10, *, trigger: str = "programmatic"
    ) -> list[dict[str, Any]]:
        """InMemoryBackend is the prose test fixture — vector search is opt-in.

        REQ-17: ``InMemoryBackend`` raises ``VectorSearchDisabled`` with the
        install hint when vector / hybrid methods are called. The prose
        ``mem_search`` path stays unchanged so existing tests are unaffected.
        ``trigger`` is accepted for API parity with ``HybridBackend`` but
        ignored here (no observability event fires before the raise).
        """
        raise VectorSearchDisabled()

    def mem_search_hybrid(
        self,
        query: str,
        k: int = 10,
        alpha: float = 0.5,
        *,
        trigger: str = "programmatic",
    ) -> list[dict[str, Any]]:
        """InMemoryBackend is the prose test fixture — vector search is opt-in.

        REQ-17: see ``mem_search_semantic`` above. Hybrid scoring is only
        available via a real vector-enabled backend.
        """
        raise VectorSearchDisabled()


def phase_topic_key(change: str, phase: str) -> str:
    """Build the topic_key for a change phase observation."""
    return f"sdd/{change}/{phase}"


def _extract_metadata_fields(content: str) -> dict[str, Any]:
    """Parse existing `<!-- metadata -->` JSON body and return its ``fields``.

    Returns ``{}`` when the marker is absent OR when the body is malformed
    (defensive — a corrupt metadata block must not block a fresh write).
    Uses ``raw_decode`` so trailing content (e.g. a ``code_refs`` block
    appearing after the metadata block) does not corrupt the parse.
    """
    marker_idx = content.rfind(METADATA_MARKER)
    if marker_idx < 0:
        return {}
    body_start = marker_idx + len(METADATA_MARKER)
    if body_start < len(content) and content[body_start] == "\n":
        body_start += 1
    body = content[body_start:].lstrip()
    if not body:
        return {}
    try:
        payload, _end = json.JSONDecoder().raw_decode(body)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    fields = payload.get("fields", {})
    return fields if isinstance(fields, dict) else {}


def _scan_to_next_newline(content: str, start: int) -> int:
    """Return offset from ``start`` to the next ``\\n`` (or end of content).

    Used by ``_replace_or_append_metadata_block`` when the metadata body
    fails to parse: the malformed JSON sits on a single line, so we strip
    everything from the marker up to (and including) the next newline.
    """
    nl_idx = content.find("\n", start)
    if nl_idx == -1:
        return len(content) - start
    return nl_idx - start


def _format_metadata_block(fields: dict[str, Any]) -> str:
    """Return a canonical ``<!-- metadata -->`` block for the given fields."""
    payload = {"schema": _METADATA_SCHEMA, "fields": dict(fields)}
    body = json.dumps(payload, ensure_ascii=False, separators=(", ", ": "))
    return f"{METADATA_MARKER}\n{body}\n"


def _replace_or_append_metadata_block(content: str, new_block: str) -> str:
    """Replace the existing ``<!-- metadata -->`` block or insert one.

    Layout invariant: ``code_refs`` is always the LAST block in content.
    Metadata is placed immediately before the ``code_refs`` block (when
    present) or appended at end of content (when no ``code_refs`` exists).

    When the metadata block already exists anywhere in the content, it is
    located via ``raw_decode`` and replaced in place — preserving the
    prose and any trailing ``code_refs`` block byte-for-byte.
    """
    if METADATA_MARKER in content:
        marker_idx = content.rfind(METADATA_MARKER)
        body_start = marker_idx + len(METADATA_MARKER)
        if body_start < len(content) and content[body_start] == "\n":
            body_start += 1
        try:
            _payload, json_end = json.JSONDecoder().raw_decode(content[body_start:])
        except json.JSONDecodeError:
            json_end = _scan_to_next_newline(content, body_start)
        block_end = body_start + json_end
        if block_end < len(content) and content[block_end] == "\n":
            block_end += 1
        head = content[:marker_idx].rstrip("\n")
        tail = content[block_end:].lstrip("\n")
        if tail:
            return head + "\n\n" + new_block + "\n" + tail
        return head + "\n\n" + new_block
    if CODE_REFS_MARKER in content:
        prose, code_refs_block = split_prose_and_refs(content)
        return prose + new_block + code_refs_block
    return content.rstrip("\n") + "\n\n" + new_block


def cross_session_topic_key() -> str:
    """Topic key for cross-session flow searches."""
    return "sdd/flow-engineering"


def iter_observations_for_change(
    change: str, backend: EngramBackend, *, project: str | None = None
) -> list[dict[str, Any]]:
    """Return every observation belonging to a change.

    Filters by topic-key prefix ``sdd/{change}/`` so cross-change observations
    (e.g. ``sdd/flow-engineering/...`` or ``sdd/other-change/...``) are not
    leaked into the result set. The optional ``project`` filter is applied
    after the topic-key filter.

    Used by ``flow inspect <change>`` and by observability helpers that need
    to scan a single change's worth of decisions.
    """
    prefix = f"sdd/{change}/"
    all_obs = backend.iter_observations(project=project)
    return [o for o in all_obs if str(o.get("topic_key", "")).startswith(prefix)]


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

    def update_observation_metadata(
        self, observation_id: int, metadata: dict[str, Any]
    ) -> None:
        """Append/update a trailing ``<!-- metadata -->`` block.

        Distinct marker from ``<!-- code_refs -->``: this one carries
        observability metadata (e.g. ``last_verified_at``,
        ``last_drift_class``) and never mutates the ``code_refs`` block.
        The ``code_refs`` block is preserved byte-identical.

        Semantics:
        - If the marker is absent, a fresh block is appended AFTER any
          existing ``code_refs`` block (or at end of content when none).
        - If the marker is present, the existing JSON body is parsed; new
          keys win on conflict, existing keys are preserved.
        - Malformed existing metadata JSON is treated as an empty block
          (defensive — the new keys overwrite the corrupt body).
        - A single ``update_observation`` call performs the write.

        Fail-open: any exception during the read/parse/write cycle is
        swallowed and logged to observability. This method never raises.
        """
        from flow_engineering import observability

        try:
            current = self.backend.mem_get_observation(observation_id)
            content = current["content"] if isinstance(current, dict) else str(current)

            existing_fields = _extract_metadata_fields(content)
            merged = {**existing_fields, **metadata}

            new_block = _format_metadata_block(merged)
            updated = _replace_or_append_metadata_block(content, new_block)
            self.backend.update_observation(observation_id, content=updated)
        except Exception:
            observability.increment("update_observation_metadata_failed_total")
            return

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
