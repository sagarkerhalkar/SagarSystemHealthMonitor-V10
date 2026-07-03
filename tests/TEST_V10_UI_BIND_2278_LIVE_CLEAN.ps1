
param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 UI BIND 2278 LIVE CLEAN TEST ===" -ForegroundColor Cyan
function Get-Json($Url){
  $r=Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 20
  $txt=$r.Content
  if($txt -is [byte[]]){ $txt=[Text.Encoding]::UTF8.GetString($txt) }
  return $txt | ConvertFrom-Json
}
$idx=(Invoke-WebRequest "$BaseUrl/" -UseBasicParsing -TimeoutSec 20).Content
if($idx -is [byte[]]){ $idx=[Text.Encoding]::UTF8.GetString($idx) }
foreach($n in @('v10_bind_2278_clean.js','v10_bind_2278_clean.css','V10_UI_BIND_2278_CLEAN_SOURCE')){
  if($idx -notlike "*$n*"){ throw "index missing $n" }
}
Write-Host "PASS: index has clean binding assets"
$hs=Get-Json "$BaseUrl/api/v10/source2278/hardware/status"
if(!$hs.ok){ throw "hardware status not ok" }
if([int]$hs.machines_checked -lt 1){ throw "hardware status machines_checked < 1" }
Write-Host "PASS: hardware status machines_checked=$($hs.machines_checked) fresh=$($hs.fresh_machines) stale=$($hs.stale_machines)"
$h=Get-Json "$BaseUrl/api/v10/source2278/hardware?limit=2&freshness=all"
if(!$h.ok -or $h.machines.Count -lt 1){ throw "hardware list missing machines" }
$m=$h.machines[0]
foreach($field in @('hostname','cpu_name','ram_total_gb','disks','gpus','usb_devices','network_adapters')){
  if($null -eq $m.$field){ throw "hardware machine missing $field" }
}
Write-Host "PASS: hardware machine has CPU/RAM/disk/GPU/USB/network fields"
$sw=Get-Json "$BaseUrl/api/v10/source2278/software/status"
if(!$sw.ok){ throw "software status not ok" }
if([int]$sw.extracted_software_rows_total -lt 1){ throw "software rows not extracted" }
Write-Host "PASS: software rows extracted=$($sw.extracted_software_rows_total)"
$tr=Get-Json "$BaseUrl/api/v10/source2278/home-traffic-kpi"
if(!$tr.ok){ throw "traffic KPI not ok" }
foreach($field in @('today_download_gb','today_upload_gb','current_download_mbps','current_upload_mbps')){
  if($null -eq $tr.$field){ throw "traffic missing $field" }
}
Write-Host "PASS: traffic KPI available from 2278 source"
$nt=Get-Json "$BaseUrl/api/v10/source2278/notification-test"
if(!$nt.ok){ throw "notification test not ok" }
Write-Host "PASS: notification simulation rules=$($nt.rules_count) machines=$($nt.machines_checked) alerts=$($nt.simulated_alerts_count)"
Write-Host "=== V10 UI BIND 2278 LIVE CLEAN TEST PASS ===" -ForegroundColor Green
