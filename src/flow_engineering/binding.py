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


def extract_code_refs(content: str) -> list[CodeRef]:
    """Return the list of CodeRef from a content string.

    Returns an empty list when the marker is absent (legacy content).
    Raises ``ParseError`` when the marker is present but the block is malformed.
    """
    # Full implementation lands in GREEN commit; stub returns empty.
    return []


def format_code_refs_block(refs: list[CodeRef], *, source: Source = "unbound") -> str:
    """Return a canonical block string for the given bindings.

    The output starts with ``<!-- code_refs -->`` on its own line and ends with
    a trailing newline. Nodes are sorted by ``id`` to ensure determinism
    (``extract(format(extract(x))) == extract(x)``).
    """
    raise NotImplementedError("format_code_refs_block lands in GREEN commit")


def split_prose_and_refs(content: str) -> tuple[str, str]:
    """Split content into (prose, block). The block is ``""`` when absent."""
    raise NotImplementedError("split_prose_and_refs lands in GREEN commit")


def validate_block(body_json: str) -> list[CodeRef]:
    """Validate a raw JSON body string. Returns parsed refs or raises ``ParseError``."""
    raise NotImplementedError("validate_block lands in GREEN commit")