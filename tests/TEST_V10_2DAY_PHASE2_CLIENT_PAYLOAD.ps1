param(
  [string]$BaseUrl = "http://127.0.0.1:2294"
)
$ErrorActionPreference = "Stop"
Write-Host "=== V10 2-Day Phase 2 Client Payload Test ===" -ForegroundColor Cyan
function Get-Json($Url) {
  Write-Host "GET $Url" -ForegroundColor DarkCyan
  $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 20
  $txt = if ($r.Content -is [byte[]]) { [Text.Encoding]::UTF8.GetString($r.Content) } else { [string]$r.Content }
  try { return $txt | ConvertFrom-Json } catch { Write-Host $txt; throw "Invalid JSON from $Url" }
}
$health = Get-Json "$BaseUrl/api/health"
Write-Host "PASS: server reachable" -ForegroundColor Green
$status = Get-Json "$BaseUrl/api/v10phase2/status"
if (!$status.ok) { throw "Phase2 status not OK" }
Write-Host "PASS: Phase2 status OK" -ForegroundColor Green
$self = Get-Json "$BaseUrl/api/v10phase2/selftest"
if (!$self.ok) {
  $self | ConvertTo-Json -Depth 20 | Write-Host
  throw "Phase2 selftest failed"
}
$checks = $self.checks
foreach ($p in $checks.PSObject.Properties) {
  if (!$p.Value) { throw "Selftest check failed: $($p.Name)" }
  Write-Host "PASS: $($p.Name)" -ForegroundColor Green
}
# trigger reprocess, should not fail even with no machines
$rp = Get-Json "$BaseUrl/api/v10phase2/reprocess"
if ($rp.ok -eq $false) {
  $rp | ConvertTo-Json -Depth 10 | Write-Host
  throw "Reprocess latest failed"
}
Write-Host "PASS: latest reprocess executed" -ForegroundColor Green
# If phase1 exists, check machines API shape but do not require machines to exist.
try {
  $machines = Get-Json "$BaseUrl/api/v10final/machines"
  if ($machines.ok -eq $false) { throw "v10final machines returned ok false" }
  Write-Host "PASS: v10final machines API available; count=$($machines.count)" -ForegroundColor Green
} catch {
  Write-Host "WARN: v10final machines API not available yet: $($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host "=== PHASE2 TEST PASS ===" -ForegroundColor Green
