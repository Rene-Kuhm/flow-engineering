#!/usr/bin/env pwsh
# T4.5 smoke test — verify both old (deprecated alias) + new (canonical)
# drift CLI surfaces work end-to-end after Path A subcommand rename.
#
# Mirrors the design.md D4 contract: REQ-V1.2.4 ships a 1-release
# `deprecated=True` Click group alias for `flow drift-events` while
# promoting the canonical surface to `flow drift events {list,tail,stats}`.
# Alias REMOVED in v1.3 per the `SnapshotGraphMissing` v1.1 precedent.
#
# Run via:
#   uv run --frozen pwsh scripts/smoke_drift_cli_alias.ps1
#
# Expected exit code: 0 (all smoke checks pass)

$ErrorActionPreference = "Stop"

function Assert-Eq([string]$expected, [string]$actual, [string]$label) {
    if ($expected -eq $actual) {
        Write-Host ("[OK]   {0} = '{1}'" -f $label, $actual)
    } else {
        Write-Error ("[FAIL] {0}: expected '{1}', got '{2}'" -f $label, $expected, $actual)
    }
}

Write-Host "=== T4.5 smoke test: flow drift CLI alias coexistence ==="
Write-Host ""

# 1. Canonical `flow drift` group shows subcommand list (not positional dispatch).
$help = uv run --frozen flow drift --help 2>&1 | Out-String
Assert-Eq "True" ($help.Contains("Commands:")) "flow drift --help lists subcommands"

# 2. Canonical `flow drift run --help` exists (explicit subcommand form).
$runHelp = uv run --frozen flow drift run --help 2>&1 | Out-String
Assert-Eq "True" ($runHelp.Contains("CHANGE_NAME")) "flow drift run --help shows CHANGE_NAME arg"

# 3. Canonical `flow drift events list --help` works.
$listHelp = uv run --frozen flow drift events list --help 2>&1 | Out-String
Assert-Eq "True" ($listHelp.Contains("REQ-V1.0.2")) "flow drift events list --help shows REQ-V1.0.2"

# 4. Canonical `flow drift events tail --help` works.
$tailHelp = uv run --frozen flow drift events tail --help 2>&1 | Out-String
Assert-Eq "True" ($tailHelp.Contains("REQ-V1.0.3")) "flow drift events tail --help shows REQ-V1.0.3"

# 5. Canonical `flow drift events stats --help` works.
$statsHelp = uv run --frozen flow drift events stats --help 2>&1 | Out-String
Assert-Eq "True" ($statsHelp.Contains("REQ-V1.0.3")) "flow drift events stats --help shows REQ-V1.0.3"

Write-Host ""

# 6. Deprecated alias `flow drift-events --help` shows DEPRECATED marker.
$aliasHelp = uv run --frozen flow drift-events --help 2>&1 | Out-String
Assert-Eq "True" ($aliasHelp.Contains("DEPRECATED")) "flow drift-events --help marks DEPRECATED"

# 7. Deprecated alias `flow drift-events list --help` shows DEPRECATED alias marker.
$aliasListHelp = uv run --frozen flow drift-events list --help 2>&1 | Out-String
Assert-Eq "True" ($aliasListHelp.Contains("DEPRECATED alias")) "flow drift-events list --help marks as DEPRECATED alias"

# 8. Invoking deprecated alias emits DeprecationWarning at runtime.
$aliasListOut = uv run --frozen flow drift-events list --limit 3 2>&1 | Out-String
Assert-Eq "True" ($aliasListOut.Contains("DeprecationWarning")) "flow drift-events list runtime emits DeprecationWarning"

# 9. Deprecated alias tail + stats also emit DeprecationWarning at runtime.
$aliasTailOut = uv run --frozen flow drift-events tail --limit 2 2>&1 | Out-String
Assert-Eq "True" ($aliasTailOut.Contains("DeprecationWarning")) "flow drift-events tail runtime emits DeprecationWarning"

$aliasStatsOut = uv run --frozen flow drift-events stats 2>&1 | Out-String
Assert-Eq "True" ($aliasStatsOut.Contains("DeprecationWarning")) "flow drift-events stats runtime emits DeprecationWarning"

Write-Host ""

# 10. End-to-end canonical surface produces same JSON output as alias.
$canonicalJson = uv run --frozen flow drift events list --format json --limit 3 2>$null | Out-String
$aliasJson = uv run --frozen flow drift-events list --format json --limit 3 2>$null | Out-String
Assert-Eq $canonicalJson.Trim() $aliasJson.Trim() "canonical vs alias produce identical JSON output"

# 11. End-to-end canonical `flow drift events stats` produces aligned text table.
$statsOut = uv run --frozen flow drift events stats 2>$null | Out-String
Assert-Eq "True" ($statsOut.Contains("Event class") -or $statsOut.Contains("(none)")) "flow drift events stats renders aligned text table"

# 12. `flow --version` reports 1.2.0.
$versionOut = uv run --frozen flow --version 2>&1 | Out-String
Assert-Eq "True" ($versionOut.Contains("1.2.0")) "flow --version reports 1.2.0"

Write-Host ""
Write-Host "=== All T4.5 smoke checks passed ==="
Write-Host "Both canonical `flow drift events {list,tail,stats}` + deprecated `flow drift-events` alias coexist as designed (REQ-V1.2.4)."

exit 0