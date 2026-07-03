param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
cd $App
Write-Host "=== GitHub Push Status Check ===" -ForegroundColor Cyan
Write-Host "Remote:" (git remote get-url origin)
$local=(git rev-parse HEAD).Trim()
git fetch origin main | Out-Null
$remote=(git rev-parse origin/main).Trim()
Write-Host "Local HEAD : $local"
Write-Host "Remote main: $remote"
if($local -eq $remote){ Write-Host "PUSHED OK: local source and GitHub main are same commit." -ForegroundColor Green; exit 0 }
Write-Host "NOT PUSHED: local and remote differ." -ForegroundColor Red
exit 1
