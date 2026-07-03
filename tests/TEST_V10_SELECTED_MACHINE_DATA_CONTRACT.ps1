param(
  [string]$BaseUrl = "http://127.0.0.1:2294",
  [string]$App = "D:\SagarMonitor_V10_CleanBuild"
)
$ErrorActionPreference = "Stop"
Write-Host "=== V10 Selected-Machine Data Contract Test ===" -ForegroundColor Cyan
function Get-Json($Url, $Timeout=25){
  try { return Invoke-RestMethod $Url -TimeoutSec $Timeout }
  catch { throw "GET failed: $Url -> $($_.Exception.Message)" }
}
$idx = (Invoke-WebRequest "$BaseUrl/?selectedContract=1" -UseBasicParsing -TimeoutSec 20).Content
foreach($needle in @("v10_selected_machine_contract_ui.js","v10_selected_machine_contract_ui.css","V10_SELECTED_MACHINE_DATA_CONTRACT")){
  if($idx -notlike "*$needle*"){ throw "index missing $needle" }
}
Write-Host "PASS: index has selected-machine contract UI" -ForegroundColor Green
$list = Get-Json "$BaseUrl/api/v10/selected-machine/list" 25
if(-not $list.ok){ throw "selected list not ok" }
if([int]$list.client_machines -lt 1){ throw "no client machines found" }
Write-Host "PASS: selected-machine list ok clients=$($list.client_machines) fresh=$($list.fresh_clients) server=$($list.monitor_server_count)" -ForegroundColor Green
$machines = @($list.machines | Where-Object { -not $_.is_monitor_server } | Select-Object -First 3)
if($machines.Count -lt 2){ throw "need at least 2 non-server machines to prove selection" }
foreach($m in $machines){
  $mid = [uri]::EscapeDataString([string]$m.machine_id)
  $h = Get-Json "$BaseUrl/api/v10/selected-machine/hardware?machine_id=$mid" 25
  if(-not $h.ok){ throw "hardware not ok for $($m.machine_id)" }
  if([string]$h.returned_machine_id -ne [string]$m.machine_id){ throw "machine_id contract failed requested=$($m.machine_id) returned=$($h.returned_machine_id)" }
  if(-not $h.machine.hostname){ throw "hostname missing for $($m.machine_id)" }
  if(-not $h.machine.disks){ throw "disk array missing for $($m.hostname)" }
  if(-not $h.machine.network_adapters){ throw "network array missing for $($m.hostname)" }
  $s = Get-Json "$BaseUrl/api/v10/selected-machine/software?machine_id=$mid&limit=2000" 35
  if(-not $s.ok){ throw "software not ok for $($m.machine_id)" }
  if([string]$s.returned_machine_id -ne [string]$m.machine_id){ throw "software machine_id contract failed requested=$($m.machine_id) returned=$($s.returned_machine_id)" }
  $n = Get-Json "$BaseUrl/api/v10/selected-machine/network?machine_id=$mid" 25
  if([string]$n.returned_machine_id -ne [string]$m.machine_id){ throw "network machine_id contract failed requested=$($m.machine_id) returned=$($n.returned_machine_id)" }
  Write-Host "PASS: selected $($m.hostname) -> hw/sw/network same machine" -ForegroundColor Green
}
$home = Get-Json "$BaseUrl/api/v10/selected-machine/home" 25
if(-not $home.ok){ throw "home not ok" }
if($home.PSObject.Properties.Name -notcontains "today_download_gb"){ throw "home missing traffic kpis" }
Write-Host "PASS: home selected contract ok clients=$($home.client_machines) traffic=$($home.today_download_gb)GB/$($home.today_upload_gb)GB" -ForegroundColor Green
$nt = Get-Json "$BaseUrl/api/v10/selected-machine/notification-fast" 10
if(-not $nt.ok){ throw "notification fast not ok" }
Write-Host "PASS: notification fast ok alerts=$($nt.simulated_alerts_count)" -ForegroundColor Green
Write-Host "=== V10 SELECTED-MACHINE DATA CONTRACT TEST PASS ===" -ForegroundColor Green
