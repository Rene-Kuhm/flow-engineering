"""OpenCode SKILL.md runtime catalog + checksum drift detection (REQ-49).

REQ-49 D1 + D6: Mirror catalog for the 10 OpenCode runtime sdd-* agent prompts
across both surfaces (``~/.config/opencode/skills/sdd-*/SKILL.md`` and
``~/.config/opencode/prompts/sdd/*.md``) for a total of 20 catalog entries.

Public API:
- :class:`SkillEntry` -- frozen dataclass describing one catalog entry.
- :class:`SkillDrift` -- frozen dataclass describing one drift finding.
- :data:`SKILL_CATALOG` -- the 20-entry catalog keyed by ``<skill>/<surface>``.
- :data:`SIDECAR_PATH` -- path to ``~/.flow-engineering/prompt_checksums.json``.
- :class:`SkillVersionError` -- raised on parse errors per design.
- :data:`FRONTMATTER_PATTERN` -- regex matching the YAML frontmatter block.
- :func:`compute_frontmatter_sha256` -- SHA-256 of the canonicalized frontmatter.
- :func:`parse_frontmatter` -- YAML frontmatter -> dict parser.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_PATTERN: re.Pattern[str] = re.compile(
    r"\A---\s*\n(.*?\n)---\s*\n",
    re.DOTALL,
)
r"""Regex that captures the YAML frontmatter block between two ``---`` markers.

The pattern is anchored at start-of-string (``\A``) so trailing content
(body + closing fence) does NOT participate in the match. Whitespace after
the opening and closing ``---`` fences is tolerated so ``---\n`` and
``--- \n`` both work (matches the OpenCode SKILL.md convention).
"""


SIDECAR_PATH: Path = Path.home() / ".flow-engineering" / "prompt_checksums.json"
"""JSON sidecar at ``~/.flow-engineering/prompt_checksums.json``.

Mirrors the existing ``~/.flow-engineering/metrics.jsonl`` (REQ-8) convention.
Created lazily on first ``flow prompts check --init`` invocation.
"""


@dataclass(frozen=True)
class SkillEntry:
    """One OpenCode runtime SKILL.md catalog entry.

    Attributes:
        skill_name: The sdd-* agent identifier (e.g., ``"sdd-apply"``).
            MUST be lowercase kebab-case ``[a-z0-9-]+``.
        surface: Either ``"skill"`` (the ``SKILL.md`` file) or ``"prompt"``
            (the ``prompts/sdd/*.md`` file). The two surfaces are
            maintained separately per OpenCode convention.
        expected_version: The minimum semver ``MAJOR.MINOR`` (e.g., ``"3.0"``)
            parsed from the on-disk frontmatter ``version`` field.
        expected_path: Absolute path to the file (e.g.,
            ``~/.config/opencode/skills/sdd-apply/SKILL.md``). Resolved at
            import time so callers can detect when the user has removed a
            SKILL.md directory (via the ``missing_file`` drift_kind).
        last_verified_checksum: 64-char lowercase hex SHA-256 digest of the
            canonicalized YAML frontmatter dict (per design D5:
            frontmatter-only to avoid whitespace false positives).
        owner: The catalog owner tag (e.g., ``"gentleman-programming"``);
            mirrors the ``owner`` convention from ``PROMPT_REGISTRY``.
    """

    skill_name: str
    surface: str
    expected_version: str
    expected_path: str
    last_verified_checksum: str
    owner: str


@dataclass(frozen=True)
class SkillDrift:
    """One drift finding from :func:`check_drift` (REQ-49 S1 + S2).

    Attributes:
        skill_name: The :class:`SkillEntry` ``skill_name`` that drifted.
        surface: The :class:`SkillEntry` ``surface`` (``"skill"`` or
            ``"prompt"``).
        expected_version: Version recorded at last verification (or the
            catalog ``expected_version`` when the sidecar has no entry yet).
        on_disk_version: Version parsed from the current on-disk frontmatter;
            ``""`` when the file is missing or frontmatter fails to parse.
        expected_checksum: SHA-256 recorded at last verification (or ``""``
            when the sidecar has no entry yet).
        on_disk_checksum: SHA-256 computed from the current on-disk
            frontmatter; ``""`` when the file is missing or frontmatter
            fails to parse.
        drift_kind: One of ``"version_mismatch"``, ``"checksum_mismatch"``,
            ``"missing_file"``, ``"frontmatter_parse_error"``.
    """

    skill_name: str
    surface: str
    expected_version: str
    on_disk_version: str
    expected_checksum: str
    on_disk_checksum: str
    drift_kind: str


class SkillVersionError(Exception):
    """Raised on missing or malformed YAML frontmatter (REQ-49 D5).

    Callers (typically :func:`check_drift`) wrap this in a
    :class:`SkillDrift` with ``drift_kind="frontmatter_parse_error"``
    rather than surfacing the raw exception, so the CLI can present the
    failure in a stable ``<skill>: <version>: <status>`` table format.
    """


SKILL_CATALOG: dict[str, SkillEntry] = {
    "sdd-init/skill": SkillEntry(
        skill_name="sdd-init",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-init/SKILL.md",
        last_verified_checksum="857cb68b23728dab73cd98406a6dcc8d26f89017e560baed70060a5c7a09a14c",
        owner="gentleman-programming",
    ),
    "sdd-init/prompt": SkillEntry(
        skill_name="sdd-init",
        surface="prompt",
        expected_version="3.0",
        expected_path="~/.config/opencode/prompts/sdd/sdd-init.md",
        last_verified_checksum="857cb68b23728dab73cd98406a6dcc8d26f89017e560baed70060a5c7a09a14c",
        owner="gentleman-programming",
    ),
    "sdd-explore/skill": SkillEntry(
        skill_name="sdd-explore",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-explore/SKILL.md",
        last_verified_checksum="b7fa42ec93e99973d33044139e13ad60cbf757eb2c02abc6f787be2e29e52601",
        owner="gentleman-programming",
    ),
    "sdd-explore/prompt": SkillEntry(
        skill_name="sdd-explore",
        surface="prompt",
        expected_version="3.0",
        expected_path="~/.config/opencode/prompts/sdd/sdd-explore.md",
        last_verified_checksum="b7fa42ec93e99973d33044139e13ad60cbf757eb2c02abc6f787be2e29e52601",
        owner="gentleman-programming",
    ),
    "sdd-propose/skill": SkillEntry(
        skill_name="sdd-propose",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-propose/SKILL.md",
        last_verified_checksum="0ebe13d7d3e9a76f59ef3f6769939f6f3b055a61ce93c17d38ab981f3ab76e00",
        owner="gentleman-programming",
    ),
    "sdd-propose/prompt": SkillEntry(
        skill_name="sdd-propose",
        surface="prompt",
        expected_version="3.0",
        expected_path="~/.config/opencode/prompts/sdd/sdd-propose.md",
        last_verified_checksum="0ebe13d7d3e9a76f59ef3f6769939f6f3b055a61ce93c17d38ab981f3ab76e00",
        owner="gentleman-programming",
    ),
    "sdd-design/skill": SkillEntry(
        skill_name="sdd-design",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-design/SKILL.md",
        last_verified_checksum="65b6cc3caca91ce595c5bc3f515f38a330e8945af0701c340756b6b19717b30e",
        owner="gentleman-programming",
    ),
    "sdd-design/prompt": SkillEntry(
        skill_name="sdd-design",
        surface="prompt",
        expected_version="3.0",
        expected_path="~/.config/opencode/prompts/sdd/sdd-design.md",
        last_verified_checksum="65b6cc3caca91ce595c5bc3f515f38a330e8945af0701c340756b6b19717b30e",
        owner="gentleman-programming",
    ),
    "sdd-spec/skill": SkillEntry(
        skill_name="sdd-spec",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-spec/SKILL.md",
        last_verified_checksum="2b925e472985d86d94287d1447f442f8d1ca2429004cff8cd0e158910217a7e6",
        owner="gentleman-programming",
    ),
    "sdd-spec/prompt": SkillEntry(
        skill_name="sdd-spec",
        surface="prompt",
        expected_version="3.0",
        expected_path="~/.config/opencode/prompts/sdd/sdd-spec.md",
        last_verified_checksum="2b925e472985d86d94287d1447f442f8d1ca2429004cff8cd0e158910217a7e6",
        owner="gentleman-programming",
    ),
    "sdd-tasks/skill": SkillEntry(
        skill_name="sdd-tasks",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-tasks/SKILL.md",
        last_verified_checksum="cbb194af9efe1a42a9c35009fac4249cc36f14cd21171c02e4d101f36c4c7fa4",
        owner="gentleman-programming",
    ),
    "sdd-tasks/prompt": SkillEntry(
        skill_name="sdd-tasks",
        surface="prompt",
        expected_version="3.0",
        expected_path="~/.config/opencode/prompts/sdd/sdd-tasks.md",
        last_verified_checksum="cbb194af9efe1a42a9c35009fac4249cc36f14cd21171c02e4d101f36c4c7fa4",
        owner="gentleman-programming",
    ),
    "sdd-apply/skill": SkillEntry(
        skill_name="sdd-apply",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-apply/SKILL.md",
        last_verified_checksum="4775286cf0553544af427ee43e21a8e7c722d427915d1e77c6dffcfa3bde247e",
        owner="gentleman-programming",
    ),
    "sdd-apply/prompt": SkillEntry(
        skill_name="sdd-apply",
        surface="prompt",
        expected_version="3.0",
        expected_path="~/.config/opencode/prompts/sdd/sdd-apply.md",
        last_verified_checksum="4775286cf0553544af427ee43e21a8e7c722d427915d1e77c6dffcfa3bde247e",
        owner="gentleman-programming",
    ),
    "sdd-verify/skill": SkillEntry(
        skill_name="sdd-verify",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-verify/SKILL.md",
        last_verified_checksum="384107722d6a09a03b4b0a782dcaa4959065037050139bc1357cb55703149ed8",
        owner="gentleman-programming",
    ),
    "sdd-verify/prompt": SkillEntry(
        skill_name="sdd-verify",
        surface="prompt",
        expected_version="3.0",
        expected_path="~/.config/opencode/prompts/sdd/sdd-verify.md",
        last_verified_checksum="384107722d6a09a03b4b0a782dcaa4959065037050139bc1357cb55703149ed8",
        owner="gentleman-programming",
    ),
    "sdd-archive/skill": SkillEntry(
        skill_name="sdd-archive",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-archive/SKILL.md",
        last_verified_checksum="5be1cae448c6583104fcc03d15eaa57ec401781a7b0ec9abf676a3dbc7ee4029",
        owner="gentleman-programming",
    ),
    "sdd-archive/prompt": SkillEntry(
        skill_name="sdd-archive",
        surface="prompt",
        expected_version="3.0",
        expected_path="~/.config/opencode/prompts/sdd/sdd-archive.md",
        last_verified_checksum="5be1cae448c6583104fcc03d15eaa57ec401781a7b0ec9abf676a3dbc7ee4029",
        owner="gentleman-programming",
    ),
    "sdd-onboard/skill": SkillEntry(
        skill_name="sdd-onboard",
        surface="skill",
        expected_version="3.0",
        expected_path="~/.config/opencode/skills/sdd-onboard/SKILL.md",
        last_verified_checksum="9ee8d00658a25d8b39377460145eeda8d2494bb275d30a24da4a79e28072e4a9",
        owner="gentleman-programming",
    ),
    "sdd-onboard/prompt": SkillEntry(
        skill_name="sdd-onboard",
        surface="prompt",
        expected_version="3.0",
        expected_path="~/.config/opencode/prompts/sdd/sdd-onboard.md",
        last_verified_checksum="9ee8d00658a25d8b39377460145eeda8d2494bb275d30a24da4a79e28072e4a9",
        owner="gentleman-programming",
    ),
}
"""20-entry catalog of OpenCode runtime sdd-* agent prompts.

Per design D6, the catalog covers BOTH surfaces for each of the 10 sdd-*
agents (``~/.config/opencode/skills/<name>/SKILL.md`` and
``~/.config/opencode/prompts/sdd/<name>.md``), keyed by
``<skill_name>/<surface>``. The catalog is statically defined (not
discovered at runtime) for deterministic drift detection.
"""


__all__ = [
    "FRONTMATTER_PATTERN",
    "SIDECAR_PATH",
    "SKILL_CATALOG",
    "SkillDrift",
    "SkillEntry",
    "SkillVersionError",
    "compute_frontmatter_sha256",
    "parse_frontmatter",
]


def compute_frontmatter_sha256(path: Path) -> str:
    """Compute SHA-256 of the canonicalized YAML frontmatter dict at ``path``.

    Per design D5 + OQ-5: parse the YAML block between ``---`` markers,
    canonicalize via JSON-dump with sorted keys + no whitespace, then hash
    the UTF-8 bytes. The body is intentionally IGNORED so a whitespace-only
    body edit does NOT trigger a false-positive drift signal.

    Args:
        path: The on-disk ``SKILL.md`` (or ``prompts/sdd/*.md``) file.

    Returns:
        A 64-char lowercase hex SHA-256 digest.

    Raises:
        SkillVersionError: When ``path`` has no YAML frontmatter, the YAML
            parses to a non-dict, or the file does not exist.
    """
    parsed = parse_frontmatter(path)
    canonical = json.dumps(
        parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_frontmatter(path: Path) -> dict[str, Any]:
    """Parse the YAML frontmatter block at ``path`` into a ``dict``.

    The block is delimited by ``---`` fences (see :data:`FRONTMATTER_PATTERN`).
    Non-dict YAML parses (e.g., a scalar at the top level) are rejected with
    :class:`SkillVersionError` so the caller can surface a uniform
    ``frontmatter_parse_error`` drift signal.

    Args:
        path: The on-disk file to parse.

    Returns:
        The parsed YAML mapping as a plain ``dict``. UTF-8 unicode is
        preserved (no normalization).

    Raises:
        SkillVersionError: When the file is missing, has no YAML frontmatter,
            or the parsed YAML is not a dict.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SkillVersionError(f"{path}: file not found") from exc
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        raise SkillVersionError(f"{path}: no YAML frontmatter found")
    try:
        parsed = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise SkillVersionError(f"{path}: YAML parse failed: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SkillVersionError(f"{path}: frontmatter is not a YAML dict")
    return parsed
