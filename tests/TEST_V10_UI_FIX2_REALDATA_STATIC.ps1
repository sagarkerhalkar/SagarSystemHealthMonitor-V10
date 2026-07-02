
param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
$Index=Join-Path $App "public\index.html"; $Js=Join-Path $App "public\app.js"; $Css=Join-Path $App "public\styles.css"; $Style=Join-Path $App "public\style.css"; $Server=Join-Path $App "V10_IDENTITY_CORE_2294.py"
if(!(Test-Path $Server)){ $Server=Join-Path $App "server.py" }
$Need=@(@($Index,'retentionKeepDays'),@($Js,'activeNotificationSummary'),@($Js,'retention_keep_days'),@($Css,'V10_FIX2_READABILITY_START'),@($Style,'V10_FIX2_READABILITY_START'),@($Server,'retention_keep_days'))
foreach($n in $Need){ if(!(Test-Path $n[0])){throw "Missing file $($n[0])"}; $txt=Get-Content $n[0] -Raw; if($txt -notmatch [regex]::Escape($n[1])){throw "Missing marker '$($n[1])' in $($n[0])"} }
Get-ChildItem (Join-Path $App "public") -Recurse -Include *.js,*.html,*.css | ForEach-Object { $txt=Get-Content $_.FullName -Raw; if($txt -match 'http://(?!127\.0\.0\.1|localhost)'){throw "Insecure http reference in $($_.FullName)"} }
Write-Host "PASS: V10 UI Fix2 realdata/readability/deploy/retention static test"
