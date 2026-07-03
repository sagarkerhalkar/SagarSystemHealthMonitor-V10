param(
  [string]$BaseUrl = "http://127.0.0.1:2294"
)
$ErrorActionPreference = "Stop"
Write-Host "=== V10 2-Day Phase 2 Client Payload Test v4 ===" -ForegroundColor Cyan

function Get-Json($Url) {
  Write-Host "GET $Url" -ForegroundColor DarkCyan
  $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 30
  $txt = if ($r.Content -is [byte[]]) { [Text.Encoding]::UTF8.GetString($r.Content) } else { [string]$r.Content }
  if ([string]::IsNullOrWhiteSpace($txt)) { throw "Empty response from $Url" }
  try { return $txt | ConvertFrom-Json } catch { Write-Host $txt; throw "Invalid JSON from $Url" }
}

# Health only proves server is reachable. Do not enforce old/new schema.
try {
  $null = Get-Json "$BaseUrl/api/health"
  Write-Host "PASS: server reachable" -ForegroundColor Green
} catch {
  throw "Server not reachable at $BaseUrl. Start V10 on port 2294 first. Details: $($_.Exception.Message)"
}

$status = Get-Json "$BaseUrl/api/v10phase2/status"
if ($status.ok -eq $false -or !$status.phase) {
  $status | ConvertTo-Json -Depth 20 | Write-Host
  throw "Phase2 status not OK or normalizer not loaded"
}
Write-Host "PASS: Phase2 status OK; version=$($status.version)" -ForegroundColor Green

$self = Get-Json "$BaseUrl/api/v10phase2/selftest"
if ($self.ok -ne $true) {
  Write-Host "FAILED CHECKS:" -ForegroundColor Red
  if ($self.failed_checks) { $self.failed_checks | ForEach-Object { Write-Host " - $_" -ForegroundColor Red } }
  Write-Host "CHECK OBJECT:" -ForegroundColor Yellow
  $self.checks | ConvertTo-Json -Depth 20 | Write-Host
  Write-Host "SUMMARY:" -ForegroundColor Yellow
  $self.summary | ConvertTo-Json -Depth 20 | Write-Host
  throw "Phase2 selftest failed"
}

$checks = $self.checks
foreach ($p in $checks.PSObject.Properties) {
  if ($p.Value -ne $true) { throw "Selftest check failed: $($p.Name)" }
  Write-Host "PASS: $($p.Name)" -ForegroundColor Green
}

$rp = Get-Json "$BaseUrl/api/v10phase2/reprocess"
if ($rp.ok -eq $false) {
  $rp | ConvertTo-Json -Depth 20 | Write-Host
  throw "Reprocess latest failed"
}
Write-Host "PASS: latest reprocess executed; rows=$($rp.updated_latest_rows)" -ForegroundColor Green

try {
  $machines = Get-Json "$BaseUrl/api/v10final/machines"
  if ($machines.ok -eq $false) { throw "v10final machines returned ok false" }
  Write-Host "PASS: v10final machines API available; count=$($machines.count)" -ForegroundColor Green
} catch {
  Write-Host "WARN: v10final machines API not available yet: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "=== PHASE2 TEST PASS ===" -ForegroundColor Green
