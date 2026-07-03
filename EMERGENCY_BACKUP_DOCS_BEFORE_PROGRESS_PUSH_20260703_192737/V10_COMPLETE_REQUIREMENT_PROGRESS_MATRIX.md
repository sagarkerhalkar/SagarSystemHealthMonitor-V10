# V10 Complete Requirement + Progress Matrix

Date: 2026-07-02
Project: **Sagar Kerhalkar System Health Monitor Tool - V10 / Next Toppers Customer Version**
Owner GitHub: `sagarkerhalkar`
Target repo: `sagarkerhalkar/SagarSystemHealthMonitor-V10`
Target local source: `D:\SagarMonitor_V10_CleanBuild`
Protected old/live demo source: `D:\SagarSystemHealthMonitor` on port `2278` - **do not touch unless explicitly approved**.
V10 development/test port: `2294`.

## Purpose of this file
This is the master source-of-truth file. Every future code change, error, requirement, failure, fix, and test result must update this file or a linked document inside `docs/` before the change is called complete.

## User's core complaint and locked rule
The user did not ask for repeated UI patches. The user asked for one complete working web app where all small requirements from the last 14-15 days remain connected together: database, backend, client payload, UI, inventory, notification, deploy, settings, optimization, CI/CD, branding, and real-data testing.

From now on:

1. No more UI-only patches.
2. No replacement of old working modules without backup and rollback.
3. No feature is complete until DB + API + UI + test + Git commit are done.
4. No fake data. If a client does not report GPU/disk/USB/etc., show `Not reported` with reason.
5. Every requirement and progress update must be committed to GitHub when the repo is ready.

---

# A. Current source-study truth from uploaded project ZIP

The uploaded source study showed the following real status:

| Area | Current truth |
|---|---|
| Active V10 DB | `D:\SagarMonitor_V10_CleanBuild\data\monitor_v10_notify.db` |
| Current DB tables found | `latest`, `heartbeats`, `notifications`, `notification_rules`, `notification_state`, `client_messages`, `client_message_receipts`, `change_events`, `settings`, `users` |
| Missing DB tables | hardware inventory, software licenses/assets, edit audit logs, branding settings, retention settings, deploy profiles, ISO audit results, history cache, roles/permissions, inventory sync matches |
| Live machine sample | `HOSTNAME:DESKTOP-1VTKP12` |
| Live CPU/RAM | CPU and RAM data present in sample |
| Live software | Payload contains 131 apps, but summary mapping showed `software_count: 0`; this is a mapping bug |
| Disk/SSD | `disk_max_percent: 0.0`; payload/mapping/client disk logic incomplete or not reported correctly |
| GPU | empty/not reported; must show real GPU only or `Not reported` |
| USB/peripherals | summary showed `usb_count: 0`; old logic exists in backups but active UI/backend not properly connected |
| H/W inventory | uploaded H/W inventory exists, about 370 rows |
| S/W license inventory | file exists but usable license rows are 0; must not fake rows |
| Notification backend | core policy fixed: CPU+RAM critical, disk high, GPU temp high, CPU temp high if real; CPU-only/RAM-only locked disabled |
| Change events | table exists but count 0; change detection not complete |
| UI status | last preferred UI was around 65% acceptable; latest/current UI became dirty and backend logic disconnected |
| GitHub repo | intended repo not visible yet because repo creation failed when `gh.exe` was missing |

---

# B. Requirement + progress checklist

Legend:
- ✅ Complete / verified enough to preserve
- 🟡 Partial / exists but incomplete or not connected
- ❌ Missing / not done
- 🔴 Broken / caused regression or wrong delivery

## 1. Source control, memory, and process

| ID | Requirement | Status | Notes / next action |
|---|---|---:|---|
| SCM-01 | Create GitHub repo `sagarkerhalkar/SagarSystemHealthMonitor-V10` | ❌ | Not visible yet. Previous creation failed due missing `gh.exe`. Must complete repo creation first. |
| SCM-02 | Push full V10 source to GitHub | ❌ | Source must be pushed after repo creation. Avoid DB/log/secrets. |
| SCM-03 | Auto-save to GitHub after every change | 🟡 | Auto-save scripts were prepared, but repo not created yet; not active. |
| SCM-04 | Every new requirement committed to docs | 🟡 | Several docs made, but user says incomplete; this file becomes the master. |
| SCM-05 | Work log maintained after each change | ❌ | Need `docs/V10_WORK_LOG.md` updated every time. |
| SCM-06 | Error/fix history maintained | ❌ | Need `docs/V10_ERROR_FIX_HISTORY.md` updated for every pasted error. |
| SCM-07 | Backup before each apply | 🟡 | Some patches backed up; must become mandatory scripted backup. |
| SCM-08 | Rollback script for each delivery | ❌ | Must be included before next code delivery. |
| SCM-09 | No blind patch loop | 🔴 | Failed today; now locked as rule. |

## 2. Database requirements

| ID | Requirement | Status | Notes / next action |
|---|---|---:|---|
| DB-01 | Stable V10 DB file path | ✅ | `data\monitor_v10_notify.db` identified. |
| DB-02 | `latest` machine summary table | ✅ | Exists. |
| DB-03 | `heartbeats` table | ✅ | Exists. |
| DB-04 | `notifications` table | ✅ | Exists. |
| DB-05 | `notification_rules` table | ✅ | Exists. |
| DB-06 | `notification_state` table | ✅ | Exists. |
| DB-07 | `client_messages` table | ✅ | Exists. |
| DB-08 | `client_message_receipts` table | ✅ | Exists. |
| DB-09 | `change_events` table | 🟡 | Exists but empty; detection logic incomplete. |
| DB-10 | `users` table | 🟡 | Exists with role field; missing full permissions/admin flows. |
| DB-11 | `settings` table | 🟡 | Exists; not complete for branding/retention/deploy profiles. |
| DB-12 | `hardware_assets` / `hw_assets` table | ❌ | Required for 370-row inventory Add/Edit/Delete. |
| DB-13 | `software_assets` / `software_licenses` table | ❌ | Required for S/W Register and license CRUD. |
| DB-14 | `inventory_sync_matches` table | ❌ | Required to match live machine to inventory asset by serial/hostname/tag/IP/MAC. |
| DB-15 | `asset_edit_audit_log` table | ❌ | Required for H/W audit. |
| DB-16 | `software_edit_audit_log` table | ❌ | Required for S/W audit. |
| DB-17 | `branding_settings` table or settings keys | ❌ | Required for logo, company website, login photo, company name. |
| DB-18 | `retention_settings` table or settings keys | 🟡 | Partial scripts exist; must connect to UI and cleanup. |
| DB-19 | `deploy_profiles` table | ❌ | Required for real deploy command center. |
| DB-20 | `history_summary_cache` table | ❌ | Required for fast Day History, no heavy heartbeat page. |
| DB-21 | `iso_audit_results` or computed audit view | ❌ | Required for ISO Audit Center. |
| DB-22 | Indexes for machine/time/serial/tag/app | 🟡 | Some indexes exist; missing for future tables. |
| DB-23 | Safe migration script, idempotent | ❌ | Next build must start here. |
| DB-24 | DB migration test | ❌ | Must be in CI/local tests. |

## 3. Client and machine data collection

| ID | Requirement | Status | Notes / next action |
|---|---|---:|---|
| CL-01 | Windows client heartbeat every 5-15 sec | 🟡 | Some heartbeat works; verify interval and stability. |
| CL-02 | Ubuntu client heartbeat | 🟡 | Required; current parity not verified. |
| CL-03 | Correct live client count | 🟡 | `latest` has sample; needs verified count logic online/offline. |
| CL-04 | Online/offline status | 🟡 | last heartbeat exists; need clear offline timeout and UI. |
| CL-05 | Hostname | ✅ | sample hostname present. |
| CL-06 | Machine identity by motherboard serial first | 🟡 | hostname fallback exists; serial logic needs verification. |
| CL-07 | Multi-LAN IP addresses | 🟡 | sample only one IP; all-IP logic must be verified. |
| CL-08 | MAC addresses | ❌ | Not verified in current summary. |
| CL-09 | OS name/version | 🟡 | Windows present; Ubuntu parity not verified. |
| CL-10 | CPU percent | ✅ | sample CPU present. |
| CL-11 | CPU name/model | ❌ | Required; not verified in summary. |
| CL-12 | CPU cores/logical processors | ❌ | Required; not verified. |
| CL-13 | CPU temperature real only | 🟡 | Notification rule exists; client real temp not verified. |
| CL-14 | RAM percent | ✅ | sample RAM present. |
| CL-15 | RAM total GB | ✅ | sample RAM total present. |
| CL-16 | RAM used/free GB | 🟡 | summary showed 0 used/free despite percent; mapping bug. |
| CL-17 | SSD/HDD/NVMe capacity and usage | ❌ | sample disk max 0; client or mapping broken. |
| CL-18 | Multiple disks names/types | ❌ | Required. |
| CL-19 | Disk free/used percent | ❌ | Required. |
| CL-20 | GPU name | ❌ | Not reported. |
| CL-21 | GPU memory | ❌ | Not reported. |
| CL-22 | GPU usage/temp real only | ❌ | Rule exists, client data not verified. |
| CL-23 | Installed software list Windows | 🟡 | Payload has 131 apps; summary mapping bug. |
| CL-24 | Installed software list Ubuntu | ❌ | Not verified. |
| CL-25 | USB/peripheral list Windows | 🟡 | Old logic exists, active summary 0; needs reconnect. |
| CL-26 | Keyboard/mouse/headset/USB storage | ❌ | Required and not verified. |
| CL-27 | VPN status | 🟡 | summary false; detection not verified. |
| CL-28 | Current upload/download speed | 🟡 | summary 0; live adapter usage not fully verified. |
| CL-29 | Daily upload/download totals | ❌ | Required; not verified. |
| CL-30 | ISP/provider name | 🟡 | server ISP cache exists; UI integration incomplete. |
| CL-31 | Latency/jitter/loss | 🟡 | Required; not fully connected. |
| CL-32 | Sudden power off/restart handling | 🟡 | Needs offline timeout and last heartbeat UI. |
| CL-33 | Client popup message for 2 minutes with close | 🟡 | Message tables exist; client delivery/popup not fully verified. |
| CL-34 | Client self-update/deploy command | ❌ | Deploy Center wrong/incomplete. |

## 4. Notification rules

| ID | Requirement | Status | Notes / next action |
|---|---|---:|---|
| NTF-01 | CPU-only high alert disabled | ✅ | Locked disabled by triggers. |
| NTF-02 | RAM-only high alert disabled | ✅ | Locked disabled by triggers. |
| NTF-03 | CPU+RAM both critical alert | ✅ | Backend policy fixed. |
| NTF-04 | Disk/SSD/HDD/NVMe >= 90 alert | ✅ | Backend rule exists. |
| NTF-05 | GPU temp >= 90 if real | ✅ | Rule exists. |
| NTF-06 | CPU temp >= 90 if real | ✅ | Rule exists. |
| NTF-07 | Notification cooldown | ✅ | Table has cooldown. |
| NTF-08 | Show active/off/locked clearly in UI | 🟡 | Page looked okay in one build; latest UI not trusted. |
| NTF-09 | Avoid duplicate alerts | 🟡 | User saw duplicate disk high; must deduplicate. |
| NTF-10 | Notification test script | 🟡 | Some tests exist; must be part of CI. |

## 5. Inventory requirements

| ID | Requirement | Status | Notes / next action |
|---|---|---:|---|
| INV-01 | H/W inventory uploaded count 370 | ✅ | Source files show 370-row H/W inventory. |
| INV-02 | Import 370 H/W rows into DB | ❌ | Files exist but not final DB table. |
| INV-03 | H/W Asset Register professional UI | 🔴 | Latest UI dirty/generic; must rebuild on real API. |
| INV-04 | H/W Add | ❌ | Required DB/API/UI. |
| INV-05 | H/W Edit | ❌ | Required DB/API/UI. |
| INV-06 | H/W Delete | ❌ | Required DB/API/UI. |
| INV-07 | H/W edit audit log | ❌ | Required. |
| INV-08 | H/W search/filter | 🟡 | Some frontend search existed in old UI; not complete. |
| INV-09 | H/W export CSV/PDF | 🟡 | Required; not fully verified. |
| INV-10 | Vendor Name column | 🟡 | In CSV but must map in DB/UI. |
| INV-11 | Make Name column | 🟡 | In CSV but must map in DB/UI. |
| INV-12 | Model Name column | 🟡 | In CSV but must map in DB/UI. |
| INV-13 | Warranty End Date / Year | 🟡 | In requirement; DB/UI missing. |
| INV-14 | Purchase Date | 🟡 | In requirement; DB/UI missing. |
| INV-15 | Invoice/PO/Bill no/path | 🟡 | In requirement; DB/UI missing. |
| INV-16 | Tag/hostname | 🟡 | In files; live sync incomplete. |
| INV-17 | Serial number | 🟡 | In files; matching incomplete. |
| INV-18 | Assigned To | 🟡 | Required; UI/DB incomplete. |
| INV-19 | Location | 🟡 | Required; UI/DB incomplete. |
| INV-20 | Status | 🟡 | Required; UI/DB incomplete. |
| INV-21 | Remarks | 🟡 | Required; UI/DB incomplete. |
| INV-22 | Live sync status | ❌ | Requires matching table/API. |
| INV-23 | S/W license inventory file | ✅ | File exists but empty usable data. |
| INV-24 | S/W license rows shown honestly as 0 | 🟡 | Must show honest message, no fake rows. |
| INV-25 | S/W Add/Edit/Delete | ❌ | Required DB/API/UI. |
| INV-26 | Live software list per machine | 🟡 | Payload exists; UI/mapping bug. |
| INV-27 | S/W license match/unmatch | ❌ | Required. |
| INV-28 | Inventory sync by serial/hostname/IP/MAC/tag | ❌ | Required. |

## 6. Page-wise web app requirements

| ID | Page / feature | Status | Notes / next action |
|---|---|---:|---|
| UI-01 | Login page with Next Toppers logo/person photo | 🟡 | Assets exist, integration inconsistent. |
| UI-02 | Logo in top/header and suitable background | 🟡 | Basic requirement not consistently applied. |
| UI-03 | Company website link `https://www.nexttoppers.com/` | 🟡 | Required in branding/settings. |
| UI-04 | International-level design | 🔴 | Latest UI became dirty; last acceptable UI around 65%. |
| UI-05 | Responsive mobile/tablet/iPad/Apple/laptop | 🟡 | Static responsive tests partial; not verified. |
| UI-06 | Classic readable font, no hidden text | 🔴 | Previous UI had readability complaints. |
| UI-07 | Command Center real overview | 🟡 | Page exists but not all real data connected. |
| UI-08 | Fleet total/online/offline/attention | 🟡 | Needs correct count/offline logic. |
| UI-09 | ISP/router health overview | 🟡 | Required; partial server cache. |
| UI-10 | Active backend alerts in overview | 🟡 | Requires API/UI. |
| UI-11 | Recent human changes in overview | ❌ | change_events empty. |
| UI-12 | Machine Fleet page | 🟡 | Exists partially. |
| UI-13 | Machine click opens Machine 360 | 🟡 | Old logic exists; current needs verify. |
| UI-14 | Machine 360 full story | 🔴 | Not fully connected to DB/client/inventory. |
| UI-15 | Machine 360 CSV/PDF download | ❌ | Required. |
| UI-16 | Network + VPN machine-wise | ❌ | Required; not mixed across all machines. |
| UI-17 | Hardware Intelligence machine-wise | ❌ | Required. |
| UI-18 | Software Intelligence machine-wise | ❌ | Required. |
| UI-19 | Hardware Asset Register | 🔴 | Not correct final. |
| UI-20 | Software Register | ❌ | Not correct final. |
| UI-21 | ISO Audit Center | 🟡 | Old UI existed; backend DB missing. |
| UI-22 | USB + Peripherals old logic preserved | 🟡 | Old good logic in backup; active app not verified. |
| UI-23 | Human Change Log machine/day-wise | ❌ | Required; table empty. |
| UI-24 | Day History fast/no heavy samples | 🟡 | Need history cache and UI. |
| UI-25 | Client Messages professional UI | 🟡 | Tables exist; UI/history/popup incomplete. |
| UI-26 | Notifications page active/off/locked | 🟡 | Partially okay in previous build. |
| UI-27 | Deploy Center real commands | 🔴 | Wrong/incomplete commands; must rebuild. |
| UI-28 | Settings users/roles | 🟡 | Basic users present; role permissions incomplete. |
| UI-29 | Settings branding/logo/company/photo | 🟡 | Assets present; DB/UI incomplete. |
| UI-30 | Settings retention days | 🟡 | Script partial; UI/backend not complete. |
| UI-31 | Settings password change/reset | 🟡 | Basic partial; must verify. |
| UI-32 | Viewer no download rights | ❌ | Required permissions not implemented/verified. |
| UI-33 | Admin/Super Admin download/create users | ❌ | Required permissions not fully implemented. |
| UI-34 | All tabs different real modules | 🔴 | User saw repeated/generic tabs. |

## 7. Deploy and public access requirements

| ID | Requirement | Status | Notes / next action |
|---|---|---:|---|
| DEP-01 | V10 server run command on 2294 | 🟡 | Existing run scripts; verify. |
| DEP-02 | Windows client install command for V10 | ❌ | Must be accurate and not wrongly use 2278. |
| DEP-03 | Windows client update command | ❌ | Required. |
| DEP-04 | Ubuntu client install/update command | ❌ | Required. |
| DEP-05 | Domain/server URL config | 🟡 | `monitor.sagarkerhalkar.com` known; V10 mapping must be clear. |
| DEP-06 | Public/domain instructions | 🟡 | Existing docs but deploy UI incomplete. |
| DEP-07 | Push updated client code to clients | ❌ | Required future deploy/update mechanism. |
| DEP-08 | Multi-LAN client deployment guidance | ❌ | User mentioned LANs 156.156.10/20/5/30/40/50/12 etc.; must document/implement. |
| DEP-09 | Autostart server task | 🟡 | Main has scripts; V10 needs safe version. |
| DEP-10 | Cloudflare/tunnel/domain test | 🟡 | Existing scripts but must align with V10. |

## 8. Reports, exports, and audit

| ID | Requirement | Status | Notes / next action |
|---|---|---:|---|
| REP-01 | Machine 360 CSV export | ❌ | Required. |
| REP-02 | Machine 360 PDF export | ❌ | Required. |
| REP-03 | H/W inventory CSV export | 🟡 | Some data files exist; UI/API export must be verified. |
| REP-04 | H/W inventory PDF export | ❌ | Required. |
| REP-05 | S/W inventory CSV export | ❌ | Required. |
| REP-06 | S/W inventory PDF export | ❌ | Required. |
| REP-07 | ISO H/W download separate | ❌ | Required. |
| REP-08 | ISO S/W download separate | ❌ | Required. |
| REP-09 | Date range export for day history | ❌ | Required. |
| REP-10 | Human-readable table/download | ❌ | Required. |

## 9. Optimization requirements

| ID | Requirement | Status | Notes / next action |
|---|---|---:|---|
| OPT-01 | No heavy heartbeat sample UI | 🟡 | Need history cache. |
| OPT-02 | Pagination for inventory/software | ❌ | Required. |
| OPT-03 | Indexed DB queries | 🟡 | Existing index limited; add for new DB. |
| OPT-04 | Summary cache | ❌ | Required. |
| OPT-05 | Incremental source backups only | 🟡 | Some backups; must automate. |
| OPT-06 | Do not copy full live DB unless needed | ✅ | Rule locked. |
| OPT-07 | Avoid frontend rendering huge tables | ❌ | Required. |
| OPT-08 | Client heartbeat stable and no flicker | 🟡 | Earlier flicker issue; must test. |
| OPT-09 | Machine selection must not jump to another machine | 🟡 | Previously complained; must verify. |

## 10. CI/CD, security, and tests

| ID | Requirement | Status | Notes / next action |
|---|---|---:|---|
| TEST-01 | Static frontend test | 🟡 | Some tests exist but not comprehensive. |
| TEST-02 | API route test | ❌ | Required. |
| TEST-03 | DB schema migration test | ❌ | Required. |
| TEST-04 | Inventory CRUD test | ❌ | Required. |
| TEST-05 | Notification rule test | 🟡 | Partial exists. |
| TEST-06 | Role permission test | ❌ | Required. |
| TEST-07 | Browser responsive smoke test | 🟡 | Static only; manual checklist needed. |
| TEST-08 | Security static test | 🟡 | Partial only. |
| TEST-09 | No secrets in public JS | 🟡 | Must test. |
| TEST-10 | No wrong external HTTP except localhost/test | 🟡 | Must test. |
| TEST-11 | GitHub Actions workflow | 🟡 | Scripts prepared but repo not active. |
| TEST-12 | Rollback test | ❌ | Required. |
| TEST-13 | Customer demo checklist | ❌ | Required. |
| TEST-14 | Final delivery cannot pass if any critical item is red | ✅ | Rule locked. |

## 11. Today's failure report summary

| Failure | What happened | Correct prevention |
|---|---|---|
| UI overwrite | Working modules were overwritten/disconnected by new UI packages. | DB/API freeze first, module-level diff review, backup/rollback. |
| Incomplete requirement docs | User said all small requirements were not mentioned. | This complete matrix must be maintained. |
| DB missing | UI pages were delivered before proper DB schema. | Phase 1 must be DB-first. |
| Backend disconnected | Inventory/UI called APIs that missing module/tables could not support. | API tests before UI delivery. |
| Dirty current UI | Last 65% acceptable UI was not preserved properly. | Restore acceptable UI baseline, then connect real APIs. |
| GitHub not visible | Repo creation failed because `gh.exe` missing. | Fix GitHub CLI install/auth and verify repo URL. |
| False final language | Packages were called final/customer-ready before full verification. | No final claim until checklist passes. |

---

# C. Required delivery roadmap to fulfill all requirements

## Phase 0 - GitHub + Freeze + Source Baseline (0.5 day)

Deliverables:
- GitHub repo visible.
- Current source pushed.
- `docs/` contains this file and work/error/test logs.
- Current V10 backed up.
- Last acceptable UI baseline identified.
- Main 2278 protected.

Acceptance:
- Repo URL opens.
- `git status` clean.
- `V10 starts on 2294`.
- rollback folder created.

## Phase 1 - Database-first migration (1 day)

Deliverables:
- Idempotent DB migration script creates all missing tables.
- Import 370 H/W inventory rows into `hardware_assets`.
- Honest S/W register state: 0 uploaded license rows but live apps available.
- Add indexes.
- Add audit tables.
- Add settings for branding/retention/deploy.

Acceptance:
- DB schema test passes.
- Counts test shows H/W rows = 370.
- No live DB destructive overwrite.

## Phase 2 - Backend API bridge (1 to 1.5 days)

Deliverables:
- Overview API.
- Machines API.
- Machine 360 API.
- Network/VPN API.
- Hardware/software intelligence APIs.
- Inventory CRUD APIs.
- ISO audit API.
- Settings/users/roles APIs.
- Deploy APIs.
- Messages APIs.
- Notifications API.

Acceptance:
- API tests pass with current DB.
- No UI tab calls missing endpoint.

## Phase 3 - Client payload completeness (1 day)

Deliverables:
- Windows client sends CPU/RAM/disk/GPU-if-real/USB/network/VPN/software/upload-download/latency.
- Ubuntu client parity where possible.
- Summary mapping fixed: software count 131 must show correctly for sample.
- Disk mapping fixed: real disk data must show or clear Not reported.
- GPU shows real data or Not reported.

Acceptance:
- One real Windows machine verified.
- One Ubuntu machine verified if available.
- Machine 360 data matches raw payload.

## Phase 4 - Frontend integrated web app (2 days)

Deliverables:
- Restore acceptable UI quality, not dirty current UI.
- Next Toppers logo/photo in login/header/background where suitable.
- Every page is a real module.
- All pages use real APIs, not placeholders.
- Responsive UI.
- Exports where required.

Acceptance:
- Page-by-page checklist passes.
- User confirms UI quality before final packaging.

## Phase 5 - Optimization + CI/CD + Security + Delivery (1 day)

Deliverables:
- Pagination/cache/history optimization.
- CI workflow.
- Security tests.
- Role tests.
- Rollback script.
- Customer demo checklist.
- Final ZIP/installer.

Acceptance:
- All tests pass.
- GitHub Actions green.
- Rollback tested.
- Final app can be called customer-ready.

---

# D. Definition of 100% working app

The app is 100% working only when every critical item below passes:

1. V10 starts on port 2294.
2. Login works.
3. Roles work: Super Admin, Admin, Viewer.
4. Branding works: logo, company photo, company website, login/header/background.
5. Command Center shows real fleet count and real alerts.
6. Machine Fleet count is correct.
7. Machine click opens the correct Machine 360 and does not switch/jump.
8. Machine 360 shows CPU/RAM/disk/GPU/USB/software/network/VPN/inventory match.
9. CPU/RAM values match latest payload.
10. Disk/SSD/HDD/NVMe shows real data or clear Not reported reason.
11. GPU shows real data or clear Not reported reason.
12. Live software count maps correctly from payload.
13. USB/peripherals logic works and is understandable.
14. H/W inventory count = 370 after import.
15. H/W Add/Edit/Delete works.
16. H/W audit log records changes.
17. S/W Register shows live apps and honest license state.
18. S/W Add/Edit/Delete works when license rows exist or are manually added.
19. Inventory sync matches live machines to assets.
20. ISO Audit shows missing invoice/warranty/serial/unmatched machine/unmatched asset.
21. Client Messages send and history work.
22. Client popup delivery works where client supports it.
23. Notifications follow locked policy.
24. Deploy Center commands are correct for V10.
25. Settings users/password/branding/retention work.
26. Day History loads fast and does not hang.
27. Change Log shows meaningful changes by machine/day.
28. CSV/PDF exports work.
29. CI/CD tests pass.
30. Security tests pass.
31. Rollback works.
32. GitHub repo contains source and docs.
33. Every future error/requirement goes into GitHub automatically or in the same apply script.

