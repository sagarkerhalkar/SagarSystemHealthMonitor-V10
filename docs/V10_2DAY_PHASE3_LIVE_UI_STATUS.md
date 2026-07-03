# V10 2-Day Phase 3 Live UI Status

Date: 2026-07-03

## What this phase does
- Builds the customer-facing web UI on top of live APIs.
- It does not use dummy data.
- It reads live server endpoints from port 2294:
  - `/api/v10final/status`
  - `/api/v10final/machines`
  - `/api/v10final/machine360`
  - `/api/v10final/inventory/hardware`
  - `/api/v10final/inventory/software`
  - `/api/v10final/notifications/rules`
  - `/api/v10final/deploy/profiles`
  - `/api/v10final/iso/audit`
  - existing `/api/messages`, `/api/history?samples=0`, `/api/notifications` if available.

## Locked UI requirements covered
- Command Center
- Machine Fleet
- Machine 360
- Network + VPN
- Hardware Intelligence
- Software Intelligence
- H/W Inventory Register
- S/W Inventory Register
- ISO Audit
- USB + Peripherals
- Human Change Log
- Day History
- Client Messages
- Notifications
- Deploy Center
- Settings
- Next Toppers logo/person/photo/header/hero

## Important truth
If client does not report disk, GPU, USB or network data, UI shows `Not reported` and does not fake values.
