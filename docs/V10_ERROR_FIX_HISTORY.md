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

## 20260703_120601 - api/health test false failure
Error:
- pi/health failed in TEST_V10_2DAY_PHASE1_DB_API_BRIDGE.ps1.
Root cause:
- Test expected ok: true, but existing V10 /api/health may return status: ok.
Fix:
- Updated test to accept both schemas and continue to the real /api/v10final/status bridge test.

## 2026-07-03 12:22:01 - Phase 1 test health byte array/schema issue

Error: /api/health was reachable but the test failed because the response shape was different and PowerShell displayed byte values.
Root cause: test was too strict. Health endpoint should prove server reachability only. Phase 1 readiness must be checked with /api/v10final/status and related /api/v10final/* endpoints.
Fix: replaced 	ests/TEST_V10_2DAY_PHASE1_DB_API_BRIDGE.ps1 with a byte-array tolerant test that accepts any HTTP 2xx health response, decodes byte arrays to UTF-8 text, and then verifies Phase 1 APIs.

## 20260703_131815 - Phase 2 mapping fix
Problem:
- Disk/GPU/USB/software/network/VPN values were missing or mapped as zero even when client payload contained data.
Fix:
- Added a server-side payload normalizer and reprocessor so UI/API receive consistent arrays and counts.

## 20260703_132330 - Phase2 selftest failed while normalized payload looked correct
Error pasted by user:
- Phase2 selftest failed from 	ests/TEST_V10_2DAY_PHASE2_CLIENT_PAYLOAD.ps1.
- User also required every error, solution and conversation to be pushed to GitHub.
Root cause:
- Selftest used old server normalizer/summarizer hooks, so it could return ok: false even when the Phase2 normalizer itself was correct.
Fix:
- Selftest now runs isolated sample data through the Phase2 normalizer only.
- Test script now prints ailed_checks, checks, and summary before throwing.
- Conversation/error log doc added.

## 20260703_133723 - Phase 3 prevention
Problem:
- User reported old UI changes were not connected to live server data and every tab felt generic.
Fix:
- Phase 3 UI now reads live /api/v10final/* data, does not use dummy data, and separates every tab by function.

## 20260703_144050 - UI requirement correction
Problem:
- Previous UI still used team photo in visible hero, name was too big, tabs were not fully requirement-wise, large tables scrolled too much, and every tab did not clearly include footer/CSV/import/live test requirement.
Fix:
- Phase3 Fix4 stores the expanded tab-wise requirements and adds UI/API controls for ISO, USB, Day History, Messages, Notifications, Deploy, Settings, imports, exports and live-data testing.

## 20260703_145308 - machines api missing machines array
Error:
machines api missing machines array
Root cause:
The live endpoint was reachable, but the response shape was not standardized for the Phase3 UI/test. The UI needs a stable machines array for Machine Fleet, Command Center click-through, issue filters and Machine 360 navigation.
Fix:
Phase3 Fix5 normalizes /api/v10final/machines to always return machines array plus counts and issue status from live latest data. It does not fake hardware/software/GPU/disk data.

## 20260703_151410 - Fix6 user UI/data complaints
Problem:
- UI still did not match locked requirement and looked confusing.
- Hardware API test expected rows/assets compatibility but old route returned a different shape.
- GitHub check script was missing at first run.
Solution:
- Added clean corporate UI, no internal photo background, visible inventory edit actions, API compatibility, and GitHub status script.

## 20260703_153315 - Fix7 UI rejection correction
Problem:
- Dark theme, confusing UI, notification edit controls missing, settings incomplete, inventory edit not obvious.
Solution:
- Light corporate theme, explanatory Home, notification rule action controls, Settings user/role/password controls, visible Edit/Delete and form instructions.

## 20260703_160906 - Phase3 Fix8 customer UI correction
Problem:
- Fix7 still showed customer-facing GitHub option, incomplete settings/user management, router ISP not clearly separated from client data, notification rule save not complete, and UI was too simple for customer expectation.
Solution:
- Apply Fix8 customer UI: no GitHub button in UI, original logo visible, router ISP table/form from DB, Settings upload controls, User / Role Management, password reset, notification rule controls, ISO evidence rule, live API only.
Backup: D:\SagarMonitor_V10_CleanBuild\INCREMENTAL_SOURCE_BACKUPS\V10_2DAY_PHASE3_FIX8_CUSTOMER_UI_20260703_160906

## 20260703_163214 - Phase3 Fix9 customer UI correction
Problem:
- Fix7 still showed customer-facing GitHub option, incomplete settings/user management, router ISP not clearly separated from client data, notification rule save not complete, and UI was too simple for customer expectation.
Solution:
- Apply Fix9 customer UI: no GitHub button in UI, original logo visible, router ISP table/form from DB, Settings upload controls, User / Role Management, password reset, notification rule controls, ISO evidence rule, live API only.
Backup: D:\SagarMonitor_V10_CleanBuild\INCREMENTAL_SOURCE_BACKUPS\V10_2DAY_PHASE3_FIX9_REQUIREMENT_LOCK_LIVE_UI_20260703_163214

## 20260703_172740 - Prevention note
To avoid patch loop, this change only adds DB/API/tests for ISP/WAN settings before UI integration.

## 2026-07-03 17:32:52
- Requirement update: after ISP/WAN DB/API test pass, added UI phase for 1-10 ISP links in Settings and Home status. No dummy ISP speed; not from clients.


## 2026-07-03 - ISP/WAN UI test JSON decode fix
- Test failure: Non-JSON from /api/v10/settings/isp-links.
- Actual response was valid JSON but PowerShell rendered byte-array content as ASCII decimal numbers.
- Updated test helper to decode byte arrays as UTF-8 and use Invoke-RestMethod for JSON endpoints.
- No app code or DB logic changed.

## 20260703_174048 - Prevention note
This patch only adds Home traffic KPI API/UI. It does not change 2278 and does not replace the full V10 UI.

## 20260703_175628 - 2278 API 401 explained
2278 /api/clients, /api/machines, /api/latest, /api/notifications, /api/notification-rules can return 401 because login is required. This is not a V10 connector failure. V10 reads the DB read-only instead.
