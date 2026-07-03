# Live Server Incident: 2278 and V10

Date: 2026-07-03

## Incident summary
During the V10 work, the user reported that the main 2278 server login was not working and data collection was not working.

## Protected system
- Main live/demo app: `D:\SagarSystemHealthMonitor`
- Port: `2278`
- This system was supposed to remain untouched unless explicitly approved.

## Required immediate action
Stop all V10 patching. Do not apply new V10 UI packages. First recover 2278.

## Recovery checklist for 2278
1. Check whether port 2278 is listening.
2. Check whether the server process is running from `D:\SagarSystemHealthMonitor`.
3. Check `/api/health` locally.
4. Backup DB before any login repair.
5. Verify admin login.
6. Verify latest client data in DB.
7. Verify clients are still posting to 2278.
8. Verify Cloudflare/domain route only after local 2278 works.

## Root cause status
Not fully confirmed yet. Possible causes include process stopped, wrong DB path, login hash mismatch, route/tunnel issue, or client agents redirected/changed. No claim should be made until diagnostics are run.

## Rule
Do not touch V10 until 2278 login and client data collection are confirmed healthy.
