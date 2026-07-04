
## 20260703_174048 - Requirement stored
Home page must show Today Download, Today Upload, Current Download, Current Upload from live client traffic. No dummy values.

## 20260703_175628 - Requirement stored
V10 must read 2278 live data in read-only mode first, then test notifications, then proceed to Hardware tab. Do not modify 2278.

## 20260703_180848 - Hardware tab locked implementation path
Hardware tab must read live hardware details from 2278 read-only source first: CPU, RAM, disk, GPU, USB, network, software count, serial/BIOS/motherboard serial when reported. Missing fields must show Not reported by client, not fake values. CSV download required. Notification test must remain working.


## 20260703_181756 - Software Intelligence locked implementation path
Software Intelligence must read installed software from 2278 read-only source first, machine-wise. It must show full installed list when client reports it, otherwise show count-only / Not reported by client. No fake software rows. CSV export and sample software CSV required.


## 20260703_185203 - No-start-from-zero UI binding rule
- Do not rebuild client/server logic. Use 2278 read-only latest.summary_json as source of truth. Home must show 64/latest source counts, fresh/stale split, traffic KPIs from 2278, notification simulation, machine 360 hardware/software details. Old V10 single-client cards must not be visible on bound pages.


---

# 2026-07-03 Progress/Error/Solution Checkpoint

The full conversation/progress/error/solution report was added to docs:
- V10_20260703_FULL_CONVERSATION_PROGRESS_ERROR_LOG.md
- V10_20260703_NO_MORE_PATCH_LOOP_SOLUTION.md
- V10_20260703_ACCEPTANCE_LOCK_CURRENT_STATUS.md
- V10_20260703_HANDOFF_FOR_NEXT_DEVELOPER.md

Key decision: do not touch 2278. V10 reads 2278 read-only only. Do not move to ISO until Home, Machine Fleet, Machine 360, Network + VPN, Hardware Intelligence and Software Intelligence are accepted.

## 2026-07-03 19:33:18 â€” Requirement lock from video
- Do not proceed to ISO until Home, Machine Fleet, Machine 360, Network + VPN, Hardware Intelligence, Software Intelligence are accepted.
- Machine-wise tabs must be selected-machine views, not fleet views.
- 2278 remains read-only source of truth.
- No old/new duplicate UI sections.

## 2026-07-03 19:33:33 â€” Requirement lock from video
- Do not proceed to ISO until Home, Machine Fleet, Machine 360, Network + VPN, Hardware Intelligence, Software Intelligence are accepted.
- Machine-wise tabs must be selected-machine views, not fleet views.
- 2278 remains read-only source of truth.
- No old/new duplicate UI sections.

## 2026-07-03 19:38:51 - Video error next solution locked

- Video shows core issue is not backend source, but mixed/duplicated UI binding.
- 2278 read-only source remains source of truth.
- Do not touch 2278 or client.
- Next build locked: V10_SELECTED_MACHINE_UI_ACCEPTANCE_AND_NOTIFICATION_TIMEOUT_FIX.
- Do not move to ISO until Home, Machine 360, Network + VPN, Hardware Intelligence and Software Intelligence are clean and selected-machine focused.
- Notification-test timeout must be bounded/cached/non-blocking.

## 2026-07-03T20:11:27 - Selected-machine rule locked
Every machine detail page must use machine_id. If machine_id is selected, hardware/software/network must return the same machine_id. Server health must be separate from client machine data. Do not move to ISO until this passes.


## 2026-07-03 End-of-Day Handoff
- User stopped coding for today and requested all conversation, GitHub findings, errors, and next solution be stored in GitHub.
- Root cause locked: V10 browser runtime is loading multiple old patch scripts together. Old renderer and selected-machine renderer fight each other.
- 2278 is working and must not be touched.
- Tomorrow must start with V10_CLEAN_RUNTIME_2278_SELECTED_MACHINE_APP, not ISO and not another overlay patch.
- New handoff docs:
  - docs/V10_20260703_END_OF_DAY_FINAL_HANDOFF_TOMORROW.md
  - docs/V10_20260703_GITHUB_SOURCE_FINDINGS_AND_ROOT_CAUSE.md

## 2026-07-04T14:41:20 - Clean runtime auth gate fix
- Test showed index uses only clean runtime.
- /api/v10/app/health returned login_required because original auth gate protected all /api/* paths.
- Whitelisted GET /api/v10/app/* for clean runtime read-only dashboard/test access.
- No 2278/client/data collection logic changed.
