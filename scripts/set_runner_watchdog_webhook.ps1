param(
  [string]$WebhookUrl,
  [ValidateSet("User", "Machine")]
  [string]$Target = "User",
  [switch]$DryRun,
  [switch]$Json
)

$ErrorActionPreference = "Stop"

$variable = "FLOW_RUNNER_ALERT_WEBHOOK"
if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
  $secureWebhook = Read-Host "Enter webhook URL" -AsSecureString
  $WebhookUrl = [System.Net.NetworkCredential]::new("", $secureWebhook).Password
}

if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
  throw "WebhookUrl cannot be empty."
}

if ($WebhookUrl -notmatch "^https://") {
  throw "WebhookUrl must start with https://."
}

$hashBytes = [System.Security.Cryptography.SHA256]::HashData([System.Text.Encoding]::UTF8.GetBytes($WebhookUrl))
$fingerprint = (($hashBytes | Select-Object -First 6 | ForEach-Object { $_.ToString("x2") }) -join "")

$summary = [pscustomobject]@{
  variable = $variable
  target = $Target
  value_present = $true
  value_fingerprint = $fingerprint
  dry_run = [bool]$DryRun
  restart_note = "Restart shells and re-register or restart scheduled tasks that need to read the new environment variable."
}

if (-not $DryRun) {
  [Environment]::SetEnvironmentVariable($variable, $WebhookUrl, $Target)
}

if ($Json) {
  $summary | ConvertTo-Json -Depth 4
} else {
  $verb = if ($DryRun) { "Would set" } else { "Set" }
  Write-Host "$verb $variable for $Target environment."
  Write-Host "value fingerprint: $fingerprint"
  Write-Host $summary.restart_note
}
