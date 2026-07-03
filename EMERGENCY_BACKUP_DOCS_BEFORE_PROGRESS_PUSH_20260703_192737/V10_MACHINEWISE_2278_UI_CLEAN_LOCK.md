# V10 Machine-wise 2278 UI Clean Binding Lock

Date: 2026-07-03

## Purpose
Fix the confusing duplicate UI problem without changing the working 2278 source logic.

## Locked source
- Source DB: `D:\SagarSystemHealthMonitor\data\monitor.db`
- Read mode: SQLite read-only
- Table: `latest`
- Field: `summary_json`

## This patch does
- Home becomes compact and shows 2278 client counts, traffic KPIs, alerts and ISP/WAN summary.
- Machine Fleet stays as list/table with filters.
- Machine 360 becomes machine-wise and includes software rows for selected machine.
- Network + VPN becomes machine-wise, not fleet again.
- Hardware Intelligence becomes machine-wise, not fleet again.
- Software Intelligence becomes machine-wise, not all-machine fleet again.
- Hostname and asset fingerprint are displayed separately from official serial number.
- Old duplicate cards/old fake-looking summary sections are replaced in these pages.

## This patch does not do
- It does not change 2278.
- It does not rebuild client.
- It does not recalculate CPU/GPU/RAM/SSD/network logic.
- It does not fake missing serial number.
- It does not start ISO work.

## Next gate
Proceed to ISO only after these pages are visually accepted:
- Home / Command Center
- Machine Fleet
- Machine 360
- Network + VPN
- Hardware Intelligence
- Software Intelligence
