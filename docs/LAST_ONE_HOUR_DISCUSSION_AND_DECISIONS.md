# LAST ONE HOUR DISCUSSION AND DECISIONS

This document stores the critical last discussion where the project direction was corrected.

## User's main point

The user said the issue is not only missing UI. The real issue is that the new V10 customer version must preserve all working modules and all small requirements from the last 14â€“15 days:

- CPU, GPU, RAM, SSD/HDD/NVMe logic.
- Correct client/machine count.
- Inventory logic.
- Notification logic.
- Database requirement.
- Optimization.
- CI/CD.
- Branding with company logo/person/photo in upper side/background.
- Settings, deploy, roles, retention.
- Old working model must be used as foundation.
- No restart from zero every few days.
- No more loop: database logic, machine logic, GPU logic, UI/UX logic repeated again and again.

## Assistant acknowledgement

The assistant acknowledged:

- The current V10 was not customer-ready.
- The old 2278 demo was already done and was not the solution.
- V10 is the required new version.
- Previous patch process caused frontend/backend logic to be overwritten or disconnected.
- Saying "use 2278" was not useful because the user needs the new V10 customer app.
- The proper solution is source-of-truth + GitHub + DB-first integrated build.

## GitHub decision

The user wants:

- GitHub repo created.
- Public repo is okay.
- All source stored there.
- Every new requirement, every error, every fix, every new step, and every completed part must be updated automatically.
- User should not have to remind every time to update GitHub.

The planned repo:

`https://github.com/sagarkerhalkar/SagarSystemHealthMonitor-V10`

Rules:

- Every apply script must call Git autosave if available.
- Requirement docs must be updated before/with code.
- Error/fix must be written to docs.
- Work log must be updated.
- Commit and push after changes.

## GitHub CLI issue

User ran:

```powershell
where.exe gh
gh --version
```

Output:

```text
INFO: Could not find files for the given pattern(s).
gh : The term 'gh' is not recognized as the name of a cmdlet...
```

Resolution package was created:

`GITHUB_CLI_MISSING_FIX_AND_AUTOSAVE.zip`

It installs/finds GitHub CLI, creates public repo, pushes source, adds docs, CI workflow, and installs autosave scheduled task.

## Permanent development commandment

No more final claim until:

- Source is committed.
- DB schema is correct.
- Backend APIs are tested.
- UI uses real APIs.
- Client data is verified.
- CI/security tests pass.
- Rollback exists.
