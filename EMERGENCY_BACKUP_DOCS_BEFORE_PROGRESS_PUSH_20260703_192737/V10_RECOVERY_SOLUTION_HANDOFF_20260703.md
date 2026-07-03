# V10 Recovery Solution and Handoff Plan

Date: 2026-07-03

## Immediate decision
Stop UI patch loop. Recover 2278 first. Then rebuild V10 using acceptance-driven delivery.

## Phase 0: Protect and recover main 2278
- Backup `D:\SagarSystemHealthMonitor` and its DB.
- Restore login if broken.
- Confirm `/api/health`.
- Confirm live clients are sending data.
- Confirm domain/tunnel only after local app works.

## Phase 1: V10 baseline freeze
- Backup current V10.
- Tag GitHub baseline.
- Do not overwrite old working modules.
- Compare against backups before replacing any file.

## Phase 2: DB/API foundation
Complete and test:
- machines/latest/heartbeats
- hardware_assets
- software_assets
- edit audit logs
- inventory sync
- notifications
- messages
- deploy profiles
- users/roles
- branding
- retention
- history cache
- ISO evidence tables/reports

## Phase 3: Live data collection
Fix client payload and mapping for:
- today download/upload totals
- current download/upload Mbps
- CPU/RAM
- SSD/HDD/NVMe
- GPU if real
- USB/peripherals
- software list
- network/VPN
- public route and ISP probe

## Phase 4: UI only after API acceptance
Use live data only. No dummy data. No global machine selector. Logo only on internal pages. Login photo only as background. Settings must allow upload/name/roles/password/retention.

## Phase 5: Final acceptance
Final ZIP only after all tests pass:
- 2278 healthy
- V10 health
- DB migration
- live data
- inventory CRUD
- notification controls
- settings users/password/branding
- deploy commands
- reports/exports
- GitHub push check
- rollback

## Home page locked KPI requirement
Home page must include:
- Today Download
- Today Upload
- Current Download
- Current Upload
- Total/online/issue clients
- Hardware and software asset counts
- Organization-wide asset usage details
- Alert summary
- Router/ISP/WAN details where router feed is available
- Cloudflare/server active route probe

## Statement for next developer
Do not trust chat memory. Trust GitHub docs, source, DB schema, and passing tests.
