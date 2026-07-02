param([string]$App = "D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference = "Stop"
Write-Host "=== V10 Security / CI static test ==="
$files = Get-ChildItem "$App\public" -File -Include *.js,*.html,*.css -Recurse -ErrorAction SilentlyContinue
foreach($f in $files){
  $txt = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
  if($txt -match 'http://(?!127\.0\.0\.1|localhost)') { throw "Insecure non-local http:// reference in $($f.FullName)" }
  if($txt -match '\beval\s*\(') { throw "eval() found in $($f.FullName)" }
  if($txt -match 'document\.write\s*\(') { throw "document.write() found in $($f.FullName)" }
}
Write-Host "PASS: static security checks OK."
