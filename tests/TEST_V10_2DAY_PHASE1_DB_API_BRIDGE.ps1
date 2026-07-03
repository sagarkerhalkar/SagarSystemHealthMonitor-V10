param(
  [string]$BaseUrl = "http://127.0.0.1:2294"
)

$ErrorActionPreference = "Stop"

function Convert-ResponseContentToText {
  param($Content)
  if ($null -eq $Content) { return "" }
  if ($Content -is [byte[]]) {
    return [System.Text.Encoding]::UTF8.GetString($Content)
  }
  if ($Content -is [System.Array] -and $Content.Length -gt 0 -and $Content[0] -is [byte]) {
    return [System.Text.Encoding]::UTF8.GetString([byte[]]$Content)
  }
  return [string]$Content
}

function Invoke-JsonGet {
  param([string]$Path)
  $url = "$BaseUrl/$($Path.TrimStart('/'))"
  Write-Host "GET $url" -ForegroundColor DarkCyan
  try {
    $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15 -Headers @{ "Cache-Control"="no-cache" }
  } catch {
    throw "GET failed for $url :: $($_.Exception.Message)"
  }
  $text = Convert-ResponseContentToText $resp.Content
  $out = [ordered]@{
    url = $url
    status_code = [int]$resp.StatusCode
    raw = $text
    json = $null
  }
  try {
    if ($text.Trim().Length -gt 0) { $out.json = $text | ConvertFrom-Json }
  } catch {
    $out.json = $null
  }
  return [pscustomobject]$out
}

function Assert-Reachable {
  param([string]$Name, $Result)
  if ($Result.status_code -lt 200 -or $Result.status_code -ge 300) {
    throw "$Name returned HTTP $($Result.status_code)"
  }
  Write-Host "PASS: $Name reachable HTTP $($Result.status_code)" -ForegroundColor Green
}

function Assert-JsonOkFlexible {
  param([string]$Name, $Result)
  Assert-Reachable $Name $Result
  if ($null -eq $Result.json) {
    Write-Host "RAW RESPONSE:" -ForegroundColor Yellow
    Write-Host $Result.raw
    throw "$Name returned non-JSON response"
  }

  $j = $Result.json
  $ok = $false
  if ($j.PSObject.Properties.Name -contains "ok" -and ($j.ok -eq $true -or "$($j.ok)".ToLower() -eq "true")) { $ok = $true }
  if ($j.PSObject.Properties.Name -contains "status" -and "$($j.status)".ToLower() -match "ok|healthy|running|loaded") { $ok = $true }
  if ($j.PSObject.Properties.Name -contains "success" -and ($j.success -eq $true -or "$($j.success)".ToLower() -eq "true")) { $ok = $true }
  if ($j.PSObject.Properties.Name -contains "loaded" -and ($j.loaded -eq $true -or "$($j.loaded)".ToLower() -eq "true")) { $ok = $true }

  if (!$ok) {
    Write-Host "JSON RESPONSE:" -ForegroundColor Yellow
    $j | ConvertTo-Json -Depth 20
    throw "$Name JSON did not contain ok/status/success/loaded marker"
  }
  Write-Host "PASS: $Name JSON OK" -ForegroundColor Green
}

Write-Host "=== V10 2-Day Phase 1 DB/API Bridge Test FIX2 ===" -ForegroundColor Cyan
Write-Host "BaseUrl: $BaseUrl"

# Health endpoint: only prove server is alive. Do not enforce old/new health JSON shape.
$health = Invoke-JsonGet "/api/health"
Assert-Reachable "/api/health" $health
Write-Host "Health raw preview:" -ForegroundColor Gray
Write-Host (($health.raw -replace "`r|`n", " ").Substring(0, [Math]::Min(300, $health.raw.Length)))

# Phase 1 bridge must exist.
$status = Invoke-JsonGet "/api/v10final/status"
Assert-JsonOkFlexible "/api/v10final/status" $status

$db = Invoke-JsonGet "/api/v10final/db/status"
Assert-Reachable "/api/v10final/db/status" $db
if ($null -eq $db.json) { throw "/api/v10final/db/status returned non-JSON" }
Write-Host "PASS: DB status JSON returned" -ForegroundColor Green

# Safe read endpoints. These prove API bridge is loaded without changing data.
$endpoints = @(
  "/api/v10final/machines",
  "/api/v10final/inventory/hardware",
  "/api/v10final/inventory/software",
  "/api/v10final/notifications/rules",
  "/api/v10final/branding",
  "/api/v10final/retention",
  "/api/v10final/deploy/profiles",
  "/api/v10final/iso/audit"
)

foreach ($ep in $endpoints) {
  $r = Invoke-JsonGet $ep
  Assert-Reachable $ep $r
  if ($null -eq $r.json) {
    Write-Host "RAW RESPONSE for ${ep}:" -ForegroundColor Yellow
    Write-Host $r.raw
    throw "$ep returned non-JSON"
  }
  Write-Host "PASS: $ep JSON returned" -ForegroundColor Green
}

Write-Host "=== PHASE 1 BASIC DB/API BRIDGE TEST PASSED ===" -ForegroundColor Green
Write-Host "Next: run deeper CRUD/API tests after confirming this basic bridge is loaded." -ForegroundColor Cyan

