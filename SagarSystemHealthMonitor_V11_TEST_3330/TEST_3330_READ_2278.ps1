param(
  [string]$TestUrl = "http://127.0.0.1:3330",
  [string]$SourceUrl = "http://127.0.0.1:2278"
)
$ErrorActionPreference = "Continue"
Write-Host "Testing source 2278..." -ForegroundColor Cyan
Invoke-WebRequest "$SourceUrl/api/health" -UseBasicParsing -TimeoutSec 10 | Select-Object StatusCode, Content
Write-Host "Testing test bridge 3330..." -ForegroundColor Cyan
Invoke-WebRequest "$TestUrl/api/test3330/health" -UseBasicParsing -TimeoutSec 10 | Select-Object StatusCode, Content
Write-Host "Testing 3330 dashboard HTML..." -ForegroundColor Cyan
Invoke-WebRequest "$TestUrl/" -UseBasicParsing -TimeoutSec 10 | Select-Object StatusCode, @{n='Length';e={$_.Content.Length}}
Write-Host "Testing 3330 reading 2278 overview..." -ForegroundColor Cyan
Invoke-WebRequest "$TestUrl/api/overview" -UseBasicParsing -TimeoutSec 20 | Select-Object StatusCode, @{n='Length';e={$_.Content.Length}}
