# V10 ISP/WAN UI Test JSON Decode Fix

The endpoint `/api/v10/settings/isp-links` was returning valid JSON:

```json
{"ok": true, "max_isp_links": 10, "links": []}
```

PowerShell `Invoke-WebRequest` returned the response body as a byte array on this machine, so the old test converted it to decimal byte values and incorrectly reported `Non-JSON`.

Fix: update the test helper to decode byte-array HTTP responses as UTF-8 and prefer `Invoke-RestMethod` for JSON endpoints.

No application code, database, login, 2278 server, or V10 server logic is changed by this fix. This is a test-script-only correction.
