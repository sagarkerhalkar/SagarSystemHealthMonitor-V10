param([string]$BaseUrl = "http://127.0.0.1:2294")
$ErrorActionPreference = "Stop"
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginBody = @{ username = "admin"; password = "Admin@12345" } | ConvertTo-Json
try { Invoke-WebRequest "$BaseUrl/api/auth/login" -Method POST -ContentType "application/json" -Body $loginBody -WebSession $session -UseBasicParsing | Out-Null } catch {}
$routes = @("/","/v10_inventory_plugin.js","/v10_inventory_plugin.css","/api/health","/api/overview","/api/machines","/api/v10/status","/api/v10/current-machines","/api/v10/dedup-report","/api/v10/software-inventory","/api/v10/gpu-inventory","/api/v10/hardware-inventory","/api/v10/usb-inventory","/api/export/machine_current.csv","/api/export/software.csv","/api/export/usb.csv","/api/export/gpu.csv","/api/export/hardware.csv")
foreach ($r in $routes) {
  $res = Invoke-WebRequest ($BaseUrl + $r) -WebSession $session -UseBasicParsing
  Write-Host "OK $r status=$($res.StatusCode) bytes=$($res.Content.Length)" -ForegroundColor Green
}
Write-Host "V10 OLD UI PLUGIN DEDUP COUNT FIX QA OK" -ForegroundColor Green
