# V10 Current Progress Locked Before ISO — 2026-07-03

## Do not move to ISO until these pages are accepted

- Home / Command Center
- Machine Fleet
- Machine 360
- Network + VPN
- Hardware Intelligence
- Software Intelligence
- Notifications
- Settings

## Accepted / passed work

### 2278 source
- 2278 is working.
- V10 must not modify 2278.
- V10 reads `D:\SagarSystemHealthMonitor\data\monitor.db` using SQLite read-only mode.

### 2278 hardware API
- 64 machines found.
- Fresh/stale counts available.
- CPU/RAM/disk/GPU/USB/network arrays are available from `latest.summary_json`.
- Missing serial is a client-payload limitation; do not call data fake.
- Asset fingerprint such as `hostname / MAC-like fingerprint` must be shown separately from official serial number.

### 2278 software API
- Software source works.
- 58,353 software rows extracted.
- Machine-wise software list is available.

### ISP/WAN
- Admin/Super Admin can add 1 to 10 ISP/WAN links in settings.
- ISP/WAN data must not come from client machine.
- Manual router/ISP details first; backend monitors automatically after save.

### Notifications
- Notification read-only simulation previously passed with real 2278 rules and machines.
- Latest test timed out, so endpoint must be optimized and made non-blocking.

## Rejected / not accepted yet

- Home page still too long.
- Hostname/identity display still unclear.
- Machine 360 lacks clean software section.
- Network + VPN is not selected-machine focused.
- Hardware Intelligence is not selected-machine focused.
- Software Intelligence is not selected-machine focused.
- UI still not global/corporate enough.
- Duplicate old/new sections still create confusion.

## Next build name
`V10_SELECTED_MACHINE_UI_ACCEPTANCE_AND_NOTIFICATION_TIMEOUT_FIX`
