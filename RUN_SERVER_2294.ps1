param(
  [int]$Port = 2294
)

Set-Location $PSScriptRoot

$Server = Join-Path $PSScriptRoot "V10_IDENTITY_CORE_2294.py"
if (!(Test-Path $Server)) {
  $Server = Join-Path $PSScriptRoot "server.py"
}

Write-Host "Starting V10 server on port $Port..."
Write-Host "Server file: $Server"
Write-Host "App folder: $PSScriptRoot"

$env:SAGAR_MONITOR_PORT = "$Port"
$env:PORT = "$Port"

python $Server --host 0.0.0.0 --port $Port