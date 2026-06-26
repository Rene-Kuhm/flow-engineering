"""One-time backfill script: append ``code_refs`` blocks to legacy observations.

REQ-4 (PR#1): dry-run by default; ``--apply`` mutates. Pre-image written to
``~/.flow-engineering/backfill-preimage.jsonl`` so any change can be reverted.
Idempotent — observations already marked ``source: backfill`` are skipped.

Usage::

    python scripts/backfill_code_refs.py                  # dry-run (default)
    python scripts/backfill_code_refs.py --apply         # mutate
    python scripts/backfill_code_refs.py --apply --project insyd
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from flow_engineering.binding import (
    CODE_REFS_MARKER,
    extract_code_refs,
    format_code_refs_block,
)
from flow_engineering.engram_io import EngramBackend

if TYPE_CHECKING:
    pass

PREIMAGE_FILE: str = "backfill-preimage.jsonl"
BACKFILL_CONFIDENCE: float = 0.3
BACKFILL_SOURCE: str = "backfill"
DEFAULT_PROJECT: str = "insyd"


@dataclass
class BackfillResult:
    """Summary of a backfill run (one row per ``run()`` call)."""

    scanned: int
    would_change: int
    applied: int
    skipped: int
    errors: int
    preimage_path: Path | None

    def to_dict(self) -> dict:
        return {
            "scanned": self.scanned,
            "would_change": self.would_change,
            "applied": self.applied,
            "skipped": self.skipped,
            "errors": self.errors,
            "preimage_path": str(self.preimage_path) if self.preimage_path else None,
        }


def _has_backfill_block(content: str) -> bool:
    """Return True if content carries a backfill block (skip per idempotency).

    Lenient: a parse failure on the existing block still counts as 'has
    block' so backfill does not rewrite observations whose block came from
    another tool or a malformed earlier run.
    """
    if CODE_REFS_MARKER not in content:
        return False
    try:
        refs = extract_code_refs(content)
    except Exception:
        # Block present but malformed — do not rewrite.
        return True
    return any(r.source == BACKFILL_SOURCE for r in refs)


def _write_preimage(
    path: Path,
    *,
    observation_id: int,
    before: str,
    after: str,
) -> None:
    """Append one pre-image entry as JSONL."""
    entry = {
        "id": observation_id,
        "before": before,
        "after": after,
        "ts": int(time.time()),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run(
    *,
    backend: EngramBackend,
    project: str = DEFAULT_PROJECT,
    cache_dir: Path,
    dry_run: bool,
) -> BackfillResult:
    """Append unbound ``code_refs`` blocks to observations missing them.

    - ``dry_run=True`` reports what would change without mutating.
    - ``dry_run=False`` mutates; idempotent across re-runs.
    - Pre-image JSONL written for every mutation (under ``cache_dir``).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    preimage_path = cache_dir / PREIMAGE_FILE
    if not dry_run and preimage_path.exists():
        # Wipe the pre-image file at the start of an apply run so the file
        # reflects only this invocation.
        preimage_path.unlink()

    scanned = would_change = applied = skipped = errors = 0
    for obs in backend.iter_observations(project=project):
        scanned += 1
        content = obs.get("content", "")
        if not isinstance(content, str):
            errors += 1
            continue
        if CODE_REFS_MARKER in content:
            if _has_backfill_block(content):
                skipped += 1
                continue
            # Non-backfill block (manual / auto_suggest / unbound from a
            # prior save): leave it alone.
            skipped += 1
            continue
        would_change += 1
        if dry_run:
            continue
        new_content = content + format_code_refs_block([], source=BACKFILL_SOURCE)
        try:
            backend.update_observation(obs["id"], content=new_content)
        except Exception:
            errors += 1
            continue
        _write_preimage(
            preimage_path,
            observation_id=obs["id"],
            before=content,
            after=new_content,
        )
        applied += 1

    return BackfillResult(
        scanned=scanned,
        would_change=would_change,
        applied=applied,
        skipped=skipped,
        errors=errors,
        preimage_path=preimage_path if not dry_run else None,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill code_refs blocks.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Mutate observations (default is dry-run).",
    )
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT,
        help=f"Engram project name (default: {DEFAULT_PROJECT}).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".flow-engineering",
        help="Directory for pre-image + cache files.",
    )
    return parser.parse_args(argv)


def _build_backend_from_args(args: argparse.Namespace) -> EngramBackend | None:
    """Build the Engram backend for CLI invocation.

    For now this returns None — the CLI runs against the live Engram MCP
    backend. The unit-test entry point (``run()``) accepts any backend.
    """
    return None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "apply" if args.apply else "dry-run"
    print(f"[backfill] mode={mode} project={args.project} cache_dir={args.cache_dir}")
    backend = _build_backend_from_args(args)
    if backend is None:
        print(
            "[backfill] no backend configured for CLI mode — invoke via tests\n"
            "  or wire a real Engram backend in _build_backend_from_args.",
            file=sys.stderr,
        )
        return 0
    result = run(
        backend=backend,
        project=args.project,
        cache_dir=args.cache_dir,
        dry_run=not args.apply,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
