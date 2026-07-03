param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 Software Tab 2278 Read-Only Live Test ===" -ForegroundColor Cyan
function Get-Text($Url){
  $r = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 20
  if($r.Content -is [byte[]]){ return [Text.Encoding]::UTF8.GetString($r.Content) }
  return [string]$r.Content
}
function Get-Json($Url){
  $txt = Get-Text $Url
  try { return $txt | ConvertFrom-Json } catch { throw "Non-JSON from $Url : $($txt.Substring(0,[Math]::Min(220,$txt.Length)))" }
}
$idx = Get-Text "$BaseUrl/"
foreach($n in @("V10_SOFTWARE_2278_READONLY_MARKER","Software Intelligence","Created by Sagar Kerhalkar")){
  if($idx -notlike "*$n*"){ throw "index missing $n" }
}
Write-Host "PASS: index has software markers" -ForegroundColor Green
$js = Invoke-WebRequest "$BaseUrl/v10_software_2278_readonly.js" -UseBasicParsing -TimeoutSec 20
if($js.StatusCode -ne 200){ throw "software js missing" }
Write-Host "PASS: JS available" -ForegroundColor Green
$status = Get-Json "$BaseUrl/api/v10/source2278/software/status"
if(-not $status.ok){ throw "software status not ok: $($status | ConvertTo-Json -Depth 5)" }
if(-not $status.no_write_to_2278){ throw "software connector must be read-only" }
if([int]$status.machines_checked -lt 1){ throw "software status machines_checked < 1" }
Write-Host "PASS: status ok, machines_checked=$($status.machines_checked), reported_software_total=$($status.reported_software_count_total)" -ForegroundColor Green
$list = Get-Json "$BaseUrl/api/v10/source2278/software?limit=10&with_items=1"
if(-not $list.ok){ throw "software list not ok" }
if([int]$list.count_machines -lt 1){ throw "software list has no machines" }
Write-Host "PASS: list ok, machines=$($list.count_machines), software_rows=$($list.count_software_rows)" -ForegroundColor Green
$csv = Invoke-WebRequest "$BaseUrl/api/v10/source2278/software/export.csv" -UseBasicParsing -TimeoutSec 30
if($csv.StatusCode -ne 200){ throw "CSV export failed" }
Write-Host "PASS: CSV export available" -ForegroundColor Green
# Existing 2278 notification simulation must remain if previous read-only package is installed.
try {
  $nt = Get-Json "$BaseUrl/api/v10/source2278/notification-test"
  if($nt.ok){ Write-Host "PASS: notification read-only simulation still works, simulated_alerts=$($nt.simulated_alerts_count)" -ForegroundColor Green }
} catch {
  Write-Host "WARN: notification-test endpoint not available in this V10 instance: $($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host "=== V10 SOFTWARE TAB 2278 READ-ONLY LIVE TEST PASS ===" -ForegroundColor Green
