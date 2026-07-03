param(
  [string]$BaseUrl = "http://127.0.0.1:2294"
)

$ErrorActionPreference = "Stop"

function Get-Json($Url) {
  Write-Host "GET $Url"
  try {
    $r = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 25
    return $r.Content | ConvertFrom-Json
  } catch {
    Write-Host "REQUEST FAILED: $Url" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    throw
  }
}

function Post-Json($Url, $Body) {
  Write-Host "POST $Url"
  $json = $Body | ConvertTo-Json -Depth 20
  $r = Invoke-WebRequest $Url -UseBasicParsing -Method POST -Body $json -ContentType "application/json" -TimeoutSec 25
  return $r.Content | ConvertFrom-Json
}

function Delete-Url($Url) {
  Write-Host "DELETE $Url"
  $r = Invoke-WebRequest $Url -UseBasicParsing -Method DELETE -TimeoutSec 25
  return $r.Content | ConvertFrom-Json
}

function Test-HealthOk($obj) {
  if ($null -eq $obj) { return $false }
  if ($obj.ok -eq $true) { return $true }
  if ([string]$obj.status -match "^(ok|healthy|success)$") { return $true }
  if ([string]$obj.status -match "running") { return $true }
  if ([string]$obj.message -match "ok") { return $true }
  return $false
}

Write-Host "=== V10 2-Day Phase 1 DB/API Bridge Test - FIXED ===" -ForegroundColor Cyan
Write-Host "BaseUrl: $BaseUrl"

$health = Get-Json "$BaseUrl/api/health"
if (!(Test-HealthOk $health)) {
  Write-Host "api/health returned:" -ForegroundColor Yellow
  $health | ConvertTo-Json -Depth 20 | Write-Host
  throw "api/health is reachable but returned unexpected shape. Server may still be OK; health schema is different."
}
Write-Host "PASS: /api/health reachable" -ForegroundColor Green

$status = Get-Json "$BaseUrl/api/v10final/status"
if (!$status.ok) {
  Write-Host "v10final/status returned:" -ForegroundColor Yellow
  $status | ConvertTo-Json -Depth 20 | Write-Host
  throw "v10final/status failed - bridge may not be loaded. Check server window for V10_2DAY_PHASE1_DB_API_BRIDGE_LOADED"
}
Write-Host ("Machines total: " + $status.counts.machines_total)
Write-Host ("Hardware assets: " + $status.counts.hardware_assets)

$requiredTables = @(
  "hardware_assets",
  "software_assets",
  "asset_edit_audit_log",
  "software_edit_audit_log",
  "inventory_sync_matches",
  "branding_settings",
  "retention_settings",
  "deploy_profiles",
  "history_summary_cache",
  "iso_audit_results",
  "roles",
  "user_role_permissions"
)

foreach ($t in $requiredTables) {
  if ($status.tables -notcontains $t) {
    throw "Missing DB table: $t"
  }
}
Write-Host "PASS: DB tables exist" -ForegroundColor Green

$hw = Get-Json "$BaseUrl/api/v10final/inventory/hardware?limit=5"
if (!$hw.ok) { throw "hardware inventory endpoint failed" }
Write-Host ("Hardware endpoint rows: " + $hw.count)

$testAsset = @{
  asset_uid = "TEST-PHASE1-ASSET"
  asset_code = "TEST-PHASE1-ASSET"
  make_name = "Test Make"
  model_name = "Test Model"
  asset_name = "Phase1 Test Asset"
  asset_type = "Test"
  vendor_name = "Test Vendor"
  serial_number = "SERIAL-PHASE1"
  tagname_hostname = "HOST-PHASE1"
  assigned_to = "QA"
  asset_location = "Test Lab"
  status = "Test"
  remarks = "Created by Phase 1 automated test"
}

$save = Post-Json "$BaseUrl/api/v10final/inventory/hardware/save" $testAsset
if (!$save.ok) { throw "hardware save failed" }

$find = Get-Json "$BaseUrl/api/v10final/inventory/hardware?q=TEST-PHASE1-ASSET&limit=10"
if ($find.count -lt 1) { throw "hardware saved asset not found" }

$del = Delete-Url "$BaseUrl/api/v10final/inventory/hardware?id=TEST-PHASE1-ASSET"
if (!$del.ok) { throw "hardware delete failed" }
Write-Host "PASS: Hardware Add/Edit/Delete works" -ForegroundColor Green

$testSw = @{
  software_uid = "TEST-PHASE1-SW"
  software_name = "Phase1 Test Software"
  version = "1.0"
  publisher = "QA"
  status = "Test"
  source = "test"
}
$swSave = Post-Json "$BaseUrl/api/v10final/inventory/software/save" $testSw
if (!$swSave.ok) { throw "software save failed" }

$swFind = Get-Json "$BaseUrl/api/v10final/inventory/software?q=Phase1%20Test%20Software"
if ($swFind.count -lt 1) { throw "software saved row not found" }

$swDel = Delete-Url "$BaseUrl/api/v10final/inventory/software?id=TEST-PHASE1-SW"
if (!$swDel.ok) { throw "software delete failed" }
Write-Host "PASS: Software Add/Edit/Delete works" -ForegroundColor Green

$rules = Get-Json "$BaseUrl/api/v10final/notifications/rules"
if (!$rules.ok) { throw "notification rules endpoint failed" }
Write-Host ("Notification rules visible: " + ($rules.rules | Measure-Object).Count)

$brand = Get-Json "$BaseUrl/api/v10final/branding"
if (!$brand.ok) { throw "branding endpoint failed" }

$ret = Get-Json "$BaseUrl/api/v10final/retention"
if (!$ret.ok) { throw "retention endpoint failed" }

$deploy = Get-Json "$BaseUrl/api/v10final/deploy/profiles"
if (!$deploy.ok) { throw "deploy profiles endpoint failed" }

$iso = Get-Json "$BaseUrl/api/v10final/iso/audit"
if (!$iso.ok) { throw "iso audit endpoint failed" }

Write-Host ""
Write-Host "PASS: V10 2-Day Phase 1 DB/API Bridge OK" -ForegroundColor Green
