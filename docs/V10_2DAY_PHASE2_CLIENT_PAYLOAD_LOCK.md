# V10 2-Day Phase 2 Client Payload Lock

Date: 2026-07-03

## Purpose
This phase fixes the server-side mapping that was causing CPU/GPU/RAM/SSD/software/USB/network values to show missing, zero or wrong even when client payload contained data.

## Scope
- CPU: name, usage, temperature, cores, logical processors.
- RAM: total, used, free, percent.
- Storage: SSD/HDD/NVMe disks, mount, type, total, used, free, percent.
- GPU: name, memory, usage, temperature. No fake GPU.
- Software: installed app list and count from live payload.
- USB/peripherals: device list and count, preserving old cleaner when available.
- Network: adapters, IPs, MAC, gateway, DNS, traffic.
- VPN: detected from explicit VPN object and VPN adapter names.
- Internet metrics: current upload/download, daily upload/download, latency, jitter, packet loss.

## Delivery rule
This does not replace UI. It fixes the data bridge first. UI can only be connected after Phase 1 and Phase 2 tests pass.

## Test
Run:

```powershell
powershell -ExecutionPolicy Bypass -File "D:\SagarMonitor_V10_CleanBuild\tests\TEST_V10_2DAY_PHASE2_CLIENT_PAYLOAD.ps1" -BaseUrl "http://127.0.0.1:2294"
```

Expected result: `PHASE2 TEST PASS`.
