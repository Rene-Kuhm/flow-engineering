param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
  [string]$Repo = "Rene-Kuhm/flow-engineering",
  [string]$TaskName = "flow-engineering-monthly-maintenance",
  [int]$DayOfMonth = 1,
  [string]$At = "09:00",
  [switch]$SkipGitHub,
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

if ($DayOfMonth -lt 1 -or $DayOfMonth -gt 31) {
  throw "DayOfMonth must be between 1 and 31."
}

if ($At -notmatch "^\d{2}:\d{2}$") {
  throw "At must use HH:mm format."
}

$repoRootPath = (Resolve-Path -LiteralPath $RepoRoot).Path
$maintenancePath = Join-Path $repoRootPath "scripts/monthly_maintenance.ps1"
if (-not (Test-Path -LiteralPath $maintenancePath)) {
  throw "monthly maintenance script not found: $maintenancePath"
}

$pwshCommand = Get-Command pwsh -ErrorAction SilentlyContinue
if ($null -eq $pwshCommand) {
  $pwshCommand = Get-Command powershell -ErrorAction SilentlyContinue
}
if ($null -eq $pwshCommand) {
  throw "Neither pwsh nor powershell is available on PATH."
}

$scriptArguments = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", ('"{0}"' -f $maintenancePath),
  "-Repo", ('"{0}"' -f $Repo)
)
if ($SkipGitHub) {
  $scriptArguments += "-SkipGitHub"
}
$arguments = $scriptArguments -join " "
$taskRunCommand = ('"{0}" {1}' -f $pwshCommand.Source, $arguments)

$summary = [pscustomobject]@{
  task_name = $TaskName
  schedule = "monthly"
  day_of_month = $DayOfMonth
  at = $At
  executable = $pwshCommand.Source
  arguments = $arguments
  maintenance_path = $maintenancePath
  repo = $Repo
  skip_github = [bool]$SkipGitHub
  dry_run = [bool]$DryRun
}

if ($DryRun) {
  if ($Json) {
    $summary | ConvertTo-Json -Depth 4
  } else {
    Write-Host "monthly-maintenance scheduled task dry-run"
    Write-Host "task: $TaskName"
    Write-Host "schedule: day $DayOfMonth of every month at $At"
    Write-Host "command: $taskRunCommand"
  }
  exit 0
}

$schtasks = Get-Command schtasks.exe -ErrorAction SilentlyContinue
if ($null -eq $schtasks) {
  throw "schtasks.exe is required to register a monthly scheduled task."
}

& $schtasks.Source /Create /F /TN $TaskName /SC MONTHLY /D $DayOfMonth /ST $At /TR $taskRunCommand | Out-Null

if ($Json) {
  $summary | ConvertTo-Json -Depth 4
} else {
  Write-Host "Registered scheduled task: $TaskName"
  Write-Host "Runs monthly on day $DayOfMonth at $At."
}
