# V10 DATABASE REQUIREMENTS LOCKED

The previous active DB was not enough. It had only a small subset like latest, heartbeats, notifications, notification_rules, notification_state, client_messages, receipts, change_events, settings, users.

The final DB must support the full web app.

## Required database principles

- SQLite allowed for current V10, but schema must be production-style.
- Migrations must be safe and idempotent.
- No dropping tables.
- No overwriting DB.
- DB backup before migration.
- Use indexes.
- Use audit logs for manual edits.
- Use summary/cache tables for fast UI.

## Required tables

### machines
Stores stable machine identity.

Fields expected:
- id
- machine_id
- hostname
- serial_number
- motherboard_serial
- os_name
- os_version
- client_version
- first_seen
- last_seen
- status
- assigned_user
- location
- branch
- notes

### latest_machine_state
One latest row per machine for fast dashboard.

Fields expected:
- machine_id
- hostname
- payload_json
- cpu_percent
- ram_percent
- disk_percent_max
- gpu_percent
- gpu_temp
- online_status
- network_status
- updated_at

### heartbeats
Raw client reports with retention.

Fields expected:
- id
- machine_id
- hostname
- ts
- payload_json
- cpu_json
- ram_json
- disk_json
- gpu_json
- network_json
- usb_json
- software_json

### heartbeat_summary_daily
Fast daily history.

### hardware_assets
Manual/uploaded H/W inventory.

### hardware_asset_audit
Every add/edit/delete of H/W asset.

### software_assets
Manual/uploaded S/W licenses/assets.

### software_asset_audit
Every add/edit/delete of S/W asset.

### software_installs_live
Installed software detected from clients.

### inventory_sync_matches
Machine-to-asset and software matching result.

### notification_rules
Rules with active/inactive/locked state.

### notifications
Generated notification events.

### notification_state
Dedup/suppression state.

### client_messages
Sent messages.

### client_message_receipts
Client acknowledgement.

### change_events
Human-readable meaningful changes.

### iso_audit_results
Audit snapshots.

### deploy_profiles
Install/update/rollback command profiles.

### branding_settings
Company logo, login photo, website, colors.

### retention_settings
Days to keep raw/summaries/logs.

### users / roles / user_role_permissions
RBAC.

### app_migrations
Migration history.

## Required indexes

- machine_id + timestamp.
- hostname.
- serial_number.
- asset tag.
- notification rule/type/state.
- date summary.
- software name + machine.

## Required DB acceptance

A test must prove:

- Tables exist.
- Migrations are idempotent.
- Existing data remains.
- 370 H/W inventory rows still accessible.
- Notification locked rules still correct.
- CRUD for H/W and S/W writes audit rows.
- Dashboard queries are fast.
