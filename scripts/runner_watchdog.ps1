param(
  [string]$Repo = "Rene-Kuhm/flow-engineering",
  [string]$RunnerNamePattern = "actions.runner.*",
  [int]$RunLimit = 5,
  [int]$MaxCiAgeHours = 24,
  [string]$WebhookUrl = $env:FLOW_RUNNER_ALERT_WEBHOOK,
  [switch]$SkipGitHub,
  [switch]$WebhookTest,
  [switch]$WebhookDryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

function New-Check {
  param(
    [string]$Name,
    [string]$Status,
    [string]$Message
  )
  [pscustomobject]@{
    name = $Name
    status = $Status
    message = $Message
  }
}

$checks = @()

$services = @(Get-Service | Where-Object { $_.Name -like $RunnerNamePattern })
if ($services.Count -eq 0) {
  $checks += New-Check "runner_service" "critical" "No runner service matches '$RunnerNamePattern'."
} else {
  $badServices = @($services | Where-Object { $_.Status -ne "Running" -or $_.StartType -ne "Automatic" })
  if ($badServices.Count -gt 0) {
    $summary = ($badServices | ForEach-Object { "$($_.Name)=$($_.Status)/$($_.StartType)" }) -join ", "
    $checks += New-Check "runner_service" "critical" "Runner service unhealthy: $summary."
  } else {
    $summary = ($services | ForEach-Object { "$($_.Name)=$($_.Status)/$($_.StartType)" }) -join ", "
    $checks += New-Check "runner_service" "ok" "Runner service healthy: $summary."
  }
}

if ($SkipGitHub) {
  $checks += New-Check "github_ci" "skipped" "GitHub CI check skipped by -SkipGitHub."
} elseif (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  $checks += New-Check "github_ci" "warning" "GitHub CLI is not available on PATH."
} else {
  $runsJson = gh run list --repo $Repo --branch main --limit $RunLimit --json databaseId,workflowName,status,conclusion,createdAt,url 2>$null
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($runsJson)) {
    $checks += New-Check "github_ci" "warning" "Could not read GitHub Actions runs for $Repo."
  } else {
    $runs = @($runsJson | ConvertFrom-Json)
    $latestTests = @($runs | Where-Object { $_.workflowName -eq "tests" } | Select-Object -First 1)
    if ($latestTests.Count -eq 0) {
      $checks += New-Check "github_ci" "warning" "No recent tests workflow found in the last $RunLimit runs."
    } else {
      $run = $latestTests[0]
      $created = [datetime]$run.createdAt
      $ageHours = ((Get-Date).ToUniversalTime() - $created.ToUniversalTime()).TotalHours
      if ($run.status -ne "completed" -or $run.conclusion -ne "success") {
        $checks += New-Check "github_ci" "critical" "Latest tests run $($run.databaseId) is $($run.status)/$($run.conclusion): $($run.url)."
      } elseif ($ageHours -gt $MaxCiAgeHours) {
        $checks += New-Check "github_ci" "warning" ("Latest green tests run {0} is stale: {1:N1}h old." -f $run.databaseId, $ageHours)
      } else {
        $checks += New-Check "github_ci" "ok" ("Latest tests run {0} is green: {1}." -f $run.databaseId, $run.url)
      }
    }
  }
}

if ($WebhookTest) {
  $checks += New-Check "webhook_test" "warning" "Controlled webhook test payload requested."
}

$criticalCount = @($checks | Where-Object { $_.status -eq "critical" }).Count
$warningCount = @($checks | Where-Object { $_.status -eq "warning" }).Count
$overall = if ($criticalCount -gt 0) { "critical" } elseif ($warningCount -gt 0) { "warning" } else { "ok" }

$webhookConfigured = -not [string]::IsNullOrWhiteSpace($WebhookUrl)
$payload = [pscustomobject]@{
  checked_at = (Get-Date).ToUniversalTime().ToString("o")
  repo = $Repo
  overall = $overall
  checks = $checks
  webhook = [pscustomobject]@{
    configured = $webhookConfigured
    dry_run = [bool]$WebhookDryRun
    test = [bool]$WebhookTest
  }
}

if ($overall -ne "ok" -and $webhookConfigured -and -not $WebhookDryRun) {
  try {
    Invoke-RestMethod -Method Post -Uri $WebhookUrl -ContentType "application/json" -Body ($payload | ConvertTo-Json -Depth 5) | Out-Null
  } catch {
    $checks += New-Check "webhook" "warning" "Failed to post alert webhook: $($_.Exception.Message)"
    $payload = [pscustomobject]@{
      checked_at = $payload.checked_at
      repo = $payload.repo
      overall = $overall
      checks = $checks
      webhook = $payload.webhook
    }
  }
}

if ($Json) {
  $payload | ConvertTo-Json -Depth 5
} else {
  Write-Host "runner-watchdog: $overall"
  foreach ($check in $checks) {
    Write-Host ("{0}: {1} - {2}" -f $check.name, $check.status, $check.message)
  }
}

if ($WebhookDryRun) { exit 0 }
if ($overall -eq "critical") { exit 2 }
if ($overall -eq "warning") { exit 1 }
exit 0
