# V10 ACCEPTANCE TEST CHECKLIST

Do not call any build final until every item is checked.

## Login and roles

- [ ] Login works.
- [ ] Viewer role cannot edit.
- [ ] Admin can edit allowed items.
- [ ] Super Admin can manage users/settings.
- [ ] Password change works.
- [ ] Admin reset password works.

## Branding

- [ ] Next Toppers logo visible.
- [ ] Company person/photo visible in login/header/background.
- [ ] Company website stored and clickable/configurable.
- [ ] Branding settings save and persist.

## Dashboard

- [ ] Correct machine count.
- [ ] Correct online/offline count.
- [ ] No dummy counts.
- [ ] Last heartbeat visible.
- [ ] Health summary real.

## Machine 360

- [ ] CPU real data shown.
- [ ] RAM total/used/percent shown.
- [ ] SSD/HDD/NVMe capacity/usage shown.
- [ ] GPU shown if client reports; otherwise "Not reported".
- [ ] Network adapters/IP/MAC shown.
- [ ] VPN status shown.
- [ ] USB/peripherals shown.
- [ ] Installed software shown.
- [ ] Inventory match shown.
- [ ] Day history shown.
- [ ] Download works where enabled.

## Inventory

- [ ] 370 H/W rows loaded correctly.
- [ ] H/W Add works.
- [ ] H/W Edit works.
- [ ] H/W Delete works.
- [ ] H/W audit log created.
- [ ] S/W Add works.
- [ ] S/W Edit works.
- [ ] S/W Delete works.
- [ ] S/W audit log created.
- [ ] Live/inventory matching works.

## Notifications

- [ ] cpu_ram_critical active.
- [ ] cpu_high disabled and locked.
- [ ] ram_high disabled and locked.
- [ ] disk_high active.
- [ ] gpu_temp_high active.
- [ ] cpu_temp_high only real numeric temp.
- [ ] No fake single CPU/RAM alerts.
- [ ] UI shows active/off/locked.

## Messages

- [ ] Send message to selected client.
- [ ] Send message to all.
- [ ] Message history visible.
- [ ] Receipt visible when supported.

## Deploy

- [ ] Windows install command correct.
- [ ] Ubuntu install command correct.
- [ ] Domain command correct.
- [ ] Local IP/test port command correct.
- [ ] Update command correct.
- [ ] Rollback command correct.
- [ ] Copy buttons work.

## History/change log

- [ ] Human change log shows meaningful changes only.
- [ ] Day history fast.
- [ ] No heavy heartbeat hang.
- [ ] Machine/date filters work.

## CI/security

- [ ] GitHub CI runs.
- [ ] Python syntax test passes.
- [ ] API smoke test passes.
- [ ] Frontend static test passes.
- [ ] DB migration test passes.
- [ ] Inventory CRUD test passes.
- [ ] Notification rule test passes.
- [ ] Security static test passes.

## Delivery

- [ ] Backup created.
- [ ] Rollback command created.
- [ ] Git commit pushed.
- [ ] Version tag created.
- [ ] Customer demo checklist exported.
