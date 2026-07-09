param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
  [string]$Repo = "Rene-Kuhm/flow-engineering",
  [string]$TaskName = "flow-engineering-runner-watchdog",
  [string]$RunnerNamePattern = "actions.runner.*",
  [int]$ScheduleMinutes = 15,
  [int]$MaxCiAgeHours = 24,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

$repoRootPath = (Resolve-Path -LiteralPath $RepoRoot).Path
$watchdogPath = Join-Path $repoRootPath "scripts/runner_watchdog.ps1"
if (-not (Test-Path -LiteralPath $watchdogPath)) {
  throw "runner watchdog script not found: $watchdogPath"
}

$pwshCommand = Get-Command pwsh -ErrorAction SilentlyContinue
if ($null -eq $pwshCommand) {
  $pwshCommand = Get-Command powershell -ErrorAction SilentlyContinue
}
if ($null -eq $pwshCommand) {
  throw "Neither pwsh nor powershell is available on PATH."
}

$arguments = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", ('"{0}"' -f $watchdogPath),
  "-Repo", ('"{0}"' -f $Repo),
  "-RunnerNamePattern", ('"{0}"' -f $RunnerNamePattern),
  "-MaxCiAgeHours", $MaxCiAgeHours
) -join " "

$summary = [pscustomobject]@{
  task_name = $TaskName
  schedule_minutes = $ScheduleMinutes
  executable = $pwshCommand.Source
  arguments = $arguments
  watchdog_path = $watchdogPath
  repo = $Repo
  dry_run = [bool]$DryRun
  webhook_source = "FLOW_RUNNER_ALERT_WEBHOOK environment variable"
}

if ($DryRun) {
  if ($Json) {
    $summary | ConvertTo-Json -Depth 4
  } else {
    Write-Host "runner-watchdog scheduled task dry-run"
    Write-Host "task: $TaskName"
    Write-Host "schedule: every $ScheduleMinutes minutes"
    Write-Host "command: $($pwshCommand.Source) $arguments"
    Write-Host "webhook: FLOW_RUNNER_ALERT_WEBHOOK environment variable"
  }
  exit 0
}

if ($ScheduleMinutes -lt 5) {
  throw "ScheduleMinutes must be >= 5 to avoid noisy alert loops."
}

$action = New-ScheduledTaskAction -Execute $pwshCommand.Source -Argument $arguments -WorkingDirectory $repoRootPath
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $ScheduleMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Out-of-band flow-engineering runner watchdog" -Force | Out-Null

if ($Json) {
  $summary | ConvertTo-Json -Depth 4
} else {
  Write-Host "Registered scheduled task: $TaskName"
  Write-Host "Runs every $ScheduleMinutes minutes."
  Write-Host "Webhook source: FLOW_RUNNER_ALERT_WEBHOOK environment variable"
}
