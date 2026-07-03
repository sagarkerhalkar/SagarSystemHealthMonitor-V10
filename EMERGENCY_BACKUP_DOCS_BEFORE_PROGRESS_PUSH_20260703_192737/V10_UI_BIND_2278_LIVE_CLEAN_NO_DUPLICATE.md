# V10 UI Bind 2278 Live Clean No Duplicate

This step is not a restart and not a backend logic rewrite.

It binds existing V10 customer pages to the verified 2278 read-only APIs:

- Home / Command Center
- Machine Fleet
- Machine 360
- Hardware Intelligence
- Software Intelligence

Source of truth:

`D:\SagarSystemHealthMonitor\data\monitor.db` read-only, `latest.summary_json`.

Rules:

- No write to 2278.
- No client rebuild.
- No recalculation of working CPU/RAM/GPU/SSD/network/traffic logic.
- Old single-client V10 cards are replaced on these pages.
- Missing serial remains an audit gap; asset fingerprint is displayed separately.
- Notification test remains read-only.
