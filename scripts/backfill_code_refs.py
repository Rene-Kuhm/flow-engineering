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
from pathlib import Path

PREIMAGE_FILE: str = "backfill-preimage.jsonl"
BACKFILL_CONFIDENCE: float = 0.3
DEFAULT_PROJECT: str = "insyd"


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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "apply" if args.apply else "dry-run"
    print(f"[backfill] mode={mode} project={args.project} cache_dir={args.cache_dir}")
    # Real implementation lands in the GREEN commit.
    print("[backfill] stub: no-op (implementation pending)")
    return 0


if __name__ == "__main__":
    sys.exit(main())