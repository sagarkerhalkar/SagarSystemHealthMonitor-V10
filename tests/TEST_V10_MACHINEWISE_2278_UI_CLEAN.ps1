param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 Machine-wise 2278 UI Clean Test ==="
function GetText($Url){ (Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 20).Content }
$idx = GetText "$BaseUrl/"
foreach($n in @("V10_MACHINEWISE_2278_UI_MARKER","v10_machinewise_2278_ui.js","v10_machinewise_2278_ui.css")){
  if($idx -notlike "*$n*"){ throw "index missing $n" }
}
Write-Host "PASS: index has machine-wise clean UI files"
$hw = Invoke-RestMethod "$BaseUrl/api/v10/source2278/hardware/status" -TimeoutSec 30
if(!$hw.ok){ throw "hardware status not ok" }
if([int]$hw.machines_checked -lt 1){ throw "no 2278 machines" }
Write-Host "PASS: 2278 hardware source ok machines=$($hw.machines_checked) fresh=$($hw.fresh_machines)"
$data = Invoke-RestMethod "$BaseUrl/api/v10/source2278/hardware?limit=1&freshness=fresh" -TimeoutSec 30
$m = $data.machines[0]
if(!$m.hostname){ throw "hostname missing" }
if(!$m.cpu_name){ throw "cpu_name missing from selected fresh machine" }
if($m.disks.Count -lt 1){ throw "disk array missing" }
if($m.network_adapters.Count -lt 1){ throw "network adapter array missing" }
Write-Host "PASS: fresh machine has hostname/cpu/disk/network arrays: $($m.hostname)"
$sw = Invoke-RestMethod "$BaseUrl/api/v10/source2278/software/status" -TimeoutSec 40
if(!$sw.ok){ throw "software status not ok" }
if([int]$sw.extracted_software_rows_total -lt 1){ throw "software rows missing" }
Write-Host "PASS: software source ok rows=$($sw.extracted_software_rows_total)"
$nt = Invoke-RestMethod "$BaseUrl/api/v10/source2278/notification-test?fast=1" -TimeoutSec 60
if(!$nt.ok){ throw "notification read-only test not ok" }
if([int]$nt.machines_checked -lt 1){ throw "notification test machines missing" }
Write-Host "PASS: notification read-only simulation ok machines=$($nt.machines_checked) alerts=$($nt.simulated_alerts_count) mode=$($nt.mode) elapsed=$($nt.elapsed_ms)ms"
Write-Host "=== V10 MACHINE-WISE 2278 UI CLEAN TEST PASS ===" -ForegroundColor Green
