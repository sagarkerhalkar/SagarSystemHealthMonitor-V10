param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
$Public=Join-Path $App "public"
foreach($f in "index.html","customer_ready.js","customer_ready.css","assets\nexttoppers-logo.png","assets\nexttoppers-team.png"){
 if(!(Test-Path (Join-Path $Public $f))){ throw "Missing $f" }
}
$js=Get-Content (Join-Path $Public "customer_ready.js") -Raw
foreach($token in "Asset Register","openHwForm","Software Register","openSwForm","Client Messages","Deploy Center","Machine 360","Network + VPN","ISO Audit"){
 if($js -notmatch [regex]::Escape($token)){ throw "Missing token $token in customer_ready.js" }
}
$css=Get-Content (Join-Path $Public "customer_ready.css") -Raw
if($css -notmatch "@media\(max-width:1100px\)"){ throw "Responsive media query missing" }
Write-Host "PASS: V10 customer-ready UI static test"
