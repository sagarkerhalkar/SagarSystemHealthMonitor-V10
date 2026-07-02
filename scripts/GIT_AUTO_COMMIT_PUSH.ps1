param([string]$Message = "Auto-save V10 source")
$ErrorActionPreference = "Continue"
$App = Split-Path $PSScriptRoot -Parent
Set-Location $App

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$workLog = Join-Path $App "docs\V10_WORK_LOG.md"
if (!(Test-Path (Split-Path $workLog -Parent))) { New-Item -ItemType Directory -Path (Split-Path $workLog -Parent) -Force | Out-Null }
Add-Content -Path $workLog -Value "`n## $stamp`n$Message`n"

git add .
$status = git status --porcelain
if ($status) {
  git commit -m "$Message"
  git push
} else {
  Write-Host "No Git changes to commit."
}
