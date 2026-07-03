# V10 Error and Fix History

## 2026-07-02 - GitHub CLI missing

### Error
`gh : The term 'gh' is not recognized as the name of a cmdlet...`

### Root cause
GitHub CLI was not installed or not available in PowerShell PATH. Because of this, the repo creation script stopped before creating `sagarkerhalkar/SagarSystemHealthMonitor-V10`.

### Required fix
Install/find GitHub CLI using full path, then run browser login and create repo. Verify repo URL opens.

## 2026-07-02 - Repo not visible

### Error
`SagarSystemHealthMonitor-V10` repo not visible / Not Found.

### Root cause
Repo creation never completed due to missing `gh.exe`.

### Required fix
Run the GitHub repo create autofix script and verify final output shows repo URL.

## 2026-07-02 - Requirement memory incomplete

### Error
User reported all small requirements and progress were not mentioned.

### Root cause
Previous docs were not detailed enough and did not include full progress matrix.

### Required fix
Create and store `V10_COMPLETE_REQUIREMENT_PROGRESS_MATRIX.md` and keep it updated for every change.


## 20260703_120209 - Phase 1 prevention fix
Problem:
- Earlier builds changed UI before DB/API foundation.
Fix:
- Added DB-first bridge and tests before UI work.
