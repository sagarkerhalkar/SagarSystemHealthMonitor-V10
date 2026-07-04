param(
  [string]$BaseUrl = "http://127.0.0.1:2294",
  [string]$App = "D:\SagarMonitor_V10_CleanBuild"
)
$ErrorActionPreference = "Stop"
Write-Host "=== V10 CLEAN RUNTIME ROUTE FIX V4 TEST ===" -ForegroundColor Cyan

$idx = Invoke-WebRequest "$BaseUrl/" -UseBasicParsing -TimeoutSec 10
if ($idx.Content -notmatch "v10_clean_app_2278\.js" -or $idx.Content -match "v10_phase3_fix9_global\.js|v10_bind_2278_clean\.js|v10_selected_machine_contract_ui\.js") {
  throw "Index is not clean runtime only"
}
Write-Host "PASS: index clean runtime only" -ForegroundColor Green

$health = Invoke-RestMethod "$BaseUrl/api/v10/app/health" -TimeoutSec 15
if (-not $health.ok) { throw "clean app health not ok" }
Write-Host "PASS: clean app health public readonly" -ForegroundColor Green

$list = Invoke-RestMethod "$BaseUrl/api/v10/app/machines" -TimeoutSec 30
if (-not $list.ok -or -not $list.machines -or $list.machines.Count -lt 1) { throw "machines endpoint not returning rows" }
Write-Host ("PASS: machines endpoint rows=" + $list.machines.Count) -ForegroundColor Green

$clients = @($list.machines | Where-Object { -not $_.is_monitor_server })
if ($clients.Count -lt 1) { throw "No client machines after monitor-server separation" }
$pick = $clients[0]
$mid = $pick.machine_id
Write-Host ("Selected test machine: " + $pick.hostname + " | " + $mid) -ForegroundColor Yellow

$hw = Invoke-RestMethod ("$BaseUrl/api/v10/app/hardware?machine_id=" + [uri]::EscapeDataString($mid)) -TimeoutSec 30
if (-not $hw.ok) { throw "hardware endpoint not ok" }
if ([string]$hw.returned_machine_id -ne [string]$mid) { throw "hardware returned wrong machine_id. requested=$mid returned=$($hw.returned_machine_id)" }
Write-Host "PASS: hardware exact selected machine" -ForegroundColor Green

$net = Invoke-RestMethod ("$BaseUrl/api/v10/app/network?machine_id=" + [uri]::EscapeDataString($mid)) -TimeoutSec 30
if (-not $net.ok) { throw "network endpoint not ok" }
if ([string]$net.returned_machine_id -ne [string]$mid) { throw "network returned wrong machine_id" }
Write-Host "PASS: network exact selected machine" -ForegroundColor Green

$sw = Invoke-RestMethod ("$BaseUrl/api/v10/app/software?machine_id=" + [uri]::EscapeDataString($mid) + "&limit=50") -TimeoutSec 40
if (-not $sw.ok) { throw "software endpoint not ok" }
if ([string]$sw.returned_machine_id -ne [string]$mid) { throw "software returned wrong machine_id" }
Write-Host ("PASS: software exact selected machine rows=" + $sw.software_count) -ForegroundColor Green

Write-Host "=== V10 CLEAN RUNTIME ROUTE FIX V4 TEST PASS ===" -ForegroundColor Green
