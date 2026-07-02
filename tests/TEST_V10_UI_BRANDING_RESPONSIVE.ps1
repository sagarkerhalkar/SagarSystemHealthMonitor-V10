
param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
$Public=Join-Path $App "public"
$checks=@(
  (Join-Path $Public "index.html"),
  (Join-Path $Public "v10_nexttoppers_ui.css"),
  (Join-Path $Public "v10_nexttoppers_ui.js"),
  (Join-Path $Public "nt-brand.config.json"),
  (Join-Path $Public "assets\brand\nexttoppers_logo.png"),
  (Join-Path $Public "assets\brand\nexttoppers_login_photo.png")
)
foreach($c in $checks){ if(!(Test-Path $c)){ throw "Missing: $c" } }
$idx=Get-Content (Join-Path $Public "index.html") -Raw
if($idx -notmatch 'viewport'){ throw "Viewport meta missing" }
if($idx -notmatch 'v10_nexttoppers_ui.css'){ throw "CSS injection missing" }
if($idx -notmatch 'v10_nexttoppers_ui.js'){ throw "JS injection missing" }
$css=Get-Content (Join-Path $Public "v10_nexttoppers_ui.css") -Raw
if($css -notmatch '@media \(max-width:900px\)'){ throw "Responsive media query missing" }
if($css -notmatch 'prefers-reduced-motion'){ throw "Reduced motion support missing" }
Write-Host "PASS: V10 UI branding/responsive static checks" -ForegroundColor Green
