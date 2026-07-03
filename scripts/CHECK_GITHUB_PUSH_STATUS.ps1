param([string]$App = "D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference = "Stop"
Write-Host "=== GitHub Push Status Check ===" -ForegroundColor Cyan
if (!(Test-Path $App)) { throw "App not found: $App" }
Push-Location $App
try {
  $remote = (git remote get-url origin 2>$null).Trim()
  Write-Host "Remote: $remote"
  git fetch origin main | Out-Null
  $local = (git rev-parse HEAD).Trim()
  $remoteHead = (git rev-parse origin/main).Trim()
  Write-Host "Local HEAD : $local"
  Write-Host "Remote main: $remoteHead"
  if ($local -eq $remoteHead) { Write-Host "PUSHED OK: local source and GitHub main are same commit." -ForegroundColor Green } else { Write-Host "NOT PUSHED: local and remote are different." -ForegroundColor Red }
  Write-Host "`nLast 5 commits:"
  git log -5 --oneline --decorate | Out-Host
  Write-Host "`nFiles not committed locally:"
  git status --short | Out-Host
} finally { Pop-Location }
