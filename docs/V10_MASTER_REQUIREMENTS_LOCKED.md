
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
