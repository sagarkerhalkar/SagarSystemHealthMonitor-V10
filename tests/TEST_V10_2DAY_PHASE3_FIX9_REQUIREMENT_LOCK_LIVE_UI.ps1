param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 Phase3 Fix9 Requirement Lock Live UI Test ===" -ForegroundColor Cyan
function GetJson($Path){ $u="$BaseUrl$Path"; Write-Host "GET $u" -ForegroundColor DarkCyan; $r=Invoke-WebRequest $u -UseBasicParsing -TimeoutSec 20; return $r.Content | ConvertFrom-Json }
$idx=(Invoke-WebRequest "$BaseUrl/?phase3=fix9" -UseBasicParsing -TimeoutSec 20).Content
$needles=@('Created by Sagar Kerhalkar','Organization Asset Usage Details','Auto Router / Cloudflare ISP Probe','Notification Rule Management','User / Role Management','Hardware Asset Register','Software Asset Register','ISO Audit Center')
foreach($n in $needles){ if($idx -notlike "*$n*"){ throw "index missing $n" } }
if($idx -like '*GitHub Status*'){ throw 'Customer UI must not show GitHub Status option' }
$status=GetJson '/api/v10final/status'
$machines=GetJson '/api/v10final/machines'
if($null -eq $machines.machines){ throw 'machines api missing machines array' }
$hw=GetJson '/api/v10final/inventory/hardware?limit=5'
if(($null -eq $hw.rows) -and ($null -eq $hw.assets)){ throw 'hardware inventory api missing rows/assets' }
$sw=GetJson '/api/v10final/inventory/software?limit=5'
if(($null -eq $sw.rows) -and ($null -eq $sw.assets)){ throw 'software inventory api missing rows/assets' }
$isp=GetJson '/api/v10final/router/isps'
if($null -eq $isp.rows){ throw 'router isp api missing rows' }
Write-Host "Machines: $($machines.machines.Count)" -ForegroundColor Green
Write-Host "Hardware rows: $($hw.rows.Count)" -ForegroundColor Green
Write-Host "Software rows: $($sw.rows.Count)" -ForegroundColor Green
Write-Host "ISP/probe rows: $($isp.rows.Count)" -ForegroundColor Green
Write-Host "=== FIX9 TEST PASS ===" -ForegroundColor Green
