"""Binding helpers for `code_refs` blocks appended to Engram observations.

REQ-1, REQ-2 (PR#1): parse and format the trailing `<!-- code_refs -->` JSON block.

The block is the wire contract for decision-to-code linking (Approach D from
`sdd/decision-code-linking/proposal`). It lives at the END of observation
`content`, gated by an HTML comment marker, so existing FTS5 queries keep
working without migration.

Public surface (PR#1):
- ``CodeRef`` — frozen dataclass for a single binding.
- ``ParseError`` — raised when a marker is found but the block is malformed.
- ``extract_code_refs(content)`` — return list[CodeRef] from content.
- ``format_code_refs_block(refs, source)`` — produce canonical block string.
- ``split_prose_and_refs(content)`` — return (prose, block_or_empty).
- ``validate_block(body_json)`` — validate the JSON object shape.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final, Literal

CODE_REFS_MARKER: Final[str] = "<!-- code_refs -->"
SUPPORTED_SCHEMA: Final[int] = 1
Source = Literal["manual", "auto_suggest", "backfill", "unbound"]
ALLOWED_SOURCES: Final[tuple[str, ...]] = ("manual", "auto_suggest", "backfill", "unbound")


@dataclass(frozen=True)
class CodeRef:
    """A single binding between a decision observation and a code node."""

    project: str
    id: str
    label: str
    file: str
    line: int
    confidence: float
    source: Source


class ParseError(ValueError):
    """Raised when a ``code_refs`` marker is found but the block is malformed.

    ``offset`` carries the character offset of the malformed body within the
    original content (0-based), enabling precise error messages.
    """

    def __init__(self, message: str, *, offset: int = -1) -> None:
        super().__init__(message)
        self.offset = offset


def _split_marker(content: str) -> tuple[str, str]:
    """Return (prose, marker_block) where marker_block starts with the marker line.

    If no marker is present, returns (content, ""). The marker may appear
    anywhere; we keep everything up to and including the marker line in
    ``marker_block``, and the JSON body (everything after the marker line
    up to a trailing newline) is appended after.
    """
    idx = content.rfind(CODE_REFS_MARKER)
    if idx < 0:
        return content, ""
    marker_end = idx + len(CODE_REFS_MARKER)
    return content[:idx], content[idx:]


def split_prose_and_refs(content: str) -> tuple[str, str]:
    """Split content into (prose, block). The block is ``""`` when absent."""
    prose, marker_block = _split_marker(content)
    if not marker_block:
        return prose, ""
    # Normalise: the block must end with a newline; ensure trailing newline.
    block = marker_block if marker_block.endswith("\n") else marker_block + "\n"
    return prose, block


def _parse_nodes(payload: dict) -> list[CodeRef]:
    if not isinstance(payload, dict):
        raise ParseError("code_refs block must be a JSON object", offset=0)
    nodes = payload.get("nodes", [])
    if not isinstance(nodes, list):
        raise ParseError("'nodes' must be a list", offset=0)
    refs: list[CodeRef] = []
    for node in nodes:
        if not isinstance(node, dict):
            raise ParseError("each node must be an object", offset=0)
        node_source = node.get("source", "manual")
        if node_source not in ALLOWED_SOURCES:
            raise ParseError(
                f"unknown node source value: {node_source!r} "
                f"(allowed: {', '.join(ALLOWED_SOURCES)})",
                offset=0,
            )
        try:
            refs.append(
                CodeRef(
                    project=str(node["project"]),
                    id=str(node["id"]),
                    label=str(node["label"]),
                    file=str(node["file"]),
                    line=int(node["line"]),
                    confidence=float(node["confidence"]),
                    source=node_source,
                )
            )
        except KeyError as exc:
            raise ParseError(f"node missing required field: {exc.args[0]}", offset=0) from exc
    return refs


def validate_block(body_json: str) -> list[CodeRef]:
    """Validate a raw JSON body string. Returns parsed refs or raises ``ParseError``."""
    try:
        payload = json.loads(body_json)
    except json.JSONDecodeError as exc:
        raise ParseError(f"invalid JSON: {exc.msg}", offset=exc.pos) from exc
    if not isinstance(payload, dict):
        raise ParseError("code_refs block must be a JSON object", offset=0)
    schema = payload.get("schema")
    if schema != SUPPORTED_SCHEMA:
        raise ParseError(
            f"unsupported schema version: {schema!r} (expected {SUPPORTED_SCHEMA})",
            offset=0,
        )
    source = payload.get("source", "manual")
    if source not in ALLOWED_SOURCES:
        raise ParseError(
            f"unknown source value: {source!r} "
            f"(allowed: {', '.join(ALLOWED_SOURCES)})",
            offset=0,
        )
    return _parse_nodes(payload)


def extract_code_refs(content: str) -> list[CodeRef]:
    """Return the list of CodeRef from a content string.

    Returns an empty list when the marker is absent (legacy content).
    Raises ``ParseError`` when the marker is present but the block is malformed.
    """
    idx = content.rfind(CODE_REFS_MARKER)
    if idx < 0:
        return []
    # Find the body after the marker line.
    marker_end = idx + len(CODE_REFS_MARKER)
    # Skip the marker line's terminating newline if present.
    body_start = marker_end
    if body_start < len(content) and content[body_start] == "\n":
        body_start += 1
    # Body ends at next blank line or end of content.
    body_end = len(content)
    for stop in ("\n\n",):
        candidate = content.find(stop, body_start)
        if 0 <= candidate < body_end:
            body_end = candidate
    body = content[body_start:body_end].strip()
    if not body:
        # Empty body — treat as unbound (no nodes).
        return []
    try:
        return validate_block(body)
    except ParseError as exc:
        # Re-raise with the offset of the body within the original content.
        if exc.offset < 0:
            raise ParseError(str(exc), offset=body_start) from exc
        raise ParseError(str(exc), offset=body_start + exc.offset) from exc


def format_code_refs_block(refs: list[CodeRef], *, source: Source = "unbound") -> str:
    """Return a canonical block string for the given bindings.

    The output starts with ``<!-- code_refs -->`` on its own line and ends with
    a trailing newline. Nodes are sorted by ``id`` to ensure determinism
    (``extract(format(extract(x))) == extract(x)``).
    """
    if source not in ALLOWED_SOURCES:
        raise ValueError(
            f"unknown source: {source!r} (allowed: {', '.join(ALLOWED_SOURCES)})"
        )
    sorted_refs = sorted(refs, key=lambda r: r.id)
    nodes = [
        {
            "project": r.project,
            "id": r.id,
            "label": r.label,
            "file": r.file,
            "line": r.line,
            "confidence": r.confidence,
            "source": r.source,
        }
        for r in sorted_refs
    ]
    payload = {"schema": SUPPORTED_SCHEMA, "nodes": nodes, "source": source}
    body = json.dumps(payload, ensure_ascii=False, separators=(", ", ": "))
    return f"{CODE_REFS_MARKER}\n{body}\n"