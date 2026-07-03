param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 Phase3 Fix8 Customer UI Live Test ===" -ForegroundColor Cyan
function Get-Json($Path){
  $u="$BaseUrl$Path"; Write-Host "GET $u" -ForegroundColor DarkCyan
  try { return Invoke-RestMethod -Uri $u -UseBasicParsing -TimeoutSec 20 } catch { throw "GET failed $Path :: $($_.Exception.Message)" }
}
function NeedText($Text,$Needle){ if($Text -notlike "*$Needle*"){ throw "index missing $Needle" } }
$ui=(Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 20).Content
$needles=@(
 'Home / Command Center','Machine Fleet','Machine 360','Network + VPN','Hardware Intelligence','Software Intelligence','Hardware Asset Register','Software Asset Register','ISO Audit Center','USB + Peripherals','Human Change Log','Day History','Client Messages','Notifications','Deploy Center','Settings',
 'User / Role Management','Router ISP Details','Notification Rule Management','Branding Image Upload','Password Reset','Created by Sagar Kerhalkar'
)
foreach($n in $needles){ NeedText $ui $n }
if($ui -like '*GitHub Status*'){ throw 'Customer UI must not show GitHub Status button' }
$status=Get-Json '/api/v10final/status'
$machines=Get-Json '/api/v10final/machines'
$hw=Get-Json '/api/v10final/inventory/hardware?limit=5'
$router=Get-Json '/api/v10final/router/isps'
$users=Get-Json '/api/v10final/settings/users'
$rules=Get-Json '/api/v10final/notifications/rules'
$branding=Get-Json '/api/v10final/branding'
if($null -eq $machines.machines -and $null -eq $machines.rows){ throw 'machines endpoint missing machines/rows' }
if($null -eq $hw.rows -and $null -eq $hw.assets){ throw 'hardware endpoint missing rows/assets' }
if($null -eq $router.rows){ throw 'router ISP endpoint missing rows' }
if($null -eq $users.rows -and $null -eq $users.users){ throw 'users endpoint missing rows/users' }
if($null -eq $rules.rules -and $null -eq $rules.rows){ throw 'notification rules endpoint missing rules/rows' }
Write-Host "=== PHASE3 FIX8 CUSTOMER UI TEST PASS ===" -ForegroundColor Green
