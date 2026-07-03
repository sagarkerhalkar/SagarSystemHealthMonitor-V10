param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
Write-Host "=== GitHub Push Status Check ===" -ForegroundColor Cyan
if(!(Test-Path $App)){ throw "App not found: $App" }
Push-Location $App
try{
  if(!(Test-Path ".git")){ throw "Not a git repo: $App" }
  $remote=(git remote get-url origin).Trim()
  Write-Host "Remote: $remote"
  $local=(git rev-parse HEAD).Trim()
  git fetch origin main | Out-Null
  $remoteHead=(git rev-parse origin/main).Trim()
  Write-Host "Local HEAD : $local"
  Write-Host "Remote main: $remoteHead"
  if($local -eq $remoteHead){ Write-Host "PUSHED OK: local source and GitHub main are same commit." -ForegroundColor Green } else { Write-Host "NOT PUSHED: local and GitHub main are different." -ForegroundColor Red }
  Write-Host "`nLast 5 local commits:" -ForegroundColor Cyan
  git log -5 --oneline --decorate
  Write-Host "`nFiles not committed locally:" -ForegroundColor Cyan
  git status --short
} finally { Pop-Location }
