# V10 UI/UX Requirements Locked — Next Toppers System Health Monitor

## Scope lock
- Work only on V10 path `D:\SagarMonitor_V10_CleanBuild` and port `2294`.
- Do not touch live/main `D:\SagarSystemHealthMonitor` / port `2278`.
- Notification backend logic is already locked and must not be disturbed.

## Brand
- Company name: **Next Toppers**.
- Website: `https://www.nexttoppers.com/`.
- Use company logo instead of “Profile Website”.
- Home/login page must support company logo and company photo.
- Settings must later allow Super Admin/Admin to change company logo, website, login image and profile photo.

## UI/UX direction
- International-level, classic, innovative SaaS dashboard.
- Not oversized, not childish, not local-looking.
- Clean font, strong hierarchy, subtle 3D/glass depth, animated but not heavy.
- Must be understandable for any user from age 5 to 90.
- Optimized for all major browsers, Apple Safari, mobile, laptop, tablet and iPad.
- Must not hang, must not flicker, must not jump selected machine.

## Command Center
- App-wide command overview with 3D animated summary cards.
- H/W and S/W inventory overview.
- Connected ISP/router/network health: upload, download, latency, jitter, loss via Cloudflare/server probe.
- Backend notification attention summary only.
- Good high-level explanation of fleet state.

## Machine Fleet
- Fleet page is okay, but clicking a machine must open Machine 360.

## Machine 360
- Machine-wise full understandable view.
- Hardware and software summary.
- CPU, GPU, RAM, HDD/SSD/NVMe, disks, network, VPN, USB/peripherals.
- All sections visually clear with icons/cards/charts.
- CSV and PDF download options.

## Network + VPN
- Machine-wise, not all machines dumped together.
- Show all IP addresses, MAC addresses, VPN details, adapter details.
- Public IP is not required now.

## Hardware Intelligence
- Machine-wise hardware details synced with H/W inventory.
- Must include vendor name, warranty end date, invoice number, serial number, model, make, assigned to, location, status and remarks.
- Hardware page should not look like a local table; use international asset-intelligence naming.

## Software Intelligence
- Machine-wise software details synced with S/W inventory.
- Clean international naming and filtering.
- Download individual machine software details if required.

## Inventory
- H/W Inventory and S/W Inventory should be professional asset intelligence pages.
- Add/edit inventory permission through role management.
- Sync inventory with live machine serial number/software data.

## ISO Audit
- Must look like ISO-standard audit, not a simple local page.
- Download single H/W or S/W details separately when required.

## USB + Peripherals / Human Change Log
- USB page should be understandable to 5–90 year old users.
- Human Change Log should collaborate with USB/peripheral changes.
- Machine-wise and day-wise filters.
- Show Monday/day changes clearly.
- Important changes: USB/peripheral, VPN and IP changes.

## Day History
- Remove/avoid heavy Heartbeat Samples from UI.
- Keep useful day summary and fast loading.
- Must not hang.

## Client Messages
- Existing flow is good.
- Add sent-message history so admin can see what was sent.

## Notifications
- Rules are correct.
- Show which notifications are active.
- CPU single and RAM single rules are locked disabled.
- Attention card must use backend notification rows only.

## Settings and Roles
- User roles:
  - Viewer: read-only live view, no download/edit.
  - Admin: create users, inventory add/edit, download/export, manage notifications, branding settings.
  - Super Admin: all admin rights plus can create admin users, change logo, website, login photo, reset self/other passwords.
- Admin and Super Admin can create users.
- Self password change and other user password reset required.
- Branding settings required: company name, company logo, website URL, login photo/profile photo.

## Deploy
- Deploy page must use same design system and clear settings.

## Quality gates
- Responsive test required.
- Browser test required.
- CI/CD test required.
- Security test required.
- No fake hardware values.
- No old heavy heartbeat samples on Day History.
- Main 2278 must not be touched.
