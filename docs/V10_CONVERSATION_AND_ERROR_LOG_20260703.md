# V10 Conversation + Error/Solution Log - 2026-07-03

## Locked user instruction
- User has 2 days to complete the new V10 customer version.
- GitHub must store source, requirements, errors, solutions, and discussion logs.
- User should not need to remind every time to update GitHub.
- No more UI-only patches. DB + API + real data + tests + GitHub update are mandatory.

## GitHub status
- Repo is visible: `sagarkerhalkar/SagarSystemHealthMonitor-V10`.
- Direct ChatGPT connector write was not permitted by GitHub integration, so all apply packages must write docs locally and run `git add/commit/push` from the user's server.
- Auto-save is active in work log and must be preserved.

## Phase 1 issue
- Phase 1 test failed multiple times because PowerShell test expected a different `/api/health` shape and had a `$ep:` syntax issue.
- Fix: health test must only check reachability; PowerShell variable followed by colon must use `${ep}:`.

## Phase 2 issue
- Phase 2 normalizer output showed CPU/RAM/disk/GPU/software/USB/network test payload, but `/api/v10phase2/selftest` returned `ok: false`.
- Root cause: selftest was passing old server normalizer/summarizer hooks into the isolated selftest, so the selftest could fail even when the new normalizer produced correct normalized data.
- Fix: Phase 2 fix v4 makes selftest isolated from old hooks and reports exact failed checks if any remain.

## Rule for every next package
Every apply package must:
1. Backup changed files.
2. Write docs work log and error/fix history.
3. Run syntax checks.
4. Commit and push to GitHub if git remote exists.
5. Provide rollback script if production behavior changes.

## 20260703_172740 - ISP/WAN Settings DB/API added
User requested admin-managed ISP details in Settings, maximum 10 ISP links. Implemented DB/API first and not UI patching.
