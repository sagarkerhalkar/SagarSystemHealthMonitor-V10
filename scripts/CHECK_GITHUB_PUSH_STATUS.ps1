param([string]$App="D:\SagarMonitor_V10_CleanBuild")
$ErrorActionPreference="Stop"
Push-Location $App
try {
  $branch = (git rev-parse --abbrev-ref HEAD).Trim()
  $local = (git rev-parse HEAD).Trim()
  git fetch origin $branch | Out-Null
  $remote = (git rev-parse "origin/$branch").Trim()
  Write-Host "branch: $branch"
  Write-Host "local : $local"
  Write-Host "remote: $remote"
  if($local -eq $remote){ Write-Host "PUSHED OK: local source and GitHub $branch are same commit." -ForegroundColor Green }
  else { throw "NOT PUSHED: local and remote are different." }
} finally { Pop-Location }
