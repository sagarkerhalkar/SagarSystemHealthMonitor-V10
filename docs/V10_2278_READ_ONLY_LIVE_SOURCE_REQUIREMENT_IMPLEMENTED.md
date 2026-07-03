# V10 2278 Read-Only Live Source Requirement Implemented

Date: 2026-07-03

## Requirement

V10 must read the working 2278 monitor data without modifying 2278.

2278 HTTP API endpoints may return 401 because they are protected by login. That is acceptable. V10 must therefore read the 2278 SQLite database directly in read-only mode.

## Safety rule

- Do not modify `D:\SagarSystemHealthMonitor`.
- Do not write to `D:\SagarSystemHealthMonitor\data\monitor.db`.
- Do not restart or patch 2278.
- V10 only reads `D:\SagarSystemHealthMonitor\data\monitor.db` using SQLite `mode=ro`.

## APIs added in V10

- `GET /api/v10/source2278/status`
- `GET /api/v10/source2278/machines`
- `GET /api/v10/source2278/home-traffic-kpi`
- `GET /api/v10/source2278/notifications`
- `GET /api/v10/source2278/notification-test`
- `GET /api/v10/source2278/machines/export.csv`

Aliases are also available under `/api/v10/live-source2278/...`.

## Data parsed from 2278 latest table

- machine id
- hostname
- OS
- primary IP
- CPU usage and temperature if reported
- RAM total/used/free/usage
- disk max usage
- GPU name/count/memory/usage/temp if reported
- WAN download/upload Mbps
- today download/upload GB
- VPN status
- ISP name and public IP from client payload if present
- software count
- USB count
- last updated time and freshness

## Notification test

The notification test endpoint reads 2278 notification rules and latest machine data, then simulates alerts in memory only. It does not write alerts anywhere.

Rules simulated:

- cpu_ram_critical
- disk_high
- cpu_temp_high
- gpu_temp_high

## Important freshness note

If the newest 2278 latest row is older than 10 minutes, the connector is working but data is stale. That means clients may not currently be posting fresh data to 2278, or latest table has old rows only.
