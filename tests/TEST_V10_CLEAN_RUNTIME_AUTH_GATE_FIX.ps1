param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 Clean Runtime Auth Gate Fix Test ==="
$health = Invoke-RestMethod "$BaseUrl/api/v10/app/health" -TimeoutSec 20
if (-not $health.ok) { throw "health not ok" }
Write-Host "PASS: /api/v10/app/health reachable"
$list = Invoke-RestMethod "$BaseUrl/api/v10/app/machines" -TimeoutSec 30
if (-not $list.ok) { throw "machines not ok" }
$count = ($list.machines | Measure-Object).Count
if ($count -lt 1) { throw "no machines returned" }
Write-Host "PASS: /api/v10/app/machines reachable machines=$count"
Write-Host "=== V10 CLEAN RUNTIME AUTH GATE FIX TEST PASS ==="
