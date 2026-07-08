param(
  [string]$Repo = "Rene-Kuhm/flow-engineering",
  [string]$RunnerNamePattern = "actions.runner.*",
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [int]$RunLimit = 3
)

$ErrorActionPreference = "Stop"

function Write-Section {
  param([string]$Title)
  Write-Host ""
  Write-Host "== $Title =="
}

function Write-KeyValue {
  param(
    [string]$Key,
    [string]$Value
  )
  Write-Host ("{0}: {1}" -f $Key, $Value)
}

Write-Section "Runner service"
$services = Get-Service | Where-Object { $_.Name -like $RunnerNamePattern }
if (-not $services) {
  Write-KeyValue "status" "missing"
} else {
  $services |
    Select-Object Status, StartType, Name, DisplayName |
    Format-Table -AutoSize
}

Write-Section "Startup fallback"
$startupFallback = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup\flow-engineering-actions-runner.cmd"
Write-KeyValue "path" $startupFallback
Write-KeyValue "exists" ([string](Test-Path $startupFallback))

Write-Section "Latest CI runs"
if (Get-Command gh -ErrorAction SilentlyContinue) {
  gh run list --repo $Repo --limit $RunLimit
} else {
  Write-KeyValue "gh" "not found on PATH"
}

Write-Section "Active OpenSpec changes"
$changesRoot = Join-Path $RepoRoot "openspec\changes"
if (Test-Path $changesRoot) {
  Get-ChildItem $changesRoot -Directory |
    Where-Object { $_.Name -ne "archive" } |
    Select-Object Name, LastWriteTime |
    Format-Table -AutoSize
} else {
  Write-KeyValue "openspec changes" "missing"
}

Write-Section "Follow-up audit"
$followUpAudit = Join-Path $RepoRoot "docs\follow-up-audit.md"
if (Test-Path $followUpAudit) {
  Select-String -Path $followUpAudit -Pattern "Active guardrail|No urgent blocker|Resolved|Audit-only" |
    ForEach-Object { $_.Line }
} else {
  Write-KeyValue "follow-up audit" "missing"
}

Write-Section "Memory maintenance"
Write-Host "Review docs/memory-maintenance.md before promoting old Engram/SDD follow-ups."
