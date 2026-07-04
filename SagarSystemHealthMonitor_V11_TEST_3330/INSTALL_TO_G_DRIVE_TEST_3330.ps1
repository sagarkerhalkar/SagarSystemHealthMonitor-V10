param(
  [string]$Target = "G:\SagarSystemHealthMonitor_V11_TEST_3330",
  [string]$SourceUrl = "http://127.0.0.1:2278",
  [int]$Port = 3330
)
$ErrorActionPreference = "Stop"
$Src = Split-Path -Parent $MyInvocation.MyCommand.Path
New-Item -ItemType Directory -Force -Path $Target | Out-Null
Write-Host "Copying V11 TEST 3330 package to $Target" -ForegroundColor Cyan
robocopy $Src $Target /E /XD __pycache__ /XF *.pyc | Out-Host
if ($LASTEXITCODE -le 7) { $global:LASTEXITCODE = 0 }
Write-Host "Done. Run:" -ForegroundColor Green
Write-Host "cd $Target" -ForegroundColor Yellow
Write-Host "powershell -ExecutionPolicy Bypass -File .\RUN_TEST_3330_READ_2278.ps1 -SourceUrl $SourceUrl -Port $Port" -ForegroundColor Yellow
