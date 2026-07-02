# V10 MASTER SOURCE OF TRUTH â€” FROM DAY 0 TO NOW

Project: **Sagar Kerhalkar System Health Monitor Tool / Next Toppers V10**
Owner GitHub: **sagarkerhalkar**
Main stable app: `D:\SagarSystemHealthMonitor` on port `2278`
New V10 app: `D:\SagarMonitor_V10_CleanBuild` on port `2294`
Public domain used in project: `https://monitor.sagarkerhalkar.com`

This file is the permanent locked memory. Every new requirement, error, fix, test result, and delivery decision must be added here or in linked docs before code is changed.

---

## 1. Core rule after project failure loop

No more blind patches.
No UI-only replacement.
No backend-only replacement without tests.
No overwriting old working logic.
No "final" package unless every checklist passes.

Required order for every future change:

1. Backup current source.
2. Add/update requirement in docs.
3. Build DB/API/client/UI in correct order.
4. Run tests.
5. Commit/push to GitHub.
6. Create rollback point for big changes.
7. Only then proceed to next requirement.

---

## 2. What went wrong and must never repeat

During the last 14â€“15 days, many pieces were built/tested step by step. At final stages, UI packages replaced active frontend files and disconnected/overwrote working modules. This created the loop where CPU/GPU/RAM/SSD logic, machine logic, inventory, deploy, settings, notifications, and small requirements did not remain together in one full app.

The user repeatedly said:

- 2278 demo is already done. The requirement is the **new V10 customer version**.
- Last UI was around 65% acceptable visually, but backend logic was broken.
- Current UI became dirty and generic.
- Company person/photo/logo should be visible in header/top/background; this is basic branding logic.
- Every tab must have real logic, not the same generic screen.
- Database requirements must be implemented, not only docs/UI.
- The project must not restart every 3 days.
- Every small requirement from previous work must be preserved.

Permanent lesson:

> Build and preserve complete working app, not separate patches.

---

## 3. Locked final app requirement

The final V10 must be a complete web app with real backend, real DB, real client data, responsive UI, CI/CD, security tests, and GitHub history.

### 3.1 Branding / company requirement

- Company: Next Toppers branding.
- Company website should be configurable: `https://www.nexttoppers.com/`
- Company logo must show in login and app header.
- Company person/team/photo must show in login background, top banner, or hero area.
- Branding must be configurable from Settings:
  - Logo
  - Login photo/background
  - Company name
  - Company website
  - App title
- UI must look international/professional, not basic/dirty.
- Use modern SaaS dashboard style, good font, clean spacing, mobile-first responsive layout.

### 3.2 Dashboard / Command Center

Must show real overview, not dummy values:

- Correct total live clients.
- Online/offline count.
- Last heartbeat time.
- Critical/warning/healthy status.
- CPU/RAM/disk/GPU summary.
- ISP/router/network health overview.
- Upload/download/latency/jitter/loss where available.
- Notification summary.
- Inventory summary.
- Message summary.
- Deploy/update status.
- Human-readable system health: easy for 5-year-old to 90-year-old.

### 3.3 Machine Fleet

- Correct client/machine count.
- No flicker or auto-switching when user selects a machine.
- Machine identity rules:
  - hostname
  - serial/motherboard serial fallback
  - machine id
  - IP/MAC as supporting identity only
- Online/offline status must survive sudden power off/restart.
- Show last seen, uptime, OS, client version, location, assigned user/branch if known.
- Clicking a machine opens Machine 360.

### 3.4 Machine 360

Must be machine-wise and complete:

- CPU model, cores, usage, temp if real sensor exists.
- RAM total/used/free/usage percent.
- Disk/SSD/HDD/NVMe model, capacity, used/free, health where available.
- GPU name, memory, usage, temperature where real data exists.
- Network adapters, IPs, MACs, gateway, DNS, VPN status.
- USB/peripherals: keyboard, mouse, USB headset, storage, printer, camera, etc.
- Installed software/apps.
- Hardware asset mapping.
- Software license mapping.
- Warranty/invoice/vendor details.
- Human change log for that machine.
- Day history for that machine.
- Download CSV/PDF for that machine.

### 3.5 CPU/GPU/RAM/SSD client payload requirement

Client must send real data every 5â€“15 seconds where safe:

- CPU usage, model, logical/physical cores.
- RAM capacity, used/free/percent.
- SSD/HDD/NVMe names, drive letters, capacity, usage.
- GPU name, memory, usage/temp when available.
- Installed software list.
- USB/peripheral list.
- Network adapters, IPs, MAC, gateway, DNS.
- VPN detection.
- Current upload/download counters/speed.
- Latency/jitter/loss probe where possible.
- Hostname and serial fallback.

No fake values. If data is unavailable, show "Not reported" with reason.

### 3.6 Inventory / Hardware Asset Register

Must support uploaded inventory and live merge:

- Import existing H/W inventory rows.
- User had 370 uploaded H/W inventory rows in source study.
- Show all columns properly, not weird/empty generic table.
- Add/Edit/Delete H/W assets.
- Audit every edit/delete.
- Track:
  - asset tag
  - serial number
  - hostname
  - vendor
  - make/model
  - processor
  - RAM
  - disk/SSD
  - GPU if applicable
  - invoice no
  - purchase date
  - warranty end date
  - assigned person
  - branch/location
  - status
  - remarks
- Match live machine to inventory by serial, hostname, tag, MAC/IP as fallback.
- Show matched, unmatched live machine, unmatched asset.
- Export H/W inventory CSV/PDF/Excel where implemented.

### 3.7 Software Inventory / Software Register

- Live installed software from Windows and Ubuntu clients.
- Uploaded software/license data if present.
- Add/Edit/Delete software assets/licenses.
- Audit changes.
- Track:
  - software name
  - version
  - publisher/vendor
  - install date
  - license key/reference where allowed
  - license count
  - assigned machine/user
  - expiry date
  - compliance status
- Match live installed apps with approved software list.
- Export software inventory.

### 3.8 ISO Audit

Must be professional audit page:

- H/W compliance.
- S/W compliance.
- Missing serial/asset tag/warranty/invoice/vendor.
- Unmatched live machines.
- Unmatched inventory assets.
- Unauthorized or unlicensed software.
- Export separate H/W audit and S/W audit.
- Show audit score and clear next action.

### 3.9 USB + Peripherals

Old USB/peripheral logic was considered good and must not be replaced with worse UI.

Must show machine-wise:

- USB device name/type/vendor/id if available.
- Keyboard/mouse/headset/printer/camera/storage.
- First seen/last seen.
- Connected/disconnected change events.
- Human-friendly explanation.
- Collaborate with Human Change Log.

### 3.10 Human Change Log

- Machine-wise and day-wise.
- Show meaningful changes only:
  - IP changed
  - VPN on/off
  - USB connected/removed
  - software installed/uninstalled
  - hardware changes
  - disk/RAM/GPU changed
  - client online/offline
- Must not spam heartbeat samples.
- Simple language: "On Monday, this machine changed IP from X to Y".

### 3.11 Day History

- Fast and optimized.
- No heavy heartbeat sample page hang.
- Use summary/cache tables.
- Filter by machine/date.
- Download history.

### 3.12 Notifications

Notification backend rules already fixed and must be preserved:

- `cpu_ram_critical` enabled.
- `cpu_high` disabled and locked.
- `ram_high` disabled and locked.
- `disk_high` enabled for disk >= 90%.
- `gpu_temp_high` enabled for GPU temp >= 90C.
- `cpu_temp_high` enabled for real numeric CPU temp >= 90C only.
- No fake CPU/RAM single alerts.
- Notification UI must show active/inactive/locked clearly.
- User can select notification types.
- Popup/client message should show to client for configured time where client supports it.

### 3.13 Client Messages

- Admin can send messages to selected client/machine/all.
- Show sent message history.
- Show acknowledgement/receipt where available.
- UI must be professional, not ugly horizontal form.

### 3.14 Deploy / Update Center

Must not show wrong placeholder like SERVER_IP.

Must support:

- Correct install commands for Windows.
- Correct install commands for Ubuntu.
- Domain-based command using `https://monitor.sagarkerhalkar.com` where applicable.
- Local IP command where applicable.
- V10 test port 2294 command.
- Client update command.
- Server restart command.
- Rollback command.
- Copy command buttons.
- Command cards should be editable/admin configurable.

### 3.15 Settings

Must include:

- Create users.
- Roles: Viewer, Admin, Super Admin.
- Admin/Super Admin create users.
- Self password change.
- Admin password reset/change for others.
- Branding: logo, login photo/background, company website, company name.
- Retention days: incremental retention setting.
- Notification settings.
- Deploy settings.
- GitHub autosave status.

### 3.16 Roles / permissions

- Viewer: read-only, no downloads if configured, no edits.
- Admin: edit inventory, send messages, download reports.
- Super Admin: all settings, user creation, branding, retention, deploy profiles.

### 3.17 Database requirements

Final V10 DB must include at least these logical tables, even if implemented incrementally:

- machines
- latest_machine_state
- heartbeats
- heartbeat_summary_daily
- hardware_assets
- hardware_asset_audit
- software_assets
- software_asset_audit
- software_installs_live
- inventory_sync_matches
- notification_rules
- notification_state
- notifications
- client_messages
- client_message_receipts
- change_events
- iso_audit_results
- deploy_profiles
- branding_settings
- retention_settings
- users
- roles
- user_role_permissions
- settings
- app_migrations

All migrations must be idempotent and safe. No DB overwrite.

### 3.18 Optimization requirements

- UI must not load all heartbeat samples.
- Use indexed queries.
- Add indexes on machine id, hostname, serial, timestamp, date, status.
- Paginate inventory/software tables.
- Cache daily summaries.
- Avoid blocking API calls.
- Avoid frontend flicker.
- Avoid auto-switching selected machine.
- Use incremental backups, not full app copies every minute.
- Keep old-day data according to retention settings.

### 3.19 CI/CD requirements

- GitHub repo must store source and docs.
- Every change must be committed.
- CI must run basic tests.
- Static security checks.
- API route smoke tests.
- Frontend static checks.
- Inventory CRUD tests.
- Notification rule tests.
- Role/permission tests.
- Build/package test.
- Rollback script test.

### 3.20 Security requirements

- No secrets in GitHub.
- DB files ignored from GitHub.
- Logs ignored from GitHub.
- `.env` ignored.
- Passwords must be hashed where stored.
- Admin-only write APIs.
- Viewer no write/download when restricted.
- Avoid unsafe command execution from UI.
- Validate inputs for inventory/message/settings APIs.

---

## 4. Required source files/doc files to maintain

Every project must keep:

- `docs/V10_MASTER_SOURCE_OF_TRUTH_FROM_DAY_ZERO.md`
- `docs/LAST_ONE_HOUR_DISCUSSION_AND_DECISIONS.md`
- `docs/V10_DATABASE_REQUIREMENTS_LOCKED.md`
- `docs/V10_ACCEPTANCE_TEST_CHECKLIST.md`
- `docs/V10_DEVELOPMENT_RULES_NO_MORE_PATCH_LOOP.md`
- `docs/V10_ERROR_FIX_HISTORY.md`
- `docs/V10_WORK_LOG.md`
- `docs/V10_GITHUB_AUTOSAVE_RULE.md`
- `docs/START_NEW_CHAT_HANDOFF.txt`

---

## 5. Delivery roadmap locked

A real 100% working app is not one more UI patch. It is a DB-first integrated delivery:

### Phase 0 â€” Freeze and GitHub baseline

- Push current source to GitHub.
- Store this memory pack.
- Add autosave scheduled task.
- Tag baseline.

### Phase 1 â€” DB schema and migrations

- Create missing tables.
- Do not overwrite DB.
- Add indexes.
- Add migration tracking.
- Add tests.

### Phase 2 â€” Backend API bridge

- Implement APIs for Machine 360, inventory, software, notifications, messages, deploy, settings, ISO, history.
- All APIs use real data.
- No dummy counts.

### Phase 3 â€” Client payload completion

- Windows + Ubuntu metrics.
- CPU/RAM/disk/GPU/network/USB/software/VPN/speed/latency.
- Client version and update flow.

### Phase 4 â€” Frontend connected to real API

- Use the visually acceptable UI direction but preserve old working logic.
- Every tab must be unique and functional.
- Branding visible.
- Mobile/tablet/browser optimized.

### Phase 5 â€” QA, CI/CD, rollback, customer build

- Full test checklist.
- Security tests.
- Performance tests.
- Create final ZIP/installer.
- Create rollback package.

---

## 6. Acceptance rule

The app is not complete until this statement is true:

> A customer can log in, see real clients, open any machine, verify CPU/RAM/GPU/SSD/network/USB/software, edit inventory, send messages, check notifications, run deploy commands, change settings, download audit/history, and CI/security tests pass without breaking old working logic.
