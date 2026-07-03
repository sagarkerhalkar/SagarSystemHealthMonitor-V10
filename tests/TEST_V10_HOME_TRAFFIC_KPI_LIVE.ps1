param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 Home Traffic KPI Live Test ===" -ForegroundColor Cyan
function Get-Text($Url){
  $r = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 15
  if($r.Content -is [byte[]]){ return [System.Text.Encoding]::UTF8.GetString($r.Content) }
  return [string]$r.Content
}
function Get-Json($Url){
  try { return Invoke-RestMethod $Url -TimeoutSec 15 }
  catch {
    $txt = Get-Text $Url
    try { return $txt | ConvertFrom-Json } catch { throw "Non-JSON from $Url : $($txt.Substring(0,[Math]::Min(200,$txt.Length)))" }
  }
}
$idx = Get-Text "$BaseUrl/"
foreach($needle in @('v10_home_traffic_kpi.js','v10_home_traffic_kpi.css','Today Download','Current Upload')){
  if($idx -notlike "*$needle*"){ throw "index missing $needle" }
}
Write-Host "PASS: index has Home Traffic KPI markers" -ForegroundColor Green
$js = Get-Text "$BaseUrl/v10_home_traffic_kpi.js"
if($js -notlike "*Live Organization Traffic KPIs*"){ throw "traffic JS missing content" }
Write-Host "PASS: JS available" -ForegroundColor Green
$j = Get-Json "$BaseUrl/api/v10/home/traffic-kpi"
if(-not $j.ok){ throw "traffic API ok false" }
foreach($field in @('today_download_gb','today_upload_gb','current_download_mbps','current_upload_mbps','cards','per_machine')){
  if(-not ($j.PSObject.Properties.Name -contains $field)){ throw "traffic API missing $field" }
}
if($j.source -notlike "*live*" -and $j.source -notlike "*latest*"){ throw "traffic API source not live/latest" }
Write-Host "Traffic summary:" -ForegroundColor Yellow
$j | ConvertTo-Json -Depth 4
Write-Host "=== V10 HOME TRAFFIC KPI LIVE TEST PASS ===" -ForegroundColor Green
