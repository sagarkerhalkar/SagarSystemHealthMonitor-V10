param([string]$BaseUrl = "http://127.0.0.1:2294", [string]$App = "D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference = "Stop"
Write-Host "=== V10 Stable Selected-Machine No-Flicker Fix Test ==="
function Need($Cond,$Msg){ if(-not $Cond){ throw $Msg } else { Write-Host "PASS: $Msg" -ForegroundColor Green } }
$idx = (Invoke-WebRequest "$BaseUrl/" -UseBasicParsing -TimeoutSec 15).Content
Need ($idx -like "*v10_machinewise_2278_ui.js*") "index loads stable machine-wise UI JS"
Need ($idx -like "*v10_machinewise_2278_ui.css*") "index loads stable machine-wise UI CSS"
$old = Get-Content (Join-Path $App "public\v10_phase3_fix9_global.js") -Raw
Need ($old -notlike "*setInterval(refreshAll,30000)*") "old 30-second auto refresh disabled"
Need ($old -notlike "*renderCommand();renderFleet();renderMachine360();renderNetwork();renderHardware();renderSoftware();renderHWInv()*") "old renderer no longer rewrites selected-machine tabs"
Need ($old -like "*gh.style.display='none'*") "old global Home hero hidden"
$ui = Get-Content (Join-Path $App "public\v10_machinewise_2278_ui.js") -Raw
Need ($ui -notlike "*MutationObserver*") "new UI has no MutationObserver render loop"
Need ($ui -notlike "*setInterval(*") "new UI has no auto setInterval loop"
Need ($ui -like "*localStorage.setItem(LS_SEL,id)*") "selected machine persists"
Need ($ui -like "*Monitor Server*") "monitor server separated from client machines"
$h = Invoke-RestMethod "$BaseUrl/api/v10/source2278/hardware/status" -TimeoutSec 20
Need ($h.ok -eq $true) "2278 hardware source OK"
Need ([int]$h.machines_checked -ge 1) "2278 machines available: $($h.machines_checked)"
$d = Invoke-RestMethod "$BaseUrl/api/v10/source2278/hardware?limit=5&freshness=fresh" -TimeoutSec 25
Need ($d.ok -eq $true) "fresh hardware API OK"
Need ($d.machines.Count -ge 1) "fresh machine rows available"
$s = Invoke-RestMethod "$BaseUrl/api/v10/source2278/software/status" -TimeoutSec 25
Need ($s.ok -eq $true) "software source OK"
Need ([int]$s.extracted_software_rows_total -ge 1) "software rows available: $($s.extracted_software_rows_total)"
Write-Host "=== V10 STABLE SELECTED-MACHINE NO-FLICKER TEST PASS ===" -ForegroundColor Green
