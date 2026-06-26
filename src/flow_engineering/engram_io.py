"""Engram I/O wrapper for flow-engineering.

REQ-8: Cross-session recovery via Engram topic keys.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any


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
            if query.lower() in obs["content"].lower() or query.lower() in obs["title"].lower():
                results.append(obs)
            if len(results) >= limit:
                break
        return results

    def mem_get_observation(self, id: int) -> dict[str, Any]:
        if id not in self.observations:
            raise KeyError(f"No observation with id {id}")
        return self.observations[id]


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

    def save_phase(self, phase: str, content: str, title: str | None = None) -> dict[str, Any]:
        """Save a phase artifact (explore/propose/design/spec/tasks/apply-progress/etc)."""
        if title is None:
            title = f"{self.change}/{phase}"
        return self.backend.mem_save(
            title=title,
            content=content,
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

    def save_progress(
        self,
        task_id: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Save apply-progress for a specific task. Merge with existing if present."""
        existing = self.load_phase("apply-progress") or "{}"
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
