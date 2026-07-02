# V10 GITHUB AUTOSAVE RULE

Target public repo:

`https://github.com/sagarkerhalkar/SagarSystemHealthMonitor-V10`

## Required behavior

After GitHub setup is complete, every script/package must run:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\SagarMonitor_V10_CleanBuild\scripts\GIT_AUTO_COMMIT_PUSH.ps1" -Message "meaningful change message"
```

## What must be committed

- Source code.
- Public UI.
- Scripts.
- Tests.
- Docs.
- Requirements.
- Work log.
- Error/fix history.
- CI workflow.

## What must not be committed

- DB files.
- Logs.
- Secrets.
- `.env`.
- Huge incremental backups.

## Auto-save schedule

Auto-save scheduled task should run every 30 minutes after setup.

## Manual emergency commit

```powershell
cd D:\SagarMonitor_V10_CleanBuild
powershell -ExecutionPolicy Bypass -File .\scripts\GIT_AUTO_COMMIT_PUSH.ps1 -Message "manual checkpoint"
```
