# Sagar System Health Monitor V10 - LOCKED REQUIREMENTS

## Non-negotiable rule
No UI-only patch. No backend-only patch without tests. No replacing old working logic without backup and rollback.

## Required final app
- CPU, RAM, SSD/HDD/NVMe, GPU, USB/peripherals, network, VPN.
- Correct live client count and machine-wise data.
- Machine 360 with full human-readable machine story.
- Hardware inventory Add/Edit/Delete.
- Software inventory Add/Edit/Delete.
- Inventory sync with live machine by serial/hostname/tag/IP.
- Notifications active/off/locked.
- Client messages with sent history and receipts.
- Deploy command center with correct install/update commands.
- Settings: users, roles, branding, logo, company website, login photo, retention days.
- Next Toppers logo/person/company branding visible in login/header/background.
- Database schema for machines, heartbeats, inventory, software, users, roles, branding, retention, notifications, messages, deploy, ISO audit, history cache.
- Optimization: no heavy heartbeat samples in UI, pagination, indexes, cache, retention jobs.
- CI/CD, security, responsive tests, rollback.
- Public repo must not contain private DB, machine IP data, tokens, .env, logs, or customer secrets.

## Required delivery order
1. Database schema and migrations.
2. Backend APIs.
3. Real client payload completeness.
4. Frontend connected to real APIs.
5. CI/CD + security + performance tests.
6. Rollback package.
7. Final customer ZIP.
