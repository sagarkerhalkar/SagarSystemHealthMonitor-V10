
# V10 Phase3 Fix4 Full Tab-Wise Requirements Locked

Date: 2026-07-03

This file stores the user's expanded UI and live-data requirements. These requirements must be implemented and tested with live server data.

## Home / Command Center
- Show logo, not team photo, in header/sidebar.
- Organization name defaults to Sagar and is editable per organization request.
- Machine-wise animated 3D live summary cards.
- Total client count, online count, issue client count.
- Issue client count must be clickable and take user to issue machines in Machine Fleet.
- Show hardware asset count and software asset count.
- Alert summary from live notification tables.
- Show live ISP/internet details: upload, download, latency, jitter, packet loss, public IP and all ISP/router details available from live server/client/cloudflare/router payload.

## Machine Fleet
- Correct live client count.
- Online/offline, last seen, IP, OS, CPU/RAM.
- Page-wise table, no endless scroll.
- Clicking a machine opens Machine 360.
- Search option.
- Filters: all, online, offline, issue machines.
- CSV download.
- Good font and light animation.

## Machine 360
- Full selected-machine story: CPU, RAM, SSD/HDD/NVMe, GPU, USB, network, software and inventory sync.
- Show capacity, usage, temperature and details where available.
- No fake values; show Not reported if client does not send real data.
- Machine-wise CSV download.

## Network + VPN
- Machine-wise IP, MAC, adapters, gateway, DNS, VPN, ISP, latency, jitter, packet loss, upload/download and public IP.
- CSV download machine-wise.

## Software Intelligence
- Machine-wise live installed software list.
- Sync/fallback with Software Asset Register.
- Search and CSV download.

## Hardware Asset Register
- H/W inventory with search, Add/Edit/Delete, export, live machine sync.
- CSV import capability.
- Sample H/W CSV download.

## Software Asset Register
- S/W register/license/live fallback with no fake rows.
- Search, Add/Edit/Delete, export, sync with live machine software.
- CSV import capability.
- Sample S/W CSV download.

## ISO Audit Center
- International-level audit style acceptable for ISO organization review.
- Show missing serial, vendor, invoice, warranty and unmatched assets/machines.
- Download option.

## USB + Peripherals
- Machine-wise keyboard, mouse, headset, USB storage and peripheral changes.
- Explain in simple way so any person can understand.
- Do not mix all machines in one shot.
- CSV download.

## Human Change Log
- Track only meaningful IP/USB/VPN/software/hardware changes.
- Current date focused.
- All-machine and selected-machine view/download.

## Day History
- Fast summary, no heavy heartbeat loading by default.
- Settings controls how many DB days to retain.
- Backend must automatically use retention setting.
- Download day-wise summary and changes CSV.
- Support selected date and selected machine or all machines.

## Client Messages
- Send message to selected machine or all machines.
- Sent history visible with date.
- Message retention follows DB retention setting.

## Notifications
- Show active/off/locked rules and alert history.
- Admin can edit normal notification rules.
- Super admin can manage locked rules; super admin is for Sagar only.

## Deploy Center
- Real Windows and Ubuntu install/update commands.
- No wrong SERVER_IP placeholder.
- Commands editable.
- Test command column.
- Troubleshooting column.
- Message column.

## Settings
- Organization name, logo path, login background photo, website, retention.
- User creation roles: viewer, asset entry user, organization admin, super admin.
- Super admin always for Sagar only.
- Self password reset and admin password reset required.
- Database must be incremental and retention-managed, not one uncontrolled huge DB.

## Footer
Every page must show a small corporate footer:
Created by Sagar Kerhalkar · 8105977226 · sagarkerhalkar.com
