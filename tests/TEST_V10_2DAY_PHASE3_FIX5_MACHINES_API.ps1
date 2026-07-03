param([string]$BaseUrl="http://127.0.0.1:2294")
$ErrorActionPreference="Stop"
Write-Host "=== V10 Phase3 Fix5 Machines API Test ===" -ForegroundColor Cyan
function Get-Json($path){
  $url="$BaseUrl$path"; Write-Host "GET $url" -ForegroundColor Gray
  $r=Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 20
  try { return $r.Content | ConvertFrom-Json } catch { throw "Non JSON from $path : $($r.Content.Substring(0,[Math]::Min(200,$r.Content.Length)))" }
}
$m=Get-Json "/api/v10final/machines"
if($null -eq $m.machines){ throw "machines api missing machines array after Fix5" }
if($null -eq $m.count){ throw "machines api missing count" }
Write-Host "Machine count: $($m.count), online: $($m.online_count), offline: $($m.offline_count), issues: $($m.issue_count)" -ForegroundColor Green
$ui=(Invoke-WebRequest "$BaseUrl/?phase3=fix4" -UseBasicParsing -TimeoutSec 20).Content
foreach($n in @("Machine Fleet","Machine 360","Hardware Asset Register","Software Asset Register","Created by","8105977226","sagarkerhalkar.com")){
  if($ui -notlike "*$n*"){ throw "index missing $n" }
}
Write-Host "=== PHASE3 FIX5 MACHINES API TEST PASS ===" -ForegroundColor Green
