param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
$Public=Join-Path $App "public"
foreach($f in @("index.html","app.js","style.css")){
  $p=Join-Path $Public $f
  if(!(Test-Path $p)){ throw "Missing $p" }
  if((Get-Item $p).Length -lt 100){ throw "Too small $p" }
}
$html=Get-Content (Join-Path $Public "index.html") -Raw
$js=Get-Content (Join-Path $Public "app.js") -Raw
$css=Get-Content (Join-Path $Public "style.css") -Raw
foreach($s in @("Next Toppers","Command Center","Machine 360","Notifications","Settings")){
  if(($html+$js+$css) -notmatch [regex]::Escape($s)){ throw "Missing UI text: $s" }
}
Write-Host "PASS: V10 UI restore smoke test"