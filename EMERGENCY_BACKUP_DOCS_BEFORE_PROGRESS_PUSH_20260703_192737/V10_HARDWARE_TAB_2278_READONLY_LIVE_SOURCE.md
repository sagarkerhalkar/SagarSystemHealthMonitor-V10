# V10 Hardware Tab from 2278 Read-Only Live Source

Date: 2026-07-03

## Scope
This phase adds the Hardware tab foundation using the working 2278 database as a read-only live source.

## Safety
- Does not modify 2278.
- Does not restart 2278.
- Does not write to `D:\SagarSystemHealthMonitor\data\monitor.db`.
- Reads SQLite with `mode=ro` only.

## APIs added
- `/api/v10/source2278/hardware/status`
- `/api/v10/source2278/hardware`
- `/api/v10/source2278/hardware-machine?machine_id=...`
- `/api/v10/source2278/hardware/export.csv`

## Hardware details extracted when reported by client
- Machine name / hostname
- Serial number / motherboard serial / BIOS serial
- CPU name, usage, temp, core data if reported
- RAM total, used, free, usage, slots if reported
- SSD/HDD/NVMe disk list, capacity, usage, health/temp if reported
- GPU name, memory, usage, temp if reported
- USB/peripherals including keyboard/mouse/headset/storage when reported
- Network adapters, IP/MAC/gateway/DNS when reported
- Software count
- VPN/public IP/ISP from latest summary when reported

## Missing data rule
If client payload does not report a value, show `Not reported by client`. Never fake hardware values.

## Notification test
The acceptance test also verifies `/api/v10/source2278/notification-test` so notifications remain working while Hardware tab is added.
