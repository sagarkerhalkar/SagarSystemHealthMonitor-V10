param([string]$BaseUrl = "http://127.0.0.1:2294")
$ErrorActionPreference = "Stop"
$routes = @(
  "/api/health",
  "/api/v10/status",
  "/api/v10/current-machines",
  "/api/v10/hardware-inventory",
  "/api/v10/gpu-inventory",
  "/api/v10/software-inventory",
  "/api/v10/usb-inventory",
  "/v10-integrated-inventory.html"
)
foreach ($r in $routes) {
  $u = $BaseUrl + $r
  $res = Invoke-WebRequest $u -UseBasicParsing
  Write-Host "OK $r status=$($res.StatusCode) bytes=$($res.Content.Length)" -ForegroundColor Green
}
Write-Host "V10 MERGE QA OK" -ForegroundColor Green
