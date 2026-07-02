param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
$Public=Join-Path $App "public"
foreach($f in @("index.html","ui_fix4.js","ui_fix4_readability.css")){
  if(!(Test-Path (Join-Path $Public $f))){ throw "Missing $f" }
}
$idx=Get-Content (Join-Path $Public "index.html") -Raw
if($idx -notmatch "ui_fix4\.js"){ throw "index.html missing ui_fix4.js" }
if($idx -notmatch "ui_fix4_readability\.css"){ throw "index.html missing ui_fix4_readability.css" }
$js=Get-Content (Join-Path $Public "ui_fix4.js") -Raw
foreach($m in @("renderDeploy","renderMessages","renderHwInventory","renderSwInventory","renderNotifications","V10_UI_FIX4")){
  if($js -notmatch [regex]::Escape($m)){ throw "ui_fix4.js missing $m" }
}
$css=Get-Content (Join-Path $Public "ui_fix4_readability.css") -Raw
foreach($m in @("nt-login","deploy-hero","message-card","asset-table")){
  if($css -notmatch [regex]::Escape($m)){ throw "ui_fix4_readability.css missing $m" }
}
Write-Host "PASS: V10 UI Fix4 readability/deploy/messages/assets static test"