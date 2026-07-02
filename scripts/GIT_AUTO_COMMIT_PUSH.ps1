param(
  [string]$Message = ""
)

$ErrorActionPreference = "Stop"
$App = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $App

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
if ([string]::IsNullOrWhiteSpace($Message)) {
  $Message = "autosave: V10 source update $stamp"
}

if (Test-Path "docs\WORK_LOG.md") {
  Add-Content "docs\WORK_LOG.md" "`n## $stamp`n- Auto-save commit attempted.`n"
}

git add .
$pending = git status --porcelain

if ([string]::IsNullOrWhiteSpace($pending)) {
  Write-Host "No source changes to commit."
  exit 0
}

git commit -m "$Message"
git push
Write-Host "GitHub auto-save pushed."
