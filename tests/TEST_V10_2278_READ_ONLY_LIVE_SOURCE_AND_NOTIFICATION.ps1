param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 2278 Read-Only Live Source + Notification Test ===" -ForegroundColor Cyan
function Get-Text($Url){
  $r = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 20
  if($r.Content -is [byte[]]){ return [System.Text.Encoding]::UTF8.GetString($r.Content) }
  return [string]$r.Content
}
function Get-Json($Url){
  try { return Invoke-RestMethod $Url -TimeoutSec 20 }
  catch {
    $txt = Get-Text $Url
    try { return $txt | ConvertFrom-Json } catch { throw "Non-JSON from $Url : $($txt.Substring(0,[Math]::Min(200,$txt.Length)))" }
  }
}
$idx = Get-Text "$BaseUrl/"
if($idx -notlike "*V10_2278_READ_ONLY_LIVE_SOURCE_MARKER*"){ Write-Host "WARN: index marker not visible, continuing API test" -ForegroundColor Yellow }
$status = Get-Json "$BaseUrl/api/v10/source2278/status"
if(-not $status.ok){ throw "2278 read-only status ok=false: $($status | ConvertTo-Json -Depth 5)" }
if(-not $status.no_write_to_2278){ throw "status does not confirm no_write_to_2278" }
if(-not $status.source_db_exists){ throw "2278 source DB not found: $($status.source_db)" }
if(-not ($status.counts.PSObject.Properties.Name -contains 'latest')){ throw "2278 latest table count missing" }
if([int]$status.counts.latest -lt 1){ throw "2278 latest has no rows" }
Write-Host "PASS: 2278 DB read-only status ok. latest rows:" $status.counts.latest -ForegroundColor Green
if($null -ne $status.newest_age_minutes -and [double]$status.newest_age_minutes -gt 10){
  Write-Host "WARN: newest 2278 latest row is stale by $($status.newest_age_minutes) minutes. Connector works, but clients may not be posting fresh data." -ForegroundColor Yellow
}
$machines = Get-Json "$BaseUrl/api/v10/source2278/machines"
if(-not $machines.ok){ throw "machines ok=false" }
if([int]$machines.total -lt 1){ throw "source2278 machines total < 1" }
foreach($field in @('machine_id','hostname','cpu_percent','ram_percent','wan_download_mbps','today_download_gb','software_count','usb_count')){
  if(-not ($machines.machines[0].PSObject.Properties.Name -contains $field)){ throw "machine row missing $field" }
}
Write-Host "PASS: machines parsed from 2278 latest:" $machines.total -ForegroundColor Green
$traffic = Get-Json "$BaseUrl/api/v10/source2278/home-traffic-kpi"
if(-not $traffic.ok){ throw "traffic ok=false" }
foreach($field in @('today_download_gb','today_upload_gb','current_download_mbps','current_upload_mbps','per_machine')){
  if(-not ($traffic.PSObject.Properties.Name -contains $field)){ throw "traffic API missing $field" }
}
Write-Host "PASS: traffic KPI from 2278 read-only available" -ForegroundColor Green
$notif = Get-Json "$BaseUrl/api/v10/source2278/notifications"
if(-not $notif.ok){ throw "notifications ok=false" }
if($null -eq $notif.notification_rules){ throw "notification rules missing" }
Write-Host "PASS: notifications/rules read-only available. rules:" ($notif.notification_rules.Count) -ForegroundColor Green
$ntest = Get-Json "$BaseUrl/api/v10/source2278/notification-test"
if(-not $ntest.ok){ throw "notification-test ok=false" }
if($ntest.mode -notlike "*read_only*"){ throw "notification-test is not read_only" }
Write-Host "PASS: notification simulation read-only. alerts:" $ntest.simulated_alerts_count -ForegroundColor Green
Write-Host "Summary:" -ForegroundColor Yellow
$status | ConvertTo-Json -Depth 5
$traffic | Select-Object today_download_gb,today_upload_gb,current_download_mbps,current_upload_mbps,clients_count,stale_warning | ConvertTo-Json -Depth 4
$ntest | Select-Object rules_count,recent_notifications_count,machines_checked,simulated_alerts_count,note | ConvertTo-Json -Depth 4
Write-Host "=== V10 2278 READ-ONLY LIVE SOURCE + NOTIFICATION TEST PASS ===" -ForegroundColor Green
