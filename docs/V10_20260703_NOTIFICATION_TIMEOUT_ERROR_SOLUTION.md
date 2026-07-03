# V10 Notification Test Timeout Error and Solution — 2026-07-03

## Error
Latest test for machine-wise clean UI timed out on:

`/api/v10/source2278/notification-test`

The earlier parts passed:

- index has machine-wise clean UI files
- 2278 hardware source OK with 64 machines
- fresh machine has hostname/cpu/disk/network arrays
- software source OK with 58,353 rows

## Meaning
This is not a data-source failure. It is a notification simulation performance problem.

## Solution
The notification test endpoint must be changed from heavy full scan to fast safe simulation:

1. Limit machines checked by default to fresh machines only.
2. Limit rows to a configurable maximum such as 50.
3. Avoid reading huge payloads repeatedly inside the loop.
4. Cache parsed latest rows for a short TTL.
5. Add query parameters:
   - `max_machines=50`
   - `freshness=fresh`
   - `timeout_ms=3000`
6. Return partial result with `timed_out: true` instead of blocking PowerShell.
7. UI should never wait on notification-test; it should use alert summary endpoint.

## Acceptance
`TEST_V10_MACHINEWISE_2278_UI_CLEAN.ps1` should pass without timing out.
