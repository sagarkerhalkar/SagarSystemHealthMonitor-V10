param([string]$BaseUrl = "http://127.0.0.1:2294")
$ErrorActionPreference = "Stop"
Write-Host "=== V10 ISP/WAN Settings UI + Home Status Test ===" -ForegroundColor Cyan

function Convert-ContentToText($Content){
  if ($null -eq $Content) { return "" }
  if ($Content -is [byte[]]) { return [System.Text.Encoding]::UTF8.GetString($Content) }
  if ($Content -is [System.Array] -and $Content.Count -gt 0 -and $Content[0] -is [byte]) {
    return [System.Text.Encoding]::UTF8.GetString([byte[]]$Content)
  }
  return [string]$Content
}

function Get-Text($Url){
  $r = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 20
  $txt = Convert-ContentToText $r.Content
  if ($txt.Length -gt 0) { return $txt }
  return Convert-ContentToText $r.RawContent
}

function Get-Json($Url){
  try {
    return Invoke-RestMethod $Url -UseBasicParsing -TimeoutSec 20
  } catch {
    $txt = Get-Text $Url
    try { return $txt | ConvertFrom-Json } catch { throw "Non-JSON from $Url : $($txt.Substring(0,[Math]::Min(180,$txt.Length)))" }
  }
}

$index = Get-Text "$BaseUrl/"
$needles = @(
  "v10_isp_wan_settings_ui.js",
  "v10_isp_wan_settings_ui.css",
  "ISP / WAN Manager",
  "Organization ISP / WAN Health",
  "Maximum 10 ISP Links",
  "Created by Sagar Kerhalkar"
)
foreach($n in $needles){ if($index -notlike "*$n*"){ throw "index missing $n" } }
Write-Host "PASS: index has ISP/WAN UI markers" -ForegroundColor Green

$js = Get-Text "$BaseUrl/v10_isp_wan_settings_ui.js?v=test"
foreach($n in @("ISP / WAN Manager","api/v10/settings/isp-links","api/v10/isp-wan/status","Save All Visible ISP Links")){
  if($js -notlike "*$n*"){ throw "JS missing $n" }
}
Write-Host "PASS: JS available" -ForegroundColor Green

$links = Get-Json "$BaseUrl/api/v10/settings/isp-links"
if($links.ok -ne $true){ throw "isp-links api did not return ok" }
if($null -eq $links.max_isp_links){ throw "isp-links missing max_isp_links" }
if([int]$links.max_isp_links -ne 10){ throw "max_isp_links should be 10" }
Write-Host "PASS: settings ISP links API ok, current links: $(@($links.links).Count)" -ForegroundColor Green

$status = Get-Json "$BaseUrl/api/v10/isp-wan/status"
if($status.ok -ne $true){ throw "isp-wan status api did not return ok" }
if($null -eq $status.links){ throw "isp-wan status missing links" }
Write-Host "PASS: home ISP/WAN status API ok, total links: $($status.total_links)" -ForegroundColor Green

$sample = Invoke-WebRequest "$BaseUrl/api/v10/isp-wan/sample.csv" -UseBasicParsing -TimeoutSec 20
$sampleText = Convert-ContentToText $sample.Content
if($sampleText -notlike "*isp_name*"){ throw "sample CSV missing isp_name header" }
Write-Host "PASS: sample CSV available" -ForegroundColor Green

Write-Host "=== V10 ISP/WAN SETTINGS UI + HOME STATUS TEST PASS ===" -ForegroundColor Green
