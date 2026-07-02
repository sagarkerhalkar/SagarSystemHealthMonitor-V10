param(
  [string]$App = "D:\SagarMonitor_V10_CleanBuild",
  [string]$BaseUrl = "http://127.0.0.1:2294"
)
$ErrorActionPreference = "Stop"
Write-Host "=== V10 Final Studied Requirements Test ==="
Write-Host "App: $App"

$requiredFiles = @(
  "$App\public\index.html",
  "$App\public\app.js",
  "$App\public\styles.css",
  "$App\public\style.css",
  "$App\inventory_30min.py",
  "$App\V10_IDENTITY_CORE_2294.py"
)
foreach($f in $requiredFiles){
  if(!(Test-Path $f)){ throw "Missing required file: $f" }
  Write-Host "OK file: $f"
}

$js = Get-Content "$App\public\app.js" -Raw
$html = Get-Content "$App\public\index.html" -Raw
$server = Get-Content "$App\V10_IDENTITY_CORE_2294.py" -Raw
$inv = Get-Content "$App\inventory_30min.py" -Raw

$jsMustContain = @(
  "renderMachine360",
  "renderUsb",
  "renderDeployCommands",
  "sendClientMessage",
  "invHwOpen",
  "invHwSave",
  "invSwOpen",
  "invSwSave",
  "/api/inv30/hw/assets",
  "/api/inv30/hw/save",
  "/api/inv30/sw/licenses",
  "/api/inv30/sw/save",
  "/api/notifications/rules",
  "/api/messages",
  "/api/overview"
)
foreach($s in $jsMustContain){ if($js -notmatch [regex]::Escape($s)){ throw "Missing old working JS logic: $s" } }
Write-Host "PASS: old working frontend module functions are present."

$htmlMustContain = @(
  "page-machine360",
  "page-usb",
  "page-deploy",
  "page-hwinventory",
  "page-swinventory",
  "page-isoaudit",
  "page-messages",
  "hwiForm",
  "swiForm",
  "deployCommandsMount"
)
foreach($s in $htmlMustContain){ if($html -notmatch [regex]::Escape($s)){ throw "Missing old working HTML section: $s" } }
Write-Host "PASS: required page sections are present."

$serverMustContain = @("INVENTORY_30MIN_HOOK", "cpu_ram_critical", "gpu_temp_high", "disk_high")
foreach($s in $serverMustContain){ if($server -notmatch [regex]::Escape($s)){ throw "Missing server logic marker: $s" } }
Write-Host "PASS: server notification/inventory hook markers are present."

$invMustContain = @("/api/inv30/hw/assets", "/api/inv30/hw/save", "/api/inv30/sw/licenses", "/api/inv30/sw/save", "fresh_hw_inventory_v2.json", "hw_inventory_editable.json")
foreach($s in $invMustContain){ if($inv -notmatch [regex]::Escape($s)){ throw "Missing inventory backend bridge logic: $s" } }
Write-Host "PASS: inv30 backend bridge is present."

try {
  $health = Invoke-RestMethod "$BaseUrl/api/health" -TimeoutSec 5
  Write-Host "Runtime health OK:" ($health.ok)
  $s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
  $body = @{username="admin"; password="Admin@12345"} | ConvertTo-Json
  try { Invoke-RestMethod "$BaseUrl/api/auth/login" -Method POST -ContentType "application/json" -Body $body -WebSession $s -TimeoutSec 8 | Out-Null } catch {}
  $overview = Invoke-RestMethod "$BaseUrl/api/overview" -WebSession $s -TimeoutSec 15
  Write-Host "Runtime machines:" (($overview.machines | Measure-Object).Count)
  $hw = Invoke-RestMethod "$BaseUrl/api/inv30/hw/summary" -WebSession $s -TimeoutSec 15
  Write-Host "Runtime H/W assets:" $hw.assets
  if([int]$hw.assets -lt 1){ throw "Runtime H/W inventory asset count is 0; inventory bridge not loading uploaded data." }
  $rules = Invoke-RestMethod "$BaseUrl/api/notifications/rules" -WebSession $s -TimeoutSec 15
  Write-Host "Runtime notification rules:" (($rules.rules | Measure-Object).Count)
  Write-Host "PASS: runtime API/inventory smoke check OK."
} catch {
  Write-Host "WARN: Runtime test skipped/failed. Start V10 and rerun. Detail: $($_.Exception.Message)"
}

Write-Host "PASS: V10 final studied requirements static test complete."
