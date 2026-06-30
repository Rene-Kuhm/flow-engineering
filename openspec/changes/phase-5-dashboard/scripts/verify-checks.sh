#!/usr/bin/env bash
# verify-checks.sh — 8 structural checks for the workspace root spec.
#
# Phase 5 dashboard (phase-5-dashboard) change — see
# ``openspec/changes/phase-5-dashboard/design.md`` §8 for the authoritative
# contract. This script is the executable verification surface used by
# ``sdd-verify`` (T6.1) and the AC2/AC14 acceptance criteria.
#
# Exit codes:
#   0  all 8 checks PASS
#   1  any check FAILED (diagnostic printed to stderr)
#
# Usage:
#   bash openspec/changes/phase-5-dashboard/scripts/verify-checks.sh
#
# The first 7 checks are inherited from ``workspace-capability-bootstrap``
# (design #492) and re-validated against the post-Phase-5 root spec. Check 8
# is NEW — it guards the 6 ``REQ-WORKSPACE-DASHBOARD-*`` blocks against
# silent placeholder regression or wrong ``Source:`` paths.

set -uo pipefail

# Resolve a working Python interpreter.
#
# The WindowsApps ``python.exe`` / ``python3.exe`` are Microsoft Store stubs
# that error out instead of running real Python. We probe candidates in
# order, accepting the first that reports a real version.
_resolve_python() {
    local candidates=()
    if [[ -n "${PYTHON:-}" ]]; then
        candidates+=("${PYTHON}")
    fi
    # Common names on PATH.
    candidates+=(python3 python python3.exe python.exe)
    # Windows-native Python at the standard installer location.
    if [[ -n "${LOCALAPPDATA:-}" && -x "${LOCALAPPDATA}/Programs/Python/Python312/python.exe" ]]; then
        candidates+=("${LOCALAPPDATA}/Programs/Python/Python312/python.exe")
    fi
    if [[ -n "${PROGRAMFILES:-}" && -x "${PROGRAMFILES}/Python312/python.exe" ]]; then
        candidates+=("${PROGRAMFILES}/Python312/python.exe")
    fi
    # uv-managed Python is the project's preferred interpreter.
    if command -v uv >/dev/null 2>&1; then
        local uv_py
        uv_py="$(uv run --frozen --no-project python -c "import sys; print(sys.executable)" 2>/dev/null || true)"
        if [[ -n "$uv_py" && -x "$uv_py" ]]; then
            candidates+=("$uv_py")
        fi
    fi

    for cand in "${candidates[@]}"; do
        if [[ -x "$cand" ]] && "$cand" -c "import sys; assert sys.version_info >= (3, 11)" >/dev/null 2>&1; then
            PY="$cand"
            return 0
        fi
        # ``command -v`` style lookup.
        if command -v "$cand" >/dev/null 2>&1; then
            local resolved
            resolved="$(command -v "$cand")"
            if [[ -x "$resolved" ]] && "$resolved" -c "import sys; assert sys.version_info >= (3, 11)" >/dev/null 2>&1; then
                PY="$resolved"
                return 0
            fi
        fi
    done
    return 1
}

if ! _resolve_python; then
    echo "FATAL: no working python interpreter found (set PYTHON=/path/to/python.exe)" >&2
    exit 2
fi

REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
SPEC_FILE="${SPEC_FILE:-${REPO_ROOT}/openspec/specs/workspace/spec.md}"
DASHBOARD_DELTA="${DASHBOARD_DELTA:-${REPO_ROOT}/openspec/changes/phase-5-dashboard/specs/workspace-dashboard/spec.md}"

FAIL_COUNT=0

# ---- Helpers ----------------------------------------------------------------

fail() {
    # Print a single FAIL diagnostic and increment the failure counter.
    # Args: $1 = diagnostic message
    echo "FAIL: $1" >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

pass() {
    # Print a single PASS diagnostic. Args: $1 = check description
    echo "PASS: $1"
}

# ---- Check 1 ----------------------------------------------------------------
# Every root REQ has exactly one ``Source:`` line.
# Expected: 12/12 (was 7/7; placeholder REQ replaced by 6 dashboard REQs).

check_1_root_reqs_source_lines() {
    local spec="$1"
    local expected=12

    # Extract every ``### REQ-...`` block and count ``**Source:**`` occurrences.
    # Output is one line per REQ in the form ``REQ-ID<TAB>count``.
    local counts
    counts=$("$PY" - "$spec" <<'PY'
import re, sys, pathlib
spec = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
blocks = re.findall(r"^### (REQ-[A-Z0-9-]+)\b(.*?)(?=^### |\Z)",
                    spec, re.MULTILINE | re.DOTALL)
for req, body in blocks:
    n = body.count("**Source:**")
    print(f"{req}\t{n}")
PY
)

    local bad
    bad=$(echo "$counts" | awk -F'\t' '$2 != 1 { print $1 " has " $2 " Source: lines" }')
    if [[ -n "$bad" ]]; then
        fail "Check 1 (root REQ Source: lines): $bad"
        return
    fi

    local total
    total=$(echo "$counts" | wc -l | tr -d ' ')
    if [[ "$total" != "$expected" ]]; then
        fail "Check 1 (root REQ count): expected ${expected}, got ${total}"
        return
    fi

    pass "Check 1 — ${expected}/${expected} root REQs each have exactly one Source: line"
}

# ---- Check 2 ----------------------------------------------------------------
# Every ``Source:`` path exists on disk.

check_2_source_paths_exist() {
    local spec="$1"

    local missing
    missing=$("$PY" - "$spec" <<'PY'
import re, sys, pathlib
spec = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
paths = set(re.findall(r"\*\*Source:\*\* `([^`]+)`", spec))
for p in sorted(paths):
    if not pathlib.Path(p).exists():
        print(p)
PY
)

    if [[ -n "$missing" ]]; then
        fail "Check 2 (Source: paths): missing $missing"
        return
    fi

    pass "Check 2 — all Source: paths exist on disk"
}

# ---- Check 3 ----------------------------------------------------------------
# Every cited ``REQ-ID`` exists in the cited delta spec.

check_3_cited_req_ids_exist() {
    local spec="$1"

    "$PY" - "$spec" <<'PY'
import re, sys, pathlib
spec_path = pathlib.Path(sys.argv[1])
spec = spec_path.read_text(encoding="utf-8")
blocks = re.findall(r"^### (REQ-[A-Z0-9-]+)\b(.*?)(?=^### |\Z)",
                    spec, re.MULTILINE | re.DOTALL)
fail = 0
for req, body in blocks:
    src = re.search(r"\*\*Source:\*\* `([^`]+)`\s*(?:→\s*)?(.*)", body)
    if not src:
        continue
    path, ids_blob = src.group(1), src.group(2)
    if not pathlib.Path(path).exists():
        print(f"FAIL: {req} cites {path} but the file is missing")
        fail = 1
        continue
    ids = re.findall(r"REQ-[A-Z][A-Z0-9-]*", ids_blob)
    src_text = pathlib.Path(path).read_text(encoding="utf-8")
    for rid in ids:
        # Match either ``### Requirement: <rid>`` (delta-internal style) or
        # ``### REQ-...`` (root REQ style — for cross-deltabootstraps).
        pattern = rf"^### (?:Requirement:\s+)?{re.escape(rid)}\b"
        if not re.search(pattern, src_text, re.MULTILINE):
            print(f"FAIL: {req} cites {rid} but {path} does not define it")
            fail = 1
sys.exit(fail)
PY
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        fail "Check 3 (cited REQ-IDs exist in cited delta spec) — see diagnostics above"
        return
    fi

    pass "Check 3 — every cited REQ-ID exists in its cited delta spec"
}

# ---- Check 4 ----------------------------------------------------------------
# Cross-Impact mentions ``flow-where-cross-project-capability-merge``.

check_4_cross_impact_mentions_merge() {
    local spec="$1"

    if ! grep -F "flow-where-cross-project-capability-merge" "$spec" >/dev/null; then
        fail "Check 4 (Cross-Impact must mention flow-where-cross-project-capability-merge)"
        return
    fi

    pass "Check 4 — Cross-Impact mentions flow-where-cross-project-capability-merge"
}

# ---- Check 5 ----------------------------------------------------------------
# §7 Future Changes mentions ``workspace-dashboard``.

check_5_future_changes_dashboard() {
    local spec="$1"

    if ! grep -F "workspace-dashboard" "$spec" >/dev/null; then
        fail "Check 5 (§7 Future Changes must mention workspace-dashboard)"
        return
    fi

    pass "Check 5 — §7 Future Changes mentions workspace-dashboard"
}

# ---- Check 6 ----------------------------------------------------------------
# §8 Drift Detection footer present.

check_6_drift_detection_footer() {
    local spec="$1"

    if ! grep -F "Drift Detection" "$spec" >/dev/null; then
        fail "Check 6 (§8 Drift Detection footer must be present)"
        return
    fi

    pass "Check 6 — §8 Drift Detection footer present"
}

# ---- Check 7 ----------------------------------------------------------------
# "Family index" callout in first 10 lines.

check_7_family_index_in_first_10() {
    local spec="$1"

    if ! head -n 10 "$spec" | grep -F "Family index" >/dev/null; then
        fail "Check 7 ('Family index, not canonical source' callout must appear in the first 10 lines)"
        return
    fi

    pass "Check 7 — 'Family index' callout in the first 10 lines"
}

# ---- Check 8 (NEW) ----------------------------------------------------------
# Every ``REQ-WORKSPACE-DASHBOARD-*`` block has a Source: pointing to the
# dashboard delta spec. Guards against placeholder regression and wrong paths.

check_8_dashboard_reqs_source_path() {
    local spec="$1"
    local expected_suffix="phase-5-dashboard/specs/workspace-dashboard/spec.md"

    "$PY" - "$spec" "$expected_suffix" <<'PY'
import re, sys, pathlib
spec = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
expected_suffix = sys.argv[2]
# Find every REQ-WORKSPACE-DASHBOARD-* block.
blocks = re.findall(r"^### (REQ-WORKSPACE-DASHBOARD-[A-Z0-9-]+)\b(.*?)(?=^### |\Z)",
                    spec, re.MULTILINE | re.DOTALL)
fail = 0
for req, body in blocks:
    src = re.search(r"\*\*Source:\*\* `([^`]+)`", body)
    if not src:
        print(f"FAIL: {req} has no Source: path")
        fail = 1
        continue
    if expected_suffix not in src.group(1):
        print(f"FAIL: {req} Source: path {src.group(1)} does not point to dashboard delta spec")
        fail = 1
sys.exit(fail)
PY
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        fail "Check 8 (dashboard REQ Source: paths) — see diagnostics above"
        return
    fi

    pass "Check 8 — every dashboard REQ Source: points to the dashboard delta spec"
}

# ---- Main -------------------------------------------------------------------

if [[ ! -f "$SPEC_FILE" ]]; then
    echo "FATAL: spec file not found: $SPEC_FILE" >&2
    exit 2
fi

echo "Running 8 verify checks against: $SPEC_FILE"
echo

check_1_root_reqs_source_lines "$SPEC_FILE"
check_2_source_paths_exist "$SPEC_FILE"
check_3_cited_req_ids_exist "$SPEC_FILE"
check_4_cross_impact_mentions_merge "$SPEC_FILE"
check_5_future_changes_dashboard "$SPEC_FILE"
check_6_drift_detection_footer "$SPEC_FILE"
check_7_family_index_in_first_10 "$SPEC_FILE"
check_8_dashboard_reqs_source_path "$SPEC_FILE"

echo
if [[ $FAIL_COUNT -gt 0 ]]; then
    echo "FAILED: ${FAIL_COUNT} check(s) failed"
    exit 1
fi

echo "ALL 8 CHECKS PASSED"
exit 0