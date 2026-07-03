# V10 2-Day Phase 1 - DB + API Bridge

Date: 2026-07-03

## Why this phase exists
The last failure happened because UI was changed before the database and backend were complete. This phase reverses that mistake.

## What this package does
- Does not touch main 2278.
- Backs up current V10 source.
- Adds `v10_final_bridge.py`.
- Hooks it into `V10_IDENTITY_CORE_2294.py` and `server.py`.
- Creates missing DB tables safely without deleting old data.
- Imports existing hardware inventory into DB when the DB table is empty.
- Adds API endpoints under `/api/v10final/*`.
- Adds tests.
- Commits/pushes to GitHub if local git remote is available.

## DB tables added
- hardware_assets
- software_assets
- asset_edit_audit_log
- software_edit_audit_log
- inventory_sync_matches
- branding_settings
- retention_settings
- deploy_profiles
- history_summary_cache
- iso_audit_results
- roles
- user_role_permissions

## API endpoints added
- GET /api/v10final/status
- GET /api/v10final/db/status
- GET /api/v10final/machines
- GET /api/v10final/machine360?id=<machine_id>
- GET /api/v10final/inventory/hardware
- POST /api/v10final/inventory/hardware/save
- DELETE /api/v10final/inventory/hardware?id=<asset_uid>
- GET /api/v10final/inventory/software
- POST /api/v10final/inventory/software/save
- DELETE /api/v10final/inventory/software?id=<software_uid>
- GET /api/v10final/notifications/rules
- GET /api/v10final/branding
- POST /api/v10final/branding
- GET /api/v10final/retention
- POST /api/v10final/retention
- GET /api/v10final/deploy/profiles
- GET /api/v10final/iso/audit
- GET /api/v10final/inventory/sync
- POST /api/v10final/inventory/sync
- GET /api/v10final/export/hardware.csv
- GET /api/v10final/export/software.csv

## Acceptance for this phase
- Server starts and prints `V10_2DAY_PHASE1_DB_API_BRIDGE_LOADED`.
- `/api/v10final/status` returns ok true.
- DB tables exist.
- H/W inventory table contains source rows where available.
- Add/Edit/Delete test hardware asset works.
- Add/Edit/Delete software asset works.
- Machine count comes from real `latest` data.
- Notification rules are readable and preserved.
