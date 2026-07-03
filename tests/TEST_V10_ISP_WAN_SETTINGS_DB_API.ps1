param(
  [string]$BaseUrl = "http://127.0.0.1:2294"
)
$ErrorActionPreference = "Stop"
Write-Host "=== V10 ISP/WAN Settings DB/API Test ===" -ForegroundColor Cyan
function Get-Json($Url){
  Write-Host "GET $Url" -ForegroundColor DarkCyan
  return Invoke-RestMethod -Uri $Url -UseBasicParsing -TimeoutSec 20
}
function Post-Json($Url, $Body){
  Write-Host "POST $Url" -ForegroundColor DarkCyan
  $json = $Body | ConvertTo-Json -Depth 20
  return Invoke-RestMethod -Uri $Url -Method Post -Body $json -ContentType "application/json" -UseBasicParsing -TimeoutSec 30
}
$health = Get-Json "$BaseUrl/api/health"
if($null -eq $health){ throw "api health not reachable" }
$list = Get-Json "$BaseUrl/api/v10/settings/isp-links"
if($list.max_isp_links -ne 10){ throw "max_isp_links should be 10" }
$save = Post-Json "$BaseUrl/api/v10/settings/isp-link" @{
  slot = 10
  enabled = $true
  isp_name = "SELFTEST ISP"
  wan_name = "WAN SELFTEST"
  router_ip = "127.0.0.1"
  gateway_ip = "127.0.0.1"
  interface_name = "SELFTEST"
  expected_download_mbps = 100
  expected_upload_mbps = 50
  role = "backup"
  notes = "temporary acceptance test row"
}
if(!$save.ok){ throw "save selftest ISP failed: $($save | ConvertTo-Json -Depth 10)" }
$list2 = Get-Json "$BaseUrl/api/v10/settings/isp-links"
$found = $false
foreach($l in $list2.links){ if($l.slot -eq 10 -and $l.isp_name -eq "SELFTEST ISP"){ $found = $true } }
if(!$found){ throw "saved selftest ISP not found in list" }
$status = Get-Json "$BaseUrl/api/v10/isp-wan/status?force=1"
if(!$status.ok){ throw "status failed" }
if($status.max_isp_links -ne 10){ throw "status max_isp_links missing" }
if($null -eq $status.links){ throw "status links missing" }
$tooMany = @()
for($i=1; $i -le 11; $i++){ $tooMany += @{slot=$i; isp_name="ISP $i"; wan_name="WAN $i"} }
$many = Post-Json "$BaseUrl/api/v10/settings/isp-links" @{ isp_links = $tooMany }
if($many.ok){ throw "saving 11 ISP links should fail" }
$del = Post-Json "$BaseUrl/api/v10/settings/isp-link/delete" @{ slot = 10 }
if(!$del.ok){ throw "delete selftest ISP failed" }
Write-Host "=== V10 ISP/WAN SETTINGS DB/API TEST PASS ===" -ForegroundColor Green
