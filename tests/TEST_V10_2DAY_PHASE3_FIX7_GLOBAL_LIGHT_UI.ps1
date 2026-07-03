param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 Phase3 Fix7 Global Light UI Test ===" -ForegroundColor Cyan
function GetText($url){ (Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 20).Content }
function GetJson($url){ (Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 20).Content | ConvertFrom-Json }
$status=GetJson "$BaseUrl/api/v10final/status"
if(!$status){ throw "status API failed" }
$machines=GetJson "$BaseUrl/api/v10final/machines"
if(($null -eq $machines.machines) -and ($null -eq $machines.rows)){ throw "machines API missing machines/rows" }
$hw=GetJson "$BaseUrl/api/v10final/inventory/hardware?limit=5"
if(($null -eq $hw.rows) -and ($null -eq $hw.assets)){ throw "hardware inventory API missing rows/assets" }
$ui=GetText "$BaseUrl/"
foreach($needle in @('v10_phase3_global.css','v10_phase3_global.js','Created by','Hardware Asset Register','Notifications','Settings','User / Role Management','Login Background Preview')){
  if($ui -notlike "*$needle*"){ throw "index missing $needle" }
}
Write-Host "=== PHASE3 FIX7 GLOBAL LIGHT UI TEST PASS ===" -ForegroundColor Green
