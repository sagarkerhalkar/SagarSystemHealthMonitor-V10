param([string]$BaseUrl="http://127.0.0.1:2294",[string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
Write-Host "=== V10 CLEAN RUNTIME 2278 SELECTED MACHINE APP TEST ==="
$index=Get-Content (Join-Path $App "public\index.html") -Raw
if($index -notmatch "v10_clean_app_2278.js"){throw "FAIL: clean app JS not loaded"}
if($index -match "v10_phase3_fix9_global.js|v10_bind_2278_clean.js|v10_selected_machine_contract_ui.js|v10_hardware_2278_readonly.js|v10_software_2278_readonly.js"){throw "FAIL: old patch-chain JS still loaded"}
Write-Host "PASS: index uses only clean runtime"
$health=Invoke-RestMethod "$BaseUrl/api/v10/app/health" -TimeoutSec 20
if(-not $health.ok){throw "FAIL: clean API health not ok"}
Write-Host "PASS: clean API health ok"
$machines=Invoke-RestMethod "$BaseUrl/api/v10/app/machines" -TimeoutSec 30
if(-not $machines.ok){throw "FAIL: machines API not ok"}
$clients=@($machines.machines|Where-Object{-not $_.is_monitor_server})
if($clients.Count -lt 1){throw "FAIL: no client machines after server separation"}
Write-Host "PASS: machines ok rows=$(@($machines.machines).Count) clients=$($clients.Count)"
foreach($m in @($clients|Select-Object -First ([Math]::Min(3,$clients.Count)))){
  $id=[uri]::EscapeDataString([string]$m.machine_id)
  foreach($ep in @("hardware","network","software","machine360")){
    $r=Invoke-RestMethod "$BaseUrl/api/v10/app/$ep`?machine_id=$id&limit=10000" -TimeoutSec 45
    if(-not $r.ok){throw "FAIL: $ep not ok for $($m.hostname)"}
    if([string]$r.returned_machine_id -ne [string]$m.machine_id){throw "FAIL: $ep returned wrong machine requested=$($m.machine_id) returned=$($r.returned_machine_id)"}
  }
  Write-Host "PASS: selected-machine contract ok for $($m.hostname)"
}
$home=Invoke-RestMethod "$BaseUrl/api/v10/app/home" -TimeoutSec 45
if(-not $home.ok){throw "FAIL: home API not ok"}
Write-Host "PASS: home API ok"
Write-Host "=== V10 CLEAN RUNTIME 2278 SELECTED MACHINE APP TEST PASS ==="
