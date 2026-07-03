param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 2-Day Phase3 Live UI Test ===" -ForegroundColor Cyan
function Get-Json($Path){
  $u="$BaseUrl$Path"; Write-Host "GET $u" -ForegroundColor DarkCyan
  $r=Invoke-WebRequest $u -UseBasicParsing -TimeoutSec 20
  $txt=$r.Content
  if($txt -is [byte[]]){ $txt=[Text.Encoding]::UTF8.GetString($txt) }
  try{ return $txt | ConvertFrom-Json }catch{ throw "Non JSON from $Path : $($txt.Substring(0,[Math]::Min(200,$txt.Length)))" }
}
$status=Get-Json "/api/v10final/status"
if(-not $status.ok){ throw "v10final status not ok" }
$machines=Get-Json "/api/v10final/machines"
$hw=Get-Json "/api/v10final/inventory/hardware?limit=5"
$rules=Get-Json "/api/v10final/notifications/rules"
$iso=Get-Json "/api/v10final/iso/audit"
$deploy=Get-Json "/api/v10final/deploy/profiles"
$idx=Invoke-WebRequest "$BaseUrl/" -UseBasicParsing -TimeoutSec 20
$body=$idx.Content; if($body -is [byte[]]){ $body=[Text.Encoding]::UTF8.GetString($body) }
foreach($needle in @("Machine 360","Hardware Asset Register","v10_phase3_live.js","Next Toppers")){
  if($body -notlike "*$needle*"){ throw "index missing $needle" }
}
$ReportDir="D:\SagarMonitor_V10_CleanBuild\reports"; New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
$Stamp=Get-Date -Format "yyyyMMdd_HHmmss"
$Report=[ordered]@{
  time=(Get-Date).ToString("s")
  base_url=$BaseUrl
  status_counts=$status.counts
  machine_count=$machines.count
  hardware_total=$hw.total
  notification_rules=($rules.rules|Measure-Object).Count
  iso_hardware=$iso.hardware
  deploy_profiles=($deploy.rows|Measure-Object).Count
  ui_index_loaded=$true
}
$Report | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $ReportDir "V10_PHASE3_LIVE_DATA_SNAPSHOT_$Stamp.json") -Encoding UTF8
Write-Host "PHASE3 TEST PASS" -ForegroundColor Green
try{
  Push-Location "D:\SagarMonitor_V10_CleanBuild"
  if(Get-Command git -ErrorAction SilentlyContinue){
    git add reports docs tests public
    git commit -m "V10 Phase3 live UI test snapshot" 2>$null
    git push 2>$null
    Write-Host "Git snapshot push attempted." -ForegroundColor Green
  }
  Pop-Location
}catch{ try{Pop-Location}catch{}; Write-Host "Git snapshot push skipped/failed: $($_.Exception.Message)" -ForegroundColor Yellow }
