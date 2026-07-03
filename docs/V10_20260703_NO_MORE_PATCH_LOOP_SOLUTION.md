# V10 Final Solution Plan — No More Patch Loop

## Goal
Deliver V10 as a stable enterprise acceptance build without repeatedly breaking working logic.

## Non-Negotiable Rules
1. Do not touch 2278.
2. V10 reads 2278 in SQLite read-only mode only.
3. Do not rebuild client logic unless a separate client acceptance plan is approved.
4. Do not add duplicate UI sections.
5. Replace old UI with verified live-source UI only after API tests pass.
6. Do not move to ISO until core live pages are clean.
7. Commit/push every checkpoint to GitHub.

## Current Good Foundation
- 2278 DB source works.
- 64 machines are available.
- Hardware arrays are available from 2278 payload.
- Software rows are available from 2278 payload.
- ISP/WAN DB/API exists.
- Machine Fleet is mostly acceptable.
- Machine 360 is about 80% but needs software and clean machine-wise binding.

## Immediate Fix Needed
The latest failure is not a full failure. It is:
`/api/v10/source2278/notification-test` timeout.

Make it fast by:
- no heavy heartbeat scan;
- only latest + rules;
- machine limit/caching;
- short timeout handling;
- return warning if partial instead of hanging.

## UI Solution
### Home
Make Home compact with sections:
1. Organization header with original logo.
2. KPI tiles: total, fresh, stale, issue, H/W, S/W, alerts.
3. Traffic tiles: Today Download, Today Upload, Current Download, Current Upload.
4. Compact 3D machine live cards with only fresh/issues and pagination.
5. Organization asset usage summary condensed.
6. ISP/WAN status from Settings/Probe.

### Machine 360
One selected machine only:
- Hostname
- Asset fingerprint / identity
- Official serial
- OS/IP
- CPU/RAM
- Disk/NVMe
- GPU
- USB/peripherals
- Network adapters
- Installed software mini-list + link/export

### Network + VPN
One selected machine only:
- adapters
- MAC/IP
- gateway/DNS if reported
- VPN status
- public IP/ISP route from payload
- router/WAN status from Settings

### Hardware Intelligence
One selected machine only:
- CPU, RAM, disk, GPU, USB, network detailed cards/tables

### Software Intelligence
One selected machine only:
- installed software searchable table for selected machine
- CSV export
- sync status with Software Asset Register

## ISO Solution
ISO starts only after page acceptance. ISO must be evidence-based:
- Pass only when evidence exists.
- Gap when serial/vendor/invoice/PO/warranty/assignment/location missing.
- Manual evidence entry allowed.
- Automatic checking after entry.

## Acceptance Gate
A page is not complete until:
- data comes from 2278 read-only or V10 register API;
- no duplicate old UI;
- selected-machine pages are not fleet pages;
- CSV works;
- empty fields show `Not reported by client`, not fake values;
- test passes;
- GitHub pushed.