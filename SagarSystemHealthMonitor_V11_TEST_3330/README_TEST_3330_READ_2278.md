# Sagar System Health Monitor V11 TEST 3330 Bridge

This package is for your exact requirement:

- Do **not** touch the working `2278` server.
- Run a separate V11 test dashboard on **port `3330`**.
- Read live production/client data from existing `http://127.0.0.1:2278` APIs.
- Keep test-only asset register / ISO audit / settings / test messages in local shadow JSON under the test folder.
- Run from **G drive** folder.

## Recommended folder

```powershell
G:\SagarSystemHealthMonitor_V11_TEST_3330
```

## Install/copy to G drive

From the extracted package folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\INSTALL_TO_G_DRIVE_TEST_3330.ps1 -Target "G:\SagarSystemHealthMonitor_V11_TEST_3330" -SourceUrl "http://127.0.0.1:2278" -Port 3330
```

## Run test dashboard

```powershell
cd G:\SagarSystemHealthMonitor_V11_TEST_3330
powershell -ExecutionPolicy Bypass -File .\RUN_TEST_3330_READ_2278.ps1 -SourceUrl "http://127.0.0.1:2278" -Port 3330
```

Open:

```text
http://127.0.0.1:3330
```

LAN test:

```text
http://SERVER-IP:3330
```

Health check:

```text
http://127.0.0.1:3330/api/test3330/health
```

## What 3330 does

3330 is a bridge/proxy:

```text
Browser -> http://127.0.0.1:3330 -> existing http://127.0.0.1:2278
```

So your Windows/Ubuntu clients continue sending data only to 2278. The 3330 app only reads the already collected 2278 data.

## Safe write behavior

By default, 3330 does **not** write messages/notification changes into 2278.

Local-only test data is stored here:

```text
data\test3330_shadow_store.json
```

This includes:

- manual hardware asset test rows
- manual software asset test rows
- ISO audit test evidence
- local settings test values
- local test messages/notifications

## Allow writing to 2278 only when you really want

Default is safe:

```powershell
$env:CMP_3330_ALLOW_WRITE_2278 = "0"
```

Only if you want POST/PUT/DELETE to go to the real 2278 server:

```powershell
$env:CMP_3330_ALLOW_WRITE_2278 = "1"
python -u .\server_3330_proxy.py --host 0.0.0.0 --port 3330 --source http://127.0.0.1:2278
```

## Testing commands

After 3330 is running:

```powershell
powershell -ExecutionPolicy Bypass -File .\TEST_3330_READ_2278.ps1 -TestUrl "http://127.0.0.1:3330" -SourceUrl "http://127.0.0.1:2278"
```

## CI/static tests

```powershell
python -m py_compile .\server_3330_proxy.py
node --check .\public\app.js
python .\tests\static_check.py
```

## Important safety note

This package is a **test runner**. It does not replace:

```text
D:\SagarSystemHealthMonitor\server.py
D:\SagarSystemHealthMonitor\public\app.js
D:\SagarSystemHealthMonitor\scripts\client_windows.ps1
D:\SagarSystemHealthMonitor\scripts\client_ubuntu.sh
D:\SagarSystemHealthMonitor\data\monitor.db
```

Your current 2278 monitor remains source of truth.
