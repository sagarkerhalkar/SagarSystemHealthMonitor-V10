# V10 Customer Delivery Locked Requirements and Roadmap

Date: 2026-07-02
Project: Sagar Kerhalkar System Health Monitor Tool - V10 / Next Toppers customer version
Target app folder: `D:\SagarMonitor_V10_CleanBuild`
Protected live app: `D:\SagarSystemHealthMonitor` on port `2278` must not be touched.
Development/test app: V10 on port `2294`.

## Why this file exists
This file is the source-of-truth memory file for the project. Do not rely only on chat memory. Every future chat must start from this file. Every code change must keep this file updated.

## Current truth
The V10 project suffered from repeated UI/source patches. Some old working frontend logic was overwritten or disconnected from backend data. The user needs one complete working web app, not more blind patches. The stable 2278 demo is already done; the requirement now is the new V10 customer version.

## Non-negotiable operating rules
1. Main 2278 must not be changed unless explicitly requested.
2. V10 2294 is the only development target.
3. No UI replacement is allowed until DB schema and API bridge pass tests.
4. No file overwrite without incremental backup and rollback command.
5. Every feature must have backend test, UI test, and real-data verification.
6. No fake hardware values. If data is unavailable, show `Not reported` with reason.
7. A build is not final until all Definition of Done checks pass.

## Locked functional requirements

### 1. Real client and machine data
- Correct live client count.
- Online/offline status with last heartbeat.
- CPU usage, CPU name, CPU cores/logical processors.
- RAM total, RAM usage, RAM used/free where available.
- SSD/HDD/NVMe storage usage, capacity, free, highest disk percent.
- GPU name, GPU memory, GPU usage/temp where real; no fake GPU values.
- USB and peripherals: keyboard, mouse, USB storage, USB headset, Bluetooth/HID when available.
- Installed software list from Windows/Ubuntu clients.
- Network: all IP addresses, MAC addresses, adapters, gateway, DNS.
- VPN status where available.
- Internet: current upload/download, daily upload/download, latency, jitter, loss, ISP/provider.

### 2. Database requirements
The final V10 database must include or migrate to equivalent tables:
- `machines` or `latest` with normalized machine identity.
- `heartbeats` with retention policy.
- `hardware_assets` for uploaded/managed H/W inventory.
- `software_assets` / `software_licenses` for uploaded/managed S/W inventory.
- `inventory_sync_matches` for live-machine-to-inventory matching by serial, hostname/tag, IP, MAC.
- `asset_edit_audit_log`.
- `software_edit_audit_log`.
- `notification_rules`, `notifications`, `notification_state`.
- `client_messages`, `client_message_receipts`.
- `change_events` for USB/IP/VPN/software/hardware changes.
- `users`, `roles` or role field, role permissions.
- `branding_settings` for company name, logo, website, login image.
- `retention_settings` for configurable data retention days.
- `deploy_profiles` for client install/update commands.
- `history_summary_cache` for fast history page.
- `iso_audit_results` or computed ISO audit view.

### 3. Inventory requirements
Hardware Asset Register must show uploaded 370 H/W rows correctly and support Add/Edit/Delete.
Required H/W columns:
- Vendor Name
- Make Name
- Model Name
- Warranty End Date / Year
- Purchase Date
- PO / Invoice / Bill No
- PO / Invoice / Bill Path
- Tag Name / Hostname
- Serial Number
- Assigned To
- Location
- Status
- Remarks
- Live Sync Status

Software Register must show uploaded S/W inventory/licensing where available and live software data from clients. If license rows are 0, it must clearly say no license register uploaded; it must not fake S/W license rows.

### 4. Page-wise UI requirements
Every tab must be a different real module, not the same generic page.

#### Command Center
- Overall app overview.
- Fleet total/online/offline/attention.
- H/W assets, S/W apps/license count.
- ISP/router/cloudflare/server probe: upload, download, latency, jitter, loss.
- Active backend alerts.
- Recent human changes.
- System-wise command analysis. Clicking a machine opens Machine 360.

#### Machine Fleet
- Clean fleet table/cards.
- Machine click -> Machine 360.
- Search/filter by hostname, IP, OS, GPU, app.

#### Machine 360
Readable for age 5 to 90. Full machine story:
- identity, hostname, serial, OS, online/offline, IP/MAC.
- CPU, RAM, disk/SSD/NVMe/HDD, GPU.
- USB/peripherals.
- software count and list.
- network/VPN.
- inventory match: vendor, warranty, invoice, assigned to, location, status.
- CSV/PDF download.

#### Network + VPN
Machine-wise network view, not all machines mixed.
- all IPs, MACs, adapters, public IP when available, gateway, DNS, VPN status.
- latency/jitter/loss, upload/download.

#### Hardware Intelligence
Machine-wise hardware details synced with H/W inventory.
- CPU/RAM/GPU/storage/USB/peripheral.
- serial/vendor/warranty/invoice/location.

#### Software Intelligence
Machine-wise software details synced with S/W inventory.
- live installed apps.
- license match/unmatch.

#### Hardware Asset Register
International name and clean UI.
- H/W Add/Edit/Delete.
- search/filter/export CSV/PDF.
- live sync status.

#### Software Register
- S/W Add/Edit/Delete.
- license/live app sync.
- search/filter/export CSV/PDF.

#### ISO Audit Center
ISO-style audit, not local table.
- missing invoice/warranty/serial/asset owner.
- unmatched live machine.
- unmatched inventory asset.
- single H/W and S/W downloads separately.

#### USB + Peripherals
Keep old good logic and make it understandable.
- device type, name, status, machine, change status.

#### Human Change Log
Machine-wise and day-wise.
- USB, IP, VPN, software/hardware change.
- Monday/day filter must show what changed that day.

#### Day History
Fast summary only. No heavy heartbeat samples. Must not hang.

#### Client Messages
Professional message composer.
- send popup/message to selected machine/all.
- sent message history visible.

#### Notifications
Current backend notification logic is correct and must be preserved:
- Disk/SSD/HDD/NVMe >= 90 => alert.
- CPU + RAM both >= 95 => alert.
- CPU-only and RAM-only single alerts locked disabled.
- CPU temp >= 90 only if real value.
- GPU temp >= 90 only if real value.
- Show active/off/locked rules clearly.

#### Deploy Center
Real deploy command center.
- Windows client install command for V10.
- Ubuntu client command where available.
- server URL/domain config.
- update existing client command.
- public/domain instructions.
- must not show wrong 2278 command when testing V10 unless labeled.

#### Settings
- Super Admin, Admin, Viewer roles.
- Super Admin/Admin can create users.
- Viewer read-only.
- self password change.
- admin/super admin can reset others.
- change company name.
- change website.
- change logo.
- change login page/company photo.
- retention days setting.

### 5. Branding/UI requirements
- Next Toppers logo and company photo on login and upper area/background where suitable.
- Company website: https://www.nexttoppers.com/
- International-level UI: classic, innovative, professional, readable.
- Fonts must be visible on all backgrounds.
- Responsive for mobile, tablet, iPad, Apple/Safari, laptop, Chrome/Edge/Firefox.
- Good animation/3D effects, but not heavy or childish.

### 6. Optimization requirements
- Pagination for big inventory/software lists.
- History cache; no heavy heartbeat sample loading.
- Indexes on machine_id, hostname, updated_at/received_at, serial, tag, app name.
- Retention cleanup reads Settings value.
- Incremental source backup only changed files.
- No full DB copy unless explicitly required.
- Avoid frontend rendering huge tables at once.

### 7. CI/CD and security requirements
- Static frontend test.
- API route test.
- DB schema migration test.
- Inventory CRUD test.
- Notification rule test.
- Role permission test.
- Browser/responsive smoke checklist.
- No insecure external HTTP links except localhost/127.0.0.1.
- No secrets in public JS.
- Rollback script.
- Backup before apply.

## Delivery roadmap

### Phase 0: Freeze and recovery baseline - 0.5 day
- Stop patching.
- Backup current V10.
- Identify best old working modules from backups.
- Create rollback point.
- Verify 2294 starts and health works.

### Phase 1: Database schema and migrations - 1 day
- Add/migrate required DB tables.
- Import 370 H/W inventory into DB.
- Keep S/W license rows honest; show 0 if no uploaded license file exists.
- Add indexes.
- Add retention setting and role permissions.
- Tests: DB schema, counts, migration rollback.

### Phase 2: Backend API bridge - 1 to 1.5 days
- `/api/overview`
- `/api/machines`
- `/api/machine360/full`
- `/api/network/machine`
- `/api/hardware/machine`
- `/api/software/machine`
- `/api/inventory/hardware` CRUD
- `/api/inventory/software` CRUD
- `/api/iso/audit`
- `/api/settings/*`
- `/api/deploy/*`
- `/api/messages/*`
- `/api/notifications/*`
- Tests: API endpoints with real DB.

### Phase 3: Client data completeness - 1 day
- Fix Windows client payload to send disk, GPU where available, USB, apps, network, MAC.
- Ubuntu parity where possible.
- Tests: one Windows real machine; verify Command Center and Machine 360.

### Phase 4: Frontend rebuild on real APIs - 2 days
- Build each tab from real API data.
- No generic placeholder tabs.
- Add responsive UI.
- Add Next Toppers branding.
- Add CSV/PDF export buttons.
- Tests: page-by-page UI checklist.

### Phase 5: QA, optimization, CI/CD, delivery - 1 day
- Performance test for inventory and history.
- Security/static tests.
- Role tests.
- Rollback test.
- Customer demo checklist.
- Final ZIP + installer.

## Realistic delivery estimate
A verified complete app requires 5 to 6 focused working days from a clean freeze. A limited demo build can be prepared sooner, but it must be clearly labeled demo and not customer-final.

## Definition of Done
The app is not done until all items below pass:
- V10 starts on 2294.
- Login works.
- Command Center uses real overview API.
- One real client appears online.
- CPU/RAM/disk/network shown correctly.
- GPU shows real data or clear Not reported.
- USB/peripherals shows old working logic.
- Uploaded H/W inventory count = 370.
- H/W Add/Edit/Delete works and audit logs.
- S/W Register shows live apps and honest license status.
- Machine 360 merges live + inventory.
- Notifications locked rules work.
- Deploy page commands are correct for V10.
- Settings roles/branding/retention/password work.
- Day History does not hang.
- CI/CD/security tests pass.
- Rollback works.
