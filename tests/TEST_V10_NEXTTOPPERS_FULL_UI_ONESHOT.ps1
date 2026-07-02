param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
$Public=Join-Path $App "public"
$index=Get-Content (Join-Path $Public "index.html") -Raw
$css=Get-Content (Join-Path $Public "styles.css") -Raw
$js=Get-Content (Join-Path $Public "app.js") -Raw
foreach($s in @("Next Toppers","Company Website","Machine 360","Network + VPN","Hardware Intelligence","Software Intelligence","ISO Audit Center","Client Messages","Settings")){
  if(($index+$js) -notmatch [regex]::Escape($s)){ throw "Missing UI requirement text: $s" }
}
foreach($s in @("@media(max-width:1180px)","@media(max-width:860px)","@media(max-width:520px)","@media print")){
  if($css -notmatch [regex]::Escape($s)){ throw "Missing responsive/print rule: $s" }
}
if(($index+$css+$js) -match 'http://(?!127\.0\.0\.1|localhost)'){ throw "Insecure non-local http reference found" }
if(!(Test-Path (Join-Path $Public "assets\nexttoppers-logo.png"))){ throw "Logo asset missing" }
if(!(Test-Path (Join-Path $Public "assets\nexttoppers-team.png"))){ throw "Login photo asset missing" }
Write-Host "PASS: V10 Next Toppers full UI one-shot static test"
