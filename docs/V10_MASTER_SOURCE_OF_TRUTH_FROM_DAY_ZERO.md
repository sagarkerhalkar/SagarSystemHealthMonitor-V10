# V10 MASTER SOURCE OF TRUTH FROM DAY ZERO

This file is the permanent memory for Sagar Kerhalkar System Health Monitor Tool V10.

## Non-negotiable delivery rule
No random UI patch. No backend-only patch. No replacing old working logic without backup, rollback, tests, and Git commit.

## Required complete web app
- New V10 customer version, not old 2278 demo.
- International UI/UX with Next Toppers branding.
- Company logo and company/person photo visible in login/header/background where appropriate.
- Fully responsive for mobile, laptop, iPad/tablet, browser, Apple devices.

## Live machine requirements
- Correct live client count.
- Machine-wise CPU, RAM total/used, SSD/HDD/NVMe usage, GPU name/memory/temp/usage where real.
- Hostname, serial, IP, MAC, network adapters, ISP/router details, VPN status.
- USB and peripherals: keyboard, mouse, headset, storage, printer, other connected devices.
- Software installed list for Windows and Ubuntu.
- Latency, jitter, packet loss, current upload/download, day upload/download where real.

## Database requirements
Must include schema/tables for machines, heartbeats, hardware inventory, software inventory/licenses, inventory edit audit, software edit audit, users, roles, permissions, branding settings, retention settings, notifications, notification rules/state, client messages/receipts/history, deploy profiles, ISO audit, inventory sync matches, human change log, day history cache.

## Inventory requirements
- Uploaded H/W inventory must be stored and displayed correctly.
- H/W inventory Add/Edit/Delete must work.
- S/W inventory Add/Edit/Delete must work.
- Live machine data must sync with inventory by serial, hostname, asset tag, IP, MAC fallback.
- ISO audit must show missing fields, unmatched live machines, unmatched assets, export H/W and S/W separately.

## Notification requirements
- cpu_ram_critical enabled.
- cpu_high and ram_high disabled and locked.
- disk_high enabled at >=90%.
- gpu_temp_high enabled at >=90C.
- cpu_temp_high enabled only when real numeric CPU temp exists.
- UI must show active/off/locked clearly.

## UI pages required
Command Center, Machine Fleet, Machine 360, Network+VPN, Hardware Intelligence, Software Intelligence, Asset Register, Software Register, USB+Peripherals, Human Change Log, Day History, Client Messages, Notifications, Deploy Center, Settings, ISO Audit.

## Settings requirements
Users, roles: Viewer/Admin/Super Admin; user creation; password change/reset; branding logo; company website; login photo; retention days.

## Optimization requirements
No heavy heartbeat samples on UI, pagination, indexes, cached summaries, fast day history, no DB full copy, incremental source backup only.

## CI/CD and security requirements
GitHub repo must always be updated. Add tests for DB migration, API routes, inventory CRUD, notifications, role permissions, UI static checks, security static checks, rollback.

## Last discussion locked decision
The user rejected more patch loop. Every change must update GitHub automatically and must preserve source-of-truth docs.
