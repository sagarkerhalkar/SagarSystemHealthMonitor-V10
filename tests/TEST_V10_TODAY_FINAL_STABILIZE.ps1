param([string]$BaseUrl="http://127.0.0.1:2294", [string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
Write-Host "=== V10 TODAY FINAL STABILIZE TEST ===" -ForegroundColor Cyan
$h=Invoke-RestMethod "$BaseUrl/api/v10/app/health" -TimeoutSec 15
if(!$h.ok){ throw "health not ok" }
if($h.no_write_to_2278 -ne $true){ throw "no_write_to_2278 marker missing" }
Write-Host "PASS: health" -ForegroundColor Green
$m=Invoke-RestMethod "$BaseUrl/api/v10/app/machines" -TimeoutSec 30
if(!$m.ok){ throw "machines not ok" }
if([int]$m.count -lt 1){ throw "no machines returned" }
Write-Host ("PASS: machines count = {0}, clients = {1}" -f $m.count,$m.client_count) -ForegroundColor Green
$sample=@($m.clients | Select-Object -First 3)
if($sample.Count -lt 1){ $sample=@($m.machines | Select-Object -First 3) }
foreach($x in $sample){
  $mid=[string]$x.machine_id
  $enc=[uri]::EscapeDataString($mid)
  $hw=Invoke-RestMethod "$BaseUrl/api/v10/app/hardware?machine_id=$enc" -TimeoutSec 30
  if($hw.returned_machine_id -ne $mid){ throw "hardware returned wrong machine for $($x.hostname)" }
  $net=Invoke-RestMethod "$BaseUrl/api/v10/app/network?machine_id=$enc" -TimeoutSec 30
  if($net.returned_machine_id -ne $mid){ throw "network returned wrong machine for $($x.hostname)" }
  $sw=Invoke-RestMethod "$BaseUrl/api/v10/app/software?machine_id=$enc&limit=2000" -TimeoutSec 60
  if($sw.returned_machine_id -ne $mid){ throw "software returned wrong machine for $($x.hostname)" }
  Write-Host ("PASS: {0} CPU={1}% RAM={2}% Disk={3}% SW={4} USB={5}" -f $x.hostname,$hw.machine.cpu_percent,$hw.machine.ram_percent,$hw.machine.disk_max_percent,$sw.loaded_count,$hw.machine.usb_count) -ForegroundColor Green
}
try {
  Invoke-RestMethod "$BaseUrl/api/v10/app/hardware?machine_id=__BAD_MACHINE_ID__" -TimeoutSec 10 | Out-Null
  throw "bad machine id defaulted instead of error"
} catch {
  if($_.Exception.Message -match "bad machine id defaulted") { throw }
  Write-Host "PASS: bad machine id does not silently default" -ForegroundColor Green
}
Write-Host "=== V10 TODAY FINAL STABILIZE TEST PASS ===" -ForegroundColor Green
