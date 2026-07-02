
param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
$Public=Join-Path $App "public"
$files=Get-ChildItem $Public -Recurse -File -Include *.html,*.js,*.css
foreach($f in $files){
  $t=Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
  if($t -match 'http://(?!127\.0\.0\.1|localhost)') { throw "Insecure http reference in $($f.FullName)" }
  if($t -match 'eval\s*\(') { throw "eval() found in $($f.FullName)" }
  if($t -match 'document\.write\s*\(') { throw "document.write found in $($f.FullName)" }
}
Write-Host "PASS: V10 UI static security checks" -ForegroundColor Green
