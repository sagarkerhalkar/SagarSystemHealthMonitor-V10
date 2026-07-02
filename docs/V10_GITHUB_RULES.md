# V10 GitHub Rules

Target repo: `sagarkerhalkar/SagarSystemHealthMonitor-V10`

## Required rule
Every code or requirement update must be committed to GitHub. The user should not need to remind anyone.

## Every apply script must do this at the end

```powershell
if (Test-Path "D:\SagarMonitor_V10_CleanBuild\scripts\GIT_AUTO_COMMIT_PUSH.ps1") {
  powershell -ExecutionPolicy Bypass -File "D:\SagarMonitor_V10_CleanBuild\scripts\GIT_AUTO_COMMIT_PUSH.ps1" -Message "Describe exact change"
}
```

## Files that must be versioned
- server source
- client source
- public UI files
- scripts
- tests
- docs
- requirements
- CI/CD workflow

## Files that must not be versioned
- DB files
- logs
- secrets
- `.env`
- large backups
- temporary build folders

