param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 Phase3 Fix6 Clean Corporate Live UI Test ===" -ForegroundColor Cyan
function Get-Json($path){
  $url="$BaseUrl$path"; Write-Host "GET $url" -ForegroundColor Gray
  $r=Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 20
  try { return $r.Content | ConvertFrom-Json } catch { throw "Non JSON from $path : $($r.Content.Substring(0,[Math]::Min(200,$r.Content.Length)))" }
}
$m=Get-Json "/api/v10final/machines"
if($null -eq $m.machines){ throw "machines API missing machines array" }
$hw=Get-Json "/api/v10final/inventory/hardware?limit=5"
if($null -eq $hw.rows){ throw "hardware inventory API missing rows" }
if($null -eq $hw.assets){ throw "hardware inventory API missing assets compatibility array" }
Write-Host "Hardware rows returned: $($hw.count), total: $($hw.total)" -ForegroundColor Green
$sw=Get-Json "/api/v10final/inventory/software?limit=5"
if($null -eq $sw.rows){ throw "software inventory API missing rows" }
$ui=(Invoke-WebRequest "$BaseUrl/?phase3=fix6" -UseBasicParsing -TimeoutSec 20).Content
foreach($n in @("Home / Command Center","Machine Fleet","Machine 360","Hardware Asset Register","Software Asset Register","Created by","8105977226","sagarkerhalkar.com")){
  if($ui -notlike "*$n*"){ throw "index missing $n" }
}
if($ui -like "*<select*DESKTOP*"){ throw "top/global machine selector still appears in static index" }
Write-Host "Machines: $($m.count) | HW total: $($hw.total) | SW rows: $($sw.count)" -ForegroundColor Green
Write-Host "=== PHASE3 FIX6 CLEAN LIVE UI TEST PASS ===" -ForegroundColor Green
