param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
Write-Host "=== GitHub Push Status Check ===" -ForegroundColor Cyan
if(!(Test-Path $App)){ throw "App folder not found: $App" }
Push-Location $App
try {
  if(!(Get-Command git -ErrorAction SilentlyContinue)){ throw "git not found" }
  $remoteUrl = (git remote get-url origin 2>$null)
  if(!$remoteUrl){ throw "origin remote not configured" }
  Write-Host "Remote: $remoteUrl" -ForegroundColor Gray
  git fetch origin main --quiet
  $local = (git rev-parse HEAD).Trim()
  $remote = (git rev-parse origin/main).Trim()
  Write-Host "Local HEAD : $local"
  Write-Host "Remote main: $remote"
  if($local -eq $remote){
    Write-Host "PUSHED OK: local source and GitHub main are same commit." -ForegroundColor Green
  } else {
    Write-Host "NOT PUSHED: local and GitHub are different." -ForegroundColor Red
    Write-Host "Run: git push origin main" -ForegroundColor Yellow
  }
  Write-Host ""
  Write-Host "Last 5 local commits:" -ForegroundColor Cyan
  git log -5 --oneline --decorate
  Write-Host ""
  Write-Host "Files not committed locally:" -ForegroundColor Cyan
  git status --short
} finally { Pop-Location }
