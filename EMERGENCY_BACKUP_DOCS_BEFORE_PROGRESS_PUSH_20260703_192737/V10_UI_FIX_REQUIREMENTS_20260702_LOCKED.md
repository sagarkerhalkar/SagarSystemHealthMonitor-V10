# V10 UI Requirements Locked - 2026-07-02

This file records Sagar Kerhalkar's latest UI requirements for the V10 System Health Monitor / Next Toppers build.

## Immediate recovery
- If the browser shows a blank white/blue page after a UI patch, restore the last known working full UI files.
- Main 2278 must not be touched.
- V10 notification backend and locked CPU/RAM rules must not be disturbed.

## UI requirements to build after recovery
- Improve font readability; every label must be visible on login, dashboard, machine pages, settings, deploy, notification pages.
- Login page must use Next Toppers logo/photo, improve animation, 3D/elegant effects, and real professional SaaS look.
- UI must be optimized for mobile, tablet, iPad, Apple devices, laptop, desktop, and all major browsers.
- Use actual backend data from V10 APIs; do not show dummy-only dashboard feeling.
- Command Center must show overall app overview, H/W and S/W inventory overview, ISP upload/download/latency/jitter/loss, notification attention count, and real machine status.
- Machine Fleet can remain simple, but clicking a machine should open Machine 360.
- Machine 360 must be understandable from age 5 to 90 and show H/W, S/W, CPU, GPU, RAM, HDD/SSD/NVMe, USB/peripherals, network, VPN, inventory sync and CSV/PDF export.
- Network + VPN must be machine-wise, not all machines mixed; show all IPs, MAC address, local/public IP where available, VPN status, adapter details. Public IP is not mandatory if unavailable.
- Hardware page must sync with Hardware Asset Register and show machine-wise H/W details plus vendor name, warranty end date, invoice number, purchase info where serial number matches.
- Software page must sync with Software Asset Register and show machine-wise software details and licensing/audit context.
- H/W Inventory and S/W Inventory names must be international/professional, clean, searchable, filterable, exportable.
- ISO Audit must look like an ISO-standard audit center and support downloading H/W and S/W details separately or together.
- USB + Peripherals should stay but be simplified and human-readable.
- Human Change Log must collaborate with USB/peripherals and show machine-wise/day-wise changes, especially IP changes.
- Day History should not show heavy Heartbeat Samples and must load fast, not hang.
- Client Messages should show what was sent before, not only send new message.
- Notifications page is good; only add active/inactive/locked notification visibility clearly.
- Deploy page must be redesigned and updated with real deployment settings and commands.
- Settings page must include keep-data-days option, user roles, company logo/name/website/login photo change, password change for self and admin/super-admin-managed password changes.
- Roles: viewer, inventory add/edit user, admin, super admin. Admin and super admin can create users; super admin has full branding/user/password settings.
- CI/CD tests, responsive tests, browser tests, and security static tests must be available.

## Safety
- V10 only: D:\SagarMonitor_V10_CleanBuild.
- Main 2278 live server must not be modified.
- Do not use Google Drive/OneDrive/sync drive for SQLite DB operations.
