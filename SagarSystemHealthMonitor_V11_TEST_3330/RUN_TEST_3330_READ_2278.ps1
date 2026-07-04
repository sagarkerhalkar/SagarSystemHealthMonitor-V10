param(
  [string]$SourceUrl = "http://127.0.0.1:2278",
  [int]$Port = 3330,
  [string]$HostIp = "0.0.0.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Sagar Monitor V11 TEST on port $Port" -ForegroundColor Cyan
Write-Host " Reading live data from: $SourceUrl" -ForegroundColor Cyan
Write-Host " Folder: $Root" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

try {
  $h = Invoke-WebRequest "$SourceUrl/api/health" -UseBasicParsing -TimeoutSec 5
  Write-Host "2278 source health reachable: HTTP $($h.StatusCode)" -ForegroundColor Green
} catch {
  Write-Host "WARNING: 2278 source not reachable yet: $($_.Exception.Message)" -ForegroundColor Yellow
  Write-Host "Start your existing 2278 server first, then refresh 3330." -ForegroundColor Yellow
}

try {
  New-NetFirewallRule -DisplayName "Sagar Monitor TEST 3330" -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -ErrorAction SilentlyContinue | Out-Null
} catch {}

$env:CMP_SOURCE_2278 = $SourceUrl
$env:CMP_3330_PORT = "$Port"
$env:CMP_3330_HOST = $HostIp
$env:CMP_3330_ALLOW_WRITE_2278 = "0"

python -m py_compile .\server_3330_proxy.py
python -u .\server_3330_proxy.py --host $HostIp --port $Port --source $SourceUrl
