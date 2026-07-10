param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
  [string]$Repo = "Rene-Kuhm/flow-engineering",
  [switch]$SkipGitHub,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

$repoRootPath = (Resolve-Path -LiteralPath $RepoRoot).Path
$healthScript = Join-Path $repoRootPath "scripts/system_health.ps1"
$followUpAudit = Join-Path $repoRootPath "docs/follow-up-audit.md"
$memoryPolicy = Join-Path $repoRootPath "docs/memory-maintenance.md"

foreach ($required in @($healthScript, $followUpAudit, $memoryPolicy)) {
  if (-not (Test-Path -LiteralPath $required)) {
    throw "Required maintenance artifact missing: $required"
  }
}

function Invoke-Step {
  param(
    [string]$Name,
    [scriptblock]$Action
  )
  try {
    $output = & $Action *>&1 | Out-String
    [pscustomobject]@{ name = $Name; status = "ok"; output = $output.Trim() }
  } catch {
    [pscustomobject]@{ name = $Name; status = "failed"; output = $_.Exception.Message }
  }
}

$steps = @()
$steps += Invoke-Step "git_status" { git -C $repoRootPath status --short }
$steps += Invoke-Step "system_health" {
  if ($SkipGitHub) {
    & $healthScript -RepoRoot $repoRootPath -SkipGitHub
  } else {
    & $healthScript -RepoRoot $repoRootPath -RunLimit 5
  }
}
$steps += Invoke-Step "follow_up_audit" {
  Select-String -Path $followUpAudit -Pattern "No urgent blocker remains|Active guardrail|Resolved" | ForEach-Object { $_.Line }
}
$steps += Invoke-Step "memory_policy" {
  Select-String -Path $memoryPolicy -Pattern "Monthly audit checklist|Promotion test" | ForEach-Object { $_.Line }
}

$failed = @($steps | Where-Object { $_.status -ne "ok" })
$payload = [pscustomobject]@{
  checked_at = (Get-Date).ToUniversalTime().ToString("o")
  repo = $Repo
  repo_root = $repoRootPath
  overall = if ($failed.Count -gt 0) { "failed" } else { "ok" }
  steps = $steps
}

if ($Json) {
  $payload | ConvertTo-Json -Depth 5
} else {
  Write-Host "monthly-maintenance: $($payload.overall)"
  foreach ($step in $steps) {
    Write-Host "== $($step.name): $($step.status) =="
    if (-not [string]::IsNullOrWhiteSpace($step.output)) {
      Write-Host $step.output
    }
  }
}

if ($failed.Count -gt 0) { exit 1 }
exit 0
