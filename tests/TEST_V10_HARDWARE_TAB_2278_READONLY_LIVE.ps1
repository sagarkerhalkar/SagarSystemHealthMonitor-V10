
param([string]$BaseUrl = "http://127.0.0.1:2294")
$ErrorActionPreference = "Stop"
Write-Host "=== V10 Hardware Tab 2278 Read-Only Live Test ===" -ForegroundColor Cyan
function Convert-ContentToText($Content){
  if($null -eq $Content){ return "" }
  if($Content -is [byte[]]){ return [System.Text.Encoding]::UTF8.GetString($Content) }
  if($Content -is [System.Array] -and $Content.Count -gt 0 -and $Content[0] -is [byte]){ return [System.Text.Encoding]::UTF8.GetString([byte[]]$Content) }
  return [string]$Content
}
function Get-Text($Url){
  $r = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 25
  $txt = Convert-ContentToText $r.Content
  if($txt.Length -gt 0){ return $txt }
  return Convert-ContentToText $r.RawContent
}
function Get-Json($Url){
  try { return Invoke-RestMethod $Url -UseBasicParsing -TimeoutSec 30 } catch {
    $txt = Get-Text $Url
    try { return $txt | ConvertFrom-Json } catch { throw "Non-JSON from $Url : $($txt.Substring(0,[Math]::Min(220,$txt.Length)))" }
  }
}
$index = Get-Text "$BaseUrl/"
foreach($n in @("v10_hardware_2278_readonly.js","v10_hardware_2278_readonly.css","Live Hardware from 2278","Created by Sagar Kerhalkar")){
  if($index -notlike "*$n*"){ throw "index missing $n" }
}
Write-Host "PASS: index has hardware UI markers" -ForegroundColor Green
$js = Get-Text "$BaseUrl/v10_hardware_2278_readonly.js?v=test"
foreach($n in @("Live Hardware from 2278","api/v10/source2278/hardware","notification-test","Download CSV")){
  if($js -notlike "*$n*"){ throw "JS missing $n" }
}
Write-Host "PASS: JS available" -ForegroundColor Green
$status = Get-Json "$BaseUrl/api/v10/source2278/hardware/status"
if($status.ok -ne $true){ throw "hardware status not ok" }
if($status.no_write_to_2278 -ne $true){ throw "no_write_to_2278 not true" }
if([int]$status.machines_checked -lt 1){ throw "hardware status machines_checked < 1" }
Write-Host "PASS: hardware status ok, machines: $($status.machines_checked)" -ForegroundColor Green
$list = Get-Json "$BaseUrl/api/v10/source2278/hardware?limit=100"
if($list.ok -ne $true){ throw "hardware list not ok" }
$rows = @($list.machines)
if($rows.Count -lt 1){ throw "hardware list empty" }
$first = $rows[0]
foreach($k in @("machine_id","hostname","cpu_percent","ram_total_gb","disk_max_percent","gpu_count","usb_count","hardware_completeness_percent")){
  if($null -eq $first.$k){ throw "first hardware row missing $k" }
}
Write-Host "PASS: hardware list has required fields, rows: $($rows.Count)" -ForegroundColor Green
$notify = Get-Json "$BaseUrl/api/v10/source2278/notification-test"
if($notify.ok -ne $true){ throw "notification test not ok" }
if([int]$notify.rules_count -lt 1){ throw "notification rules count < 1" }
Write-Host "PASS: notification test still working, rules: $($notify.rules_count), simulated alerts: $($notify.simulated_alerts_count)" -ForegroundColor Green
$csv = Invoke-WebRequest "$BaseUrl/api/v10/source2278/hardware/export.csv" -UseBasicParsing -TimeoutSec 30
$csvText = Convert-ContentToText $csv.Content
foreach($h in @("machine_id","hostname","serial_number","cpu_name","ram_total_gb","disk_max_percent","gpu_count","usb_count")){
  if($csvText -notlike "*$h*"){ throw "hardware CSV missing header $h" }
}
Write-Host "PASS: hardware CSV export available" -ForegroundColor Green
Write-Host "=== V10 HARDWARE TAB 2278 READ-ONLY LIVE TEST PASS ===" -ForegroundColor Green
