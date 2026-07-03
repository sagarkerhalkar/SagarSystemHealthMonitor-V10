
param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 Phase3 Fix4 Full Tab Requirements Live UI Test ===" -ForegroundColor Cyan
function Get-Json($path){
  $url="$BaseUrl$path"; Write-Host "GET $url" -ForegroundColor Gray
  $r=Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 20
  try { return $r.Content | ConvertFrom-Json } catch { throw "Non JSON from $path : $($r.Content.Substring(0,[Math]::Min(200,$r.Content.Length)))" }
}
$status=Get-Json "/api/v10final/status"
if(-not $status){ throw "status api missing" }
$machines=Get-Json "/api/v10final/machines"
if($null -eq $machines.machines){ throw "machines api missing machines array" }
$hw=Get-Json "/api/v10final/inventory/hardware?limit=5"
if($null -eq $hw.rows -and $null -eq $hw.assets){ throw "hardware inventory api missing rows" }
$rules=Get-Json "/api/v10final/notifications/rules"
if($null -eq $rules.rules){ throw "notification rules api missing rules" }
$iso=Get-Json "/api/v10final/iso/audit"
if(-not $iso){ throw "iso api missing" }
$body=(Invoke-WebRequest "$BaseUrl/?phase3=fix4" -UseBasicParsing -TimeoutSec 20).Content
$needles=@(
  "Home / Command Center","Machine Fleet","Machine 360","Network + VPN","Software Intelligence",
  "Hardware Asset Register","Software Asset Register","ISO Audit Center","USB + Peripherals","Human Change Log",
  "Day History","Client Messages","Notifications","Deploy Center","Settings","Created by","8105977226","sagarkerhalkar.com"
)
foreach($n in $needles){ if($body -notlike "*$n*"){ throw "index missing $n" } }
Write-Host "=== PHASE3 FIX4 FULL TAB REQUIREMENTS LIVE UI TEST PASS ===" -ForegroundColor Green
