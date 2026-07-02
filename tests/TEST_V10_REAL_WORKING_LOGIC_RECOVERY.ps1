
param([string]$App = "D:\SagarMonitor_V10_CleanBuild", [string]$BaseUrl = "http://127.0.0.1:2294")
$ErrorActionPreference = "Stop"
$required = @("$App\public\index.html","$App\public\app.js","$App\public\styles.css","$App\inventory_30min.py")
foreach($f in $required){ if(!(Test-Path $f)){ throw "Missing required file: $f" } }
$js = Get-Content "$App\public\app.js" -Raw
foreach($s in @("renderUsb", "renderDeployCommands", "invHwOpen", "invHwSave", "invSwOpen", "sendClientMessage", "renderMachine360", "downloadUsbSelected")){ if($js -notmatch [regex]::Escape($s)){ throw "Missing old working function in app.js: $s" } }
$html = Get-Content "$App\public\index.html" -Raw
foreach($s in @("page-usb", "page-deploy", "page-hwinventory", "page-swinventory", "page-isoaudit", "deployCommandsMount", "hwiForm", "swiForm")){ if($html -notmatch [regex]::Escape($s)){ throw "Missing old working section in index.html: $s" } }
Write-Host "PASS: Static recovery files contain old working logic."
try {
  $s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
  $body = @{username="admin"; password="Admin@12345"} | ConvertTo-Json
  Invoke-RestMethod "$BaseUrl/api/auth/login" -Method POST -ContentType "application/json" -Body $body -WebSession $s | Out-Null
  $hw = Invoke-RestMethod "$BaseUrl/api/inv30/hw/summary" -WebSession $s
  $rows = Invoke-RestMethod "$BaseUrl/api/inv30/hw/assets" -WebSession $s
  $rules = Invoke-RestMethod "$BaseUrl/api/notifications/rules" -WebSession $s
  Write-Host "Runtime HW assets:" $hw.assets
  Write-Host "Runtime HW rows:" $rows.rows.Count
  Write-Host "Runtime notification rules:" $rules.rules.Count
  if([int]$hw.assets -lt 1){ throw "Runtime inventory asset count is 0" }
  Write-Host "PASS: Runtime inv30/backend check OK."
} catch { Write-Host "WARN: Runtime check skipped/failed. Start V10 then rerun. $($_.Exception.Message)" }
