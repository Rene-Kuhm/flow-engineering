"""Graphify query wrapper for the `code_refs` suggester.

REQ-3 (PR#1): thin wrapper around the ``graphify query`` CLI plus a Jaccard
fallback when the binary is missing. Cache lives at
``~/.flow-engineering/graphify_cache.json`` keyed by sha1(text + graph.json
mtime). Returns ``[]`` on every error path — never raises from the save flow.

Public surface (PR#1):
- ``query_nodes(text, threshold, max_results, cache_dir)``
- ``jaccard_fallback(text, graph_json_path, top_k)``
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from flow_engineering.binding import ALLOWED_SOURCES, CodeRef

DEFAULT_CACHE_DIR: Final[Path] = Path.home() / ".flow-engineering"
DEFAULT_CACHE_FILE: Final[str] = "graphify_cache.json"
DEFAULT_TIMEOUT_SECONDS: Final[float] = 5.0
DEFAULT_THRESHOLD: Final[float] = 0.3
DEFAULT_MAX_RESULTS: Final[int] = 5
GRAPHIFY_BIN: Final[str] = "graphify"
DEFAULT_GRAPH_JSON: Final[Path] = Path(r"c:\dev\proyects\graphify-out\graph.json")

_TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")
_CACHE_MAX_ENTRIES: Final[int] = 64


def _graph_json_mtime(graph_path: Path = DEFAULT_GRAPH_JSON) -> int:
    """Return the mtime of the graph.json file, or 0 when missing."""
    try:
        return int(graph_path.stat().st_mtime)
    except FileNotFoundError:
        return 0


def _cache_key(text: str, mtime: int) -> str:
    """Return a stable cache key for (text, mtime)."""
    h = hashlib.sha1()
    h.update(text.encode("utf-8"))
    h.update(b"\x00")
    h.update(str(mtime).encode("ascii"))
    return h.hexdigest()


def _cache_path(cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / DEFAULT_CACHE_FILE


def _load_cache(cache_dir: Path) -> dict[str, dict]:
    path = _cache_path(cache_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache_dir: Path, cache: dict[str, dict]) -> None:
    """Persist the cache, trimming to the last CACHE_MAX_ENTRIES entries."""
    if len(cache) > _CACHE_MAX_ENTRIES:
        # Drop the oldest entries by insertion order (Python dicts preserve it).
        keep = list(cache.items())[-_CACHE_MAX_ENTRIES:]
        cache = dict(keep)
    try:
        _cache_path(cache_dir).write_text(
            json.dumps(cache, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError:
        # Cache write failure is non-fatal; the caller already has the
        # in-memory result and the next call will re-query.
        pass


def _run_graphify_cli(
    text: str,
    *,
    bin_name: str = GRAPHIFY_BIN,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[int, str, str]:
    """Run ``<bin> query <text>`` and return (returncode, stdout, stderr)."""
    if shutil.which(bin_name) is None:
        raise FileNotFoundError(f"{bin_name} not on PATH")
    completed = subprocess.run(
        [bin_name, "query", text],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def _refs_from_cli_payload(payload: str) -> list[CodeRef]:
    """Parse a JSON CLI payload into a list of CodeRef objects."""
    data = json.loads(payload)
    nodes = data.get("nodes", []) if isinstance(data, dict) else []
    refs: list[CodeRef] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        try:
            source = n.get("source", "auto_suggest")
            if source not in ALLOWED_SOURCES:
                source = "auto_suggest"
            refs.append(
                CodeRef(
                    project=str(n.get("project", "")),
                    id=str(n["id"]),
                    label=str(n.get("label", n["id"])),
                    file=str(n.get("file", "")),
                    line=int(n.get("line", 0)),
                    confidence=float(n.get("confidence", 0.0)),
                    source=source,  # type: ignore[arg-type]
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    return refs


def _filter_by_threshold(
    refs: Iterable[CodeRef], threshold: float, max_results: int
) -> list[CodeRef]:
    ranked = sorted(refs, key=lambda r: r.confidence, reverse=True)
    return [r for r in ranked if r.confidence >= threshold][:max_results]


def query_nodes(
    text: str,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    max_results: int = DEFAULT_MAX_RESULTS,
    cache_dir: Path = DEFAULT_CACHE_DIR,
) -> list[CodeRef]:
    """Return up to ``max_results`` candidate CodeRefs for ``text``.

    Wraps ``graphify query <text>`` with sha1(text + graph.json mtime) caching.
    Returns ``[]`` on missing binary / missing graph.json / non-zero exit /
    timeout — never raises.
    """
    if not text:
        return []
    mtime = _graph_json_mtime()
    key = _cache_key(text, mtime)
    cache = _load_cache(cache_dir)
    if key in cache:
        cached_refs = cache[key].get("refs", [])
        return _filter_by_threshold(_refs_from_cli_payload(json.dumps({"nodes": cached_refs})),
                                    threshold, max_results)
    try:
        returncode, stdout, stderr = _run_graphify_cli(text)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    if returncode != 0:
        return []
    try:
        refs = _refs_from_cli_payload(stdout)
    except (json.JSONDecodeError, ValueError):
        return []
    filtered = _filter_by_threshold(refs, threshold, max_results)
    # Persist for next call (filtered snapshot — same call returns this).
    cache[key] = {"refs": [
        {
            "project": r.project,
            "id": r.id,
            "label": r.label,
            "file": r.file,
            "line": r.line,
            "confidence": r.confidence,
            "source": r.source,
        }
        for r in filtered
    ], "mtime": mtime}
    _save_cache(cache_dir, cache)
    return filtered


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return {t.lower() for t in _TOKEN_PATTERN.findall(text)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def _node_tokens(node: dict) -> set[str]:
    parts: list[str] = []
    for key in ("label", "source_file", "community_name"):
        value = node.get(key)
        if isinstance(value, str):
            parts.append(value)
    label_id = node.get("id")
    if isinstance(label_id, str):
        parts.append(label_id)
    return _tokenize(" ".join(parts))


def jaccard_fallback(text: str, graph_json_path: Path, top_k: int) -> list[CodeRef]:
    """Score nodes by Jaccard similarity of tokens.

    Used when the graphify CLI is unavailable. Returns at most ``top_k`` refs.
    """
    if not text:
        return []
    if not graph_json_path.exists():
        return []
    try:
        data = json.loads(graph_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    nodes = data.get("nodes", []) if isinstance(data, dict) else []
    if not isinstance(nodes, list):
        return []
    query_tokens = _tokenize(text)
    scored: list[tuple[float, CodeRef]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_tokens = _node_tokens(node)
        score = _jaccard(query_tokens, node_tokens)
        if score <= 0:
            continue
        try:
            ref = CodeRef(
                project="insyd",
                id=str(node.get("id", "")),
                label=str(node.get("label", node.get("id", ""))),
                file=str(node.get("source_file", "")),
                line=_parse_line(node.get("source_location")),
                confidence=round(score, 3),
                source="auto_suggest",
            )
        except (KeyError, ValueError, TypeError):
            continue
        scored.append((score, ref))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:top_k]]


def _parse_line(location: object) -> int:
    if isinstance(location, int):
        return location
    if isinstance(location, str):
        match = re.search(r"\d+", location)
        if match:
            return int(match.group(0))
    return 0
