# V10 Final Studied Source Audit - Customer Recovery Delivery

This package is based on the uploaded source study ZIP `V10_FULL_SOURCE_STUDY_20260702_200635.zip`.

## What was actually found in the source

1. The old working frontend logic was present in:
   - `backups\UI_BEFORE_BIG_CHANGE_20260702_150145\app.js`
   - `backups\UI_BEFORE_BIG_CHANGE_20260702_150145\index.html`

2. That old frontend contains the modules the user was referring to:
   - Machine 360 logic
   - USB + Peripherals logic
   - Deploy command cards
   - Client Messages logic
   - Hardware inventory Add/Edit/Delete
   - Software inventory Add/Edit/Delete
   - ISO Audit views and exports
   - Day History / CSV export hooks
   - Notification rules page hooks

3. The later customer UI had better look but replaced the old working module logic with a smaller display-only frontend. That caused tabs to look similar and removed expected behavior.

4. The backend already has hooks for missing modules:
   - `INVENTORY_30MIN_HOOK_START`
   - `NATIVE_HW_SW_ISO_INVENTORY_HOOK_START`
   - `HISTORY_CACHE_LITE_HOOK_START`

   But the key file `inventory_30min.py` was not present in the collected source. The old app expected `/api/inv30/*` endpoints, so inventory Add/Edit pages could not fully work without this module.

5. This recovery package restores `inventory_30min.py` and restores the old frontend logic while keeping the current V10 DB and notification database data untouched.

## Requirement coverage in this package

- CPU/RAM/SSD/GPU live view: restored from old Machine 360 frontend and current `/api/overview` backend.
- USB + Peripherals: restored from old working UI logic; not redesigned away.
- Client count: taken from backend overview, not fake frontend count.
- Inventory: Add/Edit/Delete restored through `/api/inv30/hw/*` and `/api/inv30/sw/*`.
- Uploaded H/W inventory: loads from `fresh_hw_inventory_v2.json`, `fresh_hw_inventory.json`, or `inventory_assets.json` and creates editable store `hw_inventory_editable.json`.
- Uploaded S/W inventory: loads from `software_asset_register_2294.json` or `fresh_sw_inventory.json` and creates editable store `software_license_editable.json`.
- Inventory live sync: matches uploaded inventory with live machines by serial, tag/hostname, asset code/name.
- Notifications: keeps the already-fixed backend DB rules and locked CPU/RAM single rules.
- Deploy page: restored from old working deploy command card logic.
- Client Messages: restored old working message compose and sent history UI.
- Optimization: does not copy the main 2278 DB, does not touch V10 DB, uses JSON inventory store, includes static and runtime tests.
- CI/CD: includes PowerShell smoke tests and a GitHub Actions workflow skeleton under `.github/workflows`.
- Security: includes a static security check for obvious non-local `http://`, `eval`, and insecure script patterns.

## Important safety boundary

This package touches only:

- `D:\SagarMonitor_V10_CleanBuild\public\index.html`
- `D:\SagarMonitor_V10_CleanBuild\public\app.js`
- `D:\SagarMonitor_V10_CleanBuild\public\styles.css`
- `D:\SagarMonitor_V10_CleanBuild\public\style.css`
- `D:\SagarMonitor_V10_CleanBuild\inventory_30min.py`
- `D:\SagarMonitor_V10_CleanBuild\tests\*`
- `D:\SagarMonitor_V10_CleanBuild\docs\*`

It does not touch:

- Main live 2278 folder
- Main 2278 database
- V10 monitor DB
- V10 notification DB rows
